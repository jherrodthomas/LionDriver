#!/usr/bin/env python3
"""LionDriver plan as a Jantt chart (WP-P-11 §7): one linked view of activities, gates and decisions.

Writes `liondriver.jantt.json` in the Jantt JSON format (https://github.com/AhmadHassan-BTed/Jantt,
schema `schema/jantt.schema.json` at the vendored commit) and `index.html`, a self-contained page
that renders it with the vendored Jantt bundle. Nothing in the plan is entered here. It is read at
generation time from:

| Plan element | Read from |
|---|---|
| Activities, lanes, inputs and outputs, confirmation reviews | `assurance/process/model/*.yaml` (WP-P-11) |
| Status and file of each work product, gate names | WP-M-00 §2, §3 (through `process_model.py`) |
| Phase windows and gate dates | WP-M-03 §5 (through `fig_m_plans.py`, as Figure 5-2) |
| Decisions still to be made or applied by the lead | `assurance/01-management/decisions/register.yaml` |

The activities have no durations of their own: WP-M-03 estimates effort per phase only. Each
activity is therefore drawn inside its phase window, on the earliest dates, in the column of its
place in the phase's input order. The bars show order and dependency, not a schedule.

The output is not committed: the decision register changes in most pull requests, and a committed
plan would go stale with each of them. CI builds it on every run and keeps it as the `plan`
workflow artifact (WP-P-11 §7).

Usage:
    python3 jantt_plan.py --check        # build in memory; fail on a Jantt rule or an altered bundle
    python3 jantt_plan.py [--out DIR]    # same checks, then write both files to DIR (default build/plan)
"""
# ruff: noqa: E501
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
PROCESS_DIR = TOOLS_DIR.parent
ASSURANCE_DIR = PROCESS_DIR.parent
REPO_DIR = ASSURANCE_DIR.parent
OUT_DIR = REPO_DIR / "build" / "plan"
VENDOR_DIR = TOOLS_DIR / "vendor" / "jantt-2fd3830"
REGISTER_YAML = ASSURANCE_DIR / "01-management" / "decisions" / "register.yaml"
REPO_URL = "https://github.com/jherrodthomas/LionDriver/blob/liondriver-dev"

# The vendored bundle, built from Jantt commit 2fd3830 (vendor/jantt-2fd3830/SOURCE.md). A changed
# file fails --check: the bundle is replaced only together with SOURCE.md and these digests.
BUNDLE = {
  "jantt.standalone.iife.js": "ae7caabbda202ce3f8cdff4001990ea56f8b3a7a4c7ec0397c38331e74c79a1e",
  "style.css": "562045ff85cda99959a9691b3c669c942b770500a7a4b19e9f117ab53ca2967b",
}

sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(ASSURANCE_DIR / "01-management" / "figures"))
import fig_m_plans as fmp
import process_model as pm

LANE_COLORS = {
  "joint": ("#475569", "#E2E8F0"), "fusa": ("#B91C1C", "#FDE2E1"), "hw": ("#92400E", "#FDE9D2"),
  "sw": ("#1D4ED8", "#DBEAFE"), "sotif": ("#047857", "#D1FAE5"), "ai": ("#6D28D9", "#EDE9FE"),
  "cs": ("#0E7490", "#CFFAFE"), "assess": ("#A16207", "#FEF3C7"),
}
EXTRA_CATEGORIES = {
  "gate": ("Gate", "#111827", "#E5E7EB"),
  "decision": ("Decision for the project lead", "#BE185D", "#FCE7F3"),
}
# Work-product status (WP-M-00) to Jantt status and progress. Progress shows the register status,
# not effort spent: an activity is as far as the least advanced work product it produces.
STATUS = {"S": ("not-started", 0.0), "D": ("in-progress", 0.5), "R": ("submitted", 0.8),
          "A": ("completed", 1.0), "B": ("completed", 1.0), "N/A": ("completed", 1.0)}
STATUS_ORDER = ["S", "D", "R", "A", "B", "N/A"]
DOC_STATUS = {"S": "missing", "D": "pending", "R": "pending", "A": "have", "B": "have", "N/A": "have"}
DECISION_STATUS = {"open": ("blocked", 0.0), "queued": ("not-started", 0.0), "answered": ("in-progress", 0.5)}
WP_ID = re.compile(r"\bWP-[A-Z]-\d{2}\b")
ACTIVITY_ID = re.compile(r"(GOV|CON|DES|DEV|INT|REL|OPS)-\d{2}$")
P6_MONTHS = 12   # operation is continuous; this many months are drawn after the earliest G5


def add_months(start: dt.date, months: float) -> dt.date:
  whole = int(months)
  y, m = divmod(start.year * 12 + start.month - 1 + whole, 12)
  base = dt.date(y, m + 1, 1)
  return base + dt.timedelta(days=round((months - whole) * 30.44))


def iso(d: dt.date) -> str:
  return d.isoformat()


def phase_windows(plan) -> dict[str, tuple[dt.date, dt.date, str]]:
  """Gate -> (phase start, earliest gate date, latest gate month), from WP-M-03 §5.

  A gate falls on the first day of the month WP-M-03 names for it (G0 "Mar 2027" is 2027-03-01);
  the phase's activities fill the days before it, and the next phase starts on the gate date."""
  start = dt.date(plan.start[0], plan.start[1], 1)
  ends = fmp.gate_months(plan)
  out, prev = {}, 0.0
  for ph in plan.phases:
    if ph.gate in ends:
      lo, hi = ends[ph.gate]
      out[ph.gate] = (add_months(start, prev), add_months(start, lo), fmp.cal_month(plan, hi))
      prev = lo
    else:
      out[ph.gate] = (add_months(start, prev), add_months(start, prev + P6_MONTHS), "continuous")
  return out


def span(window_start: dt.date, column: int, width: int) -> tuple[str, str]:
  """Dates of the bar in `column` of a phase window split into columns of `width` days."""
  s = window_start + dt.timedelta(days=column * width)
  return iso(s), iso(s + dt.timedelta(days=width - 1))


def in_phase_deps(acts: dict[str, dict]) -> dict[str, set[str]]:
  """Activity -> earlier activities of the same phase whose outputs it consumes (latest supplier
  of each input, as the process maps draw it), with transitive edges removed."""
  suppliers = pm.phase_suppliers(acts)
  deps = {}
  for a, act in acts.items():
    ds = set()
    for wp in act["inputs"]:
      earlier = [s for s in suppliers.get(wp, []) if s < a]
      if earlier:
        ds.add(earlier[-1])
    deps[a] = ds

  def reach(a: str, seen: set[str]) -> set[str]:
    for d in deps.get(a, ()):
      if d not in seen:
        seen.add(d)
        reach(d, seen)
    return seen

  return {a: {d for d in ds if not any(d in reach(o, set()) for o in ds - {d})} for a, ds in deps.items()}


def least_status(wps: list[str], reg: dict) -> str:
  known = [reg[w].status for w in wps if w in reg and reg[w].status in STATUS]
  return min(known, key=STATUS_ORDER.index) if known else "S"


def wp_link(wp: str, reg: dict) -> str:
  row = reg.get(wp)
  return f"{REPO_URL}/{row.path.relative_to(REPO_DIR).as_posix()}" if row else ""


def lead_decisions(path: Path = REGISTER_YAML) -> list[dict]:
  """Decisions the lead still has to make (open, queued) or Claude still has to apply (answered)."""
  items = yaml.safe_load(path.read_text(encoding="utf-8"))
  return [d for d in items if d.get("decider", "lead") == "lead" and d.get("status") in DECISION_STATUS]


def build() -> dict:
  model = pm.load_model()
  ctx = pm.load_context()
  orders = pm.check(model, ctx)
  if model.errors:
    raise SystemExit("process model has errors; run process_model.py first:\n" + "\n".join(model.errors))
  plan = fmp.load_plan()
  if not plan.start:
    raise SystemExit("WP-M-03 §5 has no calendar start: the plan cannot be dated")
  reg = ctx.register
  windows = phase_windows(plan)
  phase_name = {ph.gate: f"{ph.pid} {ph.name} ({ph.gate})" for ph in plan.phases}

  tasks: list[dict] = []
  by_id: dict[str, dict] = {}
  first_task_of_wp: dict[str, str] = {}   # work product -> activity that first produces it
  phase_of: dict[str, str] = {}
  prev_gate = None
  for wbs, gate in enumerate(pm.GATES):
    if gate not in orders:
      continue
    ws, gd, latest = windows[gate]
    acts = {a: model.activities[a] for a in orders[gate]}
    deps = in_phase_deps(acts)
    reviews = {r: x for r, x in model.reviews.items() if x["phase"] == gate}
    suppliers = pm.phase_suppliers(acts)
    rev_deps = {r: {suppliers[w][-1] for w in x["covers"] if w in suppliers} for r, x in reviews.items()}
    level: dict[str, int] = {}
    for a in sorted(acts):
      level[a] = 1 + max((level[d] for d in deps[a]), default=-1)
    for r in reviews:
      level[r] = 1 + max((level[d] for d in rev_deps[r]), default=-1)
    columns = max(level.values(), default=0) + 1
    width = max(1, (gd - ws).days // columns)
    has_dependents = {d for ds in list(deps.values()) + list(rev_deps.values()) for d in ds}

    for n, a in enumerate(sorted(acts), 1):
      act = acts[a]
      outs = pm.outputs(act)
      st = least_status(outs, reg)
      status, progress = STATUS[st]
      dep_ids = sorted(deps[a]) or ([prev_gate] if prev_gate else [])
      earlier = sorted({w for w in act["inputs"] if w in first_task_of_wp and phase_of[first_task_of_wp[w]] != gate})
      start, end = span(ws, level[a], width)
      lane = model.lanes[act["lane"]]["name"]
      notes = [f"{act['name']}. Lane: {lane}. Phase: {phase_name[gate]}.",
               f"Produces: {', '.join(act['produces']) or 'none'}." + (f" Updates: {', '.join(act['updates'])}." if act.get("updates") else ""),
               f"Inputs: {', '.join(act['inputs']) or 'none'}."]
      if earlier:
        notes.append("From earlier phases (reached through the gate): " + ", ".join(f"{w} ({first_task_of_wp[w]})" for w in earlier) + ".")
      notes.append(f"Status from WP-M-00: {pm.STATUS_NAMES.get(st, st)} (the least advanced output). Dates are placement inside the phase window, not an estimate.")
      task = {"id": a, "wbs": f"{wbs}.{n}",
              "label": f"{a} {act['name']}", "category": act["lane"], "phase": phase_name[gate],
              "start": start, "end": end, "dependsOn": dep_ids or None, "gapDays": 0,
              "progress": progress, "status": status, "locked": True, "notes": " ".join(notes),
              "fields": {"produces": ", ".join(act["produces"]), "updates": ", ".join(act.get("updates", [])),
                         "inputs": ", ".join(act["inputs"]), "lane": lane,
                         "documents": " ".join(wp_link(w, reg) for w in outs)}}
      tasks.append(task)
      by_id[a] = task
      phase_of[a] = gate
      for w in act["produces"]:
        first_task_of_wp.setdefault(w, a)

    for n, r in enumerate(sorted(reviews), 1):
      x = reviews[r]
      present = pm.record_present(x, reg)
      start, end = span(ws, level[r], width)
      dep_ids = sorted(rev_deps[r]) or ([prev_gate] if prev_gate else [])
      task = {"id": r, "wbs": f"{wbs}.R{n}",
              "label": f"{r} {x['name']}", "category": "assess", "phase": phase_name[gate],
              "start": start, "end": end, "dependsOn": dep_ids or None, "gapDays": 0,
              "progress": 1.0 if present else 0.0, "status": "completed" if present else "not-started", "locked": True,
              "notes": f"Confirmation measure {pm.measure_id(r)} (WP-M-06), independence {x['independence']}. Covers {', '.join(x['covers'])}. Record: {pm.record_label(x)} ({'present' if present else 'not yet'}).",
              "fields": {"covers": ", ".join(x["covers"]), "independence": x["independence"]}}
      tasks.append(task)
      by_id[r] = task
      phase_of[r] = gate

    gate_id = f"GATE-{gate}"
    sinks = sorted(i for i in list(acts) + list(reviews) if i not in has_dependents)
    passed = gate in plan.passed
    tasks.append({"id": gate_id, "wbs": f"{wbs}.G", "label": f"{gate} {ctx.gates[gate][0]}", "category": "gate",
                  "phase": phase_name[gate], "start": iso(gd), "end": iso(gd), "milestone": True, "locked": True,
                  "dependsOn": sinks or None, "gapDays": 0, "progress": 1.0 if passed else 0.0,
                  "status": "completed" if passed else "not-started",
                  "notes": f"Gate {gate}: {ctx.gates[gate][0]}. Exit: {ctx.gates[gate][1]} Earliest date shown; latest {latest} (WP-M-03 §5). {'Passed.' if passed else 'Not passed: no gate record says Pass.'}",
                  "fields": {"latest": latest}})
    phase_of[gate_id] = gate
    prev_gate = gate_id

  # Decisions: each blocks the activities that produce or update the work products it names.
  producers: dict[str, list[str]] = {}
  for a, act in model.activities.items():
    for w in pm.outputs(act):
      producers.setdefault(w, []).append(a)
  plan_start = iso(dt.date(plan.start[0], plan.start[1], 1))
  for d in lead_decisions():
    text = f"{d.get('blocks', '')} {' '.join(d.get('sources', []) or [])}"
    wps = sorted(set(WP_ID.findall(text)))
    gate = d.get("gate")
    targets = sorted({min((a for a in producers.get(w, []) if model.activities[a]["phase"] == gate), default=None)
                      or (producers[w][0] if producers.get(w) else None) for w in wps} - {None})
    status, progress = DECISION_STATUS[d["status"]]
    day = str(d.get("answer", {}).get("at") if d["status"] == "answered" and d.get("answer") else d.get("asked") or plan_start)
    blocked, waits = [], []
    for a in targets:
      (blocked if by_id[a]["start"] > day else waits).append(a)
      if by_id[a]["start"] > day:
        deps = by_id[a]["dependsOn"] or []
        by_id[a]["dependsOn"] = sorted(set(deps) | {d["id"]})
      else:
        by_id[a]["fields"]["waits_on"] = ", ".join(filter(None, [by_id[a]["fields"].get("waits_on", ""), d["id"]]))
    tasks.append({"id": d["id"], "wbs": f"D.{d['id'][3:]}", "label": f"{d['id']} {d['question']}", "category": "decision",
                  "phase": "Decisions", "start": day, "end": day, "milestone": True, "locked": True,
                  "progress": progress, "status": status, "urgent": d["status"] == "open",
                  "notes": f"{d.get('context', '')} Status: {d['status']}" + (f", answered {d['answer'].get('choice')}" if d.get("answer") else "") +
                           f". Gate {gate or '—'}. Blocks: {d.get('blocks', '—')}." + (f" Activities in progress that wait on it: {', '.join(waits)}." if waits else ""),
                  "fields": {"blocks_activities": ", ".join(blocked + waits), "register": f"{REPO_URL}/assurance/01-management/decisions/register.yaml"}})

  documents = [{"id": wp, "label": f"{wp} {row.name}", "status": DOC_STATUS.get(row.status, "missing"),
                "url": wp_link(wp, reg), "note": f"WP-M-00: {pm.STATUS_NAMES.get(row.status, row.status)}, gate {row.gate}"}
               for wp, row in sorted(reg.items())]
  categories = {lid: {"label": lane["name"], "color": LANE_COLORS.get(lid, ("#334155", "#E2E8F0"))[0],
                      "soft": LANE_COLORS.get(lid, ("#334155", "#E2E8F0"))[1]} for lid, lane in model.lanes.items()}
  categories.update({k: {"label": v[0], "color": v[1], "soft": v[2]} for k, v in EXTRA_CATEGORIES.items()})
  last = max(t["end"] for t in tasks)
  return {
    "meta": {"title": "LionDriver assurance plan", "description": "Generated by assurance/process/tools/jantt_plan.py from the process model (WP-P-11), WP-M-00, WP-M-03 §5 and the decision register. Activities are placed inside their phase window on the earliest dates; the bars show order and dependency, not an estimate. Do not edit: regenerate.",
             "organization": "LionDriver", "start": plan_start, "end": last, "defaultGapDays": 0, "scale": "month",
             "linkRouting": "orthogonal", "showCriticalPath": False, "showBaselines": False, "autoCascade": False, "version": "1.4.0"},
    "categories": categories,
    "documents": documents,
    "tasks": tasks,
  }


def problems(plan: dict) -> list[str]:
  """The Jantt validation rules (README §2 at the vendored commit), checked here so CI needs no Node."""
  out = []
  ids = [t["id"] for t in plan["tasks"]]
  if len(ids) != len(set(ids)):
    out.append("duplicate task ids")
  tasks = {t["id"]: t for t in plan["tasks"]}
  dates: dict[str, tuple[dt.date, dt.date]] = {}
  for t in plan["tasks"]:
    try:
      dates[t["id"]] = (dt.date.fromisoformat(t["start"]), dt.date.fromisoformat(t["end"]))
    except ValueError:
      out.append(f"{t['id']}: date not YYYY-MM-DD")
  for t in plan["tasks"]:
    if t["id"] not in dates:
      continue
    s, e = dates[t["id"]]
    if e < s:
      out.append(f"{t['id']}: end before start")
    if t.get("milestone") and s != e:
      out.append(f"{t['id']}: milestone with a duration")
    if t["category"] not in plan["categories"]:
      out.append(f"{t['id']}: unknown category {t['category']}")
    if not 0.0 <= t.get("progress", 0.0) <= 1.0:
      out.append(f"{t['id']}: progress outside 0..1")
    for d in t.get("dependsOn") or []:
      if d not in tasks:
        out.append(f"{t['id']}: depends on unknown {d}")
      elif d in dates and s < dates[d][1] + dt.timedelta(days=t.get("gapDays", 0)):
        out.append(f"{t['id']}: starts {t['start']} before {d} ends {tasks[d]['end']}")
  state: dict[str, int] = {}

  def visit(i: str, path: list[str]) -> None:
    state[i] = 1
    for d in tasks[i].get("dependsOn") or []:
      if d in tasks and state.get(d) == 1:
        out.append("dependency cycle: " + " -> ".join(path + [d]))
      elif d in tasks and not state.get(d):
        visit(d, path + [d])
    state[i] = 2

  for i in tasks:
    if not state.get(i):
      visit(i, [i])
  return out


def digest(path: Path) -> str:
  return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_problems() -> list[str]:
  out = []
  for name, want in BUNDLE.items():
    p = VENDOR_DIR / name
    if not p.exists():
      out.append(f"vendored bundle file missing: {p.relative_to(REPO_DIR)}")
    elif digest(p) != want:
      out.append(f"{p.relative_to(REPO_DIR)}: SHA-256 {digest(p)} differs from the pinned {want}")
  return out


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LionDriver Plan</title>
{style}
<style>
:root {{ --bg: #ffffff; --fg: #0f172a; --muted: #475569; --line: #e2e8f0; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg: #0b1120; --fg: #e2e8f0; --muted: #94a3b8; --line: #1e293b; }} }}
:root[data-theme="dark"] {{ --bg: #0b1120; --fg: #e2e8f0; --muted: #94a3b8; --line: #1e293b; }}
html, body {{ margin: 0; height: 100%; background: var(--bg); color: var(--fg); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }}
header {{ padding: 12px 16px; border-bottom: 1px solid var(--line); }}
header h1 {{ margin: 0 0 4px; font-size: 18px; }}
header p {{ margin: 0; color: var(--muted); max-width: 72ch; }}
#plan {{ height: calc(100vh - 92px); min-height: 480px; max-width: 100vw; overflow: auto; }}
</style>
</head>
<body>
<header>
<h1>LionDriver assurance plan</h1>
<p>{summary} Bars sit inside their phase window on the earliest dates and show order and dependency, not an estimate. Generated by <code>jantt_plan.py</code>; read-only.</p>
</header>
<div id="plan"></div>
{script}
<script>
const plan = {data};
const pref = document.documentElement.dataset.theme;
const dark = pref ? pref === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
Jantt.mount("#plan", plan, {{ readOnly: true, autoCascade: false, themeClassName: dark ? "jantt-theme-dark" : "jantt-theme-light" }});
</script>
</body>
</html>
"""


def page(plan: dict) -> str:
  """The plan page with the bundle and the data inlined, so it opens offline and publishes as one file."""
  n_act = sum(1 for t in plan["tasks"] if ACTIVITY_ID.match(t["id"]))
  n_rev = sum(1 for t in plan["tasks"] if t["category"] == "assess" and not ACTIVITY_ID.match(t["id"]))
  n_dec = sum(1 for t in plan["tasks"] if t["category"] == "decision")
  n_gate = sum(1 for t in plan["tasks"] if t["category"] == "gate")
  summary = f"{n_act} activities, {n_rev} confirmation measures, {n_gate} gates and {n_dec} lead decisions not yet applied, linked by the work products they exchange."
  style = "<style>\n" + (VENDOR_DIR / "style.css").read_text(encoding="utf-8") + "\n</style>"
  script = "<script>\n" + (VENDOR_DIR / "jantt.standalone.iife.js").read_text(encoding="utf-8").replace("</script", "<\\/script") + "\n</script>"
  data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
  return PAGE.format(style=style, script=script, data=data, summary=summary)


def main(argv: list[str]) -> int:
  plan = build()
  errs = problems(plan) + bundle_problems()
  if errs:
    print("\n".join(errs))
    print(f"FAIL: {len(errs)} plan problem(s)")
    return 1
  if "--check" in argv:
    print(f"OK: {len(plan['tasks'])} tasks, Jantt rules hold, bundle matches its pin")
    return 0
  out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else OUT_DIR
  out.mkdir(parents=True, exist_ok=True)
  (out / "liondriver.jantt.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
  (out / "index.html").write_text(page(plan), encoding="utf-8")
  print(f"wrote {out}/liondriver.jantt.json and {out}/index.html ({len(plan['tasks'])} tasks)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
