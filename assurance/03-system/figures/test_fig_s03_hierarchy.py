#!/usr/bin/env python3
"""Tests for fig_s03_hierarchy.py: §5 allocates every TSR, the committed SVG is current, lists fit their boxes."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s03_hierarchy as fh


class TestHierarchyFigure(unittest.TestCase):
  def setUp(self):
    self.md = fh.SOURCE.read_text(encoding="utf-8")

  def test_no_problems(self):
    self.assertEqual(fh.problems(self.md), [])

  def test_committed_output_current(self):
    self.assertEqual((fh.HERE / fh.OUT).read_text(encoding="utf-8"), fh.build(self.md),
                     "stale; run fig_s03_hierarchy.py")

  def test_svg_parses_and_has_title(self):
    root = ET.fromstring(fh.build(self.md))
    self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))

  def test_every_allocated_number_drawn(self):
    svg = fh.build(self.md)
    for e in fh.BOXES:
      cell = fh.allocation(self.md).get(e, "")
      for n in re.findall(r"\d{3}", cell):
        self.assertIn(n, svg, f"{e}: {n}")

  def test_lines_fit_boxes(self):
    for e, (x, w, _) in fh.BOXES.items():
      for line in fh.wrap(fh.allocation(self.md).get(e, ""), w):
        if " " in line:  # a single word wider than the box cannot be broken
          self.assertLessEqual(fh.width(line), w, line)

  def test_unallocated_tsr_detected(self):
    md = self.md.replace(", 713 |", " |", 1)
    self.assertIn(713, fh.unallocated(md))

  def test_sm_ranges(self):
    self.assertEqual(fh.sm_list(["SM-25", "SM-27", "SM-28", "SM-30", "SM-31", "SM-32"]), "SM-25, 27, 28, 30–32")

  def test_all_mechanisms_placed(self):
    sms = fh.mechanisms(self.md)
    self.assertEqual(len(sms), int(max(sms)[3:]))


if __name__ == "__main__":
  unittest.main()
