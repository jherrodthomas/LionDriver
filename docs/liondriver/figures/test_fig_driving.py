#!/usr/bin/env python3
"""Tests for fig_driving.py: committed SVGs current, every WP-C-07 modification placed, sources parsed."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_driving as fd


class TestDrivingFigures(unittest.TestCase):
  def setUp(self):
    self.md = fd.WP_C07.read_text(encoding="utf-8")
    self.fms = fd.fm_rows(self.md)

  def test_committed_output_current(self):
    for name, s in fd.build_all().items():
      self.assertEqual((fd.OUT_DIR / name).read_text(encoding="utf-8"), s, f"stale {name}; run fig_driving.py")

  def test_svgs_parse_and_have_title(self):
    for name, s in fd.build_all().items():
      root = ET.fromstring(s)
      self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"), name)

  def test_every_fm_placed(self):
    self.assertEqual(fd.unplaced(self.fms), [])

  def test_unmapped_fm_detected(self):
    fms = dict(self.fms, **{"FM-99": {"title": "x", "priority": "P2", "code": "`openpilot/system/ui/elsewhere.py`"}})
    self.assertEqual(fd.unplaced(fms), ["FM-99"])

  def test_whole_file_names_only(self):
    # dmonitoringmodeld.py must not put a driver-monitoring change on the driving model
    self.assertFalse(fd.file_hits("`openpilot/selfdrive/modeld/dmonitoringmodeld.py:99`", ["modeld.py"]))
    self.assertTrue(fd.file_hits("`openpilot/selfdrive/modeld/modeld.py:49`", ["modeld.py"]))

  def test_new_component_goes_to_new_box_only(self):
    cell = "New component; inputs from `modelV2` (`fill_model_msg.py`)"
    self.assertTrue(fd.file_hits(cell, fd.BOXES["monitor"][5]))
    self.assertFalse(fd.file_hits(cell, fd.BOXES["modeld"][5]))

  def test_every_chip_drawn(self):
    s = fd.build_pipeline(self.fms)
    for fm in self.fms:
      self.assertIn(f">{fm}<", s)

  def test_code_constants_drawn(self):
    f = fd.code_facts()
    s = fd.build_paths(f)
    for k in ("max_curv", "lat_accel", "lat_jerk", "cruise_min"):
      self.assertIn(f[k], s, k)


if __name__ == "__main__":
  unittest.main()
