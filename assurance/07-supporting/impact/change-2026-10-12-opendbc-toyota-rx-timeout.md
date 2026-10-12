# Change impact: Toyota RX timeout of 5 periods in the envelope

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Draft: proposed change, not integrated.** The LionDriver `opendbc_repo` pin is unchanged |
| Change request | [jherrodthomas/opendbc#1](https://github.com/jherrodthomas/opendbc/pull/1) |
| Range | opendbc `229dc70..de80b63` (branch `claude/toyota-rx-timeout`); LionDriver pin stays at `229dc70` until the change is merged to the fork's `master` |
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

Not covered: TSR-306. Authority can still be granted on a PCM rising edge between two ticks while a message is lagging, for at most one task period (10 ms).

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
| Mutation check | Toyota threshold 5 → 6 fails 7 tests |
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
| OI-1 | Run safety replay on Toyota routes (reference vehicle first) and record any false timeouts | Integration |
| OI-2 | Confirm the declared RX rates against measured rates (WP-S-05 OI-7) | Integration |
| OI-3 | Add `0x262`, `0x1D3` and `0xB4` to the RX check set (TSR-110, TSR-401) | Later change |
| OI-4 | HIL fault injection: remove each RX message and measure the time to revocation | Release |
