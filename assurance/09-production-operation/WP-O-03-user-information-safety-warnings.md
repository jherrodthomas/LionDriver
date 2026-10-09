# WP-O-03 User Information and Safety Warnings

| Field | Value |
|---|---|
| Work product | WP-O-03 User information and safety warnings |
| Standard reference | ISO 26262-7:2018 §6 (user manual / information for operation); ISO 21448:2022 §6 and Annex B (reasonably foreseeable misuse), §13 (information to users in operation); ISO 26262-3:2018 §6 (controllability assumptions) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Controllability basis for SG-01…SG-06 (AOU-06, AOU-07); SOTIF misuse measures |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); HMI / human-factors reviewer TBD |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose and how to use this document

The HARA ([WP-C-03](../02-concept/WP-C-03-hara.md)) rates controllability for "a typical attentive driver" and credits a driver who is "licensed, attentive, briefed according to WP-O-03" (AOU-06). This document is that briefing. It has three parts:

- **Part A (§2–§10)** is the draft user-facing text: the LD-SDA driver information. It is written to be handed to the driver as-is after review. Each paragraph carries an ID (`UI-nn`) for traceability.
- **Part B (§11)** is the safety-driver briefing addendum for the development phase (AOU-07, [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md)).
- **Part C (§12)** traces each UI item to the hazards, safety goals, AoUs and misuse it addresses.

Sources: upstream `docs/LIMITATIONS.md` (reworded for LionDriver; lines cited in §12), the alert definitions in `openpilot/selfdrive/selfdrived/events.py`, the DM policy in `openpilot/selfdrive/monitoring/policy.py`, and [WP-C-01](../02-concept/WP-C-01-item-definition.md). The ODD ([WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md)), functional insufficiencies ([WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md)) and misuse analysis ([WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)) did not exist when this draft was written; their content must be merged in before review (OI-1).

The on-device alert texts are inherited from upstream and say "openpilot". The user text below uses "LD-SDA" and quotes the on-screen texts exactly so the driver recognises them.

---

## Part A — LD-SDA driver information (draft user text)

## 2. What LD-SDA is

**UI-01.** LD-SDA (LionDriver Supervised Driving Assistance) is a **driver assistance system**. It can steer to keep the car centred in its lane and control speed to follow the car ahead, including stopping and starting in traffic. It is SAE Level 2: **you are driving the car at all times.** LD-SDA does not make the car self-driving.

**UI-02.** LD-SDA is approved for use only on this combination: a 2020 Toyota Corolla LE (US, non-hybrid) with Toyota Safety Sense 2.0, the specific comma device and Toyota harness installed and checked by an approved installer, and a released LionDriver software version. Do not move the device to another car.

**UI-03.** LD-SDA replaces two Toyota functions while installed: Lane Tracing Assist (steering) and Dynamic Radar Cruise Control (speed). Toyota's Pre-Collision System (automatic emergency braking) is intended to keep working, but you must never rely on any automatic braking.

## 3. Your responsibilities

**UI-04.** Keep your eyes on the road and your attention on driving the whole time LD-SDA is on. Be ready to steer, brake or accelerate yourself **immediately**, at any moment, without warning.

**UI-05.** Keep your hands at or near the steering wheel. LD-SDA does not require your hands on the wheel, but its steering force is deliberately limited and it can make mistakes that you must correct within about a second.

**UI-06.** You are responsible for the vehicle and for obeying traffic laws. LD-SDA does not detect speed limits, and you must not count on it to stop for traffic lights or stop signs.

**UI-07.** Only use LD-SDA if you are licensed, rested, sober and have read this information. Do not let anyone drive with LD-SDA who has not read it.

**UI-08.** Lane changes: LD-SDA cannot see beside or behind the car. Check mirrors and blind spot yourself, signal, and only then nudge the wheel to start the lane change.

## 4. Where you may use it (operating conditions)

**UI-09.** Use LD-SDA only on: (the final list comes from WP-C-02; draft below)
- limited-access highways and well-marked major roads with clear lane markings;
- in daylight or well-lit conditions with good visibility;
- on dry or wet roads without standing water, snow or ice;
- at speeds you would legally and safely drive yourself.

**UI-10.** Do not use LD-SDA:
- in construction zones, at lane closures, or where lanes are restricted or marked with temporary lines;
- in heavy rain, snow, fog, or blowing dust, or on snow- or ice-covered roads;
- on sharp curves such as on- and off-ramps, at intersections, roundabouts, or on narrow, winding or hilly roads;
- in parking areas, on unpaved roads, or roads without lane markings;
- on highly banked roads or in strong cross-winds;
- when towing a trailer;
- in toll-booth lanes or near railway crossings.

**UI-11. Experimental Mode.** The setting "Experimental Mode" lets the driving model control speed by itself, including attempting to stop at lights and signs. In this LionDriver release it is **[off and not permitted / permitted under conditions — to be set by decision D-08]**. If it is enabled, expect mistakes: it may brake unexpectedly or fail to stop.

## 5. Before every drive

**UI-12.** Check that:
1. no warning lamps for steering, brakes, stability control, engine or Toyota Safety Sense are on;
2. VSC (stability control) is on;
3. the windscreen in front of the device and the Toyota camera is clean and clear (no ice, stickers, objects);
4. the device sits firmly in its mount and the screen shows no calibration message;
5. nothing blocks the device's view of your face (cap brim, mask, phone holder, sun visor).

If any check fails, drive without LD-SDA and fix the problem first.

**UI-13.** After a new installation, a device remount, or a windscreen or suspension repair, LD-SDA needs to calibrate. Drive normally on straight roads above 15 mph until the calibration message disappears. LD-SDA cannot be turned on until calibration is complete.

## 6. Turning it on and off

**UI-14.** Turn on: switch on the Toyota cruise control main switch and set a speed with the cruise lever. LD-SDA becomes active and the device shows it is engaged.

**UI-15.** Turn off at any time by any of:
- **pressing the brake pedal** (turns LD-SDA off immediately);
- pulling the cruise lever to **cancel**;
- switching off the cruise main switch.

**UI-16.** Steering yourself overrides LD-SDA's steering. You can always turn the wheel against it. **Pressing the accelerator does not turn LD-SDA off**: it pauses LD-SDA's speed control while you press it, and steering assistance continues. (This depends on the "disengage on accelerator" setting fixed by the release; see OI-3.)

**UI-17.** If you are not sure whether LD-SDA is on, assume it is **off** and drive manually. Then check the device screen.

## 7. What the warnings mean and what to do

LD-SDA shows messages on the device screen, plays sounds, and may show a steering-wheel symbol in the instrument cluster. Messages are grouped by urgency.

| UI-ID | You see / hear | Meaning | What you must do |
|---|---|---|---|
| UI-18 | **"TAKE CONTROL IMMEDIATELY"**, red full-screen, loud repeating alarm, followed by a reason (e.g. "Controls Mismatch", "Harness Relay Malfunction", "CAN Bus Disconnected", "LKAS Fault: Restart the Car") | A fault was detected. LD-SDA has **already stopped** steering and speed control | Steer and control speed yourself now. Pull over when safe. Do not re-engage; report it (§9) |
| UI-19 | **"TAKE CONTROL IMMEDIATELY"**, full screen with softer alarm and a reason (e.g. "Calibration Invalid", "Excessive Actuation", "Sensor Data Invalid") | LD-SDA has a problem and **will stop within about 3 seconds**. It may keep steering and braking during those seconds, possibly wrongly | Take over **at once**; do not wait for the countdown |
| UI-20 | **"BRAKE!" — "Risk of Collision"** (red, sound) | LD-SDA predicts a collision ahead. **This is only a warning. LD-SDA is not braking hard for you** | Brake and steer as needed immediately |
| UI-21 | **"BRAKE!" — "Stock AEB: Risk of Collision"** | Toyota's own emergency braking has triggered | Brake firmly and steer as needed |
| UI-22 | **"Take Control" — "Turn Exceeds Steering Limit"** | The curve needs more steering than LD-SDA is allowed to apply | Steer yourself now |
| UI-23 | **"Steering Assist Temporarily Unavailable"** | Steering assistance is paused | Steer yourself |
| UI-24 | **"openpilot Unavailable"** with a reason, short "refuse" sound | LD-SDA cannot be engaged right now (e.g. calibration in progress, door open, seatbelt, too distracted) | Drive manually; fix the reason if you can |
| UI-25 | **"Lane Departure Detected"** (when LD-SDA steering is not engaged, above 31 mph) | The car is leaving its lane without the turn signal | Steer back |
| UI-26 | **"openpilot will disengage"** | You did something that will turn LD-SDA off (for example, reverse gear) | Take control |
| UI-27 | A ring of chimes when engaging or disengaging | State change confirmation | Confirm the new state on the screen |

**UI-28.** Never ignore an alert, and never wait to see whether LD-SDA corrects itself. If something looks wrong — the car drifts, steers toward an obstacle, brakes for no reason or does not slow for a stopped car — take over **before** any alert appears. Alerts do not cover every mistake LD-SDA can make.

## 8. Driver monitoring

**UI-29.** A camera facing you checks whether you are watching the road. It works above about 6 mph (10 km/h). If you look away:

| Stage | After about (looking away) | You see / hear |
|---|---|---|
| 1 | 5 s | "Pay Attention" (small, soft tone) |
| 2 | 8 s | "Pay Attention — Driver Distracted" (repeating tone) |
| 3 | 13 s | **"DISENGAGE IMMEDIATELY — Driver Distracted"** (red, loud) |

If the camera cannot see your face, it asks you to touch the wheel instead ("Touch Steering Wheel: No Face Detected", then "Touch Steering Wheel — Driver Unresponsive", then "DISENGAGE IMMEDIATELY — Driver Unresponsive"), at about 5 s, 15 s and 25 s. (Timers from `policy.py:30-35`; the times shorten if you are repeatedly inattentive.)

**UI-30.** If you do not respond to stage 3, LD-SDA slows the car down. It does **not** stop the car safely at the roadside — you must take over.

**UI-31.** If you reach stage 3 twice, or do not respond once, LD-SDA locks itself out for 1 to 30 minutes, getting longer each time. You will see "openpilot Unavailable" with a distraction message. Drive manually.

**UI-32.** Driver monitoring can be fooled or can fail: in low light, at night, in tunnels, in glare, with sunglasses, if your face is partly out of view, or if the camera is blocked. Touching the wheel or pedals resets the "touch wheel" timer even if you are not watching the road. **Driver monitoring is a reminder, not a measure of your attention.** You are responsible for your attention.

**UI-33.** Do not block, cover or point the driver camera away, and do not use the "driver camera view" setting while driving.

## 9. Limitations you must know

**UI-34.** LD-SDA's steering may fail to work as intended, for example:
- poor visibility (rain, snow, fog), glare from low sun or oncoming headlights;
- dirty, iced or damaged windscreen in front of the cameras; stickers or coatings;
- a wrongly mounted device;
- sharp curves (LD-SDA's steering force is limited);
- construction zones, restricted lanes, faded or confusing lane markings;
- banked roads, strong cross-wind, hills, narrow or winding roads;
- very hot or cold temperatures.

**UI-35.** LD-SDA's speed control and collision warning may fail to work as intended, for example:
- **stopped vehicles in your lane** — LD-SDA may not slow down for them;
- vehicles cutting in close in front of you;
- situations needing hard braking — LD-SDA's braking is limited (about 3.5 m/s²);
- pedestrians, cyclists, animals and objects on the road;
- traffic lights and stop signs (not reliably detected);
- speed limits (not detected; LD-SDA holds the speed you set);
- toll booths, bridges, large metal plates, other radar equipment;
- poor visibility, dirty or blocked camera or radar, hills, winding roads, extreme temperatures, glare.

**UI-36.** LD-SDA may brake when there is no reason ("phantom braking"). Watch your mirrors and be ready to press the accelerator.

**UI-37.** These lists are not complete. Other situations can also cause LD-SDA to behave wrongly.

## 10. Prohibited use

**UI-38.** Do **not**:
1. read, use a phone, watch video, sleep or do anything else that takes your eyes or mind off driving while LD-SDA is on;
2. leave the driver's seat, or let anyone else operate LD-SDA without having read this information;
3. use LD-SDA outside the conditions in §4, or in any car other than the one it was installed in;
4. modify the device, harness, software or settings (other than the settings this document allows), install unofficial software, or run developer or debug modes;
5. defeat or trick driver monitoring (covering the camera, weights on the wheel, devices that imitate steering input);
6. use LD-SDA if any warning lamp is on, after a crash, or after a "TAKE CONTROL IMMEDIATELY" fault until it has been checked;
7. use LD-SDA when towing, or with non-standard tyres, suspension or steering parts;
8. let LD-SDA drive through intersections, around pedestrians, or in places where you would not trust a beginner driver.

## 11. Reporting problems and updates

**UI-39.** Press the flag button on the device screen right after anything that felt wrong or unsafe. This saves that part of the drive. Then report it to LionDriver through the channel given at installation [to be defined, see [WP-O-04](WP-O-04-field-monitoring.md)]. Do not delete drives before they have been collected.

**UI-40.** Report every crash or near miss that happened while LD-SDA was on, or within 30 seconds after it turned off.

**UI-41.** Install only LionDriver releases that you have been told are approved. Tell LionDriver about any repair to the steering, suspension, brakes, windscreen, cameras or radar, and about any software update a dealer installed. Some of these mean LD-SDA must be re-checked before you use it again ([WP-O-02](WP-O-02-operation-service-decommissioning.md) §4).

**UI-42.** If LionDriver issues a **stop-use notice**, stop using LD-SDA at once. The car remains normal to drive with LD-SDA off.

**UI-43. Data.** The device records video of the road and of you, vehicle data and your location while driving. [Where recordings go, who can see them and how to delete them: to be completed from the data-protection decision, [WP-O-04](WP-O-04-field-monitoring.md) §5.]

---

## Part B — Development-phase safety-driver briefing addendum

This addendum applies until release (G5). It supplements, and does not replace, the safety-driver procedures in [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md).

| ID | Briefing item |
|---|---|
| SD-01 | The software is a development build. It has **not** passed safety validation. Behaviour may change between builds without notice. Treat every build as untrusted |
| SD-02 | Only approved safety drivers who completed the training in [WP-M-04](../01-management/WP-M-04-organization-competence-safety-culture.md) may engage the item on public roads, on routes and conditions approved in the test plan |
| SD-03 | Hands on the wheel at all times (stricter than UI-05). Foot ready to cover the brake in traffic |
| SD-04 | Known weaknesses of this baseline that the driver must be aware of: soft-disable keeps actuating up to 3 s on failed inputs (GAP-16); fault detection times in the safety MCU are seconds, not tenths of seconds (GAP-06); Experimental Mode is on by default upstream (GAP-18; check the setting before every drive); `cruiseMismatch` produces no reaction (GAP-19); the safety envelope does not itself monitor driver steering torque (GAP-02) |
| SD-05 | Abort criteria: any unexpected steering input, any "TAKE CONTROL IMMEDIATELY", any Excessive Actuation, any unexplained brake event. After an abort, testing on that build stops until the safety manager releases it ([WP-M-02 §9](../01-management/WP-M-02-safety-plan.md#9-safety-anomaly-handling)) |
| SD-06 | Flag every event (UI-39) and log it in the test log with time and route ID |
| SD-07 | No passengers other than test personnel; no testing in conditions excluded by UI-10 unless the test plan explicitly covers them with extra measures |
| SD-08 | Never modify parameters or run tools onroad; the second person (if present) monitors the device, not the driver |

---

## Part C — Traceability

## 12. Traceability to hazards, safety goals, AoUs and misuse

Misuse-case IDs are to be taken from [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) when it exists; the "Misuse / insufficiency addressed" column describes them in words until then (OI-2).

| UI item | Hazard / SG | AoU | Misuse / insufficiency addressed | Source |
|---|---|---|---|---|
| UI-01, UI-04 | H-01, H-02, H-03, H-06 / SG-01, SG-02, SG-03, SG-06 (controllability C2 basis) | AOU-06 | Over-reliance; treating L2 as self-driving | WP-C-03 §5; `docs/LIMITATIONS.md:4, 25` |
| UI-02 | All | AOU-08, AOU-09 | Use on non-reference vehicle | WP-M-01 §3.1 |
| UI-03, UI-21 | H-08 / SG-07 | AOU-04 | Reliance on AEB | WP-C-01 §2.2 |
| UI-05 | H-01, H-02 / SG-01, SG-02 | AOU-02, AOU-06 | Hands-off driving (foreseeable; openpilot does not require hands on) | WP-C-03 HE-02.1; `docs/SAFETY.md:32` (0.9 s to 1 m) |
| UI-06, UI-35 | H-06 / SG-06 (SOTIF SH-06) | AOU-06 | Reliance on light/sign detection; speed limits | `docs/LIMITATIONS.md:35-36`; GAP-18 |
| UI-07 | All | AOU-06 | Impaired or unbriefed driver | AOU-06 |
| UI-08 | H-01 | AOU-06 | Lane change without checking | `docs/LIMITATIONS.md:6` |
| UI-09, UI-10 | H-01, H-02, H-04, H-06 (SOTIF triggering conditions) | AOU-06 | Use outside ODD | WP-C-02 (pending); `docs/LIMITATIONS.md:8-21, 27-43` |
| UI-11 | H-03, H-04, H-06 | — | Unvalidated end-to-end longitudinal | D-08; GAP-18 |
| UI-12 | All | AOU-08, AOU-09, AOU-10 | Driving with faults or obstructed sensors | [WP-O-02](WP-O-02-operation-service-decommissioning.md) OPS-01…OPS-05 |
| UI-13 | H-01, H-02 (SOTIF) | AOU-08 | Driving with stale calibration | `calibrationd.py:24-36` |
| UI-14…UI-17 | H-05 / SG-05; mode confusion → H-02, H-06 | AOU-03 | Mode confusion; belief that gas disengages | WP-C-03 §4 (F-03/F-05), HE-05.3; `longitudinal.h:3-5`; `params_keys.h:35` |
| UI-18, UI-19 | H-02, H-06 / SG-02, SG-06 | AOU-06 | Slow reaction to take-over request; waiting out soft disable | `events.py:161-182` (alert classes); GAP-16 |
| UI-20 | H-06 (SOTIF) | AOU-06 | Confusing FCW with automatic braking | `events.py:493-498`; F-06 |
| UI-22, UI-23 | H-02 / SG-02 | AOU-06 | Reliance in sharp curves | `events.py:511-517, 619-625` |
| UI-24 | — | — | Repeated attempts to engage under no-entry | `events.py:149-158` |
| UI-25 | — (QM) | — | — | F-07; `selfdrive/controls/lib/ldw.py` |
| UI-28 | H-01…H-06 | AOU-06 | Expecting an alert before every error | SOTIF residual insufficiency |
| UI-29…UI-31 | H-02, H-06 (controllability) | AOU-06 | Inattention | `policy.py:28-44`; `events.py:519-565` |
| UI-32, UI-33 | H-02, H-06 | AOU-06 | Over-trust in DM; DM defeat; DM demo mode (`IsDriverViewEnabled`) | `docs/LIMITATIONS.md:47-58`; GAP-20, GAP-21 |
| UI-34 | H-01, H-02 | AOU-06, AOU-08 | — (functional insufficiency awareness) | `docs/LIMITATIONS.md:8-21` |
| UI-35, UI-36 | H-03, H-04, H-06 | AOU-06 | Reliance on ACC for stationary vehicles; surprise at phantom braking | `docs/LIMITATIONS.md:27-43` |
| UI-38 | All | AOU-06, AOU-09 | Deliberate misuse (inattention, DM defeat, modification, debug modes) | GAP-20; ISO 21448 Annex B categories |
| UI-39, UI-40 | — (field monitoring) | — | Under-reporting | [WP-O-04](WP-O-04-field-monitoring.md) |
| UI-41, UI-42 | All | AOU-01…AOU-05, AOU-09 | Use after vehicle changes; use after stop-use notice | [WP-O-02](WP-O-02-operation-service-decommissioning.md) §4, §6 |
| UI-43 | — (privacy, CS) | AOU-11 | — | [WP-O-04](WP-O-04-field-monitoring.md) §5 |
| SD-01…SD-08 | All | AOU-07 | Development-phase test risk | [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) |

### 12.1 Effectiveness

User information is a weak measure on its own. ISO 21448 expects its effectiveness to be shown, not assumed. Planned evidence: a comprehension check of the briefing for every driver (signed, WP-O-01 INS-30), and field-monitoring KPIs on DM alerts, lockouts and out-of-ODD use ([WP-O-04](WP-O-04-field-monitoring.md)). Until that evidence exists, the safety case treats AOU-06 as an assumption, not a verified measure ([WP-K-01](../10-safety-case/WP-K-01-safety-case.md)).

## 13. Inconsistencies found in the inherited HMI

These affect the user text and should be fixed in the software rather than explained around:

| # | Inherited behaviour | Effect on user information |
|---|---|---|
| 1 | `canError` shows "Unknown Vehicle Variant" (`events.py:928-936`) for CAN rate faults (GAP-19) | Users cannot connect the text to a wiring fault. UI-18 lists the other texts only |
| 2 | Alert texts say "openpilot", not "LD-SDA" | Users must be told they are the same (§1) |
| 3 | Fault texts say "Contact comma.ai/support" (`events.py:629, 976`: fan malfunction, harness relay malfunction) | Conflicts with UI-39; LionDriver, not comma.ai, supports this configuration |
| 4 | Experimental Mode on by default (`params_keys.h:43`) while `docs/LIMITATIONS.md:35` says lights are not detected | UI-06 and UI-11 depend on D-08 |
| 5 | `StartupAlert` default text "Always keep hands on wheel and eyes on road" (`events.py:199-200`) vs. no hands-on requirement in DM | UI-05 explains the difference; consider aligning |

## 14. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Merge the final ODD (WP-C-02), insufficiency list (WP-C-06) and misuse analysis (WP-C-08) into §4, §9, §10 and §12 | G1 |
| OI-2 | Replace the misuse descriptions in §12 with WP-C-08 misuse-case IDs | G1 |
| OI-3 | Fix the accelerator behaviour statement (UI-16) after the HMI decision on `DisengageOnAccelerator` | G1 |
| OI-4 | Complete UI-11 after decision D-08, UI-39/UI-43 after the WP-O-04 data path and privacy decisions | G1 |
| OI-5 | Human-factors review and comprehension test of the draft text with drivers who are not project members | G5 |
| OI-6 | Raise change requests for the HMI inconsistencies in §13 | G2 |
| OI-7 | Decide the delivery format (printed booklet plus on-device acceptance; the inherited `HasAcceptedTerms` / `CompletedTrainingVersion` flow shows comma.ai's terms and training) | G5 |
