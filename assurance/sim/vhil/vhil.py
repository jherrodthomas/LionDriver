"""Virtual HIL bench: the panda HIL tests (panda/tests/hitl) against the panda firmware's safety code on the host.

The firmware logic is the same source the plant model runs (../plant/sim_panda.c, built by ../plant/panda_loop.py):
opendbc libsafety (Toyota mode, reference build) and the panda drivers of the 100 Hz safety task (heartbeat monitor,
heartbeat and EPS-fault sirens, the engaged-mismatch check). What is modelled here is the bench around it:

  - VirtualPanda and VirtualJungle offer the calls the HIL tests make on Panda and PandaJungle (health, can_send,
    send_heartbeat, set_safety_mode, can_send_many, ...). The jungle plays the car on bus 0 of the default harness.
  - The clocks. Firmware time is locked to time.monotonic(): before each call is served, every safety-task run
    (100 Hz), tick (8 Hz, speaker on odd ticks) and 1 Hz pass that has fallen due runs in order, then the call is
    applied at that instant. One lock serialises the calls of all test threads. So the firmware sees the same
    timing as on the bench, and a slow test thread shows only as late polling, like USB latency on the bench.
  - The CAN paths of panda/board/drivers (can_common.h can_send: the TX hook, safety_tx_blocked; fdcan.h: the RX and
    forwarding hooks, safety_rx_invalid) and the parts of main.c set_safety_mode that the safety code reads.

Not modelled (these stay on the real bench): main.c interrupt priorities and load, USB and SPI, the relay and the
harness, the IWDG hardware (test_10), the USB command lock (test_11), the 1 Hz heartbeat-loss SILENT path (T-06b) and
the 1 Hz siren countdown (T-07). A model of the bench, not a measurement (WP-S-04 §6).
"""

from __future__ import annotations

import os
import sys
import threading
import time
import types
from collections import deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "plant"))
import panda_loop
from panda_loop import ffi, libsafety_py

ffi.cdef("""
void heartbeat_siren_reset(void);
void eps_fault_siren_reset(void);
void heartbeat_monitor_reset(void);
void engaged_mismatch_reset(void);
""")

SAFETY_SILENT = 0            # opendbc CarParams.SafetyModel.silent
TASK_US = 10_000             # SAFETY_TASK_FREQ 100 Hz (panda/board/stm32h7/stm32h7_config.h)
TICK_US = 125_000            # tick_handler, 8 Hz (panda/board/main.c)
QUEUE_MAX = 4096             # CAN frames kept per receive queue; older ones are dropped, as a full ring would


class VirtualFirmware:
  """The panda firmware's safety code with its clocks, shared by the virtual panda and jungle of one bench."""

  def __init__(self, reference: bool | None = None, clock=time.monotonic):
    if reference is None:
      reference = os.environ.get("REFERENCE_BUILD") == "1"
    self.reference = reference
    self.lib = ffi.dlopen(panda_loop.build(reference))
    self.lock = threading.RLock()
    self.clock = clock                               # wall clock the firmware time is locked to (tests pass a fake)
    self.t0 = clock()
    self.panda_rx: deque = deque(maxlen=QUEUE_MAX)   # frames the host reads with can_recv (bus, or 0x80 | bus echo)
    self.jungle_rx: deque = deque(maxlen=QUEUE_MAX)  # frames the car side (jungle) receives
    self.siren_log: list[tuple[int, bool]] = []      # (firmware µs, speaker on) at every change
    self.revocations: list[int] = []                 # firmware µs at every controls_allowed true -> false
    self.boot()

  # ---------------------------------------------------------------- clocks
  def now_us(self) -> int:
    return int((self.clock() - self.t0) * 1e6)

  def _advance(self, until_us: int) -> None:
    """Run every safety-task run and tick due up to until_us, in time order (the task first on a tie)."""
    lib = self.lib
    while min(self.next_task, self.next_tick) <= until_us:
      if self.next_task <= self.next_tick:
        t = self.next_task
        lib.set_timer(t & 0xFFFFFFFF)
        before = lib.get_controls_allowed()
        lib.sim_main_loop_alive()
        lib.sim_safety_task()
        self._note_revocation(before, t)
        self.task_runs += 1
        self.next_task += TASK_US
      else:
        t = self.next_tick
        lib.set_timer(t & 0xFFFFFFFF)
        on = bool(lib.sim_siren_on(self.loop_counter))
        if on != self.speaker:
          self.speaker = on
          self.siren_log.append((t, on))
        if self.loop_counter == 0:  # main.c: the 1 Hz part of tick_handler
          before = lib.get_controls_allowed()
          lib.sim_tick_1hz()
          self._note_revocation(before, t)
        self.loop_counter = (self.loop_counter + 1) % 8
        self.ticks += 1
        self.next_tick += TICK_US
    self.time_us = until_us
    lib.set_timer(until_us & 0xFFFFFFFF)

  def _note_revocation(self, before: bool, t: int) -> None:
    if before and not self.lib.get_controls_allowed():
      self.revocations.append(t)

  def sync(self) -> int:
    """Bring the firmware up to the wall clock; call with the lock held. Returns the firmware time in µs."""
    self._advance(max(self.now_us(), self.time_us))
    return self.time_us

  # ---------------------------------------------------------------- firmware entry points
  def boot(self) -> None:
    """Power-on reset: static state cleared, SILENT mode (panda/board/main.c)."""
    with self.lock:
      self.time_us = self.now_us()
      self.next_task = self.time_us + TASK_US
      self.next_tick = self.time_us + TICK_US
      self.loop_counter = 0
      self.task_runs = 0
      self.ticks = 0
      self.speaker = False
      self.lib.sim_board_reset()
      self.set_safety_mode(SAFETY_SILENT, 0)
      self.alternative_experience = 0
      self.panda_rx.clear()
      self.jungle_rx.clear()

  def set_safety_mode(self, mode: int, param: int) -> None:
    """panda/board/main.c set_safety_mode: the hooks, the siren and monitor state, the counters."""
    with self.lock:
      self.sync()
      lib = self.lib
      before = lib.get_controls_allowed()
      if lib.set_safety_hooks(mode, param) == -1:
        lib.set_safety_hooks(SAFETY_SILENT, 0)
        mode = SAFETY_SILENT
      lib.eps_fault_siren_reset()
      lib.heartbeat_siren_reset()
      if self.reference:
        lib.engaged_mismatch_reset()
      self._note_revocation(before, self.time_us)
      self.mode = mode
      self.safety_tx_blocked = 0
      self.safety_rx_invalid = 0

  def heartbeat(self, engaged: bool) -> None:
    """panda/board/main_comms.h 0xf3."""
    with self.lock:
      self.sync()
      self.lib.sim_heartbeat(engaged)

  def host_send(self, addr: int, dat: bytes, bus: int) -> bool:
    """A frame from the host (USB): drivers/can_common.h can_send runs the TX hook; a refused frame is counted and
    dropped. A sent frame reaches the car side and is echoed to the host as 0x80 | bus."""
    with self.lock:
      self.sync()
      before = self.lib.get_controls_allowed()
      ok = self.mode != SAFETY_SILENT and bool(self.lib.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat)))
      self._note_revocation(before, self.time_us)
      if not ok:
        self.safety_tx_blocked += 1
        return False
      self.jungle_rx.append((addr, bytes(dat), bus))
      self.panda_rx.append((addr, bytes(dat), 0x80 | bus))
      return True

  def car_send(self, addr: int, dat: bytes, bus: int) -> None:
    """A frame from the car side (the jungle): drivers/fdcan.h runs the forwarding and RX hooks."""
    with self.lock:
      self.sync()
      before = self.lib.get_controls_allowed()
      pkt = libsafety_py.make_CANPacket(addr, bus, dat)
      fwd = int(self.lib.safety_fwd_hook(bus, addr))
      if fwd != -1 and self.mode != SAFETY_SILENT:
        self.jungle_rx.append((addr, bytes(dat), fwd))
      if not self.lib.safety_rx_hook(pkt):
        self.safety_rx_invalid += 1
      self._note_revocation(before, self.time_us)
      self.panda_rx.append((addr, bytes(dat), bus))

  def health(self) -> dict:
    """The fields of the panda health packet (panda/board/main_comms.h) the HIL tests read, plus the speaker."""
    with self.lock:
      self.sync()
      lib = self.lib
      return {
        "controls_allowed": bool(lib.get_controls_allowed()),
        "safety_mode": self.mode,
        "safety_param": int(lib.get_current_safety_param()),
        "safety_tx_blocked": self.safety_tx_blocked,
        "safety_rx_invalid": self.safety_rx_invalid,
        "eps_fault": bool(lib.get_safety_eps_fault()),
        "tx_rate_exceeded": bool(lib.get_safety_tx_rate_exceeded()),
        "alternative_experience": self.alternative_experience,
        "power_save_enabled": False,
        "heartbeat_lost": False,
        "faults": 0,
        "fault_status": 0,
        "siren": self.speaker,  # virtual bench only: the real host cannot read the speaker
      }

  def siren_on_since(self, t_us: int) -> int | None:
    """Firmware time of the first speaker-on edge at or after t_us, or None."""
    with self.lock:
      self.sync()
      return next((t for t, on in self.siren_log if on and t >= t_us), None)


CAN_HEALTH = {"bus_off_cnt": 0, "receive_error_cnt": 0, "transmit_error_cnt": 0, "error_passive": 0, "error_warning": 0,
              "total_rx_lost_cnt": 0, "total_tx_lost_cnt": 0, "total_error_cnt": 0, "total_tx_checksum_error_cnt": 0}


class _Device:
  """Calls that only configure bus hardware or the USB link: accepted and recorded, without effect on the logic."""

  def __init__(self, fw: VirtualFirmware):
    self.fw = fw
    self.can_speed = {0: 500, 1: 500, 2: 500}
    self.connected = True
    self.bootstub = False

  def set_can_speed_kbps(self, bus, speed):
    self.can_speed[bus] = speed

  def set_can_loopback(self, enable):
    pass

  def can_health(self, bus):
    return {**CAN_HEALTH, "can_speed": self.can_speed.get(bus, 500)}

  def close(self):
    pass

  def __enter__(self):
    return self

  def __exit__(self, *exc):
    return False


class VirtualPanda(_Device):
  """The calls of panda.Panda that the HIL tests use, served by the shared virtual firmware."""

  HW_TYPE_RED_PANDA = b"\x07"

  def __init__(self, serial=None, claim=True, **kwargs):
    super().__init__(bench())

  @staticmethod
  def wait_for_panda(serial, timeout):
    return True

  @staticmethod
  def list():
    return ["virtual-panda"]

  def get_usb_serial(self):
    return "virtual-panda"

  def get_serial(self):
    return ["virtual-panda", 0]

  def get_type(self):
    return self.HW_TYPE_RED_PANDA

  def get_dfu_serial(self):
    return "virtual-dfu"

  def up_to_date(self):
    return True

  def reset(self, enter_bootstub=False, enter_bootloader=False, reconnect=True):
    self.fw.boot()

  def reconnect(self):
    self.connected = True

  def set_safety_mode(self, mode, param=0):
    self.fw.set_safety_mode(int(mode), int(param))

  def set_alternative_experience(self, alternative_experience):
    self.fw.alternative_experience = int(alternative_experience)

  def set_power_save(self, power_save_enabled=0):
    pass

  def send_heartbeat(self, engaged=True):
    self.fw.heartbeat(bool(engaged))

  def can_send(self, addr, dat, bus, timeout=0):
    self.fw.host_send(addr, dat, bus)

  def can_send_many(self, arr, timeout=0):
    for addr, dat, bus in arr:
      self.fw.host_send(addr, dat, bus)

  def can_recv(self):
    with self.fw.lock:
      self.fw.sync()
      out = list(self.fw.panda_rx)
      self.fw.panda_rx.clear()
      return out

  def can_clear(self, bus):
    with self.fw.lock:
      if bus == 0xFFFF:
        self.fw.panda_rx.clear()

  def health(self):
    return self.fw.health()


class VirtualJungle(_Device):
  """The calls of panda.PandaJungle that the HIL tests use: the jungle plays the car on the panda's buses."""

  HARNESS_ORIENTATION_NONE = 0
  HARNESS_ORIENTATION_1 = 1
  HARNESS_ORIENTATION_2 = 2

  def __init__(self, serial=None, **kwargs):
    super().__init__(bench())

  def set_panda_power(self, enabled):
    pass

  def set_obd(self, obd):
    pass

  def set_harness_orientation(self, mode):
    pass

  def can_send(self, addr, dat, bus):
    self.fw.car_send(addr, dat, bus)

  def can_send_many(self, arr, timeout=0):
    for addr, dat, bus in arr:
      self.fw.car_send(addr, dat, bus)

  def can_recv(self):
    with self.fw.lock:
      self.fw.sync()
      out = list(self.fw.jungle_rx)
      self.fw.jungle_rx.clear()
      return out

  def can_clear(self, bus):
    with self.fw.lock:
      if bus == 0xFFFF:
        self.fw.jungle_rx.clear()

  def health(self):
    return {"ch1_power": True}


class VirtualPandaDFU:
  def __init__(self, serial=None):
    pass

  @staticmethod
  def list():
    return []

  def reset(self):
    pass


_BENCH: VirtualFirmware | None = None


def bench() -> VirtualFirmware:
  """The one virtual firmware of this process (the bench has one panda and one jungle)."""
  global _BENCH
  if _BENCH is None:
    _BENCH = VirtualFirmware()
  return _BENCH


def install() -> types.ModuleType:
  """Make `import panda` give the virtual bench, so the HIL tests run as on the bench. The module keeps the real package
  path, so panda.tests.hitl and its helpers import from the checkout; panda/python (USB, libusb) is never imported."""
  mod = types.ModuleType("panda")
  mod.__path__ = [str(ROOT / "panda")]
  mod.__file__ = str(ROOT / "panda" / "__init__.py")
  mod.Panda = VirtualPanda
  mod.PandaJungle = VirtualJungle
  mod.PandaDFU = VirtualPandaDFU
  sys.modules["panda"] = mod
  return mod
