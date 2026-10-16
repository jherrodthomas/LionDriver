#!/usr/bin/env python3
"""Tests for fta_diagrams.py: parse WP-A-04, resolve references, reject malformed trees."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fta_cutsets as fc
import fta_diagrams as fd


def parse(md: str):
  trees = fd.parse_document(md)
  fd.resolve(trees)
  return trees


def walk(node):
  yield node
  for c in node.children:
    yield from walk(c)


TREE = """## 2. FTA — SG-01: test goal

```
TE-01 Top                                                   [OR]
├── G1.1 Both                                               [AND]
│   ├── BE-1.01 First event
│   │          continued text                               (SPF, systematic)
│   └── UE-1.02 Outside the item
└── BE-1.03 Other [CCF → DFI-10]
```
"""


class TestRealDocument(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.trees = parse(fd.SOURCE.read_text(encoding="utf-8"))

  def test_all_goals_present(self):
    self.assertEqual(sorted(t.goal for t in self.trees), [f"SG-0{i}" for i in range(1, 8)])

  def test_gates_have_two_inputs_and_leaves_are_events(self):
    for t in self.trees:
      for n in walk(t.root):
        if n.children:
          self.assertIn(n.gate, ("OR", "AND"), n.ident)
          self.assertGreaterEqual(len(n.children), 2, n.ident)
        else:
          self.assertIn(n.kind, ("basic", "undeveloped", "transfer_in"), n.ident)

  def test_each_event_defined_once(self):
    seen = set()
    for t in self.trees:
      for n in walk(t.root):
        if n.ref_of is None and n.ident:
          self.assertNotIn(n.ident, seen)
          seen.add(n.ident)

  def test_cross_tree_gate_reference_is_a_transfer(self):
    sg03 = next(t for t in self.trees if t.goal == "SG-03")
    genv = [n for n in walk(sg03.root) if n.ident == "G-ENV"]
    self.assertEqual(len(genv), 1)
    self.assertEqual(genv[0].kind, "transfer_in")
    self.assertEqual(genv[0].ref_tree, "SG-01")

  def test_goal_asils_from_wp_c03(self):
    # SG-08 (HARA v0.4) has no fault tree yet; the ASILs are read for every goal of WP-C-03.
    self.assertEqual(sorted(fd.goal_asils()), [f"SG-0{i}" for i in range(1, 9)])

  def test_committed_outputs_current(self):
    outputs = fd.build()
    for name, content in outputs.items():
      self.assertEqual((fd.HERE / name).read_text(encoding="utf-8"), content, name)


class TestParser(unittest.TestCase):
  def test_continuation_and_tags(self):
    (t,) = parse(TREE)
    be = t.root.children[0].children[0]
    self.assertEqual(be.ident, "BE-1.01")
    self.assertEqual(be.text, "First event continued text")
    self.assertIn(("spf", "SPF, systematic"), be.badges)
    self.assertEqual(t.root.children[0].children[1].kind, "undeveloped")
    self.assertIn(("ccf", "CCF DFI-10"), t.root.children[1].badges)

  def test_multi_reference_under_and_becomes_or(self):
    md = TREE.replace("└── BE-1.03 Other [CCF → DFI-10]",
                      "└── G1.2 Again                                 [AND]\n" +
                      "    ├── BE-1.01 / UE-1.02\n" +
                      "    └── BE-1.03 New")
    (t,) = parse(md)
    g12 = t.root.children[1]
    self.assertEqual(g12.children[0].kind, "implicit_or")
    self.assertEqual([c.ident for c in g12.children[0].children], ["BE-1.01", "UE-1.02"])
    self.assertTrue(all(c.ref_of is not None for c in g12.children[0].children))

  def test_undefined_reference_rejected(self):
    md = TREE.replace("BE-1.03 Other [CCF → DFI-10]", "BE-1.08, BE-1.09 (as SG-01)")
    with self.assertRaises(fd.FtaError):
      parse(md)

  def test_gate_without_tag_rejected(self):
    with self.assertRaises(fd.FtaError):
      parse(TREE.replace("Both                                               [AND]", "Both"))

  def test_pagination_respects_limit(self):
    trees = parse(fd.SOURCE.read_text(encoding="utf-8"))
    for t in trees:
      for root in fd.paginate(t):
        self.assertLessEqual(fd.leaves(root), fd.MAX_LEAVES_PER_SHEET, f"{t.goal} {root.ident}")


CS_DOC = """## 2. FTA — SG-01: test goal

```
TE-01 Top                                                   [OR]
├── G1.1 Both                                               [AND]
│   ├── G1.1.1 Either                                       [OR]
│   │   ├── BE-1.01 First
│   │   └── BE-1.02 Second
│   └── UE-1.03 Outside the item
├── G1.2 Pair                                               [AND]
│   ├── BE-1.04 Cause
│   └── BE-1.05 Always so at the baseline (latent, baseline)
└── BE-1.06 Single
```

### 2.1 SG-01 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-01.1 | 1 + ext. | {BE-1.01 or BE-1.02, UE-1.03} | exact |
| MCS-01.2 | 1 (effective) | {BE-1.04} | latent omitted |
| MCS-01.3 | 1 | {BE-1.01} | omits the UE |
| MCS-01.4 | 2 | {BE-1.06, BE-1.04} | not minimal |
| MCS-01.5 | 1 | {BE-1.09} | not in the tree |
| MCS-01.6 | 1 | {whatever in words} | prose |

## 3. Next
"""


class TestCutSets(unittest.TestCase):
  def setUp(self):
    self.trees = fd.parse_document(CS_DOC)
    fd.resolve(self.trees)
    self.solver = fc.Solver(self.trees)
    self.solver.finish()
    self.computed = self.solver.cut_sets(self.trees[0].root)

  def test_boolean_reduction(self):
    self.assertEqual(set(self.computed), {
      frozenset({"BE-1.06"}), frozenset({"BE-1.04", "BE-1.05"}),
      frozenset({"BE-1.01", "UE-1.03"}), frozenset({"BE-1.02", "UE-1.03"})})

  def test_absorption(self):
    self.assertEqual(fc.minimise([frozenset("ab"), frozenset("a"), frozenset("abc")]), [frozenset("a")])

  def test_row_classification(self):
    rows = fc.parse_tables(CS_DOC, self.solver)["SG-01"]
    events = {e for c in self.computed for e in c}
    for r in rows:
      fc.classify(r, self.computed, self.solver, events)
    self.assertEqual([r.status for r in rows],
                     ["match", "effective", "reduced", "not minimal", "outside tree", "in words"])

  def test_real_document_parses_and_report_current(self):
    self.assertEqual(fc.OUTPUT.read_text(encoding="utf-8"), fc.build())

  def test_single_point_path(self):
    t = self.trees[0]
    hot = fd.single_point_nodes(t)
    drawn = {n.ident for n in walk(t.root) if id(n) in hot}
    self.assertEqual(drawn, {"TE-01", "G1.1", "G1.1.1", "BE-1.01", "BE-1.02", "BE-1.06"})

  def test_single_point_paths_match_cut_sets(self):
    trees = fd.parse_document(fd.SOURCE.read_text(encoding="utf-8"))
    fd.resolve(trees)
    solver = fc.Solver(trees)
    for t in trees:
      hot = fd.single_point_nodes(t)
      drawn = {n.ident for n in walk(t.root) if id(n) in hot and n.ident.startswith("BE-") and not n.children}
      order_one = {e for c in solver.cut_sets(t.root) if sum(e.startswith("BE-") for e in c) == 1
                   for e in c if e.startswith("BE-")}
      self.assertEqual(drawn, order_one, t.goal)

  def test_transfer_expanded(self):
    trees = fd.parse_document(fd.SOURCE.read_text(encoding="utf-8"))
    fd.resolve(trees)
    solver = fc.Solver(trees)
    sg03 = next(t for t in trees if t.goal == "SG-03")
    sets = solver.cut_sets(sg03.root)
    self.assertIn(frozenset({"BE-1.06", "BE-3.02", "UE-3.05"}), sets)


if __name__ == "__main__":
  unittest.main()
