#!/usr/bin/env python3
"""Tunnel entry and exit (WP-C-06 TC-18, WP-V-03 KS-12): how long openpilot's road camera is badly exposed.

At a tunnel portal the brightness of the road ahead drops by a factor of hundreds, and rises again at the exit. The
road camera's auto exposure is openpilot's own loop, ported line by line with its constants read from camerad
(`camera_ae.py`, OX03C10 sensor). It is driven here with the median luminance of the road ahead at 110 km/h: the
sunlit approach, the threshold zone, the transition and the interior of a lit tunnel (orders of CIE 88), then the
exit into daylight. A frame counts as badly exposed when its grey is more than one stop from the loop's target.
Writes `../results/tunnel.json` and `.md`.

    python3 tunnel.py --figures
    python3 tunnel.py --check

The scene is a single median luminance per frame (what the loop measures), with the sensor's gamma curve; HDR
merging, tone mapping beyond the gamma, and how the driving model copes with the frames are not modelled.
TC-18 is excluded from the ODD until validated: this gives the length of the windows a validation must cover.
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

SIM = HERE.parent
OUT_JSON = SIM / "results" / "tunnel.json"
OUT_MD = SIM / "results" / "tunnel.md"
LEAD_S = 3.0            # seconds of approach before the portal


def target_grey(c: dict, ev: float) -> float:
  """The loop's settled target grey at exposure ev (the code's new_target_grey)."""
  return min(max(0.4 - 0.3 * math.log2(1.0 + c["target_grey_factor"] * ev) / math.log2(6000.0), c["grey_min_road"]), 0.4)


def scale_for(c: dict, lum: float, ev: float) -> float:
  """Sensor sensitivity that makes the loop settle at ev on luminance lum."""
  return lum * ev / ae.gamma_inv(target_grey(c, ev))


def profile(p: dict, fps: float, outside: float) -> tuple[np.ndarray, np.ndarray, dict]:
  """Median luminance ahead, frame by frame, from the approach through the tunnel to the exit."""
  tp = p["tunnel"]
  v = tp["speed_kph"] / 3.6
  th, tr, length = tp["threshold_m"]["value"], tp["transition_m"]["value"], tp["length_m"]["value"]
  L_th = outside * tp["threshold_ratio"]["value"]
  L_in = tp["interior_cd_m2"]["value"]
  t_entry = LEAD_S
  t_exit = LEAD_S + length / v
  t = np.arange(0, t_exit + 6.0, 1 / fps)
  s = (t - t_entry) * v                                   # metres past the portal
  inside = np.where(s < th, L_th, np.exp(np.interp(s, [th, th + tr], [math.log(L_th), math.log(L_in)])))
  w = tp["portal_s"]["value"]
  def smooth(x):                                          # 0 -> 1 over the portal time, centred on the event
    return 0.5 * (1 + np.tanh(x / (w / 4)))
  lum = np.exp(np.log(outside) + smooth(t - t_entry) * (np.log(inside) - np.log(outside)))
  lum = np.exp(np.log(lum) + smooth(t - t_exit) * (np.log(outside) - np.log(lum)))
  return t, lum, {"entry_s": t_entry, "exit_s": t_exit, "threshold_cd_m2": L_th, "interior_cd_m2": L_in}


def windows(t: np.ndarray, grey: np.ndarray, target: np.ndarray, stops: float, after: float, before: float) -> dict:
  """Frames whose grey is more than `stops` from the target, between `after` and `before`."""
  sel = (t >= after) & (t < before)
  off = np.abs(np.log2(np.maximum(grey, 1e-6) / target)) > stops
  bad = off & sel
  dark = bad & (grey < target)
  bright = bad & (grey > target)
  idx = np.where(bad)[0]
  last = float(t[idx[-1]] - after) if len(idx) else 0.0
  return {"frames": int(bad.sum()), "dark_frames": int(dark.sum()), "bright_frames": int(bright.sum()),
          "until_s": round(last, 2)}


def run(p: dict) -> dict:
  tp = p["tunnel"]
  c = ae.code()
  stops = tp["off_stops"]["value"]
  out = {"about": "Synthetic (DSR-12), design aid, no evidence credit. openpilot's auto exposure, ported from camerad; "
                  "CIE 88 orders of tunnel luminance.",
         "code": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items() if k != "gains"},
         "ev_floor": round(c["exposure_time_min"] * c["gains"][c["gain_min_idx"]] * c["gain_factor"], 3), "cases": {}}
  for name, outside, ev_day in (("nominal", tp["outside_cd_m2"]["value"], tp["ev_day"]["value"]),
                                ("bright_day", tp["outside_cd_m2"]["high"], tp["ev_day"]["value"]),
                                ("dull_day", tp["outside_cd_m2"]["low"], tp["ev_day"]["value"]),
                                ("sensitive", tp["outside_cd_m2"]["value"], tp["ev_day"]["low"]),
                                ("insensitive", tp["outside_cd_m2"]["value"], tp["ev_day"]["high"])):
    t, lum, ev_ = profile(p, c["fps"], outside)
    scale = scale_for(c, tp["outside_cd_m2"]["value"], ev_day)
    r = ae.run(c, lum, scale)
    entry = windows(t, r["grey"], r["target"], stops, ev_["entry_s"] - 0.5, ev_["exit_s"] - 0.5)
    exit_ = windows(t, r["grey"], r["target"], stops, ev_["exit_s"] - 0.5, t[-1] + 1)
    case = {"outside_cd_m2": outside, "ev_day": ev_day, "entry": entry, "exit": exit_,
            "ev_inside": round(float(r["ev"][np.searchsorted(t, ev_["exit_s"] - 1.0)]), 1),
            "ev_max_hit": bool(r["ev"].max() >= 0.999 * c["max_ev"]),
            "ev_floor_hit": bool(r["ev"].min() <= 1.001 * out["ev_floor"]),
            "grey_settled_out": round(float(r["grey"][0]), 3), **{k: round(v, 3) for k, v in ev_.items()}}
    if name == "nominal":
      case["trace"] = {"t": [round(float(x), 3) for x in t], "lum": [round(float(x), 3) for x in lum],
                       "grey": [round(float(x), 4) for x in r["grey"]], "target": [round(float(x), 4) for x in r["target"]],
                       "ev": [round(float(x), 2) for x in r["ev"]]}
    out["cases"][name] = case
  return out


NAMES = {"nominal": "Nominal (4000 cd/m² outside, settles at exposure 30)", "bright_day": "Brighter approach (8000 cd/m²)",
         "dull_day": "Duller approach (2000 cd/m²)", "sensitive": "More sensitive sensor (settles at exposure 15)",
         "insensitive": "Less sensitive sensor (settles at exposure 120)"}


def markdown(r: dict, p: dict) -> str:
  tp = p["tunnel"]
  fps = r["code"]["fps"]
  n = r["cases"]["nominal"]
  def ms(f):
    return f"{1000 * f / fps:.0f} ms"
  L = [
    "# Tunnel entry and exit: how long the road camera is badly exposed",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/tunnel.py`](../weather/tunnel.py) with openpilot's auto exposure ported from camerad "
    "([`camera_ae.py`](../weather/camera_ae.py)); do not edit by hand. Luminances are typical orders (CIE 88), not a "
    "real tunnel; the sensor's sensitivity is an assumption until local logs give the exposure on a sunny road.",
    "",
    f"At {tp['speed_kph']:.0f} km/h: the sunlit approach, then the threshold zone at "
    f"{100 * tp['threshold_ratio']['value']:.0f} % of it for {tp['threshold_m']['value']:.0f} m, a transition to "
    f"{tp['interior_cd_m2']['value']:.0f} cd/m² inside, a {tp['length_m']['value'] / 1000:.0f} km tunnel and the exit "
    f"into daylight. The loop runs at {fps:.0f} frames a second; a frame is badly exposed when its grey is more than "
    f"{tp['off_stops']['value']:.0f} stop from the target. The exposure cannot go below {r['ev_floor']:.1f} "
    "(2 lines at the always-on conversion gain of 7.32).",
    "",
    "| Case | Entry: badly exposed frames (dark / bright) | Entry: last one after | Exit: badly exposed frames | "
    "Exit: last one after | Exposure floor reached |",
    "|---|---|---|---|---|---|",
  ]
  for k, cs in r["cases"].items():
    e, x = cs["entry"], cs["exit"]
    L.append(f"| {NAMES[k]} | {e['frames']} ({e['dark_frames']} / {e['bright_frames']}), {ms(e['frames'])} | "
             f"{e['until_s']:.2f} s | {x['frames']} ({x['dark_frames']} / {x['bright_frames']}), {ms(x['frames'])} | "
             f"{x['until_s']:.2f} s | {'yes' if cs['ev_floor_hit'] else 'no'} |")
  e, x = n["entry"], n["exit"]
  worst_exit = max(r["cases"].values(), key=lambda cs: cs["exit"]["frames"])
  L += ["", "## What this shows (generated)", "",
        f"- **Entry:** {e['frames']} frames ({ms(e['frames'])}) badly exposed, {e['dark_frames']} too dark and "
        f"{e['bright_frames']} too bright, the last {e['until_s']:.2f} s after the portal. A dark frame tells the loop "
        "how far off it is (the grey is not clipped), so it corrects in a few steps; it overshoots briefly because it "
        "acts on the same dark frames again while its first correction is still in flight (three frames of latency).",
        f"- **Exit:** {x['frames']} frames ({ms(x['frames'])}) badly exposed, the last {x['until_s']:.2f} s after the "
        f"exit, up to {worst_exit['exit']['frames']} frames in the cases above: the exit is the longer window. An "
        "overexposed frame tells the loop less (its grey is near the top of the gamma curve), so it steps down only a "
        "little each frame.",
        f"- Inside, the loop settles at an exposure about {n['ev_inside'] / tp['ev_day']['value']:.0f} times the "
        "daylight one, well within the sensor's range.",
        "- For KS-12 and TC-18: a validation drive through tunnels must cover windows of about a second at each portal "
        "where the road camera's image is far from its target. How the driving model copes with them is the "
        "question for the logged drives; this says only how long they last.",
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
    print("tunnel:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, {k: (v["entry"], v["exit"], v["ev_inside"], v["ev_floor_hit"]) for k, v in r["cases"].items()})
  if a.figures:
    import fig_weather
    fig_weather.tunnel_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
