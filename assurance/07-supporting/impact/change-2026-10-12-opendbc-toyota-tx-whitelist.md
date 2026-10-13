# Change impact: PCS and DSU messages removed from the Toyota TX whitelist

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins panda `9f60e17`, opendbc `aff4033`; follow-ups at panda `3859fa8`, opendbc `5b5a4ba` (merge commits on the forks' `master`); not yet verified on hardware (HIL bench D-04); not reviewed independently.** D-1 decided and implemented in the reference build (§2): opendbc#5, pin `5b5a4ba` |
| Change request | [jherrodthomas/opendbc#2](https://github.com/jherrodthomas/opendbc/pull/2) |
| Range | opendbc `229dc70..e089e85` (branch `claude/toyota-tx-whitelist`); independent of opendbc#1 |
| Reference configuration affected | Yes: the Toyota safety mode with openpilot longitudinal control runs on the reference device |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `e089e85` | `opendbc/safety/modes/toyota.h`, `opendbc/safety/tests/test_toyota.py` | The envelope no longer accepts from the SoC PRE_COLLISION_2 `0x344` (PCS brake triggers), the DSU bus-0 messages `0x2E6`, `0x2E7`, `0x33E`, `0x365`, `0x366`, `0x4CB` or the DSU bus-1 set `0x128`, `0x141`, `0x160`, `0x161`, `0x470`. PRE_COLLISION `0x283` stays with zero payload only (unchanged check). No openpilot code sends any removed ID (the only builder of `0x344`, `toyotacan.create_pcs_commands()`, has no caller), so host behaviour is unchanged | Yes | No | No | Yes (smaller TX surface from a compromised SoC) | SG-07; FSR-07.02; GAP-42; NF-07 | WP-S-02 (TSR-705 Impl), WP-W-02 (SWSR-705 status), gap assessment (GAP-42), WP-W-06 (new unit test), WP-A-02/WP-A-04 (SG-07 interference paths), TARA (spoofed PCS frames) | Safety unit tests with 100 % line coverage; opendbc and panda MISRA; process replay on Toyota routes (no blocked TX expected) | Take after review; D-1 decided separately |

## 2. Open decision

| # | TSR-705 requires | This change | Effect | Options |
|---|---|---|---|---|
| D-1 | PCS_HUD `0x411` not accepted, or restricted to the inactive value | Kept unchanged | The SoC can still write the PCS indicator, FCW and PCS-off bits shown on the cluster. The host sends `0x411` only when `DISABLE_RADAR` is set (radar-ACC TSS2 with alpha longitudinal). The reference Corolla TSS2 is camera-ACC and never sends it | (a) Remove it: the FCW HUD is lost on radar-ACC alpha-longitudinal Toyotas, outside the reference configuration. (b) Restrict content: the host frame is not the inactive value (`PCS_OFF=1`, FCW bit), so the host must change too. (c) Keep it as a documented exception in TSR-705, limited to `DISABLE_RADAR` configurations |

Recommendation: (a) for the reference release build, since the reference configuration never sends `0x411`.

Decision (2026-10-12, project maintainer): **(a) for the reference build.** Implemented in [jherrodthomas/opendbc#5](https://github.com/jherrodthomas/opendbc/pull/5) (opendbc `5b5a4ba`): with `LIONDRIVER_REFERENCE` defined, `0x411` is left out of the Toyota longitudinal TX whitelist; other builds keep it for radar-ACC cars with alpha longitudinal. The opendbc safety suite runs in both variants (test `test_pcs_hud`; LionDriver `safety.yaml` runs the reference variant with the 100 % coverage gate). A maintainer decision, not an independent review (WP-M-06).

## 3. Verification results

| Check | Result |
|---|---|
| Safety unit tests (`python -m unittest discover` in `opendbc/safety/tests`) | OK |
| Line coverage (gcovr, `--fail-under-line=100`) | 100 % |
| New test `test_pcs_and_dsu_messages_blocked` (every Toyota test class) | Pass; fails on the old whitelist (6 failures) |
| opendbc MISRA (cppcheck step of `tests/misra/test_misra.sh`) | Clean |
| panda `tests/misra/test_misra.sh` built against this tree | Clean |
| Process replay with Toyota routes | Not run in the session; CI process replay runs on the pin update |

## 4. Work products to update on integration

- WP-S-02 TSR-705 Impl column: met except `0x411` (D-1); regenerate `trace/items/tsr.yaml`.
- WP-W-02 SWSR-705 status; WP-W-06: add the unit test.
- Gap assessment: GAP-42 partly closed.

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Closed 2026-10-12: D-1 decided, (a) for the reference build (§2) | — |
| OI-2 | Check that no tool or fork feature outside `opendbc/car/toyota` sends the removed IDs (e.g. DSU emulation in community forks used for comparison) | Integration |

## Addendum: further work products affected (2026-10-12)

The software alignment audit ([RR-2026-009](../../05-software/reviews/RR-2026-009.md) F-30) found that this change also affects: WP-W-05 (UN-15 TX whitelist), WP-W-09 (CD-04 TX table), WP-W-11 (CSR-092). These were updated in the RR-2026-009 alignment change, not in the change above. The original "WPs affected" entries are left as recorded.
