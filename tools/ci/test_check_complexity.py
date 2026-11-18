#!/usr/bin/env python3
"""Tests for check_complexity.py (WP-P-07 TL-63): each failure rule on synthetic lizard output, no lizard needed."""
from __future__ import annotations

import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_complexity as cc  # noqa: E402

LIMITS = {"nloc": 60, "ccn": 15}
CSV = (
  '10,3,50,1,12,"small@1-12@a.h","a.h","small","small( int x)",1,12\n'
  '90,20,500,1,110,"big@20-130@a.h","a.h","big","big( int x)",20,130\n'
)


def fn(name: str, nloc: int, ccn: int, file: str = "a.h") -> cc.Function:
  return cc.Function(file=file, name=name, nloc=nloc, ccn=ccn, start=1)


def exc(name: str, nloc: int, ccn: int, file: str = "a.h") -> dict:
  return {"file": file, "function": name, "nloc": nloc, "ccn": ccn, "reason": "to justify"}


class TestCompare(unittest.TestCase):
  def test_parse_csv(self):
    rows = cc.parse_csv(CSV)
    self.assertEqual([(f.name, f.nloc, f.ccn, f.start) for f in rows], [("small", 10, 3, 1), ("big", 90, 20, 20)])

  def test_listed_exception_passes(self):
    errors, _ = cc.compare([fn("small", 10, 3), fn("big", 90, 20)], LIMITS, [exc("big", 90, 20)])
    self.assertEqual(errors, [])

  def test_new_violation_fails(self):
    for nloc, ccn in ((61, 1), (1, 16)):
      errors, _ = cc.compare([fn("new", nloc, ccn)], LIMITS, [])
      self.assertEqual(len(errors), 1)
      self.assertIn("not in the exception list", errors[0])

  def test_at_the_limit_passes(self):
    errors, _ = cc.compare([fn("edge", 60, 15)], LIMITS, [])
    self.assertEqual(errors, [])

  def test_grown_exception_fails(self):
    for nloc, ccn in ((91, 20), (90, 21)):
      errors, _ = cc.compare([fn("big", nloc, ccn)], LIMITS, [exc("big", 90, 20)])
      self.assertEqual(len(errors), 1)
      self.assertIn("grew past its exception", errors[0])

  def test_shrunk_exception_notes(self):
    errors, notes = cc.compare([fn("big", 80, 20)], LIMITS, [exc("big", 90, 20)])
    self.assertEqual(errors, [])
    self.assertEqual(len(notes), 1)

  def test_stale_exceptions_fail(self):
    errors, _ = cc.compare([fn("big", 50, 10)], LIMITS, [exc("big", 90, 20)])
    self.assertIn("within the limits now", errors[0])
    errors, _ = cc.compare([], LIMITS, [exc("gone", 90, 20)])
    self.assertIn("not found", errors[0])

  def test_exception_is_per_file(self):
    errors, _ = cc.compare([fn("big", 90, 20, file="b.h")], LIMITS, [exc("big", 90, 20, file="a.h")])
    self.assertEqual(len(errors), 2)  # unlisted in b.h, and the a.h entry is stale

  def test_duplicate_entry_fails(self):
    errors, _ = cc.compare([fn("big", 90, 20)], LIMITS, [exc("big", 90, 20), exc("big", 90, 20)])
    self.assertIn("listed twice", errors[0])

  def test_scope_entry_without_files_fails(self):
    with tempfile.TemporaryDirectory() as d:
      (Path(d) / "x.h").write_text("")
      files, errors = cc.scope_files(Path(d), ["x.h", "missing/*.h"])
    self.assertEqual(files, ["x.h"])
    self.assertEqual(len(errors), 1)


class TestCommittedList(unittest.TestCase):
  def test_entries_are_complete(self):
    config = tomllib.loads(cc.CONFIG.read_text())
    self.assertEqual(config["limits"], LIMITS)
    for e in config["exceptions"]:
      self.assertTrue({"file", "function", "unit", "nloc", "ccn", "structure", "reason"} <= e.keys(), e)
      self.assertTrue(e["nloc"] > LIMITS["nloc"] or e["ccn"] > LIMITS["ccn"], e)
      self.assertTrue(e["reason"].strip(), e)

  def test_pinned_version_matches_requirements(self):
    config = tomllib.loads(cc.CONFIG.read_text())
    reqs = (cc.REPO / "tools/ci/lizard-requirements.txt").read_text()
    self.assertIn(f"lizard=={config['lizard_version']} ", reqs)


if __name__ == "__main__":
  unittest.main()
