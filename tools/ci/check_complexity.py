#!/usr/bin/env python3
"""ENV-R-07 size and complexity check of the envelope code with lizard (WP-W-01 §6, WP-P-07 TL-63, DQ-158 A).

Runs the pinned lizard on the files named in `complexity_exceptions.toml` and compares every function with
the limits there (NLOC 60, CCN 15). Fails when:

- a function exceeds a limit and is not in the exception list;
- a listed function has grown past the NLOC or CCN recorded for it (an exception cannot grow unnoticed);
- an entry is stale: its function is not found, or is back within both limits (remove the entry);
- the lizard found is not the pinned version, a scope entry matches no file, or no function is measured.

Usage: python3 tools/ci/check_complexity.py [--lizard PATH] [--report FILE.md]
Standard library only (Python 3.11+ for tomllib); needs lizard, installed from tools/ci/lizard-requirements.txt.
"""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "tools/ci/complexity_exceptions.toml"


@dataclass(frozen=True)
class Function:
  file: str
  name: str
  nloc: int
  ccn: int
  start: int


def scope_files(repo: Path, patterns: list[str]) -> tuple[list[str], list[str]]:
  """Expand the scope entries; return (files, errors). Files are repository-relative, sorted, unique."""
  files, errors = set(), []
  for pattern in patterns:
    found = sorted(p for p in repo.glob(pattern) if p.is_file())
    if not found:
      errors.append(f"scope entry matches no file: {pattern} (submodules checked out?)")
    files.update(p.relative_to(repo).as_posix() for p in found)
  return sorted(files), errors


def parse_csv(text: str) -> list[Function]:
  """lizard --csv rows: NLOC, CCN, token, PARAM, length, location, file, function, long_name, start, end."""
  out = []
  for row in csv.reader(io.StringIO(text)):
    if not row or row[0] == "NLOC":
      continue
    out.append(Function(file=row[6], name=row[7], nloc=int(row[0]), ccn=int(row[1]), start=int(row[9])))
  return out


def compare(functions: list[Function], limits: dict, exceptions: list[dict]) -> tuple[list[str], list[str]]:
  """Return (errors, notes) for the measured functions against the limits and the exception list."""
  errors, notes = [], []
  max_nloc, max_ccn = limits["nloc"], limits["ccn"]
  listed = {}
  for e in exceptions:
    key = (e["file"], e["function"])
    if key in listed:
      errors.append(f"{e['file']}: {e['function']} is listed twice")
    listed[key] = e
  seen = set()
  for f in functions:
    key = (f.file, f.name)
    over = f.nloc > max_nloc or f.ccn > max_ccn
    e = listed.get(key)
    if e is None:
      if over:
        errors.append(f"{f.file}:{f.start}: {f.name} has NLOC {f.nloc}, CCN {f.ccn} (limits {max_nloc}, {max_ccn}) "
                      "and is not in the exception list: split it, or add a justified exception (WP-W-01 ENV-R-07)")
      continue
    seen.add(key)
    if not over:
      errors.append(f"{f.file}:{f.start}: {f.name} is within the limits now (NLOC {f.nloc}, CCN {f.ccn}): "
                    "remove its exception")
      continue
    if f.nloc > e["nloc"] or f.ccn > e["ccn"]:
      errors.append(f"{f.file}:{f.start}: {f.name} grew past its exception: NLOC {f.nloc} (listed {e['nloc']}), "
                    f"CCN {f.ccn} (listed {e['ccn']})")
    elif f.nloc < e["nloc"] or f.ccn < e["ccn"]:
      notes.append(f"{f.name} shrank to NLOC {f.nloc}, CCN {f.ccn}: the exception can be tightened")
  for key, e in listed.items():
    if key not in seen:
      errors.append(f"{e['file']}: {e['function']} not found: remove its exception or correct the file name")
  return errors, notes


def report(functions: list[Function], limits: dict, exceptions: list[dict], version: str, files: list[str],
           errors: list[str]) -> str:
  listed = {(e["file"], e["function"]): e for e in exceptions}
  over = [f for f in functions if f.nloc > limits["nloc"] or f.ccn > limits["ccn"]]
  lines = [
    "# ENV-R-07 size and complexity (lizard)",
    "",
    f"lizard {version}; limits NLOC {limits['nloc']}, CCN {limits['ccn']}; {len(files)} files, "
    f"{len(functions)} functions, {len(over)} over a limit, {len(errors)} errors.",
    "",
    "| File | Function | NLOC | CCN | Exception | Reason |",
    "|---|---|---|---|---|---|",
  ]
  for f in sorted(over, key=lambda f: (f.file, f.start)):
    e = listed.get((f.file, f.name))
    lines.append(f"| `{f.file}:{f.start}` | `{f.name}` | {f.nloc} | {f.ccn} | "
                 f"{'listed' if e else '**not listed**'} | {e['reason'] if e else '—'} |")
  if errors:
    lines += ["", "## Errors", ""] + [f"- {x}" for x in errors]
  return "\n".join(lines) + "\n"


def run_lizard(lizard: str, files: list[str]) -> tuple[str, str]:
  version = subprocess.run([lizard, "--version"], capture_output=True, text=True, check=True).stdout.strip()
  out = subprocess.run([lizard, "-l", "c", "--csv", *files], cwd=REPO, capture_output=True, text=True, check=False)
  if out.returncode not in (0, 1):  # 1: lizard warned under its own default thresholds, which are not ours
    raise RuntimeError(f"lizard failed ({out.returncode}): {out.stderr.strip()}")
  return version, out.stdout


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--lizard", default="lizard", help="lizard executable (default: lizard on PATH)")
  ap.add_argument("--report", type=Path, help="write a Markdown report here")
  args = ap.parse_args(argv)

  config = tomllib.loads(CONFIG.read_text())
  limits, exceptions = config["limits"], config.get("exceptions", [])
  files, errors = scope_files(REPO, config["scope"]["files"])
  version, text = run_lizard(args.lizard, files) if files else ("not run", "")
  if version != config["lizard_version"]:
    errors.append(f"lizard {version} found, {config['lizard_version']} pinned (tools/ci/lizard-requirements.txt)")
  functions = parse_csv(text)
  if not functions:
    errors.append("lizard measured no function")
  found_errors, notes = compare(functions, limits, exceptions)
  errors += found_errors

  print(f"lizard {version}: {len(files)} files, {len(functions)} functions, "
        f"{len(exceptions)} listed exceptions (limits NLOC {limits['nloc']}, CCN {limits['ccn']})")
  for n in notes:
    print(f"note: {n}")
  for e in errors:
    print(f"error: {e}")
  if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report(functions, limits, exceptions, version, files, errors))
  return 1 if errors else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
