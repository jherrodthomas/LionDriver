#!/usr/bin/env python3
"""Steering authority for the ODD's curves (physics plan round 4, study 26; WP-C-02 §3.2, OI-2, GAP-04, AOU-01).

openpilot's torque controller limits its own output to the lateral acceleration that full steering torque gives:
`latcontrol_torque.py` sets the PID limits at `lateral_accel_from_torque(steer_max)`, which is `steer_max ·
latAccelFactor` with steer_max = 1. For the Corolla TSS2, opendbc's torque data (fitted by comma on fleet data) gives
latAccelFactor 1.99 m/s², and the most lateral acceleration it measured 1.87 m/s²; the online learner (`torqued.py`)
may move the factor by ±30 %. These lines are read and pinned here.

The ODD's curve bound is R = v² / 2.5 m/s² (WP-C-02 §3.2). In a curve the steering has to give v²/R less what the
road's bank toward the inside gives (g·e); an adverse crown adds to it, and a side wind adds the crosswind study's
steering need. This compares that demand with the controller's ceiling, and finds the tightest curve the ceiling can
hold at each speed and bank. No raw torque scale is needed: the ceiling is in m/s². Writes
`../results/steer-authority.json` and `.md`.

    python3 steer_authority.py --figures
    python3 steer_authority.py --check

The fleet fit is comma's, for the model year mix in their data, not a measurement of the reference car (OI-2 asks for
that). Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
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
SIM = HERE.parent
ROOT = SIM.parents[1]
TORQUE = ROOT / "opendbc_repo" / "opendbc" / "car" / "torque_data" / "params.toml"
LATCONTROL = ROOT / "openpilot" / "selfdrive" / "controls" / "lib" / "latcontrol_torque.py"
LATBASE = ROOT / "openpilot" / "selfdrive" / "controls" / "lib" / "latcontrol.py"
TORQUED = ROOT / "openpilot" / "selfdrive" / "locationd" / "torqued.py"
CROSSWIND = SIM / "results" / "crosswind.json"
OUT_JSON = SIM / "results" / "steer-authority.json"
OUT_MD = SIM / "results" / "steer-authority.md"
G = 9.81
CAR = "TOYOTA_COROLLA_TSS2"


def code() -> dict:
  """The controller's ceiling and the Corolla's torque data, read from the sources; stops if a line moved."""
  t = TORQUE.read_text(encoding="utf-8")
  if 'legend = ["LAT_ACCEL_FACTOR", "MAX_LAT_ACCEL_MEASURED", "FRICTION"]' not in t:
    raise SystemExit("torque_data/params.toml changed its legend; review steer_authority.py")
  m = re.search(rf'^"{CAR}" = \[([^\]]*)\]', t, re.M)
  if not m:
    raise SystemExit(f"{CAR} not in torque_data/params.toml; review steer_authority.py")
  laf, measured, friction = (float(x) for x in m.group(1).split(","))
  lc = LATCONTROL.read_text(encoding="utf-8")
  for pat in (r"self\.pid\.set_limits\(self\.lateral_accel_from_torque\(self\.steer_max, self\.torque_params\),",):
    if not re.search(pat, lc):
      raise SystemExit(f"latcontrol_torque.py changed: {pat!r}; review steer_authority.py")
  sm = re.search(r"self\.steer_max = ([\d.]+)", LATBASE.read_text(encoding="utf-8"))
  fs = re.search(r"^FACTOR_SANITY = ([\d.]+)", TORQUED.read_text(encoding="utf-8"), re.M)
  if not (sm and fs):
    raise SystemExit("latcontrol.py or torqued.py changed; review steer_authority.py")
  return {"lat_accel_factor": round(laf, 4), "max_lat_accel_measured": round(measured, 4),
          "friction": round(friction, 4), "steer_max": float(sm.group(1)), "factor_sanity": float(fs.group(1))}


def wind_need(v_kph: float, wind_kph: float) -> tuple[float, float]:
  """The crosswind study's steering need (m/s², lower and upper) at this speed and side wind, interpolated."""
  cw = json.loads(CROSSWIND.read_text(encoding="utf-8"))["speeds"]
  speeds = sorted(float(k) for k in cw)
  w = wind_kph / 3.6
  lo = [float(np.interp(w, cw[f"{s}"]["wind"], cw[f"{s}"]["lower"])) for s in speeds]
  hi = [float(np.interp(w, cw[f"{s}"]["wind"], cw[f"{s}"]["upper"])) for s in speeds]
  # the push grows with the square of speed for a given wind angle; between the study's speeds, interpolate
  return float(np.interp(v_kph, speeds, lo)), float(np.interp(v_kph, speeds, hi))


def run(p: dict) -> dict:
  sa = p["steer_authority"]
  c = code()
  ceil = {"fit": c["lat_accel_factor"] * c["steer_max"], "measured": c["max_lat_accel_measured"],
          "learned_low": c["lat_accel_factor"] * (1 - c["factor_sanity"]),
          "learned_high": c["lat_accel_factor"] * (1 + c["factor_sanity"])}
  a_odd = p["curves"]["lateral_odd"]["value"]
  a_ctrl = p["curves"]["lateral_ctrl"]["value"]
  rows = []
  for vk in sa["speeds_kph"]:
    v = vk / 3.6
    R = v * v / a_odd
    banks = {}
    for e in sa["bank"]["value"]:
      demand = v * v / R - G * e
      winds = {f"{w:g}": [round(demand + x, 3) for x in wind_need(vk, w)] for w in sa["wind_kph"]["value"]}
      r_min = {k: round(v * v / (x + G * e), 1) for k, x in (("fit", ceil["fit"]), ("measured", ceil["measured"]))}
      banks[f"{e:g}"] = {"demand": round(demand, 3), "margin_fit": round(ceil["fit"] - demand, 3),
                         "margin_measured": round(ceil["measured"] - demand, 3), "with_wind": winds,
                         "r_min_m": r_min}
    rows.append({"speed_kph": vk, "r_odd_m": round(R, 1), "r_ctrl_m": round(v * v / a_ctrl, 1), "banks": banks})
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. The controller's ceiling from opendbc's "
                   "fleet-fitted torque data (comma); the ODD's curve bound; the crosswind study's push.",
          "car": CAR, "code": c, "ceiling_m_s2": {k: round(x, 3) for k, x in ceil.items()},
          "odd_lateral_m_s2": a_odd, "controller_lateral_m_s2": a_ctrl,
          "bound_for_ceiling": {k: round(x, 3) for k, x in ceil.items()}, "rows": rows}


def markdown(r: dict, p: dict) -> str:
  c, ce = r["code"], r["ceiling_m_s2"]
  banks = [f"{e:g}" for e in p["steer_authority"]["bank"]["value"]]
  bname = {"-0.02": "adverse crown −2 %", "0": "flat", "0.06": "banked 6 %"}
  L = [
    "# Steering authority for the ODD's curves",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/steer_authority.py`](../weather/steer_authority.py) from openpilot's torque controller and opendbc's "
    "torque data, read and pinned; do not edit by hand. The torque data is comma's fit on fleet data, not a "
    "measurement of the reference car (WP-C-02 OI-2 asks for that).",
    "",
    f"openpilot's torque controller limits its output to the lateral acceleration full torque gives "
    f"(`latcontrol_torque.py`: `lateral_accel_from_torque(steer_max)`). For the Corolla TSS2 that is "
    f"**{ce['fit']:.2f} m/s²** (`LAT_ACCEL_FACTOR`); the most comma measured is {ce['measured']:.2f} m/s². The online "
    f"learner may move the factor ±{100 * c['factor_sanity']:.0f} % ({ce['learned_low']:.2f}–{ce['learned_high']:.2f}). "
    f"The ODD's curve bound asks for {r['odd_lateral_m_s2']:.1f} m/s² (R = v² / {r['odd_lateral_m_s2']:.1f}); "
    f"WP-C-02 takes the controller's limit as {r['controller_lateral_m_s2']:.1f} m/s² (`drive_helpers.py`), the "
    "curvature the planner may ask for, not what the torque can deliver.",
    "",
    "## On the ODD's tightest curve",
    "",
    "| Speed | R_ODD | Steering needed: " + " / ".join(bname[b] for b in banks) +
    " | Left under the fitted ceiling | With a 30 km/h side wind (flat) |",
    "|---|---|---|---|---|",
  ]
  for x in r["rows"]:
    b = x["banks"]
    L.append(f"| {x['speed_kph']} km/h | {x['r_odd_m']:.0f} m | " +
             " / ".join(f"{b[k]['demand']:.2f}" for k in banks) + " m/s² | " +
             " / ".join(f"{b[k]['margin_fit']:+.2f}" for k in banks) + " | " +
             f"{b['0']['with_wind']['30'][0]:.2f}–{b['0']['with_wind']['30'][1]:.2f} m/s² |")
  L += ["", "Below 80 km/h the side wind's push is held at the crosswind study's 80 km/h value, an upper bound.",
        "", "## The tightest curve the ceiling holds", "",
        "| Speed | R_ODD today | Fitted ceiling: " + " / ".join(bname[k] for k in banks) +
        " | Measured maximum, flat |", "|---|---|---|---|"]
  for x in r["rows"]:
    b = x["banks"]
    L.append(f"| {x['speed_kph']} km/h | {x['r_odd_m']:.0f} m | " +
             " / ".join(f"{b[k]['r_min_m']['fit']:.0f} m" for k in banks) + f" | {b['0']['r_min_m']['measured']:.0f} m |")
  r110 = next(x for x in r["rows"] if x["speed_kph"] == 110)["banks"]
  L += ["", "## What this shows (generated)", "",
        f"- **On a flat curve at the ODD's bound the steering cannot hold the lane.** The bound asks for "
        f"{r['odd_lateral_m_s2']:.1f} m/s²; the controller's ceiling is {ce['fit']:.2f} ({ce['measured']:.2f} measured), "
        f"{r110['0']['margin_fit']:+.2f} m/s² short. At 110 km/h the tightest flat curve it holds is "
        f"{r110['0']['r_min_m']['fit']:.0f} m, against R_ODD's {next(x for x in r['rows'] if x['speed_kph'] == 110)['r_odd_m']:.0f} m.",
        f"- **A banked curve closes the gap, only just.** At 6 % superelevation the road gives "
        f"{G * 0.06:.2f} m/s² and the steering needs {r110['0.06']['demand']:.2f}: "
        + (f"{r110['0.06']['margin_fit']:.2f} m/s² to spare" if r110["0.06"]["margin_fit"] >= 0 else
           f"still {-r110['0.06']['margin_fit']:.2f} m/s² over the ceiling")
        + f". An adverse crown makes it {r110['-0.02']['margin_fit']:+.2f}.",
        f"- **Wind takes the rest.** A 30 km/h side wind adds the crosswind study's "
        f"{r110['0']['with_wind']['30'][0] - r110['0']['demand']:.1f}–{r110['0']['with_wind']['30'][1] - r110['0']['demand']:.1f} "
        "m/s²: on any of these curves the total is over the ceiling.",
        "- **What happens then:** the controller saturates and the car runs wide of the lane; openpilot raises "
        "`steerSaturated` after 0.4 s (WP-S-04 §3.8). WP-C-02 §3.2 already rests the curve bound on AOU-01 (EPS "
        "authority suffices), not characterised (GAP-04, OI-2). The fleet fit says that assumption does not hold at "
        "2.5 m/s² on a flat curve. **A question for the lead** (an ODD limit), queued as DQ-444.",
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
    sys.path.insert(0, str(HERE))
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("steer authority:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name)
  if a.figures:
    sys.path.insert(0, str(HERE))
    import fig_weather
    fig_weather.steer_authority_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
