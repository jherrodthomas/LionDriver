#!/usr/bin/env python3
"""Tests for fig_s03_functional_flow.py: committed SVG current, and the checks against WP-S-03 §8–§9, WP-C-01 §2.1 and
WP-C-11 §5 catch a change."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s03_functional_flow as ff


class TestFunctionalFlow(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.s03 = ff.SOURCE.read_text(encoding="utf-8")
    cls.item = ff.ITEM.read_text(encoding="utf-8")
    cls.ai = ff.AI.read_text(encoding="utf-8")

  def test_committed_output_current(self):
    for name, content in ff.build().items():
      self.assertEqual((ff.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s03_functional_flow.py")

  def test_every_process_and_service_drawn(self):
    svg = (ff.HERE / ff.OUT).read_text(encoding="utf-8")
    for name, *_ in ff.PROCESSES:
      self.assertIn(f">{name}<", svg)
    for name, *_ in ff.SERVICES:
      self.assertIn(f">{name}<", svg)

  def test_service_rerouted_fails(self):
    md = self.s03.replace("| `longitudinalPlan` | 20 | plannerd → controlsd |", "| `longitudinalPlan` | 20 | plannerd → card |")
    self.assertNotEqual(md, self.s03)
    with self.assertRaises(ff.FlowError):
      ff.check(md, self.item, self.ai)

  def test_process_removed_fails(self):
    md = self.s03.replace("| `radard` |", "| `radard_old` |")
    self.assertNotEqual(md, self.s03)
    with self.assertRaises(ff.FlowError):
      ff.check(md, self.item, self.ai)

  def test_new_error_type_fails(self):
    ai = self.ai.replace("| AE-D |", "| AE-X | x | x | x | x |\n| AE-D |", 1)
    with self.assertRaises(ff.FlowError):
      ff.check(self.s03, self.item, ai)


if __name__ == "__main__":
  unittest.main()
