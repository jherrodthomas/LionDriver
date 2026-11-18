#!/usr/bin/env python3
"""Tests for fig_h02_box_anim.py: committed SVG current, every frame drawn once from its scenario, a changed source
fails, and the box state of each frame follows the rule ngspice's verdict states."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_h02_box_anim as fg


class TestFigure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.net, cls.frames, cls.vals = fg.load()
    cls.svg = (fg.HERE / fg.OUT).read_text(encoding="utf-8")

  def test_committed_output_current(self):
    for name, content in fg.build().items():
      self.assertEqual((fg.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_every_frame_drawn_once(self):
    self.assertEqual(len(self.frames), len(fg.FRAMES))
    for i, f in enumerate(self.frames):
      self.assertEqual(self.svg.count(f'class="fr f{i}"'), 1, f["id"])
      self.assertIn(f["title"], self.svg)
    self.assertIn('<g class="terms">', self.svg)

  def test_box_state_matches_the_verdict(self):
    states = {f["id"]: f["intercept"] for f in self.frames}
    self.assertEqual(states, {"pass_through": False, "intercept": True, "pulldown_open_leak_up": True,
                              "threshold_high_vin_high": False})

  def test_switch_path_from_the_netlist(self):
    self.assertEqual(self.net["sw"]["U1"]["com"], "can2h")
    self.assertEqual(self.net["term"]["R7"][2], 120.0)
    self.assertEqual(self.vals["pull_down"], 240.0)

  def test_missing_scenario_fails(self):
    data = json.loads(fg.RESULTS.read_text(encoding="utf-8"))
    data["scenarios"] = [s for s in data["scenarios"] if s["id"] != "intercept"]
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "harness-box.json"
      p.write_text(json.dumps(data), encoding="utf-8")
      saved, fg.RESULTS = fg.RESULTS, p
      try:
        with self.assertRaises(fg.FigureError):
          fg.load()
      finally:
        fg.RESULTS = saved

  def test_verdict_disagreeing_with_the_voltages_fails(self):
    data = json.loads(fg.RESULTS.read_text(encoding="utf-8"))
    for s in data["scenarios"]:
      if s["id"] == "intercept":
        s["nodes"]["SBU1"] = 1.0
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "harness-box.json"
      p.write_text(json.dumps(data), encoding="utf-8")
      saved, fg.RESULTS = fg.RESULTS, p
      try:
        with self.assertRaises(fg.FigureError):
          fg.load()
      finally:
        fg.RESULTS = saved


if __name__ == "__main__":
  unittest.main()
