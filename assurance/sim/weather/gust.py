#!/usr/bin/env python3
"""A crosswind gust through the Corolla and its lane keeping (WP-C-06 TC-15, WP-V-03 KS-02, DQ-415).

The crosswind study gave the steady push of a side wind. Here the wind changes in time. The side force and yaw
moment come from the crosswind study's loads on the measured side elevation (`crosswind.py`), quasi-steady. They act
on a linear single-track Corolla, the plant's car: opendbc mass, axles and inertia; cornering stiffness as in the
crosswind push. The car is steered by the plant's perfect-perception lane keeping:
- the control law of `plant/simulate.py` (a_des = -k_y e_y - k_psi v sin e_psi), read from that file;
- 100 Hz frames, through opendbc's own torque limiter (`apply_dist_to_meas_limits`, executed from
  `opendbc/car/lateral.py`) with the Corolla's limits (`toyota/values.py`);
- an EPS that follows the torque with the first-order lag `steerActuatorDelay`, as the plant has it.
Two gust shapes at the KS-02 wind: a step (leaving a cutting or a bridge) and one-minus-cosine gusts of 0.5 to 8 s.
Writes `../results/gust.json` and `.md`.

    python3 gust.py --figures
    python3 gust.py --check

The lane keeping is the plant's stand-in for openpilot, with perfect perception and no driver: it tells how the
loop answers a gust, not how openpilot's planner does. Synthetic (DSR-12), design aid, no evidence credit.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crosswind as cw  # noqa: E402

SIM = HERE.parent
ROOT = SIM.parents[1]
SIMULATE = SIM / "plant" / "simulate.py"
LATERAL = ROOT / "opendbc_repo" / "opendbc" / "car" / "lateral.py"
TOYOTA = ROOT / "opendbc_repo" / "opendbc" / "car" / "toyota" / "values.py"
OUT_JSON = SIM / "results" / "gust.json"
OUT_MD = SIM / "results" / "gust.md"
G = 9.81
DT = 0.005          # dynamics step, as the plant's DYN_EVERY
FRAME = 0.01        # 100 Hz steering frames


def code() -> dict:
  """The lane keeping's law and the torque limits, read from the plant and opendbc sources."""
  sim = SIMULATE.read_text(encoding="utf-8")
  m = re.search(r"a_des = v \* v \* kappa - ([\d.]+) \* e_y - ([\d.]+) \* v \* math\.sin\(e_psi\)", sim)
  tv = TOYOTA.read_text(encoding="utf-8")
  torque_branch = re.search(r"if CP\.lateralTuning\.which\(\) == 'torque':\s*\n\s*self\.STEER_DELTA_UP = (\d+).*\n\s*self\.STEER_DELTA_DOWN = (\d+)", tv)
  src = LATERAL.read_text(encoding="utf-8")
  fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "apply_dist_to_meas_limits")
  ns = {"np": np}
  exec(compile(ast.Module([fn], []), str(LATERAL), "exec"), ns)  # opendbc's function, unchanged
  return {"k_y": float(m.group(1)), "k_psi": float(m.group(2)),
          "steer_max": int(re.search(r"STEER_MAX = (\d+)", tv).group(1)),
          "steer_error_max": int(re.search(r"STEER_ERROR_MAX = (\d+)", tv).group(1)),
          "delta_up": int(torque_branch.group(1)), "delta_down": int(torque_branch.group(2)),
          "limiter": ns["apply_dist_to_meas_limits"]}


def stiffness(c: dict) -> tuple[float, float]:
  """Front and rear cornering stiffness (N/rad), as the crosswind push takes them."""
  return c["C_S"] * c["m"] * G * c["b"] / c["L"], c["C_S"] * c["m"] * G * c["a"] / c["L"]


def wind_profile(kind: str, w0: float, t: np.ndarray, v: float, length: float, period: float = 0.0) -> np.ndarray:
  if kind == "step":
    return w0 * np.clip((t - 1.0) / (length / v), 0, 1)
  return np.where((t >= 1.0) & (t <= 1.0 + period), w0 * 0.5 * (1 - np.cos(2 * math.pi * (t - 1.0) / period)), 0.0)


def simulate(c: dict, k: dict, v: float, Y: np.ndarray, N: np.ndarray, t: np.ndarray, controller: bool = True,
             delta_open: float = 0.0, feedforward: np.ndarray | None = None) -> dict:
  """Single-track car (beta, r, psi, y) under side force Y and yaw moment N (both toward +y), at speed v.
  feedforward: a lateral acceleration added to the lane keeping's demand (the gust's own push, known exactly)."""
  m, Iz, a, b, L = c["m"], c["I_z"], c["a"], c["b"], c["L"]
  Cf, Cr = stiffness(c)
  beta = r = psi = y = 0.0
  torque = eps = 0.0                      # commanded and applied (EPS) torque
  tau, laf = c["tau_eps"], c["lat_accel_factor"]
  out = {"y": [], "a_eps": [], "ay": []}
  next_frame = 0.0
  for i, ti in enumerate(t):
    if controller and ti >= next_frame - 1e-12:
      a_des = -k["k_y"] * y - k["k_psi"] * v * math.sin(psi)
      if feedforward is not None:
        a_des += feedforward[i]
      new = int(round(max(-1.0, min(1.0, a_des / laf)) * k["steer_max"]))
      torque = int(round(k["limiter"](new, torque, eps, k["delta_up"], k["delta_down"], k["steer_error_max"], k["steer_max"])))
      next_frame += FRAME
    eps += (torque - eps) * min(DT / tau, 1.0)
    a_eps = laf * eps / k["steer_max"]
    delta = (L * a_eps / v ** 2) if controller else delta_open   # neutral steer, as the push mapping
    def f(s, delta=delta, yw=Y[i], nw=N[i]):
      be, rr = s
      Fyf = Cf * (delta - be - a * rr / v)
      Fyr = Cr * (-be + b * rr / v)
      return np.array([(Fyf + Fyr + yw) / (m * v) - rr, (a * Fyf - b * Fyr + nw) / Iz])
    s = np.array([beta, r])
    k1 = f(s); k2 = f(s + DT / 2 * k1); k3 = f(s + DT / 2 * k2); k4 = f(s + DT * k3)
    beta, r = s + DT / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    y += v * math.sin(psi + beta) * DT
    psi += r * DT
    out["y"].append(y); out["a_eps"].append(a_eps); out["ay"].append(v * (r + (beta - s[0]) / DT))
  return {k_: np.array(v_) for k_, v_ in out.items()} | {"r": r, "beta": beta}


def loads_series(p: dict, prof: dict, x_cg: float, v: float, w: np.ndarray, edge: str) -> tuple[np.ndarray, np.ndarray]:
  c = p["crosswind"]
  cd = c["crossflow_cd"][edge]
  kp = c["potential_factor"][edge]
  Y, N = np.zeros_like(w), np.zeros_like(w)
  for i, wi in enumerate(w):
    if wi > 0:
      beta = math.atan2(wi, v)
      q = 0.5 * c["air_density"]["value"] * (v * v + wi * wi)
      Y[i], N[i], _ = cw.loads(prof, x_cg, beta, q, cd, kp)
  return Y, N


def run(p: dict) -> dict:
  g = p["gust"]
  c = cw.corolla()
  k = code()
  geom = json.loads(cw.GEOM.read_text(encoding="utf-8"))
  prof = cw.profile(geom)
  x_cg = prof["front_axle_x"] - c["a"]
  length = geom["extent_m"]["length"]
  v = g["speed_kph"] / 3.6
  w0 = g["wind_kph"]["value"] / 3.6
  t = np.arange(0, g["duration_s"], DT)
  lane, narrow = g["lane_width_m"]["value"], g["lane_width_m"]["narrow"]
  room = {"lane": (lane - c["width"]) / 2, "narrow": (narrow - c["width"]) / 2}
  cases = [("step", 0.0)] + [("cosine", T) for T in g["cosine_periods_s"]["value"]]
  rows, traces = [], {}
  for kind, T in cases:
    w = wind_profile(kind, w0, t, v, length, T)
    row = {"kind": kind, "period_s": T}
    for edge in ("low", "high"):
      Y, N = loads_series(p, prof, x_cg, v, w, edge)
      # the push that holds a straight line against these loads (crosswind.push), signed toward the wind
      ff = np.array([-math.copysign(cw.push(yy, nn, v, c), yy) if yy else 0.0 for yy, nn in zip(Y, N, strict=True)])
      for mode, kw in (("feedback", {}), ("ideal", {"feedforward": ff})):
        res = simulate(c, k, v, Y, N, t, **kw)
        i = int(np.argmax(np.abs(res["y"])))
        row[f"{mode}_{edge}"] = {"peak_m": round(float(abs(res["y"][i])), 3), "at_s": round(float(t[i] - 1.0), 2),
                                 "a_eps_max": round(float(np.abs(res["a_eps"]).max()), 3),
                                 "saturated": bool(np.abs(res["a_eps"]).max() >= 0.999 * c["lat_accel_factor"])}
        if mode == "ideal" and (kind == "step" or edge == "high"):
          traces[f"{mode}-{edge}-{kind}-{T:g}"] = {"y": [round(float(x), 4) for x in res["y"][::10]],
                                                   "w": [round(float(x), 3) for x in w[::10]]}
      row["push_max"] = round(float(np.abs(ff).max()), 3) if edge == "high" else row.get("push_max")
    rows.append(row)
  worst = max(rows, key=lambda r_: r_["ideal_high"]["peak_m"])
  return {"about": "Synthetic (DSR-12), design aid, no evidence credit. Textbook loads on the mesh outline; the "
                   "plant's perfect-perception lane keeping.",
          "code": {k_: v_ for k_, v_ in k.items() if k_ != "limiter"}, "speed_kph": g["speed_kph"],
          "wind_kph": g["wind_kph"]["value"], "room_m": {k_: round(v_, 3) for k_, v_ in room.items()},
          "eps_max_m_s2": round(c["lat_accel_factor"], 3), "rows": rows,
          "worst": {"kind": worst["kind"], "period_s": worst["period_s"], "peak_m": worst["ideal_high"]["peak_m"]},
          "t_s": [round(float(x), 2) for x in t[::10]], "traces": traces}


def label(r_):
  return "step (leaving shelter)" if r_["kind"] == "step" else f"gust {r_['period_s']:g} s"


def markdown(r: dict) -> str:
  room, eps_max = r["room_m"], r["eps_max_m_s2"]
  rows = r["rows"]
  step = next(x for x in rows if x["kind"] == "step")
  gusts = [x for x in rows if x["kind"] != "step"]
  def cm(x):
    return f"{100 * x:.0f}"
  L = [
    "# A crosswind gust through the Corolla and its lane keeping",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/gust.py`](../weather/gust.py) from [`params.yaml`](../weather/params.yaml), the crosswind study's loads "
    "and the plant's lane keeping; do not edit by hand. Textbook loads on an artist's mesh; perfect perception, no "
    "driver.",
    "",
    f"At {r['speed_kph']:.0f} km/h, the wind rising to {r['wind_kph']:.0f} km/h square to the road (KS-02). The car's "
    f"body has {cm(room['lane'])} cm of room to the line of a 3.7 m lane, {cm(room['narrow'])} cm in a 3.3 m lane. "
    f"The steering can give at most {eps_max:.2f} m/s² (opendbc's full torque times the Corolla's lateral "
    f"acceleration factor), rising at most {r['code']['delta_up']} torque units per 10 ms frame. Two kinds of lane "
    "keeping:",
    "",
    "- **Ideal steering**: it knows the gust's push exactly and adds it at once, on top of the plant's law; only the "
    "torque limiter and the EPS lag hold it back. A bound on what any lane keeping can do with this steering.",
    f"- **The plant's stand-in**: its law alone (a_des = −{r['code']['k_y']:g}·e_y − {r['code']['k_psi']:g}·v·sin e_psi, "
    "`plant/simulate.py`). It has no integral action, so a steady wind leaves it off the lane centre by the push "
    "divided by its gain, a property of the stand-in, not of openpilot.",
    "",
    "| Wind | Steady push, upper band | Peak movement, ideal steering (lower – upper band) | "
    "Peak movement, plant's stand-in (lower – upper) | Steering used, ideal, upper |",
    "|---|---|---|---|---|",
  ]
  for x in rows:
    il, ih, fl, fh = x["ideal_low"], x["ideal_high"], x["feedback_low"], x["feedback_high"]
    sat = " (at its limit)" if ih["saturated"] else ""
    L.append(f"| {label(x)} | {x['push_max']:.2f} m/s² | {cm(il['peak_m'])} – {cm(ih['peak_m'])} cm | "
             f"{cm(fl['peak_m'])} – {cm(fh['peak_m'])} cm | {ih['a_eps_max']:.2f} of {eps_max:.2f} m/s²{sat} |")
  gmax = max(x["ideal_high"]["peak_m"] for x in gusts)
  L += ["", "## What this shows (generated)", "",
        f"- **Gusts that come and go** ({gusts[0]['period_s']:g}–{gusts[-1]['period_s']:g} s): with ideal steering the "
        f"car moves at most {cm(gmax)} cm, {100 * gmax / room['lane']:.0f} % of the room in a 3.7 m lane. The steering's "
        "rise rate and lag are fast enough for these.",
        f"- **A step** (leaving a cutting or a bridge into the full wind): {cm(step['ideal_low']['peak_m'])} cm at the "
        f"lower load band, but **{cm(step['ideal_high']['peak_m'])} cm at the upper band**. There the steady push alone "
        f"({step['push_max']:.2f} m/s²) takes {100 * step['push_max'] / eps_max:.0f} % of the steering's "
        f"{eps_max:.2f} m/s², so little is left to bring the car back; even ideal steering leaves the lane.",
        "- So the question for the windy-day log (WP-C-02 OI-10) is not only how hard a 30 km/h wind pushes but how "
        "much steering is left: near the upper band the Corolla's torque authority, not the lane keeping, decides. "
        "This adds to DQ-415's finding that the curve margin does not cover crosswind.",
        "- The plant's stand-in moves further on long gusts because it has no integral action; openpilot plans its "
        "path back to the lane centre, so the ideal line is the better guide.",
        ""]
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
    print("gust:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name,
        [(label(x), x["ideal_low"]["peak_m"], x["ideal_high"]["peak_m"], x["feedback_high"]["peak_m"]) for x in r["rows"]])
  if a.figures:
    import fig_weather
    fig_weather.gust_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
