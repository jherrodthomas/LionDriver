#!/usr/bin/env python3
"""Draw the WP-A-04 fault trees as conventional FTA diagrams (IEC 61025 symbols).

The source of record is the indented text tree of each safety goal in
`../WP-A-04-system-fta-fmea.md`. This script parses those trees and writes one
SVG per sheet, plus `README.md` listing the sheets. Nothing here is analysis
content: change the trees in WP-A-04 and regenerate.

Each event is a card in the style of `fta-viewer.html`. Symbols: the icon before
the ID is the IEC 61025 shape (square = gate, with its AND / OR symbol beneath the
card; circle = basic event; diamond = undeveloped event; triangle = transfer, to
another sheet or to a gate developed in another tree). An event that already
appears earlier (same ID) is drawn again with a "repeated" tag. Each gate card
shows the fewest item basic events in its cut sets and how many there are
(`fta_cutsets.Solver`).

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
GAP_X = 18
CHARS = 32
LINE_H = 15
NOTE_H = 13.5
CHIP_H = 17
SYM_H = 30
LEVEL_GAP = 40
MARGIN = 40
HEADER_H = 96
MIN_WIDTH = 1180

# Palette shared with fta-viewer.html (fta_viewer.template.html)
BG, CARD, INK, INK2, MUTED, LINE, GRID, SOFT = "#fcfcfb", "#ffffff", "#0b0b0b", "#52514e", "#898781", "#c9c7bf", "#e1e0d9", "#f3f2ee"
OR_C, AND_C, BASIC_C, UE_C, HOT = "#2a78d6", "#6250d6", "#1baf7a", "#eda100", "#d03b3b"
NAVY = INK   # kept for callers of the old palette
SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"

BADGE_STYLE = {   # chip background, chip text, outline (None: filled chip)
  "spf": ("#fbe9e9", "#9e2424", None),
  "latent": ("none", INK2, MUTED),
  "sotif": (SOFT, INK2, None),
  "ccf": (SOFT, INK2, None),
  "ffi": (SOFT, INK2, None),
  "ue": ("#fff5dc", "#7a5600", None),
  "repeat": ("none", INK2, LINE),
  "sheet": (INK, "#fff", None),
  "fmea": ("none", INK2, GRID),
  "nofmea": ("#fbe9e9", "#9e2424", None),
}
STAT_STYLE = {1: ("#fbe9e9", "#9e2424"), 2: ("#fdeee6", "#9a4a25"), 3: ("#fff5dc", "#7a5600"), 4: ("#e6f5e6", "#0a6a0a"),
              0: (SOFT, INK2)}
KIND_LABEL = {
  "top": "TOP EVENT", "gate": "GATE", "basic": "BASIC EVENT", "undeveloped": "UNDEVELOPED",
  "transfer_in": "TRANSFER IN", "implicit_or": "ANY OF", "transfer_out": "TRANSFER OUT",
}
STATS: dict[int, tuple[int, int]] = {}   # id(defining gate) -> (fewest item BE, minimal cut sets), filled by build()

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
  lines: list[str]
  italic: list[str]
  chip_rows: list[list[tuple[str, str, float]]]
  h: float
  hot: bool = False
  x: float = 0.0
  y: float = 0.0
  children: list[Box] = field(default_factory=list)
  symbol: str = "basic"
  stat: tuple[int, int] | None = None


def _chip_w(label: str) -> float:
  return 12 + 5.6 * len(label)


def _stat_label(m: int) -> str:
  return "UE only" if m == 0 else f"{m} fault{'s' if m != 1 else ''}"


def _stat_w(m: int) -> float:
  return 24 + 6.1 * len(_stat_label(m))


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
    badges.append(("sheet", f"continued on sheet {node.sheet_link} ▸"))
  if node is sheet_root and node.sheet_from is not None:
    badges.append(("repeat", f"from sheet {node.sheet_from}"))
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
    if row and used + w > CARD_W - 24:
      rows.append(row)
      row, used = [], 0.0
    row.append((kind, label, w))
    used += w + 4
  if row:
    rows.append(row)
  target = node.ref_of if node.ref_of is not None else node
  stat = STATS.get(id(target)) if target.children else None
  h = (34 if title else 14) + LINE_H * len(lines) + NOTE_H * len(italic) + (CHIP_H + 5) * len(rows) + 10
  if stat:
    h += CHIP_H + 8
  kind = "transfer_out" if transfer_out else node.kind
  if node.kind == "implicit_or":
    symbol = "or"
  elif node.kind in ("top", "gate"):
    symbol = "transfer_out" if transfer_out else node.gate.lower()
  elif node.kind in ("transfer_in", "undeveloped"):
    symbol = node.kind
  else:
    symbol = "basic"
  box = Box(node, title, kind, lines, italic, rows, h, hot=id(node) in hot, symbol=symbol, stat=stat)
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
  level_y = {0: HEADER_H + 32}
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


def _gate(kind: str, cx: float, top: float, col: str) -> str:
  """Small gate symbol hanging from a card, as in fta-viewer.html (34 x 30)."""
  x0 = cx - 17
  if kind == "or":
    d = f"M{x0 + 2},{top + 30} Q{cx},{top + 21} {x0 + 32},{top + 30} Q{x0 + 32},{top + 10.5} {cx},{top + 1} Q{x0 + 2},{top + 10.5} {x0 + 2},{top + 30} Z"
  elif kind == "and":
    d = f"M{x0 + 3},{top + 30} V{top + 14.4} A14,13.4 0 0 1 {x0 + 31},{top + 14.4} V{top + 30} Z"
  else:   # transfer out: triangle with the outgoing line
    return (f'<path d="M{cx},{top + 1} L{cx + 15},{top + 27} L{cx - 15},{top + 27} Z" fill="{CARD}" stroke="{col}" ' +
            f'stroke-width="2" stroke-linejoin="round"/><line x1="{cx + 8}" y1="{top + 14}" x2="{cx + 26}" y2="{top + 14}" ' +
            f'stroke="{col}" stroke-width="2" stroke-linecap="round"/>')
  return (f'<path d="{d}" fill="{CARD}" stroke="{col}" stroke-width="2" stroke-linejoin="round"/>' +
          f'<text x="{cx}" y="{top + 24}" class="gl" fill="{col}">{kind.upper()}</text>')


def _icon(symbol: str, x: float, y: float) -> str:
  """14 x 13 type icon left of the ID: gate square, basic circle, undeveloped diamond, transfer triangle."""
  if symbol in ("or", "and"):
    return f'<rect x="{x + 1}" y="{y + 1}" width="12" height="11" rx="3" fill="{OR_C if symbol == "or" else AND_C}"/>'
  if symbol == "basic":
    return f'<circle cx="{x + 7}" cy="{y + 6.5}" r="5.5" fill="{BASIC_C}"/>'
  if symbol == "undeveloped":
    return f'<path d="M{x + 7},{y + 0.5} L{x + 13.5},{y + 6.5} L{x + 7},{y + 12.5} L{x + 0.5},{y + 6.5} Z" fill="{UE_C}"/>'
  return (f'<path d="M{x + 7},{y + 1} L{x + 13},{y + 12} H{x + 1} Z" fill="none" stroke="{INK2}" stroke-width="1.7" ' +
          'stroke-linejoin="round"/>')


def _chip(out: list[str], x: float, y: float, kind: str, label: str, w: float) -> None:
  bg, fg, outline = BADGE_STYLE[kind]
  stroke = f' stroke="{outline}" stroke-dasharray="3 2"' if kind == "latent" else (f' stroke="{outline}"' if outline else "")
  out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{CHIP_H}" rx="4" fill="{bg}"{stroke}/>')
  out.append(f'<text x="{x + w / 2:.1f}" y="{y + 12:.1f}" class="chip" fill="{fg}">{escape(label)}</text>')


def _stat(out: list[str], x: float, y: float, m: int) -> float:
  """Pill with the fewest item basic events in a cut set below the gate: shape and words, never colour alone."""
  bg, fg = STAT_STYLE[min(m, 4)]
  w = _stat_w(m)
  out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{CHIP_H}" rx="8.5" fill="{bg}"/>')
  cx, cy = x + 11, y + CHIP_H / 2
  if m == 1:
    out.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{fg}"/><rect x="{cx - 3}" y="{cy - 1}" width="6" height="2" fill="{bg}"/>')
  elif m == 2:
    out.append(f'<path d="M{cx},{cy - 4.5} L{cx + 5},{cy + 4} H{cx - 5} Z" fill="{fg}"/>')
  elif m == 3:
    out.append(f'<path d="M{cx},{cy - 5} L{cx + 5},{cy} L{cx},{cy + 5} L{cx - 5},{cy} Z" fill="{fg}"/>')
  elif m >= 4:
    out.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{fg}"/>')
  out.append(f'<text x="{x + (19 if m else 8)}" y="{y + 12.3:.1f}" class="st" fill="{fg}">{_stat_label(m)}</text>')
  return w


def _elbow(x0: float, y0: float, x1: float, y1: float, cls: str) -> str:
  my, r = (y0 + y1) / 2, 10
  if abs(x1 - x0) < 1:
    d = f"M{x0:.1f},{y0:.1f} V{y1:.1f}"
  else:
    s = 1 if x1 > x0 else -1
    r = min(r, abs(x1 - x0) / 2)
    d = (f"M{x0:.1f},{y0:.1f} V{my - r:.1f} Q{x0:.1f},{my:.1f} {x0 + s * r:.1f},{my:.1f} H{x1 - s * r:.1f} " +
         f"Q{x1:.1f},{my:.1f} {x1:.1f},{my + r:.1f} V{y1:.1f}")
  return f'<path d="{d}" class="{cls}"/>'


def draw_box(b: Box, out: list[str], wires: list[str] | None = None) -> None:
  x, y = b.x, b.y
  node = b.node
  top = node.kind == "top"
  latent = "latent" in {k for k, _ in node.badges}
  dash = ' stroke-dasharray="5 4"' if node.kind == "implicit_or" or latent else ""
  border, bw = (HOT, 2.5) if b.hot else ((MUTED, 1.5) if latent else (GRID, 1))
  out.append(f'<rect x="{x}" y="{y + 3}" width="{CARD_W}" height="{b.h}" rx="12" class="shadow"/>')
  out.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{b.h}" rx="12" fill="{CARD}" stroke="{border}" ' +
             f'stroke-width="{bw}"{dash}/>')
  if top:
    out.append(f'<path d="M{x + 12},{y} H{x + CARD_W - 12} A12,12 0 0 1 {x + CARD_W},{y + 12} V{y + 5} H{x} V{y + 12} ' +
               f'A12,12 0 0 1 {x + 12},{y} Z" fill="{INK}"/>')
  ty = y + (24 if b.title else 10)
  if b.title:
    out.append(_icon(node.gate.lower() if b.symbol == "transfer_out" else b.symbol, x + 12, ty - 10.5))
    out.append(f'<text x="{x + 32}" y="{ty}" class="id">{escape(b.title)}</text>')
  label = KIND_LABEL["transfer_out" if b.kind == "transfer_out" else node.kind]
  if node.kind == "gate" and b.kind != "transfer_out":
    label = f"{node.gate} GATE"
  out.append(f'<text x="{x + CARD_W - 12}" y="{ty if b.title else y + 18}" class="kind">{label}</text>')
  ty += 4
  for ln in b.lines:
    ty += LINE_H
    out.append(f'<text x="{x + 12}" y="{ty}" class="d">{escape(ln)}</text>')
  for ln in b.italic:
    ty += NOTE_H
    out.append(f'<text x="{x + 12}" y="{ty}" class="n">{escape(ln)}</text>')
  ty += 8
  for row in b.chip_rows:
    bx = x + 12
    for kind, lab, w in row:
      _chip(out, bx, ty, kind, lab, w)
      bx += w + 4
    ty += CHIP_H + 5
  if b.stat:
    m, cs = b.stat
    sy = y + b.h - CHIP_H - 10
    w = _stat(out, x + 12, sy, m)
    out.append(f'<text x="{x + 18 + w}" y="{sy + 12.3:.1f}" class="cs">{cs} cut set{"s" if cs != 1 else ""}</text>')
  cx = x + CARD_W / 2
  if b.symbol in ("and", "or", "transfer_out"):
    col = HOT if b.hot else (INK2 if b.symbol == "transfer_out" else (OR_C if b.symbol == "or" else AND_C))
    out.append(_gate(b.symbol, cx, y + b.h - 2, col))
  if b.children:
    own = wires is None
    wires = [] if own else wires
    sb = y + b.h - 2 + SYM_H
    for c in sorted(b.children, key=lambda c: c.hot):
      wires.append(_elbow(cx, sb, c.x + CARD_W / 2, c.y, "wh" if b.hot and c.hot else "w"))
    for c in b.children:
      draw_box(c, out, wires)
    if own:
      hot_last = sorted(wires, key=lambda w: 'class="wh"' in w)
      out[0:0] = hot_last


def _legend(x: float, y: float) -> tuple[list[str], float]:
  out = [f'<text x="{x}" y="{y + 14}" class="lh">Symbols · IEC 61025</text>']
  items = [("top", "Top event"), ("or", "OR gate"), ("and", "AND gate"), ("basic", "Basic event"),
           ("undeveloped", "Undeveloped"), ("transfer_in", "Transfer in"), ("transfer_out", "Transfer out")]
  sx = x
  for kind, label in items:
    if kind == "top":
      out.append(f'<rect x="{sx}" y="{y + 30}" width="16" height="13" rx="3" fill="{CARD}" stroke="{GRID}"/>')
      out.append(f'<rect x="{sx}" y="{y + 30}" width="16" height="3" fill="{INK}"/>')
    elif kind == "transfer_out":
      out.append(_icon("transfer_in", sx + 1, y + 30) +
                 f'<line x1="{sx + 11}" y1="{y + 36.5}" x2="{sx + 19}" y2="{y + 36.5}" stroke="{INK2}" stroke-width="1.7"/>')
    else:
      out.append(_icon(kind, sx + 1, y + 30))
    out.append(f'<text x="{sx + (26 if kind == "transfer_out" else 22)}" y="{y + 41}" class="s">{label}</text>')
    sx += 26 + 6.3 * len(label) + 20
  cy = y + 58
  bx = x
  for kind, label in [("spf", "SPF"), ("latent", "latent"), ("sotif", "SOTIF"), ("ccf", "CCF DFI-nn"),
                      ("ffi", "FFI"), ("ue", "outside item"), ("repeat", "repeated / transfer"),
                      ("sheet", "continued on sheet ▸"), ("fmea", "FMEA / FMEDA row"), ("nofmea", "no FMEA")]:
    w = _chip_w(label)
    _chip(out, bx, cy, kind, label, w)
    bx += w + 6
  sy = cy + 30
  bx = x
  for m in (1, 2, 3, 4):
    bx += _stat(out, bx, sy, m) + 6
  out.append(f'<text x="{bx + 6}" y="{sy + 12.3}" class="s">Fewest item basic events in a cut set below the gate ' +
             '(UE assumed)</text>')
  py = sy + 44
  out.append(f'<line x1="{x}" y1="{py - 4}" x2="{x + 34}" y2="{py - 4}" class="wh"/>')
  out.append(f'<text x="{x + 46}" y="{py}" class="lb">Single-point path</text>')
  out.append(f'<text x="{x + 46}" y="{py + 16}" class="s">One basic event in the item reaches the top event; undeveloped events ' +
             'outside the item assumed.</text>')
  out.append(f'<text x="{x + 46}" y="{py + 31}" class="s">Computed from the gate logic (see cut-sets.md); the SPF tags are ' +
             'WP-A-04\'s own claims. Dashed card: latent event.</text>')
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
    out.append(f'<line x1="{px:.1f}" y1="{py + 10:.1f}" x2="{cx:.1f}" y2="{cy - 10:.1f}" stroke="{LINE}" stroke-width="1.3"/>')
  for no, (cx, cy) in pos.items():
    cur = no == current
    out.append(f'<rect x="{cx - 14:.1f}" y="{cy - 10:.1f}" width="28" height="20" rx="6" ' +
               f'fill="{INK if cur else CARD}" stroke="{INK if cur else GRID}" stroke-width="1.3"/>')
    out.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" class="mm" fill="{"#fff" if cur else INK2}">{no}</text>')
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
  if tb_x < MARGIN + 880:   # narrow sheet: title block under the legend
    tb_x, tb_y = MARGIN, fy + lh + 16
  split = tb_x + 318
  footer += [
    f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" rx="12" fill="{CARD}" stroke="{GRID}"/>',
    f'<line x1="{tb_x}" y1="{tb_y + 46}" x2="{tb_x + tb_w}" y2="{tb_y + 46}" stroke="{GRID}"/>',
    f'<line x1="{split}" y1="{tb_y + 46}" x2="{split}" y2="{tb_y + tb_h}" stroke="{GRID}"/>',
    f'<text x="{tb_x + 18}" y="{tb_y + 29}" class="tbh">LionDriver · FTA {tree.goal}</text>',
    f'<rect x="{tb_x + tb_w - 150}" y="{tb_y + 14}" width="132" height="20" rx="10" fill="#fff5dc"/>',
    f'<text x="{tb_x + tb_w - 84}" y="{tb_y + 28}" class="chip" fill="#7a5600">DRAFT · NOT VERIFIED</text>',
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

  title = f"{tree.root.ident} {tree.title}"
  title_cls = "title" if len(title) * 11 < width - 2 * MARGIN - 300 else "title2"
  root_stat = STATS.get(id(tree.root))
  css = "".join([
    f".id{{font:700 12.5px {MONO};fill:{INK}}}",
    f".kind{{font:600 9px {SANS};letter-spacing:.08em;fill:{MUTED};text-anchor:end}}",
    f".d{{font:400 12px {SANS};fill:{INK}}}",
    f".n{{font:italic 400 10.5px {SANS};fill:{INK2}}}",
    f".chip{{font:700 9.5px {SANS};text-anchor:middle}}",
    f".st{{font:700 10.5px {SANS}}}",
    f".cs{{font:400 10.5px {SANS};fill:{MUTED}}}",
    f".gl{{font:700 7.5px {SANS};letter-spacing:.04em;text-anchor:middle}}",
    f".eyebrow{{font:400 12px {SANS};fill:{INK2}}}",
    f".title{{font:700 20px {SANS};fill:{INK}}}",
    f".title2{{font:700 16px {SANS};fill:{INK}}}",
    f".hc{{font:600 12px {SANS};fill:{INK2};text-anchor:middle}}",
    f".lh{{font:600 13px {SANS};fill:{INK}}}",
    f".lb{{font:600 12px {SANS};fill:{INK}}}",
    f".s{{font:400 11px {SANS};fill:{INK2}}}",
    f".tbh{{font:700 14px {SANS};fill:{INK}}}",
    f".k{{font:600 9px {SANS};letter-spacing:.12em;fill:{MUTED}}}",
    f".v{{font:400 11.5px {SANS};fill:{INK}}}",
    f".mm{{font:700 11px {MONO};text-anchor:middle}}",
    f".w{{fill:none;stroke:{LINE};stroke-width:1.6;stroke-linecap:round}}",
    f".wh{{fill:none;stroke:{HOT};stroke-width:2.6;stroke-linecap:round}}",
    ".shadow{fill:#000;opacity:.05}",
  ])
  head = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{total_h:.0f}" viewBox="0 0 {width:.0f} {total_h:.0f}">',
    f'<title>FTA {tree.goal} sheet {sheet_no} of {n_sheets}: {escape(tree.title)}</title>',
    f'<style>{css}</style>',
    '<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">' +
    '<circle cx="1.2" cy="1.2" r="1.2" fill="#e7e6e0"/></pattern></defs>',
    f'<rect width="100%" height="100%" fill="{BG}"/>',
    f'<rect y="{HEADER_H}" width="100%" height="{total_h - HEADER_H:.0f}" fill="url(#dots)"/>',
    f'<line x1="0" y1="{HEADER_H}" x2="{width:.0f}" y2="{HEADER_H}" stroke="{GRID}"/>',
    f'<text x="{MARGIN}" y="34" class="eyebrow">FTA › {tree.goal} · WP-A-04 §{tree.section} · ASIL {asil}</text>',
    f'<text x="{MARGIN}" y="60" class="{title_cls}">{escape(title)}</text>',
  ]
  if root_stat:
    m, cs = root_stat
    sw: list[str] = []
    w = _stat(sw, MARGIN, 70, m)
    sw.append(f'<text x="{MARGIN + w + 8}" y="{82.3}" class="cs">fewest item faults that reach the top event · {cs} minimal cut sets</text>')
    head += sw
  chip_w = 150
  head += [
    f'<rect x="{width - MARGIN - chip_w:.0f}" y="28" width="{chip_w}" height="30" rx="8" fill="{CARD}" stroke="{GRID}"/>',
    f'<text x="{width - MARGIN - chip_w / 2:.0f}" y="47" class="hc">Sheet {sheet_no} of {n_sheets}</text>',
  ]
  return "\n".join(head + body + footer) + "\n</svg>\n"


# ---------------------------------------------------------------- phone view

PHONE_W = 640
PHONE_CSS = f"""<style>
svg {{ --bg:{BG}; --card:{CARD}; --ink:{INK}; --ink2:{INK2}; --mute:{MUTED}; --line:{LINE}; --grid:{GRID}; --soft:{SOFT};
      --or:{OR_C}; --and:{AND_C}; --basic:{BASIC_C}; --ue:{UE_C}; --hot:{HOT}; --chipink:#ffffff;
      --s1b:{STAT_STYLE[1][0]}; --s1f:{STAT_STYLE[1][1]}; --s2b:{STAT_STYLE[2][0]}; --s2f:{STAT_STYLE[2][1]};
      --s3b:{STAT_STYLE[3][0]}; --s3f:{STAT_STYLE[3][1]}; --s4b:{STAT_STYLE[4][0]}; --s4f:{STAT_STYLE[4][1]}; }}
@media (prefers-color-scheme: dark) {{
  svg {{ --bg:#1a1a19; --card:#242422; --ink:#f2f1ec; --ink2:#b5b3ab; --mute:#8a8880; --line:#55534e; --grid:#3a3936;
        --soft:#2e2d2a; --chipink:#1a1a19; --s1b:#4a1f1f; --s1f:#ffb3b3; --s2b:#4a2a1c; --s2f:#ffc6a8; --s3b:#43361a;
        --s3f:#ffd98a; --s4b:#1d3a1d; --s4f:#9fe09f; }}
}}
.bg {{ fill:var(--bg); }} .t {{ font:14px {SANS}; fill:var(--ink); }} .t2 {{ font:12px {SANS}; fill:var(--ink2); }}
.ti {{ font:italic 12px {SANS}; fill:var(--ink2); }} .h {{ font:600 20px {SANS}; fill:var(--ink); }}
.pid {{ font:700 13px {MONO}; fill:var(--ink); }} .pidhot {{ font:700 13px {MONO}; fill:var(--hot); }}
.gl {{ font:700 8px {SANS}; fill:#ffffff; }} .pc {{ font:600 11px {SANS}; }} .ps {{ font:600 11px {SANS}; }}
.rule {{ stroke:var(--grid); stroke-width:1; }} .rail {{ stroke:var(--line); stroke-width:1.2; fill:none; }}
.railhot {{ stroke:var(--hot); stroke-width:2; fill:none; }}
</style>"""
PHONE_CHIP = {   # badge kind -> (fill, text, outline, dashed): BADGE_STYLE in theme tokens
  "spf": ("var(--s1b)", "var(--s1f)", "", False), "nofmea": ("var(--s1b)", "var(--s1f)", "", False),
  "latent": ("none", "var(--ink2)", "var(--mute)", True), "sotif": ("var(--soft)", "var(--ink2)", "", False),
  "ccf": ("var(--soft)", "var(--ink2)", "", False), "ffi": ("var(--soft)", "var(--ink2)", "", False),
  "ue": ("var(--s3b)", "var(--s3f)", "", False), "repeat": ("none", "var(--ink2)", "var(--line)", False),
  "sheet": ("var(--ink)", "var(--chipink)", "", False), "fmea": ("none", "var(--ink2)", "var(--grid)", False),
}


def _pwrap(text: str, px: float) -> list[str]:
  return wrap(text, max(8, int(px / 7.1)))


def _phone_icon(symbol: str, x: float, cy: float, hot: bool) -> str:
  """The type icons of _icon() at 24 px: gate square (OR blue, AND violet, labelled), basic green circle, undeveloped amber
  diamond, transfer outlined triangle; a red ring on a single-point path."""
  ring = ' stroke="var(--hot)" stroke-width="2.4"' if hot else ""
  if symbol in ("or", "and", "transfer_out"):
    lab = {"or": "OR", "and": "AND", "transfer_out": "▸"}[symbol]
    return (f'<rect x="{x:.1f}" y="{cy - 10:.1f}" width="24" height="20" rx="4" fill="var(--{"and" if symbol == "and" else "or"})"{ring}/>'
            f'<text x="{x + 12:.1f}" y="{cy + 3:.1f}" class="gl" text-anchor="middle">{lab}</text>')
  if symbol == "undeveloped":
    return f'<path d="M{x + 12:.1f},{cy - 11:.1f} l11,11 l-11,11 l-11,-11 z" fill="var(--ue)"{ring}/>'
  if symbol == "transfer_in":
    return (f'<path d="M{x + 12:.1f},{cy - 10:.1f} l11,19 h-22 z" fill="none" stroke="{"var(--hot)" if hot else "var(--ink2)"}" '
            'stroke-width="1.8" stroke-linejoin="round"/>')
  return f'<circle cx="{x + 12:.1f}" cy="{cy:.1f}" r="9.5" fill="var(--basic)"{ring}/>'


def _phone_stat(x: float, y: float, m: int, n: int) -> tuple[list[str], float]:
  """The fewest-item-faults pill of _stat() in theme tokens, then the cut-set count as muted text."""
  k = min(m, 4)
  bg, fg = ("var(--soft)", "var(--ink2)") if k == 0 else (f"var(--s{k}b)", f"var(--s{k}f)")
  w = _stat_w(m)
  out = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="18" rx="9" fill="{bg}"/>']
  cx, cy = x + 11, y + 9
  if m == 1:
    out.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{fg}"/><rect x="{cx - 3}" y="{cy - 1}" width="6" height="2" fill="{bg}"/>')
  elif m == 2:
    out.append(f'<path d="M{cx},{cy - 4.5} L{cx + 5},{cy + 4} H{cx - 5} Z" fill="{fg}"/>')
  elif m == 3:
    out.append(f'<path d="M{cx},{cy - 5} L{cx + 5},{cy} L{cx},{cy + 5} L{cx - 5},{cy} Z" fill="{fg}"/>')
  elif m >= 4:
    out.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{fg}"/>')
  out.append(f'<text x="{x + (19 if m else 8):.1f}" y="{y + 13:.1f}" class="ps" fill="{fg}">{escape(_stat_label(m))}</text>')
  lab = f"{n} cut set{'s' if n != 1 else ''}"
  out.append(f'<text x="{x + w + 6:.1f}" y="{y + 13:.1f}" class="t2">{lab}</text>')
  return out, w + 6 + 6.2 * len(lab)


def render_phone(tree: Tree, sheets: list[Node], sheet_no: int, asil: str, hot: set[int], full: str) -> str:
  """The sheet as an indented outline at phone width (640 px): one row per event in reading order, with the gate
  type, the tags, the cut-set figures and the single-point paths (red) of the full sheet."""
  root = sheets[sheet_no - 1]
  box = make_box(root, root, True, hot)
  rows: list[tuple[Box, int, Box | None]] = []

  def visit(b: Box, d: int, parent: Box | None) -> None:
    rows.append((b, d, parent))
    for c in b.children:
      visit(c, d + 1, b)

  visit(box, 0, None)
  body: list[str] = []
  rails: list[str] = []
  y = 34.0
  body.append(f'<text x="16" y="{y:.0f}" class="h">{escape(tree.goal)} fault tree · sheet {sheet_no} of {len(sheets)}</text>')
  y += 22
  body.append(f'<text x="16" y="{y:.0f}" class="t2">ASIL {escape(asil)} · phone view of {escape(full)}; the full sheet has the drawing.</text>')
  y += 20
  body.append(f'<text x="16" y="{y:.0f}" class="t2">Red: a single item fault reaches the top event along this path.</text>')
  y += 12
  centre: dict[int, tuple[float, float]] = {}
  for b, depth, parent in rows:
    n = b.node
    x = 16 + 18 * depth
    tx = x + 100
    width = PHONE_W - 16 - tx
    label = b.title or "any of"
    lines = _pwrap(n.text, width) if n.text else []
    if len(lines) > 4:
      lines = lines[:4]
      lines[-1] = lines[-1][:max(8, int(width / 7.1)) - 1] + "…"
    notes = [ln for note in n.notes for ln in _pwrap(note, width)][:2]
    chips = [(k, lab) for row in b.chip_rows for k, lab, _w in row]
    cy = y + 16
    body.append(_phone_icon(b.symbol, x, cy, b.hot))
    centre[id(b)] = (x + 12, cy)
    if parent is not None:
      px, py = centre[id(parent)]
      rails.append(f'<path d="M{px:.1f},{py + 11:.1f} V{cy:.1f} H{x - 1:.1f}" class="{"railhot" if b.hot and parent.hot else "rail"}"/>')
    body.append(f'<text x="{x + 30}" y="{cy + 5:.1f}" class="{"pidhot" if b.hot else "pid"}">{escape(label)}</text>')
    yy = cy + 5
    for i, ln in enumerate(lines):
      body.append(f'<text x="{tx}" y="{yy + 18 * i:.1f}" class="t">{escape(ln)}</text>')
    if lines:
      yy += 18 * (len(lines) - 1)
    for ln in notes:
      yy += 16
      body.append(f'<text x="{tx}" y="{yy:.1f}" class="ti">{escape(ln)}</text>')
    cx, chip_y = float(tx), yy + 10
    if b.stat:
      els, used = _phone_stat(cx, chip_y, *b.stat)
      body += els
      cx += used + 8
    for k, lab in chips:
      w = 14 + 6.2 * len(lab)
      if cx > tx and cx + w > PHONE_W - 16:
        cx, chip_y = float(tx), chip_y + 22
      fill, ink, outline, dashed = PHONE_CHIP.get(k, ("var(--soft)", "var(--ink2)", "", False))
      stroke = f' stroke="{outline}"' + (' stroke-dasharray="3 2"' if dashed else "") if outline else ""
      body.append(f'<rect x="{cx:.1f}" y="{chip_y:.1f}" width="{w:.1f}" height="18" rx="4" fill="{fill}"{stroke}/>'
                  f'<text x="{cx + 7:.1f}" y="{chip_y + 13:.1f}" class="pc" fill="{ink}">{escape(lab)}</text>')
      cx += w + 6
    bottom = (chip_y + 18 if chips or b.stat else yy) + 10
    body.append(f'<line x1="{tx}" y1="{bottom:.1f}" x2="{PHONE_W - 16}" y2="{bottom:.1f}" class="rule"/>')
    y = bottom
  h = y + 16
  desc = (f"{tree.goal} fault tree (ASIL {asil}), sheet {sheet_no} of {len(sheets)} as an outline: " +
          "; ".join(f"{b.title or 'any of'}{' (' + b.node.gate + ')' if b.node.gate else ''}"
                    f"{', single-point path' if b.hot else ''}" for b, _d, _p in rows) + ".")
  return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{PHONE_W}" height="{h:.0f}" viewBox="0 0 {PHONE_W} {h:.0f}" '
                    'role="img" aria-labelledby="t d">',
                    f'<title id="t">{escape(tree.goal)} fault tree, sheet {sheet_no}: phone view</title>',
                    f'<desc id="d">{escape(desc)}</desc>', PHONE_CSS,
                    f'<rect class="bg" width="{PHONE_W}" height="{h:.0f}"/>', *rails, *body, "</svg>"]) + "\n"


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
  import fta_cutsets   # imports this module, so not at the top
  solver = fta_cutsets.Solver(trees)
  STATS.clear()
  stack = [t.root for t in trees]
  while stack:
    n = stack.pop()
    if n.children and n.ref_of is None:
      STATS[id(n)] = (_min_be(n), len(solver.cut_sets(n)))
      stack += n.children
  asils = goal_asils()
  for tree in trees:
    sheets = all_sheets[tree.goal]
    hot = single_point_nodes(tree)
    names = []
    for no, root in enumerate(sheets, 1):
      name = f"fta-{tree.goal}-{no}.svg"
      outputs[name] = render_sheet(tree, sheets, no, asils.get(tree.goal, "?"), hot)
      phone = f"fta-{tree.goal}-{no}-phone.svg"
      outputs[phone] = render_phone(tree, sheets, no, asils.get(tree.goal, "?"), hot, name)
      names.append(f"[{no}: {root.ident}]({name}) ([outline]({phone}))")
    index.append(f"| {tree.goal} | {tree.root.ident} {tree.title} | {', '.join(names)} |")
  index += ["", "Each event is a card, styled like [fta-viewer.html](fta-viewer.html). Symbols follow IEC 61025, " +
            "as the icon before the ID: square = gate (blue OR, violet AND), with the gate symbol beneath the card; " +
            "circle = basic event; diamond = undeveloped event; triangle = transfer. A dashed card is a latent event. " +
            "Each gate card shows the fewest item basic events in a cut set below it (undeveloped events assumed) and " +
            "its number of minimal cut sets. " +
            "Tags: SPF (single point in the baseline design), latent, SOTIF, CCF (→ WP-A-03 DFI), " +
            "FFI (→ WP-A-02), repeated (event drawn again; defined where first shown). " +
            "Red path: single-point path, one basic event in the item reaching the top event " +
            "(undeveloped events outside the item assumed), computed from the gate logic. " +
            "Outlined tags: the FMEA failure modes and FMEDA rows that realise a basic event " +
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
  index[4:4] = [f"[![First sheet of the {first.goal} fault tree as an outline: top event {first.root.ident} {first.title}, "
                "with the gates and events beneath it down to the transfers to the next sheets; red marks single-point "
                f"paths](fta-{first.goal}-1-phone.svg)](fta-{first.goal}-1.svg)", "",
                f"*Sheet 1 of {first.goal} as an outline that reads on a phone; tap it for the [full sheet](fta-{first.goal}-1.svg). "
                "Every sheet has both, listed below; the notation is explained under the table.*", ""]
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
    n = sum(1 for k in outputs if k.endswith("-phone.svg"))
    print(f"fta_diagrams: {len(outputs) - 1 - n} sheet(s) and {n} phone views current")
    return 0
  for n in sorted(existing - set(outputs)):
    (HERE / n).unlink()
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
  n = sum(1 for k in outputs if k.endswith("-phone.svg"))
  print(f"fta_diagrams: wrote {len(outputs) - 1 - n} sheet(s), {n} phone views and README.md")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
