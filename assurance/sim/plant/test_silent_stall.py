#!/usr/bin/env python3
"""Tests for silent_stall.py and the what-if siren: off by default, and when on, the siren follows the revocation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import silent_stall as ss
import simulate


class TestSilentStall(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rs = ss.runs()

  def test_what_if_is_off_by_default(self):
    self.assertEqual(simulate.ASSUMPTIONS["whatif_siren_on_revoke"][0], 0.0)

  def test_as_built_stall_is_silent(self):
    for r in self.rs:
      if r["flag"] == 0.0:
        self.assertIsNotNone(r["revoke"], r["road"])
        self.assertIsNone(r["siren"], r["road"])

  def test_what_if_siren_within_one_tick_of_revocation(self):
    for r in self.rs:
      if r["flag"] == 1.0:
        self.assertEqual(r["cue_kind"], "siren", r["road"])
        self.assertTrue(0.0 < r["siren"] - r["revoke"] <= 0.125 + 1e-9, r["road"])

  def test_siren_never_makes_a_curve_worse(self):
    for road in {r["road_key"] for r in self.rs if r["road_key"] != "straight"}:
      a, b = [r for r in self.rs if r["road_key"] == road]
      self.assertLess(b["corr"], a["corr"], road)
      self.assertLess(b["max_dev"], a["max_dev"], road)

  def test_outputs_current(self):
    for path, content in ss.build().items():
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run silent_stall.py")


if __name__ == "__main__":
  unittest.main()
