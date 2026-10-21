#!/usr/bin/env python3
"""TE-03 step P3: check that the FRETish requirements can be met together (realizability), with Kind 2.

For the restated TSRs this asks: is there any envelope that meets every guarantee for every behaviour of its inputs
that the assumptions allow? An unrealizable set means two requirements demand opposite outputs in some reachable
situation, so the text contradicts itself, whatever the code does.

The contract is built the way FRET's own realizability check builds it:
  * FRET's past-time Lustre form of each requirement (`lustre` in `fretish-formalizations.json`, FRET's CoCoSpecCode);
  * inputs and outputs from the glossary `role`; requirements whose id contains "assumption" become `assume`;
  * one contract per connected component (requirements linked through shared outputs, as in FRET's compositional
    analysis), with the assumptions that share a variable with it;
  * rendered by FRET's own Kind 2 template (support/RealizabilityTemplates/kind2) through `render_contract.js`, and
    checked with `kind2 -json --enable CONTRACTCK`, as FRET runs it.
One change to FRET's output: Kind 2 v2.2.0 stops with an internal assertion (lustreAstNormalizer.ml:106) when an
`assume` names a contract ghost variable, which is how the template declares every requirement (FRET marks
assumptions experimental). Each assumption's formula is therefore written into its `assume` clause instead of a
ghost variable; the formula itself is FRET's, unchanged.
For an unrealizable component, guarantees are dropped one at a time while the rest stays unrealizable: what remains is
a minimal conflicting set. Kind 2 runtimes are not written, so the page is deterministic.

    FRET_DIR=.fret/fret-electron python3 assurance/models/fret/fret_realizability.py           # write the page
    FRET_DIR=.fret/fret-electron python3 assurance/models/fret/fret_realizability.py --check   # fail if it differs

Needs Node.js, FRET (install_fret.sh), Kind 2 v2.2.0 and Z3 4.14.1 on PATH (install_solvers.sh), and PyYAML.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tsr-fretish.yaml"
FORMULAS = HERE / "fretish-formalizations.json"
OUTPUT = HERE / "fret-realizability.md"
LUSTRE_DIR = HERE / "realizability"
RENDER = HERE / "render_contract.js"
TIMEOUT_S = int(os.environ.get("KIND2_TIMEOUT", "300"))
LUSTRE_TYPES = {"bool": "bool", "int": "int", "mode": "bool"}
DURATION = re.compile(r"\b(?:within|for|after) (\d+) ticks?\b", re.I)
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def lustre_id(rid: str) -> str:
  return re.sub(r"[^a-zA-Z0-9_~]", "_", rid)


def components(reqs: list[dict], uses: dict[str, set[str]], outputs: set[str]) -> list[list[dict]]:
  """Group the guarantees that share an output; each assumption joins every group it shares a variable with."""
  guarantees = [r for r in reqs if "assumption" not in r["id"].lower()]
  parent = {r["id"]: r["id"] for r in guarantees}

  def find(x):
    while parent[x] != x:
      parent[x] = parent[parent[x]]
      x = parent[x]
    return x

  owner: dict[str, str] = {}
  for r in guarantees:
    for v in sorted(uses[r["id"]] & outputs):
      if v in owner:
        parent[find(r["id"])] = find(owner[v])
      else:
        owner[v] = r["id"]
  groups: dict[str, list[dict]] = {}
  for r in guarantees:
    groups.setdefault(find(r["id"]), []).append(r)
  out = []
  for members in groups.values():
    names = set().union(*(uses[r["id"]] for r in members))
    out.append(members + [a for a in reqs if "assumption" in a["id"].lower() and uses[a["id"]] & names])
  return sorted(out, key=lambda g: [r["id"] for r in reqs].index(g[0]["id"]))


def contract(name: str, members: list[dict], uses: dict[str, set[str]], glossary: dict, formulas: dict) -> dict:
  names = set().union(*(uses[r["id"]] for r in members))
  ordered = [g for g in glossary if g in names]
  delays = sorted({m for r in members for m in DURATION.findall(r["fretish"])}, key=int)
  return {
    "componentName": name,
    "inputVariables": [{"name": v, "type": LUSTRE_TYPES[glossary[v]["type"]]} for v in ordered if glossary[v]["role"] == "input"],
    "outputVariables": [{"name": v, "type": LUSTRE_TYPES[glossary[v]["type"]]} for v in ordered if glossary[v]["role"] == "output"],
    "internalVariables": [], "assignments": [], "modes": [], "delays": delays,
    "properties": [{"reqid": r["id"], "fullText": r["fretish"], "value": formulas[r["id"]]["lustre"]} for r in members],
  }


def render(fret_dir: Path, data: dict) -> str:
  run = subprocess.run(["node", str(RENDER), str(fret_dir)], input=json.dumps(data), capture_output=True, text=True,
                       timeout=120, check=False)
  if run.returncode != 0:
    raise RuntimeError(f"render_contract.js failed: {run.stderr.strip()[-400:]}")
  lustre = run.stdout
  for prop in data["properties"]:
    if "assumption" in prop["reqid"].lower():
      ident = lustre_id(prop["reqid"])
      decl = f"var {ident} : bool = {prop['value']};"
      if lustre.count(decl) != 1 or lustre.count(f"assume {ident};") != 1:
        raise RuntimeError(f"unexpected template output for {prop['reqid']}")
      lustre = lustre.replace(decl, "").replace(f"assume {ident};", f"assume {prop['value']};")
  return lustre


def kind2(lustre: str, top: str) -> str:
  with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / f"{top}.lus"
    path.write_text(lustre, encoding="utf-8")
    run = subprocess.run(["kind2", "-json", "--enable", "CONTRACTCK", "--timeout", str(TIMEOUT_S), str(path)],
                         capture_output=True, text=True, timeout=TIMEOUT_S + 120, check=False)
  try:
    objects = json.loads(run.stdout)
  except json.JSONDecodeError as exc:
    raise RuntimeError(f"kind2 gave no JSON: {run.stderr.strip()[-400:] or run.stdout[-400:]}") from exc
  current, result = None, "unknown"
  for o in objects:
    if o.get("objectType") == "analysisStart":
      current = (o.get("top"), o.get("context"))
    elif o.get("objectType") == "realizabilityCheck" and current == (top, "contract"):
      result = o.get("result", "unknown")
    elif o.get("level") == "fatal" and o.get("value") != "Wallclock timeout.":
      raise RuntimeError(f"kind2 failed on {top}: {o.get('value')}")
  return result


def minimal_conflicts(fret_dir: Path, name: str, members: list[dict], uses, glossary, formulas) -> list[list[str]]:
  """Every minimal set of guarantees that is unrealizable with the component's assumptions.

  Deletion finds one minimal set; then each of its guarantees is removed in turn, and any remainder that is still
  unrealizable is searched the same way, until no new set appears."""
  assumptions = [m for m in members if "assumption" in m["id"].lower()]
  cache: dict[frozenset, bool] = {}

  def unrealizable(ids: frozenset) -> bool:
    if ids not in cache:
      chosen = [m for m in members if m["id"] in ids] + assumptions
      cache[ids] = kind2(render(fret_dir, contract(name, chosen, uses, glossary, formulas)), name) == "unrealizable"
    return cache[ids]

  def shrink(ids: frozenset) -> frozenset:
    for rid in [m["id"] for m in members if m["id"] in ids]:
      if unrealizable(ids - {rid}):
        ids = ids - {rid}
    return ids

  found: list[frozenset] = []
  todo = [frozenset(m["id"] for m in members if m not in assumptions)]
  seen: set[frozenset] = set()
  while todo:
    ids = todo.pop(0)
    if ids in seen or not unrealizable(ids):
      continue
    seen.add(ids)
    core = shrink(ids)
    if core not in found:
      found.append(core)
    todo += [ids - {rid} for rid in sorted(core)]
  order = [m["id"] for m in members]
  return sorted(([r for r in order if r in core] for core in found), key=lambda c: [order.index(r) for r in c])


def analyse(fret_dir: Path) -> tuple[str, dict[str, str]]:
  data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
  formulas = json.loads(FORMULAS.read_text(encoding="utf-8"))["requirements"]
  glossary = {g["name"]: g for g in data["glossary"]}
  reqs = data["requirements"]
  uses = {r["id"]: set(NAME.findall(formulas[r["id"]]["lustre"])) & set(glossary) for r in reqs}
  outputs = {n for n, g in glossary.items() if g["role"] == "output"}
  rows, files = [], {}
  for i, members in enumerate(components(reqs, uses, outputs)):
    name = f"envelope_cc{i}"
    lustre = render(fret_dir, contract(name, members, uses, glossary, formulas))
    files[f"{name}.lus"] = lustre
    result = kind2(lustre, name)
    conflict = minimal_conflicts(fret_dir, name, members, uses, glossary, formulas) if result == "unrealizable" else []
    rows.append((name, members, result, conflict))
  return page(rows, glossary, uses), files


def page(rows, glossary, uses) -> str:
  lines = [
    "# Realizability of the FRETish requirements (TE-03 P3)",
    "",
    "> Generated by [`fret_realizability.py`](fret_realizability.py) with FRET's Kind 2 template and Kind 2 v2.2.0 "
    "(Z3 4.14.1); do not edit by hand. AI-drafted, not reviewed. No evidence credit.",
    "",
    "Realizable: some envelope meets every guarantee of the component for every input behaviour its assumptions allow. "
    "Unrealizable: the requirements contradict each other; the minimal conflicting set names the ones that do. "
    "Components follow FRET's compositional analysis (guarantees linked through a shared output). The Lustre contracts "
    f"are in [`realizability/`](realizability/). Kind 2 timeout {TIMEOUT_S} s.",
    "",
    "| Component | Outputs | Requirements | Assumptions | Result | Minimal conflicting sets |",
    "|---|---|---|---|---|---|",
  ]
  for name, members, result, conflict in rows:
    outs = sorted(set().union(*(uses[r["id"]] for r in members)) & {n for n, g in glossary.items() if g["role"] == "output"})
    gs = [r["id"] for r in members if "assumption" not in r["id"].lower()]
    as_ = [r["id"] for r in members if "assumption" in r["id"].lower()]
    lines.append(f"| [{name}](realizability/{name}.lus) | {', '.join(f'`{o}`' for o in outs)} | {', '.join(gs)} | "
                 f"{', '.join(as_) or '—'} | **{result}** | {'; '.join('{' + ', '.join(c) + '}' for c in conflict) or '—'} |")
  return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
  fret_dir = Path(os.environ.get("FRET_DIR", ".fret/fret-electron")).resolve()
  if not (fret_dir / "support" / "RealizabilityTemplates" / "kind2" / "Complete.ejs").exists():
    print(f"fret_realizability: no FRET in {fret_dir}; run install_fret.sh first", file=sys.stderr)
    return 2
  text, files = analyse(fret_dir)
  if "--check" in argv:
    stale = [OUTPUT.name] if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text else []
    stale += [f"realizability/{n}" for n, body in files.items()
              if not (LUSTRE_DIR / n).exists() or (LUSTRE_DIR / n).read_text(encoding="utf-8") != body]
    stale += [f"realizability/{p.name}" for p in LUSTRE_DIR.glob("*.lus") if p.name not in files]
    if stale:
      print(f"fret_realizability: stale {', '.join(stale)}; run fret_realizability.py", file=sys.stderr)
      return 1
    print(f"fret_realizability: {len(files)} components; page and contracts current")
    return 0
  LUSTRE_DIR.mkdir(exist_ok=True)
  for p in LUSTRE_DIR.glob("*.lus"):
    p.unlink()
  for n, body in files.items():
    (LUSTRE_DIR / n).write_text(body, encoding="utf-8")
  OUTPUT.write_text(text, encoding="utf-8")
  print(f"fret_realizability: wrote {OUTPUT.name} and {len(files)} contracts")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
