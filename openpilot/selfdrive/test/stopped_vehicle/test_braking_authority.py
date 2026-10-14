import unittest

from openpilot.common.parameterized import parameterized
from openpilot.selfdrive.test.stopped_vehicle import scenarios as S
from openpilot.selfdrive.test.stopped_vehicle.emergency_brake import EmergencyBrakeConfig
from openpilot.selfdrive.test.stopped_vehicle.harness import run

# CA-004 braking-authority study: checks on the option (b) prototype and the findings it rests on

EMERGENCY = EmergencyBrakeConfig(decel=8.)
ORDINARY_LEAD_BRAKING = [S.lead_braking(kph, d) for kph in (60, 100, 120) for d in (2., 3.)]


def name(scenario):
  return scenario.name


def stopping_distance(v, decel):
  return v * S.LATENCY + v ** 2 / (2 * decel)


class TestEmergencyBrakePrototype(unittest.TestCase):
  @parameterized.expand(S.CUT_OUT, ids=name)
  def test_avoids_what_its_authority_allows(self, scenario):
    """At -8 m/s², a cut-out revealed beyond the -8 m/s² stopping distance is avoided."""
    reveal_gap = scenario.initial_gap - scenario.v_ego * scenario.reveal_time
    result = run(scenario, EMERGENCY)
    if reveal_gap >= stopping_distance(scenario.v_ego, EMERGENCY.decel):
      self.assertFalse(result.collided, f"impact at {result.impact_speed * 3.6:.1f} km/h")
    baseline = run(scenario)
    self.assertLessEqual(result.impact_speed, baseline.impact_speed)

  @parameterized.expand(S.VISIBLE_FROM_RANGE + S.SLOW_VEHICLE + ORDINARY_LEAD_BRAKING, ids=name)
  def test_no_trigger_when_normal_authority_suffices(self, scenario):
    """Nuisance check: it stays off when -3.5 m/s² is enough (HZ-006)."""
    result = run(scenario, EMERGENCY)
    self.assertFalse(result.emergency_triggered)
    self.assertFalse(result.collided)

  def test_no_trigger_without_fused_confirmation(self):
    """By design it needs vision and radar together, so a radar-only target does not trigger it."""
    for scenario in S.RADAR_ONLY:
      with self.subTest(scenario=scenario.name):
        self.assertFalse(run(scenario, EMERGENCY).emergency_triggered)

  def test_lead_emergency_stop(self):
    """A lead stopping at 6 m/s² from 100 km/h: current authority collides, the prototype avoids it."""
    scenario = S.lead_braking(100, 6.)
    self.assertTrue(run(scenario).collided)
    result = run(scenario, EMERGENCY)
    self.assertTrue(result.emergency_triggered)
    self.assertFalse(result.collided)


class TestCurrentAuthority(unittest.TestCase):
  @unittest.expectedFailure
  def test_lead_hard_braking_at_highway_speed(self):
    """Known gap (CA-004 finding, HZ-008): at the standard following distance, a lead braking at 4 m/s² or more
    from highway speed is hit, because the lead out-brakes the -3.5 m/s² limit.

    Expected to fail until a corrective action closes it. Then remove expectedFailure and update CA-004.
    """
    for kph in (100, 120):
      for decel in (4., 6.):
        with self.subTest(speed=kph, decel=decel):
          self.assertFalse(run(S.lead_braking(kph, decel)).collided)
