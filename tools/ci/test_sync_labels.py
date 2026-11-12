#!/usr/bin/env python3
"""Tests for sync_labels.py: the committed file is valid, malformed files fail, and the plan only adds or updates."""

from __future__ import annotations

import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_labels as s  # noqa: E402

GOOD = '- name: sr-a\n  color: B60205\n  description: "a"\n'


class SyncLabels(unittest.TestCase):
  def test_committed_file_is_valid_and_has_the_change_classes(self):
    labels = s.parse(s.LABELS.read_text(encoding="utf-8"))
    s.validate(labels)
    self.assertTrue(set(s.REQUIRED) <= {lb["name"] for lb in labels})

  def test_malformed_entries_fail(self):
    bad = [GOOD.replace("color", "colour"), GOOD.replace("B60205", "B6020"),
           GOOD.replace('"a"', '"' + "x" * 101 + '"'), GOOD + GOOD, "  color: B60205\n",
           GOOD.replace("- name", "- color")]
    for text in bad:
      with self.subTest(text=text), self.assertRaises(s.LabelError):
        s.validate(s.parse(text))

  def test_missing_change_class_fails(self):
    with self.assertRaises(s.LabelError) as e:
      s.validate(s.parse(GOOD))
    self.assertIn("sr-q", str(e.exception))

  def test_plan_creates_missing_updates_different_and_leaves_the_rest(self):
    wanted = [{"name": "sr-a", "color": "B60205", "description": "a"},
              {"name": "sr-t", "color": "FBCA04", "description": "t"},
              {"name": "nsr", "color": "C5DEF5", "description": "n"}]
    existing = {"sr-t": {"name": "sr-t", "color": "ededed", "description": ""},
                "nsr": {"name": "NSR", "color": "c5def5", "description": "n"},
                "car": {"name": "car", "color": "000000", "description": ""}}
    self.assertEqual([(a, lb["name"]) for a, lb in s.plan(wanted, existing)], [("create", "sr-a"), ("update", "sr-t")])

  def test_apply_posts_new_labels_and_patches_changed_ones(self):
    calls = []

    def fake(method, url, token, body=None):
      calls.append((method, url.split("/repos/")[1], body))
      if method == "GET":
        return [{"name": "SR-T", "color": "ededed", "description": ""}], ""
      return {}, ""

    wanted = [{"name": "sr-a", "color": "B60205", "description": "a"},
              {"name": "sr-t", "color": "FBCA04", "description": "t"}]
    env = {"GITHUB_TOKEN": "x", "GITHUB_REPOSITORY": "o/r"}
    with unittest.mock.patch.object(s, "_call", fake), unittest.mock.patch.dict(s.os.environ, env):
      self.assertEqual(s.apply(wanted), 0)
    self.assertEqual(calls, [
      ("GET", "o/r/labels?per_page=100", None),
      ("POST", "o/r/labels", {"name": "sr-a", "color": "B60205", "description": "a"}),
      ("PATCH", "o/r/labels/SR-T", {"color": "FBCA04", "description": "t"})])


if __name__ == "__main__":
  unittest.main()
