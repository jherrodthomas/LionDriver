#!/usr/bin/env python3
"""Consistency checks between the SysML v2 architecture model and the work products.

The Markdown work products are the documents of record; the model is checked against them,
so a change to one without the other fails CI (assurance/models/sysml/README.md §4).

  M1  elements of WP-S-03 §3.1 exist in the model with the same integrity
  M2  firmware elements of WP-W-03 §3.1: same names, units, build scope and integrity
  M3  host components of WP-W-03 §4.1: same names and integrity
  M4  interfaces of WP-S-03 §3.3: every IF exists, its item-side elements are its endpoints
  M5  safety mechanisms of WP-S-03 §6: same set, performers and TSRs
  M6  cereal services of WP-S-03 §9 between modelled processes: same set
  M7  integrity rules: every element inside the item has an integrity; a connection between
      a QM element and an ASIL element inside the item declares the FFI claims it crosses
  M8  the allocation-resolution report (generated/allocation-resolution.md) is up to date
  M9  functions of WP-C-01 §2.1: same IDs and titles; every step of a function is performed by an element
  M10 security zones and trust boundaries of WP-S-07 §3.1 and §3.2: same rows, cell by cell; every element inside
      the item is in a zone
  M11 integration steps of WP-S-08 §3.1: same rows, cell by cell; the elements a step integrates and the interfaces
      it exercises exist in the model; every element inside the item is integrated by some step
  M12 operating modes of WP-C-01 §4: every row is a state of SM-SYS (description and actuation cell by cell) or a
      listed configuration; the record states and transitions it names exist in the state-machine records
  R1  Requirements, Satisfaction and Verification (.sysml) match the work products they are generated from
  R2  every satisfy relationship ends on an element inside the item; every SYS requirement of WP-S-01 is
      satisfied and every name in WP-S-01 §10.1 resolves
  R3  every verification case that names a requirement verifies it in the model (ranges expanded)
  N1  stakeholders and actors of WP-S-01 §1.2: every stakeholder has a need and every actor takes part in a use case,
      and nothing else does
  N2  needs of WP-S-01 §1.3: every need is refined by a requirement and served by a use case; every SYS requirement
      and every safety goal refines a need
  N3  use cases of WP-S-01 §1.4: every function of the model is performed by a use case
  B1  StateRecords.sysml and Sequences.sysml match the state-machine records and WP-S-03 §4.1 they are generated from
  B2  every unit that runs a record state machine is an element of the model; every lifeline of a sequence stands for
      an element; every record a step names is a record transition, and the state after it a state of that machine;
      every requirement a step's condition names is in the model
  B3  every lifeline of a sequence takes part in a step
  H1  Timing.sysml and Signals.sysml match WP-S-04 §3.7 and WP-S-05 §11 they are generated from
  H2  every timing budget names safety goals and TSRs of the model and adds up: FDTI + FRTI within the FTTI, FHTI equal
      to FDTI + FRTI and the margin within FTTI - FHTI wherever the cells are times; every safety goal has a budget
  H3  every HSI signal has an owner element, a TSR and test cases, and every one of them is in the model
  R4  the requirements-coverage report (generated/requirements-coverage.md) is up to date: satisfied,
      verified and derived, per kind, with the requirements that are not (informational)

Usage:
  check_model.py            run all checks
  check_model.py --write    regenerate generated/allocation-resolution.md and requirements-coverage.md, then check
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sysml_lite

SYSML_DIR = HERE.parent
ASSURANCE = SYSML_DIR.parent.parent
REPO = ASSURANCE.parent
WP_S03 = ASSURANCE / "03-system" / "WP-S-03-technical-safety-concept-architecture.md"
WP_W03 = ASSURANCE / "05-software" / "WP-W-03-software-architecture.md"
WP_C01 = ASSURANCE / "02-concept" / "WP-C-01-item-definition.md"
WP_S07 = ASSURANCE / "03-system" / "WP-S-07-cybersecurity-requirements-architecture.md"
WP_S08 = ASSURANCE / "03-system" / "WP-S-08-system-integration-test.md"
ITEMS = ASSURANCE / "trace" / "items"
REPORT = SYSML_DIR / "generated" / "allocation-resolution.md"
COVERAGE = SYSML_DIR / "generated" / "requirements-coverage.md"
KIND_NAMES = {"SG": "Safety goals (WP-C-03)", "FSR": "Functional safety requirements (WP-C-04)",
              "TSR": "Technical safety requirements (WP-S-02, WP-S-06)", "SYS": "System requirements (WP-S-01)",
              "CSR": "Cybersecurity requirements (WP-S-07)"}
OUTSIDE = {"EXT": "outside the item (AoU)", "OPS": "operations (WP-S-06)", "ENV": "release environment",
           "USR": "owner or service"}

INTEGRITY_RANK = {"AoU": 0, "Untrusted": 0, "QM": 1, "QMBsup": 2, "B": 3, "BDagger": 4, "C": 5}
ASIL = {"B", "BDagger", "C"}


class Report:
  def __init__(self):
    self.errors: list[str] = []
    self.notes: list[str] = []

  def err(self, check: str, msg: str):
    self.errors.append(f"{check}: {msg}")


# ---------------------------------------------------------------- Markdown tables

def section_table(md: str, heading: str) -> list[dict[str, str]]:
  """First table under the heading that starts with `heading`, as dicts keyed by column name."""
  lines = md.splitlines()
  try:
    start = next(i for i, ln in enumerate(lines) if ln.startswith("#") and ln.lstrip("#").strip().startswith(heading))
  except StopIteration:
    raise sysml_lite.ModelError(f"heading {heading!r} not found") from None
  rows = []
  for ln in lines[start + 1:]:
    if ln.startswith("#"):
      break
    if ln.startswith("|"):
      rows.append([c.strip() for c in ln.strip().strip("|").split(" | ")])
    elif rows:
      break
  if len(rows) < 3:
    raise sysml_lite.ModelError(f"no table under {heading!r}")
  header = rows[0]
  return [dict(zip(header, r, strict=False)) for r in rows[2:]]


def strip_md(s: str) -> str:
  return re.sub(r"[`*]", "", s).strip()


def integrity_of_text(cell: str) -> str:
  """Highest integrity a work-product cell names (C > B‡ > B > QM (B-sup) > QM)."""
  s = cell
  found = []
  if re.search(r"(?<![A-Za-z(-])C(?![A-Za-z‡-])", s.replace("C-sup", "")):
    found.append("C")
  if "B‡" in s:
    found.append("BDagger")
  if re.search(r"(?<![A-Za-z(-])B(?![‡A-Za-z-])", s.replace("B-sup", "")):
    found.append("B")
  if "B-sup" in s:
    found.append("QMBsup")
  if "AoU" in s:
    found.append("AoU")
  if not found:
    found.append("QM")
  return max(found, key=INTEGRITY_RANK.__getitem__)


# ---------------------------------------------------------------- M1 - M6

def check_elements(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_S03.read_text(encoding="utf-8")
  for row in section_table(md, "3.1 Elements"):
    cell = row["Element"]
    ids = re.findall(r"\b(E-0\d[ab]?|EXT-[A-Z]+)\b", cell)
    for ident in ids:
      e = m.find(ident)
      if e is None:
        rep.err("M1", f"{ident} (WP-S-03 §3.1) is not in the model")
        continue
      if not ident.startswith("EXT"):
        want, got = integrity_of_text(row["Integrity"]), e.integrity()
        if want != got:
          rep.err("M1", f"{ident}: integrity {got} in the model, {want} in WP-S-03 §3.1 ({row['Integrity']!r})")


def check_firmware(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_W03.read_text(encoding="utf-8")
  seen = set()
  for row in section_table(md, "3.1 Component catalogue"):
    names = re.findall(r"`([a-z0-9_.]+)`", row["Element name"])
    if not names:
      continue
    name = names[0]
    seen.add(name)
    e = m.find(name)
    if e is None:
      rep.err("M2", f"{name} (WP-W-03 §3.1) is not in the model")
      continue
    unit = row["Unit"].strip()
    got_unit = (e.meta.get("Unit") or {}).get("id")
    if unit != "—" and unit != got_unit:
      rep.err("M2", f"{name}: unit {got_unit} in the model, {unit} in WP-W-03")
    build = "reference" if "[ref]" in row["Build"] else "both"
    got_build = str((e.meta.get("Unit") or {}).get("build", "Build::both")).split("::")[-1]
    if unit != "—" and build != got_build:
      rep.err("M2", f"{name}: build {got_build} in the model, {build} in WP-W-03")
    want, got = integrity_of_text(row["ASIL attribution"]), e.integrity()
    if want != got:
      rep.err("M2", f"{name}: integrity {got} in the model, {want} in WP-W-03 ({row['ASIL attribution'][:60]!r})")
  fw = m.find("E-03")
  for e in fw.walk():
    if e.short and e.short.startswith("panda.") and e.short not in seen:
      rep.err("M2", f"{e.short} is in the model but not in WP-W-03 §3.1")


def check_host(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_W03.read_text(encoding="utf-8")
  seen = set()
  for row in section_table(md, "4.1 Components relevant to safety"):
    for name in re.findall(r"`(host\.[a-z_]+)`", row["Element name"]):
      seen.add(name)
      e = m.find(name)
      if e is None:
        rep.err("M3", f"{name} (WP-W-03 §4.1) is not in the model")
        continue
      want, got = integrity_of_text(row["Class"]), e.integrity()
      if want != got:
        rep.err("M3", f"{name}: integrity {got} in the model, {want} in WP-W-03 §4.1 ({row['Class']!r})")
  for e in m.find("E-01").walk():
    if e.short and e.short.startswith("host.") and e.short not in seen:
      rep.err("M3", f"{e.short} is in the model but not in WP-W-03 §4.1")


def component_of(m: sysml_lite.Model, path: str) -> set[str]:
  """E-xx identifiers of the element at `path`, its ancestors and the elements allocated to it.

  E-03a also counts as E-03; E-02 counts for host.modeld because the driving model is allocated
  to (executed by) it.
  """
  e = m.owner_element(path)
  hosted = [m.elements[src] for src, dst in m.allocations if dst == e.path]
  out = set()
  for start in (e, *hosted):
    for x in (start, *start.ancestors()):
      if x.short and re.fullmatch(r"E-0\d[ab]?", x.short):
        out.add(x.short)
        out.add(x.short[:4])
  return out


def check_interfaces(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_S03.read_text(encoding="utf-8")
  by_id: dict[str, list[sysml_lite.Connection]] = defaultdict(list)
  for c in m.connections:
    if c.interface_id:
      by_id[c.interface_id].append(c)
  documented = set()
  for row in section_table(md, "3.3 Interfaces"):
    m_id = re.fullmatch(r"(IF-\d\d)(b|/(\d\d))?", row["ID"])
    if not m_id:
      rep.err("M4", f"unrecognised interface id {row['ID']!r} in WP-S-03 §3.3")
      continue
    ids = [m_id[1] + (m_id[2] if m_id[2] == "b" else "")]
    if m_id[3]:
      ids.append("IF-" + m_id[3])
    item_side = set(re.findall(r"E-0\d[ab]?", row["Between"]))
    for ident in ids:
      documented.add(ident)
      conns = by_id.get(ident)
      if not conns:
        rep.err("M4", f"{ident} (WP-S-03 §3.3) has no connection in the model")
        continue
      ends = set().union(*(component_of(m, p) for c in conns for p in c.ends))
      for e_id in item_side:
        if e_id not in ends:
          rep.err("M4", f"{ident}: WP-S-03 §3.3 names {e_id} but no model connection of {ident} ends in it")
  for ident in sorted(set(by_id) - documented):
    rep.err("M4", f"{ident} is in the model but not in WP-S-03 §3.3")


def expand_tsr(cell: str) -> list[str]:
  out = []
  for part in re.split(r",\s*", cell):
    part = part.strip()
    r = re.fullmatch(r"(\d{3})\s*[–-]\s*(\d{3})", part)
    if r:
      out += [f"TSR-{n}" for n in range(int(r[1]), int(r[2]) + 1)]
    elif re.match(r"\d{3}", part):
      out.append("TSR-" + part)
  return out


def check_mechanisms(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_S03.read_text(encoding="utf-8")
  documented = set()
  for row in section_table(md, "6. Safety mechanism catalogue"):
    sm = row["SM"]
    documented.add(sm)
    mech = m.mechanisms.get(sm)
    if mech is None:
      rep.err("M5", f"{sm} (WP-S-03 §6) is not in the model")
      continue
    want = set()
    for e in re.sub(r"\s*\(.*?\)", "", row["Element"]).split("/"):
      e = e.strip()
      want.add("E-03b" if e == "b" else e)
    got = {m.elements[p].short for p in mech.performers}
    if want != got:
      rep.err("M5", f"{sm}: performed by {sorted(got)} in the model, {sorted(want)} in WP-S-03 §6")
    if sorted(expand_tsr(row["TSR"])) != sorted(mech.tsr):
      rep.err("M5", f"{sm}: TSRs {mech.tsr} in the model, {expand_tsr(row['TSR'])} in WP-S-03 §6")
  for sm in sorted(set(m.mechanisms) - documented):
    rep.err("M5", f"{sm} is in the model but not in WP-S-03 §6")


PROCESS = {"pandad": "host.pandad", "card": "host.card", "selfdrived": "host.selfdrived",
           "controlsd": "host.controlsd", "modeld": "host.modeld", "plannerd": "host.plannerd",
           "radard": "host.radard", "dmonitoringmodeld": "host.dm", "dmonitoringd": "host.dm",
           "locationd": "estimators", "calibrationd": "estimators", "paramsd": "estimators",
           "torqued": "estimators", "lagd": "estimators", "hardwared": "hardwared"}


def check_functions(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_C01.read_text(encoding="utf-8")
  documented = {}
  for row in section_table(md, "2.1 Functions"):
    documented[row["ID"]] = strip_md(row["Function"])
  for fid, title in documented.items():
    f = m.functions.get(fid)
    if f is None:
      rep.err("M9", f"{fid} (WP-C-01 §2.1) is not in the model")
    elif f.doc != title:
      rep.err("M9", f"{fid}: {f.doc!r} in the model, {title!r} in WP-C-01 §2.1")
  for fid, f in m.functions.items():
    if fid not in documented:
      rep.err("M9", f"{fid} is in the model but not in WP-C-01 §2.1")
    if not f.steps:
      rep.err("M9", f"{fid} has no steps")
    for st in f.steps:
      if not st.performers:
        rep.err("M9", f"{st.short} ({st.name}) is performed by no element")


def check_security(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_S07.read_text(encoding="utf-8")
  def same(kind: str, ident: str, col: str, model_val: object, doc_val: str):
    if str(model_val) != doc_val:
      rep.err("M10", f"{ident} {col}: {str(model_val)!r} in the model, {doc_val!r} in WP-S-07 {kind}")
  seen = set()
  for row in section_table(md, "3.1 Elements and security zones"):
    zid, name = row["Zone"].split(" ", 1)
    seen.add(zid)
    z = m.zones.get(zid)
    if z is None:
      rep.err("M10", f"{zid} (WP-S-07 §3.1) is not in the model")
      continue
    same("§3.1", zid, "name", z.doc, name)
    for col, key in (("Elements", "holds"), ("Trust level", "trust"), ("Basis", "basis")):
      same("§3.1", zid, col, z.values.get(key, ""), row[col])
  for zid in sorted(set(m.zones) - seen):
    rep.err("M10", f"{zid} is in the model but not in WP-S-07 §3.1")
  seen = set()
  for row in section_table(md, "3.2 Trust boundaries"):
    tb = row["ID"]
    seen.add(tb)
    b = m.boundaries.get(tb)
    if b is None:
      rep.err("M10", f"{tb} (WP-S-07 §3.2) is not in the model")
      continue
    same("§3.2", tb, "Boundary", b.doc, row["Boundary"])
    want = re.findall(r"Z\d", row["Boundary"])
    if sysml_lite._as_list(b.values.get("zones")) != want:
      rep.err("M10", f"{tb}: zones {b.values.get('zones')} in the model, {want} in WP-S-07 §3.2")
    for col, key in (("Data / control crossing", "crossing"), ("Threats (TS)", "threats"), ("Controls (CSR)", "controls")):
      same("§3.2", tb, col, b.values.get(key, ""), row[col])
  for tb in sorted(set(m.boundaries) - seen):
    rep.err("M10", f"{tb} is in the model but not in WP-S-07 §3.2")
  for e in m.find("E-01").parent.children:  # a component split across zones (E-04) is checked by its parts
    for x in [e] if e.zone() or not e.children else e.children:
      if x.zone() is None:
        rep.err("M10", f"{x.short or x.path} is inside the item but in no security zone")


def find_element(m: sysml_lite.Model, ident: str) -> sysml_lite.Element | None:
  """An element by its short name, alias or (for elements without one) its name."""
  return m.find(ident) or next((e for e in m.elements.values() if e.name == ident and not e.short), None)


def check_integration(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_S08.read_text(encoding="utf-8")
  seen = set()
  for row in section_table(md, "3.1 Approach"):
    sid = row["Step"]
    seen.add(sid)
    st = m.integration.get(sid)
    if st is None:
      rep.err("M11", f"{sid} (WP-S-08 §3.1) is not in the model")
      continue
    for col, key in (("Integrated elements", "elements"), ("Interfaces exercised", "interfaces"),
                     ("Stimulus", "stimulus"), ("Purpose", "purpose")):
      if str(st.values.get(key, "")) != row[col]:
        rep.err("M11", f"{sid} {col}: {st.values.get(key)!r} in the model, {row[col]!r} in WP-S-08 §3.1")
  for sid in sorted(set(m.integration) - seen):
    rep.err("M11", f"{sid} is in the model but not in WP-S-08 §3.1")
  ifs = {c.interface_id for c in m.connections if c.interface_id}
  integrated = set()
  for sid, st in m.integration.items():
    for ident in sysml_lite._as_list(st.values.get("integrates")):
      e = find_element(m, ident)
      if e is None:
        rep.err("M11", f"{sid} integrates {ident!r}, which is not an element of the model")
      else:
        integrated |= {e.path, *(x.path for x in e.walk())}
    for i in sysml_lite._as_list(st.values.get("exercises")):
      if i not in ifs:
        rep.err("M11", f"{sid} exercises {i!r}, which is not an interface of the model")
  for e in m.find("E-01").parent.walk():
    if e.short and re.fullmatch(r"E-0\d[ab]?", e.short) and not any(x.path in integrated for x in e.walk()):
      rep.err("M11", f"{e.short} is integrated by no step of WP-S-08 §3.1")


def record_ids(sm: sysml_lite.StateMachine) -> list[str]:
  """The record transition IDs of a record state machine (one ID can stand for several model transitions)."""
  return list(dict.fromkeys(str((t.meta.get("RecordTransition") or {}).get("id", "")) for t in sm.transitions))


def known_record(m: sysml_lite.Model, ref: str, what: str) -> bool:
  """Whether "SM-X item" names a state or a record transition of a record state machine in the model."""
  machine, _, item = ref.partition(" ")
  sm = m.state_machines.get(machine)
  if sm is None or "StateRecord" not in sm.meta:
    return False
  return item in (sm.states if what == "state" else record_ids(sm))


def check_modes(m: sysml_lite.Model, rep: Report) -> None:
  sm = m.state_machines.get("SM-SYS")
  if sm is None:
    rep.err("M12", "the system modes state machine SM-SYS is not in the model")
    return
  md = WP_C01.read_text(encoding="utf-8")
  by_title = {st.doc: st for st in sm.states.values() if "ModeRow" in st.meta}
  configs = sysml_lite._as_list((sm.meta.get("ModeConfigurations") or {}).get("rows"))
  seen = set()
  for row in section_table(md, "4. Operating modes and states"):
    mode = row["Mode"]
    seen.add(mode)
    if mode in configs:
      continue
    st = by_title.get(mode)
    if st is None:
      rep.err("M12", f"WP-C-01 §4 mode {mode!r} is neither a state of SM-SYS nor a listed configuration")
      continue
    for col, key in (("Description", "description"), ("Actuation", "actuation")):
      if str(st.meta["ModeRow"].get(key, "")) != row[col]:
        rep.err("M12", f"{mode} {col}: {st.meta['ModeRow'].get(key)!r} in the model, {row[col]!r} in WP-C-01 §4")
  for mode in sorted((set(by_title) | set(configs)) - seen):
    rep.err("M12", f"{mode!r} is in the model but not a row of WP-C-01 §4")
  def known(ref: str, what: str) -> bool:
    return known_record(m, ref, what)
  for st in sm.states.values():
    for side in ("host", "panda"):
      for ref in sysml_lite._as_list((st.meta.get("ModeRow") or {}).get(side)):
        if not known(ref, "state"):
          rep.err("M12", f"state {st.path}: {side} names {ref!r}, which is not a state of the records")
  for t in sm.transitions:
    enf = t.meta.get("Enforcement")
    if not enf:
      rep.err("M12", f"transition {t.name} says nothing about who enforces it (@Enforcement)")
      continue
    for ref in sysml_lite._as_list(enf.get("records")):
      if not known(ref, "transition"):
        rep.err("M12", f"transition {t.name}: {ref!r} is not a transition of the records")


def check_flows(m: sysml_lite.Model, rep: Report) -> None:
  md = WP_S03.read_text(encoding="utf-8")
  want = set()
  for row in section_table(md, "9. Interfaces to cereal services"):
    pubsub = row["Publisher → main subscribers"]
    if "→" not in pubsub:
      continue
    pubs, subs = (x.strip() for x in pubsub.split("→", 1))
    svc = ", ".join(s.strip().strip("`") for s in row["Service"].split(","))
    for p in pubs.split("/"):
      for s in subs.split(","):
        a, b = PROCESS.get(p.strip()), PROCESS.get(s.strip())
        if a and b and a != b:
          want.add((svc, a, b))
  got = set()
  for c in m.connections:
    if c.definition == "DataFlow":
      got.add((str(c.values.get("service")), m.elements[c.ends[0]].ident, m.elements[c.ends[1]].ident))
  for f in sorted(want - got):
    rep.err("M6", f"service {f[0]} {f[1]} → {f[2]} (WP-S-03 §9) is not in the model")
  for f in sorted(got - want):
    rep.err("M6", f"service {f[0]} {f[1]} → {f[2]} is in the model but not in WP-S-03 §9")


def check_integrity_rules(m: sysml_lite.Model, rep: Report) -> None:
  item = m.elements["context.ldsda"]
  for e in item.walk():
    if e is not item and e.integrity() is None:
      rep.err("M7", f"{e.path} has no integrity attribution (directly or from a containing element)")
  for c in m.connections:
    a, b = (m.elements[p] for p in c.ends)
    if a.scope() != "inside" or b.scope() != "inside":
      continue
    ia, ib = a.integrity(), b.integrity()
    if (ia in ASIL) != (ib in ASIL) and "FfiClaim" not in c.meta:
      rep.err("M7", f"{c.name or c.kind} {a.ident} ({ia}) – {b.ident} ({ib}) crosses the integrity boundary " +
                    "without an @FfiClaim")


# ---------------------------------------------------------------- M8 allocation resolution

TOKEN_RES = [
  re.compile(r"`([a-z][A-Za-z0-9_.]+)`"),
  re.compile(r"\b(E-0\d[ab]?|U-[A-Z]{3}-[A-Z]{2,6}|P-SW|P-HW|SoC|HAR|EXT|OPS|IWDG1|SPI4)\b"),
  re.compile(r"\b((?:host|panda)\.[a-z0-9_.]*[a-z0-9_])\b"),
]
NON_ELEMENT = {"OPS": "operations (WP-S-06, not an architecture element)", "EXT": "external element (AoU)"}


def load_items() -> list[dict]:
  sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
  import check_trace
  out = []
  for f in sorted(ITEMS.glob("*.yaml")):
    out += check_trace.load_yaml(f)
  return out


def resolve_allocation(m: sysml_lite.Model, text: str, units: dict[str, list[str]]):
  tokens = []
  for rx in TOKEN_RES:
    for t in rx.findall(text):
      if t not in tokens:
        tokens.append(t)
  resolved, unresolved = [], []
  for t in tokens:
    if t in NON_ELEMENT:
      resolved.append((t, NON_ELEMENT[t]))
    elif m.find(t) is not None:
      resolved.append((t, m.find(t).path))
    elif t in units:
      resolved.append((t, ", ".join(units[t])))
    elif len(parts := [e for e in m.elements.values() if e.kind == "part" and e.name == t]) == 1:
      resolved.append((t, parts[0].path))  # a uniquely named part, as R2 resolves WP-S-01 §10.1 names
    else:
      unresolved.append(t)
  return tokens, resolved, unresolved


def allocation_report(m: sysml_lite.Model) -> str:
  units: dict[str, list[str]] = defaultdict(list)
  for e in m.elements.values():
    u = e.meta.get("Unit")
    if u:
      units[u["id"]].append(e.short)
  rows = []
  for it in load_items():
    a = it.get("allocated_to")
    if a:
      rows.append((it["id"], it.get("kind", ""), str(a)))
  status = Counter()
  by_text: dict[str, dict] = {}
  per_kind: dict[str, Counter] = defaultdict(Counter)
  for ident, kind, text in rows:
    tokens, res, unres = resolve_allocation(m, text, units)
    s = "resolved" if res and not unres else ("partly resolved" if res else "not resolved")
    status[s] += 1
    per_kind[kind][s] += 1
    d = by_text.setdefault(text, {"ids": [], "status": s, "unresolved": unres, "resolved": res})
    d["ids"].append(ident)

  def esc(s: str) -> str:
    return s.replace("|", "\\|")

  total = len(rows)
  out = [
    "# Allocation resolution",
    "",
    "Generated by `assurance/models/sysml/tools/check_model.py --write` — do not edit by hand.",
    "",
    "Every `allocated_to` value in [`assurance/trace/items`](../../../trace/items) is matched against the " +
    "architecture model: element identifiers (`E-03a`, `host.selfdrived`, `panda.safety.toyota`, `IWDG1`), " +
    "software units (`U-SAF-TOY`), the allocation short forms of WP-S-02 §2.1 (`P-SW`, `P-HW`, `SoC`, `HAR`, " +
    "declared as aliases in the model) and the two non-element targets `EXT` and `OPS`. A value is " +
    "**resolved** when every identifier in it names something in the model, **partly resolved** when some do, " +
    "and **not resolved** when none do (free text such as \"Firmware + IWDG\").",
    "",
    "This report is informational: it does not fail CI. It changes, and CI asks for it to be regenerated, " +
    "whenever the model or an allocation changes, so a new unresolved allocation shows up in review.",
    "",
    "## Summary",
    "",
    "| Requirement kind | Allocations | Resolved | Partly resolved | Not resolved |",
    "|---|---|---|---|---|",
  ]
  for kind in sorted(per_kind):
    c = per_kind[kind]
    out.append(f"| {kind} | {sum(c.values())} | {c['resolved']} | {c['partly resolved']} | {c['not resolved']} |")
  out.append(f"| **all** | **{total}** | **{status['resolved']}** | **{status['partly resolved']}** | " +
             f"**{status['not resolved']}** |")
  out += ["", f"{len(by_text)} distinct `allocated_to` values.", ""]
  for title, s in (("Not resolved", "not resolved"), ("Partly resolved", "partly resolved")):
    items = [(t, d) for t, d in by_text.items() if d["status"] == s]
    out += [f"## {title} ({len(items)} values)", "", "| `allocated_to` | Requirements | Identifiers not in the model |",
            "|---|---|---|"]
    for t, d in sorted(items, key=lambda x: (-len(x[1]["ids"]), x[0])):
      ids = ", ".join(d["ids"][:6]) + (f" and {len(d['ids']) - 6} more" if len(d["ids"]) > 6 else "")
      out.append(f"| {esc(t)} | {ids} | {esc(', '.join(d['unresolved'])) or 'no element identifier in the text'} |")
    out.append("")
  return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- requirements (R1-R4)

def check_requirements(m: sysml_lite.Model, rep: Report) -> None:
  import gen_requirements
  for key, text in gen_requirements.build().items():
    f = gen_requirements.OUT[key]
    if not f.exists() or f.read_text(encoding="utf-8") != text:
      rep.err("R1", f"{f.relative_to(REPO)} does not match the work products; run tools/gen_requirements.py")
  for r in m.requirements.values():
    for p in r.satisfied_by:
      if m.elements[p].scope() != "inside":
        rep.err("R2", f"{r.short} is satisfied by {p}, which is not inside the item")
    if r.short.startswith("SYS-"):
      if not r.satisfied_by:
        rep.err("R2", f"{r.short} has no satisfying element (WP-S-01 §10.1)")
      for name in re.findall(r"`([^`]+)`", str(r.values.get("allocText", ""))):
        if m.find(name) is None and sum(1 for e in m.elements.values() if e.kind == "part" and e.name == name) != 1:
          rep.err("R2", f"{r.short}: {name!r} in WP-S-01 §10.1 names no element of the model")
  for v in m.verifications.values():
    for r in v.verifies:
      if v.short not in m.requirements[r].verified_by:
        rep.err("R3", f"{v.short} verifies {r} but {r} does not list it")


# ---------------------------------------------------------------- needs and use cases (N1-N3)

def check_needs(m: sysml_lite.Model, rep: Report) -> None:
  import gen_requirements
  people, _, _ = gen_requirements.stakeholder_needs()
  needs = {s: r for s, r in m.requirements.items() if r.definition == "StakeholderNeed"}
  if not needs:
    rep.err("N2", "the model has no stakeholder needs (WP-S-01 §1.3)")
    return
  as_stakeholder = {d for r in needs.values() for _, d in r.stakeholders}
  as_actor = {d for u in m.use_cases.values() for _, d in u.actors}
  for p in people:
    d = gen_requirements.camel(p["name"], True)
    for role, used, where in (("stakeholder", as_stakeholder, "names no need"), ("actor", as_actor, "takes part in no use case")):
      if role in p["kinds"] and d not in used:
        rep.err("N1", f"{p['name']} is a {role} in WP-S-01 §1.2 but {where}")
      if role not in p["kinds"] and d in used:
        rep.err("N1", f"{p['name']} is used as a {role} but WP-S-01 §1.2 does not list it as one")
  refined = defaultdict(list)
  for r in m.requirements.values():
    for parent in r.derived_from:
      if parent in needs:
        refined[parent].append(r.short)
  served = {n for u in m.use_cases.values() for n in u.needs}
  for s in needs:
    if not refined[s]:
      rep.err("N2", f"{s} is refined by no requirement")
    if s not in served:
      rep.err("N2", f"{s} is served by no use case")
  for r in m.requirements.values():
    if r.short.split("-")[0] in ("SYS", "SG") and not any(p in needs for p in r.derived_from):
      rep.err("N2", f"{r.short} refines no stakeholder need (WP-S-01 §1.3)")
  for u in m.use_cases.values():
    if not u.functions:
      rep.err("N3", f"{u.short} performs no function")
    if not u.actors:
      rep.err("N3", f"{u.short} has no actor")
  used = {f for u in m.use_cases.values() for f in u.functions}
  for f in m.functions:
    if f not in used:
      rep.err("N3", f"{f} is performed by no use case (WP-S-01 §1.4)")


# ---------------------------------------------------------------- behaviour (B1-B3)

def find_any(m: sysml_lite.Model, ident: str) -> sysml_lite.Element | None:
  """An element by short name, alias or (unique) part name; for a software unit, the first element in it."""
  e = m.find(ident)
  if e is None:
    named = [x for x in m.elements.values() if x.kind == "part" and x.name == ident]
    units = [x for x in m.elements.values() if (x.meta.get("Unit") or {}).get("id") == ident]
    e = named[0] if len(named) == 1 else units[0] if units else None
  return e


def check_behaviour(m: sysml_lite.Model, rep: Report) -> None:
  import gen_behaviour
  try:
    texts = gen_behaviour.build()
  except gen_behaviour.BehaviourError as e:
    rep.err("B1", str(e))
    texts = {}
  for key, text in texts.items():
    f = gen_behaviour.OUT[key]
    if not f.exists() or f.read_text(encoding="utf-8") != text:
      rep.err("B1", f"{f.relative_to(REPO)} does not match its record; run tools/gen_behaviour.py")
  records = {k: sm for k, sm in m.state_machines.items() if "StateRecord" in sm.meta}
  if not records:
    rep.err("B1", "the model has no state-machine records")
  for k, sm in records.items():
    for u in sysml_lite._as_list(sm.meta["StateRecord"].get("units")):
      if find_any(m, u) is None:
        rep.err("B2", f"{k} runs on {u!r}, which is not an element of the model")
  if not m.sequences:
    rep.err("B1", "the model has no sequence (WP-S-03 §4.1)")
  for q in m.sequences.values():
    for name, ident in q.lifelines:
      if find_any(m, ident) is None:
        rep.err("B2", f"{q.short} lifeline {name} stands for {ident!r}, which is not an element of the model")
    used = {x for msg in q.messages for x in (msg.source, msg.target)}
    for name, _ in q.lifelines:
      if name not in used:
        rep.err("B3", f"{q.short} lifeline {name} takes part in no step")
    for msg in q.messages:
      step = msg.meta.get("SequenceStep") or {}
      refs = [r for r in sysml_lite._as_list(step.get("records")) if r]
      for ref in refs:
        if not known_record(m, ref, "transition"):
          rep.err("B2", f"{q.short} {msg.short}: {ref!r} is not a transition of the state-machine records")
      after = str(step.get("stateAfter", ""))
      if after:
        state = after.split(":", 1)[-1].strip()
        machines = {r.split(" ")[0] for r in refs}
        if not any(known_record(m, f"{x} {state}", "state") for x in machines):
          rep.err("B2", f"{q.short} {msg.short}: state after {state!r} is not a state of a machine its records name")
      for req in re.findall(r"\b(?:TSR|SYS|FSR|SG)-[0-9.]+[a-z]?\b", str(step.get("condition", ""))):
        if req not in m.requirements:
          rep.err("B2", f"{q.short} {msg.short}: condition names {req}, which is not a requirement of the model")


# ---------------------------------------------------------------- timing and HSI (H1-H3)

def check_timing_hsi(m: sysml_lite.Model, rep: Report) -> None:
  import gen_timing_hsi
  try:
    texts = gen_timing_hsi.build()
  except gen_timing_hsi.TimingError as e:
    rep.err("H1", str(e))
    texts = {}
  for key, text in texts.items():
    f = gen_timing_hsi.OUT[key]
    if not f.exists() or f.read_text(encoding="utf-8") != text:
      rep.err("H1", f"{f.relative_to(REPO)} does not match its work product; run tools/gen_timing_hsi.py")
  if not m.budgets or not m.signals:
    rep.err("H1", "the model has no timing budgets or no HSI signals")
  eps = 1e-9
  covered = set()
  for label, b in m.budgets.items():
    v = b.values
    sec = {a: v.get(f"{a}Seconds") for a in ("ftti", "fdti", "frti", "margin", "fhti")}
    for ref in [*sysml_lite._as_list(v.get("goals")), *sysml_lite._as_list(v.get("tsr"))]:
      if ref and ref not in m.requirements:
        rep.err("H2", f"budget {label!r} names {ref}, which is not a requirement of the model")
    covered.update(sysml_lite._as_list(v.get("goals")))
    d, r, f, h, mg = (sec[a] for a in ("fdti", "frti", "ftti", "fhti", "margin"))
    if None not in (d, r, f) and d + r > f + eps:
      rep.err("H2", f"budget {label!r}: FDTI {d:g} s + FRTI {r:g} s exceeds the FTTI {f:g} s")
    if None not in (d, r, h) and abs(h - (d + r)) > eps:
      rep.err("H2", f"budget {label!r}: FHTI {h:g} s is not FDTI + FRTI = {d + r:g} s")
    if None not in (f, h, mg) and mg > f - h + eps:
      rep.err("H2", f"budget {label!r}: margin {mg:g} s is more than FTTI - FHTI = {f - h:g} s")
  for sg in (s for s in m.requirements if s.startswith("SG-")):
    if sg not in covered:
      rep.err("H2", f"{sg} has no timing budget in WP-S-04 §3.7")
  for sid, sgl in m.signals.items():
    v = sgl.values
    owners = [x for x in sysml_lite._as_list(v.get("owners")) if x]
    if not owners:
      rep.err("H3", f"{sid} names no owner element (E-nn or host `process`)")
    for o in owners:
      if find_any(m, o) is None:
        rep.err("H3", f"{sid} is owned by {o!r}, which is not an element of the model")
    tsr = [x for x in sysml_lite._as_list(v.get("tsr")) if x]
    if not tsr:
      rep.err("H3", f"{sid} serves no TSR")
    for x in tsr:
      if x not in m.requirements:
        rep.err("H3", f"{sid} names {x}, which is not a requirement of the model")
    for c in (x for x in sysml_lite._as_list(v.get("tests")) if x):
      if c not in m.verifications:
        rep.err("H3", f"{sid} is tested by {c}, which is not a verification case of the model")


def outside_reason(text: str) -> str | None:
  toks = [t for t in re.split(r"[^A-Z]+", text) if t]
  hits = [OUTSIDE[t] for t in toks if t in OUTSIDE]
  return hits[0] if hits else None


def coverage_report(m: sysml_lite.Model) -> str:
  kinds: dict[str, list] = defaultdict(list)
  for r in m.requirements.values():
    kinds[r.short.split("-")[0]].append(r)
  rows, lists = [], []
  for k, label in KIND_NAMES.items():
    rs = kinds.get(k, [])
    sat = [r for r in rs if r.satisfied_by]
    out_ = [r for r in rs if not r.satisfied_by and outside_reason(str(r.values.get("allocText", "")))]
    none = [r for r in rs if not r.satisfied_by and r not in out_]
    ver = [r for r in rs if r.verified_by]
    der = [r for r in rs if r.derived_from]
    rows.append(f"| {label} | {len(rs)} | {len(sat)} | {len(out_)} | {len(none)} | {len(ver)} | " +
                (f"{len(der)} |" if k != "CSR" else "— |"))
    if none:
      lists.append((f"{k}: no satisfying element", [f"{r.short} (`{r.values.get('allocText', '') or 'no allocation'}`)" for r in none]))
    unver = [r.short for r in rs if not r.verified_by]
    if unver:
      lists.append((f"{k}: not verified by any case", unver))
    if k != "CSR":
      underived = [r.short for r in rs if not r.derived_from]
      if underived:
        lists.append((f"{k}: no parent requirement in the model", underived))
  cases = list(m.verifications.values())
  naming = [v for v in cases if v.verifies]
  out = [
    "# Requirements coverage",
    "",
    "Generated by `assurance/models/sysml/tools/check_model.py --write` — do not edit by hand.",
    "",
    "Read from the SysML model: the requirements of [`Requirements.sysml`](../model/Requirements.sysml), the `satisfy` " +
    "relationships of [`Satisfaction.sysml`](../model/Satisfaction.sysml) and the verification cases of " +
    "[`Verification.sysml`](../model/Verification.sysml), all generated from the work products by " +
    "`tools/gen_requirements.py`. **Satisfied** means a `satisfy` relationship to an element inside the item; " +
    "**outside the item** means the allocation is EXT, OPS, ENV or USR; **verified** means at least one case of a " +
    "test specification names the requirement. A verified requirement has a specified case, not a passed one.",
    "",
    "This report is informational: it does not fail CI, but CI asks for it to be regenerated whenever a " +
    "requirement, an allocation or a test specification changes, so a new gap shows up in review.",
    "",
    "## Summary",
    "",
    "| Kind | Requirements | Satisfied | Outside the item | No satisfying element | Verified by ≥ 1 case | Derived from a parent |",
    "|---|---|---|---|---|---|---|",
    *rows,
    "",
    f"{len(cases)} verification cases; {len(naming)} name at least one modelled requirement.",
    "",
  ]
  for title, ids in lists:
    out += [f"## {title} ({len(ids)})", "", ", ".join(ids), ""]
  return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------- main

def main(argv: list[str]) -> int:
  rep = Report()
  try:
    m = sysml_lite.load()
  except sysml_lite.ModelError as e:
    print(f"FAIL model: {e}")
    return 1
  for check in (check_elements, check_firmware, check_host, check_interfaces, check_mechanisms, check_functions, check_security, check_integration, check_modes, check_flows,
                check_integrity_rules, check_requirements, check_needs, check_behaviour, check_timing_hsi):
    try:
      check(m, rep)
    except sysml_lite.ModelError as e:
      rep.err(check.__name__, str(e))

  text = allocation_report(m)
  if "--write" in argv:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(text, encoding="utf-8")
  elif not REPORT.exists() or REPORT.read_text(encoding="utf-8") != text:
    rep.err("M8", f"{REPORT.relative_to(REPO)} is out of date; run check_model.py --write")
  cov = coverage_report(m)
  if "--write" in argv:
    COVERAGE.write_text(cov, encoding="utf-8")
  elif not COVERAGE.exists() or COVERAGE.read_text(encoding="utf-8") != cov:
    rep.err("R4", f"{COVERAGE.relative_to(REPO)} is out of date; run check_model.py --write")

  parts = sum(1 for e in m.elements.values() if e.kind == "part")
  print(f"sysml model: {parts} parts, {len(m.connections)} connections, {len(m.mechanisms)} mechanisms, " +
        f"{len(m.views)} views")
  summary = re.search(r"\| \*\*all\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \| \*\*(\d+)\*\* \|", text)
  if summary:
    print(f"allocations: {summary[1]} total, {summary[2]} resolved, {summary[3]} partly, {summary[4]} not resolved " +
          f"(informational, {REPORT.name})")
  for e in rep.errors:
    print("FAIL", e)
  if rep.errors:
    print(f"{len(rep.errors)} problem(s)")
    return 1
  print(f"requirements: {len(m.requirements)} in the model, " +
        f"{sum(1 for r in m.requirements.values() if r.satisfied_by)} satisfied, " +
        f"{sum(1 for r in m.requirements.values() if r.verified_by)} verified by a case " +
        f"(informational, {COVERAGE.name})")
  print(f"needs: {sum(1 for r in m.requirements.values() if r.definition == 'StakeholderNeed')} stakeholder needs, " +
        f"{len(m.use_cases)} use cases")
  print(f"behaviour: {sum(1 for s in m.state_machines.values() if 'StateRecord' in s.meta)} state-machine records, " +
        f"{sum(len(q.messages) for q in m.sequences.values())} sequence steps")
  print(f"timing and HSI: {len(m.budgets)} timing budgets, {len(m.signals)} HSI signals")
  print("OK: M1-M12, N1-N3, B1-B3, H1-H3 and R1-R4 passed")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
