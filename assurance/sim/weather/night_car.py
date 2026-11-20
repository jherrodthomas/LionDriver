#!/usr/bin/env python3
"""A stopped car beyond the headlights (physics plan round 4, study 21; WP-C-06 TC-08, TC-20, WP-V-03 KS-05).

At night on an unlit road the only light on a stopped car is our own. A low beam has a cut-off: aimed 0.57° below
the horizontal, it puts at least 5,100 cd on the road below that line and at most a few hundred cd above it (UN R112,
class B). The cut-off line meets the road about 65 m ahead, so beyond a few tens of metres a car's whole rear is above
it, in the dim part of the beam. For each distance this finds the light on the car's rear and on the road beside it,
from both lamps; their luminance (a dark, grey and white rear; the road, dry and wet, by its retroreflectivity); the
red reflex reflectors' return (FMVSS 108's minimum); and what the road camera's auto exposure, settled on the road
near the car, makes of each. The same with a driving beam. Set against the 149 m the item needs to stop from
110 km/h (the stopped-car study). Writes `../results/night-car.json` and `.md`.

    python3 night_car.py --figures
    python3 night_car.py --check

The beam above the cut-off is bounded by the regulation's caps, so the car is at most this bright; the reflectors at
least. What the model detects at a given contrast is learned, not computed here. Synthetic (DSR-12), design aid, no
evidence credit (DQ-413).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import camera_ae as ae  # noqa: E402
import sun_glare as sg  # noqa: E402
import tunnel as tu  # noqa: E402
import wet_braking as wb  # noqa: E402

SIM = HERE.parent
STOPPED = SIM / "results" / "stopped-car.json"
OUT_JSON = SIM / "results" / "night-car.json"
OUT_MD = SIM / "results" / "night-car.md"
CAMERA_HEIGHT = 1.2       # the road camera, as the crest and headlight studies


def passing_cd(alpha: float, beta: float, b: dict, above: float, width: float) -> float:
  """Luminous intensity of one class B passing beam (right-hand traffic) at alpha degrees up and beta degrees right of
  its H-V axis: at least `below_cutoff` under the cut-off, `above` over it, log-linear across `width` degrees. The
  cut-off's horizontal part sits at cutoff_deg and rises at the shoulder angle to the right of the elbow (at V)."""
  cut = b["cutoff_deg"] + max(beta, 0.0) * math.tan(math.radians(b["shoulder_deg"]))
  lo, hi = cut - width / 2, cut + width / 2
  if alpha <= lo:
    return b["below_cutoff"]
  if alpha >= hi:
    return above
  f = (alpha - lo) / width
  return math.exp((1 - f) * math.log(b["below_cutoff"]) + f * math.log(above))


def lamps(p: dict) -> list[tuple[float, float]]:
  n = p["night_car"]
  return [(-n["lamp_half_track_m"]["value"], n["lamp_height_m"]["value"]), (n["lamp_half_track_m"]["value"], n["lamp_height_m"]["value"])]


def light_at(p: dict, x: float, y: float, z: float, beam: str, above: float) -> list[dict]:
  """Illuminance from each of our lamps on a surface facing us at x right, y up, z ahead (m), with the angles."""
  n = p["night_car"]
  out = []
  for lx, ly in lamps(p):
    dx, dy = x - lx, y - ly
    r2 = dx * dx + dy * dy + z * z
    alpha = math.degrees(math.atan2(dy, z))
    beta = math.degrees(math.atan2(dx, z))
    if beam == "passing":
      cd = passing_cd(alpha, beta, n["passing_beam_cd"], above, n["cutoff_width_deg"]["value"])
    else:
      cd = n["driving_beam_hv_cd"]["value"]
    out.append({"lx": lx, "ly": ly, "cd": cd, "E": cd / r2, "alpha": alpha})
  return out


def cil(p: dict, obs_deg: float) -> float:
  """Red reflex reflector, candela per lux, at an observation angle: FMVSS 108's minimum, log-linear between its two
  observation angles, held below the first and above the second."""
  (a0, c0), (a1, c1) = p["night_car"]["reflector"]["cil_mcd_lx"]
  if obs_deg <= a0:
    return c0 / 1000
  if obs_deg >= a1:
    return c1 / 1000
  f = (obs_deg - a0) / (a1 - a0)
  return math.exp((1 - f) * math.log(c0) + f * math.log(c1)) / 1000


def exposure(p: dict) -> dict:
  """The road camera's auto exposure settled at night on the road near the car (the headlight study's sensor)."""
  c = ae.code()
  tp = p["tunnel"]
  scale = tu.scale_for(c, tp["outside_cd_m2"]["value"], tp["ev_day"]["value"])
  road = p["headlights"]["road_cd_m2"]["value"]
  night = ae.run(c, np.full(10, road), scale)
  return {"ev": float(night["ev"][-1]), "scale": scale, "road_median": road}


def grey(L: float, ex: dict) -> float:
  return float(ae.gamma(L * ex["ev"] / ex["scale"]))


def at_distance(p: dict, d: float, beam: str, above: float, ex: dict, focal: float) -> dict:
  n = p["night_car"]
  h = n["rear_heights_m"]
  pave = p["markings"]["pavement_rl"]
  rho = n["paint_reflectance"]
  body = {}
  for y in h["body"]:
    E = sum(x["E"] for x in light_at(p, 0.0, y, d, beam, above))
    body[f"{y:g}"] = E
  e_mid = body[f"{h['body'][1]:g}"]
  lum = {k: rho[k] * e_mid / math.pi for k in ("dark", "grey", "white")}
  road_E = sum(x["E"] for x in light_at(p, 0.0, 0.0, d, beam, above))
  road = {"dry": pave["dry"] / 1000 * road_E, "wet": pave["wet"] / 1000 * road_E}
  # one reflector (of two), lit by both lamps; its return toward the camera at the centre of our car
  rf = n["reflector"]
  I_r = 0.0
  for x in light_at(p, rf["half_spacing_m"], h["reflector"], d, beam, above):
    sep = math.hypot(x["lx"] - 0.0, x["ly"] - CAMERA_HEIGHT)
    obs = math.degrees(sep / d)
    I_r += cil(p, obs) * x["E"]
  px_area = (d / focal) ** 2                                        # one pixel's footprint at the car, m²
  L_ref = I_r / max(rf["area_m2"], px_area)
  out = {"distance_m": d, "rear_lux": {k: round(v, 5) for k, v in body.items()},
         "road_lux": round(road_E, 5),
         "luminance_cd_m2": {**{k: float(f"{v:.3g}") for k, v in lum.items()},
                             "road_dry": float(f"{road['dry']:.3g}"), "road_wet": float(f"{road['wet']:.3g}"),
                             "reflector": float(f"{L_ref:.3g}")},
         "reflector_cd": float(f"{I_r:.3g}"),
         "reflector_px": round(math.sqrt(rf["area_m2"]) * focal / d, 2)}
  out["stops_below_median"] = {k: round(math.log2(ex["road_median"] / v), 1) for k, v in out["luminance_cd_m2"].items()}
  out["grey_of_255"] = {k: round(255 * grey(v, ex), 1) for k, v in out["luminance_cd_m2"].items()}
  out["contrast_to_road_dry"] = {k: round(lum[k] / road["dry"] - 1, 2) for k in lum}
  out["contrast_to_road_wet"] = {k: round(lum[k] / road["wet"] - 1, 2) for k in lum}
  out["rear_above_cutoff"] = all(x["alpha"] > n["passing_beam_cd"]["cutoff_deg"] + n["cutoff_width_deg"]["value"] / 2
                                 for y in h["body"] for x in light_at(p, 0.0, y, d, "passing", above))
  return out


def cutoff_ground_m(p: dict) -> float:
  n = p["night_car"]
  return n["lamp_height_m"]["value"] / math.tan(math.radians(-n["passing_beam_cd"]["cutoff_deg"]))


def rear_clear_m(p: dict) -> float:
  """Distance beyond which the whole rear (from its lowest body height) is over the cut-off's upper edge."""
  n = p["night_car"]
  top = n["passing_beam_cd"]["cutoff_deg"] + n["cutoff_width_deg"]["value"] / 2
  dy = n["lamp_height_m"]["value"] - n["rear_heights_m"]["body"][0]
  return dy / math.tan(math.radians(-top))


def run(p: dict) -> dict:
  n = p["night_car"]
  ex = exposure(p)
  focal = sg.camera_fov()["focal_px"]
  stop = json.loads(STOPPED.read_text(encoding="utf-8"))["stop_m"]
  a_item = -wb.accel_min()
  ab = n["passing_beam_cd"]["above_cutoff"]
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. UN R112 class B beam bounds (above the cut-off "
                  "at most, below at least); FMVSS 108 reflector minimum; paint reflectances assumed.",
         "exposure": {"ev": round(ex["ev"], 1), "road_median_cd_m2": ex["road_median"]},
         "focal_px": focal, "cutoff_on_road_m": round(cutoff_ground_m(p), 1),
         "rear_over_cutoff_beyond_m": round(rear_clear_m(p), 1),
         "stop_m": {"item_110": stop["item"],
                    "item_120": round(wb.stop_m(120.0, a_item, p["braking"]["reaction_s"]["value"]), 1),
                    "driver_unwarned_dry": stop["driver_unwarned_dry"]},
         "passing": {}, "driving": {}}
  for k in ("low", "value", "high"):
    out["passing"][k] = [at_distance(p, float(d), "passing", ab[k], ex, focal) for d in n["distances_m"]]
  out["driving"] = [at_distance(p, float(d), "driving", ab["value"], ex, focal) for d in n["distances_m"]]
  curve = {"d": [], "lux": {"low": [], "value": [], "high": [], "driving": []}, "stops": {k: [] for k in
           ("dark", "white", "road_dry", "reflector")}}
  for d in np.arange(15.0, 225.0, 5.0):
    curve["d"].append(float(d))
    for k in ("low", "value", "high"):
      x = at_distance(p, float(d), "passing", ab[k], ex, focal)
      curve["lux"][k].append(x["rear_lux"][f"{n['rear_heights_m']['body'][1]:g}"])
      if k == "value":
        for kk in curve["stops"]:
          curve["stops"][kk].append(x["stops_below_median"][kk])
    curve["lux"]["driving"].append(at_distance(p, float(d), "driving", ab["value"], ex, focal)["rear_lux"][
      f"{n['rear_heights_m']['body'][1]:g}"])
  out["curve"] = curve
  # the stopped car at the item's own stopping distance, low beam, the generous cap
  d149 = out["stop_m"]["item_110"]
  out["at_item_stop"] = {k: at_distance(p, d149, "passing", ab[k], ex, focal) for k in ("low", "value", "high")}
  out["at_item_stop_driving"] = at_distance(p, d149, "driving", ab["value"], ex, focal)
  return out


def markdown(r: dict, p: dict) -> str:
  n = p["night_car"]
  ab = n["passing_beam_cd"]["above_cutoff"]
  s = r["stop_m"]
  L = [
    "# A stopped car beyond the headlights: what the road camera sees of it at night",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/night_car.py`](../weather/night_car.py) from UN R112's beam limits, FMVSS 108's reflector minimum and "
    "openpilot's auto exposure ported from camerad ([`camera_ae.py`](../weather/camera_ae.py)); do not edit by hand. "
    "Above the cut-off the regulation only caps the beam, so the car is at most this bright; paint reflectances are "
    "assumed.",
    "",
    f"Our low beam's cut-off is aimed {-n['passing_beam_cd']['cutoff_deg']:.2f}° down and meets the road "
    f"{r['cutoff_on_road_m']:.0f} m ahead. Below it the beam gives at least {n['passing_beam_cd']['below_cutoff']:,.0f} cd; "
    f"above it at most {ab['low']:.0f}–{ab['high']:,.0f} cd (the regulation's caps, {ab['value']:.0f} cd taken as the middle). "
    f"Beyond {r['rear_over_cutoff_beyond_m']:.0f} m a car's whole rear is above the cut-off. The auto exposure is "
    f"settled on the road near our car ({r['exposure']['road_median_cd_m2']:g} cd/m²), as it is at night.",
    "",
    f"| Distance | Light on the rear (lux) | Dark rear | White rear | Road beside it, dry | Dark rear against the dry "
    f"road | A reflector (minimum) | Reflector's size in the image |",
    "|---|---|---|---|---|---|---|---|",
  ]
  for x in r["passing"]["value"]:
    lu, st = x["luminance_cd_m2"], x["stops_below_median"]
    mid = x["rear_lux"][f"{n['rear_heights_m']['body'][1]:g}"]
    L.append(f"| {x['distance_m']:.0f} m | {mid:.3f} | {lu['dark']:.2g} cd/m² ({st['dark']:.0f} stops under) | "
             f"{lu['white']:.2g} ({st['white']:.0f}) | {lu['road_dry']:.2g} ({st['road_dry']:.0f}) | "
             f"{100 * x['contrast_to_road_dry']['dark']:+.0f} % | {lu['reflector']:.2g} ({st['reflector']:+.0f}) | "
             f"{x['reflector_px']:.1f} px |")
  a = r["at_item_stop"]
  dv = r["at_item_stop_driving"]
  v_lo, v_hi = a["low"], a["high"]
  L += ["", "Stops are below the road the exposure is set on (a minus sign: above it). Contrast is the rear's "
        "luminance over the road's beside it, less one.", "",
        "## What this shows (generated)", "",
        f"- **At {s['item_110']:.0f} m, where the item would have to start braking from 110 km/h, the car's rear is "
        f"above the cut-off and gets {v_lo['rear_lux'][f'{n['rear_heights_m']['body'][1]:g}']:.3f}–"
        f"{v_hi['rear_lux'][f'{n['rear_heights_m']['body'][1]:g}']:.3f} lux** from our low beams (at most). A dark rear "
        f"is then {v_hi['stops_below_median']['dark']:.0f}–{v_lo['stops_below_median']['dark']:.0f} stops under the "
        f"road the exposure is set on, {v_hi['grey_of_255']['dark']:.1f} of 255 at best: black. A white rear is "
        f"{v_hi['stops_below_median']['white']:.0f}–{v_lo['stops_below_median']['white']:.0f} stops under.",
        f"- **There is little silhouette either.** A dark rear and the road beside it are both under "
        f"{max(a['value']['luminance_cd_m2']['dark'], a['value']['luminance_cd_m2']['road_dry']):.3f} cd/m²: the rear is "
        f"{100 * a['value']['contrast_to_road_dry']['dark']:+.0f} % against a dry road and "
        f"{100 * a['value']['contrast_to_road_wet']['dark']:+.0f} % against a wet one, which returns even less of the light. "
        "Both are lit by the same beam, so the paint's colour, not the light, sets the difference, and in the image both "
        "are near black.",
        f"- **The reflectors are the brightest part of an unlit car.** At the regulation's minimum each is "
        f"{a['value']['luminance_cd_m2']['reflector']:.2g} cd/m², {-a['value']['stops_below_median']['reflector']:.0f} "
        f"stops over the road the exposure is set on, but {a['value']['reflector_px']:.1f} px across in the road camera, "
        f"{a['value']['reflector_px'] * r['stopped_px_ratio']:.1f} px in the model's input: two red dots.",
        f"- **A driving beam changes it**: at least {n['driving_beam_hv_cd']['value']:,.0f} cd straight ahead puts "
        f"{dv['rear_lux'][f'{n['rear_heights_m']['body'][1]:g}']:.1f} lux on the rear at {s['item_110']:.0f} m, and a dark "
        f"rear is {dv['stops_below_median']['dark']:.0f} stops under the road's exposure, a white one at about the road's level "
        f"({dv['grey_of_255']['white']:.0f} of 255). Highway traffic usually means low beams.",
        f"- **Over the ODD's speed** the item needs {s['item_120']:.0f} m from 120 km/h (TC-20), further into the dark.",
        "- So at night on an unlit road the model would have to take an unlit stopped car from its reflectors and its "
        "silhouette against whatever lies beyond, not from the light on it. A lit car (tail or hazard lights) is a "
        "different case: its lamps are far brighter than anything here. For KS-05: test an unlit stopped car at night, "
        "dark and light coloured, on low beams; a night log (T1) shows what the model does.",
        ""]
  return "\n".join(L)


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  st = json.loads(STOPPED.read_text(encoding="utf-8"))["code"]
  r["stopped_px_ratio"] = round(st["narrow_fl_px"] / r["focal_px"], 4)
  md = markdown(r, p)
  if a.check:
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("night car:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name)
  if a.figures:
    import fig_weather
    fig_weather.night_car_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
