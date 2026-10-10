# WP-W-09 Safety-Related Configuration and Calibration Data

| Field | Value |
|---|---|
| Work product | WP-W-09 Safety-related configuration and calibration data (car params, fingerprints, limits, model weights) |
| Standard reference | ISO 26262-6:2018 Annex C (software configuration; calibration data); ISO 26262-6:2018 §6, §9 (requirements on and verification of data); ISO 26262-8:2018 §7 (configuration management); ISO/PAS 8800:2024 (model as configuration item, informative); ASPICE 4.0 SWE.3 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Up to ASIL D (data that configures or parameterises the envelope E-03); QM / SOTIF / PAS 8800 for host data |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

ISO 26262-6 Annex C treats configuration data (selecting a variant or behaviour of the software) and calibration data (adapting the software's behaviour by values) as part of the software that must be specified, verified and controlled with the same rigour as code of the same ASIL. This document:

1. lists every data item that can change the safety-relevant behaviour of the LionDriver reference configuration (2020 Corolla LE, `TOYOTA_COROLLA_TSS2`, openpilot longitudinal, comma device with panda);
2. classifies each item, assigns an owner and ASIL, and records how it is verified, protected and changed today;
3. states requirements for data verification and protection (DVR-nn, §6).

A particular concern in openpilot is **online-learned parameters** (§4.4): the host stack adapts torque, steering-ratio, calibration and delay parameters while driving and stores them across drives. They change controller behaviour without any code change or release.

Related work products: CM classes CI-3, CI-4, CI-5 in [WP-P-01 §3](../07-supporting/WP-P-01-configuration-management-plan.md#3-configuration-items); requirements [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) (FSR-01.10, FSR-01.14, FSR-02.08); [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (Draft; TSR IDs cited below, in particular TSR-102, TSR-512, TSR-514, TSR-605 and TSR-801…806); model lifecycle [WP-W-10](WP-W-10-ml-engineering.md); installation and provisioning [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md).

## 2. Classification scheme

| Attribute | Values |
|---|---|
| Type | **CFG** configuration data (selects variant/feature); **CAL** calibration data (numeric value adapting behaviour); **LRN** learned calibration (computed and stored at run time); **MDL** ML model weights |
| Binding time | **Build** (compiled into firmware or committed source), **Fingerprint** (chosen at start-up from vehicle identification), **Install** (set during installation/provisioning), **User** (settings UI), **Runtime** (learned or written while driving) |
| Consumer | E-03 (envelope, panda), E-01 (host), E-02 (models) |
| ASIL | ASIL of the requirement the item parameterises. An item consumed by E-03 inherits the envelope ASIL (D provisional for SG-01, C for SG-03…SG-05). An item produced by QM and consumed by E-03 is an FFI concern ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) |
| Owner | Role accountable for the value and its rationale |

## 3. Inventory summary

| ID | Item | Type | Binding | Consumer | ASIL | Owner |
|---|---|---|---|---|---|---|
| CD-01 | Safety model and safety parameter (`safetyParam` = EPS scale 73 + flag bits) | CFG + CAL | Fingerprint (host) → SoC command `0xdc` | E-03 | C | Safety engineer (envelope) |
| CD-02 | Toyota envelope limit constants (`toyota.h`) | CAL | Build | E-03 | C | Safety engineer (envelope) |
| CD-03 | Generic envelope timing constants (RX timeouts, RT interval, heartbeat timeouts) | CAL | Build | E-03 | C | Safety engineer (envelope) |
| CD-04 | Toyota RX check table and TX whitelist | CFG | Build | E-03 | C | Safety engineer (envelope) |
| CD-05 | panda firmware build configuration (`RELEASE`/`ALLOW_DEBUG`, certificate) | CFG | Build | E-03 | C + CS | Release manager |
| CD-06 | Host controller limits `CarControllerParams` | CAL | Build (source) | E-01 | QM (must stay below CD-02, FSR-01.14) | Vehicle port owner |
| CD-07 | Platform configuration (flags, DBC choice, car specs) | CFG + CAL | Build + Fingerprint | E-01 (and CD-01 derivation) | QM; flags that set CD-01 bits: C | Vehicle port owner |
| CD-08 | Interface tuning (`interface.py`: delays, limit timer, longitudinal mode, accel limit flag) | CFG + CAL | Fingerprint | E-01 | QM | Vehicle port owner |
| CD-09 | Offline torque model (`torque_data/*.toml`) | CAL | Build | E-01 | QM | Vehicle port owner |
| CD-10 | Fingerprints and FW versions (`fingerprints.py`, fuzzy matching) | CFG | Fingerprint | E-01 → CD-01 | Selection result feeds C | Vehicle port owner |
| CD-11 | DBC files (Toyota) | CFG | Build | E-01 | QM | Vehicle port owner |
| CD-12 | Params defaults and user/debug settings (`params_keys.h`) | CFG | Build default + User/Runtime | E-01 | QM (SR-Q); some affect FSR-02.08 | Product owner |
| CD-13 | Cached vehicle identity and CarParams (`CarParamsCache`, `CarParams`, `CarParamsPersistent`, `CarParamsPrevRoute`) | CFG | Runtime | E-01 → CD-01 | Feeds C | Vehicle port owner |
| CD-14 | ML model weights (driving, DM; small and big variants) | MDL | Build (LFS) | E-02 | QM (PAS 8800 / SOTIF) | ML owner |
| CD-15 | Driver-monitoring policy thresholds (`policy.py`) | CAL | Build | E-01/DM | QM (SOTIF misuse measure, FSC §7) | DM owner |
| CD-16 | Camera calibration (`calibrationd`, `CalibrationParams`) | LRN | Runtime | E-01, E-02 | QM | Localization owner |
| CD-17 | Vehicle model learning (`paramsd`, `LiveParametersV2`) | LRN | Runtime | E-01 | QM | Controls owner |
| CD-18 | Lateral torque learning (`torqued`, `LiveTorqueParameters`) | LRN | Runtime | E-01 | QM | Controls owner |
| CD-19 | Actuator delay learning (`lagd`, `LiveDelay`) | LRN | Runtime | E-01 | QM | Controls owner |
| CD-20 | Host monitoring thresholds (excessive actuation, controller lateral limits) | CAL | Build | E-01 | QM | Controls owner |
| CD-21 | Model storage location (`.lfsconfig`) | CFG | Build | Supply of CD-14 | QM / CS | Configuration manager |
| CD-22 | Speed-dependent torque bound table τ_max(v) (future, TSR-102) | CAL | Build | E-03 | C | Safety engineer (envelope) |

## 4. Item details

Each entry gives: current value and source; what it affects; where it is verified today; protection (integrity/plausibility) today; change control; gaps.

### 4.1 Envelope data (E-03)

**CD-01 Safety model and safety parameter**

| Aspect | Content |
|---|---|
| Value (reference configuration) | `safetyModel = toyota`; `safetyParam = 73` (`0x0049`): low byte EPS torque factor 73 % (`EPS_SCALE` default, `opendbc_repo/opendbc/car/toyota/values.py:588-589`; set at `interface.py:27-28`). Flag bits (byte 2): `ALT_BRAKE 0x100`, `STOCK_LONGITUDINAL 0x200`, `LTA 0x400`, `SECOC 0x800` (`values.py:53-58`) — **none set** for the reference configuration (`interface.py:30-41, 105-111`). `alternativeExperience = 0` (`openpilot/selfdrive/car/card.py:110`) |
| Decoding in envelope | `toyota_init`: `toyota_dbc_eps_torque_factor = param & 0xFF`; flags via `GET_FLAG`; SECOC flag parsed only under `ALLOW_DEBUG` (`opendbc_repo/opendbc/safety/modes/toyota.h:367-383`) |
| Effect | EPS factor scales measured torque used by the measured-torque check (`toyota.h:104`, FSR-01.03). Flags select RX checks, TX whitelist and the lateral path (`toyota.h:384-425`). A wrong STOCK_LONGITUDINAL bit changes the TX set; a wrong EPS factor loosens or tightens the ±350 tracking bound |
| Path | Host fingerprints the car (CD-10) → `CarParams` written to Params by `card.py:146-150` → `pandad` reads `CarParams` and sends model/param to panda (`openpilot/selfdrive/pandad/panda_safety.cc:56-70`) → panda `0xdc` (`panda/board/main_comms.h:222-225`) |
| Verified today | Host side: `selfdrived` raises `controlsMismatch` if panda-reported model/param/alt-experience differ from `CarParams` for > 10 s (`openpilot/selfdrive/selfdrived/selfdrived.py:328-338`). Envelope side: tests set the param explicitly (`test_toyota.py`); `test_models.py` sets `safetyConfigs[-1]` per route (`opendbc_repo/opendbc/car/tests/test_models.py:186-190`) |
| Protection today | **None in the envelope.** No range or equality check of the EPS factor (any 0–255 accepted, including 0); unknown flag bits ignored; the SoC can change mode/param at any time without authentication (GAP-09). Host check is QM and slow (10 s) |
| Change control | `values.py`/`interface.py` are SR-Q; `toyota.h` is SR-A ([WP-P-01 §4.2](../07-supporting/WP-P-01-configuration-management-plan.md#42-globs)) |
| Gaps | GAP-09, FSR-01.10 not implemented. Addressed by DVR-01, DVR-02 |

**CD-02 Toyota envelope limit constants**

| Constant | Value | Source |
|---|---|---|
| `max_torque` | 1500 raw | `opendbc_repo/opendbc/safety/modes/toyota.h:173` |
| `max_rate_up` / `max_rate_down` | 15 / 25 raw per frame | `toyota.h:174-175` |
| `max_torque_error` | 350 raw | `toyota.h:176` |
| `max_rt_delta` | 450 raw per `MAX_RT_INTERVAL` | `toyota.h:177` |
| Steer-request cut | `min_valid_request_frames` 17, `max_invalid_request_frames` 1, `min_valid_request_rt_interval` 162 ms | `toyota.h:182-185` |
| LTA angle limits (not used in ref. config) | `max_angle` 1657, rate lookups | `toyota.h:188-201` |
| LTA torque limits (not used) | 1500 / 150 | `toyota.h:203-204` |
| `max_accel` / `min_accel` | 2000 / −3500 (0.001 m/s²) | `toyota.h:207-210` |

| Aspect | Content |
|---|---|
| Effect | Directly bound actuation (FSR-01.01…01.04, FSR-03.01, FSR-04.01) |
| Verified today | Toyota and common safety tests (WP-W-06 §4.1); test classes copy the same constants (`test_toyota.py:139-155`), so a wrong value passes (GAP-14) |
| Protection | Compiled into signed firmware (integrity = firmware integrity, CD-05). No physical rationale (GAP-04) |
| Change control | SR-A; independent review; WP-W-06 VS-UV-02…07 |
| Gaps | GAP-04 (rationale), GAP-14 (trace). DVR-03, DVR-04 |

**CD-22 Speed-dependent torque bound τ_max(v) (future)**

TSR-102 in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) requires a speed-dependent torque bound derived on the reference vehicle. It does not exist at the baseline: `dynamic_max_torque` is not set for Toyota (`modes/toyota.h:172-186`), although the mechanism exists in `lateral.h:66-71`. When introduced it is ASIL calibration data of E-03 and needs: a derivation record (measurement data, method, margins), a monotonicity and range check at build time, unit tests at every breakpoint and between breakpoints (WP-W-06 VS-UV-02), and SR-A change control. DVR-22.

**CD-03 Generic envelope timing constants**

| Constant | Value | Source |
|---|---|---|
| `MAX_RT_INTERVAL` | 250 000 µs | `opendbc_repo/opendbc/safety/declarations.h:71` |
| RX lag threshold | max(10 × expected period, 1 s), evaluated at 1 Hz | `opendbc_repo/opendbc/safety/safety.h:321-344` |
| Relay-malfunction grace | `safety_mode_cnt > 1` (1–2 s) | `safety.h:215-220, 372-380` |
| Heartbeat mismatch / loss | 3 s / 5 s with ignition (2 s without) | `panda/board/main.c:101-103, 182-213` |
| Expected RX frequencies (Toyota) | `0xAA` 83 Hz, `0x260` 50 Hz, `0x1D2` 33 Hz, `0x226` 40 Hz | `toyota.h:39-46` |

Verified by `test_safety_tick` (`common.py:1208`) for the RX timeout; heartbeat timing has no unit test. Values exceed the FSC §8 budgets (GAP-06). Change control SR-A. DVR-03.

**CD-04 Toyota RX check table and TX whitelist**

| Aspect | Content |
|---|---|
| Value | RX: `TOYOTA_RX_CHECKS(false)` for LKA: `0xAA` (no checksum, no counter), `0x260` (checksum, no counter, quality ignored), `0x1D2` (checksum, no counter), `0x226` (no checksum, no counter) (`toyota.h:39-46`). TX: `TOYOTA_LONG_TX_MSGS` (`toyota.h:6-32`, selected `toyota.h:384-393`) |
| Effect | Defines which inputs are integrity-checked and which outputs the SoC may command (FSR-01.06, FSR-07.02) |
| Verified today | `test_rx_hook` (checksum, `test_toyota.py:110`), `test_block_aeb` (`:87`), `test_spam_can_buses` (`common.py:937`) |
| Protection | Firmware integrity only |
| Gaps | GAP-01 (no counters); `0x344`/`0x411` allowed on TX (FSC OI-5) |

**CD-05 panda firmware build configuration**

| Aspect | Content |
|---|---|
| Value | Default `BUILD_TYPE = "DEBUG"`, adds `-DALLOW_DEBUG` and signs with the committed debug key unless `RELEASE` and `CERT` are set (`panda/SConscript:12-20`); version string `<BUILDER>-<git8>-<type>` (`SConscript:25-30`, `BUILDER = "DEV"` line 8) |
| Effect | `ALLOW_DEBUG` enables debug safety modes (`safety.h:413-422`) and SecOC flag parsing (`toyota.h:374-377`); debug key acceptance in the bootstub (GAP-25) |
| Verified today | panda CI builds both debug and release (release with the **debug** cert); no check that an installed device runs a RELEASE build |
| Protection | Bootstub signature check (RSA-1024/SHA-1, GAP-24) |
| Change control | `panda/SConscript` is SR-A; release procedure [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| Gaps | GAP-24, GAP-25. DVR-05 |

### 4.2 Vehicle-port data (host, E-01)

**CD-06 Host controller limits (`CarControllerParams`)**

| Value | Source |
|---|---|
| `STEER_MAX` 1500, `STEER_ERROR_MAX` 350, `STEER_STEP` 1 | `opendbc_repo/opendbc/car/toyota/values.py:18-21` |
| `STEER_DELTA_UP` 15 / `STEER_DELTA_DOWN` 25 (torque tune; 10/25 otherwise) | `values.py:45-51` |
| `ACCEL_MAX` 2.0 (with `RAISED_ACCEL_LIMIT`, else 1.5), `ACCEL_MIN` −3.5 m/s² | `values.py:38-43` |
| Driver-torque cut 500 raw; steer-rate cut ≥ 100 °/s after 17 frames | `opendbc_repo/opendbc/car/toyota/carcontroller.py:29-33` |

Effect: the host commands within these limits; the envelope (CD-02) enforces. **Zero margin** between CD-06 and CD-02 (gap assessment §3.1); FSR-01.14 requires margin. Verified by `opendbc_repo/opendbc/car/tests/test_lateral_limits.py` (jerk and lateral-accel bounds, lines 12-17, 63-69). No automated check that CD-06 < CD-02. DVR-06.

**CD-07 Platform configuration**

`TOYOTA_COROLLA_TSS2 = ToyotaTSS2PlatformConfig(...)` (`values.py:201-213`): flags `TSS2 | NO_DSU` (`values.py:108-116`), DBC `toyota_nodsu_pt_generated` + `toyota_tss2_adas`, `CarSpecs(mass=3060 lb, wheelbase=2.67 m, steerRatio=13.9, tireStiffnessFactor=0.444)`. The platform also covers hybrids and several non-US variants (`values.py:204-211`); the reference configuration is the US ICE sedan only. Flags drive CD-01 bits through `interface.py`. Verified by `opendbc_repo/opendbc/car/tests/test_platform_configs.py`, `toyota/tests/test_toyota.py` (`test_car_flags`, `test_tss2_dbc`). QM, SR-Q. Gap: variants covered by the same platform are outside the claim (WP-C-01); DVR-08.

**CD-08 Interface tuning**

`interface.py`: `steerActuatorDelay = 0.12`, `steerLimitTimer = 0.4` (`:49-50`); `openpilotLongitudinalControl = True` for TSS2 without `RADAR_ACC` (`:105-106`); `RAISED_ACCEL_LIMIT` for all TSS2 (`:117-118`); `HYBRID` flag set if a hybrid ECU answers (`:57-58`), which changes `longitudinalActuatorDelay` (`:121-122`). QM. Gap: `RAISED_ACCEL_LIMIT` not validated for the Corolla (FSR-03.01); hybrid detection by ECU presence. DVR-08.

**CD-09 Offline torque model**

`opendbc_repo/opendbc/car/torque_data/params.toml:65`: `TOYOTA_COROLLA_TSS2 = [LAT_ACCEL_FACTOR 1.991, MAX_LAT_ACCEL_MEASURED 1.869, FRICTION 0.196]`; `override.toml`, `substitute.toml` may replace values for other platforms. Used to configure the torque controller and as the centre of the torqued sanity window (CD-18). Verified by `test_lateral_limits.py` (`MAX_LAT_ACCEL_MEASURED ≤ ISO_LATERAL_ACCEL = 3.0`). Origin of the values (fleet data fit by comma) is not reproducible by LionDriver. QM. DVR-09.

**CD-10 Fingerprints and firmware versions**

| Aspect | Content |
|---|---|
| Value | `opendbc_repo/opendbc/car/toyota/fingerprints.py:445-632`: engine `0x700` 63 versions, engine `0x7e0` 16, EPS `0x7a1` 21, ABS `0x7b0` 49, fwdRadar `0x750/0xf` 5, fwdCamera `0x750/0x6d` 20 |
| Matching | Exact FW match, else fuzzy match by platform codes (`values.py:449`, `opendbc_repo/opendbc/car/fw_versions.py:54-98, 147-162`); result recorded as `CP.fuzzyFingerprint` (`opendbc_repo/opendbc/car/car_helpers.py:164`) |
| Effect | Chooses the platform → CD-01, CD-06…CD-09 |
| Verified today | `toyota/tests/test_toyota.py` (FW format, fuzzy rules, `test_valid_fw_versions`), `test_fw_fingerprint.py` |
| Protection | None against misidentification other than the fingerprint logic; cached result (CD-13) can bypass re-query |
| Gap | A fuzzy or wrong match selects another platform's data without the installer noticing. DVR-10 |

**CD-11 DBC files**

`toyota_nodsu_pt_generated.dbc`, `toyota_tss2_adas.dbc` and generator sources (`opendbc_repo/opendbc/dbc/generator/toyota/**`). Used by host parse/pack only; the envelope hard-codes addresses and bit positions in `toyota.h`. A DBC error can make host and envelope disagree; `test_models.py::test_panda_safety_carstate` compares them on recorded routes (needs comma route data). QM, SR-Q. DVR-11.

### 4.3 Settings, caches and models

**CD-12 Params defaults and settings** (`openpilot/common/params_keys.h`)

| Key | Default / flags | Line | Safety relevance | Proposed reference-configuration value |
|---|---|---|---|---|
| `ExperimentalMode` | PERSISTENT, `"1"` | 43 | End-to-end longitudinal by default (GAP-18, D-08) | `0` until validated |
| `DisengageOnAccelerator` | PERSISTENT, `"0"` | 35 | Gas does not disengage; envelope blocks long only (`longitudinal.h:3-5`) | Decision in WP-C-08 |
| `OpenpilotEnabledToggle` | PERSISTENT, `"1"` | 112 | `0` → passive/noOutput (`card.py:110-117`) | `1` |
| `IsDriverViewEnabled` | CLEAR_ON_MANAGER_START | 59 | Puts DM into demo mode with synthetic inputs (`selfdrive/monitoring/dmonitoringd.py:26-27`) (GAP-20, FSR-02.08) | Must not be settable while the item can engage |
| `JoystickDebugMode` | CLEAR_ON_MANAGER_START \| CLEAR_ON_OFFROAD_TRANSITION | 68 | Replaces controlsd by joystickd (`system/manager/process_config.py:34-47`) | Disabled in release |
| `LateralManeuverMode` / `LongitudinalManeuverMode` | same | 87 / 88 | Override model curvature / replace plannerd (GAP-20) | Disabled in release |
| `AlphaLongitudinalEnabled` | PERSISTENT \| DEVELOPMENT_ONLY | 42 | No effect on ref. config (not `RADAR_ACC`) | n/a |
| `LongitudinalPersonality` | PERSISTENT, STANDARD | 89 | Following distance / accel profile | Fixed set validated in WP-V-03 |
| `IsLdwEnabled` | PERSISTENT | 61 | Lane departure warning | QM |
| `SshEnabled`, `UpdaterTargetBranch` | PERSISTENT / CLEAR_ON_MANAGER_START | 124 / 135 | Remote access and update source (CS, GAP-26/27) | Per WP-C-10 |
| `SecOCKey` | PERSISTENT \| DONT_LOG | 120 | Not used (no `SECOC` flag) | n/a |

Protection: Params are unauthenticated files on the device; any local process can write them (GAP-20). Change control of defaults: `params_keys.h` is SR-Q (CI-4). DVR-12, DVR-13.

**CD-13 Cached vehicle identity and CarParams**

`CarParamsCache` (CLEAR_ON_MANAGER_START, `params_keys.h:24`) is used to skip FW querying when it has FW entries and a known VIN (`opendbc_repo/opendbc/car/car_helpers.py:93-98`). `card.py:141-150` writes `CarParams`, `CarParamsCache`, `CarParamsPersistent` and copies the previous route's params to `CarParamsPrevRoute`. `pandad` reads `CarParams` to set the safety mode (CD-01). No integrity protection (plain bytes). DVR-01, DVR-14.

**CD-14 ML model weights**

| File | LFS oid (prefix) | Size (bytes) | Use |
|---|---|---|---|
| `openpilot/selfdrive/modeld/models/driving_supercombo.onnx` | `sha256:65a08adc31d5c456219…` | 60 918 562 | Small driving model, compiled to `driving_tinygrad.pkl` (`modeld/SConscript:52`) |
| `dmonitoring_model.onnx` | `sha256:dee5a294e8afaacc929…` | 7 844 499 | DM model, compiled to `dmonitoring_model_tinygrad.pkl` (`SConscript:51`) |
| `big_driving_tinygrad.pkl` | `sha256:51420a138242fe57dc4…` | 799 942 038 | Big model (Chestnut, external eGPU) |
| `big_driving_warp_1344x760_tinygrad.pkl`, `big_driving_warp_1928x1208_tinygrad.pkl` | `sha256:17e31388…`, `sha256:e761b629…` | 844 637 / 844 380 | Warp kernels for big model |

Effect: the driving model produces the lateral and longitudinal action; the DM model drives the attention policy. Model selection depends on file presence and USB device detection (`modeld/helpers.py:11-44`). Protection: LFS content addressing at fetch time only; **no hash, version or signature check at load**; loading uses `pickle` (GAP-22). Storage is comma's LFS store (GAP-40, CD-21). Change control: model change = SOTIF-relevant change (D-05), [WP-W-10](WP-W-10-ml-engineering.md). DVR-15, DVR-16.

**CD-15 Driver-monitoring policy thresholds** (`openpilot/selfdrive/monitoring/policy.py`)

| Parameter | Value | Line |
|---|---|---|
| Alert minimum speed | 2.8 m/s | 29 |
| Wheel-touch policy alert 1/2/3 | 5 / 15 / 25 s | 31-33 |
| Vision policy alert 1/2/3 | 5 / 8 / 13 s | 34-36 |
| No-response timeout | 5 s | 39 |
| Lockout after | 2 × alert 3 or 1 × no response; durations 1/5/15/30 min | 42-44 |
| Face / eye / sunglasses / blink / phone / sleep thresholds | 0.7 / 0.65 / 0.9 / 0.865 / 0.5 / 0.75 | 49-54 |
| Pose pitch / yaw thresholds | 0.3133 / 0.4020 rad (slack 0.3237 / 0.5042) | 55-60 |
| High-uncertainty fallback | std > 0.3 for 10 s → wheel-touch policy | 77-78 |

QM under FSC §7 but required for the controllability assumption (AOU-06R). Verified by `selfdrive/monitoring/test_monitoring.py` (scenario tests; no data-loss tests, GAP-21). Values must match the timing set in [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) §5. DVR-17.

### 4.4 Online-learned parameters (LRN)

All four learners run on the QM host, persist their state in unauthenticated Params, restore it at the next start, and feed the lateral controller or the model input. The envelope bounds the **resulting actuation** (CD-02) regardless of what they learn, so their worst-case effect is an unwanted but envelope-bounded command (SOTIF, not an envelope violation). They matter because (a) they change behaviour between drives without a release, (b) a corrupted or drifted value can bias steering systematically within the envelope (e.g. a constant lateral offset), and (c) field observations cannot be reproduced without the learned state.

| ID | Learner | Stored as | Learned quantities | Plausibility bounds today | Used by | Restore check |
|---|---|---|---|---|---|---|
| CD-16 | `calibrationd` | `CalibrationParams` (PERSISTENT, `params_keys.h:19`) | Device mounting roll/pitch/yaw, camera height | Pitch `PITCH_LIMITS`, yaw ±0.0691 rad (`selfdrive/locationd/calibrationd.py:43-51`); clip ±0.005 beyond limits (`:56-59`); `INPUTS_NEEDED` 5 blocks before valid (`:33`) | modeld (warp), locationd; uncalibrated → no engagement (`selfdrived.py:275-286`) | Read with exception fallback (`calibrationd.py:72-87`) |
| CD-17 | `paramsd` | `LiveParametersV2` (PERSISTENT, `:82`), every 60 s (`paramsd.py:272-273`) | Steer ratio, tire stiffness, steering-angle offset, road roll | Steer ratio valid 0.5–2.0 × `CP.steerRatio` (`paramsd.py:47, 171`); stiffness valid 0.2–5.0 (`:172`); angle offset ≤ 10° (lowered 8°) with hysteresis (`:22-23, 155-156`); roll ±10° (`:18`); rate limits 20°/s offset, 20°/s roll (`:16-17`) | controlsd vehicle model and curvature (`controlsd.py:74-83`), which only floors stiffness and steer ratio at 0.1 and does not read the validity flags; invalidity is handled by selfdrived events (`paramsdTemporaryError`, `selfdrived.py:403-411`) | Steer-ratio sanity on restore (`paramsd.py:204-232`); stiffness reset to 1.0 every drive (`:235-237`) |
| CD-18 | `torqued` | `LiveTorqueParameters` (PERSISTENT \| DONT_LOG, `:85`) | Lateral-accel factor, offset, friction | Clipped to offline value (CD-09) ± 30 % (factor) and ± 50 % (friction) (`torqued.py:24-27, 93-96, 230-231`); learning only when engaged, no steer override, v > 15 m/s (`:22, 202`); enabled for Toyota (`ALLOWED_CARS`, `:37, 76`) | controlsd torque controller when `useParams` and `all_checks` (`controlsd.py:85-90`) | Restored only if restore key and `VERSION` match (`torqued.py:98-122`); **offset** has no explicit sanity bound in the lines reviewed (OI-5) |
| CD-19 | `lagd` | `LiveDelay` (PERSISTENT, `:81`) | Lateral actuator delay | `MIN_LAG` 0.15 s – `MAX_LAG` 0.65 s; confidence ≥ 0.7; v ≥ 50 mph (`lagd.py:24-34`) | Lateral planning/control delay compensation | To confirm (OI-5) |

Change control: algorithms and bounds are SR-Q source. The **learned values themselves are not configuration-controlled**: they differ per device, are not logged in full (`LiveTorqueParameters` is DONT_LOG) and are not part of any baseline. DVR-18…DVR-21.

### 4.5 Host monitoring thresholds and storage

**CD-20 Host monitoring thresholds**: excessive actuation detection uses 2 × `ACCEL_MAX`/`ACCEL_MIN` (±4 / −7 m/s²) and 2 × `ISO_LATERAL_ACCEL` (6 m/s²) for 0.25 s (`openpilot/selfdrive/selfdrived/helpers.py:12, 30, 41`; `opendbc_repo/opendbc/car/interfaces.py:25-26`); controller lateral limits `MAX_LATERAL_JERK` 5.0 m/s³, `MAX_LATERAL_ACCEL_NO_ROLL` 3.0 m/s², `MAX_CURVATURE` 0.2 1/m (`openpilot/selfdrive/controls/lib/drive_helpers.py:9-14`). QM; FSR-01.14 margin targets. DVR-06.

**CD-21 Model storage location**: `.lfsconfig` points to `https://huggingface.co/commaai/openpilot-lfs.git/info/lfs` with `locksverify = false` (GAP-40). Change: SR-T. DVR-16.

## 5. Protection and verification overview

| ID | ASIL | Verified today (where) | Integrity protection today | Plausibility today | Change control today | Main gap |
|---|---|---|---|---|---|---|
| CD-01 | C | Host 10 s mismatch check; safety tests set param explicitly | None | None in envelope | SR-Q (source) / runtime unprotected | GAP-09 |
| CD-02 | C | opendbc safety tests (upstream CI) | Firmware signature (weak) | n/a (constants) | SR-A | GAP-04, GAP-14 |
| CD-03 | C | `test_safety_tick` | Firmware signature | n/a | SR-A | GAP-06 |
| CD-04 | C | `test_rx_hook`, `test_block_aeb` | Firmware signature | n/a | SR-A | GAP-01 |
| CD-05 | C + CS | panda CI builds | Bootstub RSA-1024/SHA-1 | None (DEBUG not detected at runtime) | SR-A | GAP-24, GAP-25 |
| CD-06 | QM | `test_lateral_limits.py` | Source | None vs CD-02 | SR-Q | Zero margin |
| CD-07…CD-11 | QM (feeds C) | opendbc car tests | Source | Fingerprint logic | SR-Q | Fuzzy match (CD-10) |
| CD-12 | QM | None | None (Params files) | None | SR-Q (defaults only) | GAP-18, GAP-20 |
| CD-13 | feeds C | None | None | VIN/FW presence | — | Unprotected cache |
| CD-14 | QM/PAS | Model replay (comma Jenkins only) | LFS oid at fetch | None at load | D-05 (proposed) | GAP-22, GAP-40 |
| CD-15 | QM | `test_monitoring.py` | Source | n/a | SR-Q | GAP-21 |
| CD-16…CD-19 | QM | Process replay (comma refs) | None | Bounds in §4.4 | Algorithm only | Not baselined |
| CD-20 | QM | Unit tests partial | Source | n/a | SR-Q | — |
| CD-22 | C | — (future) | Firmware signature | Build-time check (DVR-22) | SR-A | Not yet defined |
| CD-21 | QM/CS | — | — | — | SR-T | GAP-40 |

## 6. Requirements on configuration and calibration data

Requirement IDs `DVR-nn` are local to this work product until they are migrated into [WP-W-02](WP-W-02-software-safety-requirements.md) as SWSRs and into `assurance/trace/` (OI-1). Parents use FSRs from WP-C-04 and TSRs from WP-S-02 (Draft). All statuses: Proposed.

| ID | Requirement | ASIL | Parent | Allocation | Verification | Current state / GAP |
|---|---|---|---|---|---|---|
| DVR-01 | In the reference configuration the envelope shall accept only safety model `toyota` with safety parameter `73` (no flag bits); any other model or parameter requested by the SoC shall leave the envelope in a non-actuating mode. | C | FSR-01.10 / TSR-512, TSR-804 | E-03 (`toyota_init`, `set_safety_hooks`) | T-SIL (WP-W-06 VS-UV-12), T-HIL | Not met: any 0–255 EPS factor accepted (`toyota.h:383`) (GAP-09) |
| DVR-02 | Once a car safety mode is active, the envelope shall reject mode or parameter changes from the SoC until ignition off. | C | FSR-01.10 / TSR-512, TSR-513 | E-03 (`main_comms.h` `0xdc`) | T-HIL (VS-UV-13) | Not met (GAP-09) |
| DVR-03 | Every envelope limit and timing constant (CD-02, CD-03) shall have a requirement ID, physical unit, value, tolerance and rationale recorded in `assurance/trace/` and a `@req` tag at its definition. | C | FSR-01.01…01.07 / TSR-101…104, 201…205, 401, 407 | E-03 source + trace | Review, trace check K10 (WP-P-06) | Not met (GAP-14, GAP-04) |
| DVR-04 | Unit tests of envelope limits shall take expected values from the requirement data (`assurance/trace/`), not from copies of the source constants. | C | DVR-03 | Test code | Review | Not met (`test_toyota.py:139-155`) |
| DVR-05 | Firmware installed in a vehicle shall be a RELEASE build signed with the LionDriver release key; the device shall report build type and firmware hash, and the host shall refuse to engage on a DEBUG build. | C | FSR-01.10 / TSR-514, TSR-802 | E-03 build, E-01 check | Release audit (WP-P-01 §11), T-HIL | Not met (GAP-25) |
| DVR-06 | An automated check shall verify that every host controller limit (CD-06, CD-20) is below the corresponding envelope limit (CD-02) by the margin set in FSR-01.14. | QM (supports C) | FSR-01.14 / TSR-605 | CI check | Analysis, CI | Not met (zero margin) |
| DVR-07 | The platform data used by the reference configuration (CD-07…CD-09) shall be recorded in the item definition as expected values, and a start-up check shall compare the selected platform and `CarParams` with them. | QM (feeds C) | FSR-01.10 / TSR-804 | E-01 | T-SIL, installation check (WP-O-01) | Not met |
| DVR-08 | Platform variants and flags not validated for the reference vehicle (hybrid, non-US variants, `RAISED_ACCEL_LIMIT` without Corolla validation) shall be excluded or validated before release. | QM | FSR-03.01 | E-01, WP-V-01 | Review, T-VEH | Open |
| DVR-09 | The provenance of the offline torque model (CD-09) shall be recorded, or the values re-derived from LionDriver reference-vehicle data. | QM | FSR-01.14 | E-01 | Analysis | Open |
| DVR-10 | In the reference configuration, fingerprinting shall require an exact FW match against the VIN-recorded ECU versions of the reference vehicle; fuzzy matching shall be disabled. | QM (feeds C) | FSR-01.10 / TSR-803 | E-01 (`car_helpers.py`, `fw_versions.py`) | T-SIL, installation check | Not met (fuzzy enabled by default, `fw_versions.py:147-153`) |
| DVR-11 | Host CAN signal definitions (DBC) for every signal the envelope also decodes shall be checked against the envelope decoding on recorded LionDriver routes. | QM (supports C) | FSR-01.06 | Test | `test_panda_safety_carstate` on fork-owned routes | Partial (comma routes only) |
| DVR-12 | Safety-relevant Params (CD-12) shall have documented reference-configuration values; at engagement the host shall verify them and refuse engagement if a debug or demo key (`IsDriverViewEnabled`, `JoystickDebugMode`, maneuver modes) is set. | QM | FSR-02.08 / TSR-610, TSR-613, TSR-806 | E-01 (selfdrived) | T-SIL | Not met (GAP-20) |
| DVR-13 | `ExperimentalMode` shall default to `0` in the reference configuration until the SOTIF evaluation of end-to-end longitudinal control is complete. | QM (SOTIF) | D-08, GAP-18 / TSR-806 | `params_keys.h` | Review | Not met (default `"1"`) |
| DVR-14 | Cached `CarParams` and `CarParamsCache` shall carry an integrity check (CRC or hash) that is verified before use; a mismatch shall force full fingerprinting. | QM (feeds C) | FSR-01.10 | E-01 (`card.py`) | T-SIL, FI | Not met |
| DVR-15 | Each model file shall be verified against a hash recorded in the release manifest before it is loaded; a mismatch shall prevent engagement. | QM (PAS 8800 / CS) | GAP-22 / TSR-801 | E-02 loader (`modeld`) | T-SIL, FI | Not met |
| DVR-16 | Released model files shall be stored in a LionDriver-controlled store, and the release manifest shall list each model's path, LFS oid and size. | QM | GAP-40, D-05 | CM | PCA audit (WP-P-01 §11) | Not met |
| DVR-17 | DM thresholds and timers (CD-15) shall match the values specified in WP-C-08 §5; a change shall trigger the DM validation tests of WP-V-02. | QM (SOTIF) | FSR-02.06 / TSR-608 | E-01/DM | Review, T-SIL | Open |
| DVR-18 | Every learned parameter (CD-16…CD-19) shall be bounded at the point of use by limits that are recorded with rationale, including the lateral-accel offset learned by `torqued`. | QM (SOTIF) | FSR-01.14 / TSR-605 | E-01 | Review, T-SIL | Partial (§4.4) |
| DVR-19 | Learned parameters restored from storage shall pass an integrity check and the same plausibility bounds as live values; failure shall reset to offline defaults. | QM | DVR-18 | E-01 | T-SIL, FI | Partial (paramsd steer ratio; torqued version key) |
| DVR-20 | The complete learned state (CD-16…CD-19) shall be logged at start and end of each drive so field events can be reproduced. | QM | WP-O-04 | E-01 logging | Review | Partial (`LiveTorqueParameters` DONT_LOG) |
| DVR-21 | An installer-initiated reset of all learned parameters shall exist and shall be performed at installation, after service on steering/suspension/tires, and after a software update that changes a learner. | QM | WP-O-01, WP-O-02 | E-01, procedure | Procedure review | Open |
| DVR-22 | The τ_max(v) table (CD-22) shall be generated from a recorded derivation (data set ID, method, margin) and checked at build time for monotonic speed breakpoints, values within [0, 1500] raw and agreement with the derivation record; the check result shall be part of the release evidence. | C | FSR-01.01 / TSR-102 | E-03 build + data | Analysis, T-SIL | Not implemented (no table yet) |

## 7. Change control rules for data

| Data class | Route ([WP-P-02](../07-supporting/WP-P-02-change-management.md)) | Additional evidence |
|---|---|---|
| CD-01…CD-05, CD-22 | SR-A | Re-run WP-W-06 VS-UV for the affected units; update trace data; I1 review minimum |
| CD-06…CD-11, CD-20 | SR-Q | DVR-06 check; car tests; process replay with fork-owned refs |
| CD-12 (defaults) | SR-Q | Impact analysis against WP-C-05/WP-C-08 |
| CD-14, CD-21 | SR-Q + D-05 model change | WP-V-03 scenario re-run; manifest update |
| CD-15 | SR-Q | DM validation per WP-V-02 |
| CD-16…CD-19 algorithms/bounds | SR-Q | Replay on fork-owned logs; DVR-18 review |
| Learned values (runtime) | Not change-controlled; governed by DVR-19…DVR-21 | Field monitoring (WP-O-04) |

## 8. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Migrate DVR-01…DVR-21 into WP-W-02 (SWSR) or WP-S-01/WP-C-07 as appropriate and into `assurance/trace/`; `DVR` is not a registered prefix in the README | Safety engineer | G3 |
| OI-2 | Re-check TSR parents when WP-S-02 is approved | Safety engineer | G2 |
| OI-3 | Record the reference vehicle's VIN-specific FW versions in WP-C-01 (input to DVR-07, DVR-10) | Maintainer | G1 |
| OI-4 | Decide whether learned parameters should be disabled (fixed offline values) for the reference configuration during validation, to make results reproducible | Safety engineer | G2 |
| OI-5 | Review `torqued` offset bounds and `lagd` restore logic in full (only constants and the lines cited were reviewed) | Controls owner | G3 |
| OI-6 | Confirm whether `CarParamsCache` can bypass fingerprinting on a different vehicle with the same device (VIN check) | Vehicle port owner | G2 |
| OI-7 | New finding for the gap assessment: envelope accepts any EPS scale factor in `safetyParam` (no range check, `toyota.h:383`); propose a GAP ID (related to GAP-09) | Safety engineer | G1 |
