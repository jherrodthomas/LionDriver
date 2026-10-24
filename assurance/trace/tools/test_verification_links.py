#!/usr/bin/env python3
"""Tests for verification_links.py: reading WP-W-06 §4.1, resolving inherited test methods, and the generated file.

Run from the repository root:  python3 -m unittest discover -s assurance/trace/tools -p 'test_*.py' -v
Standard library only. The tests that read test sources need opendbc_repo and panda and are skipped without them.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verification_links as vl


class TestParsing(unittest.TestCase):
  def test_methods_of(self):
    self.assertEqual(vl.methods_of("`MotorTorqueSteeringSafetyTest::test_torque_absolute_limits` (`common.py:550`)"),
                     ["test_torque_absolute_limits"])
    # every suffix extends the stem of the last full name, not the previous expansion
    self.assertEqual(vl.methods_of("`test_steer_req_bit_frames`, `_multi_invalid`, `_realtime` (`:333-395`)"),
                     ["test_steer_req_bit_frames", "test_steer_req_bit_multi_invalid", "test_steer_req_bit_realtime"])
    self.assertEqual(vl.methods_of("`SafetyTest`/`CarSafetyTest::test_safety_tick` (`common.py:1208`)"),
                     ["test_safety_tick"])

  def test_requirement_ids(self):
    self.assertEqual(vl.requirement_ids("LionDriver TSR-512/513, SWSR-512/512a/513"),
                     ["TSR-512", "SWSR-512", "TSR-513", "SWSR-512a", "SWSR-513"])
    self.assertEqual(vl.requirement_ids("FSR-07.02 / TSR-705 D-1"), ["FSR-07.02", "TSR-705"])
    self.assertEqual(vl.requirement_ids("TSR-405(c)"), ["TSR-405"])

  def test_merge_keeps_one_entry_per_test(self):
    a = {"test": "f::C::t", "reqs": ["FSR-01.06"], "partial": True, "behaviour": "x"}
    b = {"test": "f::C::t", "reqs": ["FSR-01.06", "TSR-401"], "partial": False, "behaviour": "y"}
    self.assertEqual(vl.merge([a, b]), [{"test": "f::C::t", "reqs": ["FSR-01.06", "TSR-401"], "partial": True,
                                         "behaviour": "x; y"}])


SOURCES = all((vl.REPO / p).exists() for p in (vl.TEST_FILE, vl.PANDA_TESTS))


@unittest.skipUnless(SOURCES, "opendbc_repo or panda is not checked out")
class TestSources(unittest.TestCase):
  def test_links_from_the_work_product(self):
    links = vl.links()
    by = {ln["test"].rsplit("::", 1)[1]: ln for ln in links if ln["test"].startswith(vl.TEST_FILE.as_posix())}
    self.assertEqual(by["test_torque_absolute_limits"]["reqs"], ["FSR-01.01"])
    self.assertEqual(by["test_steer_req_bit_frames"]["reqs"], ["TSR-106"])  # "(TSR-106)"
    self.assertTrue(by["test_rx_hook"]["partial"])
    self.assertNotIn("test_diagnostics", by)  # its row names no requirement
    self.assertEqual(by["test_eps_fault_blocks_lka"]["reqs"], ["FSR-02.01", "TSR-110"])  # §4.9
    self.assertTrue(any(m.startswith("test_tx_rate_") for m in by))  # `test_tx_rate_*` expanded
    self.assertEqual(len({ln["test"] for ln in links}), len(links))  # one entry per test
    panda = [ln for ln in links if ln["test"].startswith("panda/tests/heartbeat_monitor/")]
    self.assertTrue(panda)
    self.assertEqual(panda[0]["reqs"], ["TSR-407", "SWSR-407"])  # from the suite's module docstring

  def test_generated_file_is_current(self):
    self.assertEqual(vl.OUT.read_text(encoding="utf-8"), vl.render(vl.links()))

  def test_inherited_methods_resolve(self):
    have = vl.test_methods(vl.REPO, vl.TEST_FILE, "TestToyotaSafetyTorque")
    self.assertIn("test_rx_hook", have)                   # TestToyotaSafetyBase (test_toyota.py)
    self.assertIn("test_torque_absolute_limits", have)    # MotorTorqueSteeringSafetyTest (common.py)
    self.assertIn("test_safety_tick", have)               # SafetyTest via CarSafetyTest (common.py)
    self.assertNotIn("test_angle_cmd_when_enabled", have)  # AngleSteeringSafetyTest is not a base

  def test_every_linked_test_exists(self):
    self.assertEqual(vl.problems(), [])


if __name__ == "__main__":
  unittest.main()
