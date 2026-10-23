#!/usr/bin/env python3
"""Unit tests for sotif_animations.py: the records each figure stands on, the counts, the figures and the wiki build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import sotif_animations as S


def copy_records(root: Path) -> None:
  for path in {p for p, _ in S.SOURCES} | {S.FIG / "fig_c05_four_areas.py"}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(S.ROOT / path, root / path)


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(S.problems(), [])

  def test_a_changed_rating_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      copy_records(root)
      f = root / S.C06
      f.write_text(f.read_text(encoding="utf-8").replace("Needs modification (ODD bound + authority", "Needs validation (ODD bound + authority"),
                   encoding="utf-8")
      self.assertTrue(any("TC-14" in e for e in S.problems(root)))

  def test_counts_follow_the_tables(self):
    c = S.counts()
    self.assertEqual(c["mod"] + c["val"] + c["acc"], c["rows"])
    svg = S.render()["sotif-triggering.svg"]
    self.assertIn(f"{c['tc']} triggering conditions, {c['fi']} insufficiencies", svg)


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = S.render()
    self.assertEqual(tuple(out), S.NAMES)
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)
      self.assertNotIn("MOCK-UP", text)

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "SOTIF-and-ISO-26262.md").read_text(encoding="utf-8")
      for name in S.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
