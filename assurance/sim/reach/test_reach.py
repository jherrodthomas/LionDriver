#!/usr/bin/env python3
"""Tests of the reachability pilot (assurance/sim/reach).

The bounds tests read REACH_BOUNDS (a fresh reach.jl output) if set, else the committed bounds.json; they skip when
neither exists unless REQUIRE_BOUNDS=1 (the CI reachability job sets both).
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reach_compare as C  # noqa: E402
from reach_inputs import envelope, expm  # noqa: E402

BOUNDS = Path(os.environ.get("REACH_BOUNDS", C.BOUNDS))


class Inputs(unittest.TestCase):
  def test_envelope_is_the_panda_ramp(self):
    self.assertEqual(envelope(0.0), 15)
    self.assertEqual(envelope(0.0099), 15)
    self.assertEqual(envelope(0.01), 30)
    self.assertEqual(envelope(0.99), 1500)
    self.assertEqual(envelope(2.0), 1500)

  def test_expm_rotation(self):
    w = 3.0
    E = expm(np.array([[0.0, w], [-w, 0.0]]) * 0.7)
    c, s = math.cos(w * 0.7), math.sin(w * 0.7)
    np.testing.assert_allclose(E, [[c, s], [-s, c]], atol=1e-12)

  def test_hard_over_is_the_exact_worst_case(self):
    """The exact bound of the linear model is reached, within the quadrature error, by the hard-over sample."""
    m, s = C.load(C.MODEL), C.load(C.SAMPLES)
    ex = C.exact(m, len(s["t"]))
    i = C.idx(s, s["takeover_s"])
    for v in ("y", "psi"):
      self.assertLessEqual(s[f"lin_{v}_max"][i], ex["env"][v][i] * (1 + 1e-4))
      self.assertGreater(s[f"lin_{v}_max"][i], ex["env"][v][i] * 0.999)
      self.assertLess(ex["env"][v][i], ex["amp"][v][i])


@unittest.skipUnless(BOUNDS.exists() or os.environ.get("REQUIRE_BOUNDS") == "1", "no reach.jl bounds")
class Bounds(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.b, cls.s, cls.m = C.load(BOUNDS), C.load(C.SAMPLES), C.load(C.MODEL)

  def test_every_linear_sample_inside(self):
    c = C.containment(self.b, self.s)
    for v in ("y", "psi"):
      self.assertLessEqual(c[("linear", v)], C.TOL, v)

  def test_every_plant_sample_inside_widened_set(self):
    c = C.containment(self.b, self.s)
    for v in ("y", "psi"):
      self.assertLessEqual(c[("nonlinear", v)], C.TOL, v)

  def test_bound_not_below_exact(self):
    """A sound set can't be tighter than the exact reachable bound (up to the reference's quadrature error)."""
    ex = C.exact(self.m, len(self.s["t"]))
    for v in ("y", "psi"):
      for k in ("amp", "env"):
        for i, e in enumerate(ex[k][v]):
          bound = max(self.b[k][f"{v}_hi"][i], -self.b[k][f"{v}_lo"][i])
          self.assertGreaterEqual(bound, e * (1 - 1e-4) - C.TOL, f"{k} {v} t={self.s['t'][i]}")

  def test_intersection(self):
    for v in ("y", "psi"):
      for i in range(len(self.s["t"])):
        hi = self.b["both"][f"{v}_hi"][i]
        self.assertLessEqual(hi, min(self.b["amp"][f"{v}_hi"][i], self.b["env"][f"{v}_hi"][i]) + 1e-12)


if __name__ == "__main__":
  unittest.main()
