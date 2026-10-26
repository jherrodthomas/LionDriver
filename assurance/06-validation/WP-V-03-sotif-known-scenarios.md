# WP-V-03 Evaluation of Known Hazardous Scenarios

| Field | Value |
|---|---|
| Work product | WP-V-03 Evaluation of known hazardous scenarios (specification and results) |
| Standard reference | ISO 21448:2022 §10 (verification of the SOTIF, known hazardous scenarios); ISO/PAS 8800:2024 (AI V&V); ASPICE 4.0 SYS.5, VAL.1 |
| Version | 0.10 (§2 B2 row: paired closed-course runs against stock TSS2, DQ-138 A; KS-01, KS-03, KS-08, KS-09, KS-11 and KS-27 now marked B2 beside KS-05, KS-07 and KS-20, with the metric compared per scenario and why the others get no pair; §4 B2 row; OI-3 names the queued site question DQ-041; 2026-10-25). 0.9 (KS-27: the reveal gap depends on the radius, 40–80 m at 250–400 m with a barrier at or just outside the lane edge, about 95 m at 600 m; 2026-10-19). 0.8 (KS-27: lead detected late in a curve while accelerating to the set speed, TC-35, from RR-2026-011 F-6; 2026-10-19). 0.7 (KS-20 names TC-34 and FI-23, the stock PCS interaction added to WP-C-06; 2026-10-18). 0.6 (simulation credit rule decided by the lead, DQ-139: §2 and §5.4; 2026-10-16). 0.5 (KS-25 at the 110 km/h ODD bound, decision register DQ-260; 2026-10-16). 0.4 (§5.4: first simulation result recorded as synthetic data with no credit, SIM-2026-001 from the layer-1 plant model; OI-7; 2026-10-16). 0.3 (simulation rule: synthetic-data labelling and scenario families per WP-V-02 §5.3; 2026-10-16). 0.2 (the lead's decisions applied: highways only, decision register DQ-023, KS-22 re-scoped to the highway shoulder and OI-2 closed; public-road limits, DQ-046; closed-course speeds to 110 km/h, DQ-091; logs kept by LionDriver, DQ-084; model-change re-runs, DQ-038; 2026-10-16). 0.1 |
| Status | Draft (specification). Results section is a template: **Not yet executed** |
| ASIL / scope | SOTIF |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (SOTIF lead) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document lists the known hazardous scenarios for LD-SDA, the test method and pass criteria for each, and the record format for results. It implements the strategy of [WP-V-02](WP-V-02-sotif-vv-strategy.md) (methods M1–M9, validation targets VT-nn).

Source of the scenarios. The catalogue is derived from:
- the triggering conditions TC-01…TC-33 and functional insufficiencies FI-01…FI-22 of [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) and the SOTIF hazards SH-01…SH-13 of [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md);
- `docs/LIMITATIONS.md:8-56` (upstream's own list of conditions that degrade ALC, ACC/FCW and DM);
- the gap assessment (GAP-16, GAP-17, GAP-18, GAP-21, GAP-22);
- the HARA situation catalogue OS-01…OS-11 and hazards H-01…H-08 ([WP-C-03](../02-concept/WP-C-03-hara.md));
- AI error types AE-P/L/T/O/N/D ([WP-C-11 §5](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md#5-ai-related-error-types));
- domain knowledge of camera-based L2 systems.

Every TC of WP-C-06 maps to at least one KS (coverage table in [WP-V-02 §6](WP-V-02-sotif-vv-strategy.md#6-coverage-of-triggering-conditions)). KS-06 and KS-08 cover TC-32 and TC-33, added to WP-C-06 at this document's request (OI-1, closed). TCs that WP-C-06 resolves by ODD exclusion ([WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md): work zones, fog/snow, tunnels) get an ODD-exit check instead of a performance test.

Scope: reference configuration, Chill longitudinal mode. Experimental Mode scenarios (traffic lights, stop signs, e2e stops) are excluded (FM-01, D-08); KS-24 only verifies that the exclusion holds. Scenarios run in ODD-H, the only ODD part since 2026-10-14 (decision register DQ-023 option B).

## 2. General test conditions

| Item | Rule |
|---|---|
| Configuration | Released software tag, pinned models (hashes recorded), parameters per [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-19; INS-21…INS-25 passed before the campaign |
| Vehicle operations | All vehicle tests under [WP-V-07](WP-V-07-vehicle-test-operations.md). Closed-course (CC) tests at the test level and with the crew rules defined there. Public-road (PR) tests only after G1 |
| Logging | Full logs kept in the LionDriver log store, not uploaded to comma's servers (DQ-084 option A); bookmark at each trial start; drive sheet per WP-V-07 §10 |
| Speeds | Engaged public-road (M9) trials at ≤ 105 km/h and within the 0.5 m abort margin (WP-V-07 limits adopted by the project lead, DQ-046 option A). Closed-course (M8) points up to 90 km/h, and up to 110 km/h only after the risk review the lead decided to hold (DQ-091 option A). Points above that run by M4/M5 only |
| Measurement | Lateral position: lane-line annotation on road video, or survey markers on the closed course plus video. Distances to targets: course markers and radar track. Driver inputs: `carState` (steering torque, pedals) |
| B2 comparison | Paired runs on the closed course (decided 2026-10-25, DQ-138 A; method in [WP-V-02 §2.2](WP-V-02-sotif-vv-strategy.md#22-b2-paired-runs-against-stock-tss2-dq-138)). Where marked "B2", each parameter point is run with LD-SDA and with the stock TSS2 functions (Lane Tracing Assist / DRCC), same speeds and targets, several runs per arm, logged on the device. The stock arm needs the item passive or the harness removed (OI-4, WP-V-07 OI-3), recorded per trial. **Paired, with the metric compared:** KS-01, KS-03 (peak lateral excursion; for KS-01 also the alert time before it); KS-05, KS-09 (contact or minimum gap, TTC at first deceleration and at FCW); KS-07, KS-08, KS-27 (contact or minimum gap, peak deceleration, any acceleration toward the target; KS-27 only where the site has a curve that hides the target); KS-11 (peak deceleration with no relevant object, CC metal plate); KS-20 (PCS timing, VT-07). **Not paired:** KS-02, KS-04, KS-06, KS-10, KS-12, KS-13, KS-15 (public road or recorded data, where traffic differs run to run; option B of DQ-138 not chosen); KS-14 (the stock car has no lane-change function); KS-16, KS-19, KS-21, KS-24…KS-26 (the item's own functions, no stock counterpart); KS-17, KS-18 (driver monitoring; the stock car has none); KS-22, KS-23 (the stock lane and cruise functions have no VRU response to compare; the stock PCS is compared in KS-20) |
| Trial count | Per VT-nn: zero-failure demonstration of p ≤ 5 % needs 59 trials, p ≤ 1 % needs 299 (95 % confidence). Closed-course trials start with an exploratory set of 10 per parameter point and are extended where the WP-V-02 target requires it |
| Abort | Any trial is aborted by the safety driver per WP-V-07 §8; an aborted trial counts as a **failure** unless the abort cause is unrelated to the item (recorded) |
| Simulation | MetaDrive (M4) results are recorded but get no credit until the WP-V-02 §5.3 fidelity case is approved for that scenario family (decided by the project lead, DQ-139 option A). Each result is labelled as synthetic (WP-V-02 §5.3.5, DSR-12), reported on its own line and never pooled with real-world trials. Families and the scenarios MetaDrive cannot represent: WP-V-02 §5.3.2 |

Abbreviations: M1 process replay, M3 model evaluation on recorded data, M4 MetaDrive simulation, M5 longitudinal planner maneuver tests (`openpilot/selfdrive/test/longitudinal_maneuvers/`), M8 closed course, M9 public road with safety driver. "Fail" means the pass criterion is not met in a trial.

## 3. Scenario catalogue

### 3.1 Lateral scenarios

| ID | Scenario | SH | TC (WP-C-06) | Parameters | Methods | Pass criteria | VT |
|---|---|---|---|---|---|---|---|
| KS-01 | Curve at or beyond the lateral capability (ramps, interchange loops) | SH-02, SH-01 | TC-14 | Radius 150–500 m; speed such that required lateral acceleration is 2.0, 2.5, 3.0, 3.5 m/s² | M3, M4, M8 (B2), M9 | Below 3.0 m/s²: lane keeping within ±0.5 m. At or above the controller limit: a take-over alert (`steerSaturated` or equivalent) is issued **before** the outer wheel crosses the lane line, and ≥ 1 s before a 0.5 m lane excursion (SG-02 budget). No unannounced departure | VT-01, VT-02, VT-09 |
| KS-02 | Banked or crowned road, steady crosswind | SH-01, SH-02 | TC-15, TC-16 | Bank 2–6 % or crosswind ≥ 30 km/h (natural, recorded) | M9, M3 | Lateral offset within ±0.5 m; no envelope torque saturation lasting > 2 s without alert | VT-01 |
| KS-03 | Faded or missing lane markings, tar seams, repainted lines | SH-01, SH-02 | TC-05 | Marking visibility classes: good / faded / one side missing / ghost lines | M3, M8 (taped lines, B2), M9 | No lane departure; if `laneLineProbs` < 0.5 on both sides for > 2 s, a take-over alert or no change of lateral offset > 0.3 m | VT-01, VT-02, VT-09 |
| KS-04 | Lane split, exit gore, lane merge, widening lane | SH-01 | TC-31 | Highway exit with and without exit desire; merge from 2 to 1 lane | M3, M9 | Vehicle follows the through lane without crossing the gore; no swerve > 0.5 m toward the exit | VT-01 |
| KS-05 | Stationary vehicle in lane at highway approach | SH-06 (SH-04 if late hard braking) | TC-08, TC-17 | Soft target (radar-reflective) stationary; approach 40, 60, 80 km/h on CC (higher speeds by M5/M4 only); lateral offset 0 and ±0.5 m | M5, M8 (B2), M3 | Stop without contact; first deceleration at TTC ≥ 3.0 s **(TBC)**; FCW at TTC ≥ 2.0 s where braking above envelope is needed (AIR-06); not worse than stock DRCC (B2) | VT-06, VT-09 |
| KS-06 | Narrow lane with adjacent truck or concrete barrier | SH-01 | TC-32 (FI-01) | Lane width ≤ 3.3 m; adjacent large vehicle | M9, M3 | Lateral offset toward the obstacle ≤ 0.3 m; no move toward the obstacle | VT-01 |
| KS-14 | Driver-initiated lane change (turn signal + nudge) | SH-10 | TC-28 | Adjacent lane free / occupied (target vehicle at 2–3 s gap on CC) | M8, M9 | Lane change starts only after the driver nudge; aborts / does not start when the driver releases the signal; driver can override at any point with ≤ the AOU-02 force | VT-13 |
| KS-22 | Pedestrian on the highway shoulder, for example beside a broken-down vehicle (VRU response is a driver task per WP-C-02; re-scoped from the arterial lane edge after DQ-023) | SH-11, SH-01 | TC-12 | Dummy at 0.5 m and 1.0 m beyond the edge line, stopped vehicle on the shoulder; ego at 50 and 80 km/h | M8, M4 (no credit) | No lateral move toward the dummy > 0.2 m; driver can correct within the envelope | VT-01 |

### 3.2 Longitudinal scenarios

| ID | Scenario | SH | TC (WP-C-06) | Parameters | Methods | Pass criteria | VT |
|---|---|---|---|---|---|---|---|
| KS-07 | Close cut-in | SH-03, SH-06 | TC-07 | Target cuts in at 10, 15, 20 m ahead; Δv −10…0 km/h | M5 (`test_longitudinal.py:113`), M8 (B2) | No contact; no positive acceleration toward the target after it enters the lane; deceleration ≤ −3.5 m/s² envelope; not worse than stock (B2) | VT-03, VT-06, VT-09 |
| KS-08 | Lead decelerating hard, slow lead at highway speed | SH-03, SH-06 | TC-33 (FI-10) | Lead brakes at 3, 5, 7 m/s² from 50/80 km/h; time gap 1.5 s | M5, M8 (soft target on trolley, lower speeds; B2), M3 | No contact where the envelope allows avoidance; FCW at TTC ≥ 2.0 s when required deceleration > 3.5 m/s²; no positive acceleration while the lead decelerates | VT-03, VT-06, VT-09 |
| KS-27 | Lead detected late in a curve while accelerating to the set speed | SH-03, SH-06 | TC-35 (FI-04, FI-06, FI-07) | Ego below set speed entering a curve of radius 250–600 m (ramp or interchange) at 50–90 km/h; slower or stopped lead hidden by an inside barrier until 40–80 m at radius 250–400 m, and until about 95 m at 600 m, the closest a barrier at the lane edge allows (reveal gap ≈ √(8·R·m), m = clearance from lane centre to the barrier); set speed 20–30 km/h above ego speed | M5, M8 (soft target, B2 where the site allows), M3 replay of recorded ramps | No positive acceleration toward the lead once it is in the path; deceleration within the −3.5 m/s² envelope; FCW at TTC ≥ 2.0 s when the required deceleration exceeds 3.5 m/s²; no contact where the envelope allows avoidance | VT-03, VT-06, VT-09 |
| KS-09 | Cut-out revealing a stopped vehicle | SH-06 | TC-09 | Lead changes lane at 30–60 m from a stopped target, 50 km/h | M8 (B2) | As KS-05 | VT-06, VT-09 |
| KS-10 | Overpass, bridge shadow, overhead gantry | SH-04 | TC-10 | Recorded highway segments with overpasses | M3, M9 | No deceleration < −2.0 m/s² without a relevant object (AIR-05) | VT-04 |
| KS-11 | Metal plates, toll plaza, roadside radar clutter, parked cars on a curve | SH-04 | TC-10, TC-11 | Recorded segments; CC metal plate | M3, M8 (B2, metal plate), M9 | As KS-10 | VT-04, VT-09 |
| KS-23 | Stop-and-go queue and resume; pedestrian crossing in front of the stopped vehicle | SH-03, SH-11 | TC-27 | Stopped behind lead; lead leaves; dummy crosses 3 m ahead | M5 (`test_longitudinal.py:171` "resume from a stop"), M8 | No launch while an obstacle is in front; resume only after driver confirmation where the vehicle requires it (`resumeRequired`) | VT-03 |

### 3.3 Perception-environment scenarios

| ID | Scenario | SH | TC (WP-C-06) | Parameters | Methods | Pass criteria | VT |
|---|---|---|---|---|---|---|---|
| KS-12 | Low sun, oncoming headlights, tunnel entry/exit | SH-01, SH-02, SH-06 | TC-01, TC-02, TC-18 | Sun elevation < 15° ahead (outside ODD when directly in view: ODD-exit check); night with oncoming traffic; tunnel transitions (excluded until validated: recorded data only) | M3, M9 | AIR-01/03/05 metrics within thresholds in the stratum, **or** a monitor flag/alert precedes degradation (AIR-14). Otherwise the stratum is removed from the ODD | VT-01, VT-04, VT-06 |
| KS-13 | Construction zone, temporary markings, cones | SH-13, SH-01 | TC-06 (outside ODD) | Recorded segments; CC with cones and conflicting tape lines | M3, M8, M9 | Work zones are outside the ODD (WP-C-02 §3.1). Check: the safety driver procedure (WP-V-07 A-06) and user information lead to disengagement before the zone; if FM-08 adds detection, the item requests take-over before the first cone. Recorded segments also measure behaviour if the driver did not disengage (no credit) | VT-12 |
| KS-15 | Light rain, wet road reflections (ODD edge) | SH-01, SH-04 | TC-03 (TC-04 outside ODD) | Light rain recorded; heavy rain = outside ODD | M3, M9 | Light rain: metrics within thresholds; heavy rain: driver procedure (WP-V-07 abort) | VT-01 |
| KS-16 | Camera obstruction, dirty windscreen, mis-mount, calibration drift | SH-01, SH-02 | TC-19 | Masks 5–30 % on CC (stationary obstruction film); device tilted outside INS-25 tolerance | M3 (perturbation), M8 | Calibration outside limits blocks engagement (`calibrationInvalid`); obstruction → monitor flag or degraded but in-lane behaviour; no unannounced departure | VT-01, VT-02 |

### 3.4 Driver-monitoring and driver-interaction scenarios

| ID | Scenario | SH | TC (WP-C-06) | Parameters | Methods | Pass criteria | VT |
|---|---|---|---|---|---|---|---|
| KS-17 | DM under night, glare, sunglasses, glasses | SH-12 | TC-24 | Day/night; IR-opaque and IR-transparent sunglasses; low sun on face | WP-W-10 VS-ML-06 (M3), M8 parked + CC | Scripted look-away detected per AIR-07 timing; if the model is uncertain, the wheel-touch fallback activates (`policy.py:82-83`); no stratum where distraction is missed **and** no fallback is active | VT-08 |
| KS-18 | Distraction behaviours and face out of view | SH-12 | TC-24, TC-25 | Phone in lap / at ear, looking at passenger, eyes closed, leaning out of camera view | VS-ML-06, M8 | Alerts follow 5/8/13 s vision timers (`policy.py:34-36`); no-response → forced deceleration (`policy.py`, `noResponseForceDecel`); lockout counts as specified | VT-08 |
| KS-19 | Driver override interactions | SH-05 | TC-29 | Steering override in a curve; gas override while following; brake tap; cancel button; at 30/60/90 km/h | M8 (≥ 299 trials per input type for VT-05, accumulated over campaigns) | Release within the SG-05 budget (≤ 0.2 s preliminary) for brake and cancel; steering override possible with ≤ AOU-02 force; no residual torque after disengagement | VT-05 |

### 3.5 Vehicle-integration and system scenarios

| ID | Scenario | SH | TC (WP-C-06) | Parameters | Methods | Pass criteria | VT |
|---|---|---|---|---|---|---|---|
| KS-20 | Stock PCS activation with the item installed | SH-08 | TC-34 (FI-23); AOU-04R | Soft target, stock PCS speeds (e.g., 20–40 km/h); LD-SDA engaged, disengaged and not installed | M8 (B2) | PCS warning and braking occur at the same TTC ± 0.2 s as without the item (VT-07). Shared with WP-V-01 VS-VAL for AOU-04 | VT-07 |
| KS-21 | Internal degradation while engaged: model lag, frame drops, stale model output, process crash, soft-disable window | SH-01, SH-02, SH-06 | TC-21, TC-23 | Induced by CPU load, process kill, camera stream interruption (bench and CC only) | M1, M4, M8 (with WP-V-05 fault-injection rules) | Take-over alert within the SG-02 budget; actuation during the soft-disable window stays within the lane (GAP-16); no actuation on stale (> AIR-17 limit) model output | VT-02 |
| KS-24 | Exclusion check: Experimental Mode and Chestnut not active | SH-09, SH-12, SH-13 | TC-13, TC-22, TC-26 | Fresh install, parameter dump, ignition cycles, settings UI | Inspection | `ExperimentalMode` off and locked (FM-01); no big-model artefacts present (FM-02, AIR-30); debug, maneuver, joystick and DM demo modes cannot be set (FM-06) | AC-04 |
| KS-25 | Speed above the ODD bound | SH-13 | TC-20 | Set speed and actual speed crossing the ODD-H bound (110 km/h, DQ-260) on CC where the site allows, otherwise by M1 replay with synthetic `carState` | M1, M8 | With FM-07: engagement refused / take-over requested at the bound in every trial. Baseline behaviour (warning only above ≈ 149 km/h, `events.py:989-996`) is recorded as a known failure until FM-07 exists | VT-12 |
| KS-26 | PCM cruise stays active after an item disengagement | SH-05 | TC-30 | Injected `cruiseMismatch` condition on HIL, then CC | M1, M8 (WP-V-05 rules) | With FM-04: driver warned and cancel requested within the FSR-05.06 bound. Baseline (event without reaction, `events.py:458-460`) recorded as a known failure | VT-05 |

## 4. Scenario-to-requirement coverage

| Requirement / target | Scenarios |
|---|---|
| AIR-01, AIR-02, VT-01 | KS-01…KS-04, KS-06, KS-12…KS-16, KS-22 |
| AIR-03, AIR-04, AIR-06, VT-06 | KS-05, KS-07…KS-09, KS-27 |
| AIR-05, VT-04 | KS-10, KS-11, KS-12 |
| AIR-07, AIR-08, VT-08 | KS-17, KS-18 |
| AIR-11, VT-14 | Steady segments of KS-01…KS-06; KS-07, KS-08, KS-10, KS-11 |
| AIR-14, VT-15 | KS-12, KS-13, KS-16 |
| AIR-17, AIR-25, GAP-16 | KS-21 |
| SG-05 / VT-05 | KS-19 |
| SG-07 / VT-07 | KS-20 |
| B2 / VT-09 (paired runs, DQ-138 A) | KS-01, KS-03, KS-05, KS-07, KS-08, KS-09, KS-11, KS-27; KS-20 through VT-07 |
| D-08, FM-01, FM-02, FM-06, AIR-29, AIR-30 | KS-24 |
| FM-07, SH-13 | KS-13, KS-25 |
| FM-04, SH-05 | KS-19, KS-26 |
| SH-10, VT-13 | KS-14 |
| SH-11 | KS-22, KS-23 |

## 5. Results

**Not yet executed.** No scenario in this catalogue has been run on LionDriver software. §5.4 records simulation results, which are synthetic and give no credit. The upstream `longitudinal_maneuvers` tests exist but have not been run in LionDriver CI against a LionDriver baseline, and their results are not traced to these scenarios.

### 5.1 Campaign record template

| Field | Value |
|---|---|
| Campaign ID | KS-CAMP-<yyyy>-<nn> |
| Software tag / commit | |
| Model hashes (AI-1, AI-3) | |
| Panda firmware version / signature | |
| Vehicle / device IDs | |
| Site / route | |
| Dates, weather, light | |
| Crew (safety driver, test operator) | |
| Test level (WP-V-07) | |
| Deviations from specification | |

### 5.2 Per-scenario result template

| KS | Method | Parameter point | Trials | Fails | Aborts (item-related / unrelated) | Metric summary | B2 result | Upper bound p (95 %) | Verdict | Log IDs |
|---|---|---|---|---|---|---|---|---|---|---|
| KS-01 | | | | | | | | | Not yet executed | |
| KS-02 | | | | | | | | | Not yet executed | |
| KS-03 | | | | | | | | | Not yet executed | |
| KS-04 | | | | | | | | | Not yet executed | |
| KS-05 | | | | | | | | | Not yet executed | |
| KS-06 | | | | | | | | | Not yet executed | |
| KS-07 | | | | | | | | | Not yet executed | |
| KS-08 | | | | | | | | | Not yet executed | |
| KS-09 | | | | | | | | | Not yet executed | |
| KS-10 | | | | | | | | | Not yet executed | |
| KS-11 | | | | | | | | | Not yet executed | |
| KS-12 | | | | | | | | | Not yet executed | |
| KS-13 | | | | | | | | | Not yet executed | |
| KS-14 | | | | | | | | | Not yet executed | |
| KS-15 | | | | | | | | | Not yet executed | |
| KS-16 | | | | | | | | | Not yet executed | |
| KS-17 | | | | | | | | | Not yet executed | |
| KS-18 | | | | | | | | | Not yet executed | |
| KS-19 | | | | | | | | | Not yet executed | |
| KS-20 | | | | | | | | | Not yet executed | |
| KS-21 | | | | | | | | | Not yet executed | |
| KS-22 | | | | | | | | | Not yet executed | |
| KS-23 | | | | | | | | | Not yet executed | |
| KS-24 | | | | | | | | | Not yet executed | |
| KS-25 | | | | | | | | | Not yet executed | |
| KS-26 | | | | | | | | | Not yet executed | |
| KS-27 | | | | | | | | | Not yet executed | |

Verdict values: Pass / Fail / Insufficient trials / Not yet executed. A Fail opens a problem report ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)) and a WP-C-06 update; the decision (functional modification, ODD restriction, or accepted with rationale) is recorded here and in [WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md).

### 5.3 Re-execution triggers

The suite (or the affected scenarios) is re-run after any change listed in [WP-W-10 §8](../05-software/WP-W-10-ml-engineering.md) and [WP-M-08 §9](../01-management/WP-M-08-sotif-plan.md#9-change-triggered-re-evaluation-including-model-changes), and when field monitoring adds a scenario. Every change of model weights or of the tinygrad runtime is such a change (D-05, adopted as written by the project lead on 2026-10-14, decision register DQ-038 option A).

### 5.4 Simulation results (synthetic data, no credit)

Results from the simulation track ([`assurance/sim/`](../sim/README.md)), recorded under the rule of §2 and [WP-V-02](WP-V-02-sotif-vv-strategy.md) §5.3.5. They are synthetic data (DSR-12): they are not pooled with the trials of §5.2, they set no verdict there, and they get **no evidence credit**. Credit is possible per scenario family once its fidelity case is approved (DQ-139 option A); no family has one yet. They are used to rank risks and to choose closed-course parameter points.

| Run | Source | Layer and model | Scenario | Relates to | Result | Use |
|---|---|---|---|---|---|---|
| SIM-2026-001 | [`plant-results.md`](../sim/results/plant-results.md) case N-3, PR #104 (merged 2026-10-16) | Layer 1 fault-injection plant: the real panda safety code (reference build) in the loop. A stand-in lateral controller, **not openpilot**. Single-track vehicle model with the opendbc Corolla CarParams. EPS lag and driver model assumed | No fault; 120 km/h; clothoid into a left curve at the ODD bound R_ODD = v²/2.5 m/s² | KS-01 (TC-14, SH-02), VT-02; [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) OI-2 | The steering saturates: at full envelope torque, openpilot's torque map for this platform (`latAccelFactor` 1.99 m/s²) gives less lateral acceleration than R_ODD needs (2.5 m/s²). The car drifts outward, up to 0.80 m. Its body edge reaches the line of a 3.0 m lane 3.71 s after curve entry. It stays inside a 3.7 m lane. The model's driver notices at 2.10 s and corrects at 3.60 s | **Hypothesis to test, not a finding.** If the vehicle confirms it, R_ODD (WP-C-02 §3.2) is beyond the item's steering authority at this speed, and KS-01's 2.5 m/s² point is a beyond-capability point. KS-01 then needs the take-over alert before the outer wheel crosses the line (§3.1). Closed-course KS-01 points at 2.0 and 2.5 m/s² and the lateral step tests of WP-V-01 decide it (OI-7) |

What the run cannot show:
- openpilot's own lateral behaviour, or whether `steerSaturated` would alert in time: the controller is a stand-in;
- the real EPS authority: the torque map is openpilot's fit, not a measurement on the reference vehicle (AOU-01, GAP-04).

## Open items

| ID | Item |
|---|---|
| OI-1 | Closed: WP-C-06 added TC-32 (KS-06, narrow lane next to a large vehicle or barrier) and TC-33 (KS-08, lead braking harder than the envelope allows) |
| OI-2 | Closed 2026-10-16: the project lead dropped ODD-A (DQ-023 option B). The ODD-A parameter points are removed and KS-22 is re-scoped to a pedestrian on the highway shoulder |
| OI-3 | Select the closed-course site and soft-target equipment (radar-reflective target, trolley) and confirm speed limits per WP-V-07. The site is a question still queued for the project lead (DQ-041). The soft targets for stopped and cut-in vehicles that the B2 paired runs need (DQ-138 A) are stage 2 of the equipment purchase, which waits on a site booking (DQ-043 B; WP-V-07 §8.1.1) |
| OI-4 | Define how B2 runs restore the stock TSS2 functions (harness removal procedure and time per swap) |
| OI-5 | Port the relevant `longitudinal_maneuvers` cases into LionDriver CI with traceability to KS-05, KS-07, KS-08, KS-23 |
| OI-6 | Confirm the (TBC) thresholds with WP-V-02 OI-3 before the first campaign |
| OI-7 | Check SIM-2026-001 (§5.4) on the vehicle: measure the lateral acceleration at full envelope torque (WP-V-01 lateral step tests), and run KS-01 at 2.0 and 2.5 m/s² on the closed course. If the authority is below 2.5 m/s², R_ODD changes (WP-C-02 OI-2), and KS-01's pass criterion at that point becomes the take-over alert |
