#!/usr/bin/env python3
"""Top-down scene kit shared by the generated scene figures: one road, one car, one set of marks, one animation.

The reference style is the guide-word scene of WP-C-03 §4 (guideword_scenes.py): a 280 x 130 scene, seen from above,
with grass, verge, asphalt and white paint; the ego car red, other traffic grey; what should happen dashed green, what
does happen solid red, the gap between them shaded; an amber marker where the fault starts and a yellow ring with a
label at the moment it matters; status pills in the top-left corner. Scenes loop (SMIL, no script, DUR s) and a viewer
that does not animate shows the last frame, so every animated element's static pose is its end state.

What lives here is drawing only: palette, road builders, the car, the marks, the pills and the SMIL helpers. What a
scene shows (paths, timings, the behaviour models) stays with the figure that draws it.

Three scene sizes, one look: the full scene (W x H); the strip (W x STRIP_H, the same road cropped to its two lanes) for
cards that show two scenes; and the large scene (LARGE_W x LARGE_H), the full scene scaled by LARGE_K so its lanes match
the STPA cards' hand-placed coordinates. Text and pills are not scaled: they are sized for reading at the card's size.

Drawn with it: 02-concept/hara/guideword_scenes.py and hazlog_cards.py; 02-concept/sotif/sotif_scenes.py and
fm_scenes.py; 08-analyses/figures/stpa_ls_scenes.py and tools/safety/fmea_cards.py (strip, through fm_scenes);
08-analyses/figures/stpa_scenes.py, 02-concept/figures/fig_c09_scenes.py and 02-concept/fsc/fsc_scenes.py (large).
test_scenekit fails if a new figure draws the road from its own copy of the palette.

Standard library only; every function is deterministic.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from figkit import INK, text_w

# ---------------------------------------------------------------- palette

GRASS, VERGE, ASPHALT, PAINT = "#C9DDBA", "#B9C7A6", "#565E69", "#F8FAFC"
ARROW = "#E5E7EB"                          # faded direction-of-travel arrow on the asphalt
EGO, EGO_EDGE = "#DC2626", "#450A0A"       # the item's car
OTHER, OTHER_EDGE = "#9CA3AF", "#4B5563"   # other traffic
STOPPED, HAZARD_LAMP = "#94A3B8", "#F59E0B"
GLASS, WHEEL, LAMP = "#1F2937", "#111827", "#FDE68A"
REQ, PERF = "#16A34A", "#DC2626"           # required (dashed) and performed (solid) on a white chart
REQ_S, PERF_S = "#4ADE80", "#F87171"       # the same on the dark road surface
FAULT, CALLOUT = "#FBBF24", "#FEF08A"      # fault starts; the moment it matters
BADGE = {"bad": ("#7F1D1D", "#FEE2E2", "#FCA5A5"), "ok": ("#14532D", "#DCFCE7", "#4ADE80"),
         "info": ("#1E293B", "#E2E8F0", "#94A3B8"), "drv": ("#1E3A8A", "#DBEAFE", "#93C5FD")}   # status pill: fill, text, stroke

# ---------------------------------------------------------------- geometry (scene units; lane = 30, about 3.6 m)

W, H = 280, 130                            # scene viewBox
HALF_LANE = 15
TOP_EDGE, CENTRE_LINE, BOTTOM_EDGE = 39, 69, 99   # straight road: edge line, dashed centre line, edge line
OTHER_LANE, EGO_LANE = 54, 84              # straight road: lane centres
CAR_L = 22                                 # car length
# strip: the straight road cropped to 280 x 80 (for cards with two scenes); the same lanes, moved up by STRIP_DY
STRIP_H, STRIP_DY = 80, -29
STRIP_TOP, STRIP_CENTRE, STRIP_BOTTOM = TOP_EDGE + STRIP_DY, CENTRE_LINE + STRIP_DY, BOTTOM_EDGE + STRIP_DY   # 10, 40, 70
STRIP_OTHER, STRIP_EGO = OTHER_LANE + STRIP_DY, EGO_LANE + STRIP_DY                                       # 25, 55
# large scene: the STPA, TARA and FSC cards draw in 460 x 250 with 63-unit lanes; the kit's scene scaled by LARGE_K and
# moved up by LARGE_DY puts the lane lines at 62 / 125 / 188, so their road, cars and marks keep the kit's proportions
LARGE_W, LARGE_H, LARGE_K, LARGE_DY = 460, 250, 2.1, -20

# ---------------------------------------------------------------- animation (SMIL, no script; a still viewer shows the last frame)

DUR, DRIVE = 6, 0.8                        # loop length in s; share of the loop spent driving, the rest holds the end


def anim(attr, kind, values, keys):
  kt = ";".join(f"{k:.4f}" for k in keys)
  tag = "animateTransform" if kind else "animate"
  ty = f' type="{kind}"' if kind else ""
  return f'<{tag} attributeName="{attr}"{ty} values="{";".join(values)}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'


def appear(k):
  """Hidden until loop time k (0..1), then shown to the end of the loop."""
  return f'<animate attributeName="opacity" values="0;1" keyTimes="0;{max(k, 0.001):.4f}" calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>'


def window(k0, k1):
  """Shown from loop time k0 to k1 only."""
  return (f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;{max(k0, .001):.4f};{k1:.4f};1" '
          f'calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>')


# ---------------------------------------------------------------- paths

def d(p):
  return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in p)


def heading(p, i):
  i = max(1, min(len(p) - 1, i))
  (x0, y0), (x1, y1) = p[i - 1], p[i]
  return math.degrees(math.atan2(y1 - y0, x1 - x0))


def pose(p, i):
  i = max(1, min(len(p) - 1, i))
  return f"translate({p[i][0]:.1f} {p[i][1]:.1f}) rotate({heading(p, i):.1f})"


def driving(p, inner, key):
  """A group that drives along p (keyed by key(x) -> loop time) and holds at its end; its static pose is the end."""
  keys = [key(x) for x, _ in p] + [1]
  tr = [f"{x:.1f},{y:.1f}" for x, y in p] + [f"{p[-1][0]:.1f},{p[-1][1]:.1f}"]
  rot = [f"{heading(p, i):.1f}" for i in range(len(p))] + [f"{heading(p, len(p) - 1):.1f}"]
  keys[0] = 0
  return (f'<g transform="translate({p[-1][0]:.1f} {p[-1][1]:.1f})">{anim("transform", "translate", tr, keys)}'
          f'<g transform="rotate({heading(p, len(p) - 1):.1f})">{anim("transform", "rotate", rot, keys)}{inner}</g></g>')


def drive_t(samples, inner, thin=True):
  """Time-keyed group that slides without turning: samples are (drive share 0..1, x, y); static pose = last."""
  keys = [DRIVE * f for f, _, _ in samples] + [1]
  vals = [f"{x:.1f},{y:.1f}" for _, x, y in samples] + [f"{samples[-1][1]:.1f},{samples[-1][2]:.1f}"]
  keys[0] = 0
  if thin:   # SMIL interpolates linearly between the kept keyframes; enough for a straight road
    keep = sorted({0, len(samples) - 1, *range(0, len(samples), 4)})
    keys = [keys[i] for i in keep] + [1]
    vals = [vals[i] for i in keep] + [vals[-1]]
  return f'<g transform="translate({samples[-1][1]:.1f} {samples[-1][2]:.1f})">{anim("transform", "translate", vals, keys)}{inner}</g>'


def drive_turning(samples, inner):
  """Time-keyed group that turns with its path: samples are (drive share 0..1, x, y); static pose = last.
  A sample that does not move keeps the heading it had."""
  keys = [0] + [DRIVE * f for f, _, _ in samples[1:]] + [1]
  heads, last = [], 0.0
  for i in range(len(samples)):
    j = max(1, i)
    (_, x0, y0), (_, x1, y1) = samples[j - 1], samples[j]
    if (x1, y1) != (x0, y0):
      last = math.degrees(math.atan2(y1 - y0, x1 - x0))
    heads.append(last)
  tr = [f"{x:.1f},{y:.1f}" for _, x, y in samples] + [f"{samples[-1][1]:.1f},{samples[-1][2]:.1f}"]
  rot = [f"{a:.1f}" for a in heads] + [f"{heads[-1]:.1f}"]
  _, xe, ye = samples[-1]
  return (f'<g transform="translate({xe:.1f} {ye:.1f})">{anim("transform", "translate", tr, keys)}'
          f'<g transform="rotate({heads[-1]:.1f})">{anim("transform", "rotate", rot, keys)}{inner}</g></g>')


def draw_on(p, keys):
  """Reveal path p from its start in step with the car: keys[i] is the loop time the car reaches p[i]."""
  seg = [math.dist(a, b) for a, b in zip(p, p[1:])]
  total, run, vals = sum(seg) or 1, 0.0, ["1"]
  for s in seg:
    run += s
    vals.append(f"{1 - run / total:.4f}")
  return anim("stroke-dashoffset", None, vals + ["0"], [0] + list(keys[1:]) + [1])


# ---------------------------------------------------------------- text

def t(x, y, s, size=11, fill=INK, weight=None, anchor=None, extra=""):
  a = f' text-anchor="{anchor}"' if anchor else ""
  w = f' font-weight="{weight}"' if weight else ""
  return f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" fill="{fill}"{w}{a}{extra}>{escape(s)}</text>'


def fit_x(x, label, size=8, anchor="middle", pad=5):
  """Keep a label inside the scene width."""
  w = text_w(label, size, True)
  if anchor == "start":
    return round(min(W - pad - w, max(pad, x)), 1)
  if anchor == "end":
    return round(min(W - pad, max(pad + w, x)), 1)
  return round(min(W - w / 2 - pad, max(w / 2 + pad, x)), 1)


def road_label(x, y, s, fill="#334155", size=7, weight=600, anchor="middle", halo=False, k=None):
  """A label in the scene: dark text on the verge or grass, or light text with a dark halo on the asphalt (halo=True);
  shown from loop time k when k is given."""
  extra = f' stroke="{INK}" stroke-width="2.4" paint-order="stroke"' if halo else ""
  lab = t(round(x, 1), round(y, 1), s, size, fill, weight, anchor, extra)
  return lab if k is None else f"<g>{appear(k)}{lab}</g>"


# ---------------------------------------------------------------- road

def direction_arrow(transform):
  return (f'<g transform="{transform}" opacity="0.55"><path d="M-6 -2 L2 -2 L2 -4.5 L8 0 L2 4.5 L2 2 L-6 2 Z" '
          f'fill="{ARROW}"/></g>')


def straight_road(arrow_y=OTHER_LANE, edge_right=True, under="", markings=True, width=W, faded=False):
  """A straight two-lane road across the scene. under: drawn on the asphalt below the paint (a seam, an exit, a
  crossing road); edge_right=False leaves the ego lane's edge line to the caller; markings=False is an unmarked road;
  faded: worn paint."""
  wd = f"{width:g}"
  op = ' opacity="0.35"' if faded else ""
  b = [f'<rect width="{wd}" height="{H}" fill="{GRASS}"/>', f'<rect x="0" y="32" width="{wd}" height="74" fill="{VERGE}"/>',
       f'<rect x="0" y="35" width="{wd}" height="68" fill="{ASPHALT}"/>']
  if under:
    b.append(under)
  if markings:
    if edge_right:
      b.append(f'<line x1="0" y1="{BOTTOM_EDGE}" x2="{wd}" y2="{BOTTOM_EDGE}" stroke="{PAINT}" stroke-width="1.5"{op}/>')
    b += [f'<line x1="0" y1="{TOP_EDGE}" x2="{wd}" y2="{TOP_EDGE}" stroke="{PAINT}" stroke-width="1.5"{op}/>',
          f'<line x1="0" y1="{CENTRE_LINE}" x2="{wd}" y2="{CENTRE_LINE}" stroke="{PAINT}" stroke-width="1.3" stroke-dasharray="9 9"{op}/>']
  return b + [direction_arrow(f"translate(26 {arrow_y})")]


def large_road(**kw):
  """straight_road() for the large scene (LARGE_W x LARGE_H)."""
  return [f'<rect width="{LARGE_W}" height="{LARGE_H}" fill="{GRASS}"/>', f'<g transform="translate(0 {LARGE_DY}) scale({LARGE_K})">',
          *straight_road(width=round(LARGE_W / LARGE_K, 2), **kw), "</g>"]


def single_lane_road(path_d, k=1.0):
  """One lane with edge lines on both sides along any path (a slip road, a curve); k scales it like the scene."""
  hl = HALF_LANE
  return [f'<path d="{path_d}" fill="none" stroke="{c}" stroke-width="{2 * r * k:.1f}"/>'
          for c, r in ((VERGE, hl + 7.5), (ASPHALT, hl + 4), (PAINT, hl + 0.75), (ASPHALT, hl - 0.75))]


def strip_road(markings=True):
  """The straight road cropped to a 280 x STRIP_H strip; draw on it with the STRIP_* coordinates."""
  return [f'<g transform="translate(0 {STRIP_DY})">', *straight_road(markings=markings), "</g>"]


def curved_road(edge, arrow=True):
  """A two-lane road along any centre line; edge(k) gives the points offset k from the ego lane centre (+ is right)."""
  hl = HALF_LANE
  asphalt = d(edge(hl + 4) + edge(-3 * hl - 4)[::-1]) + " Z"
  return [f'<rect width="{W}" height="{H}" fill="{GRASS}"/>',
          *[f'<path d="{d(edge(k))}" fill="none" stroke="{VERGE}" stroke-width="7"/>' for k in (hl + 4, -3 * hl - 4)],
          f'<path d="{asphalt}" fill="{ASPHALT}"/>',
          *[f'<path d="{d(edge(k))}" fill="none" stroke="{PAINT}" stroke-width="1.5"/>' for k in (hl, -3 * hl)],
          f'<path d="{d(edge(-hl))}" fill="none" stroke="{PAINT}" stroke-width="1.3" stroke-dasharray="9 9"/>',
          *([direction_arrow(pose(edge(0), 6))] if arrow else [])]


def traffic_light(stopx, green_at=None):
  """Stop line across the ego lane and a signal head on the verge; red, or red turning green at loop share green_at."""
  head = (f'<circle cx="{stopx + 6}" cy="118" r="3.4" fill="#DC2626">' +
          (anim("fill", None, ["#DC2626", "#22C55E", "#22C55E"], [0, DRIVE * green_at, 1]).replace("<animate ", '<animate calcMode="discrete" ')
           if green_at is not None else "") + "</circle>")
  return [f'<line x1="{stopx}" y1="70" x2="{stopx}" y2="98" stroke="{PAINT}" stroke-width="3"/>',
          f'<rect x="{stopx + 2}" y="112" width="8" height="12" rx="2" fill="{GLASS}"/>', head]


# ---------------------------------------------------------------- cars

def car_body(body, stroke=INK):
  """A car seen from above, 22 x 10 (plus wheels), facing +x; origin at its centre."""
  wheels = "".join(f'<rect x="{x}" y="{y}" width="4.5" height="2.4" rx="1" fill="{WHEEL}"/>' for x in (-8.5, 4.5) for y in (-6, 3.6))
  return (f'{wheels}<rect x="-11" y="-5" width="22" height="10" rx="3.5" fill="{body}" stroke="{stroke}" stroke-width="0.9"/>'
          f'<path d="M2.5 -4 L6.5 -3.2 L6.5 3.2 L2.5 4 Z" fill="{GLASS}" opacity="0.75"/>'
          f'<path d="M-6.5 -3.6 L-8.5 -3 L-8.5 3 L-6.5 3.6 Z" fill="{GLASS}" opacity="0.6"/>'
          f'<rect x="10" y="-4.2" width="1.2" height="2" fill="{LAMP}"/><rect x="10" y="2.2" width="1.2" height="2" fill="{LAMP}"/>')


def brake_lights():
  return f'<rect x="-12" y="-4.4" width="1.6" height="2.4" fill="{PERF_S}"/><rect x="-12" y="2" width="1.6" height="2.4" fill="{PERF_S}"/>'


def ego_body(brake=False):
  return car_body(EGO, EGO_EDGE) + (brake_lights() if brake else "")


def other_body(stopped=False):
  """Other traffic; a stopped car is paler and shows its hazard lights."""
  if not stopped:
    return car_body(OTHER, OTHER_EDGE)
  return car_body(STOPPED, OTHER_EDGE) + (f'<rect x="-12" y="-5.5" width="2" height="2" fill="{HAZARD_LAMP}"/>'
                                          f'<rect x="-12" y="3.5" width="2" height="2" fill="{HAZARD_LAMP}"/>')


def ghost_body(stroke=REQ_S):
  """Where the car should be: a dashed green outline (another stroke for what a sensor believes)."""
  return f'<rect x="-11" y="-5" width="22" height="10" rx="3.5" fill="none" stroke="{stroke}" stroke-width="1.3" stroke-dasharray="3 2"/>'


def car(transform, body, opacity=1.0, stroke=INK):
  return f'<g transform="{transform}" opacity="{opacity:g}">{car_body(body, stroke)}</g>'


def car_at(x, y, body, stroke=INK, opacity=1.0, angle=0):
  """A parked or stopped car at (x, y)."""
  return car(f"translate({x:.1f} {y:.1f}) rotate({angle:.1f})", body, opacity, stroke)


def pedestrian(samples):
  """A pedestrian seen from above, walking through samples (drive share, x, y)."""
  return drive_t(samples, f'<circle r="3.2" fill="{HAZARD_LAMP}" stroke="{INK}" stroke-width="0.8"/>'
                          f'<circle cx="0" cy="-0.5" r="1.4" fill="#7C2D12"/>', thin=False)


def start_marker(transform):
  """The car's starting position, faded."""
  return car(transform, PAINT, 0.45)


# ---------------------------------------------------------------- marks

def intended_path(p):
  return f'<path d="{d(p)}" fill="none" stroke="{REQ_S}" stroke-width="2.2" stroke-dasharray="5 3" stroke-linecap="round"/>'


def performed_path(path_d, reveal, color=PERF_S, width=2.6):
  """The car's actual track, drawn in by reveal (an animate on stroke-dashoffset)."""
  return (f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="{width:g}" stroke-linejoin="round" stroke-linecap="round" '
          f'pathLength="1" stroke-dasharray="1 1">{reveal}</path>')


def track(samples, color=PERF_S, width=2.6):
  """performed_path for time-keyed samples (drive share, x, y)."""
  p = [(x, y) for _, x, y in samples]
  return performed_path(d(p), draw_on(p, [DRIVE * f for f, _, _ in samples]), color, width)


def gap_band(band_d, uid, x0, x1):
  """The area between intended and actual, filled in behind the car (clipped to the distance driven so far)."""
  return [f'<clipPath id="r{uid}"><rect width="{W}" height="{H}">{anim("width", None, [str(x0), str(x1), str(W)], [0, DRIVE, 1])}</rect></clipPath>',
          f'<path d="{band_d}" fill="{PERF_S}" opacity="0.22" clip-path="url(#r{uid})"/>']


def fault_marker(x, y, k):
  """Amber marker with a bolt where the fault starts, shown from loop time k."""
  return (f'<g transform="translate({x:.1f} {y:.1f})">{appear(k)}<circle r="4.2" fill="{FAULT}" stroke="{INK}" stroke-width="0.9"/>'
          f'<path d="M0.6 -2.8 L-1.6 0.4 L0 0.4 L-0.6 2.8 L1.6 -0.4 L0 -0.4 Z" fill="{INK}"/></g>')


def callout(x, y, r, label, label_y, k):
  """Yellow ring at the moment it matters and its label, shown from loop time k."""
  return (f'<g>{appear(k)}<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:g}" fill="none" stroke="{CALLOUT}" stroke-width="1.6"/>' +
          road_label(fit_x(x, label), label_y, label, CALLOUT, 8, halo=True) + "</g>")


def pill(x, y, text, style, size=7.5, h=13, num=None, weight=700, font=None):
  """One status pill; with num, a numbered disc first (the number keys it to a mark on the card's chart). font: for a
  sheet whose root sets none."""
  fill, fg, stroke = BADGE[style]
  lead = h + 3 if num is not None else 6
  w = text_w(text, size, True) + lead + 6
  b = f'<rect x="{x:g}" y="{y:g}" width="{w:.1f}" height="{h:g}" rx="{h / 2:g}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
  if num is not None:
    b += (f'<circle cx="{x + h / 2 + 1:g}" cy="{y + h / 2:g}" r="{h / 2 - 3:g}" fill="{fg}"/>' +
          t(x + h / 2 + 1, round(y + h / 2 + size * 0.36, 1), str(num), size * 0.95, fill, 700, "middle"))
  b += t(x + lead, round(y + h / 2 + size * 0.374, 1), text, size, fg, weight)
  return f'<g font-family="{escape(font, {chr(34): "&quot;"})}">{b}</g>' if font else b


def badges(items, key):
  """Status pills in the scene's top-left corner: (text, from, to or None, style), times mapped by key()."""
  out, y = [], 6
  for text, t0, t1, style in items:
    if t1 is None:
      a = appear(key(t0)) if t0 > 0 else ""
    else:
      a = window(key(t0), key(t1))
    out.append(f"<g>{a}" + pill(6, y, text, style) + "</g>")
    y += 16
  return out


# ---------------------------------------------------------------- legend swatches (for a sheet's key, 12 units tall)

def legend_swatch(kind, x, y):
  """One legend mark at (x, y - 4); returns (svg, width used)."""
  if kind == "req":
    return f'<line x1="{x}" y1="{y - 4}" x2="{x + 26}" y2="{y - 4}" stroke="{REQ}" stroke-width="2.4" stroke-dasharray="6 3"/>', 32
  if kind == "perf":
    return f'<line x1="{x}" y1="{y - 4}" x2="{x + 26}" y2="{y - 4}" stroke="{PERF}" stroke-width="2.8"/>', 32
  if kind == "fault":
    return f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{FAULT}" stroke="{INK}" stroke-width="0.9"/>', 16
  if kind == "ring":
    return f'<circle cx="{x + 6}" cy="{y - 4}" r="6" fill="{ASPHALT}" stroke="{CALLOUT}" stroke-width="1.8"/>', 16
  if kind == "band":
    return f'<rect x="{x}" y="{y - 10}" width="20" height="12" fill="{PERF_S}" opacity="0.35"/>', 26
  if kind == "other":
    return car(f"translate({x + 11} {y - 4}) scale(0.9)", OTHER, 1, OTHER_EDGE), 26
  raise ValueError(kind)


# ---------------------------------------------------------------- the browser kit (scenekit.js) shares these constants

JS = Path(__file__).resolve().parent / "scenekit.js"
JS_BEGIN, JS_END = "/* constants: written by scenekit.py --js; do not edit */", "/* end constants */"


def constants() -> dict:
  """Everything scenekit.js must agree on with this module: palette, geometry, scene sizes, loop timing."""
  return dict(INK=INK, GRASS=GRASS, VERGE=VERGE, ASPHALT=ASPHALT, PAINT=PAINT, ARROW=ARROW, EGO=EGO, EGO_EDGE=EGO_EDGE,
              OTHER=OTHER, OTHER_EDGE=OTHER_EDGE, STOPPED=STOPPED, HAZARD_LAMP=HAZARD_LAMP, GLASS=GLASS, WHEEL=WHEEL, LAMP=LAMP,
              REQ=REQ, PERF=PERF, REQ_S=REQ_S, PERF_S=PERF_S, FAULT=FAULT, CALLOUT=CALLOUT, BADGE=BADGE,
              W=W, H=H, HALF_LANE=HALF_LANE, TOP_EDGE=TOP_EDGE, CENTRE_LINE=CENTRE_LINE, BOTTOM_EDGE=BOTTOM_EDGE,
              OTHER_LANE=OTHER_LANE, EGO_LANE=EGO_LANE, CAR_L=CAR_L, STRIP_H=STRIP_H, STRIP_DY=STRIP_DY,
              LARGE_W=LARGE_W, LARGE_H=LARGE_H, LARGE_K=LARGE_K, LARGE_DY=LARGE_DY, DUR=DUR, DRIVE=DRIVE)


def js_block() -> str:
  return f"{JS_BEGIN}\nconst SK = {json.dumps(constants(), indent=2)};\n{JS_END}"


def _js_with_block(src: str) -> str:
  pat = re.compile(re.escape(JS_BEGIN) + r".*?" + re.escape(JS_END), re.S)
  if not pat.search(src):
    raise SystemExit(f"{JS.name}: no constants block")
  return pat.sub(lambda m: js_block(), src)


def main(argv: list[str]) -> int:
  """--js writes the constants block into scenekit.js; --check fails if it is stale."""
  src = JS.read_text(encoding="utf-8")
  new = _js_with_block(src)
  if "--check" in argv:
    if new != src:
      print(f"scenekit: {JS.name} constants are stale; run python3 scenekit.py --js")
      return 1
    print(f"scenekit: {JS.name} constants current")
    return 0
  if "--js" in argv:
    JS.write_text(new, encoding="utf-8")
    print(f"scenekit: wrote the constants block of {JS.name}")
    return 0
  print(main.__doc__)
  return 2


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
