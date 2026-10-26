#!/usr/bin/env python3
"""Tests for fig_a03_two_channel.py: every dfa.yaml DFI placed once, committed SVG current, drift rejected."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_a03_two_channel as tc

SVG = "{http://www.w3.org/2000/svg}"


class TestRealSource(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.text = tc.SOURCE.read_text(encoding="utf-8")
    cls.data = tc.load(cls.text)

  def test_every_dfi_placed_once(self):
    self.assertEqual(sorted(d["id"] for d in self.data["dfis"]), sorted(tc.PLACE))

  def test_every_placement_names_a_group(self):
    keys = {g[0] for g in tc.GROUPS}
    for i, (g, label) in tc.PLACE.items():
      self.assertIn(g, keys, i)
      self.assertTrue(label, i)

  def test_cascade_row_holds_only_cascading_dfis(self):
    kind = {d["id"]: d["kind"] for d in self.data["dfis"]}
    for i, (g, _) in tc.PLACE.items():
      if g == "cascade":
        self.assertEqual(kind[i], "cascading", i)

  def test_each_dfi_drawn_with_its_assessment_colour(self):
    root = ET.fromstring(tc.build())
    drawn = {}
    for t in root.iter(SVG + "text"):
      if t.text in tc.PLACE:
        drawn.setdefault(t.text, set()).add(t.get("fill"))
    self.assertEqual(sorted(drawn), sorted(tc.PLACE))
    for d in self.data["dfis"]:
      self.assertEqual(drawn[d["id"]], {tc.COLOUR[d["assessment"]]}, d["id"])

  def test_committed_output_current(self):
    path = tc.HERE / tc.OUTPUT
    self.assertTrue(path.exists())
    self.assertEqual(path.read_text(encoding="utf-8"), tc.build(), "stale; run fig_a03_two_channel.py")

  def test_svg_parses_and_has_title(self):
    root = ET.fromstring(tc.build())
    self.assertIsNotNone(root.find(SVG + "title"))
    self.assertIsNotNone(root.find(SVG + "desc"))


class TestDrift(unittest.TestCase):
  def setUp(self):
    self.data = yaml.safe_load(tc.SOURCE.read_text(encoding="utf-8"))

  def test_new_dfi_without_placement_rejected(self):
    extra = dict(self.data["dfis"][0], id="DFI-99")
    self.data["dfis"].append(extra)
    with self.assertRaises(tc.SourceError):
      tc.load(yaml.safe_dump(self.data))

  def test_removed_dfi_rejected(self):
    self.data["dfis"] = [d for d in self.data["dfis"] if d["id"] != "DFI-03"]
    with self.assertRaises(tc.SourceError):
      tc.load(yaml.safe_dump(self.data))

  def test_unknown_assessment_rejected(self):
    self.data["dfis"][0]["assessment"] = "maybe"
    with self.assertRaises(tc.SourceError):
      tc.load(yaml.safe_dump(self.data))

  def test_needs_text(self):
    status = {"DM-01": "required", "DM-02": "existing_unverified", "DM-03": "existing"}
    self.assertEqual(tc.needs({"measures": ["DM-01", "DM-02", "DM-03"]}, status), "needs DM-01 · 1 unverified")
    self.assertEqual(tc.needs({"measures": ["DM-03"]}, status), "measures in place")
    self.assertEqual(tc.needs({"measures": []}, status), "no measure yet")


if __name__ == "__main__":
  unittest.main()
