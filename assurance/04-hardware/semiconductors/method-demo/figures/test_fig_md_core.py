#!/usr/bin/env python3
"""Tests for fig_md_core.py (Figures 1 and 2 of the Part 11 method demonstration)."""
import copy
import re
import unittest

import fig_md_core as F
from mdkit import HERE, FigureError, load


class FigMdCore(unittest.TestCase):
  def setUp(self):
    self.S, self.C, self.H = load("subparts.json"), load("coverage.json"), load("coverage-history.json")

  def test_committed_output_is_current(self):
    for name, content in F.build().items():
      self.assertEqual((HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale")

  def test_every_sub_part_drawn_once(self):
    for svg in (F.fig_split(self.S), F.fig_coverage(self.C, self.H)):
      for s in self.S["sub_parts"]:
        label = F.name(s["sub_part"]).replace("&", "&amp;")
        self.assertEqual(len(re.findall(rf">{re.escape(label)}<", svg)), 1, label)

  def test_unknown_or_missing_sub_part_fails(self):
    bad = copy.deepcopy(self.S)
    bad["sub_parts"][0]["sub_part"] = "Cache"
    with self.assertRaises(FigureError):
      F.fig_split(bad)
    bad = copy.deepcopy(self.C)
    del bad["sub_parts"][-1]
    with self.assertRaises(FigureError):
      F.fig_coverage(bad, self.H)

  def test_areas_and_history_must_agree(self):
    bad = copy.deepcopy(self.S)
    bad["sub_parts"][0]["area_um2"] += 500
    with self.assertRaises(FigureError):
      F.fig_split(bad)
    bad = copy.deepcopy(self.H)
    bad["runs"][-1]["perm_dc"] = 0.5
    with self.assertRaises(FigureError):
      F.fig_coverage(self.C, bad)

  def test_readme_states_the_figure_numbers(self):
    readme = (HERE.parent / "README.md").read_text(encoding="utf-8")
    self.assertIn(f"{self.C['perm_dc'] * 100:.1f} %", readme)
    self.assertIn(f"{self.C['perm_dc_excl_safe'] * 100:.1f} %", readme)
    self.assertIn(f"{self.S['cells']:,} cells", readme)


if __name__ == "__main__":
  unittest.main()
