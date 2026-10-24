#!/usr/bin/env python3
"""Tests for fig_c01_allocation.py: every function is mapped, every column is a WP-C-01 element, the SVG is current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c01_allocation as fa


class TestAllocation(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fa.SOURCE.read_text(encoding="utf-8")

  def test_committed_output_current(self):
    for name, content in fa.build().items():
      self.assertEqual((fa.HERE / name).read_text(encoding="utf-8"), content, name)

  def test_functions_match_wp_c01(self):
    funcs, elements = fa.parse(self.md)
    self.assertEqual(list(funcs), [f"F-0{i}" for i in range(1, 10)])
    self.assertTrue({"E-01", "E-03", "E-05"} <= elements)
    self.assertEqual(fa.ALLOCATION["F-08"]["E-03"], fa.R)

  def test_unmapped_function_rejected(self):
    old = fa.ALLOCATION.pop("F-09")
    try:
      with self.assertRaises(fa.AllocationError):
        fa.parse(self.md)
    finally:
      fa.ALLOCATION["F-09"] = old


if __name__ == "__main__":
  unittest.main()
