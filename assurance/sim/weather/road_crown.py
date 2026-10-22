#!/usr/bin/env python3
"""Road crown and bank while engaged (WP-C-06 TC-15, WP-V-03 KS-02, WP-C-02 §3.2): the push left over after
openpilot's roll compensation, against the 0.5 m/s² curve margin.

A cross slope θ pushes the car downhill by g·sin θ. openpilot's torque controller takes it off what it commands:
`roll_compensation = params.roll * g` (`latcontrol_torque.py`), with the road roll estimated by paramsd's Kalman
filter from the localizer's roll of the device (`paramsd.py`, `car_kf.py`). What is left over:
- **the filter's lag** when the slope changes, as in a lane change across a crown line: the steady-state Kalman gain
  of the code's process noise and the localizer's roll noise gives the time constant;
- **the device's mount roll**: calibration takes it as zero (`calibrationd.py`), so it enters the roll estimate as a
  bias until torqued learns `latAccelOffset`;
- **body roll**: the device sees the body lean as road roll. Proportional to the lateral force, it is absorbed by the
  fitted torque gain (torqued fits on the same roll, `torqued.py`); only this car's difference from the fit is left;
- **the fallback**: when the localizer's roll is invalid, paramsd observes zero roll and the estimate decays to 0, so
  the whole g·sin θ comes back.
Writes `../results/road-crown.json` and `.md`.

    python3 road_crown.py --figures
    python3 road_crown.py --check

Steady pushes and errors are compared with the margin; a brief error is given with the sideways speed it builds up
before any correction. Synthetic (DSR-12), design aid, no evidence credit (DQ-413).
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
OP = ROOT / "openpilot"
OUT_JSON = SIM / "results" / "road-crown.json"
OUT_MD = SIM / "results" / "road-crown.md"
CROSSWIND = SIM / "results" / "crosswind.json"


def code() -> dict:
  """The constants of the roll path, read from the openpilot source at the baseline."""
  rt = (OP / "common" / "realtime.py").read_text(encoding="utf-8")
  kf = (OP / "selfdrive" / "locationd" / "models" / "car_kf.py").read_text(encoding="utf-8")
  pd_ = (OP / "selfdrive" / "locationd" / "paramsd.py").read_text(encoding="utf-8")
  lt = (OP / "selfdrive" / "controls" / "lib" / "latcontrol_torque.py").read_text(encoding="utf-8")
  cal = (OP / "selfdrive" / "locationd" / "calibrationd.py").read_text(encoding="utf-8")
  const = (OP / "common" / "constants.py").read_text(encoding="utf-8")
  states = re.search(r"class States:(.*?)\nclass ", kf, re.S).group(1)
  order = re.findall(r"^\s+(\w+) = _slice\((\d)\)", states, re.M)
  idx = sum(int(n) for name, n in order[:[o[0] for o in order].index("ROAD_ROLL")])
  q_block = re.search(r"Q = np\.diag\(\[(.*?)\]\)", kf, re.S).group(1)
  q_terms = [t.strip() for t in q_block.replace("\n", " ").split(",") if t.strip()]
  q_roll = q_terms[idx]
  m = re.fullmatch(r"math\.radians\(([\d.]+)\)\*\*2", q_roll)
  out = {
    "dt": float(re.search(r"DT_MDL = ([\d.]+)", rt).group(1)),
    "q_roll_deg": float(m.group(1)),
    "obs_std_factor": float(re.search(r"roll_std = (\d+) \* localizer_roll_std", pd_).group(1)),
    "invalid_std_deg": float(re.search(r"^\s+roll_std = np\.radians\(([\d.]+)\)", pd_, re.M).group(1)),
    "roll_std_max_deg": float(re.search(r"ROLL_STD_MAX = np\.radians\(([\d.]+)\)", pd_).group(1)),
    "g": float(re.search(r"ACCELERATION_DUE_TO_GRAVITY = ([\d.]+)", const).group(1)),
    "compensates": bool(re.search(r"roll_compensation = params\.roll \* ACCELERATION_DUE_TO_GRAVITY", lt)),
    "calibration_roll_zero": "here we assume it's zero" in cal,
  }
  return out


def kalman_gain(q_rad2_s: float, r_rad2: float, dt: float) -> float:
  """Steady-state gain of the scalar random-walk filter (P += dt·Q, then the update), as paramsd runs it."""
  P = q_rad2_s * dt
  for _ in range(10000):
    Pm = P + q_rad2_s * dt
    K = Pm / (Pm + r_rad2)
    P_new = (1 - K) * Pm
    if abs(P_new - P) < 1e-18:
      break
    P = P_new
  return K


def tau(K: float, dt: float) -> float:
  return -dt / math.log(1 - K)


def track(K: float, dt: float, truth: np.ndarray, start: float) -> np.ndarray:
  est = np.empty_like(truth)
  x = start
  for i, z in enumerate(truth):
    x = x + K * (z - x)
    est[i] = x
  return est


def speed_error(a: np.ndarray, dt: float) -> float:
  """The lateral speed (m/s) an acceleration error builds up while it lasts, before any correction."""
  return float(np.abs(np.cumsum(a) * dt).max())


def crown_flip(c: dict, p: dict, sigma_deg: float) -> dict:
  """A lane change across a crown line: the slope goes from +s to −s while the car crosses it."""
  cr, w = p["crown"], p["water"]["cross_slope_pct"]
  dt = c["dt"]
  K = kalman_gain(math.radians(c["q_roll_deg"]) ** 2, (c["obs_std_factor"] * math.radians(sigma_deg)) ** 2, dt)
  s = w["value"] / 100
  t = np.arange(0, 6.0, dt)
  ramp = np.clip((t - 1.0) / cr["crown_change_s"]["value"], 0, 1)
  theta = np.arctan(s) * (1 - 2 * ramp)
  est = track(K, dt, theta, float(theta[0]))
  err = c["g"] * (np.sin(theta) - est)
  return {"tau_s": round(tau(K, dt), 3), "peak": round(float(np.abs(err).max()), 3),
          "speed_m_s": round(speed_error(err, dt), 3),
          "t": [round(float(x), 2) for x in t], "truth_deg": [round(math.degrees(x), 3) for x in theta],
          "est_deg": [round(math.degrees(x), 3) for x in est]}


def run(p: dict) -> dict:
  c = code()
  cr, w = p["crown"], p["water"]["cross_slope_pct"]
  g = c["g"]
  def push(pct):
    return g * math.sin(math.atan(pct / 100))
  sig = cr["localizer_roll_std_deg"]
  flips = {k: crown_flip(c, p, sig[k]) for k in ("low", "value", "high")}
  k_inv = kalman_gain(math.radians(c["q_roll_deg"]) ** 2, math.radians(c["invalid_std_deg"]) ** 2, c["dt"])
  rg = cr["roll_gradient_deg_g"]
  mism = math.radians(rg["high"]) * cr["gradient_mismatch"]["value"]
  mount = {k: round(g * math.sin(math.radians(cr["mount_roll_deg"][k])), 3) for k in ("low", "value", "high")}
  cw = json.loads(CROSSWIND.read_text(encoding="utf-8"))
  wind = cw["speeds"]["110.0"]["push_at_ks02"]
  margin = cw["odd_margin_m_s2"]
  rows = [
    {"what": "crown", "uncompensated": [round(push(w["low"]), 3), round(push(w["high"]), 3)]},
    {"what": "bank", "uncompensated": [round(push(cr["bank_pct"]["low"]), 3), round(push(cr["bank_pct"]["high"]), 3)]},
  ]
  return {
    "about": "Synthetic (DSR-12), design aid, no evidence credit. openpilot's roll path read from the code; car and "
             "localizer inputs estimated.",
    "code": c, "margin_m_s2": margin, "slopes": rows,
    "residual": {
      "flip_peak": [flips["low"]["peak"], flips["high"]["peak"]],
      "flip_speed_m_s": [flips["low"]["speed_m_s"], flips["high"]["speed_m_s"]],
      "tau_s": [flips["low"]["tau_s"], flips["high"]["tau_s"]],
      "gradient_mismatch_crown": round(mism * push(w["high"]), 4),
      "gradient_mismatch_bank": round(mism * push(cr["bank_pct"]["high"]), 4),
      "mount": mount,
      "fallback_tau_s": round(tau(k_inv, c["dt"]), 2),
    },
    "flip_nominal": flips["value"],
    "crosswind_ks02": wind,
  }


def markdown(r: dict, p: dict) -> str:
  s, res, c, m = r["slopes"], r["residual"], r["code"], r["margin_m_s2"]
  crown, bank = s[0]["uncompensated"], s[1]["uncompensated"]
  mt = res["mount"]
  cr = p["crown"]
  L = [
    "# Road crown and bank while engaged: what is left after roll compensation",
    "",
    "> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** Generated by "
    "[`weather/road_crown.py`](../weather/road_crown.py) from [`params.yaml`](../weather/params.yaml) and the "
    "openpilot source; do not edit by hand. The roll path's constants are the code's; the car's and the localizer's "
    "are estimates.",
    "",
    f"At {cr['speed_kph']:.0f} km/h, against the {m} m/s² curve margin of WP-C-02 §3.2 (controller error and road "
    "crown). A cross slope pushes the car downhill by g·sin θ; openpilot subtracts `params.roll · g` from what it "
    "commands (`latcontrol_torque.py`), so only the error in its roll estimate is left.",
    "",
    "| Source | Lateral push or error, m/s² | Lasts | Against the margin |",
    "|---|---|---|---|",
    f"| Crown {p['water']['cross_slope_pct']['low']:.1f}–{p['water']['cross_slope_pct']['high']:.1f} %, not compensated | "
    f"{crown[0]:.2f}–{crown[1]:.2f} | while on it | removed by the compensation |",
    f"| Bank {cr['bank_pct']['low']:.0f}–{cr['bank_pct']['high']:.0f} % (KS-02), not compensated | {bank[0]:.2f}–"
    f"{bank[1]:.2f} | while on it | |",
    f"| Filter lag, lane change across a crown line | peak {res['flip_peak'][0]:.2f}–{res['flip_peak'][1]:.2f} | "
    f"time constant {res['tau_s'][0]:.2f}–{res['tau_s'][1]:.2f} s | leaves a sideways speed of "
    f"{100 * res['flip_speed_m_s'][0]:.0f}–{100 * res['flip_speed_m_s'][1]:.0f} cm/s to correct |",
    f"| Body roll: this car against the fitted gain (±{100 * cr['gradient_mismatch']['value']:.0f} %) | "
    f"{res['gradient_mismatch_crown']:.3f} (crown), {res['gradient_mismatch_bank']:.3f} (6 % bank) | while on it | "
    "negligible |",
    f"| Device mount roll {cr['mount_roll_deg']['value']:.0f}° (up to {cr['mount_roll_deg']['high']:.0f}°) | "
    f"{mt['value']:.2f} (up to {mt['high']:.2f}) | until torqued learns its offset | "
    f"{100 * mt['value'] / m:.0f} % of it (up to {100 * mt['high'] / m:.0f} %) |",
    f"| Roll invalid: the estimate decays to 0 | the whole push: crown {crown[1]:.2f}, bank {bank[1]:.2f} | from "
    f"{res['fallback_tau_s']:.1f} s on, while invalid | {'over' if bank[1] > m else 'within'} it on a "
    f"{cr['bank_pct']['high']:.0f} % bank |",
    f"| For comparison: crosswind 30 km/h (KS-02, crosswind study) | {r['crosswind_ks02'][0]:.2f}–"
    f"{r['crosswind_ks02'][1]:.2f} | | not covered (DQ-415) |",
    "",
    "## What this shows (generated)",
    "",
    f"- With a valid roll estimate the crown itself is taken out: the filter follows a crown change with a "
    f"{res['tau_s'][0]:.2f}–{res['tau_s'][1]:.2f} s time constant (the code's process noise, "
    f"{c['q_roll_deg']:.0f}°/√s, against the localizer's roll noise); the error peaks at "
    f"{res['flip_peak'][1]:.2f} m/s² and leaves at most {100 * res['flip_speed_m_s'][1]:.0f} cm/s of sideways speed, "
    "a small, brief disturbance for the lateral control.",
    f"- Body roll is taken out by the fitted torque gain; what is left is under {res['gradient_mismatch_bank']:.2f} m/s².",
    f"- **The device's mount roll is the largest crown-related term.** Calibration takes it as zero, so a "
    f"{cr['mount_roll_deg']['value']:.0f}° tilt is {mt['value']:.2f} m/s² ({100 * mt['value'] / m:.0f} % of the "
    "margin) until torqued learns `latAccelOffset`, which starts from its default after a fresh install or a "
    "parameter reset. A level at installation measures it (an INS check and T1).",
    f"- **When the roll estimate is invalid** (localizer roll noise above {c['roll_std_max_deg']:.1f}°, roll out of "
    f"range, sensors not OK) paramsd observes zero roll and the estimate decays within about "
    f"{3 * res['fallback_tau_s']:.0f} s: the whole push returns, {crown[1]:.2f} m/s² on a crown and {bank[1]:.2f} on a "
    f"{cr['bank_pct']['high']:.0f} % bank, {'more than' if bank[1] > m else 'within'} the margin. How often roll is "
    "invalid on the highway is a question for local logs (`liveParameters` roll and its standard deviation).",
    "- So the 0.5 m/s² margin covers crown while the roll estimate is valid and the mount offset is learned; it does "
    "not cover a steep bank with roll invalid, nor a crosswind (DQ-415).",
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
  md = markdown(r, p)
  if a.check:
    from sun_glare import compare
    errs = compare(r, json.loads(OUT_JSON.read_text(encoding="utf-8")))
    if not errs and OUT_MD.read_text(encoding="utf-8") != md:
      errs.append(f"{OUT_MD.name} is stale")
    for e in errs[:20]:
      print("FAIL", e)
    print("road crown:", "OK" if not errs else f"{len(errs)} difference(s)")
    return 1 if errs else 0
  OUT_JSON.write_text(json.dumps(r, separators=(",", ":")) + "\n", encoding="utf-8")
  OUT_MD.write_text(md, encoding="utf-8")
  print("wrote", OUT_JSON.name, OUT_MD.name, r["slopes"], r["residual"])
  if a.figures:
    import fig_weather
    fig_weather.crown_figures(p, r, HERE / "figures")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
