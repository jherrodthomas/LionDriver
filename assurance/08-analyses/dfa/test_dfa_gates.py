#!/usr/bin/env python3
"""Tests for dfa_gates.py: the shared-resource rule, the checks, and a build of the real records."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dfa_gates as D

RES = [
  {"id": "R-A", "name": "power", "category": "power", "elements": ["E-01", "E-03"], "dfis": ["DFI-01"]},
  {"id": "R-B", "name": "host only", "category": "shared part", "elements": ["E-01", "E-02"], "dfis": ["DFI-14"]},
  {"id": "R-C", "name": "audio", "category": "shared part", "elements": ["E-01"], "unknown": ["E-03"], "dfis": ["DFI-23"]},
]


class SharedTests(unittest.TestCase):
  def test_a_resource_counts_only_across_inputs_in_different_elements(self):
    gate = {"inputs": {"cause": ["E-01", "E-02"], "soc warning": ["E-01"], "siren": ["E-03"]}}
    got = {r["id"]: maybe for r, maybe in D.shared(gate, RES)}
    self.assertEqual(got, {"R-A": False, "R-C": True})   # R-B reaches the two host inputs only

  def test_inputs_in_one_element_share_nothing(self):
    self.assertEqual(D.shared({"inputs": {"a": ["E-03"], "b": ["E-03"]}}, RES), [])

  def test_claims_may_be_one_or_a_list(self):
    self.assertEqual(D.claims_of({"claim": "IC-01"}), ["IC-01"])
    self.assertEqual(D.claims_of({"claim": ["IC-01", "IC-03"]}), ["IC-01", "IC-03"])
    self.assertEqual(D.claims_of({"claim": None}), [])


class RecordTests(unittest.TestCase):
  def test_every_tree_and_gate_is_classified_and_the_outputs_are_current(self):
    out = D.build()
    for path, text in out.items():
      self.assertEqual(path.read_text(encoding="utf-8"), text, f"{path.name} is stale")

  def test_an_unclassified_gate_and_a_changed_input_are_errors(self):
    tree = D.tree_gates()
    gates, elements, res, dfis, claims = D.load()
    g = next(iter(gates))
    missing = {k: v for k, v in gates.items() if k != g}
    self.assertTrue(any(g in e for e in D.validate(tree, missing, elements, res, dfis, claims)))
    changed = dict(gates)
    changed[g] = {**gates[g], "inputs": {"X": ["E-01"]}}
    self.assertTrue(any("differ from the tree" in e for e in D.validate(tree, changed, elements, res, dfis, claims)))

  def test_the_pcm_gates_are_reported_without_a_claim(self):
    rows, no_claim, *_ = D.analyse()
    self.assertIn("G3.1", no_claim)
    self.assertNotIn("G1.1.1.a", no_claim)


if __name__ == "__main__":
  unittest.main()
