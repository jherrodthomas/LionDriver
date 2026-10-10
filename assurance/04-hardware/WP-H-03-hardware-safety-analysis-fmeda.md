# WP-H-03 Hardware safety analysis (FMEA / FMEDA)

| Field | Value |
|---|---|
| Work product | WP-H-03 Hardware safety analysis (FMEA/FMEDA) |
| Standard reference | ISO 26262-5:2018 §7 (safety analyses on HW design), §8 (metrics input), Annex D (diagnostic coverage of safety mechanisms, informative); ISO 26262-9:2018 §8 (safety analyses); ISO 26262-11:2018 (semiconductor failure modes, informative); ASPICE 4.0 HWE.2 |
| Version | 0.1 |
| Status | Draft (qualitative FMEA); quantitative FMEDA is a template |
| ASIL / scope | ASIL D (provisional, SG-01, until re-rated under FSC option (c)) / ASIL C (SG-03…SG-05) / ASIL B (SG-02, SG-06, SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `8b8c6ae` |

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

### 2.3 Failure-rate sources (proposal)

| Element class | Proposed source | Reason |
|---|---|---|
| Discrete parts, relay, connectors, crystal, transceivers, regulators | **SN 29500** (Siemens) series, with its reference conditions adjusted to the mission profile | Widely used in automotive FMEDAs, covers relays and connectors, publicly purchasable, consistent stress model |
| Integrated circuits without supplier data | SN 29500 (IC part) as primary; **IEC 61709** for the conversion of reference conditions | Consistency with the above |
| STM32H7 (die + package) | Supplier FIT and failure-mode distribution from ST if obtainable ([WP-H-07](WP-H-07-hardware-component-qualification.md) QE-02); otherwise a die/package model of the IEC TR 62380 type as referenced in ISO 26262-11 (IEC TR 62380 is no longer maintained by IEC — verify status) | ISO 26262-11 gives the method for splitting a microcontroller into parts and distributing failure modes |
| Soft errors (SRAM, flash, registers) | Supplier soft-error data (SER in FIT/Mbit) if available; otherwise a literature value with justification | Transient faults dominate SRAM; ECC credit depends on it |
| Harness wiring and crimps | SN 29500 (connections) | |

One source per class is used throughout; mixing handbooks within one class is avoided. The
choice is to be confirmed by the safety manager (OI-2).

### 2.4 Mission profile (placeholder)

To be defined in WP-H-05 §3: vehicle service life, operating hours per year, ambient and
in-cabin temperature profile (windscreen-mounted device, sun load), and on/off cycles. Needed
for SN 29500 stress factors and for the latent-fault exposure time.

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

### 4.1 MCU core (CPU, buses, interrupt controller)

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned mechanism | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-CPU-01 | Wrong instruction execution / wrong data path result (permanent) | Safety check computes wrong result (e.g. torque limit passes out-of-range value, `controls_allowed` wrongly true) | SG-01, SG-03, SG-04, SG-05 | SPF | None in MCU. Host compares `controls_allowed` with its own state after 2 s (`controlsMismatch`, onboard review) — QM, slow, and does not check limits | None | Software CPU self-test library at start-up and periodically (vendor STL if available for STM32H7, WP-H-07 QE-03), plus control-flow monitoring with the IWDG (DC-01) | Medium (single core, no lockstep; "high" is not credible without hardware redundancy) |
| FM-CPU-02 | Transient upset (soft error in registers/pipeline) | As FM-CPU-01 for one cycle | SG-01… (one frame) | RF | None | None | Same as above; per-frame limit re-evaluation bounds a single-frame effect | Low–medium |
| FM-CPU-03 | Program-flow hang (stuck in loop or ISR, stuck critical section) | TX stops; forwarding stops; relay stays in last state | SG-07 (relay driven, PCS forwarding lost); SG-02/06 (actuation lost — EPS timeout — without MCU warning) | SPF for SG-07 | SW watchdog in the same ISR (`drivers/simple_watchdog.h:7-17`) cannot see a hang; host sees missing panda states (QM) | Low (host only) | IWDG window + safe service point (DC-01) → reset → relay released | High (for hang); medium for timing faults |
| FM-CPU-04 | Unexpected exception (HardFault/NMI) | Reset via cookie path (`early_init.h:73-80`) | Transient loss of function; safe for SG-01; relay released after reset *(if HWSR-502 holds)* | S / MPF-D | Reset + `HEALTH_FLAG_*_RESET` reported (`main.c:319-325`) | High (for this mode) | — | High |
| FM-CPU-05 | Exception routed to `Default_Handler` (unused vector, SVC, PendSV, DebugMon) | Infinite loop (`stm32h7/startup_stm32h7x5xx.s:111-114`) | As FM-CPU-03 | SPF for SG-07 | None | None | DC-08 + IWDG | High |
| FM-CPU-06 | Interrupt controller fault: CAN or tick IRQ lost or storm | Missing checks or overload | SG-01 (missed RX checks), SG-07 | RF | Interrupt-rate monitor, report-only (`drivers/interrupts.h:34-37`) | Low | DC-04 (reaction) + IWDG | Medium |
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
| FM-CLK-04 | LSI failure (IWDG clock) | Watchdog would not expire | Latent (once IWDG used) | MPF-L | n/a today | — | IWDG start check at boot (prove reset path periodically, e.g. by a controlled watchdog reset at power-up) | Medium |

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

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-REL-01 | Relay stuck released (contacts welded in stock position, coil open, driver open) while commanded to intercept | Stock camera LKA/ACC messages reach the car together with panda TX | SG-01, SG-03 (conflicting commands) | MPF-D (slow) | Stock-message-on-car-side check after 1 s grace, at 1 Hz (`safety.h:372-380`; `main.c:242`) → TX blocked (`safety.h:252`) | Medium (detected, 1–2 s latency, GAP-12) | Readback (DC-03, HWSR-506a) | High |
| FM-REL-02 | Relay stuck intercepting (contacts welded, driver shorted) while commanded released (SILENT, power-save, after fault) | Camera disconnected from car while panda forwards nothing or is off | **SG-07** (PCS messages lost) | **SPF** | None | None | Readback (DC-03); harness design check (HWSR-702) | High |
| FM-REL-03 | Relay contact intermittent / chatter | Bus interruptions | SG-07 (intermittent), SG-01 (RX timeouts) | RF | RX timeouts, CAN errors | Low | Readback | Medium |
| FM-REL-04 | Relay driver output stuck (MCU pin or driver transistor) "on" | As FM-REL-02 | SG-07 | SPF | None | None | Readback; external supervisor cut (DC-02) | High |
| FM-REL-05 | Debug command drives relay (`0xc5`, `main_comms.h:144-147`) | Systematic, listed for completeness | SG-07 | n/a (systematic, GAP-09) | — | — | DC-09 | — |

### 4.8 SPI link (SoC↔MCU)

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-SPI-01 | Bit errors on the link | Corrupted command/TX frame accepted | SG-01, SG-03 (frame then passes the envelope checks, which bound the effect) | RF | 8-bit XOR checksum (`drivers/spi.h:97-104`) | Low | CRC + sequence counter (TSR-4xx, GAP-10) | High |
| FM-SPI-02 | Link stuck / no transfer | No commands, no heartbeat | Safe after heartbeat timeout (5 s, GAP-06) | MPF-D | Heartbeat (`main.c:191-225`) | Medium (slow) | Faster timeout (FSC §8) | High |
| FM-SPI-03 | SPI DMA overrun / interrupt storm | Lost or repeated frames | as FM-SPI-01 | RF | Interrupt-rate fault, report-only (`stm32h7/llspi.h:86-88`) | Low | DC-04 | Medium |

### 4.9 Harness connector and sense lines

| FM-ID | Failure mode | Local effect | SG effect | Class (today) | Existing diagnostic | DC today | Planned | DC planned |
|---|---|---|---|---|---|---|---|---|
| FM-HAR-01 | Connector disconnected / partially inserted while driving | Panda loses CAN and relay drive; relay de-energises *(if HWSR-506)* | Safe for SG-07 if relay releases; SG-02/06 warning from SoC | MPF-P | Orientation detection paused while relay driven (`drivers/harness.h:59`); CAN loss → RX timeouts; host `canBusMissing` | Medium | HWSR-701a | Medium–high |
| FM-HAR-02 | Wrong orientation detection (sense line fault) | Wrong relay/ignition pin and wrong CAN pin mux (`boards/tres.h:58-98`) | Relay not driven → stock messages on car side → FM-REL-01 detection path; SG-07 safe | MPF-D | Relay malfunction check | Medium | Plausibility of both SBU voltages | Medium |
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
   (FSC option (c)). An ASIL D claim for SG-01 (its rating until re-rated) would effectively need DC-02
   and/or a second independent channel (FSC §4.3); the ASIL C targets of SG-03…SG-05 are also unlikely
   without DC-02 (WP-H-04 §5.1).

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

## 7. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Obtain BOM and schematic (WP-H-02 OI-1) and fill §6.1 | G3 |
| OI-2 | Safety manager to confirm the failure-rate source choice in §2.3 | G2 |
| OI-3 | Request ST FIT and failure-mode distribution for STM32H72x/73x, or select a die/package model and justify it (WP-H-07 QE-02) | G3 |
| OI-4 | Confirm which STM32H725 SRAM regions have ECC and how errors are signalled (RM0468) and adjust FM-RAM rows | G2 |
| OI-5 | Perform the deductive (FTA) check of this FMEA in WP-A-04 | G3 |
| OI-6 | Define fault-injection methods for each "planned" DC claim (WP-H-06) | G3 |
| OI-7 | Analyse the harness relay design to confirm or refute FM-REL-02/04 plausibility (relay type, coil drive) | G2 |
| OI-8 | Re-run the FMEA after each WP-H-02 §6 change is implemented | G3 |
