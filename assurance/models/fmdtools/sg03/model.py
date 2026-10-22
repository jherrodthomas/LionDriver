#!/usr/bin/env python3
"""SG-03 fault-propagation model in NASA fmdtools (tool evaluation TE-02, extended by DQ-417; step P1).

No `from __future__ import annotations`: fmdtools reads the State field types from the annotations at run time.

SG-03 is the acceleration goal (WP-A-04 §3), and the model is built like the SG-01 one (../sg01/model.py): the driver
and PCM, the panda RX path, the SoC, the envelope, the TX path after the hook, the harness relay and the PCM's execution
of the request exchange a few flows, and the envelope and the SoC read the same CAN frames (DFI-10).

A run gives TE-03 when, after the fault:
- an acceleration above the controllable bound (or a step to the bound) reaches the PCM and the PCM executes it
  without its own bound (G3.1, G3.6);
- an in-bound positive acceleration in a closing situation is not stopped by the driver (G3.2);
- the item's acceleration reaches the bus while the driver has not engaged, or longer than the SG-05 release time after
  the driver brakes or cancels (G3.3);
- the item's acceleration reaches the bus while the driver presses the accelerator and the PCM adds it (G3.4);
- a stale positive acceleration is held longer than the 1 s FTTI (G3.5);
- the stock ACC and the item's frames are on the car bus together for longer than the FTTI (G3.7).

Synthetic (DSR-12): no evidence credit. Vehicle physics stays in assurance/sim/plant.

    python3 model.py                       # every single fault in each phase, one line each
    python3 model.py BE-3.13 BE-1.25       # one joint-fault run, every phase
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
RELEASE = round(EVENTS["release_s"] / TICK)
# Delays round up to whole ticks, so a protection is never earlier in the model than in its source.
T = {k: math.ceil(round(v["s"] / TICK, 6)) for k, v in EVENTS["timing"].items()}
FAULT_TICK = 25            # cause injected 0.5 s into the run
END_TICK = FAULT_TICK + T["driver_action"] + RELEASE + BUDGET + 4
NONE = -1.0                # time not reached

PHASES = {p["id"]: p for p in EVENTS["phases"]}
DEFAULT_PHASE = "engaged"

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

class CarS(State):
  item_on: bool = True           # the phase starts with the item engaged
  action: int = 0                # the phase's driver action: 0 none, 1 brake, 2 cancel, 3 accelerator
  engaged: bool = True           # the driver has the item engaged, until the driver brakes or cancels
  t_action: float = NONE         # the driver brakes or cancels
  brake: bool = False            # brake pressed (0x226 on the bus)
  cruise: bool = True            # PCM cruise active (0x1D2 on the bus)
  gas: bool = False              # accelerator pressed (GAS_RELEASED = 0)
class Car(Flow):
  container_s = CarS

class RxS(State):
  brake: bool = False            # brake as the envelope and the SoC read it
  cruise: bool = True            # PCM cruise as the envelope and the SoC read it
  gas: bool = False              # accelerator as the envelope reads it
  edge: bool = False             # a cruise rising edge is read in this step
class Rx(Flow):
  container_s = RxS

class SocS(State):
  engaged: bool = True           # openpilot engaged (also the heartbeat's engaged flag)
  t_disengaged: float = NONE
  accel: bool = False            # requests a positive acceleration
  excess: bool = False           # ... above the controllable bound
  step: bool = False             # ... a step to the bound
  closing: bool = False          # ... in bound, but toward a closing lead
  stale: bool = False            # ... frozen at an old value
class Soc(Flow):
  container_s = SocS

class EnvS(State):
  allowed: bool = True           # controls_allowed
  refused: bool = False          # the item's frames are refused (relay malfunction)
  t_stock_seen: float = NONE     # the stock frames are first seen on the car side
  relay_check: bool = True       # the relay-malfunction check works
class Env(Flow):
  container_s = EnvS

class BusS(State):
  accel: bool = False            # the item's positive acceleration reaches the car bus
  excess: bool = False
  closing: bool = False
  stale: bool = False
  corrupt: bool = False          # a frame is corrupted after the TX hook
  stock: bool = False            # the stock ACC_CONTROL reaches the car side
class Bus(Flow):
  container_s = BusS

class DrvS(State):
  no_brake: bool = False         # the driver does not brake in time for a closing lead (UE-3.08)
class Drv(Flow):
  container_s = DrvS

class OutS(State):
  t_excess: float = NONE         # acceleration above the bound executed by the PCM
  t_closing: float = NONE        # in-bound acceleration toward a closing lead, not stopped by the driver
  t_since: float = NONE          # start of the current run of acceleration the driver does not want
  t_unwanted: float = NONE       # ... once that run has lasted the SG-05 release time
  t_gas: float = NONE            # the item's acceleration added on top of the driver's pedal
  t_stale_over: float = NONE     # a stale acceleration still held at the FTTI
  t_overlap_over: float = NONE   # stock ACC and the item still together at the FTTI
class Out(Flow):
  container_s = OutS


# ------------------------------------------------------------------------------------------------------ functions

class Driver(Function):
  """Driver and PCM: keep the item engaged, or brake, cancel or press the accelerator 0.1 s after the fault (phase);
  the driver also brakes for a closing lead unless UE-3.08."""

  container_m = _modes("driver")
  flow_car = Car
  flow_drv = Drv

  def static_behavior(self):
    car, now = self.car.s, self.t.time
    self.drv.s.no_brake = self.m.has_fault("no_brake")
    if car.action and now >= FAULT_TICK + T["driver_action"]:
      if car.action == 3:
        car.gas = True                           # an override: the item stays engaged
        return
      car.t_action = _first(car.t_action, FAULT_TICK + T["driver_action"])
      car.engaged = False
      car.cruise = False                         # the PCM drops cruise on a brake press or a cancel
      car.brake = car.action == 1


class RxPath(Function):
  """Panda RX path: what the envelope and the SoC read of the brake, cruise and gas signals (one path, DFI-10)."""

  container_m = _modes("rx")
  flow_car = Car
  flow_rx = Rx

  def static_behavior(self):
    car, rx, now, m = self.car.s, self.rx.s, self.t.time, self.m
    unseen = m.has_fault("brake_unseen")         # BE-3.09: 0x226 not detected and the PCM keeps ACC on the brake
    rx.brake = car.brake and not unseen
    stuck = m.has_fault("stuck_path") or (unseen and car.action == 1)
    rx.cruise = car.item_on if stuck else car.cruise
    rx.gas = car.gas and not m.has_fault("gas_stuck_released")
    # a corrupted frame: one step reads cruise active, the genuine frames that follow read the true state
    rx.edge = m.has_fault("false_edge") and now == FAULT_TICK and not rx.cruise
    if rx.edge:
      rx.cruise = True


class SocFn(Function):
  """SoC: selfdrived engagement from the frames it reads, and the acceleration plannerd, controlsd and card request."""

  container_m = _modes("soc")
  flow_rx = Rx
  flow_soc = Soc

  def static_behavior(self):
    rx, soc, now, m = self.rx.s, self.soc.s, self.t.time, self.m
    if soc.engaged and soc.t_disengaged == NONE and (rx.brake or not rx.cruise):
      soc.engaged = False
      soc.t_disengaged = now
    engaged = soc.engaged or rx.edge             # pcmCruise: openpilot engages on the edge it reads
    soc.accel = engaged or m.has_fault("accel_ungated")
    soc.excess = soc.accel and any(m.has_fault(f) for f in ("planner_fault", "wrong_params"))
    soc.step = engaged and m.has_fault("step")
    soc.closing = engaged and m.has_fault("closing_accel")
    stale_model = m.has_fault("stale_model") and now - FAULT_TICK < T["stale_model_removed"]
    soc.stale = engaged and (stale_model or m.has_fault("replay"))


class Envelope(Function):
  """Panda safety envelope: controls_allowed, the inactive-value check (also while the accelerator is pressed,
  TSR-305), the acceleration clamp, the engaged-mismatch check and the relay-malfunction check."""

  container_m = _modes("envelope")
  flow_rx = Rx
  flow_soc = Soc
  flow_env = Env
  flow_bus = Bus

  def static_behavior(self):
    rx, soc, env, bus, now, m = self.rx.s, self.soc.s, self.env.s, self.bus.s, self.t.time, self.m
    if rx.brake or not rx.cruise:                # TSR-302 brake, TSR-301 cruise inactive
      env.allowed = False
    if rx.edge:                                  # TSR-301: the edge opens a window and the heartbeat flag grants;
      env.allowed = True                         # the SoC reads the same edge and engages, so the flag is set
    if soc.t_disengaged != NONE and now - soc.t_disengaged >= T["engaged_mismatch_revoke"]:
      env.allowed = False                        # TSR-307(a)
    if m.has_fault("allowed_set"):
      env.allowed = True
    if env.t_stock_seen != NONE and env.relay_check:
      if now - env.t_stock_seen >= T["relay_detect"]:
        env.refused = True
      if now - env.t_stock_seen >= T["relay_revoke"]:
        env.allowed = False
    check = not any(m.has_fault(f) for f in ("mode_changed", "firmware_replaced", "not_allowed_defect",
                                              "inactive_bypass"))
    clamp = not any(m.has_fault(f) for f in ("long_defect", "mcu_fault", "mode_changed", "firmware_replaced"))
    active = env.allowed and not rx.gas          # TSR-305: the inactive value only while the accelerator is pressed
    bus.accel = soc.accel and (active or not check) and not env.refused
    # A request above the clamp is refused (TSR-108); one that the bound lets through is excessive (BE-3.01: the
    # controller uses the same bound, DFI-08). A step to the bound passes: no jerk limit (BE-3.03, latent_in_model).
    bus.excess = bus.accel and ((soc.excess and not clamp) or soc.step or m.has_fault("limits_high"))
    bus.closing = bus.accel and soc.closing
    bus.stale = bus.accel and soc.stale


class TxPath(Function):
  """CAN TX path after the safety TX hook: message RAM, FDCAN core, transceiver."""

  container_m = _modes("txpath")
  flow_bus = Bus

  def static_behavior(self):
    if self.m.has_fault("corrupt"):
      self.bus.s.corrupt = True                  # BE-3.04: the frame on the bus is not the one the hook checked


class Relay(Function):
  """Harness relay: keeps the stock camera's ACC_CONTROL off the car side while the item drives."""

  container_m = _modes("relay")
  flow_env = Env
  flow_bus = Bus

  def static_behavior(self):
    self.env.s.relay_check = not self.m.has_fault("undetected")
    if self.m.has_fault("released") or self.m.has_fault("forwarded"):
      self.bus.s.stock = True
      self.env.s.t_stock_seen = _first(self.env.s.t_stock_seen, self.t.time)


class Pcm(Function):
  """PCM: executes the item's acceleration within its own bound (AOU-05R) and not on top of the driver's pedal, unless
  those fail (UE-3.05, UE-3.12). Also reads TE-03 from the flows."""

  container_m = _modes("pcm")
  flow_car = Car
  flow_soc = Soc
  flow_env = Env
  flow_bus = Bus
  flow_out = Out
  flow_drv = Drv

  def static_behavior(self):
    car, soc, env, bus, out, now = self.car.s, self.soc.s, self.env.s, self.bus.s, self.out.s, self.t.time
    if (bus.excess or bus.corrupt) and self.m.has_fault("no_bound"):
      out.t_excess = _first(out.t_excess, now)
    if bus.closing and self.drv.s.no_brake:
      out.t_closing = _first(out.t_closing, now)
    # Acceleration the driver does not want: while never engaged, or after the driver brakes or cancels. It counts
    # once it has lasted the SG-05 release time.
    unwanted = not car.item_on or car.t_action != NONE
    if bus.accel and unwanted:
      out.t_since = _first(out.t_since, max(now, car.t_action))
      if now - out.t_since >= RELEASE:
        out.t_unwanted = _first(out.t_unwanted, now)
    elif not bus.accel:
      out.t_since = NONE
    if bus.accel and car.gas and self.m.has_fault("adds_on_pedal"):
      out.t_gas = _first(out.t_gas, now)
    if bus.stale and now - FAULT_TICK >= BUDGET:
      out.t_stale_over = _first(out.t_stale_over, now)
    together = bus.stock and soc.engaged and not env.refused
    if together and now - FAULT_TICK >= BUDGET:
      out.t_overlap_over = _first(out.t_overlap_over, now)


class Sg03Param(Parameter):
  phase: str = DEFAULT_PHASE     # a row of events.yaml phases


class Sg03(FunctionArchitecture):
  """SG-03 chain: one function per element, flows between them."""

  container_p = Sg03Param
  default_sp = dict(end_time=float(END_TICK), dt=1.0)
  default_track = {"flows": {"out": "all", "soc": "all", "env": "all", "bus": "all"}}

  def init_architecture(self, **kwargs):
    ph = PHASES[self.p.phase]
    on = ph["engaged"]
    action = {"none": 0, "brake": 1, "cancel": 2, "gas": 3}[ph["driver"]]
    self.add_flow("car", Car, s={"item_on": on, "action": action, "engaged": on, "cruise": on})
    self.add_flow("rx", Rx, s={"cruise": on})
    self.add_flow("soc", Soc, s={"engaged": on})
    self.add_flow("env", Env, s={"allowed": on})
    for name, flow in (("bus", Bus), ("out", Out), ("drv", Drv)):
      self.add_flow(name, flow)
    self.add_fxn("driver", Driver, "car", "drv")
    self.add_fxn("rx", RxPath, "car", "rx")
    self.add_fxn("soc", SocFn, "rx", "soc")
    self.add_fxn("relay", Relay, "env", "bus")
    self.add_fxn("envelope", Envelope, "rx", "soc", "env", "bus")
    self.add_fxn("txpath", TxPath, "bus")
    self.add_fxn("pcm", Pcm, "car", "soc", "env", "bus", "out", "drv")


# ------------------------------------------------------------------------------------------------------- results

BRANCHES = {"t_excess": "excess", "t_closing": "closing", "t_unwanted": "unwanted", "t_gas": "gas",
            "t_stale_over": "stale", "t_overlap_over": "overlap"}


@dataclass(frozen=True)
class Outcome:
  events: tuple[str, ...]
  phase: str
  branch: str | None         # first TE-03 branch reached: excess, closing, unwanted, gas, stale or overlap
  t: float | None            # when, seconds after the injection
  top_event: bool

  def line(self) -> str:
    when = "-" if self.t is None else f"{self.t:.2f} s"
    return (f"{'+'.join(self.events) or 'nominal':32} {self.phase:8} {(self.branch or ''):9} {when:>7}  "
            f"{'TE-03' if self.top_event else 'ok'}")


def run_phase(events: tuple[str, ...] | list[str] = (), phase: str = DEFAULT_PHASE) -> Outcome:
  """Inject the failure modes of `events` together at FAULT_TICK in `phase` and read TE-03 from the history."""
  events = tuple(sorted(events))
  seq: dict[str, list[str]] = {}
  for e in events:
    fxn, mode = MODE_OF[e]
    seq.setdefault(fxn, []).append(mode)
  mdl = Sg03(p={"phase": phase})
  if seq:
    _, hist = propagate.sequence(mdl, faultseq={float(FAULT_TICK): seq}, include_nominal=False, showprogress=False)
  else:
    _, hist = propagate.nominal(mdl, showprogress=False)
  last = {k[k.index("flows."):]: v[-1] for k, v in hist.items() if "flows." in k}
  hits = sorted((float(last.get(f"flows.out.s.{f}", NONE)), b) for f, b in BRANCHES.items()
                if float(last.get(f"flows.out.s.{f}", NONE)) != NONE)
  if not hits:
    return Outcome(events, phase, None, None, False)
  t, branch = hits[0]
  return Outcome(events, phase, branch, round((t - FAULT_TICK) * TICK, 6), True)


def run(events: tuple[str, ...] | list[str] = ()) -> Outcome:
  """TE-03 in the first phase that reaches it, else the engaged phase's (clean) outcome."""
  first = None
  for ph in PHASES:
    o = run_phase(events, ph)
    if o.top_event:
      return o
    first = first or o
  return first


def main(argv: list[str]) -> int:
  if argv:
    for ph in PHASES:
      print(run_phase(argv, ph).line())
    return 0
  for ph in PHASES:
    print(run_phase((), ph).line())
  for e in MODE_OF:
    print(run((e,)).line())
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
