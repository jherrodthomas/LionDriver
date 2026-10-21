#!/usr/bin/env python3
"""TE-03 step P4: runtime monitors from the FRETish requirements, run against the panda's own code.

  1. Write `monitor-spec.json`, a FRET component specification (Ogma's `fcs` format) holding FRET's past-time
     formulas for MONITORED and the glossary types of their variables.
  2. Ogma (`ogma standalone --input-format fcs --prop-format smv`) turns it into a Copilot program; GHC runs that
     program, and Copilot writes the C99 monitor (`monitor.c`, `monitor.h`): one `step()` per tick, and a handler
     call whenever a requirement is violated. The generated code stays in a temporary folder: it is not committed and
     goes nowhere near the firmware (TE-03 OI-3).
  3. `harness.c` runs panda's `engaged_mismatch.h` and `heartbeat_siren.h` (the pinned submodule) in the order of
     `safety_task_handler()`, scripted and random scenarios, with the monitor watching. MUTANTS change one constant
     of the code each, to show that the monitor catches a defect.
  4. Write `monitor-results.md`; `--check` fails if it, or the spec, differs from a fresh run.

    python3 assurance/models/fret/monitor/run_monitor.py           # write
    python3 assurance/models/fret/monitor/run_monitor.py --check   # compare

Needs Ogma and GHC with the Copilot libraries (TE-03 P4 setup), gcc, PyYAML and the panda submodule.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FRET = HERE.parent
REPO = FRET.parent.parent.parent
SOURCE = FRET / "tsr-fretish.yaml"
FORMULAS = FRET / "fretish-formalizations.json"
SPEC = HERE / "monitor-spec.json"
OUTPUT = HERE / "monitor-results.md"
HARNESS = HERE / "harness.c"
PANDA_DRIVERS = REPO / "panda" / "board" / "drivers"
HEADERS = ["engaged_mismatch.h", "heartbeat_siren.h"]
MONITORED = ["FR-307a", "FR-516c", "FR-516-duration"]
FRET_TYPES = {"bool": "bool", "int": "integer", "mode": "bool"}
OGMA = os.environ.get("OGMA", "ogma")

# (label, header, constant, original value, mutated value, the requirement expected to catch it)
MUTANTS = [
  ("revocation 0.45 s instead of 0.3 s", "engaged_mismatch.h", "ENGAGED_MISMATCH_REVOKE_TICKS", "30U", "45U", "FR-307a"),
  ("siren 1.2 s after the first not-engaged heartbeat instead of 0.5 s", "engaged_mismatch.h",
   "ENGAGED_MISMATCH_SIREN_TICKS", "50U", "120U", "FR-516c"),
  ("siren held 2 s instead of 3 s", "heartbeat_siren.h", "HEARTBEAT_SIREN_HOLD_TICKS", "300U", "200U", "FR-516-duration"),
]


def handler_id(rid: str) -> str:
  return re.sub(r"[^A-Za-z0-9_]", "_", rid)


def spec() -> str:
  data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
  formulas = json.loads(FORMULAS.read_text(encoding="utf-8"))["requirements"]
  glossary = {g["name"]: g for g in data["glossary"]}
  reqs = {r["id"]: r for r in data["requirements"]}
  names = sorted({n for rid in MONITORED for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formulas[rid]["pt"])
                  if n in glossary}, key=list(glossary).index)
  out = {"RTSASpec": {
    "Internal_variables": [],
    "Other_variables": [{"name": n, "type": FRET_TYPES[glossary[n]["type"]]} for n in names],
    "Requirements": [{"name": handler_id(rid), "fretish": reqs[rid]["fretish"], "CoCoSpecCode": formulas[rid]["lustre"],
                      "ptLTL": formulas[rid]["pt"]} for rid in MONITORED],
  }}
  return json.dumps(out, indent=2) + "\n"


def run(cmd: list[str], cwd: Path, timeout: int = 900) -> str:
  proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
  if proc.returncode != 0:
    raise RuntimeError(f"{' '.join(cmd[:3])} failed: {(proc.stderr or proc.stdout).strip()[-800:]}")
  return proc.stdout


def generate_monitor(work: Path, spec_text: str) -> Path:
  (work / "monitor-spec.json").write_text(spec_text, encoding="utf-8")
  gen = work / "gen"
  run([OGMA, "standalone", "--input-file", "monitor-spec.json", "--input-format", "fcs", "--prop-format", "smv",
       "--target-dir", str(gen), "--target-file-name", "monitor"], work)
  copilot = next(gen.glob("*.hs"))
  run(["runghc", copilot.name], gen)
  if not (gen / "monitor.c").exists():
    raise RuntimeError(f"Copilot wrote no monitor.c in {gen}: {sorted(p.name for p in gen.iterdir())}")
  return gen


def handlers_c(gen: Path) -> str:
  names = re.findall(r"void\s+(handler\w*)\s*\(\s*void\s*\)\s*;", (gen / "monitor.h").read_text(encoding="utf-8"))
  if not names:
    raise RuntimeError("no handler declarations in monitor.h")
  lines = ["#include <stdbool.h>", "#include <stdint.h>", "#include \"monitor.h\"",
           f"const int handler_total = {len(names)};",
           "const char *const handler_names[] = {" + ", ".join(f'"{n}"' for n in names) + "};",
           f"long handler_first[{len(names)}];", "extern long current_tick;"]
  lines += [f"void {n}(void) {{ if (handler_first[{i}] < 0) {{ handler_first[{i}] = current_tick; }} }}"
            for i, n in enumerate(names)]
  return "\n".join(lines) + "\n"


def build_and_run(work: Path, gen: Path, drivers: Path, label: str) -> list[list[str]]:
  (work / "harness_handlers.c").write_text(handlers_c(gen), encoding="utf-8")
  exe = work / f"harness-{label}"
  run(["gcc", "-std=c99", "-O1", "-Wall", "-Werror", "-Wno-unused-function", f"-I{drivers}", f"-I{gen}",
       str(HARNESS), str(gen / "monitor.c"), str(work / "harness_handlers.c"), "-o", str(exe)], work)
  total = int(run([str(exe)], work).strip())
  return [run([str(exe), str(i)], work, timeout=300).strip().split("|") for i in range(total)]


def requirement_of(handler: str) -> str:
  for rid in MONITORED:
    if handler_id(rid) in handler:
      return rid
  return handler


def first_violations(row: list[str]) -> dict[str, int]:
  """Fields: name, ticks, revocations, siren starts, revoked after, siren after, then handler=first tick (-1: none)."""
  return {requirement_of(k): int(v) for k, v in (c.split("=") for c in row[6:])}


def page(base: list[list[str]], mutants: list[tuple]) -> str:
  lines = [
    "# Runtime monitors from the FRETish requirements (TE-03 P4)",
    "",
    "> Generated by [`run_monitor.py`](run_monitor.py); do not edit by hand. AI-drafted, not reviewed. "
    "No evidence credit: the harness is not the vehicle, and the generated monitor is not part of the firmware.",
    "",
    f"NASA Ogma turned FRET's past-time formulas for {', '.join(MONITORED)} ([`monitor-spec.json`](monitor-spec.json)) "
    "into a Copilot program, and Copilot generated a C99 monitor from it. [`harness.c`](harness.c) runs the panda's own "
    f"{' and '.join(f'`{h}`' for h in HEADERS)} (pinned submodule) in the order of `safety_task_handler()`, one 100 Hz "
    "tick at a time, and the monitor watches every tick. A violation is one call of the monitor's handler for that "
    "requirement. FRET's past-time formulas hold \"historically\" (H), so a violated requirement stays violated: the "
    "tables give the tick of the first violation.",
    "",
    "## The code as pinned",
    "",
    "| Scenario | Ticks | Revocations | Siren starts | Revoked after (ticks) | Siren after (ticks) | "
    + " | ".join(f"{r} first violated" for r in MONITORED) + " |",
    "|---|---|---|---|---|---|" + "---|" * len(MONITORED),
  ]
  for row in base:
    v = first_violations(row)
    rev = "—" if row[4] in ("", "-1") else row[4]
    sir = "—" if row[5] in ("", "-1") else row[5]
    lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {rev} | {sir} | "
                 + " | ".join("never" if v.get(r, -1) < 0 else f"tick {v[r]}" for r in MONITORED) + " |")
  lines += ["", "Revoked and siren after: ticks (10 ms) from the first \"not engaged\" heartbeat in the scripted scenarios; "
            "— means none. Each scenario runs in its own process, because the generated monitor has no reset. The random "
            "scenarios start not-engaged episodes of 0.1 to 1.2 s at 2 % of the heartbeats, drop and restore PCM cruise "
            "about every 4 s and re-grant authority, so they exercise the revocation and the siren repeatedly (counts "
            "above).", "",
            "## Defects injected on purpose", "",
            "Each mutant changes one constant of the code. The monitor of the requirement it breaks must report it.", "",
            "| Mutant | Constant | Expected | Scenarios that violate it | Other requirements violated | Caught |",
            "|---|---|---|---|---|---|"]
  for label, header, const, old, new, expect, rows in mutants:
    hit = [r[0] for r in rows if first_violations(r).get(expect, -1) >= 0]
    others = sorted({q for r in rows for q, t in first_violations(r).items() if t >= 0 and q != expect})
    lines.append(f"| {label} | `{const}` {old} → {new} (`{header}`) | {expect} | {len(hit)} of {len(rows)} | "
                 f"{', '.join(others) or 'none'} | {'yes' if hit else '**no**'} |")
  return "\n".join(lines) + "\n"


def analyse() -> tuple[str, str]:
  spec_text = spec()
  for h in HEADERS:
    if not (PANDA_DRIVERS / h).exists():
      raise RuntimeError(f"no {PANDA_DRIVERS / h}; run git submodule update --init panda")
  with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    gen = generate_monitor(work, spec_text)
    base = build_and_run(work, gen, PANDA_DRIVERS, "pinned")
    mutants = []
    for label, header, const, old, new, expect in MUTANTS:
      drivers = work / f"drivers-{const}"
      drivers.mkdir()
      for h in HEADERS:
        shutil.copy(PANDA_DRIVERS / h, drivers / h)
      text = (drivers / header).read_text(encoding="utf-8")
      pattern = rf"(#define {const}\s+){old}\b"
      if len(re.findall(pattern, text)) != 1:
        raise RuntimeError(f"{const} {old} not found once in {header}")
      (drivers / header).write_text(re.sub(pattern, rf"\g<1>{new}", text), encoding="utf-8")
      mutants.append((label, header, const, old, new, expect, build_and_run(work, gen, drivers, const)))
  return spec_text, page(base, mutants)


def main(argv: list[str]) -> int:
  spec_text, text = analyse()
  if "--check" in argv:
    stale = [p.name for p, body in ((SPEC, spec_text), (OUTPUT, text))
             if not p.exists() or p.read_text(encoding="utf-8") != body]
    if stale:
      print(f"run_monitor: stale {', '.join(stale)}; run run_monitor.py", file=sys.stderr)
      return 1
    print("run_monitor: spec and results current")
    return 0
  SPEC.write_text(spec_text, encoding="utf-8")
  OUTPUT.write_text(text, encoding="utf-8")
  print(f"run_monitor: wrote {SPEC.name} and {OUTPUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
