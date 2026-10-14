"""
LionDriver stock AEB interlock (LD-FSR-001, corrective action CA-001).

LD-FSR-001: In any LionDriver assured configuration, openpilot shall not disable,
suppress or override the stock OEM AEB/PCS function.

On several platforms, alpha openpilot longitudinal control takes over by silencing
the stock radar/ADAS ECU. On radar-ACC Toyotas, for example, the car port disables
the radar ECU over UDS and reports PCS as off. That removes the vehicle's independent
last-resort braking barrier (FI-2026-001, RC-01, HZ-002). No platform has evidence
that alpha longitudinal preserves stock AEB, so it is never permitted on a vehicle.
Permitting it on a platform needs an approved safety case (impact analysis plus a
vehicle test showing stock AEB still intervenes) and a change to this module.

See docs/safety/field-monitoring/cases/FI-2026-001-nhtsa-pe26007/.
"""
import os

from opendbc.car.structs import car
from openpilot.common.swaglog import cloudlog


def is_simulation() -> bool:
  # Simulator only: SIMULATION selects the sim, and NOBOARD stops pandad, so there is
  # no path to a vehicle CAN bus.
  return "SIMULATION" in os.environ and "NOBOARD" in os.environ


def alpha_long_permitted() -> bool:
  """Whether alpha longitudinal may be offered at all (e.g. as a settings toggle)."""
  return is_simulation()


def alpha_long_allowed(requested: bool) -> bool:
  """Whether the alpha longitudinal request may be passed to the car interface."""
  if not requested:
    return False
  if alpha_long_permitted():
    return True
  cloudlog.warning("LD-FSR-001: alpha longitudinal request refused, it may disable stock AEB")
  return False


def stock_aeb_preserved(CP: car.CarParams) -> bool:
  """Postcondition check on the CarParams returned by the car interface.

  Every car port only enables openpilot longitudinal on an alpha-capable platform
  when alpha longitudinal was requested, so both being set means the stock radar/ADAS
  ECU may be disabled.
  """
  if is_simulation():
    return True
  return not (CP.alphaLongitudinalAvailable and CP.openpilotLongitudinalControl)
