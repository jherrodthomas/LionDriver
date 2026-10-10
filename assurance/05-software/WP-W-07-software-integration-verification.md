# WP-W-07 Software Integration and Verification Specification and Report

| Field | Value |
|---|---|
| Work product | WP-W-07 Software integration and verification specification and report |
| Standard reference | ISO 26262-6:2018 §10 (software integration and verification: integration steps, methods, test-case derivation, coverage at architectural level, test environment); ISO 26262-8:2018 §9; ASPICE 4.0 SWE.5 |
| Version | 0.1 |
| Status | Draft (specification); results section **Not yet executed** |
| ASIL / scope | Envelope software (E-03): B‡ (ASIL C until SG-01 re-rating); host↔panda software interface: QM (B-sup) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document specifies how the software units of [WP-W-05](WP-W-05-software-unit-design.md) are integrated into the components and the embedded software of [WP-W-03](WP-W-03-software-architecture.md), and how the integrated software is verified against the architecture and the SWSRs of [WP-W-02](WP-W-02-software-safety-requirements.md). It ends where system integration of [WP-S-08](../03-system/WP-S-08-system-integration-test.md) starts (S-08 levels I-1…I-4). Embedded software testing on the target in a representative environment is in [WP-W-08](WP-W-08-embedded-software-testing.md).

**No LionDriver integration test has been executed.** Upstream CI and comma's device farm results are not LionDriver evidence (GAP-30, GAP-39).

## 2. Integration strategy

| Step | Name | What is integrated | Environment | Purpose |
|---|---|---|---|---|
| SWI-1 | Envelope on host | U-SAF-CORE + U-SAF-TOY + U-SAF-LAT + U-SAF-LONG + U-SAF-HELP as `libsafety.so` (`opendbc_repo/opendbc/safety/tests/libsafety/`) | Host x86-64, release configuration (ENV-H-REL of WP-W-06) | Hook sequences across units: RX → authority → TX; mode change; tick |
| SWI-2 | Firmware comms on host | SWI-1 + U-PND-COMMS + U-PND-SPI (protocol layer) + U-PND-FDCAN queue logic via `panda/tests/libpanda` (`panda.c`) | Host | Control requests, CAN stream packing, queues, `can_send` → TX hook |
| SWI-3 | Firmware on target | Complete release firmware (bootstub + application) on the STM32H7 of the reference device or a bare panda | Bench: target + CAN interfaces + scripted SPI/USB host (`panda` Python library) (ENV-T) | Interrupt interplay, timing, resources, drivers, fault injection |
| SWI-4 | Host software ↔ firmware | SWI-3 + `pandad` (C++), `card` with recorded or scripted `carControl` | Bench with SoC or Linux PC running `pandad` | SPI protocol both sides, heartbeat, sendcan age, health → `pandaStates` → `selfdrived` reactions |

Order: SWI-1 → SWI-2 → SWI-3 → SWI-4. Each step starts only when the previous one has passed for the same baseline. SWI-3 and SWI-4 need the HIL bench (D-04, WP-W-08 §3).

Integration approach: bottom-up along the call tree of WP-W-03 §5.3. Stubs: microsecond timer (`set_timer` in `libsafety`), FDCAN registers (libpanda fake), SPI DMA (host harness).

## 3. Methods and coverage

| Method | Applied to | Notes |
|---|---|---|
| Requirements-based test | every envelope SWSR with IT in its verification column | `@req` tags (WP-P-06 §6) |
| Interface test | SI-01…SI-13 of WP-W-03 §3.3 | all parameters at boundaries |
| Fault injection test | SPI corruption, length overrun, queue overflow, ISR load, stale/replayed transfers, mode commands | SW level; HW-level FI in WP-W-08 and [WP-V-05](../06-validation/WP-V-05-fault-injection.md) |
| Resource usage evaluation | stack, RAM, CPU load, ISR latency | target only (SWI-3) |
| Back-to-back | host vs target hook results on same vectors | shared with WP-W-06 VS-UV-20 |
| Drive-log replay | `opendbc_repo/opendbc/safety/tests/safety_replay/replay_drive.py` on fork-owned Corolla logs | detects false RX faults and blocked TX on real data |

Derivation: analysis of requirements and interfaces, equivalence classes, boundary values, error guessing from [WP-W-04](WP-W-04-software-safety-analysis.md) SWF/SDF rows.

Architectural coverage target: **100 % function coverage** of the E-03 units in the release image and **100 % call coverage** of the interfaces SI-01…SI-12, measured on SWI-1/SWI-2 with gcov; any uncovered function needs a justification (dead code from other brand modes is listed separately, WP-W-03 OI-2).

## 4. Existing assets

| Asset | Path | Use here | Limitation |
|---|---|---|---|
| `libsafety` harness | `opendbc_repo/opendbc/safety/tests/libsafety/{safety.c, libsafety_py.py}` | SWI-1 driver | Built with `ALLOW_DEBUG` by default (GAP-41) |
| Safety replay | `opendbc_repo/opendbc/safety/tests/safety_replay/replay_drive.py` | SWI-1 replay (VS-SWI-18) | Needs fork-owned logs (WP-W-06 OI-9) |
| `libpanda` harness | `panda/tests/libpanda/{panda.c, SConscript, libpanda_py.py}`; `panda/tests/usbprotocol/test_comms.py` (5 tests) | SWI-2 | Covers packing only |
| panda HITL tests | `panda/tests/hitl/test_1…9_*.py` (e.g. `test_5_spi.py`: bad header/checksum; `test_6_safety.py`: NOOUTPUT only; `test_4_can_loopback.py`) | SWI-3 starting point | Need comma jigs and Jenkins (GAP-30) |
| Process replay | `openpilot/selfdrive/test/process_replay/{process_replay.py, test_processes.py}` (card, controlsd, selfdrived, …) | SWI-4 host-side regression | Reference logs from comma (D-03) |
| opendbc car tests | `opendbc_repo/opendbc/car/tests/test_models.py` (`test_panda_safety_carstate`) | host vs envelope decoding | Route data from comma |

## 5. Integration test specification (VS-SWI)

Status of all: Specified, not implemented. Env: SWI step.

| ID | Objective | SWSRs | Env | Method / injected condition | Pass criterion |
|---|---|---|---|---|---|
| VS-SWI-01 | Actuation path across units: SoC frame → TX hook → limits → accept/reject; lateral and longitudinal; substitute zero-torque frame after rejection | 101–109, 201–207 | SWI-1, SWI-2 | Sequences at limit ± 1 through `can_send`; check queue content | Accepted frames unchanged in queue; rejected frames not in queue; substitute frame present (once implemented); authority revoked on violation |
| VS-SWI-02 | Engagement chain: RX frames (`0x1D2`, `0x226`, `0xAA`, `0x260`) → authority → TX acceptance | 301–306, 311 | SWI-1 | All transitions of WP-W-05 §5.2 driven through RX hook, TX checked after each | Every transition observable in TX acceptance in the next call |
| VS-SWI-03 | RX check integration: forwarding before RX validation, checksum failure, quality flag, whitelisting | 402, 406, 704 | SWI-2, SWI-3 | Corrupted frames on bus 0 and 2 | Corrupted frame forwarded per rules but no authority; reason reported |
| VS-SWI-04 | RX timeout through the periodic task | 401, 401a, 306 | SWI-1 (timer stub), SWI-3 | Stop each RX message at random phase | Detection ≤ 5 periods + task period; today expected to **fail** |
| VS-SWI-05 | Heartbeat path `0xf3` → tick/safety task | 307, 407, 409, 510 | SWI-2, SWI-3 | Stop heartbeat; send `engaged=0`; frozen loop counter | Revocation ≤ 0.3 s; SILENT ≤ 2 s; today expected to fail |
| VS-SWI-06 | Command freshness | 408, 109a | SWI-3 | Stop `0x2E4`/`0x343` while heartbeat continues | Revocation at 50/100 ms; zero frames emitted |
| VS-SWI-07 | SPI corruption | 410, 410a, 410b, 413 | SWI-2, SWI-3 | Bit flips in header, data, CAN packets; replayed, dropped and reordered transfers; DMA error flags | Every corrupted transfer NACKed/discarded; no frame from a corrupted transfer reaches the TX hook; error burst revokes |
| VS-SWI-08 | SPI length and index bounds (fuzz) | 412, 412a, 412b | SWI-2, SWI-3 | Header lengths 0…65535; `0xe8` param 0…65535; random CAN streams | No write outside buffers (canary/guard check on target, ASan on host); NACK for out-of-range |
| VS-SWI-09 | Forwarding and relay malfunction interplay | 704, 705, 707, 710, 506a | SWI-1, SWI-3 | `check_relay` messages on bus 0 before/after 1 s; `0xdc` after latch | Latch set; TX and forwarding blocked; latch survives mode change (target) |
| VS-SWI-10 | Mode-set sequence SILENT → NOOUTPUT → ELM327 → TOYOTA/73, and lock | 311, 512, 104a | SWI-2, SWI-3 | Valid sequence; invalid modes/params; requests after TOYOTA | Valid sequence reaches TOYOTA with state reset; others rejected and reported |
| VS-SWI-11 | Queue overflow | 707, 502b | SWI-2, SWI-3 | Flood `sendcan`; SoC stops reading `rx_q`; camera-side burst | Overflow counted and treated as fault per WP-W-05 §6.1; forwarded PCS frames not starved (measure) |
| VS-SWI-12 | ISR load and priority scheme | 401a, 501, 502b, 519 | SWI-3 | CAN at 100 % bus load on 3 buses + max SPI rate | Safety task period held; interrupt-rate fault → SS-S; no watchdog reset under nominal worst case |
| VS-SWI-13 | Fault reaction integration | 502, 502a, 503a, 516 | SWI-3 | Trigger each fault source of WP-W-05 §6.1 (debug build hooks) | SS-S ≤ 0.1 s; siren per SWSR-516 |
| VS-SWI-14 | Control-request gating in car mode | 511a, 513 | SWI-2, SWI-3 | Every request of WP-W-05 UN-21 table in TOYOTA mode | Gated requests have no effect |
| VS-SWI-15 | Resource usage | WP-W-03 §7 | SWI-3 | Map file, stack painting, `interrupt_load`, cycle counter around hooks | Stack margin ≥ 20 %; RAM within regions; hook WCET recorded; TX path latency recorded |
| VS-SWI-16 | `pandad` ↔ firmware interface | 409h, 410h, 414h, 514h, 619 | SWI-4 | Normal traffic; delayed `sendcan`; debug firmware | Loop counter advancing; CRC/sequence accepted; old messages dropped at 20 ms; no engagement with debug FW |
| VS-SWI-17 | Host reaction chain: health → `pandaStates` → `selfdrived` | 307h, 601, 615, 606 | SWI-4 | Inject each panda flag/reason code | Immediate disable ≤ 0.2 s, alert class correct |
| VS-SWI-19 | Per-ID TX rate supervision and TX read-back | 517, 518 | SWI-1, SWI-3 | `0x2E4` at 2× rate; corrupt frame after TX hook (debug hook) | Excess frames rejected, revocation on persistence; corruption detected ≤ 2 frames |
| VS-SWI-18 | Replay of fork-owned reference drives through the release `libsafety` | 401–406, 101–207 | SWI-1 | `replay_drive.py` with mode TOYOTA, param 73 | Zero RX invalid and zero blocked `0x2E4`/`0x343` on nominal drives; expected detections on fault-injected copies |

## 6. Test environment

| ID | Description | Status |
|---|---|---|
| ENV-SWI-H | Host Linux x86-64, `libsafety` and `libpanda` release builds, gcov, ASan/UBSan | Partly exists (debug build only) |
| ENV-SWI-T | HIL bench of WP-W-08 §3 with debug-probe access (SWD) for fault hooks and cycle counter | Not available (D-04) |
| ENV-SWI-S | ENV-SWI-T + SoC or PC running `pandad` and scripted openpilot services | Not available |

Configuration of every run (superproject, opendbc, panda commit, build type, tool versions) is recorded per [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md).

## 7. Pass/fail and regression

- All VS-SWI on the release configuration; a debug build is used only to inject faults that cannot be injected otherwise, and the test record states it.
- Any SR-A change re-runs SWI-1/SWI-2 in CI; SWI-3/SWI-4 at each release candidate.
- Failures expected at the baseline (VS-SWI-04, 05, 06, 08, 13, 14) are tracked as problem reports ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)), not waived.

## 8. Integration and verification report (template)

**Status: Not yet executed.**

| Field | Value |
|---|---|
| Baseline (superproject / opendbc / panda) | Not yet executed |
| Build type and image hash | Not yet executed |
| Environments used | Not yet executed |
| Tool versions | Not yet executed |

| VS ID | Step | Cases | Passed | Failed | Not run | Result | Evidence |
|---|---|---|---|---|---|---|---|
| VS-SWI-01 … VS-SWI-19 | — | — | — | — | — | Not yet executed | — |

| Function / call coverage (SWI-1/2) | Not yet executed |
|---|---|
| Resource usage results | Not yet executed |
| Deviations | Not yet executed |
| Problem reports | Not yet executed |
| Verdict | Not yet executed |

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Build `libsafety` and `libpanda` in the release configuration for SWI-1/2 (GAP-41) | Maintainer | G3 |
| OI-2 | Extend `libpanda` to cover `spi_rx_done` and `comms_control_handler` with fake DMA | Maintainer | G3 |
| OI-3 | Provide fork-owned Corolla drive logs for VS-SWI-18 | Maintainer | G4 |
| OI-4 | Define fault-injection hooks for SWI-3 that do not exist in the release image (debug-probe based preferred) | SW lead | G4 |
| OI-5 | Align VS-SWI with WP-S-08 I-1/I-2 to avoid duplicate cases | Safety engineer | G4 |
