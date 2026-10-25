#!/usr/bin/env python3
"""Tests for fig_s03_mechanisms.py: committed SVG current, every §6 mechanism drawn once, statuses read as documented."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s03_mechanisms as fm


class TestMechanisms(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fm.SOURCE.read_text(encoding="utf-8")
    cls.sms, cls.integrity = fm.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fm.build().items():
      self.assertEqual((fm.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s03_mechanisms.py")

  def test_every_mechanism_once(self):
    ids = [s["id"] for s in self.sms]
    self.assertEqual(ids, re.findall(r"^\| (SM-\d\d) \|", self.md, re.M))
    svg = (fm.HERE / fm.OUT).read_text(encoding="utf-8")
    for i in ids:
      self.assertIn(f">{i}<", svg)

  def test_classify(self):
    self.assertEqual(fm.classify("Impl"), "impl")
    self.assertEqual(fm.classify("Impl/Partial"), "partial")
    self.assertEqual(fm.classify("New at baseline; **Impl, not verified** 2026-10-12 (IWDG1)"), "impl")
    self.assertEqual(fm.classify("**Not met** (GAP-42) at baseline; **Met (reference build)** 2026-10-12"), "impl")
    self.assertEqual(fm.classify("Impl (704) / Not verified (707) / Not impl (711)"), "partial")
    self.assertEqual(fm.classify("New"), "not")
    self.assertEqual(fm.classify("Unknown"), "unknown")
    with self.assertRaises(fm.MechanismError):
      fm.classify("Maybe")

  def test_elements(self):
    self.assertEqual(fm.elements("E-03a/b"), ["E-03a", "E-03b"])
    self.assertEqual(fm.elements("E-01 (HMI)"), ["E-01"])
    self.assertEqual(fm.elements("E-04a/E-05"), ["E-04a", "E-05"])

  def test_envelope_is_asil_c(self):
    for e in ("E-03a", "E-03b", "E-04a"):
      self.assertEqual(self.integrity[e], "C")


if __name__ == "__main__":
  unittest.main()
