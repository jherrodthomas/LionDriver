#!/usr/bin/env python3
"""Draw the safety case (WP-K-01) as GSN diagrams (GSN Community Standard v3 notation).

Structure comes from the case records (assurance/case/): goals (claims), strategies
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

    python3 assurance/case/tools/gsn_diagrams.py            # write the SVGs and README.md
    python3 assurance/case/tools/gsn_diagrams.py --check    # fail if they are out of date

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


# ---------------------------------------------------------------- sheets

def paginate(root: Node) -> list[Node]:
  """One sheet per sub-argument: every goal below the top that has a strategy starts a sheet
  (the layout of WP-K-01 §3 and §4.1…§4.5). Sheets are numbered in depth-first order."""
  sheets: list[Node] = []

  def visit(node: Node, sheet_no: int) -> None:
    for c in node.children:
      if c.kind == "goal" and any(k.kind == "strategy" for k in c.children):
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

GOAL_W = 230
STRAT_W = 250
SOL_D = 46
SOL_W = 112
SIDE_W = 190
GAP_X = 22
LEVEL_GAP = 46
MARGIN = 30
LINE_H = 12.5


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
  tags: list[tuple[str, str]] = field(default_factory=list)

  @property
  def foot(self) -> float:
    """Horizontal space this node needs, including its side elements."""
    return self.w + (GAP_X / 2 + SIDE_W if self.side_boxes else 0)


def make_box(node: Node, sheet_root: Node) -> Box:
  tags: list[tuple[str, str]] = []
  if node.kind == "solution":
    lines = _clip(wrap(node.text, 20), 4, 20)
    h = SOL_D + 6 + LINE_H * len(lines)
    box = Box(node, SOL_W, h, lines, [])
  else:
    width = GOAL_W if node.kind == "goal" else STRAT_W
    chars = 38 if node.kind == "goal" else 36
    lines = _clip(wrap(node.text, chars), 9, chars)
    if node.defeaters:
      tags.append(("df", "defeaters: " + ", ".join(node.defeaters)))
    if node is not sheet_root and node.sheet_link is not None:
      tags.append(("sheet", f"developed on sheet {node.sheet_link}"))
    if node is sheet_root and node.sheet_from is not None:
      tags.append(("sheet", f"from sheet {node.sheet_from}"))
    tag_lines = sum(len(wrap(t, 44)) for _, t in tags)
    h = 8 + 14 + LINE_H * len(lines) + 15 * tag_lines + 8
    box = Box(node, width, h, lines, [], tags=tags)
  sides = []
  for kind, cid, text in node.sides:
    sl = _clip(wrap(text, 30), 6, 30)
    sides.append((kind, cid, sl, 8 + 13 + LINE_H * len(sl) + 8))
  box.side_boxes = sides
  box.side_h = sum(s[3] for s in sides) + 8 * max(0, len(sides) - 1)
  developed_here = not (node is not sheet_root and node.sheet_link is not None)
  if developed_here:
    box.children = [make_box(c, sheet_root) for c in node.children]
  return box


def layout(root: Box) -> tuple[float, float]:
  level_h: dict[int, float] = {}

  def heights(b: Box, d: int):
    extra = 16 if b.node.undeveloped else 0
    level_h[d] = max(level_h.get(d, 0), max(b.h + extra, b.side_h))
    for c in b.children:
      heights(c, d + 1)

  heights(root, 0)
  level_y = {0: MARGIN + 40}
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
  return cursor[0] - GAP_X + MARGIN, level_y[depth] + level_h[depth] + MARGIN


def _arrow(x1, y1, x2, y2, hollow: bool) -> str:

  ang = math.atan2(y2 - y1, x2 - x1)
  ax, ay = x2 - 9 * math.cos(ang - 0.4), y2 - 9 * math.sin(ang - 0.4)
  bx, by = x2 - 9 * math.cos(ang + 0.4), y2 - 9 * math.sin(ang + 0.4)
  fill = "#fff" if hollow else "#111"
  return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="w"/>' +
          f'<path d="M{x2:.1f},{y2:.1f} L{ax:.1f},{ay:.1f} L{bx:.1f},{by:.1f} Z" fill="{fill}" stroke="#111" stroke-width="1"/>')


def _side(kind: str, cid: str, lines: list[str], x: float, y: float, h: float, out: list[str]) -> None:
  if kind == "C":
    out.append(f'<rect x="{x}" y="{y}" width="{SIDE_W}" height="{h}" rx="14" class="ctx"/>')
  else:
    out.append(f'<ellipse cx="{x + SIDE_W / 2}" cy="{y + h / 2}" rx="{SIDE_W / 2}" ry="{h / 2 + 4}" class="ctx"/>')
    out.append(f'<text x="{x + SIDE_W - 4}" y="{y + h + 6}" class="aj">{kind}</text>')
  ty = y + 8 + 10
  label = cid if cid != "A" else "Assumption"
  out.append(f'<text x="{x + SIDE_W / 2}" y="{ty}" class="cid">{escape(label)}</text>')
  for ln in lines:
    ty += LINE_H
    out.append(f'<text x="{x + SIDE_W / 2}" y="{ty}" class="cs">{escape(ln)}</text>')


def draw(b: Box, out: list[str]) -> None:
  n = b.node
  x, y, cx = b.x, b.y, b.x + b.w / 2
  if n.kind == "solution":
    fill, stroke, _ = STATUS_STYLE.get(n.status, ("#eee", "#555", n.status))
    dash = ' stroke-dasharray="4 3"' if n.status == "missing" else ""
    r = SOL_D / 2
    out.append(f'<circle cx="{cx}" cy="{y + r}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{dash}/>')
    tcol = "#fff" if n.status == "available" else "#111"
    out.append(f'<text x="{cx}" y="{y + r + 4}" class="sid" fill="{tcol}">{escape(n.ident)}</text>')
    ty = y + SOL_D + 4
    for ln in b.lines:
      ty += LINE_H
      out.append(f'<text x="{cx}" y="{ty - 2}" class="cs">{escape(ln)}</text>')
  else:
    if n.kind == "goal":
      out.append(f'<rect x="{x}" y="{y}" width="{b.w}" height="{b.h}" class="g"/>')
    else:
      k = 14
      out.append(f'<path d="M{x + k},{y} L{x + b.w},{y} L{x + b.w - k},{y + b.h} L{x},{y + b.h} Z" class="g"/>')
    ty = y + 8 + 11
    out.append(f'<text x="{cx}" y="{ty}" class="id">{escape(n.ident)}</text>')
    ty += 3
    for ln in b.lines:
      ty += LINE_H
      out.append(f'<text x="{cx}" y="{ty - 2}" class="d">{escape(ln)}</text>')
    for kind, t in b.tags:
      for ln in wrap(t, 44):
        ty += 15
        cls = "df" if kind == "df" else "sh"
        out.append(f'<text x="{cx}" y="{ty - 3}" class="{cls}">{escape(ln)}</text>')
    if n.undeveloped:
      dy = y + b.h
      out.append(f'<path d="M{cx},{dy} L{cx + 9},{dy + 8} L{cx},{dy + 16} L{cx - 9},{dy + 8} Z" fill="#fff" stroke="#111" stroke-width="1.2"/>')
  # side elements (InContextOf)
  if b.side_boxes:
    sy = y
    sx = x + b.w + GAP_X / 2
    spine = x + b.w + 4
    mids = []
    for kind, cid, lines, h in b.side_boxes:
      _side(kind, cid, lines, sx, sy, h, out)
      mids.append(sy + h / 2)
      sy += h + 8
    start = y + min(b.h / 2, 20)
    out.append(f'<line x1="{x + b.w}" y1="{start}" x2="{spine}" y2="{start}" class="w"/>')
    out.append(f'<line x1="{spine}" y1="{min(mids + [start])}" x2="{spine}" y2="{max(mids + [start])}" class="w"/>')
    for m in mids:
      out.append(_arrow(spine, m, sx - 1, m, hollow=True))
  # SupportedBy
  if b.children:
    top_y = y + b.h
    bus = top_y + LEVEL_GAP / 2 - 4
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
  out = [f'<text x="{x}" y="{y + 12}" class="h">Notation (GSN Community Standard v3)</text>']
  cy = y + 26
  items = [
    ("goal", "Goal (claim)"), ("strategy", "Strategy (argument)"),
    ("available", "Solution: evidence available"), ("partial", "Solution: evidence partial"),
    ("missing", "Solution: evidence missing"), ("C", "Context"), ("A", "Assumption (A) / justification (J)"),
    ("undev", "Undeveloped goal"), ("sup", "SupportedBy"), ("ctx", "InContextOf"),
  ]
  for kind, label in items:
    if kind == "goal":
      out.append(f'<rect x="{x}" y="{cy}" width="40" height="22" class="g"/>')
    elif kind == "strategy":
      out.append(f'<path d="M{x + 7},{cy} L{x + 40},{cy} L{x + 33},{cy + 22} L{x},{cy + 22} Z" class="g"/>')
    elif kind in STATUS_STYLE:
      fill, stroke, _ = STATUS_STYLE[kind]
      dash = ' stroke-dasharray="4 3"' if kind == "missing" else ""
      out.append(f'<circle cx="{x + 20}" cy="{cy + 11}" r="11" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{dash}/>')
    elif kind == "C":
      out.append(f'<rect x="{x}" y="{cy}" width="40" height="22" rx="10" class="ctx"/>')
    elif kind == "A":
      out.append(f'<ellipse cx="{x + 20}" cy="{cy + 11}" rx="20" ry="11" class="ctx"/>')
    elif kind == "undev":
      out.append(f'<path d="M{x + 20},{cy + 2} L{x + 29},{cy + 11} L{x + 20},{cy + 20} L{x + 11},{cy + 11} Z" fill="#fff" stroke="#111" stroke-width="1.2"/>')
    elif kind == "sup":
      out.append(_arrow(x, cy + 11, x + 40, cy + 11, hollow=False))
    else:
      out.append(_arrow(x, cy + 11, x + 40, cy + 11, hollow=True))
    out.append(f'<text x="{x + 56}" y="{cy + 15}" class="l">{escape(label)}</text>')
    cy += 30
  out.append(f'<text x="{x}" y="{cy + 10}" class="dfl">defeaters: DF-nn</text>')
  out.append(f'<text x="{x + 110}" y="{cy + 10}" class="l">open counter-evidence on the goal (WP-K-01 §7)</text>')
  return out, cy + 24 - y


def render_sheet(root: Node, no: int, total: int) -> str:
  box = make_box(root, root)
  width, height = layout(box)
  width = max(width, 1100)
  body: list[str] = []
  draw(box, body)
  fy = height + 10
  leg, lh = legend(MARGIN, fy)
  tb_w, tb_h = 440, 92
  tb_x = width - MARGIN - tb_w
  rows = [
    ("h", "LionDriver — Safety case (GSN)"),
    ("l", f"Argument from {root.ident}"),
    ("l", f"Sheet {no} of {total}"),
    ("l", "Source: case records (assurance/case/) and WP-K-01 contexts"),
    ("s", "Generated by gsn_diagrams.py — edit the records or WP-K-01, not this file"),
  ]
  foot = [f'<rect x="{tb_x}" y="{fy}" width="{tb_w}" height="{tb_h}" fill="#fff" stroke="#111" stroke-width="1.4"/>']
  ry = fy + 6
  for cls, t in rows:
    ry += 16
    foot.append(f'<text x="{tb_x + 10}" y="{ry}" class="{cls}">{escape(t)}</text>')
  total_h = max(fy + lh, fy + tb_h) + MARGIN
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{total_h:.0f}" ' +
          f'viewBox="0 0 {width:.0f} {total_h:.0f}" font-family="Helvetica, Arial, sans-serif">\n' +
          '<style>' +
          '.g{fill:#fff;stroke:#111;stroke-width:1.4}' +
          '.ctx{fill:#f4f4f4;stroke:#111;stroke-width:1.1}' +
          '.id{font-size:11.5px;font-weight:700;text-anchor:middle}' +
          '.d{font-size:10px;text-anchor:middle}' +
          '.sid{font-size:10.5px;font-weight:700;text-anchor:middle}' +
          '.cid{font-size:10px;font-weight:700;text-anchor:middle}' +
          '.cs{font-size:9.5px;text-anchor:middle;fill:#333}' +
          '.aj{font-size:11px;font-weight:700;text-anchor:end}' +
          '.df{font-size:9.5px;font-weight:700;fill:#b3261e;text-anchor:middle}' +
          '.dfl{font-size:9.5px;font-weight:700;fill:#b3261e}' +
          '.sh{font-size:9.5px;font-weight:600;fill:#444;text-anchor:middle}' +
          '.h{font-size:12px;font-weight:700}.l{font-size:10.5px}.s{font-size:9px;fill:#555}' +
          '.w{stroke:#111;stroke-width:1.1}' +
          '</style>\n<rect width="100%" height="100%" fill="#fff"/>\n' +
          f'<text x="{MARGIN}" y="{MARGIN + 6}" class="h">Safety case — argument from {escape(root.ident)}' +
          f'{"" if total == 1 else f"  (sheet {no} of {total})"}</text>\n')
  return head + "\n".join(body + leg + foot) + "\n</svg>\n"


def build() -> dict[str, str]:
  root = build_tree()
  sheets = paginate(root)
  outputs: dict[str, str] = {}
  index = [
    "# Safety case diagrams (GSN)",
    "",
    "Generated from the case records in [`assurance/case/`](../../case/README.md) and the contexts of " +
    "[WP-K-01](../WP-K-01-safety-case.md) by `assurance/case/tools/gsn_diagrams.py`. WP-K-01 stays the reviewed " +
    "document; edit it or the records and regenerate (CI runs `--check`).",
    "",
    "| Sheet | Argument from | Goals | Solutions |",
    "|---|---|---|---|",
  ]
  for no, root_node in enumerate(sheets, 1):
    name = f"gsn-{no}-{root_node.ident}.svg"
    outputs[name] = render_sheet(root_node, no, len(sheets))
    box = make_box(root_node, root_node)
    goals = sum(1 for b in _walk(box) if b.node.kind == "goal")
    sols = sum(1 for b in _walk(box) if b.node.kind == "solution")
    index.append(f"| [{no}]({name}) | {root_node.ident} | {goals} | {sols} |")
  index += ["", "Notation: goal = rectangle; strategy = parallelogram; solution = circle (green available, " +
            "amber partial, white dashed missing); context = rounded box; assumption / justification = oval " +
            "(A / J); diamond = undeveloped goal. Solid arrows are SupportedBy, hollow arrows InContextOf. " +
            "Defeaters (open counter-evidence, WP-K-01 §7) are listed in red on the goal they undermine.", ""]
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
      print("run: python3 assurance/case/tools/gsn_diagrams.py", file=sys.stderr)
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
