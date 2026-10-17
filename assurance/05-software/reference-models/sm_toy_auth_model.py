#!/usr/bin/env python3
"""Executable reference model of SM-TOY-AUTH (Toyota authority, controls_allowed).

Written from the specification layer only, not from the C:
  - the state-machine record   assurance/05-software/state-machines/sm-toy-auth.yaml (transition ids, events, guards)
  - the SWSR texts              WP-W-02 / trace/items/swsr.yaml (SWSR-301, 302, 306, 311, 401, 402, 405(c) v0.20, 406, 408, 518)
  - the TX rate design          05-software/design-notes/DN-01-tx-rate-supervision.md §4 and §10
  - configuration data          WP-W-09 CD-03 (timeout), CD-04 (RX set), DN-01 §4.1 (budgets); DLC from the DBC
  - the engagement window        WP-S-02 TSR-301 v0.20 (LS-06: the grant waits for the heartbeat's engaged flag) and
                                 the record's T1a, T1b, T1c (reference build; no SWSR text yet, change record OI-2)
Where these sources are silent the model makes a modelling assumption (MA-xx in README.md). Each place where the
model may differ from the C on purpose is a named option in DEVIATIONS, off by default, so that a divergence found by
the back-to-back run can be attributed: switching the option on must make that class of divergence disappear.

Scope: the transitions observable through libsafety (T1, T1a, T1b, T1c, T2, T3, T4, T5, T7, T8, T10b, T10c, T11). T6 and T10a are
panda main.c and are not in libsafety; T9, T10d, T10e, T12-T15 are target state ("not implemented") and are not
compared. T10b (SWSR-408) is in the reference build since opendbc 273f44e. Drafting origin: ai-assisted (Claude), not reviewed. The author had read the C before writing this model, so
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
ENGAGE_WINDOW_US = 1_000_000    # SM record T1b "within 1 s of the edge" (TSR-301 v0.20, LS-06); MA-10: 1 s itself is within
HEARTBEAT_GATE = True           # TSR-301 v0.20: the grant waits for the heartbeat's engaged flag (reference build)
MAIN_OFF_CLOSES_WINDOW = True   # SWSR-405(c) "at once": a refusal for MAIN_ON = 0 leaves no window open (SM-F1)

# DN-01 §4.1 (reference build): addr -> (f Hz, burst). TX whitelist DLC from WP-W-09 CD-04 TX column.
TX_RATE_ROWS = {0x2E4: (100, 5), 0x191: (50, 3), 0x343: (33, 3), 0x412: (5, 4), 0x283: (1, 2), 0x1D2: (1, 2),
                0x750: (5, 2)}
# SWSR-408 (reference build): longest gap between accepted actuation frames while authority is granted. 0x343 is
# supervised with openpilot longitudinal, which the reference configuration (param 73, no stock-longitudinal flag) is.
TX_ARRIVAL_US = {0x2E4: 50_000, 0x343: 100_000}
TX_WINDOW_US = 250_000          # DN-01 §4: 250 ms window of two 125 ms half-windows
TX_REVOKE_REJECTED = 3          # DN-01 D-3

# Deviations: each option makes the model follow a reading other than the literal specification text.
# All False = the literal reading. The harness switches them on one at a time to attribute divergences.
DEVIATIONS = {
  # SWSR-402 says a length failure of an RX-set message is an RX fault. Option: a frame with the wrong DLC is
  # treated as a message outside the RX set (ignored apart from the brake-edge check). Upstream build only: the
  # reference build makes it an RX fault since opendbc ATC-25 (B2B-01), so the option has no effect there.
  "length_not_checked": False,
  # SWSR-302 says "any wheel speed is non-zero". Option: moving = sum of the four wheel speeds non-zero.
  "moving_from_sum": False,
  # SWSR-408 / MA-08: supervision starts when authority is granted (B2B-04). Option: it starts at the first safety task that
  # finds authority granted, and "granted before" is what the previous safety task saw.
  "arrival_from_first_tick": False,
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
class Heartbeat:
  """The SoC heartbeat's engaged flag changes (0xf3, TSR-301 v0.20). Only the flag is modelled: heartbeat loss (T10a)
  and the 1 Hz engaged-mismatch check (T6) are panda main.c and not in libsafety."""
  engaged: bool


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
  def __init__(self, reference: bool, deviations: dict | None = None, heartbeat_engaged: bool = True):
    self.reference = reference
    self.dev = dict(DEVIATIONS)
    self.dev.update(deviations or {})
    self.now = 0
    self.heartbeat_engaged = heartbeat_engaged   # host state: a safety mode set does not change it
    self.reset()

  # T7, SWSR-311: authority false, all edge, sample and limiter state reset; the cruise edge state is "not yet seen
  # disengaged" (SWSR-311 v0.24)
  def reset(self) -> None:
    rx = dict(RX_SET_COMMON)
    if self.reference:
      rx.update(RX_SET_REFERENCE)
    self.rx = {a: _RxCheck(*v) for a, v in rx.items()}
    self.tx = {a: _TxRate() for a in TX_RATE_ROWS} if self.reference else {}
    self.allowed = False
    self.tx_rate_exceeded = False
    self.cruise_active = False      # last valid 0x1D2 CRUISE_ACTIVE (edge reference)
    self.seen_disengaged = False    # CRUISE_ACTIVE = 0 received since the last mode set (SWSR-311 v0.24)
    self.tx_block = False           # SWSR-518 v0.24: a TX-rate revocation blocks the next grants
    self.last_reject_ts: int | None = None
    self.main_on = False            # last valid 0x1D3 MAIN_ON
    self.brake = False              # last valid 0x226 BRAKE_PRESSED
    self.brake_prev = False
    self.wheels = (0, 0, 0, 0)      # last valid 0xAA wheel speeds, raw offset removed (0 = standing)
    self.mismatch_start: int | None = None
    self.arrival_last = {a: None for a in TX_ARRIVAL_US}   # last accepted (or, deviation, offered) frame per ID
    self.grant_ts: int | None = None                        # time authority was last granted
    self.allowed_prev_tick = False                          # authority as the previous safety task left it
    self.pending = False            # ENGAGE_PENDING (reference build): a cruise edge waits for the heartbeat flag
    self.pending_ts = 0

  # ---------------------------------------------------------------- helpers

  def _check_ok(self, c: _RxCheck) -> bool:
    lagging = (self.now - c.last_ts) > timeout_us(c.freq)
    return c.seen and c.last_frame_ok and not lagging and c.freq >= MIN_RX_FREQUENCY_HZ

  def _all_checks_ok(self) -> bool:
    return all(self._check_ok(c) for c in self.rx.values())

  def _tx_block_holds(self) -> bool:
    """SWSR-518 v0.24: after a revocation, no grant until a full window without a rejected frame (the block ends then)."""
    if self.tx_block and self.last_reject_ts is not None and self.now - self.last_reject_ts >= TX_WINDOW_US:
      self.tx_block = False
    return self.tx_block

  def _moving(self) -> bool:
    if self.dev["moving_from_sum"]:
      return sum(self.wheels) != 0
    return any(w != 0 for w in self.wheels)

  # ---------------------------------------------------------------- steps

  def step(self, ev) -> list[str]:
    """Apply one event at self.now; return the ids of the SM-record transitions taken (for coverage).

    A transition counts only from its source state: T2, T3, T4, T5, T10c and T11 leave ALLOWED; T1, T1a and T8 leave
    NOT_ALLOWED; T1b and T1c leave ENGAGE_PENDING (authority not granted); T7 leaves any state."""
    was_allowed = self.allowed
    if isinstance(ev, SetMode):
      self.reset()
      return ["T7"]
    if isinstance(ev, Heartbeat):
      self.heartbeat_engaged = ev.engaged
      return []
    if isinstance(ev, Tick):
      fired = self._tick()
    elif isinstance(ev, Tx):
      fired = self._tx(ev)
    else:
      fired = self._rx(ev)
    from_not_allowed = {"T1", "T1a", "T1b", "T1c", "T8"}
    return [t for t in fired if (t in from_not_allowed) != was_allowed]

  def _tick(self) -> list[str]:
    fired = []
    # T5: any RX check lagging, below 10 Hz or invalid -> clear
    if not self._all_checks_ok():
      self.allowed = False
      fired.append("T5")
      if self.pending:              # T1c: an RX check lagging, below 10 Hz or invalid in the safety task
        self.pending = False
        fired.append("T1c")
    # T1b / T1c (reference build): the window grants once the heartbeat reports engaged, within 1 s of the edge, if
    # rx_checks_allow_engagement() holds then; otherwise it closes without a grant
    if self.pending:
      if self.now - self.pending_ts > ENGAGE_WINDOW_US:
        self.pending = False
        fired.append("T1c")
      elif self.heartbeat_engaged:
        self.pending = False
        if self._all_checks_ok() and not self._tx_block_holds():
          if not self.allowed:
            self.grant_ts = self.now
          self.allowed = True
          fired.append("T1b")
        else:
          fired.append("T1c")
    # T10b (reference build), SWSR-408: an actuation message not accepted for longer than its limit -> clear.
    # MA-07: evaluated in the safety task (acceptance: "50/100 ms + task period")
    if self.reference:
      if self.dev["arrival_from_first_tick"] and self.allowed and not self.allowed_prev_tick:
        self.arrival_last = {a: self.now for a in TX_ARRIVAL_US}
      if self.allowed:
        for a, limit in TX_ARRIVAL_US.items():
          since = [x for x in (self.arrival_last[a], None if self.dev["arrival_from_first_tick"] else self.grant_ts)
                   if x is not None]
          if since and self.now - max(since) > limit:
            self.allowed = False
            fired.append("T10b")
            break
      self.allowed_prev_tick = self.allowed
    return fired

  def _tx(self, ev: Tx) -> list[str]:
    # T11 (reference build), DN-01 §4.2. Only frames on the TX whitelist reach the rate check; the harness sends
    # whitelisted (addr, bus, dlc) only, so the whitelist itself is not modelled.
    row = self.tx.get(ev.addr) if ev.bus == 0 else None
    if row is None:
      return []
    supervised = ev.addr in TX_ARRIVAL_US
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
      self.last_reject_ts = self.now
      if self.allowed and row.rejected >= TX_REVOKE_REJECTED:
        self.allowed = False
        self.tx_rate_exceeded = True
        self.tx_block = True
        return ["T11"]
    else:
      row.msgs += 1
      if supervised:
        self.arrival_last[ev.addr] = self.now   # SWSR-408: accepted. MA-09: content is not modelled (B2B-05)
    return []

  def _rx(self, ev: Rx) -> list[str]:
    fired: list[str] = []
    clear = False
    grant = False

    c = self.rx.get(ev.addr) if ev.bus == RX_BUS else None
    if c is not None and ev.dlc != RX_DLC and self.dev["length_not_checked"] and not self.reference:
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
          self.seen_disengaged = True
          if self.pending:          # T1c: CRUISE_ACTIVE = 0 closes the window
            self.pending = False
            fired.append("T1c")
        elif not self.cruise_active:
          # rising edge: T1 if every RX check passes now (SWSR-306) and, in the reference build, MAIN_ON = 1
          # (SWSR-405(c) v0.20: cruise becoming active while main is off is an RX fault at once); else T8.
          # Reference build, v0.24: also CRUISE_ACTIVE = 0 seen since the mode set (SWSR-311) and no TX-rate block
          # (SWSR-518). Both are LIONDRIVER_REFERENCE changes; the upstream build keeps the old behaviour
          tx_blocked = self.reference and self._tx_block_holds()
          edge_counts = (not self.reference) or self.seen_disengaged
          # Reference build, TSR-301 v0.20 (LS-06): with the heartbeat not engaged the edge opens the window (T1a)
          # instead of granting. An edge refused for MAIN_ON = 0 opens no window (T8; SM-F1 fixed at opendbc 98d3be1)
          guards = self._all_checks_ok() and edge_counts and not tx_blocked
          main_refused = self.reference and not self.main_on
          if (guards and self.reference and HEARTBEAT_GATE and not self.heartbeat_engaged
              and not (main_refused and MAIN_OFF_CLOSES_WINDOW)):
            self.pending = True
            self.pending_ts = self.now
            fired.append("T1a")
          elif guards and not main_refused:
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
            clear = True            # SWSR-405(c) v0.20: the mismatch began with cruise becoming active
        elif self.now - self.mismatch_start > CRUISE_MAIN_TOLERANCE_US:
          clear = True
          fired.append("T10c")
          if self.pending and MAIN_OFF_CLOSES_WINDOW:  # T1c: MAIN_ON = 0 with cruise active > 150 ms closes it
            self.pending = False
            fired.append("T1c")

    # T3, SWSR-302: on any RX call, brake rising, or pressed while moving (brake from the last valid 0x226)
    if self.brake and (not self.brake_prev or self._moving()):
      clear = True
      fired.append("T3")
      if self.pending:              # T1c: brake rising, or pressed while moving, closes the window
        self.pending = False
        fired.append("T1c")
    self.brake_prev = self.brake

    # MA-03: within one call a clearing condition wins over a grant
    if clear:
      self.allowed = False
    elif grant:
      if not self.allowed:
        self.grant_ts = self.now
      self.allowed = True
    return fired
