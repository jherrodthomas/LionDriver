#!/usr/bin/env python3
"""Crosswind on the Corolla (WP-C-06 TC-15, WP-V-03 KS-02): how hard a side wind pushes, against the steering margin.

The side force and yaw moment come from the car's side elevation, measured on the purchased mesh
(`../figures/corolla-e210-geometry.json`), with two textbook models applied along its height profile h(x):
- **slender-body (potential) force**, the car and its mirror image in the road taken as a slender wing of span 2 h(x):
  side force per unit length q β π d(h²)/dx where the height grows; where it falls (rear window, boot) the flow is
  separated and gives none (attached flow would add a negative force there and a yaw moment real cars do not show).
  Howell and Panigrahi (SAE 2016-01-1620) find notchbacks below slender-wing theory, so the band takes 0.5–1.0 of it;
- **crossflow drag** on the side area, q sin²β C_d h(x) (Allen and Perkins).
The force and moment go into the plant's single-track Corolla (opendbc mass, axles, neutral steer) to give the
steering-equivalent lateral push: the lateral acceleration the controller must add to hold a straight line, which is
what `plant/straight_drift.py` adds as its push.

    python3 crosswind.py --figures
    python3 crosswind.py --check

Steady wind, square to the road; gusts and the car's own motion are not modelled. Textbook models on an artist's mesh:
a band, not a measurement. Synthetic (DSR-12), design aid, no evidence credit.
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
from matplotlib.path import Path as MPath

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
GEOM = SIM / "figures" / "corolla-e210-geometry.json"
DRIFT = SIM / "results" / "straight-drift.md"
HELPERS = SIM.parents[1] / "openpilot" / "selfdrive" / "controls" / "lib" / "drive_helpers.py"
OUT_JSON = SIM / "results" / "crosswind.json"
OUT_MD = SIM / "results" / "crosswind.md"
G = 9.81
DX = 0.01


def corolla() -> dict:
  sys.path.insert(0, str(SIM / "plant"))
  import corolla as c
  return c.as_dict()


def profile(geom: dict) -> dict:
  """Top and bottom of the side elevation along x (m, x forward), by sampling the body polygon."""
  poly = MPath(np.array(geom["side_elevation"]["body"][0]))
  xs = np.arange(-2.35, 2.36, DX)
  ys = np.arange(0.0, 1.6, 0.005)
  X, Y = np.meshgrid(xs, ys)
  inside = poly.contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(Y.shape)
  has = inside.any(axis=0)
  top = np.where(has, np.where(inside, Y, -1).max(axis=0), 0.0)
  bot = np.where(has, np.where(inside, Y, 9).min(axis=0), 0.0)
  wheels = [np.array(w).mean(0) for w in geom["side_elevation"]["wheels"]]
  front, rear = max(w[0] for w in wheels), min(w[0] for w in wheels)
  return {"x": xs[has], "top": top[has], "bottom": bot[has], "front_axle_x": front, "rear_axle_x": rear}


def loads(prof: dict, x_cg: float, beta: float, q: float, cd: float, k_pot: float = 1.0):
  """Side force (N, + downwind) and yaw moment about the CoG (N m, + nose downwind), and the force per unit length."""
  x, h = prof["x"], prof["top"]
  dh2 = np.gradient(h ** 2, x)                      # x forward: the flow meets the nose first (high x)
  pot = k_pot * np.maximum(-q * beta * math.pi * dh2, 0.0)   # grows aft from the nose; separated where it falls
  cross = q * math.sin(beta) ** 2 * cd * (h - prof["bottom"])
  dY = pot + cross
  Y = float(np.sum(dY) * DX)
  N = float(np.sum(dY * (x - x_cg)) * DX)
  return Y, N, dY


def push(Y: float, N: float, v: float, c: dict) -> float:
  """Steering-equivalent lateral push (m/s²): the still-air lateral acceleration of the steer angle that holds a
  straight line against Y and N. Single-track, neutral steer (equal normalised cornering stiffness front and rear)."""
  m, L, a, b, cs = c["m"], c["L"], c["a"], c["b"], c["C_S"]
  Cf, Cr = cs * m * G * b / L, cs * m * G * a / L
  Fyf = (-Y * b - N) / L
  Fyr = (-Y * a + N) / L
  delta = Fyf / Cf - Fyr / Cr
  return abs(v ** 2 * delta / L)


def drift_table() -> dict:
  """Time to the 3.7 m lane line after a silent assist loss, by push, from the plant's straight-drift page (F-04b)."""
  txt = DRIFT.read_text(encoding="utf-8")
  sec = txt.split("## F-04b")[1].split("## ")[0]
  out = {}
  for row in re.findall(r"^\| ([\d.]+) m/s² \|(.+)$", sec, re.M):
    cells = [c.strip() for c in row[1].split("|")]
    out[f"{float(row[0]):.1f}"] = cells[4]              # string keys: they survive the JSON round trip
  return out


def run(p: dict) -> dict:
  cw = p["crosswind"]
  geom = json.loads(GEOM.read_text(encoding="utf-8"))
  c = corolla()
  prof = profile(geom)
  x_cg = prof["front_axle_x"] - c["a"]
  limit = float(re.search(r"MAX_LATERAL_ACCEL_NO_ROLL = ([\d.]+)", HELPERS.read_text(encoding="utf-8")).group(1))
  rho, cd = cw["air_density"]["value"], cw["crossflow_cd"]
  rows = {}
  for kph in cw["speeds_kph"]:
    v = kph / 3.6
    r = {"wind": cw["wind_m_s"], "upper": [], "lower": [], "beta_deg": [], "Y_upper": [], "N_upper": []}
    for w in cw["wind_m_s"]:
      beta = math.atan2(w, v)
      q = 0.5 * rho * (v * v + w * w)
      kp = cw["potential_factor"]
      Yu, Nu, _ = loads(prof, x_cg, beta, q, cd["high"], kp["high"])
      Yl, Nl, _ = loads(prof, x_cg, beta, q, cd["low"], kp["low"])
      r["upper"].append(round(push(Yu, Nu, v, c), 3))
      r["lower"].append(round(push(Yl, Nl, v, c), 3))
      r["beta_deg"].append(round(math.degrees(beta), 1))
      r["Y_upper"].append(round(Yu, 1)); r["N_upper"].append(round(Nu, 1))
    w = np.array(cw["wind_m_s"], float)
    r["wind_at_margin"] = round(float(np.interp(cw["odd_margin_m_s2"]["value"], r["upper"], w)), 1)
    r["wind_at_limit"] = None if max(r["upper"]) < limit else round(float(np.interp(limit, r["upper"], w)), 1)
    ks = cw["ks02_wind_kph"]["value"] / 3.6
    r["push_at_ks02"] = [round(float(np.interp(ks, w, r["lower"])), 2), round(float(np.interp(ks, w, r["upper"])), 2)]
    rows[str(kph)] = r
  v = max(cw["speeds_kph"]) / 3.6
  beta = math.atan2(cw["ks02_wind_kph"]["value"] / 3.6, v)
  q = 0.5 * rho * (v * v + (cw["ks02_wind_kph"]["value"] / 3.6) ** 2)
  Y, N, dY = loads(prof, x_cg, beta, q, cd["value"], cw["potential_factor"]["value"])
  # per-degree coefficients at 5° on frontal area and wheelbase, the form published car data use
  af = float(geom["frontal_area_m2"]) if "frontal_area_m2" in geom else None
  b5 = math.radians(5.0)
  Y5, N5, _ = loads(prof, x_cg, b5, 1.0, cd["value"], cw["potential_factor"]["value"])
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. Textbook models on the mesh's side elevation.",
          "controller_limit_m_s2": limit, "odd_margin_m_s2": cw["odd_margin_m_s2"]["value"],
          "wheelbase_mesh_m": round(prof["front_axle_x"] - prof["rear_axle_x"], 3), "wheelbase_opendbc_m": c["L"],
          "x_cg_m": round(x_cg, 3), "cp_m": round(x_cg + N / Y, 3) if Y else None,
          "coefficients_per_deg": None if af is None else
            {"frontal_area_m2": af, "C_Y": round(Y5 / af / 5.0, 4), "C_N": round(N5 / (af * c["L"]) / 5.0, 4)},
          "distribution_110_ks02": {"x": [round(float(v), 2) for v in prof["x"][::5]],
                                    "dY": [round(float(v), 2) for v in dY[::5]],
                                    "top": [round(float(v), 3) for v in prof["top"][::5]]},
          "speeds": rows, "drift_3p7_by_push": drift_table(), "beaufort": cw["beaufort"]}


def markdown(r: dict, p: dict) -> str:
  cw = p["crosswind"]
  ks = cw["ks02_wind_kph"]["value"]
  L = [
    "# Crosswind: how hard a side wind pushes the Corolla, against the steering margin",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit.** Generated by "
    "[`weather/crosswind.py`](../weather/crosswind.py) from the side elevation measured on the Corolla mesh "
    "([`corolla-e210-geometry.json`](../figures/corolla-e210-geometry.json)) and the plant's Corolla; do not edit by "
    "hand. **Textbook models** (slender-body side force, crossflow drag) on an artist's mesh: a band, not a measurement. "
    "Steady wind square to the road; gusts are not modelled.",
    "",
    f"The push is steering-equivalent: the lateral acceleration the controller must add to hold a straight line, as "
    f"the plant's straight-drift study adds it. Margins: the ODD keeps **{r['odd_margin_m_s2']} m/s²** for controller "
    f"error, road crown and wind (WP-C-02 §3.2); the controller's limit is **{r['controller_limit_m_s2']} m/s²** "
    f"(`drive_helpers.py`). Wheelbase on the mesh {r['wheelbase_mesh_m']} m against opendbc's {r['wheelbase_opendbc_m']} m; "
    f"centre of pressure at {r['cp_m']} m against the CoG at {r['x_cg_m']} m (x forward): ahead of the CoG, so the wind "
    "also turns the nose away from it.",
    "",
    "| Wind | " + " | ".join(f"Push at {float(k):.0f} km/h (lower – upper)" for k in r["speeds"]) + " |",
    "|---|" + "---|" * len(r["speeds"]),
  ]
  first = next(iter(r["speeds"].values()))
  for i, w in enumerate(first["wind"]):
    L.append(f"| {w} m/s ({w * 3.6:.0f} km/h) | " + " | ".join(
      f"{d['lower'][i]:.2f} – {d['upper'][i]:.2f} m/s²" for d in r["speeds"].values()) + " |")
  L += ["", "## Against the margins", "",
        "| Speed | Push in the KS-02 wind (" + f"{ks:.0f} km/h) | Wind that uses up the ODD's 0.5 m/s² | Wind that reaches the controller limit |",
        "|---|---|---|---|"]
  for k, d in r["speeds"].items():
    lim = "beyond 25 m/s" if d["wind_at_limit"] is None else f"{d['wind_at_limit']} m/s ({d['wind_at_limit'] * 3.6:.0f} km/h)"
    L.append(f"| {float(k):.0f} km/h | {d['push_at_ks02'][0]} – {d['push_at_ks02'][1]} m/s² | "
             f"{d['wind_at_margin']} m/s ({d['wind_at_margin'] * 3.6:.0f} km/h) | {lim} |")
  hi = r["speeds"][str(max(float(k) for k in r["speeds"]))]
  L += ["", "## What this shows (generated)", "",
        f"- The KS-02 wind ({ks:.0f} km/h) pushes the Corolla at 110 km/h with {hi['push_at_ks02'][0]}–"
        f"{hi['push_at_ks02'][1]} m/s²: {'within' if hi['push_at_ks02'][1] <= r['odd_margin_m_s2'] else 'beyond'} the "
        f"ODD's {r['odd_margin_m_s2']} m/s² margin.",
        f"- The upper estimate uses the whole margin from {hi['wind_at_margin']} m/s ({hi['wind_at_margin'] * 3.6:.0f} km/h) "
        f"of wind at 110 km/h; Beaufort 7 (near gale) starts at {r['beaufort']['7 near gale']} m/s.",
        "- With assist lost silently, the plant's straight-drift page gives the time to the 3.7 m lane line for these "
        "pushes (F-04b, 80–110 km/h): " + "; ".join(f"{k} m/s²: {v}" for k, v in r["drift_3p7_by_push"].items()
                                                     if float(k) > 0) + ".",
        "- Gusts are stronger than the steady wind and arrive in a second; they are the next step (a gust profile into "
        "the plant), together with a measurement on a windy day.", ""]
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
    print("crosswind:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, {k: (d["push_at_ks02"], d["wind_at_margin"], d["wind_at_limit"]) for k, d in r["speeds"].items()},
        "cp", r["cp_m"], "cg", r["x_cg_m"])
  if a.figures:
    import fig_weather
    fig_weather.crosswind_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
