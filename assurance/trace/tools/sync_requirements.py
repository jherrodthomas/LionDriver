#!/usr/bin/env python3
"""Copy the functional and technical safety requirements from their work products into trace items.

Sources (the work products stay the reviewed documents; the YAML files are generated copies):
  FSR  WP-C-04 §5 requirement tables; SG parents from the WP-C-04 §9 FSR -> SG matrix
  TSR  WP-S-02 §3-§9 requirement tables (TSR-1xx...7xx); WP-S-06 tables (TSR-8xx, full text)

Outputs: assurance/trace/items/fsr.yaml, assurance/trace/items/tsr.yaml

Usage:
  python3 assurance/trace/tools/sync_requirements.py           # regenerate the YAML files
  python3 assurance/trace/tools/sync_requirements.py --check   # fail if they differ from the work products

Parent references are expanded: "FSR-07.01, 07.03" -> FSR-07.01, FSR-07.03; "SG-01…07" -> SG-01...SG-07;
"AOU-01…05, 09" -> AOU-01...AOU-05, AOU-09. References that are not item IDs (a standard clause, a
tailoring ID) are kept verbatim in parent_text and listed in other_parents.
Standard library only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TRACE_DIR = Path(__file__).resolve().parent.parent
ASSURANCE_DIR = TRACE_DIR.parent
ITEMS_DIR = TRACE_DIR / "items"
FSC_MD = ASSURANCE_DIR / "02-concept" / "WP-C-04-functional-safety-concept.md"
TSR_MD = ASSURANCE_DIR / "03-system" / "WP-S-02-technical-safety-requirements.md"
TSR8_MD = ASSURANCE_DIR / "03-system" / "WP-S-06-requirements-production-operation.md"

ITEM_PREFIXES = {"FSR", "TSR", "SG", "AOU", "H", "HE", "GAP"}


def cells(line: str) -> list[str]:
  return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def quote(s: str) -> str:
  s = re.sub(r"\s+", " ", s).strip()
  return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def flow(items: list[str]) -> str:
  for x in items:
    if "," in x or " " in x:
      raise ValueError(f"list element not allowed in flow list: {x!r}")
  return "[" + ", ".join(items) + "]"


def expand_refs(text: str) -> tuple[list[str], list[str]]:
  """Expand a parent cell into item IDs plus any references that are not item IDs."""
  ids: list[str] = []
  other: list[str] = []
  prefix = None
  for part in re.split(r"[;,]", text):
    tok = part.strip()
    if not tok:
      continue
    m = re.match(r"^([A-Z]+)-([0-9.]+[a-z]?)\s*[…–-]\s*(?:[A-Z]+-)?([0-9.]+[a-z]?)$", tok)
    if m and m.group(1) in ITEM_PREFIXES:
      prefix, a, b = m.groups()
      ids += _range(prefix, a, b)
      continue
    m = re.match(r"^([0-9.]+[a-z]?)\s*[…–-]\s*([0-9.]+[a-z]?)$", tok)
    if m and prefix:
      ids += _range(prefix, *m.groups())
      continue
    m = re.match(r"^([A-Z]+)-([0-9.]+[a-z]?)$", tok)
    if m and m.group(1) in ITEM_PREFIXES:
      prefix = m.group(1)
      ids.append(tok)
      continue
    if re.match(r"^[0-9.]+[a-z]?$", tok) and prefix:
      ids.append(f"{prefix}-{tok}")
      continue
    other.append(tok)
    prefix = None
  return list(dict.fromkeys(ids)), other


def _range(prefix: str, a: str, b: str) -> list[str]:
  if "." in a:
    major, lo = a.split(".")
    hi = b.rsplit(".", maxsplit=1)[-1]
    return [f"{prefix}-{major}.{n:0{len(lo)}d}" for n in range(int(lo), int(hi) + 1)]
  return [f"{prefix}-{n:0{len(a)}d}" for n in range(int(a), int(b) + 1)]


# ---------------------------------------------------------------- FSR

def fsr_items() -> list[dict]:
  text = FSC_MD.read_text(encoding="utf-8")
  sec5 = text.split("## 5. Functional safety requirements", 1)[1].split("\n## 6.", 1)[0]
  sec9 = text.split("## 9. FSR → SG trace", 1)[1].split("\n## 10.", 1)[0]
  sg_of: dict[str, list[str]] = {}
  header = None
  for line in sec9.splitlines():
    c = cells(line) if line.startswith("|") else []
    if c and c[0] == "FSR":
      header = c[1:]
      continue
    if not c or not c[0].startswith("FSR-") or header is None:
      continue
    fsrs, _ = expand_refs(c[0])
    sgs = [sg for sg, mark in zip(header, c[1:], strict=True) if mark == "●"]
    for f in fsrs:
      sg_of.setdefault(f, [])
      sg_of[f] += [s for s in sgs if s not in sg_of[f]]
  items = []
  for line in sec5.splitlines():
    if not re.match(r"^\| FSR-[0-9]{2}\.[0-9]{2} \|", line):
      continue
    c = cells(line)
    if len(c) != 6:
      raise ValueError(f"WP-C-04: unexpected column count {len(c)} in {c[0]}")
    fid, req, asil, alloc, verif, impl = c
    items.append({
      "id": fid, "kind": "fsr", "text": req, "asil": asil, "parents": sg_of.get(fid, []),
      "allocated_to": alloc, "verification": verif, "baseline_impl": impl,
      "status": "proposed", "source": "WP-C-04",
    })
  return items


# ---------------------------------------------------------------- TSR

def tsr_items() -> list[dict]:
  items = []
  s02 = TSR_MD.read_text(encoding="utf-8").split("\n## 10.", 1)[0]
  for line in s02.splitlines():
    if not re.match(r"^\| TSR-[0-9]{3}[a-z]? \|", line):
      continue
    c = cells(line)
    if len(c) != 9:
      raise ValueError(f"WP-S-02: unexpected column count {len(c)} in {c[0]}")
    tid, req, asil, parent, alloc, sm, timing, verif, impl = c
    items.append(_tsr(tid, req, asil, parent, "WP-S-02", allocated_to=alloc, mechanism=sm, timing=timing,
                      verification=verif, baseline_impl=impl))
  in_req_table = False
  for line in TSR8_MD.read_text(encoding="utf-8").splitlines():
    if line.startswith("| ID | Requirement |"):
      in_req_table = True
      continue
    if not line.startswith("|"):
      in_req_table = False
    if not in_req_table or not re.match(r"^\| TSR-8[0-9]{2}[a-z]? \|", line):
      continue
    c = cells(line)
    if len(c) != 7:
      raise ValueError(f"WP-S-06: unexpected column count {len(c)} in {c[0]}")
    tid, req, asil, parent, impl_by, verif, status_text = c
    items.append(_tsr(tid, req, asil, parent, "WP-S-06", allocated_to="OPS", mechanism="",
                      timing="", verification=verif, baseline_impl=f"Implemented by: {impl_by}. Status: {status_text}"))
  return items


def _tsr(tid, req, asil, parent, source, **kw) -> dict:
  ids, other = expand_refs(parent)
  return {"id": tid, "kind": "tsr", "text": req, "asil": asil, "parents": ids, "parent_text": parent,
          "other_parents": bool(other), **kw, "status": "proposed", "source": source}


# ---------------------------------------------------------------- output

FIELD_ORDER = ["id", "kind", "text", "asil", "parents", "parent_text", "other_parents", "allocated_to", "mechanism",
               "timing", "verification", "baseline_impl", "status", "source"]


def render(items: list[dict], header: str) -> str:
  out = [header, ""]
  for it in items:
    first = True
    for key in FIELD_ORDER:
      if key not in it:
        continue
      v = it[key]
      if isinstance(v, list):
        val = flow(v)
      elif isinstance(v, bool):
        val = "true" if v else "false"
      elif key in ("id", "kind", "status", "source"):
        val = v
      else:
        val = quote(v)
      out.append(f"{'- ' if first else '  '}{key}: {val}")
      first = False
    out.append("")
  return "\n".join(out)


FSR_HEADER = """# FSR items: functional safety requirements from WP-C-04 §5 (parents from the §9 FSR -> SG matrix).
# GENERATED by tools/sync_requirements.py from the work product, which stays the source of truth.
# Do not edit by hand: change WP-C-04 and regenerate. CI fails if this file is out of date.
# Schema: see ../README.md §4.5."""

TSR_HEADER = """# TSR items: technical safety requirements from WP-S-02 §3-§9 (TSR-1xx...7xx) and WP-S-06 (TSR-8xx).
# GENERATED by tools/sync_requirements.py from the work products, which stay the source of truth.
# Do not edit by hand: change WP-S-02 or WP-S-06 and regenerate. CI fails if this file is out of date.
# Schema: see ../README.md §4.5."""


def main(argv: list[str]) -> int:
  check = "--check" in argv
  outputs = {
    ITEMS_DIR / "fsr.yaml": render(fsr_items(), FSR_HEADER),
    ITEMS_DIR / "tsr.yaml": render(tsr_items(), TSR_HEADER),
  }
  stale = []
  for path, content in outputs.items():
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
      continue
    if check:
      stale.append(path.name)
    else:
      path.write_text(content, encoding="utf-8")
      print(f"wrote {path.relative_to(ASSURANCE_DIR.parent).as_posix()}")
  if stale:
    print(f"FAIL: {', '.join(stale)} out of date with WP-C-04 / WP-S-02 / WP-S-06; run assurance/trace/tools/sync_requirements.py")
    return 1
  print("OK: requirement items match the work products" if check else "OK: requirement items generated")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
