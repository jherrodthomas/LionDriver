# Change impact: explicit interrupt priorities and atomic safety-configuration switch

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-12: LionDriver pins panda `52cad44` (merge commit of panda#10 on the fork's `master`); not yet verified on hardware (HIL bench D-04); not reviewed independently** |
| Change request | [jherrodthomas/panda#10](https://github.com/jherrodthomas/panda/pull/10) |
| Range | panda `c2e5d93..52cad44` |
| Reference configuration affected | Yes: every build of the panda firmware |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `65b75d3` | `board/drivers/irq_priorities.h` (new), `board/drivers/drivers.h`, `board/main.c`, `board/sys/faults.h`, `tests/irq_priorities/` (new) | Implements the prerequisites of [WP-W-03 §5.4.4](../../05-software/WP-W-03-software-architecture.md). `interrupt_priorities_init()` sets an explicit NVIC priority for each of the 21 enabled interrupts before any is enabled. All five classes (safety task, CAN, host, housekeeping, peripheral) are at level 8, so no ISR preempts another, as before. `set_safety_hooks` runs in a critical section (R-1). `fault_occurred` / `fault_recovered` run in a critical section (R-8). No functional behaviour change is intended | Yes | No | No | No | SG-01, SG-02; FSR-01.07, FSR-01.09; GAP-50 | WP-S-02 (TSR-519 Impl), WP-W-02 (SWSR-519), WP-H-01 (HWSR-519), WP-W-03 §5.4.4, WP-W-04 (SWF-48), WP-W-06 (host test) | Builds (all variants), MISRA, host tests; HIL: read back the NVIC priority registers; time the critical sections (WP-W-03 §5.4.5) | Taken (maintainer merged panda#10, 2026-10-12) |

## 2. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| Interrupts masked while the safety configuration is copied (`set_safety_hooks`) | Other interrupts, the safety task included, are delayed by the length of the copy and of the mode's init hook | WP-W-03 §5.4.5: worst-case critical-section length on the target; it adds to the safety-task jitter that the IWDG window tolerates (about 4.4 ms) |
| Interrupts masked in `fault_occurred`, which prints to the debug UART on a new fault | Only on the first occurrence of each fault bit; the print goes to a ring buffer | Same measurement |
| R-2 not changed in code | Under a future priority scheme, a revocation can be lost for at most one task period (10 ms); recorded as SWF-48 in [WP-W-04](../../05-software/WP-W-04-software-safety-analysis.md) | Re-assess when the scheme is adopted |

## 3. Verification results

| Check | Result |
|---|---|
| `scons` default, `LIONDRIVER_REFERENCE=1`, `FAULT_INJECTION=1`, `RELEASE=1 LIONDRIVER_REFERENCE=1` (debug cert) | Pass (`-Werror`; panda and body images) |
| `tests/misra/test_misra.sh` (standard and reference variants) | Clean |
| Host tests `tests/irq_priorities` (new), `heartbeat_monitor`, `reference_lock`, `usbprotocol` | Pass |
| Mutation check | Dropping one IRQ from the table, or setting the CAN class to 4, each fails a test |
| HIL / device | **Not run** (GAP-30; HIL bench plan D-04) |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Measure the worst-case critical-section and handler lengths on the target (WP-W-03 §5.4.5) before adopting the §5.4.2 levels | Priority scheme |
| OI-2 | HIL: read back NVIC IPR registers after start-up and compare with `irq_priorities.h` | Release |

## Addendum: further work products affected (2026-10-12)

The software alignment audit ([RR-2026-009](../../05-software/reviews/RR-2026-009.md) F-30) found that this change also affects: WP-W-05 (interrupt units), WP-W-09 (CD-03 if priority values are treated as configuration). These were updated in the RR-2026-009 alignment change, not in the change above. The original "WPs affected" entries are left as recorded.

## Addendum: interrupt count (2026-10-12)

The row above says "each of the 21 enabled interrupts". A code reading at panda `8aa8671` finds 20, and every one has an explicit priority: the 17 registered with `REGISTER_INTERRUPT` in the panda firmware and the three wake-up lines `EXTI1`, `EXTI4`, `EXTI9_5` enabled in `sys/power_saving.h:153-155`, against 20 `NVIC_SetPriority` calls in `drivers/irq_priorities.h`. `TIM8_UP_TIM13` is registered only by the comma body firmware (`board/body/main.c:99`), which is out of scope. The "21" is a miscount; no interrupt lacks a priority ([RR-2026-009](../../05-software/reviews/RR-2026-009.md) F-42).
