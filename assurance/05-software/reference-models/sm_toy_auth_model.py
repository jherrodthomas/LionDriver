#!/usr/bin/env python3
"""Executable reference model of SM-TOY-AUTH (Toyota authority, controls_allowed).

Written from the specification layer only, not from the C:
  - the state-machine record   assurance/05-software/state-machines/sm-toy-auth.yaml (transition ids, events, guards)
  - the SWSR texts              WP-W-02 / trace/items/swsr.yaml (SWSR-301, 302, 306, 311, 401, 402, 405(c) v0.16, 406, 518)
  - the TX rate design          05-software/design-notes/DN-01-tx-rate-supervision.md §4 and §10
  - configuration data          WP-W-09 CD-03 (timeout), CD-04 (RX set), DN-01 §4.1 (budgets); DLC from the DBC
Where these sources are silent the model makes a modelling assumption (MA-xx in README.md). Each place where the
model may differ from the C on purpose is a named option in DEVIATIONS, off by default, so that a divergence found by
the back-to-back run can be attributed: switching the option on must make that class of divergence disappear.

Scope: the transitions observable through libsafety (T1, T2, T3, T4, T5, T7, T8, T10c, T11). T6 and T10a are panda
main.c and are not in libsafety; T9, T10b, T10d, T10e, T12-T15 are target state ("not implemented") and are not
compared. Drafting origin: ai-assisted (Claude), not reviewed. The author had read the C before writing this model, so
it is an independent implementation, not an independent reading of the requirements (README.md §4).

Standard library only. The model works on decoded events, not on CAN bytes; the harness (b2b_toy_auth.py) encodes the
same events into frames for the C.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ------------------------------------------------------------------ configuration (cited)

# WP-W-09 CD-04 / WP-W-05 UN-02 table: RX set of the reference car (non-SecOC, LKA, BRAKE_MODULE 0x226, param 73).
# (nominal Hz, checksum checked, quality checked). All on bus 0; DLC 8 for every message (toyota_nodsu_pt DBC).
RX_SET_COMMON = {
  0x0AA: (83, False, True),   # WHEEL_SPEEDS, quality = no wheel-speed fault bit
  0x260: (50, True, False),   # STEER_TORQUE_SENSOR (LKA: quality not checked)
  0x1D2: (33, True, False),   # PCM_CRUISE
  0x226: (40, False, False),  # BRAKE_MODULE
}
RX_SET_REFERENCE = {
  0x262: (25, True, False),   # EPS_STATUS, reference build only
  0x1D3: (33, True, False),   # PCM_CRUISE_2, reference build only
}
RX_BUS = 0
RX_DLC = 8
TIMEOUT_PERIODS = 5             # WP-W-09 CD-03, SWSR-401: "more than 5 nominal periods"
MIN_RX_FREQUENCY_HZ = 10        # SM record T5 guard "below 10 Hz"
CRUISE_MAIN_TOLERANCE_US = 150_000  # SM record T10c "> 150 ms"

# DN-01 §4.1 (reference build): addr -> (f Hz, burst). TX whitelist DLC from WP-W-09 CD-04 TX column.
TX_RATE_ROWS = {0x2E4: (100, 5), 0x191: (50, 3), 0x343: (33, 3), 0x412: (5, 4), 0x283: (1, 2), 0x1D2: (1, 2),
                0x750: (5, 2)}
TX_WINDOW_US = 250_000          # DN-01 §4: 250 ms window of two 125 ms half-windows
TX_REVOKE_REJECTED = 3          # DN-01 D-3

# Deviations: each option makes the model follow a reading other than the literal specification text.
# All False = the literal reading. The harness switches them on one at a time to attribute divergences.
DEVIATIONS = {
  # SWSR-402 says a length failure of an RX-set message is an RX fault. Option: a frame with the wrong DLC is
  # treated as a message outside the RX set (ignored apart from the brake-edge check).
  "length_not_checked": False,
  # SWSR-302 says "any wheel speed is non-zero". Option: moving = sum of the four wheel speeds non-zero.
  "moving_from_sum": False,
}


def tx_budget(freq: int, burst: int) -> int:
  # DN-01 §4.1: ceil(f x 0.25 s x 1.2) + 1 + burst
  return -(-freq * 3 // 10) + 1 + burst


def timeout_us(freq: int) -> int:
  # CD-03 writes the threshold as 5 x (10^6 / f) us with the period truncated to whole microseconds
  return TIMEOUT_PERIODS * (1_000_000 // freq)


# ------------------------------------------------------------------ events

@dataclass
class Rx:
  """One received frame, decoded. `signals` holds the values the harness packs; flags describe corruption."""
  addr: int
  bus: int = 0
  dlc: int = 8
  checksum_ok: bool = True
  signals: dict = field(default_factory=dict)


@dataclass
class Tick:
  """One call of the periodic safety task (safety_tick)."""


@dataclass
class Tx:
  """One SoC frame offered to the TX hook. Content is not modelled: only the rate supervision acts on authority."""
  addr: int
  bus: int = 0
  dlc: int = 8


@dataclass
class SetMode:
  """Safety mode set (0xdc, heartbeat loss, harness change): Toyota with the same parameter again."""


# ------------------------------------------------------------------ model

@dataclass
class _RxCheck:
  freq: int
  checksum: bool
  quality: bool
  seen: bool = False
  last_ts: int = 0
  last_frame_ok: bool = False


@dataclass
class _TxRate:
  msgs: int = 0
  msgs_prev: int = 0
  rejected: int = 0
  ts_last: int = 0


class SmToyAuth:
  def __init__(self, reference: bool, deviations: dict | None = None):
    self.reference = reference
    self.dev = dict(DEVIATIONS)
    self.dev.update(deviations or {})
    self.now = 0
    self.reset()

  # T7, SWSR-311: authority false, all edge, sample and limiter state reset
  def reset(self) -> None:
    rx = dict(RX_SET_COMMON)
    if self.reference:
      rx.update(RX_SET_REFERENCE)
    self.rx = {a: _RxCheck(*v) for a, v in rx.items()}
    self.tx = {a: _TxRate() for a in TX_RATE_ROWS} if self.reference else {}
    self.allowed = False
    self.tx_rate_exceeded = False
    self.cruise_active = False      # last valid 0x1D2 CRUISE_ACTIVE (edge reference)
    self.main_on = False            # last valid 0x1D3 MAIN_ON
    self.brake = False              # last valid 0x226 BRAKE_PRESSED
    self.brake_prev = False
    self.wheels = (0, 0, 0, 0)      # last valid 0xAA wheel speeds, raw offset removed (0 = standing)
    self.mismatch_start: int | None = None

  # ---------------------------------------------------------------- helpers

  def _check_ok(self, c: _RxCheck) -> bool:
    lagging = (self.now - c.last_ts) > timeout_us(c.freq)
    return c.seen and c.last_frame_ok and not lagging and c.freq >= MIN_RX_FREQUENCY_HZ

  def _all_checks_ok(self) -> bool:
    return all(self._check_ok(c) for c in self.rx.values())

  def _moving(self) -> bool:
    if self.dev["moving_from_sum"]:
      return sum(self.wheels) != 0
    return any(w != 0 for w in self.wheels)

  # ---------------------------------------------------------------- steps

  def step(self, ev) -> list[str]:
    """Apply one event at self.now; return the ids of the SM-record transitions taken (for coverage).

    A transition counts only from its source state: T2, T3, T4, T5, T10c and T11 leave ALLOWED, T1 and T8 leave
    NOT_ALLOWED, T7 leaves any state."""
    was_allowed = self.allowed
    if isinstance(ev, SetMode):
      self.reset()
      return ["T7"]
    if isinstance(ev, Tick):
      fired = self._tick()
    elif isinstance(ev, Tx):
      fired = self._tx(ev)
    else:
      fired = self._rx(ev)
    from_not_allowed = {"T1", "T8"}
    return [t for t in fired if (t in from_not_allowed) != was_allowed]

  def _tick(self) -> list[str]:
    # T5: any RX check lagging, below 10 Hz or invalid -> clear
    if not self._all_checks_ok():
      self.allowed = False
      return ["T5"]
    return []

  def _tx(self, ev: Tx) -> list[str]:
    # T11 (reference build), DN-01 §4.2. Only frames on the TX whitelist reach the rate check; the harness sends
    # whitelisted (addr, bus, dlc) only, so the whitelist itself is not modelled.
    row = self.tx.get(ev.addr) if ev.bus == 0 else None
    if row is None:
      return []
    freq, burst = TX_RATE_ROWS[ev.addr]
    elapsed = self.now - row.ts_last
    if elapsed >= TX_WINDOW_US // 2:
      # DN-01 §4.2 step 2; §10: after a whole window without frames the previous half-window is empty too
      row.msgs_prev = 0 if elapsed >= TX_WINDOW_US else row.msgs
      row.msgs = 0
      row.rejected = 0
      row.ts_last = self.now
    if row.msgs + row.msgs_prev >= tx_budget(freq, burst):
      row.rejected += 1
      if self.allowed and row.rejected >= TX_REVOKE_REJECTED:
        self.allowed = False
        self.tx_rate_exceeded = True
        return ["T11"]
    else:
      row.msgs += 1
    return []

  def _rx(self, ev: Rx) -> list[str]:
    fired: list[str] = []
    clear = False
    grant = False

    c = self.rx.get(ev.addr) if ev.bus == RX_BUS else None
    if c is not None and ev.dlc != RX_DLC and self.dev["length_not_checked"]:
      c = None  # deviation: treated as a message outside the RX set
    valid = False
    if c is not None:
      # SWSR-402: checksum and length; quality flag where configured (0xAA wheel-speed fault bits)
      frame_ok = ev.dlc == RX_DLC
      if c.checksum:
        frame_ok = frame_ok and ev.checksum_ok
      if c.quality:
        frame_ok = frame_ok and not any(ev.signals.get(f"WHEEL_SPEED_{w}_FAULT", 0) for w in ("FR", "FL", "RR", "RL"))
      c.seen = True
      c.last_ts = self.now
      c.last_frame_ok = frame_ok
      valid = frame_ok
      if not frame_ok:
        clear = True              # T4, SWSR-406: clear in the same call
        fired.append("T4")

    if valid:
      s = ev.signals
      if ev.addr == 0x1D2:
        cruise = bool(s.get("CRUISE_ACTIVE", 0))
        if not cruise:
          clear = True
          fired.append("T2")
        elif not self.cruise_active:
          # rising edge: T1 if every RX check passes now (SWSR-306) and, in the reference build, MAIN_ON = 1
          # (SWSR-405(c) v0.16: cruise becoming active while main is off is an RX fault at once); else T8
          if self._all_checks_ok() and not (self.reference and not self.main_on):
            grant = True
            fired.append("T1")
          else:
            fired.append("T8")
        self.cruise_active = cruise
      elif ev.addr == 0x1D3:
        self.main_on = bool(s.get("MAIN_ON", 0))
      elif ev.addr == 0x226:
        self.brake = bool(s.get("BRAKE_PRESSED", 0))
      elif ev.addr == 0x0AA:
        self.wheels = tuple(int(s.get(f"WHEEL_SPEED_{w}_RAW", 6767)) - 6767 for w in ("FR", "FL", "RR", "RL"))
      # 0x260 and 0x262 carry no authority input (EPS fault is non-revoking in the SM record)

      # T10c (reference build), SWSR-405(c): MAIN_ON off while CRUISE_ACTIVE for > 150 ms, evaluated on 0x1D2 / 0x1D3
      if self.reference and ev.addr in (0x1D2, 0x1D3):
        mismatch = self.cruise_active and not self.main_on
        if not mismatch:
          self.mismatch_start = None
        elif self.mismatch_start is None:
          self.mismatch_start = self.now
          if ev.addr == 0x1D2:
            clear = True            # SWSR-405(c) v0.16: the mismatch began with cruise becoming active
        elif self.now - self.mismatch_start > CRUISE_MAIN_TOLERANCE_US:
          clear = True
          fired.append("T10c")

    # T3, SWSR-302: on any RX call, brake rising, or pressed while moving (brake from the last valid 0x226)
    if self.brake and (not self.brake_prev or self._moving()):
      clear = True
      fired.append("T3")
    self.brake_prev = self.brake

    # MA-03: within one call a clearing condition wins over a grant
    if clear:
      self.allowed = False
    elif grant:
      self.allowed = True
    return fired
