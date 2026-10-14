#!/usr/bin/env python3
"""Check the state-machine records and generate the WP-W-05 §5 tables from them (RR-2026-009 F-16).

Records: assurance/05-software/state-machines/*.yaml. Each is the normative source of one WP-W-05 §5
table. Implementation state is not stored in the records; it is read from the WP-W-02 Baseline column
(trace/items/swsr.yaml) of the SWSRs each transition cites.

Checks:
  S1  every state used by a transition is declared ("any", "same" and "m" are placeholders)
  S2  every declared state is reachable from the initial state
  S3  transitions with the same source, event and build overlap must declare each other in exclusive_with
  S4  every transition cites at least one SWSR, and every cited SWSR exists in swsr.yaml
  S5  (warning) code citation and WP-W-02 Baseline disagree: "not implemented" here but implemented there,
      or the other way round
  S6  (warning, authority machines only) an envelope SWSR whose text requires clearing or revoking authority
      is not realised by any transition (a record may list reasoned exceptions under s6_exempt)
  S7  (warning) a transition without an SWSR that records the requirement gap in its "gap" field (without a
      "gap" field an empty swsr list is an S4 error)

S1-S4 are errors (exit 1). S5, S6 and S7 are findings for the engineer and do not fail the run.

Usage:
  python3 assurance/trace/tools/check_state_machines.py           # check, print findings
  python3 assurance/trace/tools/check_state_machines.py --write   # also regenerate the WP-W-05 §5 blocks
  python3 assurance/trace/tools/check_state_machines.py --check   # also fail if those blocks are out of date
Standard library only; PyYAML is used if importable.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ASSURANCE = TOOLS.parent.parent
SM_DIR = ASSURANCE / "05-software" / "state-machines"
SWSR_YAML = ASSURANCE / "trace" / "items" / "swsr.yaml"
WP_W05 = ASSURANCE / "05-software" / "WP-W-05-software-unit-design.md"
PLACEHOLDERS = {"any", "same", "m"}
BLOCKS = {"SM-SAFETY-MODE": "sm-safety-mode", "SM-TOY-AUTH": "sm-toy-auth", "SM-SELFDRIVED": "sm-selfdrived"}


# ---------------------------------------------------------------- loading

def _split_top(s: str, sep: str = ",") -> list[str]:
  out, depth, quote, cur = [], 0, False, ""
  for ch in s:
    if ch == '"':
      quote = not quote
    elif not quote and ch in "[{":
      depth += 1
    elif not quote and ch in "]}":
      depth -= 1
    if ch == sep and depth == 0 and not quote:
      out.append(cur)
      cur = ""
    else:
      cur += ch
  if cur.strip():
    out.append(cur)
  return out


def _value(v: str):
  v = v.strip()
  if v.startswith('"') and v.endswith('"'):
    return v[1:-1].replace('\\"', '"')
  if v.startswith("[") and v.endswith("]"):
    return [_value(x) for x in _split_top(v[1:-1])]
  if v.startswith("{") and v.endswith("}"):
    d = {}
    for part in _split_top(v[1:-1]):
      k, _, val = part.partition(":")
      d[k.strip()] = _value(val)
    return d
  return v


def _load_subset(text: str) -> dict:
  """Top-level 'key: value' lines and 'key:' followed by '  - {flow map}' items."""
  doc: dict = {}
  key = None
  for raw in text.splitlines():
    line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
    if not line.strip():
      continue
    if line.startswith("  - "):
      doc[key].append(_value(line[4:]))
      continue
    k, _, v = line.partition(":")
    key = k.strip()
    doc[key] = _value(v) if v.strip() else []
  return doc


def load(path: Path) -> dict:
  text = path.read_text(encoding="utf-8")
  try:
    import yaml  # type: ignore
    return yaml.safe_load(text)
  except ImportError:
    return _load_subset(text)


def swsr_records() -> dict[str, dict]:
  out = {}
  for rec in re.split(r"\n(?=- id: )", SWSR_YAML.read_text(encoding="utf-8")):
    m = re.search(r"^- id: (SWSR-\S+)", rec, re.M)
    if not m:
      continue
    def f(k, rec=rec):
      mm = re.search(rf'^  {k}: "(.*)"$', rec, re.M)
      return mm.group(1) if mm else ""
    out[m.group(1)] = {"text": f("text"), "baseline": f("baseline_impl"),
                       "withdrawn": "status: withdrawn" in rec}
  return out


def impl_state(baseline: str) -> str:
  b = baseline.lstrip("*")
  for prefix, state in (("Not impl", "not"), ("Not met", "not"), ("Partial", "partial"), ("Impl", "impl"),
                        ("Met", "impl"), ("Not verified", "impl")):
    if b.startswith(prefix):
      return state
  return "unknown"


LABEL = {"impl": "Implemented", "partial": "Partial", "not": "Not implemented", "unknown": "Not assessed"}


def transition_state(t: dict, sw: dict) -> str:
  states = [impl_state(sw[s]["baseline"]) for s in t.get("swsr", []) if s in sw]
  if states and all(s == "impl" for s in states):
    return "impl"
  if any(s in ("impl", "partial") for s in states):
    return "partial"
  return "not" if states else "unknown"


# ---------------------------------------------------------------- checks

def _sources(t: dict, states: list[str]) -> list[str]:
  src = t["from"]
  return list(states) if src == "any" else [s.strip() for s in src.split(",")]


def _builds_overlap(a: str, b: str) -> bool:
  return a == b or "all" in (a, b)


def check(sm: dict, sw: dict) -> tuple[list[str], list[str]]:
  errors, warnings = [], []
  states = sm["states"]
  T = sm["transitions"]
  name = sm["machine"]
  for t in T:
    for s in [*_sources(t, states), t["to"]]:
      if s not in states and s not in PLACEHOLDERS:
        errors.append(f"S1 {name} {t['id']}: undeclared state {s}")
  reach, changed = {sm["initial"]}, True
  while changed:
    changed = False
    for t in T:
      if set(_sources(t, states)) & reach:
        targets = states if t["to"] == "m" else ([] if t["to"] == "same" else [t["to"]])
        for s in targets:
          if s not in reach:
            reach.add(s)
            changed = True
  for s in states:
    if s not in reach:
      errors.append(f"S2 {name}: state {s} unreachable from {sm['initial']}")
  for i, a in enumerate(T):
    for b in T[i + 1:]:
      if a["event"] != b["event"] or not set(_sources(a, states)) & set(_sources(b, states)):
        continue
      ba, bb = a.get("build", "all"), b.get("build", "all")
      if not _builds_overlap(ba, bb):
        continue  # e.g. reference vs upstream: never in the same build
      if b["id"] not in a.get("exclusive_with", []) or a["id"] not in b.get("exclusive_with", []):
        errors.append(f"S3 {name}: {a['id']} and {b['id']} share source and event '{a['event']}' "
                      + "but are not declared mutually exclusive")
  for t in T:
    if not t.get("swsr"):
      if t.get("gap"):
        warnings.append(f"S7 {name} {t['id']}: no SWSR (gap: {t['gap']})")
      else:
        errors.append(f"S4 {name} {t['id']}: no SWSR reference")
    for s in t.get("swsr", []):
      if s not in sw:
        errors.append(f"S4 {name} {t['id']}: {s} not in swsr.yaml")
  for t in T:
    code_missing = t.get("code", "").startswith("not implemented")
    st = transition_state(t, sw)
    if code_missing and st in ("impl", "partial"):
      warnings.append(f"S5 {name} {t['id']}: code says not implemented, WP-W-02 says {LABEL[st]} for "
                      + ", ".join(t["swsr"]))
    if not code_missing and st == "not":
      warnings.append(f"S5 {name} {t['id']}: code cited ({t.get('code')}) but WP-W-02 says not implemented for "
                      + ", ".join(t["swsr"]) + " (the transition exists but does not meet the SWSR)")
  if "ALLOWED" in states:
    cited = {s for t in T for s in t.get("swsr", [])}
    for sid, rec in sw.items():
      if rec["withdrawn"] or sid.endswith("h") or sid.startswith("SWSR-6"):
        continue
      exempt = {e["swsr"] for e in sm.get("s6_exempt", [])}
      if re.search(r"clear (all |lateral |longitudinal )?authority|revoke", rec["text"]) and sid not in cited \
         and sid not in exempt:
        nr = [n for n in sm.get("non_revoking", []) if sid in n.get("swsr", [])]
        note = f" (the code only does: {nr[0]['reaction']})" if nr else ""
        warnings.append(f"S6 {name}: {sid} requires clearing authority but no transition realises it{note}")
  return errors, warnings


# ---------------------------------------------------------------- generation

def _cell(s: str) -> str:
  return str(s).replace("|", "\\|") or "—"


def render(sm: dict, sw: dict) -> str:
  T = sm["transitions"]
  lines = [f"Generated from [`state-machines/{BLOCKS[sm['machine']]}.yaml`](state-machines/{BLOCKS[sm['machine']]}.yaml) "
           + "by `assurance/trace/tools/check_state_machines.py --write`; do not edit by hand. Status is taken from the "
           + "WP-W-02 Baseline column of the cited SWSRs (\"Implemented\" = code changed and host tests pass, not verified "
           + "on hardware). Build: all, reference (`LIONDRIVER_REFERENCE=1` only) or upstream (without it).",
           "",
           "| # | Current | Event | Guard | Action | Next | Build | SWSR | Status | Code |",
           "|---|---|---|---|---|---|---|---|---|---|"]
  for t in T:
    sws = ", ".join(s.replace("SWSR-", "") for s in t.get("swsr", [])) or ("gap" if t.get("gap") else "")
    lines.append("| " + " | ".join(_cell(x) for x in (
      t["id"], t["from"], t["event"], t.get("guard", ""), t.get("action", ""), t["to"], t.get("build", "all"),
      sws, LABEL[transition_state(t, sw)], t.get("code", ""))) + " |")
  gaps = [t for t in T if not t.get("swsr") and t.get("gap")]
  if gaps:
    lines += ["", "Transitions without an SWSR (requirement gaps, checker finding S7):", "",
              "| # | Gap |", "|---|---|"]
    for t in gaps:
      lines.append(f"| {_cell(t['id'])} | {_cell(t['gap'])} |")
  if sm.get("non_revoking"):
    lines += ["", "Reactions that do **not** change the state:", "",
              "| Event | Reaction | Build | SWSR | Code |", "|---|---|---|---|---|"]
    for n in sm["non_revoking"]:
      lines.append("| " + " | ".join(_cell(x) for x in (
        n["event"], n["reaction"], n.get("build", "all"), ", ".join(s.replace("SWSR-", "") for s in n["swsr"]),
        n.get("code", ""))) + " |")
  lines += ["", "```mermaid", "stateDiagram-v2", f"  [*] --> {sm['initial']}"]
  for t in T:
    if t["to"] in ("same", "m"):
      continue
    for s in _sources(t, sm["states"]):
      if s == t["to"] and t.get("action") == "none":
        continue
      lines.append(f"  {s} --> {t['to']}: {t['id']}")
  lines.append("```")
  return "\n".join(lines)


def blocks(sms: list[dict], sw: dict, text: str) -> str:
  for sm in sms:
    tag = BLOCKS[sm["machine"]]
    begin = f"<!-- BEGIN GENERATED: {tag} (assurance/trace/tools/check_state_machines.py) -->"
    end = f"<!-- END GENERATED: {tag} -->"
    if begin not in text or end not in text:
      raise SystemExit(f"WP-W-05: markers for {tag} not found")
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    text = head + begin + "\n" + render(sm, sw) + "\n" + end + tail
  return text


def main(argv: list[str]) -> int:
  sw = swsr_records()
  sms = [load(p) for p in sorted(SM_DIR.glob("*.yaml"))]
  n_err = 0
  for sm in sms:
    errors, warnings = check(sm, sw)
    n_err += len(errors)
    print(f"{sm['machine']}: {len(sm['states'])} states, {len(sm['transitions'])} transitions, "
          + f"{len(errors)} errors, {len(warnings)} findings")
    for e in errors:
      print("  ERROR " + e)
    for w in warnings:
      print("  finding " + w)
  current = WP_W05.read_text(encoding="utf-8")
  expected = blocks(sms, sw, current)
  if "--write" in argv and expected != current:
    WP_W05.write_text(expected, encoding="utf-8")
    print(f"wrote {WP_W05.relative_to(ASSURANCE.parent)}")
  elif "--check" in argv and expected != current:
    print("ERROR WP-W-05 §5 tables are out of date; run with --write")
    n_err += 1
  print("OK: state machines consistent" if n_err == 0 else f"FAILED: {n_err} errors")
  return 1 if n_err else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
