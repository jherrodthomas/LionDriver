#!/usr/bin/env python3
"""Mutation check of the LionDriver host safety tests (SW FMEA SWF-ACT-078, -080, -081; RT-2 detection D 4).

The SW FMEA gives a targeted host test D 8 until it is shown to fail on a defect in the code it covers. This
tool applies each hand-written mutant of `host_mutants.toml` to its file, one at a time, runs the tests named for
it, and requires them to fail. The mutants are the defects the FMEA causes describe: a comparison or limit off by
one, a branch dropped, a latch never set or never cleared. First the tests run on the unmutated code and must pass.
The file is restored after every mutant, also when a run is interrupted.

    python3 tools/ci/host_mutation.py             # run every mutant; exit 1 if one survives
    python3 tools/ci/host_mutation.py --list      # list the mutants and the FMEA causes they back
    python3 tools/ci/host_mutation.py --only ID   # run one mutant
    python3 tools/ci/host_mutation.py --json PATH # also write the results

Each mutant's `find` text must occur exactly once in its file, so a mutant that no longer matches the code fails
the run instead of passing silently. Needs the openpilot environment (CI unit_tests job, after scons).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import tomllib

REPO = Path(__file__).resolve().parents[2]
MUTANTS = Path(__file__).with_name("host_mutants.toml")
TIMEOUT_S = 600


class MutantError(Exception):
  pass


@dataclass(frozen=True)
class Mutant:
  id: str
  file: str
  find: str
  replace: str
  tests: tuple[str, ...]
  fmea: tuple[str, ...]
  why: str


def load(path: Path = MUTANTS) -> list[Mutant]:
  doc = tomllib.loads(path.read_text(encoding="utf-8"))
  out, seen = [], set()
  for m in doc["mutants"]:
    if m["id"] in seen:
      raise MutantError(f"{m['id']}: duplicate id")
    seen.add(m["id"])
    if m["find"] == m["replace"]:
      raise MutantError(f"{m['id']}: replace equals find")
    if not m.get("tests") or not m.get("fmea"):
      raise MutantError(f"{m['id']}: needs tests and fmea")
    out.append(Mutant(m["id"], m["file"], m["find"], m["replace"], tuple(m["tests"]), tuple(m["fmea"]), m["why"]))
  return out


def mutate(text: str, m: Mutant) -> str:
  n = text.count(m.find)
  if n != 1:
    raise MutantError(f"{m.id}: `find` occurs {n} times in {m.file}, not once")
  return text.replace(m.find, m.replace)


def write_source(path: Path, text: str) -> None:
  """Write a source file and drop its cached bytecode. A mutant of the same length written within the same second as the
  original keeps the size and mtime that the .pyc records, so Python would load the stale original and the mutant would
  survive for no reason."""
  path.write_text(text, encoding="utf-8")
  Path(importlib.util.cache_from_source(str(path))).unlink(missing_ok=True)


def run_tests(tests: tuple[str, ...]) -> subprocess.CompletedProcess:
  cmd = [sys.executable, str(REPO / "tools/test_runner.py"), "-j", "1", "--durations", "0", *tests]
  return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=TIMEOUT_S)


def check(mutants: list[Mutant]) -> list[dict]:
  results = []
  for tests in sorted({m.tests for m in mutants}):
    base = run_tests(tests)
    if base.returncode != 0:
      raise MutantError(f"tests fail on the unmutated code: {' '.join(tests)}\n{base.stdout[-2000:]}")
  for m in mutants:
    path = REPO / m.file
    original = path.read_text(encoding="utf-8")
    mutated = mutate(original, m)
    try:
      write_source(path, mutated)
      r = run_tests(m.tests)
    finally:
      write_source(path, original)
    if "COLLECTION ERROR" in r.stdout:
      reason = "an import or syntax error kills nothing"
      raise MutantError(f"{m.id}: the tests could not be collected on the mutant ({reason}):\n{r.stdout[-2000:]}")
    killed = r.returncode != 0
    results.append({"id": m.id, "file": m.file, "fmea": list(m.fmea), "killed": killed})
    print(f"{'killed  ' if killed else 'SURVIVED'} {m.id}  ({', '.join(m.fmea)})")
  return results


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("--list", action="store_true")
  ap.add_argument("--only")
  ap.add_argument("--json", type=Path)
  a = ap.parse_args(argv)
  mutants = load()
  if a.only:
    mutants = [m for m in mutants if m.id == a.only]
    if not mutants:
      print(f"no mutant {a.only}", file=sys.stderr)
      return 2
  if a.list:
    for m in mutants:
      print(f"{m.id}  {m.file}  {', '.join(m.fmea)}: {m.why}")
    return 0
  try:
    results = check(mutants)
  except MutantError as e:
    print(f"host_mutation: {e}", file=sys.stderr)
    return 1
  if a.json:
    a.json.parent.mkdir(parents=True, exist_ok=True)
    a.json.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
  survived = [r["id"] for r in results if not r["killed"]]
  print(f"host_mutation: {len(results) - len(survived)} of {len(results)} mutants killed")
  if survived:
    print(f"host_mutation: survived: {', '.join(survived)}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
