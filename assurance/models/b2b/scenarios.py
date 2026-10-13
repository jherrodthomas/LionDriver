"""Stimulus scenarios BB-01..BB-11 for the SM-TOY-AUTH back-to-back test.

A scenario is a timeline of abstract events on a 1 ms grid: the car's RX messages at their nominal rates, the host's
TX frames at its control rates, and the 100 Hz safety task. Each scenario changes signal values, stops or corrupts
messages, or injects frames at chosen times. The same event list drives the C code (encoded with the DBC) and the
model (as values).

Drafting origin: ai-assisted (Claude), not reviewed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# name: (period ms, phase ms, build). Nominal rates of the reference car; phases keep messages in a fixed order
RX_SCHEDULE = {
  "WHEEL_SPEEDS": (12, 1, "all"),
  "STEER_TORQUE_SENSOR": (20, 3, "all"),
  "EPS_STATUS": (40, 5, "all"),
  "PCM_CRUISE_2": (30, 7, "all"),
  "PCM_CRUISE": (30, 9, "all"),
  "BRAKE_MODULE": (25, 2, "all"),
}
TX_SCHEDULE = {"STEERING_LKA": (10, 4), "ACC_CONTROL": (30, 6)}
TICK_MS = 10
ENGAGE_MS = 300  # all RX checks have been received by then

DEFAULTS = {"CRUISE_ACTIVE": 0, "GAS_RELEASED": 1, "MAIN_ON": 1, "BRAKE_PRESSED": 0, "speed": 0.0,
            "wheel_fault": 0, "STEER_TORQUE_EPS": 0, "STEER_TORQUE_DRIVER": 0, "LKA_STATE": 5}


@dataclass
class Event:
  t_ms: int
  kind: str          # rx, tx, tick, mode
  name: str = ""
  values: dict = field(default_factory=dict)
  corrupt: bool = False
  content_ok: bool = True


@dataclass
class Scenario:
  id: str
  transitions: str
  title: str
  duration_ms: int
  changes: list = field(default_factory=list)   # (t_ms, signal, value)
  stops: list = field(default_factory=list)     # (name, t0, t1): message not sent in [t0, t1)
  corrupts: list = field(default_factory=list)  # (name, t0, t1): sent corrupted in [t0, t1)
  inject: list = field(default_factory=list)    # extra Event objects
  rate: list = field(default_factory=list)      # (name, t0, t1, period_ms): TX period override

  def set(self, t, **kw):
    self.changes += [(t, k, v) for k, v in kw.items()]
    return self

  def events(self) -> list[Event]:
    sig = dict(DEFAULTS)
    changes = sorted(self.changes)
    out: list[Event] = []
    for t in range(self.duration_ms):
      while changes and changes[0][0] <= t:
        _, k, v = changes.pop(0)
        sig[k] = v
      for name, (period, phase, _) in RX_SCHEDULE.items():
        if t % period == phase and not any(n == name and a <= t < b for n, a, b in self.stops):
          bad = any(n == name and a <= t < b for n, a, b in self.corrupts)
          out.append(Event(t, "rx", name, dict(sig), corrupt=bad))
      for name, (period, phase) in TX_SCHEDULE.items():
        for n, a, b, p in self.rate:
          if n == name and a <= t < b:
            period, phase = p, phase % p
        if t % period == phase and not any(n == name and a <= t < b for n, a, b in self.stops):
          out.append(Event(t, "tx", name, dict(sig)))
      out += [e for e in self.inject if e.t_ms == t]
      if t % TICK_MS == 0:
        out.append(Event(t, "tick"))
    return out


def engaged(sid, transitions, title, duration_ms=1500):
  return Scenario(sid, transitions, title, duration_ms).set(ENGAGE_MS, CRUISE_ACTIVE=1)


def scenarios() -> list[Scenario]:
  s = []
  s.append(engaged("BB-01a", "T1", "Cruise rising edge with every RX check valid", 600))
  b = engaged("BB-01b", "T8", "Cruise rising edge while one RX check is lagging (EPS_STATUS stopped)", 800)
  b.stops.append(("EPS_STATUS", 100, 800))
  s.append(b)
  b = engaged("BB-01c", "T8, T1", "Cruise already active at start: held, no edge; then off and on again", 900)
  b.set(0, CRUISE_ACTIVE=1).set(500, CRUISE_ACTIVE=0).set(650, CRUISE_ACTIVE=1)
  s.append(b)
  s.append(engaged("BB-02", "T2", "Cruise off while engaged", 800).set(600, CRUISE_ACTIVE=0))
  b = engaged("BB-03", "T3", "Brake: rising edge at standstill; held at standstill then moving", 1400)
  b.set(500, BRAKE_PRESSED=1).set(700, CRUISE_ACTIVE=0).set(800, CRUISE_ACTIVE=1).set(1000, speed=1.0)
  s.append(b)
  b = engaged("BB-04a", "T4", "STEER_TORQUE_SENSOR checksum wrong while engaged", 900)
  b.corrupts.append(("STEER_TORQUE_SENSOR", 600, 640))
  s.append(b)
  b = engaged("BB-04b", "T4", "Wheel-speed fault flag (quality) while engaged", 900)
  b.set(600, wheel_fault=1).set(640, wheel_fault=0)
  s.append(b)
  for name in RX_SCHEDULE:
    b = engaged(f"BB-05-{name}", "T5", f"{name} stops while engaged", 1000)
    b.stops.append((name, 600, 1000))
    s.append(b)
  b = engaged("BB-06a", "T10c", "MAIN_ON goes off while cruise is active", 1000)
  b.set(600, MAIN_ON=0)
  s.append(b)
  b = Scenario("BB-06b", "T10c, T1", "Cruise goes active while MAIN_ON is off", 800)
  b.set(0, MAIN_ON=0).set(ENGAGE_MS, CRUISE_ACTIVE=1)
  s.append(b)
  b = engaged("BB-07", "T11", "STEERING_LKA flood at 2x (5 ms period) while engaged", 1000)
  b.rate.append(("STEERING_LKA", 600, 1000, 5))
  s.append(b)
  # after a mode set, set_safety_hooks clears the RX checks and the CRUISE_ACTIVE edge memory (SWSR-311); whether
  # authority comes back depends on whether every RX check is received again before the next PCM_CRUISE frame
  b = engaged("BB-08a", "T7", "Safety mode set while engaged, cruise held; BRAKE_MODULE arrives after the next PCM_CRUISE", 900)
  b.inject.append(Event(600, "mode"))
  b.stops.append(("BRAKE_MODULE", 600, 615))
  s.append(b)
  b = engaged("BB-08b", "T7, T1", "Safety mode set while engaged, cruise held; every RX check arrives before the next PCM_CRUISE", 900)
  b.inject.append(Event(600, "mode"))
  s.append(b)
  b = engaged("BB-09", "T9", "STEERING_LKA torque step 0 -> 1500 (rate limit) while engaged", 900)
  b.inject.append(Event(605, "tx", "STEERING_LKA", dict(DEFAULTS, STEER_TORQUE_CMD=1500, STEER_REQUEST=1),
                        content_ok=False))
  s.append(b)
  b = engaged("BB-10a", "T10b", "Host stops STEERING_LKA while engaged", 1000)
  b.stops.append(("STEERING_LKA", 600, 1000))
  s.append(b)
  b = engaged("BB-10b", "T10b", "Host stops ACC_CONTROL while engaged", 1000)
  b.stops.append(("ACC_CONTROL", 600, 1000))
  s.append(b)
  b = engaged("BB-11", "non_revoking", "EPS fault (LKA_STATE 25) and gas pressed while engaged: authority kept", 1000)
  b.set(600, LKA_STATE=25).set(700, LKA_STATE=5).set(800, GAS_RELEASED=0)
  s.append(b)
  return s
