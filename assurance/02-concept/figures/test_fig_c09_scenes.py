#!/usr/bin/env python3
"""Tests for fig_c09_scenes.py: one card per WP-C-09 threat scenario, §8 checked against §3, §6 and §7, sheets current."""

import copy
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c09_scenes as fc


class TestThreatScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.S = fc.load()
    cls.out = fc.build(cls.S)

  def test_tables_parsed(self):
    self.assertEqual(sorted(self.S.ts), [f"TS-{n:02d}" for n in range(1, 15)])
    self.assertEqual(self.S.ts["TS-01"]["damage"], [f"DS-0{n}" for n in range(1, 8)])
    self.assertEqual(self.S.matrix[4], [5, 4, 3, 2])
    self.assertEqual(self.S.rank[0], "TS-02")

  def test_one_card_per_threat_scenario_in_rank_order(self):
    cards = []
    for name, (num, _, keep) in fc.SHEETS.items():
      found = re.findall(r"<title>(TS-\d+): ", self.out[name])
      self.assertTrue(all(keep(self.S.risk[t]["risk"]) for t in found), name)
      self.assertIn(f"Figure {num}.", self.out[name])
      cards += found
    self.assertEqual(cards, self.S.rank)

  def test_committed_sheets_current_and_valid(self):
    for name, content in self.out.items():
      self.assertEqual((fc.HERE / name).read_text(encoding="utf-8"), content, f"{name} stale; run fig_c09_scenes.py")
      root = ET.fromstring(content)
      self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"), name)

  def test_every_sheet_is_referenced_in_wp_c09(self):
    doc = fc.SOURCE.read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"figures/{name}", doc, name)

  def test_risk_table_must_follow_the_matrix(self):
    S = copy.deepcopy(self.S)
    S.risk["TS-13"]["risk"] = 4
    with self.assertRaisesRegex(fc.ParseError, "TS-13: §8 risk 4 is not the §7 matrix value 3"):
      S.check()

  def test_feasibility_must_be_the_highest_of_the_paths(self):
    S = copy.deepcopy(self.S)
    S.feas["AP-01"]["feas"] = "High"
    with self.assertRaisesRegex(fc.ParseError, "TS-01: §8 gives impact 4 / Medium"):
      S.check()

  def test_missing_or_extra_card_fails(self):
    model = dict(fc.MODEL)
    del model["TS-07"]
    model["TS-99"] = fc.MODEL["TS-07"]
    with mock.patch.object(fc, "MODEL", model):
      with self.assertRaisesRegex(fc.ParseError, r"no card for \['TS-07'\].*\['TS-99'\]"):
        fc.build(self.S)

  def test_scenes_loop_and_output_is_deterministic(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
    self.assertEqual(self.out, fc.build(self.S))

  def test_no_procedural_detail_in_the_cards(self):
    # WP-C-09 stays at the §5 abstraction: no command bytes, payloads or key material on the cards either
    text = repr(fc.MODEL)
    self.assertNotRegex(text, r"0x[0-9a-fA-F]{2,}")
    self.assertNotRegex(text, r"(?i)\b(exploit|shellcode|password)\b")


if __name__ == "__main__":
  unittest.main()
