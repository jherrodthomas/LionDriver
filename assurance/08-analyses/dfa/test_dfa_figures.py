#!/usr/bin/env python3
"""Tests for dfa_figures.py: the per-gate state, the claim attribution of figure 3, and a build of the real records."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dfa_figures as F

POWER = {"id": "R-A", "name": "power", "category": "power", "elements": ["E-01", "E-03"], "dfis": ["DFI-01"]}
AUDIO = {"id": "R-C", "name": "audio", "category": "shared part", "elements": ["E-01"], "unknown": ["E-03"],
         "dfis": ["DFI-23"]}


def gate(claim, shared, kind="independence"):
  return {"gate": "G", "goal": "SG-01", "kind": kind, "claim": claim, "shared": shared, "inputs": {}}


class GateStateTests(unittest.TestCase):
  under = {"IC-01": {"DFI-01"}, "IC-06": {"DFI-23"}}

  def test_a_resource_whose_dfi_is_under_the_claim_is_analysed(self):
    self.assertEqual(F.gate_state(gate("IC-01", [(POWER, False)]), self.under)[0], "analysed")

  def test_a_resource_whose_dfis_are_not_under_the_claim_is_a_gap(self):
    st, ok, gap, _ = F.gate_state(gate("IC-06", [(POWER, False)]), self.under)
    self.assertEqual((st, [r["id"] for r in gap]), ("gap", ["R-A"]))

  def test_an_unknown_dependence_alone_is_unknown(self):
    self.assertEqual(F.gate_state(gate("IC-01", [(POWER, False), (AUDIO, True)]), self.under)[0], "unknown")

  def test_no_claim_and_other_kinds(self):
    self.assertEqual(F.gate_state(gate(None, [(POWER, False)]), self.under)[0], "none")
    self.assertEqual(F.gate_state(gate(None, [], kind="common_cause"), self.under)[0], "other")


class RealRecordTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.d = F.data()
    cls.out = F.build()

  def test_every_claim_a_gate_uses_has_a_place_on_the_boundary(self):
    used = {c for r in self.d["rows"] for c in F.dfa_gates.claims_of(r)}
    self.assertLessEqual(used, set(F.CLAIM_AT))

  def test_every_element_with_a_resource_has_a_place(self):
    deps = {e for r in self.d["res"]["resources"] for e in r["elements"] + r.get("unknown", [])}
    self.assertLessEqual(deps, set(F.PLACES))

  def test_the_states_add_up_to_every_gate(self):
    states = [F.gate_state(r, self.d["under"])[0] for r in self.d["rows"]]
    self.assertEqual(len(states), len(self.d["rows"]))
    self.assertEqual(states.count("none"), len(self.d["no_claim"]))

  def test_figure_3_counts_the_same_gaps_as_dfa_gates(self):
    svg = self.out[F.OUTS["gaps"]]
    self.assertIn(f"{len(self.d['not_under'])} claim-and-resource cells", svg)

  def test_the_outputs_are_current(self):
    stale = [p.name for p, c in self.out.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    self.assertEqual(stale, [], "run dfa_figures.py")


if __name__ == "__main__":
  unittest.main()
