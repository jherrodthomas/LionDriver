#!/usr/bin/env python3
"""Back-to-back run: reference model SM-TOY-AUTH (sm_toy_auth_model.py) against the opendbc safety C (libsafety).

Each event (RX frame, safety tick, TX frame, safety-mode set) goes to both. The C gets real CAN frames, packed with
opendbc's CANPacker from the toyota_nodsu_pt DBC and fed through the libsafety_py harness of
opendbc_repo/opendbc/safety/tests; the model gets the decoded event. After every event `controls_allowed` (and, in
the reference build, the reported TX-rate flag) is compared. The first divergence ends a sequence and is recorded.

Event sources: directed scenarios (one or more per in-scope transition, plus WP-W-05 OI-1) and seeded random
sequences. Results are only what a run printed or wrote; nothing here is a verification verdict (README.md).

Needs the opendbc test environment (cffi, pycapnp, numpy) and a C compiler; libsafety is built at import, once per
variant, so each variant runs in its own process:

  opendbc_repo/.venv/bin/python assurance/05-software/reference-models/b2b_toy_auth.py --variant reference
  opendbc_repo/.venv/bin/python assurance/05-software/reference-models/b2b_toy_auth.py --all --json out.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
from sm_toy_auth_model import (DEVIATIONS, RX_SET_COMMON, RX_SET_REFERENCE, TX_RATE_ROWS, Rx, SetMode,  # noqa: E402
                               SmToyAuth, Tick, Tx, timeout_us)

import sm_toy_auth_model as M  # noqa: E402

# Seeded model faults for checking that the comparison detects a wrong model (README.md §5). Each is run with all
# deviations switched on, so that the known divergence classes do not mask it; it must produce at least one divergence.
MUTANTS = {
  "timeout_6_periods": lambda: setattr(M, "TIMEOUT_PERIODS", 6),
  "timeout_4_periods": lambda: setattr(M, "TIMEOUT_PERIODS", 4),
  "tx_revoke_after_4_rejected": lambda: setattr(M, "TX_REVOKE_REJECTED", 4),
  "tx_budget_plus_1": lambda: setattr(M, "tx_budget", lambda f, b, _o=M.tx_budget: _o(f, b) + 1),
  "cruise_main_tolerance_160ms": lambda: setattr(M, "CRUISE_MAIN_TOLERANCE_US", 160_000),
  "brake_while_moving_ignored": lambda: setattr(M.SmToyAuth, "_moving", lambda self: False),
  "engagement_not_gated": lambda: setattr(M.SmToyAuth, "_all_checks_ok", lambda self: True),
  "quality_flag_ignored": lambda: M.RX_SET_COMMON.__setitem__(0x0AA, (83, False, False)),
  "tx_arrival_limit_60ms": lambda: M.TX_ARRIVAL_US.__setitem__(0x2E4, 60_000),
}

IN_SCOPE = ["T1", "T2", "T3", "T4", "T5", "T7", "T8", "T10b", "T10c", "T11"]
REFERENCE_ONLY = {"T10b", "T10c", "T11"}
TOYOTA_PARAM = 73          # reference configuration (CD-01): EPS factor 73, no flags
TICK_US = 10_000           # 100 Hz safety task (SWSR-401a)
TX_DLC = {0x2E4: 5, 0x191: 8, 0x412: 8, 0x343: 8, 0x1D2: 8, 0x283: 7, 0x750: 8}  # whitelist lengths (CD-04)
MSG_NAME = {0x0AA: "WHEEL_SPEEDS", 0x260: "STEER_TORQUE_SENSOR", 0x1D2: "PCM_CRUISE", 0x226: "BRAKE_MODULE",
            0x262: "EPS_STATUS", 0x1D3: "PCM_CRUISE_2"}
ACTUATION = {0x2E4: 100, 0x343: 33}  # SoC actuation frames a running host sends (SWSR-408 supervises both)
WHEELS = ("FR", "FL", "RR", "RL")
STANDING = 6767            # raw wheel speed for 0 km/h (factor 0.01, offset -67.67)


# ------------------------------------------------------------------ event streams

class Feeder:
  """Holds the vehicle signal state and emits (time, event) pairs: periodic RX frames at their nominal rates, the
  100 Hz safety tick and, as a running host would, the SoC's actuation frames 0x2E4 (100 Hz) and 0x343 (33 Hz).
  Directed scenarios drive it explicitly; the random generator perturbs it and sends its own TX traffic."""

  def __init__(self, reference: bool):
    self.rx = dict(RX_SET_COMMON)
    if reference:
      self.rx.update(RX_SET_REFERENCE)
    self.now = 0
    self.next_due = {a: 0 for a in self.rx}
    self.next_tick = 0
    self.muted: set[int] = set()
    self.actuate = True                        # emit nominal SoC actuation traffic
    self.next_tx = {a: 0 for a in ACTUATION}
    self.tx_muted: set[int] = set()
    self.sig = {"CRUISE_ACTIVE": 0, "GAS_RELEASED": 1, "MAIN_ON": 1, "BRAKE_PRESSED": 0, "LKA_STATE": 5,
                **{f"WHEEL_SPEED_{w}_RAW": STANDING for w in WHEELS}, **{f"WHEEL_SPEED_{w}_FAULT": 0 for w in WHEELS}}
    self.events: list[tuple[int, object]] = []

  def frame(self, addr: int, **kw) -> Rx:
    return Rx(addr=addr, signals=dict(self.sig), **kw)

  def emit(self, ev, at: int | None = None) -> None:
    self.events.append((self.now if at is None else at, ev))

  def run(self, dur_us: int, period_scale: float = 1.0, rng: random.Random | None = None, jitter: float = 0.0) -> None:
    end = self.now + dur_us
    while True:
      tx_due = [self.next_tx[a] for a in ACTUATION] if self.actuate else []
      due = min([self.next_tick] + [self.next_due[a] for a in self.rx] + tx_due)
      if due > end:
        break
      self.now = due
      if self.next_tick == due:
        self.emit(Tick())
        self.next_tick = due + TICK_US
      for a, (freq, _, _) in self.rx.items():
        if self.next_due[a] == due:
          if a not in self.muted:
            self.emit(self.frame(a))
          period = int(1_000_000 / freq * period_scale)
          if rng is not None and jitter:
            period = max(1, int(period * (1 + rng.uniform(-jitter, jitter))))
          self.next_due[a] = due + period
      if self.actuate:
        for a, hz in ACTUATION.items():
          if self.next_tx[a] == due:
            if a not in self.tx_muted:
              self.emit(Tx(a, dlc=TX_DLC[a]))
            self.next_tx[a] = due + 1_000_000 // hz
    self.now = end

  def engage(self) -> None:
    """All messages flowing, cruise off then on (a rising edge)."""
    self.sig["CRUISE_ACTIVE"] = 0
    self.run(300_000)
    self.sig["CRUISE_ACTIVE"] = 1
    self.emit(self.frame(0x1D2))
    self.run(50_000)


def directed(reference: bool) -> dict[str, list]:
  """Directed scenarios. Each returns an event list; expectations are not asserted here: model and C are compared."""
  S: dict[str, list] = {}

  def new() -> Feeder:
    return Feeder(reference)

  f = new(); f.engage(); f.run(500_000)
  S["D01 T1 engage, all RX checks passing"] = f.events

  for a in sorted(f.rx):
    f = new(); f.muted = {a}; f.engage()
    S[f"D02 T8 rising edge while {a:#x} never received"] = f.events

  f = new(); f.run(300_000); f.emit(f.frame(0x260, checksum_ok=False)); f.now += 1_000
  f.sig["CRUISE_ACTIVE"] = 1; f.emit(f.frame(0x1D2)); f.run(100_000)
  S["D03 T8 rising edge after a bad 0x260 checksum"] = f.events

  f = new(); f.engage(); f.sig["CRUISE_ACTIVE"] = 0; f.emit(f.frame(0x1D2)); f.run(100_000)
  S["D04 T2 cruise off"] = f.events

  f = new(); f.engage(); f.sig["BRAKE_PRESSED"] = 1; f.emit(f.frame(0x226)); f.run(100_000)
  S["D05a T3 brake rising, standing"] = f.events

  f = new(); f.sig["BRAKE_PRESSED"] = 1; f.engage(); f.run(100_000)
  f.sig["WHEEL_SPEED_FL_RAW"] = STANDING + 500; f.emit(f.frame(0x0AA)); f.run(100_000)
  S["D05b T3 engaged with brake held at standstill, then moving"] = f.events

  f = new(); f.sig["BRAKE_PRESSED"] = 1; f.engage(); f.run(100_000)
  f.sig["WHEEL_SPEED_FR_RAW"] = STANDING + 1; f.sig["WHEEL_SPEED_FL_RAW"] = STANDING - 1
  f.emit(f.frame(0x0AA)); f.run(100_000)
  S["D06 T3 brake held, two wheels non-zero with opposite sign (SWSR-302 'any wheel')"] = f.events

  for a, (_, cks, _) in sorted(f.rx.items()):
    if cks:
      f = new(); f.engage(); f.emit(f.frame(a, checksum_ok=False)); f.run(100_000)
      S[f"D07 T4 bad checksum on {a:#x}"] = f.events

  for a in sorted(f.rx):
    f = new(); f.engage(); f.emit(f.frame(a, dlc=7)); f.now += 1_000; f.emit(Tick())
    S[f"D08 T4 wrong DLC (7) on {a:#x} (SWSR-402 length)"] = f.events

  for a, (freq, _, _) in sorted(f.rx.items()):
    for delta, tag in ((0, "at"), (1, "1 us past")):
      f = new(); f.engage(); f.muted = {a}
      last = max(t for t, ev in f.events if isinstance(ev, Rx) and ev.addr == a)
      f.run(last + timeout_us(freq) + delta - f.now - 1)
      f.now = last + timeout_us(freq) + delta
      f.emit(Tick())
      S[f"D09 T5 tick {tag} the {a:#x} timeout ({timeout_us(freq)} us)"] = f.events

  f = new(); f.engage(); f.emit(SetMode()); f.run(300_000)
  S["D10 T7 safety mode set while allowed"] = f.events

  # Ported from the retired models/b2b harness (BB-08a, BB-08b, BB-01c). D19: a mode set while CRUISE_ACTIVE is held 1
  # (B2B-06 / BB-C-01). After the reset the held 1 is a new edge (MA-01, SWSR-311); whether authority comes back
  # depends on every RX check being received again before the next 0x1D2.
  f = new(); f.engage(); f.run(100_000); f.emit(SetMode()); f.muted = {0x226}
  f.run(f.next_due[0x1D2] - f.now + 1_000); f.muted = set(); f.run(200_000)
  S["D19a T7 mode set, cruise held; 0x226 arrives after the next 0x1D2: no regrant"] = f.events

  f = new(); f.engage(); f.run(100_000); f.emit(SetMode())
  for a in sorted(f.rx):
    if a != 0x1D2:
      f.now += 100; f.emit(f.frame(a))
  f.run(200_000)
  S["D19b T7 mode set, cruise held; every RX check received before the next 0x1D2: authority granted again"] = f.events

  f = new(); f.sig["CRUISE_ACTIVE"] = 1; f.run(300_000)
  f.sig["CRUISE_ACTIVE"] = 0; f.emit(f.frame(0x1D2)); f.run(100_000)
  f.sig["CRUISE_ACTIVE"] = 1; f.emit(f.frame(0x1D2)); f.run(100_000)
  S["D20 T8 then T1: cruise active from the start (no edge), then off and on again"] = f.events

  if reference:
    for extra, tag in ((0, "exactly 150 ms"), (1, "150 ms + 1 us")):
      f = new(); f.engage()
      f.sig["MAIN_ON"] = 0; f.emit(f.frame(0x1D3)); start = f.now
      f.run(start + 150_000 + extra - f.now - 1)
      f.now = start + 150_000 + extra
      f.emit(f.frame(0x1D3))
      S[f"D11 T10c main off with cruise on, evaluated at {tag}"] = f.events

    f = new(); f.sig["MAIN_ON"] = 0; f.engage()
    S["D12 T10c cruise rising edge while main off"] = f.events

    for mult in (2, 10):
      f = new(); f.engage(); f.tx_muted = {0x2E4}   # the flood replaces the nominal 0x2E4 traffic
      for k in range(60 * mult // 2):
        f.emit(Tx(0x2E4, dlc=5), at=f.now + k * (10_000 // mult))
      f.run(300_000)
      S[f"D13 T11 0x2E4 flood at {mult}x while allowed"] = f.events

    f = new(); f.engage(); f.tx_muted = {0x2E4}
    for k in range(60):
      f.emit(Tx(0x2E4, dlc=5), at=f.now + k * 5_000)
    f.run(300_000)
    f.sig["CRUISE_ACTIVE"] = 0; f.run(200_000); f.sig["CRUISE_ACTIVE"] = 1; f.emit(f.frame(0x1D2)); f.run(100_000)
    S["D13c T11 revoked, then a new cruise edge (F-34)"] = f.events

    for a, limit in sorted(M.TX_ARRIVAL_US.items()):
      f = new(); f.engage(); f.run(100_000); f.tx_muted = {a}; f.run(limit + 100_000)
      S[f"D18 T10b {a:#x} stops while allowed (limit {limit // 1000} ms)"] = f.events

  f = new(); f.engage(); f.sig["BRAKE_PRESSED"] = 1; f.emit(f.frame(0x226, dlc=7)); f.now += 1_000
  f.emit(f.frame(0x260)); f.run(100_000)
  S["D14 OI-1 brake pressed in a 0x226 frame that fails validation"] = f.events

  f = new(); f.engage(); f.sig["WHEEL_SPEED_RL_FAULT"] = 1; f.emit(f.frame(0x0AA)); f.run(100_000)
  S["D15 T4 wheel-speed fault bit (quality)"] = f.events

  f = new(); f.engage()
  f.emit(Rx(0x1D2, bus=2, signals={**f.sig, "CRUISE_ACTIVE": 0})); f.now += 100
  f.emit(Rx(0x226, bus=2, signals={**f.sig, "BRAKE_PRESSED": 1})); f.run(100_000)
  S["D16 cruise off and brake on bus 2 (not the car bus): no effect"] = f.events

  f = new(); f.engage(); f.sig["GAS_RELEASED"] = 0; f.sig["LKA_STATE"] = 9; f.run(300_000)
  S["D17 gas pressed and EPS fault while allowed: non-revoking"] = f.events
  return S


def random_sequence(reference: bool, seed: int, n_events: int) -> list:
  rng = random.Random(seed)
  f = Feeder(reference)
  f.sig["MAIN_ON"] = int(rng.random() < 0.9)
  dropout: dict[int, int] = {}
  flood: tuple[int, float, int] | None = None   # (addr, multiplier, until)
  f.actuate = False                            # TX traffic is generated below, with floods and dropouts
  next_tx = {0x2E4: 0, 0x343: 0, 0x412: 0}
  tx_gap: dict[int, int] = {}                  # actuation dropouts (T10b): addr -> until
  while len(f.events) < n_events:
    # one 10 ms slice at a time, frames at nominal rates with jitter and occasional long gaps
    f.muted = {a for a, until in dropout.items() if until > f.now}
    f.run(TICK_US, rng=rng, jitter=0.25)
    for a in f.rx:
      if a not in dropout or dropout[a] <= f.now:
        if rng.random() < 0.002:
          dropout[a] = f.now + rng.choice([20_000, 60_000, 100_000, 150_000, 160_000, 250_000, 1_000_000])
    # signal changes
    r = rng.random()
    if r < 0.02:
      f.sig["CRUISE_ACTIVE"] ^= 1
    elif r < 0.03:
      f.sig["BRAKE_PRESSED"] ^= 1
    elif r < 0.035:
      f.sig["MAIN_ON"] ^= 1
    elif r < 0.05:
      f.sig["GAS_RELEASED"] ^= 1
    elif r < 0.06:
      kind = rng.choice(["stand", "stand", "move", "mixed", "creep"])
      for w in WHEELS:
        f.sig[f"WHEEL_SPEED_{w}_RAW"] = {"stand": STANDING, "move": STANDING + rng.randint(100, 3000),
                                         "creep": STANDING + rng.choice([0, 1]),
                                         "mixed": STANDING + rng.choice([-1, 1])}[kind]
    elif r < 0.065:
      f.sig["LKA_STATE"] = rng.choice([0, 3, 5, 9, 11, 17, 21, 25])
    # corrupted or unusual frames
    if rng.random() < 0.01:
      a = rng.choice(sorted(f.rx))
      kind = rng.choice(["checksum", "dlc", "fault", "bus2"])
      if kind == "checksum" and f.rx[a][1]:
        f.emit(f.frame(a, checksum_ok=False))
      elif kind == "dlc":
        f.emit(f.frame(a, dlc=rng.choice([0, 6, 7])))
      elif kind == "fault" and a == 0x0AA:
        sig = dict(f.sig); sig[f"WHEEL_SPEED_{rng.choice(WHEELS)}_FAULT"] = 1
        f.emit(Rx(0x0AA, signals=sig))
      elif kind == "bus2":
        f.emit(Rx(a, bus=2, signals={**f.sig, "CRUISE_ACTIVE": rng.randint(0, 1), "BRAKE_PRESSED": rng.randint(0, 1)}))
    if rng.random() < 0.0005:
      f.emit(SetMode())
    # SoC TX: nominal 0x2E4 / 0x343 / 0x412 traffic, sometimes a flood on any rate-checked ID
    if flood is None and rng.random() < 0.003:
      flood = (rng.choice(sorted(TX_RATE_ROWS)), rng.choice([0.5, 1.0, 1.5, 2.0, 4.0, 10.0]),
               f.now + rng.choice([100_000, 300_000, 1_000_000]))
    if rng.random() < 0.004:
      a = rng.choice(sorted(ACTUATION))
      tx_gap[a] = f.now + rng.choice([20_000, 40_000, 50_000, 60_000, 90_000, 100_000, 110_000, 200_000])
    for a, hz in ((0x2E4, 100), (0x343, 33), (0x412, 5)):
      while next_tx[a] <= f.now:
        if tx_gap.get(a, 0) <= next_tx[a]:
          f.emit(Tx(a, dlc=TX_DLC[a]), at=next_tx[a])
        next_tx[a] += int(1_000_000 / hz)
    if flood is not None:
      a, mult, until = flood
      freq = TX_RATE_ROWS[a][0]
      n = max(1, round(freq * mult * TICK_US / 1_000_000 + rng.random() - 0.5))
      for k in range(n):
        f.emit(Tx(a, dlc=TX_DLC[a]), at=f.now - TICK_US + k * TICK_US // n)
      if f.now >= until:
        flood = None
  f.events.sort(key=lambda te: te[0])
  return f.events[:n_events]


# ------------------------------------------------------------------ C side

class CSide:
  def __init__(self):
    sys.path.insert(0, str(REPO / "opendbc_repo"))
    from opendbc.can import CANPacker
    from opendbc.car.structs import CarParams
    from opendbc.safety.tests.libsafety import libsafety_py
    self.lp = libsafety_py
    self.s = libsafety_py.libsafety
    self.packer = CANPacker("toyota_nodsu_pt_generated")
    self.mode = CarParams.SafetyModel.toyota

  def start(self) -> None:
    assert self.s.set_safety_hooks(self.mode, TOYOTA_PARAM) == 0
    self.s.init_tests()

  def apply(self, t: int, ev) -> None:
    self.s.set_timer(t)
    if isinstance(ev, Tick):
      self.s.safety_tick()
    elif isinstance(ev, SetMode):
      self.s.set_safety_hooks(self.mode, TOYOTA_PARAM)
    elif isinstance(ev, Tx):
      self.s.safety_tx_hook(self.lp.make_CANPacket(ev.addr, ev.bus, b"\x00" * ev.dlc))
    else:
      self.s.safety_rx_hook(self.lp.make_CANPacket(ev.addr, ev.bus, self.encode(ev)))

  def encode(self, ev: Rx) -> bytes:
    s = ev.signals
    name = MSG_NAME[ev.addr]
    values = {
      "PCM_CRUISE": {"CRUISE_ACTIVE": s["CRUISE_ACTIVE"], "GAS_RELEASED": s["GAS_RELEASED"]},
      "PCM_CRUISE_2": {"MAIN_ON": s["MAIN_ON"]},
      "BRAKE_MODULE": {"BRAKE_PRESSED": s["BRAKE_PRESSED"]},
      "EPS_STATUS": {"LKA_STATE": s["LKA_STATE"]},
      "STEER_TORQUE_SENSOR": {},
      "WHEEL_SPEEDS": {**{f"WHEEL_SPEED_{w}": s[f"WHEEL_SPEED_{w}_RAW"] * 0.01 - 67.67 for w in WHEELS},
                       **{f"WHEEL_SPEED_{w}_FAULT": s[f"WHEEL_SPEED_{w}_FAULT"] for w in WHEELS}},
    }[name]
    _, dat, _ = self.packer.make_can_msg(name, 0, values)
    dat = bytearray(dat)
    if not ev.checksum_ok:
      dat[-1] ^= 0x01            # Toyota checksum is the last byte (DBC CHECKSUM signal)
    return bytes(dat[:ev.dlc])

  def allowed(self) -> bool:
    return bool(self.s.get_controls_allowed())

  def tx_rate_flag(self) -> bool:
    return bool(self.s.get_safety_tx_rate_exceeded())


# ------------------------------------------------------------------ comparison

def describe(ev) -> str:
  if isinstance(ev, Rx):
    extra = []
    if ev.bus != 0:
      extra.append(f"bus {ev.bus}")
    if ev.dlc != 8:
      extra.append(f"dlc {ev.dlc}")
    if not ev.checksum_ok:
      extra.append("bad checksum")
    keys = {0x1D2: ["CRUISE_ACTIVE"], 0x1D3: ["MAIN_ON"], 0x226: ["BRAKE_PRESSED"],
            0x0AA: [f"WHEEL_SPEED_{w}_RAW" for w in WHEELS] + [f"WHEEL_SPEED_{w}_FAULT" for w in WHEELS]}
    sig = {k.replace("WHEEL_SPEED_", "").replace("_RAW", ""): (v - STANDING if k.endswith("_RAW") else v)
           for k, v in ev.signals.items() if k in keys.get(ev.addr, []) and (v or k.endswith("_RAW"))}
    return f"RX {ev.addr:#x}" + (f" ({', '.join(extra)})" if extra else "") + (f" {sig}" if sig else "")
  if isinstance(ev, Tx):
    return f"TX {ev.addr:#x}"
  return type(ev).__name__


def run_sequence(c: CSide, reference: bool, deviations: dict, events: list, coverage: dict) -> dict | None:
  m = SmToyAuth(reference, deviations)
  c.start()
  for i, (t, ev) in enumerate(events):
    m.now = t
    fired = m.step(ev)
    c.apply(t, ev)
    for tid in fired:
      coverage[tid] = coverage.get(tid, 0) + 1
    ca, cf = c.allowed(), (c.tx_rate_flag() if reference else False)
    if ca != m.allowed or cf != m.tx_rate_exceeded:
      lo = max(0, i - 6)
      return {"step": i, "t_us": t, "event": describe(ev), "model_fired": fired,
              "model_allowed": m.allowed, "c_allowed": ca, "model_tx_flag": m.tx_rate_exceeded, "c_tx_flag": cf,
              "context": [f"{tt} us  {describe(e)}" for tt, e in events[lo:i + 1]],
              "signature": f"{describe(ev).split(' {')[0]} | model fired {fired or '-'} | "
                           f"model {int(m.allowed)}/{int(m.tx_rate_exceeded)} vs C {int(ca)}/{int(cf)} "
                           f"(allowed/tx flag)"}
  return None


def run_variant(variant: str, deviations: dict, seeds: int, n_events: int) -> dict:
  reference = variant == "reference"
  c = CSide()
  coverage: dict[str, int] = {}
  out = {"variant": variant, "deviations": [k for k, v in deviations.items() if v], "directed": {}, "random": {},
         "events": 0}
  for name, events in directed(reference).items():
    events.sort(key=lambda te: te[0])
    out["events"] += len(events)
    d = run_sequence(c, reference, deviations, events, coverage)
    out["directed"][name] = d or "agree"
  diverged = []
  for seed in range(seeds):
    events = random_sequence(reference, seed, n_events)
    out["events"] += len(events)
    d = run_sequence(c, reference, deviations, events, coverage)
    if d:
      d["seed"] = seed
      diverged.append(d)
  classes: dict[str, dict] = {}
  for d in diverged:
    k = d["signature"]
    if k not in classes or d["step"] < classes[k]["example"]["step"]:
      classes[k] = {"count": classes.get(k, {}).get("count", 0), "example": d}
    classes[k]["count"] += 1
  out["random"] = {"sequences": seeds, "events_per_sequence": n_events, "diverged": len(diverged),
                   "classes": classes}
  out["coverage"] = {t: coverage.get(t, 0) for t in IN_SCOPE if reference or t not in REFERENCE_ONLY}
  return out


def environment() -> dict:
  def git(*a, cwd=REPO):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()
  cc = subprocess.run(["cc", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
  return {"superproject": git("rev-parse", "--short", "HEAD"),
          "opendbc": git("rev-parse", "--short", "HEAD", cwd=REPO / "opendbc_repo"),
          "panda_pinned": git("rev-parse", "--short", "HEAD:panda"),  # not used by libsafety; may not be checked out
          "python": sys.version.split()[0], "cc": cc,
          "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "sm_toy_auth_model.py", HERE / "b2b_toy_auth.py")}}


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--variant", choices=["reference", "upstream"])
  ap.add_argument("--all", action="store_true", help="both variants, literal model and each deviation (subprocesses)")
  ap.add_argument("--deviation", action="append", default=[], choices=sorted(DEVIATIONS) + ["all"])
  ap.add_argument("--mutant", choices=sorted(MUTANTS))
  ap.add_argument("--seeds", type=int, default=100)
  ap.add_argument("--events", type=int, default=3000)
  ap.add_argument("--json", type=Path)
  ap.add_argument("--gate", action="store_true",
                  help="with --all: exit 1 unless the all-deviations runs agree everywhere, every deviation is still "
                       "needed and every mutant is detected (CI)")
  a = ap.parse_args()

  if a.all:
    runs = []
    names = sorted(DEVIATIONS)
    dev_sets = [()] + [(d,) for d in names] + [tuple(x for x in names if x != d) for d in names] + [tuple(names)]
    dev_sets = list(dict.fromkeys(dev_sets))
    for variant in ("reference", "upstream"):
      for dev in dev_sets:
        cmd = [sys.executable, __file__, "--variant", variant, "--seeds", str(a.seeds), "--events", str(a.events)]
        for d in dev:
          cmd += ["--deviation", d]
        env = dict(os.environ, LIONDRIVER_REFERENCE="1" if variant == "reference" else "0")
        p = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if p.returncode != 0:
          sys.stderr.write(p.stderr)
          return 2
        runs.append(json.loads(p.stdout))
        r = runs[-1]
        bad = [k for k, v in r["directed"].items() if v != "agree"]
        print(f"{variant:9} deviations={','.join(r['deviations']) or 'none':58} events={r['events']:7} "
              f"directed diverged={len(bad):2}/{len(r['directed'])} random diverged={r['random']['diverged']:3}/"
              f"{a.seeds} classes={len(r['random']['classes'])}", file=sys.stderr)
    mutants = {}
    for mutant in sorted(MUTANTS):
      cmd = [sys.executable, __file__, "--variant", "reference", "--deviation", "all", "--mutant", mutant,
             "--seeds", str(max(1, a.seeds // 5)), "--events", str(a.events)]
      p = subprocess.run(cmd, env=dict(os.environ, LIONDRIVER_REFERENCE="1"), capture_output=True, text=True)
      if p.returncode != 0:
        sys.stderr.write(p.stderr)
        return 2
      r = json.loads(p.stdout)
      directed_hits = sorted(k for k, v in r["directed"].items() if v != "agree")
      mutants[mutant] = {"directed_diverged": directed_hits, "random_diverged": r["random"]["diverged"],
                         "random_sequences": r["random"]["sequences"],
                         "detected": bool(directed_hits or r["random"]["diverged"])}
      print(f"mutant {mutant:30} detected={mutants[mutant]['detected']} directed={len(directed_hits)} "
            f"random={r['random']['diverged']}/{r['random']['sequences']}", file=sys.stderr)
    gate = []
    for r in runs:
      if set(r["deviations"]) == set(names):
        n = sum(v != "agree" for v in r["directed"].values()) + r["random"]["diverged"]
        if n:
          gate.append(f"{r['variant']}: {n} divergences with all deviations on (a new difference between model and C)")
    for d in names:
      rest = set(names) - {d}
      if not any(set(r["deviations"]) == rest and (r["random"]["diverged"] or
                                                   any(v != "agree" for v in r["directed"].values())) for r in runs):
        gate.append(f"deviation {d} is no longer needed in either build (code or specification changed): remove it")
    gate += [f"mutant {m} not detected" for m, v in mutants.items() if not v["detected"]]
    for g in gate:
      print(f"GATE FAIL: {g}", file=sys.stderr)
    print("GATE " + ("FAIL" if gate else "OK"), file=sys.stderr)
    result = {"environment": environment(), "runs": runs, "mutants": mutants, "gate": gate}
    text = json.dumps(result, indent=1)
    if a.json:
      a.json.write_text(text + "\n")
    else:
      print(text)
    return 1 if (a.gate and gate) else 0

  if a.variant is None:
    ap.error("--variant or --all is required")
  want = "1" if a.variant == "reference" else "0"
  if os.environ.get("LIONDRIVER_REFERENCE", "0") != want:
    os.environ["LIONDRIVER_REFERENCE"] = want
    os.execv(sys.executable, [sys.executable, *sys.argv])
  if a.mutant:
    MUTANTS[a.mutant]()
  devs = {k: ("all" in a.deviation or k in a.deviation) for k in DEVIATIONS}
  print(json.dumps(run_variant(a.variant, devs, a.seeds, a.events), indent=1))
  return 0


if __name__ == "__main__":
  sys.exit(main())
