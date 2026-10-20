#!/usr/bin/env python3
"""Tests of the failure search: the robustness sign means what the README says, and the search is deterministic; the
families of families.yaml are well formed, the driver-model options are off by default, every scene that names an
edge-case row reproduces it, and every new-hazard finding is queued in the decision register. (search.py --check in CI
compares the committed outputs with a fresh run.)"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import re  # noqa: E402

import numpy as np  # noqa: E402
import yaml  # noqa: E402

import search  # noqa: E402

sys.path.insert(0, str(search.SIM / "blender"))
import export_scene  # noqa: E402
import simulate  # noqa: E402


class TestSearch(unittest.TestCase):
  def test_straight_road_holds_and_curve_departs(self):
    straight = search.evaluate(np.array([100.0, 0.0, 3.7, 1.0, 0.2]))
    curve = search.evaluate(np.array([100.0, 1.5, 3.7, 1.0, 0.2]))
    self.assertGreater(straight["rho"], 0)        # nothing pushes the car sideways once the assist is lost
    self.assertLess(curve["rho"], 0)              # the 1.5 m/s² the assist was holding is lost: departure
    self.assertIsNotNone(curve["t_edge"])

  def test_space_inside_the_odd(self):
    self.assertLessEqual(search.SPACE["speed_kph"][1], 110.0)
    self.assertGreaterEqual(search.SPACE["lane_width"][0], 3.0)
    self.assertLessEqual(search.SPACE["a_y"][1], 2.5)

  def test_monte_carlo_is_seeded(self):
    a = np.random.default_rng(search.SEED).random(5)
    b = np.random.default_rng(search.SEED).random(5)
    self.assertTrue((a == b).all())


class TestFamilies(unittest.TestCase):
  def test_families_are_well_formed(self):
    kinds = {"hardover", "hardover_left", "frozen", "soc_stall", "eps_fault"}
    for fam in search.SPEC["families"]:
      lo, hi = search.bounds(fam)
      self.assertTrue((lo < hi).all(), fam["id"])
      p = search.params_of(fam, (lo + hi) / 2)
      case, assume = search.make_case(fam, p)
      self.assertIn(case.fault, kinds, fam["id"])
      self.assertLessEqual(set(assume), set(simulate.ASSUMPTIONS) | set(simulate.DRIVER_OPTIONS), fam["id"])
      self.assertIn(fam["robustness"], ("lane", "corridor"), fam["id"])
      if "speed_kph" in fam["space"]:
        self.assertLessEqual(fam["space"]["speed_kph"][1], simulate.ODD_KPH, fam["id"])
      for rule in fam["hara"]:
        self.assertRegex(rule["he"], r"^HE-\d\d\.\d$", fam["id"])
        if rule.get("new"):
          self.assertIn(rule["new"], search.SPEC["findings"], fam["id"])

  def test_choice_is_sampled_over_its_options(self):
    fam = search.FAMILIES["combo-odd-bound"]
    opts = fam["space"]["fault"]["choice"]
    self.assertEqual([search.params_of(fam, [i + 0.5, 105, 3.7, 1.0])["fault"] for i in range(len(opts))], opts)
    self.assertEqual(search.params_of(fam, [len(opts), 105, 3.7, 1.0])["fault"], opts[-1])   # the upper bound

  def test_driver_options_off_by_default(self):
    self.assertEqual(simulate.DRIVER_OPTIONS["driver_wrong_s"][0], 0.0)
    self.assertEqual(simulate.DRIVER_OPTIONS["driver_zeta"][0], 1.0)
    self.assertEqual(simulate.DRIVER_OPTIONS["driver_eps_lag_s"][0], 0.0)
    self.assertEqual(simulate.DRIVER_OPTIONS["driver_brakes_only"][0], 0.0)
    self.assertFalse(set(simulate.DRIVER_OPTIONS) & set(simulate.ASSUMPTIONS))   # plant-results.md lists ASSUMPTIONS
    c = simulate.Case("x", "x", "none", "straight", "", "")
    self.assertEqual((c.fault_clear, c.clear_after_correction, c.fault2, c.lane_change, c.ay_disturbance),
                     (None, None, "", None, 0.0))

  def test_braking_driver_ends_a_hardover(self):
    """The brake press revokes the panda's authority: the real safety code ends the hard-over."""
    fam = search.FAMILIES["driver-edge"]
    p = {"fault": "hardover", "behaviour": "brakes", "k": 0.0, "a_y": 0.0, "speed_kph": 100.0, "t_r": 1.0}
    case, assume = search.make_case(fam, p)
    r = simulate.simulate(case, assume)
    ev = r.metrics["events"]
    self.assertIn("authority revoked", ev)
    self.assertAlmostEqual(ev["authority revoked"], ev["driver correction"], delta=0.05)

  def test_lane_change_corridor(self):
    """A lane change without a fault stays inside the two lanes; the plain lane measure would call it a departure."""
    fam = search.FAMILIES["fault-timing-lane-change"]
    case = simulate.Case("x", "x", "none", "straight", "", "", t_fault=6.0, duration=8.0, speed_kph=100.0,
                         lane_change=6.0)
    out = search.robustness(fam, case, simulate.simulate(case))
    self.assertGreater(out["rho"], 0.3)

  def test_scenes_reproduce_their_rows(self):
    text = search.CATALOGUE.read_text(encoding="utf-8")
    rows = {m[0]: (m[1], float(m[2])) for m in re.findall(r"<!-- edge-case (EC-\d+) family=(\S+) rho=(\S+) -->", text)}
    scenes = [s for s in yaml.safe_load(search.SCENES.read_text(encoding="utf-8"))["scenes"] if s.get("edge_case")]
    self.assertGreaterEqual(len(scenes), 6)
    for s in scenes:
      fid, rho = rows[s["edge_case"]]
      _, case = export_scene.plant_case(s)
      out = search.robustness(search.FAMILIES[fid], case, simulate.simulate(case, s.get("assumptions")))
      self.assertAlmostEqual(out["rho"], rho, places=3, msg=s["id"])

  def test_findings_are_queued(self):
    reg = yaml.safe_load((search.SIM.parent / "01-management" / "decisions" / "register.yaml").read_text())
    entries = {e["id"]: e for e in reg}
    for fid, fd in search.SPEC["findings"].items():
      self.assertIn(fd["dq"], entries, fid)
      self.assertIn("assurance/sim/results/edge-cases.md", " ".join(entries[fd["dq"]]["sources"]), fid)


if __name__ == "__main__":
  unittest.main()
