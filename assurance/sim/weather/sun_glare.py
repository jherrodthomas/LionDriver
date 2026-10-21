#!/usr/bin/env python3
"""Sun in the road camera (WP-C-06 TC-01, WP-V-03 KS-12): when, on which headings, and for how long in a year.

For every 5 min of a year at the corridor of the test sites, the sun's position (NREL SPA through pvlib, apparent
elevation with refraction) is compared with the road camera's field of view, read from
`openpilot/common/transformations/camera.py`. Writes `../results/sun-glare.json` and `.md`; `--figures` draws them.

    python3 sun_glare.py --figures   # results and figures
    python3 sun_glare.py --check     # CI: fail if a fresh run differs from the committed results

Terrain, trees, buildings and clouds are not modelled: the hours are an upper bound on glare, not a count of it.
Synthetic (DSR-12), design aid, no evidence credit (DQ-139).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CAMERA = ROOT / "openpilot" / "common" / "transformations" / "camera.py"
OUT_JSON = HERE.parent / "results" / "sun-glare.json"
OUT_MD = HERE.parent / "results" / "sun-glare.md"
TOL = 0.05   # hours, minutes or degrees


def camera_fov() -> dict:
  """Field of view of the comma 3X / four road camera (AR0231/OX03C10) from its intrinsics in camera.py."""
  src = CAMERA.read_text(encoding="utf-8")
  m = re.search(r"_ar_ox_config = DeviceCameraConfig\(CameraConfig\((\d+), (\d+), ([\d.]+)\)", src)
  if not m:
    raise SystemExit(f"road camera intrinsics not found in {CAMERA}")
  w, h, f = int(m.group(1)), int(m.group(2)), float(m.group(3))
  return {"width_px": w, "height_px": h, "focal_px": f,
          "hfov_deg": round(2 * math.degrees(math.atan(w / 2 / f)), 2),
          "vfov_deg": round(2 * math.degrees(math.atan(h / 2 / f)), 2)}


def sun(p: dict) -> pd.DataFrame:
  s = p["sun"]
  t = pd.date_range(f"{s['year']}-01-01", f"{s['year'] + 1}-01-01", freq=f"{s['step_min']}min", inclusive="left",
                    tz=s["site"]["tz"])
  sp = pvlib.solarposition.spa_python(t, s["site"]["lat"], s["site"]["lon"])
  return pd.DataFrame({"elev": sp["apparent_elevation"].to_numpy(), "az": sp["azimuth"].to_numpy()}, index=t)


def offaxis(az: np.ndarray, heading: float) -> np.ndarray:
  return (az - heading + 180.0) % 360.0 - 180.0


def masks(df: pd.DataFrame, heading: float, fov: dict, p: dict) -> dict:
  s = p["sun"]
  d = np.abs(offaxis(df["az"].to_numpy(), heading))
  e = df["elev"].to_numpy() - s["camera_pitch_deg"]["value"]
  up = df["elev"].to_numpy() > 0
  hh, vh, mg = fov["hfov_deg"] / 2, fov["vfov_deg"] / 2, s["flare_margin_deg"]["value"]
  return {"in_view": up & (d <= hh) & (e <= vh),
          "flare": up & (d <= hh + mg) & (e <= vh + mg),
          "ks12": up & (d <= hh) & (df["elev"].to_numpy() < s["ks12_elevation_deg"]["value"])}


def run(p: dict) -> dict:
  fov = camera_fov()
  df = sun(p)
  dt_h = p["sun"]["step_min"] / 60
  headings = list(range(0, 360, 5))
  by_heading = {k: [] for k in ("in_view", "flare", "ks12")}
  for hd in headings:
    for k, v in masks(df, hd, fov, p).items():
      by_heading[k].append(round(float(v.sum() * dt_h), 1))
  corridor = {}
  days = df.index.normalize()
  for name, c in p["sun"]["corridor"].items():
    m = masks(df, c["heading"], fov, p)
    iv = m["in_view"]
    local = df.index[iv]
    month = pd.Series(iv, index=df.index).groupby(df.index.month).sum() * dt_h
    minutes = (local.hour * 60 + local.minute).to_numpy()
    corridor[name] = {
      "heading": c["heading"],
      "hours_in_view": round(float(iv.sum() * dt_h), 1),
      "hours_flare": round(float(m["flare"].sum() * dt_h), 1),
      "days_with_sun_in_view": int(pd.Series(iv, index=days).groupby(level=0).any().sum()),
      "longest_daily_min": round(float(pd.Series(iv, index=days).groupby(level=0).sum().max() * p["sun"]["step_min"]), 1),
      "by_month_h": [round(float(month.get(i, 0.0)), 1) for i in range(1, 13)],
      "morning_share": round(float((minutes < 12 * 60).mean()) if len(minutes) else 0.0, 3),
      "calendar": _calendar(df, iv, p["sun"]["step_min"]),
    }
  daylight = float((df["elev"] > 0).sum() * dt_h)
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. Upper bound: no terrain, trees or clouds.",
          "camera": fov, "pitch_deg": p["sun"]["camera_pitch_deg"]["value"], "site": p["sun"]["site"], "year": p["sun"]["year"], "daylight_hours": round(daylight, 1),
          "headings": headings, "by_heading_h": by_heading, "corridor": corridor}


def _calendar(df, iv, step):
  """Day of year x 20 min slot: minutes of sun in view per slot (kept small for the JSON)."""
  slot = 20
  per = slot // step
  doy = df.index.dayofyear.to_numpy() - 1
  sl = ((df.index.hour * 60 + df.index.minute).to_numpy()) // slot
  grid = np.zeros((int(doy.max()) + 1, 24 * 60 // slot), dtype=int)
  np.add.at(grid, (doy[iv], sl[iv]), step)
  assert grid.max() <= per * step
  return grid.tolist()


def markdown(r: dict) -> str:
  c, fov = r["corridor"], r["camera"]
  months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
  L = [
    "# Sun in the road camera: the I-85 corridor over a year",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit.** Generated by "
    "[`weather/sun_glare.py`](../weather/sun_glare.py) from [`params.yaml`](../weather/params.yaml); do not edit by "
    "hand. **An upper bound:** terrain, trees, buildings and clouds are not modelled, so the sun is counted whenever "
    "it is geometrically in the frame.",
    "",
    f"Road camera from `camera.py`: {fov['width_px']}×{fov['height_px']} px, focal length {fov['focal_px']:.0f} px, "
    f"so **{fov['hfov_deg']:.1f}° × {fov['vfov_deg']:.1f}°** (pitch {r['pitch_deg']:.0f}°, assumed level). Sun position: NREL SPA "
    f"(pvlib), every 5 min of {r['year']} at {r['site']['lat']}° N, {abs(r['site']['lon'])}° W "
    f"({r['daylight_hours']:.0f} daylight hours).",
    "",
    "| Direction | Heading | Sun in the frame | Within 10° of the frame (flare) | Days with sun in the frame | Longest in one day | Mornings |",
    "|---|---|---|---|---|---|---|",
  ]
  for name, d in c.items():
    L.append(f"| I-85 {name} | {d['heading']:.0f}° | {d['hours_in_view']:.0f} h/year | {d['hours_flare']:.0f} h/year | "
             f"{d['days_with_sun_in_view']} | {d['longest_daily_min']:.0f} min | {100 * d['morning_share']:.0f} % |")
  L += ["", "## By month (hours with the sun in the frame)", "",
        "| Direction | " + " | ".join(months) + " |", "|---|" + "---|" * 12]
  for name, d in c.items():
    L.append(f"| {name} | " + " | ".join(f"{v:.0f}" for v in d["by_month_h"]) + " |")
  hv = r["by_heading_h"]["in_view"]
  worst = r["headings"][int(np.argmax(hv))]
  L += ["", "## What this shows (generated from the numbers above)", "",
        f"- Of all headings, {worst}° has the most sun in the frame ({max(hv):.0f} h/year); "
        f"{r['headings'][int(np.argmin(hv))]}° the least ({min(hv):.0f} h/year).",
        f"- Northbound the sun is in the frame on mornings ({100 * c['northbound']['morning_share']:.0f} % of its "
        f"hours), southbound on evenings ({100 - 100 * c['southbound']['morning_share']:.0f} %): the months are the "
        "table's, and the calendar figure gives the clock times to schedule KS-12 drives.",
        "- Not a count of glare: whether the sun really sits in the frame depends on the skyline, which needs the "
        "logged drives (recorded sun position against the road camera's exposure).", ""]
  return "\n".join(L)


def compare(new, old, path=""):
  if isinstance(new, dict):
    return [e for k in set(new) | set(old) for e in
            ([f"{path}/{k}: missing"] if k not in new or k not in old else compare(new[k], old[k], f"{path}/{k}"))]
  if isinstance(new, list):
    if len(new) != len(old):
      return [f"{path}: length differs"]
    return [e for i, (a, b) in enumerate(zip(new, old, strict=True)) for e in compare(a, b, f"{path}[{i}]")]
  if isinstance(new, float) and isinstance(old, (int, float)):
    return [] if abs(new - old) <= TOL else [f"{path}: {new} != {old}"]
  return [] if new == old else [f"{path}: {new!r} != {old!r}"]


def main(argv):
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--figures", action="store_true")
  a = ap.parse_args(argv[1:])
  p = yaml.safe_load((HERE / "params.yaml").read_text(encoding="utf-8"))
  r = run(p)
  md = markdown(r)
  if a.check:
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("sun glare:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, {k: v["hours_in_view"] for k, v in r["corridor"].items()})
  if a.figures:
    import fig_weather
    fig_weather.sun_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
