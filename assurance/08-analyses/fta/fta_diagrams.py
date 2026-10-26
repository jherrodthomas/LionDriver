#!/usr/bin/env python3
"""Draw the WP-A-04 fault trees as conventional FTA diagrams (IEC 61025 symbols).

The source of record is the indented text tree of each safety goal in
`../WP-A-04-system-fta-fmea.md`. This script parses those trees and writes one
SVG per sheet, plus `README.md` listing the sheets. Nothing here is analysis
content: change the trees in WP-A-04 and regenerate.

Symbols: rectangle = top or intermediate event; AND / OR gate below it;
circle = basic event; diamond = undeveloped event; triangle = transfer
(to another sheet, or to a gate developed in another tree). An event that
already appears earlier (same ID) is drawn again with a "repeated" tag.

Each sheet also shows, in red, the single-point paths: from a basic event in a
cut set with exactly one item basic event (undeveloped events assumed) up to the
top event, computed from the gate logic as `fta_cutsets.py` does. The ASIL in the
header comes from the safety goal table of WP-C-03.

    python3 fta_diagrams.py            # regenerate the SVGs and README.md
    python3 fta_diagrams.py --check    # fail if the committed outputs are stale

Standard library only.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-A-04-system-fta-fmea.md"
FTA_FMEA_MAP = HERE.parent / "fta-fmea-map.yaml"
FMEA_REFS: dict[str, dict] = {}   # event id -> its row in fta-fmea-map.yaml, filled by build()

MAX_LEAVES_PER_SHEET = 10
SHEET_OF: dict[int, tuple[str, int]] = {}   # id(defining node) -> (goal, sheet), filled by build()

ID_RE = r"(?:TE-\d+|G(?:-[A-Za-z]+|\d+(?:\.\d+)*(?:\.[a-z])?)|BE-\d+\.\d+|UE-\d+\.\d+)"
SECTION_RE = re.compile(r"^## \d+\. FTA — (SG-\d+): (.+)$")
NODE_START_RE = re.compile(rf"^({ID_RE})\b\s*(.*)$")
MULTI_REF_RE = re.compile(rf"^({ID_RE}(?:\s*[,/]\s*{ID_RE})+)\s*(.*)$")

TAG_RULES = [
  # (regex, badge kind, label function)
  (re.compile(r"\((SPF[^)]*)\)"), "spf", lambda m: m.group(1)),
  (re.compile(r"\(latent, ([^)]*)\)"), "latent", lambda m: "latent, " + m.group(1)),
  (re.compile(r"\[SOTIF\](?:/QM)?"), "sotif", lambda m: m.group(0).strip("[]").replace("]", "")),
  (re.compile(r"\[CCF → (DFI-\d+)\]"), "ccf", lambda m: "CCF " + m.group(1)),
  (re.compile(r"\[FFI → ([\w-]+)\]"), "ffi", lambda m: m.group(1)),
  (re.compile(r"\[FFI\]"), "ffi", lambda m: "FFI"),
]


class FtaError(Exception):
  pass


@dataclass(eq=False)
class Node:
  ident: str
  text: str = ""
  gate: str | None = None           # "OR" / "AND" for gates
  kind: str = "basic"               # top, gate, basic, undeveloped, transfer_in, implicit_or
  badges: list[tuple[str, str]] = field(default_factory=list)
  notes: list[str] = field(default_factory=list)
  children: list[Node] = field(default_factory=list)
  ref_of: Node | None = None        # set for a repeated event or a transfer to another gate
  ref_tree: str | None = None       # tree that defines the referenced node, if another tree
  tree: str = ""
  sheet_link: int | None = None     # transfer-out: sheet that develops this gate
  sheet_from: int | None = None     # sheet root: sheet that transfers in

  def label(self) -> str:
    return self.ident


@dataclass
class Tree:
  goal: str
  title: str
  section: str
  root: Node


# ---------------------------------------------------------------- parsing

def _extract_tags(text: str) -> tuple[str, str | None, list[tuple[str, str]], bool]:
  gate = None
  m = re.search(r"\[(OR|AND)\]", text)
  if m:
    gate = m.group(1)
    text = text[:m.start()] + text[m.end():]
  badges = []
  for rx, kind, fn in TAG_RULES:
    for m in rx.finditer(text):
      badges.append((kind, fn(m)))
    text = rx.sub("", text)
  undeveloped = False
  if re.search(r"\(UE:[^)]*\)", text):
    undeveloped = True
    badges.append(("ue", re.search(r"\(UE:\s*([^)]*)\)", text).group(1)))
    text = re.sub(r"\(UE:[^)]*\)", "", text)
  text = re.sub(r"\s+", " ", text).strip()
  return text, gate, badges, undeveloped


def _raw_lines(block: list[str]):
  """Yield (depth, kind, content) with kind 'node', 'note' or 'cont'."""
  for line in block:
    if not line.strip():
      continue
    i = 0
    while i < len(line) and line[i] in "│├└─ ":
      i += 1
    content = line[i:].rstrip()
    if i == 0:
      yield 0, "node", content
    elif line[i - 4:i] in ("├── ", "└── "):
      kind = "note" if content.startswith("(") else "node"
      yield i // 4, kind, content
    elif i % 4 == 0 and content.startswith("(") and line[i - 4:i] == "│   ":
      yield i // 4, "sibling_note", content
    else:
      yield None, "cont", content


def parse_document(md: str) -> list[Tree]:
  lines = md.splitlines()
  trees: list[Tree] = []
  i = 0
  while i < len(lines):
    m = SECTION_RE.match(lines[i])
    if not m:
      i += 1
      continue
    goal, title = m.group(1), m.group(2)
    section = lines[i].split(".")[0].removeprefix("## ")
    j = i + 1
    while not lines[j].startswith("```"):
      j += 1
    k = j + 1
    while not lines[k].startswith("```"):
      k += 1
    trees.append(_parse_tree(goal, title, section, lines[j + 1:k]))
    i = k + 1
  if not trees:
    raise FtaError("no FTA sections found in WP-A-04")
  return trees


def _parse_tree(goal: str, title: str, section: str, block: list[str]) -> Tree:
  # First collect raw entries with joined continuation text.
  entries: list[list] = []   # [depth, kind, text]
  for depth, kind, content in _raw_lines(block):
    if kind == "cont":
      if not entries:
        raise FtaError(f"{goal}: continuation before any node: {content!r}")
      entries[-1][2] += " " + content
    else:
      entries.append([depth, kind, content])

  root = None
  stack: list[Node] = []   # stack[d] = last node at depth d
  for depth, kind, text in entries:
    if kind in ("note", "sibling_note"):
      owner_depth = depth - 1 if kind == "note" else depth
      owner = stack[owner_depth]
      owner.notes.append(re.sub(r"\s+", " ", text.strip()).strip("()"))
      continue
    node = Node(ident="", text=text, tree=goal)
    node._raw = text  # type: ignore[attr-defined]
    if depth == 0:
      root = node
      stack = [node]
    else:
      if depth > len(stack):
        raise FtaError(f"{goal}: indentation jumps a level at {text!r}")
      stack = stack[:depth]
      stack[-1].children.append(node)
      stack.append(node)
  if root is None:
    raise FtaError(f"{goal}: empty tree")
  return Tree(goal, title, section, root)


def resolve(trees: list[Tree]) -> None:
  """Assign IDs, kinds and tags; turn repeated IDs into references."""
  defined: dict[str, Node] = {}

  def visit(node: Node, parent: Node | None) -> list[Node]:
    raw = node._raw  # type: ignore[attr-defined]
    multi = MULTI_REF_RE.match(raw)
    if multi:
      ids = re.findall(ID_RE, multi.group(1))
      _, _, badges, _ = _extract_tags(multi.group(2))
      refs = []
      for ident in ids:
        if ident not in defined:
          raise FtaError(f"{node.tree}: {ident} is referenced before it is defined")
        refs.append(_make_ref(ident, defined[ident], node.tree, badges))
      sep = "/" if "/" in multi.group(1) else ","
      if parent is not None and (parent.gate == "AND" or sep == "/" and parent.gate != "OR"):
        wrapper = Node(ident="", kind="implicit_or", gate="OR", text="Any of " + ", ".join(ids),
                       tree=node.tree, children=refs)
        return [wrapper]
      return refs

    m = NODE_START_RE.match(raw)
    if not m:
      raise FtaError(f"{node.tree}: line does not start with an event ID: {raw!r}")
    ident, rest = m.group(1), m.group(2)
    text, gate, badges, undeveloped = _extract_tags(rest)
    if ident in defined:
      ref = _make_ref(ident, defined[ident], node.tree, badges)
      if text:
        ref.notes.append(text.strip("()"))
      return [ref]

    node.ident, node.text, node.gate, node.badges = ident, text, None, badges
    if node.children:
      if gate is None:
        raise FtaError(f"{node.tree}: {ident} has inputs but no [OR]/[AND] gate")
      node.gate = gate
      node.kind = "top" if parent is None else "gate"
    elif ident.startswith("UE-") or undeveloped:
      node.kind = "undeveloped"
    else:
      node.kind = "basic"
    defined[ident] = node
    new_children: list[Node] = []
    for child in node.children:
      new_children.extend(visit(child, node))
    node.children = new_children
    if node.gate and len(node.children) < 2:
      raise FtaError(f"{node.tree}: gate {ident} has fewer than two inputs")
    return [node]

  for tree in trees:
    if not tree.root._raw.startswith(f"TE-{tree.goal[3:]} "):
      raise FtaError(f"{tree.goal}: top event ID does not match the goal")
    (tree.root,) = visit(tree.root, None)


def _make_ref(ident: str, target: Node, tree: str, badges) -> Node:
  if target.kind in ("gate", "top"):
    kind = "transfer_in"
  else:
    kind = target.kind
  return Node(ident=ident, text=target.text, kind=kind, badges=list(badges) or list(target.badges),
              ref_of=target, ref_tree=None if target.tree == tree else target.tree, tree=tree)


# ---------------------------------------------------------------- sheets

def leaves(node: Node, top: bool = True) -> int:
  if not node.children or (not top and node.sheet_link is not None):
    return 1
  return sum(leaves(c, False) for c in node.children)


def _desc(node: Node):
  """Descendants drawn on the same sheet (a transferred gate is included, its inputs are not)."""
  for c in node.children:
    yield c
    if c.sheet_link is None:
      yield from _desc(c)


def _depth(root: Node, target: Node, d: int = 0) -> int:
  if root is target:
    return d
  for c in root.children:
    r = _depth(c, target, d + 1)
    if r >= 0:
      return r
  return -1


def paginate(tree: Tree) -> list[Node]:
  """Split the tree into sheets; returns the root node of each sheet."""
  sheets = [tree.root]
  idx = 0
  while idx < len(sheets):
    root = sheets[idx]
    while leaves(root) > MAX_LEAVES_PER_SHEET:
      candidates = [n for n in _desc(root) if n.children and n.sheet_link is None]
      if not candidates:
        break
      best = max(candidates, key=lambda n: (leaves(n), -_depth(root, n)))
      best.sheet_link = len(sheets) + 1
      best.sheet_from = idx + 1
      sheets.append(best)
    idx += 1
  return sheets


# ---------------------------------------------------------------- single-point paths

def _min_be(node: Node) -> int:
  """Fewest item basic events (BE) in any cut set of `node`; undeveloped events (UE) count 0."""
  if node.kind == "transfer_in":
    return _min_be(node.ref_of)
  if not node.children:
    return 1 if node.ident.startswith("BE-") else 0
  orders = [_min_be(c) for c in node.children]
  return min(orders) if node.gate == "OR" else sum(orders)


def single_point_nodes(tree: Tree) -> set[int]:
  """Nodes on a path along which one item basic event reaches the top event.

  The path runs from a basic event in a cut set with exactly one BE (any undeveloped events,
  outside the item, assumed to occur) up to the top event. Returns id() of every drawn node on
  such a path; nodes inside another tree reached through a transfer are not recorded.
  """
  hot: set[int] = set()

  def mark(node: Node, budget: int, record: bool) -> bool:
    if node.kind == "transfer_in":
      found = mark(node.ref_of, budget, False)
    elif not node.children:
      found = node.ident.startswith("BE-") and budget >= 1
    else:
      orders = [_min_be(c) for c in node.children]
      found = False
      for c, order in zip(node.children, orders, strict=True):
        room = budget if node.gate == "OR" else budget - (sum(orders) - order)
        if order <= room and mark(c, room, record):
          found = True
    if found and record:
      hot.add(id(node))
    return found

  if _min_be(tree.root) <= 1:
    mark(tree.root, 1, True)
  return hot


# ---------------------------------------------------------------- drawing

CARD_W = 220
GAP_X = 22
CHARS = 32
LINE_H = 14.5
NOTE_H = 13.5
CHIP_H = 16
SYM_H = 40
LEVEL_GAP = 46
MARGIN = 40
HEADER_H = 78
MIN_WIDTH = 1180

INK, MUTED, WIRE, HAIR, NAVY, HOT = "#1d2433", "#5b6475", "#9aa3b2", "#d9dee6", "#0f2a44", "#c62828"
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, monospace"

BADGE_STYLE = {   # chip background, chip text
  "spf": ("#c62828", "#fff"),
  "latent": ("#5f6368", "#fff"),
  "sotif": ("#6a3fb5", "#fff"),
  "ccf": ("#b45309", "#fff"),
  "ffi": ("#1a5fb4", "#fff"),
  "ue": ("#3d6b3d", "#fff"),
  "repeat": ("#e6e9ef", "#334155"),
  "sheet": ("#e6e9ef", "#334155"),
  "fmea": ("#111827", "#fff"),
  "nofmea": ("#fff1f1", "#c62828"),
}
TINT = {   # event colour (card stripe, symbol outline) and symbol fill
  "spf": ("#c62828", "#fde8e8"),
  "latent": ("#5f6368", "#eceef1"),
  "sotif": ("#6a3fb5", "#efe8fb"),
  "ccf": ("#b45309", "#fdf0e1"),
  "ffi": ("#1a5fb4", "#e6effb"),
  "ue": ("#3d6b3d", "#e7f1e7"),
  "plain": ("#64748b", "#eef1f5"),
  "gate": (INK, "#fff"),
  "top": (NAVY, "#fff"),
}
KIND_LABEL = {
  "top": "TOP EVENT", "gate": "INTERMEDIATE", "basic": "BASIC", "undeveloped": "UNDEVELOPED",
  "transfer_in": "TRANSFER IN", "implicit_or": "ANY OF",
}

ASIL_RE = re.compile(r"^\| \*\*(SG-\d+)\*\* \|[^|]*\| \*\*([A-D]|QM)\*\*", re.M)
HARA = HERE.parents[1] / "02-concept" / "WP-C-03-hara.md"


def goal_asils() -> dict[str, str]:
  """ASIL of each safety goal, from the WP-C-03 safety goal table."""
  return dict(ASIL_RE.findall(HARA.read_text(encoding="utf-8")))


def wrap(text: str, width: int = CHARS) -> list[str]:
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


@dataclass
class Box:
  node: Node
  title: str
  kind: str
  tint: str
  lines: list[str]
  italic: list[str]
  chip_rows: list[list[tuple[str, str, float]]]
  h: float
  hot: bool = False
  x: float = 0.0
  y: float = 0.0
  children: list[Box] = field(default_factory=list)
  symbol: str = "basic"


def _chip_w(label: str) -> float:
  return 14 + 5.7 * len(label)


def _tint(node: Node) -> str:
  if node.kind in ("top", "gate", "implicit_or", "transfer_in"):
    return "top" if node.kind == "top" else ("plain" if node.kind == "transfer_in" else "gate")
  if node.kind == "undeveloped":
    return "ue"
  for kind in ("spf", "sotif", "ccf", "latent", "ffi"):
    if kind in {k for k, _ in node.badges}:
      return kind
  return "plain"


def make_box(node: Node, sheet_root: Node, expand: bool, hot: set[int]) -> Box:
  title = "" if node.kind == "implicit_or" else node.ident
  lines = wrap(node.text) if node.text else []
  if len(lines) > 9:
    lines = lines[:9]
    lines[-1] = lines[-1][:CHARS - 1] + "…"
  italic = [ln for note in node.notes for ln in wrap(note, CHARS + 2)]
  badges = list(node.badges)
  if node.ref_of is not None:
    if node.kind == "transfer_in" and id(node.ref_of) in SHEET_OF:
      goal, no = SHEET_OF[id(node.ref_of)]
      badges.append(("repeat", f"→ {goal} sheet {no}" if node.ref_tree else f"→ sheet {no}"))
    else:
      badges.append(("repeat", f"repeated, {node.ref_tree}" if node.ref_tree else "repeated"))
  transfer_out = node is not sheet_root and node.sheet_link is not None
  if transfer_out:
    badges.append(("sheet", f"continued on sheet {node.sheet_link}"))
  if node is sheet_root and node.sheet_from is not None:
    badges.append(("sheet", f"from sheet {node.sheet_from}"))
  ref = FMEA_REFS.get(node.ident) if node.kind != "transfer_in" else None
  if ref is not None:
    backing = list(ref.get("fmea", [])) + [f.partition(":")[2] for f in ref.get("fmeda", [])]
    badges += [("fmea", b) for b in backing]
    if not backing and not node.children and ref.get("class") not in ("by_design", "external"):
      badges.append(("nofmea", "no FMEA"))
  rows: list[list[tuple[str, str, float]]] = []
  row: list[tuple[str, str, float]] = []
  used = 0.0
  for kind, label in badges:
    w = _chip_w(label)
    if row and used + w > CARD_W - 28:
      rows.append(row)
      row, used = [], 0.0
    row.append((kind, label, w))
    used += w + 5
  if row:
    rows.append(row)
  h = (30 if title else 12) + LINE_H * len(lines) + NOTE_H * len(italic) + (CHIP_H + 6) * len(rows) + 12
  kind = "transfer_out" if transfer_out else node.kind
  if node.kind == "implicit_or":
    symbol = "or"
  elif node.kind in ("top", "gate"):
    symbol = "transfer_out" if transfer_out else node.gate.lower()
  elif node.kind in ("transfer_in", "undeveloped"):
    symbol = node.kind
  else:
    symbol = "basic"
  box = Box(node, title, kind, _tint(node), lines, italic, rows, h, hot=id(node) in hot, symbol=symbol)
  if expand and node.children and not transfer_out:
    box.children = [make_box(c, sheet_root, True, hot) for c in node.children]
  return box


def layout(root: Box) -> tuple[float, float]:
  level_h: dict[int, float] = {}

  def heights(b: Box, d: int):
    level_h[d] = max(level_h.get(d, 0), b.h)
    for c in b.children:
      heights(c, d + 1)

  heights(root, 0)
  level_y = {0: HEADER_H + 36}
  for d in range(1, max(level_h) + 1):
    level_y[d] = level_y[d - 1] + level_h[d - 1] + SYM_H + LEVEL_GAP

  cursor = [MARGIN]

  def place(b: Box, d: int):
    b.y = level_y[d]
    if not b.children:
      b.x = cursor[0]
      cursor[0] += CARD_W + GAP_X
      return
    for c in b.children:
      place(c, d + 1)
    b.x = (b.children[0].x + b.children[-1].x) / 2

  place(root, 0)
  width = cursor[0] - GAP_X + MARGIN
  depth = max(level_h)
  height = level_y[depth] + level_h[depth] + SYM_H + 24
  return width, height


def _symbol(kind: str, cx: float, top: float, stroke: str = INK, fill: str = "#fff", heavy: bool = False) -> str:
  s = f'fill="{fill}" stroke="{stroke}" stroke-width="{2.4 if heavy else 1.7}"'
  if kind in ("and", "or"):
    if kind == "and":
      shape = (f'<path d="M{cx - 20},{top + 38} L{cx - 20},{top + 18} ' +
               f'A20,18 0 0 1 {cx + 20},{top + 18} L{cx + 20},{top + 38} Z" {s}/>')
    else:
      shape = (f'<path d="M{cx - 20},{top + 38} Q{cx},{top + 29} {cx + 20},{top + 38} ' +
               f'Q{cx + 18},{top + 11} {cx},{top} Q{cx - 18},{top + 11} {cx - 20},{top + 38} Z" {s}/>')
    return shape + f'<text x="{cx}" y="{top + 30}" class="gl" fill="{stroke}">{kind.upper()}</text>'
  if kind == "basic":
    return f'<circle cx="{cx}" cy="{top + 17}" r="16" {s}/>'
  if kind == "undeveloped":
    return f'<path d="M{cx},{top} L{cx + 22},{top + 17} L{cx},{top + 34} L{cx - 22},{top + 17} Z" {s}/>'
  if kind in ("transfer_in", "transfer_out"):
    tri = f'<path d="M{cx},{top} L{cx + 20},{top + 33} L{cx - 20},{top + 33} Z" {s}/>'
    if kind == "transfer_out":
      tri += (f'<line x1="{cx + 10}" y1="{top + 16}" x2="{cx + 34}" y2="{top + 16}" stroke="{stroke}" ' +
              f'stroke-width="{2.4 if heavy else 1.7}" stroke-linecap="round"/>')
    return tri
  raise ValueError(kind)


def _sym_bottom(kind: str) -> float:
  return {"and": 38, "or": 38, "basic": 33, "undeveloped": 34, "transfer_in": 33, "transfer_out": 33}[kind]


def _chip(out: list[str], x: float, y: float, kind: str, label: str, w: float) -> None:
  bg, fg = BADGE_STYLE[kind]
  out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{CHIP_H}" rx="8" fill="{bg}"/>')
  out.append(f'<text x="{x + w / 2:.1f}" y="{y + 11.5:.1f}" class="chip" fill="{fg}">{escape(label)}</text>')


def _wire(out: list[str], x1: float, y1: float, x2: float, y2: float, hot: bool) -> None:
  out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{"wh" if hot else "w"}"/>')


def draw_box(b: Box, out: list[str]) -> None:
  x, y = b.x, b.y
  node = b.node
  stripe, sym_fill = TINT[b.tint]
  top = node.kind == "top"
  dash = ' stroke-dasharray="5 4"' if node.kind == "implicit_or" else ""
  border = HOT if b.hot else (NAVY if top else HAIR)
  out.append(f'<rect x="{x + 1.5}" y="{y + 2.5}" width="{CARD_W}" height="{b.h}" rx="9" class="shadow"/>')
  out.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{b.h}" rx="9" fill="#fff" stroke="{border}" ' +
             f'stroke-width="{2 if b.hot or top else 1}"{dash}/>')
  if node.kind != "implicit_or":
    out.append(f'<path d="M{x + 9},{y} H{x + CARD_W - 9} A9,9 0 0 1 {x + CARD_W},{y + 9} V{y + 5} H{x} V{y + 9} ' +
               f'A9,9 0 0 1 {x + 9},{y} Z" fill="{stripe}"/>')
  ty = y + (25 if b.title else 8)
  if b.title:
    out.append(f'<text x="{x + 14}" y="{ty}" class="id">{escape(b.title)}</text>')
  label = "TRANSFER OUT" if b.kind == "transfer_out" else KIND_LABEL[node.kind]
  out.append(f'<text x="{x + CARD_W - 14}" y="{y + 25 if b.title else y + 18}" class="kind">{label}</text>')
  for ln in b.lines:
    ty += LINE_H
    out.append(f'<text x="{x + 14}" y="{ty}" class="d">{escape(ln)}</text>')
  for ln in b.italic:
    ty += NOTE_H
    out.append(f'<text x="{x + 14}" y="{ty}" class="n">{escape(ln)}</text>')
  ty += 8
  for row in b.chip_rows:
    bx = x + 14
    for kind, lab, w in row:
      _chip(out, bx, ty, kind, lab, w)
      bx += w + 5
    ty += CHIP_H + 6
  cx = x + CARD_W / 2
  sym_top = y + b.h
  is_event = b.symbol in ("basic", "undeveloped", "transfer_in")
  stroke = HOT if b.hot else (stripe if is_event else INK)
  out.append(_symbol(b.symbol, cx, sym_top, stroke, sym_fill if is_event else "#fff", b.hot))
  if b.children:
    sb = sym_top + _sym_bottom(b.symbol)
    bus_y = sb + LEVEL_GAP / 2
    xs = [c.x + CARD_W / 2 for c in b.children]
    _wire(out, min(xs), bus_y, max(xs), bus_y, False)
    hot_xs = [c.x + CARD_W / 2 for c in b.children if c.hot]
    if hot_xs:
      _wire(out, min(hot_xs + [cx]), bus_y, max(hot_xs + [cx]), bus_y, True)
    _wire(out, cx, sb, cx, bus_y, b.hot)
    for c in b.children:
      _wire(out, c.x + CARD_W / 2, bus_y, c.x + CARD_W / 2, c.y, c.hot)
    for c in b.children:
      draw_box(c, out)


def _legend(x: float, y: float) -> tuple[list[str], float]:
  out = [f'<text x="{x}" y="{y + 14}" class="lh">Symbols · IEC 61025</text>']
  items = [
    ("rect", "Event"), ("or", "OR gate"), ("and", "AND gate"), ("basic", "Basic event"),
    ("undeveloped", "Undeveloped"), ("transfer_out", "Transfer out"), ("transfer_in", "Transfer in"),
  ]
  sx = x
  for kind, label in items:
    cx = sx + 28
    if kind == "rect":
      out.append(f'<rect x="{cx - 22}" y="{y + 34}" width="44" height="28" rx="6" fill="#fff" stroke="{HAIR}"/>')
      out.append(f'<rect x="{cx - 22}" y="{y + 34}" width="44" height="4" rx="2" fill="{INK}"/>')
    elif kind in ("or", "and", "transfer_out"):
      out.append(_symbol(kind, cx, y + 30))
    else:
      fill = TINT["ue" if kind == "undeveloped" else "plain"]
      out.append(_symbol(kind, cx, y + 31, fill[0], fill[1]))
    out.append(f'<text x="{cx}" y="{y + 88}" class="s" text-anchor="middle">{label}</text>')
    sx += 80
  cy = y + 106
  bx = x
  for kind, label in [("spf", "SPF"), ("latent", "latent"), ("sotif", "SOTIF"), ("ccf", "CCF DFI-nn"),
                      ("ffi", "FFI"), ("ue", "outside item"), ("repeat", "repeated / transfer"),
                      ("fmea", "FMEA / FMEDA row"), ("nofmea", "no FMEA")]:
    w = _chip_w(label)
    _chip(out, bx, cy, kind, label, w)
    bx += w + 6
  py = cy + 38
  out.append(f'<line x1="{x}" y1="{py - 4}" x2="{x + 34}" y2="{py - 4}" class="wh"/>')
  out.append(f'<text x="{x + 46}" y="{py}" class="lb">Single-point path</text>')
  out.append(f'<text x="{x + 46}" y="{py + 16}" class="s">One basic event in the item reaches the top event; undeveloped events ' +
             'outside the item assumed.</text>')
  out.append(f'<text x="{x + 46}" y="{py + 31}" class="s">Computed from the gate logic (see cut-sets.md); the SPF tags are ' +
             'WP-A-04\'s own claims.</text>')
  return out, py + 40 - y


def _sheet_map(sheets: list[Node], current: int, x: float, y: float, w: float, h: float) -> list[str]:
  """Small tree of the goal's sheets (parent = the sheet that transfers out), current one filled."""
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


def render_sheet(tree: Tree, sheets: list[Node], sheet_no: int, asil: str, hot: set[int]) -> str:
  sheet_root = sheets[sheet_no - 1]
  n_sheets = len(sheets)
  box = make_box(sheet_root, sheet_root, True, hot)
  width, height = layout(box)
  width = max(width, MIN_WIDTH)
  body: list[str] = []
  draw_box(box, body)
  n_hot = sum(1 for b in _walk_sheet(box) if b.hot and b.symbol == "basic")

  # Footer: legend and title block.
  fy = height + 20
  footer, lh = _legend(MARGIN, fy)
  tb_w, tb_h = 500, 196
  tb_x, tb_y = width - MARGIN - tb_w, fy
  split = tb_x + 318
  footer += [
    f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" rx="10" fill="#fff" stroke="{HAIR}"/>',
    f'<line x1="{tb_x}" y1="{tb_y + 46}" x2="{tb_x + tb_w}" y2="{tb_y + 46}" stroke="{HAIR}"/>',
    f'<line x1="{split}" y1="{tb_y + 46}" x2="{split}" y2="{tb_y + tb_h}" stroke="{HAIR}"/>',
    f'<text x="{tb_x + 18}" y="{tb_y + 29}" class="tbh">LionDriver · FTA {tree.goal}</text>',
    f'<rect x="{tb_x + tb_w - 150}" y="{tb_y + 14}" width="132" height="20" rx="10" fill="#fff4e0" stroke="#f0c36d"/>',
    f'<text x="{tb_x + tb_w - 84}" y="{tb_y + 28}" class="chip" fill="#8a5a00">DRAFT · NOT VERIFIED</text>',
  ]
  rows = [
    ("Top of sheet", sheet_root.ident),
    ("Single-point", f"{n_hot} basic event{'s' if n_hot != 1 else ''} on this sheet"),
    ("Source", f"WP-A-04 §{tree.section} (analysis of record)"),
    ("Generated by", "fta_diagrams.py"),
    ("Edit", "WP-A-04, not this file"),
  ]
  ry = tb_y + 72
  for k, v in rows:
    footer.append(f'<text x="{tb_x + 18}" y="{ry}" class="k">{k.upper()}</text>')
    footer.append(f'<text x="{tb_x + 116}" y="{ry}" class="v">{escape(v)}</text>')
    ry += 26
  footer.append(f'<text x="{split + 16}" y="{tb_y + 70}" class="k">SHEETS</text>')
  footer += _sheet_map(sheets, sheet_no, split + 10, tb_y + 84, tb_x + tb_w - split - 20, tb_h - 100)
  total_h = max(fy + lh, tb_y + tb_h) + MARGIN

  title = tree.title[0].upper() + tree.title[1:]
  title_cls = "title" if len(title) * 11 < width - 2 * MARGIN - 260 else "title2"
  chip_w = 236
  css = "".join([
    f".id{{font:700 13px {MONO};fill:{INK}}}",
    f".kind{{font:600 9px {SANS};letter-spacing:.1em;fill:#8a93a3;text-anchor:end}}",
    f".d{{font:400 11.5px {SANS};fill:#2b3343}}",
    f".n{{font:italic 400 10.5px {SANS};fill:#6b7385}}",
    f".chip{{font:600 9.5px {SANS};text-anchor:middle}}",
    f".gl{{font:700 7.5px {SANS};letter-spacing:.06em;text-anchor:middle}}",
    f".eyebrow{{font:600 12px {SANS};letter-spacing:.14em;fill:#9fb7d1}}",
    f".title{{font:600 21px {SANS};fill:#fff}}",
    f".title2{{font:600 17px {SANS};fill:#fff}}",
    f".hc{{font:600 12px {SANS};letter-spacing:.04em;fill:#fff;text-anchor:middle}}",
    f".lh{{font:600 13px {SANS};fill:{INK}}}",
    f".lb{{font:600 12px {SANS};fill:{INK}}}",
    f".s{{font:400 11px {SANS};fill:{MUTED}}}",
    f".tbh{{font:700 14px {SANS};fill:{NAVY}}}",
    f".k{{font:600 9px {SANS};letter-spacing:.12em;fill:#8a93a3}}",
    f".v{{font:400 11.5px {SANS};fill:{INK}}}",
    f".mm{{font:700 11px {MONO};text-anchor:middle}}",
    f".w{{stroke:{WIRE};stroke-width:1.4;stroke-linecap:round}}",
    f".wh{{stroke:{HOT};stroke-width:3.2;stroke-linecap:round}}",
    ".shadow{fill:#0f172a;opacity:.06}",
  ])
  head = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{total_h:.0f}" viewBox="0 0 {width:.0f} {total_h:.0f}">',
    f'<title>FTA {tree.goal} sheet {sheet_no} of {n_sheets}: {escape(tree.title)}</title>',
    f'<style>{css}</style>',
    '<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">' +
    '<circle cx="1" cy="1" r="1" fill="#e3e7ee"/></pattern></defs>',
    '<rect width="100%" height="100%" fill="#f7f8fa"/>',
    f'<rect y="{HEADER_H}" width="100%" height="{total_h - HEADER_H:.0f}" fill="url(#dots)"/>',
    f'<rect width="100%" height="{HEADER_H}" fill="{NAVY}"/>',
    f'<text x="{MARGIN}" y="32" class="eyebrow">FTA · {tree.goal} · WP-A-04 §{tree.section}</text>',
    f'<text x="{MARGIN}" y="59" class="{title_cls}">{escape(title)}</text>',
    f'<rect x="{width - MARGIN - chip_w:.0f}" y="21" width="{chip_w}" height="36" rx="18" fill="#ffffff14" stroke="#ffffff40"/>',
    f'<text x="{width - MARGIN - chip_w / 2:.0f}" y="44" class="hc">Sheet {sheet_no} of {n_sheets}  ·  ASIL {asil}</text>',
  ]
  return "\n".join(head + body + footer) + "\n</svg>\n"


def _walk_sheet(b: Box):
  yield b
  for c in b.children:
    yield from _walk_sheet(c)


# ---------------------------------------------------------------- outputs

def load_fmea_refs() -> dict[str, dict]:
  """Events and gates of fta-fmea-map.yaml by id; empty without the file (the map is checked by tools/safety/fmea_lint.py)."""
  if not FTA_FMEA_MAP.exists():
    return {}
  import yaml
  doc = yaml.safe_load(FTA_FMEA_MAP.read_text(encoding="utf-8")) or {}
  return {r["id"]: r for r in doc.get("events", []) + doc.get("gates", [])}


def build() -> dict[str, str]:
  FMEA_REFS.clear()
  FMEA_REFS.update(load_fmea_refs())
  trees = parse_document(SOURCE.read_text(encoding="utf-8"))
  resolve(trees)
  trees.sort(key=lambda t: t.goal)
  outputs: dict[str, str] = {}
  index = [
    "# Fault tree diagrams",
    "",
    "Generated from the text trees in [WP-A-04](../WP-A-04-system-fta-fmea.md) by `fta_diagrams.py`. " +
    "WP-A-04 is the analysis of record; edit it and run `python3 fta_diagrams.py` (CI runs `--check`).",
    "",
    "| Goal | Top event | Sheets |",
    "|---|---|---|",
  ]
  all_sheets = {tree.goal: paginate(tree) for tree in trees}
  SHEET_OF.clear()
  for goal, sheets in all_sheets.items():
    for no, root in enumerate(sheets, 1):
      SHEET_OF[id(root)] = (goal, no)
      for n in _desc(root):
        if n.sheet_link is None:
          SHEET_OF.setdefault(id(n), (goal, no))
  asils = goal_asils()
  for tree in trees:
    sheets = all_sheets[tree.goal]
    hot = single_point_nodes(tree)
    names = []
    for no, root in enumerate(sheets, 1):
      name = f"fta-{tree.goal}-{no}.svg"
      outputs[name] = render_sheet(tree, sheets, no, asils.get(tree.goal, "?"), hot)
      names.append(f"[{no}: {root.ident}]({name})")
    index.append(f"| {tree.goal} | {tree.root.ident} {tree.title} | {', '.join(names)} |")
  index += ["", "Symbols follow IEC 61025: rectangle = top or intermediate event; OR / AND gate beneath it; " +
            "circle = basic event; diamond = undeveloped event; triangle = transfer. " +
            "Tags: SPF (single point in the baseline design), latent, SOTIF, CCF (→ WP-A-03 DFI), " +
            "FFI (→ WP-A-02), repeated (event drawn again; defined where first shown). " +
            "Red path: single-point path, one basic event in the item reaching the top event " +
            "(undeveloped events outside the item assumed), computed from the gate logic. " +
            "Dark tags: the FMEA failure modes and FMEDA rows that realise a basic event " +
            "([fta-fmea-map.yaml](../fta-fmea-map.yaml), checked by `fmea_lint.py`); red \"no FMEA\": an event of a mapped " +
            "tree that no FMEA row backs yet.", "",
            "Minimal cut sets computed from the same trees, and the check of the WP-A-04 tables: " +
            "[cut-sets.md](cut-sets.md) (`fta_cutsets.py`).", "",
            "Interactive view of every tree on one page, without sheets: [fta-viewer.html](fta-viewer.html) " +
            "(`fta_viewer.py`; download it and open it in a browser, it needs no network). Gates and transfers open in " +
            "place, each gate shows its cut sets and the fewest item faults among them, and the red paths are the ones " +
            "on these sheets; a switch also counts latent events as already failed. Light, dark and left-to-right " +
            "layouts. The sheets stay the drawing of record.", ""]
  first = trees[0]
  index[4:4] = [f"![First sheet of the {first.goal} fault tree: top event {first.root.ident} {first.title}, with the "
                "gates and events beneath it down to the transfers to the next sheets; red marks single-point paths]"
                f"(fta-{first.goal}-1.svg)", "",
                f"*Sheet 1 of {first.goal}, as an example of the notation explained under the table; every sheet is "
                "listed below.*", ""]
  outputs["README.md"] = "\n".join(index)
  return outputs


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    outputs = build()
  except FtaError as e:
    print(f"fta_diagrams: {e}", file=sys.stderr)
    return 1
  existing = {p.name for p in HERE.glob("fta-*.svg")}
  if check:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    extra = sorted(existing - set(outputs))
    if stale or extra:
      for n in stale:
        print(f"stale: {n}", file=sys.stderr)
      for n in extra:
        print(f"no longer generated: {n}", file=sys.stderr)
      print("run: python3 assurance/08-analyses/fta/fta_diagrams.py", file=sys.stderr)
      return 1
    print(f"fta_diagrams: {len(outputs) - 1} sheet(s) current")
    return 0
  for n in sorted(existing - set(outputs)):
    (HERE / n).unlink()
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
  print(f"fta_diagrams: wrote {len(outputs) - 1} sheet(s) and README.md")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
