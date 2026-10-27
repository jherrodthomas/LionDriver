# WP-W-09 Safety-Related Configuration and Calibration Data

| Field | Value |
|---|---|
| Work product | WP-W-09 Safety-related configuration and calibration data (car params, fingerprints, limits, model weights) |
| Standard reference | ISO 26262-6:2018 Annex C (software configuration; calibration data); ISO 26262-6:2018 §6, §9 (requirements on and verification of data); ISO 26262-8:2018 §7 (configuration management); ISO/PAS 8800:2024 (model as configuration item, informative); ASPICE 4.0 SWE.3 |
| Version | 0.7 (RX timeout bound ≤ 0.162 s, was ≤ 0.16 s, as WP-S-04 v0.21 T-01 (161.5 ms: 5 periods of 30.3 ms plus one 10 ms task period); no requirement, budget or verdict changed; 2026-10-27). 0.6 (DVR-02 reworded to match SWSR-512, OI-8 closed (register DQ-073 A); OI-4 decided: learned values frozen for most validation runs plus a learning-on campaign (register DQ-072 A); 2026-10-19). 0.5.1 (CD-03 EPS-fault siren: persistence 70 ticks, panda `bf8102a`, DQ-048; 2026-10-17). 0.5 (merge of PR #47 software alignment with the base; CD-03 gains the EPS-fault and heartbeat-loss siren constants; 2026-10-13). It carries PR #47's draft, numbered 0.2 there: RR-2026-009 F-19: CD-01…CD-05, CD-22 and DVR-01/02 updated to the reference lock and the current pins; `LIONDRIVER_REFERENCE` inventoried as CD-23 with DVR-23; "Applies to" added to every CD and DVR item; F-28: author. History on the base: 0.4 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.3 (reference configuration named by generation, E210; 2026-10-12). 0.2 (status update 2026-10-12: CD-01, CD-03, CD-04 and §5 updated to the integrated LionDriver changes at panda `b790fca`, opendbc `7993399`; DVR-01/02 status. Nothing verified on hardware). 0.1: initial draft at `8b8c6ae` |
| Status | Draft |
| ASIL / scope | Up to ASIL C (data that configures or parameterises the envelope E-03); QM / SOTIF / PAS 8800 for host data |
| Author | Assurance team (AI-assisted draft, Claude) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `682f184` (opendbc `7993399`, panda `8aa8671`); the siren constants in CD-03 at panda `b790fca` and `c33343b` (current pins: panda `c33343b`, opendbc `273f44e`). The base's status update used `bf6ce8c` (panda `b790fca`, opendbc `7993399`). Earlier: `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

> [!NOTE]
> **Status at `682f184` (opendbc `7993399`, panda `8aa8671`).** This document describes the code at `8b8c6ae` unless a statement names a later pin. Safety mechanisms integrated since then (hardware watchdog and 100 Hz safety task, RX timeout, TX whitelist, safety-mode lock, 0.3 s heartbeat, IRQ priorities, EPS fault, cruise-main check, TX rate supervision) are recorded in the [WP-W-02](WP-W-02-software-safety-requirements.md) Baseline column and the [change records](../07-supporting/impact/README.md). The sections of this document that still describe the earlier behaviour are listed in [RR-2026-009](reviews/RR-2026-009.md) and are to be updated ([WP-M-14 §2.3](../01-management/WP-M-14-iso26262-6-implementation-specification.md#23-pre-entry-engineering-track) P-03).

## 1. Purpose and scope

ISO 26262-6 Annex C treats configuration data (selecting a variant or behaviour of the software) and calibration data (adapting the software's behaviour by values) as part of the software that must be specified, verified and controlled with the same rigour as code of the same ASIL. This document:

1. lists every data item that can change the safety-relevant behaviour of the LionDriver reference configuration (Toyota Corolla, 12th generation (E210), TSS 2.0, `TOYOTA_COROLLA_TSS2`, openpilot longitudinal, comma device with panda);
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
| ASIL | ASIL of the requirement the item parameterises. An item consumed by E-03 inherits the envelope ASIL (C provisional). An item produced by QM and consumed by E-03 is an FFI concern ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) |
| Owner | Role accountable for the value and its rationale |
| Applies to | The configurations whose behaviour the item sets ([WP-M-14 §7](../01-management/WP-M-14-iso26262-6-implementation-specification.md#7-multi-vehicle-configuration-management)): **CFG-001 reference build only** (compiled only with `LIONDRIVER_REFERENCE`, CD-23); **all Toyota configurations** (Toyota safety mode or Toyota port code, every build); **`TOYOTA_COROLLA_TSS2` platform** (all variants of that platform); **all configurations (shared code)** (generic code used by every brand and every build). An item marked shared is also used by configurations outside the claim; evidence for it covers another configuration only after an applicability analysis (WP-M-14 §7.2) |

## 3. Inventory summary

| ID | Item | Type | Binding | Consumer | ASIL | Owner | Applies to |
|---|---|---|---|---|---|---|---|
| CD-01 | Safety model and safety parameter (`safetyParam` = EPS scale 73 + flag bits) | CFG + CAL | Fingerprint (host) → SoC command `0xdc` | E-03 | C | Safety engineer (envelope) | Reference lock (only TOYOTA with parameter 73): CFG-001 reference build only. Decoding in `toyota_init`: all Toyota configurations |
| CD-02 | Toyota envelope limit constants (`toyota.h`) | CAL | Build | E-03 | C | Safety engineer (envelope) | All Toyota configurations (one constant set for every Toyota platform) |
| CD-03 | Envelope and firmware timing constants (RX timeouts, RT interval, safety task, heartbeat, watchdog, TX rate, EPS fault set, cruise-main tolerance) | CAL | Build | E-03 | C | Safety engineer (envelope) | Per constant (§4.1): all configurations (shared code: `safety.h`, `declarations.h`, `lateral.h`, panda `main.c` and drivers, used by every brand); all Toyota configurations (5-period RX timeout); CFG-001 reference build only (TX rate, LKA_STATE set, cruise-main) |
| CD-04 | Toyota RX check table and TX whitelist | CFG | Build | E-03 | C | Safety engineer (envelope) | Base tables and the `0x344`/DSU removal: all Toyota configurations. `0x262`/`0x1D3` RX checks and `0x411` refusal: CFG-001 reference build only |
| CD-05 | panda firmware build configuration (`RELEASE`/`ALLOW_DEBUG`, certificate) | CFG | Build | E-03 | C + CS | Release manager | All configurations (every panda build) |
| CD-06 | Host controller limits `CarControllerParams` | CAL | Build (source) | E-01 | QM (must stay below CD-02, FSR-01.14) | Vehicle port owner | All Toyota configurations (`values.py` shared by every Toyota platform) |
| CD-07 | Platform configuration (flags, DBC choice, car specs) | CFG + CAL | Build + Fingerprint | E-01 (and CD-01 derivation) | QM; flags that set CD-01 bits: C | Vehicle port owner | `TOYOTA_COROLLA_TSS2` platform (CFG-001 is one of its variants) |
| CD-08 | Interface tuning (`interface.py`: delays, limit timer, longitudinal mode, accel limit flag) | CFG + CAL | Fingerprint | E-01 | QM | Vehicle port owner | All Toyota configurations (values chosen per platform) |
| CD-09 | Offline torque model (`torque_data/*.toml`) | CAL | Build | E-01 | QM | Vehicle port owner | `TOYOTA_COROLLA_TSS2` platform (row in a table shared by all brands) |
| CD-10 | Fingerprints and FW versions (`fingerprints.py`, fuzzy matching) | CFG | Fingerprint | E-01 → CD-01 | Selection result feeds C | Vehicle port owner | All Toyota configurations (matching code `fw_versions.py`: all configurations, shared code) |
| CD-11 | DBC files (Toyota) | CFG | Build | E-01 | QM | Vehicle port owner | Toyota configurations that use these DBCs (several Toyota platforms) |
| CD-12 | Params defaults and user/debug settings (`params_keys.h`) | CFG | Build default + User/Runtime | E-01 | QM (SR-Q); some affect FSR-02.08 | Product owner | All configurations (shared host code) |
| CD-13 | Cached vehicle identity and CarParams (`CarParamsCache`, `CarParams`, `CarParamsPersistent`, `CarParamsPrevRoute`) | CFG | Runtime | E-01 → CD-01 | Feeds C | Vehicle port owner | All configurations (shared host code) |
| CD-14 | ML model weights (driving, DM; small and big variants) | MDL | Build (LFS) | E-02 | QM (PAS 8800 / SOTIF) | ML owner | All configurations (shared models) |
| CD-15 | Driver-monitoring policy thresholds (`policy.py`) | CAL | Build | E-01/DM | QM (SOTIF misuse measure, FSC §7) | DM owner | All configurations (shared host code) |
| CD-16 | Camera calibration (`calibrationd`, `CalibrationParams`) | LRN | Runtime | E-01, E-02 | QM | Localization owner | All configurations (shared host code) |
| CD-17 | Vehicle model learning (`paramsd`, `LiveParametersV2`) | LRN | Runtime | E-01 | QM | Controls owner | All configurations (shared host code) |
| CD-18 | Lateral torque learning (`torqued`, `LiveTorqueParameters`) | LRN | Runtime | E-01 | QM | Controls owner | Shared host code; learning used only for brands in `ALLOWED_CARS` (toyota, hyundai, rivian, honda, volkswagen) with torque control (`openpilot/selfdrive/locationd/torqued.py:37, 76`) |
| CD-19 | Actuator delay learning (`lagd`, `LiveDelay`) | LRN | Runtime | E-01 | QM | Controls owner | All configurations (shared host code) |
| CD-20 | Host monitoring thresholds (excessive actuation, controller lateral limits) | CAL | Build | E-01 | QM | Controls owner | All configurations (shared host code) |
| CD-21 | Model storage location (`.lfsconfig`) | CFG | Build | Supply of CD-14 | QM / CS | Configuration manager | All configurations |
| CD-22 | Speed-dependent torque bound table τ_max(v) (future, TSR-102) | CAL | Build | E-03 | C | Safety engineer (envelope) | CFG-001 (derived on the reference vehicle); placed unguarded in `toyota.h` it would apply to all Toyota configurations |
| CD-23 | Reference build switch `LIONDRIVER_REFERENCE` | CFG | Build | E-03 | C | Release manager | CFG-001 reference build only (by definition) |

## 4. Item details

Each entry gives: current value and source; what it affects; where it is verified today; protection (integrity/plausibility) today; change control; gaps.

### 4.1 Envelope data (E-03)

**CD-01 Safety model and safety parameter**

| Aspect | Content |
|---|---|
| Value (reference configuration) | `safetyModel = toyota`; `safetyParam = 73` (`0x0049`): low byte EPS torque factor 73 % (`EPS_SCALE` default, `opendbc_repo/opendbc/car/toyota/values.py:588-589`; set at `interface.py:27-28`). Flag bits (byte 2): `ALT_BRAKE 0x100`, `STOCK_LONGITUDINAL 0x200`, `LTA 0x400`, `SECOC 0x800` (`values.py:53-58`) — **none set** for the reference configuration (`interface.py:30-41, 105-111`). `alternativeExperience = 0` (`openpilot/selfdrive/car/card.py:110`) |
| Decoding in envelope | `toyota_init` (opendbc `7993399`, `opendbc_repo/opendbc/safety/modes/toyota.h:459-563`): flags via `GET_FLAG` (`:489-491`); SECOC flag parsed only under `ALLOW_DEBUG` (`:484-487`); `toyota_dbc_eps_torque_factor = param & TOYOTA_EPS_FACTOR` (`:492`) **with no range check, in every build** (SWSR-104a, GAP-44) |
| Effect | EPS factor scales measured torque used by the measured-torque check (`toyota.h:186`, FSR-01.03). Flags select the TX whitelist (`toyota.h:500-512`), the RX checks (`:514-540`), the TX rate rows (reference build, non-SecOC, `:545-560`) and the lateral path (`:366`, `:424`). A wrong STOCK_LONGITUDINAL bit changes the TX set; a wrong EPS factor loosens or tightens the ±350 tracking bound |
| Path | Host fingerprints the car (CD-10) → `CarParams` written to Params by `card.py:146-150` → `pandad` reads `CarParams` and sends model/param to panda (`openpilot/selfdrive/pandad/panda_safety.cc:56-70`) → panda `0xdc` (panda `8aa8671`, `panda/board/main_comms.h:243-245`), in the reference build first through the request gate (`main_comms.h:74-79`, `board/reference_lock.h:18-62`) |
| Verified today | Host side: `selfdrived` raises `controlsMismatch` if panda-reported model/param/alt-experience differ from `CarParams` for > 10 s (`openpilot/selfdrive/selfdrived/selfdrived.py:351-366`). Envelope side: tests set the param explicitly (`test_toyota.py:503-505`); `test_models.py` sets `safetyConfigs[-1]` per route (`opendbc_repo/opendbc/car/tests/test_models.py:186-190`). Reference lock: host unit tests `panda/tests/reference_lock/test_reference_lock.py:77-131` (pass, per the [mode-lock change record](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §4); HIL test `panda/tests/hitl/test_11_reference_lock.py` **not run**. Not verified on hardware |
| Protection today | **Reference build** (`LIONDRIVER_REFERENCE`, CD-23): the panda lock admits `0xdc` TOYOTA only with `param2 == 73` (16-bit compare, so no flag bits) and, once TOYOTA is active, only NOOUTPUT or SILENT (panda `8aa8671`, `board/reference_lock.h:14, 22-28`); `0xdf` (alternative experience) is refused in every mode (`:30-32`), so it stays at its reset value 0. A refused request is mapped to `0x00` and has no effect; it is counted in the health packet (`main_comms.h:27-31, 74-79`). Implemented, not verified on hardware (SWSR-512, SWSR-512a). **Every other build**: no protection — any EPS factor 0–255 is accepted (including 0), unknown flag bits are ignored, and the SoC can change mode/param at any time without authentication (GAP-09). In all builds `toyota_init` itself has no range check (`toyota.h:492`; SWSR-104a open). Host check is QM and slow (10 s) |
| Change control | `values.py`/`interface.py` are SR-Q; `toyota.h` and `panda/board/reference_lock.h` are SR-A ([WP-P-01 §4.2](../07-supporting/WP-P-01-configuration-management-plan.md#42-globs)) |
| Applies to | Lock: CFG-001 reference build only. Decoding and the missing range check in `toyota_init`: all Toyota configurations |
| Gaps | GAP-09 and GAP-44 are mitigated in the reference build by the panda lock (not verified on hardware) and remain open for every other build; SWSR-104a (range check in the envelope) not implemented. DVR-01, DVR-02 |

**CD-02 Toyota envelope limit constants**

| Constant | Value | Source (opendbc `7993399`) |
|---|---|---|
| `max_torque` | 1500 raw | `opendbc_repo/opendbc/safety/modes/toyota.h:270` |
| `max_rate_up` / `max_rate_down` | 15 / 25 raw per frame | `toyota.h:271-272` |
| `max_torque_error` | 350 raw | `toyota.h:273` |
| `max_rt_delta` | 450 raw per `MAX_RT_INTERVAL` | `toyota.h:274` |
| Steer-request cut | `min_valid_request_frames` 17, `max_invalid_request_frames` 1, `min_valid_request_rt_interval` 162 ms | `toyota.h:279-282` |
| LTA angle limits (not used in ref. config) | `max_angle` 1657, rate lookups | `toyota.h:285-298` |
| LTA torque limits (not used) | 1500 / 150 | `toyota.h:300-301` |
| `max_accel` / `min_accel` | 2000 / −3500 (0.001 m/s²) | `toyota.h:304-307` |

| Aspect | Content |
|---|---|
| Effect | Directly bound actuation (FSR-01.01…01.04, FSR-03.01, FSR-04.01). In the reference build the LKA torque checks are skipped while the EPS fault gate refuses the frame (`toyota.h:425-434`, CD-03) |
| Verified today | Toyota and common safety tests (WP-W-06 §4.1); test classes copy the same constants (`test_toyota.py:490-501`), so a wrong value passes (GAP-14) |
| Protection | Compiled into signed firmware (integrity = firmware integrity, CD-05). No physical rationale (GAP-04) |
| Change control | SR-A; independent review; WP-W-06 VS-UV-02…07 |
| Applies to | All Toyota configurations (the constants are local to `toyota_tx_hook` and do not depend on the platform or the build) |
| Gaps | GAP-04 (rationale), GAP-14 (trace). DVR-03, DVR-04 |

**CD-22 Speed-dependent torque bound τ_max(v) (future)**

TSR-102 in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) requires a speed-dependent torque bound derived on the reference vehicle. It does not exist at the baseline: `dynamic_max_torque` is not set for Toyota (opendbc `7993399`, `modes/toyota.h:269-283`), although the mechanism exists in `lateral.h:67`. When introduced it is ASIL calibration data of E-03 and needs: a derivation record (measurement data, method, margins), a monotonicity and range check at build time, unit tests at every breakpoint and between breakpoints (WP-W-06 VS-UV-02), and SR-A change control. Applies to: CFG-001 (derived on the reference vehicle); a table placed in `toyota.h` without a `LIONDRIVER_REFERENCE` guard would apply to all Toyota configurations. DVR-22.

**CD-03 Envelope and firmware timing constants**

Values are the constants in the code at opendbc `7993399` and panda `8aa8671`. Derived thresholds (e.g. 5 periods of a message) are arithmetic on those constants; **no timing value below has been measured** (detection latencies and the IWDG tolerance are not measured).

| Constant | Value | Source | Applies to |
|---|---|---|---|
| `MAX_RT_INTERVAL` | 250 000 µs | `opendbc_repo/opendbc/safety/declarations.h:83`; used by `lateral.h:92, 158, 167, 180, 188` | All configurations (shared code, every brand) |
| RX timeout, Toyota | 5 nominal periods, no 1 s floor (`TOYOTA_RX_TIMEOUT_PERIODS`): `0xAA` 83 Hz → 5 × 12 048 µs; `0x260` 50 Hz → 100 ms; `0x1D2` 33 Hz → 5 × 30 303 µs; `0x226` 40 Hz → 125 ms; reference build also `0x262` 25 Hz → 200 ms and `0x1D3` 33 Hz → 5 × 30 303 µs | `toyota.h:83, 543`; evaluation `safety.h:373-386`; frequencies `toyota.h:46-48, 56-60, 65-69` | All Toyota configurations (not under `LIONDRIVER_REFERENCE`); `0x262`/`0x1D3` CFG-001 reference build only. The mechanism (`rx_timeout_periods`, `safety.h:382-384`) is shared code; no other brand mode sets it |
| RX timeout, other modes | max(10 × expected period, 1 s) | `safety.h:374-381` | All configurations whose mode does not set `rx_timeout_periods` (every brand except Toyota) |
| Engagement gate on RX checks | A PCM rising edge grants controls only if no RX check is lagging or invalid at that moment | `safety.h:388-401, 601-610` | Modes with `rx_timeout_periods` > 0: all Toyota configurations |
| Safety task | 100 Hz (`SAFETY_TASK_FREQ`), TIM4, 10 ms period; runs `safety_tick`, the heartbeat monitor and the IWDG feed | `panda/board/stm32h7/stm32h7_config.h:40-41`; `board/drivers/timers.h:30-33`; `board/main.c:128-144` | All configurations (every panda build, all safety modes) |
| Safety task rate fault | More than 110 calls (`SAFETY_TASK_FREQ + 10`) within one interrupt-timer second → `FAULT_INTERRUPT_RATE_TICK` (the same fault code as the 8 Hz tick) | `main.c:352`; check `board/drivers/interrupts.h:31-37`, counters reset `:49-61` | All configurations (every panda build) |
| Heartbeat authority revocation | No `0xf3` heartbeat for 30 safety-task ticks (0.3 s) in a car safety mode → `controls_allowed = false` every tick until the next heartbeat | `board/drivers/heartbeat_monitor.h:15, 25-30`; `main.c:134-137`; reset on `0xf3` `main_comms.h:297-301` | All configurations (every panda build, every car safety mode) |
| Heartbeat engaged mismatch | `controls_allowed` without host `heartbeat_engaged` for 3 consecutive 1 Hz ticks → controls cleared | `main.c:225-233` | All configurations (every panda build) |
| Heartbeat loss → SILENT | 5 s with ignition, 2 s without (1 Hz counter) | `main.c:115-117, 235-256` | All configurations (every panda build); SWSR-510 (≤ 2 s) not met |
| Relay-malfunction grace | `safety_mode_cnt > 1` (1–2 s, 1 Hz counter) | `safety.h:448-456`; counter `main.c:282` | All configurations (shared code) |
| Hardware watchdog (IWDG1) | Prescaler /4 (`PR` 0), reload 719, window 679: nominal timeout 90 ms and closed window 5 ms after a feed at f_LSI = 32 kHz (computed in the source comment; LSI tolerance **not confirmed**). Started the first time the relay is driven; fed from the 100 Hz task only if the main loop ran since the previous feed; first tick after start skipped | `board/drivers/hw_watchdog.h:20-37, 45-76`; start `board/drivers/harness.h:16-21`; `stm32h7_config.h:48` | All configurations (every panda build) |
| TX rate supervision | Sliding window of two 125 ms halves (`TX_RATE_WINDOW_US` 250 000 µs); budget per ID = ⌈f × 0.3⌉ + 1 + burst frames per window; a frame over budget is rejected before the brand hook; 3 rejected frames in a half-window while controls are allowed revoke controls and set `safety_tx_rate_exceeded` | `safety.h:243-281, 290-299`; reset `safety.h:558-562` | CFG-001 reference build only (code compiled only with `LIONDRIVER_REFERENCE`) |
| TX rate rows, Toyota (non-SecOC) | `0x2E4` 100 Hz burst 5 (budget 36); `0x191` 50/3 (19); `0x343` 33/3 (14); `0x412` 5/4 (7); `0x1D2` 1/2 (4); `0x283` 1/2 (4); `0x750` 5/2 (5) | `toyota.h:545-560`; budgets from `safety.h:263` | CFG-001 reference build only |
| EPS fault set (`EPS_STATUS.LKA_STATE`) | Codes 0, 3, 9, 11, 17, 21, 25 = fault; while set, `0x2E4` with torque ≠ 0 or steer request is refused | `toyota.h:99-116`; decode `:236-240`; gate `:425-434` | CFG-001 reference build only (code set reverse-engineered, to be confirmed for the reference EPS firmware, `toyota.h:94-95`) |
| Cruise-main tolerance | `CRUISE_ACTIVE` with `MAIN_ON` = 0: refused at once when cruise becomes active; revokes controls after 150 000 µs of disagreement when main goes off | `toyota.h:118-144`; inputs `:241-249`; reset `:493-497` | CFG-001 reference build only (not for alt-brake cars) |
| EPS-fault siren (panda `b790fca`) | `EPS_FAULT_SIREN_PERSIST_TICKS` 70 (0.7 s persistence once seen while engaged; DQ-048, panda `bf8102a`; 100 before), `EPS_FAULT_SIREN_HOLD_TICKS` 300 (3 s hold); speaker on odd 8 Hz ticks, worst case ≈ 0.96 s after the fault onset | `panda/board/drivers/eps_fault_siren.h:17-18` | All configurations (compiled in every build); only the reference build sets `safety_eps_fault` |
| Heartbeat-loss siren (panda `c33343b`) | `HEARTBEAT_SIREN_HOLD_TICKS` 300 (3 s hold from the 0.3 s revocation of granted authority); audible ≈ 0.56 s after the last heartbeat worst case | `panda/board/drivers/heartbeat_siren.h:17` | All configurations (every panda build) |

Verified today (unit level, host): `test_safety_tick` (`common.py:1208`); `test_rx_timeout_5_periods`, `test_no_engagement_with_invalid_rx_checks`, `test_rx_timeout_5_periods_each_msg` (`test_toyota.py:369-429`); `test_tx_rate_*` (`test_toyota.py:128, 135, 147, 163, 183, 208, 228`); `test_cruise_active_with_main_off` (`:263`); `test_eps_fault_blocks_lka` (`:309`); panda host tests `panda/tests/heartbeat_monitor/`, `panda/tests/hw_watchdog/`. The opendbc tests run in both variants in CI (`.github/workflows/safety.yaml:37-43`). HIL tests `panda/tests/hitl/test_10_hw_watchdog.py`, `test_12_rx_timeout.py`, `test_13_eps_fault.py`, `test_14_tx_rate.py` exist and have **not been run** ([change records](../07-supporting/impact/README.md)). The heartbeat-loss SILENT path and the safety task rate fault have no unit test. Nothing is verified on hardware. The FSC §8 budgets are not yet shown to be met (GAP-06; latencies not measured). Change control SR-A. DVR-03.

*Status 2026-10-12:* the RX timeout now has `test_rx_timeout_5_periods` and `test_rx_timeout_5_periods_each_msg` (`test_toyota.py`); the panda constants have host tests (`panda/tests/heartbeat_monitor`, `hw_watchdog`, `eps_fault_siren`; since 2026-10-13 also `heartbeat_siren`); the TX rate budgets have `test_tx_rate_*`. On paper the RX timeout (≤ 0.162 s) and heartbeat (0.3 s) now fit the FSC §8 budgets; none is verified on hardware (HIL D-04). The constants still lack the requirement IDs, tolerances and rationale of DVR-03.

**CD-04 Toyota RX check table and TX whitelist**

| Aspect | Content |
|---|---|
| Value (opendbc `7993399`) | RX, LKA non-SecOC non-alt-brake (`TOYOTA_RX_CHECKS(false)`, `toyota.h:46-48, 65-69`, selected `:527-536`): `0xAA` 83 Hz (no checksum, no counter, wheel-speed fault bits checked, `:166-175`), `0x260` 50 Hz (checksum, no counter, quality ignored), `0x1D2` 33 Hz (checksum, no counter), `0x226` 40 Hz (no checksum, no counter). Reference build adds `0x262` EPS_STATUS 25 Hz and `0x1D3` PCM_CRUISE_2 33 Hz (checksum, no counter, `:50-60`). Timeout 5 periods (CD-03). TX: `TOYOTA_LONG_TX_MSGS` (`:28-39, 468-470`, selected `:507-511`): `0x191`, `0x412`, `0x1D2` (`:6-7`), `0x2E4`, `0x343` (`:9-12`), `0x283` zero payload only (`:33`, check `:347-354`), `0x750` tester present only (`:37`, check `:447-454`), `0x343` with relay check (`:39`); `0x411` PCS_HUD only outside the reference build (`:19-26`). **Removed in every build:** `0x344` PRE_COLLISION_2, the DSU bus-0 messages `0x2E6`, `0x2E7`, `0x33E`, `0x365`, `0x366`, `0x4CB` and the DSU bus-1 set (`:30-32`; [TX-whitelist change record](../07-supporting/impact/change-2026-10-12-opendbc-toyota-tx-whitelist.md), SWSR-705) |
| Effect | Defines which inputs are integrity-checked and which outputs the SoC may command (FSR-01.06, FSR-07.02) |
| Verified today | `test_rx_hook` (checksum, `test_toyota.py:461`), `test_block_aeb` (`:438`), `test_pcs_and_dsu_messages_blocked` (`:91-99`), `test_pcs_hud` (`:84-89`, refused in the reference variant), `test_reference_rx_checks` (`:349`), `test_spam_can_buses` (`common.py:937`); unit level only, not verified on hardware |
| Protection | Firmware integrity only |
| Applies to | Base RX and TX tables and the `0x344`/DSU removal: all Toyota configurations (openpilot longitudinal, non-SecOC, for the TX set). `0x262`/`0x1D3` RX checks and the `0x411` refusal: CFG-001 reference build only |
| Gaps | GAP-01 (no counters on any Toyota RX message). FSC OI-5 resolved in code: `0x344` removed in every build, `0x411` refused in the reference build (D-1); not verified on hardware |

**CD-05 panda firmware build configuration**

| Aspect | Content |
|---|---|
| Value (panda `8aa8671`) | Default `BUILD_TYPE = "DEBUG"`, adds `-DALLOW_DEBUG` and signs with the committed debug key unless `RELEASE` and `CERT` are set (`panda/SConscript:12-20`); version string `<BUILDER>-<git8>-<type>` (`SConscript:36-41`, `BUILDER = "DEV"` line 8). `LIONDRIVER_REFERENCE` is a separate switch (CD-23, `SConscript:22-26`); bench fault-injection hooks (`FAULT_INJECTION`) are allowed in DEBUG builds only (`SConscript:28-31`) |
| Effect | `ALLOW_DEBUG` registers the debug safety modes (opendbc `7993399`, `safety.h:489-498`) and enables SecOC flag parsing (`toyota.h:484-487`); debug key acceptance in the bootstub (GAP-25) |
| Verified today | panda CI builds debug and release (release with the **debug** cert, `panda/.github/workflows/test.yaml:25-28`); no check that an installed device runs a RELEASE build |
| Protection | Bootstub signature check (RSA-1024/SHA-1, GAP-24) |
| Change control | `panda/SConscript` is SR-A; release procedure [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| Applies to | All configurations (every panda build) |
| Gaps | GAP-24, GAP-25. DVR-05 |

**CD-23 Reference build switch `LIONDRIVER_REFERENCE`**

| Aspect | Content |
|---|---|
| Value | Environment variable `LIONDRIVER_REFERENCE` at build time; when set, `panda/SConscript:22-26` adds `-DLIONDRIVER_REFERENCE` to the firmware flags (panda `8aa8671`). The superproject build includes `panda/SConscript` (`SConstruct:272`), so the same variable applies to a device build. *On the base (LionDriver #36, merged in v0.5):* the top-level `SConstruct` sets `LIONDRIVER_REFERENCE=1` around `SConscript(['panda/SConscript'])` unless the variable is set, so a device build from LionDriver is a reference build by default; `LIONDRIVER_REFERENCE=` (empty) opts out ([mode-lock change record](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §6). The configuration under assessment is the reference release build **`RELEASE=1 LIONDRIVER_REFERENCE=1`** (`SConscript:22-24`; `RELEASE` also needs `CERT`, CD-05). It is not verified on hardware. A DEBUG build with `LIONDRIVER_REFERENCE=1` also compiles (HIL bench) but keeps `ALLOW_DEBUG` |
| What it selects (code compiled only with the define) | panda: the request gate (`board/reference_lock.h:13-62`, applied `board/main_comms.h:74-79`): `0xdc` only SILENT, NOOUTPUT, ELM327 or TOYOTA with parameter 73, and only NOOUTPUT/SILENT once TOYOTA is active; `0xdf` refused; `0xd1` softloader entry and `0xc5`, `0xd8`, `0xdb`, `0xde`, `0xe5`–`0xe8`, `0xf1`, `0xf9`, `0xfc` refused in a car mode; rejected-request count in the health packet (`main_comms.h:27-31`). opendbc (compiled into the firmware): RX set adds `0x262` and `0x1D3` (`toyota.h:56-63`); EPS `LKA_STATE` fault gate (`toyota.h:91-116, 236-240, 425-434`); cruise-main check (`toyota.h:118-145, 241-249, 493-497`); `0x411` removed from the TX whitelist (`toyota.h:22-26`); TX rate supervision (`safety.h:243-281, 290-299, 558-562`; Toyota rows `toyota.h:545-560`) |
| What it does not select | In every build: 5-period Toyota RX timeout and the engagement gate (`toyota.h:83, 543`; `safety.h:373-401`), `0x344`/DSU removal (`toyota.h:28-39`), 100 Hz safety task, 0.3 s heartbeat revocation and the IWDG (panda `main.c:128-144`, `heartbeat_monitor.h`, `hw_watchdog.h`) |
| Where it is set and tested | Firmware: `panda/SConscript:22-26` (environment of the person or job that builds). Unit tests: `opendbc_repo/opendbc/safety/tests/libsafety/libsafety_py.py:32-34` compiles libsafety with the define when `LIONDRIVER_REFERENCE=1`; CI runs the opendbc safety tests in that variant (`.github/workflows/safety.yaml:39-43`). MISRA: `panda/tests/misra/test_misra.sh:67-68` (cppcheck with the define). panda host tests `panda/tests/reference_lock/` compile the gate with the define. HIL tests skip unless `REFERENCE_BUILD=1` (e.g. `panda/tests/hitl/test_11_reference_lock.py:27`). Device build: the top-level `SConstruct` sets it by default (LionDriver #36), which also exports `liondriver_reference` so that `pandad` is built with the host check (LionDriver #41) |
| Effect | A firmware built with it refuses every car other than the reference configuration ([mode-lock change record](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §3); a firmware built without it lacks the lock, the reference RX set, the EPS fault gate, the cruise-main check, the `0x411` refusal and TX rate supervision |
| Verified today | Builds `LIONDRIVER_REFERENCE=1 scons` and `RELEASE=1 LIONDRIVER_REFERENCE=1 scons` pass per the mode-lock and TX-rate change records (local builds). **No CI job builds the firmware with the define**: panda CI builds debug and release only (`panda/.github/workflows/test.yaml:25-28`), and `test_misra.sh:26-27` runs a plain `scons`. At `682f184` nothing in the repository set the variable for a device build; the base's top-level `SConstruct` now sets it by default (LionDriver #36) |
| Protection | At `682f184` (panda `8aa8671`): none at run time: the version string (`SConscript:36-41`) does not record the switch, and the health field `requests_rejected_pkt` is 0 both outside the reference build and in a reference build without rejections (`main_comms.h:27-31`), so the host could not tell which build is installed. *On the base (panda `6dee6fa`, LionDriver #41):* a reference build sets `HEALTH_FLAG_REFERENCE_BUILD` (bit 12) in every health packet; in a reference build `pandad` keeps the panda in NOOUTPUT unless the flag is set, and `selfdrived` raises `pandaNotReferenceBuild` (SWSR-514h Partly). The version string still does not record the switch; a debug (non-release) build is not detected |
| Change control | `panda/SConscript`, `board/reference_lock.h` and the guarded opendbc code are SR-A |
| Applies to | CFG-001 reference build only (by definition) |
| Gaps | Reference build reported and checked by the host on the base (panda `6dee6fa`); RELEASE vs DEBUG not reported or checked (DVR-23, DVR-05); no CI build of the reference firmware (OI-9) |

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
| CD-16 | `calibrationd` | `CalibrationParams` (PERSISTENT, `params_keys.h:19`) | Device mounting roll/pitch/yaw, camera height | Pitch `PITCH_LIMITS`, yaw ±0.0691 rad (`selfdrive/locationd/calibrationd.py:43-51`); clip ±0.005 beyond limits (`:56-59`); `INPUTS_NEEDED` 5 blocks before valid (`:33`) | modeld (warp), locationd; uncalibrated → no engagement (`selfdrived.py:298-309`) | Read with exception fallback (`calibrationd.py:72-87`) |
| CD-17 | `paramsd` | `LiveParametersV2` (PERSISTENT, `:82`), every 60 s (`paramsd.py:272-273`) | Steer ratio, tire stiffness, steering-angle offset, road roll | Steer ratio valid 0.5–2.0 × `CP.steerRatio` (`paramsd.py:47, 171`); stiffness valid 0.2–5.0 (`:172`); angle offset ≤ 10° (lowered 8°) with hysteresis (`:22-23, 155-156`); roll ±10° (`:18`); rate limits 20°/s offset, 20°/s roll (`:16-17`) | controlsd vehicle model and curvature (`controlsd.py:74-83`), which only floors stiffness and steer ratio at 0.1 and does not read the validity flags; invalidity is handled by selfdrived events (`paramsdTemporaryError`, `selfdrived.py:449-457`) | Steer-ratio sanity on restore (`paramsd.py:204-232`); stiffness reset to 1.0 every drive (`:235-237`) |
| CD-18 | `torqued` | `LiveTorqueParameters` (PERSISTENT \| DONT_LOG, `:85`) | Lateral-accel factor, offset, friction | Clipped to offline value (CD-09) ± 30 % (factor) and ± 50 % (friction) (`torqued.py:24-27, 93-96, 230-231`); learning only when engaged, no steer override, v > 15 m/s (`:22, 202`); enabled for Toyota (`ALLOWED_CARS`, `:37, 76`) | controlsd torque controller when `useParams` and `all_checks` (`controlsd.py:85-90`) | Restored only if restore key and `VERSION` match (`torqued.py:98-122`); **offset** has no explicit sanity bound in the lines reviewed (OI-5) |
| CD-19 | `lagd` | `LiveDelay` (PERSISTENT, `:81`) | Lateral actuator delay | `MIN_LAG` 0.15 s – `MAX_LAG` 0.65 s; confidence ≥ 0.7; v ≥ 50 mph (`lagd.py:24-34`) | Lateral planning/control delay compensation | To confirm (OI-5) |

Change control: algorithms and bounds are SR-Q source. The **learned values themselves are not configuration-controlled**: they differ per device, are not logged in full (`LiveTorqueParameters` is DONT_LOG) and are not part of any baseline. DVR-18…DVR-21.

### 4.5 Host monitoring thresholds and storage

**CD-20 Host monitoring thresholds**: excessive actuation detection uses 2 × `ACCEL_MAX`/`ACCEL_MIN` (±4 / −7 m/s²) and 2 × `ISO_LATERAL_ACCEL` (6 m/s²) for 0.25 s (`openpilot/selfdrive/selfdrived/helpers.py:12, 30, 41`; `opendbc_repo/opendbc/car/interfaces.py:25-26`); controller lateral limits `MAX_LATERAL_JERK` 5.0 m/s³, `MAX_LATERAL_ACCEL_NO_ROLL` 3.0 m/s², `MAX_CURVATURE` 0.2 1/m (`openpilot/selfdrive/controls/lib/drive_helpers.py:9-14`). QM; FSR-01.14 margin targets. DVR-06.

**CD-21 Model storage location**: `.lfsconfig` points to `https://huggingface.co/commaai/openpilot-lfs.git/info/lfs` with `locksverify = false` (GAP-40). Change: SR-T. DVR-16.

## 5. Protection and verification overview

| ID | ASIL | Verified today (where) | Integrity protection today | Plausibility today | Change control today | Main gap |
|---|---|---|---|---|---|---|
| CD-01 | C | Host 10 s mismatch check; safety tests set param explicitly; reference lock: panda host tests `tests/reference_lock` (HIL not run) | None | Reference build: panda lock admits only TOYOTA with parameter 73 (not verified on hardware). Other builds and `toyota_init`: none | SR-Q (source) / SR-A (envelope, lock) / runtime unprotected outside the reference build | GAP-09, GAP-44 outside the reference build; SWSR-104a |
| CD-02 | C | opendbc safety tests, both variants (`.github/workflows/safety.yaml:37-43`) | Firmware signature (weak) | n/a (constants) | SR-A | GAP-04, GAP-14 |
| CD-03 | C | opendbc unit tests (RX timeout, engagement gate, TX rate, EPS fault, cruise-main); panda host tests (heartbeat monitor, IWDG); HIL not run | Firmware signature | n/a | SR-A | GAP-06 (latencies not measured); IWDG LSI tolerance not confirmed |
| CD-04 | C | `test_rx_hook`, `test_block_aeb`, `test_pcs_and_dsu_messages_blocked`, `test_pcs_hud`, `test_reference_rx_checks` | Firmware signature | n/a | SR-A | GAP-01 |
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
| CD-23 | C | opendbc safety tests in the reference variant (CI); local reference builds (change records); no CI firmware build | Firmware signature | At `682f184` none (build not reported at run time); on the base the health flag `HEALTH_FLAG_REFERENCE_BUILD` and the `pandad` check (panda `6dee6fa`) | SR-A | DVR-23, OI-9 |

## 6. Requirements on configuration and calibration data

Requirement IDs `DVR-nn` are local to this work product until they are migrated into [WP-W-02](WP-W-02-software-safety-requirements.md) as SWSRs and into `assurance/trace/` (OI-1). Parents use FSRs from WP-C-04 and TSRs from WP-S-02 (Draft). All statuses: Proposed.

| ID | Requirement | ASIL | Parent | Allocation | Verification | Current state / GAP | Applies to |
|---|---|---|---|---|---|---|---|
| DVR-01 | In the reference configuration the envelope shall accept only safety model `toyota` with safety parameter `73` (no flag bits); any other model or parameter requested by the SoC shall leave the envelope in a non-actuating mode. | C | FSR-01.10 / TSR-512, TSR-804 | E-03 panda request gate (`panda/board/reference_lock.h`, U-PND-COMMS; SWSR-512), not `toyota_init`; a range check in `toyota_init` is SWSR-104a | T-SIL (WP-W-06 VS-UV-12; `panda/tests/reference_lock`), T-HIL (`panda/tests/hitl/test_11_reference_lock.py`) | Implemented in the reference build, not verified on hardware: `0xdc` TOYOTA accepted only with `param2 == 73` (panda `8aa8671`, `board/reference_lock.h:22-28`); a refused request leaves the previous mode (`main_comms.h:74-79`), which is SILENT, NOOUTPUT or ELM327 (diagnostic TX only, opendbc `modes/elm327.h:6-34`) when TOYOTA is not yet active. Host tests pass (mode-lock change record §4); HIL not run. Not met in any other build. `toyota_init` still accepts any EPS factor 0–255 in every build (opendbc `7993399`, `modes/toyota.h:492`; GAP-44, SWSR-104a) | CFG-001 reference build only |
| DVR-02 | Once a car safety mode is active, the envelope shall accept from the SoC only the mode and parameter changes that SWSR-512 allows (a change to NOOUTPUT or SILENT, and from there back to a mode of the reference set, TOYOTA only with parameter 73); every other change shall be rejected. | C | FSR-01.10 / TSR-512, TSR-513 | E-03 panda request gate (`panda/board/reference_lock.h`, applied in `main_comms.h` before `0xdc`; SWSR-512, SWSR-512a, SWSR-513) | T-SIL (`panda/tests/reference_lock`), T-HIL (VS-UV-13, `test_11_reference_lock.py`) | Partly implemented in the reference build, not verified on hardware: with TOYOTA active only NOOUTPUT or SILENT is accepted (`reference_lock.h:23-24`); `0xdf` is refused in every mode (`:30-32`); `0xd1` softloader entry and the SWSR-513 list are refused in a car mode (`:33-48`). A change to NOOUTPUT or SILENT followed by TOYOTA with parameter 73 is accepted, as the requirement now allows (reworded 2026-10-19 from "until ignition off" to match SWSR-512, register DQ-073 A; OI-8). Internal mode changes (heartbeat loss, faults) do not pass the gate (`:12`). Not met in any other build (GAP-09) | CFG-001 reference build only |
| DVR-03 | Every envelope limit and timing constant (CD-02, CD-03) shall have a requirement ID, physical unit, value, tolerance and rationale recorded in `assurance/trace/` and a `@req` tag at its definition. | C | FSR-01.01…01.07 / TSR-101…104, 201…205, 401, 407 | E-03 source + trace | Review, trace check K10 (WP-P-06) | Not met (GAP-14, GAP-04) | All Toyota configurations (CD-02); all configurations (shared code: the CD-03 constants in `safety.h`, `declarations.h`, `lateral.h` and panda `main.c`/drivers are used by every brand); CFG-001 reference build only for the guarded CD-03 constants |
| DVR-04 | Unit tests of envelope limits shall take expected values from the requirement data (`assurance/trace/`), not from copies of the source constants. | C | DVR-03 | Test code | Review | Not met (`test_toyota.py:139-155`) | All Toyota configurations (`test_toyota.py`); all configurations for the shared tests in `common.py` |
| DVR-05 | Firmware installed in a vehicle shall be a RELEASE build signed with the LionDriver release key; the device shall report build type and firmware hash, and the host shall refuse to engage on a DEBUG build. | C | FSR-01.10 / TSR-514, TSR-802 | E-03 build, E-01 check | Release audit (WP-P-01 §11), T-HIL | Not met (GAP-25) | All configurations (every panda build installed in a vehicle); claimed for CFG-001 |
| DVR-06 | An automated check shall verify that every host controller limit (CD-06, CD-20) is below the corresponding envelope limit (CD-02) by the margin set in FSR-01.14. | QM (supports C) | FSR-01.14 / TSR-605 | CI check | Analysis, CI | Not met (zero margin) | CFG-001 (CD-06 is shared by all Toyota configurations; CD-20 by all configurations) |
| DVR-07 | The platform data used by the reference configuration (CD-07…CD-09) shall be recorded in the item definition as expected values, and a start-up check shall compare the selected platform and `CarParams` with them. | QM (feeds C) | FSR-01.10 / TSR-804 | E-01 | T-SIL, installation check (WP-O-01) | Not met | CFG-001 |
| DVR-08 | Platform variants and flags not validated for the reference vehicle (hybrid, non-US variants, `RAISED_ACCEL_LIMIT` without Corolla validation) shall be excluded or validated before release. | QM | FSR-03.01 | E-01, WP-V-01 | Review, T-VEH | Open | CFG-001 (excludes the other variants of `TOYOTA_COROLLA_TSS2`) |
| DVR-09 | The provenance of the offline torque model (CD-09) shall be recorded, or the values re-derived from LionDriver reference-vehicle data. | QM | FSR-01.14 | E-01 | Analysis | Open | `TOYOTA_COROLLA_TSS2` platform; claimed for CFG-001 |
| DVR-10 | In the reference configuration, fingerprinting shall require an exact FW match against the VIN-recorded ECU versions of the reference vehicle; fuzzy matching shall be disabled. | QM (feeds C) | FSR-01.10 / TSR-803 | E-01 (`car_helpers.py`, `fw_versions.py`) | T-SIL, installation check | Not met (fuzzy enabled by default, `fw_versions.py:147-153`) | CFG-001 (matching code `fw_versions.py` is shared by all configurations) |
| DVR-11 | Host CAN signal definitions (DBC) for every signal the envelope also decodes shall be checked against the envelope decoding on recorded LionDriver routes. | QM (supports C) | FSR-01.06 | Test | `test_panda_safety_carstate` on fork-owned routes | Partial (comma routes only) | CFG-001 (signals shared with the Toyota configurations that use the same DBCs) |
| DVR-12 | Safety-relevant Params (CD-12) shall have documented reference-configuration values; at engagement the host shall verify them and refuse engagement if a debug or demo key (`IsDriverViewEnabled`, `JoystickDebugMode`, maneuver modes) is set. | QM | FSR-02.08 / TSR-610, TSR-613, TSR-806 | E-01 (selfdrived) | T-SIL | Not met (GAP-20) | CFG-001 (check in shared host code; all configurations) |
| DVR-13 | `ExperimentalMode` shall default to `0` in the reference configuration until the SOTIF evaluation of end-to-end longitudinal control is complete. | QM (SOTIF) | D-08, GAP-18 / TSR-806 | `params_keys.h` | Review | Not met (default `"1"`) | CFG-001 (the default is shared by all configurations) |
| DVR-14 | Cached `CarParams` and `CarParamsCache` shall carry an integrity check (CRC or hash) that is verified before use; a mismatch shall force full fingerprinting. | QM (feeds C) | FSR-01.10 | E-01 (`card.py`) | T-SIL, FI | Not met | All configurations (shared host code `card.py`) |
| DVR-15 | Each model file shall be verified against a hash recorded in the release manifest before it is loaded; a mismatch shall prevent engagement. | QM (PAS 8800 / CS) | GAP-22 / TSR-801 | E-02 loader (`modeld`) | T-SIL, FI | Not met | All configurations (shared models) |
| DVR-16 | Released model files shall be stored in a LionDriver-controlled store, and the release manifest shall list each model's path, LFS oid and size. | QM | GAP-40, D-05 | CM | PCA audit (WP-P-01 §11) | Not met | All configurations (shared models) |
| DVR-17 | DM thresholds and timers (CD-15) shall match the values specified in WP-C-08 §5; a change shall trigger the DM validation tests of WP-V-02. | QM (SOTIF) | FSR-02.06 / TSR-608 | E-01/DM | Review, T-SIL | Open | All configurations (shared DM code) |
| DVR-18 | Every learned parameter (CD-16…CD-19) shall be bounded at the point of use by limits that are recorded with rationale, including the lateral-accel offset learned by `torqued`. | QM (SOTIF) | FSR-01.14 / TSR-605 | E-01 | Review, T-SIL | Partial (§4.4) | All configurations (shared host learners; `torqued` for `ALLOWED_CARS` brands only) |
| DVR-19 | Learned parameters restored from storage shall pass an integrity check and the same plausibility bounds as live values; failure shall reset to offline defaults. | QM | DVR-18 | E-01 | T-SIL, FI | Partial (paramsd steer ratio; torqued version key) | All configurations (shared host code) |
| DVR-20 | The complete learned state (CD-16…CD-19) shall be logged at start and end of each drive so field events can be reproduced. | QM | WP-O-04 | E-01 logging | Review | Partial (`LiveTorqueParameters` DONT_LOG) | All configurations (shared host code) |
| DVR-21 | An installer-initiated reset of all learned parameters shall exist and shall be performed at installation, after service on steering/suspension/tires, and after a software update that changes a learner. | QM | WP-O-01, WP-O-02 | E-01, procedure | Procedure review | Open | All configurations (procedure applied to CFG-001) |
| DVR-22 | The τ_max(v) table (CD-22) shall be generated from a recorded derivation (data set ID, method, margin) and checked at build time for monotonic speed breakpoints, values within [0, 1500] raw and agreement with the derivation record; the check result shall be part of the release evidence. | C | FSR-01.01 / TSR-102 | E-03 build + data | Analysis, T-SIL | Not implemented (no table yet) | CFG-001 (would apply to all Toyota configurations if not guarded by `LIONDRIVER_REFERENCE`) |
| DVR-23 | Firmware installed in the reference vehicle shall be built with `RELEASE=1 LIONDRIVER_REFERENCE=1`; the device shall report that it is a reference build, and the host shall refuse to engage when it is not. A CI job shall build this configuration for every change to `panda/` or `opendbc/safety/`. | C | FSR-01.10 / TSR-512, TSR-802 | E-03 build, E-01 check, CI | Release audit (WP-P-01 §11), T-HIL | Not met: at `682f184` the switch was not reported at run time; on the base the reference build is the default device build (LionDriver #36), is reported in the health packet and is required by `pandad` (panda `6dee6fa`, LionDriver #41), so the reference part is partly met, not verified on hardware; `RELEASE=1` is not the default and no CI job builds the reference firmware (CD-23) | CFG-001 reference build only |

## 7. Change control rules for data

| Data class | Route ([WP-P-02](../07-supporting/WP-P-02-change-management.md)) | Additional evidence |
|---|---|---|
| CD-01…CD-05, CD-22, CD-23 | SR-A | Re-run WP-W-06 VS-UV for the affected units, with the opendbc safety tests in both variants (default and `LIONDRIVER_REFERENCE=1`) and the panda host tests; build `RELEASE=1 LIONDRIVER_REFERENCE=1`; state for each change which configurations it applies to (reference build only, all Toyota, shared code); update trace data; I1 review minimum |
| CD-06…CD-11, CD-20 | SR-Q | DVR-06 check; car tests; process replay with fork-owned refs |
| CD-12 (defaults) | SR-Q | Impact analysis against WP-C-05/WP-C-08 |
| CD-14, CD-21 | SR-Q + D-05 model change | WP-V-03 scenario re-run; manifest update |
| CD-15 | SR-Q | DM validation per WP-V-02 |
| CD-16…CD-19 algorithms/bounds | SR-Q | Replay on fork-owned logs; DVR-18 review |
| Learned values (runtime) | Not change-controlled; governed by DVR-19…DVR-21 | Field monitoring (WP-O-04) |

## 8. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Migrate DVR-01…DVR-23 into WP-W-02 (SWSR) or WP-S-01/WP-C-07 as appropriate and into `assurance/trace/`; `DVR` is not a registered prefix in the README | Safety engineer | G3 |
| OI-2 | Re-check TSR parents when WP-S-02 is approved | Safety engineer | G2 |
| OI-3 | Record the reference vehicle's VIN-specific FW versions in WP-C-01 (input to DVR-07, DVR-10) | Maintainer | G1 |
| OI-4 | Decide whether learned parameters should be disabled (fixed offline values) for the reference configuration during validation, to make results reproducible. **Decided 2026-10-14** (register DQ-072 A): the learned values are frozen for most validation runs, and a separate campaign runs with learning on. Still to do: the freezing method and the learning-on campaign in the validation plan ([WP-V-01](../06-validation/WP-V-01-safety-validation.md)) and test operations ([WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md)) | Safety engineer | G2 |
| OI-5 | Review `torqued` offset bounds and `lagd` restore logic in full (only constants and the lines cited were reviewed) | Controls owner | G3 |
| OI-6 | Confirm whether `CarParamsCache` can bypass fingerprinting on a different vehicle with the same device (VIN check) | Vehicle port owner | G2 |
| OI-7 | Closed: recorded as GAP-44 in the [gap assessment](../00-assessment/gap-assessment.md). In the reference build the panda lock accepts only parameter 73 (SWSR-512); `toyota_init` itself still has no range check (SWSR-104a) | Safety engineer | G1 |
| OI-8 | ~~DVR-02 requires mode changes to be refused until ignition off; the lock (SWSR-512) allows TOYOTA → NOOUTPUT/SILENT → TOYOTA 73. Decide whether DVR-02 is reworded to SWSR-512 or a further requirement is raised~~ **Closed 2026-10-19:** DVR-02 reworded to SWSR-512 (register DQ-073 A, decided 2026-10-14): a return to TOYOTA 73 after a drop to SILENT stays possible within a drive | Safety engineer | G2 |
| OI-9 | No CI job builds the panda firmware with `LIONDRIVER_REFERENCE=1`, and nothing in the repository sets it for a device build; add a CI build of `RELEASE=1 LIONDRIVER_REFERENCE=1` (with a test certificate) and a release-procedure check (DVR-23) | Release manager | G3 |
