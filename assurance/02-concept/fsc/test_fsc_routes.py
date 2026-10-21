#!/usr/bin/env python3
"""Tests for fsc_routes.py: outputs current, every route quote found, slot texts follow the documents, strips fit."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fsc_routes as fr


class TestRoutes(unittest.TestCase):
  def test_outputs_current(self):
    for p, s in fr.build().items():
      self.assertEqual(p.read_text(encoding="utf-8"), s, f"stale: {p.name}; run fsc_routes.py")

  def test_svgs_parse_with_title(self):
    for p, s in fr.build().items():
      if p.suffix == ".svg":
        self.assertIsNotNone(ET.fromstring(s).find("{http://www.w3.org/2000/svg}title"), p.name)

  def test_six_routes_each_quoted(self):
    self.assertEqual(len(fr.ROUTES), 6)
    for r in fr.ROUTES:
      self.assertTrue(r["src"], r["key"])
      self.assertTrue(set(r["fixed"]) <= set(fr.KEYS), r["key"])

  def test_missing_quote_fails(self):
    r = fr.ROUTES[0]
    old = r["src"]
    r["src"] = [(old[0][0], "a sentence that is not in WP-A-04", "probe")]
    try:
      with self.assertRaises(fr.RouteError):
        fr.check_sources()
    finally:
      r["src"] = old

  def test_slot_drift_fails(self):
    old = fr.TSR_NOW["CONSTRAINT"]
    fr.TSR_NOW["CONSTRAINT"] = "within ≤ 0.4 s of detection"
    try:
      with self.assertRaises(fr.RouteError):
        fr.check_sources()
    finally:
      fr.TSR_NOW["CONSTRAINT"] = old

  def test_every_slot_filled_in_tsr(self):
    self.assertTrue(all(fr.TSR_NOW[k] for k in fr.KEYS))
    self.assertIsNone(fr.FSR["CONSTRAINT"])

  def test_every_figure_linked_from_page(self):
    page = fr.page()
    for p in fr.build():
      if p.suffix == ".svg":
        self.assertIn(f"figures/{p.name}", page)


if __name__ == "__main__":
  unittest.main()
