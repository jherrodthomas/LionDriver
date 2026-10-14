#!/usr/bin/env python3
"""Tests for trace_figures.py: the committed figures are current, and the numbers they show match the data."""
from __future__ import annotations

import re
import sys
import unittest
import xml.dom.minidom
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_figures as tf


class Figures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.d = tf.load()
    cls.out = tf.render_all()

  def test_committed_figures_are_current(self):
    for p, t in self.out.items():
      self.assertTrue(p.exists(), f"{p.name} missing; run trace_figures.py")
      self.assertEqual(p.read_text(encoding="utf-8"), t, f"{p.name} stale; run trace_figures.py")

  def test_deterministic(self):
    self.assertEqual(self.out, tf.render_all())

  def test_valid_svg_with_title_and_desc(self):
    for p, t in self.out.items():
      doc = xml.dom.minidom.parseString(t)
      self.assertEqual(doc.documentElement.getAttribute("role"), "img", p.name)
      self.assertTrue(doc.getElementsByTagName("title") and doc.getElementsByTagName("desc"), p.name)

  def test_every_kind_counted(self):
    fig2 = self.out[tf.FIG_DIR / "fig-2-trace-data-model.svg"]
    for k in tf.F2_POS:
      self.assertIn(f">{k}  {tf.count(self.d, k)}<", fig2, k)

  def test_goal_reach_includes_every_derived_fsr(self):
    for g in tf.goals(self.d):
      fsrs = {i for i in tf.descendants(self.d, g) if self.d.kind[i] == "FSR"}
      direct = {i for i in self.d.m.ids["FSR"] if g in (self.d.m.items[i].get("parents") or [])}
      self.assertEqual(fsrs, direct, g)

  def test_named_is_never_shown_as_verified(self):
    fig4 = self.out[tf.FIG_DIR / "fig-4-trace-depth-per-goal.svg"]
    self.assertIn("not a passed test", fig4)
    self.assertNotIn(tf.GREEN_BG, fig4.split("NAMED BY A", 1)[1].split("TAGGED", 1)[0])

  def test_check_board_matches_readme(self):
    fig7 = self.out[tf.FIG_DIR / "fig-7-consistency-checks.svg"]
    for c, _, _ in self.d.checks:
      self.assertIn(f">{c}<", fig7, c)
    self.assertEqual({c for c, _, _ in self.d.checks}, {c for _, ids in tf.CHECK_GROUPS for c in ids})

  def test_allocation_matches_sysml_report(self):
    report = (tf.ASSURANCE_DIR / "models" / "sysml" / "generated" / "allocation-resolution.md").read_text(encoding="utf-8")
    m = re.search(r"\| \*\*all\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|", report)
    resolved = sum(1 for s in self.d.alloc.values() if s == "resolved")
    self.assertEqual((int(m[1]), int(m[2])), (len(self.d.alloc), resolved))

  def test_readme_counts_match_the_data(self):
    readme = tf.README.read_text(encoding="utf-8")
    m = re.search(r"`trace: (\d+) files, (\d+) items ([^`]+)`", readme)
    self.assertIsNotNone(m, "README §2 result line missing")
    self.assertEqual(int(m[2]), len(self.d.m.items))
    aous = sorted(self.d.m.ids["AOU"])
    self.assertIn(f"{aous[0]}…{aous[-1]}", readme)

  def test_readme_embeds_every_figure(self):
    readme = tf.README.read_text(encoding="utf-8")
    for n, name in enumerate(tf.FIGURES, start=1):
      self.assertIn(f"(figures/{name})", readme, name)
      self.assertIn(f"*Figure {n}.*", readme, name)

  def test_system_v_figures_come_from_vmodel(self):
    self.assertIs(tf.FIGURES["fig-9-system-v-status.svg"], tf.fig9)
    self.assertIs(tf.FIGURES["fig-10-v-per-goal.svg"], tf.fig10)
    vd = tf.vmodel.load(self.d.m)
    fig9 = self.out[tf.FIG_DIR / "fig-9-system-v-status.svg"]
    self.assertIn("".join(tf.vmodel.draw("status", "full", model=vd).body), fig9)
    fig10 = self.out[tf.FIG_DIR / "fig-10-v-per-goal.svg"]
    for g in tf.goals(self.d):
      self.assertIn(f">{g}</text>", fig10, g)

  def test_system_v_figures_show_nothing_green_unless_earned(self):
    vd = tf.vmodel.load(self.d.m)
    earned = any(st in ("A", "B") for st, _ in vd.register.values()) or "passed" in vd.gate_status.values()
    if not earned:
      for name in ("fig-9-system-v-status.svg", "fig-10-v-per-goal.svg"):
        self.assertNotIn(tf.vmodel.GREEN, self.out[tf.FIG_DIR / name], name)


if __name__ == "__main__":
  unittest.main()
