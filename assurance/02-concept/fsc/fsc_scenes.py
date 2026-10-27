#!/usr/bin/env python3
"""Draw the WP-C-04 FTTI scene sheets: one card per safety goal SG-01 … SG-08.

Three sheets in `figures/`: Figure 8-1 lateral (SG-01, SG-02, SG-05), Figure 8-2 longitudinal (SG-03, SG-04, SG-06) and
Figure 8-3 stock PCS and the driver (SG-07, SG-08). Each card shows:

- the goal's ASIL, safe state and preliminary FTTI (§3);
- the FTTI budget of one §8 row (detection + reaction inside the FTTI) against how long it takes today;
- a looping top-down road scene of what the safety mechanism must prevent (SMIL, 6 s; a still viewer shows the key
  moment);
- a timeline from the fault to the safe state and the warning: the §8 budget as "needed by", today as a dot, or hatched
  where it does not happen at all;
- what the safety mechanism must do against what it does today;
- which elements carry the FSRs that serve the goal (§9 trace, §5 Alloc), with a QM element that carries an ASIL FSR
  outlined in red, and how many of those FSRs are implemented, partial, not met or unverified (§5 Impl).

The goals, FSRs and trace come from `fsc_figures.parse` (passed in by `fsc_figures.build`, so this module never imports
it); the §8 budgets and the §5 implementation status are read here. The titles, scenes, "today" times and texts below
are drawings that explain each goal: schematic, not measurements. Every "today" time quotes the §8 "Current behaviour"
text it is taken from (`src`). The build fails if a §3 goal has no card, a card names a §8 row that is not there, a quoted
text is no longer in its row, its timeline asks for a budget the row does not give, or a card cites an ID (GAP-, FSR-,
TSR-, DQ-, AOU-) that WP-C-04 does not contain.

The road scenes and text helpers are shared with the STPA scene cards (`assurance/08-analyses/figures/stpa_scenes.py`).
Regenerate with `python3 fsc_figures.py`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "08-analyses" / "figures"))
import stpa_scenes as ss  # drawing helpers only; it never imports this module
from stpa_scenes import GRASS, INK, MUTED, PERF, REQ, RULE, M, P, T, wrap

W, H, GAP = 980, 730, 24
TEAL = "#0F766E"
K = None  # fsc_figures, passed in by build(): its FigureError and ELEMENTS
SHEETS = {
  "fig-c04-8-1-ftti-scenes-lateral.svg": ("8-1", "Lateral", "the lateral safety goals", ["SG-01", "SG-02", "SG-05"]),
  "fig-c04-8-2-ftti-scenes-longitudinal.svg": ("8-2", "Longitudinal", "the longitudinal safety goals", ["SG-03", "SG-04", "SG-06"]),
  "fig-c04-8-3-ftti-scenes-pcs-driver.svg": ("8-3", "Stock PCS and driver", "stock PCS and the driver", ["SG-07", "SG-08"]),
}
TILES = [
  ("E-03", "envelope", "ASIL C"),
  ("E-05", "harness", "ASIL C · B for PCS"),
  ("E-01", "SoC", "QM"),
  ("E-01/DM", "DM", "QM"),
  ("E-01/HMI", "HMI", "QM"),
  ("E-02", "models", "QM"),
  ("EXT", "Toyota", "assumed (AOU)"),
]
QM_TILES = {"E-01", "E-01/DM", "E-01/HMI", "E-02"}
STATUS = [("implemented", "#2F7D4F"), ("partial", "#C08A1E"), ("not met", "#B42318"), ("unverified", "#6B7480"), ("see §5", "#94A3B8")]


def fail(msg):
  raise K.FigureError(msg)


# ============================================================================ what this module reads itself
def _seconds(cell):
  """'≤ 0.3 s', '≤ 1 frame (10 ms)', '0 (per-frame check)', '—' -> seconds or None."""
  if cell.startswith("—"):
    return None
  m = re.search(r"(\d+(?:\.\d+)?)\s*(ms|s)\b", cell)
  if m:
    return float(m.group(1)) / (1000 if m.group(2) == "ms" else 1)
  return 0.0 if cell.startswith("0") else None


def budgets(md):
  sec = re.search(r"^## 8\. .*?(?=^## 9\. )", md, re.M | re.S)
  if not sec:
    fail("WP-C-04 §8 not found")
  out = {}
  for line in sec.group(0).splitlines():
    if line.startswith("| SG-"):
      c = [x.strip() for x in line.strip()[1:-1].split(" | ")]
      out[c[0]] = dict(ftti=_seconds(c[1]), det=_seconds(c[2]), react=_seconds(c[3]), today=c[4], gap=c[5])
  return out


def impl(md):
  """FSR -> implemented / partial / not met / unverified / other, from the Impl column of the §5 tables."""
  sec = re.search(r"^## 5\. .*?(?=^## 6\. )", md, re.M | re.S)
  if not sec:
    fail("WP-C-04 §5 not found")
  out = {}
  for line in sec.group(0).splitlines():
    c = [x.strip() for x in line.strip()[1:-1].split(" | ")]
    if line.startswith("| FSR-") and len(c) == 6:
      s = c[5].replace("*", "").strip().lower()
      out[c[0]] = next(
        (k for k, w in (("implemented", "implemented"), ("partial", "partial"), ("not met", "not"), ("unverified", "unverified")) if s.startswith(w)), "see §5"
      )
  return out


def tile_of(element):
  return "EXT" if element.startswith("EXT-") else element


# ============================================================================ card parts
def budget(b, row):
  sc, x0, w = row["scale"], 70, 316
  X = lambda t: x0 + min(t, sc) / sc * w
  o = [M(0, 10, f"FTTI BUDGET (§8) · {row['row']}".upper(), 11, MUTED), T(62, 34, "needed", 11, MUTED, anchor="end")]
  if b["det"] is None or b["react"] is None:
    o += [
      f'<rect x="{x0}" y="22" width="{X(b["ftti"]) - x0:.1f}" height="16" fill="#BBF7D0" stroke="{REQ}"/>',
      T(x0 + 4, 34, "within the FTTI (no split in §8)", 10, "#14532D"),
    ]
  else:
    o += [
      f'<rect x="{x0}" y="22" width="{max(X(b["det"]) - x0, 2):.1f}" height="16" fill="#BBF7D0" stroke="{REQ}"/>',
      f'<rect x="{X(b["det"]):.1f}" y="22" width="{max(X(b["det"] + b["react"]) - X(b["det"]), 2):.1f}" height="16" fill="#86EFAC" stroke="{REQ}"/>',
    ]
    if X(b["det"]) - x0 > 44:
      o.append(T(x0 + 4, 34, "detect", 10, "#14532D"))
    if X(b["det"] + b["react"]) - X(b["det"]) > 40:
      o.append(T(X(b["det"]) + 4, 34, "react", 10, "#14532D"))
  o += [
    f'<line x1="{X(b["ftti"]):.1f}" y1="20" x2="{X(b["ftti"]):.1f}" y2="70" stroke="{INK}" stroke-width="2"/>',
    T(X(b["ftti"]) + 5, 35, f"FTTI {ss._f(b['ftti'])} s", 11, INK, 700),
    T(62, 60, "today", 11, MUTED, anchor="end"),
  ]
  t = row["today"]
  o += [f'<rect x="{x0}" y="48" width="{X(t) - x0:.1f}" height="16" fill="#FDE4E1" stroke="{PERF}"/>', T(x0 + 4, 60, row["today_label"], 10.5, "#7F1D1D", 600)]
  if t > sc:
    o.append(f'<path d="M{x0 + w + 2} 46 l8 10 l-8 10" fill="none" stroke="{PERF}" stroke-width="2"/>')
  o += [T(X(v), 84, f"{ss._f(v)} s", 10, MUTED, anchor="middle") for v in row["ticks"]]
  return '<g transform="translate(564 24)">' + "".join(o) + "</g>"


def timeline(b, c):
  t1 = c["t1"]
  X = lambda t: 112 + min(t, t1) / t1 * 310
  need = {"fault": 0.0, "detect": b["det"], "react": None if b["det"] is None or b["react"] is None else b["det"] + b["react"], "ftti": b["ftti"]}
  o = [
    '<defs><pattern id="{id}hz" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#FFF5F4"/>'
    '<line x1="0" y1="0" x2="0" y2="8" stroke="#FCA5A5" stroke-width="2"/></pattern></defs>'
  ]
  for i, (name, kind, today, label) in enumerate(c["lanes"]):
    y = 34 + i * 44
    o += [T(10, y + 12, name, 12, INK, 600), f'<line x1="112" y1="{y + 8}" x2="422" y2="{y + 8}" stroke="{RULE}"/>']
    n = need[kind]
    if n is not None:
      o += [
        f'<line x1="{X(n):.1f}" y1="{y - 4}" x2="{X(n):.1f}" y2="{y + 20}" stroke="{REQ}" stroke-width="2" stroke-dasharray="4 3"/>',
        T(X(n) + 4, y - 2, f"by {ss._f(n)} s", 10, "#166534", 600),
      ]
    if today is None:
      o += [f'<rect x="112" y="{y + 2}" width="310" height="12" fill="url(#{{id}}hz)"/>', T(116, y + 26, label, 10.5, "#B42318", 600)]
    else:
      x = X(today)
      o += [
        f'<circle cx="{x:.1f}" cy="{y + 8}" r="6" fill="{PERF}"/>',
        T(x - 10, y + 26, label, 10.5, "#B42318", 600, "end") if x > 300 else T(x + 10, y + 12, label, 10.5, "#B42318", 600),
      ]
  o.append('<line x1="112" y1="214" x2="422" y2="214" stroke="#94A3B8"/>')
  o += [T(X(v), 228, f"{ss._f(v)} s", 10.5, MUTED, anchor="middle") for v in c["ticks"]]
  o.append(
    '<g transform="translate(14 242)">'
    + f'<line x1="0" y1="-4" x2="14" y2="-4" stroke="{REQ}" stroke-width="2" stroke-dasharray="4 3"/>'
    + T(20, 0, "needed by (§8)", 10.5, MUTED)
    + f'<circle cx="122" cy="-4" r="5" fill="{PERF}"/>'
    + T(132, 0, "today", 10.5, MUTED)
    + T(410, 0, "schematic timeline", 10.5, MUTED, anchor="end")
    + "</g>"
  )
  return o


def allocation(goal, fsrs, status):
  o = [M(0, 12, f"WHO CARRIES THE {len(fsrs)} FSRs SERVING {goal} (§9, §5 ALLOC)", 11, MUTED)]
  for i, (e, desc, cap) in enumerate(TILES):
    mine = [f for f in fsrs if any(tile_of(x) == e for x in f.elements)]
    hot = e in QM_TILES and any(f.asil in ("A", "B", "C", "D") for f in mine)
    x, y = (i % 4) * 106, 20 + (i // 4) * 58
    f, s = ("#FDE4E1", "#B42318") if hot else (("#E3F2E8", "#2F7D4F") if mine else ("#FFFFFF", RULE))
    o += [
      f'<rect x="{x}" y="{y}" width="100" height="50" rx="6" fill="{f}" stroke="{s}" stroke-width="{2 if hot else 1}"/>',
      T(x + 8, y + 16, e, 11.5 if len(e) > 5 else 12, INK, 700),
      T(x + 92, y + 31, f"{len(mine)} FSR" if mine else "—", 11, s if mine else MUTED, 600, "end"),
      T(x + 8, y + 31, desc, 10.5, MUTED),
      T(x + 8, y + 44, "QM, carries ASIL" if hot else cap, 10, "#B42318" if hot else MUTED, 600 if hot else 400),
    ]
  counts = [(name, col, sum(1 for f in fsrs if status.get(f.ident, "see §5") == name)) for name, col in STATUS]
  counts = [c for c in counts if c[2]]
  o.append(M(0, 152, f"{len(fsrs)} FSRs TODAY (§5 IMPL)", 11, MUTED))
  x = 0
  for name, col, v in counts:
    w = 420 * v / len(fsrs)
    o += [
      f'<rect x="{x:.1f}" y="160" width="{w:.1f}" height="22" fill="{col}"/>',
      T(x + w / 2, 175, f"{v} {name}" if w > 80 else str(v), 10.5, "#FFFFFF", 600, "middle"),
    ]
    x += w
  return '<g transform="translate(516 446)">' + "".join(o) + "</g>"


def card(goal, m, b, fsrs, status, x, y, n, md):
  ids = set(re.findall(r"\b(?:GAP|FSR|TSR|DQ|AOU)-[\w.]+\b", repr(m)))
  missing = sorted(i for i in ids if i.rstrip(".") not in md)
  if missing:
    fail(f"{goal.ident} card cites {', '.join(missing)}, which WP-C-04 does not contain")
  for name, kind, *_ in m["chart"]["lanes"]:
    if kind == "react" and (b["det"] is None or b["react"] is None):
      fail(f"{goal.ident} card: lane '{name}' needs a reaction budget, which §8 row '{m['budget']['row']}' does not give")
  if len(wrap(m["title"], 38)) > 2:
    fail(f"{goal.ident} card: title runs over two lines")
  cid = f"f{n}"
  asil = goal.asil_text.split(" (")[0]
  o = [
    f'<g transform="translate({x} {y})"><title>{escape(goal.ident)}: {escape(m["title"])}</title>',
    f'<rect width="{W}" height="{H}" rx="12" fill="#F6F7F8" stroke="{RULE}"/>',
    M(24, 36, f"{goal.ident} · ASIL {asil} · safe state: {m['safe']}".upper(), 12, TEAL),
  ]
  o += [T(24, 70 + 30 * i, line, 25, INK, 700) for i, line in enumerate(wrap(m["title"], 38))]
  o += [T(24, 132, f"{m['hazard']} · FTTI {goal.ftti.split(' (')[0]} · {len(fsrs)} FSRs serve it", 13, MUTED), budget(b, m["budget"])]
  sc = m["scene"]
  o += [
    M(24, 162, "WHAT THE SAFETY MECHANISM MUST PREVENT · SCHEMATIC, LOOPS EVERY 6 S", 11, MUTED),
    f'<svg x="24" y="170" width="470" height="255" viewBox="0 0 460 250"><rect width="460" height="250" rx="8" fill="{GRASS}"/>'
    + "".join(ss.SCENE[sc["kind"]](sc))
    + "</svg>",
    M(516, 162, "FAULT TO SAFE STATE · NEEDED AGAINST TODAY", 11, MUTED),
    f'<svg x="516" y="170" width="440" height="250" viewBox="0 0 440 250"><rect x="0.5" y="0.5" width="439" height="249" rx="8" fill="#FFFFFF" '
    f'stroke="{RULE}"/>' + "".join(timeline(b, m["chart"])).replace("{id}", cid) + "</svg>",
  ]
  q, tr = wrap(m["must"], 52), wrap(m["today"], 62)
  h1, h2 = 34 + 21 * len(q), 34 + 20 * len(tr)
  if h1 + 10 + h2 > 206:
    fail(f"{goal.ident} card: must and today text too long ({len(q)} + {len(tr)} lines)")
  o += [f'<rect x="24" y="446" width="470" height="{h1}" rx="8" fill="#E6F4F1" stroke="{TEAL}"/>', M(38, 466, "WHAT THE SAFETY MECHANISM MUST DO", 11, TEAL)]
  o += [T(38, 489 + 21 * i, line, 15.5, INK, 600) for i, line in enumerate(q)]
  y2 = 456 + h1
  o += [f'<rect x="24" y="{y2}" width="470" height="{h2}" rx="8" fill="#FFFFFF" stroke="{RULE}"/>', M(38, y2 + 20, "WHAT IT DOES TODAY", 11, MUTED)]
  o += [T(38, y2 + 42 + 20 * i, line, 14) for i, line in enumerate(tr)]
  o.append(allocation(goal.ident, fsrs, status))
  gaps = sorted(set(re.findall(r"GAP-\d+", b["gap"])), key=lambda g: int(g[4:]))
  chips = [(f"FTTI {goal.ftti.split(' (')[0]}", "teal")] + [(g, "red") for g in gaps] + [(c, None) for c in m.get("chips", ())]
  cx, cy = 24, 662
  for text, st in chips:
    w = ss.tw(text, 12.5) + 22
    if cx + w > W - 24:
      cx, cy = 24, cy + 32
    f, s = {"red": ("#FDE4E1", "#B42318"), "teal": ("#E6F4F1", TEAL), None: ("#FFFFFF", RULE)}[st]
    o += [
      f'<rect x="{cx:.0f}" y="{cy}" width="{w:.0f}" height="26" rx="13" fill="{f}" stroke="{s}"/>',
      T(cx + 11, cy + 17.5, text, 12.5, s if st else INK, 600 if st else 400),
    ]
    cx += w + 8
  if cy + 26 > H - 8:
    fail(f"{goal.ident} card: footer chips overflow the card")
  return "".join(o) + "</g>"


def sheet(name, goals, md, rows, status):
  num, short, who, ids = SHEETS[name]
  cards = []
  for i, gid in enumerate(ids):
    m = MODEL[gid]
    if m["budget"]["row"] not in rows:
      fail(f"{gid} card names §8 row '{m['budget']['row']}', which WP-C-04 §8 does not have")
    for row, text in m["budget"]["src"]:
      if row not in rows or text not in rows[row]["today"]:
        fail(f"{gid} card: '{text}' is no longer in the Current behaviour of §8 row '{row}'; update the card")
    fsrs = [f for g in goals.values() for f in g.fsrs if gid in f.serves]
    cards.append(card(goals[gid], m, rows[m["budget"]["row"]], fsrs, status, GAP + (i % 2) * (W + GAP), 120 + (i // 2) * (H + GAP), i, md))
  rws = (len(ids) + 1) // 2
  w, h = GAP + 2 * (W + GAP), 120 + rws * (H + GAP) + 30
  b = [
    f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>',
    T(GAP, 46, f"Figure {num}. FTTI scenes: {who}", 28, INK, 700),
    T(
      GAP,
      76,
      "Each card: the §8 FTTI budget against today; what the safety mechanism must prevent (schematic, loops every 6 s); the "
      "timeline from fault to safe state; what it must do and does today; who carries the FSRs and how many are met.",
      14,
      MUTED,
    ),
    T(
      GAP,
      98,
      "Goals, FSRs, trace, budgets and implementation status from WP-C-04 §3, §5, §8 and §9. The scenes and the times shown "
      "for today are schematic, not measurements.",
      14,
      MUTED,
    ),
  ] + cards
  b.append(
    T(
      GAP,
      h - 14,
      f"WP-C-04 Figure {num} · generated by fsc/fsc_scenes.py through fsc_figures.py; regenerate after any change to WP-C-04 §3, §5, §8 or §9.",
      12,
      MUTED,
    )
  )
  defs = (
    "<defs>"
    + "".join(
      f'<marker id="{i}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
      for i, c in (("ah-b", "#93C5FD"), ("ah-r", "#FCA5A5"))
    )
    + "</defs>"
  )
  title = f"Figure {num}. FTTI scenes: {who} (WP-C-04 §8)"
  desc = f"One card per safety goal, {who}: " + "; ".join(f"{g} {MODEL[g]['title']}" for g in ids) + "."
  return (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
    f'<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n{defs}\n' + "".join(b) + "\n</svg>\n"
  )


def build(goals_list, md, kit) -> dict[str, str]:
  """The scene sheets. goals_list is fsc_figures.parse(md); kit is the fsc_figures module (FigureError)."""
  global K
  K = kit
  goals = {g.ident: g for g in goals_list}
  on_sheets = [g for *_, ids in SHEETS.values() for g in ids]
  if sorted(on_sheets) != sorted(goals) or sorted(MODEL) != sorted(goals):
    fail(f"FTTI scene cards and WP-C-04 §3 differ: goals {sorted(goals)}, sheets {sorted(on_sheets)}, cards {sorted(MODEL)}")
  rows, status = budgets(md), impl(md)
  return {name: sheet(name, goals, md, rows, status) for name in SHEETS}


# ============================================================================ the cards
CURVE_DRIFT = dict(kind="curve", still=0.8, want=ss.CURVE, act=[(-10, 70), (100, 70), (190, 70), (250, 72), (310, 84), (360, 108), (400, 138), (430, 172)])
SWERVE = dict(
  kind="lat",
  still=0.62,
  want=[(20, 157), (440, 157)],
  act=[(20, 157), (180, 157), (240, 135), (300, 112), (360, 105), (440, 110)],
  actors=[dict(y=93, keys=[(0, 180), (0.92, 420)])],
)
STOPPED = dict(
  kind="lon",
  still=0.85,
  want=[(20, 157), (320, 157)],
  labels=[(180, 140, "where it should stop", "#BBF7D0")],
  actors=[dict(y=157, body=ss.sk.STOPPED, keys=[(0, 392)]), dict(y=157, body="#DC2626", keys=[(0, 20), (0.92, 345)])],
)

MODEL: dict[str, dict] = {
  "SG-01": dict(
    title="If the panda's own processor faults, steering must stop within 0.5 s",
    safe="torque 0, request cleared",
    hazard="H-01 unintended steering",
    budget=dict(
      row="SG-01 (MCU execution fault)",
      src=[("SG-01 (MCU execution fault)", "90 ms IWDG")],
      today=0.09,
      scale=0.6,
      ticks=[0, 0.2, 0.4, 0.6],
      today_label="90 ms watchdog, under review (DQ-114)",
    ),
    scene=dict(
      SWERVE,
      pills=P(
        (1, "Panda MCU hangs while steering", "bad", 0.15, 6),
        (2, "Watchdog resets it; envelope silent", "ok", 0.3, 28),
        (3, "Without it: a stuck command steers on", "bad", 0.6, 224),
      ),
    ),
    chart=dict(
      t1=0.6,
      ticks=[0, 0.2, 0.4, 0.6],
      lanes=[
        ("fault", "fault", 0.0, "MCU hangs"),
        ("detected", "detect", 0.09, "watchdog ≈ 90 ms"),
        ("safe state", "react", 0.09, "reset: no TX"),
        ("warning", "ftti", 0.5, "SoC alert ≤ 0.5 s"),
      ],
    ),
    must="Detect its own execution faults (hang, clock, memory) and go silent, with the relay released, within the FTTI.",
    today="The baseline had no hardware watchdog (GAP-07). A 90 ms watchdog is in all builds since panda 3859fa8 and counts once "
    "its independent review is done (DQ-114).",
    chips=["FSR-01.09", "DQ-114"],
  ),
  "SG-02": dict(
    title="If steering is lost, the driver must be warned within 1 s",
    safe="warning, torque ramp-down",
    hazard="H-02 silent loss of steering",
    budget=dict(
      row="SG-02, SG-06 (loss without warning)",
      src=[("SG-02, SG-06 (loss without warning)", "≈3.5 s")],
      today=3.5,
      scale=1.5,
      ticks=[0, 0.5, 1, 1.5],
      today_label="warns at once, actuates on stale inputs ≈ 3.5 s",
    ),
    scene=dict(
      CURVE_DRIFT,
      pills=P(
        (1, "Lateral control lost at the curve", "bad", 0.36, 150),
        (2, "Soft disable: alert, but stale actuation", "bad", 0.48, 174),
        (3, "≈ 0.7 s to 0.6 m drift in this curve", "bad", 0.68, 198),
      ),
    ),
    chart=dict(
      t1=4,
      ticks=[0, 1, 2, 3, 4],
      lanes=[
        ("fault", "fault", 0.0, "lateral control lost"),
        ("detected", "detect", 0.3, "soft disable raised"),
        ("warning", "ftti", 0.3, "alert at once"),
        ("safe state", "react", 3.5, "≈ 3.5 s on stale inputs"),
      ],
    ),
    must="Detect a loss of lateral control within 0.5 s, warn within 1 s, and stop acting on inputs it no longer trusts.",
    today="The soft disable warns at once but keeps actuating on stale inputs for up to about 3.5 s (GAP-16). In the ODD's tightest curve "
    "0.7 s already gives 0.6 m of drift (WP-S-04 §3.2).",
    chips=["DQ-059"],
  ),
  "SG-05": dict(
    title="When the driver steers against it, the torque must back off within 0.2 s",
    safe="disengaged",
    hazard="H-05 cannot override",
    budget=dict(
      row="SG-05 (steering override)",
      src=[("SG-05 (steering override)", "Not in envelope")],
      today=9,
      scale=0.4,
      ticks=[0, 0.1, 0.2, 0.3, 0.4],
      today_label="not in the envelope: never backs off",
    ),
    scene=dict(
      kind="lat",
      objects=[("debris", 306, 166)],
      want=[(20, 157), (170, 157), (230, 120), (330, 118), (440, 157)],
      act=[(20, 157), (170, 157), (255, 141), (300, 151), (440, 156)],
      arrows=("drv", "op"),
      still=0.6,
      labels=[(328, 112, "where the driver steers", "#BBF7D0"), (352, 150, "where the car goes", "#FECACA")],
      pills=P(
        (1, "Driver steers around debris", "drv", 0.28, 6),
        (2, "The envelope has no override check", "bad", 0.38, 28),
        (3, "Torque keeps fighting the driver", "bad", 0.6, 224),
      ),
    ),
    chart=dict(
      t1=0.5,
      ticks=[0, 0.1, 0.2, 0.3, 0.4, 0.5],
      lanes=[
        ("override", "fault", 0.0, "driver steers against"),
        ("detected", "ftti", None, "no driver-torque check in the envelope"),
        ("torque backs off", "ftti", None, "decided (DQ-053), not built"),
        ("cue shown", "ftti", None, "no cue today"),
      ],
    ),
    must="Detect the driver's steering override, ramp the torque toward zero for as long as it lasts, and show the driver it was noticed.",
    today="Brake and cancel are in the envelope; steering override is not, so the torque keeps coming (GAP-02). The back-off is decided (DQ-053), not built.",
    chips=["FSR-05.03", "DQ-053"],
  ),
  "SG-03": dict(
    title="If an input is lost or wrong, acceleration must stop within 1 s",
    safe="accel ≤ 0, ACC cancelled",
    hazard="H-03 unintended acceleration",
    budget=dict(
      row="SG-03, SG-04",
      src=[('SG-03, SG-04', 'as SG-01 detection'), ('SG-01 (RX loss/corruption)', '≤ 0.162 s')],
      today=0.162,
      scale=1.2,
      ticks=[0, 0.4, 0.8, 1.2],
      today_label="≤ 0.162 s, reference build, not verified",
    ),
    scene=dict(
      STOPPED,
      pills=P(
        (1, "An input the envelope gates on is lost", "bad", 0.15, 6),
        (2, "Acceleration still allowed", "bad", 0.3, 28),
        (3, "Closes on the stopped car", "bad", 0.6, 228),
      ),
    ),
    chart=dict(
      t1=1.2,
      ticks=[0, 0.4, 0.8, 1.2],
      lanes=[
        ("fault", "fault", 0.0, "input lost or corrupt"),
        ("detected", "detect", 0.162, "RX check ≤ 0.162 s"),
        ("safe state", "react", 0.162, "authority revoked"),
      ],
    ),
    must="Detect a lost, corrupt, repeated or stale input within 0.5 s and bring acceleration to zero within the 1 s FTTI.",
    today="Detection is as for SG-01. Since opendbc de80b63 the RX checks revoke within 0.162 s, not yet verified on hardware; the "
    "baseline took 1–2 s (GAP-06).",
    chips=["FSR-01.06"],
  ),
  "SG-04": dict(
    title="If an input is lost or wrong, hard braking must stop within 1 s",
    safe="inactive, bounded jerk",
    hazard="H-04 unintended braking",
    budget=dict(
      row="SG-03, SG-04",
      src=[('SG-03, SG-04', 'as SG-01 detection'), ('SG-01 (RX loss/corruption)', '≤ 0.162 s')],
      today=0.162,
      scale=1.2,
      ticks=[0, 0.4, 0.8, 1.2],
      today_label="≤ 0.162 s, reference build, not verified",
    ),
    scene=dict(
      kind="lon",
      still=0.7,
      actors=[
        dict(y=157, body="#DC2626", brake=True, keys=[(0, 40), (0.4, 200), (0.7, 250), (0.92, 262)]),
        dict(y=157, keys=[(0, -52), (0.4, 108), (0.7, 190), (0.92, 210)]),
      ],
      pills=P(
        (1, "A wrong input reads as a lead braking", "bad", 0.15, 6),
        (2, "Hard braking passes the envelope", "bad", 0.3, 28),
        (3, "The follower closes in", "bad", 0.6, 228),
      ),
    ),
    chart=dict(
      t1=1.2,
      ticks=[0, 0.4, 0.8, 1.2],
      lanes=[
        ("fault", "fault", 0.0, "input lost or corrupt"),
        ("detected", "detect", 0.162, "RX check ≤ 0.162 s"),
        ("safe state", "react", 0.162, "ACC inactive"),
      ],
    ),
    must="Detect a lost or corrupt input within 0.5 s and end the braking command, with bounded jerk, within the 1 s FTTI.",
    today="Same detection as SG-03: within 0.162 s in the reference build, not yet verified on hardware (GAP-06). The envelope has no "
    "jerk limit, so any in-bound step passes.",
    chips=["FSR-01.06"],
  ),
  "SG-06": dict(
    title="If braking is lost, the driver must be warned within 1 s",
    safe="warning, ACC cancelled",
    hazard="H-06 silent loss of braking",
    budget=dict(
      row="SG-02, SG-06 (loss without warning)",
      src=[("SG-02, SG-06 (loss without warning)", "≈3.5 s")],
      today=3.5,
      scale=1.5,
      ticks=[0, 0.5, 1, 1.5],
      today_label="warns at once, actuates on stale inputs ≈ 3.5 s",
    ),
    scene=dict(
      STOPPED,
      pills=P(
        (1, "Longitudinal control lost", "bad", 0.15, 6),
        (2, "Stale command: no braking", "bad", 0.3, 28),
        (3, "Driver must brake, warned or not", "drv", 0.6, 228),
      ),
    ),
    chart=dict(
      t1=4,
      ticks=[0, 1, 2, 3, 4],
      lanes=[
        ("fault", "fault", 0.0, "braking lost"),
        ("detected", "detect", 0.3, "soft disable raised"),
        ("warning", "ftti", 0.3, "alert at once"),
        ("safe state", "react", 3.5, "≈ 3.5 s on stale inputs"),
      ],
    ),
    must="Detect a loss of longitudinal deceleration within 0.5 s, warn within 1 s and cancel ACC so the driver brakes.",
    today="As for SG-02: the soft disable warns at once but keeps acting on stale inputs for up to about 3.5 s (GAP-16).",
    chips=["DQ-036"],
  ),
  "SG-07": dict(
    title="If forwarding stops, stock PCS must be back within 0.2 s",
    safe="PCS forwarded, relay released",
    hazard="H-08 stock PCS suppressed",
    budget=dict(
      row="SG-07 (forwarding loss)",
      src=[("SG-07 (forwarding loss)", "No supervision of forwarding while the MCU runs"), ("SG-07 (forwarding loss)", "90 ms IWDG")],
      today=9,
      scale=0.4,
      ticks=[0, 0.1, 0.2, 0.3, 0.4],
      today_label="no forwarding supervision",
    ),
    scene=dict(
      STOPPED,
      labels=[(180, 140, "with PCS: stops here", "#BBF7D0")],
      pills=P(
        (1, "Forwarding stalls; the MCU keeps running", "bad", 0.15, 6),
        (2, "Nothing notices; the relay stays in", "bad", 0.3, 28),
        (3, "Stock PCS frames lost: no AEB", "bad", 0.6, 228),
      ),
    ),
    chart=dict(
      t1=0.5,
      ticks=[0, 0.1, 0.2, 0.3, 0.4, 0.5],
      lanes=[
        ("forwarding lost", "fault", 0.0, "PCS frames stop"),
        ("detected", "detect", None, "no supervision of forwarding"),
        ("relay released", "react", None, "only after a hang (watchdog)"),
        ("driver told", "ftti", None, "no warning today"),
      ],
    ),
    must="Supervise the forwarding of stock PCS frames and release the relay within 0.2 s when forwarding cannot be guaranteed.",
    today="A hang is caught by the 90 ms watchdog (under review, DQ-114). A forwarding stall with the MCU still running is not caught at all (GAP-43, GAP-49).",
    chips=["TSR-711", "DQ-062"],
  ),
  "SG-08": dict(
    title="If the driver looks away, the first alert must come within 6 s",
    safe="escalation, stop in lane",
    hazard="H-09 driver not supervising",
    budget=dict(
      row="SG-08 (driver not supervising)",
      src=[("SG-08 (driver not supervising)", "First vision alert at 5 s")],
      today=5.3,
      scale=8,
      ticks=[0, 2, 4, 6, 8],
      today_label="first alert at 5 s, plus latency",
    ),
    scene=dict(
      kind="lon",
      still=0.6,
      objects=[("phone", 440, 30)],
      actors=[dict(y=157, body="#DC2626", keys=[(0, 20), (0.92, 430)])],
      pills=P(
        (1, "Driver looks at the phone", "drv", 0.1, 6),
        (2, "Driver monitoring counts 5 s", "info", 0.3, 28),
        (3, "First alert; latency not yet counted", "bad", 0.55, 228),
      ),
    ),
    chart=dict(
      t1=8,
      ticks=[0, 2, 4, 6, 8],
      lanes=[
        ("attention lost", "fault", 0.0, "driver looks away"),
        ("detected", "detect", 5.0, "policy: 5 s"),
        ("first alert", "react", 5.3, "+ frame and model latency"),
        ("end to end", "ftti", None, "not yet measured"),
      ],
    ),
    must="Give the first alert within 6 s of the loss of attention, measured end to end from the driver's change to the alert.",
    today="The first vision alert comes after 5 s of distraction. Camera frame and model latency are not counted, and the end-to-end time is not yet measured.",
    chips=["FSR-08.01", "DQ-205"],
  ),
}
