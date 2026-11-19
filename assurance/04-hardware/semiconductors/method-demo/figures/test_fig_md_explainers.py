#!/usr/bin/env python3
"""Tests for fig_md_explainers.py (the six "Part 11 in one minute" explainers)."""
import copy
import re
import unittest

import fig_md_explainers as F
from mdkit import HERE, FigureError, load


class FigMdExplainers(unittest.TestCase):
  def setUp(self):
    self.C, self.H = load("coverage.json"), load("coverage-history.json")
    self.S, self.L = load("subparts.json"), load("sky130_dfxtp_1.json")
    self.E, self.K = load("ecc_summary.json"), load("lockstep_summary.json")

  def test_committed_output_is_current(self):
    out = F.build()
    self.assertEqual(len(out), 6)
    for name, content in out.items():
      self.assertEqual((HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale")

  def test_every_sub_part_once_in_the_bar_charts(self):
    for svg in (F.e3(self.C, self.H), F.e4(self.C), F.e6(self.K)):
      for s in self.C["sub_parts"]:
        label = F.name(s["sub_part"]).replace("&", "&amp;")
        self.assertEqual(len(re.findall(rf">{re.escape(label)}<", svg)), 1, label)

  def test_counts_that_do_not_add_up_fail(self):
    bad = copy.deepcopy(self.E)
    bad["ecc_single"]["wrong"] += 1
    with self.assertRaises(FigureError):
      F.e5(bad)
    bad = copy.deepcopy(self.L)
    bad["gates"] = bad["gates"][:-1]
    with self.assertRaises(FigureError):
      F.e2(self.S, bad)
    bad = copy.deepcopy(self.K)
    bad["caught_first"] -= 1
    with self.assertRaises(FigureError):
      F.e6(bad)

  def test_missing_field_fails(self):
    bad = copy.deepcopy(self.C)
    del bad["seu_dc"]
    with self.assertRaises(FigureError):
      F.e4(bad)

  def test_headline_numbers_match_the_results_and_readme(self):
    readme = (HERE.parent / "README.md").read_text(encoding="utf-8")
    self.assertIn(f"{self.E['base_single']['wrong']} of {self.E['base_single']['n']:,}", readme)
    self.assertIn(f"{self.K['caught_first']:,}", readme)
    self.assertIn(f"{self.K['cc_wrong_cmd_delayed_caught']} of the {self.K['cc_wrong_cmd']}", readme)
    self.assertIn(f"{self.K['area_um2']['lockstep'] / self.K['area_um2']['single']:.2f}", readme)


if __name__ == "__main__":
  unittest.main()
