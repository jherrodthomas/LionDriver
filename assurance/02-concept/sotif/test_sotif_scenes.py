#!/usr/bin/env python3
"""Tests for sotif_scenes.py: one card per SOTIF hazard, card texts from WP-C-05/06, scene models complete and looping."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sotif_figures as sf
import sotif_scenes as ss


class TestSotifScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.docs = ss.load()
    cls.cards = ss.cards(cls.docs)
    cls.svg = ss.sheet(cls.docs)

  def test_committed_output_current(self):
    self.assertEqual((sf.OUT_DIR / ss.NAME).read_text(encoding="utf-8"), ss.build()[ss.NAME])

  def test_one_card_per_hazard(self):
    self.assertEqual([c["sh"] for c in self.cards], sorted(self.docs.data.sh))
    self.assertNotIn("SH-07", [c["sh"] for c in self.cards])
    for c in self.cards:
      self.assertIn(f">{c['sh']}</text>", self.svg)

  def test_cards_follow_the_documents(self):
    for c in self.cards:
      self.assertEqual(c["hazard"], self.docs.data.sh[c["sh"]][0])
      if c["row"] is None:
        self.assertFalse([f for f, v in self.docs.data.fi.items() if c["sh"] in v[3]])
        continue
      self.assertIn(c["tc"], c["row"]["tc"])
      self.assertIn(c["fi"], c["row"]["fi"])
      self.assertIn(c["sh"], c["row"]["sh"])
      self.assertIn(c["sh"], self.docs.data.fi[c["fi"]][3])
      self.assertEqual(c["cls"], self.docs.data.fi[c["fi"]][0])
      self.assertNotIn(c["tc"], c["also"])
    by = {c["sh"]: c for c in self.cards}
    self.assertEqual((by["SH-01"]["cls"], by["SH-02"]["cls"]), ("P", "S"))
    self.assertEqual(by["SH-02"]["row"]["out"], "mod")
    self.assertEqual(by["SH-04"]["hchip"], "SH-04 · H-04 · S2 C2")
    self.assertEqual(by["SH-12"]["hchip"], "SH-12 · enabling")
    self.assertEqual(by["SH-14"]["hchip"], "SH-14 · new · S3 C2")   # accepted by the lead (DQ-429 A)
    self.assertEqual((by["SH-08"]["tc"], by["SH-08"]["fi"], by["SH-08"]["cls"]), ("TC-34", "FI-23", "S"))

  def test_missing_model_rejected(self):
    models = dict(ss.MODELS)
    del models["SH-05"]
    with self.assertRaisesRegex(sf.FigureError, "no card model for SH-05"):
      ss.cards(self.docs, models)

  def test_fi_not_linked_rejected(self):
    models = dict(ss.MODELS)
    models["SH-01"] = ("x", "TC-05", "FI-10", ss.sh01)        # FI-10 links SH-06 only
    with self.assertRaisesRegex(sf.FigureError, "does not link"):
      ss.cards(self.docs, models)

  def test_row_must_exist(self):
    models = dict(ss.MODELS)
    models["SH-01"] = ("x", "TC-14", "FI-01", ss.sh01)        # FI-01 links SH-01, but TC-14's row names FI-09/FI-11
    with self.assertRaisesRegex(sf.FigureError, "no row"):
      ss.cards(self.docs, models)

  def test_card_without_row_rejected_once_an_fi_links_it(self):
    models = dict(ss.MODELS)
    models["SH-08"] = ("x", None, None, ss.sh08)              # FI-23 links SH-08, so the card needs its row
    with self.assertRaisesRegex(sf.FigureError, "SH-08"):
      ss.cards(self.docs, models)

  def test_scenes_loop_and_still_frame_is_the_end(self):
    self.assertEqual(self.svg.count('repeatCount="indefinite"'), self.svg.count("<animate"))
    self.assertEqual(self.svg.count("<clipPath"), len(self.cards))
    path = ss.sh01()[1]
    ego = [s for s in path if s.startswith('<g transform="translate(') and "animateTransform" in s][-1]
    self.assertIn('translate(262.0 ', ego)                    # static pose = end of the drive


if __name__ == "__main__":
  unittest.main()
