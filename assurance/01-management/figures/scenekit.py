#!/usr/bin/env python3
"""Top-down scene kit shared by the generated scene figures: one road, one car, one set of marks, one animation.

The reference style is the guide-word scene of WP-C-03 §4 (guideword_scenes.py): a 280 x 130 scene, seen from above,
with grass, verge, asphalt and white paint; the ego car red, other traffic grey; what should happen dashed green, what
does happen solid red, the gap between them shaded; an amber marker where the fault starts and a yellow ring with a
label at the moment it matters; status pills in the top-left corner. Scenes loop (SMIL, no script, DUR s) and a viewer
that does not animate shows the last frame, so every animated element's static pose is its end state.

What lives here is drawing only: palette, road builders, the car, the marks, the pills and the SMIL helpers. What a
scene shows (paths, timings, the behaviour models) stays with the figure that draws it.

Migrated: 02-concept/hara/guideword_scenes.py. Still on their own copies, to move here next: 02-concept/sotif/
sotif_scenes.py and fm_scenes.py, 08-analyses/figures/stpa_scenes.py (test_scenekit.PENDING lists them; the guard test
fails if a new figure draws the road outside this kit).

Standard library only; every function is deterministic.
"""

from __future__ import annotations

import math
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
         "info": ("#1E293B", "#E2E8F0", "#94A3B8")}   # status pill: fill, text, stroke

# ---------------------------------------------------------------- geometry (scene units; lane = 30, about 3.6 m)

W, H = 280, 130                            # scene viewBox
HALF_LANE = 15
TOP_EDGE, CENTRE_LINE, BOTTOM_EDGE = 39, 69, 99   # straight road: edge line, dashed centre line, edge line
OTHER_LANE, EGO_LANE = 54, 84              # straight road: lane centres
CAR_L = 22                                 # car length

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


def drive_t(samples, inner):
  """Time-keyed driving group on a straight road (heading 0): samples are (loop share 0..1, x, y); static pose = last."""
  keys = [DRIVE * f for f, _, _ in samples] + [1]
  vals = [f"{x:.1f},{y:.1f}" for _, x, y in samples] + [f"{samples[-1][1]:.1f},{samples[-1][2]:.1f}"]
  # thin the keyframes: SMIL handles linear interpolation between them
  keep = sorted({0, len(samples) - 1, *range(0, len(samples), 4)})
  keys = [keys[i] for i in keep] + [1]
  vals = [vals[i] for i in keep] + [vals[-1]]
  return f'<g transform="translate({samples[-1][1]:.1f} {samples[-1][2]:.1f})">{anim("transform", "translate", vals, keys)}{inner}</g>'


def draw_on(p, key):
  """Reveal a path from its start in step with the car (stroke-dashoffset over pathLength 1)."""
  seg = [math.dist(a, b) for a, b in zip(p, p[1:])]
  total, run, vals = sum(seg) or 1, 0.0, ["1"]
  for s in seg:
    run += s
    vals.append(f"{1 - run / total:.4f}")
  return anim("stroke-dashoffset", None, vals + ["0"], [0] + [key(x) for x, _ in p[1:]] + [1])


# ---------------------------------------------------------------- text

def t(x, y, s, size=11, fill=INK, weight=None, anchor=None, extra=""):
  a = f' text-anchor="{anchor}"' if anchor else ""
  w = f' font-weight="{weight}"' if weight else ""
  return f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" fill="{fill}"{w}{a}{extra}>{escape(s)}</text>'


def fit_x(x, label, size=8):
  """Keep a centred label inside the scene width."""
  half = text_w(label, size, True) / 2 + 5
  return round(min(W - half, max(half, x)), 1)


# ---------------------------------------------------------------- road

def direction_arrow(transform):
  return (f'<g transform="{transform}" opacity="0.55"><path d="M-6 -2 L2 -2 L2 -4.5 L8 0 L2 4.5 L2 2 L-6 2 Z" '
          f'fill="{ARROW}"/></g>')


def straight_road(arrow_y=OTHER_LANE):
  """A straight two-lane road across the scene."""
  return [f'<rect width="{W}" height="{H}" fill="{GRASS}"/>', f'<rect x="0" y="32" width="{W}" height="74" fill="{VERGE}"/>',
          f'<rect x="0" y="35" width="{W}" height="68" fill="{ASPHALT}"/>',
          f'<line x1="0" y1="{BOTTOM_EDGE}" x2="{W}" y2="{BOTTOM_EDGE}" stroke="{PAINT}" stroke-width="1.5"/>',
          f'<line x1="0" y1="{TOP_EDGE}" x2="{W}" y2="{TOP_EDGE}" stroke="{PAINT}" stroke-width="1.5"/>',
          f'<line x1="0" y1="{CENTRE_LINE}" x2="{W}" y2="{CENTRE_LINE}" stroke="{PAINT}" stroke-width="1.3" stroke-dasharray="9 9"/>',
          direction_arrow(f"translate(26 {arrow_y})")]


def curved_road(edge):
  """A two-lane road along any centre line; edge(k) gives the points offset k from the ego lane centre (+ is right)."""
  hl = HALF_LANE
  asphalt = d(edge(hl + 4) + edge(-3 * hl - 4)[::-1]) + " Z"
  return [f'<rect width="{W}" height="{H}" fill="{GRASS}"/>',
          *[f'<path d="{d(edge(k))}" fill="none" stroke="{VERGE}" stroke-width="7"/>' for k in (hl + 4, -3 * hl - 4)],
          f'<path d="{asphalt}" fill="{ASPHALT}"/>',
          *[f'<path d="{d(edge(k))}" fill="none" stroke="{PAINT}" stroke-width="1.5"/>' for k in (hl, -3 * hl)],
          f'<path d="{d(edge(-hl))}" fill="none" stroke="{PAINT}" stroke-width="1.3" stroke-dasharray="9 9"/>',
          direction_arrow(pose(edge(0), 6))]


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


def ego_body():
  return car_body(EGO, EGO_EDGE)


def other_body(stopped=False):
  """Other traffic; a stopped car is paler and shows its hazard lights."""
  if not stopped:
    return car_body(OTHER, OTHER_EDGE)
  return car_body(STOPPED, OTHER_EDGE) + (f'<rect x="-12" y="-5.5" width="2" height="2" fill="{HAZARD_LAMP}"/>'
                                          f'<rect x="-12" y="3.5" width="2" height="2" fill="{HAZARD_LAMP}"/>')


def ghost_body():
  """Where the car should be: a dashed green outline."""
  return f'<rect x="-11" y="-5" width="22" height="10" rx="3.5" fill="none" stroke="{REQ_S}" stroke-width="1.3" stroke-dasharray="3 2"/>'


def car(transform, body, opacity=1.0, stroke=INK):
  return f'<g transform="{transform}" opacity="{opacity:g}">{car_body(body, stroke)}</g>'


def start_marker(transform):
  """The car's starting position, faded."""
  return car(transform, PAINT, 0.45)


# ---------------------------------------------------------------- marks

def intended_path(p):
  return f'<path d="{d(p)}" fill="none" stroke="{REQ_S}" stroke-width="2.2" stroke-dasharray="5 3" stroke-linecap="round"/>'


def performed_path(path_d, reveal):
  """The car's actual track, drawn in by reveal (an animate on stroke-dashoffset)."""
  return (f'<path d="{path_d}" fill="none" stroke="{PERF_S}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" '
          f'pathLength="1" stroke-dasharray="1 1">{reveal}</path>')


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
          t(fit_x(x, label), label_y, label, 8, CALLOUT, 600, "middle", f' stroke="{INK}" stroke-width="2.4" paint-order="stroke"') + "</g>")


def badges(items, key):
  """Status pills in the scene's top-left corner: (text, from, to or None, style), times mapped by key()."""
  out, y = [], 6
  for text, t0, t1, style in items:
    fill, fg, stroke = BADGE[style]
    w = text_w(text, 7.5, True) + 12
    if t1 is None:
      a = appear(key(t0)) if t0 > 0 else ""
    else:
      a = window(key(t0), key(t1))
    out.append(f'<g>{a}<rect x="6" y="{y}" width="{w:.1f}" height="13" rx="6.5" fill="{fill}" stroke="{stroke}" stroke-width="1"/>' +
               t(12, y + 9.3, text, 7.5, fg, 700) + "</g>")
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
