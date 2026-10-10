# WP-W-08 Testing of the Embedded Software

| Field | Value |
|---|---|
| Work product | WP-W-08 Testing of the embedded software (software qualification, HIL) |
| Standard reference | ISO 26262-6:2018 §11 (testing of the embedded software: test environments, methods, test-case derivation); ISO 26262-8:2018 §9; ASPICE 4.0 SWE.6 |
| Version | 0.1 |
| Status | Draft (specification); results section **Not yet executed** |
| ASIL / scope | Embedded envelope software on the STM32H7 (E-03): B‡ (ASIL D until SG-01 re-rating; C for SG-03…SG-05) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document specifies tests that show the embedded software, as built for release and running on the target MCU in a representative environment, meets the SWSRs of [WP-W-02](WP-W-02-software-safety-requirements.md). It is the software qualification step after integration ([WP-W-07](WP-W-07-software-integration-verification.md)) and before system integration ([WP-S-08](../03-system/WP-S-08-system-integration-test.md)). It also covers the SPI integrity tests that [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) assigns here for HWSR-401.

**No test in this document has been executed.** LionDriver has no HIL bench (GAP-30); building one is decision D-04 ([WP-M-01](../01-management/WP-M-01-assurance-strategy.md)).

## 2. Test strategy

| Aspect | Decision |
|---|---|
| Object under test | Release-signed firmware (bootstub + application, no `ALLOW_DEBUG`) of the tagged baseline, image hash recorded |
| Target | STM32H7 panda of the reference device hardware revision (WP-C-01), or a bare panda of the same MCU and board type where the device is not needed |
| Environment | HIL bench (§3), representative for CAN traffic, supply and timing; vehicle not included |
| Methods | Requirements-based test; fault injection; resource and timing measurement; back-to-back against the host model (VS-UV-20) |
| Derivation | Requirements analysis, equivalence classes, boundary values (limit ± 1 raw, timing thresholds ± one task period), error guessing from [WP-W-04](WP-W-04-software-safety-analysis.md) |
| Coverage | Every envelope SWSR with HIL in its verification column has ≥ 1 VS-SWQ case (§5, §6) |

## 3. Test environment (HIL bench, D-04)

| Item | Description | Representativeness argument |
|---|---|---|
| DUT | Reference device (SoC + panda) or bare panda, release firmware | Same MCU, clocks, peripherals, firmware image |
| CAN | 3 channels to bus 0, 1, 2 via harness-equivalent wiring; CAN interfaces able to replay at full rate, inject errors (stuff, CRC), hold dominant, measure timestamps ≤ 10 µs | Toyota 500 kbit/s classic CAN |
| Vehicle simulation | Replay of fork-owned Corolla logs; closed-loop plant for `0x260` (EPS torque response to `0x2E4`), `0xAA`, `0x1D2`, `0x226`, `0x262`, `0x1D3`, `0xB4` (as in S-08 I-3) | Message set and rates of the reference vehicle |
| SoC side | Scripted host using the `panda` Python library over SPI (or `pandad` for S-08) with a fault-injecting SPI layer | Same SPI protocol |
| Relay | Harness relay or equivalent load on the relay outputs; readback signal once added (HWSR-506a) | Same driver circuit |
| Supply | Programmable supply 9–16 V with dips and ramps | Vehicle supply range |
| Debug | SWD probe for cycle counter, stack painting, fault-injection breakpoints (non-intrusive where possible) | Probe effects recorded |
| Siren | Audio capture | TSR-516 timing |
| Thermal | Thermal chamber or heat gun for DTS tests (optional) | |

Existing upstream assets usable after porting: `panda/tests/hitl/test_*.py` (health, SPI bad header/checksum, CAN loopback, harness) — they need comma jigs today.

## 4. Pass/fail rules

- A case passes only with the release image. A case that needs a debug hook is marked and repeated with the release image wherever the hook is not needed.
- Timing results report the worst observed value over ≥ 100 repetitions with randomised phase relative to the tick.
- Cases expected to fail at the baseline are run and recorded as failures with problem reports.

## 5. Test specification (VS-SWQ)

Status of all: Specified, not implemented.

| ID | Objective | SWSRs | Stimulus | Pass criterion |
|---|---|---|---|---|
| VS-SWQ-01 | Torque magnitude limit on target | 101, 101a, 102 | `0x2E4` with \|τ\| at τ_max − 1, τ_max, τ_max + 1 at speeds over the table | Frames > τ_max not on bus 0; others unchanged |
| VS-SWQ-02 | Rate and RT window | 103, 103a | Ramps at Δ, Δ + 1; RT window sweeps | Rejections exactly at limit + 1 |
| VS-SWQ-03 | Measured-torque tracking with plant | 104, 104a | Plant EPS torque lagging command | Rejection at meas + 351 raw |
| VS-SWQ-04 | Gating, steer-request rules, latch and safe-state frames | 105–109, 109a | Requests without authority; cut patterns; violation while engaged | No actuation without authority; authority latched off after violation; zero-torque frame within one period (once implemented); today SWSR-105, 108, 109 expected to fail |
| VS-SWQ-05 | Longitudinal limits and fields | 201–207 | Accel boundaries, steps, field variations, gas pressed | As per SWSRs; jerk and field checks expected to fail today |
| VS-SWQ-06 | Engagement and brake/gas | 301–306, 309, 311 | PCM edges, brake at standstill/moving, gas | Authority transitions per WP-W-05 §5.2 within the RX frame |
| VS-SWQ-07 | Driver override and heartbeat mismatch | 304, 304a, 307 | Plant driver torque; heartbeat `engaged=0` | Revocation timing per SWSRs (0.3 s for 307; expected fail today: ≈3 s) |
| VS-SWQ-08 | RX timeouts | 401, 401a, 406 | Remove each RX message at random phase | Detection ≤ 5 periods + task period; today 1–2 s (expected fail) |
| VS-SWQ-09 | RX plausibility | 402–405 | Corrupted checksums, 1.5× rate, frozen payload, disagreeing cross-signals | Each detected within its bound |
| VS-SWQ-10 | Heartbeat loss, SILENT, siren | 407, 409, 510, 516 | Stop heartbeat with ignition on/off; frozen loop counter | Revocation ≤ 0.3 s; SILENT ≤ 2 s; siren ≤ 0.5 s; today 3–5 s (expected fail) |
| VS-SWQ-11 | Command stall | 408, 109a | Stop `0x2E4`/`0x343` with heartbeat alive | Revocation 50/100 ms; zero frames |
| VS-SWQ-12 | SPI integrity and bounds on target (also HWSR-401) | 410, 410a, 410b, 411, 412, 412a, 412b, 413 | Corrupted, replayed, reordered, oversized transfers via fault-injecting SPI host | No effect from corrupted transfer; no memory corruption (stack/guard canaries via SWD); error burst revokes |
| VS-SWQ-13 | EPS status monitoring | 110 | Plant reports LKA_STATE fault codes; `0x262` loss | Lateral revocation within one frame / timeout |
| VS-SWQ-14 | Watchdog and hang | 501, 501b, 502a | Halt main/tick/comms ISR via SWD; infinite loop in a handler; `assert_fatal` | MCU reset ≤ 0.2 s; relay released; CAN TX silent |
| VS-SWQ-15 | Fault reaction | 502, 502b, 503a, 503b, 504, 505, 508, 509 | Interrupt storm, register divergence, ECC event (if injectable), clock drift, supply ramp, bus-off, temperature | SS-S ≤ 0.1 s after detection, latch class per WP-W-05 §6.1 |
| VS-SWQ-16 | Start-up tests and image integrity | 503, 515, 502c | Corrupted image byte; failing relay readback; power-up observation of relay and transceivers | Relay never driven on failure; outputs safe from reset |
| VS-SWQ-17 | Configuration lock and request gating | 511a, 512, 512a, 513, 514 | All control requests in TOYOTA mode; non-reference `0xdc`; `0xd6` build type | Rejected as specified; build type "release" |
| VS-SWQ-18 | Bootstub signature | 511 | Tampered, debug-signed, truncated images | Not executed; soft flasher entered |
| VS-SWQ-19 | Relay readback, orientation, relay latch | 506, 506a, 506b, 701, 701a, 706, 710 | Relay stuck open/closed (simulated); harness flip/unplug while driven; `0xdc` after latch | Detection ≤ 0.3 s; SS-S; latch persists |
| VS-SWQ-20 | Host reaction to envelope reports (with `pandad` and `selfdrived`) | 307h, 514h, 601, 606, 615, 619, 620 | Each envelope reason code and flag | Immediate disable ≤ 0.2 s, take-over request ≤ 1 s |
| VS-SWQ-21 | Forwarding and PCS message rules | 704, 705, 707 | Camera-side traffic at full load; SoC sends PCS/DSU IDs | Forwarding latency ≤ bound (TSR-707); PCS/DSU IDs not transmitted from SoC |
| VS-SWQ-22 | Relay malfunction detection by traffic | 710 | `check_relay` IDs on car side | Latch and TX/forward block |
| VS-SWQ-23 | Resource usage and timing on target | WP-W-03 §7; 401a | Worst-case bus + SPI load | Stack margin ≥ 20 %; safety task period ≤ 20 ms; hook WCET and TX latency within WP-S-04 budgets |
| VS-SWQ-25 | TX read-back, per-ID TX rate, priority scheme | 517, 518, 519 | Corruption between TX hook and bus (SWD); SoC TX at 2× rate; worst-case IRQ load | Mismatch → SS-S ≤ 2 frames; excess rejected and revoked; safety-task latency within budget |
| VS-SWQ-24 | Endurance replay | all envelope | ≥ 10 h of fork-owned Corolla logs at real time, nominal | No false revocation, no watchdog reset, no fault flag |

## 6. SWSR coverage

| SWSR block | VS-SWQ |
|---|---|
| 101–110 | 01–04, 13 |
| 201–207 | 05 |
| 301–311 | 06, 07 |
| 401–406 | 08, 09 |
| 407–413 | 10–12 |
| 501–519 | 14–18, 23, 25, 10 (510, 516) |
| 701–710 | 19, 21, 22 |
| Host (SWSR-6xx, h-suffix) | 20 (others by host tests and WP-S-08) |

SWSRs whose only verification is review or analysis (e.g. SWSR-102a, 309, 605a) are not tested here.

## 7. Test report (template)

**Status: Not yet executed.**

| Field | Value |
|---|---|
| Firmware image hash and build type | Not yet executed |
| Baseline (superproject / opendbc / panda) | Not yet executed |
| Bench configuration and calibration | Not yet executed |
| Tool and script versions | Not yet executed |

| VS ID | Cases | Passed | Failed | Not run | Worst-case timing | Result | Evidence |
|---|---|---|---|---|---|---|---|
| VS-SWQ-01 … VS-SWQ-25 | — | — | — | — | — | Not yet executed | — |

| Deviations from specification | Not yet executed |
|---|---|
| Problem reports | Not yet executed |
| Verdict | Not yet executed |

## 8. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Build the HIL bench (D-04), including fault-injecting SPI host and plant model | Maintainer | G4 |
| OI-2 | Decide release-image-compatible fault-injection methods (SWD vs debug build) and document the representativeness argument | SW lead | G4 |
| OI-3 | Port `panda/tests/hitl` to the LionDriver bench without comma jigs | Maintainer | G4 |
| OI-4 | Fork-owned Corolla log set for VS-SWQ-24 and plant parameter identification | Maintainer | G4 |
| OI-5 | Agree split of cases with WP-S-08 (I-1) and WP-V-05 to avoid duplication | Safety engineer | G4 |
