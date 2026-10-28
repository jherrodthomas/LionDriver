#!/usr/bin/env python3
"""Tests for gsn_diagrams.py: tree from the case records, contexts from WP-K-01, outputs current."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gsn_diagrams as gd
from caselib import load_case


def walk(node):
  yield node
  for c in node.children:
    yield from walk(c)


class TestGsn(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.root = gd.build_tree()

  def test_every_claim_drawn_once(self):
    claims = {r["id"] for r in load_case().of_kind("claim")}
    goals = [n.ident for n in walk(self.root) if n.kind == "goal"]
    self.assertEqual(sorted(goals), sorted(claims))

  def test_strategies_and_solutions(self):
    strategies = {r["id"] for r in load_case().of_kind("argument")}
    self.assertEqual({n.ident for n in walk(self.root) if n.kind == "strategy"}, strategies)
    g112 = next(n for n in walk(self.root) if n.ident == "G1.1.2")
    self.assertEqual([c.ident for c in g112.children], ["Sn-02", "Sn-03", "Sn-10", "Sn-12"])

  def test_undeveloped_goal(self):
    self.assertTrue(next(n for n in walk(self.root) if n.ident == "G2.4").undeveloped)
    self.assertFalse(next(n for n in walk(self.root) if n.ident == "G1.1").undeveloped)

  def test_contexts_attach_to_owner(self):
    g0 = self.root
    self.assertEqual([cid for _, cid, _ in g0.sides], ["C1", "C2", "C3", "C4", "C5", "C6", "A1", "J0"])
    g3 = next(n for n in walk(self.root) if n.ident == "G3")
    self.assertIn(("J", "J3"), [(k, c) for k, c, _ in g3.sides])

  def test_context_without_owner_rejected(self):
    with self.assertRaises(gd.GsnError):
      gd.contexts_from_safety_case("```text\n ⊙ C1   orphan\n```\n")

  def test_continuation_joined(self):
    ctx = gd.contexts_from_safety_case("```text\nG9  Goal text\n ⊙ C1   first line\n        second line\n```\n")
    self.assertEqual(ctx["G9"], [("C", "C1", "first line second line")])

  def test_one_sheet_per_sub_argument(self):
    sheets = gd.paginate(gd.build_tree())
    self.assertEqual([s.ident for s in sheets], ["G0", "G1", "G1.1", "G2", "G3", "G5"])

  def test_cyber_case_structure(self):
    root = gd.build_cyber_tree()
    nodes = {n.ident: n for n in walk(root)}
    self.assertEqual(root.ident, "CG0")
    self.assertEqual([c.ident for c in nodes["CS1"].children], ["CG1", "CG2", "CG3", "CG4", "CG5", "CG6"])
    self.assertEqual([c.ident for c in nodes["CG2.2"].children], ["CSn-10", "CSn-11", "CSn-20", "CSn-22", "CSn-31"])
    self.assertEqual(nodes["CG2.2"].defeaters, ["CDF-01", "CDF-02", "CDF-03"])
    self.assertEqual([c.ident for c in nodes["CG4.1"].children], [f"CSn-{k}" for k in range(30, 38)])
    self.assertEqual([cid for _, cid, _ in root.sides], ["CC1", "CC2", "CC3", "CA-01…CA-05"])
    self.assertIn("Requirements", [cid for _, cid, _ in nodes["CG2.1"].sides])
    self.assertEqual(nodes["CSn-04"].status, "missing")

  def test_cyber_defeater_register_must_match_trees(self):
    md = gd.CYBER_MD.read_text(encoding="utf-8").replace("        ⇐ CDF-10\n", "", 1)
    with self.assertRaises(gd.GsnError):
      gd.build_cyber_tree(md)

  def test_cyber_unknown_evidence_rejected(self):
    md = gd.CYBER_MD.read_text(encoding="utf-8").replace("→ CSn-54", "→ CSn-99", 1)
    with self.assertRaises(gd.GsnError):
      gd.build_cyber_tree(md)

  def test_outputs_current(self):
    for name, content in gd.build().items():
      self.assertEqual((gd.OUT_DIR / name).read_text(encoding="utf-8"), content, name)

  def test_every_sheet_has_a_phone_view_with_every_element(self):
    import xml.etree.ElementTree as ET
    out = gd.build()
    for prefix, case, _src, builder, _doc, _id in gd.CASES:
      sheets = gd.paginate(builder())
      for no, root in enumerate(sheets, 1):
        svg = out[f"{prefix}-{no}-{root.ident}-phone.svg"]
        el = ET.fromstring(svg)
        self.assertEqual(el.get("width"), str(gd.PHONE_W))
        self.assertIn("prefers-color-scheme: dark", svg)
        seen = []

        def visit(n, top=True):
          seen.append(n.ident)
          if not top and n.sheet_link:
            return
          for c in n.children:
            visit(c, False)
        visit(root)
        for ident in seen:
          self.assertIn(f">{ident}<", svg, f"{prefix} sheet {no}: {ident} missing from the phone view")
        for d in root.defeaters:
          self.assertIn(d, svg)


if __name__ == "__main__":
  unittest.main()
