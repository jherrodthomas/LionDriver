#!/usr/bin/env python3
"""Oncoming headlights at night (WP-C-06 TC-02, WP-V-03 KS-12): what they do to openpilot's road camera.

An oncoming car closes at twice the speed. Its headlamps are a small bright source in the road camera's frame
(field of view from `camera.py`); they leave the frame when they pass more than half the field of view to the side.
The light they send toward us is bounded by UN R112: at most 350 cd from a low beam toward an oncoming driver (point
B50L), 40,500–215,000 cd from an undipped driving beam. Two effects on the image:
- **The source itself** saturates a few pixels. openpilot's auto exposure measures the median grey of a large
  rectangle (`calculate_exposure_value`), so a few bright pixels do not move it.
- **Veiling glare**: the lens and the windshield scatter a share of the light over the whole image, which lifts the
  median like a brighter road. The exposure loop (`camera_ae.py`, ported from camerad) then darkens the frame, and
  the road loses contrast. The share is not known for this camera: 1–10 % spans a clean lens to a dirty windshield.
Inside the ODD (divided highways) the oncoming traffic is across a median; the undivided road is outside the ODD
and kept for reference. Writes `../results/headlights.json` and `.md`.

    python3 headlights.py --figures
    python3 headlights.py --check

The weakest of the plan's studies: no flare data for this camera, a single median luminance for the road, and the
beams' bounding intensities taken in every direction.
Synthetic (DSR-12), design aid, no evidence credit.
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
OUT_JSON = SIM / "results" / "headlights.json"
OUT_MD = SIM / "results" / "headlights.md"
AE_RECT_PX = (1734, 986)    # road camera exposure rectangle at its own focal length (camera_qcom2.cc set_exposure_rect)


def encounter(p: dict, fps: float, offset: float) -> dict:
  """Distance, bearing and illuminance at the camera per frame, from start_m until the cars pass."""
  h = p["headlights"]
  v_close = 2 * h["speed_kph"] / 3.6
  t = np.arange(0, h["start_m"] / v_close, 1 / fps)
  d = h["start_m"] - v_close * t                       # along the road
  rng = np.hypot(d, offset)
  bearing = np.degrees(np.arctan2(offset, d))           # to the side of the camera's axis
  elev = np.degrees(np.arctan2(h["lamp_height_m"]["value"] - h["camera_height_m"]["value"], d))
  return {"t": t, "d": d, "range": rng, "bearing": bearing, "elev": elev}


def run_case(p: dict, c: dict, fov: dict, scale: float, offset: float, intensity: float, veil: float, road: float) -> dict:
  e = encounter(p, c["fps"], offset)
  in_frame = (e["bearing"] <= fov["hfov_deg"] / 2) & (np.abs(e["elev"]) <= fov["vfov_deg"] / 2)
  E = 2 * intensity / e["range"] ** 2                       # lux at the lens, two lamps
  L_veil = np.where(in_frame, veil * E / math.pi, 0.0)       # scattered light, as an even luminance over the image
  base = ae.run(c, np.full(len(e["t"]), road), scale)
  glare = ae.run(c, road + L_veil, scale)
  road_grey = ae.gamma(road * glare["ev"] / scale)           # the road itself, in the darkened frame
  base_grey = ae.gamma(road * base["ev"] / scale)
  stops = np.log2(np.maximum(road_grey, 1e-6) / np.maximum(base_grey, 1e-6))
  contrast = road / (road + L_veil)
  px = p["headlights"]["lamp_size_m"]["value"] * fov["focal_px"] / e["range"]
  leave = e["d"][np.argmax(~in_frame)] if (~in_frame).any() else 0.0
  return {"leave_frame_m": round(float(leave), 1), "veil_ratio_max": round(float((L_veil / road).max()), 4),
          "contrast_min": round(float(contrast.min()), 3), "road_stops_min": round(float(stops.min()), 2),
          "frames_over_1_stop": int((stops < -1).sum()),
          "lamp_px_at_exit": round(float(px[np.argmax(~in_frame)] if (~in_frame).any() else px[-1]), 1),
          "lamp_share_of_rect": float(f"{2 * (px[in_frame].max() ** 2) / (AE_RECT_PX[0] * AE_RECT_PX[1]):.2e}"),
          "trace": {"d": [round(float(x), 1) for x in e["d"]], "stops": [round(float(x), 3) for x in stops],
                    "veil": [round(float(x), 4) for x in (L_veil / road)]}}


def run(p: dict) -> dict:
  h, tp = p["headlights"], p["tunnel"]
  c = ae.code()
  fov = sg.camera_fov()
  scale = tu.scale_for(c, tp["outside_cd_m2"]["value"], tp["ev_day"]["value"])   # the tunnel study's sensor
  road = h["road_cd_m2"]["value"]
  night = ae.run(c, np.full(10, road), scale)
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. UN R112 intensity bounds; veiling glare share "
                  "assumed; openpilot's auto exposure ported from camerad.",
         "fov": fov, "night_ev": round(float(night["ev"][-1]), 1), "night_grey": round(float(night["grey"][-1]), 3),
         "max_ev": round(c["max_ev"], 1), "cases": {}}
  beams = {"low": h["low_beam_cd"]["value"], "high": h["high_beam_cd"]["value"]}
  for road_kind, offs in (("undivided", [h["offsets_m"]["undivided"]]), ("divided", h["offsets_m"]["divided"])):
    for off in offs:
      for beam, I in beams.items():
        for vk in ("low", "value", "high"):
          key = f"{road_kind}-{off:g}-{beam}-{vk}"
          r_ = run_case(p, c, fov, scale, off, I, h["veil_fraction"][vk], road)
          if not (vk == "value" and beam == "high"):
            r_.pop("trace")
          out["cases"][key] = {"road": road_kind, "offset_m": off, "beam": beam, "veil": h["veil_fraction"][vk], **r_}
  return out


def markdown(r: dict, p: dict) -> str:
  h = p["headlights"]
  cs = r["cases"]
  def get(road, off, beam, vk):
    return cs[f"{road}-{off:g}-{beam}-{vk}"]
  L = [
    "# Oncoming headlights at night: what they do to the road camera",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/headlights.py`](../weather/headlights.py) with openpilot's auto exposure ported from camerad "
    "([`camera_ae.py`](../weather/camera_ae.py)); do not edit by hand. Headlamp intensities are UN R112's bounds; the "
    "share of light the lens and windshield scatter (veiling glare) is assumed, 1–10 %. The weakest of the plan's "
    "studies: a band, not a line.",
    "",
    f"Both cars at {h['speed_kph']:.0f} km/h. The road ahead at {h['road_cd_m2']['value']:g} cd/m² under our own low "
    f"beams, where the exposure loop settles at exposure {r['night_ev']:.0f} (its maximum is {r['max_ev']:.0f}). The "
    f"road camera sees ±{r['fov']['hfov_deg'] / 2:.0f}° to the side; the oncoming lamps leave its frame once they are "
    "that far off its axis.",
    "",
    "| Road | Oncoming beam | Lamps leave the frame at | Glare veil over the road, at most (1 % / 3 % / 10 % scatter) | "
    "Road contrast left, at worst (10 %) | Road darkened in the image, at most (10 %) | Frames darkened by more than a stop |",
    "|---|---|---|---|---|---|---|",
  ]
  offs = [("undivided", h["offsets_m"]["undivided"])] + [("divided", o) for o in h["offsets_m"]["divided"]]
  for road, off in offs:
    for beam in ("low", "high"):
      lo, mid, hi = (get(road, off, beam, k) for k in ("low", "value", "high"))
      where = "undivided, one lane over (outside the ODD)" if road == "undivided" else f"divided, {off:g} m across the median"
      L.append(f"| {where} | {'low beam (≤ 350 cd)' if beam == 'low' else 'undipped high beam (40,500 cd)'} | "
               f"{mid['leave_frame_m']:.0f} m | {100 * lo['veil_ratio_max']:.1f} % / {100 * mid['veil_ratio_max']:.1f} % / "
               f"{100 * hi['veil_ratio_max']:.1f} % of the road | {100 * hi['contrast_min']:.0f} % | "
               f"{-hi['road_stops_min']:.1f} stops | {hi['frames_over_1_stop']} |")
  und_hi = get("undivided", h["offsets_m"]["undivided"], "high", "high")
  div = [get("divided", o, "low", "high") for o in h["offsets_m"]["divided"]]
  div_hi = [get("divided", o, "high", "high") for o in h["offsets_m"]["divided"]]
  share = max(x["lamp_share_of_rect"] for x in cs.values())
  L += ["", "## What this shows (generated)", "",
        f"- **The lamps themselves do not move the exposure.** At their closest in frame they cover at most "
        f"{100 * share:.3f} % of the exposure rectangle; the loop takes the median, so the road stays exposed and the "
        "lamps appear as small saturated spots.",
        f"- **Low beams across a median (inside the ODD)**: the veil stays under "
        f"{100 * max(x['veil_ratio_max'] for x in div):.1f} % of the road even with a dirty windshield; the lamps leave "
        f"the frame {min(x['leave_frame_m'] for x in div):.0f}–{max(x['leave_frame_m'] for x in div):.0f} m before the "
        "cars pass, so the closest, brightest part of the encounter is outside the camera's view.",
        f"- **An undipped high beam** is the case that matters. Across an {h['offsets_m']['divided'][0]:g} m median "
        f"with 10 % scatter the veil leaves {100 * div_hi[0]['contrast_min']:.0f} % of the road's contrast and the "
        f"loop darkens the road by up to {-div_hi[0]['road_stops_min']:.1f} stops; on an undivided road (outside the "
        f"ODD) {100 * und_hi['contrast_min']:.0f} % and {-und_hi['road_stops_min']:.1f} stops. These take the beam's "
        "peak intensity in every direction, an upper bound: 20° off its axis a driving beam is much dimmer.",
        "- For KS-12: the night test should include oncoming undipped high beams across the median and a dirty "
        "windshield, the two things that move the result. A measurement of this camera's veiling glare would turn the "
        "band into a line.",
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
    print("headlights:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["night_ev"], r["night_grey"])
  for k, v in r["cases"].items():
    print(k, v["leave_frame_m"], v["veil_ratio_max"], v["road_stops_min"], v["frames_over_1_stop"], v["lamp_share_of_rect"])
  if a.figures:
    import fig_weather
    fig_weather.headlight_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
