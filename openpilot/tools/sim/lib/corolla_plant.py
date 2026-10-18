"""Actuator and vehicle-response model of the reference Corolla (E210, TSS2) for the closed-loop simulator.

The simulator does not take openpilot's intent from carControl. It takes the CAN frames openpilot sent that the
panda safety code let through (STEERING_LKA, ACC_CONTROL) and turns them into vehicle motion with this model:

Lateral (EPS, torque control, LKA):
  - the EPS applies the commanded torque after a first-order lag (EPS_TAU) and while STEER_REQUEST is set;
  - the applied torque produces lateral acceleration through the same linear torque map openpilot's torque
    controller assumes for this platform (latAccelFactor of CarParams), after the rest of steerActuatorDelay;
  - driver torque adds to it (DRIVER_TORQUE_TO_LAT_ACCEL) and is reported on STEER_TORQUE_DRIVER;
  - the steering-wheel angle reported on CAN is the one openpilot's own vehicle model gives for that curvature.

Longitudinal (PCM, openpilot longitudinal through ACC_CONTROL):
  - while cruise is active, the PCM follows ACCEL_CMD after longitudinalActuatorDelay and a first-order lag
    (PCM_TAU); otherwise the car coasts (COAST_DECEL) or follows the scripted driver's gas or brake.

FIDELITY. Every constant below that is not taken from CarParams is an assumption, not a measurement. The plant uses
openpilot's own torque map and vehicle model, so the controller is tested against its own assumptions; that hides
any error in those assumptions. The fidelity case (WP-V-02 §5.3, assurance/06-validation/sim/fidelity-case-plan.md)
replaces these values with measurements from the reference vehicle (VS-VAL-08 PCM onset, lateral step responses)
before any scenario family gets credit.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

from opendbc.car.toyota.values import CAR
from opendbc.car.vehicle_model import VehicleModel

CAR_FINGERPRINT = CAR.TOYOTA_COROLLA_TSS2

DT = 0.01                       # s, plant step (100 Hz, the CAN loop rate)
STEER_MAX = 1500                # STEERING_LKA.STEER_TORQUE_CMD at full authority (CarControllerParams.STEER_MAX)
EPS_TAU = 0.05                  # s, EPS torque lag (assumption)
PCM_TAU = 0.3                   # s, PCM acceleration lag after the dead time (assumption)
COAST_DECEL = -0.3              # m/s^2, drag and rolling resistance with no pedal (assumption)
DRIVER_TORQUE_TO_LAT_ACCEL = 1.0 / 1500.  # (m/s^2) per raw STEER_TORQUE_DRIVER unit (assumption)
DRIVER_BRAKE_DECEL = -4.0       # m/s^2 at full scripted brake (assumption)
DRIVER_GAS_ACCEL = 2.0          # m/s^2 at full scripted gas (assumption)
MIN_SPEED_FOR_CURVATURE = 1.0   # m/s, below this lateral acceleration does not turn into curvature


def corolla_car_params():
  """CarParams of the reference platform, as card builds them for this fingerprint (no firmware query)."""
  from opendbc.car.toyota.interface import CarInterface
  return CarInterface.get_non_essential_params(CAR_FINGERPRINT)


@dataclass
class PlantCommand:
  steer_torque: int = 0         # STEERING_LKA.STEER_TORQUE_CMD of the last frame the panda let through
  steer_request: bool = False   # STEERING_LKA.STEER_REQUEST
  accel: float = 0.0            # ACC_CONTROL.ACCEL_CMD, m/s^2
  cancel: bool = False          # ACC_CONTROL.CANCEL_REQ


@dataclass
class DriverInput:
  steer_torque: float = 0.0     # raw STEER_TORQUE_DRIVER units
  gas: float = 0.0              # 0..1
  brake: float = 0.0            # 0..1


class CorollaPlant:
  def __init__(self, CP=None):
    self.CP = CP if CP is not None else corolla_car_params()
    self.VM = VehicleModel(self.CP)
    self.lat_accel_factor = float(self.CP.lateralTuning.torque.latAccelFactor)
    lat_delay = max(float(self.CP.steerActuatorDelay) - EPS_TAU, 0.0)
    long_delay = float(self.CP.longitudinalActuatorDelay)
    self._lat_buffer = deque([0.0] * max(int(round(lat_delay / DT)), 1), maxlen=max(int(round(lat_delay / DT)), 1))
    self._long_buffer = deque([0.0] * max(int(round(long_delay / DT)), 1), maxlen=max(int(round(long_delay / DT)), 1))
    self.eps_torque = 0.0       # raw torque the EPS applies
    self.accel = 0.0            # m/s^2, actual longitudinal acceleration
    self.lat_accel = 0.0        # m/s^2, actual lateral acceleration
    self.curvature = 0.0        # 1/m
    self.steering_angle_deg = 0.0
    self.steering_rate_deg = 0.0

  def reset(self):
    self.__init__(self.CP)

  def step(self, v_ego: float, cmd: PlantCommand, driver: DriverInput, cruise_active: bool) -> None:
    # EPS
    target = float(np.clip(cmd.steer_torque, -STEER_MAX, STEER_MAX)) if cmd.steer_request else 0.0
    self.eps_torque += (target - self.eps_torque) * DT / EPS_TAU
    self._lat_buffer.append(self.eps_torque / STEER_MAX * self.lat_accel_factor
                            + driver.steer_torque * DRIVER_TORQUE_TO_LAT_ACCEL)
    self.lat_accel = self._lat_buffer[0]
    v = max(v_ego, MIN_SPEED_FOR_CURVATURE)
    self.curvature = self.lat_accel / v ** 2 if v_ego > MIN_SPEED_FOR_CURVATURE else 0.0
    angle = float(np.degrees(self.VM.get_steer_from_curvature(self.curvature, v, 0.0)))
    self.steering_rate_deg = (angle - self.steering_angle_deg) / DT
    self.steering_angle_deg = angle

    # PCM and driver pedals
    if driver.brake > 0:
      a_target = DRIVER_BRAKE_DECEL * driver.brake
    elif driver.gas > 0:
      a_target = max(DRIVER_GAS_ACCEL * driver.gas, cmd.accel if cruise_active else COAST_DECEL)
    elif cruise_active:
      a_target = cmd.accel
    else:
      a_target = COAST_DECEL
    self._long_buffer.append(a_target)
    self.accel += (self._long_buffer[0] - self.accel) * DT / PCM_TAU
    if v_ego <= 0.0 and self.accel < 0.0:
      self.accel = 0.0
