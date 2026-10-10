# WP-P-07 Software Tool Classification and Qualification

| Field | Value |
|---|---|
| Work product | WP-P-07 Software tool classification and qualification |
| Standard reference | ISO 26262-8:2018 §11; ISO/SAE 21434:2021 §5 (tool management); ISO/PAS 8800:2024 (tools for AI development, informative) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (qualification effort driven by the envelope ASIL from WP-C-03) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review CR-09 per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) (I2 minimum) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Classifies every software tool used to develop, build or verify LionDriver and plans qualification for tools that reach TCL2 or TCL3. Closes the planning side of GAP-34 ([gap assessment](../00-assessment/gap-assessment.md)). Tool versions are configuration items ([WP-P-01](WP-P-01-configuration-management-plan.md) CI-8).

The envelope ASIL is not yet approved (HARA [WP-C-03](../02-concept/WP-C-03-hara.md) is Draft; revision 0.2 rates SG-01 at ASIL D). This plan assumes the envelope may reach ASIL D and plans qualification methods accordingly; it is re-checked once safety goals are approved (OI-1).

## 2. Method

For each tool and use case:

- **TI (tool impact):** TI2 if a malfunction can introduce an error into a safety-related element or fail to detect one; TI1 otherwise.
- **TD (tool error detection):** confidence that a tool error is prevented or detected by other measures in the process. TD1 high, TD2 medium, TD3 low.
- **TCL:** TI1 → TCL1; TI2 with TD1 → TCL1; TI2 with TD2 → TCL2; TI2 with TD3 → TCL3.
- **Qualification methods** named by the standard: (1a) increased confidence from use, (1b) evaluation of the tool development process, (1c) validation of the software tool, (1d) development in accordance with a safety standard. Method choice per TCL and ASIL is checked against the licensed copy.

A tool used only on QM elements (the SoC stack under T-03) needs no ISO 26262 qualification. It is still listed, because its output can affect SOTIF ([WP-M-08](../01-management/WP-M-08-sotif-plan.md)) and AI safety ([WP-M-10](../01-management/WP-M-10-ai-safety-plan.md)) claims and FFI.

## 3. Tool inventory and classification

Versions are taken from `uv.lock` (openpilot) and `opendbc_repo/uv.lock` (opendbc tests) at the baseline unless stated.

| ID | Tool | Version / source | Use case | Target element | TI | TD | TCL | Rationale for TD |
|---|---|---|---|---|---|---|---|---|
| TL-01 | arm-none-eabi-gcc | 13.2.1 (`comma-deps-gcc-arm-none-eabi` 13.2.1.post103, PyPI wheel built by comma) | Compile panda firmware incl. opendbc safety for STM32H7 | Envelope (ASIL) | TI2 | TD3 | **TCL3** | Safety tests run on an x86 host build, not on the target binary. No target tests exist in the fork (GAP-30). Becomes TD2 once the safety test suite runs against the target build on a HIL bench (D-04) |
| TL-02 | Host C compiler `cc` (gcc on Linux CI, clang on macOS) | System compiler, **unpinned** (`libsafety_py.py` calls `cc`); top-level build forces `clang`/`clang++` (`SConstruct:179-180`), also unpinned | Build `libsafety.so` for safety unit tests; build host code | Envelope verification; QM host | TI2 | TD2 | TCL2 | A miscompile of the test library can hide a defect; tests run under both gcc and clang (Linux/macOS CI matrix in `opendbc_repo/.github/workflows/tests.yml`) and UBSan, which gives medium detection |
| TL-03 | SCons | 4.11.1 | Build orchestration for firmware and host | Envelope build | TI2 | TD2 | TCL2 | Wrong flags (e.g. DEBUG instead of RELEASE, `panda/SConscript:12-20`) are detectable by checking the version string `<builder>-<git8>-<type>` and binary hash at release ([WP-P-10](WP-P-10-release-management.md)) |
| TL-04 | cppcheck + MISRA C:2012 addon | opendbc: 2.21.0 from `git+https://github.com/commaai/dependencies.git@release-cppcheck` (resolved `b7253dd`); panda: `comma-deps-cppcheck` (version not in openpilot `uv.lock`; panda has no lockfile in tree) | MISRA and static analysis of `opendbc/safety` (`tests/misra/test_misra.sh`) and panda `board/main.c` (`panda/tests/misra/test_misra.sh`) | Envelope verification | TI2 | TD2 | **TCL2** | Self-test `misra/test_mutation.py` injects known violations and checks they are reported (samples a subset per run). Without that self-test it would be TD3 |
| TL-05 | gcov + gcovr | gcovr 8.6; gcov from the host gcc (unpinned); `llvm-cov gcov` on macOS | 100% line coverage gate (`opendbc/safety/tests/test.sh`, `--fail-under-line=100`) | Envelope verification | TI2 | TD2 | TCL2 | Mutation testing independently exposes untested code; disagreement between gcc and llvm gcov is accepted upstream (comment in `test.sh`) |
| TL-06 | `mutation.py` (in-house) with tree-sitter 0.26.0, tree-sitter-c 0.24.2 | opendbc submodule `229dc70` | Mutation testing of `opendbc/safety` | Envelope verification | TI2 | TD3 | **TCL3** | In-house, no external user base; a false "killed" verdict would not be noticed. Has a baseline smoke check that aborts if unmutated tests fail (`mutation.py:527-532`), which does not detect false kills |
| TL-07 | Python `unittest`, `unittest-parallel` 1.8.6, `tools/test_runner.py` (in-house), `libsafety_py.py` / cffi 2.1.1 harness | CPython 3.12.13 (`.python-version`) | Execute safety tests (opendbc) and openpilot unit tests | Envelope verification; QM | TI2 | TD2 | TCL2 | Harness errors could report false passes; detection relies on test counts and failing-test checks. Note: no pytest is used in this repository |
| TL-08 | `process_replay` (`process_replay.py`, `compare_logs.py`, in-house) | openpilot `8b8c6ae` | Regression oracle for controlsd, plannerd, dmonitoringd, etc. | QM stack (SWE.5 evidence) | TI2 (if used for safety claims) | TD3 | TCL3 / not required for QM | Reference logs come from `commaai/ci-artifacts` (`test_processes.py:70`), not fork-owned; no independent check of comparator |
| TL-09 | tinygrad | 0.14.0, submodule `d3f09c9`, `.gitmodules` tracks `branch = master` | Compile ONNX models to `*_tinygrad.pkl` (`openpilot/selfdrive/modeld/SConscript`) and run them | QM ML stack (SOTIF / PAS 8800) | TI2 (SOTIF) | TD3 | QM: no 26262 TCL; treat as TCL3-equivalent under PAS 8800 | Fork has no model replay (Jenkins only) |
| TL-10 | Cap'n Proto compiler + pycapnp | `comma-deps-capnproto` 1.0.1.post103; pycapnp 2.1.0 (openpilot lock) / 2.2.4 (opendbc lock) | Code generation and serialization for `cereal` and `car.capnp` | QM host, car interface | TI2 | TD2 | TCL2 (QM: not required) | Process replay and car tests exercise the generated code |
| TL-11 | acados | `comma-deps-acados` 0.2.2.post103 | Generate MPC solver code (`controls/lib/longitudinal_mpc_lib`) | QM host | TI2 | TD2 | TCL2 (QM: not required) | Longitudinal maneuver tests, process replay |
| TL-12 | rednose code generation (sympy 1.14.0) | rednose submodule `8671c17` (not initialized in this checkout) | Generate EKF code for `locationd` | QM host | TI2 | TD2 | TCL2 (QM) | Replay of `locationd` |
| TL-13 | Cython | 3.3.0 | Generate C for Python extensions on host | QM host | TI2 | TD2 | TCL2 (QM) | Unit tests |
| TL-14 | DBC generator | `opendbc_repo/opendbc/dbc/generator/generator.py` | Generate Toyota DBCs from sources | Host CAN parse/pack (SR-Q) | TI2 | TD2 | TCL2 | Car model tests, check-dirty on generated files |
| TL-15 | panda signing (`panda/board/crypto/sign.py`) and `tools/release/build_release.sh` | panda `92eb565` | Sign release firmware; assemble release | Envelope delivery (CS) | TI2 | TD2 | TCL2 | Bootstub verifies signature on device; hashes compared at release. Script embeds comma cert path `/data/pandaextra/certs/release` and comma identity |
| TL-16 | uv + lockfiles | uv **unpinned** (installed via `astral.sh/uv/install.sh`, `tools/setup_dependencies.sh:116`); lock hash-pinned | Resolve and install dependencies and toolchain wheels | All | TI2 | TD1 | TCL1 | Hash-pinned lock detects wrong artefacts; uv version itself should still be pinned |
| TL-17 | git, git-lfs | git system; `comma-deps-git-lfs` 3.6.1.post103 | Version control, large files | All | TI2 | TD1 | TCL1 | Content-addressed (SHA-1/SHA-256 oids); baseline manifest check |
| TL-18 | GitHub Actions | Hosted runners `ubuntu-24.04`/`ubuntu-latest`/`macos-latest` (fork fallback in `tests.yaml`) | Execute CI | All | TI2 | TD1 | TCL1 | Logs archived and reviewed for release evidence ([WP-P-10](WP-P-10-release-management.md)); runner images are not pinned (OI-6) |
| TL-19 | ruff 0.16.7, ty 0.0.80, codespell 2.4.3, cpplint 2.0.2, lefthook 2.1.17 | `uv.lock` / `opendbc_repo/uv.lock` | Lint, type check, style | QM | TI1 | — | TCL1 | No verification credit taken (ty ignores unresolved import/attribute, `pyproject.toml`) |
| TL-20 | coverage (Python) | 7.16.0 | Informational line coverage of openpilot | QM | TI1 | — | TCL1 | No threshold, no credit (GAP-36) |
| TL-21 | UBSan | via host compiler | Undefined-behaviour detection in safety tests | Envelope verification | TI1 | — | TCL1 | Additional measure; no credit claimed beyond TL-02 TD rationale |
| TL-22 | Jenkins (`Jenkinsfile`, `panda/Jenkinsfile`) | comma infrastructure | HIL, on-device tests | — | — | — | N/A | Not available to the fork (GAP-30) |

## 4. Known issues affecting the classification

| # | Issue | Evidence | Handling |
|---|---|---|---|
| K-1 | cppcheck does not always return a non-zero exit code on MISRA violations (cppcheck ticket 12440) | Comment and `grep` fallback in `opendbc_repo/opendbc/safety/tests/misra/test_misra.sh` and `panda/tests/misra/test_misra.sh` | The grep on "misra violation", "error", "style: " is part of the qualified use case; any change to it is SR-T |
| K-2 | cppcheck sourced from a mutable branch (`release-cppcheck`) and two different packagings (opendbc git dependency vs panda `comma-deps-cppcheck`) | `opendbc_repo/pyproject.toml`, `panda/pyproject.toml` | Pin one cppcheck build by commit/hash for both, in the LionDriver fork of `commaai/dependencies` or a LionDriver package |
| K-3 | Coverage is line coverage only; no branch or MC/DC | `test.sh` `--fail-under-line=100` | Add branch coverage (`gcovr --fail-under-branch`) and an MC/DC argument per [WP-W-06](../05-software/WP-W-06-software-unit-verification.md); gcovr qualification must then cover branch metrics |
| K-4 | MISRA suppressions file: 6 global MISRA rule suppressions (11.4, 11.5, 15.1, 19.2, 20.10, 2.5) plus `unmatchedSuppression` and an `unusedFunction` pattern; inline suppressions for GNU extensions | `opendbc_repo/opendbc/safety/tests/misra/suppressions.txt` | Deviation records in [WP-W-01](../05-software/WP-W-01-software-development-environment-guidelines.md) §9. Inline suppressions of the mandatory Rule 17.3 (`typeof` macros, `__WFI`) are not deviations: WP-W-01 records them as tool false positives (DEV-10, DEV-13, DEV-19), each needing a reproducer |
| K-5 | panda MISRA run uses `-UBOOTSTUB`, so the bootstub is not analysed | `panda/tests/misra/test_misra.sh` | Add a bootstub variant |
| K-6 | Safety unit tests compile `libsafety` with `-DALLOW_DEBUG` (except the release-build test) | `libsafety_py.py`; `tests/test_release_build.py` | Tests exercise a superset configuration; the release configuration must be covered explicitly ([WP-W-06](../05-software/WP-W-06-software-unit-verification.md)) |
| K-7 | Three accepted surviving mutants (two on the Toyota LTA path) are whitelisted in code | `mutation.py` `known_survivors` | Each needs a justification record; LTA path is not used by the reference configuration |
| K-8 | Host compiler, uv and CI runner images are unpinned | §3 | Pin (OI-6) |
| K-9 | pycapnp differs between the two lockfiles (2.1.0 vs 2.2.4) | `uv.lock`, `opendbc_repo/uv.lock` | Fork CI for opendbc tests should run with the superproject environment, or the difference is justified |
| K-10 | `tools/test_runner.py` ignores `process_replay/test_processes.py` and `tools/sim` | `IGNORED` in `tools/test_runner.py` | Process replay runs as its own CI job; record this in the tool use case |

## 5. Qualification plans (TCL2 and TCL3 tools in the ASIL path)

| Tool | TCL | Planned methods | Qualification activities | Evidence (to be produced) |
|---|---|---|---|---|
| TL-01 arm-none-eabi-gcc | 3 → 2 after HIL | 1a + 1c | Fix the exact compiler build (hash of the wheel). Restrict options (`-O` level, no LTO changes) to a documented set. Validation: run the opendbc safety test vectors against the target binary on the HIL bench (back-to-back host vs target results); review GCC 13.2 known-bug lists for the used options; compile a compiler test suite subset for Cortex-M7 | Tool qualification report TQR-01 |
| TL-02 host cc | 2 | 1a + 1c | Pin compiler version in CI; record versions in test logs; keep the gcc + clang dual run | TQR-02 |
| TL-03 SCons | 2 | 1a | Use history (SCons widely used); release check that the panda binary has build type RELEASE and is reproducible from the tag | TQR-03 (short) |
| TL-04 cppcheck + MISRA | 2 | 1a + 1c | Pin version; extend `misra/test_mutation.py` to run all injected rules (not a sample) at release; add injected cases for each MISRA rule the project claims; validate the grep fallback (K-1) | TQR-04 |
| TL-05 gcov/gcovr | 2 | 1a + 1c | Validation project: small C file with known line/branch coverage, checked each release with the pinned versions | TQR-05 |
| TL-06 mutation.py | 3 | 1c (+ 1d-style review as in-house tool) | Treat as LionDriver-owned software: requirements, review, tests. Validation: seed mutants with known outcome (one must survive, one must be killed) and check verdicts; report the mutation score per run | TQR-06 |
| TL-07 unittest harness | 2 | 1a + 1c | Validation: a deliberately failing test must fail the job; test counts compared run-to-run; harness code (`libsafety_py.py`) reviewed as SR-T | TQR-07 |
| TL-15 signing + release script | 2 | 1c | Validation in [WP-P-10](WP-P-10-release-management.md) dry-run: wrong key and tampered binary must be rejected by the bootstub on a bench device | TQR-15 (with WP-W-11) |

QM tools (TL-08 to TL-14) get confidence measures under SOTIF/PAS 8800 instead: pinned versions, fork-owned process-replay references, and for tinygrad a back-to-back comparison of compiled-model outputs against a reference ONNX runtime on a fixed input set ([WP-W-10](../05-software/WP-W-10-ml-engineering.md)). If any of them is later used to support an ASIL claim, it is reclassified here.

## 6. Tool management

| Rule | Detail |
|---|---|
| Version control | Every tool version in §3 is pinned in a lockfile or CI configuration; changes follow CT-4 in [WP-P-02](WP-P-02-change-management.md) with a re-check of TD and qualification |
| Environment record | CI jobs print tool versions; the baseline manifest ([WP-P-01 §8](WP-P-01-configuration-management-plan.md#8-baselines)) lists them |
| Use constraints | Each TQR states allowed options and known limitations; reviewers check them ([WP-P-05 §5.6](WP-P-05-verification-review-procedure.md#56-code-sr-a-also-used-for-sr-q-with-judgement)) |
| Supply chain (CS) | comma-built `comma-deps-*` wheels come from PyPI under comma's control; mirror the pinned artefacts in a LionDriver-controlled store and verify hashes (input to [WP-C-09](../02-concept/WP-C-09-tara.md)) |

## 7. Open items

| ID | Item |
|---|---|
| OI-1 | Re-check TI/TD/TCL and methods once the envelope ASIL is approved in WP-C-03 |
| OI-2 | Build the HIL bench (D-04) so TL-01 can move to TD2 |
| OI-3 | Pin a single cppcheck build for opendbc and panda (K-2) |
| OI-4 | Write TQR-01..07 and TQR-15 |
| OI-5 | Add branch coverage and an MC/DC strategy (K-3) |
| OI-6 | Pin host compiler, uv and CI runner images (K-8) |
| OI-7 | Determine the `comma-deps-cppcheck` version used by panda (no panda lockfile in tree) |
