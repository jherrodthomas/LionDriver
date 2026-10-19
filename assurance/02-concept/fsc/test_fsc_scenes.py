#!/usr/bin/env python3
"""Tests for fsc_scenes.py: one card per WP-C-04 safety goal, §8 budgets and §5 status read from the document, IDs checked."""

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fsc_figures as ff
import fsc_scenes as fs


class TestFttiScenes(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = ff.SOURCE.read_text(encoding="utf-8")
    cls.goals = ff.parse(cls.md)
    cls.out = fs.build(cls.goals, cls.md, ff)

  def test_one_card_per_goal(self):
    cards = []
    for name, (num, _, _, ids) in fs.SHEETS.items():
      found = re.findall(r"<title>(SG-\d+): ", self.out[name])
      self.assertEqual(found, ids, name)
      self.assertIn(f"Figure {num}.", self.out[name])
      cards += found
    self.assertEqual(sorted(cards), [g.ident for g in self.goals])

  def test_budgets_and_status_parsed(self):
    rows = fs.budgets(self.md)
    self.assertEqual((rows["SG-07 (forwarding loss)"]["ftti"], rows["SG-07 (forwarding loss)"]["det"]), (0.2, 0.1))
    self.assertIsNone(rows["SG-05 (steering override)"]["det"])
    self.assertEqual(rows["SG-01 (continuous limiting)"]["react"], 0.01)
    st = fs.impl(self.md)
    self.assertEqual(set(st), {f.ident for g in self.goals for f in g.fsrs})
    self.assertEqual(st["FSR-05.01"], "implemented")

  def test_sheets_written_through_fsc_figures_and_referenced(self):
    built = ff.build()
    doc = self.md
    for name, content in self.out.items():
      self.assertEqual(built[name], content)
      self.assertEqual((ff.OUT_DIR / name).read_text(encoding="utf-8"), content, f"{name} stale; run fsc_figures.py")
      self.assertIn(f"fsc/figures/{name}", doc, name)

  def test_unknown_id_or_row_fails(self):
    model = copy.deepcopy(fs.MODEL)
    model["SG-07"]["today"] += " (GAP-999)"
    with mock.patch.object(fs, "MODEL", model):
      with self.assertRaisesRegex(ff.FigureError, "GAP-999"):
        fs.build(self.goals, self.md, ff)
    model = copy.deepcopy(fs.MODEL)
    model["SG-07"]["budget"]["row"] = "SG-07 (nonexistent)"
    with mock.patch.object(fs, "MODEL", model):
      with self.assertRaisesRegex(ff.FigureError, "does not have"):
        fs.build(self.goals, self.md, ff)

  def test_quoted_current_behaviour_must_still_be_in_its_row(self):
    md = self.md.replace("No forwarding supervision", "Forwarding supervised")
    with self.assertRaisesRegex(ff.FigureError, "no longer in the Current behaviour"):
      fs.build(ff.parse(md), md, ff)

  def test_lane_needing_a_missing_budget_fails(self):
    model = copy.deepcopy(fs.MODEL)
    model["SG-05"]["chart"]["lanes"][2] = ("torque backs off", "react", None, "x")
    with mock.patch.object(fs, "MODEL", model):
      with self.assertRaisesRegex(ff.FigureError, "reaction budget"):
        fs.build(self.goals, self.md, ff)

  def test_missing_card_fails(self):
    model = dict(fs.MODEL)
    del model["SG-08"]
    with mock.patch.object(fs, "MODEL", model):
      with self.assertRaisesRegex(ff.FigureError, "differ"):
        fs.build(self.goals, self.md, ff)

  def test_scenes_loop_and_output_is_deterministic(self):
    for svg in self.out.values():
      self.assertEqual(svg.count('repeatCount="indefinite"'), svg.count("<animate"))
    self.assertEqual(self.out, fs.build(self.goals, self.md, ff))

  def test_does_not_import_fsc_figures(self):
    src = Path(fs.__file__).read_text(encoding="utf-8")
    self.assertNotRegex(src, r"(?m)^\s*(import|from)\s+fsc_figures")


if __name__ == "__main__":
  unittest.main()
