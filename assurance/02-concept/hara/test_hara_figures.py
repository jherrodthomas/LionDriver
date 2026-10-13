#!/usr/bin/env python3
"""Tests for hara_figures.py: committed figures are current and agree with the model and WP-C-03."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hara_figures as hf
import hara_model as hm


class TestHaraFigures(unittest.TestCase):
  def test_committed_outputs_current(self):
    for name, content in hf.build().items():
      self.assertEqual((hf.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_heatmap_counts_cover_every_rated_row(self):
    rows, rated, failed, s0 = hf.heat_counts()
    self.assertEqual(sum(rated.values()) + s0, len(rows))
    self.assertEqual(sum(failed.values()) + s0, len(rows))
    for (s, e, c), n in rated.items():
      self.assertEqual(sum(1 for r in rows if (r["S"], r["E"], r["C"]) == (s, e, c)), n)
    by_cell = {a: sum(n for k, n in rated.items() if hm.asil(*k) == a) for a in "ABCD"}
    self.assertEqual(by_cell, {a: sum(1 for r in rows if r["asil"] == a) for a in "ABCD"})
    by_cell_f = {a: sum(n for k, n in failed.items() if hm.asil(*k) == a) for a in "ABCD"}
    self.assertEqual(by_cell_f, {a: sum(1 for r in rows if r["asil_aou_fail"] == a) for a in "ABCD"})

  def test_overview_parses_document(self):
    hazards, hes, goals = hf.parse_hara(hf.SOURCE.read_text(encoding="utf-8"))
    self.assertEqual(sorted(hazards), [f"H-0{i}" for i in range(1, 9)])
    self.assertEqual([g.ident for g in goals], [f"SG-0{i}" for i in range(1, 8)])
    self.assertEqual(hes["HE-02.3"].goals, ["SG-01"])
    self.assertEqual(hes["HE-07.3"].goals, ["SG-06"])
    self.assertEqual(hes["HE-06.2"].goals, [])

  def test_goal_asil_mismatch_rejected(self):
    md = hf.SOURCE.read_text(encoding="utf-8").replace("| **SG-03** | The item shall not cause unintended vehicle acceleration | **B**",
                                                        "| **SG-03** | The item shall not cause unintended vehicle acceleration | **C**")
    with self.assertRaises(hf.FigureError):
      hf.parse_hara(md)

  def test_unlisted_rated_event_rejected(self):
    md = hf.SOURCE.read_text(encoding="utf-8").replace("HE-01.1–01.4, HE-02.3", "HE-01.1–01.4")
    with self.assertRaises(hf.FigureError):
      hf.parse_hara(md)


if __name__ == "__main__":
  unittest.main()
