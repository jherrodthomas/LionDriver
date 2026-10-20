#!/usr/bin/env python3
"""Tests for scenekit.py: the shared top-down scene style, and the guard that keeps new figures on it."""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import scenekit as sk

# figures that still draw the road from their own copy; remove a file here when it moves onto the kit
PENDING = {"assurance/02-concept/sotif/sotif_scenes.py", "assurance/02-concept/sotif/fm_scenes.py",
           "assurance/08-analyses/figures/stpa_scenes.py"}
ROAD = re.compile(r"#565E69|#C9DDBA|#B9C7A6", re.I)   # asphalt, grass, verge


class TestScenekit(unittest.TestCase):
  def test_straight_road_is_the_reference_layout(self):
    road = "".join(sk.straight_road())
    self.assertIn(f'width="{sk.W}" height="{sk.H}" fill="{sk.GRASS}"', road)
    for y in (sk.TOP_EDGE, sk.CENTRE_LINE, sk.BOTTOM_EDGE):
      self.assertIn(f'y1="{y}" x2="{sk.W}" y2="{y}"', road)
    self.assertEqual(road.count('stroke-dasharray="9 9"'), 1)          # one dashed centre line
    self.assertEqual(sk.EGO_LANE - sk.OTHER_LANE, 2 * sk.HALF_LANE)

  def test_curved_road_follows_its_edge_function(self):
    edge = lambda k: [(x, 80 + k) for x in (0, 140, 280)]          # noqa: E731  a straight centre line
    road = "".join(sk.curved_road(edge))
    self.assertIn('d="M0.0 95.0 L140.0 95.0 L280.0 95.0"', road)     # edge line half a lane right of centre
    self.assertIn('d="M0.0 65.0 L140.0 65.0 L280.0 65.0" fill="none" stroke="#F8FAFC" stroke-width="1.3" stroke-dasharray="9 9"', road)

  def test_cars_share_one_body(self):
    self.assertIn(f'fill="{sk.EGO}" stroke="{sk.EGO_EDGE}"', sk.ego_body())
    self.assertIn(f'fill="{sk.OTHER}" stroke="{sk.OTHER_EDGE}"', sk.other_body())
    self.assertEqual(sk.other_body(True).count(sk.HAZARD_LAMP), 2)
    self.assertEqual(sk.ego_body().count("<rect"), sk.other_body().count("<rect"))

  def test_still_frame_is_the_end(self):
    p = [(10.0, 50.0), (60.0, 50.0), (110.0, 70.0)]
    g = sk.driving(p, sk.ego_body(), lambda x: sk.DRIVE * (x - 10) / 100)
    self.assertTrue(g.startswith('<g transform="translate(110.0 70.0)">'))
    self.assertIn('keyTimes="0.0000;0.4000;0.8000;1.0000"', g)
    g = sk.drive_t([(0, 10, 84), (0.5, 60, 84), (1, 90, 84)], sk.ghost_body())
    self.assertTrue(g.startswith('<g transform="translate(90.0 84.0)">'))

  def test_every_animation_loops(self):
    parts = [sk.appear(0.3), sk.window(0.2, 0.5), sk.fault_marker(50, 60, 0.3), sk.callout(50, 60, 6, "crosses edge line", 49, 0.4),
             *sk.badges([("a", 0, None, "info"), ("b", 0.2, None, "bad"), ("c", 0.2, 0.6, "ok")], lambda t: t),
             *sk.gap_band("M0 0 L10 10 Z", "x", 14, 262), *sk.traffic_light(150, 0.55)]
    svg = "".join(parts)
    self.assertEqual(svg.count("<animate"), svg.count(f'dur="{sk.DUR}s" repeatCount="indefinite"'))

  def test_callout_label_stays_inside_the_scene(self):
    self.assertGreater(sk.fit_x(2, "into the next lane"), 30)
    self.assertLess(sk.fit_x(278, "into the next lane"), sk.W - 30)

  def test_new_scene_figures_use_the_kit(self):
    """No generator draws the road from its own palette copy, except the ones still to migrate."""
    found = set()
    for p in (REPO / "assurance").rglob("*.py"):
      rel = p.relative_to(REPO).as_posix()
      if p.name.startswith("test_") or rel == "assurance/01-management/figures/scenekit.py":
        continue
      if ROAD.search(p.read_text(encoding="utf-8")):
        found.add(rel)
    for p in (REPO / "docs").rglob("*.py"):
      if not p.name.startswith("test_") and ROAD.search(p.read_text(encoding="utf-8")):
        found.add(p.relative_to(REPO).as_posix())
    self.assertEqual(found - PENDING, set(), "draw top-down scenes with scenekit.py instead of a palette copy")
    self.assertEqual(PENDING - found, set(), "migrated: remove it from PENDING")


if __name__ == "__main__":
  unittest.main()
