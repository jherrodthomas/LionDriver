#!/usr/bin/env python3
"""Tests for fig_models.py: tables consistent, SVGs current and valid, every §2 row drawn, drift detected."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_models as fm

NS = "{http://www.w3.org/2000/svg}"


class TestModelsFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fm.README.read_text(encoding="utf-8")
    cls.out = fm.build()

  def test_no_source_problems(self):
    self.assertEqual(fm.problems(self.md), [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fm.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_models.py")

  def test_deterministic(self):
    self.assertEqual(fm.build(), self.out)

  def test_svgs_valid_phone_width_with_title_desc_and_dark_theme(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), str(fm.W), name)
      self.assertTrue(root.find(f"{NS}title").text, name)
      self.assertTrue(root.find(f"{NS}desc").text, name)
      self.assertIn("prefers-color-scheme: dark", content, name)

  def test_every_item_drawn_with_its_state(self):
    its = fm.items(self.md)
    self.assertEqual([it.num for it in its][:2], ["1", "2"])
    desc = ET.fromstring(self.out["fig-md-2-work-items.svg"]).find(f"{NS}desc").text
    for it in its:
      self.assertIn(f"{it.title}: {it.state}", desc)

  def test_tool_map_shows_gates_and_rule(self):
    svg = self.out["fig-md-1-tool-map.svg"]
    for _num, tl, _k in fm.GATES:
      self.assertIn(f">{tl}<", svg)
    self.assertIn(fm.EVIDENCE_RULE, svg)
    self.assertIn(">only if needed<", svg)  # OpenModelica on item 4, from "OpenModelica only as in MD-01"

  def test_drift_is_reported(self):
    # a changed state word, a new tool row without a gate, and a lost rule sentence each fail
    md = self.md.replace("| Exists: [`octave/`]", "| Planned: [`octave/`]")
    self.assertTrue(any("state" in p for p in fm.problems(md)))
    md = self.md.replace("| 5 | Architecture model", "| 9 | Something new | Python | Draft |\n| 5 | Architecture model")
    self.assertTrue(any("item 9 names a tool" in p for p in fm.problems(md)))
    md = self.md.replace(fm.EVIDENCE_RULE, "Model output is evidence")
    self.assertTrue(any("sentence" in p for p in fm.problems(md)))

  def test_item_parsing(self):
    it = fm.Item("4", "HIL plant model: Corolla EPS", "Python (OpenModelica only as in MD-01)", "In progress: x")
    self.assertEqual((it.title, it.state), ("HIL plant model", "In progress"))
    self.assertEqual(it.tools, [("Python", "py", False), ("OpenModelica", "om", True)])
    it = fm.Item("2", "SM-SELFDRIVED record (host state machine)", "Python checker", "Exists: y")
    self.assertEqual(it.title, "SM-SELFDRIVED record")


if __name__ == "__main__":
  unittest.main()
