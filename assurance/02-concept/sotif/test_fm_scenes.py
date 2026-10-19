#!/usr/bin/env python3
"""Tests for fm_scenes.py: one card per WP-C-07 modification, chips and texts from the documents, quotes still current."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fm_scenes as fs
import sotif_figures as sf


class TestFmScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.docs = fs.load()
    cls.cards = fs.cards(cls.docs)
    cls.out = fs.build(cls.docs)

  def test_committed_output_current(self):
    for name, svg in self.out.items():
      self.assertEqual((sf.OUT_DIR / name).read_text(encoding="utf-8"), svg, name)

  def test_written_through_sotif_figures(self):
    self.assertLessEqual(set(self.out), set(sf.build()))

  def test_one_card_per_modification_in_section_2_order(self):
    self.assertEqual([c["fm"] for c in self.cards], list(self.docs["summary"]))
    self.assertEqual(len(self.cards), 11)
    p1, rest = self.out["fig-c07-3-1-fm-scenes-p1.svg"], self.out["fig-c07-3-2-fm-scenes-p2-p3.svg"]
    for c in self.cards:
      self.assertIn(f">{c['fm']}</text>", p1 if c["prio"] == "P1" else rest)
      self.assertNotIn(f">{c['fm']}</text>", rest if c["prio"] == "P1" else p1)

  def test_chips_and_cells_follow_wp_c_07(self):
    for c in self.cards:
      s, tb = self.docs["summary"][c["fm"]], self.docs["table"][c["fm"]]
      self.assertEqual((c["prio"], c["gap"], c["shs"]), (s["prio"], s["gap"], s["sh"]))
      self.assertIn(c["sh"], s["sh"])
      self.assertEqual(c["change"], fs._plain(tb["Change"]))
      self.assertEqual(c["expected"], fs._plain(tb["Expected risk reduction"]))
    by = {c["fm"]: c for c in self.cards}
    self.assertEqual((by["FM-03"]["prio"], by["FM-03"]["gap"]), ("P1", ["GAP-16"]))
    self.assertEqual((by["FM-08"]["prio"], by["FM-08"]["gap"]), ("P3", []))

  def test_plain_drops_markdown(self):
    self.assertEqual(fs._plain("from [WP-C-04 §4.2](a.md#x) and *input-loss* `x`"), "from WP-C-04 §4.2 and input-loss x")

  def test_changed_quote_fails(self):
    docs = copy.deepcopy(self.docs)
    docs["text"]["WP-C-04"] = docs["text"]["WP-C-04"].replace("actuates on stale inputs up to ≈3.5 s", "stops at once")
    with self.assertRaisesRegex(sf.FigureError, "FM-03: WP-C-04 no longer says"):
      fs.cards(docs)
    docs = copy.deepcopy(self.docs)
    docs["table"]["FM-11"]["Rationale"] = "FI-12"
    with self.assertRaisesRegex(sf.FigureError, "FM-11: FM-11.Rationale no longer says"):
      fs.cards(docs)

  def test_missing_or_extra_card_fails(self):
    models = dict(fs.MODELS)
    del models["FM-05"]
    with self.assertRaisesRegex(sf.FigureError, "no card model for FM-05"):
      fs.cards(self.docs, models)
    models = dict(fs.MODELS, **{"FM-99": fs.MODELS["FM-01"]})
    with self.assertRaisesRegex(sf.FigureError, "FM-99"):
      fs.cards(self.docs, models)

  def test_card_hazard_must_be_addressed(self):
    models = dict(fs.MODELS)
    models["FM-11"] = dict(models["FM-11"], sh="SH-01")
    with self.assertRaisesRegex(sf.FigureError, "FM-11: WP-C-07 §2 says it addresses"):
      fs.cards(self.docs, models)

  def test_priority_must_agree(self):
    md = fs.C07.read_text(encoding="utf-8").replace("| FM-11 | Restrict auto-resume from standstill | SH-03, SH-11 | — | P2 |",
                                                    "| FM-11 | Restrict auto-resume from standstill | SH-03, SH-11 | — | P1 |")
    with self.assertRaisesRegex(sf.FigureError, "FM-11 priority is P1 in §2 but P2 in §3"):
      fs.load(md)

  def test_referenced_in_wp_c_07(self):
    md = fs.C07.read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"(figures/{name})", md)

  def test_scenes_loop(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
      self.assertEqual(svg.count("<clipPath"), 2 * svg.count("WITH FM-"))

  def test_deterministic(self):
    self.assertEqual(fs.build(self.docs), self.out)


if __name__ == "__main__":
  unittest.main()
