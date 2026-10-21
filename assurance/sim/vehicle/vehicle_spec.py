#!/usr/bin/env python3
"""Vehicle spec: a car's parameters with their sources and ranges, the physics that derives the rest, and the
Chrono::Vehicle JSON set built from them.

A spec (`specs/*.toml`) lists each parameter with a value, a plausible range (low, high), a status (published, fleet,
derived, assumed) and its source; `check()` refuses an entry without them. `derive()` turns a set of values into the
quantities a vehicle model needs (axle loads, CoG position, inertias, tyre radius, steering lock, openpilot's own axle
cornering stiffness for comparison). `chrono_files()` writes a Chrono::Vehicle JSON vehicle from the Chrono sedan
templates, changed to the spec: chassis mass, CoG and inertia; wheelbase; suspension hardpoints scaled to the track;
spring and damper rates scaled with the corner load; a TMeasy tyre from the tyre size and load index (Chrono derives
its stiffness from them); steering lock from the turning circle.

Plain Python (tomllib, json): it runs in the plant's Python and in the PyChrono build alike. Another car needs only
another spec file.

    python3 vehicle_spec.py specs/toyota_corolla_e210_sedan.toml    # check the spec and print the derived values

Synthetic (DSR-12), no evidence credit: nothing in a spec is measured on the reference car.
"""

from __future__ import annotations

import copy
import json
import math
import re
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPECS = HERE / "specs"
STATUSES = ("published", "fleet", "derived", "assumed")
G = 9.81

# opendbc VehicleDynamicsParams (car/__init__.py): the Civic reference openpilot scales every car's tyres from
OP_REF = {"mass": 1326.0 + 136.0, "wheelbase": 2.70, "ctf": 0.4, "cf": 192150.0, "cr": 202500.0}


def load(path: str | Path) -> dict:
  spec = tomllib.loads(Path(path).read_text(encoding="utf-8"))
  check(spec)
  return spec


def check(spec: dict) -> None:
  """Every parameter has a value inside its range, a known status and a source."""
  bad = []
  for name, p in spec["param"].items():
    for k in ("value", "low", "high", "unit", "status", "source"):
      if k not in p:
        bad.append(f"{name}: no {k}")
    if not bad and not p["low"] <= p["value"] <= p["high"]:
      bad.append(f"{name}: value {p['value']} outside [{p['low']}, {p['high']}]")
    if p.get("status") not in STATUSES:
      bad.append(f"{name}: status {p.get('status')!r} not one of {STATUSES}")
    if not str(p.get("source", "")).strip():
      bad.append(f"{name}: empty source")
  if bad:
    raise ValueError("spec: " + "; ".join(bad))


def values(spec: dict, corner: dict[str, str] | None = None) -> dict[str, float]:
  """Parameter values; corner maps a name to 'low' or 'high' to take that end of its range."""
  corner = corner or {}
  unknown = set(corner) - set(spec["param"])
  if unknown:
    raise KeyError(f"not a parameter: {sorted(unknown)}")
  return {n: p[corner.get(n, "value")] for n, p in spec["param"].items()}


def swept(spec: dict) -> list[str]:
  """Parameters with a range: the one-at-a-time sweep moves each to its ends."""
  return [n for n, p in spec["param"].items() if p["low"] != p["high"]]


def derive(v: dict[str, float]) -> dict[str, float]:
  """The quantities a vehicle model reads, from the spec values (SI units)."""
  m = v["curb_mass"] + v["load_mass"]
  L = v["wheelbase"]
  ff = v["front_weight_fraction"]
  a = (1.0 - ff) * L                      # CoG to front axle
  b = ff * L                              # CoG to rear axle
  izz = v["yaw_inertia_factor"] * m * a * b
  r_tire = v["rim_diameter"] / 2 + v["tire_width"] * v["tire_aspect"]
  # steering lock from the curb-to-curb turning circle (Ackermann, turn centre on the rear axle line): the outer front
  # tyre's outer edge runs on the circle, so its centre runs half a tyre width inside it
  r_out = v["turning_circle"] / 2 - v["tire_width"] / 2
  t = v["track_front"]
  delta_out = math.asin(min(L / r_out, 1.0))
  delta_in = math.atan(L / (math.sqrt(r_out ** 2 - L ** 2) - t))
  # openpilot's axle cornering stiffness (scale_tire_stiffness): the fleet-fitted cross-check of the tyre model
  ref_a = OP_REF["wheelbase"] * OP_REF["ctf"]
  ref_b = OP_REF["wheelbase"] - ref_a
  cf = OP_REF["cf"] * v["tire_stiffness_factor"] * m / OP_REF["mass"] * (b / L) / (ref_b / OP_REF["wheelbase"])
  cr = OP_REF["cr"] * v["tire_stiffness_factor"] * m / OP_REF["mass"] * (a / L) / (ref_a / OP_REF["wheelbase"])
  k_us = m / L * (b / cf - a / cr)        # rad per m/s^2, single-track understeer gradient
  return {"mass": m, "a": a, "b": b, "front_axle_load": m * G * ff, "rear_axle_load": m * G * (1 - ff),
          "cg_height": v["cg_height"], "izz": izz, "iyy": v["pitch_inertia_ratio"] * izz,
          "ixx": m * v["roll_gyration_radius"] ** 2, "tire_radius": r_tire, "delta_max_outer": delta_out,
          "delta_max_inner": delta_in, "op_cf": cf, "op_cr": cr, "op_understeer": k_us}


# ------------------------------------------------------------------------------------------ Chrono::Vehicle JSON

def _read_json(path: Path) -> dict:
  text = re.sub(r"(?m)^\s*//.*$|(?<=[,\[{\s])//[^\n]*", "", path.read_text(encoding="utf-8"))
  return json.loads(text)


def _scale_y(obj, f: float):
  """Scale the y coordinate of every 3-vector in a suspension description (its hardpoints and COMs)."""
  if isinstance(obj, dict):
    return {k: (_scale_y(x, f) if k not in ("Inertia", "Moments of Inertia", "Products of Inertia",
                                            "Universal Joint Axis Link", "Universal Joint Axis Chassis") else x)
            for k, x in obj.items()}
  if isinstance(obj, list) and len(obj) == 3 and all(isinstance(x, (int, float)) for x in obj):
    return [obj[0], obj[1] * f, obj[2]]
  return obj


def _suspension(src: dict, track: float, load_ratio: float, spring_scale: float, side_y: str) -> dict:
  s = copy.deepcopy(src)
  y0 = s["Spindle"]["COM"][1]
  s = _scale_y(s, (track / 2) / y0)
  s["Name"] = s["Name"] + " (vehicle_spec)"
  k = load_ratio * spring_scale
  s["Spring"]["Spring Coefficient"] *= k
  # damper with the spring: c ~ sqrt(k m), and k ~ m, so c scales as k keeps the sedan's damping ratio
  s["Shock"]["Damping Coefficient"] *= k
  return s


def chrono_files(v: dict[str, float], chrono_data: str | Path, out: str | Path, chassis_mass: float | None = None,
                 chassis_com: tuple[float, float, float] | None = None) -> Path:
  """Write the vehicle's JSON set under out/vehicle_spec/ and return the vehicle file. chrono_data is Chrono's
  data/vehicle directory (the sedan templates). chassis_mass and chassis_com, when given, override the first guess
  (the runner calibrates them against the assembled vehicle's mass and CoG)."""
  d = derive(v)
  src = Path(chrono_data) / "sedan"
  out = Path(out)
  root = out / "vehicle_spec"
  for sub in ("vehicle", "chassis", "suspension", "steering", "wheel", "brake", "driveline", "powertrain", "tire"):
    (root / sub).mkdir(parents=True, exist_ok=True)

  veh = _read_json(src / "vehicle" / "Sedan_Vehicle.json")
  sedan_chassis = _read_json(src / "chassis" / "Sedan_Chassis.json")
  dw = _read_json(src / "suspension" / "Sedan_DoubleWishbone.json")
  ml = _read_json(src / "suspension" / "Sedan_MultiLink.json")
  sedan_mass = sedan_chassis["Components"][0]["Mass"]
  # corner loads relative to the sedan's (its CoG is midway between the axles)
  f_front = (d["mass"] * v["front_weight_fraction"]) / (sedan_mass / 2)
  f_rear = (d["mass"] * (1 - v["front_weight_fraction"])) / (sedan_mass / 2)
  json.dump(_suspension(dw, v["track_front"], f_front, v["spring_scale"], "front"),
            open(root / "suspension" / "front.json", "w"), indent=1)
  json.dump(_suspension(ml, v["track_rear"], f_rear, v["spring_scale"], "rear"),
            open(root / "suspension" / "rear.json", "w"), indent=1)

  ch = copy.deepcopy(sedan_chassis)
  c = ch["Components"][0]
  L = v["wheelbase"]
  x_cg = L / 2 - d["a"]                   # axles at +L/2 and -L/2
  c["Mass"] = chassis_mass if chassis_mass is not None else d["mass"] - 160.0
  c["Centroidal Frame"]["Location"] = list(chassis_com) if chassis_com is not None else [x_cg, 0, 0.55]
  c["Moments of Inertia"] = [d["ixx"], d["iyy"], d["izz"]]
  ch.pop("Visualization", None)
  ch["Name"] = "chassis (vehicle_spec)"
  json.dump(ch, open(root / "chassis" / "chassis.json", "w"), indent=1)

  for sub, name in (("steering", "Sedan_RackPinion.json"), ("wheel", "Sedan_Wheel.json"),
                    ("brake", "Sedan_BrakeSimple.json"), ("driveline", "Sedan_Driveline2WD.json"),
                    ("powertrain", "Sedan_EngineSimpleMap.json"),
                    ("powertrain", "Sedan_AutomaticTransmissionSimpleMap.json")):
    j = _read_json(src / sub / name)
    j.pop("Visualization", None)
    json.dump(j, open(root / sub / name, "w"), indent=1)

  axles = veh["Axles"]
  axles[0]["Suspension Input File"] = "vehicle_spec/suspension/front.json"
  axles[1]["Suspension Input File"] = "vehicle_spec/suspension/rear.json"
  axles[0]["Suspension Location"][0] = L / 2
  axles[1]["Suspension Location"][0] = -L / 2
  for ax in axles:
    for k in ("Left Wheel Input File", "Right Wheel Input File"):
      ax[k] = "vehicle_spec/wheel/Sedan_Wheel.json"
    for k in ("Left Brake Input File", "Right Brake Input File"):
      ax[k] = "vehicle_spec/brake/Sedan_BrakeSimple.json"
  veh["Chassis"]["Input File"] = "vehicle_spec/chassis/chassis.json"
  veh["Steering Subsystems"][0]["Input File"] = "vehicle_spec/steering/Sedan_RackPinion.json"
  veh["Steering Subsystems"][0]["Location"][0] = L / 2 - 0.188     # the sedan's rack sits 0.188 m behind its axle
  veh["Driveline"]["Input File"] = "vehicle_spec/driveline/Sedan_Driveline2WD.json"
  veh["Wheelbase"] = L
  veh["Minimum Turning Radius"] = v["turning_circle"] / 2
  veh["Name"] = "vehicle_spec vehicle"
  json.dump(veh, open(root / "vehicle" / "vehicle.json", "w"), indent=1)

  rim = v["rim_diameter"] / 2
  tire = {"Name": "TMeasy tyre (vehicle_spec)", "Type": "Tire", "Template": "TMeasyTire",
          "Design": {"Unloaded Radius [m]": d["tire_radius"], "Mass [kg]": v["tire_mass"],
                     # thin-ring inertia about the spin axis; the other two halved, as the sedan's tyre file has them
                     "Inertia [kg.m2]": [0.5 * v["tire_mass"] * (d["tire_radius"] ** 2 + rim ** 2) / 2,
                                         v["tire_mass"] * (d["tire_radius"] ** 2 + rim ** 2) / 2,
                                         0.5 * v["tire_mass"] * (d["tire_radius"] ** 2 + rim ** 2) / 2],
                     "Width [m]": v["tire_width"], "Rim Radius [m]": rim},
          "Coefficient of Friction": v["friction"], "Rolling Resistance Coefficient": 0.015,
          "Vehicle Type": "Passenger", "Load Index": int(round(v["tire_load_index"]))}
  json.dump(tire, open(root / "tire" / "tire.json", "w"), indent=1)
  return root / "vehicle" / "vehicle.json"


def main(argv: list[str]) -> int:
  spec = load(argv[0] if argv else SPECS / "toyota_corolla_e210_sedan.toml")
  print(spec["vehicle"]["name"])
  for n, p in spec["param"].items():
    print(f"  {n:24s} {p['value']:>10g} {p['unit']:6s} [{p['low']:g}, {p['high']:g}] {p['status']}")
  print("derived:")
  for k, x in derive(values(spec)).items():
    print(f"  {k:24s} {x:>12.5g}")
  print("swept:", ", ".join(swept(spec)))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
