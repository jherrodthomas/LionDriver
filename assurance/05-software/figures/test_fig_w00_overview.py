#!/usr/bin/env python3
"""Tests for fig_w00_overview.py: committed outputs current, every work product drawn once with its count, the
status figure agrees with the SWSR records, a changed source fails, and the gallery points at files that exist."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_w00_overview as fg


class TestFigure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.sw = fg.swsrs()
    cls.n = fg.counts(cls.sw)

  def test_committed_output_current(self):
    for name, content in fg.build().items():
      self.assertEqual((fg.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_every_work_product_drawn_once(self):
    svg = (fg.HERE / fg.OUT_V).read_text(encoding="utf-8")
    for wid in fg.WPS:
      self.assertEqual(svg.count(f">{wid}<"), 1, wid)
      self.assertIn(f">{self.n[wid]} {fg.WPS[wid][2]}<", svg)
    self.assertIn('<g class="terms">', svg)

  def test_status_agrees_with_the_records(self):
    svg = (fg.HERE / fg.OUT_S).read_text(encoding="utf-8")
    self.assertIn(f">{len(self.sw)} software safety requirements (WP-W-02)<", svg)
    impl = sum(r["state"] == "impl" for r in self.sw.values())
    self.assertIn(f">in the code {impl}<", svg)

  def test_missing_section_fails(self):
    saved = dict(fg.WPS)
    try:
      fg.WPS["WP-W-06"] = ("Unit verification", r"VS-UV-\d+", "test cases", "## 99.")
      with self.assertRaises(fg.FigureError):
        fg.counts(self.sw)
    finally:
      fg.WPS.clear()
      fg.WPS.update(saved)

  def test_gallery_files_exist(self):
    md = (fg.HERE / fg.SECTION).read_text(encoding="utf-8")
    for p, cap, _where in fg.GALLERY:
      self.assertTrue((fg.SOFTWARE / p).exists(), p)
      self.assertIn(cap, md)


if __name__ == "__main__":
  unittest.main()
