#!/usr/bin/env python3
"""Tests for fig_sim_plots.py: current, deterministic, valid, small, looping, no script, read from the committed
results, drift detected, embedded in the README."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_sim_plots as fp

NS = "{http://www.w3.org/2000/svg}"


class TestSimPlotLoops(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.out, cls.errs = fp.build()

  def test_no_problems(self):
    self.assertEqual(fp.ks.sprite_problems() + self.errs, [])

  def test_committed_outputs_current(self):
    for name, content in self.out.items():
      path = fp.HERE / name
      self.assertTrue(path.exists(), name)
      self.assertEqual(path.read_text(encoding="utf-8"), content, f"{name} is stale; run fig_sim_plots.py")

  def test_deterministic(self):
    self.assertEqual(fp.build()[0], self.out)

  def test_valid_phone_width_looping_no_script(self):
    for name, content in self.out.items():
      root = ET.fromstring(content)
      self.assertEqual(root.get("role"), "img", name)
      self.assertEqual(root.get("width"), str(fp.W), name)
      self.assertTrue(root.find(f"{NS}title").text, name)
      self.assertIn("Synthetic (DSR-12), no evidence credit", root.find(f"{NS}desc").text, name)
      self.assertIn("prefers-color-scheme: dark", content, name)
      self.assertIn('repeatCount="indefinite"', content, name)
      self.assertNotIn("<script", content, name)
      self.assertLess(len(content.encode()), 50_000, name)

  def test_reach_events_from_the_data(self):
    desc = ET.fromstring(self.out["fig-sim-reach-anim.svg"]).find(f"{NS}desc").text
    d = fp.reach_data()
    self.assertIn(f"at {d['s']['takeover_s']:.2f} s", desc)
    self.assertIn(f"bound {fp.at(d['t'], d['bound'], d['s']['takeover_s']):.2f} m", desc)
    self.assertIn("62 sampled runs", desc)

  def test_search_reads_every_sample(self):
    d, errs = fp.search_data()
    self.assertEqual(errs, [])
    self.assertEqual(len(d["mc"]), 120)
    self.assertEqual(sum(r["bad"] for r in d["mc"]), 71)
    for r in d["mc"]:
      self.assertTrue(-0.01 <= r["a_y"] <= 1.81 and 0.74 <= r["t_r"] <= 1.51, r)
    self.assertEqual(sorted({r["round"] for r in d["ce"]}), [1, 2, 3, 4])

  def test_drift_is_reported(self):
    md = fp.SEARCH_MD.read_text(encoding="utf-8")
    real = fp.SEARCH_MD
    tmp = Path(__file__).resolve().parent / "_drift_search.md"
    try:
      tmp.write_text(md.replace("71 of 120 samples depart", "70 of 120 samples depart"), encoding="utf-8")
      fp.SEARCH_MD = tmp
      _d, errs = fp.search_data()
      self.assertTrue(any("departing" in e for e in errs), errs)
    finally:
      fp.SEARCH_MD = real
      tmp.unlink(missing_ok=True)

  def test_embedded_in_readme(self):
    md = (fp.SIM / "README.md").read_text(encoding="utf-8")
    for name in self.out:
      self.assertIn(f"](figures/{name})", md, name)


if __name__ == "__main__":
  unittest.main()
