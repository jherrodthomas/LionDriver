#!/usr/bin/env python3
"""Draw the safety case (WP-K-01) as GSN diagrams (GSN Community Standard v3 notation).

Structure comes from the case records (assurance/case-records/): goals (claims), strategies
(arguments), solutions (evidence), defeaters and the assumptions each claim relies
on. Contexts and justifications (C1…, J0…) are not records; they are read from the
"⊙" lines of WP-K-01 §3–§4 and attached to the goal or strategy above them.
Nothing here is argument content: change the records or WP-K-01 and regenerate.

Symbols: goal = rectangle; strategy = parallelogram; solution = circle, filled by
evidence status; context = rounded rectangle; assumption / justification = oval
marked A / J; undeveloped goal = diamond below it. Solid arrow = SupportedBy,
hollow arrow = InContextOf. Defeaters (UL 4600 style, not GSN) are listed on the
goal they undermine. Each sub-argument (a goal with a strategy) is drawn on its own sheet; a goal developed on
another sheet carries a "developed on sheet N" tag.

    python3 assurance/case-records/tools/gsn_diagrams.py            # write the SVGs and README.md
    python3 assurance/case-records/tools/gsn_diagrams.py --check    # fail if they are out of date

The records are validated first; invalid records produce no output.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from caselib import ASSURANCE_DIR, SAFETY_CASE_MD, load_case, validate

OUT_DIR = ASSURANCE_DIR / "10-safety-case" / "gsn"

STATUS_STYLE = {   # evidence_status -> (fill, stroke, label)
  "available": ("#2e7d32", "#1b5e20", "available"),
  "partial": ("#f2b233", "#9a6b00", "partial"),
  "missing": ("#ffffff", "#b3261e", "missing"),
}


class GsnError(Exception):
  pass


@dataclass(eq=False)
class Node:
  ident: str
  kind: str                 # goal, strategy, solution
  text: str
  status: str = ""          # solutions: evidence_status
  sides: list[tuple[str, str, str]] = field(default_factory=list)   # (kind C/A/J, id, text)
  defeaters: list[str] = field(default_factory=list)
  children: list[Node] = field(default_factory=list)
  undeveloped: bool = False
  sheet_link: int | None = None
  sheet_from: int | None = None


# ---------------------------------------------------------------- sources

CTX_RE = re.compile(r"^(\s*)⊙\s+(C\d+|A\d+|J\d+)\b\s*(.*)$")
ELEM_RE = re.compile(r"^(\s*)(?:→\s*)?(G\d+(?:\.\d+)*|S\d+(?:\.\d+)*)\s{2,}\S")


def contexts_from_safety_case(md: str) -> dict[str, list[tuple[str, str, str]]]:
  """Map goal/strategy ID -> [(kind, id, text)] from the ⊙ lines of the text trees."""
  out: dict[str, list[tuple[str, str, str]]] = {}
  defined: dict[str, str] = {}
  in_block = False
  stack: list[tuple[int, str]] = []
  current: list | None = None
  cur_indent = 0
  for line in md.splitlines():
    if line.startswith("```"):
      in_block = not in_block
      stack, current = [], None
      continue
    if not in_block:
      continue
    m = ELEM_RE.match(line)
    if m:
      indent = len(m.group(1))
      stack = [(i, e) for i, e in stack if i < indent] + [(indent, m.group(2))]
      current = None
      continue
    m = CTX_RE.match(line)
    if m:
      indent = len(m.group(1))
      owners = [e for i, e in stack if i < indent]
      if not owners:
        raise GsnError(f"context {m.group(2)} has no goal or strategy above it")
      cid, text = m.group(2), m.group(3).strip()
      current = [cid[0], cid, text]
      cur_indent = indent
      out.setdefault(owners[-1], []).append(current)  # type: ignore[arg-type]
      continue
    stripped = line.strip()
    if current is not None and stripped and not stripped.startswith(("→", "⊙", "⇐")) \
        and len(line) - len(line.lstrip()) > cur_indent:
      current[2] += " " + stripped
    else:
      current = None
  # A context cited again later ("⊙ C4 (safety goals …)") keeps its first text in brackets.
  result: dict[str, list[tuple[str, str, str]]] = {}
  for owner, items in out.items():
    for kind, cid, text in items:
      text = re.sub(r"\s+", " ", text)
      if cid not in defined:
        defined[cid] = text
      result.setdefault(owner, []).append((kind, cid, text))
  return result


def build_tree() -> Node:
  case = load_case()
  report = validate(case)
  if report.errors:
    raise GsnError("case records invalid; run validate.py:\n  " + "\n  ".join(report.errors[:10]))
  recs = case.records
  ctx = contexts_from_safety_case(SAFETY_CASE_MD.read_text(encoding="utf-8"))
  strategies = {r["claim"]: r for r in case.of_kind("argument")}
  claims = {r["id"]: r for r in case.of_kind("claim")}
  roots = [c for c in claims.values() if not c.get("parent")]
  if len(roots) != 1:
    raise GsnError(f"expected one top-level goal, found {[r['id'] for r in roots]}")

  def solution(sid: str) -> Node:
    ev = recs.get(sid)
    if ev is None:
      raise GsnError(f"evidence {sid} not found")
    return Node(sid, "solution", ev["title"], status=ev.get("evidence_status", ""))

  def goal(cid: str) -> Node:
    c = claims[cid]
    g = Node(cid, "goal", c["description"], defeaters=list(c.get("defeaters") or []))
    g.sides = list(ctx.get(cid, []))
    aous = c.get("related_assumptions") or []
    if aous and not any(k == "A" for k, _, _ in g.sides):
      g.sides.append(("A", "A", ", ".join(aous) + " hold (WP-K-01 §5)"))
    s = strategies.get(cid)
    if s is not None:
      st = Node(s["id"], "strategy", s["description"])
      st.sides = list(ctx.get(s["id"], []))
      st.children = [goal(sc) for sc in s["subclaims"]]
      g.children.append(st)
    g.children.extend(solution(e) for e in (c.get("evidence_refs") or []))
    g.undeveloped = not g.children
    return g

  return goal(roots[0]["id"])


# ---------------------------------------------------------------- cybersecurity case (WP-K-03)

CYBER_MD = ASSURANCE_DIR / "10-safety-case" / "WP-K-03-cybersecurity-case.md"
CY_ELEM_RE = re.compile(r"^(CG\d+(?:\.\d+)*|CS\d+(?:\.\d+)*)\b\s*(.*)$")
CY_CTX_RE = re.compile(r"^⊙\s+(CC\d+|CA-[0-9]+(?:…CA-[0-9]+)?|CJ\d+)\s+(.*)$")
CSN_RE = re.compile(r"CSn-(\d+)(?:…CSn-(\d+))?")


def _table(md: str, heading_prefix: str) -> list[list[str]]:
  rows, on = [], False
  for line in md.splitlines():
    if line.startswith("## "):
      on = line.startswith(heading_prefix)
      continue
    if on and line.startswith("| ") and not line.startswith("| ID") and not line.startswith("|---"):
      rows.append([c.strip() for c in line.strip().strip("|").split("|")])
  return rows


def build_cyber_tree(md: str | None = None) -> Node:
  """Goal structure of WP-K-03 §2–§3 (text trees), with evidence status from §4 and defeaters from §6."""
  md = md if md is not None else CYBER_MD.read_text(encoding="utf-8")
  evidence = {r[0]: r for r in _table(md, "## 4.")}
  status_of = {"Available": "available", "Partial": "partial", "Missing": "missing"}
  nodes: dict[str, Node] = {}
  root: Node | None = None

  def solutions(text: str, owner: Node) -> None:
    for m in CSN_RE.finditer(text):
      lo = int(m.group(1))
      hi = int(m.group(2) or lo)
      for k in range(lo, hi + 1):
        sid = f"CSn-{k:02d}"
        if sid not in evidence:
          if m.group(2):
            continue
          raise GsnError(f"{owner.ident}: evidence {sid} is not in the WP-K-03 §4 table")
        row = evidence[sid]
        if not any(c.ident == sid for c in owner.children):
          owner.children.append(Node(sid, "solution", row[1], status=status_of.get(row[4].split()[0], "missing")))

  in_block = False
  stack: list[tuple[int, Node]] = []
  last: tuple[int, Node] | None = None
  for line in md.splitlines():
    if line.startswith("```"):
      in_block = not in_block
      stack, last = [], None
      continue
    if not in_block or not line.strip():
      continue
    indent = len(line) - len(line.lstrip())
    body = line.strip()
    owners = [n for i, n in stack if i < indent]
    if body.startswith("⊙"):
      m = CY_CTX_RE.match(body)
      if not m or not owners:
        raise GsnError(f"WP-K-03: cannot attach context line {body!r}")
      cid = m.group(1)
      kind = {"CC": "C", "CA": "A", "CJ": "J"}[cid[:2]]
      owners[-1].sides.append([kind, cid, m.group(2).strip()])  # type: ignore[arg-type]
      last = (indent, owners[-1].sides[-1])  # type: ignore[assignment]
      continue
    if body.startswith("⇐"):
      if not owners:
        raise GsnError(f"WP-K-03: defeater line without a goal: {body!r}")
      owners[-1].defeaters.extend(d for d in re.findall(r"CDF-\d+", body) if d not in owners[-1].defeaters)
      continue
    arrow = body.startswith("→")
    rest = body[1:].strip() if arrow else body
    m = CY_ELEM_RE.match(rest)
    if m:
      ident, text = m.group(1), m.group(2)
      text, _, tail = text.partition("→")
      node = nodes.get(ident)
      if node is None:
        node = Node(ident, "strategy" if ident.startswith("CS") else "goal", "")
        nodes[ident] = node
      text = re.sub(r"\s+", " ", text).strip()
      if len(text) > len(node.text):
        node.text = text
      if arrow:
        if not owners:
          raise GsnError(f"WP-K-03: {ident} has no parent")
        parent = owners[-1]
        if node not in parent.children:
          parent.children.append(node)
      elif root is None:
        root = node
      solutions(tail, node)
      stack = [(i, n) for i, n in stack if i < indent] + [(indent, node)]
      last = (indent, node)
      continue
    if arrow and rest.startswith("CSR"):
      reqs, _, tail = rest.partition("→")
      owners[-1].sides.append(["C", "Requirements", re.sub(r"\s+", " ", reqs).strip()])  # type: ignore[arg-type]
      solutions(tail, owners[-1])
      continue
    if arrow and rest.startswith("CSn"):
      solutions(rest, owners[-1])
      continue
    if last is not None and indent > last[0]:
      text, _, tail = body.partition("→")
      target = last[1]
      if isinstance(target, Node):
        target.text = (target.text + " " + text.strip()).strip()
        solutions(tail, target)
      else:
        target[2] = (target[2] + " " + text.strip()).strip()
      continue
    raise GsnError(f"WP-K-03: cannot read line {body!r}")
  if root is None:
    raise GsnError("WP-K-03: no argument found")
  # The trees (⇐) and the §6 register must name the same defeater-goal pairs.
  register = {(row[0], gid) for row in _table(md, "## 6.") for gid in re.findall(r"CG\d+(?:\.\d+)*", row[3])}
  in_trees = {(d, n.ident) for n in nodes.values() for d in n.defeaters}
  if register != in_trees:
    diff = sorted(register ^ in_trees)
    raise GsnError(f"WP-K-03: §3 trees and §6 register disagree on defeaters: {diff}")
  for n in nodes.values():
    n.sides = [tuple(sd) for sd in n.sides]  # type: ignore[misc]
    n.undeveloped = n.kind == "goal" and not n.children
  return root


# ---------------------------------------------------------------- sheets

def paginate(root: Node) -> list[Node]:
  """One sheet per sub-argument: every goal below the top that is developed further (by a
  strategy or sub-goals) starts a sheet, the layout of WP-K-01 §3–§4 and WP-K-03 §2–§3.
  Sheets are numbered in depth-first order."""
  sheets: list[Node] = []

  def visit(node: Node, sheet_no: int) -> None:
    for c in node.children:
      if c.kind == "goal" and any(k.kind != "solution" for k in c.children):
        sheets.append(c)
        c.sheet_link = len(sheets)
        c.sheet_from = sheet_no
        visit(c, c.sheet_link)
      else:
        visit(c, sheet_no)

  sheets.append(root)
  visit(root, 1)
  return sheets


# ---------------------------------------------------------------- drawing

GOAL_W = 244
STRAT_W = 262
SOL_D = 48
SOL_W = 120
SIDE_W = 196
GAP_X = 24
LEVEL_GAP = 54
MARGIN = 40
HEADER_H = 78
LINE_H = 14
MIN_WIDTH = 1180

INK, MUTED, WIRE, HAIR, NAVY = "#1d2433", "#5b6475", "#7d8798", "#d9dee6", "#0f2a44"
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, monospace"
STRATEGY = ("#e4e7fb", "#4b5bb7")      # fill, stroke
SIDE_STYLE = {                           # kind -> fill, stroke, marker colour
  "C": ("#dfeaf6", "#6f8fb5", "#2f557f"),
  "A": ("#fbeccd", "#c9963a", "#7a4f00"),
  "J": ("#dcefe0", "#5f9f6d", "#245a31"),
}
SUPPORT = {   # evidence roll-up of a goal's subtree -> stripe colour, label, card tint, card border
  "available": ("#2e7d32", "all evidence available", "#edf7ee", "#9fcfa3"),
  "partial": ("#e0a21b", "evidence partial", "#fdf5e1", "#ecc77a"),
  "missing": ("#c62828", "evidence missing", "#fdecec", "#eba9a9"),
  "none": ("#8a93a3", "not developed", "#f1f3f6", "#c9cfd8"),
}


def wrap(text: str, width: int) -> list[str]:
  out, line = [], ""
  for word in text.split():
    while len(word) > width:
      if line:
        out.append(line)
        line = ""
      out.append(word[:width])
      word = word[width:]
    if not line:
      line = word
    elif len(line) + 1 + len(word) <= width:
      line += " " + word
    else:
      out.append(line)
      line = word
  if line:
    out.append(line)
  return out


def _clip(lines: list[str], n: int, width: int) -> list[str]:
  if len(lines) <= n:
    return lines
  lines = lines[:n]
  lines[-1] = lines[-1][:width - 1] + "…"
  return lines


def support(node: Node) -> str:
  """Worst evidence status of the solutions below a goal or strategy, across all sheets."""
  statuses = set()

  def visit(n: Node) -> None:
    if n.kind == "solution":
      statuses.add(n.status)
    for c in n.children:
      visit(c)

  visit(node)
  for s in ("missing", "partial", "available"):
    if s in statuses:
      return s
  return "none"


@dataclass(eq=False)
class Box:
  node: Node
  w: float
  h: float                  # main shape height (solution: circle + caption)
  lines: list[str]
  side_boxes: list[tuple[str, str, list[str], float]]   # kind, id, lines, height
  side_h: float = 0.0
  x: float = 0.0            # left edge of the main shape
  y: float = 0.0
  children: list[Box] = field(default_factory=list)
  chips: list[list[tuple[str, str, float]]] = field(default_factory=list)   # rows of (kind, label, width)

  @property
  def foot(self) -> float:
    """Horizontal space this node needs, including its side elements."""
    return self.w + (GAP_X / 2 + SIDE_W if self.side_boxes else 0)


def _chip_w(label: str) -> float:
  return 14 + 5.7 * len(label)


def _chip_rows(chips: list[tuple[str, str]], width: float) -> list[list[tuple[str, str, float]]]:
  rows: list[list[tuple[str, str, float]]] = []
  row: list[tuple[str, str, float]] = []
  used = 0.0
  for kind, label in chips:
    w = _chip_w(label)
    if row and used + w > width:
      rows.append(row)
      row, used = [], 0.0
    row.append((kind, label, w))
    used += w + 5
  if row:
    rows.append(row)
  return rows


def make_box(node: Node, sheet_root: Node) -> Box:
  if node.kind == "solution":
    lines = _clip(wrap(node.text, 21), 4, 21)
    h = SOL_D + 8 + LINE_H * len(lines)
    box = Box(node, SOL_W, h, lines, [])
  else:
    width = GOAL_W if node.kind == "goal" else STRAT_W
    chars = 36 if node.kind == "goal" else 34
    lines = _clip(wrap(node.text, chars), 9, chars)
    chips = [("df", d) for d in node.defeaters]
    if node is not sheet_root and node.sheet_link is not None:
      chips.append(("sheet", f"→ sheet {node.sheet_link}"))
    if node is sheet_root and node.sheet_from is not None:
      chips.append(("sheet", f"from sheet {node.sheet_from}"))
    rows = _chip_rows(chips, width - 34)
    h = 30 + LINE_H * len(lines) + 22 * len(rows) + 12
    box = Box(node, width, h, lines, [], chips=rows)
  sides = []
  for kind, cid, text in node.sides:
    sl = _clip(wrap(text, 29), 6, 29)
    sides.append((kind, cid, sl, 30 + LINE_H * len(sl) + 10))
  box.side_boxes = sides
  box.side_h = sum(s[3] for s in sides) + 10 * max(0, len(sides) - 1)
  developed_here = not (node is not sheet_root and node.sheet_link is not None)
  if developed_here:
    box.children = [make_box(c, sheet_root) for c in node.children]
  return box


def layout(root: Box) -> tuple[float, float]:
  level_h: dict[int, float] = {}

  def heights(b: Box, d: int):
    extra = 22 if b.node.undeveloped else 0
    level_h[d] = max(level_h.get(d, 0), max(b.h + extra, b.side_h))
    for c in b.children:
      heights(c, d + 1)

  heights(root, 0)
  level_y = {0: HEADER_H + 36}
  for d in range(1, max(level_h) + 1):
    level_y[d] = level_y[d - 1] + level_h[d - 1] + LEVEL_GAP
  cursor = [MARGIN]

  def place(b: Box, d: int):
    b.y = level_y[d]
    if not b.children:
      b.x = cursor[0]
      cursor[0] += b.foot + GAP_X
      return
    start = cursor[0]
    for c in b.children:
      place(c, d + 1)
    first, last = b.children[0], b.children[-1]
    center = (first.x + first.w / 2 + last.x + last.w / 2) / 2
    b.x = max(start, center - b.w / 2)
    cursor[0] = max(cursor[0], b.x + b.foot + GAP_X)

  place(root, 0)
  depth = max(level_h)
  return cursor[0] - GAP_X + MARGIN, level_y[depth] + level_h[depth] + 24


def _arrow(x1, y1, x2, y2, hollow: bool) -> str:
  ang = math.atan2(y2 - y1, x2 - x1)
  ax, ay = x2 - 10 * math.cos(ang - 0.42), y2 - 10 * math.sin(ang - 0.42)
  bx, by = x2 - 10 * math.cos(ang + 0.42), y2 - 10 * math.sin(ang + 0.42)
  cls = "wc" if hollow else "w"
  head = (f'fill="#fff" stroke="{WIRE}" stroke-width="1.3"' if hollow else f'fill="{INK}" stroke="{INK}" stroke-width="1"')
  return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}"/>' +
          f'<path d="M{x2:.1f},{y2:.1f} L{ax:.1f},{ay:.1f} L{bx:.1f},{by:.1f} Z" {head} stroke-linejoin="round"/>')


def _chip(out: list[str], x: float, y: float, kind: str, label: str, w: float) -> None:
  bg, fg = ("#c62828", "#fff") if kind == "df" else ("#e6e9ef", "#334155")
  out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="16" rx="8" fill="{bg}"/>')
  out.append(f'<text x="{x + w / 2:.1f}" y="{y + 11.5:.1f}" class="chip" fill="{fg}">{escape(label)}</text>')


def _side(kind: str, cid: str, lines: list[str], x: float, y: float, h: float, out: list[str]) -> None:
  fill, stroke, mark = SIDE_STYLE.get(kind, SIDE_STYLE["C"])
  if kind == "C":
    out.append(f'<rect x="{x}" y="{y}" width="{SIDE_W}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
  else:
    out.append(f'<ellipse cx="{x + SIDE_W / 2}" cy="{y + h / 2}" rx="{SIDE_W / 2}" ry="{h / 2 + 5}" fill="{fill}" ' +
               f'stroke="{stroke}" stroke-width="1.2"/>')
    out.append(f'<circle cx="{x + SIDE_W - 8}" cy="{y + h + 2}" r="9" fill="{mark}"/>')
    out.append(f'<text x="{x + SIDE_W - 8}" y="{y + h + 6}" class="aj">{kind}</text>')
  ty = y + 21
  label = cid if cid != "A" else "Assumption"
  out.append(f'<text x="{x + SIDE_W / 2}" y="{ty}" class="cid" fill="{mark}">{escape(label)}</text>')
  for ln in lines:
    ty += LINE_H
    out.append(f'<text x="{x + SIDE_W / 2}" y="{ty}" class="cs">{escape(ln)}</text>')


def _solution(out: list[str], cx: float, cy: float, r: float, status: str, ident: str | None) -> None:
  fill, stroke, _ = STATUS_STYLE.get(status, ("#eee", "#555", status))
  dash = ' stroke-dasharray="5 3"' if status == "missing" else ""
  if status != "missing":
    out.append(f'<circle cx="{cx}" cy="{cy + 2}" r="{r}" fill="#0f172a" opacity=".10"/>')
  out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.8"{dash}/>')
  if status == "available":
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r - 4}" fill="none" stroke="#ffffff" stroke-opacity=".35" stroke-width="1.2"/>')
  if ident:
    tcol = "#fff" if status == "available" else ("#b3261e" if status == "missing" else INK)
    out.append(f'<text x="{cx}" y="{cy + 4}" class="sid" fill="{tcol}">{escape(ident)}</text>')


def draw(b: Box, out: list[str]) -> None:
  n = b.node
  x, y, cx = b.x, b.y, b.x + b.w / 2
  if n.kind == "solution":
    r = SOL_D / 2
    _solution(out, cx, y + r, r, n.status, n.ident)
    ty = y + SOL_D + 6
    for ln in b.lines:
      ty += LINE_H
      out.append(f'<text x="{cx}" y="{ty - 2}" class="cs">{escape(ln)}</text>')
  else:
    if n.kind == "goal":
      stripe, _, tint, border = SUPPORT["none" if n.undeveloped else support(n)]
      out.append(f'<rect x="{x + 1.5}" y="{y + 2.5}" width="{b.w}" height="{b.h}" rx="4" class="shadow"/>')
      out.append(f'<rect x="{x}" y="{y}" width="{b.w}" height="{b.h}" rx="4" fill="{tint}" stroke="{border}" stroke-width="1.2"/>')
      out.append(f'<path d="M{x + 4},{y} H{x + b.w - 4} A4,4 0 0 1 {x + b.w},{y + 4} V{y + 6} H{x} V{y + 4} ' +
                 f'A4,4 0 0 1 {x + 4},{y} Z" fill="{stripe}"/>')
      tx, anchor = x + 14, "start"
      kind_x = x + b.w - 14
    else:
      k = 16
      pts = f"M{x + k},{y} L{x + b.w},{y} L{x + b.w - k},{y + b.h} L{x},{y + b.h} Z"
      out.append(f'<path d="{pts}" transform="translate(1.5 2.5)" class="shadow"/>')
      out.append(f'<path d="{pts}" fill="{STRATEGY[0]}" stroke="{STRATEGY[1]}" stroke-width="1.4"/>')
      tx, anchor = x + k + 12, "start"
      kind_x = x + b.w - 14
    ty = y + 25
    out.append(f'<text x="{tx}" y="{ty}" class="id" text-anchor="{anchor}">{escape(n.ident)}</text>')
    out.append(f'<text x="{kind_x}" y="{ty}" class="kind">{"GOAL" if n.kind == "goal" else "STRATEGY"}</text>')
    for ln in b.lines:
      ty += LINE_H
      out.append(f'<text x="{tx}" y="{ty}" class="d">{escape(ln)}</text>')
    ty += 8
    for row in b.chips:
      bx = tx
      for kind, label, w in row:
        _chip(out, bx, ty, kind, label, w)
        bx += w + 5
      ty += 22
    if n.undeveloped:
      dy = y + b.h
      out.append(f'<path d="M{cx},{dy + 2} L{cx + 10},{dy + 11} L{cx},{dy + 20} L{cx - 10},{dy + 11} Z" fill="#fff" ' +
                 f'stroke="{INK}" stroke-width="1.4"/>')
  # side elements (InContextOf)
  if b.side_boxes:
    sy = y
    sx = x + b.w + GAP_X / 2
    spine = x + b.w + 5
    mids = []
    for kind, cid, lines, h in b.side_boxes:
      _side(kind, cid, lines, sx, sy, h, out)
      mids.append(sy + h / 2)
      sy += h + 10
    start = y + min(b.h / 2, 22)
    out.append(f'<line x1="{x + b.w}" y1="{start}" x2="{spine}" y2="{start}" class="wc"/>')
    out.append(f'<line x1="{spine}" y1="{min(mids + [start])}" x2="{spine}" y2="{max(mids + [start])}" class="wc"/>')
    for m in mids:
      out.append(_arrow(spine, m, sx - 1, m, hollow=True))
  # SupportedBy
  if b.children:
    top_y = y + b.h
    # below the side column too, so the bus never crosses a context box
    bus = y + max(b.h + (22 if n.undeveloped else 0), b.side_h) + LEVEL_GAP / 2 - 4
    out.append(f'<line x1="{cx}" y1="{top_y}" x2="{cx}" y2="{bus}" class="w"/>')
    xs = [c.x + c.w / 2 for c in b.children]
    out.append(f'<line x1="{min(xs + [cx])}" y1="{bus}" x2="{max(xs + [cx])}" y2="{bus}" class="w"/>')
    for c in b.children:
      ccx = c.x + c.w / 2
      out.append(_arrow(ccx, bus, ccx, c.y - 1, hollow=False))
    for c in b.children:
      draw(c, out)


def _walk(b: Box):
  yield b
  for c in b.children:
    yield from _walk(c)


def legend(x: float, y: float) -> tuple[list[str], float]:
  out = [f'<text x="{x}" y="{y + 14}" class="lh">Notation · GSN Community Standard v3</text>']

  def item(kind: str, cx: float, top: float, label: str) -> None:
    if kind == "goal":
      out.append(f'<rect x="{cx - 26}" y="{top}" width="52" height="30" rx="4" fill="{SUPPORT["partial"][2]}" ' +
                 f'stroke="{SUPPORT["partial"][3]}"/>')
      out.append(f'<rect x="{cx - 26}" y="{top}" width="52" height="5" rx="2" fill="{SUPPORT["partial"][0]}"/>')
    elif kind == "strategy":
      out.append(f'<path d="M{cx - 18},{top} L{cx + 28},{top} L{cx + 18},{top + 30} L{cx - 28},{top + 30} Z" ' +
                 f'fill="{STRATEGY[0]}" stroke="{STRATEGY[1]}" stroke-width="1.4"/>')
    elif kind in STATUS_STYLE:
      _solution(out, cx, top + 15, 14, kind, None)
    elif kind == "C":
      fill, stroke, _ = SIDE_STYLE["C"]
      out.append(f'<rect x="{cx - 26}" y="{top + 1}" width="52" height="28" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
    elif kind in ("A", "J"):
      fill, stroke, mark = SIDE_STYLE[kind]
      out.append(f'<ellipse cx="{cx}" cy="{top + 15}" rx="27" ry="14" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
      out.append(f'<text x="{cx}" y="{top + 19}" class="cid" fill="{mark}">{kind}</text>')
    else:
      out.append(f'<path d="M{cx},{top + 4} L{cx + 11},{top + 15} L{cx},{top + 26} L{cx - 11},{top + 15} Z" ' +
                 f'fill="#fff" stroke="{INK}" stroke-width="1.4"/>')
    out.append(f'<text x="{cx}" y="{top + 48}" class="s" text-anchor="middle">{label}</text>')

  row1 = [("goal", "Goal"), ("strategy", "Strategy"), ("C", "Context"), ("A", "Assumption"), ("J", "Justification"),
          ("undev", "Undeveloped")]
  for i, (kind, label) in enumerate(row1):
    item(kind, x + 34 + 92 * i, y + 30, label)
  sy = y + 102
  out.append(f'<text x="{x}" y="{sy + 19}" class="lb">Solution</text>')
  for i, (kind, label) in enumerate((("available", "Available"), ("partial", "Partial"), ("missing", "Missing"))):
    item(kind, x + 126 + 92 * i, sy, label)
  ay = sy + 80
  out.append(_arrow(x, ay, x + 44, ay, hollow=False))
  out.append(f'<text x="{x + 54}" y="{ay + 4}" class="s">SupportedBy</text>')
  out.append(_arrow(x + 150, ay, x + 194, ay, hollow=True))
  out.append(f'<text x="{x + 204}" y="{ay + 4}" class="s">InContextOf</text>')
  _chip(out, x + 300, ay - 8, "df", "DF-nn", _chip_w("DF-nn"))
  out.append(f'<text x="{x + 300 + _chip_w("DF-nn") + 8}" y="{ay + 4}" class="s">open defeater on the goal</text>')
  gy = ay + 30
  out.append(f'<text x="{x}" y="{gy}" class="lb">Goal colour: the evidence below it, on every sheet</text>')
  gx = x
  for key in ("available", "partial", "missing", "none"):
    colour, label, tint, border = SUPPORT[key]
    out.append(f'<rect x="{gx}" y="{gy + 8}" width="26" height="14" rx="3" fill="{tint}" stroke="{border}"/>')
    out.append(f'<rect x="{gx}" y="{gy + 8}" width="26" height="4" rx="2" fill="{colour}"/>')
    out.append(f'<text x="{gx + 32}" y="{gy + 19}" class="s">{label}</text>')
    gx += 32 + 5.6 * len(label) + 16
  return out, gy + 30 - y


def _sheet_map(sheets: list[Node], current: int, x: float, y: float, w: float, h: float) -> list[str]:
  """Small tree of the case's sheets (parent = the sheet that develops into it), current one filled."""
  depth = {1: 0}
  for no, root in enumerate(sheets[1:], 2):
    depth[no] = depth[root.sheet_from] + 1
  levels: dict[int, list[int]] = {}
  for no in range(1, len(sheets) + 1):
    levels.setdefault(depth[no], []).append(no)
  dy = min(34, (h - 22) / max(1, len(levels) - 1)) if len(levels) > 1 else 0
  pos = {}
  for d, nos in levels.items():
    step = w / len(nos)
    for i, no in enumerate(nos):
      pos[no] = (x + step * (i + 0.5), y + 11 + d * dy)
  out = []
  for no, root in enumerate(sheets[1:], 2):
    (px, py), (cx, cy) = pos[root.sheet_from], pos[no]
    out.append(f'<line x1="{px:.1f}" y1="{py + 10:.1f}" x2="{cx:.1f}" y2="{cy - 10:.1f}" stroke="{WIRE}" stroke-width="1.3"/>')
  for no, (cx, cy) in pos.items():
    cur = no == current
    out.append(f'<rect x="{cx - 14:.1f}" y="{cy - 10:.1f}" width="28" height="20" rx="5" ' +
               f'fill="{NAVY if cur else "#fff"}" stroke="{NAVY}" stroke-width="1.3"/>')
    out.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" class="mm" fill="{"#fff" if cur else NAVY}">{no}</text>')
  return out


def render_sheet(sheets: list[Node], no: int, case: str = "Safety case", source: str = "", doc_id: str = "") -> str:
  root = sheets[no - 1]
  total = len(sheets)
  box = make_box(root, root)
  width, height = layout(box)
  width = max(width, MIN_WIDTH)
  body: list[str] = []
  draw(box, body)
  counts = dict.fromkeys(STATUS_STYLE, 0)
  for b in _walk(box):
    if b.node.kind == "solution" and b.node.status in counts:
      counts[b.node.status] += 1

  fy = height + 20
  leg, lh = legend(MARGIN, fy)
  tb_w, tb_h = 520, 250
  tb_x = width - MARGIN - tb_w
  split = tb_x + 330
  foot = [
    f'<rect x="{tb_x}" y="{fy}" width="{tb_w}" height="{tb_h}" rx="10" fill="#fff" stroke="{HAIR}"/>',
    f'<line x1="{tb_x}" y1="{fy + 46}" x2="{tb_x + tb_w}" y2="{fy + 46}" stroke="{HAIR}"/>',
    f'<line x1="{split}" y1="{fy + 46}" x2="{split}" y2="{fy + tb_h}" stroke="{HAIR}"/>',
    f'<text x="{tb_x + 18}" y="{fy + 29}" class="tbh">LionDriver · {escape(case)}</text>',
    f'<rect x="{tb_x + tb_w - 150}" y="{fy + 14}" width="132" height="20" rx="10" fill="#fff4e0" stroke="#f0c36d"/>',
    f'<text x="{tb_x + tb_w - 84}" y="{fy + 28}" class="chip" fill="#8a5a00">DRAFT · NOT VERIFIED</text>',
  ]
  rows = [
    ("Argument from", root.ident),
    ("Source", source or "case records and WP-K-01 contexts"),
    ("Generated by", "gsn_diagrams.py"),
    ("Edit", "the source, not this file"),
  ]
  ry = fy + 72
  for k, v in rows:
    foot.append(f'<text x="{tb_x + 18}" y="{ry}" class="k">{k.upper()}</text>')
    for i, ln in enumerate(wrap(v, 30)[:2]):
      foot.append(f'<text x="{tb_x + 122}" y="{ry + 15 * i}" class="v">{escape(ln)}</text>')
    ry += 26 + 15 * (min(2, len(wrap(v, 30))) - 1)
  # evidence bar on this sheet
  total_sol = sum(counts.values())
  foot.append(f'<text x="{tb_x + 18}" y="{ry + 4}" class="k">EVIDENCE ON THIS SHEET</text>')
  bx, bw = tb_x + 18, 294
  if total_sol:
    cx = bx
    for s in ("available", "partial", "missing"):
      if counts[s]:
        w = bw * counts[s] / total_sol
        fill, stroke, _ = STATUS_STYLE[s]
        foot.append(f'<rect x="{cx:.1f}" y="{ry + 12}" width="{w:.1f}" height="10" fill="{fill}" stroke="{stroke}" stroke-width=".8"/>')
        cx += w
  foot.append(f'<text x="{bx}" y="{ry + 38}" class="s">{counts["available"]} available · {counts["partial"]} partial · ' +
              f'{counts["missing"]} missing</text>')
  foot.append(f'<text x="{split + 16}" y="{fy + 70}" class="k">SHEETS</text>')
  foot += _sheet_map(sheets, no, split + 10, fy + 86, tb_x + tb_w - split - 20, tb_h - 100)
  total_h = max(fy + lh, fy + tb_h) + MARGIN

  css = "".join([
    f".id{{font:700 13px {MONO};fill:{INK}}}",
    f".kind{{font:600 9px {SANS};letter-spacing:.1em;fill:#8a93a3;text-anchor:end}}",
    f".d{{font:400 11.5px {SANS};fill:#2b3343}}",
    f".sid{{font:700 11px {MONO};text-anchor:middle}}",
    f".cid{{font:700 11px {MONO};text-anchor:middle}}",
    f".cs{{font:400 10.5px {SANS};text-anchor:middle;fill:#3c4556}}",
    f".aj{{font:700 10px {SANS};fill:#fff;text-anchor:middle}}",
    f".chip{{font:600 9.5px {SANS};text-anchor:middle}}",
    f".eyebrow{{font:600 12px {SANS};letter-spacing:.14em;fill:#9fb7d1}}",
    f".title{{font:600 21px {SANS};fill:#fff}}",
    f".hc{{font:600 12px {SANS};letter-spacing:.04em;fill:#fff;text-anchor:middle}}",
    f".lh{{font:600 13px {SANS};fill:{INK}}}",
    f".lb{{font:600 12px {SANS};fill:{INK}}}",
    f".s{{font:400 11px {SANS};fill:{MUTED}}}",
    f".tbh{{font:700 14px {SANS};fill:{NAVY}}}",
    f".k{{font:600 9px {SANS};letter-spacing:.12em;fill:#8a93a3}}",
    f".v{{font:400 11.5px {SANS};fill:{INK}}}",
    f".mm{{font:700 11px {MONO};text-anchor:middle}}",
    f".w{{stroke:{INK};stroke-width:1.3}}",
    f".wc{{stroke:{WIRE};stroke-width:1.2;stroke-dasharray:4 3}}",
    ".shadow{fill:#0f172a;opacity:.06}",
  ])
  chip_w = 200
  summary = wrap(root.text, 72)
  title = f"{root.ident} · {summary[0]}{'…' if len(summary) > 1 else ''}"
  head = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{total_h:.0f}" viewBox="0 0 {width:.0f} {total_h:.0f}">',
    f'<title>{escape(case)} (GSN), sheet {no} of {total}: argument from {escape(root.ident)}</title>',
    f'<style>{css}</style>',
    '<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">' +
    '<circle cx="1" cy="1" r="1" fill="#e3e7ee"/></pattern></defs>',
    '<rect width="100%" height="100%" fill="#f7f8fa"/>',
    f'<rect y="{HEADER_H}" width="100%" height="{total_h - HEADER_H:.0f}" fill="url(#dots)"/>',
    f'<rect width="100%" height="{HEADER_H}" fill="{NAVY}"/>',
    f'<text x="{MARGIN}" y="32" class="eyebrow">GSN · {escape(case.upper())}{" · " + escape(doc_id) if doc_id else ""}</text>',
    f'<text x="{MARGIN}" y="59" class="title">{escape(title)}</text>',
    f'<rect x="{width - MARGIN - chip_w:.0f}" y="21" width="{chip_w}" height="36" rx="18" fill="#ffffff14" stroke="#ffffff40"/>',
    f'<text x="{width - MARGIN - chip_w / 2:.0f}" y="44" class="hc">Sheet {no} of {total}</text>',
  ]
  return "\n".join(head + body + leg + foot) + "\n</svg>\n"


CASES = [
  # (prefix, case name, source label, tree builder, document, document ID)
  ("gsn", "Safety case", "case records (assurance/case-records/) and WP-K-01 contexts", build_tree,
   "[WP-K-01](../WP-K-01-safety-case.md)", "WP-K-01"),
  ("gsn-cs", "Cybersecurity case", "WP-K-03 §2–§4, §6 (text trees and tables)", build_cyber_tree,
   "[WP-K-03](../WP-K-03-cybersecurity-case.md)", "WP-K-03"),
]


def build() -> dict[str, str]:
  outputs: dict[str, str] = {}
  index = [
    "# Safety and cybersecurity case diagrams (GSN)",
    "",
    "Generated by `assurance/case-records/tools/gsn_diagrams.py` (CI runs `--check`). The documents stay the reviewed " +
    "arguments; edit them, or the case records, and regenerate.",
    "",
    "- **Safety case** ([WP-K-01](../WP-K-01-safety-case.md)): structure from the case records in " +
    "[`assurance/case-records/`](../../case-records/README.md), contexts from WP-K-01 §3–§4.",
    "- **Cybersecurity case** ([WP-K-03](../WP-K-03-cybersecurity-case.md)): structure from the text trees of " +
    "§2–§3, evidence status from §4, defeaters from §6. It supports G4 of the safety case.",
    "",
    "| Case | Sheet | Argument from | Goals | Solutions |",
    "|---|---|---|---|---|",
  ]
  first = None
  for prefix, case, source, builder, doc, doc_id in CASES:
    sheets = paginate(builder())
    for no, root_node in enumerate(sheets, 1):
      name = f"{prefix}-{no}-{root_node.ident}.svg"
      outputs[name] = render_sheet(sheets, no, case, source, doc_id)
      box = make_box(root_node, root_node)
      goals = sum(1 for b in _walk(box) if b.node.kind == "goal")
      sols = sum(1 for b in _walk(box) if b.node.kind == "solution")
      index.append(f"| {doc} | [{no}]({name}) | {root_node.ident} | {goals} | {sols} |")
      first = first or (name, root_node.ident, case)
  index += ["", "Notation: goal = rectangle; strategy = parallelogram; solution = circle (green available, " +
            "amber partial, white dashed missing); context = rounded box; assumption / justification = oval " +
            "(A / J); diamond = undeveloped goal. Solid arrows are SupportedBy, hollow arrows InContextOf. " +
            "The colour of a goal (stripe and tint) is the worst evidence status of all solutions below it, on every " +
            "sheet (green all available, amber partial, red missing, grey not developed). " +
            "Defeaters (open counter-evidence, WP-K-01 §7, WP-K-03 §6) are listed in red on the goal they " +
            "undermine. In the cybersecurity case the requirements that refine a goal (CSR-nnn) are shown as " +
            "a context.", ""]
  name, ident, case = first
  index[7:7] = [f"![First sheet of the {case.lower()}: the top goal {ident} with the strategies and goals that support it, "
                "each goal coloured by the worst evidence status below it, and open defeaters in red on the goal they "
                f"undermine]({name})", "",
                "*Sheet 1, the top of the argument; the notation is explained under the table and every sheet is "
                "listed in it.*", ""]
  outputs["README.md"] = "\n".join(index)
  return outputs


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except GsnError as e:
    print(f"gsn_diagrams: {e}", file=sys.stderr)
    return 1
  existing = {p.name for p in OUT_DIR.glob("gsn-*.svg")} if OUT_DIR.exists() else set()
  if "--check" in argv:
    stale = [n for n, c in outputs.items()
             if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text(encoding="utf-8") != c]
    extra = sorted(existing - set(outputs))
    if stale or extra:
      for n in stale + extra:
        print(f"stale: {n}", file=sys.stderr)
      print("run: python3 assurance/case-records/tools/gsn_diagrams.py", file=sys.stderr)
      return 1
    print(f"gsn_diagrams: {len(outputs) - 1} sheet(s) current")
    return 0
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  for n in sorted(existing - set(outputs)):
    (OUT_DIR / n).unlink()
  for n, c in outputs.items():
    (OUT_DIR / n).write_text(c, encoding="utf-8")
  print(f"gsn_diagrams: wrote {len(outputs) - 1} sheet(s) and README.md")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
