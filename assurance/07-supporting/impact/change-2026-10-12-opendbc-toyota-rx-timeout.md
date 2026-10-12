# Change impact: Toyota RX timeout of 5 periods in the envelope

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins panda `9f60e17`, opendbc `aff4033`; follow-ups at panda `3859fa8`, opendbc `5b5a4ba` (merge commits on the forks' `master`); not yet verified on hardware (HIL bench D-04); not reviewed independently.** |
| Change request | [jherrodthomas/opendbc#1](https://github.com/jherrodthomas/opendbc/pull/1); follow-on [jherrodthomas/opendbc#3](https://github.com/jherrodthomas/opendbc/pull/3) for TSR-306, stacked on #1 (§7) |
| Range | opendbc `229dc70..0edef9b` (branch `claude/toyota-rx-timeout`; `0edef9b` adds a test only); LionDriver pin stays at `229dc70` until the change is merged to the fork's `master` |
| Depends on | [jherrodthomas/panda#3](https://github.com/jherrodthomas/panda/pull/3) (100 Hz safety task, SWSR-401a). Without it `safety_tick()` runs at 1 Hz and detection stays ≥ 1 s. Integrate both in the same pin update |
| Reference configuration affected | Yes: the Toyota safety mode runs on the reference device |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `de80b63` | `opendbc/safety/declarations.h`, `opendbc/safety/safety.h`, `opendbc/safety/modes/toyota.h`, `opendbc/safety/modes/defaults.h`, `opendbc/safety/tests/test_toyota.py` | New `safety_config.rx_timeout_periods`. When non-zero, an RX check lags after that many nominal periods, with no 1 s floor; 0 keeps upstream max(10 periods, 1 s). Toyota sets 5: `0xAA` 60 ms, `0x260` 100 ms, `0x226` 125 ms, `0x1D2` 150 ms, each plus one 10 ms task period. All other modes are unchanged | Yes | No | No | No | SG-01, SG-02; FSR-01.06; GAP-06 | WP-S-02 (TSR-401 Impl), WP-W-02 (SWSR-401 status), WP-S-04 (RX detection time), gap assessment (GAP-06), WP-W-06 (new unit test), WP-V-05 (RX loss fault injection) | Safety unit tests with 100 % line coverage; opendbc and panda MISRA; safety replay on Toyota routes; RX loss fault injection on the HIL bench; drive with logging for false timeouts | Take with panda#3 after review, safety replay and HIL evidence |

## 2. Effect on TSR-401

| TSR-401 requires | With this change and panda#3 | Remaining |
|---|---|---|
| Absence longer than 5 nominal periods detected | Yes, for the four Toyota RX checks in the envelope | `0x262`, `0x1D3` and `0xB4` are not in the RX check set yet (TSR-401 "once added"; TSR-110) |
| Evaluated at ≥ 50 Hz | 100 Hz (panda#3) | Measured period and jitter on the device (SWSR-401a, HIL) |
| Worst-case detection ≤ 0.2 s | ≤ 0.16 s (`0x1D2`, 33 Hz) | Confirm the nominal rates against the measured ones (WP-S-05 OI-7) |

Not covered by opendbc#1: TSR-306. Authority can still be granted on a PCM rising edge between two ticks while a message is lagging, for at most one task period (10 ms). opendbc#3 proposes to close this (§7).

## 3. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| Tighter threshold (5 periods instead of ≥ 1 s) | Bus load, arbitration or a late ECU can cause a false timeout. Authority is revoked and openpilot disengages, which is the safe direction, but frequent disengagements hurt availability | Safety replay on Toyota routes; logged drives on the reference vehicle; count `safety_rx_checks_invalid` events |
| A message rate below its declared nominal rate on some Toyota variant | Permanent false timeouts: openpilot cannot engage on that car | Compare the declared rates in `modes/toyota.h` with measured rates (WP-S-05 OI-7) across the supported Toyota platforms |
| Other brands | No change (field defaults to 0) | Full safety test suite |

## 4. Verification results

| Check | Result |
|---|---|
| Safety unit tests (`python -m unittest discover` in `opendbc/safety/tests`) | 3180 tests, OK |
| Line coverage (gcovr, `--fail-under-line=100`, the `test.sh` gate) | 100 % |
| New test `test_rx_timeout_5_periods` (every Toyota test class) | Pass. Checks that the config is valid at exactly 5 periods of `0xAA` and invalid, with controls cleared, 1 µs later |
| Test `test_rx_timeout_5_periods_each_msg` (`0edef9b`, every Toyota test class) | Pass. For every RX check (SecOC `0x176`, `0x116`, `0x101` included), that message alone stops while the others keep arriving: valid at exactly 5 of its nominal periods, invalid with controls cleared 1 µs later. Ported from jherrodthomas/opendbc#4, closed as a duplicate of opendbc#1 |
| Mutation check | Toyota threshold 5 → 6 fails 7 tests. A wrong nominal rate on `0x1D2` (33 → 34 Hz) passes `test_rx_timeout_5_periods` and fails `test_rx_timeout_5_periods_each_msg` |
| opendbc MISRA (cppcheck step of `tests/misra/test_misra.sh`) | Clean |
| panda `tests/misra/test_misra.sh` built against this tree | Clean |
| `test.sh` and the MISRA script as-is | **Not run as-is**: their `setup.sh` fetches a dataset the session proxy blocks; the steps were run directly |
| Safety replay on Toyota routes | **Not run**: no route data available in the session |
| HIL fault injection, vehicle | **Not run** (GAP-30; HIL bench plan D-04) |

## 5. Work products to update on integration

None are changed yet, because the change is not integrated. When opendbc#1 and panda#3 are merged and the pins are moved:

- WP-S-02 TSR-401 Impl column: "Met for the four current Toyota RX checks (5 periods, 100 Hz); `0x262`, `0x1D3`, `0xB4` not yet in the set"; regenerate `trace/items/tsr.yaml`.
- WP-W-02 SWSR-401 status: met for the current set.
- WP-S-04: update the RX timeout detection time.
- Gap assessment: GAP-06 partly closed (RX timeout); heartbeat detection times still open.
- WP-W-06: add the unit test. WP-V-05: add RX loss cases per message.

## 6. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Run safety replay on Toyota routes (reference vehicle first) and record any false timeouts. Tool for the gap part: [`tools/can_gaps/can_gap_scan.py`](../../../tools/can_gaps/README.md) reports the longest inter-frame gap of each RX message in rlogs or candump captures against the timeout; not yet run (no drive data in the development environment) | Integration |
| OI-2 | Confirm the declared RX rates against measured rates (WP-S-05 OI-7). The gap scan also reports each message's observed rate | Integration |
| OI-3 | `0x262` and `0x1D3` added in the reference build (§8, opendbc `98404a4`); `0xB4` still open until its nominal rate is measured | Later change |
| OI-4 | HIL fault injection: remove each RX message and measure the time to revocation | Release |

## 7. Follow-on change: engagement gated on the RX checks (opendbc#3)

[jherrodthomas/opendbc#3](https://github.com/jherrodthomas/opendbc/pull/3) is stacked on opendbc#1 (branch `claude/toyota-rx-grant-check`, `de80b63..7d97fbf`; `7d97fbf` merges in `0edef9b`) and integrated with it.

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `00a51b5` | `opendbc/safety/safety.h`, `opendbc/safety/tests/test_toyota.py` | For modes with `rx_timeout_periods` (Toyota), the PCM rising edge grants controls only if every RX check is seen, valid and not lagging at that moment. The lag computation is shared with `safety_tick()` (`rx_check_lagging()`). Other modes are unchanged | Yes | Yes (engagement refused more often if a message is late at the moment of engagement) | No | No | SG-01, SG-02; FSR-01.05, FSR-01.06; GAP-06 | WP-S-02 (TSR-306 Impl), WP-W-02 (SWSR-306 status), WP-W-06 (new unit test), WP-V-05 | As §1, plus engagement with a missing message on the HIL bench | Take with opendbc#1 after review |

Effect (proposed; pending review): TSR-306 / SWSR-306 met for the checks the envelope has today (seen, checksum, counter, quality flag, timeout) on the four Toyota RX checks. The frozen-value and cross-checks that SWSR-306 also names do not exist yet, so SWSR-306 stays partial. A late message at the moment of a PCM rising edge leaves openpilot not engaged, and the driver has to engage again once the message is back. That is the safe direction; its frequency belongs to the false-timeout check of OI-1.

Verification of opendbc#3 (host only): full safety suite OK; 100 % line coverage; new test `test_no_engagement_with_invalid_rx_checks` (both sides of the threshold, and a message never received); mutation (gate always allows) fails 14 tests; opendbc and panda MISRA clean. The Toyota tests now receive every checked message in `setUp`, as on a live bus; the common tests are unchanged.

## 8. Follow-on change: `0x262` and `0x1D3` in the reference RX set (opendbc#6)

[jherrodthomas/opendbc#6](https://github.com/jherrodthomas/opendbc/pull/6) (branch `claude/toyota-rx-additions`, `5b5a4ba..98404a4`; LionDriver pins `98404a4`).

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `21d8dd8` | `opendbc/safety/modes/toyota.h`, `opendbc/safety/tests/test_toyota.py` | With `LIONDRIVER_REFERENCE`, the non-SecOC Toyota RX set with BRAKE_MODULE (the reference car, parameter 73) adds EPS_STATUS `0x262` (25 Hz) and PCM_CRUISE_2 `0x1D3` (33 Hz) with checksum and the 5-period timeout. Engagement needs both (TSR-306); a timeout revokes authority (TSR-401). Their content is not used yet. Alt-brake and SecOC sets, and all other builds, are unchanged | Yes | Yes (engagement refused if either message is missing, late or corrupt) | No | No | SG-01, SG-02; FSR-01.06, FSR-02.01; GAP-03, GAP-06 | WP-S-02 (TSR-110, 401), WP-W-02 (SWSR-110, 401), WP-S-05 (§3, S-12, S-13), WP-W-06 (unit test) | As §1; plus the false-timeout check for both messages on reference logs (OI-1, OI-2) | Taken (maintainer merged opendbc#6, 2026-10-12) |

**Nominal rates.** The DBC files carry no cycle times. 25 Hz and 33 Hz are the minimum rates openpilot's CAN parser required for these messages (`selfdrive/car/toyota/carstate.py`, openpilot v0.8.16). A declared rate below the real one only lengthens detection: at 25 Hz the `0x262` timeout is 0.2 s plus one task period, slightly above the 0.2 s of TSR-401 if the real rate is that low. A declared rate above the real one would block engagement permanently, which is why `0xB4` (no known rate) is not added. Both rates are to be confirmed by OI-2.

**Verification (host only):** safety suite OK in the default and reference variants with 100 % line coverage; new test `test_reference_rx_checks` (bad checksum rejected; no engagement with either message missing); `test_rx_timeout_5_periods_each_msg` covers both messages in the reference variant; mutations (rate 25 → 26 Hz, checksum ignored on `0x1D3`, `0x262` removed) each fail tests; opendbc and panda MISRA clean. Safety replay and HIL not run.
