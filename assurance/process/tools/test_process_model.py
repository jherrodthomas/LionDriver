#!/usr/bin/env python3
"""Self-tests for process_model.py: the committed model passes, and each check rejects a broken copy."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import process_model as pm


class ProcessModelTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.base = pm.load_model()
    cls.ctx = pm.load_context()

  def run_check(self, mutate=None) -> list[str]:
    model = copy.deepcopy(self.base)
    model.errors = []
    if mutate:
      mutate(model)
    pm.check(model, self.ctx)
    return model.errors

  def assertFails(self, check: str, mutate) -> None:
    errors = self.run_check(mutate)
    self.assertTrue(any(e.startswith(f"[{check}]") for e in errors), f"expected a {check} error, got {errors}")

  def test_committed_model_passes(self):
    self.assertEqual(self.run_check(), [])

  def test_committed_maps_are_current(self):
    self.assertEqual(pm.main(["process_model.py", "--check"]), 0)

  def test_unknown_role(self):
    self.assertFails("P2", lambda m: m.lanes["sotif"].update(role="SOTIF wizard"))

  def test_unregistered_work_product(self):
    self.assertFails("P3", lambda m: m.activities["CON-01"].update(produces=["WP-C-99"]))

  def test_work_product_in_wrong_phase(self):
    self.assertFails("P3", lambda m: m.activities["CON-13"].update(produces=["WP-T-01", "WP-K-01", "WP-S-01"]))

  def test_g1_work_product_without_activity(self):
    self.assertFails("P4", lambda m: m.activities.pop("CON-12"))

  def test_input_from_later_activity(self):
    self.assertFails("P5", lambda m: m.activities["CON-02"]["inputs"].append("WP-C-03"))

  def test_input_from_later_gate(self):
    self.assertFails("P5", lambda m: m.activities["CON-02"]["inputs"].append("WP-S-01"))

  def test_review_set_differs_from_wp_m_06(self):
    self.assertFails("P6", lambda m: m.reviews.pop("SR-01"))

  def test_missing_anchor_text(self):
    self.assertFails("P7", lambda m: m.interfaces["IX-01"].update(anchors=["WP-C-03:text that is not in the HARA"]))

  def test_open_interface_needs_open_item(self):
    self.assertFails("P7", lambda m: m.interfaces["IX-02"].update(open_item=None))

  def test_review_gate_suffix_matches_phase(self):
    self.assertFails("P6", lambda m: m.reviews["CR-06@G2"].update(phase="G1"))

  def test_mermaid_node_ids_are_plain(self):
    self.assertEqual(pm._nid("CR-06@G2"), "CR_06_G2")

  def test_roles_of_lanes_idle_in_a_phase_are_still_listed(self):
    # The hardware lane has no G2 activity, but WP-M-02 needs its role by G2.
    model = copy.deepcopy(self.base)
    orders = pm.check(model, self.ctx)
    g2 = pm.render_phase("G2", orders["G2"], model, self.ctx)
    self.assertIn("needs by G2:** ", g2)
    self.assertIn("Hardware safety engineer", g2.split("needs by G2:** ")[1].splitlines()[0])

  def test_interface_due_before_its_phase(self):
    self.assertFails("P7", lambda m: m.interfaces["IX-20"].update(due="G3"))

  def test_transitive_edges_removed(self):
    acts = {"A": {"inputs": []}, "B": {"inputs": ["a"]}, "C": {"inputs": ["a", "b"]}}
    self.assertEqual(pm.direct_deps(acts, {"a": "A", "b": "B"}), {"A": set(), "B": {"A"}, "C": {"B"}})


if __name__ == "__main__":
  unittest.main()
