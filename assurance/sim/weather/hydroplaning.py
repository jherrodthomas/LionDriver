#!/usr/bin/env python3
"""Hydroplaning (WP-C-06 TC-03, WP-C-02 precipitation): at what speed the Corolla's tyres lose the road in rain.

Two published models:
- **Water film and speed**, the PAVDRN model of NCHRP (Anderson et al. 1998) from Gallaway et al. 1979 (FHWA-RD-79-31)
  and Huebner et al. 1986: rain intensity, drainage path and texture give the water film over the texture; the film
  gives the hydroplaning speed.
- **NASA**, Horne and Dreher 1963 (NASA TN D-2056): V = 10.35 sqrt(p) mph, tyre pressure p in psi. Full dynamic
  hydroplaning when the water is deeper than the tread (ruts, puddles, a worn tyre), independent of rain.

Writes `../results/hydroplaning.json` and `.md`; `--figures` draws them.

    python3 hydroplaning.py --figures
    python3 hydroplaning.py --check

Empirical models from trough and track tests of the 1960s–80s, not of this tyre. Synthetic (DSR-12), design aid,
no evidence credit (DQ-139).
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
OUT_JSON = HERE.parent / "results" / "hydroplaning.json"
OUT_MD = HERE.parent / "results" / "hydroplaning.md"
MPH = 1.609344
IN = 25.4
TOL = 0.05


def film_mm(rain_mm_h, path_m, slope_pct, texture_mm):
  """Gallaway water film above the texture top, metric form (mm; m; mm/h; %). Zero when the texture drains it."""
  d = 0.103 * texture_mm ** 0.11 * path_m ** 0.43 * np.asarray(rain_mm_h, float) ** 0.59 / slope_pct ** 0.42 - texture_mm
  return np.maximum(d, 0.0)


def pavdrn_mph(film_in, texture_in):
  """PAVDRN hydroplaning speed (mph) from the water film (in) and mean texture depth (in); inf for no film."""
  film_in = np.asarray(film_in, float)
  out = np.full(film_in.shape, np.inf)
  thin = (film_in > 0) & (film_in < 0.095)
  out[thin] = 26.04 * film_in[thin] ** -0.259
  thick = film_in >= 0.095
  w = film_in[thick] ** 0.06
  a = np.maximum(10.409 / w + 3.507, (28.952 / w - 7.817) * texture_in ** 0.14)
  out[thick] = 3.09 * a
  return out


def nasa_mph(psi):
  return 10.35 * math.sqrt(psi)


def path(lanes, lane_w, slope, grade):
  """Drainage path across `lanes` lanes on a crowned road with a longitudinal grade, and its resultant slope (%)."""
  w = lanes * lane_w
  return w * math.sqrt(1 + (grade / slope) ** 2), math.hypot(slope, grade)


def run(p: dict) -> dict:
  w = p["water"]
  rain = w["rain_mm_h"]
  odd = w["odd_speed_kph"]["value"]
  tex = w["texture_depth_mm"]
  rows = {}
  for lanes in w["lanes_drained"]:
    for g in w["grade_pct"]:
      L, S = path(lanes, w["lane_width_m"]["value"], w["cross_slope_pct"]["value"], g)
      f = film_mm(rain, L, S, tex["value"])
      v = pavdrn_mph(f / IN, tex["value"] / IN) * MPH
      rows[f"{lanes} lane{'s' if lanes > 1 else ''}, {g:g} % grade"] = {
        "path_m": round(L, 2), "slope_pct": round(S, 2), "film_mm": [round(float(x), 3) for x in f],
        "speed_kph": [None if not np.isfinite(x) else round(float(x), 1) for x in v],
        "rain_at_odd_speed_mm_h": _rain_at(odd, L, S, tex["value"])}
  # sensitivity on the worst-case row (most lanes, steepest grade): texture and cross slope at their ends
  lanes, g = max(w["lanes_drained"]), max(w["grade_pct"])
  sens = {}
  for name, slope, t in (("texture low", w["cross_slope_pct"]["value"], tex["low"]),
                         ("texture high", w["cross_slope_pct"]["value"], tex["high"]),
                         ("cross slope low", w["cross_slope_pct"]["low"], tex["value"]),
                         ("cross slope high", w["cross_slope_pct"]["high"], tex["value"])):
    L, S = path(lanes, w["lane_width_m"]["value"], slope, g)
    sens[name] = _rain_at(odd, L, S, t)
  pr = w["tyre_pressure_psi"]
  nasa = {k: round(nasa_mph(pr[k]) * MPH, 1) for k in ("low", "value", "high")}
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. Empirical models, not of this tyre.",
          "odd_speed_kph": odd, "rain_mm_h": rain, "classes_mm_h": w["rain_classes_mm_h"], "rows": rows,
          "worst_row": f"{lanes} lane{'s' if lanes > 1 else ''}, {g:g} % grade", "sensitivity_rain_at_odd_mm_h": sens, "nasa_kph": nasa,
          "nasa_pressure_psi": {k: pr[k] for k in ("low", "value", "high")}}


def _rain_at(v_kph, L, S, tex):
  """Lowest rain intensity (mm/h) at which the PAVDRN speed falls to v_kph, by bisection on a monotone curve."""
  lo, hi = 0.1, 500.0
  f = lambda r: pavdrn_mph(film_mm([r], L, S, tex) / IN, tex / IN)[0] * MPH - v_kph  # noqa: E731
  if f(hi) > 0:
    return None
  for _ in range(60):
    mid = math.sqrt(lo * hi)
    lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
  return round(hi, 1)


def markdown(r: dict) -> str:
  odd, light, mod = r["odd_speed_kph"], r["classes_mm_h"]["light"], r["classes_mm_h"]["moderate"]
  L = [
    "# Hydroplaning: when the Corolla's tyres lose the road in rain",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit.** Generated by "
    "[`weather/hydroplaning.py`](../weather/hydroplaning.py) from [`params.yaml`](../weather/params.yaml); do not "
    "edit by hand. Empirical models from trough and track tests (Gallaway et al. 1979, FHWA-RD-79-31; PAVDRN, NCHRP "
    "1998; Horne and Dreher 1963, NASA TN D-2056), not tests of this car's tyres.",
    "",
    f"ODD speed bound {odd:.0f} km/h (WP-C-02, DQ-260). Rain classes (US NWS): light below {light} mm/h, moderate "
    f"to {mod} mm/h, heavy above. The ODD includes light rain and excludes moderate and heavy rain, but gives no number.",
    "",
    "## Rain intensity at which the hydroplaning speed falls to the ODD bound",
    "",
    "| Road (lanes draining across, grade) | Drainage path | Rain at which hydroplaning starts at "
    f"{odd:.0f} km/h | Speed in {light} mm/h | Speed in 50 mm/h |",
    "|---|---|---|---|---|",
  ]
  i_light, i_50 = r["rain_mm_h"].index(light), r["rain_mm_h"].index(50)
  for name, d in r["rows"].items():
    sp = lambda v: "no water film" if v is None else f"{v:.0f} km/h"  # noqa: E731
    L.append(f"| {name} | {d['path_m']:.1f} m | {d['rain_at_odd_speed_mm_h']} mm/h | {sp(d['speed_kph'][i_light])} | "
             f"{sp(d['speed_kph'][i_50])} |")
  s = r["sensitivity_rain_at_odd_mm_h"]
  n = r["nasa_kph"]
  worst = r["rows"][r["worst_row"]]["rain_at_odd_speed_mm_h"]
  dry = all(d["speed_kph"][i_light] is None for d in r["rows"].values())
  L += [
    "",
    f"Sensitivity on the worst row ({r['worst_row']}): texture {s['texture low']} – {s['texture high']} mm/h, "
    f"cross slope {s['cross slope low']} – {s['cross slope high']} mm/h.",
    "",
    "## Standing water deeper than the tread (NASA)",
    "",
    f"Horne's formula gives full dynamic hydroplaning at **{n['value']:.0f} km/h** at {r['nasa_pressure_psi']['value']} psi "
    f"({n['low']:.0f} km/h at {r['nasa_pressure_psi']['low']} psi, {n['high']:.0f} km/h at "
    f"{r['nasa_pressure_psi']['high']} psi): {'below' if n['value'] < odd else 'above'} the {odd:.0f} km/h bound. It "
    "applies where water stands deeper than the tread: wheel ruts, puddles at low spots, a worn tyre.",
    "",
    "## What this shows (generated)",
    "",
    (f"- In light rain (below {light} mm/h) the texture drains the water on every road here: no film, no "
     "hydroplaning from rain alone." if dry else
     f"- In light rain (below {light} mm/h) a water film forms on some roads here; see the table."),
    f"- The film model brings the hydroplaning speed down to {odd:.0f} km/h from {worst} mm/h on the worst road "
    f"here, {worst / mod:.1f} times the top of moderate rain{', so only in rain the ODD excludes' if worst > mod else ''}.",
    f"- Standing water is the case to watch: NASA's {n['value']:.0f} km/h is "
    f"{'below' if n['value'] < odd else 'above'} the ODD bound. Excluding heavier rain does not exclude a puddle or "
    "a rut holding water after the rain, which the ODD's rain bound does not address.",
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
  md = markdown(r)
  if a.check:
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("hydroplaning:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, "nasa", r["nasa_kph"])
  if a.figures:
    import fig_weather
    fig_weather.water_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
