#!/usr/bin/env python3
"""Tests for fig_sim_he.py: ASIL C events match WP-C-03, the runs show the reactions drawn, SVGs current and animated."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_sim_he as fh

NS = "{http://www.w3.org/2000/svg}"


class TestHeFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out, cls.errs = fh.build()

  def test_asil_c_events_match_hara(self):
    self.assertEqual(fh.problems(), [])
    h = fh.hara()
    for he in fh.RUNS:
      self.assertEqual(h[he]["asil"], "C", he)

  def test_runs_show_the_reactions_drawn(self):
    self.assertEqual(self.errs, [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fh.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_sim_he.py")

  def test_build_is_deterministic(self):
    self.assertEqual(fh.build()[0], self.out)

  def test_svgs_valid_small_synthetic(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), str(fh.W), name)
      self.assertTrue(root.find(f"{NS}desc").text.startswith("Synthetic (DSR-12)"), name)
      self.assertLess(len(content.encode()), 25_000, name)

  def test_animations_loop_without_script(self):
    for name, content in self.out.items():
      if name.endswith("-anim.svg"):
        self.assertIn('repeatCount="indefinite"', content, name)
        self.assertNotIn("<script", content, name)

  def test_readme_embeds_each_figure_and_links_kinematic_dashboards(self):
    md = (fh.SIM / "README.md").read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"](figures/{name})", md, name)
    for he in fh.KINEMATIC:
      self.assertIn(f"[{he}](blender/dashboards/", md, he)


if __name__ == "__main__":
  unittest.main()
