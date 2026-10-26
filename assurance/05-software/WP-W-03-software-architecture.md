# WP-W-03 Software Architectural Design

| Field | Value |
|---|---|
| Work product | WP-W-03 Software architectural design |
| Standard reference | ISO 26262-6:2018 §7 (software architectural design: notation, design principles, static and dynamic aspects, ASIL attribution, resource usage); ISO 26262-9:2018 §6 (coexistence, by reference to WP-A-02); ASPICE 4.0 SWE.2 |
| Version | 0.21 (OI-2, OI-3, OI-4 and ATC-04, -10, -11, -22 record DQ-153, DQ-155, DQ-156 and DQ-147 (all A); the panda changes are open; 2026-10-26). 0.20 (§3.1: U-PND-HK attributed ASIL C, all its code developed and verified to ASIL C instead of QM with FFI, lead decision DQ-126 option B, closing WP-A-02 OI-2; mirrored in the SysML model; I0, Claude; 2026-10-25). 0.19 (§3.1: the catalogue is mirrored in the SysML model and checked cell by cell (SY-05, DQ-186); 2026-10-24). 0.18 (§10: ATC-21 not taken, register DQ-082 B; 2026-10-19). 0.17 (§3: EPS-fault siren unit, persistence 0.7 s at panda `bf8102a`, DQ-048; 2026-10-17). 0.16 (§10: ATC-27 added and implemented at the pin bump to opendbc `27f20db` (SWSR-408, B2B-05), [change-2026-10-17-pin-27f20db](../07-supporting/impact/change-2026-10-17-pin-27f20db.md); 2026-10-17). 0.15 (§10: ATC-25 implemented at the pin bump to opendbc `62b89a3`, [change-2026-10-17-pin-62b89a3](../07-supporting/impact/change-2026-10-17-pin-62b89a3.md); 2026-10-17). 0.14 (§3.1 and §3.3: envelope units and software interfaces changed from B‡ to ASIL C after DQ-341 (envelope hardened to C), B units unchanged; header and Figures 3-1 and 3-2 labels to match; with WP-S-03 v0.12 OI-6; 2026-10-16). 0.13 (§10: ATC-20 and ATC-26 implemented at the pin bump to opendbc `515b9a2`, [change-2026-10-16-pin-515b9a2](../07-supporting/impact/change-2026-10-16-pin-515b9a2.md); 2026-10-16). 0.12 (§10: ATC-19 status corrected (mostly done on the base, completed by the release-variant change), ATC-20 proposed, ATC-26 added for B2B-06 (cruise edge after a mode change); 2026-10-14). 0.11 (§3.2: generated Simulink-style firmware diagram added beside Figure 3-2; §4.2: generated host data-flow diagram; diagrams coloured by block kind; 2026-10-13). 0.10 (§3.2: Simulink-style envelope block diagram added as a generated figure; 2026-10-13). 0.9 (§10 ATC-25: wrong-length RX frame as RX fault, B2B-01, maintainer decision; 2026-10-13). 0.8 (§3.1 element hierarchy added as Figure 3-1; §3.2 block diagram renumbered Figure 3-2; 2026-10-13). 0.7 (merge of PR #47 software alignment with the base; 2026-10-13: Figure 3-1 kept with the text version of §3.2 rewritten from the code reading; heartbeat-loss siren (panda `c33343b`) and EPS-fault siren (panda `b790fca`) added to §3.1, §3.2, §5.1 and §5.2; host supervision (TSR-308/602/615/621) noted in §4.2 and §10). It carries PR #47's drafts, numbered 0.4–0.5 there: 0.5 (RR-2026-009 F-11: §2, §3, §5.1–§5.2, §5.5–§5.6, §6, §7 and §8 rewritten from a code reading at `682f184` (opendbc `7993399`, panda `8aa8671`), new modules added to the catalogue, reference-build-only elements marked; F-12: TX-hook revocation (SWSR-518) added to §6.3 and to the §5.4.3 race analysis; F-13: every target-state entry moved to the new §10; F-28: Author field; status note removed; 2026-10-12). 0.4 (alignment pass, [RR-2026-009](reviews/RR-2026-009.md): sections renumbered so §5.4 is only the interrupt-priority scheme, start-up is §5.5 and the safety-mode state machine §5.6; §5.1 priority note updated to panda `52cad44`; status note on stale sections; 2026-10-12). History on the base: 0.6 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.5 (§3.2 block diagram redrawn as Figure 3-1 with unit IDs and SI interface tags; text version kept; 2026-10-13). 0.4 (status update 2026-10-12: §2, §3 and §4.2 aligned with the 100 Hz TIM4 safety task and 0.3 s heartbeat of §5.1; new units in §3.1 (heartbeat monitor, IWDG, IRQ priority table, reference lock, EPS-fault siren in panda `b790fca`, LionDriver PR #45, not merged; TX rate check in `safety_tx_hook`); §5.1 priorities, §5.4 start-up, §5.4 status, §6.2 and §8 ratings updated. Nothing verified on hardware). 0.3 (§5.4.4 prerequisites implemented, panda `52cad44`: explicit priority table, atomic safety-config switch and fault word; R-2 recorded as a 10 ms bound; 2026-10-12). 0.2 (§5.1–5.2 updated to panda `c2e5d93`; new §5.4 proposed interrupt-priority scheme and race analysis (OI-4, SWSR-519); §6.3 re-assessed; 2026-10-12) |
| Status | Draft |
| ASIL / scope | Envelope (E-03a/E-03b): ASIL C (hardened to C, register DQ-341, 2026-10-16; notation of [WP-S-02 §2.1](../03-system/WP-S-02-technical-safety-requirements.md)); host (E-01): QM / QM (B-sup) |
| Author | Assurance team (AI-assisted draft, Claude) |
| Reviewer(s) | TBD (I1); I2 for §6 and §8 |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `682f184` (opendbc `7993399`, panda `8aa8671`); facts merged from the base at panda `b790fca`/`c33343b` (EPS-fault and heartbeat-loss sirens) name their pin. Current pins: panda `c33343b`, opendbc `273f44e` (not re-read in full). Earlier: `bf6ce8c` (status update 2026-10-12; panda `b790fca`, opendbc `7993399`); `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document describes the software architecture of LD-SDA as it exists at the baseline. §1–§9 describe only the code as it is; the changes that the SWSRs of [WP-W-02](WP-W-02-software-safety-requirements.md) still require are collected in §10 (target-state changes). It covers:

- (a) the panda firmware with the opendbc safety layer (E-03a/E-03b), which runs the safety envelope on the STM32H7;
- (b) the host stack on the SoC (E-01): the openpilot processes and cereal services that matter to safety.

It is the reference for the element catalogue used in allocations (`assurance/trace/elements.yaml`, [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) OI-4), for the software safety analysis ([WP-W-04](WP-W-04-software-safety-analysis.md)), the unit design ([WP-W-05](WP-W-05-software-unit-design.md)) and the shared-data documentation required by [WP-W-01](WP-W-01-software-development-environment-guidelines.md) ENV-R-12 (OI-6 there; §6.3 here). System context: [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md). HSI: [WP-S-05](../03-system/WP-S-05-hsi-specification.md).

Notation (WP-W-01 §14): component tables, ASCII block diagrams, state-transition tables, data-flow tables. Paths as in WP-W-02 §2.2. Code references give the repository pin once per table or paragraph; panda paths are relative to `panda/`, opendbc paths to `opendbc_repo/opendbc/safety/`.

**Build variants.** Two firmware builds matter here. The *reference build* is `RELEASE=1 LIONDRIVER_REFERENCE=1` (panda `8aa8671`, `SConscript:24-26` adds `-DLIONDRIVER_REFERENCE`); the *standard build* is the same without `LIONDRIVER_REFERENCE`. Elements compiled only under `#ifdef LIONDRIVER_REFERENCE` are marked **[ref]** below. Everything else is in both builds. What each integrated change does is recorded in the [change records](../07-supporting/impact/README.md) and the WP-W-02 Baseline column. Nothing in this document is verified on hardware unless a cited record says so.

## 2. Architectural drivers

| Driver | Source | Consequence |
|---|---|---|
| Envelope independent of QM commands | AP-1, AP-5 (WP-S-03 §2) | All SoC actuation passes `safety_tx_hook`; in the reference build the host's configuration requests are restricted by `reference_lock.h` (SWSR-512, 513) |
| Fail-silent | AP-2 | One safe state SS-S reachable from every fault (SWSR-502; not yet implemented, §10) |
| Timing budgets 0.05–0.3 s | [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | Periodic checks run in a 100 Hz safety task (SWSR-401a, partial); its period and jitter are not measured (§5.4.5) |
| Single MCU, single address space | GAP-11 | FFI must be argued by software means and MPU (SWSR-507; no MPU at the baseline) |
| Reuse of upstream code | T-03 | Architecture back-filled; minimal structural change preferred; LionDriver additions are gated by `LIONDRIVER_REFERENCE` where they would change upstream behaviour |

## 3. Static architecture: panda firmware (E-03)

### 3.1 Component catalogue

Unit IDs U-xxx follow [WP-W-06 §2](WP-W-06-software-unit-verification.md). U-PND-USB, U-PND-PWR, U-PND-HK and U-PND-PLAT are new here (OI-1). Pins: panda `8aa8671`, opendbc `7993399`; the two siren rows were added from panda `b790fca` and `c33343b`. The table is held cell by cell in the [SysML model](../models/sysml/README.md) (SY-05, check T1): change a cell there too, until the model review makes the model its record and the table is generated from it.

| Element name | Unit | Files | Responsibility at the baseline | Build | ASIL attribution |
|---|---|---|---|---|---|
| `panda.safety.core` | U-SAF-CORE | `safety.h` | Hook dispatch (`safety_rx_hook` `:201-230`, `safety_tx_hook` `:283-302`, `safety_fwd_hook` `:316`); RX checks and timeout (`rx_check_lagging` `:373-386`, `safety_tick` `:404-420`); authority `controls_allowed` (`:57`) with grant on PCM rising edge gated by `rx_checks_allow_engagement` (`:390-401`, `pcm_cruise_check` `:601-610`); generic brake/gas edges (`:426-446`); relay-malfunction detection; TX whitelist (`tx_msg_safety_check` `:232-241`); mode switching (`set_safety_hooks` `:467-565`) | both | C |
| `panda.safety.core.rx_engagement` | U-SAF-CORE | `safety.h:373-401`; `declarations.h:242` | `rx_timeout_periods` tightens the lag threshold to N nominal periods with no 1 s floor (`:380-383`); `rx_checks_allow_engagement` refuses a grant while any RX check lags or is invalid. Active for any mode that sets `rx_timeout_periods`; Toyota sets 5 (`modes/toyota.h:83, 543`) | both (Toyota) | C |
| `panda.safety.core.tx_rate_check` | U-SAF-CORE | `safety.h:243-281`, called first in `safety_tx_hook` (`:290-294`) | Per-ID TX rate budget over a sliding 250 ms window; frames over budget are rejected before the mode's TX hook; on the 3rd rejection while authority is granted, clears `controls_allowed` and sets `safety_tx_rate_exceeded` (`:269-272`) (SWSR-518) | **[ref]** | C |
| `panda.safety.lateral` | U-SAF-LAT | `lateral.h` | Torque limit, rate, measured-torque, RT window, steer-request tolerance (`steer_torque_cmd_checks`, reads `controls_allowed` at `:64, 99, 141`); angle/curvature checks unused in the reference configuration | both | C |
| `panda.safety.longitudinal` | U-SAF-LONG | `longitudinal.h` | Longitudinal allowed, accel bounds, inactive value | both | B |
| `panda.safety.helpers` | U-SAF-HELP | `helpers.h`, `declarations.h`, `can.h` | Macros, CRC8, message matching, timestamps, interpolation, packet type, `safety_config` incl. `rx_timeout_periods` and `tx_rate_checks` (`declarations.h:242-244`) | both | C |
| `panda.safety.toyota` | U-SAF-TOY | `modes/toyota.h` | Toyota RX parsing, TX checks, limits, init/param decoding; hook table `toyota_hooks` (`:565-572`) | both | C |
| `panda.safety.toyota.eps_fault` | U-SAF-TOY | `modes/toyota.h:91-116, 236-240, 425-434` | `toyota_lka_state_is_fault` decodes `0x262` EPS_STATUS.LKA_STATE into `safety_eps_fault`; while set, `0x2E4` frames with non-zero torque or steer request are refused before the limit checks. Does not clear `controls_allowed` (SWSR-110 partial) | **[ref]** | C |
| `panda.safety.toyota.ref_rx_set` | U-SAF-TOY | `modes/toyota.h:56-63` | Adds `0x262` (25 Hz) and `0x1D3` (33 Hz) to the RX checks (presence, checksum, timeout) | **[ref]** | C |
| `panda.safety.toyota.cruise_main` | U-SAF-TOY | `modes/toyota.h:123-145, 241-249` | `toyota_cruise_main_check`: CRUISE_ACTIVE with MAIN_ON = 0 revokes authority at once on a cruise edge, or after 150 ms of disagreement (SWSR-405 (c)) | **[ref]** | C |
| `panda.safety.toyota.tx_budgets` | U-SAF-TOY | `modes/toyota.h:545-560` | TX rate rows for non-SecOC configurations (`0x2E4` 100 Hz + 5, `0x191`, `0x343`, `0x412`, `0x1D2`, `0x283`, `0x750`) | **[ref]** | C |
| `panda.safety.defaults` | U-SAF-DEF | `modes/defaults.h`, `modes/elm327.h` | SILENT/NOOUTPUT/ELM327 hooks | both | C (safe-state modes) |
| `panda.safety.ignition` | U-SAF-IGN | `ignition.h` | CAN ignition detection | both | B (feeds heartbeat timeout choice, TSR-510) |
| `panda.safety.other_modes` | — | `modes/*.h` other brands, included at `safety.h:10-33`, registered at `:468-498` | Linked in both builds. Standard build: selectable via `0xdc`. Reference build: not selectable by the host (`reference_lock.h:22-29`), so dead code (OI-2) | both | Interference source (standard build); dead code to be removed or justified (reference build, OI-2) |
| `panda.main` | U-PND-MAIN | `board/main.c` | Start-up (`main` `:292-383`), `set_safety_mode` (`:38-93`, both `set_safety_hooks` calls in `ENTER_CRITICAL` `:43-45, 49-51`), 8 Hz tick (`tick_handler` `:147-290`: harness, software watchdog kick, siren; 1 Hz: heartbeat counter, `heartbeat_engaged` mismatch, SILENT after 5 s/2 s heartbeat loss, `check_registers`), main loop (`:386-420`) | both | C |
| `panda.main.safety_task` | U-PND-MAIN | `board/main.c:130-144`; timer `board/drivers/timers.h:30-38`; `board/stm32h7/stm32h7_config.h:39-41` | TIM4 safety task at `SAFETY_TASK_FREQ` = 100 Hz: `safety_tick` (`:133`), heartbeat monitor with revocation in car modes (`:135-137`), IWDG feed (`:138`). Rate supervision at 110 calls/s (`main.c:352`) (SWSR-401a partial). Since panda `b790fca` / `c33343b` it also runs the EPS-fault siren and the heartbeat-loss siren (rows below) | both | C |
| `panda.drivers.heartbeat_monitor` | U-PND-MAIN | `board/drivers/heartbeat_monitor.h` | `heartbeat_age_ticks` reset on `0xf3` (`:20-22`, called from `main_comms.h:301`); incremented in the safety task, returns true at ≥ 30 ticks = 0.3 s (`:15, 25-30`) (SWSR-407) | both | C |
| `panda.drivers.heartbeat_siren` | U-PND-HK | `board/drivers/heartbeat_siren.h` (panda `c33343b`) | When the heartbeat monitor revokes authority in a car mode while `controls_allowed` was set, the safety task requests the siren at once and holds it 3 s (`HEARTBEAT_SIREN_HOLD_TICKS` 300); reset on every mode change. Audible ≈ 0.56 s after the last heartbeat worst case (odd 8 Hz ticks) (SWSR-516 (a)) | both | B |
| `panda.drivers.eps_fault_siren` | U-PND-HK | `board/drivers/eps_fault_siren.h` (panda `b790fca`) | Once `safety_eps_fault` has been set for 0.7 s, counted from when it was first seen while `controls_allowed` (DQ-048, DQ-367; panda `bf8102a`), siren for at least 3 s, re-triggered while the fault persists; reset on every mode change. Worst case ≈ 0.96 s after the fault onset (SWSR-516 (b), EPS fault). Compiled in every build; only the reference build sets `safety_eps_fault` | both | B |
| `panda.drivers.hw_watchdog` | U-PND-FLT | `board/drivers/hw_watchdog.h` | IWDG1, prescaler /4, RLR 719, window 679 (`:35-37`); started on the first relay drive by `set_intercept_relay` (`drivers/harness.h:16-21`), not at boot (`:45-58`); fed from the safety task only if the main loop has run since the last feed (`:61-76`); first tick after start skipped. A watchdog reset is reported as `HEALTH_FLAG_WATCHDOG_RESET` (`main.c:377-380`) (SWSR-501) | both | C |
| `panda.drivers.irq_priorities` | U-PND-PLAT | `board/drivers/irq_priorities.h` | `interrupt_priorities_init` (`:21-46`, called at `main.c:300` before any `NVIC_EnableIRQ`) sets an explicit priority for every enabled IRQ; five classes, all at level 8 (`:15-19`) (SWSR-519 partial) | both | C |
| `panda.reference_lock` | U-PND-COMMS | `board/reference_lock.h:13-63`, called at `board/main_comms.h:74-79` | `reference_request_allowed`: `0xdc` limited to SILENT, NOOUTPUT, ELM327 and TOYOTA param 73, and from TOYOTA only to NOOUTPUT/SILENT (`:22-29`); `0xdf` always refused (`:30-32`); `0xd1` softloader refused in car modes (`:33-36`); `0xc5, 0xd8, 0xdb, 0xde, 0xe5–0xe8, 0xf1, 0xf9, 0xfc` refused in car modes (`:37-49`); refused requests counted in `reference_requests_rejected` (health) | **[ref]** | C |
| `panda.comms` | U-PND-COMMS | `board/main_comms.h`, `board/can_comms.h` | Control-request dispatcher `comms_control_handler` (`main_comms.h:69-343`), health packet (`:8-61`), CAN stream packing/unpacking (`comms_can_write` `can_comms.h:83-129`) | both | C (it calls envelope APIs and can change configuration) |
| `panda.drivers.spi` | U-PND-SPI | `board/drivers/spi.h`, `board/stm32h7/llspi.h` | SPI framing, XOR checksum, DMA control; `spi_rx_done` (`spi.h:106`) runs in the DMA2 Stream2 IRQ (`llspi.h:56-61`) | both | C |
| `panda.drivers.usb` | U-PND-USB | `board/drivers/usb.h`, `board/stm32h7/llusb.h` | USB endpoint handling; reaches the same comms handlers (`usb.h:616` → `comms_can_write`); initialised in both builds (`main.c:356`) | both | Not needed by the reference device (SPI); interference source (OI-3) |
| `panda.drivers.fdcan` | U-PND-FDCAN | `board/drivers/fdcan.h`, `board/drivers/can_common.h`, `board/stm32h7/llfdcan.h` | CAN RX ISR `can_rx` (`fdcan.h:154-243`: forward hook `:199`, forwarding with hook skipped `:213`, RX hook `:221`), TX path `can_send` (`can_common.h:161-177`) → TX hook → queue → `process_can` (`fdcan.h:88-150`, XOR check `:100`) | both | C |
| `panda.drivers.harness` | U-PND-HARN | `board/drivers/harness.h` | Relay drive (`set_intercept_relay` `:9-37`, also starts the IWDG), orientation and ignition sense | both | C (blocking) / B (PCS restore) |
| `panda.sys.faults` | U-PND-FLT | `board/sys/faults.h`, `board/drivers/simple_watchdog.h`, `board/drivers/registers.h`, `board/drivers/interrupts.h` | Fault recording (`fault_occurred`/`fault_recovered` in critical sections, `faults.h:10-11, 25-26`), software watchdog (kicked and checked in the 8 Hz tick, `simple_watchdog.h:7-17`, `main.c:160`), register check (1 Hz), interrupt-rate supervision (`interrupts.h:50`) | both | C (report-only; `PERMANENT_FAULTS 0U`, `sys/sys.h:50`) |
| `panda.sys.power_saving` | U-PND-PWR | `board/sys/power_saving.h` | Power-save: CAN IRQ and transceiver disable | both | C (can stop camera-side forwarding, WP-A-02 FFI-CM-08) |
| `panda.drivers.siren` / housekeeping | U-PND-HK | `board/drivers/fake_siren.h`, `board/stm32h7/sound.h`, `board/drivers/{fan,led,bootkick,clock_source,pwm}.h`, `board/stm32h7/lldts.h`, ADC | Siren (B, TSR-516); fan, LED and the rest developed to ASIL C, no FFI claimed (WP-A-02 §2, DQ-126) | both | C |
| `panda.platform` | U-PND-PLAT | `board/stm32h7/startup_stm32h7x5xx.s`, `board/early_init.h`, `board/stm32h7/{clock,peripherals,interrupt_handlers,llflash}.h`, `board/drivers/timers.h`, `board/sys/sys.h` | Reset, exception handlers (NMI/HardFault `early_init.h:73-81`), clocks, vectors, timers, critical sections (`sys.h:10-22`) | both | C |
| `panda.bootstub` | U-PND-BOOT | `board/bootstub.c`, `board/crypto/*`, `board/flasher.h` | Signature check (`bootstub.c:33-82`), soft flasher | both | C + CS |

`board/drivers/fault_injection.h` and request `0xa9` exist only with `LIONDRIVER_FAULT_INJECTION` (`main.c:11-13`, `main_comms.h:91-96`), a debug build for fault-injection tests; they are not part of the reference or standard release build and are not catalogued as an element.

![Figure 3-1: software element hierarchy: E-03 safety MCU firmware (runs on the panda MCU) consists of 19 software components of §3.1 (U-SAF-CORE, U-SAF-TOY, U-SAF-LAT, U-SAF-LONG, U-SAF-HELP, U-SAF-DEF, U-SAF-IGN, the other modes, U-PND-MAIN, U-PND-COMMS, U-PND-SPI, U-PND-FDCAN, U-PND-HARN, U-PND-FLT, U-PND-PWR, U-PND-HK, U-PND-PLAT, U-PND-BOOT, U-PND-USB), which consist of the units UN-01 to UN-46 and UN-N1 of WP-W-05 §2 plus the planned UN-N2 to UN-N6; E-01 application SoC software (runs on the SoC) consists of the 10 QM host elements of §4.1](figures/fig-w03-3-1-software-element-hierarchy.svg)

*Figure 3-1.* Element hierarchy at software level: the components E-03 and E-01 of [WP-C-01 Figure 3-1](../02-concept/WP-C-01-item-definition.md) → the software components of this catalogue (§3.1, grouped by unit ID; §4.1) → the software units of [WP-W-05 §2](WP-W-05-software-unit-design.md), with the ASIL attribution of the tables. Units marked "ref" exist only in the reference build (`LIONDRIVER_REFERENCE`), UN-44 only in the fault-injection debug build; dashed red units are planned and not implemented. The "E-03a/E-03b" group labels follow WP-S-05 (opendbc safety layer / panda firmware). Nothing shown is verified on hardware. Source: [`figures/fig-w03-3-1-software-element-hierarchy.svg`](figures/fig-w03-3-1-software-element-hierarchy.svg); change it together with §3.1, §4.1 and WP-W-05 §2.

### 3.2 Block diagram

Pins: panda `8aa8671`, opendbc `7993399`. **[ref]** = reference build only. All interrupts at NVIC level 8 (§5.1).

![Figure 3-2: software architecture of the panda firmware, with the QM host stack (host.pandad) and the safety envelope units U-PND-SPI, U-PND-COMMS, U-PND-MAIN, U-PND-HARN, U-PND-FDCAN, U-SAF-CORE, U-SAF-TOY, U-SAF-LAT and U-SAF-LONG, interfaces SI-01 to SI-10 and the execution contexts](figures/fig-w03-3-2-panda-software-architecture.svg)

*Figure 3-2.* The QM host stack (left) reaches the panda envelope (ASIL C) through SPI4 (USB, not used by the reference device, is not drawn). Inside the panda, boxes are the units of §3.1 with their functions as chips; U-PND-FDCAN spans the TX and RX chips (dashed region). Orange lines are the command and actuation path, teal lines CAN reception, forwarding and data back to the SoC, grey lines control requests and internal calls; each tag is an interface ID of §3.3. The bridge on the TX line marks a crossing without a connection. Source: [`figures/fig-w03-3-2-panda-software-architecture.svg`](figures/fig-w03-3-2-panda-software-architecture.svg); change it together with §3.1, §3.3 and §5.1. The text version below is the more detailed one (pins as stated); the figure does not show the **[ref]** marks.

<details><summary>Text version of Figure 3-2</summary>

```
          SoC (pandad)                       panda STM32H7 (one address space, no MPU)
   ───────────────────────────    ┌──────────────────────────────────────────────────────────────────┐
     SPI4 transfers  ─────────────┼─▶ U-PND-SPI (DMA2 Stream2 IRQ) ──ctrl──▶ comms_control_handler    │
     (hdr+data, XOR)              │     │                    [ref] reference_request_allowed ─ refuse │
                                  │     │                    │ 0xdc ─▶ set_safety_mode ─(critical)─▶  │
                                  │     │                    │           U-SAF-CORE set_safety_hooks  │
                                  │     │                    │ 0xf3 ─▶ heartbeat vars, heartbeat_monitor_reset
                                  │     │                    └ 0xc5 ─▶ U-PND-HARN relay (+IWDG start) │
                                  │     └─can write─▶ comms_can_write ─▶ can_send ─▶ safety_tx_hook   │
                                  │                     whitelist ─▶ [ref] tx_rate_check (may revoke) │
                                  │                     ─▶ U-SAF-TOY tx ([ref] EPS-fault gate)       │
                                  │                        ─▶ U-SAF-LAT/LONG                         │
                                  │                                          │ accept   │ reject     │
                                  │                       can_queues[bus] ◀──┘          └▶ rx_q      │
                                  │                            │ process_can (XOR check)              │
   bus 0 car side ◀═══════════════╪══ FDCAN1/3 TX FIFO ◀───────┘                                     │
   bus 0/2 RX ════════════════════╪══▶ can_rx: safety_fwd_hook ─▶ can_send(skip hook) other bus      │
                                  │            safety_rx_hook ─▶ U-SAF-TOY rx ─▶ controls_allowed     │
                                  │              ([ref] eps_fault, cruise-main; grant gated by        │
                                  │               rx_checks_allow_engagement)                         │
                                  │            can_push(rx_q) ─▶ comms_can_read ─▶ SPI to SoC        │
                                  │  TIM4 safety task 100 Hz: safety_tick (RX timeout), heartbeat    │
                                  │     monitor (0.3 s → revoke), hw_watchdog_tick (IWDG1 feed)      │
                                  │     EPS-fault siren (b790fca), heartbeat-loss siren (c33343b)    │
                                  │  TIM12 tick 8 Hz: harness, simple_watchdog_kick, siren           │
                                  │     └ 1 Hz: heartbeat counter → SILENT, engaged mismatch,        │
                                  │             check_registers                                       │
                                  │  TIM6 interrupt-rate statistics                                   │
                                  │  main loop: hw_watchdog_main_loop_alive, LED fade / WFI          │
                                  └──────────────────────────────────────────────────────────────────┘
```

</details>

The same firmware, grouped by execution context, is also drawn as a Simulink-style block diagram generated by [`diagrams/make_diagrams.py`](diagrams/make_diagrams.py) (design description; CI checks it is current). Dashed frames are interrupt contexts, dashed blocks are reference build only, and the thin dashed lines are writes (W) and reads (R) of the shared authority flag `controls_allowed` (§6.3). Block colours give the block kind; the legend is in the figure. It was drawn from the text version at panda `8aa8671` and does not yet show the changes merged from the base (panda `c33343b`, `b790fca`).

![Panda firmware block diagram](diagrams/simulink-panda-firmware.svg)

The signal flow inside the envelope, for the Toyota reference build, is also drawn as a Simulink-style block diagram (generated, design description): [`diagrams/simulink-envelope.svg`](diagrams/simulink-envelope.svg).

![Safety envelope block diagram](diagrams/simulink-envelope.svg)

### 3.3 Interfaces between components

Pins: panda `8aa8671`, opendbc `7993399`.

| ID | Provider → user | Interface | Data | Safety relevance |
|---|---|---|---|---|
| SI-01 | U-SAF-CORE → U-PND-FDCAN | `safety_rx_hook(const CANPacket_t*)`, `safety_fwd_hook(bus, addr)` | RX frame; return validity / destination bus | C |
| SI-02 | U-SAF-CORE → U-PND-FDCAN (`can_send`) | `safety_tx_hook(CANPacket_t*)` | TX frame; accept/reject. In the reference build it can also clear `controls_allowed` (`tx_rate_check`) | C |
| SI-03 | U-SAF-CORE → U-PND-MAIN | `set_safety_hooks(mode, param)`, `safety_tick()` | mode, param; return status | C |
| SI-04 | U-SAF-CORE → U-PND-COMMS/MAIN | globals: `controls_allowed`, `relay_malfunction`, `safety_rx_checks_invalid`, `safety_eps_fault`, `safety_tx_rate_exceeded`, `heartbeat_engaged`, `heartbeat_engaged_mismatches`, `current_safety_mode/param`, `safety_mode_cnt`, `alternative_experience` | shared state (§6.3) | C |
| SI-05 | U-SAF-TOY → U-SAF-CORE | `toyota_hooks` table (`modes/toyota.h:565-572`) | function pointers init/rx/tx/checksum/quality | C (ENV-R-06: constant table) |
| SI-06 | U-SAF-LAT/LONG → U-SAF-TOY | `steer_torque_cmd_checks`, `longitudinal_accel_checks` | value, limits struct; violation flag | C |
| SI-07 | U-PND-SPI → U-PND-COMMS | `comms_control_handler`, `comms_can_write`, `comms_can_read` | `ControlPacket_t`; byte streams | C |
| SI-08 | U-PND-COMMS → U-PND-MAIN | `set_safety_mode` prototype (`main_comms.h:6`) | mode/param | C |
| SI-09 | U-PND-FDCAN ↔ U-PND-COMMS | `can_rx_q`, `can_queues[]` ring buffers with `can_push`/`can_pop` | `CANPacket_t` | C |
| SI-10 | U-PND-HARN → U-PND-MAIN/COMMS | `set_intercept_relay`, `harness.status`, `harness_check_ignition` | relay, orientation | C/B |
| SI-11 | U-PND-FLT → all | `fault_occurred`, `fault_recovered`, `faults`, `REGISTER_INTERRUPT` | fault bits | C (report-only) |
| SI-12 | Platform → all | `microsecond_timer_get` (µs counter, `drivers/timers.h:16-18`), `ENTER_CRITICAL/EXIT_CRITICAL` (`sys/sys.h:10-22`) | time base, IRQ masking | C |
| SI-13 | U-PND-COMMS → SoC | health packet `0xd2` (`main_comms.h:8-61`); LionDriver flags `HEALTH_FLAG_WATCHDOG_RESET`, `_EPS_FAULT`, `_TX_RATE_EXCEEDED` (`health.h:12-14`) and `requests_rejected_pkt` (`main_comms.h:27-31`, non-zero only in the reference build) | flags, counters, faults | QM consumer (SWSR-615) |
| SI-14 | U-PND-COMMS → U-PND-MAIN (heartbeat monitor) | `heartbeat_monitor_reset()` on `0xf3` (`main_comms.h:301`); `heartbeat_monitor_tick()` in the safety task (`main.c:135`) | `heartbeat_age_ticks` | C |
| SI-15 | U-PND-MAIN / U-PND-HARN → U-PND-FLT (hw watchdog) | `hw_watchdog_start()` (`harness.h:20`), `hw_watchdog_main_loop_alive()` (`main.c:122`), `hw_watchdog_tick()` (`main.c:138`) | IWDG state, main-loop flag | C |
| SI-16 | U-PND-COMMS → reference lock **[ref]** | `reference_request_allowed(const ControlPacket_t*)` (`reference_lock.h:18`); a refused request is mapped to `0x00`, which has no handler (`main_comms.h:74-79`) | request, mode | C |

## 4. Static architecture: host stack (E-01)

### 4.1 Components relevant to safety

Pin: superproject `682f184`, paths under `openpilot/`.

| Element name | Process / module | Role | Class | SWSRs |
|---|---|---|---|---|
| `host.pandad` | `selfdrive/pandad/{pandad.py, pandad.cc, panda.cc, spi.cc, panda_safety.cc}` | Firmware check/flash, SPI link, CAN in/out, heartbeat, safety-mode set | QM (B-sup); FFI interface | 409h, 410h, 414h, 514h |
| `host.card` | `selfdrive/car/card.py` + `opendbc/car/toyota/{carcontroller,carstate,interface,values}.py` | CAN parse → `carState`; `carControl` → `sendcan`; CarParams/fingerprint | QM (B-sup) | 303h, 605, 607 |
| `host.controlsd` | `selfdrive/controls/controlsd.py` | Lateral/longitudinal control law | QM (B-sup) | 602, 604, 605 |
| `host.selfdrived` | `selfdrive/selfdrived/{selfdrived,events,state}.py` | Engagement state machine, event classification, alerts | QM (B-sup) | 307h, 308h, 601, 603, 606, 615, 617, 618 |
| `host.plannerd`, `host.radard` | `selfdrive/controls/plannerd.py`, `radard.py` | Longitudinal plan, lead fusion | QM (SOTIF) | — |
| `host.modeld` | `selfdrive/modeld/modeld.py` | Driving model | QM (SOTIF / PAS 8800) | 603, 616 |
| `host.dm` | `dmonitoringmodeld.py`, `selfdrive/monitoring/{dmonitoringd,policy}.py` | Driver monitoring | QM (SOTIF) | 608–612 |
| `host.hmi` | `ui`, `soundd` | Alerts | QM (B-sup) | 606 |
| `host.manager` | `system/manager/{manager,process_config}.py` | Process start/stop by run condition | QM | 613 |
| `host.cereal` | `cereal/`, `msgq` | Pub/sub, alive/valid/freq checks | QM | 601a |

### 4.2 Data flow (per control frame)

Rates from `cereal/services.py` (`682f184`, `openpilot/cereal/services.py:33-73`). Consumers and alive limits as in [WP-S-03 §9](../03-system/WP-S-03-technical-safety-concept-architecture.md). Target freshness values are in §10.

| Producer → service → consumer | Rate | Safety use | Freshness at the baseline |
|---|---|---|---|
| modeld → `modelV2` → controlsd, plannerd, selfdrived | 20 Hz | desired path/curvature | alive 0.5 s |
| plannerd → `longitudinalPlan` → controlsd | 20 Hz | accel target | 0.5 s |
| card → `carState` → controlsd, selfdrived | 100 Hz | vehicle state | 0.1 s |
| selfdrived → `selfdriveState` → controlsd, pandad | 100 Hz | enabled/active | 0.1 s |
| controlsd → `carControl` → card | 100 Hz | actuator request | card sends only if alive (`selfdrive/car/card.py:234-238`) |
| card → `sendcan` → pandad → SPI → panda | 100 Hz | CAN frames | pandad drops > 1 s (`selfdrive/pandad/pandad.cc:78-79`); panda: **[ref]** TX rate budget per ID, no freshness check |
| pandad → `0xf3` heartbeat → panda | 10 Hz (host rate not confirmed) | engaged flag | panda: authority revoked after 0.3 s without heartbeat in a car mode (safety task, `heartbeat_monitor.h:15`); SILENT after 5 s (ignition on) / 2 s (off) (1 Hz tick, `main.c:116-117, 235-270`) |
| panda → health → pandad → `pandaStates` → selfdrived | 10 Hz | authority, faults | mismatch 2 s at `682f184`; on the base (host supervision change, 2026-10-13): `controlsMismatch` after 2 consecutive samples, ≤ 0.5 s (SWSR-621); heartbeat-lost, TX-rate and rising `safetyTxBlocked` flags disable at once (SWSR-615, partly) |

The same flow as a Simulink-style block diagram (generated by [`diagrams/make_diagrams.py`](diagrams/make_diagrams.py), design description). The engagement chart in `selfdrived` is [WP-W-05 §5.3](WP-W-05-software-unit-design.md); the panda block is the subsystem drawn in §3.2.

![Host engagement and control data flow](diagrams/simulink-host.svg)

## 5. Dynamic behaviour

### 5.1 Execution model of the panda firmware

Pin: panda `8aa8671` (opendbc `7993399` for the hooks). All envelope processing runs in **interrupt context**. The main loop (`main.c:386-420`) only marks progress for the hardware watchdog (`main_loop_progress`, `:121-126`), fades the LED or waits in `__WFI()`.

| Context | Trigger | NVIC level | Code executed | Envelope functions called |
|---|---|---|---|---|
| FDCANx IT0 (RX) | frame received, per bus | 8 (`IRQ_PRIO_CAN`) | `can_rx` (`drivers/fdcan.h:154-243`) | `safety_fwd_hook`, `safety_rx_hook` (grant via `pcm_cruise_check`, revocations), `ignition_can_hook` |
| FDCANx IT1 (TX) | TX FIFO empty / `process_can` | 8 (`IRQ_PRIO_CAN`) | `process_can` (`drivers/fdcan.h:88-150`) | none (XOR check only) |
| DMA2 Stream2 (SPI RX done) | end of MOSI DMA | 8 (`IRQ_PRIO_HOST`) | `spi_rx_done` (`drivers/spi.h:106`) via `stm32h7/llspi.h:56-61` | via `comms_control_handler` (`spi.h:143`): **[ref]** `reference_request_allowed`, `set_safety_mode` → `set_safety_hooks`, heartbeat; via `comms_can_write` (`spi.h:162`) → `can_send` (`can_comms.h:97, 118`) → `safety_tx_hook` (`can_common.h:162`), incl. **[ref]** `tx_rate_check` revocation |
| DMA2 Stream3, SPI4 | MISO done | 8 (`IRQ_PRIO_HOST`) | `DMA2_Stream3_IRQ_Handler`, `spi_tx_done` (`llspi.h:64-83`) | none |
| USB OTG_HS | USB transfer | 8 (`IRQ_PRIO_HOST`) | `drivers/usb.h` | same comms handlers (`usb.h:616` → `comms_can_write`) |
| TIM4 safety task | 100 Hz (`drivers/timers.h:30-38`, `SAFETY_TASK_FREQ` `stm32h7_config.h:41`) | 8 (`IRQ_PRIO_SAFETY_TASK`) | `safety_task_handler` (`main.c:130-144`) | `safety_tick` (RX timeout and validity), heartbeat monitor (revokes after 0.3 s in a car mode), EPS-fault siren (`drivers/eps_fault_siren.h`, panda `b790fca`), heartbeat-loss siren (`drivers/heartbeat_siren.h`, panda `c33343b`), `hw_watchdog_tick` (IWDG feed) |
| TIM12 tick | 8 Hz (`drivers/timers.h:40-43`) | 8 (`IRQ_PRIO_HOUSEKEEPING`) | `tick_handler` (`main.c:147-290`) | 8 Hz: harness, software watchdog kick, siren, `set_safety_mode` on harness change (`:176-184`); 1 Hz: heartbeat counter and SILENT after 5 s/2 s, `heartbeat_engaged` mismatch revocation (`:226-233`), `check_registers` |
| TIM6 | interrupt-rate timer (`drivers/timers.h:20-28`) | 8 (`IRQ_PRIO_HOUSEKEEPING`) | `interrupt_timer_handler` (`drivers/interrupts.h:50`) | rate statistics |
| Thread mode | main loop | lowest | `main.c:386-420` | none (writes only `hw_watchdog_main_loop_ran`) |
| NMI / HardFault | exception | fixed | `early_init.h:73-81` | reset |

**Priorities.** Every enabled interrupt gets an explicit priority from `interrupt_priorities_init()` (`drivers/irq_priorities.h:21-46`), called before any interrupt is enabled (`main.c:297-300`). All five classes are at level 8 (`irq_priorities.h:15-19`); the distinct levels of §5.4.2 are not adopted. Equal priority means no preemption between interrupts: each handler runs to completion and pending handlers are served in exception-number order. Consequences: (i) envelope state is never accessed concurrently by two interrupts, and the main loop does not write envelope state, which keeps the single-writer argument of §6.3 simple; (ii) a long handler (e.g. a CAN burst or `set_safety_mode` → `can_init_all`) delays every other handler, including the safety task; (iii) the safety task cannot preempt a hung handler; a hang in any interrupt or in the main loop stops the IWDG feed (`hw_watchdog.h:66-76`) and ends in a reset, once the IWDG has been started (§3.1). `ENTER_CRITICAL` masks all interrupts (`sys/sys.h:10-14`). This matches [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) FFI-SP-04 and GAP-50. Entry latency and jitter of the safety task are **not measured** (§5.4.5).

### 5.2 Tick and task schedule

Pin: panda `8aa8671`. At `8b8c6ae` (panda `92eb565`) RX timeouts were evaluated in the 1 Hz part of the tick and there was no safety task.

| Period | Context | Activity | Lines |
|---|---|---|---|
| 10 ms | TIM4 safety task | `safety_tick` (RX timeout: Toyota 5 nominal periods, `modes/toyota.h:83`; validity; minimum frequency), heartbeat monitor (authority revoked after 0.3 s in a car mode), EPS-fault siren (1 s persistence, 3 s hold; panda `b790fca`), heartbeat-loss siren (3 s hold from that revocation if authority was granted; panda `c33343b`), IWDG feed if the main loop has run | `main.c:130-144` (at `8aa8671`) |
| 125 ms | TIM12 tick | siren toggle, `fan_tick`, `harness_tick`, `simple_watchdog_kick`, `sound_tick`, relay-fault reporting, harness re-init and `set_safety_mode` on harness change | `main.c:154-184` |
| 1 s | TIM12 tick (every 8th) | LEDs, ignition, `bootkick_tick`, heartbeat counter, `heartbeat_engaged` mismatch (3 ticks) → revoke, heartbeat loss → SILENT (5 s ign on / 2 s off), siren countdown, `check_registers`, CAN ignition timeout, counters | `main.c:187-284` |
| main loop | thread mode | `hw_watchdog_main_loop_alive` on every iteration and every LED fade step | `main.c:121-126, 386-409` |

At `8aa8671` the safety task does not yet run command freshness (TSR-408; implemented in the reference build at opendbc `273f44e`, WP-W-02 SWSR-408), SPI error rate, relay readback or the platform monitors; these are target-state items (§10, ATC-01).

### 5.3 Message flow per control frame (lateral, 10 ms)

Pins: panda `8aa8671`, opendbc `7993399`, superproject `682f184`.

1. `card` packs `0x2E4` into `sendcan`; `pandad` send thread checks age < 1 s (`selfdrive/pandad/pandad.cc:78-79`) and writes it over SPI endpoint 3.
2. DMA2 Stream2 IRQ → `spi_rx_done`: header XOR checked (`drivers/spi.h:122`), then data DMA of `spi_data_len_mosi + 1` bytes (`:233`), then data XOR (`:137`).
3. `comms_can_write` reassembles `CANPacket_t` (`can_comms.h:83-129`) → `can_send(…, false)` (`drivers/can_common.h:161`).
4. `safety_tx_hook` (`safety.h:283-302`): whitelist (`:284`, `tx_msg_safety_check` `:232-241`) → **[ref]** `tx_rate_check` (`:292`) → `toyota_tx_hook` (**[ref]** EPS-fault gate `modes/toyota.h:428-430`) → `steer_torque_cmd_checks` (`lateral.h`) → relay check (`safety.h:301`).
5. Accept: `can_push(can_queues[0])`, `process_can` writes the FDCAN TX FIFO after the packet XOR check (`drivers/fdcan.h:100`) and echoes the frame to `rx_q`. Reject: `safety_tx_blocked++`, frame returned to `rx_q` with `rejected=1` (`can_common.h:168-175`).
6. EPS answers on `0x260` at 50 Hz → FDCAN RX ISR → forwarded to bus 2 → `safety_rx_hook` updates `torque_meas` used by the next check; **[ref]** `0x262` updates `safety_eps_fault`.

Worst-case latency step 2→5 is **not measured** (VS-SWI-15, VS-SWQ-23).

### 5.4 Interrupt priority scheme (proposed, SWSR-519, OI-4)

**Status: proposal for review; the distinct levels are not implemented** (all classes at level 8, `irq_priorities.h:15-19`, panda `8aa8671`). Analysis first made at panda `c2e5d93`, opendbc `5b5a4ba`; R-2 and R-5 re-checked at panda `8aa8671`, opendbc `7993399` for the TX-hook revocation (SWSR-518). The timing claims below are design targets until measured on the target (§5.4.5).

#### 5.4.1 Why equal priority is not enough

With every interrupt at one level, the safety task waits behind whichever handler is running. Its entry latency is bounded only by the longest handler or critical section anywhere in the firmware. Candidates for long ones are `set_safety_mode` (it calls `set_safety_hooks` and `can_init_all`, which wait for the FDCAN init handshake), a burst of CAN frames on three buses (each `can_rx` runs the forward and RX hooks per frame), and SPI control requests. None of these has a measured WCET.

Two budgets depend on that latency:

- **TSR-401 / TSR-407 detection times.** RX timeout ≤ 0.2 s and heartbeat ≤ 0.3 s each include one task period (10 ms). A delayed task run adds its delay directly.
- **IWDG window mode (HWSR-501b).** A feed is rejected, and the MCU reset, if it comes less than about 5 ms after the previous feed (WINR 679 of RLR 719, `hw_watchdog.h:36-37`; 4.5–5.6 ms over an assumed ±10 % LSI range, not confirmed from the datasheet). The task timer runs on a fixed period, so if one run is delayed by *d* and the next is not, the two feeds are 10 ms − *d* apart. **Entry-latency jitter above about 4.4 ms therefore causes a spurious watchdog reset.** The window that guards against a runaway task also makes the safety task's jitter a reset cause.

#### 5.4.2 Proposed priorities

The Cortex-M7 in the STM32H725 implements 4 priority bits (`__NVIC_PRIO_BITS` = 4; 16 levels, 0 highest). With the default grouping all bits are preemption bits. Proposed assignment, to be set in `irq_priorities.h` (the five `IRQ_PRIO_*` values):

| Priority | Interrupts | Rationale |
|---|---|---|
| 2 | TIM4 safety task | Must preempt all comms so that RX-timeout, heartbeat and IWDG timing hold under any bus or host load |
| 4 | FDCAN1–3 IT0 (RX: forward hook, RX hook), FDCAN1–3 IT1 (TX completion) | RX hook revokes authority on invalid input; it must not wait behind host commands |
| 6 | DMA2 Stream2/3, SPI4 (host commands, TX hook), USB OTG | Host-side path; a busy or misbehaving host must not delay CAN reception or the safety task |
| 8 | TIM12 tick (8 Hz/1 Hz housekeeping, 5 s SILENT path), TIM6 interrupt-rate timer | Housekeeping; their timing needs are in seconds |
| 10 | BDMA/DMA1 sound, EXTI fan tachometer and wake-up lines | Not safety-related |

Levels 0–1 stay free for a possible future high-priority supervisor, and odd levels for insertion. NMI and HardFault keep their fixed priorities.

#### 5.4.3 Race analysis under the proposed scheme

Preemption creates the concurrent access that equal priority prevents (§5.1 consequence (i)). Each shared item of §6.3 under the proposal:

| # | Shared data | Access under the proposal | Hazard | Measure under the proposal |
|---|---|---|---|---|
| R-1 | `current_safety_config`, `current_hooks`, `current_safety_mode/param` | Written by `set_safety_hooks` (SPI ISR via `0xdc`, priority 6; tick via 5 s heartbeat loss or harness change, priority 8). Read by `safety_tick` (safety task, priority 2), which iterates `rx_checks[0..rx_checks_len)` | **Out-of-bounds read** if the safety task preempts `set_safety_hooks` between the copy of `rx_checks` and of `rx_checks_len` | In place: both `set_safety_hooks` calls run in `ENTER_CRITICAL` (`main.c:43-45, 49-51`). Section length to be measured (§5.4.5) |
| R-2 | `controls_allowed` | Granted only in the RX path (`pcm_cruise_check`, `safety.h:607`, priority 4). Revoked by the RX path (priority 4: `safety.h:119, 431, 437, 443, 604`; **[ref]** `modes/toyota.h:136, 141`), the safety task (priority 2: `safety.h:119, 415`; `main.c:136`), the tick (priority 8: `main.c:229`), the host path (priority 6: **[ref]** TX-hook revocation `safety.h:269-272`), and `set_safety_hooks` (`safety.h:534`, in a critical section) | **Lost revocation.** If the safety task preempts the grant between `rx_checks_allow_engagement()` and the store of `true`, its revocation is overwritten. All safety-task revocations are condition-based and re-evaluated every period, so the loss lasts at most one period (10 ms). The TX-hook revocation (priority 6) cannot preempt the grant (priority 4), so it cannot be lost this way; see the TX-hook paragraph below | Bound recorded (WP-W-04 SWF-48); single-writer API is a target item (§10, ATC-09) |
| R-3 | `rx_checks[i].status` fields | Written by the RX hook (priority 4); read by `safety_tick` (priority 2) | Torn **set** of fields: the task may see a frame's new timestamp with its old checksum result. Each field is a single aligned 8/16/32-bit store and is atomic | Accept: at most one period of stale evaluation, then consistent |
| R-4 | `heartbeat_age_ticks` (heartbeat monitor) | Reset by `0xf3` (SPI ISR, priority 6); read-modify-written by the safety task (priority 2) | A reset preempted by the task (single store) cannot tear. The task's increment cannot be preempted by the lower-priority SPI ISR | None |
| R-5 | TX hook state (`desired_torque_last`, `rt_torque_last`, …; **[ref]** `tx_rate_checks[].status`, `safety_tx_rate_exceeded`) and `controls_allowed` read in the TX hook | TX hook runs in the host ISR (DMA2 Stream2 or OTG_HS, priority 6); safety task (2) and RX hook (4) can preempt it. **[ref]** `tx_rate_check` reads `controls_allowed` and may store `false` (`safety.h:269-272`); `tx_rate_checks[].status` is written only by the TX hook and reset by `set_safety_hooks` (`safety.h:558-562`) | **One frame after revocation.** The TX hook reads `controls_allowed` as true, is preempted by a revocation, then passes the frame. Bounded to one frame per revocation (≤ 10 ms of `0x2E4`), inside the TSR-406 reaction time of 0.1 s. **[ref]** A grant by the RX hook between `tx_rate_check`'s read (true) and its store of `false` is cleared again (fail-safe direction). Both host ISRs are at priority 6 and cannot preempt each other, so the rate-window state is not torn | Accept and record, or re-check `controls_allowed` with interrupts masked just before the FDCAN TX load (§10, ATC-18) |
| R-6 | `can_rx_q`, `can_queues[]` | RX ISR, SPI ISR, FDCAN IT1 | Already protected by `ENTER_CRITICAL` (`drivers/can_common.h:45, 64, 85, 97`) | None. These sections delay the safety task too; include them in the measurement |
| R-7 | `hw_watchdog_main_loop_ran` | Set by the main loop (thread mode, `hw_watchdog.h:61-63`); read and cleared by the safety task (`:70-72`) | Single byte, `volatile`; atomic | None |
| R-8 | `faults`, `fault_status` | Bit-OR from any ISR | Lost bit on preemption | In place: `fault_occurred` and `fault_recovered` run in a critical section (`sys/faults.h:10-11, 25-26`) |

**TX-hook revocation (SWSR-518, [ref]) — author analysis, needs I1 review.** Code reading at opendbc `7993399`, panda `8aa8671`:

- *Calling context.* `safety_tx_hook` runs in the DMA2 Stream2 IRQ (`llspi.h:56-61` → `spi_rx_done` `spi.h:106` → `comms_can_write` `spi.h:162` → `can_send` `can_comms.h:97, 118` → `can_common.h:162`) or, if USB is used, in the OTG_HS IRQ (`usb.h:616`). Both are `IRQ_PRIO_HOST` (`irq_priorities.h:17`, set at `:31-34`). The forwarding path calls `can_send` with the hook skipped (`fdcan.h:213`), so the CAN RX ISR never runs `tx_rate_check`.
- *Writers and readers of `controls_allowed` at the baseline.* Writers: CAN RX ISR (grant and revocations), safety task (revocations), tick (revocation; `set_safety_hooks` on heartbeat loss or harness change), host ISR (TX-hook revocation; `set_safety_hooks` via `0xdc`). Readers: TX hook (`lateral.h:64, 99, 141`; `safety.h:269`), tick (`main.c:191, 217, 226`), RX hook (`safety.h:202, 225`), health packet (`main_comms.h:19`, host ISR). Thread mode does not write it at run time; `main()` calls `set_safety_mode` only before interrupts are enabled (`main.c:339, 383`). All writer contexts are at level 8, so no interleaving is possible today: each read-check-store sequence completes before another writer runs.
- *Under the §5.4.2 proposal.* The TX-hook revocation stores only `false`, so its store cannot grant authority. It cannot be lost by interleaving: the only grant (`safety.h:607`, priority 4) either completes before the TX hook runs (and is then cleared) or preempts it between read and store (and is then cleared, R-5). The R-2 window (safety task preempting the grant) does not involve the TX hook. The revocation is also re-issued on every further over-budget frame, because `status.rejected` is reset only at a half-window boundary (`safety.h:255-261`).
- *Re-grant after a TX-hook revocation.* Authority returns only on a new PCM cruise rising edge (`safety.h:606-607`; the revocation does not touch `cruise_engaged_prev`). `rx_checks_allow_engagement` (`safety.h:390-401`) checks RX checks only, not `safety_tx_rate_exceeded` or the TX rate state, so a rising edge during a continuing flood re-grants until the next rejected frame revokes again. This is the same in every priority scheme and is a requirement question, not a race (reported to the requirement owner; WP-W-02 SWSR-518 does not say whether re-engagement must be inhibited).
- *Conclusion (author, not reviewed).* At the baseline and under the proposal, no interleaving re-grants authority through the TX-hook path or loses a TX-hook revocation. The residual effects are R-2 (10 ms, safety-task revocations only) and R-5 (one frame).

#### 5.4.4 Changes needed before the scheme can be enabled

| # | Change | Status (panda `52cad44`, [jherrodthomas/panda#10](https://github.com/jherrodthomas/panda/pull/10); unchanged at `8aa8671`) |
|---|---|---|
| 1 | Mask the safety task during `set_safety_mode` / `set_safety_hooks` (R-1). Mandatory: without it the proposal introduces an out-of-bounds read | **Done:** both `set_safety_hooks` calls in `set_safety_mode` run in `ENTER_CRITICAL`/`EXIT_CRITICAL` (`main.c:43-45, 49-51`) |
| 2 | Make the grant in `pcm_cruise_check` atomic with respect to the safety task (R-2), or record the 10 ms bound in WP-W-04 | **Bound recorded** ([WP-W-04](WP-W-04-software-safety-analysis.md) SWF-48): opendbc has no critical-section primitive, and every safety-task revocation is re-evaluated each period, so a lost revocation lasts at most one task period (10 ms) plus its jitter |
| 3 | Make `fault_occurred` atomic (R-8) | **Done:** `fault_occurred` and `fault_recovered` run in a critical section |
| 4 | Add the priority table and set it before the first `NVIC_EnableIRQ` (§5.1) | **Done:** `board/drivers/irq_priorities.h`, `interrupt_priorities_init()` before `clock_init()`. All classes at level 8. Host test `tests/irq_priorities` checks that every `NVIC_EnableIRQ` site has an entry and that the classes are still equal |
| 5 | Host tests cannot show the timing; it needs the target measurement below | Open (D-04) |

Adopting §5.4.2 is a change of the five `IRQ_PRIO_*` values and of the `test_classes_equal_until_scheme_adopted` host test, after the §5.4.5 measurements (§10, ATC-04).

#### 5.4.5 Measurement plan (target, HIL bench D-04)

| Measurement | Method | Acceptance |
|---|---|---|
| Safety-task entry latency and jitter | GPIO toggled at entry and exit of `safety_task_handler`, scope or logic analyser, 10 min per load case | Jitter < 4 ms (IWDG window margin, §5.4.1); worst-case latency < 1 ms with the proposed priorities |
| Load cases | (a) idle; (b) three CAN buses at maximum bus load from the jungle; (c) host SPI at maximum rate with control requests; (d) repeated `0xdc` mode changes; (e) all at once | All cases meet the acceptance above |
| Longest masked section | GPIO around `set_safety_mode` and every `ENTER_CRITICAL` site, under load case (e) | Below the jitter budget, with the result recorded |
| Equal-priority baseline | The same measurements at panda `8aa8671` (all classes at level 8) | Gives the evidence for or against keeping equal priority (§5.4.6) |

#### 5.4.6 Alternative: keep equal priority

If the baseline measurement shows that the longest handler or critical section stays well below 4 ms under load case (e), equal priority can be kept and R-1…R-8 do not arise. The argument then rests on measured WCET of every handler, which has to be re-measured on every change to any ISR. The proposal in §5.4.2 instead bounds the safety task's latency by construction, at the cost of the measures in §5.4.4. Recommendation: measure the baseline first; adopt §5.4.2 with the §5.4.4 measures unless the baseline margin is large.

### 5.5 Start-up and mode-set sequence

Pins: panda `8aa8671`, opendbc `7993399`, superproject `682f184`.

| Step | Actor | Action | Lines |
|---|---|---|---|
| 1 | bootstub | length, SHA-1, RSA check, jump or soft flasher; IWDG not started | `bootstub.c:33-82` |
| 2 | main | interrupt table, interrupts disabled, `interrupt_priorities_init`, clocks, peripherals, board detect, ADC, DTS | `main.c:294-311` |
| 3 | main | board init, `harness_init` (relay released) | `main.c:324-326` |
| 4 | main | `set_safety_mode(SILENT)`; CAN transceivers on; software watchdog; 8 Hz tick; 100 Hz safety task; USB; SPI | `main.c:339-361` |
| 5 | main | NMI/HardFault/IWDG reset causes recorded in `reset_flags`; interrupts enabled; idle loop | `main.c:367-386` |
| 6 | pandad | ELM327 for fingerprinting | `selfdrive/pandad/panda_safety.cc:23-34` |
| 7 | card / pandad | CarParams → `0xdf` alternative experience and `0xdc` TOYOTA, param 73 | `panda_safety.cc:55-69`. **[ref]** `0xdf` is refused and counted (`reference_lock.h:30-32`); `0xdc` passes only with param 73 |
| 8 | panda | `set_safety_hooks` resets state (in a critical section); relay driven → `hw_watchdog_start` (first time); CAN re-init | `main.c:43-45, 84-92`; `harness.h:16-21`; `safety.h:467-565` |
| 9 | PCM | CRUISE_ACTIVE rising edge → `controls_allowed = rx_checks_allow_engagement()` | `safety.h:601-610` |

### 5.6 Safety-mode state machine (panda)

Pins: panda `8aa8671`, opendbc `7993399`. Host requests are `0xdc`; internal changes (heartbeat loss, failed mode set, harness change) do not pass through the reference lock (`reference_lock.h:12`).

| State | Relay | CAN | Entry | Exit (standard build) | Exit (reference build **[ref]**, `reference_lock.h:22-29`) |
|---|---|---|---|---|---|
| SILENT | released | silent | reset, heartbeat loss (5 s/2 s), failed mode set (`main.c:46-54`) | `0xdc` any registered mode | `0xdc` NOOUTPUT, ELM327, TOYOTA param 73 |
| NOOUTPUT | released | normal, TX hook rejects all | `0xdc` | `0xdc` any | as SILENT |
| ELM327 | released | OBD mux per param | `0xdc` | `0xdc` any | as SILENT |
| TOYOTA | driven | normal | `0xdc` TOYOTA (standard: any param; **[ref]**: param 73 only) | `0xdc` any; heartbeat loss → SILENT | `0xdc` NOOUTPUT or SILENT only; heartbeat loss → SILENT |
| other brand modes | driven | normal | `0xdc` (standard build only) | `0xdc` any; heartbeat loss → SILENT | not reachable |

There is no latched fault state; faults are report-only (`sys/sys.h:50`). The target fault state SS-S is ATC-05 in §10.

## 6. Partitioning and freedom from interference at software level

### 6.1 Mechanisms present

Pins: panda `8aa8671`, opendbc `7993399`.

| Mechanism | Effect | Build | Evidence |
|---|---|---|---|
| Single entry for actuation | Every SoC frame passes `safety_tx_hook`; forwarded frames skip it but use the static block list | both | `drivers/can_common.h:161-162`; `drivers/fdcan.h:213`; `safety.h:304-337` |
| Constant hook table | Brand behaviour selected only through `set_safety_hooks` | both | `safety.h:467-565` |
| Atomic configuration switch | `set_safety_hooks` runs with all interrupts masked | both | `main.c:43-45, 49-51` |
| Host-request lock | Mode/parameter whitelist; configuration requests refused in car modes; refused requests counted and reported | **[ref]** | `reference_lock.h:13-63`; `main_comms.h:74-79` |
| TX rate supervision | Per-ID budget; flood rejected before the content checks; persistent excess revokes authority | **[ref]** | `safety.h:243-281, 290-294`; `modes/toyota.h:545-560` |
| EPS-fault gate | Lateral torque/steer request refused while LKA_STATE is in the fault set | **[ref]** | `modes/toyota.h:91-116, 425-434` |
| RX timeout and engagement gating | RX checks time out after 5 nominal periods (Toyota); no grant while any RX check lags or is invalid | both (Toyota) | `safety.h:373-401`; `modes/toyota.h:83, 543` |
| Periodic safety task | RX timeout and heartbeat evaluated at 100 Hz, independent of the 8 Hz tick | both | `main.c:130-144` |
| Hardware watchdog with main-loop checkpoint | IWDG1 window mode; fed only from the safety task after main-loop progress; started on first relay drive | both | `hw_watchdog.h`; `harness.h:20` |
| Explicit interrupt priorities | Every enabled IRQ has a documented level (all equal); run-to-completion, no concurrent access to envelope state | both | `irq_priorities.h`; §5.1 |
| Critical sections on ring buffers and fault word | Queue and fault-bit integrity | both | `drivers/can_common.h:45, 64, 85, 97`; `sys/faults.h:10-11, 25-26` |
| Packet XOR from TX hook to FIFO | Detects corruption in the TX queue | both | `drivers/fdcan.h:100` |
| Memory placement | SPI buffers in SRAM1/2, RX queue in AXI SRAM, TX queues 1–2 in ITCM | both | `drivers/spi.h:7-8`; `drivers/can_common.h:26-29` |

### 6.2 Mechanisms missing

Each item was checked against the code at panda `8aa8671`, opendbc `7993399`. The changes are tracked in §10.

| Missing | Evidence of absence | Consequence | SWSR | §10 |
|---|---|---|---|---|
| MPU configuration | No MPU set-up outside the CMSIS header (`board/stm32h7/inc/mpu_armv7.h`) | Any comms defect can overwrite envelope state | 507 | ATC-07 |
| Bounds checks on SoC lengths/indices | `spi_data_len_mosi` from the header used for DMA length and checksum without a check against `SPI_BUF_SIZE` (`drivers/spi.h:115, 137, 233`); `0xe8` indexes `bus_config[param1]` unchecked (`main_comms.h:283`; **[ref]** refused in car modes only) | DMA/array overrun from the QM SoC | 412, 412a, 412b | ATC-08 |
| IWDG started at boot | IWDG started only on the first relay drive (`harness.h:16-21`); a hang before that is not reset | Start-up hang undetected (relay not driven, so no SG-07 effect) | 501b | ATC-02 |
| Full temporal isolation | Safety task at the same level as all comms (`irq_priorities.h:15-19`); latency not measured | Comms interrupt load can delay safety checks; bounded only by handler WCET | 401a, 502b, 519 | ATC-04 |
| Fault reaction | Faults report-only, `PERMANENT_FAULTS 0U` (`sys/sys.h:50`) | No transition to a latched safe state | 502 | ATC-05 |
| Command gating in the standard build | `reference_request_allowed` compiled only with `LIONDRIVER_REFERENCE` | Standard build: QM SoC can set any mode and relay (`0xc5`) at any time; out of scope for the reference release (SWSR-512/513 apply to the reference build) | 512, 513 | — |
| Removal of unused brand modes and USB path | Other modes linked (`safety.h:10-33, 468-498`); USB initialised (`main.c:356`) | Larger interference surface | OI-2, OI-3 | ATC-10, ATC-11 |

### 6.3 Shared data between contexts (ENV-R-12)

Pins: panda `8aa8671`, opendbc `7993399`. All interrupt contexts are at NVIC level 8 (`irq_priorities.h:15-19`); "host ISR" means DMA2 Stream2 or OTG_HS. Behaviour under the §5.4.2 proposal is in §5.4.3; target protections are in §10.

| Data | Writers (context) | Readers | Protection at the baseline | Race analysis |
|---|---|---|---|---|
| `controls_allowed` | CAN RX ISR (grant `pcm_cruise_check`; revoke `pcm_cruise_check`, `generic_rx_checks`, `is_msg_valid`; **[ref]** `toyota_cruise_main_check`); safety task (`safety_tick`, `is_msg_valid`, heartbeat monitor `main.c:136`); tick (heartbeat mismatch `main.c:229`; `set_safety_hooks` on heartbeat loss or harness change); host ISR (**[ref]** TX-hook revocation `tx_rate_check`, `safety.h:269-272`; `set_safety_hooks` via `0xdc`) | TX hook (host ISR), tick (LED, countdown, mismatch), RX hook, health (host ISR) | Equal priority (no preemption); `set_safety_hooks` additionally in a critical section | R-2, R-5 and TX-hook paragraph (§5.4.3) |
| `safety_tx_rate_exceeded`, `tx_rate_checks[].status` **[ref]** | host ISR (TX hook); `set_safety_hooks` (reset, `safety.h:538, 558-562`) | health (host ISR) | Equal priority; single writer context at run time | R-5 |
| `safety_eps_fault` **[ref]** | CAN RX ISR (`modes/toyota.h:239`); `set_safety_hooks` (reset, `safety.h:537`) | TX hook (host ISR), health | Equal priority; single bool store | Under §5.4.2: RX (4) preempts the TX hook (6); the TX hook sees the old or new value, at most one frame late |
| `heartbeat_engaged`, `heartbeat_counter`, `heartbeat_lost`, `heartbeat_disabled` | host ISR (`0xf3`, `0xf8`), tick, `set_safety_mode` | tick, health | Equal priority | — |
| `heartbeat_age_ticks` | host ISR (`0xf3` reset), safety task (increment) | safety task | Equal priority | R-4 |
| `current_safety_mode/param`, `current_hooks`, `current_safety_config` | host ISR (`0xdc`), tick (heartbeat loss, harness change) | all hooks, safety task (`safety_tick`), **[ref]** reference lock | Equal priority; switch in a critical section (`main.c:43-45, 49-51`) | R-1 |
| `relay_malfunction` | CAN RX ISR, `set_safety_hooks` (cleared, `safety.h:535`) | TX hook, fwd hook, tick | Equal priority | — |
| `torque_meas`, `torque_driver`, `vehicle_speed`, `desired_torque_last`, `rt_torque_last` | CAN RX ISR / TX path | TX path | Equal priority | R-5 |
| `can_rx_q`, `can_queues[]` | CAN RX ISR, TX path, host ISR | host ISR, FDCAN IT1 | Critical sections | R-6 |
| `faults`, `fault_status` | any ISR | health | Critical sections in `fault_occurred`/`fault_recovered` | R-8 |
| `hw_watchdog_main_loop_ran` | thread mode (set), safety task (clear) | safety task | `volatile` bool, single store | R-7 |
| `hw_watchdog_running`, `hw_watchdog_skip_tick` | `hw_watchdog_start` (from `set_intercept_relay`: host ISR via `0xc5` or `set_safety_mode`; tick), safety task | safety task | Equal priority; set once | Under §5.4.2: the task may preempt `hw_watchdog_start` after `running` is set (`hw_watchdog.h:56`) but `skip_tick` is set first (`:55`), so the first tick is still skipped |
| `reference_requests_rejected` **[ref]** | host ISR | health (host ISR) | Single context | — |
| `spi_buf_rx/tx` | DMA, host ISR | host ISR | SPI state machine | — |

## 7. Resource usage (estimates, to be measured)

Values computed from source and linker script at panda `8aa8671`; **not measured**. Measurement: VS-SWI-15 and VS-SWQ-23.

| Resource | Estimate | Basis |
|---|---|---|
| `CANPacket_t` | 72 B (70 B packed, aligned 4) | `can.h:8-18` |
| CAN RX queue | 4096 × 72 B ≈ 288 KiB of 320 KiB AXI SRAM | `drivers/can_common.h:22, 27`; `stm32h7/stm32h7x5_flash.ld:73` |
| CAN TX queues 1, 2 | 2 × 416 × 72 B ≈ 58.5 KiB of 64 KiB ITCM | `drivers/can_common.h:23, 28-29`; `.ld:79` |
| SPI buffers | 2 × 4096 B in 32 KiB SRAM1/2 | `drivers/drivers.h:231`; `.ld:72` |
| Stack | single main stack, minimum 1 KiB checked by linker; actual usage unknown | `.ld:64`; WP-W-01 ENV-R-14 |
| CPU load | `interrupt_load` measured by firmware and reported in health | `drivers/interrupts.h:63-67`; `main_comms.h:47-48` |
| Interrupt-rate limits | CAN 16000/s, SPI DMA 16000/s (SPI4 32000/s), tick 10/s, safety task 110/s | `stm32h7/stm32h7_config.h:28`; `drivers/drivers.h:229`; `llspi.h:86-88`; `main.c:348, 352` |
| WCET of hooks and of the safety task | not measured | VS-UV-21; §5.4.5 |

## 8. Architectural design principles assessment

ISO 26262-6 §7 lists design principles with recommendation levels per ASIL; the levels are taken from the licensed copy (OI-5). Assessment for E-03 at panda `8aa8671`, opendbc `7993399`. The "Action" column points to §10.

| Principle | Assessment at the baseline | Rating | Action |
|---|---|---|---|
| Appropriate hierarchical structure | Two layers (safety layer vs platform) are clear; LionDriver additions sit in their own headers (`reference_lock.h`, `hw_watchdog.h`, `heartbeat_monitor.h`, `irq_priorities.h`). `main_comms.h` still mixes safety-relevant and housekeeping requests in one switch; in the reference build `reference_lock.h` classifies the safety-relevant ones | Partial | ATC-12 |
| Restricted size and complexity of components | Safety layer for the reference path: `safety.h` 620, `lateral.h` 409, `modes/toyota.h` 572 lines (line counts, not a complexity metric); `comms_control_handler` is one switch of about 275 lines (`main_comms.h:69-343`); `tick_handler` 144 lines (`main.c:147-290`) | Partial | ATC-17 |
| Restricted size of interfaces | Hooks have narrow signatures, but much state is shared as globals (§6.3), now including `safety_eps_fault` and `safety_tx_rate_exceeded` | Partial | ATC-09 |
| Strong cohesion | Safety layer cohesive; periodic safety checks moved out of `tick_handler` into `safety_task_handler`, but the tick still holds the heartbeat-mismatch revocation and the SILENT transition | Partial | ATC-01 |
| Loose coupling | Safety core coupled to all brand modes via compile-time inclusion (`safety.h:10-33`) | Partial | ATC-10 |
| Appropriate scheduling properties | 100 Hz periodic safety task exists (`main.c:130-144`) with explicit, equal priorities; not all periodic checks run in it; period, latency and jitter not measured | Partial | ATC-01, ATC-04 |
| Restricted use of interrupts | Whole envelope runs in ISRs at one priority level; documented in `irq_priorities.h` and §5.1 | Partial (to be justified by measurement or changed) | ATC-04 |
| Appropriate spatial isolation | No MPU | **No** | ATC-07 |
| Appropriate management of shared resources | Ring buffers, fault word and configuration switch protected by critical sections; other globals rely on equal priority (§6.3) | Partial | §5.4.3; ATC-09 |

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Add U-PND-USB to the WP-W-06 unit list (U-PND-PWR, U-PND-HK and U-PND-PLAT added in WP-W-06 v0.2) | Safety engineer | G3 |
| OI-2 | Remove unused brand modes from the reference firmware build (decided 2026-10-26, DQ-155 A; WP-A-02 OI-2). Left: the build variant in the panda fork, kept at each sync | SW lead | G3 |
| OI-3 | USB comms are disabled in the reference build (decided 2026-10-26, DQ-156 A); USB bench tools use the debug build. Left: the panda change and its test | SW lead | G3 |
| OI-4 | Define the NVIC priority scheme for the new safety task (SWSR-519) and re-assess §6.3. **Proposed in §5.4 (2026-10-12, AI draft, I0)**; §5.4.4 code changes done (panda `52cad44`); TX-hook revocation added to the race analysis (v0.5, author analysis); still needed: I1 review and the §5.4.5 measurements on the target. Decided 2026-10-26 (DQ-153 A): measure the handler times first, then adopt the §5.4.2 ranking unless the measured margin is large | SW architect | G3 |
| OI-5 | Check principle recommendation levels against the licensed ISO 26262-6 | Safety engineer | G3 |
| OI-6 | Measure the resource estimates of §7 from the map file and on target | Maintainer | G4 |
| OI-7 | Create `elements.yaml` from §3.1 and §4.1 (WP-P-06 OI-4); include the new elements of v0.5 | Safety engineer | G3 |
| OI-8 | Decide whether a TX-rate revocation (SWSR-518) must inhibit re-engagement until the next mode change; today a new PCM rising edge re-grants (§5.4.3) | Safety engineer | G3 |

## 10. Target-state changes

Changes that the SWSRs or the analyses of this document still require. None is a change request yet unless the column says so; each needs one per [WP-M-14 §4.3](../01-management/WP-M-14-iso26262-6-implementation-specification.md#43-clause-7--software-architectural-design). Status is checked against panda `8aa8671`, opendbc `7993399`, superproject `682f184`. IDs ATC-xx are new in v0.5.

| ID | Item | Required change | SWSR | Change request / GAP | Status at the baseline |
|---|---|---|---|---|---|
| ATC-01 | Safety-task contents | Run command freshness (TSR-408), SPI error rate, relay readback, platform monitors and the periodic checks of SWSR-307, 403, 404, 405, 408, 413, 506 in the safety task; keep only housekeeping in the 8 Hz/1 Hz tick | 401a | GAP-50 | Partial: task runs `safety_tick`, heartbeat monitor and IWDG feed only (`main.c:130-144`, panda `8aa8671`); the EPS-fault and heartbeat-loss sirens were added later (panda `b790fca`, `c33343b`), and TSR-408 arrival supervision (`tx_arrival_checks`) is implemented in the reference build at opendbc `273f44e` (WP-W-02 SWSR-408; where it runs not re-read here) |
| ATC-02 | IWDG start | Start IWDG1 in window mode in the bootstub before the jump to the application | 501b | GAP-07, GAP-43 | Not impl: started on first relay drive (`harness.h:16-21`) |
| ATC-03 | Start-up tests | Start-up tests between steps 4 and 8 of §5.5 | 515 | — | Not impl (none in `main.c:292-383`) |
| ATC-04 | Priority scheme | Adopt §5.4.2 levels after the §5.4.5 measurements, or justify equal priority by measurement (§5.4.6); measure first (DQ-153 A) | 519, 401a | GAP-50, OI-4 | Proposed; all classes at level 8 (`irq_priorities.h:15-19`) |
| ATC-05 | Fault state | New latched fault state SS-S (= SILENT + latch) reachable from every state; TOYOTA exits only to SILENT/NOOUTPUT also for internal transitions | 502 | GAP-08 | Not impl: faults report-only (`sys/sys.h:50`) |
| ATC-06 | Relay-malfunction latch | Latch not clearable by `0xdc` | 506a | GAP-48 | Not impl: cleared in `set_safety_hooks` (`safety.h:535`) |
| ATC-07 | MPU | MPU regions for envelope state; configuration protected after the mode lock | 507, 512 | GAP-08, GAP-11 | Not impl |
| ATC-08 | SoC length/index bounds | Check SPI lengths against `SPI_BUF_SIZE` and every request index against its array | 412, 412a, 412b | GAP-47 | Not impl (`spi.h:115, 137, 233`; `main_comms.h:283`) |
| ATC-09 | Authority API | Single-writer API `safety_revoke(reason)`, grant only in the RX path; accessor functions instead of globals | — (WP-W-04 SWF-48) | — | Not impl |
| ATC-10 | Unused brand modes | Remove from the reference build (DQ-155 A) | — | OI-2 | Not impl (`safety.h:10-33, 468-498`) |
| ATC-11 | USB path | Disable USB comms in the reference build (DQ-156 A) | — | OI-3 | Not impl (`main.c:356`) |
| ATC-12 | Request classification | Split control requests into safety-relevant and QM groups | 513 | GAP-49 | Partial: **[ref]** car-mode refusal list (`reference_lock.h:37-49`) |
| ATC-13 | Queue overflow | Queue overflow → fault reaction | 707 | — | Not impl: overflow counted only (`can_common.h:165`) |
| ATC-14 | Heartbeat content | Heartbeat carries a control-loop counter; frozen counter treated as missing | 409 | — | Not impl: `0xf3` carries only `engaged` (`main_comms.h:298-305`) |
| ATC-15 | Host freshness | `modelV2` ≤ 100 ms (SWSR-602), `longitudinalPlan` ≤ 100 ms, `carState` ≤ 20 ms, `sendcan` ≤ 20 ms (SWSR-414h), `pandaStates` 0.3 s (SWSR-307h) | 602, 414h, 307h | — | Partly on the base (host supervision change, 2026-10-13): `controlsd` input freshness at 10 nominal periods, not 2 (SWSR-602); `controlsMismatch` ≤ 0.5 s (SWSR-621). Others not impl (§4.2 values) |
| ATC-16 | EPS fault revocation | Revoke `controls_allowed` (not only refuse frames) on an EPS fault code | 110 | — | Partial: **[ref]** frames refused (`modes/toyota.h:428-430`), authority not cleared |
| ATC-17 | Complexity | Complexity metric (WP-W-01 OI-5); split `tick_handler` and `comms_control_handler` | — | — | Not started |
| ATC-18 | TX after revocation | Optional under §5.4.2: re-check `controls_allowed` with interrupts masked just before the FDCAN TX load (R-5) | 406 | — | Not decided |
| ATC-19 | Reference release build | Build the release firmware as `RELEASE=1 LIONDRIVER_REFERENCE=1` through an explicit reference-release variant of `tools/release/build_release.sh` (the upstream variant stays available); add a CI job that builds the reference firmware; mark the build in the version string so the host can tell which firmware is installed | 512, 513, 518, 705 | RR-2026-009 F-33 | Mostly done on the base, completed by a proposed change: the root `SConstruct` defaults to `LIONDRIVER_REFERENCE=1` (#36, `e84f850`), the panda reports `HEALTH_FLAG_REFERENCE_BUILD` and `pandad` refuses a non-reference panda (#41, `717f0e9`); explicit `RELEASE_VARIANT` in `build_release.sh` and CI job `panda_reference_release_build` proposed in [change-2026-10-13-release-variant](../07-supporting/impact/change-2026-10-13-release-variant.md) |
| ATC-20 | Re-engagement after TX-rate revocation | Do not grant authority on a PCM rising edge after a TX-rate revocation until one full 250 ms window has passed without a rejected frame (a separate engagement block; the report flag `safety_tx_rate_exceeded` stays latched until the mode changes) | 518 (amended, WP-W-02 v0.24) | RR-2026-009 F-34 | Impl **[ref]**: at the pin since opendbc `515b9a2` (`tx_rate_engagement_blocked`, `safety.h:261, 288, 431-437`), [change-2026-10-13-tx-rate-reengagement](../07-supporting/impact/change-2026-10-13-tx-rate-reengagement.md); unit-tested, B2B gate OK (D13c, D13d); not on hardware |
| ATC-21 | Refused host request while engaged | In the reference build, a refused request while authority is granted also clears `controls_allowed` and is reported (CSR-012 intent: suspected compromised host → no actuation) | 512, 513 (CSR-012) | RR-2026-009 F-36 | **Not taken** (register DQ-082 B, 2026-10-19): a refused request stays mapped to `0x00` and ignored (panda `main_comms.h:74-78`), authority is not withdrawn. CSR-012's intent stays an open item of the cybersecurity case ([WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md)) |
| ATC-22 | Request allow-list in car modes | Replace the deny-list of `reference_request_allowed()` with an allow-list of the requests the reference host needs in a car mode (DQ-147 A) | 513 (CSR-014, SC-C-05) | RR-2026-009 F-37 | Not impl: deny-list; `0xb0`, `0xb1`, `0xc0`, `0xf6` pass (panda `board/reference_lock.h:50-51`) |
| ATC-23 | Alternative experience from the host | `pandad` does not send `0xdf` when the reference build is installed (or the lock accepts `0xdf` with the reference value without counting it), so `requests_rejected_pkt` counts only real refusals | 512a | RR-2026-009 F-39 | Not impl: `openpilot/selfdrive/pandad/panda_safety.cc:67` sends it on every mode set |
| ATC-24 | Safety-task rate fault code | Give the 100 Hz safety-task rate fault its own fault code | 401a, 502 | RR-2026-009 F-40 | Not impl: shares `FAULT_INTERRUPT_RATE_TICK` with the 8 Hz tick (panda `main.c:348, 352`) |
| ATC-25 | Wrong-length frame of an RX-checked message | In the reference build, a frame on the RX-check bus whose address matches an RX-check entry but whose length does not is an RX fault: authority cleared in the same call, entry invalid until the next valid frame | 402, 406 | B2B-TOY-AUTH-2026-10-13 B2B-01 ([change proposal](../07-supporting/impact/change-2026-10-13-opendbc-rx-length-fault.md), [pin bump](../07-supporting/impact/change-2026-10-17-pin-62b89a3.md)) | Impl (reference build, modes with `rx_timeout_periods`): opendbc `62b89a3` `safety.h:178-197` (`rx_length_check`), `:114-129` (`is_msg_valid` checks `wrong_length`); test `test_wrong_length_is_rx_fault`. Upstream build unchanged: the frame matches no entry and is ignored |
| ATC-26 | Cruise edge after a safety-mode change | After `set_safety_hooks`, a CRUISE_ACTIVE held through the change is not a rising edge: authority needs CRUISE_ACTIVE = 0 to be received first in the new mode (reference build) | 301, 311 | [B2B-TOY-AUTH-2026-10-13](reference-models/results/B2B-TOY-AUTH-2026-10-13.md) B2B-06 (candidate BB-C-01) | Impl **[ref]**: at the pin since opendbc `515b9a2` (`pcm_cruise_seen_disengaged`, `safety.h:414, 716, 725`), [change-2026-10-14-mode-set-regrant](../07-supporting/impact/change-2026-10-14-mode-set-regrant.md); unit-tested, B2B gate OK (D19a, D19b); not on hardware |
| ATC-27 | TX arrival supervision counts accepted frames only | In the reference build, the arrival time of a supervised actuation message (`0x2E4`, `0x343`) is noted only for a frame the TX hook accepts (whitelist, TX rate check, content checks), so a host that sends only refused frames loses authority after the timeout | 408 | B2B-TOY-AUTH-2026-10-13 B2B-05; register DQ-150 ([pin bump](../07-supporting/impact/change-2026-10-17-pin-27f20db.md)) | Impl (reference build): opendbc `27f20db` `safety.h:288-297` (`tx_arrival_update`), `:362-367` (`safety_tx_hook`); test `test_tx_arrival_counts_accepted_frames_only` |
