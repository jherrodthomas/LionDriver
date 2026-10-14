#!/usr/bin/env python3
"""Tests for fig_p_process.py: source texts present, committed SVGs current, valid, and drawn from the tables."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_p_process as fp

NS = "{http://www.w3.org/2000/svg}"


class TestProcessFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.outputs = fp.build()

  def test_source_texts_present(self):
    self.assertEqual(fp.missing_sources(), [])

  def test_committed_outputs_current(self):
    for name, content in self.outputs.items():
      path = fp.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_p_process.py")

  def test_deterministic(self):
    self.assertEqual(fp.build(), self.outputs)

  def test_svgs_valid_with_role_title_desc(self):
    for name, content in self.outputs.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertTrue(root.find(f"{NS}title").text, name)
      self.assertTrue(root.find(f"{NS}desc").text, name)

  def test_every_step_drawn_in_its_lane(self):
    for doc, heading, first, cols, name in [
        (fp.WP_P_02, "## 5. Process", "Step", ("Step", "Activity", "Output", "Responsible"), "fig-p02-5-1-change-swimlane.svg"),
        (fp.WP_P_03, "## 5. Workflow", "State (label)", ("State (label)", "Activity", "Exit criterion", "Who"), "fig-p03-5-1-problem-swimlane.svg"),
        (fp.WP_P_10, "## 4. Procedure", "Step", ("Step", "Activity", "Output", "Responsible"), "fig-p10-4-1-release-swimlane.svg")]:
      steps = fp.load_steps(doc, heading, first, *cols)
      desc = ET.fromstring(self.outputs[name]).find(f"{NS}desc").text
      for s in steps:
        self.assertIn(f"{s.label}: {s.activity} ({s.lane}", desc, f"{name}: step {s.label}")
        self.assertIn(f">{s.lane}</text>", self.outputs[name], f"{name}: lane {s.lane}")

  def test_split_who(self):
    self.assertEqual(fp.split_who("Author; checked by reviewer"), ("Author", "checked by reviewer"))
    self.assertEqual(fp.split_who("Maintainer (CCB, §7.3)"), ("Maintainer", "CCB, §7.3"))
    self.assertEqual(fp.split_who("Safety manager + CS manager + maintainer"), ("Safety manager", "CS manager + maintainer"))
    self.assertEqual(fp.split_who("verifier"), ("Verifier", ""))

  def test_plain(self):
    self.assertEqual(fp.plain("update [WP-M-00](../x.md) and `assurance/trace/` **now**"), "update WP-M-00 and assurance/trace/ now")

  def test_wrap_limits_lines(self):
    lines = fp.wrap("word " * 80, 120, 11, 3)
    self.assertEqual(len(lines), 3)
    self.assertTrue(lines[-1].endswith("…"))

  def test_lifecycle_rules_name_known_states(self):
    states, rules, review, _ = fp.load_lifecycle()
    self.assertEqual([s for s, _ in states], ["Skeleton", "Draft", "In review", "Approved", "Baselined"])
    self.assertEqual(set(rules), {"In review", "Approved", "Baselined"})
    self.assertEqual(review[0][0], "Author submits")
    self.assertEqual(review[-1][0], "Merge")


if __name__ == "__main__":
  unittest.main()
