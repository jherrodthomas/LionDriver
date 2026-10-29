#!/usr/bin/env python3
"""Draw the SysML views of the LionDriver architecture model as SVG figures.

Every figure comes from the model (../model/*.sysml) and the layout of the same view in
../views/layout.toml. The model decides what is drawn: elements, integrity, ports, interfaces,
mechanisms. The layout only decides where. Nothing in generated/ is edited by hand.

  render_views.py           regenerate generated/*.svg
  render_views.py --check   fail if a generated figure is out of date (CI)
"""
from __future__ import annotations

import hashlib
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import svgkit as k
import sysml_lite

SYSML_DIR = HERE.parent
LAYOUT = SYSML_DIR / "views" / "layout.toml"
OUT = SYSML_DIR / "generated"
TITLES: dict[str, str] = {}  # display names of elements, from [titles] in layout.toml
GENERATED = "Generated from assurance/models/sysml by tools/render_views.py — do not edit by hand"


def model_digest(m: sysml_lite.Model) -> str:
  h = hashlib.sha256()
  for p in [*m.files, LAYOUT]:
    h.update(p.read_bytes())
  return h.hexdigest()[:12]


# ---------------------------------------------------------------- styles

def style_of(e: sysml_lite.Element | None, override: str | None = None) -> dict:
  if override == "ml" or (e is not None and "MlElement" in e.classes):
    return k.ML
  if override:
    return {"envelope": k.ENVELOPE, "outside": k.OUTSIDE, "untrusted": k.UNTRUSTED, "slate": k.SLATE,
            "b": k.ASIL_B}[override]
  if e is None:
    return k.SLATE
  scope, integ = e.scope(), e.integrity()
  if integ == "Untrusted":
    return k.UNTRUSTED
  if scope != "inside":
    return k.OUTSIDE
  if integ in ("C", "BDagger"):
    return k.ENVELOPE
  if integ == "B":
    return k.ASIL_B
  return k.SLATE


def integrity_pill(x, y, e: sysml_lite.Element, anchor="end", h=17, size=9.5):
  integ = e.integrity()
  if integ is None:
    return "", 0
  label = k.INTEGRITY_LABEL[integ]
  if integ in ("C", "BDagger"):
    return k.pill(x, y, label, k.ENVELOPE["chip"], h=h, size=size, anchor=anchor)
  if integ == "B":
    return k.pill(x, y, label, k.ASIL_B["chip"], h=h, size=size, anchor=anchor)
  if integ == "QMBsup":
    return k.pill(x, y, label, "#FFFFFF", k.INK2, h=h, size=size, anchor=anchor, stroke=k.FAINT)
  if integ == "Untrusted":
    return k.pill(x, y, label, k.UNTRUSTED["chip"], h=h, size=size, anchor=anchor)
  if integ == "AoU":
    return k.pill(x, y, label, "#FFFFFF", k.MUTED, h=h, size=size, anchor=anchor, stroke=k.FAINT)
  return k.pill(x, y, label, k.SLATE["chip"], h=h, size=size, anchor=anchor)


def sm_line(e: sysml_lite.Element) -> str:
  nums = sorted(int(s[3:]) for s in e.performs)
  return "SM-" + " · ".join(f"{n:02d}" for n in nums) if nums else ""


# ---------------------------------------------------------------- figure frame

def header(w: float, view: sysml_lite.View, title: str, subtitle: str, digest: str) -> list[str]:
  out = [k.text(40, 46, f"{view.short} · {title}", 21, k.INK, 700),
         k.text(40, 69, subtitle, 12.5, k.MUTED),
         k.text(w - 40, 44, f"SysML v2 view LionDriverViews::{view.name}", 11, k.MUTED, 400, "end"),
         k.text(w - 40, 62, f"{view.definition} · render {view.render} · model {digest}", 11, k.MUTED, 400, "end"),
         f'<line x1="40" y1="86" x2="{k.f(w - 40)}" y2="86" stroke="{k.HAIR}"/>']
  return out


def footer(w: float, y: float, items: list[str]) -> list[str]:
  return [f'<line x1="40" y1="{k.f(y)}" x2="{k.f(w - 40)}" y2="{k.f(y)}" stroke="{k.HAIR}"/>', *items,
          k.text(40, y + 76, GENERATED, 9.5, k.FAINT)]


# ---------------------------------------------------------------- interconnection views

@dataclass
class Node:
  key: str
  box: tuple[float, float, float, float]
  element: sysml_lite.Element | None
  spec: dict
  kind: str = "card"     # frame, card, bus, external, actor, note

  @property
  def x(self):
    return self.box[0]

  @property
  def y(self):
    return self.box[1]

  @property
  def w(self):
    return self.box[2]

  @property
  def h(self):
    return self.box[3]

  @property
  def cx(self):
    return self.x + self.w / 2

  @property
  def cy(self):
    return self.y + self.h / 2


@dataclass
class Edge:
  a: str
  b: str
  cls: str
  ids: list[str]
  fwd: bool = True        # arrow at b
  back: bool = False      # arrow at a
  conns: list[str] = field(default_factory=list)
  spec: dict = field(default_factory=dict)
  label: str | None = None
  ports: bool = True
  group: str | None = None


CLASS_PRIORITY = ["actuation", "ffi", "boot", "sensing", "power", "network", "internal", "bus"]


def edge_class(c: sysml_lite.Connection) -> str:
  iid = c.interface_id or ""
  d = c.definition
  if d == "CanLink":
    return "actuation" if iid == "IF-01" else "sensing"
  if d == "SpiLink":
    return "ffi"
  if d == "GpioLink":
    return "boot" if iid == "IF-04b" else "actuation"
  if d == "PowerLink":
    return "power"
  if d == "NetworkLink":
    return "network"
  if d == "DataFlow":
    return "internal"
  if d == "HmiLink" and iid == "IF-07" and "siren" in c.end_ports[0]:
    return "actuation"
  return "sensing"


def orthogonal(pts: list[tuple[float, float]], horizontal_first: bool) -> list[tuple[float, float]]:
  """Insert a corner between consecutive points that differ in both coordinates."""
  out = [pts[0]]
  horiz = horizontal_first
  for q in pts[1:]:
    p = out[-1]
    if abs(p[0] - q[0]) > 0.5 and abs(p[1] - q[1]) > 0.5:
      out.append((q[0], p[1]) if horiz else (p[0], q[1]))
    out.append(q)
    a, b = out[-2], out[-1]
    horiz = abs(a[1] - b[1]) < 0.5
    horiz = not horiz
  return out


class Canvas:
  def __init__(self, m: sysml_lite.Model, vid: str, spec: dict):
    self.m, self.vid, self.spec = m, vid, spec
    self.nodes: dict[str, Node] = {}
    self.order: list[str] = []
    self.labels: list[tuple[float, float, float, float]] = []
    self.markers: dict[str, str] = {}

  # -- node placement
  def element(self, ident: str, within: sysml_lite.Element | None = None) -> sysml_lite.Element:
    if within is not None:
      for d in within.walk():
        if ident in (d.name, d.short):
          return d
    e = self.m.find(ident) or self.m.elements.get(ident) or self.m.elements.get("context." + ident)
    if e is None:
      e = next((x for x in self.m.elements.values() if x.kind == "part" and x.name == ident), None)
    if e is None:
      raise sysml_lite.ModelError(f"layout {self.vid}: {ident!r} is not an element of the model")
    return e

  def add(self, key: str, box, spec: dict, kind: str, within: sysml_lite.Element | None = None):
    el = None if kind in ("note", "band") else self.element(spec.get("el", key), within)
    n = Node(key, tuple(float(v) for v in box), el, spec, kind)
    self.nodes[key] = n
    self.order.append(key)
    return n

  def place(self):
    for spec in self.spec.get("node", []):
      kind = spec.get("kind", "card")
      key = spec.get("el", spec.get("key"))
      n = self.add(key, spec["box"], spec, kind)
      grid = spec.get("grid")
      if grid:
        self.place_grid(n, grid)

  def place_grid(self, parent: Node, grid: dict):
    rows = grid["rows"]
    x0, y0 = parent.x + grid.get("pad", 16), parent.y + grid.get("top", 46)
    gap_x, gap_y = grid.get("gap", 14), grid.get("vgap", 12)
    cols = max(len(r) for r in rows)
    cw = (parent.w - 2 * grid.get("pad", 16) - gap_x * (cols - 1)) / cols
    rh = grid.get("row_h", 58)
    for ri, row in enumerate(rows):
      for ci, ident in enumerate(row):
        if not ident:
          continue
        self.add(ident, (x0 + ci * (cw + gap_x), y0 + ri * (rh + gap_y), cw, rh),
                 {"el": ident, "_parent_integrity": parent.element.integrity()}, "card", parent.element)

  # -- which drawn node stands for a model path
  def visible(self, path: str) -> str | None:
    by_path = {n.element.path: key for key, n in self.nodes.items() if n.element is not None}
    p = path
    while True:
      if p in by_path:
        return by_path[p]
      if "." not in p:
        return None
      p = p.rsplit(".", 1)[0]

  # -- edges from the model connections
  def edges(self) -> list[Edge]:
    flows = self.spec.get("flows", False)
    raw: list[Edge] = []
    ignore_route = set(self.spec.get("ignore_route", []))
    for c in self.m.connections:
      if c.definition == "DataFlow" and not flows:
        continue
      a, b = self.visible(c.end_ports[0]), self.visible(c.end_ports[1])
      if a is None or b is None or a == b:
        continue
      if c.kind == "connect":
        raw.append(Edge(a, b, "bus", [], fwd=False, conns=[c.name or ""], ports=False))
        continue
      cls = edge_class(c)
      group = "can" if c.definition == "CanLink" else cls
      iid = c.interface_id
      route = (c.meta.get("InterfaceId") or {}).get("route") or []
      route = [route] if isinstance(route, str) else list(route)
      if c.name in ignore_route:
        route = []
      vias = [self.visible(self.element(r).path) for r in route]
      via = next((v for v in vias if v), None)
      ids = [iid] if iid else []
      name = c.name or ""
      if via and via not in (a, b):
        raw.append(Edge(a, via, cls, ids, conns=[name], group=group))
        raw.append(Edge(via, b, cls, ids, conns=[name], group=group))
      else:
        raw.append(Edge(a, b, cls, ids, conns=[name], group=group))
    # merge edges between the same pair of nodes and of the same kind (CAN TX and RX are one kind)
    merged: dict[tuple[str, str, str], Edge] = {}
    for e in raw:
      key = (*sorted((e.a, e.b)), e.group or e.cls)
      if key not in merged:
        merged[key] = Edge(key[0], key[1], e.cls, [], fwd=False, back=False, ports=e.ports, group=key[2])
      g = merged[key]
      if e.cls == "bus":
        pass
      elif e.a == g.a:
        g.fwd = True
      else:
        g.back = True
      for i in e.ids:
        if i not in g.ids:
          g.ids.append(i)
      g.conns += e.conns
      if CLASS_PRIORITY.index(e.cls) < CLASS_PRIORITY.index(g.cls):
        g.cls = e.cls
    overrides = self.spec.get("edge", [])
    out = []
    for g in merged.values():
      for o in overrides:
        if set(o.get("between", [])) == {g.a, g.b} and o.get("kind", g.group) == g.group:
          g.spec = o
          if o["between"][0] != g.a:
            g.a, g.b, g.fwd, g.back = g.b, g.a, g.back, g.fwd
      if g.spec.get("hide"):
        continue
      g.ids.sort()
      g.label = g.spec.get("label", " · ".join(g.ids) if g.ids else None) or None
      out.append(g)
    return out

  # -- routing
  def sides(self, e: Edge) -> tuple[str, str]:
    if "sides" in e.spec:
      return tuple(e.spec["sides"])
    A, B = self.nodes[e.a], self.nodes[e.b]
    if A.x + A.w <= B.x:
      return "right", "left"
    if B.x + B.w <= A.x:
      return "left", "right"
    if A.y + A.h <= B.y:
      return "bottom", "top"
    return "top", "bottom"

  def route(self, edges: list[Edge]) -> dict[int, list[tuple[float, float]]]:
    # attachment points: spread edges that share a side, ordered by where the other end is
    slots: dict[tuple[str, str], list[tuple[float, int, str]]] = {}
    sides = {}
    for i, e in enumerate(edges):
      sa, sb = self.sides(e)
      sides[i] = (sa, sb)
      A, B = self.nodes[e.a], self.nodes[e.b]
      for node, side, other in ((A, sa, B), (B, sb, A)):
        coord = other.cy if side in ("left", "right") else other.cx
        slots.setdefault((node.key, side), []).append((coord, i, "a" if node is A else "b"))
    attach: dict[tuple[int, str], tuple[float, float]] = {}
    for (key, side), lst in slots.items():
      n = self.nodes[key]
      lst.sort()
      horizontal = side in ("left", "right")
      lo, hi = (n.y + 14, n.y + n.h - 14) if horizontal else (n.x + 18, n.x + n.w - 18)
      for j, (coord, i, end) in enumerate(lst):
        e = edges[i]
        fixed = e.spec.get(f"{end}_at")
        other = self.nodes[e.b if end == "a" else e.a]
        if fixed is not None:
          pos = (n.y if horizontal else n.x) + fixed * (n.h if horizontal else n.w)
        elif n.kind == "bus":
          pos = min(max(other.cx if not horizontal else other.cy, lo), hi)
        elif len(lst) == 1:
          other = self.nodes[e.b if end == "a" else e.a]
          olo, ohi = (other.y, other.y + other.h) if horizontal else (other.x, other.x + other.w)
          a, b = max(lo, olo + 10), min(hi, ohi - 10)
          pos = (a + b) / 2 if a <= b else min(max(coord, lo), hi)
        else:
          pos = lo + (hi - lo) * (j + 1) / (len(lst) + 1)
        if horizontal:
          attach[(i, end)] = (n.x + (n.w if side == "right" else 0), pos)
        else:
          attach[(i, end)] = (pos, n.y + (n.h if side == "bottom" else 0))
    paths = {}
    for i, e in enumerate(edges):
      (x1, y1), (x2, y2) = attach[(i, "a")], attach[(i, "b")]
      sa, sb = sides[i]
      if "points" in e.spec:
        pts = orthogonal([(x1, y1), *[tuple(p) for p in e.spec["points"]], (x2, y2)], sa in ("left", "right"))
      elif sa in ("left", "right") and sb in ("left", "right"):
        if abs(y1 - y2) < 0.5:
          pts = [(x1, y1), (x2, y2)]
        else:
          mx = e.spec.get("mid", (x1 + x2) / 2)
          pts = [(x1, y1), (mx, y1), (mx, y2), (x2, y2)]
      elif sa in ("top", "bottom") and sb in ("top", "bottom"):
        if abs(x1 - x2) < 0.5:
          pts = [(x1, y1), (x2, y2)]
        else:
          my = e.spec.get("mid", (y1 + y2) / 2)
          pts = [(x1, y1), (x1, my), (x2, my), (x2, y2)]
      elif sa in ("left", "right"):
        pts = [(x1, y1), (x2, y1), (x2, y2)]
      else:
        pts = [(x1, y1), (x1, y2), (x2, y2)]
      paths[i] = pts
    return paths

  # -- drawing
  def marker(self, cls: str, ported: bool = False) -> str:
    mid = f"arr-{cls}{'-p' if ported else ''}"
    if mid not in self.markers:
      self.markers[mid] = k.arrow_marker(mid, k.EDGE[cls]["color"], back=4.5 if ported else 0)
    return mid

  def draw_edge(self, e: Edge, pts) -> tuple[list[str], list[str]]:
    st = k.EDGE[e.cls]
    mid = self.marker(e.cls, e.ports and e.cls != "internal")
    dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
    ms = f' marker-end="url(#{mid})"' if e.fwd else ""
    me = f' marker-start="url(#{mid})"' if e.back else ""
    lines = [f'<path d="{k.rounded_path(pts)}" fill="none" stroke="{st["color"]}" stroke-width="{st["width"]}"' +
             f' stroke-linejoin="round"{dash}{ms}{me}/>']
    over = []
    if e.ports and e.cls != "internal":
      for (px, py), node in ((pts[0], self.nodes[e.a]), (pts[-1], self.nodes[e.b])):
        if node.kind in ("bus",):
          continue
        over.append(k.rect(px - 4, py - 4, 8, 8, "#FFFFFF", st["color"], rx=1.5, sw=1.3))
    if e.label:
      over.append(self.edge_label(e, pts, st["color"]))
    return lines, over

  def edge_label(self, e: Edge, pts, color) -> str:
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    if "label_seg" in e.spec:
      (x1, y1), (x2, y2) = segs[e.spec["label_seg"]]
    else:
      (x1, y1), (x2, y2) = max(segs, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
    t = e.spec.get("label_t", 0.5)
    cx, cy = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
    w = k.text_w(e.label, 9.5, 700) + 14
    box = (cx - w / 2, cy - 9, w, 18)
    for _ in range(12):
      if not any(self._overlap(box, b) for b in self.labels):
        break
      if abs(x2 - x1) > abs(y2 - y1):
        cx += w * 0.6 * (1 if x2 > x1 else -1)
      else:
        cy += 22 * (1 if y2 > y1 else -1)
      box = (cx - w / 2, cy - 9, w, 18)
    self.labels.append(box)
    svg, _ = k.pill(cx, cy - 9, e.label, color, h=18, size=9.5, anchor="middle")
    return svg

  @staticmethod
  def _overlap(a, b) -> bool:
    return not (a[0] + a[2] < b[0] or b[0] + b[2] < a[0] or a[1] + a[3] < b[1] or b[1] + b[3] < a[1])

  def draw_node(self, n: Node) -> list[str]:
    s = n.spec
    if n.kind == "band":
      st = style_of(None, s.get("style", "slate"))
      svg, _ = k.pill(n.x, n.y, s["text"], st["chip"], h=n.h, size=10.5)
      return [k.rect(n.x, n.y, n.w, n.h, st["chip"], rx=n.h / 2),
              k.text(n.x + n.w / 2, n.y + n.h / 2 + 3.8, s["text"], 10.5, "#FFFFFF", 700, "middle",
                     extra=' letter-spacing="0.6"')]
    if n.kind == "note":
      out = []
      for i, ln in enumerate(s["text"]):
        out.append(k.text(n.x, n.y + 12 + i * 14, ln, s.get("size", 10.5), s.get("color", k.MUTED),
                          s.get("weight", 400), s.get("anchor")))
      return out
    e = n.element
    st = style_of(e, s.get("style"))
    titles, subs = self.spec.get("titles", {}), self.spec.get("subs", {})
    title = s.get("title") or titles.get(n.key) or self.default_title(e)
    sub = s.get("sub") or subs.get(n.key)
    if sub is None and n.kind == "card" and s.get("doc", True):
      sub = re.split(r"(?<=[a-z0-9)])[.;:] ", e.doc + " ")[0].strip().rstrip(".")
    if n.kind == "frame":
      out = [k.rect(n.x, n.y, n.w, n.h, s.get("fill", st.get("wash", st["fill"])), st["stroke"],
                    rx=12, sw=1.4, dash=s.get("dash"))]
      x = n.x + 16
      y = n.y + 26
      if e.short and re.match(r"E-0\d", e.short or ""):
        svg, w = k.pill(x, y - 13, e.short, st["chip"], h=18, size=10)
        out.append(svg)
        x += w + 8
      out.append(k.text(x, y + 0.5, title, 14, k.INK, 700))
      x += k.text_w(title, 14, 700) + 10
      if sub:
        out.append(k.text(x, y, sub, 11, k.MUTED))
      rx = n.x + n.w - 14
      if s.get("integrity", True):
        svg, pw = integrity_pill(rx, y - 12.5, e)
        out.append(svg)
        rx -= pw + 10
      if s.get("keyword", False):
        out.append(k.text(rx, y - 0.5, f"«part» {e.name} : {e.definition}", 9.5, k.FAINT, 400, "end", mono=True))
      smt = sm_line(e)
      if smt and s.get("sm", True):
        out.append(k.text(n.x + 16, n.y + n.h - 12, smt, 9.5, k.ENVELOPE["chip"], 700))
      return out
    if n.kind == "bus":
      out = [f'<line x1="{k.f(n.x)}" y1="{k.f(n.cy)}" x2="{k.f(n.x + n.w)}" y2="{k.f(n.cy)}" ' +
             f'stroke="{k.EDGE["bus"]["color"]}" stroke-width="4" stroke-linecap="round"/>',
             k.text(n.x, n.y - 2, title, 12, k.INK, 700)]
      if sub:
        out.append(k.text(n.x + k.text_w(title, 12, 700) + 10, n.y - 2, sub, 10.5, k.MUTED))
      return out
    # cards (inside, external, actor)
    fill = s.get("fill", st["fill"])
    dash = s.get("dash")
    if e.scope() == "excluded":
      fill, dash = "url(#hatch)", "4 3"
    out = [k.rect(n.x, n.y, n.w, n.h, fill, st["stroke"], rx=9, sw=1.2, dash=dash,
                  extra=' filter="url(#lift)"' if e.scope() == "inside" else "")]
    pad = 11
    if n.kind == "actor":
      out.append(k.actor(n.cx, n.y + 22, k.INK2, 1.0))
      out.append(k.text(n.cx, n.y + 84, title, 13, k.INK, 700, "middle"))
      for i, ln in enumerate(k.wrap(sub or "", n.w - 20, 10.5)):
        out.append(k.text(n.cx, n.y + 101 + i * 14, ln, 10.5, k.MUTED, 400, "middle"))
      return out
    narrow = n.w < 200
    y = n.y + 20
    x = n.x + pad
    right = n.x + n.w - pad
    show_id = e.short and not e.short.startswith(("host.", "panda.")) and s.get("id", True)
    if show_id:
      svg, w = k.pill(x, y - 12.5, e.short, st["chip"], h=17, size=9.5)
      out.append(svg)
      x += w + 7
    show_integrity = s.get("integrity", e.scope() == "inside" and e.integrity() != s.get("_parent_integrity"))
    if show_integrity and narrow and e.integrity():
      label = k.INTEGRITY_LABEL[e.integrity()]
      if k.text_w(title, 12, 700) + k.text_w(label, 9, 700) + 14 + 8 <= right - x:
        narrow = False
    ipw = 0
    if show_integrity and not narrow:
      svg, ipw = integrity_pill(right, y - 12.5, e, h=16, size=9)
      out.append(svg)
      ipw += 6
    out.append(k.text(x, y, k.clip(title, right - ipw - x, 12, 700), 12, k.INK, 700))
    yy = y + 16
    bottom = n.y + n.h - 9
    smt = sm_line(e) if s.get("sm", True) else ""
    foot = 0
    if show_integrity and narrow:
      foot = 22
    if smt:
      sm_lines = k.wrap(smt, n.w - 2 * pad, 9.5, 700)
      foot += 12 * len(sm_lines) + 2
    if sub:
      sub_lines = k.wrap(sub, n.w - 2 * pad, 10.5)
      room = max(0, int((bottom - foot - 4 - yy) // 13.5) + 1)
      if len(sub_lines) > room and room:
        sub_lines = sub_lines[:room]
        sub_lines[-1] = k.clip(sub_lines[-1].rstrip(" ·,") + " …", n.w - 2 * pad, 10.5)
      for ln in sub_lines[:room]:
        out.append(k.text(n.x + pad, yy, ln, 10.5, k.MUTED))
        yy += 13.5
    if s.get("list"):
      yy += 4
      out += self.chips(e, s, n.x + pad, yy, n.w - 2 * pad)
    fy = n.y + n.h - 9
    if smt:
      for i, ln in enumerate(reversed(sm_lines)):
        out.append(k.text(n.x + pad, fy - i * 12, ln, 9.5, k.ENVELOPE["chip"], 700))
      fy -= 12 * len(sm_lines) + 2
    if show_integrity and narrow:
      svg, _ = integrity_pill(n.x + pad, fy - 14, e, anchor="start", h=15, size=8.5)
      out.append(svg)
    return out

  def chips(self, e: sysml_lite.Element, s: dict, x0: float, y0: float, width: float) -> list[str]:
    mode = s.get("list")
    items: list[tuple[str, sysml_lite.Element]] = []
    for c in e.walk():
      if c is e:
        continue
      if mode == "units-inline":
        u = (c.meta.get("Unit") or {}).get("id")
        if u and u not in [i[0] for i in items]:
          items.append((u, c))
      elif c.parent is e:
        items.append((c.short or self.default_title(c).lower(), c))
    out, x, y = [], x0, y0
    for label, c in items:
      w = k.text_w(label, 8.8, mono=True) + 12
      if x + w > x0 + width:
        x, y = x0, y + 20
      integ = c.integrity()
      fill, stroke = ("#FFEDD5", "#FDBA74") if integ in ("C", "BDagger") else (
        ("#FFF7ED", "#FED7AA") if integ == "B" else ("#FFFFFF", k.HAIR))
      out.append(k.rect(x, y, w, 16, fill, stroke, rx=4, sw=1))
      out.append(k.text(x + 6, y + 11.4, label, 8.8, k.INK2, 400, mono=True))
      x += w + 5
    return out

  @staticmethod
  def default_title(e: sysml_lite.Element) -> str:
    if e.name in TITLES:
      return TITLES[e.name]
    if e.short and e.short.startswith(("host.", "panda.")):
      return e.short.split(".", 1)[1]
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", e.name).lower()
    return words[:1].upper() + words[1:]


def render_interconnection(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  cv = Canvas(m, vid, spec)
  cv.place()
  view = m.views[vid]
  w, h = spec["width"], spec["height"]
  body = header(w, view, spec["title"], spec["subtitle"], digest)
  def group(n: Node) -> list[str]:
    inner = cv.draw_node(n)
    if n.element is None:
      return inner
    return [f'<g data-el="{n.element.path}">', *inner, "</g>"]

  for key in cv.order:
    n = cv.nodes[key]
    if n.kind in ("frame", "band"):
      body += group(n)
  edges = cv.edges()
  paths = cv.route(edges)
  overlays = []
  for i, e in sorted(enumerate(edges), key=lambda x: -CLASS_PRIORITY.index(x[1].cls)):
    lines, over = cv.draw_edge(e, paths[i])
    pa, pb = cv.nodes[e.a].element.path, cv.nodes[e.b].element.path
    tag = f'<g data-edge="{e.group}" data-a="{pa}" data-b="{pb}" data-ids="{" ".join(e.ids)}">'
    body += [tag, *lines, "</g>"]
    overlays += [tag, *over, "</g>"] if over else []
  for key in cv.order:
    n = cv.nodes[key]
    if n.kind not in ("frame", "band"):
      body += group(n)
  body += overlays
  body += legend(w, h - 100, sorted({e.cls for e in edges}, key=CLASS_PRIORITY.index), spec)
  desc = spec.get("desc", view.doc)
  return k.svg_doc(w, h, f"{view.short}. {spec['title']} (SysML v2 view {view.name})", desc, body,
                   "".join(cv.markers.values()))


def legend(w: float, y: float, classes: list[str], spec: dict) -> list[str]:
  items = []
  x = 40
  for cls in classes:
    st = k.EDGE[cls]
    dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
    items.append(f'<line x1="{x}" y1="{k.f(y + 26)}" x2="{x + 26}" y2="{k.f(y + 26)}" stroke="{st["color"]}" ' +
                 f'stroke-width="{st["width"]}"{dash}/>')
    items.append(k.text(x + 34, y + 30, st["label"], 10.5, k.INK2))
    x += 34 + k.text_w(st["label"], 10.5) + 26
  x = 40
  yy = y + 50
  swatches = [(k.ENVELOPE, "ASIL C safety envelope"), (k.ASIL_B, "ASIL B element"), (k.SLATE, "QM element"),
              (k.ML, "ML element (E-02)"), (k.OUTSIDE, "Outside the item"), (k.UNTRUSTED, "Untrusted")]
  for st, label in swatches:
    items.append(k.rect(x, yy - 10, 22, 14, st["fill"], st["stroke"], rx=4))
    items.append(k.text(x + 30, yy + 1, label, 10.5, k.INK2))
    x += 30 + k.text_w(label, 10.5) + 22
  items.append(k.rect(x, yy - 7.5, 8, 8, "#FFFFFF", k.INK2, rx=1.5, sw=1.3))
  items.append(k.text(x + 14, yy + 1, "port (SysML)", 10.5, k.INK2))
  x += 14 + k.text_w("port (SysML)", 10.5) + 22
  items.append(k.text(x, yy + 1, "SM-nn", 10.5, k.ENVELOPE["chip"], 700))
  items.append(k.text(x + k.text_w("SM-nn", 10.5, 700) + 6, yy + 1, "safety mechanisms performed (WP-S-03 §6)",
                      10.5, k.INK2))
  return footer(w, y, items)


# ---------------------------------------------------------------- V-02 element hierarchy

def tree_rows(e: sysml_lite.Element, depth: int = 0) -> list[tuple[int, sysml_lite.Element]]:
  out = []
  for c in e.children:
    out.append((depth, c))
    out += tree_rows(c, depth + 1)
  return out


def node_label(e: sysml_lite.Element) -> tuple[str, bool]:
  """Label of a tree row and whether it is a code name (drawn in monospace)."""
  if e.short and e.short.startswith(("host.", "panda.")):
    return e.short, True
  if e.short and re.fullmatch(r"E-0\d[ab]?", e.short):
    return f"{e.short}  {Canvas.default_title(e)}", False
  return (e.short or Canvas.default_title(e)), False


INTEGRITY_DOT = {"C": "#C2410C", "BDagger": "#C2410C", "B": "#FB923C", "QMBsup": "#475569", "QM": "#CBD5E1", "AoU": "#E2E8F0"}


def render_hierarchy(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  item = m.elements["context.ldsda"]
  w = spec["width"]
  cols = spec["columns"]
  body = header(w, view, spec["title"], spec["subtitle"], digest)
  # item card
  iw, ih = 360, 74
  ix, iy = (w - iw) / 2, 112
  body.append(k.rect(ix, iy, iw, ih, "#FFFDF8", k.ENVELOPE["stroke"], rx=12, sw=1.6, dash="6 4"))
  svg, pw = k.pill(ix + 16, iy + 14, "ITEM", k.ENVELOPE["chip"], h=18, size=9.5)
  body.append(svg)
  body.append(k.text(ix + 16 + pw + 8, iy + 28, "LD-SDA", 15, k.INK, 700))
  body.append(k.text(ix + 16, iy + 50, "Supervised Driving Assistance · aftermarket SAE Level 2 retrofit", 10.5, k.MUTED))
  body.append(k.text(ix + 16, iy + 64, f"«part» ldsda : {item.definition}", 9.5, k.FAINT, mono=True))
  # columns
  gap = 18
  x = 40
  col_boxes = []
  top = 250
  max_bottom = top
  row_h = 19
  for col in cols:
    e = m.find(col["el"])
    cw = col["width"]
    st = style_of(e)
    rows = tree_rows(e)
    nsm = len({s for d in e.walk() for s in d.performs})
    nparts = len(rows)
    hh = 66
    ch = hh + 10 + row_h * len(rows) + 12
    body.append(k.rect(x, top, cw, ch, "#FFFFFF", k.HAIR, rx=12, sw=1.2, extra=' filter="url(#lift)"'))
    body.append(f'<path d="M{k.f(x)} {k.f(top + 12)}a12 12 0 0 1 12 -12h{k.f(cw - 24)}a12 12 0 0 1 12 12' +
                f'v{k.f(hh - 12)}h{k.f(-cw)}z" fill="{st.get("fill2", st["fill"])}" />')
    body.append(f'<line x1="{k.f(x)}" y1="{k.f(top + hh)}" x2="{k.f(x + cw)}" y2="{k.f(top + hh)}" stroke="{st["stroke"]}" stroke-width="1"/>')
    svg, pw = k.pill(x + 14, top + 13, e.short, st["chip"], h=18, size=10)
    body.append(svg)
    svg, _ = integrity_pill(x + cw - 14, top + 13, e, h=17, size=9.5)
    body.append(svg)
    body.append(k.text(x + 14, top + 46, k.clip(col.get("title", Canvas.default_title(e)), cw - 28, 13.5, 700),
                       13.5, k.INK, 700))
    meta = f"{nparts} parts · {nsm} SM" if nsm else f"{nparts} parts"
    body.append(k.text(x + 14, top + 60, meta, 10, k.MUTED))
    yy = top + hh + 10
    body.append(f'<g data-el="{e.path}"><rect x="{k.f(x)}" y="{k.f(top)}" width="{k.f(cw)}" height="{hh}" fill="transparent"/></g>')
    for depth, d in rows:
      body.append(f'<g data-el="{d.path}"><rect x="{k.f(x + 4)}" y="{k.f(yy)}" width="{k.f(cw - 8)}" height="{row_h}" rx="4" fill="transparent"/>')
      label, mono = node_label(d)
      indent = 14 + depth * 14
      group = bool(d.children)
      cy = yy + row_h / 2
      if depth:
        body.append(f'<path d="M{k.f(x + indent - 8)} {k.f(cy - row_h + 4)}V{k.f(cy)}h5" fill="none" ' +
                    f'stroke="{k.HAIR}" stroke-width="1.2"/>')
      dot = INTEGRITY_DOT.get(d.integrity() or "QM", "#CBD5E1")
      body.append(f'<circle cx="{k.f(x + indent + 3)}" cy="{k.f(cy)}" r="3.6" fill="{dot}"/>')
      unit = (d.meta.get("Unit") or {}).get("id")
      ref = str((d.meta.get("Unit") or {}).get("build", "")).endswith("reference")
      right = x + cw - 12
      tail = []
      if d.performs:
        tail.append((f"{len(d.performs)} SM", k.ENVELOPE["chip"], 700, False))
      if ref:
        tail.append(("[ref]", "#7C3AED", 700, False))
      if unit and (d.parent is None or (d.parent.meta.get("Unit") or {}).get("id") != unit):
        tail.append((unit, k.MUTED, 400, True))
      for txt, color, wt, mn in tail:
        body.append(k.text(right, cy + 3.4, txt, 9, color, wt, "end", mono=mn))
        right -= k.text_w(txt, 9, wt, mn) + 8
      size = 10.5 if not mono else 9.8
      weight = 600 if group else 400
      lab = k.clip(label, right - (x + indent + 12) - 4, size, weight, mono)
      body.append(k.text(x + indent + 12, cy + 3.6, lab, size, k.INK if group or depth == 0 else k.INK2, weight,
                         mono=mono))
      body.append("</g>")
      yy += row_h
    col_boxes.append((x, top, cw, ch))
    max_bottom = max(max_bottom, top + ch)
    x += cw + gap
  # composition: filled diamond at the owner (SysML part / composite association)
  bx, by = w / 2, iy + ih
  bar = top - 26
  body.append(f'<path d="M{k.f(bx)} {k.f(by)}l6 9l-6 9l-6 -9z" fill="{k.INK2}"/>')
  body.append(f'<line x1="{k.f(bx)}" y1="{k.f(by + 18)}" x2="{k.f(bx)}" y2="{k.f(bar)}" stroke="{k.INK2}" stroke-width="1.4"/>')
  xs = [cx + cw / 2 for cx, _, cw, _ in col_boxes]
  body.append(f'<line x1="{k.f(min(xs))}" y1="{k.f(bar)}" x2="{k.f(max(xs))}" y2="{k.f(bar)}" stroke="{k.INK2}" stroke-width="1.4"/>')
  for cx in xs:
    body.append(f'<line x1="{k.f(cx)}" y1="{k.f(bar)}" x2="{k.f(cx)}" y2="{k.f(top)}" stroke="{k.INK2}" stroke-width="1.4"/>')
  body.append(k.text(bx + 12, by + 30, f"{len(cols)} components", 10, k.MUTED))
  h = max_bottom + 110
  legend_y = max_bottom + 24
  items = []
  lx = 40
  for integ, label in (("C", "ASIL C"), ("B", "ASIL B"), ("QMBsup", "QM (B-sup)"), ("QM", "QM")):
    items.append(f'<circle cx="{lx + 4}" cy="{k.f(legend_y + 26)}" r="4" fill="{INTEGRITY_DOT[integ]}"/>')
    items.append(k.text(lx + 14, legend_y + 30, label, 10.5, k.INK2))
    lx += 14 + k.text_w(label, 10.5) + 24
  items.append(f'<path d="M{lx} {k.f(legend_y + 26)}l6 -5l6 5l-6 5z" fill="{k.INK2}"/>')
  items.append(k.text(lx + 18, legend_y + 30, "composite part (SysML)", 10.5, k.INK2))
  lx += 18 + k.text_w("composite part (SysML)", 10.5) + 24
  for txt, color, wt, mn, label in (("U-XXX", k.MUTED, 400, True, "software unit (WP-W-06 §2)"),
                                    ("[ref]", "#7C3AED", 700, False, "reference build only"),
                                    ("n SM", k.ENVELOPE["chip"], 700, False, "safety mechanisms performed")):
    items.append(k.text(lx, legend_y + 30, txt, 10, color, wt, mono=mn))
    lx += k.text_w(txt, 10, wt, mn) + 6
    items.append(k.text(lx, legend_y + 30, label, 10.5, k.INK2))
    lx += k.text_w(label, 10.5) + 24
  body += footer(w, legend_y, items)
  desc = spec.get("desc", view.doc)
  return k.svg_doc(w, h + 6, f"{view.short}. {spec['title']} (SysML v2 view {view.name})", desc, body)


# ---------------------------------------------------------------- V-04 mechanism allocation

DC_FILL = {"high": ("#9A3412", "#FFFFFF"), "medium": ("#FB923C", "#FFFFFF"), "low": ("#FED7AA", "#7C2D12"),
           "QM": ("#E2E8F0", "#334155")}


def dc_style(me: sysml_lite.Mechanism) -> tuple[str, str, str, str | None]:
  """Label, fill, text colour and outline of a mechanism's DC target: high, medium, low, QM, or its note (enabler)."""
  dc = me.dc_target.split(" ")[0].split("(")[0].strip().rstrip(",") or "—"
  key = "QM" if dc.startswith(("QM", "ASIL")) else dc
  fill, color = DC_FILL.get(key, ("#FFFFFF", k.MUTED))
  label = key if key in DC_FILL else (re.findall(r"\((\w+)\)", me.dc_target) or [dc])[0]
  return label, fill, color, None if key in DC_FILL else k.FAINT


def render_matrix(m: sysml_lite.Model, vid: str, spec: dict, digest: str) -> str:
  view = m.views[vid]
  cols = [m.find(c) for c in spec["columns"]]
  w = spec["width"]
  label_w, cell_w, row_h = 360, 74, 19
  x0 = 40
  cx0 = x0 + label_w
  dc_x = cx0 + cell_w * len(cols) + 24
  tsr_x = dc_x + 150
  order = {c.path: i for i, c in enumerate(cols)}
  mechs = sorted(m.mechanisms.values(), key=lambda me: (min(order.get(p, 99) for p in me.performers), int(me.short[3:])))
  body = header(w, view, spec["title"], spec["subtitle"], digest)
  top = 116
  # column headers
  for i, c in enumerate(cols):
    st = style_of(c)
    cx = cx0 + i * cell_w + cell_w / 2
    svg, _ = k.pill(cx, top, c.short, st["chip"], h=18, size=10, anchor="middle")
    body.append(svg)
    title = spec.get("titles", {}).get(c.short, Canvas.default_title(c))
    for j, ln in enumerate(k.wrap(title, cell_w - 6, 9.5)[:2]):
      body.append(k.text(cx, top + 34 + j * 12, ln, 9.5, k.INK2, 400, "middle"))
    n = sum(1 for me in mechs if c.path in me.performers)
    body.append(k.text(cx, top + 66, f"{n}", 13, st["chip"], 700, "middle"))
  body.append(k.text(x0, top + 66, "Safety mechanism (WP-S-03 §6)", 10.5, k.MUTED, 600))
  body.append(k.text(dc_x, top + 66, "DC target", 10.5, k.MUTED, 600))
  body.append(k.text(tsr_x, top + 66, "TSRs", 10.5, k.MUTED, 600))
  y = top + 80
  body.append(f'<line x1="{x0}" y1="{y}" x2="{w - 40}" y2="{y}" stroke="{k.HAIR}"/>')
  prev_group = None
  for r, me in enumerate(mechs):
    group = min(order.get(p, 99) for p in me.performers)
    if prev_group is not None and group != prev_group:
      y += 8
      body.append(f'<line x1="{x0}" y1="{k.f(y - 4)}" x2="{w - 40}" y2="{k.f(y - 4)}" stroke="{k.HAIR}"/>')
    prev_group = group
    cy = y + row_h / 2
    body.append(f'<g data-sm="{me.short}">')
    body.append(k.rect(x0, y, w - 80, row_h, k.WASH if r % 2 == 0 else "#FFFFFF", rx=3))
    body.append(k.text(x0 + 6, cy + 3.6, me.short, 10, k.ENVELOPE["chip"], 700))
    name = me.doc or me.name
    body.append(k.text(x0 + 56, cy + 3.6, k.clip(name, label_w - 64, 10.5), 10.5, k.INK))
    idx = sorted(order[p] for p in me.performers if p in order)
    if len(idx) > 1:
      xa, xb = cx0 + idx[0] * cell_w + cell_w / 2, cx0 + idx[-1] * cell_w + cell_w / 2
      body.append(f'<line x1="{k.f(xa)}" y1="{k.f(cy)}" x2="{k.f(xb)}" y2="{k.f(cy)}" stroke="#CBD5E1" stroke-width="2.4" stroke-linecap="round"/>')
    for i in idx:
      st = style_of(cols[i])
      body.append(f'<circle cx="{k.f(cx0 + i * cell_w + cell_w / 2)}" cy="{k.f(cy)}" r="5.6" fill="{st["chip"]}"/>')
    label, fill, color, stroke = dc_style(me)
    svg, _ = k.pill(dc_x, y + 1.5, label, fill, color, h=16, size=9, stroke=stroke)
    body.append(svg)
    tsr = ", ".join(s.replace("TSR-", "") for s in me.tsr)
    body.append(k.text(tsr_x, cy + 3.4, k.clip(tsr, w - 40 - tsr_x, 9.5, mono=True), 9.5, k.INK2, mono=True))
    body.append("</g>")
    y += row_h
  body.append(f'<line x1="{x0}" y1="{k.f(y + 4)}" x2="{w - 40}" y2="{k.f(y + 4)}" stroke="{k.HAIR}"/>')
  legend_y = y + 20
  items = []
  lx = 40
  for st, lab in ((k.SLATE, "performed by a QM element"), (k.ML, "by an ML element"),
                  (k.ENVELOPE, "by an ASIL C element")):
    items.append(f'<circle cx="{lx + 5}" cy="{k.f(legend_y + 26)}" r="5" fill="{st["chip"]}"/>')
    items.append(k.text(lx + 15, legend_y + 30, lab, 10.5, k.INK2))
    lx += 15 + k.text_w(lab, 10.5) + 20
  ly = k.f(legend_y + 26)
  items.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 26}" y2="{ly}" stroke="#CBD5E1" stroke-width="2.4" stroke-linecap="round"/>')
  items.append(k.text(lx + 34, legend_y + 30, "shared mechanism", 10.5, k.INK2))
  lx += 34 + k.text_w("shared mechanism", 10.5) + 24
  for dc in ("high", "medium", "low"):
    fill, color = DC_FILL[dc]
    svg, pw = k.pill(lx, legend_y + 18, dc, fill, color, h=16, size=9)
    items.append(svg)
    lx += pw + 6
  items.append(k.text(lx + 4, legend_y + 30, "DC target", 10.5, k.INK2))
  body += footer(w, legend_y, items)
  h = legend_y + 92
  desc = spec.get("desc", view.doc)
  return k.svg_doc(w, h, f"{view.short}. {spec['title']} (SysML v2 view {view.name})", desc, body)


# ---------------------------------------------------------------- main

def render_all(m: sysml_lite.Model) -> dict[str, str]:
  layout = tomllib.loads(LAYOUT.read_text(encoding="utf-8"))
  TITLES.clear()
  TITLES.update(layout.get("titles", {}))
  for name in TITLES:
    if not any(e.name == name for e in m.elements.values()):
      raise sysml_lite.ModelError(f"layout.toml [titles]: {name!r} is not an element name of the model")
  digest = model_digest(m)
  out = {}
  for vid, spec in layout["views"].items():
    if vid not in m.views:
      raise sysml_lite.ModelError(f"layout.toml: view {vid} is not declared in Views.sysml")
    kind = spec.get("kind", "interconnection")
    import render_arch
    import render_requirements
    import render_se
    render_requirements.rv = render_se.rv = render_arch.rv = sys.modules[__name__]  # with TITLES filled
    fn = {"interconnection": render_interconnection, "hierarchy": render_hierarchy, "matrix": render_matrix,
          **render_requirements.RENDERERS, **render_se.RENDERERS, **render_arch.RENDERERS}[kind]
    result = fn(m, vid, spec, digest)
    if isinstance(result, dict):  # a view drawn as several figures (e.g. one requirement diagram per function)
      out.update(result)
    else:
      out[spec["file"]] = result
    if "phone" in spec:  # the same view laid out again at phone width
      out[spec["phone"]["file"]] = render_arch.render_interconnection_phone(m, vid, spec, digest)
  import render_se
  out.update(render_se.extra_outputs(m))
  missing = sorted(set(m.views) - set(layout["views"]))
  if missing:
    print(f"warning: views without a layout: {', '.join(missing)}")
  return out


def main(argv: list[str]) -> int:
  m = sysml_lite.load()
  figures = render_all(m)
  stale = []
  for name, svg in figures.items():
    p = OUT / name
    if "--check" in argv:
      if not p.exists() or p.read_text(encoding="utf-8") != svg:
        stale.append(name)
    else:
      p.parent.mkdir(parents=True, exist_ok=True)
      p.write_text(svg, encoding="utf-8")
  if stale:
    print("FAIL out of date (run tools/render_views.py):", ", ".join(stale))
    return 1
  print(f"render_views: {len(figures)} figures {'up to date' if '--check' in argv else 'written'}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
