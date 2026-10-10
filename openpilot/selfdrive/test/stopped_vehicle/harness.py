"""
Closed-loop SIL harness for CA-002 (FI-2026-001).

Runs the real radard lead selection (RadarD) and the real LongitudinalPlanner / MPC
against a synthetic scene. Perception is idealized: vision confirms the target once
it is within the scenario's vision range, and radar reports it within radar range.
The car is the reference vehicle (Toyota Corolla TSS2): commanded acceleration is
applied after CP.longitudinalActuatorDelay, with perfect tracking. The driver and
stock AEB are not modeled, so results describe openpilot alone (RCA barrier L1).
"""
from collections import deque
from dataclasses import dataclass
from typing import cast

from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from opendbc.car.structs import car
from openpilot.cereal import log
import openpilot.cereal.messaging as messaging
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.longcontrol import LongCtrlState
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.radard import RADAR_TO_CAMERA, RadarD
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.selfdrive.test.stopped_vehicle.scenarios import Scenario

REFERENCE_CAR = CAR.TOYOTA_COROLLA_TSS2


@dataclass
class Result:
  scenario: Scenario
  collided: bool
  impact_speed: float  # closing speed at impact, m/s
  min_gap: float
  first_detection_gap: float | None  # gap when radarState.leadOne first became present
  fcw_ttc: float | None  # time-to-collision when the planner FCW first fired
  peak_decel: float  # most negative applied acceleration, m/s^2


class FakeSubMaster:
  """The parts of SubMaster that RadarD.update reads."""
  def __init__(self):
    self.data = {}
    self.seen = {'modelV2': True}
    self.recv_frame = {'carState': 0}
    self.logMonoTime = {'modelV2': 0}

  def __getitem__(self, key):
    return self.data[key]

  def all_checks(self):
    return True


def lead_v3(lead, prob, gap, v_target, y_rel):
  lead.prob = prob
  lead.x = [float(gap + RADAR_TO_CAMERA)]
  lead.y = [float(-y_rel)]
  lead.v = [float(v_target)]
  lead.a = [0.]
  lead.xStd = [float(max(1., 0.05 * gap))]
  lead.yStd = [0.5]
  lead.vStd = [1.]


def run(scenario: Scenario) -> Result:
  CP = CarInterface.get_non_essential_params(REFERENCE_CAR)
  planner = LongitudinalPlanner(CP, init_v=scenario.v_ego)
  radard = RadarD(CP.radarDelay)
  sm = FakeSubMaster()

  delay_steps = max(1, round(CP.longitudinalActuatorDelay / DT_MDL))
  accel_queue = deque([0.] * delay_steps, maxlen=delay_steps)

  v_ego, a_ego, x_ego = scenario.v_ego, 0., 0.
  x_target = scenario.initial_gap
  first_detection_gap = fcw_ttc = None
  min_gap = scenario.initial_gap
  peak_decel = 0.
  stopped_frames = 0

  for frame in range(int(scenario.duration / DT_MDL)):
    t = frame * DT_MDL
    gap = x_target - x_ego
    closing = v_ego - scenario.v_target
    observable = t >= scenario.reveal_time
    vision = observable and gap <= scenario.vision_range
    radar = observable and scenario.radar_range > 0 and gap <= scenario.radar_range

    car_state = car.CarState.new_message(vEgo=float(v_ego), aEgo=float(a_ego), standstill=bool(v_ego < 0.01),
                                         vCruise=float(scenario.v_ego * 3.6))

    model = log.ModelDataV2.new_message()
    leads = model.init('leadsV3', 2)
    lead_v3(leads[0], 1. if vision else 0., gap, scenario.v_target, scenario.lateral_offset)
    lead_v3(leads[1], 0., gap, scenario.v_target, scenario.lateral_offset)
    model.velocity.x = [float(v_ego)] * len(ModelConstants.T_IDXS)
    model.position.x = [float(v_ego * t_idx) for t_idx in ModelConstants.T_IDXS]
    model.acceleration.x = [0.] * len(ModelConstants.T_IDXS)
    model.meta.disengagePredictions.gasPressProbs = [1.] * 6

    radar_data = car.RadarData.new_message()
    if radar:
      pts = radar_data.init('points', 1)
      pts[0].trackId = 1
      pts[0].dRel = float(gap)
      pts[0].yRel = float(scenario.lateral_offset)
      pts[0].vRel = float(scenario.v_target - v_ego)

    sm.data = {'modelV2': model, 'carState': car_state}
    sm.recv_frame['carState'] = frame + 1
    radard.update(cast(messaging.SubMaster, sm), radar_data)
    radar_state = radard.radar_state

    if first_detection_gap is None and radar_state.leadOne.present:
      first_detection_gap = gap

    controls_state = log.ControlsState.new_message(longControlState=LongCtrlState.pid)
    selfdrive_state = log.SelfdriveState.new_message(personality=log.LongitudinalPersonality.standard)
    planner.update({
      'radarState': radar_state,
      'carState': car_state,
      'carControl': car.CarControl.new_message(orientationNED=[0., 0., 0.]),
      'controlsState': controls_state,
      'selfdriveState': selfdrive_state,
      'vehicleParameters': log.VehicleParameters.new_message(),
      'modelV2': model,
    })

    if planner.fcw and fcw_ttc is None:
      fcw_ttc = gap / closing if closing > 0 else float('inf')

    # actuator: commanded accel takes effect after the actuator delay
    a_ego = accel_queue[0]
    accel_queue.append(float(planner.output_a_target))
    peak_decel = min(peak_decel, a_ego)

    v_ego = max(0., v_ego + a_ego * DT_MDL)
    if v_ego == 0.:
      a_ego = 0.
    x_ego += v_ego * DT_MDL
    x_target += scenario.v_target * DT_MDL

    gap = x_target - x_ego
    min_gap = min(min_gap, gap)
    if gap <= 0.:
      return Result(scenario, True, v_ego - scenario.v_target, gap, first_detection_gap, fcw_ttc, peak_decel)

    # done once the ego has matched the target's speed for a second
    stopped_frames = stopped_frames + 1 if v_ego <= scenario.v_target + 0.05 else 0
    if stopped_frames * DT_MDL >= 1.:
      break

  return Result(scenario, False, 0., min_gap, first_detection_gap, fcw_ttc, peak_decel)
