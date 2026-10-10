from types import SimpleNamespace
from unittest import mock

from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.parameterized import parameterized
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived import assured_config, selfdrived

# CA-008 verification (FI-2026-001 RC-05, HZ-005)

REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2
ORIGIN = "https://github.com/jherrodthomas/LionDriver.git"
ASSURED_VALUES = {key: assured for key, (assured, _) in assured_config.ASSURED_PARAMS.items()}


def evaluate(platform=REFERENCE, params=None, commit="abc123", origin=ORIGIN, dirty=False):
  return assured_config.evaluate(platform, {**ASSURED_VALUES, **(params or {})}, commit, origin, dirty)


class TestAssuredConfig(OpenpilotTestCase):
  def test_reference_configuration_in_scope(self):
    status = evaluate()
    self.assertTrue(status.in_scope)
    self.assertEqual(status.deviations, ())

  @parameterized.expand([
    ("LongitudinalPersonality", log.LongitudinalPersonality.standard),
    ("ExperimentalMode", True),
    ("AlphaLongitudinalEnabled", True),
    ("JoystickDebugMode", True),
    ("LongitudinalManeuverMode", True),
    ("LateralManeuverMode", True),
  ])
  def test_param_deviation(self, key, value):
    status = evaluate(params={key: value})
    self.assertFalse(status.in_scope)
    self.assertEqual(len(status.deviations), 1)
    assert key in status.deviations[0]

  def test_platform_deviation(self):
    status = evaluate(platform=TOYOTA.TOYOTA_RAV4_TSS2_2022)
    self.assertFalse(status.in_scope)
    assert "platform" in status.deviations[0]

  def test_software_deviations(self):
    self.assertFalse(evaluate(origin="https://github.com/FrogAi/FrogPilot.git").in_scope)
    self.assertFalse(evaluate(dirty=True).in_scope)
    # the origin check ignores case and URL form
    self.assertTrue(evaluate(origin="git@github.com:JherrodThomas/LionDriver").in_scope)

  def test_hash_identifies_configuration(self):
    self.assertEqual(evaluate().config_hash, evaluate().config_hash)
    self.assertNotEqual(evaluate().config_hash, evaluate(commit="def456").config_hash)
    self.assertNotEqual(evaluate().config_hash, evaluate(params={"ExperimentalMode": True}).config_hash)

  def test_fresh_device_params(self):
    """A fresh device matches the assured params except ExperimentalMode, which upstream defaults on.

    Known deviation (CA-008 finding): the CA-002 / CA-004 analyses ran without experimental mode.
    Update this test if the default or the assured configuration changes.
    """
    values = assured_config.read_params(Params())
    self.assertEqual(values, {**ASSURED_VALUES, "ExperimentalMode": True})
    status = evaluate(params=values)
    self.assertEqual(len(status.deviations), 1)
    assert "ExperimentalMode" in status.deviations[0]

  def test_selfdrived_logs_and_stores_on_change(self):
    params = Params()
    params.put_bool("ExperimentalMode", False, block=True)
    metadata = SimpleNamespace(openpilot=SimpleNamespace(git_commit="abc123", git_origin=ORIGIN, is_dirty=False))
    sd = mock.Mock(params=params, CP=SimpleNamespace(carFingerprint=REFERENCE), build_metadata=metadata, assured_config=None)

    with mock.patch.object(selfdrived.cloudlog, "event") as event:
      selfdrived.SelfdriveD.update_assured_config(sd)
      selfdrived.SelfdriveD.update_assured_config(sd)
      event.assert_called_once()
      self.assertTrue(params.get("AssuredConfiguration")["in_scope"])

      params.put_bool("ExperimentalMode", True, block=True)
      selfdrived.SelfdriveD.update_assured_config(sd)
      self.assertEqual(event.call_count, 2)
      stored = params.get("AssuredConfiguration")
      self.assertFalse(stored["in_scope"])
      self.assertEqual(stored["config_hash"], sd.assured_config.config_hash)
