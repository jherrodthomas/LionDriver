import math

import numpy as np

import openpilot.cereal.messaging as messaging
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.common.constants import CV
from openpilot.common.realtime import DT_MDL
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_planner import (A_CRUISE_MAX_BP, A_CRUISE_MIN, A_MINIMUM_RISK_STOP,
                                                                   J_CRUISE_VALS, J_MINIMUM_RISK_STOP, LongitudinalPlanner,
                                                                   get_cruise_accel, get_max_accel)
from openpilot.selfdrive.modeld.constants import ModelConstants

# LionDriver TSR-633 (register DQ-424 A): the minimum-risk forced stop after an unresponsive driver ramps in to 2 m/s² and
# holds it to standstill, within the envelope's a_min (TSR-202) and j_down (TSR-205). Normal cruise and the fault
# soft-disable slow-down keep upstream's A_CRUISE_MIN.

REFERENCE = TOYOTA.TOYOTA_COROLLA_TSS2
A_MIN = -3.5     # m/s², TSR-202 a_min (ACCEL_CMD floor of the envelope)
J_DOWN = 5.0     # m/s³, TSR-205 j_down, provisional value of WP-W-02 §2.5
V0 = 110 * CV.KPH_TO_MS


def kinematic_stop(v0, a, jerk):
  """(time s, distance m) to standstill from v0, ramping in from 0 at jerk, then holding deceleration a."""
  tr = a / jerk
  v1 = v0 - jerk * tr ** 2 / 2
  return tr + v1 / a, v0 * tr - jerk * tr ** 3 / 6 + v1 ** 2 / (2 * a)


def upstream_cruise_accel(e2e, v_cruise, v_ego, a_cruise_prev, angle_steers, CP, dt, accel_coast, allow_throttle):
  """get_cruise_accel as upstream openpilot has it (liondriver-dev before DQ-424), to show normal cruise is unchanged."""
  max_accel = 2.0 if e2e else get_max_accel(v_ego)
  if not e2e:
    a_total_max = np.interp(v_ego, [20., 40.], [1.7, 3.2])
    a_y = v_ego ** 2 * angle_steers * CV.DEG_TO_RAD / (CP.steerRatio * CP.wheelbase)
    a_x_allowed = math.sqrt(max(a_total_max ** 2 - a_y ** 2, 0.))
    max_accel = min(max_accel, a_x_allowed)
    if not allow_throttle:
      clipped_accel_coast = max(accel_coast, -3.5)
      coast_limit = np.interp(v_ego, [2.5, 5.0], [max_accel, clipped_accel_coast])
      max_accel = min(max_accel, coast_limit)
  target_accel = np.clip(v_cruise - v_ego, -1.2, max_accel)
  j_cruise = np.interp(v_ego, A_CRUISE_MAX_BP, J_CRUISE_VALS)
  return float(np.clip(target_accel, a_cruise_prev - j_cruise * dt, a_cruise_prev + j_cruise * dt))


class Drive:
  """The longitudinal planner on the reference car, closed over a plant that follows its output exactly."""

  def __init__(self, speed, v_cruise=V0):
    self.CP = CarInterface.get_non_essential_params(REFERENCE)
    self.planner = LongitudinalPlanner(self.CP, init_v=speed)
    self.speed, self.distance, self.v_cruise = speed, 0.0, v_cruise
    self.accel = 0.0

  def step(self, force_decel=False, minimum_risk=False):
    model = messaging.new_message('modelV2')
    model.modelV2.position.x = [float(x) for x in (self.speed + 0.5) * np.array(ModelConstants.T_IDXS)]
    model.modelV2.velocity.x = [float(self.speed)] * len(ModelConstants.T_IDXS)
    model.modelV2.acceleration.x = [0.0] * len(ModelConstants.T_IDXS)
    model.modelV2.meta.disengagePredictions.gasPressProbs = [1.0] * 6
    model.modelV2.action.desiredAcceleration = float(self.accel)
    cs = messaging.new_message('controlsState')
    cs.controlsState.longControlState = LongCtrlState.pid
    cs.controlsState.forceDecel = force_decel
    ss = messaging.new_message('selfdriveState')
    ss.selfdriveState.enabled = True
    ss.selfdriveState.minimumRiskManeuver = minimum_risk
    car_state = messaging.new_message('carState')
    car_state.carState.vEgo = float(self.speed)
    car_state.carState.standstill = bool(self.speed < 0.01)
    car_state.carState.vCruise = float(self.v_cruise * CV.MS_TO_KPH)
    car_control = messaging.new_message('carControl')
    car_control.carControl.orientationNED = [0., 0., 0.]
    radar = messaging.new_message('radarState')
    radar.radarState.leadOne.dRel = 200.
    radar.radarState.leadTwo.dRel = 200.
    sm = {'radarState': radar.radarState, 'carState': car_state.carState, 'carControl': car_control.carControl,
          'controlsState': cs.controlsState, 'selfdriveState': ss.selfdriveState,
          'vehicleParameters': messaging.new_message('vehicleParameters').vehicleParameters, 'modelV2': model.modelV2}
    self.planner.update(sm)
    a = float(self.planner.output_a_target)
    self.accel = min(-0.5, a) if self.planner.output_should_stop else a   # as the maneuver plant
    self.speed = max(0.0, self.speed + self.accel * DT_MDL)
    self.distance += self.speed * DT_MDL
    return a

  def forced_stop(self, minimum_risk, max_s=60.):
    """Run the forced stop to standstill: (planner a_target per step, time s, distance m)."""
    start, out = self.distance, []
    while self.speed > 0. and len(out) * DT_MDL < max_s:
      out.append(self.step(force_decel=True, minimum_risk=minimum_risk))
    return np.array(out), len(out) * DT_MDL, self.distance - start


class TestMinimumRiskStop(OpenpilotTestCase):
  """TSR-633 (DQ-424 A): from 110 km/h the stop ramps in to 2 m/s², holds it and reaches standstill in about 15.5 s, 240 m"""

  def test_constants_inside_the_envelope(self):
    assert A_MINIMUM_RISK_STOP == -2.0
    assert A_MIN < A_MINIMUM_RISK_STOP < A_CRUISE_MIN
    assert 0. < J_MINIMUM_RISK_STOP < J_DOWN

  def test_stop_time_and_distance_from_110_kmh(self):
    drive = Drive(V0)
    for _ in range(40):            # 2 s of steady cruise at the set speed first
      drive.step()
    _, t, d = drive.forced_stop(minimum_risk=True)
    t_k, d_k = kinematic_stop(V0, -A_MINIMUM_RISK_STOP, J_MINIMUM_RISK_STOP)
    assert abs(t_k - 15.5) < 0.1 and abs(d_k - 240.) < 2.     # the closed form behind "about 15.5 s and 240 m"
    self.assertAlmostEqual(t, t_k, delta=0.25)
    self.assertAlmostEqual(d, d_k, delta=0.02 * d_k)

  def test_ramps_in_and_holds_the_rate_to_standstill(self):
    drive = Drive(V0)
    for _ in range(40):
      drive.step()
    a, _, _ = drive.forced_stop(minimum_risk=True)
    ramp = int(round(-A_MINIMUM_RISK_STOP / J_MINIMUM_RISK_STOP / DT_MDL))
    assert a[0] > A_MINIMUM_RISK_STOP / 2                       # no step at onset
    np.testing.assert_allclose(a[ramp:], A_MINIMUM_RISK_STOP, atol=1e-6)   # held to standstill, no taper at low speed

  def test_within_a_min_and_j_down(self):
    # from several speeds, and from a car still accelerating to its set speed when the stop starts
    for v_start, v_set, warmup in [(V0, V0, 40), (25., 25., 40), (10., 10., 40), (20., 30., 20), (3., 3., 40)]:
      with self.subTest(v_start=v_start, v_set=v_set):
        drive = Drive(v_start, v_cruise=v_set)
        prev = [drive.step() for _ in range(warmup)][-1]
        a, _, _ = drive.forced_stop(minimum_risk=True)
        assert drive.speed == 0.
        assert a.min() >= A_MINIMUM_RISK_STOP - 1e-6 > A_MIN
        jerk = np.diff(np.concatenate([[prev], a])) / DT_MDL
        assert jerk.min() >= -J_DOWN, f"deceleration onset {jerk.min():.2f} m/s³ is faster than j_down"
        assert jerk.min() >= -J_MINIMUM_RISK_STOP - 1e-6


class TestNormalDrivingUnchanged(OpenpilotTestCase):
  """DQ-424 changes the minimum-risk stop only: cruise and the fault soft-disable slow-down are upstream's"""

  def test_cruise_accel_is_upstream_without_the_stop(self):
    CP = CarInterface.get_non_essential_params(REFERENCE)
    for e2e in (False, True):
      for allow_throttle in (False, True):
        for v_ego in (0., 2., 4., 10., 20., 30.6, 40.):
          for v_cruise in (0., 8., 25., 35.):
            for a_prev in (-2.5, -1.2, -0.3, 0., 0.7, 1.6):
              for angle in (0., 15.):
                args = (e2e, v_cruise, v_ego, a_prev, angle, CP, DT_MDL, -0.4, allow_throttle)
                assert get_cruise_accel(*args) == upstream_cruise_accel(*args), args
                assert get_cruise_accel(*args, minimum_risk_stop=False) == upstream_cruise_accel(*args), args

  def test_soft_disable_slows_at_a_cruise_min(self):
    # controlsd also forces the deceleration while soft disabling after a fault; that stays at A_CRUISE_MIN
    drive = Drive(30.)
    for _ in range(40):
      drive.step()
    a = np.array([drive.step(force_decel=True) for _ in range(200)])
    assert a.min() >= A_CRUISE_MIN - 1e-9
    self.assertAlmostEqual(a[-1], A_CRUISE_MIN)

  def test_latch_flag_alone_does_not_slow_the_car(self):
    # the stop rate applies only while controlsd forces the stop; cruise traces are identical with or without the flag
    traces = []
    for flag in (False, True):
      drive = Drive(30., v_cruise=20.)
      traces.append([drive.step(minimum_risk=flag) for _ in range(300)])
    assert traces[0] == traces[1]
    assert min(traces[0]) >= A_CRUISE_MIN - 1e-9

  def test_normal_slow_down_at_a_cruise_min(self):
    drive = Drive(30., v_cruise=15.)
    a = np.array([drive.step() for _ in range(300)])
    assert a.min() >= A_CRUISE_MIN - 1e-9
    self.assertAlmostEqual(a.min(), A_CRUISE_MIN)
