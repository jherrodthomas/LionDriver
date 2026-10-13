"""Executable reference model of the Toyota authority state machine (SM-TOY-AUTH).

Written from the record assurance/05-software/state-machines/sm-toy-auth.yaml, not from the C code (modelling plan
MD-03): where the record and the code differ, the model follows the record, and the back-to-back run shows the
difference. Where the record is silent the model needs an assumption; each one is listed in ASSUMPTIONS and in the
run report, so a reviewer can accept or reject it.

The model consumes abstract stimulus events (message name, signal values, flags), never CAN bytes, so it shares no
decoding with the C code. The timing figures it uses come either from the record (guard text) or, where the record
gives none, from the configuration in opendbc modes/toyota.h; the latter are listed in CODE_CONSTANTS and
run_b2b.py checks them against the source at the pinned commit before every run.

Drafting origin: ai-assisted (Claude), not reviewed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

NOT_ALLOWED, ALLOWED = "NOT_ALLOWED", "ALLOWED"

# Transitions this model executes, and the ones it cannot execute at the libsafety boundary, with the reason.
# run_b2b.py fails if the record holds a transition that is in neither list.
EXECUTED = ["T1", "T8", "T2", "T3", "T4", "T5", "T7", "T9", "T10b", "T10c", "T11"]
NOT_EXECUTED = {
  "T6": "panda main.c heartbeat counter; not part of libsafety (needs a panda-level harness)",
  "T10a": "panda heartbeat_monitor_tick; not part of libsafety",
  "T10d": "platform faults are raised in panda, not in libsafety",
  "T10e": "record gives no event definition for a Toyota LKA driver override",
  "T12": "record leaves T_ovr and t_ovr undefined, so the guard cannot be evaluated",
  "T13": "SPI errors are a panda driver event; not part of libsafety",
  "T14": "CAN bus-off is a panda driver event; not part of libsafety",
  "T15": "forwarding supervision is panda-level; not part of libsafety",
}

# From the record (guard text of the cited transition)
RX_TIMEOUT_PERIODS = 5             # T5 "lagging (5 periods)"
RX_MIN_FREQUENCY_HZ = 10           # T5 "below 10 Hz"
CRUISE_MAIN_TOLERANCE_US = 150000  # T10c "lasts > 150 ms" (and "at once if first seen on 0x1D2")
TX_ARRIVAL_TIMEOUT_US = {"STEERING_LKA": 50000, "ACC_CONTROL": 100000}  # T10b "0x2E4/0x343 for 50/100 ms"
TX_RATE_REVOKE_REJECTED = 3        # T11 "3 rejected frames in one 125 ms half-window"
TX_RATE_HALF_WINDOW_US = 125000

# From the configuration in opendbc modes/toyota.h (the record does not list them); checked by run_b2b.py.
# RX checks of the LKA, non-SecOC, non-alt-brake configuration (CFG-001): name -> (address, frequency Hz, build)
CODE_CONSTANTS = {
  "rx_checks": {
    "WHEEL_SPEEDS": (0xAA, 83, "all"),
    "STEER_TORQUE_SENSOR": (0x260, 50, "all"),
    "EPS_STATUS": (0x262, 25, "reference"),
    "PCM_CRUISE_2": (0x1D3, 33, "reference"),
    "PCM_CRUISE": (0x1D2, 33, "all"),
    "BRAKE_MODULE": (0x226, 40, "all"),
  },
  # TX rate rows (DN-01): name -> (address, nominal Hz, burst); budget = ceil(f * 0.3) + 1 + burst per 250 ms
  "tx_rate": {
    "STEERING_LKA": (0x2E4, 100, 5),
    "ACC_CONTROL": (0x343, 33, 3),
  },
}

ASSUMPTIONS = [
  ("A-1", "T1 guard 'rx_checks_allow_engagement()' read as: every RX check of the build has been received, its last " +
          "frame was valid, and it is not lagging (T5 threshold)"),
  ("A-2", "T3 and the RX-check bookkeeping run on every received frame; the message's own effect (e.g. T1 on " +
          "PCM_CRUISE) is applied before T3 within the same frame"),
  ("A-3", "T5 lag threshold per message = 5 x floor(1e6 / frequency) us, compared with '>' at each safety task"),
  ("A-4", "T10b supervision starts at the moment authority is granted (the record gives no other reference point)"),
  ("A-5", "T11 counts rate-rejected frames per ID in the current half-window; the budget follows DN-01"),
  ("A-6", "T7 clears authority only. T1 needs a real 0->1 change of CRUISE_ACTIVE (SWSR-301 'rising edge of " +
          "CRUISE_ACTIVE'); the model does not treat the edge-state reset of SWSR-311 as creating a new edge"),
]


@dataclass
class RxCheck:
  period_us: int
  seen: bool = False
  valid: bool = False
  last_us: int = 0


@dataclass
class RateWindow:
  ts_last: int = 0
  msgs: int = 0
  msgs_prev: int = 0
  rejected: int = 0


@dataclass
class ToyAuthModel:
  build: str  # "reference" or "upstream"
  state: str = NOT_ALLOWED
  fired: list = field(default_factory=list)  # (t_us, transition id) of every transition that changed or held state

  def __post_init__(self):
    self.checks = {n: RxCheck(RX_TIMEOUT_PERIODS * (1000000 // f)) for n, (_, f, b) in CODE_CONSTANTS["rx_checks"].items()
               if b == "all" or (b == "reference" and self.build == "reference")}
    self.freq = {n: f for n, (_, f, _) in CODE_CONSTANTS["rx_checks"].items()}
    self.cruise = False
    self.main_on = False
    self.brake = False
    self.brake_prev = False
    self.moving = False
    self.mismatch_since: int | None = None
    self.grant_us = 0
    self.tx_last: dict[str, int] = {}
    self.rate = {n: RateWindow() for n in CODE_CONSTANTS["tx_rate"]}

  # ------------------------------------------------------------------ helpers
  def _enabled(self, tid: str) -> bool:
    return tid not in ("T10b", "T10c", "T11") or self.build == "reference"

  def _go(self, t: int, tid: str, to: str) -> None:
    if not self._enabled(tid):
      return
    if to == ALLOWED and self.state != ALLOWED:
      self.grant_us = t
    self.state = to
    self.fired.append((t, tid))

  def _clear(self, t: int, tid: str) -> None:
    if self.state == ALLOWED:
      self._go(t, tid, NOT_ALLOWED)

  def _lagging(self, name: str, t: int) -> bool:
    c = self.checks[name]
    return (t - c.last_us) > c.period_us

  def _checks_ok(self, t: int) -> bool:
    return all(c.seen and c.valid and not self._lagging(n, t) for n, c in self.checks.items())

  def resync(self, t: int, state: str) -> None:
    """Align with the C state after a reported divergence, so that later divergences are found independently."""
    if state == ALLOWED and self.state != ALLOWED:
      self.grant_us = t
    self.state = state

  # ------------------------------------------------------------------ events
  def rx(self, t: int, name: str, values: dict, corrupt: bool) -> None:
    if name in self.checks:
      c = self.checks[name]
      c.seen, c.valid, c.last_us = True, not corrupt, t
      if corrupt:
        self._clear(t, "T4")
    if not corrupt:
      if name == "PCM_CRUISE":
        cruise = bool(values["CRUISE_ACTIVE"])
        if not cruise:
          self._clear(t, "T2")
        elif not self.cruise:
          if self.state == NOT_ALLOWED and self._checks_ok(t):
            self._go(t, "T1", ALLOWED)
          else:
            self.fired.append((t, "T8"))
        self.cruise = cruise
        self._cruise_main(t, on_pcm_cruise=True)
      elif name == "PCM_CRUISE_2":
        self.main_on = bool(values["MAIN_ON"])
        self._cruise_main(t, on_pcm_cruise=False)
      elif name == "BRAKE_MODULE":
        self.brake = bool(values["BRAKE_PRESSED"])
      elif name == "WHEEL_SPEEDS":
        self.moving = values["speed"] != 0
      # EPS_STATUS (LKA_STATE fault) and gas: non_revoking in the record; no state change
    if self.brake and (not self.brake_prev or self.moving):
      self._clear(t, "T3")
    self.brake_prev = self.brake

  def _cruise_main(self, t: int, on_pcm_cruise: bool) -> None:
    if not self._enabled("T10c"):
      return
    if self.cruise and not self.main_on:
      if self.mismatch_since is None:
        self.mismatch_since = t
        if on_pcm_cruise:
          self._clear(t, "T10c")
      elif t - self.mismatch_since > CRUISE_MAIN_TOLERANCE_US:
        self._clear(t, "T10c")
    else:
      self.mismatch_since = None

  def tx(self, t: int, name: str, content_ok: bool) -> bool:
    """Returns whether the model accepts the frame."""
    if name in self.rate and self._enabled("T11"):
      w = self.rate[name]
      _, f, burst = CODE_CONSTANTS["tx_rate"][name]
      elapsed = t - w.ts_last
      if elapsed >= TX_RATE_HALF_WINDOW_US:
        w.msgs_prev = 0 if elapsed >= 2 * TX_RATE_HALF_WINDOW_US else w.msgs
        w.msgs, w.rejected, w.ts_last = 0, 0, t
      budget = -(-f * 3 // 10) + 1 + burst
      if w.msgs + w.msgs_prev >= budget:
        w.rejected += 1
        if w.rejected >= TX_RATE_REVOKE_REJECTED:
          self._clear(t, "T11")
        return False
      w.msgs += 1
    if not content_ok:
      self._clear(t, "T9")
      return False
    self.tx_last[name] = t
    return True

  def tick(self, t: int) -> None:
    for n in self.checks:
      if self._lagging(n, t) or self.freq[n] < RX_MIN_FREQUENCY_HZ or not (self.checks[n].seen and self.checks[n].valid):
        self._clear(t, "T5")
        break
    if self.state == ALLOWED and self._enabled("T10b"):
      for n, timeout in TX_ARRIVAL_TIMEOUT_US.items():
        if t - max(self.grant_us, self.tx_last.get(n, 0)) > timeout:
          self._clear(t, "T10b")
          break

  def mode_set(self, t: int) -> None:
    if self.state == ALLOWED:
      self._go(t, "T7", NOT_ALLOWED)
    else:
      self.fired.append((t, "T7"))
