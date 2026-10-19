#!/usr/bin/env python3
"""Tests for check_pin_records.py.

Each case builds a throwaway git repository whose submodules are bare gitlinks, so a pin can move to any commit id.

Run from the repository root:  python3 -m unittest discover -s tools/ci -p 'test_*.py' -v
Standard library only; needs git.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_pin_records", HERE / "check_pin_records.py")
assert _spec is not None and _spec.loader is not None
cpr = importlib.util.module_from_spec(_spec)
sys.modules["check_pin_records"] = cpr
_spec.loader.exec_module(cpr)

OLD = "27f20db6" + "0" * 32
NEW = "e233362c" + "1" * 32
STALE = "98d3be12" + "2" * 32
RECORD = "assurance/07-supporting/impact/change-pin.md"


@unittest.skipIf(shutil.which("git") is None, "needs git")
class TestCheckPinRecords(unittest.TestCase):
  def setUp(self):
    self.repo = Path(tempfile.mkdtemp())
    self.addCleanup(shutil.rmtree, self.repo)
    self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                    GIT_COMMITTER_EMAIL="t@t")
    self.git("init", "-q")
    self.set_pin("opendbc_repo", OLD)
    self.set_pin("panda", OLD)
    self.write("README.md", "base\n")
    self.commit("base")

  def git(self, *args):
    return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True,
                          env=self.env).stdout

  def set_pin(self, path, sha):
    self.git("update-index", "--add", "--cacheinfo", f"160000,{sha},{path}")

  def write(self, name, text):
    p = self.repo / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    self.git("add", name)

  def commit(self, msg):
    self.git("commit", "-q", "-m", msg)

  def test_no_pin_moved(self):
    self.write("README.md", "docs only\n")
    self.commit("docs")
    self.assertEqual(cpr.check(self.repo, "HEAD^1"), [])

  def test_pin_moved_with_record_naming_new_commit(self):
    self.set_pin("opendbc_repo", NEW)
    self.write(RECORD, "opendbc pin `27f20db` -> `e233362`\n")
    self.commit("pin")
    self.assertEqual(cpr.check(self.repo, "HEAD^1"), [])

  def test_pin_moved_without_record(self):
    # the case seen in review: a stale checkout committed with `git add .` rolls the pin back
    self.set_pin("opendbc_repo", STALE)
    self.write("README.md", "unrelated edit\n")
    self.commit("stale")
    errors = cpr.check(self.repo, "HEAD^1")
    self.assertEqual(len(errors), 1)
    assert "opendbc_repo" in errors[0]
    assert "98d3be1" in errors[0]

  def test_record_naming_another_commit_does_not_count(self):
    self.set_pin("panda", NEW)
    self.write(RECORD, "panda pin `27f20db` -> `98d3be1`\n")
    self.commit("pin")
    errors = cpr.check(self.repo, "HEAD^1")
    self.assertEqual(len(errors), 1)
    assert "panda" in errors[0]

  def test_existing_record_not_edited_does_not_count(self):
    # a record naming the commit already on the base branch does not cover a later move back to it
    self.write(RECORD, "opendbc pin `98d3be1`\n")
    self.commit("old record")
    self.set_pin("opendbc_repo", STALE)
    self.commit("roll back")
    self.assertEqual(len(cpr.check(self.repo, "HEAD^1")), 1)

  def test_each_moved_pin_checked(self):
    self.set_pin("opendbc_repo", NEW)
    self.set_pin("panda", STALE)
    self.write(RECORD, "opendbc `e233362`\n")
    self.commit("two pins")
    errors = cpr.check(self.repo, "HEAD^1")
    self.assertEqual(len(errors), 1)
    assert "panda" in errors[0]

  def test_pin_removed(self):
    self.git("rm", "-q", "--cached", "panda")
    self.commit("remove")
    errors = cpr.check(self.repo, "HEAD^1")
    self.assertEqual(len(errors), 1)
    assert "removed" in errors[0]

  def test_missing_base_is_an_error(self):
    with self.assertRaises(cpr.GitError):
      cpr.check(self.repo, "HEAD~5")


if __name__ == "__main__":
  unittest.main()
