#!/usr/bin/env python3
"""Tests of the known-scenario files: committed files equal a fresh generation, every WP-V-03 scenario is either
written or has a recorded reason, and the plant reads the scenario roads as written."""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "plant"))

import generate  # noqa: E402
from roads import from_xodr  # noqa: E402

WP_V_03 = HERE.parents[1] / "06-validation" / "WP-V-03-sotif-known-scenarios.md"


class TestScenarios(unittest.TestCase):
  def test_committed_files_current(self):
    for path, content in generate.build().items():
      self.assertTrue(path.exists(), path)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run generate.py")

  def test_every_wp_v_03_scenario_accounted_for(self):
    ids = set(re.findall(r"^\| (KS-\d+) \|", WP_V_03.read_text(encoding="utf-8"), re.M))
    written = {sc.id for sc in generate.SCENARIOS}
    self.assertFalse(written & set(generate.NOT_REPRESENTED), "a scenario is both written and excluded")
    self.assertEqual(ids, written | set(generate.NOT_REPRESENTED))

  def test_files_named_by_scenario_id(self):
    for sc in generate.SCENARIOS:
      for fid, _road in generate.files_of(sc):
        self.assertTrue(fid == sc.id or fid.startswith(sc.id + "-"), fid)
        self.assertTrue((HERE / "xosc" / f"{fid}.xosc").exists())
        self.assertTrue((HERE / "xodr" / f"{fid}.xodr").exists())

  def test_defaults_inside_sweeps_and_speeds(self):
    for sc in generate.SCENARIOS:
      for name, (default, sweep, *_r) in sc.params.items():
        self.assertIn(default, sweep, f"{sc.id} {name}")
        if name == "EgoSpeed":
          self.assertLessEqual(max(sweep), generate.SWEEP_MAX + 1e-6, f"{sc.id}: above the highest WP-V-03 sweep speed")

  def test_ks25_crosses_the_odd_speed_bound(self):
    p = {k: v[0] for k, v in generate.SCENARIOS_BY_ID["KS-25"].params.items()}
    self.assertLess(p["StartSpeed"], generate.ODD_SPEED)
    self.assertGreater(p["EndSpeed"], generate.ODD_SPEED)

  def test_ks04_lanes_open_and_end(self):
    """The exit lane grows from 0 to a full lane over the taper; lane -3 of the merge shrinks from a full lane to 0."""
    import xml.etree.ElementTree as ET

    def width_at(path, road, lane, s):
      rd = next(r for r in ET.parse(path).getroot().iter("road") if r.get("id") == road)
      secs = [ls for ls in rd.iter("laneSection") if float(ls.get("s")) <= s]
      ls = secs[-1]
      ln = next((x for x in ls.iter("lane") if int(x.get("id")) == lane), None)
      if ln is None:
        return 0.0
      w = ln.find("width")
      ds = s - float(ls.get("s"))
      return sum(float(w.get(k)) * ds ** n for n, k in enumerate("abcd"))
    sc = generate.SCENARIOS_BY_ID["KS-04"]
    for fid, road in generate.files_of(sc):
      path = HERE / "xodr" / f"{fid}.xodr"
      t0, t1 = road["taper_start"], road["taper_start"] + road["taper"]
      if road["kind"] == "exit":
        self.assertAlmostEqual(width_at(path, "0", -4, t0), 0.0)
        self.assertAlmostEqual(width_at(path, "0", -4, t1 - 1e-9), generate.LANE_W, places=6)
        self.assertAlmostEqual(width_at(path, "0", -4, road["nose"] - 1), generate.LANE_W)
        mark = "broken" if road["marked"] else "none"
        rd0 = next(r for r in ET.parse(path).getroot().iter("road") if r.get("id") == "0")
        for ls in list(rd0.iter("laneSection"))[1:]:
          ln = next(x for x in ls.iter("lane") if x.get("id") == "-3")
          self.assertEqual(ln.find("roadMark").get("type"), mark, fid)
      else:
        self.assertAlmostEqual(width_at(path, "0", -3, t0), generate.LANE_W)
        self.assertAlmostEqual(width_at(path, "0", -3, t1 - 1e-9), 0.0, places=6)
        self.assertEqual(width_at(path, "0", -3, t1 + 1), 0.0)

  def test_plant_reads_ks01_lane_centre(self):
    road = from_xodr(HERE / "xodr" / "KS-01.xodr")
    self.assertAlmostEqual(road.lane_width, 3.7)
    self.assertAlmostEqual(road.curve_start, generate.SCENARIOS[0].road["straight"])
    # ego lane -2: 1.5 lane widths right of the reference line, on the outside of the left curve
    self.assertAlmostEqual(1 / road.curvature(road.curve_start + 1000), generate.R01 + 1.5 * 3.7, places=6)


if __name__ == "__main__":
  unittest.main()
