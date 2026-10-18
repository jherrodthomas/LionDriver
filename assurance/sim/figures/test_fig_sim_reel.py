#!/usr/bin/env python3
"""Tests for fig_sim_reel.py: source clips present, ratings match WP-C-03, the reel animated, small and embedded."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_sim_reel as fr


class TestReel(unittest.TestCase):
  def test_no_problems(self):
    self.assertEqual(fr.problems(), [])

  def test_every_segment_labelled_with_a_rating_or_sotif(self):
    for clip, _s, _d, event, rating, text in fr.SEGMENTS:
      lab = fr.label(event, rating, text)
      self.assertTrue(lab.startswith(f"{event} · "), clip)
      self.assertTrue("ASIL " in lab or "SOTIF hazard" in lab, clip)
    self.assertIn("no evidence credit", fr.BAND_TEXT)

  def test_segments_inside_their_clips(self):
    # clip lengths (s) as committed; each clip starts 1.5 s before the fault
    length = {"he-02-1-eps-loss-curve": 7.54, "he-01-1-rural-hardover-oncoming": 4.08, "sh-11-pedestrian-occluded": 4.08}
    for clip, start, dur, *_ in fr.SEGMENTS:
      self.assertGreaterEqual(start, 0.0, clip)
      self.assertLessEqual(start + dur, length[clip], clip)

  def test_readme_embeds_the_reel(self):
    md = (fr.SIM / "README.md").read_text(encoding="utf-8")
    self.assertIn(f"](figures/{fr.OUT.name})", md)


if __name__ == "__main__":
  unittest.main()
