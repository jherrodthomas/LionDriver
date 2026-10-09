# WP-O-02 Operation, Service and Decommissioning

| Field | Value |
|---|---|
| Work product | WP-O-02 Operation, service (maintenance, repair) and decommissioning |
| Standard reference | ISO 26262-7:2018 §6 (operation, service and decommissioning: planning, instructions, records); ISO 26262-4:2018 §6 (requirements for operation and service, by reference to WP-S-06); ISO/SAE 21434:2021 §14 (end of cybersecurity support and decommissioning) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Up to ASIL C (actions that restore or preserve SG-01…SG-07 preconditions); SOTIF; CS |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document says what has to happen during the life of an installed LD-SDA so that the conditions the safety case relies on stay true:

- **Operation**: checks before and during driving (§3).
- **Vehicle maintenance and repair** that can invalidate an assumption of use (AoU) or the calibration, and what must follow it (§4).
- **Service of the item**: device, harness and firmware faults, replacement (§5).
- **Software updates** (§6), with the policy owned by [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md) and decision D-05.
- **Decommissioning**: removing the item, restoring the stock vehicle, and wiping data and keys (§7).

It applies to the reference configuration only ([WP-M-01 §3.1](../01-management/WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to)). The derived requirements belong in the TSR-8xx block of [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md), which does not exist yet (OI-1). The user-facing wording of the operating instructions is in [WP-O-03](WP-O-03-user-information-safety-warnings.md).

## 2. Assumptions this document protects

| AoU ([WP-C-01 §7](../02-concept/WP-C-01-item-definition.md)) | Threat during the life of the vehicle | Section |
|---|---|---|
| AOU-01, AOU-02 (EPS limits LKA torque; driver can overpower) | EPS replacement, EPS software reflash by a dealer, steering rack repair | §4 |
| AOU-03 (brake overrides; PCM cancels ACC on brake) | Brake system repair, ECM/PCM reflash | §4 |
| AOU-04 (stock PCS keeps full function) | Windscreen or forward-camera replacement, radar replacement, harness damage | §4, §5 |
| AOU-05 (PCM bounds ACC requests) | ECM/PCM reflash | §4 |
| AOU-06 (attentive, briefed driver) | New or occasional driver; DM camera obstructed | §3 |
| AOU-08 (device mounted and calibrated) | Device knocked, remounted, windscreen replaced | §3, §4 |
| AOU-09 (vehicle maintained, unmodified, no active DTCs) | Wear, modifications, DTCs | §3, §4 |
| AOU-10 (VSC/ABS on and working) | VSC switched off, ABS fault | §3 |
| AOU-11 (no safety function depends on the back end) | Update or remote-access configuration changes | §6 |

## 3. Operation

### 3.1 Pre-drive checks (every drive)

The driver performs these. The ones the item can check itself are noted; the others depend on the driver and are in the user information ([WP-O-03](WP-O-03-user-information-safety-warnings.md) §5).

| ID | Check | Automatic support at baseline | Action if not met |
|---|---|---|---|
| OPS-01 | No vehicle warning lamps for EPS, brake, ABS/VSC, engine, PCS/TSS | Partial: the item raises events for some car faults (`openpilot/selfdrive/car/car_events.py:116-180` ESP disabled, steering faults; `openpilot/selfdrive/selfdrived/events.py`). Not all DTCs are visible to it | Do not engage. Get the vehicle checked (AOU-09/10) |
| OPS-02 | VSC is on (not switched off with the VSC OFF button) | Yes: `espDisabled` event (`openpilot/selfdrive/car/car_events.py:116-117`) | Turn VSC on |
| OPS-03 | Windscreen area in front of both cameras is clean and clear of ice, stickers or objects | Partial: camera health and model checks; no specific obstruction detector | Clean before driving |
| OPS-04 | Device is firmly in its mount, not tilted; display shows no calibration alert | Yes: `calibrationInvalid` / `calibrationRecalibrating` events (`events.py:816-832`), engagement blocked until `calibrated` (`selfdrived.py:275-286`) | Re-seat; if remounted, follow §4.2 |
| OPS-05 | Driver-facing camera can see the driver's face; no hat brim, mask or object in the way | Partial: DM falls back to wheel-touch timers on model uncertainty (`selfdrive/monitoring/policy.py:77-78, 307-308`) | Remove obstruction |
| OPS-06 | No offroad alerts on the device home screen (for example `Offroad_ExcessiveActuation`, `Offroad_Recalibration`, update failure) | Yes: offroad alerts | Follow §3.3 |
| OPS-07 | The driver is briefed and fit to drive (licensed, not impaired, not fatigued) | No | Do not use the item |

### 3.2 During operation

The driver supervises at all times. Operating rules for the driver (ODD, when to take over, prohibited use) are in [WP-O-03](WP-O-03-user-information-safety-warnings.md). Operation-specific rules for the operator of the vehicle:

| ID | Rule |
|---|---|
| OPS-08 | Use only within the ODD defined in [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) |
| OPS-09 | Do not change parameters that the release record fixes (Experimental Mode, debug modes, driver-view demo, SSH) unless a released configuration allows it ([WP-O-01](WP-O-01-installation-and-provisioning-control.md) INS-19) |
| OPS-10 | Do not run developer tools on the device while onroad (`tools/scripts/*`, joystick, maneuver modes, `set_car_params.py`) |
| OPS-11 | Keep the drive logs (do not delete routes) until the field-monitoring data retrieval for that period is done ([WP-O-04](WP-O-04-field-monitoring.md)) |
| OPS-12 | Use the bookmark (flag) button on the device after any event that felt unsafe; this preserves the segment (`userBookmark` → `user.preserve` attribute, `system/loggerd/loggerd.cc:198-285`, `system/loggerd/deleter.py:16-43`) and report it per [WP-O-04](WP-O-04-field-monitoring.md) |

### 3.3 Latched faults and offroad alerts

| Indication | Meaning | Action |
|---|---|---|
| `Offroad_ExcessiveActuation` (latched by `selfdrived.py:305-310`; criteria in `selfdrive/selfdrived/helpers.py`) | The item measured longitudinal or lateral acceleration beyond twice the design limits while engaged | Stop use. Report as a potential safety goal violation (S-1 in [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)). The alert must be cleared only by the maintainer after analysis |
| `relayMalfunction` (permanent alert "Harness Relay Malfunction") | Intercepted messages seen on the car side; all TX blocked by the panda | Stop use. Service the harness (§5) |
| `canBusMissing`, `canError` | CAN not received or wrong rates; often wiring | Check harness connectors (§5). Note the text "Unknown Vehicle Variant" for `canError` is misleading (GAP-19) |
| `controlsMismatch` | Panda safety state differs from the host's expectation | Stop use; report (S-1 or S-2) |
| `Offroad_ConnectivityNeeded` | The updater could not check for updates for > 27 h onroad and > 84 routes (`system/updated/updated.py:34-37, 336-341`); engagement is then blocked | Connect to the network so the update check completes against the LionDriver update origin (§6) |
| DM lockout (`tooDistracted`) | Repeated non-compliance; engagement blocked 1–30 min (`policy.py:42-44`) | Drive manually. Repeated lockouts are recorded in field monitoring |

## 4. Vehicle maintenance and repair that affect the item

### 4.1 Trigger list

Any of the following events on the vehicle requires the follow-up in the right-hand columns before LD-SDA is engaged again. The driver or owner must tell the maintainer (development phase) or follow the instructions in [WP-O-03](WP-O-03-user-information-safety-warnings.md) (after release).

| ID | Vehicle event | Affected AoU / SG | Required follow-up | Records |
|---|---|---|---|---|
| SVC-01 | Wheel alignment, steering rack, tie-rod, suspension or ride-height work | AOU-09; SOTIF (lateral bias) | Reset calibration and recalibrate (WP-O-01 INS-25); straight-road drive check that lane centring has no bias | R-CAL |
| SVC-02 | EPS replacement or EPS software update by a dealer | AOU-01, AOU-02; SG-01, SG-05 | Re-run the reference-configuration check (WP-O-01 INS-21/22). A new EPS FW version puts the vehicle outside the reference configuration: no engagement until the EPS characterization ([WP-C-01](../02-concept/WP-C-01-item-definition.md) AOU-01/02 verification) is repeated or an impact analysis accepts it | R-CFG |
| SVC-03 | ECM/PCM or ABS/VSC software update, or replacement | AOU-03, AOU-05, AOU-10; SG-03, SG-04, SG-05 | As SVC-02 for the affected ECU (AOU-03/05 verification) | R-CFG |
| SVC-04 | Windscreen replacement | AOU-04, AOU-08; SG-07 | Stock forward-camera recalibration by the repairer per Toyota procedure; device remount (WP-O-01 INS-09/10); LD-SDA calibration reset and recalibration (INS-25); PCS-preservation check (INS-27) | R-INS, R-CAL, R-FUN |
| SVC-05 | Forward camera or radar replacement, or their recalibration | AOU-04; SG-07; FW identity | INS-21 (FW versions), INS-27; stock camera aiming per Toyota procedure first | R-CFG, R-FUN |
| SVC-06 | Tyre change to a different size, or mixed tyres | AOU-09; SOTIF (speed, curvature estimation) | Only OEM sizes allowed. Recalibrate; check `paramsd` converges (steer ratio, stiffness) over a drive | R-CAL |
| SVC-07 | Brake repair (pads, discs, hydraulics, booster) | AOU-03 | Brake function test by the repairer; no LD-SDA-specific test unless the brake module or its CAN messages changed (then INS-21) | R-VEH |
| SVC-08 | Collision repair, or airbag deployment | All | Treat as reinstallation: full WP-O-01 procedure after repair; field-monitoring report if LD-SDA was engaged in the collision ([WP-O-04](WP-O-04-field-monitoring.md)) | Full installation record |
| SVC-09 | 12 V battery disconnection or replacement | Fingerprint cache, calibration persistence | Check that calibration and fingerprint are still valid (no `calibrationIncomplete`; INS-22 values unchanged) | R-CFG |
| SVC-10 | Workshop diagnostic session with a scan tool on the OBD port while the item is installed | FW identity; DTC state | After the session, read DTCs (INS-06). Clearing DTCs with `tools/scripts/car/clear_dtc.py` is **prohibited** on the reference vehicle except under a recorded repair | R-VEH |
| SVC-11 | Aftermarket accessory that adds CAN nodes or modifies the forward-camera area (dash cams, radar detectors near the mirror, window films) | AOU-04, AOU-08, AOU-09 | Not allowed in the reference configuration without impact analysis | — |

### 4.2 Device remounting

Any removal of the device from its mount, or a `calibrationRecalibrating` alert ("Device Remount Detected", triggered when the calibration spread exceeds 4° pitch or 2° yaw, `calibrationd.py:35-36, 164-167`), requires: re-seat or remount per WP-O-01 INS-09, reset calibration (`selfdrive/ui/layouts/settings/device.py:93-110`), calibration drive (INS-25). The `calibrationd` check does not detect a small, stable mounting error within its validity limits, so the tolerance check in INS-25 is the control, not the absence of alerts.

### 4.3 Periodic maintenance of the item

| ID | Interval | Activity |
|---|---|---|
| PM-01 | Monthly | Inspect the harness routing and connectors for chafing or loose latches; clean camera windows |
| PM-02 | Monthly (development phase: weekly) | Retrieve logs for field monitoring ([WP-O-04](WP-O-04-field-monitoring.md)) |
| PM-03 | Every 6 months, and after any SVC trigger | Re-run INS-21…INS-23 (reference-configuration check) and INS-27 (PCS preservation) |
| PM-04 | Every 12 months | Check device mount adhesive; read DTCs; review that the installed release is still supported (§6) |

The intervals are proposals; they are confirmed or adjusted from field-monitoring data (OI-3).

## 5. Service of the item

| ID | Situation | Procedure |
|---|---|---|
| ITS-01 | Harness relay malfunction, CAN bus missing, or intermittent CAN errors | Inspect and reseat connectors (WP-O-01 INS-11/13). If the fault persists, replace the harness and repeat INS-14, INS-27. Return the faulty harness to quarantine and raise a problem report ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)) |
| ITS-02 | Panda firmware mismatch that `pandad` cannot resolve (`pandad.py:42-50` asserts) | Do not drive with the item. Reflash only from the release; if it fails, replace the device. Report |
| ITS-03 | Device hardware failure (overheating, fan, display, camera, power) | Replace the device. The replacement unit goes through the full provisioning and configuration steps INS-01, INS-15…INS-26 |
| ITS-04 | Device swap between vehicles | Prohibited without full reinstallation and clearing of `CarParamsCache`, calibration and learned parameters (WP-O-01 INS-24) |
| ITS-05 | Repairs inside the device or harness | Not allowed. LionDriver does not repair COTS hardware. Defective units go back to the supplier |

All service actions are recorded as an amendment to the vehicle's installation record ([WP-O-01 §5](WP-O-01-installation-and-provisioning-control.md#5-records)).

## 6. Software update policy

The full update and vulnerability process is in [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md). The operation-phase rules are:

| ID | Rule | Basis |
|---|---|---|
| UPD-01 | Only released LionDriver baselines (`ld-vX.Y.Z` with a signed release record, [WP-K-06](../10-safety-case/WP-K-06-release-record.md)) are installed on the reference vehicle | D-02, D-05; [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| UPD-02 | The updater's origin and branch point at the LionDriver release channel. The inherited updater fetches git from a configurable branch and has no signature check beyond TLS (`system/updated/updated.py:238, 387`; GAP-26). Until signed updates exist, automatic updates are disabled and updates are installed manually by the maintainer, followed by WP-O-01 INS-15…INS-23 | GAP-26; AOU-11 |
| UPD-03 | Every update that changes the model weights is SOTIF-relevant and needs the scenario re-evaluation of [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) before release | D-05 |
| UPD-04 | Every update that changes panda firmware or the opendbc safety code needs the envelope verification evidence for that release | T-03 |
| UPD-05 | Updates install offroad only (inherited: `updated` is an offroad process, `process_config.py:114`) | — |
| UPD-06 | After an update, the parameter set is checked against the release record (INS-19), because updates can change parameter defaults (example: upstream `f21bfc3` turned Experimental Mode on by default, GAP-18) | GAP-18 |
| UPD-07 | AGNOS OS updates are applied only when the LionDriver release pins the new version | WP-O-01 INS-16 |
| UPD-08 | A release that is withdrawn (field action, [WP-O-04](WP-O-04-field-monitoring.md) §9) must be replaced or the item put in dashcam mode on every installed vehicle | — |

Note on `Offroad_ConnectivityNeeded` (§3.3): with automatic updates disabled the inherited updater may still require periodic successful update checks before it allows engagement. How this behaves against a LionDriver update origin must be tested (OI-4).

## 7. Decommissioning

Decommissioning applies when the item is removed from the vehicle permanently, when the vehicle is sold or scrapped, when the device is reassigned, or when a release is withdrawn without replacement.

### 7.1 Removal and restoration of the stock vehicle

| ID | Step | Check |
|---|---|---|
| DEC-01 | Ignition off. Disconnect the device from the harness | — |
| DEC-02 | Remove the harness; reconnect the stock forward camera connector directly to the vehicle connector; seat latches fully | Latch engaged; pull test |
| DEC-03 | Ignition on: confirm no TSS warning; LTA/LDA, DRCC and PCS are available as before installation (compare with WP-O-01 INS-08 record) | Stock functions available, no DTC on camera, radar, EPS |
| DEC-04 | Read DTCs and clear only those caused by the disconnection, by a workshop scan tool | No remaining active DTCs |
| DEC-05 | Remove the device mount; clean the windscreen. If the stock camera bracket was disturbed, the stock camera must be re-aimed per Toyota procedure | Visual |

### 7.2 Data and key wiping

| ID | Step | Basis |
|---|---|---|
| DEC-06 | Retrieve the logs needed for field monitoring and any open problem report before wiping | [WP-O-04](WP-O-04-field-monitoring.md) |
| DEC-07 | Run the device reset ("reset & erase"). The inherited reset deletes `/data/*` and reformats the userdata partition (`openpilot/system/ui/tici_reset.py:47-63`); `HARDWARE.uninstall()` triggers it via `/data/__system_reset__` (`openpilot/common/hardware/comma/hardware.py:95-98`) | Removes routes, params, calibration, CarParams, VIN cache |
| DEC-08 | Wipe the device identity: the reset above does **not** erase `/persist/comma/` (device key pair `id_rsa`/`id_ecdsa` and `dongle_id`, `openpilot/common/api.py:59-63`, `system/athena/registration.py:38-41`). If the device leaves LionDriver control, the keys must be removed or the device unpaired from every back end it was registered with; if the device stays with LionDriver for reuse, the keys stay and the unit history is recorded | 21434 §14; privacy |
| DEC-09 | Remove any LionDriver credentials or SSH keys from the device (`GithubSshKeys`, `SshEnabled`) and revoke them on the server side | GAP-27 |
| DEC-10 | Revoke the device from LionDriver data paths (log upload endpoint, if one exists per WP-O-04) | WP-O-04 |
| DEC-11 | If the device is to be reused, put it in quarantine until refurbishment and incoming inspection (WP-O-01 INS-01…INS-04) | — |

### 7.3 End of support for a release

When a release reaches end of support (no further security or safety fixes), every user is informed through the channel in [WP-O-03](WP-O-03-user-information-safety-warnings.md) §9, with the date after which the release must not be engaged. End of support is decided and announced under [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md) (21434 §14).

### 7.4 Records

A decommissioning record is added to the vehicle's installation record: date, person, DEC-01…DEC-11 results, device disposition (reuse / returned / destroyed), confirmation that stock functions were restored.

## 8. Traceability

| This document | Traces to |
|---|---|
| OPS-01, OPS-02 | AOU-09, AOU-10 |
| OPS-03…OPS-05, §4.2 | AOU-08, AOU-06; SOTIF ([WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md)) |
| SVC-02, SVC-03 | AOU-01, AOU-02, AOU-03, AOU-05; SG-01, SG-03, SG-04, SG-05 |
| SVC-04, SVC-05, ITS-01, DEC-02, DEC-03 | AOU-04; SG-07 |
| UPD-01…UPD-08 | D-02, D-05, D-08; GAP-18, GAP-26, GAP-37 |
| DEC-06…DEC-10 | 21434 §14; GAP-27 |

## 9. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Specify TSR-8xx operation, service and decommissioning requirements in [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md) and trace OPS/SVC/UPD/DEC items to them | G2 |
| OI-2 | Decide whether the item should read selected vehicle DTC states itself (e.g. EPS, VSC) and block engagement, instead of relying on the driver's lamp check (OPS-01) | G2 |
| OI-3 | Confirm periodic maintenance intervals (§4.3) from field data | G6 |
| OI-4 | Test the inherited updater's connectivity-required lockout against a LionDriver update origin with automatic updates disabled | G4 |
| OI-5 | Define the procedure and tool for removing `/persist/comma/` keys on decommissioning (DEC-08) without damaging the device | G5 |
| OI-6 | Get Toyota service information for camera and radar aiming, and EPS/ECM software update practice, to refine SVC-02…SVC-05 | G2 |
