# WP-S-06 Requirements for Production, Operation, Service and Decommissioning

| Field | Value |
|---|---|
| Work product | WP-S-06 Requirements for production, operation, service and decommissioning |
| Standard reference | ISO 26262-4:2018 §6 (specification of requirements for production, operation, service and decommissioning); ISO 26262-7:2018 §5–§6 (by reference); ISO 21448:2022 §13 (operation phase); ISO/SAE 21434:2021 §10, §12, §14 (production, operations, end of support, by reference); ASPICE 4.0 SYS.2 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Up to ASIL D (SG-01, until re-rated under FSC option (c); B‡ per [WP-S-02 §2.1](WP-S-02-technical-safety-requirements.md)); SOTIF; CS overlaps |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and tailoring

ISO 26262-4 §6 asks the system design to state what production, operation, service and decommissioning must do so that the safety concept holds in the field. Under tailoring **T-07** ([WP-M-01 §5](../01-management/WP-M-01-assurance-strategy.md)) LionDriver does not manufacture hardware; "production" means **installation, provisioning and configuration** of a COTS device and harness in a reference vehicle. comma.ai's manufacturing is a supplier matter ([WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md), [WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md)).

This document specifies TSR-801…TSR-818 in full. They are listed in summary in [WP-S-02 §10](WP-S-02-technical-safety-requirements.md). The procedures that implement them are:

| Procedure | Work product |
|---|---|
| Installation, provisioning, configuration check (INS-01…INS-30, SPC-01…SPC-09) | [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) |
| Operation, vehicle service, item service, update policy, decommissioning (OPS, SVC, PM, ITS, UPD, DEC) | [WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) |
| User information and warnings (UI-nn, SD-nn) | [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md) |
| Field monitoring | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |
| Cybersecurity incident response and updates | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |

This closes WP-O-01 OI-1 and WP-O-02 OI-1 at specification level.

## 2. Why these requirements are safety-relevant

The technical safety concept depends on facts that only installation and operation can establish or preserve:

| Concept dependency | Established/preserved by | Concept element |
|---|---|---|
| The envelope runs the release firmware with the reference mode and parameter | provisioning checks | TSR-511…514; until TSR-512 is implemented this is the **only** control of the safety-mode configuration (GAP-09) |
| The vehicle is the one whose EPS/PCM behaviour was characterised | ECU firmware identity | AOU-01R…05R; TSR-102 table, TSR-111, 208, 310, 708 |
| The harness is intact and the relay works in both directions | installation and periodic test | TSR-506, 701…706 (no readback today, GAP-12, GAP-43) |
| The camera is mounted and calibrated within the range the model was validated in | installation and service | AOU-08; SOTIF |
| The driver is briefed and attentive | user information | AOU-06; controllability ratings |
| Debug paths are absent | parameter set, build type | TSR-514, 610, 613 |

## 3. Requirements

Attributes as in [WP-S-02 §2](WP-S-02-technical-safety-requirements.md). "Special characteristic" (SC) refers to SPC-nn in WP-O-01 §4.

### 3.1 Installation and provisioning ("production")

| ID | Requirement | ASIL | Parent | Implemented by | Verification / record | Status at baseline |
|---|---|---|---|---|---|---|
| TSR-801 | Only a released LionDriver baseline shall be installed: the installed openpilot commit, AGNOS version and model artefact hashes shall equal the release record, and the build shall not be dirty. | B‡ | SG-01…07; T-03 | INS-15, INS-16, INS-18; SPC-04 | R-SW record, second-person check | Procedure defined; release channel not yet defined (WP-O-01 OI-6) |
| TSR-802 | The panda firmware shall be the release-signed, non-debug build recorded in the release record; its version string and signature shall be compared before first engagement. | B‡ | FSR-01.10; TSR-511, 514 | INS-17; SPC-05 | R-SW | Blocked in substance by GAP-24/25 (no LionDriver key, debug build default) |
| TSR-803 | Every vehicle ECU firmware version (engine, EPS, ABS, radar, camera) shall equal the reference record before engagement; a mismatch shall put the item in dashcam mode until an impact analysis extends the scope. | B‡ | AOU-01…05; WP-M-12 | INS-21; SPC-07; WP-O-01 §6 | R-CFG raw FW query output | Procedure defined |
| TSR-804 | The installed configuration shall show fingerprint `TOYOTA_COROLLA_TSS2` (exact, not fuzzy), safety model `toyota`, safety parameter 73, alternative experience 0, openpilot longitudinal on, both in `carParams` and in `pandaStates`. | B‡ | FSR-01.10; TSR-512 | INS-22, INS-23, INS-24; SPC-06 | R-CFG | Procedure defined. Needed because the panda accepts any mode from the SoC (GAP-09) |
| TSR-805 | Harness seating and the relay intercept/PCS-forwarding function shall be verified at installation: no relay malfunction or CAN errors, intercepted messages absent on the car side, PCS-relevant camera messages present on the car side with LD-SDA disengaged. | B | FSR-07.01, 07.03; TSR-704, 706 | INS-11, INS-13, INS-14, INS-27; SPC-01, SPC-02 | R-INS, R-FUN | Procedure defined; message list pending (WP-O-01 OI-7) |
| TSR-806 | The parameter set shall equal the release record: Experimental Mode per D-08, `DisengageOnAccelerator` per WP-C-08, debug/maneuver/joystick modes absent, DM demo mode off, SSH off. | QM (B-sup) | FSR-02.08; TSR-610, 613 | INS-19; SPC-09 | R-SW parameter dump | Procedure defined |
| TSR-807 | The device shall be mounted within the position tolerance and calibrated within the angle tolerance band derived from the model validation range. | QM (SOTIF) | AOU-08 | INS-09, INS-10, INS-25, INS-26; SPC-03 | R-CAL | Tolerance band TBD (WP-O-01 OI-2) |
| TSR-815 | Only devices and harnesses of the approved hardware revision, with clean history, shall be installed; units returned after a field event or decommissioned from another vehicle shall pass refurbishment inspection first. | B‡ | T-04; WP-H-07 | INS-01…INS-04; ITS-03…ITS-05 | R-DEV | Procedure defined; approved revision TBD (WP-C-01 OI-2) |
| TSR-816 | Installation shall be done by a trained installer, and the installation record (R-DEV…R-USR) shall be complete and second-person checked before the first engagement and retained per WP-P-04. | B‡ | ISO 26262-7 §5 (by ref.) | WP-O-01 §5; WP-M-04 | Record review | Template pending (WP-O-01 OI-3) |

### 3.2 Operation

| ID | Requirement | ASIL | Parent | Implemented by | Verification / record | Status at baseline |
|---|---|---|---|---|---|---|
| TSR-811 | Before every drive the driver shall perform the pre-drive checks and shall not engage if a check fails (vehicle warning lamps, VSC on, clean camera area, device seated, DM camera unobstructed, no offroad alert, driver fit). | QM (B-sup) | AOU-06, 08, 09, 10 | OPS-01…OPS-07; WP-O-03 §5 | Briefing acknowledgement | Defined. WP-O-02 OI-2: consider system-side DTC checks |
| TSR-812 | Each driver shall receive the user information and safety warnings before first use and acknowledge them; in the development phase only approved safety drivers shall operate the item. | QM (B-sup) | AOU-06, AOU-07 | WP-O-03 Part A/B; INS-30 | R-USR | Defined |
| TSR-813 | Field monitoring shall collect and analyse drive logs and driver reports of every installed item, including every disengagement caused by a safety mechanism (`controlsMismatch`, `relayMalfunction`, RX invalid, heartbeat lost, `safetyTxBlocked` > 0), and feed problem resolution and the safety case. | QM | SG-01…07; ISO 21448 §13 | OPS-11, OPS-12; WP-O-04; WP-P-03 | Monitoring reports | WP-O-04 pending |

### 3.3 Service (maintenance and repair)

| ID | Requirement | ASIL | Parent | Implemented by | Verification / record | Status at baseline |
|---|---|---|---|---|---|---|
| TSR-808 | Vehicle service actions that can invalidate an AoU or the calibration (alignment/steering/suspension, EPS or ECM/ABS replacement or reflash, windscreen, camera or radar work, tyre size, brake repair, collision repair, battery disconnection, scan-tool sessions, aftermarket accessories) shall trigger the re-verification defined for that action before the item is engaged again. | B‡ | AOU-01…05, 08, 09 | SVC-01…SVC-11 | R-CAL / R-CFG / R-FUN as listed | Defined; Toyota service information pending (WP-O-02 OI-6) |
| TSR-809 | The reference-configuration check (INS-21…INS-23), PCS-preservation check (INS-27) and harness inspection shall be repeated at least every 6 months and after any service trigger; harness and camera windows inspected monthly. | B | SG-07; AOU-09; latent faults of TSR-506 | PM-01…PM-04 | Maintenance log | Defined. The 6-month interval is also the latent-fault interval for relay stuck-intercepting until TSR-506 readback and TSR-515 start-up test exist (GAP-43) |
| TSR-817 | Item faults shall be handled by replacement, not repair: defective devices or harnesses shall be quarantined, reported and returned; after replacement the full provisioning and configuration steps shall be repeated. | B‡ | T-04 | ITS-01…ITS-05 | Problem report (WP-P-03) | Defined |

### 3.4 Software updates

| ID | Requirement | ASIL | Parent | Implemented by | Verification / record | Status at baseline |
|---|---|---|---|---|---|---|
| TSR-810 | Only released baselines shall be installed by update; until signed updates exist, automatic updates shall be disabled and updates installed manually, followed by INS-15…INS-23; model-weight changes require SOTIF re-evaluation; envelope changes require the envelope verification evidence; parameters shall be re-checked after each update; a withdrawn release shall be replaced or the item put in dashcam mode. | B‡ | FSR-01.10; D-02, D-05; GAP-26 | UPD-01…UPD-08; WP-O-05 | Release record (WP-K-06) | Defined |

### 3.5 Decommissioning and end of support

| ID | Requirement | ASIL | Parent | Implemented by | Verification / record | Status at baseline |
|---|---|---|---|---|---|---|
| TSR-814 | On removal of the item the stock camera connection shall be restored and stock TSS functions (LTA/LDA, DRCC, PCS) and the absence of DTCs verified; logs needed for field monitoring retrieved; device data, credentials and identity keys wiped or the device kept under LionDriver control with its history recorded. | B (stock path); CS (data) | SG-07; ISO/SAE 21434 §14 (by ref.) | DEC-01…DEC-11 | Decommissioning record | Defined; key-wipe tool pending (WP-O-02 OI-5) |
| TSR-818 | At end of support of a release, every user shall be informed with the date after which the release must not be engaged. | QM | ISO/SAE 21434 §14 (by ref.) | WP-O-02 §7.3; WP-O-05 | Notification record | Defined |

## 4. Requirements on the design that support production and operation

These are design-side requirements that make the TSR-8xx checks possible or replace them by system measures. They are already TSRs in WP-S-02; listed here for completeness.

| Need | Design TSR | Status |
|---|---|---|
| Firmware build type and identity readable for INS-17 | TSR-514 (version shows build type) | Not met (GAP-25) |
| Safety mode/param fixed in firmware so INS-22/23 become a confirmation, not the only control | TSR-512 | Not met (GAP-09) |
| Relay checked at every power-up so PM-03 is not the latent-fault interval | TSR-506, TSR-515 | Not met (GAP-12, GAP-43) |
| Configuration extraction from the installation log | WP-O-01 OI-5 script | Not started |
| Logs identify software, firmware and model versions | SYS-141; AIR-23 | Partial |

## 5. Traceability

| TSR | Parent | Procedure steps |
|---|---|---|
| TSR-801 | SG-01…07 | INS-15, INS-16, INS-18 |
| TSR-802 | FSR-01.10 | INS-17 |
| TSR-803 | AOU-01…05 | INS-21; SVC-02, SVC-03, SVC-05 |
| TSR-804 | FSR-01.10 | INS-22…INS-24 |
| TSR-805 | FSR-07.01, 07.03 | INS-11, INS-13, INS-14, INS-27 |
| TSR-806 | FSR-02.08 | INS-19; UPD-06 |
| TSR-807 | AOU-08 | INS-09, INS-10, INS-25, INS-26 |
| TSR-808 | AOU-01…05, 08, 09 | SVC-01…SVC-11 |
| TSR-809 | SG-07, AOU-09 | PM-01…PM-04 |
| TSR-810 | FSR-01.10 | UPD-01…UPD-08 |
| TSR-811 | AOU-06, 08, 09, 10 | OPS-01…OPS-07 |
| TSR-812 | AOU-06, 07 | WP-O-03; INS-30 |
| TSR-813 | SG-01…07 | OPS-11, OPS-12; WP-O-04 |
| TSR-814 | SG-07 | DEC-01…DEC-11 |
| TSR-815 | T-04 | INS-01…INS-04; ITS-03…ITS-05 |
| TSR-816 | 26262-7 §5 | WP-O-01 §5 |
| TSR-817 | T-04 | ITS-01…ITS-05 |
| TSR-818 | 21434 §14 | WP-O-02 §7.3 |

## 6. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Define the LionDriver release channel, key and build pipeline so TSR-801/802 can be met in substance (with WP-S-07) | Maintainer | G3 |
| OI-2 | Set the latent-fault interval assumption for the relay (PM-03, 6 months) in WP-H-04 and replace it by TSR-515 start-up tests once implemented | Safety engineer | G3 |
| OI-3 | Add a WP-O-01/WP-O-02 cross-reference column for TSR-8xx IDs (owner of those WPs) | Maintainer | G2 |
| OI-4 | Decide on system-side checks that can replace manual pre-drive checks (WP-O-02 OI-2), e.g. blocking engagement on EPS/VSC DTC status | Safety engineer | G2 |
