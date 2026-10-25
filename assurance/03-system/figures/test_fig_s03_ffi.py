#!/usr/bin/env python3
"""Tests for fig_s03_ffi.py: committed SVG current, every §7 claim drawn once, statuses read as documented."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s03_ffi as ff


class TestFfi(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = ff.SOURCE.read_text(encoding="utf-8")
    cls.rows = ff.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in ff.build().items():
      self.assertEqual((ff.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s03_ffi.py")

  def test_every_claim_once(self):
    ids = [r["id"] for r in self.rows]
    self.assertEqual(ids, re.findall(r"^\| ((?:FFI|DFA|IND)-\d+) \|", self.md, re.M))
    svg = (ff.HERE / ff.OUT).read_text(encoding="utf-8")
    for i in ids:
      self.assertEqual(svg.count(f">{i}<"), 1)

  def test_classify(self):
    self.assertEqual(ff.classify("Partial")[0], "partial")
    self.assertEqual(ff.classify("**Not met** (GAP-24, GAP-38)")[0], "not")
    self.assertEqual(ff.classify("**Not met** (GAP-09); 2026-10-12: **Partial** (reference build lock)"),
                     ("partial", "Partial (reference build lock)"))
    self.assertEqual(ff.classify("Unknown")[0], "open")
    self.assertEqual(ff.classify("Open")[0], "open")
    self.assertEqual(ff.classify("—")[0], "absent")
    with self.assertRaises(ff.FfiError):
      ff.classify("Probably fine")


if __name__ == "__main__":
  unittest.main()
