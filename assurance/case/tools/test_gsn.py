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

  def test_outputs_current(self):
    for name, content in gd.build().items():
      self.assertEqual((gd.OUT_DIR / name).read_text(encoding="utf-8"), content, name)


if __name__ == "__main__":
  unittest.main()
