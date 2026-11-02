#!/usr/bin/env python3
"""Tests for fig_scene_template.py: committed SVG current, the scene style kept, a reworded source fails.

Template from .claude/skills/road-scene: rename with the generator and import it as `fs`.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_scene_template as fs

sk = fs.sk


class TestScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.svg = (fs.HERE / fs.OUT).read_text(encoding="utf-8")

  def test_committed_output_current(self):
    for name, content in fs.build().items():
      self.assertEqual((fs.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_one_red_car_per_scene(self):
    # Rule 1 of scene-style.md: the item's car is the only red car.
    self.assertEqual(self.svg.count(f'fill="{sk.EGO}"'), len(fs.SCENES))

  def test_one_fault_and_one_moment_per_scene(self):
    # Rule 3: each mark at most once per scene.
    self.assertEqual(self.svg.count(f'fill="{sk.FAULT}"'), len(fs.SCENES))
    self.assertEqual(self.svg.count(f'stroke="{sk.CALLOUT}"'), len(fs.SCENES))

  def test_still_frame_is_the_end(self):
    # Rule 5: a viewer that does not animate shows each car where its path ends.
    for s in fs.SCENES:
      x, y = s["path"][-1]
      self.assertIn(f'<g transform="translate({x:.1f} {y:.1f})">', self.svg, s["title"])

  def test_every_animation_loops(self):
    for a in re.findall(r"<animate(?:Transform)?\b[^>]*>", self.svg):
      self.assertIn(f'dur="{sk.DUR}s"', a)
      self.assertIn('repeatCount="indefinite"', a)

  def test_says_it_is_not_evidence(self):
    self.assertIn("not test or simulation output", self.svg)

  def test_reworded_source_fails(self):
    saved = fs.SCENES[0]["quote"]
    try:
      fs.SCENES[0]["quote"] = saved + " (reworded)"
      with self.assertRaises(fs.FigureError):
        fs.build()
    finally:
      fs.SCENES[0]["quote"] = saved


if __name__ == "__main__":
  unittest.main()
