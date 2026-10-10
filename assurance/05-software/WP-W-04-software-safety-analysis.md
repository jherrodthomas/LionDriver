# WP-W-04 Software Safety Analysis and Software-Level Dependent Failure Analysis

| Field | Value |
|---|---|
| Work product | WP-W-04 Software safety analysis and software-level DFA |
| Standard reference | ISO 26262-6:2018 §7 (safety analysis and DFA at the software architectural level; Annex E informative); ISO 26262-9:2018 §7 (dependent failures), §8 (safety analyses); ASPICE 4.0 SWE.2 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Envelope software (E-03a/E-03b): B‡ (ASIL D until SG-01 re-rating; C for SG-03…SG-05); host components summarised |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); I2 per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This analysis examines the software architecture of [WP-W-03](WP-W-03-software-architecture.md) for failure modes that can violate the safety goals (SG-01…SG-07, [WP-C-03](../02-concept/WP-C-03-hara.md)), checks which existing mechanisms cover them, and derives SWSRs for the gaps. It also analyses dependent failures inside the software (shared state, interrupts, buffers, common-mode between controller and envelope).

Inputs: [WP-W-02](WP-W-02-software-safety-requirements.md), [WP-W-03](WP-W-03-software-architecture.md), [WP-S-03 §6](../03-system/WP-S-03-technical-safety-concept-architecture.md) (mechanism catalogue SM-nn), [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md) SFMEA-12, -13, -16, -18, -19 (system-level software rows refined here), [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) (FFI-SP/TM/CM rows), [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md).

The analysis was done by code reading at the baseline. It has not been reviewed. Nothing here is test evidence.

## 2. Method

- **SW FMEA / HAZOP hybrid.** For each component of WP-W-03 §3.1 and each of its outputs, the guide words *wrong value*, *stuck* (no update), *late*, *omission* and *commission* (unintended output) are applied. Causes considered: systematic software defects, wrong configuration from the SoC, corrupted input data, and random hardware faults that manifest in software (RAM bit flip, hang).
- **Effect** is traced to the vehicle level through the safe states SS-L, SS-G, SS-S of [WP-S-02 §2.3](../03-system/WP-S-02-technical-safety-requirements.md).
- **Mechanism** is what detects or prevents the failure at the baseline, with file:line. **Gap** leads to an SWSR in WP-W-02.
- Rating: **C** covered, **P** partly covered, **N** not covered.
- **DFA** (§4) uses the coupling factors of ISO 26262-9 §7 applied to software: shared resources (memory, execution time, peripherals), shared information inputs, common design/specification, and common development (same author/values).

## 3. Software FMEA

### 3.1 Safety layer (E-03a)

| ID | Component / output | Guide word: failure mode | Effect (SG) | Existing mechanism | Rating | Gap → SWSR |
|---|---|---|---|---|---|---|
| SWF-01 | U-SAF-LAT torque check | Wrong value: limit check passes an excessive torque (defect in comparison, sign handling, `to_signed`) | Excess lateral torque (SG-01) | Unit tests, mutation tests (upstream CI only); 100 % line coverage | P | Branch/MC/DC (WP-W-06 UV-G1); `@req`-based boundary tests (SWSR-101, 103) |
| SWF-02 | U-SAF-LAT | Stuck: `desired_torque_last`/`rt_torque_last` not reset after violation or disengagement | Rate limit too loose on resume (SG-01) | Reset on violation or `!controls_allowed` (`lateral.h:140-148`); reset on mode change (`safety.h:440-449`) | C | — |
| SWF-03 | U-SAF-LAT | Commission: torque accepted while not engaged with STEER_REQUEST=1 and torque 0 | EPS enters LKA-active with zero torque; next frame may ramp (SG-01, mode confusion) | Torque ≠ 0 rejected (`lateral.h:98-101`) | P | SWSR-105 (GAP-48) |
| SWF-04 | U-SAF-LAT | Omission of safe state: violation detected, frame dropped, EPS keeps last torque until its own timeout | Torque persists up to ≈2 s (SG-01, SG-05) | `safety_tx_blocked` counted (`drivers/can_common.h:168-171`) | N | SWSR-108, 109, 109a (GAP-46) |
| SWF-05 | U-SAF-LAT | Wrong value: speed-independent limit too high at high speed | Lateral deviation beyond controllability (SG-01) | Fixed 1500 raw | N | SWSR-102, 102a (GAP-04) |
| SWF-06 | U-SAF-LAT | Wrong value: measured-torque window uses wrong EPS scale (`param & 0xFF` from SoC) | Measured-torque limit wrong by factor up to 3.5 (SG-01) | none (`modes/toyota.h:383`) | N | SWSR-104a, 512 (GAP-44) |
| SWF-07 | U-SAF-LAT | Commission: driver opposes, envelope keeps accepting torque within limits | Fight with driver (SG-05, SG-01) | EPS (AoU); host 500 raw (QM) | N | SWSR-304, 304a (GAP-02) |
| SWF-08 | U-SAF-LONG | Wrong value: accel outside bounds accepted | Unintended accel/decel (SG-03, SG-04) | Bound check (`longitudinal.h:8-12`), tests | C (defect) | — |
| SWF-09 | U-SAF-LONG | Wrong value: abrupt step within bounds (−3.5 → +2.0 in one frame) | Jerk beyond controllability (SG-03, SG-04) | none in envelope | N | SWSR-204, 205 |
| SWF-10 | U-SAF-TOY TX | Commission: other `0x343` fields (PERMIT_BRAKING, RELEASE_STANDSTILL) request action without authority | Standstill release / braking without engagement (SG-03, SG-04) | ACCEL_CMD only | N | SWSR-207 (GAP-48) |
| SWF-11 | U-SAF-TOY TX | Commission: PCS/DSU messages (`0x344`, `0x411`, DSU set) sent by SoC | Stock PCS altered (SG-07) | whitelist allows; `0x283` content check only | N | SWSR-705 (GAP-42, GAP-49) |
| SWF-12 | U-SAF-CORE authority | Commission: authority granted on edge while an RX message is already lagging | Actuation on stale state (SG-01, SG-03) | Timeout evaluated at 1 Hz | P | SWSR-306, 401a |
| SWF-13 | U-SAF-CORE RX | Stuck: `0x1D2`/`0x226` frozen or replayed with valid checksum (`0x226` has none) | Authority not revoked on brake/cancel (SG-05, SG-01) | Timeout only; checksum on `0x1D2` | N | SWSR-403, 404, 405 (GAP-01); refines WP-A-04 SFMEA-13 |
| SWF-14 | U-SAF-CORE RX | Late: message loss detected after 1–2 s | Actuation on stale vehicle state (SG-01, SG-03) | `safety_tick` (`safety.h:321-344`) | P | SWSR-401, 401a (GAP-06) |
| SWF-15 | U-SAF-CORE RX | Wrong value: wheel speed corrupted (no checksum) → `vehicle_moving` false | Brake-while-moving rule disabled; dynamic limit (future) wrong | Wheel fault bits only (`modes/toyota.h:84-93`) | P | SWSR-405(a) |
| SWF-16 | U-SAF-CORE mode | Commission: `set_safety_hooks` with another brand/param | Envelope enforces wrong limits (all SGs) | Host cross-check after 10 s (QM, same source) | N | SWSR-512 (GAP-09) |
| SWF-17 | U-SAF-CORE relay | Omission: relay malfunction latch cleared by `0xdc` | Camera and item commands both reach the car (SG-01), PCS cut (SG-07) | none | N | SWSR-506a (GAP-48) |
| SWF-18 | U-SAF-CORE forwarding | Late/omission: forwarding of camera frames stops or is delayed (queue full, power save) | Stock PCS frames lost while relay driven (SG-07) | overflow counted (`drivers/can_common.h:165`) | N | SWSR-707, 513 (`0xe7`) |
| SWF-19 | U-SAF-CORE EPS status | Omission: EPS fault not seen by envelope | Unannounced loss of steering assist (SG-02) | host only | N | SWSR-110 (GAP-03) |
| SWF-20 | U-SAF-HELP | Wrong value: macro side effects / overflow in `SAFETY_ABS(INT_MIN)`, float rounding in `safety_interpolate` | Wrong limit | UBSan on host; review | P | VS-UV-01, VS-UV-S3 |

### 3.2 Panda platform (E-03b)

| ID | Component / output | Guide word: failure mode | Effect (SG) | Existing mechanism | Rating | Gap → SWSR |
|---|---|---|---|---|---|---|
| SWF-21 | U-PND-SPI | Wrong value: corrupted control request passes 8-bit XOR | Wrong command executed, e.g. `0xdc`, `0xc5` (all) | XOR, NACK (`drivers/spi.h:97-138`) | P | SWSR-410 (GAP-10); refines SFMEA-18 |
| SWF-22 | U-PND-SPI | Commission: header length > buffer → DMA overrun | Corruption of SRAM1/2 beyond `spi_buf_rx` (`spi_buf_tx`), then DMA error; effect on envelope state to be confirmed from map file | none (`drivers/spi.h:115-116, 233`) | N | SWSR-412 (GAP-47); refines SFMEA-19 |
| SWF-23 | U-PND-COMMS | Commission: `0xe8` index out of range | Write outside `bus_config[]` | none (`main_comms.h:262-264`) | N | SWSR-412a (GAP-47) |
| SWF-24 | U-PND-COMMS | Commission: configuration requests in car mode (`0xc5`, `0xe5`, `0xde`, `0xf9`, `0xfc`, `0xe8`, `0xdb`, `0xe6`, `0xe7`, `0xf1`, `0xd1/1`, `0xd8`) | Relay/CAN config changed, softloader entry, MCU reset while driving (all; loss of function) | `0xdf`, `0xf8` gated; `0xb5`, `0xd1/0` debug-only | N | SWSR-511a, 512a, 513 (GAP-49); `0xc0` → WP-W-02 OI-5 |
| SWF-25 | U-PND-COMMS | Stuck: SoC freezes but `pandad` keeps sending heartbeats with `engaged=1` | Envelope keeps authority while last frames repeat or stop (SG-01, SG-02) | Mismatch only if `engaged` drops | N | SWSR-408, 409, 409h (GAP-10); WP-A-02 FFI-CM-11 |
| SWF-26 | U-PND-COMMS | Wrong value: repeated/old CAN-TX transfer | Stale command re-applied within limits | none | N | SWSR-410a, 411 |
| SWF-27 | U-PND-COMMS reassembly | Wrong value: partial packet carried over after resync | Malformed frame to TX hook (rejected by whitelist/length unless it matches) | Whitelist + XOR (`drivers/fdcan.h:100`) | P | SWSR-412b |
| SWF-28 | U-PND-MAIN heartbeat | Late: heartbeat loss detected after 4–5 s | Actuation continues on dead SoC (SG-01, SG-02) | 1 Hz counter | P | SWSR-407, 510 (GAP-06) |
| SWF-29 | U-PND-MAIN tick | Omission: tick ISR not executed (starved by comms ISRs or hung handler) | No timeout or heartbeat supervision (all) | Interrupt-rate fault, report-only; software watchdog in the same ISR | N | SWSR-501, 502b, 519 (GAP-07, GAP-50); refines SFMEA-16 |
| SWF-30 | U-PND-PLAT | Stuck: any handler or `assert_fatal` loops | Relay stays driven, forwarding stops (SG-07), no TX (SG-02) | NMI/HardFault reset only | N | SWSR-501, 502a (GAP-43) |
| SWF-31 | U-PND-FLT | Omission: detected faults (interrupt rate, register divergence, siren) produce no reaction | Fault persists while engaged (all) | report-only (`sys/faults.h:8-27`) | N | SWSR-502, 503a (GAP-08) |
| SWF-32 | U-PND-FDCAN TX | Wrong value: frame altered after TX hook (queue RAM bit flip) | Approved frame changed (SG-01, SG-03) | Packet XOR before FIFO load (`drivers/fdcan.h:100`); message RAM not covered | P | SWSR-517 (TX read-back), SWSR-503b; HW measures (WP-H-03) |
| SWF-33 | U-PND-FDCAN RX | Omission: RX FIFO overflow loses frames | Missed brake edge if `0x226` lost (SG-05) | `total_rx_lost_cnt` (`drivers/fdcan.h:168-171`) | P | Edge logic tolerates one loss only if brake stays pressed; SWSR-401 timeout; add overflow → fault (SWSR-502b) |
| SWF-34 | U-PND-FDCAN RX ordering | Commission: frame forwarded before RX validation | Invalid camera frame forwarded (acceptable for PCS path) | Static block list | C (by design) | Documented (GAP-11) |
| SWF-35 | U-PND-FDCAN bus-off | Omission: car-side bus-off while engaged | No actuation frames; EPS drop-out (SG-02) | counted, core reset (`drivers/fdcan.h:76-83`) | P | SWSR-508 |
| SWF-36 | U-PND-HARN | Wrong value: orientation wrong or lost while relay driven | Commands on wrong bus, PCS cut (SG-07) | detection suspended while driven (`drivers/harness.h:59`) | P | SWSR-701 |
| SWF-37 | U-PND-HARN relay | Stuck: relay stuck intercepting | PCS cut when item inactive (SG-07) | none | N | SWSR-506, 506b (GAP-12) |
| SWF-38 | U-PND-PWR | Commission: power save entered in car mode (`0xe7`) | Camera-side CAN IRQs and transceivers off with relay driven (SG-07) | none | N | SWSR-513; WP-A-02 FFI-CM-08 |
| SWF-39 | U-PND-HK siren | Omission: siren not sounding when SoC lost | No warning (SG-02, SG-06) | malfunction reported only (`drivers/fake_siren.h`) | P | SWSR-516, 515 |
| SWF-40 | U-PND-BOOT | Commission: non-release image executed | Unverified envelope (all) | RSA-1024/SHA-1; debug key in debug builds | P | SWSR-511, 514 (GAP-24, GAP-25) |
| SWF-41 | U-PND-PLAT clock | Wrong value: clock drift → timers wrong | Timeouts and RT windows wrong (SG-01) | CSS on HSE loss only | P | SWSR-504 |
| SWF-42 | U-PND-PLAT memory | Wrong value: RAM bit flip in `controls_allowed`, limits, mode | Authority/limit wrong (all) | none | N | SWSR-503b, 507; WP-A-04 SFMEA-23 |

### 3.3 Host components (summary, QM)

Host failure modes are analysed at system level in [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md) SFMEA-01…11. The software-level conclusions:

| ID | Component | Failure mode | Envelope backstop | Host requirement |
|---|---|---|---|---|
| SWF-43 | `host.controlsd` | Stale input used for actuation | SWSR-408 (only for stop of frames, not stale content) | SWSR-602, 601 |
| SWF-44 | `host.selfdrived` | Diagnostics masked (big-model path) | Envelope limits only | SWSR-603 (GAP-17) |
| SWF-45 | `host.controlsd` | Non-finite output replaced by 0 | none needed (0 is in bounds) | SWSR-604 |
| SWF-46 | `host.pandad` | Wrong mode/param sent | SWSR-512 | — |
| SWF-47 | `host.pandad` | `sendcan` delayed up to 1 s | SWSR-411 | SWSR-414h |

### 3.4 Coverage summary

| Rating | Count (SWF-01…42) |
|---|---|
| C | 3 |
| P | 16 |
| N | 23 |

Every N and P row has an SWSR in WP-W-02. Diagnostic-coverage targets in WP-S-03 §6 cannot be claimed until those SWSRs are implemented and verified.

## 4. Software-level dependent failure analysis

### 4.1 Shared resources

| ID | Coupling factor | Elements involved | Dependent failure | Measure today | Required |
|---|---|---|---|---|---|
| SDF-01 | Shared address space (no MPU) | comms handlers, USB/SPI drivers, envelope state | A defect in QM-like code (housekeeping, comms) corrupts `controls_allowed`, limits, mode, `relay_malfunction` | none | SWSR-507; WP-A-02 FFI-SP-01 |
| SDF-02 | Shared execution time: all ISRs at one priority (§5.1 of WP-W-03) | CAN RX, SPI, USB, tick | Interrupt storm or long handler delays the tick → supervision late or absent | interrupt-rate fault, report-only | SWSR-401a, 501, 502b, 519 (GAP-50); WP-A-02 FFI-TM-01 |
| SDF-03 | Busy-waits reachable from SoC commands (`while (harness.sbu_adc_lock)`, SPI drain loop) | `set_intercept_relay` via `0xdc`/`0xc5`; `llspi_mosi_dma` | A stuck flag hangs the SPI ISR and with it all processing | equal priority prevents the tick from holding the lock while SPI runs | Argue by priority scheme (WP-W-03 OI-4); bounded waits; SWSR-501 |
| SDF-04 | Shared ring buffers (`can_rx_q`, `can_queues[]`) | TX path, forwarding, rejected-frame echo, SoC read | SoC not reading → `rx_q` full → only reporting lost; forwarding TX queue full → PCS frames dropped | overflow counters | SWSR-707; queue overflow → fault |
| SDF-05 | Shared TX queue for forwarded and SoC frames on bus 0 | forwarding (camera→car) and SoC actuation on the same queue `can_queues[0]` | SoC flood (in-limit frames) delays forwarded PCS frames | whitelist and per-frame limits; no rate limit | SWSR-518 (per-ID TX rate); separate forwarding queue (OI-2) |
| SDF-06 | Shared global time base (TIM2 µs counter) | RT window, steer-request interval, RX timeouts, ISR load | One timer fault breaks all timing checks in the same way | none | SWSR-504 cross-check |
| SDF-07 | Shared `set_safety_mode` path | mode change, heartbeat loss, harness re-init (`main.c:138`) | Re-init by harness flicker resets authority and limiter state, and (today) the relay latch | authority reset is safe direction | SWSR-506a |

### 4.2 Shared information and common-mode between controller and envelope

| ID | Coupling factor | Description | Effect | Measure |
|---|---|---|---|---|
| SDF-08 | Same limit values | Host `CarControllerParams` equal to envelope constants (1500, 15/25, 350, 2.0/−3.5) (`values.py:20, 39-47`; `modes/toyota.h:172-210`) | Controller operates at the envelope boundary; a common wrong value (copied) is not caught by either | SWSR-605, 605a; independent derivation of envelope values (SWSR-102, WP-S-02 OI-3) |
| SDF-09 | Same specification source | Envelope tests copy constants from `toyota.h` (`test_toyota.py:139-155`) | A wrong limit passes its own test (GAP-14) | W-09 DVR-04; tests from requirement data |
| SDF-10 | Same signal decoding | Host DBC and envelope hard-coded bit positions decode the same frames | Common misinterpretation of a signal | Diverse decoding (DBC vs hand-coded) is a weak benefit; `test_panda_safety_carstate` on fork-owned routes (W-09 DVR-11) |
| SDF-11 | Same input source for engagement | Driver, host and envelope all follow PCM cruise state | Corrupted `0x1D2` affects all three | SWSR-405(c) cross-check with `0x1D3` |
| SDF-12 | Same configuration source | Safety mode/param chosen by host fingerprint and confirmed by the host itself | Wrong configuration undetected | SWSR-512 (compiled-in configuration) |
| SDF-13 | Same development team / upstream | Envelope and controller written and reviewed by the same upstream contributors | Common misconception of limits | I2 review of envelope values; external assessor (T-09) |
| SDF-14 | Same compiler | Envelope and platform built by one toolchain | Compiler defect affects all checks | TCL3 tool (WP-P-07 TL-01); back-to-back host/target (VS-UV-20) |

### 4.3 Independence claims affected

| Claim ([WP-S-03 §7](../03-system/WP-S-03-technical-safety-concept-architecture.md)) | Software-level verdict |
|---|---|
| FFI-1 (wrong commands) | Holds for per-frame limits; not for omission of safe state (SWF-04) or stale repetition (SWF-26) |
| FFI-2 (reconfiguration) | Does not hold (SWF-16, 24) |
| FFI-4 (memory corruption via SPI) | Does not hold (SWF-22, 23, SDF-01) |
| FFI-5 (SoC timing) | Partly (SWF-25, 28) |
| FFI-6 (ISR starvation) | Does not hold (SWF-29, SDF-02) |

## 5. Results feeding other work products

| To | Content |
|---|---|
| [WP-W-02](WP-W-02-software-safety-requirements.md) | All gaps above map to existing SWSRs; new items: queue overflow → fault (under SWSR-502b/707); per-ID TX rate limit now SWSR-518 |
| [WP-W-03](WP-W-03-software-architecture.md) | Priority scheme (OI-4), removal of unused modes and USB |
| [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md), [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md) | SDF-01…14 |
| [WP-S-03 §6](../03-system/WP-S-03-technical-safety-concept-architecture.md) | DC targets remain unconfirmed (WP-S-03 OI-1) |
| [WP-W-07](WP-W-07-software-integration-verification.md), [WP-W-08](WP-W-08-embedded-software-testing.md) | Fault-injection cases derived from SWF rows |

## 6. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm the effect of the SPI DMA overrun (SWF-22) from the map file and the STM32H7 reference manual (memory beyond SRAM2) | SW lead | G3 |
| OI-2 | Decide whether a separate forwarding queue is needed in addition to SWSR-518 (SDF-05) | Safety engineer | G3 |
| OI-3 | Repeat this analysis after the SWSRs are implemented (new failure modes of new mechanisms, e.g. autonomous zero-torque frames) | Safety engineer | G4 |
| OI-4 | Independent (I2) review of this analysis | Safety manager | G3 |
| OI-5 | Align SWF IDs with WP-A-04 SFMEA rows in the trace data | Safety engineer | G3 |
