#!/usr/bin/env python3
"""Tests for fig_speed.py: committed SVGs current, sources present, constants and formulas drawn as the code has them."""

import math
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_speed as fs


class TestSpeedFigures(unittest.TestCase):
  def setUp(self):
    self.f = fs.facts()

  def test_committed_output_current(self):
    for name, s in fs.build_all().items():
      self.assertEqual((fs.OUT_DIR / name).read_text(encoding="utf-8"), s, f"stale {name}; run fig_speed.py")

  def test_svgs_parse_and_have_title(self):
    for name, s in fs.build_all().items():
      self.assertIsNotNone(ET.fromstring(s).find("{http://www.w3.org/2000/svg}title"), name)

  def test_sources_present(self):
    self.assertEqual(fs.problems(), [])

  def test_mpc_grid(self):
    self.assertEqual(len(self.f["t_idxs"]), int(self.f["n"]) + 1)
    self.assertAlmostEqual(self.f["t_idxs"][-1], self.f["max_t"])

  def test_personalities_ordered(self):
    t = self.f["t_follow"]
    self.assertGreater(t["relaxed"], t["standard"])
    self.assertGreater(t["standard"], t["aggressive"])

  def test_lead_extrapolation_matches_formula(self):
    # constant braking (tau 0) reaches standstill at v0 / a0 on the MPC's grid; a large tau keeps most of v0
    v = fs.lead_traj(self.f, 25.0, -3.0, 0.0)
    self.assertEqual(v[-1], 0.0)
    v = fs.lead_traj(self.f, 25.0, -3.0, self.f["tau_radar"])
    self.assertGreater(v[-1], 20.0)

  def test_tau_after_one_second(self):
    alpha = 0.05 / (self.f["tau_rc"] + 0.05)
    self.assertAlmostEqual(self.f["tau_1s"], self.f["tau_radar"] * (1 - alpha) ** 20)
    self.assertLess(self.f["tau_1s"], self.f["tau_vision"])

  def test_follow_gap_text(self):
    s = fs.build_follow(self.f)
    self.assertIn(f"{self.f['t_follow']['standard'] * 30 + self.f['stop']:.1f} m", s)
    self.assertIn(f"{30 ** 2 / (2 * -fs.ENV['a_min']):.0f} m", s)
    self.assertFalse(math.isnan(self.f["comfort"]))


if __name__ == "__main__":
  unittest.main()
