#!/usr/bin/env python3
"""Tests for hara_views.py: the situation and function figures follow hara_model.py and are current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hara_figures as hf
import hara_model as hm
import hara_views as hv


class TestHaraViews(unittest.TestCase):
  def test_committed_output_current(self):
    for name, content in hv.build().items():
      self.assertEqual((hf.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_function_model(self):
    m = hv.function_model()
    self.assertEqual(list(m), [f[0] for f in hm.FUNCTIONS])
    for f_id, v in m.items():
      self.assertEqual(len(v["cells"]), 14)
      self.assertEqual(v["n_sc"], sum(1 for mid, _ in hm.MALFUNCTIONS if hm.FM[f_id][mid][0] == hm.SC))
    self.assertEqual(m["F-01"]["top"], "C")
    self.assertEqual(m["F-09"]["hazards"], [])
    self.assertIn("SG-07", m["F-08"]["goals"])
    self.assertEqual(m["F-05"]["goals"], ["SG-02", "SG-06"])

  def test_every_situation_drawn(self):
    svg = (hf.OUT_DIR / hv.SIT_NAME).read_text(encoding="utf-8")
    for s in hm.SITUATIONS:
      self.assertIn(f">{s[0]}<", svg)
    for w in hm.WEATHER:
      self.assertIn(f">{w[0]}<", svg)


if __name__ == "__main__":
  unittest.main()
