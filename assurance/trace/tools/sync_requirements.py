#!/usr/bin/env python3
"""Copy the functional and technical safety requirements from their work products into trace items.

Sources (the work products stay the reviewed documents; the YAML files are generated copies):
  FSR   WP-C-04 §5 requirement tables; SG parents from the WP-C-04 §9 FSR -> SG matrix
  TSR   WP-S-02 §3-§9 requirement tables (TSR-1xx...7xx); WP-S-06 tables (TSR-8xx, full text)
  SWSR  WP-W-02 §3-§9 requirement tables; §11 SW-HW interface rows (parent = the TSR of the same number)
  HWSR  WP-H-01 §4 requirement tables
  SOTIF WP-C-05 §3 (SH), WP-C-06 §3 (FI), §4 and §5 (TC), WP-C-07 §2 (FM); the TC and FM links come from the
        WP-C-06 §5 TC → FI → SH evaluation rows
  AI    WP-C-11 §6 (AIR) and §7 (DSR) requirement tables
  CS    WP-C-09 §4 and §8 (TS), WP-C-10 §4 and §8 (CSG), WP-S-07 §4 (CSR)

Outputs: assurance/trace/items/fsr.yaml, tsr.yaml, swsr.yaml, hwsr.yaml, sotif.yaml, ai.yaml, cs.yaml

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
SWSR_MD = ASSURANCE_DIR / "05-software" / "WP-W-02-software-safety-requirements.md"
HWSR_MD = ASSURANCE_DIR / "04-hardware" / "WP-H-01-hardware-safety-requirements.md"
SH_MD = ASSURANCE_DIR / "02-concept" / "WP-C-05-sotif-hazard-identification.md"
FI_MD = ASSURANCE_DIR / "02-concept" / "WP-C-06-sotif-insufficiencies-triggering-conditions.md"
FM_MD = ASSURANCE_DIR / "02-concept" / "WP-C-07-sotif-functional-modifications.md"
AI_MD = ASSURANCE_DIR / "02-concept" / "WP-C-11-ai-system-definition-and-safety-requirements.md"
TARA_MD = ASSURANCE_DIR / "02-concept" / "WP-C-09-tara.md"
CSG_MD = ASSURANCE_DIR / "02-concept" / "WP-C-10-cybersecurity-goals-and-concept.md"
CSR_MD = ASSURANCE_DIR / "03-system" / "WP-S-07-cybersecurity-requirements-architecture.md"

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


# ---------------------------------------------------------------- SWSR, HWSR

def _parent_cell(text: str) -> str:
  """Normalise a SWSR/HWSR parent cell for expand_refs: 'FSR-01.09 / TSR-501 (note)' -> 'FSR-01.09, TSR-501';
  'TSR-307(a)' -> 'TSR-307'."""
  return re.sub(r"\s*\([^)]*\)", "", text).replace(" / ", ", ")


def swsr_attributes(text: str) -> tuple[str, dict[str, str]]:
  """WP-W-02 §2.4: the drafting origin of all SWSRs and the configuration applicability table."""
  sec = re.split(r"\n#{2,3} ", text.split("### 2.4 ", 1)[1], maxsplit=1)[0] if "### 2.4 " in text else ""
  m = re.search(r"Drafting origin: \*\*(.+?)\*\*", sec)
  origin = m.group(1) if m else ""
  applies: dict[str, str] = {}
  for line in sec.splitlines():
    c = cells(line) if line.startswith("| SWSR-") else []
    if len(c) >= 2:
      for sid in re.findall(r"SWSR-[0-9]{3}[a-z]?", c[0]):
        applies[sid] = c[1]
  return origin, applies


def _swsr_status(req: str) -> str:
  return "withdrawn" if re.match(r"^\**Withdrawn", req) else "proposed"


def swsr_items() -> list[dict]:
  items = []
  tsr_asil = {t["id"]: t["asil"] for t in tsr_items()}
  text = SWSR_MD.read_text(encoding="utf-8")
  origin, applies = swsr_attributes(text)
  default_applies = applies.get("SWSR-default", "CFG-001")
  section = ""
  for line in text.splitlines():
    if line.startswith("#"):
      section = line.lstrip("#").split()[0]
    if not re.match(r"^\| SWSR-[0-9]{3}[a-z]? \|", line) or section == "2.4":
      continue
    c = cells(line)
    extra = {"applies_to": applies.get(c[0], default_applies), "proposed_by": origin}
    if section == "11.":  # §11 SW-HW interface requirement: parent is the TSR of the same number
      if len(c) != 8:
        raise ValueError(f"WP-W-02 §11: unexpected column count {len(c)} in {c[0]}")
      sid, req, hw, hsi, hwsr, verif, accept, impl = c
      tid = "TSR-" + re.match(r"SWSR-([0-9]{3})", sid).group(1)
      items.append({"id": sid, "kind": "swsr", "text": req, "asil": tsr_asil.get(tid, ""), "parents": [tid],
                    "parent_text": f"{tid} (WP-W-02 §11; ASIL taken from {tid})", "other_parents": False,
                    "allocated_to": hw, "verification": verif, "acceptance": accept, **extra, "baseline_impl": impl,
                    "status": _swsr_status(req), "source": "WP-W-02"})
    elif len(c) == 8:
      sid, req, asil, parent, alloc, verif, accept, impl = c
      ids, other = expand_refs(_parent_cell(parent))
      items.append({"id": sid, "kind": "swsr", "text": req, "asil": asil, "parents": ids, "parent_text": parent,
                    "other_parents": bool(other), "allocated_to": alloc, "verification": verif, "acceptance": accept,
                    **extra, "baseline_impl": impl, "status": _swsr_status(req), "source": "WP-W-02"})
    else:
      raise ValueError(f"WP-W-02: unexpected column count {len(c)} in {c[0]}")
  return items


def hwsr_items() -> list[dict]:
  items = []
  for line in HWSR_MD.read_text(encoding="utf-8").splitlines():
    if not re.match(r"^\| HWSR-[0-9]{3}[a-z]? \|", line):
      continue
    c = cells(line)
    if len(c) != 8:
      raise ValueError(f"WP-H-01: unexpected column count {len(c)} in {c[0]}")
    hid, req, asil, parent, alloc, kind, verif, impl = c
    ids, other = expand_refs(_parent_cell(parent))
    items.append({"id": hid, "kind": "hwsr", "text": req, "asil": asil, "parents": ids, "parent_text": parent,
                  "other_parents": bool(other), "allocated_to": alloc, "hw_kind": kind, "verification": verif,
                  "baseline_impl": impl, "status": "proposed", "source": "WP-H-01"})
  return items


# ---------------------------------------------------------------- SOTIF: SH, FI, TC, FM

def _ids(text: str, prefix: str) -> list[str]:
  """IDs of one kind named in a cell, ranges expanded ('SH-01…SH-03' -> SH-01, SH-02, SH-03)."""
  out: list[str] = []
  for a, b in re.findall(rf"\b{prefix}-([0-9]{{2}})(?:\s*[…–]\s*(?:{prefix}-)?([0-9]{{2}}))?", text):
    out += [f"{prefix}-{n:02d}" for n in range(int(a), int(b or a) + 1)]
  return list(dict.fromkeys(out))


def _section(text: str, start: str, end: str, md: Path) -> str:
  if start not in text:
    raise ValueError(f"{md.name}: heading {start!r} not found")
  return text.split(start, 1)[1].split(end, 1)[0]


def _rows(text: str, prefix: str, ncols: int, md: Path) -> list[list[str]]:
  rows = []
  for line in text.splitlines():
    if re.match(rf"^\| {prefix}-[0-9]{{2}} \|", line):
      c = cells(line)
      if len(c) != ncols:
        raise ValueError(f"{md.name}: unexpected column count {len(c)} in {c[0]}")
      rows.append(c)
  return rows


def _rating(cell: str, letter: str) -> int | None:
  m = re.fullmatch(rf"{letter}([0-3])", cell)
  return int(m.group(1)) if m else None


def evaluation_rows() -> list[dict[str, list[str] | str]]:
  """WP-C-06 §5: one dict per TC → FI → SH row, with the modifications its action names."""
  sec = _section(FI_MD.read_text(encoding="utf-8"), "## 5. TC → FI → SH evaluation", "\n### ", FI_MD)
  rows = []
  for line in sec.splitlines():
    if not re.match(r"^\| TC-[0-9]{2}", line):
      continue
    c = cells(line)
    if len(c) != 6:
      raise ValueError(f"{FI_MD.name} §5: unexpected column count {len(c)} in {c[0]}")
    rows.append({"tc": _ids(c[0], "TC"), "fi": _ids(c[1], "FI"), "sh": _ids(c[2], "SH"), "evaluation": c[4],
                 "fm": _ids(c[5], "FM")})
  return rows


def sotif_items() -> list[dict]:
  items: list[dict] = []
  sec = _section(SH_MD.read_text(encoding="utf-8"), "## 3. SOTIF hazards", "\n## 4.", SH_MD)
  for sid, text, func, linked, situations, s, c, _ in _rows(sec, "SH", 8, SH_MD):
    unused = text.startswith("—")
    it = {"id": sid, "kind": "sotif-hazard", "text": text.lstrip("— ").strip() if unused else text,
          "functions": re.findall(r"F-[0-9]{2}", func), "function_text": func, "shares_event": _ids(linked, "H") if linked.startswith("H-") else [],
          "linked_text": linked, "situations": situations}
    for key, val in (("s", _rating(s, "S")), ("c", _rating(c, "C"))):
      if val is not None:
        it[key] = val
    items.append({**it, "status": "withdrawn" if unused else "proposed", "source": "WP-C-05"})
  fi_text = FI_MD.read_text(encoding="utf-8")
  sec = _section(fi_text, "## 3. Functional insufficiencies", "\n## 4.", FI_MD)
  for fid, typ, comp, text, sh, _ in _rows(sec, "FI", 6, FI_MD):
    items.append({"id": fid, "kind": "functional-insufficiency", "text": text, "fi_type": typ, "component": comp,
                  "parents": _ids(sh, "SH"), "status": "proposed", "source": "WP-C-06"})
  ev = evaluation_rows()
  sec = _section(fi_text, "## 4. Triggering conditions", "\n## 5.", FI_MD)
  for tid, text, cat, _ in _rows(sec, "TC", 4, FI_MD):
    mine = [r for r in ev if tid in r["tc"]]
    items.append({"id": tid, "kind": "triggering-condition", "text": text, "category": cat,
                  "parents": list(dict.fromkeys(x for r in mine for x in r["sh"])),
                  "insufficiencies": list(dict.fromkeys(x for r in mine for x in r["fi"])),
                  "evaluation": "; ".join(dict.fromkeys(str(r["evaluation"]) for r in mine)),
                  "status": "proposed", "source": "WP-C-06"})
  sec = _section(FM_MD.read_text(encoding="utf-8"), "## 2. Summary", "\n### ", FM_MD)
  for mid, title, addresses, gap, prio in _rows(sec, "FM", 5, FM_MD):
    mine = [r for r in ev if mid in r["fm"]]
    items.append({"id": mid, "kind": "functional-modification", "title": title, "addresses": _ids(addresses, "SH"),
                  "parents": list(dict.fromkeys([x for r in mine for x in r["tc"]] + [x for r in mine for x in r["fi"]])),
                  "gap_text": gap, "priority": prio, "status": "proposed", "source": "WP-C-07"})
  return items


# ---------------------------------------------------------------- AI: AIR, DSR

AI_PARENT_PREFIXES = ("SG", "FSR", "SH", "TC", "FI", "FM", "GAP", "AIR", "DSR")
AI_REF = re.compile(r"^([A-Z]+)-([0-9]{2,3}(?:\.[0-9]{2})?)(?:\s*…\s*(?:[A-Z]+-)?([0-9]{2,3}(?:\.[0-9]{2})?))?$")


def ai_refs(cell: str) -> tuple[list[str], list[str], bool]:
  """Read a WP-C-11 Parent cell: (parent IDs, TSRs it names, whether it also names something that is not an item).
  A TSR is never a parent: AIRs sit at the FSR level, and the cell names TSRs that refine an AIR ('refined by') or
  share its FSR. Markdown links are read as their text; parentheticals are notes and are dropped."""
  parents: list[str] = []
  tsrs: list[str] = []
  other = False
  for group in re.sub(r"\([^)]*\)", "", MD_LINK.sub(r"\1", cell)).split(";"):
    group = re.sub(r"^\s*refined by\s+", "", group)
    for tok in (t.strip() for t in group.split(",")):
      if not tok:
        continue
      m = AI_REF.match(tok)
      if m and m.group(1) == "TSR":
        tsrs.append(tok)
      elif m and m.group(1) in AI_PARENT_PREFIXES:
        prefix, a, b = m.groups()
        parents += _range(prefix, a, b) if b else [tok]
      else:
        other = True
  return list(dict.fromkeys(parents)), list(dict.fromkeys(tsrs)), other


def ai_items() -> list[dict]:
  text = AI_MD.read_text(encoding="utf-8")
  items: list[dict] = []
  category = ""
  for line in _section(text, "## 6. AI safety requirements", "\n## 7.", AI_MD).splitlines():
    m = re.match(r"^### 6\.[0-9]+ (.+?)\s*$", line)
    if m:
      category = m.group(1)
    if not re.match(r"^\| AIR-[0-9]{2} \|", line):
      continue
    c = cells(line)
    if len(c) != 6:
      raise ValueError(f"{AI_MD.name} §6: unexpected column count {len(c)} in {c[0]}")
    aid, req, comp, parent, verif, status = c
    parents, tsrs, other = ai_refs(parent)
    items.append({"id": aid, "kind": "ai-requirement", "text": req, "category": category, "component": comp,
                  "parents": parents, "parent_text": parent, "other_parents": other, "related_tsr": tsrs,
                  "verification": verif, "baseline_impl": status, "status": "proposed", "source": "WP-C-11"})
  for c in _rows(_section(text, "## 7. Dataset requirements", "\n## 8.", AI_MD), "DSR", 5, AI_MD):
    did, req, parent, verif, status = c
    parents, _, other = ai_refs(parent)
    items.append({"id": did, "kind": "dataset-requirement", "text": req, "parents": parents, "parent_text": parent,
                  "other_parents": other, "verification": verif, "baseline_impl": status, "status": "proposed",
                  "source": "WP-C-11"})
  return items


# ---------------------------------------------------------------- CS: TS, CSG, CSR

def _ids3(text: str, prefix: str) -> list[str]:
  """Three-digit IDs of one kind named in a cell, ranges expanded ('TSR-401…405' -> TSR-401 … TSR-405)."""
  out: list[str] = []
  for a, b in re.findall(rf"\b{prefix}-([0-9]{{3}})(?:\s*…\s*(?:{prefix}-)?([0-9]{{3}}))?", text):
    out += [f"{prefix}-{n:03d}" for n in range(int(a), int(b or a) + 1)]
  return list(dict.fromkeys(out))


def _plain(cell: str) -> str:
  return cell.replace("**", "").strip()


def cs_items() -> list[dict]:
  items: list[dict] = []
  tara = TARA_MD.read_text(encoding="utf-8")
  risk: dict[str, tuple[int, str]] = {}
  for tid, _, _, value, treatment, _ in _rows(_section(tara, "## 8. Risk determination", "\n## 9.", TARA_MD), "TS", 6,
                                              TARA_MD):
    risk[tid] = (int(_plain(value)), _plain(treatment))
  for tid, text, stride, assets, prop, damage, gap in _rows(_section(tara, "## 4. Threat scenarios", "\n## 5.", TARA_MD),
                                                            "TS", 7, TARA_MD):
    if tid not in risk:
      raise ValueError(f"{TARA_MD.name}: {tid} has no row in §8")
    items.append({"id": tid, "kind": "threat-scenario", "text": text, "stride": stride, "assets": assets,
                  "violated_property": prop, "damage_text": damage, "gap_text": gap, "risk": risk[tid][0],
                  "treatment": risk[tid][1], "status": "proposed", "source": "WP-C-09"})
  goals = CSG_MD.read_text(encoding="utf-8")
  protects: dict[str, list[str]] = {}
  for line in _section(goals, "## 8. Relation to safety goals", "\n## ", CSG_MD).splitlines():
    if re.match(r"^\| SG-[0-9]{2} ", line):
      c = cells(line)
      for g in _ids(c[1], "CSG"):
        protects.setdefault(g, []).append(c[0].split()[0])
  for line in _section(goals, "## 4. Cybersecurity goals", "\n## 5.", CSG_MD).splitlines():
    if not re.match(r"^\| \*\*CSG-[0-9]{2}\*\* \|", line):
      continue
    c = cells(line)
    if len(c) != 5:
      raise ValueError(f"{CSG_MD.name} §4: unexpected column count {len(c)} in {c[0]}")
    gid, text, addresses, cal, rationale = (_plain(x) for x in c)
    items.append({"id": gid, "kind": "cybersecurity-goal", "text": text, "parents": _ids(addresses, "TS"),
                  "parent_text": addresses, "cal": cal, "protects": protects.get(gid, []), "rationale": rationale,
                  "status": "proposed", "source": "WP-C-10"})
  head = ("", [], "")
  for line in _section(CSR_MD.read_text(encoding="utf-8"), "## 4. Detailed cybersecurity requirements", "\n## 5.",
                       CSR_MD).splitlines():
    m = re.match(r"^### 4\.[0-9]+ (CSR-C-[0-9]{2}) .*\((.*)\)\s*$", line)
    if m:
      cal = re.search(r"CAL [0-9]", m.group(2))
      head = (m.group(1), _ids(m.group(2), "CSG"), cal.group(0) if cal else "")
    if not re.match(r"^\| CSR-[0-9]{3} \|", line):
      continue
    c = cells(line)
    if len(c) != 6:
      raise ValueError(f"{CSR_MD.name} §4: unexpected column count {len(c)} in {c[0]}")
    rid, text, alloc, relation, verif, evidence = c
    items.append({"id": rid, "kind": "cybersecurity-requirement", "text": text, "parents": head[1],
                  "concept_requirement": head[0], "cal": head[2], "other_parents": not head[1], "allocated_to": alloc,
                  "safety_relation": relation, "related_tsr": _ids3(relation, "TSR"), "verification": verif,
                  "baseline_impl": evidence, "status": "proposed", "source": "WP-S-07"})
  return items


def not_refined(md: Path, heading: str) -> list[str]:
  """TSR IDs listed in a work product's 'TSRs not refined into ...' table (first column)."""
  text = md.read_text(encoding="utf-8")
  if heading not in text:
    return []
  sec = text.split(heading, 1)[1].split("\n## ", 1)[0]
  out: list[str] = []
  for line in sec.splitlines():
    c = cells(line) if line.startswith("|") else []
    if c and c[0].startswith("TSR-"):
      out += expand_refs(c[0])[0]
  return out


# ---------------------------------------------------------------- output

FIELD_ORDER = ["id", "kind", "title", "text", "fi_type", "component", "category", "functions", "function_text", "s", "c",
               "situations", "asil", "parents", "shares_event", "linked_text", "insufficiencies", "addresses", "evaluation",
               "gap_text", "priority", "stride", "assets", "violated_property",
               "damage_text", "risk", "treatment", "concept_requirement", "cal", "protects", "rationale", "safety_relation",
               "related_tsr", "parent_text", "other_parents", "allocated_to", "mechanism",
               "timing", "hw_kind", "verification", "acceptance", "applies_to", "proposed_by", "baseline_impl", "status",
               "source"]
SOURCE_MD = {"WP-C-04": FSC_MD, "WP-S-02": TSR_MD, "WP-S-06": TSR8_MD, "WP-W-02": SWSR_MD, "WP-H-01": HWSR_MD,
             "WP-C-05": SH_MD, "WP-C-06": FI_MD, "WP-C-07": FM_MD, "WP-C-11": AI_MD,
             "WP-C-09": TARA_MD, "WP-C-10": CSG_MD, "WP-S-07": CSR_MD}
REPO_ROOT = ASSURANCE_DIR.parent
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")


def delink(s: str, source_md: Path | None) -> str:
  """Markdown links copied from a work product do not resolve from trace/items/. Rewrite '[text](relative)' to
  'text (repository-relative path)'; absolute URLs are kept as 'text (url)'."""
  def repl(m: re.Match) -> str:
    text, target = m.group(1), m.group(2)
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or source_md is None:
      return f"{text} ({target})"
    path, _, anchor = target.partition("#")
    resolved = (source_md.parent / path).resolve() if path else source_md.resolve()
    try:
      rel = resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
      rel = target
    return f"{text} ({rel}{'#' + anchor if anchor else ''})"
  return MD_LINK.sub(repl, s)


def render(items: list[dict], header: str) -> str:
  out = [header, ""]
  for it in items:
    src = SOURCE_MD.get(it.get("source", ""))
    first = True
    for key in FIELD_ORDER:
      if key not in it:
        continue
      v = it[key]
      if isinstance(v, list):
        val = flow(v)
      elif isinstance(v, bool):
        val = "true" if v else "false"
      elif isinstance(v, int):
        val = str(v)
      elif key in ("id", "kind", "status", "source"):
        val = v
      else:
        val = quote(delink(v, src))
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


SWSR_HEADER = """# SWSR items: software safety requirements from WP-W-02 §3-§9 and the §11 SW-HW interface rows.
# GENERATED by tools/sync_requirements.py from the work product, which stays the source of truth.
# Do not edit by hand: change WP-W-02 and regenerate. CI fails if this file is out of date.
# Schema: see ../README.md §4.5."""

HWSR_HEADER = """# HWSR items: hardware safety requirements from WP-H-01 §4.
# GENERATED by tools/sync_requirements.py from the work product, which stays the source of truth.
# Do not edit by hand: change WP-H-01 and regenerate. CI fails if this file is out of date.
# Schema: see ../README.md §4.5."""


SOTIF_HEADER = """# SOTIF items: SOTIF hazards (WP-C-05 §3), functional insufficiencies (WP-C-06 §3), triggering conditions
# (WP-C-06 §4) and functional modifications (WP-C-07 §2). TC parents and insufficiencies, and FM parents, come from
# the WP-C-06 §5 TC -> FI -> SH evaluation rows.
# GENERATED by tools/sync_requirements.py from the work products, which stay the source of truth.
# Do not edit by hand: change WP-C-05, WP-C-06 or WP-C-07 and regenerate. CI fails if this file is out of date.
# Schema: see ../README.md §4.6."""


AI_HEADER = """# AI items: AI safety requirements (WP-C-11 §6) and dataset requirements (WP-C-11 §7).
# GENERATED by tools/sync_requirements.py from the work product, which stays the source of truth.
# Do not edit by hand: change WP-C-11 and regenerate. CI fails if this file is out of date.
# Schema: see ../README.md §4.7."""


CS_HEADER = """# Cybersecurity items: threat scenarios (WP-C-09 §4, risk and treatment from §8), cybersecurity goals (WP-C-10 §4,
# the safety goals they protect from §8) and detailed cybersecurity requirements (WP-S-07 §4, parent goals from the
# heading of their CSR-C section).
# GENERATED by tools/sync_requirements.py from the work products, which stay the source of truth.
# Do not edit by hand: change WP-C-09, WP-C-10 or WP-S-07 and regenerate. CI fails if this file is out of date.
# Schema: see ../README.md §4.8."""


def expected_outputs() -> dict[str, str]:
  return {
    "fsr.yaml": render(fsr_items(), FSR_HEADER),
    "tsr.yaml": render(tsr_items(), TSR_HEADER),
    "swsr.yaml": render(swsr_items(), SWSR_HEADER),
    "hwsr.yaml": render(hwsr_items(), HWSR_HEADER),
    "sotif.yaml": render(sotif_items(), SOTIF_HEADER),
    "ai.yaml": render(ai_items(), AI_HEADER),
    "cs.yaml": render(cs_items(), CS_HEADER),
  }


def main(argv: list[str]) -> int:
  check = "--check" in argv
  outputs = {ITEMS_DIR / name: content for name, content in expected_outputs().items()}
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
    print(f"FAIL: {', '.join(stale)} out of date with WP-C-04 / WP-S-02 / WP-S-06 / WP-W-02 / WP-H-01 / WP-C-05…07 / WP-C-11 / WP-C-09 / WP-C-10 / WP-S-07; run assurance/trace/tools/sync_requirements.py")
    return 1
  print("OK: requirement items match the work products" if check else "OK: requirement items generated")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
