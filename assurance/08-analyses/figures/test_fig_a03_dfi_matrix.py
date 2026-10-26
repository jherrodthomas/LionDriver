#!/usr/bin/env python3
"""Tests for fig_a03_dfi_matrix.py: parse WP-A-03 §4/§5, committed SVG current, parser rejects bad rows."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_a03_dfi_matrix as fm


class TestRealDocument(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.dfis, cls.claims, cls.sections = fm.parse(fm.SOURCE.read_text(encoding="utf-8"))

  def test_all_initiators_and_claims(self):
    self.assertEqual(sorted(d.ident for d in self.dfis), [f"DFI-{i:02d}" for i in range(1, 37)])
    self.assertEqual([c.ident for c in self.claims], [f"IC-{i:02d}" for i in range(1, 8)])
    self.assertEqual(sorted(self.sections), [f"4.{i}" for i in range(1, 10)])

  def test_ratings_are_known(self):
    for d in self.dfis:
      self.assertIn(d.base, ("N", "P", "C"), d.ident)
      self.assertIn(d.ref, (None, "N", "P", "C"), d.ident)

  def test_reference_build_changes_parsed(self):
    changed = {d.ident: (d.base, d.ref) for d in self.dfis if d.ref}
    self.assertEqual(changed, {"DFI-09": ("N", "P"), "DFI-13": ("N", "P")})

  def test_committed_output_current(self):
    path = fm.HERE / fm.OUTPUT
    self.assertTrue(path.exists())
    self.assertEqual(path.read_text(encoding="utf-8"), fm.build(), "stale; run fig_a03_dfi_matrix.py")

  def test_svg_parses_and_has_title(self):
    root = ET.fromstring(fm.build())
    self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))


class TestParser(unittest.TestCase):
  def test_dfi_list_shorthand_and_parentheses(self):
    self.assertEqual(fm.dfi_list("DFI-03, -08 (2026-10-12: DFI-09 moves)"), ["DFI-03", "DFI-08"])
    self.assertEqual(fm.dfi_list("DFI-01, -05 plus WP-A-02 FFI-CM-05/08"), ["DFI-01", "DFI-05"])
    self.assertEqual(fm.dfi_list("—"), [])

  def test_eval_without_rating_rejected(self):
    with self.assertRaises(fm.ParseError):
      fm.parse_eval("controlled")

  def test_unknown_dfi_in_s5_rejected(self):
    md = """### 4.1 Shared
| ID | Initiator | Coupling | Elements reached | Effect | Existing | Eval | Required |
|---|---|---|---|---|---|---|---|
| DFI-01 | **Power**: x | y | E-01 (IC-01) | z | w | **P** | m |

## 5. Evaluation per independence claim

| Claim | Not controlled DFIs | Partly controlled DFIs | Verdict | Condition |
|---|---|---|---|---|
| IC-01 envelope vs SoC | DFI-02 | DFI-01 | **Not independent** | c |
"""
    with self.assertRaises(fm.ParseError):
      fm.parse(md)


if __name__ == "__main__":
  unittest.main()
