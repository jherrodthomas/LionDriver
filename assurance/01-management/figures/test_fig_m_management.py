#!/usr/bin/env python3
"""Tests for fig_m_management.py: source texts present, committed SVGs current, valid, and drawn from the tables."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_m_management as fm

NS = "{http://www.w3.org/2000/svg}"


class TestManagementFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.outputs = fm.build()
    cls.reg = fm.load_register()
    cls.risks = fm.load_risks()
    cls.profile = fm.load_profile()

  def test_source_texts_present(self):
    self.assertEqual(fm.missing_sources(), [])

  def test_committed_outputs_current(self):
    for name, content in self.outputs.items():
      path = fm.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_m_management.py")

  def test_deterministic(self):
    self.assertEqual(fm.build(), self.outputs)

  def test_svgs_valid_with_role_title_desc(self):
    for name, content in self.outputs.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), "1280", name)
      self.assertTrue(root.find(f"{NS}title").text.startswith("Figure "), name)
      self.assertTrue(root.find(f"{NS}desc").text, name)

  def test_m00_every_register_row_drawn(self):
    md = fm.WP_M_00.read_text(encoding="utf-8")
    rows = re.findall(r"^\| \[(WP-[A-Z]-\d+)\]\(.*\| (\S+) \|$", md, re.M)
    self.assertEqual([w.wid for w in self.reg.products], [r[0] for r in rows])
    self.assertEqual(Counter(w.status for w in self.reg.products), Counter(r[1] for r in rows))
    svg = self.outputs["fig-m00-3-1-wp-status.svg"]
    for w in self.reg.products:
      self.assertIn(f">{w.wid}<", svg)
    totals = Counter(w.status for w in self.reg.products)
    self.assertIn(f"Draft {totals['D']}", svg)

  def test_m00_no_green_without_approved_status(self):
    statuses = {w.status for w in self.reg.products}
    if not statuses & {"A", "B"}:
      self.assertNotIn(fm.GREEN, self.outputs["fig-m00-3-1-wp-status.svg"])

  def test_m07_exposure_and_bands_match_register(self):
    risks = self.risks.risks
    self.assertEqual(len(risks), len({r.rid for r in risks}))
    for r in risks:
      self.assertEqual(r.e, r.p * r.i, r.rid)
    by_band = {b: sorted(r.rid for r in risks if not r.closed and fm.band(r.e) == b) for b in ("High", "Medium", "Low")}
    for b, ids in by_band.items():
      self.assertEqual(sorted(self.risks.summary[b]), ids, f"§4.1 {b}")
    self.assertEqual(sorted(self.risks.summary["Closed"]), sorted(r.rid for r in risks if r.closed))
    svg = self.outputs["fig-m07-4-1-risk-heat-map.svg"]
    for r in risks:
      self.assertIn(f">{r.rid}<", svg)

  def test_m13_ratings_and_cl_consistent(self):
    procs = self.profile.processes
    md = fm.WP_M_13.read_text(encoding="utf-8")
    s4 = fm.section(md, "## 4. Capability level 1")
    self.assertEqual(len(procs), len(re.findall(r"^\| [A-Z]{3}\.\d+ ", s4, re.M)))
    split = [p.code for p in procs if len(p.ratings) > 1]
    self.assertIn("SWE.3", split)
    for p in procs:
      # §4 CL column agrees with the §2 rule applied to the PA 1.1 rating(s) (PA 2.x is N, so at most CL1)
      if p.cl:
        derived = " / ".join("1" if r in "LF" else "0" for r, _ in p.ratings)
        self.assertEqual(re.sub(r"\s*\([^)]*\)", "", p.cl), derived, p.code)
      if p.group == "C":
        self.assertIsNone(p.target, p.code)
      else:
        self.assertIn(p.target, fm.CL_NEEDS, p.code)
    svg = self.outputs["fig-m13-6-1-capability-profile.svg"]
    self.assertEqual(svg.count(">safety code<"), len(split))


if __name__ == "__main__":
  unittest.main()
