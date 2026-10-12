#!/usr/bin/env python3
"""Tests for severity_ratio.py on synthetic FARS/CRSS files with known answers."""
from __future__ import annotations

import io
import json
import math
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from tools.severity import severity_ratio as sr


def write(d, name, header, rows):
  os.makedirs(d, exist_ok=True)
  with open(os.path.join(d, name), "w") as f:
    f.write(",".join(header) + "\n")
    for r in rows:
      f.write(",".join(str(x) for x in r) + "\n")


def fars(d, crashes):
  """crashes: list of (st_case, man_coll, harm_ev, route, speed_limit)."""
  write(d, "accident.csv", ["ST_CASE", "MAN_COLL", "HARM_EV", "ROUTE"], [c[:4] for c in crashes])
  write(d, "vehicle.csv", ["ST_CASE", "VSPD_LIM"], [(c[0], c[4]) for c in crashes])


def crss(d, crashes):
  """crashes: list of (casenum, man_coll, harm_ev, int_hwy, max_sev, stratum, psu, weight, speed_limit)."""
  write(d, "ACCIDENT.CSV", ["CASENUM", "MAN_COLL", "HARM_EV", "INT_HWY", "MAX_SEV", "PSUSTRAT", "PSU_VAR", "WEIGHT"],
        [c[:8] for c in crashes])
  write(d, "VEHICLE.CSV", ["CASENUM", "VSPD_LIM"], [(c[0], c[8]) for c in crashes])


# 40 interstate rear-end crashes at 65 mph: 2 strata x 2 PSUs x 10 cases, weight 100 or 300.
# PSU totals per stratum: S1 {A: 1000, B: 3000}, S2 {C: 1000, D: 3000}; total 8000.
# Injury (MAX_SEV 2) in the first 3 cases of every PSU.
def rear_end_crss():
  rows, n = [], 0
  for stratum, psus in (("1", ("A", "B")), ("2", ("C", "D"))):
    for psu, w in zip(psus, (100, 300), strict=True):
      for i in range(10):
        n += 1
        rows.append((n, 1, 12, 1, 2 if i < 3 else 0, stratum, psu, w, 65))
  return rows


class SeverityRatioTest(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.f = os.path.join(self.tmp.name, "fars")
    self.c = os.path.join(self.tmp.name, "crss")

  def tearDown(self):
    self.tmp.cleanup()

  def results(self):
    return {k: sr.estimate(v, 1.645) for k, v in sr.load(self.f, self.c).items()}

  def test_fatal_ratio_and_bound(self):
    fars(self.f, [(i, 1, 12, 1, 65) for i in range(8)])
    crss(self.c, rear_end_crss())
    r = self.results()[("rear_end", True, (60, 65))]
    self.assertEqual(r["fars_fatal_crashes"], 8)
    self.assertAlmostEqual(r["crss_crashes"], 8000)
    # each stratum: n=2, PSU totals 1000 and 3000, mean 2000 -> 2/1 * (1e6 + 1e6) = 4e6; two strata -> 8e6
    self.assertAlmostEqual(r["crss_crashes_se"], math.sqrt(8e6))
    self.assertAlmostEqual(r["p_fatal"], 8 / 8000)
    self.assertAlmostEqual(r["p_fatal_ub"], 8 / (8000 - 1.645 * math.sqrt(8e6)))
    self.assertIsNone(r["fallback"])

  def test_injury_ratio_is_design_consistent(self):
    fars(self.f, [])
    crss(self.c, rear_end_crss())
    r = self.results()[("rear_end", True, (60, 65))]
    # 30 % of cases injured in every PSU -> ratio 0.3 and zero between-PSU variance of y - R x
    self.assertAlmostEqual(r["p_injury"], 0.3)
    self.assertAlmostEqual(r["p_injury_ub"], 0.3)

  def test_small_cell_falls_back_to_one(self):
    fars(self.f, [(1, 7, 12, 1, 70)])
    crss(self.c, [(1, 7, 12, 1, 0, "1", "A", 50, 70), (2, 7, 12, 1, 0, "1", "B", 50, 70)])
    r = self.results()[("sideswipe_same", True, (70, 85))]
    self.assertEqual((r["p_fatal_ub"], r["p_injury_ub"]), (1.0, 1.0))
    self.assertIn("fewer than", r["fallback"])

  def test_single_psu_stratum_falls_back(self):
    rows = [(i, 1, 12, 1, 0, "1", "A", 10, 65) for i in range(40)]
    fars(self.f, [])
    crss(self.c, rows)
    r = self.results()[("rear_end", True, (60, 65))]
    self.assertIn("single PSU", r["fallback"])

  def test_classification(self):
    self.assertEqual(sr.collision_type({"MAN_COLL": "0", "HARM_EV": "8"}), "pedestrian")
    self.assertEqual(sr.collision_type({"MAN_COLL": "2", "HARM_EV": "12"}), "head_on")
    self.assertIsNone(sr.collision_type({"MAN_COLL": "0", "HARM_EV": "42"}))
    self.assertEqual(sr.band_of(55), (50, 55))
    self.assertIsNone(sr.band_of(None))

  def test_unknown_speed_limits_are_ignored(self):
    write(self.f, "vehicle.csv", ["ST_CASE", "VSPD_LIM"], [(1, 99), (1, 65), (2, 98)])
    limits = sr.max_speed_limits(os.path.join(self.f, "vehicle.csv"))
    self.assertEqual(limits, {"1": 65})

  def test_missing_design_variable_is_reported(self):
    fars(self.f, [])
    write(self.c, "accident.csv", ["CASENUM", "MAN_COLL", "HARM_EV", "INT_HWY", "MAX_SEV", "WEIGHT"], [(1, 1, 12, 1, 0, 10)])
    write(self.c, "vehicle.csv", ["CASENUM", "VSPD_LIM"], [(1, 65)])
    with self.assertRaises(SystemExit) as cm:
      sr.load(self.f, self.c)
    self.assertIn("design variables", str(cm.exception))

  def test_sh_summary_takes_worst_cell_and_counts_missing(self):
    fars(self.f, [(i, 1, 12, 1, 65) for i in range(8)])
    crss(self.c, rear_end_crss())
    summary = {(s["sh"], s["odd"]): s for s in sr.by_sh(self.results())}
    h = summary[("SH-06", "ODD-H")]
    # only the 60-65 mph band has data; the 70-85 band is missing, so the bound is 1
    self.assertEqual(h["missing_cells"], 1)
    self.assertEqual(h["p_fatal_ub"], 1.0)

  def test_main_writes_json(self):
    fars(self.f, [(i, 1, 12, 1, 65) for i in range(8)])
    crss(self.c, rear_end_crss())
    out = os.path.join(self.tmp.name, "out.json")
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(sr.main(["--fars", self.f, "--crss", self.c, "--json", out]), 0)
    self.assertIn("| rear_end | yes | 60–65 |", buf.getvalue())
    with open(out) as f:
      data = json.load(f)
    self.assertEqual(data["cells"][0]["collision"], "rear_end")
    self.assertEqual(len(data["by_sh"]), len(sr.SH_COLLISIONS) * len(sr.ODD))


if __name__ == "__main__":
  unittest.main()
