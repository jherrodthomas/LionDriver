"""The panda safety code in the loop: builds sim_panda.c into a shared library and drives it like the firmware.

What is real code: every decision on a CAN frame (opendbc libsafety, Toyota mode, reference build), the 100 Hz
safety task (RX timeouts, TX-arrival supervision, heartbeat monitor, both sirens, IWDG feed) and the frame packing
of the host (opendbc CANPacker, `toyotacan.create_steer_command`). What is modelled here: the clocks that call that
code, and the IWDG hardware counter, which counts down from the reload value the firmware writes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from functools import cache
from pathlib import Path

from corolla import ROOT

sys.path.insert(0, str(ROOT / "opendbc_repo"))
from opendbc.safety.tests.libsafety import libsafety_py  # noqa: E402  (cffi declarations of libsafety)
from opendbc.can import CANPacker  # noqa: E402

HERE = Path(__file__).resolve().parent
SAFETY_TOYOTA = 2            # opendbc CarParams.SafetyModel.toyota
REFERENCE_PARAM = 73         # panda/board/reference_lock.h LIONDRIVER_REFERENCE_TOYOTA_PARAM (EPS factor 73, no flags)
LSI_HZ = 32000.0             # nominal LSI frequency of the STM32H7 (hw_watchdog.h comment); tolerance not modelled
DBC = "toyota_nodsu_pt_generated"

ffi = libsafety_py.ffi
ffi.cdef("""
void sim_safety_task(void);
void sim_heartbeat(bool engaged);
bool sim_siren_on(uint8_t loop_counter);
void sim_relay_driven(void);
void sim_main_loop_alive(void);
void sim_board_reset(void);
bool sim_get_heartbeat_siren(void);
bool sim_get_eps_fault_siren(void);
bool sim_get_relay_malfunction(void);
uint32_t sim_iwdg_kr(void);
void sim_iwdg_clear_kr(void);
uint32_t sim_iwdg_pr(void);
uint32_t sim_iwdg_rlr(void);
uint32_t sim_iwdg_winr(void);
bool sim_iwdg_running(void);
""")


@cache
def build(reference: bool = True) -> str:
  """Compile sim_panda.c (with libsafety and the panda drivers) and return the library path."""
  fd, out = tempfile.mkstemp(suffix=".so", prefix="sim_panda_")
  os.close(fd)
  cmd = ["cc", "-fPIC", "-shared", "-std=gnu11", "-O1", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function",
         "-Wno-unused-parameter", "-Wno-pointer-to-int-cast", "-DALLOW_DEBUG",
         "-I", str(ROOT / "opendbc_repo"), "-I", str(ROOT / "panda"), str(HERE / "sim_panda.c"), "-o", out]
  if reference:
    cmd.insert(5, "-DLIONDRIVER_REFERENCE")
  subprocess.check_call(cmd)
  return out


class Panda:
  """One safety MCU: libsafety state plus the board drivers, with an IWDG counter model."""

  def __init__(self, reference: bool = True):
    # each Panda gets its own copy of the library, so runs do not share static firmware state
    src = build(reference)
    fd, path = tempfile.mkstemp(suffix=".so", prefix="sim_panda_run_")
    os.close(fd)
    Path(path).write_bytes(Path(src).read_bytes())
    self.lib = ffi.dlopen(path)
    os.unlink(path)
    self.packer = CANPacker(DBC)
    self.hung = False
    self.resets = 0
    self.iwdg_counter = None   # None: not started
    self._iwdg_frac = 0.0
    self.boot()

  # ------------------------------------------------------------------ firmware life cycle
  def boot(self):
    lib = self.lib
    lib.sim_board_reset()
    lib.set_safety_hooks(SAFETY_TOYOTA, REFERENCE_PARAM)
    lib.init_tests()
    lib.set_heartbeat_engaged(False)
    self.iwdg_counter = None
    self.relay_driven = True
    lib.sim_relay_driven()

  def reset_to_silent(self):
    """IWDG reset: GPIOs float, the switch returns to pass-through, the firmware restarts in SILENT."""
    self.resets += 1
    self.lib.sim_board_reset()
    self.lib.set_safety_hooks(0, 0)   # SAFETY_SILENT: nothing is sent, nothing is forwarded
    self.relay_driven = False
    self.iwdg_counter = None
    self.hung = False

  # ------------------------------------------------------------------ hooks (each is the real firmware code)
  def set_time(self, t_us: int):
    self.lib.set_timer(t_us & 0xFFFFFFFF)

  def rx(self, name: str, values: dict, bus: int = 0) -> bool:
    if self.hung:
      return False
    addr, dat, bus = self.packer.make_can_msg(name, bus, values)
    return bool(self.lib.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, dat)))

  def rx_raw(self, addr: int, dat: bytes, bus: int = 0) -> bool:
    if self.hung:
      return False
    return bool(self.lib.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, dat)))

  def tx(self, addr: int, dat: bytes, bus: int = 0) -> bool:
    """True if the frame is sent to the car (the TX hook allows it)."""
    if self.hung or not self.relay_driven:
      return False
    return bool(self.lib.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat)))

  def heartbeat(self, engaged: bool):
    if not self.hung and self.relay_driven:
      self.lib.sim_heartbeat(engaged)

  def main_loop(self):
    if not self.hung:
      self.lib.sim_main_loop_alive()

  def safety_task(self):
    """100 Hz safety task. Returns 'reset' when the IWDG fires during this period."""
    # the counter runs down over the 10 ms since the previous task period, then the task may feed it
    if self.iwdg_step(0.010) == "reset":
      return "reset"
    if not self.hung:
      self.lib.sim_safety_task()
      if self.lib.sim_iwdg_running() and self.iwdg_counter is None:
        self.iwdg_counter = float(self.lib.sim_iwdg_rlr())
      if self.lib.sim_iwdg_kr() == 0xAAAA:   # the firmware wrote the feed key
        self.lib.sim_iwdg_clear_kr()
        if self.iwdg_counter is not None and self.iwdg_counter > self.lib.sim_iwdg_winr():
          return self._fire()                # window mode: a feed before the window opens resets
        self.iwdg_counter = float(self.lib.sim_iwdg_rlr())
    return None

  def iwdg_step(self, dt: float):
    if self.iwdg_counter is None:
      return None
    div = 4 * 2 ** self.lib.sim_iwdg_pr()
    self.iwdg_counter -= dt * LSI_HZ / div
    if self.iwdg_counter <= 0:
      return self._fire()
    return None

  def iwdg_timeout(self) -> float:
    """Nominal timeout (s) from the values the firmware writes: 4 * 2^PR * (RLR + 1) / f_LSI."""
    return 4 * 2 ** self.lib.sim_iwdg_pr() * (self.lib.sim_iwdg_rlr() + 1) / LSI_HZ

  def _fire(self):
    self.reset_to_silent()
    return "reset"

  # ------------------------------------------------------------------ state
  @property
  def controls_allowed(self) -> bool:
    return bool(self.lib.get_controls_allowed())

  @property
  def eps_fault(self) -> bool:
    return bool(self.lib.get_safety_eps_fault())

  @property
  def relay_malfunction(self) -> bool:
    return bool(self.lib.sim_get_relay_malfunction())

  def siren(self, loop_counter: int) -> bool:
    return (not self.hung) and bool(self.lib.sim_siren_on(loop_counter & 0xFF))
