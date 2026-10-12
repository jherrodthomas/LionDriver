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

MAX_LEAVES_PER_SHEET = 16

ID_RE = r"(?:TE-\d+|G(?:-[A-Za-z]+|\d+(?:\.\d+)*(?:\.[a-z])?)|BE-\d+\.\d+|UE-\d+\.\d+)"
SECTION_RE = re.compile(r"^## \d+\. FTA — (SG-\d+): (.+)$")
NODE_START_RE = re.compile(rf"^({ID_RE})\b\s*(.*)$")
MULTI_REF_RE = re.compile(rf"^({ID_RE}(?:\s*[,/]\s*{ID_RE})+)\s*(.*)$")

TAG_RULES = [
  # (regex, badge kind, label function)
  (re.compile(r"\((SPF[^)]*)\)"), "spf", lambda m: m.group(1)),
  (re.compile(r"\(latent, design\)"), "latent", lambda m: "latent, design"),
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


# ---------------------------------------------------------------- drawing

BOX_W = 200
GAP_X = 18
CHARS = 35
LINE_H = 12.5
SYM_H = 36
LEVEL_GAP = 34
MARGIN = 30

BADGE_STYLE = {
  "spf": ("#b3261e", "#fff"),
  "latent": ("#5f6368", "#fff"),
  "sotif": ("#6a3fb5", "#fff"),
  "ccf": ("#c25e00", "#fff"),
  "ffi": ("#1a5fb4", "#fff"),
  "ue": ("#3d6b3d", "#fff"),
  "repeat": ("#e8e8e8", "#222"),
  "sheet": ("#e8e8e8", "#222"),
}


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
  lines: list[str]
  italic: list[str]
  badges: list[tuple[str, str]]
  badge_rows: list[list[tuple[str, str, float]]]
  h: float
  x: float = 0.0
  y: float = 0.0
  children: list[Box] = field(default_factory=list)
  symbol: str = "basic"


def _badge_w(label: str) -> float:
  return 8 + 5.4 * len(label)


def make_box(node: Node, sheet_root: Node, expand: bool) -> Box:
  if node.kind == "implicit_or":
    title, text = "", node.text
  else:
    title, text = node.ident, node.text
  lines = wrap(text) if text else []
  if len(lines) > 9:
    lines = lines[:9]
    lines[-1] = lines[-1][:CHARS - 1] + "…"
  italic = [ln for note in node.notes for ln in wrap(note)]
  badges = list(node.badges)
  if node.ref_of is not None:
    badges.append(("repeat", f"repeated, {node.ref_tree}" if node.ref_tree else "repeated"))
  if node is not sheet_root and node.sheet_link is not None:
    badges.append(("sheet", f"continued on sheet {node.sheet_link}"))
  if node is sheet_root and node.sheet_from is not None:
    badges.append(("sheet", f"from sheet {node.sheet_from}"))
  rows: list[list[tuple[str, str, float]]] = []
  row: list[tuple[str, str, float]] = []
  used = 0.0
  for kind, label in badges:
    w = _badge_w(label)
    if row and used + w > BOX_W - 10:
      rows.append(row)
      row, used = [], 0.0
    row.append((kind, label, w))
    used += w + 4
  if row:
    rows.append(row)
  h = 8 + (14 if title else 0) + LINE_H * (len(lines) + len(italic)) + 16 * len(rows) + 6
  if node.kind == "implicit_or":
    symbol = "or"
  elif node.kind in ("top", "gate"):
    symbol = "transfer_out" if (node is not sheet_root and node.sheet_link is not None) else node.gate.lower()
  elif node.kind == "transfer_in":
    symbol = "transfer_in"
  elif node.kind == "undeveloped":
    symbol = "undeveloped"
  else:
    symbol = "basic"
  box = Box(node, title, lines, italic, badges, rows, h, symbol=symbol)
  if expand and node.children and not (node is not sheet_root and node.sheet_link is not None):
    box.children = [make_box(c, sheet_root, True) for c in node.children]
  return box


def layout(root: Box) -> tuple[float, float]:
  level_h: dict[int, float] = {}

  def heights(b: Box, d: int):
    level_h[d] = max(level_h.get(d, 0), b.h)
    for c in b.children:
      heights(c, d + 1)

  heights(root, 0)
  level_y = {0: MARGIN + 40}
  for d in range(1, max(level_h) + 1):
    level_y[d] = level_y[d - 1] + level_h[d - 1] + SYM_H + LEVEL_GAP

  cursor = [MARGIN]

  def place(b: Box, d: int):
    b.y = level_y[d]
    if not b.children:
      b.x = cursor[0]
      cursor[0] += BOX_W + GAP_X
      return
    for c in b.children:
      place(c, d + 1)
    b.x = (b.children[0].x + b.children[-1].x) / 2

  place(root, 0)
  width = cursor[0] - GAP_X + MARGIN
  depth = max(level_h)
  height = level_y[depth] + level_h[depth] + SYM_H + MARGIN
  return width, height


def _symbol(kind: str, cx: float, top: float) -> str:
  s = 'fill="#fff" stroke="#111" stroke-width="1.4"'
  if kind == "and":
    return (f'<path d="M{cx - 18},{top + 34} L{cx - 18},{top + 16} ' +
            f'A18,16 0 0 1 {cx + 18},{top + 16} L{cx + 18},{top + 34} Z" {s}/>')
  if kind == "or":
    return (f'<path d="M{cx - 18},{top + 34} Q{cx},{top + 26} {cx + 18},{top + 34} ' +
            f'Q{cx + 16},{top + 10} {cx},{top} Q{cx - 16},{top + 10} {cx - 18},{top + 34} Z" {s}/>')
  if kind == "basic":
    return f'<circle cx="{cx}" cy="{top + 15}" r="15" {s}/>'
  if kind == "undeveloped":
    return (f'<path d="M{cx},{top} L{cx + 20},{top + 15} L{cx},{top + 30} ' +
            f'L{cx - 20},{top + 15} Z" {s}/>')
  if kind in ("transfer_in", "transfer_out"):
    tri = f'<path d="M{cx},{top} L{cx + 18},{top + 30} L{cx - 18},{top + 30} Z" {s}/>'
    if kind == "transfer_out":
      tri += f'<line x1="{cx + 9}" y1="{top + 15}" x2="{cx + 30}" y2="{top + 15}" stroke="#111" stroke-width="1.4"/>'
    return tri
  raise ValueError(kind)


def _sym_bottom(kind: str) -> float:
  return {"and": 34, "or": 34, "basic": 30, "undeveloped": 30,
          "transfer_in": 30, "transfer_out": 30}[kind]


def draw_box(b: Box, out: list[str]) -> None:
  x, y = b.x, b.y
  node = b.node
  heavy = node.kind == "top"
  fill = "#fff" if node.kind != "implicit_or" else "#f6f6f6"
  dash = ' stroke-dasharray="4 3"' if node.kind == "implicit_or" else ""
  out.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{b.h}" rx="2" fill="{fill}" ' +
             f'stroke="#111" stroke-width="{2.2 if heavy else 1.1}"{dash}/>')
  ty = y + 8
  cx = x + BOX_W / 2
  if b.title:
    ty += 11
    out.append(f'<text x="{cx}" y="{ty}" class="id">{escape(b.title)}</text>')
    ty += 3
  for ln in b.lines:
    ty += LINE_H
    out.append(f'<text x="{cx}" y="{ty - 2}" class="d">{escape(ln)}</text>')
  for ln in b.italic:
    ty += LINE_H
    out.append(f'<text x="{cx}" y="{ty - 2}" class="n">{escape(ln)}</text>')
  for row in b.badge_rows:
    total = sum(w for _, _, w in row) + 4 * (len(row) - 1)
    bx = cx - total / 2
    ty += 16
    for kind, label, w in row:
      bg, fg = BADGE_STYLE[kind]
      out.append(f'<rect x="{bx:.1f}" y="{ty - 12}" width="{w:.1f}" height="13" rx="6.5" fill="{bg}"/>')
      out.append(f'<text x="{bx + w / 2:.1f}" y="{ty - 2.5}" class="b" fill="{fg}">{escape(label)}</text>')
      bx += w + 4
  sym_top = y + b.h
  out.append(_symbol(b.symbol, cx, sym_top))
  if b.children:
    bus_y = sym_top + _sym_bottom(b.symbol) + LEVEL_GAP / 2 + 1
    out.append(f'<line x1="{cx}" y1="{sym_top + _sym_bottom(b.symbol)}" x2="{cx}" y2="{bus_y}" class="w"/>')
    xs = [c.x + BOX_W / 2 for c in b.children]
    out.append(f'<line x1="{min(xs)}" y1="{bus_y}" x2="{max(xs)}" y2="{bus_y}" class="w"/>')
    for c in b.children:
      ccx = c.x + BOX_W / 2
      out.append(f'<line x1="{ccx}" y1="{bus_y}" x2="{ccx}" y2="{c.y}" class="w"/>')
    for c in b.children:
      draw_box(c, out)


def _legend(x: float, y: float) -> tuple[list[str], float]:
  out = [f'<text x="{x}" y="{y + 12}" class="h">Symbols (IEC 61025)</text>']
  items = [
    ("rect", "Top / intermediate event"),
    ("or", "OR gate"),
    ("and", "AND gate"),
    ("basic", "Basic event"),
    ("undeveloped", "Undeveloped event (outside the item or not developed)"),
    ("transfer_out", "Transfer: continued on another sheet"),
    ("transfer_in", "Transfer in: gate developed elsewhere"),
  ]
  cy = y + 26
  for kind, label in items:
    if kind == "rect":
      out.append(f'<rect x="{x + 2}" y="{cy}" width="36" height="22" fill="#fff" stroke="#111" stroke-width="1.1"/>')
    else:
      out.append(_symbol(kind, x + 20, cy - 4))
    out.append(f'<text x="{x + 66}" y="{cy + 15}" class="l">{escape(label)}</text>')
    cy += 38
  cy += 4
  bx = x
  for kind, label in [("spf", "SPF"), ("latent", "latent"), ("sotif", "SOTIF"), ("ccf", "CCF DFI-nn"),
                      ("ffi", "FFI"), ("ue", "outside item"), ("repeated", "repeated")]:
    bg, fg = BADGE_STYLE.get(kind, BADGE_STYLE["repeat"])
    w = _badge_w(label)
    out.append(f'<rect x="{bx}" y="{cy}" width="{w:.1f}" height="13" rx="6.5" fill="{bg}"/>')
    out.append(f'<text x="{bx + w / 2:.1f}" y="{cy + 9.5}" class="b" fill="{fg}">{escape(label)}</text>')
    bx += w + 5
  return out, cy + 20 - y


def render_sheet(tree: Tree, sheet_root: Node, sheet_no: int, n_sheets: int) -> str:
  box = make_box(sheet_root, sheet_root, True)
  width, height = layout(box)
  width = max(width, 980)
  body: list[str] = []
  draw_box(box, body)

  # Footer: notes, legend and title block.
  fy = height + 10
  footer: list[str] = []
  ny = fy
  legend, lh = _legend(MARGIN, ny)
  footer.extend(legend)
  tb_w, tb_h = 430, 92
  tb_x = width - MARGIN - tb_w
  tb_y = ny
  footer.append(f'<rect x="{tb_x}" y="{tb_y}" width="{tb_w}" height="{tb_h}" fill="#fff" stroke="#111" stroke-width="1.4"/>')
  rows = [
    ("h", f"LionDriver — FTA {tree.goal}"),
    ("l", tree.title[:70]),
    ("l", f"Sheet {sheet_no} of {n_sheets}   ·   top of sheet: {sheet_root.ident}"),
    ("l", f"Source: WP-A-04 §{tree.section} (analysis of record)"),
    ("s", "Generated by fta_diagrams.py — edit WP-A-04, not this file"),
  ]
  ry = tb_y + 6
  for cls, text in rows:
    ry += 16
    footer.append(f'<text x="{tb_x + 10}" y="{ry}" class="{cls}" text-anchor="start">{escape(text)}</text>')
  total_h = max(ny + lh, tb_y + tb_h) + MARGIN

  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{total_h:.0f}" ' +
          f'viewBox="0 0 {width:.0f} {total_h:.0f}" font-family="Helvetica, Arial, sans-serif">\n' +
          '<style>' +
          '.id{font-size:11px;font-weight:700;text-anchor:middle}' +
          '.d{font-size:10px;text-anchor:middle}' +
          '.n{font-size:9.5px;font-style:italic;text-anchor:middle;fill:#444}' +
          '.b{font-size:8.6px;font-weight:600;text-anchor:middle}' +
          '.h{font-size:12px;font-weight:700}' +
          '.l{font-size:10.5px}' +
          '.s{font-size:9px;fill:#555}' +
          '.w{stroke:#111;stroke-width:1.1}' +
          '</style>\n' +
          '<rect width="100%" height="100%" fill="#fff"/>\n' +
          f'<text x="{MARGIN}" y="{MARGIN + 6}" class="h">FTA {tree.goal} — {escape(tree.title)}' +
          f'{"" if n_sheets == 1 else f"  (sheet {sheet_no} of {n_sheets})"}</text>\n')
  return head + "\n".join(body + footer) + "\n</svg>\n"


def _walk_sheet(b: Box):
  yield b
  for c in b.children:
    yield from _walk_sheet(c)


# ---------------------------------------------------------------- outputs

def build() -> dict[str, str]:
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
  for tree in trees:
    sheets = paginate(tree)
    names = []
    for no, root in enumerate(sheets, 1):
      name = f"fta-{tree.goal}-{no}.svg"
      outputs[name] = render_sheet(tree, root, no, len(sheets))
      names.append(f"[{no}: {root.ident}]({name})")
    index.append(f"| {tree.goal} | {tree.root.ident} {tree.title} | {', '.join(names)} |")
  index += ["", "Symbols follow IEC 61025: rectangle = top or intermediate event; OR / AND gate beneath it; " +
            "circle = basic event; diamond = undeveloped event; triangle = transfer. " +
            "Tags: SPF (single point in the baseline design), latent, SOTIF, CCF (→ WP-A-03 DFI), " +
            "FFI (→ WP-A-02), repeated (event drawn again; defined where first shown).", ""]
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
