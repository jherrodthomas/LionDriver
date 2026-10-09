# WP-S-08 System Integration and Test

| Field | Value |
|---|---|
| Work product | WP-S-08 System integration and test strategy, specification and report |
| Standard reference | ISO 26262-4:2018 §7 (item integration and testing); ISO 26262-4 §7 test methods and fault-injection guidance (verify table numbers against the licensed copy); ISO 26262-8:2018 §9 (verification); ASPICE 4.0 SYS.4 (system integration and integration verification) |
| Version | 0.1 |
| Status | Draft (specification). **Results: not yet executed** |
| ASIL / scope | ASIL C (SG-01 until re-rated), ASIL B (SG-02…SG-07); reference configuration only |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); test specification review with independence per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document specifies how the LionDriver elements are integrated into the item and how the integrated item is verified against the technical safety requirements and the system interfaces, as ISO 26262-4 §7 and ASPICE SYS.4 require. It covers:

- the integration strategy and sequence (§3),
- the integration environment, which is the **LionDriver HIL bench** that decision D-04 ([WP-M-01 §8](../01-management/WP-M-01-assurance-strategy.md#8-strategic-decisions-required)) requires and that [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) §2 defines (§4),
- the test specification VS-SI-01…VS-SI-26, traced to TSRs and interfaces (§6),
- the report template (§8), with every result **"Not yet executed"**.

Out of scope: hardware integration of the device (WP-H-06, VS-HW-nn), software integration ([WP-W-07](../05-software/WP-W-07-software-integration-verification.md)), embedded software qualification ([WP-W-08](../05-software/WP-W-08-embedded-software-testing.md)), system qualification on the vehicle ([WP-S-09](WP-S-09-system-verification.md)), and the systematic fault-injection campaign, which is specified in [WP-V-05](../06-validation/WP-V-05-fault-injection.md). Test cases here that inject faults reference the WP-V-05 case for the detailed procedure.

**TSR references.** [WP-S-02](WP-S-02-technical-safety-requirements.md) is being written in parallel. Each test traces to the FSR it verifies and to the TSR block (TSR-1xx…8xx); TSR numbers already in use in [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md) are cited. Exact TSR IDs are filled in when WP-S-02 is published (OI-1).

## 2. Current verification capability (baseline)

| Asset | What it does | Usable for LionDriver evidence today? |
|---|---|---|
| opendbc safety tests (`opendbc_repo/opendbc/safety/tests/test_toyota.py`, `common.py`) | Host-built (x86) unit/integration tests of the safety modes, 100 % line coverage gate (`tests/test.sh:36-43`), mutation tests (`tests/mutation.py`) | Only once run in fork CI (D-03). Not on target (GAP-13) |
| opendbc safety replay (`opendbc_repo/opendbc/safety/tests/safety_replay/replay_drive.py`) | Replays drive logs through the safety model | Needs fork-owned Corolla logs |
| panda HITL tests (`panda/tests/hitl/test_1_program.py` … `test_9_harness.py`) | Flashing, health/heartbeat (`test_2_health.py:38`), CAN loopback, SPI protocol incl. bad header/checksum (`test_5_spi.py:58-72`), NO_OUTPUT safety (`test_6_safety.py:8`), harness orientation | Run on comma's farm only; no LionDriver bench (GAP-30) |
| pandad device tests (`openpilot/selfdrive/pandad/tests/test_pandad_spi.py`) | SPI corruption injection via `SPI_ERR_PROB` (`openpilot/selfdrive/pandad/spi.cc:280-301`) | Device-only; Jenkins stages (`Jenkinsfile:303-307`) use comma device pools |
| Process replay (`openpilot/selfdrive/test/process_replay/test_processes.py`) | Regression of controlsd, plannerd, radard, … against reference logs fetched from comma storage (`test_processes.py:70`) | Needs fork-owned references (D-03) |
| Process fuzzing (`openpilot/selfdrive/test/process_replay/test_fuzzy.py`) | Random message fuzzing with Corolla fingerprint; **excludes** selfdrived, controlsd, card, plannerd, dmonitoringd (`test_fuzzy.py:12`) | Partial: the safety-relevant processes are excluded |
| On-road device tests (`openpilot/selfdrive/test/test_onroad.py`) | Timing, CPU, service frequencies | comma device pools only (`Jenkinsfile:262-265`) |
| Simulator (`openpilot/tools/sim`, MetaDrive bridge) | Closed-loop driving; simulates a **Honda** and publishes `can`/`pandaStates` directly, bypassing the panda (`tools/sim/lib/simulated_car.py:12-20`); CI job disabled (`.github/workflows/tests.yaml:185`) | Only for QM SoC behaviour; does not exercise the Toyota envelope |

Conclusion: **no system integration evidence exists under LionDriver control.** This specification assumes the HIL bench of D-04 is built.

## 3. Integration strategy

### 3.1 Approach

Bottom-up integration in four steps. Each step adds one element or interface, and each step's tests must pass before the next starts. Safety-related interfaces are verified at the earliest step where they exist.

| Step | Integrated elements | Interfaces exercised | Stimulus | Purpose |
|---|---|---|---|---|
| I-1 | E-03 panda firmware (release build) on the reference device MCU, SoC running a **test host** (`panda` Python library) instead of openpilot | IF-01, IF-02, IF-03 (via bench CAN), IF-04 (SPI, scripted), relay (E-05) | Scripted CAN frames and Corolla log replay on bus 0/2; scripted host commands | Envelope behaviour on target hardware, independent of the QM stack |
| I-2 | I-1 + full openpilot on the SoC (pandad, card, controlsd, selfdrived, ui/soundd), camera inputs from recorded video or covered (no model credit) | IF-04 real traffic, IF-07 HMI | Open-loop Corolla log replay on the CAN side; process faults injected on the SoC | SoC ↔ envelope integration, fault reactions, warnings, heartbeat |
| I-3 | I-2 in closed loop with a vehicle model (Corolla lateral/longitudinal plant on the bench PC, producing `0x260`, `0xAA`, `0x1D2`, `0x226` responses to `0x2E4`/`0x343`) | Closed control loop through the panda | Scenario scripts | Dynamic behaviour at limits; FTTI-relevant timing with plant response |
| I-4 | Device + harness installed in the reference vehicle, **stationary** (engine on, wheels on ground or lifted per [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md)) | All IF incl. real EPS/PCM/camera | Engagement attempts, stalk/brake/gas inputs, relay checks, PCS message capture | Integration with existing vehicle elements before driving; hand-over to WP-S-09 |

Element entry criteria for each step: element versions recorded as configuration items ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)); unit/software integration results available for the version under test (WP-W-07); open problem reports reviewed ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)).

### 3.2 Test methods

| Method | Use in this document |
|---|---|
| Requirements-based test | Every VS-SI case traces to an FSR and TSR block; pass criteria derive from the requirement, not from current behaviour |
| Interface test | VS-SI-05…-11 (IF-04 commands and data), VS-SI-20…-21 (IF-03 forwarding, IF-01 whitelist) |
| Fault injection | VS-SI-09…-13, -17, -19, -22, -23, -25; detailed procedures in WP-V-05 (VS-FI-nn) |
| Back-to-back | VS-SI-26 (a) target MCU vs host-built libsafety on the same frame sequence, (b) process replay against fork-owned references |
| Resource / timing test | VS-SI-02, -05, -06, -12, -19, -22, -23 measure detection and reaction times against the FSC §8 budget |
| Analysis of equivalence classes and boundary values | Limit tests VS-SI-15…-17 at, just below and just above each limit |

### 3.3 Timing references

Pass criteria use the preliminary FTTI allocation of [WP-C-04 §8](../02-concept/WP-C-04-functional-safety-concept.md#8-ftti-allocation-preliminary) until [WP-S-04](WP-S-04-timing-ftti-budget.md) is approved. Where the baseline is known not to meet the target, the expected baseline result is stated so that a "fail" is recognised as a known GAP, not a test fault.

## 4. Test environment

| Item | Specification |
|---|---|
| Bench | LionDriver HIL bench per [WP-H-06 §2](../04-hardware/WP-H-06-hardware-integration-verification.md#2-test-environment-hil-bench-decision-d-04): reference comma device, Toyota TSS2 harness with instrumented relay box, 3-channel CAN interface (panda jungle or equivalent), programmable supply, oscilloscope/logic analyser |
| CAN data | Fork-owned Corolla TSS2 drive logs (reference vehicle, WP-C-01 OI-1), decoded with `toyota_nodsu_pt_generated` DBC; scripted frame generators for fault cases |
| Plant model (I-3) | Bench-PC Corolla model: EPS torque response with assumed LKA authority and timeout (AOU-01R values once measured), longitudinal response with PCM ACC bound (AOU-05R) |
| Firmware | Release build of the LionDriver panda fork; fault-injection build only where stated (configuration item, differences documented) |
| Host software | Tagged LionDriver release; for I-1 the `panda` Python library at the same commit |
| Measurement | Time stamps from the CAN interface hardware clock; relay contact probe; audio capture for siren/alerts; SoC logs (`rlog`) |
| Tool classification | Bench scripts, plant model and CAN interface classified per [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) |
| Records | Raw logs, scripts, firmware and software hashes archived per [WP-P-04](../07-supporting/WP-P-04-documentation-management.md) |

## 5. Pass/fail and regression rules

- A test passes only if every pass criterion is met and no actuation frame outside the envelope limits appears on bus 0 at any time during the test (global criterion GC-1), and the camera-side PCS frames are forwarded unchanged whenever the item is not intercepting them by design (GC-2).
- A known-GAP result is recorded as **Fail (known GAP-nn)** and linked to the problem report; it is not waived.
- Any change to a safety-relevant file (WP-P-01 list) re-runs the affected VS-SI cases per the impact analysis ([WP-P-02](../07-supporting/WP-P-02-change-management.md)).

## 6. Test specification

Columns: **Trace** = FSR / TSR block / interface; **Step** = integration step; **Expected baseline** = what the code at `8b8c6ae` is expected to do (from code reading), where it differs from the pass criterion.

### 6.1 Engagement, disengagement, override (TSR-3xx)

| ID | Title | Trace | Step | Preconditions | Procedure | Pass criteria | Expected baseline |
|---|---|---|---|---|---|---|---|
| VS-SI-01 | Engagement only on PCM cruise rising edge | FSR-01.05; TSR-3xx; IF-02 | I-1, I-2, I-4 | Toyota mode, param 73 | (1) Command torque/accel with cruise inactive. (2) Toggle `0x1D2` CRUISE_ACTIVE 0→1. (3) Hold 1 without an edge after mode set. (4) Engage via stalk in vehicle (I-4) | (1) all non-zero frames blocked; (2) authority granted on the edge only; (3) no authority; (4) envelope state equals PCM state and cluster indicator | Meets (`opendbc_repo/opendbc/safety/safety.h:518-527`) |
| VS-SI-02 | Disengagement on brake and cancel | FSR-05.01, FSR-05.02; TSR-3xx; IF-02 | I-1, I-3, I-4 | Engaged | (1) Brake rising edge at speed and at standstill. (2) Brake held while moving. (3) Cruise inactive (cancel, main off) | Authority revoked; next actuation frame zero/inactive; time from triggering frame to first blocked frame ≤ 1 frame (10 ms) + one brake message period; total ≤ 0.2 s (SG-05) | Meets for (1)–(3) logic (`safety.h:354-356, 520-521`); timing to be measured |
| VS-SI-03 | Driver steering override | FSR-05.03; TSR-3xx | I-1, I-3 | Engaged, torque commanded | Raise driver torque in `0x260` above threshold against commanded direction | Envelope reduces torque so it does not oppose the driver within ≤ 0.2 s | **Fail (known GAP-02)**: no driver-torque check in envelope; host-only (`opendbc_repo/opendbc/car/toyota/carcontroller.py:33, 83`) |
| VS-SI-04 | Gas override and restricted host commands in car mode | FSR-04.04, FSR-05.04; TSR-2xx, TSR-3xx; IF-04 | I-1 | Engaged | (1) Gas pressed (`GAS_RELEASED`=0): command positive and negative accel. (2) In car mode send `0xdf` (alternative experience) and `0xf8` (disable heartbeat) | (1) only inactive accel passes while gas pressed, lateral unaffected; (2) both ignored | Meets (`opendbc_repo/opendbc/safety/longitudinal.h:3-12`; `panda/board/main_comms.h:242-247, 291-295`) |

### 6.2 SoC ↔ panda interface (TSR-4xx, TSR-5xx)

| ID | Title | Trace | Step | Preconditions | Procedure | Pass criteria | Expected baseline |
|---|---|---|---|---|---|---|---|
| VS-SI-05 | Heartbeat loss | FSR-01.07, FSR-02.05; TSR-4xx; IF-04 | I-1, I-2 | Engaged, ignition on | Stop heartbeat (`0xf3`) and all SPI traffic | Actuation removed within ≤ 0.3 s detection + ≤ 0.1 s reaction; relay released (SS-S); siren within the SG-02 warning budget (≤ 1 s) | **Fail (known GAP-06)**: SILENT after 5 s, siren 3 s (`panda/board/main.c:101-103, 193-213`) |
| VS-SI-06 | Heartbeat engaged mismatch | FSR-01.07; TSR-4xx | I-1 | Engaged | Send heartbeat with `engaged=0` | Authority revoked within the FTTI budget | **Fail (known GAP-06)**: 3 ticks at 1 Hz (`main.c:182-189`) |
| VS-SI-07 | Safety mode / param set in car mode | FSR-01.10; TSR-5xx (safety-mode lock); IF-04 | I-1 | Toyota mode, engaged | Send `0xdc` with (a) another car mode, (b) Toyota with another param, (c) SILENT, (d) NO_OUTPUT | (a),(b) rejected, mode unchanged; (c),(d) accepted, relay released, authority cleared | **Fail (known GAP-09)**: any mode accepted (`main_comms.h:223-225`); authority is cleared on change (`safety.h:458`) |
| VS-SI-08 | Configuration commands in car mode | FFI-CM-07…-10 ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)); TSR-5xx, TSR-506; IF-04 | I-1 | Toyota mode, engaged, camera traffic on bus 2 | Send each of `0xc5`, `0xe7`(1), `0xe5`(1), `0xde`, `0xdb`, `0xe8`, `0xf1`, `0xd1`(1), `0xd8` | Each rejected, or the item enters SS-S with siren; never a state with relay energised and forwarding stopped; never a relay state change outside SS-S | **Fail expected** (all accepted; WP-A-02 §6.2). `0xe7` expected to stop camera-side forwarding with relay energised (new finding) |
| VS-SI-09 | SPI corruption | FSR-01.08; TSR-4xx; IF-04 | I-2 | Engaged, CAN replay | Enable `SPI_ERR_PROB` (e.g. 0.001 and 0.01) in pandad (`openpilot/selfdrive/pandad/spi.cc:280-301`); also scripted bad header/checksum (`panda/tests/hitl/test_5_spi.py:58-72`); detailed in WP-V-05 VS-FI-06 | No corrupted frame on bus 0 (GC-1); corrupted control commands rejected; error counters increase; sustained corruption → safe state within budget | Frames: GC-1 expected to hold (TX hook); 8-bit XOR residual error not quantified (GAP-10) |
| VS-SI-10 | Stale / replayed command stream | FSR-01.07, FSR-01.08; TSR-4xx | I-1 | Engaged | Replay a captured command buffer repeatedly with valid checksums; freeze command value | Detected as stale within ≤ 0.3 s; SS-L/SS-G | **Fail (known GAP-10)**: no sequence counter |
| VS-SI-11 | TX flooding (babbling SoC) | FSR-01.08; TSR-4xx | I-1 | Engaged | Flood `0x2E4`/`0x343` at 10× nominal and send non-whitelisted IDs (reuse logic of `common.py:937` `test_spam_can_buses`) | Non-whitelisted IDs never on bus 0; actuation message rate on bus 0 within spec; tick timing unaffected (siren/heartbeat timing unchanged); interrupt-rate fault → safe state | Whitelist meets; rate supervision and fault reaction absent (GAP-08) |

### 6.3 Vehicle CAN RX integrity (TSR-4xx)

| ID | Title | Trace | Step | Preconditions | Procedure | Pass criteria | Expected baseline |
|---|---|---|---|---|---|---|---|
| VS-SI-12 | RX timeout per gating signal | FSR-01.06; TSR-4xx; IF-02 | I-1, I-3 | Engaged | Stop, one at a time: `0x1D2`, `0x226`, `0x260`, `0xAA` | Authority revoked within ≤ 0.3 s of the last valid frame; host warning | **Fail (known GAP-06)**: ≤ ≈2 s (`safety.h:321-344`) |
| VS-SI-13 | E2E plausibility: stuck and replayed frames | FSR-01.06; TSR-4xx | I-1, I-3 | Engaged | (a) Repeat last `0x1D2` with valid checksum while the plant cancels; (b) `0x226` stuck "not pressed" while plant brakes; (c) `0xAA` frozen; (d) `0x260` frozen | Each detected within ≤ 0.3 s and authority revoked | **Fail (known GAP-01)**: only silence detected |
| VS-SI-14 | Checksum and quality-flag rejection | FSR-01.06; TSR-4xx | I-1 | Engaged | Corrupt checksum of `0x1D2`/`0x260`; set wheel-speed fault bits in `0xAA` | Authority revoked on the faulty frame | Meets for checksummed messages and wheel fault bits (`modes/toyota.h:84-93`, `safety.h:112-121`) |

### 6.4 Actuation limits (TSR-1xx, TSR-2xx)

| ID | Title | Trace | Step | Preconditions | Procedure | Pass criteria | Expected baseline |
|---|---|---|---|---|---|---|---|
| VS-SI-15 | Torque magnitude, rate and measured tracking end-to-end | FSR-01.01…01.04, FSR-01.12; TSR-1xx | I-1, I-3 | Engaged | Host commands torque at, below and above each limit (magnitude, up/down rate, RT window, measured-torque difference); also non-zero torque when not engaged | Bus 0 shows only in-limit frames (GC-1); violating frames blocked; authority revoked on violation (FSR-01.12) | Limits enforced (`lateral.h:60-151`); TX violation alone does not revoke (expected **Fail** for revocation); limit values not yet derived (GAP-04) |
| VS-SI-16 | Accel bounds, inactive value, jerk | FSR-03.01…03.03, FSR-04.01, FSR-04.02; TSR-2xx | I-1, I-3 | Engaged / not engaged | Command accel above +2.0, below −3.5, steps of ±4 m/s² within one frame; non-inactive value while not engaged | Out-of-bound and non-inactive frames blocked; jerk-limited | Bounds and inactive value enforced (`longitudinal.h:8-12`); **Fail (known GAP-04)** for jerk |
| VS-SI-17 | Excessive-actuation latch and host fault reactions | FSR-06.04; TSR-6xx | I-2, I-3 | Engaged | Inject via plant: lateral accel > 6 m/s² for > 0.25 s; NaN in actuator output (fault-injection build of controlsd) | Latch set, soft disable + no-entry; NaN treated as a fault with immediate disable and warning | Latch meets (`openpilot/selfdrive/selfdrived/helpers.py`); NaN **Fail (known GAP-19)**: clamped to 0 (`controlsd.py:140-147`) |

### 6.5 Relay and stock PCS path (TSR-506, TSR-7xx)

| ID | Title | Trace | Step | Preconditions | Procedure | Pass criteria | Expected baseline |
|---|---|---|---|---|---|---|---|
| VS-SI-18 | Relay state per mode | FSR-07.03; TSR-506, TSR-702; AOU-13 | I-1, I-4 | — | Cycle SILENT → NO_OUTPUT → Toyota → SILENT; unplug device power while in Toyota mode | Relay released in SILENT/NO_OUTPUT and on power loss (stock camera↔car continuity); energised only in Toyota mode. Reuses VS-HW-01 setup | SILENT/NO_OUTPUT release in code (`main.c:45-54`); power-loss state unknown (AOU-13) |
| VS-SI-19 | Relay malfunction detection | FSR-01.11; TSR-506 | I-1 | Engaged | Inject camera LKA `0x2E4` on bus 0 side (relay bypass), see WP-H-06 VS-HW-03/04 for hardware procedure | All actuation TX and forwarding blocked within ≤ 0.3 s; host immediate disable with correct alert | Detection 1–2 s (`safety.h:215-220, 372-380`) — **Fail (known GAP-12)** for timing |
| VS-SI-20 | PCS message forwarding unchanged | FSR-07.01; TSR-7xx; IF-03 | I-1, I-2, I-4 | Each mode: SILENT, NO_OUTPUT, Toyota disengaged, Toyota engaged, engaged with gas override | Generate camera-side traffic including `0x344` PRE_COLLISION, `0x411` PCS_HUD, `0x283`; in I-4 capture real camera traffic | Every non-intercepted camera frame appears on bus 0 unchanged (content, rate, latency bound to be set); intercepted set (`0x2E4`, `0x191`, `0x412`, `0x343` with op long) not forwarded (`safety.h:270-281`) | Expected to meet in all modes (static block list) |
| VS-SI-21 | PCS masquerade from SoC | FSR-07.02; TSR-7xx; IF-01 | I-1 | Toyota mode | Host sends `0x344`, `0x411`, non-zero `0x283` on bus 0 | All blocked | **Fail (FSR-07.02 finding)**: `0x344`/`0x411` whitelisted (`modes/toyota.h:19-28`); `0x283` non-zero blocked (`toyota.h:251-257`) |

### 6.6 SoC fault reactions and warnings (TSR-6xx, TSR-4xx)

| ID | Title | Trace | Step | Preconditions | Procedure | Pass criteria | Expected baseline |
|---|---|---|---|---|---|---|---|
| VS-SI-22 | Soft disable on stale inputs | FSR-02.02, FSR-02.03, FSR-06.02; TSR-6xx | I-2, I-3 | Engaged, curve scenario (I-3) | Stop `modelV2` (pause modeld) | Visual + acoustic warning ≤ 1 s; no actuation on inputs that are no longer valid (command untrusted → immediate SS-L/SS-G per WP-C-04 §6) | **Fail (known GAP-16)**: up to ≈3.5 s actuation on stale inputs |
| VS-SI-23 | SoC process kill / hang | FSR-01.07, FSR-02.05; TSR-4xx, TSR-6xx | I-2 | Engaged | Kill (SIGKILL) and stop (SIGSTOP) in turn: controlsd, card, pandad, selfdrived, ui, soundd; detailed in WP-V-05 VS-FI-09 | Envelope safe state within FTTI budget when the command path stops; warning within 1 s from SoC or panda siren | Host `processNotRunning`/`commIssue` soft disable; panda 3–5 s (GAP-06); siren timing (GAP-06) |
| VS-SI-24 | Cruise mismatch reaction | FSR-05.06; TSR-3xx | I-2 | — | Plant holds PCM cruise active while selfdrived is disengaged (and reverse) | Warning and cancel request within the bound | **Fail (known GAP-19)**: event only after 6 s, no reaction (`selfdrived.py:421`, `events.py:458-460`) |
| VS-SI-25 | MCU reset during engagement | FSR-01.09, FSR-07.03; TSR-502 | I-1, I-2 | Engaged | `0xd8` reset; NRST from the SoC GPIO (`openpilot/common/hardware/comma/hardware.py:401-408`) | No TX and relay released during reset; after restart SILENT, re-engagement needs a new PCM rising edge; host immediate disable with warning | Expected to meet (start in SILENT, `main.c:295`); relay reset state unconfirmed (AOU-13) |

### 6.7 Back-to-back

| ID | Title | Trace | Step | Preconditions | Procedure | Pass criteria | Expected baseline |
|---|---|---|---|---|---|---|---|
| VS-SI-26 | Target vs host safety model; process replay regression | FSR-01.xx…07.xx; TSR-1xx…3xx | I-1, I-2 | Fork-owned Corolla logs | (a) Feed the same frame sequence (recorded + fault-augmented) to the target MCU on the bench and to host-built `libsafety`; compare per-frame TX/RX decisions and `controls_allowed`. (b) Run `process_replay/test_processes.py` against fork-owned references | (a) identical decisions; any difference is a defect (compiler/target, DFI-17); (b) no unexplained diffs | No fork-owned references (GAP-30) |

## 7. Coverage of TSR blocks and interfaces

| TSR block / interface | Cases |
|---|---|
| TSR-1xx lateral | VS-SI-15, -26 |
| TSR-2xx longitudinal | VS-SI-04, -16, -26 |
| TSR-3xx engagement / override | VS-SI-01…-04, -24 |
| TSR-4xx communication | VS-SI-05, -06, -09…-14, -23 |
| TSR-5xx MCU platform | VS-SI-07, -08, -25 (plus WP-H-06 VS-HW-nn, WP-V-05) |
| TSR-6xx host monitoring | VS-SI-17, -22, -23 |
| TSR-7xx PCS / harness | VS-SI-18…-21 |
| IF-01 / IF-02 / IF-03 / IF-04 / IF-07 / IF-08 | -15,-16,-21 / -01,-02,-12…-14 / -20 / -05…-11 / -22,-23 / WP-H-06 VS-HW-09 |

Every FSR allocated to E-03 or E-05 in WP-C-04 §10 has at least one VS-SI case or a WP-H-06 case. FSRs allocated to EXT-EPS/EXT-PCM are verified in WP-S-09.

## 8. Test report (template)

| Field | Value |
|---|---|
| Report ID | WP-S-08-R-nn |
| Item version | LionDriver tag, openpilot/opendbc/panda commits, model hashes, panda firmware hash |
| Bench configuration | Bench ID, device serial, harness ID, CAN interface, plant model version |
| Date / tester / reviewer (independence) | |

| Case | Step | Version under test | Result (Pass / Fail / Fail known GAP / Blocked) | Measured times | Deviations | Problem report | Evidence (log hash) |
|---|---|---|---|---|---|---|---|
| VS-SI-01 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-02 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-03 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-04 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-05 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-06 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-07 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-08 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-09 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-10 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-11 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-12 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-13 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-14 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-15 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-16 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-17 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-18 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-19 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-20 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-21 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-22 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-23 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-24 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-25 | — | — | **Not yet executed** | — | — | — | — |
| VS-SI-26 | — | — | **Not yet executed** | — | — | — | — |

Summary (to complete after execution): number passed / failed / known GAP / blocked; open problem reports; regression scope; verdict on integration readiness for WP-S-09.

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Replace TSR blocks with WP-S-02 IDs in §6 and §7 | Safety engineer | G2 |
| OI-2 | Build the HIL bench (D-04) and the bench-PC Corolla plant model; record its validation | Test lead | G4 |
| OI-3 | Record fork-owned Corolla drive logs and process-replay references (D-03, GAP-30) | Maintainer | G4 |
| OI-4 | Set latency bound for PCS forwarding (VS-SI-20) from camera message periods | Safety engineer | G2 |
| OI-5 | Decide whether to adapt `tools/sim` to Toyota and route it through a real panda (would make I-3 closed-loop with the real envelope) | SW lead | G3 |
| OI-6 | Re-baseline expected results after the envelope hardening backlog (gap assessment §9 action 5) lands | Test lead | G4 |
