#!/usr/bin/env python3
"""Tests for fig_dq424.py: numbers read and computed, agreement with the documents, card rules, layout, drift."""

import copy
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import fig_dq424 as fq
import terms
from figkit import FigureError


class TestDq424Figure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.s02 = fq.WP_S02.read_text(encoding="utf-8")
    cls.s04 = fq.WP_S04.read_text(encoding="utf-8")
    cls.w02 = fq.WP_W02.read_text(encoding="utf-8")
    cls.planner = fq.PLANNER.read_text(encoding="utf-8")
    cls.dq = fq.entry()
    cls.src = fq.sources(cls.s02, cls.s04, cls.w02, cls.planner, cls.dq)
    cls.opts = {o["key"]: o for o in fq.computed(cls.src)}
    cls.svg = fq.build(cls.src)

  def src_with(self, **kw):
    args = {"s02": self.s02, "s04": self.s04, "w02": self.w02, "planner": self.planner, "dq": self.dq} | kw
    return fq.sources(**args)

  def test_no_problems(self):
    self.assertEqual(fq.problems(self.src), [])

  def test_committed_output_current_and_deterministic(self):
    self.assertEqual(fq.OUT.read_text(encoding="utf-8"), self.svg, "stale; run fig_dq424.py")
    self.assertEqual(fq.build(self.src), self.svg)

  def test_values_read_from_the_records(self):
    self.assertEqual(self.src["v0_kmh"], 110)
    self.assertEqual([o["rate"] for o in self.src["options"]], [2.0, 1.2, 3.0])
    self.assertEqual(self.src["j_down"], 5.0)
    self.assertEqual(self.opts["A"]["jerk"], self.src["j_down"])
    self.assertIsNone(self.opts["B"]["jerk"])

  def test_kinematics(self):
    v0 = 110 / 3.6
    a = self.opts["A"]
    self.assertAlmostEqual(a["ramp"], 0.4)
    self.assertAlmostEqual(a["t"], 0.4 + (v0 - 0.4) / 2, places=6)
    self.assertAlmostEqual(self.opts["B"]["d"], v0 ** 2 / 2.4, places=6)
    self.assertAlmostEqual(self.opts["C"]["t"], v0 / 3, places=6)
    # the curve is continuous and reaches 0 at the computed stop time
    self.assertAlmostEqual(fq.speed(a["t"], v0, 2.0, 5.0), 0.0, places=6)
    self.assertAlmostEqual(fq.speed(a["ramp"] - 1e-9, v0, 2.0, 5.0), fq.speed(a["ramp"], v0, 2.0, 5.0), places=6)

  def test_agrees_with_what_the_documents_state(self):
    # options: about 15 s and 230 m; 25 s and 390 m; 10 s and 150 m. TSR-633 and WP-S-04 §3.7 state A's too.
    self.assertEqual([o["stated"] for o in self.src["options"]], [(15, 230), (25, 390), (10, 150)])
    for k, o in self.opts.items():
      self.assertTrue(fq.agrees(o["t"], o["d"], o["stated"]), k)
    for where, stated in self.src["stated_a"].items():
      self.assertEqual(stated, (15, 230), where)
    self.assertTrue(230 <= self.opts["A"]["d"] <= 241)
    t_h, d_h, _ = fq.stop(110 / 3.6, 2.0, self.src["j_host"])  # host final-command rate limit, gentler ramp
    self.assertTrue(230 <= d_h <= 241 and fq.agrees(t_h, d_h, (15, 230)))

  def test_every_option_drawn_once_with_its_computed_label(self):
    texts = [t.text or "" for t in ET.fromstring(self.svg).iter("text")]
    for o in self.opts.values():
      self.assertEqual(texts.count(o["label"]), 1, o["label"])
    self.assertEqual([o["label"] for o in self.opts.values()], ["A · 15 s, 240 m", "B · 25 s, 390 m", "C · 10 s, 155 m"])
    title = ET.fromstring(self.svg).find("title").text
    for o in self.opts.values():
      self.assertIn(f"{o['t']:.1f} s and {round(o['d'])} m", title)

  def test_card_rules(self):
    root = ET.fromstring(self.svg)
    self.assertNotIn("<style", self.svg)
    self.assertNotIn("#", re.sub(r"<title.*?</title>", "", self.svg))  # tokens only, no hex colour
    self.assertIsNone(root.get("width"))
    self.assertTrue(root.get("viewBox").startswith("0 0 640 "))
    self.assertEqual(root.get("role"), "img")
    for t in root.iter("text"):
      self.assertGreaterEqual(float(t.get("font-size")), 12)
    paths = {p.get("stroke"): p for p in root.iter("path")}
    self.assertEqual(paths["var(--accent)"].get("stroke-width"), "3.5")
    self.assertTrue(paths["var(--muted)"].get("stroke-dasharray"))
    self.assertIn("var(--bad)", paths)

  def test_labels_inside_and_clear_of_lines_and_each_other(self):
    t_max, x, y = fq.axis(self.src, list(self.opts.values()))
    lines = {k: fq.points(o, self.src, x, y) for k, o in self.opts.items()}
    placed = fq.place(list(self.opts.values()), lines)
    segs = [s for pts in lines.values() for s in zip(pts, pts[1:], strict=False)]
    boxes = [p[3] for p in placed.values()]
    for k, box in zip(placed, boxes, strict=True):
      self.assertGreaterEqual(box[0], 0, k)
      self.assertLessEqual(box[2], fq.W, k)
      self.assertFalse(fq._hits(box, segs), k)
    for i in range(len(boxes)):
      for j in range(i + 1, len(boxes)):
        self.assertFalse(fq._overlap(boxes[i], boxes[j]))

  def test_no_undefined_term(self):
    # the title row is upper case by the card convention; its words are ordinary words, checked in lower case
    title = re.search(r'<text[^>]*letter-spacing[^>]*>([^<]*)</text>', self.svg).group(1)
    self.assertEqual(terms.find(terms.svg_texts(self.svg.replace(title, title.lower())))[1], [])

  def test_drift_is_reported(self):
    with self.assertRaises(FigureError):
      self.src_with(s02=self.s02.replace("at 2 m/s², ramped in within j_down", "at 2 m/s² within j_down"))
    with self.assertRaises(FigureError):
      self.src_with(w02=self.w02.replace("| j_down | 205, 206 | 5 m/s³", "| j_down | 205, 206 | 4 m/s³"))
    with self.assertRaises(FigureError):
      self.src_with(planner=self.planner.replace("A_CRUISE_MIN = -1.2", "A_CRUISE_MIN = -1.0"))
    dq = copy.deepcopy(self.dq)
    dq["options"][2]["title"] = dq["options"][2]["title"].replace("3 m/s²", "4 m/s²")
    self.assertTrue(any("option C" in p for p in fq.problems(self.src_with(dq=dq))))
    dq = copy.deepcopy(self.dq)
    dq["options"][0]["title"] = dq["options"][0]["title"].replace("230 m", "200 m")
    self.assertTrue(any("option A" in p for p in fq.problems(self.src_with(dq=dq))))
    s04 = self.s04.replace("standstill about 15 s and 230 m later", "standstill about 10 s and 150 m later")
    self.assertTrue(any("WP-S-04" in p for p in fq.problems(self.src_with(s04=s04))))
    dq = copy.deepcopy(self.dq)
    dq["figure"] = "figures/other.svg"
    self.assertTrue(any("no longer names" in p for p in fq.problems(self.src_with(dq=dq))))


if __name__ == "__main__":
  unittest.main()
