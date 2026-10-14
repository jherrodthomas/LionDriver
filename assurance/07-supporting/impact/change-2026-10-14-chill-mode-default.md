# Change impact: Chill mode by default (B-06, D-08)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host code (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-14 (LionDriver #74, `9552997`; commit `38d3320`); process replay and the manager default test run in CI; not reviewed independently** |
| Decision | D-08 (decided 2026-10-10, [WP-M-07 §5](../../01-management/WP-M-07-risk-management.md#5-decision-log-strategic-decisions-from-wp-m-01-8)); code change chosen by the project lead in the decision register, [DQ-001](../../01-management/decisions/register.yaml) option A (2026-10-14) |
| Finding | B-06 ([WP-M-03](../../01-management/WP-M-03-project-plan.md)); R-17 ([WP-M-07](../../01-management/WP-M-07-risk-management.md)); STPA LS-31 and LS-03 ([WP-A-05](../../08-analyses/WP-A-05-stpa.md)) |
| Reference configuration affected | Yes (all builds) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| LionDriver | `openpilot/common/params_keys.h` (SR-Q) | The default of `ExperimentalMode` goes from `"1"` back to `"0"`, partly reverting upstream `f21bfc3`. A new install or factory reset starts in Chill mode. The owner can still turn Experimental mode on in Settings; the confirmation dialog that `f21bfc3` removed stays removed | No (the safety envelope does not depend on the mode) | Yes (end-to-end longitudinal control is outside the assessed configuration until WP-C-07 validates it) | Yes (fewer drives with the model in longitudinal control by default) | No | R-17; LS-31; LS-03 (partly: drivers who expect Experimental behaviour) | WP-M-03 (B-06), WP-M-07 (R-17, D-08), WP-A-05 (LS-31) | Process replay; `system/manager/test/test_manager.py::test_set_params_with_default_value` | This change |

## 2. Behaviour changes to watch

| Change | Effect | Check |
|---|---|---|
| New install or factory reset | `manager` writes the default, so `ExperimentalMode` is false and the car runs in Chill mode | First boot of a freshly flashed device |
| Device that already stored a value | Unchanged: `ExperimentalMode` is `PERSISTENT`, so an existing `1` stays `1`. Reference vehicles must still be set up per the release instructions | Release checklist: `ExperimentalMode` is false before the first drive |
| Car without openpilot longitudinal control | `selfdrived` removes the key (`selfdrived.py:118`), which now reads back as false instead of true. No behaviour change, because `selfdrived` and `card` also require `openpilotLongitudinalControl` | None |

## 3. Verification results

| Check | Result |
|---|---|
| Process replay (CI) | To run on the PR; the replay sets its own params, so no change is expected |
| `test_set_params_with_default_value` | To run in CI (checks every default is written on first start) |
| HIL / vehicle | **Not run** |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Release checklist step that `ExperimentalMode` is false on reference vehicles that were set up before this change | G1 |
| OI-2 | LS-03 user information (CC-7): tell drivers the reference configuration runs Chill mode | G1 |
