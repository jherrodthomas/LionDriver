#!/usr/bin/env python3
"""Grades and sag curves (physics plan round 4, study 22; WP-C-06 TC-16, TC-17; WP-C-02 §3.1 grade, OI-5).

Two parts.
- **Grades.** The ODD admits downhills up to 6 %. openpilot's Toyota controller asks the PCM for the car's own
  acceleration, clipped to −3.5 m/s²; the grade enters only as a short high-pass compensation of at most 1.5 m/s²
  and in the brake-permit logic (read from `carcontroller.py` and pinned here). So on a downhill the PCM has to brake
  harder at the wheels to hold −3.5: the tyres need (3.5 + g sin θ) / (g cos θ) of friction. That is set against
  the friction the wet-braking and wet-curve studies give, dry and wet, new tyres and the ODD's 3 mm. A driver's full
  stop is longer by the same gravity.
- **Sag curves.** AASHTO builds a sag so headlights 0.6 m up with a beam diverging 1° upward light the road at the
  stopping sight distance. A low beam's cut-off is aimed 0.57° down instead (UN R112), so the bright part of the beam
  meets the rising road sooner. Where it meets the road on sags built to each design speed is set against the flat
  road and the distances to stop.
Writes `../results/grades.json` and `.md`.

    python3 grades.py --figures
    python3 grades.py --check

Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
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
import crest as cr  # noqa: E402
import wet_braking as wb  # noqa: E402
import wet_curves as wc  # noqa: E402

SIM = HERE.parent
ROOT = SIM.parents[1]
CONTROLLER = ROOT / "opendbc_repo" / "opendbc" / "car" / "toyota" / "carcontroller.py"
VALUES = ROOT / "opendbc_repo" / "opendbc" / "car" / "toyota" / "values.py"
OUT_JSON = SIM / "results" / "grades.json"
OUT_MD = SIM / "results" / "grades.md"
G = 9.81

PINS = {   # the lines the grade part rests on; --check fails if one moves
  "pitch_cap": (CONTROLLER, r"^MAX_PITCH_COMPENSATION = ([\d.]+)  # m/s\^2"),
  "pitch_hp": (CONTROLLER, r"self\.pitch_hp = HighPassFilter\(0\.0, 0\.25, 1\.5, DT_CTRL\)"),
  "pitch_comp": (CONTROLLER, r"pitch_compensation = float\(np\.clip\(math\.sin\(self\.pitch_hp\.x\) \* ACCELERATION_DUE_TO_GRAVITY,"),
  "downhill_only": (CONTROLLER, r"accel_due_to_pitch = math\.sin\(min\(self\.pitch\.x, 0\.0\)\) \* ACCELERATION_DUE_TO_GRAVITY"),
  "permit": (CONTROLLER, r"net_acceleration_request_min = min\(actuators\.accel \+ accel_due_to_pitch, net_acceleration_request\)"),
  "clip": (CONTROLLER, r"pcm_accel_cmd = float\(np\.clip\(pcm_accel_cmd, self\.params\.ACCEL_MIN, self\.params\.ACCEL_MAX\)\)"),
  "accel_min": (VALUES, r"self\.ACCEL_MIN = (-[\d.]+)  # m/s2"),
}


def code() -> dict:
  out = {}
  for k, (f, pat) in PINS.items():
    m = re.search(pat, f.read_text(encoding="utf-8"), re.M)
    if not m:
      raise SystemExit(f"{f.name} changed: {pat!r} not found; review grades.py")
    out[k] = float(m.group(1)) if m.groups() else True
  return out


def sag_k(s: float, h: float, div_deg: float) -> float:
  """Sag K (m per %) so a beam from height h diverging div_deg upward meets the road at s (s shorter than the curve)."""
  return s * s / (200 * (h + s * math.tan(math.radians(div_deg))))


def beam_hits_road(k: float, h: float, ang_deg: float) -> float:
  """Distance at which a ray from height h at ang_deg (negative: down) meets a sag y = x² / (200 K) (x from the low point,
  the car at it). Inf if it never does."""
  t = math.tan(math.radians(ang_deg))
  a, b, c = 1 / (200 * k), -t, -h
  disc = b * b - 4 * a * c
  return (-b + math.sqrt(disc)) / (2 * a) if disc >= 0 else math.inf


def run(p: dict) -> dict:
  g = p["grades"]
  c = code()
  a_item = -c["accel_min"]
  v = g["speed_kph"]
  depth = float(wb.water(p, [p["curves"]["rain_mm_h"]["value"]])[0])
  avail = {"dry": wb.mu(p, "new", v, 0.0), "wet_new": wb.mu(p, "new", v, depth),
           "wet_3mm_continental": wc.mu_odd(p, v, depth, "low"), "wet_3mm_mira": wc.mu_odd(p, v, depth, "high")}
  rows = []
  for gp in g["grades_pct"]:
    th = math.atan(gp / 100)
    need = wb.need(a_item, gp)
    row = {"grade_pct": gp, "need": round(need, 3), "gravity_mps2": round(G * math.sin(th), 3),
           "margin": {k: round(m - need, 3) for k, m in avail.items()},
           "item_reachable": {k: m >= need for k, m in avail.items()}}
    stops = {}
    for k, m in avail.items():
      a_full = G * (m * math.cos(th) - math.sin(th))
      stops[k] = round(wb.stop_m(v, a_full, p["stopped_car"]["driver_reaction_s"]["value"]), 1)
    row["driver_stop_m"] = stops
    rows.append(row)
  sf = p["grades"]["sag_formula"]
  nc = p["night_car"]
  kt = p["crest"]["k_table"]
  sags = []
  for vd, s in zip(kt["speeds_kph"], kt["ssd_m"]):
    k = sag_k(s, sf["headlight_m"], sf["divergence_deg"])
    sags.append({"design_speed_kph": vd, "ssd_m": s, "k": round(k, 1),
                 "aashto_light_m": round(beam_hits_road(k, sf["headlight_m"], sf["divergence_deg"]), 1),
                 "cutoff_m": round(beam_hits_road(k, nc["lamp_height_m"]["value"], nc["passing_beam_cd"]["cutoff_deg"]), 1),
                 "cutoff_m_band": [round(beam_hits_road(k, nc["lamp_height_m"][e], nc["passing_beam_cd"]["cutoff_deg"]), 1)
                                   for e in ("low", "high")]})
  flat = nc["lamp_height_m"]["value"] / math.tan(math.radians(-nc["passing_beam_cd"]["cutoff_deg"]))
  stop = json.loads((SIM / "results" / "stopped-car.json").read_text(encoding="utf-8"))["stop_m"]
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. Friction from the wet-braking and wet-curve "
                   "studies; AASHTO's sag model; UN R112's cut-off.",
          "code": c, "speed_kph": v, "water_mm": round(depth, 3), "available": {k: round(x, 3) for k, x in avail.items()},
          "rows": rows, "sags": sags, "flat_cutoff_m": round(flat, 1), "item_stop_m": stop["item"],
          "odd_grade_pct": g["odd_grade_pct"]["value"]}


NAMES = {"dry": "dry", "wet_new": "wet, new tyres", "wet_3mm_continental": "wet, 3 mm (Continental)",
         "wet_3mm_mira": "wet, 3 mm (MIRA)"}


def markdown(r: dict, p: dict) -> str:
  c = r["code"]
  rows = {x["grade_pct"]: x for x in r["rows"]}
  odd = rows[int(r["odd_grade_pct"])]
  L = [
    "# Grades and sag curves: braking downhill, and the low beam over a sag",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/grades.py`](../weather/grades.py) with openpilot's Toyota controller read and pinned from opendbc, the "
    "wet-braking and wet-curve studies' friction, AASHTO's sag model and UN R112's cut-off; do not edit by hand.",
    "",
    "## Braking downhill",
    "",
    f"openpilot asks the PCM for the car's own acceleration, clipped at {c['accel_min']:.1f} m/s² (`carcontroller.py`). "
    f"The grade enters only as a high-pass transient of at most ±{c['pitch_cap']:.1f} m/s² and in the brake-permit "
    "logic (downhill only). So on a downhill the PCM must brake harder at the wheels to hold the same deceleration, "
    f"and the tyres need more friction. At {r['speed_kph']:.0f} km/h in the ODD's light rain ({r['water_mm']:.2f} mm "
    "of water):",
    "",
    "| Downhill | Gravity along the road | Friction the item's −3.5 m/s² needs | " +
    " | ".join(f"Margin, {NAMES[k]}" for k in r["available"]) + " |",
    "|---|---|---|" + "---|" * len(r["available"]),
  ]
  for x in r["rows"]:
    L.append(f"| {x['grade_pct']} % | {x['gravity_mps2']:.2f} m/s² | {x['need']:.2f} | " +
             " | ".join(f"{x['margin'][k]:+.2f}" for k in r["available"]) + " |")
  L += ["", "Friction available: " + ", ".join(f"{NAMES[k]} {v:.2f}" for k, v in r["available"].items()) + ".", "",
        "| Downhill | A driver's full stop from 110 km/h (2.5 s, then full braking): " +
        " | ".join(NAMES[k] for k in r["available"]) + " |",
        "|---|" + "---|" * len(r["available"])]
  for x in r["rows"]:
    L.append(f"| {x['grade_pct']} % | " + " | ".join(f"{x['driver_stop_m'][k]:.0f} m" for k in r["available"]) + " |")
  L += ["", "## The low beam over a sag curve", "",
        "AASHTO builds a sag so a beam diverging 1° upward from headlights 0.6 m up meets the road at the stopping sight "
        f"distance. Our car is at the sag's low point, the road rising ahead. A low beam's cut-off points {-p['night_car']['passing_beam_cd']['cutoff_deg']:.2f}° down; on a flat "
        f"road it meets the road {r['flat_cutoff_m']:.0f} m ahead (the night-car study).", "",
        "| Design speed | Stopping sight distance | Sag K (m/%) | Where AASHTO's 1° beam meets the road | Where the low beam's "
        "cut-off meets it |", "|---|---|---|---|---|"]
  for s in r["sags"]:
    L.append(f"| {s['design_speed_kph']} km/h | {s['ssd_m']} m | {s['k']:.0f} | {s['aashto_light_m']:.0f} m | "
             f"{s['cutoff_m']:.0f} m ({s['cutoff_m_band'][0]:.0f}–{s['cutoff_m_band'][1]:.0f}) |")
  wet_worst = min(odd["margin"].values())
  worst_k = min(odd["margin"], key=odd["margin"].get)
  s110 = next(s for s in r["sags"] if s["design_speed_kph"] == 110)
  lvl = rows[0]
  L += ["", "## What this shows (generated)", "",
        f"- **On the ODD's {r['odd_grade_pct']:.0f} % downhill the item's −3.5 m/s² needs a friction of "
        f"{odd['need']:.2f}**, against {lvl['need']:.2f} on the level. " +
        (f"Dry and wet with new tyres there is room ({odd['margin']['wet_new']:+.2f} wet). "
         if odd["margin"]["wet_new"] > 0 else "") +
        (f"With the ODD's 3 mm of tread the wet margin is {odd['margin']['wet_3mm_continental']:+.2f} "
         f"(Continental) to {odd['margin']['wet_3mm_mira']:+.2f} (MIRA)" +
         ("; at MIRA's end the PCM cannot hold −3.5 m/s² and the car stops later than the item's distance assumes."
          if wet_worst < 0 else "; almost nothing left at MIRA's end." if wet_worst < 0.05 else ".")),
        f"- **A driver's full stop grows downhill**: wet with 3 mm (MIRA) from {lvl['driver_stop_m']['wet_3mm_mira']:.0f} m "
        f"on the level to {odd['driver_stop_m']['wet_3mm_mira']:.0f} m on {r['odd_grade_pct']:.0f} %.",
        "- **openpilot does not plan for the grade**: the planner's −3.5 m/s² is the car's own deceleration and the PCM "
        "closes the loop on it; the pitch terms only shape transients and the brake permit. So the braking the item can "
        "count on is the friction left after gravity, as above.",
        f"- **Over a sag built for 110 km/h the low beam's bright part meets the road {s110['cutoff_m']:.0f} m ahead**, "
        f"against {r['flat_cutoff_m']:.0f} m on the flat and the {s110['aashto_light_m']:.0f} m AASHTO's 1° beam assumes. "
        "AASHTO's beam is the top edge of the light, which in a modern low beam is the dim part above the cut-off; the "
        f"item's {r['item_stop_m']:.0f} m stop is far beyond either. A sag at night is the night-car study's case, a "
        "little worse.",
        f"- For WP-C-02 OI-5: the grade bound costs " +
        ("braking on a wet road with worn tyres; a register question only if the ODD keeps 6 % with 3 mm of tread."
         if wet_worst < 0 else
         "none of the item's braking inside the ODD's tyre and rain bounds, but leaves almost no margin at MIRA's end of "
         "3 mm wet: a line for OI-5's rationale, not a register question." if wet_worst < 0.05 else
         "none of the item's braking inside the ODD's tyre and rain bounds."),
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
    print("grades:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name)
  if a.figures:
    import fig_weather
    fig_weather.grades_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
