# WP-V-07 Vehicle Test Operations and Safety-Driver Procedures

| Field | Value |
|---|---|
| Work product | WP-V-07 Vehicle test operations and safety-driver procedures |
| Standard reference | ISO 26262-4:2018 §8 (validation environment and conditions); ISO 21448:2022 §10–11 (testing in real conditions); ASPICE 4.0 VAL.1. Informative: SAE J3018 (safety-relevant guidance for on-road testing of prototype automated driving system-operated vehicles) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All vehicle operation of LD-SDA during development (FuSa, SOTIF, AI, CS tests) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); external reviewer with vehicle-test experience recommended before first public-road use (OI-1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This procedure governs **every** use of the LD-SDA item in a vehicle during development: installation checks, closed-course tests, data-collection drives and public-road testing with a safety driver. It protects the test crew and other road users while the item's safety case is incomplete.

It is the procedure referred to by:
- [WP-M-01 §9](../01-management/WP-M-01-assurance-strategy.md#9-top-risks-to-the-assurance-path) and gap action 10: no LionDriver public-road operation beyond safety-driver testing under this document until G1;
- [WP-C-01](../02-concept/WP-C-01-item-definition.md) AOU-07: during development only trained safety drivers operate the item on public roads;
- [WP-V-01](WP-V-01-safety-validation.md), [WP-V-03](WP-V-03-sotif-known-scenarios.md), [WP-V-04](WP-V-04-sotif-unknown-scenarios.md), [WP-V-05](WP-V-05-fault-injection.md) and [WP-W-10](../05-software/WP-W-10-ml-engineering.md) for test execution and data collection;
- [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-30 (driver approval).

**Nothing in this document may be relaxed by a test plan.** A test that cannot be run within these rules needs a written deviation approved by the safety manager before the test (§13).

### 1.1 Basic rules (summary card for the vehicle)

1. No vehicle operation of LD-SDA until this document is approved.
2. No engaged operation on public roads until gate **G1** is passed and the software baseline has passed its closed-course checkout (§4).
3. Fault injection, characterization builds and controllability tests with test subjects: **closed course only**.
4. Engaged testing at levels L3 and L5 always has **two people**: safety driver and test operator.
5. Only identified software is driven (§7). The pre-drive checks (§6) are done every time.
6. The safety driver stays in control: hands near the wheel, eyes on the road, foot ready. When in doubt, take over.
7. Abort criteria (§8) are not negotiable. Any person in the vehicle can call "Take over".
8. Every incident and near miss is reported within 24 hours (§9).

## 2. Roles

| Role | Responsibilities | Who (today) |
|---|---|---|
| Test manager | Plans campaigns; confirms entry criteria; approves crews, routes and test builds; owns incident follow-up | Project maintainer (Jherrod Thomas) |
| Safety driver (SD) | Operates the vehicle; supervises the item; takes over; final authority on safety in the vehicle | Qualified per §5. Initially the maintainer; at least one more SD needed for two-person crews (OI-2) |
| Test operator (TO) | Monitors device and logs; executes test steps; calls out alerts and anomalies; records the drive sheet; watches surroundings; operates the passenger abort switch at L3 | Qualified per §5.4 |
| Range safety officer (RSO) | At closed-course sessions with test subjects or fault injection: controls access to the course, weather and run-off checks, emergency equipment | Site staff or a third qualified person |
| Test subject | Drives in controllability studies (WP-V-01 §5.2) under supervision | External volunteers, consented |
| Incident lead | Runs §9 after an incident | Test manager unless involved, then the safety manager's delegate |

The SD has authority to refuse or stop any test. Nobody may pressure the SD to continue.

## 3. Test levels

| Level | Name | Description | Where | Item actuation |
|---|---|---|---|---|
| L0 | Desk | Replay, simulation, analysis (`process_replay`, `model_replay`, `tools/sim`) | Office | None |
| L1 | Bench / HIL | Device or bare panda on a CAN bench with replayed Corolla traffic (D-04) | Lab | On bench CAN only |
| L2 | Vehicle stationary | Installation checks, provisioning, relay and PCS message checks, DM checks; ignition on, parking brake set, P range | Private premises | None (no engagement) |
| L3 | Closed course | Characterization, controllability, fault injection, known-scenario tests | Closed course with access control | Engaged, including test builds |
| L4 | Public road, passive | Data collection with the item installed and `OpenpilotEnabledToggle = 0`, so the car interface is passive and the safety model is `noOutput` (`openpilot/selfdrive/car/card.py:112-118`) | Public road | None (cannot engage) |
| L5 | Public road, engaged, restricted | Engaged testing on pre-approved routes in the restricted ODD (§8.2) | Public road | Engaged |
| L6 | Public road, engaged, validation | Validation and exploration drives (WP-V-04 blocks) of a release candidate in the claimed ODD | Public road | Engaged |

## 4. Entry criteria per level

All criteria of the lower levels also apply.

| Level | Entry criteria |
|---|---|
| L0, L1 | None beyond configuration control of the software under test |
| L2 | This document approved. Vehicle preconditions [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-06, INS-07 met. Person performing the work briefed on this document |
| L3 | L2 checks passed for this installation (INS-01…INS-27). Site booked with written permission; site risk assessment done (run-off areas, barriers, speed limit of the site). SD qualified (§5.2, practical part may be done at this session under supervision of the test manager). Test plan for the session lists every test, its speed and its abort criteria. For fault injection and characterization builds: §7.4 rules. For test subjects: consent forms and RSO present |
| L4 | INS-01…INS-27 passed, including INS-27 relay and PCS-message check (repeat with `OpenpilotEnabledToggle = 0`, OI-3). Driver briefed (INS-30). Data-handling rules §11 in place (upload to comma disabled, consent of all occupants for cabin recording). Allowed before G1 because the item cannot actuate |
| L5 | **G1 passed** (concept phase approved, including the HARA confirmation review). AOU characterization VS-VAL-01, -03, -04, -06 done and their results accepted in WP-C-03/WP-C-04. The exact software baseline has passed an L3 checkout on the reference vehicle: engagement and disengagement (brake, cancel), steering and gas override, alerts, DM look-away, `controlsMismatch`/`relayMalfunction`/`canError` absent (as INS-28/INS-29, plus WP-V-01 VS-VAL-15 subset). Experimental Mode off and big-model artefacts absent (KS-24). Two-person crew available. Legal status of testing in the state confirmed ([WP-C-01](../02-concept/WP-C-01-item-definition.md) OI-6). Insurance confirmed to cover development testing (OI-4) |
| L6 | L5 entry criteria. The release candidate has passed the known-scenario suite subset that covers the claimed ODD ([WP-V-03](WP-V-03-sotif-known-scenarios.md)) and the L5 exploration of the same routes has no open class-U event with S2/S3 potential ([WP-V-04](WP-V-04-sotif-unknown-scenarios.md) §3). Safety manager approval of the campaign |

**Re-entry after change.** Any change to the software baseline, panda firmware, models, parameters or vehicle (repair affecting steering, brakes, camera, alignment) returns the vehicle to L3 checkout before further L5/L6 driving. A configuration that has had an incident with injury or damage returns to L2 until the incident is closed (§9.4).

## 5. Qualification and training

### 5.1 Safety driver prerequisites

| Requirement | Evidence |
|---|---|
| Full, valid US driver licence held for at least 5 years **(TBC)** | Licence copy |
| No at-fault crash, DUI/DWI or licence suspension in the last 5 years | Signed declaration; motor vehicle record where obtainable |
| Fit to drive: no condition or medication that impairs driving; uncorrected vision meets licence requirements | Signed declaration |
| Accepts the conduct rules of §5.5 | Signed |

### 5.2 Safety driver training curriculum

| Module | Content | Format | Pass criterion |
|---|---|---|---|
| T1 System knowledge | Item functions F-01…F-09; what the envelope limits and does not limit; known limitations (`docs/LIMITATIONS.md`); DM behaviour and timers; alert classes (warning, soft disable, immediate disable); the gaps that matter for the driver (GAP-16 soft-disable keeps actuating up to 3 s; GAP-02 envelope does not monitor driver torque; GAP-19 `speedTooHigh` does not disengage) | Classroom, 2 h | Written quiz ≥ 80 % |
| T2 This procedure | Levels, entry criteria, pre-drive checks, abort criteria, incident handling, data rules | Classroom, 1 h | Quiz ≥ 80 % |
| T3 Vehicle | Reference Corolla controls, cruise stalk, LKA/PCS switches, VSC, hazard lights; how to remove the device or switch the item to passive | Practical, stationary | Demonstrated |
| T4 Takeover drills | On closed course: brake, cancel and steering override at 30/50/70 km/h; unannounced takeover requests from the TO; unannounced lateral disturbance within the envelope (test build) | Practical, closed course | ≥ 10 successful takeovers per input type; reaction time to unannounced events ≤ 1.0 s **(TBC)** in every trial |
| T5 Commentary driving | Supervised drive with the test manager narrating hazards and ODD boundaries, then the trainee narrating | Practical, L4/L5 | Test manager sign-off |
| T6 Route familiarisation | Drive each L5 route in manual mode before driving it engaged | Practical | Logged |

**Recurrent training.** Every 6 months, and before driving a software baseline whose behaviour change is flagged in its change request: T1 delta briefing and a short T4 refresher (≥ 3 takeovers per input type).

**Records.** Training record per person in the competence register ([WP-M-04](../01-management/WP-M-04-organization-competence-safety-culture.md)); approval as SD signed by the test manager. The maintainer's own qualification is signed by an external reviewer until a second qualified person exists (independence, T-09).

### 5.3 Duty and fitness rules

| Rule | Value |
|---|---|
| Continuous engaged driving | ≤ 2 h, then ≥ 15 min break outside the vehicle |
| Test driving per day | ≤ 6 h total, including closed course |
| Rest before test driving | ≥ 8 h off duty |
| Alcohol and drugs | Zero; no impairing medication |
| Fatigue | SD or TO may stop the session at any time for fatigue; drowsiness = immediate end of the session |
| Phones | SD does not use a phone or the device UI while moving; navigation set before departure |

### 5.4 Test operator qualification

T1, T2, T3 as above; trained in the logging tools and drive sheet; for L3 sessions with the abort switch, practised its use. The TO does not need to be an SD but must hold a driver licence.

### 5.5 Conduct rules

- The SD's priority is safe vehicle operation, not the test.
- Hands on or within a few centimetres of the wheel, eyes on the road, right foot ready over the brake while engaged — regardless of what the item tolerates (the item does not require hands on the wheel).
- No deliberate misuse tests (hands-off, eyes-off) on public roads. Misuse behaviours are tested only on the closed course with the passenger abort switch (WP-V-01 VS-VAL-12, -17).
- No passengers other than the crew during L3, L5 and L6 testing.

## 6. Pre-drive checks

Done before every session; recorded on the drive sheet (§10). A failed check means no engaged operation until resolved.

### 6.1 Vehicle (AOU-09, AOU-10)

| ID | Check |
|---|---|
| PD-01 | [WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) OPS-01: no warning lamps for EPS, brake, ABS/VSC, engine, PCS/TSS |
| PD-02 | OPS-02: VSC on |
| PD-03 | Tyre pressures to placard; tyre condition; no change of tyre size since the reference record |
| PD-04 | Brakes and steering feel normal in a low-speed check before engaging |
| PD-05 | Weekly, or after any workshop visit: DTC scan of EPS, ABS/VSC, engine, camera, radar (INS-06) |
| PD-06 | Fuel/charge sufficient; washer fluid; wipers effective; windscreen clean in front of both cameras (OPS-03) |

### 6.2 Item and configuration

| ID | Check |
|---|---|
| PD-10 | Device firmly mounted, not tilted (OPS-04); harness connectors seated (SPC-01) |
| PD-11 | Software identity: installed commit = the tag in the session plan; clean build (INS-15) |
| PD-12 | Panda firmware version and signature as recorded (INS-17); not a DEBUG build unless this is an L3 session that requires it (§7.4) |
| PD-13 | Model hashes as recorded (INS-18) — once hashes exist ([WP-W-10](../05-software/WP-W-10-ml-engineering.md) OI-1) |
| PD-14 | Parameter dump equals the session plan (INS-19): `ExperimentalMode` off, debug/maneuver modes absent unless planned at L3, `IsDriverViewEnabled` off, `SshEnabled` per plan, `OpenpilotEnabledToggle` = 0 for L4 |
| PD-15 | After ignition on: `carParams` and `pandaStates` checks (INS-22, INS-23): safety model `toyota`, param 73 (or `noOutput` at L4) |
| PD-16 | No offroad alerts (OPS-06); calibration `calibrated` (no calibration alert) |
| PD-17 | Driver-facing camera sees the SD's face (OPS-05) |
| PD-18 | Logging active; storage has room for the session; device clock correct |
| PD-19 | First engagement of the session in a safe place at low speed: brake disengages, cancel disengages, steering override works (short form of INS-28) |

### 6.3 Crew, environment and equipment

| ID | Check |
|---|---|
| PD-20 | Crew fit to drive (§5.3); roles assigned; communication protocol agreed (§8.3) |
| PD-21 | Weather and light forecast inside the session's allowed conditions (§8.2); no forecast of conditions in the abort list during the session window |
| PD-22 | Route plan or closed-course plan printed/available; known hazards on the route reviewed |
| PD-23 | Emergency kit: first-aid kit, fire extinguisher, warning triangle, hi-vis vests, charged phone, incident form |
| PD-24 | L3 only: passenger abort switch fitted and function-tested (switching it removes power from the device so the panda releases control and the harness relay restores the stock camera path; verify before first use, OI-5); RSO present where required; independent CAN logger running |
| PD-25 | Data-handling settings per §11 (upload to comma disabled or as approved) |

## 7. Software and configuration control for testing

### 7.1 What may be driven

| Level | Allowed software |
|---|---|
| L2, L4 | Any tagged LionDriver build listed in the session plan |
| L3 | Tagged builds and identified test builds (§7.4) |
| L5 | Tagged release candidates that passed L3 checkout |
| L6 | Tagged release candidate under validation; no changes during a campaign block |

Untagged, locally modified or upstream comma builds are never driven engaged. Upstream automatic updates are disabled (no update channel other than LionDriver's, INS-15).

### 7.2 Configuration record

Each session records: software tag/commit, panda firmware version/signature, model hashes, parameter dump, vehicle odometer and any service since the last session.

### 7.3 Prohibited on public roads

Developer and debug modes (`JoystickDebugMode`, `LongitudinalManeuverMode`, `LateralManeuverMode`, `process_config.py:34-47`), Experimental Mode, the big model (Chestnut), any DEBUG panda firmware, `IsDriverViewEnabled` demo mode, SSH sessions while moving, and any tool that writes parameters or CAN while onroad (OPS-10).

### 7.4 Fault injection and characterization builds (closed course only)

1. Built from a tagged commit plus an identified patch; tag name contains `-fi-` or `-char-`.
2. Listed in the session plan with the exact faults/commands it can produce and the expected vehicle reaction.
3. Installed only at the closed course; flashed back to the release configuration and verified with PD-11…PD-15 **before leaving the site**. The drive sheet records both flashes.
4. Speed for each fault-injection test is escalated from the lowest planned speed; a test is not repeated at a higher speed until the lower one has passed and been reviewed.
5. Injection is triggered by the TO only after the SD confirms "ready"; the SD can cancel at any time.
6. The passenger abort switch is in reach of the TO; the RSO confirms the course is clear before each run.
7. Panda firmware builds that allow debug features (`ALLOW_DEBUG`, GAP-25) are fault-injection builds under these rules.

## 8. Operating rules and abort criteria

### 8.1 Closed course (L3)

| Rule | Value |
|---|---|
| Maximum speed | The lower of the site limit and the test plan; no test above 90 km/h without a separate risk review (WP-V-01 VS-VAL-10) |
| Clearance | No other vehicle or person in the test lane or its run-off area during a run, except planned soft targets |
| Soft targets | Only radar-reflective soft targets designed for collision; never real vehicles or people as targets |
| Test subjects | Only with RSO present, SD in the passenger seat with the abort switch, and consent recorded |

### 8.2 Public road (L5/L6) ODD restrictions

Initial restricted ODD for L5 — a subset of ODD-H of [WP-C-02 §3.1](../02-concept/WP-C-02-odd-and-intended-functionality.md#31-odd-taxonomy) (to be widened only by a WP-V-04 block decision):

| Attribute | L5 restriction |
|---|---|
| Road type | Limited-access divided highway with clear lane markings on pre-approved route segments |
| Speed | ≤ posted limit and ≤ 105 km/h (65 mph) **(TBC)**; set speed never above the posted limit |
| Light | Daylight, sun elevation not directly ahead and low (avoid sunrise/sunset driving toward the sun) |
| Weather | Dry road, no precipitation, visibility > 1 km |
| Traffic | Light to moderate; avoid peak congestion until stop-and-go has been checked at L3 |
| Excluded | Construction zones, toll plazas, school zones, lane-drop merges flagged on the route plan, tunnels, roads with pedestrians or cyclists, any area flagged in the route review |

L6 uses the claimed ODD of [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) (ODD-H; ODD-A only if confirmed, WP-C-02 OI-4) with the WP-V-04 block plan. Conditions WP-C-02 excludes (work zones, toll plazas, tunnels, low sun in the camera view, moderate/heavy rain, speeds above 120 km/h) remain abort criteria at every level.

### 8.3 Communication protocol

| Call | Who | Meaning |
|---|---|---|
| "Ready to engage" / "Engaging" | SD | SD intends to engage; TO checks the device shows no alerts |
| "Take over" | Anyone | SD takes over immediately; no discussion until stopped or safe |
| "Disengaged" | SD | Confirms manual control |
| "Mark" | TO or SD | TO presses the bookmark (`userBookmark`, OPS-12) and notes time and reason |
| "Stop the session" | Anyone | Pull over at the next safe place; session ends |

The TO keeps conversation to test-relevant callouts while the vehicle is moving and does not hold screens in the SD's line of sight.

### 8.4 Abort criteria — take over immediately

The SD disengages (brake or cancel) and drives manually when any of the following occurs:

| # | Criterion |
|---|---|
| A-01 | Any unexpected steering, acceleration or braking, or any doubt about what the item is doing |
| A-02 | Vehicle closer than 0.5 m **(TBC)** to a lane line without a requested lane change, or drifting toward another vehicle, barrier or road edge |
| A-03 | Time gap to the lead below 1.0 s, or a lead vehicle braking hard, or a vehicle cutting in closely |
| A-04 | Stationary or slow object in or near the lane ahead (including breakdowns, debris, emergency vehicles) |
| A-05 | Any alert from the item (warning, soft disable, immediate disable, FCW, DM alert level ≥ 2), any unexpected HMI state, or any mismatch between HMI and vehicle behaviour |
| A-06 | Leaving the session's ODD or route: construction, merges/lane drops, toll plaza, weather change, low sun ahead, tunnel, dense traffic, pedestrians or cyclists near the road |
| A-07 | Emergency vehicle approaching, police instruction, or any situation needing unusual manoeuvres |
| A-08 | Vehicle warning lamp, abnormal noise, vibration or smell |
| A-09 | Crew distraction, fatigue, discomfort, or a crew member's request |
| A-10 | Loss of logging (TO observes the device not recording) |

### 8.5 Stop rules — end the session or campaign

| # | Trigger | Action |
|---|---|---|
| S-01 | Any collision or contact, or any event where the SD's intervention prevented a likely collision | End the session; incident procedure §9; campaign suspended until §9.4 |
| S-02 | Two unexplained A-01/A-02 events in one session | End the session; triage per WP-V-04 §3 before the next session |
| S-03 | Any item fault event (`controlsMismatch`, `relayMalfunction`, `canError`, `excessiveActuation` latch, panda fault) | End engaged operation for the session; problem report |
| S-04 | Any change of vehicle condition (warning lamp, repair needed) | End the session |
| S-05 | Class-U discovery with S3 potential (WP-V-04 §3) | Campaign suspended; safety manager decides on ODD restriction before resuming |

## 9. Incident handling and reporting

### 9.1 Categories

| Category | Definition |
|---|---|
| I-1 Collision | Any contact with a vehicle, person, animal or object, any injury, or any airbag deployment, while the item was engaged or within 30 s **(TBC)** after disengagement |
| I-2 Near miss | Situation where a collision was avoided only by driver intervention or by the other party's action, or an abort criterion A-01…A-04 with a hazard in proximity |
| I-3 Item anomaly | Unexpected item behaviour without a hazard (wrong alert, unexplained disengagement, fault event) |
| I-4 Procedure deviation | A rule of this document not followed (e.g., wrong software driven, check skipped) |

### 9.2 Immediate actions (I-1)

1. Stop safely; hazard lights; secure the scene; help injured people; call emergency services when anyone is injured or the law requires it.
2. Do not change the item: leave the device powered so the current segment is closed and preserved; press the bookmark; do not reboot, update or uninstall.
3. Exchange information and report to the police as required by state law.
4. Photograph the scene, vehicle positions and damage.
5. Notify the test manager immediately (phone); the test manager notifies the safety manager and the insurer.

### 9.3 Reporting

| Report | When | To |
|---|---|---|
| Incident report (form: time, place, configuration record, crew, description, logs secured, immediate actions) | I-1: within 24 h; I-2, I-3: within 24 h; I-4: within 3 days | Test manager → problem resolution ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)) |
| Regulatory crash reporting assessment (NHTSA Standing General Order model, T-13) | I-1: on the same day; the decision whether and what to report is recorded | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) process |
| Cybersecurity event (suspected tampering, unknown firmware or software found) | Immediately | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |
| SOTIF triage of the event | Within 7 days | [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) §3; [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) update if class U |

### 9.4 Resumption

After an I-1, testing with the affected configuration resumes only when: logs have been analysed; the cause is classified (item insufficiency, malfunction, procedure, external); corrective action is decided; the safety manager signs the resumption; and, if the item was implicated, the corrected configuration has passed L3 checkout. An I-2 caused by the item needs triage and a recorded decision before the same route/scenario is driven again.

## 10. Drive sheet (record per session)

| Field | Content |
|---|---|
| Session ID, date, start/end time | |
| Level (L2…L6), site or route ID | |
| Crew: SD, TO, RSO, test subjects (IDs only) | |
| Configuration record (§7.2) | |
| Pre-drive checks PD-01…PD-25 | Pass/fail per item |
| Conditions | Weather, light, road surface, traffic |
| Tests / route segments driven | With engaged distance and time |
| Events | Time, location, type (A-nn, alert, bookmark), short description |
| Takeovers and disengagements | Count and reason classes |
| Incidents | Category and report number |
| Post-drive | Logs copied and checksummed (§11); test builds removed (§7.4); vehicle condition |
| Signatures | SD and TO |

Drive sheets are retained with the validation records ([WP-P-04](../07-supporting/WP-P-04-documentation-management.md)).

## 11. Data handling

| Topic | Rule |
|---|---|
| Collection | Full logs on every session (`rlog`, road cameras; cabin camera only with consent of all occupants and when the test needs it, `RecordFront` per the session plan) |
| Upload | Upload to comma.ai servers disabled for test and evaluation drives (device not paired, or uploads off, per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)); keeps evaluation data independent of future upstream training (DSR-05 of [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md)) |
| Retrieval | After each session, logs copied over a local connection to LionDriver storage; SHA-256 manifest created; drive sheet ID linked |
| Retention on device | Not deleted until the copy is verified (OPS-11) |
| Storage | Access limited to named project members; encrypted at rest; backups |
| Privacy | Consent forms for crew and test subjects (cabin video, voice if recorded); third-party faces and plates not published, blurred in reports; location traces treated as personal data |
| Retention period | Evaluation datasets and incident data: until the release they support is withdrawn plus 5 years **(TBC)**; other raw video: 24 months **(TBC)**; deletion on request where not needed for an incident |
| Incident data | Preserved unchanged (write-protected copy) until the incident is closed |

## 12. Legal, insurance and site matters

| Item | Status |
|---|---|
| Legal status of L2 development testing in the test state(s) | Open ([WP-C-01](../02-concept/WP-C-01-item-definition.md) OI-6) — must be confirmed before L4 |
| Insurance cover for development testing of an aftermarket driving assistance device | Open (OI-4) — must be confirmed before L3 |
| Closed-course site agreement and site rules | Open ([WP-V-01](WP-V-01-safety-validation.md) OI-1) |
| Vehicle registration and inspection current | Checked per session (PD-01…PD-06) |

## 13. Deviations

A deviation from this procedure is requested in writing by the test manager, states the rule, the reason, the alternative measures and the duration, and is approved by the safety manager before the test. While the maintainer holds both roles, a deviation for L3 or above needs agreement of an external reviewer (T-09). Deviations are listed in the campaign record and reviewed at the next gate.

## 14. Traceability

| Source | Addressed by |
|---|---|
| AOU-06, AOU-07 (driver) | §5 |
| AOU-08 (mounting/calibration) | PD-10, PD-16 |
| AOU-09, AOU-10 (vehicle) | PD-01…PD-06 |
| Gap action 10, WP-M-01 §9 risk | §1.1, §4 (L5 entry requires G1) |
| GAP-18, GAP-20, GAP-25, D-08 | §7.3, PD-12, PD-14 |
| GAP-16, GAP-19 (driver awareness) | §5.2 T1 |
| WP-V-01, WP-V-03, WP-V-04, WP-V-05 execution | §3, §4, §7.4, §8 |
| DSR-02, DSR-05, DSR-13 | §11 |

## Open items

| ID | Item |
|---|---|
| OI-1 | External review of this procedure by someone with vehicle-test or J3018 experience before first L5 use |
| OI-2 | Recruit and qualify at least one more safety driver / test operator so that two-person crews are possible; until then only L0–L4 and L3 sessions with a qualified second person are possible |
| OI-3 | Confirm that `OpenpilotEnabledToggle = 0` (passive, `noOutput`) leaves the stock camera and PCS path intact (repeat INS-27 in passive mode) |
| OI-4 | Confirm insurance cover |
| OI-5 | Design, build and verify the passenger abort switch (device power cut) and confirm the harness relay restores the stock camera path when the device is unpowered |
| OI-6 | Confirm the (TBC) values (licence years, takeover reaction time, L5 speed cap, lane-line margin, incident window, retention periods) with the external reviewer |
| OI-7 | Prepare consent forms, incident form and drive-sheet template as controlled documents (WP-P-04) |
