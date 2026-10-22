#!/usr/bin/env python3
"""Unit tests for hw_animations.py: the metrics, the verdicts, the figures and the wiki build."""
from __future__ import annotations

import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_wiki
import hw_animations as HW

DOC = {"components": [
  {"safety_related": True, "failure_rate_fit": 100, "failure_modes": [
    {"mode": "a", "distribution": 0.5, "violates_sg_directly": True},                                  # 50 SPF
    {"mode": "b", "distribution": 0.5, "violates_sg_directly": True, "safety_mechanism_spf": "SM", "dc_spf": 0.9}]},  # 5 RF
  {"safety_related": True, "failure_rate_fit": 100, "failure_modes": [
    {"mode": "c", "distribution": 1.0, "violates_sg_directly": False, "mpf_potential": True}]},       # 100 latent
  {"safety_related": False, "failure_rate_fit": 999, "failure_modes": []},
]}


class MetricTests(unittest.TestCase):
  def test_the_formulas_on_a_small_fixture(self):
    m = HW.metrics(DOC)
    self.assertAlmostEqual(m["total"], 200)
    self.assertAlmostEqual(m["spf_rf"], 55)
    self.assertAlmostEqual(m["spfm"], 1 - 55 / 200)
    self.assertAlmostEqual(m["lfm"], 1 - 100 / 145)
    self.assertEqual(m["top"][0][1:], ("latent", "c"))

  def test_the_same_as_the_fmea_lint_formulas(self):
    sys.path.insert(0, str(HW.ROOT / "tools" / "safety"))
    try:
      import fmea_lint
    except ImportError:
      self.skipTest("fmea_lint needs jsonschema")
    doc = yaml.safe_load((HW.ROOT / HW.FMEDA).read_text(encoding="utf-8"))
    ours, theirs = HW.metrics(doc), fmea_lint.fmeda_metrics(doc, HW.GOAL)
    self.assertAlmostEqual(ours["spfm"], theirs["spfm"])
    self.assertAlmostEqual(ours["lfm"], theirs["lfm"])

  def test_verdict_wording(self):
    self.assertEqual(HW.verdict_against(0.968, HW.TARGETS["spfm"])[0], "misses ASIL C by 0.2 pts; meets B")
    self.assertEqual(HW.verdict_against(0.995, HW.TARGETS["spfm"])[0], "meets ASIL D")


class RecordTests(unittest.TestCase):
  def test_the_real_records_have_everything_the_figures_rely_on(self):
    self.assertEqual(HW.problems(), [])

  def test_every_channel_has_a_verdict(self):
    v = HW.verdicts()
    for level, *_ in HW.CHANNELS:
      self.assertIn(level, v)

  def test_all_render_to_well_formed_accessible_svg(self):
    for name, text in HW.render().items():
      doc = xml.dom.minidom.parseString(text.encode("utf-8"))
      self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data, name)
      self.assertTrue(doc.getElementsByTagName("desc")[0].firstChild.data, name)

  def test_the_wiki_build_writes_both_and_accepts_the_embeds(self):
    with tempfile.TemporaryDirectory() as d:
      out = Path(d) / "wiki"
      self.assertEqual(build_wiki.build(out=out), [])
      page = (out / "Hardware-safety-and-interference.md").read_text(encoding="utf-8")
      for name in HW.NAMES:
        self.assertTrue((out / name).exists(), name)
        self.assertIn(f"]({name})", page)


if __name__ == "__main__":
  unittest.main()
