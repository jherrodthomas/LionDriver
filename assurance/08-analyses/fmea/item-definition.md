# LionDriver — Item Definition

| | |
|---|---|
| **Doc ID** | LD-ITEM-001 |
| **Revision** | 0.1 (draft) |
| **Date** | 2026-10-10 |
| **Status** | Draft — requires review by Jherrod Thomas; item-definition confirmation per ISO 26262-2 not yet performed |
| **Standard** | ISO 26262-3:2018 clause 5 |
| **Baseline** | BL-001 (LionDriver `8b8c6ae`, panda `92eb565`, opendbc `229dc70`, AGNOS 19.9) |
| **Annexes** | [Vehicle catalog](item/vehicle-catalog.md) (generated), [variants.yaml](item/variants.yaml) |
| **Downstream** | System FMEA, HARA LD-HARA-001, FSC LD-FSC-001, DFA LD-DFA-001 |

This document defines the item at three levels:

- **Part A — Platform.** LionDriver on every vehicle BL-001 supports: 334 road vehicles from 26 makes.
- **Part B — Variant family.** The Toyota Corolla E210.
- **Part C — Assured configuration.** The 2020 Corolla LE sedan, the only configuration the current safety analyses cover.

---

## 1. Variant model

### 1.1 Levels

| Level | ID | What it is | Defined by |
|---|---|---|---|
| Platform | PL-001 | Functions, architecture, interfaces and assumptions common to every supported vehicle | Part A |
| Variant family | VF-xxx | A group of vehicles sharing one opendbc platform, harness and actuator interface, so they share a safety model and limits | Part B; `item/variants.yaml` |
| Assured configuration | AC-xxx | One vehicle, trim, market, device, harness and software baseline that safety analyses are performed and claimed for | Part C; `baseline.yaml` |

### 1.2 What is claimed where

- **Safety claims are made only for assured configurations.** Today that is AC-001 alone. HARA rev 0.3, FSC rev 0.2 and DFA rev 0.3 were performed for AC-001.
- **Variant families are in assessment.** An extension from AC-001 to another member of the same family needs a variant impact analysis against the parameters in §A.10.
- **Every other vehicle is "not assessed"** (327 of 334 in the catalog). LionDriver makes no safety claim for them, even though BL-001 software runs on them.

### 1.3 Related items

| Related item | How LionDriver differs |
|---|---|
| Stock Toyota Safety Sense 2.0 (Lane Tracing Assist, Dynamic Radar Cruise Control) | The stock camera's steering and ACC commands are replaced while the item is engaged; stock AEB/FCW are meant to stay (F8, HARA OI-003) |
| Upstream openpilot (comma.ai) | Same software at BL-001; LionDriver adds the assurance lifecycle, a frozen baseline and, after LD-DES-001, its own signed panda firmware and vehicle lock |
| Other openpilot forks | Not covered; LionDriver claims nothing for software outside its baselines |
| Corolla Cross, Corolla Cross Hybrid, Lexus UX Hybrid | Share VF-001's opendbc platform but are separate vehicles outside the family (§B.3) |

---

# Part A — Platform (PL-001)

## A.1 Purpose

LionDriver adds SAE Level 2 driving assistance to production vehicles that already have adaptive cruise control and lane-keeping hardware. It is installed by the vehicle owner. The driver supervises at all times and remains responsible for the driving task.

## A.2 Functions

The functions are the same on every vehicle. Their limits and interfaces are vehicle-specific (§A.10).

| ID | Function | Vehicle-level behavior |
|---|---|---|
| F1 | Lateral control (ALC) | Steers the vehicle within its lane through the vehicle's own steering actuator (torque, angle or curvature request, depending on the vehicle) |
| F2 | Longitudinal control | Holds a set speed and follows lead vehicles. On vehicles marked "openpilot" in the catalog, LionDriver commands acceleration; on "Stock" vehicles, the vehicle's ACC does. In **Experimental Mode** (on by default in BL-001, `openpilot/common/params_keys.h:43`), the driving model also slows and stops for traffic lights, stop signs and curves. |
| F3 | Engagement management | Engages only on a driver request, through the vehicle's cruise controls; disengages on faults with a soft or immediate reaction |
| F4 | Driver override | Brake or cancel ends control; steering and accelerator input override the matching axis |
| F5 | Driver monitoring | A camera-based attention policy, with a wheel-touch fallback, escalates alerts and locks out engagement after repeated non-response |
| F6 | Alerting | Visual and audible alerts on the device; vehicle HUD and cluster indications where the vehicle supports them |
| F7 | Actuation limiting | Bounds actuator requests in the SoC controller and, independently, in the panda safety model |
| F8 | Stock function preservation | Keeps the vehicle's stock safety functions (e.g. AEB, FCW) available while installed |

**Not included:**
- Driving without supervision.
- Automatic lane changes without driver initiation.
- Operation when the vehicle's own ACC/LKA hardware is absent.
- Offroad features (navigation, logging upload, remote access) except where they affect onroad behavior. OTA updates do affect it, through the PFMEA.

## A.3 Item boundary and architecture

```
                  ┌──────────────────── item ────────────────────┐
 driver ◄──HMI──► │  comma 3X                                    │
 cameras, IMU ──► │   SoC: openpilot software (QM)               │
                  │    │ SPI + GPIO (reset/BOOT0)                │
                  │   panda MCU: safety model (opendbc)          │──► relay ─┐
                  │                                              │           │
                  │  harness (vehicle-specific connector)        │◄──────────┘
                  └──────────────┬───────────────────────────────┘
                                 │ CAN / CAN FD, 12 V
         vehicle: EPS · powertrain/brakes · ADAS camera/radar · gateway · cluster
```

| In the item | Outside the item (interfaces only) |
|---|---|
| comma 3X device: SoC, cameras, IMU, GNSS, display, speaker | Vehicle ECUs: steering, powertrain, brakes, ADAS camera and radar, gateway, instrument cluster |
| Integrated panda MCU and its firmware | Vehicle CAN buses and 12 V supply |
| Harness for the vehicle (camera-intercept, gateway/J533 or other, per catalog) | The driver |
| openpilot software, including the opendbc car port and safety model for the vehicle | Road environment, other road users |
| OTA update client (`system/updated`) | comma.ai and LionDriver servers (update source) |

The System FMEA structure (SFM-SE-001…034) and the FSC elements (EL-01…EL-12) refine this boundary for AC-001.

### Function allocation

| Function | Hardware | Software | Mechanical / external actuator |
|---|---|---|---|
| F1 | comma 3X SoC, panda MCU, harness | modeld, locationd, controlsd (lateral controller), card, panda safety model | Vehicle EPS |
| F2 | comma 3X SoC, panda MCU, harness | modeld, plannerd, radard, controlsd (longitudinal controller), card, panda safety model | Vehicle powertrain and brakes |
| F3 | comma 3X SoC, panda MCU | selfdrived state machine, card (cruise state), panda controls-allowed | Vehicle cruise switches |
| F4 | comma 3X SoC, panda MCU | card, car_events, selfdrived, panda brake/cruise checks | Brake and accelerator pedals, steering wheel |
| F5 | comma 3X driver camera and IR | dmonitoringmodeld, dmonitoringd | — |
| F6 | comma 3X display and speaker | selfdrived alert manager, ui, soundd | Vehicle cluster (indications from item messages) |
| F7 | panda MCU (primary), comma 3X SoC | panda safety model (opendbc), controlsd limits, excessive-actuation check | — |
| F8 | Harness relay, panda MCU | panda relay control, relay-malfunction detection | Stock ADAS camera |

## A.4 Interfaces

| ID | Interface | Counterpart | Direction | Data | Integrity measures (BL-001) | Varies by vehicle |
|---|---|---|---|---|---|---|
| IF-01 | Vehicle CAN at the ADAS camera or gateway | Vehicle ECUs (EPS, powertrain, brakes, ADAS, cluster) | in/out | Vehicle state in; steering, acceleration, cruise and HUD requests out | Panda safety model filters TX; panda RX checks (checksum, counter, timing); SoC canValid/canError | Bus layout, messages, harness location, message authentication |
| IF-02 | Harness relay | Stock ADAS camera | out | Switches the stock camera's control messages between vehicle and item | Panda relay-malfunction detection | Present only on camera-intercept harnesses |
| IF-03 | 12 V supply | Vehicle electrical system | in | Power | Device power management; loss of power is fail-silent (DFA DFI-01) | Connector |
| IF-04 | Driver HMI (device) | Driver | in/out | Engagement state, alerts; settings | Two-channel alerts (visual, audible) | — |
| IF-05 | Driver controls | Driver via vehicle (pedals, wheel, cruise buttons) | in | Brake, accelerator, steering torque, cruise/cancel buttons | Read over IF-01 by both SoC and panda | Button mapping |
| IF-06 | Device sensors | Road environment, driver | in | Road and driver camera frames, IMU, GNSS | Liveness and frequency checks (cameraMalfunction, sensorDataInvalid) | Mounting, calibration |
| IF-07 | Cellular / Wi-Fi | comma.ai and LionDriver servers | in/out | OTA updates, logs | Update verification per release process (PFMEA; DFA DFI-18) | — |

## A.5 Operating modes

The same modes apply to every vehicle. The FSC (OM-01…OM-08) allocates them.

| ID | Mode | Entry | Exit | Safety relevant |
|---|---|---|---|---|
| OM-01 | Off / offroad | Ignition off or not onroad | Ignition on and onroad | No: panda in NO_OUTPUT, relay to stock |
| OM-02 | Start-up | Ignition on | Vehicle identified and safety model confirmed by the panda | Yes: wrong vehicle configuration (FSR-009) |
| OM-03 | Disabled (onroad) | Start-up complete; or any disengagement | Driver engages with no NO_ENTRY event | Yes: unintended engagement (SG-008) |
| OM-04 | Engaged | Driver engagement through the vehicle cruise controls | Brake, cancel, or a SOFT_DISABLE / IMMEDIATE_DISABLE event | Yes: all actuation hazards |
| OM-05 | Overriding | Driver steering or accelerator input while engaged | Driver input ends; or disengagement | Yes: override handling (SG-007) |
| OM-06 | Soft disabling | SOFT_DISABLE event while engaged | Event clears (back to engaged) or 3 s elapse (disabled) | Yes: actuation continues for up to 3 s |
| OM-07 | Driver-monitoring lockout | Repeated non-response to alerts | Lockout time (1/5/15/30 min) or ignition cycle | Yes: SG-010 |
| OM-08 | Dashcam (car unrecognized) | Vehicle not identified | Never during the drive | No: no actuation |

## A.6 Operating conditions and performance limits

| ID | Limit (platform, BL-001) | Source |
|---|---|---|
| PF-01 | Commanded lateral acceleration ≤ 3.0 m/s² plus roll compensation (ISO 11270 basis) | `openpilot/selfdrive/controls/lib/drive_helpers.py:14`; opendbc `car/lateral.py:10` |
| PF-02 | Lateral jerk ≤ 5.0 m/s³ (ISO 11270); angle/curvature ports limited to ~3.6 m/s³ | opendbc `car/lateral.py:11-18` |
| PF-03 | Commanded longitudinal acceleration within −3.5 … +2.0 m/s² (platform); VF-001 SoC also uses +2.0 m/s² (`RAISED_ACCEL_LIMIT`, set for every TSS2 car) | opendbc `car/interfaces.py:25-26`; `car/toyota/values.py:39-43` |
| PF-04 | Excessive actuation (> 2× the above for 0.25 s) leads to soft disable | `openpilot/selfdrive/selfdrived/helpers.py` |
| PF-05 | Soft-disable takeover window 3 s | `openpilot/selfdrive/selfdrived/state.py` |
| PF-06 | Driver-monitoring escalation within 5 / 8 / 13 s (vision policy) | `openpilot/selfdrive/monitoring/policy.py` |

- **Roads:** public roads of any type. The item does not geofence; per-vehicle speed floors are listed in the catalog.
- **Driver:** licensed, attentive, able to take over at any time (L2).
- **Environment:** no restriction is enforced by the item beyond what the vehicle's own ACC/LKA imposes. Weather and lighting are covered in the HARA situations (OS-013…015).

## A.7 Assumptions

| ID | Category | Assumption |
|---|---|---|
| VA-01 | Vehicle | The vehicle has factory ACC and lane-keeping hardware with actuators that accept external requests |
| VA-02 | Vehicle | Vehicle CAN messages used by the item are not cryptographically authenticated. Vehicles that need SecOC are dashcam-only in release builds (`opendbc/car/toyota/interface.py:34-37`) |
| VA-03 | Vehicle | Vehicle ECUs behave as stock. The item does not modify ECU firmware, except that some ports disable stock radar/camera functions over diagnostics (port-specific, §A.10) |
| VA-04 | Vehicle | The vehicle's own brake and steering systems remain fully functional with the item installed |
| DA-01 | Driver | A licensed driver supervises at all times and can take over immediately (SAE L2); foreseeable inattention is assumed (HARA HA-001) |
| DA-02 | Driver | The driver has read the limitations (`docs/LIMITATIONS.md`) and engages the item only through the vehicle's cruise controls |
| MA-01 | Market | Vehicles are used in the market listed for them in the catalog. AC-001 is US only; other markets need a legal and exposure review (§A.8, P11) |
| LA-01 | Lifecycle | The owner installs the device and harness following the install instructions; installation errors are handled in the PFMEA |
| LA-02 | Lifecycle | Software reaches the device only through the LionDriver release and OTA process; each release is a new baseline (`baseline.yaml`) |
| LA-03 | Lifecycle | Vehicle service that changes ADAS hardware or ECU firmware (e.g. camera replacement, EPS reflash) invalidates the assured configuration until re-checked |

## A.8 Legal requirements and standards

| Item | Relevance |
|---|---|
| FMVSS (US) | No L2-specific standard; the installation must not compromise compliance of the vehicle's systems |
| NHTSA Standing General Order 2021-01 (L2 ADAS crash reporting) | Applicability to an open-source, owner-installed system to be assessed (IOI-005) |
| UN R79, UN R171 (non-US markets) | Steering and driver-control-assistance requirements where the vehicle is used outside the US |
| SAE J3016 | Level 2 classification |
| ISO 11270, ISO 15622, ISO 22179 | Lane-keeping, ACC and full-speed-range ACC performance references (SAFETY.md lateral limit basis) |
| ISO 26262, ISO 21448, ISO/SAE 21434, ISO/PAS 8800 | Project standards (README) |

## A.9 Known hazards and experience from similar items

- Upstream openpilot fleet experience exists but is not credited (HARA HA-005). Using it needs evidence for identical code and vehicle configuration.
- HARA LD-HARA-001 identifies 13 vehicle-level hazards for AC-001. They are expected to apply to every vehicle with the same functions; their ratings are not.

## A.10 Variant-sensitive parameters

Each must be established for a vehicle before its variant family or assured configuration can be assessed. The values for VF-001 are in §B.4.

| # | Parameter | Why it matters | Affects |
|---|---|---|---|
| P1 | opendbc platform and safety model / parameter | Defines the panda's limits and checks | FSC panda FSRs, LD-DES-001 vehicle lock record |
| P2 | Steering interface (torque, angle, curvature) and limits | Actuator authority; HARA controllability for HZ-001/002 | SG-001, SG-002 |
| P3 | Longitudinal mode (openpilot or stock) and acceleration limits | Whether F2 commands acceleration at all | SG-004, SG-005, SG-006 |
| P4 | Harness type and interception point | Relay presence; effect on stock functions | SG-009, DFA DFI-17 |
| P5 | Stock safety functions retained (AEB, FCW, lane assist) | HZ-011 | SG-009, OI-003 |
| P6 | Minimum engage speeds | Operating conditions | HARA situations |
| P7 | Vehicle mass, wheelbase, steering ratio | Lateral and longitudinal dynamics; FTTI | OI-004 |
| P8 | EPS and powertrain behavior on item requests and message loss | External measures XM-02, XM-05; DFA DM-03 | OI-001, OI-002 |
| P9 | Message authentication (SecOC) | VA-02 | Platform eligibility |
| P10 | Diagnostic actions by the port (e.g. disabling a stock ECU) | DFA DFI-08 | SG-009 |
| P11 | Market and legal context | §A.8 | HARA exposure |

---

# Part B — Variant Family VF-001: Toyota Corolla E210

## B.1 Description

The Toyota Corolla E210 is the twelfth generation of the Corolla, a compact (C-segment) car made by Toyota. It was introduced in 2018, and besides the saloon (sedan) it includes hatchback and estate (station wagon, "Touring Sports") body styles. It is built on Toyota's TNGA-C platform and, in the supported model years, carries Toyota Safety Sense 2.0 (TSS2), the camera-based ADAS that LionDriver's harness intercepts.

## B.2 Members

From the BL-001 catalog; all are on opendbc platform `TOYOTA_COROLLA_TSS2`.

| Member | Body / powertrain | Market | Longitudinal | No ACC accel / no ALC below | Harness |
|---|---|---|---|---|---|
| Toyota Corolla 2020-22 | Sedan, gasoline | US | openpilot | 0 mph / 0 mph | Toyota A |
| Toyota Corolla Hatchback 2019-22 | Hatchback, gasoline | US | openpilot | 0 mph / 0 mph | Toyota A |
| Toyota Corolla Hybrid 2020-22 | Sedan, hybrid | US | openpilot | 0 mph / 0 mph | Toyota A |
| Toyota Corolla Hybrid (South America only) 2020-23 | Sedan, hybrid | South America | openpilot | 17 mph / 0 mph | Toyota A |

## B.3 Outside the family

| Vehicle | Reason |
|---|---|
| E210 estate (Touring Sports) | Not in the BL-001 supported list |
| E210 2023+ model years (US facelift) | Not in the BL-001 supported list |
| E210 for markets not listed above | Not in the BL-001 supported list |
| Toyota Corolla 2017-19 | Previous generation (E170) |
| Corolla Cross, Corolla Cross Hybrid (non-US), Lexus UX Hybrid | Different models, but on the **same opendbc platform** as VF-001: they share its safety model, parameter, limits and vehicle specs. A change made for VF-001 changes these vehicles too (IOI-003). |

## B.4 Variant-sensitive parameters for VF-001 (BL-001 values)

| # | Value | Source (opendbc `229dc70` unless stated) |
|---|---|---|
| P1 | `SAFETY_TOYOTA`, safety parameter **73** (EPS scale; no ALT_BRAKE, LTA, SECOC or STOCK_LONGITUDINAL flags) | `car/toyota/interface.py:27-41,105-111`; `values.py:109-112,588` |
| P2 | Torque steering. Panda: max torque 1500, rate up 15 / down 25 per frame, max torque error 350. SoC controller: the same values. | `safety/modes/toyota.h:172-177`; `car/toyota/values.py:20-50` |
| P3 | openpilot longitudinal (TSS2, no radar-ACC flag). SoC accel limits +2.0 / −3.5 m/s² (`RAISED_ACCEL_LIMIT`, TSS2); panda +2.0 / −3.5 m/s². | `interface.py:105, 117-118`; `values.py:39-43`; `toyota.h:207-210` |
| P4 | Toyota A camera-intercept harness with relay | `docs/CARS.md` |
| P5 | **Unknown** which stock TSS2 functions remain with openpilot longitudinal | HARA OI-003 |
| P6 | 0 mph engage (US members); 17 mph ACC floor for the South America hybrid (`min_enable_speed=7.5` m/s) | `values.py:201-211` |
| P7 | One spec for the whole platform: mass 3060 lb, wheelbase 2.67 m, steer ratio 13.9 | `values.py:212` |
| P8 | Not characterized | HARA OI-001, OI-002 |
| P9 | No SecOC | `values.py:109-112` |
| P10 | To be confirmed for TSS2 Corolla | — |
| P11 | US (three members), South America (one member) | `docs/CARS.md` |

The identical panda and SoC steering limits under P2 are concrete evidence for DFA DFI-14 (one shared specification).

## B.5 Differences within the family relevant to safety

| Difference | Members | Consequence |
|---|---|---|
| Hybrid powertrain (regenerative braking, different brake/accelerator feel) | Corolla Hybrid (US, South America) | P3/P8 may differ; brake-signal behavior to confirm (the parameter selects no ALT_BRAKE) |
| Body style and mass | Hatchback versus sedan | P7 uses one platform-wide spec; real mass differs per body and powertrain |
| Market | South America hybrid | Different engage speed floor and legal context; HARA exposure not rated for that market |
| Model year | Hatchback from MY2019; sedan and US hybrid MY2020-22 | Firmware and fingerprint differences within the family |

---

# Part C — Assured Configuration AC-001

| | |
|---|---|
| **Vehicle** | 2020 Toyota Corolla LE, sedan, gasoline, US market (VF-001 member "Toyota Corolla 2020-22") |
| **Device** | comma 3X with integrated panda |
| **Harness** | Toyota A connector, harness box, comma power v3 |
| **Software** | BL-001 (`baseline.yaml`) |
| **Configuration** | Experimental Mode on (BL-001 default); openpilot longitudinal; safety model `SAFETY_TOYOTA`, parameter 73 |
| **Analyses** | System FMEA rev 0.4, HARA rev 0.3, FSC rev 0.2, DFA rev 0.3 |

---

## Open items

| ID | Item | Affects |
|---|---|---|
| IOI-001 | Experimental Mode is on by default in BL-001, so F2 includes model-driven stopping for lights and stop signs. Confirm the HARA situations and the SOTIF analysis cover it explicitly, or set AC-001 to Chill Mode. | HARA, SOTIF, AC-001 configuration |
| IOI-002 | Variant impact analysis for the other VF-001 members (hatchback, US hybrid, South America hybrid) against §A.10, starting with P3, P5, P7 and P8. | VF-001 |
| IOI-003 | Changes to `TOYOTA_COROLLA_TSS2` (including LD-DES-001 vehicle lock records) also change the Corolla Cross and Lexus UX Hybrid. Decide whether LionDriver splits them into their own platform or carries them along as not assessed. | VF-001, LD-DES-001 |
| IOI-004 | Platform-level HARA approach: confirm that the 13 hazards hold for all vehicles, and define how variant ratings are derived (P2, P3, P5, P7, P8 drive S/E/C). | PL-001 |
| IOI-005 | Assess NHTSA Standing General Order 2021-01 and other reporting obligations for an owner-installed open-source L2 system. | §A.8 |
| IOI-006 | Item-definition review and confirmation (ISO 26262-2). | LD-ITEM-001 |
