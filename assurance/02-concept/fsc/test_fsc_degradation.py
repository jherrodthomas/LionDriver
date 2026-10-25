#!/usr/bin/env python3
"""Tests for fsc_degradation.py: the ladder follows WP-C-04 §12.1 and every safe state it names is defined in §6."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fsc_degradation as fd
import fsc_figures as ff


class TestFscDegradation(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = ff.SOURCE.read_text(encoding="utf-8")

  def test_levels_and_states(self):
    levels, states = fd.parse(self.md)
    self.assertEqual([r[0] for r in levels], ["L0", "L1", "L2", "L3", "L4", "L5"])
    self.assertEqual(sorted(states), ["SS-G", "SS-L", "SS-S"])

  def test_committed_output_current(self):
    for name, content in fd.build(self.md).items():
      self.assertEqual((ff.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_undefined_safe_state_rejected(self):
    with self.assertRaises(fd.LadderError):
      fd.parse(self.md.replace("| L3 | Immediate disengagement | SS-L |", "| L3 | Immediate disengagement | SS-X |"))

  def test_missing_level_rejected(self):
    with self.assertRaises(fd.LadderError):
      fd.parse(self.md.replace("| L5 | Lockout |", "| L6 | Lockout |"))


if __name__ == "__main__":
  unittest.main()
