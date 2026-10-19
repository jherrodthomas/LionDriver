#!/usr/bin/env python3
"""Tests for stpa_ls_scenes.py: one card per loss scenario of WP-A-05 §5, quotes checked, scenes loop, no second copy of fig_a05_stpa."""

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_a05_stpa as fs
import stpa_ls_scenes as ls


class TestLossScenarioCards(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.S = fs.load()
    cls.out = ls.sheets(cls.S, fs)

  def test_every_scenario_is_on_exactly_one_sheet(self):
    seen = []
    for name, (num, _, _) in ls.SHEETS.items():
      self.assertIn(f"Figure {num}.", self.out[name])
      desc = re.search(r"<desc[^>]*>(.*?)</desc>", self.out[name], re.S).group(1)
      seen += re.findall(r"(LS-\d+) \(UCA-", desc)
    self.assertEqual(sorted(seen), sorted(ls.rows(self.S)))
    self.assertEqual(len(seen), len(set(seen)))
    self.assertEqual(set(ls.MODELS), {s["id"] for s in self.S.smap["scenarios"]})

  def test_scenario_sits_on_the_sheet_of_its_first_uca(self):
    by_sheet = {name: re.findall(r"(LS-\d+) \(UCA-", re.search(r"<desc[^>]*>(.*?)</desc>", svg, re.S).group(1))
                for name, svg in self.out.items()}
    for c in ls.cards(self.S):
      n = int(c["uca"][4:])
      [name] = [s for s, (_, _, pick) in ls.SHEETS.items() if pick(n)]
      self.assertIn(c["ls"], by_sheet[name], c["ls"])

  def test_status_comes_from_the_map(self):
    status = {s["id"]: s["status"] for s in self.S.smap["scenarios"]}
    for c in ls.cards(self.S):
      self.assertEqual(c["status"], status[c["ls"]], c["ls"])

  def test_quote_no_longer_in_the_row_fails(self):
    models = dict(ls.MODELS)
    title, scene, tags, steps = models["LS-02"]
    models["LS-02"] = (title, scene, tags, [("x", "a phrase WP-A-05 never says")] + list(steps[1:]))
    with mock.patch.object(ls, "MODELS", models):
      with self.assertRaisesRegex(fs.ParseError, "LS-02 step 1"):
        ls.sheets(self.S, fs)

  def test_scenario_without_a_card_fails(self):
    models = {k: v for k, v in ls.MODELS.items() if k != "LS-04"}
    with mock.patch.object(ls, "MODELS", models):
      with self.assertRaisesRegex(fs.ParseError, "no card for LS-04"):
        ls.sheets(self.S, fs)

  def test_card_for_a_scenario_wp_a05_lacks_fails(self):
    models = dict(ls.MODELS, **{"LS-99": ls.MODELS["LS-02"]})
    with mock.patch.object(ls, "MODELS", models):
      with self.assertRaisesRegex(fs.ParseError, "LS-99"):
        ls.sheets(self.S, fs)

  def test_scenes_loop(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))

  def test_output_is_deterministic(self):
    self.assertEqual(self.out, ls.sheets(self.S, fs))

  def test_every_sheet_is_in_wp_a05(self):
    doc = fs.SOURCE.read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"figures/{name}", doc)

  def test_does_not_import_fig_a05_stpa(self):
    src = Path(ls.__file__).read_text(encoding="utf-8")
    self.assertNotRegex(src, r"(?m)^\s*(import|from)\s+fig_a05_stpa")


if __name__ == "__main__":
  unittest.main()
