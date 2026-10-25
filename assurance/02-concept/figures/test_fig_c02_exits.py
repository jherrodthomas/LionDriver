#!/usr/bin/env python3
"""Tests for fig_c02_exits.py: every §5.2 exit is read and classified, the SVG is current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c02_exits as fe


class TestExits(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fe.SOURCE.read_text(encoding="utf-8")
    cls.rows = fe.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fe.build().items():
      self.assertEqual((fe.HERE / name).read_text(encoding="utf-8"), content, name)

  def test_rows(self):
    by = {r["exit"].split(" (")[0]: r for r in self.rows}
    self.assertEqual(by["Speed > 110 km/h"]["detected"], "no")
    self.assertEqual(by["Speed > 110 km/h"]["closes"], "FM-07")
    self.assertEqual(by["Device overheat"]["closes"], "implemented")
    self.assertEqual(by["Heavy rain, fog, glare, camera blocked"]["detected"], "no")

  def test_unreadable_detection_rejected(self):
    with self.assertRaises(fe.ExitError):
      fe.parse(self.md.replace("| Snow / ice | No |", "| Snow / ice | Maybe |"))


if __name__ == "__main__":
  unittest.main()
