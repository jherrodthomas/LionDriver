#!/usr/bin/env python3
"""Tests for fig_chart_template.py: output current, every value drawn once, a changed source fails, synthetic
data labelled, every term defined, and the chart agrees with the results page.

Template from .claude/skills/assurance-chart: rename with the generator (test_fig_xx_topic.py), import it as `fg`,
and keep every kind of test. Point the last test at the page that states the same numbers (a results .md table, a
summary row, a sentence in the work product), so the chart and the text cannot disagree.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_chart_template as fg
import terms  # on the path through the generator


class TestChart(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.raw = fg.SOURCE.read_text(encoding="utf-8")
    cls.data = fg.parse(cls.raw)
    cls.svg = (fg.HERE / fg.OUT).read_text(encoding="utf-8")

  def edited(self, change) -> str:
    doc = json.loads(self.raw)
    rec = doc
    for k in fg.CASE:
      rec = rec[k]
    change(doc, rec)
    return json.dumps(doc)

  def test_committed_output_current(self):
    for name, content in fg.build().items():
      self.assertEqual((fg.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run the generator")

  def test_every_result_drawn_once(self):
    for _k, label, v in self.data["results"]:
      self.assertEqual(self.svg.count(f">{label}<"), 1, label)
      self.assertIn(f">{fg.num(v)}", self.svg, label)

  def test_new_key_fails(self):
    bad = self.edited(lambda d, r: r[fg.RESULTS_KEY].update({"lidar": 300.0}))
    with self.assertRaises(fg.FigureError):
      fg.parse(bad)

  def test_missing_key_fails(self):
    bad = self.edited(lambda d, r: r[fg.RESULTS_KEY].pop(next(iter(fg.RESULTS))))
    with self.assertRaises(fg.FigureError):
      fg.parse(bad)

  def test_synthetic_data_labelled(self):
    if not fg.SYNTHETIC:
      self.skipTest("real data")
    self.assertIn(fg.SYNTHETIC, self.svg)
    self.assertIn("no evidence credit", self.svg)
    bad = self.edited(lambda d, r: d.update({"about": "Measured on the road."}))
    with self.assertRaises(fg.FigureError):
      fg.parse(bad)

  def test_every_term_defined(self):
    self.assertIn('<g class="terms">', self.svg)
    _known, unknown = terms.find(terms.svg_texts(self.svg))
    self.assertEqual(unknown, [], "add these to TERMS in assurance/trace/tools/terms.py, or reword")

  def test_agrees_with_results_page(self):
    page = fg.SOURCE.with_suffix(".md").read_text(encoding="utf-8")
    for _k, label, v in self.data["results"][:3]:   # the table states the first three as whole metres
      self.assertIn(f"{v:.0f} m", page, label)


if __name__ == "__main__":
  unittest.main()
