#!/usr/bin/env python3
"""Tests for fig_c05_four_areas.py: the counts of the four-area chart are read from WP-C-05 and WP-C-06."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c05_four_areas as fa


class TestFourAreas(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.c = fa.sotif_counts()
    cls.svg = fa.build()[fa.OUT]

  def test_counts_match_the_tables(self):
    t6 = fa.C06.read_text(encoding="utf-8")
    self.assertEqual(self.c["fi"], len(set(re.findall(r"^\| (FI-\d+) \| [PS] \|", t6, re.M))))
    self.assertEqual(self.c["mod"] + self.c["val"] + self.c["acc"], self.c["rows"])
    self.assertEqual(self.c["sh"], 13)  # SH-01…SH-14 without the placeholder SH-07
    self.assertEqual(self.c["sh_last"], "SH-14")

  def test_the_chart_shows_the_counts(self):
    self.assertIn(f"{self.c['fi']} functional insufficiencies FI-01…{self.c['fi_last']}", self.svg)
    self.assertIn(f"{self.c['tc']} triggering conditions TC-01…{self.c['tc_last']}", self.svg)
    self.assertIn(f"Evaluation of the {self.c['rows']} rows", self.svg)
    self.assertIn(f"{self.c['val']} · needs validation", self.svg)
    self.assertNotIn("$", self.svg)

  def test_a_new_acceptable_row_fails_the_build(self):
    with tempfile.TemporaryDirectory() as d:
      c06 = Path(d) / "c06.md"
      text = fa.C06.read_text(encoding="utf-8").replace("| None | Needs validation | WP-V-03; FM-09 |", "| None | Acceptable | WP-V-03; FM-09 |", 1)
      c06.write_text(text, encoding="utf-8")
      self.assertEqual(fa.sotif_counts(fa.C05, c06)["acc"], self.c["acc"] + 1)

  def test_an_unknown_outcome_is_an_error(self):
    with tempfile.TemporaryDirectory() as d:
      c06 = Path(d) / "c06.md"
      c06.write_text(fa.C06.read_text(encoding="utf-8").replace("| Needs modification (ODD exclusion + user info)", "| Maybe (ODD exclusion + user info)", 1), encoding="utf-8")
      with self.assertRaises(fa.ParseError):
        fa.sotif_counts(fa.C05, c06)

  def test_the_committed_svg_is_current(self):
    self.assertEqual((fa.HERE / fa.OUT).read_text(encoding="utf-8"), self.svg)


if __name__ == "__main__":
  unittest.main()
