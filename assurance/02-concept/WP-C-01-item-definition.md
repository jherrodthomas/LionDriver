# WP-C-01 Item Definition

| Field | Value |
|---|---|
| Work product | WP-C-01 Item definition |
| Standard reference | ISO 26262-3:2018 §5; ISO 21448:2022 §5 (specification of the functionality and system); ISO/SAE 21434:2021 §9.3; ASPICE SYS.1 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Item level (ASIL determined in [WP-C-03](WP-C-03-hara.md)) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); input to HARA confirmation review (I3) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Item identification

| Attribute | Value |
|---|---|
| Item name | LionDriver Supervised Driving Assistance (LD-SDA) |
| Item type | Aftermarket retrofit, supervised SAE Level 2 driving automation feature (lateral and longitudinal control at the same time, driver supervising) |
| Reference vehicle | 2020 Toyota Corolla LE sedan, US market, 1.8 L ICE (non-hybrid), Toyota Safety Sense 2.0 |
| openpilot platform | `TOYOTA_COROLLA_TSS2` (`opendbc_repo/opendbc/car/toyota/values.py:201`), flags `TSS2 \| NO_DSU` |
| Reference vehicle record | VIN, build date, ECU firmware versions (engine `0x700`/`0x7e0`, EPS `0x7a1`, ABS `0x7b0`, radar `0x750/0xf`, camera `0x750/0x6d`), options and tyre size: **to be recorded** (OI-1) |
| Device | comma device (comma 3X or comma four) with integrated "panda" safety MCU (STM32H7) and Toyota TSS2 harness. Exact hardware revision, panda serial and harness type **to be recorded** (OI-2) |
| Software | LionDriver release baseline: openpilot tree + submodules pinned by commit + model weights (LFS), per [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) |

## 2. Purpose and functional description

LD-SDA helps the driver by controlling steering (lane centring) and speed (adaptive cruise with stop-and-go) on roads within its ODD ([WP-C-02](WP-C-02-odd-and-intended-functionality.md)). The driver stays responsible for the driving task at all times. The driver must supervise continuously and be ready to take over immediately. A driver monitoring function enforces attention.

### 2.1 Functions

| ID | Function | Description | Main implementation |
|---|---|---|---|
| F-01 | Lateral control (lane centring) | Computes a desired path or curvature from the camera-based ML driving model and commands steering torque to the Toyota EPS over its LKA interface (`STEERING_LKA`, `0x2E4`). Lane changes are driver-initiated with the turn signal and assisted (desire input) | `selfdrive/modeld`, `selfdrive/controls/controlsd.py`, `selfdrive/controls/lib/latcontrol_torque.py`, `opendbc/car/toyota/carcontroller.py` |
| F-02 | Longitudinal control (ACC with stop-and-go) | Holds the set speed or follows a lead vehicle. Commands acceleration and deceleration to the powertrain/brake ECUs through `ACC_CONTROL` (`0x343`), including permit-braking, standstill and cancel. Lead detection fuses the stock radar track and vision. In Experimental Mode the end-to-end model also proposes acceleration (stops for traffic lights and signs; see WP-C-02 for whether it is in scope) | `selfdrive/controls/plannerd.py`, `lib/longitudinal_planner.py`, `radard.py`, `carcontroller.py:179-254` |
| F-03 | Engagement and mode management | Engagement through the stock cruise controls. The safety MCU grants control authority only on the rising edge of the PCM cruise-active signal. Disengages on brake, cancel or faults. Supports override (driver gas, driver steering) | `selfdrive/selfdrived/state.py`, `selfdrived.py`; `opendbc/safety/safety.h:518-527` |
| F-04 | Driver monitoring | A driver-facing camera and ML model estimate attention. Escalating warnings (5/8/13 s on the vision policy), forced deceleration on no response, and lockout after repeated non-compliance | `selfdrive/modeld/dmonitoringmodeld.py`, `selfdrive/monitoring/policy.py` |
| F-05 | Driver information and warnings | Device display and sounds (`soundd`), plus the instrument cluster LKA HUD (`LKAS_HUD`, `0x412`). Alerts follow the event classes (warning, soft disable, immediate disable, no-entry) | `selfdrive/selfdrived/events.py`, `alertmanager.py`, `selfdrive/ui` |
| F-06 | Forward collision warning | Warning based on the model's hard-brake prediction or a planner crash estimate. Does not brake. The stock Toyota PCS stays in charge of AEB | `selfdrived.py:441-445`, `modeld/fill_model_msg.py:142-147` |
| F-07 | Lane departure warning | Warning when the vehicle is not engaged laterally, above 31 mph, with no recent turn signal | `selfdrive/controls/lib/ldw.py` |
| F-08 | Safety envelope | On the panda MCU: TX whitelist, actuation limits (torque magnitude/rate/measured tracking, accel bounds), engagement gating, RX plausibility checks, relay malfunction detection, heartbeat supervision | `opendbc_repo/opendbc/safety/*`, `panda/board/*` |
| F-09 | Data logging, upload, remote access, software update (non-driving) | Drive logging, upload to a server, remote RPC (athena), SSH, OTA update (`updated`). Relevant for cybersecurity and field monitoring | `system/loggerd`, `system/athena`, `system/updated` |

### 2.2 Vehicle functions replaced, preserved and affected

| Stock TSS 2.0 function | With LD-SDA installed | Basis |
|---|---|---|
| Lane Departure Alert / Lane Tracing Assist (camera-based steering assist) | **Replaced.** The harness relay intercepts the camera's LKA messages; `0x2E4`, `0x191` and `0x412` from the camera are blocked from the car side | `opendbc/safety/safety.h:274-281`; `toyota.h:6-32` |
| Dynamic Radar Cruise Control | **Replaced** by openpilot longitudinal control (`0x343` from the camera blocked, relay-checked when openpilot longitudinal is active) | `toyota/interface.py:105`; `toyota.h:32-36` |
| Pre-Collision System (AEB, pedestrian detection) | **Intended to be preserved** (camera PCS messages forwarded). **Not verified** — AOU-04, and hazard H-08 in [WP-C-03](WP-C-03-hara.md) | `docs/INTEGRATION.md` |
| Road sign assist, automatic high beams | Assumed unaffected. Not verified (OI-3) | — |
| EPS, brakes, ABS/VSC, powertrain | Not modified. Commanded only through existing ADAS interfaces | — |

## 3. Item boundary

### 3.1 Elements inside the item

| Element | Description |
|---|---|
| E-01 Application SoC software | openpilot processes on the comma device (AGNOS Linux): camerad, modeld, dmonitoringmodeld, dmonitoringd, plannerd, radard, controlsd, selfdrived, card, pandad, locationd, calibrationd, paramsd, torqued, lagd, sensord, ui, soundd, plus non-driving processes (loggerd, uploader, athenad, updated, webrtcd) (`system/manager/process_config.py:70-121`) |
| E-02 ML models | Driving model(s) and driver monitoring model (LFS artefacts under `selfdrive/modeld/models/`) |
| E-03 Safety MCU firmware | panda firmware (`panda/board`) with the opendbc safety Toyota mode |
| E-04 Device hardware | comma device: SoC, panda MCU, road and driver cameras, IMU, GNSS, display, speaker, power supply, CAN transceivers, enclosure, windscreen mount |
| E-05 Harness | Toyota TSS2 harness with intercept relay between the forward camera and the vehicle CAN |
| E-06 Optional external compute ("Chestnut" big-model eGPU over USB) | **Excluded from the reference configuration** pending analysis of GAP-17 (OI-4) |

### 3.2 Elements outside the item (environment and existing vehicle elements)

| Element | Relationship | Assumptions |
|---|---|---|
| Toyota EPS | Receives LKA torque requests; reports driver torque, EPS torque and LKA state | AOU-01, AOU-02 |
| Engine/powertrain ECU and brake actuator (ABS/VSC) | Receive ACC acceleration and permit-braking commands through the PCM ACC interface; report pedal states, wheel speeds, cruise state | AOU-03, AOU-05, AOU-10 |
| Toyota forward camera | Its LKA/ACC outputs are intercepted. Its PCS outputs are forwarded | AOU-04 |
| Toyota forward radar | Provides lead tracks to openpilot. Supports the stock PCS | AOU-04 |
| Instrument cluster and cruise stalk | Driver controls (cruise main, set, resume, cancel) and LKA HUD display | AOU-05 |
| Driver | Supervises, overrides, responds to warnings | AOU-06, AOU-07 |
| comma.ai back end (connect, athena server) and update origin | External network entities. Not trusted for safety | Cybersecurity assumptions in [WP-C-10](WP-C-10-cybersecurity-goals-and-concept.md) |
| Road environment, other road users | Operating environment | [WP-C-02](WP-C-02-odd-and-intended-functionality.md) |

### 3.3 Boundary diagram

```
                ┌──────────────────────── ITEM: LD-SDA ─────────────────────────┐
 Driver ◀──HMI──┤ E-04 device display/sound   E-01 SoC software + E-02 models  │
 (eyes,  ─face─▶│ driver camera ─▶ DM          road camera ─▶ driving model    │
  hands,        │                         │ SPI                                │
  pedals)       │                 E-03 panda safety MCU (envelope)             │
                │                    bus 0 (car side) ║  bus 2 (camera side)  │
                │                 E-05 harness relay ═╬══════════════════════  │
                └─────────────────────────────────────╫────────────────────────┘
                     vehicle CAN ◀════════════════════╝════▶ Toyota forward camera
   ┌──────────┬─────────────┬───────────┬─────────────┬───────────┐
   │ EPS      │ ECM / PCM   │ ABS / VSC │ Radar       │ Cluster   │   (existing elements, outside item)
   └──────────┴─────────────┴───────────┴─────────────┴───────────┘
```

### 3.4 Interfaces

| ID | Interface | Direction | Content (examples) | Safety relevance |
|---|---|---|---|---|
| IF-01 | Vehicle CAN, car side (panda bus 0) | TX | `0x2E4` STEERING_LKA (torque, steer request), `0x343` ACC_CONTROL (accel, permit braking, cancel), `0x412` LKAS_HUD, `0x1D2` PCM cancel (TX whitelist `toyota.h:6-32`) | Actuation path (SG-01, SG-03, SG-04) |
| IF-02 | Vehicle CAN, car side | RX | `0xAA` wheel speeds, `0x260` steering torque sensor (driver and EPS torque), `0x1D2` PCM_CRUISE (cruise active, gas released), `0x226` brake module, EPS_STATUS, radar tracks | Engagement gating, override detection, limits |
| IF-03 | Camera side CAN (panda bus 2) | RX/forward | Camera messages forwarded to the car, except intercepted control messages | PCS preservation (H-08) |
| IF-04 | SoC ↔ panda | SPI | CAN TX/RX streams, heartbeat (`0xf3`), safety-mode set (`0xdc`), health | Freedom from interference ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) |
| IF-05 | Road-facing cameras | In | Images for the driving model and calibration | SOTIF |
| IF-06 | Driver-facing camera (IR) | In | Images for the DM model | Controllability basis |
| IF-07 | HMI | Out/In | Display, sounds, device touchscreen settings (toggles, e.g. Experimental Mode), cluster HUD | Mode awareness, warnings |
| IF-08 | Power | In | Vehicle 12 V via the harness; ignition detection | Availability, safe shutdown |
| IF-09 | Network (Wi-Fi/LTE) | Bidirectional | Athena RPC, uploads, OTA updates, SSH | Cybersecurity ([WP-C-09](WP-C-09-tara.md)) |

## 4. Operating modes and states

| Mode | Description | Actuation |
|---|---|---|
| Off / offroad | Ignition off or device offroad. panda in `NO_OUTPUT` or `SILENT` (`pandad.cc:204-207`) | None |
| Onroad, disengaged | Car safety mode active, `controls_allowed = false` | None (non-zero torque or accel rejected, `lateral.h:98-101`) |
| Pre-enabled / enabled | Engaged after the PCM cruise rising edge and no NO_ENTRY condition (`state.py:79-90`) | Lateral and longitudinal |
| Overriding | Driver gas or steering input while engaged. Longitudinal blocked while gas pressed (`longitudinal.h:3-5`) | Lateral; no longitudinal |
| Soft disabling | Fault detected; warning; actuation continues up to 3 s (`state.py:7`) — see GAP-16 | Lateral and longitudinal (forced decel) |
| Immediate disable | Critical fault; control released at once | None |
| Driver lockout | DM non-compliance; engagement prevented for 1–30 min (`policy.py:42-44`) | None |
| Chill vs Experimental Mode | Longitudinal policy selection (MPC vs end-to-end model). Upstream default is Experimental (`params_keys.h:43`, GAP-18) | — |
| Debug / maneuver / joystick modes | Developer modes that replace control processes (`process_config.py:34-47`) | **Excluded from the reference configuration** (OI-5) |

## 5. Legal requirements, national and international standards

| Source | Applicability |
|---|---|
| FMVSS (US) | The vehicle's FMVSS compliance must not be degraded (e.g. FMVSS 126 ESC, 135 brakes are unaffected by design — verify). No FMVSS covers L2 ADAS function |
| NHTSA Standing General Order 2021-01 (as amended) | Crash reporting for L2 ADAS applies to manufacturers and operators. Used as the model for [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |
| State vehicle codes | Driver remains legally responsible. Some states regulate testing of automated driving; L2 is generally outside those rules (to be confirmed per test state, OI-6) |
| ISO 11270 (LKAS), ISO 15622 (ACC), ISO 22179 (FSRA) | Performance and actuation limit references (`docs/SAFETY.md`) |
| UNECE R79 (ACSF), R171 (DCAS), EU 2025/1899 DM reference | Not legally binding in the US. Used as benchmarks for HMI, DM and actuation limits |
| ISO 26262, ISO 21448, ISO/SAE 21434, ISO/PAS 8800 | Applied voluntarily per [WP-M-01](../01-management/WP-M-01-assurance-strategy.md) |

## 6. Known hazards and experience from similar items

- Unintended or excessive steering torque, unexpected loss of steering assistance in curves, phantom braking, insufficient braking for stationary vehicles, failure to release on driver override, mode confusion (driver believes the system is engaged when it is not).
- Over-reliance and inattention on hands-free capable L2 systems (NHTSA investigations of L2 systems). openpilot uses vision-based DM and **does not require hands on the wheel**. This is an important factor for controllability and misuse.
- Limitations listed upstream in `docs/LIMITATIONS.md`: poor weather, glare, sharp curves, construction zones, stationary vehicles, cut-ins, pedestrians, traffic lights not detected.

## 7. Assumptions of use (AoU) and external measures

Each assumption needs verification evidence before it is credited in the HARA or safety concept. Status `Unverified` means it is only an assumption.

| ID | Assumption | Credited in | Verification approach | Status |
|---|---|---|---|---|
| AOU-01 | The Toyota EPS limits the torque applied for LKA requests to a level a normal driver can overpower. It rejects or fades out implausible requests, and it ends LKA torque within a bounded time if LKA messages stop (a code comment suggests ≈1.5–2 s, `carstate.py:15-16`) | Not credited in the HARA (D-09); design input for FSC/TSC limits on H-01/H-05 | Bench and vehicle characterization: max LKA torque at the wheel, timeout behaviour, fault states | Unverified |
| AOU-02 | A normal driver can override full LKA torque with steering force within the controllability criterion set by CA-01 in WP-C-08 §7 (ISO 11270-type limits; ≤ 50 N at the rim indicative) | Not credited in the HARA (D-09); design input for H-01/H-05 | Vehicle measurement with a steering force gauge | Unverified |
| AOU-03 | Driver brake pedal application always produces braking regardless of ACC commands, and the PCM cancels ACC on brake application | Not credited in the HARA (D-09); design input for H-05 | Vehicle test | Unverified |
| AOU-04 | The stock PCS/AEB keeps full function with the harness installed and openpilot longitudinal active | HARA H-08 | Review of forwarded and blocked messages; PCS target test (e.g. soft target) | Unverified |
| AOU-05 | The PCM bounds ACC acceleration and deceleration requests to its own ACC envelope and honours the cancel bit | Not credited in the HARA (D-09); design input for H-03/H-04 | Vehicle test with injected out-of-range requests (on a closed course) | Unverified |
| AOU-06 | The driver is licensed, attentive, briefed according to [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md), and keeps their eyes on the road | Controllability (all) | Enforced by F-04; misuse analysis [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) | Assumption (SOTIF-managed) |
| AOU-07 | During development, only trained safety drivers operate the item on public roads, under [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) | All | Training records | Not started |
| AOU-08 | The device is mounted and calibrated according to installation instructions | SOTIF | Calibration check (`calibrationd`) and installation checklist [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) | Partially (calibration check exists) |
| AOU-09 | The vehicle is maintained, unmodified (suspension, tyres, steering), and has no active DTCs in the EPS, brake or powertrain systems | All | Pre-drive checklist | Not started |
| AOU-10 | VSC/ABS are enabled and functional | Not credited in the HARA (D-09); design input for H-01/H-04 | Pre-drive checklist; CAN status signal | Not started |
| AOU-11 | The comma.ai back end and network are untrusted; no safety function depends on them | CS / FuSa | Architecture review | Design constraint |

## 8. Functional and non-functional performance (summary)

Performance targets are specified in [WP-S-01](../03-system/WP-S-01-system-requirements.md). Inherited limits that define the actuation envelope today (see [gap assessment §3.1](../00-assessment/gap-assessment.md#31-reference-configuration-as-traced-in-code)):

| Parameter | Value | Source |
|---|---|---|
| Max steering torque request | 1500 raw (physical value to be determined, GAP-04) | `toyota.h:173` |
| Torque rate | +15 / −25 raw per 10 ms frame; ≤ 450 raw per 250 ms | `toyota.h:174-177` |
| Lateral acceleration (controller) | ≤ 3.0 m/s² (roll-compensated); jerk ≤ 5 m/s³ | `controls/lib/drive_helpers.py:9-14` |
| Acceleration command | −3.5 … +2.0 m/s² | `toyota.h:207-210` |
| Minimum engagement speed | Toyota TSS2 with stop-and-go: from standstill (verify for Corolla LE, OI-7) | `car_events.py:59-72` |
| Max control speed | ≈ 149 km/h warning (`MAX_CTRL_SPEED`), no disengage | `selfdrive/car/car_events.py:126`; `selfdrived/events.py:989-996` |

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Record the reference vehicle VIN, ECU firmware versions (fingerprint query output), options, tyre size | Maintainer | G1 |
| OI-2 | Record the device hardware revision, panda hardware type and serial, harness type | Maintainer | G1 |
| OI-3 | Confirm which other TSS 2.0 functions (RSA, AHB, BSM if fitted) are affected by the harness | Safety engineer | G1 |
| OI-4 | Decide whether to exclude Chestnut/eGPU from the reference configuration (recommended: exclude) | Maintainer | G1 |
| OI-5 | Define how debug, maneuver and joystick modes are disabled in reference-configuration builds | SW lead | G2 |
| OI-6 | Confirm the legal status of L2 development testing in the state(s) where vehicle testing will take place | Maintainer | Before vehicle testing |
| OI-7 | Confirm the minimum engagement speed and stop-and-go behaviour for the Corolla LE | SW lead | G1 |
| OI-8 | Decide whether Experimental Mode (end-to-end longitudinal, traffic light stopping) is in the reference ODD | Maintainer | G1 |
