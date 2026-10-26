#!/usr/bin/env python3
"""Generate the ASPICE-aligned traceability map of WP-T-01 (assurance/trace/maps/aspice-trace-map.md).

The map places every traced item on the ASPICE 4.0 V-model: specification processes on the left
(SYS.1 ... SWE.3, HWE.1/2, MLE.1), verification processes on the right (SWE.4 ... SYS.5, HWE.3/4,
MLE.4, VAL.1), each verification level opposite the level whose work products it verifies. The
ISO 26262, ISO 21448, ISO/PAS 8800 and ISO/SAE 21434 items sit on the process that produces them.

Nothing in the map is typed by hand. It is computed from:
  - the trace data in assurance/trace/items/*.yaml (H, HE, SG, AOU, FSR, TSR, SWSR, HWSR and their
    `parents` links: the derivation links on the left of the V);
  - the IDs defined in the first column of the requirement tables of the work products that are not
    yet in the trace data (SYS, SH, TC, FI, FM, AIR, DSR, TS, CSG, CSR): counted, but without links;
  - the test-specification tables (VS-UV, VS-SWI, VS-SWQ, VS-HW, VS-ML, VS-SI, VS-FI, VS-SQ, VS-VAL):
    the requirement IDs each case names are the verification links across the V.

Usage (from the repository root):
    python3 assurance/trace/tools/trace_map.py           # write maps/aspice-trace-map.md
    python3 assurance/trace/tools/trace_map.py --check   # fail if the committed map is stale

Standard library only; check_trace.py is imported for its YAML loader.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_trace as ct

TRACE_DIR = HERE.parent
ASSURANCE_DIR = TRACE_DIR.parent
OUT = TRACE_DIR / "maps" / "aspice-trace-map.md"
FIG = TRACE_DIR / "maps" / "fig-1-aspice-v-model.svg"

# Kinds in the trace data, by ID prefix.
YAML_KIND = {"hazard": "H", "hazardous-event": "HE", "safety-goal": "SG", "aou": "AOU", "fsr": "FSR",
             "tsr": "TSR", "swsr": "SWSR", "hwsr": "HWSR", "sotif-hazard": "SH", "triggering-condition": "TC",
             "functional-insufficiency": "FI", "functional-modification": "FM", "ai-requirement": "AIR",
             "dataset-requirement": "DSR", "threat-scenario": "TS", "cybersecurity-goal": "CSG",
             "cybersecurity-requirement": "CSR", "system-requirement": "SYS",
             "interface-requirement": "IFR"}  # IFR: cross-domain interfaces (DQ-129 A); not a level of the V
# Kinds defined only in work-product tables so far: prefix -> defining work products.
DOC_KINDS: dict[str, list[str]] = {}  # every kind of KIND_NAME is in items/ now; a new kind starts here
KIND_NAME = {
  "H": "hazards", "HE": "hazardous events", "SG": "safety goals", "AOU": "assumptions of use",
  "FSR": "functional safety req.", "TSR": "technical safety req.", "SWSR": "SW safety req.",
  "HWSR": "HW safety req.", "SH": "SOTIF hazards", "TC": "triggering conditions",
  "FI": "functional insufficiencies", "FM": "functional modifications", "AIR": "AI safety req.",
  "DSR": "dataset req.", "TS": "threat scenarios", "CSG": "cybersecurity goals",
  "CSR": "cybersecurity req.", "SYS": "system req.",
}
STANDARD = {
  "H": "ISO 26262", "HE": "ISO 26262", "SG": "ISO 26262", "AOU": "ISO 26262", "FSR": "ISO 26262",
  "TSR": "ISO 26262", "SWSR": "ISO 26262", "HWSR": "ISO 26262", "SH": "ISO 21448", "TC": "ISO 21448",
  "FI": "ISO 21448", "FM": "ISO 21448", "AIR": "ISO/PAS 8800", "DSR": "ISO/PAS 8800",
  "TS": "ISO/SAE 21434", "CSG": "ISO/SAE 21434", "CSR": "ISO/SAE 21434", "SYS": "ASPICE",
}
STANDARDS = ["ISO 26262", "ISO 21448", "ISO/PAS 8800", "ISO/SAE 21434", "ASPICE"]


@dataclass(frozen=True)
class Level:
  key: str            # block id in the diagram
  process: str        # ASPICE 4.0 process ID(s)
  name: str
  wps: tuple[str, ...]
  kinds: tuple[str, ...] = ()       # items produced at this level (left side)
  tests: tuple[str, ...] = ()       # test-spec prefixes (right side)


LEFT = [
  Level("SYS1", "SYS.1", "Requirements elicitation", ("WP-C-01", "WP-C-02", "WP-C-03", "WP-C-05", "WP-C-09"),
        kinds=("AOU", "H", "HE", "SG", "SH", "TS")),
  Level("SYS2", "SYS.2", "System requirements analysis", ("WP-S-01", "WP-C-04", "WP-S-02", "WP-C-07", "WP-C-10"),
        kinds=("SYS", "FSR", "TSR", "TC", "FI", "FM", "CSG")),
  Level("SYS3", "SYS.3", "System architectural design", ("WP-S-03", "WP-S-05", "WP-S-07"), kinds=("CSR",)),
  Level("SWE1", "SWE.1", "SW requirements analysis", ("WP-W-02",), kinds=("SWSR",)),
  Level("HWE1", "HWE.1", "HW requirements analysis", ("WP-H-01",), kinds=("HWSR",)),
  Level("MLE1", "MLE.1", "ML requirements analysis", ("WP-C-11",), kinds=("AIR", "DSR")),
  Level("SWE2", "SWE.2", "SW architectural design", ("WP-W-03",)),
  Level("HWE2", "HWE.2", "HW design", ("WP-H-02",)),
  Level("SWE3", "SWE.3", "SW detailed design and unit construction", ("WP-W-05",)),
]
RIGHT = [
  Level("VAL1", "VAL.1", "Validation", ("WP-V-01",), tests=("VS-VAL",)),
  Level("SYS5", "SYS.5", "System verification", ("WP-S-09",), tests=("VS-SQ",)),
  Level("SYS4", "SYS.4", "System integration and integration verification", ("WP-S-08", "WP-V-05"),
        tests=("VS-SI", "VS-FI")),
  Level("SWE6", "SWE.6", "SW verification", ("WP-W-08",), tests=("VS-SWQ",)),
  Level("HWE4", "HWE.4", "Verification against HW requirements", ("WP-H-06",), tests=("VS-HW",)),
  Level("MLE4", "MLE.4", "ML model testing", ("WP-W-10",), tests=("VS-ML",)),
  Level("SWE5", "SWE.5", "SW component verification and integration verification", ("WP-W-07",), tests=("VS-SWI",)),
  Level("HWE3", "HWE.3", "Verification against HW design", ("WP-H-06",), tests=("VS-HW",)),
  Level("SWE4", "SWE.4", "SW unit verification", ("WP-W-06",), tests=("VS-UV",)),
]
# Verification pairs across the V: left level, right level, the kinds whose coverage is measured.
PAIRS = [
  ("SYS1", "VAL1", ("SG", "SH")),
  ("SYS2", "SYS5", ("SYS", "FSR", "TSR")),
  ("SYS3", "SYS4", ("TSR",)),
  ("SWE1", "SWE6", ("SWSR",)),
  ("HWE1", "HWE4", ("HWSR",)),
  ("MLE1", "MLE4", ("AIR", "DSR")),
  ("SWE2", "SWE5", ("SWSR",)),
  ("HWE2", "HWE3", ("HWSR",)),
  ("SWE3", "SWE4", ("SWSR",)),
]
# Derivation links on the left, from the trace data: (parent kind, child kind, label, parents that need a child).
DERIVATIONS = [
  ("H", "HE", "hazard -> hazardous event", None),
  ("HE", "SG", "hazardous event -> safety goal", None),
  ("SG", "FSR", "safety goal -> FSR", None),
  ("FSR", "TSR", "FSR -> TSR", None),
  ("TSR", "SWSR", "TSR -> SWSR (SW-allocated TSRs)", ct.SW_ALLOC),
  ("TSR", "HWSR", "TSR -> HWSR (HW-allocated TSRs)", ct.HW_ALLOC),
  ("SH", "FI", "SOTIF hazard -> functional insufficiency", None),
  ("SH", "TC", "SOTIF hazard -> triggering condition", None),
  ("TS", "CSG", "threat scenario -> cybersecurity goal", None),
  ("CSG", "CSR", "cybersecurity goal -> cybersecurity requirement", None),
]
ALLOC = {(d[0], d[1]): d[3] for d in DERIVATIONS}
# One colour rule with vmodel.py: a case naming an item is a specified link, never green (green is approved or passed).
STATUS_FILL = {"full": "#EFF6FF", "partial": "#FFFBEB", "none": "#FEF2F2", "untraced": "#F8FAFC"}
STATUS_STROKE = {"full": "#2563EB", "partial": "#D97706", "none": "#D2553F", "untraced": "#94A3B8"}
STATUS_WORD = {"full": "complete", "partial": "partial", "none": "missing", "untraced": "not in trace data"}

ID_RE = re.compile(r"(?<![\w-])(SG|FSR|TSR|SWSR|HWSR|SYS|AIR|DSR|MLR|SH|TC|FI|FM|CSR|CSG|TS|AOU|HE|H)-(\d{2,3}(?:\.\d{1,2})?)([a-z]?)\b(?!\.x)")
# "FSR-01.xx…07.xx": every FSR of goals 01…07; "HE-01.x": every hazardous event of hazard H-01
WILD_RE = re.compile(r"(?<![\w-])(FSR|HE)-(\d{2})\.xx?(?:\s*…\s*(?:\1-)?(\d{2})\.xx?)?")
RANGE_RE = re.compile(r"(?<![\w-])(TSR|SWSR|HWSR|SYS|AIR|DSR|CSR)-(\d{3}|\d{2})\s*[…–-]\s*(?:\1-)?(\d{3}|\d{2})\b")
BARE_RE = re.compile(r"(?<![\w.-])(\d{3})([a-z]?)(?:\s*[–…]\s*(\d{3}))?(?![\w.])")
ROW_ID_RE = re.compile(r"^\|\s*\*{0,2}([A-Z]{1,4}-\d{2,3}(?:\.\d{1,2})?[a-z]?)\*{0,2}\s*\|")
TEST_ROW_RE = re.compile(r"^\|\s*\*{0,2}(VS-[A-Z]+-\d{2,3}[a-z]?)\*{0,2}\s*\|")
SEP_RE = re.compile(r"^\|[-| :]+\|\s*$")


# ---------------------------------------------------------------- data

def load_items() -> dict[str, dict]:
  items: dict[str, dict] = {}
  for path in sorted((TRACE_DIR / "items").glob("*.yaml")):
    for it in ct.load_yaml(path):
      items[it["id"]] = it
  return items


def doc_ids() -> dict[str, set[str]]:
  """IDs of each document-only kind: the first cell of a table row in its defining work products."""
  out: dict[str, set[str]] = {k: set() for k in DOC_KINDS}
  for kind, files in DOC_KINDS.items():
    for rel in files:
      for line in (ASSURANCE_DIR / rel).read_text(encoding="utf-8").splitlines():
        m = ROW_ID_RE.match(line)
        if m and m.group(1).split("-")[0] == kind:
          out[kind].add(m.group(1))
  return out


def split_row(line: str) -> list[str]:
  cells = re.split(r"(?<!\\)\|", line.strip())
  return [c.strip() for c in cells[1:-1]]


def header_kind(header: str) -> str | None:
  """The requirement kind a column holds as bare numbers ("SWSRs" -> SWSR), if any."""
  for kind in ("SWSR", "HWSR", "TSR"):
    if re.search(rf"\b{kind}s?\b", header) and "/" not in header:
      return kind
  return None


def refs_in(text: str, bare_kind: str | None, known: set[str]) -> set[str]:
  """Requirement IDs named in a cell: prefixed IDs, prefixed ranges, and bare numbers in a typed column."""
  found = {f"{k}-{n}{s}" for k, n, s in ID_RE.findall(text)}
  for kind, lo, hi in WILD_RE.findall(text):
    groups = range(int(lo), int(hi or lo) + 1)
    found |= {i for i in known if i.startswith(f"{kind}-") and int(i.split("-")[1][:2]) in groups}
  for kind, lo, hi in RANGE_RE.findall(text):
    for n in range(int(lo), int(hi) + 1):
      cand = f"{kind}-{n:0{len(lo)}d}"
      if cand in known:
        found.add(cand)
  if bare_kind:
    for lo, suf, hi in BARE_RE.findall(text):
      if hi:
        found |= {f"{bare_kind}-{n}" for n in range(int(lo), int(hi) + 1) if f"{bare_kind}-{n}" in known}
      else:
        found.add(f"{bare_kind}-{lo}{suf}")
  return found


def test_specs(known: set[str]) -> dict[str, dict[str, set[str]]]:
  """prefix -> case ID -> requirement IDs it names. Only specification tables (first header cell "ID")."""
  out: dict[str, dict[str, set[str]]] = {}
  for path in sorted(ASSURANCE_DIR.rglob("*.md")):
    if "maps" in path.parts:
      continue
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] | None = None
    for i, line in enumerate(lines):
      if line.startswith("|") and i + 1 < len(lines) and SEP_RE.match(lines[i + 1]):
        header = split_row(line)
        continue
      m = TEST_ROW_RE.match(line)
      if not m or not header or header[0] != "ID":
        continue
      cells = split_row(line)
      refs: set[str] = set()
      for col, cell in zip(header[1:], cells[1:], strict=False):
        refs |= refs_in(cell, header_kind(col), known)
      prefix = m.group(1).rsplit("-", 1)[0]
      out.setdefault(prefix, {}).setdefault(m.group(1), set()).update(refs)
  return out


@dataclass
class Model:
  items: dict[str, dict]
  ids: dict[str, set[str]]           # kind -> all known IDs (trace data and documents)
  in_trace: set[str]                 # kinds present in the trace data
  specs: dict[str, dict[str, set[str]]]


def build() -> Model:
  items = load_items()
  ids: dict[str, set[str]] = {}
  for iid, it in items.items():
    ids.setdefault(YAML_KIND[it["kind"]], set()).add(iid)
  in_trace = set(ids)
  for kind, found in doc_ids().items():
    ids.setdefault(kind, set()).update(found)
  known = set().union(*ids.values())
  return Model(items, ids, in_trace, test_specs(known))


# ---------------------------------------------------------------- coverage

def status_of(done: int, total: int) -> str:
  if total == 0:
    return "untraced"
  return "full" if done == total else "partial" if done else "none"


def derivation(m: Model, parent: str, child: str, alloc: tuple[str, ...] | None) -> tuple[int, int, list[str]]:
  """Parents of kind `parent` that have >= 1 child of kind `child` in the trace data."""
  if parent not in m.in_trace or child not in m.in_trace:
    return 0, 0, []
  pool = sorted(p for p in m.ids[parent] if m.items[p].get("status") != "withdrawn")
  if alloc:
    pool = [p for p in pool if any(t in m.items[p].get("allocated_to", "") for t in alloc)]
  if child == "SG":
    pool = [p for p in pool if not m.items[p].get("sg_exempt_reason")]  # QM events exempt with a reason (K12)
  linked = {p for c in m.ids[child] for p in m.items[c].get("parents") or []}
  if (parent, child) == ("FSR", "TSR"):  # an FSR that only applies other FSRs is covered through them (K4)
    for p in pool:
      shared = [r for r in ct.expand_fsr_refs(m.items[p].get("text", "")) if r != p]
      if shared and all(r in linked for r in shared):
        linked.add(p)
  missing = [p for p in pool if p not in linked]
  return len(pool) - len(missing), len(pool), missing


def pool_for(m: Model, right: str, kind: str) -> list[str]:
  """Items a verification level is expected to name: TSRs allocated to operation (OPS, WP-S-06) are verified in
  production and operation, not on the V."""
  pool = sorted(m.ids.get(kind, set()))
  if kind == "TSR":
    pool = [t for t in pool if m.items[t].get("allocated_to") != "OPS"]
  return pool


def verified_by(m: Model, right: str, kind: str) -> tuple[int, int, list[str]]:
  """Items of `kind` expected at `right` that at least one of its test cases names."""
  named = {r for p in level(right).tests for refs in m.specs.get(p, {}).values() for r in refs}
  pool = pool_for(m, right, kind)
  missing = [i for i in pool if i not in named]
  return len(pool) - len(missing), len(pool), missing


def dangling(m: Model) -> dict[str, list[str]]:
  """Test cases that name an ID of a known kind that is defined nowhere."""
  known = set().union(*m.ids.values())
  out: dict[str, list[str]] = {}
  for cases in m.specs.values():
    for case, refs in sorted(cases.items()):
      bad = sorted(r for r in refs if r.split("-")[0] in m.ids and r not in known)
      if bad:
        out[case] = bad
  return dict(sorted(out.items()))


def level(key: str) -> Level:
  return next(lv for lv in LEFT + RIGHT if lv.key == key)


def pair_status(m: Model, right: str, kinds: tuple[str, ...]) -> tuple[str, str]:
  parts, done_all, total_all = [], 0, 0
  for kind in kinds:
    done, total, _ = verified_by(m, right, kind)
    if total:
      parts.append(f"{kind} {done}/{total}")
      done_all += done
      total_all += total
  return status_of(done_all, total_all), " · ".join(parts) or "no items"


def left_status(m: Model, lv: Level) -> str:
  traced = [k for k in lv.kinds if k in m.in_trace]
  return "all" if lv.kinds and len(traced) == len(lv.kinds) else "some" if traced else "none"


# ---------------------------------------------------------------- rendering

LEFT_STYLE = {"all": "fill:#EFF6FF,stroke:#2563EB", "some": "fill:#FFFBEB,stroke:#D97706",
              "none": "fill:#F8FAFC,stroke:#94A3B8,stroke-dasharray:5 4"}


def para(*parts: str) -> str:
  return " ".join(parts)


def q(text: str) -> str:
  return text.replace('"', "'")


SHORT = {"SYS1": "Requirements elicitation", "SYS2": "System requirements", "SYS3": "System architecture",
         "SWE1": "SW requirements", "HWE1": "HW requirements", "MLE1": "ML requirements", "SWE2": "SW architecture",
         "HWE2": "HW design", "SWE3": "SW unit design and code", "VAL1": "Validation", "SYS5": "System verification",
         "SYS4": "System integration test", "SWE6": "SW verification", "HWE4": "HW req. verification",
         "MLE4": "ML model testing", "SWE5": "SW integration test", "HWE3": "HW design verification",
         "SWE4": "SW unit verification"}
# Derivation shown inside the child box: box -> (parent kind, child kind)
BOX_DERIVED = {"SYS2": ("SG", "FSR"), "SWE1": ("TSR", "SWSR"), "HWE1": ("TSR", "HWSR")}


def lines(parts: list[str], per: int = 3) -> list[str]:
  return [" · ".join(parts[i:i + per]) for i in range(0, len(parts), per)]


def left_label(m: Model, lv: Level) -> str:
  body = lines([f"{k} {len(m.ids.get(k, ()))}" + ("" if k in m.in_trace else "*") for k in lv.kinds])
  if lv.key in BOX_DERIVED:
    parent, child = BOX_DERIVED[lv.key]
    done, total, _ = derivation(m, parent, child, ALLOC.get((parent, child)))
    body.append(f"<i>from {parent}: {done}/{total}</i>")
  return q("<br/>".join([f"<b>{lv.process}</b>", SHORT[lv.key], *body]))


def right_label(m: Model, lv: Level) -> str:
  body = [f"{p}: {len(m.specs.get(p, {}))} cases" for p in lv.tests]
  return q("<br/>".join([f"<b>{lv.process}</b>", SHORT[lv.key], *body]))


V_ROWS = [
  (["SYS1"], ["VAL1"]),
  (["SYS2"], ["SYS5"]),
  (["SYS3"], ["SYS4"]),
  (["SWE1", "HWE1", "MLE1"], ["SWE6", "HWE4", "MLE4"]),
  (["SWE2", "HWE2"], ["SWE5", "HWE3"]),
  (["SWE3"], ["SWE4"]),
]
V_DOWN = [("SYS1", "SYS2"), ("SYS2", "SYS3"), ("SYS3", "L3"), ("L3", "L4"), ("L4", "SWE3")]  # L3, L4: the stacked SWE/HWE/MLE boxes


def v_model(m: Model) -> str:
  """ASPICE V as a block grid: depth d on the left at column d, its verification level at column width-1-d."""
  width = 2 * len(V_ROWS) + 1
  out = ["block-beta", f"  columns {width}"]
  for depth, (lefts, rights) in enumerate(V_ROWS):
    for col in range(width):
      if col == depth:
        out.append(stack(m, f"L{depth}", lefts, left_label))
      elif col == width - 1 - depth:
        out.append(stack(m, f"R{depth}", rights, right_label))
      else:
        out.append("  space")
  out += [f"  {a} --> {b}" for a, b in V_DOWN]
  for left, right, kinds in PAIRS:
    out.append(f'  {right} -. "{pair_status(m, right, kinds)[1]}" .-> {left}')
  for _, right, kinds in PAIRS:
    st = pair_status(m, right, kinds)[0]
    out.append(f"  style {right} fill:{STATUS_FILL[st]},stroke:{STATUS_STROKE[st]},stroke-width:2px")
  out += [f"  style {lv.key} {LEFT_STYLE[left_status(m, lv)]}" for lv in LEFT]
  return "\n".join(out)


def stack(m: Model, group: str, keys: list[str], label) -> str:
  if len(keys) == 1:
    return f'  {keys[0]}["{label(m, level(keys[0]))}"]'
  inner = "\n".join(f'    {k}["{label(m, level(k))}"]' for k in keys)
  return f"  block:{group}\n    columns 1\n{inner}\n  end"


# ---------------------------------------------------------------- SVG (Figure 1)

def svg_v_model(m: Model) -> str:
  """Figure 1: the system V of vmodel.py, trace lens, full size (the same component the figures and the snapshot use)."""
  import vmodel  # imports this module; imported here to avoid a cycle
  return vmodel.render("trace", "full", model=m)


LANES = [  # standard, item kinds in the lane, links (parent -> child)
  ("ISO 26262", ["H", "HE", "SG", "FSR", "TSR", "SWSR", "HWSR", "AOU"],
   [("H", "HE"), ("HE", "SG"), ("SG", "FSR"), ("FSR", "TSR"), ("TSR", "SWSR"), ("TSR", "HWSR"), ("AOU", "SG")]),
  ("ISO 21448", ["SH", "TC", "FI", "FM"], [("SH", "TC"), ("SH", "FI"), ("TC", "FM"), ("FI", "FM"), ("SH", "H")]),
  ("ISO/PAS 8800", ["AIR", "DSR"], [("FI", "AIR"), ("AIR", "DSR")]),
  ("ISO/SAE 21434", ["TS", "CSG", "CSR"], [("TS", "CSG"), ("CSG", "CSR"), ("CSG", "SG")]),
  ("ASPICE", ["SYS"], [("SYS", "TSR")]),
]


def chains(m: Model) -> str:
  """One lane per standard; solid boxes and links where the trace data has them, dashed where only documents do."""
  out = ["flowchart LR"]
  for std, kinds, _ in LANES:
    sid = re.sub(r"[^A-Za-z0-9]", "", std)
    out += [f'  subgraph {sid}["{std}"]', "    direction LR"]
    for kind in kinds:
      cls = "traced" if kind in m.in_trace else "doc"
      out.append(f'    k{kind}["<b>{kind}</b> {len(m.ids.get(kind, ()))}<br/>{KIND_NAME[kind]}"]:::{cls}')
    out += ["  end", f"  style {sid} fill:#FFFFFF,stroke:#CBD5E1"]
  for _, _, links in LANES:
    for a, b in links:
      if a in m.in_trace and b in m.in_trace and (a, b) in ALLOC:
        done, total, _ = derivation(m, a, b, ALLOC[(a, b)])
        out.append(f'  k{a} -->|"{done}/{total}"| k{b}')
      elif a in m.in_trace and b in m.in_trace:
        out.append(f"  k{a} --> k{b}")
      else:
        out.append(f"  k{a} -.-> k{b}")
  out.append("  classDef traced fill:#DBEAFE,stroke:#2563EB,color:#0F172A")
  out.append("  classDef doc fill:#F1F5F9,stroke:#94A3B8,stroke-dasharray:4 3,color:#475569")
  return "\n".join(out)


def fm_scope(m: Model) -> list[str]:
  """Modifications whose stated scope (WP-C-07 §2 'Addresses') differs from the SOTIF hazards of the WP-C-06 §5
  rows that name them."""
  out = []
  for fid in sorted(m.ids.get("FM", ())):
    fm = m.items[fid]
    rows = {p for p in fm.get("parents") or [] if p.startswith("TC-")}
    via = {sh for tc in rows for sh in m.items[tc].get("parents") or []}
    stated = set(fm.get("addresses") or [])
    if stated != via:
      diff = [f"also {', '.join(sorted(stated - via))}" if stated - via else "",
              f"not {', '.join(sorted(via - stated))}" if via - stated else ""]
      out.append(f"{fid} ({'; '.join(x for x in diff if x)})")
  return out


def table(header: list[str], rows: list[list[str]]) -> list[str]:
  return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows]


def id_list(ids: list[str], limit: int = 40) -> str:
  if not ids:
    return "—"
  shown = ", ".join(ids[:limit])
  return shown + (f" … (+{len(ids) - limit})" if len(ids) > limit else "")


def render(m: Model) -> str:
  verified = sum(1 for it in m.items.values() if it.get("status") == "verified")
  links_path = TRACE_DIR / "links" / "verification.yaml"
  ver = ct.load_yaml(links_path) if links_path.exists() else []
  out = [
    "# ASPICE-Aligned Traceability Map (WP-T-01)",
    "",
    "<!-- Generated by assurance/trace/tools/trace_map.py. Do not edit by hand; run the script. CI fails if this file is stale. -->",
    "",
    "| Field | Value |",
    "|---|---|",
    "| Work product | Part of WP-T-01 Requirements and traceability data: generated view |",
    para("| Standard reference | ASPICE 4.0 SYS.1–SYS.5, SWE.1–SWE.6, HWE.1–HWE.4, MLE.1, MLE.4 and VAL.1",
         "(traceability and consistency BPs); ISO 26262-8:2018 §6.4.3; ISO 21448:2022; ISO/PAS 8800:2024; ISO/SAE 21434:2021 |"),
    "| Status | Generated. Shows what the trace data and the specifications contain, not a verification result |",
    para("| Sources | [`items/*.yaml`](../items/), the requirement tables of the defining work products and the test",
         "specifications listed in §2; generator [`tools/trace_map.py`](../tools/trace_map.py) |"),
    "",
    "## 1. The V-model",
    "",
    para("Specification on the left, verification on the right. Each verification process sits opposite the process whose",
         "work products it verifies (ASPICE 4.0): the system trunk (SYS.1–SYS.3, SYS.4, SYS.5 and VAL.1) steps inward, then",
         "one dashed bracket holds the software, hardware and machine-learning arms side by side. Each specification box",
         "lists the items its process holds (`*`: kinds defined in the work products but not yet in the trace data) and,",
         "where the trace data has the link, \"from SG 7/7\": the parents with at least one child. Each verification box",
         "lists the cases of its test specifications, then the items of the paired level they name. Arrows down the left",
         "and up the right follow decomposition and integration; dashed arrows across the V are verification links,",
         "labelled with the same counts in the trunk. The work products of each process are listed in §2."),
    "",
    f"![Figure 1: ASPICE 4.0 system V, trace lens: item counts per process and verification coverage across the V]({FIG.name})",
    "",
    para("*Figure 1.* The system V of [`tools/vmodel.py`](../tools/vmodel.py), trace lens, drawn from the same data as the",
         "tables below; the same component draws the status and per-goal Vs of the README and the safety case snapshot. Source:",
         f"[`{FIG.name}`]({FIG.name}); the Mermaid version follows as a text alternative."),
    "",
    "<details><summary>Mermaid version of Figure 1</summary>",
    "",
    "```mermaid",
    v_model(m),
    "```",
    "",
    "</details>",
    "",
    para("One colour rule for every V: blue when every item of the level is in the trace data, or every item of the",
         "paired level is named by a case (done in the design, not verified); amber when some are; red when none is;",
         "dashed grey when the level holds nothing yet. Green is kept for approved work products and passed verification;",
         "nothing here is either. The gate band shows the gate records of WP-M-00 §2 (none held yet)."),
    "",
    para(f"A named item is a **specified** link, not a passed test. {verified} of {len(m.items)} traced items carry status",
         f"`verified`. [`links/verification.yaml`](../links/verification.yaml) links {len(ver)} existing tests to",
         f"{len({r for ln in ver for r in ln.get('reqs') or []})} requirements (WP-W-06 §4.1, §4.9) and records no result;",
         "the code and tests carry no `@req` tags yet (WP-P-06 §6; checks K7–K10 in the [README](../README.md) §6",
         "are not implemented)."),
    "",
    "## 2. Process to work product and items",
    "",
  ]
  rows = []
  for lv in LEFT:
    kinds = ", ".join(f"{k} ({len(m.ids.get(k, ()))}, {'trace data' if k in m.in_trace else 'document'})" for k in lv.kinds)
    rows.append([f"**{lv.process}**", lv.name, ", ".join(lv.wps), kinds or "—"])
  for lv in RIGHT:
    cases = ", ".join(f"{p} ({len(m.specs.get(p, {}))} cases)" for p in lv.tests)
    rows.append([f"**{lv.process}**", lv.name, ", ".join(lv.wps), cases])
  out += table(["Process", "Name", "Work products", "Items or test cases"], rows)

  out += ["", "## 3. Traceability per standard", "",
          para("One lane per standard. Solid boxes and arrows are in the trace data, labelled with the parents that have",
               "at least one child; dashed ones exist only in the work-product tables and are not linked yet."),
          "", "```mermaid", chains(m), "```", ""]
  rows = []
  for std in STANDARDS:
    kinds = [k for k in KIND_NAME if STANDARD[k] == std]
    traced = [f"{k} {len(m.ids.get(k, ()))}" for k in kinds if k in m.in_trace]
    docs = [f"{k} {len(m.ids.get(k, ()))}" for k in kinds if k not in m.in_trace]
    rows.append([std, ", ".join(kinds), ", ".join(traced) or "—", ", ".join(docs) or "—"])
  out += table(["Standard", "Kinds", "In trace data", "Defined in documents only"], rows)

  out += ["", "## 4. Derivation coverage (left side of the V)", "",
          "Parents with at least one child in the trace data (WP-T-01 checks K4, K12).", ""]
  rows = []
  for parent, child, label, alloc in DERIVATIONS:
    done, total, missing = derivation(m, parent, child, alloc)
    rows.append([label, f"{done}/{total}", STATUS_WORD[status_of(done, total)], id_list(missing)])
  out += table(["Link", "Covered", "Status", "Without a child"], rows)
  scope = fm_scope(m)
  if scope:
    out += ["", para("SOTIF modifications whose stated scope (WP-C-07 §2, *Addresses*) differs from the SOTIF hazards of",
                     "the WP-C-06 §5 rows that name them, for review; a modification can address a hazard directly, so",
                     f"this is not an error: {'; '.join(scope)}. *Also* lists hazards only WP-C-07 names, *not* those",
                     "only the §5 rows give.")]

  out += ["", "## 5. Verification coverage (across the V)", "",
          para("Items named by at least one case of the paired test specification. A case names an item by its ID, by a",
               "range (`TSR-101…105`), by `FSR-01.xx…07.xx`, or by a bare number in a column headed with the kind",
               "(`SWSRs`). Bare ranges include only IDs without a letter suffix. TSRs allocated to operation (`OPS`,",
               "WP-S-06) are left out."),
          ""]
  rows = []
  for left, right, kinds in PAIRS:
    for kind in kinds:
      done, total, missing = verified_by(m, right, kind)
      rows.append([f"{level(left).process} ↔ {level(right).process}", ", ".join(level(right).tests), kind,
                   f"{done}/{total}", STATUS_WORD[status_of(done, total)], id_list(missing)])
  out += table(["Pair", "Test specification", "Kind", "Named", "Status", "Not named"], rows)

  bad = dangling(m)
  out += ["", "## 6. Test cases naming unknown IDs", ""]
  if bad:
    out += ["Each ID below is named by a case but defined neither in the trace data nor in its work product.", ""]
    out += table(["Case", "Unknown IDs"], [[c, ", ".join(ids)] for c, ids in bad.items()])
  else:
    out.append("None.")
  untraced = ", ".join(f"{k} ({len(m.ids.get(k, ()))})" for k in KIND_NAME if k not in m.in_trace)
  dashed = ", ".join(f"{a} → {b}" for _, _, links in LANES for a, b in links if not (a in m.in_trace and b in m.in_trace))
  out += ["", "## 7. Not yet traced", "",
          para(f"- **Kinds outside the trace data:** {untraced}. Their links ({dashed}) are dashed in §3 until they",
               "are added to `items/` (README §3.1).") if untraced else
          "- **Kinds outside the trace data:** none; every kind of §3 is in `items/`.",
          para("- **Allocation to elements** (SYS.3, SWE.2, HWE.2): `allocated_to` holds work-product cells; element IDs",
               "need `elements.yaml` (WP-P-06 OI-4)."),
          para("- **Code and test results:** no `@req` tags yet, so the SWE.3 → code link is absent;",
               f"`links/verification.yaml` links {len(ver)} tests to requirements but no test → result link exists",
               "(WP-P-06 §5.3, §6; check K7)."),
          ""]
  return "\n".join(out)


def main(argv: list[str]) -> int:
  m = build()
  outputs = {OUT: render(m), FIG: svg_v_model(m)}
  if "--check" in argv:
    stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    for p in stale:
      print(f"{p.relative_to(ASSURANCE_DIR.parent)} is stale; run assurance/trace/tools/trace_map.py")
    if not stale:
      print("trace map: up to date")
    return 1 if stale else 0
  OUT.parent.mkdir(exist_ok=True)
  for p, text in outputs.items():
    p.write_text(text, encoding="utf-8")
    print(f"wrote {p.relative_to(ASSURANCE_DIR.parent)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
