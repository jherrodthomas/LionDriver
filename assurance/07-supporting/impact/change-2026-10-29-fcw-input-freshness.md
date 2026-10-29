# Change impact: forward collision warning only from fresh and valid inputs (TSR-625)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). `selfdrived` raised the forward collision warning from the last received `modelV2.meta.hardBrakePredicted` and `longitudinalPlan.fcw`, with no validity or age check of its own. A held or invalid message could keep raising FCW in the same cycle in which `commIssue` is raised, and a false FCW can make the driver brake hard with a close follower (SW FMEA SWF-051, HZ-006). This change implements the freshness part of TSR-625 and SWSR-625. It follows the requirement as written (2 nominal periods, validity flags), so it needs no decision.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-29** in this LionDriver PR; unit-tested on the real `SelfdriveD` and mutation-checked in CI; not verified on the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/selfdrive/selfdrived/selfdrived.py`, `supervision.py`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)); QM tool change (`tools/ci/host_mutation.py`) |
| Reference configuration affected | Yes, and every other platform |
| Requirements | TSR-625 and SWSR-625 ([WP-S-02](../../03-system/WP-S-02-technical-safety-requirements.md), [WP-W-02](../../05-software/WP-W-02-software-safety-requirements.md)): freshness gate implemented; still partial, because the FCW trigger-source log and the false-FCW rate target (WP-V-02) are open |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| FCW freshness gate | `openpilot/selfdrive/selfdrived/supervision.py`, `selfdrived.py` | `fcw_inputs_fresh` is true only while `modelV2` and `longitudinalPlan` are both valid, both received at least once, and each received within 2 nominal periods (0.1 s at 20 Hz). Age is counted in `selfdrived` frames (`SubMaster.frame - recv_frame`), so a process replay gives the same answer as the drive. FCW (model or planner) is raised only while the gate is true. Each input normally arrives every 5 frames, so the bound of 10 frames leaves one period of margin | `test_fcw_freshness.py` (8 tests): the gate at the bound (10 frames fresh, 11 stale), each input invalid, never received; and the real `SelfdriveD.update_events` with a hard-brake prediction: FCW with fresh inputs, none with a stale model, a stale plan, or either input invalid. The test module fails to import on the previous code |
| Mutation | `tools/ci/host_mutants.toml` | FC-1 (validity ignored), FC-2 (3 periods), FC-3 (never received counts), FC-4 (planner input not checked), FC-5 (gate not called): each killed. 56 host mutants in all, all killed | `tools/ci/host_mutation.py` |
| Mutation tool | `tools/ci/host_mutation.py`, `test_host_mutation.py` | The tool now deletes a mutated file's cached bytecode after writing the mutant and after restoring the original. A mutant of the same length written within the same second keeps the size and mtime the `.pyc` records, so Python loaded the stale original. FC-2 survived once this way, then was killed on a rerun | New test: a same-length rewrite with the original mtime is seen. With the old write, the stale value is read |

## 2. Impact

- **Safety:** removes a false FCW from a held or invalid model or planner message (SWF-051.C1, WP-A-04 BE-4.11). A true FCW is lost only while an input is stale or invalid, and in that case `commIssue` already soft-disables control; the car's own PCS/AEB is unchanged.
- **Driver:** no change while the inputs are healthy.
- **Process replay:** the gate can drop an FCW only on a segment where a model or planner message is late or invalid at that moment. The CI run of this PR shows whether any reference segment does.
- **Mutation results:** a mutant that survived only through stale bytecode would have looked like a weak test. No mutant recorded before this change survived, so no earlier rating rests on a false result.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | SWSR-625: log every FCW with its trigger source (model or planner), and set the false-FCW rate target (WP-V-02) | SW requirements owner, G3 |
| OI-2 | `host_mutation.py` has no entry in WP-P-07; classify it with `mutation.py` (TL-06) | Tool owner |
