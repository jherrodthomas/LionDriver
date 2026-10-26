#!/usr/bin/env python3
"""Unit tests of check_clauses.py (clause-check register, assurance/trace/clauses/README.md)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_clauses as cc  # noqa: E402

KEYS = dict(subclause=None, source_verified_by=None, source_verified_date=None)


def reg(*obligations):
  return {"standard": "ISO 26262-3:2018", "obligations": [dict(KEYS, **o) for o in obligations]}


def ob(oid="O3-5.01", clause="5", wp="WP-C-01", checks=("section:Item boundary",)):
  return {"id": oid, "clause": clause, "topic": "t", "obligation": "Something holds.", "work_product": wp,
          "checks": list(checks)}


ITEMS = [{"id": "SG-01", "kind": "safety-goal", "safe_state": "stop", "ftti_text": "1 s"},
         {"id": "SG-02", "kind": "safety-goal", "safe_state": "", "ftti_text": "1 s"}]
STATES = {"R1": "yes", "K2": "partly", "K5": "no"}


class TestEvaluate(unittest.TestCase):
  def run_one(self, o, terrors=None):
    rows, problems = cc.evaluate(reg(o), STATES, terrors or {}, ITEMS)
    return (rows[0][1] if rows else None), problems

  def test_statuses(self):
    self.assertEqual(self.run_one(ob(checks=["trace:R1", "section:Item boundary"])), ("pass", []))
    self.assertEqual(self.run_one(ob(checks=["trace:K2"])), ("partial", []))
    self.assertEqual(self.run_one(ob(checks=["trace:K5", "section:Interfaces"])), ("gap", []))
    self.assertEqual(self.run_one(ob(checks=["manual:a review"])), ("manual", []))
    self.assertEqual(self.run_one(ob(checks=["trace:R1", "manual:a review"])), ("manual", []))
    self.assertEqual(self.run_one(ob(checks=["trace:R1"]), {"R1": ["[R1] HE-01.1 wrong"]}), ("open", []))

  def test_items_check_finds_empty_fields(self):
    status, problems = self.run_one(ob(checks=["items:safety-goal:safe_state,ftti_text"]))
    self.assertEqual((status, problems), ("open", []))
    rows, _ = cc.evaluate(reg(ob(checks=["items:safety-goal:ftti_text"])), STATES, {}, ITEMS)
    self.assertEqual(rows[0][1], "pass")

  def test_broken_register_is_reported(self):
    for bad in (ob(checks=["trace:Z9"]), ob(checks=["section:No such heading anywhere"]),
                ob(checks=["items:safety-goal:not_a_field"]), ob(checks=["items:no-kind:text"]),
                ob(checks=["weird:x"]), ob(wp="WP-Z-99"), ob(oid="O3-6.01"), ob(oid="bad"), ob(checks=[])):
      _, problems = self.run_one(bad)
      self.assertTrue(problems, bad)
    rows, problems = cc.evaluate(reg(ob(), ob()), STATES, {}, ITEMS)
    self.assertTrue(any("duplicated" in p for p in problems))
    rows, problems = cc.evaluate({"standard": "ISO 26262-3:2018", "obligations": [{"id": "O3-5.01"}]},
                                 STATES, {}, ITEMS)
    self.assertTrue(any("missing keys" in p for p in problems))


class TestSources(unittest.TestCase):
  def test_trace_states_reads_the_implemented_column(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "README.md"
      p.write_text("| Check | Description | Source | Implemented |\n|---|---|---|---|\n"
                   "| K1 | a | b | Yes (x) |\n| K2 | a | b | Partly: y |\n| R1 **[ext]** | a | b | Yes |\n"
                   "| K5 | a | b | No |\n\nafter\n| K9 | a | b | Yes |\n")
      self.assertEqual(cc.trace_states(p), {"K1": "yes", "K2": "partly", "R1": "yes", "K5": "no"})

  def test_sections_count_content_down_to_the_next_peer_heading(self):
    with tempfile.TemporaryDirectory() as d:
      p = Path(d) / "x.md"
      p.write_text("# T\n## 1. A\n### 1.1 B\ntext\n## 2. C\n## 3. D\nmore\n")
      got = {t: n for _, t, n in cc.sections(p)}
      self.assertGreater(got["1. A"], 0)        # content in its sub-section counts
      self.assertEqual(got["2. C"], 0)
      self.assertGreater(got["3. D"], 0)


class TestRegister(unittest.TestCase):
  def test_committed_registers_are_consistent(self):
    states = cc.trace_states()
    terrors, items = cc.trace_errors()
    for src in sorted(cc.CLAUSES_DIR.glob("*.yaml")):
      rows, problems = cc.evaluate(cc.yaml.safe_load(src.read_text()), states, terrors, items)
      self.assertEqual(problems, [], src.name)
      self.assertTrue(rows, src.name)
      for o, _, _ in rows:                   # nothing claims verification without saying who and when
        self.assertEqual(bool(o["source_verified_by"]), bool(o["source_verified_date"]), o["id"])


if __name__ == "__main__":
  unittest.main()
