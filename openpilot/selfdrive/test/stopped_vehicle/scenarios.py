"""
CA-002 stopped / slow in-lane vehicle scenarios (FI-2026-001, TC-01, TC-02, TC-05).

Distances are bumper-to-bumper gaps in meters, speeds in m/s.
"""
from dataclasses import dataclass, replace

from opendbc.car.common.conversions import Conversions as CV

# openpilot braking authority (opendbc ACCEL_MIN, Toyota panda limit)
BRAKE_LIMIT = 3.5
# end-to-end latency assumed in the RCA stopping-distance table (RCA §3.1)
LATENCY = 0.5
# CA-002 AC-1 margin on the required detection range
DETECTION_MARGIN = 1.2
# CA-002 AC-2 minimum FCW time-to-collision
FCW_MIN_TTC = 2.0
# AC-2 only applies when the reveal leaves this much time to collision, which allows
# for lead confirmation before an FCW can be expected
FCW_REVEAL_TTC = 2.5

SPEEDS_KPH = (40, 60, 80, 100, 120)
CUT_OUT_REVEAL_DISTANCES = (120., 80., 50.)


def required_stopping_distance(v_ego: float, v_target: float = 0.) -> float:
  """Gap needed to avoid a collision at the openpilot braking limit (RCA §3.1)."""
  v_closing = v_ego - v_target
  return v_closing * LATENCY + v_closing ** 2 / (2 * BRAKE_LIMIT)


@dataclass(frozen=True)
class Scenario:
  name: str
  v_ego: float
  v_target: float = 0.
  initial_gap: float = 400.
  # vision model confirms the target (lead prob > 0.5) once the gap is at or below this
  vision_range: float = 200.
  # radar reports the target once the gap is at or below this; 0 disables radar
  radar_range: float = 175.
  # time the target becomes observable, e.g. when a lead vehicle cuts out
  reveal_time: float = 0.
  lateral_offset: float = 0.
  duration: float = 40.

  def with_vision_range(self, vision_range: float) -> 'Scenario':
    return replace(self, vision_range=vision_range, name=f"{self.name}, vision {vision_range:.0f} m")


def visible_from_range(speed_kph: int, slow: bool = False) -> Scenario:
  """TC-01 / TC-05: target in lane, observable from the start, confirmed at AC-1 range."""
  v_ego = speed_kph * CV.KPH_TO_MS
  v_target = 0.2 * v_ego if slow else 0.
  vision_range = DETECTION_MARGIN * required_stopping_distance(v_ego, v_target)
  kind = "slow vehicle" if slow else "stopped vehicle"
  return Scenario(f"{kind} at {speed_kph} km/h, vision {vision_range:.0f} m", v_ego, v_target,
                  initial_gap=vision_range + 2 * v_ego, vision_range=vision_range)


def cut_out(speed_kph: int, reveal_gap: float) -> Scenario:
  """TC-02: a lead vehicle cuts out and reveals a stopped vehicle at reveal_gap."""
  v_ego = speed_kph * CV.KPH_TO_MS
  reveal_time = 2.
  return Scenario(f"cut-out at {speed_kph} km/h, revealed at {reveal_gap:.0f} m", v_ego,
                  initial_gap=reveal_gap + v_ego * reveal_time, reveal_time=reveal_time)


def radar_only(speed_kph: int) -> Scenario:
  """Radar sees the stopped vehicle but vision never confirms it (FTA B3)."""
  v_ego = speed_kph * CV.KPH_TO_MS
  return Scenario(f"radar only at {speed_kph} km/h", v_ego, vision_range=0.)


VISIBLE_FROM_RANGE = [visible_from_range(s) for s in SPEEDS_KPH]
SLOW_VEHICLE = [visible_from_range(s, slow=True) for s in SPEEDS_KPH]
CUT_OUT = [cut_out(s, d) for s in SPEEDS_KPH for d in CUT_OUT_REVEAL_DISTANCES]
RADAR_ONLY = [radar_only(s) for s in (40, 80, 120)]
