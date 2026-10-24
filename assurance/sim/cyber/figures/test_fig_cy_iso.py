#!/usr/bin/env python3
"""Tests for fig_cy_iso.py: TS-14 path facts read from WP-C-09 and WP-S-07, barriers as built, figure house rules."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_cy_iso as fi


class TestIsoFigure(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.S = fi.load()
    cls.svg = fi.build(cls.S)[fi.NAME]

  def test_risks_come_from_wp_c09(self):
    self.assertEqual(self.S.risk["TS-14"], self.S.tara.risk["TS-14"]["risk"])
    for ts in fi.PRECURSORS:
      self.assertIn(f"risk {self.S.risk[ts]}", self.svg)
    self.assertIn(f"TS-14 · risk {self.S.risk['TS-14']}", self.svg)
    self.assertEqual(self.S.goal, ("DS-01", "H-01"))

  def test_gates_are_drawn_as_built(self):
    for ids, state in zip(fi.GATES, self.S.walls):
      self.assertEqual(state, fi.barrier([self.S.csr[c] for c in ids]))
      self.assertIn(" · ".join(ids), self.svg)
    self.assertNotIn('class="w-done"', self.svg, "no requirement on this path is verified yet")

  def test_status_reading(self):
    self.assertEqual(fi.csr_state("Partial: 8-bit checksums on some messages (GAP-01)"), "partial")
    self.assertEqual(fi.csr_state("Implemented in part: allow-list. 2026-10-12: PCS IDs removed; not verified on hardware"), "partial")
    self.assertEqual(fi.csr_state("Partly met by design (limits are compile-time constants)"), "partial")
    self.assertEqual(fi.csr_state("Not implemented (GAP-20)"), "open")
    self.assertEqual(fi.csr_state("Not implemented. **2026-10-12: Implemented, not verified (reference build)**"), "unverified")
    self.assertEqual(fi.csr_state("Mechanism exists (`updated.py:416`); procedure in [WP-O-02](x.md)"), "unverified")
    with self.assertRaises(fi.ParseError):
      fi.csr_state("Something else entirely")

  def test_barrier_convention(self):
    self.assertEqual(fi.barrier(["open", "open"]), "open")
    self.assertEqual(fi.barrier(["done", "done"]), "done")
    self.assertEqual(fi.barrier(["partial", "done"]), "partial")
    self.assertEqual(fi.barrier(["unverified", "done"]), "unverified")

  def test_house_rules(self):
    self.assertIn('width="640"', self.svg)
    self.assertRegex(self.svg, r'<title id="t">[^<]+</title>')
    self.assertRegex(self.svg, r'<desc id="d">[^<]{80,}</desc>')
    self.assertIn("prefers-color-scheme: dark", self.svg)
    sizes = [float(s) for s in re.findall(r'font-size="([\d.]+)"', self.svg)]
    self.assertTrue(sizes and all(13 <= s <= 16 for s in sizes), sorted(set(sizes)))
    durs = [int(d) for d in re.findall(r'dur="(\d+)s"', self.svg)]
    self.assertTrue(durs and max(durs) <= 5, "a loop over 5 s needs a still alternative")
    self.assertIn("Synthetic (DSR-12)", self.svg)

  def test_deterministic_and_committed(self):
    self.assertEqual(self.svg, fi.build(self.S)[fi.NAME])
    self.assertEqual((fi.HERE / fi.NAME).read_text(encoding="utf-8"), self.svg, "stale: run fig_cy_iso.py")

  def test_no_exploitation_detail(self):
    self.assertNotRegex(self.svg, r"0x[0-9a-fA-F]{2,}", "no CAN IDs or other code-level detail in the figure")


if __name__ == "__main__":
  unittest.main()
