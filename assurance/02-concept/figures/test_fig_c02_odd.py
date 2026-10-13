#!/usr/bin/env python3
"""Tests for fig_c02_odd.py: source texts still in WP-C-02, §3.2 table equal to its formulas, SVGs current."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c02_odd as fo

NS = "{http://www.w3.org/2000/svg}"


class TestOddFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fo.SOURCE.read_text(encoding="utf-8")
    cls.out = fo.build(cls.md)

  def test_no_source_problems(self):
    self.assertEqual(fo.problems(self.md), [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fo.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_c02_odd.py")

  def test_build_is_deterministic(self):
    self.assertEqual(fo.build(self.md), self.out)

  def test_svgs_valid_with_role_title_desc(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), "1280", name)
      self.assertTrue(root.find(f"{NS}title").text.startswith("Figure 3-"), name)
      self.assertTrue(root.find(f"{NS}desc").text, name)

  def test_curve_table_equals_formulas(self):
    # §3.2: R_ctrl = v²/3.0, R_ODD = v²/2.5, v in m/s, the table rounding to whole metres and 0.1 m/s
    rows = fo.curve_table(self.md)
    self.assertEqual([r[0] for r in rows], [40, 60, 80, 100, 120])
    for kmh, ms, rc, ro in rows:
      v = kmh / 3.6
      self.assertEqual(round(v, 1), ms, kmh)
      self.assertEqual(round(v * v / 3.0), rc, kmh)
      self.assertEqual(round(v * v / 2.5), ro, kmh)
    self.assertAlmostEqual(fo.PROSE["a_ctrl"]["value"] - fo.PROSE["a_odd"]["value"], fo.PROSE["margin"]["value"])

  def test_envelope_draws_table_points(self):
    svg = self.out["fig-c02-3-2-odd-envelope.svg"]
    for _kmh, _ms, rc, ro in fo.curve_table(self.md):
      self.assertIn(f">{rc} m<", svg)
      self.assertIn(f">{ro} m<", svg)
    self.assertIn("assumes AOU-01 (unverified)", svg)
    self.assertIn("proposed, not approved", svg)

  def test_taxonomy_has_every_row_and_flags(self):
    svg = self.out["fig-c02-3-1-odd-taxonomy.svg"]
    rows = fo.taxonomy(self.md)
    self.assertEqual(len(rows), 24)
    for r in rows:
      self.assertIn(f">{r['cat']}<".replace("&", "&amp;"), svg)
    for _kind, tag, _src in fo.FLAGS.values():
      self.assertIn(f">{tag}<", svg)
    # the TBD row is drawn as a placeholder (hatched), never as a number
    self.assertEqual(len(re.findall(r'fill="url\(#hatch-amber\)" stroke="#D97706"', svg)), 2)  # value box + legend

  def test_nothing_drawn_as_verified(self):
    # nothing in §3 is verified, so the status green of the style guide must not appear
    for name, content in self.out.items():
      self.assertNotIn("#2E9E6A", content.upper(), name)


if __name__ == "__main__":
  unittest.main()
