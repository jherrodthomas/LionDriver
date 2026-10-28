#!/usr/bin/env python3
"""Tests for fmea_cards.py: one card per System FMEA failure mode, read from the YAML, sheets current."""

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_cards as fc  # noqa: E402


class TestCards(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.doc, cls.mapping = fc.load()
    cls.out = fc.build()

  def test_every_failure_mode_once_in_sheet_order(self):
    seen = []
    for name, (num, _, ids) in fc.SHEETS.items():
      found = re.findall(r"<title>(SFM-\d+): ", self.out[name])
      self.assertEqual(found, ids, name)
      self.assertIn(f"Figure {num}.", self.out[name])
      seen += found
    self.assertEqual(sorted(seen), sorted(f["id"] for f in self.doc["failure_modes"]))

  def test_ratings_come_from_the_yaml(self):
    cs = fc.cards(self.doc, self.mapping)
    f = next(x for x in self.doc["failure_modes"] if x["id"] == "SFM-006")
    self.assertEqual([(k["o"], k["d"], k["ap"]) for k in cs["SFM-006"]["causes"]],
                     [(c["occurrence"], c["detection"], c["ap"]) for c in f["causes"]])
    self.assertEqual(cs["SFM-001"]["hz"], ["H-01"])

  def test_new_failure_mode_without_a_place_fails(self):
    doc = copy.deepcopy(self.doc)
    extra = copy.deepcopy(doc["failure_modes"][0])
    extra["id"] = "SFM-999"
    doc["failure_modes"].append(extra)
    with self.assertRaisesRegex(fc.CardError, "SFM-999"):
      fc.cards(doc, self.mapping)

  def test_unmapped_hazard_or_unknown_action_fails(self):
    with self.assertRaisesRegex(fc.CardError, "hara-mapping"):
      fc.cards(self.doc, {k: v for k, v in self.mapping.items() if k != "HZ-001"})
    doc = copy.deepcopy(self.doc)
    doc["actions"] = [a for a in doc["actions"] if a["id"] != "SFM-ACT-012"]
    with self.assertRaisesRegex(fc.CardError, "SFM-ACT-012"):
      fc.cards(doc, self.mapping)

  def test_failure_mode_on_two_sheets_fails(self):
    sheets = copy.deepcopy(fc.SHEETS)
    sheets["fig-3-17-sfm-cards-3.svg"][2].append("SFM-001")
    with mock.patch.object(fc, "SHEETS", sheets):
      with self.assertRaisesRegex(fc.CardError, "two sheets"):
        fc.cards(self.doc, self.mapping)

  def test_monitoring_bands_follow_the_m_table(self):
    # rating-tables §7.3, DQ-206 A: only measured timing (M 1-4) is green; code-derived M 5 is not
    self.assertEqual([fc.monitoring(m)[0] for m in (4, 5, 7, 8, 10)], ["#16A34A", "#D97706", "#D97706", "#DC2626", "#DC2626"])
    self.assertEqual(fc.monitoring(None)[1], "no MSR rating")

  def test_completed_action_is_credited_once_a_cause_reaches_its_revised_rating(self):
    cs = fc.cards(self.doc, self.mapping)
    self.assertIn(("SFM-ACT-020", "completed"), cs["SFM-036"]["actions"])  # SFM-036.C1 at its revised O5 D8 since BL-007
    doc = copy.deepcopy(self.doc)
    c1 = next(c for f in doc["failure_modes"] if f["id"] == "SFM-036" for c in f["causes"] if c["id"] == "SFM-036.C1")
    c1["occurrence"], c1["detection"] = 8, 10  # the BL-006 rating: completed, but the cause has not reached it
    self.assertIn(("SFM-ACT-020", "completed, not yet credited"), fc.cards(doc, self.mapping)["SFM-036"]["actions"])
    self.assertIn(("SFM-ACT-023", "completed"), cs["SFM-038"]["actions"])  # SFM-038.C1 O5 D4 betters its revised O5 D8
    self.assertIn(("SFM-ACT-017", "completed"), cs["SFM-004"]["actions"])  # no revised rating: plain completed
    svg = "".join(self.out.values())
    self.assertIn("MSR H", svg)

  def test_fault_tree_strip_reads_the_map(self):
    cs = fc.cards(self.doc, self.mapping)
    sg04 = {g: ids for g, ids, kind in cs["SFM-009"]["trees"] if not kind}["SG-04"]
    self.assertEqual(sg04, [("BE-4.02", False), ("BE-4.06", False), ("BE-4.11", True), ("G4.1", False), ("G4.3", False)])
    self.assertIn(("SG-04", [], "justified"), cs["SFM-014"]["trees"])  # listed in not_in_fta for SG-04
    links = {"SFM-001": [("SG-01", [("BE-9.99", True)], None)]}
    self.assertEqual(fc.cards(self.doc, self.mapping, links)["SFM-001"]["trees"], [("SG-01", [("BE-9.99", True)], None)])
    self.assertEqual(fc.cards(self.doc, self.mapping, links)["SFM-002"]["trees"], [])

  def test_committed_sheets_current_and_embedded(self):
    plan = (fc.fd.FMEA_DIR / "fmea-plan.md").read_text(encoding="utf-8")
    for name, svg in self.out.items():
      self.assertEqual((fc.OUT / name).read_text(encoding="utf-8"), svg, name)
      self.assertIn(f"figures/cards/{name}", plan)

  def test_loops_and_deterministic(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
    self.assertEqual(self.out, fc.build())


if __name__ == "__main__":
  unittest.main()
