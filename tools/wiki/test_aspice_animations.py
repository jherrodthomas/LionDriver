#!/usr/bin/env python3
"""Unit tests for aspice_animations.py: the records each figure stands on, the computed values, the figures and the build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aspice_animations as A
import build_wiki


def copy_records(root: Path) -> None:
  for path in {p for p, _ in A.SOURCES} | {A.M13, A.MAP}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(A.ROOT / path, root / path)
  shutil.copytree(A.ROOT / A.MODEL, root / A.MODEL)


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(A.problems(), [])

  def test_values_are_read_from_the_records(self):
    d = A.data()
    self.assertIn(("SWE.4", "1/0", 2, "A"), d["base"])
    self.assertTrue(set(d["moved_ias"]) <= set(d["ias"]))
    self.assertEqual(d["cl1"], sum(1 for b in d["base"] if b[1].startswith("1")))
    self.assertTrue(all(n <= den for _, _, n, den in d["coverage"]))

  def test_a_new_rating_moves_on_the_map(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / A.M13
      f.write_text(f.read_text(encoding="utf-8").replace("| SYS.1 | 0 | 2 | 2 |", "| SYS.1 | 1 | 2 | 1 |"), encoding="utf-8")
      self.assertIn(("SYS.1", "1", 2, "A"), A.data(root)["base"])

  def test_a_missing_coverage_row_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / A.MAP
      f.write_text(f.read_text(encoding="utf-8").replace("| FSR -> TSR |", "| FSR => TSR |"), encoding="utf-8")
      self.assertTrue(any("FSR -> TSR" in e for e in A.problems(root)))


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

  def test_the_self_assessment_is_called_one(self):
    self.assertIn("self-assessment", A.render()["aspice-question.svg"].lower())

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "ASPICE-process-capability.md").read_text(encoding="utf-8")
      for name in A.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
