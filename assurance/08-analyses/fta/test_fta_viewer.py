#!/usr/bin/env python3
"""Tests for fta_viewer.py: the page's highlights agree with the sheets, and the page is self-contained."""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fta_diagrams as fd
import fta_viewer as fv


def walk(node):
  yield node
  for c in node.children:
    yield from walk(c)


def occurrences(o):
  yield o
  for c in o.get("c", []):
    yield from occurrences(c)


class TestViewerData(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.data = fv.build_data()
    cls.trees = fd.parse_document(fd.SOURCE.read_text(encoding="utf-8"))
    fd.resolve(cls.trees)
    cls.trees.sort(key=lambda t: t.goal)

  def test_every_goal_present(self):
    self.assertEqual([g["goal"] for g in self.data["goals"]], [t.goal for t in self.trees])

  def test_record_paths_equal_the_sheets(self):
    for t, g in zip(self.trees, self.data["goals"], strict=True):
      hot = fd.single_point_nodes(t)
      with self.subTest(goal=t.goal):
        self.assertEqual(fv.hot_idents(g["root"], fv.RECORD), {n.ident for n in walk(t.root) if id(n) in hot})

  def test_latents_mode_only_adds_paths(self):
    for g in self.data["goals"]:
      with self.subTest(goal=g["goal"]):
        self.assertLessEqual(fv.hot_idents(g["root"], fv.RECORD), fv.hot_idents(g["root"], fv.LATENTS))
    for k, n in self.data["nodes"].items():
      if "min" in n:
        self.assertLessEqual(n["min"][1], n["min"][0], k)

  def test_transfers_open_in_place(self):
    for g in self.data["goals"]:
      for o in occurrences(g["root"]):
        n = self.data["nodes"][o["k"]]
        if "gate" in n:
          self.assertTrue(o.get("c"), f"{g['goal']}: {o['k']} drawn without its inputs")

  def test_cut_set_counts_from_the_solver(self):
    te02 = self.data["nodes"]["TE-02"]
    self.assertEqual(te02["gate"], "OR")
    self.assertGreater(te02["cs"], 0)
    self.assertTrue(all(n["cs"] >= 1 for n in self.data["nodes"].values() if "gate" in n))


class TestPage(unittest.TestCase):
  def test_data_round_trips(self):
    data = fv.build_data()
    page = fv.render(data)
    m = re.search(r"const DATA = (.*?);</script>", page, re.S)
    self.assertIsNotNone(m)
    self.assertEqual(json.loads(m.group(1).replace("<\\/", "</")), data)

  def test_self_contained(self):
    page = fv.TEMPLATE.read_text(encoding="utf-8")
    self.assertNotRegex(page, r"(src|href)\s*=\s*[\"']?https?:")
    self.assertNotIn("@import", page)

  def test_bad_template_rejected(self):
    original = fv.TEMPLATE
    try:
      fv.TEMPLATE = Path(__file__)
      with self.assertRaises(fd.FtaError):
        fv.render({"goals": [], "nodes": {}})
    finally:
      fv.TEMPLATE = original


if __name__ == "__main__":
  unittest.main()
