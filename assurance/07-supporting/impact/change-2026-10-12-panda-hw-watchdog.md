# Change impact: independent hardware watchdog on the safety MCU

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins panda `9f60e17`, opendbc `aff4033`; follow-ups at panda `3859fa8`, opendbc `5b5a4ba` (merge commits on the forks' `master`); not yet verified on hardware (HIL bench D-04); not reviewed independently.** Deviations D-1 and D-2 accepted as interim by the maintainer on 2026-10-12 (§2). Follow-on change panda#3 proposes to resolve D-1 and D-3 (§7) |
| Change request | [jherrodthomas/panda#1](https://github.com/jherrodthomas/panda/pull/1) (draft); follow-on [jherrodthomas/panda#3](https://github.com/jherrodthomas/panda/pull/3), stacked on panda#1 (§7) |
| Range | panda `92eb565..16cd27a` (branch `liondriver/hw-watchdog`; `b8d046b` and `16cd27a` add debug-only fault-injection hooks and the HIL test, no change to release-image behaviour. panda#3 contains them through merge `b9596ed`); LionDriver pin stays at `92eb565` until panda#1 is merged to the fork's `master` |
| Reference configuration affected | Yes: the panda firmware runs on the reference device |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `6c7bf48`, `14b883b`, `32b8fd9`, `361c7a2` | `board/drivers/hw_watchdog.h` (new), `board/drivers/harness.h`, `board/drivers/drivers.h`, `board/main.c`, `board/sys/power_saving.h`, `tests/hw_watchdog/` (new) | IWDG1 (LSI, /4, reload 1399, nominal 175 ms) starts inside `set_intercept_relay()` the first time the relay is energised, on every path, including the `0xc5` debug command (`361c7a2`; the first version started it only from `set_safety_mode()`). It is fed from the 8 Hz tick only if the main loop ran since the previous tick. `enter_stop_mode()` resets first if the IWDG runs. A main-loop hang, tick hang or hang with interrupts disabled now ends in a reset (relay released, restart in SILENT) instead of a hang with the relay energised | Yes | No | No | No | SG-01, SG-07; H-01, H-08; GAP-07, GAP-43 (partly), DF-01, DF-33 (partly) | WP-S-02 (TSR-501 Impl column), gap assessment (GAP-07, GAP-43), WP-W-06 (new unit tests), WP-V-05 (MCU hang tests), WP-S-04 (detection time), WP-H-03 (diagnostic coverage for MCU hang), WP-K-01 (DF-01, DF-33) | Firmware build (debug, release); host unit tests; MISRA; HIL fault injection (main-loop hang, tick hang, interrupts disabled) in a car mode; relay drop-out timing; stop-mode entry after a drive | Take after review, with the deviations in §2 accepted or resolved, and after HIL evidence |

## 2. Deviations from TSR-501 (v0.3)

| # | TSR-501 requires | This change | Effect | Proposed resolution |
|---|---|---|---|---|
| D-1 | Reset within ≤ 0.1 s of a stall (SG-07 forwarding FDTI, [WP-S-04](../../03-system/WP-S-04-timing-ftti-budget.md) §3.6) | Nominal 175 ms | Meets the SG-01 bound (≤ 0.2 s; SG-01 FTTI 0.5 s). Does not meet SG-07: stock PCS forwarding may be lost for up to about 0.175 s plus relay drop-out before the stock path returns | Feed the IWDG from the ≥ 50 Hz periodic safety task of TSR-401/TSR-519 once it exists, then shorten the timeout to ≤ 0.1 s. Until then, record the SG-07 shortfall as a residual in WP-K-01 (DF-33 stays open). **Proposed resolution in panda#3 (§7): 100 Hz feed, 90 ms nominal; pending review** |
| D-2 | Started before the application runs | Started when the relay is first driven | Hangs in SILENT, NOOUTPUT or ELM327 are not detected. In those modes the relay is not energised, so the stock path is intact and SG-01/SG-07 are not affected | Resolved by amendment (draft, pending review): TSR-501 in WP-S-02 v0.4 and HWSR-501c in WP-H-01 v0.3 now require the start no later than the first relay energisation after a reset, on every path |
| D-3 | Window mode (HWSR-501b), so that servicing too early is also detected | Normal (non-window) mode | A runaway loop that keeps setting the main-loop flag and lets the tick run is not detected by the watchdog | **Accepted as interim by the maintainer on 2026-10-12.** Add the window when the feed moves to the ≥ 50 Hz safety task (D-1); until then a recorded residual. **Proposed resolution in panda#3 (§7): window mode, about 5 ms minimum feed interval; pending review** |

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
| HIL fault injection | **Not run**: no HIL bench yet (GAP-30). Test and fault-injection hooks written (`b8d046b`); bench plan in [hil-bench/](../../05-software/hil-bench/README.md) |

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
| OI-2 | Confirm the STM32H725 LSI tolerance and the timeout at both ends. With panda#3 this matters more: at an LSI 10 % slow the 90 ms nominal timeout reaches about 100 ms, the TSR-501 limit (§7). 2026-10-12: the STM32H725 datasheet could not be retrieved from the development environment; the LSI min/max still has to be read from it | Integration |
| OI-3 | HIL fault-injection evidence (needs the D-04 HIL bench). Test written: `tests/hitl/test_10_hw_watchdog.py` with a debug-only fault-injection build (`b8d046b`, `16cd27a`; on panda#3 also safety-task hang and early-feed window violation, `b9596ed`); bench plan in [hil-bench/](../../05-software/hil-bench/README.md) | Release |
| OI-4 | Closed 2026-10-12: a watchdog reset sets `HEALTH_FLAG_WATCHDOG_RESET` (read from `RCC->RSR` IWDG1RSTF at boot, then cleared with RMVF), published as `pandaState.watchdogReset`; `pandad` logs it ([jherrodthomas/panda#6](https://github.com/jherrodthomas/panda/pull/6), panda `3859fa8`). Not yet checked on hardware (`test_10_hw_watchdog`) | — |
| OI-5 | Review panda#3 (§7). If accepted, D-1 and D-3 close and the WP-K-01 residuals for them are not needed | Integration |

## 7. Follow-on change: 100 Hz safety task and window mode (panda#3)

[jherrodthomas/panda#3](https://github.com/jherrodthomas/panda/pull/3) is stacked on panda#1 (branch `claude/safety-task-100hz`, `361c7a2..b9596ed`; `b9596ed` merges in the fault injection and HIL test from panda#1). It is integrated with panda#1, not separately: the pin moves once both are merged to the fork's `master` with merge commits.

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `171fcdf` | `board/stm32h7/stm32h7_config.h`, `board/stm32h7/peripherals.h`, `board/drivers/timers.h`, `board/main.c`, `board/drivers/hw_watchdog.h`, `tests/hw_watchdog/` | New 100 Hz safety task on TIM4 (SWSR-401a). It runs `safety_tick()`, which previously ran at 1 Hz, and feeds the IWDG, which was previously fed from the 8 Hz tick. Reload 719: 90 ms nominal. The task's interrupt rate is limited to 110 Hz and reports `FAULT_INTERRUPT_RATE_TICK` | Yes | No | No | No | SG-01, SG-07; D-1; GAP-07; DF-33 | WP-S-02 (TSR-501, TSR-401 Impl), WP-W-02 (SWSR-401a), WP-S-04 §3.6, WP-W-06, WP-V-05 | As §1, plus the safety-task period and jitter on the device | Take with panda#1 after review and HIL evidence |
| `a35d1c6` | `board/drivers/hw_watchdog.h`, `tests/hw_watchdog/` | Window mode (HWSR-501b). WINR 679 means a feed is accepted only about 5 ms or more after the previous feed. The first tick after the start is skipped, because the start is not aligned with the task | Yes | No | No | No | D-3; DF-01 | WP-H-01 (HWSR-501b), WP-H-03 (DC for a timer that runs too fast) | HIL: feed too early (task at more than twice the rate) gives a reset | As above |

Effect on the deviations in §2 (proposed; pending review, not a decision):

| # | With panda#3 |
|---|---|
| D-1 | 90 ms nominal is within ≤ 0.1 s if the LSI is no more than 10 % slow (OI-2). Detection time is then the timeout only, because the main-loop flag is checked at every 10 ms feed |
| D-3 | Resolved. A feed that comes too early, from a task running much too fast or an interrupt storm, resets the MCU. A runaway main loop cannot feed on its own, because only the task feeds |

Not changed by panda#3: the opendbc RX timeout is still max(10 periods, 1 s). `safety_tick()` now acts on it within 10 ms instead of up to 1 s, but meeting TSR-401 needs a separate opendbc change.

Verification of panda#3 (host only):

| Check | Result |
|---|---|
| `tests/misra/test_misra.sh` (all targets built with `-Werror`, then cppcheck MISRA) | Pass |
| `python3 -m unittest tests.hw_watchdog.test_hw_watchdog` | 8/8 pass. New: window configured, first tick after start skipped, window open before the next feed is due and long enough to catch a task that runs too fast (LSI ±10 %), timeout below 0.1 s |
| Mutation check | Two planted defects (no skipped first tick; window not set) each fail a test |
| HIL / device | **Not run** (GAP-30). Do not flash a car device before bench evidence |

## Addendum: further work products affected (2026-10-12)

The software alignment audit ([RR-2026-008](../../05-software/reviews/RR-2026-008.md) F-30) found that this change also affects: WP-W-01 (§7 build configuration), WP-W-05 (watchdog unit), WP-W-09 (CD-03 IWDG timing). These were updated in the RR-2026-008 alignment change, not in the change above. The original "WPs affected" entries are left as recorded.
