# Change impact: a soft-disable fault in the pre-enable phase ends the engagement attempt (DQ-433 A)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change in a safety-relevant host path (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). When the driver engages while holding the brake at standstill, `selfdrived` waits in `preEnabled` until the brake is released. Upstream openpilot ignores a SOFT_DISABLE event in that state: on brake release the machine is enabled for one cycle and then soft-disables over 3 s, so lateral control can run for up to 3 s with the fault present ([change-2026-11-02-selfdrived-driver-transitions](change-2026-11-02-selfdrived-driver-transitions.md) OI-1). The lead decided that the attempt ends at once (register DQ-433, option A, 2026-11-03).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-11-03** in this LionDriver PR; unit tests and two mutants pass here with stubbed `msgq` and `Params`; CI to confirm; not verified on the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/selfdrive/selfdrived/state.py`, `openpilot/selfdrive/selfdrived/tests/test_driver_transitions.py`) and SR-T (`tools/ci/host_mutants.toml`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Every platform: the state machine is car-independent. Behaviour changes only when a SOFT_DISABLE event is raised while `preEnabled` |
| Decision | DQ-433 A, the lead's (vehicle-behaviour default) |
| Requirements | SWSR-302i (TSR-302), QM (B-sup), [WP-W-02](../../05-software/WP-W-02-software-safety-requirements.md) v0.52 §5; WP-W-02 OI-12 item (1) closed |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| State machine | `openpilot/selfdrive/selfdrived/state.py` (preEnabled branch, 5 lines) | In `preEnabled`, a SOFT_DISABLE event with no IMMEDIATE_DISABLE or USER_DISABLE event takes the machine to `disabled` in that cycle with the SOFT_DISABLE alert, whether or not PRE_ENABLE is still raised (new transition P2). IMMEDIATE_DISABLE and USER_DISABLE keep their priority (X1, X2). All other transitions unchanged | `test_driver_transitions.py` `TestPreEnable`: 3 new tests replace the 2 that pinned the old behaviour; 19 pass, and all 118 tests in `selfdrive/selfdrived/tests` pass |
| Mutants | `tools/ci/host_mutants.toml` MP-1, MP-2 (SW FMEA SWF-033.C1) | MP-1 ignores the fault (the old behaviour); MP-2 engages instead | Both killed by `test_driver_transitions.py` (`host_mutation.py --only`) |
| Records | `state-machines/sm-selfdrived.yaml` (P2 added, P1 guard narrowed, line references), WP-W-05 §5.3 (generated), WP-W-02 v0.52 SWSR-302i and OI-12 | | `check_state_machines.py --check`, `sync_requirements.py --check`, `check_trace.py` |

## 2. Impact

- **Safety:** positive. Steering and speed control can no longer start with a soft-disable condition present at engagement. A driver who engages at standstill with such a condition gets the soft-disable alert and no engagement; engaging again needs a new request once the condition has cleared.
- **Driver experience:** an engagement attempt at standstill can now end without the car ever moving under control, where before it ran for up to 3 s. The alert shown is the condition's own soft-disable alert.
- **Upstream difference:** `state.py` now differs from upstream openpilot; the change is carried at each sync (WP-P-08) and the tests and mutants fail if a sync drops it.
- **Process replay:** none of the replay segments raises a SOFT_DISABLE event while preEnabled, so no replay difference is expected; CI confirms.
- **Generated outputs:** WP-W-05 §5.3 and its chart, the state-machine README, the trace items and the SysML `StateRecords.sysml`, views and explorer were regenerated.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Vehicle check: engage at standstill with a soft-disable condition present (for example calibration invalid), confirm no actuation and the alert | Vehicle tests |
| OI-2 | Independent review (I1) of the change, SWSR-302i and the tests | Reviewer, G3 |
