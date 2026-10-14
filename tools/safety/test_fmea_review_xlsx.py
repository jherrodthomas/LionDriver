#!/usr/bin/env python3
"""Tests for the reviewer workbooks (fmea_review_xlsx.py)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint
import fmea_review_xlsx as rx


class TestReviewWorkbook(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.doc = rx.load("sw-fmea")
    cls.wb = rx.build("sw-fmea")
    cls.ws = cls.wb["Worksheet"]

  def test_sheets(self):
    self.assertEqual(self.wb.sheetnames, ["Cover", "Worksheet", "Actions", "Structure"])

  def test_one_row_per_cause(self):
    causes = sum(len(fm["causes"]) for fm in self.doc["failure_modes"])
    self.assertEqual(self.ws.max_row - rx.HEADER_ROWS, causes)

  def test_failure_mode_columns_merged_over_causes(self):
    merged = {(m.min_row, m.max_row) for m in self.ws.merged_cells.ranges if m.min_col == 1}
    row = rx.HEADER_ROWS + 1
    for fm in self.doc["failure_modes"]:
      n = len(fm["causes"])
      if n > 1:
        self.assertIn((row, row + n - 1), merged, fm["id"])
      row += n

  def test_ap_cells_follow_the_rating_table(self):
    col = [h for _, h, _ in rx.COLUMNS].index("AP") + 1
    row = rx.HEADER_ROWS + 1
    for fm in self.doc["failure_modes"]:
      for c in fm["causes"]:
        expected = fmea_lint.compute_ap(fm["severity"], c["occurrence"], c["detection"])
        cell = self.ws.cell(row, col)
        self.assertEqual(cell.value, expected, c["id"])
        self.assertEqual(cell.fill.fgColor.rgb[-6:], rx.AP_STYLE[expected][0], c["id"])
        row += 1

  def test_reviewer_columns_take_a_decision_from_a_list(self):
    dv = self.ws.data_validations.dataValidation
    self.assertEqual(len(dv), 1)
    self.assertIn("Agree", dv[0].formula1)

  def test_every_action_listed(self):
    ids = [r[0].value for r in self.wb["Actions"].iter_rows(min_row=2)]
    self.assertEqual(ids, [a["id"] for a in self.doc["actions"]])

  def test_all_analyses_build(self):
    for name in rx.SOURCES:
      with self.subTest(name=name):
        self.assertIn("Worksheet", rx.build(name).sheetnames)

  def test_committed_workbooks_current(self):
    self.assertEqual(rx.main(["--check"]), 0)


if __name__ == "__main__":
  unittest.main()
