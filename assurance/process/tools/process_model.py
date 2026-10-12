#!/usr/bin/env python3
"""LionDriver integrated process model (WP-P-11): checker and process-map generator.

Reads the process records in `assurance/process/model/` and checks them against the documents they
describe. It then writes the process maps (Mermaid) in `assurance/process/maps/`. Clause
references, gate names, exit criteria, work-product status and role assignments are never copied
into the model. They are read from WP-M-00, WP-M-02 and WP-M-06 at generation time, so a map
cannot disagree with the register.

Usage:
    python3 process_model.py           # check the model and write the maps
    python3 process_model.py --check   # check the model and fail if a committed map is stale
"""
# ruff: noqa: E501  (generated Markdown table rows)
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PROCESS_DIR = TOOLS_DIR.parent
ASSURANCE_DIR = PROCESS_DIR.parent
MODEL_DIR = PROCESS_DIR / "model"
MAPS_DIR = PROCESS_DIR / "maps"
REGISTER_MD = ASSURANCE_DIR / "01-management" / "WP-M-00-work-product-register.md"
SAFETY_PLAN_MD = ASSURANCE_DIR / "01-management" / "WP-M-02-safety-plan.md"
CONFIRMATION_MD = ASSURANCE_DIR / "01-management" / "WP-M-06-confirmation-measures-plan.md"
CONFIRMATION_DIR = ASSURANCE_DIR / "10-safety-case" / "confirmation"

sys.path.insert(0, str(ASSURANCE_DIR / "trace" / "tools"))
from check_trace import _load_subset

GATES = ["G0", "G1", "G2", "G3", "G4", "G5", "G6"]
STANDARDS = [("iso26262", "ISO 26262"), ("iso21448", "ISO 21448"), ("iso21434", "ISO/SAE 21434"), ("other", "Other"), ("aspice", "ASPICE")]
STATUS_NAMES = {"S": "Skeleton", "D": "Draft", "R": "In review", "A": "Approved", "B": "Baselined", "N/A": "Tailored out"}
INTERFACE_STATUS = {"documented", "open"}
HANDBOOK_WPS = {f"WP-{n}" for n in range(1, 9)}

REQUIRED = {
  "phase": ["id", "kind", "handbook_chapters", "modelled"],
  "lane": ["id", "kind", "name", "role", "plan"],
  "activity": ["id", "kind", "phase", "lane", "name", "produces", "inputs", "handbook_wp"],
  "review": ["id", "kind", "phase", "name", "covers", "independence"],
  "interface": ["id", "kind", "phase", "between", "pattern", "topic", "anchors", "status", "open_item", "due"],
}
LIST_FIELDS = {"handbook_chapters", "produces", "inputs", "handbook_wp", "covers", "between", "anchors"}


# ---------------------------------------------------------------- sources

@dataclass
class RegisterRow:
  wp: str
  name: str
  path: Path
  clauses: dict[str, str]
  gate: str
  status: str

  @property
  def first_gate(self) -> str:
    m = re.match(r"G\d", self.gate)
    return m.group(0) if m else ""


def _cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip().strip("|").split("|")]


def load_register(text: str) -> tuple[dict[str, RegisterRow], dict[str, tuple[str, str]]]:
  """Work-product rows of WP-M-00 §3 and the gate table of §2 (gate -> (name, exit criterion))."""
  rows: dict[str, RegisterRow] = {}
  gates: dict[str, tuple[str, str]] = {}
  for line in text.splitlines():
    m = re.match(r"^\| \[(WP-[A-Z]-\d\d)\]\(([^)]+)\) \|", line)
    if m:
      c = _cells(line)
      if len(c) != 9:
        raise ValueError(f"WP-M-00 row {m.group(1)}: expected 9 columns, found {len(c)}")
      clauses = dict(zip([k for k, _ in STANDARDS], c[2:7], strict=True))
      rows[m.group(1)] = RegisterRow(m.group(1), c[1], (REGISTER_MD.parent / m.group(2)).resolve(), clauses, c[7], c[8])
      continue
    g = re.match(r"^\| (G\d) \| ([^|]+) \| ([^|]+) \|$", line)
    if g:
      gates[g.group(1)] = (g.group(2).strip(), g.group(3).strip())
  return rows, gates


def load_roles(text: str) -> dict[str, tuple[str, str]]:
  """Role table of WP-M-02 §3.1: role -> (assigned to, needed by)."""
  roles: dict[str, tuple[str, str]] = {}
  in_table = False
  for line in text.splitlines():
    if line.startswith("| Role | Responsibilities | Assigned to | Needed by |"):
      in_table = True
      continue
    if in_table:
      if not line.startswith("|"):
        break
      c = _cells(line)
      if len(c) == 4 and not c[0].startswith("---"):
        roles[c[0]] = (c[2], c[3])
  return roles


def load_gate_measures(text: str) -> dict[str, list[str]]:
  """Confirmation measures per gate from the WP-M-06 §9 summary table."""
  out: dict[str, list[str]] = {}
  for line in text.splitlines():
    m = re.match(r"^\| (G\d) \| ([^|]+) \|$", line)
    if m:
      ids = re.findall(r"\b(CR-\d\d|FSA-[A-Z0-9]+|SR-\d\d|CS-I\d|AUD-\d)\b", m.group(2))
      out[m.group(1)] = ids
  return out


# ---------------------------------------------------------------- model

@dataclass
class Model:
  phases: dict[str, dict] = field(default_factory=dict)
  lanes: dict[str, dict] = field(default_factory=dict)
  activities: dict[str, dict] = field(default_factory=dict)
  reviews: dict[str, dict] = field(default_factory=dict)
  interfaces: dict[str, dict] = field(default_factory=dict)
  errors: list[str] = field(default_factory=list)

  def err(self, check: str, where: str, msg: str) -> None:
    self.errors.append(f"[{check}] {where}: {msg}")


def load_model(model_dir: Path = MODEL_DIR) -> Model:
  model = Model()
  buckets = {"phase": model.phases, "lane": model.lanes, "activity": model.activities, "review": model.reviews, "interface": model.interfaces}
  for path in sorted(model_dir.glob("*.yaml")):
    try:
      items = _load_subset(path.read_text(encoding="utf-8"))
    except ValueError as e:
      model.err("P1", path.name, f"parse error: {e}")
      continue
    for it in items:
      kind = it.get("kind")
      where = f"{path.name}:{it.get('id')}"
      if kind not in REQUIRED:
        model.err("P1", where, f"unknown kind {kind!r}")
        continue
      missing = [k for k in REQUIRED[kind] if k not in it]
      if missing:
        model.err("P1", where, f"missing fields {missing}")
        continue
      bad = [k for k in LIST_FIELDS if k in it and not isinstance(it[k], list)]
      if bad:
        model.err("P1", where, f"fields must be lists: {bad}")
        continue
      if it["id"] in buckets[kind]:
        model.err("P1", where, "duplicate id")
        continue
      it["_file"] = path.name
      buckets[kind][it["id"]] = it
  return model


def direct_deps(acts: dict[str, dict], producer: dict[str, str]) -> dict[str, set[str]]:
  """Activity -> activities whose outputs it consumes, with transitive dependencies removed (map edges)."""
  deps = {a: {producer[w] for w in act["inputs"] if producer.get(w) in acts and producer[w] != a} for a, act in acts.items()}

  def reach(a: str, seen: set[str]) -> set[str]:
    for d in deps[a]:
      if d not in seen:
        seen.add(d)
        reach(d, seen)
    return seen

  return {a: {d for d in ds if not any(d in reach(o, set()) for o in ds - {d})} for a, ds in deps.items()}


@dataclass
class Context:
  register: dict[str, RegisterRow]
  gates: dict[str, tuple[str, str]]
  roles: dict[str, tuple[str, str]]
  gate_measures: dict[str, list[str]]


def load_context() -> Context:
  register, gates = load_register(REGISTER_MD.read_text(encoding="utf-8"))
  return Context(register, gates, load_roles(SAFETY_PLAN_MD.read_text(encoding="utf-8")),
                 load_gate_measures(CONFIRMATION_MD.read_text(encoding="utf-8")))


def check(model: Model, ctx: Context) -> dict[str, list[str]]:
  """Run the checks; returns the activity order per modelled phase."""
  reg = ctx.register
  # P2 phases and lanes
  for g in GATES:
    if g not in model.phases:
      model.err("P2", g, "phase record missing")
    if g not in ctx.gates:
      model.err("P2", g, "gate missing from WP-M-00 §2")
  for lid, lane in model.lanes.items():
    if lane["role"] not in ctx.roles:
      model.err("P2", lid, f"role {lane['role']!r} not in WP-M-02 §3.1")
    if lane["plan"] not in reg:
      model.err("P2", lid, f"plan {lane['plan']} not in WP-M-00")

  producer: dict[str, str] = {}
  for aid, act in model.activities.items():
    # P3 activity references
    if act["phase"] not in model.phases:
      model.err("P3", aid, f"unknown phase {act['phase']}")
    if act["lane"] not in model.lanes or act["lane"] == "assess":
      model.err("P3", aid, f"lane {act['lane']!r} is not a work lane")
    for hb in act["handbook_wp"]:
      if hb not in HANDBOOK_WPS:
        model.err("P3", aid, f"unknown handbook work product {hb}")
    for wp in act["produces"]:
      if wp not in reg:
        model.err("P3", aid, f"produces {wp}, which is not in WP-M-00")
        continue
      if wp in producer:
        model.err("P3", aid, f"{wp} is already produced by {producer[wp]}")
      producer[wp] = aid
      if reg[wp].first_gate != act["phase"]:
        model.err("P3", aid, f"{wp} is gated {reg[wp].gate} in WP-M-00, activity is in {act['phase']}")
      if not reg[wp].path.exists():
        model.err("P3", aid, f"{wp} file {reg[wp].path} does not exist")

  orders: dict[str, list[str]] = {}
  for gid, phase in model.phases.items():
    if not phase["modelled"]:
      continue
    acts = {a: x for a, x in model.activities.items() if x["phase"] == gid}
    # P4 completeness: every work product the register gates here has a producing activity
    for wp, row in reg.items():
      if row.first_gate == gid and wp not in producer:
        model.err("P4", gid, f"{wp} ({row.name}) is gated {row.gate} but no activity produces it")
    # P5 inputs: produced by an activity with a lower ID in this phase (so the ID order is a valid
    # execution order and the inputs cannot form a cycle), or by a work product of an earlier gate
    for aid, act in acts.items():
      for wp in act["inputs"]:
        if wp not in reg:
          model.err("P5", aid, f"input {wp} not in WP-M-00")
        elif producer.get(wp) in acts:
          if producer[wp] >= aid:
            model.err("P5", aid, f"input {wp} comes from {producer[wp]}, which is not earlier; renumber, or model the iteration as an interface")
        elif GATES.index(reg[wp].first_gate or "G6") >= GATES.index(gid):
          model.err("P5", aid, f"input {wp} is gated {reg[wp].gate} and not produced in {gid}")
    orders[gid] = sorted(acts)
    # P6 confirmation measures equal the WP-M-06 §9 row for the gate
    planned = set(ctx.gate_measures.get(gid, []))
    modelled = {r for r, x in model.reviews.items() if x["phase"] == gid}
    if planned != modelled:
      model.err("P6", gid, f"confirmation measures differ from WP-M-06 §9: missing {sorted(planned - modelled)}, extra {sorted(modelled - planned)}")

  conf_text = CONFIRMATION_MD.read_text(encoding="utf-8")
  for rid, rv in model.reviews.items():
    for wp in rv["covers"]:
      if wp not in reg:
        model.err("P6", rid, f"covers {wp}, which is not in WP-M-00")
    if not re.search(rf"\b{re.escape(rid)}\b", conf_text):
      model.err("P6", rid, "not defined in WP-M-06")

  # P7 interfaces: both ends produced by an activity, anchors present verbatim
  texts: dict[str, str] = {}
  for iid, ix in model.interfaces.items():
    if ix["status"] not in INTERFACE_STATUS:
      model.err("P7", iid, f"status must be one of {sorted(INTERFACE_STATUS)}")
    if (ix["status"] == "open") != bool(ix["open_item"]):
      model.err("P7", iid, "open_item is required exactly when status is open")
    if ix["due"] not in GATES:
      model.err("P7", iid, f"unknown gate {ix['due']}")
    if len(ix["between"]) != 2:
      model.err("P7", iid, "between must name two work products")
    for wp in ix["between"]:
      if wp not in producer:
        model.err("P7", iid, f"{wp} is not produced by any activity")
    for anchor in ix["anchors"]:
      wp, sep, needle = anchor.partition(":")
      if not sep or wp not in reg:
        model.err("P7", iid, f"anchor {anchor!r} must be WP-x-nn:text with a registered work product")
        continue
      if wp not in texts:
        texts[wp] = reg[wp].path.read_text(encoding="utf-8") if reg[wp].path.exists() else ""
      if needle not in texts[wp]:
        model.err("P7", iid, f"anchor text {needle!r} not found in {wp}")
  return orders


# ---------------------------------------------------------------- rendering

GENERATED_NOTE = "<!-- GENERATED by assurance/process/tools/process_model.py from assurance/process/model/. Do not edit; edit the model and re-run. -->"


def _q(text: str) -> str:
  """Mermaid node label: quoted, with characters Mermaid would misread replaced."""
  return '"' + text.replace('"', "'").replace("[", "(").replace("]", ")") + '"'


def _nid(item_id: str) -> str:
  return item_id.replace("-", "_")


def _link(wp: str, ctx: Context) -> str:
  row = ctx.register.get(wp)
  if not row:
    return wp
  return f"[{wp}]({Path('..', '..', row.path.relative_to(ASSURANCE_DIR)).as_posix()})"


def render_lifecycle(model: Model, ctx: Context) -> str:
  lines = [GENERATED_NOTE, "", "# Integrated lifecycle (L0)", "",
           "One lifecycle with one gate per phase. All disciplines work inside each phase and decide at the same gate.",
           "Gate names and exit criteria come from [WP-M-00 §2](../../01-management/WP-M-00-work-product-register.md#2-gates). The handbook column maps each phase to the lifecycle chapters of the Integrated Automotive Standards Handbook (informative).",
           "", "```mermaid", "flowchart LR"]
  for g in GATES:
    name = ctx.gates.get(g, ("?", ""))[0]
    n = len([a for a in model.activities.values() if a["phase"] == g])
    detail = f"{n} activities modelled" if model.phases.get(g, {}).get("modelled") else "not modelled yet"
    lines.append(f"  {g}[{_q(f'{g} {name}<br/>{detail}')}]")
  lines.append("  " + " --> ".join(GATES))
  lines.append("  classDef modelled fill:#1f6feb,stroke:#0b3d91,color:#ffffff")
  lines.append("  classDef pending fill:#f6f8fa,stroke:#8c959f,color:#57606a,stroke-dasharray: 4 3")
  mod = [g for g in GATES if model.phases.get(g, {}).get("modelled")]
  if mod:
    lines.append(f"  class {','.join(mod)} modelled")
  pend = [g for g in GATES if g not in mod]
  if pend:
    lines.append(f"  class {','.join(pend)} pending")
  lines += ["```", "", "| Gate | Phase | Exit criterion (WP-M-00 §2) | Handbook chapters | Process map |", "|---|---|---|---|---|"]
  for g in GATES:
    name, exit_ = ctx.gates.get(g, ("?", "?"))
    ch = ", ".join(str(c) for c in model.phases.get(g, {}).get("handbook_chapters", []))
    mp = f"[{g} map]({g.lower()}-{_slug(name)}.md)" if model.phases.get(g, {}).get("modelled") else "Not modelled yet"
    lines.append(f"| {g} | {name} | {exit_} | {ch} | {mp} |")
  return "\n".join(lines) + "\n"


def _slug(name: str) -> str:
  return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _clause_cell(wps: list[str], ctx: Context, std: str) -> str:
  vals = []
  for wp in wps:
    v = ctx.register[wp].clauses[std] if wp in ctx.register else ""
    if v and v != "—" and v not in vals:
      vals.append(v)
  return "; ".join(vals)


def render_phase(gid: str, order: list[str], model: Model, ctx: Context) -> str:
  name, exit_ = ctx.gates[gid]
  acts = [model.activities[a] for a in order]
  producer = {wp: a["id"] for a in acts for wp in a["produces"]}
  reviews = [r for r in model.reviews.values() if r["phase"] == gid]
  ixs = [x for x in model.interfaces.values() if x["phase"] == gid]
  lane_ids = [lid for lid in model.lanes if lid != "assess" and any(a["lane"] == lid for a in acts)]

  out = [GENERATED_NOTE, "", f"# {gid} {name}: integrated process map (L1)", "",
         "Back to the [lifecycle map](lifecycle.md). Model: [`model/`](../model/), method: [process README](../README.md).", "",
         "## 1. Swimlane map", "",
         "One box per discipline; green activities are joint work of all disciplines and sit outside the boxes. Arrows are work-product inputs: an activity cannot finish before its inputs exist. An arrow implied by a longer path is left out; §2 lists every input. Iteration between disciplines is shown in the interface map (§1.1), not here.", "",
         "```mermaid", "flowchart LR"]
  # Joint activities are drawn outside the discipline lanes: they open and close the phase, and one
  # box spanning both ends would pull the flow backwards.
  for a in acts:
    if a["lane"] == "joint":
      out.append(f"  {_nid(a['id'])}[{_q(a['id'] + '<br/>' + a['name'] + '<br/>' + ', '.join(a['produces']))}]")
  for lid in [x for x in lane_ids if x != "joint"]:
    out.append(f"  subgraph L_{lid}[{_q(model.lanes[lid]['name'])}]")
    out.append("    direction LR")
    for a in acts:
      if a["lane"] == lid:
        out.append(f"    {_nid(a['id'])}[{_q(a['id'] + '<br/>' + a['name'] + '<br/>' + ', '.join(a['produces']))}]")
    out.append("  end")
  out.append(f"  subgraph L_assess[{_q(model.lanes['assess']['name'])}]")
  out.append("    direction LR")
  for r in reviews:
    out.append(f"    {_nid(r['id'])}[{_q(r['id'] + '<br/>' + r['independence'])}]")
  out.append("  end")
  out.append(f"  GATE{{{{{_q(gid + ' ' + name + ' gate')}}}}}")
  edges = direct_deps({a["id"]: a for a in acts}, producer)
  for a in acts:
    for src in sorted(edges[a["id"]]):
      out.append(f"  {_nid(src)} --> {_nid(a['id'])}")
  consumed = {w for a in acts for w in a["inputs"]}
  for a in acts:
    if not any(w in consumed for w in a["produces"]):
      out.append(f"  {_nid(a['id'])} --> GATE")
  out.append("  L_assess --> GATE")
  joint = [_nid(a["id"]) for a in acts if a["lane"] == "joint"]
  if joint:
    out += ["  classDef joint fill:#dafbe1,stroke:#1a7f37,color:#0f3d1c", f"  class {','.join(joint)} joint"]
  out += ["  classDef review fill:#fff8c5,stroke:#9a6700,color:#3d2c00", f"  class {','.join(_nid(r['id']) for r in reviews)} review",
          "  classDef gate fill:#1f6feb,stroke:#0b3d91,color:#ffffff", "  class GATE gate", "```", ""]

  # 1.1 interface map: one node per lane, one edge per lane pair listing its interfaces
  out += ["### 1.1 Interface map", "",
          "Where one discipline's analysis depends on another's. Each edge lists the interfaces of §3 between two lanes; OPEN marks one that a recorded open item still has to settle.", "",
          "```mermaid", "flowchart LR"]
  pairs: dict[tuple[str, str], list[str]] = {}
  for x in ixs:
    la, lb = sorted(model.activities[producer[w]]["lane"] for w in x["between"])
    pairs.setdefault((la, lb), []).append(x["id"] + (" OPEN" if x["status"] == "open" else ""))
  used = sorted({ln for p in pairs for ln in p}, key=list(model.lanes).index)
  for ln in used:
    out.append(f"  {ln}([{_q(model.lanes[ln]['name'])}])")
  for (la, lb), labels in pairs.items():
    out.append(f"  {la} -. {_q(', '.join(labels))} .- {lb}")
  out += ["```", ""]

  # 2. activities
  out += ["## 2. Activities", "",
          "Clause references and status are read from the [register (WP-M-00)](../../01-management/WP-M-00-work-product-register.md) row of each work product the activity produces.", "",
          "| Activity | Lane | Produces | Inputs | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Handbook WP | Status |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
  for a in acts:
    status = ", ".join(sorted({STATUS_NAMES.get(ctx.register[w].status, ctx.register[w].status) for w in a["produces"]}))
    out.append(f"| {a['id']} {a['name']} | {model.lanes[a['lane']]['name']} | {', '.join(_link(w, ctx) for w in a['produces'])} | {', '.join(a['inputs'])} | "
               + " | ".join(_clause_cell(a["produces"], ctx, k) for k, _ in STANDARDS) + f" | {', '.join(a['handbook_wp'])} | {status} |")
  out.append("")

  # 3. interfaces
  out += ["## 3. Cross-domain interfaces", "",
          "Each interface is anchored to text in both work products; the checker fails if an anchor disappears. *Documented* means the documents reference each other but nobody has reviewed the agreement yet.", "",
          "| ID | Pattern | Between | Topic | Status | Open item | Due |", "|---|---|---|---|---|---|---|"]
  for x in ixs:
    lanes = " / ".join(model.lanes[model.activities[producer[w]]["lane"]]["name"].split(" (")[0] for w in x["between"])
    out.append(f"| {x['id']} | {x['pattern']} | {', '.join(_link(w, ctx) for w in x['between'])} ({lanes}) | {x['topic']} | {x['status'].capitalize()} | {x['open_item'] or '—'} | {x['due']} |")
  out.append("")

  # 4. clause coverage by standard
  out += ["## 4. Clause coverage by standard", "",
          "Which activity answers each clause reference listed in the register. One activity can answer several standards; that is the point of the integrated lifecycle.", ""]
  for key, title in STANDARDS:
    by_clause: dict[str, list[str]] = {}
    for a in acts:
      for wp in a["produces"]:
        c = ctx.register[wp].clauses[key]
        if c and c != "—" and a["id"] not in by_clause.setdefault(c, []):
          by_clause[c].append(a["id"])
    out.append(f"- **{title}:** " + ("; ".join(f"{c} → {', '.join(ids)}" for c, ids in by_clause.items()) if by_clause else "none"))
  out.append("")

  # 5. gate readiness
  out += [f"## 5. {gid} readiness", "", f"**Exit criterion (WP-M-00 §2):** {exit_}", ""]
  wps = [w for a in acts for w in a["produces"]]
  counts: dict[str, int] = {}
  for w in wps:
    counts[ctx.register[w].status] = counts.get(ctx.register[w].status, 0) + 1
  out.append("**Work products:** " + ", ".join(f"{n} {STATUS_NAMES.get(s, s)}" for s, n in sorted(counts.items())) + f" of {len(wps)}. Approval needs the verification review of [WP-P-05](../../07-supporting/WP-P-05-verification-review-procedure.md).")
  out += ["", "**Roles the lanes need (WP-M-02 §3.1):**", "", "| Lane | Role | Assigned to | Needed by |", "|---|---|---|---|"]
  for lid in [*lane_ids, "assess"]:
    role = model.lanes[lid]["role"]
    who, by = ctx.roles.get(role, ("?", "?"))
    out.append(f"| {model.lanes[lid]['name']} | {role} | {who} | {by} |")
  out += ["", "**Confirmation measures (WP-M-06 §9):**", "", "| Measure | Covers | Independence | Record |", "|---|---|---|---|"]
  for r in reviews:
    rec = CONFIRMATION_DIR / f"{r['id']}.md"
    out.append(f"| {r['id']} {r['name']} | {', '.join(r['covers'])} | {r['independence']} | {'Performed' if rec.exists() else 'Not performed'} |")
  covered = {w for r in reviews for w in r["covers"]}
  uncovered = [w for w in wps if w not in covered]
  out += ["", "**Work products with no confirmation measure at this gate** (verification review only): " + (", ".join(uncovered) if uncovered else "none") + ".", ""]
  due = [x for x in ixs if x["status"] == "open" and GATES.index(x["due"]) <= GATES.index(gid)]
  out.append("**Open interfaces due at this gate:** " + (", ".join(f"{x['id']} ({x['open_item']})" for x in due) if due else "none") + ".")
  return "\n".join(out) + "\n"


def render_all(model: Model, ctx: Context, orders: dict[str, list[str]]) -> dict[Path, str]:
  files = {MAPS_DIR / "lifecycle.md": render_lifecycle(model, ctx)}
  for gid, order in orders.items():
    files[MAPS_DIR / f"{gid.lower()}-{_slug(ctx.gates[gid][0])}.md"] = render_phase(gid, order, model, ctx)
  return files


def main(argv: list[str]) -> int:
  model = load_model()
  ctx = load_context()
  orders = check(model, ctx)
  if model.errors:
    print("\n".join(model.errors))
    print(f"FAIL: {len(model.errors)} process model error(s)")
    return 1
  files = render_all(model, ctx, orders)
  if "--check" in argv:
    stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    extra = [p for p in MAPS_DIR.glob("*.md") if p not in files]
    for p in stale + extra:
      print(f"[P8] {p.relative_to(ASSURANCE_DIR)}: {'stale' if p in stale else 'not generated by the model'}; run process_model.py")
    if stale or extra:
      return 1
    print(f"OK: {len(model.activities)} activities, {len(model.reviews)} reviews, {len(model.interfaces)} interfaces; maps current")
    return 0
  MAPS_DIR.mkdir(exist_ok=True)
  for p, text in files.items():
    p.write_text(text, encoding="utf-8")
    print(f"wrote {p.relative_to(ASSURANCE_DIR)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
