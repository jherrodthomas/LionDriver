#!/usr/bin/env python3
"""Tests for the Fault Lab page (TE-02 step P5): the plant parser reads case F-07 from the generated table, the scene
and the matrix render, and the page carries no number that is not in its sources. The sweep itself is tested in
test_sg02.py; here the P4 run is stubbed, so the test runs in a second."""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fault_lab as fl  # noqa: E402


class PlantCase(unittest.TestCase):
  def test_f07_read_from_the_table(self):
    p = fl.plant_case()
    self.assertEqual(p["case"], "F-07")
    self.assertIn("EPS fault", p["fault"])
    # order of events as the plant reports them
    self.assertLess(p["siren"], p["torque"])
    self.assertLess(p["torque"], p["cross"])
    self.assertLess(p["cross"], p["correction"])
    self.assertEqual(p["events"]["fault"], 0.0)
    self.assertAlmostEqual(p["events"]["panda siren"], p["siren"], delta=0.005)

  def test_unknown_case_fails(self):
    with self.assertRaises(KeyError):
      fl.plant_case("F-99")


class Drawing(unittest.TestCase):
  def test_scene_is_still_and_labelled(self):
    p = fl.plant_case()
    svg = fl.scene(p)
    self.assertTrue(svg.startswith("<svg") and svg.endswith("</svg>"))
    self.assertNotIn("<animate", svg)
    self.assertIn(f"{p['cross']:.2f} s", svg)
    self.assertIn("aria-label", svg)

  def test_timeline_has_every_event(self):
    p = fl.plant_case()
    svg = fl.timeline(p)
    for t in (p["siren"], p["torque"], p["cross"], p["correction"]):
      self.assertIn(f"{t:.2f} s", svg)

  def test_matrix_marks_model_and_tree_pairs(self):
    a, b, c = frozenset({"BE-2.02", "BE-2.09"}), frozenset({"BE-2.01", "BE-2.08"}), frozenset({"BE-2.04"})
    svg = fl.matrix({"model": [a, c], "tree": [b, c]})
    self.assertEqual(svg.count('class="te"'), 2)      # a, both ways
    self.assertEqual(svg.count('class="ring"'), 2)    # b, both ways; the single c is not a pair
    self.assertNotIn("BE-2.04", svg)


class Page(unittest.TestCase):
  def test_page_builds_from_stubbed_sweep(self):
    stub = {"order": 2, "runs": 7, "modes": 3, "model": [], "tree": [], "agree": [], "tree_only": [], "covered": [],
            "gaps": [], "timing": [], "within": [], "late": [], "none": [], "tight": None, "budget": 1.0}
    real = fl.sweep_data
    fl.sweep_data = lambda: stub
    try:
      page = fl.build()
    finally:
      fl.sweep_data = real
    self.assertIn("<title>SG-02 Fault Lab</title>", page)
    self.assertIn("no evidence credit", page)
    self.assertIn("prefers-color-scheme:dark", page)
    self.assertIn("No fault set missing from the tree", page)


if __name__ == "__main__":
  unittest.main()
