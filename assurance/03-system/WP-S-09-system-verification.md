# WP-S-09 System Verification (Qualification)

| Field | Value |
|---|---|
| Work product | WP-S-09 System verification (qualification) specification and report |
| Standard reference | ISO 26262-4:2018 §7 (integration and testing at vehicle level, verification of the technical safety requirements and of AoU on external measures); ISO 21448:2022 §10 (verification of the SOTIF-related functions, interface to WP-V-03); ASPICE 4.0 SYS.5 (system verification) |
| Version | 0.1 |
| Status | Draft (specification). **Results: not yet executed** |
| ASIL / scope | ASIL D (SG-01, until re-rated under FSC option (c)), ASIL C (SG-03…SG-05), ASIL B (SG-02, SG-06, SG-07); reference configuration (2020 Corolla LE, `TOYOTA_COROLLA_TSS2`) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); test specification review with independence per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document specifies the verification of the integrated item **in the reference vehicle**, against the technical safety requirements, the system requirements, and the assumptions of use on existing vehicle elements (EPS, PCM, cluster, PCS), as ISO 26262-4 §7 (vehicle-level testing) and ASPICE SYS.5 require. It also defines the regression verification of each release on recorded data (process replay, safety replay).

| In scope | Out of scope (where it is covered) |
|---|---|
| Vehicle-level verification on a closed course (VS-SQ-01…-15) | Bench integration ([WP-S-08](WP-S-08-system-integration-test.md)) |
| AoU characterisation of EPS, PCM, cluster and PCS (AOU-01R…05R, AOU-12) | Driver controllability studies with a participant panel and safety validation ([WP-V-01](../06-validation/WP-V-01-safety-validation.md), [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) §8) |
| Regression on recorded data (VS-SQ-16…-18) | SOTIF scenario evaluation ([WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md), [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md)) |
| Supervised public-road endurance verification after G1 (VS-SQ-19) | Fault-injection campaign detail ([WP-V-05](../06-validation/WP-V-05-fault-injection.md)) |

Verification versus validation: this document checks that the item meets its specified requirements and that the AoUs it relies on hold for the reference vehicle. Whether the safety goals are adequate and achieved at vehicle level for real drivers is validated in WP-V-01.

**Requirement references.** Cases trace to FSRs, AoUs and the TSRs of [WP-S-02](WP-S-02-technical-safety-requirements.md) (Draft v0.1). System requirements are those of [WP-S-01](WP-S-01-system-requirements.md) (Draft v0.1, SYS-nnn).

## 2. Preconditions

| ID | Precondition | Source |
|---|---|---|
| PC-01 | WP-S-08 steps I-1…I-4 passed for the version under test, or failures are known GAPs accepted for closed-course testing by the safety manager | WP-S-08 §5 |
| PC-02 | Vehicle test operations procedure approved; trained safety driver; closed course booked; for VS-SQ-19, G1 passed | [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md); WP-M-01 §9 |
| PC-03 | Reference vehicle recorded (VIN, ECU firmware versions) and unchanged since recording | WP-C-01 OI-1 |
| PC-04 | Device, harness and firmware configuration items recorded; release (not debug) panda build | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md); GAP-25 |
| PC-05 | Test-specific firmware or host builds (used to inject out-of-range commands) are separate configuration items, used only on the closed course, and removed after the test | WP-P-10 |

## 3. Methods and environment

| Aspect | Specification |
|---|---|
| Methods | Requirements-based test; characterisation (measurement of an AoU parameter with uncertainty); boundary-value test at envelope limits; back-to-back regression on recorded data; long-duration observation |
| Environment | Closed course with straight section ≥ 1 km, constant-radius curve(s) (to be specified per test, e.g. R ≈ 250 m and 500 m), dry asphalt; optional wet section for VS-SQ-06 |
| Vehicle instrumentation | Steering-wheel torque/angle measurement (steering robot or torque wheel), IMU/GNSS reference (lateral position and acceleration), pedal force sensors, CAN logger on bus 0 and bus 2 with hardware timestamps, video of cluster and device, audio capture |
| Item logs | openpilot `rlog`/`qlog` with panda health and safety counters |
| Targets | Soft target (balloon car or equivalent) for PCS tests (VS-SQ-07) |
| Recorded-data regression | Fork-owned Corolla drive logs; `openpilot/selfdrive/test/process_replay/test_processes.py` with fork-owned references (reference URL currently comma storage, `test_processes.py:70`, GAP-30); `opendbc_repo/opendbc/safety/tests/safety_replay/replay_drive.py`; `openpilot/selfdrive/test/process_replay/model_replay.py` |
| Test injection on vehicle | Out-of-range or fault commands only through a closed-course test build of the host; the release panda envelope stays in place unless the case states otherwise |

## 4. Pass criteria conventions

- **GC-1** (all cases): no actuation frame outside the envelope limits on bus 0 (from the CAN log).
- **GC-2** (all cases): stock PCS frames forwarded unchanged when not intercepted by design.
- Characterisation cases (VS-SQ-01, -02, -05) pass when the parameter is measured with stated uncertainty and the measured value satisfies the corresponding AoU. If it does not, the AoU stays uncredited and the HARA rating stays as it is (D-09; WP-C-03 OI-1); the FSC design input is revisited — this is a result, not a test failure.
- Timing criteria use the WP-C-04 §8 budget until [WP-S-04](WP-S-04-timing-ftti-budget.md) is approved.

## 5. Verification specification

### 5.1 Vehicle-element characterisation (AoU)

| ID | Title | Trace | Procedure (summary) | Pass criteria |
|---|---|---|---|---|
| VS-SQ-01 | EPS LKA torque authority | AOU-01R, FSR-01.13; TSR-111; input to TSR-102 | At standstill and at 30/60/90/110 km/h on a straight: command LKA torque steps up to the envelope maximum (1500 raw) with the release envelope; measure steering-wheel torque, rack response and lateral acceleration. Repeat across the range of raw values to obtain raw→Nm mapping | Mapping raw→Nm and max EPS-delivered torque recorded per speed; max ≤ T_EPS value required by AOU-01R; repeatability documented. Input to the physical limit derivation (GAP-04) |
| VS-SQ-02 | EPS timeout and request-bit behaviour | AOU-01R, FSR-01.13; TSR-111, TSR-109 | (a) While applying torque, stop `0x2E4` (test host build stops sending); (b) clear the steer-request bit with torque non-zero; (c) send implausible frames (bad checksum) | Time to LKA torque removal t_EPS measured for (a)–(c); fade profile recorded; EPS fault state reported on `EPS_STATUS`. Compare with the ≈1.5–2 s code comment (`opendbc_repo/opendbc/car/toyota/carstate.py:15-16`) |
| VS-SQ-03 | Envelope-bounded worst case: lateral deviation | FSR-01.01, FSR-01.02; TSR-101, TSR-102, TSR-103; SG-01 | With the test host build, command the worst case allowed by the envelope (max torque at max rate, both directions) for the FTTI and beyond, at each speed, hands near but not on the wheel until the safety-driver intervention cue | Lateral deviation and lateral acceleration over time recorded per speed; within the values used to derive the limit and the FTTI (WP-S-04). Input to WP-V-01 controllability tests |
| VS-SQ-04 | Brake override | AOU-03R, FSR-05.01, FSR-05.07; TSR-302, TSR-310 | Engaged with positive accel commanded; driver applies brake at three pedal forces | Vehicle decelerates per pedal input regardless of `0x343`; envelope blocks actuation within ≤ 0.2 s of the brake frame; PCM drops ACC |
| VS-SQ-05 | PCM ACC envelope and cancel | AOU-05R, FSR-03.06, FSR-04.03; TSR-206, TSR-208 | Test host build with envelope bounds temporarily set wider **only in a closed-course test firmware** (documented, PC-05): command accel above +2.0 and below −3.5 m/s²; command inactive value from steady decel; set cancel bit | PCM clamp values measured; inactive value gives coasting without a deceleration step above the FSR-04.02 bound; cancel honoured within a measured time |
| VS-SQ-06 | Stock PCS preserved | AOU-04R, FSR-07.01, FSR-07.04; TSR-704, TSR-708, TSR-709; SG-07 | Soft-target approach at PCS-relevant speeds in four states: item off (harness only), item on not engaged, engaged openpilot longitudinal, engaged with gas override | PCS warning and braking occur in all states with timing equal (within tolerance) to a baseline without harness; PCS messages on bus 0 identical to camera output (GC-2); `stockAeb`/`stockFcw` raised on the device (FSR-07.05) |
| VS-SQ-07 | Cluster cruise indication independence | AOU-12, FSR-05.05; TSR-309 | Engage/disengage via stalk, brake, cancel; also inject `0x412` variations from the test host | Cluster cruise indicator follows PCM state only; not influenced by `0x412` content beyond the LKA HUD fields |

### 5.2 Item behaviour on the vehicle (TSRs)

| ID | Title | Trace | Procedure (summary) | Pass criteria |
|---|---|---|---|---|
| VS-SQ-08 | Engagement and disengagement end-to-end | FSR-01.05, FSR-05.01, FSR-05.02, FSR-05.05; TSR-301, TSR-302, TSR-303, TSR-309; SYS-040, SYS-041, SYS-042, SYS-080 | Engage with stalk at several speeds (incl. standstill per WP-C-01 OI-7); disengage by brake, cancel, main-switch off | Engagement only on PCM edge; release ≤ 0.2 s; device HMI, cluster and envelope state agree (no mode confusion) |
| VS-SQ-09 | Gas override | FSR-04.04, FSR-05.04; TSR-203, TSR-305; SYS-042 | Press gas while engaged during decel and during follow | Only inactive accel sent while gas pressed; lateral continues; on release, longitudinal resumes without a step above the jerk bound |
| VS-SQ-10 | Steering override | FSR-05.03; TSR-304 | Driver steers against commanded torque at three force levels | Commanded torque reduced to not oppose the driver within ≤ 0.2 s. **Expected to fail until GAP-02 is closed** |
| VS-SQ-11 | Accel / decel limits and jerk on vehicle | FSR-03.01…03.03, FSR-04.01, FSR-04.02; TSR-201…TSR-205; SYS-022, SYS-024, SYS-026 | Follow a lead target that brakes/accelerates; cut-out of the lead; test host build requests limit-exceeding values (envelope in release form) | Achieved vehicle accel within derived bounds; jerk within bound; GC-1 |
| VS-SQ-12 | SoC loss while driving | FSR-01.07, FSR-02.05; TSR-407, TSR-408, TSR-510, TSR-516; SG-02 | On the straight and in a curve at 60 km/h: kill pandad (test build trigger), then freeze the SoC (SIGSTOP of all onroad processes) | Authority revoked after > 0.3 s without heartbeat (TSR-407) or > 50 ms without `0x2E4` (TSR-408); panda acoustic warning ≤ 0.5 s after detection (TSR-516); driver retakes control without lateral deviation beyond the bound. **Expected to fail timing (GAP-06)** |
| VS-SQ-13 | Fault-induced lateral safe-state transition in a curve | FSR-02.03, FSR-02.04; TSR-109, TSR-601, TSR-606; HE-02.1; SYS-081, SYS-082 | Constant-radius curve at speed: trigger (a) an "untrusted command" fault (immediate SS-L) and (b) a "planned" fault (soft disable ramp) via test host build | Warning precedes or coincides with torque reduction; (a) torque zero at once; (b) ramp per FSR-02.04; lateral deviation recorded; input to WP-C-08 §8 controllability |
| VS-SQ-14 | Longitudinal safe-state transition | FSR-04.03, FSR-06.02; TSR-206, TSR-601, TSR-606; SYS-081 | At 50/90 km/h in steady follow: trigger longitudinal fault; observe inactive value and cancel | Deceleration step ≤ jerk bound; warning ≤ 1 s; ACC cancelled |
| VS-SQ-15 | Driver monitoring escalation and lockout | FSR-02.06…02.09 (QM); TSR-608…TSR-612; SYS-060, SYS-062, SYS-063 | Closed course, safety driver simulates distraction per WP-C-08 scripts | Alerts at 5/8/13 s (vision) and wheel-touch fallback timings (`openpilot/selfdrive/monitoring/policy.py:31-36`); no-response force decel and lockout (`policy.py:39-44`) |

### 5.3 Regression on recorded data

| ID | Title | Trace | Procedure (summary) | Pass criteria |
|---|---|---|---|---|
| VS-SQ-16 | Process replay regression | TSR-601…TSR-618 (regression); SYS-001…SYS-008, SYS-020…SYS-026 (regression) | Run `test_processes.py` for controlsd, plannerd, radard, dmonitoringd, calibrationd, locationd, paramsd, torqued against fork-owned references of the previous release | No unexplained differences; each explained difference has an approved change request |
| VS-SQ-17 | Safety replay of the full Corolla log set | FSR-01.xx…07.xx; TSR-101…TSR-110, TSR-201…TSR-207, TSR-301…TSR-311, TSR-401…TSR-406 | Run `safety_replay/replay_drive.py` over all fork-owned logs with the release safety model | Zero TX violations from the release host; every `controls_allowed` transition explained by a PCM/brake event |
| VS-SQ-18 | Controller margin to envelope | FSR-01.14; TSR-605; WP-A-03 DFI-08; SYS-120 | From the replay of VS-SQ-17, compute the distribution of commanded torque, torque rate and accel relative to the envelope limits | Commanded values stay below the margin target (e.g. ≤ 90 % of envelope bound) in ≥ 99.9 % of frames; time at the bound recorded. **Expected to fail today** (identical limits, `opendbc_repo/opendbc/car/toyota/values.py:20-21`) |

### 5.4 Long-duration verification

| ID | Title | Trace | Procedure (summary) | Pass criteria |
|---|---|---|---|---|
| VS-SQ-19 | Supervised endurance drive | All SG; TSR-1xx…TSR-7xx (observation); SYS-001, SYS-003, SYS-004, SYS-008, SYS-020, SYS-022, SYS-081, SYS-120, SYS-140, SYS-141 | After G1, under WP-V-07: drive a defined mileage across the ODD with a safety driver; log everything | No GC-1/GC-2 violation; every disengagement and alert classified (driver-initiated, fault, ODD exit); no unexplained envelope intervention; no panda fault flags; problem reports for all anomalies. Mileage target set in [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) |

## 6. Coverage

| Requirement group | Cases |
|---|---|
| AoU on external elements (AOU-01R…05R, AOU-12) | VS-SQ-01, -02, -04…-07 |
| TSR-101…TSR-111 lateral | VS-SQ-01…-03, -13, -17, -18 |
| TSR-201…TSR-208 longitudinal | VS-SQ-05, -09, -11, -14, -18 |
| TSR-301…TSR-311 engagement/override | VS-SQ-04, -07, -08, -10 |
| TSR-401…TSR-413 communication | VS-SQ-12, -17 |
| TSR-501…TSR-516 MCU platform | Bench only (WP-S-08, WP-H-06, WP-V-05); VS-SQ-12 (TSR-510, -516); VS-SQ-19 observes fault flags |
| TSR-601…TSR-618 host monitoring | VS-SQ-13…-16, -18 |
| TSR-701…TSR-710 PCS / harness | VS-SQ-06 (TSR-704, -708, -709); others on the bench |
| System requirements (WP-S-01) | SYS-001…008: VS-SQ-16, -19; SYS-020…027: VS-SQ-11, -16, -19; SYS-040…043: VS-SQ-08, -09; SYS-060…063: VS-SQ-15; SYS-080…083: VS-SQ-08, -13, -14; SYS-120: VS-SQ-18, -19; SYS-140, -141: VS-SQ-19. Not covered here: SYS-005/006 (lane change), SYS-027, SYS-043, SYS-061, SYS-083, SYS-100…102, SYS-121, SYS-142…145 (OI-6) |

## 7. Report (template)

| Field | Value |
|---|---|
| Report ID | WP-S-09-R-nn |
| Item version | LionDriver tag; openpilot/opendbc/panda commits; panda firmware hash; model hashes |
| Vehicle | VIN; ECU firmware versions (fingerprint output) |
| Test site, date, weather, surface | |
| Safety driver / tester / reviewer (independence) | |

| Case | Version under test | Result (Pass / Fail / Fail known GAP / Characterised) | Measured values (with uncertainty) | Deviations | Problem report | Evidence (log hash, video ref) |
|---|---|---|---|---|---|---|
| VS-SQ-01 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-02 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-03 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-04 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-05 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-06 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-07 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-08 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-09 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-10 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-11 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-12 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-13 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-14 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-15 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-16 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-17 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-18 | — | **Not yet executed** | — | — | — | — |
| VS-SQ-19 | — | **Not yet executed** | — | — | — | — |

Summary (to complete after execution): AoU verdicts and whether they support a HARA re-rating (D-09); TSR coverage achieved; open problem reports; release recommendation input to [WP-K-06](../10-safety-case/WP-K-06-release-record.md).

## 8. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Re-check TSR and SYS references when WP-S-01/WP-S-02 leave Draft | Safety engineer | G2 |
| OI-2 | Define the closed-course test builds (host and panda) for VS-SQ-02, -03, -05, -12, -13 as configuration items, including how they are prevented from reaching public-road use | Maintainer | Before first closed-course session |
| OI-3 | Specify course geometry and speeds per case from the FTTI derivation (WP-S-04) | Safety engineer | G2 |
| OI-4 | Run VS-SQ-01, -02, -04, -05, -06 early (G1): they are the only route to a lower HARA rating (D-09) and decide the envelope strategy (WP-C-04 OI-2) | Safety engineer | G1 |
| OI-5 | Fix the margin target for VS-SQ-18 together with the derived limits (TSR-605) | Safety engineer | G2 |
| OI-6 | Add verification cases for the WP-S-01 requirements listed as not covered in §6, or allocate them to WP-S-08 / WP-V-03 | Test lead | G2 |
