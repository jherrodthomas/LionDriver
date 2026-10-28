#!/usr/bin/env python3
"""Tests for guideword_scenes.py: one card per SC guide word, goals from WP-C-03, behaviour models complete."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guideword_scenes as gs
import hara_figures as hf
import hara_model as hm


class TestGuidewordScenes(unittest.TestCase):
  def test_phone_sheets_fit_a_phone_and_carry_every_card(self):
    import xml.etree.ElementTree as ET
    out = gs.build()
    for fid in gs.SHEETS:
      full = gs.SHEETS[fid][0]
      phone = full.replace(".svg", "-phone.svg")
      self.assertEqual(ET.fromstring(out[phone]).get("width"), "640", phone)
      for c in gs.cards(fid):
        self.assertIn(f">{c['gw']}<", out[phone], f"{phone}: {c['gw']}")

  def test_one_card_per_sc_guide_word(self):
    for fid in gs.SHEETS:
      sc = sorted(g for g, row in hm.FM[fid].items() if row[0] == hm.SC)
      self.assertEqual([c["gw"] for c in gs.cards(fid)], sc)

  def test_cards_follow_model_and_goal_table(self):
    _, _, goals = hf.parse_hara(hf.SOURCE.read_text(encoding="utf-8"))
    asil = {g.ident: g.asil for g in goals}
    for c in gs.cards("F-01"):
      _, hz, sub_by, why = hm.FM["F-01"][c["gw"]]
      self.assertEqual((c["hz"], c["sub_by"], c["why"]), (hz, sub_by, why))
      self.assertEqual(c["sg"], hm.SG_MAP[hz])
      self.assertEqual(c["asil"], asil[c["sg"]])

  def test_sheet_lists_every_guide_word(self):
    name, svg = gs.sheet("F-01")
    self.assertEqual(name, "fig-c03-4-1-f01-guide-words.svg")
    for gw, label in hm.MALFUNCTIONS:
      self.assertIn(f">{gw}</text>", svg)
      self.assertIn(f">{label}</text>", svg)
    self.assertEqual(svg, gs.sheet("F-01")[1])

  def test_scenes_loop_and_still_frame_is_the_end(self):
    _, svg = gs.sheet("F-01")
    self.assertEqual(svg.count('<clipPath id="rM'), 14)                   # one band reveal per card
    self.assertEqual(svg.count('type="translate"'), 28)                  # red car and intended ghost per card
    self.assertNotIn('repeatCount="1"', svg)
    self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
    c = gs.cards("F-01")[0]
    car = c["scene"][-3] if c["scene"][-1].startswith("<g><animate") else c["scene"][-2]
    x, y = gs._pts(gs.F01["M01"][3])[-1]
    self.assertIn(f'translate({x:.1f} {y:.1f})', car)                     # static pose = end of the path

  def test_every_function_with_sc_pairs_has_a_sheet(self):
    for fid, rows in hm.FM.items():
      has_sc = any(r[0] == hm.SC for r in rows.values())
      self.assertEqual(fid in gs.SHEETS, has_sc, fid)
      if not has_sc:
        self.assertIn(fid, gs.NO_SHEET)

  def test_every_card_says_what_matters(self):
    for fid in gs.SHEETS:
      for c in gs.cards(fid):
        self.assertTrue(c["label"], f"{fid}/{c['gw']} has no callout")

  def test_longitudinal_consequences(self):
    got = {(f, c["gw"]): c["label"] for f in ("F-02", "F-02X", "F-03", "F-08") for c in gs.cards(f)}
    self.assertEqual(got[("F-02", "M01")], "closes on the lead")          # no deceleration behind a slowing lead
    self.assertEqual(got[("F-02X", "M01")], "past the stop line on red")  # does not stop for the red light
    self.assertEqual(got[("F-03", "M01")], "runs into the stopped car")   # no disengagement when the driver brakes
    self.assertEqual(got[("F-08", "M03")], "runs into the stopped car")   # stock AEB request blocked

  def test_goal_chip_without_goal_in_scope(self):
    c = gs.cards("F-02X")[0]
    self.assertEqual((c["hz"], c["asil"]), ("H-10", None))                # SG-09 exists only under D-08 option B
    self.assertIn("SG-09", c["sg"])
    mc = {c["gw"]: c for c in gs.cards("F-05")}["M01"]
    self.assertEqual(mc["sg"], "SG-02/SG-06")                             # H-07 is covered by two goals

  def test_missing_model_rejected(self):
    model = dict(gs.F01)
    del model["M05"]
    with mock.patch.dict(gs.SHEETS, {"F-01": (*gs.SHEETS["F-01"][:3], model)}):
      with self.assertRaisesRegex(hf.FigureError, "no model for SC"):
        gs.cards("F-01")

  def test_model_for_non_sc_rejected(self):
    fm = {k: (hm.NSC, *v[1:]) if k == "M06" else v for k, v in hm.FM["F-01"].items()}
    with mock.patch.dict(hm.FM, {"F-01": fm}):
      with self.assertRaisesRegex(hf.FigureError, "non-SC"):
        gs.cards("F-01")

  def test_callouts(self):
    got = {c["gw"]: c["label"] for c in gs.cards("F-01")}
    self.assertEqual(got["M01"], "crosses edge line")      # no torque: runs wide in the curve
    self.assertEqual(got["M03"], "into the next lane")     # unrequested torque toward the inner lane
    self.assertEqual(got["M10"], "past the target lane")


if __name__ == "__main__":
  unittest.main()
