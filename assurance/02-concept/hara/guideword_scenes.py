#!/usr/bin/env python3
"""Draw the guide-word scene sheet: one card per guide word, the function against time over a top-down road scene.

- Guide-word scenes (`fig-c03-4-1-f01-guide-words.svg`): F-01 lateral control (lane centring) under the 14 guide words
  M01...M14 of WP-C-03. Each card shows what the function must deliver over time (required, dashed green) against
  what the malfunction delivers (performed, red), and under it what that does to the car on a two-lane left curve:
  intended path, actual path, where the fault starts and the moment it matters (edge line, next lane, off the road).
  Each card loops (SMIL, no script, 6 s): the cars drive their paths, the red track draws in behind the car, the fault
  marker and the callout appear when they happen, and a cursor moves along the time axis. A viewer that does not
  animate shows the last frame.

The guide words, classes, hazards, subsumption and rationale come from `hara_model.FM`; the safety goal and its ASIL
come from WP-C-03 §6 (through `hara_figures.parse_hara`, which checks the goal table). The behaviour curves below are
schematic: they explain each hazard and are not simulation results (the plant runs are in assurance/sim §3.7).

A function gets a sheet once it has a behaviour model here; the build fails if a model is missing for one of its
SC guide words or exists for a guide word that is not SC. Regenerate with `python3 hara_figures.py`.

Standard library only.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hara_figures as hf  # noqa: E402
import hara_model as hm  # noqa: E402
from hara_figures import HAIR, INK, MUTED, FigureError, pill, svg_doc, t, wrap  # noqa: E402

REQ, PERF = "#16A34A", "#DC2626"          # required (dashed) and performed (solid) in the chart
REQ_S, PERF_S = "#4ADE80", "#F87171"      # the same on the dark road surface
FAULT, CALLOUT = "#FBBF24", "#FEF08A"

SUB = {"M01": "fails to occur", "M02": "stops mid-execution", "M03": "when not commanded", "M04": "stuck at one value",
       "M05": "above the intended", "M06": "below the intended", "M07": "before the command", "M08": "after the command",
       "M09": "ends early", "M10": "does not stop", "M11": "slow response", "M12": "wrong direction",
       "M13": "unstable, oscillating", "M14": "left differs from right"}

# ---------------------------------------------------------------- chart: function against time (0..100 each axis)

CX0, CX1, CY0, CY1 = 28, 268, 12, 96      # plot area inside a 280 x 110 viewBox


def _xt(tp):
  return CX0 + tp / 100 * (CX1 - CX0)


def _yt(f):
  return CY1 - 2 if f == 0 else CY1 - f / 100 * (CY1 - CY0)


def step(pts):
  d = f"M{_xt(pts[0][0]):.1f} {_yt(pts[0][1]):.1f}"
  for (_, fp), (tp, f) in zip(pts, pts[1:]):
    d += f" L{_xt(tp):.1f} {_yt(fp):.1f}" + (f" L{_xt(tp):.1f} {_yt(f):.1f}" if f != fp else "")
  return d


def ramp(pts):
  return "M" + " L".join(f"{_xt(tp):.1f} {_yt(f):.1f}" for tp, f in pts)


def _biaxial(a, b):
  ym = (CY0 + CY1) / 2
  y = lambda f: ym - f / 100 * (CY1 - CY0) / 2
  return [f"M{_xt(0):.1f} {y(0):.1f} L{_xt(20):.1f} {y(0):.1f} L{_xt(20):.1f} {y(v):.1f} L{_xt(100):.1f} {y(v):.1f}"
          for v in (a, b)], ym


# ---------------------------------------------------------------- scene: a two-lane left curve, 280 x 130

W, H = 280, 15                            # scene width; half lane width (lane = 30 units, about 3.6 m)
X0, XE = 14, 262                          # path start and end


def cy(x):
  return 104 - 46 * (x / W) ** 2


def tan(x0):
  s, y0 = -92 * x0 / W ** 2, cy(x0)
  return lambda x: cy(x) if x < x0 else y0 + s * (x - x0)


def sm(x, a, w):
  return 0 if x < a else (1 if x > a + w else (1 - math.cos(math.pi * (x - a) / w)) / 2)


CENTRE = cy
TO_LEFT = lambda x: cy(x) - 2 * H * sm(x, 60, 70)   # noqa: E731  lane change to the left (inner) lane

R = [[0, 0], [20, 0], [20, 70], [100, 70]]
_ERR = [[0, 0], [20, 0], [20, 70]] + [[22 + i * 6.5, v] for i, v in enumerate([70, 88, 50, 78, 55, 82, 60, 90, 45, 75, 58, 80])] + [[100, 80]]

# guide word: (required, performed, scene intended path, scene actual path, callout if no line is crossed)
F01 = {
  "M01": (step(R), step([[0, 0], [100, 0]]), CENTRE, tan(10), ""),
  "M02": (step(R), step([[0, 0], [20, 0], [20, 70], [55, 70], [55, 0], [100, 0]]), CENTRE, tan(120), ""),
  "M03": (step([[0, 0], [100, 0]]), step([[0, 0], [15, 0], [15, 70], [28, 70], [28, 0], [55, 0], [55, 70], [68, 70], [68, 0], [100, 0]]),
          CENTRE, lambda x: cy(x) - 2 * H * sm(x, 90, 50) + 2 * H * sm(x, 170, 70), ""),
  "M04": (step([[0, 0], [15, 0], [15, 70], [45, 70], [45, 30], [75, 30], [75, 70], [100, 70]]), step([[0, 40], [100, 40]]),
          CENTRE, lambda x: cy(x) + (0 if x < 80 else 0.0016 * (x - 80) ** 2), ""),
  "M05": (step(R), step([[0, 0], [20, 0], [20, 95], [100, 95]]), CENTRE, lambda x: cy(x) - 3.2 * H * sm(x, 90, 40), ""),
  "M06": (step(R), step([[0, 0], [20, 0], [20, 35], [100, 35]]), CENTRE, lambda x: (cy(x) + tan(10)(x)) / 2, ""),
  "M07": (step([[0, 0], [40, 0], [40, 70], [100, 70]]), step([[0, 0], [20, 0], [20, 70], [100, 70]]),
          lambda x: cy(x) - 2 * H * sm(x, 170, 70), TO_LEFT, ""),
  "M08": (step(R), ramp([[0, 0], [20, 0]] + [[tp, (tp - 20) / 65 * 60] for tp in range(20, 90, 5)] + [[100, 60]]),
          TO_LEFT, lambda x: cy(x) - 2 * H * sm(x, 160, 90), "lane change comes late"),
  "M09": (step([[0, 0], [20, 0], [20, 70], [70, 70], [70, 0], [100, 0]]), step([[0, 0], [20, 0], [20, 70], [35, 70], [35, 0], [100, 0]]),
          CENTRE, tan(70), ""),
  "M10": (step([[0, 0], [20, 0], [20, 70], [50, 70], [50, 0], [100, 0]]), step([[0, 0], [20, 0], [20, 70], [80, 70], [80, 0], [100, 0]]),
          TO_LEFT, lambda x: cy(x) - 3.6 * H * sm(x, 60, 110), ""),
  "M11": (step(R), step([[0, 0], [55, 0], [55, 70], [100, 70]]), CENTRE,
          lambda x: tan(10)(x) if x < 130 else tan(10)(130) + (cy(x) - tan(10)(130)) * sm(x, 130, 110), ""),
  "M12": (None, None, CENTRE, lambda x: cy(x) + (0 if x < 60 else 0.004 * (x - 60) ** 2), ""),
  "M13": (step(R), step(_ERR), CENTRE, lambda x: cy(x) + 9 * math.sin((x - 10) / 18) * sm(x, 30, 30), "weaves in the lane"),
  "M14": (step(R), step([[0, 0], [20, 0], [20, 55], [40, 55], [40, 75], [60, 75], [60, 40], [80, 40], [80, 85], [100, 85]]), CENTRE,
          lambda x: cy(x) + (8 * math.sin((x - 10) / 22) if math.sin((x - 10) / 22) > 0 else 3 * math.sin((x - 10) / 22)) * sm(x, 30, 30),
          "pulls to one side"),
}
CALLOUTS = {"F-01": {"M07": "changes lane too early", "M10": "past the target lane"}}

SHEETS = {"F-01": ("fig-c03-4-1-f01-guide-words.svg", "Guide-word scenes", "steering torque", F01)}


def _pts(f, n=90):
  out = []
  for i in range(n + 1):
    x = X0 + (XE - X0) * i / n
    y = f(x)
    out.append((x, y))
    if y < 8 or y > 122:
      break
  return out


def _d(p):
  return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in p)


def _edge(k):
  return [(x, cy(x) + k) for x in [W * i / 60 for i in range(61)]]


def _pose(p, i):
  i = max(1, min(len(p) - 1, i))
  (x0, y0), (x1, y1) = p[i - 1], p[i]
  return f"translate({x1:.1f} {y1:.1f}) rotate({math.degrees(math.atan2(y1 - y0, x1 - x0)):.1f})"


def _car_body(body, stroke=INK):
  wheels = "".join(f'<rect x="{x}" y="{y}" width="4.5" height="2.4" rx="1" fill="#111827"/>' for x in (-8.5, 4.5) for y in (-6, 3.6))
  return (f'{wheels}<rect x="-11" y="-5" width="22" height="10" rx="3.5" fill="{body}" stroke="{stroke}" stroke-width="0.9"/>'
          '<path d="M2.5 -4 L6.5 -3.2 L6.5 3.2 L2.5 4 Z" fill="#1F2937" opacity="0.75"/>'
          '<path d="M-6.5 -3.6 L-8.5 -3 L-8.5 3 L-6.5 3.6 Z" fill="#1F2937" opacity="0.6"/>'
          '<rect x="10" y="-4.2" width="1.2" height="2" fill="#FDE68A"/><rect x="10" y="2.2" width="1.2" height="2" fill="#FDE68A"/>')


def _car(pose, body, opacity=1.0, stroke=INK):
  return f'<g transform="{pose}" opacity="{opacity:g}">{_car_body(body, stroke)}</g>'


# ---------------------------------------------------------------- animation (SMIL, no script; a still viewer shows the last frame)

DUR, DRIVE = 6, 0.8                       # loop length in s; share of the loop spent driving, the rest holds the end


def _key(x):
  return DRIVE * (x - X0) / (XE - X0)


def _heading(p, i):
  i = max(1, min(len(p) - 1, i))
  (x0, y0), (x1, y1) = p[i - 1], p[i]
  return math.degrees(math.atan2(y1 - y0, x1 - x0))


def _anim(attr, kind, values, keys):
  kt = ";".join(f"{k:.4f}" for k in keys)
  tag = "animateTransform" if kind else "animate"
  ty = f' type="{kind}"' if kind else ""
  return f'<{tag} attributeName="{attr}"{ty} values="{";".join(values)}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'


def _driving(p, inner):
  """A group that drives along p and holds at its end; its static pose is the end (the still frame)."""
  keys = [_key(x) for x, _ in p] + [1]
  tr = [f"{x:.1f},{y:.1f}" for x, y in p] + [f"{p[-1][0]:.1f},{p[-1][1]:.1f}"]
  rot = [f"{_heading(p, i):.1f}" for i in range(len(p))] + [f"{_heading(p, len(p) - 1):.1f}"]
  keys[0] = 0
  return (f'<g transform="translate({p[-1][0]:.1f} {p[-1][1]:.1f})">{_anim("transform", "translate", tr, keys)}'
          f'<g transform="rotate({_heading(p, len(p) - 1):.1f})">{_anim("transform", "rotate", rot, keys)}{inner}</g></g>')


def _appear(k):
  """Hidden until loop time k, then shown to the end of the loop."""
  return f'<animate attributeName="opacity" values="0;1" keyTimes="0;{max(k, 0.001):.4f}" calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>'


def _draw_on(p):
  """Reveal a path from its start in step with the car (stroke-dashoffset over pathLength 1)."""
  seg = [math.dist(a, b) for a, b in zip(p, p[1:])]
  total, run, vals = sum(seg) or 1, 0.0, ["1"]
  for d in seg:
    run += d
    vals.append(f"{1 - run / total:.4f}")
  return _anim("stroke-dashoffset", None, vals + ["0"], [0] + [_key(x) for x, _ in p[1:]] + [1])


def departure(intended, actual):
  """Index and label of the first moment the car (half width 5) crosses a line, or None."""
  for i, (x, y) in enumerate(actual):
    o, own = y - cy(x), (-2 * H if intended(x) - cy(x) < -H else 0)
    if o - own > H - 5 + 0.1 and o > H - 5:
      return i, "off the road" if o > H + 6 else "crosses edge line"
    if own == 0 and o < -(H - 5) - 0.1:
      return i, "into the next lane"
    if o < -3 * H + 5:
      return i, "off the road"
  return None


def scene(intended, actual, gw, callouts, fallback):
  pr, pp = _pts(intended), _pts(actual)
  m = min(len(pr), len(pp))
  band = _d(pr[:m] + pp[:m][::-1]) + " Z"
  dep = departure(intended, pp)
  if gw == "M10":
    dep = (next((i for i, (x, y) in enumerate(pp) if y - cy(x) < -3 * H + 5), dep[0] if dep else None), "")
  label = callouts.get(gw) or (dep[1] if dep else "")
  if dep is None and fallback:
    dep, label = (max(range(m), key=lambda i: abs(pp[i][1] - pr[i][1])), ""), fallback
  fi = next((i for i in range(m) if abs(pp[i][1] - pr[i][1]) > 1.2), None)
  asphalt = _d(_edge(H + 4) + _edge(-3 * H - 4)[::-1]) + " Z"
  kf = _key(pp[fi][0]) if fi is not None else 0
  out = ['<rect width="280" height="130" fill="#C9DDBA"/>',
         *[f'<path d="{_d(_edge(k))}" fill="none" stroke="#B9C7A6" stroke-width="7"/>' for k in (H + 4, -3 * H - 4)],
         f'<path d="{asphalt}" fill="#565E69"/>',
         *[f'<path d="{_d(_edge(k))}" fill="none" stroke="#F8FAFC" stroke-width="1.5"/>' for k in (H, -3 * H)],
         f'<path d="{_d(_edge(-H))}" fill="none" stroke="#F8FAFC" stroke-width="1.3" stroke-dasharray="9 9"/>',
         f'<g transform="{_pose(_edge(0), 6)}" opacity="0.55"><path d="M-6 -2 L2 -2 L2 -4.5 L8 0 L2 4.5 L2 2 L-6 2 Z" fill="#E5E7EB"/></g>',
         _car(_pose([(199, cy(199) - 2 * H), (201, cy(201) - 2 * H)], 1), "#9CA3AF", 1, "#4B5563"),
         # the gap fills in behind the car: clipped to the distance driven so far
         f'<clipPath id="r{gw}"><rect width="280" height="130">{_anim("width", None, [str(X0), str(XE), "280"], [0, DRIVE, 1])}</rect></clipPath>',
         f'<path d="{band}" fill="{PERF_S}" opacity="0.22" clip-path="url(#r{gw})"/>',
         f'<path d="{_d(pr)}" fill="none" stroke="{REQ_S}" stroke-width="2.2" stroke-dasharray="5 3" stroke-linecap="round"/>',
         f'<path d="{_d(pp)}" fill="none" stroke="{PERF_S}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" '
         f'pathLength="1" stroke-dasharray="1 1">{_draw_on(pp)}</path>',
         _car(_pose(pp, 1), "#F8FAFC", 0.45),
         _driving(pr[:next((i for i, (x, _) in enumerate(pr) if x >= pp[-1][0]), len(pr) - 1) + 1],
                  f'<rect x="-11" y="-5" width="22" height="10" rx="3.5" fill="none" stroke="{REQ_S}" stroke-width="1.3" stroke-dasharray="3 2"/>'),
         _driving(pp, _car_body("#DC2626", "#450A0A"))]
  if fi is not None:
    x, y = pp[fi]
    out.append(f'<g transform="translate({x:.1f} {y:.1f})">{_appear(kf)}<circle r="4.2" fill="{FAULT}" stroke="{INK}" stroke-width="0.9"/>'
               f'<path d="M0.6 -2.8 L-1.6 0.4 L0 0.4 L-0.6 2.8 L1.6 -0.4 L0 -0.4 Z" fill="{INK}"/></g>')
  if dep is not None and dep[0] is not None:
    x, y = pp[dep[0]]
    out.append(f'<g>{_appear(_key(x))}<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="none" stroke="{CALLOUT}" stroke-width="1.6"/>' +
               t(round(min(236, max(44, x)), 1), round(y - 11 if y > 30 else y + 16, 1), label, 8, CALLOUT, 600, "middle",
                 f' stroke="{INK}" stroke-width="2.4" paint-order="stroke"') + "</g>")
  return out, label


def chart(req, perf, axis_y, ylabel):
  return [f'<rect x="{CX0}" y="{CY0}" width="{CX1 - CX0}" height="{CY1 - CY0}" fill="#FFFFFF"/>',
          f'<line x1="{CX0}" y1="{CY0}" x2="{CX0}" y2="{CY1}" stroke="#94A3B8"/>',
          f'<line x1="{CX0}" y1="{axis_y:g}" x2="{CX1}" y2="{axis_y:g}" stroke="#94A3B8"/>',
          t(0, 0, ylabel, 8, MUTED, 600, "middle", f' transform="translate(8 {(CY0 + CY1) / 2:g}) rotate(-90)"'),
          *([t(CX0 - 3, CY0 + 3, "+", 8, MUTED, None, "end"), t(CX0 - 3, CY1, "−", 8, MUTED, None, "end"),
             t(CX0 - 3, axis_y + 3, "0", 7.5, MUTED, None, "end")] if axis_y != CY1 else
            [t(CX0 - 3, CY1, "0", 7.5, MUTED, None, "end"), t(CX0 - 3, CY0 + 6, "max", 7.5, MUTED, None, "end")]),
          t(CX1, 106, "time", 7.5, MUTED, None, "end"),
          f'<path d="{req}" fill="none" stroke="{REQ}" stroke-width="2.2" stroke-dasharray="6 3"/>',
          f'<path d="{perf}" fill="none" stroke="{PERF}" stroke-width="2.6" stroke-linejoin="round"/>',
          # time cursor in step with the car below; the still frame leaves it at the end of the axis
          f'<line x1="{CX1}" y1="{CY0}" x2="{CX1}" y2="{CY1}" stroke="{INK}" stroke-width="0.8" opacity="0.45">'
          f'{_anim("x1", None, [str(CX0), str(CX1), str(CX1)], [0, DRIVE, 1])}{_anim("x2", None, [str(CX0), str(CX1), str(CX1)], [0, DRIVE, 1])}</line>']


# ---------------------------------------------------------------- sheet

COLS, CW, GAP, M = 3, 380, 20, 40
PW = CW - 24                               # panel width inside a card
CH_H, SC_H = PW * 110 / 280, PW * 130 / 280


def goal_asil():
  _, _, goals = hf.parse_hara(hf.SOURCE.read_text(encoding="utf-8"))
  return {g.ident: g.asil for g in goals}


def cards(fid):
  _, _, ylabel, model = SHEETS[fid]
  fm = hm.FM[fid]
  sc = [g for g, row in fm.items() if row[0] == hm.SC]
  missing, extra = sorted(set(sc) - set(model)), sorted(set(model) - set(sc))
  if missing or extra:
    raise FigureError(f"{fid} guide-word scenes: no model for SC {missing}" if missing else f"{fid}: model for non-SC {extra}")
  asil = goal_asil()
  names = dict(hm.MALFUNCTIONS)
  out = []
  for gw in sorted(model):
    cls, hz, sub_by, why = fm[gw]
    sg = hm.SG_MAP[hz]
    if sg not in asil:
      raise FigureError(f"{fid}/{gw}: {hz} maps to {sg}, which is not a safety goal in WP-C-03 §6")
    req, perf, intended, actual, fallback = model[gw]
    axis_y = CY1
    if gw == "M12":
      (req, perf), axis_y = _biaxial(70, -70)
    sc_body, label = scene(intended, actual, gw, CALLOUTS.get(fid, {}), fallback)
    out.append(dict(gw=gw, name=names[gw], sub=SUB[gw], hz=hz, hazard=hm.HAZARDS[hz], sg=sg, asil=asil[sg], sub_by=sub_by,
                    why=why, chart=chart(req, perf, axis_y, ylabel), scene=sc_body, label=label))
  return out


def card_svg(x, y, c):
  b = [f'<rect x="{x}" y="{y}" width="{CW}" height="{{H}}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>']
  px, cy_ = x + 12, y + 26
  b.append(t(px, cy_, c["gw"], 12, MUTED, 600))
  b.append(t(px + 34, cy_, c["name"], 15, INK, 700))
  b.append(t(px + 34 + hf.text_w(c["name"], 15, True) + 8, cy_, c["sub"], 11, MUTED))
  cy_ += 12
  p, w = pill(px, cy_, f'{c["hz"]} · {c["sg"]} · ASIL {c["asil"]}', "#FEE2E2", "#7F1D1D", 18, 10)
  b.append(p)
  if c["sub_by"]:
    b.append(pill(px + w + 6, cy_, f'covered by {c["sub_by"]}', "#E2E8F0", "#334155", 18, 10)[0])
  cy_ += 26
  for line in wrap(c["hazard"], PW, 10.5):
    b.append(t(px, cy_ + 8, line, 10.5, MUTED))
    cy_ += 14
  cy_ += 4
  b.append(f'<svg x="{px}" y="{cy_:.1f}" width="{PW}" height="{CH_H:.1f}" viewBox="0 0 280 110">'
           f'<rect width="280" height="110" rx="6" fill="#F8FAFC"/>' + "".join(c["chart"]) + "</svg>")
  cy_ += CH_H + 6
  b.append(f'<svg x="{px}" y="{cy_:.1f}" width="{PW}" height="{SC_H:.1f}" viewBox="0 0 280 130">'
           f'<clipPath id="k{c["gw"]}"><rect width="280" height="130" rx="6"/></clipPath>'
           f'<g clip-path="url(#k{c["gw"]})">' + "".join(c["scene"]) + "</g></svg>")
  cy_ += SC_H + 8
  for line in wrap(c["why"], PW, 11):
    cy_ += 14
    b.append(t(px, cy_, line, 11, INK))
  h = cy_ + 14 - y
  b[0] = b[0].replace("{H}", f"{h:.0f}")
  return b, h


def legend(y):
  b, x = [], M
  items = [("req", "Required (intended)"), ("perf", "Performed (malfunction)"), ("fault", "Fault starts"),
           ("ring", "The moment it matters"), ("band", "Gap between intended and actual"), ("other", "Other traffic")]
  for kind, label in items:
    if kind == "req":
      b.append(f'<line x1="{x}" y1="{y - 4}" x2="{x + 26}" y2="{y - 4}" stroke="{REQ}" stroke-width="2.4" stroke-dasharray="6 3"/>')
      x += 32
    elif kind == "perf":
      b.append(f'<line x1="{x}" y1="{y - 4}" x2="{x + 26}" y2="{y - 4}" stroke="{PERF}" stroke-width="2.8"/>')
      x += 32
    elif kind == "fault":
      b.append(f'<circle cx="{x + 6}" cy="{y - 4}" r="5" fill="{FAULT}" stroke="{INK}" stroke-width="0.9"/>')
      x += 16
    elif kind == "ring":
      b.append(f'<circle cx="{x + 6}" cy="{y - 4}" r="6" fill="#565E69" stroke="{CALLOUT}" stroke-width="1.8"/>')
      x += 16
    elif kind == "band":
      b.append(f'<rect x="{x}" y="{y - 10}" width="20" height="12" fill="{PERF_S}" opacity="0.35"/>')
      x += 26
    else:
      b.append(_car(f"translate({x + 11} {y - 4}) scale(0.9)", "#9CA3AF", 1, "#4B5563"))
      x += 26
    b.append(t(x, y, label, 11, INK))
    x += hf.text_w(label, 11) + 22
  return b


def sheet(fid):
  fname, fig, _, _ = SHEETS[fid]
  cs = cards(fid)
  fname_txt = next(f[1] for f in hm.FUNCTIONS if f[0] == fid)
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  body = hf.header(w, f"{fig} · {fid} {fname_txt} under the 14 guide words",
                   "Top of each card: the function over time, required against performed. Below: what that does to the car, seen from above.",
                   "WP-C-03 §4 · hara_model.FM", "Schematic, not simulation output")
  body += legend(108)
  y, rows = 128, []
  for r in range(0, len(cs), COLS):
    built = [card_svg(M + k * (CW + GAP), y, c) for k, c in enumerate(cs[r:r + COLS])]
    row_h = max(h for _, h in built)
    for b, h in built:   # one height per row
      b[0] = b[0].replace(f'height="{h:.0f}"', f'height="{row_h:.0f}"', 1)
      rows.append(b)
    y += row_h + GAP
  for b in rows:
    body += b
  body.append(t(M, y + 6, "Scenes are drawn to explain each hazard on a two-lane left curve; the plant runs are in assurance/sim §3.7. "
                "Ratings are proposals for review until the I3 confirmation review (WP-C-03 header).", 10.5, MUTED))
  body.append(t(w - M, y + 6, hf.GENERATED.split(" — ")[0], 10, MUTED, None, "end"))
  desc = (f"{len(cs)} cards for {fid} {fname_txt}, one per SC guide word. " +
          " ".join(f"{c['gw']} {c['name']}: {c['hz']}, {c['sg']} ASIL {c['asil']}"
                   f"{', covered by ' + c['sub_by'] if c['sub_by'] else ''}"
                   f"{'; callout: ' + c['label'] if c['label'] else ''}." for c in cs))
  return fname, svg_doc(w, int(y + 24), f"{fig}: {fid} under the 14 guide words (WP-C-03 §4)", desc, body)


def build() -> dict[str, str]:
  return dict(sheet(fid) for fid in SHEETS)


if __name__ == "__main__":
  sys.exit(hf.main(sys.argv[1:]))
