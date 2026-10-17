#!/usr/bin/env python3
"""Inputs of the reachability pilot (JuliaReach, assurance/sim/reach): the linearised L1 plant and sampled fault runs.

    python3 assurance/sim/reach/reach_inputs.py            # write model.json and samples.json
    python3 assurance/sim/reach/reach_inputs.py --check    # fail if the committed files differ from a fresh run

Case: straight road at 110 km/h (ODD-H bound, DQ-260), engaged, no driver. From t = 0 a faulty host sends any LKA
torque the panda passes; the question is how far the car can move laterally before the driver takes over.

model.json: the L1 plant (CommonRoad single-track Corolla, EPS lag, steering tracking) linearised numerically at
that speed, with the LKA command u (panda units) as its input:
    z = [y, psi, beta, r, delta, a_eps],   z' = A z + B u
The panda (Toyota TorqueMotorLimited, opendbc safety/modes/toyota.h) lets |u| grow by at most 15 per 10 ms frame
from the 0 the host sent before the fault, and lets it fall toward 0 in a single frame. So every command it passes
satisfies |u(t)| <= min(STEER_MAX, 15 + 1500 t): that envelope, not a rate limit on u, is what Julia uses.

samples.json: the same case run through the real L1 plant (nonlinear) with the real panda safety code in the loop,
for seeded random fault command sequences plus the two hard-over cases. The faulty host asks for anything inside the
range the panda allows. Kept: the envelope of lateral offset and heading over all runs; the same for the linear model
driven by the commands that reached the EPS (exact zero-order hold), which the reachable set must contain; the
linearisation error between the two; and the driver's correction time of the hard-over run.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PLANT = HERE.parent / "plant"
sys.path.insert(0, str(PLANT))
import corolla  # noqa: E402
from corolla import ROOT  # noqa: E402
from panda_loop import Panda  # noqa: E402
from plant import STEER_MAX, STEER_TRACK_S, CorollaPlant  # noqa: E402
from simulate import DT_US, DYN_EVERY, EPS_SCALE, SoC, _decode_steer  # noqa: E402
from simulate import A as assumption  # noqa: E402
from vehiclemodels.vehicle_dynamics_st import vehicle_dynamics_st  # noqa: E402

sys.path.insert(0, str(ROOT / "opendbc_repo"))
from opendbc.car.toyota import toyotacan  # noqa: E402

MODEL = HERE / "model.json"
SAMPLES = HERE / "samples.json"
SPEED_KPH = 110.0
HORIZON_S = 3.0          # fault onset to beyond the driver's correction (hard-over: drift cue 0.2 m + t_r 1.5 s)
GRID_S = 0.01            # output grid
RATE_UP = 15             # panda max_rate_up: units per 10 ms frame (modes/toyota.h)
RATE_DOWN = 25           # panda max_rate_down
TORQUE_ERROR = 350       # panda max_torque_error
FRAME_S = 0.01
N_RANDOM = 60
SEED = 20261016
T0 = 1.0                 # s: engaged and settled before the fault


def linearise(v: float) -> tuple[list[list[float]], list[list[float]]]:
  """A, B of z' = A z + B u by central differences of the L1 plant's vector field at straight driving."""
  d, p = corolla.as_dict(), corolla.commonroad_parameters()
  k_eps = d["lat_accel_factor"] / STEER_MAX          # lateral acceleration per LKA unit (plant.EPS)
  tau = d["tau_eps"]

  def f(z, u):
    y, psi, beta, r, delta, a = z
    delta_t = corolla.steer_for_lat_accel(a, v, d)
    x = [0.0, y, delta, v, psi, r, beta]
    dx = vehicle_dynamics_st(x, [(delta_t - delta) / STEER_TRACK_S, 0.0], p)
    return [dx[1], dx[4], dx[6], dx[5], dx[2], (k_eps * u - a) / tau]

  n, h = 6, 1e-6
  z0 = [0.0] * n
  A = [[0.0] * n for _ in range(n)]
  for j in range(n):
    zp, zm = list(z0), list(z0)
    zp[j] += h
    zm[j] -= h
    fp, fm = f(zp, 0.0), f(zm, 0.0)
    for i in range(n):
      A[i][j] = (fp[i] - fm[i]) / (2 * h)
  B = [[(a - b) / (2 * h)] for a, b in zip(f(z0, h), f(z0, -h), strict=True)]
  return A, B


def envelope(t: float) -> float:
  """Largest |u| the panda can pass at time t after the fault (from u = 0 before it)."""
  return min(STEER_MAX, RATE_UP * (math.floor(t / FRAME_S + 1e-9) + 1))


def run_fault(targets, v: float):
  """One run: engaged at zero torque until T0, then a faulty host steering toward `targets(t)` (units) as fast as the
  panda allows. Returns times from the fault, y and psi relative to the onset, and the commands the EPS applied."""
  d = corolla.as_dict()
  panda = Panda(reference=True)
  soc = SoC(d, panda.packer)
  plant = CorollaPlant(v, assumption("eps_release_s"), assumption("pcm_timeout_s"), d)
  last, cruise = 0, False
  out_t, out_y, out_psi, cmds = [], [], [], []
  y0 = psi0 = None
  n = int((T0 + HORIZON_S) * 1e6 / DT_US)
  for k in range(n + 1):
    t_us = k * DT_US
    t = t_us / 1e6
    panda.set_time(t_us)
    if t >= 0.2:
      cruise = True
    if k % 20 == 2:
      panda.rx("STEER_TORQUE_SENSOR", {"STEER_TORQUE_EPS": plant.eps_torque / EPS_SCALE * 100.0,
                                       "STEER_TORQUE_DRIVER": 0, "STEER_ANGLE": math.degrees(plant.x[2]) * d["steer_ratio"]})
    if k % 12 == 1:
      panda.rx("WHEEL_SPEEDS", {f"WHEEL_SPEED_{w}": v * 3.6 for w in ("FR", "FL", "RR", "RL")})
    if k % 30 == 4:
      panda.rx("PCM_CRUISE", {"CRUISE_ACTIVE": int(cruise), "GAS_RELEASED": 1})
      panda.rx("PCM_CRUISE_2", {"MAIN_ON": 1})
    if k % 25 == 7:
      panda.rx("BRAKE_MODULE", {"BRAKE_PRESSED": 0})
    if k % 40 == 9:
      panda.rx("EPS_STATUS", {"LKA_STATE": 5})
    if k % 10 == 0:
      frame = k // 10
      engaged = t >= 0.2
      want = int(round(targets(t - T0))) if t >= T0 else 0
      # the faulty host asks for its target, clipped to the range the panda allows (dist_to_meas_check)
      meas = plant.eps_torque
      hi = min(STEER_MAX, max(last, 0) + RATE_UP, max(last - RATE_DOWN, max(meas, 0) + TORQUE_ERROR))
      lo = max(-STEER_MAX, min(last, 0) - RATE_UP, min(last + RATE_DOWN, min(meas, 0) - TORQUE_ERROR))
      torque = max(lo, min(hi, want)) if engaged else 0
      addr, dat, bus = toyotacan.create_steer_command(panda.packer, torque, int(engaged))
      if panda.tx(addr, dat, bus):
        sent, req = _decode_steer(panda, dat)
        plant.lka_frame(t, sent, req)
        last = sent
      if frame % 3 == 0:
        addr, dat, bus = soc.accel_frame(engaged)
        if panda.tx(addr, dat, bus):
          plant.acc_frame(t, 0.0)
      if frame % 10 == 0:
        panda.heartbeat(engaged)
    panda.main_loop()
    if k % 10 == 3:
      panda.safety_task()
    if k % DYN_EVERY == 0:
      plant.step(t, DYN_EVERY * DT_US / 1e6)
      if t >= T0 - 1e-9:
        if y0 is None:
          y0, psi0 = plant.x[1], plant.x[4]
        tf = t - T0
        if abs(tf / GRID_S - round(tf / GRID_S)) < 1e-6:
          out_t.append(round(tf, 6))
          out_y.append(plant.x[1] - y0)
          out_psi.append(plant.x[4] - psi0)
          eps = plant.eps        # the command the EPS applies (plant.EPS.step): a refused frame times out to 0
          cmds.append(eps.last_cmd if eps.last_req and t - eps.last_t <= eps.timeout and not eps.fault else 0)
  return out_t, out_y, out_psi, cmds


def expm(M: np.ndarray) -> np.ndarray:
  """Matrix exponential by scaling and squaring of a Taylor series (small, well-scaled matrices)."""
  k = max(0, int(np.ceil(np.log2(max(np.abs(M).sum(axis=1).max(), 1e-300)))) + 1)
  X = M / 2 ** k
  E, term = np.eye(len(M)), np.eye(len(M))
  for i in range(1, 20):
    term = term @ X / i
    E = E + term
  for _ in range(k):
    E = E @ E
  return E


def linear_response(A, B, cmds):
  """The linear model driven by the commands that reached the EPS, each held over its grid step (exact ZOH)."""
  n = len(A)
  M = np.zeros((n + 1, n + 1))
  M[:n, :n], M[:n, n] = A, np.array(B)[:, 0]
  E = expm(M * GRID_S)
  Ad, Bd = E[:n, :n], E[:n, n]
  z = np.zeros(n)
  out = []
  for c in cmds:
    out.append((float(z[0]), float(z[1])))
    z = Ad @ z + Bd * c
  return out


def build() -> tuple[dict, dict]:
  v = SPEED_KPH / 3.6
  A_, B_ = linearise(v)
  model = {
    "about": "L1 plant linearised at straight driving; z = [y, psi, beta, r, delta, a_eps, u]; z' = A z + B w",
    "speed_kph": SPEED_KPH, "horizon_s": HORIZON_S, "grid_s": GRID_S,
    "u_max": STEER_MAX, "u_step": RATE_UP, "frame_s": FRAME_S, "plant_step_s": DYN_EVERY * DT_US / 1e6,
    "A": A_, "B": B_,
  }
  rng = random.Random(SEED)
  cases = [("hard-over left", lambda t: STEER_MAX), ("hard-over right", lambda t: -STEER_MAX)]
  for i in range(N_RANDOM):
    switches, tt = [], 0.0
    while tt < HORIZON_S:
      switches.append((tt, rng.uniform(-STEER_MAX, STEER_MAX) if rng.random() < 0.6 else rng.choice((-1, 1)) * STEER_MAX))
      tt += rng.expovariate(1 / 0.3)
    cases.append((f"random {i}", lambda t, s=switches: next(val for t0, val in reversed(s) if t >= t0)))
  runs = []
  for name, fn in cases:
    t, y, psi, cmds = run_fault(fn, v)
    bad = [(ti, c) for ti, c in zip(t, cmds, strict=True) if abs(c) > envelope(ti)]
    assert not bad, f"{name}: command outside the panda envelope at {bad[0]}"
    lin = linear_response(A_, B_, cmds)
    err = max(abs(a - b[0]) for a, b in zip(y, lin, strict=True))
    err_psi = max(abs(a - b[1]) for a, b in zip(psi, lin, strict=True))
    runs.append({"name": name, "y": y, "psi": psi, "lin_y": [b[0] for b in lin], "lin_psi": [b[1] for b in lin],
                 "lin_err_y": err, "lin_err_psi": err_psi})
  grid = runs[0]["y"] and [round(i * GRID_S, 6) for i in range(len(runs[0]["y"]))]
  env = {
    "about": "envelope of the sampled runs (real panda code, nonlinear L1 plant); y in m, psi in rad, from fault onset",
    "seed": SEED, "runs": len(runs), "t": grid,
    "y_min": [min(r["y"][i] for r in runs) for i in range(len(grid))],
    "y_max": [max(r["y"][i] for r in runs) for i in range(len(grid))],
    "psi_min": [min(r["psi"][i] for r in runs) for i in range(len(grid))],
    "psi_max": [max(r["psi"][i] for r in runs) for i in range(len(grid))],
    "lin_y_min": [min(r["lin_y"][i] for r in runs) for i in range(len(grid))],
    "lin_y_max": [max(r["lin_y"][i] for r in runs) for i in range(len(grid))],
    "lin_psi_min": [min(r["lin_psi"][i] for r in runs) for i in range(len(grid))],
    "lin_psi_max": [max(r["lin_psi"][i] for r in runs) for i in range(len(grid))],
    "hard_over_left_y": runs[0]["y"],
    "takeover_s": takeover(runs[0]["y"], grid),
    "max_linearisation_error_y_m": max(r["lin_err_y"] for r in runs),
    "max_linearisation_error_psi_rad": max(r["lin_err_psi"] for r in runs),
  }
  return model, env


def takeover(y, grid) -> float | None:
  """Driver correction time of a run, as the plant models it: drift cue plus reaction time (simulate.py)."""
  cue = next((t for t, v in zip(grid, y, strict=True) if abs(v) > assumption("driver_lat_cue_m")), None)
  return None if cue is None else round(cue + assumption("driver_t_r_s"), 6)


def dump(obj) -> str:
  return json.dumps(obj, indent=1, sort_keys=True, default=lambda x: round(x, 9)) + "\n"


def _round(obj):
  if isinstance(obj, float):
    return float(f"{obj:.9g}")
  if isinstance(obj, list):
    return [_round(x) for x in obj]
  if isinstance(obj, dict):
    return {k: _round(v) for k, v in obj.items()}
  return obj


def main(argv) -> int:
  model, env = build()
  files = {MODEL: dump(_round(model)), SAMPLES: dump(_round(env))}
  if "--check" in argv:
    stale = [p.name for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if stale:
      print(f"stale: {', '.join(stale)}; run: python3 assurance/sim/reach/reach_inputs.py", file=sys.stderr)
      return 1
    print("reach inputs: current")
    return 0
  for p, text in files.items():
    p.write_text(text, encoding="utf-8")
  print(f"reach inputs: wrote {MODEL.name}, {SAMPLES.name}; {env['runs']} runs, max linearisation error in y "
        f"{env['max_linearisation_error_y_m']:.4f} m")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
