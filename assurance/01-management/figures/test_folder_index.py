#!/usr/bin/env python3
"""Tests for folder_index.py: pages and figures current, every register row listed, links valid, drift detected."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import folder_index as fi

NS = "{http://www.w3.org/2000/svg}"


class TestFolderIndex(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out = fi.build()

  def test_committed_outputs_current_and_deterministic(self):
    for p, c in self.out.items():
      self.assertTrue(p.exists(), p)
      self.assertEqual(p.read_text(encoding="utf-8"), c, f"{p} is stale; run folder_index.py")
    self.assertEqual(fi.build(), self.out)

  def test_every_phase_folder_has_a_page(self):
    for folder in fi.FOLDERS:
      self.assertIn(fi.ASSURANCE / folder / "README.md", self.out)
    self.assertIn("00-assessment", fi.FOLDERS)
    self.assertIn("10-safety-case", fi.FOLDERS)

  def test_every_register_row_listed_and_drawn(self):
    regs, _ = fi.register_rows()
    for folder, (_t, items) in regs.items():
      if folder not in fi.FOLDERS:
        continue
      page = self.out[fi.ASSURANCE / folder / "README.md"]
      svg = self.out[fi.ASSURANCE / folder / fi.SVG_NAME]
      for it in items:
        self.assertIn(f"[{it['id']}](", page, f"{folder}: {it['id']}")
        self.assertIn(f">{it['id']}<", svg, f"{folder}: {it['id']}")

  def test_svgs_valid_phone_width_dark_theme(self):
    for p, c in self.out.items():
      if p.suffix != ".svg":
        continue
      root = ET.fromstring(c)
      self.assertEqual(root.get("role"), "img")
      self.assertEqual(root.get("width"), str(fi.W))
      self.assertTrue(root.find(f"{NS}desc").text)
      self.assertIn("prefers-color-scheme: dark", c)

  def test_relative_links_resolve(self):
    for p, c in self.out.items():
      if p.suffix != ".md":
        continue
      for url in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", c):
        if not re.match(r"[a-z]+:", url):
          self.assertTrue((p.parent / url).exists(), f"{p}: {url}")

  def test_no_problems(self):
    self.assertEqual(fi.problems(self.out), [])

  def test_rebase(self):
    self.assertEqual(fi.rebase("[a](00-assessment/x.md)", "00-assessment"), "[a](x.md)")
    self.assertEqual(fi.rebase("[a](01-management/y.md#s)", "05-software"), "[a](../01-management/y.md#s)")
    self.assertEqual(fi.rebase("[a](https://e.org/x)", "05-software"), "[a](https://e.org/x)")

  def test_missing_layout_row_fails(self):
    lay = fi.layout()
    lay.pop("09-production-operation")
    regs, reg = fi.register_rows()
    with self.assertRaises(fi.FigureError):
      fi.page("09-production-operation", lay, regs, reg)


if __name__ == "__main__":
  unittest.main()
