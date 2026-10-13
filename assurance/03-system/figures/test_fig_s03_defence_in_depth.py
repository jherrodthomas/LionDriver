#!/usr/bin/env python3
"""Tests for fig_s03_defence_in_depth.py: committed SVG current, well-formed, and its numbers equal the trace data."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s03_defence_in_depth as fd

SVG_NS = "{http://www.w3.org/2000/svg}"


class TestDefenceInDepth(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.items = fd.load_items()
    cls.model = fd.build_model(cls.items)

  def test_source_texts_present(self):
    self.assertEqual(fd.missing_sources(self.items), [])

  def test_committed_output_current(self):
    for name, content in fd.build().items():
      path = fd.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s03_defence_in_depth.py")

  def test_deterministic(self):
    self.assertEqual(fd.build(), fd.build())

  def test_svg_parses_with_role_title_desc(self):
    for name, content in fd.build().items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertIsNotNone(root.find(f"{SVG_NS}title"), name)
      self.assertTrue((root.findtext(f"{SVG_NS}desc") or "").strip(), name)

  def test_one_row_per_goal_with_its_asil(self):
    goals = {i: it["asil"] for i, it in self.items.items() if it["kind"] == "safety-goal"}
    self.assertEqual({r["id"]: r["asil"] for r in self.model["rows"]}, goals)

  def test_counts_equal_trace_data(self):
    # independent recount for SG-07: walk parents upwards from every TSR
    def reaches(iid, goal, seen=()):
      for p in self.items[iid].get("parents") or []:
        if p == goal or (p in self.items and p not in seen and self.items[p]["kind"] in ("fsr", "tsr")
                         and reaches(p, goal, (*seen, p))):
          return True
      return False
    row = next(r for r in self.model["rows"] if r["id"] == "SG-07")
    tsrs = [t for t, it in self.items.items() if it["kind"] == "tsr" and reaches(t, "SG-07")]
    for key, tokens in (("host", {"SoC"}), ("envelope", {"P-SW", "P-HW", "HAR"}), ("ops", {"OPS"})):
      expect = sorted(t for t in tsrs if fd.allocation(self.items[t]) & tokens)
      self.assertEqual(row["cells"][key]["tsrs"], expect, key)
    svg = fd.build()[fd.OUT]
    for key in ("host", "envelope"):
      self.assertIn(f">{len(row['cells'][key]['tsrs'])} TSRs", svg)

  def test_classification_rule(self):
    st = self.model["status"]
    self.assertEqual(st["TSR-111"], "assumed")       # EXT, "Unverified (AOU-01R, GAP-05)"
    self.assertEqual(st["TSR-103"], "partly")        # "Implemented without rationale"
    self.assertEqual(st["TSR-512"], "partly")        # "Met in the reference build"
    self.assertEqual(st["TSR-301"], "implemented")   # "Implemented: `safety.h:518-527`"
    self.assertEqual(st["TSR-102"], "not")           # "Not implemented for Toyota"
    self.assertEqual(st["TSR-802"], "not")           # OPS, "Blocked in substance"

  def test_never_green(self):
    svg = fd.build()[fd.OUT]
    self.assertNotIn("#2E9E6A", svg)
    self.assertFalse(re.search(r">\s*verified\s*<", svg))


if __name__ == "__main__":
  unittest.main()
