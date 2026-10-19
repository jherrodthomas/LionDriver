#!/usr/bin/env python3
"""Tests for hazlog_cards.py: one card per WP-C-03 hazard, IDs and counts read from the documents."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hara_figures as hf
import hazlog_cards as hl


class TestHazlogCards(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.D = hl.load()
    cls.md = hl.C03.read_text(encoding="utf-8")
    cls.svg = hl.build(hf)[hl.NAME]
    cls.cards = {h: hl.card_data(h, cls.D) for h in cls.D["c03"]["hz"]}

  def test_committed_output_current(self):
    self.assertEqual((hf.OUT_DIR / hl.NAME).read_text(encoding="utf-8"), self.svg)
    self.assertIn(hl.NAME, hf.build())

  def test_one_card_per_hazard(self):
    hs = sorted(self.D["c03"]["hz"])
    self.assertEqual(hs, [f"H-0{i}" for i in range(1, 10)])
    self.assertEqual(sorted(hl.SCENES), hs)
    for h in hs:
      self.assertIn(f">{h}</text>", self.svg)

  def test_cards_follow_the_documents(self):
    c = self.cards
    self.assertEqual(c["H-06"]["sgs"], ["SG-06"])
    self.assertEqual(c["H-07"]["sgs"], ["SG-02", "SG-06"])
    self.assertEqual(c["H-02"]["sgs"], ["SG-01", "SG-02"])      # HE-02.3 is a source HE of SG-01
    self.assertEqual((c["H-08"]["rep"]["id"], c["H-08"]["rep"]["asil"]), ("HE-08.1", "B"))
    self.assertEqual(c["H-06"]["rep"]["id"], "HE-06.1")
    lanes = {h: {k: (txt, linked) for k, txt, linked in v["lanes"]} for h, v in c.items()}
    self.assertTrue(lanes["H-06"]["fault"][0].startswith("4 SC pairs: F-02 M01"))
    self.assertTrue(lanes["H-06"]["sotif"][0].startswith("SH-06 "))
    self.assertIn("DS-06", lanes["H-06"]["attack"][0])
    self.assertFalse(lanes["H-07"]["sotif"][1])                # §7 names no SOTIF hazard for H-07
    self.assertFalse(lanes["H-09"]["attack"][1])               # no WP-C-09 damage scenario names H-09
    self.assertNotIn("misuse", lanes["H-08"])
    for v in c.values():
      self.assertEqual(sum(v["counts"]), v["fsr_n"])

  def test_he_ranges(self):
    self.assertEqual(hl.he_ids("HE-06.1, HE-06.3–06.4"), ["HE-06.1", "HE-06.3", "HE-06.4"])
    self.assertEqual(hl.he_ids("HE-01.1–01.5, HE-02.3"), ["HE-01.1", "HE-01.2", "HE-01.3", "HE-01.4", "HE-01.5", "HE-02.3"])

  def test_hazard_lists_must_agree(self):
    md = self.md.replace("| H-09 | SH-12", "| H-10 | SH-12")
    with self.assertRaisesRegex(hf.FigureError, "differ"):
      hl.load_c03(md)

  def test_rated_event_needs_a_goal(self):
    md = self.md.replace("| **B** | HE-08.1 |", "| **B** | — |")
    with self.assertRaisesRegex(hf.FigureError, "HE-08.1 .* is in no safety goal"):
      hl.load_c03(md)

  def test_missing_scene_fails(self):
    scenes = dict(hl.SCENES)
    del scenes["H-05"]
    old, hl.SCENES = hl.SCENES, scenes
    try:
      with self.assertRaisesRegex(hf.FigureError, "no scene for H-05"):
        hl.sheet(self.D)
    finally:
      hl.SCENES = old

  def test_referenced_in_wp_c_03(self):
    self.assertIn(f"(hara/figures/{hl.NAME})", self.md)

  def test_scenes_loop_and_deterministic(self):
    self.assertEqual(self.svg.count('repeatCount="indefinite"'), self.svg.count("<animate"))
    self.assertEqual(self.svg.count("<clipPath"), 9)
    self.assertEqual(hl.build(hf)[hl.NAME], self.svg)


if __name__ == "__main__":
  unittest.main()
