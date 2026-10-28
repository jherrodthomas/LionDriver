# WP-V-01 Safety Validation

| Field | Value |
|---|---|
| Work product | WP-V-01 Safety validation plan, specification and report |
| Standard reference | ISO 26262-4:2018 §8 (safety validation); ISO 26262-3:2018 §6 (controllability basis), §7 (external measures, AoU); ASPICE 4.0 VAL.1. Informative: RESPONSE 3 Code of Practice for ADAS controllability assessment; ISO 11270, ISO 15622 |
| Version | 0.11 (RX timeout bound ≤ 0.162 s, was ≤ 0.16 s, as WP-S-04 v0.21 T-01 (161.5 ms: 5 periods of 30.3 ms plus one 10 ms task period); no requirement, budget or verdict changed; 2026-10-27). 0.10 (the lead's decisions applied: controllability pass limits fixed now from the concept drafts, VS-VAL-10 and -12 judged by the WP-C-08 §7.1 criteria, OI-3 closed, DQ-042 A; VS-VAL-10 runs to 110 km/h after the risk review the lead decided to hold, OI-7, DQ-091 A; test equipment bought in stages, OI-6, DQ-043 B; 2026-10-23). 0.9 (OI-4: the test-build procedure is WP-P-01 §7.1, DQ-125 A; 2026-10-22). 0.8 (VS-VAL-17 also covers the speed-dependent wheel-touch reminders, DMP-05, WP-C-08 §5.4, TSR-634; 2026-10-17). 0.7 (§5.2 supervision decided: the project lead supervises the human-subject tests with a written protocol and consent, no external human-factors reviewer, DQ-026; 2026-10-17). 0.6 (VS-VAL-07 parents corrected to H-01, H-04 and HE-04.2, the hazards AOU-10 is credited for in WP-C-01; 2026-10-13). 0.5 (§3 verification and validation hierarchy added as Figure 3-1; 2026-10-13). 0.4 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.3 (reference configuration named by generation, E210; 2026-10-12). 0.2 (verification status for the integrated envelope changes; 2026-10-12). 0.1 |
| Status | Draft (plan and specification). Report section is a template: **Not yet executed** |
| ASIL / scope | Up to ASIL C (SG-01), D if AOU-01/02 fail ([WP-C-03](../02-concept/WP-C-03-hara.md)) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); validation report reviewed as part of the functional safety assessment (I3) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `bf6ce8c` (status update 2026-10-12; opendbc `7993399`, panda `b790fca`) |

## 1. Purpose and scope

Safety validation provides evidence, at vehicle level on the reference configuration, that:

1. the safety goals SG-01…SG-08 are achieved by the integrated item (SG-08, the unresponsive driver, since WP-C-03 v0.4);
2. the controllability assumptions used in the HARA hold, in particular the assumptions of use on the vehicle (AOU-01, AOU-02, AOU-03, AOU-04, AOU-05) and the driver's ability to control the vehicle within the safety envelope;
3. the safety mechanisms are effective in the vehicle;
4. the external measures credited in the HARA and FSC (Toyota EPS LKA limiting, PCM ACC envelope, stock PCS) behave as assumed.

[WP-C-03 §6.1](../02-concept/WP-C-03-hara.md#61-observations-for-the-functional-safety-concept) notes that vehicle characterization of AOU-01/02/03/05 is a **G1** activity because the ASILs depend on it. Those test cases (§5.1) are therefore executed early, on the closed course, before the rest of the validation campaign (G5).

Relation to the concept phase: the AoU characterization of §5.1 provides the evidence for the refined assumptions AOU-01R…AOU-05R and the external-measure requirements FSR-01.13, FSR-03.06, FSR-05.07 and FSR-07.04 of [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md); §5.2 executes the controllability validation plan of [WP-C-08 §8](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) (steps V-1…V-6) against its assumptions CA-01…CA-07. The recommended envelope strategy (WP-C-04 §4: reduced, speed-dependent authority aiming at C1 for HE-01.x, plus ASIL B hardening) makes VS-VAL-10 the test that decides the ASIL of SG-01.

Out of scope: SOTIF validation of functional insufficiencies ([WP-V-02](WP-V-02-sotif-vv-strategy.md)…[WP-V-04](WP-V-04-sotif-unknown-scenarios.md)); the full fault-injection campaign ([WP-V-05](WP-V-05-fault-injection.md)), of which only the vehicle-level subset is repeated here; cybersecurity validation ([WP-V-06](WP-V-06-cybersecurity-validation.md)).

## 2. Validation configuration

| Item | Configuration |
|---|---|
| Vehicle | Reference Toyota Corolla, 12th generation (E210), TSS 2.0 (VIN and ECU firmware per [WP-C-01](../02-concept/WP-C-01-item-definition.md) OI-1); [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-01…INS-30 passed |
| Item | Released LionDriver tag (or release candidate) with pinned models and panda firmware; parameters per INS-19 |
| Test builds | Fault-injection and characterization builds (§5.1 VS-VAL-02, -05; §5.3) are separately identified builds with their own tag, used **only** on the closed course and removed afterwards; their use is logged in the drive sheet ([WP-V-07](WP-V-07-vehicle-test-operations.md) §7.4) |
| Equipment | Steering-wheel torque/angle sensor (instrumented wheel or clamp-on), rim force gauge, accelerometer/IMU independent of the device, GNSS/RTK or video lane-position measurement, CAN logger independent of the panda (second interface on the vehicle CAN), cabin sound level meter, soft target (radar-reflective) with propulsion or trolley, passenger-side abort switch (WP-V-07 §6.3). Rear-facing camera, fitted for every engaged public-road block: it covers the ego lane behind to at least 50 m (1.5 s at 120 km/h), records on the clock of the CAN logger and IMU, and is stored with the drive's logs, so that following vehicles can be annotated for P(E-situation) of SH-04 ([WP-V-02](WP-V-02-sotif-vv-strategy.md) §3.4, OS-08). It is a data-collection instrument only: no function of the item uses it, and it is not connected to the device |
| Environment | Closed course for all controllability, characterization and fault-injection cases; public roads (after G1) only for VS-VAL-40…43 |
| Personnel | Safety driver and test operator qualified per WP-V-07; test subjects for controllability studies (§5.2) |

## 3. Validation methods

| Method | Use |
|---|---|
| Repeatable vehicle tests with specified procedures | Characterization of AoUs, SG timing, safety mechanism effectiveness |
| Controllability tests with test subjects | SG-01, SG-03, SG-04 controllability within the envelope; take-over after SG-02/SG-06 warnings |
| Analysis of recorded data | Timing from CAN logs; lateral deviation vs time |
| Long-term / user tests in real operating conditions | Public-road validation drives (after G1) for alert behaviour, nuisance rates and DM |
| Review | Evidence that AoU results are consistent with the HARA ratings; that external measures are fit for purpose |

![Figure 3-1: verification and validation hierarchy of LD-SDA: VS-VAL (WP-V-01) validates the item; VS-SQ (WP-S-09) and VS-SI (WP-S-08) verify the system; VS-HW (WP-H-06), VS-ML (WP-W-10), VS-SWQ (WP-W-08) and VS-SWI (WP-W-07) verify components E-04/E-05, E-02 and E-03; VS-UV (WP-W-06) verifies the E-03 units; VS-FI (WP-V-05) cuts across levels; no specification has been executed](figures/fig-v01-3-1-verification-hierarchy.svg)

*Figure 3-1.* Where this validation sits on the right side of the V: each level of the element hierarchy of [WP-C-01 Figure 3-1](../02-concept/WP-C-01-item-definition.md#31-elements-inside-the-item) with the test specification that verifies or validates it, its case-ID prefix, the number of specified cases and the requirements its cases name (both from the generated [trace map](../trace/maps/aspice-trace-map.md) §2 and §5), and its results as each document records them: none has been executed (§7 here). SOTIF validation is out of scope of this document (§1) and is shown dashed. Source: [`figures/fig-v01-3-1-verification-hierarchy.svg`](figures/fig-v01-3-1-verification-hierarchy.svg); change it together with §1, §3 and §7 and when a case count or result in the work products shown changes.

## 4. Acceptance criteria (overview)

| Safety goal | Validation acceptance criterion |
|---|---|
| SG-01 | Worst-case lateral actuation allowed by the envelope is controllable (CA-01): 20 of 20 valid subjects control the event at every tested speed (≥ 85 % controllable at 95 % confidence, RESPONSE 3 approach). Supporting the C1 target (≥ 99 %) needs the larger sample or argument agreed with the assessor (WP-C-08 §7). No lateral torque when not engaged under injected SoC faults |
| SG-02 | Take-over warning within the SG-02 budget (≤ 1 s preliminary) after loss of lateral control; warning perceived by all test subjects; torque ramp-down without jerk that upsets the driver |
| SG-03 | Worst-case acceleration allowed by envelope and PCM is controllable (subject criterion as SG-01); PCM bounds out-of-range requests (AOU-05) |
| SG-04 | Worst-case deceleration step allowed by envelope and PCM stays within the bounds assumed for HE-04.1; driver can cancel by gas/brake |
| SG-05 | Release within ≤ 0.2 s (preliminary) of brake, cancel; steering override possible within AOU-02 force |
| SG-06 | Take-over warning within ≤ 1 s after loss of longitudinal deceleration |
| SG-07 | Stock PCS activation unchanged with the item installed (engaged, disengaged), TTC difference ≤ 0.2 s |

Timing values are the preliminary FTTI allocation of [WP-C-04 §8](../02-concept/WP-C-04-functional-safety-concept.md) (SG-01 ≤ 0.5 s, SG-02/SG-06 ≤ 1 s to warning, SG-03/SG-04 ≤ 1 s, SG-05 ≤ 0.2 s) and are replaced by [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) values when available (OI-2).

## 5. Test specification

### 5.1 Characterization of assumptions of use (G1 activity)

| ID | Purpose | Parent | Procedure (summary) | Pass criterion | Level |
|---|---|---|---|---|---|
| VS-VAL-01 | EPS LKA torque authority (AOU-01) | AOU-01R, FSR-01.13; WP-C-08 V-1 | Vehicle stationary and at 10, 30, 60 km/h on a straight: command LKA torque steps of 25/50/75/100 % of the envelope maximum (1500 raw, `toyota.h:173`) through the normal path (engaged, test-operator-triggered steps using the lateral maneuver mechanism, `tools/lateral_maneuvers`, adapted to torque steps); measure steering-wheel torque and angle with the wheel free and with the driver holding | Physical torque at the wheel recorded for each raw value (closes the raw → Nm part of GAP-04); maximum held torque ≤ the value used in the HARA C-rating; no EPS overshoot above request | CC |
| VS-VAL-02 | EPS behaviour when LKA messages stop (AOU-01) | AOU-01R, FSR-01.13; WP-C-08 V-1 | Fault-injection build stops `STEERING_LKA` (`0x2E4`) transmission while 50 % torque is applied, at 30 and 60 km/h; also send implausible requests (steer request bit with torque at rate above EPS acceptance) | Time from last message to EPS torque < 5 % of initial value measured (code comment suggests ≈ 1.5–2 s, `carstate.py:15-16`); EPS fault state reported in `EPS_STATUS`; behaviour recorded for FTTI analysis | CC, fault-injection rules |
| VS-VAL-03 | Driver override force (AOU-02) | AOU-02R, CA-05; FSR-05.03 | At 0, 30, 60, 90 km/h with maximum envelope torque applied against the driver's intended direction, the driver overrides; measure rim force and torque needed to hold and to counter-steer | Force and torque to override within the AOU-02R / CA-05 criterion (WP-C-04 §11, WP-C-08 §7; order of 50 N at the rim per WP-C-01, to be fixed); all trained drivers succeed in every trial | CC |
| VS-VAL-04 | Brake override (AOU-03) | AOU-03R, FSR-05.07; SG-05 | Engaged with acceleration request +2.0 m/s² (envelope max, `toyota.h:207-210`); driver applies brake at 20/50/80 km/h with 3 pedal forces | Brake decelerates the vehicle regardless of the ACC request; PCM cancels ACC on brake; time from pedal switch to zero ACC acceleration recorded | CC |
| VS-VAL-05 | PCM ACC envelope and cancel (AOU-05) | AOU-05R, FSR-03.06, FSR-04.03; WP-C-08 V-1 | Characterization build sends `ACC_CONTROL` (`0x343`) accel requests beyond the panda envelope (e.g., +3, +4, −5, −7 m/s²) — only with a closed-course firmware build whose identity is logged; speeds ≤ 60 km/h; also test the cancel bit | Achieved acceleration recorded per request; PCM limits recorded; cancel honoured within a recorded time. Result decides whether AOU-05 holds (ratings of HE-03.1, HE-04.1) | CC, fault-injection rules |
| VS-VAL-06 | Stock PCS preservation (AOU-04) | AOU-04R, FSR-07.04; SG-07; AC-06 | Soft-target approach tests at stock PCS speeds with (a) harness removed, (b) item installed and disengaged, (c) item engaged. Shared with [WP-V-03](WP-V-03-sotif-known-scenarios.md) KS-20 | PCS warning and brake onset at the same TTC within ±0.2 s in (a), (b), (c); camera PCS messages present on car-side CAN in (b) and (c) | CC |
| VS-VAL-07 | VSC/ABS status visibility (AOU-10) | H-01, H-04; HE-04.2 | Switch VSC off; check `espDisabled` event and engagement behaviour (`car_events.py:116-117`) | Engagement blocked or alerting as specified in WP-C-04 | Stationary/CC |
| VS-VAL-08 | PCM ACC response onset (planning-to-actuation time) | [WP-V-02 §4.3](WP-V-02-sotif-vv-strategy.md#43-derivation-of-the-air-01-air-03-and-air-04-values) (AIR-04 t_r, AIR-03 latency); AOU-05R | Release build, engaged, no lead, straight level track at 30 and 60 km/h, and at 90 km/h if the site allows (OI-1). `tools/longitudinal_maneuvers` (`maneuversd.py`) steps `longitudinalPlan.aTarget` from 0 to −1.0, −2.0, −3.0 (a_lim) and −3.5 m/s² (envelope minimum) and to +1.0 m/s², ≥ 10 repetitions per step and speed, at random phase. Time stamps: (1) the `longitudinalPlan` message with the new target (rlog); (2) the first `ACC_CONTROL` (`0x343`) frame carrying it on the car-side bus (independent CAN logger); (3) onset of the vehicle response, the first time the independent IMU's longitudinal acceleration (filtered, logged on the same clock as the CAN logger) has moved 10 % of the step from its pre-step value; (4) 90 % of the step | Characterisation. Reported per step and speed: (1)→(2) software time, (2)→(3) PCM onset time, (1)→(3) planning-to-actuation time, (2)→(4) rise time, each as the worst observed value. The 0.5 s share for planning to actuation assumed in WP-V-02 §4.3 holds if the worst (1)→(3) is ≤ 0.5 s for the braking steps; otherwise AIR-04 t_r and the AIR-03 latency are re-derived from the measured value | CC |

### 5.2 Driver controllability tests

Test subjects: licensed drivers who are not project members and have not driven LD-SDA before, briefed only with the user information ([WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md)). The safety driver sits in the front passenger seat with the abort switch; the test operator in the rear. Twenty valid subjects per test condition, unless the worst-case condition is shown on a smaller set first (speed escalation: a condition is run only after the slower one passed). Ethics: informed consent, right to stop, debrief. Supervision (decided 2026-10-14 by the project lead, DQ-026 option B): the project lead supervises every §5.2 session under a written test protocol and signed consent; there is no external human-factors reviewer. This is weaker independence and makes the lead a single point of failure for subject protection; the protocol therefore names the abort criteria, and any subject may stop a run.

VS-VAL-10, -12, -13, -14 and -16 also supply P(not controlled) to the SOTIF validation targets ([WP-V-02](WP-V-02-sotif-vv-strategy.md) §3.3). Their result row therefore reports, per tested speed and condition, the number of valid subjects, the number who did not control the event and the one-sided 95 % upper bound on that share.

| ID | Purpose | Parent | Procedure (summary) | Pass criterion |
|---|---|---|---|---|
| VS-VAL-10 | Worst-case lateral disturbance inside the envelope | SG-01, CA-01; WP-C-08 V-3 | Unannounced, during engaged driving in a coned lane (3.5 m) at 30, 50, 70, 90 and 110 km/h, the ODD bound (DQ-260 A); 110 km/h only after the separate risk review the project lead decided to hold (DQ-091 A, OI-7): test operator triggers a torque disturbance at maximum envelope rate up to maximum envelope torque, left or right, on straight and gentle curve | ≥ 20/20 valid subjects keep the vehicle in its lane: no tyre beyond the outer edge of the lane line before the subject has corrected (WP-C-08 §7.1 CA-01, fixed before testing, DQ-042 A); record reaction time, peak lateral deviation, peak steering force. Results set the C-class for HE-01.x |
| VS-VAL-11 | Lateral deviation vs time at envelope limits (no driver reaction) | SG-01 FTTI (HARA OI-3); FSR-01.01 limit derivation | Robot or hands-off with restraint (only at ≤ 50 km/h; higher speeds by vehicle-model extrapolation validated at low speed): apply max envelope disturbance, measure lateral offset vs time | Curves delivered to WP-S-04; compared with `docs/SAFETY.md:32` (0.9 s to 1 m) |
| VS-VAL-12 | Unexpected loss of lateral control in a curve with take-over warning | SG-02, CA-02, CA-06; WP-C-08 V-3 | Test operator triggers loss of lateral control (test build stops lateral control) in a curve at 50 and 70 km/h; subject driving hands-on and, separately, hands resting on the lap (foreseeable misuse, HE-02.1) | Warning ≤ 1 s from loss; ≥ 20/20 subjects keep the vehicle in its lane as in VS-VAL-10 (WP-C-08 §7.1 CA-02, CA-06) |
| VS-VAL-13 | Unexpected acceleration while following | SG-03, CA-03; WP-C-08 V-4 | Following a soft target on a trolley at 1.5 s gap, 40 km/h; test operator triggers +2.0 m/s² request | ≥ 20/20 subjects brake before TTC < 1.0 s **(TBC)**; no contact |
| VS-VAL-14 | Unexpected deceleration step | SG-04, CA-04; WP-C-08 V-4 | At 60 and 90 km/h, trigger −3.5 m/s² step (envelope min); measure jerk, driver response (gas override) | Deceleration and jerk within the bounds assumed in HE-04.1; subjects can override with gas |
| VS-VAL-15 | Release on driver input | SG-05, CA-05; FSR-05.01…05.03 | Brake, cancel, steering override at 30/60/90 km/h during active actuation; CAN timing from the independent logger | Lateral torque and accel request to zero / inactive within ≤ 0.2 s (brake, cancel); steering override force ≤ AOU-02 |
| VS-VAL-16 | Loss of longitudinal deceleration with warning | SG-06, CA-03; FSR-06.02 | Approaching a slower soft target at 50 km/h; test build drops planner deceleration; subjects respond | Warning ≤ 1 s; ≥ 20/20 subjects stop or avoid without contact |
| VS-VAL-17 | DM-supported controllability | SH-12, DMP-01…DMP-05; FSR-02.06…02.09; TSR-634; WP-C-08 V-5 | Subjects asked to perform a scripted secondary task; measure DM alert onset vs policy timers; repeat VS-VAL-12 with a distracted-then-alerted subject. Wheel-touch fallback forced (sunglasses) at 90 and 110 km/h: measure the distance and time to each alert and the subject's response | Alerts per `policy.py:34-36`; in the fallback, alerts per WP-C-08 §5.4 and 20/20 subjects respond before the no-response stage (WP-V-02 §4.4 (b)); take-over success as VS-VAL-12 |
| VS-VAL-18 | Alert perceptibility | SG-02, SG-06, CA-07; WP-C-08 V-2 | Measure alert sound level vs cabin noise at 110 km/h with radio on, display legibility in direct sunlight | Alert ≥ 10 dB **(TBC)** above cabin noise; recognised by ≥ 20/20 subjects |

### 5.3 Effectiveness of safety mechanisms in the vehicle

Vehicle-level repetition of selected [WP-V-05](WP-V-05-fault-injection.md) cases. All on closed course, fault-injection rules of [WP-V-07 §7.4](WP-V-07-vehicle-test-operations.md).

| ID | Mechanism | Injection | Pass criterion |
|---|---|---|---|
| VS-VAL-20 | Heartbeat supervision | Stop `pandad` / SPI heartbeat while engaged at 50 km/h | Actuation removed; time measured against the FTTI. Since 2026-10-12 authority is revoked after 0.3 s without heartbeat in all builds (`panda/board/drivers/heartbeat_monitor.h`, not verified on hardware); the SILENT timers (3–5 s) are unchanged and SILENT timing is still expected to fail (GAP-06). Since 2026-10-13 the siren sounds at the revocation, ≈ 0.56 s after the last heartbeat, in all builds (panda `c33343b`; WP-S-04 T-07a; not verified on hardware) |
| VS-VAL-21 | RX checks | Disconnect / block wheel-speed or PCM message on the harness (breakout box) | `controls_allowed` cleared; release time recorded (since 2026-10-12: after 5 nominal periods, ≤ 0.162 s, opendbc `7993399`; not verified on hardware) |
| VS-VAL-22 | Torque and accel limits | Test build on SoC requests torque > 1500 raw and rates above limits; accel outside −3.5…+2.0 | Panda blocks over-limit frames (no actuation above limits on the independent CAN logger) |
| VS-VAL-23 | Engagement gating | SoC commands torque while not engaged | No torque frame on the car side |
| VS-VAL-24 | Relay malfunction | Inject camera-side LKA message on the car side (breakout box) | `relayMalfunction` detected, immediate disable |
| VS-VAL-25 | Safety-mode integrity | Send `0xdc` with a different mode while onroad | Reference build (`LIONDRIVER_REFERENCE=1`): rejected by the firmware (TSR-512, `panda/board/reference_lock.h`; not verified on hardware). Default build: detected (`controlsMismatch`), immediate disable |
| VS-VAL-26 | Host fault reactions | Kill `modeld`, `controlsd`; CPU overload | Alert and disengagement within SG-02 budget; GAP-16 3 s soft-disable behaviour measured |

### 5.4 Validation of external measures

| ID | External measure | Covered by |
|---|---|---|
| VS-VAL-30 | Toyota EPS LKA torque limiting and fault handling | VS-VAL-01, -02, -03 |
| VS-VAL-31 | PCM brake override and ACC envelope | VS-VAL-04, -05 |
| VS-VAL-32 | Stock PCS/AEB | VS-VAL-06 |

### 5.5 Public-road validation (after G1)

| ID | Purpose | Procedure | Pass criterion |
|---|---|---|---|
| VS-VAL-40 | Alert and HMI behaviour in the ODD | ≥ 2 000 km **(TBC)** engaged in the ODD per [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) block B1, all alerts logged | No unexplained soft/immediate disable; alerts correct and perceived |
| VS-VAL-41 | DM nuisance and effectiveness | Same drives; DM events reviewed against cabin video (consented) | False-alert rate within AIR-08; no missed sustained distraction |
| VS-VAL-42 | Envelope limit hits | Safety replay of all drives | Limit-hit rate reported; each hit analysed |
| VS-VAL-43 | Environmental conditions | Repeat a subset of VS-VAL-15 and VS-VAL-18 at night and in light rain (closed course) | As base test |

## 6. Schedule and dependencies

| Group | Gate | Depends on |
|---|---|---|
| §5.1 VS-VAL-01, -03, -04, -06, -07, -08 | G1 | WP-V-07 approved; closed-course site; instrumented wheel; independent IMU and CAN logger on one clock (VS-VAL-08). VS-VAL-01, -03, -04, -06 and -08 are entry criteria for public-road level L5 (WP-V-07 §4) |
| §5.1 VS-VAL-02, -05 | G1 (target) | Fault-injection/characterization build process (configuration control), WP-V-05 rules |
| §5.2 | G4–G5 | §5.1 results; envelope parameters fixed (WP-S-02); ethics/consent forms |
| §5.3 | G4 | HIL results from WP-V-05; breakout box |
| §5.5 | G5 | G1 passed; WP-V-04 B1 |

## 7. Report

**Not yet executed.** No validation test has been performed on the reference vehicle. No AoU is verified (all `Unverified` in [WP-C-01 §7](../02-concept/WP-C-01-item-definition.md#7-assumptions-of-use-aou-and-external-measures)).

### 7.1 Report header template

| Field | Value |
|---|---|
| Report ID | VAL-REP-<nn> |
| Configuration (software tag, model hashes, panda FW, vehicle FW record) | |
| Test builds used (tag, purpose) | |
| Site, dates, conditions | |
| Crew and test subjects (count, recruitment) | |
| Equipment calibration records | |
| Deviations from specification | |

### 7.2 Result template

| ID | Trials / subjects | Key measurements | Pass criterion met? | AoU / SG verdict | Consequence for HARA / FSC | Log IDs |
|---|---|---|---|---|---|---|
| VS-VAL-01 | | | Not yet executed | | | |
| VS-VAL-02 | | | Not yet executed | | | |
| VS-VAL-03 | | | Not yet executed | | | |
| VS-VAL-04 | | | Not yet executed | | | |
| VS-VAL-05 | | | Not yet executed | | | |
| VS-VAL-06 | | | Not yet executed | | | |
| VS-VAL-07 | | | Not yet executed | | | |
| VS-VAL-08 | | | Not yet executed | | | |
| VS-VAL-10…18 | | | Not yet executed | | | |
| VS-VAL-20…26 | | | Not yet executed | | | |
| VS-VAL-40…43 | | | Not yet executed | | | |

### 7.3 Conclusion template

| Item | Content |
|---|---|
| Safety goals validated | |
| AoUs verified / failed (with consequence: rating change per WP-C-03 ⚠ alternatives) | |
| Open issues | |
| Recommendation to WP-K-01 / WP-K-04 | Not yet executed |

## Open items

| ID | Item |
|---|---|
| OI-1 | Choose the closed-course site and confirm it allows the speeds of VS-VAL-03, -10, -14. Site requirements and candidates: [test-sites/](test-sites/README.md) |
| OI-2 | Replace preliminary SG timing values with WP-S-04 FTTIs |
| OI-3 | Closed 2026-10-23: the lead decided to fix the controllability pass limits now from the concept drafts, before any subject test, and not to change them after testing starts (DQ-042, option A, 2026-10-14). Values, as frozen in [WP-C-08 §7.1](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) (approved 2026-10-19): AOU-02R override force ≤ 50 N at the rim (CA-05, VS-VAL-15); CA-01 lateral margin: the vehicle stays in its lane, no tyre beyond the outer edge of the lane line (VS-VAL-10, -12). The assessor check of WP-C-08 OI-3 remains |
| OI-4 | Procedure defined 2026-10-22 in [WP-P-01 §7.1](../07-supporting/WP-P-01-configuration-management-plan.md) (DQ-125 A): each test build is a named configuration item, built only by CI, used only on the closed course, with the release build reflashed before the car leaves. Left: implementing it (WP-P-01 OI-9) before VS-VAL-02 or VS-VAL-05 runs |
| OI-5 | Write the §5.2 test protocol and the consent, recruitment and debrief material for test subjects. Supervision decided 2026-10-14 (DQ-026 option B): the project lead supervises, no external human-factors reviewer (WP-M-08 OI-6) |
| OI-6 | Procure the test equipment. Decided 2026-10-14 (DQ-043, option B): buy in stages. Stage 1: abort switch, independent CAN logger and rear-facing camera. Stage 2, when a test site is booked (OI-1): instrumented steering wheel and soft target; the closed-course controllability tests (§5.2) wait for it. Left: buy stage 1 (nothing bought yet); until the abort switch and logger exist, no engaged test drive counts as evidence |
| OI-7 | 110 km/h controllability test. Decided 2026-10-14 (DQ-091, option A): hold a separate risk review and run VS-VAL-10 up to 110 km/h, the ODD bound (DQ-260 A). Until it has run, P(not controlled) above 90 km/h stays 1 ([WP-V-02](WP-V-02-sotif-vv-strategy.md) §3.3). Left: hold and record the risk review before any test above 90 km/h ([WP-V-07](WP-V-07-vehicle-test-operations.md) §8.1), and a closed-course site that allows 110 km/h (OI-1) |
