#!/usr/bin/env python3
"""Tests for tsc_to_xlsx.py: it runs on the current documents, every sheet has its header and rows, and a renamed
heading or key stops it with a plain message naming what is missing (no traceback, no bare KeyError)."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tsc_to_xlsx as tsc

ASSURANCE = HERE.parents[2]
TOOL = HERE / "tsc_to_xlsx.py"


def run(root, out):
  return subprocess.run([sys.executable, str(TOOL), str(root), str(out)], capture_output=True, text=True)


class TestCurrentDocuments(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = tempfile.TemporaryDirectory()
    out = Path(cls.tmp.name) / "tsc-input.xlsx"
    cls.res = run(ASSURANCE, out)
    cls.wb = openpyxl.load_workbook(out) if out.exists() else None

  @classmethod
  def tearDownClass(cls):
    cls.tmp.cleanup()

  def rows(self, name):
    return list(self.wb[name].iter_rows(values_only=True))

  def test_runs(self):
    self.assertEqual(self.res.returncode, 0, self.res.stderr)
    self.assertRegex(self.res.stdout, r"fsrs=\d+ tsrs=\d+ mechs=\d+ arch=\d+ hsi=\d+ timing=\d+ fmea=\d+ dfa=\d+")

  def test_sheets(self):
    self.assertEqual(self.wb.sheetnames, tsc.SHEETS)

  def test_every_sheet_has_header_and_rows(self):
    for name in tsc.SHEETS:
      rows = self.rows(name)
      self.assertGreater(len(rows), 1, f"{name} has no data rows")
      if name != "00_Title_Page":
        self.assertTrue(all(rows[0]), f"{name} header has an empty cell: {rows[0]}")
        self.assertTrue(any(any(c not in (None, "") for c in r) for r in rows[1:]), f"{name} rows are all empty")

  def test_hsi_sheet_is_the_interface_summary(self):
    rows = self.rows("06_HSI_Specification")[1:]
    self.assertEqual(len(rows), 14)
    self.assertTrue(all(re.match(r"HSI-\d\d \S", r[0]) for r in rows), rows[0])
    self.assertEqual(rows[0][0], "HSI-01 SoC ↔ MCU SPI link")

  def test_fmea_sheet_from_system_fmea(self):
    rows = self.rows("08_System_FMEA")[1:]
    self.assertTrue(all(re.match(r"SFM-\d{3} ", r[1]) for r in rows), rows[0])
    self.assertTrue(all(re.fullmatch(r"SG-\d\d(, SG-\d\d)*", r[4]) for r in rows if r[4]))
    self.assertGreater(sum(bool(r[4]) for r in rows), len(rows) // 2)

  def test_every_fsr_has_a_goal_and_ftti(self):
    for r in self.rows("02_FSRs_From_FSC")[1:]:
      self.assertRegex(r[1], r"^SG-\d\d$", r[0])
      self.assertRegex(r[6], r"^\d+$", r[0])  # FTTI in ms from WP-C-04 §3, written as text like every cell


class TestPlainErrors(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.root = Path(self.tmp.name) / "assurance"
    for rel in tsc.SOURCES.values():
      (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
      shutil.copy(ASSURANCE / rel, self.root / rel)

  def tearDown(self):
    self.tmp.cleanup()

  def edit(self, doc, pattern, repl):
    path = self.root / tsc.SOURCES[doc]
    text, n = re.subn(pattern, repl, path.read_text(encoding="utf-8"), flags=re.M)
    self.assertGreater(n, 0, f"pattern {pattern!r} not found in {doc}")
    path.write_text(text, encoding="utf-8")

  def assertPlainFailure(self, *needles):
    res = run(self.root, Path(self.tmp.name) / "out.xlsx")
    self.assertEqual(res.returncode, 2, res.stdout + res.stderr)
    self.assertNotIn("Traceback", res.stderr)
    self.assertNotIn("KeyError", res.stderr)
    self.assertTrue(res.stderr.startswith("tsc_to_xlsx: "), res.stderr)
    for s in needles:
      self.assertIn(s, res.stderr)
    self.assertFalse((Path(self.tmp.name) / "out.xlsx").exists())

  def test_renamed_hsi_heading(self):
    self.edit("WP-S-05", r"^\| HSI \| Interface \|", "| HSI | Interface name |")
    self.assertPlainFailure("WP-S-05", "§2 interface summary", "missing 'Interface'", "2. Interface summary")

  def test_renamed_tsr_heading(self):
    self.edit("WP-S-02", r"^(\| ID \| Requirement[^|]*\| ASIL \|) Parent \|", r"\1 Parents |")
    self.assertPlainFailure("WP-S-02", "missing 'Parent'")

  def test_renamed_fmea_key(self):
    self.edit("system-fmea.yaml", r"^(\s+)failure_mode:", r"\1mode:")
    self.assertPlainFailure("system-fmea.yaml", "key 'failure_mode' not found")

  def test_missing_source(self):
    (self.root / tsc.SOURCES["WP-S-04"]).unlink()
    self.assertPlainFailure("WP-S-04", "not found")


if __name__ == "__main__":
  unittest.main()
