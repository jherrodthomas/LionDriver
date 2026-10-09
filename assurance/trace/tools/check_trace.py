#!/usr/bin/env python3
"""Consistency checker for the LionDriver trace data (WP-T-01, WP-P-06 section 7).

Checks implemented so far (IDs per assurance/trace/README.md section 6):
  K1  item files parse and carry the mandatory keys for their kind
  K2  IDs are unique and match the ID pattern
  K3  every reference (parents, aou_dependency) resolves
  K12 every hazardous event is linked to a safety goal or has sg_exempt_reason
  R1  hazardous-event ASIL equals the risk-graph result of S, E, C
  R2  safety-goal ASIL equals the highest ASIL of its source hazardous events
  R3  asil_if_aou_fails is not lower than asil and only appears with aou_dependency
  R4  every hazard has at least one hazardous event
  X1  hazardous events and safety goals match the tables in WP-C-03
  X2  assumptions of use match the table in WP-C-01

Usage: python3 assurance/trace/tools/check_trace.py [--no-source-compare]
Exit code 0 when no errors, 1 otherwise.

Dependencies: Python standard library. PyYAML is used if importable; otherwise a
minimal parser for the restricted YAML subset in README section 4.1 is used.
PyYAML is not a direct LionDriver dependency at baseline 8b8c6ae (uv.lock lists it
only as an optional extra of tinygrad).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TRACE_DIR = Path(__file__).resolve().parent.parent
ASSURANCE_DIR = TRACE_DIR.parent
ITEMS_DIR = TRACE_DIR / "items"
HARA_MD = ASSURANCE_DIR / "02-concept" / "WP-C-03-hara.md"
ITEMDEF_MD = ASSURANCE_DIR / "02-concept" / "WP-C-01-item-definition.md"

ID_RE = re.compile(
  r"^((H|HE|HS|SG|FSR|TSR|SWSR|HWSR|SH|TC|FI|FM|SOTIF|AIR|DSR|MLR|MON|KS|DVR|DEV|TS|CSG|CSR|SYS|AOU)"
  r"-[0-9]{2,3}(\.[0-9]{1,2})?[a-z]?|VS-[A-Z]{2,4}-[0-9]{2,3}[a-z]?)$")
FUNC_RE = re.compile(r"^F-[0-9]{2}$")
STATUS = {"proposed", "agreed", "implemented", "verified", "withdrawn"}
ASIL_ORDER = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}

REQUIRED = {
  "hazard": ["id", "kind", "title", "functions", "status", "source"],
  "hazardous-event": ["id", "kind", "parents", "situation", "effect", "s", "e", "c", "asil",
                      "aou_flag", "aou_dependency", "asil_if_aou_fails", "status", "source"],
  "safety-goal": ["id", "kind", "text", "type", "asil", "asil_if_aou_fails", "aou_dependency",
                  "parents", "safe_state", "ftti_ms", "ftti_text", "status", "source"],
  "aou": ["id", "kind", "text", "credited_in", "verification_approach", "aou_status", "status", "source"],
}


# ---------------------------------------------------------------- YAML loading

def _scalar(v: str):
  v = v.strip()
  if v.startswith('"'):
    if not v.endswith('"') or len(v) < 2:
      raise ValueError(f"unterminated string: {v}")
    return v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
  if v.startswith("["):
    if not v.endswith("]"):
      raise ValueError(f"unterminated list: {v}")
    inner = v[1:-1].strip()
    return [_scalar(x) for x in inner.split(",")] if inner else []
  if v in ("null", "~", ""):
    return None
  if v == "true":
    return True
  if v == "false":
    return False
  if re.fullmatch(r"-?[0-9]+", v):
    return int(v)
  return v


def _load_subset(text: str) -> list[dict]:
  """Parse a top-level list of flat mappings with scalar or flow-list values."""
  items: list[dict] = []
  cur: dict | None = None
  for n, raw in enumerate(text.splitlines(), 1):
    line = raw.rstrip()
    if not line or line.lstrip().startswith("#"):
      continue
    m = re.match(r"^(- |  )([A-Za-z_][A-Za-z0-9_]*):(?: (.*))?$", line)
    if not m:
      raise ValueError(f"line {n}: outside the supported YAML subset: {raw!r}")
    lead, key, val = m.group(1), m.group(2), m.group(3) or ""
    if lead == "- ":
      cur = {}
      items.append(cur)
    elif cur is None:
      raise ValueError(f"line {n}: key before first list item")
    cur[key] = _scalar(val)
  return items


def load_yaml(path: Path) -> list[dict]:
  text = path.read_text(encoding="utf-8")
  try:
    import yaml  # type: ignore
  except ImportError:
    return _load_subset(text)
  data = yaml.safe_load(text)
  return data or []


# ---------------------------------------------------------------- helpers

def risk_graph(s: int, e: int, c: int) -> str:
  if 0 in (s, e, c):
    return "QM"
  return {10: "D", 9: "C", 8: "B", 7: "A"}.get(s + e + c, "QM")


def expand_he_list(text: str) -> list[str]:
  """Expand 'HE-01.1–01.4, HE-02.3' into explicit IDs."""
  out: list[str] = []
  for tok in [t.strip() for t in text.split(",") if t.strip()]:
    m = re.fullmatch(r"HE-(\d\d)\.(\d)[–-](\d\d)\.(\d)", tok)
    if m:
      g1, a, g2, b = m.groups()
      if g1 != g2:
        raise ValueError(f"cross-group range not supported: {tok}")
      out += [f"HE-{g1}.{k}" for k in range(int(a), int(b) + 1)]
    else:
      out.append(tok)
  return out


class Report:
  def __init__(self) -> None:
    self.errors: list[str] = []
    self.passed: list[str] = []

  def err(self, check: str, msg: str) -> None:
    self.errors.append(f"[{check}] {msg}")


# ---------------------------------------------------------------- checks

def check_items(items: list[dict], rep: Report) -> dict[str, dict]:
  by_id: dict[str, dict] = {}
  for it in items:
    iid = it.get("id")
    kind = it.get("kind")
    if kind not in REQUIRED:
      rep.err("K1", f"{iid}: unknown kind {kind!r}")
      continue
    for k in REQUIRED[kind]:
      if k not in it:
        rep.err("K1", f"{iid}: missing key {k!r}")
    if not isinstance(iid, str) or not ID_RE.match(iid):
      rep.err("K2", f"bad ID {iid!r}")
      continue
    if iid in by_id:
      rep.err("K2", f"duplicate ID {iid}")
    by_id[iid] = it
    if it.get("status") not in STATUS:
      rep.err("K1", f"{iid}: status {it.get('status')!r} not in {sorted(STATUS)}")
  return by_id


def check_links(by_id: dict[str, dict], rep: Report) -> None:
  for iid, it in by_id.items():
    for key in ("parents", "aou_dependency"):
      for ref in it.get(key) or []:
        if ref not in by_id:
          rep.err("K3", f"{iid}: {key} reference {ref} does not resolve")
        elif key == "aou_dependency" and by_id[ref]["kind"] != "aou":
          rep.err("K3", f"{iid}: aou_dependency {ref} is not an AOU")
    for f in it.get("functions") or []:
      if not FUNC_RE.match(str(f)):
        rep.err("K3", f"{iid}: bad function ID {f}")

  hes = {i: x for i, x in by_id.items() if x["kind"] == "hazardous-event"}
  sgs = {i: x for i, x in by_id.items() if x["kind"] == "safety-goal"}
  hazards = {i: x for i, x in by_id.items() if x["kind"] == "hazard"}

  for hid in hazards:
    if not any(hid in (he.get("parents") or []) for he in hes.values()):
      rep.err("R4", f"{hid}: no hazardous event")

  for iid, he in hes.items():
    for p in he.get("parents") or []:
      if p in by_id and by_id[p]["kind"] != "hazard":
        rep.err("K3", f"{iid}: parent {p} is not a hazard")
    exp = risk_graph(he["s"], he["e"], he["c"])
    if he["asil"] != exp:
      rep.err("R1", f"{iid}: asil {he['asil']} but S{he['s']} E{he['e']} C{he['c']} gives {exp}")
    linked = any(iid in (sg.get("parents") or []) for sg in sgs.values())
    if not linked and not he.get("sg_exempt_reason"):
      rep.err("K12", f"{iid}: not linked to a safety goal and no sg_exempt_reason")

  for iid, it in by_id.items():
    alt = it.get("asil_if_aou_fails")
    if alt is not None:
      if not it.get("aou_dependency"):
        rep.err("R3", f"{iid}: asil_if_aou_fails without aou_dependency")
      if ASIL_ORDER.get(alt, -1) < ASIL_ORDER.get(it.get("asil"), 99):
        rep.err("R3", f"{iid}: asil_if_aou_fails {alt} lower than asil {it.get('asil')}")

  for iid, sg in sgs.items():
    parents = [p for p in sg.get("parents") or [] if p in hes]
    if not parents:
      rep.err("K3", f"{iid}: no source hazardous events")
      continue
    top = max((hes[p]["asil"] for p in parents), key=lambda a: ASIL_ORDER[a])
    if sg["asil"] != top:
      rep.err("R2", f"{iid}: asil {sg['asil']} but highest source HE ASIL is {top}")


def check_against_hara(by_id: dict[str, dict], rep: Report) -> None:
  md = HARA_MD.read_text(encoding="utf-8")
  he_rows = {}
  for line in md.splitlines():
    m = re.match(r"^\| (HE-\d\d\.\d) \| (.*?) \| (.*?) \| S(\d) \| E(\d) \| C(\d)( ⚠)? \| \*\*(\w+)\*\* \|", line)
    if m:
      he_rows[m.group(1)] = m.groups()
  yaml_hes = {i for i, x in by_id.items() if x["kind"] == "hazardous-event"}
  for missing in sorted(set(he_rows) ^ yaml_hes):
    rep.err("X1", f"{missing}: present in only one of WP-C-03 / hazards.yaml")
  for hid, (_, sit, eff, s, e, c, warn, asil) in he_rows.items():
    it = by_id.get(hid)
    if not it:
      continue
    for key, md_val in (("situation", sit), ("effect", eff), ("s", int(s)), ("e", int(e)), ("c", int(c)),
                        ("asil", asil), ("aou_flag", bool(warn))):
      if it.get(key) != md_val:
        rep.err("X1", f"{hid}.{key}: yaml {it.get(key)!r} != WP-C-03 {md_val!r}")

  sg_rows = {}
  for line in md.splitlines():
    m = re.match(r"^\| \*\*(SG-\d\d)\*\* \| (.*?) \| \*\*(\w+)\*\*(.*?) \| (.*?) \| (.*?) \| (.*?) \|", line)
    if m:
      sg_rows[m.group(1)] = m.groups()
  yaml_sgs = {i for i, x in by_id.items() if x["kind"] == "safety-goal"}
  for missing in sorted(set(sg_rows) ^ yaml_sgs):
    rep.err("X1", f"{missing}: present in only one of WP-C-03 / goals.yaml")
  for sid, (_, text, asil, rest, src, safe, ftti) in sg_rows.items():
    it = by_id.get(sid)
    if not it:
      continue
    m_alt = re.search(r"\((\w) if", rest)
    checks = (("text", text), ("asil", asil), ("asil_if_aou_fails", m_alt.group(1) if m_alt else None),
              ("parents", expand_he_list(src)), ("safe_state", safe))
    for key, md_val in checks:
      if it.get(key) != md_val:
        rep.err("X1", f"{sid}.{key}: yaml {it.get(key)!r} != WP-C-03 {md_val!r}")
    if not ftti.replace("**", "").startswith(it.get("ftti_text", "").split(" (")[0]):
      rep.err("X1", f"{sid}.ftti_text: yaml {it.get('ftti_text')!r} does not match WP-C-03 {ftti[:40]!r}")


def check_against_itemdef(by_id: dict[str, dict], rep: Report) -> None:
  md = ITEMDEF_MD.read_text(encoding="utf-8")
  rows = {}
  for line in md.splitlines():
    m = re.match(r"^\| (AOU-\d\d) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$", line)
    if m:
      rows[m.group(1)] = m.groups()
  yaml_aous = {i for i, x in by_id.items() if x["kind"] == "aou"}
  for missing in sorted(set(rows) ^ yaml_aous):
    rep.err("X2", f"{missing}: present in only one of WP-C-01 / aou.yaml")
  for aid, (_, text, cred, ver, st) in rows.items():
    it = by_id.get(aid)
    if not it:
      continue
    for key, md_val in (("text", text), ("credited_in", cred), ("verification_approach", ver), ("aou_status", st)):
      if it.get(key) != md_val:
        rep.err("X2", f"{aid}.{key}: yaml {it.get(key)!r} != WP-C-01 {md_val!r}")


def main(argv: list[str]) -> int:
  rep = Report()
  items: list[dict] = []
  files = sorted(ITEMS_DIR.glob("*.yaml"))
  for f in files:
    try:
      data = load_yaml(f)
    except Exception as exc:  # noqa: BLE001 - report any parse failure as K1
      rep.err("K1", f"{f.name}: {exc}")
      continue
    if not isinstance(data, list):
      rep.err("K1", f"{f.name}: top level must be a list")
      continue
    items += data
  by_id = check_items(items, rep)
  check_links(by_id, rep)
  if "--no-source-compare" not in argv:
    check_against_hara(by_id, rep)
    check_against_itemdef(by_id, rep)

  kinds: dict[str, int] = {}
  for it in by_id.values():
    kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
  print(f"trace: {len(files)} files, {len(by_id)} items " +
        ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
  if rep.errors:
    for e in rep.errors:
      print("ERROR", e)
    print(f"FAILED: {len(rep.errors)} error(s)")
    return 1
  print("OK: all implemented checks passed")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
