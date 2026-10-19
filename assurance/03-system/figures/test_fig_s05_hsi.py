#!/usr/bin/env python3
"""Tests for fig_s05_hsi.py: every §2 interface placed, committed SVG current, cards carry the §2 ASIL."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s05_hsi as fh


class TestHsiFigure(unittest.TestCase):
  def setUp(self):
    self.md = fh.SOURCE.read_text(encoding="utf-8")

  def test_every_interface_placed(self):
    self.assertEqual(fh.problems(self.md), [])

  def test_committed_output_current(self):
    self.assertEqual((fh.HERE / fh.OUT).read_text(encoding="utf-8"), fh.build(self.md), "stale; run fig_s05_hsi.py")

  def test_svg_parses_and_has_title(self):
    root = ET.fromstring(fh.build(self.md))
    self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))

  def test_each_card_shows_id_and_asil(self):
    svg = fh.build(self.md)
    for r in fh.interfaces(self.md):
      self.assertIn(f">{r['id']}<", svg)
      self.assertIn(f">{r['asil'].replace(' (+CS)', ' + CS')}<", svg)

  def test_new_row_detected(self):
    md = self.md.replace("| HSI-14 |", "| HSI-15 |", 1)
    self.assertIn("HSI-15: in WP-S-05 §2 but not placed in fig_s05_hsi.PLACE", fh.problems(md))

  def test_plain_drops_parentheticals(self):
    self.assertEqual(fh.plain("IWDG1 (window mode, 90 ms (nominal)), software `check`"), "IWDG1, software check")


if __name__ == "__main__":
  unittest.main()
