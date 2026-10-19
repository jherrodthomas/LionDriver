"""Closed loop of the fault-injection plant model.

    SoC stub --frames--> panda (real safety code) --allowed frames--> car bus --> EPS / PCM models --> CommonRoad
    single-track Corolla <-- driver model;  car bus RX frames (wheel speeds, torque sensor, EPS status, PCM cruise,
    brake) --> panda.

Clocks: 1 ms base step; dynamics integrated with RK4 every 5 ms; RX messages at the nominal rates of the Toyota RX
checks; SoC control frames at 100 Hz (ACC_CONTROL every third frame), heartbeat at 10 Hz (WP-S-04 T-10); panda
safety task at 100 Hz; panda 8 Hz tick for the siren; one panda main-loop pass per ms.

Everything here other than the panda code is a model with stated assumptions (ASSUMPTIONS). Results are synthetic
data under DSR-12 and earn no evidence credit (WP-V-02 §5.3).
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import corolla
from corolla import ROOT
from panda_loop import Panda
from plant import STEER_MAX, CorollaPlant
from roads import Road, from_xodr, lane_line_threshold

sys.path.insert(0, str(ROOT / "opendbc_repo"))
from opendbc.car.lateral import apply_meas_steer_torque_limits  # noqa: E402  (host torque limiting, real code)
from opendbc.car.toyota import toyotacan  # noqa: E402  (host frame packing, real code)

DT_US = 1000
DRIVER_KE, DRIVER_KV = 1.5 ** 2, 2 * 1.5   # driver return-to-centre loop (ASSUMPTIONS driver_ay_max)
DYN_EVERY = 5            # dynamics step = 5 ms
EPS_SCALE = 73           # reference safety parameter: EPS torque factor

# Assumptions of the models around the panda code. None is measured; each names what would replace it.
ASSUMPTIONS = {
  "eps_release_s": (0.03, "EPS-release: the EPS stops applying LKA torque 30 ms (3 frames) after the last STEERING_LKA frame. Replace with M-02"),
  "eps_hold_s": (2.0, "EPS-hold: the EPS keeps the last LKA torque for 2 s without frames, the LKA_STATE 9 -> 11 window of T-23. Replace with M-02"),
  "pcm_timeout_s": (0.10, "PCM: acceleration request taken as 0 when no ACC_CONTROL frame arrived for 100 ms (3 frames). Replace with M-03"),
  "driver_t_r_s": (1.5, "driver reaction time from the first cue, upper end of the 0.75-1.5 s of WP-S-04 §3.2 (to be confirmed in WP-C-08 §8)"),
  "driver_lat_cue_m": (0.2, "lateral cue: the driver notices a drift of 0.2 m from the offset at fault onset. No source; WP-C-08 to replace"),
  "driver_long_cue": (1.0, "longitudinal cue: the driver notices an acceleration 1 m/s2 away from the one at fault onset. No source; WP-C-08 to replace"),
  "driver_ay_max": (4.0, "the driver's correction is limited to 4 m/s2 of lateral acceleration and builds up over 0.2 s; it steers back to the lane centre as a critically damped second-order loop at 1.5 rad/s. No source"),
  "driver_brake": (3.0, "a braking driver adds -3 m/s2, built up over 0.3 s. No source"),
  "camera_lka": (0.0, "stock camera LKA is off: its STEERING_LKA frames carry STEER_REQUEST 0 and torque 0"),
  "a_pcs": (6.0, "stock PCS braking deceleration, assumption A-PCS-1 of WP-S-04 §3.6, to be measured (OI-4)"),
  "whatif_siren_on_revoke": (0.0, "what-if, off (0) in every catalog case: when 1, the panda also sounds the siren at its next 8 Hz tick after it revokes steering authority. Not in the reference build; used by silent_stall.py (decision register DQ-404)"),
  "speaker_phase": (0.0, "the 8 Hz tick starts at t = 3 ms; the siren can come up to 125 ms later at another phase"),
}


# Driver-model options for the edge-case search (../search) and its scenes: every one is off by default, so no catalog
# case uses them and plant-results.md does not list them. Set them per run like an assumption (simulate overrides).
DRIVER_OPTIONS = {
  "driver_wrong_s": (0.0, "what-if, off (0): the driver's first correction goes the wrong way for this long, then reverses. No source"),
  "driver_zeta": (1.0, "damping ratio of the driver's return-to-centre loop: 1 is the critically damped loop of driver_ay_max; below 1 the driver over-corrects past the lane centre. No source"),
  "driver_eps_lag_s": (0.0, "the driver feels a change of the item's steering torque this late (first-order lag); 0 at once. No source"),
  "driver_brakes_only": (0.0, "what-if, off (0): when 1 the driver of a lateral case brakes (driver_brake) instead of steering. No source"),
}

_OVERRIDES: dict[str, float] = {}   # per-run assumption values (the search varies e.g. the driver reaction time)


def A(key: str) -> float:
  if key in _OVERRIDES:
    return _OVERRIDES[key]
  return ASSUMPTIONS[key][0] if key in ASSUMPTIONS else DRIVER_OPTIONS[key][0]


ODD_KPH = 110.0        # ODD-H speed bound (decision register DQ-260)
OVERSPEED_KPH = 120.0  # margin cases outside the ODD (rows ending -OS)


@dataclass
class Case:
  id: str
  title: str
  fault: str                  # key of the fault function below
  road: str                   # 'straight', 'curve' (inside the ODD) or 'curve-odd-bound'
  sg: str
  fmea: str
  wpv05: str = ""
  eps: str = "release"        # 'release' or 'hold' (ASSUMPTIONS)
  speed_kph: float = ODD_KPH
  lane_width: float = 3.7     # m; generic roads only (a KS road has its own)
  t_fault: float | None = 6.0  # s; None: when the vehicle reaches the curve
  duration: float = 6.0       # s after the fault
  engaged: bool = True
  figure: bool = False
  longitudinal: bool = False
  note: str = ""
  tsr: str = ""
  pcs: bool = False           # SG-07 case: the stock camera requests PCS braking at the fault onset
  # edge-case search (../search) and its scenes only; no catalog case sets them
  fault_clear: float | None = None   # s after the onset at which the fault clears
  clear_after_correction: float | None = None  # s after the driver's correction starts at which the fault clears
  fault2: str = ""                   # a second fault of this kind, fault2_gap s after the first clears
  fault2_gap: float = 0.5
  lane_change: float | None = None   # s at which the SoC starts an assisted lane change to the left
  lane_change_s: float = 4.0         # duration of that lane change (cosine profile)
  ay_disturbance: float = 0.0        # m/s², a steady lateral push to the left (crosswind or bank, TC-15), built up over
                                     # 2-4 s and added as the driver's input is (an L1 stand-in: no aerodynamics, no roll)


@dataclass
class Result:
  case: Case
  t: list = field(default_factory=list)
  x: list = field(default_factory=list)
  y: list = field(default_factory=list)
  e_y: list = field(default_factory=list)
  s: list = field(default_factory=list)
  ay: list = field(default_factory=list)
  ax: list = field(default_factory=list)
  gap: list = field(default_factory=list)
  torque: list = field(default_factory=list)
  events: dict = field(default_factory=dict)
  t0: float = 0.0
  e0: float = 0.0
  metrics: dict = field(default_factory=dict)

  def event(self, name: str, t: float):
    self.events.setdefault(name, t)


SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"


def scenario_param(ks: str, name: str) -> float:
  """Default of a parameter declared in a scenario file (../scenarios/xosc), e.g. the KS-08 time gap."""
  text = (SCENARIOS / "xosc" / f"{ks}.xosc").read_text(encoding="utf-8")
  return float(re.search(rf'<ParameterDeclaration name="{name}" parameterType="double" value="([^"]*)"', text).group(1))


def make_road(kind: str, v: float, lane_width: float = 3.7) -> Road:
  # a scenario road (OpenDRIVE of ../scenarios/xodr), ego lane -2;
  # curve inside the ODD: required lateral acceleration 1.5 m/s2; at the ODD bound: 2.5 m/s2 (R_ODD = v^2 / 2.5)
  if kind.startswith("KS-"):
    return from_xodr(SCENARIOS / "xodr" / f"{kind}.xodr")
  if kind == "straight":
    return Road("straight highway", lane_width, straight=3000.0, length=1200.0)
  # "curve@<a_y>": a left curve whose steady lateral acceleration at speed v is a_y; "rcurve@<a_y>": the same to the
  # right (scenes of ../blender only; no catalog case uses it)
  # "arc@<a_y>:<L>" / "rarc@<a_y>:<L>": the same left / right curve with an exit: L m of arc, then a 100 m clothoid back
  # to a straight, after a 200 m straight approach (edge-case search only)
  if kind.startswith(("arc@", "rarc@")):
    a_y, arc = (float(x) for x in kind.split("@")[1].split(":"))
    k = (1 if kind.startswith("arc@") else -1) * a_y / (v * v)
    return Road(f"{'left' if k > 0 else 'right'} curve with exit, R = v²/{a_y:g} m/s², {arc:g} m of arc", lane_width,
                straight=0.0, length=1500.0, segments=[(200.0, 0.0, 0.0), (100.0, 0.0, k), (arc, k, k), (100.0, k, 0.0),
                                                       (2000.0, 0.0, 0.0)])
  if kind.startswith("rcurve@"):
    a_y = float(kind.split("@")[1])
    return Road(f"right curve, R = v²/{a_y:g} m/s²", lane_width, straight=60.0, radius=-v * v / a_y, length=1200.0)
  a_y = float(kind.split("@")[1]) if kind.startswith("curve@") else {"curve": 1.5, "curve-odd-bound": 2.5}[kind]
  return Road(f"left curve, R = v²/{a_y:g} m/s²", lane_width, straight=60.0, radius=v * v / a_y, length=1200.0)


class SoC:
  """Stand-in for openpilot: a lane-keeping and speed-holding controller with perfect perception. Its torque goes
  through opendbc's host limits (apply_meas_steer_torque_limits) and its frames are packed by opendbc's toyotacan."""

  def __init__(self, d, packer):
    self.d, self.packer = d, packer
    self.last_torque = 0
    self.frozen = None
    self.override_torque = None    # fault: a host build that skips the host limits (VS-FI-14)
    self.hardover = 0.0            # fault: actuators.torque forced to this value, through the host limits
    self.accel_cmd = 0.0
    self.heartbeat_ok = True
    self.stalled = False

  def steer_frame(self, engaged, v, kappa, e_y, e_psi, eps_torque, a_ff=None):
    if self.frozen is not None:
      return self.frozen
    if self.override_torque is not None:
      torque, req = self.override_torque, 1
    else:
      a_des = v * v * kappa - 1.0 * e_y - 1.6 * v * math.sin(e_psi)
      if a_ff is not None:           # lane change: feed-forward of the planned path
        a_des += a_ff
      actuator = a_des / self.d["lat_accel_factor"]
      if self.hardover:
        actuator = self.hardover
      new = int(round(max(-1.0, min(1.0, actuator)) * STEER_MAX)) if engaged else 0
      torque = apply_meas_steer_torque_limits(new, self.last_torque, eps_torque, LIMITS) if engaged else 0
      req = 1 if engaged else 0
    self.last_torque = torque
    return toyotacan.create_steer_command(self.packer, torque, req)

  def accel_frame(self, engaged):
    accel = self.accel_cmd if engaged else 0.0
    return toyotacan.create_accel_command(self.packer, accel, 0, 1, 0, 1, 1, 0, 0)


class LIMITS:   # opendbc toyota CarControllerParams with torque lateral tuning (values.py:20-21, 46-47)
  STEER_MAX = 1500
  STEER_DELTA_UP = 15
  STEER_DELTA_DOWN = 25
  STEER_ERROR_MAX = 350


def simulate(case: Case, overrides: dict[str, float] | None = None) -> Result:
  """Run one case. overrides: assumption values for this run only (keys of ASSUMPTIONS or DRIVER_OPTIONS)."""
  unknown = set(overrides or {}) - set(ASSUMPTIONS) - set(DRIVER_OPTIONS)
  if unknown:
    raise KeyError(f"not an assumption: {sorted(unknown)}")
  _OVERRIDES.clear()
  _OVERRIDES.update(overrides or {})
  try:
    return _simulate(case)
  finally:
    _OVERRIDES.clear()


def _simulate(case: Case) -> Result:
  d = corolla.as_dict()
  p = corolla.commonroad_parameters()
  v0 = case.speed_kph / 3.6
  road = make_road(case.road, v0, case.lane_width)
  panda = Panda(reference=True)
  soc = SoC(d, panda.packer)
  plant = CorollaPlant(v0, A("eps_hold_s") if case.eps == "hold" else A("eps_release_s"), A("pcm_timeout_s"), d, p)
  eps = plant.eps
  res = Result(case)

  # lead at the KS-08 time gap (read from the scenario file), follower at a 1.0 s gap (WP-S-04 §3.4)
  lead_s, follow_s = scenario_param("KS-08", "TimeGap") * v0, -1.0 * v0
  lead_v = follow_v = v0
  follow_brake_t = None
  thr = lane_line_threshold(road.lane_width, d["width"])

  t_fault = case.t_fault if case.t_fault is not None else None
  fault_on = False
  t_clear = None
  eps_seen = 0.0           # the item's lateral acceleration as the driver feels it (driver_eps_lag_s)
  stuck_pass = stuck_intercept = False
  rx_stop: set[str] = set()
  lka_state = 5
  driver_t_react = None
  driver_cue = None
  driver_brake = driver_gas = False
  d_steer = 0.0
  d_acc = 0.0
  cruise_active = False
  loop_counter = 0
  ay_meas = ax_meas = 0.0

  periods = {"WHEEL_SPEEDS": 12048, "STEER_TORQUE_SENSOR": 20000, "PCM_CRUISE": 30303, "PCM_CRUISE_2": 30303,
             "BRAKE_MODULE": 25000, "EPS_STATUS": 40000}
  phase = {"WHEEL_SPEEDS": 1000, "STEER_TORQUE_SENSOR": 2000, "PCM_CRUISE": 4000, "PCM_CRUISE_2": 6000,
           "BRAKE_MODULE": 7000, "EPS_STATUS": 9000}
  next_rx = dict(phase)
  t_end = (t_fault if t_fault is not None else road.curve_start / v0) + case.duration
  t_engage = 1.0
  n_steps = int(t_end * 1e6 / DT_US)
  torque0 = None

  def inject(f, on, v, kappa, e_y, e_psi):
    """Start (on) or clear a fault of kind f. Clearing is defined for the kinds the edge-case search uses."""
    nonlocal stuck_pass, stuck_intercept, lka_state
    if not on:
      if f in ("hardover", "hardover_left"):
        soc.hardover = 0.0
      elif f in ("frozen", "heartbeat_frozen"):
        soc.frozen = None
        soc.heartbeat_ok = True
      elif f in ("heartbeat", "soc_stall"):
        soc.stalled = False
        soc.heartbeat_ok = True
      elif f == "eps_fault":
        plant.set_eps_fault(False)
        lka_state = 5
      elif f == "rx_loss":
        rx_stop.discard("STEER_TORQUE_SENSOR")
      elif f == "overlimit":
        soc.override_torque = None
      else:
        raise ValueError(f"{f}: clearing not modelled")
      return
    if f == "overlimit":
      soc.override_torque = -3000
    elif f == "hardover":
      soc.hardover = -1.0
    elif f == "hardover_left":             # mirror of hardover (scenes of ../blender only; no catalog case uses it)
      soc.hardover = 1.0
    elif f == "not_engaged":
      soc.override_torque = -STEER_MAX
    elif f in ("frozen", "heartbeat_frozen"):
      soc.frozen = soc.steer_frame(True, v, kappa, *soc_errors(t, e_y, e_psi), eps.torque, a_ff(t))
      if f == "heartbeat_frozen":
        soc.heartbeat_ok = False
    elif f == "heartbeat":
      soc.heartbeat_ok = False
    elif f == "soc_stall":
      soc.stalled = True
      soc.heartbeat_ok = False
    elif f in ("mcu_hang", "mcu_hang_stuck_intercept", "pcs_mcu_hang", "pcs_stuck_intercept"):
      panda.hung = True
      stuck_intercept = f in ("mcu_hang_stuck_intercept", "pcs_stuck_intercept")
    elif f == "pcs_stock":
      pass
    elif f == "switch_pass":
      stuck_pass = True
    elif f == "eps_fault":
      plant.set_eps_fault(True)
      lka_state = 9
    elif f == "rx_loss":
      rx_stop.add("STEER_TORQUE_SENSOR")
    elif f == "accel_max":
      soc.accel_cmd = 2.0
    elif f == "accel_overlimit":
      soc.accel_cmd = 4.0
    elif f == "decel_min":
      soc.accel_cmd = -3.5
    elif f == "decel_overlimit":
      soc.accel_cmd = -6.0
    elif f == "none":
      pass
    else:
      raise ValueError(f)

  # assisted lane change to the left (edge-case search): the SoC follows a cosine profile from the lane centre to the
  # next lane's; its errors are taken to that planned path
  def lc_ref(t):
    if case.lane_change is None or t < case.lane_change:
      return 0.0, 0.0, 0.0
    T = case.lane_change_s
    u = min((t - case.lane_change) / T, 1.0)
    lw = road.lane_width
    if u >= 1.0:
      return lw, 0.0, 0.0
    return (lw * (1 - math.cos(math.pi * u)) / 2, lw * math.pi / (2 * T) * math.sin(math.pi * u),
            lw * math.pi ** 2 / (2 * T * T) * math.cos(math.pi * u))

  def soc_errors(t, e_y, e_psi):
    if case.lane_change is None:
      return e_y, e_psi
    y, dy, _ = lc_ref(t)
    return e_y - y, e_psi - math.atan2(dy, max(plant.speed, 1.0))

  def a_ff(t):
    return None if case.lane_change is None else lc_ref(t)[2]

  def lc_drift(t):            # planned lateral motion since the fault (lane change); 0 otherwise
    return 0.0 if case.lane_change is None else lc_ref(t)[0] - lc_ref(res.t0)[0]

  def state_on_road():
    x = plant.x
    s, lat, hr = road.project(x[0], x[1])
    return s, lat, (x[4] + x[6]) - hr

  for k in range(n_steps + 1):
    t_us = k * DT_US
    t = t_us / 1e6
    panda.set_time(t_us)
    if k % DYN_EVERY == 0:
      s, e_y, e_psi = state_on_road()
    v = plant.speed
    kappa = road.curvature(s + v * d["tau_eps"])

    # ------------------------------------------------ fault onset
    if not fault_on and ((t_fault is not None and t >= t_fault) or (t_fault is None and s >= road.curve_start)):
      fault_on = True
      res.t0, res.e0 = t, e_y
      inject(case.fault, True, v, kappa, e_y, e_psi)
      res.event("fault", t)
    # a transient fault clears (edge-case search), and a second one follows
    if fault_on and t_clear is None and (
        (case.fault_clear is not None and t >= res.t0 + case.fault_clear) or
        (case.clear_after_correction is not None and driver_t_react is not None
         and t >= driver_t_react + case.clear_after_correction)):
      t_clear = t
      inject(case.fault, False, v, kappa, e_y, e_psi)
      res.event("fault clears", t)
    if t_clear is not None and case.fault2 and "second fault" not in res.events and t >= t_clear + case.fault2_gap:
      inject(case.fault2, True, v, kappa, e_y, e_psi)
      res.event("second fault", t)

    engaged_soc = case.engaged and t >= t_engage and not soc.stalled
    intercept = (panda.relay_driven and not stuck_pass) or stuck_intercept

    # ------------------------------------------------ car bus -> panda (RX)
    if case.engaged and t >= t_engage:
      cruise_active = True
    if driver_brake or driver_gas:
      cruise_active = cruise_active and not driver_brake
    for name, per in periods.items():
      if t_us >= next_rx[name]:
        next_rx[name] += per
        if name in rx_stop:
          continue
        vals = {
          "WHEEL_SPEEDS": {f"WHEEL_SPEED_{w}": v * 3.6 for w in ("FR", "FL", "RR", "RL")},
          "STEER_TORQUE_SENSOR": {"STEER_TORQUE_EPS": eps.torque / EPS_SCALE * 100.0, "STEER_TORQUE_DRIVER": 0,
                                  "STEER_ANGLE": math.degrees(plant.x[2]) * d["steer_ratio"]},
          "PCM_CRUISE": {"CRUISE_ACTIVE": int(cruise_active), "GAS_RELEASED": int(not driver_gas)},
          "PCM_CRUISE_2": {"MAIN_ON": 1},
          "BRAKE_MODULE": {"BRAKE_PRESSED": int(driver_brake)},
          "EPS_STATUS": {"LKA_STATE": lka_state},
        }[name]
        panda.rx(name, vals)

    # ------------------------------------------------ SoC -> panda -> car bus (TX), 100 Hz
    if k % 10 == 0 and not soc.stalled:
      frame = k // 10
      # the panda's car-side transceiver is on the car bus whatever the switch position; the switch only decides
      # whether the stock camera reaches the car directly
      if case.lane_change is None:
        addr, dat, bus = soc.steer_frame(engaged_soc, v, kappa, e_y, e_psi, eps.torque)
      else:
        addr, dat, bus = soc.steer_frame(engaged_soc, v, kappa, *soc_errors(t, e_y, e_psi), eps.torque, a_ff(t))
      torque, req = _decode_steer(panda, dat)
      if panda.hung:
        if fault_on:
          res.event("MCU hung: no frame reaches the car", t)
      elif panda.relay_driven:
        if panda.tx(addr, dat, bus):
          plant.lka_frame(t, torque, req)
        elif fault_on and (req or torque):
          res.event("panda refuses STEERING_LKA", t)
      if frame % 3 == 0:
        addr, dat, bus = soc.accel_frame(engaged_soc)
        if panda.relay_driven and panda.tx(addr, dat, bus):
          plant.acc_frame(t, _decode_accel(panda, dat))
        elif fault_on and engaged_soc and panda.relay_driven and not panda.hung and case.longitudinal:
          res.event("panda refuses ACC_CONTROL", t)
      if frame % 10 == 0 and soc.heartbeat_ok:
        panda.heartbeat(engaged_soc)
    # stock camera STEERING_LKA (100 Hz, offset 5 ms): reaches the car only through a pass-through switch
    if k % 10 == 5 and not intercept:
      addr, dat, bus = toyotacan.create_steer_command(panda.packer, 0, 0)
      plant.lka_frame(t, 0, 0)
      if panda.relay_driven:
        panda.rx_raw(addr, bytes(dat), 0)   # the panda sees the camera's frame on the car side

    # stock PCS braking request (0x344, camera side): reaches the car directly through a pass-through switch, or is
    # forwarded by a running panda when its forwarding hook allows it (real code: safety_fwd_hook)
    if case.pcs and fault_on and "PCS request reaches the car" not in res.events:
      if not intercept or (not panda.hung and panda.relay_driven and panda.forward(2, 0x344) == 0):
        res.event("PCS request reaches the car", t)

    # ------------------------------------------------ panda clocks
    panda.main_loop()
    if k % 10 == 3:
      if panda.safety_task() == "reset":
        res.event("IWDG reset" + (", switch stays in intercept" if stuck_intercept else ", switch to pass-through"), t)
    elif panda.hung:
      panda.iwdg_step(0.0)
    if k % 125 == 3:
      loop_counter = (loop_counter + 1) % 8
      what_if = A("whatif_siren_on_revoke") and "authority revoked" in res.events
      if (panda.siren(loop_counter) or what_if) and fault_on:
        res.event("panda siren", t)
    if fault_on and not panda.controls_allowed and case.engaged and "authority revoked" not in res.events and not panda.hung:
      if panda.relay_driven:
        res.event("authority revoked", t)
    if fault_on and panda.relay_malfunction:
      res.event("relay malfunction detected", t)

    # ------------------------------------------------ driver
    if fault_on and driver_cue is None:
      if "panda siren" in res.events:
        driver_cue = ("siren", res.events["panda siren"])
      elif not case.longitudinal and abs(e_y - res.e0 - lc_drift(t)) > A("driver_lat_cue_m"):
        driver_cue = ("drift", t)
      elif case.longitudinal and abs(ax_meas - 0.0) > A("driver_long_cue"):
        driver_cue = ("acceleration", t)
      if driver_cue:
        driver_t_react = driver_cue[1] + A("driver_t_r_s")
        res.event(f"driver cue ({driver_cue[0]})", driver_cue[1])
    if driver_t_react is not None and t >= driver_t_react:
      res.event("driver correction", driver_t_react)
      ramp = min((t - driver_t_react) / 0.2, 1.0)
      if case.longitudinal:
        if soc.accel_cmd > 0:
          driver_brake = True
          d_acc = -A("driver_brake") * min((t - driver_t_react) / 0.3, 1.0)
        else:
          driver_gas = True
          d_acc = 0.0
      elif A("driver_brakes_only"):   # driver-model option: brakes instead of steering
        driver_brake = True
        d_acc = -A("driver_brake") * min((t - driver_t_react) / 0.3, 1.0)
      else:
        zeta = A("driver_zeta")
        kv = DRIVER_KV if zeta == 1.0 else 2 * zeta * 1.5
        target = road.lane_width if case.lane_change is not None and t >= case.lane_change else 0.0  # completes it
        a_need = v * v * road.curvature(s) - DRIVER_KE * (e_y - target) - kv * v * math.sin(e_psi)
        a_item = eps.lat_accel() if not A("driver_eps_lag_s") else eps_seen
        a_drv = max(-A("driver_ay_max"), min(A("driver_ay_max"), a_need - a_item))
        if t < driver_t_react + A("driver_wrong_s"):
          a_drv = -a_drv                # driver-model option: the first correction goes the wrong way
        d_steer = ramp * a_drv
    if A("driver_eps_lag_s"):
      eps_seen += (eps.lat_accel() - eps_seen) * min(DT_US / 1e6 / A("driver_eps_lag_s"), 1.0)

    # ------------------------------------------------ dynamics
    if k % DYN_EVERY == 0:
      dt = DYN_EVERY * DT_US / 1e6
      if case.ay_disturbance:            # builds up over 2-4 s, after the item has engaged
        plant.step(t, dt, d_steer + case.ay_disturbance * min(max((t - 2.0) / 2.0, 0.0), 1.0), d_acc)
      else:
        plant.step(t, dt, d_steer, d_acc)
      if fault_on and torque0 is None:
        torque0 = eps.torque
      if fault_on and "EPS LKA torque below 5 %" not in res.events and abs(eps.torque) < 0.05 * STEER_MAX \
         and abs(torque0) >= 0.05 * STEER_MAX and not case.longitudinal:
        res.event("EPS LKA torque below 5 %", t)
      ay_meas = v * plant.x[5]
      ax_meas = plant.ax
      # lead and follower vehicles (longitudinal cases)
      lead_s += lead_v * dt
      if case.longitudinal:
        if follow_brake_t is None and ax_meas < -1.0:
          follow_brake_t = t + A("driver_t_r_s")
        # the follower brakes at -3.5 m/s2 (equal to the envelope minimum, WP-S-04 §3.4) until it is no faster
        if follow_brake_t is not None and t >= follow_brake_t and follow_v > plant.speed:
          follow_v = max(plant.speed, follow_v - 3.5 * dt)
        follow_s += follow_v * dt
      if k % 10 == 0:
        res.t.append(t)
        res.x.append(plant.x[0])
        res.y.append(plant.x[1])
        res.e_y.append(e_y)
        res.s.append(s)
        res.ay.append(ay_meas)
        res.ax.append(ax_meas)
        res.torque.append(eps.torque)
        ego_s = s
        res.gap.append((lead_s - ego_s - 4.6, ego_s - follow_s - 4.6))

  res.metrics = metrics(res, thr, lane_line_threshold(3.0, d["width"]))
  return res


def _decode_steer(panda, dat):
  m = panda.packer.dbc.name_to_msg["STEERING_LKA"]
  return _sig(dat, m.sigs["STEER_TORQUE_CMD"]), _sig(dat, m.sigs["STEER_REQUEST"])


def _decode_accel(panda, dat):
  m = panda.packer.dbc.name_to_msg["ACC_CONTROL"]
  return _sig(dat, m.sigs["ACCEL_CMD"])


def _sig(dat, sig):
  raw = sig.get_raw_value(dat)
  if sig.is_signed:
    raw -= ((raw >> (sig.size - 1)) & 0x1) * (1 << sig.size)
  return raw * sig.factor + sig.offset


def metrics(res: Result, thr: float, thr_narrow: float) -> dict:
  t0 = res.t0
  after = [(t, e) for t, e in zip(res.t, res.e_y) if t >= t0]
  dev = [(t, e - res.e0) for t, e in after]
  m = {"lane_threshold": thr, "narrow_threshold": thr_narrow}
  if dev:
    tmax, dmax = max(dev, key=lambda te: abs(te[1]))
    m["max_dev"] = dmax
    m["t_max_dev"] = tmax - t0
    m["max_offset"] = max((abs(e) for _, e in after), default=0.0)
    m["t_line"] = next((t - t0 for t, e in after if abs(e) >= thr), None)
    m["t_narrow"] = next((t - t0 for t, e in after if abs(e) >= thr_narrow), None)
    m["dev_at_ftti"] = next((e for t, e in dev if t - t0 >= 0.5), None)
  if res.case.longitudinal:
    i0 = next(i for i, t in enumerate(res.t) if t >= t0)
    lead = [g[0] for g in res.gap[i0:]]
    follow = [g[1] for g in res.gap[i0:]]
    m["gap0_lead"], m["min_gap_lead"] = lead[0], min(lead)
    i1 = next((i for i, t in enumerate(res.t[i0:]) if t - t0 >= 1.0), None)
    m["gap_loss_1s"] = lead[0] - lead[i1] if i1 is not None else None
    m["gap0_follow"], m["min_gap_follow"] = follow[0], min(follow)
  m["events"] = {k: v - t0 for k, v in sorted(res.events.items(), key=lambda kv: kv[1])}
  return m
