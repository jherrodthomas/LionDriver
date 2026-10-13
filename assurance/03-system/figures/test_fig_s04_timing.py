#!/usr/bin/env python3
"""Tests for fig_s04_timing.py: source texts still in WP-S-04, committed SVGs current and well-formed."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s04_timing as ft


class TestTimingFigures(unittest.TestCase):
  def test_source_texts_present(self):
    md = ft.SOURCE.read_text(encoding="utf-8")
    self.assertEqual(ft.missing_sources(md), [])

  def test_committed_outputs_current(self):
    for name, content in ft.build().items():
      path = ft.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s04_timing.py")

  def test_svgs_parse_and_have_title(self):
    for name, content in ft.build().items():
      root = ET.fromstring(content)
      self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"), name)

  def test_budgets_fit_ftti(self):
    for g in ft.GROUPS:
      for r in g["rows"]:
        total = r["fdti"] + (r["frti"] or 0)
        self.assertLessEqual(total, g["ftti"] + 1e-9, r["title"])

  def test_eps_fault_chain_matches_t28(self):
    t = ft.T28
    # worst case: 1 s persistence + one 10 ms task period + two 125 ms ticks (speaker only on every other 8 Hz tick)
    self.assertAlmostEqual(t["persist"] + t["task"] + t["tick"], 1.26)
    eps = ft.GROUPS[1]["rows"][0]["ref"]["kind"]
    self.assertAlmostEqual(eps[1], 1.26)

  def test_heartbeat_siren_matches_t07a(self):
    # 0.3 s heartbeat timeout + one 10 ms task period + two 125 ms ticks, within the SG-02 1 s warning budget
    hb = ft.GROUPS[1]["rows"][1]
    self.assertAlmostEqual(hb["ref"]["kind"][1], 0.3 + 0.01 + 0.25)
    self.assertLessEqual(hb["ref"]["kind"][1], hb["limit"])

  def test_build_is_deterministic(self):
    self.assertEqual(ft.build(), ft.build())


if __name__ == "__main__":
  unittest.main()
