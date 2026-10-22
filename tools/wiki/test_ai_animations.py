#!/usr/bin/env python3
"""Unit tests for ai_animations.py: the records each figure stands on, the computed values, the figures and the build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_animations as A
import build_wiki


def copy_records(root: Path) -> None:
  for path in {p for p, _ in A.SOURCES}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(A.ROOT / path, root / path)


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(A.problems(), [])

  def test_statuses_are_read_from_the_record(self):
    d = A.data()
    self.assertEqual(len(d["groups"]), len(A.GROUP_NAMES))
    self.assertEqual(sum(len(g) for g in d["groups"]), d["n_air"])
    self.assertEqual(d["air"]["AIR-20"], "nm")
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / A.C11
      text = f.read_text(encoding="utf-8")
      line = next(l for l in text.splitlines() if l.startswith("| AIR-20 "))
      f.write_text(text.replace(line, line.rsplit("|", 2)[0] + "| Met: artefacts loaded from a non-executable format |"), encoding="utf-8")
      self.assertEqual(A.data(root)["air"]["AIR-20"], "ok")

  def test_an_unknown_status_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / A.C11
      text = f.read_text(encoding="utf-8")
      line = next(l for l in text.splitlines() if l.startswith("| AIR-01 "))
      f.write_text(text.replace(line, line.rsplit("|", 2)[0] + "| Somewhat |"), encoding="utf-8")
      self.assertTrue(any("status not recognised" in e for e in A.problems(root)))

  def test_monitor_statuses_follow_their_requirements(self):
    out = A.render()["ai-layers.svg"]
    d = A.data()
    for _, _, air in A.MONITORS:
      self.assertIn(A.STATUS[d["air"][air]][0], out)


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = A.render()
    self.assertEqual(tuple(out), A.NAMES)
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
      page = (out / "AI-safety-and-ISO-PAS-8800.md").read_text(encoding="utf-8")
      for name in A.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
