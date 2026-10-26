from types import SimpleNamespace

from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.car.vehicle_dtc import ACTIVE, FAILED, OK, DtcStatus, EcuDtcResult
from openpilot.selfdrive.selfdrived import assured_config, selfdrived
from openpilot.selfdrive.selfdrived.events import ET, EVENTS, Events

# TSR-629, SWSR-629d (register DQ-056 A, DQ-132 A): the start-up fault-code read refuses entry on the reference
# platform. Not verified on the reference vehicle (WP-S-09 VS-SQ-20)

EventName = log.OnroadEvent.EventName
REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2
FLOOR = assured_config.HIGHWAY_SPEED_FLOOR
DTC_EVENTS = (EventName.epsFaultCode, EventName.brakeFaultCode, EventName.faultCodeReadFailed)


def status(eps=OK, abs_=OK, read=True):
  return DtcStatus(read, "test", (EcuDtcResult("eps", eps), EcuDtcResult("abs", abs_)))


def selfdrive(dtc_status, platform):
  """Just the state the entry checks use, in the assured settings"""
  assured = {key: value for key, (value, _) in assured_config.ASSURED_PARAMS.items()}
  return SimpleNamespace(reference_platform=platform in assured_config.ASSURED_PLATFORMS, events=Events(),
                         assured_config=assured_config.evaluate(platform, assured, "abc123", "jherrodthomas/liondriver", False),
                         dtc_entry_events=selfdrived.dtc_entry_events(dtc_status))


def entry_events(dtc_status, platform=REFERENCE):
  sd = selfdrive(dtc_status, platform)
  selfdrived.SelfdriveD.add_reference_entry_events(sd, SimpleNamespace(vEgo=FLOOR))
  return sd.events


class TestFaultCodeEntry(OpenpilotTestCase):
  def test_no_active_code_allows(self):
    events = entry_events(status())
    self.assertEqual(events.names, [])

  def test_active_eps_code_refuses_entry(self):
    events = entry_events(status(eps=ACTIVE))
    self.assertEqual(events.names, [EventName.epsFaultCode])
    self.assertTrue(events.contains(ET.NO_ENTRY))

  def test_active_brake_code_refuses_entry(self):
    self.assertEqual(entry_events(status(abs_=ACTIVE)).names, [EventName.brakeFaultCode])

  def test_both_named(self):
    self.assertEqual(entry_events(status(eps=ACTIVE, abs_=ACTIVE)).names, [EventName.epsFaultCode, EventName.brakeFaultCode])

  def test_failed_read_refuses_entry(self):
    for s in (status(eps=FAILED), status(abs_=FAILED), status(read=False), DtcStatus.from_dict(None)):
      events = entry_events(s)
      self.assertEqual(events.names, [EventName.faultCodeReadFailed], s)
      self.assertTrue(events.contains(ET.NO_ENTRY))

  def test_active_and_failed(self):
    self.assertEqual(entry_events(status(eps=ACTIVE, abs_=FAILED)).names,
                     [EventName.epsFaultCode, EventName.faultCodeReadFailed])

  def test_entry_only(self):
    events = entry_events(status(eps=ACTIVE, abs_=FAILED))
    self.assertFalse(events.contains(ET.SOFT_DISABLE) or events.contains(ET.IMMEDIATE_DISABLE))
    for name in DTC_EVENTS:
      self.assertEqual(set(EVENTS[name]), {ET.NO_ENTRY})

  def test_other_platforms_unchanged(self):
    self.assertEqual(entry_events(DtcStatus.from_dict(None), platform=TOYOTA.TOYOTA_RAV4_TSS2_2022).names, [])

  def test_alert_names_the_system(self):
    def text(name):
      a = EVENTS[name][ET.NO_ENTRY]
      return a.alert_text_1 + a.alert_text_2
    assert "EPS" in text(EventName.epsFaultCode)
    assert "ABS/VSC" in text(EventName.brakeFaultCode)
    assert "Fault Code" in text(EventName.faultCodeReadFailed)
