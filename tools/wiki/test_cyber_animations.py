#!/usr/bin/env python3
"""Unit tests for cyber_animations.py: the records each figure stands on, the computed values, the figures and the build."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import cyber_animations as C


def copy_records(root: Path) -> None:
  for path in {p for p, _ in C.SOURCES} | {C.C09, C.C10, C.IX}:
    if (C.ROOT / path).exists():
      (root / path).parent.mkdir(parents=True, exist_ok=True)
      shutil.copy(C.ROOT / path, root / path)


class RecordTests(unittest.TestCase):
  def test_every_figure_stands_on_its_records(self):
    self.assertEqual(C.problems(), [])

  def test_a_re_rated_threat_moves_on_the_map(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      copy_records(root)
      f = root / C.C09
      f.write_text(f.read_text(encoding="utf-8").replace("| TS-13 | 3 | Medium | **3** |", "| TS-13 | 3 | Low | **2** |"), encoding="utf-8")
      self.assertIn("TS-13", [ts for ts, _ in C.data(root)["cells"][(3, "Low")]])
      self.assertEqual(C.problems(root), [])

  def test_a_risk_that_contradicts_the_matrix_is_reported(self):
    with tempfile.TemporaryDirectory() as d:
      root = Path(d)
      copy_records(root)
      f = root / C.C09
      f.write_text(f.read_text(encoding="utf-8").replace("| TS-13 | 3 | Medium | **3** |", "| TS-13 | 3 | Medium | **5** |"), encoding="utf-8")
      self.assertTrue(any("TS-13" in e for e in C.problems(root)))

  def test_computed_values(self):
    d = C.data()
    self.assertEqual(d["ix_hurt"] + d["ix_help"] + d["ix_hold"], d["ix"])
    self.assertEqual(sum(len(v) for v in d["cells"].values()), d["ts"])
    self.assertEqual(d["ap"]["AP-02"][1], "High")
    self.assertLessEqual(d["ds_hara"], d["ds"])


class RenderTests(unittest.TestCase):
  def test_all_render_to_well_formed_accessible_svg(self):
    out = C.render()
    self.assertEqual(tuple(out), C.NAMES)
    for name, text in out.items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)
      self.assertIn("prefers-reduced-motion: reduce", text)
      self.assertNotIn("MOCK-UP", text)

  def test_the_example_report_is_labelled(self):
    self.assertIn("EXAMPLE, NOT A REAL REPORT", C.render()["cyber-after-release.svg"])

  def test_the_wiki_build_writes_all_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "Cybersecurity-and-ISO-21434.md").read_text(encoding="utf-8")
      for name in C.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
