#!/usr/bin/env python3
"""Tests for box_model.py: node citations agree with the wiring drawings, the box topology matches the v3 drawing as
transcribed there, outputs are current, and the headline predictions keep their physics."""

import csv
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import box_model as bm

WIRING = bm.HERE.parent / "wiring"


def wire_ends() -> dict:
  with open(WIRING / "wire-ends.tsv", encoding="utf-8") as f:
    return {r["id"]: r for r in csv.DictReader(f, delimiter="\t")}


class TestCitations(unittest.TestCase):
  def test_every_node_cites_a_wire_end_or_a_readme_row(self):
    ends = wire_ends()
    readme = (WIRING / "README.md").read_text(encoding="utf-8")
    for node, (_, cite) in bm.NODES.items():
      if cite.startswith("README 3: "):
        part = cite.split(": ", 1)[1]
        self.assertIn(f"| {part} |", readme, f"{node}: {part} not in the wiring README section 3 table")
      else:
        self.assertIn(cite, ends, f"{node}: {cite} not in wire-ends.tsv")

  def test_switch_pins_match_the_box_drawing(self):
    # the netlist's COM/NC/NO assignment must be the one the wiring drawing shows for U1 and U2
    hb = yaml.safe_load((WIRING / "e05-harness-box.yaml").read_text(encoding="utf-8"))
    u1 = dict(zip(hb["connectors"]["U1"]["pins"], hb["connectors"]["U1"]["pinlabels"]))
    u2 = dict(zip(hb["connectors"]["U2"]["pins"], hb["connectors"]["U2"]["pinlabels"]))
    self.assertIn("CAN2_H camera", u1[1])
    self.assertIn("CAN0_H car", u1[2])
    self.assertIn("CAN0_L car", u2[1])
    self.assertIn("CAN2_L camera", u2[2])
    net = "\n".join(bm.box("pass"))
    self.assertIn("RU1NC can2h can0h", net)
    self.assertIn("RU2NC can0l can2l", net)
    self.assertIn("RU1NO can2h can2hp", net)
    self.assertIn("RU2NO can0l can0lp", net)

  def test_switch_state_swaps_nc_and_no(self):
    p, i = "\n".join(bm.box("pass")), "\n".join(bm.box("intercept"))
    self.assertIn(f"RU1NC can2h can0h {bm.p('R_ON'):g}", p)
    self.assertIn(f"RU1NC can2h can0h {bm.p('R_OFF'):g}", i)


class TestOutputs(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out = bm.build()
    with open(bm.OUT_TSV, encoding="utf-8") as f:
      cls.rows = {r["id"]: r for r in csv.DictReader(f, delimiter="\t")}

  def test_committed_outputs_current(self):
    for name, text in self.out.items():
      self.assertEqual((bm.HERE / name).read_text(encoding="utf-8"), text, f"{name} stale; run box_model.py")

  def test_deterministic(self):
    self.assertEqual(bm.build(), self.out)

  def test_every_row_names_its_bench_case(self):
    for r in self.rows.values():
      self.assertRegex(r["prediction for"], r"VS-HW-2[234]")

  def test_says_prediction_not_evidence(self):
    self.assertIn("not measurements. No FMEDA credit", self.out[bm.OUT_MD.name])

  def test_physics_of_headline_rows(self):
    r = self.rows
    # nominal termination: about 2-3 V dominant, fast recessive edge
    self.assertEqual(r["T-nominal/intercept"]["verdict"], "levels OK")
    # unterminated camera bus misses the sample point
    self.assertIn("too slow", r["T-both-open/intercept"]["verdict"])
    # a CAN_H short to ground kills dominant on the joined bus in pass-through: the stock path fails too
    self.assertEqual(r["C-D3-H-gnd/pass"]["verdict"], "dominant lost")
    # the bench drive through 1 kohm reaches only the 240 ohm divider voltage, 5 * 240 / 1240
    self.assertAlmostEqual(float(r["I-bench-1k/sbu1"]["dominant Vdiff or IN (V)"]), 5 * 240 / 1240, places=2)
    # with the pull-down open the leakage sign decides the rail
    self.assertGreater(float(r["I-open+/sbu1"]["dominant Vdiff or IN (V)"]), 10)
    self.assertLess(float(r["I-open-/sbu1"]["dominant Vdiff or IN (V)"]), 0.5)


class TestAgreesWithSimHarnessBox(unittest.TestCase):
  """Cross-check with assurance/sim/harness_box (agreed with the simulation session, option c): the two models of the
  same box keep the same shared values and reach the same answers where their cases overlap. A mismatch fails here
  first; one topology source replaces this test at the switch-level campaign."""

  SIM = bm.HERE.parent.parent / "sim"

  @classmethod
  def setUpClass(cls):
    cls.params = yaml.safe_load((cls.SIM / "harness_box" / "params.yaml").read_text(encoding="utf-8"))
    import json
    res = json.loads((cls.SIM / "results" / "harness-box.json").read_text(encoding="utf-8"))
    cls.sim = {s["id"]: s for s in res["scenarios"]}
    with open(bm.OUT_TSV, encoding="utf-8") as f:
      cls.rows = {r["id"]: r for r in csv.DictReader(f, delimiter="\t")}

  def test_same_pull_down(self):
    self.assertEqual(self.params["pull_down"]["value"], bm.p("R_PULLDOWN"))

  def test_vin_inside_their_band(self):
    lo, hi = self.params["vin"]["band"]
    self.assertTrue(lo <= bm.p("VIN") <= hi)

  def test_same_sbu1_drive_divider(self):
    # their nominal drive (5 V through r_out into R2/R3) gives the same SBU1 in both netlists, within their 5 mV
    d = self.params["drive"]
    r = bm.sbu1_case(pulldown=True, leak=0.0, src=d["v"]["value"], r_src=d["r_out"]["value"])
    self.assertAlmostEqual(r["vin_node"], self.sim["intercept"]["nodes"]["SBU1"], delta=0.005)

  def test_pull_down_open_settles_on_the_leakage_rail(self):
    vin_sim = self.sim["pulldown_open_leak_up"]["nodes"]["VIN"]
    self.assertGreater(self.sim["pulldown_open_leak_up"]["nodes"]["SBU1"], 0.5 * vin_sim)
    self.assertGreater(float(self.rows["I-open+/sbu1"]["dominant Vdiff or IN (V)"]), 0.5 * bm.p("VIN"))
    self.assertLess(self.sim["pulldown_open_leak_down"]["nodes"]["SBU1"], 0.5)
    self.assertLess(float(self.rows["I-open-/sbu1"]["dominant Vdiff or IN (V)"]), 0.5)

  def test_d2_short_to_gnd_loses_dominant_in_both(self):
    self.assertIn("NOT dominant", self.sim["clamp_short"]["verdict"])
    self.assertEqual(self.rows["C-D2-H-gnd/pass"]["verdict"], "dominant lost")


if __name__ == "__main__":
  unittest.main()
