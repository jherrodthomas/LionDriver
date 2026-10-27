# WP-V-05 Fault Injection

| Field | Value |
|---|---|
| Work product | WP-V-05 Fault injection test specification and report |
| Standard reference | ISO 26262-4:2018 §7 (fault injection at system and vehicle level); ISO 26262-5:2018 §10 (hardware integration, fault injection for safety mechanisms); ISO 26262-6:2018 §10–§11 (fault injection at software integration and embedded software test); ASPICE 4.0 SYS.4, SWE.6 |
| Version | 0.13 (RX timeout bound ≤ 0.162 s, was ≤ 0.16 s, as WP-S-04 v0.21 T-01 (161.5 ms: 5 periods of 30.3 ms plus one 10 ms task period); no requirement, budget or verdict changed; 2026-10-27). 0.12 (§5 VS-FI-24, §6 and OI-6: the System FMEA rows are cited by their SFM- IDs, since WP-A-04 v1.19 retired its SFMEA table (DQ-127 A); coverage and cases unchanged; 2026-10-25). 0.11 (OI-1: fault-injection builds follow the test-build procedure of WP-P-01 §7.1, DQ-125 A; 2026-10-22). 0.10 (§5.6: VS-FI-32, a frozen command or an EPS fault late in an assisted lane change, for HE-01.6 (WP-C-03 v0.8, DQ-406 A); AI-drafted; 2026-10-22). 0.9 (VS-FI-10 (b): `test_16` in the pin since `3a8b7c2` (#405); AI-drafted; 2026-10-21). 0.8 (VS-FI-10 (b) test reference: `test_16_engaged_mismatch_siren.py`, panda PR #22; AI-drafted; 2026-10-21). 0.7 (VS-FI-10 (b) follows TSR-307(a) and TSR-516(c), panda `f4803c5`, with variant (b2); VS-FI-31 persistence 0.7 s (DQ-048); VS-FI-09 note on the selfdrived kill; requirement-routes walk of #395; 2026-10-21). 0.6 (OI-5 closed: VS-FI-07 on the reference device, reflashed and rechecked afterwards, DQ-085 B; 2026-10-19). 0.5 (Figure 6-1 added, generated from §5, §6 and §8; 2026-10-13). 0.4 (merge of PR #47 software alignment with the base; the base's baseline-expectation and asset updates and VS-FI-30, VS-FI-31 kept, PR #47's column "At `682f184`" kept; 2026-10-13). It carries PR #47's draft, numbered 0.2 there: RR-2026-009 F-26: current-pin column, ownership of software-level FI, HIL reference. History on the base: 0.3 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.2 (verification status for the integrated envelope changes; 2026-10-12). 0.1 |
| Status | Draft (specification). **Results: not yet executed** |
| ASIL / scope | ASIL C (SG-01 until re-rated, WP-S-02 "B‡"), ASIL B (SG-02…SG-07); reference configuration |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); campaign plan reviewed with independence per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `bf6ce8c` (status update 2026-10-12; opendbc `7993399`, panda `b790fca`) |

> [!NOTE]
> **Status at `682f184` (opendbc `7993399`, panda `8aa8671`).** This document describes the code at `8b8c6ae` unless a statement names a later pin. Safety mechanisms integrated since then (hardware watchdog and 100 Hz safety task, RX timeout, TX whitelist, safety-mode lock, 0.3 s heartbeat, IRQ priorities, EPS fault, cruise-main check, TX rate supervision) are recorded in the [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) Baseline column and the [change records](../07-supporting/impact/README.md). The sections of this document that still describe the earlier behaviour are listed in [RR-2026-009](../05-software/reviews/RR-2026-009.md) and are to be updated ([WP-M-14 §2.3](../01-management/WP-M-14-iso26262-6-implementation-specification.md#23-pre-entry-engineering-track) P-03).

## 1. Purpose and scope

**Ownership of software-level fault injection.** Fault injection at the software level (ISO 26262-6 §10, §11) is specified and owned by [WP-W-07](../05-software/WP-W-07-software-integration-verification.md) (VS-SWI) and [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md) (VS-SWQ). The VS-FI cases below that exercise envelope software mechanisms are their item-level counterparts and link to them; this document owns the system- and vehicle-level campaign (ISO 26262-4 §7, -5 §10). The column "At `682f184`" lists the WP-W-02 Baseline entries that changed since `8b8c6ae` for the SWSRs refining each case's TSRs; "Baseline expectation" stays as written at `8b8c6ae` ([RR-2026-009](../05-software/reviews/RR-2026-009.md) F-26).

This document specifies the fault-injection campaign that shows each safety mechanism of LD-SDA detects the faults it is designed for and reaches the safe state within the fault-tolerant time interval. It covers faults on the vehicle CAN, the SoC↔panda link, the SoC software, the panda MCU and the harness, and tampering with configuration data. It is the detailed procedure source for the fault-injection cases referenced from [WP-S-08](../03-system/WP-S-08-system-integration-test.md) (VS-SI-nn), [WP-S-09](../03-system/WP-S-09-system-verification.md) (VS-SQ-nn) and [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) (VS-HW-nn).

Inputs: the safety mechanisms and timing of [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (Draft v0.1); the FTTI allocation of [WP-C-04 §8](../02-concept/WP-C-04-functional-safety-concept.md#8-ftti-allocation-preliminary) until [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) is approved; the failure modes and single points of failure of [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md); the interference cases of [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md); the dependent failure initiators of [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md).

Not in scope: cybersecurity penetration testing ([WP-V-06](WP-V-06-cybersecurity-validation.md)) — the configuration-tampering cases here assume a faulty, not a malicious, QM element; SOTIF triggering-condition testing ([WP-V-03](WP-V-03-sotif-known-scenarios.md)).

## 2. Existing fault-injection assets

| Asset | Faults it injects | Level | Limitation for LionDriver evidence |
|---|---|---|---|
| opendbc safety tests (`opendbc_repo/opendbc/safety/tests/common.py`, `test_toyota.py`) | Bad checksums and wheel-fault bits (`test_toyota.py:461-483`), RX timeouts via `safety_tick` (`common.py:1208`) and the 5-period tests `test_rx_timeout_5_periods*` (`test_toyota.py:369, 413`), cruise active with main off (`:263`), EPS fault (`:309`), TX rate flood (`test_tx_rate_*`, `:128-228`), relay malfunction (`common.py:1067`), TX spam on all buses (`common.py:937`), out-of-limit torque/accel (`common.py:550-650`), brake/gas/cruise edge cases (`common.py:1086-1176`) | Unit/integration on host `libsafety` | Runs on x86 with `ALLOW_DEBUG` (GAP-41), not on the Cortex-M7 (GAP-13); in LionDriver CI `safety.yaml` (default and `LIONDRIVER_REFERENCE` variants) from 2026-10-12, no run recorded as evidence yet |
| Mutation testing (`opendbc_repo/opendbc/safety/tests/mutation.py`) | Code mutations to check that tests detect faults in the safety code | Unit (test-suite adequacy) | Measures test strength, not mechanism behaviour; 3 accepted survivors (GAP-13); in LionDriver CI `safety.yaml`, default and reference builds (`mutation`, `mutation_reference`, LionDriver #44) |
| Process fuzzing (`openpilot/selfdrive/test/process_replay/test_fuzzy.py`) | Random capnp messages into replayed processes with the Corolla fingerprint | SoC software | Excludes selfdrived, controlsd, card, plannerd, calibrationd, dmonitoringd, paramsd, modeld (`test_fuzzy.py:12`); 10 examples per process |
| pandad SPI corruption (`openpilot/selfdrive/pandad/spi.cc:280-301`, `tests/test_pandad_spi.py`) | Random bit corruption of SPI TX/RX at probability `SPI_ERR_PROB` | Device | comma device farm only (`Jenkinsfile:303-307`) |
| panda HITL (`panda/tests/hitl/test_5_spi.py:58-72`, `test_2_health.py:38`, `test_6_safety.py:8`, `test_9_harness.py`) | Bad SPI header and checksum, heartbeat, NO_OUTPUT TX blocking, harness orientation | HIL | comma farm only (GAP-30); no car-mode safety cases |
| LionDriver HITL (`panda/tests/hitl/test_10_hw_watchdog.py` … `test_14_tx_rate.py`, panda `b790fca`) | MCU hangs (fault-injection build), mode-lock requests, RX message silence, EPS fault codes, TX flood; the jungle plays the car on bus 0 | HIL | Implemented, **not run** (bench not built, GAP-30; [HIL bench plan](../05-software/hil-bench/README.md)) |
| LionDriver panda host tests (`panda/tests/heartbeat_monitor`, `heartbeat_siren` (2026-10-13), `reference_lock`, `irq_priorities`, `eps_fault_siren`, `hw_watchdog`) | Heartbeat loss, heartbeat-loss siren, refused requests, EPS-fault siren timing, watchdog feed logic | Unit on host | In LionDriver CI (`safety.yaml` `panda_host_tests`) from 2026-10-12; no run recorded as evidence yet |
| selfdrived state-machine tests (`openpilot/selfdrive/selfdrived/tests/test_state_machine.py`) | Event-driven state transitions | Unit | No timing; no input-loss injection |

None of these has produced recorded evidence under LionDriver control yet. The campaign reuses them where possible and adds the cases marked "new".

## 3. Injection levels and methods

| Level | Code | Environment | Injection method |
|---|---|---|---|
| Unit | U | Host build of opendbc `libsafety` (release defines, GAP-41) and openpilot unit tests in fork CI | Test harness calls hooks with crafted frames; Python fault hooks in processes |
| SoC software-in-the-loop | S | Process replay with modified input logs; `test_fuzzy` extended to the excluded processes | Message deletion, delay, duplication, NaN injection, param changes |
| Hardware-in-the-loop | H | LionDriver HIL bench: plan in [`05-software/hil-bench/`](../05-software/hil-bench/README.md), software test environment [WP-W-08 §3](../05-software/WP-W-08-embedded-software-testing.md#3-test-environment-hil-bench-d-04), hardware side [WP-H-06 §2](../04-hardware/WP-H-06-hardware-integration-verification.md#2-test-environment-hil-bench-decision-d-04); reference device, harness, CAN interface, programmable supply | Bench CAN generator (frame corruption, stuck, replay, silence, error frames); host scripts (`panda` library) for SPI/commands; `SPI_ERR_PROB`; process kill/stop on the SoC; fault-injection firmware build (SWD, forced loops); power supply profiles |
| Vehicle, closed course | V | Reference vehicle under [WP-V-07](WP-V-07-vehicle-test-operations.md) | Closed-course test host build with trigger points (process kill, frozen command); no injection on public roads |

Rules:

1. A fault-injection firmware or host build is a separate configuration item ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)); its differences from release are listed and reviewed; it is never installed for public-road use.
2. Each case is run first at the lowest level that can show the property, and again at the highest level needed to show timing on target hardware.
3. Every case checks the global criteria of WP-S-08 §5: **GC-1** no actuation frame outside the envelope limits on bus 0; **GC-2** stock PCS frames forwarded unchanged when not intercepted by design.

## 4. Timing basis

| Safety goal | FTTI (prelim.) | Budget used here | Source |
|---|---|---|---|
| SG-01 | ≤ 0.5 s | Detection ≤ 0.3 s, reaction ≤ 0.1 s, plus EPS response | WP-C-04 §8; TSR-401, -406, -407, -408 |
| SG-02, SG-06 | ≤ 1 s to warning | Panda siren ≤ 0.5 s after detection; SoC take-over request ≤ 1 s | TSR-516, TSR-606 |
| SG-03, SG-04 | ≤ 1 s | Detection ≤ 0.5 s, reaction ≤ 0.3 s | WP-C-04 §8 |
| SG-05 | ≤ 0.2 s | One brake message period + one frame | TSR-302 |
| SG-07 | ≤ 0.2 s (forwarding loss, preliminary) | Detect ≤ 0.1 s (TSR-711, TSR-501), relay to stock path ≤ 0.1 s (TSR-706) | TSR-501, TSR-706, TSR-711 |
| MCU execution faults | ≤ 0.5 s (SG-01); ≤ 0.2 s (SG-07 forwarding) | Detection ≤ 0.1 s (watchdog), reaction ≤ 0.1 s | TSR-501, TSR-502 |

## 5. Fault list and test specification

Columns: **Lvl** = level(s); **Mechanism** = safety mechanism expected to act (TSR); **Expected reaction and time**; **Pass criteria**; **Baseline expectation** = what the code at `8b8c6ae` is expected to do (rows marked 2026-10-12 or naming later commits state the code at `bf6ce8c`, panda `b790fca`, opendbc `7993399`; none verified on hardware); **Asset** = existing test to reuse or "new".

### 5.1 Vehicle CAN faults (RX side)

| ID | Fault | Target / signal | Lvl | Mechanism | Expected reaction and time | Pass criteria | Baseline expectation | Asset | At `682f184` (from WP-W-02) |
|---|---|---|---|---|---|---|---|---|---|
| VS-FI-01 | Corrupted frame (bad checksum, wrong length) | `0x1D2`, `0x260` (checksummed); `0x226`, `0xAA` (none) | U, H | TSR-402, TSR-406 | Authority revoked on the faulty frame, ≤ 0.1 s to SS-L/SS-G | Revocation on first bad frame; GC-1 | Checksummed messages meet (`safety.h:164-197`); `0x226`/`0xAA` cannot be detected (GAP-01) | `test_toyota.py:461-483`; new HIL | SWSR-108a: Partial |
| VS-FI-02 | Stuck / frozen payload with valid checksum | `0x1D2` CRUISE_ACTIVE stuck 1; `0x260` torque frozen; `0xAA` frozen while moving; `0x226` stuck "not pressed" | U, H | TSR-404, TSR-405, TSR-406 | Detected within t_frz or cross-check tolerance; revoke ≤ 0.1 s | Detection inside SG-01 budget (≤ 0.3 s) where signals are gating | Not detected (GAP-01) | new | SWSR-405: Partial; SWSR-108a: Partial |
| VS-FI-03 | Replayed / duplicated / inserted frames | Same IDs at 2× rate; old frames re-injected | U, H | TSR-403, TSR-406 | Detected within ≤ 0.1 s window | Revocation and fault code | Not detected (no counters, GAP-01) | new | SWSR-108a: Partial |
| VS-FI-04 | Message timeout | Each of `0x1D2`, `0x226`, `0x260`, `0xAA` (later `0x262`, `0x1D3`, `0xB4`) silenced | U, H | TSR-401, TSR-406 | Absence after 5 periods detected at ≥ 50 Hz; revoke ≤ 0.1 s | Total ≤ 0.3 s | 2026-10-12: 5 nominal periods, 100 Hz task, no 1 s floor: `0xAA` 60 ms, `0x260` 100 ms, `0x226` 125 ms, `0x1D2` 151.5 ms, each +10 ms (≤ 0.162 s); reference build adds `0x262` (25 Hz) and `0x1D3` (33 Hz). Rates not yet confirmed on logs (`tools/can_gaps/can_gap_scan.py`, WP-S-05 OI-7) | U: `test_rx_timeout_5_periods*`; H: `panda/tests/hitl/test_12_rx_timeout.py` (not run) | SWSR-401: Met for the Toyota RX checks; SWSR-401a: Partial; SWSR-108a: Partial |
| VS-FI-05 | Cross-signal implausibility | Brake in `0x226` vs PCM brake; wheel speed vs vehicle speed | U, H | TSR-405 | Disagreement beyond tolerance → RX fault | Revocation | TSR-405(c) implemented in the reference build: CRUISE_ACTIVE with `0x1D3` MAIN_ON = 0 refuses engagement, revokes after 150 ms (`test_cruise_active_with_main_off`); (a), (b), (d) not implemented | U: `test_cruise_active_with_main_off`; new for (a), (b), (d) | SWSR-405: Partial |
| VS-FI-22 | Car-side bus-off, CAN-H/L short, error frames | Bus 0 | H | TSR-508 | Authority revoked; warning | ≤ SG-01 budget | Bus-off counted, core reset; no safety reaction (HWSR-508b) | WP-H-06 VS-HW-11 | As at `8b8c6ae` |
| VS-FI-31 | EPS fault | `0x262` EPS_STATUS `LKA_STATE` in the fault set {0, 3, 9, 11, 17, 21, 25} while engaged | U, H | TSR-110, TSR-516(b) | LKA actuation (torque or steer request) refused while the fault lasts; reported (`pandaState.epsFault`); siren once the fault has persisted 0.7 s while authority is granted (DQ-048, panda `bf8102a`; siren ≤ 0.96 s from onset, WP-S-04 T-28) | As stated; GC-1 | Implemented in the reference build (opendbc `242d63d`, panda `b790fca`); fault code set to be confirmed for the reference EPS firmware | U: `test_eps_fault_blocks_lka`, `panda/tests/eps_fault_siren`; H: `panda/tests/hitl/test_13_eps_fault.py` (not run) | SWSR-110: Partial (reference build); SWSR-516: Partial (EPS-fault siren, panda `b790fca`) |

### 5.2 SoC ↔ panda link faults

| ID | Fault | Target | Lvl | Mechanism | Expected reaction and time | Pass criteria | Baseline expectation | Asset | At `682f184` (from WP-W-02) |
|---|---|---|---|---|---|---|---|---|---|
| VS-FI-06 | SPI bit errors | All SPI transfers at `SPI_ERR_PROB` 0.001 / 0.01 / 0.1; targeted single-bit flips in header and in CAN payload | H | TSR-410, TSR-413 | Corrupted transfers rejected (NACK); error burst while engaged → revoke ≤ 0.3 s | No corrupted frame on bus 0 (GC-1); no unintended control command executed | 8-bit XOR; some multi-bit errors pass (GAP-10); error counted only | `spi.cc:280-301`, `test_pandad_spi.py`, `test_5_spi.py:58-72` | As at `8b8c6ae` |
| VS-FI-07 | Out-of-range length fields and indices | SPI header MOSI/MISO length > buffer; `0xe8` with `param1 ≥ PANDA_CAN_CNT` | H (fault-injection host) | TSR-412 | NACK, SPI error counted; no memory written outside buffers | Memory map check after test (SWD read of guard patterns around `spi_buf_rx`/`spi_buf_tx` and DTCM safety data) unchanged | No bound check (WP-S-02 NF-04, `drivers/spi.h:115-116, 233`); expected effect limited to SRAM1/2 (WP-A-02 FFI-SP-02) — to confirm | new | As at `8b8c6ae` |
| VS-FI-08 | Stale / replayed / frozen command stream | Replay identical `0x2E4`/`0x343` transfers; stop `0x2E4` while heartbeat continues | H | TSR-408, TSR-411 | Stale transfers rejected; no `0x2E4` for > 50 ms → SS-L | SS-L within ≤ 0.1 s of the 50 ms limit | Not detected; heartbeat 3–5 s (GAP-10, GAP-06) | new | As at `8b8c6ae` |
| VS-FI-10 | Heartbeat faults | (a) heartbeat stops; (b) `engaged=0` while authority granted; (c) heartbeat continues but control-loop evidence frozen | H | TSR-407, TSR-307 (a), TSR-409, TSR-510, TSR-516(a), TSR-516(c) | (a) revoke after 0.3 s, SS-S ≤ 2 s, siren ≤ 0.5 s; (b) revoke 0.3 s after the first heartbeat that reports not engaged (TSR-307(a)); while PCM cruise is still active, siren ≤ 0.5 s after that heartbeat (TSR-516(c)); variant (b2): selfdrived killed while controlsd, card and pandad run on, so the heartbeat continues with engaged=0 once selfdriveState is stale; (c) revoke ≤ 0.3 s | As stated | (a) authority revoked at 0.3 s (`heartbeat_monitor.h`, all builds; host-tested only, `panda/tests/heartbeat_monitor`); SILENT after 5 s unchanged; siren: 2026-10-13, 3 s at the revocation when authority was granted, ≈ 0.56 s after the last heartbeat, all builds (panda `c33343b`, host test `panda/tests/heartbeat_siren`), otherwise 3 s after 5 s as before; (b) since panda `f4803c5` (#382): revoked 0.3 s after the first not-engaged heartbeat and siren if PCM cruise is still active 0.5 s after it (`engaged_mismatch.h`, reference build; other builds keep the 1 Hz check, ≈ 2–3 s, no siren); plant run of (b2): revoked 0.39–0.48 s, siren 0.63–0.88 s after the stop ([engaged-mismatch.md](../sim/results/engaged-mismatch.md), synthetic, no evidence credit); (c) not detected | `test_2_health.py:38`; (a) `panda/tests/hitl/test_15_heartbeat_siren.py` (revocation timing; siren by ear; not run); (b) `panda/tests/hitl/test_16_engaged_mismatch_siren.py` (revoke ≤ 0.3 s; siren at 0.5 s while PCM cruise stays active, silent when cruise drops first or before 0.5 s; siren by ear; panda PR #22, in the pin since `3a8b7c2` (#405); not run on hardware); new | SWSR-401a: Partial; SWSR-407: Implemented; SWSR-516: Partial (heartbeat-loss siren, panda `c33343b`) |
| VS-FI-11 | Unauthorised configuration commands in car mode | `0xdc` (other mode/param), `0xc5`, `0xe7`, `0xe5`, `0xde`, `0xf9`, `0xfc`, `0xe8`, `0xdb`, `0xe6`, `0xf1`; for information `0xd1`/1, `0xd8` | H | TSR-512, TSR-513 | Rejected; state unchanged | Mode, relay and CAN configuration unchanged; GC-2 holds (forwarding continues) | Reference build: refused by `reference_lock.h` (host `panda/tests/reference_lock`; HIL `test_11_reference_lock.py`, not run). Default build: all accepted (GAP-09, WP-S-02 NF-05); `0xe7` expected to stop camera-side forwarding with relay energised (WP-A-02 FFI-CM-08) | U: `panda/tests/reference_lock`; H: `test_11_reference_lock.py` | SWSR-104a: Met in the reference build through the panda lock, not verified on hardware; SWSR-512: Met in the reference build; SWSR-512a: Met in the reference build; SWSR-513: Met in the reference build for the listed requests |
| VS-FI-30 | SoC TX flood (babbling SoC) | Any TX-whitelisted ID, e.g. `0x2E4` at 2× nominal rate and line rate (reference build) | U, H | TSR-518 (DN-01) | Frames beyond the per-ID budget rejected; authority revoked ≤ 0.1 s after the first rejected frame; reported (`pandaState.txRateExceeded`) | As stated; GC-1 | Implemented in the reference build (opendbc `7993399`); default build: no rate supervision | U: `test_tx_rate_*`; H: `panda/tests/hitl/test_14_tx_rate.py` (not run) | SWSR-518: Implemented in the reference build |

**VS-FI-07 on the reference device (DQ-085, option B, 2026-10-19).** No spare unit is bought. VS-FI-07 runs on the reference device and panda; afterwards both are reflashed with the release image and rechecked against their provisioning record before any further evidence is taken from them. A difference found by that recheck is recorded, and the evidence it affects is repeated. The lead accepted the risk of altering the reference unit.

### 5.3 SoC software faults

| ID | Fault | Target | Lvl | Mechanism | Expected reaction and time | Pass criteria | Baseline expectation | Asset | At `682f184` (from WP-W-02) |
|---|---|---|---|---|---|---|---|---|---|
| VS-FI-09 | Process kill (SIGKILL) and hang (SIGSTOP) | controlsd, card, pandad, selfdrived, plannerd, modeld, radard, ui, soundd, dmonitoringd | S, H, V (controlsd, pandad only) | TSR-407, TSR-408, TSR-409, TSR-516 (envelope); TSR-601, TSR-606 (SoC) | Command path loss → SS-L/SS-G ≤ 0.3 s; warning ≤ 1 s (SoC) or ≤ 0.5 s siren (SoC dead); for a selfdrived kill the 1 s warning is met only by the panda siren under TSR-516(c), since openpilot's own alert comes at 5 s (soundd `SELFDRIVE_STATE_TIMEOUT`), see VS-FI-10(b2) | Per process: time to safe state and time to warning recorded and within budget | `processNotRunning`/`commIssue` soft disable keeps actuating up to 3 s (GAP-16); panda 3–5 s. 2026-10-13: where the heartbeat stops (`pandad`, whole SoC), revocation at 0.3 s and siren ≈ 0.56 s after the last heartbeat if engaged, all builds (panda `c33343b`), not verified | new | SWSR-401a: Partial; SWSR-407: Implemented; SWSR-516: Partial (heartbeat-loss siren, panda `c33343b`) |
| VS-FI-12 | Stale or faulty model output | `modelV2` delayed (0.1–1 s), dropped, frozen; NaN/Inf in plan, curvature, accel; out-of-range curvature | S, H | TSR-602, TSR-603, TSR-616, TSR-601 | Stale/non-finite input → immediate disable (untrusted command) | No actuation on invalid input beyond one frame; take-over request ≤ 1 s | Alive window 10× period (0.5 s) plus 3 s soft disable (GAP-16); NaN guard only on big model (`modeld.py:210-211`) | new (extend `test_fuzzy.py` to modeld outputs) | As at `8b8c6ae` |
| VS-FI-13 | Non-finite actuator commands | controlsd actuator output NaN/Inf | U, S | TSR-604 | Immediate disable | Fault raised, not clamped | Clamped to 0 silently (`controlsd.py:140-147`, GAP-19) | new | As at `8b8c6ae` |
| VS-FI-14 | Out-of-limit commands from the SoC | Test host build of card sends torque above magnitude/rate/measured bound, accel outside bounds and above jerk bound, non-zero torque while not engaged, `STEER_REQUEST`=1 with zero torque while not engaged | U, H, V (bounded) | TSR-101…TSR-109, TSR-201…TSR-205 | Frame rejected; authority revoked; zero-torque frame within ≤ 0.1 s | GC-1; revocation; EPS receives torque 0 | Frames rejected; no revocation on TX violation; no zero-torque substitution (WP-S-02 NF-01, NF-02); no jerk limit (GAP-04) | `common.py:550-650`; new HIL/V | SWSR-104a: Met in the reference build through the panda lock, not verified on hardware; SWSR-108a: Partial |
| VS-FI-25 | Driver-monitoring input loss | Driver camera blocked / disconnected; `dmonitoringmodeld` killed; `driverStateV2` invalid | S, H | TSR-609 | DM invalid > 2 s while engaged → take-over request | Within 2 s | Source validity hard-coded `True` (`dmonitoringmodeld.py:99`, GAP-21); `dmonitoringd` invalid → `commIssue` | new (no DM data-loss tests exist, `monitoring/test_monitoring.py`) | As at `8b8c6ae` |

### 5.4 Panda MCU and hardware faults

| ID | Fault | Target | Lvl | Mechanism | Expected reaction and time | Pass criteria | Baseline expectation | Asset | At `682f184` (from WP-W-02) |
|---|---|---|---|---|---|---|---|---|---|
| VS-FI-15 | Power dips and brown-out | Device 12 V input: dropouts 1 ms–1 s, slow ramp, plateau between nominal and BOR, cranking profile | H | TSR-505, TSR-706 | Reset or SS-S; relay to stock path; restart in SILENT, new engagement needed | GC-1 throughout; relay state as specified; no hang with relay energised | PVD not enabled; BOR level unset in code; behaviour unknown | WP-H-06 VS-HW-09 | As at `8b8c6ae` |
| VS-FI-16 | Panda reset during engagement | `0xd8`; NRST from SoC GPIO; IWDG reset (after TSR-501) | H | TSR-311, TSR-706 | No TX and relay released during reset; authority false after restart | Re-engagement only on new PCM edge; SoC immediate disable with warning | Starts in SILENT (`main.c:295`); relay reset state unconfirmed (AOU-13) | new; WP-H-06 VS-HW-19 | As at `8b8c6ae` |
| VS-FI-17 | Panda hang | Fault-injection build: infinite loop in main context, in tick ISR, in SPI ISR; interrupts disabled | H | TSR-501, TSR-502, TSR-706 | Watchdog reset ≤ 0.2 s; relay to stock path ≤ 0.1 s | Total ≤ 0.3 s; camera PCS path restored (GC-2) | IWDG in window mode in the pin (`drivers/hw_watchdog.h`); host `panda/tests/hw_watchdog`; HIL `test_10_hw_watchdog.py` (main loop, tick, interrupts disabled, safety task, early feed; not run); SPI-ISR hang injection not implemented | WP-H-06 VS-HW-06; `test_10_hw_watchdog.py` | SWSR-501: Implemented; SWSR-501b: Implemented, not verified on hardware |
| VS-FI-18 | Memory corruption | SWD write to `controls_allowed`, limit state, safety mode; ECC error injection where silicon allows; stack overflow; write to safety data from comms handler | H (fault-injection build) | TSR-503, TSR-507, TSR-502 | Detected (ECC/MPU/CRC) → SS-S ≤ 0.1 s | No actuation outside limits after injection | No MPU, no ECC handling (GAP-08): corruption not detected | WP-H-06 VS-HW-17, -18 | As at `8b8c6ae` |
| VS-FI-19 | Interrupt storm | CAN flood on bus 0/2 at line rate; SPI request flood; USB flood | H | TSR-502 (interrupt-rate faults), TSR-508 | Rate fault → SS-S; tick and timeouts keep their timing until then | Heartbeat/RX timeout timing unchanged under load, or SS-S | Rate faults report-only (`drivers/interrupts.h:33-35`, GAP-08) | `common.py:937` (logic); new HIL | As at `8b8c6ae` |
| VS-FI-20 | Clock fault | HSE stop (test pad) or analysis; clock drift (if injectable) | H, A | TSR-504 | CSS → NMI → reset; drift detected | Safe state; no actuation with wrong timing | CSS enabled (`stm32h7/clock.h:118-119`); drift not detected | WP-H-06 VS-HW-16 | As at `8b8c6ae` |
| VS-FI-21 | Relay faults | Stuck released, stuck intercepting, coil open, contact bounce | H | TSR-506, TSR-710 | Mismatch detected ≤ 0.3 s both directions; actuation TX inhibited | As stated | Only "released" direction by traffic, 1–2 s; "intercepting" not detected (GAP-12) | `common.py:1067`; WP-H-06 VS-HW-03, -04 | As at `8b8c6ae` |
| VS-FI-24 | Camera-side forwarding interruption with relay energised | `0xe7` in car mode; bus-2 transceiver disabled; bus-2 error frames | H | TSR-513, TSR-707 | Forwarding loss detected and reported; command rejected | GC-2 or SS-S (relay released) within ≤ 0.1 s | Not detected (WP-A-04 SPF-08, SFM-033.C2) | new | SWSR-513: Met in the reference build for the listed requests |
| VS-FI-26 | Over-temperature | MCU DTS above threshold; fan stall | H | TSR-509 | SS-S ≤ 1 s | As stated | Reported only | WP-H-06 VS-HW-15 | As at `8b8c6ae` |
| VS-FI-28 | Harness disconnect / orientation change while relay driven | Unplug harness; flip | H | TSR-701 | SS-S; warning | As stated | Detection suspended while relay driven (`drivers/harness.h:59`) | WP-H-06 VS-HW-13; `test_9_harness.py` | As at `8b8c6ae` |
| VS-FI-29 | Firmware integrity | Corrupted application image; debug build; image signed with the committed debug key | H | TSR-503 (CRC), TSR-511, TSR-514 | Image refused or safe state at start-up; debug build detectable by version request | Release device refuses non-release images | Debug key accepted in debug builds; no run-time CRC (GAP-24, GAP-25) | `panda/tests/hitl/test_1_program.py`; WP-V-06 for the malicious variant | SWSR-511a: Partial |

### 5.5 Configuration data tampering (faulty QM element)

| ID | Fault | Target | Lvl | Mechanism | Expected reaction and time | Pass criteria | Baseline expectation | Asset | At `682f184` (from WP-W-02) |
|---|---|---|---|---|---|---|---|---|---|
| VS-FI-23 | Params tampering | `CarParams` with another safety model or safety param (EPS scale ≠ 73, ALT_BRAKE, LTA flags); `JoystickDebugMode`, `LateralManeuverMode`, `LongitudinalManeuverMode`; `IsDriverViewEnabled`; `ExperimentalMode`; `DisengageOnAccelerator`; changed while onroad and before boot | S, H | TSR-512 (envelope ignores non-reference param), TSR-610, TSR-613, TSR-806 (installation check) | Envelope runs only Toyota/param 73 or refuses to drive the relay; debug modes and DM demo unavailable in reference builds | No change of envelope behaviour; no debug process started; DM not in demo mode while engagement possible | Envelope takes whatever pandad sends (`openpilot/selfdrive/pandad/panda_safety.cc:56-70`); debug processes start from params (`openpilot/system/manager/process_config.py:34-47`); DM demo mode (`openpilot/selfdrive/monitoring/dmonitoringd.py:26-27`) (GAP-09, GAP-20) | new | SWSR-104a: Met in the reference build through the panda lock, not verified on hardware; SWSR-512: Met in the reference build; SWSR-512a: Met in the reference build |

### 5.6 Vehicle-level confirmation (closed course)

| ID | Fault | Target | Lvl | Mechanism | Expected reaction and time | Pass criteria | Baseline expectation | Asset | At `682f184` (from WP-W-02) |
|---|---|---|---|---|---|---|---|---|---|
| VS-FI-27 | Selected faults while driving | VS-FI-08 (frozen command), VS-FI-09 (pandad kill, SoC freeze), VS-FI-14 (bounded out-of-limit command) in a constant-radius curve and on a straight at 60 km/h | V | As in the referenced cases | As referenced, plus measured lateral deviation | Lateral deviation within the value used for the FTTI derivation (WP-S-04); safety driver not required to intervene beyond the expected take-over | Timing failures expected (GAP-06, GAP-16) | WP-S-09 VS-SQ-12, -13 | As at `8b8c6ae` |
| VS-FI-32 | Fault late in an assisted lane change (HE-01.6, DQ-406 A) | (a) command stream frozen (as VS-FI-08) and (b) EPS fault (as VS-FI-31), each injected in the second half of a driver-initiated lane change to the left, straight road and gentle curve, 80–110 km/h | S, V | TSR-408, TSR-110, TSR-516(b) | (a) stale command detected and authority revoked ≤ 0.1 s after the 50 ms limit; (b) LKA refused while the fault lasts, siren once it has persisted 0.7 s | The car does not cross the target lane's far line; the safety driver is not required to intervene beyond the expected take-over | (a) Not detected (GAP-10): in the plant the frozen frame carries the car over the far line (edge-case row EC-11, about 12 m at 80 km/h); (b) siren as VS-FI-31, the car's lateral speed still carries it about 0.7 m over the far line (EC-13). Synthetic plant runs, no credit | S: plant scene `he-01-6-lane-change-overshoot` and search family `fault-timing-lane-change` ([`sim/search/families.yaml`](../sim/search/families.yaml)); V: new (closed course, with VS-FI-27) | As at `8b8c6ae` |

## 6. Coverage of safety analyses

| Analysis item | Fault-injection cases |
|---|---|
| WP-A-04 SPF-01 (limit values) | Not testable by fault injection; covered by limit derivation and WP-S-09 VS-SQ-03 |
| WP-A-04 SPF-02 (post-hook frame corruption) | VS-FI-18 (TX queue RAM corruption via SWD: expected detected by the packet XOR and dropped); FDCAN message RAM injection only if supported (WP-A-04 OI-4) |
| WP-A-04 SPF-03 (SoC disables monitor) | VS-FI-11, VS-FI-23, VS-FI-29 |
| WP-A-04 SPF-04 (shared RX path) | VS-FI-02, VS-FI-03, VS-FI-05 |
| WP-A-04 SPF-05 (debug build) | VS-FI-29 |
| WP-A-04 SPF-06 (MCU hang, relay energised; GAP-43) | VS-FI-17 |
| WP-A-04 SPF-07 (relay welded) | VS-FI-21 |
| WP-A-04 SPF-08 (`0xe7` stops forwarding) | VS-FI-11, VS-FI-24 |
| WP-A-02 FFI-SP-02 (SPI length) | VS-FI-07 |
| WP-A-02 FFI-TM-01/02 (ISR load, hang) | VS-FI-17, VS-FI-19 |
| WP-A-02 FFI-CM-01…-04, -11 | VS-FI-06, -08, -10, -19 |
| WP-A-03 DFI-01, -02, -04, -07 | VS-FI-15, -20, -22, -26 |
| WP-A-03 DFI-09 (shared `CarParams`) | VS-FI-23 |
| WP-A-03 DFI-14 (SoC crash removes warning) | VS-FI-09, VS-FI-10 |

Every System FMEA cause in the WP-A-04 §10 map with a named mechanism maps to at least one case above, except eight added in WP-A-04 v0.2, which still need cases (OI-6): SFM-016.C2 (envelope blocking detected late), SFM-026.C1 (hung UI render loop), SFM-026.C2 (stalled or muted audio), SFM-009.C4 (unannounced deceleration), SFM-009.C1 (FCW from stale input), SFM-029.C6 (TX burst), SFM-033.C6 (camera-side bus fault) and SFM-033.C2 (block-list entry). Causes whose mechanism is "none" are run to confirm the baseline expectation and to record the gap. The IDs are those of [system-fmea.yaml](../08-analyses/fmea/analyses/system-fmea.yaml), the only System FMEA since WP-A-04 retired its table (DQ-127 A).

![Figure 6-1: matrix of the fault-injection cases VS-FI-01 to VS-FI-32 grouped by §5.1 to §5.6, against injection levels, TSR blocks 1xx to 8xx, safety goals SG-01 to SG-07, §6 coverage, WP-W-02 status and §8 result, with a strip of the §6 analysis items of WP-A-04, WP-A-02 and WP-A-03](figures/fig-v05-6-1-fault-coverage.svg)

*Figure 6-1.* One row per §5 case: the TSR blocks its Mechanism column names (with the number of TSRs), the safety goals reached through those TSRs' parent FSRs in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), whether the table above names it, the "At `682f184`" status (implementation, not verification) and the §8 result. VS-FI-27 inherits the TSRs of the cases it repeats (hollow). The strip below shows the table above per analysis; nothing is green because no case has been executed. Drawn from the §5 tables, the table above and §8. Generated by [`figures/fig_v05_fault_coverage.py`](figures/fig_v05_fault_coverage.py); CI fails if it is stale.

## 7. Campaign execution order

1. **U level in fork CI**: VS-FI-01…-05, -11 (reference build), -13, -14, -30, -31 on host `libsafety` and the panda host tests. They run in LionDriver CI `safety.yaml` (default and reference variants) from 2026-10-12, still in the `ALLOW_DEBUG` configuration (GAP-41); no run recorded as evidence yet.
2. **S level**: VS-FI-09, -12, -13, -23, -25 with process replay on fork-owned Corolla logs.
3. **H level, release firmware**: VS-FI-01…-11, -14…-16, -19, -21…-26, -28…-31 (-30, -31 and the reference part of -11 with a reference build, [HIL bench plan](../05-software/hil-bench/README.md) §5.5). Baseline run first to record known GAPs. A case that [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md) §6.1 maps to a VS-SWQ case is run once, on the reference device, and reported in WP-W-08; this document cites that entry and does not re-run it. This document stays the only source of the injection procedure.
4. **H level, fault-injection firmware**: VS-FI-07, -17, -18, -20 (after the related mechanisms exist; WP-H-06 DC-nn).
5. **V level**: VS-FI-27 after G1 and WP-S-08 completion.
6. **Regression**: after each change to a safety-relevant file, re-run the cases whose mechanism the change touches (impact analysis per [WP-P-02](../07-supporting/WP-P-02-change-management.md)).

## 8. Report (template)

| Field | Value |
|---|---|
| Report ID | WP-V-05-R-nn |
| Item version | LionDriver tag; openpilot/opendbc/panda commits; panda firmware hash (release and fault-injection builds); model hashes |
| Environment | Level; bench ID / vehicle VIN; CAN interface; supply; instruments and calibration |
| Date / tester / reviewer (independence) | |

| Case | Level | Version under test | Injected fault (exact) | Detected? | Detection time | Reaction time | Safe state reached | GC-1 / GC-2 | Result (Pass / Fail / Fail known GAP / Blocked) | Problem report | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| VS-FI-01 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-02 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-03 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-04 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-05 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-06 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-07 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-08 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-09 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-10 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-11 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-12 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-13 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-14 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-15 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-16 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-17 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-18 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-19 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-20 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-21 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-22 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-23 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-24 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-25 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-26 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-27 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-28 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-29 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-30 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-31 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |
| VS-FI-32 | — | — | — | — | — | — | — | — | **Not yet executed** | — | — |

Summary (to complete after execution): cases passed / failed / known GAP / blocked; mechanisms whose timing does not meet the FTTI; diagnostic coverage observations handed to [WP-H-04](../04-hardware/WP-H-04-hardware-metrics.md); open problem reports.

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Build fault-injection support: bench CAN fault generator, fault-injection firmware build (documented configuration item), closed-course test host build. The fault-injection firmware build follows WP-P-01 §7.1 (DQ-125 A) | Test lead | G4 |
| OI-2 | Run the opendbc safety tests in fork CI with release defines (GAP-39, GAP-41) so U-level cases produce LionDriver evidence. CI part done 2026-10-12 (`safety.yaml`); release defines open (GAP-41) | SW lead | G3 |
| OI-3 | Extend `test_fuzzy.py` to the excluded safety-relevant processes, or document why each cannot be fuzzed | SW lead | G3 |
| OI-4 | Confirm FTTI and budgets (WP-S-04) and update §4 | Safety engineer | G2 |
| OI-5 | **Closed 2026-10-19 (DQ-085, option B):** no spare is bought; VS-FI-07 (SPI overflow) runs on the reference device, which is reflashed and rechecked afterwards (§5.2) | Test lead | G4 |
| OI-6 | Add fault-injection cases for the eight System FMEA causes of §6 that came from WP-A-04 v0.2: SFM-016.C2 (envelope blocking with stale `pandaStates`), SFM-026.C1 (hung UI render loop), SFM-026.C2 (stalled or muted audio), SFM-009.C4 (unannounced deceleration), SFM-009.C1 (stale FCW inputs), SFM-029.C6 (TX burst), SFM-033.C6 (camera-side bus fault), SFM-033.C2 (block-list entry). IDs follow DQ-127 since v0.12 | Test lead | G4 |
