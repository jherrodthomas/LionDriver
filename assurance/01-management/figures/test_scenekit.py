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
PENDING: set[str] = set()
ROAD = re.compile(r"#565E69|#C9DDBA|#B9C7A6", re.I)   # asphalt, grass, verge


class TestScenekit(unittest.TestCase):
  def test_straight_road_is_the_reference_layout(self):
    road = "".join(sk.straight_road())
    self.assertIn(f'width="{sk.W}" height="{sk.H}" fill="{sk.GRASS}"', road)
    for y in (sk.TOP_EDGE, sk.CENTRE_LINE, sk.BOTTOM_EDGE):
      self.assertIn(f'y1="{y}" x2="{sk.W}" y2="{y}"', road)
    self.assertEqual(road.count('stroke-dasharray="9 9"'), 1)          # one dashed centre line
    self.assertEqual(sk.EGO_LANE - sk.OTHER_LANE, 2 * sk.HALF_LANE)

  def test_strip_is_the_same_road_cropped(self):
    strip = "".join(sk.strip_road())
    self.assertTrue(strip.startswith(f'<g transform="translate(0 {sk.STRIP_DY})">'))
    self.assertIn("".join(sk.straight_road()), strip)
    self.assertEqual((sk.STRIP_TOP, sk.STRIP_CENTRE, sk.STRIP_BOTTOM, sk.STRIP_OTHER, sk.STRIP_EGO), (10, 40, 70, 25, 55))
    self.assertLess(sk.STRIP_BOTTOM, sk.STRIP_H)
    self.assertNotIn("stroke-dasharray", "".join(sk.strip_road(markings=False)))

  def test_large_scene_lines_match_the_stpa_lanes(self):
    """The scaled road puts its lines where the STPA, TARA and FSC scene coordinates expect them."""
    lines = [round(y * sk.LARGE_K + sk.LARGE_DY) for y in (sk.TOP_EDGE, sk.CENTRE_LINE, sk.BOTTOM_EDGE)]
    self.assertEqual(lines, [62, 125, 188])
    road = "".join(sk.large_road())
    self.assertIn(f'translate(0 {sk.LARGE_DY}) scale({sk.LARGE_K})', road)
    self.assertIn(f'x2="{round(sk.LARGE_W / sk.LARGE_K, 2):g}"', road)                  # spans the full 460

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

  def test_browser_kit_shares_the_constants(self):
    """scenekit.js carries the constants block scenekit.py writes, and uses no constant the block lacks."""
    src = sk.JS.read_text(encoding="utf-8")
    self.assertEqual(sk._js_with_block(src), src, "run python3 scenekit.py --js")
    used = set(re.findall(r"\bSK\.([A-Z_]+)", src))
    self.assertLessEqual(used, set(sk.constants()))
    self.assertGreater(len(used), 25)
    self.assertNotIn("</script", src.lower())                            # pages inline it

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

  def test_strip_cards_take_their_size_from_the_kit(self):
    """Cards that embed the strip (FM, hazard log, loss scenarios, FMEA) size it from STRIP_H, not a fixed 70."""
    old = re.compile(r'viewBox="0 0 280 70"|PW \* 70 / 280')
    hits = [p.relative_to(REPO).as_posix() for d in ("assurance", "tools") for p in (REPO / d).rglob("*.py")
            if not p.name.startswith("test_") and old.search(p.read_text(encoding="utf-8"))]
    self.assertEqual(hits, [])


if __name__ == "__main__":
  unittest.main()
