#!/usr/bin/env python3
"""Self-tests for process_model.py: the committed model passes, and each check rejects a broken copy."""
from __future__ import annotations

import copy
import fnmatch
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

  def test_interface_needs_its_ifr_item(self):
    self.assertFails("P7", lambda m: m.ifrs.pop("IFR-01"))
    self.assertFails("P7", lambda m: m.interfaces["IX-01"].update(ifr="IFR-02"))
    self.assertFails("P7", lambda m: m.ifrs["IFR-01"].update(interface="IX-99"))

  def test_ifr_owners_are_the_lane_roles(self):
    self.assertFails("P7", lambda m: m.ifrs["IFR-01"].update(owners=["Safety manager", "SOTIF lead"]))

  def test_status_is_read_from_the_ifr_item(self):
    model = copy.deepcopy(self.base)
    ix = model.interfaces["IX-13"]
    self.assertEqual(pm.ix_status(model, ix), "open")
    model.ifrs["IFR-13"].update(open_item=None)
    self.assertEqual(pm.ix_status(model, ix), "documented")
    model.ifrs["IFR-13"].update(status="agreed", review_ref="REV-001")
    self.assertEqual(pm.ix_status(model, ix), "agreed")
    orders = pm.check(model, self.ctx)
    sk = pm.render_gate_skeleton("G2", orders["G2"], model, self.ctx)
    self.assertIn("| IFR-13 | IX-13 |", sk)
    self.assertIn("| REV-001 | Yes |", sk)

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

  def test_update_of_non_living_work_product(self):
    self.assertFails("P3", lambda m: m.activities["REL-10"].update(updates=["WP-K-01", "WP-C-03"]))

  def test_update_outside_living_range(self):
    self.assertFails("P3", lambda m: m.activities["CON-13"].update(updates=["WP-K-01"]))

  def test_input_from_later_update(self):
    self.assertFails("P5", lambda m: m.activities["REL-09"]["inputs"].append("WP-K-01"))

  def test_assessor_report_counts_as_confirmation_of_its_inputs(self):
    model = copy.deepcopy(self.base)
    orders = pm.check(model, self.ctx)
    g5 = pm.render_phase("G5", orders["G5"], model, self.ctx)
    line = next(ln for ln in g5.splitlines() if ln.startswith("**Work products with no confirmation measure"))
    for wp in ("WP-K-03", "WP-K-04", "WP-K-05", "WP-V-06"):
      self.assertNotIn(wp, line)

  def test_feedback_into_a_later_phase(self):
    self.assertFails("P9", lambda m: m.feedback["FB-01"].update(targets=["WP-O-05"]))

  def test_feedback_source_neither_produced_nor_updated_in_its_phase(self):
    # WP-O-04 is produced at G1 and updated at G6 (DQ-122 A); without the G6 update its G6 feedback has no source there
    self.assertFails("P9", lambda m: m.activities["OPS-01"].update(updates=[]))

  def test_feedback_anchor_missing(self):
    self.assertFails("P9", lambda m: m.feedback["FB-03"].update(anchors=["WP-O-04:no such routing row"]))

  def test_gate_without_measures_renders_without_empty_lane(self):
    model = copy.deepcopy(self.base)
    orders = pm.check(model, self.ctx)
    g6 = pm.render_phase("G6", orders["G6"], model, self.ctx)
    self.assertNotIn("L_assess", g6)
    self.assertIn("none planned at this gate", g6)
    self.assertNotRegex(g6, r"\n  class +review")

  def test_plan_role_table_is_parsed(self):
    roles = pm.load_plan_roles("x\n| Role | Holder (today) | Duty |\n|---|---|---|\n| SOTIF lead | A. Person | x |\n\nafter")
    self.assertEqual(roles, {"SOTIF lead": "A. Person"})

  def test_role_disagreement_is_reported(self):
    ctx = copy.deepcopy(self.ctx)
    ctx.roles["SOTIF lead"] = ("TBD", "G1")
    ctx.plan_roles["WP-M-08"] = {"SOTIF lead": "A. Person"}
    self.assertTrue(any(c.startswith("SOTIF lead:") for c in pm.role_disagreements(ctx, self.base)))
    ctx.roles["SOTIF lead"] = ("B. Person", "G1")
    self.assertFalse(any(c.startswith("SOTIF lead:") for c in pm.role_disagreements(ctx, self.base)))

  def test_record_patterns_follow_confirmation_readme(self):
    self.assertEqual(pm.record_pattern("CR-02"), "CR-02-*.md")
    self.assertEqual(pm.record_pattern("CR-06@G2"), "CR-06-*.md")
    self.assertEqual(pm.record_pattern("SR-04@G3"), "SR-04-G3.md")
    self.assertEqual(pm.record_pattern("FSA-I1"), "FSA-I1.md")
    self.assertTrue(fnmatch.fnmatch("CR-02-WP-C-03-v1.0.md", pm.record_pattern("CR-02")))

  def test_record_wp_counts_only_when_approved(self):
    fsa = self.base.reviews["FSA-F"]
    self.assertFalse(pm.record_present(fsa, self.ctx.register))
    reg = copy.deepcopy(self.ctx.register)
    reg["WP-K-04"].status = "A"
    self.assertTrue(pm.record_present(fsa, reg))

  def test_gate_skeleton_is_marked_and_complete(self):
    model = copy.deepcopy(self.base)
    orders = pm.check(model, self.ctx)
    for gid in pm.GATES:
      sk = pm.render_gate_skeleton(gid, orders[gid], model, self.ctx)
      self.assertIn("Generated skeleton, not a gate review record", sk)
      for heading in ("## Inputs (WP-M-02 §10)", "## Exit criteria (WP-M-00 §2)", "## Outcome"):
        self.assertIn(heading, sk)
      participants = next(ln for ln in sk.splitlines() if ln.startswith("| Participants |"))
      self.assertEqual(participants.count("Safety manager ("), 1)

  def test_transitive_edges_removed(self):
    acts = {"A": {"inputs": []}, "B": {"inputs": ["a"]}, "C": {"inputs": ["a", "b"]}}
    self.assertEqual(pm.direct_deps(acts, {"a": "A", "b": "B"}), {"A": set(), "B": {"A"}, "C": {"B"}})


if __name__ == "__main__":
  unittest.main()
