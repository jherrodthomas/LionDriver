#!/usr/bin/env python3
"""Tests for build_manifest.py (WP-P-07 TL-38, OI-13).

The manifest is built in a throwaway git repository with one submodule, controlled environment variables and a PATH
holding only fake tools, so every field has a known expected value.

Run from the repository root:  python3 -m unittest discover -s tools/ci -p 'test_*.py' -v
Standard library only; needs git.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("build_manifest", HERE / "build_manifest.py")
bm = importlib.util.module_from_spec(_spec)
sys.modules["build_manifest"] = bm
_spec.loader.exec_module(bm)

GIT = shutil.which("git")


def git(cwd, *args):
  env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
         "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "PATH": os.environ.get("PATH", "")}
  return subprocess.run([GIT, "-c", "protocol.file.allow=always", "-c", "init.defaultBranch=main", *args], cwd=cwd,
                        env=env, check=True, capture_output=True, text=True).stdout.strip()


@unittest.skipIf(GIT is None, "git not installed")
class TestManifest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.tmp = Path(tempfile.mkdtemp())
    sub = cls.tmp / "sub"
    sub.mkdir()
    git(sub, "init", "-q")
    (sub / "f").write_text("x")
    git(sub, "add", "f")
    git(sub, "commit", "-q", "-m", "s")
    cls.sub_sha = git(sub, "rev-parse", "HEAD")
    cls.repo = cls.tmp / "repo"
    cls.repo.mkdir()
    git(cls.repo, "init", "-q")
    git(cls.repo, "submodule", "add", "-q", str(sub), "mod")
    git(cls.repo, "commit", "-q", "-m", "r")
    cls.repo_sha = git(cls.repo, "rev-parse", "HEAD")
    # a fake tool first on PATH, the system PATH behind it
    cls.bin = cls.tmp / "bin"
    cls.bin.mkdir()
    fake = cls.bin / "scons"
    fake.write_text("#!/bin/sh\necho 'SCons by Steven Knight et al.:'\necho 'second line'\n")
    fake.chmod(0o755)

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.tmp, ignore_errors=True)

  def manifest(self, env, tools=None):
    base = {"PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}"}
    with mock.patch.object(bm, "REPO", self.repo), mock.patch.object(bm, "TOOLS", tools or bm.TOOLS), \
         mock.patch.dict(os.environ, {**base, **env}, clear=True):
      return bm.manifest()

  def test_fields_outside_ci(self):
    tools = ["scons", "git", "no-such-tool-ld-test"]
    m = self.manifest({"LIONDRIVER_REFERENCE": "1"}, tools)
    self.assertEqual(m["superproject"], self.repo_sha)
    self.assertEqual(m["submodules"], {"mod": f"{self.sub_sha} (at pin)"})
    self.assertEqual(m["flags"], {"RELEASE": "", "LIONDRIVER_REFERENCE": "1"})
    self.assertEqual(m["tools"]["scons"], "SCons by Steven Knight et al.:")
    self.assertTrue(m["tools"]["git"].startswith("git version"))
    self.assertEqual(m["tools"]["no-such-tool-ld-test"], "not on PATH")
    self.assertEqual(set(m["tools"]), set(tools))

  def test_failed_git_command_is_an_error_not_a_submodule(self):
    with mock.patch.object(bm, "REPO", self.tmp):  # not a git repository
      self.assertEqual(list(bm.submodules()), ["(error)"])
      self.assertTrue(bm.run(["git", "rev-parse", "HEAD"]).startswith("error: exit "))

  def test_ci_environment_wins(self):
    env = {"GITHUB_SHA": "f" * 40, "GITHUB_REF": "refs/pull/1/merge", "GITHUB_RUN_ID": "7", "GITHUB_JOB": "j",
           "RUNNER_OS": "Linux", "RELEASE": "1"}
    m = self.manifest(env)
    self.assertEqual(m["superproject"], "f" * 40)
    self.assertEqual(m["ref"], "refs/pull/1/merge")
    self.assertEqual(m["ci_run"]["GITHUB_RUN_ID"], "7")
    self.assertEqual(m["ci_run"]["GITHUB_JOB"], "j")
    self.assertEqual(m["runner"]["RUNNER_OS"], "Linux")
    self.assertEqual(m["flags"]["RELEASE"], "1")

  def test_submodule_states(self):
    sub_dir = self.repo / "mod"
    (sub_dir / "g").write_text("y")
    git(sub_dir, "add", "g")
    git(sub_dir, "commit", "-q", "-m", "moved")
    try:
      m = self.manifest({})
      self.assertTrue(m["submodules"]["mod"].endswith("(differs from pin)"), m["submodules"])
    finally:
      git(sub_dir, "checkout", "-q", self.sub_sha)
    git(self.repo, "submodule", "deinit", "-q", "-f", "mod")
    try:
      m = self.manifest({})
      self.assertEqual(m["submodules"], {"mod": f"{self.sub_sha} (not checked out)"})
    finally:
      git(self.repo, "submodule", "update", "-q", "--init")

  def test_main_writes_json(self):
    out = self.tmp / "o" / "m.json"
    with mock.patch.object(bm, "REPO", self.repo), \
         mock.patch.dict(os.environ, {"PATH": os.environ.get("PATH", "")}, clear=True), \
         mock.patch("sys.stdout"):
      self.assertEqual(bm.main(["x", str(out)]), 0)
    self.assertEqual(json.loads(out.read_text())["superproject"], self.repo_sha)
    with mock.patch("sys.stdout"):
      self.assertEqual(bm.main(["x"]), 2)


if __name__ == "__main__":
  unittest.main()
