#!/usr/bin/env python3
"""Tests for fig_sim_guide.py: source dashboard pinned, images present and small, boxes inside the dashboard, embedded."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_sim_guide as fg


class TestGuide(unittest.TestCase):
  def test_no_problems(self):
    self.assertEqual(fg.problems(), [])

  def test_ten_panels_inside_the_dashboard(self):
    self.assertEqual(sorted(fg.PANELS), list(range(1, 11)))
    w, h = fg.SOURCE_SIZE
    for n, (_name, (x0, y0, x1, y1)) in fg.PANELS.items():
      self.assertTrue(0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h, n)

  def test_spotlights_cover_every_panel_but_header_footer_once(self):
    lit = [n for ids, _t, _s in fg.IMAGES.values() if ids for n in ids]
    self.assertEqual(sorted(lit), [1, 2, 3, 4, 5, 6, 7, 8, 9])

  def test_overview_says_synthetic(self):
    self.assertIn("no evidence credit", fg.IMAGES["sim-guide-0-overview.jpg"][2])

  def test_readme_embeds_every_image_and_names_every_panel(self):
    md = (fg.SIM / "README.md").read_text(encoding="utf-8")
    for name in fg.IMAGES:
      self.assertIn(f"](figures/{name})", md, name)
    for n, (name, _box) in fg.PANELS.items():
      self.assertIn(f"{n}. **{name}**", md, name)


if __name__ == "__main__":
  unittest.main()
