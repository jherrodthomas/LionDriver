#!/usr/bin/env python3
"""Tests for risk_curve.py (injury-risk curve for SH-06)."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from tools.severity import risk_curve as rc


class RiskCurveTest(unittest.TestCase):
  def test_delta_v_conserves_momentum(self):
    v, m1, m2 = 100.0, 1400.0, 1500.0
    dv1, dv2 = rc.delta_v(v, m1, m2, e=0.0), rc.delta_v(v, m2, m1, e=0.0)
    self.assertAlmostEqual(m1 * dv1, m2 * dv2)
    self.assertAlmostEqual(dv1 + dv2, v)

  def test_restitution_raises_delta_v(self):
    self.assertAlmostEqual(rc.delta_v(100, 1000, 1000, e=0.1), 55.0)

  def test_heavy_lead_gives_ego_nearly_the_closing_speed(self):
    self.assertGreater(rc.delta_v(90, 1400, 15000, e=0.0), 0.9 * 90)

  def test_joksch_curve(self):
    self.assertAlmostEqual(rc.joksch(71 / rc.MPH_PER_KMH), 1.0)
    self.assertAlmostEqual(rc.joksch(35.5 / rc.MPH_PER_KMH), 1 / 16)
    self.assertEqual(rc.joksch(500), 1.0)

  def test_union_bound_over_occupants(self):
    ego = {"mass_kg": 1000, "occupants": 2}
    lead = {"name": "x", "mass_kg": 1000, "occupants": 3}
    r = rc.crash_fatal_ub(40, ego, lead, e=0.0)
    self.assertAlmostEqual(r["p_fatal_crash_ub"], 2 * r["p_driver_ego"] + 3 * r["p_driver_lead"])

  def test_sh06_has_no_severity_credit_at_odd_speeds(self):
    for v in rc.ODD_SPEEDS_KMH.values():
      worst = max(rc.crash_fatal_ub(v, rc.EGO, lead)["p_fatal_crash_ub"] for lead in rc.LEADS)
      self.assertEqual(worst, 1.0)

  def test_main_prints_table(self):
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--speed", "50"]), 0)
    self.assertIn("| custom | 50 km/h | 50 | heavy truck |", buf.getvalue())

  def test_sh03_following_impact_speed(self):
    # 90 km/h, 1.45 s gap: d = 1.45 * 25 + 6 = 42.25 m; v = sqrt(2 * 2 * 42.25) = 13 m/s
    self.assertAlmostEqual(rc.following_impact_kmh(90, 1.45), 13 * 3.6)
    self.assertGreater(rc.following_impact_kmh(120, 1.75), rc.following_impact_kmh(120, 1.45))

  def test_cases_cover_all_mapped_situations(self):
    labels = {sh for sh, _, _ in rc.cases()}
    self.assertEqual(labels, {"SH-06; SH-03 OS-07", "SH-03 OS-05", "SH-04 OS-08"})

  def test_sh04_follower_that_brakes_harder_early_stops_short(self):
    self.assertEqual(rc.rear_impact_kmh(120, 1.5, reaction_s=1.0, follower_decel=6.0), 0.0)

  def test_sh04_rear_impact_matches_kinematics(self):
    # Gap 0 and no follower braking: contact at once, relative speed 0; after t the gap is 1.75 t^2
    self.assertAlmostEqual(rc.rear_impact_kmh(100, 0.0, reaction_s=99, follower_decel=0.0), 0.0, places=1)
    # Slower or later follower braking strikes harder
    self.assertGreater(rc.rear_impact_kmh(120, 1.0, 2.0, 3.0), rc.rear_impact_kmh(120, 1.0, 1.5, 3.0))

  def test_sh04_bound_is_small_but_not_zero(self):
    worst = max(rc.crash_fatal_ub(v, rc.EGO, o)["p_fatal_crash_ub"]
                for sh, _, v in rc.cases() if sh == "SH-04 OS-08" for o in rc.LEADS)
    self.assertTrue(0.01 < worst < 0.1)

  def test_sensitivity_grid(self):
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--sensitivity"]), 0)
    self.assertIn("| 120 | 1.5 |", buf.getvalue())

  def test_sh03_following_earns_credit_but_approaching_does_not(self):
    for sh, _, v in rc.cases():
      worst = max(rc.crash_fatal_ub(v, rc.EGO, lead)["p_fatal_crash_ub"] for lead in rc.LEADS)
      if sh in ("SH-03 OS-05", "SH-04 OS-08"):
        self.assertLess(worst, 0.5)
      else:
        self.assertEqual(worst, 1.0)


if __name__ == "__main__":
  unittest.main()
