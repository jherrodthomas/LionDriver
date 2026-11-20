#!/usr/bin/env python3
"""A lead hidden on the inside of a curve (physics plan round 4, study 23; WP-C-06 TC-35, TC-14).

The ODD's curve bound is R = v² / 2.5 m/s² (WP-C-02 §3.2). Two questions on that curve, our car in the lane next to
the inside shoulder:
- **A lead at the follow gap.** openpilot keeps v·T_FOLLOW + STOP_DISTANCE behind a lead at the same speed
  (`long_mpc.py`, read and pinned here). On the arc the lead is off our heading by half the angle the gap subtends.
  That angle is set against the road camera's frame and the driving model's two input frames (narrow and wide).
- **A stopped car round the bend.** The line of sight to a car ahead in our lane is a chord of the lane's arc and
  bows toward the inside by up to R (1 − cos(s / 2R)) (AASHTO's horizontal sightline offset). A wall or cutting on the
  inside edge of the shoulder hides the car once the chord crosses it; a barrier only where the sight line passes
  below its top. The longest sight distance is set against the item's and a driver's stop.
Writes `../results/curve-sight.json` and `.md`.

    python3 curve_sight.py --figures
    python3 curve_sight.py --check

The item does not brake for a stopped car it has not taken as a lead (WP-C-02 F-02). Synthetic (DSR-12), design aid,
no evidence credit (DQ-413).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stopped_car as sc  # noqa: E402
import sun_glare as sg  # noqa: E402
import wet_braking as wb  # noqa: E402
import wet_curves as wc  # noqa: E402

SIM = HERE.parent
ROOT = SIM.parents[1]
MPC = ROOT / "openpilot" / "selfdrive" / "controls" / "lib" / "longitudinal_mpc_lib" / "long_mpc.py"
OUT_JSON = SIM / "results" / "curve-sight.json"
OUT_MD = SIM / "results" / "curve-sight.md"


def mpc_code() -> dict:
  """openpilot's follow gaps per personality and its stop distance; stops if they moved."""
  src = MPC.read_text(encoding="utf-8")
  def num(pat):
    m = re.search(pat, src, re.M)
    if not m:
      raise SystemExit(f"long_mpc.py changed: {pat!r} not found; review curve_sight.py")
    return float(m.group(1))
  for pat in (r"return \(v_ego\*\*2\) / \(2 \* COMFORT_BRAKE\) \+ t_follow \* v_ego \+ STOP_DISTANCE",
              r"return \(v_lead\*\*2\) / \(2 \* COMFORT_BRAKE\)"):
    if not re.search(pat, src):
      raise SystemExit(f"long_mpc.py changed: {pat!r} not found; review curve_sight.py")
  fn = re.search(r"^def get_T_FOLLOW\(.*?(?=^def )", src, re.M | re.S)
  if not fn:
    raise SystemExit("long_mpc.py changed: get_T_FOLLOW not found; review curve_sight.py")
  def tf(name):
    g = re.search(rf"LongitudinalPersonality\.{name}:\n    return ([\d.]+)", fn.group(0))
    if not g:
      raise SystemExit(f"long_mpc.py changed: get_T_FOLLOW {name} not found; review curve_sight.py")
    return float(g.group(1))
  return {"stop_distance_m": num(r"^STOP_DISTANCE = ([\d.]+)"), "comfort_brake": num(r"^COMFORT_BRAKE = ([\d.]+)"),
          "t_follow_s": {k: tf(k) for k in ("relaxed", "standard", "aggressive")}}


def gap(m: dict, v: float, t: float) -> float:
  """Steady gap behind a lead at our speed: our safe distance less the lead's, as the planner's cost has it."""
  return (v * v / (2 * m["comfort_brake"]) + t * v + m["stop_distance_m"]) - v * v / (2 * m["comfort_brake"])


def bearing_deg(s: float, R: float) -> float:
  """Angle off our heading of a point s ahead along an arc of radius R: half the arc's angle."""
  return math.degrees(s / (2 * R))


def offset(s: float, R: float) -> float:
  """AASHTO's horizontal sightline offset: how far the chord of an arc s long bows from the arc, R (1 − cos(s/2R))."""
  return R * (1 - math.cos(s / (2 * R)))


def sight(R: float, m: float, h_cam: float, h_obj: float, h_obs: float) -> float:
  """Longest s along our lane's arc (radius R) at which the line from the camera (h_cam) to a point h_obj high on a car
  ahead clears an obstruction h_obs tall standing m inside the lane's centre line. The chord crosses the obstruction's
  line at two symmetric points; the sight line's height there decides. Bisection on s."""
  def clear(s):
    if offset(s, R) <= m:
      return True
    phi = s / R                                   # the arc's angle
    # points on the chord: from P0 = (R, 0) to P1 = (R cos phi, R sin phi); distance from the centre r(f)
    f = np.linspace(0.0, 1.0, 2001)
    x = R + f * (R * math.cos(phi) - R)
    y = f * R * math.sin(phi)
    r = np.hypot(x, y)
    inside = (R - r) > m                          # beyond the obstruction's line, toward the centre
    h_line = h_cam + f * (h_obj - h_cam)
    return not np.any(inside & (h_line < h_obs))
  lo, hi = 1.0, math.pi * R
  if clear(hi):
    return math.inf
  for _ in range(60):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if clear(mid) else (lo, mid)
  return lo


def fin(x: float) -> float | None:
  """A sight distance for the JSON: None when nothing on the arc blocks it."""
  return None if x == math.inf else round(x, 1)


def run(p: dict) -> dict:
  cs = p["curve_sight"]
  m = mpc_code()
  fov = sg.camera_fov()
  st = sc.code()
  half = {"camera": fov["hfov_deg"] / 2,
          "model_narrow": math.degrees(math.atan(st["model_input_px"][0] / 2 / st["narrow_fl_px"])),
          "model_wide": math.degrees(math.atan(st["model_input_px"][0] / 2 / st["wide_fl_px"]))}
  a_lat = p["curves"]["lateral_odd"]["value"]
  a_item = -wb.accel_min()
  t_item = p["braking"]["reaction_s"]["value"]
  t_drv = p["stopped_car"]["driver_reaction_s"]["value"]
  depth = float(wb.water(p, [p["curves"]["rain_mm_h"]["value"]])[0])
  offsets = [cs["lane_width_m"]["value"] / 2 + w for w in cs["inside_shoulder_m"]["value"]]
  hc = cs["camera_height_m"]["value"]
  tg = p["crest"]["targets_m"]
  rows = []
  for vk in cs["speeds_kph"]:
    v = vk / 3.6
    R = v * v / a_lat
    leads = {}
    for name, t in m["t_follow_s"].items():
      s = gap(m, v, t)
      leads[name] = {"gap_m": round(s, 1), "bearing_deg": round(bearing_deg(s, R), 2)}
    # the item's stop in the curve: its braking on top of the curve's lateral load is the wet-curve study's case;
    # here the straight-line stop distance, which the sight distance has to cover
    need = {"item": wb.stop_m(vk, a_item, t_item),
            "driver_dry": wb.stop_m(vk, wb.mu(p, "new", vk, 0.0) * 9.81, t_drv),
            "driver_wet_3mm": wb.stop_m(vk, wc.mu_odd(p, vk, depth) * 9.81, t_drv)}
    sights = {}
    for i, mo in enumerate(offsets):
      for obs, h in cs["obstruction_heights_m"].items():
        if obs in ("status", "source"):
          continue
        sights[f"{obs}_{i}"] = {"offset_m": round(mo, 2), "obstruction": obs, "height_m": h,
                                "tail_lights_m": fin(sight(R, mo, hc, tg["tail_lights"], h)),
                                "roof_m": fin(sight(R, mo, hc, tg["roof"], h))}
    rows.append({"speed_kph": vk, "radius_m": round(R, 1), "leads": leads,
                 "need_m": {k: round(x, 1) for k, x in need.items()}, "sight": sights})
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. Arc geometry on the ODD's curve bound; "
                   "openpilot's follow gaps; Interstate shoulders and barrier heights.",
          "mpc": m, "half_angle_deg": {k: round(x, 2) for k, x in half.items()}, "offsets_m": [round(x, 2) for x in offsets],
          "camera_height_m": hc, "rows": rows}


def markdown(r: dict, p: dict) -> str:
  h = r["half_angle_deg"]
  m = r["mpc"]
  rows = r["rows"]
  o = r["offsets_m"]
  L = [
    "# A lead hidden on the inside of a curve",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/curve_sight.py`](../weather/curve_sight.py) with openpilot's follow gaps read and pinned from "
    "`long_mpc.py` and the model's input frames from `model.py`; do not edit by hand. The curve is the ODD's bound, "
    "R = v² / 2.5 m/s² (WP-C-02 §3.2); our car is in the lane next to the inside shoulder.",
    "",
    "## A lead at the follow gap",
    "",
    f"openpilot follows at v·T + {m['stop_distance_m']:.0f} m (T = {m['t_follow_s']['aggressive']:g}, "
    f"{m['t_follow_s']['standard']:g} and {m['t_follow_s']['relaxed']:g} s by personality). On the arc the lead is off "
    f"our heading by half the angle the gap subtends. The road camera sees ±{h['camera']:.0f}°; the model's narrow "
    f"input ±{h['model_narrow']:.1f}°, its wide input ±{h['model_wide']:.1f}°.",
    "",
    "| Speed | Curve radius | Gap (standard) | Lead off our heading: aggressive / standard / relaxed |",
    "|---|---|---|---|",
  ]
  for x in rows:
    ld = x["leads"]
    L.append(f"| {x['speed_kph']} km/h | {x['radius_m']:.0f} m | {ld['standard']['gap_m']:.0f} m | "
             f"{ld['aggressive']['bearing_deg']:.1f}° / {ld['standard']['bearing_deg']:.1f}° / {ld['relaxed']['bearing_deg']:.1f}° |")
  L += ["", "## A stopped car round the bend", "",
        f"The longest distance at which the camera ({r['camera_height_m']:.1f} m up) sees a stopped car ahead in our lane, "
        f"past an obstruction on the inside edge of a {p['curve_sight']['inside_shoulder_m']['value'][0]:.1f} m shoulder "
        f"({o[0]:.1f} m from our lane's centre) or a {p['curve_sight']['inside_shoulder_m']['value'][1]:.1f} m one "
        f"({o[1]:.1f} m): to its tail lights (0.6 m) and its roof (1.43 m).", "",
        "| Speed | Item stops in | Driver stops in (wet, 3 mm) | Wall or cutting: narrow / wide shoulder | "
        "1.07 m barrier, to the tail lights | 0.81 m barrier, to the tail lights |",
        "|---|---|---|---|---|---|"]
  def fm(x):
    return "clear" if x is None else f"{x:.0f} m"
  for x in rows:
    s = x["sight"]
    L.append(f"| {x['speed_kph']} km/h | {x['need_m']['item']:.0f} m | {x['need_m']['driver_wet_3mm']:.0f} m | "
             f"{fm(s['wall_0']['tail_lights_m'])} / {fm(s['wall_1']['tail_lights_m'])} | "
             f"{fm(s['tall_barrier_0']['tail_lights_m'])} / {fm(s['tall_barrier_1']['tail_lights_m'])} | "
             f"{fm(s['barrier_0']['tail_lights_m'])} / {fm(s['barrier_1']['tail_lights_m'])} |")
  inside = [x for x in rows if x["speed_kph"] <= 110]
  worst = max((x["leads"]["relaxed"]["bearing_deg"], x["speed_kph"]) for x in inside)
  beyond = [x["speed_kph"] for x in inside if x["leads"]["relaxed"]["bearing_deg"] > h["model_narrow"]]
  r110 = next(x for x in rows if x["speed_kph"] == 110)
  short = [x["speed_kph"] for x in inside if x["sight"]["wall_1"]["tail_lights_m"] < x["need_m"]["item"]]
  L += ["", "## What this shows (generated)", "",
        f"- **A lead at the follow gap stays in the road camera's frame** on every ODD curve: at most {worst[0]:.1f}° off "
        f"our heading (relaxed, {worst[1]} km/h), inside ±{h['camera']:.0f}°. " +
        (f"At {', '.join(map(str, beyond))} km/h on a relaxed gap it is beyond the model's narrow input "
         f"(±{h['model_narrow']:.1f}°) and only in its wide one."
         if beyond else f"It is inside the model's narrow input (±{h['model_narrow']:.1f}°) too."),
        f"- **A wall or cutting on the inside hides a stopped car well inside the item's stop.** At 110 km/h on the "
        f"ODD's {r110['radius_m']:.0f} m curve the camera sees its tail lights from "
        f"{r110['sight']['wall_0']['tail_lights_m']:.0f} m (narrow shoulder) or "
        f"{r110['sight']['wall_1']['tail_lights_m']:.0f} m (wide), against {r110['need_m']['item']:.0f} m for the item and "
        f"{r110['need_m']['driver_wet_3mm']:.0f} m for a driver in the wet. "
        + (f"Even with the wide shoulder the sight falls short of the item's stop at {', '.join(map(str, short))} km/h."
           if short else ""),
        (f"- **A safety-shape barrier hides the lower part of the car, not all of it.** The sight line to the tail "
         f"lights meets the barrier near the stopped car, where it is already down near their height: at 110 km/h a "
         f"0.81 m barrier hides them beyond {r110['sight']['barrier_0']['tail_lights_m']:.0f}–"
         f"{r110['sight']['barrier_1']['tail_lights_m']:.0f} m, a 1.07 m one beyond "
         f"{r110['sight']['tall_barrier_0']['tail_lights_m']:.0f}–{r110['sight']['tall_barrier_1']['tail_lights_m']:.0f} m. "
         "The roof stays in view over either at any distance, so the model sees the top of the car only."
         if all(x["sight"][k]["roof_m"] is None for x in inside for k in ("barrier_0", "tall_barrier_0")) else
         f"- **A safety-shape barrier hides the tail lights** at 110 km/h beyond "
         f"{r110['sight']['barrier_0']['tail_lights_m']:.0f} m (0.81 m) and "
         f"{r110['sight']['tall_barrier_0']['tail_lights_m']:.0f} m (1.07 m), and the roof beyond "
         f"{fm(r110['sight']['tall_barrier_0']['roof_m'])}."),
        "- So TC-35's late detection comes from what stands on the inside of the curve, not from the camera's frame. The "
        "ODD's curve bound alone does not leave a stopped car in view at the item's stopping distance where a wall, "
        "cutting, hedge or glare screen lines the inside. For KS tests in curves: a stopped car beyond a walled or cut "
        "inside edge.",
        ""]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r, p)
  if a.check:
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("curve sight:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name)
  if a.figures:
    import fig_weather
    fig_weather.curve_sight_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
