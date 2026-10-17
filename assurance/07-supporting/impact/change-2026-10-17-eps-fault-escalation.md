# Change impact: EPS-fault prompt after an override escalates after 1.5 s

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements TSR-607 (b) as decided by the project lead on 2026-10-16 (register DQ-342, option A) and closes the code part of System FMEA SFM-ACT-023.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-17 ([jherrodthomas/LionDriver#174](https://github.com/jherrodthomas/LionDriver/pull/174), `7158a9a`); TSR-607 (c) (DQ-366 A) in the follow-up PR; unit-tested in CI; not verified on the vehicle; not reviewed independently** |
| Change requests | This LionDriver PR |
| Reference configuration affected | Yes; the change applies to every build and every brand that reports `steerFaultTemporary` |
| Decision | DQ-342 A: gentle prompt for at most 1.5 s after an override or at standstill, then the take-over request. DQ-366 A: a fault that outlasts 1.5 s while the driver keeps steering gets the gentle prompt while they steer |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Requirements | Verification |
|---|---|---|---|---|
| openpilot `card` events | `selfdrive/car/car_events.py`, `selfdrive/car/tests/test_steer_fault_warning.py` | A temporary steering fault that starts within 1.5 s of a driver override, or at standstill, still gets `steerTempUnavailableSilent` (small alert, chime). That prompt is now limited to the first 1.5 s of the fault (`STEER_FAULT_SILENT_FRAMES`, counted from the first fault frame). If the fault is still present after that, the event is `steerTempUnavailable` (soft disable, take-over request). Before, once the silent prompt started, it was latched for the whole fault | TSR-607 (a), (b) | 6 new unit tests; 4 of them fail on the previous code (no escalation after an override, at standstill, after releasing the wheel, and on a returning fault) |

## 2. Timing

The first fault frame is frame 1. Frames 1 to 150 (0 to 1.49 s at 100 Hz) may get the lighter prompt; from frame 151 (1.50 s after onset) the take-over request is raised. This meets TSR-607 (b): prompt ≤ 1 s, take-over request ≤ 1.5 s after fault onset. A fault without a recent override is the take-over request from its first frame, as before (TSR-607 (a)).

## 3. Behaviour to watch

| Change | Normal-driving risk | How it is bounded |
|---|---|---|
| Escalation after 1.5 s | A hard override that trips the Toyota EPS for longer than 1.5 s now soft-disables instead of showing the small alert | This is the behaviour the lead chose (DQ-342 A); short override-induced faults stay quiet. Vehicle test to measure how often it happens (OI-1) |
| Driver holds the wheel through the fault onset | No alert for the first 1.5 s (upstream `no_steer_warning`); from 1.5 s the lighter prompt while the driver keeps steering (TSR-607 (c), DQ-366 A). On release, the take-over request at once | A fault shorter than 1.5 s while steering stays quiet, as upstream; covered by `test_short_fault_while_holding` |

## 4. Open items

| ID | Item |
|---|---|
| OI-1 | Vehicle or replay: count override-induced EPS faults longer than 1.5 s on the reference car, to confirm the nuisance rate behind DQ-342 A |
| OI-2 | ~~Decide whether a fault that starts while the driver is steering needs any alert while they keep steering~~ **Decided by the lead, DQ-366 A (2026-10-17):** the lighter prompt after 1.5 s while steering; TSR-607 (c); implemented in the follow-up PR with `test_released_after_holding` and `test_short_fault_while_holding` |
| OI-3 | ~~TSR-607 Impl column, SWSR mirror and SFM-ACT-023 status to be updated by their owners~~ **Done:** TSR-607 / SWSR-607 in [jherrodthomas/LionDriver#171](https://github.com/jherrodthomas/LionDriver/pull/171); SFM-ACT-023 in [jherrodthomas/LionDriver#177](https://github.com/jherrodthomas/LionDriver/pull/177) |
| OI-4 | The test file was a pytest-style class, which `tools/test_runner.py` (unittest) does not collect; converted to `unittest.TestCase` before #174 merged (CI 1529 → 1535 passed). The same defect kept `test_supervision.py` and `test_input_freshness.py` (19 tests) out of CI since #51; converted in the follow-up PR (SW FMEA SWF-ACT-055) |
