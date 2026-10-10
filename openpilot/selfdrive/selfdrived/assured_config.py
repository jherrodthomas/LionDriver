"""
LionDriver assured configuration (CA-008; FI-2026-001 RC-05, HZ-005).

The safety analyses (CA-001, CA-002, CA-004, CA-011) only cover one configuration:
the reference vehicle, LionDriver software, and the settings below. A drive in any
other configuration is outside the assured scope. That is allowed, but it must be
identifiable afterwards. This module states the configuration and checks against it,
and gives each configuration an identity hash for logs.

Changing what counts as assured needs an impact analysis (PROCESS §5.7).
"""
import hashlib
import json
from dataclasses import dataclass

from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log

# reference vehicle (README "Initial Reference Platform")
ASSURED_PLATFORMS = frozenset({TOYOTA.TOYOTA_COROLLA_TSS2})

# param: (assured value, why other values are outside the assured scope)
ASSURED_PARAMS: dict[str, tuple[bool | int, str]] = {
  "LongitudinalPersonality": (log.LongitudinalPersonality.relaxed, "CA-011 relaxed following distance"),
  "ExperimentalMode": (False, "end-to-end longitudinal is not covered by the CA-002 / CA-004 analyses"),
  "AlphaLongitudinalEnabled": (False, "CA-001: alpha longitudinal may disable stock AEB"),
  "JoystickDebugMode": (False, "debug control mode"),
  "LongitudinalManeuverMode": (False, "debug maneuver mode"),
  "LateralManeuverMode": (False, "debug maneuver mode"),
}

ASSURED_ORIGIN = "jherrodthomas/liondriver"


@dataclass(frozen=True)
class AssuredConfigStatus:
  in_scope: bool
  deviations: tuple[str, ...]
  config_hash: str

  def to_dict(self) -> dict:
    return {"in_scope": self.in_scope, "deviations": list(self.deviations), "config_hash": self.config_hash}


def read_params(params) -> dict[str, bool | int]:
  values = {}
  for key, (assured, _) in ASSURED_PARAMS.items():
    value = params.get(key, return_default=True)
    values[key] = bool(value) if isinstance(assured, bool) else value
  return values


def evaluate(car_fingerprint: str, param_values: dict[str, bool | int], git_commit: str, git_origin: str,
             is_dirty: bool) -> AssuredConfigStatus:
  deviations = []
  if car_fingerprint not in ASSURED_PLATFORMS:
    deviations.append(f"platform {car_fingerprint} is not an assured platform")
  for key, (assured, reason) in ASSURED_PARAMS.items():
    if param_values.get(key) != assured:
      deviations.append(f"{key}={param_values.get(key)}: {reason}")
  if ASSURED_ORIGIN not in git_origin.lower():
    deviations.append(f"software origin {git_origin!r} is not LionDriver")
  if is_dirty:
    deviations.append("software has uncommitted local changes")

  identity = {
    "platform": car_fingerprint,
    "params": param_values,
    "git_commit": git_commit,
    "git_origin": git_origin,
    "is_dirty": is_dirty,
  }
  config_hash = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
  return AssuredConfigStatus(not deviations, tuple(deviations), config_hash)
