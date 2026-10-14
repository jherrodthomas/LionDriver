import unittest

from openpilot.cereal import log
from openpilot.selfdrive.test.process_replay.compare_logs import compare_logs
from openpilot.selfdrive.test.process_replay.test_processes import EXPLAINED_DIFFS, drop_sendcan_addresses

# LionDriver: the process-replay exclusions for explained diffs stay as narrow as their entries say

TESLA_CARD = ("aebd8f1d4ea16066|000002d8--5850d3ea5c--2", "card")


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
