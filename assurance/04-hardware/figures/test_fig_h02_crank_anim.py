#!/usr/bin/env python3
"""Tests for fig_h02_crank_anim.py: committed SVG current, every run of the results table drawn once, a changed source
fails, and the figure agrees with the count of resets in the table."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_h02_crank_anim as fg


class TestFigure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.data, cls.th, cls.grid = fg.load()
    cls.svg = (fg.HERE / fg.OUT).read_text(encoding="utf-8")

  def test_committed_output_current(self):
    for name, content in fg.build().items():
      self.assertEqual((fg.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_every_run_drawn_once(self):
    md = fg.TABLE.read_text(encoding="utf-8")
    rows = [ln for ln in md.splitlines() if ln.startswith("| I")]
    self.assertEqual(len(self.grid), len(rows))
    self.assertEqual(self.svg.count(">rides through<") + self.svg.count(">resets, restarts at US<"), len(self.grid))
    self.assertIn('<g class="terms">', self.svg)

  def test_reset_count_agrees(self):
    resets = sum(o != "rides through" for _, _, o in self.grid)
    self.assertIn(f"{resets} of the {len(self.grid)} runs reset", self.svg)

  def test_mcu_state_rule(self):
    th = self.th
    self.assertEqual(fg.mcu_state(3.3, th)[0], "running")
    self.assertTrue(fg.mcu_state(th["bor1"], th)[0].startswith("below BOR3"))
    self.assertEqual(fg.mcu_state(0.0, th)[0], "power-down reset")

  def test_unknown_outcome_fails(self):
    md = fg.TABLE.read_text(encoding="utf-8")
    bad = md.replace("| rides through |", "| browns out |", 1)
    self.assertNotEqual(bad, md)
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "crank-dip.md"
      p.write_text(bad, encoding="utf-8")
      saved, fg.TABLE = fg.TABLE, p
      try:
        with self.assertRaises(fg.FigureError):
          fg.load()
      finally:
        fg.TABLE = saved

  def test_missing_threshold_fails(self):
    data = json.loads(fg.RESULTS.read_text(encoding="utf-8"))
    del data["thresholds"]["bor3"]
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "crank-dip.json"
      p.write_text(json.dumps(data), encoding="utf-8")
      saved, fg.RESULTS = fg.RESULTS, p
      try:
        with self.assertRaises(fg.FigureError):
          fg.load()
      finally:
        fg.RESULTS = saved


if __name__ == "__main__":
  unittest.main()
