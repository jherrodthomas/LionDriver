#!/usr/bin/env python3
"""Fail when a change moves a safety submodule pin without a change record (WP-P-02, WP-M-11 §3).

For `opendbc_repo` and `panda`, compares the pinned commit at a base revision with HEAD. If a pin
moved, at least one change record under `assurance/07-supporting/impact/` that the change adds or
edits must name the new commit (its first 7 hex digits). A pin that moves without one, for example a
stale local submodule checkout committed by accident, fails the check.

In CI the checkout is the pull request's merge commit (or the push), fetched with depth 2, so the
default base `HEAD^1` is the target branch before the change.

Usage: python3 tools/ci/check_pin_records.py [--base REV]
Standard library only; needs git.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBMODULES = ("opendbc_repo", "panda")
RECORDS = "assurance/07-supporting/impact/"
SHORT = 7


class GitError(Exception):
  pass


def git(repo: Path, *args: str) -> str:
  out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
  if out.returncode != 0:
    raise GitError(f"git {' '.join(args)}: {out.stderr.strip()}")
  return out.stdout


def pin(repo: Path, rev: str, path: str) -> str | None:
  """The commit a gitlink points to at `rev`, or None if the path is not a submodule there."""
  line = git(repo, "ls-tree", rev, "--", path).strip()
  if not line:
    return None
  mode, kind, sha = line.split("\t")[0].split()
  return sha if mode == "160000" and kind == "commit" else None


def check(repo: Path, base: str, head: str = "HEAD") -> list[str]:
  """Return one error per moved pin that no added or edited change record names."""
  errors = []
  changed = git(repo, "diff", "--name-only", "--diff-filter=AM", base, head, "--", RECORDS).split()
  records = {name: git(repo, "show", f"{head}:{name}") for name in changed if name.endswith(".md")}
  for path in SUBMODULES:
    old, new = pin(repo, base, path), pin(repo, head, path)
    if old == new:
      continue
    if new is None:
      errors.append(f"{path}: pin removed (was {old})")
      continue
    named = sorted(name for name, text in records.items() if new[:SHORT] in text)
    if named:
      print(f"{path}: {(old or 'none')[:SHORT]} -> {new[:SHORT]}, recorded in {', '.join(named)}")
    else:
      moved = f"{path}: pin moved {(old or 'none')[:SHORT]} -> {new[:SHORT]}"
      missing = f"no change record added or edited under {RECORDS} names {new[:SHORT]}"
      fix = "if the move is not intended, run `git submodule update` and restore the pin; otherwise add the record"
      errors.append(f"{moved}, but {missing}. {fix}")
  return errors


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument("--base", default="HEAD^1", help="revision to compare with (default: HEAD^1)")
  args = parser.parse_args()
  try:
    errors = check(REPO, args.base)
  except GitError as e:
    print(f"check_pin_records: {e}", file=sys.stderr)
    return 2
  for e in errors:
    print(f"ERROR: {e}", file=sys.stderr)
  if not errors:
    print("check_pin_records: OK, no pin moved without a change record")
  return 1 if errors else 0


if __name__ == "__main__":
  sys.exit(main())
