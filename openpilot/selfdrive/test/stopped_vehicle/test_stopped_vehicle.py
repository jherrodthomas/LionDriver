import unittest

from openpilot.common.realtime import DT_MDL
from openpilot.common.parameterized import parameterized
from openpilot.selfdrive.test.stopped_vehicle import scenarios as S
from openpilot.selfdrive.test.stopped_vehicle.harness import run

# CA-002 stopped / slow in-lane vehicle scenario suite (FI-2026-001)


def name(scenario):
  return scenario.name


class TestStoppedVehicle(unittest.TestCase):
  @parameterized.expand(S.VISIBLE_FROM_RANGE + S.SLOW_VEHICLE, ids=name)
  def test_ac1_visible_from_range(self, scenario):
    """AC-1: confirmed at 1.2x the required stopping distance, openpilot avoids the collision."""
    result = run(scenario)
    self.assertIsNotNone(result.first_detection_gap)
    required = S.required_stopping_distance(scenario.v_ego, scenario.v_target)
    # detection is sampled every frame, so it can land up to one frame of closing inside the range
    frame_travel = (scenario.v_ego - scenario.v_target) * DT_MDL
    self.assertGreaterEqual(result.first_detection_gap, S.DETECTION_MARGIN * required - frame_travel)
    self.assertFalse(result.collided, f"impact at {result.impact_speed * 3.6:.1f} km/h")

  @parameterized.expand(S.VISIBLE_FROM_RANGE + S.SLOW_VEHICLE, ids=name)
  def test_braking_limit_reached(self, scenario):
    """The planner uses the full braking authority: confirmed at exactly the required distance, it still stops."""
    required = S.required_stopping_distance(scenario.v_ego, scenario.v_target)
    result = run(scenario.with_vision_range(required))
    self.assertFalse(result.collided, f"impact at {result.impact_speed * 3.6:.1f} km/h")

  @parameterized.expand(S.CUT_OUT, ids=name)
  def test_ac2_cut_out(self, scenario):
    """AC-2: after a cut-out reveal, avoid what is physically avoidable and warn in time for the rest."""
    result = run(scenario)
    reveal_gap = scenario.initial_gap - scenario.v_ego * scenario.reveal_time
    if reveal_gap >= S.required_stopping_distance(scenario.v_ego):
      self.assertFalse(result.collided, f"avoidable collision, impact at {result.impact_speed * 3.6:.1f} km/h")
    if result.collided:
      self.assertIsNotNone(result.fcw_ttc, "collision without FCW")
      if reveal_gap / scenario.v_ego >= S.FCW_REVEAL_TTC:
        self.assertGreaterEqual(result.fcw_ttc or 0., S.FCW_MIN_TTC)

  @unittest.expectedFailure
  def test_radar_only_stationary_target(self):
    """Known gap (FI-2026-001 RC-02, FTA B3): a stationary target seen only by radar is ignored above 4 m/s.

    Expected to fail until a corrective action makes radar-only stationary targets usable.
    When it starts passing, remove expectedFailure and update the CA-002 record.
    """
    for scenario in S.RADAR_ONLY:
      with self.subTest(scenario=scenario.name):
        self.assertFalse(run(scenario).collided)

  def test_no_target_holds_speed(self):
    """Harness check: with nothing ahead, the ego holds its set speed."""
    scenario = S.Scenario("no target", 25., initial_gap=10_000., vision_range=0., radar_range=0., duration=10.)
    result = run(scenario)
    self.assertFalse(result.collided)
    self.assertIsNone(result.first_detection_gap)
    self.assertGreater(result.peak_decel, -0.5)
