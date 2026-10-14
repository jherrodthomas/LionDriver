#!/usr/bin/env python3
"""Structural coverage (branch and MC/DC) of the envelope's opendbc units, measured with two independent tools.

WP-W-06 §4 asks for branch coverage and MC/DC of the safety units. The opendbc safety tests already run the C code
through `libsafety_py.py`, which compiles `safety.c` with `cc`. This tool puts a `cc` wrapper first on PATH, so the
same tests are measured without changing the opendbc fork:

- `llvm`: clang with source-based coverage and MC/DC (`-fprofile-instr-generate -fcoverage-mapping -fcoverage-mcdc`),
  read with `llvm-cov export`. This is the primary measurement (WP-P-07 TL-42).
- `gcc`: gcc 14 with condition coverage (`--coverage -fcondition-coverage`), read with `gcov --json-format
  --conditions`. This is the independent cross-check (WP-P-07 TL-43).

UBSan flags are dropped while measuring, as `test.sh` does for its coverage run. The tests run on the reference build
(`LIONDRIVER_REFERENCE=1`), which is what the panda reference firmware compiles.

    structural_coverage.py run --tool llvm --out DIR     # build, run the tests, write DIR/llvm.json
    structural_coverage.py run --tool gcc --out DIR      # same with gcc 14, DIR/gcc.json
    structural_coverage.py report DIR [--check | --write-baseline] [--md FILE]

`--check` fails when a unit's uncovered branches or MC/DC conditions exceed the committed baseline
(`assurance/05-software/coverage/structural-baseline.json`), or when the opendbc pin changed and the baseline was
not re-recorded. The baseline is a ratchet: it records today's gaps so they cannot grow, it is not a pass criterion
of WP-W-06 (100 % or a justification per decision).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OPENDBC = ROOT / "opendbc_repo"
TESTS = OPENDBC / "opendbc" / "safety" / "tests"
BASELINE = ROOT / "assurance" / "05-software" / "coverage" / "structural-baseline.json"
JUSTIFICATIONS = ROOT / "assurance" / "05-software" / "coverage" / "justifications.md"
CLASSES = {"N": "not called", "C": "configuration constant", "I": "infeasible", "T": "test needed"}

# Units of WP-W-06 §2 in the opendbc fork (U-SAF-CORE, -LAT, -LONG, -TOY)
UNITS = {
  "U-SAF-CORE": "opendbc/safety/safety.h",
  "U-SAF-LAT": "opendbc/safety/lateral.h",
  "U-SAF-LONG": "opendbc/safety/longitudinal.h",
  "U-SAF-TOY": "opendbc/safety/modes/toyota.h",
}
# Test modules that exercise the reference configuration: the Toyota mode, the default (no output) mode and ELM327,
# which pandad uses for fingerprinting before the car mode is set
TEST_MODULES = ["test_toyota", "test_defaults", "test_elm327"]

COMPILERS = {
  "llvm": ("clang-18", ["-fprofile-instr-generate", "-fcoverage-mapping", "-fcoverage-mcdc"]),
  "gcc": ("gcc-14", ["--coverage", "-fcondition-coverage"]),
}
TOOLS = {"llvm": ("llvm-profdata-18", "llvm-cov-18"), "gcc": ("gcov-14",)}

SHIM = """#!/bin/bash
# cc wrapper written by structural_coverage.py: drop sanitizer flags, add coverage flags, log the output file
args=(); out=""; prev=""
for a in "$@"; do
  case "$a" in -fsanitize*|-fno-sanitize*) ;; *) args+=("$a");; esac
  [ "$prev" = "-o" ] && out="$a"
  prev="$a"
done
[ -n "$out" ] && echo "$out" >> "{log}"
exec {cc} {flags} "${{args[@]}}" -Wno-error
"""


class CoverageError(Exception):
  pass


def need(tool: str) -> str:
  path = shutil.which(tool)
  if not path:
    raise CoverageError(f"{tool} not found; install it (CI: apt-get install clang-18 libclang-rt-18-dev llvm-18 gcc-14)")
  return path


def tool_versions(tool: str) -> dict[str, str]:
  out = {}
  for t in (COMPILERS[tool][0], *TOOLS[tool]):
    r = subprocess.run([t, "--version"], capture_output=True, text=True)
    out[t] = (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "?"
  return out


def opendbc_pin() -> str:
  r = subprocess.run(["git", "-C", str(OPENDBC), "rev-parse", "--short=7", "HEAD"], capture_output=True, text=True)
  return r.stdout.strip() or "?"


def run_tests(tool: str, work: Path) -> list[str]:
  """Run the reference-configuration tests with the coverage compiler; return the files the wrapper wrote."""
  cc, flags = COMPILERS[tool]
  need(cc)
  for t in TOOLS[tool]:
    need(t)
  bindir = work / "bin"
  bindir.mkdir(parents=True, exist_ok=True)
  log = work / "outputs.log"
  shim = bindir / "cc"
  shim.write_text(SHIM.format(log=log, cc=need(cc), flags=" ".join(flags)), encoding="utf-8")
  shim.chmod(0o755)
  env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}", LIONDRIVER_REFERENCE="1",
             LLVM_PROFILE_FILE=str(work / "prof" / "%p-%m.profraw"), SAFETY_COVERAGE="0")
  py = os.environ.get("OPENDBC_PYTHON")
  cmd = (f'"{py}" -m unittest {" ".join(TEST_MODULES)}' if py else
         f'source "{OPENDBC}/setup.sh" >/dev/null && python -m unittest {" ".join(TEST_MODULES)}')
  r = subprocess.run(["bash", "-c", cmd], cwd=TESTS, env=env, capture_output=True, text=True)
  tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
  if r.returncode != 0:
    raise CoverageError("safety tests failed under the coverage compiler:\n" + "\n".join(tail))
  # clang 18 measures MC/DC only for decisions of at most 6 conditions; one in a unit would silently drop out
  dropped = sorted({ln.split(": warning")[0] for ln in (r.stdout + r.stderr).splitlines()
                    if "unsupported MC/DC" in ln and unit_of(ln.split(":")[0])})
  if dropped:
    raise CoverageError("decisions in the units are not measured for MC/DC (too many conditions): " + ", ".join(dropped))
  return [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln] if log.exists() else []


def unit_of(filename: str) -> str | None:
  for unit, rel in UNITS.items():
    if filename.endswith("/" + rel):
      return unit
  return None


def norm(src: str) -> str:
  return " ".join(src.split())


def gaps_of(f: dict, functions: list[dict], lines: list[int]) -> list[dict]:
  """The uncovered items of one file: functions never entered, and decisions with an uncovered branch or condition
  inside functions that ran. A decision is named by its function and its normalized source line, so a justification
  survives line shifts."""
  path = f["filename"]
  src = Path(path).read_text(encoding="utf-8").splitlines() if Path(path).exists() else []
  spans = []
  for fn in functions:
    idx = [i for i, name in enumerate(fn["filenames"]) if name == path]
    regs = [r for r in fn["regions"] if r[5] in idx]
    if regs:
      spans.append((min(r[0] for r in regs), max(r[2] for r in regs), fn["name"].split(":")[-1], fn["count"]))
  gaps = [{"function": n, "decision": "*"} for _, _, n, c in sorted(spans) if c == 0]
  for ln in lines:
    owner = sorted((e - b, n, c) for b, e, n, c in spans if b <= ln <= e)
    if not owner or owner[0][2] == 0:
      continue   # inside a function that never ran: covered by its "*" entry
    gaps.append({"function": owner[0][1], "decision": norm(src[ln - 1]) if ln <= len(src) else f"line {ln}", "line": ln})
  return gaps


def measure_llvm(work: Path, outputs: list[str]) -> dict:
  profdata, llvm_cov = TOOLS["llvm"]
  raws = sorted((work / "prof").glob("*.profraw"))
  sos = [o for o in outputs if o.endswith(".so")]
  if not raws or not sos:
    raise CoverageError("no LLVM profile or shared library was produced")
  merged = work / "merged.profdata"
  subprocess.run([profdata, "merge", "-o", str(merged), *map(str, raws)], check=True)
  units = {}
  for so in sos:
    exp = json.loads(subprocess.run([llvm_cov, "export", so, f"-instr-profile={merged}"], check=True,
                                    capture_output=True, text=True).stdout)
    for f in exp["data"][0]["files"]:
      u = unit_of(f["filename"])
      if not u or u in units:
        continue
      s = f["summary"]
      unc_br = sorted({b[0] for b in f["branches"] if b[4] == 0 or b[5] == 0})
      unc_mc = sorted({r[0] for r in f.get("mcdc_records", []) if not all(r[-1])})
      units[u] = {"file": UNITS[u],
                  "branches": {"total": s["branches"]["count"], "covered": s["branches"]["covered"], "uncovered_lines": unc_br},
                  "mcdc": {"total": s["mcdc"]["count"], "covered": s["mcdc"]["covered"], "uncovered_lines": unc_mc},
                  "gaps": gaps_of(f, exp["data"][0]["functions"], sorted(set(unc_br) | set(unc_mc)))}
    for o in outputs:
      Path(o).unlink(missing_ok=True)
  return units


def measure_gcc(work: Path, outputs: list[str]) -> dict:
  (gcov,) = TOOLS["gcc"]
  objs = [Path(o) for o in outputs if o.endswith(".os")]
  units = {}
  for obj in objs:
    gcda = obj.with_suffix(".gcda")
    if not gcda.exists():
      continue
    r = subprocess.run([gcov, "--json-format", "--conditions", "--stdout", gcda.name], cwd=gcda.parent,
                       check=True, capture_output=True, text=True)
    for doc in r.stdout.splitlines():
      if not doc.strip():
        continue
      for f in json.loads(doc)["files"]:
        u = unit_of(f["file"])
        if not u or u in units:
          continue
        tot = cov = mtot = mcov = 0
        unc = set()
        for ln in f["lines"]:
          for c in ln.get("conditions", []):
            tot += c["count"]
            cov += c["covered"]
            if c["count"] >= 4:   # two or more conditions: the decisions LLVM's MC/DC counts
              mtot += c["count"]
              mcov += c["covered"]
              if c["covered"] < c["count"]:
                unc.add(ln["line_number"])
        units[u] = {"file": UNITS[u], "conditions": {"outcomes": tot, "covered": cov},
                    "multi_conditions": {"outcomes": mtot, "covered": mcov, "uncovered_lines": sorted(unc)}}
  for o in objs:
    for suf in (".os", ".gcda", ".gcno"):
      o.with_suffix(suf).unlink(missing_ok=True)
  for o in outputs:
    if o.endswith(".so"):
      Path(o).unlink(missing_ok=True)
  return units


def cmd_run(tool: str, out: Path) -> int:
  out.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    t0 = time.time()
    outputs = run_tests(tool, work)
    units = measure_llvm(work, outputs) if tool == "llvm" else measure_gcc(work, outputs)
  missing = sorted(set(UNITS) - set(units))
  if missing:
    raise CoverageError(f"{tool}: no coverage data for {missing}")
  data = {"tool": tool, "versions": tool_versions(tool), "opendbc": opendbc_pin(), "tests": TEST_MODULES,
          "variant": "LIONDRIVER_REFERENCE=1", "seconds": round(time.time() - t0, 1), "units": units}
  (out / f"{tool}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
  print(f"structural_coverage: {tool} measured {len(units)} units in {data['seconds']} s")
  return 0


def pct(c: int, t: int) -> str:
  return f"{100 * c / t:.1f} %" if t else "n/a"


def cross_check(llvm: dict, gcc: dict | None) -> dict[str, dict]:
  """Lines with an uncovered multi-condition decision, per unit, as each tool sees them."""
  out = {}
  for u, d in llvm["units"].items():
    a = set(d["mcdc"]["uncovered_lines"])
    b = set(gcc["units"][u]["multi_conditions"]["uncovered_lines"]) if gcc else set()
    out[u] = {"both": sorted(a & b), "llvm_only": sorted(a - b), "gcc_only": sorted(b - a)}
  return out


def gap_section(llvm: dict) -> list[str]:
  if not any("gaps" in v for v in llvm["units"].values()) or not JUSTIFICATIONS.exists():
    return []
  matched, missing, stale = match_gaps(llvm, load_justifications())
  out = ["## Gaps and their justifications", "", "| Unit | Function | Decision | Row | Class |", "|---|---|---|---|---|"]
  for u, g, r in matched:
    out.append(f"| {u} | `{g['function']}` | {'whole function' if g['decision'] == '*' else '`' + g['decision'][:70].replace('|', '\\|') + '`'} | "
               f"{r['id']} | {CLASSES[r['class']]} |")
  for u, g in missing:
    out.append(f"| {u} | `{g['function']}` | `{g['decision'][:70].replace('|', '\\|')}` | **none** | unjustified |")
  for r in stale:
    out.append(f"| {r['unit']} | `{r['function']}` | (no longer a gap) | {r['id']} | stale row |")
  return out + [""]


def render_md(llvm: dict, gcc: dict | None) -> str:
  cc = cross_check(llvm, gcc)
  lines = ["# Structural coverage of the envelope's opendbc units", "",
           f"Generated by `tools/ci/coverage/structural_coverage.py` at opendbc `{llvm['opendbc']}`, reference build "
           f"(`{llvm['variant']}`), tests {', '.join('`' + t + '`' for t in llvm['tests'])}.", "",
           "| Unit | File | Branches (LLVM) | MC/DC conditions (LLVM) | Multi-condition outcomes (gcc 14) |",
           "|---|---|---|---|---|"]
  for u, d in llvm["units"].items():
    b, m = d["branches"], d["mcdc"]
    g = gcc["units"][u]["multi_conditions"] if gcc else None
    gtxt = f"{g['covered']}/{g['outcomes']} ({pct(g['covered'], g['outcomes'])})" if g else "not run"
    lines.append(f"| {u} | `{d['file']}` | {b['covered']}/{b['total']} ({pct(b['covered'], b['total'])}) | "
                 f"{m['covered']}/{m['total']} ({pct(m['covered'], m['total'])}) | {gtxt} |")
  lines += ["", "## Cross-check: lines with an uncovered multi-condition decision", "",
            "| Unit | Both tools | LLVM only | gcc only |", "|---|---|---|---|"]
  for u, c in cc.items():
    lines.append(f"| {u} | {', '.join(map(str, c['both'])) or '—'} | {', '.join(map(str, c['llvm_only'])) or '—'} | "
                 f"{', '.join(map(str, c['gcc_only'])) or '—'} |")
  lines += ["", "LLVM counts each condition of a decision with two or more conditions once; gcc counts both outcomes of "
            "each condition. A line in only one column is a disagreement to review (WP-P-07 TQR-42).", "",
            *gap_section(llvm),
            "Tool versions: " + "; ".join(f"{k}: {v}" for k, v in {**llvm["versions"], **(gcc or {}).get("versions", {})}.items()), ""]
  return "\n".join(lines)


def load_justifications(path: Path | None = None) -> list[dict]:
  """Rows of the justification table: ID | Unit | Function | Decision | Class | Rationale."""
  rows = []
  for ln in (path or JUSTIFICATIONS).read_text(encoding="utf-8").splitlines():
    if not ln.startswith("| CJ-"):
      continue
    cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", ln.strip())[1:-1]]
    if len(cells) != 6 or cells[4] not in CLASSES:
      raise CoverageError(f"justification row malformed: {ln[:80]}")
    rows.append({"id": cells[0], "unit": cells[1], "function": cells[2], "decision": norm(cells[3]),
                 "class": cells[4], "rationale": cells[5]})
  return rows


def match_gaps(llvm: dict, rows: list[dict]) -> tuple[list[tuple[str, dict, dict]], list[tuple[str, dict]], list[dict]]:
  """(matched (unit, gap, row), unjustified (unit, gap), stale rows)."""
  index = {(r["unit"], r["function"], r["decision"]): r for r in rows}
  matched, missing, used = [], [], set()
  for u, v in llvm["units"].items():
    for g in v.get("gaps", []):
      r = index.get((u, g["function"], norm(g["decision"])))
      if r:
        matched.append((u, g, r))
        used.add(r["id"])
      else:
        missing.append((u, g))
  return matched, missing, [r for r in rows if r["id"] not in used]


def cmd_report(d: Path, check: bool, write: bool, md: Path | None) -> int:
  llvm = json.loads((d / "llvm.json").read_text(encoding="utf-8"))
  gcc = json.loads((d / "gcc.json").read_text(encoding="utf-8")) if (d / "gcc.json").exists() else None
  text = render_md(llvm, gcc)
  if md:
    md.write_text(text, encoding="utf-8")
  print(text)
  current = {"opendbc": llvm["opendbc"], "units": {u: {"branches_uncovered": v["branches"]["total"] - v["branches"]["covered"],
                                                       "branches_total": v["branches"]["total"],
                                                       "mcdc_uncovered": v["mcdc"]["total"] - v["mcdc"]["covered"],
                                                       "mcdc_total": v["mcdc"]["total"]}
                                                   for u, v in llvm["units"].items()}}
  if write:
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(f"structural_coverage: baseline written to {BASELINE}")
    return 0
  if not check:
    return 0
  base = json.loads(BASELINE.read_text(encoding="utf-8"))
  problems = []
  for u, cur in current["units"].items():
    b = base["units"].get(u)
    if not b:
      problems.append(f"{u}: not in the baseline")
      continue
    for k in ("branches", "mcdc"):
      if cur[f"{k}_uncovered"] > b[f"{k}_uncovered"]:
        problems.append(f"{u}: {cur[k + '_uncovered']} uncovered {k} (baseline {b[k + '_uncovered']})")
  if current["opendbc"] != base["opendbc"] and current["units"] != base["units"]:
    problems.append(f"opendbc pin {base['opendbc']} -> {current['opendbc']} changed the measured units; "
                    "re-record the baseline (--write-baseline) and review the change in WP-W-06 §4")
  if any("gaps" in v for v in llvm["units"].values()):
    matched, missing, stale = match_gaps(llvm, load_justifications())
    for u, g in missing:
      problems.append(f"{u} {g['function']}: gap without a justification row: {g['decision'][:80]}")
    for r in stale:
      problems.append(f"{r['id']}: no longer matches a gap (closed by a test or the code changed); remove or update it")
    by = {}
    for _, _, r in matched:
      by[r["class"]] = by.get(r["class"], 0) + 1
    print("structural_coverage: gaps by class: " + ", ".join(f"{CLASSES[k]} {by.get(k, 0)}" for k in CLASSES))
  for p in problems:
    print(f"structural_coverage: {p}", file=sys.stderr)
  if problems:
    return 1
  print(f"structural_coverage: no unit has more uncovered branches or MC/DC conditions than the baseline "
        f"(opendbc {base['opendbc']})")
  return 0


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  sub = ap.add_subparsers(dest="cmd", required=True)
  r = sub.add_parser("run")
  r.add_argument("--tool", choices=sorted(COMPILERS), required=True)
  r.add_argument("--out", type=Path, required=True)
  p = sub.add_parser("report")
  p.add_argument("dir", type=Path)
  g = p.add_mutually_exclusive_group()
  g.add_argument("--check", action="store_true")
  g.add_argument("--write-baseline", action="store_true")
  p.add_argument("--md", type=Path)
  a = ap.parse_args(argv)
  try:
    if a.cmd == "run":
      return cmd_run(a.tool, a.out)
    return cmd_report(a.dir, a.check, a.write_baseline, a.md)
  except CoverageError as e:
    print(f"structural_coverage: {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
