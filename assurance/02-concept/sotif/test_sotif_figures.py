#!/usr/bin/env python3
"""Tests for sotif_figures.py: committed figure is current and agrees with WP-C-06 §3-§5 and WP-C-05 §3."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sotif_figures as sf


class TestSotifFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md5 = sf.C05.read_text(encoding="utf-8")
    cls.md6 = sf.C06.read_text(encoding="utf-8")
    cls.data = sf.parse(cls.md5, cls.md6)

  def test_committed_output_current(self):
    for name, content in sf.build().items():
      self.assertEqual((sf.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_every_tc_and_fi_in_the_chain(self):
    self.assertEqual(sorted({x for r in self.data.rows for x in r[0]}), sorted(self.data.tc))
    self.assertEqual(sorted({x for r in self.data.rows for x in r[1]}), sorted(self.data.fi))
    self.assertNotIn("SH-07", self.data.sh)

  def test_examples(self):
    rows = {tc: r for r in self.data.rows for tc in r[0]}
    self.assertEqual(rows["TC-01"][1], ["FI-02"])
    self.assertEqual(rows["TC-13"][3], "mod")
    self.assertEqual(rows["TC-28"][3], "acc")
    self.assertEqual(self.data.fi["FI-10"][3], ["SH-06"])

  def test_tc_without_evaluation_rejected(self):
    md6 = self.md6.replace("| TC-32 | FI-01 |", "| TC-31 | FI-01 |")
    with self.assertRaises(sf.FigureError):
      sf.parse(self.md5, md6)

  def test_undefined_fi_rejected(self):
    with self.assertRaises(sf.FigureError):
      sf.parse(self.md5, self.md6.replace("| TC-30 | FI-17 |", "| TC-30 | FI-99 |"))

  def test_unknown_outcome_rejected(self):
    with self.assertRaises(sf.FigureError):
      sf.parse(self.md5, self.md6.replace("| Event without reaction | Needs modification |", "| Event without reaction | Fine |"))

  def test_hazard_not_linked_is_a_warning(self):
    self.assertTrue(all("names" in w for w in sf.warnings(self.data)))


if __name__ == "__main__":
  unittest.main()
