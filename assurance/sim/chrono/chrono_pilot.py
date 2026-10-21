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

The same cases also run on the vehicle of a spec (`../vehicle/specs/`, built by `../vehicle/vehicle_spec.py`): the
reference Corolla from public data and physics, with its chassis mass and CoG calibrated against the assembled vehicle,
an understeer-gradient cross-check against openpilot's model, and a one-at-a-time sweep over the uncertain parameters.

    python chrono_pilot.py               # Sedan (about 3 min) and spec with its sweep (about 25 min): both JSON files
    python chrono_pilot.py --only=spec   # one of them (--only=sedan, --only=spec)
    python chrono_pilot.py --check       # CI: fail if a fresh run differs from the committed JSON beyond the tolerance

`compare_l1.py` (plant Python) reads the JSON and writes the comparison with the L1 plant. Synthetic (DSR-12), no
evidence credit.
"""

from __future__ import annotations

import bisect
import json
import math
import sys
import tempfile
from pathlib import Path

import pychrono as chrono
import pychrono.vehicle as veh

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results" / "chrono-pilot.json"
OUT_COROLLA = HERE.parent / "results" / "chrono-corolla.json"
sys.path.insert(0, str(HERE.parent / "vehicle"))
import vehicle_spec  # noqa: E402

SPEC = vehicle_spec.SPECS / "toyota_corolla_e210_sedan.toml"

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


def sedan(v0: float):
  """Chrono::Vehicle's generic Sedan (C++ model)."""
  car = veh.Sedan()
  car.SetContactMethod(chrono.ChContactMethod_SMC)
  car.SetChassisFixed(False)
  car.SetInitPosition(chrono.ChCoordsysd(chrono.ChVector3d(0, 0, 0.5), chrono.QUNIT))
  car.SetInitFwdVel(v0)
  car.SetTireType(veh.TireModelType_TMEASY)
  car.SetTireStepSize(STEP)
  car.Initialize()
  return car, car.GetVehicle(), {}


def _assemble(vals: dict, out: str, v0: float, z0: float, cm=None, com=None):
  f = vehicle_spec.chrono_files(vals, chrono.GetChronoDataPath() + "vehicle", out, cm, com)
  veh.SetDataPath(out + "/")
  car = veh.WheeledVehicle(str(f), chrono.ChContactMethod_SMC)
  car.Initialize(chrono.ChCoordsysd(chrono.ChVector3d(0, 0, z0), chrono.QUNIT), v0)
  for axle in car.GetAxles():
    for wheel in axle.GetWheels():
      tire = veh.ReadTireJSON(out + "/vehicle_spec/tire/tire.json")
      tire.SetStepsize(STEP)
      car.InitializeTire(tire, wheel, veh.VisualizationType_NONE)
  engine = veh.ReadEngineJSON(out + "/vehicle_spec/powertrain/Sedan_EngineSimpleMap.json")
  trans = veh.ReadTransmissionJSON(out + "/vehicle_spec/powertrain/Sedan_AutomaticTransmissionSimpleMap.json")
  car.InitializePowertrain(veh.ChPowertrainAssembly(engine, trans))
  return car


def spec_vehicle(v0: float, corner: dict | None = None):
  """The vehicle of the spec (vehicle_spec.py), its chassis mass and CoG calibrated so the assembled vehicle has the
  spec's total mass, CoG position and CoG height, and its tyres placed on the ground."""
  spec = vehicle_spec.load(SPEC)
  vals = vehicle_spec.values(spec, corner)
  d = vehicle_spec.derive(vals)
  out = tempfile.mkdtemp(prefix="vehicle_spec_")
  z0 = 0.6
  probe = _assemble(vals, out, v0, z0)
  # all in the chassis reference frame: the chassis and vehicle COM frames are reported in it
  ref = probe.GetChassis().GetBody().GetFrameRefToAbs().GetPos()
  ground = min(probe.GetSpindlePos(i, s).z for i in (0, 1) for s in (veh.LEFT, veh.RIGHT)) - ref.z - d["tire_radius"]
  cm0, c0 = probe.GetChassis().GetBody().GetMass(), probe.GetChassis().GetCOMFrame().GetPos()
  m, com = probe.GetMass(), probe.GetCOMFrame().GetPos()
  rest_x, rest_z = m * com.x - cm0 * c0.x, m * com.z - cm0 * c0.z
  cm = d["mass"] - (m - cm0)
  x_t, z_t = vals["wheelbase"] / 2 - d["a"], ground + d["cg_height"]
  com_local = ((d["mass"] * x_t - rest_x) / cm, 0.0, (d["mass"] * z_t - rest_z) / cm)
  z_init = 0.005 - ground                    # chassis frame placed so the tyres start 5 mm above the road
  car = _assemble(vals, out, v0, z_init, cm, com_local)
  ref = car.GetChassis().GetBody().GetFrameRefToAbs().GetPos()
  ground = min(car.GetSpindlePos(i, s).z for i in (0, 1) for s in (veh.LEFT, veh.RIGHT)) - ref.z - d["tire_radius"]
  com = car.GetCOMFrame().GetPos()
  realised = {"mass": car.GetMass(), "a": vals["wheelbase"] / 2 - com.x, "cg_height": com.z - ground,
              "tyre_clearance": ref.z + ground}
  return car, car, realised


def run(kph: float, push: float = 0.0, a_y: float = 0.0, settle: float = 12.0, after: float = 8.0,
        vehicle: str = "sedan", corner: dict | None = None, hold: bool = False) -> dict:
  """One case. Straight (a_y = 0): loss at `settle` s. Curve: loss at the clothoid start, reached after `settle` s.
  vehicle: "sedan" (Chrono's generic Sedan) or "spec" (the vehicle of SPEC at the given range corner).
  hold: no loss; the item follows the arc and the mean front-wheel angle over 2 s of steady cornering is returned."""
  v0 = kph / 3.6
  xs, ys, hs, ks, ss = make_path(a_y / (v0 * v0), settle * v0)
  car, vehicle_obj, realised = sedan(v0) if vehicle == "sedan" else spec_vehicle(v0, corner)
  system = car.GetSystem()
  system.SetCollisionSystemType(chrono.ChCollisionSystem.Type_BULLET)
  terrain = veh.RigidTerrain(system)
  mat = chrono.ChContactMaterialSMC()
  mat.SetFriction(0.9)
  terrain.AddPatch(mat, chrono.ChCoordsysd(chrono.ChVector3d(600, 600, 0), chrono.QUNIT), 3000.0, 3000.0)
  terrain.Initialize()
  vehicle = vehicle_obj
  L, dmax = vehicle.GetWheelbase(), vehicle.GetMaxSteeringAngle()

  def steer_for(a):
    return max(-1.0, min(1.0, math.atan(a * L / max(v * v, 1.0)) / dmax))

  inputs = veh.DriverInputs()
  steer = integ = 0.0
  i = 0
  t, t_loss, e0, t_cue, t_react = 0.0, None, None, None, None
  out = {"t_line30": None, "t_line37": None, "max_dev": 0.0}
  thr30, thr37 = (3.0 - WIDTH) / 2, (3.7 - WIDTH) / 2
  arc_start = settle * v0 + 100.0                # clothoid end
  wheel = []
  while (t_loss is None or t < t_loss + after) and not (hold and len(wheel) >= int(2.0 / STEP)):
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
    if not hold and t_loss is None and ss[i] >= settle * v0:
      t_loss, e0 = t, e_y
    if hold and ss[i] >= arc_start + 6.0 * v0:   # 6 s into the arc: steady
      # the wheel spins about its axle (local y), so read the steer angle from the axle's direction, not from
      # Cardan angles, which flip as the spin angle passes 90 degrees
      ang = []
      for side in (veh.LEFT, veh.RIGHT):
        ax = vehicle.GetSpindleRot(0, side).Rotate(chrono.ChVector3d(0, 1, 0))
        ang.append(math.atan2(-ax.x, ax.y))
      wheel.append(math.atan2(math.sin(sum(ang) / 2 - yaw), math.cos(sum(ang) / 2 - yaw)))
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
  if hold:
    return {"delta": round(sum(wheel) / len(wheel), 6), **{f"realised_{k}": round(x, 3) for k, x in realised.items()}}
  out["cue"] = None if t_cue is None else t_cue - t_loss
  out["corr"] = None if t_react is None else t_react - t_loss
  out["e0"] = e0
  out.update({f"realised_{k}": x for k, x in realised.items()})
  return {k: (None if x is None else round(x, 3)) for k, x in out.items()}


def understeer(kph: float = 110.0, vehicle: str = "spec", corner: dict | None = None) -> float:
  """Understeer gradient (rad per m/s^2) from the front-wheel angle in two steady turns, 1.0 and 2.0 m/s^2: the
  kinematic part L/R is taken out, so what is left is the tyres' and the suspension's."""
  v0 = kph / 3.6
  d1, d2 = (run(kph, a_y=a, vehicle=vehicle, corner=corner, hold=True)["delta"] for a in (1.0, 2.0))
  L = vehicle_spec.values(vehicle_spec.load(SPEC), corner)["wheelbase"] if vehicle == "spec" else 2.776   # Sedan JSON
  return round(((d2 - d1) - L * (2.0 - 1.0) / v0 ** 2) / (2.0 - 1.0), 6)


def runs(vehicle: str = "sedan", corner: dict | None = None) -> list[dict]:
  rs = [{"road": "straight", "push": p, "kph": k, **run(k, push=p, vehicle=vehicle, corner=corner)} for p, k in STRAIGHT]
  rs += [{"road": "curve", "a_y": a, "kph": 110.0, **run(110.0, a_y=a, vehicle=vehicle, corner=corner)} for a in CURVES]
  return rs


def build() -> dict:
  return {"chrono": CHRONO_VERSION,
          "vehicle": "Chrono::Vehicle Sedan, TMeasy tyres", "step_s": STEP, "cases": runs()}


# the spec parameters the sweep moves, each to both ends of its range with the others at their values; the rest of
# the spec's ranges (track, turning circle, roll and pitch inertia, tyre mass, steering ratio) barely enter these cases
SWEEP = ["curb_mass", "front_weight_fraction", "cg_height", "yaw_inertia_factor", "tire_load_index", "friction",
         "spring_scale"]
SWEEP_CASES = [("straight", 0.2, 110.0), ("curve", 1.5, 110.0), ("curve", 2.5, 110.0)]


def sweep_case(road: str, x: float, kph: float, corner: dict) -> dict:
  if road == "straight":
    return {"road": road, "push": x, "kph": kph, **run(kph, push=x, vehicle="spec", corner=corner)}
  return {"road": road, "a_y": x, "kph": kph, **run(kph, a_y=x, vehicle="spec", corner=corner)}


def build_spec() -> dict:
  spec = vehicle_spec.load(SPEC)
  data = {"chrono": CHRONO_VERSION, "spec": SPEC.name, "vehicle": spec["vehicle"]["name"], "step_s": STEP,
          "nominal": {"cases": runs("spec"), "understeer": understeer()}, "sweep": []}
  for name in SWEEP:
    for end in ("low", "high"):
      corner = {name: end}
      data["sweep"].append({"param": name, "end": end, "value": spec["param"][name][end],
                            "cases": [sweep_case(r, x, k, corner) for r, x, k in SWEEP_CASES],
                            "understeer": understeer(corner=corner)})
  return data


def differ(a, b, path: str = "") -> list[str]:
  """Differences between two results beyond TOL (numbers) or at all (anything else)."""
  if isinstance(a, dict) and isinstance(b, dict):
    if set(a) != set(b):
      return [f"{path}: keys {sorted(set(a) ^ set(b))}"]
    return [d for k in a for d in differ(a[k], b[k], f"{path}/{k}")]
  if isinstance(a, list) and isinstance(b, list):
    if len(a) != len(b):
      return [f"{path}: {len(a)} != {len(b)} entries"]
    return [d for i, (x, y) in enumerate(zip(a, b)) for d in differ(x, y, f"{path}[{i}]")]
  if isinstance(a, float) and isinstance(b, float):
    # understeer gradients are small (rad per m/s^2): compare them relatively
    tol = max(TOL, 0.05 * abs(a)) if "understeer" not in path else max(2e-4, 0.05 * abs(a))
    return [] if abs(a - b) <= tol else [f"{path}: {a} != {b}"]
  return [] if a == b else [f"{path}: {a} != {b}"]


def main(argv: list[str]) -> int:
  which = [w for w in ("sedan", "spec") if f"--only={w}" in argv] or ["sedan", "spec"]
  targets = {"sedan": (OUT, build), "spec": (OUT_COROLLA, build_spec)}
  bad = 0
  for w in which:
    out, fn = targets[w]
    data = fn()
    if "--check" in argv:
      diffs = differ(json.loads(out.read_text(encoding="utf-8")), data)
      for d in diffs:
        print(f"differs: {out.name}{d}", file=sys.stderr)
      bad += bool(diffs)
      if not diffs:
        print(f"chrono_pilot: {out.name} within tolerance")
    else:
      out.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
      print(f"wrote {out.name}")
  return 1 if bad else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
