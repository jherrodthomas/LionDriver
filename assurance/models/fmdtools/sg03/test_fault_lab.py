#!/usr/bin/env python3
"""Tests for the SG-03 Fault Lab page (tool evaluation TE-02 step P5, DQ-417): the plant parser reads case L-01, the
timeline shows its events, and the page builds from a stubbed sweep."""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fault_lab as fl  # noqa: E402


class PlantCase(unittest.TestCase):
  def test_l01_read_from_the_table(self):
    p = fl.plant_case()
    self.assertEqual(p["case"], "L-01")
    self.assertIn("envelope maximum", p["fault"])
    self.assertLess(p["cue"], p["correction"])
    self.assertLessEqual(p["correction"], p["revoked"])
    self.assertLess(p["gap_min"], p["gap_onset"])

  def test_unknown_case_fails(self):
    with self.assertRaises(KeyError):
      fl.plant_case("F-99")

  def test_timeline_has_every_event(self):
    p = fl.plant_case()
    svg = fl.timeline(p)
    for v in (p["cue"], p["correction"], p["revoked"]):
      self.assertIn(f"{v:.2f} s", svg)


class Page(unittest.TestCase):
  def test_page_builds_from_stubbed_sweep(self):
    stub = {"order": 2, "runs": 7, "modes": 3, "model": [], "tree": [], "agree": [], "tree_only": [], "gaps": [],
            "branches": {"excess": 0, "closing": 0, "unwanted": 0, "gas": 0, "stale": 1, "overlap": 0},
            "budget": 1.0}
    real = fl.sweep_data
    fl.sweep_data = lambda: stub
    try:
      page = fl.build()
    finally:
      fl.sweep_data = real
    self.assertIn("<title>SG-03 Fault Lab</title>", page)
    self.assertIn("no evidence credit", page)
    self.assertIn("No fault set missing from the tree", page)
    self.assertIn("A replayed command buffer stays a single point", page)


if __name__ == "__main__":
  unittest.main()
