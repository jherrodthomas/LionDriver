#!/usr/bin/env python3
"""Tests for verification_links.py: reading WP-W-06 §4.1, resolving inherited test methods, and the generated file.

Run from the repository root:  python3 -m unittest discover -s assurance/trace/tools -p 'test_*.py' -v
Standard library only. The method-existence tests need opendbc_repo and are skipped without it.
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

  def test_links_from_the_work_product(self):
    links = vl.links()
    self.assertTrue(links)
    self.assertTrue(all(ln["test"].startswith(f"{vl.TEST_FILE.as_posix()}::TestToyotaSafetyTorque::") for ln in links))
    by = {ln["test"].rsplit("::", 1)[1]: ln for ln in links}
    self.assertEqual(by["test_torque_absolute_limits"]["reqs"], ["FSR-01.01"])
    self.assertEqual(by["test_steer_req_bit_frames"]["reqs"], ["TSR-106"])  # "(TSR-106)"
    self.assertTrue(by["test_rx_hook"]["partial"])
    self.assertNotIn("test_diagnostics", by)  # its row names no requirement

  def test_generated_file_is_current(self):
    self.assertEqual(vl.OUT.read_text(encoding="utf-8"), vl.render(vl.links()))


@unittest.skipUnless((vl.REPO / vl.TEST_FILE).exists(), "opendbc_repo is not checked out")
class TestSources(unittest.TestCase):
  def test_inherited_methods_resolve(self):
    have = vl.test_methods(vl.REPO, "TestToyotaSafetyTorque")
    self.assertIn("test_rx_hook", have)                   # TestToyotaSafetyBase (test_toyota.py)
    self.assertIn("test_torque_absolute_limits", have)    # MotorTorqueSteeringSafetyTest (common.py)
    self.assertIn("test_safety_tick", have)               # SafetyTest via CarSafetyTest (common.py)
    self.assertNotIn("test_angle_cmd_when_enabled", have)  # AngleSteeringSafetyTest is not a base

  def test_every_linked_test_exists(self):
    self.assertEqual(vl.problems(), [])


if __name__ == "__main__":
  unittest.main()
