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

The road, cars, marks, pills and SMIL helpers come from the shared scene kit (01-management/figures/scenekit.py),
whose reference style these cards are; this module keeps the scene geometry and the behaviour models.

Standard library only.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "01-management" / "figures"))
import hara_figures as hf  # noqa: E402
import hara_model as hm  # noqa: E402
import scenekit as sk  # noqa: E402  (road, car, marks, pills, SMIL helpers)
from hara_figures import HAIR, INK, MUTED, FigureError, pill, svg_doc, t, wrap  # noqa: E402
from scenekit import DRIVE, PERF, REQ  # noqa: E402

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


def _edge(k):
  return [(x, cy(x) + k) for x in [W * i / 60 for i in range(61)]]


def _key(x):
  """Loop time at which the car passes x."""
  return DRIVE * (x - X0) / (XE - X0)


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
  band = sk.d(pr[:m] + pp[:m][::-1]) + " Z"
  dep = departure(intended, pp)
  if gw == "M10":
    dep = (next((i for i, (x, y) in enumerate(pp) if y - cy(x) < -3 * H + 5), dep[0] if dep else None), "")
  label = callouts.get(gw) or (dep[1] if dep else "")
  if dep is None and fallback:
    dep, label = (max(range(m), key=lambda i: abs(pp[i][1] - pr[i][1])), ""), fallback
  fi = next((i for i in range(m) if abs(pp[i][1] - pr[i][1]) > 1.2), None)
  kf = _key(pp[fi][0]) if fi is not None else 0
  out = [*sk.curved_road(_edge),
         sk.car(sk.pose([(199, cy(199) - 2 * H), (201, cy(201) - 2 * H)], 1), sk.OTHER, 1, sk.OTHER_EDGE),
         *sk.gap_band(band, gw, X0, XE),
         sk.intended_path(pr),
         sk.performed_path(sk.d(pp), sk.draw_on(pp, [_key(x) for x, _ in pp])),
         sk.start_marker(sk.pose(pp, 1)),
         sk.driving(pr[:next((i for i, (x, _) in enumerate(pr) if x >= pp[-1][0]), len(pr) - 1) + 1], sk.ghost_body(), _key),
         sk.driving(pp, sk.ego_body(), _key)]
  if fi is not None:
    out.append(sk.fault_marker(*pp[fi], kf))
  if dep is not None and dep[0] is not None:
    x, y = pp[dep[0]]
    out.append(sk.callout(x, y, 6, label, round(y - 11 if y > 30 else y + 16, 1), _key(x)))
  out += sk.badges(badges, lambda tt: DRIVE * tt)
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
          f'{sk.anim("x1", None, [str(CX0), str(CX1), str(CX1)], [0, DRIVE, 1])}{sk.anim("x2", None, [str(CX0), str(CX1), str(CX1)], [0, DRIVE, 1])}</line>']


# ---------------------------------------------------------------- longitudinal scene: a straight two-lane road, 280 x 130

LANE_Y, CAR_L = sk.EGO_LANE, sk.CAR_L     # ego lane centre; car length (scene units)
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
  out = sk.straight_road()
  if stopx is not None:
    out += sk.traffic_light(stopx, green)
  for x, y, txt in sc.get("labels", ()):
    out.append(t(sk.fit_x(x, txt, 7), y, txt, 7, "#334155", 600, "middle"))
  # gap kept by the intended run, as a ghost outline
  out.append(sk.drive_t(ego_r, sk.ghost_body()))
  track = [(x, y) for _, x, y in ego]
  out.append(sk.performed_path(f"M{track[0][0]:.1f} {LANE_Y} L{track[-1][0]:.1f} {LANE_Y}",
                               sk.anim("stroke-dashoffset", None, ["1", "0", "0"], [0, DRIVE, 1])))
  if ld:
    out.append(sk.drive_t(ld, sk.other_body(sc.get("stopped", False))))
  out.append(sk.drive_t(fl, sk.other_body()))
  out.append(sk.drive_t(ego, sk.ego_body()))
  fi = next((i for i, ((_, a), (_, b)) in enumerate(zip(acc_p, acc_r)) if abs(a - b) > 6), None)
  if spec.get("fault_t") is not None:
    fi = int(spec["fault_t"] * NT)
  if fi is not None:
    out.append(sk.fault_marker(ego[fi][1], LANE_Y - 11, DRIVE * ego[fi][0]))
  ev = _events(sc, (ego, ld, fl), (ego_r, ld_r, fl_r))
  label = ev[1] if ev else spec.get("fallback", "")
  idx = ev[0] if ev else spec.get("fallback_i")
  if label and idx is not None:
    tt, x, _ = ego[idx]
    if label == "follower closes in":
      x = (x + fl[idx][1]) / 2
    elif ld and label == sc.get("lead_label", "closes on the lead"):
      x = x + CAR_L / 2 + 1
    out.append(sk.callout(x, LANE_Y, 7, label, LANE_Y + 21, DRIVE * tt))
  out += sk.badges(spec.get("badges", ()), lambda tt: DRIVE * tt)
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


def card_svg(x, y, c, cw=CW):
  pw = cw - 24
  ch_h, sc_h = pw * 110 / 280, pw * 130 / 280
  b = [f'<rect x="{x}" y="{y}" width="{cw}" height="{{H}}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>']
  px, cy_ = x + 12, y + 26
  b.append(t(px, cy_, c["gw"], 12, MUTED, 600))
  b.append(t(px + 34, cy_, c["name"], 15, INK, 700))
  if px + 34 + hf.text_w(c["name"], 15, True) + 8 + hf.text_w(c["sub"], 11) <= x + cw - 12:
    b.append(t(px + 34 + hf.text_w(c["name"], 15, True) + 8, cy_, c["sub"], 11, MUTED))
  cy_ += 12
  goal = f'{c["hz"]} · {c["sg"]} · ASIL {c["asil"]}' if c["asil"] else f'{c["hz"]} · {c["sg"]}'
  p, w = pill(px, cy_, goal, "#FEE2E2", "#7F1D1D", 18, 10)
  b.append(p)
  if c["sub_by"]:
    b.append(pill(px + w + 6, cy_, f'covered by {c["sub_by"]}', "#E2E8F0", "#334155", 18, 10)[0])
  cy_ += 26
  for line in wrap(c["hazard"], pw, 10.5):
    b.append(t(px, cy_ + 8, line, 10.5, MUTED))
    cy_ += 14
  cy_ += 4
  b.append(f'<svg x="{px}" y="{cy_:.1f}" width="{pw}" height="{ch_h:.1f}" viewBox="0 0 280 110">'
           f'<rect width="280" height="110" rx="6" fill="#F8FAFC"/>' + "".join(c["chart"]) + "</svg>")
  cy_ += ch_h + 6
  b.append(f'<svg x="{px}" y="{cy_:.1f}" width="{pw}" height="{sc_h:.1f}" viewBox="0 0 280 130">'
           f'<clipPath id="k{c["gw"]}"><rect width="280" height="130" rx="6"/></clipPath>'
           f'<g clip-path="url(#k{c["gw"]})">' + "".join(c["scene"]) + "</g></svg>")
  cy_ += sc_h + 8
  for line in wrap(c["why"], pw, 11):
    cy_ += 14
    b.append(t(px, cy_, line, 11, INK))
  h = cy_ + 14 - y
  b[0] = b[0].replace("{H}", f"{h:.0f}")
  return b, h


def legend(y, m=M, w=None):
  """The legend from x = m; with a sheet width w, items that would pass the right margin start a new line.
  Returns the elements and the y of the last line."""
  b, x = [], m
  items = [("req", "Required (intended)"), ("perf", "Performed (malfunction)"), ("fault", "Fault starts"),
           ("ring", "The moment it matters"), ("band", "Gap between intended and actual"), ("other", "Other traffic")]
  for kind, label in items:
    if w is not None and x > m and x + 22 + hf.text_w(label, 11) > w - m:
      x, y = m, y + 20
    mark, used = sk.legend_swatch(kind, x, y)
    b.append(mark)
    x += used
    b.append(t(x, y, label, 11, INK))
    x += hf.text_w(label, 11) + 22
  return b, y


PHONE = dict(cols=2, cw=290, gap=12, m=24)   # 2 * 24 + 2 * 290 + 12 = 640 px: the cards at full size on a phone


def _phone_header(w, m, title, subtitle):
  b, y = [], 30
  for line in wrap(title, w - 2 * m, 18, True):
    b.append(t(m, y, line, 18, INK, 700))
    y += 23
  for line in wrap(subtitle, w - 2 * m, 12):
    b.append(t(m, y, line, 12, MUTED))
    y += 16
  b.append(t(m, y, "WP-C-03 §4 · hara_model.FM · schematic, not simulation output · phone view", 11, MUTED))
  y += 10
  b.append(f'<line x1="{m}" y1="{y}" x2="{w - m}" y2="{y}" stroke="{HAIR}"/>')
  return b, y + 22


def sheet(fid, cols=COLS, cw=CW, gap=GAP, m=M, phone=False):
  fname, fig, what, _ = SHEETS[fid]
  cs = cards(fid)
  fname_txt = function_name(fid)
  w = 2 * m + cols * cw + (cols - 1) * gap
  n = f"All {len(cs)}" if len(cs) == 14 else f"The {len(cs)} safety-relevant (SC)"
  sub = f"{n} guide words. Chart: the function ({what}), required vs performed. Scene: what it does to the car."
  if phone:
    body, ly = _phone_header(w, m, f"{fig} · {fid} {fname_txt}", sub)
    leg, ly = legend(ly, m, w)
    body += leg
    y = ly + 20
  else:
    body = hf.header(w, f"{fig} · {fid} {fname_txt}", sub, "WP-C-03 §4 · hara_model.FM", "Schematic, not simulation output")
    body += legend(108)[0]
    y = 128
  rows = []
  for r in range(0, len(cs), cols):
    built = [card_svg(m + k * (cw + gap), y, c, cw) for k, c in enumerate(cs[r:r + cols])]
    row_h = max(h for _, h in built)
    for b, h in built:   # one height per row
      b[0] = b[0].replace(f'height="{h:.0f}"', f'height="{row_h:.0f}"', 1)
      rows.append(b)
    y += row_h + gap
  for b in rows:
    body += b
  foot = ("Scenes are drawn to explain each hazard; the plant runs are in assurance/sim §3.7. "
          "Ratings are proposals for review until the I3 confirmation review (WP-C-03 header).")
  if phone:
    for line in wrap(foot + " " + hf.GENERATED.split(" — ")[0] + ".", w - 2 * m, 10.5):
      body.append(t(m, y + 6, line, 10.5, MUTED))
      y += 14
  else:
    body.append(t(m, y + 6, foot, 10.5, MUTED))
    body.append(t(w - m, y + 6, hf.GENERATED.split(" — ")[0], 10, MUTED, None, "end"))
  desc = (f"{len(cs)} cards for {fid} {fname_txt}, one per SC guide word. " +
          " ".join(f"{c['gw']} {c['name']}: {c['hz']}, {c['sg']}{' ASIL ' + c['asil'] if c['asil'] else ''}"
                   f"{', covered by ' + c['sub_by'] if c['sub_by'] else ''}"
                   f"{'; callout: ' + c['label'] if c['label'] else ''}." for c in cs))
  if phone:
    fname = fname.replace(".svg", "-phone.svg")
  return fname, svg_doc(w, int(y + 24), f"{fig}: {fid} {fname_txt} under its SC guide words (WP-C-03 §4)"
                        f"{', phone view' if phone else ''}", desc, body)


def build() -> dict[str, str]:
  return {**dict(sheet(fid) for fid in SHEETS), **dict(sheet(fid, **PHONE, phone=True) for fid in SHEETS)}


if __name__ == "__main__":
  sys.exit(hf.main(sys.argv[1:]))
