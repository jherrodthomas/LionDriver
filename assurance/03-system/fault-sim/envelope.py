"""Envelope in the loop: the real opendbc safety code (Toyota mode) through libsafety, plus Python models of the
panda firmware timing that is not part of libsafety (heartbeat monitor, sirens, hardware watchdog, relay).

libsafety is compiled here from `opendbc_repo/opendbc/safety/tests/libsafety/safety.c` with the flags of
`libsafety_py._build_libsafety` for a release build (no ALLOW_DEBUG) of the LionDriver reference build
(LIONDRIVER_REFERENCE), into a temporary directory so the submodule stays clean. Its C declarations are taken from
`libsafety_py.ffi`. The firmware constants are read from the panda sources, so a change there changes the results.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OPENDBC = ROOT / "opendbc_repo"
PANDA = ROOT / "panda"
SAFETY_C = OPENDBC / "opendbc" / "safety" / "tests" / "libsafety" / "safety.c"

SAFETY_TOYOTA = 2      # opendbc/safety/declarations.h SAFETY_TOYOTA
TOYOTA_PARAM = 73      # reference safety parameter: EPS factor 73, no flags (WP-S-02 TSR-512)


def _define(path: Path, name: str) -> int:
  m = re.search(rf"#define {name} (\d+)U?", path.read_text(encoding="utf-8"))
  if not m:
    raise RuntimeError(f"{name} not found in {path}")
  return int(m.group(1))


DRIVERS = PANDA / "board" / "drivers"
FW = {
  # 100 Hz safety task (panda main.c safety_task_handler)
  "heartbeat_timeout_ticks": _define(DRIVERS / "heartbeat_monitor.h", "HEARTBEAT_AUTHORITY_TIMEOUT_TICKS"),
  "heartbeat_siren_hold_ticks": _define(DRIVERS / "heartbeat_siren.h", "HEARTBEAT_SIREN_HOLD_TICKS"),
  "eps_siren_persist_ticks": _define(DRIVERS / "eps_fault_siren.h", "EPS_FAULT_SIREN_PERSIST_TICKS"),
  "eps_siren_hold_ticks": _define(DRIVERS / "eps_fault_siren.h", "EPS_FAULT_SIREN_HOLD_TICKS"),
  "iwdg_reload": _define(DRIVERS / "hw_watchdog.h", "HW_WATCHDOG_RELOAD"),
  "iwdg_prescaler_code": _define(DRIVERS / "hw_watchdog.h", "HW_WATCHDOG_PRESCALER"),
  # 1 Hz path of the 8 Hz tick (panda main.c tick_handler)
  "heartbeat_silent_cnt_on": _define(PANDA / "board" / "main.c", "HEARTBEAT_IGNITION_CNT_ON"),
}
LSI_HZ_NOMINAL = 32000.0  # STM32H7 LSI nominal; WP-S-04 T-09a
IWDG_DIV = 4 << FW["iwdg_prescaler_code"]  # PR = 0 -> divide by 4


def iwdg_timeout_s(lsi_hz: float = LSI_HZ_NOMINAL) -> float:
  return IWDG_DIV * (FW["iwdg_reload"] + 1) / lsi_hz


def _build() -> str:
  sys.path.insert(0, str(OPENDBC))
  from opendbc.safety.tests.libsafety import libsafety_py  # noqa: E402  (cffi declarations only; nothing is built)
  out = Path(tempfile.mkdtemp(prefix="ld-fault-sim-"))
  obj, so = out / "safety.o", out / "libsafety.so"
  cflags = ["-Wall", "-Wextra", "-Werror", "-nostdlib", "-fno-builtin", "-std=gnu11", "-Wfatal-errors",
            "-Wno-pointer-to-int-cast", "-g", "-O0", "-fno-omit-frame-pointer", "-DLIONDRIVER_REFERENCE"]
  subprocess.check_call(["cc", "-fPIC", *cflags, "-I", str(OPENDBC), "-c", str(SAFETY_C), "-o", str(obj)])
  subprocess.check_call(["cc", "-shared", str(obj), "-o", str(so)])
  global ffi
  ffi = libsafety_py.ffi
  return str(so)


ffi = None
_lib = None


def lib():
  global _lib
  if _lib is None:
    path = _build()
    _lib = ffi.dlopen(path)
  return _lib


# --------------------------------------------------------------------------- CAN frames (byte layouts as parsed
# by modes/toyota.h; signal positions from opendbc/dbc/generator/toyota/_toyota_2017.dbc)

def _cks(addr: int, data: bytearray) -> bytearray:
  s = (addr & 0xFF) + (addr >> 8) + len(data) + sum(data[:-1])
  data[-1] = s & 0xFF
  return data


def _i16(v: int) -> tuple[int, int]:
  v = int(v) & 0xFFFF
  return v >> 8, v & 0xFF


def wheel_speeds(v_ms: float) -> bytearray:
  raw = int(round(v_ms * 3.6 / 0.01 + 6767))
  d = bytearray(8)
  for i in range(4):
    d[2 * i], d[2 * i + 1] = (raw >> 8) & 0x7F, raw & 0xFF
  return d


def steer_torque_sensor(eps_torque_cmd_units: float, driver_raw: float) -> bytearray:
  d = bytearray(8)
  d[1], d[2] = _i16(round(driver_raw))
  d[5], d[6] = _i16(round(eps_torque_cmd_units * 100.0 / TOYOTA_PARAM))  # envelope scales by 73/100
  return _cks(0x260, d)


def pcm_cruise(active: bool, gas_pressed: bool = False) -> bytearray:
  d = bytearray(8)
  d[0] = (0x20 if active else 0) | (0 if gas_pressed else 0x10)
  return _cks(0x1D2, d)


def pcm_cruise_2(main_on: bool = True) -> bytearray:
  d = bytearray(8)
  d[1] = 0x80 if main_on else 0
  return _cks(0x1D3, d)


def brake_module(pressed: bool) -> bytearray:
  d = bytearray(8)
  d[4] = 0x20 if pressed else 0
  return d


LKA_STATE_ACTIVE = 5   # not in the envelope's fault set {0, 3, 9, 11, 17, 21, 25}
LKA_STATE_FAULT = 25   # "temporary fault"


def eps_status(lka_state: int) -> bytearray:
  d = bytearray(8)
  d[3] = (lka_state & 0x7F) << 1
  return _cks(0x262, d)


def steering_lka(torque: int, steer_req: bool) -> bytearray:
  d = bytearray(5)
  d[0] = 1 if steer_req else 0
  d[1], d[2] = _i16(torque)
  return _cks(0x2E4, d)


def acc_control(accel: float) -> bytearray:
  d = bytearray(8)
  d[0], d[1] = _i16(round(accel * 1000.0))
  return _cks(0x343, d)


# --------------------------------------------------------------------------- envelope + panda firmware model

class Panda:
  """libsafety (real C) for the safety mode; firmware timing modelled after panda main.c and drivers/*."""

  def __init__(self, eps_persist_ticks: int | None = None):
    self.c = lib()
    self.eps_persist_limit = FW["eps_siren_persist_ticks"] if eps_persist_ticks is None else eps_persist_ticks
    self.c.set_safety_hooks(SAFETY_TOYOTA, TOYOTA_PARAM)
    self.c.init_tests()
    self.c.set_heartbeat_engaged(True)
    self.hb_age = 0
    self.hb_siren = 0
    self.eps_persist = 0
    self.eps_siren = 0
    self.hung = False
    self.silent = False   # SS-S after a watchdog reset: no TX, relay released, no siren (DQ-054 not implemented)
    self.hb_silent = False  # SILENT after the 1 Hz heartbeat loss (T-06b): no TX, relay released, siren allowed
    self.last_feed_us = 0
    self.heartbeat_counter = 0
    self.siren_countdown = 0
    self.controls_allowed_countdown = 0
    self.loop_counter = 0
    self._hb_engaged = True

  def _pkt(self, addr: int, bus: int, data: bytearray):
    from opendbc.safety import LEN_TO_DLC
    p = ffi.new("CANPacket_t *")
    p[0].extended = 0
    p[0].addr = addr
    p[0].data_len_code = LEN_TO_DLC[len(data)]
    p[0].bus = bus
    p[0].data = bytes(data)
    return p

  def set_time(self, t_us: int):
    self.c.set_timer(t_us & 0xFFFFFFFF)

  @property
  def down(self) -> bool:
    return self.hung or self.silent or self.hb_silent

  def rx(self, addr: int, data: bytearray, bus: int = 0) -> None:
    if not self.down:
      self.c.safety_rx_hook(self._pkt(addr, bus, data))

  def tx(self, addr: int, data: bytearray) -> bool:
    """True if the frame reaches the car-side bus."""
    if self.down:
      return False
    return bool(self.c.safety_tx_hook(self._pkt(addr, 0, data)))

  def heartbeat(self, engaged: bool) -> None:
    if not (self.hung or self.silent):
      self.hb_age = 0
      self.heartbeat_counter = 0
      self._hb_engaged = engaged
      self.c.set_heartbeat_engaged(engaged)

  def safety_task(self, t_us: int) -> None:
    """One 100 Hz safety task, in the order of panda main.c safety_task_handler."""
    if self.down:
      return
    self.c.safety_tick()
    if self.hb_age < FW["heartbeat_timeout_ticks"]:
      self.hb_age += 1
    revoke = self.hb_age >= FW["heartbeat_timeout_ticks"]
    allowed = bool(self.c.get_controls_allowed())
    if revoke and allowed:
      self.hb_siren = FW["heartbeat_siren_hold_ticks"]
    elif self.hb_siren > 0:
      self.hb_siren -= 1
    if revoke:
      self.c.set_controls_allowed(False)
    eps_fault = bool(self.c.get_safety_eps_fault())
    allowed = bool(self.c.get_controls_allowed())
    if eps_fault and allowed:
      self.eps_persist = min(self.eps_persist + 1, self.eps_persist_limit)
    else:
      self.eps_persist = 0
    if self.eps_persist >= self.eps_persist_limit:
      self.eps_siren = FW["eps_siren_hold_ticks"]
    elif self.eps_siren > 0:
      self.eps_siren -= 1
    self.last_feed_us = t_us  # IWDG fed after main-loop progress (hw_watchdog_tick)

  def speaker_tick(self) -> bool:
    """One 8 Hz tick (main.c tick_handler): returns True if the speaker sounds on this tick."""
    if self.hung or self.silent:
      return False
    sound = bool(self.loop_counter & 1) and (self.siren_countdown > 0 or self.eps_siren > 0 or self.hb_siren > 0)
    if self.loop_counter == 0:
      self._one_hz()
    self.loop_counter = (self.loop_counter + 1) % 8
    return sound

  def _one_hz(self) -> None:
    self.heartbeat_counter += 1
    if self.siren_countdown > 0:
      self.siren_countdown -= 1
    hb_engaged = bool(self.c.get_heartbeat_engaged()) if hasattr(self.c, "get_heartbeat_engaged") else self._hb_engaged
    if self.controls_allowed or hb_engaged:
      self.controls_allowed_countdown = 5
    elif self.controls_allowed_countdown > 0:
      self.controls_allowed_countdown -= 1
    if self.heartbeat_counter >= FW["heartbeat_silent_cnt_on"] and not self.hb_silent:
      if self.controls_allowed_countdown > 0:
        self.siren_countdown = 3
        self.controls_allowed_countdown = 0
      self.c.set_heartbeat_engaged(False)
      self._hb_engaged = False
      self.hb_silent = True   # set_safety_mode(SAFETY_SILENT): no TX, relay released

  @property
  def controls_allowed(self) -> bool:
    return bool(self.c.get_controls_allowed()) and not self.down

  @property
  def relay_malfunction(self) -> bool:
    return bool(self.c.get_relay_malfunction())
