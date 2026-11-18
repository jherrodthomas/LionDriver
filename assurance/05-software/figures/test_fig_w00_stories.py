#!/usr/bin/env python3
"""Tests for fig_w00_stories.py: committed outputs current, the chain of SWSR-407 read from the records, the timing
constants agree with each other, and a broken link of the chain fails."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_w00_stories as fg


class TestFigure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.c = fg.chain()
    cls.k = fg.constants(cls.c)

  def test_committed_output_current(self):
    for name, content in fg.build().items():
      self.assertEqual((fg.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_chain_from_the_records(self):
    self.assertEqual(self.c["tsr"][0], "TSR-407")
    self.assertEqual(self.c["fsr"][0], "FSR-01.07")
    self.assertEqual(self.c["transition"]["id"], "T10a")
    self.assertEqual({u["id"] for u in self.c["units"]}, {"UN-42", "UN-N1"})
    self.assertEqual([t["id"] for t in self.c["tests"]], ["VS-UV-14", "VS-SWI-05", "VS-SWQ-10"])
    svg = (fg.HERE / fg.OUT_R).read_text(encoding="utf-8")
    for t in self.c["tests"]:
      self.assertIn(f">{t['id']}<", svg)
    self.assertIn('<g class="terms">', svg)

  def test_timing_constants_agree(self):
    k = self.k
    self.assertEqual(k["ticks"] / k["f"], k["t_th"])
    self.assertLessEqual(k["t_th"], k["detect"])

  def test_unknown_requirement_fails(self):
    saved = fg.REQ
    try:
      fg.REQ = "SWSR-999"
      with self.assertRaises(fg.FigureError):
        fg.chain()
    finally:
      fg.REQ = saved


if __name__ == "__main__":
  unittest.main()
