#!/usr/bin/env python3
"""Draw the SOTIF scene sheet: one card per SOTIF hazard, the chain TC -> FI -> SH as a chart over a top-down scene.

`../figures/fig-c06-5-2-sotif-scenes.svg`: one card for each hazard of WP-C-05 §3 (SH-07 is not used). Nothing fails in
these scenes: the system works as specified, and a triggering condition (WP-C-06 §4) exposes a functional insufficiency
(§3). Each card draws one primary row of the §5 evaluation and lists the other triggering conditions that reach the same
hazard. The card style follows the class §3 gives the primary insufficiency:

- P, performance insufficiency ("it sees it wrong"): a blue dashed layer shows what the camera or radar believes, drawn
  over the true road; the chart sets that belief against what is true.
- S, specification insufficiency ("it does what it was told, and that is not enough"): the chart sets what the situation
  needs against what the specification delivers, with the specified limit as a grey dashed line where there is one and
  the gap shaded.

Each scene loops (SMIL, no script, 6 s); a viewer that does not animate shows the last frame. Hazard texts, S and C come
from WP-C-05 §3; the triggering condition, insufficiency, system response, evaluation and action from WP-C-06 §3-§5. The
behaviour curves below are schematic: they explain each hazard and are not simulation results.

The build fails if a card's triggering condition, insufficiency or hazard is not in the documents, if the insufficiency
does not link to the hazard in §3 or the §5 row does not name it, or if a hazard has no card. A card may have no row (a
model with no triggering condition) only while no insufficiency links its hazard; the build fails once one does.
Built and checked by `sotif_figures.py`.

Standard library only. Drawing helpers come from ../hara/.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hara"))
sys.path.insert(0, str(HERE.parents[1] / "01-management" / "figures"))
import hara_figures as hf  # noqa: E402
import sotif_figures as sf  # noqa: E402
import scenekit as sk  # noqa: E402  (road, car, marks, SMIL helpers)
from scenekit import DRIVE, anim as _anim, car_body as _car_body, d as _d  # noqa: E402
from hara_figures import HAIR, INK, MUTED, pill, svg_doc, t, wrap  # noqa: E402

NAME = "fig-c06-5-2-sotif-scenes.svg"
GREEN, RED, FAULT, CALL = sk.REQ_S, sk.PERF_S, sk.FAULT, sk.CALLOUT
CG, CR = sk.REQ, sk.PERF
EGO, EGO_S, GREY, GREY_S = sk.EGO, sk.EGO_EDGE, sk.OTHER, sk.OTHER_EDGE
BLUE, CB, CL = "#60A5FA", "#2563EB", "#475569"   # what the camera or radar believes (on the road, in the chart); a limit
EV_CHIP = {"val": ("#FEF3C7", "#78350F", "Needs validation"), "mod": ("#FEE2E2", "#7F1D1D", "Needs modification"),
           "acc": ("#DCFCE7", "#14532D", "Acceptable"), "none": ("#E2E8F0", "#334155", "Not in WP-C-06")}
CLASS_CHIP = {"P": ("#DBEAFE", "#1E3A8A", "P · it sees it wrong"), "S": ("#EDE9FE", "#4C1D95", "S · not enough as specified"),
              "": ("#E2E8F0", "#334155", "no insufficiency yet")}


# ---------------------------------------------------------------- documents

@dataclass
class Docs:
  data: sf.Data
  h: dict[str, str]                       # SH -> linked-H column (WP-C-05 §3)
  proposed: set[str]                      # SHs whose S and C still wait for the lead's acceptance (WP-C-05 §3 rationale)
  rows: list[dict]                        # WP-C-06 §5 rows with response and action
  measures: dict[str, str]                # SH -> WP-C-05 §6 proposed modifications


def load() -> Docs:
  md5, md6 = sf.C05.read_text(encoding="utf-8"), sf.C06.read_text(encoding="utf-8")
  data = sf.parse(md5, md6)
  h, proposed = {}, set()
  for ln in sf._section(md5, 3, "WP-C-05").splitlines():
    if re.match(r"^\| SH-\d\d \|", ln):
      c = sf._cells(ln)
      h[c[0]] = c[3]
      if "pending the lead's acceptance" in c[7]:
        proposed.add(c[0])
  measures = {}
  for ln in sf._section(md5, 6, "WP-C-05").splitlines():
    if re.match(r"^\| SH-\d\d \|", ln):
      c = sf._cells(ln)
      measures[c[0]] = c[3]
  rows = []
  for ln in sf._section(md6, 5, "WP-C-06").splitlines():
    if re.match(r"^\| TC-\d\d", ln):
      c = sf._cells(ln)
      rows.append(dict(tc=sf._ids(c[0], "TC"), fi=sf._ids(c[1], "FI"), sh=sf._ids(c[2], "SH"),
                       resp=c[3].replace("`", ""), ev=c[4], out=sf.outcome(c[4]), act=c[5].replace("`", "")))
  return Docs(data, h, proposed, rows, measures)


# ---------------------------------------------------------------- scene helpers over the scene kit (time-based; f in [0, 1] of the drive)

def kt(f):
  return DRIVE * f


def drive(samples, inner):
  return sk.drive_turning(samples, inner)


def appear(f):
  return sk.appear(kt(f))


def window(f0, f1):
  """Shown between f0 and f1 of the drive; the still frame (last frame) hides it."""
  return sk.window(kt(f0), kt(f1))


def trail(samples, col=RED, w=2.6):
  return sk.track(samples, col, w)


def car(x, y, a, body, stroke=INK, op=1.0):
  return sk.car_at(x, y, body, stroke, op, a)


def ghost(stroke=GREEN):
  return sk.ghost_body(stroke)


def label(x, y, s, col="#334155", size=7, anchor="middle", halo=False, weight=600):
  return sk.road_label(x, y, s, col, size, weight, anchor, halo)


def ring(x, y, text, f, above=True):
  return sk.callout(x, y, 6.5, text, min(124, max(10, y - 11 if above else y + 16)), kt(f))


def marker(x, y, f):
  return sk.fault_marker(x, y, kt(f))


def walker(samples):
  return sk.pedestrian(samples)


def straight(edge_right=True, extra=""):
  """Two-lane carriageway: ego lane centre y = 84 (edges 99 / 69), next lane above (69 / 39)."""
  return sk.straight_road(sk.EGO_LANE, edge_right, extra)


def start(x, y):
  """The ego car's start, faded."""
  return sk.start_marker(f"translate({x:.1f} {y:.1f}) rotate(0.0)")


def sample(fn, n=80):
  return [(i / n, *fn(i / n)) for i in range(n + 1)]


# ---------------------------------------------------------------- charts (280 x 110)

CX0, CX1, CY0, CY1 = 28, 268, 12, 96


def xt(f):
  return CX0 + f * (CX1 - CX0)


def frame(ylabel, ticks):
  b = [f'<rect x="{CX0}" y="{CY0}" width="{CX1 - CX0}" height="{CY1 - CY0}" fill="#FFFFFF"/>',
       f'<line x1="{CX0}" y1="{CY0}" x2="{CX0}" y2="{CY1}" stroke="#94A3B8"/>',
       f'<line x1="{CX0}" y1="{CY1}" x2="{CX1}" y2="{CY1}" stroke="#94A3B8"/>',
       t(CX0 - 3, 8, ylabel, 8, MUTED, 600),
       t(CX1, 106, "time", 7.5, MUTED, None, "end")]
  b += [t(CX0 - 3, y + 2.5, s, 7.5, MUTED, None, "end") for y, s in ticks]
  return b


def line(pts, col, w=2.6, dash=None):
  d = f' stroke-dasharray="{dash}"' if dash else ""
  return (f'<path d="M' + " L".join(f"{xt(f):.1f} {y:.1f}" for f, y in pts) +
          f'" fill="none" stroke="{col}" stroke-width="{w}"{d} stroke-linejoin="round"/>')


def needed(pts):
  return line(pts, CG, 2.2, "6 3")


def believed(pts, text, ty):
  return line(pts, CB, 1.8, "2 3") + t(xt(pts[0][0]) + 4, ty, text, 7, CB, 600)


def limit(y, text, below=False):
  return (f'<line x1="{CX0}" y1="{y:.1f}" x2="{CX1}" y2="{y:.1f}" stroke="{CL}" stroke-width="1.2" stroke-dasharray="3 3"/>' +
          t(CX1 - 2, y + (9 if below else -3), text, 7, CL, None, "end"))


def gap(upper, lower):
  """Shade between two series given as [(f, y)] on the same f grid."""
  pts = [(xt(f), y) for f, y in upper] + [(xt(f), y) for f, y in lower[::-1]]
  return f'<path d="{_d(pts)} Z" fill="{RED}" opacity="0.18"/>'


def cursor():
  v = [str(CX0), str(CX1), str(CX1)]
  return (f'<line x1="{CX1}" y1="{CY0}" x2="{CX1}" y2="{CY1}" stroke="{INK}" stroke-width="0.8" opacity="0.45">'
          f'{_anim("x1", None, v, [0, DRIVE, 1])}{_anim("x2", None, v, [0, DRIVE, 1])}</line>')


def note(f, y, s, col="#B45309"):
  anchor = "end" if f > 0.6 else "start"
  return f"<g>{appear(f)}" + t(xt(f) + (-3 if anchor == "end" else 3), y, s, 7, col, 600, anchor) + "</g>"


# ---------------------------------------------------------------- scene models, one per SOTIF hazard

def sh01():
  """TC-05 / FI-01: a tar seam taken for the lane edge."""
  n, seam = 80, (lambda x: 99 - (x - 70) * (27 / 192))
  right = lambda x: 99 if x < 92 else seam(x)
  y, path = 84.0, []
  for i in range(n + 1):
    f = i / n
    x = 14 + 248 * f
    y += ((69 + right(x)) / 2 - y) * 0.09
    path.append((f, x, y))
  dep = next(p for p in path if p[2] - 5 < 69)
  f92 = (92 - 14) / 248
  sc = straight(False, '<path d="M70 99.6 L262 72" stroke="#1F242B" stroke-width="2.6" stroke-linecap="round"/>')
  sc += [f'<line x1="0" y1="99" x2="70" y2="99" stroke="{sk.PAINT}" stroke-width="1.5"/>',
         f'<line x1="70" y1="99" x2="280" y2="99" stroke="{sk.PAINT}" stroke-width="1.5" opacity="0.3"/>',
         label(250, 117, "edge line faded"), label(118, 109, "tar seam"),
         f'<path d="M92 {seam(92):.1f} L262 72" fill="none" stroke="{BLUE}" stroke-width="1.6" stroke-dasharray="4 3"/>',
         f'<path d="M92 {(69 + seam(92)) / 2:.1f} L262 70.5" fill="none" stroke="{BLUE}" stroke-width="1.2" stroke-dasharray="2 3"/>',
         label(150, 62, "camera: lane edge", BLUE, 7, "middle", True),
         f'<path d="M14 84 L262 84" fill="none" stroke="{GREEN}" stroke-width="2.2" stroke-dasharray="5 3"/>',
         car(215, 54, 0, GREY, GREY_S), trail(path), start(20, 84),
         drive(path, _car_body(EGO, EGO_S)), marker(92, path[int(f92 * n)][2], f92),
         ring(dep[1], dep[2], "into the next lane", dep[0])]
  zero, ln = 58, 28
  off = [(f, zero + (y - 84) * 2.0) for f, _, y in path[::4]]
  ch = frame("offset in lane", [(zero, "0"), (ln, "line")]) + [
    limit(ln, "lane line"), needed([(0, zero), (1, zero)]),
    believed([(0, zero + 2), (1, zero + 2)], "believed: centred", zero + 12), line(off, CR), cursor()]
  return ch, sc


def sh02():
  """TC-14 / FI-09, FI-11: a curve tighter than the steering torque can follow."""
  n, k_max, cap = 90, 0.0040, 0.0024
  kap = lambda x: 0 if x < 40 else (k_max * (x - 40) / 90 if x < 130 else k_max)
  rs = ry = cs = cy = 0.0
  road, path, sat = [], [], None
  xs = [14 + 248 * i / n for i in range(n + 1)]
  for i, x in enumerate(xs):
    if i:
      dx = x - xs[i - 1]
      rs -= kap(x) * dx
      ry += rs * dx
      if kap(x) > cap and sat is None:
        sat = i
      cs -= min(kap(x), cap) * dx
      cy += cs * dx
    road.append((x, 108 + ry))
    path.append((i / n, x, 108 + cy))
  path = [p for p in path if p[2] < 124]
  edge = lambda k: [(x, y + k) for x, y in road]
  dep = next(p for i, p in enumerate(path) if p[2] - road[i][1] > 10)
  sc = [*sk.curved_road(edge, arrow=False),
        label(276, 125, "curve tighter than R_ODD at the travel speed", anchor="end"),
        f'<path d="{_d(road)}" fill="none" stroke="{GREEN}" stroke-width="2.2" stroke-dasharray="5 3"/>',
        trail(path), start(20, 108), drive(path, _car_body(EGO, EGO_S)),
        marker(path[sat][1], path[sat][2], path[sat][0]), ring(dep[1], dep[2], "crosses edge line", dep[0], above=False)]
  cap_y = 96 - cap / k_max * 78
  need = [(i / n, 96 - kap(x) / k_max * 78) for i, x in enumerate(xs)]
  got = [(f, max(y, cap_y)) for f, y in need]
  fs = sat / n
  ch = frame("steering torque", [(96, "0"), (cap_y, "limit")]) + [
    gap([p for p in need if p[0] >= fs], [p for p in got if p[0] >= fs]), limit(cap_y, "torque limit (FI-11)", below=True),
    needed(need), line(got, CR), note(fs, cap_y + 20, "steerSaturated: warning only"), cursor()]
  return ch, sc


def sh03():
  """TC-27 / FI-12: auto-resume from standstill while a pedestrian crosses between ego and lead."""
  ego = sample(lambda f: (110 + (350 * (f - .3) ** 2 if f < .6 else 31.5 + 210 * (f - .6)) * (f >= .3), 84))
  lead = sample(lambda f: (150 + (420 * (f - .15) ** 2 if f >= .15 else 0), 84))
  lead = [(f, min(x, 300), y) for f, x, y in lead]
  ped = sample(lambda f: (138, 112 - 54 * min(1, max(0, (f - .25) / .35))), 40)
  near = next(i for i, p in enumerate(ego) if p[1] + 11 >= 135)
  sc = straight(extra='<line x1="0" y1="114" x2="280" y2="114" stroke="#94A3B8" stroke-width="0.6"/>')
  sc += [label(138, 124, "pedestrian crosses between the cars"),
         f'<g transform="translate(110.0 84.0) rotate(0.0)">{ghost()}</g>',
         drive(lead, _car_body(GREY, GREY_S)), walker(ped), trail(ego), drive(ego, _car_body(EGO, EGO_S)),
         marker(150 + 13, 72, .15), label(163, 26, "lead moves off"),
         ring(ego[near][1] + 11, 84, "resumes toward the pedestrian", ego[near][0])]
  acc = [(f, 94 if f < .3 else 40) for f in (0, .299, .3, 1)]
  ch = frame("acceleration", [(94, "0"), (40, "go")]) + [
    gap([(.3, 40), (1, 40)], [(.3, 94), (1, 94)]), needed([(0, 94), (1, 94)]), line(acc, CR),
    note(.15, 22, "lead moves off", CL), note(.3, 34, "auto-resume, as specified"), cursor()]
  return ch, sc


def sh04():
  """TC-10 / FI-06: a radar return from an overhead gantry taken for a lead."""
  n, g = 100, 170
  ex, fx, ev, fv, e, fl = 70.0, 26.0, 150.0, 150.0, [], []
  g0, g1 = .28, .58
  for i in range(n + 1):
    f = i / n
    e.append((f, ex, 84))
    fl.append((f, fx, 84))
    ev = max(55, ev - 330 / n) if g0 <= f < g1 else min(150, ev + 140 / n)
    fv = fv if f < .42 else max(70, fv - 260 / n)
    ex += ev / n
    fx = min(fx + fv / n, ex - 27)
  i_min = min(range(n + 1), key=lambda i: e[i][1] - fl[i][1])
  sc = straight(extra=f'<rect x="{g - 5}" y="30" width="10" height="78" fill="#2D333B" opacity="0.85"/>'
                      f'<rect x="{g - 14}" y="42" width="28" height="12" rx="1.5" fill="#15803D"/>')
  sc += [label(g, 22, "overhead gantry"),
         f'<g opacity="0">{window(g0, g1)}<g transform="translate({g} 84)">{ghost(BLUE)}</g>' +
         label(g, 75, "radar: lead", BLUE, 7, "middle", True) + "</g>",
         drive([(0, 70, 84), (1, 220, 84)], ghost()), drive(fl, _car_body(GREY, GREY_S)), drive(e, _car_body(EGO, EGO_S)),
         marker(g, 62, g0), ring(fl[i_min][1] + 12, 84, "close follower closes in", fl[i_min][0], above=False)]
  brake = [(0, 94), (g0, 94), (g0 + .03, 24), (g1, 24), (g1 + .02, 94), (1, 94)]
  ch = frame("braking", [(94, "0"), (24, "max")]) + [
    f'<rect x="{xt(g0):.1f}" y="{CY0}" width="{xt(g1) - xt(g0):.1f}" height="{CY1 - CY0}" fill="{BLUE}" opacity="0.12"/>',
    t(xt((g0 + g1) / 2), CY0 + 9, "ghost lead in radar", 7, CB, 600, "middle"),
    needed([(0, 94), (1, 94)]), line(brake, CR), cursor()]
  return ch, sc


def sh05():
  """TC-29 / FI-21: gas pressed to override; the driver believes the system is off and steers for the exit."""
  exit_road = (f'<path d="M120 99 L280 99 L280 130 L205 130 Z" fill="{sk.ASPHALT}"/>'
               f'<path d="M118 101 L205 130" stroke="{sk.PAINT}" stroke-width="1.5"/>')
  sc = straight(False, exit_road)
  sc += [f'<line x1="0" y1="99" x2="130" y2="99" stroke="{sk.PAINT}" stroke-width="1.5"/>',
         f'<line x1="130" y1="99" x2="280" y2="99" stroke="{sk.PAINT}" stroke-width="1.5" stroke-dasharray="4 4"/>',
         label(250, 125, "exit lane", sk.ARROW)]
  want = sample(lambda f: (14 + 248 * f, 84 + 32 * max(0, min(1, (f - .35) / .45)) ** 1.5))
  got = sample(lambda f: (14 + 248 * f, 84 + 9 * math.sin(math.pi * max(0, min(1, (f - .35) / .4)))))
  sc += [f'<path d="{_d([(x, y) for _, x, y in want])}" fill="none" stroke="{GREEN}" stroke-width="2.2" stroke-dasharray="5 3"/>',
         trail(got), drive(got, _car_body(EGO, EGO_S)), marker(14 + 248 * .25, 72, .25),
         label(14 + 248 * .25, 26, "gas pressed"), ring(got[50][1], got[50][2], "still steering in lane", got[50][0], above=False)]
  ch = frame("lateral control", [(94, "off"), (30, "on")]) + [
    gap([(.25, 30), (1, 30)], [(.25, 94), (1, 94)]), needed([(0, 30), (.25, 30), (.25, 94), (1, 94)]),
    t(xt(.27), 88, "driver expects: off", 7, CG, 600), line([(0, 30), (1, 30)], CR), note(.25, 22, "gas pressed: override, no disengage"), cursor()]
  return ch, sc


def sh06():
  """TC-33 / FI-10: the lead brakes harder than the item's deceleration bound."""
  n, v = 100, 120.0
  def run(x0, f0, a):
    out, x, s = [], x0, v
    for i in range(n + 1):
      f = i / n
      out.append((f, x, 84))
      if f >= f0:
        s = max(0, s - a / n)
      x += s / n
    return out
  lead, ego, need = run(150, .25, 360), run(90, .32, 180), run(90, .32, 260)
  i_min = min(range(n + 1), key=lambda i: lead[i][1] - ego[i][1])
  sc = straight() + [drive(need, ghost()), drive(lead, _car_body(GREY, GREY_S)), trail(ego), drive(ego, _car_body(EGO, EGO_S)),
                     marker(lead[25][1] + 14, 72, .25), label(lead[25][1] + 14, 26, "lead brakes hard"),
                     ring(ego[i_min][1] + 11, 84, "closes on the lead", ego[i_min][0], above=False)]
  lim = 50
  need_c = [(0, 94), (.32, 94), (.33, 26), (1, 26)]
  got = [(0, 94), (.32, 94), (.33, lim), (1, lim)]
  ch = frame("braking", [(94, "0"), (lim, "bound")]) + [
    gap([(.33, 26), (1, 26)], [(.33, lim), (1, lim)]), limit(lim, "decel bound 3.5 m/s² (FI-10)", below=True),
    needed(need_c), line(got, CR), cursor()]
  return ch, sc


def sh08():
  """TC-34 / FI-23: stock PCS braking delayed by the item's commands or message handling (AOU-04 unverified)."""
  def run(f0, a, x0=40.0, v=230.0, n=100):
    out, x, s = [], x0, v
    for i in range(n + 1):
      f = i / n
      out.append((f, x, 84))
      if f >= f0:
        s = max(0, s - a / n)
      x += s / n
    return out
  stopped = 248
  ego, need = run(.52, 460), run(.40, 460)
  sc = straight() + [car(stopped, 84, 0, GREY, GREY_S), label(stopped, 26, "stopped car"),
                     drive(need, ghost()), trail(ego), drive(ego, _car_body(EGO, EGO_S)),
                     ring(ego[-1][1] + 12, 84, "PCS brakes late", .9, above=False)]
  ch = frame("PCS braking", [(94, "0"), (26, "full")]) + [
    gap([(.40, 26), (.52, 26)], [(.40, 94), (.52, 94)]), needed([(0, 94), (.40, 94), (.40, 26), (1, 26)]),
    line([(0, 94), (.52, 94), (.52, 26), (1, 26)], CR), note(.4, 18, "forwarding unverified (AOU-04)", CL), cursor()]
  return ch, sc


def sh09():
  """TC-13 / FI-05: Experimental Mode misses a red light."""
  cross = (f'<rect x="176" y="0" width="30" height="130" fill="{sk.ASPHALT}"/>'
           f'<line x1="191" y1="0" x2="191" y2="32" stroke="{sk.PAINT}" stroke-width="1" stroke-dasharray="6 6"/>'
           f'<line x1="191" y1="106" x2="191" y2="130" stroke="{sk.PAINT}" stroke-width="1" stroke-dasharray="6 6"/>'
           f'<line x1="172" y1="69" x2="172" y2="99" stroke="{sk.PAINT}" stroke-width="2.4"/>'
           '<rect x="160" y="103" width="8" height="18" rx="2" fill="#1F2937"/><circle cx="164" cy="108" r="2.6" fill="#EF4444"/>'
           '<circle cx="164" cy="115" r="2.6" fill="#374151"/>')
  sc = straight(extra=cross)
  ego = sample(lambda f: (30 + 230 * f, 84))
  stop = sample(lambda f: (30 + 230 * f if f < .35 else 110.5 + 50 * (1 - (1 - min(1, (f - .35) / .4)) ** 2), 84))
  cross_car = sample(lambda f: (198, -20 + 170 * f), 60)
  i_hit = min(range(len(ego)), key=lambda i: abs(ego[i][1] - 186) + 9)
  sc += [label(164, 128, "red light"), drive(stop, ghost()), drive(cross_car, _car_body(GREY, GREY_S)),
         f'<g opacity="0">{window(.3, .7)}<rect x="155" y="99" width="18" height="26" rx="3" fill="none" stroke="{BLUE}" stroke-width="1.4" stroke-dasharray="3 2"/>' +
         label(152, 110, "model: no stop", BLUE, 7, "end", True) + "</g>",
         trail(ego), drive(ego, _car_body(EGO, EGO_S)), marker(164, 98, .3), ring(ego[i_hit][1], 84, "enters on red", ego[i_hit][0])]
  ch = frame("braking", [(94, "0"), (40, "stop")]) + [
    gap([(.35, 40), (.75, 40)], [(.35, 94), (.75, 94)]), needed([(0, 94), (.35, 94), (.36, 40), (.75, 40), (.76, 94), (1, 94)]),
    believed([(0, 92), (1, 92)], "believed: no stop needed", 86), line([(0, 94), (1, 94)], CR), cursor()]
  return ch, sc


def sh10():
  """TC-28 / FI-13: the driver nudges for a lane change with a car in the blind spot."""
  lane = lambda f: 84 - 30 * (0 if f < .3 else min(1, (f - .3) / .4)) ** 1.2
  ego = sample(lambda f: (50 + 190 * f, lane(f)))
  other = sample(lambda f: (24 + 190 * f, 54))
  i_hit = next(i for i, p in enumerate(ego) if p[2] - 5 < 69)
  sc = straight() + [f'<path d="M50 84 L240 84" fill="none" stroke="{GREEN}" stroke-width="2.2" stroke-dasharray="5 3"/>',
                     drive(other, _car_body(GREY, GREY_S)), trail(ego), drive(ego, _car_body(EGO, EGO_S)),
                     marker(50 + 190 * .3, 98, .3), label(50 + 190 * .3, 112, "driver nudges"),
                     label(24, 30, "car in the blind spot", "#334155", 7, "start"),
                     ring(ego[i_hit][1], ego[i_hit][2], "into an occupied lane", ego[i_hit][0], above=False)]
  mv = [(f, 94 - 64 * (0 if f < .3 else min(1, (f - .3) / .4))) for f in [i / 20 for i in range(21)]]
  ch = frame("lane change", [(94, "0"), (30, "full")]) + [
    gap(mv, [(f, 94) for f, _ in mv]), needed([(0, 94), (1, 94)]), line(mv, CR), note(.3, 22, "nudge: no blind-spot check"), cursor()]
  return ch, sc


def sh11():
  """TC-12 / FI-04: a pedestrian in the lane is not treated as a lead."""
  ego = sample(lambda f: (30 + 160 * f, 84))
  stop = sample(lambda f: (30 + 160 * f if f < .5 else 110 + 45 * (1 - (1 - min(1, (f - .5) / .35)) ** 2), 84))
  ped = sample(lambda f: (214, 118 - 32 * min(1, max(0, (f - .15) / .45))), 40)
  sc = straight() + [label(214, 126, "pedestrian on the carriageway"), drive(stop, ghost()), walker(ped),
                     f'<g opacity="0">{appear(.4)}<circle cx="214" cy="86" r="8" fill="none" stroke="{BLUE}" stroke-width="1.3" stroke-dasharray="3 2"/>' +
                     label(214, 62, "model: no lead", BLUE, 7, "middle", True) + "</g>",
                     trail(ego), drive(ego, _car_body(EGO, EGO_S)), marker(214, 98, .4),
                     ring(ego[-1][1] + 12, 84, "no reaction to the pedestrian", .92, above=False)]
  ch = frame("braking", [(94, "0"), (34, "stop")]) + [
    gap([(.5, 34), (1, 34)], [(.5, 94), (1, 94)]), needed([(0, 94), (.5, 94), (.51, 34), (1, 34)]),
    believed([(0, 92), (1, 92)], "believed: no lead", 86), line([(0, 94), (1, 94)], CR), cursor()]
  return ch, sc


def sh12():
  """TC-25 / FI-19: small periodic steering inputs reset the awareness estimate of a driver who is not watching."""
  ego = sample(lambda f: (20 + 240 * f, 84 + 1.2 * math.sin(f * 40)))
  sc = straight() + [trail(ego), drive(ego, _car_body(EGO, EGO_S)),
                     *[label(20 + 240 * f, 106, "input", "#334155") + marker(20 + 240 * f, 98, f) for f in (.2, .4, .6, .8)],
                     label(140, 26, "driver looking at a phone; small wheel inputs only"),
                     ring(ego[-1][1], 84, "never alerted", .95)]
  thr, base, rate = 50, 94, 72
  saw, last = [], 0.0
  for i in range(101):
    f = i / 100
    if any(abs(f - r) < 1e-9 for r in (.2, .4, .6, .8)):
      saw.append((f, base - rate * (f - last)))
      last = f
    saw.append((f, base - rate * (f - last)))
  f_thr = (base - thr) / rate
  ch = frame("inattention", [(94, "0"), (22, "high")]) + [
    limit(thr, "alert threshold"), needed([(0, base), (1, base - rate)]), line(saw, CR),
    note(f_thr, thr + 26, "should alert here", CG), cursor()]
  return ch, sc


def sh13():
  """TC-20 / FI-16: above the ODD speed bound the item stays engaged; only a warning above 149 km/h."""
  spd = lambda f: 95 + 60 * f                       # km/h, schematic
  x, ego = 20.0, []
  for i in range(101):
    f = i / 100
    ego.append((f, x, 84))
    x += spd(f) / 100 * 1.55
  f110, f149 = (110 - 95) / 60, (149 - 95) / 60
  odd = [(f, 20 + sum(min(spd(j / 100), 110) / 100 * 1.55 for j in range(int(f * 100))), 84) for f in [i / 100 for i in range(101)]]
  sc = straight() + [drive(odd, ghost()), trail(ego), drive(ego, _car_body(EGO, EGO_S)),
                     marker(ego[int(f110 * 100)][1], 98, f110), label(ego[int(f110 * 100)][1], 112, "110 km/h: ODD bound"),
                     ring(ego[int(f149 * 100)][1], 84, "149 km/h: warning only, still engaged", f149)]
  sy = lambda v: 96 - (v - 90) / 70 * 80
  ch = frame("speed", [(sy(110), "110"), (sy(149), "149")]) + [
    gap([(f110, sy(110)), (1, sy(155))], [(f110, sy(110)), (1, sy(110))]),
    limit(sy(110), "ODD bound", below=True), limit(sy(149), "warning (speedTooHigh)", below=True),
    needed([(0, sy(95)), (f110, sy(110)), (1, sy(110))]), line([(0, sy(95)), (1, sy(155))], CR), cursor()]
  return ch, sc


def sh14():
  """TC-36 / FI-24: a patrol car stopped on the shoulder, its officer at the lane edge; the item does not move over."""
  lane = lambda f: 84 - 30 * (0 if f < .25 else min(1, (f - .25) / .3)) ** 1.2
  ego = sample(lambda f: (30 + 230 * f, 84))
  over = sample(lambda f: (30 + 230 * f, lane(f)))
  officer = sample(lambda f: (172, 103), 10)
  beacon = '<circle cx="158" cy="110" r="2.2" fill="#EF4444"/><circle cx="164" cy="110" r="2.2" fill="#3B82F6"/>'
  i_pass = min(range(len(ego)), key=lambda i: abs(ego[i][1] - 172))
  sc = straight() + [car(160, 116, 0, GREY, GREY_S), beacon, label(150, 128, "patrol car on the shoulder", anchor="end"),
                     drive(over, ghost()), walker(officer),
                     f'<g opacity="0">{window(.2, .6)}<rect x="146" y="102" width="30" height="22" rx="3" fill="none" stroke="{BLUE}" stroke-width="1.4" stroke-dasharray="3 2"/>' +
                     label(178, 56, "model: no beacon output", BLUE, 7, "middle", True) + "</g>",
                     trail(ego), drive(ego, _car_body(EGO, EGO_S)), marker(118, 98, .25),
                     ring(ego[i_pass][1], 84, "passes the officer at 105 km/h", ego[i_pass][0])]
  mv = [(f, 94 - 64 * (0 if f < .25 else min(1, (f - .25) / .3))) for f in [i / 20 for i in range(21)]]
  ch = frame("move over", [(94, "0"), (30, "lane")]) + [
    gap(mv, [(f, 94) for f, _ in mv]), needed([(f, y) for f, y in mv]), line([(0, 94), (1, 94)], CR),
    note(.25, 22, "beacons ahead: no move-over"), cursor()]
  return ch, sc


# hazard: (short title, primary TC, primary FI, draw)
MODELS = {
  "SH-01": ("Leaves the lane on a false line", "TC-05", "FI-01", sh01),
  "SH-02": ("Runs wide in a tight curve", "TC-14", "FI-11", sh02),
  "SH-03": ("Auto-resumes into a crossing pedestrian", "TC-27", "FI-12", sh03),
  "SH-04": ("Phantom braking under a gantry", "TC-10", "FI-06", sh04),
  "SH-05": ("Gas override does not disengage", "TC-29", "FI-21", sh05),
  "SH-06": ("Lead brakes harder than the bound", "TC-33", "FI-10", sh06),
  "SH-08": ("Stock PCS braking delayed", "TC-34", "FI-23", sh08),
  "SH-09": ("Drives through a red light", "TC-13", "FI-05", sh09),
  "SH-10": ("Lane change into an occupied lane", "TC-28", "FI-13", sh10),
  "SH-11": ("No reaction to a pedestrian", "TC-12", "FI-04", sh11),
  "SH-12": ("Inattention reset by small inputs", "TC-25", "FI-19", sh12),
  "SH-13": ("Stays engaged above the ODD speed", "TC-20", "FI-16", sh13),
  "SH-14": ("Does not move over for a stopped patrol car", "TC-36", "FI-24", sh14),
}


def h_chip(sh, docs):
  h = docs.h[sh]
  hid = sf._ids(h, "H")
  head = hid[0] if h.startswith("H-") else ("new" if h.startswith("new") else "enabling")
  s, c = docs.data.sh[sh][1], docs.data.sh[sh][2]
  sc = f" · {s} {c}" if re.fullmatch(r"S\d", s) and re.fullmatch(r"C\d", c) else ""
  sc += " proposed" if sc and sh in docs.proposed else ""
  return f"{sh} · {head}{sc}"


def cards(docs: Docs | None = None, models: dict | None = None):
  docs = docs or load()
  models = MODELS if models is None else models
  shs = sorted(docs.data.sh)
  if missing := [s for s in shs if s not in models]:
    raise sf.FigureError(f"SOTIF scenes: no card model for {', '.join(missing)}")
  if extra := [s for s in models if s not in docs.data.sh]:
    raise sf.FigureError(f"SOTIF scenes: model for {', '.join(extra)}, which WP-C-05 §3 does not define")
  out = []
  for sh in shs:
    title, tc, fi, draw = models[sh]
    linked = [f for f, v in docs.data.fi.items() if sh in v[3]]
    if tc is None:
      if linked:
        raise sf.FigureError(f"{sh}: {', '.join(linked)} now link to it in WP-C-06 §3; give its card a §5 row")
      row, cls = None, ""
    else:
      if tc not in docs.data.tc:
        raise sf.FigureError(f"{sh}: {tc} is not defined in WP-C-06 §4")
      if fi not in docs.data.fi:
        raise sf.FigureError(f"{sh}: {fi} is not defined in WP-C-06 §3")
      if sh not in docs.data.fi[fi][3]:
        raise sf.FigureError(f"{sh}: {fi} does not link to {sh} in WP-C-06 §3")
      row = next((r for r in docs.rows if tc in r["tc"]), None)
      if row is None or fi not in row["fi"] or sh not in row["sh"]:
        raise sf.FigureError(f"{sh}: WP-C-06 §5 has no row {tc} -> {fi} -> {sh}")
      cls = docs.data.fi[fi][0]
    also = sorted({x for r in docs.rows if sh in r["sh"] for x in r["tc"]} - {tc})
    chart, scene = draw()
    out.append(dict(sh=sh, title=title, tc=tc, fi=fi, cls=cls, row=row, also=also, chart=chart, scene=scene,
                    hchip=h_chip(sh, docs), hazard=docs.data.sh[sh][0], docs=docs))
  return out


# ---------------------------------------------------------------- sheet

COLS, CW, GAP, M = 3, 400, 20, 40
PW = CW - 24
CH_H, SC_H = PW * 110 / 280, PW * 130 / 280
LW, FS = 86, 10                                  # row label width, row font size


def _rows(c):
  d = c["docs"]
  if c["row"] is None:
    return [("Triggering condition", "None in WP-C-06 §4-§5"),
            ("Insufficiency", f"No insufficiency links {c['sh']} in WP-C-06 §3"),
            ("System response", "Intended forwarding is unverified (AOU-04), WP-C-05 §3"),
            ("Evaluation", f"Not evaluated in WP-C-06. WP-C-05 §6: {d.measures.get(c['sh'], '—')}")]
  r = c["row"]
  fi = d.data.fi[c["fi"]]
  rows = [("Triggering condition", f"{c['tc']} {d.data.tc[c['tc']]}"),
          ("Insufficiency", f"{c['fi']} ({fi[0]}, {fi[1]}) {fi[2]}"),
          ("System response", r["resp"]),
          ("Evaluation", f"{r['ev']}. Action: {r['act']}")]
  if c["also"]:
    rows.append(("Also reached by", ", ".join(c["also"])))
  return rows


def _lines(s, width, max_lines=3):
  ls = wrap(s, width, FS)
  if len(ls) > max_lines:
    ls = ls[:max_lines]
    ls[-1] = sf._trunc(ls[-1] + " …", width, FS)
  return ls


def card_svg(x, y, c):
  b = [None]
  px, yy = x + 12, y + 26
  b.append(t(px, yy, c["sh"], 12, MUTED, 600))
  b.append(t(px + 44, yy, c["title"], 14.5, INK, 700))
  yy += 12
  out = c["row"]["out"] if c["row"] else "none"
  chips = [CLASS_CHIP[c["cls"]], ("#FEE2E2", "#7F1D1D", c["hchip"]), EV_CHIP[out]]
  cx = px
  for bg, fg, s in chips:
    w = hf.text_w(s, 10, True) + 14
    if cx + w > px + PW:
      cx, yy = px, yy + 22
    b.append(pill(cx, yy, s, bg, fg, 18, 10)[0])
    cx += w + 6
  yy += 26
  for ln in _lines(c["hazard"], PW, 2):
    b.append(t(px, yy + 8, ln, 10, MUTED))
    yy += 13
  yy += 6
  b.append(f'<svg x="{px}" y="{yy:.1f}" width="{PW}" height="{CH_H:.1f}" viewBox="0 0 280 110">'
           '<rect width="280" height="110" rx="6" fill="#F8FAFC"/>' + "".join(c["chart"]) + "</svg>")
  yy += CH_H + 6
  b.append(f'<svg x="{px}" y="{yy:.1f}" width="{PW}" height="{SC_H:.1f}" viewBox="0 0 280 130">'
           f'<clipPath id="s{c["sh"]}"><rect width="280" height="130" rx="6"/></clipPath>'
           f'<g clip-path="url(#s{c["sh"]})">' + "".join(c["scene"]) + "</g></svg>")
  yy += SC_H + 4
  for k, v in _rows(c):
    ls = _lines(v, PW - LW)
    kl = wrap(k, LW - 6, FS)
    for i in range(max(len(ls), len(kl))):
      yy += 13
      if i < len(kl):
        b.append(t(px, yy, kl[i], FS, MUTED))
      if i < len(ls):
        b.append(t(px + LW, yy, ls[i], FS, INK))
    yy += 3
  return b, yy + 12 - y


def legend(y):
  items = [(*sk.legend_swatch("req", 0, 0), "What the situation needs"), (*sk.legend_swatch("perf", 0, 0), "What the car does"),
           (f'<line x1="0" y1="-4" x2="26" y2="-4" stroke="{CB}" stroke-width="2" stroke-dasharray="3 3"/>', 32, "What the system believes (P)"),
           (f'<line x1="0" y1="-4" x2="26" y2="-4" stroke="{CL}" stroke-width="1.6" stroke-dasharray="3 3"/>', 32, "Specified limit (S)"),
           (*sk.legend_swatch("band", 0, 0), "Gap"), (*sk.legend_swatch("fault", 0, 0), "Triggering condition acts"),
           (*sk.legend_swatch("ring", 0, 0), "The moment it matters")]
  b, x = [], M
  for g, w, s in items:
    b.append(f'<g transform="translate({x} {y})">{g}</g>')
    x += w
    b.append(t(x, y, s, 11, INK))
    x += hf.text_w(s, 11) + 20
  return b


def sheet(docs: Docs | None = None) -> str:
  cs = cards(docs)
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  body = hf.header(w, "SOTIF scenes · one card per SOTIF hazard",
                   "Nothing fails: a triggering condition exposes an insufficiency of the intended function. Chart over the scene, seen from above.",
                   "WP-C-05 §3 · WP-C-06 §3-§5", "Schematic, not simulation output")
  body += legend(108)
  y, rows = 128, []
  for r in range(0, len(cs), COLS):
    built = [card_svg(M + k * (CW + GAP), y, c) for k, c in enumerate(cs[r:r + COLS])]
    row_h = max(h for _, h in built)
    for (b, _), k in zip(built, range(COLS)):
      b[0] = f'<rect x="{M + k * (CW + GAP)}" y="{y}" width="{CW}" height="{row_h:.0f}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>'
      rows += b
    y += row_h + GAP
  body += rows
  body.append(t(M, y + 6, "P: performance insufficiency, the blue layer is what the camera or radar believes. S: specification "
                "insufficiency, the chart sets the need against what the specification delivers. Each scene loops; the plant runs are in assurance/sim §3.7.",
                10.5, MUTED))
  body.append(t(w - M, y + 24, "Generated by sotif_scenes.py", 10, MUTED, None, "end"))
  desc = (f"{len(cs)} cards, one per SOTIF hazard of WP-C-05 §3. " +
          " ".join(f"{c['sh']} {c['title']}: " +
                   (f"{c['tc']} via {c['fi']} ({c['cls']}), {c['row']['ev']}." if c["row"] else "no WP-C-06 insufficiency yet.")
                   for c in cs))
  return svg_doc(w, int(y + 36), "SOTIF scenes: one card per SOTIF hazard (WP-C-05, WP-C-06)", desc, body)


def build() -> dict[str, str]:
  return {NAME: sheet()}


if __name__ == "__main__":
  sys.exit(sf.main(sys.argv[1:]))
