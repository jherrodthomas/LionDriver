#!/usr/bin/env python3
"""Checks of the planner studies (physics plan round 4, phase C). Synthetic (DSR-12), no evidence credit.

  O1  The solver is openpilot's: long_mpc.py's SHA-256 and the constants it reads equal the committed record
      (mpc-source.json), and build/long_mpc.py is byte-identical to openpilot's.
  O2  Steady following: a lead at our speed at the planner's own gap (v·T + STOP_DISTANCE) asks for no braking
      (|a| < 1e-3 m/s²) and the gap holds within 0.1 m for 20 s.
  O3  get_accel_from_plan runs from drive_helpers.py's source: a constant-speed plan gives zero; a plan slowing at a
      constant rate gives that rate.
  O4  A lead braking within the item's bound (2 m/s², relaxed gap) is followed to a stop without impact and without
      reaching the −3.5 m/s² clip.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loop  # noqa: E402
import lead_events as le  # noqa: E402
import mpc_build  # noqa: E402


class Planner(unittest.TestCase):
  def test_o1_source(self):
    self.assertEqual(mpc_build.record(), json.loads(mpc_build.RECORD.read_text(encoding="utf-8")))
    self.assertEqual(mpc_build.sha(mpc_build.BUILD / "long_mpc.py"), mpc_build.sha(mpc_build.SRC))

  def test_o2_steady_following(self):
    v = 110 / 3.6
    gap = le.follow_gap(v, "standard")
    r = loop.run(v, lambda t, x: (True, gap + le.CAR + v * t, v, 0.0), 20.0)
    self.assertLess(max(abs(a) for a in r.a), 1e-3)
    self.assertLess(max(abs(g - gap) for g in r.gap), 0.1)

  def test_o3_accel_from_plan(self):
    t = np.asarray(loop.CONTROL_N_T_IDX, float)
    f = loop.H["get_accel_from_plan"]
    self.assertAlmostEqual(f(np.full(len(t), 20.0), np.zeros(len(t)), t, action_t=0.2), 0.0, places=9)
    self.assertAlmostEqual(f(20.0 - 2.0 * t, np.full(len(t), -2.0), t, action_t=0.4), -2.0, places=6)

  def test_o4_within_bound(self):
    v = 80 / 3.6
    gap = le.follow_gap(v, "relaxed")
    al = 2.0
    def lead(t, x):
      ts = v / al
      tt = min(max(t - 1.0, 0.0), ts)
      return (True, gap + le.CAR + v * min(t, 1.0) + v * tt - al * tt * tt / 2, max(v - al * tt, 0.0),
              -al if 0 < tt < ts else 0.0)
    r = loop.run(v, lead, 25.0, personality=loop.PERSONALITY.relaxed)
    self.assertIsNone(r.impact_v)
    self.assertGreater(min(r.a_cmd), loop.LM.ACCEL_MIN + 1e-3)


if __name__ == "__main__":
  unittest.main(verbosity=2)
