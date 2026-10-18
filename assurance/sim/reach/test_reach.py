#!/usr/bin/env python3
"""Tests of the reachability bound (assurance/sim/reach, README §3.6)."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reach_compare as C  # noqa: E402
from reach_inputs import envelope, expm  # noqa: E402


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

  def test_every_sample_inside(self):
    """Every linear-model run inside the exact bound; every plant run inside it widened by the measured
    linearisation error."""
    c = C.containment(self.ex, self.s)
    for k, x in c.items():
      self.assertLessEqual(x, C.TOL, k)


if __name__ == "__main__":
  unittest.main()
