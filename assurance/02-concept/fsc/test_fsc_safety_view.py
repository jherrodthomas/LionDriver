#!/usr/bin/env python3
"""Tests for fsc_safety_view.py: the safety view counts the §5 allocation and flags QM elements carrying ASIL FSRs."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fsc_figures as ff
import fsc_safety_view as sv


class TestFscSafetyView(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = ff.SOURCE.read_text(encoding="utf-8")
    cls.goals = ff.parse(cls.md)
    cls.view = sv.model(cls.goals, cls.md)

  def test_counts_follow_allocation(self):
    for e, v in self.view.items():
      expected = sorted(f.ident for g in self.goals for f in g.fsrs if e in f.elements)
      self.assertEqual(sorted(f.ident for f in v["fsrs"]), expected, e)

  def test_envelope_and_soc(self):
    self.assertEqual(self.view["E-03"]["top"], "C")
    self.assertFalse(self.view["E-03"]["qm_carries"])
    self.assertTrue(self.view["E-01"]["qm_carries"])
    self.assertEqual(sv.driver_aous(self.md), ["AOU-06R", "AOU-02R"])

  def test_committed_output_current(self):
    for name, content in sv.build(self.goals, self.md).items():
      self.assertEqual((ff.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_element_without_box_rejected(self):
    md = self.md.replace("| C | E-03 (HW+SW) |", "| C | E-03, E-06 |")
    self.assertNotEqual(md, self.md)
    with self.assertRaises((sv.SafetyViewError, ff.FigureError)):
      sv.model(ff.parse(md), md)


if __name__ == "__main__":
  unittest.main()
