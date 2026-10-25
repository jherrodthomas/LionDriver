#!/usr/bin/env python3
"""Tests for fig_s04_verdicts.py: committed SVG current, every §5 row sorted once, a changed verdict cell fails."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s04_verdicts as fv


class TestVerdicts(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fv.SOURCE.read_text(encoding="utf-8")
    cls.rows = fv.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fv.build().items():
      self.assertEqual((fv.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s04_verdicts.py")

  def test_every_row_once(self):
    self.assertEqual(len(self.rows), len(fv.VERDICT))
    svg = (fv.HERE / fv.OUT).read_text(encoding="utf-8")
    for r in self.rows:
      self.assertEqual(svg.count(f">{r['name']}<"), 1, r["name"])

  def test_changed_cell_fails(self):
    md = self.md.replace("Met (envelope side)", "Met, measured on the bench", 1)
    self.assertNotEqual(md, self.md)
    with self.assertRaises(fv.VerdictError):
      fv.parse(md)

  def test_new_row_fails(self):
    md = re.sub(r"(\n\| Brake / cancel \|)", "\n| New fault | ≤ 1 s | — | Not met | — | TSR-999 |\\1", self.md, count=1)
    with self.assertRaises(fv.VerdictError):
      fv.parse(md)


if __name__ == "__main__":
  unittest.main()
