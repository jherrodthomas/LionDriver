#!/usr/bin/env python3
"""Tests for the SG-02 fault-propagation model (TE-02, steps P1 to P3).

Mapping: every event of the WP-A-04 SG-02 tree has a model mode or a latent entry, every mode names a tree event, and
every event is in the FTA <-> FMEA map. Behaviour: the nominal run is clean, every mode runs, and reference cases
taken from the WP-A-04 §4.1 cut-set table give the expected result. Two cases where the model and the table differ
are pinned as such: they are the kind of finding step P3 reports (the revocation siren covers EPS faults, so the
latent tag on BE-2.14 is out of date for them).
"""

import json
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "assurance/08-analyses/fta"))
import model as m  # noqa: E402
import fta_cutsets as fc  # noqa: E402
import fta_diagrams as fd  # noqa: E402


def tree_events(goal: str) -> set[str]:
  trees = fd.parse_document(fd.SOURCE.read_text(encoding="utf-8"))
  fd.resolve(trees)
  solver = fc.Solver(trees)
  solver.finish()
  tree = next(t for t in trees if t.goal == goal)
  return {e for cs in solver.cut_sets(tree.root) for e in cs}


class TestMapping(unittest.TestCase):
  def test_every_tree_event_has_a_mode_or_is_latent(self):
    events = tree_events(m.EVENTS["goal"])
    covered = set(m.MODE_OF) | {e["id"] for e in m.EVENTS["latent_in_model"]}
    self.assertEqual(events - covered, set(), "tree events with no model mode")
    self.assertEqual(covered - events, set(), "model modes that name no SG-02 tree event")

  def test_every_event_is_in_the_fta_fmea_map(self):
    fmap = yaml.safe_load((ROOT / "assurance/08-analyses/fta-fmea-map.yaml").read_text(encoding="utf-8"))
    mapped = {e["id"] for e in fmap["events"]}
    covered = set(m.MODE_OF) | {e["id"] for e in m.EVENTS["latent_in_model"]}
    self.assertEqual(covered - mapped, set())

  def test_modes_are_unique(self):
    pairs = [(x["function"], x["mode"]) for x in m.EVENTS["modes"]]
    self.assertEqual(len(pairs), len(set(pairs)))
    self.assertEqual(len(m.MODE_OF), len(m.EVENTS["modes"]))


class TestBehaviour(unittest.TestCase):
  def test_nominal_run_is_clean(self):
    o = m.run()
    self.assertIsNone(o.t_lost)
    self.assertFalse(o.top_event)

  def test_every_mode_is_a_fault_of_its_function(self):
    mdl = m.Sg02()
    for event, (fxn, mode) in m.MODE_OF.items():
      self.assertIn(mode, mdl.fxns[fxn].m.get_all_faultnames(), event)

  def assertTop(self, events, expected, note=""):
    o = m.run(events)
    self.assertEqual(o.top_event, expected, f"{'+'.join(events)}: {o.line()} {note}")

  def test_cut_sets_the_model_reproduces(self):
    self.assertTop(("BE-2.04",), True, "MCS-02.4: silent loss, BE-2.11 latent")
    self.assertTop(("BE-2.02", "BE-2.09"), True, "MCS-02.2")
    self.assertTop(("BE-2.01", "UE-2.19"), True, "MCS-02.10: silent EPS drop")
    self.assertTop(("BE-2.06", "BE-2.17"), True, "MCS-02.8")
    self.assertTop(("BE-2.07", "UE-2.18"), True, "MCS-02.7")
    self.assertTop(("BE-2.23", "BE-2.24"), True, "MCS-02.12")
    self.assertTop(("BE-2.03", "BE-2.10"), True, "MCS-02.3")
    self.assertTop(("BE-2.03", "BE-1.20"), True, "MCS-02.3")
    self.assertTop(("BE-2.02", "BE-2.12"), True, "MCS-02.6")

  def test_single_causes_that_are_covered(self):
    self.assertTop(("BE-2.01",), False, "alert at 0.1 s")
    self.assertTop(("BE-2.05",), False, "revocation siren at 0.26 s")
    self.assertTop(("BE-2.07",), False, "driver feels the end of LKA torque")
    self.assertTop(("BE-2.05", "BE-2.22"), True, "MCS-02.5 as dual: heartbeat siren path failed")
    # card stops sending after a selfdrived stop, so the command-arrival check revokes and the siren sounds (T-34)
    self.assertTop(("BE-2.21",), False, "MCS-02.9: revocation siren at 0.38 s, before the 5 s UI")
    self.assertTop(("BE-2.21", "BE-2.22"), True, "MCS-02.9 as dual: siren path failed")

  def test_where_the_model_differs_from_the_table(self):
    # MCS-02.1 and MCS-02.11 hold BE-2.14 latent. The siren sounds about 0.25 s after an EPS fault (revocation siren,
    # TSR-516(b), panda 8a69ccf; plant F-07), so the warning failure alone is not enough: a siren failure is needed too.
    # Finding for step P3, not an error here.
    self.assertTop(("BE-2.01", "BE-2.08"), False, "revocation siren, inside the 1 s budget")
    self.assertTop(("BE-2.01", "BE-2.08", "BE-2.14"), True)
    self.assertTop(("BE-2.20", "BE-7.20", "BE-2.12"), False, "EPS reset is an EPS fault: revocation siren")
    self.assertTop(("BE-2.20", "BE-7.20", "BE-2.12", "BE-2.22"), True)


class TestPhases(unittest.TestCase):
  def test_phases_are_the_three_of_the_plan(self):
    self.assertEqual(list(m.PHASES), ["straight", "curve_entry", "mid_curve"])
    self.assertEqual(m.DEFAULT_PHASE, "mid_curve")

  def test_no_curvature_asked_on_a_straight(self):
    self.assertIsNone(m.run(("BE-2.23",), phase="straight").t_lost)
    self.assertTrue(m.run(("BE-2.23", "BE-2.24"), phase="curve_entry").top_event)

  def test_supply_loss_on_a_straight_gives_no_cue(self):
    # Finding of step P2 (assumption in events.yaml phases): MCS-02.7 relies on the driver feeling the end of LKA torque
    self.assertTrue(m.run(("BE-2.07",), phase="straight").top_event)
    self.assertFalse(m.run(("BE-2.07",), phase="curve_entry").top_event)


class TestJointSweep(unittest.TestCase):
  """Step P3. The sets themselves are checked by `sweep.py joint --check`; here the diff must catch a tree error."""

  def test_an_injected_tree_error_is_caught(self):
    import sweep
    solver, cut_sets = sweep.solve(m.EVENTS["goal"])
    model_sets = [frozenset(c) for c in json.loads(sweep.P3_JSON.read_text(encoding="utf-8"))["sets"]]
    self.assertEqual(sweep.tree_gaps(model_sets, cut_sets, solver.latent), [])
    # drop the cut sets of MCS-02.4 (non-finite command clamped): the diff must report the model's {BE-2.04}
    broken = [c for c in cut_sets if "BE-2.04" not in c]
    self.assertEqual(sweep.tree_gaps(model_sets, broken, solver.latent), [frozenset({"BE-2.04"})])


if __name__ == "__main__":
  unittest.main()
