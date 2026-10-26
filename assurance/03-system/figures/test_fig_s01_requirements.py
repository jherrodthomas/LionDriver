#!/usr/bin/env python3
"""Tests for fig_s01_requirements.py: committed SVG current, every SYS requirement drawn once, flags read as documented."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s01_requirements as fr


class TestRequirements(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fr.SOURCE.read_text(encoding="utf-8")
    cls.cov = fr.COVERAGE.read_text(encoding="utf-8")
    cls.by = {r["id"]: r for _, rs in fr.parse(cls.md, cls.cov) for r in rs}

  def test_committed_output_current(self):
    for name, content in fr.build().items():
      self.assertEqual((fr.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s01_requirements.py")

  def test_every_requirement_once(self):
    ids = sorted(set(re.findall(r"^\| (SYS-\d{3}) \| [A-Z]", self.md, re.M)))
    self.assertEqual(sorted(self.by), ids)
    svg = (fr.HERE / fr.OUT).read_text(encoding="utf-8")
    for i in ids:
      self.assertEqual(svg.count(f">{i}<"), 1, i)

  def test_flags(self):
    self.assertTrue(self.by["SYS-020"]["tbd"])   # TBD in the statement
    self.assertTrue(self.by["SYS-001"]["tbd"])   # TBD in the target
    self.assertFalse(self.by["SYS-002"]["tbd"])
    self.assertFalse(self.by["SYS-005"]["case"])
    self.assertTrue(self.by["SYS-001"]["case"])
    self.assertEqual(self.by["SYS-024"]["types"], ["F", "P"])

  def test_unknown_coverage_entry_fails(self):
    cov = self.cov.replace("SYS-005,", "SYS-999, SYS-005,", 1)
    with self.assertRaises(fr.SysError):
      fr.parse(self.md, cov)


if __name__ == "__main__":
  unittest.main()
