#!/usr/bin/env python3
"""Tests for the SG-06 Fault Lab page (tool evaluation TE-02 step P5, DQ-417): the replay is the model's run, the
timeline shows every event it reaches, and the page builds. The sweep itself is tested in test_sg06.py; here the P4
run is stubbed, so the test runs in a few seconds."""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fault_lab as fl  # noqa: E402


class Replay(unittest.TestCase):
  def test_replay_is_cued_by_the_cluster(self):
    r = fl.replay()
    self.assertEqual(r["outcome"].cue, "cluster")
    self.assertFalse(r["outcome"].top_event)
    self.assertNotIn("t_alert", r["t"])                     # the hung HMI never shows the alert
    self.assertLess(r["t"]["t_disengage"], r["t"]["t_cluster"])
    self.assertEqual(r["without_cancel"].cue, "siren")      # cancel-lag guard

  def test_timeline_has_every_event(self):
    r = fl.replay()
    svg = fl.timeline(r)
    for k in ("t_alert_request", "t_disengage", "t_cluster"):
      self.assertIn(f"{r['t'][k]:.2f} s", svg)
    self.assertIn(">none<", svg)                             # alert shown, siren


class Page(unittest.TestCase):
  def test_page_builds_from_stubbed_sweep(self):
    stub = {"order": 2, "runs": 7, "modes": 3, "model": [], "tree": [], "agree": [], "tree_only": [], "by_siren": [],
            "by_cancel": [], "gaps": [], "timing": [], "within": [], "late": [], "none": [], "tight": None,
            "budget": 1.0}
    real = fl.sweep_data
    fl.sweep_data = lambda: stub
    try:
      page = fl.build()
    finally:
      fl.sweep_data = real
    self.assertIn("<title>SG-06 Fault Lab</title>", page)
    self.assertIn("no evidence credit", page)
    self.assertIn("prefers-color-scheme:dark", page)
    self.assertIn("No plant case for a loss of deceleration", page)


if __name__ == "__main__":
  unittest.main()
