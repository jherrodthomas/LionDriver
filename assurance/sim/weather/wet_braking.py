#!/usr/bin/env python3
"""Stopping on a wet road (WP-C-06 TC-03, TC-33; WP-C-02 precipitation, DQ-414): does the road give the friction the
item's braking bound and a full stop need?

The item brakes at most at −3.5 m/s² (opendbc `ACCEL_MIN`, WP-C-02 F-02); on a level road that needs a peak
tyre-road friction of 0.36, on a 4 % downhill a little more. The friction the road gives comes from the Bosch
Automotive Handbook's table of peak friction against speed, water depth and tread (new, worn to 1.6 mm),
interpolated; the water depth in rain from the Gallaway film of the hydroplaning study (`hydroplaning.py`), at least
the table's 0.2 mm 'wet'. Stopping distances from the ODD speed follow at the item's rate and at the most the road
gives. Writes `../results/wet-braking.json` and `.md`.

    python3 wet_braking.py --figures
    python3 wet_braking.py --check

A handbook table of typical values, not this car's tyres. Synthetic (DSR-12), design aid, no evidence credit.
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
import hydroplaning as hp  # noqa: E402

SIM = HERE.parent
OPENDBC = SIM.parents[1] / "opendbc_repo" / "opendbc" / "car" / "interfaces.py"
OUT_JSON = SIM / "results" / "wet-braking.json"
OUT_MD = SIM / "results" / "wet-braking.md"
G = 9.81
TYRES = ("new", "worn_1_6mm")


def accel_min() -> float:
  return float(re.search(r"^ACCEL_MIN = (-?[\d.]+)", OPENDBC.read_text(encoding="utf-8"), re.M).group(1))


def mu(p: dict, tyre: str, v_kph, water_mm):
  """Peak friction, bilinear in speed and water depth over the Bosch table; held at its edges."""
  t = p["braking"]["friction_table"]
  sp, wd, tab = np.array(t["speeds_kph"]), np.array(t["water_mm"]), np.array(t[tyre])
  v = np.clip(np.asarray(v_kph, float), sp[0], sp[-1])
  w = np.clip(np.asarray(water_mm, float), wd[0], wd[-1])
  by_speed = np.array([np.interp(w, wd, tab[i]) for i in range(len(sp))])
  if by_speed.ndim == 1:
    return float(np.interp(v, sp, by_speed))
  return np.array([np.interp(vv, sp, by_speed[:, k]) for k, vv in enumerate(np.broadcast_to(v, w.shape).ravel())]
                  ).reshape(w.shape)


def need(a: float, grade_pct: float = 0.0) -> float:
  """Friction to brake at a (m/s², positive) on a downhill grade."""
  th = math.atan(grade_pct / 100)
  return (a + G * math.sin(th)) / (G * math.cos(th))


def stop_m(v_kph: float, a: float, reaction: float) -> float:
  v = v_kph / 3.6
  return v * reaction + v * v / (2 * a) if a > 0 else math.inf


def water(p: dict, rain_mm_h) -> np.ndarray:
  """Water depth on the worst drainage row of the hydroplaning study, at least the 'wet' floor."""
  w = p["water"]
  lanes, g = max(w["lanes_drained"]), max(w["grade_pct"])
  L, S = hp.path(lanes, w["lane_width_m"]["value"], w["cross_slope_pct"]["value"], g)
  f = hp.film_mm(rain_mm_h, L, S, w["texture_depth_mm"]["value"])
  return np.maximum(f, p["braking"]["wet_floor_mm"]["value"])


def run(p: dict) -> dict:
  b = p["braking"]
  a_item = -accel_min()
  odd = p["water"]["odd_speed_kph"]["value"]
  rain = b["rain_mm_h"]
  depth = water(p, rain)
  speeds = list(range(50, 131, 5))
  curves = {}
  for tyre in TYRES:
    curves[tyre] = {"dry": [round(mu(p, tyre, v, 0.0), 3) for v in speeds]}
    for r_, d in zip(rain, depth, strict=True):
      curves[tyre][f"{r_:g}"] = [round(mu(p, tyre, v, float(d)), 3) for v in speeds]
  conds = [("dry", 0.0)] + [(f"{r_:g}", float(d)) for r_, d in zip(rain, depth, strict=True)]
  stops = {}
  for tyre in TYRES:
    stops[tyre] = {}
    for name, d in conds:
      m = mu(p, tyre, odd, d)
      a_max = m * G
      a_used = min(a_item, a_max)
      stops[tyre][name] = {"water_mm": round(d, 3), "mu": round(m, 3), "a_max": round(a_max, 2),
                           "item_rate_available": a_max >= a_item,
                           "stop_item_m": round(stop_m(odd, a_used, b["reaction_s"]["value"]), 1),
                           "stop_full_m": round(stop_m(odd, a_max, 0.0), 1) if a_max > 0 else None}
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. Handbook friction table, not this car's tyres.",
          "item_decel": a_item, "need_level": round(need(a_item), 3),
          "need_downhill": round(need(a_item, b["grade_pct"]["value"]), 3), "odd_speed_kph": odd,
          "speeds_kph": speeds, "rain_mm_h": rain, "water_mm": [round(float(d), 3) for d in depth],
          "curves": curves, "at_odd_speed": stops,
          "nasa_kph": round(hp.nasa_mph(p["water"]["tyre_pressure_psi"]["value"]) * hp.MPH, 1)}


def markdown(r: dict, p: dict) -> str:
  b = p["braking"]
  s = r["at_odd_speed"]
  lab = {"dry": "Dry"}
  for rr, d in zip(r["rain_mm_h"], r["water_mm"], strict=True):
    lab[f"{rr:g}"] = f"Rain {rr:g} mm/h (water {d:.2f} mm)"
  L = [
    "# Stopping on a wet road: the friction the item's braking needs",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/wet_braking.py`](../weather/wet_braking.py) from [`params.yaml`](../weather/params.yaml); do not edit by "
    "hand. Friction from a handbook table of typical tyres (Bosch Automotive Handbook, 4th ed., p. 335, read from a "
    "reproduction), not this car's tyres; the water depth from the hydroplaning study's worst drainage row.",
    "",
    f"The item brakes at most at {r['item_decel']:.1f} m/s² (opendbc `ACCEL_MIN`). On a level road that needs a peak "
    f"friction of **{r['need_level']:.2f}**; on a {b['grade_pct']['value']:.0f} % downhill, {r['need_downhill']:.2f}.",
    "",
    f"## At the ODD speed, {r['odd_speed_kph']:.0f} km/h",
    "",
    "| Road | New tyres: peak friction, most braking | Item's −3.5 m/s² available? | Worn tyres (1.6 mm): peak friction, "
    "most braking | Item's rate available? | Stop at the item's rate (+0.5 s), new / worn |",
    "|---|---|---|---|---|---|",
  ]
  for k in s["new"]:
    n, w = s["new"][k], s["worn_1_6mm"][k]
    L.append(f"| {lab[k]} | {n['mu']:.2f}, {n['a_max']:.1f} m/s² | {'yes' if n['item_rate_available'] else '**no**'} | "
             f"{w['mu']:.2f}, {w['a_max']:.1f} m/s² | {'yes' if w['item_rate_available'] else '**no**'} | "
             f"{n['stop_item_m']:.0f} m / {w['stop_item_m']:.0f} m |")
  odd_rain = f"{r['rain_mm_h'][0]:g}"
  n0, w0 = s["new"][odd_rain], s["worn_1_6mm"][odd_rain]
  L += [
    "",
    "## What this shows (generated)",
    "",
    f"- **New tyres, light rain (the ODD's bound, {r['rain_mm_h'][0]:g} mm/h):** the road gives {n0['a_max']:.1f} m/s², "
    f"well above the item's {r['item_decel']:.1f} (friction {n0['mu']:.2f} against the {r['need_downhill']:.2f} a "
    f"{p['braking']['grade_pct']['value']:.0f} % downhill needs): with good tyres the item's braking is there inside the ODD.",
    f"- **Worn tyres (1.6 mm, the legal minimum), any rain:** the road gives about {w0['a_max']:.1f} m/s² at "
    f"{r['odd_speed_kph']:.0f} km/h, below the item's {r['item_decel']:.1f}. The item would ask for more than the "
    f"tyres hold, and a stop from {r['odd_speed_kph']:.0f} km/h takes {w0['stop_item_m']:.0f} m instead of "
    f"{n0['stop_item_m']:.0f} m. A line for the user information and the installation checks: tread depth, and the "
    "AOU that the car's tyres are in good condition.",
    f"- In heavier rain the water deepens and friction at speed falls quickly; by about 2 mm the table reaches the "
    f"hydroplaning region (NASA's {r['nasa_kph']:.0f} km/h at 35 psi): standing water and heavy rain stay outside the "
    "ODD (DQ-414).",
    "- TC-33 (a lead braking harder than −3.5 m/s²): on a wet road with good tyres the lead can still brake at "
    f"{n0['a_max']:.1f} m/s², so the gap the item's bound leaves is not closed by the rain.",
    "",
  ]
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
    print("wet braking:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["water_mm"],
        {t: {k: (v["mu"], v["stop_item_m"]) for k, v in d.items()} for t, d in r["at_odd_speed"].items()})
  if a.figures:
    import fig_weather
    fig_weather.braking_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
