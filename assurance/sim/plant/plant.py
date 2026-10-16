"""The vehicle plant behind the interface of ../INTERFACE.md: EPS, PCM and the CommonRoad single-track Corolla.

Fidelity level L1. Every harness drives this one class: the fault-injection loop (simulate.py) directly, and FMI
tools through the FMU wrapper (fmu/corolla_plant_fmu.py). A plant of another fidelity level replaces it behind the
same inputs and outputs. The driver and the road are not part of it: they are the harness's.
"""

from __future__ import annotations

import corolla
from vehiclemodels.vehicle_dynamics_st import vehicle_dynamics_st

STEER_MAX = 1500         # opendbc toyota CarControllerParams.STEER_MAX
STEER_TRACK_S = 0.02     # the front-wheel angle follows its target with this time constant (numerical, not physical)


class EPS:
  """LKA torque with a first-order lag; lateral acceleration from the openpilot torque model (assumed, MD-04)."""

  def __init__(self, d, frame_timeout: float):
    self.d = d
    self.timeout = frame_timeout
    self.last_cmd, self.last_req, self.last_t = 0, 0, -1e9
    self.torque = 0.0
    self.fault = False

  def frame(self, t, torque, req):
    self.last_cmd, self.last_req, self.last_t = torque, req, t

  def step(self, t, dt):
    cmd = self.last_cmd if (self.last_req and t - self.last_t <= self.timeout and not self.fault) else 0.0
    self.torque += (cmd - self.torque) * min(dt / self.d["tau_eps"], 1.0)

  def lat_accel(self):
    return self.d["lat_accel_factor"] * self.torque / STEER_MAX


class PCM:
  """Acceleration request with a first-order lag; taken as 0 after a frame timeout (assumed)."""

  def __init__(self, d, frame_timeout: float):
    self.d = d
    self.timeout = frame_timeout
    self.cmd, self.last_t = 0.0, -1e9
    self.accel = 0.0

  def frame(self, t, accel):
    self.cmd, self.last_t = accel, t

  def step(self, t, dt):
    cmd = self.cmd if t - self.last_t <= self.timeout else 0.0
    self.accel += (cmd - self.accel) * min(dt / self.d["tau_pcm"], 1.0)


def rk4(x, u, p, dt):
  def f(xx):
    return vehicle_dynamics_st(xx, u, p)
  k1 = f(x)
  k2 = f([a + 0.5 * dt * b for a, b in zip(x, k1)])
  k3 = f([a + 0.5 * dt * b for a, b in zip(x, k2)])
  k4 = f([a + dt * b for a, b in zip(x, k3)])
  return [a + dt / 6.0 * (b1 + 2 * b2 + 2 * b3 + b4) for a, b1, b2, b3, b4 in zip(x, k1, k2, k3, k4)]


class CorollaPlant:
  """State x = [sx, sy, delta, v, psi, psi_dot, beta] of the CommonRoad single-track model (reference point CoG)."""

  def __init__(self, v0: float, eps_timeout: float, pcm_timeout: float, d: dict | None = None, p=None):
    self.d = d or corolla.as_dict()
    self.p = p if p is not None else corolla.commonroad_parameters()
    self.eps = EPS(self.d, eps_timeout)
    self.pcm = PCM(self.d, pcm_timeout)
    self.x = [0.0, 0.0, 0.0, v0, 0.0, 0.0, 0.0]
    self.ax = 0.0

  # inputs (INTERFACE.md §1)
  def lka_frame(self, t, torque, req):
    self.eps.frame(t, torque, req)

  def acc_frame(self, t, accel):
    self.pcm.frame(t, accel)

  def set_eps_fault(self, fault: bool):
    self.eps.fault = fault

  def step(self, t: float, dt: float, driver_ay: float = 0.0, driver_ax: float = 0.0):
    """Advance by dt. driver_ay / driver_ax: the driver's added lateral and longitudinal acceleration."""
    v = self.x[3]
    self.eps.step(t, dt)
    self.pcm.step(t, dt)
    delta_t = corolla.steer_for_lat_accel(self.eps.lat_accel() + driver_ay, v, self.d)
    self.ax = self.pcm.accel + driver_ax
    self.x = rk4(self.x, [(delta_t - self.x[2]) / STEER_TRACK_S, self.ax], self.p, dt)

  # outputs (INTERFACE.md §2)
  @property
  def speed(self):
    return self.x[3]

  @property
  def eps_torque(self):
    return self.eps.torque

  @property
  def ay(self):
    return self.x[3] * self.x[5]
