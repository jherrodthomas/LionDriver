#!/usr/bin/env python3
"""Tests for fig_c09_boundary.py: every asset and attack path is placed, the figure follows WP-C-09 and is current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c09_boundary as fb


class TestBoundary(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fb.SOURCE.read_text(encoding="utf-8")
    cls.d = fb.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fb.build().items():
      self.assertEqual((fb.HERE / name).read_text(encoding="utf-8"), content, name)

  def test_every_threat_scenario_drawn(self):
    m = fb.place_model(self.d)
    drawn = {x for v in m.values() for x in v["ts"]}
    self.assertEqual(drawn, set(self.d["ts"]))
    self.assertEqual(m["E-03"]["top"], 5)
    self.assertIn("AP-11", m["E-04"]["aps"])

  def test_unplaced_asset_rejected(self):
    old = fb.ASSET_PLACE.pop("AS-16")
    try:
      with self.assertRaises(fb.BoundaryError):
        fb.parse(self.md)
    finally:
      fb.ASSET_PLACE["AS-16"] = old

  def test_unknown_risk_rejected(self):
    with self.assertRaises(fb.BoundaryError):
      fb.parse(self.md.replace("| TS-13 | 3 | Medium | **3** |", "| TS-99 | 3 | Medium | **3** |"))


if __name__ == "__main__":
  unittest.main()
