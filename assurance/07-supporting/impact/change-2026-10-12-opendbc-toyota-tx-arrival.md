# Change impact: arrival supervision of the SoC's actuation frames (reference build)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-12: LionDriver pins opendbc `31e890d` (branch `claude/tx-arrival-supervision`) until opendbc#11 is merged; not yet verified on the vehicle or on hardware (HIL bench D-04); not reviewed independently** |
| Change request | [jherrodthomas/opendbc#11](https://github.com/jherrodthomas/opendbc/pull/11) |
| Range | opendbc `875e325..31e890d` |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE`, Toyota LKA torque control without SecOC); other builds and configurations are unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `31e890d` | `opendbc/safety/safety.h`, `declarations.h`, `modes/defaults.h`, `modes/toyota.h`, `tests/test_toyota.py` | While authority is granted, STEERING_LKA (`0x2E4`, 100 Hz) must reach the TX hook at least every 50 ms and, with openpilot longitudinal, ACC_CONTROL (`0x343`, 33 Hz) at least every 100 ms; otherwise the 100 Hz safety task revokes authority. Supervision starts when authority is granted. Generic mechanism (`safety_config.tx_arrival_checks`), compiled only with `LIONDRIVER_REFERENCE` | Yes | No | Yes (a stalled ML control loop ends in a stalled `controlsd`) | No | SG-01, SG-03, SG-06; HE-02.3; WP-A-04 SPF-14 (stale SoC command held), BE-1.19, BE-6.05; GAP-10 | WP-S-02 (TSR-408), WP-W-02 (SWSR-408), WP-W-06 (unit test), WP-V-05 (FI), WP-A-04 (SPF-14) | Safety unit tests (both variants, 100 % line coverage); mutation of the new code; opendbc and panda MISRA; replay of reference logs (TX gaps while engaged); HIL; vehicle test | Pending (opendbc#11) |

## 2. What it detects

| SoC failure | Before | After |
|---|---|---|
| `controlsd` hangs or stops publishing `carControl` | `card` stops sending within 0.1 s; the last torque stays applied until the EPS drops LKA (AOU-01R). The heartbeat stays alive (it reflects `pandad`) | Authority revoked ≤ 50 ms after the last `0x2E4` (plus one 10 ms safety-task period) |
| `card` hangs | As above, without the 0.1 s | As above |
| `pandad` send thread stalls, heartbeat thread alive | No reaction until the EPS drop-out | As above |
| SoC replays an old command buffer (BE-1.21) | — | **Not detected**: frames keep arriving. Needs the transfer counter of TSR-410/411 |
| Stale model input while `controlsd` runs (BE-1.19 with fresh frames) | — | **Not detected**: frames keep arriving. Host-side (GAP-16) and TSR-409 (heartbeat carries control-loop evidence) |

The driver sees the revocation as "Controls Mismatch" (the panda withdraws authority while `selfdrived` is engaged), an immediate disable with an alert.

## 3. Thresholds and false positives

| Message | Nominal period | Timeout | Missed frames tolerated |
|---|---|---|---|
| `0x2E4` STEERING_LKA | 10 ms | 50 ms (TSR-408) | 4 |
| `0x343` ACC_CONTROL | 30 ms | 100 ms (TSR-408) | 2 |

A host stall longer than the timeout now ends the engagement. That is the intended reaction to a stalled control loop, but a stall that occurs in normal driving (CPU load, `card` or `pandad` scheduling) would be a nuisance disengagement. The values come from TSR-408 and are **not yet confirmed on reference drive logs** (OI-1).

## 4. Verification results

| Check | Result |
|---|---|
| Safety unit tests, default and `LIONDRIVER_REFERENCE=1` (all modes) | OK under UBSan and with coverage; 100 % line coverage in both variants |
| New tests (reference variant) | `test_tx_arrival_supervision` (per message: at the timeout allowed, 1 µs later revoked, 10 ms task steps with the other frames arriving); `test_tx_arrival_starts_at_grant`; `test_tx_arrival_acc_control_only_with_openpilot_longitudinal`; `test_tx_arrival_not_supervised_outside_reference` |
| Existing test changed | `test_rx_timeout_5_periods_each_msg` held authority for up to 200 ms without actuation frames; it now sends them, so it still tests only the RX timeout |
| Mutation | 20/20 mutants of the new code killed (scratch run of `mutation.py` with `-DLIONDRIVER_REFERENCE`, filtered to the changed lines). By hand: revocation removed → 8 failures; ACC_CONTROL always supervised → 1 failure. Note: CI's `mutation.py` preprocesses without `LIONDRIVER_REFERENCE`, so reference-only code is never mutated in CI (OI-3) |
| opendbc MISRA (cppcheck step, both variants) and panda `tests/misra/test_misra.sh` (standard and reference) | Clean |
| panda `panda_h7` build, both variants | Builds with `-Werror` |
| Replay, vehicle, HIL | **Not run** (no reference logs; GAP-30; D-04) |

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Confirm the 50 ms / 100 ms timeouts on reference logs: longest `0x2E4` and `0x343` gaps while engaged (`tools/can_gaps`) | Integration |
| OI-2 | Report the reason to the host (health flag, as DN-01 §4.3), so a TX-arrival revocation is not only a generic `controlsMismatch` | Later change |
| OI-3 | Run `mutation.py` on the reference variant in CI (preprocess with `-DLIONDRIVER_REFERENCE`); affects all reference-only additions | Later change |
| OI-4 | HIL: stop `card` while engaged; authority must drop within ≤ 60 ms | D-04 |
