# WP-C-06 Functional Insufficiencies and Triggering Conditions

| Field | Value |
|---|---|
| Work product | WP-C-06 Functional insufficiencies and triggering conditions analysis |
| Standard reference | ISO 21448:2022 §7 (identification and evaluation of functional insufficiencies and triggering conditions); ISO/PAS 8800:2024 (AI error causes, informative) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose and method

This document lists the functional insufficiencies (FI-nn) of LD-SDA and the triggering conditions (TC-nn) that can activate them, links each pair to the SOTIF hazards of [WP-C-05](WP-C-05-sotif-hazard-identification.md), and evaluates whether the system's response is acceptable.

- **Specification insufficiency (S):** the specified behaviour itself is hazardous in some situation (e.g. soft disable keeps actuating on failed inputs).
- **Performance insufficiency (P):** the specification is fine, but a component does not perform well enough in some conditions (e.g. lane perception in glare).
- **Sources:** `docs/LIMITATIONS.md`, the onboard code review, the gap assessment (GAP-16…GAP-23), and domain knowledge of camera/radar L2 systems.
- **Evaluation outcome:** `Acceptable` (risk is low and controllable; user information suffices), `Needs modification` (a functional modification in [WP-C-07](WP-C-07-sotif-functional-modifications.md) or an ODD restriction is required), `Needs validation` (acceptability depends on evidence from [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md)).

The driving model is a black box from LionDriver's point of view: training data and its ODD are not available (GAP-22). Its insufficiencies are therefore stated at the level of observable outputs.

## 2. Components analysed

| Component | Code | Role |
|---|---|---|
| Driving model (E-02) | `openpilot/selfdrive/modeld/modeld.py`, `fill_model_msg.py` | Path, lanes, road edges, leads, desired curvature and acceleration, hard-brake probability |
| Radar fusion | `openpilot/selfdrive/controls/radard.py` | Associates stock radar tracks with model leads |
| Calibration / localization | `calibrationd`, `locationd`, `paramsd`, `torqued`, `lagd` | Camera extrinsics, pose, vehicle parameters, lateral delay |
| DM model and policy | `modeld/dmonitoringmodeld.py`, `monitoring/policy.py` | Driver attention |
| Planner / controllers | `controls/lib/longitudinal_planner.py`, `controlsd.py`, `latcontrol_torque.py`, `drive_helpers.py` | Longitudinal MPC, lateral control, limits |
| System supervision | `selfdrive/selfdrived/selfdrived.py`, `state.py`, `events.py` | Fault reactions, alerts |
| Toyota EPS authority | `opendbc/safety/modes/toyota.h:173-177`; EPS (external) | Limits steering capability |

## 3. Functional insufficiencies

| ID | Type | Component | Insufficiency | Linked SH | Evidence |
|---|---|---|---|---|---|
| FI-01 | P | Driving model | Lane/path estimate wrong or unstable when markings are faded, missing, doubled (old and new), or when tar seams/shadows look like lines | SH-01, SH-02 | `LIMITATIONS.md:15`; domain |
| FI-02 | P | Driving model | Degraded perception in poor visibility (rain, fog, spray), low sun, oncoming glare, low light, camera obstruction | SH-01, SH-02, SH-06 | `LIMITATIONS.md:10-12, 18` |
| FI-03 | P | Driving model | Out-of-distribution input (unusual road layouts, construction, speeds above training data) yields unpredictable output; no uncertainty gating of the action | SH-01, SH-03, SH-04, SH-13 | `events.py:988-989` comment ("faster than most cars in the training data"); GAP-22 |
| FI-04 | P | Driving model | Lead detection misses stationary vehicles not seen moving and objects other than vehicles; VRUs not handled as leads | SH-06, SH-11 | `LIMITATIONS.md:34, 37`; `radard.py:153-165` |
| FI-05 | P | Driving model (Experimental) | e2e acceleration misinterprets traffic lights/signs: false stops and missed stops | SH-04, SH-09 | `toggles.py:155-158`; `longitudinal_planner.py:132-149` |
| FI-06 | P | Radar fusion | Radar false targets from overhead structures, metal plates, toll booths; misassociation of a track to the vision lead in curves and on cut-ins; interference from other radar sources | SH-03, SH-04, SH-06 | `LIMITATIONS.md:33, 43`; `radard.py:113-134` |
| FI-07 | P | Radar fusion | Lead kept or dropped wrongly when the model is uncertain (lead kept "when uncertain", dropped below prob 0.5) leading to acceleration toward a real lead or braking for a ghost | SH-03, SH-04 | `radard.py:156`, onboard review (`:234-239`) |
| FI-08 | P | Calibration/localization | Calibration drift after mount disturbance; wrong pose in banked or crowned roads; paramsd/torqued learning wrong values | SH-01, SH-02 | `LIMITATIONS.md:13, 16`; AOU-08 |
| FI-09 | S | Planner (Chill) | No speed reduction for curves; set speed may exceed safe curve speed, so lateral demand exceeds 3.0 m/s² | SH-02 | `longitudinal_planner.py:37-50` (acceleration limit in turns only) |
| FI-10 | S | Planner / limits | Deceleration bounded at −3.5 m/s²; insufficient for abrupt braking needs | SH-06 | `LIMITATIONS.md:38`; `interfaces.py:26` |
| FI-11 | S | Controller / EPS authority | Steering torque bounded (1500 raw, physical value unknown); insufficient for sharp curves, strong cross-wind, banking | SH-02 | `LIMITATIONS.md:14, 16`; `toyota.h:173` (GAP-04) |
| FI-12 | S | Planner | Auto-resume from standstill when the lead moves, without checking for objects between ego and lead (VRU crossing) | SH-03, SH-11 | `toyota/interface.py:107`; `carcontroller.py:175-185` |
| FI-13 | S | Lane change assist | No blind-spot or rear sensing; lane change starts on driver nudge | SH-10 | `LIMITATIONS.md:6`; `desire_helper.py:48-55` |
| FI-14 | S | System supervision | Soft disable keeps actuating for 3 s on the failed inputs; inputs considered alive up to 10× period | SH-02, SH-06 | `state.py:7-8`; `cereal/messaging/__init__.py:152-153`; GAP-16 |
| FI-15 | S | System supervision | Diagnostics (commIssue, posenet, locationd, modeldLagging) masked during big-model ("Chestnut") load and for 5 s after; cold small-model hot-switch while actuating | SH-01, SH-02, SH-04 | `selfdrived.py:382-384, 403, 457`; `modeld.py:411-419`; GAP-17 |
| FI-16 | S | System supervision | `speedTooHigh` warns but does not disengage; no ODD monitor for speed below 149 km/h | SH-13 | `events.py:989-996`; GAP-19 |
| FI-17 | S | System supervision | `cruiseMismatch` raised with no reaction; `canError` shows misleading text; non-finite commands silently clamped | SH-05, SH-02 | `events.py:458-460, 928-936`; `controlsd.py:140-147`; GAP-19 |
| FI-18 | P | DM model | Reduced detection with sunglasses, low light, glare, face partly out of view, obstructions; model high-uncertainty fallback to wheel touch | SH-12 | `LIMITATIONS.md:53-56`; `policy.py:77-78` |
| FI-19 | S | DM policy | Wheel-touch fallback resets awareness on any steering or gas input; source validity hard-coded `True`; alerts only above 2.8 m/s | SH-12 | `policy.py:29, 334-335`; `dmonitoringmodeld.py:99`; GAP-21 |
| FI-20 | S | Configuration | Behaviour-changing parameters without protection: Experimental default on, debug/maneuver modes, `IsDriverViewEnabled` DM demo mode | SH-09, SH-12, SH-13 | `params_keys.h:43, 59`; `process_config.py:34-47`; GAP-18, GAP-20 |
| FI-21 | S | Override semantics | Gas overrides longitudinal but does not disengage; host steering override threshold 500 raw; the driver may misjudge the state | SH-05 | `params_keys.h:35`; `carcontroller.py:33, 83` |
| FI-22 | P | Driving model | Temporal effects: model lag or frame drops degrade the plan; recurrent state reset after model switch | SH-01, SH-02 | `selfdrived.py:457` (`modeldLagging`); `modeld.py:411-419` |

## 4. Triggering conditions

| ID | Triggering condition | Category | Source |
|---|---|---|---|
| TC-01 | Low sun in the camera field of view; sun reflection on wet road | Environment / lighting | `LIMITATIONS.md:18, 42` |
| TC-02 | Oncoming headlights at night, esp. on undivided roads | Environment / lighting | `LIMITATIONS.md:18` |
| TC-03 | Rain, spray from trucks, wet road reflections | Weather | `LIMITATIONS.md:10, 29` |
| TC-04 | Fog, snow, dust reducing visibility | Weather (outside ODD) | `LIMITATIONS.md:10` |
| TC-05 | Faded, missing or doubled lane markings; tar seams; shadows | Infrastructure | domain |
| TC-06 | Construction / work zone: lane shifts, cones, temporary markings, barriers close to lane | Infrastructure (outside ODD) | `LIMITATIONS.md:15` |
| TC-07 | Close cut-in from an adjacent lane | Traffic | `LIMITATIONS.md:39` |
| TC-08 | Stationary vehicle in lane (broken-down car, end of queue around a curve) | Traffic | `LIMITATIONS.md:37` |
| TC-09 | Lead vehicle changes lanes and reveals a stopped vehicle ("cut-out") | Traffic | domain |
| TC-10 | Overhead structures, bridges, metal plates, toll booths | Infrastructure | `LIMITATIONS.md:33` |
| TC-11 | Other radar emitters | Environment | `LIMITATIONS.md:43` |
| TC-12 | Pedestrian or cyclist at the road edge or crossing | Traffic / VRU | `LIMITATIONS.md:34` |
| TC-13 | Signalised intersection or stop sign (Experimental Mode active) | Infrastructure | `toggles.py:155-158` |
| TC-14 | Curve tighter than R_ODD at the travel speed; on/off ramps | Geometry | `LIMITATIONS.md:14`; WP-C-02 §3.2 |
| TC-15 | Strongly banked road or crowned road; strong cross-wind | Geometry / weather | `LIMITATIONS.md:16` |
| TC-16 | Steep grade, hills, winding narrow road | Geometry | `LIMITATIONS.md:19, 40` |
| TC-17 | Crest with limited sight distance (lead or stationary object hidden) | Geometry | domain |
| TC-18 | Tunnel entry/exit (lighting change; GNSS loss) | Infrastructure (not validated) | `LIMITATIONS.md:53`; domain |
| TC-19 | Device mount disturbed, windscreen dirty, sticker or wrap over camera area | Vehicle / installation | `LIMITATIONS.md:11-13` |
| TC-20 | Speed above training distribution (> 120 km/h, and > 149 km/h) | Operation | `events.py:988-996` |
| TC-21 | Extreme ambient temperature (device throttling, sensor effects) | Environment | `LIMITATIONS.md:17, 41` |
| TC-22 | Big model load/fail event (eGPU disconnected, timeout) | System (Chestnut) | `modeld.py:234-235, 266-283, 411-419` |
| TC-23 | Inter-process message delays or drops within the 10× "alive" window; process restart | System | `cereal/messaging/__init__.py:152-153`; GAP-16 |
| TC-24 | Driver wears sunglasses, low cabin light, face partly out of view, camera covered | Driver / DM | `LIMITATIONS.md:53-56` |
| TC-25 | Driver makes small periodic steering or gas inputs while not watching the road (incl. defeat devices) | Driver misuse | `policy.py:334-335` |
| TC-26 | Debug parameter set: `IsDriverViewEnabled`, maneuver or joystick modes | Configuration | `params_keys.h:59`; `process_config.py:34-47` |
| TC-27 | Lead moves off from standstill while a pedestrian crosses between ego and lead | Traffic / VRU | FI-12 |
| TC-28 | Driver nudges for a lane change with a vehicle in the blind spot | Driver / traffic | `LIMITATIONS.md:6` |
| TC-29 | Driver presses gas to override and believes the system disengaged | Driver / HMI | `params_keys.h:35` |
| TC-30 | PCM cruise remains active after an item disengagement (cancel not effective) | Vehicle / system | `selfdrived.py:421`; GAP-19 |
| TC-31 | Exit lane or lane split on a highway (path follows the wrong branch) | Infrastructure | domain |
| TC-32 | Narrow lane (≤ 3.3 m) with an adjacent large vehicle or a concrete barrier close to the lane edge | Infrastructure / traffic | domain; proposed by [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) KS-06 |
| TC-33 | Lead vehicle braking harder than the item's deceleration bound (lead decel > 3.5 m/s²), incl. slow lead at highway speed | Traffic | `LIMITATIONS.md:38`; proposed by WP-V-03 KS-08 |

## 5. TC → FI → SH evaluation

| TC | FI | SH | Current system response | Evaluation | Action |
|---|---|---|---|---|---|
| TC-01, TC-02 | FI-02 | SH-01, SH-02, SH-06 | None specific; no uncertainty gating | Needs validation | Scenario tests (WP-V-03); FM-09 |
| TC-03 | FI-02, FI-06 | SH-01, SH-04, SH-06 | None specific | Needs validation | Light rain in ODD; heavier rain excluded (WP-C-02) |
| TC-04 | FI-02 | SH-01, SH-02, SH-06 | None | Needs modification (ODD exclusion + user info) | WP-C-02 exclusion; FM-09 |
| TC-05 | FI-01 | SH-01, SH-02 | None | Needs validation | WP-V-03; FM-09 |
| TC-06 | FI-01, FI-03 | SH-01, SH-02, SH-13 | None | Needs modification (ODD exclusion; detection if feasible) | FM-08 |
| TC-07 | FI-06, FI-07 | SH-04, SH-06 | Lead fused late; decel ≤ 3.5 m/s² | Needs validation | WP-V-03; FCW review |
| TC-08 | FI-04, FI-06, FI-10 | SH-06 | Often no lead; FCW may trigger from model hard-brake prob | Needs validation (driver responsibility; user info) | User info (WP-O-03); FM-09 |
| TC-09 | FI-04, FI-07 | SH-06 | as TC-08 | Needs validation | WP-V-03 |
| TC-10, TC-11 | FI-06 | SH-04 | Radar track may become lead | Needs validation | WP-V-03 (phantom braking rate) |
| TC-12 | FI-04 | SH-11 | No VRU response | Needs modification (ODD restriction to ODD-A with driver responsibility; user info) | WP-C-02; WP-O-03 |
| TC-13 | FI-05 | SH-09, SH-04 | e2e stops when detected | Needs modification | FM-01 |
| TC-14 | FI-09, FI-11 | SH-02 | `steerSaturated` warning (`events.py:619`) | Needs modification (ODD bound + authority characterisation) | WP-C-02 §3.2; FM-10 |
| TC-15 | FI-08, FI-11 | SH-01, SH-02 | Roll compensation in limits | Needs validation | WP-V-03 |
| TC-16 | FI-01, FI-11 | SH-02 | None | Needs validation | Grade bound in ODD |
| TC-17 | FI-04 | SH-06 | None | Needs validation | WP-V-03 |
| TC-18 | FI-02, FI-18 | SH-01, SH-12 | None | Needs validation; excluded until validated | WP-C-02 |
| TC-19 | FI-08, FI-02 | SH-01, SH-02 | Calibration check → `calibrationInvalid` soft disable | Acceptable for large errors; small errors need validation | Installation check (WP-O-01) |
| TC-20 | FI-03, FI-16 | SH-13 | Warning only above 149 km/h | Needs modification | FM-07 |
| TC-21 | FI-22 | SH-01, SH-02 | `overheat` soft disable (`events.py:800`) | Acceptable after FM-03 (stale-input handling) | FM-03 |
| TC-22 | FI-15, FI-22 | SH-01, SH-02, SH-04 | Diagnostics masked; cold model switch | Needs modification | FM-02 |
| TC-23 | FI-14 | SH-02, SH-06 | Actuation on stale inputs up to ≈3.5 s | Needs modification | FM-03 |
| TC-24 | FI-18 | SH-12 | Wheel-touch fallback | Needs validation | WP-C-08 §8; FM-05 |
| TC-25 | FI-19 | SH-12 | Awareness reset by any input | Needs modification | FM-05 |
| TC-26 | FI-20 | SH-12, SH-13 | DM demo mode, debug modes active | Needs modification | FM-06 |
| TC-27 | FI-12 | SH-03, SH-11 | Auto-resume | Needs modification | FM-11 |
| TC-28 | FI-13 | SH-10 | Lane change on nudge | Acceptable with user info (driver-initiated, abortable); needs validation of abort controllability | WP-C-08; WP-O-03 |
| TC-29 | FI-21 | SH-05 | Override indication shown | Needs validation (HMI clinic) | WP-C-08 §8 |
| TC-30 | FI-17 | SH-05 | Event without reaction | Needs modification | FM-04 |
| TC-31 | FI-01, FI-03 | SH-01 | None | Needs validation | WP-V-03 |
| TC-32 | FI-01 | SH-01 | None specific; lateral offset toward the obstacle not bounded | Needs validation | WP-V-03 KS-06 |
| TC-33 | FI-10 | SH-03, SH-06 | Decel ≤ 3.5 m/s²; FCW | Needs validation (driver responsibility; user info) | WP-V-03 KS-08; WP-O-03 |

## 6. AI-specific error causes (ISO/PAS 8800 view, summary)

| Cause | FI | Note |
|---|---|---|
| Training-data coverage unknown (distribution shift to LionDriver ODD) | FI-01…FI-05, FI-18 | Training data not available; must be bounded by validation on fork-owned data ([WP-W-10](../05-software/WP-W-10-ml-engineering.md)) |
| No uncertainty / OOD supervision of the control action | FI-03 | Model outputs std for some quantities; not used to gate actuation (GAP-22) |
| Model change without re-validation | all model FIs | D-05 in WP-M-01: pin and re-validate |
| Runtime integrity (unsigned pickle, no hash check) | — | Cybersecurity and integrity concern (GAP-22), handled in WP-C-09/WP-C-11 |

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Turn every "Needs validation" row into a scenario in WP-V-03 with pass criteria | SOTIF lead | G2 |
| OI-2 | Verify `radard.py` lead-retention line references (onboard review cites `:234-239`) at the baseline | SW lead | G1 |
| OI-3 | Collect fork-owned drive logs to estimate occurrence rates of TC-01, TC-05, TC-07, TC-10 in the ODD | SOTIF lead | G2 |
| OI-4 | Review TC list with the unknown-scenario exploration plan (WP-V-04) | SOTIF lead | G2 |
