from types import SimpleNamespace

from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived.events import EVENTS, ET, AudibleAlert, EventName, dm_terminal_alert, minimum_risk_maneuver_alert
from openpilot.selfdrive.selfdrived.minimum_risk import MinimumRiskManeuver
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD


class TestMinimumRiskManeuver(OpenpilotTestCase):
  """TSR-633 (DQ-365 A): stop, stay stopped and held, and do not resume until the driver takes over."""

  def test_off_until_the_dm_requests_it(self):
    mrm = MinimumRiskManeuver()
    assert not any(mrm.update(True, False) for _ in range(100))

  def test_stays_latched_when_the_dm_request_drops(self):
    # e.g. dmonitoringd restarts, or its awareness resets: the car must not drive off again
    mrm = MinimumRiskManeuver()
    assert mrm.update(True, True)
    assert all(mrm.update(True, False) for _ in range(6000))   # one minute at 100 Hz, held

  def test_ends_only_when_the_driver_takes_over(self):
    mrm = MinimumRiskManeuver()
    mrm.update(True, True)
    assert not mrm.update(False, False)                         # brake or cancel: the item disengages
    assert not mrm.update(True, False)                          # a new engagement starts clean

  def test_not_set_while_disengaged(self):
    mrm = MinimumRiskManeuver()
    assert not mrm.update(False, True)


class TestManeuverAnnouncement(OpenpilotTestCase):
  """TSR-624: deceleration that traffic does not cause is announced, visually and acoustically, before it starts."""

  @staticmethod
  def _sm(decel_in):
    return {'driverMonitoringState': SimpleNamespace(noResponseDecelIn=decel_in)}

  def test_terminal_alert_counts_down_to_the_stop(self):
    alert = dm_terminal_alert("Driver Distracted")
    CS = car.CarState(vEgo=30.)
    assert alert(None, CS, self._sm(4.2), False, 0, None).alert_text_2 == "Driver Distracted - Car Stops in 5 s"
    assert alert(None, CS, self._sm(0.4), False, 0, None).alert_text_2 == "Driver Distracted - Car Stops in 1 s"
    assert alert(None, CS, self._sm(0.), False, 0, None).alert_text_2 == "Driver Distracted - Car Is Stopping"
    assert alert(None, CS, self._sm(-1.), False, 0, None).alert_text_2 == "Driver Distracted"
    a = alert(None, CS, self._sm(3.), False, 0, None)
    assert a.audible_alert == AudibleAlert.warningImmediate                 # acoustic as well as visual

  def test_maneuver_alert_while_stopping_and_held(self):
    moving = minimum_risk_maneuver_alert(None, car.CarState(vEgo=20.), self._sm(0.), False, 0, None)
    held = minimum_risk_maneuver_alert(None, car.CarState(standstill=True), self._sm(0.), False, 0, None)
    assert moving.alert_text_1 == "TAKE CONTROL: CAR STOPPING"
    assert held.alert_text_1 == "TAKE CONTROL: CAR STOPPED" and held.alert_text_2 == "Held Until You Take Over"
    assert moving.audible_alert == held.audible_alert == AudibleAlert.warningImmediate   # it keeps sounding

  def test_events_wired(self):
    assert EVENTS[EventName.minimumRiskManeuver][ET.PERMANENT] is minimum_risk_maneuver_alert


class TestManeuverAlertInSelfdrived(OpenpilotTestCase):
  """TSR-633, TSR-624: selfdrived raises the maneuver's alert on every frame while latched, with no DM alert"""

  def setUp(self):
    super().setUp()
    CP = car.CarParams.new_message()
    CP.carFingerprint = TOYOTA.TOYOTA_COROLLA_TSS2
    self.sd = SelfdriveD(CP=CP.as_reader())
    self.sd.initialized = True

  def events(self, latched):
    self.sd.mrm.active = latched
    self.sd.update_events(car.CarState.new_message())
    return self.sd.events.names

  def test_raised_while_latched(self):
    for _ in range(3):
      assert EventName.minimumRiskManeuver in self.events(True)

  def test_not_raised_when_not_latched(self):
    assert EventName.minimumRiskManeuver not in self.events(False)
