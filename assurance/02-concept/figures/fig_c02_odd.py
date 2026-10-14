#!/usr/bin/env python3
"""Draw the WP-C-02 ODD figures (Figure 3-1 ODD taxonomy, Figure 3-2 speed-curvature envelope).

The source of record is `../WP-C-02-odd-and-intended-functionality.md`:
  - Figure 3-1 is generated from the §3.1 ODD taxonomy table (category, attribute, included in ODD-H and
    ODD-A). The status tags (proposed, to be validated, TBD) are listed in FLAGS below; each carries the
    exact text it was read from (`src`).
  - Figure 3-2 plots the §3.2 table points (speed, R_ctrl, R_ODD) and the two curves R = v²/a that the §3.2
    text states. The two lateral accelerations and every prose value are listed in PROSE with their `src`.
`--check` fails when a `src` text no longer appears in WP-C-02 (or, for the controller limit, in
drive_helpers.py), when the §3.2 table no longer equals its formulas, or when a committed SVG differs.

    python3 fig_c02_odd.py            # regenerate the SVGs
    python3 fig_c02_odd.py --check    # fail if a source text changed or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-02-odd-and-intended-functionality.md"
REPO = HERE.parents[2]
DRIVE_HELPERS = REPO / "openpilot" / "selfdrive" / "controls" / "lib" / "drive_helpers.py"

# ---------------------------------------------------------------- palette (assurance figure style)

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
CHIP = "#F8FAFC"
SAFETY, SAFETY_BG = "#C2410C", "#FFF7ED"
SW, SW_BG = "#0F766E", "#F0FDFA"
AMBER, AMBER_BG = "#D97706", "#FFFBEB"
RED, RED_BG = "#D2553F", "#FEF2F2"
GREY_BG = "#F1F5F9"
SCOPE = "#B45309"

# ---------------------------------------------------------------- prose values (each with its source text)

PROSE = {
  "a_ctrl": {"value": 3.0, "src": ["R_ctrl = v² / 3.0 m/s² is the curve the controller can command at its lateral acceleration limit"]},
  "a_odd": {"value": 2.5, "src": ["R_ODD = v² / 2.5 m/s² is the proposed ODD bound"]},
  "margin": {"value": 0.5, "src": ["(0.5 m/s² margin for controller error, road crown and wind)"]},
  "aou": {"src": ["Both assume the EPS torque authority suffices; that is not yet characterised (GAP-04, AOU-01)."]},
  "chill": {"src": ["The planner in Chill mode does not reduce speed ahead of curves",
                    "Entering a curve tighter than R_ODD at the current speed is therefore a driver task."]},
  "saturated": {"src": ["| Curve tighter than R_ODD | Partly: `steerSaturated` warning when the controller saturates (`events.py:619`) | Warning only |"]},
  "v_odd_h": {"value": 120, "src": ["| Ego speed | 0 – 120 km/h (75 mph), not above the posted limit |"]},
  "v_odd_a": {"value": 90, "src": ["| 0 – 90 km/h (55 mph), not above the posted limit |"]},
  "oi2": {"src": ["| OI-2 | Characterise EPS torque authority and confirm R_ODD (§3.2)"]},
}
# The controller limit is also read from the code it cites (drive_helpers.py:14).
CODE_SRC = "MAX_LATERAL_ACCEL_NO_ROLL = 3.0  # m/s^2"

# Status tags of §3.1 attributes: (category, attribute) -> (kind, tag text, source texts).
# kind "proposed": a bound that is proposed or still to be confirmed; "tbd": a placeholder without a value.
FLAGS = {
  ("Geometry", "Horizontal curve radius"): (
    "proposed", "proposed · GAP-04, OI-2",
    ["R_ODD = v² / 2.5 m/s² is the proposed ODD bound", "torque authority not yet characterised (GAP-04)"]),
  ("Geometry", "Longitudinal grade"): (
    "proposed", "to be validated · OI-5",
    ["Pitch compensation in `carcontroller.py` (±1.5 m/s²); to be validated",
     "| OI-5 | Confirm grade and banking bounds (6 %) by vehicle test |"]),
  ("Geometry", "Cross-slope / banking"): (
    "proposed", "to be confirmed · OI-5", ["| OI-5 | Confirm grade and banking bounds (6 %) by vehicle test |"]),
  ("Weather", "Ambient temperature"): (
    "tbd", "TBD · OI-3", ["(to be specified from device data, OI-3)", "| OI-3 | Obtain the device operating temperature range"]),
}
ODD_A_SRC = ["| OI-4 | Confirm ODD-A inclusion with the HARA owner"]
PROPOSED_SRC = ["## 3. Reference ODD (proposed)"]
PLACEHOLDER = re.compile(r"\b(TBD|TBC|to be specified|placeholder)\b", re.I)
DRIVER_ACTS = re.compile(r"driver must act", re.I)

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


def pill(x, y, s, fill, size=10) -> list[str]:
  """A status tag: rounded rect height 18 with white bold text, left edge at x, vertical centre at y."""
  w = 12 + 5.9 * len(s) * size / 10
  return [rect(x, y - 9, w, 18, fill=fill, stroke="none", rx=9),
          text(x + w / 2, y + 3.5, s, size=size, fill="#FFFFFF", weight=700, anchor="middle")]


def pill_width(s: str, size=10) -> float:
  return 12 + 5.9 * len(s) * size / 10


MARKERS = {"muted": MUTED, "faint": FAINT, "amber": AMBER}


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  defs = "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" ' +
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k, c in MARKERS.items())
  defs += ('<pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">' +
           f'<line x1="0" y1="0" x2="0" y2="8" stroke="{FAINT}" stroke-width="1.2"/></pattern>')
  defs += ('<pattern id="hatch-amber" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">' +
           f'<rect width="8" height="8" fill="{AMBER_BG}"/><line x1="0" y1="0" x2="0" y2="8" stroke="#FCD34D" ' +
           'stroke-width="1.4"/></pattern>')
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" ' +
          f'font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc), f"<defs>{defs}</defs>",
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def header(width: int, number: str, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


def legend(x: float, y: float, entries: list[tuple[str, str, str]]) -> list[str]:
  """entries: (fill, stroke, label); a stroke ending in ' dashed' is drawn dashed."""
  out = []
  for fill, stroke, label in entries:
    dash = ""
    if stroke.endswith(" dashed"):
      stroke, dash = stroke[:-7], "4 3"
    out.append(rect(x, y - 10, 14, 12, fill=fill, stroke=stroke, rx=3, dash=dash))
    out.append(text(x + 20, y, label, size=11, fill=MUTED))
    x += 34 + 6.2 * len(label)
  return out


def wrap(s: str, width_px: float, size=10.5) -> list[str]:
  """Greedy word wrap with a conservative average glyph width."""
  limit = max(8, int(width_px / (0.53 * size)))
  out: list[str] = []
  cur = ""
  for w in s.split():
    if cur and len(cur) + 1 + len(w) > limit:
      out.append(cur)
      cur = w
    else:
      cur = f"{cur} {w}" if cur else w
  if cur:
    out.append(cur)
  return out or [""]


# ---------------------------------------------------------------- source parsing


def split_row(row: str) -> list[str]:
  cells = re.split(r"(?<!\\)\|", row.strip())
  return [c.strip() for c in cells[1:-1]]


def section(md: str, heading: str) -> str:
  body = md.split(heading, 1)[1]
  return re.split(r"\n#{2,3} ", body, maxsplit=1)[0]


def table(body: str) -> list[list[str]]:
  rows = [split_row(r) for r in body.splitlines() if r.startswith("|")]
  return [r for r in rows[2:] if r]  # skip header and separator


def plain(s: str) -> str:
  return s.replace("**", "").replace("`", "").strip()


def taxonomy(md: str) -> list[dict]:
  """§3.1 rows: category, attribute, ODD-H value, ODD-A value (None when 'same' or equal), basis."""
  body = section(md, "### 3.1 ODD taxonomy")
  head = split_row(next(r for r in body.splitlines() if r.startswith("|")))
  want = ["Category", "Attribute", "Included (ODD-H)", "Included (ODD-A)", "Excluded", "Basis"]
  if head != want:
    raise SystemExit(f"WP-C-02 §3.1 header changed: {head}; update fig_c02_odd.py")
  out = []
  for cat, attr, h, a, _excl, basis in table(body):
    h, a = plain(h), plain(a)
    if a.lower() == "same" or a == h:
      a_val = None
    elif a.lower().startswith("same "):
      a_val = "Same as ODD-H " + a[5:]
    else:
      a_val = a
    out.append({"cat": cat, "attr": attr, "h": h, "a": a_val, "basis": basis})
  return out


def curve_table(md: str) -> list[tuple[int, float, int, int]]:
  """§3.2 rows: speed km/h, speed m/s, R_ctrl m, R_ODD m."""
  body = section(md, "### 3.2 Minimum curve radius versus speed")
  head = split_row(next(r for r in body.splitlines() if r.startswith("|")))
  if head != ["Speed (km/h)", "Speed (m/s)", "R_ctrl (m)", "R_ODD (m)"]:
    raise SystemExit(f"WP-C-02 §3.2 header changed: {head}; update fig_c02_odd.py")
  return [(int(k), float(m), int(c), int(o)) for k, m, c, o in table(body)]


def radius(kmh: float, a: float) -> float:
  v = kmh / 3.6
  return v * v / a


def sources() -> list[str]:
  out = list(PROPOSED_SRC) + list(ODD_A_SRC)
  for p in PROSE.values():
    out += p["src"]
  for _k, _t, src in FLAGS.values():
    out += src
  return out


def problems(md: str) -> list[str]:
  """Everything that makes the figures disagree with their sources."""
  out = [f"source text no longer in WP-C-02: {s}" for s in sources() if s not in md]
  if CODE_SRC not in DRIVE_HELPERS.read_text(encoding="utf-8"):
    out.append(f"source text no longer in {DRIVE_HELPERS.relative_to(REPO)}: {CODE_SRC}")
  for kmh, ms, rc, ro in curve_table(md):
    if round(kmh / 3.6, 1) != ms:
      out.append(f"§3.2 {kmh} km/h: table says {ms} m/s, {kmh}/3.6 = {kmh / 3.6:.2f}")
    for name, a, r in (("R_ctrl", PROSE["a_ctrl"]["value"], rc), ("R_ODD", PROSE["a_odd"]["value"], ro)):
      if round(radius(kmh, a)) != r:
        out.append(f"§3.2 {kmh} km/h: table {name} = {r} m, formula v²/{a} = {radius(kmh, a):.1f} m")
  rows = taxonomy(md)
  keys = {(r["cat"], r["attr"]) for r in rows}
  for k in FLAGS:
    if k not in keys:
      out.append(f"FLAGS names {k}, which is no longer a §3.1 row")
  for r in rows:
    for cell in (r["h"], r["a"] or ""):
      if PLACEHOLDER.search(cell) and FLAGS.get((r["cat"], r["attr"]), ("",))[0] != "tbd":
        out.append(f"§3.1 {r['cat']} / {r['attr']} has a placeholder but no 'tbd' flag in FLAGS")
  return out


# ---------------------------------------------------------------- Figure 3-1 ODD taxonomy

W = 1280
X_ROOT, W_ROOT = 40, 128
X_CAT, W_CAT = 196, 150
X_ATTR, W_ATTR = 376, 196
X_H = 600
X_A = 924
W_VAL = 316
LINE_H = 14


def figure_3_1(md: str) -> str:
  rows = taxonomy(md)
  b: list[str] = []
  b += header(W, "3-1", "ODD taxonomy",
              "Reference ODD of §3.1 by category and attribute, with the value included in ODD-H and ODD-A. " +
              "The whole ODD is proposed.", "WP-C-02 §3.1")
  top = 122
  b.append(text(X_CAT, top - 16, "Category", size=11, fill=MUTED, weight=700))
  b.append(text(X_ATTR, top - 16, "Attribute", size=11, fill=MUTED, weight=700))
  b.append(text(X_H, top - 16, "ODD-H · limited-access highway", size=11, fill=MUTED, weight=700))
  b.append(text(X_A, top - 16, "ODD-A · arterial and rural", size=11, fill=MUTED, weight=700))
  oi4 = "to be confirmed · OI-4"
  b += pill(X_A + W_VAL - pill_width(oi4, 9), top - 20, oi4, AMBER, size=9)

  y = top
  cats: list[tuple[str, float, float, list[float]]] = []
  prev = None
  body: list[str] = []
  for r in rows:
    if r["cat"] != prev:
      if prev is not None:
        y += 8
      cats.append((r["cat"], y, y, []))
      prev = r["cat"]
    flag = FLAGS.get((r["cat"], r["attr"]))
    merged = r["a"] is None
    vw = (X_A + W_VAL - X_H) if merged else W_VAL
    tag_w = 96 if merged else 0
    h_lines = wrap(r["h"], vw - 20 - tag_w)
    a_lines = [] if merged else wrap(r["a"], W_VAL - 20)
    attr_lines = wrap(r["attr"], W_ATTR - 20, size=11.5)
    n_attr = len(attr_lines) + (1.4 if flag else 0)
    n = max(len(h_lines), len(a_lines), n_attr, 1)
    h = LINE_H * n + 14
    cy = y + h / 2
    # attribute box
    stroke, dash, fill = LINE, "", "#FFFFFF"
    if flag:
      stroke, dash, fill = AMBER, "4 3", AMBER_BG
    body.append(rect(X_ATTR, y, W_ATTR, h, fill=fill, stroke=stroke, dash=dash, rx=8, sw=1.3))
    ty = y + 7 + 11 + (h - 14 - LINE_H * n_attr) / 2
    for i, s in enumerate(attr_lines):
      body.append(text(X_ATTR + 10, ty + LINE_H * i, s, size=11.5, weight=600))
    if flag:
      body += pill(X_ATTR + 10, ty + LINE_H * len(attr_lines) + 5, flag[1], AMBER if flag[0] == "proposed" else RED, size=9)
    body.append(line(X_ATTR + W_ATTR, cy, X_H, cy, stroke=FAINT, sw=1.2))
    # value boxes
    for x, lines_, width, is_merged in ((X_H, h_lines, vw, merged), (X_A, a_lines, W_VAL, False)):
      if x == X_A and merged:
        continue
      cell = r["h"] if x == X_H else (r["a"] or "")
      tbd = flag is not None and flag[0] == "tbd"
      driver = bool(DRIVER_ACTS.search(cell))
      nothing = cell.strip() in ("—", "-", "")
      vfill, vstroke, vdash = "#FFFFFF", LINE, ""
      if tbd:
        vfill, vstroke, vdash = "url(#hatch-amber)", AMBER, "4 3"
      elif nothing:
        vfill, vstroke, vdash = GREY_BG, FAINT, "4 3"
      body.append(rect(x, y, width, h, fill=vfill, stroke=vstroke, dash=vdash, rx=8, sw=1.2))
      if driver:
        body.append(rect(x, y, 5, h, fill=SAFETY, stroke="none", rx=2))
      if nothing:
        lines_ = ["nothing included (exclusions only)"]
      ty = y + 7 + 10.5 + (h - 14 - LINE_H * len(lines_)) / 2
      for i, s in enumerate(lines_):
        body.append(text(x + 12, ty + LINE_H * i, s, size=10.5, fill=MUTED if nothing else INK,
                         style="italic" if nothing else ""))
      if is_merged:
        body.append(text(x + width - 12, y + 7 + 10.5 + (h - 14 - LINE_H) / 2, "ODD-H = ODD-A", size=10, fill=FAINT,
                         anchor="end", weight=600))
    c = cats[-1]
    cats[-1] = (c[0], c[1], y + h, [*c[3], cy])
    y += h + 6
  bottom = y - 6

  # category boxes and their branches
  trunk_x = X_ATTR - 14
  cat_cys = []
  for name, y0, y1, cys in cats:
    hh = y1 - y0
    b.append(rect(X_CAT, y0, W_CAT, hh, fill=CHIP, stroke="#64748B", rx=8, sw=1.3))
    b.append(text(X_CAT + W_CAT / 2, y0 + hh / 2 + 4, name, size=12, weight=700, anchor="middle"))
    ccy = y0 + hh / 2
    cat_cys.append(ccy)
    if len(cys) > 1:
      b.append(line(X_CAT + W_CAT, ccy, trunk_x, ccy, stroke=FAINT, sw=1.2))
      b.append(line(trunk_x, cys[0], trunk_x, cys[-1], stroke=FAINT, sw=1.2))
      for cy in cys:
        b.append(line(trunk_x, cy, X_ATTR, cy, stroke=FAINT, sw=1.2))
    else:
      b.append(line(X_CAT + W_CAT, ccy, X_ATTR, ccy, stroke=FAINT, sw=1.2))
  b += body

  # root
  root_trunk = X_CAT - 14
  rh = 96
  ry = (cat_cys[0] + cat_cys[-1]) / 2 - rh / 2
  b.append(line(root_trunk, cat_cys[0], root_trunk, cat_cys[-1], stroke=MUTED, sw=1.3))
  b.append(line(X_ROOT + W_ROOT, ry + rh / 2, root_trunk, ry + rh / 2, stroke=MUTED, sw=1.3))
  for cy in cat_cys:
    b.append(line(root_trunk, cy, X_CAT, cy, stroke=MUTED, sw=1.3))
  b.append(rect(X_ROOT, ry, W_ROOT, rh, fill="#FFFBEB", stroke=SCOPE, dash="10 5", rx=10, sw=1.5))
  b.append(text(X_ROOT + W_ROOT / 2, ry + 30, "Reference ODD", size=13, weight=700, anchor="middle"))
  b.append(text(X_ROOT + W_ROOT / 2, ry + 48, "ODD-H + ODD-A", size=10.5, fill=MUTED, anchor="middle"))
  b += pill(X_ROOT + (W_ROOT - pill_width("proposed", 10)) / 2, ry + 70, "proposed", SCOPE)

  # legend
  ly = bottom + 30
  b.append(line(40, ly - 18, W - 40, ly - 18, stroke=HAIR, sw=1))
  b += legend(40, ly, [
    ("#FFFBEB", SCOPE + " dashed", "proposed ODD (§3 heading)"),
    (AMBER_BG, AMBER + " dashed", "bound proposed or to be confirmed (open item named)"),
    ("url(#hatch-amber)", AMBER + " dashed", "TBD: no value yet"),
    (GREY_BG, FAINT + " dashed", "nothing included"),
  ])
  b.append(rect(40, ly + 14, 5, 12, fill=SAFETY, stroke="none", rx=2))
  b.append(text(60, ly + 24, "value says the system does not handle it reliably; the driver must act", size=11, fill=MUTED))
  b.append(text(560, ly + 24, "ODD-H = ODD-A: the table says “same” (or gives the same value); one box spans both columns", size=11,
                fill=MUTED))
  b.append(text(40, ly + 48, "Drawn with the table’s own categories; the excluded conditions and the basis of each row are in §3.1. " +
                "Status tags: §3.2, §3.1 Basis and the open items of §7.", size=11, fill=MUTED))
  height = int(ly + 72)
  desc = ("Tree of the reference ODD of WP-C-02 §3.1: " + ", ".join(c[0] for c in cats) + ". " +
          "Each attribute shows the value included in ODD-H and in ODD-A. The horizontal curve radius bound is proposed " +
          "(GAP-04, OI-2), grade and banking bounds are to be confirmed (OI-5), the ambient temperature bound is TBD (OI-3), " +
          "and the ODD-A inclusion is to be confirmed (OI-4).")
  return svg(W, height, "Figure 3-1 · ODD taxonomy", desc, b)


# ---------------------------------------------------------------- Figure 3-2 speed-curvature envelope

PX0, PX1, PY0, PY1 = 110, 1000, 124, 604
V_MAX, R_MAX = 130, 600


def sx(kmh: float) -> float:
  return PX0 + (PX1 - PX0) * kmh / V_MAX


def sy(r: float) -> float:
  return PY1 - (PY1 - PY0) * r / R_MAX


def curve_points(a: float, reverse=False) -> list[tuple[float, float]]:
  pts = [(sx(k / 2), sy(radius(k / 2, a))) for k in range(2 * V_MAX + 1)]
  return pts[::-1] if reverse else pts


def poly(pts: list[tuple[float, float]]) -> str:
  return "M" + " L".join(f"{fmt(x)},{fmt(y)}" for x, y in pts) + " Z"


def polyline(pts: list[tuple[float, float]]) -> str:
  return "M" + " L".join(f"{fmt(x)},{fmt(y)}" for x, y in pts)


def figure_3_2(md: str) -> str:
  a_ctrl, a_odd = PROSE["a_ctrl"]["value"], PROSE["a_odd"]["value"]
  margin = PROSE["margin"]["value"]
  pts = curve_table(md)
  vh, va = PROSE["v_odd_h"]["value"], PROSE["v_odd_a"]["value"]
  b: list[str] = []
  b += header(W, "3-2", "ODD speed–curvature envelope",
              "Minimum curve radius against ego speed: the controller limit, the proposed ODD bound and the margin between them.",
              "WP-C-02 §3.2")
  # regions
  b.append(path(poly([(sx(0), sy(R_MAX)), (sx(V_MAX), sy(R_MAX)), *curve_points(a_odd, reverse=True)]),
                fill=SW_BG, stroke="none"))
  b.append(path(poly([*curve_points(a_odd), *curve_points(a_ctrl, reverse=True)]), fill=AMBER_BG, stroke="none"))
  b.append(path(poly([*curve_points(a_ctrl), (sx(V_MAX), sy(0)), (sx(0), sy(0))]), fill=RED_BG, stroke="none"))
  # above the ODD-H speed bound
  b.append(rect(sx(vh), PY0, sx(V_MAX) - sx(vh), PY1 - PY0, fill="url(#hatch)", stroke="none", rx=0, sw=0))
  # grid and axes
  for k in range(0, V_MAX + 1, 10):
    b.append(line(sx(k), PY0, sx(k), PY1, stroke=HAIR, sw=1))
    b.append(text(sx(k), PY1 + 18, str(k), size=11, fill=MUTED, anchor="middle"))
  for r in range(0, R_MAX + 1, 100):
    b.append(line(PX0, sy(r), PX1, sy(r), stroke=HAIR, sw=1))
    b.append(text(PX0 - 10, sy(r) + 4, str(r), size=11, fill=MUTED, anchor="end"))
  b.append(rect(PX0, PY0, PX1 - PX0, PY1 - PY0, fill="none", stroke=FAINT, rx=0, sw=1))
  b.append(text((PX0 + PX1) / 2, PY1 + 42, "Ego speed v (km/h)", size=12, weight=600, anchor="middle"))
  b.append(el("text", "Minimum curve radius R (m)", x=56, y=fmt((PY0 + PY1) / 2), font_size=12, font_weight=600, fill=INK,
              text_anchor="middle", transform=f"rotate(-90 56 {fmt((PY0 + PY1) / 2)})"))
  # speed bounds of §3.1
  for v, label in ((va, f"ODD-A ≤ {va} km/h"), (vh, f"ODD-H ≤ {vh} km/h")):
    b.append(line(sx(v), PY0, sx(v), PY1, stroke=MUTED, sw=1.2, dash="6 4"))
    b.append(text(sx(v), PY0 - 8, label, size=11, fill=MUTED, anchor="middle", weight=600))
  b.append(text((sx(vh) + sx(V_MAX)) / 2, PY0 + 18, "above", size=10, fill=MUTED, anchor="middle", weight=600))
  b.append(text((sx(vh) + sx(V_MAX)) / 2, PY0 + 31, "ODD speed", size=10, fill=MUTED, anchor="middle", weight=600))
  # curves
  b.append(path(polyline(curve_points(a_ctrl)), stroke=SAFETY, sw=2.2))
  b.append(path(polyline(curve_points(a_odd)), stroke=SW, sw=2.2, dash="8 5"))
  # table points
  for kmh, _ms, rc, ro in pts:
    b.append(el("circle", None, cx=fmt(sx(kmh)), cy=fmt(sy(ro)), r=4.5, fill="#FFFFFF", stroke=SW, stroke_width=2))
    b.append(el("circle", None, cx=fmt(sx(kmh)), cy=fmt(sy(rc)), r=4.5, fill="#FFFFFF", stroke=SAFETY, stroke_width=2))
    b.append(text(sx(kmh) - 8, sy(ro) - 7, f"{ro} m", size=10.5, fill=SW, anchor="end", weight=700))
    b.append(text(sx(kmh) + 8, sy(rc) + 15, f"{rc} m", size=10.5, fill=SAFETY, weight=700))
  # curve labels right of the plot
  lx = PX1 + 14
  yo, yc = sy(radius(V_MAX, a_odd)), sy(radius(V_MAX, a_ctrl))
  b.append(text(lx, yo - 2, f"R_ODD = v² / {a_odd} m/s²", size=12, fill=SW, weight=700))
  b += pill(lx, yo + 14, "proposed, not approved", SW)
  b.append(text(lx, yc - 2, f"R_ctrl = v² / {a_ctrl} m/s²", size=12, fill=SAFETY, weight=700))
  b.append(text(lx, yc + 14, "controller limit,", size=10.5, fill=MUTED))
  b.append(text(lx, yc + 28, "drive_helpers.py:14", size=10.5, fill=MUTED, family=MONO))
  # AOU-01 honesty tag
  ay = yc + 52
  b.append(rect(lx, ay, W - 40 - lx, 92, fill=AMBER_BG, stroke=AMBER, dash="4 3", rx=8, sw=1.3))
  b += pill(lx + 10, ay + 18, "assumes AOU-01 (unverified)", AMBER)
  for i, s in enumerate(["Both curves assume the EPS", "torque authority suffices; not", "yet characterised (GAP-04, OI-2)."]):
    b.append(text(lx + 10, ay + 44 + 14 * i, s, size=10.5, fill=INK))
  # region labels
  b.append(text(sx(6), sy(540), "Inside the proposed ODD", size=14, fill=SW, weight=700))
  b.append(text(sx(6), sy(540) + 18, f"R ≥ R_ODD, lateral acceleration ≤ {a_odd} m/s²", size=11.5, fill=INK))
  b.append(text(sx(6), sy(540) + 34, "(and speed within the ODD-H / ODD-A bound)", size=11, fill=MUTED))
  # margin callout
  mx, my = sx(44), sy(400)
  vk = 64
  tx, tyy = sx(vk), sy((radius(vk, a_odd) + radius(vk, a_ctrl)) / 2)
  b.append(text(mx, my, f"Margin {margin} m/s²: R_ctrl ≤ R < R_ODD", size=13, fill=AMBER, weight=700))
  b.append(text(mx, my + 17, "for controller error, road crown and wind", size=11.5, fill=INK))
  b.append(text(mx, my + 33, "outside the proposed ODD: driver task", size=11, fill=MUTED))
  b.append(line(mx + 40, my + 42, tx - 3, tyy - 5, stroke=AMBER, sw=1.4, marker="amber"))
  # beyond controller authority: between the two speed bounds, where the region below R_ctrl is tallest
  dx, dy = sx(va) + 9, sy(radius(va, a_ctrl)) + 50
  b.append(text(dx, dy, "Beyond controller", size=12.5, fill=RED, weight=700))
  b.append(text(dx, dy + 16, "authority: R < R_ctrl", size=12.5, fill=RED, weight=700))
  for i, s in enumerate([f"lateral acceleration > {a_ctrl} m/s²", "driver task: Chill mode does", "not slow for curves"]):
    b.append(text(dx, dy + 36 + 15 * i, s, size=11, fill=INK))
  b.append(text(dx, dy + 86, "system: steerSaturated", size=10.5, fill=MUTED))
  b.append(text(dx, dy + 100, "warning only (§5.2)", size=10.5, fill=MUTED))
  # legend and footnote
  ly = PY1 + 82
  b.append(line(40, ly - 20, W - 40, ly - 20, stroke=HAIR, sw=1))
  b += legend(40, ly, [
    (SW_BG, SW_BG, "inside the proposed ODD"),
    (AMBER_BG, AMBER_BG, "margin, driver task"),
    (RED_BG, RED_BG, "beyond controller authority, driver task"),
    ("url(#hatch)", FAINT, f"above the ODD-H speed bound ({vh} km/h, §3.1)"),
  ])
  lx2 = 40
  b.append(line(lx2, ly + 22, lx2 + 26, ly + 22, stroke=SAFETY, sw=2.2))
  b.append(text(lx2 + 34, ly + 26, "R_ctrl (code limit)", size=11, fill=MUTED))
  b.append(line(lx2 + 170, ly + 22, lx2 + 196, ly + 22, stroke=SW, sw=2.2, dash="8 5"))
  b.append(text(lx2 + 204, ly + 26, "R_ODD (proposed)", size=11, fill=MUTED))
  b.append(el("circle", None, cx=lx2 + 336, cy=ly + 22, r=4.5, fill="#FFFFFF", stroke=MUTED, stroke_width=2))
  b.append(text(lx2 + 348, ly + 26, "points and numbers: §3.2 table (rounded to 1 m); curves: the §3.2 formulas", size=11, fill=MUTED))
  b.append(text(40, ly + 52, "Footnote: both curves assume the EPS torque authority suffices to reach the lateral acceleration. " +
                "That is not yet characterised (GAP-04, AOU-01); OI-2 confirms or adjusts R_ODD.", size=11, fill=MUTED))
  height = int(ly + 76)
  desc = (f"Plot of minimum curve radius R in metres against ego speed 0 to {V_MAX} km/h. The solid curve R_ctrl = v²/{a_ctrl} m/s² " +
          f"is the controller lateral-acceleration limit; the dashed curve R_ODD = v²/{a_odd} m/s² is the proposed ODD bound. " +
          "Above R_ODD is inside the proposed ODD; between the curves is the 0.5 m/s² margin; below R_ctrl is beyond controller " +
          "authority. Both are driver tasks. Table points: " +
          "; ".join(f"{k} km/h R_ctrl {c} m, R_ODD {o} m" for k, _m, c, o in pts) +
          f". Speed bounds {va} and {vh} km/h are marked. Both curves assume AOU-01, EPS torque authority, which is unverified (GAP-04).")
  return svg(W, height, "Figure 3-2 · ODD speed–curvature envelope", desc, b)


# ---------------------------------------------------------------- build / check

OUTPUTS = {
  "fig-c02-3-1-odd-taxonomy.svg": figure_3_1,
  "fig-c02-3-2-odd-envelope.svg": figure_3_2,
}


def build(md: str | None = None) -> dict[str, str]:
  md = md if md is not None else SOURCE.read_text(encoding="utf-8")
  return {name: fn(md) for name, fn in OUTPUTS.items()}


def main(argv: list[str]) -> int:
  md = SOURCE.read_text(encoding="utf-8")
  issues = problems(md)
  if issues:
    for s in issues:
      print(s, file=sys.stderr)
    print("review the figure data in fig_c02_odd.py against WP-C-02 and regenerate", file=sys.stderr)
    return 1
  outputs = build(md)
  if "--check" in argv:
    stale = [n for n, t in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != t]
    for n in stale:
      print(f"{(HERE / n).relative_to(REPO)} is stale; run fig_c02_odd.py", file=sys.stderr)
    if not stale:
      print(f"WP-C-02 figures: {len(outputs)} up to date")
    return 1 if stale else 0
  for n, t in outputs.items():
    (HERE / n).write_text(t, encoding="utf-8")
    print(f"wrote {(HERE / n).relative_to(REPO)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
