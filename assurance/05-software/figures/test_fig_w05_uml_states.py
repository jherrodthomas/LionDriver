#!/usr/bin/env python3
"""Tests for fig_w05_uml_states.py: committed SVGs current, every transition of each record drawn once in its chip and
once in its table, a changed record fails, and the subtitle counts agree with the record."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_w05_uml_states as fg


class TestFigure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.ms = fg.machines()

  def test_committed_output_current(self):
    for name, content in fg.build().items():
      self.assertEqual((fg.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_every_transition_drawn(self):
    for machine, _, name, _ in fg.FIGS:
      svg = (fg.HERE / name).read_text(encoding="utf-8")
      for t in self.ms[machine]["transitions"]:
        self.assertGreaterEqual(svg.count(f">{t['id']}<"), 2, f"{machine} {t['id']}: chip and table row")
      self.assertIn('<g class="terms">', svg)

  def test_counts_agree(self):
    sm = self.ms["SM-TOY-AUTH"]
    svg = (fg.HERE / "fig-w05-5-1-uml-sm-toy-auth.svg").read_text(encoding="utf-8")
    n_not = sum(t["status"] == "not" for t in sm["transitions"])
    self.assertIn(f"{len(sm['transitions'])} transitions", svg)
    self.assertIn(f"{n_not} not implemented", svg)

  def test_unknown_state_fails(self):
    sm = copy.deepcopy(self.ms["SM-TOY-AUTH"])
    sm["transitions"][0]["to"] = "NOWHERE"
    with self.assertRaises(fg.FigureError):
      fg.edges(sm)

  def test_state_without_position_fails(self):
    sm = copy.deepcopy(self.ms["SM-SELFDRIVED"])
    sm["states"].append("newState")
    with self.assertRaises(fg.FigureError):
      fg.diagram(sm, (0, 0, 100, 100))

  def test_walk_must_chain(self):
    saved = list(fg.WALK)
    try:
      fg.WALK[:] = ["T1b"]                 # T1b leaves ENGAGE_PENDING, not the initial NOT_ALLOWED
      with self.assertRaises(fg.FigureError):
        fg.walk(self.ms["SM-TOY-AUTH"])
    finally:
      fg.WALK[:] = saved

  def test_any_source_leaves_the_frame(self):
    es = fg.edges(self.ms["SM-TOY-AUTH"])
    self.assertIn(("*", "NOT_ALLOWED"), {(e["src"], e["dst"]) for e in es})      # T7 from any state


if __name__ == "__main__":
  unittest.main()
