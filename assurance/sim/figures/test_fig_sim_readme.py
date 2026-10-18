#!/usr/bin/env python3
"""Tests for fig_sim_readme.py: source texts still in the sim README, SVGs current, figures embedded, hero strip small."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_sim_readme as fs

NS = "{http://www.w3.org/2000/svg}"


class TestSimReadmeFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fs.README.read_text(encoding="utf-8")
    cls.out = fs.build()

  def test_no_source_problems(self):
    self.assertEqual(fs.problems(self.md), [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fs.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_sim_readme.py")

  def test_build_is_deterministic(self):
    self.assertEqual(fs.build(), self.out)

  def test_svgs_valid_phone_width_with_title_desc_and_dark_theme(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), str(fs.W), name)
      self.assertTrue(root.find(f"{NS}title").text, name)
      self.assertTrue(root.find(f"{NS}desc").text, name)
      self.assertIn("prefers-color-scheme: dark", content, name)
      self.assertLess(len(content.encode()), 20_000, f"{name}: keep the SVG small")

  def test_every_figure_says_synthetic(self):
    for name, content in self.out.items():
      self.assertIn("Synthetic (DSR-12)", content, name)

  def test_open_items_figure_equals_table(self):
    table = fs.open_items(self.md)
    self.assertIn("SIM-OI-1", table)
    self.assertTrue(table["SIM-OI-9"])
    svg = self.out["fig-sim-r7-open.svg"]
    for oid in table:
      self.assertIn(f">{oid}<", svg)

  def test_no_text_wider_than_figure(self):
    # the width estimate is what the layout wraps by; no single line may run past the right margin
    for name, content in self.out.items():
      for m in re.finditer(r'<text x="([\d.]+)" y="[\d.]+" class="(\w+)"( text-anchor="(\w+)")?[^>]*>([^<]*)</text>', content):
        x, cls, anchor, s = float(m.group(1)), m.group(2), m.group(4), m.group(5)
        if "rotate" in m.group(0):
          continue
        w = fs.width(s.replace("&amp;", "&"), cls)
        right = x + (w / 2 if anchor == "middle" else 0 if anchor == "end" else w)
        self.assertLessEqual(right, fs.W - 8, f"{name}: {s!r} overruns")

  def test_readme_embeds_every_figure_and_the_hero(self):
    for name in list(self.out) + [fs.HERO.name]:
      self.assertIn(f"](figures/{name})", self.md, name)

  def test_hero_strip_small_and_sized(self):
    self.assertLess(fs.HERO.stat().st_size, fs.HERO_MAX_BYTES)
    self.assertEqual(fs.jpeg_size(fs.HERO), fs.hero_size())


if __name__ == "__main__":
  unittest.main()
