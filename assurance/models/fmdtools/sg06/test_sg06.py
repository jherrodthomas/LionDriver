#!/usr/bin/env python3
"""Tests for the SG-06 fault-propagation model (tool evaluation TE-02, extended by DQ-417; step P1).

Mapping: every event of the WP-A-04 §7 SG-06 tree has a model mode or a latent entry, every mode names a tree event,
and every event is in the FTA <-> FMEA map. Behaviour: the nominal run is clean, every mode runs, and reference cases
taken from the WP-A-04 §7.1 cut-set table give the expected result. The cases where the model and the table differ
are pinned as such: the siren covers a SoC crash and a selfdrived stop (as in SG-02), and the host's ACC cancel on an
immediate disable changes the cluster cruise indicator, so the tree's latent tag on BE-6.06 is out of date for them.
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


def tree_events(goal: str) -> set[str]:
  _, cut_sets = td.solve(goal)
  return {e for cs in cut_sets for e in cs}


class TestMapping(unittest.TestCase):
  def test_every_tree_event_has_a_mode_or_is_latent(self):
    events = tree_events(m.EVENTS["goal"])
    covered = set(m.MODE_OF) | {e["id"] for e in m.EVENTS["latent_in_model"]}
    self.assertEqual(events - covered, set(), "tree events with no model mode")
    self.assertEqual(covered - events, set(), "model modes that name no SG-06 tree event")

  def test_every_event_is_in_the_fta_fmea_map(self):
    fmap = yaml.safe_load((ROOT / "assurance/08-analyses/fta-fmea-map.yaml").read_text(encoding="utf-8"))
    mapped = {e["id"] for e in fmap["events"]}
    covered = set(m.MODE_OF) | {e["id"] for e in m.EVENTS["latent_in_model"]}
    self.assertEqual(covered - mapped, set())

  def test_modes_are_unique(self):
    pairs = [(x["function"], x["mode"]) for x in m.EVENTS["modes"]]
    self.assertEqual(len(pairs), len(set(pairs)))
    self.assertEqual(len(m.MODE_OF), len(m.EVENTS["modes"]))

  def test_every_timing_has_a_source(self):
    for k, v in m.EVENTS["timing"].items():
      self.assertTrue(v.get("source"), k)


class TestBehaviour(unittest.TestCase):
  def test_nominal_run_is_clean(self):
    o = m.run()
    self.assertIsNone(o.t_lost)
    self.assertFalse(o.top_event)

  def test_every_mode_is_a_fault_of_its_function(self):
    mdl = m.Sg06()
    for event, (fxn, mode) in m.MODE_OF.items():
      self.assertIn(mode, mdl.fxns[fxn].m.get_all_faultnames(), event)

  def assertTop(self, events, expected, note=""):
    o = m.run(events)
    self.assertEqual(o.top_event, expected, f"{'+'.join(events)}: {o.line()} {note}")

  def test_cut_sets_the_model_reproduces(self):
    self.assertTop(("BE-6.04",), True, "MCS-06.4: silent loss, BE-2.11 latent")
    self.assertTop(("BE-6.05",), True, "MCS-06.6: BE-1.22 latent")
    self.assertTop(("BE-6.09",), True, "MCS-06.10: the FCW comes from the same lead, BE-6.10 latent")
    self.assertTop(("BE-6.01", "BE-2.10"), True, "MCS-06.1: soft disable, cancel only after 3 s, no siren")
    self.assertTop(("BE-6.01", "BE-1.20"), True, "MCS-06.1: diagnostics masked")
    self.assertTop(("BE-6.02", "BE-2.09"), True, "MCS-06.2")
    self.assertTop(("BE-6.03", "UE-6.08"), True, "MCS-06.11: PCM silent")
    self.assertTop(("BE-6.03", "BE-2.12"), True, "MCS-06.3: no cancel credit for a PCM that does not execute ACC")
    self.assertTop(("BE-2.06", "BE-2.17"), True, "MCS-06.7")
    self.assertTop(("BE-2.06", "BE-2.12"), True, "MCS-06.8: no frames, so no cancel")
    self.assertTop(("BE-6.02", "BE-2.13"), True, "MCS-06.8: the envelope blocks the cancel; the guard's siren is late")
    self.assertTop(("BE-2.07", "UE-6.07"), True, "MCS-06.9")

  def test_single_causes_that_are_covered(self):
    self.assertTop(("BE-6.01",), False, "alert at 0.1 s")
    self.assertTop(("BE-6.03",), False, "accFaulted, immediate disable")
    self.assertTop(("BE-2.07",), False, "driver feels the end of ACC deceleration")

  def test_where_the_model_differs_from_the_table(self):
    # MCS-06.5 holds BE-2.14 latent. As in SG-02, the siren sounds on a heartbeat loss (0.25 s) and on the engaged
    # mismatch after a selfdrived stop (0.88 s), so each needs a siren failure too. Finding, not an error here.
    self.assertTop(("BE-2.05",), False, "heartbeat-loss siren")
    self.assertTop(("BE-2.05", "BE-2.22"), True)
    self.assertTop(("BE-2.21",), False, "engaged-mismatch siren")
    self.assertTop(("BE-2.21", "BE-2.14"), True)
    # MCS-06.8 holds BE-6.06 latent. An immediate disable sets the ACC cancel (TSR-303), so the cluster cruise
    # indicator changes within 0.7 s, and a cancel without effect gets the cancel-lag siren (TSR-516(c)): an HMI
    # failure needs both BE-6.06 and a siren failure.
    o = m.run(("BE-6.01", "BE-2.12"))
    self.assertEqual((o.cue, round(o.t_cue, 2), o.top_event), ("cluster", 0.7, False))
    o = m.run(("BE-6.01", "BE-2.12", "BE-6.06"))
    self.assertEqual((o.cue, round(o.t_cue, 2), o.top_event), ("siren", 0.86, False))
    self.assertTop(("BE-6.01", "BE-2.12", "BE-6.06", "BE-2.14"), True)


class TestPhases(unittest.TestCase):
  def test_phases(self):
    self.assertEqual(list(m.PHASES), ["following", "approach"])
    self.assertEqual(m.DEFAULT_PHASE, "approach")

  def test_supply_loss_while_following_gives_no_cue(self):
    # MCS-06.9 relies on the driver noticing the end of ACC deceleration; while following at a steady gap there is
    # little to notice (assumption in events.yaml phases)
    self.assertTrue(m.run(("BE-2.07",), phase="following").top_event)
    self.assertFalse(m.run(("BE-2.07",), phase="approach").top_event)


class TestTiming(unittest.TestCase):
  def test_late_cues_are_timed(self):
    o = m.run(("BE-6.01", "BE-2.10"), horizon_s=6.0)
    self.assertEqual((o.cue, round(o.t_cue, 2)), ("cluster", 3.6))   # cancel only once the soft disable ends
    o = m.run(("BE-2.21", "BE-2.22"), horizon_s=6.0)
    self.assertAlmostEqual(o.t_cue - o.t_lost, 4.9, places=6)


if __name__ == "__main__":
  unittest.main()
