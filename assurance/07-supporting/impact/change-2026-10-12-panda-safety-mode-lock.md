# Change impact: safety-mode lock in the LionDriver reference build

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins panda `9f60e17`, opendbc `aff4033`; follow-ups at panda `3859fa8`, opendbc `5b5a4ba` (merge commits on the forks' `master`); not yet verified on hardware (HIL bench D-04); not reviewed independently.** |
| Change request | [jherrodthomas/panda#4](https://github.com/jherrodthomas/panda/pull/4), stacked on panda#3 and panda#1 |
| Range | panda `a35d1c6..7e2d148` (branch `claude/safety-mode-lock`) |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE=1`). Since the follow-up below, openpilot's own build (`SConstruct`) builds the panda firmware with the flag by default; opt-out is `LIONDRIVER_REFERENCE=` (empty) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `d0fbeec`, `7e2d148` | `SConscript`, `board/reference_lock.h` (new), `board/main_comms.h`, `board/main.c`, `tests/misra/test_misra.sh`, `tests/misra/checkers.txt`, `tests/reference_lock/` (new) | With `LIONDRIVER_REFERENCE=1`, host request `0xdc` accepts only SILENT, NOOUTPUT, ELM327 and TOYOTA with parameter 73; in TOYOTA only NOOUTPUT or SILENT. `0xdf` is refused in every mode (alternative experience stays 0). `0xc5`, `0xd8`, `0xdb`, `0xde`, `0xe5`, `0xe6`, `0xe7`, `0xe8`, `0xf1`, `0xf9`, `0xfc` are refused in a car mode. A rejected request has no effect and is printed to the debug console. Internal mode changes are not gated | Yes | No | No | Yes (a compromised SoC can no longer select another mode or parameter, or reconfigure CAN in a car mode) | FSR-01.10; GAP-09, GAP-44, GAP-49; SG-01, SG-07 | WP-S-02 (TSR-512, TSR-513 Impl), WP-W-02 (SWSR-512, 512a, 513), WP-C-01 (new AoU, §3), gap assessment (GAP-09, GAP-49), WP-W-06 (new unit tests), WP-V-05 (request injection in TOYOTA mode), TARA | Builds (reference debug and release); MISRA, both variants; host unit tests; HIL: each refused request in TOYOTA mode, ignition-off power save sequence | Take with panda#1 and #3 after review and HIL evidence |

## 2. Effect on the requirements

| Requirement | With this change | Remaining |
|---|---|---|
| TSR-512 / SWSR-512 (mode and parameter lock) | Met in the reference build | "Rejected **and reported**": only the debug console. Reporting to the host needs a health packet field (OI-1) |
| SWSR-512a (alternative experience fixed) | Met in the reference build (reset value 0) | — |
| TSR-513 / SWSR-513 (requests refused in a car mode) | Met for the SWSR-513 list, and `0xd1` param 1 (softloader entry, SWSR-511a; `7e2d148`) | `0xc0`, `0xb0`, `0xb1`, `0xf6` still to be confirmed (WP-W-02 OI-5) |
| "In release builds" | The lock is tied to `LIONDRIVER_REFERENCE`, not to `RELEASE`. The reference release build is `RELEASE=1 LIONDRIVER_REFERENCE=1` | Release procedure must build with both flags (OI-2) |

## 3. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| Alternative experience fixed at 0 | If the user turns off "disengage on accelerator" (or any setting that sets alternative-experience bits), the host and panda disagree and openpilot reports a controls mismatch. New assumption of use: the reference build is used with the default alternative experience | Add an AoU to WP-C-01 on integration (OI-3); host-side guard (hide the toggle in the reference build) as a follow-up |
| Ignition off | `pandad` sends `0xe7` (power save) before NOOUTPUT; the first `0xe7` is refused in TOYOTA and succeeds on the next loop | HIL: parked-car current after ignition off |
| Any car other than the reference | Refused: TOYOTA with another parameter, or any other brand, stays in the previous mode, so openpilot cannot engage | Intended for the reference build |

## 4. Verification results

| Check | Result |
|---|---|
| `LIONDRIVER_REFERENCE=1 scons`; `RELEASE=1 LIONDRIVER_REFERENCE=1 scons` | Pass (`-Werror`) |
| `tests/misra/test_misra.sh` (standard and reference variants) | Clean; `checkers.txt` regenerated for the new variant |
| `tests/reference_lock` (host, real `ControlPacket_t` and mode numbers) | Pass. Covers mode requests outside and inside TOYOTA, parameter variants, `0xdf` in every mode, the SWSR-513 list in car and non-car modes, and the requests `pandad` sends onroad |
| Mutation check | `0xe7` not gated; parameter compared on 8 bits: each fails a test |
| HIL / device | **Not run** (GAP-30; HIL bench plan D-04) |

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Closed 2026-10-12: refused requests are counted in the health packet (`requests_rejected_pkt`, saturating) and published as `pandaState.requestsRejected`; `pandad` logs every increase ([jherrodthomas/panda#6](https://github.com/jherrodthomas/panda/pull/6), panda `3859fa8`). No driver-facing alert yet | — |
| OI-2 | Partly closed: the top-level `SConstruct` sets `LIONDRIVER_REFERENCE=1` for the panda firmware unless the variable is set (follow-up §6), so every openpilot build, including on the device, has the lock. Still open: `RELEASE=1` with the LionDriver key (D-09) and recording the flag in WP-P-01 | Release |
| OI-3 | Add the alternative-experience AoU to WP-C-01 and decide the host-side guard | Integration |
| OI-4 | Confirm `0xc0`, `0xb0`, `0xb1`, `0xf6` (WP-W-02 OI-5). `0xd1` param 1 is gated in a car mode since `7e2d148` | Later change |

## 6. Follow-up: reference build by default (SW FMEA SWF-ACT-009, PFMEA PFM-ACT-001)

| Item | Detail |
|---|---|
| Change | Top-level `SConstruct`: around `SConscript(['panda/SConscript'])`, `LIONDRIVER_REFERENCE` is set to `1` unless already set, and removed again afterwards if it was unset |
| Why | The lock was compiled only when someone set the variable. No build path did, so the firmware that `pandad` flashes on the device had no lock, and the host could still select any safety mode and parameter |
| Effect | Device firmware built from LionDriver accepts only SILENT, NOOUTPUT, ELM327 and TOYOTA with parameter 73 (D-12: LionDriver-only devices for the reference configuration). A vehicle other than the reference configuration stays in ELM327 and cannot engage. `0xdf` is refused; openpilot always sends alternative experience 0 (`card.py:111`), so there is no mismatch (AOU-14). The comma body firmware (`body_h7`) also gets the flag; the body is out of scope |
| Opt-out | `LIONDRIVER_REFERENCE=` (empty) for development on other vehicles; such firmware is outside the safety claims |
| Not affected | opendbc `libsafety` for the tests reads the variable at import time in the test process, not during the build, so openpilot's car-model tests are unchanged. The variable is restored after the panda SConscript |
| Verification | The exact `SConstruct` block, run in front of the real `panda/SConscript` with scons 4.11.1 and arm-none-eabi-gcc 13.2.1 (the pins of the fork CI): unset → `-DLIONDRIVER_REFERENCE` on every firmware compile; empty → absent. Real compile of `panda_h7` with `-Werror` passes; the signed image contains the reference-lock code. The full openpilot build was not run locally (it needs acados and other device dependencies); CI builds it |
| Open | Host-side check that the running panda firmware is a reference build: done, §7. RELEASE build with the LionDriver key (D-09) |

## 7. Follow-up: the host requires a reference panda build (TSR-514, SWSR-514h)

| Item | Detail |
|---|---|
| Change request | jherrodthomas/panda#12 (firmware flag) and this LionDriver change (host check); panda pinned at `14f8f15` (branch `claude/reference-build-health-flag`) until panda#12 is merged |
| Change, firmware | `HEALTH_FLAG_REFERENCE_BUILD` (bit 12) is set in every health packet of a firmware built with `LIONDRIVER_REFERENCE` (`reference_build_health_flags()`, `board/reference_lock.h`), 0 otherwise. The Python library reports it as `health()['reference_build']` |
| Change, host | `SConstruct` exports `liondriver_reference` from the same setting that builds the firmware (§6); `selfdrive/pandad/SConscript` then compiles `pandad` with `LIONDRIVER_REFERENCE`. Before it sets the car safety mode from `CarParams`, `pandad` reads the health packet; without the flag (or if the read fails) it logs an error and sets NOOUTPUT instead. `pandaState.referenceBuild` (`@45`) carries the flag in the logs |
| Why | §6 makes LionDriver build the reference firmware, but a panda flashed with other firmware (upstream openpilot, a development build, a different fork) would still accept any safety mode, and the host would configure it. The lock must be present on the running panda, not only in the build |
| Effect | On a panda without the reference build, the safety model stays NOOUTPUT (no TX), `selfdrived` sees it differ from `CarParams` and raises `controlsMismatch` (no entry, "Controls Mismatch"): no engagement. `pandad` normally reflashes the panda with the firmware of the same build at start-up, so this is the fallback for a failed or skipped flash and for a panda programmed elsewhere |
| Opt-out | `LIONDRIVER_REFERENCE=` (empty) builds neither the firmware lock nor the host check; the two cannot be built mismatched |
| Alert | `selfdrived` raises `pandaNotReferenceBuild` (`@106`) when the car needs a car safety mode but, after the 10 s settling time that also applies to `controlsMismatch`, the panda is still in NOOUTPUT and does not report the reference build: "Panda Firmware Not Verified" (no entry, and a permanent "Not a LionDriver build: reflash"). In a build without `LIONDRIVER_REFERENCE`, `pandad` configures the car mode as before, so the event does not occur |
| Not covered | The check runs once per onroad transition, before the car safety mode is set. Detection of a debug (non-release) build stays open (D-09) |
| Verification | Firmware: `tests/reference_lock` (flag set only with `LIONDRIVER_REFERENCE`; C and Python definitions agree; flag bits unique), full panda suite 81 tests (44 HIL skipped), MISRA (cppcheck) for both variants, `panda_h7` compiled with `-Werror` in both variants. Host: `panda_safety.cc` and `pandad.cc` compiled with openpilot's warning flags against generated cereal headers, with and without `LIONDRIVER_REFERENCE`; the exact `SConstruct` and `pandad/SConscript` blocks run in scons 4.11.1: unset or `1` → both firmware and `pandad` defined, empty → neither. Not run: the full openpilot build (CI builds it) and HIL (D-04: a panda with non-reference firmware must not reach TOYOTA mode) |

