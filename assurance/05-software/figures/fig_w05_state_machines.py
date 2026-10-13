#!/usr/bin/env python3
"""Generate the WP-W-05 §5 state diagrams (Figure 5-1, 5-2, ...) from the state-machine records.

Source of record: assurance/05-software/state-machines/*.yaml. The records are read with the loader of
assurance/trace/tools/check_state_machines.py, and the implementation state of every transition is the one that
module derives from the WP-W-02 Baseline column (trace/items/swsr.yaml) of the SWSRs the transition cites. The same
module generates the WP-W-05 §5 tables and the figure embeds (figure_number, figure_file), so the tables, the
embeds and the figures cannot disagree.

Drawing rules:
  - states are rounded boxes, laid out in columns by BFS rank from the initial state ("m" counts as every state,
    as check S2 does); a column holding one state is drawn as a tall box so every arrow to it is straight;
  - a transition from "any" state starts on the dashed frame that encloses all states; one to "same" from "any"
    is an internal transition, listed in the frame's top compartment; "m" (the requested mode) is a dashed
    pseudo-state; a transition with several source states joins at a junction dot;
  - arrow colour is the implementation state: teal = implemented at the baseline (host tests only, not verified),
    amber = partial, red dashed = not implemented, grey dotted = not assessed. Nothing is drawn as verified;
  - the records do not classify states as safe or fault states, so no state is styled as one.
The layout is checked geometrically on every run (no line through a box or a label, no overlapping labels, no
crossing lines, nothing outside the canvas); a record change that the layout cannot draw cleanly fails the run.

Usage (from the repository root):
    python3 assurance/05-software/figures/fig_w05_state_machines.py           # write the SVGs
    python3 assurance/05-software/figures/fig_w05_state_machines.py --check   # fail if a committed SVG is stale

Standard library only (PyYAML is used by the loader if importable).
"""
from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parent.parent
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import check_state_machines as csm

# ---------------------------------------------------------------- palette (copied from trace_figures.py)

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
BORDER = "#64748B"
CHIP = "#F8FAFC"
SW = "#0F766E"
AMBER = "#D97706"
RED = "#D2553F"
GREY_BG = "#F1F5F9"
ACTION = "#334155"

W = 1280
FX0, FX1 = 40, W - 40          # frame (any state) left and right border

# status -> (colour, dash, legend text)
STATUS = {
  "impl": (SW, "", "Implemented at the baseline (WP-W-02 Baseline; host tests only, not verified)"),
  "partial": (AMBER, "", "Partial"),
  "not": (RED, "6 4", "Not implemented"),
  "unknown": (FAINT, "2 3", "Not assessed"),
}
MARKERS = {"ink": INK, "muted": MUTED, "impl": SW, "partial": AMBER, "not": RED, "unknown": FAINT}


# ---------------------------------------------------------------- SVG helpers (copied from trace_figures.py)

def el(tag: str, text: str | None = None, **attrs) -> str:
  """One SVG element; attribute names use _ for - (stroke_width -> stroke-width), a trailing _ is dropped."""
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if text is None else f"<{tag}{a}>{escape(text)}</{tag}>"


def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def text(x, y, s, size=11, fill=INK, weight="", anchor="", family="", style="") -> str:
  return el("text", s, x=fmt(x), y=fmt(y), font_size=size, fill=fill, font_weight=weight, text_anchor=anchor,
            font_family=family, font_style=style)


def rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, sw=1.2, rx=8, dash="", opacity="") -> str:
  return el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, fill=fill, stroke=stroke,
            stroke_width=sw, stroke_dasharray=dash, opacity=opacity)


def line(x1, y1, x2, y2, stroke=MUTED, sw=1.4, dash="", marker="") -> str:
  return el("line", None, x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=sw,
            stroke_dasharray=dash, marker_end=f"url(#{marker})" if marker else "")


def path(d, stroke=MUTED, sw=1.4, fill="none", dash="", marker="", opacity="") -> str:
  return el("path", None, d=d, stroke=stroke, stroke_width=sw, fill=fill, stroke_dasharray=dash,
            marker_end=f"url(#{marker})" if marker else "", opacity=opacity, stroke_linejoin="round")


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  defs = "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" ' +
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k, c in MARKERS.items())
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" ' +
          f'font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc), f"<defs>{defs}</defs>",
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def header(width: int, number: str, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


# ---------------------------------------------------------------- text measurement and labels

def tw(s: str, size: float, bold: bool = False, mono: bool = False) -> float:
  """Approximate rendered width of s in Inter (or a monospace font)."""
  if mono:
    return len(s) * size * 0.61
  w = 0.0
  for ch in s:
    if ch in "il.,:;'|!·":
      k = 0.26
    elif ch == " ":
      k = 0.28
    elif ch in "fjrt()[]{}/-":
      k = 0.37
    elif ch in "mwMW":
      k = 0.86
    elif ch.isupper() or ch in "≥≤∈→":
      k = 0.68
    elif ch.isdigit():
      k = 0.6
    else:
      k = 0.55
    w += k * size
  return w * (1.07 if bold else 1.0)


def wrap(s: str, width: float, size: float, bold: bool = False, first: float | None = None) -> list[str]:
  """Greedy word wrap; the first line may have a different width."""
  lines, cur = [], ""
  for word in s.split():
    lim = first if (first is not None and not lines) else width
    cand = f"{cur} {word}" if cur else word
    if not cur or tw(cand, size, bold) <= lim:
      cur = cand
    else:
      lines.append(cur)
      cur = word
  lines.append(cur)
  return lines


EV_SIZE, TX_SIZE, LH, PILL_H = 11, 10.5, 14, 18


@dataclass
class Label:
  tid: str
  status: str
  build: str
  ev: list[str]
  rest: list[tuple[str, str]]       # (text, colour)
  pill_w: float
  chip_w: float
  width: float
  height: float


def pill_w(tid: str) -> float:
  return tw(tid, 10, bold=True) + 14


def chip_w(build: str) -> float:
  return tw(build, 9.5) + 12 if build != "all" else 0


def make_label(t: dict, status: str, width: float) -> Label:
  build = t.get("build", "all")
  pw, cw = pill_w(t["id"]), chip_w(build)
  head = pw + 6 + (cw + 6 if cw else 0)
  ev = wrap(t["event"], width, EV_SIZE, bold=True, first=width - head)
  rest: list[tuple[str, str]] = []
  if t.get("guard"):
    rest += [(s, MUTED) for s in wrap(f"[{t['guard']}]", width, TX_SIZE)]
  if t.get("action"):
    rest += [(s, ACTION) for s in wrap(f"/ {t['action']}", width, TX_SIZE)]
  widths = [head + tw(ev[0], EV_SIZE, True)] + [tw(s, EV_SIZE, True) for s in ev[1:]] + [tw(s, TX_SIZE) for s, _ in rest]
  h = PILL_H + LH * (len(ev) - 1 + len(rest)) + 2
  return Label(t["id"], status, build, ev, rest, pw, cw, max(widths), h)


def natural_width(t: dict) -> float:
  """Width of the label when nothing is wrapped (each of event, guard, action on one line)."""
  head = pill_w(t["id"]) + 6 + (chip_w(t.get("build", "all")) + 6 if t.get("build", "all") != "all" else 0)
  parts = [head + tw(t["event"], EV_SIZE, True)]
  if t.get("guard"):
    parts.append(tw(f"[{t['guard']}]", TX_SIZE))
  if t.get("action"):
    parts.append(tw(f"/ {t['action']}", TX_SIZE))
  return max(parts)


def pill(x: float, y: float, tid: str, status: str) -> list[str]:
  """Transition-ID pill with its top-left corner at (x, y)."""
  w = pill_w(tid)
  return [rect(x, y, w, PILL_H, fill=STATUS[status][0], stroke="none", rx=9, sw=0),
          text(x + w / 2, y + 12.5, tid, size=10, fill="#FFFFFF", weight=700, anchor="middle")]


def chip(x: float, y: float, build: str) -> list[str]:
  w = chip_w(build)
  return [rect(x, y + 2, w, PILL_H - 4, fill="#FFFFFF", stroke=FAINT, rx=4, sw=1),
          text(x + w / 2, y + 12.5, build, size=9.5, fill=MUTED, anchor="middle")]


def draw_label(lb: Label, x: float, top: float) -> list[str]:
  out = pill(x, top, lb.tid, lb.status)
  cx = x + lb.pill_w + 6
  if lb.chip_w:
    out += chip(cx, top, lb.build)
    cx += lb.chip_w + 6
  y = top + 13
  out.append(text(cx, y, lb.ev[0], size=EV_SIZE, weight=600))
  y += 4
  for s in lb.ev[1:]:
    y += LH
    out.append(text(x, y, s, size=EV_SIZE, weight=600))
  for s, c in lb.rest:
    y += LH
    out.append(text(x, y, s, size=TX_SIZE, fill=c))
  return out


# ---------------------------------------------------------------- layout model

@dataclass
class Item:
  kind: str                 # init | frame | self | gap
  region: object            # "L", "R" or the gap index
  t: dict | None = None
  status: str = "unknown"
  target: str = ""
  sources: list[str] = field(default_factory=list)   # gap: sources in the adjacent column
  skips: list[str] = field(default_factory=list)     # gap: sources further away (routed over the column tops)
  side: str = ""            # gap: "L" when the sources are in the left column of the gap, else "R"
  order: tuple = ()
  label: Label | None = None


@dataclass
class Box:
  name: str
  x: float
  w: float
  y: float = 0
  h: float = 0
  lane: bool = False
  pseudo: bool = False


class LayoutError(ValueError):
  pass


def ranks(sm: dict) -> dict[str, int]:
  """BFS rank of every state from the initial state; 'm' reaches every state (as check S2)."""
  states = sm["states"]
  rank = {sm["initial"]: 0}
  frontier = [sm["initial"]]
  while frontier:
    nxt = []
    for t in sm["transitions"]:
      if not set(csm._sources(t, states)) & set(frontier):
        continue
      targets = states if t["to"] == "m" else ([] if t["to"] == "same" else [t["to"]])
      for s in targets:
        if s not in rank:
          rank[s] = 1 + min(rank[f] for f in frontier if f in csm._sources(t, states))
          nxt.append(s)
    frontier = nxt
  missing = [s for s in states if s not in rank]
  if missing:
    raise LayoutError(f"{sm['machine']}: states not reachable from {sm['initial']}: {missing}")
  return rank


@dataclass
class Figure:
  sm: dict
  number: str
  cols: list[list[str]]
  boxes: dict[str, Box]
  items: list[Item]
  internal: list[tuple[dict, str]]
  regions: dict[object, tuple[float, float]]
  junction_x: dict[int, float]   # id(item) -> x
  channel_y: dict[str, float]    # skip source -> y
  g0: float = 0
  g1: float = 0
  frame: bool = False
  top: float = 0
  cols_index: dict[str, int] = field(default_factory=dict)   # state -> column
  stack: dict[str, int] = field(default_factory=dict)        # state -> position in its column
  rows: dict[int, tuple[float, list[float]]] = field(default_factory=dict)


def classify(sm: dict, sw: dict) -> tuple[list[list[str]], list[Item], list[tuple[dict, str]]]:
  states = sm["states"]
  rank = ranks(sm)
  ncol = max(rank.values()) + 1
  cols = [[s for s in states if rank[s] == r] for r in range(ncol)]
  if any(t["to"] == "m" for t in sm["transitions"]):
    cols.append(["m"])
  col = {s: i for i, c in enumerate(cols) for s in c}
  last = len(cols) - 1
  items = [Item("init", "L", target=sm["initial"], order=(-1,))]
  internal = []
  for k, t in enumerate(sm["transitions"]):
    st = csm.transition_state(t, sw)
    if t["from"] == "any":
      if t["to"] == "same":
        internal.append((t, st))
        continue
      c = col[t["to"]]
      if c not in (0, last):
        raise LayoutError(f"{t['id']}: a transition from any state to a middle column is not drawn by this layout")
      items.append(Item("frame", "L" if c == 0 else "R", t, st, target=t["to"], order=(k,)))
      continue
    srcs = csm._sources(t, states)
    tgt = t["to"]
    if tgt == "same" or (srcs == [tgt]):
      for s in srcs:
        c = col[s]
        if c not in (0, last):
          raise LayoutError(f"{t['id']}: self-transition of a middle-column state is not drawn by this layout")
        items.append(Item("self", "L" if c == 0 else "R", t, st, target=s, order=(k,)))
      continue
    if tgt in srcs:
      raise LayoutError(f"{t['id']}: mixed self and outgoing transition is not drawn by this layout")
    ct = col[tgt]
    left = [s for s in srcs if col[s] < ct]
    right = [s for s in srcs if col[s] > ct]
    if (left and right) or any(col[s] == ct for s in srcs):
      raise LayoutError(f"{t['id']}: sources on both sides of, or in the column of, {tgt}")
    if left:
      g, side = ct - 1, "L"
      adj = [s for s in left if col[s] == ct - 1]
      skips = [s for s in left if col[s] < ct - 1]
    else:
      g, side = ct, "R"
      adj = [s for s in right if col[s] == ct + 1]
      skips = [s for s in right if col[s] > ct + 1]
    for s in skips:
      if len(cols[col[s]]) != 1 or side != "L":
        raise LayoutError(f"{t['id']}: only a single-state column can skip to the right over the column tops")
    if not adj:
      raise LayoutError(f"{t['id']}: a skip transition needs at least one source in the adjacent column")
    items.append(Item("gap", g, t, st, target=tgt, sources=adj, skips=skips, side=side, order=(k,)))
  return cols, items, internal


def build_figure(sm: dict, sw: dict, number: str) -> Figure:
  cols, items, internal = classify(sm, sw)
  frame = bool(internal) or any(i.kind == "frame" for i in items)
  # column widths
  boxes: dict[str, Box] = {}
  col_w = []
  for c in cols:
    w = max(140 if s == "m" else tw(s, 13, mono=True) + 44 for s in c)
    col_w.append(max(120, w))
  # region widths: desired from natural label widths, scaled to the room left
  ncol = len(cols)
  regions_order: list[object] = ["L", *range(ncol - 1), "R"]
  band: dict[object, dict[str, int]] = {r: {"L": 0, "R": 0} for r in regions_order}
  for it in items:
    if it.kind == "gap" and (len(it.sources) > 1 or it.skips):
      band[it.region][it.side] += 1
  desire = {}
  for r in regions_order:
    its = [i for i in items if i.region == r and i.t is not None]
    nat = max([natural_width(i.t) + (48 if i.kind == "self" else 0) for i in its], default=0)
    bands = sum(18 + 16 * (n - 1) + 8 for n in band[r].values() if n)
    if r == "L":
      nat = max(nat, 90)
    if not its and r != "L":
      desire[r] = 24 if r == "R" else 90
    else:
      desire[r] = min(nat + 28, 300 if r in ("L", "R") else 660) + bands
  room = (FX1 - FX0) - sum(col_w)
  total = sum(desire.values())
  if total <= room:
    gaps = [r for r in regions_order if r not in ("L", "R")]
    for r in gaps:
      desire[r] += (room - total) / len(gaps)
  else:
    fixed = {r: min(desire[r], 200) for r in regions_order}
    flex = total - sum(fixed.values())
    scale = (room - sum(fixed.values())) / flex
    for r in regions_order:
      desire[r] = fixed[r] + (desire[r] - fixed[r]) * scale
  x = FX0 + desire["L"]
  regions: dict[object, tuple[float, float]] = {}
  for i, c in enumerate(cols):
    for s in c:
      boxes[s] = Box(s, x, col_w[i], lane=len(c) == 1, pseudo=s == "m")
    x += col_w[i]
    if i < ncol - 1:
      x += desire[i]
  # label x-ranges and junction lanes
  junction_x: dict[int, float] = {}
  count = {r: {"L": 0, "R": 0} for r in regions_order}
  for it in items:
    if it.kind == "gap" and (len(it.sources) > 1 or it.skips):
      lb = boxes[cols[it.region][0]]
      rb = boxes[cols[it.region + 1][0]]
      k = count[it.region][it.side]
      count[it.region][it.side] += 1
      junction_x[id(it)] = lb.x + lb.w + 18 + 16 * k if it.side == "L" else rb.x - 18 - 16 * k
  for r in regions_order:
    if r == "L":
      regions[r] = (FX0 + 14, boxes[cols[0][0]].x - 14)
    elif r == "R":
      lb = boxes[cols[-1][0]]
      regions[r] = (lb.x + lb.w + 14, FX1 - 14)
    else:
      lb = boxes[cols[r][0]]
      rb = boxes[cols[r + 1][0]]
      pl = 18 + 16 * (band[r]["L"] - 1) + 10 if band[r]["L"] else 0
      pr = 18 + 16 * (band[r]["R"] - 1) + 10 if band[r]["R"] else 0
      regions[r] = (lb.x + lb.w + 12 + pl, rb.x - 12 - pr)
  for it in items:
    if it.t is None:
      continue
    x0, x1 = regions[it.region]
    if it.kind == "self":
      x1 -= 44
    it.label = make_label(it.t, it.status, x1 - x0)
  return Figure(sm, number, cols, boxes, items, internal, regions, junction_x, {}, frame=frame,
                cols_index={s: i for i, c in enumerate(cols) for s in c},
                stack={s: j for c in cols for j, s in enumerate(c)})


def place(f: Figure, top: float) -> None:
  """Vertical placement: lanes span the graph; stacked boxes are pushed down or grown until every label fits."""
  f.top = top
  skips = sorted({s for it in f.items if it.kind == "gap" for s in it.skips})
  f.g0 = top
  f.channel_y = {s: f.g0 + 14 + 16 * i for i, s in enumerate(skips)}
  start = f.g0 + (16 * len(skips) + 22 if skips else 8)
  multi = [c for c in f.cols if len(c) > 1]
  extra = {s: 0.0 for c in multi for s in c}
  hmin = {s: 46.0 for c in multi for s in c}
  # attachments: (state, side) -> items, in item order
  attach: dict[tuple[str, str], list[int]] = defaultdict(list)
  regs = sorted({str(i.region) for i in f.items})
  ordered = []
  for r in regs:
    its = [i for i in f.items if str(i.region) == r]
    its.sort(key=lambda i: (min([f.stack[s] for s in [*i.sources, i.target] if not f.boxes[s].lane] or [-1]), i.order))
    ordered += its
  for it in ordered:
    for s in [*it.sources, it.target]:
      b = f.boxes[s]
      if b.lane:
        continue
      side = facing(f, it, s)
      attach[(s, side)].append(id(it))
  for (s, _), lst in attach.items():
    hmin[s] = max(hmin[s], 22.0 + 18 * len(lst))
  for _ in range(400):
    for c in multi:
      y = start
      for s in c:
        b = f.boxes[s]
        y += extra[s]
        b.y, b.h = y, hmin[s]
        y += b.h + 20
    cursor = dict.fromkeys(regs, start)
    f.rows = {}
    ok = True
    for it in ordered:
      r = str(it.region)
      lab_h = it.label.height if it.label else LH
      need_top = cursor[r] + 6
      tied = [s for s in it.sources + [it.target] if not f.boxes[s].lane]
      if it.kind == "gap" and (len(it.sources) > 1 or it.skips):
        if not f.boxes[it.target].lane:
          raise LayoutError(f"{it.t['id']}: a joined transition must end in a single-state column")
        ys = [row(f, attach, s, facing(f, it, s), id(it)) for s in it.sources if not f.boxes[s].lane]
        if len(ys) != len(it.sources):
          raise LayoutError(f"{it.t['id']}: a joined transition needs its adjacent sources in a stacked column")
        y_main = max(sum(ys) / len(ys), need_top + lab_h + 5)
        trunk = ys + [y_main] + [f.channel_y[s] for s in it.skips]
        f.rows[id(it)] = (y_main, ys)
        cursor[r] = max(max(trunk), y_main) + 10
        continue
      if tied:
        if len(tied) > 1:
          raise LayoutError(f"{it.t['id'] if it.t else 'init'}: both ends in stacked columns is not drawn by this layout")
        s = tied[0]
        y = row(f, attach, s, facing(f, it, s), id(it))
        top_lab = y - 5 - lab_h if it.kind != "self" else min(y + 10 - lab_h, y - 12)
        if top_lab < need_top:
          deficit = need_top - top_lab
          lst = attach[(s, facing(f, it, s))]
          i = lst.index(id(it))
          if i == 0:
            extra[s] += deficit
          else:
            hmin[s] += deficit * (len(lst) + 1) / (i + 1) + 1
          ok = False
          break
        f.rows[id(it)] = (y, [])
        cursor[r] = y + (20 if it.kind == "self" else 8)
        continue
      if it.kind == "self":
        y = need_top + max(lab_h - 10, 12)
        cursor[r] = y + 20
      else:
        y = need_top + lab_h + 5
        cursor[r] = y + 10
      f.rows[id(it)] = (y, [])
    if ok:
      break
  else:
    raise LayoutError("vertical placement did not converge")
  bottom = max([*cursor.values()] + [b.y + b.h + 14 for b in f.boxes.values() if not b.lane])
  f.g1 = bottom + 4
  for b in f.boxes.values():
    if b.lane:
      b.y, b.h = f.g0, f.g1 - f.g0


def facing(f: Figure, it: Item, s: str) -> str:
  """Side of box s that item it attaches to."""
  if it.region == "L":
    return "L"
  if it.region == "R":
    return "R"
  return "R" if f.cols_index[s] == it.region else "L"


def row(f: Figure, attach, s: str, side: str, key: int) -> float:
  lst = attach[(s, side)]
  b = f.boxes[s]
  i = lst.index(key)
  return b.y + b.h * (i + 1) / (len(lst) + 1)


# ---------------------------------------------------------------- drawing and the geometric check

@dataclass
class Geo:
  boxes: list[tuple[str, float, float, float, float]] = field(default_factory=list)
  labels: list[tuple[str, float, float, float, float]] = field(default_factory=list)
  segs: list[tuple[str, float, float, float, float]] = field(default_factory=list)


def seg_path(geo: Geo, owner: str, pts: list[tuple[float, float]]) -> str:
  for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
    geo.segs.append((owner, x1, y1, x2, y2))
  return "M" + " L".join(f"{fmt(x)},{fmt(y)}" for x, y in pts)


def arrow(geo: Geo, owner: str, pts, status: str, head: bool = True) -> str:
  c, dash, _ = STATUS[status]
  return path(seg_path(geo, owner, pts), stroke=c, sw=1.6, dash=dash, marker=status if head else "")


def draw_state(b: Box, initial: bool) -> list[str]:
  if b.pseudo:
    out = [rect(b.x, b.y, b.w, b.h, fill=CHIP, stroke=BORDER, rx=12, sw=1.4, dash="5 4")]
    cy = b.y + b.h / 2
    out.append(text(b.x + b.w / 2, cy - 4, "m", size=15, weight=700, anchor="middle", family=MONO))
    out.append(text(b.x + b.w / 2, cy + 13, "the requested mode", size=10.5, fill=MUTED, anchor="middle"))
    out.append(text(b.x + b.w / 2, cy + 27, "(the guard says which)", size=10.5, fill=MUTED, anchor="middle"))
    return out
  out = [rect(b.x, b.y, b.w, b.h, fill="#FFFFFF", stroke=INK if initial else BORDER, rx=12, sw=2 if initial else 1.5)]
  cy = b.y + b.h / 2 + 5
  out.append(text(b.x + b.w / 2, cy, b.name, size=13, weight=700, anchor="middle", family=MONO))
  if initial:
    out.append(text(b.x + b.w / 2, cy + 16, "initial state", size=10.5, fill=MUTED, anchor="middle"))
  return out


def draw(f: Figure, geo: Geo) -> list[str]:
  out: list[str] = []
  sm = f.sm
  for b in f.boxes.values():
    out += draw_state(b, b.name == sm["initial"])
    geo.boxes.append((b.name, b.x, b.y, b.x + b.w, b.y + b.h))
  for it in f.items:
    y, ys = f.rows[id(it)]
    x0, x1 = f.regions[it.region]
    tgt = f.boxes[it.target]
    if it.kind == "init":
      out.append(el("circle", None, cx=fmt(x0 + 6), cy=fmt(y), r=6, fill=INK))
      out.append(path(seg_path(geo, "init", [(x0 + 12, y), (tgt.x, y)]), stroke=INK, sw=1.6, marker="ink"))
      out.append(text(x0 + 20, y - 7, "initial", size=10.5, fill=MUTED))
      geo.labels.append(("init", x0 + 20, y - 18, x0 + 20 + tw("initial", 10.5), y - 4))
      continue
    tid = it.t["id"]
    lb = it.label
    if it.kind == "frame":
      if it.region == "L":
        out.append(arrow(geo, tid, [(FX0, y), (tgt.x, y)], it.status))
      else:
        out.append(arrow(geo, tid, [(FX1, y), (tgt.x + tgt.w, y)], it.status))
      top = y - 5 - lb.height
    elif it.kind == "self":
      if it.region == "L":
        bx, ox = tgt.x, tgt.x - 32
      else:
        bx, ox = tgt.x + tgt.w, tgt.x + tgt.w + 32
      out.append(arrow(geo, tid, [(bx, y - 10), (ox, y - 10), (ox, y + 10), (bx, y + 10)], it.status))
      top = min(y + 10 - lb.height, y - 12)
      x1 -= 44
    elif len(it.sources) == 1 and not it.skips:
      src = f.boxes[it.sources[0]]
      if it.side == "L":
        pts = [(src.x + src.w, y), (tgt.x, y)]
      else:
        pts = [(src.x, y), (tgt.x + tgt.w, y)]
      out.append(arrow(geo, tid, pts, it.status))
      top = y - 5 - lb.height
    else:
      jx = f.junction_x[id(it)]
      for s, sy in zip(it.sources, ys, strict=True):
        b = f.boxes[s]
        sx = b.x + b.w if it.side == "L" else b.x
        out.append(arrow(geo, tid, [(sx, sy), (jx, sy)], it.status, head=False))
      for s in it.skips:
        b = f.boxes[s]
        cy = f.channel_y[s]
        out.append(arrow(geo, tid, [(b.x + b.w, cy), (jx, cy)], it.status, head=False))
      span = ys + [y] + [f.channel_y[s] for s in it.skips]
      out.append(arrow(geo, tid, [(jx, min(span)), (jx, max(span))], it.status, head=False))
      tx = tgt.x if it.side == "L" else tgt.x + tgt.w
      out.append(arrow(geo, tid, [(jx, y), (tx, y)], it.status))
      out.append(el("circle", None, cx=fmt(jx), cy=fmt(y), r=4, fill=STATUS[it.status][0]))
      top = y - 5 - lb.height
    out += draw_label(lb, x0, top)
    geo.labels.append((tid, x0, top, x0 + lb.width, top + lb.height))
    if x0 + lb.width > x1 + 1:
      raise LayoutError(f"{tid}: label wider than its region")
  return out


def check_geometry(geo: Geo, width: float, height: float) -> list[str]:
  """Every problem that would make the figure unclean."""
  bad = []

  def hits(seg, r, pad=0.0):
    _, x1, y1, x2, y2 = seg
    ax0, ax1 = sorted((x1, x2))
    ay0, ay1 = sorted((y1, y2))
    return ax1 > r[1] + pad and ax0 < r[3] - pad and ay1 > r[2] + pad and ay0 < r[4] - pad

  for s in geo.segs:
    for b in geo.boxes:
      if hits(s, b, 1.5):
        bad.append(f"line of {s[0]} passes through state {b[0]}")
    for lb in geo.labels:
      if hits(s, lb, -2):
        bad.append(f"line of {s[0]} crosses the label of {lb[0]}")
  rects = geo.boxes + geo.labels
  for i, a in enumerate(rects):
    for b in rects[i + 1:]:
      if a[1] < b[3] + 2 and b[1] < a[3] + 2 and a[2] < b[4] + 2 and b[2] < a[4] + 2:
        bad.append(f"{a[0]} overlaps {b[0]}")
  for i, a in enumerate(geo.segs):
    for b in geo.segs[i + 1:]:
      if a[0] == b[0]:
        continue
      if hits(a, (b[0], min(b[1], b[3]) - 1.5, min(b[2], b[4]) - 1.5, max(b[1], b[3]) + 1.5, max(b[2], b[4]) + 1.5)):
        bad.append(f"line of {a[0]} crosses or runs along the line of {b[0]}")
  for name, x0, y0, x1, y1 in rects:
    if x0 < 40 - 0.5 or x1 > width - 40 + 0.5 or y0 < 84 or y1 > height:
      bad.append(f"{name} outside the drawing area")
  return bad


# ---------------------------------------------------------------- figure

def internal_lines(f: Figure) -> list[tuple[dict, str, list[str]]]:
  out = []
  for t, st in f.internal:
    head = 20 + pill_w(t["id"]) + 6 + (chip_w(t.get("build", "all")) + 6 if t.get("build", "all") != "all" else 0)
    s = t["event"] + (f"  [{t['guard']}]" if t.get("guard") else "") + (f"  / {t['action']}" if t.get("action") else "")
    out.append((t, st, wrap(s, FX1 - FX0 - 60 - head, TX_SIZE)))
  return out


def legend_entries(f: Figure) -> list[tuple[str, float, list[str]]]:
  """(kind, width, svg drawn at the origin) for the entries actually used."""
  used = {i.status for i in f.items if i.t} | {st for _, st in f.internal}
  out = []
  for st in ("impl", "partial", "not", "unknown"):
    if st in used:
      c, dash, lab = STATUS[st]
      out.append((st, 48 + tw(lab, 11), [path("M0,-4 L34,-4", stroke=c, sw=1.6, dash=dash, marker=st),
                                          text(42, 0, lab, size=11, fill=MUTED)]))
  pw = pill_w("T1")
  out.append(("pill", pw + 8 + tw("transition ID (colour = status)", 11),
              [*pill(0, -13, "ID", "impl"), text(pw + 8, 0, "transition ID (colour = status)", size=11, fill=MUTED)]))
  builds = sorted({i.t.get("build", "all") for i in f.items if i.t} | {t.get("build", "all") for t, _ in f.internal})
  notes = {"reference": "only with LIONDRIVER_REFERENCE=1", "upstream": "only without LIONDRIVER_REFERENCE=1"}
  for b in builds:
    if b in notes:
      lab = f"{notes[b]} (others: every build)"
      out.append((b, chip_w(b) + 8 + tw(lab, 11), [*chip(0, -13, b), text(chip_w(b) + 8, 0, lab, size=11, fill=MUTED)]))
  out.append(("label", 8 + tw("label: event  [guard]  / action", 11), [text(0, 0, "label: event  [guard]  / action",
                                                                             size=11, fill=MUTED)]))
  out.append(("initial", 40 + tw("initial state", 11),
              [el("circle", None, cx=5, cy=-4, r=5, fill=INK), path("M10,-4 L30,-4", stroke=INK, sw=1.4, marker="ink"),
               text(38, 0, "initial state", size=11, fill=MUTED)]))
  if f.frame:
    lab = "dashed frame: an arrow starting on it applies in every state"
    out.append(("frame", 36 + tw(lab, 11), [rect(0, -11, 26, 14, fill="none", stroke=BORDER, rx=4, dash="5 4"),
                                            text(34, 0, lab, size=11, fill=MUTED)]))
  if any(len(i.sources) > 1 or i.skips for i in f.items):
    lab = "junction: one transition from several states"
    out.append(("junction", 30 + tw(lab, 11), [path("M0,-9 L12,-4 M0,1 L12,-4", stroke=MUTED, sw=1.4),
                                               el("circle", None, cx=12, cy=-4, r=3.5, fill=MUTED),
                                               text(24, 0, lab, size=11, fill=MUTED)]))
  return out


def render_figure(sm: dict, sw: dict, number: str, ref: str) -> str:
  f = build_figure(sm, sw, number)
  body: list[str] = []
  machine = sm["machine"]
  body += header(W, number, f"{sm['title']} state machine ({machine})",
                 f"Generated from the record state-machines/{csm.BLOCKS[machine]}.yaml; arrow colour = implementation state "
                 + "of the cited SWSRs (WP-W-02 Baseline column). Nothing is verified.", ref)
  y = 104
  geo = Geo()
  frame_parts: list[str] = []
  if f.frame:
    y += 22
    il = internal_lines(f)
    if il:
      frame_parts.append(text(FX0 + 16, y + 4, "In every state, without a state change (internal transitions):",
                              size=11, weight=700, fill=MUTED))
      y += 14
      for t, st, lines in il:
        px = FX0 + 16
        frame_parts += pill(px, y + 2, t["id"], st)
        cx = px + pill_w(t["id"]) + 6
        if t.get("build", "all") != "all":
          frame_parts += chip(cx, y + 2, t["build"])
          cx += chip_w(t["build"]) + 6
        for j, s in enumerate(lines):
          frame_parts.append(text(cx, y + 15 + j * LH, s, size=TX_SIZE, fill=ACTION))
        geo.labels.append((t["id"], FX0 + 14, y + 2, cx + max(tw(s, TX_SIZE) for s in lines), y + 2 + PILL_H
                           + LH * (len(lines) - 1)))
        y += PILL_H + 4 + LH * (len(lines) - 1)
      y += 8
      frame_parts.append(line(FX0 + 14, y, FX1 - 14, y, stroke=HAIR, sw=1))
      y += 10
  place(f, y + 6)
  graph = draw(f, geo)
  bottom = f.g1 + 12
  if f.frame:
    body.append(rect(FX0, 98, FX1 - FX0, bottom - 98, fill="none", stroke=BORDER, rx=14, sw=1.4, dash="7 5"))
    lab = f"any state of {machine}"
    body.append(rect(FX0 + 14, 89, tw(lab, 10, True) + 20, PILL_H, fill=MUTED, stroke="none", rx=9, sw=0))
    body.append(text(FX0 + 24, 101.5, lab, size=10, weight=700, fill="#FFFFFF"))
    body += frame_parts
  body += graph
  y = bottom + 16
  if sm.get("non_revoking"):
    rows = []
    for n in sm["non_revoking"]:
      s = f"{n['event']}  →  {n['reaction']}  ({', '.join(n['swsr'])})"
      rows.append((n, wrap(s, FX1 - FX0 - 60 - chip_w(n.get("build", "all")), TX_SIZE)))
    h = 30 + sum(PILL_H + LH * (len(ls) - 1) + 2 for _, ls in rows) + 6
    body.append(rect(FX0, y, FX1 - FX0, h, fill=GREY_BG, stroke=LINE, rx=10, sw=1.2))
    body.append(text(FX0 + 16, y + 20, "Reactions that do not change the state (record field non_revoking; drawn "
                     + "neutral: the §5 table gives them no Status column)", size=11, weight=700, fill=MUTED))
    yy = y + 28
    for n, ls in rows:
      cx = FX0 + 16
      if n.get("build", "all") != "all":
        body.extend(chip(cx, yy, n["build"]))
        cx += chip_w(n["build"]) + 8
      for j, s in enumerate(ls):
        body.append(text(cx, yy + 13 + j * LH, s, size=TX_SIZE, fill=ACTION))
      yy += PILL_H + LH * (len(ls) - 1) + 2
    geo.labels.append(("non_revoking", FX0, y, FX1, y + h))
    y += h + 16
  # legend
  body.append(line(40, y, W - 40, y, stroke=HAIR, sw=1))
  y += 24
  lx = 40
  for _, w, parts in legend_entries(f):
    if lx + w > W - 40:
      lx, y = 40, y + 24
    body.append(f'<g transform="translate({fmt(lx)},{fmt(y)})">' + "".join(parts) + "</g>")
    lx += w + 26
  height = int(y + 22)
  bad = check_geometry(geo, W, height)
  if bad:
    raise LayoutError(f"{machine}: layout not clean:\n  " + "\n  ".join(sorted(set(bad))))
  return svg(W, height, f"Figure {number} · {sm['title']} state machine ({machine})", describe(sm, sw), body)


def describe(sm: dict, sw: dict) -> str:
  parts = []
  for t in sm["transitions"]:
    st = csm.LABEL[csm.transition_state(t, sw)].lower()
    build = "" if t.get("build", "all") == "all" else f", {t['build']} build"
    parts.append(f"{t['id']} {t['from']} to {t['to']} on {t['event']} ({st}{build})")
  return (f"State diagram of {sm['machine']} ({sm['title']}) with states {', '.join(sm['states'])}; initial state "
          + f"{sm['initial']}. Transitions: " + "; ".join(parts) + ". Implemented means implemented at the baseline "
          + "with host tests only; nothing is verified.")


def outputs() -> dict[str, str]:
  sw = csm.swsr_records()
  doc = csm.WP_W05.read_text(encoding="utf-8")
  out = {}
  for p in sorted(csm.SM_DIR.glob("*.yaml")):
    sm = csm.load(p)
    tag = csm.BLOCKS[sm["machine"]]
    number = csm.figure_number(tag, doc)
    name = Path(csm.figure_file(tag, number)).name
    out[name] = render_figure(sm, sw, number, f"WP-W-05 §{number.replace('-', '.')}")
  return out


def main(argv: list[str]) -> int:
  try:
    figs = outputs()
  except LayoutError as e:
    print(f"ERROR {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in figs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"stale: {n}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/05-software/figures/fig_w05_state_machines.py", file=sys.stderr)
      return 1
    print(f"fig_w05_state_machines: {len(figs)} figure(s) current")
    return 0
  for n, c in figs.items():
    (HERE / n).write_text(c, encoding="utf-8")
  print(f"fig_w05_state_machines: wrote {len(figs)} figure(s): {', '.join(figs)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
