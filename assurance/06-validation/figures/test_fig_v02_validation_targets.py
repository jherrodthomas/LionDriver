#!/usr/bin/env python3
"""Tests for fig_v02_validation_targets.py: source texts still in WP-V-02, §4 rows parsed, SVG current and well-formed."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_v02_validation_targets as fv

SVG_NS = "{http://www.w3.org/2000/svg}"


class TestValidationTargets(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fv.SOURCE.read_text(encoding="utf-8")
    cls.targets = fv.parse(cls.md)

  def test_source_texts_present(self):
    self.assertEqual(fv.missing_sources(self.md), [])

  def test_every_target_drawn_once(self):
    ids = [t.ident for t in self.targets]
    self.assertEqual(ids, [f"VT-{i:02d}" for i in range(1, 16)])
    drawn = {m["vt"] for m in fv.MARKS} | set(fv.NO_COUNT)
    self.assertEqual(drawn, set(ids))
    self.assertFalse({m["vt"] for m in fv.MARKS} & set(fv.NO_COUNT))

  def test_numbers_match_source(self):
    # case D: 6 x 10^5 mi at 95 % is 1.5 x 10^4 h at 64 km/h, as §3.1 states
    vt01 = next(m for m in fv.MARKS if m["vt"] == "VT-01" and m["panel"] == "km")
    self.assertAlmostEqual(vt01["value"] / fv.KMH, 1.5e4)
    # zero-failure trials of §3 step 5: N = ln(1 - C) / ln(1 - p_max) -> 299 at 1 %, 59 at 5 %
    import math
    self.assertEqual(math.ceil(math.log(0.05) / math.log(0.99)), 299)
    self.assertEqual(math.ceil(math.log(0.05) / math.log(0.95)), 59)
    for m in fv.MARKS:
      if m["panel"] == "count":
        self.assertIn(m["value"], (14, 20, 59, 299), m["label"])
        self.assertIn(str(m["value"]), m["label"])
    self.assertIn("299 trials", self.md)

  def test_bands_below_rate_level_target(self):
    road = next(b for b in fv.BANDS if b["panel"] == "km")
    vt01 = next(m for m in fv.MARKS if m["vt"] == "VT-01" and m["panel"] == "km")
    self.assertLess(road["hi"], vt01["value"])  # §3.2: case D out of reach

  def test_committed_output_current(self):
    path = fv.HERE / fv.OUTPUT
    self.assertTrue(path.exists())
    self.assertEqual(path.read_text(encoding="utf-8"), fv.build(), "stale; run fig_v02_validation_targets.py")

  def test_svg_valid_with_role_title_desc(self):
    root = ET.fromstring(fv.build())
    self.assertEqual(root.get("role"), "img")
    self.assertIsNotNone(root.find(f"{SVG_NS}title"))
    self.assertIsNotNone(root.find(f"{SVG_NS}desc"))

  def test_no_solid_target(self):
    # §4: every numeric target is a placeholder, so every target mark is dashed
    out = fv.build()
    self.assertNotIn('fill="#C2410C" stroke="#C2410C"', out)

  def test_build_is_deterministic(self):
    self.assertEqual(fv.build(), fv.build())


if __name__ == "__main__":
  unittest.main()
