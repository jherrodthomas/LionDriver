#!/usr/bin/env python3
"""Unit tests for p7_animations.py: the records each step stands on, the figures and the wiki build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import p7_animations as P


class RecordTests(unittest.TestCase):
  def test_every_step_stands_on_its_record(self):
    self.assertEqual(P.problems(), [])

  def test_a_closed_open_item_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      for _, _, lines in P.OURS:
        for _, _, refs in lines:
          for path, _ in refs:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(P.ROOT / path, root / path)
      f = root / P.O02
      f.write_text(f.read_text(encoding="utf-8").replace("| OI-7 | Specify how", "| OI-7 | ~~Specify how"), encoding="utf-8")
      self.assertTrue(any("Rollback" in e for e in P.problems(root)))

  def test_every_step_that_is_not_in_place_has_a_short_name(self):
    for _, _, lines in P.OURS:
      for line, status, _ in lines:
        if status != P.OK:
          self.assertIn(line, P.SHORT)


class RenderTests(unittest.TestCase):
  def test_both_render_to_well_formed_accessible_svg(self):
    for name, text in P.render().items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)

  def test_the_general_figure_carries_no_clause_numbers(self):
    import re
    self.assertIsNone(re.search(r"\b\d+\.\d+\.\d+\b|§", P.render()["p7-general.svg"]))

  def test_the_wiki_build_writes_both_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "After-release.md").read_text(encoding="utf-8")
      for name in P.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
