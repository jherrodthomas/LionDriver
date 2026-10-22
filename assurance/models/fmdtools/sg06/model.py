#!/usr/bin/env python3
"""SG-06 fault-propagation model in NASA fmdtools (tool evaluation TE-02, extended by DQ-417; step P1).

No `from __future__ import annotations`: fmdtools reads the State field types from the annotations at run time.

The functions of the SG-06 chain (supply, SoC, envelope, PCM, the host's alert logic, HMI, siren, driver) exchange a
few flows. Each failure mode of `events.yaml` is one fmdtools fault on one function and realises one event of the
WP-A-04 §7 tree. The structure follows the SG-02 model (../sg02/model.py); what is new is the ACC cancel: when
selfdrived disengages with an immediate disable, the host cancels ACC, PCM cruise drops and the cluster cruise
indicator changes (TSR-303, AOU-12), and if the cancel has no effect the panda's cancel-lag guard sounds the siren
(TSR-516(c)). The times are in `events.yaml`.

The top event TE-06 is read from a run's history: longitudinal deceleration is lost while engaged, and no perceivable
cue (a delivered SoC alert, the panda siren, the cluster cruise change, or the driver feeling the end of ACC
deceleration on a supply loss) comes within the 1 s budget.

Synthetic (DSR-12): no evidence credit. Vehicle physics stays in assurance/sim/plant.

    python3 model.py                       # nominal run and every single fault, one line each
    python3 model.py BE-6.01 BE-2.12       # one joint-fault run
"""

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from fmdtools.define.architecture.function import FunctionArchitecture
from fmdtools.define.block.function import Function
from fmdtools.define.container.mode import Mode
from fmdtools.define.container.parameter import Parameter
from fmdtools.define.container.state import State
from fmdtools.define.flow.base import Flow
import fmdtools.sim.propagate as propagate

HERE = Path(__file__).resolve().parent
EVENTS = yaml.safe_load((HERE / "events.yaml").read_text(encoding="utf-8"))
TICK = EVENTS["tick_s"]
BUDGET = round(EVENTS["budget_s"] / TICK)
# Delays round up to whole ticks, so a cue is never earlier in the model than in its source.
T = {k: math.ceil(round(v["s"] / TICK, 6)) for k, v in EVENTS["timing"].items()}
FAULT_TICK = 25            # cause injected 0.5 s into the run
# A run ends once the budget has passed for the latest possible loss: a cue after that cannot prevent TE-06.
END_TICK = FAULT_TICK + T["control_stop_after_selfdrived_stop"] + BUDGET + 2
NONE = -1.0                # time not reached

PHASES = {p["id"]: p for p in EVENTS["phases"]}
DEFAULT_PHASE = "approach"

MODE_OF = {m["event"]: (m["function"], m["mode"]) for m in EVENTS["modes"]}
EVENT_OF = {v: k for k, v in MODE_OF.items()}


def _modes(function: str):
  """Mode container of one function: one fault per events.yaml row of that function."""
  attrs = {f"fault_{m['mode']}": (1.0, 0) for m in EVENTS["modes"] if m["function"] == function}
  attrs["__doc__"] = f"Failure modes of {function} (events.yaml)."
  return type(f"{function.title()}Mode", (Mode,), attrs)


def _first(old: float, now: float) -> float:
  return now if old == NONE else old


def _earliest(old: float, t: float) -> float:
  return t if old == NONE else min(old, t)


# ---------------------------------------------------------------------------------------------------------- flows

class PowerS(State):
  on: bool = True
class Power(Flow):
  container_s = PowerS

class RoadS(State):
  decel_felt: bool = True        # the driver can feel the end of ACC deceleration
class Road(Flow):
  container_s = RoadS

class SocS(State):
  alive: bool = True             # whole SoC running
  selfdrived: bool = True        # selfdrived running
  t_selfdrived_stop: float = NONE
  frames: bool = True            # actuation frames, ACC_CONTROL with its cancel bit included, reach the bus
class Soc(Flow):
  container_s = SocS

class LongS(State):
  t_input: float = NONE          # plan, lead or model input lost
  t_block: float = NONE          # envelope blocks longitudinal authority
  t_acc: float = NONE            # PCM does not execute ACC
  acc_reported: bool = False     # ... and signals it as accFaulted
  t_nonfinite: float = NONE
  t_stale: float = NONE
  t_lead: float = NONE           # lead missed or late
  t_frames: float = NONE
  t_selfdrived: float = NONE     # control stop after a selfdrived stop
  t_soc_down: float = NONE
  t_supply: float = NONE
class Long(Flow):
  container_s = LongS

class CueS(State):
  t_alert_request: float = NONE  # the host's alert logic asks the HMI for a take-over alert
  t_alert: float = NONE          # alert delivered by the HMI
  t_disengage: float = NONE      # selfdrived disengages on the fault
  t_siren_request: float = NONE  # the envelope asks for the siren
  t_siren: float = NONE          # siren sounds
  t_cluster: float = NONE        # PCM cruise drops on the host's cancel: the cluster cruise indicator changes
  t_feel: float = NONE           # driver feels the end of ACC deceleration (supply loss only)
class Cue(Flow):
  container_s = CueS


# ------------------------------------------------------------------------------------------------------ functions

class Supply(Function):
  """12 V supply to the device (FSC node N08)."""

  container_m = _modes("supply")
  flow_power = Power
  flow_long = Long

  def static_behavior(self):
    if self.m.has_fault("loss"):
      self.power.s.on = False
      self.long.s.t_supply = _first(self.long.s.t_supply, self.t.time)


class SocFn(Function):
  """SoC: model input, plannerd, controlsd, card, pandad, selfdrived (the causes that start on the SoC)."""

  container_m = _modes("soc")
  flow_power = Power
  flow_soc = Soc
  flow_long = Long

  def static_behavior(self):
    now, lon = self.t.time, self.long.s
    if not self.power.s.on or self.m.has_fault("crash"):
      if self.soc.s.alive:
        self.soc.s.alive = False
        self.soc.s.frames = False
        lon.t_soc_down = _first(lon.t_soc_down, now)
      return
    if self.m.has_fault("selfdrived_stop"):
      if self.soc.s.selfdrived:
        self.soc.s.selfdrived = False
        self.soc.s.t_selfdrived_stop = now
      if now - self.soc.s.t_selfdrived_stop >= T["control_stop_after_selfdrived_stop"]:
        lon.t_selfdrived = _first(lon.t_selfdrived, now)
    if self.m.has_fault("input_stale"):
      lon.t_input = _first(lon.t_input, now)
    if self.m.has_fault("nonfinite"):
      lon.t_nonfinite = _first(lon.t_nonfinite, now)
    if self.m.has_fault("stale_accel"):
      lon.t_stale = _first(lon.t_stale, now)     # not removed by the envelope: BE-1.22 latent_in_model
    if self.m.has_fault("lead_missed"):
      lon.t_lead = _first(lon.t_lead, now)
    if self.m.has_fault("frames_stop"):
      self.soc.s.frames = False
      lon.t_frames = _first(lon.t_frames, now)


class Envelope(Function):
  """Panda safety envelope: longitudinal authority, heartbeat watch, siren triggers."""

  container_m = _modes("envelope")
  flow_power = Power
  flow_soc = Soc
  flow_long = Long
  flow_cue = Cue

  def static_behavior(self):
    now, lon, cue = self.t.time, self.long.s, self.cue.s
    if not self.power.s.on:
      return
    if self.m.has_fault("block"):
      lon.t_block = _first(lon.t_block, now)
    # The siren sounds on a heartbeat loss (TSR-516(a), (b) via TSR-408) and on the engaged-mismatch revocation after a
    # selfdrived stop (TSR-307(a), TSR-516(c), panda f4803c5), as in the SG-02 model. BE-6.02 gets none: as BE-2.02,
    # the event includes blocking without a revocation.
    if lon.t_soc_down != NONE:
      cue.t_siren_request = _earliest(cue.t_siren_request, lon.t_soc_down + T["siren_after_heartbeat_loss"])
    if not self.soc.s.selfdrived:
      cue.t_siren_request = _earliest(cue.t_siren_request, self.soc.s.t_selfdrived_stop + T["siren_after_selfdrived_stop"])


class Pcm(Function):
  """PCM: executes ACC, signals its faults (accFaulted), and drops cruise on the host's cancel (TSR-303)."""

  container_m = _modes("pcm")
  flow_soc = Soc
  flow_long = Long
  flow_cue = Cue

  def static_behavior(self):
    now, lon, cue = self.t.time, self.long.s, self.cue.s
    if self.m.has_fault("acc_fault") and lon.t_acc == NONE:
      lon.t_acc = now
      lon.acc_reported = not self.m.has_fault("silent")
    if cue.t_disengage == NONE:
      return
    # The cancel reaches the PCM only in ACC_CONTROL from a running SoC and only while the envelope passes the frame.
    # A PCM that has stopped executing ACC gets no credit: its cruise state after the fault is not characterised.
    cancel = (self.soc.s.alive and self.soc.s.frames and lon.t_block == NONE and lon.t_acc == NONE
              and not self.m.has_fault("no_cancel"))
    if cancel:
      t = cue.t_disengage + T["cluster_after_disengage"]
      if now >= t:
        cue.t_cluster = _first(cue.t_cluster, t)
    elif self.soc.s.alive and self.soc.s.frames and lon.t_acc == NONE:
      # PCM cruise is still active 0.5 s after the first "not engaged" heartbeat: the cancel-lag guard (TSR-516(c)).
      # Not credited when the frames stop: BE-2.06 includes an MCU hang, so the model takes the case with no siren.
      cue.t_siren_request = _earliest(cue.t_siren_request, cue.t_disengage + T["siren_after_failed_cancel"])


class Monitor(Function):
  """The host's alert logic (selfdrived, events.py): when it asks the HMI for a take-over alert, and when it
  disengages."""

  container_m = _modes("monitor")
  flow_power = Power
  flow_soc = Soc
  flow_long = Long
  flow_cue = Cue

  def due(self) -> tuple[float, float]:
    """(alert time, disengagement time) for the faults present; NONE where there is none."""
    lon, m = self.long.s, self.m
    if not self.power.s.on or not self.soc.s.alive:
      return NONE, NONE
    if not self.soc.s.selfdrived:
      return self.soc.s.t_selfdrived_stop + T["ui_unresponsive_after_selfdrived_stop"], NONE
    alerts, disengage = [], []
    if lon.t_input != NONE and not m.has_fault("diag_masked"):
      if m.has_fault("soft_disable"):
        disengage.append(lon.t_input + T["soft_disable"])     # no adequate alert while soft-disabling (BE-2.10)
      else:
        alerts.append(lon.t_input + T["host_alert_input_loss"])
    if lon.t_block != NONE and not m.has_fault("block_undetected"):
      alerts.append(lon.t_block + T["host_alert_envelope_block"])
    if lon.t_acc != NONE and lon.acc_reported:
      alerts.append(lon.t_acc + T["host_alert_acc_fault"])
    # lon.t_nonfinite: never warned at the baseline (BE-2.11); lon.t_stale: no freshness check (BE-1.22);
    # lon.t_lead: the FCW comes from the same lead (BE-6.10)
    if lon.t_frames != NONE and not m.has_fault("frames_unreported"):
      alerts.append(lon.t_frames + T["host_alert_frames_lost"])
    alert = min(alerts) if alerts else NONE
    # every alert above comes with an immediate disable
    return alert, min(disengage + alerts) if disengage or alerts else NONE

  def static_behavior(self):
    alert, disengage = self.due()
    now, cue = self.t.time, self.cue.s
    if alert != NONE and now >= alert:
      cue.t_alert_request = _first(cue.t_alert_request, alert)
    if disengage != NONE and now >= disengage:
      cue.t_disengage = _first(cue.t_disengage, disengage)


class Hmi(Function):
  """UI and soundd: deliver the requested take-over alert."""

  container_m = _modes("hmi")
  flow_power = Power
  flow_soc = Soc
  flow_cue = Cue

  def static_behavior(self):
    cue = self.cue.s
    ok = self.power.s.on and self.soc.s.alive and not any(self.m.has_fault(f) for f in ("hang", "inaudible", "masked"))
    if ok and cue.t_alert_request != NONE and self.t.time >= cue.t_alert_request:
      cue.t_alert = _first(cue.t_alert, cue.t_alert_request)


class Siren(Function):
  """Panda siren (TSR-516): sounds when the envelope asks, unless its trigger or path fails."""

  container_m = _modes("siren")
  flow_power = Power
  flow_cue = Cue

  def static_behavior(self):
    cue = self.cue.s
    ok = self.power.s.on and not any(self.m.has_fault(f) for f in ("not_triggered", "silenced", "path_fault"))
    if ok and cue.t_siren_request != NONE and self.t.time >= cue.t_siren_request:
      cue.t_siren = _first(cue.t_siren, cue.t_siren_request)


class Driver(Function):
  """Driver: notices the end of ACC deceleration on a supply loss (UE-6.07, AOU-12)."""

  container_m = _modes("driver")
  flow_long = Long
  flow_cue = Cue
  flow_road = Road

  def static_behavior(self):
    lon = self.long.s
    if lon.t_supply != NONE and self.road.s.decel_felt and not self.m.has_fault("unaware"):
      self.cue.s.t_feel = _first(self.cue.s.t_feel, lon.t_supply)


class Sg06Param(Parameter):
  phase: str = DEFAULT_PHASE     # a row of events.yaml phases


class Sg06(FunctionArchitecture):
  """SG-06 chain: one function per element, flows between them."""

  container_p = Sg06Param
  default_sp = dict(end_time=float(END_TICK), dt=1.0)
  default_track = {"flows": {"long": "all", "cue": "all"}}

  def init_architecture(self, **kwargs):
    for name, flow in (("power", Power), ("soc", Soc), ("long", Long), ("cue", Cue)):
      self.add_flow(name, flow)
    self.add_flow("road", Road, s={"decel_felt": PHASES[self.p.phase]["decel_felt"]})
    self.add_fxn("supply", Supply, "power", "long")
    self.add_fxn("soc", SocFn, "power", "soc", "long")
    self.add_fxn("envelope", Envelope, "power", "soc", "long", "cue")
    self.add_fxn("monitor", Monitor, "power", "soc", "long", "cue")
    self.add_fxn("pcm", Pcm, "soc", "long", "cue")
    self.add_fxn("hmi", Hmi, "power", "soc", "cue")
    self.add_fxn("siren", Siren, "power", "cue")
    self.add_fxn("driver", Driver, "long", "cue", "road")


# ------------------------------------------------------------------------------------------------------- results

LOSS_FIELDS = ("t_input", "t_block", "t_acc", "t_nonfinite", "t_stale", "t_lead", "t_frames", "t_selfdrived",
               "t_soc_down", "t_supply")
CUE_FIELDS = ("t_alert", "t_siren", "t_cluster", "t_feel")


@dataclass(frozen=True)
class Outcome:
  events: tuple[str, ...]
  t_lost: float | None       # seconds after injection, None if deceleration was not lost
  t_cue: float | None        # first perceivable cue, seconds after injection
  cue: str | None
  top_event: bool            # TE-06: lost, and no cue within the budget

  def line(self) -> str:
    fmt = lambda v: "-" if v is None else f"{v:.2f} s"
    return (f"{'+'.join(self.events) or 'nominal':32} lost {fmt(self.t_lost):>7}  cue {fmt(self.t_cue):>7} "
            f"{(self.cue or ''):7}  {'TE-06' if self.top_event else 'ok'}")


def times(events: tuple[str, ...] | list[str] = (), tick: int = FAULT_TICK, phase: str = DEFAULT_PHASE,
          horizon_s: float | None = None) -> dict[str, float]:
  """Inject the failure modes of `events` together at `tick` in road `phase`; every time the long and cue flows reach,
  in seconds after the injection (fields never reached are left out). `horizon_s` runs on that long after the
  injection, to see cues that come after the budget (step P4)."""
  seq: dict[str, list[str]] = {}
  for e in sorted(events):
    fxn, mode = MODE_OF[e]
    seq.setdefault(fxn, []).append(mode)
  sp = None if horizon_s is None else dict(end_time=float(tick + math.ceil(horizon_s / TICK)), dt=1.0)
  mdl = Sg06(p={"phase": phase}) if sp is None else Sg06(p={"phase": phase}, sp=sp)
  if seq:
    _, hist = propagate.sequence(mdl, faultseq={float(tick): seq}, include_nominal=False, showprogress=False)
  else:
    _, hist = propagate.nominal(mdl, showprogress=False)
  # keys are "<scenario>.flows..." for a fault run and "flows..." for a nominal run
  last = {k[k.index("flows."):]: v[-1] for k, v in hist.items() if "flows." in k}
  out = {}
  for flow, fields in (("long", LOSS_FIELDS), ("cue", CUE_FIELDS + ("t_alert_request", "t_disengage", "t_siren_request"))):
    for f in fields:
      v = float(last.get(f"flows.{flow}.s.{f}", NONE))
      if v != NONE:
        out[f] = round((v - tick) * TICK, 6)
  return out


def run(events: tuple[str, ...] | list[str] = (), tick: int = FAULT_TICK, phase: str = DEFAULT_PHASE,
        horizon_s: float | None = None) -> Outcome:
  """Inject the failure modes of `events` together at `tick` in road `phase` and read TE-06 from the history."""
  events = tuple(sorted(events))
  t = times(events, tick, phase, horizon_s)
  losses = [t[f] for f in LOSS_FIELDS if f in t]
  cues = [(t[f], f[2:]) for f in CUE_FIELDS if f in t]
  t_lost = min(losses) if losses else None
  t_cue, cue = min(cues) if cues else (None, None)
  te = t_lost is not None and (t_cue is None or round((t_cue - t_lost) / TICK) > BUDGET)   # in whole ticks
  return Outcome(events, t_lost, t_cue, cue, bool(te))


def main(argv: list[str]) -> int:
  if argv:
    print(run(argv).line())
    return 0
  print(run().line())
  for e in MODE_OF:
    print(run((e,)).line())
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
