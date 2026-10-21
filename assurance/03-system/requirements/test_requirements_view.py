#!/usr/bin/env python3
"""Tests for requirements_view.py: outputs current, every requirement and link drawn, coverage gaps reported."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import requirements_view as rv


class TestRequirementsView(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.fs, cls.ts, cls.goals = rv.load()
    cls.kids = rv.children(cls.fs, cls.ts)
    cls.out = rv.build()

  def test_outputs_current(self):
    for name, content in self.out.items():
      self.assertEqual((rv.HERE / name).read_text(encoding="utf-8"), content, f"{name} stale; run requirements_view.py")

  def test_svgs_parse_and_have_title(self):
    for name, content in self.out.items():
      if name.endswith(".svg"):
        root = ET.fromstring(content)
        self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"), name)

  def test_one_tree_per_goal(self):
    self.assertEqual(sorted(n for n in self.out if "-tree.svg" in n),
                     sorted(f"figures/fig-req-1-{g.lower()}-tree.svg" for g in self.goals))

  def test_every_fsr_in_a_tree_and_every_link_drawn(self):
    for f in self.fs:
      trees = [self.out[f"figures/fig-req-1-{g.lower()}-tree.svg"] for g in f["parents"] if g in self.goals]
      self.assertTrue(trees, f["id"])
      for tree in trees:
        self.assertIn(f">{f['id']}<", tree)
        for t in self.kids[f["id"]]:
          self.assertIn(f">{t['id']}<", tree)

  def test_matrix_has_every_fsr(self):
    for f in self.fs:
      self.assertIn(f">{f['id']}<", self.out["figures/fig-req-2-matrix.svg"])

  def test_lists_have_every_requirement(self):
    for f in self.fs:
      self.assertIn(f"[{f['id']}]", self.out["fsr-list.md"])
    for t in self.ts:
      self.assertIn(f"[{t['id']}]", self.out["tsr-list.md"])

  def test_gap_reported(self):
    fs = [dict(f) for f in self.fs] + [{"id": "FSR-09.99", "parents": ["SG-08"], "text": "x", "asil": "A",
                                        "verification": "T", "baseline_impl": "Not"}]
    kids = rv.children(fs, self.ts)
    self.assertIn("FSRs without a TSR: FSR-09.99.", rv.readme(fs, self.ts, self.goals, kids))

  def test_slug(self):
    self.assertEqual(rv.slug("3. TSR-1xx Lateral actuation envelope (SG-01, SG-02)"),
                     "3-tsr-1xx-lateral-actuation-envelope-sg-01-sg-02")

  def test_asil_short(self):
    self.assertEqual(rv.asil("A (SG-08; allocated to the QM SoC)"), "A")
    self.assertEqual(rv.asil("— (ext.)"), "ext")
    self.assertEqual(rv.asil("B‡"), "B‡")


if __name__ == "__main__":
  unittest.main()
