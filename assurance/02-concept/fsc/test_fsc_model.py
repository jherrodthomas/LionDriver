#!/usr/bin/env python3
"""Tests for fsc_model.py (WP-P-07 TL-35, OI-12).

Each completeness rule of check() has a one-entry change to the real model that must make it fail, and the real
model must pass. The model is patched in memory only; no file is written.

Run from the repository root:  python3 -m unittest discover -s assurance/02-concept/fsc -p 'test_*.py' -v
Standard library only.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fsc_model", HERE / "fsc_model.py")
fm = importlib.util.module_from_spec(_spec)
sys.modules["fsc_model"] = fm
_spec.loader.exec_module(fm)


def relevant_node_with(pred):
  for n in fm.NODES:
    if n[3]:
      for sg, c in fm.COVERAGE[n[0]].items():
        if pred(c):
          return n[0], sg
  raise AssertionError("no such entry")


class TestCheck(unittest.TestCase):
  def setUp(self):
    self.cov = copy.deepcopy(fm.COVERAGE)
    self.md = fm.coverage_md()  # the table as committed; isolates the rule under test from the staleness rule

  def errs(self):
    with mock.patch.object(fm, "COVERAGE", self.cov), mock.patch.object(fm, "coverage_md", lambda: self.md):
      return fm.check()

  def test_real_model_passes(self):
    self.assertEqual(fm.check(), [])

  def test_omitted_entry_is_an_error_not_not_relevant(self):
    nid, sg = relevant_node_with(lambda c: c is not None)
    del self.cov[nid][sg]
    self.assertIn(f"{sg}/{nid}: no coverage entry (list the FSRs, or NA with the goal's not-relevant reason)",
                  self.errs())

  def test_missing_node_is_reported_not_crashed(self):
    nid, _ = relevant_node_with(lambda c: True)
    del self.cov[nid]
    errs = self.errs()
    self.assertTrue(any(e.endswith(f"/{nid}: no coverage entry (list the FSRs, or NA with the goal's not-relevant "
                                   "reason)") for e in errs), errs)

  def test_entry_without_fsrs(self):
    nid, sg = relevant_node_with(lambda c: c is not None)
    self.cov[nid][sg] = ([], "note")
    self.assertIn(f"{sg}/{nid}: no FSR and no reason", self.errs())

  def test_undefined_fsr(self):
    nid, sg = relevant_node_with(lambda c: c is not None)
    self.cov[nid][sg] = (["FSR-99.99"], "note")
    self.assertIn(f"{sg}/{nid}: FSR-99.99 is not defined in WP-C-04", self.errs())

  def test_unknown_goal_key(self):
    nid, _ = relevant_node_with(lambda c: True)
    self.cov[nid]["SG-99"] = fm.NA
    self.assertIn(f"{nid}: unknown safety goal key", self.errs())

  def test_unused_fsr(self):
    # remove every citation of one FSR: it must be reported as not cited
    fsr = sorted(fm.defined_fsrs())[0]
    for nid in self.cov:
      for sg, c in list(self.cov[nid].items()):
        if c and fsr in c[0]:
          rest = [f for f in c[0] if f != fsr] or ["FSR-01.01" if fsr != "FSR-01.01" else "FSR-01.02"]
          self.cov[nid][sg] = (rest, c[1])
    self.assertTrue(any(e.startswith("FSRs in WP-C-04 not cited") and fsr in e for e in self.errs()))

  def test_stale_table(self):
    with mock.patch.object(fm, "coverage_md", lambda: self.md + "x"):
      self.assertIn("fsc-coverage.md is stale - run python3 fsc_model.py", fm.check())


class TestModel(unittest.TestCase):
  def test_every_relevant_node_has_every_goal(self):
    for n in fm.NODES:
      if n[3]:
        self.assertEqual(set(fm.COVERAGE[n[0]]), set(fm.SGS), n[0])

  def test_not_relevant_reason_for_every_goal(self):
    self.assertEqual(set(fm.NOT_RELEVANT), set(fm.SGS))

  def test_block_diagram_references_resolve(self):
    ids = {n[0] for n in fm.NODES}
    for n in fm.NODES:
      for ref in n[4] + n[5]:
        self.assertIn(ref, ids, n[0])


if __name__ == "__main__":
  unittest.main()
