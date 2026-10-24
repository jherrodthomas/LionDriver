#!/usr/bin/env python3
"""Tests for fig_o05_updates.py: sources found, statuses checked, gates drawn as built, still has no motion, no detail."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_o05_updates as fo


class TestUpdateFigures(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.D = fo.load()
    cls.out = fo.build(cls.D)

  def test_every_source_text_is_found(self):
    self.assertEqual(fo.problems(self.D), [])

  def test_a_changed_source_fails(self):
    D = dict(self.D, docs=dict(self.D["docs"], S07=self.D["docs"]["S07"].replace("pinned public key", "public key")))
    self.assertTrue(any("pinned public key" in p for p in fo.problems(D)))

  def test_statuses_come_from_wp_s07(self):
    self.assertEqual({r: v["status"][0] for r, v in self.D["csr"].items()}, fo.DRAWN)
    self.assertEqual(fo.csr_status("Not implemented: x (GAP-26)"), ("open", "Not implemented"))
    self.assertEqual(fo.csr_status("Partial: y. **2026-11-01: Implemented, not verified**"), ("unverified", "Implemented, not verified"))
    with self.assertRaises(fo.FigureError):
      fo.csr_status("Something else")

  def test_status_change_without_a_redraw_fails(self):
    csr = dict(self.D["csr"], **{"CSR-121": dict(self.D["csr"]["CSR-121"], status=("unverified", "Implemented, not verified"))})
    with self.assertRaisesRegex(fo.FigureError, "CSR-121 is now 'unverified'"):
      fo.build(dict(self.D, csr=csr))

  def test_csg07_still_has_no_control(self):
    self.assertEqual(self.D["csg07_barrier"], "open")
    with self.assertRaisesRegex(fo.FigureError, "CSG-07"):
      fo.build(dict(self.D, csg07_barrier="partial"))

  def test_gates_are_drawn_as_built(self):
    svg = self.out["fig-o05-6-2-update-attacks.svg"]
    self.assertEqual(svg.count('class="gate-partial"'), 1 + 1)  # the legend and CSR-125
    self.assertEqual(svg.count('class="gate-unverified"'), 1)  # the legend only
    self.assertEqual(len(re.findall(r'class="entry"', svg)), len(fo.PANELS) + 1)

  def test_phone_width_and_still_alternative(self):
    for name, s in self.out.items():
      self.assertIn('width="640"', s, name)
      self.assertIn("<title", s, name)
      self.assertIn("<desc", s, name)
      self.assertLess(len(s.encode()), 50_000, name)
    self.assertIn("<animate", self.out["fig-o05-6-3-update-states.svg"])
    self.assertNotIn("<animate", self.out["fig-o05-6-3-update-states-still.svg"])

  def test_no_exploitation_detail(self):
    for name, s in self.out.items():
      for f in fo.FORBIDDEN:
        self.assertNotIn(f, s, name)

  def test_committed_figures_are_current(self):
    for name, s in self.out.items():
      self.assertEqual((fo.HERE / name).read_text(encoding="utf-8"), s, name)


if __name__ == "__main__":
  unittest.main()
