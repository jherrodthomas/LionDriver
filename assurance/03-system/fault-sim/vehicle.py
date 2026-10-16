"""Plant: Corolla E210 lateral and longitudinal dynamics, lane geometry, EPS and PCM behaviour, driver.

Parameters come from the opendbc sources where opendbc has them (read at import, so they follow the pinned
submodule) and are otherwise stated assumptions with the WP-S-04 item they stand for. See README.md §3.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAR = ROOT / "opendbc_repo" / "opendbc" / "car"


def _corolla_specs() -> dict:
  values = (CAR / "toyota" / "values.py").read_text(encoding="utf-8")
  m = re.search(r"TOYOTA_COROLLA_TSS2 = .*?CarSpecs\(mass=([\d.]+)\s*\*\s*CV\.LB_TO_KG, wheelbase=([\d.]+), "
                r"steerRatio=([\d.]+), tireStiffnessFactor=([\d.]+)\)", values, re.S)
  if not m:
    raise RuntimeError("TOYOTA_COROLLA_TSS2 CarSpecs not found in opendbc toyota/values.py")
  base = (CAR / "__init__.py").read_text(encoding="utf-8")
  g = lambda name: float(re.search(rf"{name} = ([\d.]+)", base).group(1))  # noqa: E731
  torque = (CAR / "torque_data" / "params.toml").read_text(encoding="utf-8")
  laf = float(re.search(r'"TOYOTA_COROLLA_TSS2" = \[([\d.]+),', torque).group(1))
  iface = (CAR / "toyota" / "interface.py").read_text(encoding="utf-8")
  c2f_ratio = float(re.search(r"ret\.centerToFront = ret\.wheelbase \* ([\d.]+)", iface).group(1))
  return {
    "mass_lb": float(m.group(1)), "wheelbase": float(m.group(2)), "steer_ratio": float(m.group(3)),
    "tire_stiffness_factor": float(m.group(4)), "std_cargo": g("STD_CARGO_KG"),
    "ref_mass": 1326. + g("STD_CARGO_KG"), "ref_wheelbase": 2.70, "ref_c2f": 0.4,
    "ref_inertia": g("ROTATIONAL_INERTIA"), "ref_cf": g("TIRE_STIFFNESS_FRONT"), "ref_cr": g("TIRE_STIFFNESS_REAR"),
    "lat_accel_factor": laf, "c2f_ratio": c2f_ratio,
  }


SPEC = _corolla_specs()
LB_TO_KG = 0.453592
MASS = SPEC["mass_lb"] * LB_TO_KG + SPEC["std_cargo"]
L = SPEC["wheelbase"]
A_CG = L * SPEC["c2f_ratio"]          # centre of gravity to front axle
B_CG = L - A_CG
# opendbc scale_rot_inertia / scale_tire_stiffness (opendbc/car/__init__.py)
IZ = SPEC["ref_inertia"] * MASS * L ** 2 / (SPEC["ref_mass"] * SPEC["ref_wheelbase"] ** 2)
_ref_cr_frac = (SPEC["ref_wheelbase"] * (1 - SPEC["ref_c2f"])) / SPEC["ref_wheelbase"]
_ref_cf_frac = SPEC["ref_c2f"]
CF = SPEC["ref_cf"] * SPEC["tire_stiffness_factor"] * MASS / SPEC["ref_mass"] * (B_CG / L) / _ref_cr_frac
CR = SPEC["ref_cr"] * SPEC["tire_stiffness_factor"] * MASS / SPEC["ref_mass"] * (A_CG / L) / _ref_cf_frac
K_US = MASS / L * (B_CG / CF - A_CG / CR)   # understeer gradient, rad per m/s^2
LAF = SPEC["lat_accel_factor"]              # lateral acceleration per normalised torque (1500 raw), m/s^2
TORQUE_MAX = 1500                          # STEER_MAX, modes/toyota.h max_torque

# ---------------------------------------------------------------- assumptions (README §3.2)
ASSUME = {
  "vehicle_width": 1.78,          # m, WP-S-04 §3.1 (to be confirmed, OI-1)
  "lane_width": 3.7,              # m, highway lane in the ODD (WP-C-02 §3.1: 2.9-3.9 m)
  "lane_margin_design": 0.6,      # m, WP-S-04 §3.1 design value for the hazard threshold
  "steer_tau": 0.10,              # s, road-wheel angle response to the torque balance (first order)
  "eps_delay": 0.12,              # s, steerActuatorDelay of the Corolla (toyota/interface.py)
  "eps_dropout_ramp": 2.0,        # s, LKA torque decay after 0x2E4 stops (carstate.py:15-16 comment; AOU-01R)
  "a_y_eps_max": 3.0,             # m/s^2, EPS LKA authority when the envelope is defeated (WP-S-04 §3.1: 3-5)
  "driver_rt": 1.0,               # s, reaction to a cue (WP-S-04 §3.2: 0.75-1.5 s)
  "driver_drift_cue": 0.3,        # m, lateral drift a hands-near-wheel driver notices without a warning
  "driver_accel_cue": 0.5,        # m/s^2, unexpected lateral acceleration the driver feels (no warning needed)
  "driver_a_max": 4.0,            # m/s^2, corrective lateral acceleration the driver adds (AOU-02R)
  "driver_ramp": 0.3,             # s, time to build up the driver's correction
  "pcm_tau": 0.3,                 # s, ACC acceleration response (AOU-05R)
  "pcm_hold": 1.0,                # s, PCM keeps the last ACC request after ACC_CONTROL stops (unknown)
  "coast": -0.4,                  # m/s^2, drag with the inactive value (AOU-05R: no step)
  "a_pcs": 6.0,                   # m/s^2, stock PCS braking (WP-S-04 A-PCS-1)
  "relay_release": 0.02,          # s, harness path back to stock after release (WP-S-04 A-PCS-2, upper value)
  "host_alert_latency": 0.2,      # s, panda state -> host alert (pandaStates 10 Hz, 2 samples, TSR-621)
  "host_reset_alert": 0.5,        # s, host alert after a panda reset (DQ-054 context)
}


@dataclass
class Road:
  """Lane centre curvature, piecewise linear in the path length: points (s [m], curvature [1/m]).
  A linear change of curvature is a clothoid transition, as used in highway design."""
  points: list = field(default_factory=lambda: [(0.0, 0.0)])

  def curvature(self, s: float) -> float:
    pts = self.points
    if s <= pts[0][0]:
      return pts[0][1]
    for (s0, k0), (s1, k1) in zip(pts, pts[1:]):
      if s <= s1:
        return k0 + (k1 - k0) * (s - s0) / (s1 - s0)
    return pts[-1][1]


@dataclass
class Lateral:
  v: float          # m/s, constant longitudinal speed for lateral scenarios
  vy: float = 0.0
  r: float = 0.0
  e_y: float = 0.0  # lateral offset from lane centre, + left
  e_psi: float = 0.0
  s: float = 0.0
  delta: float = 0.0

  def a_y(self) -> float:
    return self.v * self.r + self.vy_dot

  vy_dot: float = 0.0

  def steady_delta(self, a_target: float) -> float:
    return a_target / (self.v ** 2) * L + K_US * a_target

  def step(self, dt: float, a_target: float, kappa_road: float) -> None:
    self.delta += (self.steady_delta(a_target) - self.delta) * dt / ASSUME["steer_tau"]
    v = self.v
    af = self.delta - (self.vy + A_CG * self.r) / v
    ar = -(self.vy - B_CG * self.r) / v
    fyf, fyr = CF * af, CR * ar
    self.vy_dot = (fyf + fyr) / MASS - v * self.r
    r_dot = (A_CG * fyf - B_CG * fyr) / IZ
    self.vy += self.vy_dot * dt
    self.r += r_dot * dt
    self.e_y += (v * math.sin(self.e_psi) + self.vy * math.cos(self.e_psi)) * dt
    self.e_psi += (self.r - v * kappa_road) * dt
    self.s += v * dt


class EPS:
  """LKA torque applied by the EPS, in 0x2E4 command units (raw)."""

  def __init__(self, dt: float):
    self.dt = dt
    self.queue = [0.0] * int(round(ASSUME["eps_delay"] / dt))
    self.applied = 0.0
    self.last_cmd = 0.0
    self.since_frame = 0.0
    self.fault = False

  def frame(self, torque: int, steer_req: bool) -> None:
    self.last_cmd = float(torque) if steer_req else 0.0
    self.since_frame = 0.0

  def step(self) -> float:
    self.since_frame += self.dt
    if self.since_frame > 0.025:   # frames missing: decay toward zero (AOU-01R)
      step = TORQUE_MAX * self.dt / ASSUME["eps_dropout_ramp"]
      self.last_cmd = math.copysign(max(abs(self.last_cmd) - step, 0.0), self.last_cmd)
    self.queue.append(0.0 if self.fault else self.last_cmd)
    self.applied = self.queue.pop(0)
    return self.applied


class Driver:
  """Supervising driver, hands near the wheel: notices a cue, reacts after t_r, then steers back to the lane centre."""

  def __init__(self, rt: float | None = None, present: bool = True):
    self.rt = ASSUME["driver_rt"] if rt is None else rt
    self.present = present
    self.cue_t: float | None = None
    self.cue_kind = ""

  def cue(self, t: float, kind: str) -> None:
    if self.present and self.cue_t is None:
      self.cue_t, self.cue_kind = t, kind

  def active(self, t: float) -> float:
    if self.cue_t is None or t < self.cue_t + self.rt:
      return 0.0
    return min(1.0, (t - self.cue_t - self.rt) / ASSUME["driver_ramp"])

  def correction(self, t: float, lat: Lateral, kappa: float, a_assist: float) -> float:
    w = self.active(t)
    if w == 0.0:
      return 0.0
    e_dot = lat.v * math.sin(lat.e_psi) + lat.vy
    a_need = lat.v ** 2 * kappa - 0.8 * lat.e_y - 1.2 * e_dot
    a_drv = max(-ASSUME["driver_a_max"], min(ASSUME["driver_a_max"], a_need - a_assist))
    return w * a_drv


def summary() -> dict:
  return {"mass": MASS, "wheelbase": L, "a": A_CG, "b": B_CG, "iz": IZ, "cf": CF, "cr": CR, "k_us": K_US,
          "steer_ratio": SPEC["steer_ratio"], "laf": LAF}
