import math
import threading
import time
import traceback
from dataclasses import dataclass, field

import openpilot.cereal.messaging as messaging

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus
from opendbc.car.toyota.values import DBC, EPS_SCALE
from openpilot.common.params import Params
from openpilot.selfdrive.pandad.pandad_api_impl import can_list_to_can_capnp
from openpilot.tools.sim.lib.common import SimulatorState
from openpilot.tools.sim.lib.corolla_plant import CAR_FINGERPRINT, CorollaPlant, DriverInput, PlantCommand, corolla_car_params
from openpilot.tools.sim.lib.panda_safety import SimulatedPanda

# Corolla TSS2 radar (toyota_tss2_adas): 16 track slots, TRACK_A at 0x180.., TRACK_B at 0x190..
RADAR_SLOTS = 16
RADAR_RANGE = 160.0           # m (assumption; the radar's range is not measured on the reference vehicle)
RADAR_HALF_FOV = math.radians(10.0)  # rad (assumption)
RADAR_EMPTY_DIST = 327.0      # LONG_DIST of an empty slot (>= 255 means no target)
COMMAND_TIMEOUT = 0.1         # s without an accepted STEERING_LKA / ACC_CONTROL frame before the EPS / PCM drop it (assumption)

GEAR_DRIVE = 0                # GEAR_PACKET.GEAR "D"
CRUISE_STATE_ADAPTIVE_ENGAGED = 8
LKA_STATE_STANDBY = 1
LKA_STATE_ACTIVE = 5
TURN_SIGNALS = {(False, False): 3, (True, False): 1, (False, True): 2}

CRUISE_SET = "set"
CRUISE_CANCEL = "cancel"
CRUISE_MAIN = "main"
CRUISE_ACCEL = "accel"
CRUISE_DECEL = "decel"


@dataclass
class RadarTarget:
  """An object as the radar would report it: dRel from the front bumper, yRel positive left, vRel closing negative."""
  target_id: int
  d_rel: float
  y_rel: float
  v_rel: float


@dataclass
class PcmState:
  main_on: bool = True
  cruise_active: bool = False
  set_speed_kph: float = 0.0
  standstill: bool = False


@dataclass
class CarOutputs:
  """What the simulated car hands to the world each step (read by the bridge thread)."""
  accel: float = 0.0
  curvature: float = 0.0
  steering_angle_deg: float = 0.0
  cruise_active: bool = False
  controls_allowed: bool = False
  tx_blocked: int = 0
  radar_targets: list = field(default_factory=list)


class SimulatedCar:
  """Simulates the reference Corolla (E210, TSS2) to openpilot: its powertrain, radar and camera CAN buses, its PCM and
  EPS (corolla_plant), and a panda that runs the LionDriver safety code on every frame in both directions
  (panda_safety). openpilot's sendcan frames reach the car only if the panda lets them through."""

  def __init__(self):
    self.CP = corolla_car_params()
    self.pm = messaging.PubMaster(['can', 'pandaStates'])
    self.sm = messaging.SubMaster(['carParams', 'selfdriveState'])
    self.sendcan_sock = messaging.sub_sock('sendcan', conflate=False, timeout=0)
    self.params = Params()

    pt_dbc = DBC[CAR_FINGERPRINT][Bus.pt]
    self.packer = CANPacker(pt_dbc)
    self.radar_packer = CANPacker(DBC[CAR_FINGERPRINT][Bus.radar])
    self.tx_parser = CANParser(pt_dbc, [("STEERING_LKA", float('nan')), ("ACC_CONTROL", float('nan'))], 0)
    self.eps_scale = EPS_SCALE[CAR_FINGERPRINT]

    safety = self.CP.safetyConfigs[0]
    self.panda = SimulatedPanda(safety.safetyModel, safety.safetyParam)
    self.plant = CorollaPlant(self.CP)
    self.cmd = PlantCommand()
    self.pcm = PcmState()
    self.radar_slots: dict[int, int] = {}   # target_id -> slot
    self.radar_targets: list[RadarTarget] = []

    self.lock = threading.Lock()
    self.outputs = CarOutputs()
    self.engaged = False
    self.engageable = False
    self.idx = 0
    self.obd_multiplexing = False
    self.last_lka = -1e9
    self.last_acc = -1e9

  # *** openpilot -> panda -> car ***

  def receive_sendcan(self):
    allowed = []
    for msg in messaging.drain_sock(self.sendcan_sock):
      for c in msg.sendcan:
        if self.panda.tx(c.address, bytes(c.dat), c.src):
          allowed.append((c.address, bytes(c.dat), c.src))
    now = time.monotonic()
    if allowed:
      updated = self.tx_parser.update([(int(now * 1e9), allowed)])
      if 0x2E4 in updated:
        self.last_lka = now
      if 0x343 in updated:
        self.last_acc = now
    lka = self.tx_parser.vl["STEERING_LKA"]
    acc = self.tx_parser.vl["ACC_CONTROL"]
    # the EPS and the PCM drop a command whose frames stopped arriving
    lka_fresh = now - self.last_lka < COMMAND_TIMEOUT
    acc_fresh = now - self.last_acc < COMMAND_TIMEOUT
    self.cmd = PlantCommand(steer_torque=int(lka["STEER_TORQUE_CMD"]) if lka_fresh else 0,
                            steer_request=bool(lka["STEER_REQUEST"]) and lka_fresh,
                            accel=float(acc["ACCEL_CMD"]) if acc_fresh else 0.0,
                            cancel=bool(acc["CANCEL_REQ"]) and acc_fresh)

  def update_pcm(self, state: SimulatorState):
    pcm = self.pcm
    speed_kph = state.speed * 3.6
    button, state.cruise_button = state.cruise_button, ""  # a press is consumed once
    if button == CRUISE_MAIN:
      pcm.main_on = not pcm.main_on
      pcm.cruise_active = False
    if self.cmd.cancel or state.user_brake > 0 or button == CRUISE_CANCEL or not pcm.main_on:
      pcm.cruise_active = False
    elif button == CRUISE_SET:
      if not pcm.cruise_active:
        pcm.set_speed_kph = state.cruise_set_speed_kph or max(round(speed_kph), 30)
      pcm.cruise_active = True
    if pcm.cruise_active and button == CRUISE_ACCEL:
      pcm.set_speed_kph += 5
    if pcm.cruise_active and button == CRUISE_DECEL:
      pcm.set_speed_kph = max(pcm.set_speed_kph - 5, 30)
    pcm.standstill = pcm.cruise_active and state.speed < 0.1 and self.plant.accel <= 0

  # *** car -> panda -> openpilot ***

  def car_frames(self, state: SimulatorState) -> list:
    p, pcm, plant, i = self.packer, self.pcm, self.plant, self.idx
    speed_kph = state.speed * 3.6
    driver_torque = state.user_torque
    msgs = [
      p.make_can_msg("WHEEL_SPEEDS", 0, {f"WHEEL_SPEED_{w}": speed_kph for w in ("FL", "FR", "RL", "RR")}),
      p.make_can_msg("STEER_ANGLE_SENSOR", 0, {"STEER_ANGLE": plant.steering_angle_deg, "STEER_RATE": plant.steering_rate_deg}),
    ]
    if i % 2 == 0:
      msgs += [
        p.make_can_msg("STEER_TORQUE_SENSOR", 0, {
          "STEER_ANGLE": plant.steering_angle_deg,
          "STEER_TORQUE_DRIVER": driver_torque,
          "STEER_TORQUE_EPS": plant.eps_torque / self.eps_scale * 100.,
          "STEER_OVERRIDE": int(abs(driver_torque) > 500),
        }),
        p.make_can_msg("BRAKE_MODULE", 0, {"BRAKE_PRESSED": int(state.user_brake > 0)}),
        p.make_can_msg("VSC1S07", 0, {"GVC": plant.accel / 9.81}),
      ]
    if i % 3 == 0:
      msgs += [
        p.make_can_msg("PCM_CRUISE", 0, {
          "CRUISE_ACTIVE": int(pcm.cruise_active),
          "CRUISE_STATE": 7 if pcm.standstill else (CRUISE_STATE_ADAPTIVE_ENGAGED if pcm.cruise_active else 0),
          "GAS_RELEASED": int(state.user_gas <= 0),
          "ACCEL_NET": plant.accel,
        }),
        p.make_can_msg("PCM_CRUISE_2", 0, {
          "MAIN_ON": int(pcm.main_on),
          "SET_SPEED": pcm.set_speed_kph if pcm.cruise_active else 0,
          "LOW_SPEED_LOCKOUT": 1,
          "BRAKE_PRESSED": int(state.user_brake > 0),
        }),
      ]
    if i % 4 == 0:
      lka = LKA_STATE_ACTIVE if (self.cmd.steer_request and self.panda.controls_allowed) else LKA_STATE_STANDBY
      msgs.append(p.make_can_msg("EPS_STATUS", 0, {"LKA_STATE": lka, "TYPE": 1}))
    if i % 10 == 0:
      msgs += [
        p.make_can_msg("GEAR_PACKET", 0, {"GEAR": GEAR_DRIVE}),
        p.make_can_msg("BODY_CONTROL_STATE", 0, {}),
        p.make_can_msg("BODY_CONTROL_STATE_2", 0, {"UNITS": 1}),
        p.make_can_msg("ESP_CONTROL", 0, {}),
        p.make_can_msg("PCM_CRUISE_SM", 0, {"MAIN_ON": int(pcm.main_on), "UI_SET_SPEED": pcm.set_speed_kph}),
        p.make_can_msg("BLINKERS_STATE", 0, {"TURN_SIGNALS": TURN_SIGNALS[(state.left_blinker, state.right_blinker)]}),
        p.make_can_msg("LIGHT_STALK", 0, {}),
        # stock ADAS camera, cut off by the harness relay: its frames arrive on bus 2 only
        p.make_can_msg("ACC_CONTROL", 2, {"ACC_TYPE": 1}),
        p.make_can_msg("PCS_HUD", 2, {}),
        p.make_can_msg("LKAS_HUD", 2, {}),
        p.make_can_msg("PRE_COLLISION", 2, {}),
      ]
    if i % 5 == 0:
      msgs += self.radar_frames(with_status=(i % 10 == 0))
    return msgs

  def radar_frames(self, with_status: bool) -> list:
    rp = self.radar_packer
    visible = sorted((t for t in self.radar_targets
                      if 0 < t.d_rel <= RADAR_RANGE and abs(math.atan2(t.y_rel, t.d_rel)) <= RADAR_HALF_FOV),
                     key=lambda t: t.d_rel)[:RADAR_SLOTS]
    ids = {t.target_id for t in visible}
    self.radar_slots = {tid: s for tid, s in self.radar_slots.items() if tid in ids}
    free = [s for s in range(RADAR_SLOTS) if s not in self.radar_slots.values()]
    new_ids = set()
    for t in visible:
      if t.target_id not in self.radar_slots:
        self.radar_slots[t.target_id] = free.pop(0)
        new_ids.add(t.target_id)
    by_slot = {s: t for t in visible for tid, s in self.radar_slots.items() if tid == t.target_id}

    frames_a, frames_b = [], []
    for s in range(RADAR_SLOTS):
      t = by_slot.get(s)
      if t is None:
        frames_a.append(rp.make_can_msg(f"TRACK_A_{s}", 1, {"VALID": 0, "LONG_DIST": RADAR_EMPTY_DIST}))
        frames_b.append(rp.make_can_msg(f"TRACK_B_{s}", 1, {"SCORE": 0}))
      else:
        frames_a.append(rp.make_can_msg(f"TRACK_A_{s}", 1, {
          "VALID": 1, "NEW_TRACK": int(t.target_id in new_ids),
          "LONG_DIST": t.d_rel, "LAT_DIST": -t.y_rel, "REL_SPEED": t.v_rel}))
        frames_b.append(rp.make_can_msg(f"TRACK_B_{s}", 1, {"SCORE": 100}))
    frames = frames_a + frames_b
    if with_status:
      frames.append(rp.make_can_msg("STATUS_MSG", 1, {"RADAR_STATUS": 1}))
    return frames

  def send_can_messages(self, state: SimulatorState):
    if not state.valid:
      return
    frames = self.car_frames(state)
    for addr, dat, bus in frames:
      self.panda.rx(addr, dat, bus)
    self.pm.send('can', can_list_to_can_capnp(frames))

  def send_panda_state(self, state: SimulatorState):
    if self.params.get_bool("ObdMultiplexingEnabled") != self.obd_multiplexing:
      self.obd_multiplexing = not self.obd_multiplexing
      self.params.put_bool("ObdMultiplexingChanged", True, block=True)

    dat = messaging.new_message('pandaStates', 1)
    dat.valid = True
    dat.pandaStates[0] = {
      'ignitionLine': state.ignition,
      'pandaType': "redPanda",
      'controlsAllowed': self.panda.controls_allowed,
      'safetyModel': 'toyota',
      'safetyParam': self.panda.safety_param,
      'alternativeExperience': self.sm["carParams"].alternativeExperience,
      'safetyRxChecksInvalid': self.panda.rx_checks_invalid,
      'safetyTxBlocked': self.panda.tx_blocked,
      'epsFault': self.panda.eps_fault,
      'txRateExceeded': self.panda.tx_rate_exceeded,
      'referenceBuild': True,
    }
    self.pm.send('pandaStates', dat)

  def update(self, state: SimulatorState):
    try:
      self.sm.update(0)
      self.engaged = self.sm['selfdriveState'].enabled
      self.engageable = self.sm['selfdriveState'].engageable

      self.receive_sendcan()
      self.update_pcm(state)
      allowed = self.panda.controls_allowed
      self.plant.step(state.speed, self.cmd, DriverInput(state.user_torque, state.user_gas, state.user_brake),
                      self.pcm.cruise_active)
      with self.lock:
        self.radar_targets = list(state.radar_targets)
        self.outputs = CarOutputs(self.plant.accel, self.plant.curvature, self.plant.steering_angle_deg,
                                  self.pcm.cruise_active, allowed, self.panda.tx_blocked)

      self.send_can_messages(state)
      # pandad sends the heartbeat with selfdriveState.enabled; the safety task runs at 100 Hz
      self.panda.tick(self.engaged)
      if self.idx % 10 == 0:
        self.send_panda_state(state)
      self.idx += 1
    except Exception:
      traceback.print_exc()
      raise

  def get_outputs(self) -> CarOutputs:
    with self.lock:
      return self.outputs
