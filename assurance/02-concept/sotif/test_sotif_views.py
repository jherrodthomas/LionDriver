#!/usr/bin/env python3
"""Tests for sotif_views.py: every triggering condition sits in one ODD category, the line-up follows the documents."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sotif_figures as sf
import sotif_views as sv


class TestSotifViews(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.d = sf.load()
    cls.md2 = sv.C02.read_text(encoding="utf-8")
    cls.md5 = sf.C05.read_text(encoding="utf-8")
    cls.md7 = sv.C07.read_text(encoding="utf-8")
    cls.mv2 = sv.V02.read_text(encoding="utf-8")

  def test_committed_output_current(self):
    for name, content in sv.build(self.d).items():
      self.assertEqual((sf.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_every_tc_has_an_odd_category(self):
    sv.check_tc_odd(self.d, sv.odd_categories(self.md2))
    self.assertEqual(set(sv.TC_ODD), set(self.d.tc))

  def test_unknown_category_rejected(self):
    old = sv.TC_ODD["TC-05"]
    sv.TC_ODD["TC-05"] = "Lane paint"
    try:
      with self.assertRaises(sv.ViewError):
        sv.check_tc_odd(self.d, sv.odd_categories(self.md2))
    finally:
      sv.TC_ODD["TC-05"] = old

  def test_lineup_examples(self):
    m = sv.lineup_model(self.d, self.md5, self.md7, self.mv2)
    self.assertIn(("FM-01", "P1"), m["SH-09"]["fm"])
    self.assertEqual(m["SH-08"]["vt"], ["VT-07"])
    self.assertEqual(m["SH-01"]["ac"], ["AC-02"])
    self.assertIn("AC-07", m["SH-01"]["ac_all"])
    self.assertIn("TC-34", m["SH-08"]["tc"])

  def test_sh_list(self):
    known = ["SH-01", "SH-03", "SH-04", "SH-06"]
    self.assertEqual(sv._sh_list("SH-01, 03, 04", known, "t"), ["SH-01", "SH-03", "SH-04"])
    self.assertEqual(sv._sh_list("All SH", known, "t"), known)
    with self.assertRaises(sv.ViewError):
      sv._sh_list("SH-99 something", known, "t")


if __name__ == "__main__":
  unittest.main()
