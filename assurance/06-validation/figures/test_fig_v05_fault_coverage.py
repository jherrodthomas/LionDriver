#!/usr/bin/env python3
"""Tests for fig_v05_fault_coverage.py: §5/§6/§8 of WP-V-05 parsed, SVG current and well-formed, nothing green."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_v05_fault_coverage as ff

SVG_NS = "{http://www.w3.org/2000/svg}"


class TestFaultCoverage(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.cases, cls.sections, cls.items, cls.tsrs, cls.titles = ff.load()
    cls.by_id = {c.ident: c for c in cls.cases}

  def test_source_texts_present(self):
    self.assertEqual(ff.missing_sources(ff.SOURCE.read_text(encoding="utf-8")), [])

  def test_all_cases_and_sections(self):
    self.assertEqual(sorted(self.by_id), [f"VS-FI-{i:02d}" for i in range(1, 32)])
    self.assertEqual(sorted(self.sections), [f"5.{i}" for i in range(1, 7)])
    self.assertEqual(len(self.items), 14)

  def test_mechanism_refs(self):
    self.assertEqual(self.by_id["VS-FI-14"].tsrs,
                     {f"TSR-{n}" for n in list(range(101, 110)) + list(range(201, 206))})
    self.assertEqual(self.by_id["VS-FI-31"].tsrs, {"TSR-110", "TSR-516"})
    self.assertEqual(self.by_id["VS-FI-31"].goals, {"SG-02", "SG-06"})
    fi27 = self.by_id["VS-FI-27"]
    self.assertTrue(fi27.inherited)
    self.assertEqual(fi27.tsrs, self.by_id["VS-FI-08"].tsrs | self.by_id["VS-FI-09"].tsrs
                     | self.by_id["VS-FI-14"].tsrs)

  def test_section6_short_forms(self):
    cm = next(i for i in self.items if i.ident.startswith("FFI-CM"))
    self.assertEqual(cm.cases, ["VS-FI-06", "VS-FI-08", "VS-FI-10", "VS-FI-19"])
    spf01 = next(i for i in self.items if i.ident == "SPF-01")
    self.assertEqual(spf01.cases, [])

  def test_nothing_executed_nothing_green(self):
    self.assertTrue(all(c.result == "Not yet executed" for c in self.cases))
    self.assertNotIn(ff.GREEN, ff.build())

  def test_committed_output_current(self):
    path = ff.HERE / ff.OUTPUT
    self.assertTrue(path.exists())
    self.assertEqual(path.read_text(encoding="utf-8"), ff.build(), "stale; run fig_v05_fault_coverage.py")

  def test_svg_valid_with_role_title_desc(self):
    root = ET.fromstring(ff.build())
    self.assertEqual(root.get("role"), "img")
    self.assertIsNotNone(root.find(f"{SVG_NS}title"))
    self.assertIsNotNone(root.find(f"{SVG_NS}desc"))

  def test_case_refs_parser(self):
    self.assertEqual(ff.case_refs("VS-FI-15, -20, -22, -26"), ["VS-FI-15", "VS-FI-20", "VS-FI-22", "VS-FI-26"])
    self.assertEqual(ff.case_refs("VS-FI-11, VS-FI-24"), ["VS-FI-11", "VS-FI-24"])

  def test_build_is_deterministic(self):
    self.assertEqual(ff.build(), ff.build())


if __name__ == "__main__":
  unittest.main()
