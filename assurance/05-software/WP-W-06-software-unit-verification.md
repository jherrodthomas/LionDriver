# WP-W-06 Software Unit Verification Specification and Report

| Field | Value |
|---|---|
| Work product | WP-W-06 Software unit verification specification and report (static analysis, MISRA, coverage, mutation) |
| Standard reference | ISO 26262-6:2018 §9 (software unit verification; methods, test-case derivation and structural coverage tables of §9); ISO 26262-8:2018 §9 (verification), §11 (tools, by reference to WP-P-07); ISO/SAE 21434:2021 §10 (verification of implementation); ASPICE 4.0 SWE.4 |
| Version | 0.1 |
| Status | Draft (specification); results section **Not yet executed** |
| ASIL / scope | Envelope (E-03) units: ASIL D provisional (SG-01, D-09; C for SG-03…SG-05; B or C expected after SG-01 re-rating, [WP-C-04 §4.2](../02-concept/WP-C-04-functional-safety-concept.md)). Host (E-01) units: QM, summarised only |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); I2 for the ASIL D strategy per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This work product defines how the software units of the safety envelope are verified, records the verification assets inherited from upstream with exact figures, lists the gaps, and specifies the LionDriver unit verification cases (VS-UV-nn). It also gives the report template. **No LionDriver unit verification has been executed yet.** Upstream CI runs do not count as LionDriver evidence until the same jobs run in LionDriver CI on a LionDriver baseline (GAP-39, D-03).

In scope:

- E-03 units: opendbc safety core and the Toyota mode, and the panda firmware units the envelope depends on (§2).
- E-01 units: a summary of the QM test base only. QM unit testing has no ISO 26262 coverage requirement; it supports SOTIF and the FFI argument.

Inputs: [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) (FSRs), [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (TSRs, Draft; §6 references its TSR IDs; SWSR IDs follow the same numbers), [WP-W-02](WP-W-02-software-safety-requirements.md) (SWSRs, mirror TSR numbering), [WP-W-05](WP-W-05-software-unit-design.md), [WP-W-01](WP-W-01-software-development-environment-guidelines.md) (coding guidelines), [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) (tools).

## 2. Units under verification

Unit granularity: one C header/source module, verified through its public hooks. The table is the working list until [WP-W-03](WP-W-03-software-architecture.md) fixes the unit catalogue.

| Unit ID | Module | Responsibility | ASIL | TSR block (WP-S-02) |
|---|---|---|---|---|
| U-SAF-CORE | `opendbc_repo/opendbc/safety/safety.h` | Hook dispatch, RX checks (checksum/counter/quality/timeout), `controls_allowed` state, PCM/brake engagement logic, relay malfunction, TX whitelist, forwarding block list | C | TSR-3xx, TSR-4xx, TSR-7xx |
| U-SAF-LAT | `opendbc_repo/opendbc/safety/lateral.h` | Torque magnitude, rate, measured-torque and real-time checks; steer-request tolerance; angle/curvature checks (not used in ref. config) | C | TSR-1xx |
| U-SAF-LONG | `opendbc_repo/opendbc/safety/longitudinal.h` | Longitudinal allowed, accel bounds, inactive value | C (SG-03/04: B) | TSR-2xx |
| U-SAF-HELP | `opendbc_repo/opendbc/safety/helpers.h`, `can.h`, `declarations.h` | Min/max/clamp/abs macros, CRC8, message match, timestamp arithmetic, interpolation, sample buffers | C | all |
| U-SAF-IGN | `opendbc_repo/opendbc/safety/ignition.h` | Ignition detection from CAN | C | TSR-5xx |
| U-SAF-TOY | `opendbc_repo/opendbc/safety/modes/toyota.h` | Toyota RX parsing, limits, TX hook, init and safety-parameter decoding | C | TSR-1xx, 2xx, 3xx, 4xx, 7xx |
| U-SAF-DEF | `opendbc_repo/opendbc/safety/modes/defaults.h` | `noOutput`/`allOutput` modes | C | TSR-5xx |
| U-PND-MAIN | `panda/board/main.c` (tick, heartbeat, safe-mode transitions) | Heartbeat supervision, SILENT on loss, siren, mode switching | C | TSR-4xx, TSR-5xx |
| U-PND-COMMS | `panda/board/main_comms.h`, `can_comms.h` | Host command handling (`0xdc` set mode, `0xc5` relay, `0xf3` heartbeat), host CAN packet unpacking | C | TSR-4xx, TSR-5xx |
| U-PND-SPI | `panda/board/drivers/spi.h` | SPI framing, XOR checksum, ACK/NACK | C | TSR-4xx |
| U-PND-FDCAN | `panda/board/drivers/fdcan.h`, `drivers/can_common.h` | RX → forward hook → RX hook; TX via TX hook | C | TSR-4xx, TSR-7xx |
| U-PND-HARN | `panda/board/drivers/harness.h` | Relay drive and harness orientation | C | TSR-5xx, TSR-7xx |
| U-PND-FLT | `panda/board/sys/faults.h`, `drivers/simple_watchdog.h`, `drivers/registers.h`, `drivers/interrupts.h` | Fault recording, software watchdog, register check, interrupt-rate check | C | TSR-5xx |
| U-PND-BOOT | `panda/board/bootstub.c`, `crypto/*` | Signature verification of application | C + CS | TSR-5xx |

## 3. Verification strategy

### 3.1 Methods

ISO 26262-6 §9 gives methods for unit verification with recommendation levels per ASIL. The table records LionDriver's **decision** for E-03 at ASIL D (provisional) and the fallback at ASIL B (parts that serve SG-03…SG-05 stay at ASIL C); the recommendation levels themselves are checked against the licensed copy (OI-1) and are not reproduced.

| Method | Decision for E-03 (ASIL D prov.) | At ASIL B | How applied | Exists today? |
|---|---|---|---|---|
| Walk-through | Not used alone | Allowed | — | No records |
| Inspection (pair-review / Fagan-style with checklist) | **Applied** to every E-03 unit at G3 and to every SR-A PR | Applied | [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) checklist + WP-W-01 §5.4 | No (GAP-32) |
| Semi-formal verification | Applied to engagement state machine (state table vs code) | Optional | State-transition table in WP-W-05; review | No |
| Formal verification | Not applied; rationale: effort vs ASIL D recommendation level to be checked (OI-1) | Not applied | — | No |
| Control-flow analysis | **Applied** | Applied | cppcheck `--check-level=exhaustive --safety`; review | Partial (tool only) |
| Data-flow analysis | **Applied** | Applied | cppcheck; review of ISR shared data (WP-W-01 ENV-R-12) | Partial |
| Static code analysis (MISRA) | **Applied**, zero unrecorded violations | Applied | `test_misra.sh` (opendbc and panda) | Yes, upstream CI only |
| Static analysis by abstract interpretation | Planned (run-time error absence, e.g. integer overflow) | Optional | Tool to be selected and classified (OI-2) | No |
| Requirements-based test | **Applied**: every SWSR has ≥ 1 test with `@req` link | Applied | §6 VS-UV | No (tests reference constants, GAP-14) |
| Interface test | **Applied**: hook signatures, safety-param decoding, CAN packet layout, SPI framing | Applied | VS-UV-12…15 | Partial |
| Fault injection test (unit level) | **Applied**: corrupt RX frames, stale timestamps, invalid params, invalid SPI frames | Applied | VS-UV-09…16 | Partial (checksum/timeout tests exist) |
| Resource usage evaluation | **Applied**: stack, execution time per hook on target | Applied | HIL (D-04) | No |
| Back-to-back comparison (model/code, host/target) | **Applied** as host-build vs target-build comparison on the same vectors | Recommended | VS-UV-20 | No |

Test-case derivation methods applied to every requirements-based test: analysis of requirements; equivalence classes (generation and analysis); boundary values (limit, limit ± 1 raw unit, extreme values of the data type); error guessing from GAP findings and field experience.

### 3.2 Structural coverage

| Metric | E-03 target (ASIL D prov.) | At ASIL B | Today | Tool |
|---|---|---|---|---|
| Statement (line) coverage | 100 % of E-03 units in the release configuration, with justified exclusions | 100 % | 100 % **line** coverage gate over `opendbc/safety/**` excluding `libsafety` (`tests/test.sh:36`), in the `ALLOW_DEBUG` configuration | gcovr 8.6 (TL-05) |
| Branch coverage | 100 % with justified exclusions | 100 % with justified exclusions | Not measured (GAP-13, WP-P-07 K-3) | gcovr `--fail-under-branch` |
| MC/DC | 100 % of decisions in U-SAF-CORE, U-SAF-LAT, U-SAF-LONG, U-SAF-TOY, U-PND-MAIN, U-PND-COMMS, or a documented justification per decision | Not required; branch coverage suffices (check licensed table) | Not measured | Tool to select (e.g. gcc 14 `-fcondition-coverage` or a qualified commercial tool), OI-3 |
| Function coverage (integration) | See [WP-W-07](WP-W-07-software-integration-verification.md) | | | |

Coverage is measured on the host build. Because of the host/target differences in [WP-W-01 §7.3](WP-W-01-software-development-environment-guidelines.md), host coverage is accepted only together with the back-to-back target run VS-UV-20.

Coverage exclusions (`GCOV_EXCL`, e.g. `modes/defaults.h:5-10, 18-24`) need a record in [WP-W-01 §9.4](WP-W-01-software-development-environment-guidelines.md).

### 3.3 Complementary measures

| Measure | Role | Today |
|---|---|---|
| Mutation analysis | Checks test-suite strength (fault detection), complements coverage | `tests/mutation.py`, 3 accepted survivors (§4.4) |
| Undefined-behaviour sanitizer | Detects UB on the host build | UBSan run (`test.sh:11`, `libsafety_py.py:27-28`) |
| Drive-log safety replay | Plausibility of the safety mode on real data | `tests/safety_replay/replay_drive.py` (needs logs; not fork-owned) |
| Analyser self-test | Confidence in MISRA tool | `misra/test_mutation.py` (§4.3) |
| Independent re-implementation with trace equivalence | Shows the unit tests fully determine the Toyota safety mode's behaviour, including at every limit boundary | XZACT port outside this repository (§4.8); not reproduced in LionDriver CI |

### 3.4 Test environment

| Environment | ID | Use | Status |
|---|---|---|---|
| Host x86-64 Linux, gcc, `-O0`, `ALLOW_DEBUG` | ENV-H-DBG | Current upstream safety tests | Exists (upstream) |
| Host, release configuration (`release=True`) | ENV-H-REL | Same tests without `ALLOW_DEBUG` | Build only today (`tests/test_release_build.py`) |
| Host macOS, clang | ENV-H-CL | Dual-compiler check | Exists (upstream CI matrix) |
| Target STM32H7 on HIL bench | ENV-T | Back-to-back, resource usage, panda units | Not available (GAP-30, D-04) |

## 4. Existing verification assets (as found at the baseline)

All figures below were obtained by inspecting the files at the baseline. Test-method counts are **static counts of `def test_` definitions**; the number of executed test cases is higher because brand classes inherit from shared bases. No run was performed for this document.

### 4.1 opendbc safety unit tests

| Item | Figure | Source |
|---|---|---|
| Test modules in `opendbc_repo/opendbc/safety/tests/` | 25 `test_*.py` files (21 brand/platform modules, plus `test_defaults.py`, `test_elm327.py`, `test_body.py`, `test_release_build.py`) | directory listing |
| Shared test base `common.py` | 1217 lines; 51 test methods in 12 test classes (e.g. `CarSafetyTest` line 1033, `MotorTorqueSteeringSafetyTest` 537, `SteerRequestCutSafetyTest` 321, `LongitudinalAccelSafetyTest` 163, `SafetyTest` 908) | `tests/common.py` |
| Toyota suite `test_toyota.py` | 397 lines; 16 test methods; 10 classes. Reference-configuration class: `TestToyotaSafetyTorque` (line 139) = Toyota base + `MotorTorqueSteeringSafetyTest` + `SteerRequestCutSafetyTest` | `tests/test_toyota.py` |
| Static count of test methods over the safety test directory | 236 | `grep "def test_"` |
| Harness | cffi wrapper builds `libsafety.so` from `tests/libsafety/safety.c` with `cc` (`libsafety_py.py:14-40`) | |
| Runner | `python -m unittest discover -s .`, run twice: UBSan pass (`SAFETY_COVERAGE=0`, `test.sh:11`) and coverage pass (`SAFETY_COVERAGE=1`, `test.sh:17`) | `tests/test.sh` |
| Coverage gate | `gcovr -r opendbc/safety -d --fail-under-line=100 -e ^libsafety` (`test.sh:36-42`); gcov on Linux, `llvm-cov gcov` on macOS (`test.sh:22-26`) | |
| Release configuration | `test_release_build.py` (16 lines, 2 tests) only **compiles** `libsafety` with and without `release=True`; no test is executed in the release configuration | GAP-41 |
| Upstream CI | jobs `safety` (`test.sh`), `mutation` (Linux + macOS), `tests` (`./test.sh` → `lefthook run test` incl. MISRA and `unittest-parallel`) in `opendbc_repo/.github/workflows/tests.yml:10-56` | Not in LionDriver CI (GAP-39) |

Toyota-relevant coverage of the reference configuration by existing tests (traced to FSRs of WP-C-04; to be re-traced to SWSRs):

| Behaviour | Existing test (class::method, file:line) | FSR |
|---|---|---|
| Torque absolute limit 1500 | `MotorTorqueSteeringSafetyTest::test_torque_absolute_limits` (`common.py:550`) | FSR-01.01 |
| Rate up/down, real-time 450/250 ms | `test_non_realtime_limit_up` (`common.py:290`), `test_non_realtime_limit_down` (`:568`), `test_realtime_limit_up` (`:593`) | FSR-01.02 |
| Measured-torque tracking ±350 | `test_exceed_torque_sensor` (`:582`), `test_torque_measurements` (`:616`) | FSR-01.03 |
| No torque / steer bit while not allowed | `test_steer_safety_check` (`:277`), `test_steer_req_bit` (`:304`) | FSR-01.04 |
| Steer-request cut tolerance | `test_steer_req_bit_frames`, `_multi_invalid`, `_realtime` (`:333-395`) | (TSR-106) |
| Engagement on PCM edge / disengage | `test_enable_control_allowed_from_cruise` (`:1123`), `test_disable_control_allowed_from_cruise` (`:1129`), `test_cruise_engaged_prev` (`:1134`) | FSR-01.05, FSR-05.02 |
| Brake disengage | `test_prev_user_brake`, `test_allow_user_brake_at_zero_speed`, `test_not_allow_user_brake_when_moving` (`:1111-1176`) | FSR-05.01 |
| Gas blocks long, no disengage | `test_prev_gas`, `test_no_disengage_on_gas` (`:1086-1110`) | FSR-03.02, FSR-05.04 |
| Accel bounds | `test_accel_limits_correct`, `test_accel_actuation_limits` (`:174-178`) | FSR-03.01, FSR-04.01 |
| RX checksum, wheel-speed fault | `TestToyotaSafetyBase::test_rx_hook` (`test_toyota.py:110`) | FSR-01.06 (partial) |
| RX timeout | `SafetyTest`/`CarSafetyTest::test_safety_tick` (`common.py:1208`) | FSR-01.06 (partial) |
| Relay malfunction | `test_relay_malfunction` (`common.py:1067`) | FSR-01.11 |
| Forwarding block list | `test_fwd_hook` (`common.py:927`) | FSR-07.01 |
| TX whitelist, bus spam | `test_spam_can_buses` (`common.py:937`), `test_tx_hook_on_wrong_safety_mode` (`:952`) | FSR-07.02 (partial) |
| AEB `0x283` blocked unless zero | `test_block_aeb` (`test_toyota.py:87`) | FSR-07.02 (partial) |
| Diagnostics TX restrictions | `test_diagnostics` (`test_toyota.py:80`) | — |

Note: tests assert constants copied into the test classes (`test_toyota.py:139-155`), not requirement values. A wrong limit in `toyota.h` that is copied into the test passes (GAP-14).

### 4.2 Structural coverage

| Item | Figure | Source |
|---|---|---|
| Metric | Line coverage only | `test.sh:36` |
| Threshold | 100 % of executable lines in `opendbc/safety/**` (excluding `libsafety/`) | `test.sh:36` |
| Exclusions | `GCOV_EXCL` blocks in `modes/defaults.h:5-10, 18-24` | |
| Configuration measured | `ALLOW_DEBUG` (debug superset) | `libsafety_py.py:30-31` |
| Branch / MC/DC | Not measured | GAP-13 |

### 4.3 MISRA C:2012 static analysis

| Item | Figure | Source |
|---|---|---|
| Tool | cppcheck 2.21.0 + MISRA addon, `--check-level=exhaustive --safety --platform=arm32-wchar_t4 --std=c11` | `tests/misra/test_misra.sh:40-47` |
| Analysed entry point | `opendbc/safety/tests/misra/main.c` (includes `safety.h` and all modes) | `test_misra.sh:62` |
| Rules in coverage table | 156; 154 checked (129 addon, 25 cppcheck core); 2 unchecked: **1.1, 3.2** | `tests/misra/coverage_table` |
| Global suppressions | 6 MISRA rules (11.4, 11.5, 15.1, 19.2, 20.10, 2.5) + `unmatchedSuppression` + `unusedFunction` for interrupt handlers | `tests/misra/suppressions.txt` (21 lines) |
| Inline suppressions in safety code | 8 (rules 1.2 and 17.3 on each of 4 macros, `helpers.h:5-31`) + 1 non-MISRA (`modes/rivian.h:174`) | grep |
| Fail criterion | exit code 2 **or** grep for "misra violation", "error", "style: " (workaround for cppcheck ticket 12440) | `test_misra.sh:51-56` |
| Analyser self-test | `misra/test_mutation.py`: 1 no-change case + 10 injected rule patterns, **2 sampled per run** with a fixed seed | `misra/test_mutation.py:18-46` |
| Deviation records | None upstream; register created in [WP-W-01 §9](WP-W-01-software-development-environment-guidelines.md) | GAP-13 |
| panda firmware | `panda/tests/misra/test_misra.sh` analyses `board/main.c` for H7 with `-UBOOTSTUB` (lines 35, 65) — bootstub not analysed; same 6-rule suppression file; self-test samples 2 of 10 patterns + 1 fixed mutation | GAP-13 |

### 4.4 Mutation testing

| Item | Figure | Source |
|---|---|---|
| Tool | `tests/mutation.py` (621 lines), tree-sitter based | |
| Mutator families | 9: increment, decrement, comparison, boundary (number literal), bitwise_assignment, bitwise, arithmetic_assignment, arithmetic, remove_negation | `mutation.py:40-50` |
| Pass criterion | No surviving mutant other than the accepted list | `mutation.py:608-617` |
| Accepted survivors | 3, all `boundary` mutator: `lateral.h:188` (curvature real-time window roll, `MAX_RT_INTERVAL / 2U`), `lateral.h:218` and `lateral.h:219` (angle-rate bounds in `steer_angle_cmd_checks`) | `mutation.py:608-612` |
| Relevance to reference configuration | None of the 3 lines executes in the Toyota LKA torque path: line 188 is in the curvature check (not used by Toyota); lines 218-219 are in the angle check used by Toyota **LTA** (`ToyotaSafetyFlags.LTA`), which is not set for `TOYOTA_COROLLA_TSS2`. Each still needs a justification record (WP-P-07 K-7) | |
| Mutation score report | Not produced | |
| Baseline sanity check | Aborts if unmutated tests fail (`mutation.py:527-532`); does not detect false "killed" verdicts | WP-P-07 TL-06 |

### 4.5 panda firmware tests

| Item | Figure | Source |
|---|---|---|
| Test modules | 12 `test_*.py`: 9 HITL (`tests/hitl/test_1…9_*.py`, 29 test methods), 2 host protocol tests (`tests/usbprotocol/test_comms.py` 5 methods, `test_pandalib.py` 1 method), 1 MISRA self-test | `panda/tests/` |
| Host unit harness | `tests/libpanda` builds `panda.c` as a shared library (`tests/libpanda/SConscript`) used by `test_comms.py` | |
| HITL | Needs comma test jigs and Jenkins (`panda/Jenkinsfile`); `test_6_safety.py` has 1 test (no-output mode) | Not available to the fork (GAP-30) |
| Coverage | No coverage measurement, no mutation testing of panda firmware units | gap |
| CI in panda repo | `.github/workflows/test.yaml`: build debug FW, build release FW with the **debug** cert (`CERT=board/crypto/certs/debug RELEASE=1 scons`), `./test.sh` (`ruff`, `unittest discover -s tests`) | panda CI only |

### 4.6 Related opendbc car-level tests (data and interface)

| Test | What it checks | Limitation |
|---|---|---|
| `opendbc_repo/opendbc/car/tests/test_lateral_limits.py` | ISO 11270-derived jerk bounds on controller limits and `MAX_LAT_ACCEL_MEASURED ≤ 3.0 m/s²` per platform (lines 12-17, 63-69) | Uses controller limits, not envelope limits |
| `opendbc_repo/opendbc/car/tests/test_models.py` | Per route: CarParams, interfaces, `test_panda_safety_rx_checks`, `test_panda_safety_tx_cases`, `test_panda_safety_carstate` (host CarState vs envelope view) (lines 192-376) | Needs route data from comma storage (`test_models.py:43-45`) |
| `opendbc_repo/opendbc/car/toyota/tests/test_toyota.py` | Toyota flags, FW version format, fuzzy-fingerprint rules | Host data checks |

### 4.7 openpilot host unit tests (QM, summary)

| Item | Figure | Source |
|---|---|---|
| Python test modules under `openpilot/` | 68 `test_*.py`; 327 test methods (static count). By area: controls 6, locationd 5, selfdrived 3, monitoring 1, car 3, pandad 3, selfdrive/test 5, cereal 3, common 9, system 16, tools 9, ui 4 (+`test_native.py`) | `find openpilot -name 'test_*.py'` |
| C++ test sources | 4 (`common/tests/test_swaglog.cc`, `selfdrive/pandad/tests/test_pandad_canprotocol.cc`, `tools/cabana/tests/test_cabana.cc`, `tools/replay/tests/test_route.cc`) | |
| Runner | `tools/test_runner.py` (unittest-based; ignores process replay and `tools/sim`) via `tools/op.sh test` | WP-P-07 K-10 |
| Coverage threshold | None (Python `coverage` 7.16.0 informational only) | GAP-36 |
| DM unit tests | `selfdrive/monitoring/test_monitoring.py`: scenario tests; none for DM data loss | GAP-21 |
| LionDriver CI | `.github/workflows/tests.yaml` runs on `push` to `master` and on PRs; not on `liondriver-dev` pushes | GAP-39 |

### 4.8 Independent re-implementation of the Toyota safety mode (XZACT)

The Toyota safety mode was re-implemented independently in [XZACT](https://github.com/jherrodthomas/XZACT-Lang/tree/claude/admiring-ritchie-hneag0/apps/openpilot_toyota_safety) and compared with the unmodified opendbc C at the pinned commit `229dc70`. Carried over from the earlier `docs/safety/` drafts ([reconciliation record](../00-assessment/docs-safety-reconciliation.md)).

| Check | Result |
|---|---|
| Event traces byte-identical between the C original and the port (directed tests, exhaustive sweeps of wheel-speed rounding and angle-rate limits, 64 randomized drives over every mode-flag combination) | 72 / 72 traces, 1,703,142 events |
| Reachable upstream lines of the Toyota mode executed (gcov) | 100 % |
| Planted bugs detected by the traces | 30 / 30 |

| Item | Note |
|---|---|
| What it shows | The safety mode's behaviour is fully determined by its tests, and an independent implementation reproduces it exactly |
| What it does not show | That the limits are the right limits for the vehicle (WP-C-03, AOU-01…05), or anything about timing on the safety MCU |
| Relation to §4.4 | The 30 planted bugs are a separate experiment from `tests/mutation.py`; they do not replace the mutation-score report (OI-5) |
| Tool confidence | The XZACT compiler has silently miscompiled valid programs (earlier safety-plan anomaly A02). The port is used only as a test oracle, so a miscompilation can produce a false mismatch but cannot change the shipped C. No XZACT-generated code may be used in the product |
| Status | Produced outside this repository, not reviewed, not reproducible from LionDriver CI (OI-10) |

## 5. Gaps against the strategy

| # | Gap | Effect | GAP | Closure |
|---|---|---|---|---|
| UV-G1 | Line coverage only; no branch, no MC/DC | ASIL D (prov.) structural coverage not demonstrated | GAP-13 | Add branch gate; select and qualify MC/DC tool (OI-3) |
| UV-G2 | Tests run on x86/arm64 host, `-O0`; target Cortex-M7 `-Os` never tested by unit tests | Compiler (TL-01 TCL3) and target-specific defects undetected | GAP-13, GAP-30 | VS-UV-20 on HIL (D-04) |
| UV-G3 | Tested configuration is `ALLOW_DEBUG`; release configuration only compiled | Tested ≠ shipped | GAP-41 | VS-UV-19 |
| UV-G4 | Envelope verification not run in LionDriver CI | No evidence under LionDriver control | GAP-39 | OI-4 |
| UV-G5 | No requirement tags; tests assert copied constants | No requirements-based test argument | GAP-14 | `@req` tags + `links/verification.yaml` (WP-P-06) |
| UV-G6 | No deviation records for MISRA suppressions; bootstub not analysed; 2 rules unchecked | MISRA compliance claim incomplete | GAP-13 | WP-W-01 §9, panda bootstub variant |
| UV-G7 | 3 accepted mutation survivors without justification; no mutation score | Weak evidence of test strength | GAP-13 | Justification records; mutation score in report |
| UV-G8 | panda firmware units: no unit tests with coverage; HITL needs comma infrastructure | U-PND-* unverified at unit level | GAP-30 | Extend `tests/libpanda` host harness; HIL bench |
| UV-G9 | No tests for behaviours that are not implemented yet (E2E counters, IWDG, safety-mode lock, driver-torque override, EPS fault, jerk limit) | Will be needed once implemented | GAP-01, -02, -03, -04, -07, -09 | VS-UV-08…18 specified now |
| UV-G10 | No resource-usage (stack, execution time) evaluation | ASIL D (prov.) method not applied | — | VS-UV-21 |
| UV-G11 | Tools unqualified (gcovr, cppcheck, mutation.py, harness) | Evidence confidence | GAP-34 | WP-P-07 TQR-04…07 |

## 6. Unit verification specification (VS-UV)

Each VS-UV is a group of test cases. Detailed cases are generated from the SWSRs of [WP-W-02](WP-W-02-software-safety-requirements.md) once agreed; the parent column gives the TSR of [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (Draft) and the FSR it traces to. **Environment:** H = host (ENV-H-REL unless stated), T = target (ENV-T). **Status** of all entries: Specified, not implemented unless "Existing (partial)".

| ID | Unit | Objective | Parent TSR (WP-S-02) / FSR | Methods (derivation) | Env. | Pass criterion | Existing basis |
|---|---|---|---|---|---|---|---|
| VS-UV-01 | U-SAF-HELP | Min/max/clamp/abs macros, CRC8, `safety_get_ts_elapsed` wrap-around, `safety_interpolate` hold-at-ends | supports all E-03 TSRs | Equivalence classes, boundary values (INT_MIN/MAX, unsigned wrap) | H, T | Results equal to reference model for all vectors; no UBSan report | None dedicated |
| VS-UV-02 | U-SAF-LAT, U-SAF-TOY | Torque magnitude limit | TSR-101, TSR-102 / FSR-01.01 | Boundary: limit−1, limit, limit+1, −limit−1, extreme int16 | H, T | Frames with \|τ\| > limit rejected, `controls_allowed` and counters as specified | Existing (partial): `test_torque_absolute_limits` |
| VS-UV-03 | U-SAF-LAT | Rate up/down and real-time window | TSR-103 / FSR-01.02 | Boundary on delta per frame and per 250 ms window; window roll-over timing | H, T | Violations exactly at limit+1; window reset at 250 ms ± 0 µs | Existing (partial) |
| VS-UV-04 | U-SAF-LAT, U-SAF-TOY | Measured-torque tracking incl. EPS scale and ±1 padding | TSR-104 / FSR-01.03 | Boundary; EPS factor 73 (reference) | H, T | Command beyond meas ± 350 (+ padding) rejected | Existing (partial) |
| VS-UV-05 | U-SAF-LAT | No torque / no steer-request bit without authority; steer-request cut tolerance; LTA frame rejection; authority revocation on rejected frame | TSR-105…108 / FSR-01.04, FSR-01.12 | State × input combinations (MC/DC on decision) | H | All combinations per decision table | Existing (partial) |
| VS-UV-06 | U-SAF-CORE, U-SAF-TOY | Engagement only on PCM rising edge; revocation on PCM inactive, brake edge or brake while moving | TSR-301, TSR-302, TSR-311 / FSR-01.05, FSR-05.01, FSR-05.02 | State-transition coverage (all transitions of WP-W-05 table) | H | Every transition and every guard false/true covered; MC/DC on guards | Existing (partial) |
| VS-UV-07 | U-SAF-LONG, U-SAF-TOY | Accel bounds, inactive value, gas blocks longitudinal | TSR-201, 202, 203, 305 / FSR-03.01, 03.02, 04.01, 05.04 | Boundary on ±raw limits; gas × authority combinations | H, T | As specified | Existing (partial) |
| VS-UV-08 | U-SAF-LONG | Accel rate (jerk) limit — once implemented | TSR-204, TSR-205 / FSR-03.03, FSR-04.02 | Boundary | H, T | Per SWSR | None (GAP-04) |
| VS-UV-09 | U-SAF-CORE, U-SAF-TOY | RX integrity: checksum, counter, quality flag per Toyota message; repeated/stale frame detection | TSR-402…406 / FSR-01.06 | Fault injection: bit flips, frozen payload with valid checksum, replay, wrong length/bus | H | Every injected fault detected within the SWSR bound; authority revoked | Existing (partial): `test_rx_hook` (checksum only); counters not implemented (GAP-01) |
| VS-UV-10 | U-SAF-CORE | RX timeout detection time | TSR-401, TSR-306 / FSR-01.06 | Fault injection: message stop at each phase relative to the 1 Hz tick | H, T | Detection within TSR-401 (absence > 5 nominal periods); today up to ≈ 2 s, expected to **fail** (GAP-06) | Existing (partial): `test_safety_tick` |
| VS-UV-11 | U-SAF-CORE | Relay malfunction latch and TX/forward inhibition | TSR-710 / FSR-01.11 | Fault injection of check-relay messages on bus 0 before/after grace | H | Latch set after grace; all TX and forwarding blocked until re-init | Existing (partial) |
| VS-UV-12 | U-SAF-TOY (init) | Safety-parameter decoding and **range check** (EPS factor, flag bits) | TSR-512 / FSR-01.10 | Interface test: all 16-bit params incl. 0, 72, 73, 74, 255, unknown flag bits | H, T | Only the reference parameter is accepted in the locked configuration; any other → no actuation | None; today any EPS factor 0–255 is accepted (`modes/toyota.h:369-383`) |
| VS-UV-13 | U-PND-COMMS | `0xdc` set-mode rejected while a car mode is active / not the locked mode; `0xc5` unavailable in release | TSR-512, TSR-513 / FSR-01.10 | Interface + fault injection on control commands | H (libpanda), T | Commands rejected as specified | None (GAP-09) |
| VS-UV-14 | U-PND-MAIN | Heartbeat supervision: mismatch and loss timing, SILENT + relay release + siren | TSR-407, 409, 516 / FSR-01.07, FSR-02.05 | Timing boundary on tick phases | H (libpanda), T | Detection within TSR-407 (> 0.3 s heartbeat absence); today 3 s / 5 s, expected to **fail** (GAP-06) | None at unit level |
| VS-UV-15 | U-PND-SPI, U-PND-COMMS, U-PND-FDCAN | SoC→MCU frame integrity: checksum, length, sequence/freshness (once implemented) | TSR-410…413 / FSR-01.08 | Fault injection: corrupted, truncated, duplicated, reordered frames | H (libpanda), T | Corrupted frames discarded; no actuation from an unverified frame | Partial: `usbprotocol/test_comms.py` (5 tests, packing) |
| VS-UV-16 | U-PND-FLT, U-PND-MAIN | Fault → safe state; watchdog servicing (once IWDG implemented) | TSR-501, 502, 503 / FSR-01.09 | Fault injection: stalled main loop, stalled tick, register divergence | T | Safe state within budget (≤ 0.2 s detection) | None (GAP-07, GAP-08) |
| VS-UV-17 | U-SAF-TOY, U-SAF-LAT | Driver steering override and EPS fault monitoring (once moved into envelope) | TSR-304 / FSR-05.03; TSR-110 / FSR-02.01 | Boundary on driver torque threshold; EPS `LKA_STATE` codes | H, T | Per SWSR | None (GAP-02, GAP-03) |
| VS-UV-18 | U-SAF-CORE, U-SAF-TOY | TX whitelist content checks incl. PCS messages `0x344`/`0x411` and AEB `0x283` | TSR-704, 705, 207 / FSR-07.01, 07.02 | Equivalence classes over every whitelisted address and content | H | No PCS-relevant frame passes in the reference configuration | Partial: `test_block_aeb`; `0x344`/`0x411` pass today (FSC OI-5) |
| VS-UV-19 | all U-SAF-* | Run the **complete** safety suite in the release configuration (`release=True`) with coverage | all; TSR-514 | Re-execution | H (ENV-H-REL) | All pass; coverage targets of §3.2 met in release config | Build only today (GAP-41) |
| VS-UV-20 | all E-03 units | Back-to-back host vs target: replay the VS-UV vectors on the target binary and compare hook outputs bit-exactly | all | Back-to-back | H + T | Identical outputs for all vectors | None (GAP-30) |
| VS-UV-21 | all E-03 units | Resource usage: max stack per hook, WCET of RX/TX/tick hooks on target | TSR-501 (timing), budgets of WP-S-04 | Measurement + static stack analysis | T | Stack margin ≥ 20 %; WCET within the timing budget of [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | None |
| VS-UV-22 | U-PND-BOOT | Signature verification accepts only the release key; tampered image rejected | TSR-511 | Fault injection on image bytes and signature | T | Rejection of all tampered images | None (GAP-24, GAP-25) |

Static verification items (not tests):

| ID | Item | Pass criterion |
|---|---|---|
| VS-UV-S1 | MISRA analysis of opendbc safety and panda (incl. bootstub) with the pinned cppcheck | Zero violations not covered by an approved DEV record |
| VS-UV-S2 | Inspection of each E-03 unit against WP-W-01 §5–§6 and WP-W-05 | All findings closed |
| VS-UV-S3 | Abstract-interpretation run (integer overflow, division by zero, out-of-bounds) | No unproven run-time errors without justification |
| VS-UV-S4 | Mutation run with score report | No unjustified survivors; score reported |

## 7. Pass/fail and regression rules

- A VS-UV case passes only if it passes in ENV-H-REL and, where marked T, on ENV-T.
- Coverage below target fails the run unless every uncovered item has an approved exclusion record.
- Every safety-relevant PR (SR-A) re-runs VS-UV-01…19 and VS-UV-S1, VS-UV-S4 in LionDriver CI; VS-UV-20…22 run at each release candidate.
- Results are archived as CI-13 ([WP-P-01 §3](../07-supporting/WP-P-01-configuration-management-plan.md#3-configuration-items)) with run ID, commit SHA and tool versions.

## 8. Unit verification report (template)

**Status: Not yet executed.** No LionDriver run exists. Fill this section from the first LionDriver CI run on a gate baseline.

| Field | Value |
|---|---|
| Baseline (superproject / opendbc / panda) | Not yet executed |
| CI run ID(s) | Not yet executed |
| Tool versions (cppcheck, gcc, gcovr, Python) | Not yet executed |
| Configuration (release / debug) | Not yet executed |

| VS ID | Cases | Passed | Failed | Not run | Environment | Coverage (stmt / branch / MC/DC) | Result | Evidence |
|---|---|---|---|---|---|---|---|---|
| VS-UV-01 … VS-UV-22 | — | — | — | — | — | — | Not yet executed | — |
| VS-UV-S1 … S4 | — | — | — | — | — | — | Not yet executed | — |

| Deviations from this specification | Not yet executed |
|---|---|
| Open problems raised ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)) | Not yet executed |
| Verdict | Not yet executed |

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Check method and coverage recommendation levels for ASIL B, C and D against the licensed ISO 26262-6 §9 tables; adjust §3 decisions | Safety engineer | G3 |
| OI-2 | Select and classify (WP-P-07) an abstract-interpretation or bounded-model-checking tool for VS-UV-S3 | Maintainer | G3 |
| OI-3 | Select and qualify an MC/DC measurement approach; add branch gate (`--fail-under-branch`) to `test.sh` in the opendbc fork | Maintainer | G3 |
| OI-4 | Add the opendbc `safety`, `mutation` and MISRA jobs and the panda MISRA job to LionDriver CI, triggered on `liondriver-dev` (GAP-39, WP-P-01 OI-7/OI-8) | Maintainer | G3 |
| OI-5 | Write justification records for the 3 accepted mutation survivors and add a mutation-score report | Safety engineer | G3 |
| OI-6 | Re-trace §4.1 test methods to SWSRs once WP-W-02 is agreed; re-check §6 parents when WP-S-02 is approved | Safety engineer | G3 |
| OI-7 | Extend `panda/tests/libpanda` to host-test U-PND-MAIN/COMMS/SPI with coverage | Maintainer | G3 |
| OI-8 | HIL bench (D-04) for ENV-T | Maintainer | G4 |
| OI-9 | Fork-owned drive logs for `safety_replay/replay_drive.py` and `test_models.py` | Maintainer | G4 |
| OI-10 | Make the XZACT equivalence check (§4.8) reproducible: pin the XZACT revision, store the trace generator and results with this WP, and classify XZACT under WP-P-07 as a verification tool | Maintainer | G3 |

> Note from the consistency pass: WP-W-03 defines additional panda units U-PND-USB, U-PND-PWR, U-PND-HK and U-PND-PLAT that are not yet in this unit list. Add them with their verification methods. "ASIL D provisional" in this document equals the B‡ notation used in WP-W-02 and WP-S-02.
