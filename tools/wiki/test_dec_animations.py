#!/usr/bin/env python3
"""Unit tests for dec_animations.py: the records each figure stands on, the values read from them, the figures and the build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import dec_animations as D


def copy_records(root: Path) -> None:
  for path in {p for p, _ in D.SOURCES} | {D.A01, D.H04, D.S02}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(D.ROOT / path, root / path)


def edit(root: Path, path: Path, old: str, new: str) -> None:
  f = root / path
  text = f.read_text(encoding="utf-8")
  assert old in text, old
  f.write_text(text.replace(old, new), encoding="utf-8")


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(D.problems(), [])

  def test_values_are_read_from_the_records(self):
    d = D.data()
    self.assertEqual(tuple(d["irs"]), D.IRS)
    self.assertEqual(d["recs"]["DEC-01"], "Proposed")
    self.assertEqual({d["recs"][k] for k in ("DEC-02", "DEC-03", "DEC-04")}, {"Withdrawn"})
    self.assertLess(d["spfm"], d["target"])

  def test_the_schemes_add_up(self):
    for orig, splits in D.SCHEMES:
      for a, c in splits:
        self.assertEqual(D.LEVEL[a] + D.LEVEL[c], D.LEVEL[orig], (orig, a, c))

  def test_an_applied_decomposition_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      edit(root, D.A01, "| **Proposed (fallback, not applied)** |", "| **Applied** |")
      self.assertTrue(any("changed status" in e for e in D.problems(root)))

  def test_a_met_target_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      edit(root, D.H04, "SPFM 96.84 % on the shared generic-rate estimate, 0.16 points below 97 %",
           "SPFM 97.20 % on the shared generic-rate estimate, 0.16 points below 97 %")
      self.assertTrue(any("likely missed" in e for e in D.problems(root)))

  def test_a_new_independence_requirement_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      edit(root, D.A01, "\n![Figure 4-1", "| IR-11 | A new rule | x | y |\n\n![Figure 4-1")
      self.assertTrue(any("IR-11" in e for e in D.problems(root)))


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = D.render()
    self.assertEqual(tuple(out), D.NAMES)
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)
      self.assertNotIn("mock-up", text.lower())

  def test_the_decision_shows_the_record_values(self):
    svg = D.render()["dec-liondriver.svg"]
    d = D.data()
    self.assertIn(f"{d['spfm']:g} % against {d['target']:g} %", svg)
    self.assertIn("Proposed", svg)

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as tmp:
      out = Path(tmp) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "ASIL-decomposition.md").read_text(encoding="utf-8")
      for name in D.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
