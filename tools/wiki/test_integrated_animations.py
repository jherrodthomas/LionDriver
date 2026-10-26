#!/usr/bin/env python3
"""Unit tests for integrated_animations.py: the records each figure stands on, the computed values, the figures and the build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import integrated_animations as I


def copy_records(root: Path) -> None:
  for path in {p for p, _ in I.SOURCES} | {I.REG, I.HARA, I.TARA, I.MAP, I.IFR}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(I.ROOT / path, root / path)
  shutil.copytree(I.ROOT / I.MODEL, root / I.MODEL, dirs_exist_ok=True)
  shutil.copytree(I.ROOT / I.CASE, root / I.CASE, dirs_exist_ok=True)


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(I.problems(), [])

  def test_values_are_read_from_the_records(self):
    d = I.data()
    self.assertEqual(sum(d["lanes"].values()), d["activities"])
    self.assertEqual(d["unlaned"], 0)
    self.assertIn("WP-C-03", {r[1] for r in d["reg"]})
    self.assertTrue(all(len(f) == 5 for _, _, f in d["reg"]))
    self.assertEqual([n for n, _, _ in d["trace"]][0], "ISO 26262")
    self.assertTrue(all(traced for _, traced in d["trace"][0][2]))

  def test_the_hazard_log_agrees_with_the_tara(self):
    log = {h: (sh, ds, flag) for h, sh, ds, flag in I.data()["log"]}
    self.assertIn("DS-04", log["H-04"][1])
    self.assertIn("DS-14", log["H-09"][1])
    self.assertEqual([h for h, (_, _, flag) in log.items() if flag], [])

  def test_a_hazard_the_tara_reaches_but_the_log_does_not_is_flagged(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / I.HARA
      text = f.read_text(encoding="utf-8")
      row = next(line for line in text.splitlines() if line.startswith("| H-04 "))
      f.write_text(text.replace(row, "| H-04 | SH-04 (phantom braking) | — | FSR-04.x |"), encoding="utf-8")
      flags = {h: flag for h, _, _, flag in I.data(root)["log"]}
      self.assertIn("DS-04", flags["H-04"])

  def test_a_new_lane_is_a_problem(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp)
      copy_records(root)
      f = root / I.MODEL / "concept.yaml"
      f.write_text(f.read_text(encoding="utf-8").replace("lane: joint", "lane: newlane", 1), encoding="utf-8")
      self.assertTrue(any("LANES" in e for e in I.problems(root)))


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = I.render()
    self.assertEqual(tuple(out), I.NAMES)
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)
      self.assertNotIn("mock-up", text.lower())

  def test_served_names_the_standards(self):
    self.assertEqual(I.served([True] * 5), "all five")
    self.assertEqual(I.served([True, False, False, False, False]), "ISO 26262 only")
    self.assertEqual(I.served([True, True, False, False, False]), "ISO 26262, ISO 21448")

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "Integrated-standards.md").read_text(encoding="utf-8")
      for name in I.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
