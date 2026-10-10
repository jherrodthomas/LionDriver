# WP-H-02 Hardware architectural and detailed design

| Field | Value |
|---|---|
| Work product | WP-H-02 Hardware architectural and detailed design (device, panda MCU, harness, relay) |
| Standard reference | ISO 26262-5:2018 §7 (hardware design: architectural and detailed design, safety-related HW elements); ISO 26262-8:2018 §13; ASPICE 4.0 HWE.2 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | ASIL C (provisional, SG-01) / ASIL B (SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `8b8c6ae` |

## 1. Purpose and limits of this document

LionDriver does not design the hardware. The comma device and the harness are COTS components
(T-04). This document is therefore a **recovered architecture**: it records what can be observed
about the hardware from the firmware and host software in the repository, identifies the
safety-related hardware elements, lists what is unknown and must be obtained, and recommends
design changes with their impact.

Every statement in §2–§4 is derived from code. **Code shows how firmware drives a pin; it does not
show the circuit behind it.** Statements marked *(inferred)* need confirmation against a
schematic, a teardown or measurement (§5).

## 2. Hardware variants

| Item | Observation | Source |
|---|---|---|
| Device families in scope | comma 3X (`tizi`) and comma four (`mici`), both Snapdragon 845-based | `openpilot/common/hardware/comma/hardware.py:60-67` |
| Internal panda boards | `tres` (HW type 9) and `cuatro` (HW type 10). `red` (type 7) is the external red panda, not in scope | `panda/board/boards/board_declarations.h:49-52`; board detection by strap pins `panda/board/stm32h7/board.h:23-52` |
| Board ↔ device mapping | tres in comma 3X, cuatro in comma four *(inferred from naming and from cuatro-only stop mode/amp code; confirm from the reference device's reported `hw_type`)* | `panda/board/main.c:353`; `boards/cuatro.h:46-48` |
| Safety MCU | STM32H7, built for **STM32H725xx** (`-DSTM32H725xx`). Linker script header names STM32H735ZGTx, 1 MB flash, 560 KB RAM; H735 is the H725 with crypto. Firmware distinguishes H725 (SMPS packages LQFP144/UFBGA169) from H723 (TFBGA100) by package register | `panda/SConscript:136-137`; `panda/board/stm32h7/stm32h7x5_flash.ld:8-10`; `panda/board/stm32h7/clock.h:28-48` |
| Core and clocks | Cortex-M7 at 240 MHz from PLL1 on a 25 MHz HSE; FDCAN kernel 80 MHz (PLL1Q); HSI48 for USB; ADC on per_ck (HSE) | `stm32h7/clock.h:3-20, 85-117`; `stm32h7/stm32h7_config.h:7-12` |
| MCU IDCODE | `0x483` | `stm32h7/stm32h7_config.h:5` |

The reference configuration fixes one device revision (WP-M-01 §3.1). Until WP-C-01 records which,
this document covers both boards (WP-H-01 OI-7).

## 3. Architecture (observable)

### 3.1 Block diagram

```
                     Vehicle (2020 Corolla TSS2)
   Forward camera (LKA/ACC/PCS)                 Vehicle CAN (EPS, ECM/PCM, ABS, ...)
          │ camera-side CAN                                │ car-side CAN
          │                                                │
 ┌────────┴──────────────── E-05 Harness ──────────────────┴────────────┐
 │   ┌───────────── Intercept relay (in harness box) ──────────┐        │
 │   │ de-energised: camera ⇄ car (stock path)  [AOU-13]       │        │
 │   │ energised:    camera ⇄ panda bus 2 ; panda bus 0 ⇄ car  │        │
 │   └─────────────▲───────────────────────────────────────────┘        │
 │                 │ relay coil drive (SBU relay line)                   │
 │   12 V + GND    │   ignition line (SBU ign)   CAN pairs              │
 └──────┬──────────┼──────────────┬──────────────┬─────────────────────┘
        │          │ USB-C-type harness connector (SBU1/SBU2 + CAN + power) 
 ┌──────┴──────────┴──────────────┴──────────────┴──────────────── E-04 comma device ──────┐
 │  Power input ── DC/DC, PMIC (unknown) ──┬───────────────┬───────────────┐                │
 │  (cuatro: DC_IN_EN_N PC11,             │               │               │                │
 │   current sense ADC1 ch3,              ▼               ▼               ▼                │
 │   voltage ADC ×11)              ┌─────────────┐  ┌──────────────────────────────────┐   │
 │                                 │ Application │  │ panda safety MCU STM32H725       │   │
 │  Road cams (2) ── MIPI ────────▶│ SoC (SD845) │  │                                  │   │
 │  Driver cam (IR) ── MIPI ──────▶│ AGNOS Linux │  │  FDCAN1 ─ XCVR1 ─ bus 0 (car)    │   │
 │  IR LEDs ◀── PWM (tres: panda)  │ openpilot   │  │  FDCAN2 ─ XCVR2/XCVR4 ─ bus 1    │   │
 │  Display, touch ◀──────────────▶│ (QM, E-01)  │  │           (mux by orientation)   │   │
 │  Speaker/amp ◀─ audio ─────────▶│             │  │  FDCAN3 ─ XCVR3 ─ bus 2 (camera) │   │
 │  Modem, Wi-Fi, GNSS, IMU ──────▶│             │  │  GPIO ─ relay drive (2 lines)    │   │
 │                                 │   SPI ◀─────┼──┼─ SPI4 + DMA2 (IF-04)             │   │
 │                                 │ STM_RST_N ──┼──┼─▶ NRST    STM_BOOT0 ─▶ BOOT0      │   │
 │                                 │ SOM GPIO ───┼──┼─▶ PC2 (input)                     │   │
 │                                 │   ◀── bootkick / SOM reset (panda → SoC)           │   │
 │                                 └─────────────┘  │  ADC ─ SBU1/SBU2 sense, Vin      │   │
 │  Fan ◀── PWM TIM3 + enable; tach ─▶ EXTI ───────▶│  DTS (die temp)                  │   │
 │  "Siren" (buzzer function via audio path) ◀──────│  I2C5 (tres) / TIM7+SAI4 (cuatro)│   │
 │                                                  │  USB (OTG HS)                    │   │
 │                                                  └──────────────────────────────────┘   │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

Bus numbering is that of the Toyota safety mode: bus 0 = car side, bus 2 = camera side
(WP-C-01 IF-01…IF-03). The STM32H7 has three FDCAN controllers (`panda/board/can.h:3`,
`PANDA_CAN_CNT 3U`) and the boards have four transceiver enables (§3.3).

### 3.2 Safety-relevant hardware elements

| HW-ID | Element | Function | SG | Observable facts | Source |
|---|---|---|---|---|---|
| HE-01 | STM32H725 core, buses, interrupt controller | Executes the envelope (E-03) | SG-01…07 | Single core, no lockstep; no MPU configured | GAP-11; WP-H-01 HWSR-507 |
| HE-02 | Embedded flash (1 MB) | Bootstub + application + provisioning/serial | all | Sector 0 (bootstub) protected from flasher erase in software; no RDP/WRP set by code | `stm32h7/llflash.h:12-14`; GAP-24 |
| HE-03 | SRAM (DTCM 128 K, AXI 320 K, SRAM1/2 32 K, SRAM4 16 K, backup 4 K) | Data, stack, CAN queues | all | ECC hardware present on STM32H7 SRAM *(verify RM0468)*; monitors not configured | `stm32h7/stm32h7x5_flash.ld:67-75` |
| HE-04 | Clock: 25 MHz HSE crystal/oscillator, PLL1, LSI (IWDG), HSI48 | Time base for all timeouts and CAN bit timing | all | CSS on HSE enabled → NMI → reset | `stm32h7/clock.h:79-80, 119`; `early_init.h:73-76` |
| HE-05 | MCU power: SMPS/LDO of the STM32H7 and the board regulator feeding it | Supply | all | SMPS or LDO chosen by package; board regulator unknown | `stm32h7/clock.h:61-69` |
| HE-06 | IWDG1 | Independent watchdog | SG-01…07 | **Present in silicon, not used** | `stm32h7/stm32h7_config.h:43` (GAP-07) |
| HE-07 | CAN transceivers XCVR1–4 | Physical layer for buses 0/1/2 | SG-01, SG-03…07 | Active-low enables per transceiver. tres: XCVR1 and XCVR3 share one enable pair (PG11, PD7) "CAN0 and 2 are tied"; XCVR2 PB10, XCVR4 PB11. cuatro: PB7, PB10, PD8, PB11. Part numbers unknown | `boards/tres.h:32-56`; `boards/cuatro.h:9-26` |
| HE-08 | Intercept relay (harness) and its driver | Breaks the camera→car link for LKA/ACC messages; restores stock path when released | SG-01, SG-07 | Two open-drain, active-low outputs (relay, and an "ignition relay" used only for testing). Assignment swaps with harness orientation. No readback | `drivers/harness.h:7-33, 96-107`; pins tres PA8/PA3, cuatro PA9/PA3 (`boards/tres.h:138-149`, `boards/cuatro.h:99-110`) |
| HE-09 | Harness connector, SBU lines | Orientation detection, ignition sense, relay drive | SG-07 | SBU1/SBU2 read by ADC (PC4 ch4 / PA1 ch17), threshold `avdd_mV/2` = 900 mV; pins not 5 V tolerant in ADC mode | `drivers/harness.h:54-90`; `boards/tres.h:155` |
| HE-10 | Ignition sense | Ignition from harness line | SG-07, availability | Digital input on the SBU line selected by orientation, active-low | `drivers/harness.h:35-52` |
| HE-11 | SPI link SoC↔MCU | Commands, heartbeat, safety-mode set | SG-01…06 (FFI) | SPI4 with DMA2 streams 2/3; 8-bit XOR on header/data | `stm32h7/llspi.h:86-88`; `drivers/spi.h:97-104` |
| HE-12 | SoC → MCU reset and boot-mode lines | SoC can reset the MCU and enter ROM bootloader | FFI | `STM_RST_N`, `STM_BOOT0` driven by SoC GPIO | `openpilot/common/hardware/comma/hardware.py:401-419` (GAP-38) |
| HE-13 | MCU → SoC bootkick / SOM reset | MCU powers up or resets the SoC | availability | tres PA0/PC12; cuatro PA0/PC11 (DC_IN_EN_N) | `boards/tres.h:21-24`; `boards/cuatro.h:40-44`; `drivers/bootkick.h` |
| HE-14 | Input-voltage and current sensing | Vin measurement | availability, SG (supply) | Vin via ×11 divider (cuatro ADC1 ch8; tres ADC1 ch2); cuatro current ADC1 ch3 ×2 | `boards/cuatro.h:28-34`; `boards/red.h:70-72` |
| HE-15 | Die temperature sensor (DTS) | Thermal monitoring | all | Reported only | `stm32h7/lldts.h`; `main_comms.h:51-52` |
| HE-16 | Fan and tachometer | Cooling of SoC and MCU | availability | PWM on TIM3 ch3, enable line, tach on EXTI2 | `drivers/fan.h`; `stm32h7/llfan.h:14` |
| HE-17 | "Siren" acoustic output | SoC-independent warning on SoC loss (FSR-02.05) | SG-02, SG-06 | tres: driven over I2C5 (open drain PC10/PC11); cuatro: TIM7 + SAI4 audio path. Whether it shares amplifier/speaker with the SoC audio is unknown | `boards/tres.h:129-132`; `drivers/fake_siren.h:71, 92`; `boards/cuatro.h:87-96` |

Non-safety-relevant (QM) hardware: cameras, IR illumination, display, modem, GNSS, IMU, USB. They
matter for SOTIF (cameras, IMU) and for dependent-failure analysis (shared power, thermal,
EMC) in [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md).

### 3.3 CAN topology detail

| FDCAN | Transceiver | Bus (Toyota mode) | Notes |
|---|---|---|---|
| FDCAN1 | XCVR1 | bus 0, car side (actuation TX, RX for envelope) | tres: enable tied with XCVR3 |
| FDCAN2 | XCVR2 or XCVR4 | bus 1 (OBD / alternate), pins switched PB5/PB6 ↔ PB12/PB13 by harness orientation and CAN mode | `boards/tres.h:58-98` (cuatro reuses `tres_set_can_mode`, `boards/cuatro.h:123`) |
| FDCAN3 | XCVR3 | bus 2, camera side | cuatro uses PD12/PD13 (`boards/cuatro.h:67-71`) |

The car-side and camera-side buses are physically separated only while the relay is energised.
When it is released, the panda's bus 0 and bus 2 transceivers are both on the same joined bus
*(inferred from the relay function; confirm)*. A transceiver fault (dominant-stuck) could then
disturb the stock path (WP-H-03 FM-CAN-03).

### 3.4 Power path

```
Vehicle 12 V ─ harness ─ device input ─┬─ (cuatro) DC_IN enable PC11 ── SoC/PMIC rail
                                       ├─ MCU regulator (unknown) ── STM32H7 (SMPS or LDO internal)
                                       └─ relay coil supply (in harness box? unknown)
```

Known: the MCU keeps running with the SoC off (stop mode with CAN/SBU wake on cuatro,
`main.c:353-356`); the MCU can switch SoC power (bootkick). Unknown: whether MCU and SoC share a
regulator, whether there is a supply supervisor, where the relay coil gets its supply, and the
input protection (load dump, reverse polarity). These determine common-cause failures with the
QM SoC (GAP-11) and HWSR-502a.

### 3.5 Reset and safe-state behaviour (from firmware)

| Event | Firmware behaviour | Relay | CAN TX | Source |
|---|---|---|---|---|
| Power-on / any reset | GPIOs float; bootstub verifies signature; app inits clock, board, `harness_init` (relay outputs high = released), SILENT mode, then enables transceivers | Released *(if driver circuit is de-energise-to-safe)* | None until car mode | `stm32h7_config.h:92-97`; `harness.h:96-107`; `main.c:251-298` |
| HSE failure | CSS → NMI → cookie + reset; then `clock_init` waits forever on `HSERDY` | Released (reset state) *(inferred)* | None | `clock.h:80, 119`; `early_init.h:73-76` |
| HardFault | Cookie + reset | Released *(inferred)* | None | `early_init.h:78-80` |
| Other exceptions / unused vectors | `Default_Handler` infinite loop | **Last state (may stay driven)** | Stops (no ISR), pending FIFO frames may still go out | `startup_stm32h7x5xx.s:111-114` |
| `assert_fatal` | `while(1)` with interrupts as they were | **Last state** | Stops | `libc.h:12-20` |
| Main loop or ISR hang | No hardware watchdog → no recovery | **Last state** | Stops | GAP-07 |
| SoC heartbeat loss | SILENT after 5 s (ign on) / 2 s; relay released; siren 3 s if engaged | Released | None | `main.c:191-225` |
| Relay malfunction detected | TX and forwarding blocked | Unchanged | Blocked | `safety.h:252, 268` |

The rows marked **Last state** are the key hardware finding: a hang with the relay energised
blocks the camera→car path (SG-07) and keeps the panda in the middle of the bus while forwarding
has stopped. The EPS times out on missing `0x2E4` (AOU-01), so SG-01 is protected by the vehicle,
but stock PCS messages from the camera no longer reach the car until power cycle. This is the
main motivation for HWSR-501 (IWDG) and HWSR-506a.

## 4. Detailed design notes relevant to safety mechanisms

| Mechanism | Hardware resource | Present | Configured by firmware | Reaction |
|---|---|---|---|---|
| Independent watchdog | IWDG1 (LSI) | Yes | **No** | — |
| Window watchdog | WWDG1 (APB clock) | Yes *(verify)* | No | — |
| Clock security system | RCC CSS (HSE) | Yes | Yes (`clock.h:119`) | NMI → reset |
| Brown-out reset | PWR BOR (option bytes) | Yes | Unknown (option bytes not set by code) | Reset |
| Programmable voltage detector | PWR PVD/AVD | Yes | **No** (`interrupt_handlers.h:7` stub only) | — |
| SRAM ECC + RAMECC monitors | RAMECC | Yes *(verify)* | **No** | — |
| Flash ECC | FLASH | Yes *(verify)* | Not handled | — |
| MPU | Cortex-M7 MPU | Yes | **No** | — |
| CRC unit | CRC | Yes | Not used for flash check | — |
| Register readback | Software | n/a | Yes (`registers.h:56-70`), 1 Hz | Report only |
| Interrupt-rate monitor | Software + TIM6 | n/a | Yes (`interrupts.h:34-37`) | Report only |
| Relay readback | Needs extra circuit | **No** | — | — |
| FDCAN error/bus-off status | FDCAN PSR/ECR | Yes | Read (`fdcan.h:44-63`), core reset on bus-off | No safety reaction in MCU |
| Temperature | DTS | Yes | Read | Report only |
| Vin measurement | ADC | Yes | Read | Report only |

## 5. Unknowns that must be obtained

| ID | Information needed | Why | Source options |
|---|---|---|---|
| UK-01 | Device schematic (panda section, power, relay driver, transceivers) | HWSR-502/505/506/508; FMEDA structure | comma.ai (request); otherwise board-level reverse engineering |
| UK-02 | BOM with manufacturer part numbers (MCU ordering code and temperature grade, transceivers, regulators, relay, connector, crystal) | Failure rates (WP-H-03/05), qualification (WP-H-07) | comma.ai; teardown and part marking |
| UK-03 | Harness schematic, relay part number, coil drive and supply, de-energised contact state | AOU-13, HWSR-502a, -506, -702 | comma.ai shop / harness teardown and continuity test (VS-HW-02 in WP-H-06) |
| UK-04 | MCU option-byte state on shipped devices (RDP, WRP, BOR level, IWDG_SW, IWDG freeze) | HWSR-501c, -505, -502c | Read out from a reference device with ST tools (read-only) |
| UK-05 | Whether MCU and SoC share supply rails and clock sources | DFA, GAP-11 | UK-01, measurement |
| UK-06 | Board pull-ups/pull-downs on relay drive and transceiver enable lines (behaviour at high-Z during reset) | HWSR-502, -508 | UK-01 or measurement with MCU held in reset |
| UK-07 | Audio path of the "siren" (shared with SoC?) | FSR-02.05 independence | UK-01 |
| UK-08 | Device input protection and operating voltage range | HWSR-505b, ISO 16750-2-type conditions | Supplier data |
| UK-09 | Manufacturing revision control (how a board revision change is identified) | Configuration of the qualified component | comma.ai; `hw_type` + serial (`stm32h7_config.h:45-46`) |

## 6. Recommended design changes

LionDriver cannot change comma's PCB. Changes are either firmware configuration of existing
silicon (low cost) or add-ons in the harness path (LionDriver-controlled hardware).

| ID | Change | Addresses | Kind | Impact | Recommendation |
|---|---|---|---|---|---|
| DC-01 | Enable IWDG1 in window mode from the bootstub; service it from the end of the 8 Hz tick processing and only if the main loop and CAN RX/TX safety processing reported progress; timeout ≤ 0.2 s minus reset time | GAP-07, HWSR-501–501c | Firmware config | Small code change in the panda fork; must be verified for stop mode, flashing and bootloader paths (an IWDG that cannot be stopped also runs during firmware update — the flasher must service it). Requires HIL (D-04) | **Do (G3)**. Needed at any ASIL |
| DC-02 | External voltage supervisor + watchdog (separate clock) that holds MCU in reset and cuts the relay coil supply | GAP-07 residual (common cause with MCU), GAP-11, HWSR-501d | HW add-on in a LionDriver harness adapter | Requires a LionDriver-built adapter between harness and device; new component to qualify; changes the item (impact analysis per WP-M-12) | Needed if SG-01 stays ASIL C or decomposition (FSC §4.3) is chosen. Optional at ASIL B |
| DC-03 | Relay readback: sense the camera-side and car-side bus continuity, or use a relay with auxiliary contact, wired to a spare MCU input (or to the DC-02 supervisor) | GAP-12, HWSR-506a | HW add-on (harness adapter) + firmware | Same adapter as DC-02; adds an input to the HSI; closes the "stuck intercepting" detection hole for SG-07 | **Recommended** for SG-07 at ASIL B; LFM benefit for the relay |
| DC-04 | Fault reaction: make relay malfunction, register divergence, ECC double error, PVD, interrupt-rate faults and watchdog-loop faults permanent faults leading to SILENT (relay released, TX off) | GAP-08 | Firmware | Changes `PERMANENT_FAULTS` and adds a reaction in `fault_occurred()`; availability impact to be evaluated (false trips) | **Do (G3)** |
| DC-05 | Enable RAMECC monitors and flash-ECC interrupts; periodic flash CRC | GAP-08, HWSR-503–503c | Firmware | Moderate code; needs fault-injection method (ECC error injection is limited on STM32H7 — verify) | **Do** |
| DC-06 | Configure MPU (stack guard, read-only code, protected safety data) | GAP-08/11, HWSR-507 | Firmware | Moderate code; impacts all panda drivers; MISRA/ref tests | **Do** |
| DC-07 | Set BOR level and enable PVD with safe-state reaction; set RDP/WRP for release devices | HWSR-505/505a, GAP-24, GAP-38 | Option bytes + firmware | RDP level changes are partly irreversible; production/provisioning procedure in [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) | **Do** with care (RDP level 2 is permanent) |
| DC-08 | Replace `Default_Handler` loop and `assert_fatal` hang with a safe-state-then-reset routine | HWSR-502b | Firmware | Small | **Do** |
| DC-09 | Gate debug relay command `0xc5` with `ALLOW_DEBUG` | GAP-09, HWSR-506c | Firmware | Trivial | **Do** |
| DC-10 | Monitor MCU DTS and Vin in firmware with safe-state thresholds | HWSR-505b, -509 | Firmware | Small; thresholds need datasheet values | Do |

## 7. Hardware architecture evaluation against ISO 26262-5 §7 expectations

| Expectation | Assessment |
|---|---|
| Safety-related HW elements identified | Done at block level (§3.2); part level blocked by UK-01/02 |
| Safety mechanisms specified with fault reaction | Mostly missing reactions (§4); DC-01, DC-04…DC-08 |
| Robust design against operating conditions (temperature, vibration, EMC, supply) | Not assessable; supplier evidence needed (WP-H-07) |
| Avoidance of systematic faults (design reviews, derating) | Not available from supplier; residual risk documented in WP-H-07 |
| Independence between QM SoC and safety MCU | Shared PCB, likely shared supply and harness; SoC controls MCU reset/boot (GAP-38). Analysed in WP-A-02/WP-A-03 |

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Request schematic, BOM and harness data from comma.ai (UK-01…UK-03); if refused, plan a teardown of one reference device and harness | G2 |
| OI-2 | Read option bytes of a reference device (UK-04), read-only | G2 |
| OI-3 | Confirm tres/cuatro ↔ comma 3X/comma four mapping and fix the reference device in WP-C-01 | G1 |
| OI-4 | Decide DC-02/DC-03 (harness adapter) together with the FSC strategy decision (WP-C-04 OI-1) | G2 |
| OI-5 | Verify STM32H7 silicon safety features listed as *(verify)* against the reference manual (RM0468) and datasheet | G2 |
| OI-6 | Confirm the relay/bus topology in §3.3 (joined bus when released) | G2 |
