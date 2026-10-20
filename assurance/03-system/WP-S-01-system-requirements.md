# WP-S-01 System Requirements Specification (Functional, Non-Safety)

| Field | Value |
|---|---|
| Work product | WP-S-01 System requirements specification (functional, non-safety) |
| Standard reference | ASPICE 4.0 SYS.2; ISO 21448:2022 §5 (specification of the intended functionality); ISO 15622, ISO 22179, ISO 11270 as informative performance references |
| Version | 0.5 (lead answers of 2026-10-18: SYS-040 refuses engagement outside the assured settings (DQ-221 A); SYS-041 refuses engagement below a highway speed floor (DQ-280 A); 2026-10-18). 0.4 (§10.1 allocation of every SYS requirement to architecture elements, read by the SysML model; SYS-027 updated for the Chill-mode default; 2026-10-14). 0.3 (reference configuration named by generation, E210; 2026-10-12). History: 0.2 (status update 2026-10-12: SYS-120 metric excludes frames refused by design in the reference build; SYS-121 evidence lists the health fields added at `bf6ce8c`). 0.1 |
| Status | Draft |
| ASIL / scope | QM / SOTIF (safety requirements are in [WP-S-02](WP-S-02-technical-safety-requirements.md)) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer |
| Baseline | `bf6ce8c` (status update 2026-10-12; opendbc `7993399`, panda `b790fca`). Originally `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document specifies the functional and performance requirements (SYS-nnn) of LD-SDA for functions F-01…F-09 of the [item definition (WP-C-01 §2.1)](../02-concept/WP-C-01-item-definition.md), within the ODD of [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md). These requirements describe **what the system should do well**. What it must never do is specified as TSRs in [WP-S-02](WP-S-02-technical-safety-requirements.md); where a SYS requirement and a TSR touch the same quantity, the TSR wins and the SYS value must sit inside it with margin (TSR-605).

Many targets need data that LionDriver does not yet have (fork-owned drive logs, vehicle characterisation, user studies). Such targets are marked **TBD** with the rationale and the activity that will set them. A TBD is not an accepted requirement; it blocks G2 for its function unless the maintainer accepts it as an open item.

### 1.1 Attributes

| Attribute | Values |
|---|---|
| Type | F functional, P performance, I interface, H HMI, C constraint |
| Verif | A analysis, R review, T-SIL software test / process replay, T-HIL bench test, T-VEH vehicle test, LOG analysis of drive logs, SIM scenario simulation |
| Status | all `Proposed` |
| SOTIF link | validation target or functional modification it supports ([WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md), [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md)) |

Paths are under `openpilot/` unless prefixed.

## 2. F-01 Lateral control (lane centring, assisted lane change)

| ID | Requirement | Type | Target / criterion | Verif | Current implementation | Rationale for TBD |
|---|---|---|---|---|---|---|
| SYS-001 | While lateral control is active on a straight or curved road inside the ODD, the system shall keep the vehicle near the lane centre. | P | Lateral offset from lane centre: p95 ≤ **TBD** (proposed 0.3 m), p99.9 ≤ **TBD** (proposed 0.6 m) per stratum | LOG, T-VEH | Model `action.desiredCurvature` → `selfdrive/controls/controlsd.py:120-131` → torque controller (`selfdrive/controls/lib/latcontrol_torque.py`) | Needs ground-truth lane offset on fork-owned logs; aligned with AIR-01 in [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) |
| SYS-002 | The commanded lateral acceleration shall not exceed 3.0 m/s² (roll-compensated) and the lateral jerk shall not exceed 5 m/s³. | C | as stated | T-SIL | `selfdrive/controls/lib/drive_helpers.py:9-14, 28-42` | — |
| SYS-003 | The system shall follow curves down to the radius R_ODD = v²/2.5 m/s² at the travel speed without saturating the steering command. | P | No `steerSaturated` in curves ≥ R_ODD in ≥ **TBD** % of passes | T-VEH, LOG | `selfdrive/selfdrived/selfdrived.py:435-443` (saturation event) | Depends on the reduced torque authority of TSR-102; may force R_ODD to grow ([WP-S-04](WP-S-04-timing-ftti-budget.md) OI-2) |
| SYS-004 | When the steering command saturates, the system shall warn the driver ("Turn Exceeds Steering Limit"). | H | Warning within ≤ 1 s of saturation | T-SIL | `selfdrive/selfdrived/events.py` steerSaturated | — |
| SYS-005 | An assisted lane change shall start only after the driver activates the turn signal **and** applies steering torque in the same direction, above 20 mph. | F | as stated | T-SIL | `selfdrive/controls/lib/desire_helper.py:8-10` | — |
| SYS-006 | An assisted lane change shall complete or be cancelled within 10 s of the turn signal; it shall be cancelled when the turn signal is released. | F | 10 s | T-SIL | `LANE_CHANGE_TIME_MAX = 10` (`desire_helper.py:9`) | — |
| SYS-007 | Lateral control shall not be active at standstill and shall resume without a steering jump when the vehicle moves off. | F | Torque change at resume within TSR-103 rate | T-SIL | `controlsd.py:100-101`; curvature reset when inactive `controlsd.py:120-127` | — |
| SYS-008 | Lateral control shall not cause oscillation (weaving) on a straight road. | P | Lateral offset spectral peak 0.2–2 Hz below **TBD** | LOG, T-VEH | Torque controller with learned parameters (`torqued`, `lagd`) | Metric and threshold need data |

## 3. F-02 Longitudinal control (ACC with stop-and-go)

| ID | Requirement | Type | Target / criterion | Verif | Current implementation | Rationale for TBD |
|---|---|---|---|---|---|---|
| SYS-020 | The system shall hold the set speed within ±**TBD** km/h on level road without a lead. | P | proposed ±2 km/h | T-VEH | `selfdrive/controls/lib/longitudinal_planner.py` | Grade effects need measurement |
| SYS-021 | The set-speed range shall be the PCM cruise set range of the reference vehicle, and shall not exceed the ODD speed bound of 120 km/h (ODD-H) / 90 km/h (ODD-A). | C | as stated | R, T-VEH | Toyota set speed from PCM (pcm cruise); openpilot cap `V_CRUISE_MAX = 145` km/h (`selfdrive/car/cruise.py:12`); engagement allowed to ≈ 149 km/h (`opendbc_repo/opendbc/car/interfaces.py:23-24`) | System-side enforcement of the ODD bound is FM-07 ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)) |
| SYS-022 | When following a lead, the system shall keep a time gap equal to the selected personality: relaxed 1.75 s, standard 1.45 s, aggressive 1.25 s. | P | steady-state gap error ≤ **TBD** | T-VEH, LOG | `selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py:71-79` | Steady-state accuracy needs logs |
| SYS-023 | The default personality in the reference configuration shall be "standard" or "relaxed", not "aggressive". | C | as stated | R | Param `LongitudinalPersonality` | Decision in [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) |
| SYS-024 | The system shall bring the vehicle to a stop behind a stopping lead, keeping a stopped distance of about 6 m, and hold it at standstill. | F/P | stop distance 6 m ± **TBD** | T-VEH | `STOP_DISTANCE = 6.0` (`long_mpc.py:57`); standstill/permit braking `opendbc_repo/opendbc/car/toyota/carcontroller.py:179-186, 244-248` | — |
| SYS-025 | After a standstill, the system shall resume automatically when the lead moves off, within **TBD** s; without a lead, it shall not move off without a driver action. | F | as stated | T-VEH | Stop-and-go for TSS2 (`opendbc_repo/opendbc/car/toyota/interface.py:52, 107, 115`) | Resume latency needs measurement; resume-without-lead behaviour to be verified for HE-03.2 |
| SYS-026 | Comfort: in normal following, the commanded acceleration shall stay within the cruise limits (1.6→0.6 m/s² by speed, −1.2 m/s² cruise braking) and use stronger braking only for lead-following, down to −3.5 m/s². | P | as stated | T-SIL | `longitudinal_planner.py:19-22, 37-50, 149` | — |
| SYS-027 | Experimental Mode (end-to-end longitudinal) shall be disabled and not selectable in the reference configuration until decision D-08 includes it. | C | Param default "0", toggle disabled | R, T-SIL | Default "0" since 2026-10-14 (`common/params_keys.h:43`, B-06, decision register DQ-001); the toggle is still selectable | Not selectable: open (D-08 covers the default only) |

## 4. F-03 Engagement and mode management

| ID | Requirement | Type | Target / criterion | Verif | Current implementation | Rationale for TBD |
|---|---|---|---|---|---|---|
| SYS-040 | Engagement shall be possible only through the stock cruise controls and only when no no-entry condition is present. In the reference configuration a setting outside the assured values (`assured_config.py`: following distance other than relaxed, CA-011; Experimental Mode on; alpha longitudinal; a debug or maneuver mode) is a no-entry condition, with a no-entry alert that names the setting (decided 2026-10-18, DQ-221 A; SWF-067, SWF-ACT-063). | F | as stated | T-SIL, T-VEH | `selfdrive/selfdrived/state.py:79-90`. Settings outside the assured values are only logged today (`selfdrived.py:505-509, 611-631`); the no-entry is not implemented (code by the implementation spec) | — |
| SYS-041 | The system shall refuse engagement, with a no-entry alert, below the highway speed floor v_floor, and shall engage from v_floor up to the ODD speed bound. This is the entry check for the highways-only ODD (DQ-023) until road-type data exists (WP-C-07 FM-08). Once engaged, slowing below v_floor (traffic, stop-and-go) does not disengage. (Decided 2026-10-18, DQ-280 A; STPA LS-13.) | F | v_floor = **TBD** (proposed 60 km/h) | T-SIL, T-VEH | Not implemented: `minEnableSpeed = -1` (`opendbc_repo/opendbc/car/toyota/interface.py:115`) allows engagement from standstill; code by the implementation spec | v_floor set with the ODD entry condition (WP-C-02) |
| SYS-042 | A brake press or cancel shall disengage; the accelerator shall override longitudinal control without disengaging (reference setting). | F | as stated | T-VEH | `selfdrived.py:258-261`; `DisengageOnAccelerator` default 0 (`common/params_keys.h:35`) | HMI decision in WP-C-08 |
| SYS-043 | After start-up, the system shall be ready to engage within **TBD** s of ignition on. | P | proposed ≤ 30 s | T-VEH | init waits for checks or 6 s (`selfdrived.py:479-480`) | Device boot time varies (`common/hardware/comma/hardware.py` `booted`) |

## 5. F-04 Driver monitoring

| ID | Requirement | Type | Target / criterion | Verif | Current implementation | Rationale for TBD |
|---|---|---|---|---|---|---|
| SYS-060 | Above 10 km/h, DM shall warn a visually distracted driver with escalating alerts at 5, 8 and 13 s (vision policy) or 5, 15 and 25 s (wheel-touch policy). | H | as stated | T-SIL, T-VEH | `selfdrive/monitoring/policy.py:29-36` | — |
| SYS-061 | DM classification performance shall meet AIR-07/AIR-08 of WP-C-11. | P | recall ≥ 95 % gaze-off > 2 s; false distraction ≤ 1/h (confirmed, WP-C-08 OI-2) | LOG | Model + policy thresholds `policy.py:54-77` | Needs labelled LionDriver data |
| SYS-062 | DM shall work in the ODD lighting conditions (day, dusk, night with IR) and with sunglasses, or fall back to the wheel-touch policy. | P | fallback triggered when uncertain; coverage **TBD** | T-VEH, LOG | `policy.py:82-83, 333-334` | Data |
| SYS-063 | On no response to the highest alert, the system shall slow the vehicle, disengage and lock out re-engagement (1/5/15/30 min). | F | as stated | T-SIL, T-VEH | `policy.py:44-49, 437`; `controlsd.py:204-205` | — |

## 6. F-05 Driver information and warnings (HMI)

| ID | Requirement | Type | Target / criterion | Verif | Current implementation | Rationale for TBD |
|---|---|---|---|---|---|---|
| SYS-080 | The engaged/disengaged state shall be shown continuously on the device and through the cluster cruise indicator and LKAS HUD. | H | as stated | T-VEH | `selfdrive/ui`; `0x412` LKAS_HUD (`opendbc_repo/opendbc/car/toyota/carcontroller.py`) | — |
| SYS-081 | An alert shall be displayed and its sound started within ≤ 0.2 s of the event being raised by `selfdrived`. | P | p99 ≤ 0.2 s | T-HIL | `selfdrive/selfdrived/alertmanager.py`, `selfdrive/ui/soundd.py` | Needs latency measurement (WP-S-04 M-10) |
| SYS-082 | Alert text shall describe the actual cause. | H | Review of every alert used in the reference configuration | R | `canError` mislabelled (`events.py:928-936`, GAP-19) | — |
| SYS-083 | Alerts and sounds shall be perceivable at highway noise levels. | P | sound level ≥ **TBD** dB(A) above cabin noise | T-VEH | `soundd` volume control | Measurement needed |

## 7. F-06 / F-07 Forward collision warning and lane departure warning

| ID | Requirement | Type | Target / criterion | Verif | Current implementation | Rationale for TBD |
|---|---|---|---|---|---|---|
| SYS-100 | FCW shall alert when the model predicts hard braking or the planner predicts a collision. | F | as stated | T-SIL | `selfdrived.py:446-450`; `selfdrive/modeld/fill_model_msg.py:142-147` | — |
| SYS-101 | FCW false alert rate shall be ≤ **TBD** per 1000 km. | P | TBD | LOG | — | Needs field data |
| SYS-102 | LDW shall warn when not laterally engaged, above 31 mph, with no turn signal in the last 5 s, when the vehicle drifts toward a visible lane line. | F | as stated | T-SIL | `selfdrive/controls/lib/ldw.py:7-35` | — |

## 8. F-08 Safety envelope (functional aspects)

The safety requirements of F-08 are TSR-1xx…7xx in [WP-S-02](WP-S-02-technical-safety-requirements.md). Non-safety requirements:

| ID | Requirement | Type | Target / criterion | Verif | Current implementation |
|---|---|---|---|---|---|
| SYS-120 | In normal operation inside the ODD, the envelope shall not reject any command produced by the SoC controller (no false interventions). | P | `safetyTxBlocked` increments per hour of engaged driving = 0 (excluding intentional tests, and excluding frames refused by design: STEERING_LKA frames refused by the EPS-fault gate at fault onset (TSR-110) and frames rejected by the TX rate supervision (TSR-518), reference build, added 2026-10-12) | LOG | Reported in `pandaStates` (`panda/board/main_comms.h:27`) |
| SYS-121 | The envelope shall report its mode, parameter, authority state, fault flags and counters to the SoC at ≥ 10 Hz. | I | as stated | T-HIL | health packet `panda/board/main_comms.h:9-55`; pandad 10 Hz (`selfdrive/pandad/pandad.cc:385-394`). 2026-10-12 (`bf6ce8c`): health flags and counter added and published in `pandaState`: `watchdogReset` (TSR-501), `requestsRejected` (counter, TSR-512/513), `epsFault` (TSR-110), `txRateExceeded` (TSR-518); not verified on hardware |

## 9. F-09 Logging, upload, remote access, update

| ID | Requirement | Type | Target / criterion | Verif | Current implementation | Rationale for TBD |
|---|---|---|---|---|---|---|
| SYS-140 | Every drive shall be logged in 60 s segments including CAN, `carControl`, `selfdriveState`, `pandaStates` and model outputs. | F | as stated | T-SIL | `system/loggerd/config.py:5`; services `cereal/services.py:21-95` | — |
| SYS-141 | Logs shall identify the software release, panda firmware version and model artefacts in use. | F | as stated | R | Partial; model identification is AIR-23 | — |
| SYS-142 | Segments flagged by the driver shall be preserved from automatic deletion. | F | as stated | T-SIL | `system/loggerd/deleter.py:16-43` (preserve attribute) | — |
| SYS-143 | Automatic deletion shall keep at least 5 GiB or 10 % of storage free. | C | as stated | T-SIL | `deleter.py:11-12` | — |
| SYS-144 | Uploads, remote access and software updates shall be configurable to the LionDriver policy and shall not run while onroad unless the policy allows it. | C | as stated | R, T-SIL | `updated` offroad only (`system/manager/process_config.py:114`); athena always (`process_config.py:71`) | Policy in [WP-S-07](WP-S-07-cybersecurity-requirements-architecture.md), [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |
| SYS-145 | With automatic updates disabled, the system shall not block engagement because of missing update connectivity. | F | as stated | T-VEH | `Offroad_ConnectivityNeeded` gate (`system/updated/updated.py:324-341`; `system/hardware/hardwared.py:349`, `DisableUpdates` honoured) | To be tested ([WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) OI-4) |

## 10. Traceability

| SYS | Function | Related TSR / SOTIF item |
|---|---|---|
| SYS-001…008 | F-01 | TSR-101…105, 605; SH-01, SH-02; AIR-01, AIR-11 |
| SYS-020…027 | F-02 | TSR-201…207, 605; SH-03, SH-04, SH-06, SH-09; D-08 |
| SYS-040…043 | F-03 | TSR-301…311 |
| SYS-060…063 | F-04 | TSR-608…612; SH-12; AIR-07, AIR-08 |
| SYS-080…083 | F-05 | TSR-606; WP-C-08 |
| SYS-100…102 | F-06, F-07 | QM (HARA §5.8) |
| SYS-120…121 | F-08 | TSR-108, 406, 615 |
| SYS-140…145 | F-09 | TSR-813; WP-O-04; WP-S-07 |

### 10.1 Allocation to architecture elements

Each requirement is allocated to the architecture elements that satisfy it, named as in the SysML model ([`assurance/models/sysml`](../models/sysml/README.md)): host processes `host.*`, the safety layer `E-03a` and platform firmware `E-03b`, and the grouped host parts `estimators`, `hardwared` and `remoteAndLogging` of WP-S-03 §8. The model turns each row into `satisfy` relationships and checks that every name resolves (check R2).

| SYS | Allocated to |
|---|---|
| SYS-001 | `host.modeld`, `host.controlsd` |
| SYS-002 | `host.controlsd` |
| SYS-003 | `host.controlsd`, `host.selfdrived` |
| SYS-004 | `host.selfdrived`, `host.hmi` |
| SYS-005 | `host.modeld` |
| SYS-006 | `host.modeld` |
| SYS-007 | `host.controlsd` |
| SYS-008 | `host.controlsd`, `estimators` |
| SYS-020 | `host.plannerd` |
| SYS-021 | `host.card` |
| SYS-022 | `host.plannerd` |
| SYS-023 | `host.manager` |
| SYS-024 | `host.plannerd`, `host.card` |
| SYS-025 | `host.card` |
| SYS-026 | `host.plannerd` |
| SYS-027 | `host.manager`, `host.hmi` |
| SYS-040 | `host.selfdrived` |
| SYS-041 | `host.card` |
| SYS-042 | `host.selfdrived` |
| SYS-043 | `host.selfdrived`, `hardwared` |
| SYS-060 | `host.dm` |
| SYS-061 | `host.dm` |
| SYS-062 | `host.dm` |
| SYS-063 | `host.dm`, `host.controlsd` |
| SYS-080 | `host.hmi`, `host.card` |
| SYS-081 | `host.selfdrived`, `host.hmi` |
| SYS-082 | `host.selfdrived` |
| SYS-083 | `host.hmi` |
| SYS-100 | `host.selfdrived`, `host.modeld` |
| SYS-101 | `host.selfdrived` |
| SYS-102 | `host.plannerd` |
| SYS-120 | `E-03a` |
| SYS-121 | `E-03b`, `host.pandad` |
| SYS-140 | `remoteAndLogging` |
| SYS-141 | `remoteAndLogging` |
| SYS-142 | `remoteAndLogging` |
| SYS-143 | `remoteAndLogging` |
| SYS-144 | `remoteAndLogging`, `host.manager` |
| SYS-145 | `remoteAndLogging`, `hardwared` |

## 11. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Set the TBD targets (SYS-001, 003, 008, 020, 022, 025, 043, 061, 062, 081, 083, 101) from fork-owned logs and vehicle tests | SW lead | G2 (or accepted as open at G2) |
| OI-2 | Confirm the reference-vehicle PCM set-speed range and stop-and-go behaviour (WP-C-01 OI-7) | Maintainer | G1 |
| OI-3 | Decide the default personality and `DisengageOnAccelerator` in WP-C-08 | Maintainer | G1 |
| OI-4 | Re-check SYS-003 after the reduced torque bound τ_max(v) is known | Safety engineer | G2 |
