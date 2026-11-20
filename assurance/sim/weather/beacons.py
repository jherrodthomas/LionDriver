#!/usr/bin/env python3
"""Emergency beacons at night (physics plan round 4, study 24; WP-C-06 TC-36, TC-02).

A vehicle stopped on the shoulder flashes its warning beacons at 1–4 Hz. As our car approaches at night, each flash
sends light into the road camera. As in the headlight study, the lamps themselves are a few pixels and do not move the
median the auto exposure measures; the light the lens and windshield scatter over the whole image (veiling glare, 1–10 %)
does. openpilot's auto exposure (ported from camerad, `camera_ae.py`) answers within a frame or two, so a flash it can
follow pumps the exposure: the road darkens on each flash and comes back between them. This runs the loop on the
approach and reads how far the road is darkened and how much it pumps. Then the geometry of passing: lane centring
keeps our car mid-lane, so the gap to the stopped vehicle is set by where it stands on the shoulder; every US state's
move-over law asks for more. Writes `../results/beacons.json` and `.md`.

    python3 beacons.py --figures
    python3 beacons.py --check

The beacons' intensity is taken at its peak in every direction, an upper bound; the veil share is assumed. Synthetic
(DSR-12), design aid, no evidence credit (DQ-413).
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

SIM = HERE.parent
OUT_JSON = SIM / "results" / "beacons.json"
OUT_MD = SIM / "results" / "beacons.md"
CAMERA_HEIGHT = 1.2


def lateral_m(p: dict) -> float:
  """Our camera to the beacons, sideways: half our lane, the shoulder's near part, half the vehicle (1.8 m wide)."""
  b = p["beacons"]
  return p["curve_sight"]["lane_width_m"]["value"] / 2 + b["vehicle_from_edge_m"]["value"][1] + 0.9


def flash(t: np.ndarray, hz: float, duty: float, low: float) -> np.ndarray:
  """Beacon output over time, a fraction of the peak: on for `duty` of each period, `low` between flashes."""
  return np.where((t * hz) % 1.0 < duty, 1.0, low)


def run_case(p: dict, c: dict, fov: dict, scale: float, hz: float, peak: float, veil: float, low: float) -> dict:
  b, h = p["beacons"], p["headlights"]
  road = h["road_cd_m2"]["value"]
  v = b["speed_kph"] / 3.6
  t = np.arange(0, b["start_m"] / v, 1 / c["fps"])
  d = b["start_m"] - v * t
  lat = lateral_m(p)
  rng = np.sqrt(d ** 2 + lat ** 2 + (b["beacon_height_m"]["value"] - CAMERA_HEIGHT) ** 2)
  bearing = np.degrees(np.arctan2(lat, np.maximum(d, 1e-6)))
  in_frame = bearing <= fov["hfov_deg"] / 2
  E = b["beacons"]["value"] * peak * flash(t, hz, b["duty"]["value"], low) / rng ** 2
  L_veil = np.where(in_frame, veil * E / math.pi, 0.0)
  base = ae.run(c, np.full(len(t), road), scale)
  glare = ae.run(c, road + L_veil, scale)
  stops = np.log2(np.maximum(ae.gamma(road * glare["ev"] / scale), 1e-6) /
                  np.maximum(ae.gamma(road * base["ev"] / scale), 1e-6))
  def window(lo, hi):
    m = (d <= hi) & (d > lo)
    return float(stops[m].min()), float(stops[m].max())
  w = {f"{int(hi)}": window(hi - 50, hi) for hi in (300, 200, 100, 50)}
  leave = float(d[np.argmax(~in_frame)]) if (~in_frame).any() else 0.0
  out = {"leave_frame_m": round(leave, 1), "veil_ratio_max": round(float((L_veil / road).max()), 3),
         "darkest_stops": round(float(stops.min()), 2),
         "frames_over_1_stop": int((stops < -1).sum()),
         "swing_stops": {k: round(hi - lo, 2) for k, (lo, hi) in w.items()},
         "darkest_by_window": {k: round(lo, 2) for k, (lo, hi) in w.items()}}
  return out, {"d": d, "stops": stops}


def clearance(p: dict) -> list[dict]:
  b = p["beacons"]
  lane = p["curve_sight"]["lane_width_m"]["value"]
  base = lane / 2 - b["our_half_width_m"]["value"]
  return [{"vehicle_from_edge_m": e, "to_vehicle_m": round(base + e, 2),
           "to_person_m": round(base + e - b["person_out_m"]["value"], 2)} for e in b["vehicle_from_edge_m"]["value"]]


def run(p: dict) -> dict:
  b, h, tp = p["beacons"], p["headlights"], p["tunnel"]
  c = ae.code()
  fov = sg.camera_fov()
  scale = tu.scale_for(c, tp["outside_cd_m2"]["value"], tp["ev_day"]["value"])
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. Beacon intensities from Rea and Bullough (2016), "
                  "flash rates from SAE J845 as they quote it; veiling glare share assumed; openpilot's auto exposure "
                  "ported from camerad.",
         "lateral_m": round(lateral_m(p), 2), "fps": c["fps"], "cases": {}, "clearance": clearance(p)}
  traces = {}
  for hz in b["flash_hz"]["value"]:
    for pk in ("low", "value", "high"):
      for vk in ("low", "value", "high"):
        for mode, low in (("off", 0.0), ("partial", b["partial_off"]["value"])):
          key = f"{hz:g}-{pk}-{vk}-{mode}"
          r_, tr = run_case(p, c, fov, scale, hz, b["peak_cd"][pk], h["veil_fraction"][vk], low)
          out["cases"][key] = {"hz": hz, "peak_cd": b["peak_cd"][pk], "veil": h["veil_fraction"][vk], "mode": mode, **r_}
          if pk == "value" and vk == "value" and mode == "off":
            traces[f"{hz:g}"] = tr
  _, worst_tr = run_case(p, c, fov, scale, b["flash_hz"]["value"][0], b["peak_cd"]["high"], h["veil_fraction"]["high"], 0.0)
  mw = worst_tr["d"] <= 120
  out["trace_worst"] = {"d": [round(float(x), 2) for x in worst_tr["d"][mw]],
                        "stops": [round(float(x), 3) for x in worst_tr["stops"][mw]]}
  keep = traces[f"{b['flash_hz']['value'][0]:g}"]
  m = keep["d"] <= 120
  out["trace"] = {"hz": b["flash_hz"]["value"][0], "d": [round(float(x), 2) for x in keep["d"][m]],
                  "stops": [round(float(x), 3) for x in keep["stops"][m]]}
  return out


def markdown(r: dict, p: dict) -> str:
  b = p["beacons"]
  cs = r["cases"]
  def g(hz, pk, vk, mode="off"):
    return cs[f"{hz:g}-{pk}-{vk}-{mode}"]
  L = [
    "# Emergency beacons at night: what the flashes do to the road camera",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/beacons.py`](../weather/beacons.py) with openpilot's auto exposure ported from camerad "
    "([`camera_ae.py`](../weather/camera_ae.py)); do not edit by hand. Beacon intensities from Rea and Bullough (2016), "
    "flash rates from SAE J845 as they quote it; the share of light the lens and windshield scatter (1–10 %) is assumed, "
    "as in the headlight study.",
    "",
    f"A vehicle stopped on the shoulder, its {b['beacons']['value']} beacons {r['lateral_m']:.1f} m to our right, "
    f"{b['beacon_height_m']['value']:.1f} m up, flashing fully on and off (50 % duty). We approach at "
    f"{b['speed_kph']:.0f} km/h on a dark road (the exposure settled at {p['headlights']['road_cd_m2']['value']:g} cd/m²). "
    "The beacons stay in the camera's frame until we are almost level with them "
    f"({g(b['flash_hz']['value'][0], 'value', 'value')['leave_frame_m']:.0f} m).",
    "",
    "| Flash rate | Beacon peak | Scatter 1 / 3 / 10 %: road darkened at most | Swing of the road's exposure in the last "
    "50 m, 3 % / 10 % scatter | Frames darkened by more than a stop, 10 % |",
    "|---|---|---|---|---|",
  ]
  for hz in b["flash_hz"]["value"]:
    for pk in ("low", "value", "high"):
      lo, mid, hi = (g(hz, pk, vk) for vk in ("low", "value", "high"))
      L.append(f"| {hz:g} Hz | {b['peak_cd'][pk]:,.0f} cd | {-lo['darkest_stops']:.1f} / {-mid['darkest_stops']:.1f} / "
               f"{-hi['darkest_stops']:.1f} stops | {mid['swing_stops']['50']:.1f} / {hi['swing_stops']['50']:.1f} stops | "
               f"{hi['frames_over_1_stop']} |")
  hz0 = b["flash_hz"]["value"][0]
  a = g(hz0, "value", "value")
  ap = g(hz0, "value", "value", "partial")
  worst = min((x for x in cs.values() if x["mode"] == "off"), key=lambda x: x["darkest_stops"])
  hl = json.loads((SIM / "results" / "headlights.json").read_text(encoding="utf-8"))["cases"]["divided-8-high-high"]
  slow, fast = g(hz0, "high", "high"), g(b["flash_hz"]["value"][-1], "high", "high")
  cl = r["clearance"]
  L += ["", "## Passing it", "",
        "Lane centring keeps our car in the middle of a "
        f"{p['curve_sight']['lane_width_m']['value']:.2f} m lane, so the gap to a vehicle on the shoulder is set by where "
        "it stands. openpilot does not move over or slow for it.", "",
        "| Vehicle's near side from the edge line | Our car's side to the vehicle | To a person at its door |",
        "|---|---|---|"]
  for x in cl:
    L.append(f"| {x['vehicle_from_edge_m']:.1f} m | {x['to_vehicle_m']:.2f} m | {x['to_person_m']:.2f} m |")
  L += ["", "## What this shows (generated)", "",
        f"- **The beacons hardly move the exposure until the last 50 m.** With a {b['peak_cd']['value']:,.0f} cd beacon "
        f"and 3 % scatter the road is darkened by at most {-a['darkest_stops']:.1f} stops; at 50–100 m the swing is "
        f"{a['swing_stops']['100']:.2f} stops. A beacon is far dimmer than a high beam: an undipped one across a median "
        f"darkens the road by up to {-hl['road_stops_min']:.1f} stops (the headlight study).",
        f"- **Close in, each flash darkens the road.** openpilot's exposure reacts within a frame or two, and the last "
        f"50 m take {50 / (b['speed_kph'] / 3.6):.1f} s, one to a few flashes: up to {worst['swing_stops']['50']:.1f} stops "
        f"in the worst case ({worst['peak_cd']:,.0f} cd at {worst['hz']:g} Hz, a dirty windshield), with "
        f"{worst['frames_over_1_stop']} frames darkened by more than a stop. Faster flashing is smoothed a little by the "
        f"loop's averaging ({slow['swing_stops']['50']:.1f} stops at {hz0:g} Hz, {fast['swing_stops']['50']:.1f} at "
        f"{b['flash_hz']['value'][-1]:g} Hz).",
        f"- **Flashing that stays partly on** (10 % between flashes, as Rea and Bullough recommend) "
        + ("hardly changes it" if abs(ap['swing_stops']['50'] - a['swing_stops']['50']) < 0.05 else
           f"cuts the last 50 m swing to {ap['swing_stops']['50']:.1f} stops") + ": the flashes' peaks set the veil.",
        f"- **Passing**: lane centring leaves {cl[0]['to_vehicle_m']:.2f}–{cl[-1]['to_vehicle_m']:.2f} m to the vehicle "
        f"and {cl[0]['to_person_m']:.2f}–{cl[-1]['to_person_m']:.2f} m to a person at its door. Move-over laws ask the "
        "driver to change lanes or slow down; the item does neither, so it stays the driver's task (TC-36).",
        "- For KS tests at night: a vehicle on the shoulder with flashing beacons, a dirty windshield, and a check of the "
        "lane lines while the image blinks in the last 50 m. A log of this camera's veiling glare would turn the band into a line.",
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
    print("beacons:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name)
  if a.figures:
    import fig_weather
    fig_weather.beacons_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
