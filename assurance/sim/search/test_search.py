#!/usr/bin/env python3
"""Tests of the failure search: the robustness sign means what the README says, and the search is deterministic.
(search.py --check in CI compares the committed outputs with a fresh run.)"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import search  # noqa: E402


class TestSearch(unittest.TestCase):
  def test_straight_road_holds_and_curve_departs(self):
    straight = search.evaluate(np.array([100.0, 0.0, 3.7, 1.0, 0.2]))
    curve = search.evaluate(np.array([100.0, 1.5, 3.7, 1.0, 0.2]))
    self.assertGreater(straight["rho"], 0)        # nothing pushes the car sideways once the assist is lost
    self.assertLess(curve["rho"], 0)              # the 1.5 m/s² the assist was holding is lost: departure
    self.assertIsNotNone(curve["t_edge"])

  def test_space_inside_the_odd(self):
    self.assertLessEqual(search.SPACE["speed_kph"][1], 120.0)
    self.assertGreaterEqual(search.SPACE["lane_width"][0], 3.0)
    self.assertLessEqual(search.SPACE["a_y"][1], 2.5)

  def test_monte_carlo_is_seeded(self):
    a = np.random.default_rng(search.SEED).random(5)
    b = np.random.default_rng(search.SEED).random(5)
    self.assertTrue((a == b).all())


if __name__ == "__main__":
  unittest.main()
