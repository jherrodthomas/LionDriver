# Change impact: panda pin to `fd0a6a7` (car-mode allow-list of host requests, SWSR-513, 513a, 513b)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-11-03** in this LionDriver PR; host-tested; not verified on hardware; not reviewed independently |
| Pin | panda `0e8a7b9` → `fd0a6a7` (merge commit of [jherrodthomas/panda#25](https://github.com/jherrodthomas/panda/pull/25), change commit `49591fb`). opendbc unchanged |
| Decision | Register DQ-147 A (project lead, 2026-10-26): in car modes the reference lock becomes an allow-list of what the host sends while driving. The list is the FSC/TSC owner's WP-S-05 §4.2a, confirmed against `pandad`, `pandad.py` and the Python library in this change. The lead approved the panda merge in chat on 2026-11-03 ("Merge, then pin") |
| Requirements | TSR-511, TSR-512, TSR-513; SWSR-511a, SWSR-513 (rewritten), SWSR-513a and SWSR-513b (new) |
| Reference configuration affected | Yes, reference build only (`LIONDRIVER_REFERENCE`); other builds are unchanged |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| panda `49591fb` | `board/reference_lock.h`, `tests/reference_lock`, `tests/hitl/test_11_reference_lock.py` | In a car mode only the allow-list is accepted: `pandad`'s loop (`f3`, `d2`, `c2`, `b0`, `b1`, `b2`, `c0`, `e0`), the reads of a `pandad` restart (`c3`, `c1`, `dd`, `d6`, `d3`, `d4`), `dc` as SWSR-512 restricts it, and `e7` with param1 0. Before, the gate was a deny-list and every request it did not name was accepted in TOYOTA. `c5`, `de`, `e5`, `e6`, `f8`, `f9`, `fc` are now refused in every mode. After TOYOTA, `d1` param 1 and `db` stay refused outside a car mode until the ignition is seen off. The gate is split into three helpers and the list is a table | Yes (freedom from interference of the QM host, TSR-513) | No | No | Yes | WP-S-05 §4.2a findings; GAP-24 (part) | WP-W-02 SWSR-511a, 513, 513a, 513b, OI-5 | panda host tests, panda MISRA, HIL `test_11` | DQ-147 A; lead, chat 2026-11-03 |
| this PR | `panda`, WP-W-02 v0.54, `tools/ci/complexity_exceptions.toml` (the `reference_request_allowed` exception, CCN 29, removed: every new function is within the ENV-R-07 limits), sim results (pinned SHA only) | Pin; records | — | — | — | — | — | — | — | — |

## 2. Effect on the host

- `pandad`'s driving loop and its restart path are all on the list, so engagement and a `pandad` restart while driving work as before.
- The Python library's `connect()`, which `pandad.py` uses at every start, writes `f8` and `de` per bus. These are now refused and counted, about 4 per boot. `pandad` logs each new rejection as an error. Nothing else changes (OI-1).
- At ignition off `pandad` sends power save (`e7` param1 1) before NOOUTPUT. That request was already refused in a car mode before this change; the order is a host follow-up (OI-1).

## 3. Verification results

| Check | Result |
|---|---|
| panda host test (local) | `tests/reference_lock`: 22 tests pass, including a sweep of all 256 request codes in TOYOTA. Six tests fail on the gate before the change |
| panda host suites (local) | All eight suites pass |
| panda MISRA (local) | cppcheck MISRA C:2012 clean in both builds, with the host gcc include path (the ARM toolchain is not installed locally; CI runs the real script) |
| ENV-R-07 (local) | `check_complexity.py` passes; one exception fewer |
| HIL | Not run (D-04). `test_11` now expects the CAN bit rate to stay refused outside a car mode |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Host follow-up: `pandad.py` connects without the default configuration writes, `pandad` sets NOOUTPUT before power save and sends no `0xdf` to a reference build (WP-W-02 OI-5) | Next host PR |
| OI-2 | A separate counter for `0xc0` in a car mode (new health-packet field, WP-S-05 §4.2a) | Follow-up panda PR |
| OI-3 | HIL drive with a forced `pandad` restart, to confirm the restart path needs nothing beyond the list | HIL bench (D-04) |
