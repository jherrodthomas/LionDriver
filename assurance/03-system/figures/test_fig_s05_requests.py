#!/usr/bin/env python3
"""Tests for fig_s05_requests.py: committed SVG current, every §4.2 request drawn once, treatments read as documented."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s05_requests as fr


class TestRequests(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fr.SOURCE.read_text(encoding="utf-8")
    cls.rows = fr.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fr.build().items():
      self.assertEqual((fr.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s05_requests.py")

  def test_every_request_once(self):
    sec = re.search(r"^### 4\.2 .*?$(.*?)(?=^### )", self.md, re.M | re.S).group(1)
    self.assertEqual(len(self.rows), len(re.findall(r"^\| \*{0,2}`0x", sec, re.M)))
    svg = (fr.HERE / fr.OUT).read_text(encoding="utf-8")
    for r in self.rows:
      self.assertIn(r["req"].split(",")[0].split(" ")[0], svg)

  def test_open_requests(self):
    by = {r["req"]: r for r in self.rows}
    self.assertTrue(by["0xc5"]["open"])
    self.assertTrue(by["0xd1"]["open"])  # the softloader parameter is ungated
    self.assertTrue(by["0xdc"]["open"])
    self.assertFalse(by["0xde"]["open"])  # speed whitelist
    self.assertFalse(by["0xa8"]["open"])  # allowed

  def test_treatment(self):
    self.assertEqual(fr.treatment("**reject**"), "refused")
    self.assertEqual(fr.treatment("absent"), "refused")
    self.assertEqual(fr.treatment("only reference modes"), "limited")
    self.assertEqual(fr.treatment("allow (logged)"), "allowed")
    self.assertEqual(fr.treatment("—"), "na")
    with self.assertRaises(fr.RequestError):
      fr.treatment("maybe")


if __name__ == "__main__":
  unittest.main()
