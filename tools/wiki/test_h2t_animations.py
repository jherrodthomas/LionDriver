#!/usr/bin/env python3
"""Unit tests for h2t_animations.py: the records it quotes, the figures, and the wiki build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import h2t_animations as H


def copy_sources(tmp: Path) -> Path:
  root = tmp / "repo"
  for path in {p for p, _ in H.SOURCES}:
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(H.ROOT / path, root / path)
  shutil.copytree(H.ROOT / H.CASE, root / H.CASE)
  return root


class SourceTests(unittest.TestCase):
  def test_every_quoted_record_is_in_the_real_sources(self):
    self.assertEqual(H.problems(), [])

  def test_a_reworded_requirement_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = copy_sources(Path(d))
      f = root / H.S02
      f.write_text(f.read_text(encoding="utf-8").replace("shall reject every `0x2E4` frame", "shall drop each `0x2E4` frame"), encoding="utf-8")
      self.assertTrue(any("TSR-105" in e for e in H.problems(root)))

  def test_missing_submodules_skip_the_code_check(self):
    with tempfile.TemporaryDirectory() as d:
      self.assertEqual(H.problems(copy_sources(Path(d))), [])


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = H.render()
    self.assertEqual(set(out), set(H.NAMES))
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)

  def test_the_mechanism_is_labelled_an_illustration(self):
    self.assertIn(">ILLUSTRATION<", H.render()["h2t-mechanism.svg"])

  def test_test_statuses_come_from_the_case_records(self):
    _, ev = H.case()
    text = H.render()["h2t-testing.svg"]
    for e in ev.values():
      self.assertIn(f"{e['evidence_status']} · {e['review_state'].replace('-', ' ')}", text)

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "From-hazard-to-test.md").read_text(encoding="utf-8")
      for name in H.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
