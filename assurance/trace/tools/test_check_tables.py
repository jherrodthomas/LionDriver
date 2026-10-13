#!/usr/bin/env python3
"""Tests for check_tables.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_tables import check_text


class TestCheckTables(unittest.TestCase):
  def test_consistent_table(self):
    self.assertEqual(check_text("| A | B |\n|---|---|\n| 1 | 2 |\n", "t"), [])

  def test_missing_cell(self):
    errors = check_text("| A | B | C |\n|---|---|---|\n| 1 | 2 |\n", "t")
    self.assertEqual(errors, ["t:3: 2 cells, the table header (line 1) has 3"])

  def test_extra_cell(self):
    # the failure that moved a status text out of its column
    errors = check_text("| ID | Status |\n|---|---|\n| X-1 | old | new |\n", "t")
    self.assertEqual(len(errors), 1)

  def test_text_after_last_pipe_is_a_cell(self):
    # the exact defect of LionDriver#41/#42: the row's closing pipe replaced by a new cell's text
    errors = check_text("| ID | Status |\n|---|---|\n| X-1 | old | new \n", "t")
    self.assertEqual(errors, ["t:3: 3 cells, the table header (line 1) has 2"])

  def test_row_without_outer_pipes(self):
    self.assertEqual(check_text("| A | B |\n|---|---|\n| 1 | 2 |\n", "t"), [])

  def test_escaped_pipe_is_not_a_separator(self):
    self.assertEqual(check_text("| A | B |\n|---|---|\n| a \\| b | 2 |\n", "t"), [])

  def test_pipe_in_code_span_counts(self):
    # GitHub splits cells on an unescaped pipe even inside a code span
    self.assertEqual(len(check_text("| A | B |\n|---|---|\n| `a | b` | 2 |\n", "t")), 1)

  def test_fenced_block_ignored(self):
    self.assertEqual(check_text("```\n| a | b |\n| c |\n```\n", "t"), [])

  def test_tables_separated_by_text(self):
    self.assertEqual(check_text("| A |\n|---|\n\ntext\n\n| A | B |\n|---|---|\n| 1 | 2 |\n", "t"), [])


if __name__ == '__main__':
  unittest.main()
