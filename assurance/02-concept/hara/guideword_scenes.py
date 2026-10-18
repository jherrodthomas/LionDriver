#!/usr/bin/env python3
"""Draw the guide-word scene sheets: one card per SC guide word, the function against time over a top-down road scene.

One sheet per function that has SC guide words (`fig-c03-4-<n>-<function>-guide-words.svg`; F-07 and F-09 have none).
Each card shows what the function must deliver over time (required, dashed green) against what the malfunction
delivers (performed, red), and under it what that does to the car, with where the fault starts and the moment it
matters. Two scene types:

- lateral (F-01, and the lateral cases of F-03, F-05 and F-08): a two-lane left curve; the intended and actual paths.
- longitudinal (F-02, F-02X, and the longitudinal cases of F-03, F-04, F-06 and F-08): a straight road with a lead,
  a follower, a stopped car or a red light. A small simulation runs the intended controller (ACC gap keeping, or a
  stop for the light) twice: once as specified and once with the guide word applied to its output; the chart then
  plots the commanded acceleration of both runs. The callout is the first moment the faulty run is clearly worse
  than the intended one (closes on the lead, follower closes in, past the stop line on red).

Each card loops (SMIL, no script, 6 s): the cars drive, the red track draws in, the fault marker, status pills and
the callout appear when they happen, and a cursor moves along the time axis. A viewer that does not animate shows the
last frame.

The guide words, classes, hazards, subsumption and rationale come from `hara_model.FM`; the safety goal(s) and ASIL
come from WP-C-03 §6 (through `hara_figures.parse_hara`, which checks the goal table), mapped by `hara_model.SG_MAP`.
The behaviour models below are schematic: they explain each hazard and are not simulation results of the item (the
plant runs are in assurance/sim §3.7).

The build fails if a function with SC guide words has no sheet, or a sheet lacks a model for one of its SC guide words
or has one for a guide word that is not SC. Regenerate with `python3 hara_figures.py`.

Standard library only.
"""

from __future__ import annotations

import math
import re
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


def scene(intended, actual, gw, callouts, fallback, badges=()):
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
               t(_lx(x, label), round(y - 11 if y > 30 else y + 16, 1), label, 8, CALLOUT, 600, "middle",
                 f' stroke="{INK}" stroke-width="2.4" paint-order="stroke"') + "</g>")
  out += _badges(badges, lambda tt: DRIVE * tt)
  return out, label


def _lx(x, label, size=8):
  """Keep a centred callout inside the 280-wide scene."""
  half = hf.text_w(label, size, True) / 2 + 5
  return round(min(280 - half, max(half, x)), 1)


def _badges(badges, key):
  """Status pills in the scene's top-left corner: (text, from, to or None, style), times as loop fractions 0..1."""
  out, y = [], 6
  for text, t0, t1, style in badges:
    fill, fg, stroke = BADGE[style]
    w = hf.text_w(text, 7.5, True) + 12
    if t1 is None:
      anim = _appear(key(t0)) if t0 > 0 else ""
    else:
      anim = (f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;{max(key(t0), .001):.4f};{key(t1):.4f};1" '
              f'calcMode="discrete" dur="{DUR}s" repeatCount="indefinite"/>')
    out.append(f'<g>{anim}<rect x="6" y="{y}" width="{w:.1f}" height="13" rx="6.5" fill="{fill}" stroke="{stroke}" stroke-width="1"/>' +
               t(12, y + 9.3, text, 7.5, fg, 700) + "</g>")
    y += 16
  return out


BADGE = {"bad": ("#7F1D1D", "#FEE2E2", "#FCA5A5"), "ok": ("#14532D", "#DCFCE7", "#4ADE80"), "info": ("#1E293B", "#E2E8F0", "#94A3B8")}


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


# ---------------------------------------------------------------- longitudinal scene: a straight two-lane road, 280 x 130

LANE_Y, CAR_L = 84, 22                    # ego lane centre; car length (scene units)
AMAX_A, AMAX_B = 160, 240                 # full-scale acceleration and braking (scene units per loop time squared)
V0, VSET, NT = 175, 175, 200              # start speed, set speed, simulation steps over the drive


def _acc(st):
  """The intended ACC law, in percent of full scale (+ accelerate, - brake)."""
  if st["lead"] is None:
    a = 0.9 * (VSET - st["v"])
  else:
    gap = st["lead"] - st["x"] - CAR_L
    a = 1.3 * (gap - (24 + 0.16 * st["v"])) + 2.2 * (st["vl"] - st["v"])
  return max(-100.0, min(60.0, a / (AMAX_A if a > 0 else AMAX_B) * 100))


def _stop_ctrl(st, stopx, green_at):
  """Stop for a red light at stopx (front bumper on the line), go again after green_at."""
  if green_at is not None and st["t"] >= green_at:
    return max(-100.0, min(60.0, 0.9 * (VSET - st["v"]) / AMAX_A * 100))
  d = stopx - (st["x"] + CAR_L / 2) - 1
  if d <= 0.5:
    return -100.0 if st["v"] > 0 else 0.0
  need = st["v"] ** 2 / (2 * d)
  return -min(100.0, need / AMAX_B * 100) if need > 0.85 * AMAX_B else 0.0


def _lead_speed(spec, tt):
  if spec is None:
    return None
  pts = spec["v"]
  for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
    if t0 <= tt <= t1:
      return v0 + (v1 - v0) * (tt - t0) / (t1 - t0) if t1 > t0 else v1
  return pts[-1][1]


def simulate(sc, law):
  """Run one scenario with ego law(t, st, mem) -> accel %. Returns samples and the commanded accel trace."""
  lead = sc.get("lead")
  x0 = float(sc.get("x0", 40))
  st = {"t": 0.0, "x": x0, "v": float(sc.get("v0", V0)), "lead": lead["x"] if lead else None,
        "vl": _lead_speed(lead, 0) if lead else 0.0, "fx": x0 - CAR_L - 30, "fv": float(sc.get("v0", V0))}
  mem, ego, ld, fl, acc = {"hist": []}, [], [], [], []
  dt = 1 / NT
  fhist = []
  for i in range(NT + 1):
    st["t"] = i / NT
    a = law(st["t"], st, mem)
    a = max(-100.0, min(100.0, a))
    mem["hist"].append(a)
    acc.append((st["t"], a))
    ego.append((st["t"], st["x"], LANE_Y)); fl.append((st["t"], st["fx"], LANE_Y))
    if lead:
      ld.append((st["t"], st["lead"], LANE_Y))
    # follower: a driver keeping a gap, reacting 0.1 of the loop late with moderate braking
    fgap = st["x"] - st["fx"] - CAR_L
    fhist.append(1.2 * (fgap - (24 + 0.14 * st["fv"])) + 2.0 * (st["v"] - st["fv"]))
    fa = fhist[max(0, len(fhist) - 1 - int(0.08 * NT))]
    st["fv"] = max(0.0, st["fv"] + max(-AMAX_B * 0.7, min(AMAX_A, fa)) * dt)
    st["v"] = max(0.0, st["v"] + a / 100 * (AMAX_A if a > 0 else AMAX_B) * dt)
    st["x"] += st["v"] * dt
    st["fx"] = min(st["fx"] + st["fv"] * dt, st["x"] - CAR_L - 2)
    if lead:
      st["vl"] = _lead_speed(lead, st["t"] + dt)
      st["lead"] += st["vl"] * dt
      st["x"] = min(st["x"], st["lead"] - CAR_L - 2)
  return ego, ld, fl, acc


def _drive_t(samples, inner):
  """Time-based driving group (straight road, heading 0); its static pose is the last sample."""
  keys = [DRIVE * f for f, _, _ in samples] + [1]
  vals = [f"{x:.1f},{y:.1f}" for _, x, y in samples] + [f"{samples[-1][1]:.1f},{samples[-1][2]:.1f}"]
  # thin the keyframes: SMIL handles linear interpolation between them
  keep = sorted({0, len(samples) - 1, *range(0, len(samples), 4)})
  keys = [keys[i] for i in keep] + [1]
  vals = [vals[i] for i in keep] + [vals[-1]]
  return (f'<g transform="translate({samples[-1][1]:.1f} {samples[-1][2]:.1f})">{_anim("transform", "translate", vals, keys)}{inner}</g>')


def _events(sc, run, ref):
  """First moment that matters in the actual run, judged against the intended run: (index, label) or None."""
  (ego, ld, fl), (ego_r, ld_r, fl_r) = run, ref
  stopx, green = sc.get("stopx"), sc.get("green_at")
  for i, (tt, x, _) in enumerate(ego):
    if ld and ld[i][1] - x - CAR_L < 12 and ld[i][1] - x < ld_r[i][1] - ego_r[i][1] - 6:
      return i, sc.get("lead_label", "closes on the lead")
    if stopx is not None and (green is None or tt < green) and x + CAR_L / 2 > stopx + 4:
      return i, "past the stop line on red"
    if x - fl[i][1] - CAR_L < 14 and x - fl[i][1] < ego_r[i][1] - fl_r[i][1] - 6:
      return i, "follower closes in"
  return None


def lon_scene(spec):
  sc = spec["scenario"]
  ego, ld, fl, acc_p = simulate(sc, spec["perf"])
  ego_r, ld_r, fl_r, acc_r = simulate(sc, spec["req"])
  stopx, green = sc.get("stopx"), sc.get("green_at")
  out = ['<rect width="280" height="130" fill="#C9DDBA"/>', '<rect x="0" y="32" width="280" height="74" fill="#B9C7A6"/>',
         '<rect x="0" y="35" width="280" height="68" fill="#565E69"/>',
         '<line x1="0" y1="99" x2="280" y2="99" stroke="#F8FAFC" stroke-width="1.5"/>',
         '<line x1="0" y1="39" x2="280" y2="39" stroke="#F8FAFC" stroke-width="1.5"/>',
         '<line x1="0" y1="69" x2="280" y2="69" stroke="#F8FAFC" stroke-width="1.3" stroke-dasharray="9 9"/>',
         '<g transform="translate(26 54)" opacity="0.55"><path d="M-6 -2 L2 -2 L2 -4.5 L8 0 L2 4.5 L2 2 L-6 2 Z" fill="#E5E7EB"/></g>']
  if stopx is not None:
    head = (f'<circle cx="{stopx + 6}" cy="118" r="3.4" fill="#DC2626">' +
            (_anim("fill", None, ["#DC2626", "#22C55E", "#22C55E"], [0, DRIVE * green, 1]).replace("<animate ", '<animate calcMode="discrete" ')
             if green is not None else "") + "</circle>")
    out += [f'<line x1="{stopx}" y1="70" x2="{stopx}" y2="98" stroke="#F8FAFC" stroke-width="3"/>',
            f'<rect x="{stopx + 2}" y="112" width="8" height="12" rx="2" fill="#1F2937"/>', head]
  for x, y, txt in sc.get("labels", ()):
    out.append(t(_lx(x, txt, 7), y, txt, 7, "#334155", 600, "middle"))
  # gap kept by the intended run, as a ghost outline
  out.append(_drive_t(ego_r, f'<rect x="-11" y="-5" width="22" height="10" rx="3.5" fill="none" stroke="{REQ_S}" stroke-width="1.3" stroke-dasharray="3 2"/>'))
  track = [(x, y) for _, x, y in ego]
  out.append(f'<path d="M{track[0][0]:.1f} {LANE_Y} L{track[-1][0]:.1f} {LANE_Y}" fill="none" stroke="{PERF_S}" stroke-width="2.6" '
             f'stroke-linecap="round" pathLength="1" stroke-dasharray="1 1">' +
             _anim("stroke-dashoffset", None, ["1", "0", "0"], [0, DRIVE, 1]) + "</path>")
  if ld:
    body = "#9CA3AF" if not sc.get("stopped") else "#94A3B8"
    out.append(_drive_t(ld, _car_body(body, "#4B5563") + ('<rect x="-12" y="-5.5" width="2" height="2" fill="#F59E0B"/><rect x="-12" y="3.5" width="2" height="2" fill="#F59E0B"/>'
                                                          if sc.get("stopped") else "")))
  out.append(_drive_t(fl, _car_body("#9CA3AF", "#4B5563")))
  out.append(_drive_t(ego, _car_body("#DC2626", "#450A0A")))
  fi = next((i for i, ((_, a), (_, b)) in enumerate(zip(acc_p, acc_r)) if abs(a - b) > 6), None)
  if spec.get("fault_t") is not None:
    fi = int(spec["fault_t"] * NT)
  if fi is not None:
    x = ego[fi][1]
    out.append(f'<g transform="translate({x:.1f} {LANE_Y - 11})">{_appear(DRIVE * ego[fi][0])}<circle r="4.2" fill="{FAULT}" stroke="{INK}" stroke-width="0.9"/>'
               f'<path d="M0.6 -2.8 L-1.6 0.4 L0 0.4 L-0.6 2.8 L1.6 -0.4 L0 -0.4 Z" fill="{INK}"/></g>')
  ev = _events(sc, (ego, ld, fl), (ego_r, ld_r, fl_r))
  label = ev[1] if ev else spec.get("fallback", "")
  idx = ev[0] if ev else spec.get("fallback_i")
  if label and idx is not None:
    tt, x, _ = ego[idx]
    if label == "follower closes in":
      x = (x + fl[idx][1]) / 2
    elif ld and label == sc.get("lead_label", "closes on the lead"):
      x = x + CAR_L / 2 + 1
    out.append(f'<g>{_appear(DRIVE * tt)}<circle cx="{x:.1f}" cy="{LANE_Y}" r="7" fill="none" stroke="{CALLOUT}" stroke-width="1.6"/>' +
               t(_lx(x, label), LANE_Y + 21, label, 8, CALLOUT, 600, "middle",
                 f' stroke="{INK}" stroke-width="2.4" paint-order="stroke"') + "</g>")
  out += _badges(spec.get("badges", ()), lambda tt: DRIVE * tt)
  return out, label, acc_r, acc_p


def bpath(pts):
  """Biaxial chart path from (t 0..1, value -100..100)."""
  ym = (CY0 + CY1) / 2
  return "M" + " L".join(f"{_xt(tt * 100):.1f} {ym - v / 100 * (CY1 - CY0) / 2 * 0.92:.1f}" for tt, v in pts[::2] + [pts[-1]])


# ---------------------------------------------------------------- behaviour models of the other functions

def lon(scenario, perf, req=None, **kw):
  return dict(kind="lon", scenario=scenario, perf=perf, req=req or (lambda tt, st, m: scenario["law"](st)), **kw)


def lat(req, perf, intended, actual, fallback="", axis=CY1, badges=()):
  return dict(kind="lat", req=req, perf=perf, axis=axis, intended=intended, actual=actual, fallback=fallback, badges=badges)


SLOWS = {"lead": {"x": 132, "v": [(0, V0), (.15, V0), (.38, 45), (1, 45)]}, "law": _acc}
SLOW_GO = {"lead": {"x": 132, "v": [(0, V0), (.12, V0), (.3, 60), (.4, 60), (.55, V0), (1, V0)]}, "law": _acc}
FREE = {"lead": None, "law": _acc}


def _delayed(d):
  return lambda tt, st, m: (m["acc"].append(_acc(st)) or m["acc"][max(0, len(m["acc"]) - 1 - int(d * NT))]) if "acc" in m else (m.update(acc=[]) or 0.0)


def _brake_limited(dur):
  def f(tt, st, m):
    a = _acc(st)
    if a < -5:
      m.setdefault("b0", tt)
      return a if tt - m["b0"] < dur else 0.0
    return a
  return f


F02 = {
  "M01": lon(SLOWS, lambda tt, st, m: max(_acc(st), 0.0)),
  "M02": lon(SLOWS, lambda tt, st, m: _acc(st) if tt < .28 else max(_acc(st), 0.0)),
  "M03": lon(FREE, lambda tt, st, m: _acc(st) - (90 if .25 <= tt < .5 else 0), lead_label="closes on the lead", fallback="brakes for nothing", fallback_i=int(0.3 * NT)),
  "M04": lon(SLOWS, lambda tt, st, m: 30.0),
  "M05": lon(SLOWS, lambda tt, st, m: _acc(st) + (55 if tt > .12 else 0)),
  "M06": lon(SLOWS, lambda tt, st, m: _acc(st) * (0.35 if _acc(st) < 0 else 1)),
  "M07": lon(FREE, lambda tt, st, m: _acc(st) - (90 if .12 <= tt < .38 else 0), fallback="brakes for nothing", fallback_i=int(0.15 * NT)),
  "M08": lon(SLOWS, _delayed(.16)),
  "M09": lon(SLOWS, _brake_limited(.06)),
  "M10": lon(SLOW_GO, lambda tt, st, m: min(_acc(st), -60.0) if .22 <= tt < .85 else _acc(st)),
  "M11": lon(SLOWS, _delayed(.12), fallback="brakes late", fallback_i=int(0.5 * NT)),
  "M12": lon(SLOWS, lambda tt, st, m: -_acc(st) if _acc(st) < 0 else _acc(st)),
  "M13": lon(FREE, lambda tt, st, m: _acc(st) + ((-80 if math.sin(2 * math.pi * 6 * tt) < 0 else 40) if tt > .15 else 0), fallback="surges: brake, go, brake", fallback_i=int(0.45 * NT)),
}

RED = {"lead": None, "x0": 100, "v0": 110, "stopx": 180, "law": lambda st: _stop_ctrl(st, 180, None), "labels": [(180, 28, "red light")]}
RED_GREEN = {"lead": None, "x0": 80, "v0": 110, "stopx": 150, "green_at": .55, "law": lambda st: _stop_ctrl(st, 150, .55),
             "labels": [(150, 28, "red, then green")]}
NO_SIGNAL = {"lead": None, "x0": 100, "v0": 110, "law": lambda st: 0.9 * (110 - st["v"]) / AMAX_A * 100,
             "labels": [(165, 28, "no signal, shadow on the road")]}


def _stop(stopx, gain=1.0, delay=0.0, release=None, creep=None):
  def f(tt, st, m):
    m.setdefault("h", []).append(_stop_ctrl(st, stopx, None))
    a = m["h"][max(0, len(m["h"]) - 1 - int(delay * NT))] * gain
    if release is not None and tt >= release:
      return 0.0
    if creep is not None and tt > creep:
      return 45.0
    return a
  return f


F02X = {
  "M01": lon(RED, lambda tt, st, m: 0.0),
  "M02": lon(RED, _stop(180, release=.4)),
  "M03": lon(NO_SIGNAL, _stop(165), fallback="stops for nothing", fallback_i=int(.55 * NT)),
  "M05": lon(RED, lambda tt, st, m: _stop_ctrl(st, 150, None)),
  "M06": lon(RED, _stop(180, gain=0.45)),
  "M07": lon(RED, lambda tt, st, m: _stop_ctrl(st, 140, None)),
  "M08": lon(RED, _stop(180, delay=.14)),
  "M09": lon(RED, _stop(180, creep=.6)),
  "M10": lon(RED_GREEN, lambda tt, st, m: _stop_ctrl(st, 150, None) if tt < .55 else 0.0, fallback="stays stopped on green",
             fallback_i=int(.7 * NT)),
  "M11": lon(RED, _stop(180, delay=.1)),
  "M13": lon(RED, lambda tt, st, m: _stop_ctrl(st, 180, None) + ((-70 if math.sin(2 * math.pi * 5 * tt) < 0 else 45) if tt > .15 else 0), fallback="stop-go at the light", fallback_i=int(0.5 * NT)),
}

# F-03 engagement: chart is the engaged state (0 off, 100 engaged); the scene shows what the state does to the car
ENG = lambda pts: step([[tp, v] for tp, v in pts])  # noqa: E731
STOPPED = {"lead": {"x": 212, "v": [(0, 0), (1, 0)]}, "stopped": True, "law": _acc, "labels": [(212, 28, "stopped car")],
           "lead_label": "runs into the stopped car"}
DRIVER_BRAKES = ("driver brakes", .3, None, "info")


def _override(net):
  return lambda tt, st, m: (0.0 if tt < .3 else net)


F03 = {
  "M01": lon(STOPPED, _override(-38), req=_override(-100), chart=(ENG([[0, 100], [30, 100], [30, 0], [100, 0]]), ENG([[0, 100], [100, 100]])),
             badges=[DRIVER_BRAKES, ("system keeps accelerating", .3, None, "bad")]),
  "M02": lat(ENG([[0, 100], [100, 100]]), ENG([[0, 100], [35, 100], [35, 0], [100, 0]]), CENTRE, tan(100),
             badges=[("system drops out, no warning", .35, None, "bad")]),
  "M03": lat(ENG([[0, 0], [100, 0]]), ENG([[0, 0], [30, 0], [30, 100], [100, 100]]), CENTRE,
             lambda x: cy(x) - 2 * H * sm(x, 95, 60), badges=[("engages unrequested", .3, None, "bad")]),
  "M04": lon(STOPPED, _override(-38), req=_override(-100), chart=(ENG([[0, 100], [30, 100], [30, 0], [100, 0]]), ENG([[0, 100], [100, 100]])),
             badges=[DRIVER_BRAKES, ("state stuck: engaged", .3, None, "bad")]),
  "M06": lon(STOPPED, _override(-62), req=_override(-100), chart=(ENG([[0, 100], [30, 100], [30, 0], [100, 0]]), ENG([[0, 100], [30, 100], [30, 50], [100, 50]])),
             badges=[DRIVER_BRAKES, ("steering off, ACC still on", .3, None, "bad")]),
  "M08": lon(STOPPED, lambda tt, st, m: 0.0 if tt < .3 else (-38 if tt < .5 else -100), req=_override(-100),
             chart=(ENG([[0, 100], [30, 100], [30, 0], [100, 0]]), ENG([[0, 100], [50, 100], [50, 0], [100, 0]])), badges=[DRIVER_BRAKES], fallback="stops closer to the car", fallback_i=int(0.55 * NT)),
  "M10": lon(STOPPED, _override(-38), req=_override(-100), chart=(ENG([[0, 100], [30, 100], [30, 0], [100, 0]]), ENG([[0, 100], [100, 100]])),
             badges=[("driver cancels", .3, None, "info"), ("keeps going", .3, None, "bad")]),
  "M11": lon(STOPPED, lambda tt, st, m: 0.0 if tt < .3 else (-38 if tt < .42 else -100), req=_override(-100),
             chart=(ENG([[0, 100], [30, 100], [30, 0], [100, 0]]), ENG([[0, 100], [42, 100], [42, 0], [100, 0]])), badges=[DRIVER_BRAKES], fallback="stops closer to the car", fallback_i=int(0.5 * NT)),
  "M12": lat(ENG([[0, 100], [30, 100], [30, 0], [100, 0]]), ENG([[0, 100], [30, 100], [30, 0], [34, 0], [34, 100], [100, 100]]), CENTRE,
             lambda x: cy(x) - 2 * H * sm(x, 105, 60), badges=[("driver cancels", .3, None, "info"), ("re-engages", .34, None, "bad")]),
  "M13": lat(ENG([[0, 100], [100, 100]]), ENG([[0, 100], [25, 100], [25, 0], [35, 0], [35, 100], [50, 100], [50, 0], [60, 0], [60, 100],
                                                [75, 100], [75, 0], [85, 0], [85, 100], [100, 100]]),
             CENTRE, lambda x: cy(x) + 4.5 * (sm(x, 75, 25) - sm(x, 100, 25) + sm(x, 135, 25) - sm(x, 160, 25) + sm(x, 195, 25) - sm(x, 220, 25)) * 2.2,
             fallback="drops out again and again", badges=[("toggling", .25, None, "bad")]),
}

# F-04 driver monitoring: chart is the escalation level; the driver looks away from t = .1
EYES_OFF = ("driver: eyes off road", .1, None, "info")
ATTENTIVE = ("driver: attentive", 0, None, "ok")
ESC = [[0, 0], [30, 0], [30, 33], [48, 33], [48, 66], [62, 66], [62, 100], [100, 100]]
HAZARD = {"lead": {"x": 262, "v": [(0, 0), (1, 0)]}, "stopped": True, "law": _acc, "labels": [(262, 28, "stopped car")]}
FORCED = lambda t0: (lambda tt, st, m: 0.0 if tt < t0 else -45.0)   # noqa: E731


def _dm(perf_esc, perf_law, badges, req_esc=ESC, req_law=FORCED(.62), scen=HAZARD, **kw):
  return lon(scen, perf_law, req=req_law, chart=(step(req_esc), step(perf_esc)), badges=badges, **kw)


NOBODY = dict(fallback="nobody watching, no escalation", fallback_i=int(.7 * NT))
F04 = {
  "M01": _dm([[0, 0], [100, 0]], lambda tt, st, m: 0.0, [EYES_OFF], **NOBODY),
  "M02": _dm([[0, 0], [30, 0], [30, 33], [42, 33], [42, 0], [100, 0]], lambda tt, st, m: 0.0, [EYES_OFF, ("monitoring stops", .42, None, "bad")], **NOBODY),
  "M03": _dm([[0, 0], [20, 0], [20, 100], [100, 100]], FORCED(.28), [ATTENTIVE, ("forced deceleration", .28, None, "bad")],
             req_esc=[[0, 0], [100, 0]], req_law=lambda tt, st, m: 0.0, fallback="forced stop, driver attentive", fallback_i=int(0.35 * NT)),
  "M04": _dm([[0, 0], [100, 0]], lambda tt, st, m: 0.0, [EYES_OFF, ("estimate stuck: attentive", .1, None, "bad")], **NOBODY),
  "M05": _dm([[0, 0], [12, 0], [12, 66], [22, 66], [22, 100], [100, 100]], FORCED(.24), [ATTENTIVE, ("over-sensitive", .12, None, "bad")],
             req_esc=[[0, 0], [100, 0]], req_law=lambda tt, st, m: 0.0, fallback="forced stop, driver attentive", fallback_i=int(0.3 * NT)),
  "M06": _dm([[0, 0], [30, 0], [30, 33], [100, 33]], lambda tt, st, m: 0.0, [EYES_OFF, ("stays at first warning", .3, None, "bad")], **NOBODY),
  "M07": _dm([[0, 0], [15, 0], [15, 33], [22, 33], [22, 66], [28, 66], [28, 100], [100, 100]], FORCED(.28), [EYES_OFF],
             req_esc=ESC, fallback="forced stop too early", fallback_i=int(0.35 * NT)),
  "M08": _dm([[0, 0], [55, 0], [55, 33], [72, 33], [72, 66], [86, 66], [86, 100], [100, 100]], FORCED(.86), [EYES_OFF], **NOBODY),
  "M11": _dm([[0, 0], [50, 0], [50, 33], [68, 33], [68, 66], [82, 66], [82, 100], [100, 100]], FORCED(.82), [EYES_OFF], **NOBODY),
}

# F-05 driver information: chart is the take-over alert; the system hands back at t = .3 in the curve
ALERT_R = [[0, 0], [30, 0], [30, 100], [55, 100], [55, 0], [100, 0]]
HANDBACK = ("system hands back", .3, None, "info")
LATE = lambda x: tan(85)(x) if x < 175 else tan(85)(175) + (cy(x) - tan(85)(175)) * sm(x, 175, 70)   # noqa: E731
F05 = {
  "M01": lat(step(ALERT_R), step([[0, 0], [100, 0]]), CENTRE, tan(85), badges=[HANDBACK, ("no alert", .3, None, "bad")]),
  "M02": lat(step(ALERT_R), step([[0, 0], [20, 0], [20, 0], [100, 0]]), CENTRE, tan(85), badges=[("display goes blank", .2, None, "bad"), HANDBACK]),
  "M04": lat(step([[0, 100], [30, 100], [30, 0], [100, 0]]), step([[0, 100], [100, 100]]), CENTRE, tan(85),
             badges=[HANDBACK, ("still shows engaged", .3, None, "bad")]),
  "M06": lat(step(ALERT_R), step([[0, 0], [30, 0], [30, 45], [55, 45], [55, 0], [100, 0]]), CENTRE, LATE, "driver corrects late",
             badges=[HANDBACK, ("visual only, no sound", .3, None, "bad")]),
  "M08": lat(step(ALERT_R), step([[0, 0], [58, 0], [58, 100], [80, 100], [80, 0], [100, 0]]), CENTRE, LATE, "driver corrects late",
             badges=[HANDBACK, ("alert comes late", .58, None, "bad")]),
  "M09": lat(step(ALERT_R), step([[0, 0], [30, 0], [30, 100], [33, 100], [33, 0], [100, 0]]), CENTRE, tan(85),
             badges=[HANDBACK, ("alert too short", .3, .4, "bad")]),
  "M11": lat(step(ALERT_R), step([[0, 0], [50, 0], [50, 100], [75, 100], [75, 0], [100, 0]]), CENTRE, LATE, "driver corrects late",
             badges=[HANDBACK, ("alert delayed", .5, None, "bad")]),
  "M12": lat(step([[0, 100], [30, 100], [30, 0], [100, 0]]), step([[0, 100], [100, 100]]), CENTRE, tan(85),
             badges=[HANDBACK, ("shows engaged", .3, None, "bad")]),
}

# F-06 forward collision warning: a false warning provokes reflex braking by the driver
F06 = {
  "M03": lon(FREE, lambda tt, st, m: -85.0 if .36 <= tt < .56 else _acc(st), chart=(step([[0, 0], [100, 0]]),
             step([[0, 0], [30, 0], [30, 100], [45, 100], [45, 0], [100, 0]])),
             badges=[("FCW: BRAKE! (false)", .3, .45, "bad"), ("driver brakes hard", .36, None, "info")], fallback="driver brakes for nothing", fallback_i=int(0.4 * NT)),
}

# F-08 safety envelope and forwarding
AEB = {"lead": {"x": 238, "v": [(0, 0), (1, 0)]}, "stopped": True, "law": _acc, "labels": [(238, 28, "stopped car")],
       "lead_label": "runs into the stopped car"}
F08 = {
  "M03": lon(AEB, lambda tt, st, m: 0.0, req=lambda tt, st, m: 0.0 if tt < .38 else -100.0,
             chart=(step([[0, 0], [38, 0], [38, 100], [100, 100]]), step([[0, 0], [100, 0]])),
             badges=[("stock AEB brakes", .38, None, "ok"), ("AEB request blocked", .38, None, "bad")]),
  "M04": lat(step([[0, 100], [100, 100]]), step([[0, 100], [30, 100], [30, 0], [100, 0]]), CENTRE, tan(85),
             badges=[("envelope stuck blocking", .3, None, "bad"), ("screen: engaged", 0, None, "info")]),
  "M05": lat(step([[0, 100], [100, 100]]), step([[0, 100], [30, 100], [30, 40], [100, 40]]), CENTRE, lambda x: (cy(x) + tan(85)(x)) / 2, "drifts wide in the curve",
             badges=[("valid commands cut", .3, None, "bad")]),
  "M13": lat(step([[0, 100], [100, 100]]), step([[0, 100], [25, 100], [25, 0], [38, 0], [38, 100], [55, 100], [55, 0], [68, 0], [68, 100], [100, 100]]),
             CENTRE, lambda x: cy(x) + 4 * (sm(x, 75, 30) - sm(x, 110, 30) + sm(x, 150, 30) - sm(x, 185, 30)) * 2.2,
             fallback="blocks on and off", badges=[("intermittent blocking", .25, None, "bad")]),
}

# function: (file, figure, what the chart's "function" is for this function, models)
SHEETS = {
  "F-01": ("fig-c03-4-1-f01-guide-words.svg", "Guide-word scenes", "steering torque", F01),
  "F-02": ("fig-c03-4-2-f02-guide-words.svg", "Guide-word scenes", "acceleration command (+ accelerate, − brake)", F02),
  "F-02X": ("fig-c03-4-3-f02x-guide-words.svg", "Guide-word scenes", "acceleration command (+ accelerate, − brake)", F02X),
  "F-03": ("fig-c03-4-4-f03-guide-words.svg", "Guide-word scenes", "engaged state (or the car's response, see card)", F03),
  "F-04": ("fig-c03-4-5-f04-guide-words.svg", "Guide-word scenes", "escalation level (warning → alert → forced deceleration)", F04),
  "F-05": ("fig-c03-4-6-f05-guide-words.svg", "Guide-word scenes", "take-over alert or displayed state", F05),
  "F-06": ("fig-c03-4-7-f06-guide-words.svg", "Guide-word scenes", "forward collision warning", F06),
  "F-08": ("fig-c03-4-8-f08-guide-words.svg", "Guide-word scenes", "commands or messages passed", F08),
}
NO_SHEET = {"F-07": "no SC guide word", "F-09": "no SC guide word"}


# ---------------------------------------------------------------- sheet

COLS, CW, GAP, M = 3, 380, 20, 40
PW = CW - 24                               # panel width inside a card
CH_H, SC_H = PW * 110 / 280, PW * 130 / 280


def goal_asil():
  _, _, goals = hf.parse_hara(hf.SOURCE.read_text(encoding="utf-8"))
  return {g.ident: g.asil for g in goals}


def _goal(hz, asil):
  """Safety goal(s) of a hazard per hara_model.SG_MAP that exist in WP-C-03 §6, and the highest ASIL among them."""
  ids = re.findall(r"SG-\d\d", hm.SG_MAP[hz])
  if not ids:
    raise FigureError(f"{hz}: no safety goal in hara_model.SG_MAP")
  have = [g for g in ids if g in asil]
  if not have:
    return hm.SG_MAP[hz], None          # e.g. H-10: SG-09 exists only if D-08 option B is chosen
  return "/".join(have), max((asil[g] for g in have), key=hf.ORDER.index)


def _as_spec(m, gw):
  if isinstance(m, dict):
    return m
  req, perf, intended, actual, fallback = m
  if gw == "M12" and req is None:
    (req, perf), axis = _biaxial(70, -70)
    return lat(req, perf, intended, actual, fallback, axis)
  return lat(req, perf, intended, actual, fallback)


def function_name(fid):
  if fid == hm.EXPERIMENTAL_FUNCTION[0]:
    return hm.EXPERIMENTAL_FUNCTION[1]
  return next(f[1] for f in hm.FUNCTIONS if f[0] == fid)


def cards(fid):
  model = SHEETS[fid][3]
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
    sg, a = _goal(hz, asil)
    spec = _as_spec(model[gw], gw)
    if spec["kind"] == "lat":
      sc_body, label = scene(spec["intended"], spec["actual"], gw, CALLOUTS.get(fid, {}), spec["fallback"], spec["badges"])
      ch = chart(spec["req"], spec["perf"], spec["axis"], "function")
    else:
      sc_body, label, acc_r, acc_p = lon_scene(spec)
      if "chart" in spec:
        ch = chart(*spec["chart"], CY1, "function")
      else:
        ch = chart(bpath(acc_r), bpath(acc_p), (CY0 + CY1) / 2, "function")
    out.append(dict(gw=gw, name=names[gw], sub=SUB[gw], hz=hz, hazard=hm.HAZARDS[hz], sg=sg, asil=a, sub_by=sub_by,
                    why=why, chart=ch, scene=sc_body, label=label))
  return out


def card_svg(x, y, c):
  b = [f'<rect x="{x}" y="{y}" width="{CW}" height="{{H}}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>']
  px, cy_ = x + 12, y + 26
  b.append(t(px, cy_, c["gw"], 12, MUTED, 600))
  b.append(t(px + 34, cy_, c["name"], 15, INK, 700))
  b.append(t(px + 34 + hf.text_w(c["name"], 15, True) + 8, cy_, c["sub"], 11, MUTED))
  cy_ += 12
  goal = f'{c["hz"]} · {c["sg"]} · ASIL {c["asil"]}' if c["asil"] else f'{c["hz"]} · {c["sg"]}'
  p, w = pill(px, cy_, goal, "#FEE2E2", "#7F1D1D", 18, 10)
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
  fname, fig, what, _ = SHEETS[fid]
  cs = cards(fid)
  fname_txt = function_name(fid)
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  n = f"All {len(cs)}" if len(cs) == 14 else f"The {len(cs)} safety-relevant (SC)"
  body = hf.header(w, f"{fig} · {fid} {fname_txt}",
                   f"{n} guide words. Chart: the function ({what}), required vs performed. Scene: what it does to the car.",
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
  body.append(t(M, y + 6, "Scenes are drawn to explain each hazard; the plant runs are in assurance/sim §3.7. "
                "Ratings are proposals for review until the I3 confirmation review (WP-C-03 header).", 10.5, MUTED))
  body.append(t(w - M, y + 6, hf.GENERATED.split(" — ")[0], 10, MUTED, None, "end"))
  desc = (f"{len(cs)} cards for {fid} {fname_txt}, one per SC guide word. " +
          " ".join(f"{c['gw']} {c['name']}: {c['hz']}, {c['sg']}{' ASIL ' + c['asil'] if c['asil'] else ''}"
                   f"{', covered by ' + c['sub_by'] if c['sub_by'] else ''}"
                   f"{'; callout: ' + c['label'] if c['label'] else ''}." for c in cs))
  return fname, svg_doc(w, int(y + 24), f"{fig}: {fid} {fname_txt} under its SC guide words (WP-C-03 §4)", desc, body)


def build() -> dict[str, str]:
  return dict(sheet(fid) for fid in SHEETS)


if __name__ == "__main__":
  sys.exit(hf.main(sys.argv[1:]))
