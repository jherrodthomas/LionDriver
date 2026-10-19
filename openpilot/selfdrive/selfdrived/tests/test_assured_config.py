from types import SimpleNamespace
from unittest import mock

from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.parameterized import parameterized
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived import assured_config, selfdrived
from openpilot.selfdrive.selfdrived.events import ET, EVENTS, Events

# CA-008 verification (FI-2026-001 RC-05, HZ-005); DQ-221 and DQ-280 entry checks

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

  def test_fresh_device_params_are_assured(self):
    """Param defaults put a fresh device in the assured configuration (CA-011, and ExperimentalMode off)."""
    values = assured_config.read_params(Params())
    self.assertEqual(values, ASSURED_VALUES)
    self.assertTrue(evaluate(params=values).in_scope)

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


EventName = log.OnroadEvent.EventName
FLOOR = assured_config.HIGHWAY_SPEED_FLOOR


def selfdrive(platform=REFERENCE, status=None):
  """Just the state the entry checks and the distance button use"""
  return SimpleNamespace(reference_platform=platform in assured_config.ASSURED_PLATFORMS, events=Events(),
                         assured_config=status if status is not None else evaluate(platform=platform),
                         personality=log.LongitudinalPersonality.relaxed, params=mock.Mock(),
                         set_personality=mock.Mock())


def entry_events(sd, v_ego):
  sd.events.clear()
  selfdrived.SelfdriveD.add_reference_entry_events(sd, SimpleNamespace(vEgo=v_ego))
  return sd.events


class TestReferenceEntry(OpenpilotTestCase):
  def test_settings_in_scope_tracks_settings_only(self):
    self.assertTrue(evaluate().settings_in_scope)
    # platform and software deviations are logged but are not settings
    self.assertTrue(evaluate(platform=TOYOTA.TOYOTA_RAV4_TSS2_2022).settings_in_scope)
    self.assertTrue(evaluate(dirty=True).settings_in_scope)
    for key, (assured, _) in assured_config.ASSURED_PARAMS.items():
      other = (not assured) if isinstance(assured, bool) else log.LongitudinalPersonality.standard
      self.assertFalse(evaluate(params={key: other}).settings_in_scope, key)
    self.assertIn("settings_in_scope", evaluate().to_dict())

  def test_reference_platform_in_assured_settings_engages_at_floor(self):
    sd = selfdrive()
    self.assertFalse(entry_events(sd, FLOOR).contains(ET.NO_ENTRY))
    self.assertFalse(entry_events(sd, 30.).contains(ET.NO_ENTRY))

  def test_below_highway_speed_refuses_entry(self):
    sd = selfdrive()
    for v_ego in (0., 10., FLOOR - 0.01):
      events = entry_events(sd, v_ego)
      self.assertEqual(events.names, [EventName.belowHighwaySpeed], v_ego)
      self.assertTrue(events.contains(ET.NO_ENTRY))
      # entry only: an engaged item is not disengaged by it
      self.assertFalse(events.contains(ET.SOFT_DISABLE) or events.contains(ET.IMMEDIATE_DISABLE))

  @parameterized.expand([
    ("LongitudinalPersonality", log.LongitudinalPersonality.standard),
    ("LongitudinalPersonality", log.LongitudinalPersonality.aggressive),
    ("ExperimentalMode", True),
    ("AlphaLongitudinalEnabled", True),
    ("JoystickDebugMode", True),
  ])
  def test_setting_outside_assured_refuses_entry(self, key, value):
    sd = selfdrive(status=evaluate(params={key: value}))
    events = entry_events(sd, 30.)
    self.assertEqual(events.names, [EventName.settingNotAssured])
    self.assertTrue(events.contains(ET.NO_ENTRY))
    self.assertFalse(events.contains(ET.SOFT_DISABLE) or events.contains(ET.IMMEDIATE_DISABLE))

  def test_other_platforms_unchanged(self):
    platform = TOYOTA.TOYOTA_RAV4_TSS2_2022
    sd = selfdrive(platform=platform, status=evaluate(platform=platform, params={"ExperimentalMode": True}))
    self.assertEqual(entry_events(sd, 5.).names, [])

  def test_distance_button_keeps_assured_distance_on_reference(self):
    sd = selfdrive()
    with mock.patch.object(selfdrived.cloudlog, "event") as event:
      selfdrived.SelfdriveD.distance_button_pressed(sd)
    sd.set_personality.assert_not_called()
    sd.params.put.assert_not_called()
    self.assertEqual(sd.events.names, [])
    event.assert_called_once()

  def test_distance_button_unchanged_on_other_platforms(self):
    sd = selfdrive(platform=TOYOTA.TOYOTA_RAV4_TSS2_2022)
    selfdrived.SelfdriveD.distance_button_pressed(sd)
    sd.set_personality.assert_called_once_with((log.LongitudinalPersonality.relaxed - 1) % 3)
    self.assertEqual(sd.events.names, [EventName.personalityChanged])

  def test_alerts(self):
    self.assertIn(ET.NO_ENTRY, EVENTS[EventName.settingNotAssured])
    alert = EVENTS[EventName.belowHighwaySpeed][ET.NO_ENTRY]
    for metric, shown in ((True, "60 km/h"), (False, "37 mph")):
      a = alert(None, None, None, metric, 0, None)
      self.assertIn(shown, a.alert_text_1 + a.alert_text_2)
