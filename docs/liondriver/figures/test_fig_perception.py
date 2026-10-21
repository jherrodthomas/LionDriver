#!/usr/bin/env python3
"""Tests for fig_perception.py: committed SVGs current, sources present, parsed tables complete."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_perception as fp


class TestPerceptionFigures(unittest.TestCase):
  def test_committed_output_current(self):
    for name, s in fp.build_all().items():
      self.assertEqual((fp.OUT_DIR / name).read_text(encoding="utf-8"), s, f"stale {name}; run fig_perception.py")

  def test_svgs_parse_and_have_title(self):
    for name, s in fp.build_all().items():
      self.assertIsNotNone(ET.fromstring(s).find("{http://www.w3.org/2000/svg}title"), name)

  def test_sources_present(self):
    self.assertEqual(fp.problems(), [])

  def test_every_air_on_figure_1_exists(self):
    air = fp.airs()
    for o in fp.OUTPUTS:
      for a in o[5]:
        self.assertIn(a, air)

  def test_air_status_classes(self):
    air = fp.airs()
    self.assertEqual(air["AIR-15"]["cls"], "red")      # valid hard-coded True
    self.assertEqual(air["AIR-16"]["cls"], "amber")    # only AI-2 checked

  def test_insufficiency_rows(self):
    rows = {r["id"]: r for r in fp.insufficiencies()}
    self.assertIn("FI-06", rows)
    self.assertIn("TC-10", rows["FI-06"]["tc"])
    for r in rows.values():
      self.assertTrue(r["sh"], r["id"])

  def test_page_names_the_rows_without_airs(self):
    page = (fp.REPO / "docs" / "liondriver" / "perception-models.md").read_text(encoding="utf-8")
    for r in fp.insufficiencies():
      if not r["air"]:
        self.assertIn(r["id"], page, f"{r['id']} has no AIR; the page's §3 list is stale")

  def test_dm_timers_increase(self):
    f = fp.dm_facts()
    self.assertEqual(f["vision"], sorted(f["vision"]))
    self.assertEqual(f["wheel"], sorted(f["wheel"]))


if __name__ == "__main__":
  unittest.main()
