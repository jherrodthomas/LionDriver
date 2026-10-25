#!/usr/bin/env python3
"""Checks of the cranking-dip model (crank.py): what would catch a wrong netlist, solver set-up or input.

C1  ngspice against the closed form: a capacitor discharging into a resistor follows V0 exp(-t/RC) (0.5 %).
C2  The behavioural regulators do what params.yaml says, on a slow ramp of the supply: the buck holds 5 V, follows the
    input less its headroom in dropout and stops below its lockout; the LDO holds 3.3 V or the 5 V rail less 0.3 V.
C3  Power balance: before the dip the device's input power is its 5 V load and the MCU's draw over the buck's
    efficiency (2 %).
C4  The profile is ISO 16750-2's as TI reproduces it (SCPS268A Table 10-5, transcribed here independently), and the
    car's supply node follows it.

Runs in the environment of `supply-linux-64.lock`. Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crank  # noqa: E402

P = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))


class Checks(unittest.TestCase):
  def test_c1_rc_discharge(self):
    R, C, V0 = 10.0, 100e-6, 12.0
    w = crank.simulate(f"* RC\nC1 a 0 {C} IC={V0}\nR1 a 0 {R}\n.tran 1e-6 5e-3 0 1e-6 uic\n.end\n", ["v(a)"])
    t = w["time"]
    exact = V0 * np.exp(-t / (R * C))
    sel = t > 1e-5
    self.assertLess(np.abs(w["v(a)"][sel] / exact[sel] - 1).max(), 0.005)

  def test_c2_regulators(self):
    pts = [(0.0, 14.0), (0.002, 14.0), (2.0, 2.0)]
    w = crank.simulate(crank.deck(P, pts, crank.parts(P, "nominal"), 2.0, 1e-4), ["v(vin)", "v(v5)", "v(v33)"])
    vin, v5, v33 = w["v(vin)"], w["v(v5)"], w["v(v33)"]
    b, ldo = P["buck"], P["ldo"]
    reg = vin > b["vout"] + b["headroom"] + 0.1
    drop = (vin < b["vout"] + b["headroom"] - 0.1) & (vin > b["uvlo"]["value"] + 0.2)
    off = vin < b["uvlo"]["value"] - 0.3
    self.assertLess(np.abs(v5[reg] - b["vout"]).max(), 0.05)
    self.assertLess(np.abs(v5[drop] - (vin[drop] - b["headroom"])).max(), 0.05)
    self.assertTrue(off.any() and v5[off].min() < 0.5)
    on = vin > b["uvlo"]["value"] + 0.2
    want = np.minimum(ldo["vout"], v5[on] - ldo["dropout"])
    self.assertLess(np.abs(v33[on] - want).max(), 0.03)

  def test_c3_power_balance(self):
    pts = [(0.0, 14.0), (0.05, 14.0)]
    w = crank.simulate(crank.deck(P, pts, crank.parts(P, "nominal"), 0.05, 1e-5), ["v(vin)", "v(v5)", "v(v33)", "vcar#branch"])
    i = -w["vcar#branch"][-1]                       # ngspice: a source's current flows into its + node
    v5, v33 = w["v(v5)"][-1], w["v(v33)"][-1]
    p_out = P["load_5v"]["power"] + v5 * v33 / (P["ldo"]["vout"] / P["mcu_load"]["current"])
    self.assertLess(abs(i * w["v(vin)"][-1] / (p_out / P["buck"]["efficiency"]) - 1), 0.02)

  def test_c4_profile(self):
    table = {"I": (8.0, 9.5, 1.0, 0.040), "II": (4.5, 6.5, 10.0, 0.100), "IV": (6.0, 6.5, 10.0, 0.100)}
    pr = P["profile"]
    self.assertEqual((pr["ub"], pr["tf"], pr["t6"], pr["t7"]), (14.0, 0.005, 0.015, 0.050))
    for lv, (us6, us, t8, tr) in table.items():
      d = pr["levels"][lv]
      self.assertEqual((d["us6"], d["us"], d["t8"], d["tr"]), (us6, us, t8, tr))
    pts = crank.profile_points(P, "II")
    w = crank.simulate(crank.deck(P, pts, crank.parts(P, "nominal"), 0.2, 1e-5), ["v(car)"])
    mid = crank.T0 + pr["tf"] + pr["t6"] / 2
    self.assertAlmostEqual(float(np.interp(mid, w["time"], w["v(car)"])), 4.5, places=3)
    self.assertAlmostEqual(float(w["v(car)"][-1]), 6.5, places=3)


if __name__ == "__main__":
  unittest.main(verbosity=2)
