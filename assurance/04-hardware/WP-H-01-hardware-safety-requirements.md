# WP-H-01 Hardware safety requirements specification

| Field | Value |
|---|---|
| Work product | WP-H-01 Hardware safety requirements specification |
| Standard reference | ISO 26262-5:2018 §6 (specification of hardware safety requirements); ISO 26262-4:2018 §6 (TSR and HSI inputs); ISO 26262-8:2018 §6 (requirement attributes), §13 (HW component qualification); ASPICE 4.0 HWE.1 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | ASIL C (provisional, from SG-01; expected to drop to B per [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §4.2) and ASIL B (SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer while the project has a single maintainer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document states the hardware safety requirements (HWSR) for the hardware elements of
LD-SDA that carry safety-goal integrity:

- **E-04 device hardware**, restricted to the safety-relevant part: the STM32H7 "panda" safety MCU,
  its clock, supply, memories and peripherals, the CAN transceivers, and the SPI link and reset/boot
  lines from the application SoC.
- **E-05 harness** with the intercept relay, the ignition sense line and the orientation-detect lines.

The application SoC (Qualcomm), cameras, display, modem and GNSS are QM elements under the FSC
([WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §2). They appear here only where
they can interfere with the safety MCU (freedom from interference, FFI) or where they provide
the power path.

Under tailoring **T-04** ([WP-M-01](../01-management/WP-M-01-assurance-strategy.md)) the device
and the MCU are COTS hardware components qualified per ISO 26262-8 §13
([WP-H-07](WP-H-07-hardware-component-qualification.md)), and LionDriver computes the hardware
metrics itself ([WP-H-04](WP-H-04-hardware-metrics.md), [WP-H-05](WP-H-05-random-hardware-failures-pmhf.md)).
LionDriver cannot change the PCB. HWSRs are therefore of three kinds:

| Kind | Meaning | Marker |
|---|---|---|
| HW-existing | A property the COTS hardware must already have; verified by analysis, supplier data and test | `[HW]` |
| HW-config | A hardware safety mechanism present in the silicon that must be configured by firmware (IWDG, CSS, PVD, ECC, MPU, option bytes) | `[CFG]` |
| HW-add | Needs a hardware change or an external add-on (external supervisor, relay readback). Recommended in [WP-H-02](WP-H-02-hardware-design.md) §6 | `[ADD]` |

## 2. Inputs and parent requirements

| Input | Status at writing | Used for |
|---|---|---|
| [WP-C-03 HARA](../02-concept/WP-C-03-hara.md) | Draft, not confirmed | SG-01 (C ⚠), SG-02…SG-06 (B), SG-07 (B) |
| [WP-C-04 FSC](../02-concept/WP-C-04-functional-safety-concept.md) | Draft | Parent FSRs: FSR-01.07, 01.09, 01.10, 01.11, 02.05, 07.01, 07.03; AOU-13; FTTI budget §8 |
| [WP-S-02 TSR](../03-system/WP-S-02-technical-safety-requirements.md) | **Does not exist yet** | TSR parents below are **provisional** and use the reserved ranges TSR-5xx (safety-MCU platform) and TSR-7xx (PCS preservation / harness) |
| [WP-S-05 HSI](../03-system/WP-S-05-hsi-specification.md) | **Does not exist yet** | HSI candidate entries in §6 are proposed for WP-S-05 |
| [Gap assessment](../00-assessment/gap-assessment.md) | Draft | GAP-07, -08, -09, -11, -12, -15, -24, -38 |

Numbering: `HWSR-5nn` refines the provisional `TSR-5nn` with the same number; `HWSR-7nn` refines
`TSR-7nn`. Extra HWSRs under one TSR get a suffix letter (e.g. HWSR-503a). When WP-S-02 is
written, any renumbering of a TSR must be mirrored here (OI-1).

### 2.1 ASIL inheritance

| Hardware function | Serves SG | ASIL assigned here | Note |
|---|---|---|---|
| Safety-MCU platform integrity (execution, clock, supply, memory) | SG-01, SG-03, SG-04, SG-05 (all actuation passes through it) | **C (provisional)** | Inherited from SG-01. FSC §4.2 recommends option (c), after which SG-01 is expected to be ASIL B. Requirements are written so that the ASIL attribute is the only thing that changes |
| Relay drive, relay state detection, harness | SG-01 (blocks camera-originated actuation), SG-07 (stock PCS path) | **C** for the actuation-blocking function, **B** for PCS restoration | Same component, two functions |
| SoC-independent acoustic warning (panda buzzer path) | SG-02, SG-06 | B | FSR-02.05 |
| Ignition sensing | SG-07 (relay state on power transitions), availability | B | |
| Temperature monitoring | All (operating-condition guard) | B | |

## 3. Hardware metric targets

The targets below are the values commonly used from ISO 26262-5 §8 and §9 for each ASIL.
**Verify against the licensed text before use in an audit.** They apply per safety goal, to the
hardware elements of the item that can violate that goal.

| Metric | ASIL B | ASIL C | ASIL D | Applicable here |
|---|---|---|---|---|
| Single-point fault metric (SPFM) | ≥ 90 % | ≥ 97 % | ≥ 99 % | SG-01 (C provisional, B expected), SG-03…SG-07 (B) |
| Latent fault metric (LFM) | ≥ 60 % | ≥ 80 % | ≥ 90 % | as above |
| PMHF (probabilistic metric for random hardware failures) | < 10⁻⁷ /h (100 FIT) | < 10⁻⁷ /h (100 FIT) | < 10⁻⁸ /h (10 FIT) | as above |

Notes:

- The ASIL B SPFM/LFM targets are recommendations in the standard rather than mandatory values;
  LionDriver adopts them as targets (decision to record in WP-M-01 §8, OI-2).
- If option (b) of the FSC (decomposition) is chosen, the metric targets stay those of the
  safety goal before decomposition (ISO 26262-9 §5, by reference) — decomposition does not
  relax hardware metric targets. This is a further reason the FSC recommends option (c).
- Diagnostic coverage claims for each mechanism below feed [WP-H-03](WP-H-03-hardware-safety-analysis-fmeda.md).

## 4. Hardware safety requirements

Attributes: **ASIL** (provisional), **Parent** (FSR from WP-C-04; TSR provisional), **Alloc**
(hardware part), **Kind** (§1), **Verif** (A = analysis, R = review, T-HIL = bench/HIL test
per [WP-H-06](WP-H-06-hardware-integration-verification.md), FI = fault injection),
**Status** (all `Proposed`), **Impl** (current evidence with file:line, or GAP).

Paths are under `panda/board/` unless prefixed otherwise. `safety.h` is
`opendbc_repo/opendbc/safety/safety.h`.

### 4.1 Program-flow and execution supervision (TSR-501)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-501 | The safety MCU shall be supervised by a watchdog whose clock source and counter are independent of the CPU core clock tree and of the software it supervises, and whose expiry forces an MCU reset. | C | FSR-01.09 / TSR-501 | STM32H7 IWDG1 | CFG | R, T-HIL, FI | **Not implemented.** `IND_WDG` defined as `IWDG1` (`stm32h7/stm32h7_config.h:43`) and never used. The only watchdog is a software timestamp check called from the 8 Hz tick ISR it is meant to supervise (`drivers/simple_watchdog.h:7-17`, `main.c:119, 301`) and only raises a report-only fault (GAP-07) |
| HWSR-501a | The watchdog shall be serviced only from a point that proves completion of the safety-relevant periodic processing (tick handler and RX/TX safety checks), not from an ISR that keeps running when the main processing has stalled. | C | FSR-01.09 / TSR-501 | Firmware + IWDG | CFG | R, FI | Not implemented (GAP-07) |
| HWSR-501b | The watchdog shall operate in window mode, so that servicing too early (runaway loop) is detected as well as servicing too late. Window and timeout shall be chosen so that detection plus reset completes within the MCU-execution-fault detection budget (≤ 0.2 s, FSC §8). | C | FSR-01.09 / TSR-501 | IWDG1 window register | CFG | A, T-HIL | Not implemented. STM32H7 IWDG has a window register (verify against RM0468) |
| HWSR-501c | The watchdog shall be started by the bootstub (or by option byte hardware-start, if chosen) before the application runs and shall stay active in all modes in which the relay can be driven; it shall not be stoppable by the SoC. | C | FSR-01.09, FSR-01.10 / TSR-501 | IWDG option bytes (IWDG_SW, freeze in stop/standby) | CFG | R, T-HIL | Not implemented. Interaction with stop mode (`main.c:353-356`, `sys/power_saving.h`) must be analysed: freezing IWDG in stop mode is acceptable only when the relay is released and TX is off |
| HWSR-501d | An independent external supervisor (voltage supervisor with watchdog input, on its own clock) that can force the relay to its released state, independent of the MCU, should be added. | C (if (a)/(b)); recommendation at B | FSR-01.09, FSR-07.03 / TSR-501 | External | ADD | A, T-HIL | Not present on the COTS PCB as far as observable. See [WP-H-02](WP-H-02-hardware-design.md) §6, DC-01. Needed for an ASIL C claim because IWDG shares supply and silicon with the CPU (GAP-11) |

### 4.2 Fault reaction and safe state on reset (TSR-502)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-502 | In and after any MCU reset (power-on, brown-out, watchdog, software, external NRST from the SoC), the relay drive outputs shall be in the state that de-energises the intercept relay, and no CAN transceiver shall transmit actuation frames, until the firmware has re-established a valid safety mode. | C | FSR-01.09, FSR-07.03 / TSR-502 | GPIO reset state, relay driver circuit, transceiver standby pins | HW + CFG | A (schematic), T-HIL, FI | **Partly observable.** Relay outputs are open-drain and written high (released) in `harness_init` (`drivers/harness.h:96-107`); the firmware starts in SILENT (`main.c:295`). GPIO reset state is analog/high-Z (`stm32h7_config.h:92-97`). Whether high-Z de-energises the relay depends on the driver circuit and pull-ups, which are **unknown without a schematic** (AOU-13, FSC OI-6) |
| HWSR-502a | The relay shall be de-energised (stock camera-to-vehicle path) when the device loses power or the harness 12 V supply is interrupted. | B | FSR-07.03 / TSR-502 | Relay (harness), coil supply | HW | A, T-HIL | Unverified (AOU-13) |
| HWSR-502b | Every unhandled exception (HardFault, NMI, MemManage, BusFault, UsageFault, unused vectors) and every fatal assertion shall end in a reset or in a state with relay released and CAN TX disabled; no fault path shall leave the MCU hung with the relay driven. | C | FSR-01.09 / TSR-502 | Exception handlers | CFG | R, FI | **Partial.** NMI and HardFault set a cookie and reset (`early_init.h:66-80`). MemManage/BusFault/UsageFault are not enabled, so they escalate to HardFault (to confirm). Other vectors use `Default_Handler`, an infinite loop (`stm32h7/startup_stm32h7x5xx.s:111-114, 319-332`). `assert_fatal` hangs in `while(1)` (`libc.h:12-20`) and the clock init hangs on an unknown package or a non-starting HSE (`stm32h7/clock.h:68, 80`). Without an IWDG, a hang keeps the relay in its last state (GAP-07, GAP-08) |
| HWSR-502c | The SoC's control of the MCU reset (`STM_RST_N`) and boot-mode (`STM_BOOT0`) lines shall not be able to put the MCU into a state where the relay is driven by anything other than the release-signed application firmware. | C | FSR-01.10 / TSR-502, TSR-511 | Boot pins, option bytes (RDP/WRP), relay driver | HW + CFG | A, T-HIL | **Not met.** The SoC drives `STM_RST_N`/`STM_BOOT0` (`openpilot/common/hardware/comma/hardware.py:401-419`) (GAP-38). In the ROM bootloader the GPIOs are at reset state, so the relay is expected to be released (HWSR-502), which is the safe direction for SG-01/SG-07; the remaining risk is firmware substitution (cybersecurity, GAP-24) |

### 4.3 Memory integrity (TSR-503)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-503 | The hardware ECC of all SRAM regions used by the safety firmware (DTCM, AXI SRAM, SRAM1/2, SRAM4, backup SRAM; `stm32h7/stm32h7x5_flash.ld:67-75`) shall be enabled, and uncorrectable (double-bit) errors shall be signalled to firmware and lead to the safe state. | C | FSR-01.09 / TSR-503 | STM32H7 RAMECC monitor units | CFG | R, FI | **Not implemented.** ECC on SRAM is a silicon feature (verify per RM0468); the RAMECC monitors and `ECC_IRQn` are not configured — `ECC_IRQHandler` only dispatches to the generic table (`stm32h7/interrupt_handlers.h:129`) and no handler is registered (GAP-08) |
| HWSR-503a | Single-bit (corrected) ECC error events shall be counted and reported in health, so that latent memory degradation is visible (latent-fault diagnostic). | C | FSR-01.09 / TSR-503 | RAMECC + flash ECC flags | CFG | T-HIL | Not implemented |
| HWSR-503b | Flash ECC double-error detection shall lead to the safe state; single-error correction events shall be reported. | C | FSR-01.09 / TSR-503 | Embedded flash ECC | CFG | R, FI | Not handled (no reference to flash ECC flags in `stm32h7/llflash.h`) |
| HWSR-503c | The firmware image in flash shall be checked by a CRC (or hash) over the application region at start-up and periodically at run time, with a period no longer than the latent-fault interval used in WP-H-04 (proposed: once per drive cycle at start-up plus a background check completing at least once per hour of operation). A mismatch shall lead to the safe state. | C | FSR-01.09 / TSR-503 | Firmware + CRC unit | CFG | T-HIL, FI | **Not implemented.** Only the bootstub signature check at boot (`bootstub.c:47-72`), which uses SHA-1/RSA-1024 and is not repeated at run time (GAP-24) |
| HWSR-503d | Critical configuration registers (clock, GPIO, FDCAN, relay pins) shall be checked periodically against their expected values, and divergence shall lead to the safe state rather than only a report. | C | FSR-01.09 / TSR-503 | Firmware register map | CFG | T-HIL, FI | **Partial.** Register-divergence check runs at 1 Hz (`drivers/registers.h:56-70`, `main.c:229`) but only calls `fault_occurred()`; `PERMANENT_FAULTS` is `0U` (`sys/sys.h:50`) so no reaction (GAP-08) |

### 4.4 Clock monitoring (TSR-504)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-504 | Failure of the external high-speed oscillator (HSE, 25 MHz) shall be detected by the clock security system and lead to the safe state. | C | FSR-01.09 / TSR-504 | RCC CSS on HSE | CFG | FI | **Implemented (detection).** CSS enabled (`stm32h7/clock.h:119`). On the STM32H7 a CSS event raises NMI (verify against RM0468); the NMI handler resets the MCU (`early_init.h:73-76`). After reset `clock_init` waits forever for `HSERDY` (`clock.h:80`) — a hang with GPIOs at reset state. Acceptable only if HWSR-502 is confirmed |
| HWSR-504a | Drift of the CPU/peripheral clock outside a tolerance that would invalidate timing-based checks (RX timeouts, heartbeat timeout, CAN bit timing) shall be detected by a cross-check against an independent clock (e.g. IWDG LSI or HSI vs HSE-derived timer). | C | FSR-01.09 / TSR-504 | Timers + LSI/HSI | CFG | A, FI | **Partial.** Interrupt-rate checks (`drivers/interrupts.h:34-37`) catch gross over-rates, report-only. No frequency cross-check |

### 4.5 Supply monitoring (TSR-505)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-505 | The MCU core and I/O supply shall be supervised so that operation below the specified minimum voltage is impossible (brown-out reset at a level inside the MCU's operating range). | C | FSR-01.09 / TSR-505 | STM32H7 BOR (option bytes), on-board regulator/supervisor | HW + CFG | R, T-HIL | **Unknown.** BOR level is an option-byte setting; no code sets it. On-board supervisor unknown (schematic needed) |
| HWSR-505a | Supply degradation above the brown-out level but outside the safe operating range (programmable voltage detector) shall lead to the safe state before brown-out. | C | FSR-01.09 / TSR-505 | PWR PVD/AVD | CFG | T-HIL | **Not implemented.** `PVD_AVD_IRQHandler` exists only as a dispatch stub (`stm32h7/interrupt_handlers.h:7`); PVD is not enabled |
| HWSR-505b | The vehicle supply voltage at the device input shall be measured and reported; an out-of-range value while the relay is driven shall lead to the safe state. Thresholds to be set from the device input rating. | B | TSR-505 | ADC on input divider | HW + CFG | T-HIL | **Partial.** Measured and reported only: `cuatro_read_voltage_mV` (ADC1 ch8 ×11, `boards/cuatro.h:28-30`), `red_read_voltage_mV` used by tres (ADC1 ch2 ×11, `boards/red.h:70-72`, `boards/tres.h:162`), reported in health (`main_comms.h:14`). Host uses it only for power management (`openpilot/system/hardware/power_monitoring.py`) |

### 4.6 Memory protection (TSR-507)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-507 | The Cortex-M7 MPU shall be configured so that safety-critical data (safety mode, limits, `controls_allowed`, relay state) and the stack are protected against writes from non-safety code paths (USB/SPI comms handlers), stack overflow is trapped by a guard region, and code regions are non-writable; MemManage faults shall lead to the safe state. | C | FSR-01.09, FSR-01.10 / TSR-507 | Cortex-M7 MPU | CFG | R, FI | **Not implemented.** No MPU configuration in `panda/board` (`mpu_armv7.h` is vendored in `stm32h7/inc/` but unused) (GAP-08, GAP-11) |

### 4.7 Relay drive and relay state detection (TSR-506)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-506 | The intercept relay shall be energised only by an active output from the MCU (de-energise-to-safe): any open circuit, MCU reset or loss of drive shall release it. | C/B | FSR-07.03 / TSR-506 | Relay driver, relay, harness | HW | A (schematic), T-HIL | Relay outputs are open-drain, active-low (`drivers/harness.h:22-28, 98-101`); "released" = output high/open. Driver circuit unknown (AOU-13) |
| HWSR-506a | The actual relay contact state (or the continuity of the camera-to-car path) shall be read back by the MCU independently of the drive signal, and a mismatch between commanded and actual state shall be detected within the SG-01 detection budget (≤ 0.3 s) in both directions (stuck released and stuck intercepting). | C/B | FSR-01.11, FSR-07.03 / TSR-506 | Relay auxiliary contact or bus-sense circuit | ADD | A, T-HIL, FI | **Not implemented (GAP-12).** Current detection is indirect and one-directional: camera control messages seen on the car side after a 1 s transition timeout (`safety.h:372-380`), checked at 1 Hz in `safety_tick` (so 1–2 s). "Stuck intercepting while commanded released" is not detected at all |
| HWSR-506b | A detected relay malfunction shall inhibit all actuation TX until the next power cycle, and shall be reported to the SoC. | C | FSR-01.11 / TSR-506 | Firmware | CFG | T-HIL | **Implemented.** `relay_malfunction` blocks TX (`safety.h:252`) and forwarding (`safety.h:268`); reported as `FAULT_RELAY_MALFUNCTION` (`main.c:122-129`); host immediate-disable (`openpilot/selfdrive/selfdrived/selfdrived.py:341`). Cleared on any safety-mode change (`safety.h:427, 459`), not latched to a power cycle |
| HWSR-506c | The relay drive path shall not be operable by debug commands in release builds. | C | FSR-01.10 / TSR-506 | Firmware | CFG | R, T-HIL | **Not met.** `0xc5` drives the relay without `ALLOW_DEBUG` gating (`main_comms.h:144-147`) (GAP-09) |
| HWSR-506d | The relay's rated contact life, switching current and coil characteristics shall cover the expected number of engage/release cycles over the vehicle life with margin. | B | TSR-506 | Relay part | HW | A (datasheet) | Part number unknown ([WP-H-07](WP-H-07-hardware-component-qualification.md) QE-05) |

### 4.8 CAN transceivers and bus-off handling (TSR-508)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-508 | The CAN transceivers on the actuation bus (car side) shall be in a non-transmitting state from reset until the firmware enables them, and the firmware shall be able to disable them as part of the safe state. | C | FSR-01.09 / TSR-508 | Transceiver standby/enable pins | HW + CFG | A, T-HIL | Enable lines are active-low GPIOs per transceiver (`boards/cuatro.h:9-26`; `boards/tres.h:32-56`); enabled after SILENT is set (`main.c:295-298`). Behaviour of the enable pin at high-Z (MCU reset) depends on board pull-ups — unknown |
| HWSR-508a | A transceiver failure that produces a dominant-stuck or babbling bus shall not prevent the stock camera-to-vehicle path from working once the relay is released. | B | FSR-07.03 / TSR-508, TSR-702 | Transceivers, relay topology | HW | A (schematic) | Unknown: depends on whether the panda transceivers stay attached to the car-side bus when the relay is released |
| HWSR-508b | Bus-off, error-passive and persistent TX failure on the car-side bus while engaged shall be detected and lead to the actuation safe state and a driver warning. | B | FSR-01.12 / TSR-508 | FDCAN status | CFG | T-HIL, FI | **Partial.** Bus-off and error counters read into `can_health` (`drivers/fdcan.h:44-63`); on bus-off the core is reset (`drivers/fdcan.h:76-84`, `can_clear_send` rate-limited to 10 Hz, `:23-34`). No safety reaction in firmware; the host raises `canError` (gap assessment GAP-19 for wrong text) |
| HWSR-508c | CAN controller interrupt storms shall be detected and lead to the safe state. | B | TSR-508 | Interrupt-rate monitor | CFG | FI | Detected, report-only (`drivers/fdcan.h:257-262`, `drivers/interrupts.h:34-37`) (GAP-08) |

### 4.9 Ignition sensing (TSR-510)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-510 | The ignition state shall be sensed from the harness ignition line; loss or implausibility of the ignition signal shall not leave the relay driven without a valid heartbeat. | B | FSR-07.03 / TSR-510 | Harness SBU ignition line, MCU input | HW + CFG | T-HIL | **Partial.** `harness_check_ignition` reads the SBU line selected by orientation (`drivers/harness.h:35-52`). Toyota has no CAN ignition hook (`opendbc_repo/opendbc/safety/ignition.h:12-63` covers GM, Rivian, Tesla, Mazda, VW MEB only), so the Corolla relies on the line alone. Ignition sets the heartbeat timeout: 5 s with ignition, 2 s without (`main.c:101-103, 193`) |
| HWSR-510a | A short or open of the ignition line shall be detected or shown to be safe (an open line reads "ignition off" and shortens the heartbeat timeout — safe direction; a short to ground reads "ignition on" — longer timeout, analyse). | B | TSR-510 | Analysis | HW | A | Not analysed ([WP-H-03](WP-H-03-hardware-safety-analysis-fmeda.md) FM-IGN-*) |

### 4.10 Temperature (TSR-509)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-509 | The safety MCU die temperature shall be monitored, and operation outside the MCU's specified junction range shall lead to the safe state. | B | TSR-509 | STM32H7 DTS | CFG | T-HIL | **Partial.** DTS read and reported (`stm32h7/lldts.h`, `main_comms.h:51-52`), no reaction in firmware. The host's thermal policy uses SoC CPU/GPU/memory/PMIC temperatures only, not the panda DTS (`openpilot/system/hardware/hardwared.py:320-329`) |
| HWSR-509a | Loss of forced cooling (fan stall) shall be detected. | QM (availability) / B if thermal margin requires it | TSR-509 | Fan tachometer | HW + CFG | T-HIL | Tach measured (`drivers/fan.h:23-43`); host raises a fault when fan < 500 rpm for > 15 s (onboard review, `selfdrived.py:268-271`) |

### 4.11 SoC–MCU link (TSR-4xx, HW part)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-401 | The SPI link shall carry an integrity mechanism strong enough for the residual-error target of the TSR (e.g. CRC-16 or stronger plus a sequence counter); the HW part is the SPI peripheral and DMA, which shall report overrun and mode faults. | C | FSR-01.08 / TSR-4xx | SPI4 + DMA2 | CFG | A, FI | Weak: 8-bit XOR (`drivers/spi.h:97-104`) (GAP-10). Software requirement; listed here for the HSI |

### 4.12 Harness (TSR-7xx)

| ID | Statement | ASIL | Parent | Alloc | Kind | Verif | Impl |
|---|---|---|---|---|---|---|---|
| HWSR-701 | The harness orientation (normal, flipped, not connected) shall be detected before the relay is driven, and the CAN routing and relay/ignition pin assignment shall follow the detected orientation. | B | FSR-07.03 / TSR-701 | SBU ADC sense, harness | HW + CFG | T-HIL | **Implemented.** ADC of SBU1/SBU2 against `avdd_mV/2` (`drivers/harness.h:54-90`); relay/ignition pin swap by orientation (`drivers/harness.h:22-28`); CAN pin mux by orientation (`boards/tres.h:58-98`). Detection is skipped while the relay is driven (`drivers/harness.h:59`) |
| HWSR-701a | A change of detected orientation or loss of harness while the relay is driven shall be detected and lead to the safe state. | B | TSR-701 | Firmware | CFG | T-HIL, FI | Partial: orientation change re-inits CAN and the safety mode (`main.c:132-140`), but detection is suspended while the relay is driven, so harness disconnection is seen only through CAN/heartbeat effects |
| HWSR-702 | In the de-energised relay state the harness shall connect the forward camera to the vehicle CAN without any active component in the path (stock PCS path). | B | FSR-07.03, AOU-13 / TSR-702 | Harness relay | HW | A (inspection), T-HIL | Unverified (AOU-13, FSC OI-6). Code comment "keep buses connected by default" (`drivers/harness.h:106`) supports this but is not evidence |
| HWSR-703 | Harness connectors shall be keyed/latched so that partial insertion is detected (NC status) or cannot occur. | B | TSR-703 | Connectors | HW | A, inspection | Unknown |

## 5. Requirements on the hardware that the FSC FTTI budget implies

| SG / fault class | Detection budget (FSC §8) | HWSRs that must meet it |
|---|---|---|
| SG-01 MCU execution fault | ≤ 0.2 s (HW watchdog) + ≤ 0.1 s reaction | HWSR-501, -501b, -502, -502b |
| SG-01 relay stuck released | ≤ 0.3 s (proposed) | HWSR-506a (today 1–2 s, GAP-12) |
| SG-07 relay stuck intercepting with MCU silent | Continuous | HWSR-506a, HWSR-702 |
| All: memory, clock, supply | ≤ 0.2 s for faults that can corrupt actuation; latent checks once per drive cycle | HWSR-503…505 |

## 6. HSI candidate entries for WP-S-05

The HSI does not exist yet ([WP-S-05](../03-system/WP-S-05-hsi-specification.md)). These entries
are proposed for it; IDs to be assigned there.

| Proposed entry | Hardware resource | Software owner | HWSR |
|---|---|---|---|
| IWDG1 configuration (prescaler, reload, window, start in bootstub) and service point | IWDG1, LSI | panda bootstub + main loop | 501–501c |
| Relay drive outputs (SBU1/SBU2 relay pins per board: tres PA8/PA3, cuatro PA9/PA3; open-drain, active-low) | GPIO | `drivers/harness.h` | 506, 502 |
| Relay readback input (to be added) | GPIO/ADC (new) | new driver | 506a |
| Harness SBU sense (PC4 / PA1, ADC1 ch4 / ch17) | ADC1, GPIO | `drivers/harness.h` | 701, 510 |
| CAN transceiver enables (cuatro PB7/PB10/PD8/PB11; tres PB10/PB11 + tied PG11/PD7) | GPIO | `boards/*.h` | 508 |
| FDCAN1..3 status (PSR, ECR, IR) | FDCAN | `drivers/fdcan.h` | 508b |
| RAMECC monitors, flash ECC flags, ECC IRQ | RAMECC, FLASH | new | 503–503b |
| CSS/NMI, PVD/AVD IRQ, BOR option byte | RCC, PWR | `stm32h7/clock.h`, new | 504, 505 |
| DTS temperature | DTS | `stm32h7/lldts.h` | 509 |
| Input voltage ADC (cuatro ADC1 ch8, tres ADC1 ch2; ×11 divider) | ADC1 | `boards/*.h` | 505b |
| SoC-controlled `STM_RST_N`, `STM_BOOT0` | SoC GPIO → MCU NRST/BOOT0 | `openpilot/common/hardware/comma/hardware.py` | 502c |
| MPU region map | Cortex-M7 MPU | new | 507 |
| SPI4 + DMA2 streams 2/3 | SPI, DMA | `stm32h7/llspi.h`, `drivers/spi.h` | 401 |

Pin assignments above are from firmware (`boards/tres.h:138-149`, `boards/cuatro.h:99-110`) and
must be confirmed against the schematic (WP-H-02 §5).

## 7. Traceability summary

| FSR (WP-C-04) | HWSRs |
|---|---|
| FSR-01.08 | 401 |
| FSR-01.09 | 501, 501a–d, 502, 502b, 503, 503a–d, 504, 504a, 505, 505a, 507 |
| FSR-01.10 | 501c, 502c, 506c, 507 |
| FSR-01.11 | 506a, 506b |
| FSR-01.12 | 508b |
| FSR-07.03 | 501d, 502, 502a, 506, 506a, 508a, 510, 701, 702 |
| FSR-02.05 (buzzer path) | none yet — the panda buzzer ("siren") hardware path is analysed in WP-H-03 (FM-SIR-01); add an HWSR if the analysis needs one (OI-5) |

Machine-readable trace entries go to `trace/` per [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) when WP-S-02 exists.

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Re-align HWSR numbering and parents once [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) defines TSR-5xx/7xx; current TSR parents are provisional | G2 |
| OI-2 | Record the adopted SPFM/LFM/PMHF targets (§3) as a decision in WP-M-01 §8; verify values against the licensed ISO 26262-5 | G2 |
| OI-3 | Obtain the device schematic (or reverse-engineer the relay driver, transceiver enables and supply supervision) to close HWSR-502, -502a, -505, -506, -508, -508a ([WP-H-02](WP-H-02-hardware-design.md) OI-1) | G2 |
| OI-4 | Update the ASIL attribute of all `C` HWSRs when the HARA re-rates SG-01 (FSC OI-2) | G2 |
| OI-5 | Decide whether the panda buzzer hardware path (FSR-02.05) needs its own HWSR after the WP-H-03 analysis | G3 |
| OI-6 | Decide on HWSR-501d (external supervisor) and HWSR-506a (relay readback): both need hardware change outside comma's design; see WP-H-02 §6 | G2 |
| OI-7 | Confirm that the reference device type (comma 3X "tres" board vs comma four "cuatro" board) is fixed in WP-C-01; requirements cover both today | G1 |
