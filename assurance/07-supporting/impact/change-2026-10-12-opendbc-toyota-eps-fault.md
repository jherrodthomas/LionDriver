# Change impact: LKA actuation refused while the EPS reports a fault (reference build)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins opendbc `242d63d` (merge commit of opendbc#7 on the fork's `master`); reporting (§6) at panda `877730e`, opendbc `adcb7c2`; not yet verified on the vehicle or on hardware (HIL bench D-04); not reviewed independently** |
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
| Cause reported (§6) | `pandaState.epsFault` follows the envelope's state; `pandad` logs each change | Drive logs: `epsFault` intervals against the host's `steerFaultTemporary/Permanent` |

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
| OI-2 | Closed 2026-10-12: reported to the host (§6) | — |
| OI-3 | Closed 2026-10-12: siren on a persistent EPS fault (§7) | — |
| OI-4 | Confirm the 1 s persistence threshold against EPS fault durations in reference logs (temporary codes during message drop-out) | Integration |

## 6. Follow-on change: EPS fault reported to the host (opendbc#8, panda#11)

[jherrodthomas/opendbc#8](https://github.com/jherrodthomas/opendbc/pull/8) (`242d63d..adcb7c2`) and [jherrodthomas/panda#11](https://github.com/jherrodthomas/panda/pull/11) (`52cad44..877730e`), integrated together with the host side in LionDriver.

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| opendbc `6d80176` | `opendbc/safety/declarations.h`, `safety.h`, `modes/toyota.h`, tests | The EPS fault state is kept in the global `safety_eps_fault` (cleared on every mode change) instead of a Toyota-local static. No behaviour change | Yes | No | No | No | TSR-110 (report) | WP-S-02, WP-W-02 | Safety suite both variants, 100 % line coverage; MISRA | Taken (maintainer merged, 2026-10-12) |
| panda `53b1a8b` | `board/health.h`, `board/main_comms.h`, `python/__init__.py`, `tests/hitl/test_12_rx_timeout.py`, `tests/hitl/test_13_eps_fault.py` (new) | Health flag `HEALTH_FLAG_EPS_FAULT` (bit 10) mirrors `safety_eps_fault`; struct layout unchanged. HIL test 12 sends EPS_STATUS and PCM_CRUISE_2 with `REFERENCE_BUILD=1` (required since opendbc `98404a4`); new HIL test 13 | Yes | No | No | No | TSR-110 (report) | WP-V-05 (HIL cases) | Builds (all variants), MISRA, host tests; HIL tests 12 and 13 | Taken (maintainer merged, 2026-10-12) |
| LionDriver | `openpilot/cereal/log.capnp`, `openpilot/selfdrive/pandad/pandad.cc` | `pandaState.epsFault` (field 44) set from the flag; `pandad` logs each change (error on onset, warning on clearing). No alert or engagement logic changes | No (QM host) | No | No | No | TSR-110 (report) | WP-S-05 (S-12) | Unit tests, process replay | This change |

Verification: opendbc safety suite OK in both variants with 100 % line coverage, MISRA clean; panda builds, MISRA and host tests pass; `log.capnp` loads with the new field. HIL tests 12 and 13 **not run** (D-04).

## 7. Follow-on change: siren on a persistent EPS fault (panda#14)

[jherrodthomas/panda#14](https://github.com/jherrodthomas/panda/pull/14) (`8aa8671..b790fca`).

Decision (2026-10-12, project maintainer): the siren sounds only for an EPS fault that **persists 1 s while authority is granted**; shorter faults (temporary codes during a message drop-out) do not sound it, so that the driver does not learn to ignore it. A maintainer decision, not an independent review (WP-M-06).

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `6a7f2fb` | `board/drivers/eps_fault_siren.h` (new), `board/drivers/drivers.h`, `board/main.c`, `tests/eps_fault_siren/` (new) | In the 100 Hz safety task: once `safety_eps_fault` has been set for 1 s while `controls_allowed`, the panda's own siren sounds for at least 3 s and is re-triggered while the fault persists. Reset on every safety mode change. Starts ≤ 1 s + 10 ms + 125 ms after the fault onset (8 Hz speaker tick). Only the reference build sets `safety_eps_fault` | Yes | Yes (driver warned of a lasting loss of lateral support) | No | No | SG-02, SG-06; FSR-02.05, FSR-06.05 | WP-S-02 (TSR-516), WP-W-02 (SWSR-516), WP-S-05 (S-12), WP-V-05 (siren on EPS fault) | Host tests; panda builds and MISRA; HIL: EPS fault held > 1 s while engaged → siren audible | Taken (maintainer merged panda#14, 2026-10-12) |

Verification (host only): `tests/eps_fault_siren` (constants; siren after 1 s; no siren for repeated short faults or when not engaged; 3 s hold after the fault clears or the driver disengages; persistence restarts after a clear); mutations (`&&` → `||`, hold not counted down, persistence not reset) each fail tests; panda builds in four variants (`-Werror`) and MISRA (standard and reference) clean. HIL **not run**: the siren is not in the health packet, so the bench check is audible or with a scope on the speaker line.

*Note 2026-10-13 (correction):* the start time above (≤ 1 s + 10 ms + 125 ms, about 1.14 s) assumed the speaker sounds on every 8 Hz tick. `main.c` drives it only on odd ticks (`set_siren((loop_counter & 1U) && ...)`), so the worst case is 1 s + 10 ms + 2 × 125 ms ≈ 1.26 s after the fault onset (≤ 0.26 s after the end of the 1 s persistence). Corrected in WP-S-04 T-28 and OI-8, WP-M-02 OI-9 and the documents that quote the figure; the row above is kept as recorded on 2026-10-12. The code is unchanged.
