# Change impact: LKA actuation refused while the EPS reports a fault (reference build)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins opendbc `242d63d` (merge commit of opendbc#7 on the fork's `master`); not yet verified on the vehicle or on hardware (HIL bench D-04); not reviewed independently** |
| Change request | [jherrodthomas/opendbc#7](https://github.com/jherrodthomas/opendbc/pull/7) |
| Range | opendbc `98404a4..242d63d` |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE`, Toyota LKA torque control); other builds and configurations are unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `338f5fc` | `opendbc/safety/modes/toyota.h`, `opendbc/safety/tests/test_toyota.py` | The RX hook reads EPS_STATUS.LKA_STATE (`0x262`, 8 bytes, bus 0). While it is in {0, 3, 9, 11, 17, 21, 25}, the TX hook refuses STEERING_LKA (`0x2E4`) frames with non-zero torque or STEER_REQUEST = 1; zero frames pass. The check runs before the torque limit checks, so a refused frame does not change their state. `controls_allowed` is not cleared: longitudinal control continues | Yes | Yes (lateral control unavailable while the EPS reports these codes) | No | No | SG-01, SG-02; FSR-02.01; GAP-03 | WP-S-02 (TSR-110), WP-W-02 (SWSR-110), WP-S-05 (S-12), WP-W-06 (unit test), WP-V-05 (EPS fault injection) | Safety unit tests (both variants, 100 % line coverage); opendbc and panda MISRA; replay of reference logs with EPS faults; vehicle test of an EPS temporary fault | Taken (maintainer merged opendbc#7, 2026-10-12) |

## 2. Fault code set

The set is `TEMP_STEER_FAULTS ∪ PERM_STEER_FAULTS` of `opendbc/car/toyota/carstate.py`, the codes on which the host already sets `steerFaultTemporary` / `steerFaultPermanent` and stops lateral control. The envelope and the host therefore stop on the same codes. The codes are reverse-engineered (comments in `carstate.py`); TSR-110 requires them to be confirmed for the reference EPS firmware.

| Code | Meaning (DBC / host comment) | Host | Envelope |
|---|---|---|---|
| 0 | initializing / catch-all | temporary | refuse |
| 1 | standby | — | allow |
| 3 | LKA message missing, unavailable | permanent | refuse |
| 5 | active | — | allow |
| 9 | temporary fault 2 (message drop-out) | temporary | refuse |
| 11 | LKA message missing, unavailable 2 | temporary | refuse |
| 17 | permanent fault (prolonged high driver torque) | permanent | refuse |
| 21 | (not in the DBC value table) | temporary | refuse |
| 25 | temporary fault | temporary | refuse |
| other | — | — | allow |

## 3. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| Host reaction lags the envelope | The envelope reacts on the `0x262` frame; the host after parsing it. One or two STEERING_LKA frames with torque may be refused at the onset of a fault and are counted in `safety_tx_blocked` | Replay of reference logs with EPS faults: count refused frames and confirm no controls mismatch |
| Code 0 refused | If the EPS reports 0 during normal LKA operation on the reference car, lateral control is unavailable in that state (the host behaves the same) | Reference logs: LKA_STATE histogram while engaged |
| Cause not reported | TSR-110 "report the cause" is not met; only the TX-blocked counter records it | Add a reason code with the next health packet change |

## 4. Verification results

| Check | Result |
|---|---|
| Safety unit tests, default and `LIONDRIVER_REFERENCE=1` | OK under UBSan and with coverage; 100 % line coverage (`toyota.h` 176/176 lines in the reference variant) |
| New test `test_eps_fault_blocks_lka` (LKA classes, reference variant) | Pass. Every LKA_STATE value 0…127; zero frames always pass; the fault clears on the next good frame; a refused frame does not widen the rate limit |
| Mutation check | Code 21 → 22, wrong LKA_STATE shift, steer request ignored, limit checks run before the gate: each fails tests |
| opendbc MISRA (cppcheck step) and panda `tests/misra/test_misra.sh` (standard and reference) | Clean |
| Replay, vehicle, HIL | **Not run** (no reference logs; GAP-30; D-04) |

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Confirm the fault code set on reference EPS logs (LKA_STATE values while engaged, during driver override and after message drop-out) | Integration |
| OI-2 | Report the cause to the host (health packet reason code) | Later change |
| OI-3 | Siren on EPS fault (TSR-516(b)) | Later change |
