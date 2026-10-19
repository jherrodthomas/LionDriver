# WP-C-08 Driver Interaction, HMI and Foreseeable Misuse Analysis

| Field | Value |
|---|---|
| Work product | WP-C-08 Driver interaction, HMI and reasonably foreseeable misuse analysis |
| Standard reference | ISO 26262-3:2018 §6 (controllability basis); ISO 21448:2022 §6 and Annex B (misuse, informative); UNECE R79 and R171 (informative benchmarks, WP-M-01 T-13); RESPONSE 3 Code of Practice for ADAS (informative) |
| Version | 0.7 (§7.1 controllability pass criteria and sample size drafted from the RESPONSE 3 Code of Practice (DQ-034 A) and approved by the lead as proposed on 2026-10-19, now frozen; CA-01 statistics corrected; OI-3 narrowed to the assessor check; 2026-10-19). 0.6 (§5.4 and OI-8: the rule is implemented in `policy.py`, SWSR-634; validation still open; 2026-10-17). 0.5 (§5.4 added: supervision bound and speed table for the wheel-touch fallback, required by TSR-634 (DQ-077 A); DMP-05; OI-8; 2026-10-17). 0.4 (OI-7, the duplicate OI-4: gas override behaviour kept, DQ-022 A; MC-08 updated; 2026-10-16). 0.3 (§6.1 HARA side recorded: WP-C-03 v0.4 rates H-STPA-1 as OS-17/OS-18 and adds H-09 with SG-08, ASIL A, decision register DQ-003, DQ-205; OI-4 narrowed to the FSC follow-up; 2026-10-16). 0.2 (§6.1: H-STPA-1 treated as reasonably foreseeable misuse in both SOTIF and the HARA, decision register DQ-003; HARA side open; MC-09 updated for the Chill mode default; 2026-10-14). 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF; backs the HARA C2 ratings (SG-01…SG-08) |
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
| DMP-01 | Detect continuous eyes-off-road and give the first DM alert no later than 6 s after the eyes leave the road (classification within 1.0 s per [WP-C-11](WP-C-11-ai-system-definition-and-safety-requirements.md) AIR-07, plus the 5 s vision-policy alert-1 timeout, `policy.py:34`), with recall per AIR-07, validated under [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) VT-08, for the reference driver population (incl. glasses, sunglasses, night). Target confirmed 2026-10-12 (OI-2) | DM clinic, §8 |
| DMP-02 | Detect phone use and sleep states with rates per WP-C-11 AIR-08, validated under WP-V-02 VT-08. Target confirmed 2026-10-12 (OI-2) | DM clinic |
| DMP-03 | Detect a covered or blocked driver camera within 10 s and fall back to the stricter policy | Test; FM-05 |
| DMP-04 | Wheel-touch fallback cannot be satisfied by periodic small inputs (FM-05) | Test |
| DMP-05 | In the wheel-touch fallback, alert *k* fires at no more than D*k* = 150 / 240 / 395 m driven since the last interaction, or T*k* = 5 / 15 / 25 s if that comes first (§5.4; TSR-634) | Test (T-SIL at constant and varying speed); DM clinic, §8 V-5; WP-V-02 §4.4 |

### 5.4 Wheel-touch escalation by speed (TSR-634)

The lead decided on 2026-10-14 that, in the wheel-touch fallback, the reminders come faster at highway speed (decision register DQ-077, option A). [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) TSR-634 requires this, with the speed table and the supervision bound set here. The problem it treats is [WP-A-05](../08-analyses/WP-A-05-stpa.md) LS-09. With sunglasses or in low light the camera confidence drops, and the policy falls back to wheel touch with fixed 5 / 15 / 25 s timers (§5.1). At 110 km/h, 25 s is 764 m driven before the strongest alert. Over the same 764 m, a driver seen by the vision policy gets that alert after 13 s.

**Supervision bound.** In the wheel-touch fallback, the distance driven since the last driver interaction before alert *k* shall not exceed D*k*:

| Alert | Vision policy time (`policy.py:34-36`) | Bound D*k* = vision time × 110 km/h, rounded down to 5 m | Wheel-touch time cap, unchanged (`policy.py:31-33`) |
|---|---|---|---|
| 1 | 5 s | 150 m | 5 s |
| 2 | 8 s | 240 m | 15 s |
| 3 | 13 s | 395 m | 25 s |

Rule: alert *k* fires at whichever comes first, T*k* seconds or D*k* metres since the last interaction. Distance is the integral of vehicle speed, so the rule also holds while speed changes. The no-response stage (5 s after alert 3, §5.1) and the lockout are unchanged.

Why this bound:

1. **The bound is the distance the vision policy allows at the ODD speed bound.** At 110 km/h (WP-C-02, DQ-260), each wheel-touch alert comes no later than the vision-policy alert of the same level. A driver whose face the camera cannot read gets no more unsupervised distance than the vision policy gives a driver it sees looking away at 110 km/h. At lower speeds the vision policy gives less distance than D*k*, because its timers are fixed. The fallback stays weaker there, but never by more distance than is already accepted at 110 km/h.
2. **No change below about 57 km/h.** The time caps still govern there, so the bound does not add nuisance alerts in slow traffic. Alert 1 is set by time at every speed up to 108 km/h, so the first reminder is as frequent as today across almost the whole ODD.
3. **Above the ODD bound the rule only tightens.** Distance keeps governing, so at 120 km/h the alerts come at 4.5 / 7.2 / 11.8 s.

**Speed table (derived from the rule; for TSR-634 and the SWSR).**

| Speed (km/h) | Alert 1 / 2 / 3 (s) | Distance to alert 1 / 2 / 3 (m) | Today, distance (m) |
|---|---|---|---|
| ≤ 50 | 5.0 / 15.0 / 25.0 | ≤ 69 / 208 / 347 | same |
| 60 | 5.0 / 14.4 / 23.7 | 83 / 240 / 395 | 83 / 250 / 417 |
| 70 | 5.0 / 12.3 / 20.3 | 97 / 240 / 395 | 97 / 292 / 486 |
| 80 | 5.0 / 10.8 / 17.8 | 111 / 240 / 395 | 111 / 333 / 556 |
| 90 | 5.0 / 9.6 / 15.8 | 125 / 240 / 395 | 125 / 375 / 625 |
| 100 | 5.0 / 8.6 / 14.2 | 139 / 240 / 395 | 139 / 417 / 694 |
| 110 | 4.9 / 7.9 / 12.9 | 150 / 240 / 395 | 153 / 458 / 764 |

Limits of this derivation:

- It caps exposure; it does not show that drivers respond. Whether drivers in the fallback respond to the faster alerts, and whether the extra alerts become a nuisance that drivers defeat (FM-05, DMP-04), is validated under [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) §4.4.
- Anchoring on the vision-policy times is a technical choice. A different anchor, such as a fixed time to the strongest alert at highway speed, would change only D*k*. The anchor is revisited if the §4.4 nuisance or response results fail.
- Implemented 2026-10-17 in `selfdrive/monitoring/policy.py:37-41, 402-408` ([WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) SWSR-634). Unit tests reproduce the speed table within one 50 ms DM step; the vehicle validation of WP-V-02 §4.4 is still open.

## 6. Reasonably foreseeable misuse

| ID | Misuse | Likelihood / driver motive | Consequence | Current measures | Additional measures | Linked SH |
|---|---|---|---|---|---|---|
| MC-01 | Hands-off driving for long periods | High: system does not require hands on wheel | Longer reaction to lateral errors (SH-01, SH-02); C2 basis weakened | Vision DM | User info; controllability tests with hands-off posture (§8); consider a hands-on requirement (the ODD-A case is gone with the highway-only ODD, DQ-023) | SH-01, SH-02 |
| MC-02 | Phone use, eyes off road | High | Late reaction to all SH | DM phone threshold 0.5; alerts > 10 km/h | DMP-02 validation; review below-10 km/h behaviour | SH-03, SH-06, SH-11 |
| MC-03 | Sleeping / drowsy / impaired driver | Medium (long highway drives) | No reaction until force decel | DM sleep detection; no-response force decel; lockout | Validate force-decel scenario on highway; consider hazard lights | SH-02, SH-06 |
| MC-04 | DM camera covered or driver out of view | Medium | DM falls back to wheel touch | Wheel-touch fallback (`policy.py:82-83`) | FM-05 (strict fallback, camera-blocked detection, no-entry if persistent) | SH-12 |
| MC-05 | `IsDriverViewEnabled` set to force DM demo mode | Low–medium (known to the community) | DM neutralised with synthetic inputs | None | FM-06 | SH-12 |
| MC-06 | Defeat devices: steering-wheel weights, periodic nudgers, fake faces/photos | Medium | Wheel-touch fallback defeated; vision possibly fooled | Partial (vision primary) | FM-05; liveness checks in DM model (WP-C-11) | SH-12 |
| MC-07 | Use outside the ODD (snow, construction, city streets, > 110 km/h) | High | SH-13; higher rates of SH-01…SH-06 | `speedTooHigh` warning; some diagnostics | FM-07, FM-08; user info | SH-13 |
| MC-08 | Gas override mistaken for disengagement | Medium | Driver releases gas expecting manual control; system resumes ACC (or the reverse expectation) | Override alert | HMI clinic (§8 V-2) shows the override alert is understood; `DisengageOnAccelerator` stays `0` (DQ-022, A) | SH-05 |
| MC-09 | Over-trust after Experimental Mode default (expects stops at lights/signs; transfers this expectation to Chill mode) | Lower since the default is Chill mode (B-06, 2026-10-14); still high for drivers who used Experimental mode before | Red-light running, missed stop signs | UI text "Mistakes should be expected" | FM-01; user info | SH-09 |
| MC-10 | Lane change without blind-spot check, relying on the system | Medium | Side collision | `LIMITATIONS.md:6` | User info; validation of abort controllability | SH-10 |
| MC-11 | Installing on a different vehicle or with modified software (unsupported configuration) | Medium | Outside claimed scope | Fingerprinting; dashcam mode for unknown cars | Configuration control (WP-O-01) | — |
| MC-12 | Ignoring or silencing alerts (volume low, device muted) | Medium | Take-over requests missed | Panda buzzer only on SoC loss | Minimum alert volume not user-adjustable below a floor (to check) | SH-02, SH-06 |

### 6.1 Classification of H-STPA-1

The STPA hazard H-STPA-1, "the vehicle is driven with the item engaged while the driver is not supervising it" ([WP-A-05](../08-analyses/WP-A-05-stpa.md) §2), is treated as **reasonably foreseeable misuse in both analyses**: as a misuse hazard under SOTIF, recorded here through MC-01, MC-02 and MC-03, and as foreseeable misuse in the HARA ([WP-C-03](WP-C-03-hara.md); ISO 26262-3 §6.4.2).

| Field | Value |
|---|---|
| Decision | "Both SOTIF and HARA foreseeable misuse" (decision register [DQ-003](../01-management/decisions/register.yaml), answer "other") |
| Decided by, date | Project lead, 2026-10-14, on the decision inbox. This answer supersedes the first one the same day (option B, SOTIF only) |
| SOTIF side | Recorded: MC-01…MC-03 in §6, DM performance targets DMP-01…DMP-04 in §5.3, controllability validation in §8 |
| HARA side | **Recorded in WP-C-03 v0.4 (2026-10-16).** Two misuse situations: OS-17, the driver not supervising but still able to respond (E2), and OS-18, the driver unresponsive (E1). Every malfunction is crossed with them; the representative events are HE-01.5, HE-02.6, HE-03.6, HE-06.4 and HE-07.4 (ASIL A or B, none above its goal). A silent DM failure in these situations is the new hazard H-09 with SG-08, ASIL A (HE-09.1, HE-09.2; decision register DQ-205, A) |
| Consequence | Driver monitoring now carries SG-08 at ASIL A, so the WP-C-04 §7 proposal (DM QM) has to be revised. ASIL A measures on the DM chain are a smaller step than the B the first reading feared, but the current DM runs on the QM SoC. If sustained non-supervision proves more common than 1 % of engaged time (OS-17 at E3), SG-08 becomes ASIL B (WP-C-03 §6.1) |

## 7. Controllability assumptions to be backed up

These assumptions underlie the C2 (and target C1) ratings in the HARA and the FSC strategy. Each must be confirmed by §8.

| ID | Assumption | Used in | Pass criterion (summary; the full criteria are in §7.1) |
|---|---|---|---|
| CA-01 | A typical attentive driver corrects envelope-bounded worst-case steering torque (step to max, at max rate, in either direction) before the lane departure becomes hazardous | HE-01.x, SG-01; FSC §4 (C1 target) | ≥ 20 valid subjects; 20/20 keep the vehicle in its lane (§7.1 CA-01). This shows ≥ 85 % controllable at 95 % confidence, which confirms the C2 rating. The C1 target (≥ 99 %) would need 299 of 299, or an argument (§7.1 rule 6) |
| CA-02 | A supervising driver notices an unannounced loss of lateral control in a highway curve and recovers within the lane plus margin | HE-02.1/02.2, SG-02 | Same sample logic; outcome measured as maximum lateral deviation |
| CA-03 | A driver brakes in time when the system accelerates toward a slower lead or launches from standstill unexpectedly | HE-03.x | Reaction time and minimum distance |
| CA-04 | Following drivers and the ego driver control an unexpected deceleration at the envelope bound | HE-04.1 | Instrumented follow test on closed course |
| CA-05 | A driver can overpower the LKA torque during an evasive manoeuvre and the system releases on brake | HE-05.x | Steering force measurement; release time ≤ SG-05 FTTI |
| CA-06 | A driver who is hands-off but eyes-on responds within the times assumed in CA-01/CA-02 | MC-01, HE-02.1 ("hands off foreseeable") | Repeat CA-01/CA-02 with hands-off posture |
| CA-07 | Take-over requests (soft and immediate disable) are perceived and understood within 1 s | SG-02, SG-06 | HMI clinic: detection and correct response |

### 7.1 Pass criteria and sample size (approved by the lead 2026-10-19; frozen)

The lead chose to set the criteria now, before any test runs, and to have an assessor check them later (decision register DQ-034, option A; no assessor is engaged yet, DQ-009 C). Claude drafted them from the RESPONSE 3 Code of Practice for the validation of ADAS, the established practice for controllability evidence under ISO 26262-3. **The lead approved them as proposed on 2026-10-19** (in the chat with Claude, recorded here), before any controllability test has run. They are now frozen. Any change needs a new dated approval made before the affected test runs, never after its results are seen.

**Rules common to all CA tests**

1. **Sample.** At least 20 valid subjects per scenario, at each tested speed and posture.
   - A subject is valid if they completed the run as specified: naive to the scenario, no protocol deviation, data complete.
   - Every subject excluded is recorded with the reason. Exclusion is decided before the outcome is evaluated, never because of the outcome, and the subject is replaced.
2. **Pass.** All valid subjects meet the outcome criterion of the CA (20 of 20).
   - **One failure means the CA is not met.** The C rating it supports is not confirmed. The HARA rating is revised, or the design changes and the test is repeated with new subjects.
   - Adding subjects after a failure to dilute it is not allowed.
3. **What 20 of 20 shows.** At least 85 % of drivers control the event, at 95 % one-sided confidence (0.05^(1/20) = 0.861). The code of practice accepts this as evidence that the situation is controllable. The project uses it to **confirm C2 ratings** (ISO 26262-3 Table B.6: ≥ 90 % of drivers; 20 of 20 gives 88 % confidence of that).
4. **Subjects.**
   - Licensed drivers, not members of the project, representative of the intended users in age and driving experience, briefed only as an owner would be (WP-O-03).
   - The fault and its timing are unknown to the subject.
   - Informed consent; a safety driver or dual controls; closed course only (WP-V-07, DQ-104 B).
5. **Measures.** Objective measures are recorded for every run: lateral position, time-to-collision, reaction times, and steering and pedal inputs, all on one clock (WP-V-01 VS-VAL-08). Subjective ratings are recorded too but do not decide the pass.
6. **C1 claims.** A C1 rating (≥ 99 %) cannot be confirmed with 20 subjects: at 95 % confidence it needs 299 of 299. C1 ratings stay ⚠ unless one of these holds:
   - that sample is run;
   - an argument from physical bounds is accepted. For example, a deceleration bounded by the PCM envelope that the following driver's normal headway absorbs (HE-04.x).

   Which route each C1 rating takes is recorded with the result.

**Outcome criterion per CA** (approved as proposed, 2026-10-19)

| CA | Scenario (closed course) | Outcome criterion, met by every valid subject |
|---|---|---|
| CA-01 | Injected worst-case lateral torque: step to the envelope maximum at the maximum rate, in either direction. Straight and at R_ODD, at 70, 90 and 110 km/h, hands on the wheel | The vehicle stays in its lane: no tyre beyond the outer edge of the lane line before the subject has corrected and the vehicle is back inside the lane |
| CA-02 | Unannounced loss of lateral control on a straight, and in a curve of radius above R_ODD, at 90 and 110 km/h | As CA-01. The curve at the R_ODD bound is already rated C3 (HE-02.1, DQ-059) and is not used to claim C2 |
| CA-03 | Unexpected acceleration at the envelope bound (+2.0 m/s²) towards a slower soft target at 70–110 km/h, and an unexpected launch from standstill behind a soft target | No contact with the target; minimum time-to-collision ≥ 1.0 s at the moment the subject's braking takes effect |
| CA-04 | Unexpected deceleration step at the envelope bound (−3.5 m/s²) with a following vehicle driven by a subject at a 1.5 s gap, at 70–110 km/h | No contact between the following vehicle and the ego. The ego subject keeps the vehicle in its lane |
| CA-05 | Evasive lane change with the item applying full LKA torque against it, then a brake application | The subject completes the evasive path without cone contact, with a steering force at the rim of ≤ 50 N (AOU-02). The item releases within the SG-05 FTTI (≤ 0.2 s preliminary) of the brake input |
| CA-06 | CA-01 and CA-02, repeated with the subject's hands off the wheel and eyes on the road | As CA-01 and CA-02 |
| CA-07 | Soft and immediate disable alerts at unannounced times, at 70–110 km/h (HMI clinic V-2 and the track) | The subject starts the correct response (hands to the wheel, or braking where asked) within 1 s of alert onset, and afterwards states the system state correctly |

## 8. Controllability validation plan

| Step | Activity | Setting | Output | Prerequisite |
|---|---|---|---|---|
| V-1 | Vehicle characterization: EPS torque at the wheel vs `0x2E4` request; EPS timeout; PCM response to accel requests and cancel | Closed course, safety driver (WP-V-07) | AOU-01R/03R/05R evidence; input to FM-10 | Test procedure approved |
| V-2 | HMI clinic (static/parked and low-speed): alert perception, comprehension of override/disengage states, Experimental vs Chill | Parked vehicle / test track | CA-07, MC-08 evidence | — |
| V-3 | Controllability test: injected worst-case lateral events (step, ramp, frozen torque) at representative speeds, naive subjects, hands-on and hands-off postures | Closed course, dual controls or safety driver, fault injection via a test build only | CA-01, CA-02, CA-06 | V-1; ethics/consent; injection build locked to test vehicle |
| V-4 | Longitudinal controllability: unexpected acceleration/deceleration events at envelope bounds | Closed course, soft targets | CA-03, CA-04 | V-1 |
| V-5 | DM clinic: distraction tasks (phone, look-away), sunglasses, night, camera covered, defeat attempts; wheel-touch fallback driven at 90–110 km/h (§5.4) | Test track and controlled public-road drives with safety driver | DMP-01…05 | FM-05, FM-06 implemented |
| V-6 | Evaluation against pass criteria; report into WP-V-01 and HARA re-rating | — | Confirmed or revised C ratings | V-1…V-5 |

Method notes (RESPONSE 3 Code of Practice, informative): use naive subjects representative of the user population, define the controllability criterion before testing, keep the scenario unknown to the subject, and record objective measures (lateral deviation, time-to-collision, reaction time) plus subjective ratings. Results: **not yet executed**.

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm benchmark values (R79, R171, EU 2025/1899) against licensed texts and finalise §5.2 | HF specialist | G1 |
| OI-2 | Closed (2026-10-12): the numeric DM performance targets for DMP-01/02 were confirmed by the SOTIF lead and AI/ML safety lead (acting, one person) as proposed in WP-C-11 AIR-07/AIR-08, with the end-to-end alert time set at ≤ 6 s. Validation is VT-08 in WP-V-02. Assessor approval of the numeric validation targets is still WP-V-02 OI-3 | SOTIF lead | G2 |
| OI-3 | Controllability pass criteria and sample size (CA-01…CA-07): set in §7.1 (decision register DQ-034, A) and approved by the lead as proposed on 2026-10-19, before any test; now frozen. Open: the later check by an assessor (none engaged yet, DQ-009 C) | Safety manager | G1 |
| OI-4 | HARA side done 2026-10-16: H-STPA-1 is rated in WP-C-03 v0.4 (OS-17, OS-18, H-09, SG-08 ASIL A; DQ-003, DQ-205). Left: revise WP-C-04 §7 (driver monitoring QM) for SG-08, and confirm the C2 of HE-09.1 with the DM clinic (§8 V-5) | Safety engineer | G1 |
| OI-7 | Closed 2026-10-14 (listed as a second OI-4 until v0.3): the lead kept today's behaviour, gas pauses speed control only and `DisengageOnAccelerator` stays `0` (decision register DQ-022, A). The confusion of MC-08 is covered by the override alert, which the HMI clinic (§8 V-2) must show is understood | Maintainer | — |
| OI-5 | Check whether alert volume can be reduced below an audible floor (MC-12) | SW lead | G2 |
| OI-6 | Confirm whether the `mici` device-specific DM alerts (`events.py:1018+`) apply to the reference device | SW lead | G1 |
| OI-8 | ~~Implement the §5.4 rule in `policy.py`~~ (done 2026-10-17, SWSR-634; unit tests only). Validate it per WP-V-02 §4.4; revisit the anchor of D*k* if the response or nuisance results fail | SW lead (implementation); SOTIF lead (validation) | G3 |
