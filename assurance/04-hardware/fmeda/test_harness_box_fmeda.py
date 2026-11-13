#!/usr/bin/env python3
"""Tests of the harness box component FMEDA (harness_box_fmeda.py)."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_box_fmeda as hb  # noqa: E402


class TestHarnessBoxFmeda(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.data, cls.flow, cls.goals = hb.load()
    cls.r = hb.build()

  def test_every_designator_of_the_drawing_is_a_part(self):
    self.assertEqual({p["ref"] for p in self.r["parts"]}, hb.source_designators())
    self.assertEqual(len(self.r["parts"]), 18)

  def test_a_missing_part_fails(self):
    data = copy.deepcopy(self.data)
    data["parts"] = [p for p in data["parts"] if p["ref"] != "R6"]
    with self.assertRaises(hb.BoxError):
      hb.check_parts(data)

  def test_parts_add_up_to_the_goal_rows(self):
    # every difference is a listed one: the DG419LE split of the SG-001 file
    self.assertEqual([(d["file"], d["row"]) for d in self.r["diffs"]], [("fmeda-sg001", "FMD-C-007")])

  def test_a_changed_rate_or_class_fails(self):
    parts = copy.deepcopy(self.r["parts"])
    next(p for p in parts if p["ref"] == "D4")["rate_fit"] = 2
    with self.assertRaises(hb.BoxError):
      hb.roll_up(parts, self.goals, self.data["known_differences"])
    parts = copy.deepcopy(self.r["parts"])
    next(p for p in parts if p["ref"] == "R7")["modes"][1]["goals"]["SG-07"] = "safe"
    with self.assertRaises(hb.BoxError):
      hb.roll_up(parts, self.goals, self.data["known_differences"])

  def test_a_stale_known_difference_fails(self):
    known = self.data["known_differences"] + [{"file": "fmeda-sg009", "row": "FMD-C-012", "reason": "x"}]
    with self.assertRaises(hb.BoxError):
      hb.roll_up(self.r["parts"], self.goals, known)

  def test_categories_add_up_to_the_rated_parts(self):
    rated = sum(p["rate_fit"] for p in self.r["parts"] if p["rate_fit"] is not None)
    for g, cat in self.r["cat"].items():
      self.assertAlmostEqual(sum(cat.values()), rated, places=9, msg=g)

  def test_workbook_columns_and_empty_reviewer(self):
    wb = hb.workbook(self.r)
    ws = wb["SG-07 FMEDA"]
    rows = list(ws.iter_rows(values_only=True))
    self.assertEqual(rows[0][6], "Reviewed by:")
    self.assertIsNone(rows[0][7])  # left for the independent reviewer
    self.assertEqual(rows[2][:7], ("Part designator", "Part type", "Quan.", "Failure mode", "Effect (S, D, L, #, ?)",
                                   "Lambda (FIT)", "Diagnostic coverage"))
    lam_total, split_total = rows[1][5], sum(x for x in rows[1][7:] if x)
    self.assertAlmostEqual(lam_total, split_total, places=6)

  def test_committed_outputs_current(self):
    self.assertEqual(hb.main(["--check"]), 0)


if __name__ == "__main__":
  unittest.main()
