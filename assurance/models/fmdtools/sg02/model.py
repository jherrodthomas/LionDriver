#!/usr/bin/env python3
"""SG-02 fault-propagation model in NASA fmdtools (TE-02, step P1).

No `from __future__ import annotations`: fmdtools reads the State field types from the annotations at run time.

The functions of the SG-02 chain (supply, SoC, envelope, EPS, the host's alert logic, HMI, siren, driver) exchange a
few flows. Each failure mode of `events.yaml` is one fmdtools fault on one function and realises one event of the
WP-A-04 §4 tree. Nominal behaviour and timing follow the reference build after BL-005 as WP-A-04 describes it; the
times are in `events.yaml`.

The top event TE-02 is read from a run's history: lateral control is lost while engaged, and no perceivable cue
(a delivered SoC alert, the panda siren, or the driver feeling the end of LKA torque on a supply loss) comes within
the 1 s budget.

Synthetic (DSR-12): no evidence credit. Vehicle physics stays in assurance/sim/plant.

    python3 model.py                       # nominal run and every single fault, one line each
    python3 model.py BE-2.01 BE-2.14       # one joint-fault run
"""

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml
from fmdtools.define.architecture.function import FunctionArchitecture
from fmdtools.define.block.function import Function
from fmdtools.define.container.mode import Mode
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
# A run ends once the budget has passed for the latest possible loss: a cue after that cannot prevent TE-02.
END_TICK = FAULT_TICK + T["control_stop_after_selfdrived_stop"] + BUDGET + 2
NONE = -1.0                # time not reached

MODE_OF = {m["event"]: (m["function"], m["mode"]) for m in EVENTS["modes"]}
EVENT_OF = {v: k for k, v in MODE_OF.items()}


def _modes(function: str):
  """Mode container of one function: one fault per events.yaml row of that function."""
  attrs = {f"fault_{m['mode']}": (1.0, 0) for m in EVENTS["modes"] if m["function"] == function}
  attrs["__doc__"] = f"Failure modes of {function} (events.yaml)."
  return type(f"{function.title()}Mode", (Mode,), attrs)


def _first(old: float, now: float) -> float:
  return now if old == NONE else old


# ---------------------------------------------------------------------------------------------------------- flows

class PowerS(State):
  on: bool = True
class Power(Flow):
  container_s = PowerS

class SocS(State):
  alive: bool = True             # whole SoC running
  selfdrived: bool = True        # selfdrived running
  t_selfdrived_stop: float = NONE
class Soc(Flow):
  container_s = SocS

class LateralS(State):
  t_lost: float = NONE           # earliest loss or degradation of lateral control
  t_eps: float = NONE            # EPS drop (reported or not)
  eps_reported: bool = False     # the drop is reported in 0x262
  t_block: float = NONE
  t_input: float = NONE
  t_nonfinite: float = NONE
  t_frames: float = NONE
  t_insufficient: float = NONE
  t_selfdrived: float = NONE     # control stop after a selfdrived stop
  t_soc_down: float = NONE
  t_supply: float = NONE
  diag_request: bool = False     # the SoC sends a diagnostic request towards the EPS
  reset_request: bool = False    # ... and the envelope passes it
class Lateral(Flow):
  container_s = LateralS

class CueS(State):
  t_alert_request: float = NONE  # the host's alert logic asks the HMI for a take-over alert
  t_alert: float = NONE          # alert delivered by the HMI
  t_siren_request: float = NONE  # the envelope asks for the siren
  t_siren: float = NONE          # siren sounds
  t_feel: float = NONE           # driver feels the end of LKA torque and sees the cluster (supply loss only)
class Cue(Flow):
  container_s = CueS


# ------------------------------------------------------------------------------------------------------ functions

class Supply(Function):
  """12 V supply to the device (FSC node N08)."""

  container_m = _modes("supply")
  flow_power = Power
  flow_lateral = Lateral

  def static_behavior(self):
    if self.m.has_fault("loss"):
      self.power.s.on = False
      self.lateral.s.t_supply = _first(self.lateral.s.t_supply, self.t.time)


class SocFn(Function):
  """SoC: model input, controlsd, card, pandad, selfdrived (the causes that start on the SoC)."""

  container_m = _modes("soc")
  flow_power = Power
  flow_soc = Soc
  flow_lateral = Lateral

  def static_behavior(self):
    now, lat = self.t.time, self.lateral.s
    if not self.power.s.on or self.m.has_fault("crash"):
      if self.soc.s.alive:
        self.soc.s.alive = False
        lat.t_soc_down = _first(lat.t_soc_down, now)
      return
    if self.m.has_fault("selfdrived_stop"):
      if self.soc.s.selfdrived:
        self.soc.s.selfdrived = False
        self.soc.s.t_selfdrived_stop = now
      if now - self.soc.s.t_selfdrived_stop >= T["control_stop_after_selfdrived_stop"]:
        lat.t_selfdrived = _first(lat.t_selfdrived, now)
    if self.m.has_fault("input_stale"):
      lat.t_input = _first(lat.t_input, now)
    if self.m.has_fault("nonfinite"):
      lat.t_nonfinite = _first(lat.t_nonfinite, now)
    if self.m.has_fault("frames_stop"):
      lat.t_frames = _first(lat.t_frames, now)
    if self.m.has_fault("insufficient"):
      lat.t_insufficient = _first(lat.t_insufficient, now)
    if self.m.has_fault("diag_request"):
      lat.diag_request = True


class Envelope(Function):
  """Panda safety envelope: authority, heartbeat watch, siren triggers, diagnostic TX filter."""

  container_m = _modes("envelope")
  flow_power = Power
  flow_soc = Soc
  flow_lateral = Lateral
  flow_cue = Cue

  def static_behavior(self):
    now, lat, cue = self.t.time, self.lateral.s, self.cue.s
    if not self.power.s.on:
      return
    if self.m.has_fault("block"):
      lat.t_block = _first(lat.t_block, now)
    lat.reset_request = lat.diag_request and self.m.has_fault("diag_pass")
    # The siren sounds on every revocation that is not a driver action (TSR-516(b), panda 8a69ccf): a heartbeat loss,
    # a reported EPS fault, and the engaged mismatch after a selfdrived stop. BE-2.02 gets none: the event includes
    # blocking without a revocation (SWF-047.C3), so the model takes the case with no siren.
    if lat.t_soc_down != NONE:
      cue.t_siren_request = _first(cue.t_siren_request, lat.t_soc_down + T["siren_after_heartbeat_loss"])
    if lat.t_eps != NONE and lat.eps_reported:
      cue.t_siren_request = _first(cue.t_siren_request, lat.t_eps + T["siren_after_eps_fault"])
    if not self.soc.s.selfdrived:
      revoke = self.soc.s.t_selfdrived_stop + T["revoke_after_engaged_mismatch"]
      cue.t_siren_request = _first(cue.t_siren_request, revoke + T["siren_after_revocation"])


class Eps(Function):
  """EPS: LKA assistance and its fault state in 0x262."""

  container_m = _modes("eps")
  flow_lateral = Lateral

  def static_behavior(self):
    lat = self.lateral.s
    if self.m.has_fault("lka_drop") or lat.reset_request:
      if lat.t_eps == NONE:
        lat.t_eps = self.t.time
        lat.eps_reported = not self.m.has_fault("silent_drop")


class Monitor(Function):
  """The host's alert logic (selfdrived, events.py): when it asks the HMI for a take-over alert."""

  container_m = _modes("monitor")
  flow_power = Power
  flow_soc = Soc
  flow_lateral = Lateral
  flow_cue = Cue

  def due(self) -> float:
    lat, m = self.lateral.s, self.m
    if not self.power.s.on or not self.soc.s.alive:
      return NONE
    if not self.soc.s.selfdrived:
      return self.soc.s.t_selfdrived_stop + T["ui_unresponsive_after_selfdrived_stop"]
    times = []
    if lat.t_eps != NONE and lat.eps_reported:
      delay = "host_alert_eps_fault_after_override" if m.has_fault("eps_prompt_only") else "host_alert_eps_fault"
      times.append(lat.t_eps + T[delay])
    if lat.t_block != NONE and not m.has_fault("block_undetected"):
      times.append(lat.t_block + T["host_alert_envelope_block"])
    if lat.t_input != NONE and not (m.has_fault("soft_disable") or m.has_fault("diag_masked")):
      times.append(lat.t_input + T["host_alert_input_loss"])
    # lat.t_nonfinite: never warned at the baseline (BE-2.11, latent_in_model)
    if lat.t_frames != NONE and not m.has_fault("frames_unreported"):
      times.append(lat.t_frames + T["host_alert_frames_lost"])
    if lat.t_insufficient != NONE and not m.has_fault("saturation_late"):
      times.append(lat.t_insufficient + T["host_alert_saturation"])
    return min(times) if times else NONE

  def static_behavior(self):
    due = self.due()
    if due != NONE and self.t.time >= due:
      self.cue.s.t_alert_request = _first(self.cue.s.t_alert_request, due)


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
  """Driver: notices the end of LKA torque and the cluster on a supply loss (AOU-01R, AOU-12)."""

  container_m = _modes("driver")
  flow_lateral = Lateral
  flow_cue = Cue

  def static_behavior(self):
    lat = self.lateral.s
    if lat.t_supply != NONE and not self.m.has_fault("unaware"):
      self.cue.s.t_feel = _first(self.cue.s.t_feel, lat.t_supply)


class Sg02(FunctionArchitecture):
  """SG-02 chain: one function per element, flows between them."""

  default_sp = dict(end_time=float(END_TICK), dt=1.0)
  default_track = {"flows": {"lateral": "all", "cue": "all"}}

  def init_architecture(self, **kwargs):
    for name, flow in (("power", Power), ("soc", Soc), ("lateral", Lateral), ("cue", Cue)):
      self.add_flow(name, flow)
    self.add_fxn("supply", Supply, "power", "lateral")
    self.add_fxn("soc", SocFn, "power", "soc", "lateral")
    self.add_fxn("envelope", Envelope, "power", "soc", "lateral", "cue")
    self.add_fxn("eps", Eps, "lateral")
    self.add_fxn("monitor", Monitor, "power", "soc", "lateral", "cue")
    self.add_fxn("hmi", Hmi, "power", "soc", "cue")
    self.add_fxn("siren", Siren, "power", "cue")
    self.add_fxn("driver", Driver, "lateral", "cue")


# ------------------------------------------------------------------------------------------------------- results

LOSS_FIELDS = ("t_eps", "t_block", "t_input", "t_nonfinite", "t_frames", "t_insufficient", "t_selfdrived",
               "t_soc_down", "t_supply")
CUE_FIELDS = ("t_alert", "t_siren", "t_feel")


@dataclass(frozen=True)
class Outcome:
  events: tuple[str, ...]
  t_lost: float | None       # seconds after injection, None if control was not lost
  t_cue: float | None        # first perceivable cue, seconds after injection
  cue: str | None
  top_event: bool            # TE-02: lost, and no cue within the budget

  def line(self) -> str:
    fmt = lambda v: "-" if v is None else f"{v:.2f} s"
    return (f"{'+'.join(self.events) or 'nominal':32} lost {fmt(self.t_lost):>7}  cue {fmt(self.t_cue):>7} "
            f"{(self.cue or ''):6}  {'TE-02' if self.top_event else 'ok'}")


def run(events: tuple[str, ...] | list[str] = (), tick: int = FAULT_TICK) -> Outcome:
  """Inject the failure modes of `events` together at `tick` and read TE-02 from the history."""
  events = tuple(sorted(events))
  seq: dict[str, list[str]] = {}
  for e in events:
    fxn, mode = MODE_OF[e]
    seq.setdefault(fxn, []).append(mode)
  mdl = Sg02()
  if seq:
    _, hist = propagate.sequence(mdl, faultseq={float(tick): seq}, include_nominal=False, showprogress=False)
  else:
    _, hist = propagate.nominal(mdl, showprogress=False)
  # keys are "<scenario>.flows..." for a fault run and "flows..." for a nominal run
  last = {k[k.index("flows."):]: v[-1] for k, v in hist.items() if "flows." in k}
  get = lambda flow, f: float(last.get(f"flows.{flow}.s.{f}", NONE))
  losses = [get("lateral", f) for f in LOSS_FIELDS if get("lateral", f) != NONE]
  cues = [(get("cue", f), f[2:]) for f in CUE_FIELDS if get("cue", f) != NONE]
  t_lost = min(losses) if losses else None
  t_cue, cue = min(cues) if cues else (None, None)
  rel = lambda t: None if t is None else (t - tick) * TICK
  te = t_lost is not None and (t_cue is None or t_cue - t_lost > BUDGET)
  return Outcome(events, rel(t_lost), rel(t_cue), cue, bool(te))


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
