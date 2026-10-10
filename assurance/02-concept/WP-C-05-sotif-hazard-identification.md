# WP-C-05 SOTIF Hazard Identification and Risk Evaluation

| Field | Value |
|---|---|
| Work product | WP-C-05 SOTIF hazard identification and risk evaluation, acceptance criteria |
| Standard reference | ISO 21448:2022 §6 (hazard identification and risk evaluation, acceptance criteria), Annex B (misuse, informative); ISO 26262-3:2018 §6 (shared hazard log) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document identifies hazards that the **intended functionality** of LD-SDA can cause without any E/E fault: through insufficiencies of the specification, performance limits of perception, ML and planning, and reasonably foreseeable misuse. It evaluates their risk with the HARA method, links them to the functional-safety hazard log, and defines the acceptance criteria that later validation ([WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md)) must meet.

Scope: reference configuration ([WP-C-01](WP-C-01-item-definition.md)) inside the reference ODD ([WP-C-02](WP-C-02-odd-and-intended-functionality.md)). Experimental Mode is analysed (SH-09) because it is the upstream default, even though WP-C-02 §6.4 recommends excluding it.

Inputs: [WP-C-03 HARA](WP-C-03-hara.md) (H-01…H-06, H-08; OS-01…OS-11), `docs/LIMITATIONS.md`, gap assessment GAP-16…GAP-23, onboard code review.

## 2. Method

1. **Hazardous behaviour identification.** For each function F-01…F-07, ask: what output does the intended functionality produce that is hazardous in some situation of the ODD, while every component works as designed? Sources: `docs/LIMITATIONS.md`, known L2 field experience (WP-C-01 §6), the code review, and the misuse analysis ([WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md)).
2. **Numbering.** SH-0x matches H-0x where the vehicle-level effect is the same (hazard log convention, [WP-C-03 §7](WP-C-03-hara.md#7-hazard-log-cross-references)). H-07 does not exist in the HARA, so SH-07 is not used. SOTIF-only hazards start at SH-09.
3. **Severity and controllability.** Reused from the HARA hazardous event with the same effect and situation. Where no HARA event exists, rated here with the HARA scales and marked "new".
4. **Exposure** is not used to compute an ASIL (ISO 21448 does not assign ASILs). It is recorded to help set validation targets.
5. **Evaluation.** A hazard with S0 or C0 needs no further SOTIF treatment. Every other hazard goes into the triggering-condition analysis ([WP-C-06](WP-C-06-sotif-insufficiencies-triggering-conditions.md)) and needs an acceptance criterion (§5).

## 3. SOTIF hazards

| ID | Hazardous behaviour (intended function, no fault) | Function | Linked H | Example situations | S | C | Reused from / rationale |
|---|---|---|---|---|---|---|---|
| SH-01 | Model-commanded steering moves the vehicle out of the lane (wrong path: follows a wrong line, road edge, tar seam, exit lane, or reacts to a phantom obstacle) | F-01 | H-01 | OS-01, OS-03 (oncoming), OS-04 (VRU at edge) | S3 | C2 | HE-01.1–01.3. Lateral motion bounded by the same envelope; controllable by a supervising driver |
| SH-02 | Lateral control insufficient for the road: vehicle drifts out in curves tighter than the lateral limit, at lane-marking loss, in banking or cross-wind, without a timely take-over request | F-01, F-05 | H-02 | OS-02 highway curve, OS-03 rural curve | S3 | C2 | HE-02.1/02.2. `steerSaturated` gives only a warning (`events.py:619`) |
| SH-03 | Unintended acceleration: lead lost or misassociated (lead "drops out" in a curve or on cut-out), auto-resume from standstill into a VRU or vehicle, e2e acceleration | F-02 | H-03 | OS-05, OS-06, OS-07 | S3 | C2 | HE-03.1–03.3 (worst S taken). Auto-resume: `autoResumeSng` (`opendbc_repo/opendbc/car/toyota/interface.py:107`) |
| SH-04 | Unintended deceleration ("phantom braking"): false lead from radar (bridge, metal plate, toll booth), false vision lead, misread sign or light in Experimental Mode, FCW false positive leading to driver over-braking | F-02, F-06 | H-04 | OS-08 close follower; OS-11 wet curve | S2 | C2 | HE-04.1 (S2 C2), HE-04.2 (S3 C1). `LIMITATIONS.md:33` |
| SH-05 | Driver override not recognised or not effective as the driver expects: driver steering below the override threshold is resisted; gas press overrides but does not disengage, so the driver believes the system is off | F-03, F-05 | H-05 | OS-10 | S3 | C2 | HE-05.2/05.3. `DisengageOnAccelerator` default `0` (`common/params_keys.h:35`); host override threshold 500 raw (`carcontroller.py:33, 83`) |
| SH-06 | Insufficient deceleration: stationary or slow vehicle not treated as lead, late reaction to close cut-in, lead beyond radar/vision range at a crest, deceleration need above −3.5 m/s² | F-02 | H-06 | OS-07 approach to stationary traffic | S3 | C2 | HE-06.1. `LIMITATIONS.md:37-39`. Stock PCS not credited |
| SH-07 | — not used (no H-07 in the HARA) | — | — | — | — | — | — |
| SH-08 | Stock PCS performance degraded by the item's intended behaviour (e.g. openpilot longitudinal commands or forwarded/blocked messages that change PCS timing; PCS warnings missed because the device alert covers them) | F-02, F-08 | H-08 | OS-09 | S3 | C3 | HE-08.1. Intended forwarding is unverified (AOU-04) |
| SH-09 | Traffic-control non-compliance with over-trust: in Experimental Mode the driver expects the vehicle to stop for red lights and stop signs; the model misses one and the vehicle enters the intersection. In Chill mode the same over-trust can arise from confusion between modes | F-02, F-05 | new (effect like H-03/H-06) | Signalised intersection in ODD-A, cross traffic | S3 | C2 | New. S3: side impact or VRU at intersection speed. C2: driver supervising, but trained expectation delays braking. Without Experimental Mode the expectation does not arise from the function itself |
| SH-10 | Assisted lane change into an occupied lane: driver nudges after signalling; the system does not check the blind spot | F-01 | new (effect like H-01) | OS-01 multi-lane highway | S3 | C2 | New. `LIMITATIONS.md:6`. The reference Corolla LE is assumed to have no blind-spot input (`desire_helper.py:48` would use it if present). Controllable: driver initiated and can abort |
| SH-11 | No reaction to a VRU in or entering the path (pedestrian crossing, cyclist in lane) | F-01, F-02 | new (effect like H-06) | OS-04, OS-06 | S3 | C2 | New. `LIMITATIONS.md:34`. Lead logic is vehicle-oriented (`radard.py:153-165`). Stock PCS pedestrian AEB exists but is not credited |
| SH-12 | Prolonged unsupervised operation: DM does not detect inattention (sunglasses, glare, face out of view, wheel-touch fallback reset by small inputs), so warnings and the force-decel stage come late or never | F-04 | Contributes to all; no direct H | Any, esp. long highway drives | — | — | Not a vehicle-level hazard on its own (HARA §4). It removes the controllability basis (C2) of SH-01…SH-11. Handled as a misuse-enabling insufficiency in WP-C-08 |
| SH-13 | System stays engaged outside the ODD: above 120 km/h (up to and above 149 km/h, where only a warning is given), in construction zones, in heavy rain, on roads without markings | all | Increases probability of SH-01…SH-06 | ODD exit | as linked SH | as linked SH | New. `events.py:989-996` (no disengage). The model's training distribution is unknown (GAP-22) |

## 4. Foreseeable misuse considered

Misuse cases are analysed in [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) §6. Those that change the SOTIF hazards here:

| Misuse (WP-C-08 ID) | Effect on SH |
|---|---|
| Hands-off, eyes-off driving, phone use (MC-01, MC-02) | Raises the C of SH-01…SH-11 towards C3; partly countered by DM |
| Sleeping / incapacitated driver (MC-03) | DM no-response → force decel; until then SH-02, SH-06 uncontrolled |
| DM camera covered, demo mode, defeat devices (MC-04, MC-05, MC-06) | Removes the DM safeguard → SH-12 |
| Use outside ODD (MC-07) | SH-13 |
| Over-trust after Experimental Mode default (MC-09) | SH-09, SH-11 |

## 5. Acceptance criteria

### 5.1 Approach

The top-level claim ([WP-M-01 §3.2](../01-management/WP-M-01-assurance-strategy.md#32-top-level-claim)) is that residual risk is **no worse than manual driving of the same vehicle with its stock TSS 2.0 assistance**. The acceptance criteria follow that claim in two layers:

1. **Quantitative residual-risk criterion (per SH group).** The rate of harm caused by SH-xx while engaged shall not exceed the corresponding rate for human drivers in comparable conditions (same road types, US), reduced by a factor that reflects that the stock vehicle with LKA/ACC is the comparison baseline. The specific numbers are **deferred to [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md)** (validation targets VT-nn), derived as in §5.2.
2. **Qualitative criteria** that do not need statistics and are checked by analysis and test (§5.3).

### 5.2 Derivation method for validation targets (to be applied in WP-V-02)

1. **Baseline rate.** Take the human-driver crash rate A_H for the relevant severity (e.g. injury crashes, fatal crashes) and road class from US public data (NHTSA FARS / CRSS, FHWA VMT). Record source, year and road class. Use the road-class-specific rate (Interstate vs arterial), not the national average.
2. **Stock TSS2 baseline.** Where data allow, adjust A_H for vehicles with LKA/ACC/PCS (published insurance or NHTSA studies). If no adequate data exist, use A_H and state the assumption.
3. **Allocation.** Split the acceptable rate across SH groups (lateral SH-01/02/10, longitudinal SH-03/04/06/11, mode/override SH-05/09, SH-08) in proportion to their share of the baseline crash types. Record the split.
4. **Controllability credit.** Not every hazardous behaviour leads to harm: the driver controls most. The share of uncontrolled events is estimated from controllability tests ([WP-C-08 §8](WP-C-08-driver-hmi-misuse-analysis.md)). Using it lets the target be expressed as a rate of **hazardous behaviours** (e.g. lane exits, unexpected decelerations > x m/s²) per km, which is measurable.
5. **Target distance.** For a zero-event demonstration at confidence 1 − α, the required exposure is d = −ln(α) / λ (≈ 3/λ for 95 %). With observed events, use the chi-square bound. The required distance is per ODD part (ODD-H, ODD-A).
6. **Evidence mix.** Distance can be split between fleet/replay data (driving-model replay on fork-owned logs), simulation and on-road validation, with the weighting justified in WP-V-02.

### 5.3 Qualitative acceptance criteria

| ID | Criterion | Applies to | Checked by |
|---|---|---|---|
| AC-01 | All known triggering conditions in WP-C-06 are evaluated, and each is either acceptable, removed by a functional modification ([WP-C-07](WP-C-07-sotif-functional-modifications.md)), or excluded from the ODD with user information | All SH | Review of WP-C-06 |
| AC-02 | Every actuation produced by the intended function stays inside the envelope limits whose controllability is demonstrated | SH-01, 03, 04 | Analysis + test (FSR-01.01, 03.01, 04.01) |
| AC-03 | Every insufficiency the system can detect leads to a take-over request within 1 s; no actuation on inputs known to be invalid | SH-02, SH-06 | Test; FM-02, FM-03 |
| AC-04 | No function is active by default whose hazards have not been evaluated (Experimental Mode, debug modes) | SH-09, SH-13 | Configuration review; FM-01, FM-06 |
| AC-05 | Driver monitoring meets the misuse detection performance set in WP-C-08 §5 and cannot be bypassed by a configuration parameter | SH-12 | Test; FM-05, FM-06 |
| AC-06 | The stock PCS function is shown unchanged (target tests with and without the item) | SH-08 | Vehicle test (AOU-04) |
| AC-07 | Unknown-scenario exploration (WP-V-04) finds no new hazardous scenario class in the final validation campaign, or each found is addressed | All | WP-V-04 |

## 6. Risk evaluation summary

| SH | Needs further SOTIF treatment | Key insufficiency areas (WP-C-06) | Proposed modifications (WP-C-07) |
|---|---|---|---|
| SH-01 | Yes | Driving model path, calibration | FM-09, FM-10 |
| SH-02 | Yes | EPS authority, curvature limits, lane-line loss | FM-03, FM-10 |
| SH-03 | Yes | radard association, auto-resume, e2e | FM-01, FM-11 |
| SH-04 | Yes | radar false targets, e2e false stops | FM-01, FM-09 |
| SH-05 | Yes | Override thresholds, gas override semantics | (WP-C-08 HMI measures), FSR-05.03 |
| SH-06 | Yes | Stationary objects, cut-ins, decel limit | FM-09, user info |
| SH-08 | Yes | Harness/forwarding, PCS arbitration | (FSR-07.x), AOU-04 test |
| SH-09 | Yes (if Experimental Mode kept) | e2e traffic-control | FM-01 |
| SH-10 | Yes | No blind-spot sensing | User info; WP-C-08 |
| SH-11 | Yes | No VRU response | ODD restriction (ODD-A), user info |
| SH-12 | Yes (enabling) | DM model, policy | FM-05, FM-06 |
| SH-13 | Yes | No ODD monitor | FM-07, FM-08 |

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm S/C ratings for new hazards SH-09, SH-10, SH-11 in the shared hazard log (WP-C-03 §7) | HARA owner | G1 |
| OI-2 | Decide whether SH-09/10/11 also need functional-safety hazardous events (E/E fault causing the same effect) | HARA owner | G1 |
| OI-3 | Select the human-driver baseline data sources and road-class split for §5.2 | SOTIF lead | G2 |
| OI-4 | Confirm whether the reference vehicle has a blind-spot monitor input (affects SH-10) | Maintainer | G1 |
| OI-5 | Update the HARA cross-reference table (WP-C-03 §7) to include SH-09…SH-13 | HARA owner | G1 |
