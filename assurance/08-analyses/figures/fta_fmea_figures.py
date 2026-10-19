#!/usr/bin/env python3
"""Draw the FTA → FMEA hand-off figures of fta-fmea-mapping.md from WP-A-04, fta-fmea-map.yaml and the FMEAs.

The fault trees run down from a safety goal to basic events; the FMEAs run up from a cause to a vehicle effect. They
meet at the basic event, which is the top of an FMEA failure mode. Three kinds of figure show that hand-off:

- `fig-map-1-ladders.svg`: the two analyses as two ladders on shared levels (vehicle, system, element, cause), one real
  chain from a goal's top event down to a basic event and from that event's FMEA cause up to the goal's hazard. The
  rungs are where fmea_lint.py checks that the two agree. The chain is chosen in CHAIN; everything on it is read.
- `fig-map-2-trees.svg`: every goal's tree drawn small, in its real shape. Each basic event is a dot coloured by its
  FMEA backing, with a stalk below for the number of FMEA causes behind it.
- `fig-map-3-<goal>-<n>.svg`: per goal, one row per event of its tree (events borrowed through transfers included),
  grouped under the gate it feeds: the event, its FMEA failure mode, the worst of its causes with O, D and AP, and the
  detection that cause credits. The first sheet opens with the goal's single points (from the tree logic, as
  fta_diagrams.single_point_nodes) and the detection range of their FMEA causes.

Nothing is written into the analyses. The events reached, their counts and the single points are computed as
tools/safety/fmea_lint.py computes them (the test compares the two). The build fails if a mapped FMEA failure mode is
not in any FMEA, a goal in scope has no tree, or the CHAIN event, its gate or its goal's hazard is not found. Long
texts are cut with "…" and given in full in each figure's text description.

    python3 assurance/08-analyses/figures/fta_fmea_figures.py            # regenerate
    python3 assurance/08-analyses/figures/fta_fmea_figures.py --check    # fail if an SVG is stale

backlinks() is also used by tools/safety/fmea_cards.py for the "In the fault trees" strip of each System FMEA card.
Standard library only (YAML through fmea_diagrams' loader). Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in ("assurance/08-analyses/fta", "tools/safety", "assurance/02-concept/hara"):
  sys.path.insert(0, str(ROOT / p))
import fmea_diagrams as fmd  # noqa: E402  the FMEA's stdlib YAML loader
import fta_diagrams as ftd  # noqa: E402  the tree parser of WP-A-04
from hara_figures import HAIR, INK, MUTED, header, pill, svg_doc, t, text_w, wrap  # noqa: E402

MAP = ROOT / "assurance" / "08-analyses" / "fta-fmea-map.yaml"
HARA_MAP = fmd.FMEA_DIR / "hara-mapping.yaml"
OUT = HERE
W, M = 1344, 40
ANALYSIS = {"sw-fmea": "SW FMEA", "system-fmea": "System FMEA", "dfmea": "DFMEA", "pfmea": "PFMEA"}
CHAIN = ("SG-04", "BE-4.03")  # the worked chain of Figure 1: a goal and one of its basic events with an FMEA row
RED, GREY, GREEN, BLUE, BLUE_BG, ORG, ORG_BG = "#DC2626", "#94A3B8", "#16A34A", "#2563EB", "#EFF6FF", "#C2410C", "#FFF7ED"
AP_C = {"H": RED, "M": "#D97706", "L": "#0F766E"}
AP_RANK = {"H": 3, "M": 2, "L": 1}
SHEET_H = 1560  # body height of a hand-off sheet before it continues on the next
ROW_H, GROUP_H = 62, 40
DEFS = ('<marker id="ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0 0L10 5L0 10z" fill="#2563EB"/></marker>'
        '<marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0 0L10 5L0 10z" fill="#C2410C"/></marker>'
        '<marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
        '<path d="M0 0L10 5L0 10z" fill="#475569"/></marker>')


class FigureError(Exception):
  pass


# ---------------------------------------------------------------- data (as tools/safety/fmea_lint.py)

GOAL_ROW = re.compile(r"^\| \*\*(SG-\d{2})\*\* \|[^|]*\|[^|]*\|([^|]*)\|")
HE_RANGE = re.compile(r"HE-(\d{2})\.(\d+)(?:\s*[–-]\s*(\d{2})\.(\d+))?")


def goal_events(text: str) -> dict[str, set[str]]:
  """Hazardous events each WP-C-03 goal covers (fmea_lint.goal_events)."""
  out: dict[str, set[str]] = {}
  for line in text.splitlines():
    m = GOAL_ROW.match(line)
    if not m:
      continue
    evs = out.setdefault(m.group(1), set())
    for h, a, h2, b in HE_RANGE.findall(m.group(2)):
      if h2 and h2 != h:
        continue
      evs.update(f"HE-{h}.{i}" for i in range(int(a), int(b or a) + 1))
  return out


def reach(tree):
  """Leaf events (first node per id) and gate ids reachable from the top event, through transfers (fmea_lint.fta_reach)."""
  leaves: dict[str, object] = {}
  gates: set[str] = set()

  def visit(n):
    if n.kind == "transfer_in":
      gates.add(n.ident)
      visit(n.ref_of)
      return
    if n.children:
      if n.ident:
        gates.add(n.ident)
      for c in n.children:
        visit(c)
    elif n.ident:
      leaves.setdefault(n.ident, n)

  visit(tree.root)
  return list(leaves.values()), gates


def rows_of(tree):
  """The leaves of reach() in the same order, each with the gate it feeds and the path of gates above it."""
  out: dict[str, dict] = {}

  def visit(n, path, borrowed):
    if n.kind == "transfer_in":
      src = n.ref_tree or tree.goal
      grp = borrowed or (n.ident, f"from {src}" if src != tree.goal else "developed elsewhere in this tree",
                         tuple(p.ident for p in path))
      visit(n.ref_of, path, grp)
    elif n.children:
      for c in n.children:
        visit(c, path if borrowed else path + (n,), borrowed)
    elif n.ident and n.ident not in out:
      parent = path[-1]
      grp = borrowed or (parent.ident, f"{parent.gate} gate" if parent.gate else "", tuple(p.ident for p in path[:-1]))
      out[n.ident] = dict(node=n, group=grp)

  visit(tree.root, (), None)
  return list(out.values())


class Data:
  def __init__(self, map_doc=None, analyses=None):
    trees = ftd.parse_document(ftd.SOURCE.read_text(encoding="utf-8"))
    ftd.resolve(trees)
    self.trees = {t_.goal: t_ for t_ in trees}
    doc = map_doc if map_doc is not None else fmd.load_yaml(MAP.read_text(encoding="utf-8"))
    self.scope = doc["scope"]
    self.events = {e["id"]: e for e in doc.get("events", [])}
    self.gates = {g["id"]: g for g in doc.get("gates", [])}
    self.not_in_fta = doc.get("not_in_fta", [])
    self.fms: dict[str, tuple[str, dict]] = {}
    for name, d in (analyses if analyses is not None else fmd.load_analyses()).items():
      for f in d.get("failure_modes") or []:
        self.fms[f["id"]] = (ANALYSIS.get(name, name), f)
    for row in list(self.events.values()) + list(self.gates.values()):
      for f in row.get("fmea") or []:
        if f not in self.fms:
          raise FigureError(f"{row['id']}: FMEA failure mode {f} is in fta-fmea-map.yaml but in no FMEA")
    hm = fmd.load_yaml(HARA_MAP.read_text(encoding="utf-8"))
    sg = goal_events((ROOT / hm["target"]).read_text(encoding="utf-8"))
    self.hz_h = {h["second"]: h.get("wp_c03") or [] for h in hm["hazards"]}
    self.goal_hz = {g: {h["second"] for h in hm["hazards"] if set(h["events"]) & sg.get(g, set())} for g in self.scope}
    self.goals = {}
    for g in self.scope:
      if g not in self.trees:
        raise FigureError(f"scope goal {g} has no fault tree in WP-A-04")
      self.goals[g] = self.summary(g)

  def summary(self, goal):
    tree = self.trees[goal]
    leaves, gate_ids = reach(tree)
    ids = [n.ident for n in leaves]
    mapped = [self.events[e] for e in ids if e in self.events]
    hot = ftd.single_point_nodes(tree)
    cited = {f for e in ids if e in self.events for f in self.events[e].get("fmea") or []}
    cited |= {f for g in gate_ids if g in self.gates for f in self.gates[g].get("fmea") or []}
    relevant = {fid for fid, (_, f) in self.fms.items() if {x.get("hazard") for x in f["effects"]} & self.goal_hz[goal]}
    rows = [r for r in self.not_in_fta if r["goal"] == goal]
    backed = lambda e: bool(e.get("fmea") or e.get("fmeda"))
    return dict(
      tree=tree, hot=hot, rows=rows_of(tree), gate_ids=gate_ids,
      spf=[n.ident for n in leaves if id(n) in hot and n.ident in self.events],
      events=len(ids), backed=sum(backed(e) for e in mapped),
      by_design=sum(e.get("class") == "by_design" for e in mapped), external=sum(e.get("class") == "external" for e in mapped),
      unbacked=sum(e.get("class") not in ("by_design", "external") and not backed(e) for e in mapped),
      modes=len(relevant), in_tree=len(relevant & cited), justified=sum(r["kind"] == "justified" for r in rows),
      tree_gaps=sum(r["kind"] == "tree_gap" for r in rows))

  def causes(self, fids):
    return [c for f in fids for c in self.fms[f][1].get("causes") or []]

  def worst(self, fids):
    cs = self.causes(fids)
    return max(cs, key=lambda c: (AP_RANK.get(c.get("ap"), 0), c.get("detection") or 0, c.get("occurrence") or 0)) if cs else None


def report_line(goal, s) -> str:
  """The goal's line of `fmea_lint.py --report`, from this module's counts (the test compares the two)."""
  return (f"FTA-FMEA map {goal}: {s['events']} events (backed {s['backed']}, by design {s['by_design']}, external "
          f"{s['external']}, unbacked {s['unbacked']}); {s['modes']} FMEA modes reach {goal} (in the tree {s['in_tree']}, "
          f"justified {s['justified']}, tree gaps {s['tree_gaps']})")


def backlinks(data: Data | None = None) -> dict[str, list[tuple[str, list[tuple[str, bool]], str | None]]]:
  """FMEA failure mode -> [(goal, [(event or gate id, single point)], not-in-tree kind or None)] for every goal in scope."""
  data = data or Data()
  out: dict[str, list] = {}
  for g in data.scope:
    s = data.goals[g]
    hot_ids = set(s["spf"])
    per: dict[str, list] = {}
    for r in s["rows"]:
      for f in data.events.get(r["node"].ident, {}).get("fmea") or []:
        per.setdefault(f, []).append((r["node"].ident, r["node"].ident in hot_ids))
    for gid in sorted(s["gate_ids"] & set(data.gates), key=_id_key):
      for f in data.gates[gid].get("fmea") or []:
        per.setdefault(f, []).append((gid, False))
    for f, ids in per.items():
      out.setdefault(f, []).append((g, ids, None))
    for r in data.not_in_fta:
      if r["goal"] == g:
        out.setdefault(r["fm"], []).append((g, [], r["kind"]))
  return out


def _id_key(ident):
  return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", ident)]


def short(s, n):
  s = re.sub(r"\s+", " ", str(s)).strip()
  return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + " …"


def cut(text, width, size, n, bold=False):
  ls_ = wrap(text, width, size, bold)
  return ls_[:n - 1] + [ls_[n - 1] + " …"] if len(ls_) > n else ls_


def fade(i, n=6):
  k = i % n
  return (f'<animate attributeName="opacity" values="0.2;0.2;1;1" keyTimes="0;{0.08 + 0.12 * k:.2f};{0.14 + 0.12 * k:.2f};1" '
          f'dur="6s" repeatCount="indefinite"/>')


def box(x, y, w, h, title, lines, stroke, fill="#FFFFFF", dash=None):
  da = f' stroke-dasharray="{dash}"' if dash else ""
  b = [f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.4"{da}/>',
       t(x + 10, y + 18, title, 11, stroke, 700)]
  b += [t(x + 10, y + 33 + 12.5 * i, ln, 10, INK) for i, ln in enumerate(lines)]
  return b


def dchips(x, y, c, size=9):
  out = []
  d = c["detection"]
  for lab, fill, fg in ((f"O {c['occurrence']}", "#F1F5F9", "#334155"),
                        (f"D {d}", "#FEE2E2" if d >= 7 else "#DCFCE7" if d <= 4 else "#F1F5F9",
                         RED if d >= 7 else "#14532D" if d <= 4 else "#334155"),
                        (f"AP {c['ap']}", AP_C.get(c["ap"], GREY), "#FFFFFF")):
    s, w = pill(x, y, lab, fill, fg, 16, size)
    out.append(s)
    x += w + 5
  return out


# ---------------------------------------------------------------- Figure 1: two ladders

def find(n, ident, path=()):
  if n.ident == ident and n.ref_of is None:
    return n, path
  for c in n.children:
    r = find(c, ident, path + (n,))
    if r:
      return r
  return None


def ladders(data: Data) -> str:
  goal, ev = CHAIN
  tree = data.trees[goal]
  hit = find(tree.root, ev)
  if not hit:
    raise FigureError(f"CHAIN: {ev} is not in the {goal} tree")
  node, path = hit
  fids = data.events.get(ev, {}).get("fmea") or []
  if not fids or not path:
    raise FigureError(f"CHAIN: {ev} has no FMEA row or no gate above it")
  gate, top = path[-1], tree.root
  src, fm = data.fms[fids[0]]
  nh = [e for e in fm["effects"] if e["level"] == "next_higher"]
  end = [e for e in fm["effects"] if e["level"] == "end" and e.get("hazard") in data.goal_hz[goal]]
  if not nh or not end:
    raise FigureError(f"CHAIN: {fids[0]} has no next-higher effect or no end effect on a {goal} hazard")
  cause = data.worst(fids)
  hz = end[0]["hazard"]
  hot = id(node) in data.goals[goal]["hot"]
  b = header(W, "How the fault trees and the FMEAs meet",
             "The tree climbs down from the goal, the FMEA climbs up from the cause. The rungs are where fmea_lint.py checks "
             "that they agree.", "fta-fmea-map.yaml · ISO 26262-9 §8", "Figure 1")
  levels = [("Vehicle", "the hazard"), ("System", "how faults combine"), ("Element", "where they meet"), ("Cause", "why it fails")]
  y0, rh, lx, rx, bw = 116, 118, 210, 900, 320
  for i, (lv, sub) in enumerate(levels):
    y = y0 + i * rh
    b.append(f'<rect x="{M}" y="{y - 10}" width="{W - 2 * M}" height="{rh - 12}" rx="10" fill="{"#F8FAFC" if i % 2 == 0 else "#FFFFFF"}"/>')
    b.append(t(M + 16, y + 22, lv, 13, INK, 700))
    b.append(t(M + 16, y + 40, sub, 10.5, MUTED))
  left = [(f"{top.ident} top event · {goal}", top.text), (f"{gate.ident} {gate.gate or ''} gate".replace("  ", " "), gate.text),
          (f"{ev} basic event" + (" · single point" if hot else ""), node.text)]
  right = [(f"End effect · {hz} → {', '.join(data.hz_h.get(hz, []))}", end[0]["description"]),
           ("Next-higher effect", nh[0]["description"]), (f"{fids[0]} failure mode · {src}", fm["failure_mode"]),
           (f"{cause['id']} · O {cause['occurrence']} · D {cause['detection']} · AP {cause['ap']}", cause["description"])]
  for i in range(4):
    y = y0 + i * rh
    if i < 3:
      st = RED if (i == 2 and hot) else BLUE
      b.append(f"<g>{fade(i, 8)}" + "".join(box(lx, y, bw, 70, left[i][0], cut(left[i][1], bw - 20, 10, 2), st, BLUE_BG)) + "</g>")
    b.append(f"<g>{fade(3 - i + 4, 8)}" + "".join(box(rx, y, bw, 70, right[i][0], cut(right[i][1], bw - 20, 10, 2), ORG, ORG_BG)) + "</g>")
  b.append(f'<path d="M{lx - 20} {y0 + 6} V{y0 + 2 * rh + 62}" stroke="{BLUE}" stroke-width="3" marker-end="url(#ab)"/>')
  b.append(t(lx - 28, y0 + 2 * rh + 92, "Fault tree: top down", 11, BLUE, 700, "end"))
  b.append(f'<path d="M{rx + bw + 20} {y0 + 3 * rh + 64} V{y0 + 6}" stroke="{ORG}" stroke-width="3" marker-end="url(#ao)"/>')
  b.append(t(rx + bw + 14, y0 + 3 * rh + 92, "FMEA: bottom up", 11, ORG, 700, "end"))
  rungs = [(0, f"checked: {hz} is a hazard of {goal}", True), (1, "optional: a gate may cite a System FMEA mode", False),
           (2, f"checked: {ev} is backed, {fids[0]} is in the tree", True)]
  for i, lab, solid in rungs:
    y = y0 + i * rh + 35
    da = "" if solid else ' stroke-dasharray="5 4"'
    b.append(f'<line x1="{lx + bw}" y1="{y}" x2="{rx}" y2="{y}" stroke="#475569" stroke-width="{2.2 if solid else 1.2}"{da}/>')
    w = text_w(lab, 10, True) + 16
    b.append(f'<rect x="{(lx + bw + rx - w) / 2:g}" y="{y - 22}" width="{w:g}" height="16" fill="#FFFFFF"/>')
    b.append(t((lx + bw + rx) / 2, y - 10, lab, 10, "#334155", 700, "middle"))
  b.append(t(lx, y0 + 3 * rh + 40, "The tree stops at the basic event; the causes live only in the FMEA.", 10.5, MUTED))
  rows = [("Top event", "End effect: its hazard maps to the goal's hazardous events (hara-mapping.yaml)"),
          ("Gate", "System FMEA failure mode, optional (gates in the map)"),
          ("Basic event: software / SOTIF", "SW FMEA or System FMEA failure mode"),
          ("Basic event: hardware", "DFMEA failure mode or FMEDA row"), ("Basic event: installation", "PFMEA failure mode"),
          ("Undeveloped event, by design", "No FMEA: an assumption of use or a reason")]
  y = y0 + 4 * rh + 6
  b.append(t(M, y, "The same pairing for every event", 11.5, INK, 700))
  for i, (a, z) in enumerate(rows):
    yy = y + 22 + (i // 2) * 20
    x = M + (i % 2) * 640
    b.append(t(x, yy, a, 10.5, BLUE, 700))
    b.append(t(x + 200, yy, z, 10.5, INK))
  y += 22 + 3 * 20 + 8
  b.append(t(W - M, y, "Generated by fta_fmea_figures.py", 10, MUTED, None, "end"))
  desc = (f"Figure 1. The fault tree and the FMEA as two ladders on shared levels. Worked chain: {top.ident} ({top.text}) of "
          f"{goal}, gate {gate.ident} ({gate.text}), basic event {ev} ({node.text}){', a single point' if hot else ''}; FMEA "
          f"{fids[0]} ({fm['failure_mode']}), next-higher effect: {nh[0]['description']}; end effect on {hz}: "
          f"{end[0]['description']}; worst cause {cause['id']} ({cause['description']}; O {cause['occurrence']}, D "
          f"{cause['detection']}, AP {cause['ap']}). Pairing: " + "; ".join(f"{a}: {z}" for a, z in rows) + ".")
  return svg_doc(W, int(y + 22), "Figure 1. How the fault trees and the FMEAs meet", desc, b, DEFS)


# ---------------------------------------------------------------- Figure 2: the trees drawn small

def trees_fig(data: Data) -> str:
  b = header(W, "Every fault tree, and what backs its events",
             "Each goal's tree in its real shape. Each basic event is a dot coloured by its FMEA backing; the stalk below it "
             "is one tick per FMEA cause.", "WP-A-04 · fta-fmea-map.yaml", "Figure 2")
  cw, ch, gx = 300, 300, 16
  desc = []
  for k, g in enumerate(data.scope):
    s = data.goals[g]
    tree = s["tree"]
    ox, oy = M + (k % 4) * (cw + gx), 110 + (k // 4) * (ch + 20)
    b.append(f'<rect x="{ox}" y="{oy}" width="{cw}" height="{ch}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>')
    b.append(t(ox + 12, oy + 22, g, 12.5, INK, 700))
    b.append(t(ox + 60, oy + 22, cut(tree.title, cw - 76, 10, 1)[0], 10, MUTED))
    leaves, edges = [], []

    def walk(n, d, seen):
      m = n.ref_of if n.kind == "transfer_in" and n.ref_of is not None and id(n.ref_of) not in seen else n
      if not (m.children and d < 12):
        leaves.append((n, d))
        return len(leaves) - 1, d
      kids = [walk(c, d + 1, seen | {id(m)}) for c in m.children]
      edges.append((d, kids, id(n) in s["hot"]))
      return sum(i for i, _ in kids) / len(kids), d

    walk(tree.root, 0, frozenset())
    nl, maxd = len(leaves), max(d for _, d in leaves)
    px = lambda i: ox + 16 + (cw - 32) * ((i + 0.5) / nl)
    py = lambda d: oy + 44 + (150 / max(1, maxd)) * d
    for d, kids, h in edges:
      xm = sum(px(i) for i, _ in kids) / len(kids)
      for i, kd in kids:
        b.append(f'<path d="M{xm:.1f} {py(d):.1f} L{px(i):.1f} {py(kd):.1f}" stroke="{"#FCA5A5" if h else "#CBD5E1"}" stroke-width="1"/>')
    base = oy + 194
    seen_ids, gaps = set(), []
    for i, (n, d) in enumerate(leaves):
      x = px(i)
      if n.ident in seen_ids:
        b.append(f'<circle cx="{x:.1f}" cy="{base}" r="2.6" fill="#FFFFFF" stroke="{GREY}" stroke-width="1"/>')
        continue
      seen_ids.add(n.ident)
      e = data.events.get(n.ident, {})
      backed = bool(e.get("fmea") or e.get("fmeda"))
      col = GREEN if backed else GREY if e.get("class") in ("by_design", "external") else RED
      if col == RED:
        gaps.append(n.ident)
      b.append(f'<line x1="{x:.1f}" y1="{py(d):.1f}" x2="{x:.1f}" y2="{base}" stroke="#E2E8F0" stroke-dasharray="2 2"/>')
      b.append(f'<circle cx="{x:.1f}" cy="{base}" r="3.6" fill="{col}"/>')
      nc = len(data.causes(e.get("fmea") or []))
      if nc:
        y2 = base + 5 + 5 * min(nc, 12)
        b.append(f'<line x1="{x:.1f}" y1="{base + 5}" x2="{x:.1f}" y2="{y2}" stroke="{ORG}" stroke-width="2">'
                 f'<animate attributeName="y2" values="{base + 5};{y2};{y2}" keyTimes="0;0.5;1" dur="6s" repeatCount="indefinite"/></line>')
    b.append(f'<line x1="{ox + 12}" y1="{base}" x2="{ox + cw - 12}" y2="{base}" stroke="{GREY}" stroke-width="0.8"/>')
    if len(seen_ids) != s["events"]:
      raise FigureError(f"{g}: drew {len(seen_ids)} events, the map reaches {s['events']}")
    msg = f"{s['events']} events · " + (f"{len(gaps)} without FMEA: {', '.join(gaps)}" if gaps else "all backed or reasoned")
    b.append(t(ox + 12, oy + ch - 12, cut(msg, cw - 24, 10, 1)[0], 10, RED if gaps else MUTED, 700 if gaps else None))
    desc.append(f"{g} ({tree.title}): {msg}; {s['modes']} FMEA modes reach it, {s['in_tree']} in the tree, "
                f"{s['justified']} justified, {s['tree_gaps']} tree gaps.")
  ly = 110 + 2 * (ch + 20) + 4
  x = M
  for lab, col, ring in (("FMEA or FMEDA row", GREEN, None), ("by design or external", GREY, None), ("no FMEA yet", RED, None),
                         ("stalk: FMEA causes, one tick each (up to 12)", ORG, None), ("event repeated", "#FFFFFF", GREY)):
    b.append(f'<circle cx="{x + 5}" cy="{ly}" r="4" fill="{col}" stroke="{ring or col}"/>')
    b.append(t(x + 14, ly + 4, lab, 10.5, MUTED))
    x += text_w(lab, 10.5) + 40
  b.append(t(M, ly + 24, "Leaves include events borrowed from other trees through transfers. Red edges are single-point paths, "
             "from the gate logic. Counts are those of fmea_lint.py --report.", 10.5, MUTED))
  b.append(t(W - M, ly + 44, "Generated by fta_fmea_figures.py", 10, MUTED, None, "end"))
  return svg_doc(W, ly + 60, "Figure 2. Every fault tree, and what backs its events", "Figure 2. " + " ".join(desc), b, DEFS)


# ---------------------------------------------------------------- Figure 3: hand-off sheets per goal

def sp_panel(data: Data, g, y):
  s = data.goals[g]
  b = [t(M, y + 14, "Single points: one event in the item reaches the top event (events outside the item assumed)", 12, RED, 700)]
  y += 26
  if not s["spf"]:
    b.append(t(M, y + 14, "None in this tree: every path to the top event needs two or more item events.", 10.5, MUTED))
    return b, 34 + 26, []
  tw = (W - 2 * M - 3 * 12) / 4
  desc = []
  for i, ev in enumerate(s["spf"]):
    x, yy = M + (i % 4) * (tw + 12), y + (i // 4) * 70
    e = data.events[ev]
    fids = e.get("fmea") or []
    ds = [c["detection"] for c in data.causes(fids)]
    b.append(f'<rect x="{x:g}" y="{yy}" width="{tw:g}" height="60" rx="8" fill="#FFFFFF" stroke="{RED}" stroke-width="1.6"/>')
    b.append(t(x + 10, yy + 18, ev, 11, RED, 700))
    if ds:
      lo, hi = min(ds), max(ds)
      lab, fill, fg = (("every cause D ≤ 4: tree and FMEA disagree", RED, "#FFFFFF") if hi <= 4 else
                       ("not detected", "#FEE2E2", RED) if lo >= 7 else ("partly detected", "#FEF3C7", "#92400E"))
      rng = f"D {lo}" + (f"–{hi}" if hi != lo else "")
      b.append(t(x + 10, yy + 34, cut(f"{', '.join(fids)} · {len(ds)} cause{'s' if len(ds) > 1 else ''} · {rng}", tw - 20, 10, 1, True)[0], 10, ORG, 700))
      b.append(pill(x + 10, yy + 40, lab, fill, fg, 15, 8.5)[0])
      desc.append(f"{ev}: {', '.join(fids)}, {len(ds)} causes, {rng}, {lab}")
    else:
      if e.get("fmeda"):
        why, lab, fill, fg = "FMEDA " + ", ".join(e["fmeda"]), "FMEDA rows, no FMEA cause", "#DCFCE7", "#14532D"
      else:
        why = e.get("gap") or e.get("reason") or e.get("class", "")
        lab, fill, fg = ("no FMEA row yet", RED, "#FFFFFF") if e.get("gap") else ("no FMEA row needed", "#F1F5F9", "#334155")
      b.append(t(x + 10, yy + 34, cut(why, tw - 20, 10, 1)[0], 10, MUTED))
      b.append(pill(x + 10, yy + 40, lab, fill, fg, 15, 8.5)[0])
      desc.append(f"{ev}: {lab}; {why}")
  return b, 26 + ((len(s["spf"]) + 3) // 4) * 70 + 8, desc


def row(data: Data, r, y, i, hot):
  n = r["node"]
  e = data.events.get(n.ident, {})
  col = RED if hot else "#334155"
  sym = "◆" if n.kind == "undeveloped" or n.ident.startswith("UE-") else "●"
  b = [f'<rect x="{M}" y="{y}" width="310" height="54" rx="8" fill="#FFFFFF" stroke="{col}" stroke-width="{1.8 if hot else 1}"/>',
       t(M + 10, y + 17, f"{sym} {n.ident}" + ("  single point" if hot else ""), 10.5, col, 700)]
  b += [t(M + 10, y + 31 + 12 * k, ln, 9.5, INK) for k, ln in enumerate(cut(n.text, 290, 9.5, 2))]
  fids = e.get("fmea") or []
  g = [f"<g>{fade(i)}"]
  if fids:
    src, fm = data.fms[fids[0]]
    c = data.worst(fids)
    g.append(f'<path d="M{M + 312} {y + 27} H{M + 356}" stroke="{col}" stroke-width="1.6" marker-end="url(#ag)"/>')
    g.append(f'<rect x="{M + 360}" y="{y}" width="306" height="54" rx="8" fill="{ORG_BG}" stroke="{ORG}"/>')
    g.append(t(M + 370, y + 17, f"{fids[0]} · {src}" + (f"  + {len(fids) - 1} more" if len(fids) > 1 else ""), 10.5, ORG, 700))
    g += [t(M + 370, y + 31 + 12 * k, ln, 9.5, INK) for k, ln in enumerate(cut(fm["failure_mode"], 286, 9.5, 2))]
    if c:
      g += [t(M + 680, y + 14 + 12 * k, ln, 9.5, INK) for k, ln in enumerate(cut(f"{c['id']}: {c['description']}", 320, 9.5, 2))]
      g += dchips(M + 680, y + 36, c)
      det = (c.get("detection_controls") or [{}])[0].get("description", "none recorded")
      g += [t(M + 1020, y + 14 + 12 * k, ln, 9.5, MUTED) for k, ln in enumerate(cut(det, 244, 9.5, 3))]
      text = (f"{n.ident} ({n.text}) → {', '.join(fids)}: {fm['failure_mode']}; worst cause {c['id']} ({c['description']}; "
              f"O {c['occurrence']}, D {c['detection']}, AP {c['ap']}); detection: {det}")
    else:
      text = f"{n.ident} ({n.text}) → {', '.join(fids)}: {fm['failure_mode']}"
  else:
    if e.get("fmeda"):
      head, why, st, fill, dash = "FMEDA rows, no FMEA failure mode", ", ".join(e["fmeda"]), GREEN, "#F0FDF4", None
    elif e.get("gap") or e.get("class") not in ("by_design", "external", None):
      head, why, st, fill, dash = "No FMEA row yet", e.get("gap", "no gap statement"), RED, "#FEF2F2", "5 4"
    else:
      head = f"No FMEA row needed: {(e.get('class') or n.kind).replace('_', ' ')}"
      why, st, fill, dash = e.get("reason") or e.get("note") or e.get("ref") or "assumption of use", GREY, "#F8FAFC", "5 4"
    g.append(f'<rect x="{M + 360}" y="{y}" width="{W - 2 * M - 360}" height="54" rx="8" fill="{fill}" stroke="{st}" stroke-dasharray="{dash or 0}"/>')
    g.append(t(M + 370, y + 18, head, 10.5, st if st != GREY else MUTED, 700))
    g += [t(M + 370, y + 33 + 12 * k, ln, 9.5, MUTED) for k, ln in enumerate(cut(why, W - 2 * M - 380, 9.5, 2))]
    text = f"{n.ident} ({n.text}): {head}; {why}"
  return b + g + ["</g>"], text


def group_head(data: Data, g, grp, y, hot, cont):
  ident, what, crumbs = grp
  crumb = " › ".join(crumbs + (ident,)) if ident else g
  node = next((h for tr in [data.trees[g]] + list(data.trees.values()) if ident for h in [find(tr.root, ident)] if h), None)
  text = node[0].text if node else ""
  b = [f'<rect x="{M}" y="{y}" width="{W - 2 * M}" height="28" rx="6" fill="{"#FEF2F2" if hot else "#F1F5F9"}"/>',
       t(M + 12, y + 18, crumb + (f" ({what})" if what else ""), 10.5, RED if hot else "#334155", 700)]
  x = M + 24 + text_w(crumb + (f" ({what})" if what else ""), 10.5, True)
  rest = cut(text + (" (continued)" if cont else ""), W - M - x - 12, 10.5, 1)
  if rest:
    b.append(t(x, y + 18, rest[0], 10.5, INK))
  return b


def handoff(data: Data, g) -> dict[str, str]:
  s = data.goals[g]
  hot_nodes = s["hot"]
  groups: dict[tuple, list] = {}  # gate -> its events, in the order the tree first reaches the gate
  for r in s["rows"]:
    groups.setdefault(r["group"], []).append(r)
  items = list(groups.items())
  pages, cur, used = [], [], 0
  sp_b, sp_h, sp_desc = sp_panel(data, g, 108)
  cap = SHEET_H - sp_h
  for grp, rs in items:
    first = True
    for r in rs:
      need = ROW_H + (GROUP_H if first or not cur else 0)
      if cur and used + need > cap:
        pages.append(cur)
        cur, used, cap = [], 0, SHEET_H
        need = ROW_H + GROUP_H
      head = first or not cur or cur[-1][0] != grp
      cur.append((grp, r, head, not first and head))
      used += need if head else ROW_H
      first = False
  pages.append(cur)
  out = {}
  for k, page in enumerate(pages, 1):
    name = f"fig-map-3-{g.lower()}-{k}.svg"
    b = header(W, f"{g}: from the fault tree to the FMEA" + (f" ({k} of {len(pages)})" if len(pages) > 1 else ""),
               cut(data.trees[g].title[:1].upper() + data.trees[g].title[1:], 900, 12.5, 1)[0], "WP-A-04 · fta-fmea-map.yaml",
               f"Figure 3-{g}-{k}")
    y, desc = 100, []
    if k == 1:
      b += sp_b
      y += sp_h
      desc.append("Single points: " + ("; ".join(sp_desc) if sp_desc else "none") + ".")
    cols = [(M, "Event (fault tree)"), (M + 360, "FMEA failure mode it hands off to"), (M + 680, "Worst cause and its ratings"),
            (M + 1020, "Detection that cause credits")]
    b += [t(x, y + 14, lab, 10.5, MUTED, 700) for x, lab in cols]
    y += 22
    for i, (grp, r, head, cont) in enumerate(page):
      if head:
        gnode = find(data.trees[g].root, grp[0]) if grp[0] else None
        b += group_head(data, g, grp, y + 6, bool(gnode and id(gnode[0]) in hot_nodes), cont)
        y += GROUP_H
      rb, text = row(data, r, y, i, id(r["node"]) in hot_nodes)
      b += rb
      desc.append(text)
      y += ROW_H
    foot = report_line(g, s).replace(f"FTA-FMEA map {g}: ", f"{g}: ")
    b.append(t(M, y + 16, foot, 10.5, MUTED))
    b.append(t(M, y + 34, "Worst cause: highest AP, then highest D. Red: single-point path from the gate logic. Text cut with … is "
               "given in full in the figure description.", 10.5, MUTED))
    b.append(t(W - M, y + 52, "Generated by fta_fmea_figures.py", 10, MUTED, None, "end"))
    out[name] = svg_doc(W, int(y + 68), f"Figure 3-{g}-{k}. {g}: from the fault tree to the FMEA",
                        f"Figure 3-{g}-{k}. {foot}. " + " ".join(desc), b, DEFS)
  return out


def build(data: Data | None = None) -> dict[str, str]:
  data = data or Data()
  out = {"fig-map-1-ladders.svg": ladders(data), "fig-map-2-trees.svg": trees_fig(data)}
  for g in data.scope:
    out.update(handoff(data, g))
  return out


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    out = build()
  except (FigureError, ftd.FtaError, fmd.FigError) as e:
    print(f"fta_fmea_figures: {e}", file=sys.stderr)
    return 1
  old = {p.name for p in OUT.glob("fig-map-*.svg")}
  stale = sorted(n for n, svg in out.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != svg)
  extra = sorted(old - set(out))
  if check:
    if stale or extra:
      print("fta_fmea_figures: stale or extra figures; run assurance/08-analyses/figures/fta_fmea_figures.py: "
            + ", ".join(stale + extra), file=sys.stderr)
      return 1
    print(f"fta_fmea_figures: {len(out)} figures current")
    return 0
  for n in extra:
    (OUT / n).unlink()
  for n, svg in out.items():
    (OUT / n).write_text(svg, encoding="utf-8")
  print(f"fta_fmea_figures: {len(out)} figures written")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
