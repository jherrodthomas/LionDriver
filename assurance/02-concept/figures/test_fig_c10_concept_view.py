#!/usr/bin/env python3
"""Tests for fig_c10_concept_view.py: every concept requirement is placed, statuses read as documented, SVG current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c10_concept_view as fc


class TestConceptView(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.d = fc.parse(fc.SOURCE.read_text(encoding="utf-8"))

  def test_committed_output_current(self):
    for name, content in fc.build().items():
      self.assertEqual((fc.HERE / name).read_text(encoding="utf-8"), content, name)

  def test_every_requirement_placed(self):
    ids = [r["id"] for r in self.d["reqs"]]
    self.assertEqual(ids, [f"CSR-C-{i:02d}" for i in range(1, 17)])
    by = {r["id"]: r for r in self.d["reqs"]}
    self.assertEqual(by["CSR-C-01"]["places"], ["E-03"])
    self.assertIn("USER", by["CSR-C-16"]["places"])

  def test_classify(self):
    self.assertEqual(fc.classify("Not implemented; x **2026-10-12: Implemented in the reference build, not verified**"), "impl")
    self.assertEqual(fc.classify("Partially: onroad streaming blocked"), "partial")
    self.assertEqual(fc.classify("Not met; routes to comma"), "not")
    with self.assertRaises(fc.ConceptError):
      fc.classify("Unclear")


if __name__ == "__main__":
  unittest.main()
