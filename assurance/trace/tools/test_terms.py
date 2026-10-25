#!/usr/bin/env python3
"""Tests for terms.py: terms are found the way readers see them, unknown ones are flagged, outputs are current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import terms as T


class TestTerms(unittest.TestCase):
  def test_codes_words_and_classes(self):
    found, unknown = T.find("FSR-01.05 serves SG-01 at ASIL C on the SoC; HE-02.1 is S3 E4 C2; SS-L; EXT-EPS; WP-C-04")
    for k in ("FSR-", "SG-", "ASIL", "SoC", "HE-", "S#", "E#", "C#", "SS-", "EXT-", "WP-"):
      self.assertIn(k, found)
    self.assertEqual(unknown, [])

  def test_plural_and_bare_prefix(self):
    found, _ = T.find("the FSRs and TSRs of the TSC")
    self.assertIn("FSR-", found)
    self.assertIn("TSR-", found)
    self.assertIn("TSC", found)

  def test_unknown_flagged(self):
    _, unknown = T.find("the XYZW module")
    self.assertEqual(unknown, ["XYZW"])

  def test_code_spans_and_links_ignored(self):
    _, unknown = T.find(T.plain_markdown("see `QQQ_FLAG` and [a page](ZZZ/README.md)"))
    self.assertEqual(unknown, [])

  def test_every_term_has_a_meaning(self):
    for k, v in T.TERMS.items():
      self.assertTrue(v.strip(), k)

  def test_outputs_current(self):
    self.assertEqual(T.main(["--check"]), 0)


if __name__ == "__main__":
  unittest.main()
