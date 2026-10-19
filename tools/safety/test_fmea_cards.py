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

  def test_monitoring_bands(self):
    self.assertEqual(fc.monitoring(5)[1], "a monitor reacts")
    self.assertEqual(fc.monitoring(8)[1], "warns, or late")
    self.assertEqual(fc.monitoring(9)[1], "no monitor")
    self.assertEqual(fc.monitoring(None)[1], "no MSR rating")

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
