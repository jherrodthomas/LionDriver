#!/usr/bin/env python3
"""Tests for fig_fi001_problem.py: the committed figures are current, every source row is drawn once, a changed
source fails loudly, and the figures agree with the numbers the problem statement and the RCA state."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fig_fi001_problem as fig  # noqa: E402


class FigureTests(unittest.TestCase):
  def test_committed_figures_are_current(self):
    for name, content in fig.build().items():
      self.assertEqual((HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_every_layer_and_weakness_drawn_once(self):
    out = fig.fig_barriers()
    for b in fig.barriers():
      self.assertEqual(out.count(f">{fig.LAYERS[b['id']]}<"), 1, b["id"])
      for label, _ in b["holes"]:
        first = fig.wrap(label, 222 - 44, 11.5)[0]
        self.assertEqual(out.count(f">{first}<"), 1, label)

  def test_every_speed_drawn_once(self):
    out = fig.fig_distance()
    rows = fig.distances()
    self.assertEqual(len(rows), 4)
    for kmh, cap, full, _ in rows:
      self.assertEqual(out.count(f">{kmh} km/h<"), 1)
      self.assertIn(f">{cap} m · ", out)
      self.assertIn(f">{full} m<", out)

  def test_every_scene_drawn_once(self):
    out = fig.fig_scenes()
    for s in fig.SCENES:
      self.assertEqual(out.count(f">{s['title']}<"), 1, s["title"])

  def test_reworded_weakness_fails(self):
    md = fig.RCA.read_text(encoding="utf-8").replace("tolerates **5 s**", "tolerates **4 s**")
    with mock.patch.object(Path, "read_text", lambda self, encoding=None: md), self.assertRaises(fig.FigureError):
      fig.barriers()

  def test_unknown_layer_fails(self):
    md = fig.RCA.read_text(encoding="utf-8").replace("**L2 — Driver**", "**L9 — Driver**")
    with mock.patch.object(Path, "read_text", lambda self, encoding=None: md), self.assertRaises(fig.FigureError):
      fig.barriers()

  def test_unparsable_distance_fails(self):
    md = fig.RCA.read_text(encoding="utf-8").replace("| 144 m |", "| about 144 m |")
    with mock.patch.object(Path, "read_text", lambda self, encoding=None: md), self.assertRaises(fig.FigureError):
      fig.distances()

  def test_scene_quote_must_stay_in_source(self):
    gone = [dict(fig.SCENES[0], quote="a phrase that is not in the report")]
    with mock.patch.object(fig, "SCENES", gone), self.assertRaises(fig.FigureError):
      fig.fig_scenes()

  def test_page_agrees_with_the_figures(self):
    page = (fig.CASE / "PROBLEM-STATEMENT.md").read_text(encoding="utf-8")
    for name in fig.OUTPUTS:
      self.assertIn(f"figures/{name}", page)
    for kmh, cap, full, _ in fig.distances():
      if kmh in (108, 126):
        self.assertIn(f"{cap} m", page, f"the page should quote the {kmh} km/h distance")
    self.assertIn(fig.RANGE, page)
    self.assertEqual(len(re.findall(r"^\| \*\*Layer \d", page, re.M)), len(fig.LAYERS))


if __name__ == "__main__":
  unittest.main()
