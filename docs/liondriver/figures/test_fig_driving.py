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

  def test_overlay_grids_match_model_constants(self):
    f = fd.overlay_facts()
    self.assertEqual(len(f["x_idxs"]), f["idx_n"])
    self.assertAlmostEqual(f["x_idxs"][-1], f["x_max"])
    self.assertAlmostEqual(f["t_idxs"][-1], f["t_max"])
    self.assertAlmostEqual(f["x_idxs"][1], f["x_max"] / (f["idx_n"] - 1) ** 2)

  def test_overlay_states_command_and_label(self):
    f = fd.overlay_facts()
    s = fd.build_overlay(f)
    v = fd.SCENE["v_kmh"] / 3.6
    self.assertIn(f"{fd.SCENE['a_lat'] / v ** 2:.5f}", s)
    self.assertIn("FOR DISPLAY, NOT FOR STEERING", s)
    self.assertIn("data_kind: synthetic", s)
    self.assertIn(f"{f['cam_w']}×{f['cam_h']}", s)

  def test_overlay_source_change_detected(self):
    real = fd.OVERLAY_SOURCES["ui"]
    tmp = Path(__file__).resolve().parent / "_ui_probe.py"
    try:
      tmp.write_text(real.read_text(encoding="utf-8").replace("MAX_DRAW_DISTANCE = ", "MAX_DRAW = "), encoding="utf-8")
      fd.OVERLAY_SOURCES["ui"] = tmp
      with self.assertRaises(SystemExit):
        fd.overlay_facts()
    finally:
      fd.OVERLAY_SOURCES["ui"] = real
      tmp.unlink(missing_ok=True)


if __name__ == "__main__":
  unittest.main()
