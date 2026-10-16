"""FMI 2.0 co-simulation wrapper of the L1 plant (pythonfmu, MIT). Built by build_fmu.py; run by any FMI 2.0 master,
FMPy (BSD-2-Clause) in the tests. Inputs and outputs follow ../../INTERFACE.md.

STEERING_LKA and ACC_CONTROL frames are passed as values plus a frame counter: the plant takes a frame as received
when its counter changes, so the master's step can be longer than one frame period.
"""

import json
from pathlib import Path

from pythonfmu import Boolean, Fmi2Causality, Fmi2Slave, Fmi2Variability, Integer, Real

import corolla
from plant import CorollaPlant

DT = 0.005


class CorollaPlantFMU(Fmi2Slave):
  author = "LionDriver simulation track"
  description = "Corolla E210 L1 plant: EPS and PCM lags, CommonRoad single-track model (assumed parameters marked)"

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.v0, self.eps_timeout, self.pcm_timeout = 33.33, 0.03, 0.10
    self.lka_torque, self.lka_request, self.lka_frames = 0.0, False, 0
    self.accel_cmd, self.acc_frames = 0.0, 0
    self.eps_fault = False
    self.driver_ay, self.driver_ax = 0.0, 0.0
    self.sx = self.sy = self.delta = self.v = self.psi = self.yaw_rate = self.beta = 0.0
    self.eps_torque = self.ax = self.ay = 0.0
    for name in ("v0", "eps_timeout", "pcm_timeout"):
      self.register_variable(Real(name, causality=Fmi2Causality.parameter, variability=Fmi2Variability.tunable))
    for name in ("lka_torque", "accel_cmd", "driver_ay", "driver_ax"):
      self.register_variable(Real(name, causality=Fmi2Causality.input))
    for name in ("lka_frames", "acc_frames"):
      self.register_variable(Integer(name, causality=Fmi2Causality.input, variability=Fmi2Variability.discrete))
    for name in ("lka_request", "eps_fault"):
      self.register_variable(Boolean(name, causality=Fmi2Causality.input, variability=Fmi2Variability.discrete))
    for name in ("sx", "sy", "delta", "v", "psi", "yaw_rate", "beta", "eps_torque", "ax", "ay"):
      self.register_variable(Real(name, causality=Fmi2Causality.output))
    self.plant = None
    self._lka_seen = self._acc_seen = 0

  def exit_initialization_mode(self):
    d = json.loads((Path(self.resources) / "parameters.json").read_text())
    self.plant = CorollaPlant(self.v0, self.eps_timeout, self.pcm_timeout, d, corolla.commonroad_parameters(d))
    self._outputs()

  def do_step(self, current_time, step_size):
    pl = self.plant
    if self.lka_frames != self._lka_seen:
      self._lka_seen = self.lka_frames
      pl.lka_frame(current_time, self.lka_torque, int(self.lka_request))
    if self.acc_frames != self._acc_seen:
      self._acc_seen = self.acc_frames
      pl.acc_frame(current_time, self.accel_cmd)
    pl.set_eps_fault(bool(self.eps_fault))
    n = max(1, round(step_size / DT))
    for i in range(n):
      t = current_time + i * step_size / n
      v = pl.speed
      pl.step(t, step_size / n, self.driver_ay, self.driver_ax)
      self.ay = v * pl.x[5]
    self._outputs()
    return True

  def _outputs(self):
    x = self.plant.x
    self.sx, self.sy, self.delta, self.v, self.psi, self.yaw_rate, self.beta = x
    self.eps_torque, self.ax = self.plant.eps_torque, self.plant.ax
