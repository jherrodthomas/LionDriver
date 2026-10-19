#!/usr/bin/env python3
"""Tests for fig_c10_goals.py: one card per WP-C-10 goal, requirements and risks checked, barrier drawn as built."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c10_goals as fg


class TestGoalCards(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.G = fg.load()
    cls.out = fg.build(cls.G)
    cls.svg = cls.out[fg.NAME]

  def test_one_card_per_goal(self):
    self.assertEqual(re.findall(r"<title>(CSG-\d+): ", self.svg), sorted(self.G.csg))
    self.assertEqual(len(self.G.csg), 8)
    self.assertIn("Figure 7-1.", self.svg)

  def test_every_requirement_with_a_goal_is_on_its_cards(self):
    for g in self.G.csg:
      self.assertEqual(sorted(fg.MODEL[g][3]), sorted(self.G.under(g)), g)
    self.assertEqual(self.G.csr["CSR-C-16"]["parents"], [])
    self.assertIn("CSR-C-16 supports every goal", self.svg)

  def test_status_is_the_latest_dated_one(self):
    self.assertEqual(fg.csr_status("Not implemented; x (GAP-09). **2026-10-12: Implemented in the reference build, not verified**"),
                     "unverified")
    self.assertEqual(fg.csr_status("Not implemented; y. **2026-10-12: Partial in the reference build, not verified**: z"), "partial")
    self.assertEqual(fg.csr_status("Not met; z"), "open")
    self.assertEqual(fg.csr_status("Not confirmed; w"), "unconfirmed")
    with self.assertRaises(fg.ParseError):
      fg.csr_status("Something else")

  def test_barrier_follows_the_statuses(self):
    self.assertEqual(fg.barrier(["open", "unconfirmed"]), "open")
    self.assertEqual(fg.barrier(["unverified", "partial"]), "partial")
    self.assertEqual(fg.barrier(["unverified", "done"]), "unverified")
    self.assertEqual(fg.barrier(["done"]), "done")

  def test_status_change_without_a_redraw_fails(self):
    G = fg.load()
    G.csr["CSR-C-08"] = dict(G.csr["CSR-C-08"], status="unverified")
    with self.assertRaisesRegex(fg.ParseError, "CSG-04: .*redraw the card"):
      fg.build(G)

  def test_risk_must_match_wp_c09(self):
    doc = fg.GOALS.read_text(encoding="utf-8").replace("TS-02 (5)", "TS-02 (4)")
    with self.assertRaisesRegex(fg.ParseError, "TS-02 risk 4"):
      fg.Goals(doc, fg.fc.load())

  def test_quote_no_longer_in_the_requirement_fails(self):
    model = dict(fg.MODEL)
    title, scene, cap, para = model["CSG-05"]
    model["CSG-05"] = (title, scene, cap, {"CSR-C-09": ("x", "a phrase WP-C-10 never says")})
    with self.assertRaisesRegex(fg.ParseError, "no longer in CSR-C-09"):
      fg.cards(self.G, model)

  def test_missing_or_extra_card_fails(self):
    with self.assertRaisesRegex(fg.ParseError, "no card for CSG-03"):
      fg.cards(self.G, {k: v for k, v in fg.MODEL.items() if k != "CSG-03"})
    with self.assertRaisesRegex(fg.ParseError, "CSG-99"):
      fg.cards(self.G, dict(fg.MODEL, **{"CSG-99": fg.MODEL["CSG-01"]}))

  def test_committed_figure_current_and_referenced(self):
    self.assertEqual((fg.HERE / fg.NAME).read_text(encoding="utf-8"), self.svg)
    self.assertIn(f"figures/{fg.NAME}", fg.GOALS.read_text(encoding="utf-8"))

  def test_scenes_loop_and_output_is_deterministic(self):
    self.assertEqual(self.svg.count('repeatCount="indefinite"'), self.svg.count("<animate"))
    self.assertEqual(self.out, fg.build(self.G))

  def test_no_procedural_detail(self):
    self.assertNotRegex(self.svg, r"0x[0-9a-fA-F]{2}")


if __name__ == "__main__":
  unittest.main()
