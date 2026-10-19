#!/usr/bin/env python3
"""Tests for fig_sim_ks.py: one animated top view per scenario file, current, small, synthetic, looping (or a still), no script,
every listed event seen in the replay, no loop past an overlap, and each embedded in the scenarios README."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_sim_ks as fk

NS = "{http://www.w3.org/2000/svg}"


class TestKsFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out, cls.errs = fk.build()

  def test_one_figure_per_scenario_file(self):
    import generate
    self.assertEqual(sorted(self.out), sorted(f"fig-sim-{fk.slug(sc.id)}-anim.svg" for sc in generate.SCENARIOS))

  def test_every_event_happens_in_the_replay(self):
    self.assertEqual(self.errs, [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fk.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_sim_ks.py")

  def test_build_is_deterministic(self):
    self.assertEqual(fk.build()[0], self.out)

  def test_svgs_valid_small_synthetic_looping(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), str(fk.W), name)
      self.assertTrue(root.find(f"{NS}desc").text.startswith("Synthetic (DSR-12)"), name)
      self.assertLess(len(content.encode()), 30_000, name)
      self.assertNotIn("<script", content, name)
      if " Looping top view " in root.find(f"{NS}desc").text:
        self.assertIn('repeatCount="indefinite"', content, name)
      else:
        self.assertNotIn("<animate", content, name)

  def test_sprites_are_the_pinned_files(self):
    self.assertEqual(fk.sprite_problems(), [])

  def test_readme_embeds_each_figure(self):
    md = (fk.SCEN / "README.md").read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"](../figures/{name})", md, name)


if __name__ == "__main__":
  unittest.main()
