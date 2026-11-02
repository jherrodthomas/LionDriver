#!/usr/bin/env python3
"""Tests for fig_template.py: committed SVG current, every source row drawn once, a changed source fails.

Template from .claude/skills/assurance-figure: rename with the generator (test_fig_xx_topic.py), import it as `fg`,
and keep the three kinds of test. Add one that checks the figure against a number the document states elsewhere
(a summary row, a count in the prose), so the figure and the text cannot disagree.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_template as fg


class TestFigure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.md = fg.SOURCE.read_text(encoding="utf-8")
    cls.rows = fg.parse(cls.md)

  def test_committed_output_current(self):
    for name, content in fg.build().items():
      self.assertEqual((fg.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_every_row_drawn_once(self):
    svg = (fg.HERE / fg.OUT).read_text(encoding="utf-8")
    for r in self.rows:
      self.assertEqual(svg.count(f">{r['id']}<"), 1, r["id"])

  def test_ends_with_definitions_line(self):
    self.assertIn('<g class="terms">', (fg.HERE / fg.OUT).read_text(encoding="utf-8"))

  def test_unknown_status_fails(self):
    first = self.rows[0]
    bad = self.md.replace(f"| {first['status']} |", "| Somewhere else |", 1)
    self.assertNotEqual(bad, self.md)
    with self.assertRaises(fg.FigureError):
      fg.parse(bad)

  def test_missing_section_fails(self):
    with self.assertRaises(fg.FigureError):
      fg.parse(self.md.replace(fg.HEADING, "## Renamed", 1))


if __name__ == "__main__":
  unittest.main()
