# WP-P-08 Qualification of Software Components

| Field | Value |
|---|---|
| Work product | WP-P-08 Qualification of software components (third-party and upstream software) |
| Standard reference | ISO 26262-8:2018 §12; ISO 26262-6:2018 §7 (reuse in architecture); ISO 26262-9:2018 §6 (coexistence); ISO/SAE 21434:2021 §10 (reuse, off-the-shelf and open-source components) |
| Version | 0.2 (RR-2026-008 F-29: reuse-assessment records per WP-M-14 §6 (§4.5), inherited/LionDriver-authored split; pins updated to `682f184`; F-28: Author, baseline; 2026-10-12). 0.1 |
| Status | Draft |
| ASIL / scope | QM components and the boundary to the ASIL path; reuse assessment of the ASIL-path components |
| Author | Assurance team (AI-assisted draft, Claude) |
| Reviewer(s) | TBD (I1); confirmation review CR-10 per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) (I2 minimum) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `682f184` (opendbc `7993399`, panda `8aa8671`) |

## 1. Purpose and scope

Lists the third-party and upstream software components in the LionDriver reference configuration, allocates each one, and states how it is qualified or why qualification is not needed. Implements tailoring T-05 of [WP-M-01](../01-management/WP-M-01-assurance-strategy.md#5-tailoring) and policy U-5 of [WP-M-02](../01-management/WP-M-02-safety-plan.md). §4.5 holds the reuse-assessment records that [WP-M-14 §6](../01-management/WP-M-14-iso26262-6-implementation-specification.md) requires for every safety-relevant component.

**Key boundary.** The code in the ASIL path (opendbc safety and the panda firmware paths it relies on) is **not** qualified under 8 §12. Under T-03 it is treated as LionDriver-developed: requirements are back-filled and it is re-verified to the ASIL from the HARA ([WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) to [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md)). 8 §12 is used here only for QM components and for components whose non-interference with the envelope has to be shown.

**Inherited and LionDriver-authored code.** The ASIL-path repositories are LionDriver forks of comma.ai upstream: `jherrodthomas/opendbc` (upstream base `229dc70`, commaai/opendbc) and `jherrodthomas/panda` (upstream base `92eb565`, commaai/panda). All non-merge commits in opendbc `229dc70..7993399` (10) and panda `92eb565..8aa8671` (17) are LionDriver commits. They change only `opendbc/safety/**` in opendbc and `board/**`, `SConscript`, `python/__init__.py` and `tests/**` in panda. The split per software unit (inherited, inherited and modified, LionDriver-authored) is the Origin column of [WP-W-05 §2](../05-software/WP-W-05-software-unit-design.md).

## 2. Allocation categories

| Category | Meaning | Qualification route |
|---|---|---|
| ASIL | Executes in, or produces data used by, the envelope on the panda MCU | T-03 re-verification (not this document) |
| QM-SR | QM element whose output can contribute to a hazard (bounded by the envelope), SOTIF-relevant, or able to interfere with the envelope | 8 §12 qualification at QM + FFI argument ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) + SOTIF evaluation |
| QM-CS | Not safety-related functionally, but part of the attack surface | 21434 §10 component assessment, TARA input |
| NSR | Not safety-related and not in the attack surface of the reference configuration | Freedom-from-interference argument only (resource use on shared SoC) |

## 3. Component inventory

Pins from the gitlinks of superproject `682f184` (`git ls-tree 682f184`) and from `uv.lock` at `682f184`. The pins of msgq, rednose, teleoprtc and tinygrad and the `uv.lock` versions are unchanged from `8b8c6ae`. Submodules marked *(not init.)* are not initialized in this checkout, so their content was not reviewed ([gap assessment §1](../00-assessment/gap-assessment.md#1-scope-and-method)).

| ID | Component | Version / pin | Origin | Where used | Category |
|---|---|---|---|---|---|
| SC-01 | opendbc safety (`opendbc_repo/opendbc/safety/**`) | `7993399` (at `8b8c6ae`: `229dc70`) | jherrodthomas/opendbc, fork of commaai/opendbc at `229dc70`; LionDriver changes in `229dc70..7993399` | Panda firmware safety modes (Toyota) | **ASIL** (T-03) |
| SC-02 | panda firmware (`panda/board/**`) | `8aa8671` (at `8b8c6ae`: `92eb565`) | jherrodthomas/panda, fork of commaai/panda at `92eb565`; LionDriver changes in `92eb565..8aa8671` | STM32H7 main loop, CAN/SPI drivers, heartbeat, relay, faults, bootstub, IWDG, safety task, reference lock | **ASIL** (T-03) for safety paths; rest analysed for FFI inside the MCU |
| SC-03 | STM32H7 CMSIS / device headers (`panda/board/stm32h7/inc/`) | in panda `8aa8671` | ST / ARM (vendored in upstream panda) | Register definitions | **ASIL** (reviewed with SC-02; vendor headers checked against reference manual) |
| SC-04 | opendbc car port (`opendbc_repo/opendbc/car/**`, Toyota) | `7993399` (no LionDriver change since `229dc70`) | commaai/opendbc via the fork | Host: CAN parse, state, control commands | QM-SR |
| SC-05 | opendbc CAN parser/packer (`opendbc_repo/opendbc/can/**`) | `7993399` (no LionDriver change since `229dc70`) | commaai/opendbc via the fork | Host | QM-SR |
| SC-06 | openpilot selfdrive stack (`openpilot/selfdrive/**`) | `682f184` | commaai/openpilot, LionDriver-maintained fork | Host processes | QM-SR (LionDriver-maintained after fork; developed under QM + SOTIF, not "qualified") |
| SC-07 | AGNOS (Ubuntu-based Linux OS for comma devices) | `AGNOS_VERSION` default 19.9 (`launch_env.sh` at `682f184`); actual device version recorded in [WP-C-01](../02-concept/WP-C-01-item-definition.md) | comma.ai | SoC OS, kernel, drivers, SPI to panda | QM-SR, QM-CS |
| SC-08 | msgq | `0e266c1` *(not init.)*; a sync to `326a9f5` is drafted, not taken ([sync record](impact/sync-2026-10-10-msgq-326a9f5.md)) | jherrodthomas/msgq, fork of commaai/msgq | Shared-memory IPC between all host processes | QM-SR (data integrity between QM processes), QM-CS (GAP-20) |
| SC-09 | cereal schemas + pycapnp / Cap'n Proto runtime | `openpilot/cereal/**` at `682f184`; pycapnp 2.1.0; `comma-deps-capnproto` 1.0.1.post103 | comma / capnproto project | Message definitions and serialization | QM-SR |
| SC-10 | rednose (EKF library) | `8671c17` *(not init.)* | jherrodthomas/rednose, fork of commaai/rednose | `locationd` | QM-SR |
| SC-11 | tinygrad runtime and compiled models | tinygrad 0.14.0 at `d3f09c9` *(not init.)*; models as LFS oids | tinygrad project (submodule URL tinygrad/tinygrad, not forked); comma (models) | `modeld`, `dmonitoringmodeld` | QM-SR; AI component under [WP-W-10](../05-software/WP-W-10-ml-engineering.md) |
| SC-12 | numpy | 2.5.3 | numpy project | Host maths in control, planning, modeld | QM-SR |
| SC-13 | acados runtime + generated MPC solver | `comma-deps-acados` 0.2.2.post103 | acados project (packaged by comma) | Longitudinal MPC (`controls/lib/longitudinal_mpc_lib`) | QM-SR |
| SC-14 | CPython | 3.12.13 (`.python-version`) | python.org (uv-managed) | Interpreter for most host processes | QM-SR |
| SC-15 | raylib UI (`comma-deps-raylib` 6.0.0.1.post103) | PyPI wheel | raylib project (packaged by comma) | Onroad UI and alerts | QM-SR (alert presentation is a SOTIF/HMI measure, [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)) |
| SC-16 | teleoprtc + WebRTC stack (`openpilot/system/webrtc`) | teleoprtc `1aa8fc4` *(not init.)* | jherrodthomas/teleoprtc, fork of commaai/teleoprtc | Live camera streaming, remote body control | QM-CS (GAP-27) |
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

Not qualified here. Re-verification under T-03 in WP-W-02..WP-W-08; the reuse-assessment records RA-01…RA-04 (§4.5) record what exists and what is missing. The only 8 §12-like activity is for SC-03 vendor headers: check register definitions used by the safety paths against the STM32H7 reference manual revision recorded in [WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md).

### 4.5 Reuse-assessment records (WP-M-14 §6)

One record per safety-relevant software component, with the fields of [WP-M-14 §6](../01-management/WP-M-14-iso26262-6-implementation-specification.md). "Not confirmed" means the statement could not be checked against the code or a record for this draft. No record is reviewed: the Review field is TBD everywhere. "Existing verification evidence" lists what is defined and where it runs; no LionDriver run is recorded as evidence yet ([WP-W-06](../05-software/WP-W-06-software-unit-verification.md) results section: not yet executed), and no HIL test has been run ([WP-W-08](../05-software/WP-W-08-embedded-software-testing.md), bench D-04).

#### RA-01 opendbc safety core (SC-01, part)

| Field | Content |
|---|---|
| Component, source, owner | `opendbc_repo/opendbc/safety/{safety.h, lateral.h, longitudinal.h, helpers.h, declarations.h, modes/defaults.h}`; upstream commaai/opendbc; fork jherrodthomas/opendbc (LionDriver) |
| Version and baseline | opendbc `7993399` (LionDriver `master`); upstream base `229dc70`; no upstream tag |
| Intended function; safety relevance | Generic envelope: RX validation and timeout, TX whitelist and hook dispatch, forwarding block, engagement edges, lateral/longitudinal limit helpers, TX rate supervision (reference build). ASIL B‡ (E-03a). SWSRs allocated to U-SAF-CORE, U-SAF-LAT, U-SAF-LONG, U-SAF-HELP (e.g. 103–108, 201–206, 301–311, 401–406, 506a, 516b, 518, 704, 710; [`swsr.yaml`](../trace/items/swsr.yaml)) |
| Origin split | Inherited unchanged: `lateral.h`, `longitudinal.h`, `helpers.h`, `safety_rx_hook`, RX checks, forwarding, `generic_rx_checks`. Modified by LionDriver: `safety_tx_hook`, `safety_tick`, `set_safety_hooks`, `pcm_cruise_check`, `safety_config` (`declarations.h:236-245`). LionDriver-authored: `tx_rate_check`, `rx_check_lagging`, `rx_checks_allow_engagement` ([WP-W-05 §2](../05-software/WP-W-05-software-unit-design.md), UN-01…UN-13, UN-36, UN-37) |
| Existing development evidence | Upstream: none found (no requirements, design or review records; code comments only). LionDriver: back-filled SWSRs (WP-W-02), unit design (WP-W-05), design note [DN-01](../05-software/design-notes/DN-01-tx-rate-supervision.md), change records in [`impact/`](impact/README.md); none reviewed |
| Existing verification evidence | Upstream unit tests in `opendbc/safety/tests/` (Python on `libsafety`, host x86), 100 % line-coverage gate, MISRA C:2012 (cppcheck), mutation tests: run in the opendbc fork CI (`.github/workflows/tests.yml`, job "safety") and in the superproject `.github/workflows/safety.yaml` (default and `LIONDRIVER_REFERENCE=1` variants, MISRA, mutation), on GitHub-hosted Ubuntu runners. Coverage type: line only (GAP-13). LionDriver tests added in `tests/test_toyota.py` (e.g. `test_tx_rate_*`, `test_rx_timeout_5_periods*`, `test_no_engagement_with_invalid_rx_checks`). Not run on target hardware |
| Operational assumptions | Compiled into the panda firmware (STM32H7, single core, all ISRs at equal priority); 32-bit µs timer; `safety_tick` called periodically (100 Hz in LionDriver panda, 1 Hz upstream); mode and parameter supplied by the host (locked only in the reference build) |
| Known defects and limitations | GAP-01 (no counters, 8-bit checksums), GAP-02 (no driver-torque check on LKA), GAP-04 (limits without rationale), GAP-06 (detection times, partly addressed), GAP-11 (forwarding before validation), GAP-13 (line coverage only), GAP-46 (rejected frame dropped, not replaced), GAP-48 (incomplete checks) |
| Dependencies | `CANPacket_t` and `dlc_to_len` from panda; `microsecond_timer_get` from panda; GCC (arm-none-eabi for target, host GCC for tests); cppcheck MISRA addon |
| Gaps | Requirements: back-filled SWSRs proposed, not reviewed. Architecture: ISR context and shared data argued in WP-W-03 §6.3, not verified. Verification: no branch/MC/DC coverage, no target execution, no requirements-based test specification reviewed (WP-W-06 VS-UV-nn) |
| Strategy | Re-verify to the ASIL (T-03) |
| Additional engineering needed | Requirements-based unit tests per WP-W-06 with branch coverage; record CI runs as evidence (build manifest, WP-W-01 ENV-01); independent review of WP-W-05; HIL tests (WP-W-08). Owner: SW lead |
| Review | TBD |

#### RA-02 Toyota safety mode (SC-01, part)

| Field | Content |
|---|---|
| Component, source, owner | `opendbc_repo/opendbc/safety/modes/toyota.h`; upstream commaai/opendbc; fork jherrodthomas/opendbc |
| Version and baseline | opendbc `7993399`; upstream base `229dc70` |
| Intended function; safety relevance | Toyota RX decoding, TX content checks, whitelist, RX set, timeout periods, EPS-fault gate and cruise-main check (reference build). ASIL B‡. SWSRs allocated to U-SAF-TOY (101–110, 201a, 207, 301–305, 402, 405, 512, 518, 705) |
| Origin split | Modified by LionDriver: `toyota_rx_hook`, `toyota_tx_hook`, `toyota_init`, TX/RX tables. LionDriver-authored: `toyota_lka_state_is_fault`, `toyota_cruise_main_check`. Inherited: checksum and quality helpers (WP-W-05 UN-14…UN-17, UN-38, UN-39) |
| Existing development evidence | As RA-01; change records for RX timeout, TX whitelist, EPS fault, cruise-main check, TX rate supervision ([`impact/`](impact/README.md)) |
| Existing verification evidence | `opendbc/safety/tests/test_toyota.py` (31 `def test_` definitions at `7993399`, inherited and LionDriver-added), run as RA-01 in both build variants. HIL tests `panda/tests/hitl/test_12_rx_timeout.py`, `test_13_eps_fault.py`, `test_14_tx_rate.py` exist, not run |
| Operational assumptions | Reference car 2020 Corolla LE TSS2, non-SecOC, LKA torque control, BRAKE_MODULE `0x226`, parameter 73; DBC signal layout of `toyota_nodsu_pt_generated.dbc`; EPS LKA_STATE fault codes reverse-engineered (to be confirmed); nominal rates of `0x262`/`0x1D3` and TX budgets not yet confirmed on reference logs (WP-S-05 OI-7) |
| Known defects and limitations | GAP-01, GAP-02, GAP-03 (EPS status, partly addressed), GAP-04, GAP-44 (EPS factor unchecked outside the reference build), GAP-48 |
| Dependencies | RA-01; panda reference lock (RA-03) for the parameter |
| Gaps | Requirements: signal semantics from reverse-engineered DBC. Verification: no vehicle or HIL evidence; fault set and rates unconfirmed |
| Strategy | Re-verify to the ASIL (T-03) |
| Additional engineering needed | Confirm rates and LKA_STATE codes on reference logs; vehicle and HIL tests; review of the reference-build branches. Owner: SW lead |
| Review | TBD |

#### RA-03 panda firmware units the envelope depends on (SC-02)

| Field | Content |
|---|---|
| Component, source, owner | `panda/board/`: `main.c`, `main_comms.h`, `can_comms.h`, `drivers/{spi,fdcan,can_common,harness,interrupts,registers,simple_watchdog}.h`, `stm32h7/llspi.h`, `sys/{faults,power_saving}.h`, `early_init.h`, `bootstub.c`, `health.h`, and the LionDriver modules `reference_lock.h`, `drivers/{hw_watchdog,heartbeat_monitor,irq_priorities}.h`; upstream commaai/panda; fork jherrodthomas/panda |
| Version and baseline | panda `8aa8671`; upstream base `92eb565` |
| Intended function; safety relevance | Execution platform of the envelope: CAN RX/TX and forwarding, host command handling and reference lock, 100 Hz safety task, heartbeat supervision, IWDG, relay control, fault recording, IRQ priorities, boot signature check. ASIL B‡ for the safety paths. SWSRs allocated to U-PND-* (307, 401a, 407–413, 501–519, 701–711) |
| Origin split | LionDriver-authored: `reference_lock.h`, `hw_watchdog.h`, `heartbeat_monitor.h`, `irq_priorities.h`, `fault_injection.h` (debug only), `safety_task_handler`, `safety_task_timer_init`, `main_loop_progress`. Modified: `set_safety_mode`, `tick_handler`, `main`, `comms_control_handler`, `get_health_pkt`, `set_intercept_relay`, `fault_occurred/recovered`, `enter_stop_mode`. Inherited: SPI, FDCAN, CAN queues, interrupts, registers, bootstub (WP-W-05 UN-18…UN-35, UN-40…UN-44, UN-N1) |
| Existing development evidence | Upstream: none found. LionDriver: WP-W-03, WP-W-05, change records (watchdog, safety-mode lock, fast heartbeat, IRQ priorities); none reviewed |
| Existing verification evidence | Panda MISRA C:2012 in the superproject `safety.yaml` (job "panda MISRA"); panda fork CI `test.yaml` builds debug and release firmware and runs `./test.sh` (`unittest discover -s tests`); LionDriver host tests `tests/{hw_watchdog,reference_lock,heartbeat_monitor,irq_priorities}/` (whether each is collected by that discovery: not confirmed). HIL tests `tests/hitl/test_10…14` exist; not run as recorded evidence. Upstream HIL runs on comma's device pools, which the fork cannot use (GAP-30) |
| Operational assumptions | STM32H725 on the comma panda board; harness relay; SPI to the SoC; release build `RELEASE=1 LIONDRIVER_REFERENCE=1`; LSI frequency and tolerance for the IWDG to be confirmed from the datasheet |
| Known defects and limitations | GAP-08 (faults report-only), GAP-10 (XOR, no sequence counter), GAP-11, GAP-12 (no relay readback), GAP-24/25 (signing, debug default), GAP-43 (partly addressed by the IWDG), GAP-47 (bounds), GAP-49, GAP-50 (partly addressed) |
| Dependencies | RA-01, RA-02 (compiled in); SC-03 headers; arm-none-eabi-gcc (comma-packaged); SCons build flags |
| Gaps | Requirements: back-filled, not reviewed. Architecture: single MCU, no MPU, equal IRQ priorities (WP-W-03 §5.4). Verification: no target timing (safety-task period, WCET, latency not measured), no HIL evidence, no start-up tests |
| Strategy | Re-verify to the ASIL (T-03) for the safety paths; FFI argument for the rest of the firmware (WP-A-02) |
| Additional engineering needed | HIL bench (D-04) and the HIL tests; timing measurements (WP-W-03 §5.4.5); fault reaction (SWSR-502); record CI runs. Owner: SW lead / test lead |
| Review | TBD |

#### RA-04 STM32H7 CMSIS and device headers (SC-03)

| Field | Content |
|---|---|
| Component, source, owner | `panda/board/stm32h7/inc/`; ST and ARM, vendored by upstream panda |
| Version and baseline | As in panda `8aa8671` (not changed by LionDriver in `92eb565..8aa8671`); vendor release version not confirmed |
| Intended function; safety relevance | Register definitions and NVIC access used by all firmware units (ASIL B‡ by use) |
| Existing development evidence | Vendor headers; no LionDriver record |
| Existing verification evidence | Compiled in every build; MISRA analysis excludes or suppresses vendor headers (scope not confirmed here) |
| Operational assumptions | Header revision matches the STM32H725 silicon and reference manual in WP-H-07 |
| Known defects and limitations | None recorded |
| Dependencies | arm-none-eabi-gcc |
| Gaps | No check of the used register definitions against the reference manual |
| Strategy | Re-verify with SC-02 (T-03): review of the used definitions against the reference manual |
| Additional engineering needed | Identify the vendor release; review the definitions used by safety paths (IWDG, TIM4, FDCAN, NVIC, RCC). Owner: SW lead |
| Review | TBD |

#### RA-05 msgq (SC-08)

| Field | Content |
|---|---|
| Component, source, owner | `msgq_repo/`; upstream commaai/msgq; fork jherrodthomas/msgq |
| Version and baseline | `0e266c1` (not initialized in this checkout); drafted sync to `326a9f5` not taken |
| Intended function; safety relevance | Shared-memory publish/subscribe IPC between all host processes, including `card`, `controlsd`, `selfdrived`, `pandad`. QM-SR (data integrity and timeliness of inputs to QM control), QM-CS (GAP-20). No SWSR on the panda side; host SWSRs relying on message freshness (e.g. SWSR-601a) |
| Existing development evidence | Not reviewed (content not available, OI-1) |
| Existing verification evidence | Upstream tests in the msgq repository; whether and where they run for the LionDriver pin: not confirmed |
| Operational assumptions | Single SoC, AGNOS shared memory; all publishers trusted |
| Known defects and limitations | GAP-20 (IPC without authentication), GAP-16 (alive limits) |
| Dependencies | C++ toolchain, Cython, AGNOS kernel |
| Gaps | No requirements on the component; no review; no qualification tests in the LionDriver configuration |
| Strategy | Qualify at QM (T-05) and argue non-interference with the envelope (the envelope bounds any command) |
| Additional engineering needed | Initialize and review at the pin (OI-1); SCQ record (OI-2); decide the drafted sync. Owner: maintainer |
| Review | TBD |

#### RA-06 cereal and Cap'n Proto (SC-09)

| Field | Content |
|---|---|
| Component, source, owner | `openpilot/cereal/**` (LionDriver superproject); pycapnp 2.1.0 and `comma-deps-capnproto` 1.0.1.post103 from `uv.lock` |
| Version and baseline | cereal at `682f184`; library versions as listed |
| Intended function; safety relevance | Schemas and serialization of all host messages, including `pandaState` fields added by LionDriver (`epsFault`, `txRateExceeded`, `watchdogReset`, `requestsRejected`; `openpilot/cereal/log.capnp:582-588`). QM-SR |
| Existing development evidence | Upstream schemas; LionDriver schema changes in the change records |
| Existing verification evidence | Host tests in the superproject `tests.yaml` (scope for cereal not confirmed) |
| Operational assumptions | Same schema version on all processes of one build |
| Known defects and limitations | None specific recorded; capnp code generator at TCL (GAP-34) |
| Dependencies | capnp compiler, Python, C++ |
| Gaps | No requirements on the component; no qualification record |
| Strategy | Qualify at QM (T-05) |
| Additional engineering needed | SCQ record; tool classification of the capnp compiler (WP-P-07). Owner: maintainer |
| Review | TBD |

#### RA-07 rednose (SC-10)

| Field | Content |
|---|---|
| Component, source, owner | `rednose_repo/`; upstream commaai/rednose; fork jherrodthomas/rednose |
| Version and baseline | `8671c17` (not initialized in this checkout) |
| Intended function; safety relevance | EKF library used by `locationd` (pose and calibration inputs to control). QM-SR |
| Existing development evidence | Not reviewed (OI-1) |
| Existing verification evidence | Upstream tests in the rednose repository; where they run for the pin: not confirmed |
| Operational assumptions | Sensor inputs from the comma device; numerical behaviour of the generated code |
| Known defects and limitations | GAP-17 (locationd checks masked during model fallback) |
| Dependencies | SymPy code generation, numpy, C++ |
| Gaps | No requirements on the component; no review; no qualification tests |
| Strategy | Qualify at QM (T-05); the envelope bounds the effect on actuation |
| Additional engineering needed | Initialize and review (OI-1); SCQ record. Owner: maintainer |
| Review | TBD |

#### RA-08 tinygrad runtime and compiled models (SC-11)

| Field | Content |
|---|---|
| Component, source, owner | `tinygrad_repo/` (tinygrad project, not forked) and model files under `openpilot/selfdrive/modeld/models/` (comma, LFS) |
| Version and baseline | tinygrad 0.14.0 at `d3f09c9` (not initialized in this checkout); model LFS oids at `682f184` |
| Intended function; safety relevance | Compiles and runs the driving and driver-monitoring models (`modeld`, `dmonitoringmodeld`). QM-SR; AI component under WP-W-10 |
| Existing development evidence | Upstream model release notes only; no training-data or ODD specification (GAP-22) |
| Existing verification evidence | Model replay in the superproject CI cannot fail (GAP-45); no LionDriver model evaluation recorded |
| Operational assumptions | comma device GPU; model and runtime versions matched |
| Known defects and limitations | GAP-22 (no uncertainty gating, pickle deserialisation, no model hash check), GAP-45, GAP-17, GAP-34 (compiler at TCL) |
| Dependencies | GPU drivers on AGNOS, numpy |
| Gaps | Requirements (WP-W-10), verification (model regression), tool qualification |
| Strategy | Qualify at QM (T-05) with WP-W-10; the envelope bounds the effect on actuation |
| Additional engineering needed | Initialize and review; model hash check; regression tests that can fail. Owner: TBD (WP-W-10) |
| Review | TBD |

#### RA-09 opendbc car port and CAN parser (SC-04, SC-05)

| Field | Content |
|---|---|
| Component, source, owner | `opendbc_repo/opendbc/car/**` (Toyota), `opendbc_repo/opendbc/can/**`; upstream commaai/opendbc via the fork |
| Version and baseline | opendbc `7993399`; unchanged by LionDriver since `229dc70` |
| Intended function; safety relevance | Host-side parse of vehicle CAN, car state, and construction of control frames sent to the envelope. QM-SR; its outputs are bounded by RA-01/RA-02 |
| Existing development evidence | None found upstream |
| Existing verification evidence | opendbc fork CI `tests.yml` (car tests, car diff, model tests) on GitHub-hosted runners |
| Operational assumptions | Correct fingerprinting of the reference car (SWSR-620, not impl) |
| Known defects and limitations | GAP-19, GAP-46 (host side of the dropped frame) |
| Dependencies | SC-09, SC-12 |
| Gaps | No qualification record; fingerprint lock |
| Strategy | Qualify at QM (T-05); argue that the envelope bounds every frame it sends |
| Additional engineering needed | SCQ record; confirm OI-6 (no SC-04/SC-05 code on the MCU). Owner: SW lead |
| Review | TBD |

## 5. Interfaces between the QM stack and the ASIL path

These interfaces decide whether a QM component can defeat the envelope, and are the main input to [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md). Code references at panda `8aa8671`.

| Interface | QM side | ASIL side | Known issue |
|---|---|---|---|
| SPI transport | `openpilot/selfdrive/pandad/spi.cc` on AGNOS kernel SPI | `panda/board/drivers/spi.h` | 8-bit XOR, no sequence counter (GAP-10) |
| Safety mode / param | `openpilot/selfdrive/pandad/panda_safety.cc` | `panda/board/main_comms.h` cmd `0xdc`, gated by `panda/board/reference_lock.h` in the reference build | Unauthenticated (GAP-09); in the reference build only the locked configuration is accepted, in other builds any mode at any time |
| TX CAN frames | `card` → `pandad` | `safety_tx_hook` (opendbc `7993399`) | Bounded by envelope checks; per-ID rate supervision in the reference build |
| Heartbeat | `pandad` | `panda/board/main.c`, `panda/board/drivers/heartbeat_monitor.h` | Shows pandad liveness, not control loop (GAP-10); authority revoked after 0.3 s without it |
| Health report | `pandad` → `pandaState` | `panda/board/main_comms.h` `get_health_pkt` | Report only; no general reason code (SWSR-108a) |
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
| OI-7 | Review the reuse-assessment records RA-01…RA-09 (§4.5) and resolve their "not confirmed" statements |
| OI-8 | Add reuse-assessment records for the remaining safety-relevant components of [`safety-relevant-paths.txt`](safety-relevant-paths.txt) (host processes in the actuation path, AGNOS, acados) |
