#!/usr/bin/env python3
"""Unit tests for case_animations.py: the records it relies on, the figures, and the wiki build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import case_animations as C


def copy_sources(tmp: Path) -> Path:
  root = tmp / "repo"
  shutil.copytree(C.ROOT / C.CASE, root / C.CASE)
  for path, _ in C.SUMMARIES:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(C.ROOT / path, root / path)
  return root


class SourceTests(unittest.TestCase):
  def test_the_real_records_have_everything_the_figures_rely_on(self):
    self.assertEqual(C.problems(), [])

  def test_a_closed_example_defeater_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = copy_sources(Path(d))
      f = root / C.CASE / "defeaters" / "defeaters.yaml"
      text = f.read_text(encoding="utf-8")
      i = text.index(f"id: {C.DEFEATER}")
      j = text.index("lifecycle_status: open", i)
      f.write_text(text[:j] + "lifecycle_status: closed" + text[j + len("lifecycle_status: open"):], encoding="utf-8")
      self.assertTrue(any(C.DEFEATER in e for e in C.problems(root)))

  def test_a_reworded_rule_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = copy_sources(Path(d))
      f = root / C.CASE / "README.md"
      f.write_text(f.read_text(encoding="utf-8").replace("no defeater attached to it is open", "no blocker"), encoding="utf-8")
      self.assertTrue(any("no defeater attached" in e for e in C.problems(root)))


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = C.render()
    self.assertEqual(set(out), set(C.NAMES))
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)

  def test_counts_come_from_the_records(self):
    n = C.counts(C.load())
    out = C.render()
    self.assertIn(f"Today: {n['evidence']} evidence items, {n['ev_accepted']} accepted", out["case-evidence.svg"])
    self.assertIn(f"Today: {n['df_open']} open defeaters", out["case-defeaters.svg"])
    self.assertIn(f"{n['claims']} claims in all", out["case-claim-tree.svg"])

  def test_fit_cuts_with_an_ellipsis(self):
    self.assertEqual(C.fit("Process, confirmation and operation", 19, 1), ["Process, confirmat…"])
    self.assertEqual(C.fit("Envelope faults reach the safe state in the FTTI", 23, 3),
                     ["Envelope faults reach", "the safe state in the", "FTTI"])

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "What-is-a-safety-case.md").read_text(encoding="utf-8")
      for name in C.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
