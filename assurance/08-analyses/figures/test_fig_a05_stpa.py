#!/usr/bin/env python3
"""Tests for fig_a05_stpa.py: sources parse, committed SVGs current, every figure referenced in WP-A-05, unknown IDs rejected."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_a05_stpa as fs


class TestRealSources(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.S = fs.load()
    cls.out = fs.build()

  def test_tables_parsed(self):
    self.assertEqual(sorted(self.S.losses), ["L-1", "L-2", "L-3", "L-4"])
    self.assertIn("H-STPA-1", self.S.hazards)
    self.assertEqual(set(self.S.ucas), {u for u in self.S.ids if u.startswith("UCA-")})
    self.assertEqual(set(self.S.ls_type), set(self.S.scen))

  def test_every_uca_has_a_known_controller_and_type(self):
    for uid, u in self.S.ucas.items():
      self.assertIn(u["type"], ("N", "P", "T", "D"), uid)
      self.assertRegex(u["ctrl"], r"^C\d", uid)

  def test_committed_output_current(self):
    for name, content in self.out.items():
      p = fs.HERE / name
      self.assertTrue(p.exists(), name)
      self.assertEqual(p.read_text(encoding="utf-8"), content, f"{name} stale; run fig_a05_stpa.py")

  def test_svgs_parse_with_title_and_desc(self):
    ns = "{http://www.w3.org/2000/svg}"
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertIsNotNone(root.find(ns + "title"), name)
      self.assertIsNotNone(root.find(ns + "desc"), name)

  def test_every_figure_is_referenced_in_wp_a05(self):
    doc = fs.SOURCE.read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"figures/{name}", doc, name)

  def test_figure_numbers_match_file_names(self):
    for name, content in self.out.items():
      num = re.match(r"fig-a05-(\d+)-(\d+)-", name).groups()
      self.assertIn(f"Figure {num[0]}-{num[1]}.", content, name)


class TestRejects(unittest.TestCase):
  def test_unknown_id_fails(self):
    S = fs.load()
    with self.assertRaises(fs.ParseError):
      S.need("LS-999")
    with self.assertRaises(fs.ParseError):
      S.need("DQ-999")
    with self.assertRaises(fs.ParseError):
      S.need("CA-99")

  def test_figure_3_1_must_draw_every_vehicle_level_action(self):
    S = fs.load()
    self.assertEqual({e[0] for e in fs.F31_EDGES}, fs.vehicle_level_ids(S))
    saved = fs.F31_EDGES
    try:
      fs.F31_EDGES = [e for e in saved if e[0] != "CA-13"]
      with self.assertRaises(fs.ParseError):
        fs.fig_3_1(S)
    finally:
      fs.F31_EDGES = saved

  def test_missing_tables_fail(self):
    with self.assertRaises(fs.ParseError):
      fs.Sources("# empty", {"scenarios": []}, [])


if __name__ == "__main__":
  unittest.main()
