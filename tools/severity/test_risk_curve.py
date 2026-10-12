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
    self.assertIn("| 50 km/h | 50 | heavy truck |", buf.getvalue())


if __name__ == "__main__":
  unittest.main()
