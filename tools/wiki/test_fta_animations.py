#!/usr/bin/env python3
"""Unit tests for fta_animations.py: every drawn fact is in its source, and the figures are well formed."""
from __future__ import annotations

import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import fta_animations


class SourceTests(unittest.TestCase):
  def test_every_drawn_fact_is_in_the_real_sources(self):
    self.assertEqual(fta_animations.problems(), [])

  def test_a_changed_tree_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      for rel in (fta_animations.FTA, fta_animations.ITEM, fta_animations.TSC):
        text = (fta_animations.ROOT / rel).read_text(encoding="utf-8")
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text.replace("| MCS-02.5 | 1 (effective) | {BE-2.05} |", "| MCS-02.5 | 2 | {BE-2.05, BE-2.15} |"),
                                encoding="utf-8")
      errs = fta_animations.problems(root)
      self.assertTrue(any("MCS-02.5" in e for e in errs), errs)


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = fta_animations.render()
    self.assertEqual(set(out), set(fta_animations.NAMES))
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)

  def test_gates_are_the_wp_a04_symbols(self):
    text = fta_animations.render()["fta-symbols.svg"]
    self.assertIn("A20,18 0 0 1", text)             # the AND gate's arc
    self.assertIn('r="16"', text)                   # the basic-event circle
    self.assertEqual(text.count("<path d=\"M"), 4)  # OR, AND, diamond, triangle

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "Building-a-fault-tree.md").read_text(encoding="utf-8")
      for name in fta_animations.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
