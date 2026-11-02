# Change impact: ENV-R-07 size and complexity check with lizard in CI

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to the CI workflow and its tooling (change types CT-4 and CT-5, [WP-P-02 §3](../WP-P-02-change-management.md#3-change-types)). The project lead decided that the ENV-R-07 limit (functions at most 60 logical lines and cyclomatic complexity 15, unless justified) is measured in CI with lizard and classified under WP-P-07 (register DQ-158 A, 2026-10-30). The same change classifies GitHub's dependency graph and Dependabot alerts in WP-P-07 (DQ-169 B); that part changes no file the CI runs.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-11-02**; the check passes locally on the current pins; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | **SR-T**: `.github/workflows/safety.yaml` matches `.github/workflows/**` ([safety-relevant-paths.txt](../safety-relevant-paths.txt)). The new `tools/ci/` files match no listed path, but they decide a verification result on the envelope, so they are SR-T by work-product impact (WP-P-02 §4 rule 2) |
| Reference configuration affected | No: no source, build flag or binary changes. The check reads the pinned opendbc and panda sources |
| Requirements | None changed. ENV-R-07 (WP-W-01 §6) is now measured; its limits are unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft, I0) / TBD: one code owner, with the tool impact noted in WP-P-07 (WP-P-02 §7.1, SR-T, I1) |

## 1. Change

| Change | Files | Effect | Verification |
|---|---|---|---|
| CI step | `.github/workflows/safety.yaml` (panda MISRA job; trigger paths) | After the panda MISRA analysis, and even when it fails, installs lizard by hash and runs the checker; uploads `complexity/env-r-07.md` with the build manifest | Workflow YAML parses; the step's two commands run locally with the same files |
| Checker and data | `tools/ci/check_complexity.py`, `tools/ci/complexity_exceptions.toml`, `tools/ci/lizard-requirements.txt` | Fails on a function over NLOC 60 or CCN 15 that is not listed, a listed function that grew, a stale entry, a scope entry with no file, or a lizard other than 1.24.1 | Local run at opendbc `f23b4fa`, panda `131320c`: 53 files, 376 functions, 14 over a limit, all listed, exit 0 |
| Self-tests | `tools/ci/test_check_complexity.py` | 12 tests of each failure rule on synthetic lizard output, and of the committed list | Run by the existing `unittest discover -s tools/ci` step of `assurance.yaml` |
| Records | WP-W-01 v0.8 (§3, ENV-R-07, OI-5), WP-W-05 v0.9.6 (OI-2), WP-P-07 v0.9.34 (TL-63, TL-64, TQR-63 plan, OI-15), WP-W-11 v0.7 (OI-1), WP-M-09 v0.9 (OI-4); `NLOC` and `CCN` added to the terms list | What is in place and what is left | `terms.py --check`, `check_links.py` |

## 2. Impact checklist (WP-P-02 §6)

- Change type: CT-5 (CI workflow) and CT-4 (a new pinned tool: lizard 1.24.1, pathspec 1.1.1, Pygments 2.21.0, by SHA-256).
- Class and matched paths: SR-T, `.github/workflows/safety.yaml` (`.github/workflows/**`).
- Reference configuration affected: no.
- Safety goals and requirements affected: none changed; ENV-R-07 evidence added.
- Work products updated: listed in §1.
- Hazard log, HARA, SOTIF, cybersecurity, FFI or DFA impact: none. The cybersecurity tooling row TL-64 changes no process step; Dependabot alerts are not turned on by this change.
- Envelope limits or detection times changed: no.
- Panda firmware rebuilt, safety mode or parameter changed: no.
- Models changed: no.
- Tools changed: lizard added as TL-63, TCL2 proposed (TI2, TD2), not qualified; GitHub dependency graph and Dependabot alerts added as TL-64, TCL1.
- Verification to re-run: the panda MISRA job (it now also runs the check) and the `tools/ci` unit tests.
- CI time: a few seconds for the install and the check.

## 3. Results at the current pins

lizard 1.24.1 on the 53 envelope files: 376 functions; 14 functions over a limit, all marked "to justify" in the exception list. No justification is recorded for any of them.

| Function | File | NLOC | CCN | Over |
|---|---|---|---|---|
| `comms_control_handler` | `panda/board/main_comms.h` | 224 | 60 | both |
| `toyota_tx_hook` | `opendbc/safety/modes/toyota.h` | 143 | 48 | both |
| `spi_rx_done` | `panda/board/drivers/spi.h` | 101 | 22 | both |
| `tick_handler` | `panda/board/main.c` | 95 | 31 | both |
| `set_safety_hooks` | `opendbc/safety/safety.h` | 94 | 10 | NLOC |
| `toyota_init` | `opendbc/safety/modes/toyota.h` | 89 | 14 | NLOC |
| `main` | `panda/board/main.c` | 86 | 14 | NLOC |
| `comms_control_handler` (bootstub) | `panda/board/flasher.h` | 72 | 15 | NLOC |
| `steer_torque_cmd_checks` | `opendbc/safety/lateral.h` | 69 | 17 | both |
| `enter_stop_mode` | `panda/board/sys/power_saving.h` | 67 | 5 | NLOC |
| `toyota_rx_hook` | `opendbc/safety/modes/toyota.h` | 66 | 20 | both |
| `can_rx` | `panda/board/drivers/fdcan.h` | 63 | 16 | both |
| `reference_request_allowed` | `panda/board/reference_lock.h` | 50 | 29 | CCN |
| `RSA_verify` | `panda/board/crypto/rsa.c` | 41 | 23 | CCN |

For information only: the other opendbc brand modes, outside the item, have 19 more functions over a limit; with lizard's modified count (`-m`, a switch counts once) `comms_control_handler` would be CCN 24 and `reference_request_allowed` CCN 16. ENV-R-07 uses the standard count.

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Justify or split each of the 14 functions; WP-W-01 does not yet say who approves an ENV-R-07 justification (WP-W-01 OI-5, WP-W-05 OI-2) | G3 |
| OI-2 | Write TQR-63 and confirm TCL2 in review (WP-P-07 OI-15) | G3 |
| OI-3 | A repository admin turns on Dependabot alerts; confirm what the dependency graph reads (WP-P-07 OI-15, TL-64) | G3 |
