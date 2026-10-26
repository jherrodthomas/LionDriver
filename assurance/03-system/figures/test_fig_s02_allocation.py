#!/usr/bin/env python3
"""Tests for fig_s02_allocation.py: committed SVG current, every TSR drawn in each column it is allocated to."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_s02_allocation as fa


class TestAllocation(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.ts = fa.load()
    cls.by = {t["id"]: t for t in cls.ts}

  def test_committed_output_current(self):
    for name, content in fa.build().items():
      self.assertEqual((fa.HERE / name).read_text(encoding="utf-8"), content, f"{name} is stale; run fig_s02_allocation.py")

  def test_every_tsr_once_per_column(self):
    svg = (fa.HERE / fa.OUT).read_text(encoding="utf-8")
    self.assertEqual(len(self.ts), 128)
    for t in self.ts:
      label = f"{t['num']}{'+' if len(t['cols']) > 1 else ''} {t['asil']}"
      self.assertEqual(svg.count(f">{label}<"), len(t["cols"]), t["id"])

  def test_asil_classes(self):
    self.assertEqual(fa.asil_class("B‡"), "B‡")
    self.assertEqual(fa.asil_class("QM (C-sup: TSR-516)"), "QM*")
    self.assertEqual(fa.asil_class("QM"), "QM")
    self.assertEqual(fa.asil_class("ext"), "ext")
    self.assertEqual(fa.asil_class("(a) C; (b) QM (C-sup)"), "C")
    self.assertEqual(fa.asil_class("A (SG-08; allocated to the QM SoC, open: WP-C-04 OI-11)"), "A")

  def test_allocation_and_status(self):
    self.assertEqual(self.by["TSR-109"]["cols"], ["P-SW", "EXT"])
    self.assertEqual(self.by["TSR-501"]["status"], "implemented")
    self.assertEqual(self.by["TSR-111"]["status"], "assumed")


if __name__ == "__main__":
  unittest.main()
