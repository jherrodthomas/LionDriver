"""Panda safety in the simulation loop.

The simulated car hands every CAN frame to the same safety code that runs on the panda MCU
(opendbc_repo/opendbc/safety, built as libsafety), instead of bypassing it:
  - frames from the car (bus 0, 1, 2) go through safety_rx_hook, as on the panda's receive path;
  - frames from openpilot (sendcan) go through safety_tx_hook; a refused frame never reaches the simulated car;
  - safety_tick runs at 100 Hz, as the LionDriver safety task does;
  - the heartbeat's engaged flag comes from selfdriveState.enabled, as pandad sends it.

The library is compiled as the LionDriver reference build (LIONDRIVER_REFERENCE) in release mode, which is what the
reference vehicle runs. The microsecond timer is the simulation's wall clock.
"""
import os
import time

from opendbc.safety.tests.libsafety import libsafety_py

_lib = None


def load_libsafety():
  """Build and load libsafety once per process, as the LionDriver reference release build."""
  global _lib
  if _lib is None:
    # globals the panda reports in its health packet; not exported as functions by libsafety
    libsafety_py.ffi.cdef("extern bool safety_rx_checks_invalid; extern bool heartbeat_engaged;")
    old = os.environ.get("LIONDRIVER_REFERENCE")
    os.environ["LIONDRIVER_REFERENCE"] = "1"
    try:
      path = libsafety_py._build_libsafety(release=True)
    finally:
      if old is None:
        del os.environ["LIONDRIVER_REFERENCE"]
      else:
        os.environ["LIONDRIVER_REFERENCE"] = old
    libsafety_py.load(path)
    _lib = libsafety_py.libsafety
  return _lib


class SimulatedPanda:
  def __init__(self, safety_model: int, safety_param: int, clock=time.monotonic):
    self.lib = load_libsafety()
    self.clock = clock
    self.safety_model = int(getattr(safety_model, "raw", safety_model))  # capnp enum or int
    self.safety_param = int(safety_param)
    self.tx_blocked = 0
    self.rx_invalid = 0
    self._set_timer()
    ret = self.lib.set_safety_hooks(self.safety_model, self.safety_param)
    assert ret == 0, f"set_safety_hooks({self.safety_model}, {self.safety_param}) failed"
    self.lib.init_tests()

  def _set_timer(self):
    self.lib.set_timer(int(self.clock() * 1e6) & 0xFFFFFFFF)

  def rx(self, addr: int, dat: bytes, bus: int) -> bool:
    self._set_timer()
    ok = self.lib.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, dat))
    if not ok:
      self.rx_invalid += 1
    return ok

  def tx(self, addr: int, dat: bytes, bus: int) -> bool:
    self._set_timer()
    ok = self.lib.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, dat))
    if not ok:
      self.tx_blocked += 1
    return ok

  def tick(self, heartbeat_engaged: bool):
    self.lib.set_heartbeat_engaged(heartbeat_engaged)
    self._set_timer()
    self.lib.safety_tick()

  @property
  def controls_allowed(self) -> bool:
    return bool(self.lib.get_controls_allowed())

  @property
  def rx_checks_invalid(self) -> bool:
    return bool(self.lib.safety_rx_checks_invalid)

  @property
  def eps_fault(self) -> bool:
    return bool(self.lib.get_safety_eps_fault())

  @property
  def tx_rate_exceeded(self) -> bool:
    return bool(self.lib.get_safety_tx_rate_exceeded())
