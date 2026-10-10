# WP-C-08 Driver Interaction, HMI and Foreseeable Misuse Analysis

| Field | Value |
|---|---|
| Work product | WP-C-08 Driver interaction, HMI and reasonably foreseeable misuse analysis |
| Standard reference | ISO 26262-3:2018 §6 (controllability basis); ISO 21448:2022 §6 and Annex B (misuse, informative); UNECE R79 and R171 (informative benchmarks, WP-M-01 T-13); RESPONSE 3 Code of Practice for ADAS (informative) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF; backs the HARA C2 ratings (SG-01…SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); HF specialist review recommended |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose

The HARA ([WP-C-03](WP-C-03-hara.md)) rates almost every hazardous event C2 on the basis of a supervising driver, and the functional safety concept ([WP-C-04](WP-C-04-functional-safety-concept.md) §7) does not give driver monitoring an ASIL on the condition that those ratings do not depend on DM. This document:

1. defines the driver's tasks and how the HMI supports mode awareness;
2. inventories the alerts the system can give (from `openpilot/selfdrive/selfdrived/events.py`);
3. reviews the DM timing against informative benchmarks;
4. analyses reasonably foreseeable misuse, its consequences and measures;
5. states the controllability assumptions the HARA relies on and a plan to validate them.

## 2. Driver tasks

| Task | When | Supported by |
|---|---|---|
| T-01 Decide the situation is inside the ODD; engage | Before engagement | User information (WP-O-03); no-entry alerts |
| T-02 Monitor the road continuously, eyes on road | Engaged | DM (F-04) |
| T-03 Keep hands near the wheel, ready to steer | Engaged | Not enforced (openpilot does not require hands on wheel) |
| T-04 Brake for stationary objects, VRUs, traffic signals, stop signs | Engaged | FCW (F-06) for some cases only |
| T-05 Check blind spot before lane change; initiate with signal and nudge | Engaged | Lane change alerts (`preLaneChangeLeft/Right`, `laneChangeBlocked`) |
| T-06 Override (steer, gas) or disengage (brake, cancel) when needed | Engaged | F-03; envelope release on brake/cancel |
| T-07 Respond to take-over requests at once | On alert | F-05 |
| T-08 Disengage before leaving the ODD | ODD exit | None (WP-C-02 §5) |
| T-09 Keep device mounted, clean and calibrated; vehicle maintained | Pre-drive | Calibration alerts; checklist (AOU-08…AOU-10) |

## 3. Mode awareness

| State | Device indication | Vehicle indication | Remarks |
|---|---|---|---|
| Disengaged | No engaged border; startup alert "Be ready to take over at any time" (`events.py:425`) | Cruise indicator off / main only | |
| Engaged | Engaged colour on display; engage sound | Cruise indicator active (PCM-driven); LKAS HUD lane lines (`0x412`) | The envelope ties authority to PCM cruise (FSR-05.05), so the stock cruise indicator is an independent indication |
| Override (gas) | `gasPressedOverride` (`events.py:728`) | Cruise remains active | Gas does not disengage (`DisengageOnAccelerator` default `0`, `params_keys.h:35`): risk of believing the system is off (MC-08) |
| Override (steer) | `steerOverride` (`events.py:736`) | — | |
| Soft disabling | "TAKE CONTROL IMMEDIATELY"-type soft-disable alert; immediate form < 0.5 s before end (`events.py:224-234`) | — | Actuation continues during this period (GAP-16) |
| Immediate disable | Immediate-disable alert + sound | Cruise cancelled | |
| Experimental vs Chill | Icon in settings/onroad UI | None | Behaviour difference not visible on the cluster (MC-09) |

Mode-awareness weaknesses: gas override semantics, Experimental/Chill difference, and `cruiseMismatch` (PCM cruise active while openpilot is not) with no reaction (GAP-19).

## 4. Alert inventory

From `events.py` (`EVENTS` dict, lines 387-1016; device type `mici` overrides some DM alerts at lines 1018+). Event types are defined in `class ET` (`events.py:35-45`).

| Class (ET) | Effect | Representative events (line) | Safety observations |
|---|---|---|---|
| ENABLE / PRE_ENABLE | Engage | `pcmEnable` (679), `buttonEnable` (683), `preEnableStandstill` (720) | Engagement via PCM edge only (envelope) |
| USER_DISABLE | Disengage on driver action | `pcmDisable` (687), `buttonCancel` (691), `pedalPressed` (709), `steerDisengage` (715), `parkBrake` (704), `wrongCruiseMode` (757), `reverseGear` (954) | — |
| OVERRIDE_LATERAL / LONGITUDINAL | Override indication | `steerOverride` (736), `gasPressedOverride` (728) | See MC-08 |
| WARNING | Message, stays engaged | `steerSaturated` (619), `steerTempUnavailableSilent` (511), `preLaneChange*` (587, 595), `laneChangeBlocked` (603), `resumeRequired` (575), `speedTooHigh` (989), `personalityChanged` (1004) | `speedTooHigh` is an ODD exit with warning only (GAP-19) |
| PERMANENT (DM) | Escalating DM alerts | `driverDistracted1/2/3` (519/527/535), `driverUnresponsive1/2/3` (543/551/559) | Level 3 "DISENGAGE IMMEDIATELY" with `warningImmediate` sound |
| PERMANENT (collision) | Collision warnings | `fcw` (493), `stockAeb` (480), `aeb` (471), `ldw` (501) | FCW has sound `warningSoft`; stock AEB alert has no sound (`AudibleAlert.none`) — relies on vehicle sound |
| NO_ENTRY | Engagement refused | `tooDistracted` (791), `belowEngageSpeed` (777), `calibrationIncomplete` (822), `selfdriveInitializing` (421), `bigModelLoading` (407) | DM lockout via `tooDistracted` |
| SOFT_DISABLE | Warning, actuation continues up to 3 s | `commIssue` (853), `processNotRunning` (868), `modeldLagging` (886), `posenetInvalid` (897), `cameraMalfunction` (633), `calibrationInvalid` (816), `overheat` (800), `steerTempUnavailable` (762), `radarFault` (873), `excessiveActuation` (795), `doorOpen` (834), `seatbeltNotLatched` (839), `espDisabled` (844), `bigModelFailed` (411) | Input-loss causes share the 3 s actuation period with benign causes (GAP-16, FM-03) |
| IMMEDIATE_DISABLE | Release at once | `controlsMismatch` (919), `canError` (928), `canBusMissing` (938), `steerUnavailable` (948), `relayMalfunction` (974), `accFaulted` (908), `cruiseDisabled` (966), `speedTooLow` (980), `vehicleSensorsInvalid` (998), `locationdPermanentError` (652), `paramsdPermanentError` (671) | `canError` text "Unknown Vehicle Variant" misdescribes the fault (GAP-19) |
| (none) | Event without reaction | `cruiseMismatch` (458, all alerts commented out), `noGps` (390), `stockFcw` (391) | `cruiseMismatch` no reaction (GAP-19, FM-04) |

Developer modes (`joystickDebug` 396, `longitudinalManeuver` 401, `lateralManeuver` 416) produce only warning/permanent alerts; they must be unavailable in reference builds (FM-06).

## 5. Driver monitoring timing review

### 5.1 Current policy (`openpilot/selfdrive/monitoring/policy.py`)

| Parameter | Value | Line |
|---|---|---|
| Minimum speed for alerts | 2.8 m/s (10 km/h); code comment cites EU 2025/1899 | 28-29 |
| Vision policy alert 1 / 2 / 3 | 5 / 8 / 13 s of distraction | 34-36 |
| Wheel-touch policy alert 1 / 2 / 3 | 5 / 15 / 25 s without interaction | 31-33 |
| No response after alert 3 | 5 s → force deceleration (`noResponseForceDecel`) | 39, 398 |
| Lockout | after 2 × alert 3 or 1 × no-response; 1 / 5 / 15 / 30 min | 42-44 |
| Fallback to wheel touch | model std > 0.3 for 10 s | 77-78 |
| Thresholds | face 0.7, eye 0.65, sunglasses 0.9, phone 0.5, sleep 0.75 | 49-54 |

### 5.2 Comparison with informative benchmarks

These regulations are not binding in the US (WP-M-01 T-13). Values must be checked against licensed text before use; the table records the comparison approach, not normative numbers.

| Aspect | LD-SDA today | Benchmark (informative) | Observation |
|---|---|---|---|
| Hands-on requirement | Not required; vision DM primary | UNECE R79 (ACSF): hands-on detection with escalating hands-off warnings | LD-SDA is closer to a hands-free DCAS concept; R79 is not the right comparator for the vision policy but is for the wheel-touch fallback |
| Eyes-off-road warning | First alert after 5 s of distraction, escalation to 13 s | UNECE R171 (DCAS): driver disengagement detection with visual-attention monitoring and escalation within a few seconds of eyes-off-road | Order of magnitude consistent; the time to the strongest alert (13 s) and to force decel (≈18 s) should be compared in detail |
| Wheel-touch fallback | Alert 3 after 25 s; any steer/gas input resets | R79-type hands-off escalation | Reset on any input is weaker than a hands-on detection (GAP-21, FM-05) |
| Escalation end state | Force decel to standstill target via cruise 0, then lockout | R171: escalation to a risk-mitigation function | Comparable concept; no hazard lights or lane-keeping-to-stop sequence specified |
| Activation speed | > 10 km/h | Cited regulation threshold (per code comment) | Consistent with comment; below 10 km/h no monitoring (stop-and-go phone use, MC-02) |

### 5.3 Required DM performance (for AC-05, WP-C-05)

| ID | Requirement (QM, SOTIF) | Verification |
|---|---|---|
| DMP-01 | Detect eyes-off-road ≥ 5 s with true-positive rate per [WP-C-11](WP-C-11-ai-system-definition-and-safety-requirements.md) AIR-07 (proposed, TBC), validated under [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) VT-08, for the reference driver population (incl. glasses, sunglasses, night) | DM clinic, §8 |
| DMP-02 | Detect phone use and sleep states with rates per WP-C-11 AIR-08 (proposed, TBC), validated under WP-V-02 VT-08 | DM clinic |
| DMP-03 | Detect a covered or blocked driver camera within 10 s and fall back to the stricter policy | Test; FM-05 |
| DMP-04 | Wheel-touch fallback cannot be satisfied by periodic small inputs (FM-05) | Test |

## 6. Reasonably foreseeable misuse

| ID | Misuse | Likelihood / driver motive | Consequence | Current measures | Additional measures | Linked SH |
|---|---|---|---|---|---|---|
| MC-01 | Hands-off driving for long periods | High: system does not require hands on wheel | Longer reaction to lateral errors (SH-01, SH-02); C2 basis weakened | Vision DM | User info; controllability tests with hands-off posture (§8); consider hands-on requirement in ODD-A | SH-01, SH-02 |
| MC-02 | Phone use, eyes off road | High | Late reaction to all SH | DM phone threshold 0.5; alerts > 10 km/h | DMP-02 validation; review below-10 km/h behaviour | SH-03, SH-06, SH-11 |
| MC-03 | Sleeping / drowsy / impaired driver | Medium (long highway drives) | No reaction until force decel | DM sleep detection; no-response force decel; lockout | Validate force-decel scenario on highway; consider hazard lights | SH-02, SH-06 |
| MC-04 | DM camera covered or driver out of view | Medium | DM falls back to wheel touch | Wheel-touch fallback (`policy.py:77-78`) | FM-05 (strict fallback, camera-blocked detection, no-entry if persistent) | SH-12 |
| MC-05 | `IsDriverViewEnabled` set to force DM demo mode | Low–medium (known to the community) | DM neutralised with synthetic inputs | None | FM-06 | SH-12 |
| MC-06 | Defeat devices: steering-wheel weights, periodic nudgers, fake faces/photos | Medium | Wheel-touch fallback defeated; vision possibly fooled | Partial (vision primary) | FM-05; liveness checks in DM model (WP-C-11) | SH-12 |
| MC-07 | Use outside the ODD (snow, construction, city streets, > 120 km/h) | High | SH-13; higher rates of SH-01…SH-06 | `speedTooHigh` warning; some diagnostics | FM-07, FM-08; user info | SH-13 |
| MC-08 | Gas override mistaken for disengagement | Medium | Driver releases gas expecting manual control; system resumes ACC (or the reverse expectation) | Override alert | HMI clinic (§8); review default of `DisengageOnAccelerator` for reference build | SH-05 |
| MC-09 | Over-trust after Experimental Mode default (expects stops at lights/signs; transfers this expectation to Chill mode) | High if default kept | Red-light running, missed stop signs | UI text "Mistakes should be expected" | FM-01; user info | SH-09 |
| MC-10 | Lane change without blind-spot check, relying on the system | Medium | Side collision | `LIMITATIONS.md:6` | User info; validation of abort controllability | SH-10 |
| MC-11 | Installing on a different vehicle or with modified software (unsupported configuration) | Medium | Outside claimed scope | Fingerprinting; dashcam mode for unknown cars | Configuration control (WP-O-01) | — |
| MC-12 | Ignoring or silencing alerts (volume low, device muted) | Medium | Take-over requests missed | Panda buzzer only on SoC loss | Minimum alert volume not user-adjustable below a floor (to check) | SH-02, SH-06 |

## 7. Controllability assumptions to be backed up

These assumptions underlie the C2 (and target C1) ratings in the HARA and the FSC strategy. Each must be confirmed by §8.

| ID | Assumption | Used in | Pass criterion (proposed, informed by RESPONSE 3 practice) |
|---|---|---|---|
| CA-01 | A typical attentive driver corrects envelope-bounded worst-case steering torque (step to max, at max rate, in either direction) before the lane departure becomes hazardous | HE-01.x, SG-01; FSC §4 (C1 target) | ≥ 20 valid subjects; 20/20 control the event (no lane exceedance beyond the agreed margin) → supports C1 at ≈85 % confidence of ≥ 90 %; for C1 (≥ 99 %) a larger sample or argument is needed — to be defined with the assessor |
| CA-02 | A supervising driver notices an unannounced loss of lateral control in a highway curve and recovers within the lane plus margin | HE-02.1/02.2, SG-02 | Same sample logic; outcome measured as maximum lateral deviation |
| CA-03 | A driver brakes in time when the system accelerates toward a slower lead or launches from standstill unexpectedly | HE-03.x | Reaction time and minimum distance |
| CA-04 | Following drivers and the ego driver control an unexpected deceleration at the envelope bound | HE-04.1 | Instrumented follow test on closed course |
| CA-05 | A driver can overpower the LKA torque during an evasive manoeuvre and the system releases on brake | HE-05.x | Steering force measurement; release time ≤ SG-05 FTTI |
| CA-06 | A driver who is hands-off but eyes-on responds within the times assumed in CA-01/CA-02 | MC-01, HE-02.1 ("hands off foreseeable") | Repeat CA-01/CA-02 with hands-off posture |
| CA-07 | Take-over requests (soft and immediate disable) are perceived and understood within 1 s | SG-02, SG-06 | HMI clinic: detection and correct response |

## 8. Controllability validation plan

| Step | Activity | Setting | Output | Prerequisite |
|---|---|---|---|---|
| V-1 | Vehicle characterization: EPS torque at the wheel vs `0x2E4` request; EPS timeout; PCM response to accel requests and cancel | Closed course, safety driver (WP-V-07) | AOU-01R/03R/05R evidence; input to FM-10 | Test procedure approved |
| V-2 | HMI clinic (static/parked and low-speed): alert perception, comprehension of override/disengage states, Experimental vs Chill | Parked vehicle / test track | CA-07, MC-08 evidence | — |
| V-3 | Controllability test: injected worst-case lateral events (step, ramp, frozen torque) at representative speeds, naive subjects, hands-on and hands-off postures | Closed course, dual controls or safety driver, fault injection via a test build only | CA-01, CA-02, CA-06 | V-1; ethics/consent; injection build locked to test vehicle |
| V-4 | Longitudinal controllability: unexpected acceleration/deceleration events at envelope bounds | Closed course, soft targets | CA-03, CA-04 | V-1 |
| V-5 | DM clinic: distraction tasks (phone, look-away), sunglasses, night, camera covered, defeat attempts | Test track and controlled public-road drives with safety driver | DMP-01…04 | FM-05, FM-06 implemented |
| V-6 | Evaluation against pass criteria; report into WP-V-01 and HARA re-rating | — | Confirmed or revised C ratings | V-1…V-5 |

Method notes (RESPONSE 3 Code of Practice, informative): use naive subjects representative of the user population, define the controllability criterion before testing, keep the scenario unknown to the subject, and record objective measures (lateral deviation, time-to-collision, reaction time) plus subjective ratings. Results: **not yet executed**.

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm benchmark values (R79, R171, EU 2025/1899) against licensed texts and finalise §5.2 | HF specialist | G1 |
| OI-2 | Confirm the numeric DM performance targets for DMP-01/02 proposed in WP-C-11 AIR-07/AIR-08 (TBC values; validation target VT-08 in WP-V-02) | SOTIF lead | G2 |
| OI-3 | Agree controllability pass criteria and sample size (CA-01…CA-07) with the external assessor | Safety manager | G1 |
| OI-4 | Decide `DisengageOnAccelerator` default for the reference build (MC-08) | Maintainer | G1 |
| OI-5 | Check whether alert volume can be reduced below an audible floor (MC-12) | SW lead | G2 |
| OI-6 | Confirm whether the `mici` device-specific DM alerts (`events.py:1018+`) apply to the reference device | SW lead | G1 |
