#!/usr/bin/env python3
"""Draw a looping top view of each known scenario written as a file (../scenarios/xosc), from its esmini replay.

One SVG per scenario, fig-sim-ks-<nn>-anim.svg, in the style of fig_sim_he.py's animations (SMIL, no script): the
road straightened with the ego held in place and the lane dashes streaming at its speed, the other road users where
the replay puts them, a plot of the scenario's key quantity with a moving cursor, and the events lighting up as they
happen. Motion: replay.run() at the parameter defaults, sampled every STEP. Cars: Kenney Racing Pack sprites (CC0),
sized to the Dimensions in the xosc file; see assets/kenney-racing/SOURCES.md.

The ego only holds the speed its file gives it (the harness is meant to drive it), so in the scenarios with a slower
or stopped vehicle ahead it would drive through it: those loops end before the bodies overlap.

    python3 fig_sim_ks.py            # replay the scenarios in esmini and write the SVGs
    python3 fig_sim_ks.py --check    # fail if a committed SVG differs from a fresh replay
"""

from __future__ import annotations

import base64
import math
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
SCEN = SIM / "scenarios"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCEN))

import fig_sim_readme as fs  # noqa: E402  (style and SVG helpers)
from fig_sim_readme import T, el, fmt, para, W  # noqa: E402

SPRITES = Path(os.environ.get("KENNEY_RACING_DIR", HERE / "assets" / "kenney-racing"))
STEP = 0.1           # s between keyframes
HOLD = 1.5           # s held on the last frame before the loop restarts
LANE_W = 3.7
MIN_CAR_PX = 45.0    # shortest drawn car, so that it reads on a phone at 640 px
MIN_PANEL_PX = 110.0  # lowest road panel: the lateral scale is stretched to reach it
LABEL_W = 70.0       # room for the lane labels at the panel's left edge
EGO_LABEL_W = 34.0   # room for the "ego" label behind the ego
NAMES = {"stopped": "stopped car", "lead": "lead", "cutin": "cut-in car", "target": "car behind", "truck": "truck"}

# sprite per role: (file, hue rotation in degrees applied by an SVG filter, 0 for none)
EGO_SPRITE = ("car_red_1.png", 0)
OTHER_SPRITES = [("car_blue_1.png", 0), ("car_green_1.png", 0), ("car_yellow_1.png", 0)]
# without those colours (a partial copy of the pack), the red car hue-rotated: blue, green, yellow
HUE_FALLBACK = [216, 120, 60]


def other_sprite(i: int) -> tuple[str, int]:
  f, hue = OTHER_SPRITES[i % len(OTHER_SPRITES)]
  return (f, hue) if (SPRITES / f).exists() else (EGO_SPRITE[0], HUE_FALLBACK[i % len(HUE_FALLBACK)])


def sprite_problems() -> list[str]:
  """Each sprite this script draws must be listed in sources.yaml and match its SHA-256 there."""
  import hashlib
  import yaml
  man = SPRITES / "sources.yaml"
  if not man.exists():
    return [f"{man} missing"]
  files = yaml.safe_load(man.read_text(encoding="utf-8"))["files"]
  errs = []
  for f in sorted({EGO_SPRITE[0], *(f for f, _h in OTHER_SPRITES)}):
    p = SPRITES / f
    if f not in files:
      errs.append(f"{f} not listed in sources.yaml")
    elif not p.exists():
      errs.append(f"{f} missing")
    elif hashlib.sha256(p.read_bytes()).hexdigest() != files[f]["sha256"]:
      errs.append(f"{f} does not match its SHA-256 in sources.yaml")
  return errs


# ---------------------------------------------------------------- replay and geometry

def replay_rows(sc_id: str) -> dict[str, list[dict]]:
  import replay
  from fetch_esmini import esmini_bin
  return replay.run(esmini_bin(), sc_id, {})


def dims(sc_id: str) -> dict[str, tuple[float, float, float]]:
  """Entity name -> (length, width, centre x ahead of the reference point), from the xosc file."""
  root = ET.parse(SCEN / "xosc" / f"{sc_id}.xosc").getroot()
  out = {}
  for so in root.iter("ScenarioObject"):
    bb = so.find(".//BoundingBox")
    d, c = bb.find("Dimensions"), bb.find("Center")
    out[so.get("name")] = (float(d.get("length")), float(d.get("width")), float(c.get("x")))
  return out


def at(rows: list[dict], t: float) -> dict:
  """The recorded row nearest to t (esmini records every 50 ms; the frames are 100 ms apart)."""
  i = min(range(len(rows)), key=lambda k: abs(rows[k]["time"] - t))
  return rows[i]


def wrap_pi(a: float) -> float:
  return (a + math.pi) % (2 * math.pi) - math.pi


def bumper_gap(D, a: str, ra: dict, b: str, rb: dict) -> float:
  """Gap along the road from a's front bumper to b's rear bumper (b ahead), from the reference points and boxes."""
  la, _wa, ca = D[a]
  lb, _wb, cb = D[b]
  return (rb["s"] + cb - lb / 2) - (ra["s"] + ca + la / 2)


def first_time(frames, pred):
  return next((f for f in frames if pred(f)), None)


# ---------------------------------------------------------------- per-scenario content

def ks_spec(sc, R, D) -> dict:
  """Window, plot and events for one scenario, every value read from the replay rows R. view: metres of road shown,
  back: of those, metres behind the ego's reference point."""
  ego = R["ego"]
  sid = sc.id
  dur = ego[-1]["time"]
  g = lambda name: (lambda t: bumper_gap(D, "ego", at(ego, t), name, at(R[name], t)))  # noqa: E731
  allt = [round(STEP * k, 3) for k in range(int(dur / STEP) + 1)]
  if sid == "KS-01":
    r0 = sc.road["straight"] + sc.road["clothoid"]
    v = ego[0]["speed"]

    def ay(t):
      a, b = at(ego, max(0.0, t - 0.25)), at(ego, min(dur, t + 0.25))
      return v * wrap_pi(b["h"] - a["h"]) / max(b["time"] - a["time"], 1e-6)
    t_cl = first_time(allt, lambda t: at(ego, t)["s"] >= sc.road["straight"])
    t_arc = first_time(allt, lambda t: at(ego, t)["s"] >= r0)
    return dict(situation=f"Left curve R = {sc.road['radius']:g} m at {v * 3.6:.0f} km/h: the speed for 2.5 m/s² lateral acceleration",
                t0=max(0.0, t_cl - 2.0), t1=min(dur, t_arc + 4.0), view=70, back=12,
                plot=("LATERAL ACCELERATION OF THE EGO (m/s²)", ay, 0.0, 3.5, [(2.5, "2.5 m/s²: the parameter's v²/R", "thr")]),
                band=(t_cl, t_arc, "clothoid"),
                events=[(t_cl, "clothoid starts: curvature ramps up"), (t_arc, f"arc R = {sc.road['radius']:g} m starts"),
                        (t_arc + 1.0, f"steady {v * v / sc.road['radius']:.2f} m/s² (v²/R)")])
  if sid == "KS-05":
    gap = g("stopped")
    t1 = first_time(allt, lambda t: gap(t) < 4.0)
    t_100 = first_time(allt, lambda t: gap(t) < 100)
    t_50 = first_time(allt, lambda t: gap(t) < 50)
    v = ego[0]["speed"]
    return dict(situation=f"A stopped car in the ego lane, approached at {v * 3.6:.0f} km/h",
                t0=max(0.0, t1 - 8.0), t1=t1, view=110, back=8,
                plot=("GAP TO THE STOPPED CAR (m)", gap, 0.0, None, [(50.0, "50 m", "hairl")]),
                ends_before_overlap=True,
                events=[(t_100, "gap 100 m"), (t_50, f"gap 50 m: {50 / v:.1f} s to contact at this speed"),
                        (t1, "loop ends before contact")])
  if sid == "KS-06":
    tr = R["truck"]

    def clear(t):
      e, k = at(ego, t), at(tr, t)
      return abs(k["t"] - e["t"]) - (D["ego"][1] + D["truck"][1]) / 2
    return dict(situation="A truck alongside in the right lane; lanes 3.3 m wide",
                t0=0.0, t1=min(dur, 6.0), view=40, back=14, lane_w=sc.road.get("lane_width", LANE_W), still=True,
                dim=True,
                plot=None,
                events=[(0.0, f"truck alongside at the ego speed, {clear(0.0):.2f} m clear")])
  if sid == "KS-07":
    c = R["cutin"]
    gap = g("cutin")
    t1 = first_time(allt, lambda t: gap(t) < 4.0) or dur
    t_in = first_time(allt, lambda t: at(c, t)["laneId"] == -2)
    t_end_lc = first_time(allt, lambda t: t > 2.0 and at(c, t)["laneId"] == -2 and abs(at(c, t)["offset"]) < 0.05)
    t_10 = first_time(allt, lambda t: gap(t) < 10.0)
    return dict(situation="A car cuts in close from the left lane",
                t0=0.0, t1=t1, view=45, back=8,
                plot=("GAP TO THE CUT-IN CAR (m)", gap, 0.0, None, [(10.0, "10 m", "thr")]),
                band=(2.0, t_end_lc or 4.0, "lane change"), ends_before_overlap=True,
                events=[(2.0, f"cut-in starts, {gap(2.0):.1f} m ahead (bumper to bumper)"),
                        (t_in, "cut-in car crosses into the ego lane"), (t_10, "gap under 10 m"),
                        (t1, "loop ends before overlap")])
  if sid == "KS-08":
    ld = R["lead"]
    gap = g("lead")
    t1 = first_time(allt, lambda t: gap(t) < 4.0) or dur
    t_stop = first_time(allt, lambda t: t > 3.0 and at(ld, t)["speed"] == 0)
    return dict(situation=f"The lead brakes hard at {sc.params['LeadDecel'][0]:g} m/s² from a {sc.params['TimeGap'][0]:g} s gap",
                t0=0.0, t1=t1, view=60, back=8,
                plot=("GAP TO THE LEAD (m)", gap, 0.0, None, []), ends_before_overlap=True,
                events=[(3.0, f"lead brakes at {sc.params['LeadDecel'][0]:g} m/s²"),
                        *([(t_stop, "lead stops")] if t_stop and t_stop < t1 else []),
                        (t1, "loop ends before overlap")])
  if sid == "KS-09":
    ld = R["lead"]
    gap = g("stopped")
    start = next(r["time"] for r in ld if r["laneId"] != -2 or abs(r["offset"]) > 1e-3)
    t_out = first_time(allt, lambda t: t > start and at(ld, t)["laneId"] == -1)
    t1 = first_time(allt, lambda t: gap(t) < 4.0) or dur
    return dict(situation="The lead changes lane and reveals a stopped car",
                t0=max(0.0, start - 3.0), t1=t1, view=80, back=8,
                plot=("GAP TO THE STOPPED CAR (m)", gap, 0.0, None, []),
                band=(start, start + 2.0, "lead changes lane"), ends_before_overlap=True,
                events=[(start, f"lead starts its lane change, {sc.params['CutOutDistance'][0]:g} m short of the stopped car"),
                        (t_out, "lead leaves the ego lane: the stopped car is in the open"),
                        (t1, "loop ends before contact")])
  if sid == "KS-14":
    tg = R["target"]
    lat = lambda t: at(ego, t)["t"] + 1.5 * LANE_W  # noqa: E731  (0 at the centre of lane -2)
    t_in = first_time(allt, lambda t: at(ego, t)["laneId"] == -3)
    t_done = first_time(allt, lambda t: t > 3.0 and at(ego, t)["laneId"] == -3 and abs(at(ego, t)["offset"]) < 0.05)
    behind = (at(ego, 0)["s"] - at(tg, 0)["s"]) / ego[0]["speed"]
    return dict(situation=f"The driver changes lane to the right, a car {behind:.1f} s behind in the target lane",
                t0=0.0, t1=min(dur, (t_done or 7.0) + 2.0), view=100, back=80, lane_labels="right",
                plot=("EGO LATERAL POSITION FROM THE LANE -2 CENTRE (m)", lat, -4.5, 1.0, [(-LANE_W, "lane -3 centre", "hairl")]),
                band=(3.0, t_done or 7.0, "lane change"),
                footer="The ego's lane change is scripted in the file; in a closed loop the driver's nudge starts it.",
                events=[(3.0, "driver starts the lane change (scripted here)"), (t_in, "ego crosses into lane -3"),
                        (t_done, f"ego centred in lane -3, the car behind {behind:.1f} s back")])
  if sid == "KS-23":
    ld = R["lead"]
    spd = lambda t: at(ld, t)["speed"] * 3.6  # noqa: E731
    move = next(r["time"] for r in ld if r["speed"] > 0)
    return dict(situation="Stop-and-go: the lead stands, then moves off",
                t0=0.0, t1=min(dur, move + 6.0), view=40, back=8,
                plot=("LEAD SPEED (km/h)", spd, 0.0, None, []),
                events=[(0.0, "ego and lead stand, 8 m apart"), (move, "lead moves off at 1.5 m/s²")],
                footer="The ego stands: its file gives it speed 0; the item under test drives it in layer 1 and on the bench.")
  if sid == "KS-25":
    spd = lambda t: at(ego, t)["speed"] * 3.6  # noqa: E731
    t_x = first_time(allt, lambda t: spd(t) > 120)
    return dict(situation="The ego accelerates through the 120 km/h ODD bound",
                t0=0.0, t1=min(dur, (t_x or 10.0) + 3.0), view=60, back=10,
                plot=("EGO SPEED (km/h)", spd, 100.0, 135.0, [(120.0, "ODD bound 120 km/h", "thr", "left")]),
                events=[(1.0, "ego accelerates at 0.5 m/s² (scripted here)"), (t_x, "ego crosses 120 km/h")],
                footer="The ego's acceleration is scripted in the file; in a closed loop the item limits it.")
  if sid == "KS-27":
    ld, r = R["lead"], sc.road
    rp, rw = r["radius"] + LANE_W / 2, r["radius"] - r["wall"]["t"]
    arc0 = r["straight"] + r["clothoid"]
    gap = g("lead")

    def visible(t):
      e, l_ = at(ego, t), at(ld, t)
      if e["s"] < arc0:
        return False
      return rp * math.cos((l_["s"] - e["s"]) / r["radius"] / 2) >= rw
    t_rev = first_time(allt, visible)
    t1 = first_time(allt, lambda t: gap(t) < 4.0) or dur
    t_arc = first_time(allt, lambda t: at(ego, t)["s"] >= arc0)
    return dict(situation=f"A stopped lead hidden by a wall in a {r['radius']:g} m ramp curve while the ego accelerates",
                t0=max(0.0, t_rev - 6.0), t1=t1, view=80, back=8, lanes=1, wall=r["wall"]["t"],
                plot=("GAP TO THE LEAD, BUMPER TO BUMPER (m)", gap, 0.0, None, []),
                band=(0.0, t_rev, "hidden behind the wall"), hidden=("lead", t_rev), ends_before_overlap=True,
                events=[(t_arc, f"ego enters the {r['radius']:g} m arc, accelerating to the set speed"),
                        (t_rev, f"lead comes out from behind the wall, {gap(t_rev):.0f} m ahead (bumper to bumper)"),
                        (t1, "loop ends before contact")])
  raise ValueError(sid)


# ---------------------------------------------------------------- drawing

def sprite_defs(roles: list[tuple[str, int]]) -> tuple[str, dict]:
  """<defs> with one embedded PNG per sprite file and a hue filter per non-zero rotation; ids by role tuple."""
  out, ids, seen = [], {}, {}
  for f, hue in roles:
    if f not in seen:
      data = (SPRITES / f).read_bytes()
      from PIL import Image  # size only
      w, h = Image.open(SPRITES / f).size
      seen[f] = (f"spr{len(seen)}", w, h)
      out.append(f'<image id="{seen[f][0]}" width="{w}" height="{h}" '
                 f'href="data:image/png;base64,{base64.b64encode(data).decode()}"/>')
    if hue and f"hue{hue}" not in "".join(out):
      out.append(f'<filter id="hue{hue}"><feColorMatrix type="hueRotate" values="{hue}"/></filter>')
    ids[(f, hue)] = (*seen[f], hue)
  return "<defs>" + "".join(out) + "</defs>", ids


def car_use(sid_w_h_hue, length_px, width_px, extra="") -> str:
  sid, w, h, hue = sid_w_h_hue
  # sprites point up: rotate +90° so the front faces +x, then stretch to the box (length along x)
  sx, sy = width_px / w, length_px / h
  flt = f' filter="url(#hue{hue})"' if hue else ""
  return (f'<use href="#{sid}"{flt} transform="rotate(90) scale({sx:.4f},{sy:.4f}) translate({-w / 2},{-h / 2})"'
          f'{extra}/>')


def fig(sc, R, D) -> tuple[str, list[str]]:
  sp = ks_spec(sc, R, D)
  errs = []
  t0, t1 = sp["t0"], sp["t1"]
  frames = [round(t0 + STEP * k, 3) for k in range(int(round((t1 - t0) / STEP)) + 1)]
  span = frames[-1] - t0
  dur = span + HOLD
  kt = ";".join(f"{(f - t0) / dur:.4f}" for f in frames) + ";1"

  still = sp.get("still", False)

  def anim(attr, vals, typ=None, discrete=False):
    if still:
      return ""
    v = ";".join(vals) + ";" + vals[-1]
    cm = ' calcMode="discrete"' if discrete else ""
    if typ:
      return (f'<animateTransform attributeName="transform" type="{typ}" values="{v}" keyTimes="{kt}" '
              f'dur="{dur:.2f}s" repeatCount="indefinite"/>')
    return (f'<animate attributeName="{attr}" values="{v}" keyTimes="{kt}"{cm} dur="{dur:.2f}s" '
            f'repeatCount="indefinite"/>')

  ego = R["ego"]
  others = [n for n in R if n != "ego"]
  roles = [EGO_SPRITE] + [other_sprite(i) for i in range(len(others))]
  defs, ids = sprite_defs([r for r, n in zip(roles, ["ego"] + others) if n != "truck"])

  # header
  hl, hy = para(24, 34, f"{sc.id} · {sc.title}", W - 48, "h", lh=26)
  sl, sy = para(24, hy - 4, sp["situation"], W - 48, "t2", lh=17)   # para returns the next line's y
  b = [*hl, *sl, T(24, sy + 4, "Synthetic (DSR-12) · no evidence credit", "tbad"),
       T(24, sy + 23, f"esmini replay of {sc.id}.xosc at its defaults, " +
         f"{t0:.1f}–{t1:.1f} s", "t2b"),
       el("line", None, x1=24, y1=sy + 34, x2=W - 24, y2=sy + 34, class_="hair")]

  # road panel: s along x (ego held in place), t along y (reference line at the top, lanes below). Cars shorter than
  # MIN_CAR_PX at this scale are drawn at MIN_CAR_PX, wider in proportion, and the panel note says so.
  lanes = sp.get("lanes", 3)
  lw = sp.get("lane_w", LANE_W)
  px = (W - 48) / sp["view"]
  grow = max(1.0, MIN_CAR_PX / (D["ego"][0] * px))
  label_right = sp.get("lane_labels") == "right"
  # keep the ego's rear clear of the lane labels on the left
  x_ego = 24 + sp["back"] * px
  if not label_right:
    x_ego = max(x_ego, 24 + LABEL_W + EGO_LABEL_W + D["ego"][0] * px * grow / 2 - D["ego"][2] * px)
  ry = sy + 46
  wall = sp.get("wall")
  margin = 14.0
  wall_m = (wall + 1.0) if wall is not None else 0.0
  # lateral scale: true unless the panel would be lower than MIN_PANEL_PX
  lat = max(1.0, (MIN_PANEL_PX - 2 * margin - (16 if wall is not None else 0)) / ((lanes * lw + wall_m) * px))
  lat = math.ceil(lat * 2) / 2
  py_m = px * lat
  top_extra = wall_m * py_m + 16 if wall is not None else 0
  road_h = lanes * lw * py_m
  rh = road_h + 2 * margin + top_extra
  y_ref = ry + margin + top_extra

  def X(s_rel):
    return x_ego + s_rel * px

  def Y(tl):
    return y_ref - tl * py_m
  b += [f'<clipPath id="road"><rect x="24" y="{fmt(ry)}" width="{W - 48}" height="{fmt(rh)}" rx="8"/></clipPath>',
        el("rect", None, x=24, y=fmt(ry), width=W - 48, height=fmt(rh), rx=8, class_="card"),
        el("rect", None, x=24, y=fmt(Y(0)), width=W - 48, height=fmt(road_h), class_="asph")]
  ds = [at(ego, f)["s"] for f in frames]
  dash, gap_ = 3.0 * px, 9.0 * px
  for k in range(lanes + 1):
    yl = Y(-k * lw)
    if k in (0, lanes):
      b += [el("line", None, x1=24, y1=fmt(yl), x2=W - 24, y2=fmt(yl), class_="edge")]
    else:
      offs = [fmt((s - ds[0]) * px) for s in ds]
      b += [el("line", None, x1=24, y1=fmt(yl), x2=W - 24, y2=fmt(yl), class_="laned",
               stroke_dasharray=f"{fmt(dash)} {fmt(gap_)}").replace("/>", ">" + anim("stroke-dashoffset", offs) + "</line>")]
  ego_lane = ego[0]["laneId"]
  for k in range(lanes):
    lid = -(k + 1)
    txt, cls = ("ego lane", "t2b") if lid == ego_lane else (f"lane {lid}", "t2")
    yl = Y(-(k + 0.5) * lw) + 4
    b += [T(W - 30, yl, txt, cls, "end") if label_right else T(30, yl, txt, cls)]
  if wall is not None:
    wy = Y(wall)
    b += [el("rect", None, x=24, y=fmt(wy - 4), width=W - 48, height=4, class_="wall"),
          T(30, wy - 8, "wall on the inside of the curve, 2 m high", "t2")]
  b += ['<g clip-path="url(#road)">']
  markers = []
  for name, role in zip(["ego"] + others, roles):
    rows = R[name]
    L, Wd, cx = D[name]
    pos, rot, off = [], [], []
    g = grow if name != "truck" else max(1.0, MIN_CAR_PX / (L * px))
    for i, f in enumerate(frames):
      r = at(rows, f)
      xc = X(r["s"] + cx - ds[i])
      pos.append(f"{fmt(xc)},{fmt(Y(r['t']))}")
      off.append(">" if xc - L * px * g / 2 > W - 24 else "<" if xc + L * px * g / 2 < 24 else "")
      a, c = at(rows, max(0.0, f - 0.2)), at(rows, f + 0.2)
      dsr, dtr = c["s"] - a["s"], c["t"] - a["t"]
      rot.append(f"{-math.degrees(math.atan2(dtr, dsr)) if abs(dsr) > 0.05 else 0.0:.2f}")
    turning = any(abs(float(x)) > 0.2 for x in rot)
    if name == "truck":
      tl, tw = L * px * g, Wd * px * g
      body = (el("rect", None, x=fmt(-tl / 2 + 1), y=fmt(-tw / 2 + 1), width=fmt(tl), height=fmt(tw), rx=3, class_="shadow")
              + el("rect", None, x=fmt(-tl / 2), y=fmt(-tw / 2), width=fmt(tl), height=fmt(tw), rx=3, class_="truck")
              + el("line", None, x1=fmt(tl / 2 - 2.0 * px * g), y1=fmt(-tw / 2), x2=fmt(tl / 2 - 2.0 * px * g),
                   y2=fmt(tw / 2), class_="cab") + T(0, 4, "truck", "t2", "middle"))
    else:
      body = car_use(ids[role], L * px * g, 2.0 * px * g)
    if name == "ego":
      body += T(-L * px * g / 2 - 6, 4, "ego", "t2b", "end")
    inner = f"<g>{anim(None, rot, 'rotate')}{body}</g>" if turning else body
    hid = sp.get("hidden")
    if hid and hid[0] == name and not still:
      k0 = max(0.0, (hid[1] - t0) / dur)
      b += [f'<g opacity="0.3"><animate attributeName="opacity" values="0.3;1" keyTimes="0;{k0:.4f}" calcMode="discrete" '
            f'dur="{dur:.2f}s" repeatCount="indefinite"/>']
    else:
      b += ["<g>"]
    b += [f'<g transform="translate({pos[0].replace(",", " ")})">{anim(None, pos, "translate")}{inner}</g>', "</g>"]
    # an edge marker while the car is off the panel: "lead ahead →" at the right edge, "← car behind" at the left
    for side in "<>":
      if name != "ego" and any(o == side for o in off):
        lab = NAMES.get(name, name)
        ym = Y(at(rows, frames[[o == side for o in off].index(True)])["t"]) + 4
        txt = f"{lab} ahead →" if side == ">" else f"← {lab}"
        vis = ["1" if o == side else "0" for o in off]
        markers += [f'<g opacity="{vis[0]}">{anim("opacity", vis, discrete=True)}' +
                    (T(W - 32, ym, txt, "mark", "end") if side == ">" else T(32 + (LABEL_W if not label_right else 0), ym, txt, "mark")) +
                    "</g>"]
  b += ["</g>", *markers]
  if sp.get("dim"):
    e0, k0 = at(ego, t0), at(R["truck"], t0)
    xd = X(at(ego, t0)["s"] - ds[0] + D["ego"][2])
    y1, y2 = Y(e0["t"] - D["ego"][1] / 2), Y(k0["t"] + D["truck"][1] / 2)
    clear = abs(e0["t"] - k0["t"]) - (D["ego"][1] + D["truck"][1]) / 2
    b += [el("line", None, x1=fmt(xd), y1=fmt(y1), x2=fmt(xd), y2=fmt(y2), class_="dim"),
          el("line", None, x1=fmt(xd - 5), y1=fmt(y1), x2=fmt(xd + 5), y2=fmt(y1), class_="dim"),
          el("line", None, x1=fmt(xd - 5), y1=fmt(y2), x2=fmt(xd + 5), y2=fmt(y2), class_="dim"),
          T(xd + 8, (y1 + y2) / 2 + 4, f"{clear:.2f} m", "mark")]
  note = "road straightened, ego held in place" + ("" if still else "; dashes stream at its speed")
  if grow > 1.01:
    note += "; cars larger than scale"
  if lat > 1.0:
    note += f"; lateral ×{lat:g}"
  if sp.get("hidden"):
    note = ("road straightened; faded car: hidden behind the wall" + ("; cars larger than scale" if grow > 1.01 else "")
            + (f"; lateral ×{lat:g}" if lat > 1.0 else ""))
  nl, ny = para(36, ry + rh + 16, note, W - 60, "t2", lh=15)
  b += nl
  rh += ny - (ry + rh + 16) - 15   # later rows move down by the note's extra lines

  # plot (none for a still with a dimension line)
  y_after = ry + rh + 40
  if sp.get("plot"):
    title, fn, lo, hi, lines_ = sp["plot"]
    vals = [fn(f) for f in frames]
    lo = min(lo, min(vals)) if lo is not None else min(vals)
    hi = hi if hi is not None else max(vals) * 1.08
    hi = max(hi, max(vals))
    if hi - lo < 1e-6:
      hi = lo + 1.0
    py = ry + rh + 46
    ph = 130
    px0, px1 = 64, W - 32

    def TX(tt):
      return px0 + (tt - t0) / span * (px1 - px0)

    def DY(v):
      return py + (hi - v) / (hi - lo) * ph
    b += [T(24, py - 8, title, "t2b")]
    if sp.get("band"):
      a0, a1, lab = sp["band"]
      a0, a1 = max(a0, t0), min(a1, frames[-1])
      if a1 > a0:
        b += [el("rect", None, x=fmt(TX(a0)), y=fmt(py), width=fmt(TX(a1) - TX(a0)), height=ph, class_="band"),
              T(TX(a0) + 4, py + 14, lab, "t2")]
    step_v = nice_step(hi - lo)
    v = math.ceil(lo / step_v) * step_v
    while v <= hi + 1e-9:
      b += [el("line", None, x1=px0, y1=fmt(DY(v)), x2=px1, y2=fmt(DY(v)), class_="hair"),
            T(px0 - 6, DY(v) + 4, f"{v:g}", "t2", "end")]
      v += step_v
    tg = math.ceil(t0)
    while tg <= frames[-1] + 1e-9:
      b += [T(TX(tg), py + ph + 16, f"{tg:g}", "t2", "middle")]
      tg += 1 if span <= 12 else 2
    b += [T(px1, py + ph + 30, "time (s)", "t2", "end")]
    for yv, lab, cls, *left in lines_:
      if lo <= yv <= hi:
        b += [el("line", None, x1=px0, y1=fmt(DY(yv)), x2=px1, y2=fmt(DY(yv)), class_=cls),
              T(px0 + 6, DY(yv) - 4, lab, "t2") if left else T(px1, DY(yv) - 4, lab, "t2", "end")]
    b += [el("path", None, d="M" + " L".join(f"{fmt(TX(f))},{fmt(DY(v))}" for f, v in zip(frames, vals)), class_="trace")]
    cur = [f"{fmt(TX(f) - px0)},0" for f in frames]
    if not still:
      b += [f'<g>{anim(None, cur, "translate")}<line x1="{px0}" y1="{fmt(py)}" x2="{px0}" y2="{fmt(py + ph)}" class="cursor"/></g>']

    y_after = py + ph + 52
  # events
  ev = sorted((te, lab) for te, lab in sp["events"] if te is not None)
  if not still and not any(abs(te - t1) < 1e-6 for te, _l in ev):
    ev.append((t1, "loop ends"))
  for te, lab in sp["events"]:
    if te is None:
      errs.append(f"{sc.id}: event '{lab}' did not happen in the replay")
  y = y_after
  b += [T(24, y - 6, "EVENTS" if still else "EVENTS (light up as they happen)", "t2b")]
  y += 14
  for te, lab in ev:
    k0 = min(1.0, max(0.0, (te - t0) / dur))
    row = T(24, y, f"{te:.1f} s", "tb") + T(84, y, lab, "t")
    b += [f"<g>{row}</g>" if still else
          f'<g opacity="0.25"><animate attributeName="opacity" values="0.25;1" keyTimes="0;{k0:.4f}" '
          f'calcMode="discrete" dur="{dur:.2f}s" repeatCount="indefinite"/>{row}</g>']
    y += 22
  foot = ("Layer 2 fixes the road and the other road users. " +
          sp.get("footer", "The ego only holds its start speed here; the item under test drives it in layer 1 and on "
                           "the bench" + (", so the loop ends before the bodies overlap." if sp.get("ends_before_overlap")
                                          else ".")) + " Cars: Kenney Racing Pack (CC0).")
  fl, fy = para(24, y + 10, foot, W - 48, "t2", lh=16)
  b += fl
  y = fy + 10
  style = ("<style>.laned { stroke:var(--ink3); stroke-width:2; } .edge { stroke:var(--ink2); stroke-width:2; } "
           ".asph { fill:var(--grid); } .wall { fill:var(--ink2); } .truck { fill:var(--ink3); stroke:var(--ink); "
           "stroke-width:1; } .shadow { fill:var(--ink); opacity:0.45; } .cab { stroke:var(--ink); stroke-width:1; } "
           ".mark { fill:var(--amb); font:600 12px system-ui, sans-serif; } .dim { stroke:var(--amb); stroke-width:1.4; } .trace { fill:none; stroke:var(--real); stroke-width:2.2; } .thr { stroke:var(--bad); "
           "stroke-width:1.3; stroke-dasharray:6 4; } .hairl { stroke:var(--ink3); stroke-width:1; stroke-dasharray:3 3; } "
           ".band { fill:var(--amb-bg); } .cursor { stroke:var(--ink); stroke-width:1.6; }</style>")
  desc = (f"Synthetic (DSR-12), no evidence credit. {'Still' if still else 'Looping'} top view of {sc.id} ({sc.title}) from its esmini replay at the "
          f"parameter defaults, {t0:.1f} to {t1:.1f} s: {sp['situation']}. " +
          (f"Plot: {sp['plot'][0].lower()}. " if sp.get("plot") else "") + "Events: " +
          "; ".join(f"{lab} at {te:.1f} s" for te, lab in ev) + f". {foot}")
  out = fs.svg(int(y + 6), f"{sc.id} animated top view", desc, b)
  out = out.replace("</style>", "</style>" + style, 1).replace("<defs>", defs[:-7], 1)
  return out, errs


def nice_step(rng: float) -> float:
  for s in (0.5, 1, 2, 5, 10, 20, 25, 50, 100):
    if rng / s <= 6:
      return s
  return 200


# ---------------------------------------------------------------- build and check

def slug(sc_id: str) -> str:
  return "ks-" + sc_id[3:].lower()


def build() -> tuple[dict[str, str], list[str]]:
  import generate
  out, errs = {}, []
  for sc in generate.SCENARIOS:
    R = replay_rows(sc.id)
    svg, e = fig(sc, R, dims(sc.id))
    out[f"fig-sim-{slug(sc.id)}-anim.svg"] = svg
    errs += e
  return out, errs


def main(argv: list[str]) -> int:
  out, errs = build()
  errs = sprite_problems() + errs
  if "--check" in argv:
    errs += [f"{n} is stale; run fig_sim_ks.py" for n, c in out.items()
             if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for e in errs:
      print(f"error: {e}", file=sys.stderr)
    if not errs:
      print(f"fig_sim_ks: {len(out)} figures current")
    return 1 if errs else 0
  for n, c in out.items():
    (HERE / n).write_text(c, encoding="utf-8")
  for e in errs:
    print(f"warning: {e}", file=sys.stderr)
  print(f"wrote {len(out)} figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
