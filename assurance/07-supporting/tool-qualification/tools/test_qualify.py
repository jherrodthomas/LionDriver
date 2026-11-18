#!/usr/bin/env python3
"""Tests of the TQR-32 validation (qualify.py) and its figures (fig_tq.py)."""

import copy
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "figures"))
import qualify as q  # noqa: E402
import fig_tq  # noqa: E402


class TestQualify(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.faults = q.load_faults()
    cls.items, cls.links = q.load_real()

  def test_every_check_has_a_planted_fault(self):
    # a new check in check_trace.py fails here until the catalogue plants a fault for it (method.md §6)
    src = Path(q.ct.__file__).read_text(encoding="utf-8")
    tags = set(re.findall(r'rep\.err\("([A-Z]+\d+)"', src))
    self.assertGreaterEqual(len(tags), 15)
    self.assertEqual(sorted(tags - {f["expect"] for f in self.faults}), [])

  def test_every_error_class_of_the_method_is_planted(self):
    md = (q.FOLDER / "method.md").read_text(encoding="utf-8")
    classes = set(re.findall(r"^\| (EC-\d+) ", md, re.M))
    self.assertEqual(len(classes), 10)
    self.assertEqual(classes, {f["class"].split(" ")[0] for f in self.faults})

  def test_a_wrong_expectation_is_reported_missed(self):
    f = copy.deepcopy(self.faults[0])
    f["match"] = "text the tool never prints"
    _, res = q.run_catalogue([f], self.items, self.links)
    self.assertFalse(res[0]["caught"])

  def test_a_stale_target_is_refused(self):
    f = {"id": "PF-X", "class": "EC-1 broken link", "what": "", "expect": "K3", "match": "",
         "op": {"set": {"item": "TSR-999", "field": "parents", "value": []}}}
    with self.assertRaises(q.QualifyError):
      q.run_catalogue([f], self.items, self.links)

  def test_a_fault_that_changes_nothing_is_refused(self):
    f = {"id": "PF-X", "class": "EC-7 missing attribute", "what": "", "expect": "K1", "match": "",
         "op": {"set": {"item": "SG-01", "field": "status", "value": "proposed"}}}
    with self.assertRaises(q.QualifyError):
      q.run_catalogue([f], self.items, self.links)

  def test_committed_results_current(self):
    r = q.build()
    self.assertTrue(all(f["caught"] for f in r["faults"]), [f["id"] for f in r["faults"] if not f["caught"]])
    self.assertTrue(all(m["killed"] for m in r["mutants"]), [m["id"] for m in r["mutants"] if not m["killed"]])
    self.assertEqual(q.OUT_MD.read_text(encoding="utf-8"), q.markdown(r))


class TestFigures(unittest.TestCase):
  def test_committed_figures_current(self):
    for name, content in fig_tq.build().items():
      self.assertEqual((fig_tq.HERE / name).read_text(encoding="utf-8"), content, name)

  def test_figures_draw_every_step_guard_and_fault(self):
    f1, f2 = fig_tq.build().values()
    for g in fig_tq.guards():
      self.assertIn(f">{g['id']}<", f1)
    self.assertEqual(len(fig_tq.steps()), 5)
    for f in q.load_faults():
      self.assertIn(f">{f['id']}<", f2)
    for mid, _, _ in q.MUTANTS:
      self.assertIn(f">{mid}<", f2)


if __name__ == "__main__":
  unittest.main()
