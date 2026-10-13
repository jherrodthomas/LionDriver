#!/usr/bin/env python3
"""Field-monitoring event extraction for LionDriver (WP-O-04 §4.1 step 2, OI-4).

Scans openpilot logs (rlog or qlog) for the monitored events MON-01…MON-17 of WP-O-04 §2.1
and scores the SOTIF anomaly signatures AS-01…AS-11 of WP-V-04 §2.1. One script and one
signature-set version serve both development drives and field logs (WP-V-04 §2.1.1), and
every report records that version.

Output, per run:
  - an event table: route, time from route start, MON ID, AS IDs, triage class (WP-O-04
    §4.2), engaged flag and the context signals that triggered it;
  - exposure (WP-O-04 §2.2): total and engaged time and distance, engaged distance per speed
    band, the denominators for every KPI;
  - per MON and AS counts, and rates per engaged hour;
  - what could not be scored, and why.

Edge counting: openpilot republishes an active event in every `onroadEvents` message, so an
event counts once on its rising edge, not once per message.

Not scored here (reported as such):
  - AS-04 "torque/accel at the limit" needs the safety replay; only the TX-block part is here.
  - AS-08 curvature divergence: WP-V-04 gives no threshold. Only the lead-flicker part (more
    than one toggle per second, AIR-11/VT-14) is scored.
  - AS-09 needs the 99.9th percentile of the evaluation set (`--uncertainty-limits`).
  - MON-14 automatic crash detection: the deceleration threshold is open (WP-O-04 OI-8); the
    placeholder `--crash-decel` flags candidates for review, bookmarks always count.
  - MON-16 needs a release record (`--release`) to compare against.
  - qlogs carry no `modelV2`: AS-05, AS-08 and MON-13 need rlogs.

Usage:
  PYTHONPATH=.:opendbc_repo tools/field_monitoring/extract_events.py rlog.zst [...] \\
      [--release release.json] [--json out.json] [--csv events.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass, field

SIGNATURE_SET_VERSION = "WP-V-04-2.1/2026-10-12"  # bump with any change to AS-01…AS-11 below

# Thresholds of WP-V-04 §2.1 (the only definition; change them there first).
AS02_DECEL = -4.0          # m/s^2, within AS02_WINDOW_S of a brake disengagement
AS02_WINDOW_S = 2.0
AS03_PLAN_DECEL = -1.5     # m/s^2, planner target while the driver presses gas
AS05_CLEARANCE_M = 0.3     # m, vehicle side to lane line
AS05_MIN_LINE_PROB = 0.5   # line must be seen for the clearance to count (assumed)
AS06_DECEL = -2.0          # m/s^2, with no lead inside AS06_TTC_S
AS06_TTC_S = 4.0
AS08_LEAD_TOGGLES_PER_S = 1.0  # AIR-11 / VT-14
AS08_LEAD_PROB = 0.5
VEHICLE_HALF_WIDTH_M = 1.781 / 2  # reference Corolla (WP-V-02 §3.5 reference-vehicle check)

# WP-O-04 placeholders (OI-5, OI-8): flag for review, not evidence.
ODD_MAX_SPEED_MS = 120 / 3.6       # WP-C-02 §3.1, ODD-H bound
CRASH_DECEL_PLACEHOLDER = -6.0     # m/s^2, OI-8
SPEED_BANDS_KMH = (0, 30, 60, 90, 120, 1000)

# onroadEvents names per MON class (cereal EventName).
MON_EVENTS = {
  "MON-03": {"controlsMismatch"},
  "MON-04": {"relayMalfunction"},
  "MON-05": {"excessiveActuation"},
  "MON-07": {"driverDistracted1", "driverDistracted2", "driverDistracted3", "driverUnresponsive1",
             "driverUnresponsive2", "driverUnresponsive3", "tooDistracted"},
  "MON-08": {"fcw", "stockAeb", "stockFcw"},
  "MON-09": {"steerSaturated", "steerTempUnavailable", "steerTempUnavailableSilent"},
  "MON-10": {"commIssue", "commIssueAvgFreq", "processNotRunning", "modeldLagging", "selfdrivedLagging"},
  "MON-11": {"calibrationInvalid", "calibrationRecalibrating"},
  "MON-12": {"cruiseMismatch", "canError", "canBusMissing"},
  "MON-15": {"speedTooHigh"},
}
EVENT_TO_MON = {name: mon for mon, names in MON_EVENTS.items() for name in names}

# AS signatures carried by onroadEvents (WP-V-04 §2.1).
EVENT_TO_AS = {"fcw": "AS-07", "steerSaturated": "AS-11", "commIssue": "AS-11", "modeldLagging": "AS-11",
               "excessiveActuation": "AS-11", "driverDistracted2": "AS-10", "driverDistracted3": "AS-10",
               "driverUnresponsive2": "AS-10", "driverUnresponsive3": "AS-10", "tooDistracted": "AS-10"}

# WP-O-04 §4.2 triage. T2 for a T3-class event only when engaged where the table says so.
T1 = {"MON-03", "MON-04", "MON-05", "MON-14", "MON-16"}
T2_ALWAYS = {"MON-02"}
T2_IF_ENGAGED = {"MON-06"}
T2_EVENTS = {"stockAeb", "driverUnresponsive3", "tooDistracted", "nonFiniteModelOutput"}


def triage(mon: str, engaged: bool, trigger: str) -> str:
  if mon in T1:
    return "T1"
  if mon in T2_ALWAYS or (mon in T2_IF_ENGAGED and engaged) or (trigger in T2_EVENTS and (engaged or mon != "MON-08")):
    return "T2"
  return "T3"


@dataclass
class Event:
  route: str
  t_s: float
  mon: str
  signatures: list[str]
  trigger: str
  engaged: bool
  detail: dict = field(default_factory=dict)

  @property
  def triage(self) -> str:
    return triage(self.mon, self.engaged, self.trigger)

  def row(self) -> dict:
    return {"route": self.route, "t_s": round(self.t_s, 3), "mon": self.mon, "signatures": ";".join(self.signatures),
            "trigger": self.trigger, "triage": self.triage, "engaged": self.engaged,
            "detail": json.dumps(self.detail, sort_keys=True)}


@dataclass
class Exposure:
  total_s: float = 0.0
  engaged_s: float = 0.0
  total_m: float = 0.0
  engaged_m: float = 0.0
  engaged_m_by_band: dict = field(default_factory=lambda: {f"{lo}-{hi}": 0.0 for lo, hi in zip(SPEED_BANDS_KMH, SPEED_BANDS_KMH[1:], strict=False)})

  def add(self, dt: float, v: float, engaged: bool) -> None:
    self.total_s += dt
    self.total_m += v * dt
    if engaged:
      self.engaged_s += dt
      self.engaged_m += v * dt
      kmh = v * 3.6
      for lo, hi in zip(SPEED_BANDS_KMH, SPEED_BANDS_KMH[1:], strict=False):
        if lo <= kmh < hi:
          self.engaged_m_by_band[f"{lo}-{hi}"] += v * dt
          break

  def merge(self, other: Exposure) -> None:
    self.total_s += other.total_s
    self.engaged_s += other.engaged_s
    self.total_m += other.total_m
    self.engaged_m += other.engaged_m
    for k, v in other.engaged_m_by_band.items():
      self.engaged_m_by_band[k] += v


def get(obj, path: str, default=None):
  """Dotted attribute or key access on capnp readers, dicts and namespaces."""
  for part in path.split("."):
    if obj is None:
      return default
    obj = obj.get(part) if isinstance(obj, dict) else getattr(obj, part, None)
  return default if obj is None else obj


def finite_all(values) -> bool:
  return all(math.isfinite(float(x)) for x in values)


class RouteScanner:
  """Stateful scan of one route's messages in time order: (t_s, service, msg)."""

  def __init__(self, route: str, release: dict | None = None, crash_decel: float = CRASH_DECEL_PLACEHOLDER,
               uncertainty_limits: dict | None = None):
    self.route = route
    self.release = release
    self.crash_decel = crash_decel
    self.uncertainty_limits = uncertainty_limits or {}
    self.events: list[Event] = []
    self.exposure = Exposure()
    self.not_scored: set[str] = set()
    self.services: set[str] = set()
    self.enabled = False
    self.active_events: set[str] = set()
    self.last_car = None
    self.last_car_t: float | None = None
    self.last_lead = None
    self.last_plan_a: float | None = None
    self.brake_disengage_t: float | None = None
    self.panda_counters: dict[int, tuple[int, int]] = {}
    self.panda_flags: dict[tuple[int, str], bool] = {}
    self.lead_seen: bool | None = None
    self.lead_toggles: list[float] = []
    self.flicker_flagged_until = -1.0
    self.flags: dict[str, bool] = {}
    self.config: dict = {}

  def emit(self, t: float, mon: str, trigger: str, sigs=(), **detail) -> None:
    self.events.append(Event(self.route, t, mon, list(sigs), trigger, self.enabled, detail))

  def edge(self, key: str, value: bool) -> bool:
    """True on a rising edge of a named condition."""
    rising = value and not self.flags.get(key, False)
    self.flags[key] = value
    return rising

  # --- per-service handlers -------------------------------------------------------------
  def on_selfdriveState(self, t, m):
    enabled = bool(get(m, "enabled", False))
    if self.enabled and not enabled:
      self.on_disengage(t)
    self.enabled = enabled

  def on_disengage(self, t):
    fault = [e for e in self.active_events if self.flags.get(f"fault:{e}")]
    car = self.last_car
    pressed = {k: bool(get(car, k, False)) for k in ("brakePressed", "gasPressed", "steeringPressed")} if car else {}
    if fault:
      self.emit(t, "MON-02", "faultDisengage", ["AS-11"], events=sorted(fault))
    else:
      if pressed.get("brakePressed"):
        self.brake_disengage_t = t
      self.emit(t, "MON-01", "driverDisengage", [], context_from_s=round(max(0.0, t - 10.0), 3), **pressed)

  def on_carState(self, t, m):
    v = float(get(m, "vEgo", 0.0))
    if self.last_car_t is not None:
      self.exposure.add(max(0.0, t - self.last_car_t), v, self.enabled)
    self.last_car, self.last_car_t = m, t
    a = float(get(m, "aEgo", 0.0))
    # AS-02: brake disengagement followed by hard deceleration
    if self.brake_disengage_t is not None:
      if t - self.brake_disengage_t > AS02_WINDOW_S:
        self.brake_disengage_t = None
      elif a < AS02_DECEL:
        self.emit(t, "MON-01", "brakeDisengageHardDecel", ["AS-02"], aEgo=round(a, 2))
        self.brake_disengage_t = None
    # AS-01: steering override while engaged, not during a lane change (blinker as the proxy)
    lane_change = bool(get(m, "leftBlinker", False)) or bool(get(m, "rightBlinker", False))
    if self.edge("as01", self.enabled and bool(get(m, "steeringPressed", False)) and not lane_change):
      self.emit(t, "MON-01", "steeringOverride", ["AS-01"])
    # AS-03: gas while the planner decelerates
    plan_decel = self.last_plan_a is not None and self.last_plan_a < AS03_PLAN_DECEL
    if self.edge("as03", self.enabled and bool(get(m, "gasPressed", False)) and plan_decel):
      self.emit(t, "MON-17", "gasOverrideDuringDecel", ["AS-03"], aTarget=round(self.last_plan_a, 2))
    # AS-06: phantom deceleration
    if self.edge("as06", self.enabled and a < AS06_DECEL and not self.lead_within_ttc()):
      self.emit(t, "MON-17", "phantomDecel", ["AS-06"], aEgo=round(a, 2))
    # MON-14: crash candidate (placeholder threshold, OI-8)
    if self.edge("mon14", a < self.crash_decel):
      self.emit(t, "MON-14", "highDecelCandidate", [], aEgo=round(a, 2), threshold="placeholder OI-8")
    # MON-15: engaged above the ODD speed bound
    if self.edge("mon15", self.enabled and v > ODD_MAX_SPEED_MS):
      self.emit(t, "MON-15", "aboveOddSpeed", [], vEgo_kmh=round(v * 3.6, 1))

  def lead_within_ttc(self) -> bool:
    lead = self.last_lead
    if lead is None or not bool(get(lead, "status", False)):
      return False
    v_rel = float(get(lead, "vRel", 0.0))
    if v_rel >= 0:
      return False
    return float(get(lead, "dRel", 1e9)) / -v_rel <= AS06_TTC_S

  def on_radarState(self, t, m):
    self.last_lead = get(m, "leadOne")

  def on_longitudinalPlan(self, t, m):
    self.last_plan_a = float(get(m, "aTarget", 0.0))

  def on_onroadEvents(self, t, events):
    names = set()
    for e in events or []:
      name = str(get(e, "name", ""))
      names.add(name)
      self.flags[f"fault:{name}"] = bool(get(e, "softDisable", False)) or bool(get(e, "immediateDisable", False))
    for name in sorted(names - self.active_events):
      mon = EVENT_TO_MON.get(name)
      if mon:
        sig = EVENT_TO_AS.get(name)
        self.emit(t, mon, name, [sig] if sig else [])
    self.active_events = names

  def on_pandaStates(self, t, pandas):
    for i, p in enumerate(pandas or []):
      blocked, rx_invalid = int(get(p, "safetyTxBlocked", 0)), int(get(p, "safetyRxInvalid", 0))
      prev = self.panda_counters.get(i)
      if prev is not None:
        if blocked > prev[0]:
          self.emit(t, "MON-06", "safetyTxBlocked", ["AS-04"], panda=i, blocked=blocked - prev[0])
        if rx_invalid > prev[1]:
          self.emit(t, "MON-06", "safetyRxInvalid", [], panda=i, invalid=rx_invalid - prev[1])
      self.panda_counters[i] = (blocked, rx_invalid)
      for flag in ("heartbeatLost", "txRateExceeded", "epsFault"):
        if self.edge(f"panda{i}:{flag}", bool(get(p, flag, False))):
          self.emit(t, "MON-06" if flag != "epsFault" else "MON-02", flag, [], panda=i)
      if self.edge(f"panda{i}:relay", "relayMalfunction" in [str(f) for f in (get(p, "faults", []) or [])]):
        self.emit(t, "MON-04", "relayMalfunctionFault", [], panda=i)

  def on_liveCalibration(self, t, m):
    status = str(get(m, "calStatus", ""))
    prev = self.flags.get("calStatus")
    if prev is not None and status != prev and status in ("invalid", "recalibrating"):
      self.emit(t, "MON-11", f"calibration:{status}", [])
    self.flags["calStatus"] = status

  def on_modelV2(self, t, m):
    # MON-13: non-finite outputs
    pos = get(m, "position.x", []) or []
    if self.edge("nonfinite", not finite_all(pos)):
      self.emit(t, "MON-13", "nonFiniteModelOutput", ["AS-08"])
    # AS-05: lane-line proximity (lines 1 and 2 are the ego lane's left and right lines)
    lines, probs = get(m, "laneLines", []) or [], get(m, "laneLineProbs", []) or []
    near = False
    if self.enabled and len(lines) >= 3 and len(probs) >= 3:
      for idx in (1, 2):
        ys = get(lines[idx], "y", []) or []
        if ys and probs[idx] >= AS05_MIN_LINE_PROB and abs(float(ys[0])) - VEHICLE_HALF_WIDTH_M < AS05_CLEARANCE_M:
          near = True
    if self.edge("as05", near):
      self.emit(t, "MON-17", "laneLineProximity", ["AS-05"])
    # AS-08: lead flicker, more than AS08_LEAD_TOGGLES_PER_S toggles in the last second
    leads = get(m, "leadsV3", []) or []
    seen = bool(leads) and float(get(leads[0], "prob", 0.0)) > AS08_LEAD_PROB
    if self.lead_seen is not None and seen != self.lead_seen:
      self.lead_toggles.append(t)
    self.lead_seen = seen
    self.lead_toggles = [x for x in self.lead_toggles if t - x <= 1.0]
    if len(self.lead_toggles) > AS08_LEAD_TOGGLES_PER_S and t > self.flicker_flagged_until:
      self.emit(t, "MON-13", "leadFlicker", ["AS-08"], toggles_per_s=len(self.lead_toggles))
      self.flicker_flagged_until = t + 1.0
    # AS-09: uncertainty above the evaluation-set 99.9th percentile
    limit = self.uncertainty_limits.get("lead_x_std")
    if limit is not None and leads:
      std = get(leads[0], "xStd", []) or []
      if self.edge("as09", bool(std) and float(std[0]) > limit):
        self.emit(t, "MON-13", "leadUncertaintySpike", ["AS-09"], xStd=round(float(std[0]), 3))

  def on_userBookmark(self, t, m):
    self.emit(t, "MON-14", "userBookmark", [])

  def on_initData(self, t, m):
    for k in ("gitCommit", "version", "dirty"):
      self.config[f"initData.{k}"] = get(m, k)

  def on_carParams(self, t, m):
    self.config["carParams.carFingerprint"] = str(get(m, "carFingerprint", ""))
    self.config["carParams.fuzzyFingerprint"] = bool(get(m, "fuzzyFingerprint", False))
    fw = get(m, "carFw", []) or []
    self.config["carParams.carFw"] = sorted(f"{get(f, 'ecu', '')}:{get(f, 'fwVersion', '')}" for f in fw)

  # --- driver ---------------------------------------------------------------------------
  def feed(self, t: float, service: str, msg) -> None:
    self.services.add(service)
    handler = getattr(self, f"on_{service}", None)
    if handler:
      handler(t, msg)

  def finish(self) -> None:
    if "modelV2" not in self.services:
      self.not_scored.update({"AS-05", "AS-08", "AS-09", "MON-13 (no modelV2: qlog or missing service)"})
    elif not self.uncertainty_limits:
      self.not_scored.add("AS-09 (no --uncertainty-limits from the evaluation set)")
    self.not_scored.add("AS-04 at-limit part (needs safety replay)")
    self.not_scored.add("AS-08 curvature divergence (no threshold in WP-V-04)")
    if self.release is None:
      self.not_scored.add("MON-16 (no --release record)")
    else:
      drift = {k: {"expected": v, "found": self.config.get(k)} for k, v in self.release.items() if self.config.get(k) != v}
      if drift:
        self.emit(0.0, "MON-16", "configurationDrift", [], fields=drift)


def scan_messages(route: str, messages, **kw) -> RouteScanner:
  """messages: iterable of (t_s, service, msg) in time order."""
  sc = RouteScanner(route, **kw)
  for t, service, msg in messages:
    sc.feed(t, service, msg)
  sc.finish()
  return sc


def read_log(path: str):
  """Yield (t_s, service, msg) from an rlog or qlog. Needs pycapnp and the cereal schema."""
  try:
    from openpilot.tools.lib.logreader import LogReader
  except ImportError as e:
    raise SystemExit(f"reading logs needs openpilot's LogReader (pycapnp, zstandard): {e}") from e
  t0 = None
  for ev in LogReader(path, sort_by_time=True):
    t0 = ev.logMonoTime if t0 is None else t0
    which = ev.which()
    yield (ev.logMonoTime - t0) / 1e9, which, getattr(ev, which)


# KPI thresholds (WP-O-04 §5, OI-5): proposals derived from the validation targets of WP-V-02 §4,
# pending assessor review (WP-V-02 OI-3) and development-drive baselines.
# kind: "zero" any occurrence is a finding; "rate" compared with a threshold per unit of engaged
# exposure ("h" engaged hour, "1000km" 1000 engaged km); "baseline" reported until a development
# baseline sets the threshold.
KPIS = [
  {"id": "K-01", "what": "crash candidates and bookmarks (MON-14)", "mon": {"MON-14"}, "kind": "zero",
   "basis": "VT-11: zero injury crashes; every candidate is reviewed (T1)"},
  {"id": "K-02", "what": "excessive-actuation latches", "triggers": {"excessiveActuation"}, "kind": "zero",
   "basis": "SG-01/03/04: any occurrence is T1"},
  {"id": "K-03", "what": "controlsMismatch and relayMalfunction", "mon": {"MON-03", "MON-04"}, "kind": "zero",
   "basis": "SG-01/SG-07: any occurrence is T1"},
  {"id": "K-04", "what": "envelope TX blocks while engaged", "triggers": {"safetyTxBlocked"}, "engaged": True,
   "kind": "baseline", "unit": "h", "basis": "no target; > 2x the development baseline once it exists"},
  {"id": "K-06", "what": "DM level-3 alerts and lockouts", "triggers": {"driverDistracted3", "driverUnresponsive3", "tooDistracted"},
   "kind": "rate", "unit": "h", "threshold": 0.1,
   "basis": "AOU-06: a level-3 alert follows two ignored warnings; more than one per 10 engaged hours is a misuse pattern"},
  {"id": "K-07", "what": "engaged above the ODD speed bound (MON-15)", "mon": {"MON-15"}, "kind": "zero",
   "basis": "VT-12: the deterministic speed bound (FM-07) prevents it"},
  {"id": "K-08", "what": "fault disengagements (MON-02)", "mon": {"MON-02"}, "kind": "baseline", "unit": "h",
   "basis": "no target; trend against the development baseline"},
  {"id": "K-10", "what": "lead flicker, AS-08 (VT-14 failures)", "signatures": {"AS-08"}, "kind": "rate", "unit": "h",
   "threshold": 0.6, "basis": "VT-14: p_s <= 1 % of 60 s steady-scene instances, at most 60 instances per engaged hour"},
  {"id": "K-13", "what": "phantom decelerations, AS-06", "signatures": {"AS-06"}, "kind": "rate", "unit": "1000km",
   "threshold": 1.0, "basis": "VT-04: <= 1 per 1000 km"},
  {"id": "K-14", "what": "lane-line proximity, AS-05", "signatures": {"AS-05"}, "kind": "rate", "unit": "h",
   "threshold": 0.6, "basis": "VT-01/AIR-01: <= 1 % of 60 s lane-keeping instances fail, at most 60 per engaged hour"},
]
ALPHA = 0.05  # one-sided, as the validation targets (95 %)


def poisson_cdf(k: int, mu: float) -> float:
  term = total = math.exp(-mu)
  for i in range(1, k + 1):
    term *= mu / i
    total += term
  return total


def poisson_bounds(n: int, alpha: float = ALPHA) -> tuple[float, float]:
  """Exact one-sided (lower, upper) bounds on the Poisson mean for n observed events."""
  def solve(f, lo=0.0, hi=1000.0 + 10 * n):
    for _ in range(200):
      mid = (lo + hi) / 2
      lo, hi = (mid, hi) if f(mid) else (lo, mid)
    return (lo + hi) / 2
  lower = 0.0 if n == 0 else solve(lambda mu: 1 - poisson_cdf(n - 1, mu) < alpha)
  upper = solve(lambda mu: poisson_cdf(n, mu) > alpha)
  return lower, upper


def kpi_matches(kpi: dict, e: Event) -> bool:
  if kpi.get("engaged") and not e.engaged:
    return False
  return (e.mon in kpi.get("mon", set()) or e.trigger in kpi.get("triggers", set())
          or bool(kpi.get("signatures", set()) & set(e.signatures)))


def evaluate_kpis(events: list[Event], engaged_h: float, engaged_km: float) -> list[dict]:
  """Status per KPI. rate KPIs: BREACH if the lower 95 % bound is above the threshold, WATCH if
  the point rate is, MET if the upper bound is below it, else OPEN (not enough exposure yet)."""
  rows = []
  for k in KPIS:
    n = sum(1 for e in events if kpi_matches(k, e))
    row = {"id": k["id"], "what": k["what"], "count": n, "basis": k["basis"]}
    if k["kind"] == "zero":
      row["status"] = "FINDING" if n else "OK"
    else:
      exposure = engaged_h if k["unit"] == "h" else engaged_km / 1000
      lo, hi = poisson_bounds(n)
      row.update({"unit": k["unit"], "exposure": round(exposure, 4)})
      if exposure > 0:
        row.update({"rate": round(n / exposure, 4), "lower95": round(lo / exposure, 4), "upper95": round(hi / exposure, 4)})
      if k["kind"] == "baseline":
        row["status"] = "BASELINE"
      else:
        t = k["threshold"]
        row["threshold"] = t
        row["exposure_to_demonstrate"] = round(hi / t, 2)  # exposure at which this count would meet the target
        if exposure <= 0:
          row["status"] = "OPEN"
        elif lo / exposure > t:
          row["status"] = "BREACH"
        elif n / exposure > t:
          row["status"] = "WATCH"
        elif hi / exposure <= t:
          row["status"] = "MET"
        else:
          row["status"] = "OPEN"
    rows.append(row)
  return rows


def summarise(scanners: list[RouteScanner]) -> dict:
  exposure = Exposure()
  events = [e for sc in scanners for e in sc.events]
  for sc in scanners:
    exposure.merge(sc.exposure)
  hours = exposure.engaged_s / 3600
  by_mon: dict = {}
  by_as: dict = {}
  for e in events:
    by_mon[e.mon] = by_mon.get(e.mon, 0) + 1
    for s in e.signatures:
      by_as[s] = by_as.get(s, 0) + 1

  def rate(n: int) -> float | None:
    return round(n / hours, 4) if hours > 0 else None

  return {
    "signature_set": SIGNATURE_SET_VERSION,
    "routes": [sc.route for sc in scanners],
    "exposure": {"total_h": round(exposure.total_s / 3600, 4), "engaged_h": round(hours, 4),
                 "total_km": round(exposure.total_m / 1000, 3), "engaged_km": round(exposure.engaged_m / 1000, 3),
                 "engaged_km_by_band_kmh": {k: round(v / 1000, 3) for k, v in exposure.engaged_m_by_band.items()}},
    "counts_by_mon": {k: {"count": v, "per_engaged_h": rate(v)} for k, v in sorted(by_mon.items())},
    "counts_by_signature": {k: {"count": v, "per_engaged_h": rate(v)} for k, v in sorted(by_as.items())},
    "triage": {c: sum(1 for e in events if e.triage == c) for c in ("T1", "T2", "T3")},
    "kpis": evaluate_kpis(events, hours, exposure.engaged_m / 1000),
    "not_scored": sorted(set().union(*(sc.not_scored for sc in scanners))) if scanners else [],
    "events": [e.row() for e in events],
  }


def markdown(summary: dict) -> str:
  ex = summary["exposure"]
  routes = len(summary["routes"])
  head = f"Signature set {summary['signature_set']}; {routes} route(s); engaged {ex['engaged_h']} h / {ex['engaged_km']} km"
  head += f" of {ex['total_h']} h / {ex['total_km']} km."
  out = [head, "", "| MON | Count | Per engaged h |", "|---|---|---|"]
  out += [f"| {k} | {v['count']} | {v['per_engaged_h']} |" for k, v in summary["counts_by_mon"].items()]
  out += ["", "| Signature | Count | Per engaged h |", "|---|---|---|"]
  out += [f"| {k} | {v['count']} | {v['per_engaged_h']} |" for k, v in summary["counts_by_signature"].items()]
  t = summary["triage"]
  out += ["", f"Triage: T1 {t['T1']}, T2 {t['T2']}, T3 {t['T3']}.", ""]
  out += ["| KPI | Count | Rate | 95 % bounds | Threshold | Status |", "|---|---|---|---|---|---|"]
  for k in summary["kpis"]:
    unit = {"h": "/h", "1000km": "/1000 km"}.get(k.get("unit"), "")
    rate = f"{k['rate']}{unit}" if "rate" in k else ""
    bounds = f"{k['lower95']}–{k['upper95']}" if "lower95" in k else ""
    thr = f"{k['threshold']}{unit}" if "threshold" in k else ("0" if k["status"] in ("OK", "FINDING") else "")
    out.append(f"| {k['id']} {k['what']} | {k['count']} | {rate} | {bounds} | {thr} | {k['status']} |")
  out += ["", "Not scored: " + "; ".join(summary["not_scored"])]
  return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("logs", nargs="+", help="rlog/qlog files; each file is one route segment")
  ap.add_argument("--release", help="JSON release record: field -> expected value (MON-16)")
  ap.add_argument("--uncertainty-limits", help="JSON with evaluation-set 99.9th percentiles, e.g. {\"lead_x_std\": 2.5} (AS-09)")
  ap.add_argument("--crash-decel", type=float, default=CRASH_DECEL_PLACEHOLDER, help="MON-14 candidate threshold (OI-8)")
  ap.add_argument("--json", help="write the summary and event table as JSON")
  ap.add_argument("--csv", help="write the event table as CSV")
  a = ap.parse_args(argv)
  release = json.load(open(a.release)) if a.release else None
  limits = json.load(open(a.uncertainty_limits)) if a.uncertainty_limits else None
  scanners = [scan_messages(os.path.basename(p), read_log(p), release=release, crash_decel=a.crash_decel,
                            uncertainty_limits=limits) for p in a.logs]
  summary = summarise(scanners)
  print(markdown(summary))
  if a.json:
    with open(a.json, "w") as f:
      json.dump(summary, f, indent=2)
  if a.csv:
    with open(a.csv, "w", newline="") as f:
      w = csv.DictWriter(f, fieldnames=["route", "t_s", "mon", "signatures", "trigger", "triage", "engaged", "detail"])
      w.writeheader()
      w.writerows(summary["events"])
  findings = any(k["status"] in ("FINDING", "BREACH") for k in summary["kpis"])
  return 1 if summary["triage"]["T1"] or findings else 0


if __name__ == "__main__":
  sys.exit(main())
