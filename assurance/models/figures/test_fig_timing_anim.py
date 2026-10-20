#!/usr/bin/env python3
"""Tests for fig_timing_anim.py: committed SVG current and well-formed, rows and verdicts follow the Octave results,
and every SMIL animation has valid timing (an invalid keyTimes list stops the animation without an error)."""

import re
import sys
import unittest
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_timing_anim as fa

SVG = "{http://www.w3.org/2000/svg}"


class TestTimingAnimation(unittest.TestCase):
  def test_committed_output_current(self):
    self.assertEqual((fa.HERE / fa.OUT).read_text(encoding="utf-8"), fa.figure(), "stale; run fig_timing_anim.py")

  def test_parses_and_has_title_and_desc(self):
    root = ET.fromstring(fa.figure())
    self.assertIsNotNone(root.find(f"{SVG}title"))
    self.assertIsNotNone(root.find(f"{SVG}desc"))

  def test_deterministic(self):
    self.assertEqual(fa.figure(), fa.figure())

  def test_rows_come_from_the_model(self):
    rows = fa.load()
    for rid in fa.ROWS:
      self.assertIn(rid, rows)
    svg = fa.figure()
    for rid in fa.ROWS:
      self.assertIn(escape(rows[rid]["label"].replace(", baseline", "")), svg)

  def test_verdicts_follow_the_model_flags(self):
    rows = fa.load()
    self.assertEqual(fa.verdict(rows["rx-260-base"])[1], fa.RED)    # FTTI exceeded in the original baseline
    self.assertEqual(fa.verdict(rows["stall-ref"])[1], fa.AMBER)    # 10 ms over the FDTI budget, FTTI met (T-34)
    self.assertEqual(fa.verdict(rows["rx-1d2-ref"])[1], fa.GREEN)
    for rid in fa.ROWS:
      msg, col = fa.verdict(rows[rid])
      self.assertEqual(col == fa.RED, rows[rid]["ftti_ok"] != "1" or rows[rid]["warn_ok"] == "0", rid)

  def test_animation_timing_is_valid(self):
    root = ET.fromstring(fa.figure())
    anims = [e for e in root.iter() if e.tag in (f"{SVG}animate", f"{SVG}animateTransform")]
    self.assertGreater(len(anims), 30)
    for a in anims:
      self.assertEqual(a.get("dur"), f"{fa.DUR}s")
      self.assertEqual(a.get("repeatCount"), "indefinite")
      kt = [float(v) for v in a.get("keyTimes").split(";")]
      vals = a.get("values").split(";")
      self.assertEqual(len(kt), len(vals), a.attrib)
      self.assertEqual(kt[0], 0.0)
      self.assertEqual(kt[-1], 1.0)
      self.assertTrue(all(b > x for x, b in zip(kt, kt[1:])), f"keyTimes not increasing: {kt}")

  def test_bars_never_negative(self):
    for w in re.findall(r'attributeName="width" values="([^"]+)"', fa.figure()):
      self.assertTrue(all(float(v) >= 0 for v in w.split(";")), w)


if __name__ == "__main__":
  unittest.main()
