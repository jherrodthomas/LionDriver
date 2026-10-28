#!/usr/bin/env python3
"""Consistency checker for the LionDriver trace data (WP-T-01, WP-P-06 section 7).

Checks implemented so far (IDs per assurance/trace/README.md section 6):
  K1  item files parse and carry the mandatory keys for their kind
  K2  IDs are unique and match the ID pattern
  K3  every reference (parents, aou_dependency) resolves
  K5  a requirement's ASIL is not below any parent's, unless decomposed (X(Y), cited in WP-A-01) or a QM requirement
      backed by a named envelope requirement (QM (X-sup), WP-S-02 §2.1); B‡ counts as C. Findings recorded with
      their owning open item in links/k5-known.yaml are reported as known; a new finding, or an entry that no longer
      occurs, is an error, so the list only shrinks
  K6  every requirement a test links to in links/verification.yaml exists, is a requirement and is not withdrawn
      (the @req tags of the same check are not implemented)
  K12 every hazardous event is linked to a safety goal or has sg_exempt_reason
  R1  hazardous-event ASIL equals the risk-graph result of S, E, C
  R2  safety-goal ASIL equals the highest ASIL of its source hazardous events
  R3  asil_if_aou_fails is not lower than asil and only appears with aou_dependency
  R4  every hazard has at least one hazardous event
  S1  SOTIF: every SOTIF hazard in use has a functional insufficiency and a triggering condition; every
      insufficiency is evaluated with a triggering condition; every SOTIF hazard of a triggering condition is
      reached through its insufficiencies (WP-C-06 §5); every functional modification is named by an evaluation row
  A1  AI: every AI safety and dataset requirement has a parent or names what it rests on; every TSR whose row names
      an AI safety requirement is listed in that requirement's related_tsr (a TSR need not cite the AIRs it refines)
  C1  Cybersecurity: every threat scenario treated by reduction or avoidance has a cybersecurity goal; every goal has
      a cybersecurity requirement; every safety goal is protected by a cybersecurity goal; every cybersecurity
      requirement has a parent goal or says what it rests on
  Q1  ASPICE system requirements: every one names its function, its allocation and its WP-S-01 §10 traceability row
  I1  Interfaces (DQ-129 A): every IFR item names one interface of the process model, two different owners and a
      status of proposed, agreed or withdrawn; it is agreed only with no open item and a review_ref to an accepted
      review record in case/reviews/reviews.yaml that lists it
  X1  hazardous events and safety goals match the tables in WP-C-03
  X2  assumptions of use match the table in WP-C-01
  X3  the generated requirement and SOTIF items equal a fresh extraction from their work products

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
LINKS = TRACE_DIR / "links" / "verification.yaml"
# README §5: only requirements may be linked to a test, never a goal or a hazard
LINKABLE = {"fsr", "tsr", "swsr", "hwsr", "cybersecurity-requirement", "ai-requirement", "system-requirement",
            "functional-modification"}
HARA_MD = ASSURANCE_DIR / "02-concept" / "WP-C-03-hara.md"
ITEMDEF_MD = ASSURANCE_DIR / "02-concept" / "WP-C-01-item-definition.md"
REVIEWS = ASSURANCE_DIR / "case-records" / "reviews" / "reviews.yaml"
INTERFACES = ASSURANCE_DIR / "process" / "model" / "interfaces.yaml"

ID_RE = re.compile(
  r"^((H|HE|HS|SG|FSR|TSR|SWSR|HWSR|SH|TC|FI|FM|SOTIF|AIR|DSR|MLR|MON|KS|DVR|DEV|TS|CSG|CSR|SYS|AOU|IFR)"
  + r"-[0-9]{2,3}(\.[0-9]{1,2})?[a-z]?|VS-[A-Z]{2,4}-[0-9]{2,3}[a-z]?)$")
FUNC_RE = re.compile(r"^F-[0-9]{2}$")
STATUS = {"proposed", "agreed", "implemented", "verified", "withdrawn"}
IFR_STATUS = {"proposed", "agreed", "withdrawn"}  # an interface is agreed, never implemented or verified itself
ASIL_ORDER = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
K5_KINDS = ("fsr", "tsr", "swsr", "hwsr")
K5_KNOWN = TRACE_DIR / "links" / "k5-known.yaml"
WP_A01 = ASSURANCE_DIR / "08-analyses" / "WP-A-01-asil-decomposition.md"
# one rated part of an `asil` field: a level, ‡ (B‡: ASIL C applies, WP-S-02 §2.1), a decomposition X(Y), and a
# QM backstop "(X-sup)" or "(X-sup: TSR-…, …)"; "CS" and words such as "ASIL" are not levels
_ASIL_PART = re.compile(r"(?<![A-Za-z\-])(QM|[ABCD])(?![A-Za-z])(‡?)(?:\(([ABCD])\))?"
                        r"(?:\s*\(([ABCD])-sup(?::\s*([^)]*))?\))?")

REQUIRED = {
  "hazard": ["id", "kind", "title", "functions", "status", "source"],
  "hazardous-event": ["id", "kind", "parents", "situation", "effect", "s", "e", "c", "asil",
                      "aou_flag", "aou_dependency", "asil_if_aou_fails", "status", "source"],
  "safety-goal": ["id", "kind", "text", "type", "asil", "asil_if_aou_fails", "aou_dependency",
                  "parents", "safe_state", "ftti_ms", "ftti_text", "status", "source"],
  "aou": ["id", "kind", "text", "credited_in", "verification_approach", "aou_status", "status", "source"],
  "fsr": ["id", "kind", "text", "asil", "parents", "allocated_to", "verification", "baseline_impl", "status", "source"],
  "tsr": ["id", "kind", "text", "asil", "parents", "parent_text", "other_parents", "allocated_to", "verification",
          "baseline_impl", "status", "source"],
  "swsr": ["id", "kind", "text", "asil", "parents", "parent_text", "other_parents", "allocated_to", "verification",
           "acceptance", "baseline_impl", "status", "source"],
  "hwsr": ["id", "kind", "text", "asil", "parents", "parent_text", "other_parents", "allocated_to", "hw_kind",
           "verification", "baseline_impl", "status", "source"],
  "sotif-hazard": ["id", "kind", "text", "functions", "function_text", "situations", "shares_event", "linked_text",
                   "status", "source"],
  "functional-insufficiency": ["id", "kind", "text", "fi_type", "component", "parents", "status", "source"],
  "triggering-condition": ["id", "kind", "text", "category", "parents", "insufficiencies", "evaluation", "status",
                           "source"],
  "functional-modification": ["id", "kind", "title", "addresses", "parents", "gap_text", "priority", "status", "source"],
  "ai-requirement": ["id", "kind", "text", "category", "component", "parents", "parent_text", "other_parents",
                     "related_tsr", "verification", "baseline_impl", "status", "source"],
  "dataset-requirement": ["id", "kind", "text", "parents", "parent_text", "other_parents", "verification",
                          "baseline_impl", "status", "source"],
  "threat-scenario": ["id", "kind", "text", "stride", "assets", "violated_property", "damage_text", "gap_text", "risk",
                      "treatment", "status", "source"],
  "cybersecurity-goal": ["id", "kind", "text", "parents", "parent_text", "cal", "protects", "rationale", "status",
                         "source"],
  "cybersecurity-requirement": ["id", "kind", "text", "parents", "concept_requirement", "cal", "other_parents",
                                "allocated_to", "safety_relation", "related_tsr", "verification", "baseline_impl",
                                "status", "source"],
  "system-requirement": ["id", "kind", "text", "type", "functions", "criterion", "verification", "baseline_impl",
                         "allocated_to", "related_text", "related_tsr", "related_items", "status", "source"],
  "interface-requirement": ["id", "kind", "interface", "title", "owners", "open_item", "review_ref", "status", "source"],
}
GAP_MD = ASSURANCE_DIR / "00-assessment" / "gap-assessment.md"
PARENT_KINDS = {"fsr": {"safety-goal"}, "tsr": {"fsr", "tsr", "safety-goal", "aou"}, "swsr": {"tsr"},
                "hwsr": {"tsr", "fsr", "aou"}, "functional-insufficiency": {"sotif-hazard"},
                "triggering-condition": {"sotif-hazard"},
                "functional-modification": {"triggering-condition", "functional-insufficiency"},
                "ai-requirement": {"safety-goal", "fsr", "sotif-hazard", "triggering-condition",
                                   "functional-insufficiency", "functional-modification", "ai-requirement"},
                "dataset-requirement": {"ai-requirement", "dataset-requirement"},
                "cybersecurity-goal": {"threat-scenario"}, "cybersecurity-requirement": {"cybersecurity-goal"}}
# Other link keys: key -> kinds the reference must be (README §3.2)
REF_KINDS = {"shares_event": {"hazard", "hazardous-event"}, "insufficiencies": {"functional-insufficiency"},
             "addresses": {"sotif-hazard"}, "related_tsr": {"tsr"},
             "protects": {"safety-goal"}, "related_items": {"sotif-hazard", "ai-requirement"}}
SW_ALLOC = ("P-SW", "SoC")  # WP-S-02 allocation cells that put a TSR (also) on software
HW_ALLOC = ("P-HW", "HAR")  # ... and (also) on hardware


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
    self.known: list[str] = []      # findings recorded with their owner (K5 baseline)

  def err(self, check: str, msg: str) -> None:
    self.errors.append(f"[{check}] {msg}")


# ---------------------------------------------------------------- checks

def asil_parts(text) -> list[dict] | None:
  """The rated parts of an `asil` field, or None when the item makes no ASIL claim of its own: an external measure
  ("ext", "— (ext.)") or a cross-reference row ("as ref."). Each part: level (0 QM … 4 D; B‡ is C), dec (the
  original ASIL of a decomposed X(Y)), sup (the ASIL a QM (X-sup) requirement supports) and refs (its backstops)."""
  t = str(text or "").strip()
  if not t or t in ("n/a", "None") or re.match(r"^(—\s*)?\(?ext", t) or t.startswith("as ref"):
    return None
  parts = []
  for m in _ASIL_PART.finditer(t):
    level = "C" if m.group(2) else m.group(1)
    parts.append({"level": ASIL_ORDER[level], "dec": m.group(3), "sup": m.group(4),
                  "refs": re.findall(r"\b[A-Z]+-[0-9]{2,3}[a-z]?\b", m.group(5) or "")})
  return parts


def check_asil_inheritance(by_id: dict[str, dict], rep: Report, known: list[dict] | None = None) -> None:
  """K5: no requirement is rated below a parent (WP-P-06 §7, WP-W-02 §2). A part of the child's ASIL meets a
  parent's highest part when its level is not lower, when it is a decomposition X(Y) with Y not lower and the child is
  cited in WP-A-01, or when it is QM (X-sup) with X not lower and every named backstop rated at least X."""
  if known is None:
    known = load_yaml(K5_KNOWN) if K5_KNOWN.exists() else []
  a01 = WP_A01.read_text(encoding="utf-8") if WP_A01.exists() else ""
  owners = {(k.get("child"), k.get("parent")): k.get("owner") for k in known}
  found: set[tuple[str, str]] = set()

  def top(item) -> int | None:
    parts = asil_parts(item.get("asil"))
    return max((p["level"] for p in parts), default=None) if parts is not None else None

  for iid, it in by_id.items():
    if it["kind"] not in K5_KINDS:
      continue
    parts = asil_parts(it.get("asil"))
    if parts is None:
      continue
    if not parts:
      rep.err("K5", f"{iid}: asil {it.get('asil')!r} names no ASIL")
      continue
    for p in it.get("parents") or []:
      par = by_id.get(p)
      need = top(par) if par and "asil" in par else None
      if need is None:
        continue
      def meets(q) -> bool:
        if q["level"] >= need:
          return True
        if q["dec"] and ASIL_ORDER[q["dec"]] >= need and re.search(rf"(?<![\w.-]){re.escape(iid)}(?![\w.-]*\w)", a01):
          return True
        if q["sup"] and ASIL_ORDER[q["sup"]] >= need:
          return all(r in by_id and (top(by_id[r]) or 0) >= ASIL_ORDER[q["sup"]] for r in q["refs"])
        return False
      if any(meets(q) for q in parts):
        continue
      msg = f"{iid}: asil {it.get('asil')!r} is below its parent {p} ({par.get('asil')!r})"
      found.add((iid, p))
      if (iid, p) in owners:
        rep.known.append(f"[K5] {msg}; owner: {owners[(iid, p)]}")
      else:
        rep.err("K5", msg + " (raise it, decompose it in WP-A-01, or name its backstop as QM (X-sup))")
  kinds = {it["kind"] for it in by_id.values()}
  prefix = {"FSR": "fsr", "TSR": "tsr", "SWSR": "swsr", "HWSR": "hwsr"}
  for child, parent in owners:
    if (child, parent) in found:
      continue
    if child in by_id or prefix.get(str(child).split("-")[0]) in kinds:
      rep.err("K5", f"{K5_KNOWN.name}: {child} under {parent} no longer occurs; remove the entry")


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
  gaps = set(re.findall(r"\b(GAP-[0-9]{2})\b", GAP_MD.read_text(encoding="utf-8")))
  for iid, it in by_id.items():
    for key in ("parents", "aou_dependency"):
      for ref in it.get(key) or []:
        if key == "parents" and ref.startswith("GAP-"):
          if ref not in gaps:
            rep.err("K3", f"{iid}: parent {ref} is not in the gap assessment")
          continue
        if ref not in by_id:
          rep.err("K3", f"{iid}: {key} reference {ref} does not resolve")
        elif key == "parents" and it["kind"] in PARENT_KINDS and by_id[ref]["kind"] not in PARENT_KINDS[it["kind"]]:
          rep.err("K3", f"{iid}: parent {ref} is a {by_id[ref]['kind']}, not one of {sorted(PARENT_KINDS[it['kind']])}")
        elif key == "aou_dependency" and by_id[ref]["kind"] != "aou":
          rep.err("K3", f"{iid}: aou_dependency {ref} is not an AOU")
    for key, kinds in REF_KINDS.items():
      for ref in it.get(key) or []:
        if ref not in by_id:
          rep.err("K3", f"{iid}: {key} reference {ref} does not resolve")
        elif by_id[ref]["kind"] not in kinds:
          rep.err("K3", f"{iid}: {key} {ref} is a {by_id[ref]['kind']}, not one of {sorted(kinds)}")
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

  check_requirement_coverage(by_id, rep)
  check_sw_hw_coverage(by_id, rep)
  check_asil_inheritance(by_id, rep)
  check_sotif(by_id, rep)
  check_ai(by_id, rep)
  check_cs(by_id, rep)
  check_sys(by_id, rep)

  for iid, sg in sgs.items():
    parents = [p for p in sg.get("parents") or [] if p in hes]
    if not parents:
      rep.err("K3", f"{iid}: no source hazardous events")
      continue
    top = max((hes[p]["asil"] for p in parents), key=lambda a: ASIL_ORDER[a])
    if sg["asil"] != top:
      rep.err("R2", f"{iid}: asil {sg['asil']} but highest source HE ASIL is {top}")


def check_sotif(by_id: dict[str, dict], rep: Report) -> None:
  """S1: the SOTIF chain SH -> TC/FI -> FM is complete, and each TC's SOTIF hazards follow from its insufficiencies."""
  def of(kind: str) -> dict[str, dict]:
    return {i: x for i, x in by_id.items() if x["kind"] == kind and x.get("status") != "withdrawn"}
  shs, fis, tcs, fms = (of(k) for k in ("sotif-hazard", "functional-insufficiency", "triggering-condition",
                                        "functional-modification"))
  if not shs:
    return
  for iid in shs:
    for kind, children in (("functional insufficiency", fis), ("triggering condition", tcs)):
      if not any(iid in (x.get("parents") or []) for x in children.values()):
        rep.err("S1", f"{iid}: no {kind}")
  evaluated = {f for x in tcs.values() for f in x.get("insufficiencies") or []}
  for iid in sorted(set(fis) - evaluated):
    rep.err("S1", f"{iid}: not evaluated with a triggering condition (WP-C-06 §5)")
  for iid, tc in tcs.items():
    reached = {p for f in tc.get("insufficiencies") or [] if f in fis for p in fis[f].get("parents") or []}
    for sh in sorted(set(tc.get("parents") or []) - reached):
      rep.err("S1", f"{iid}: {sh} is not a parent of any of its insufficiencies {tc.get('insufficiencies')}")
  for iid, fm in fms.items():
    if not fm.get("parents"):
      rep.err("S1", f"{iid}: named by no evaluation row of WP-C-06 §5")


def check_ai(by_id: dict[str, dict], rep: Report) -> None:
  """A1: AI requirements rest on something, and every TSR that names an AIR is named by it."""
  ai = {i: x for i, x in by_id.items() if x["kind"] in ("ai-requirement", "dataset-requirement")}
  if not ai:
    return
  for iid, it in ai.items():
    if not it.get("parents") and not it.get("other_parents"):
      rep.err("A1", f"{iid}: no parent and names nothing it rests on")
  named = {(a, t) for a, x in ai.items() for t in x.get("related_tsr") or []}
  for tid, t in by_id.items():
    if t["kind"] != "tsr":
      continue
    cited = set(re.findall(r"\bAIR-[0-9]{2}\b", " ".join(str(t.get(k, "")) for k in ("text", "parent_text", "baseline_impl"))))
    for a in sorted(cited):
      if a in ai and (a, tid) not in named:
        rep.err("A1", f"{tid} names {a}, but {a} does not list {tid} in related_tsr (WP-C-11 Parent column)")


def check_cs(by_id: dict[str, dict], rep: Report) -> None:
  """C1: the TS -> CSG -> CSR chain is complete and every safety goal is protected by a cybersecurity goal."""
  def of(kind: str) -> dict[str, dict]:
    return {i: x for i, x in by_id.items() if x["kind"] == kind and x.get("status") != "withdrawn"}
  tss, csgs, csrs = of("threat-scenario"), of("cybersecurity-goal"), of("cybersecurity-requirement")
  if not tss:
    return
  for iid, ts in tss.items():
    if re.search(r"Reduce|Avoid", str(ts.get("treatment"))) and not any(iid in (g.get("parents") or [])
                                                                         for g in csgs.values()):
      rep.err("C1", f"{iid}: treated by {ts.get('treatment')!r} but no cybersecurity goal addresses it")
  for iid in csgs:
    if not any(iid in (r.get("parents") or []) for r in csrs.values()):
      rep.err("C1", f"{iid}: no cybersecurity requirement")
  protected = {sg for g in csgs.values() for sg in g.get("protects") or []}
  for iid in sorted(i for i, x in by_id.items() if x["kind"] == "safety-goal"):
    if iid not in protected:
      rep.err("C1", f"{iid}: protected by no cybersecurity goal (WP-C-10 §8)")
  for iid, r in csrs.items():
    if not r.get("parents") and not r.get("other_parents"):
      rep.err("C1", f"{iid}: no parent goal and names nothing it rests on")


def check_sys(by_id: dict[str, dict], rep: Report) -> None:
  """Q1: every system requirement names its function, its allocation and its traceability row."""
  for iid, it in by_id.items():
    if it["kind"] != "system-requirement":
      continue
    for key, what in (("functions", "function"), ("allocated_to", "allocation (WP-S-01 §10.1)"),
                      ("related_text", "traceability row (WP-S-01 §10)")):
      if not it.get(key):
        rep.err("Q1", f"{iid}: no {what}")


def check_interfaces(by_id: dict[str, dict], reviews: list[dict], interfaces: set[str] | None, rep: Report) -> None:
  """I1: an interface item is agreed only through an accepted review record that lists it (DQ-129 A)."""
  revs = {r.get("id"): r for r in reviews}
  seen: dict[str, str] = {}
  for iid, it in by_id.items():
    if it["kind"] != "interface-requirement":
      continue
    ix, owners, ref, status = it.get("interface"), it.get("owners"), it.get("review_ref"), it.get("status")
    if not isinstance(ix, str) or not re.fullmatch(r"IX-[0-9]{2}", ix):
      rep.err("I1", f"{iid}: interface {ix!r} is not an IX-nn")
    elif ix in seen:
      rep.err("I1", f"{iid}: interface {ix} already has {seen[ix]}")
    else:
      seen[ix] = iid
      if interfaces is not None and ix not in interfaces:
        rep.err("I1", f"{iid}: interface {ix} is not in the process model")
    if not isinstance(owners, list) or len(owners) != 2 or len(set(owners)) != 2:
      rep.err("I1", f"{iid}: owners must name two different roles")
    if status not in IFR_STATUS:
      rep.err("I1", f"{iid}: status {status!r} not in {sorted(IFR_STATUS)}")
    if ref is not None:
      rv = revs.get(ref)
      if rv is None:
        rep.err("I1", f"{iid}: review_ref {ref} is not a review record in case/reviews/reviews.yaml")
      elif status == "agreed" and (rv.get("outcome") != "accepted" or iid not in (rv.get("reviewed_objects") or [])):
        rep.err("I1", f"{iid}: agreed, but review {ref} is not accepted or does not list {iid}")
    if status == "agreed":
      if ref is None:
        rep.err("I1", f"{iid}: agreed without a review_ref; an interface is agreed only through a recorded review")
      if it.get("open_item"):
        rep.err("I1", f"{iid}: agreed while open item {it['open_item']} is open")


def interface_ids() -> set[str]:
  """IX-nn of the process model (assurance/process/model/interfaces.yaml)."""
  return {x["id"] for x in load_yaml(INTERFACES) if x.get("kind") == "interface"}


def check_verification_links(by_id: dict[str, dict], links: list[dict], rep: Report) -> None:
  """K6 for links/verification.yaml: each linked ID is an existing, non-withdrawn requirement."""
  for ln in links:
    for ref in ln.get("reqs") or []:
      it = by_id.get(ref)
      if it is None:
        rep.err("K6", f"{ln.get('test')}: links {ref}, which does not exist")
      elif it["kind"] not in LINKABLE:
        rep.err("K6", f"{ln.get('test')}: links {ref}, a {it['kind']}; only requirements may be linked (README §5)")
      elif it.get("status") == "withdrawn":
        rep.err("K6", f"{ln.get('test')}: links {ref}, which is withdrawn")
    if not ln.get("reqs"):
      rep.err("K6", f"{ln.get('test')}: links no requirement")


def check_requirement_coverage(by_id: dict[str, dict], rep: Report) -> None:
  """K3/K4 for requirements: every SG has an FSR, every FSR has a TSR (directly, or through the FSRs it shares)."""
  fsrs = {i: x for i, x in by_id.items() if x["kind"] == "fsr"}
  tsrs = {i: x for i, x in by_id.items() if x["kind"] == "tsr"}
  if not fsrs:
    return
  for iid, sg in by_id.items():
    if sg["kind"] == "safety-goal" and not any(iid in (f.get("parents") or []) for f in fsrs.values()):
      rep.err("K4", f"{iid}: no FSR")
  for iid, f in fsrs.items():
    if not f.get("parents"):
      rep.err("K3", f"{iid}: no parent safety goal")
  for iid, t in tsrs.items():
    if not t.get("parents") and not t.get("other_parents"):
      rep.err("K3", f"{iid}: no parent")
  covered = {p for t in tsrs.values() for p in t.get("parents") or []}
  for iid, f in fsrs.items():
    if iid in covered:
      continue
    shared = [r for r in expand_fsr_refs(f.get("text", "")) if r != iid]
    if shared and all(r in covered for r in shared):
      continue
    rep.err("K4", f"{iid}: no TSR, directly or through the FSRs it references")


def check_sw_hw_coverage(by_id: dict[str, dict], rep: Report) -> None:
  """K4 for the last level: every TSR allocated to software has an SWSR and every TSR allocated to hardware has an
  HWSR, unless the work product lists it as not refined into that discipline (WP-W-02 §10, WP-H-01 §4.0)."""
  import sync_requirements as sync
  tsrs = {i: x for i, x in by_id.items() if x["kind"] == "tsr"}
  for kind, alloc_tags, md, heading in (
      ("swsr", SW_ALLOC, sync.SWSR_MD, "## 10. TSRs not refined into software"),
      ("hwsr", HW_ALLOC, sync.HWSR_MD, "### 4.0 TSRs not refined into hardware")):
    children = [x for x in by_id.values() if x["kind"] == kind]
    if not children:
      continue
    covered = {p for x in children for p in x.get("parents") or []}
    exempt = set(sync.not_refined(md, heading))
    for iid, t in sorted(tsrs.items()):
      alloc = t.get("allocated_to", "")
      if any(tag in alloc for tag in alloc_tags) and iid not in covered and iid not in exempt:
        rep.err("K4", f"{iid}: allocated to {alloc!r} but has no {kind.upper()} and is not listed as not refined")


def expand_fsr_refs(text: str) -> list[str]:
  out = []
  for m in re.finditer(r"FSR-([0-9]{2})\.([0-9]{2})(?:\s*…\s*([0-9]{2})\.([0-9]{2}))?", text):
    major, lo, major2, hi = m.groups()
    if hi is None:
      out.append(f"FSR-{major}.{lo}")
    else:
      out += [f"FSR-{major}.{n:02d}" for n in range(int(lo), int(hi) + 1)]
  return out


def check_requirements_in_sync(rep: Report) -> None:
  """X3: the generated items/*.yaml equal a fresh extraction from their work products (sync_requirements.py)."""
  import sync_requirements as sync
  for name, content in sync.expected_outputs().items():
    path = ITEMS_DIR / name
    if not path.exists() or path.read_text(encoding="utf-8") != content:
      rep.err("X3", f"{name} differs from the work products; run tools/sync_requirements.py")


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
    except Exception as exc:  # report any parse failure as K1
      rep.err("K1", f"{f.name}: {exc}")
      continue
    if not isinstance(data, list):
      rep.err("K1", f"{f.name}: top level must be a list")
      continue
    items += data
  by_id = check_items(items, rep)
  check_links(by_id, rep)
  if LINKS.exists():
    check_verification_links(by_id, load_yaml(LINKS), rep)
  check_interfaces(by_id, load_yaml(REVIEWS) if REVIEWS.exists() else [], interface_ids(), rep)
  if "--no-source-compare" not in argv:
    check_against_hara(by_id, rep)
    check_against_itemdef(by_id, rep)
    check_requirements_in_sync(rep)

  kinds: dict[str, int] = {}
  for it in by_id.values():
    kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
  print(f"trace: {len(files)} files, {len(by_id)} items " +
        ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
  if rep.known:
    print(f"known: {len(rep.known)} recorded finding(s) with an owner (K5, {K5_KNOWN.name})")
  if rep.errors:
    for e in rep.errors:
      print("ERROR", e)
    print(f"FAILED: {len(rep.errors)} error(s)")
    return 1
  print("OK: all implemented checks passed")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
