"""Corolla E210 (TSS2) parameter set for the CommonRoad single-track model.

CommonRoad ships no Corolla set. This set starts from CommonRoad vehicle 2 (BMW 320i, Althoff and Wuersching,
"CommonRoad: Vehicle Models", 2020, Tab. 6), the closest of its four sets: a front-engined compact sedan, where
vehicle 1 (Ford Escort) is older and lighter, vehicle 3 (VW Vanagon) a van and vehicle 4 a semi-trailer truck.
Every value the single-track model reads is listed in PARAMS with its source and its status:

  opendbc   from the Corolla CarParams in opendbc (the values openpilot drives the car with)
  scaled    vehicle 2 scaled to the Corolla, with the rule given
  vehicle2  vehicle 2 unchanged, because nothing better is available
  confirmed checked against the reference vehicle record (WP-V-02 §3.5)

None of them is measured on the LionDriver reference car (WP-S-04 M-01).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OPENDBC = ROOT / "opendbc_repo" / "opendbc"
LB_TO_KG = 0.453592

# CommonRoad vehicle 2 (BMW 320i), parameters_vehicle2.yaml of commonroad-vehicle-models 3.0.2
V2 = {"m": 1093.2952334674046, "a": 1.1561957064, "b": 1.4227170936, "I_z": 1791.5995300122856, "h_s": 0.61373004}


def _read(rel: str, pattern: str) -> str:
  text = (OPENDBC / rel).read_text(encoding="utf-8")
  m = re.search(pattern, text)
  if not m:
    raise ValueError(f"{rel}: pattern not found: {pattern}")
  return m.group(1)


def opendbc_values() -> dict:
  """Read the Corolla TSS2 values from the opendbc sources (no import of opendbc.car needed)."""
  text = (OPENDBC / "car/toyota/values.py").read_text(encoding="utf-8")
  block = text[text.index("TOYOTA_COROLLA_TSS2 = "):]
  specs = re.search(r"CarSpecs\(([^)]*)\)", block).group(1)
  mass_lb = float(re.search(r"mass=([\d.]+)\s*\*\s*CV\.LB_TO_KG", specs).group(1))
  wheelbase = float(re.search(r"wheelbase=([\d.]+)", specs).group(1))
  steer_ratio = float(re.search(r"steerRatio=([\d.]+)", specs).group(1))
  cargo = float(_read("car/__init__.py", r"STD_CARGO_KG\s*=\s*([\d.]+)"))
  ctf = float(_read("car/toyota/interface.py", r"ret\.centerToFront = ret\.wheelbase \* ([\d.]+)"))
  lat = _read("car/torque_data/params.toml", r'"TOYOTA_COROLLA_TSS2" = \[([^\]]*)\]')
  lat_accel_factor = float(lat.split(",")[0])
  steer_delay = float(_read("car/toyota/interface.py", r"ret\.steerActuatorDelay = ([\d.]+)  # Default delay"))
  long_delay = float(_read("car/interfaces.py", r"ret\.longitudinalActuatorDelay = ([\d.]+)"))
  return {"mass_lb": mass_lb, "mass_kg": mass_lb * LB_TO_KG, "cargo_kg": cargo, "wheelbase": wheelbase,
          "steer_ratio": steer_ratio, "center_to_front_ratio": ctf, "lat_accel_factor": lat_accel_factor,
          "steer_actuator_delay": steer_delay, "long_actuator_delay": long_delay}


@dataclass(frozen=True)
class Param:
  name: str
  value: float
  unit: str
  status: str
  source: str


def corolla_params() -> list[Param]:
  o = opendbc_values()
  m = o["mass_kg"] + o["cargo_kg"]
  L = o["wheelbase"]
  a = L * o["center_to_front_ratio"]
  L2 = V2["a"] + V2["b"]
  I_z = V2["I_z"] * (m * L ** 2) / (V2["m"] * L2 ** 2)
  return [
    Param("m", m, "kg", "opendbc", f"CarSpecs mass {o['mass_lb']:g} lb (`car/toyota/values.py`, TOYOTA_COROLLA_TSS2) "
          f"+ STD_CARGO_KG {o['cargo_kg']:g} kg (`car/__init__.py`), as openpilot's CarParams.mass"),
    Param("L", L, "m", "opendbc", "CarSpecs wheelbase (`car/toyota/values.py`)"),
    Param("a", a, "m", "opendbc", f"CoG to front axle = wheelbase x {o['center_to_front_ratio']:g} (`car/toyota/interface.py` centerToFront)"),
    Param("b", L - a, "m", "opendbc", "CoG to rear axle = wheelbase - a"),
    Param("I_z", I_z, "kg m^2", "scaled", "vehicle 2 yaw inertia x (m L^2) / (m2 L2^2): the rule opendbc's scale_rot_inertia uses"),
    Param("h_s", V2["h_s"], "m", "vehicle2", "vehicle 2 sprung-mass CoG height; enters only with longitudinal acceleration"),
    Param("C_S", 21.92 / 1.0489, "1/rad", "vehicle2", "normalised cornering stiffness -p_ky1/p_dy1 of the vehicle-2 tyre, front and rear"),
    Param("mu", 1.0489, "-", "vehicle2", "friction coefficient p_dy1 of the vehicle-2 tyre (dry road)"),
    Param("steer_v_max", 0.4, "rad/s", "vehicle2", "front-wheel steering rate limit of vehicle 2"),
    Param("width", 1.781, "m", "confirmed", "body width 1,781 mm (WP-V-02 §3.5 reference-vehicle check; WP-S-04 §3.1 uses 1.78 m)"),
    Param("lat_accel_factor", o["lat_accel_factor"], "m/s^2", "opendbc",
          "lateral acceleration at full LKA torque (1500), `car/torque_data/params.toml` LAT_ACCEL_FACTOR: comma's fleet estimate, not measured on the reference car (AOU-01R, M-01)"),
    Param("steer_ratio", o["steer_ratio"], "-", "opendbc", "CarSpecs steerRatio; used only to report hand-wheel angles"),
    Param("tau_eps", o["steer_actuator_delay"], "s", "opendbc", "steerActuatorDelay (`car/toyota/interface.py`), used as a first-order EPS lag; not measured (M-02)"),
    Param("tau_pcm", o["long_actuator_delay"], "s", "opendbc", "longitudinalActuatorDelay default (`car/interfaces.py`; the Corolla is not a hybrid), used as a first-order PCM lag; not measured (M-03)"),
  ]


def as_dict() -> dict[str, float]:
  return {p.name: p.value for p in corolla_params()}


def commonroad_parameters(d: dict[str, float] | None = None):
  """CommonRoad vehicle 2 with the Corolla values written over it."""
  from vehiclemodels.parameters_vehicle2 import parameters_vehicle2
  d = d or as_dict()
  p = parameters_vehicle2()
  p.m, p.a, p.b, p.I_z, p.h_s = d["m"], d["a"], d["b"], d["I_z"], d["h_s"]
  p.w = d["width"]
  p.steering.v_max, p.steering.v_min = d["steer_v_max"], -d["steer_v_max"]
  return p


def understeer_gradient(d: dict[str, float] | None = None) -> float:
  """rad per m/s^2 for the single-track model: zero when front and rear share one normalised stiffness."""
  d = d or as_dict()
  L, a, b, m = d["L"], d["a"], d["b"], d["m"]
  c_f = d["mu"] * d["C_S"] * m * 9.81 * b / L
  c_r = d["mu"] * d["C_S"] * m * 9.81 * a / L
  return m / L * (b / c_f - a / c_r)


def steer_for_lat_accel(a_y: float, v: float, d: dict[str, float] | None = None) -> float:
  """Steady-state front-wheel angle (rad) for lateral acceleration a_y at speed v."""
  d = d or as_dict()
  return d["L"] * a_y / max(v, 1.0) ** 2 + understeer_gradient(d) * a_y


if __name__ == "__main__":
  for p in corolla_params():
    print(f"{p.name:18s} {p.value:12.5g} {p.unit:7s} {p.status:9s} {p.source}")
  print("understeer gradient", understeer_gradient(), "rad/(m/s^2)", math.degrees(understeer_gradient()))
