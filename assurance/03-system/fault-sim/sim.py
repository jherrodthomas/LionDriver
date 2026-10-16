"""Closed-loop fault-injection scenarios: plant (vehicle.py) + envelope in the loop (envelope.py)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import envelope as env
import vehicle as veh
from vehicle import ASSUME

DT_US = 2000                   # plant step 2 ms
FRAME_US = 10000               # control frame and safety task, 100 Hz
HEARTBEAT_US = 100000          # pandad heartbeat every 10th frame (WP-S-04 T-10)
SPEAKER_US = 125000            # panda 8 Hz tick; the speaker sounds on every other tick
RX_PERIODS_US = {0xAA: 12000, 0x260: 20000, 0x1D2: 30000, 0x1D3: 30000, 0x226: 25000, 0x262: 40000}
ENGAGE_US = 500000             # PCM cruise rising edge at 0.5 s
CURVE_START_US = 1000000       # clothoid entry begins once engaged
CURVE_ENTRY_US = 2000000       # length of the clothoid entry (time at speed)
FAULT_US = 4500000             # fault onset at 4.5 s, in the constant-radius part
KP, KD = 1.2, 1.6               # lane-centring gains of the simplified host controller (tuned for stability)
LANE_EDGE = (ASSUME["lane_width"] - ASSUME["vehicle_width"]) / 2


@dataclass
class Fault:
  kind: str = "none"
  param: dict = field(default_factory=dict)


@dataclass
class Result:
  name: str
  t_detect: float | None = None    # envelope revokes authority or refuses the first frame (s after onset)
  t_siren: float | None = None     # panda siren audible
  t_alert: float | None = None     # host alert
  t_cue: float | None = None       # driver cue
  t_06: float | None = None        # |e_y| reaches 0.6 m
  t_edge: float | None = None      # |e_y| reaches the lane edge margin
  max_ey: float = 0.0
  ey_trace: list = field(default_factory=list)
  notes: list = field(default_factory=list)


def _host_torque(val: float, last: int, meas: float) -> int:
  """Host limits: a port of opendbc car/lateral.py apply_dist_to_meas_limits with the Toyota values
  (STEER_MAX 1500, DELTA_UP 15, DELTA_DOWN 25, ERROR_MAX 350), which equal the envelope's (zero margin, GAP-04)."""
  up, down, err, smax = 15, 25, 350, veh.TORQUE_MAX
  max_lim = min(max(meas + err, err), smax)
  min_lim = max(min(meas - err, -err), -smax)
  val = min(max(val, min_lim), max_lim)
  if last > 0:
    val = min(max(val, max(last - down, -up)), last + up)
  else:
    val = min(max(val, last - up), min(last + down, up))
  return int(round(val))


def run_lateral(name: str, fault: Fault, v: float = 30.0, a_curve: float = 0.0, curve_ends_at_fault: bool = False,
                driver: bool = True, rt: float | None = None, t_end: float = 11.0, eps_persist_ticks: int | None = None,
                lsi_hz: float = env.LSI_HZ_NOMINAL) -> Result:
  """One lateral run at constant speed v: engage at ENGAGE_US, inject `fault` at FAULT_US, run to t_end."""
  kappa = a_curve / v ** 2
  s0, s1 = v * CURVE_START_US / 1e6, v * (CURVE_START_US + CURVE_ENTRY_US) / 1e6
  pts = [(0.0, 0.0), (s0, 0.0), (s1, kappa)]
  if curve_ends_at_fault:   # the road straightens at the fault (abrupt: worst case for a frozen command)
    sf = v * FAULT_US / 1e6
    pts += [(sf - 0.01, kappa), (sf, 0.0)]
  road = veh.Road(pts)
  lat = veh.Lateral(v=v)
  eps = veh.EPS(DT_US / 1e6)
  drv = veh.Driver(rt=rt, present=driver)
  p = env.Panda(eps_persist_ticks=eps_persist_ticks)
  res = Result(name)
  k = fault.kind
  host_alive, host_last = True, 0
  frozen_cmd = None
  hang_until = None
  release_us = None        # relay / switch back to the stock camera path
  allowed_prev = False
  refused_seen = False
  t_us = 0

  def alert(at: float) -> None:
    if host_alive and (res.t_alert is None or at < res.t_alert):
      res.t_alert = at

  while t_us <= int(t_end * 1e6):
    t = t_us / 1e6
    after = t_us >= FAULT_US
    tf = (t_us - FAULT_US) / 1e6
    p.set_time(t_us)
    # ---- fault onsets
    if after and k == "mcu_hang" and hang_until is None:
      p.hung = True    # hang just after an IWDG feed: the full timeout elapses (worst case)
      hang_until = t_us + int(round(env.iwdg_timeout_s(lsi_hz) * 1e6))
    if hang_until is not None and p.hung and t_us >= hang_until:
      p.hung, p.silent = False, True          # IWDG reset -> boot in SS-S, relay released
      res.t_detect = tf
      release_us = t_us
      alert(tf + ASSUME["host_reset_alert"])  # host notices the panda reset (DQ-054 context)
      res.notes.append(f"watchdog reset {tf * 1000:.0f} ms after the hang")
    if after and k == "soc_crash":
      host_alive = False
    if after and k == "eps_fault":
      eps.fault = True
    if p.hb_silent and release_us is None:
      release_us = t_us
      res.notes.append(f"SILENT after heartbeat loss at {tf:.2f} s")
    host_engaged = host_alive and t_us >= ENGAGE_US and not (res.t_alert is not None and after and tf >= res.t_alert)
    # ---- vehicle CAN RX into the envelope
    applied = eps.applied
    for addr, per in RX_PERIODS_US.items():
      if t_us % per or (after and k == "rx_loss" and addr == fault.param.get("addr", 0x260)):
        continue
      if addr == 0xAA:
        p.rx(addr, env.wheel_speeds(v))
      elif addr == 0x260:
        p.rx(addr, env.steer_torque_sensor(applied, 0.0))
      elif addr == 0x1D2:
        p.rx(addr, env.pcm_cruise(t_us >= ENGAGE_US))
      elif addr == 0x1D3:
        p.rx(addr, env.pcm_cruise_2(True))
      elif addr == 0x226:
        p.rx(addr, env.brake_module(False))
      elif addr == 0x262:
        p.rx(addr, env.eps_status(env.LKA_STATE_FAULT if eps.fault else env.LKA_STATE_ACTIVE))
    stock_on_car = (after and k == "harness_pass_through") or \
        (release_us is not None and t_us >= release_us + int(ASSUME["relay_release"] * 1e6))
    if stock_on_car and t_us % FRAME_US == 0:
      p.rx(0x2E4, env.steering_lka(0, False), bus=0)     # stock camera LKA frame on the car side (no request)
      eps.frame(0, False)
    # ---- 100 Hz: host control frame, then the panda safety task
    if t_us % FRAME_US == 0:
      if host_alive and t_us % HEARTBEAT_US == 0 and not (after and k == "heartbeat_loss"):
        p.heartbeat(host_engaged)
      if host_alive:
        e_dot = v * math.sin(lat.e_psi) + lat.vy
        a_des = v ** 2 * road.curvature(lat.s + v * 0.25) - KP * lat.e_y - KD * e_dot
        cmd = _host_torque(a_des / veh.LAF * veh.TORQUE_MAX, host_last, applied) if host_engaged else 0
        req = host_engaged
        if k == "eps_fault" and after and tf >= 0.04:   # host reads LKA_STATE (25 Hz) and sets latActive false
          cmd, req = 0, False
        elif after and host_engaged:
          if k == "over_limit_torque":
            cmd = fault.param.get("torque", 3000)
          elif k == "torque_rate":
            cmd = host_last + fault.param.get("rate", 100)
          elif k == "in_envelope_ramp":
            cmd = max(-veh.TORQUE_MAX, host_last - 15)
          elif k == "frozen":
            frozen_cmd = host_last if frozen_cmd is None else frozen_cmd
            cmd = frozen_cmd
        if k == "torque_not_engaged" and t_us < ENGAGE_US:
          cmd, req = 1500, True
        if t_us % 30000 == 0:
          p.tx(0x343, env.acc_control(0.0))          # ACC_CONTROL at 33 Hz (TSR-408 supervises it too)
        ok = p.tx(0x2E4, env.steering_lka(cmd, req))
        if ok:
          eps.frame(cmd, req)
          host_last = cmd
        elif (cmd != 0 or req) and not p.down:
          if k == "torque_not_engaged" and t_us < ENGAGE_US:
            res.notes.append("torque frames refused while not engaged") if not refused_seen else None
          elif after and not refused_seen:
            res.t_detect = tf if res.t_detect is None else res.t_detect
            alert(tf + ASSUME["host_alert_latency"])  # rising safetyTxBlocked or relayMalfunction (TSR-615)
          refused_seen = True
      p.safety_task(t_us)
      allowed = p.controls_allowed
      if after and allowed_prev and not allowed:
        res.t_detect = tf if res.t_detect is None else res.t_detect
        if not p.down:
          alert(tf + ASSUME["host_alert_latency"])    # controlsMismatch (TSR-621)
      allowed_prev = allowed
    if k == "eps_fault" and after and tf >= 1.5:
      alert(1.5)                                      # host steerFault after its 1.5 s hysteresis (T-25)
    # ---- speaker: 8 Hz tick, sounds on every other tick
    if t_us % SPEAKER_US == 0 and p.speaker_tick() and after and res.t_siren is None:
      res.t_siren = tf
    # ---- driver
    if after:
      if res.t_siren is not None:
        drv.cue(FAULT_US / 1e6 + res.t_siren, "siren")
      if res.t_alert is not None and tf >= res.t_alert:
        drv.cue(FAULT_US / 1e6 + res.t_alert, "alert")
      if abs(lat.e_y) >= ASSUME["driver_drift_cue"]:
        drv.cue(t, "drift")
      if abs(lat.a_y() - v ** 2 * road.curvature(lat.s)) >= ASSUME["driver_accel_cue"]:
        drv.cue(t, "lateral acceleration")
    # ---- plant
    a_assist = veh.LAF * eps.step() / veh.TORQUE_MAX
    kap = road.curvature(lat.s)
    a_drv = drv.correction(t, lat, kap, a_assist)
    lat.step(DT_US / 1e6, a_assist + a_drv, kap)
    if after:
      ae = abs(lat.e_y)
      res.max_ey = max(res.max_ey, ae)
      if res.t_06 is None and ae >= ASSUME["lane_margin_design"]:
        res.t_06 = tf
      if res.t_edge is None and ae >= LANE_EDGE:
        res.t_edge = tf
      if t_us % 50000 == 0:
        res.ey_trace.append((round(tf, 3), round(lat.e_y, 4)))
    t_us += DT_US
  if drv.cue_t is not None:
    res.t_cue = drv.cue_t - FAULT_US / 1e6
    res.notes.append(f"driver cue: {drv.cue_kind}")
  return res


@dataclass
class LongResult:
  name: str
  t_detect: float | None = None
  t_alert: float | None = None
  min_gap: float = 1e9           # m, to the lead (or from the follower)
  impact_speed: float = 0.0      # m/s, relative speed at contact (0 = no contact)
  gap_loss_1s: float | None = None
  pcs_delay: float | None = None
  dv_lost: float | None = None   # m/s, PCS speed reduction lost by the delay
  trace: list = field(default_factory=list)
  notes: list = field(default_factory=list)


def run_longitudinal(name: str, fault: Fault, v: float = 25.0, h: float = 1.5, rt: float | None = None,
                     t_end: float = 12.0, lsi_hz: float = env.LSI_HZ_NOMINAL) -> LongResult:
  """Ego follows a lead on a straight road (lateral control nominal, not simulated). Faults on the ACC path, the
  following vehicle (SG-04), the stock PCS forwarding (SG-07) and the braking-warning path (SG-06)."""
  dt = DT_US / 1e6
  rt = ASSUME["driver_rt"] if rt is None else rt
  p = env.Panda()
  res = LongResult(name)
  k = fault.kind
  ego_v, ego_a, ego_x = v, 0.0, 0.0
  lead_v, lead_x = v, v * h
  fol_v, fol_x, fol_a = v, -v * h, 0.0   # follower, same time gap behind
  pcm_target, last_ok_us, last_ok_accel = 0.0, 0, 0.0
  host_last = 0.0
  pcs_request_us = None
  pcs_brake_us = None
  drv_brake_us = None
  fcw_us = None
  hang_until = None
  release_us = None
  gap0 = None
  ego_brake_onset_us = None
  t_us = 0
  while t_us <= int(t_end * 1e6):
    after = t_us >= FAULT_US
    tf = (t_us - FAULT_US) / 1e6
    p.set_time(t_us)
    # ---- scenario events
    if k in ("pcs_mcu_hang", "pcs_stuck_intercept", "pcs_stock", "fcw_hard_brake") and after:
      lead_a = -fault.param.get("lead_decel", 6.0) if lead_v > 0 else 0.0
    else:
      lead_a = 0.0
    if k in ("pcs_mcu_hang", "pcs_stuck_intercept", "pcs_stock") and after and pcs_request_us is None:
      pcs_request_us = t_us                 # stock camera sends its PCS braking request (0x344) now
      fwd = p.c.safety_fwd_hook(2, 0x344)
      res.notes.append(f"0x344 from the camera bus is forwarded to bus {fwd} by the running envelope (safety_fwd_hook)")
      if k == "pcs_stock":
        pcs_brake_us = t_us                 # forwarded at once (forwarding latency, TSR-707, neglected)
      else:
        p.hung = True                       # the MCU hangs at the same instant, just after an IWDG feed (worst case)
        hang_until = t_us + int(round(env.iwdg_timeout_s(lsi_hz) * 1e6))
    if hang_until is not None and p.hung and t_us >= hang_until:
      p.hung, p.silent = False, True
      res.t_detect = tf
      release_us = t_us
    if pcs_request_us is not None and pcs_brake_us is None:
      if k == "pcs_mcu_hang" and release_us is not None and t_us >= release_us + int(ASSUME["relay_release"] * 1e6):
        pcs_brake_us = t_us                 # stock path restored: the PCS request reaches the car
    # ---- RX
    for addr, per in RX_PERIODS_US.items():
      if t_us % per:
        continue
      if addr == 0xAA:
        p.rx(addr, env.wheel_speeds(ego_v))
      elif addr == 0x260:
        p.rx(addr, env.steer_torque_sensor(0.0, 0.0))
      elif addr == 0x1D2:
        p.rx(addr, env.pcm_cruise(t_us >= ENGAGE_US and drv_brake_us is None))
      elif addr == 0x1D3:
        p.rx(addr, env.pcm_cruise_2(True))
      elif addr == 0x226:
        p.rx(addr, env.brake_module(drv_brake_us is not None))
      elif addr == 0x262:
        p.rx(addr, env.eps_status(env.LKA_STATE_ACTIVE))
    # ---- host ACC at 33 Hz, steering frames at 100 Hz (zero torque, request set)
    if t_us % FRAME_US == 0:
      if t_us % HEARTBEAT_US == 0:
        p.heartbeat(t_us >= ENGAGE_US)
      engaged = t_us >= ENGAGE_US
      p.tx(0x2E4, env.steering_lka(0, engaged))
      if t_us % 30000 == 0:
        gap = lead_x - ego_x
        a_des = 0.25 * (gap - h * ego_v) + 0.6 * (lead_v - ego_v) + lead_a   # host keeps the set time gap h
        a_des = max(-3.5, min(2.0, a_des)) if engaged else 0.0
        if after and k == "unintended_accel":
          a_des = fault.param.get("accel", 2.0)
        if after and k == "excess_decel":
          a_des = -3.5
        if after and k == "over_limit_accel":
          a_des = fault.param.get("accel", 3.0)
        if p.tx(0x343, env.acc_control(a_des)):
          last_ok_us, last_ok_accel = t_us, a_des
        elif after and res.t_detect is None and not p.down:
          res.t_detect = tf
          res.t_alert = tf + ASSUME["host_alert_latency"]
        host_last = a_des
      p.safety_task(t_us)
    # ---- PCM: follows the last accepted request; holds it for pcm_hold, then coasts
    if (t_us - last_ok_us) / 1e6 > ASSUME["pcm_hold"] or (res.t_alert is not None and tf >= res.t_alert):
      pcm_target = ASSUME["coast"]
    else:
      pcm_target = last_ok_accel
    # ---- FCW and driver braking (SG-06 warning path, §3.8.2)
    gap = lead_x - ego_x
    closing = ego_v - lead_v
    if k == "fcw_hard_brake" and after and fcw_us is None and tf >= fault.param.get("fcw_delay", 0.6):
      fcw_us = t_us                         # FCW onset after the lead brakes: swept, not derived (WP-S-04 T-31)
    if k in ("unintended_accel", "over_limit_accel") and after and fcw_us is None and ego_a >= ASSUME["driver_accel_cue"]:
      fcw_us = t_us                         # here: the driver feels the unexpected acceleration (no warning)
    if fcw_us is not None and drv_brake_us is None and t_us >= fcw_us + int(rt * 1e6):
      drv_brake_us = t_us
    target = pcm_target
    if pcs_brake_us is not None:
      target = min(target, -ASSUME["a_pcs"])
    if drv_brake_us is not None:
      target = -6.0
    ego_a += (target - ego_a) * dt / ASSUME["pcm_tau"]
    if ego_a < -0.5 and ego_brake_onset_us is None and after:
      ego_brake_onset_us = t_us
    # ---- follower (SG-04): brakes as hard as the ego after rt from the ego's brake onset
    if k == "excess_decel" and ego_brake_onset_us is not None and t_us >= ego_brake_onset_us + int(rt * 1e6):
      fol_a += (ego_a - fol_a) * dt / ASSUME["pcm_tau"]
    # ---- integrate
    ego_v = max(0.0, ego_v + ego_a * dt)
    lead_v = max(0.0, lead_v + lead_a * dt)
    fol_v = max(0.0, fol_v + fol_a * dt)
    ego_x += ego_v * dt
    lead_x += lead_v * dt
    fol_x += fol_v * dt
    if after:
      if gap0 is None:
        gap0 = lead_x - ego_x
      if k == "excess_decel":
        g = ego_x - fol_x
        if g <= 0 and res.impact_speed == 0.0:
          res.impact_speed = fol_v - ego_v
        res.min_gap = min(res.min_gap, g)
      else:
        g = lead_x - ego_x
        if g <= 0 and res.impact_speed == 0.0:
          res.impact_speed = ego_v - lead_v
        res.min_gap = min(res.min_gap, g)
      if res.gap_loss_1s is None and tf >= 1.0:
        res.gap_loss_1s = gap0 - (lead_x - ego_x) if k in ("unintended_accel", "over_limit_accel") else None
      if t_us % 100000 == 0:
        res.trace.append((round(tf, 2), round(ego_v, 3), round(lead_x - ego_x, 3)))
    if res.impact_speed > 0:
      break
    t_us += DT_US
  if pcs_request_us is not None:
    if pcs_brake_us is not None:
      res.pcs_delay = (pcs_brake_us - pcs_request_us) / 1e6
      res.dv_lost = ASSUME["a_pcs"] * res.pcs_delay
    else:
      res.notes.append("PCS request never reached the car (stock path not restored)")
  if fcw_us is not None:
    cue = "FCW" if k == "fcw_hard_brake" else "driver cue (acceleration)"
    res.notes.append(f"{cue} at {(fcw_us - FAULT_US) / 1e6:.2f} s, driver brakes at {(drv_brake_us - FAULT_US) / 1e6:.2f} s"
                     if drv_brake_us else f"{cue} at {(fcw_us - FAULT_US) / 1e6:.2f} s")
  return res
