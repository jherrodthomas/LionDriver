#!/usr/bin/env python3
"""Tests for fig_s07_csr_status.py: committed SVG current, every §4 requirement sorted once, a changed cell fails."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s07_csr_status as fc


class TestCsrStatus(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fc.SOURCE.read_text(encoding="utf-8")
    cls.groups = fc.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fc.build().items():
      self.assertEqual((fc.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s07_csr_status.py")

  def test_every_requirement_once(self):
    ids = [r["id"] for g in self.groups for r in g["reqs"]]
    self.assertEqual(len(ids), 64)
    self.assertEqual(len(self.groups), 16)
    svg = (fc.HERE / fc.OUT).read_text(encoding="utf-8")
    for i in ids:
      self.assertEqual(svg.count(f">{i}<"), 1, i)

  def test_matches_summary_counts(self):
    # §5 gives the count per parent; the figure must agree with it.
    sec = re.search(r"^## 5\. .*?$(.*?)(?=^## 6\. )", self.md, re.M | re.S).group(1)
    for g in self.groups:
      m = re.search(rf"^\| {g['parent']} \|.*\| (\d+) \|$", sec, re.M)
      self.assertEqual(int(m.group(1)), len(g["reqs"]), g["parent"])

  def test_changed_cell_fails(self):
    md = self.md.replace("Not met: the baseline scheme is weaker than required", "Implemented: ECDSA P-256", 1)
    self.assertNotEqual(md, self.md)
    with self.assertRaises(fc.CsrError):
      fc.parse(md)


if __name__ == "__main__":
  unittest.main()
