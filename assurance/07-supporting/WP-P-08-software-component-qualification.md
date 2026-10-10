# WP-P-08 Qualification of Software Components

| Field | Value |
|---|---|
| Work product | WP-P-08 Qualification of software components (third-party and upstream software) |
| Standard reference | ISO 26262-8:2018 §12; ISO 26262-6:2018 §7 (reuse in architecture); ISO 26262-9:2018 §6 (coexistence); ISO/SAE 21434:2021 §10 (reuse, off-the-shelf and open-source components) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | QM components and the boundary to the ASIL path |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review CR-10 per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) (I2 minimum) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Lists the third-party and upstream software components in the LionDriver reference configuration, allocates each one, and states how it is qualified or why qualification is not needed. Implements tailoring T-05 of [WP-M-01](../01-management/WP-M-01-assurance-strategy.md#5-tailoring) and policy U-5 of [WP-M-02](../01-management/WP-M-02-safety-plan.md).

**Key boundary.** The code in the ASIL path (opendbc safety and the panda firmware paths it relies on) is **not** qualified under 8 §12. Under T-03 it is treated as LionDriver-developed: requirements are back-filled and it is re-verified to the ASIL from the HARA ([WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) to [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md)). 8 §12 is used here only for QM components and for components whose non-interference with the envelope has to be shown.

## 2. Allocation categories

| Category | Meaning | Qualification route |
|---|---|---|
| ASIL | Executes in, or produces data used by, the envelope on the panda MCU | T-03 re-verification (not this document) |
| QM-SR | QM element whose output can contribute to a hazard (bounded by the envelope), SOTIF-relevant, or able to interfere with the envelope | 8 §12 qualification at QM + FFI argument ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) + SOTIF evaluation |
| QM-CS | Not safety-related functionally, but part of the attack surface | 21434 §10 component assessment, TARA input |
| NSR | Not safety-related and not in the attack surface of the reference configuration | Freedom-from-interference argument only (resource use on shared SoC) |

## 3. Component inventory

Pins from `git submodule status` and `uv.lock` at the baseline. Submodules marked *(not init.)* were not initialized in this checkout, so their content was not reviewed ([gap assessment §1](../00-assessment/gap-assessment.md#1-scope-and-method)).

| ID | Component | Version / pin | Origin | Where used | Category |
|---|---|---|---|---|---|
| SC-01 | opendbc safety (`opendbc_repo/opendbc/safety/**`) | `229dc70` | commaai/opendbc | Panda firmware safety modes (Toyota) | **ASIL** (T-03) |
| SC-02 | panda firmware (`panda/board/**`) | `92eb565` | commaai/panda | STM32H7 main loop, CAN/SPI drivers, heartbeat, relay, faults, bootstub | **ASIL** (T-03) for safety paths; rest analysed for FFI inside the MCU |
| SC-03 | STM32H7 CMSIS / device headers (`panda/board/stm32h7/inc/`) | in panda `92eb565` | ST / ARM (vendored) | Register definitions | **ASIL** (reviewed with SC-02; vendor headers checked against reference manual) |
| SC-04 | opendbc car port (`opendbc_repo/opendbc/car/**`, Toyota) | `229dc70` | commaai/opendbc | Host: CAN parse, state, control commands | QM-SR |
| SC-05 | opendbc CAN parser/packer (`opendbc_repo/opendbc/can/**`) | `229dc70` | commaai/opendbc | Host | QM-SR |
| SC-06 | openpilot selfdrive stack (`openpilot/selfdrive/**`) | `8b8c6ae` | commaai/openpilot | Host processes | QM-SR (LionDriver-maintained after fork; developed under QM + SOTIF, not "qualified") |
| SC-07 | AGNOS (Ubuntu-based Linux OS for comma devices) | `AGNOS_VERSION` default 19.9 (`launch_env.sh`); actual device version recorded in [WP-C-01](../02-concept/WP-C-01-item-definition.md) | comma.ai | SoC OS, kernel, drivers, SPI to panda | QM-SR, QM-CS |
| SC-08 | msgq | `0e266c1` *(not init.)* | commaai/msgq | Shared-memory IPC between all host processes | QM-SR (data integrity between QM processes), QM-CS (GAP-20) |
| SC-09 | cereal schemas + pycapnp / Cap'n Proto runtime | `openpilot/cereal/**`; pycapnp 2.1.0; `comma-deps-capnproto` 1.0.1.post103 | comma / capnproto project | Message definitions and serialization | QM-SR |
| SC-10 | rednose (EKF library) | `8671c17` *(not init.)* | commaai/rednose | `locationd` | QM-SR |
| SC-11 | tinygrad runtime and compiled models | tinygrad 0.14.0 at `d3f09c9` *(not init.)*; models as LFS oids | tinygrad project; comma (models) | `modeld`, `dmonitoringmodeld` | QM-SR; AI component under [WP-W-10](../05-software/WP-W-10-ml-engineering.md) |
| SC-12 | numpy | 2.5.3 | numpy project | Host maths in control, planning, modeld | QM-SR |
| SC-13 | acados runtime + generated MPC solver | `comma-deps-acados` 0.2.2.post103 | acados project (packaged by comma) | Longitudinal MPC (`controls/lib/longitudinal_mpc_lib`) | QM-SR |
| SC-14 | CPython | 3.12.13 (`.python-version`) | python.org (uv-managed) | Interpreter for most host processes | QM-SR |
| SC-15 | raylib UI (`comma-deps-raylib` 6.0.0.1.post103) | PyPI wheel | raylib project (packaged by comma) | Onroad UI and alerts | QM-SR (alert presentation is a SOTIF/HMI measure, [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)) |
| SC-16 | teleoprtc + WebRTC stack (`openpilot/system/webrtc`) | teleoprtc `1aa8fc4` *(not init.)* | commaai/teleoprtc | Live camera streaming, remote body control | QM-CS (GAP-27) |
| SC-17 | athena client, PyJWT 2.14.0, websocket-client 1.9.2, cryptography 50.0.1 | `uv.lock` | Various | Remote access to comma servers | QM-CS (GAP-27) |
| SC-18 | updated (git-based OTA) | `openpilot/system/updated` | commaai | Software update | QM-CS (GAP-26), safety-relevant for configuration integrity |
| SC-19 | ffmpeg, zstd, zeromq (`comma-deps-*` 7.1.0 / 1.5.6 / 4.3.5), pyzmq 27.2.0 | `uv.lock` | Various | Encoding, logging, compression | NSR (FFI only) |
| SC-20 | requests 2.34.2, tqdm, sounddevice 0.5.6, others | `uv.lock` | Various | Utilities, audio alerts (sounddevice: QM-SR via alert sounds) | NSR / QM-SR as marked |

## 4. Qualification approach per category

### 4.1 QM-SR components (8 §12 at QM)

For each QM-SR component a qualification record (SCQ-nn) documents:

| Element | Content |
|---|---|
| Identification | Name, exact version/pin, hash, origin URL, licence |
| Requirements on the component | Functional and timing behaviour LionDriver relies on (from [WP-W-03](../05-software/WP-W-03-software-architecture.md)); for numpy/CPython only the used subset |
| Configuration and environment | Build options, target (SoC), interaction with other components |
| Known anomalies | Upstream issue tracker review for the pinned version; CVE review (with [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)) |
| Verification | Tests that demonstrate the required behaviour in the LionDriver configuration (existing upstream tests run in fork CI where applicable; process replay with fork-owned refs) |
| Behaviour under failure | What happens when it fails (exception, hang, wrong data), how it is detected (e.g. `alive`/`valid` flags, `selfdrived` events), and why the envelope bounds the effect |
| Change control | Version pinned; any update is a CT-4 change with re-qualification ([WP-P-02](WP-P-02-change-management.md)) |

Priority order: SC-07 AGNOS, SC-08 msgq, SC-11 tinygrad/models, SC-09 capnp, SC-04/05 opendbc car and CAN, SC-13 acados, SC-10 rednose, SC-14 CPython, SC-12 numpy, SC-15 raylib.

### 4.2 QM-CS components

Assessed under 21434 §10 (with [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md)): SBOM entry, vulnerability monitoring, exposure in the reference configuration, and the decision to disable, constrain or keep (input to [WP-C-09](../02-concept/WP-C-09-tara.md)). For the reference configuration the recommended starting point is to disable or constrain SC-16, SC-17 and the remote features of SC-18 (gap assessment action 9).

### 4.3 NSR components

Covered by the FFI argument on the shared SoC: CPU, memory, storage and thermal budgets, and the fact that they have no path to the panda except through `pandad`. No individual qualification.

### 4.4 ASIL components (SC-01..SC-03)

Not qualified here. Re-verification under T-03 in WP-W-02..WP-W-08. The only 8 §12-like activity is for SC-03 vendor headers: check register definitions used by the safety paths against the STM32H7 reference manual revision recorded in [WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md).

## 5. Interfaces between the QM stack and the ASIL path

These interfaces decide whether a QM component can defeat the envelope, and are the main input to [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md):

| Interface | QM side | ASIL side | Known issue |
|---|---|---|---|
| SPI transport | `openpilot/selfdrive/pandad/spi.cc` on AGNOS kernel SPI | `panda/board/drivers/spi.h` | 8-bit XOR, no sequence counter (GAP-10) |
| Safety mode / param | `openpilot/selfdrive/pandad/panda_safety.cc` | `panda/board/main_comms.h` cmd `0xdc` | Unauthenticated, any time (GAP-09) |
| TX CAN frames | `card` → `pandad` | `safety_tx_hook` | Bounded by envelope checks |
| Heartbeat | `pandad` | `panda/board/main.c` | Shows pandad liveness, not control loop (GAP-10) |
| Firmware update | `pandad` / panda python flashing | bootstub signature check | RSA-1024/SHA-1, debug key (GAP-24, GAP-25) |

## 6. SBOM

A machine-readable SBOM (CycloneDX or SPDX) is generated per release from `uv.lock`, submodule pins and the AGNOS version, and stored in the evidence package ([WP-P-10](WP-P-10-release-management.md)). Generator: OI-3.

## 7. Open items

| ID | Item |
|---|---|
| OI-1 | Initialize and review msgq, rednose, teleoprtc and tinygrad submodules at their pins |
| OI-2 | Write SCQ records in the priority order of §4.1 |
| OI-3 | SBOM generation in CI |
| OI-4 | Record the actual AGNOS version on the reference device (default in `launch_env.sh` is only a fallback) |
| OI-5 | Decide which QM-CS components are disabled in the reference configuration (with WP-C-10) |
| OI-6 | Confirm that no code from SC-04/SC-05 executes on the panda MCU (only `opendbc/safety` is compiled into firmware) |
