# WP-O-01 Installation, Provisioning and Production Control

| Field | Value |
|---|---|
| Work product | WP-O-01 Installation, provisioning and production control |
| Standard reference | ISO 26262-7:2018 §5 (planning for production, production control, special characteristics, records), tailored per T-07; ISO 26262-4:2018 §6 (requirements for production, by reference to WP-S-06); ISO/SAE 21434:2021 §12 (production) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Up to ASIL C (SG-01 elements: harness, relay, panda firmware, safety-mode configuration); CS (provisioning) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

LionDriver does not manufacture hardware. The comma device, its integrated panda MCU and the Toyota harness are bought as finished COTS products (T-04). Under tailoring decision **T-07** ([WP-M-01 §5](../01-management/WP-M-01-assurance-strategy.md#5-tailoring)), the ISO 26262-7 "production" phase is reduced to what LionDriver does control:

1. **Installation** of the device and harness into the reference vehicle.
2. **Provisioning**: loading a released LionDriver software baseline, verifying the panda firmware and the safety-mode configuration, and setting parameters.
3. **Reference-configuration check**: confirming the vehicle, the device and the software match the configuration the safety case covers ([WP-M-01 §3.1](../01-management/WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to)).
4. **Calibration** of the camera extrinsics (`calibrationd`).
5. **Records and nonconformity handling** for all of the above.

Out of scope: manufacture and end-of-line test of the comma device and harness (comma.ai, upstream supplier per [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md)), and ISO 26262-7 production-process capability for those parts. The residual risk of unknown production quality is carried by hardware component qualification ([WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md)) and by the incoming-inspection steps below.

The requirements this procedure fulfils are the production and installation requirements (TSR-8xx block) that [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md) is to specify. WP-S-06 does not exist yet; this document states the procedure and proposes the requirement content (OI-1).

## 2. Context

### 2.1 Who installs

| Phase | Installer | Constraint |
|---|---|---|
| Development (G1–G5) | Project maintainer or a trained test engineer, for the single reference vehicle | Only on vehicles registered as test vehicles under [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) |
| After release (G6) | An installer who has completed the installation training in [WP-M-04](../01-management/WP-M-04-organization-competence-safety-culture.md) | Only for the reference configuration. No other vehicle may be provisioned with a LionDriver release build |

### 2.2 Inherited mechanisms that this procedure relies on

| Mechanism | What it does | Source | Limitation |
|---|---|---|---|
| Panda firmware signature check on start | `pandad` compares the 128-byte signature read from the panda with the signature at the end of the firmware file shipped in the software tree; reflashes on mismatch and asserts if the mismatch persists | `openpilot/selfdrive/pandad/pandad.py:16-50`; `panda/python/__init__.py:609-617` | Checks consistency with the firmware file on the device, not authenticity. The bootstub accepts RSA-1024/SHA-1 signed images and, in debug builds, the committed debug key (GAP-24, GAP-25) |
| Fingerprinting | FW-version query over UDS (exact match first) and CAN fingerprint fallback; result logged with `fuzzy` flag | `opendbc_repo/opendbc/car/car_helpers.py:84-148`; `card.py:96-106` | Fuzzy matching is accepted at runtime. A cached `CarParamsCache` can skip the FW query (`car_helpers.py:93-97`) |
| CarParams record | `card` writes `CarParams`, `CarParamsCache`, `CarParamsPersistent`; `carParams` is logged about every 50 s | `openpilot/selfdrive/car/card.py:141-150, 195-201` | Unauthenticated flat files (GAP-20) |
| Safety-mode set from CarParams | `pandad` sets ELM327 for fingerprinting, then the mode and param from `CarParams` once `FirmwareQueryDone` and `ControlsReady` | `openpilot/selfdrive/pandad/panda_safety.cc:5-70` | The QM host selects the safety mode (GAP-09) |
| Safety-mode cross-check | `selfdrived` raises `controlsMismatch` if the panda's reported mode, param or alternative experience differs from `CarParams` after 10 s | `openpilot/selfdrive/selfdrived/selfdrived.py:328-339` | Both sides come from the same QM `CarParams`; a wrong `CarParams` is not detected |
| Camera calibration | `calibrationd` estimates roll/pitch/yaw and height; status `uncalibrated` / `calibrated` / `invalid` / `recalibrating`; engagement blocked until `calibrated` | `openpilot/selfdrive/locationd/calibrationd.py:24-51, 150-171`; `selfdrived.py:275-286`; `events.py:816-832` | Detects only angles outside limits and large changes; does not detect a small, stable mounting error inside the limits |
| Relay malfunction detection | Panda latches `relay_malfunction` if intercepted messages appear on the car side | `opendbc_repo/opendbc/safety/safety.h:215-220, 372-380` | Traffic-based, 1–2 s grace, no contact readback (GAP-12) |

## 3. Installation procedure

Each step has an ID (`INS-nn`), the check that proves it, and the record field it fills (§5). Steps marked **[SC]** set or verify a special characteristic (§4). A step that fails stops the installation; the vehicle is not driven with the item engaged until the nonconformity is closed (§6).

### 3.1 Incoming inspection (before touching the vehicle)

| ID | Step | Acceptance check | Record |
|---|---|---|---|
| INS-01 | Identify the device: model (comma 3X / comma four), hardware serial, panda serial and hardware type | Matches the hardware revision approved in [WP-C-01](../02-concept/WP-C-01-item-definition.md) (WP-C-01 OI-2) | R-DEV |
| INS-02 | Identify the harness: type (Toyota TSS2 / "Toyota A" connector), revision, harness box revision | Matches the approved harness | R-DEV |
| INS-03 **[SC]** | Visual inspection of harness and connectors: no damaged pins, housings, latches or cable insulation; relay box undamaged | No defect found | R-DEV |
| INS-04 | Confirm the device is not a unit returned after a field event or decommissioned from another vehicle without refurbishment check (§7 of [WP-O-02](WP-O-02-operation-service-decommissioning.md)) | Unit history clean or refurbishment record present | R-DEV |

### 3.2 Vehicle preconditions

| ID | Step | Acceptance check | Record |
|---|---|---|---|
| INS-05 | Record VIN, model year, trim (LE), powertrain (ICE), tyre size, mileage | VIN decodes to a 2020 Corolla LE ICE sedan, US market | R-VEH |
| INS-06 **[SC]** | Read DTCs of EPS (`0x7a1`), ABS/VSC (`0x7b0`), engine (`0x7e0`), forward camera and radar with a scan tool, or `tools/scripts/car/read_dtc_status.py` with openpilot stopped | No active DTC in EPS, brake, powertrain, ADAS camera or radar (AOU-09, AOU-10) | R-VEH |
| INS-07 | Confirm no modification of steering, suspension, ride height, tyres outside OEM spec, or windscreen (aftermarket glass, tint strip in camera area) | None found (AOU-09) | R-VEH |
| INS-08 | Confirm stock TSS 2.0 functions work before installation: LTA/LDA, DRCC, PCS warning (static self-test at ignition), no TSS fault indicators | Functions available, no warnings | R-VEH |

### 3.3 Mechanical and electrical installation

| ID | Step | Acceptance check | Record |
|---|---|---|---|
| INS-09 **[SC]** | Mount the device on the windscreen behind the rear-view mirror, centred laterally, inside the wiper-swept area, with the road camera's view not obstructed by the mirror, sun-strip or the stock camera housing | Mount position within the tolerance band defined in OI-2; photo taken from inside and outside | R-INS |
| INS-10 | Clean the windscreen; apply mount; observe adhesive cure time from the mount supplier | Cure time observed | R-INS |
| INS-11 **[SC]** | Disconnect the stock forward camera connector; connect the harness in-line (camera side ↔ harness ↔ vehicle side); seat both connectors fully until the latches click | Both latches engaged; pull test by hand | R-INS |
| INS-12 | Route the harness cable along the headliner and A-pillar trim away from airbag deployment paths; secure it; no strain on connectors | Routing photo; airbag zones clear | R-INS |
| INS-13 | Connect the harness to the device; secure with the retaining feature | Connector seated | R-INS |
| INS-14 | Ignition on, engine off: device boots; no "CAN Bus Disconnected" or "Harness Relay Malfunction" alert (`events.py:938-946, 974-978`) | No alert | R-INS |

### 3.4 Provisioning (software, firmware, configuration)

| ID | Step | Acceptance check | Record |
|---|---|---|---|
| INS-15 **[SC]** | Install the released LionDriver software: a tagged release `ld-vX.Y.Z` ([WP-P-01 §7](../07-supporting/WP-P-01-configuration-management-plan.md)), installed from the LionDriver release channel, not from comma.ai's default installer URL or a development branch | Installed commit equals the tag's commit in the release record ([WP-K-06](../10-safety-case/WP-K-06-release-record.md)); build is not dirty (build metadata shows a clean release build) | R-SW |
| INS-16 | Confirm the AGNOS OS version equals the one pinned by the release (`AGNOS_VERSION`, `launch_env.sh:18-19`; images and hashes in `system/hardware/tici/agnos.json`) | Version matches release record | R-SW |
| INS-17 **[SC]** | Panda firmware verification: let `pandad` run its signature check (`pandad.py:20-50`), then read version and signature (`Panda.get_version()`, `Panda.get_signature()`) | Version string is the LionDriver release build (`LD-<git8>-RELEASE` per WP-P-01 §7, once implemented); signature equals the value recorded in the release record; firmware is **not** a DEBUG build (GAP-25) | R-SW |
| INS-18 | Confirm model weights: compute hashes of the files under `selfdrive/modeld/models/` that the release uses | Hashes equal those in the release record (D-05, GAP-22) | R-SW |
| INS-19 | Set parameters to the reference configuration values from the release record. At this baseline that includes at least: `ExperimentalMode` per decision D-08 (recommended off), `DisengageOnAccelerator` per the HMI decision ([WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)), `IsLdwEnabled` on, `SshEnabled` off, `JoystickDebugMode` / `LongitudinalManeuverMode` / `LateralManeuverMode` absent, `IsDriverViewEnabled` off, and `RecordFront` per the data-protection decision ([WP-O-04](WP-O-04-field-monitoring.md)) | Parameter dump equals the release record values | R-SW |
| INS-20 | Confirm remote access configuration per the cybersecurity concept: device not paired to comma connect, or pairing per the approved policy; athena and upload behaviour per [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md) | Matches policy | R-SW |

### 3.5 Reference-configuration check

This check confirms that the vehicle the item has just been fitted to is the configuration the safety case covers. It is needed because the item itself accepts fuzzy fingerprints and cached CarParams, and because the safety-mode cross-check (`selfdrived.py:328-339`) only compares two copies of the same QM data.

| ID | Step | Acceptance check | Record |
|---|---|---|---|
| INS-21 **[SC]** | Ignition on. Run the FW query (`tools/scripts/car/fw_versions.py`, which uses `opendbc/car/fw_versions.py`) or read `carFw` from the first `carParams` message of the installation drive | Every FW version for engine (`0x700`, `0x7e0`), EPS (`0x7a1`), ABS (`0x7b0`), forward radar (`0x750` sub `0xf`) and forward camera (`0x750` sub `0x6d`) is **identical** to the versions recorded for the reference vehicle (WP-C-01 OI-1). Being in the fingerprint database (`opendbc_repo/opendbc/car/toyota/fingerprints.py`) is not enough | R-CFG |
| INS-22 **[SC]** | Read the logged `carParams` | `carFingerprint == TOYOTA_COROLLA_TSS2`; `fuzzyFingerprint == false`; `fingerprintSource == fw`; `openpilotLongitudinalControl == true`; `passive == false`; `safetyConfigs[0].safetyModel == toyota`; `safetyConfigs[0].safetyParam == 73` (EPS scale only; no ALT_BRAKE, STOCK_LONGITUDINAL, LTA or SECOC flags; `toyota/interface.py:27-41, 105-111`, `values.py:53-58, 588`); `alternativeExperience == 0` (`card.py:111`) | R-CFG |
| INS-23 **[SC]** | Read `pandaStates` while onroad | `safetyModel == toyota`, `safetyParam == 73`, `alternativeExperience == 0`; `faults` empty; `safetyRxChecksInvalid == false` | R-CFG |
| INS-24 | Confirm no `CarParamsCache` from another vehicle was present before the first start (fresh install or cleared cache), and that the fingerprint override environment variables `FINGERPRINT`, `SKIP_FW_QUERY` and `DISABLE_FW_CACHE` (`car_helpers.py:86-88`) are not set in the release launch environment | Cache absent before first start, or contents match INS-22; variables unset | R-CFG |

When the safety-mode lock in panda firmware (GAP-09 action, [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) TSR-5xx) is implemented, INS-22/23 are extended to read the locked mode and param from the panda directly.

### 3.6 Calibration and functional check

| ID | Step | Acceptance check | Record |
|---|---|---|---|
| INS-25 **[SC]** | Calibration drive: drive manually on a straight road above 15 mph (`MIN_SPEED_FILTER`, `calibrationd.py:24`) with low yaw rate (< 2 °/s, `:26`) until `extrinsicsCalibration.calStatus == calibrated`. At 20 Hz camera odometry this needs at least 5 valid blocks of 100 samples (`:31-34`), i.e. ≥ 25 s of qualifying driving | `calibrated`; recorded roll, pitch, yaw and height. Pitch inside −5.2°…+9.7° and yaw inside ±4.0° (`calibrationd.py:42-46`, non-`mici` limits) and additionally inside the narrower installation tolerance from OI-2 | R-CAL |
| INS-26 | Check the "Reset Calibration" path works and does not run while engaged (`selfdrive/ui/layouts/settings/device.py:93-110`) | Reset refused while engaged; after reset a new calibration converges to within OI-2 tolerance of INS-25 | R-CAL |
| INS-27 **[SC]** | Relay and PCS-preservation check, stationary: with LD-SDA not engaged, confirm the stock forward camera's PCS messages reach the car side and the intercepted messages (`0x2E4`, `0x191`, `0x412`, `0x343`) do not (log review against `toyota.h:6-36` and `safety.h:274-281`) | Forwarding as specified; no `relayMalfunction` | R-FUN |
| INS-28 | Engagement check on a closed area or quiet road with a trained driver: engage via cruise; disengage by brake, by cancel; confirm steering override by hand; confirm `controlsMismatch`, `relayMalfunction`, `canError` are absent | All transitions as specified; driver can overpower steering | R-FUN |
| INS-29 | Driver monitoring check: driver-facing camera sees the driver's face in the normal seating position (driver view in settings, offroad only); a deliberate look-away while engaged produces "Pay Attention" | DM functional | R-FUN |
| INS-30 | Confirm the driver has received the user information and briefing ([WP-O-03](WP-O-03-user-information-safety-warnings.md)) and acknowledged it; in the development phase, confirm the driver is an approved safety driver ([WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md)) | Signed acknowledgement | R-USR |

## 4. Special characteristics

ISO 26262-7 §5 calls for special characteristics to be identified and controlled. For the retrofit they are installation and configuration characteristics whose deviation can lead to a safety goal violation.

| ID | Characteristic | Safety goal / AoU | Control | Verification | Reaction on deviation |
|---|---|---|---|---|---|
| SPC-01 | Harness connector seating and pin integrity (camera side and vehicle side) | SG-07, SG-01, SG-03/04 (CAN path) | INS-03, INS-11 | Visual and pull check; no `canBusMissing`/`canError` | Reseat or replace harness; repeat INS-14, INS-27 |
| SPC-02 | Relay intercept function | SG-07, SG-01 | INS-27 | Log review; `relayMalfunction` absent | Replace harness; do not engage |
| SPC-03 | Device mount position and attitude | SOTIF (AOU-08) | INS-09, INS-25 | Photo + calibration angles within tolerance | Remount, reset calibration, recalibrate |
| SPC-04 | Software baseline identity (commit, clean build, AGNOS version, model hashes) | All SGs | INS-15, INS-16, INS-18 | Compare with release record | Reinstall release |
| SPC-05 | Panda firmware identity (release build, signature) | SG-01…SG-07 | INS-17 | Signature and version compare | Reflash from release; if persistent, quarantine device |
| SPC-06 | Safety mode and safety parameter | SG-01, SG-03, SG-04, SG-05 | INS-22, INS-23 | `carParams` and `pandaStates` compare | Stop; investigate fingerprint; no engagement |
| SPC-07 | Vehicle ECU firmware versions equal to the reference record | All SGs (validity of AoUs) | INS-21 | Exact FW compare | Vehicle is outside the reference configuration; impact analysis ([WP-M-12](../01-management/WP-M-12-impact-analysis.md)) before any use |
| SPC-08 | Vehicle health (no active DTCs, unmodified chassis) | AOU-09, AOU-10 | INS-06, INS-07 | Scan tool | Repair vehicle first |
| SPC-09 | Parameter set (Experimental Mode, debug modes, DM demo, SSH) | SOTIF, CS, GAP-18, GAP-20 | INS-19 | Parameter dump compare | Reset parameters to release values |

## 5. Records

One installation record per vehicle and per installation event (first install, reinstall, device swap). It is stored in the LionDriver repository under `assurance/09-production-operation/records/<VIN-last6>/<date>-install.md` (private storage if the record holds personal data; see OI-4). Records are kept for the life of the installation plus the retention period set in [WP-P-04](../07-supporting/WP-P-04-documentation-management.md).

| Record block | Content |
|---|---|
| R-DEV | Device model, hardware serial, panda serial and type, harness type and revision, inspection result |
| R-VEH | VIN, model year, trim, powertrain, tyre size, mileage, DTC readout (raw output attached), modifications check |
| R-INS | Installer, date, mount photos, routing photos, connector checks, first-boot result |
| R-SW | Release tag and commit, build clean flag, AGNOS version, panda firmware version and signature (hex), model hashes, parameter dump |
| R-CFG | FW query output (raw), `carParams` excerpt (fingerprint, fuzzy flag, source, safety configs, alternative experience, longitudinal flag), `pandaStates` excerpt |
| R-CAL | Calibration angles and height, `calPerc`, number of valid blocks, route ID of the calibration drive |
| R-FUN | Results of INS-27…INS-29 with route IDs |
| R-USR | Driver name, briefing version ([WP-O-03](WP-O-03-user-information-safety-warnings.md) version), acknowledgement signature, safety-driver approval reference (development phase) |
| Sign-off | Installer signature; second-person check of R-SW and R-CFG (I1) before first engagement |

A template file is to be created with the first installation (OI-3). Automating the R-SW and R-CFG extraction from the installation route log is proposed (OI-5).

## 6. Nonconformity handling

| Situation | Action |
|---|---|
| Any INS step fails | Stop. Mark the record "nonconforming". Do not engage the item. Fix and repeat the failed step and every dependent step (dependency: INS-11 → INS-14, INS-27; INS-09 → INS-25; INS-15/17 → INS-22/23) |
| SPC-07 deviation (vehicle FW differs from the reference) | The vehicle is not the reference configuration. The item may be left installed in dashcam mode only (`passive`); engagement is prohibited until an impact analysis under [WP-M-12](../01-management/WP-M-12-impact-analysis.md) extends the scope |
| SPC-05 deviation that persists after reflash, or a DEBUG firmware found on a release install | Treat as a potential cybersecurity event. Quarantine the device. Report through [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md) and [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) |
| Defective harness or device (incoming or found during installation) | Quarantine with a tag; problem report under [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md); supplier report to comma.ai per [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md); field-monitoring entry if the part type has been installed elsewhere ([WP-O-04](WP-O-04-field-monitoring.md)) |
| A deviation found after the vehicle has been driven with the item engaged | Safety anomaly per [WP-M-02 §9](../01-management/WP-M-02-safety-plan.md#9-safety-anomaly-handling): stop use, triage, check logs of all drives since installation |

## 7. Cybersecurity aspects of provisioning (21434 §12)

| Concern | Control | Reference |
|---|---|---|
| Software from an untrusted origin | Install only from the LionDriver release channel; verify commit against the signed tag | WP-P-01 §7; [WP-O-05](WP-O-05-cybersecurity-incident-response-updates.md); GAP-26 |
| Panda firmware authenticity | INS-17 compares with the release record. Real authenticity needs a LionDriver signing key with a modern algorithm, RDP/WRP set, and no debug-key acceptance in release builds | GAP-24, GAP-25; [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) |
| OS images | AGNOS images are fetched from comma's CDN (`system/hardware/tici/agnos.json`); hashes recorded in the release record | [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md) |
| Debug access left enabled | INS-19 checks `SshEnabled` off and debug modes absent | GAP-20, GAP-27 |
| Device identity keys | Device keys live in `/persist/comma/` (`openpilot/common/api.py:59-63`). A device reused from another vehicle keeps them; see decommissioning in [WP-O-02](WP-O-02-operation-service-decommissioning.md) | — |

## 8. Traceability

| This document | Traces to |
|---|---|
| INS-03, INS-11, INS-14, INS-27; SPC-01, SPC-02 | SG-07, SG-01; GAP-12; AOU-04 |
| INS-06…INS-08; SPC-08 | AOU-09, AOU-10 |
| INS-09, INS-25, INS-26; SPC-03 | AOU-08 (SOTIF) |
| INS-15…INS-20; SPC-04, SPC-05, SPC-09 | All SGs; GAP-18, GAP-20, GAP-22, GAP-24, GAP-25, GAP-26 |
| INS-21…INS-24; SPC-06, SPC-07 | SG-01, SG-03, SG-04, SG-05; GAP-09; [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md) |
| INS-28, INS-29 | SG-05, AOU-02, AOU-03; F-04 |
| INS-30 | AOU-06, AOU-07 |

## 9. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Write the TSR-8xx production/installation requirements in [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md) and trace each INS step to them | G2 |
| OI-2 | Define the mount position tolerance and the calibration angle tolerance band (narrower than the `calibrationd` validity limits), based on the angles at which the driving model was validated | G4 |
| OI-3 | Create the installation record template (§5) and fill it for the reference vehicle; this also closes WP-C-01 OI-1/OI-2 | G1 |
| OI-4 | Decide where records holding VIN and driver identity are stored (privacy) | G1 |
| OI-5 | Write a script that extracts R-SW and R-CFG fields from the installation route log and compares them with the release record | G4 |
| OI-6 | Define the LionDriver release channel and installer URL so INS-15 cannot fall back to comma.ai's default installer | G5 |
| OI-7 | Specify the PCS-preservation check (INS-27) message list exactly, once AOU-04 analysis in [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) identifies the PCS-relevant camera messages | G2 |
| OI-8 | Installer training content and competence record ([WP-M-04](../01-management/WP-M-04-organization-competence-safety-culture.md)) | G5 |
