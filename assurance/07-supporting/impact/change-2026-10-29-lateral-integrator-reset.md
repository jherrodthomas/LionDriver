# Change impact: the steering controller starts each engagement with no integrator (DQ-426)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). `controlsd` calls `LaC.reset()` on every step where lateral control is off, but `LatControlTorque` (the reference Corolla TSS2) and `LatControlPID` did not override `reset()`, and the base class clears only the saturation timer. The PID integrator from the last engagement was therefore added again at the next one, possibly minutes later on a different road (SW FMEA SWF-042.C1, O 7 D 10, AP H). `LatControlCurvature` already resets its PID. Upstream master (`e376168`, 2026-10-27) still has no reset in either controller and gives no reason. Recorded as a reversible technical choice, DQ-426 (decider: Claude, option A).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-29** in this LionDriver PR; unit-tested and mutation-checked in CI; not verified in the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/selfdrive/controls/lib/latcontrol_torque.py`, `latcontrol_pid.py`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Yes: the Corolla TSS2 uses `LatControlTorque` |
| Decision | DQ-426 A (decider: Claude; reversible; the lead may object until 2026-11-01) |
| Requirements | None yet. A requirement for controller state across disengagement belongs to SWF-ACT-043 (requirements-based tests for controlsd, gating table per FSR-006) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| PID reset in both controllers | `openpilot/selfdrive/controls/lib/latcontrol_torque.py`, `latcontrol_pid.py` | `reset()` calls the base reset and `self.pid.reset()`, which zeroes p, i, d, f and the output. `controlsd` already calls it whenever `CC.latActive` is false (not engaged, steering fault, standstill without `steerAtStandstill`, stale lateral inputs, non-finite curvature), so the first engaged step starts with i = 0 | `test_latcontrol.py` `TestLatControlReset` (Civic PID, Corolla TSS2 torque, ID.4 curvature): the integrator builds up while active and is 0 after `reset()`. `test_controlsd_call_sites.py` `TestLateralResetCallSite`: through the real `Controls.state_control`, the reference controller's integrator is 0 one step after `selfdriveState.active` drops. Two of the three unit cases and the call-site test fail on the previous code. Mutants LR-1 (torque reset), LR-2 (PID reset), LR-3 (the `controlsd` call) are each killed (`tools/ci/host_mutation.py`) |

## 2. Impact

- **Safety:** removes a torque step at engagement from a stale correction (HZ-002 abrupt pull, HZ-003 lane departure, SWF-042 end effects). The integrator is bounded by the lateral-acceleration limits, and the CarController and panda limits (1500 units, 15 up / 25 down per frame) still apply, so the old behaviour stayed inside the envelope; the change reduces what reaches it.
- **Driving:** a steady bias (road crown, a small calibration offset) is re-learned over the first seconds of each engagement, at KI 0.15 in lateral-acceleration space, instead of starting from the last value. The feed-forward term, which carries most of the command, is unchanged.
- **Process replay:** `controlsd` output differs from comma's reference logs on two of 66 segments, neither of them Toyota (§3). Each is listed in `EXPLAINED_DIFFS` (`test_processes.py`) for that field, process and segment only.
- **Upstream:** a fork difference to carry at each openpilot sync (WP-M-11). If upstream adds its own reset, this one is dropped.

## 3. Process replay

CI process replay on `db9eb79` (#530): 4 of 66 segments changed. Two are the existing explained diffs (Tesla `card`, CA-001; Toyota `dmonitoringd`, TSR-634). Two are this change, both in `controlsd`:

| Segment | Controller | Fields | What it shows |
|---|---|---|---|
| Hyundai `regenAFB9780D823\|2025-04-08--23-00-34--0` | torque | `controlsState.lateralControlState.torqueState.i` (1474 frames) | While assist is off the logged integrator is 0 instead of the last value, -0.010. The torque command does not differ: the segment does not re-engage lateral control with that integrator |
| Honda `regenB328FF8BA0A\|2025-04-08--22-57-45--0` | PID | `pidState.i` (357), `pidState.output` (331), `carControl.actuators.torque` (331) | The cause in action. At re-engagement (frame 5644) the old integrator, -0.066, is no longer added: the command is -0.30 instead of -0.36 and converges over about 3.3 s (331 frames at 100 Hz) as the integrator builds up again |

The Toyota reference segment (`regen218A4DCFAA1`) shows no `controlsd` diff. `test_explained_diffs.py` checks that the Honda entry excludes only its three fields and that `latActive` is still compared.

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Requirement for controller state across disengagement, with the rest of the gating table (SWF-ACT-043) | SW FMEA owner |
| OI-2 | Vehicle check: no pull at engagement after a long engaged drive on a crowned road (WP-S-09) | G3 |
