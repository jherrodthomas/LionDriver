# Change impact: relay malfunction latched for the ignition cycle in the reference build

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It closes the part of DFA DM-25 found missing after the opendbc `515b9a2` pin ([WP-A-03](../../08-analyses/WP-A-03-dependent-failure-analysis.md) DFI-07).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-17: LionDriver pins panda `0a7da85` (the single commit of [jherrodthomas/panda#17](https://github.com/jherrodthomas/panda/pull/17), on top of `a55bdfc`; once #17 merges it is on the fork's `master` with the same tree as the merge commit, so the pin stays); unit-tested and MISRA-clean; not verified on the bench or the vehicle; not reviewed independently** |
| Change requests | [jherrodthomas/panda#17](https://github.com/jherrodthomas/panda/pull/17); this LionDriver PR (pin) |
| Reference configuration affected | Yes, in the reference build only (`LIONDRIVER_REFERENCE=1`, the default) |
| Decision | The project lead approved the fix on 2026-10-17 (chat). The DFA offered two options: keep the relay malfunction across a mode set, or refuse TOYOTA again within the ignition cycle. The second was chosen as a reversible technical choice: it fits the panda's existing ignition-cycle lock (DR-05) and leaves the opendbc safety model checked by the SM-TOY-AUTH back-to-back run unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | DFA | Requirements / design | Verification |
|---|---|---|---|---|---|
| panda `0a7da85` | `board/reference_lock.h`, `board/main.c`, `tests/reference_lock/` | A relay malfunction seen in the current ignition cycle is latched by the reference lock: from the 8 Hz tick, and from `set_safety_mode()` just before `set_safety_hooks()` clears opendbc's `relay_malfunction` (so internal mode changes, such as heartbeat loss, are covered). While latched, host request `0xdc` for TOYOTA is refused and counted in the health packet; SILENT and NOOUTPUT stay available. The latch clears when the 1 Hz tick sees the ignition off | DM-25: the relay-malfunction part now exists (unverified) | LD-DES-001 DR-05 pattern; TSR-513 | Host tests: 4 new (18 in the file), 3 fail without the gate; panda MISRA, both variants, run locally; LionDriver CI on this pin. Simulation L1 plant and L2 column results regenerated: only the printed panda commit changes (the reference lock is not in the simulated safety code). HIL: not run |

## 2. Behaviour to watch

| Change | Normal-driving risk | How it is bounded |
|---|---|---|
| Latch | A false relay malfunction (for example a late stock frame during the 1 s transition) now blocks the car mode until the ignition goes off, not only until the next mode set | Availability only, in the safe direction; the driver restarts the car. Count occurrences on the bench and in the vehicle tests (OI-1) |
| Latch | A real stuck harness switch is no longer hidden by a mode cycle and a quick re-engagement | The purpose of the change |

## 3. Open items

| ID | Item |
|---|---|
| OI-1 | HIL / bench: inject a relay malfunction, cycle the safety mode, and confirm TOYOTA is refused until ignition off (with DFA DM-22 and HIL `test_11_reference_lock`) |
| OI-2 | ~~Re-pin LionDriver to the fork's merge commit~~ Not needed: `0a7da85` is on the fork's `master` once jherrodthomas/panda#17 merges, as `tools/release/check-submodules.sh` requires, and its tree equals the merge commit's |
| OI-3 | DFA: DFI-07 / DM-25 records, WP-A-03 and WP-A-02 notes (DFA owner) |
