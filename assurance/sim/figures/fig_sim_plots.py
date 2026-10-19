#!/usr/bin/env python3
"""Draw the layer-1 and layer-4 result plots of the README as loops, from the committed results.

  fig-sim-reach-anim.svg   §3.6: the reachability bound growing from fault onset, with a top view of the lane where
                           the car may be under any LKA command the panda passes, and the hard-over run inside it.
                           From ../reach/model.json and ../reach/samples.json; the bound is reach_compare.exact().
  fig-sim-search-anim.svg  §3.4: the failure search filling in, the Monte Carlo samples in the order they ran, then
                           the cross-entropy worst case of each round. From the committed search figure and table
                           (search.py writes both and CI checks them against a fresh run).

SMIL, no script, in the style of fig_sim_he.py's animations; the ego sprite is the Kenney Racing Pack car of
fig_sim_ks.py (CC0, pinned in assets/kenney-racing/sources.yaml). Synthetic data (DSR-12), no evidence credit.

    python3 fig_sim_plots.py            # write the SVGs
    python3 fig_sim_plots.py --check    # fail if a committed SVG differs from a fresh build
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SIM / "reach"))

import fig_sim_readme as fs  # noqa: E402  (style and SVG helpers)
from fig_sim_readme import T, el, fmt, para, W  # noqa: E402
import fig_sim_ks as ks  # noqa: E402  (the ego sprite)
import reach_compare as rc  # noqa: E402  (the exact bound)

SEARCH_SVG = HERE / "fig-search-curve-assist-loss.svg"
SEARCH_MD = SIM / "results" / "search-curve-assist-loss.md"
LANE_W = 3.7
VEH_W = 1.781        # Corolla body width (plant/corolla.py), for the lane-line threshold
CUE_M = 0.2          # drift cue of the plant's driver model (README §3.6)
SLOW = 2.0           # the reach loop plays at half speed
HOLD = 1.5           # s held on the last frame before the loop restarts
LOOP_STYLE = ("<style>.asph { fill:var(--grid); } .laned { stroke:var(--ink3); stroke-width:2; } "
              ".edge { stroke:var(--ink2); stroke-width:2; } .thr { stroke:var(--bad); stroke-width:1.3; "
              "stroke-dasharray:6 4; } .reach { fill:var(--amb); opacity:0.28; } .reachl { fill:none; stroke:var(--amb); "
              "stroke-width:2.2; } .amp { fill:none; stroke:var(--ink3); stroke-width:1.6; stroke-dasharray:6 4; } "
              ".trace { fill:none; stroke:var(--real); stroke-width:2.2; } .env { fill:var(--real); opacity:0.18; } "
              ".cursor { stroke:var(--ink); stroke-width:1.6; } .ok { fill:var(--real); } .bad { fill:var(--bad); } "
              ".ce { fill:none; stroke:var(--amb); stroke-width:2.2; } "
              ".halo { paint-order:stroke; stroke:var(--bg); stroke-width:5px; stroke-linejoin:round; }</style>")


def keytimes(n: int, span: float, dur: float) -> str:
  return ";".join(f"{span * k / (n - 1) / dur:.4f}" for k in range(n)) + ";1"


def anim(attr: str, vals: list[str], kt: str, dur: float, discrete: bool = False, typ: str = "") -> str:
  v = ";".join(vals) + ";" + vals[-1]
  cm = ' calcMode="discrete"' if discrete else ""
  if typ:
    return (f'<animateTransform attributeName="transform" type="{typ}" values="{v}" keyTimes="{kt}" '
            f'dur="{dur:.2f}s" repeatCount="indefinite"/>')
  return f'<animate attributeName="{attr}" values="{v}" keyTimes="{kt}"{cm} dur="{dur:.2f}s" repeatCount="indefinite"/>'


def light(k0: float, dur: float, row: str, dim: float = 0.25) -> str:
  return (f'<g opacity="{dim}"><animate attributeName="opacity" values="{dim};1" keyTimes="0;{min(1.0, k0):.4f}" '
          f'calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite"/>{row}</g>')


def first_cross(t: list[float], y: list[float], thr: float) -> float | None:
  for i in range(1, len(t)):
    if y[i - 1] < thr <= y[i]:
      return t[i - 1] + (thr - y[i - 1]) / (y[i] - y[i - 1]) * (t[i] - t[i - 1])
  return None


def at(t: list[float], y: list[float], tq: float) -> float:
  i = min(range(len(t)), key=lambda k: abs(t[k] - tq))
  return y[i]


# ---------------------------------------------------------------- §3.6 reachability bound

def reach_data() -> dict:
  s, m = rc.load(rc.SAMPLES), rc.load(rc.MODEL)
  ex = rc.exact(m, len(s["t"]))
  return {"s": s, "m": m, "t": s["t"], "bound": ex["dt"]["y"], "amp": ex["amp"]["y"],
          "ho": s["hard_over_left_y"], "env_hi": s["y_max"], "env_lo": s["y_min"]}


def fig_reach(d: dict) -> tuple[str, list[str]]:
  errs = []
  t, bound, amp, ho = d["t"], d["bound"], d["amp"], d["ho"]
  tk, horizon, speed = d["s"]["takeover_s"], d["m"]["horizon_s"], d["m"]["speed_kph"]
  thr = (LANE_W - VEH_W) / 2
  frames = [i for i in range(0, len(t), 5)]                  # every 50 ms of model time
  if frames[-1] != len(t) - 1:
    frames.append(len(t) - 1)
  span = t[-1] * SLOW
  dur = span + HOLD
  kt = keytimes(len(frames), span, dur)
  b_tk, a_tk, ho_tk = at(t, bound, tk), at(t, amp, tk), at(t, ho, tk)
  lin = d["s"]["max_linearisation_error_y_m"]
  if ho_tk > b_tk + lin + 1e-6:
    errs.append(f"hard-over run {ho_tk:.3f} m lies outside the bound {b_tk:.3f} m widened by {lin:.3f} m at {tk} s")

  ev = [(0.0, "fault: from here any LKA command the panda passes"),
        (first_cross(t, ho, CUE_M), f"hard-over run drifts {CUE_M:g} m: the driver's cue"),
        (first_cross(t, bound, thr), "the bound reaches the lane line: the body may touch it"),
        (first_cross(t, ho, thr), "the hard-over run's body reaches the lane line"),
        (tk, f"driver corrects; bound {b_tk:.2f} m, hard-over {ho_tk:.2f} m"),
        (t[-1], "loop ends")]
  for te, lab in ev:
    if te is None:
      errs.append(f"reach: event '{lab}' does not happen in the data")
  ev = sorted((te, lab) for te, lab in ev if te is not None)

  hl, hy = para(24, 34, "Reachability bound: where the car can be", W - 48, "h", lh=26)
  sl, sy = para(24, hy - 4, f"Straight road, {speed:g} km/h, engaged, no driver input. From t = 0 a faulty host "
                f"sends any LKA command the panda passes. Linear L1 plant, exact bound (§3.6).", W - 48, "t2", lh=17)
  b = [*hl, *sl, T(24, sy + 4, "Synthetic (DSR-12) · no evidence credit", "tbad"),
       T(24, sy + 23, f"From reach/model.json and samples.json · played at half speed, 0–{t[-1]:g} s", "t2b"),
       el("line", None, x1=24, y1=sy + 34, x2=W - 24, y2=sy + 34, class_="hair")]

  # top view: three lanes, the ego lane in the middle, lateral offset upward (left), true scale
  ry = sy + 50
  px = 14.0
  road_h = 3 * LANE_W * px
  yc = ry + road_h / 2                                    # ego lane centre
  x0, x1 = 24, W - 24
  cx = 150.0                                              # car centre, held in place

  def Y(v):
    return yc - v * px
  b += [T(24, ry - 6, "TOP VIEW (true scale; the car is held in place, the road streams past)", "t2b"),
        el("rect", None, x=x0, y=fmt(ry), width=x1 - x0, height=fmt(road_h), class_="asph")]
  for k, yb in enumerate((1.5, 0.5, -0.5, -1.5)):
    yy = fmt(Y(yb * LANE_W))
    if k in (0, 3):
      b.append(el("line", None, x1=x0, y1=yy, x2=x1, y2=yy, class_="edge"))
    else:
      dash = f'<line x1="{x0}" y1="{yy}" x2="{x1}" y2="{yy}" class="laned" stroke-dasharray="20 20">'
      v_px = speed / 3.6 * px / SLOW                      # px per s of loop time
      b.append(dash + f'<animate attributeName="stroke-dashoffset" values="0;{-40}" dur="{40 / v_px:.3f}s" '
               'repeatCount="indefinite"/></line>')
  b += [T(x1 - 4, Y(LANE_W) + 4, "next lane", "t2", "end"), T(x1 - 4, Y(0) + 4, "ego lane", "t2", "end"),
        T(x1 - 4, Y(-LANE_W) + 4, "next lane", "t2", "end")]
  # where the body can be: the bound and the no-ramp bound (outline) on the car's centre, widened by half the body
  # width, clipped to the road; the band's edge on a lane marking is the body on the lane line
  clip = f'<clipPath id="road"><rect x="{x0}" y="{fmt(ry)}" width="{x1 - x0}" height="{fmt(road_h)}"/></clipPath>'
  bx, bw = cx - 4.63 * px / 2 - 6, 4.63 * px + 12
  half = VEH_W / 2
  ys = [fmt(Y(bound[i] + half)) for i in frames]
  hs = [fmt(2 * (bound[i] + half) * px) for i in frames]
  ya = [fmt(Y(min(amp[i] + half, 2 * LANE_W))) for i in frames]
  ha = [fmt(2 * min(amp[i] + half, 2 * LANE_W) * px) for i in frames]
  b += [f'<g clip-path="url(#road)">',
        f'<rect x="{fmt(bx)}" y="{ys[0]}" width="{fmt(bw)}" height="{hs[0]}" class="amp">{anim("y", ya, kt, dur)}{anim("height", ha, kt, dur)}</rect>',
        f'<rect x="{fmt(bx)}" y="{ys[0]}" width="{fmt(bw)}" height="{hs[0]}" class="reach">{anim("y", ys, kt, dur)}{anim("height", hs, kt, dur)}</rect>',
        "</g>"]
  # the car on the hard-over run, its trail behind it
  defs, ids = ks.sprite_defs([ks.EGO_SPRITE])
  L, Wd = 4.63 * px, VEH_W * px
  pos = [f"{fmt(cx)},{fmt(Y(ho[i]))}" for i in frames]
  b.append(f'<g transform="translate({pos[0].replace(",", " ")})">{anim(None, pos, kt, dur, typ="translate")}'
           f'{ks.car_use(ids[ks.EGO_SPRITE], L, Wd)}</g>')
  ly = ry + road_h + 18
  b += [el("rect", None, x=24, y=fmt(ly - 10), width=14, height=10, class_="reach"),
        T(44, ly, "bound: any command the panda passes", "t2"),
        el("rect", None, x=318, y=fmt(ly - 10), width=14, height=10, class_="amp"),
        T(338, ly, "no panda ramp (where the body can be)", "t2")]

  # plot: lateral offset against time
  py, ph = ly + 40, 150
  px0, px1 = 64, W - 32
  hi = math.ceil(max(at(t, amp, tk), bound[-1]) + 0.5)

  def TX(tt):
    return px0 + tt / t[-1] * (px1 - px0)

  def DY(v):
    return py + (hi - min(v, hi)) / hi * ph
  b += [T(24, py - 10, "LATERAL OFFSET FROM THE LANE CENTRE (m)", "t2b")]
  for v in range(0, int(hi) + 1):
    b += [el("line", None, x1=px0, y1=fmt(DY(v)), x2=px1, y2=fmt(DY(v)), class_="hair"),
          T(px0 - 6, DY(v) + 4, f"{v}", "t2", "end")]
  for tg in range(0, int(t[-1]) + 1):
    b += [T(TX(tg), py + ph + 16, f"{tg}", "t2", "middle")]
  b += [T(px1, py + ph + 30, "time from fault onset (s)", "t2", "end"),
        el("line", None, x1=px0, y1=fmt(DY(thr)), x2=px1, y2=fmt(DY(thr)), class_="thr"),
        T(px0 + 6, DY(thr) - 4, "body on the lane line", "t2")]

  def path(ys_):
    return "M" + " L".join(f"{fmt(TX(t[i]))},{fmt(DY(ys_[i]))}" for i in range(0, len(t), 2))
  env = (" L".join(f"{fmt(TX(t[i]))},{fmt(DY(d['env_hi'][i]))}" for i in range(0, len(t), 2)) + " L" +
         " L".join(f"{fmt(TX(t[i]))},{fmt(DY(-d['env_lo'][i]))}" for i in reversed(range(0, len(t), 2))))
  clip2 = f'<clipPath id="plot"><rect x="{px0}" y="{fmt(py - 2)}" width="0" height="{ph + 4}">' \
          f'{anim("width", [fmt(TX(t[i]) - px0) for i in frames], kt, dur)}</rect></clipPath>'
  b += [f'<g clip-path="url(#plot)">', f'<path d="M{env} Z" class="env"/>',
        f'<path d="{path(amp)}" class="amp"/>', f'<path d="{path(bound)}" class="reachl"/>',
        f'<path d="{path(ho)}" class="trace"/>', "</g>",
        el("line", None, x1=fmt(TX(tk)), y1=fmt(py), x2=fmt(TX(tk)), y2=fmt(py + ph), class_="hair")]
  cur = [f"{fmt(TX(t[i]) - px0)},0" for i in frames]
  b.append(f'<g>{anim(None, cur, kt, dur, typ="translate")}<line x1="{px0}" y1="{fmt(py)}" x2="{px0}" '
           f'y2="{fmt(py + ph)}" class="cursor"/></g>')
  ly2 = py + ph + 50
  b += [el("line", None, x1=24, y1=fmt(ly2 - 4), x2=44, y2=fmt(ly2 - 4), class_="reachl"), T(50, ly2, "bound", "t2"),
        el("line", None, x1=110, y1=fmt(ly2 - 4), x2=130, y2=fmt(ly2 - 4), class_="amp"), T(136, ly2, "no ramp", "t2"),
        el("line", None, x1=210, y1=fmt(ly2 - 4), x2=230, y2=fmt(ly2 - 4), class_="trace"),
        T(236, ly2, "hard-over run", "t2"),
        el("rect", None, x=350, y=fmt(ly2 - 10), width=14, height=10, class_="env"),
        T(370, ly2, f"{d['s']['runs']} sampled runs (nonlinear plant)", "t2")]

  y = ly2 + 30
  b += [T(24, y - 6, "EVENTS (model time; light up as they happen)", "t2b")]
  y += 14
  for te, lab in ev:
    b.append(light(te * SLOW / dur, dur, T(24, y, f"{te:.2f} s", "tb") + T(92, y, lab, "t")))
    y += 22
  foot = (f"The bound is exact for the linear model: no command the panda passes drives it further. The hard-over "
          f"and the sampled runs come from the nonlinear plant, which may exceed it by the measured linearisation "
          f"error ({lin:.3f} m); the hard-over run is the worst case. Without the "
          f"panda's ramp it would be {a_tk:.2f} m at {tk:g} s. Straight road, one speed; the plant is a model, so "
          "this ranks risks and earns no credit (DQ-139). Car: Kenney Racing Pack (CC0).")
  fl, fy = para(24, y + 10, foot, W - 48, "t2", lh=16)
  b += fl
  desc = (f"Synthetic (DSR-12), no evidence credit. Looping reachability bound at {speed:g} km/h on a straight road "
          f"under any LKA command the panda passes, played at half speed from 0 to {t[-1]:g} s. Top view: the amber "
          f"band is where the car's body can be, growing from the lane centre; the dashed outline is the bound "
          f"without the panda's ramp; the car follows the hard-over run inside the band. Plot: the same bound, the "
          f"no-ramp bound, the hard-over run and the envelope of {d['s']['runs']} sampled runs against time. Events: " +
          "; ".join(f"{lab} at {te:.2f} s" for te, lab in ev) + f". {foot}")
  out = fs.svg(int(fy + 16), "Reachability bound, animated", desc, b)
  out = out.replace("</style>", "</style>" + LOOP_STYLE, 1).replace("<defs>", defs[:-7] + clip + clip2, 1)
  return out, errs


# ---------------------------------------------------------------- §3.4 failure search

CIRCLE = re.compile(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="4" class="(ok|bad)"><title>rho (-?[\d.]+) m, '
                    r'(\d+) km/h, lane ([\d.]+) m</title></circle>')
TICK = re.compile(r'<text x="([\d.]+)" y="[\d.]+" class="t2" text-anchor="(middle|end)">([\d.]+)</text>')


def search_data() -> tuple[dict, list[str]]:
  """The Monte Carlo samples (in run order) from the committed search figure, mapped back to a_y and t_r through its
  tick labels, and the cross-entropy worst cases from the committed table."""
  errs = []
  svg = SEARCH_SVG.read_text(encoding="utf-8")
  md = SEARCH_MD.read_text(encoding="utf-8")
  xt = {float(v): float(x) for x, a, v in TICK.findall(svg) if a == "middle"}
  yt = {}
  for m in re.finditer(r'<text x="[\d.]+" y="([\d.]+)" class="t2" text-anchor="end">([\d.]+)</text>', svg):
    yt[float(m.group(2))] = float(m.group(1)) - 4
  if not ({0.0, 1.8} <= set(xt) and {0.75, 1.5} <= set(yt)):
    return {}, ["search figure: axis ticks 0 and 1.8 (a_y), 0.75 and 1.5 (t_r) not found"]

  def a_y(x):
    return (x - xt[0.0]) / (xt[1.8] - xt[0.0]) * 1.8

  def t_r(y):
    return 0.75 + (y - yt[0.75]) / (yt[1.5] - yt[0.75]) * 0.75
  mc = [{"a_y": a_y(float(cx)), "t_r": t_r(float(cy)), "bad": c == "bad", "rho": float(r), "speed": int(v),
         "lane": float(ln)} for cx, cy, c, r, v, ln in CIRCLE.findall(svg)]
  ce = []
  sec = md.split("## Cross-entropy", 1)[-1]
  for row in re.findall(r"^\| (\d) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| (-?[\d.]+) \|", sec, re.M):
    ce.append({"round": int(row[0]), "speed": float(row[1]), "a_y": float(row[2]), "t_r": float(row[4]),
               "rho": float(row[6])})
  m = re.search(r"(\d+) of (\d+) samples depart", md)
  if not m:
    errs.append("search table: 'N of M samples depart' not found")
  else:
    n_bad, n = int(m.group(1)), int(m.group(2))
    if (n_bad, n) != (sum(r["bad"] for r in mc), len(mc)):
      errs.append(f"search figure has {sum(r['bad'] for r in mc)} of {len(mc)} departing, the table {n_bad} of {n}")
  if not ce:
    errs.append("search table: no cross-entropy rows")
  return {"mc": mc, "ce": ce}, errs


def fig_search(d: dict) -> tuple[str, list[str]]:
  errs = []
  mc, ce = d["mc"], d["ce"]
  per, step = 6, 0.25                     # samples per beat, s per beat
  beats_mc = math.ceil(len(mc) / per)
  rounds = sorted({r["round"] for r in ce})
  t_mc = beats_mc * step
  t_ce = 1.0                              # s per cross-entropy round
  span = t_mc + 0.6 + len(rounds) * t_ce
  dur = span + 2.5

  hl, hy = para(24, 34, "Failure search: filling in the map", W - 48, "h", lh=26)
  sl, sy = para(24, hy - 4, "Loss of lateral assistance in a highway curve (EPS fault, F-07), plant model L1. Each "
                "dot is one run; red: the body edge crossed the lane line.", W - 48, "t2", lh=17)
  b = [*hl, *sl, T(24, sy + 4, "Synthetic (DSR-12) · no evidence credit", "tbad"),
       T(24, sy + 23, "From search.py's committed figure and table · speed, lane width and cue also vary", "t2b"),
       el("line", None, x1=24, y1=sy + 34, x2=W - 24, y2=sy + 34, class_="hair")]
  y0 = sy + 62
  x0, x1, ph = 64, W - 24, 300
  y1 = y0 + ph

  def X(a):
    return x0 + a / 1.8 * (x1 - x0)

  def Y(tr):
    return y1 - (tr - 0.75) / 0.75 * ph
  for a in (0.0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8):
    b += [el("line", None, x1=fmt(X(a)), y1=fmt(y0), x2=fmt(X(a)), y2=fmt(y1), class_="hair"),
          T(X(a), y1 + 16, f"{a:.1f}", "t2", "middle")]
  for tr in (0.75, 1.0, 1.25, 1.5):
    b += [el("line", None, x1=x0, y1=fmt(Y(tr)), x2=x1, y2=fmt(Y(tr)), class_="hair"),
          T(x0 - 6, Y(tr) + 4, f"{tr:g}", "t2", "end")]
  b += [T((x0 + x1) / 2, y1 + 34, "curve lateral acceleration a_y (m/s²)", "t2", "middle"),
        T(18, (y0 + y1) / 2, "driver reaction time t_r (s)", "t2", "middle", rotate=-90)]
  for i, r in enumerate(mc):
    k0 = (i // per + 1) * step / dur
    dot = (f'<circle cx="{fmt(X(r["a_y"]))}" cy="{fmt(Y(r["t_r"]))}" r="5" class="{"bad" if r["bad"] else "ok"}">'
           f'<title>rho {r["rho"]:.2f} m, {r["speed"]} km/h, lane {r["lane"]:.2f} m</title></circle>')
    b.append(light(k0, dur, dot, dim=0))
  # running count: one text per beat, shown in turn
  n_bad = 0
  for k in range(beats_mc):
    chunk = mc[k * per:(k + 1) * per]
    n_bad += sum(r["bad"] for r in chunk)
    n = min(len(mc), (k + 1) * per)
    a, z = (k + 1) * step / dur, ((k + 2) * step / dur if k < beats_mc - 1 else 1.0)
    vals, kts = ("0;1;0", f"0;{a:.4f};{z:.4f}") if z < 1.0 else ("0;1", f"0;{a:.4f}")
    b.append(f'<g opacity="0"><animate attributeName="opacity" values="{vals}" keyTimes="{kts}" calcMode="discrete" '
             f'dur="{dur:.2f}s" repeatCount="indefinite"/>'
             f'{T(x0 + 8, y0 - 10, f"Monte Carlo: {n} runs, {n_bad} depart ({round(100 * n_bad / n)}%)", "tb")}</g>')
  # cross-entropy: the best of each round, ringed, with its label
  best = {}
  for r in ce:
    if r["round"] not in best or r["rho"] < best[r["round"]]["rho"]:
      best[r["round"]] = r
  ev = []
  for j, rd in enumerate(rounds):
    r = best[rd]
    tk = t_mc + 0.6 + j * t_ce
    ring = el("circle", None, cx=fmt(X(r["a_y"])), cy=fmt(Y(r["t_r"])), r=fmt(9 + 4 * j), class_="ce")
    b.append(light(tk / dur, dur, ring, dim=0))
    ev.append((tk, f"cross-entropy round {rd}: worst rho {r['rho']:.2f} m at a_y {r['a_y']:.2f}, "
                   f"t_r {r['t_r']:.2f} s, {r['speed']:.0f} km/h"))
  # label the worst cases once the first ring is drawn
  r1 = best[rounds[0]]
  lab = T(X(r1["a_y"]) - 30, Y(r1["t_r"]) + 30, "worst cases (cross-entropy)", "t2b halo", "end")
  b.append(light((t_mc + 0.6) / dur, dur, lab, dim=0))

  y = y1 + 64
  b += [T(24, y - 6, "STEPS (light up as they happen)", "t2b")]
  y += 14
  n_bad = sum(r["bad"] for r in mc)
  mild = min(r["a_y"] for r in mc if r["bad"])
  held = max(r["a_y"] for r in mc if not r["bad"])
  m = re.search(r"Mildest departing curve among the samples: a_y = ([\d.]+) m/s². Sharpest curve held in lane: "
                r"a_y = ([\d.]+) m/s²", SEARCH_MD.read_text(encoding="utf-8"))
  if not m or (f"{mild:.2f}", f"{held:.2f}") != (m.group(1), m.group(2)):
    errs.append(f"search: mildest departing {mild:.2f} and sharpest held {held:.2f} m/s² differ from the table")
  rows = [(step, f"Monte Carlo: {len(mc)} uniform samples over the box, in the order they ran"),
          (t_mc, f"{n_bad} of {len(mc)} depart; the mildest departing curve is a_y {mild:.2f} m/s², the sharpest "
                 f"held in lane {held:.2f} m/s²"), *ev]
  for tk, lab in rows:
    lines = fs.wrap(lab, W - 48, "t")
    row = "".join(T(24, y + 19 * i, ln, "t") for i, ln in enumerate(lines))
    b.append(light(tk / dur, dur, row))
    y += 19 * len(lines) + 6
  foot = ("The share of departing runs describes the sampled box, not a probability on the road: the box is "
          "uniform by construction. The worst cases rank where bench and closed-course tests look first (WP-V-04 U-4).")
  fl, fy = para(24, y + 8, foot, W - 48, "t2", lh=16)
  b += fl
  desc = ("Synthetic (DSR-12), no evidence credit. Looping failure search for loss of lateral assistance in a highway "
          f"curve: {len(mc)} Monte Carlo runs appear as dots in the order they ran, against curve lateral "
          f"acceleration and driver reaction time, red where the body edge crossed the lane line ({n_bad} of "
          f"{len(mc)}) and blue where it stayed in; then the cross-entropy worst case of each of {len(rounds)} rounds "
          "is ringed: " + "; ".join(lab for _t, lab in ev) + f". {foot}")
  out = fs.svg(int(fy + 16), "Failure search, animated", desc, b)
  return out.replace("</style>", "</style>" + LOOP_STYLE, 1), errs


# ---------------------------------------------------------------- build and check

def build() -> tuple[dict[str, str], list[str]]:
  r, e1 = fig_reach(reach_data())
  sd, e2 = search_data()
  s, e3 = fig_search(sd) if sd else ("", [])
  return {"fig-sim-reach-anim.svg": r, "fig-sim-search-anim.svg": s}, e1 + e2 + e3


def main(argv: list[str]) -> int:
  out, errs = build()
  errs = ks.sprite_problems() + errs
  if "--check" in argv:
    errs += [f"{n} is stale; run fig_sim_plots.py" for n, c in out.items()
             if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for e in errs:
      print(f"error: {e}", file=sys.stderr)
    if not errs:
      print(f"fig_sim_plots: {len(out)} figures current")
    return 1 if errs else 0
  for n, c in out.items():
    (HERE / n).write_text(c, encoding="utf-8")
  for e in errs:
    print(f"warning: {e}", file=sys.stderr)
  print(f"wrote {len(out)} figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
