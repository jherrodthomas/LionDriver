#!/usr/bin/env python3
"""Checks of the L2 steering column FMU (TL-44 detection, WP-P-07 §3): analytic steady states and step response,
and back-to-back with the L1 EPS on the same command sequence.

Runs where omc 1.27.1 is available (the 'simulation L2 column' CI job). Elsewhere it skips, unless REQUIRE_OMC=1.
"""

import math
import os
import shutil
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build_column_fmu  # noqa: E402

HAVE_OMC = bool(os.environ.get("OMC") or shutil.which("omc"))
if not HAVE_OMC and os.environ.get("REQUIRE_OMC") == "1":
  raise SystemExit("REQUIRE_OMC=1 but omc is not available")


@unittest.skipUnless(HAVE_OMC, "omc not available (set REQUIRE_OMC=1 to fail instead)")
class TestColumn(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.fmu = str(build_column_fmu.build())

  def run_fmu(self, t_d, t_cmd, stop=5.0, params=None):
    import fmpy
    sig = np.array([(0.0, t_d, t_cmd), (stop, t_d, t_cmd)], dtype=[("time", "f8"), ("T_d", "f8"), ("T_cmd", "f8")])
    return fmpy.simulate_fmu(self.fmu, stop_time=stop, output_interval=0.001, input=sig, start_values=params or {},
                             output=["T_tb", "th_sw", "th_l", "T_m"])

  def test_steady_states(self):
    k_r = 200.0
    r = self.run_fmu(0.0, 1.0)                      # hands off: the rack holds the motor torque
    self.assertAlmostEqual(r["th_l"][-1], 1.0 / k_r, delta=1e-5)
    self.assertAlmostEqual(r["T_tb"][-1], 0.0, delta=1e-4)
    r = self.run_fmu(2.0, 0.0)                      # driver only: the torsion bar carries the driver torque
    self.assertAlmostEqual(r["T_tb"][-1], 2.0, delta=1e-3)
    self.assertAlmostEqual(r["th_l"][-1], 2.0 / k_r, delta=1e-5)
    r = self.run_fmu(0.0, 5.0)                      # the motor limit
    self.assertAlmostEqual(r["T_m"][-1], 3.0, delta=1e-6)

  def test_step_response_analytic(self):
    tau = 0.12
    r = self.run_fmu(0.0, 1.0, stop=1.0)
    want = 1.0 - np.exp(-r["time"] / tau)
    self.assertLess(float(np.max(np.abs(r["T_m"] - want))), 1e-3)

  def test_back_to_back_with_l1_eps(self):
    """The FMU motor torque against the L1 EPS (plant.EPS) for the same command sequence: on, hold, off."""
    import corolla
    from plant import EPS
    d = corolla.as_dict()
    eps = EPS(d, frame_timeout=1.0)
    dt, t, l1 = 0.005, 0.0, []
    seq = [(0.0, 0.5, 1500), (0.5, 1.2, 1500), (1.2, 2.0, 0)]
    for _t0, t1, cmd in seq:
      while t < t1 - 1e-9:
        eps.frame(t, cmd, 1)
        eps.step(t, dt)
        t += dt
        l1.append((t, eps.torque / 1500.0))
    import fmpy
    sig = np.array([(0.0, 0.0, 1.0), (1.2 - 1e-9, 0.0, 1.0), (1.2, 0.0, 0.0), (2.0, 0.0, 0.0)],
                   dtype=[("time", "f8"), ("T_d", "f8"), ("T_cmd", "f8")])
    r = fmpy.simulate_fmu(self.fmu, stop_time=2.0, output_interval=0.001, input=sig, output=["T_m"],
                          start_values={"T_m_max": 1.0, "tau_m": d["tau_eps"]})
    err = max(abs(np.interp(tl, r["time"], r["T_m"]) - v) for tl, v in l1)
    # the L1 EPS is a forward-Euler lag at 5 ms: it leads the exact lag by up to dt/(2 tau) of the step (≈ 2 %)
    self.assertLess(err, 0.03, f"L2 and L1 motor torque differ by {err:.3f} of full scale")
    self.assertTrue(math.isfinite(err))


if __name__ == "__main__":
  unittest.main()
