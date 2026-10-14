# WP-C-07 Functional Modifications Addressing SOTIF Risk

| Field | Value |
|---|---|
| Work product | WP-C-07 Functional modifications addressing SOTIF risk |
| Standard reference | ISO 21448:2022 §8 (functional modifications addressing SOTIF-related risks); ASPICE 4.0 SYS.2 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF (some modifications also support FSRs in WP-C-04) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose

This document specifies functional modifications (FM-nn) that reduce the SOTIF risk identified in [WP-C-05](WP-C-05-sotif-hazard-identification.md) and [WP-C-06](WP-C-06-sotif-insufficiencies-triggering-conditions.md). Each modification states what changes, why, which code is affected, the expected risk reduction, how it is verified, and its priority.

**No code is changed by this document.** Each FM is implemented through a change request under [WP-P-02](../07-supporting/WP-P-02-change-management.md), with impact analysis against the safety-relevant file list ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)). Requirements derived from FMs go into [WP-S-01](../03-system/WP-S-01-system-requirements.md) / [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (TSR-6xx for host-side monitoring).

Priority: **P1** = needed before any LionDriver on-road operation beyond WP-V-07 safety-driver testing; **P2** = needed before G5 release; **P3** = improvement, decide at G2.

## 2. Summary

| FM | Title | Addresses | GAP | Priority |
|---|---|---|---|---|
| FM-01 | Experimental Mode off and locked in the reference configuration | SH-09, SH-04, SH-03 | GAP-18 | P1 |
| FM-02 | Exclude Chestnut big model; remove diagnostic masking | SH-01, SH-02, SH-04 | GAP-17 | P1 |
| FM-03 | No actuation on stale or failed inputs during soft disable | SH-02, SH-06 | GAP-16 | P1 |
| FM-04 | React to cruiseMismatch; correct canError text; fault on non-finite commands | SH-05, SH-02 | GAP-19 | P1 |
| FM-05 | DM source validity and wheel-touch fallback hardening | SH-12 | GAP-21 | P1 |
| FM-06 | Lock out debug, maneuver, joystick and DM demo modes | SH-12, SH-13 | GAP-20 | P1 |
| FM-07 | Enforce the ODD speed bound | SH-13 | GAP-19 | P2 |
| FM-08 | Road-type / construction ODD restriction (if feasible) | SH-13, SH-01 | — | P3 |
| FM-09 | ML action plausibility and uncertainty monitor | SH-01, SH-04, SH-06 | GAP-22 | P2 |
| FM-10 | Reduced, speed-dependent lateral authority | SH-01, SH-02 | GAP-04 | P2 |
| FM-11 | Restrict auto-resume from standstill | SH-03, SH-11 | — | P2 |

## 3. Modifications

### FM-01 Experimental Mode off and locked (GAP-18)

| Attribute | Content |
|---|---|
| Change | In reference-configuration builds: default `ExperimentalMode` to `"0"`; disable the toggle in the UI; ignore a stored `"1"` (treat as Chill). Matches the recommendation in [WP-C-02 §6.4](WP-C-02-odd-and-intended-functionality.md) (maintainer decision pending, D-08) |
| Rationale | Experimental Mode was made default upstream without hazard assessment; its UI text ("stopping for red lights … Mistakes should be expected") contradicts `docs/LIMITATIONS.md:35`; it raises cruise acceleration to 2.0 m/s² and adds false-stop behaviour (FI-05) |
| Affected code | `openpilot/common/params_keys.h:43`; `openpilot/selfdrive/ui/layouts/settings/toggles.py:48-185`; consumer `openpilot/selfdrive/controls/lib/longitudinal_planner.py:135-145` |
| Expected risk reduction | Removes SH-09 from scope and the e2e contribution to SH-03/SH-04 |
| Verification | Unit test of default and lock; configuration review of release build; process replay shows `experimentalMode = false` |
| Priority | P1 |

### FM-02 Exclude Chestnut; no diagnostic masking (GAP-17)

| Attribute | Content |
|---|---|
| Change | (a) Exclude the big-model / eGPU path from reference builds (model selection forced to the on-device model; WP-C-01 OI-4). (b) Independently of (a), remove the masking of `commIssue`, `posenetInvalid`, `locationdTemporaryError` and `modeldLagging` during model load: instead, prevent engagement (no-entry) while loading. (c) A model failure while engaged leads to immediate take-over request, not a hot switch to a cold model while actuating |
| Rationale | Diagnostics are masked while the system may be engaged; the hot-switch runs a model with zero recurrent state (FI-15, FI-22) |
| Affected code | `openpilot/selfdrive/selfdrived/selfdrived.py:169-176, 349-350, 380-384, 403, 457`; `openpilot/selfdrive/modeld/modeld.py:49, 234-235, 266-283, 411-419`; `openpilot/selfdrive/modeld/helpers.py:11-44` |
| Expected risk reduction | Removes TC-22 as a trigger; restores fault detection coverage for SH-01/SH-02 |
| Verification | Code review; fault-injection test (kill model, delay model output) in process replay; check that no diagnostic is masked while `enabled` |
| Priority | P1 |

### FM-03 No actuation on stale or failed inputs during soft disable (GAP-16)

| Attribute | Content |
|---|---|
| Change | Split soft-disable causes into (i) *degradation* causes, where control inputs remain valid (thermal, disk, memory), which keep the 3 s warning period, and (ii) *input-loss* causes (commIssue on modelV2/longitudinalPlan/carState, processNotRunning of a control-path process, posenet/locationd invalid), which lead to immediate take-over request with torque ramp-down and ACC cancel. Add a freshness check in `controlsd` on `modelV2` and `longitudinalPlan` with a bound derived from the FTTI (WP-S-04), independent of the 10× alive window |
| Rationale | Today the system keeps actuating up to ≈3.5 s on the inputs that failed (FI-14); at 30 m/s about 100 m |
| Affected code | `openpilot/selfdrive/selfdrived/state.py:7-8, 38-51`; `selfdrived.py:384-390`; `openpilot/selfdrive/controls/controlsd.py:66, 122-127`; `cereal/messaging/__init__.py:152-153` (no change; reference) |
| Expected risk reduction | Bounds actuation on invalid inputs to the freshness bound; supports FSR-02.02, FSR-06.02 |
| Verification | Process-replay fault injection (drop/stall each input); HIL test of take-over timing; FTTI analysis |
| Priority | P1 |

### FM-04 cruiseMismatch reaction, canError text, non-finite commands (GAP-19)

| Attribute | Content |
|---|---|
| Change | (a) `cruiseMismatch`: on persistence, warn and repeat PCM cancel; if it persists, immediate-disable alert and lockout until restart. Reduce the 6 s delay to a value justified by analysis. (b) `canError`: alert text describing a CAN communication fault. (c) Non-finite actuator values: raise an immediate-disable event (keep the clamp to 0 as the substitute value) |
| Rationale | FI-17; supports FSR-05.06, FSR-06.04 |
| Affected code | `openpilot/selfdrive/selfdrived/selfdrived.py:417-421`; `events.py:458-460, 928-936`; `controlsd.py:140-147` |
| Expected risk reduction | Removes TC-30 as unhandled; correct driver information on CAN faults |
| Verification | Unit tests on event mapping; replay with injected PCM mismatch and NaN |
| Priority | P1 |

### FM-05 DM source validity and wheel-touch fallback (GAP-21)

| Attribute | Content |
|---|---|
| Change | (a) Set `driverStateV2.valid` from real checks (frame age, model execution success, non-finite outputs) instead of `True`. (b) In wheel-touch fallback, restore awareness only on a deliberate input (steering torque above a threshold for a minimum time, not any gas or tiny torque), and cap how often wheel-touch can restore awareness within a window. (c) Add tests for DM data loss and for fallback abuse |
| Rationale | FI-19; TC-25 (defeat devices, small periodic inputs) |
| Affected code | `openpilot/selfdrive/modeld/dmonitoringmodeld.py:99`; `openpilot/selfdrive/monitoring/policy.py:77-78, 307-308, 334-335`; `openpilot/selfdrive/monitoring/test_monitoring.py` |
| Expected risk reduction | Reduces SH-12 duration; supports FSR-02.07 |
| Verification | Unit tests; DM clinic (WP-C-08 §8) with defeat-attempt scenarios |
| Priority | P1 |

### FM-06 Lock out debug, maneuver, joystick and DM demo modes (GAP-20)

| Attribute | Content |
|---|---|
| Change | In reference builds: ignore `JoystickDebugMode`, `LongitudinalManeuverMode`, `LateralManeuverMode`; do not subscribe `controlsd` to `lateralManeuverPlan`; `IsDriverViewEnabled` must not put DM into demo mode while onroad (only allowed offroad, and forces no-entry) |
| Rationale | One local parameter can replace control processes or neutralise DM (FI-20) |
| Affected code | `openpilot/system/manager/process_config.py:34-47, 95-109`; `controlsd.py:123-124`; `openpilot/selfdrive/monitoring/dmonitoringd.py:26-27`; `policy.py:428-437`; `common/params_keys.h:59` |
| Expected risk reduction | Removes TC-26; supports FSR-02.08 |
| Verification | Configuration review; test setting each parameter onroad shows no effect / no-entry |
| Priority | P1 |

### FM-07 Enforce the ODD speed bound

| Attribute | Content |
|---|---|
| Change | (a) Above the ODD bound (120 km/h, WP-C-02 §3.1): warning, then soft disable if the speed is not reduced within a set time. (b) Above `MAX_CTRL_SPEED` (≈149 km/h): soft disable instead of warning only. (c) Limit the maximum set speed to the ODD bound |
| Rationale | FI-16; TC-20 (model outputs unpredictable above training distribution, per code comment `events.py:988`) |
| Affected code | `openpilot/selfdrive/car/car_events.py:126`; `events.py:989-996`; `openpilot/selfdrive/car/cruise.py:12`; `opendbc_repo/opendbc/car/interfaces.py:23-24` |
| Expected risk reduction | Removes the high-speed part of SH-13 |
| Verification | Unit tests; vehicle test on closed course |
| Priority | P2 |

### FM-08 Road-type / construction ODD restriction (if feasible)

| Attribute | Content |
|---|---|
| Change | Investigate options: (a) offline map with road class to give a no-entry or take-over request outside ODD-H/ODD-A; (b) use model outputs (road edge, lane-line probabilities) to detect missing markings and warn. Decide feasibility at G2 |
| Rationale | No ODD monitor exists (WP-C-02 §5); construction zones and unmarked roads are TCs (TC-05, TC-06) |
| Affected code | New component; inputs from `modelV2` (`fill_model_msg.py`) and GNSS (`locationd`) |
| Expected risk reduction | Reduces exposure to TC-05/TC-06; size unknown until feasibility |
| Verification | To be defined if adopted |
| Priority | P3 |

### FM-09 ML action plausibility and uncertainty monitor (GAP-22)

| Attribute | Content |
|---|---|
| Change | Add a monitor between the driving model and controls that checks: (a) desired curvature against vehicle-dynamics plausibility and the road geometry the model reports (path vs lane lines vs road edges consistency); (b) model-reported uncertainty (std of path and lead) against thresholds; (c) temporal consistency (sudden jumps). On violation: warning, and for sustained violation a take-over request. The monitor is QM (TSR-6xx) but must be specified, tested and validated |
| Rationale | No confidence or OOD gating of the control action (FI-03); supports AC-03 |
| Affected code | `openpilot/selfdrive/modeld/fill_model_msg.py`; `controlsd.py:122-127`; `longitudinal_planner.py:132-149`; new monitor module |
| Expected risk reduction | Earlier take-over requests in TC-01…TC-05, TC-31; size to be measured on replay data |
| Verification | Replay on fork-owned logs: true/false alarm rates; scenario tests (WP-V-03) |
| Priority | P2 |

### FM-10 Reduced, speed-dependent lateral authority

| Attribute | Content |
|---|---|
| Change | Implement the speed-dependent torque limit from [WP-C-04 §4.2](WP-C-04-functional-safety-concept.md#42-recommendation) (FSR-01.01) in the envelope, and set controller limits below it with margin (FSR-01.14). Adjust the ODD curve bound (WP-C-02 §3.2) to the resulting capability |
| Rationale | Bounds the consequence of FI-01/FI-03 lateral errors (SH-01) to a controllable level; also the FuSa strategy |
| Affected code | `opendbc_repo/opendbc/safety/modes/toyota.h:171-185`; `opendbc_repo/opendbc/safety/lateral.h`; `opendbc_repo/opendbc/car/toyota/values.py:20, 45-47` |
| Expected risk reduction | Reduces severity/controllability of SH-01; may increase SH-02 frequency (less authority in curves) — must be balanced |
| Verification | Vehicle characterization; controllability tests (WP-C-08 §8); safety tests in opendbc |
| Priority | P2 |

### FM-11 Restrict auto-resume from standstill

| Attribute | Content |
|---|---|
| Change | After standstill longer than a set time (e.g. 3 s, to be justified), require a driver resume action instead of auto-resume; never auto-resume when no lead vehicle was present at stop |
| Rationale | FI-12, TC-27 (VRU crossing between ego and lead) |
| Affected code | `opendbc_repo/opendbc/car/toyota/interface.py:107`; `opendbc_repo/opendbc/car/toyota/carcontroller.py:175-185`; `openpilot/selfdrive/car/car_events.py` (`resumeRequired`) |
| Expected risk reduction | Reduces HE-03.2-type events from the intended function |
| Verification | Vehicle test; replay |
| Priority | P2 |

## 4. Residual items not addressed by modification

| SH / TC | Treatment |
|---|---|
| SH-06 stationary vehicles (TC-08), SH-11 VRUs (TC-12), SH-10 lane change (TC-28) | Driver responsibility, user information ([WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md)), DM, ODD restriction. Residual risk evaluated in WP-V-03/WP-V-04 |
| Weather and lighting (TC-01…TC-04) | ODD restriction plus FM-09; validation |

## 5. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Maintainer decision on FM-01 (linked to D-08) and FM-02 (WP-C-01 OI-4) | Maintainer | G1 |
| OI-2 | Raise change requests for P1 FMs under WP-P-02 | SW lead | G1 |
| OI-3 | Derive TSR-6xx requirements for FM-03, FM-04, FM-05, FM-06, FM-09 in WP-S-02 | Safety engineer | G2 |
| OI-4 | Feasibility study for FM-08 | SW lead | G2 |
| OI-5 | Re-run WP-C-06 evaluation after FMs are implemented | SOTIF lead | G4 |
