#!/usr/bin/env python3
"""Tests for fig_s00_se.py: the alignment YAML resolves, the committed Vee and README section are current."""

import copy
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s00_se as fs


class TestSeAlignment(unittest.TestCase):
  def setUp(self):
    self.d = fs.load()
    self.hrefs = fs.wp_hrefs()

  def test_yaml_resolves(self):
    self.assertEqual(fs.problems(self.d, self.hrefs), [])

  def test_committed_outputs_current(self):
    for path, content in fs.build().items():
      self.assertTrue(path.exists(), path.name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{path.name} is stale; run fig_s00_se.py")

  def test_svg_parses_and_has_title(self):
    root = ET.fromstring(fs.render(self.d))
    self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))

  def test_unknown_wp_and_path_are_caught(self):
    d = copy.deepcopy(self.d)
    d["stages"][0]["wps"].append("WP-S-99")
    d["views"][0]["where"].append({"path": "03-system/figures/no-such.svg", "label": "x"})
    errs = fs.problems(d, self.hrefs)
    self.assertTrue(any("WP-S-99" in e for e in errs), errs)
    self.assertTrue(any("no-such.svg" in e for e in errs), errs)

  def test_every_nasa_process_once(self):
    d = copy.deepcopy(self.d)
    d["management"].pop()
    self.assertTrue(any("1-17" in e for e in fs.problems(d, self.hrefs)))

  def test_partial_view_needs_gap(self):
    d = copy.deepcopy(self.d)
    v = next(v for v in d["views"] if v["status"] == "partial")
    del v["gap"]
    self.assertTrue(any("needs a gap" in e for e in fs.problems(d, self.hrefs)))

  def test_readme_carries_the_section(self):
    readme = (fs.ASSURANCE / fs.FOLDER / "README.md").read_text(encoding="utf-8")
    self.assertIn(fs.section_md(self.d, self.hrefs).rstrip(), readme)
    for target in (fs.N2, fs.VCRM):
      self.assertTrue((fs.HERE.parent / target).resolve().exists(), target)


if __name__ == "__main__":
  unittest.main()
