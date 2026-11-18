# Change impact: the minimum-risk stop brakes at 2 m/s², ramped in (DQ-424 A)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). When the driver does not respond to the terminal driver-monitoring alert, the item stops in its lane and holds the car (TSR-633, DQ-365 A). The stop was only `v_cruise = 0` on the planner's cruise candidate, so it slowed at upstream's gentlest cruise rate, `A_CRUISE_MIN` = −1.2 m/s², ramped in at the cruise jerk limit (0.73 m/s³ at 110 km/h) and tapering below 1.2 m/s: 27.3 s and 413 m from 110 km/h in the planner (SW FMEA SWF-086.C2, O 8 D 8, AP H). The lead chose 2 m/s², ramped in within j_down (register DQ-424, option A, 2026-10-30), and TSR-633 states it. This change implements that in the planner.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-11-02** in this LionDriver PR; unit-tested and mutation-checked (run locally, and in CI on the PR); not verified on the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/selfdrive/controls/lib/longitudinal_planner.py`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)); QM test data (`tools/ci/host_mutants.toml`) |
| Reference configuration affected | Yes, and every other platform with openpilot longitudinal control: the planner is common code |
| Decision | DQ-424 A (the lead, vehicle behaviour; 2026-10-30) |
| Requirements | TSR-633 ([WP-S-02](../../03-system/WP-S-02-technical-safety-requirements.md) v0.66: stop rate implemented in software and unit-tested, not verified on the vehicle); bounded by TSR-202 (a_min), TSR-205 and TSR-624 (j_down). No SWSR derives TSR-633 yet (WP-W-02 owner, OI-1) |
| Author / reviewer (independence) | Claude (AI-assisted draft, I0) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Stop rate | `openpilot/selfdrive/controls/lib/longitudinal_planner.py` | New constants `A_MINIMUM_RISK_STOP = -2.0` (m/s², comment citing TSR-633 and DQ-424) and `J_MINIMUM_RISK_STOP = 4.0` (m/s³). The planner recognises the minimum-risk stop as `controlsState.forceDecel` together with `selfdriveState.minimumRiskManeuver` (the selfdrived latch). Only then the cruise candidate targets −2.0 m/s² at every speed down to standstill (no taper as the speed falls) and moves towards it by at most 4 m/s³ × 0.05 s = 0.2 m/s² per planner step. Otherwise `get_cruise_accel` runs exactly as before: the new argument defaults to off, and normal cruise and the fault soft-disable slow-down (which forces the deceleration without the latch) keep `A_CRUISE_MIN` and `J_CRUISE` | `test_minimum_risk_stop.py` (below) |
| Tests | `openpilot/selfdrive/controls/tests/test_minimum_risk_stop.py` (8 tests, collected by the `unit_tests` job) | The real `LongitudinalPlanner` with the reference Corolla TSS2 parameters, closed over a plant that follows its output (as the longitudinal maneuver plant). See §3 | 8 passed |
| Mutation | `tools/ci/host_mutants.toml` MS-1..MS-7 (88 host mutants in all) | Stop not recognised; recognised from `forceDecel` alone (soft disable brakes at 2 m/s²) or from the latch alone (normal cruise slows); 3 m/s²; no ramp; tapered rate; not passed to the cruise candidate | each killed by `tools/ci/host_mutation.py --only MS-n` |

Where the stop runs and what each part does:

| Stage | Code | Part in the stop | Changed |
|---|---|---|---|
| DM policy | `selfdrive/monitoring/policy.py` | `noResponseForceDecel` 5 s after the terminal alert | No |
| selfdrived | `selfdrive/selfdrived/minimum_risk.py` | latch `minimumRiskManeuver` until the driver takes over | No |
| controlsd | `selfdrive/controls/controlsd.py:236-239` | `forceDecel` from the DM request, the latch, or a soft disable; sets `CC.driverMonitoringEscalation`, which the Toyota port does not read | No |
| Planner | `selfdrive/controls/lib/longitudinal_planner.py` | `v_cruise = 0`; since this change, the stop rate and ramp while the latch is set | **Yes** |
| Toyota car controller | `opendbc_repo/opendbc/car/toyota/carcontroller.py:22, 27` | request rate limit 4 m/s³ (`ACCEL_WINDDOWN_LIMIT`), final command limit 4.5 m/s³, clip at ACCEL_MIN; keeps standstill requested while the planner does not ask to move | No: the 4 m/s³ ramp is the same as its request limit, so it is passed on |
| Envelope | panda `toyota.h` | ACCEL_CMD ≥ a_min = −3.5 m/s² (TSR-202); no jerk check (GAP-04) | No |

## 2. Impact

- **Safety (SG-08, H-09):** the time an unresponsive driver rides at speed falls from about 27 s to 15.5 s from 110 km/h, and the stop distance from about 410 m to 240 m. The deceleration is an ordinary braking level and stays inside a_min with 1.5 m/s² to spare.
- **Following traffic (HZ-006, SG-04):** a firmer stop than before, ramped at 4 m/s³, below the provisional j_down of 5 m/s³; the alert sounds through it (TSR-624). The lead weighed this in DQ-424 (option C, 3 m/s², was declined for this reason).
- **Lead vehicle braking:** the planner still takes the lowest of the candidates, so a lead that needs harder braking gets it from the MPC up to ACCEL_MIN, as before.
- **Normal driving:** unchanged. The new branch runs only while the latch and the forced deceleration are both set; `get_cruise_accel` without it is shown equal, value for value, to upstream's formula (§3).
- **Fault soft disable:** unchanged at −1.2 m/s² for at most 3 s before control is handed back (TSR-624 rationale).
- **Other platforms:** the same rate applies wherever openpilot longitudinal control runs the minimum-risk stop; the reference build only enables the reference Corolla.
- **Process replay:** see §4.
- **Upstream:** a fork difference to carry at each openpilot sync (WP-M-11); upstream has no minimum-risk latch.

## 3. Test results (2026-11-02, local run)

The openpilot environment was built here for the purpose: Python 3.12 with the locked dependencies in a scratch environment, and `scons` of `msgq_repo`, `openpilot/cereal`, `openpilot/common` and the longitudinal MPC (acados). CI builds the same with `tools/op.sh setup` and `scons`.

| Test | Checks | Result |
|---|---|---|
| `test_stop_time_and_distance_from_110_kmh` | after 2 s of steady cruise, standstill from 110 km/h; closed form 15.53 s and 241.0 m (0.5 s ramp at 4 m/s³, then 2 m/s²); planner loop within 0.25 s and 2 % | 15.55 s, 239.5 m |
| `test_ramps_in_and_holds_the_rate_to_standstill` | first step above −1 m/s² (no step); exactly −2.0 m/s² from the end of the ramp to standstill | pass |
| `test_within_a_min_and_j_down` | from 110 km/h, 25, 10 and 3 m/s, and while still accelerating to the set speed: never below −2.0 m/s² (so above a_min = −3.5), onset never faster than j_down = 5 m/s³ (largest 4.0 m/s³) | pass |
| `test_constants_inside_the_envelope` | a_min < −2.0 < A_CRUISE_MIN; 0 < 4 < j_down | pass |
| `test_cruise_accel_is_upstream_without_the_stop` | `get_cruise_accel` equals upstream's formula exactly over 1 344 input combinations, with the new argument absent and off | pass |
| `test_soft_disable_slows_at_a_cruise_min` | forced deceleration without the latch settles at −1.2 m/s² | pass |
| `test_latch_flag_alone_does_not_slow_the_car` | the latch flag without the forced deceleration gives a trace identical to no flag | pass |
| `test_normal_slow_down_at_a_cruise_min` | a lower set speed slows at most at −1.2 m/s² | pass |
| Existing: `test_longitudinal.py` (maneuvers, with and without forced deceleration, e2e and ACC), `selfdrive/controls/tests/`, `test_minimum_risk.py`, `tools/ci/test_host_mutation.py` | unchanged behaviour | 83 passed, 2 skipped |

The kinematic check is of the planner's output with an ideal actuator. It does not model the PCM's response, the Toyota PID and pitch terms, the road grade or the car's own lag; those are T-33 on the vehicle.

## 4. Process replay

`test_processes.py --whitelist-procs plannerd` against comma's reference logs (`ref_commit` 655bfde), run here on 2026-11-02: both segments that replay `plannerd` (Hyundai `regenAA0FC4ED71E`, Toyota `regen218A4DCFAA1`) show no difference, so the planner output of normal segments is unchanged. No reference segment sets `selfdriveState.minimumRiskManeuver` (a LionDriver field). The other processes do not read the planner's constants; the full replay runs in the CI `process_replay` job on the PR.

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | SWSR for the stop rate under TSR-633 in WP-W-02, which its owner edits. Proposed row, not entered: "SWSR-633 \| While `selfdriveState.minimumRiskManeuver` is set and `controlsState.forceDecel` is on, the longitudinal planner shall request 2.0 m/s² of deceleration at every speed down to standstill, approached from its previous request at no more than 4 m/s³ (below j_down, TSR-205), and never beyond a_min (TSR-202); without the latch it shall keep the cruise and fault soft-disable rates. \| A (TSR-633; allocated to the QM SoC, open: WP-C-04 OI-11) \| TSR-633 \| `host.plannerd` \| UT, VT \| From 110 km/h with an ideal actuator: standstill within 0.25 s of 15.5 s and 2 % of 240 m; never below −2.0 m/s²; onset ≤ 4 m/s³ \| Implemented: `longitudinal_planner.py` (`A_MINIMUM_RISK_STOP`, `J_MINIMUM_RISK_STOP`), `test_minimum_risk_stop.py`, mutants MS-1..MS-7; vehicle test T-33 open" | SW requirements owner |
| OI-2 | Vehicle verification T-33 (WP-S-04 §4, M-plan): the stop from speed on the reference Corolla, deceleration against a_min and j_down on the bus (`0x343`) and in the car, stop time and distance, the hold at standstill (AOU-16) | G3 |
| OI-3 | End-to-end test from an unresponsive-driver input to standstill through policy, controlsd and plannerd (SWF-ACT-073) | SW FMEA owner |
| OI-5 | The synthetic plant model still slows the driver-monitoring stop to `A_CRUISE_MIN` at the cruise jerk rate (`assurance/sim/plant/simulate.py:94, 506-507`), and the handover-follower search result describes it so (`assurance/sim/results/search-handover-follower.md`). Model the stop at `A_MINIMUM_RISK_STOP` and `J_MINIMUM_RISK_STOP` and rerun that search; the soft-disable case is unchanged. Synthetic, no credit either way | Simulation owner |
| OI-4 | The DQ-424 option B estimate (25 s, 390 m at a constant 1.2 m/s²) understated the old stop: the planner took about 27 s and 410 m, because of the slow cruise ramp and the taper near standstill. No decision rests on it | Register owner (note only) |
