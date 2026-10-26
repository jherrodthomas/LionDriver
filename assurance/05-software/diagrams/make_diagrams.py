#!/usr/bin/env python3
"""Generate the MATLAB-style design diagrams of the software work products (SVG, deterministic).

  stateflow-<record>.svg   Stateflow-style chart of each state-machine record in ../state-machines/*.yaml:
                           states as rounded boxes, default transition, transitions grouped per state pair and
                           labelled with their IDs, and a transition table in Stateflow label notation
                           "event [guard] / {action}". Solid: implemented or partial; dashed: not implemented
                           (target state, code field "not implemented"); the table gives the WP-W-02 Baseline status
                           of the cited SWSRs, which the checker uses (a transition can exist and still not meet them).
  simulink-envelope.svg    Simulink-style block diagram of the safety envelope signal flow (reference build),
                           each block citing its WP-W-05 unit; the authority chart is drawn as a chart block.

The charts are generated from the records, so they cannot drift from WP-W-05 §5. The block diagram is defined
below as data and describes the code at the baseline of WP-W-05 (a design description, not verified).

Usage:  python3 assurance/05-software/diagrams/make_diagrams.py [--check]
Standard library only (PyYAML used by the record loader if installed).
"""
from __future__ import annotations

import importlib.util
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svgkit as K  # noqa: E402

_spec = importlib.util.spec_from_file_location("check_state_machines",
                                               HERE.parents[1] / "trace" / "tools" / "check_state_machines.py")
csm = importlib.util.module_from_spec(_spec)
sys.modules["check_state_machines"] = csm
_spec.loader.exec_module(csm)

# State positions (centre x, y) per record; a state without a position is an error, so a new state forces a layout.
# Optional per record:
#   super     a Stateflow superstate {name, label, members, box (x, y, w, h)}: a transition whose sources are exactly
#             the members is drawn once from the superstate border, and the members are drawn inside it
#   any       "note": transitions from "any" are listed under the chart instead of drawn from every state
#   builds    one chart per build; transitions tagged with the other build are left out. Per build:
#   sources   transition ID -> drawn sources, for an "any" transition that is still drawn (named in the note)
#   targets   transition ID -> drawn targets of a transition to the requested mode "m" (from its guard)
#   bend      (source, target) -> extra curvature;  via  (source, target) -> the curve's control point
#   loops     state -> "below" to put its self loops under the box
LAYOUT = {
  "SM-TOY-AUTH": {
    "size": (900, 720),
    "states": {"NOT_ALLOWED": (150, 230), "ENGAGE_PENDING": (450, 120), "ALLOWED": (750, 230)},
    "bend": {("ALLOWED", "NOT_ALLOWED"): -10},
    "loops": {"NOT_ALLOWED": "below"},
    "roles": [(None, "no authority"), (4, "engagement window (reference build)", "ENGAGE_PENDING"),
              (1, "authority on the car (controls_allowed = 1)", "ALLOWED")],
    # the revocations ALLOWED -> NOT_ALLOWED as a panel by cause instead of one label; every ID of that edge must be
    # in exactly one group, so a new revocation forces a layout. Names are short view labels; the table is normative
    "panel": {"edge": ("ALLOWED", "NOT_ALLOWED"), "y": 330,
              "groups": [("Driver", ["T2", "T3", "T10e", "T12"]), ("Car bus", ["T4", "T5", "T10c", "T14"]),
                         ("Host", ["T6", "T6a", "T10a", "T10b", "T11", "T9", "T13"]), ("Platform", ["T7", "T10d", "T15"])],
              "names": {"T2": "cruise off", "T3": "brake", "T10e": "steering override", "T12": "driver torque",
                        "T4": "checksum, quality, counter", "T5": "RX check lagging", "T10c": "cruise, main off",
                        "T14": "bus-off", "T6": "not engaged, 1 Hz", "T6a": "not engaged, 0.3 s", "T10a": "heartbeat lost",
                        "T10b": "command not fresh", "T11": "TX rate exceeded", "T9": "TX content rejected",
                        "T13": "SPI errors", "T7": "safety mode set", "T10d": "platform fault", "T15": "forwarding"}}},
  "SM-SAFETY-MODE": {
    "size": (900, 470), "any": "note",
    "states": {"SILENT": (170, 140), "NOOUTPUT": (450, 140), "ELM327": (730, 140),
               "TOYOTA": (330, 360), "OTHER_CAR": (640, 360)},
    "super": {"name": "NONCAR", "label": "non-car modes: no actuation output", "members": ["SILENT", "NOOUTPUT", "ELM327"],
              "box": (50, 78, 800, 110)},
    "loops": {"NONCAR": "below"},
    "roles": [(None, "no actuation output"), (3, "diagnostic", "ELM327"),
              (1, "car mode: actuation possible with authority", "TOYOTA", "OTHER_CAR")],
    "builds": {
      "reference": {"targets": {"M4": ["NONCAR", "TOYOTA"], "M5": ["NONCAR"]}, "bend": {("TOYOTA", "SILENT"): 60}},
      "upstream": {"targets": {"M2": ["NONCAR", "TOYOTA", "OTHER_CAR"]}, "sources": {"M2": ["NONCAR"]},
                   "bend": {("TOYOTA", "SILENT"): 60, ("OTHER_CAR", "SILENT"): -40}},
    }},
  "SM-SELFDRIVED": {
    "size": (900, 600),
    "states": {"disabled": (100, 300), "preEnabled": (360, 150), "enabled": (560, 300),
               "softDisabling": (790, 300), "overriding": (360, 440)},
    "super": {"name": "active", "label": "active (superstate)",
              "members": ["preEnabled", "enabled", "softDisabling", "overriding"], "box": (230, 72, 650, 438)},
    "via": {("active", "disabled"): (130, 120)},
    "bend": {("softDisabling", "disabled"): 230, ("disabled", "preEnabled"): -20,
             ("disabled", "overriding"): 20, ("overriding", "softDisabling"): 60},
    "loops": {"disabled": "below"},
    "roles": [(None, "not engaged"), (4, "engagement pending", "preEnabled"),
              (1, "engaged", "enabled"), (7, "engaged, driver overriding", "overriding"),
              (8, "disengaging (3 s timer)", "softDisabling")]},
}
BOX_H = 52
LEGEND_W = 860


# ------------------------------------------------------------------ geometry

def box_w(name: str) -> float:
  return max(130.0, len(name) * 8.2 + 40)


def border_point(c, w, h, toward):
  """Point where the ray from the box centre c toward `toward` leaves the box (w x h)."""
  dx, dy = toward[0] - c[0], toward[1] - c[1]
  if dx == 0 and dy == 0:
    return c
  tx = (w / 2) / abs(dx) if dx else math.inf
  ty = (h / 2) / abs(dy) if dy else math.inf
  t = min(tx, ty)
  return (c[0] + dx * t, c[1] + dy * t)


def quad(p0, c, p1, t):
  return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
          (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])


def label(x, y, lines, cls="tm"):
  w = max(len(s) for s in lines) * K.CHAR_W * 0.95 + 8
  h = 13 * len(lines) + 4
  out = [f'<rect class="lbl" x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3"/>']
  for i, s in enumerate(lines):
    out.append(K.text(x, y - h / 2 + 13 + 13 * i - 2, s, cls, "middle"))
  return out


# Requirement status of a transition that exists in the code, shown as a badge next to its label
BADGE = {"gap": (8, "no SWSR"), "s5": (4, "SWSR not met")}


def issue(t: dict, sw: dict) -> str | None:
  if t.get("code", "").startswith("not implemented"):
    return None  # drawn dashed already
  st = csm.transition_state(t, sw)
  return "gap" if st == "unknown" else "s5" if st == "not" else None


def badges(x, y, ids, by_id, sw):
  """Badges under an edge label: one per issue kind, naming the IDs when not every ID on the edge has it."""
  out = []
  for kind, (slot, text) in BADGE.items():
    hit = [i for i in ids if issue(by_id[i], sw) == kind]
    if not hit:
      continue
    s = text if len(hit) == len(ids) else f"{text}: {', '.join(hit)}"
    w = len(s) * 5.9 + 12
    out.append(f'<rect class="k{slot}" x="{x - w / 2:.1f}" y="{y - 9:.1f}" width="{w:.1f}" height="15" rx="7"/>')
    out.append(K.text(x, y + 2.5, s, "ts", "middle"))
    y += 18
  return out


B2B = HERE.parent / "reference-models" / "b2b_toy_auth.py"


def b2b_scenarios() -> dict[str, list[str]]:
  """Transition ID -> directed back-to-back scenarios that exercise it, read from the scenario names in the harness
  ("D04 T2 cruise off"), so a chip appears only where a directed scenario names the transition."""
  out: dict[str, set[str]] = {}
  for d, t in re.findall(r"[\"'](D\d+[a-z]?) (T\d+[a-z]?)\b", B2B.read_text(encoding="utf-8")):
    out.setdefault(t, set()).add(d)
  return {t: sorted(v) for t, v in out.items()}


def panel(spec: dict, ids: list[str], by_id: dict, sw: dict, y0: float) -> tuple[list[str], float]:
  """Revocation panel: one row per transition, grouped by cause in a grid of two columns, with its line style, a
  requirement badge and the B2B scenario chip."""
  grouped = [i for _, g in spec["groups"] for i in g]
  if sorted(grouped) != sorted(ids):
    raise SystemExit(f"panel groups {sorted(grouped)} do not match the transitions of the edge {sorted(ids)}")
  scen = b2b_scenarios()
  a, b = spec["edge"]
  out = [K.text(20, y0, f"Revocations {a} → {b}, by cause ({len(ids)} transitions, one row each)", "tb")]
  cols = 2
  col_w = LEGEND_W / cols
  y = y0 + 12
  for r in range(0, len(spec["groups"]), cols):
    row = spec["groups"][r:r + cols]
    h = 30 + 22 * max(len(g) for _, g in row)
    for ci, (gname, items) in enumerate(row):
      x = 20 + ci * col_w
      out.append(f'<rect class="hi" x="{x:.1f}" y="{y}" width="{col_w - 10:.1f}" height="{h}" rx="8"/>')
      out.append(K.text(x + 10, y + 18, gname, "t2"))
      for i, tid in enumerate(items):
        ty = y + 40 + 22 * i
        t = by_id[tid]
        cls = "" if not t.get("code", "").startswith("not implemented") else "todo"
        out.append(f'<path class="edge {cls}" d="M{x + 10:.1f},{ty - 4} L{x + 30:.1f},{ty - 4}"/>')
        out.append(K.arrowhead(x + 32, ty - 4, 1, 0, f"arrow {cls}", size=6))
        out.append(K.text(x + 42, ty, tid, "tb"))
        out.append(K.text(x + 84, ty, spec["names"][tid], "t"))
        bx = x + 84 + len(spec["names"][tid]) * K.CHAR_W + 12
        kind = issue(t, sw)
        if kind:
          slot, txt = BADGE[kind]
          w = len(txt) * 5.9 + 12
          out.append(f'<rect class="k{slot}" x="{bx:.1f}" y="{ty - 11}" width="{w:.1f}" height="15" rx="7"/>')
          out.append(K.text(bx + w / 2, ty, txt, "ts", "middle"))
        if tid in scen:
          chip = " ".join(scen[tid])
          w = len(chip) * 5.9 + 12
          out.append(f'<rect class="k3" x="{x + col_w - 20 - w:.1f}" y="{ty - 11}" width="{w:.1f}" height="15" rx="7"/>')
          out.append(K.text(x + col_w - 20 - w / 2, ty, chip, "ts", "middle"))
    y += h + 10
  out.append(f'<rect class="k3" x="20" y="{y}" width="26" height="14" rx="7"/>')
  out.append(K.text(52, y + 11, "directed back-to-back scenarios that name the transition "
                    "(reference-models/b2b_toy_auth.py); no chip: none does", "t2"))
  return out, y + 24 - y0


# ------------------------------------------------------------------ Stateflow-style charts

def stateflow(sm: dict, sw: dict, record: str, build: str | None = None) -> str:
  name = sm["machine"]
  lay = dict(LAYOUT[name])
  if build:
    lay.update(lay["builds"][build])
  W, H0 = lay["size"]
  pos = dict(lay["states"])
  states = sm["states"]
  missing = [s for s in states if s not in pos]
  if missing:
    raise SystemExit(f"{name}: no layout position for {missing}")
  T = [t for t in sm["transitions"] if build is None or t.get("build", "all") in ("all", build)]
  by_id = {t["id"]: t for t in T}
  size = {s: (box_w(s), BOX_H) for s in states}
  sup = lay.get("super")
  if sup:
    bx, by, bw, bh = sup["box"]
    pos[sup["name"]] = (bx + bw / 2, by + bh / 2)
    size[sup["name"]] = (bw, bh)
    members = set(sup["members"])
  body = []

  def targets(t, s):
    if t["to"] == "same":
      return [s]
    if t["to"] != "m":
      return [t["to"]]
    if t["id"] not in lay.get("targets", {}):
      raise SystemExit(f"{name}: {t['id']} goes to the requested mode m; give its drawn targets in LAYOUT")
    return lay["targets"][t["id"]]

  def drawn_sources(t):
    if t["id"] in lay.get("sources", {}):
      return lay["sources"][t["id"]]
    if t["from"] == "any" and lay.get("any") == "note":
      return []
    src = csm._sources(t, states)
    return [sup["name"]] if sup and set(src) == members else src

  # reachability in this build, from the initial state over every transition (superstate = its members)
  expand = lambda n: sup["members"] if sup and n == sup["name"] else [n]
  reached, todo = set(), [sm["initial"]]
  while todo:
    s = todo.pop()
    if s in reached:
      continue
    reached.add(s)
    for t in T:
      if s in csm._sources(t, states):
        for d in targets(t, s):
          todo += [x for x in expand(d) if x not in reached]
  dead = [s for s in states if s not in reached]

  # group transitions per (source, target, implemented?)
  groups: dict[tuple, list[str]] = {}
  undrawn = []  # transitions out of a state that is unreachable in this build: named under the chart
  for t in T:
    impl = not t.get("code", "").startswith("not implemented")  # drawn solid if the code exists
    for s in drawn_sources(t):
      if s in dead:
        undrawn.append(f"{t['id']} from {s}")
        continue
      for d in targets(t, s):
        groups.setdefault((s, d, impl), []).append(t["id"])

  pan = lay.get("panel")
  pan_ids = []
  if pan:
    for key in [k for k in groups if (k[0], k[1]) == pan["edge"]]:
      pan_ids += groups.pop(key)
    groups[(*pan["edge"], True)] = pan_ids

  def edge_cls(s, impl):
    return "" if impl else "todo"

  # superstate frame first, so edges and states draw over it
  if sup:
    body.append(f'<rect class="sup" x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="16"/>')
    body.append(K.text(bx + 12, by + 17, sup["label"], "t2"))

  # edges between distinct nodes, spread by pair
  pairs: dict[frozenset, list[tuple]] = {}
  for key in groups:
    s, d, _ = key
    if s != d:
      pairs.setdefault(frozenset((s, d)), []).append(key)
  for pair, keys in pairs.items():
    keys.sort(key=lambda k: (k[0], k[2] is False))
    n = len(keys)
    u, v = sorted(pair)  # fixed frame per pair, so both directions bend in one consistent sense
    pu, pv = pos[u], pos[v]
    fx, fy = pv[0] - pu[0], pv[1] - pu[1]
    fl = math.hypot(fx, fy) or 1
    px, py = -fy / fl, fx / fl
    for i, (s, d, impl) in enumerate(keys):
      a, b = pos[s], pos[d]
      off = (i - (n - 1) / 2) * 58 + lay.get("bend", {}).get((s, d), 0)
      mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
      ctrl = lay.get("via", {}).get((s, d)) or (mx + px * off * 2, my + py * off * 2)
      p0 = border_point(a, *size[s], ctrl)
      p1 = border_point(b, *size[d], ctrl)
      cls = edge_cls(s, impl)
      body.append(f'<path class="edge {cls}" d="M{p0[0]:.1f},{p0[1]:.1f} Q{ctrl[0]:.1f},{ctrl[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}"/>')
      e = quad(p0, ctrl, p1, 0.97)
      body.append(K.arrowhead(p1[0], p1[1], p1[0] - e[0], p1[1] - e[1], f"arrow {cls}"))
      lx, ly = quad(p0, ctrl, p1, 0.5)
      ids = groups[(s, d, impl)]
      if pan and (s, d) == pan["edge"]:
        body += label(lx, ly, [f"{len(ids)} revocations", "(by cause below)"])
        continue
      lines = K.wrap(", ".join(ids), 150)
      body += label(lx, ly, lines)
      body += badges(lx, ly + 7 * len(lines) + 12, ids, by_id, sw)

  # self loops, stacked above each state (below if the layout says so); a superstate's loops sit at its right end
  loops: dict[str, list[tuple]] = {}
  for key in groups:
    if key[0] == key[1]:
      loops.setdefault(key[0], []).append(key)
  for s, keys in loops.items():
    cx, cy = pos[s]
    w, h = size[s]
    below = lay.get("loops", {}).get(s) == "below"
    if sup and s == sup["name"]:
      cx, w = bx + bw - 90, 140
    for i, key in enumerate(sorted(keys, key=lambda k: k[2] is False)):
      impl = key[2]
      r = 18 + 16 * i
      x0, x1 = cx - w / 4 - 6 * i, cx + w / 4 + 6 * i
      sgn = 1 if below else -1
      edge = cy + sgn * h / 2
      cls = edge_cls(s, impl)
      body.append(f'<path class="edge {cls}" d="M{x0:.1f},{edge:.1f} C{x0:.1f},{edge + sgn * 2.2 * r:.1f} '
                  f'{x1:.1f},{edge + sgn * 2.2 * r:.1f} {x1:.1f},{edge:.1f}"/>')
      body.append(K.arrowhead(x1, edge, 0, -sgn, f"arrow {cls}"))
      ly = edge + sgn * 1.65 * r
      body += label(cx, ly, [", ".join(groups[key])])
      body += badges(cx + (80 if not below else 0), ly + (0 if not below else 22), groups[key], by_id, sw)

  # states (filled by role; unreachable in this build: dashed, no fill) and default transition
  role = {st: f"k{r[0]}" for r in lay["roles"] if r[0] for st in r[2:]}
  unknown = set(role) - set(states)
  if unknown:
    raise SystemExit(f"{name}: roles name unknown states {sorted(unknown)}")
  for st in states:
    cx, cy = pos[st]
    w, h = size[st]
    if st in dead:
      body.append(f'<rect class="box dead" x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>')
      body.append(K.text(cx - w / 2 + 10, cy - h / 2 + 18, st, "tb"))
      body.append(K.text(cx - w / 2 + 10, cy - h / 2 + 34, "unreachable", "ts"))
      continue
    body.append(f'<rect class="shadow" x="{cx - w / 2 + 3:.1f}" y="{cy - h / 2 + 3:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>')
    body.append(f'<rect class="{role.get(st, 'box')}" x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12"/>')
    body.append(K.text(cx - w / 2 + 10, cy - h / 2 + 18, st, "tb"))
  ix, iy = pos[sm["initial"]]
  w, h = size[sm["initial"]]
  sx = ix - w / 2 - (24 if sup and sm["initial"] in members else 46)
  body.append(f'<circle class="dot" cx="{sx:.1f}" cy="{iy:.1f}" r="4"/>')
  body.append(f'<path class="edge" d="M{sx:.1f},{iy:.1f} L{ix - w / 2:.1f},{iy:.1f}"/>')
  body.append(K.arrowhead(ix - w / 2, iy, 1, 0))

  if pan:
    rows_p, _ = panel(pan, pan_ids, by_id, sw, pan["y"])
    body += rows_p

  # transitions from "any" that are not drawn per state
  notes, anys = [], []
  if lay.get("any") == "note":
    for t in T:
      if t["from"] == "any":
        drawn = lay.get("sources", {}).get(t["id"])
        anys.append(f"{t['id']} ({t['event']} → {t['to']})" + (f", drawn from {', '.join(drawn)} only" if drawn else ""))
  if anys:
    notes.append("In every state, not drawn per state: " + "; ".join(anys) + ".")
  if undrawn:
    notes.append("Not drawn, the source is unreachable in this build: " + ", ".join(undrawn) + ".")
  notes = [ln for n in notes for ln in K.wrap(n, LEGEND_W)]
  for i, n in enumerate(notes):
    body.append(K.text(20, H0 - 44 + 16 * i, n, "t2"))
  H0 += 16 * len(notes)
  ly = H0 - 18

  # legend: state roles, then the edge styles and badges in use
  lx = 20
  for r in lay["roles"]:
    body.append(f'<rect class="{f"k{r[0]}" if r[0] else "box"}" x="{lx}" y="{ly - 10}" width="22" height="14" rx="4"/>')
    body.append(K.text(lx + 28, ly + 1, r[1], "t2"))
    lx += 28 + len(r[1]) * K.CHAR_W + 22
  ly += 20
  leg = [("edge", "in the code"), ("edge todo", "not in the code (target state)")]
  lx = 20
  for cls, txt in leg:
    body += [f'<path class="{cls}" d="M{lx},{ly - 4} L{lx + 26},{ly - 4}"/>', K.text(lx + 32, ly, txt, "t2")]
    lx += 32 + len(txt) * K.CHAR_W + 22
  ly, lx = ly + 20, 20
  for kind, (slot, txt) in BADGE.items():
    if any(issue(t, sw) == kind for t in T):
      H0 += 20 if lx == 20 else 0
      body += [f'<rect class="k{slot}" x="{lx}" y="{ly - 11}" width="26" height="14" rx="7"/>',
               K.text(lx + 32, ly, {"gap": "no SWSR cited (checker S7)", "s5": "in the code, SWSR not met (checker S5)"}[kind], "t2")]
      lx += 32 + 40 * K.CHAR_W

  # header
  scope = f" ({build} build)" if build else ""
  others = [t["id"] for t in sm["transitions"] if t not in T]
  head = [K.text(20, 26, f"{name}: {sm['title']}{scope}", "th"),
          K.text(20, 44, f"Stateflow-style chart generated from state-machines/{record} by diagrams/make_diagrams.py."
                 + (f" Only the other build: {', '.join(others)} (not drawn)." if others else ""), "ts"),
          K.text(20, 58, "Solid grey: in the code. Dashed orange: not in the code. Fill: state role (legend). "
                 "Status: WP-W-02 Baseline of the cited SWSRs.", "ts")]

  # transition table
  y = H0 + 32
  rows = [K.text(20, y, "Transitions (Stateflow label notation: event [guard] / {action})", "tb")]
  y += 10
  col = (20, 70, 620, 690)
  rows.append(f'<line class="grid" x1="20" y1="{y + 4}" x2="{20 + LEGEND_W}" y2="{y + 4}"/>')
  y += 18
  for c, hdr in zip(col, ("ID", "Transition", "Build", "WP-W-02 status")):
    rows.append(K.text(c, y, hdr, "t2"))
  y += 6
  for t in T:
    guard = f" [{t['guard']}]" if t.get("guard") else ""
    act = t.get("action") or "none"
    lab = f"{t['from']} → {t['to']}: {t['event']}{guard} / {{{act}}}"
    lines = K.wrap(lab, col[2] - col[1] - 14)
    st = csm.LABEL[csm.transition_state(t, sw)]
    if t.get("code", "").startswith("not implemented"):
      st += " (not in code)"
    rows.append(f'<line class="grid" x1="20" y1="{y + 4}" x2="{20 + LEGEND_W}" y2="{y + 4}"/>')
    if "not in code" in st:  # same orange as the dashed edge
      rows.append(f'<rect class="k2" style="stroke:none" x="20" y="{y + 5}" width="{LEGEND_W}" '
                  f'height="{14 * len(lines) + 2}"/>')
    y += 17
    rows.append(K.text(col[0], y, t["id"], "tb"))
    for i, ln in enumerate(lines):
      rows.append(K.text(col[1], y + 14 * i, ln, "t"))
    rows.append(K.text(col[2], y, t.get("build", "all"), "t2"))
    rows.append(K.text(col[3], y, st, "t2"))
    y += 14 * (len(lines) - 1) + 3
  H = int(y + 24)
  desc = (f"Stateflow-style chart of {name}{scope} with {len(states)} states and {len(T)} transitions, "
          f"generated from {record}; the table below the chart lists every transition."
          + (f" Unreachable in this build: {', '.join(dead)}." if dead else ""))
  return K.doc(W, H, f"{name} state chart{scope}", desc, head + body + rows)


# ------------------------------------------------------------------ Simulink-style block diagram

# id: (x, y, w, h, title, subtitle, kind)   kind: in | out | block | ref (reference build only) | chart
BLOCKS = {
  "IN1": (24, 109, 100, 30, "CAN RX bus 0", "", "in"),
  "RXC": (175, 88, 200, 72, "RX checks", "UN-02: ID/bus/DLC match, checksum, quality flag, time stamp", "block"),
  "HOOK": (440, 88, 210, 72, "toyota_rx_hook", "UN-14: CRUISE_ACTIVE, GAS_RELEASED, BRAKE_PRESSED, wheel speeds, MAIN_ON*", "block"),
  "GEN": (440, 190, 210, 60, "generic_rx_checks", "UN-01 (3): brake rising, or pressed while moving", "block"),
  "TICK": (440, 280, 210, 60, "safety_tick (100 Hz)", "UN-05, UN-37: RX timeout, invalid check; TX arrival*", "block"),
  "HB": (440, 370, 210, 60, "Heartbeat monitor", "panda main.c (UN-N1): SoC heartbeat lost > 0.3 s", "block"),
  "MODE": (440, 455, 210, 60, "set_safety_hooks", "UN-07: safety-mode change resets all state", "block"),
  "CHART": (800, 52, 190, 480, "SM-TOY-AUTH", "Stateflow chart (§5.2): controls_allowed", "chart"),
  "IN2": (24, 578, 100, 30, "SoC TX (SPI)", "", "in"),
  "TXW": (175, 563, 200, 60, "TX whitelist", "UN-03: (addr, bus, DLC) allowed", "block"),
  "RATE": (440, 563, 210, 60, "tx_rate_check*", "UN-36: per-ID budget in a 250 ms window", "ref"),
  "LIM": (800, 563, 210, 60, "toyota_tx_hook", "UN-15: torque and accel limits; needs authority", "block"),
  "OUT1": (1060, 578, 100, 30, "CAN TX bus 0", "", "out"),
}
# polyline points, label (x, y, anchor)
LINES = [
  ([(124, 124), (175, 124)], ("frame", 150, 118, "middle")),
  ([(375, 124), (440, 124)], ("valid", 420, 118, "middle")),
  ([(400, 124), (400, 310), (440, 310)], ("time stamps", 396, 300, "end")),
  ([(390, 124), (390, 70), (800, 70)], ("invalid frame: T4 (clear)", 595, 64, "middle")),
  ([(650, 124), (800, 124)], ("cruise edge, MAIN_ON*", 731, 118, "middle")),
  ([(668, 124), (668, 175), (425, 175), (425, 220), (440, 220)], ("brake, moving", 546, 169, "middle")),
  ([(650, 220), (800, 220)], ("brake: T3", 725, 214, "middle")),
  ([(650, 310), (800, 310)], ("T5, T10b*", 725, 304, "middle")),
  ([(650, 400), (800, 400)], ("T6a*, T10a", 725, 394, "middle")),
  ([(650, 485), (800, 485)], ("reset: T7", 725, 479, "middle")),
  ([(124, 593), (175, 593)], ("frame", 150, 587, "middle")),
  ([(375, 593), (440, 593)], ("allowed", 407, 587, "middle")),
  ([(650, 593), (684, 593), (684, 608), (800, 608)], ("within budget", 742, 622, "middle")),
  ([(700, 593), (700, 515), (800, 515)], ("excess: T11", 706, 509, "start")),
  ([(990, 292), (1028, 292), (1028, 548), (780, 548), (780, 578), (800, 578)], ("controls_allowed", 904, 542, "middle")),
  ([(1010, 593), (1060, 593)], ("accepted", 1035, 587, "middle")),
]
BRANCHES = [(400, 124), (390, 124), (668, 124), (700, 593)]


# block kind: (palette slot or None, legend text). Simulink-like colouring by role; the shape and glyph carry the kind too
KIND = {"in": (3, "input port"), "out": (2, "output port"), "block": (1, "function"), "ref": (None, "reference build only"),
        "chart": (7, "Stateflow chart"), "store": (4, "Data Store Memory"), "subsys": (6, "subsystem")}


def render_blocks(spec: dict) -> str:
  """Simulink-style block diagram from a spec: blocks, groups (interrupt contexts / areas), lines, branch points."""
  W, H = spec["size"]
  H += 24  # legend row
  body = [K.text(20, 26, spec["title"], "th")]
  for i, ln in enumerate(spec["sub"]):
    body.append(K.text(20, 44 + 14 * i, ln, "ts"))
  body.append(K.text(20, H - 14, spec["foot"], "ts"))
  lx, ly = 20, H - 36
  body.append(K.text(lx, ly, "Block colour:", "t2"))
  lx += 86
  used = {b[6] for b in spec["blocks"].values()}
  for kind, (slot, lab) in KIND.items():
    if kind in used:
      dash = ' stroke-dasharray="5 3"' if kind == "ref" else ""
      body.append(f'<rect class="{f"k{slot}" if slot else "box"}" x="{lx}" y="{ly - 10}" width="22" height="14" '
                  f'rx="{7 if kind in ("in", "out") else 0}"{dash}/>')
      body.append(K.text(lx + 28, ly + 1, lab, "t2"))
      lx += 28 + len(lab) * K.CHAR_W + 22
  for (x, y, w, h, title) in spec.get("groups", []):
    body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="edge target"/>')
    body.append(K.text(x + 10, y + 15, title, "t2"))
  lines_svg = []
  for line in spec["lines"]:
    pts, lab = line[0], line[1]
    style = line[2] if len(line) > 2 else "edge"
    d = "M" + " L".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    lines_svg.append(f'<path class="{style}" d="{d}"/>')
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    lines_svg.append(K.arrowhead(x1, y1, x1 - x0, y1 - y0, "arrow target" if "target" in style else "arrow"))
    if lab:
      t, lx, ly, anchor = lab
      lines_svg.append(K.text(lx, ly, t, "tm", anchor))
  for bx, by in spec.get("branches", []):
    lines_svg.append(f'<circle class="dot" cx="{bx}" cy="{by}" r="3"/>')
  blocks_svg = []
  for bid, (x, y, w, h, title, sub, kind) in spec["blocks"].items():
    fill = f"k{KIND[kind][0]}" if KIND[kind][0] else "box"
    if kind in ("in", "out"):
      blocks_svg.append(f'<rect class="{fill}" x="{x}" y="{y}" width="{w}" height="{h}" rx="14"/>')
      for i, ln in enumerate(K.wrap(title, w - 12)):
        blocks_svg.append(K.text(x + w / 2, y + h / 2 + 4 - 7 * (len(K.wrap(title, w - 12)) - 1) + 14 * i, ln, "t",
                                 "middle"))
      continue
    dash = ' stroke-dasharray="5 3"' if kind == "ref" else ""
    blocks_svg.append(f'<rect class="shadow" x="{x + 3}" y="{y + 3}" width="{w}" height="{h}"/>')
    blocks_svg.append(f'<rect class="{fill}" x="{x}" y="{y}" width="{w}" height="{h}"{dash}/>')
    if kind == "store":  # Simulink Data Store Memory: double top rule
      blocks_svg.append(f'<path class="edge" d="M{x},{y + 6} L{x + w},{y + 6}"/>')
    if kind == "subsys":  # subsystem: small inner frame glyph
      blocks_svg.append(f'<rect class="edge" x="{x + w - 22}" y="{y + h - 16}" width="14" height="10"/>')
    ty = y + h / 2 - 8 if kind in ("chart", "store") else y + 18
    blocks_svg.append(K.text(x + w / 2, ty, title, "tb", "middle"))
    for i, ln in enumerate(K.wrap(sub, w - 16)):
      blocks_svg.append(K.text(x + w / 2, ty + 16 + 13 * i, ln, "ts", "middle"))
    if kind == "chart":  # small Stateflow glyph
      gx, gy = x + w / 2 - 34, ty + 16 + 13 * len(K.wrap(sub, w - 16)) + 8
      blocks_svg += [f'<rect class="box" x="{gx}" y="{gy}" width="26" height="16" rx="5"/>',
                     f'<rect class="box" x="{gx + 42}" y="{gy}" width="26" height="16" rx="5"/>',
                     f'<path class="edge" d="M{gx + 26},{gy + 8} L{gx + 42},{gy + 8}"/>',
                     K.arrowhead(gx + 42, gy + 8, 1, 0, size=5)]
  return K.doc(W, H, spec["name"], spec["desc"], body + lines_svg + blocks_svg)


ENVELOPE = {
  "name": "Safety envelope block diagram", "size": (1180, 660),
  "title": "Safety envelope signal flow (reference build)",
  "sub": ["Simulink-style block diagram generated by diagrams/make_diagrams.py; blocks cite the WP-W-05 units at the "
          "WP-W-05 baseline. * reference build only (LIONDRIVER_REFERENCE=1)."],
  "foot": "Design description, not verified. The authority chart is WP-W-05 §5.2 (stateflow-sm-toy-auth.svg); "
          "transition IDs on the lines refer to it.",
  "blocks": BLOCKS, "lines": LINES, "branches": BRANCHES,
  "desc": ("Block diagram: CAN RX frames pass the RX checks and the Toyota RX hook; decoded signals, the 100 Hz safety "
           "tick, the heartbeat monitor and mode changes drive the authority chart; SoC TX frames pass the whitelist, "
           "the rate check and the Toyota TX limits, which also need controls_allowed, before CAN TX."),
}

# panda firmware (WP-W-03 §3.1, §3.2, §5.1), grouped by interrupt context
PANDA = {
  "name": "Panda firmware block diagram", "size": (1290, 830),
  "title": "Panda firmware: components by execution context (panda 8aa8671, opendbc 7993399)",
  "sub": ["Simulink-style block diagram generated by diagrams/make_diagrams.py from WP-W-03 §3.1, §3.2 and §5.1. "
          "Dashed frames: interrupt contexts (all at NVIC level 8, run to completion).",
          "Dashed blocks: reference build only. Thin dashed lines: writes (W) and reads (R) of the shared authority "
          "flag controls_allowed (Data Store Memory)."],
  "foot": "Design description, not verified. All envelope processing runs in interrupt context; the main loop only "
          "marks progress for the hardware watchdog (WP-W-03 §5.1).",
  "groups": [
    (150, 82, 970, 250, "DMA2 Stream2 IRQ: SPI RX done (U-PND-SPI → U-PND-COMMS)"),
    (150, 350, 970, 250, "FDCAN IRQs: RX (IT0) and TX (IT1)"),
    (150, 618, 470, 92, "TIM4 safety task, 100 Hz"),
    (640, 618, 480, 92, "TIM12 tick, 8 Hz (every 8th: 1 Hz)"),
    (150, 724, 470, 66, "Thread mode: main loop"),
  ],
  "blocks": {
    "SOCIN": (20, 140, 110, 44, "SoC SPI4 transfers", "", "in"),
    "SPI": (170, 132, 170, 60, "spi_rx_done", "header and data XOR, DMA", "block"),
    "CTRL": (390, 112, 180, 60, "comms_control_handler", "control requests (main_comms.h)", "block"),
    "LOCK": (610, 112, 190, 60, "reference_request_allowed", "refuses other requests, counts them", "ref"),
    "MODE": (850, 100, 250, 50, "0xdc set_safety_mode", "critical section → set_safety_hooks", "block"),
    "HBR": (850, 162, 250, 46, "0xf3 heartbeat", "counters, heartbeat_monitor_reset", "block"),
    "RELAY": (850, 220, 250, 46, "0xc5 relay (U-PND-HARN)", "set_intercept_relay, starts IWDG", "block"),
    "CANW": (390, 252, 180, 60, "comms_can_write", "→ can_send (U-PND-FDCAN)", "block"),
    "TXH": (610, 238, 220, 84, "safety_tx_hook", "whitelist → tx_rate_check* → toyota_tx_hook (EPS gate*) → lateral / longitudinal limits", "block"),
    "QUE": (870, 372, 230, 60, "can_queues → process_can", "packet XOR check, FDCAN TX FIFO", "block"),
    "BUSOUT": (1160, 380, 110, 44, "CAN TX bus 0 (car)", "", "out"),
    "BUSIN": (20, 460, 110, 44, "CAN RX bus 0 and 2", "", "in"),
    "CANRX": (170, 452, 170, 60, "can_rx", "per received frame", "block"),
    "FWD": (390, 382, 180, 56, "safety_fwd_hook", "bus 0 ↔ 2, static block of TX IDs", "block"),
    "RXH": (390, 462, 180, 56, "safety_rx_hook", "RX checks, generic edges", "block"),
    "TOY": (610, 452, 220, 66, "toyota_rx_hook", "decode; EPS fault*, cruise-main*; grant gated by RX checks", "block"),
    "RXQ": (390, 538, 180, 52, "can_push(rx_q)", "→ comms_can_read", "block"),
    "SOCOUT": (1160, 545, 110, 44, "SPI to SoC (CAN stream, health)", "", "out"),
    "STORE": (1160, 230, 110, 70, "controls_allowed", "U-SAF-CORE", "store"),
    "TASK": (170, 645, 430, 52, "safety_task_handler", "safety_tick (RX timeout) · heartbeat monitor (0.3 s → revoke) · IWDG feed", "block"),
    "TICK": (660, 645, 440, 52, "tick_handler", "harness, software watchdog, siren; 1 Hz: heartbeat counter → SILENT, engaged mismatch, check_registers", "block"),
    "LOOP": (170, 748, 430, 34, "hw_watchdog_main_loop_alive, LED fade / WFI", "", "block"),
  },
  "lines": [
    ([(130, 162), (170, 162)], None),
    ([(340, 152), (365, 152), (365, 142), (390, 142)], ("ctrl", 352, 136, "middle")),
    ([(570, 142), (610, 142)], None),
    ([(800, 142), (838, 142), (838, 125), (850, 125)], None),
    ([(838, 142), (838, 185), (850, 185)], None),
    ([(838, 185), (838, 243), (850, 243)], None),
    ([(365, 152), (365, 282), (390, 282)], ("can write", 360, 230, "end")),
    ([(570, 282), (610, 282)], None),
    ([(830, 270), (850, 270), (850, 402), (870, 402)], ("accept", 855, 340, "start")),
    ([(1100, 402), (1160, 402)], None),
    ([(130, 482), (170, 482)], None),
    ([(340, 482), (365, 482), (365, 410), (390, 410)], None),
    ([(570, 410), (590, 410), (590, 392), (870, 392)], ("forward: can_send, hook skipped", 730, 386, "middle")),
    ([(365, 482), (365, 490), (390, 490)], None),
    ([(570, 490), (610, 490)], None),
    ([(365, 490), (365, 564), (390, 564)], None),
    ([(570, 564), (1160, 564)], ("received frames to the SoC", 860, 558, "middle")),
    ([(830, 300), (845, 300), (845, 580), (1140, 580), (1140, 570), (1160, 570)], ("reject: rejected = 1 echo", 990, 594, "middle")),
    ([(1100, 125), (1130, 125), (1130, 245), (1160, 245)], ("W reset", 1135, 160, "start"), "edge thin target"),
    ([(830, 300), (1120, 300), (1120, 260), (1160, 260)], ("W* T11, R", 1000, 294, "middle"), "edge thin target"),
    ([(830, 470), (1150, 470), (1150, 285), (1160, 285)], ("W grant / clear", 1000, 464, "middle"), "edge thin target"),
    ([(600, 671), (625, 671), (625, 612), (1215, 612), (1215, 300)], ("W clear: T5, T10a", 1060, 627, "middle"), "edge thin target"),
    ([(1100, 671), (1240, 671), (1240, 300)], ("W clear: T6", 1180, 665, "middle"), "edge thin target"),
  ],
  "branches": [(365, 152), (838, 142), (838, 185), (365, 482), (365, 490), (830, 300)],
  "desc": ("Panda firmware by execution context: the SPI DMA interrupt handles control requests (mode set, heartbeat, "
           "relay) and SoC CAN frames through the TX hook; the FDCAN interrupts forward frames, run the RX hook and "
           "transmit; the 100 Hz safety task and the 8 Hz tick supervise; the main loop only marks progress. "
           "controls_allowed is shown as a data store with its writers."),
}

# host data flow per control frame (WP-W-03 §4.1, §4.2), superproject 682f184
HOST = {
  "name": "Host engagement data flow", "size": (1420, 540),
  "title": "Host engagement and control data flow (openpilot, superproject 682f184)",
  "sub": ["Simulink-style block diagram generated by diagrams/make_diagrams.py from WP-W-03 §4.1 and §4.2 (rates "
          "from cereal/services.py). Host processes are QM / QM (B-sup); authority on the car is the panda envelope."],
  "foot": "Design description, not verified. Freshness limits at the baseline are in WP-W-03 §4.2; targets in §10.",
  "blocks": {
    "MODELD": (40, 92, 170, 56, "modeld", "driving model (SOTIF / PAS 8800)", "block"),
    "PLANNERD": (340, 92, 170, 56, "plannerd", "longitudinal plan", "block"),
    "CONTROLSD": (600, 190, 180, 70, "controlsd", "lateral and longitudinal control law", "block"),
    "SELFDRIVED": (600, 330, 180, 120, "selfdrived", "Stateflow chart (WP-W-05 §5.3)", "chart"),
    "CARD": (920, 190, 180, 70, "card", "CAN parse → carState; carControl → sendcan", "block"),
    "PANDAD": (920, 330, 180, 76, "pandad", "SPI link, heartbeat, safety-mode set", "block"),
    "PANDA": (1220, 310, 180, 116, "panda safety envelope", "SPI in: CAN frames, 0xf3 heartbeat, 0xdc mode. Subsystem: simulink-envelope.svg, simulink-panda-firmware.svg", "subsys"),
  },
  "lines": [
    ([(210, 120), (340, 120)], ("modelV2 20 Hz", 296, 114, "middle")),
    ([(250, 120), (250, 212), (600, 212)], ("modelV2", 430, 206, "middle")),
    ([(230, 120), (230, 360), (600, 360)], ("modelV2", 430, 354, "middle")),
    ([(510, 120), (560, 120), (560, 230), (600, 230)], ("longitudinalPlan 20 Hz", 516, 112, "start")),
    ([(780, 225), (920, 225)], ("carControl 100 Hz", 850, 219, "middle")),
    ([(1100, 210), (1130, 210), (1130, 168), (580, 168), (580, 246), (600, 246)], ("carState 100 Hz", 855, 162, "middle")),
    ([(1130, 210), (1140, 210), (1140, 300), (575, 300), (575, 380), (600, 380)], ("carState", 855, 294, "middle")),
    ([(780, 380), (810, 380), (810, 285), (565, 285), (565, 254), (600, 254)], ("selfdriveState 100 Hz", 690, 279, "middle")),
    ([(810, 380), (830, 380), (830, 350), (920, 350)], ("selfdriveState", 875, 366, "middle")),
    ([(1100, 240), (1115, 240), (1115, 318), (900, 318), (900, 340), (920, 340)], ("sendcan 100 Hz", 1010, 312, "middle")),
    ([(1100, 350), (1220, 350)], ("SPI", 1160, 344, "middle")),
    ([(1400, 395), (1410, 395), (1410, 470), (905, 470), (905, 385), (920, 385)], ("health 10 Hz", 1160, 464, "middle")),
    ([(1100, 395), (1120, 395), (1120, 490), (570, 490), (570, 430), (600, 430)], ("pandaStates 10 Hz", 845, 484, "middle")),
  ],
  "branches": [(250, 120), (230, 120), (1130, 210), (810, 380)],
  "desc": ("Host data flow: modeld feeds plannerd, controlsd and selfdrived; card publishes carState and turns "
           "carControl into sendcan; selfdrived publishes selfdriveState to controlsd and pandad; pandad talks to the "
           "panda over SPI and returns pandaStates to selfdrived."),
}


# ------------------------------------------------------------------ system view: how the three machines couple

# lanes: (machine or None, title, subtitle); boxes: (lane, machine state or None, label, sub, x, w, role slot)
SYSTEM = {
  "lanes": [("SM-SELFDRIVED", "SM-SELFDRIVED", "host, QM"), (None, "heartbeat", "pandad → panda, 10 Hz"),
            ("SM-SAFETY-MODE", "SM-SAFETY-MODE", "panda"), ("SM-TOY-AUTH", "SM-TOY-AUTH", "envelope, ASIL C")],
  "boxes": {"dis": (0, "disabled", "disabled", "", 210, 140, None), "en": (0, "enabled", "enabled", "", 420, 140, 1),
            "hb": (1, None, "engaged flag = 1", "0xf3 heartbeat", 420, 170, None),
            "toy": (2, "TOYOTA", "TOYOTA, p = 73", "reference build: the only car mode", 210, 210, 1),
            "na": (3, "NOT_ALLOWED", "NOT_ALLOWED", "", 210, 140, None),
            "ep": (3, "ENGAGE_PENDING", "ENGAGE_PENDING", "window ≤ 1 s", 470, 170, 4),
            "al": (3, "ALLOWED", "ALLOWED", "controls_allowed = 1", 760, 170, 1)},
  # (from, to, label, kind): transition = a transition of one machine; flow = information passed between them
  "links": [("dis", "en", "D3", "transition"), ("na", "ep", "T1a cruise 0→1", "transition"),
            ("ep", "al", "T1b", "transition"), ("en", "hb", "sends engaged", "flow"),
            ("hb", "ep", "engaged flag", "flow"), ("toy", "na", "car mode required", "flow"),
            ("al", "en", "controlsAllowed in pandaState", "flow")],
}
LANE_H, LANE_GAP, LANE_TOP = 78, 12, 70


def system_view(sms: dict) -> str:
  W = 1000
  body = [K.text(20, 26, "State machines at engagement: how they couple (reference build)", "th"),
          K.text(20, 44, "Generated by diagrams/make_diagrams.py; every state named here is checked against the "
                 "state-machine records. Only the states and signals that link the machines are drawn.", "ts"),
          K.text(20, 58, "Solid: a transition of one machine (its chart and table are normative). Dashed: information "
                 "passed between machines, not a transition.", "ts")]
  lane_y = [LANE_TOP + i * (LANE_H + LANE_GAP) for i in range(len(SYSTEM["lanes"]))]
  for (m, title, sub), y in zip(SYSTEM["lanes"], lane_y):
    body.append(f'<rect class="hi" x="20" y="{y}" width="{W - 40}" height="{LANE_H}" rx="10"/>')
    body += [K.text(34, y + 34, title, "tb"), K.text(34, y + 50, sub, "t2")]
  geo = {}
  for k, (lane, st, lab, sub, x, w, slot) in SYSTEM["boxes"].items():
    m = SYSTEM["lanes"][lane][0]
    if st and st not in sms[m]["states"]:
      raise SystemExit(f"system view: {m} has no state {st}")
    y = lane_y[lane] + 14
    geo[k] = (x, y, w, LANE_H - 28)
  for a, b, lab, kind in SYSTEM["links"]:
    ax, ay, aw, ah = geo[a]
    bx, by, bw, bh = geo[b]
    cls = "edge" if kind == "transition" else "edge target"
    if ay == by:  # same lane: left to right
      p0, p1 = (ax + aw, ay + ah / 2), (bx, by + bh / 2)
      pts = [p0, p1]
      lx, ly, anchor = (p0[0] + p1[0]) / 2, p0[1] - 6, "middle"
    elif a == "al":  # back up to the host: right side, then left into the target
      pts = [(ax + aw / 2, ay), (ax + aw / 2, by + bh / 2), (bx + bw, by + bh / 2)]
      lx, ly, anchor = ax + aw / 2 - 8, lane_y[1] + 30, "end"
    else:
      sx = min(max(bx + bw / 2, ax + 10), ax + aw - 10)
      pts = [(sx, ay + ah), (sx, by)] if abs(sx - (bx + bw / 2)) < 1 else [(ax + aw / 2, ay + ah), (bx + bw / 2, by)]
      lx, ly, anchor = pts[0][0] + 8, (pts[0][1] + pts[-1][1]) / 2 + 4, "start"
    body.append(f'<path class="{cls}" d="M' + " L".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts) + '"/>')
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    body.append(K.arrowhead(x1, y1, x1 - x0, y1 - y0, "arrow" if kind == "transition" else "arrow target"))
    body += label(lx, ly, [lab]) if anchor == "middle" else [K.text(lx, ly, lab, "tm", anchor)]
  for k, (x, y, w, h) in geo.items():
    slot = SYSTEM["boxes"][k][6]
    body.append(f'<rect class="{f"k{slot}" if slot else "box"}" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>')
    body.append(K.text(x + 10, y + 20, SYSTEM["boxes"][k][2], "tb"))
    if SYSTEM["boxes"][k][3]:
      body.append(K.text(x + 10, y + 36, SYSTEM["boxes"][k][3], "t2"))

  # timeline: order of events at a normal engagement; illustrative spacing, except the window length
  y0 = lane_y[-1] + LANE_H + 46
  body += [K.text(20, y0, "Engagement over time (illustrative spacing; the order follows the code)", "tb"),
           K.text(20, y0 + 16, "Real recorded traces are the back-to-back scope plots (reference-models/results/scope/).", "ts")]
  rows = [("cruise (car PCM)", [(0, 0), (1, 1)]), ("selfdrived enabled", [(0, 0), (2, 1)]),
          ("heartbeat engaged", [(0, 0), (3, 1)]), ("window open", [(0, 0), (1, 1), (3, 0)]),
          ("controls_allowed", [(0, 0), (3, 1)])]
  xs = {0: 200, 1: 330, 2: 400, 3: 520}
  x_end, top = W - 40, y0 + 40
  for i, (name, steps) in enumerate(rows):
    hi, lo = top + i * 38, top + i * 38 + 22
    body.append(K.text(34, lo - 4, name, "t"))
    d, v = f"M{xs[0]},{lo}", 0
    for k, nv in steps[1:]:
      d += f" L{xs[k]},{hi if v else lo} L{xs[k]},{hi if nv else lo}"
      v = nv
    d += f" L{x_end},{hi if v else lo}"
    body.append(f'<path class="s{1 if i != 3 else 2}" d="{d}"/>')
  ev = [(1, "cruise rising edge: guards pass, window opens (T1a)"), (2, "selfdrived enables (D3)"),
        (3, "heartbeat engaged: grant in the safety task (T1b), window closes")]
  bottom = top + len(rows) * 38
  for n, (k, lab) in enumerate(ev, 1):
    body.append(f'<path class="grid" d="M{xs[k]},{top - 12} L{xs[k]},{bottom}" stroke-dasharray="3 3"/>')
    body.append(f'<circle class="dot" cx="{xs[k]}" cy="{top - 18}" r="8"/>')
    body.append(K.text(xs[k], top - 14, str(n), "ts", "middle").replace('class="ts"', 'class="ts" style="fill:var(--surface)"'))
    body.append(K.text(34, bottom + 8 + 16 * n, f"{n}  {lab}", "t2"))
  body.append(K.text(34, bottom + 8 + 16 * (len(ev) + 1), "The window lasts at most 1 s (PCM_ENGAGE_WINDOW_US); "
                     "about 0.21 s from edge to grant in the worst case of change-2026-10-14-pcm-engage-heartbeat-gate §2.", "t2"))
  H = int(bottom + 8 + 16 * (len(ev) + 1) + 24)
  desc = ("Coupling of the engagement state machines: selfdrived enabling sends the heartbeat engaged flag, which the "
          "panda's engagement window waits for before it grants controls_allowed in the Toyota car mode; the panda "
          "reports controlsAllowed back to selfdrived. A timeline below shows the order of events at engagement.")
  return K.doc(W, H, "State machine coupling at engagement", desc, body)


# ------------------------------------------------------------------ landing page of the state-machines folder

SECTION = {"SM-SAFETY-MODE": "5.1", "SM-TOY-AUTH": "5.2", "SM-SELFDRIVED": "5.3"}


def sm_readme(records: list[tuple[str, dict]], sw: dict) -> str:
  """state-machines/README.md: one row per record with counts computed from it, and its charts."""
  out = ["# State machines", "",
         "<!-- Generated by assurance/05-software/diagrams/make_diagrams.py; do not edit by hand. -->", "",
         "| Field | Value |", "|---|---|",
         "| Status | Draft — AI-assisted (Claude), not reviewed. The records are normative; the tables in "
         "[WP-W-05 §5](../WP-W-05-software-unit-design.md#5-normative-state-tables) and the charts are generated from them |",
         "| Checker | [`check_state_machines.py`](../../trace/tools/check_state_machines.py) (consistency, tables; "
         "findings S1–S7) |",
         "| Charts | [`diagrams/make_diagrams.py`](../diagrams/make_diagrams.py) ([notation](../diagrams/README.md)) |", "",
         "Each YAML file here is one state machine: its states, and every transition with its event, guard, action, "
         "build, the SWSRs it realises and the code that implements it. The implementation status is not stored "
         "here; it comes from the WP-W-02 Baseline column of the cited SWSRs.", "",
         "| Machine | Runs in | States | Transitions | Not in the code | No SWSR (S7) | In the code, SWSR not met (S5) "
         "| Builds | Table | Chart |",
         "|---|---|---|---|---|---|---|---|---|---|"]
  charts = []
  for stem, sm in records:
    T = sm["transitions"]
    builds = {t.get("build", "all") for t in T}
    names = LAYOUT[sm["machine"]].get("builds")
    files = [f"stateflow-{stem}-{b}.svg" for b in names] if names else [f"stateflow-{stem}.svg"]
    ids = lambda kind: [t["id"] for t in T if issue(t, sw) == kind]
    cell = lambda xs: f"{len(xs)}: {', '.join(xs)}" if xs else "0"
    todo = [t["id"] for t in T if t.get("code", "").startswith("not implemented")]
    out.append(f"| [{sm['machine']}]({stem}.yaml): {sm['title']} | {', '.join(sm['units'])} | {len(sm['states'])} "
               f"| {len(T)} | {cell(todo)} | {cell(ids('gap'))} | {cell(ids('s5'))} | {', '.join(sorted(builds))} "
               f"| [WP-W-05 §{SECTION[sm['machine']]}](../WP-W-05-software-unit-design.md) | "
               + ", ".join(f"[{f.removeprefix('stateflow-').removesuffix('.svg')}](../diagrams/{f})" for f in files) + " |")
    charts += [f"### {sm['machine']}: {sm['title']}", ""] + [f"![{sm['machine']} state chart: {sm['title']}{f', {b} build' if b else ''}](../diagrams/{f})"
                                                       for f, b in zip(files, names or [""])] + [""]
  out += ["", "How the three machines couple at engagement (WP-W-05 §5.4):", "",
          "![State machine coupling at engagement](../diagrams/stateflow-system-engagement.svg)", "", "## Charts", ""]
  out += charts
  out += ["## Changing a record", "",
          "Edit the YAML, then run `python3 assurance/trace/tools/check_state_machines.py --write` (WP-W-05 tables) and "
          "`python3 assurance/05-software/diagrams/make_diagrams.py` (charts and this page). A new state needs a "
          "position in `LAYOUT` in `make_diagrams.py`, a new revocation of SM-TOY-AUTH a group in its panel; the "
          "generator stops until it has one. The SysML model holds the records too: run "
          "`python3 tools/gen_behaviour.py` and `python3 tools/render_views.py` in `assurance/models/sysml` (view V-16). "
          "CI runs all of them with `--check`.", ""]
  return "\n".join(out)


# ------------------------------------------------------------------ main

def outputs() -> dict[str, str]:
  sw = csm.swsr_records()
  out = {}
  out["../state-machines/README.md"] = sm_readme([(p.stem, csm.load(p)) for p in sorted(csm.SM_DIR.glob("*.yaml"))], sw)
  for p in sorted(csm.SM_DIR.glob("*.yaml")):
    sm = csm.load(p)
    builds = LAYOUT[sm["machine"]].get("builds")
    for b in builds or [None]:
      out[f"stateflow-{p.stem}{'-' + b if b else ''}.svg"] = stateflow(sm, sw, p.name, b)
  out["stateflow-system-engagement.svg"] = system_view({sm["machine"]: sm for sm in
                                                       (csm.load(p) for p in sorted(csm.SM_DIR.glob("*.yaml")))})
  out["simulink-envelope.svg"] = render_blocks(ENVELOPE)
  out["simulink-panda-firmware.svg"] = render_blocks(PANDA)
  out["simulink-host.svg"] = render_blocks(HOST)
  return out


def main(argv: list[str]) -> int:
  stale = []
  for name, content in outputs().items():
    path = (HERE / name).resolve()
    if "--check" in argv:
      if not path.exists() or path.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      path.write_text(content, encoding="utf-8")
      print(f"wrote {path.relative_to(HERE.parents[2])}")
  if stale:
    print("FAIL: out of date: " + ", ".join(stale) + "; run assurance/05-software/diagrams/make_diagrams.py")
    return 1
  if "--check" in argv:
    print("OK: diagrams current")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
