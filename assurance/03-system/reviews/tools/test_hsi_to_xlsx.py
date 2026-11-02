#!/usr/bin/env python3
"""Tests for hsi_to_xlsx.py: it runs on the current WP-S-05, and every sheet has its header and data rows."""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parents[2]
SHEETS = ["00_Title_Page", "01_Document_Control", "02_HSI_Signal_Catalog", "03_Register_Map", "04_Timing_Specification",
          "05_Failure_Modes_and_Reactions", "06_Initialization_Sequence", "07_Cross_Reference", "09_Test_Cases", "10_References"]


class TestHsiToXlsx(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.TemporaryDirectory()
    out = Path(cls.tmp.name) / "hsi-input.xlsx"
    cls.res = subprocess.run([sys.executable, str(HERE / "hsi_to_xlsx.py"), str(ASSURANCE), str(out)], capture_output=True, text=True)
    cls.wb = openpyxl.load_workbook(out) if out.exists() else None

  @classmethod
  def tearDownClass(cls):
    cls.tmp.cleanup()

  def test_runs(self):
    self.assertEqual(self.res.returncode, 0, self.res.stderr)
    self.assertRegex(self.res.stdout, r"signals=\d+ regs=\d+ timing=\d+ fm=\d+ init=\d+ tests=\d+")

  def test_sheets(self):
    self.assertEqual(self.wb.sheetnames, SHEETS)

  def test_every_sheet_has_header_and_rows(self):
    for name in SHEETS:
      rows = list(self.wb[name].iter_rows(values_only=True))
      self.assertGreater(len(rows), 1, f"{name} has no data rows")
      if name != "00_Title_Page":
        self.assertTrue(all(rows[0]), f"{name} header has an empty cell: {rows[0]}")

  def test_signal_catalogue_and_cross_reference(self):
    sig = list(self.wb["02_HSI_Signal_Catalog"].iter_rows(values_only=True))[1:]
    self.assertTrue(sig)
    self.assertTrue(all(re.match(r"S-\d\d \S", r[0]) for r in sig), sig[0])
    xref = list(self.wb["07_Cross_Reference"].iter_rows(values_only=True))[1:]
    self.assertEqual([r[0] for r in xref], [f"HSI-{k:02d}" for k in range(1, 15)])


if __name__ == "__main__":
  unittest.main()
