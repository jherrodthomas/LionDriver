#!/usr/bin/env python3
"""Tests for fig_c01_modes.py: sources still say what is drawn, record IDs exist, every row drawn, SVGs current."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_c01_modes as fm

NS = "{http://www.w3.org/2000/svg}"


class TestC01ModeFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fm.SOURCE.read_text(encoding="utf-8")
    cls.recs = fm.records()
    cls.out = fm.build(cls.md, cls.recs)

  def test_no_source_problems(self):
    self.assertEqual(fm.problems(self.md, self.recs), [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fm.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_c01_modes.py")

  def test_build_is_deterministic(self):
    self.assertEqual(fm.build(self.md, self.recs), self.out)

  def test_svgs_valid_with_role_title_desc(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), "1280", name)
      self.assertRegex(root.find(f"{NS}title").text, r"^Figure [47]-[12] · ", name)
      self.assertTrue(root.find(f"{NS}desc").text, name)

  def test_every_record_id_claimed_exists(self):
    ids = fm.drawn_ids(self.recs)
    self.assertGreater(len(ids), 20)
    for machine, tid in ids:
      self.assertIsNotNone(fm.transition(self.recs, machine, tid), f"{machine} {tid}")
    # the IDs the brief names for Figure 4-2 are among them
    for tid in ("T1", "T2", "T3"):
      self.assertIn((fm.TA, tid), ids)
    for tid in ("E1", "E2", "O2", "SD2"):
      self.assertIn((fm.SD, tid), ids)
    # and every ID printed on an arrow label of Figure 4-1 is one the arrow claims
    for a in fm.arrows(self.recs):
      claimed = {t for _m, t in a["ids"]}
      for _x, _y, s, *_ in a["labels"]:
        for tok in re.findall(r"\b(?:T\d+[a-e]?|M\d|SD\d|[XEODPN]\d)\b", s):
          self.assertIn(tok, claimed, f"arrow {a['name']}: label names {tok}")

  def test_every_section4_mode_drawn(self):
    svg = self.out["fig-c01-4-1-operating-modes.svg"]
    rows = fm.modes_table(self.md)
    self.assertEqual(len(rows), 9)
    for r in rows:
      self.assertTrue(r["mode"] in fm.MODES or r["mode"] in fm.CONFIG, r["mode"])
      if r["mode"] in fm.MODES:
        self.assertIn(f">{r['mode']}<", svg)
    # actuation chips follow the Actuation column
    chips = {r["mode"]: fm.chips(r["act"]) for r in rows}
    self.assertEqual(chips["Overriding"], ["lateral", "no longitudinal"])
    self.assertEqual(chips["Soft disabling"], ["lateral", "longitudinal (forced decel)"])
    self.assertEqual(chips["Driver lockout"], ["none"])

  def test_timeline_code_values_and_honesty(self):
    svg = self.out["fig-c01-4-2-engagement-timeline.svg"]
    self.assertEqual(fm.SOFT_S, fm.T_SD2 - fm.T_FAULT)
    self.assertIn(f"softDisabling · {fm.SOFT_S} s", svg)
    self.assertIn("1–30 min", svg)
    self.assertIn("ILLUSTRATIVE EPISODE", svg)
    self.assertIn(fm.E1_ACTION, fm.transition(self.recs, fm.SD, "E1")["action"])
    # T2 clears on CRUISE_ACTIVE = 0 and T6 on the heartbeat: the two ways controls_allowed drops after SD2
    self.assertIn("CRUISE_ACTIVE = 0", fm.transition(self.recs, fm.TA, "T2")["guard"])
    self.assertIn("3 consecutive ticks", fm.transition(self.recs, fm.TA, "T6")["guard"])

  def test_every_aou_placed_once_with_status(self):
    rows = fm.aou_table(self.md)
    self.assertEqual(len(rows), 18)  # AOU-16 for the SG-08 standstill hold (DQ-365 A); AOU-17 EPS/PCM report every drop (DQ-360 A); AOU-18 network scope (DQ-419 A)
    svg = self.out["fig-c01-7-1-aou-map.svg"]
    for r in rows:
      self.assertEqual(svg.count(f">{r['id']}<"), 1, r["id"])
      self.assertIn(fm.AOU_MAP[r["id"]][0], {g for g, _n, _s in fm.AOU_GROUPS})
    self.assertEqual(sorted(fm.AOU_MAP), sorted(r["id"] for r in rows))
    self.assertIn("WP-T-01 Figure 6", svg)

  def test_nothing_drawn_as_verified(self):
    for name, content in self.out.items():
      self.assertNotIn("#2E9E6A", content.upper(), name)


if __name__ == "__main__":
  unittest.main()
