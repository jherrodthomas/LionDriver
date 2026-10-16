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
  @classmethod
  def setUpClass(cls):
    cls.m, cls.s = C.load(C.MODEL), C.load(C.SAMPLES)
    cls.ex = C.exact(cls.m, len(cls.s["t"]))

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
    """The linear model's runs (inputs held per 10 ms) lie within the exact dt bound (held per 5 ms, a superset),
    and the hard-over reaches it to within 0.1 %."""
    i = C.idx(self.s, self.s["takeover_s"])
    for v in C.OUT:
      self.assertLessEqual(self.s[f"lin_{v}_max"][i], self.ex["dt"][v][i] * (1 + 1e-9))
      self.assertGreater(self.s[f"lin_{v}_max"][i], self.ex["dt"][v][i] * 0.999)

  def test_references_ordered(self):
    """Held inputs are a subset of all inputs within the envelope, which are a subset of |u| <= u_max."""
    for v in C.OUT:
      for i in range(1, len(self.s["t"])):
        self.assertLessEqual(self.ex["dt"][v][i], self.ex["ct"][v][i] * (1 + 1e-4), (v, i))
        self.assertLess(self.ex["ct"][v][i], self.ex["amp"][v][i], (v, i))


@unittest.skipUnless(BOUNDS.exists() or os.environ.get("REQUIRE_BOUNDS") == "1", "no reach.jl bounds")
class Bounds(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.b, cls.s, cls.m = C.load(BOUNDS), C.load(C.SAMPLES), C.load(C.MODEL)
    cls.ex = C.exact(cls.m, len(cls.s["t"]))

  def test_every_linear_sample_inside(self):
    c = C.containment(self.b, self.s)
    for v in C.OUT:
      self.assertLessEqual(c[("linear", v)], C.TOL, v)

  def test_every_plant_sample_inside_widened_set(self):
    c = C.containment(self.b, self.s)
    for v in C.OUT:
      self.assertLessEqual(c[("nonlinear", v)], C.TOL, v)

  def test_dt_equals_exact(self):
    """The Julia zonotope recursion and the Python sum compute the same exact bound."""
    for v in C.OUT:
      for i, e in enumerate(self.ex["dt"][v]):
        self.assertAlmostEqual(C.mag(self.b["dt"], v, i), e, delta=1e-7 * max(1.0, e), msg=f"{v} t={self.s['t'][i]}")

  def test_ct_not_below_exact(self):
    """A sound continuous-time set can't be tighter than the exact bound (up to the reference's quadrature error)."""
    for k, r in self.b["ct"].items():
      if "error" in r:
        continue
      for v in C.OUT:
        for i, e in enumerate(self.ex["ct"][v]):
          self.assertGreaterEqual(C.mag(r, v, i), e * (1 - 1e-4) - C.TOL, f"{k} {v} t={self.s['t'][i]}")


if __name__ == "__main__":
  unittest.main()
