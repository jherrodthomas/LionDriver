#!/usr/bin/env python3
"""Tests for the SG-03 fault-propagation model (tool evaluation TE-02, extended by DQ-417; step P1).

Mapping: every event of the WP-A-04 §3 SG-03 tree has a model mode or a latent entry, every mode names a tree event,
and every event is in the FTA <-> FMEA map. Behaviour: every phase is clean without a fault, every mode runs, and
reference cases taken from the WP-A-04 §3.1 cut-set table give the expected result. The cases where the model and
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
    self.assertEqual(covered - events, set(), "model modes that name no SG-03 tree event")

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
    mdl = m.Sg03()
    for event, (fxn, mode) in m.MODE_OF.items():
      self.assertIn(mode, mdl.fxns[fxn].m.get_all_faultnames(), event)

  def assertTop(self, events, branch, note=""):
    o = m.run(events)
    self.assertEqual(o.branch, branch, f"{'+'.join(events)}: {o.line()} {note}")

  def test_cut_sets_the_model_reproduces(self):
    self.assertTop(("BE-3.01", "UE-3.05"), "excess", "MCS-03.1")
    self.assertTop(("BE-3.04", "UE-3.05"), "excess", "MCS-03.2")
    self.assertTop(("BE-4.17", "UE-3.05"), "excess", "MCS-03.3: no jerk limit in the envelope, BE-3.03 latent")
    self.assertTop(("BE-3.06", "UE-3.08"), "closing", "MCS-03.4: BE-3.07 latent")
    self.assertTop(("BE-3.02", "BE-4.16", "UE-3.05"), "excess", "MCS-03.8")
    self.assertTop(("BE-1.14", "BE-3.13"), "unwanted", "MCS-03.9")
    self.assertTop(("BE-1.25", "BE-3.13"), "unwanted", "MCS-03.9")
    self.assertTop(("BE-3.10", "BE-3.13"), "unwanted", "MCS-03.10")
    self.assertTop(("BE-3.11", "UE-3.12"), "gas", "MCS-03.11")
    self.assertTop(("BE-1.21",), "stale", "MCS-03.7: replayed frames keep arriving, BE-1.22 latent")
    self.assertTop(("BE-4.19", "BE-4.21"), "overlap", "MCS-03.12")
    self.assertTop(("BE-4.20", "BE-4.21"), "overlap", "MCS-03.12")

  def test_single_points_the_envelope_or_pcm_covers(self):
    self.assertIsNone(m.run(("BE-3.02", "UE-3.05")).branch, "the clamp refuses the request")
    self.assertIsNone(m.run(("BE-3.01",)).branch, "the PCM bounds the request")
    self.assertIsNone(m.run(("BE-3.11",)).branch, "the PCM does not add the item's request to the pedal")


class TestWhereTheModelDiffers(unittest.TestCase):
  def test_unseen_brake_is_a_single_point(self):
    # MCS-03.6 {BE-3.09, BE-3.13}: the SoC reads the same frames, so with the brake unseen and ACC kept it stays
    # engaged and keeps requesting acceleration (DFI-10, "effective through DFI-10" in the table)
    o = m.run_phase(("BE-3.09",), "brake")
    self.assertEqual((o.branch, o.t), ("unwanted", 0.3))

  def test_stuck_cruise_path_is_a_single_point(self):
    self.assertTrue(m.run_phase(("BE-1.13",), "cancel").top_event, "MCS-03.9, DFI-10")

  def test_stale_model_is_removed_within_the_ftti(self):
    # MCS-03.7 {BE-1.19, BE-1.22}: TSR-602 drops longActive at 0.52 s, inside the 1 s SG-03 FTTI
    self.assertFalse(m.run(("BE-1.19",)).top_event)

  def test_false_edge_is_revoked_by_the_next_genuine_frame(self):
    self.assertFalse(m.run(("BE-1.12", "BE-3.13")).top_event)


if __name__ == "__main__":
  unittest.main()
