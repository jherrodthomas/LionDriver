# WP-A-03 Dependent Failure Analysis

| Field | Value |
|---|---|
| Work product | WP-A-03 Dependent failure analysis (DFA), system level |
| Standard reference | ISO 26262-9:2018 §7 (analysis of dependent failures); ISO 26262-9 §5 (independence for decomposition, by reference); ISO 26262-5:2018 §7 (hardware DFA input); ISO 26262-6:2018 §7 (software-level DFA input, detailed in [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md)) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SG-01 (ASIL C ⚠) and SG-02…SG-07 (ASIL B). Elements: E-03 envelope, E-01/E-02 SoC stack, E-04 device hardware, E-05 harness, EXT-EPS, EXT-PCM, EXT-CLU, driver |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); input to G2 confirmation review |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

The LionDriver safety concept rests on several independence claims: the envelope catches SoC faults; the EPS bounds what passes the envelope; the driver controls what the EPS lets through; the stock PCS is not affected by the item. A dependent failure (common cause or cascading) that defeats both sides of such a claim is a single point of failure in disguise. This DFA identifies dependent failure initiators (DFIs), the coupling factors that let them reach more than one element, evaluates whether they are sufficiently controlled, and states the required measures.

The software-internal DFA of the panda firmware (shared memory, shared execution time) is in [WP-A-02](WP-A-02-coexistence-freedom-from-interference.md) (interference) and [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md). Hardware-level DFA of the STM32H7 (on-die common cause) belongs to [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md). This document is the system-level view and links the three.

## 2. Independence and freedom-from-common-cause claims examined

| ID | Claim | Who relies on it | Elements that must not fail together |
|---|---|---|---|
| IC-01 | A fault in the SoC command path is detected or bounded by the envelope | WP-C-04 §4.2 (envelope-only ASIL allocation); all SG | E-01/E-02 (command generator) vs E-03 (limiter/monitor) |
| IC-02 | The EPS limits LKA torque and times out independently of the item | HARA C2 ratings HE-01.x, HE-05.2 (AOU-01R); FSR-01.13 | E-03 vs EXT-EPS |
| IC-03 | The driver can control envelope-bounded worst-case actuation | All C ratings; option (c) strategy | E-03 + EXT-EPS vs driver (AOU-02R, AOU-06R) |
| IC-04 | The vehicle's cruise indicator shows engagement independently of the item HMI | FSR-05.05, AOU-12 | E-01 HMI vs EXT-CLU |
| IC-05 | The stock PCS keeps working with the item installed, engaged or not | SG-07, AOU-04R | E-03/E-05 vs stock camera/radar/PCM |
| IC-06 | The panda buzzer warns on SoC loss independently of the SoC HMI | FSR-02.05, SG-02/SG-06 | E-01 HMI (ui/soundd) vs E-03 siren path |
| IC-07 | (Fallback only) E-07 independent actuation monitor vs E-03 | [WP-A-01](WP-A-01-asil-decomposition.md) DEC-01 | E-03 vs E-07 |

## 3. Method

1. List DFIs by the categories that ISO 26262-9 §7 asks to consider: random hardware failures of shared resources, development (systematic) faults, manufacturing and installation faults, service faults, environmental conditions, failures of common external resources, and stress from use.
2. For each DFI, name the coupling factor(s): **shared resource** (power, clock, PCB, connector, memory), **shared information input** (same CAN signal, same configuration data), **systematic coupling** (same requirements, constants, people, tools, upstream source), **physical/environmental proximity** (thermal, vibration, EMC), **communication/control coupling** (one element configures, resets or reflashes the other).
3. Evaluate per claim IC-xx: *controlled* (a measure prevents the coupling or detects its effect in time), *partly controlled*, or *not controlled*.
4. State the required measure and its TSR block. Where WP-S-02 numbers were already in use in [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md), they are cited; otherwise the block (OI-1).

Rating legend for evaluation: **C** controlled, **P** partly controlled, **N** not controlled, **n/a** coupling does not reach both elements.

## 4. Dependent failure initiators

### 4.1 Shared resources (random hardware and external resources)

| ID | Initiator | Coupling factor | Elements reached | Effect | Existing measures (code / design) | Eval | Required measure |
|---|---|---|---|---|---|---|---|
| DFI-01 | **Shared power**: 12 V harness supply (IF-08), device input stage and regulators feed both SoC and MCU. Brown-out, dips at engine crank, regulator fault, connector intermittency | Shared resource | E-01, E-03, E-05 relay coil (IC-01, IC-05, IC-06) | SoC misbehaves (corrupted commands) while MCU also runs out of spec, so the monitor is unreliable when needed; MCU and SoC reset together; relay drops out (stock path) | Input voltage measured and reported only (`panda/board/boards/cuatro.h:28-30`, HWSR-505b); `PVD_AVD_IRQHandler` is a stub, PVD not enabled (`stm32h7/interrupt_handlers.h:7`); BOR level not set in code; NMI/HardFault → reset (`early_init.h:73-80`); relay released on MCU reset expected (HWSR-502, unconfirmed) | **P** | Brown-out reset level and PVD → safe state (TSR-505); relay de-energise-to-safe on supply loss (TSR-506, AOU-13); HIL power-dip tests (WP-V-05 VS-FI-15) |
| DFI-02 | **Clock**: MCU uses HSE 25 MHz → PLL (`panda/board/stm32h7/clock.h:4-6, 78-89`). Whether HSE is shared with the SoC is unknown (schematic) | Shared resource (if shared); timing reference for all MCU timeouts | E-03 (IC-01) | Slow clock lengthens every timeout (RX, heartbeat) and rate window; fast clock shortens them (availability) | Clock security system on HSE enabled (`clock.h:118-119`), CSS → NMI → reset (HWSR-504); interrupt-rate checks report-only (`drivers/interrupts.h:33-35`) | **P** | Clock-frequency cross-check against an independent oscillator (LSI/HSI) (TSR-504, HWSR-504a); confirm HSE not shared with SoC |
| DFI-03 | **Shared PCB and enclosure**: SoC and MCU on one board in one housing on the windscreen | Physical proximity | E-01, E-03, E-04 | Mechanical damage, cracked solder, moisture affect both | COTS product; no supplier evidence (WP-M-01 §9) | **N** | Hardware qualification and environmental tests ([WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md)); latent-fault start-up tests |
| DFI-04 | **Thermal**: SoC heat in a sun-loaded windscreen enclosure raises MCU temperature | Physical proximity | E-01, E-03 | Both elements out of temperature range together; SoC throttles (late commands) while MCU drifts | Host thermal policy uses SoC sensors only (`openpilot/system/hardware/hardwared.py:320-329`); host faults on `overheat` and fan < 500 rpm for > 15 s (onboard review, `selfdrive/selfdrived/selfdrived.py:259, 268-271`); MCU DTS read and reported, no firmware reaction (`stm32h7/lldts.h`) | **P** | MCU DTS out-of-range → safe state (TSR-509); thermal qualification of the device in the reference vehicle (WP-H-07) |
| DFI-05 | **Harness connector and relay**: one harness carries bus 0, bus 2, 12 V, ignition and relay coil | Shared resource | E-03 actuation, E-05 relay, stock camera→car path (IC-05) | Connector fault can cut the stock PCS path **and** the item's ability to detect it; welded relay keeps intercepting with no detection; open coil releases relay (safe) | Harness orientation detection (`drivers/harness.h:54-90`); relay malfunction by traffic (camera control messages on car side), 1–2 s grace (`opendbc_repo/opendbc/safety/safety.h:215-220, 372-380`); no contact readback (GAP-12) | **P** | Relay state readback (TSR-506, HWSR-506a); de-energised = stock path confirmed (AOU-13, TSR-702); connector keying/latching (TSR-703) |
| DFI-06 | **Vehicle 12 V low-voltage event** (cranking, alternator fault) affects the EPS, PCM and the device together | Common external resource | EXT-EPS, EXT-PCM, E-03 (IC-02, IC-05) | EPS reduces or drops assist and the item loses power simultaneously; loss of lateral control without an item warning | Out of item control. EPS own diagnostics (assumed) | **P** | AoU on EPS behaviour at low voltage (extend AOU-01R); item warning on supply out-of-range while engaged (TSR-505, TSR-6xx) |
| DFI-07 | **EMC / ESD transient on the CAN harness** | Physical proximity | E-03 RX path and SoC (via panda) | Burst of corrupted frames on all buses; frame drops | CAN CRC in the controller; bus-off recovery (`drivers/fdcan.h:76-84`); error counters to health | **P** | EMC qualification (WP-H-07); bus-off → safe state and warning (TSR-508, HWSR-508b) |

### 4.2 Shared information and configuration

| ID | Initiator | Coupling factor | Elements reached | Effect | Existing measures | Eval | Required measure |
|---|---|---|---|---|---|---|---|
| DFI-08 | **Identical constants in controller and envelope.** Controller limits equal envelope limits: `STEER_MAX = 1500`, `STEER_ERROR_MAX = 350`, delta up/down 15/25 (`opendbc_repo/opendbc/car/toyota/values.py:20-21, 44-47`) vs envelope 1500/350/15/25 (`opendbc_repo/opendbc/safety/modes/toyota.h:173-177`); accel −3.5/+2.0 (`values.py:39-43`, `opendbc_repo/opendbc/car/interfaces.py:25-26`) vs `toyota.h:207-210`. Same upstream authors, no derivation record (GAP-04) | Systematic coupling (same source of the values) | E-01 controller and E-03 envelope (IC-01, IC-03) | (1) An unsafe limit value is wrong in both places, so the envelope never trips and the error is invisible. (2) Zero margin: normal operation runs at the enforcement boundary, so envelope interventions cannot be used as a fault indicator | Tests check the envelope against values copied in the tests (`opendbc_repo/opendbc/safety/tests/test_toyota.py:139-155`), not against a requirement (GAP-14) | **N** | Derive envelope limits from controllability evidence in a separate, reviewed record (WP-C-04 §4.2; TSR-1xx/2xx); controller limits set with margin below envelope (FSR-01.14); tests reference requirement IDs, not code constants (WP-W-06) |
| DFI-09 | **Shared configuration data `CarParams`.** Fingerprinting on the SoC selects the platform; the same `CarParams` sets controller tuning and, through `safetyConfigs`, the envelope mode and `safetyParam` (EPS scale 73) sent by pandad (`openpilot/selfdrive/pandad/panda_safety.cc:56-70`). Stored in the unauthenticated params store | Shared information input; control coupling | E-01 and E-03 (IC-01) | Wrong fingerprint or tampered `CarParams` gives a wrong controller **and** a wrong envelope configuration (e.g. wrong EPS scale changes the measured-torque check, `toyota.h:104`), so the monitor shares the controller's error | Host compares panda-reported mode/param with `CarParams` after 10 s (onboard review, `selfdrived.py:330-339`) — same source, so not independent | **N** | Fixed safety mode and param in envelope firmware for the reference configuration (FSR-01.10; TSR-5xx safety-mode lock); envelope rejects any other value (WP-A-02 FFI-CM-06) |
| DFI-10 | **Shared sensor inputs.** Envelope and controller both use the same CAN signals: driver/EPS torque `0x260`, cruise state `0x1D2`, brake `0x226`, speed `0xAA` | Shared information input | E-01, E-03 (IC-01) | A stuck or wrong vehicle signal misleads the controller and the envelope check at the same time (e.g. stuck "cruise active" keeps authority; stuck EPS torque reading shifts the measured-tracking window) | Checksums on `0x260`, `0x1D2`; RX timeouts ≈2 s (`safety.h:321-344`) | **N** for stuck-with-valid-checksum (GAP-01) | Per-signal E2E or plausibility strategy using independent signals (e.g. `0x226` brake vs deceleration, wheel speed vs EPS-reported speed) (TSR-4xx, FSR-01.06) |
| DFI-11 | **EPS-reported motor torque used by the envelope to bound the EPS.** The measured-tracking check (`opendbc_repo/opendbc/safety/lateral.h:10-23`) uses torque reported by the EPS that it is meant to protect against | Shared information input | E-03, EXT-EPS (IC-02) | An EPS fault that misreports torque defeats the envelope's measured-tracking check and the EPS's own limit together | Magnitude limit and rate limit do not depend on the EPS report | **P** | Keep magnitude/rate limits independent of EPS feedback (TSR-1xx); treat measured tracking as diagnostic only; EPS fault-state monitoring in the envelope (FSR-02.01, GAP-03) |
| DFI-12 | **Shared command path to the EPS.** The EPS executes the command the envelope passed | Shared information input | E-03, EXT-EPS (IC-02) | An in-envelope but wrong command (wrong direction within limits) is not limited by the EPS either | Envelope bounds magnitude/rate; EPS bounds magnitude (assumed) | **P** (by design, both limit magnitude only) | Accept as design: controllability of envelope-bounded worst case must be shown (option (c), AOU-02R); no independence credit for EPS (WP-A-01 §5) |

### 4.3 Control coupling (one element can alter the other)

| ID | Initiator | Coupling factor | Elements reached | Effect | Existing measures | Eval | Required measure |
|---|---|---|---|---|---|---|---|
| DFI-13 | **SoC configures, resets and reflashes the MCU**: `0xdc`, `0xc5`, `0xe7`, `0xd1`, `0xd8` (`panda/board/main_comms.h`), boot pins (`openpilot/common/hardware/comma/hardware.py:401-419`), recovery flashes a development bootstub (`openpilot/selfdrive/pandad/pandad.py:34-39`) | Communication/control coupling | E-01 → E-03 (IC-01, IC-05) | A single SoC fault or compromise disables or replaces the monitor of the SoC | See WP-A-02 §6.2 | **N** | WP-A-02 measures (safety-mode lock, command rejection in car modes, RDP/WRP, signature) (TSR-5xx, TSR-511) (GAP-09, GAP-24, GAP-38) |
| DFI-14 | **SoC crash removes actuation and warnings at the same time.** `controlsd`, `selfdrived`, `ui` and `soundd` all run on the SoC (`openpilot/system/manager/process_config.py:89-97`) | Shared resource (SoC) | E-01 actuation and E-01 HMI (IC-06) | Loss of lateral/longitudinal control with no visual/acoustic warning from the SoC | Panda siren on heartbeat loss, 3 s, after 5 s detection (`panda/board/main.c:193-201`) | **P** (timing, GAP-06) | SoC-independent acoustic warning within the SG-02/SG-06 budget (FSR-02.05, TSR-4xx/5xx); EXT-CLU cruise indicator stays as an independent cue (IC-04, AOU-12) |
| DFI-15 | **Item TX can affect the cluster indication**: `0x412` LKAS_HUD is sent by the item; the cruise indicator is assumed PCM-driven | Communication coupling | E-01 vs EXT-CLU (IC-04) | Driver sees an indication generated by the faulty element | AOU-12 (unverified) | **P** | Verify AOU-12 by vehicle test (WP-S-09 VS-SQ-09) |

### 4.4 Systematic (development, tools, people)

| ID | Initiator | Coupling factor | Elements reached | Effect | Existing measures | Eval | Required measure |
|---|---|---|---|---|---|---|---|
| DFI-16 | **Common upstream source and authors** for controller (`opendbc/car/toyota`) and envelope (`opendbc/safety/modes/toyota.h`) in one repository | Systematic coupling | E-01, E-03 (IC-01) | Same misunderstanding of the vehicle (e.g. EPS fault codes, signal semantics) in both | Separate code paths; safety code MISRA-checked, 100 % line coverage, mutation testing (upstream CI only, GAP-13) | **P** | Requirements-based verification of the envelope from TSRs (not from controller behaviour); independent I1/I2 review of envelope changes (T-09) |
| DFI-17 | **Common toolchain** (arm-none-eabi-gcc 13.2.1 comma-packaged, SCons, cppcheck) | Systematic coupling | E-03 code and (for DEC-01) E-07 | Compiler defect affects all firmware | None qualified (GAP-34) | **N** | Tool classification and qualification ([WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md)); target-hardware testing on HIL (GAP-13: tests run on x86 host) |
| DFI-18 | **Same test oracle** for envelope and controller: process replay and safety replay reuse logs recorded with the same stack (`openpilot/selfdrive/test/process_replay/test_processes.py:70`; `opendbc_repo/opendbc/safety/tests/safety_replay/replay_drive.py`) | Systematic coupling | E-01, E-03 | Regression tests confirm consistency with the past, not correctness | — | **P** | Requirements-based tests and fault injection independent of recorded behaviour ([WP-S-08](../03-system/WP-S-08-system-integration-test.md), [WP-V-05](../06-validation/WP-V-05-fault-injection.md)) |
| DFI-19 | **Single maintainer** writes, reviews and approves (T-09) | Systematic coupling (people) | All | Same blind spot in specification, implementation and review | External I1/I3 reviewers planned ([WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md)) | **N** today | External reviewer for all ASIL work products; confirmation review |

### 4.5 Installation, service and use

| ID | Initiator | Coupling factor | Elements reached | Effect | Existing measures | Eval | Required measure |
|---|---|---|---|---|---|---|---|
| DFI-20 | **Mis-installation** (wrong harness variant, partially seated connector, poor mount) | Common installation step | E-04, E-05, stock path (IC-05) | Relay/harness fault plus degraded camera calibration | Harness status detection; `calibrationd` checks (AOU-08) | **P** | Installation checklist and post-install check of the stock PCS path ([WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md)); TSR-8xx |
| DFI-21 | **Driver state and DM share the cause**: fatigue/distraction that degrades controllability is also what DM must detect; glare or sunglasses degrade both driver vision and DM (`docs/LIMITATIONS.md:53-56`) | Shared environment | DRV, E-01/DM (IC-03) | Controllability assumption fails when DM is least effective | DM wheel-touch fallback on high uncertainty (`openpilot/selfdrive/monitoring/policy.py:77-78`) | **P** | Handled under ISO 21448 (WP-C-04 §7, [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)); not credited for ASIL |
| DFI-22 | **Vehicle maintenance changes the EPS or PCM** (reflash, part swap) | Service | EXT-EPS, EXT-PCM (IC-02, IC-05) | AoU evidence becomes invalid without notice | Fingerprint lists include multiple EPS FW versions (`opendbc_repo/opendbc/car/toyota/fingerprints.py`) | **N** | Record ECU FW versions of the reference vehicle (WP-C-01 OI-1); refuse engagement on FW not in the verified list (TSR-8xx) |

## 5. Evaluation per independence claim

| Claim | Not controlled DFIs | Partly controlled DFIs | Verdict (current baseline) | Condition to accept |
|---|---|---|---|---|
| IC-01 envelope vs SoC | DFI-03, -08, -09, -10, -13, -17 | DFI-01, -02, -04, -07, -16, -18 | **Not independent** | WP-A-02 command lock and boot protection; fixed safety config; E2E/plausibility on RX; limits derived independently with margin; PVD/BOR; HIL target tests |
| IC-02 envelope vs EPS | DFI-22 | DFI-06, -11, -12 | **Partly**; EPS is an external measure, not an independent element (no ASIL credit, WP-A-01 §5) | AOU-01R verified for the recorded EPS FW; envelope limits not dependent on EPS feedback |
| IC-03 envelope+EPS vs driver | DFI-08 | DFI-21 | **Open** until controllability tests | Envelope-bounded worst case shown controllable (C1 target) |
| IC-04 cluster indication | — | DFI-15 | **Partly** | AOU-12 verified |
| IC-05 stock PCS | — | DFI-01, -05, -06, -20 plus WP-A-02 FFI-CM-05/08 | **Partly** | AOU-04R/AOU-13 verified; relay readback; reject `0xe7` in car modes; whitelist fix |
| IC-06 buzzer vs SoC HMI | — | DFI-14 | **Partly** (timing) | FSR-02.05 timing met |
| IC-07 (fallback E-07) | n/a | n/a | Not applicable unless DEC-01 activated | WP-A-01 IR-01…IR-10 |

## 6. Required measures (summary)

| Measure | DFIs | TSR reference |
|---|---|---|
| BOR level, PVD → safe state; supply out-of-range warning | DFI-01, -06 | TSR-505 |
| Relay de-energise-to-safe, contact readback, connector keying | DFI-01, -05 | TSR-506, TSR-702, TSR-703 |
| Clock cross-check | DFI-02 | TSR-504 |
| MCU temperature reaction | DFI-04 | TSR-509 |
| Bus-off / error-passive → safe state | DFI-07 | TSR-508 |
| Independent limit derivation, margin, requirement-based tests | DFI-08, -16, -18 | TSR-1xx, TSR-2xx |
| Safety mode/param fixed in firmware | DFI-09, -13 | TSR-5xx (safety-mode lock) |
| E2E / plausibility on gating signals | DFI-10 | TSR-4xx |
| Magnitude/rate limits independent of EPS feedback; EPS status monitoring | DFI-11 | TSR-1xx |
| Command lock, boot protection, signature | DFI-13 | TSR-5xx, TSR-511 |
| SoC-independent warning timing | DFI-14 | TSR-4xx/5xx |
| Tool qualification; HIL target tests | DFI-17 | — (WP-P-07, WP-S-08) |
| External independent review | DFI-19 | — (WP-M-06) |
| Installation check, ECU FW allow-list | DFI-20, -22 | TSR-8xx |

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Align TSR references with WP-S-02 when published | Safety engineer | G2 |
| OI-2 | Obtain or reverse-engineer the device power and clock tree (schematic) to close DFI-01/DFI-02 evaluation | HW lead | G2 |
| OI-3 | Maintainer decision on separating the derivation of envelope limits from controller tuning (DFI-08) | Maintainer | G2 |
| OI-4 | Characterise EPS behaviour at low supply voltage and with misreported torque (DFI-06, DFI-11) as part of AOU-01R tests | Safety engineer | G2 |
| OI-5 | Repeat this DFA for IC-07 if DEC-01 is activated | Safety engineer | G2 (conditional) |
| OI-6 | Hand the on-die STM32H7 common-cause items (shared RAM, flash, clock tree, supply domain) to WP-H-03 | HW lead | G3 |
