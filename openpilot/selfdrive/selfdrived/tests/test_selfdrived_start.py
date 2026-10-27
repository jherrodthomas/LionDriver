import os
from unittest import mock

from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.car import vehicle_dtc
from openpilot.selfdrive.car.vehicle_dtc import ACTIVE, OK, DtcStatus, EcuDtcResult
from openpilot.selfdrive.selfdrived import selfdrived

# What SelfdriveD sets up at start for the reference entry checks (DQ-221, CA-008; TSR-629, DQ-132): whether it is on
# the reference platform, and the no-entry events from card's start-up fault-code read. The checks themselves are
# tested in test_assured_config.py and test_vehicle_dtc_entry.py; this runs the real constructor (SWF-067.C1,
# SWF-091.C2)

EventName = log.OnroadEvent.EventName
REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2
OTHER = TOYOTA.TOYOTA_RAV4_TSS2_2022


def start(platform=REFERENCE, dtc=None):
  params = Params()
  if dtc is None:
    params.remove(vehicle_dtc.PARAM)
  else:
    params.put(vehicle_dtc.PARAM, dtc.to_dict(), block=True)
  CP = car.CarParams.new_message()
  CP.carFingerprint = platform
  return selfdrived.SelfdriveD(CP=CP.as_reader())


def status(eps=OK, abs_=OK, read=True):
  return DtcStatus(read, "test", (EcuDtcResult("eps", eps), EcuDtcResult("abs", abs_)))


class TestSelfdrivedStart(OpenpilotTestCase):
  def setUp(self):
    super().setUp()
    patcher = mock.patch.dict(os.environ)
    patcher.start()
    self.addCleanup(patcher.stop)
    for name in ("SIMULATION", "NOBOARD"):
      os.environ.pop(name, None)

  def test_reference_platform(self):
    self.assertTrue(start(REFERENCE, status()).reference_platform)
    self.assertFalse(start(OTHER, status()).reference_platform)

  def test_clean_read_allows_entry(self):
    self.assertEqual(start(dtc=status()).dtc_entry_events, [])

  def test_active_codes_refuse_entry(self):
    self.assertEqual(start(dtc=status(eps=ACTIVE)).dtc_entry_events, [EventName.epsFaultCode])
    self.assertEqual(start(dtc=status(abs_=ACTIVE)).dtc_entry_events, [EventName.brakeFaultCode])

  def test_missing_record_counts_as_not_read(self):
    self.assertEqual(start(dtc=None).dtc_entry_events, [EventName.faultCodeReadFailed])

  def test_record_read_at_start(self):
    sd = start(dtc=status(eps=ACTIVE))
    Params().put(vehicle_dtc.PARAM, status().to_dict(), block=True)
    # a record written after start does not change the decision for this drive
    self.assertEqual(sd.dtc_entry_events, [EventName.epsFaultCode])

  def test_replay_and_simulator_not_gated(self):
    with mock.patch.object(selfdrived, "REPLAY", True):
      self.assertEqual(start(dtc=status(eps=ACTIVE)).dtc_entry_events, [])
    os.environ.update(SIMULATION="1", NOBOARD="1")
    self.assertEqual(start(dtc=status(eps=ACTIVE)).dtc_entry_events, [])

  def test_simulation_alone_still_gated(self):
    # SIMULATION without NOBOARD still has a vehicle CAN bus, so the read still decides
    os.environ["SIMULATION"] = "1"
    self.assertEqual(start(dtc=status(eps=ACTIVE)).dtc_entry_events, [EventName.epsFaultCode])
