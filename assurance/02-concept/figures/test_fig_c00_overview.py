#!/usr/bin/env python3
"""Tests for fig_c00_overview.py: the counts and the HE-01.2 thread are read from the documents, the drawn order follows
concept.yaml, and the committed figures, thumbnail and index-top.md are current."""

import copy
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c00_overview as fo

NS = "{http://www.w3.org/2000/svg}"


class TestConceptOverview(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.acts, cls.ixs = fo.activities(), fo.interfaces()
    cls.c, cls.d = fo.counts(), fo.chain()
    cls.out = fo.build()

  def test_committed_outputs_current(self):
    for path, content in self.out.items():
      self.assertTrue(path.exists(), path.name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run fig_c00_overview.py")

  def test_order_follows_the_process_model(self):
    self.assertEqual(fo.flow_problems(self.acts, self.ixs), [])
    self.assertEqual(fo.problems(), [])

  def test_counts_are_table_rows(self):
    # defined rows, not mentions: SH-07 is a placeholder row, SG-09 only a proposal in a variant
    self.assertEqual(self.c["SG"], 8)
    self.assertEqual(self.c["HE"], 39)
    for k in ("SH", "FI", "TC", "FM", "TS", "CSG", "AIR", "FSR"):
      self.assertGreater(self.c[k], 0, k)

  def test_thread_values_come_from_the_documents(self):
    d = self.d
    self.assertEqual((d["s"], d["e"], d["asil"]), ("S3", "E4", "C"))
    self.assertTrue(d["c"].startswith("C2"))
    self.assertEqual(d["fallback"], "D")
    self.assertTrue(d["sg_asil"].startswith("C"))
    self.assertEqual([f["id"] for f in d["fsrs"]], [f for f, _l, _w in fo.CHAIN_FSR])
    self.assertIn("E-03", d["elements"])
    svg = self.out[fo.HERE / fo.OUT_D]
    for v in (fo.CHAIN_HE, fo.CHAIN_SG, d["situation"].split(",")[0], *(f["id"] for f in d["fsrs"])):
      self.assertIn(v, svg)

  def test_broken_chain_fails(self):
    old = fo.CHAIN_SG
    try:
      fo.CHAIN_SG = "SG-03"
      with self.assertRaises(fo.OverviewError):
        fo.chain()
    finally:
      fo.CHAIN_SG = old

  def test_changed_requirement_text_fails(self):
    old = fo.CHAIN_FSR
    try:
      fo.CHAIN_FSR = [("FSR-01.01", "x", "words that are not there")]
      with self.assertRaises(fo.OverviewError):
        fo.chain()
    finally:
      fo.CHAIN_FSR = old

  def test_new_g1_interface_needs_a_label(self):
    ixs = copy.deepcopy(self.ixs) + [{"id": "IX-99", "between": ["WP-C-03", "WP-C-11"]}]
    self.assertTrue(any("IX-99" in e for e in fo.flow_problems(self.acts, ixs)))

  def test_wrong_arrow_fails(self):
    acts = copy.deepcopy(self.acts)
    acts["WP-C-04"]["inputs"] = [i for i in acts["WP-C-04"]["inputs"] if i != "WP-C-03"]
    self.assertTrue(any("WP-C-03 → WP-C-04" in e for e in fo.flow_problems(acts, self.ixs)))

  def test_svgs_accessible(self):
    for name in (fo.OUT_A, fo.OUT_D):
      root = ET.fromstring(self.out[fo.HERE / name])
      self.assertTrue(root.find(f"{NS}title").text)
      self.assertTrue(root.find(f"{NS}desc").text)
      self.assertEqual(root.get("width"), str(fo.W))
      self.assertIn("prefers-color-scheme: dark", self.out[fo.HERE / name])

  def test_readme_opens_with_the_section(self):
    readme = (fo.CONCEPT / "README.md").read_text(encoding="utf-8")
    i = readme.find("## The concept phase at a glance")
    self.assertGreater(i, 0)
    self.assertLess(i, readme.find("## Work products"))


if __name__ == "__main__":
  unittest.main()
