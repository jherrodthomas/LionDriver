#!/usr/bin/env python3
"""Tests for harness_box.py: ngspice against closed forms, the shared netlist, the Falstad text. Needs ngspice
(../supply/supply-linux-64.lock environment)."""

import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_box as hb


class TestAgainstClosedForm(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.p = hb.load_params()
    cls.v = hb.values(cls.p, {})

  def solve(self, switches=None, **override):
    v = hb.values(self.p, override)
    return v, hb.run_spice(hb.spice_deck(hb.circuit(v, switches or {})))

  def test_intercept_divider(self):
    v, n = self.solve()
    sbu1 = v["drive_v"] * v["pull_down"] / (v["pull_down"] + v["drive_r"])   # leak paths are 1e8, below 1 mV here
    self.assertAlmostEqual(n["SBU1"], sbu1, delta=1e-3)
    self.assertAlmostEqual(n["VTH"], v["k"] * v["vin"], delta=1e-6)

  def test_floating_input_follows_its_leakage(self):
    v, n = self.solve({"drive": False, "pulldown": False}, leak_hi=1e7, leak_lo=1e9)
    self.assertAlmostEqual(n["SBU1"], v["vin"] * 1e9 / (1e7 + 1e9), delta=1e-3)

  def test_ignition_sense(self):
    v, off = self.solve({"q6": False})
    self.assertAlmostEqual(off["SBU2"], v["pu_v"], delta=1e-3)
    _, short = self.solve({"q6": False, "q6_short": True})
    self.assertAlmostEqual(short["SBU2"], v["pu_v"] * v["r1"] / (v["r1"] + v["pu_r"]), delta=1e-3)

  def test_can_clamp_short_pulls_canh_down(self):
    v, n = self.solve({"clamp_leak": True}, leak_r=1.0)
    g = 1 / v["drv_r"] + 1 / v["bus_r"] + 1 / 1.0
    self.assertAlmostEqual(n["CANH"], (v["dom_v"] / v["drv_r"] + v["rec_v"] / v["bus_r"]) / g, delta=1e-3)


class TestShared(unittest.TestCase):
  def test_netlist_from_coordinates(self):
    els = hb.circuit(hb.values(hb.load_params(), {}), {})
    n = hb.nets(els)
    self.assertEqual(n[(64, 96)], "vin")
    self.assertEqual(n[(320, 128)], "vin")          # joined by the VIN label
    self.assertEqual(n[(320, 224)], "sbu1")         # joined by the wire
    self.assertEqual(n[(192, 384)], "0")

  def test_falstad_numbers_have_no_plus(self):
    self.assertEqual(hb.num(1e8), "100000000")      # Falstad reads 1e+08 as 1
    self.assertEqual(hb.num(1e12), "1e12")
    self.assertEqual(hb.num(240.0), "240")
    text = hb.falstad_text(hb.circuit(hb.values(hb.load_params(), {}), {}))
    self.assertNotIn("e+", text)

  def test_switch_states_drawn(self):
    p = hb.load_params()
    open_pd = hb.falstad_text(hb.circuit(hb.values(p, {}), {"pulldown": False}))
    self.assertIn("s 192 224 192 288 0 1 false", open_pd)          # 1 = open in Falstad
    self.assertIn("s 192 160 192 224 0 0 false", open_pd)          # 0 = closed

  def test_link_carries_the_circuit(self):
    p = hb.load_params()
    text = hb.falstad_text(hb.circuit(hb.values(p, {}), {}))
    link = hb.falstad_link(text)
    self.assertTrue(link.startswith(hb.FALSTAD_URL))
    self.assertEqual(urllib.parse.unquote(link.split("cct=", 1)[1]), text)

  def test_scenario_ids_unique_and_cited(self):
    s = hb.scenarios(hb.load_params())
    self.assertEqual(len({x.id for x in s}), len(s))
    self.assertTrue({"DFM-010.C3", "DFM-011.C2", "DFM-014.C2", "DFM-021.C1"} <= {x.fmea for x in s})


if __name__ == "__main__":
  unittest.main()
