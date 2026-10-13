#!/usr/bin/env python3
"""Tests for fsc_figures.py: committed figure is current and agrees with WP-C-04 §3, §5, §9."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fsc_figures as ff


class TestFscFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = ff.SOURCE.read_text(encoding="utf-8")
    cls.goals = ff.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in ff.build().items():
      self.assertEqual((ff.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_every_fsr_drawn_once(self):
    drawn = [f.ident for g in self.goals for f in g.fsrs]
    self.assertEqual(sorted(drawn), sorted(set(re.findall(r"^\| (FSR-\d\d\.\d\d) \|", self.md, re.M))))
    self.assertEqual(len(drawn), len(set(drawn)))

  def test_trace_and_allocation_examples(self):
    fsr = {f.ident: f for g in self.goals for f in g.fsrs}
    self.assertEqual(fsr["FSR-01.09"].serves, [f"SG-0{i}" for i in range(1, 8)])
    self.assertEqual(fsr["FSR-03.02"].serves, ["SG-03", "SG-04"])
    self.assertEqual(fsr["FSR-01.11"].elements, ["E-03", "E-05"])
    self.assertEqual(fsr["FSR-01.13"].asil, "ext")
    self.assertEqual(fsr["FSR-06.05"].asil, "ref")

  def test_unknown_element_rejected(self):
    with self.assertRaises(ff.FigureError):
      ff.parse(self.md.replace("| C | E-03 (HW+SW) |", "| C | E-09 |"))

  def test_fsr_missing_from_trace_rejected(self):
    with self.assertRaises(ff.FigureError):
      ff.parse(self.md.replace("| FSR-01.12 | ● |", "| FSR-01.99 | ● |"))


if __name__ == "__main__":
  unittest.main()
