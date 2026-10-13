# Change impact: CRUISE_ACTIVE checked against MAIN_ON (reference build)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins opendbc `875e325` (merge commit of opendbc#9 on the fork's `master`); not yet verified on the vehicle or on hardware (HIL bench D-04); not reviewed independently** |
| Change request | [jherrodthomas/opendbc#9](https://github.com/jherrodthomas/opendbc/pull/9) |
| Range | opendbc `adcb7c2..875e325` |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE`, non-SecOC Toyota with PCM_CRUISE_2); other builds and configurations are unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `8836b65` | `opendbc/safety/modes/toyota.h`, `opendbc/safety/tests/test_toyota.py` | PCM_CRUISE.CRUISE_ACTIVE (`0x1D2`) with PCM_CRUISE_2.MAIN_ON (`0x1D3`, bit 15) = 0 is invalid. Cruise becoming active while main is off clears `controls_allowed` at once; main going off while engaged revokes it once the disagreement has lasted more than 150 ms. The tolerance restarts whenever main is on again | Yes | Yes (engagement refused or ended on a disagreement) | No | Yes (a spoofed or corrupted CRUISE_ACTIVE without MAIN_ON does not engage) | SG-01, SG-03; FSR-01.06; GAP-01 | WP-S-02 (TSR-405), WP-W-02 (SWSR-405), WP-S-05 (S-13), WP-W-06 (unit test), WP-V-05 (FI) | Safety unit tests (both variants, 100 % line coverage); opendbc and panda MISRA; replay of reference logs (main switched off while engaged); vehicle test | Taken (maintainer merged opendbc#9, 2026-10-12) |

## 2. Tolerance

| Case | Expected disagreement | Reaction |
|---|---|---|
| Cruise becomes active while main is off | None in normal operation (the PCM requires main on to engage) | Immediate: no engagement |
| Driver switches main off while engaged | CRUISE_ACTIVE drops with MAIN_ON; the two messages (33 Hz each) can disagree for one or two frames | Revoke after 150 ms (about 5 periods); detection ≤ 0.2 s with one 30 ms frame of latency (TSR-405) |

Revoking when the driver switches main off is consistent with the host, which disengages when cruise ends. The 150 ms value is not yet confirmed against logs (OI-1).

## 3. Not implemented in this change

| Item | Reason |
|---|---|
| TSR-405(b): BRAKE_PRESSED `0x226` vs `0x1D3` | The meaning of the `0x1D3` bit is not known (DBC and host give no semantics). If it also reflects ACC braking, "treat as pressed on disagreement" would disengage during openpilot's own longitudinal braking and cause controls mismatches with the host. Needs reference logs (OI-2) |
| TSR-405(a): speed cross-check | `0xB4` not in the RX set (no nominal rate) |
| TSR-405(d): EPS-response check | Needs a plant tolerance from logs |

## 4. Verification results

| Check | Result |
|---|---|
| Safety unit tests, default and `LIONDRIVER_REFERENCE=1` | OK under UBSan and with coverage; 100 % line coverage (`toyota.h` 197/197 lines in the reference variant) |
| New test `test_cruise_active_with_main_off` | Pass. Immediate refusal; tolerance boundary (150 ms kept, 150 ms + 1 µs revoked); tolerance restart when main comes back on |
| Mutation check | Tolerance 150 → 200 ms (4 failures), MAIN_ON bit 15 → 14 (28), immediate refusal removed (4), check not run on `0x1D3` (8) |
| opendbc MISRA (cppcheck step) and panda `tests/misra/test_misra.sh` (standard and reference) | Clean |
| Replay, vehicle, HIL | **Not run** (no reference logs; GAP-30; D-04) |

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Confirm the 150 ms tolerance on reference logs: longest CRUISE_ACTIVE/MAIN_ON disagreement when the driver switches main off | Integration |
| OI-2 | Establish the meaning of `0x1D3` BRAKE_PRESSED on reference logs (driver pedal vs ACC braking) and implement TSR-405(b) | Later change |

## Addendum: further work products affected (2026-10-12)

The software alignment audit ([RR-2026-009](../../05-software/reviews/RR-2026-009.md) F-30) found that this change also affects: WP-W-05 (cruise-main check unit), WP-W-09 (150 ms tolerance). These were updated in the RR-2026-009 alignment change, not in the change above. The original "WPs affected" entries are left as recorded.
