# Change impact: panda pin to `8a69ccf` and opendbc pin to `4d1a056`, siren on a TX-arrival revocation (DQ-404 A)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-20** in this LionDriver PR; host-tested; not verified on hardware; not reviewed independently |
| Pins | opendbc `e233362` → `4d1a056` (merge commit of [jherrodthomas/opendbc#21](https://github.com/jherrodthomas/opendbc/pull/21), change commit `0ff85e6`); panda `bf8102a` → `8a69ccf` (merge commit of [jherrodthomas/panda#20](https://github.com/jherrodthomas/panda/pull/20), change commit `3f5d5a2`). The panda change needs the opendbc one: both pins move together |
| Decision | Register DQ-404, project lead, 2026-10-19, option A: sound the existing siren when authority is revoked because openpilot stopped (missing command frames or heartbeat), not on a driver disengagement. The documents were changed in #339 (WP-S-02 v0.41 TSR-516(b), WP-S-04 v0.17, WP-C-04 v0.18); the firmware change was open. Implementation confirmed by the lead in chat on 2026-10-20 ("Yes, all three"). Reusing the 3 s heartbeat-loss siren, rather than adding a new sound, is Claude's choice (reversible) |
| Requirement | TSR-516(b), SWSR-516(b) (now names SWSR-408 as a trigger), FSR-02.05 |
| Reference configuration affected | Yes: the TX-arrival check exists only in the reference build, so only the reference build sets the new flag; in other builds the flag stays false and nothing changes |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| opendbc `0ff85e6` | `opendbc/safety/safety.h`, `declarations.h`, `tests/libsafety/safety.c`, `tests/test_toyota.py` | New `safety_tx_arrival_revoked`: true in the `safety_tick()` in which the TX-arrival check (TSR-408) revokes granted authority, false otherwise; cleared on every safety mode change. Revocation itself unchanged | Yes (input to the siren) | No | No | No | WP-S-04 T-34 | WP-W-02 SWSR-516 | opendbc safety tests (both builds), MISRA, coverage, mutation | DQ-404 A |
| panda `3f5d5a2` | `board/drivers/heartbeat_siren.h`, `drivers.h`, `main.c`, `tests/heartbeat_siren`, `tests/hitl/test_12_rx_timeout.py`, `test_14_tx_rate.py`, `test_15_heartbeat_siren.py` | `heartbeat_siren_tick()` also starts the 3 s siren in the task in which the arrival check revoked granted authority. Whichever of TSR-408 and TSR-407 revokes first sounds it, once. HIL tests now send the SoC's actuation frames (`SocSim`), which the heartbeat and TX-rate tests lacked: on the reference build the arrival check would have revoked at 50 ms and failed them | Yes (a full SoC stall is no longer silent) | Yes (sirens where there were none, see §3) | No | No | HE-07.1, HE-02.4, HE-02.6; SG-01, SG-02, SG-06; WP-S-04 T-34 | WP-S-02 TSR-516, WP-W-02 SWSR-516, WP-S-04 (T-07a, T-28, T-34, §5), WP-C-04 FSR-02.05, `assurance/sim` | panda host tests, panda MISRA, plant simulation | DQ-404 A |
| this PR | `opendbc_repo`, `panda`, the work products above, `assurance/sim/plant/sim_panda.c` (follows `main.c`), `simulate.py` and `silent_stall.py` (what-if inverted; the register figure for DQ-404 is left as the lead saw it), `fig_sim_he.py` (HE-02.2 and HE-07.1 roles), `search/search.py` (fault text), `test_fig_sim_plots.py` (count), sim results and figures | Pins; records state the implemented siren; the silent-stall study now compares the build as built with a muted panda (the behaviour before this change) | — | — | — | — | — | — | — | — |

## 2. Verification results

| Check | Result |
|---|---|
| opendbc safety tests (local) | Full `opendbc/safety/tests` suite passes in both builds (reference build: 3390 tests). `test_tx_arrival_supervision` checks the flag in the revoking tick for each supervised frame; `test_tx_arrival_revoked_only_by_arrival_check`: not set on brake, cruise off, RX fault, or missing frames while not engaged |
| opendbc and panda MISRA (local) | cppcheck MISRA C:2012 clean in both builds for opendbc; panda H7 clean in both builds, run with the host gcc include path because the ARM toolchain is not installed locally (CI runs the real script) |
| panda host tests (local) | All six suites pass; `tests/heartbeat_siren` 12 tests. Three of the four new tests fail when the siren ignores the flag; the driver-disengagement test passes either way, as intended |
| Plant simulation (local) | F-04b: siren 0.25 s after the stall (none before). Silent-stall study, 110 km/h: at the ODD curve bound the driver corrects at 1.79 s instead of 2.68 s, peak offset 1.84 m instead of 7.28 m; inside the ODD 0.83 m instead of 3.64 m. The siren comes 0.25–0.29 s after the stall, not within one speaker tick as the what-if in DQ-404 assumed, because the speaker sounds on every other 8 Hz tick; at the curve bound the result is therefore a little worse than the 1.5 m shown when the lead decided. Synthetic, no evidence credit |
| Other plant cases (local) | Because the arrival check counts only accepted frames (SWSR-408), every case in which the modelled host keeps sending frames the envelope refuses now sounds the siren 0.25 s after the fault: F-01a (torque over the limit), F-06a (switch to pass-through), F-07 (EPS fault; 0.75 s before, from the persistence path), L-02 and L-04 (longitudinal request over the envelope). TSR-516(b) requires a siren for each of these revocations. `plant-results.md` regenerated |
| Failure search and HE figures (local) | Curve assist-loss search (EPS fault, F-07): 71 of 120 samples leave the lane instead of 92; mildest departing curve a_y = 0.51 m/s² (0.44 before), sharpest held 1.05 m/s² (0.42). HE-02.1 and HE-07.1: siren 0.29 s, correction 1.79 s, body still on the lane line at 1.97 s at R_ODD. HE-02.2 (rural curve, 80 km/h): siren 0.30 s, the car now stays in its lane. In the EPS-fault runs the earlier siren comes from the host model keeping its torque request through the fault, which the real host does not do (OI-2); the 0.7 s persistence path is then the one that sounds. HE figure spec, search text, plot test counts, sim README, WP-S-04 §3.9 and OI-2 updated |
| B2B and other generated checks (local) | `b2b_toy_auth.py --all --gate` passes; scope plots and the L2 steering-column study change only in the pinned SHA they name |
| HIL | **Not run** (D-04). `test_15_heartbeat_siren.py` has a new SoC-stall case; the siren is confirmed by ear |

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | HIL on the bench: `test_15` stall case (revocation from the arrival check, siren by ear) and the heartbeat cases with the frames now sent (WP-S-04 M-05) | HIL bench (D-04) |
| OI-2 | Short EPS faults: the real host stops requesting torque when it sees a temporary steer fault (`controlsd` `latActive`). If its reaction from the first fault frame to a frame without steer request takes more than 50 ms, the arrival check revokes and the siren sounds on fault blips that the 0.7 s persistence was chosen to ignore (decision 2026-10-12, DQ-048). Measure that lag in reference logs; only if it exceeds 50 ms, put the trade-off to the lead | Vehicle logs (WP-C-08) |
| OI-3 | Analyses that still state a silent SoC stall or the EPS-fault siren at 0.75–0.8 s in simulation, for their owners: System FMEA F-04b rows (`system-fmea.yaml`), WP-S-03 §5 status text, the Blender scenes and dashboards ("SoC stall (no alert)", `sim/blender/scenes.yaml`; rendered clips) | Analysis revisions; next render |
| OI-4 | SW FMEA: the new flag and its use in the siren as a cause and control row (SW FMEA owner) | SW FMEA revision |
