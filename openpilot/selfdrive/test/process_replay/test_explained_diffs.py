import unittest

from openpilot.cereal import log
from openpilot.selfdrive.test.process_replay.compare_logs import compare_logs
from openpilot.selfdrive.test.process_replay.test_processes import EXPLAINED_DIFFS, drop_sendcan_addresses

# LionDriver: the process-replay exclusions for explained diffs stay as narrow as their entries say

TESLA_CARD = ("aebd8f1d4ea16066|000002d8--5850d3ea5c--2", "card")
TOYOTA_DMONITORINGD = ("regen218A4DCFAA1|2025-04-08--22-57-51--0", "dmonitoringd")
HONDA_CONTROLSD = ("regenB328FF8BA0A|2025-04-08--22-57-45--0", "controlsd")


def sendcan(*frames):
  msg = log.Event.new_message()
  cans = msg.init("sendcan", len(frames))
  for i, (address, dat) in enumerate(frames):
    cans[i].address = address
    cans[i].dat = dat
  return msg.as_reader()


def car_params(long_control, safety_param):
  msg = log.Event.new_message()
  msg.init("carParams")
  msg.carParams.openpilotLongitudinalControl = long_control
  msg.carParams.init("safetyConfigs", 1)
  msg.carParams.safetyConfigs[0].safetyParam = safety_param
  msg.carParams.steerRatio = 15.
  return msg.as_reader()


class TestExplainedDiffs(unittest.TestCase):
  def test_entries_are_scoped(self):
    for (segment, proc), entry in EXPLAINED_DIFFS.items():
      assert "|" in segment and proc, (segment, proc)
      assert set(entry) <= {"fields", "sendcan_addresses"}

  def test_ca001_tesla_diff_is_explained(self):
    entry = EXPLAINED_DIFFS[TESLA_CARD]
    ref = [car_params(True, 1), sendcan((0x2B9, b"\x01"), (0x488, b"\x02")), sendcan((0x2B9, b"\x03"))]
    new = [car_params(False, 0), sendcan((0x488, b"\x02")), sendcan()]

    self.assertTrue(compare_logs(ref, new))
    ref, new = (drop_sendcan_addresses(m, entry["sendcan_addresses"]) for m in (ref, new))
    self.assertEqual(compare_logs(ref, new, entry["fields"]), [])

  def test_other_frames_and_fields_still_compared(self):
    entry = EXPLAINED_DIFFS[TESLA_CARD]
    # steering frame 0x488 changed: still a diff
    ref = drop_sendcan_addresses([sendcan((0x2B9, b"\x01"), (0x488, b"\x02"))], entry["sendcan_addresses"])
    new = drop_sendcan_addresses([sendcan((0x488, b"\x09"))], entry["sendcan_addresses"])
    self.assertTrue(compare_logs(ref, new, entry["fields"]))

    # a carParams field outside the entry: still a diff
    ref, new = [car_params(True, 1)], [car_params(False, 0)]
    new_builder = new[0].as_builder()
    new_builder.carParams.steerRatio = 16.
    self.assertTrue(compare_logs(ref, [new_builder.as_reader()], entry["fields"]))

  def test_tsr634_wheeltouch_awareness_diff_is_explained(self):
    entry = EXPLAINED_DIFFS[TOYOTA_DMONITORINGD]

    def dm_state(awareness_percent, alert_level=log.DriverMonitoringState.AlertLevel.none):
      msg = log.Event.new_message()
      msg.init("driverMonitoringState")
      msg.driverMonitoringState.wheeltouchPolicyState.awarenessPercent = awareness_percent
      msg.driverMonitoringState.alertLevel = alert_level
      return msg.as_reader()

    self.assertTrue(compare_logs([dm_state(78)], [dm_state(77)]))
    self.assertEqual(compare_logs([dm_state(78)], [dm_state(77)], entry["fields"]), [])
    # the alert level is still compared
    self.assertTrue(compare_logs([dm_state(78)], [dm_state(77, log.DriverMonitoringState.AlertLevel.one)], entry["fields"]))

  def test_swf042_integrator_reset_diff_is_explained(self):
    entry = EXPLAINED_DIFFS[HONDA_CONTROLSD]

    def controls(i, torque, lat_active=True):
      cs = log.Event.new_message()
      cs.init("controlsState")
      cs.controlsState.lateralControlState.init("pidState")
      cs.controlsState.lateralControlState.pidState.i = i
      cs.controlsState.lateralControlState.pidState.output = torque
      cc = log.Event.new_message()
      cc.init("carControl")
      cc.carControl.actuators.torque = torque
      cc.carControl.latActive = lat_active
      return [cs.as_reader(), cc.as_reader()]

    self.assertTrue(compare_logs(controls(-0.066, -0.36), controls(0., -0.30)))
    self.assertEqual(compare_logs(controls(-0.066, -0.36), controls(0., -0.30), entry["fields"]), [])
    # whether lateral control is active is still compared
    self.assertTrue(compare_logs(controls(-0.066, -0.36), controls(0., -0.30, lat_active=False), entry["fields"]))
