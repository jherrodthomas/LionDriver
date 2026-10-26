#!/usr/bin/env python3
"""Tests for fig_s08_cases.py: committed SVG current, every §6 case drawn once with its steps, a changed cell fails."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s08_cases as fc


class TestCases(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fc.SOURCE.read_text(encoding="utf-8")
    cls.groups = fc.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fc.build().items():
      self.assertEqual((fc.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s08_cases.py")

  def test_every_case_once(self):
    ids = [c["id"] for _, cs in self.groups for c in cs]
    sec = re.search(r"^## 6\. .*?$(.*?)(?=^## 7\. )", self.md, re.M | re.S).group(1)
    self.assertEqual(ids, re.findall(r"^\| (VS-SI-\d\d) \|", sec, re.M))
    svg = (fc.HERE / fc.OUT).read_text(encoding="utf-8")
    for i in ids:
      self.assertEqual(svg.count(f">{i}<"), 1, i)

  def test_steps_read(self):
    by = {c["id"]: c for _, cs in self.groups for c in cs}
    self.assertEqual(by["VS-SI-01"]["steps"], ["I-1", "I-2", "I-4"])
    self.assertEqual(by["VS-SI-09"]["steps"], ["I-2"])

  def test_changed_cell_fails(self):
    md = self.md.replace("**Fail (known GAP-02)**", "Meets", 1)
    self.assertNotEqual(md, self.md)
    with self.assertRaises(fc.CaseError):
      fc.parse(md)


if __name__ == "__main__":
  unittest.main()
