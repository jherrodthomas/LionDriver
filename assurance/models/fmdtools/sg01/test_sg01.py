#!/usr/bin/env python3
"""Tests for the SG-01 fault-propagation model (tool evaluation TE-02, extended by DQ-417; step P1).

Mapping: every event of the WP-A-04 §2 SG-01 tree has a model mode or a latent entry, every mode names a tree event,
and every event is in the FTA <-> FMEA map. Behaviour: every phase is clean without a fault, every mode runs, and
reference cases taken from the WP-A-04 §2.1 cut-set table give the expected result. The cases where the model and
the machine-readable tree differ are pinned as such.
"""

import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import model as m  # noqa: E402
import treediff as td  # noqa: E402


class TestMapping(unittest.TestCase):
  def test_every_tree_event_has_a_mode_or_is_latent(self):
    _, cut_sets = td.solve(m.EVENTS["goal"])
    events = {e for cs in cut_sets for e in cs}
    covered = set(m.MODE_OF) | {e["id"] for e in m.EVENTS["latent_in_model"]}
    self.assertEqual(events - covered, set(), "tree events with no model mode")
    self.assertEqual(covered - events, set(), "model modes that name no SG-01 tree event")

  def test_every_event_is_in_the_fta_fmea_map(self):
    fmap = yaml.safe_load((ROOT / "assurance/08-analyses/fta-fmea-map.yaml").read_text(encoding="utf-8"))
    covered = set(m.MODE_OF) | {e["id"] for e in m.EVENTS["latent_in_model"]}
    self.assertEqual(covered - {e["id"] for e in fmap["events"]}, set())

  def test_modes_are_unique_and_timed(self):
    pairs = [(x["function"], x["mode"]) for x in m.EVENTS["modes"]]
    self.assertEqual(len(pairs), len(set(pairs)))
    for k, v in m.EVENTS["timing"].items():
      self.assertTrue(v.get("source"), k)


class TestBehaviour(unittest.TestCase):
  def test_every_phase_is_clean_without_a_fault(self):
    for ph in m.PHASES:
      self.assertFalse(m.run_phase((), ph).top_event, ph)

  def test_every_mode_is_a_fault_of_its_function(self):
    mdl = m.Sg01()
    for event, (fxn, mode) in m.MODE_OF.items():
      self.assertIn(mode, mdl.fxns[fxn].m.get_all_faultnames(), event)

  def assertTop(self, events, branch, note=""):
    o = m.run(events)
    self.assertEqual(o.branch, branch, f"{'+'.join(events)}: {o.line()} {note}")

  def test_cut_sets_the_model_reproduces(self):
    self.assertTop(("BE-1.01", "UE-1.11"), "excess", "MCS-01.1")
    self.assertTop(("BE-1.10", "UE-1.11"), "excess", "MCS-01.2")
    self.assertTop(("BE-1.02", "BE-1.06", "UE-1.11"), "excess", "MCS-01.6")
    self.assertTop(("BE-1.24", "BE-1.07", "UE-1.11"), "excess", "MCS-01.6, SPI corruption")
    self.assertTop(("BE-1.13",), "unwanted", "MCS-01.4: one stuck RX path feeds envelope and SoC")
    self.assertTop(("BE-1.14", "BE-1.15"), "unwanted", "MCS-01.7")
    self.assertTop(("BE-1.15", "BE-1.25"), "unwanted", "MCS-01.7")
    self.assertTop(("BE-1.08", "BE-1.15"), "unwanted", "MCS-01.10")
    self.assertTop(("BE-1.19",), "stale", "MCS-01.8: BE-1.22, BE-1.23 latent")
    self.assertTop(("BE-1.20",), "stale", "MCS-01.8")
    self.assertTop(("BE-1.21",), "stale", "MCS-01.8: replayed frames keep arriving")
    self.assertTop(("BE-4.19", "BE-4.21"), "overlap", "MCS-01.11")
    self.assertTop(("BE-1.26", "BE-4.21"), "overlap", "MCS-01.11")

  def test_excess_needs_the_eps_to_fail(self):
    self.assertIsNone(m.run(("BE-1.01",)).branch)
    self.assertIsNone(m.run(("BE-1.02", "BE-1.06")).branch)

  def test_single_points_the_envelope_covers(self):
    self.assertIsNone(m.run(("BE-1.02", "UE-1.11")).branch, "the clamp refuses the command")
    self.assertIsNone(m.run(("BE-4.19",)).branch, "relay malfunction detected in 0.005 s (plant F-06a)")


class TestWhereTheModelDiffers(unittest.TestCase):
  def test_stuck_cruise_frame_is_a_single_point(self):
    # MCS-01.9 holds BE-1.15 as a separate event; the SoC reads the same stuck frame, so on a cancel it keeps the
    # item engaged and commanding (DFI-10, "effective 1" in the table)
    o = m.run_phase(("BE-1.17",), "cancel")
    self.assertEqual((o.branch, o.t), ("unwanted", 0.3))
    self.assertFalse(m.run_phase(("BE-1.17",), "brake").top_event, "the brake frame shows the disengagement")

  def test_stuck_brake_frame_is_covered_by_the_cruise_frame(self):
    # MCS-01.9 {BE-1.16, BE-1.15}: a brake press also drops PCM cruise, so the envelope revokes on 0x1D2 (TSR-301)
    for ph in m.PHASES:
      self.assertFalse(m.run_phase(("BE-1.15", "BE-1.16"), ph).top_event, ph)
    self.assertTrue(m.run_phase(("BE-1.16", "BE-1.17"), "brake").top_event)

  def test_false_edge_is_revoked_by_the_next_genuine_frame(self):
    # MCS-01.7 {BE-1.12, BE-1.15}: one corrupted frame opens the window; the next genuine 0x1D2 revokes
    self.assertFalse(m.run(("BE-1.12", "BE-1.15")).top_event)

  def test_debug_build_needs_a_soc_fault(self):
    # MCS-01.5 {BE-1.18} is a single point in the tree; without an envelope the SoC still gates its own command
    self.assertFalse(m.run(("BE-1.18",)).top_event)
    self.assertTrue(m.run(("BE-1.15", "BE-1.18")).top_event)


if __name__ == "__main__":
  unittest.main()
