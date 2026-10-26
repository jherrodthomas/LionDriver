#!/usr/bin/env python3
"""Tests for fig_s09_cases.py: committed SVG current, every §5 case drawn once, coverage and flags read as documented."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s09_cases as fc


class TestCases(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fc.SOURCE.read_text(encoding="utf-8")
    cls.by = {c["id"]: c for *_, cs in fc.parse(cls.md) for c in cs}

  def test_committed_output_current(self):
    for name, content in fc.build().items():
      self.assertEqual((fc.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s09_cases.py")

  def test_every_case_once(self):
    sec = re.search(r"^## 5\. .*?$(.*?)(?=^## 6\. )", self.md, re.M | re.S).group(1)
    self.assertEqual(list(self.by), re.findall(r"^\| (VS-SQ-\d\d) \|", sec, re.M))
    svg = (fc.HERE / fc.OUT).read_text(encoding="utf-8")
    for i in self.by:
      self.assertEqual(svg.count(f">{i}<"), 1, i)

  def test_covers(self):
    self.assertEqual(fc.covers("All SG; TSR-1xx…TSR-7xx (observation); SYS-001"),
                     {"SYS"} | {f"TSR-{d}" for d in range(1, 8)})
    self.assertEqual(fc.covers("AOU-01R, FSR-01.13; TSR-111"), {"AOU", "TSR-1"})
    self.assertEqual(fc.covers("TSR-407, TSR-408, TSR-510"), {"TSR-4", "TSR-5"})

  def test_flags(self):
    self.assertTrue(self.by["VS-SQ-01"]["early"])
    self.assertTrue(self.by["VS-SQ-12"]["build"] and self.by["VS-SQ-12"]["fail"])
    self.assertFalse(self.by["VS-SQ-08"]["fail"])


if __name__ == "__main__":
  unittest.main()
