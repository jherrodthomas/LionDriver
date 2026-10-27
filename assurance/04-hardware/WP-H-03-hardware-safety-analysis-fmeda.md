# WP-H-03 Hardware safety analysis (FMEA / FMEDA)

| Field | Value |
|---|---|
| Work product | WP-H-03 Hardware safety analysis (FMEA/FMEDA) |
| Standard reference | ISO 26262-5:2018 §7 (safety analyses on HW design), §8 (metrics input), Annex D (diagnostic coverage of safety mechanisms, informative); ISO 26262-9:2018 §8 (safety analyses); ISO 26262-11:2018 (semiconductor failure modes, informative); ASPICE 4.0 HWE.2 |
| Version | 0.10 (§6.2/§6.3: SG-07 figures from FMEDA SG-009 rev 0.9, camera-side termination R7/R8 added; λ 288 FIT, LFM 97.6 %, λSPF + λRF 63.1 FIT; planned-measure chain 83.6 → 87.3 → 94.5 %; AI-drafted; 2026-10-27). 0.9 (§6.4: SG-05 estimate from the FMEDA rev 0.7 per-goal classification, SPFM 90.38 %; 2026-10-20). 0.8 (FM-HAR-02: a flipped reading also swaps logical CAN buses 0 and 2; effect traced to the relay-malfunction check; 2026-10-20). 0.7 (§2.3 handbook set approved, DQ-068 option A, OI-2 closed; no ST licence, own self-tests with low CPU coverage, DQ-069 option B: §2.3 STM32H7 row, OI-3 and §6.4 updated, the ASIL C SPFM target likely missed and carried to G2; 2026-10-19). 0.6 (§2.4 mission profile: the WP-H-05 §3 working values approved by the lead 2026-10-18 (DQ-067, A); 2026-10-19). 0.5 (§6.4 added: the SG-001/SG-009 FMEDA rows reused for SG-02, SG-03, SG-05 and SG-06, a note per goal, decision DQ-362 option A; the ASIL C SPFM miss of 0.16 points carried as WP-H-04 OI-6 for G2; 2026-10-18). 0.4 (§6.3 recomputed with FMEDA rev 0.4: U1/U2 at the SN 29500-2 reference value, 2 × 25 FIT, SG-07 SPFM 78.1 %; planned-measure cases recomputed with stated DC assumptions; §2.3 source status; 2026-10-16). 0.3 (OI-9 closed by DQ-064; 2026-10-16). 0.2 (status update 2026-10-12: IWDG (DC-01), 0.3 s heartbeat revocation and the reference-build `0xc5` refusal recorded in the existing-diagnostic cells of FM-CPU-03/05/06, FM-CLK-04, FM-SPI-02, FM-REL-05; no DC credit taken until HIL evidence). 0.1: initial draft |
| Status | Draft (qualitative FMEA); quantitative FMEDA: generic-rate estimate in §6.3, part-level template TBD |
| ASIL / scope | ASIL C (SG-01 provisional; SG-02, SG-03, SG-06 since WP-C-03 v0.4) / ASIL B (SG-04, SG-05, SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `bf6ce8c` (status update 2026-10-12) |

## 1. Purpose

Closes the first step of **GAP-15** (no hardware safety analysis). It provides:

1. the method for the hardware FMEA and FMEDA (§2);
2. an initial **qualitative, block-level FMEA** of the safety-relevant hardware identified in
   [WP-H-02](WP-H-02-hardware-design.md) §3.2, with existing diagnostics and coverage estimates (§4);
3. an **FMEDA table template** ready for failure rates once a BOM exists (§6).

The quantitative results feed [WP-H-04](WP-H-04-hardware-metrics.md) (SPFM/LFM) and
[WP-H-05](WP-H-05-random-hardware-failures-pmhf.md) (PMHF). Nothing quantitative is computed here:
every rate and every metric is **TBD — requires BOM**.

## 2. Method

### 2.1 Approach

| Step | Content | State |
|---|---|---|
| 1 | Define safety goals and safe states the hardware can violate (SG-01…SG-07, [WP-C-03](../02-concept/WP-C-03-hara.md); safe states from [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §6) | Done (inputs) |
| 2 | Block-level qualitative FMEA (inductive): for each block, failure modes → local effect → effect on each SG → existing detection → fault class | **This version** |
| 3 | Deductive check: hardware fault-tree branches under each SG top event (in [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md)) to confirm no block is missing | Planned |
| 4 | Component-level FMEDA: BOM parts, failure rates, failure-mode distribution, safety-related flag, fault classification (safe, single-point, residual, multiple-point detected/perceived/latent), DC per mechanism | Template (§6), blocked by BOM |
| 5 | MCU internal FMEDA: split the STM32H7 into parts/sub-parts (CPU, flash, SRAM, buses, clock, power, FDCAN, GPIO, ADC, DMA, SPI, IWDG) per the ISO 26262-11 approach | Template (§6.2), needs supplier FIT or a die/package model |
| 6 | Iterate with the design changes of WP-H-02 §6 and recompute | Planned |

Fault classes used (ISO 26262-5 / -10 terms): **SPF** single-point fault (no mechanism covers
it); **RF** residual fault (part of a fault not covered by a mechanism); **MPF-D/-P/-L**
multiple-point fault detected, perceived or latent; **S** safe fault.

### 2.2 Diagnostic coverage scale

The FMEA rates each mechanism with the three-level scale used in ISO 26262-5 Annex D. In our
words:

| Level | Meaning used here | Typical numeric value for the FMEDA |
|---|---|---|
| Low | The mechanism catches the fault only in some modes or with a long latency, or checks only part of the relevant logic | 60 % |
| Medium | Catches most failure modes of the element, with known blind spots | 90 % |
| High | Catches practically all failure modes of the element within the required time | 99 % |
| None | No mechanism | 0 % |

The numeric values are the conventional anchors of the Annex D scale; **verify against the
licensed text**. A coverage claim above "low" requires justification (analysis or fault injection,
[WP-H-06](WP-H-06-hardware-integration-verification.md)).

### 2.3 Failure-rate sources (approved)

| Element class | Proposed source | Reason |
|---|---|---|
| Discrete parts, relay, connectors, crystal, transceivers, regulators | **SN 29500** (Siemens) series, with its reference conditions adjusted to the mission profile | Widely used in automotive FMEDAs, covers relays and connectors, publicly purchasable, consistent stress model |
| Integrated circuits without supplier data | SN 29500 (IC part) as primary; **IEC 61709** for the conversion of reference conditions | Consistency with the above |
| STM32H7 (die + package) | Supplier FIT and failure-mode distribution from ST only if ST provides them without a licence: the lead decided not to pay for ST's safety package ([DQ-069](../01-management/decisions/register.yaml), option B, 2026-10-19; [WP-H-07](WP-H-07-hardware-component-qualification.md) QE-02, QE-03); otherwise a die/package model of the IEC TR 62380 type as referenced in ISO 26262-11 (IEC TR 62380 is no longer maintained by IEC — verify status) | ISO 26262-11 gives the method for splitting a microcontroller into parts and distributing failure modes |
| Soft errors (SRAM, flash, registers) | Supplier soft-error data (SER in FIT/Mbit) if available; otherwise a literature value with justification | Transient faults dominate SRAM; ECC credit depends on it |
| Harness wiring and crimps | SN 29500 (connections) | |

One source per class is used throughout; mixing handbooks within one class is avoided. The
lead approved this set as safety manager ([DQ-068](../01-management/decisions/register.yaml), option A, 2026-10-19; OI-2 closed). Buying the SN 29500 series and IEC 61709 is part of that choice; neither is held yet (status below).

*Status 2026-10-16:* neither SN 29500 nor IEC 61709 is held by the project, and neither could be reached from the analysis environment. The FMEDA uses one secondary quote of SN 29500-2 (CMOS analog ICs, §6.3) and generic rates elsewhere. Each harness box part has its SN 29500 class recorded so that the values can be filled in once the standard is available.

### 2.4 Mission profile

Defined in [WP-H-05](WP-H-05-random-hardware-failures-pmhf.md) §3. The lead approved the working values on 2026-10-18
(decision register DQ-067, A): a 15-year vehicle life, about 500 operating hours a year (7,500 h), up to +85 °C in the
sun-loaded windscreen enclosure (Tj up to about +105 °C) and one power cycle per drive. They are used for the SN 29500
stress factors and the latent-fault exposure time; the hours are replaced with logged driving data once there is some
(WP-H-05 OI-6). No stress conversion has been applied to any rate yet (§6.3).

## 3. Safety-goal violation mechanisms considered

| SG | How a hardware fault can violate it |
|---|---|
| SG-01 | Envelope lets through an excessive or unauthorised `0x2E4` torque (wrong computation, corrupted limit or `controls_allowed`, corrupted frame after the check); relay stuck released while stock camera also commands (detected today, with delay) |
| SG-02, SG-06 | Loss of actuation without warning: MCU hang or reset while engaged with no acoustic warning (siren path) and SoC not alerting |
| SG-03, SG-04 | Excessive or unauthorised `0x343` acceleration/deceleration (same mechanisms as SG-01) |
| SG-05 | Override/brake not acted on: corrupted RX processing or stuck `controls_allowed` |
| SG-07 | Camera PCS messages blocked or altered: relay stuck intercepting with forwarding stopped (MCU hang, MCU in reset with relay held, readback absent), transceiver disturbing the joined bus, harness open |

The vehicle-side measures (EPS torque limitation and LKA timeout, AOU-01R; PCM clamp, AOU-05R)
are **external measures**. They are not counted as diagnostic coverage; they appear in the PMHF
argument ([WP-H-05](WP-H-05-random-hardware-failures-pmhf.md) §5).

## 4. Qualitative block-level FMEA

Code paths are under `panda/board/` unless prefixed. "DC today" is the coverage of the mechanisms
present at baseline `8b8c6ae`; "DC planned" assumes the WP-H-02 §6 changes (DC-xx) are made and
verified.

*Status note 2026-10-12:* the IWDG (DC-01, panda `9f60e17`) and the 0.3 s heartbeat revocation (panda `c2e5d93`) are now implemented but **not verified on hardware**. They are recorded in the "Existing diagnostic" cells below; "DC today" stays at the baseline `8b8c6ae` values, and no DC is credited for them until HIL fault-injection evidence exists ([watchdog impact record](../07-supporting/impact/change-2026-10-12-panda-hw-watchdog.md) OI-3) and the LSI tolerance is confirmed (OI-2).

### 4.1 MCU core (CPU, buses, interrupt controller)

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned mechanism | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-CPU-01 | Wrong instruction execution / wrong data path result (permanent) | Safety check computes wrong result (e.g. torque limit passes out-of-range value, `controls_allowed` wrongly true) | SG-01, SG-03, SG-04, SG-05 | SPF | None in MCU. Host compares `controls_allowed` with its own state after 2 s (`controlsMismatch`, onboard review) — QM, slow, and does not check limits | None | Software CPU self-test library at start-up and periodically (vendor STL if available for STM32H7, WP-H-07 QE-03), plus control-flow monitoring with the IWDG (DC-01) | Medium (single core, no lockstep; "high" is not credible without hardware redundancy) |
| FM-CPU-02 | Transient upset (soft error in registers/pipeline) | As FM-CPU-01 for one cycle | SG-01… (one frame) | RF | None | None | Same as above; per-frame limit re-evaluation bounds a single-frame effect | Low–medium |
| FM-CPU-03 | Program-flow hang (stuck in loop or ISR, stuck critical section) | TX stops; forwarding stops; relay stays in last state | SG-07 (relay driven, PCS forwarding lost); SG-02/06 (actuation lost — EPS timeout — without MCU warning) | SPF for SG-07 | SW watchdog in the same ISR (`drivers/simple_watchdog.h:7-17`) cannot see a hang; host sees missing panda states (QM). **2026-10-12:** IWDG window, started at the first relay drive, fed from the 100 Hz safety task after main-loop progress (`drivers/hw_watchdog.h`, panda `9f60e17`); no DC claimed until HIL | Low (host only) | IWDG window + safe service point (DC-01) → reset → relay released | High (for hang); medium for timing faults |
| FM-CPU-04 | Unexpected exception (HardFault/NMI) | Reset via cookie path (`early_init.h:73-80`) | Transient loss of function; safe for SG-01; relay released after reset *(if HWSR-502 holds)* | S / MPF-D | Reset + `HEALTH_FLAG_*_RESET` reported (`main.c:319-325`) | High (for this mode) | — | High |
| FM-CPU-05 | Exception routed to `Default_Handler` (unused vector, SVC, PendSV, DebugMon) | Infinite loop (`stm32h7/startup_stm32h7x5xx.s:111-114`) | As FM-CPU-03 | SPF for SG-07 | None. **2026-10-12:** the IWDG ends the loop in a reset once the relay has been driven (as FM-CPU-03); no DC claimed until HIL | None | DC-08 + IWDG | High |
| FM-CPU-06 | Interrupt controller fault: CAN or tick IRQ lost or storm | Missing checks or overload | SG-01 (missed RX checks), SG-07 | RF | Interrupt-rate monitor, report-only (`drivers/interrupts.h:34-37`). **2026-10-12:** a lost safety-task IRQ stops the IWDG feed; a safety-task storm that feeds before the window opens (≈ 5 ms) resets; no DC claimed until HIL | Low | DC-04 (reaction) + IWDG | Medium |
| FM-CPU-07 | DMA fault (SPI DMA2 writes wrong memory) | Corrupt safety state | SG-01… | RF | None | None | MPU (DC-06) on safety data; RAM ECC does not cover wrong-address writes | Medium |

### 4.2 Flash

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-FLS-01 | Single-bit error in code/constants | Corrected by flash ECC *(verify)* | None | S (if ECC active by hardware) | Flash ECC (silicon, transparent) | High for single bits | Report corrected events (HWSR-503b) for latent tracking | High |
| FM-FLS-02 | Multi-bit error / cell degradation in code or limit constants | Wrong limit value or wrong code | SG-01, SG-03, SG-04 | SPF | Bootstub signature check at boot only (`bootstub.c:47-72`); no run-time check; ECC double-error flag not handled | Low (boot only, latent during drive) | Periodic CRC (HWSR-503c, DC-05) + ECC DED → safe state | High |
| FM-FLS-03 | Unintended erase/program (flash controller fault, firmware bug) | Corrupted image | as above | RF | Sector 0 protected from flasher erase in software (`stm32h7/llflash.h:12-14`); no WRP | Low | WRP option bytes (DC-07) + CRC | High |

### 4.3 SRAM

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-RAM-01 | Soft error, single bit | Corrected by SRAM ECC *(verify which SRAMs have ECC on STM32H725)* | None | S | Hardware ECC (silicon) | High (single bit) | Count corrected errors (HWSR-503a) | High |
| FM-RAM-02 | Double-bit / multi-bit error in safety variables (limits copy, `controls_allowed`, counters) or stack | Wrong decision or crash | SG-01, SG-03…05 | SPF | None (RAMECC not configured, `ECC_IRQHandler` not registered, `stm32h7/interrupt_handlers.h:129`) | None (detection exists in silicon but nobody listens) | RAMECC DED → safe state (DC-05); redundant storage (inverse copy) of critical variables in software | Medium–high |
| FM-RAM-03 | Stuck-at / coupling faults (permanent) | as above | as above | SPF | None | None | ECC + start-up RAM test (march) of critical regions | High |
| FM-RAM-04 | Stack overflow into safety data (systematic trigger of a HW-visible fault) | Corruption | as above | RF | None | None | MPU stack guard (DC-06) | High |

### 4.4 Clock

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-CLK-01 | HSE stops | CSS → NMI → reset; re-init hangs on HSERDY (`stm32h7/clock.h:80`) | Loss of function; relay released *(if HWSR-502 holds)*; SG-02/06 warning only from SoC | MPF-D | CSS (`clock.h:119`) + NMI reset (`early_init.h:73-76`) | High | Bounded wait + safe state instead of infinite wait | High |
| FM-CLK-02 | HSE frequency drift (crystal ageing, wrong load) | All timeouts and CAN bit timing shift; CAN errors | SG-01 (RX timeouts longer than specified) | RF | CAN errors visible (`drivers/fdcan.h:44-63`), report-only | Low | Clock cross-check against LSI/HSI (HWSR-504a) | Medium |
| FM-CLK-03 | PLL unlock / wrong multiplier | CPU and FDCAN clock wrong | as FM-CLK-02 | RF | Register readback of RCC config, report-only (`drivers/registers.h:56-70`) | Low | DC-04 + HWSR-504a | Medium |
| FM-CLK-04 | LSI failure (IWDG clock) | Watchdog would not expire | Latent; relevant now (IWDG used since 2026-10-12, panda `9f60e17`) | MPF-L | None: LSI failure is latent; the start-up IWDG test (TSR-515) is open | None | IWDG start check at boot (prove reset path periodically, e.g. by a controlled watchdog reset at power-up) | Medium |

### 4.5 MCU power

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-PWR-01 | Supply loss | MCU off; relay de-energised *(if HWSR-502a holds)* | Safe for SG-01/07; SG-02/06 warning only from SoC (if SoC still powered) | S / MPF-P | — | n/a | — | n/a |
| FM-PWR-02 | Under-voltage above BOR (brown-out zone) | Undefined logic behaviour, flash read errors | SG-01… | SPF | BOR level unknown (option bytes); PVD not enabled (`stm32h7/interrupt_handlers.h:7` stub) | Unknown / low | BOR set + PVD → safe state (DC-07) | Medium–high |
| FM-PWR-03 | Over-voltage | Damage, erratic behaviour | SG-01… | SPF | None in MCU; Vin reported (`boards/cuatro.h:28-30`) | None | External supervisor (DC-02) with OV window | Medium |
| FM-PWR-04 | Supply ripple/noise, common supply with SoC | Common-cause with SoC; erratic resets | SG-02/06 (both lose function) | DFA item | — | — | DFA in WP-A-03 | — |
| FM-PWR-05 | Vin sense divider drift | Wrong reported voltage | None (report only today) | S today | — | — | Plausibility vs SoC PMIC reading | Low |

### 4.6 CAN transceivers

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-CAN-01 | Car-side XCVR1 TX stuck dominant | Car bus blocked | Vehicle-level CAN failure (EPS/ECM own diagnostics); SG-07 if PCS messages blocked on the joined bus | SPF (vehicle-level effect) | FDCAN error counters/bus-off read (`drivers/fdcan.h:44-63`); core reset on bus-off (`:76-84`); host `canError` (QM) | Low | Disable transceiver on persistent error (HWSR-508, DC-04); relay release | Medium |
| FM-CAN-02 | XCVR1 RX open / stuck recessive | No RX of car messages → envelope RX timeouts | SG-01: actuation blocked after RX timeout (≤ 2 s today, GAP-06) | MPF-D | RX checks (`safety.h:321-344`) | Medium (detected, slow) | FTTI-consistent timeouts (TSR-4xx) | High |
| FM-CAN-03 | Camera-side XCVR3 fault disturbing joined bus when relay released | Stock path disturbed | SG-07 | SPF | None | None | Disable bus-2 transceiver when relay released (firmware, if topology confirms) | Medium |
| FM-CAN-04 | Transceiver enable line stuck (enabled) | Transceiver active during reset | None by itself (no TX source during reset) | MPF-L | None | None | Read back enable state if possible | Low |
| FM-CAN-05 | Bit errors / corruption on the line (EMC) | CRC errors | Detected by CAN CRC | S / MPF-D | CAN protocol CRC | High | — | High |

### 4.7 Relay and relay driver

Since [RR-2026-010](reviews/RR-2026-010.md) the "relay" is the harness box intercept switch: two DG419LE CMOS analog switches (U1 CAN_H, U2 CAN_L), driven by SBU1, pulled to pass-through by R2 + R3, and powered from the box VIN. The FM-REL IDs are kept; their wording below follows the switch (rev 0.4). Contact welding, coil faults and chatter do not apply.

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-REL-01 | Switch stuck in pass-through (U1/U2 stuck on NC, SBU1 drive lost, R2/R3 short, or 5 V drive below the logic threshold with VL at VIN) while commanded to intercept | Stock camera LKA/ACC messages reach the car together with panda TX | SG-01, SG-03 (conflicting commands) | MPF-D (slow) | Stock-message-on-car-side check after 1 s grace, at 1 Hz (`safety.h:372-380`; `main.c:242`) → TX blocked (`safety.h:252`) | Medium (detected, 1–2 s latency, GAP-12) | Readback (DC-03, HWSR-506a) | High |
| FM-REL-02 | Switch stuck in intercept (U1/U2 stuck on NO, IN damaged high, or R2/R3 open with SBU1 undriven) while commanded released (SILENT, power-save, after fault) | Camera disconnected from car while panda forwards nothing or is off | **SG-07** (PCS messages lost) | **SPF** | None | None | Readback (DC-03); harness design check (HWSR-702) | High |
| FM-REL-03 | Switch channel open, high on-resistance, leakage or latch-up; box supply lost (RR-2026-010 F-02) | Bus interruptions or stock path broken | SG-07 (stock path), SG-01 (RX timeouts) | SPF for SG-07 | RX timeouts, CAN errors (item side only) | Low | Readback with stock-path continuity | Medium |
| FM-REL-04 | SBU1 driver output stuck (MCU pin or device-side driver, UK-06) "on" | As FM-REL-02 | SG-07 | SPF | None | None | Readback; external supervisor cut (DC-02) | High |
| FM-REL-05 | Debug command drives relay (`0xc5`, `main_comms.h:164-166`) | Systematic, listed for completeness | SG-07 | n/a (systematic, GAP-09) | 2026-10-12: refused in a car mode in the reference build (`reference_lock.h`); still operable in SILENT/NOOUTPUT | — | DC-09 | — |

### 4.8 SPI link (SoC↔MCU)

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-SPI-01 | Bit errors on the link | Corrupted command/TX frame accepted | SG-01, SG-03 (frame then passes the envelope checks, which bound the effect) | RF | 8-bit XOR checksum (`drivers/spi.h:97-104`) | Low | CRC + sequence counter (TSR-4xx, GAP-10) | High |
| FM-SPI-02 | Link stuck / no transfer | No commands, no heartbeat | Safe after heartbeat timeout (5 s, GAP-06). **2026-10-12:** authority revoked after 0.3 s in a car mode; SILENT after 5 s | MPF-D | Heartbeat (`main.c` 1 Hz path); since 2026-10-12 also `drivers/heartbeat_monitor.h` in the 100 Hz safety task (panda `c2e5d93`, not verified on hardware) | Medium (slow) | Faster timeout (FSC §8) | High |
| FM-SPI-03 | SPI DMA overrun / interrupt storm | Lost or repeated frames | as FM-SPI-01 | RF | Interrupt-rate fault, report-only (`stm32h7/llspi.h:86-88`) | Low | DC-04 | Medium |

### 4.9 Harness connector and sense lines

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-HAR-01 | Connector disconnected / partially inserted while driving | Panda loses CAN and relay drive; relay de-energises *(if HWSR-506)* | Safe for SG-07 if relay releases; SG-02/06 warning from SoC | MPF-P | Orientation detection paused while relay driven (`drivers/harness.h:59`); CAN loss → RX timeouts; host `canBusMissing` | Medium | HWSR-701a | Medium–high |
| FM-HAR-02 | Wrong orientation detection (sense line fault) | Wrong relay/ignition pin, wrong CAN pin mux (`boards/tres.h:58-98`), and logical CAN buses 0 and 2 swapped (`drivers/can_common.h:130-135`): the panda's bus 0 is then the camera side. The intercept drive goes to the ignition line, so the switch stays in pass-through, and the ignition sense reads the drive line | Switch not driven → stock camera and car joined → the stock `0x2E4` reaches logical bus 0 → relay-malfunction check (`check_relay`, 1 s grace, `safety.h` `stock_ecu_check`) blocks all TX. SG-01 and SG-07 safe; item unavailable. The reading is frozen while the switch is driven, so a misread arises only before engagement | MPF-D | Relay malfunction check | Medium | Plausibility of both SBU voltages; VS-HW-13 checks bus 0 = car side in both orientations | Medium |
| FM-HAR-03 | Harness wire short CAN-H/CAN-L or to supply | Bus failure | Vehicle-level (EPS/ECM diagnostics); SG-07 | SPF (vehicle-level) | CAN errors | Low | Out of LionDriver's control beyond installation inspection (WP-O-01) | Low |
| FM-HAR-04 | Relay box internal open in stock path | Camera disconnected | SG-07 | SPF | None | None | Installation check (PCS function check) + DC-03 | Medium |

### 4.10 Ignition sense

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-IGN-01 | Line open → reads "off" | Heartbeat timeout 2 s instead of 5 s (`main.c:101-103, 193`); SoC may not boot (bootkick) | Safe direction (shorter timeout); availability | S | Host ignition plausibility via CAN traffic (QM) | — | — | — |
| FM-IGN-02 | Line shorted → reads "on" | Heartbeat timeout 5 s; device stays powered after ignition off | Longer detection (GAP-06), battery drain | RF | None | None | Plausibility with CAN activity (Toyota has no CAN ignition hook, `opendbc_repo/opendbc/safety/ignition.h:12-63`) | Low–medium |

### 4.11 Other blocks

| FM-ID | Block | Failure mode | SG effect | Existing diagnostic | DC today | Planned |
|---|---|---|---|---|---|---|
| FM-TMP-01 | DTS | Sensor fault / over-temperature not detected | All (operation outside spec) | Reported (`main_comms.h:51-52`), no reaction | None | HWSR-509, DC-10 |
| FM-FAN-01 | Fan | Stall | Over-temperature (indirect) | Host fan check (onboard review) | Medium (QM) | — |
| FM-SIR-01 | Siren path | No sound on SoC loss | SG-02/06 (warning missing) — latent | None (no self-test) | None | Siren self-test at start-up (perceived by driver) |
| FM-RST-01 | SoC→MCU `STM_RST_N` | Held/pulsed by faulty SoC | MCU repeatedly reset: loss of function, relay released (safe for SG-01/07) | Reset flags | High (safe direction) | — |
| FM-BT0-01 | SoC→MCU `STM_BOOT0` | Asserted at reset | MCU in ROM bootloader: no TX, relay released *(inferred)* | Host detects missing panda | Medium | RDP/WRP (DC-07) for the cybersecurity aspect (GAP-38) |

## 5. Findings

1. **Dominant single-point faults today**: FM-CPU-01 (no CPU diagnostics), FM-RAM-02/03 (ECC
   not listened to), FM-FLS-02 (no run-time flash check), FM-REL-02/04 (relay stuck intercepting —
   SG-07), FM-CPU-03/05 (hang with relay driven — SG-07), FM-PWR-02 (brown-out zone). With these
   the SPFM for SG-01 and SG-07 cannot reach the ASIL B target (WP-H-04 §4).
2. **SG-07 has a hardware single-point path that no firmware change can close**: a relay stuck in
   the intercept position (FM-REL-02/04). Only readback (DC-03) or a harness design that makes this
   failure mode implausible (and evidence for it) can close it.
3. **The "report-only" pattern (GAP-08) is the main reason diagnostics present in silicon give no
   coverage**: CSS is the only hardware mechanism with a reaction today.
4. **No credible "high" coverage for the CPU** without hardware redundancy. With a software self-test
   library plus IWDG plus the vehicle external measures, the argument relies on the ASIL B target
   (FSC option (c)). An ASIL C claim for SG-01 would need DC-02 or a second channel (FSC §4.3).

## 6. FMEDA template (quantitative, to be filled)

### 6.1 Component-level FMEDA

All quantitative columns: **TBD — requires BOM** (WP-H-02 UK-02).

| Ref | Part (MPN) | Block | λ total (FIT) | Source (§2.3) | Failure mode | Distribution (%) | λ_FM (FIT) | Safety-related (Y/N) | Violates SG (without SM) | Safety mechanism (SPF/RF) | DC_RF (%) | λ_SPF/λ_RF (FIT) | Latent-fault SM | DC_MPF,L (%) | λ_MPF,L (FIT) | Safe fraction | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U? | STM32H725 (ordering code TBD) | MCU | TBD | ST data / 26262-11 model | see §6.2 | TBD | TBD | Y | SG-01…07 | §6.2 | TBD | TBD | TBD | TBD | TBD | TBD | Split per §6.2 |
| U? | CAN transceiver (TBD) ×4 | XCVR | TBD | SN 29500 | TX dominant / RX open / enable stuck / bus short | TBD | TBD | Y (XCVR1, XCVR3) | SG-01, SG-07 | FDCAN status + reaction | TBD | TBD | TBD | TBD | TBD | TBD | |
| K? | Intercept relay (TBD) | Relay | TBD | SN 29500 (relays) | Contact stuck closed / stuck open / coil open / coil short | TBD | TBD | Y | SG-01, SG-07 | Stock-message check; readback (planned) | TBD | TBD | TBD | TBD | TBD | TBD | Contact-wear dependent on cycles |
| Q? | Relay driver transistor (TBD) | Relay driver | TBD | SN 29500 | Short / open | TBD | TBD | Y | SG-07 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | |
| Y? | 25 MHz crystal/oscillator (TBD) | Clock | TBD | SN 29500 | No oscillation / drift | TBD | TBD | Y | SG-01 | CSS / cross-check | TBD | TBD | TBD | TBD | TBD | TBD | |
| U? | MCU regulator (TBD) | Power | TBD | SN 29500 | Output OV / UV / drift / off | TBD | TBD | Y | SG-01 | BOR/PVD/ext. supervisor | TBD | TBD | TBD | TBD | TBD | TBD | |
| R? | Vin divider, SBU sense resistors | Sense | TBD | SN 29500 | Open / short / drift | TBD | TBD | Y (SBU) | SG-07 | Orientation plausibility | TBD | TBD | TBD | TBD | TBD | TBD | |
| J? | Harness connector, crimps | Harness | TBD | SN 29500 | Open / short / intermittent | TBD | TBD | Y | SG-07 | CAN timeouts | TBD | TBD | TBD | TBD | TBD | TBD | |
| … | (all remaining BOM parts) | | TBD | | | | | | | | | | | | | | |

### 6.2 STM32H7 internal split (ISO 26262-11 style)

| Part / sub-part | Fraction of MCU λ (die) | Failure modes (examples) | SG relevant | Safety mechanism (planned) | DC (qualitative, planned) | λ values |
|---|---|---|---|---|---|---|
| CPU core (Cortex-M7) incl. FPU | TBD | Wrong result, hang, wrong branch | Y | STL + IWDG + plausibility | Medium | TBD — requires supplier data |
| Flash + controller | TBD | Bit errors, wrong address decode | Y | ECC + periodic CRC | High | TBD |
| SRAM (DTCM, AXI, SRAM1/2/4, backup) | TBD | Soft/hard bit errors, addressing | Y | ECC + RAMECC + start-up test | High | TBD |
| Interconnect / bus matrix / DMA | TBD | Wrong transfer, stuck | Y | MPU, end-to-end checks | Low–medium | TBD |
| Clock (RCC, PLL, HSE interface, LSI) | TBD | Stop, drift | Y | CSS, cross-check | Medium–high | TBD |
| Power (SMPS/LDO, POR/BOR, PVD) | TBD | UV/OV | Y | BOR, PVD, ext. supervisor | Medium | TBD |
| FDCAN1–3 | TBD | Wrong frame, stuck | Y | Protocol CRC, E2E (TSR-4xx), status | Medium | TBD |
| GPIO (relay, enables) | TBD | Stuck output | Y | Readback (planned) | Medium | TBD |
| ADC (SBU, Vin) | TBD | Wrong conversion | Y (SBU) | Plausibility | Low | TBD |
| SPI4 | TBD | Corrupted transfer | Y | CRC + counter | High | TBD |
| IWDG | TBD | Fails to reset | Latent | Start-up test | Medium | TBD |
| USB, SAI, I2C, timers for LEDs/fan | TBD | — | N (verify no interference) | — | — | TBD |
| Package / pins | TBD | Open, short | Y | Per pin function | — | TBD |
| Transient faults (all sequential logic) | TBD | Bit flips | Y | As per part | — | TBD |

### 6.3 First quantitative estimate with generic failure rates (BL-002)

§6.1 and §6.2 stay TBD until the BOM is known. Meanwhile a block-level FMEDA with **generic** failure rates is kept as YAML in [`../08-analyses/fmea/analyses/fmeda-sg001.yaml`](../08-analyses/fmea/analyses/fmeda-sg001.yaml) and [`fmeda-sg009.yaml`](../08-analyses/fmea/analyses/fmeda-sg009.yaml) (SG IDs of LD-HARA-001: SG-001 = SG-01 here, SG-009 = SG-07). The metrics are computed by `tools/safety/fmea_lint.py`, and the same formulas are used in the workbooks from `tools/safety/export_fmeda_xlsx.py`.

The rates are order-of-magnitude estimates per part type, not values looked up for the actual parts, with one exception from rev 0.4 (2026-10-16): the harness box analog switches U1/U2 (DG419LE) take the SN 29500-2 reference value for CMOS analog and mixed-signal ICs, 25 FIT per IC at θVJ = 55 °C. That value is quoted from TI functional-safety FIT reports (TPS1663, LM73605, LMR36015-Q1; two other TI reports quote 20 FIT, and the higher value is used). The standard itself was not read, and no stress conversion to the mission profile is applied. The other harness box parts (BAS40SDW, STPS2H100ZFY, SMF16A, DMN3200U, the resistors) are known from the v3 drawing and their SN 29500 class is named in the YAML. No reference value for them could be reached from the analysis environment, so they keep generic rates until the source is confirmed (OI-2). The results show where the architecture falls short. **They are not evidence of compliance.**

| Goal | Target used | λ (FIT) | SPFM | LFM | λSPF + λRF (FIT) | Result |
|---|---|---|---|---|---|---|
| SG-01 lateral | ASIL D (LD-HARA-001); ASIL C here, ASIL B shown alongside (DQ-063) | 255 | 96.8 % | 88.9 % | 8.1 | Misses D on SPFM and LFM. Misses C on SPFM (97 %) by 0.2 points; meets C on LFM. Meets B (90 % / 60 %) |
| SG-07 stock PCS | ASIL B | 288 | 78.1 % | 97.6 % | 63.1 | Misses B on SPFM (90 %). Accepted by the lead as a recorded deviation, conditional on the harness box bench tests ([WP-H-04](WP-H-04-hardware-metrics.md) §5.3, DQ-320) |

The SG-07 drop from 85.9 % (rev 0.3) to 78.1 % comes entirely from the switch rate: 2 × 5 FIT generic became 2 × 25 FIT. With no readback and no stock-path check, 70 % of that rate is single-point for SG-07.
Rev 0.9 (2026-10-27) adds the camera-side termination R7/R8 (FMD-C-014, 0.4 FIT): a short is single-point for SG-07 (camera frames lost in intercept), and one open is latent, because only both open leave the camera bus unterminated (harness box SPICE pilot, a prediction; VS-HW-24 (e) measures it). λSPF + λRF rises by 0.16 FIT; SPFM stays 78.1 % at one decimal.

Largest contributors:
- **SG-01:**
  - wrong result of a CPU limit or authority check, fully latent (12.5 FIT λMPF,L);
  - clock drift with no cross-check (5.0);
  - supply in the brown-out zone (4.5 FIT λSPF);
  - intercept switch stuck in pass-through while driven (1.75 FIT λRF after the relay-malfunction check).
- **SG-07:**
  - intercept switch channel open, high on-resistance, leakage or latch-up in the stock path (20.0 FIT λSPF);
  - intercept switch stuck in intercept (15.0);
  - CAN transceiver TX stuck dominant or RX open with the switch driven (6.0 each);
  - stock-path open in the harness or connector (3.0);
  - SBU1 driver stuck on, and wrong forwarding decision (2.5 each).

**Sensitivity.** About 90 of the 255 FIT are single-bit SRAM upsets that ECC corrects. They count as covered multiple-point faults and so raise SPFM. With the SRAM soft-error rate at 10, 100 and 500 FIT for the 64 KB considered, the results move as follows:

| SRAM rate (FIT) | SG-01 SPFM | SG-07 SPFM |
|---|---|---|
| 10 | 95.6 % | 68.4 % |
| 100 | 96.8 % | 78.1 % |
| 500 | 98.3 % | 90.6 % |

The switch rate matters as much: SG-07 SPFM is 85.9 % at 5 FIT per IC and 78.1 % at 25 FIT per IC. A real SER figure for the STM32H725 (OI-3) and a confirmed reference value for the DG419LE therefore matter as much as the part list.

**With the planned measures.** The DC values below are assumptions for this estimate, chosen conservatively from Annex D. They are not claims.
- **SG-01**, all of these together:
  - BOR/PVD reaction (DFM-ACT-005): DC 90 % on the brown-out mode;
  - RAMECC double-error reaction (DFM-ACT-002): DC 90 % latent on multi-bit upsets in authority variables;
  - clock cross-check (DFM-ACT-004): DC 90 % latent on drift;
  - a low-coverage CPU self-test (DFM-ACT-001): DC 60 % latent on wrong check results;
  - TX read-back (TSR-517): DC 99 % on frames altered after the check.

  Result: SPFM 99.1 %, LFM 95.4 %, λSPF + λRF 2.3 FIT. That meets ASIL D on generic rates, and so ASIL C and B.
- **SG-07**, added in this order, each with DC 90 %:
  - switch position readback (DFM-ACT-007, DC-03) on stuck in intercept and SBU1 driver stuck on: SPFM 83.6 %;
  - releasing the switch on a transceiver fault (DFM-ACT-006) on TX stuck dominant and RX open: 87.3 %;
  - a readback that also checks stock-path continuity, on channel open and harness open: **94.5 %**, λSPF + λRF 15.8 FIT. That meets ASIL B. None of the three covers an R7/R8 short (FMEDA rev 0.9), which stays single-point.

  Position readback alone no longer reaches 90 % (it did at rev 0.3). The stock-path continuity check is needed.
- **Caveat for SG-07:** a switch stuck in intercept cannot be released. The readback can only warn that stock AEB is unavailable and refuse to engage. The lead accepted that as the degraded state ([DQ-064](../01-management/decisions/register.yaml), OI-9).

### 6.4 Other safety goals: reuse of the SG-01 and SG-07 rows (DQ-362)

The lead decided to reuse the rows of the two FMEDA files for the other goals rather than build a separate FMEDA per goal ([DQ-362](../01-management/decisions/register.yaml), option A, 2026-10-18; for SG-04 already [DQ-002](../01-management/decisions/register.yaml), 2026-10-14). Their random hardware faults run through the same panda, CAN transceivers and harness box. There is one analysis, with a note per goal below and on each row the FTA cites ([`fta-fmea-map.yaml`](../08-analyses/fta-fmea-map.yaml)). Rates, classifications and metrics are unchanged. The rows stay classified for SG-01 or SG-07, so the figures of §6.3 stand for the shared path, not for a goal-specific classification.

| Goal | ASIL | Rows that carry it | Note |
|---|---|---|---|
| SG-02 lateral loss without warning | C | SG-001: FMD-003 (hang), FMD-014 (supply loss), FMD-017 (TX stuck dominant), FMD-018 (RX open); SG-009: FMD-001 (hang with the relay driven), FMD-030 (harness box unpowered) | These faults stop actuation. They are safe for SG-01 but violate SG-02 when no warning follows. The warning comes from the host (`controlsMismatch`, TSR-621) or from the panda siren when the panda still runs; the siren path has no FMEDA row (no rate data, DFM-017, FM-SIR-01) |
| SG-06 longitudinal loss without warning | C | As SG-02 | As SG-02, for ACC_CONTROL |
| SG-03 unintended acceleration | C | SG-001: FMD-002, FMD-010 (frame altered after the TX check), FMD-019 (bit errors on the line) | `0x343` leaves through the same TX path as `0x2E4`, so the rows and rates apply as for SG-04 |
| SG-05 release on brake, cancel or override | B | SG-001: FMD-001 (wrong authority check), FMD-009 (multi-bit upset in authority variables) | Multiple-point for SG-01 (they need an out-of-envelope SoC command), but effectively single-point for SG-05: authority that stays on after the brake needs no second fault. Since FMEDA rev 0.7 this is a `per_goal` entry on both rows, which gives SG-05 its own estimate: SPFM 90.38 %, LFM 95.30 %, λSPF + λRF 24.6 FIT; ASIL B met by 0.38 points |

**Result against ASIL C.** SG-02, SG-03 and SG-06 carry the SG-01 estimate: SPFM 96.84 %, LFM 88.94 %. LFM meets the ASIL C target (80 %). SPFM misses 97 % by 0.16 points. The lead accepted this as an open hardware item for G2, [WP-H-04](WP-H-04-hardware-metrics.md) OI-6. It closes with supplier rates (OI-3, OI-10) or with the TSR-517 transmit read-back. The lead decided not to pay for ST's safety package and to write LionDriver's own CPU and RAM self-tests with low CPU coverage ([DQ-069](../01-management/decisions/register.yaml), option B, 2026-10-19), so part-specific MCU rates and a higher CPU coverage claim are unlikely and **the ASIL C SPFM target is likely missed**; the gap moves to G2. As an estimate, TSR-517 alone at an assumed DC 99 % on FMD-002 and FMD-010 gives SPFM 97.53 % and LFM 89.02 %. If neither closes the gap by G2, it goes back to the lead.

**Not covered.** Reusing SG-01 classifications means the faults that are safe for SG-01 and dangerous for SG-02/SG-06 (loss of actuation) are not scored as such. A goal-specific classification was the option the lead did not choose (DQ-362 option B). The FTA events that rest on these rows (BE-2.06, BE-2.07, BE-3.04, BE-5.02, BE-6.02) now have their FMEDA rows named here.

## 7. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Obtain BOM and schematic (WP-H-02 OI-1) and fill §6.1 | G3 |
| OI-2 | ~~Safety manager to confirm the failure-rate source choice in §2.3~~ **Decided** ([DQ-068](../01-management/decisions/register.yaml), option A, 2026-10-19): the §2.3 set is approved. Obtaining SN 29500 and IEC 61709 stays with OI-10 | G2 |
| OI-3 | Request ST FIT and failure-mode distribution for STM32H72x/73x where ST gives them without a licence; no licence is bought ([DQ-069](../01-management/decisions/register.yaml), option B, 2026-10-19). Otherwise select a die/package model per ISO 26262-11 and justify it (WP-H-07 QE-02) | G3 |
| OI-4 | Confirm which STM32H725 SRAM regions have ECC and how errors are signalled (RM0468) and adjust FM-RAM rows | G2 |
| OI-5 | Perform the deductive (FTA) check of this FMEA in WP-A-04 | G3 |
| OI-6 | Define fault-injection methods for each "planned" DC claim (WP-H-06) | G3 |
| OI-7 | Analyse the harness relay design to confirm or refute FM-REL-02/04 plausibility (relay type, coil drive) | G2 |
| OI-8 | Re-run the FMEA after each WP-H-02 §6 change is implemented | G3 |
| OI-9 | ~~SG-07: decide the safe state when relay readback finds the relay welded in the intercept position~~ **Decided** ([DQ-064](../01-management/decisions/register.yaml), option A, 2026-10-14): warn the driver that stock AEB is unavailable and refuse to engage; accepted as the degraded state. It applies only once readback exists (DC-03, HWSR-506a, DQ-209); with the v3 box the same case is a switch stuck in intercept (FM-REL-02/04). The HMI warning requirement belongs to the FSC and TSR owners | G2 |
| OI-10 | Replace the generic rates of §6.3 with part-specific values (BOM, ST data, SER) and add the dual-point PMHF term. 2026-10-16: U1/U2 at the SN 29500-2 reference value (secondary source); the other harness box parts are classed but still generic | G3 |
