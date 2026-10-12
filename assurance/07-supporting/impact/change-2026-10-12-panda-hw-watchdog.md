# Change impact: independent hardware watchdog on the safety MCU

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Draft: proposed change, not integrated.** The LionDriver `panda` pin is unchanged. Deviations D-1 and D-2 accepted as interim by the maintainer on 2026-10-12 (§2) |
| Change request | [jherrodthomas/panda#1](https://github.com/jherrodthomas/panda/pull/1) (draft) |
| Range | panda `92eb565..361c7a2` (branch `liondriver/hw-watchdog`); LionDriver pin stays at `92eb565` until panda#1 is merged to the fork's `master` |
| Reference configuration affected | Yes: the panda firmware runs on the reference device |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `6c7bf48`, `14b883b`, `32b8fd9`, `361c7a2` | `board/drivers/hw_watchdog.h` (new), `board/drivers/harness.h`, `board/drivers/drivers.h`, `board/main.c`, `board/sys/power_saving.h`, `tests/hw_watchdog/` (new) | IWDG1 (LSI, /4, reload 1399, nominal 175 ms) starts inside `set_intercept_relay()` the first time the relay is energised, on every path, including the `0xc5` debug command (`361c7a2`; the first version started it only from `set_safety_mode()`). It is fed from the 8 Hz tick only if the main loop ran since the previous tick. `enter_stop_mode()` resets first if the IWDG runs. A main-loop hang, tick hang or hang with interrupts disabled now ends in a reset (relay released, restart in SILENT) instead of a hang with the relay energised | Yes | No | No | No | SG-01, SG-07; H-01, H-08; GAP-07, GAP-43 (partly), DF-01, DF-33 (partly) | WP-S-02 (TSR-501 Impl column), gap assessment (GAP-07, GAP-43), WP-W-06 (new unit tests), WP-V-05 (MCU hang tests), WP-S-04 (detection time), WP-H-03 (diagnostic coverage for MCU hang), WP-K-01 (DF-01, DF-33) | Firmware build (debug, release); host unit tests; MISRA; HIL fault injection (main-loop hang, tick hang, interrupts disabled) in a car mode; relay drop-out timing; stop-mode entry after a drive | Take after review, with the deviations in §2 accepted or resolved, and after HIL evidence |

## 2. Deviations from TSR-501 (v0.3)

| # | TSR-501 requires | This change | Effect | Proposed resolution |
|---|---|---|---|---|
| D-1 | Reset within ≤ 0.1 s of a stall (SG-07 forwarding FDTI, [WP-S-04](../../03-system/WP-S-04-timing-ftti-budget.md) §3.6) | Nominal 175 ms | Meets the SG-01 bound (≤ 0.2 s; SG-01 FTTI 0.5 s). Does not meet SG-07: stock PCS forwarding may be lost for up to about 0.175 s plus relay drop-out before the stock path returns | Feed the IWDG from the ≥ 50 Hz periodic safety task of TSR-401/TSR-519 once it exists, then shorten the timeout to ≤ 0.1 s. Until then, record the SG-07 shortfall as a residual in WP-K-01 (DF-33 stays open) |
| D-2 | Started before the application runs | Started when the relay is first driven | Hangs in SILENT, NOOUTPUT or ELM327 are not detected. In those modes the relay is not energised, so the stock path is intact and SG-01/SG-07 are not affected | Resolved by amendment (draft, pending review): TSR-501 in WP-S-02 v0.4 and HWSR-501c in WP-H-01 v0.3 now require the start no later than the first relay energisation after a reset, on every path |
| D-3 | Window mode (HWSR-501b), so that servicing too early is also detected | Normal (non-window) mode | A runaway loop that keeps setting the main-loop flag and lets the tick run is not detected by the watchdog | **Accepted as interim by the maintainer on 2026-10-12.** Add the window when the feed moves to the ≥ 50 Hz safety task (D-1); until then a recorded residual |

Decision (2026-10-12, project maintainer): **D-1 and D-2 accepted as an interim step.** D-3, found afterwards, was also accepted as interim the same day: it stays a residual until window mode is added with the ≥ 50 Hz feed. D-1 stays a recorded residual (SG-07 forwarding not covered within 0.1 s) until the watchdog is fed from the ≥ 50 Hz safety task. D-2 is to be resolved by amending TSR-501. This is a maintainer decision, not an independent review (WP-M-06); the change still needs review and HIL evidence before release.

## 3. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| First sleep after a drive (comma four, stop mode) | One extra reset: the device is awake for about 2 s more before it sleeps | Current draw in a parked car on the reference device |
| Main loop or tick blocked longer than about 125 ms by legitimate code | Spurious reset, actuation lost and re-engagement needed | Code review of blocking paths; long drives with logging (field monitoring) |
| Watchdog reset not reported to the host | A watchdog reset looks like any other reboot in the logs | Follow-up: read `RCC->RSR` IWDG1RSTF and report it (health packet change) |
| Firmware update | The bootloader is entered through a system reset, which stops the IWDG | Flash cycle on the device |

## 4. Verification results

| Check | Result |
|---|---|
| `scons` debug and `CERT=board/crypto/certs/debug RELEASE=1 scons` | Pass (`-Werror`; panda and body images) |
| `tests/hw_watchdog/test_hw_watchdog.py` (host, fake registers) | 6/6 pass. Covers: no start before a relay mode, configuration, idempotent start, feed only after main-loop progress, bounded wait on stuck update flags, timeout between the 125 ms feed period and the 0.2 s SG-01 bound |
| Mutation check of the tests | Two planted defects (feed without the main-loop condition; timeout above 0.2 s) each fail a test |
| MISRA, `tests/misra/test_misra.sh` with local cppcheck 2.13 | No new finding classes: five 10.3 reports on `bool` initialisation and assignment, the same false positive the local build raises on existing code. The pinned cppcheck in panda CI is authoritative |
| HIL fault injection | **Not run**: no HIL bench yet (GAP-30) |

## 5. Work products to update on integration

None are changed yet, because the change is not integrated. When panda#1 is merged and the pin is moved:

- WP-S-02 TSR-501: Impl column to "Partial: IWDG started on first relay drive, 175 ms (D-1, D-2)"; regenerate `trace/items/tsr.yaml`.
- Gap assessment: GAP-07 to partly closed; GAP-43 to partly closed for the hang case.
- WP-W-06: add the host unit tests; WP-V-05: add the MCU-hang fault-injection cases.
- WP-K-01: update DF-01 and DF-33 with the remaining SG-07 shortfall (D-1).

## 6. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Closed 2026-10-12: the maintainer accepted D-1 and D-2 as interim (§2); the TSR-501 and HWSR-501c amendments for D-2 are drafted (WP-S-02 v0.4, WP-H-01 v0.3). D-3 accepted as interim (2026-10-12). Still needed: review of the amendments, and recording D-1 and D-3 as residuals in WP-K-01 on integration | Integration |
| OI-2 | Confirm the STM32H725 LSI tolerance and the timeout at both ends | Integration |
| OI-3 | HIL fault-injection evidence (needs the D-04 HIL bench) | Release |
| OI-4 | Report watchdog resets to the host | G3 |
