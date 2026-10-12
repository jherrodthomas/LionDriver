# Change impact: authority revoked 0.3 s after the last SoC heartbeat

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins panda `c2e5d93` (merge commit of panda#7 on the fork's `master`); not yet verified on hardware (HIL bench D-04); not reviewed independently** |
| Change request | [jherrodthomas/panda#7](https://github.com/jherrodthomas/panda/pull/7) |
| Range | panda `3859fa8..c2e5d93` |
| Reference configuration affected | Yes: every build of the panda firmware |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `b87197f` | `board/drivers/heartbeat_monitor.h` (new), `board/drivers/drivers.h`, `board/main.c`, `board/main_comms.h`, `tests/heartbeat_monitor/` (new), `tests/hitl/test_12_rx_timeout.py` | The 100 Hz safety task counts ticks since the last `0xf3` heartbeat. In a car safety mode it clears `controls_allowed` once 0.3 s (30 ticks) have passed without one, every tick until the next heartbeat. Re-engagement needs a new PCM rising edge. The 1 Hz counter and the 5 s SILENT path (TSR-510) are unchanged | Yes | Yes (more disengagements if the host stalls) | No | Yes (a host that stops talking loses authority within 0.3 s) | SG-01, SG-03, SG-04; FSR-01.07; GAP-06, GAP-10 | WP-S-02 (TSR-407), WP-W-02 (SWSR-407), WP-W-03 §5.1–5.2, WP-W-06 (host tests), WP-V-05 (heartbeat loss) | Builds (all variants), MISRA, host tests; HIL: stop the heartbeat in a car mode and time the drop of `controls_allowed` | Taken (maintainer merged panda#7, 2026-10-12) |

## 2. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| `pandad` sends the heartbeat at 10 Hz from its 100 Hz loop (`selfdrive/pandad/pandad.cc`), only when the panda state read succeeds | Two missed heartbeats are tolerated. A `pandad` stall or failed state read of 0.3 s or more now disengages, where before it went unnoticed until the 5 s SILENT path | Count `controlsMismatch`-free disengagements caused by heartbeat loss in drive logs (the panda health has `heartbeat_lost` only for the 5 s path; add a reason code if this proves frequent) |
| Equal interrupt priority (WP-W-03 §5.1) | The safety task can be delayed by long handlers; the 0.3 s includes one task period only if the task runs on time | WP-W-03 §5.4.5 measurement |

## 3. Verification results

| Check | Result |
|---|---|
| `scons` default, `LIONDRIVER_REFERENCE=1`, `FAULT_INJECTION=1`, `RELEASE=1 LIONDRIVER_REFERENCE=1` | Pass (`-Werror`) |
| `tests/misra/test_misra.sh` (standard and reference variants) | Clean |
| `tests/heartbeat_monitor` (host) | Pass: timeout equals 0.3 s; revokes exactly after it and holds; heartbeats at 10 Hz never revoke; two missed heartbeats tolerated; a heartbeat clears it |
| HIL | **Not run** (D-04). `test_12` now keeps the heartbeat fresh while engaging |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | HIL: stop the heartbeat in TOYOTA mode and time the drop of `controls_allowed` | Release |
| OI-2 | Report a heartbeat-caused revocation to the host with its own reason (TSR-406 fault-specific reason codes) | Later change |
