from unittest import mock

from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.parameterized import parameterized
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived import selfdrived
from openpilot.selfdrive.test.stopped_vehicle import scenarios as S
from openpilot.selfdrive.test.stopped_vehicle.harness import run

# CA-011 verification: relaxed following distance by default (FI-2026-001, HZ-008)

RELAXED = log.LongitudinalPersonality.relaxed


class TestFollowingDistance(OpenpilotTestCase):
  def test_default_is_relaxed(self):
    self.assertEqual(Params().get("LongitudinalPersonality", return_default=True), RELAXED)
    self.assertEqual(selfdrived.ASSURED_PERSONALITY, RELAXED)

  def test_change_outside_assured_configuration_is_logged(self):
    sd = mock.Mock(personality=RELAXED)
    with mock.patch.object(selfdrived.cloudlog, "event") as event:
      selfdrived.SelfdriveD.set_personality(sd, RELAXED)
      event.assert_not_called()
      selfdrived.SelfdriveD.set_personality(sd, log.LongitudinalPersonality.aggressive)
      event.assert_called_once()
      # logged on change only, not on every params poll
      selfdrived.SelfdriveD.set_personality(sd, log.LongitudinalPersonality.aggressive)
      event.assert_called_once()
    self.assertEqual(sd.personality, log.LongitudinalPersonality.aggressive)

  @parameterized.expand([(kph, decel) for kph in (60, 100) for decel in (2., 3., 4.)])
  def test_acceptance_lead_braking(self, kph, decel):
    """CA-011 AC: at the relaxed distance, a lead braking at up to 4 m/s² from up to 100 km/h is not hit."""
    result = run(S.lead_braking(kph, decel, RELAXED))
    self.assertFalse(result.collided, f"impact at {result.impact_speed * 3.6:.1f} km/h")
