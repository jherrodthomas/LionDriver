#!/usr/bin/env python3
"""Project Chrono pilot: the silent assist loss of two plant studies, rerun on a multibody vehicle with tyre models.

Runs on the PyChrono that `build_chrono.sh` builds from source (Project Chrono 9.0.1, BSD 3-Clause, open-source parts
only), not in the plant's Python. The vehicle is Chrono::Vehicle's generic `Sedan` (double wishbone front, multilink rear, TMeasy tyres, its own
parameters from Chrono's data directory): not the reference Corolla. Two scenarios of the L1 plant are repeated with the
same item law, the same EPS lag and the same driver model:

  - straight with a cross slope (plant `straight_drift.py`): here the slope is real (gravity tilted), the item holds
    the lane, then assist is lost and the steering input returns to straight ahead with tau_eps;
  - curve entry (plant `silent_stall.py`, siren muted): a 100 m clothoid into a left arc R = v^2 / a_y, assist lost at
    the clothoid start.

The driver notices a drift of 0.2 m from the offset at the loss and steers back 1.5 s later (plant driver loop,
<= 4 m/s^2). Chrono's steering is a kinematic input: the wheel angle follows it, so neither the tyres' aligning torque
nor a hand on the wheel moves the steering here. What Chrono adds is the vehicle: tyre slip and saturation, yaw and
sideslip, roll and load transfer.

    python chrono_pilot.py            # run the 12 cases (about 3 min), write ../results/chrono-pilot.json
    python chrono_pilot.py --check    # CI: fail if a fresh run differs from the committed JSON beyond the tolerance

`compare_l1.py` (plant Python) reads the JSON and writes the comparison with the L1 plant. Synthetic (DSR-12), no
evidence credit.
"""

from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

import pychrono as chrono
import pychrono.vehicle as veh

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results" / "chrono-pilot.json"

G = 9.81
WIDTH = 1.781                                  # reference Corolla body width (plant corolla.py), for the lane lines
TAU_EPS = 0.12                                 # plant corolla.py tau_eps
T_R, CUE = 1.5, 0.2                            # plant driver_t_r_s, driver_lat_cue_m
KE, KV, AY_MAX = 1.5 ** 2, 2 * 1.5, 4.0        # plant driver loop (DRIVER_KE, DRIVER_KV, driver_ay_max)
KP, KH, KI = 2.0, 5.0, 0.8                     # item law: plant gains raised so the Sedan settles before the loss
STEP = 1e-3
CHRONO_VERSION = "9.0.1"                       # the tag build_chrono.sh builds
TOL = 0.05                                     # s or m: --check tolerance across machines

STRAIGHT = [(push, kph) for push in (0.0, 0.1, 0.2, 0.4, 0.6) for kph in (80.0, 110.0)]
CURVES = [1.5, 2.5]                            # m/s², at 110 km/h: plant roads "curve" and "curve-odd-bound"


def make_path(k_arc: float, straight: float, clothoid: float = 100.0, arc: float = 1500.0, ds: float = 0.05):
  xs, ys, hs, ks, ss = [0.0], [0.0], [0.0], [0.0], [0.0]
  s = 0.0
  while s < straight + clothoid + arc:
    k = 0.0 if s < straight else k_arc * min((s - straight) / clothoid, 1.0)
    h = hs[-1] + k * ds
    xs.append(xs[-1] + math.cos(h) * ds)
    ys.append(ys[-1] + math.sin(h) * ds)
    hs.append(h)
    ks.append(k)
    s += ds
    ss.append(s)
  return xs, ys, hs, ks, ss


def run(kph: float, push: float = 0.0, a_y: float = 0.0, settle: float = 12.0, after: float = 8.0) -> dict:
  """One case. Straight (a_y = 0): loss at `settle` s. Curve: loss at the clothoid start, reached after `settle` s."""
  v0 = kph / 3.6
  xs, ys, hs, ks, ss = make_path(a_y / (v0 * v0), settle * v0)
  car = veh.Sedan()
  car.SetContactMethod(chrono.ChContactMethod_SMC)
  car.SetChassisFixed(False)
  car.SetInitPosition(chrono.ChCoordsysd(chrono.ChVector3d(0, 0, 0.5), chrono.QUNIT))
  car.SetInitFwdVel(v0)
  car.SetTireType(veh.TireModelType_TMEASY)
  car.SetTireStepSize(STEP)
  car.Initialize()
  system = car.GetSystem()
  system.SetCollisionSystemType(chrono.ChCollisionSystem.Type_BULLET)
  terrain = veh.RigidTerrain(system)
  mat = chrono.ChContactMaterialSMC()
  mat.SetFriction(0.9)
  terrain.AddPatch(mat, chrono.ChCoordsysd(chrono.ChVector3d(600, 600, 0), chrono.QUNIT), 3000.0, 3000.0)
  terrain.Initialize()
  vehicle = car.GetVehicle()
  L, dmax = vehicle.GetWheelbase(), vehicle.GetMaxSteeringAngle()

  def steer_for(a):
    return max(-1.0, min(1.0, math.atan(a * L / max(v * v, 1.0)) / dmax))

  inputs = veh.DriverInputs()
  steer = integ = 0.0
  i = 0
  t, t_loss, e0, t_cue, t_react = 0.0, None, None, None, None
  out = {"t_line30": None, "t_line37": None, "max_dev": 0.0}
  thr30, thr37 = (3.0 - WIDTH) / 2, (3.7 - WIDTH) / 2
  while t_loss is None or t < t_loss + after:
    pos = vehicle.GetPos()
    yaw = vehicle.GetRot().GetCardanAnglesZYX().z
    v = vehicle.GetSpeed()
    while i + 1 < len(xs) and (xs[i + 1] - pos.x) ** 2 + (ys[i + 1] - pos.y) ** 2 < (xs[i] - pos.x) ** 2 + (ys[i] - pos.y) ** 2:
      i += 1
    e_y = -(pos.x - xs[i]) * math.sin(hs[i]) + (pos.y - ys[i]) * math.cos(hs[i])   # left of the path positive
    e_psi = math.atan2(math.sin(yaw - hs[i]), math.cos(yaw - hs[i]))
    k_ahead = ks[min(bisect.bisect_left(ss, ss[i] + v * TAU_EPS), len(ks) - 1)]
    # cross slope down to the right, built up over 2-4 s as in straight_drift.py
    a_push = push * min(max((t - 2.0) / 2.0, 0.0), 1.0)
    system.SetGravitationalAcceleration(chrono.ChVector3d(0, -a_push, -math.sqrt(G * G - a_push * a_push)))
    inputs.m_throttle = max(0.0, min(1.0, 0.3 + 0.5 * (v0 - v)))
    inputs.m_braking = 0.0
    if t_loss is None and ss[i] >= settle * v0:
      t_loss, e0 = t, e_y
    if t_loss is None:          # the item holds the path
      integ += -e_y * STEP
      target = steer_for(v * v * k_ahead - KP * e_y - KH * v * math.sin(e_psi) + KI * integ)
    else:
      dev = e_y - e0
      out["max_dev"] = max(out["max_dev"], abs(dev))
      if out["t_line30"] is None and abs(e_y) >= thr30:
        out["t_line30"] = t - t_loss
      if out["t_line37"] is None and abs(e_y) >= thr37:
        out["t_line37"] = t - t_loss
      if t_cue is None and abs(dev) > CUE:
        t_cue, t_react = t, t + T_R
      if t_react is not None and t >= t_react:   # the driver
        target = steer_for(max(-AY_MAX, min(AY_MAX, v * v * ks[i] - KE * e_y - KV * v * math.sin(e_psi))))
      else:                                      # assist lost: the steering input returns to straight ahead
        target = 0.0
    steer += (target - steer) * min(STEP / TAU_EPS, 1.0)
    inputs.m_steering = steer
    terrain.Synchronize(t)
    car.Synchronize(t, inputs, terrain)
    terrain.Advance(STEP)
    car.Advance(STEP)
    t = system.GetChTime()
  out["cue"] = None if t_cue is None else t_cue - t_loss
  out["corr"] = None if t_react is None else t_react - t_loss
  out["e0"] = e0
  return {k: (None if x is None else round(x, 3)) for k, x in out.items()}


def runs() -> list[dict]:
  rs = [{"road": "straight", "push": p, "kph": k, **run(k, push=p)} for p, k in STRAIGHT]
  rs += [{"road": "curve", "a_y": a, "kph": 110.0, **run(110.0, a_y=a)} for a in CURVES]
  return rs


def build() -> dict:
  return {"chrono": CHRONO_VERSION,
          "vehicle": "Chrono::Vehicle Sedan, TMeasy tyres", "step_s": STEP, "cases": runs()}


def differ(a: dict, b: dict) -> list[str]:
  out = []
  for x, y in zip(a["cases"], b["cases"], strict=True):
    for k in x:
      p, q = x[k], y[k]
      if isinstance(p, float) and isinstance(q, float):
        if abs(p - q) > TOL:
          out.append(f"{x['road']} {x.get('push', x.get('a_y'))} {x['kph']}: {k} {p} != {q}")
      elif p != q:
        out.append(f"{x['road']} {x.get('push', x.get('a_y'))} {x['kph']}: {k} {p} != {q}")
  return out


def main(argv: list[str]) -> int:
  data = build()
  if "--check" in argv:
    old = json.loads(OUT.read_text(encoding="utf-8"))
    bad = differ(old, data)
    for d in bad:
      print(f"differs: {d}", file=sys.stderr)
    if not bad:
      print(f"chrono_pilot: {len(data['cases'])} cases within {TOL} of {OUT.name}")
    return 1 if bad else 0
  OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
  print(f"wrote {OUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
