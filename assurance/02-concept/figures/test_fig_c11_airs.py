#!/usr/bin/env python3
"""Tests for fig_c11_airs.py: every AIR is drawn once in its §6 group, statuses read as documented, SVG current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c11_airs as fa


class TestAirs(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.groups = fa.parse(fa.SOURCE.read_text(encoding="utf-8"))

  def test_committed_output_current(self):
    for name, content in fa.build().items():
      self.assertEqual((fa.HERE / name).read_text(encoding="utf-8"), content, name)

  def test_every_air_once(self):
    ids = [r["id"] for _, rs in self.groups for r in rs]
    self.assertEqual(ids, [f"AIR-{i:02d}" for i in range(1, 31)])
    self.assertEqual(len(self.groups), 7)

  def test_classify(self):
    self.assertEqual(fa.classify("Not evaluated. No data"), "eval")
    self.assertEqual(fa.classify("**Not met**: x"), "not")
    self.assertEqual(fa.classify("**Partially**: y"), "partial")
    with self.assertRaises(fa.AirError):
      fa.classify("Met")


if __name__ == "__main__":
  unittest.main()
