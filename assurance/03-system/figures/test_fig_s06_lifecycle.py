#!/usr/bin/env python3
"""Tests for fig_s06_lifecycle.py: committed SVG current, every TSR-8nn drawn once, statuses tied to their cells."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s06_lifecycle as fl


class TestLifecycle(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fl.SOURCE.read_text(encoding="utf-8")
    cls.phases, cls.design = fl.parse(cls.md)
    cls.by = {r["id"]: r for _, rs in cls.phases for r in rs}

  def test_committed_output_current(self):
    for name, content in fl.build().items():
      self.assertEqual((fl.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s06_lifecycle.py")

  def test_every_requirement_once(self):
    ids = sorted(set(re.findall(r"^\| (TSR-8\d\d) \| [A-Z]", self.md, re.M)))
    self.assertEqual(sorted(self.by), ids)
    svg = (fl.HERE / fl.OUT).read_text(encoding="utf-8")
    for i in ids:
      self.assertEqual(svg.count(f">{i}<"), 1, i)

  def test_phases_and_statuses(self):
    self.assertEqual(len(self.phases), 5)
    self.assertEqual(self.by["TSR-802"]["status"], "blocked")
    self.assertEqual(self.by["TSR-806"]["status"], "design")
    self.assertEqual({d["tsr"]: d["kind"] for d in self.design}["TSR-512"], "implemented")

  def test_a_changed_status_cell_fails(self):
    md = self.md.replace("Blocked in substance by GAP-24/25", "Met")
    with self.assertRaises(fl.LifecycleError):
      fl.parse(md)

  def test_a_new_requirement_needs_a_status(self):
    md = self.md.replace("| TSR-818 |", "| TSR-819 | x | QM | - | - | - | Defined |\n| TSR-818 |", 1)
    with self.assertRaises(fl.LifecycleError):
      fl.parse(md)


if __name__ == "__main__":
  unittest.main()
