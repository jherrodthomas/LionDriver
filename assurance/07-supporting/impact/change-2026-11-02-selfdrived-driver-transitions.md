# Change impact: host requirements and tests for the driver-caused `selfdrived` transitions (DQ-151 A)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change in a safety-relevant host path (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). The state-machine checker reported four transitions of the `selfdrived` engagement machine with no host software safety requirement (SWSR), finding S7 ([WP-W-05](../../05-software/WP-W-05-software-unit-design.md) §5.3): the driver disengaging (X2), the driver overriding while engaged (E2, O2) and the pre-enable phase (P1). The lead chose to derive host requirements for all four (register DQ-151, option A). This change writes SWSR-302h, 302i, 305h and 305i to the current code, adds a unit test module for them, and changes no production code.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-11-02** in this LionDriver PR; the tests pass here with stubbed `msgq` and `Params` and a local mutation check; CI to confirm; not verified on the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/selfdrive/selfdrived/tests/test_driver_transitions.py`, new test only) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)); no change to `state.py` or any other production file |
| Reference configuration affected | No behaviour change on any platform |
| Decision | DQ-151 A (decider: Claude; reversible). Open for the lead: the pre-enable soft-disable behaviour (§3 OI-1) |
| Requirements | SWSR-302h (TSR-302, TSR-308), SWSR-302i (TSR-302), SWSR-305h and SWSR-305i (TSR-305), all QM (B-sup), [WP-W-02](../../05-software/WP-W-02-software-safety-requirements.md) v0.51 §5; OI-12 narrowed |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Four host SWSRs | WP-W-02 §5, §2.1, §13; `state-machines/sm-selfdrived.yaml`; WP-W-05 §5.3 (generated) | X2 → SWSR-302h, P1 → SWSR-302i, E2 → SWSR-305h, O2 → SWSR-305i. Each is worded to `selfdrive/selfdrived/state.py` as it is (upstream code, unchanged). SWSR-302i states that a SOFT_DISABLE event is not acted on in preEnabled and that the soft disable starts one cycle after the pre-enable phase ends | `check_state_machines.py --check`: no S7 finding left for `selfdrived`; `sync_requirements.py --check`, `check_trace.py` (K5 included) pass |
| Unit tests | `openpilot/selfdrive/selfdrived/tests/test_driver_transitions.py` (18 tests, 4 classes, one per SWSR) | Drives `StateMachine.update` with synthetic event types, as `test_state_machine.py` does, and checks the named driver events (`pcmDisable`, `buttonCancel`, `pedalPressed`, `steerDisengage`, `preEnableStandstill`, `steerOverride`, `gasPressedOverride`) against the real event table | 18 pass under pytest and under `unittest` (the CI runner `tools/op.sh test` collects the folder). Run here with stubs for the compiled `msgq` and `Params`; CI runs them on the built tree |
| Mutation check (local, not committed) | in-memory copies of `state.py` | Eight hand-written mutants: USER_DISABLE ignored; PRE_ENABLE ignored; preEnabled never left; SOFT_DISABLE ends preEnabled; override not entered; override disengages; override never left; end of override disengages. Each fails 2 to 4 of the new tests | Not added to `tools/ci/host_mutants.toml`: its entries cite SW FMEA causes, and `sw-fmea.yaml` has no cause for these transitions yet (OI-3) |

## 2. Impact

- **Safety:** none on the vehicle; no code changed. The tests pin today's behaviour, so a later upstream sync that changes it fails CI and comes back as a requirement change. The envelope requirements (SWSR-301, 302, 305) are unchanged and remain the backstop.
- **Pre-enable soft disable:** SWSR-302i writes down a behaviour that may not be the one wanted: with a soft-disable condition present while the brake is held at standstill, the attempt continues; on brake release the machine is enabled for one cycle, then soft-disables over 3 s with its alert, so lateral control can run for up to 3 s with the condition present. Changing it is a vehicle-behaviour default, left to the lead (OI-1).
- **Traceability:** the steering-override part of SWSR-305h/305i refines TSR-304(b), but a QM (B-sup) row under TSR-304 (B‡) is a K5 finding, so both rows trace to TSR-305 only (OI-2).
- **Generated outputs:** WP-W-05 §5.3 and its chart, the state-machine README, the trace map and figures, the SysML `StateRecords.sysml`, views and allocation report, and the explorer page were regenerated; the explorer was republished at its existing URL.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Lead decision: on a SOFT_DISABLE event in preEnabled, keep today's behaviour, end the attempt (disabled with the soft-disable alert), or go to softDisabling. SWSR-302i, its test and `state.py` follow the answer (WP-W-02 OI-12) | Project lead, G3 |
| OI-2 | Re-derive the host SWSR ASILs (WP-S-02 OI-2) and then give SWSR-305h/305i TSR-304(b) as a parent | Safety engineer, G3 |
| OI-3 | SW FMEA causes for these transitions, then the eight mutants in `host_mutants.toml` | SW FMEA owner |
| OI-4 | Independent review (I1) of the four SWSRs and the test module | Reviewer, G3 |
