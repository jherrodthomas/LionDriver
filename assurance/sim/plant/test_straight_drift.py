#!/usr/bin/env python3
"""Tests for straight_drift.py: the loss is silent, no push means no drift, and a stronger push reaches the line sooner."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import straight_drift as sd


class TestStraightDrift(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.rs = sd.runs()

  def test_loss_is_silent(self):
    for r in self.rs:
      self.assertIsNone(r["siren"], (r["fault"], r["push"], r["kph"]))

  def test_no_push_no_drift(self):
    for r in self.rs:
      if r["push"] == 0:
        self.assertIsNone(r["cue"])
        self.assertLess(r["max_dev"], 0.05)

  def test_stronger_push_reaches_the_line_sooner(self):
    for fid, _ in sd.FAULTS:
      for kph in sd.SPEEDS:
        ts = [r["t_narrow"] for r in self.rs if r["fault"] == fid and r["kph"] == kph and r["push"] >= 0.2]
        self.assertTrue(all(t is not None for t in ts))
        self.assertEqual(ts, sorted(ts, reverse=True))

  def test_outputs_current(self):
    for path, content in sd.build().items():
      self.assertTrue(path.exists(), path.name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run straight_drift.py")


if __name__ == "__main__":
  unittest.main()
