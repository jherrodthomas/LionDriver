# WP-W-01 Software Development Environment, Languages and Coding Guidelines

| Field | Value |
|---|---|
| Work product | WP-W-01 SW development environment, languages and coding guidelines |
| Standard reference | ISO 26262-6:2018 §5 (general topics for product development at the software level: development environment, modelling and coding guidelines); ISO 26262-8:2018 §11 (by reference to WP-P-07); ISO/SAE 21434:2021 §10 (secure coding); MISRA C:2012 (incl. amendments as supported by the analyser); ASPICE 4.0 SWE.3 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Envelope (E-03): ASIL D provisional (SG-01, decision D-09), ASIL C for parts that serve SG-03…SG-05; ASIL B/C expected after SG-01 re-rating ([WP-C-04 §4.2](../02-concept/WP-C-04-functional-safety-concept.md)). Host stack (E-01, E-02): QM / SOTIF / CS |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document fixes, for each software element of LionDriver, the programming language, language subset, coding and modelling guidelines, compiler configuration, static analysis and the tool environment. It is the reference that code reviews ([WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md)) and unit verification ([WP-W-06](WP-W-06-software-unit-verification.md)) check against.

It also holds the **MISRA C:2012 deviation procedure and deviation register** (§8, §9), which closes the record-keeping part of GAP-13 and K-4 of [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md).

The guidelines are written for code that LionDriver will own after the forks of opendbc and panda (D-01, [WP-P-01 §6](../07-supporting/WP-P-01-configuration-management-plan.md#6-submodule-control-d-01)). Until then they describe the inherited code and set the rules that LionDriver change requests must follow.

ASIL handling: until the HARA is confirmed, the envelope is developed to the **ASIL D** column of the 26262-6 §5 topics (SG-01 is ASIL D in HARA 0.2, decision D-09). If SG-01 is re-rated to ASIL B (WP-C-04 OI-2), the ASIL C column still applies to parts that serve SG-03…SG-05 (ASIL C) and the ASIL B column to the rest, and this document is re-issued. Recommendation levels per ASIL are taken from the licensed copy of ISO 26262-6; they are not reproduced here.

## 2. Software elements and languages

| Element | Allocation | Language / standard | Build | ASIL / class | Location |
|---|---|---|---|---|---|
| Envelope safety logic (opendbc safety) | E-03 | C (C11 with GNU extensions, `-std=gnu11`) | Included into panda firmware; host build `libsafety.so` for tests | ASIL D (prov.) | `opendbc_repo/opendbc/safety/{safety.h,lateral.h,longitudinal.h,helpers.h,declarations.h,can.h,ignition.h}`, `opendbc_repo/opendbc/safety/modes/toyota.h`, `modes/defaults.h` |
| Envelope platform (panda firmware paths used by the envelope) | E-03 | C (`-std=gnu11`), ARM assembly (startup) | `panda/SConscript` with arm-none-eabi-gcc | ASIL D (prov.) | `panda/board/main.c`, `main_comms.h`, `can_comms.h`, `drivers/{fdcan,spi,harness,simple_watchdog,registers,interrupts}.h`, `sys/*`, `stm32h7/*`, `stm32h7/startup_stm32h7x5xx.s` |
| panda bootstub | E-03 / CS | C, assembly | `panda/SConscript:106-114` (`-DBOOTSTUB`) | ASIL D (prov.) + CAL (boot integrity) | `panda/board/bootstub.c`, `crypto/{rsa,sha}.c`, `flasher.h`, `stm32h7/llflash.h` |
| Host car interface (Toyota port, CAN parse/pack) | E-01 | Python 3.12 (`.python-version`), Cython/C++ for the CAN parser | uv, SCons | QM (SR-Q) | `opendbc_repo/opendbc/car/**`, `opendbc_repo/opendbc/can/**` |
| Host stack daemons in Python | E-01 | Python 3.12 | — | QM (SR-Q) | `openpilot/selfdrive/{selfdrived,controls,monitoring,car,locationd,modeld}/**`, `openpilot/system/**` |
| Host daemons in C++ | E-01 | C++17 (`-std=c++1z`, `SConstruct:143`) | SCons, clang on device (`SConstruct:179-180`) | QM (SR-Q for pandad) | `openpilot/selfdrive/pandad/*.cc` (5 files), `openpilot/system/camerad/**`, `openpilot/system/loggerd/**` |
| Generated code | E-01 | C/C++ (acados MPC, rednose EKF, Cython, capnp) | Code generators, see §11 | QM | `openpilot/selfdrive/controls/lib/longitudinal_mpc_lib`, `openpilot/selfdrive/locationd/models`, `openpilot/cereal/gen` |
| Interface schemas | IF-0x | Cap'n Proto | `capnp` compiler + pycapnp | QM; schema of `CarParams` is SR-Q because it configures E-03 | `openpilot/cereal/{log,custom,deprecated}.capnp`, `opendbc_repo/opendbc/car/car.capnp` |
| ML models | E-02 | ONNX, compiled to tinygrad pickles | `openpilot/selfdrive/modeld/SConscript:51-52` | QM (PAS 8800 / SOTIF) | `openpilot/selfdrive/modeld/models/*` (LFS) — governed by [WP-W-10](WP-W-10-ml-engineering.md) |
| Configuration and calibration data | E-01, E-03 | Python literals, TOML, C constants, DBC | — | Per item in [WP-W-09](WP-W-09-configuration-calibration-data.md) | |

Rules on language choice:

- **L-01** New code in E-03 shall be written in C following §5–§7. No C++ and no dynamic languages in E-03.
- **L-02** New code in E-01 that is SR-Q (WP-P-01 §4.2) should be Python following §10, or C++ following §12. Code generators other than those listed in §11 need a WP-P-07 classification before use.
- **L-03** No logic that the safety argument depends on shall move from E-03 into E-01. Moving logic in the other direction (host → envelope, e.g. driver-torque override, GAP-02) follows E-03 rules.

## 3. Mapping of the ISO 26262-6 §5 topics

ISO 26262-6 §5 lists topics that modelling and coding guidelines shall cover (low complexity, language subset, strong typing, defensive implementation, established design principles, unambiguous graphical representation, style guides, naming conventions, concurrency aspects). The table maps each topic to how it is addressed. Clause wording and the per-ASIL recommendation levels are checked against the licensed copy before audit.

| Topic | E-03 envelope (C) | E-01 host (Python / C++) |
|---|---|---|
| Enforcement of low complexity | ENV-R-07 (function length, cyclomatic complexity limit), MISRA 15.x control flow | ruff `C4`, `PIE`, `B`; review |
| Use of language subsets | MISRA C:2012 (§5); GNU extensions only as recorded deviations (§9) | Python: banned APIs (§10.2); no `eval`/`exec`/`pickle` of untrusted data |
| Enforcement of strong typing | MISRA essential type model (Rules 10.x), `-Wall -Wextra -Werror` | Type hints required on new SR-Q modules; `ty` check (no verification credit, TL-19) |
| Use of defensive implementation techniques | ENV-R-08…ENV-R-11 (§6) | §10.3 |
| Use of established design principles | §6 design principles for the envelope | §10.3, §12 |
| Use of unambiguous graphical representation | §13 | §13 |
| Use of style guides | MISRA + cpplint (opendbc `lefthook.yml`) + this document | ruff + `pyproject.toml` |
| Use of naming conventions | §5.3 | PEP 8 as enforced by ruff, 2-space indent (`pyproject.toml:113`) |
| Concurrency aspects | ENV-R-12 (ISR/main-loop shared data) | §10.3 (msgq, process priorities) |

## 4. Development environment

The tools, their versions and their tool confidence levels are owned by [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md). This table states which tool is the **designated** tool for each activity in this guideline; using a different tool for an ASIL activity needs a WP-P-07 update first.

| Activity | Designated tool (WP-P-07 ID) | Configuration source | TCL (WP-P-07) | Notes |
|---|---|---|---|---|
| Target compilation (E-03) | arm-none-eabi-gcc 13.2.1 (TL-01) | `panda/SConscript:67-141` | 3 → 2 after HIL | Only option set in §7.1 is qualified |
| Host compilation of envelope for tests | host `cc` (TL-02) | `opendbc_repo/opendbc/safety/tests/libsafety/libsafety_py.py:19-39` | 2 | gcc on Linux, clang on macOS; unpinned (WP-P-07 K-8) |
| Host compilation of E-01 C/C++ | clang/clang++ (TL-02) | `SConstruct:128-143, 179-180` | QM | |
| Build orchestration | SCons 4.11.1 (TL-03) | `SConstruct`, `panda/SConscript` | 2 | |
| MISRA and static analysis (E-03) | cppcheck 2.21.0 + MISRA addon (TL-04) | `opendbc_repo/opendbc/safety/tests/misra/test_misra.sh`, `panda/tests/misra/test_misra.sh` | 2 | Two different packagings (K-2) |
| Structural coverage | gcov + gcovr 8.6 (TL-05) | `opendbc_repo/opendbc/safety/tests/test.sh:36` | 2 | Line coverage only today (K-3) |
| Mutation analysis | `mutation.py` (TL-06) | `opendbc_repo/opendbc/safety/tests/mutation.py` | 3 | In-house |
| Unit test execution | `unittest`, `unittest-parallel`, cffi harness (TL-07) | `test.sh`, `opendbc_repo/lefthook.yml` | 2 | |
| Undefined behaviour detection | UBSan (TL-21) | `libsafety_py.py:27-28` | 1 | |
| Python lint, typing | ruff 0.16.7, ty 0.0.80 (TL-19) | `pyproject.toml:111-148` | 1 | No credit |
| C++ style | cpplint 2.0.2 (TL-19) | `opendbc_repo/lefthook.yml:23-24` | 1 | |
| Code generators (QM) | capnp (TL-10), acados (TL-11), rednose/sympy (TL-12), Cython (TL-13), DBC generator (TL-14), tinygrad (TL-09) | per tool | QM | §11 |
| Firmware signing | `panda/board/crypto/sign.py` (TL-15) | `panda/SConscript:117-125` | 2 | Release key handling in [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| Dependency resolution | uv + `uv.lock` (TL-16) | `uv.lock`, `opendbc_repo/uv.lock` | 1 | uv itself unpinned |
| CI | GitHub Actions (TL-18) | `.github/workflows/tests.yaml` | 1 | Does not run the envelope verification today (GAP-39) |

Environment rules:

- **ENV-01** Every tool version used to produce an ASIL work product shall be recorded in the CI log of that run and in the baseline manifest ([WP-P-01 §8](../07-supporting/WP-P-01-configuration-management-plan.md#8-baselines)).
- **ENV-02** Release firmware shall be built only with `RELEASE=1` and a LionDriver release certificate; the DEBUG default of `panda/SConscript:12-20` (adds `-DALLOW_DEBUG`, uses the committed debug key) is forbidden for any build installed in a vehicle outside bench testing (GAP-25).
- **ENV-03** Developers may use any editor or IDE. Local hooks (`lefthook`) are a convenience; the CI result is the record.

## 5. C coding guideline for the envelope (E-03)

### 5.1 Base standard

- **C-01** All E-03 C code shall comply with MISRA C:2012 (the rule set implemented by the designated cppcheck version, see `opendbc_repo/opendbc/safety/tests/misra/coverage_table`). Mandatory rules shall not be deviated. Required and advisory rules may be deviated only through §8.
- **C-02** The language standard is C11. GNU extensions are permitted only where a deviation in §9 records them (today: statement expressions and `__typeof__` in the min/max/clamp/abs macros). This is a deviation from MISRA Rule 1.2 and must stay confined to those macros.
- **C-03** Every MISRA rule that the analyser cannot check shall be covered by review. At the baseline the analyser reports **156 rules, 154 checked** (129 by the addon, 25 by cppcheck core) and **2 unchecked: 1.1 and 3.2** (`tests/misra/coverage_table`). Rule 1.1 (no violation of the standard's syntax and constraints, no exceeding implementation limits) is covered by `-Werror` compilation with two compilers; Rule 3.2 (no line splicing in `//` comments) is covered by review checklist item CR-C-07 (§5.4).
- **C-04** MISRA directives (Dir x.y) are not listed in the cppcheck coverage table. Compliance with the directives shall be argued by review and recorded in the MISRA compliance summary (OI-3).

### 5.2 LionDriver rules in addition to MISRA

| ID | Rule | Rationale / current state |
|---|---|---|
| C-10 | No dynamic memory allocation (`malloc`, `free`, VLAs, `alloca`) in E-03 | Firmware is built with `-nostdlib -fno-builtin` (`panda/SConscript:77-78`); keep it that way |
| C-11 | No recursion, direct or indirect | MISRA 17.2; also needed for stack bound |
| C-12 | Every loop shall have a compile-time bound or a bound derived from a constant array size | e.g. `crc8_update` (`opendbc/safety/helpers.h:40-50`) loops 8 times |
| C-13 | All limit values used by a safety check shall be named constants with units in a comment and a `@req` tag ([WP-P-06 §6](../07-supporting/WP-P-06-requirements-management-traceability.md)) | Today limits are commented constants without requirement IDs (GAP-14), e.g. `modes/toyota.h:172-210` |
| C-14 | Signed/unsigned and integer-width conversions shall be explicit | MISRA 10.x; data from CAN bytes is assembled with shifts and `to_signed` (`modes/toyota.h:100-101`) |
| C-15 | Floating point in safety checks shall be avoided where integer arithmetic suffices; where used (e.g. `safety_interpolate`, `helpers.h:80+`), the conversion back to integer shall be reviewed for rounding direction | Target uses `-fsingle-precision-constant` (`panda/SConscript:82`); host test build does not (§7.3) |
| C-16 | No code under `#ifdef ALLOW_DEBUG` shall be reachable in a release build, and no safety-relevant decision shall depend on `ALLOW_DEBUG` other than to remove debug features | e.g. SecOC flag only parsed under `ALLOW_DEBUG` (`modes/toyota.h:374-377`) |
| C-17 | `GCOV_EXCL` markers shall be used only for code that is unreachable by design and each one shall have a justification record (same procedure as §8) | Present in `modes/defaults.h:5-10, 18-24` |
| C-18 | Inline `cppcheck-suppress` comments shall reference a deviation ID: `// cppcheck-suppress misra-c2012-X.Y ; DEV-nn` | Today they carry free text only |
| C-19 | Global state shared between the CAN RX ISR context and the main loop/tick shall be identified in the architecture (WP-W-03) and accessed only through the documented hooks | ENV-R-12 |

### 5.3 Naming conventions (E-03)

| Item | Convention | Example in code |
|---|---|---|
| Constants and macros | `UPPER_SNAKE_CASE`, brand prefix for brand-specific | `TOYOTA_LONG_LIMITS`, `MAX_RT_INTERVAL` |
| Functions | `lower_snake_case`, module prefix for brand hooks | `toyota_rx_hook`, `steer_torque_cmd_checks` |
| Safety helper macros | `SAFETY_` prefix | `SAFETY_CLAMP` (`helpers.h:23`) |
| Unsigned literals | `U` suffix (MISRA 7.2) | `0x260U` |
| Raw CAN units | variable or constant comment states unit and scale (raw, 0.001 m/s², etc.) | `.max_accel = 2000,   // 2.0 m/s2` (`toyota.h:208`) |

### 5.4 Code review checklist items specific to C (input to WP-P-05 §5.6)

| ID | Check |
|---|---|
| CR-C-01 | MISRA run clean on the PR head with the designated cppcheck; no new suppression without a DEV entry |
| CR-C-02 | No new GNU extension or compiler intrinsic outside §9 |
| CR-C-03 | Every new or changed limit has a `@req` tag and a test that hits both sides of the boundary |
| CR-C-04 | Loops bounded; no recursion; no dynamic memory |
| CR-C-05 | All `controls_allowed`, relay and mode transitions are covered by a state-machine test |
| CR-C-06 | Release and debug builds both compile; behaviour under `ALLOW_DEBUG` reviewed |
| CR-C-07 | Rule 3.2 (no `\` line splicing in `//` comments) and other unchecked rules |
| CR-C-08 | Defensive checks of §6 present for every new input |

## 6. Design principles for the envelope (E-03)

These principles apply to the software unit design ([WP-W-05](WP-W-05-software-unit-design.md)) and architecture ([WP-W-03](WP-W-03-software-architecture.md)). "Current state" records what the baseline does; a "No" is a finding, not a waiver.

| ID | Principle | Current state at baseline | Evidence / GAP |
|---|---|---|---|
| ENV-R-01 | No dynamic objects or variables (no heap, no VLA) | Yes | `-nostdlib`, MISRA 21.3 checked |
| ENV-R-02 | No recursion | Yes (MISRA 17.2 checked) | `coverage_table` |
| ENV-R-03 | Bounded loops with fixed upper limits | Yes for safety checks; to be confirmed for panda drivers by review | `helpers.h:42`, review pending |
| ENV-R-04 | Single entry and single exit per function where practical | Partial: many hooks use early `return`; MISRA 15.5 (advisory) is checked by the addon and reported clean, so remaining multiple exits must be confirmed by review | Review pending (OI-4) |
| ENV-R-05 | No implicit type conversions; no unions for type punning in safety logic | Partial: 19.2 (unions) globally suppressed (DEV-04) | §9 |
| ENV-R-06 | No hidden data flow or control flow: no function pointers except the brand hook table selected at mode init | Hook table `safety_hooks` selected in `set_safety_hooks` (`safety.h:391-460`); acceptable if the table is constant and integrity-protected (link to FSR-01.10) | WP-W-03 |
| ENV-R-07 | Low complexity: functions ≤ 60 logical lines and cyclomatic complexity ≤ 15 unless justified | Not measured at baseline | OI-5 (tool) |
| ENV-R-08 | Every value received from the SoC (mode, parameter, CAN frame content) and from the vehicle bus shall be range-checked before use | **No** for the safety parameter: `toyota_dbc_eps_torque_factor = param & 0xFF` accepts any 0–255 (`modes/toyota.h:369-383`); no check that it equals the reference value 73 | GAP-09; TSR-512 in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md); [WP-W-09](WP-W-09-configuration-calibration-data.md) CD-01 |
| ENV-R-09 | Plausibility checks on received data (checksum, counter, timeout, signal range) | Partial: no counters on Toyota RX; `0x226`, `0xAA` without checksum (`modes/toyota.h:39-46`) | GAP-01 |
| ENV-R-10 | Fail-silent default: unknown or unsupported states lead to no actuation (SILENT/NO_OUTPUT) | Yes for unknown mode (`panda/board/main.c:33-40`) and default `controls_allowed = false` (`safety.h:57`) | — |
| ENV-R-11 | Detected faults shall drive a defined reaction, not only a report | **No**: faults are report-only, `PERMANENT_FAULTS = 0U` (`panda/board/sys/sys.h:50`) | GAP-08 |
| ENV-R-12 | Shared data between interrupt and non-interrupt context protected (critical section or single-writer design) and documented | Not documented | WP-W-03, OI-6 |
| ENV-R-13 | No safety decision before the input it depends on is validated | **No**: forwarding hook runs before RX validation of the same frame (`panda/board/drivers/fdcan.h:199-221`) | GAP-11 |
| ENV-R-14 | Stack usage bounded and checked (static analysis or `-fstack-usage` + call-graph) with margin ≥ 20 % | Not done | OI-7 |
| ENV-R-15 | Separation of safety and non-safety code inside the MCU (MPU or argued FFI) | No MPU configuration | GAP-08, GAP-11, [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) |

## 7. Compiler configuration

### 7.1 Target build (panda firmware, E-03)

From `panda/SConscript`:

| Flag group | Flags | Line |
|---|---|---|
| CPU / ABI | `-mcpu=cortex-m7 -mhard-float -mfpu=fpv5-d16 -mlittle-endian -mthumb` | 75-76, 133-140 |
| Defines | `-DSTM32H7 -DSTM32H725xx`; `-DALLOW_DEBUG` unless `RELEASE` is set; `-DBOOTSTUB` for the bootstub; packet version hashes | 12-20, 108-109, 135-137, 165 |
| Warnings | `-Wall -Wextra -Wstrict-prototypes -Werror -fmax-errors=1` | 71-74, 80 |
| Language | `-std=gnu11 -nostdlib -fno-builtin` | 77-79 |
| Numerics | `-fsingle-precision-constant` | 82 |
| Optimisation / debug | `-Os -g` | 83-84 |
| Link | linker script `stm32h7/stm32h7x5_flash.ld`; app at `0x8020000` | 81, 122, 132 |

Rules:

- **CF-01** The qualified option set (TL-01 qualification, WP-P-07 §5) is exactly the RELEASE configuration above. Changing any flag is an SR-T change ([WP-P-01 §4](../07-supporting/WP-P-01-configuration-management-plan.md#4-safety-relevant-file-list)).
- **CF-02** Add `-Wconversion -Wsign-conversion -Wcast-align -Wshadow -Wundef` to the target build after the existing warnings are resolved (OI-8). Not present at baseline.
- **CF-03** Add `-fstack-usage` and a link map review for ENV-R-14 (OI-7).

### 7.2 Host build of the envelope for unit tests

From `opendbc_repo/opendbc/safety/tests/libsafety/libsafety_py.py:19-39`: `cc -fPIC -Wall -Wextra -Werror -nostdlib -fno-builtin -std=gnu11 -Wfatal-errors -Wno-pointer-to-int-cast -g -O0 -fno-omit-frame-pointer`, plus either coverage (`-fprofile-arcs -ftest-coverage`) or UBSan (`-fsanitize=undefined -fno-sanitize-recover=undefined`), plus `-DALLOW_DEBUG` unless `release=True`.

### 7.3 Representativeness of the host test build

| Difference host vs target | Effect | Handling |
|---|---|---|
| x86-64 / arm64 host vs Cortex-M7 | Integer widths of `int`/`long`, alignment, endianness assumptions | Envelope uses fixed-width types; back-to-back host vs target tests planned (VS-UV-20 in WP-W-06) |
| `-O0` vs `-Os` | Optimiser-dependent defects not exercised | Target tests on HIL (D-04); TL-01 qualification |
| No `-fsingle-precision-constant` on host | Float literal precision differs in `safety_interpolate` and angle limits | Review of float use (C-15); back-to-back tests |
| `-DALLOW_DEBUG` in tests | Tested configuration is a superset of the release one (GAP-41) | Run the full safety suite also with `release=True` (WP-W-06 VS-UV-19) |
| Different compiler (gcc/clang vs arm-none-eabi-gcc) | Compiler-specific behaviour | Dual-host-compiler run already exists in upstream CI; target run needed |

### 7.4 Host stack (E-01, QM)

`SConstruct:128-143`: `-g -fPIC -pipe -O2 -Wunused -Werror -Wshadow=local` (or `-Wshadow`), `-std=gnu11` for C, `-std=c++1z` for C++; clang/clang++ on the device (`SConstruct:179-180`). Cython targets remove `-Werror` (`SConstruct:221-222`). No change proposed for QM code beyond §12.

## 8. MISRA deviation procedure

A deviation is a recorded, approved decision that a MISRA guideline is not followed at a specific place or in a specific way. A suppression in the tool without a deviation record is a **finding**.

1. **Raise.** The author adds the suppression (inline preferred, global only for project-wide decisions) and a DEV entry in §9 in the same PR. The entry states: rule, category (mandatory/required/advisory, from the licensed MISRA document), scope (file:line or global), reason, safety impact analysis, compensating measure, and whether it is a *deviation* or a *tool false positive*.
2. **Classify.** Mandatory rules cannot be deviated. If a mandatory rule is reported, the code is changed, or the report is shown to be a false positive with evidence (minimal reproducer) and recorded as such.
3. **Review.** Deviations in E-03 are reviewed under SR-A rules ([WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md)), with a reviewer other than the author. Global suppressions need approval by the safety manager.
4. **Compensate.** Each deviation names a compensating measure (review, test, analysis) and where its evidence is.
5. **Re-assess.** All deviations are re-assessed when the analyser version changes (WP-P-07 TL-04) and at every gate. A deviation whose reason no longer applies is closed and the suppression removed.
6. **Report.** The MISRA compliance summary for a release lists every guideline as compliant, deviated (with DEV IDs) or disapplied (advisory only, with rationale).

## 9. Deviation register

Seeded from the baseline. **Rationale placeholders ("RATIONALE TBD") must be completed and approved before G3.** Rule categories are to be confirmed against the licensed MISRA C:2012 document (OI-2); the categories shown are the assurance team's reading.

### 9.1 Global suppressions — opendbc safety

Source: `opendbc_repo/opendbc/safety/tests/misra/suppressions.txt` (21 lines; 6 MISRA rules + 2 non-MISRA entries). `panda/tests/misra/suppressions.txt` has identical content and is covered by the same DEV IDs (scope "both").

| DEV | Rule | Cat. (to confirm) | Scope | Upstream comment (verbatim summary) | Rationale (LionDriver) | Compensating measure | Status |
|---|---|---|---|---|---|---|---|
| DEV-01 | 11.4 (conversion between pointer to object and integer) | Advisory | Global, both | "casting from void pointer to type pointer is ok. Done by STM libraries as well" (`suppressions.txt:1-2`) | RATIONALE TBD: list the actual sites (register access, CAN buffers); global scope is too wide for E-03 | Narrow to inline suppressions at register-access sites; review each | Open |
| DEV-02 | 11.5 (conversion from pointer to void into pointer to object) | Advisory | Global, both | same (`:3-4`) | RATIONALE TBD | Same as DEV-01 | Open |
| DEV-03 | 15.1 (goto) | Advisory | Global, both | "use of goto … in accordance to 15.2 and 15.3 is ok" (`:5-6`) | RATIONALE TBD: confirm 15.2/15.3 remain enforced (they are checked) and list goto sites | 15.2, 15.3 checked by tool | Open |
| DEV-04 | 19.2 (union keyword) | Advisory | Global, both | "union types can be used" (`:7-8`) | RATIONALE TBD: unions used for CAN payload/registers; confirm no type punning in safety decisions (ENV-R-05) | Review of every union use in E-03 | Open |
| DEV-05 | 20.10 (`#` and `##` operators) | Advisory | Global, both | "The # and ## preprocessor operators should not be used" (`:9-10`) | RATIONALE TBD: list macros using `#`/`##` (e.g. message table macros) | Review of macro expansions | Open |
| DEV-06 | 2.5 (unused macro declarations) | Advisory | Global, both | Added at cppcheck 2.5 → 2.13 update, "intended to be removed soon" (`:18-21`) | RATIONALE TBD: temporary; macros differ between builds. Target: remove | Remove suppression; fix or justify each macro | Open — removal planned |
| DEV-07 | cppcheck `unmatchedSuppression` (not MISRA) | n/a | Global, both | "not all of these suppressions are applicable to all builds" (`:12-13`) | Tool configuration. Risk: a stale inline suppression is not reported | Periodic review of all inline suppressions at each gate | Open |
| DEV-08 | cppcheck `unusedFunction` for `*/interrupt_handlers*.h` (not MISRA) | n/a | Pattern, both | "All interrupt handlers are defined, including ones we don't use" (`:15-16`) | Vector table completeness; acceptable if every unused handler leads to a safe state (HWSR-502b in [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md)) | Review of handler table | Open |

### 9.2 Inline suppressions — opendbc safety (GNU extensions)

| DEV | Rule | Cat. (to confirm) | Location | Kind | Rationale | Compensating measure | Status |
|---|---|---|---|---|---|---|---|
| DEV-09 | 1.2 (language extensions) | Advisory | `opendbc_repo/opendbc/safety/helpers.h:5, 13, 21, 30` (`SAFETY_MIN`, `SAFETY_MAX`, `SAFETY_CLAMP`, `SAFETY_ABS`) | Deviation | RATIONALE TBD. Statement expressions `({ … })` and `__typeof__` give single evaluation of macro arguments and type-generic min/max. Supported by gcc and clang; relies on `-std=gnu11` | Confine to these 4 macros (C-02); unit tests of each macro with signed/unsigned and boundary values (VS-UV-01); alternative: replace with typed `static inline` functions and remove the deviation (preferred, OI-9) | Open |
| DEV-10 | 17.3 (implicit function declaration) | **Mandatory** | `helpers.h:6, 14, 22, 31` | **Tool false positive** (cannot be a deviation) | Upstream comment: "suppress false implicit declaration alert on typeof extension". RATIONALE TBD: provide a minimal reproducer showing cppcheck misreads `__typeof__` as a call, and confirm with `-Werror=implicit-function-declaration` on both compilers | Compiler error on implicit declarations (C11 + `-Werror`) | Open |
| DEV-11 | cppcheck `knownConditionTrueFalse` (not MISRA) | n/a | `opendbc_repo/opendbc/safety/modes/rivian.h:174` | Tool configuration | Not in the reference configuration (Rivian mode); recorded for completeness | None needed for reference configuration | Open (N/A ref. config) |

### 9.3 Inline suppressions — panda firmware

Found by `grep cppcheck-suppress panda/board` at the baseline. The panda MISRA run analyses `board/main.c` only, with `-UBOOTSTUB` (`panda/tests/misra/test_misra.sh:35, 65`), so suppressions in bootstub-only files are not exercised (GAP-13, WP-P-07 K-5).

| DEV | Rule | Cat. (to confirm) | Location | Upstream reason | Kind | Status |
|---|---|---|---|---|---|---|
| DEV-12 | 1.2 | Advisory | `panda/board/utils.h:3, 10, 17, 25` | "allow __typeof__ extension" | Deviation (same pattern as DEV-09) | Open |
| DEV-13 | 17.3 | **Mandatory** | `panda/board/utils.h:3, 10, 17, 25` | (same macros) | Tool false positive (as DEV-10) | Open |
| DEV-14 | 21.1 (#define/#undef of reserved identifiers) | Required | `panda/board/utils.h:34` | none given | RATIONALE TBD | Open |
| DEV-15 | 21.2 (reserved identifier declared) | Required | `panda/board/libc.h:22, 35, 67` | none given (own `memset`/`memcpy`/`memcmp`-type functions under `-nostdlib`) | RATIONALE TBD | Open |
| DEV-16 | 11.3 (cast between pointers to different object types) | Required | `panda/board/libc.h:42-43` | "already checked that it's properly aligned" | RATIONALE TBD; unit test of alignment branch | Open |
| DEV-17 | 9.3 (partially initialised arrays) | Required | `panda/board/drivers/can_common.h:38` | none given | RATIONALE TBD | Open |
| DEV-18 | 8.4 (compatible declaration visible) | Required | `panda/board/main.c:91` | (with `unusedFunction`, "used in headers not included in cppcheck") | RATIONALE TBD | Open |
| DEV-19 | 17.3 | **Mandatory** | `panda/board/main.c:358`, `panda/board/sys/power_saving.h:153` | "CMSIS __WFI macro expands to inline asm" | Tool false positive; inline asm itself is Dir 4.3 / Rule 1.2 territory — RATIONALE TBD | Open |
| DEV-20 | cppcheck `objectIndex`, `unusedFunction`, `constParameterPointer` (not MISRA) | n/a | `panda/board/can_comms.h:70`; `bootstub.c:21`, `main.c:90`; `stm32h7/llspi.h:4` | various | Tool configuration; `objectIndex` in `can_comms.h` touches the host→CAN path and needs a bounds argument (RATIONALE TBD) | Open |

### 9.4 Coverage-exclusion records

| ID | Location | Reason | Status |
|---|---|---|---|
| EXC-01 | `opendbc_repo/opendbc/safety/modes/defaults.h:5-10, 18-24` (`GCOV_EXCL_*`) | RATIONALE TBD (default/no-output hooks not reachable in tests) | Open |

## 10. Python guidelines for host code (E-01, QM)

Python host code is QM under T-03. The guidelines exist because it is SOTIF-relevant, configures the envelope (CD-01 in WP-W-09) and must not interfere with it.

### 10.1 Lint and format configuration (as found)

`pyproject.toml:111-145`:

| Setting | Value |
|---|---|
| Indent / line length | 2 spaces / 160 |
| Selected rule sets | `E`, `F`, `W`, `PIE`, `C4`, `ISC`, `A`, `B`, `NPY`, `UP`, `ASYNC`, `B904`, `B905`, `PLC0207`, `TRY203`, `TRY400`, `TRY401`, `RUF006`, `RUF008`, `RUF009`, `RUF061`, `RUF064`, `RUF100`, `RUF102`, `RUF103`, `RUF104`, `TID251`, `PLE`, `PLR1704` |
| Ignored | `E741`, `E402`, `B027`, `UP007` |
| Implicit string concat over lines | not allowed |
| Format | `quote-style = "preserve"` |
| Type check (`ty`) | `unresolved-import` and `unresolved-attribute` ignored (`pyproject.toml:146-148`) — no verification credit (GAP-36) |

### 10.2 Banned APIs

As found (`pyproject.toml:135-141`, enforced by ruff `TID251`): `time.time` (use `time.monotonic`), and five `pyray` UI calls. LionDriver adds (OI-10, change request to `pyproject.toml`):

| API | Reason | Scope |
|---|---|---|
| `pickle.load`, `pickle.loads` outside `selfdrive/modeld` model loading | Arbitrary code execution on load; model loading itself must verify the file hash first (GAP-22) | SR-Q |
| `eval`, `exec` | Code injection | All |
| `os.system`, `subprocess` with `shell=True` in SR-Q processes | Injection; uncontrolled timing | SR-Q |
| `random` without seed in control code | Non-reproducible behaviour | SR-Q |

### 10.3 Rules for SR-Q Python code

| ID | Rule | Reason / current state |
|---|---|---|
| PY-01 | Type hints on all new or changed functions in SR-Q modules | `ty` cannot give credit while imports are ignored |
| PY-02 | No silent substitution of invalid values: a non-finite or out-of-range actuator value shall raise an event, not only be clamped | `controlsd.py:140-147` clamps to 0 (GAP-19, FSR-06.04) |
| PY-03 | Freshness of every input used to compute an actuator command shall be checked in the consuming process | controlsd does not check freshness (GAP-16) |
| PY-04 | No new `Params` key that changes safety behaviour (mode, monitoring, actuator path) without an entry in [WP-W-09](WP-W-09-configuration-calibration-data.md) | GAP-20 |
| PY-05 | Exceptions shall not be swallowed in SR-Q processes; `except Exception: pass` is forbidden; failures are logged and raise an event | Review |
| PY-06 | Time arithmetic uses monotonic clocks (`time.monotonic`, `DT_*` constants) | Already enforced for `time.time` |
| PY-07 | Real-time processes do not allocate unbounded memory per cycle and keep GC disabled per `config_realtime_process` (`common/realtime.py:41-46`); new per-cycle allocations are reviewed | GAP-23 |
| PY-08 | Integration between processes only via msgq services declared in `cereal/services.py`; no new IPC side channels | FFI argument (WP-A-02) |

## 11. Code generators and generated code

| Generator | Output | Class | Rules |
|---|---|---|---|
| capnp (TL-10) | `openpilot/cereal/gen/**`, pycapnp runtime | QM | Generated code is not edited by hand; regenerated in CI; `check-dirty.sh` detects drift |
| acados (TL-11) | MPC solver C code | QM | Pinned version; longitudinal maneuver tests and process replay |
| rednose / sympy (TL-12) | EKF C code for `locationd` | QM | Pinned; replay |
| Cython (TL-13) | C++ extension sources | QM | Built with `-Werror` removed (`SConstruct:221-222`) — accepted for QM |
| DBC generator (TL-14) | `opendbc_repo/opendbc/dbc/*_generated.dbc` | QM (SR-Q for Toyota) | Generated DBC committed; CI checks no diff after regeneration |
| tinygrad (TL-09) | `*_tinygrad.pkl` | QM / PAS 8800 | [WP-W-10](WP-W-10-ml-engineering.md) |

No code generator is used for E-03. **G-01:** introducing one requires a WP-P-07 classification at the envelope ASIL before use.

## 12. C++ guidelines for host daemons (E-01, QM)

- **CPP-01** `-Werror` with the warnings of `SConstruct:128-140` stays on.
- **CPP-02** `pandad` (`openpilot/selfdrive/pandad/*.cc`) is SR-Q because it sets the safety mode and parameter (`panda_safety.cc:56-70`) and sends the heartbeat. Changes to it follow SR-Q review and must not add new panda control commands without an FFI analysis.
- **CPP-03** No raw `new`/`delete` in new code; RAII containers.
- **CPP-04** cpplint filter set as used in `opendbc_repo/lefthook.yml:24` also for `openpilot/selfdrive/pandad` (OI-11).

## 13. Interface schemas (Cap'n Proto)

- **CAP-01** Field ordinals are never reused or renumbered; removed fields move to `deprecated.capnp` or keep their slot with a `Deprecated` suffix.
- **CAP-02** A type change of an existing field is forbidden; add a new field.
- **CAP-03** Any change to `CarParams` (`opendbc_repo/opendbc/car/car.capnp`), `carControl`, `carState`, `selfdriveState`, `driverMonitoringState`, `modelV2` or `pandaStates` is SR-Q and needs an impact analysis on [WP-W-09](WP-W-09-configuration-calibration-data.md) and the HSI ([WP-S-05](../03-system/WP-S-05-hsi-specification.md)).

## 14. Modelling and notation guidelines

LionDriver does not use model-based development for production code. Models appear only in work products.

| Use | Notation | Rules |
|---|---|---|
| Architecture (system, software) | Block diagrams as Markdown tables plus ASCII or Mermaid diagrams; one viewpoint per diagram | Every block has an element ID from the element catalogue (`assurance/trace/elements.yaml`, WP-P-06 OI-4); every arrow names the interface (IF-xx) |
| State machines (engagement, safety modes, selfdrived) | State-transition tables (state, event, guard, action, next state) | Tables are normative; diagrams are illustrative. Guards reference code lines |
| Data flow | Table of producer → service/message → consumer with rate and timeout | Rates from `cereal/services.py` |
| Requirements | YAML per [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) | Markdown tables must match YAML (WP-P-06 K11) |
| Timing | Tables in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md); units in ms | |

## 15. Compliance status at the baseline

| Area | Status | GAP / OI |
|---|---|---|
| MISRA analysis of opendbc safety | Runs in upstream CI; clean with 6 global + 8 inline MISRA suppressions, no deviation records | GAP-13, GAP-39 |
| MISRA analysis of panda | Runs on `main.c` only; bootstub excluded | GAP-13 |
| Analyser self-test | `misra/test_mutation.py` samples 2 of 10 injected rule patterns per run (opendbc `test_mutation.py:24-46`; panda `test_mutation.py:28-63`) | WP-P-07 TL-04 |
| Release build used in tests | Only compiled, not tested (`test_release_build.py`) | GAP-41 |
| Defensive checks on SoC-provided configuration | Missing | GAP-09 |
| Coding guideline document | This document (new) | — |
| LionDriver CI enforcement | None for E-03 | GAP-39, OI-1 |

## 16. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Add the opendbc safety MISRA job (and panda MISRA job) to LionDriver CI on `liondriver-dev` (D-03, GAP-39) | Maintainer | G3 |
| OI-2 | Confirm MISRA rule categories in §9 against the licensed MISRA C:2012 document; complete all "RATIONALE TBD" entries and get them approved | Safety engineer | G3 |
| OI-3 | Write a MISRA compliance summary (rules and directives) for the release configuration | Safety engineer | G3 |
| OI-4 | Review E-03 for single-exit and bounded-loop conformance (ENV-R-03, ENV-R-04) | Reviewer | G3 |
| OI-5 | Select a complexity metric tool (e.g. lizard or pmccabe) and classify it in WP-P-07 | Maintainer | G3 |
| OI-6 | Document ISR/main-loop shared data (ENV-R-12) in WP-W-03 | SW architect | G3 |
| OI-7 | Stack-usage analysis with `-fstack-usage` and call graph (ENV-R-14) | Maintainer | G3 |
| OI-8 | Extend target warnings (CF-02) and fix findings | Maintainer | G3 |
| OI-9 | Decide whether to replace the GNU statement-expression macros with typed inline functions to remove DEV-09/DEV-10/DEV-12/DEV-13 | Maintainer | G3 |
| OI-10 | Change request: add the LionDriver banned APIs (§10.2) to `pyproject.toml` | Maintainer | G3 |
| OI-11 | Extend cpplint to `openpilot/selfdrive/pandad` | Maintainer | G4 |
| OI-12 | Add the bootstub variant to the panda MISRA run (WP-P-07 K-5) | Maintainer | G3 |
