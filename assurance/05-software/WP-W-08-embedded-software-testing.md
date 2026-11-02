# WP-W-08 Testing of the Embedded Software

| Field | Value |
|---|---|
| Work product | WP-W-08 Testing of the embedded software (software qualification, HIL) |
| Standard reference | ISO 26262-6:2018 §11 (testing of the embedded software: test environments, methods, test-case derivation); ISO 26262-8:2018 §9; ASPICE 4.0 SWE.6 |
| Version | 0.4.2 (RX timeout bound ≤ 0.162 s, was ≤ 0.16 s, as WP-S-04 v0.21 T-01 (161.5 ms: 5 periods of 30.3 ms plus one 10 ms task period); no requirement, budget or verdict changed; 2026-10-27). 0.4.1 (VS-SWQ-26: persistence 0.7 s, worst case 0.96 s, panda `bf8102a`, DQ-048; 2026-10-17). 0.4 (merge of PR #47 software alignment with the base; VS-SWQ-26 (EPS-fault siren) from the base; 2026-10-13). It carries PR #47's drafts, numbered 0.2–0.3 there: 0.3 ([RR-2026-009](reviews/RR-2026-009.md) F-24: host reaction moved from VS-SWQ-20 to WP-S-08 VS-SI-25; F-25: deviation D-1 recorded in §4; F-28: author); 0.2 (alignment pass: expected outcomes rechecked against the WP-W-02 baseline column at opendbc `7993399`, panda `8aa8671`; §6 coverage table rebuilt from §5; HIL tests in the pins listed; report template per [WP-M-14 §8.3](../01-management/WP-M-14-iso26262-6-implementation-specification.md#83-evidence-binding)). History on the base: 0.3 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.2 (verification status for the integrated envelope changes; 2026-10-12). 0.1 |
| Status | Draft (specification); results section **Not yet executed** |
| ASIL / scope | Embedded envelope software on the STM32H7 (E-03): B‡ (ASIL C until SG-01 re-rating) |
| Author | Assurance team (AI-assisted draft, Claude) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`); expected outcomes in §5 rechecked at `682f184` (opendbc `7993399`, panda `8aa8671`); HIL script status from the base's status update at `bf6ce8c` (opendbc `7993399`, panda `b790fca`) and panda `c33343b` |

## 1. Purpose and scope

This document specifies tests that show the embedded software, as built for release and running on the target MCU in a representative environment, meets the SWSRs of [WP-W-02](WP-W-02-software-safety-requirements.md). It is the software qualification step after integration ([WP-W-07](WP-W-07-software-integration-verification.md)) and before system integration ([WP-S-08](../03-system/WP-S-08-system-integration-test.md)). It also covers the SPI integrity tests that [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) assigns here for HWSR-401.

**No test in this document has been executed.** Six cases have HIL scripts (five in panda `b790fca`, VS-SWQ-10 in `c33343b`; §5), none of them run. LionDriver has no HIL bench (GAP-30); building one is decision D-04 ([WP-M-01](../01-management/WP-M-01-assurance-strategy.md)).

## 2. Test strategy

| Aspect | Decision |
|---|---|
| Object under test | Release-signed firmware (bootstub + application, no `ALLOW_DEBUG`) of the tagged baseline, image hash recorded |
| Target | STM32H7 panda of the reference device hardware revision (WP-C-01), or a bare panda of the same MCU and board type where the device is not needed |
| Environment | HIL bench (§3), representative for CAN traffic, supply and timing; vehicle not included |
| Methods | Requirements-based test; fault injection; resource and timing measurement; back-to-back against the host model (VS-UV-20) |
| Derivation | Requirements analysis, equivalence classes, boundary values (limit ± 1 raw, timing thresholds ± one task period), error guessing from [WP-W-04](WP-W-04-software-safety-analysis.md) |
| Coverage | Target: every envelope SWSR with HIL in its verification column has ≥ 1 VS-SWQ case (§5, §6). Not yet met: SWSR-108a, 516b, 711 and 711a have no case (OI-6) |

## 3. Test environment (HIL bench, D-04)

There is one HIL bench for hardware, software and system integration testing: the bench defined in [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) §2. It is built under [WP-M-03](../01-management/WP-M-03-project-plan.md) task 5.1 and must be ready by G3, because WP-M-03 phase P4 depends on "G3; HIL bench ready". The table below lists what the software qualification tests need from that bench, in addition to WP-H-06 §2.1; it does not define a second bench.

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

LionDriver HIL tests in the panda pin (written, **not run on hardware**; [hil-bench/](hil-bench/README.md) §7): `test_10_hw_watchdog.py` (VS-SWQ-14), `test_11_reference_lock.py` (VS-SWQ-17), `test_12_rx_timeout.py` (VS-SWQ-08), `test_13_eps_fault.py` (VS-SWQ-13), `test_14_tx_rate.py` (VS-SWQ-25), `test_15_heartbeat_siren.py` (VS-SWQ-10, panda `c33343b`). Source: the change records in [`07-supporting/impact/`](../07-supporting/impact/README.md).

The staged build plan, parts list and the first bench test (hardware watchdog) are in [hil-bench/](hil-bench/README.md).

## 4. Pass/fail rules

- A case passes only with the release image. A case that needs a debug hook is marked and repeated with the release image wherever the hook is not needed.
- Timing results report the worst observed value over ≥ 100 repetitions with randomised phase relative to the tick.
- Cases expected to fail at the baseline are run and recorded as failures with problem reports.
- **Deviation D-1 (watchdog reset time).** SWSR-501 and VS-SWQ-14 require an MCU reset ≤ 0.1 s after a stall (SG-07 FDTI). Deviation D-1 of the [watchdog change record](../07-supporting/impact/change-2026-10-12-panda-hw-watchdog.md) accepts ≤ 0.2 s (SG-01 bound) as interim. The bench reports every watchdog result against both bounds: 0.2 s decides pass/fail while D-1 stands, and 0.1 s is reported so the shortfall is measured. D-1 is a maintainer decision, not a review (WP-M-06).

## 5. Test specification (VS-SWQ)

Status (2026-10-12): specified, not implemented, except five cases with HIL scripts in panda `b790fca` that are implemented and **not run** (bench not built, GAP-30): VS-SWQ-08 → `panda/tests/hitl/test_12_rx_timeout.py`, VS-SWQ-13 → `test_13_eps_fault.py`, VS-SWQ-14 → `test_10_hw_watchdog.py`, VS-SWQ-17 → `test_11_reference_lock.py`, VS-SWQ-25 (518 part) → `test_14_tx_rate.py`. `test_11`, `test_13` and `test_14` need a reference build; `test_10` needs a fault-injection debug build ([hil-bench/](hil-bench/README.md) §5.5, §7). *2026-10-13:* a sixth, VS-SWQ-10 (revocation and heartbeat-loss siren) → `test_15_heartbeat_siren.py` (panda `c33343b`), implemented and **not run**; it needs a reference build for the car simulation and an ear (or microphone) check of the siren.

| ID | Objective | SWSRs | Stimulus | Pass criterion |
|---|---|---|---|---|
| VS-SWQ-01 | Torque magnitude limit on target | 101, 101a, 102 | `0x2E4` with \|τ\| at τ_max − 1, τ_max, τ_max + 1 at speeds over the table | Frames > τ_max not on bus 0; others unchanged |
| VS-SWQ-02 | Rate and RT window | 103, 103a | Ramps at Δ, Δ + 1; RT window sweeps | Rejections exactly at limit + 1 |
| VS-SWQ-03 | Measured-torque tracking with plant | 104, 104a | Plant EPS torque lagging command | Rejection at meas + 351 raw |
| VS-SWQ-04 | Gating, steer-request rules, latch and safe-state frames | 105–109, 109a | Requests without authority; cut patterns; violation while engaged | No actuation without authority; authority latched off after violation; zero-torque frame within one period (once implemented); today SWSR-105, 108, 109 expected to fail |
| VS-SWQ-05 | Longitudinal limits and fields | 201–207 | Accel boundaries, steps, field variations, gas pressed | As per SWSRs; jerk and field checks expected to fail today |
| VS-SWQ-06 | Engagement and brake/gas | 301–306, 309, 311 | PCM edges, brake at standstill/moving, gas | Authority transitions per WP-W-05 §5.2 within the RX frame |
| VS-SWQ-07 | Driver override and heartbeat mismatch | 304, 304a, 307 | Plant driver torque; heartbeat `engaged=0` | Revocation timing per SWSRs (0.3 s for 307; expected fail today: ≈3 s) |
| VS-SWQ-08 | RX timeouts | 401, 401a, 406 | Remove each RX message at random phase | Detection ≤ 5 periods + one 10 ms task period (SWSR-401 met for the Toyota RX checks, opendbc `aff4033`, `98404a4`; not verified on hardware), worst case ≤ 0.162 s (`0x1D2`). HIL `test_12_rx_timeout.py`, not run |
| VS-SWQ-09 | RX plausibility | 402–405 | Corrupted checksums, 1.5× rate, frozen payload, disagreeing cross-signals | Each detected within its bound |
| VS-SWQ-10 | Heartbeat loss, SILENT, siren | 407, 409, 510, 516 | Stop heartbeat with ignition on/off; frozen loop counter | Revocation ≤ 0.3 s (SWSR-407 implemented, panda `c2e5d93`); SILENT ≤ 2 s (510) not implemented (SILENT after 3–5 s), expected to **fail**; siren ≤ 0.5 s (516): *2026-10-13:* siren at the revocation when authority was granted, ≤ 0.26 s after it (≈ 0.56 s after the last heartbeat), all builds (`heartbeat_siren.h`, panda `c33343b`; host test `panda/tests/heartbeat_siren`; HIL `test_15_heartbeat_siren.py` times the revocation, siren by ear; not run); the 1 Hz siren after 4–5 s unchanged |
| VS-SWQ-11 | Command stall | 408, 109a | Stop `0x2E4`/`0x343` with heartbeat alive | Revocation 50/100 ms; zero frames |
| VS-SWQ-12 | SPI integrity and bounds on target (also HWSR-401) | 410, 410a, 410b, 411, 412, 412a, 412b, 413 | Corrupted, replayed, reordered, oversized transfers via fault-injecting SPI host | No effect from corrupted transfer; no memory corruption (stack/guard canaries via SWD); error burst revokes |
| VS-SWQ-13 | EPS status monitoring | 110 | Plant reports LKA_STATE fault codes; `0x262` loss | Lateral revocation within one frame / timeout. Reference build: HIL `test_13_eps_fault.py`, not run |
| VS-SWQ-14 | Watchdog and hang | 501, 501b, 502a | Halt main/tick/comms ISR via SWD; infinite loop in a handler; `assert_fatal` | MCU reset ≤ 0.1 s (0.2 s accepted as interim, deviation D-1 of the [watchdog change record](../07-supporting/impact/change-2026-10-12-panda-hw-watchdog.md)); relay released; CAN TX silent. HIL `test_10_hw_watchdog.py` (fault-injection debug build), not run |
| VS-SWQ-15 | Fault reaction | 502, 502b, 503a, 503b, 504, 505, 508, 509 | Interrupt storm, register divergence, ECC event (if injectable), clock drift, supply ramp, bus-off, temperature | SS-S ≤ 0.1 s after detection, latch class per WP-W-05 §6.1 |
| VS-SWQ-16 | Start-up tests and image integrity | 503, 515, 502c | Corrupted image byte; failing relay readback; power-up observation of relay and transceivers | Relay never driven on failure; outputs safe from reset |
| VS-SWQ-17 | Configuration lock and request gating | 511a, 512, 512a, 513, 514 | All control requests in TOYOTA mode; non-reference `0xdc`; `0xd6` build type | Rejected as specified; build type "release". Reference build: HIL `test_11_reference_lock.py`, not run |
| VS-SWQ-18 | Bootstub signature | 511 | Tampered, debug-signed, truncated images | Tampered image never runs; soft flasher entered |
| VS-SWQ-19 | Relay readback, orientation, relay latch | 506, 506a, 506b, 701, 701a, 706, 710 | Relay stuck open/closed (simulated); harness flip/unplug while driven; `0xdc` after latch | Detection ≤ 0.3 s; SS-S; latch persists |
| VS-SWQ-20 | Envelope reports every revocation cause and fault in the health packet | 108a | Trigger each revocation cause and fault of SWSR-108a on the bench; read `0xd2` health | Each cause produces its distinct code or flag within one health period (SWSR-108a). The host reaction to these reports is WP-S-08 VS-SI-25 |
| VS-SWQ-21 | Forwarding and PCS message rules | 704, 705, 707 | Camera-side traffic at full load; SoC sends PCS/DSU IDs | Forwarding latency ≤ bound (TSR-707); PCS/DSU IDs not transmitted from SoC |
| VS-SWQ-22 | Relay malfunction detection by traffic | 710 | `check_relay` IDs on car side | Latch and TX/forward block |
| VS-SWQ-23 | Resource usage and timing on target | WP-W-03 §7; 401a | Worst-case bus + SPI load | Stack margin ≥ 20 %; safety task period ≤ 20 ms; hook WCET and TX latency within WP-S-04 budgets |
| VS-SWQ-24 | Endurance replay | all envelope | ≥ 10 h of fork-owned Corolla logs at real time, nominal | No false revocation, no watchdog reset, no fault flag |
| VS-SWQ-25 | TX read-back, per-ID TX rate, priority scheme | 517, 518, 519 | Corruption between TX hook and bus (SWD); SoC TX at 2× rate; worst-case IRQ load | Mismatch → SS-S ≤ 2 frames; excess rejected and revoked; safety-task latency within budget. 518 (reference build): HIL `test_14_tx_rate.py`, not run; 517: not implemented |
| VS-SWQ-26 | EPS-fault siren | 516(b) | EPS fault (`LKA_STATE` fault code) persisting 0.7 s once seen while engaged (DQ-048, panda `bf8102a`) | Siren ≥ 3 s (TSR-516(b)), worst case ≈ 0.96 s after the fault onset (WP-S-04 T-28). Host test `panda/tests/eps_fault_siren`; no HIL script (the siren state is not in the health packet: audible or scope check) |

## 6. SWSR coverage

| SWSR block | VS-SWQ |
|---|---|
| 101–110 | 01–04, 13. No case: 108a |
| 201–207 | 05 |
| 301, 302, 304–307, 309, 311 | 06, 07 |
| 401–406 | 08, 09 |
| 407–413 | 10–12 |
| 501–519 | 14–17, 19 (506, 506a, 506b), 23, 25, 26 (516 (b)), 10 (510, 516). No case: 503c, 504a, 505a, 507, 507a, 508a, 516a, 516b |
| 701–711 | 19 (701, 701a, 706, 710), 21, 22. No case: 711, 711a |
| Host (SWSR-6xx, h-suffix) | None here; host reaction to envelope reports is WP-S-08 VS-SI-27, other host SWSRs by host tests and WP-S-08 |

SWSRs without a case are listed in OI-6; this table is derived from §5 and is the one to keep in step with WP-W-02 §13.3.

SWSRs whose only verification is review or analysis (e.g. SWSR-102a, 605a) are not tested here. SWSR-309 (R, A) is exercised by VS-SWQ-06 as additional cover.

### 6.1 Split with WP-S-08 and WP-V-05

Three documents test the same envelope faults on the same bench: this one (VS-SWQ, against SWSRs), [WP-S-08](../03-system/WP-S-08-system-integration-test.md) (VS-SI, against TSRs and interfaces) and [WP-V-05](../06-validation/WP-V-05-fault-injection.md) (VS-FI, against the safety mechanisms of the safety analyses). WP-S-08 step I-1 uses the setup of this document: release firmware on the reference device MCU with a scripted host instead of openpilot. Each case is run once per setup and credited to every document that needs it:

1. **Procedure.** WP-V-05 is the only source of fault-injection procedures: fault model, injection method and fault-injection builds. A VS-SWQ or VS-SI case that injects a fault cites the VS-FI case and does not restate the procedure.
2. **Run at I-1.** A case in the table below is run and reported once, here, in the WP-W-08 report (§7). The VS-SI case at step I-1 and the H-level release-firmware VS-FI case cite that report entry and are not re-run. The credit holds only when the run used the reference device, not a bare panda (§2).
3. **Pass criteria.** A shared run is judged against every mapped criterion: the SWSR here, the TSR, GC-1 and GC-2 of WP-S-08 §5, and the FTTI budget of WP-V-05 §4. A run that meets one and fails another is a failure in all three.
4. **What the others add.** WP-S-08 runs only the steps that need more than the scripted host: I-2 (openpilot on the SoC), I-3 (plant model) and I-4 (vehicle). WP-V-05 runs its U, S and V levels, its fault-injection-firmware cases (§7 step 4) and H-level cases with no VS-SWQ counterpart.

| Fault or behaviour | Run at I-1, reported here | WP-S-08 adds | WP-V-05 procedure |
|---|---|---|---|
| Out-of-limit lateral and longitudinal commands | VS-SWQ-01…05 | VS-SI-15, -16 at I-3 | VS-FI-14 (also U and V) |
| Engagement, brake and gas, driver override | VS-SWQ-06, -07 | VS-SI-01, -02, -03 at I-2, I-3 or I-4; VS-SI-04 covered at I-1 | — (not a fault) |
| RX timeout | VS-SWQ-08 | VS-SI-12 at I-3 | VS-FI-04 |
| RX corruption, stuck, replayed and implausible frames | VS-SWQ-09 | VS-SI-13 at I-3; VS-SI-14 covered at I-1 | VS-FI-01, -02, -03, -05 |
| Heartbeat loss and mismatch | VS-SWQ-07, -10 | VS-SI-05 at I-2; VS-SI-06 covered at I-1 | VS-FI-10 |
| Command stall and stale command stream | VS-SWQ-11 | VS-SI-10 covered at I-1 | VS-FI-08 |
| SPI corruption and bounds | VS-SWQ-12 | VS-SI-09 at I-2 (real `pandad`) | VS-FI-06, -07 |
| Configuration commands in car mode | VS-SWQ-17 | VS-SI-07, -08 covered at I-1 | VS-FI-11 |
| TX flooding and per-ID TX rate | VS-SWQ-25 | VS-SI-11 covered at I-1 | VS-FI-19 |
| Relay faults, harness orientation and relay latch | VS-SWQ-19, -22 | VS-SI-19 covered at I-1 | VS-FI-21, -28 |
| PCS forwarding and masquerade | VS-SWQ-21 | VS-SI-20 at I-2 and I-4; VS-SI-21 covered at I-1 | VS-FI-24 |
| Host reaction to envelope reports and SoC process faults | VS-SWQ-20 | VS-SI-17, -22, -23 at I-2 and I-3 | VS-FI-09, -12, -13 (S level) |
| Watchdog and hang | VS-SWQ-14 | — | VS-FI-17 (fault-injection firmware) |
| MCU fault reactions (memory, interrupt storm, clock, supply, bus-off, temperature) | VS-SWQ-15 | — | VS-FI-15, -18, -19, -20, -22, -26 |
| Image integrity and bootstub | VS-SWQ-16, -18 | — | VS-FI-29 |
| MCU reset during engagement; relay state per mode | — | VS-SI-25, VS-SI-18 at I-1 and later steps (run there) | VS-FI-16 |

Hardware integration cases of [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) (VS-HW) are outside this split; WP-V-05 already cites them as assets.

## 7. Test report (template)

**Status: Not yet executed.**

| Field | Value |
|---|---|
| Firmware image hash and build type | Not yet executed |
| Baseline (superproject / opendbc / panda) | Not yet executed |
| Bench configuration and calibration | Not yet executed |
| Tool and script versions | Not yet executed |
| Build manifest ID | Not yet executed |
| Vehicle configuration ID (e.g. CFG-001) | Not yet executed |
| Bench record ID (D-04 stage, calibration) | Not yet executed |
| Execution date, raw artifact location | Not yet executed |
| Reviewer, independence, review state | Not yet executed |

| VS ID | SWSR IDs | Cases | Passed | Failed | Not run | Worst-case timing | Result | Anomalies | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| VS-SWQ-01 … VS-SWQ-26 | — | — | — | — | — | — | Not yet executed | — | — |

Each row also names the VS-SI and VS-FI cases it is credited to (§6.1).

| Deviations from specification | Not yet executed |
|---|---|
| Problem reports | Not yet executed |
| Verdict | Not yet executed |

## 8. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Build the HIL bench (D-04), including fault-injecting SPI host and plant model. One bench with WP-H-06 §2; tracked as WP-H-06 OI-1 and WP-M-03 task 5.1. Plan: [hil-bench/](hil-bench/README.md) (draft) | Maintainer | G3 |
| OI-2 | Decide release-image-compatible fault-injection methods (SWD vs debug build) and document the representativeness argument | SW lead | G4 |
| OI-3 | Port `panda/tests/hitl` to the LionDriver bench without comma jigs. Jungle-based tests run at bench stage B1 ([hil-bench/](hil-bench/README.md) §5.4) | Maintainer | G4 |
| OI-4 | Fork-owned Corolla log set for VS-SWQ-24 and plant parameter identification | Maintainer | G4 |
| OI-5 | Closed (2026-10-13): the split with WP-S-08 (I-1) and WP-V-05 is recorded in §6.1 (VS-SWQ-20 host part moved to WP-S-08) | Safety engineer | G4 |
| OI-6 | Specify cases for SWSR-108a, 503c, 504a, 505a, 507, 507a, 508a, 516a, 516b, 711, 711a, or record why HIL is not the method | Safety engineer | G4 |
