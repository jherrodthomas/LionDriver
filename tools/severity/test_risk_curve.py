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
    self.assertEqual(labels, {"SH-06; SH-03 OS-07", "SH-03 OS-05", "SH-04 OS-08", "SH-01/02 OS-03/OS-16"})

  def test_sh01_head_on_uses_combined_speed_and_has_no_credit(self):
    from tools.severity import severity_ratio as sr
    head_on = [v for sh, _, v in rc.cases() if sh == "SH-01/02 OS-03/OS-16"]
    self.assertEqual(head_on, [2 * rc.ODD_SPEEDS_KMH["ODD-A"]])
    for lead in rc.LEADS:
      self.assertEqual(rc.crash_fatal_ub(head_on[0], rc.EGO, lead)["p_fatal_crash_ub"], 1.0)
    for sh in ("SH-01", "SH-02"):
      self.assertNotIn("head_on", sr.SH_COLLISIONS[sh])
      self.assertEqual(set(sr.SH_COLLISIONS[sh]), {"sideswipe_same", "barrier"})

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

  def test_sh10_stays_on_the_national_ratio(self):
    from tools.severity import severity_ratio as sr
    self.assertFalse(any("SH-10" in sh for sh, _, _ in rc.cases()))
    self.assertEqual(sr.SH_COLLISIONS["SH-10"], ["sideswipe_same"])

  def test_pedestrian_curve_hits_its_anchors(self):
    for mph, risk in rc.PEDESTRIAN_ANCHORS_MPH[1:]:
      self.assertAlmostEqual(rc.pedestrian_fatality(mph / rc.MPH_PER_KMH), risk)
    self.assertEqual(rc.pedestrian_fatality(100), 1.0)
    self.assertAlmostEqual(rc.pedestrian_fatality(37 / rc.MPH_PER_KMH), 0.375)

  def test_low_speed_logistic_fits(self):
    # the Tefft fit reproduces its anchors within 0.04, Hussain gives 5 % at 30 km/h and 50 % at 59 km/h
    for mph, p in rc.PEDESTRIAN_ANCHORS_MPH[1:]:
      self.assertAlmostEqual(rc.low_speed_check(mph / rc.MPH_PER_KMH)["tefft_logistic"], p, delta=0.04)
    self.assertAlmostEqual(rc.low_speed_check(30)["hussain_logistic"], 0.05, delta=0.005)
    self.assertAlmostEqual(rc.low_speed_check(59)["hussain_logistic"], 0.5, places=6)

  def test_linear_segment_covers_logistic_curves_above_2_mph(self):
    for tenth in range(20, 231):
      c = rc.low_speed_check(tenth / 10 / rc.MPH_PER_KMH)
      self.assertGreaterEqual(c["linear"], max(c["tefft_logistic"], c["hussain_logistic"]))
    for tenth in range(20):
      c = rc.low_speed_check(tenth / 10 / rc.MPH_PER_KMH)
      self.assertLess(c["tefft_logistic"] - c["linear"], 0.0065)

  def test_low_speed_cli_reports_os06(self):
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--low-speed"]), 0)
    out = buf.getvalue()
    self.assertIn("SH-11 OS-06", out)
    self.assertIn("linear 0.048, Tefft logistic fit 0.023, Hussain 2019 0.013", out)

  def test_age_shift(self):
    # 70 vs 30 is the published 11.8 mph; no shift at or below the reference age
    self.assertAlmostEqual(rc.age_shift_mph(70), 11.8)
    self.assertEqual(rc.age_shift_mph(20), 0.0)
    self.assertEqual(rc.pedestrian_fatality(60, 0.0), rc.pedestrian_fatality(60))
    # the shift moves the curve along the speed axis: 42 mph - 11.8 mph at age 70 gives the 50 % anchor
    self.assertAlmostEqual(rc.pedestrian_fatality((42 - 11.8) / rc.MPH_PER_KMH, rc.age_shift_mph(70)), 0.5)

  def test_age_cli_reports_sh11_cases(self):
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--age"]), 0)
    out = buf.getvalue()
    self.assertIn("| SH-11 OS-04 | 60 | 0.382 | 0.537 | 0.721 | 0.788 |", out)
    self.assertIn("| SH-11 OS-06 | 18 | 0.048 | 0.073 | 0.099 | 0.145 |", out)
    # central estimate, shifted from the sample mean age of 45
    self.assertIn("Shift from age 45", out)
    self.assertIn("| SH-11 OS-04 | 60 | 0.382 | 0.419 | 0.583 | 0.675 |", out)

  def test_age_offset_sensitivity(self):
    # the 2011 report's upper confidence limit of 15.4 mph raises SH-11 at age 70 to 0.80 (OS-04) and 0.16 (OS-06)
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--age", "--age-offset-mph", "15.4"]), 0)
    self.assertIn("| SH-11 OS-04 | 60 | 0.382 | 0.593 | 0.800 | 0.872 |", buf.getvalue())
    self.assertIn("| SH-11 OS-06 | 18 | 0.048 | 0.081 | 0.156 | 0.220 |", buf.getvalue())
    self.assertLess(rc.AGE_OFFSET_70_30_2011_MPH, rc.AGE_OFFSET_70_30_MPH)

  def test_richards_frontal_fit(self):
    for mph, p in rc.RICHARDS_FRONTAL_POINTS_MPH:
      self.assertAlmostEqual(rc.richards_frontal(mph / rc.MPH_PER_KMH), p, delta=0.005)
    # below Joksch at low delta-v, above it from about 33 mph
    self.assertLess(rc.richards_frontal(25 / rc.MPH_PER_KMH), rc.joksch(25 / rc.MPH_PER_KMH))
    self.assertGreater(rc.richards_frontal(40 / rc.MPH_PER_KMH), rc.joksch(40 / rc.MPH_PER_KMH))

  def test_richards_curve_sensitivity(self):
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--curve", "richards"]), 0)
    out = buf.getvalue()
    self.assertIn("- SH-03 OS-05, ODD-H: 0.638", out)
    self.assertIn("- SH-04 OS-08, ODD-H: 0.037", out)
    with redirect_stdout(io.StringIO()) as buf:
      rc.main([])
    self.assertIn("- SH-03 OS-05, ODD-H: 0.414", buf.getvalue())

  def test_richards_side_fit_and_primary_contacts(self):
    for mph, p in rc.RICHARDS_SIDE_POINTS_MPH:
      self.assertAlmostEqual(rc.richards_side(mph / rc.MPH_PER_KMH), p, delta=0.001)
    # the barrier lateral delta-v is about (1 + e) * sqrt(2 * d * a_y), nearly the same at every speed
    import math
    for v in rc.DEPARTURE_SPEEDS_KMH:
      self.assertAlmostEqual(rc.barrier_lateral_dv_kmh(v), 1.1 * math.sqrt(2 * 4.0 * 3.0) * 3.6, delta=0.5)
    # both primary contacts are below the 24 mph median delta-v of the drivers killed in side impacts
    median_kmh = rc.RICHARDS_SIDE_MEDIAN_FATAL_DV_MPH / rc.MPH_PER_KMH
    self.assertLess(rc.barrier_lateral_dv_kmh(120), median_kmh)
    self.assertLess(rc.lane_change_contact(120)["dv_lateral_kmh"], median_kmh)
    self.assertLess(rc.richards_side(rc.barrier_lateral_dv_kmh(120)), 0.005)

  def test_pedestrian_compare_with_richards(self):
    for p30, p40 in rc.RICHARDS_PEDESTRIAN_15PLUS.values():
      self.assertAlmostEqual(rc.two_point_logistic_mph(30, p30, p40), p30)
      self.assertAlmostEqual(rc.two_point_logistic_mph(40, p30, p40), p40)
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--pedestrian-compare"]), 0)
    out = buf.getvalue()
    # Tefft is above both recent datasets at OS-04 and below only the 1970s data
    self.assertIn("| SH-11 OS-04 | 60 | 0.382 | 0.451 | 0.241 | 0.182 |", out)
    self.assertIn("| SH-11 OS-06 | 18 | 0.048 | 0.002 | 0.005 | 0.004 |", out)

  def test_ashton_elderly_odds_ratio(self):
    # 47 % (60+) against 14 % (15+) at 30 mph
    self.assertAlmostEqual(rc.ashton_elderly_odds_ratio(), (0.47 / 0.53) / (0.14 / 0.86))
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--age"]), 0)
    out = buf.getvalue()
    # OS-04: between the default age-70 bound (0.72) and its upper confidence limit (0.80)
    self.assertIn("| SH-11 OS-04 | 0.382 | 0.771 | 0.771 | 0.721 |", out)
    self.assertIn("| SH-11 OS-06 | 0.048 | 0.214 | 0.114 | 0.099 |", out)

  def test_ashton_child_odds_ratio(self):
    # 4 % (0-14) against 14 % (15+) at 30 mph: children are below the 15+ curve
    self.assertAlmostEqual(rc.ashton_child_odds_ratio(), (0.04 / 0.96) / (0.14 / 0.86))
    self.assertLess(rc.ashton_child_odds_ratio(), 1.0)
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--age"]), 0)
    out = buf.getvalue()
    self.assertIn("| SH-11 OS-04 | 0.382 | 0.137 | 0.224 |", out)
    self.assertIn("| SH-11 OS-06 | 0.048 | 0.013 | 0.023 |", out)

  def test_vehicle_grid_defaults_are_the_worst_corner(self):
    import itertools
    defaults = rc.worst_vehicle_cases(rc.EGO["mass_kg"], rc.LEADS[0]["mass_kg"], rc.LEADS[1]["mass_kg"])
    for masses in itertools.product(*rc.VEHICLE_GRID.values()):
      w = rc.worst_vehicle_cases(*masses)
      for key in ("SH-03 OS-05", "SH-04 OS-08"):
        for odd in ("ODD-H", "ODD-A"):
          self.assertLessEqual(w[(key, odd)], defaults[(key, odd)] + 1e-12)
    self.assertAlmostEqual(defaults[("SH-03 OS-05", "ODD-H")], 0.414, places=3)
    self.assertAlmostEqual(defaults[("SH-04 OS-08", "ODD-A")], 0.040, places=3)
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--vehicles"]), 0)
    self.assertIn("| **max** | | | **0.414** | **0.053** | **0.248** | **0.040** |", buf.getvalue())

  def test_pedestrian_curve_is_monotone(self):
    risks = [rc.pedestrian_fatality(v) for v in range(0, 120, 5)]
    self.assertEqual(risks, sorted(risks))

  def test_sh11_cases_and_mapping(self):
    from tools.severity import severity_ratio as sr
    cases = {sh: v for sh, _, v in rc.vru_cases()}
    self.assertEqual(cases["SH-11 OS-04"], 60)
    self.assertAlmostEqual(cases["SH-11 OS-06"], (2 * 2.0 * 6.0) ** 0.5 * 3.6)
    self.assertNotIn("SH-11", sr.SH_COLLISIONS)

  def test_sh02_curve_departure_angle(self):
    # 90 km/h at 3 m/s^2: R = 625 / 3 m; theta = sqrt(2 * 4 / R)
    import math
    self.assertAlmostEqual(rc.curve_departure_angle_deg(90), math.degrees(math.sqrt(8 * 3 / 625)))
    for v in rc.DEPARTURE_SPEEDS_KMH:
      self.assertLess(rc.curve_departure_angle_deg(v), rc.BARRIER_TEST_ANGLE_DEG)
    self.assertGreater(rc.curve_departure_angle_deg(70), rc.curve_departure_angle_deg(110))

  def test_sh10_contact_is_low_angle_and_low_lateral_speed(self):
    import math
    c = rc.lane_change_contact(90)
    self.assertAlmostEqual(c["v_lat_kmh"], math.sqrt(2 * 3.0 * rc.LANE_CHANGE_GAP_M) * 3.6)
    self.assertLess(c["v_lat_kmh"], 15)
    self.assertLess(max(rc.lane_change_contact(v)["angle_deg"] for v in rc.SH10_SPEEDS_KMH), 25)
    self.assertLess(rc.lane_change_contact(120)["angle_deg"], rc.lane_change_contact(60)["angle_deg"])

  def test_sh10_cli(self):
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--sh10"]), 0)
    self.assertIn("| 120 |", buf.getvalue())

  def test_sh01_straight_road_departure_matches_curve_formula(self):
    import math
    v, a_y, d = 120, 3.0, 4.0
    straight = math.degrees(math.atan(math.sqrt(2 * d * a_y) / (v / 3.6)))
    self.assertAlmostEqual(rc.curve_departure_angle_deg(v, d, a_y), straight, delta=0.1)
    with redirect_stdout(io.StringIO()) as buf:
      self.assertEqual(rc.main(["--sh01"]), 0)
    self.assertIn("| 120 |", buf.getvalue())

  def test_joksch_constant_sensitivity_flag(self):
    try:
      with redirect_stdout(io.StringIO()) as buf:
        self.assertEqual(rc.main(["--joksch-mph", "61.54"]), 0)
      self.assertIn("SH-03 OS-05, ODD-H: 0.734", buf.getvalue())
    finally:
      rc.JOKSCH_MPH = rc.JOKSCH_MPH_DEFAULT
    self.assertAlmostEqual(rc.JOKSCH_MPH_DEFAULT * 0.44704, 31.74, places=2)

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
