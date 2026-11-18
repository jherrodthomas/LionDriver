#!/usr/bin/env python3
"""Tests for fig_s07_boundaries_anim.py: committed SVG current, every boundary and control drawn, a changed table fails."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s07_boundaries_anim as fb
from figkit import FigureError


class TestBoundariesAnim(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fb.SOURCE.read_text(encoding="utf-8")
    cls.zones, cls.tbs = fb.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fb.build().items():
      self.assertEqual((fb.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s07_boundaries_anim.py")

  def test_boundaries_and_controls(self):
    self.assertEqual([t["id"] for t in self.tbs], fb.ORDER)
    tb = {t["id"]: t for t in self.tbs}
    self.assertEqual(tb["TB-1"]["zones"], ["Z2", "Z1"])
    self.assertEqual(tb["TB-1"]["controls"][:6], [f"CSR-01{i}" for i in range(1, 7)])  # CSR-011…CSR-016 expanded
    self.assertEqual(tb["TB-2"]["count"]["in"], 0)  # the open boundary (WP-S-07 §3.4)
    svg = (fb.HERE / fb.OUT).read_text(encoding="utf-8")
    self.assertEqual(svg.count('class="fr f'), len(self.tbs) + 1)
    self.assertIn("prefers-reduced-motion", svg)
    for t in self.tbs:
      for c in t["controls"]:
        self.assertIn(f">{c}<", svg)

  def test_unknown_control_fails(self):
    md = self.md.replace("| CSR-091…CSR-093 |", "| CSR-091…CSR-099 |", 1)
    self.assertNotEqual(md, self.md)
    with self.assertRaises(FigureError):
      fb.parse(md)


if __name__ == "__main__":
  unittest.main()
