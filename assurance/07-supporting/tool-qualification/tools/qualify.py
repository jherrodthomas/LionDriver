#!/usr/bin/env python3
"""Run the validation of TQR-32: plant every fault of the catalogue in a copy of the real trace data, run
check_trace.py (WP-P-07 TL-32) on it, and show that each fault is reported by the check it belongs to.

Two parts, both on the committed trace data (assurance/trace/items and links), never on a toy set:

  1. Planted faults (guard TG-01). The unchanged data must pass with no error. Then each fault of
     TQR-32/faults.yaml is planted alone in a fresh copy; it is caught when check_trace.py reports an error with
     the expected check tag whose text contains the expected phrase.
  2. Tool mutants. The validation is only worth something if it would notice a broken tool. Each mutant switches
     off or weakens one part of check_trace.py in memory (the file is never changed). A mutant is killed when the
     unchanged data no longer passes or at least one planted fault goes unreported. Every mutant must be killed.

It writes TQR-32/results.md (the evidence table of the report) and TQR-32/results.json (for the figures).

    python3 tools/qualify.py            # run, write the results
    python3 tools/qualify.py --check    # run, fail if a fault is missed, a mutant survives or a result is stale

Needs PyYAML (pinned in assurance/trace/requirements.txt, WP-P-07 TL-55). Output is deterministic.
"""
from __future__ import annotations

import contextlib
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
TQR = FOLDER / "TQR-32"
ASSURANCE = FOLDER.parents[1]
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import check_trace as ct  # noqa: E402

FAULTS = TQR / "faults.yaml"
OUT_MD, OUT_JSON = TQR / "results.md", TQR / "results.json"
TOOL = "assurance/trace/tools/check_trace.py"


class QualifyError(ValueError):
  pass


# ---------------------------------------------------------------- the data and one run of the tool

def load_real() -> tuple[list[dict], list[dict]]:
  items: list[dict] = []
  for f in sorted(ct.ITEMS_DIR.glob("*.yaml")):
    data = ct.load_yaml(f)
    if not isinstance(data, list):
      raise QualifyError(f"{f.name}: top level is not a list")
    items += data
  return items, ct.load_yaml(ct.LINKS)


def run_tool(items: list[dict], links: list[dict], items_dir: Path) -> list[str]:
  """check_trace.main's sequence, on in-memory items, with X3 reading items_dir."""
  rep = ct.Report()
  by_id = ct.check_items(items, rep)
  ct.check_links(by_id, rep)
  ct.check_verification_links(by_id, links, rep)
  ct.check_interfaces(by_id, ct.load_yaml(ct.REVIEWS) if ct.REVIEWS.exists() else [], ct.interface_ids(), rep)
  ct.check_against_hara(by_id, rep)
  ct.check_against_itemdef(by_id, rep)
  saved = ct.ITEMS_DIR
  ct.ITEMS_DIR = items_dir
  try:
    ct.check_requirements_in_sync(rep)
  finally:
    ct.ITEMS_DIR = saved
  return rep.errors


# ---------------------------------------------------------------- planting a fault

def _find(items: list[dict], iid: str) -> dict:
  hits = [x for x in items if x.get("id") == iid]
  if len(hits) != 1:
    raise QualifyError(f"fault target {iid}: {len(hits)} items with that ID in the trace data (catalogue stale?)")
  return hits[0]


def plant(fault: dict, items: list[dict], links: list[dict], tmp: Path) -> Path:
  """Apply one fault to the copies; return the items directory X3 should read."""
  (name, a), = fault["op"].items()
  if name == "set":
    it = _find(items, a["item"])
    if a["field"] not in it:
      raise QualifyError(f"{fault['id']}: {a['item']} has no field {a['field']}")
    if it[a["field"]] == a["value"]:
      raise QualifyError(f"{fault['id']}: {a['item']}.{a['field']} already has the planted value")
    it[a["field"]] = a["value"]
  elif name == "delete":
    del _find(items, a["item"])[a["field"]]
  elif name == "unlink":
    n = 0
    for it in items:
      if a.get("kind") and it.get("kind") != a["kind"]:
        continue
      refs = it.get(a["field"]) or []
      if a["ref"] in refs:
        it[a["field"]] = [r for r in refs if r != a["ref"]]
        n += 1
    if not n:
      raise QualifyError(f"{fault['id']}: no item names {a['ref']} in {a['field']}")
  elif name == "copy":
    items.append(dict(copy.deepcopy(_find(items, a["item"])), **({"id": a["id"]} if "id" in a else {})))
  elif name == "new":
    if any(x.get("id") == a["value"]["id"] for x in items):
      raise QualifyError(f"{fault['id']}: {a['value']['id']} already exists")
    items.append(copy.deepcopy(a["value"]))
  elif name == "link":
    hits = [ln for ln in links if ln.get("test") == a["test"]]
    if len(hits) != 1:
      raise QualifyError(f"{fault['id']}: test {a['test']} is linked {len(hits)} times")
    hits[0]["reqs"] = list(a["reqs"])
  elif name == "edit":
    d = tmp / "items"
    shutil.copytree(ct.ITEMS_DIR, d)
    p = d / a["file"]
    text = p.read_text(encoding="utf-8")
    if text.count(a["find"]) != 1:
      raise QualifyError(f"{fault['id']}: the text to edit occurs {text.count(a['find'])} times in {a['file']}")
    p.write_text(text.replace(a["find"], a["replace"]), encoding="utf-8")
    return d
  else:
    raise QualifyError(f"{fault['id']}: unknown operation {name}")
  return ct.ITEMS_DIR


def load_faults() -> list[dict]:
  faults = yaml.safe_load(FAULTS.read_text(encoding="utf-8"))
  ids = [f["id"] for f in faults]
  if len(set(ids)) != len(ids):
    raise QualifyError("fault IDs are not unique")
  for f in faults:
    for k in ("id", "class", "what", "op", "expect", "match"):
      if k not in f:
        raise QualifyError(f"{f.get('id')}: no {k}")
    if len(f["op"]) != 1:
      raise QualifyError(f"{f['id']}: one operation per fault")
  return faults


def run_catalogue(faults: list[dict], items: list[dict], links: list[dict]) -> tuple[list[str], list[dict]]:
  base = run_tool(copy.deepcopy(items), copy.deepcopy(links), ct.ITEMS_DIR)
  out = []
  for f in faults:
    its, lks = copy.deepcopy(items), copy.deepcopy(links)
    with tempfile.TemporaryDirectory() as tmp:
      d = plant(f, its, lks, Path(tmp))
      errors = run_tool(its, lks, d)
    hit = [e for e in errors if e.startswith(f"[{f['expect']}]") and f["match"] in e]
    out.append({"id": f["id"], "class": f["class"], "what": f["what"], "expect": f["expect"], "caught": bool(hit),
                "report": hit[0] if hit else "", "errors": len(errors)})
  return base, out


# ---------------------------------------------------------------- tool mutants

@contextlib.contextmanager
def _patch(obj, name, value):
  old = getattr(obj, name)
  setattr(obj, name, value)
  try:
    yield
  finally:
    setattr(obj, name, old)


def _silence(tag: str):
  orig = ct.Report.err
  def err(self, check, msg):
    if check != tag:
      orig(self, check, msg)
  return _patch(ct.Report, "err", err)


MUTANTS = [
  ("TM-01", "R1 findings are dropped (a wrong hazardous-event ASIL goes unreported)", lambda: _silence("R1")),
  ("TM-02", "the ASIL inheritance check K5 does nothing", lambda: _patch(ct, "check_asil_inheritance",
                                                                          lambda *a, **k: None)),
  ("TM-03", "the refinement check (goal to FSR to TSR) does nothing", lambda: _patch(ct, "check_requirement_coverage",
                                                                                    lambda *a, **k: None)),
  ("TM-04", "every ASIL ranks the same", lambda: _patch(ct, "ASIL_ORDER", {k: 0 for k in ct.ASIL_ORDER})),
  ("TM-05", "test links are not checked", lambda: _patch(ct, "check_verification_links", lambda *a, **k: None)),
  ("TM-06", "generated files are not compared with the work products", lambda: _patch(ct, "check_requirements_in_sync",
                                                                                     lambda *a, **k: None)),
  ("TM-07", "any ID is accepted", lambda: _patch(ct, "ID_RE", __import__("re").compile(r".*"))),
  ("TM-08", "a missing mandatory key is not reported", lambda: _patch(ct, "REQUIRED", {k: [] for k in ct.REQUIRED})),
]


def run_mutants(faults, items, links) -> list[dict]:
  out = []
  for mid, what, make in MUTANTS:
    with make():
      base, res = run_catalogue(faults, items, links)
    missed = [r["id"] for r in res if not r["caught"]]
    out.append({"id": mid, "what": what, "killed": bool(base) or bool(missed), "baseline_errors": len(base),
                "missed": missed})
  return out


# ---------------------------------------------------------------- results

def build() -> dict:
  faults = load_faults()
  items, links = load_real()
  base, res = run_catalogue(faults, items, links)
  if base:
    raise QualifyError("the unchanged trace data does not pass check_trace.py: " + "; ".join(base[:3]))
  mut = run_mutants(faults, items, links)
  kinds: dict[str, int] = {}
  for it in items:
    kinds[it.get("kind")] = kinds.get(it.get("kind"), 0) + 1
  return {"tool": TOOL, "items": len(items), "links": len(links), "kinds": len(kinds), "faults": res,
          "mutants": mut}


def markdown(r: dict) -> str:
  caught = sum(f["caught"] for f in r["faults"])
  killed = sum(m["killed"] for m in r["mutants"])
  lines = ["<!-- GENERATED by tools/qualify.py from faults.yaml and a run of check_trace.py; do not edit -->", "",
           f"Run on the committed trace data: {r['items']} items of {r['kinds']} kinds and {r['links']} test links. "
           f"The unchanged data passes with no error.", "",
           f"**Planted faults: {caught} of {len(r['faults'])} caught.**", "",
           "| Fault | Error class | Planted | Check | Reported as |", "|---|---|---|---|---|"]
  for f in r["faults"]:
    rep = f["report"].replace("|", "\\|") if f["caught"] else "**missed**"
    if len(rep) > 110:
      rep = rep[:107] + "…"
    lines.append(f"| {f['id']} | {f['class']} | {f['what']} | {f['expect']} | `{rep}` |" if f["caught"]
                 else f"| {f['id']} | {f['class']} | {f['what']} | {f['expect']} | {rep} |")
  lines += ["", f"**Tool mutants: {killed} of {len(r['mutants'])} killed.**", "",
            "| Mutant | check_trace.py broken so that | Killed by |", "|---|---|---|"]
  for m in r["mutants"]:
    by = ", ".join(m["missed"]) if m["missed"] else (f"unchanged data fails ({m['baseline_errors']} errors)"
                                                     if m["baseline_errors"] else "")
    lines.append(f"| {m['id']} | {m['what']} | {by if m['killed'] else '**survived**'} |")
  return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
  try:
    r = build()
  except QualifyError as e:
    print(f"qualify: {e}", file=sys.stderr)
    return 1
  md, js = markdown(r), json.dumps(r, indent=1, ensure_ascii=False) + "\n"
  missed = [f["id"] for f in r["faults"] if not f["caught"]]
  survived = [m["id"] for m in r["mutants"] if not m["killed"]]
  bad = []
  if missed:
    bad.append(f"faults missed: {', '.join(missed)}")
  if survived:
    bad.append(f"mutants survived: {', '.join(survived)}")
  if "--check" in argv:
    for p, content in ((OUT_MD, md), (OUT_JSON, js)):
      if not p.exists() or p.read_text(encoding="utf-8") != content:
        bad.append(f"{p.name} is stale; run tools/qualify.py")
  else:
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(js, encoding="utf-8")
  if bad:
    print("qualify: " + "; ".join(bad), file=sys.stderr)
    return 1
  print(f"qualify: TQR-32 {len(r['faults'])} of {len(r['faults'])} faults caught, "
        f"{len(r['mutants'])} of {len(r['mutants'])} mutants killed")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
