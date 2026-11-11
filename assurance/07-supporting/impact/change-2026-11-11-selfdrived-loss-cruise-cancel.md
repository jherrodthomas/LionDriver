# Change impact: controlsd cancels cruise when selfdrived stops (DQ-439 A)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change in a safety-relevant host path (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). `controlsd` took "engaged" (`carControl.enabled`) from `selfdrived`'s last `selfdriveState` message. When `selfdrived` stops while engaged, steering and openpilot's acceleration stop after 0.1 s (the TSR-602 freshness gate), the panda revokes authority 0.3 s after the first "not engaged" heartbeat (TSR-307(a)) and sounds its siren 0.5 s after it while PCM cruise is still on (TSR-516(c)), and the screen shows "System Unresponsive" after 5 s. But `carControl.enabled` stayed true, so the cruise cancel that every other disengagement sends was never sent, and the car's cruise stayed on until the driver cancelled it (SW FMEA SWF-040.C1, SWF-048.C1). The lead decided that cruise is cancelled when `selfdrived`'s messages stop, as for any other disengagement (register DQ-439, option A, 2026-11-11).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-11-11** in this LionDriver change; unit tests and mutant CA-1 pass here; CI to confirm; not verified on the vehicle; not reviewed independently |
| Change requests | This LionDriver change |
| Class | SR-Q (`openpilot/selfdrive/controls/controlsd.py`, `openpilot/selfdrive/controls/tests/test_controlsd_call_sites.py`) and SR-T (`tools/ci/host_mutants.toml`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Every platform: the change is in car-independent `controlsd` code. Behaviour changes only while `selfdriveState` is not alive |
| Decision | DQ-439 A, the lead's (vehicle-behaviour default) |
| Requirements | SWSR-303i (TSR-303), QM (B-sup), [WP-W-02](../../05-software/WP-W-02-software-safety-requirements.md) v0.55 §5; OI-18 extended to this case |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| `carControl.enabled` | `openpilot/selfdrive/controls/controlsd.py` (`state_control`, 1 line and comment) | `CC.enabled = bool(selfdriveState.enabled and sm.alive['selfdriveState'])`. The alive criterion is the one the TSR-602 gate already uses for `latActive` and `longActive` (10 nominal periods, 0.1 s). While `selfdriveState` is alive nothing changes. At start-up, before the first `selfdriveState`, `enabled` was already false (the default message) and stays false. The existing line `cancel = CS.cruiseState.enabled and (not CC.enabled or not CP.pcmCruise)` then requests the cancel | `test_controlsd_call_sites.py` `TestSelfdrivedLossCancelsCruise`, 6 tests through the real `Controls.state_control` and `publish` with the reference CarParams: no cancel while alive; `enabled` false and `cruiseControl.cancel` true from the first frame not alive and in each of the next 50; no cancel once alive again with `enabled` true; an ordinary disengagement still cancels; not alive and not enabled does not raise. Through the real Toyota `CarInterface.apply`: CANCEL_REQ = 0 in every `0x343` frame before the stop and 1 in every frame from the first one after it (reference car with openpilot longitudinal: the cancel is the CANCEL_REQ bit of ACC_CONTROL, `carcontroller.py:268`). All 25 tests in the file pass |
| Mutant | `tools/ci/host_mutants.toml` CA-1 (SW FMEA SWF-040.C1, SWF-048.C1) | CA-1 removes the alive condition (the upstream behaviour) | Killed by `test_controlsd_call_sites.py` (`host_mutation.py --only CA-1`): 3 tests fail on it |
| Records | WP-W-02 v0.55 (SWSR-303i, §13, OI-18), `trace/items/swsr.yaml` (generated), SW FMEA rev 1.23 (SWF-036 safety mechanism, SWF-040.C1 text, SWF-048.C1 D 9 → 8) and its generated review outputs | | `sync_requirements.py --check`, `check_trace.py`, `fmea_lint.py --report` (0 errors) |

## 2. Impact

- **Safety:** positive. When `selfdrived` stops while engaged, the car's cruise now drops with its own cancel, as for any other disengagement, 0.1 s after the last `selfdriveState`, instead of staying on until the driver cancels it (HZ-012, the driver misinformed about the automation state). The panda's siren (TSR-516(c)) is left for a cancel that fails to drop PCM cruise within 0.5 s of the first "not engaged" heartbeat. Whether the cancel is that fast on the reference car is not measured (WP-W-02 OI-18).
- **Other `carControl` fields that follow `enabled`:** while `selfdriveState` is not alive, `cruiseControl.override` and `cruiseControl.resume` are false, `hudControl.speedVisible` and `lanesVisible` are false, and the Toyota LKAS HUD (`0x412`) shows the not-engaged state (`BARRIERS` 0), with the UI chime the Toyota CarController plays on a forced cancel in place of the PCM's fault sound (`carcontroller.py:300-302`). These are the values of any other disengagement, and `latActive` and `longActive` were already false, so the HUD now matches what the item does. `card` initialises its set speed on a rising edge of `enabled` only for cars without PCM cruise (`cruise.py:126-129`); on the reference car nothing changes there.
- **Short stalls:** a gap of more than 0.1 s in `selfdriveState` now cancels PCM cruise. If `selfdrived` comes back still enabled, `controlsd` stops requesting the cancel, but the PCM has dropped cruise, so `selfdrived` disengages on the PCM cruise state (`pcmDisable`) and the driver engages again. Before, the same gap already ended steering and acceleration after 0.1 s and, past 0.3 s, panda authority. The register's option A states this cost.
- **Upstream difference:** `controlsd.py` now differs from upstream openpilot in this line; it is carried at each sync (WP-P-08), and the tests and mutant fail if a sync drops it.
- **Process replay:** no difference expected, by reasoning, not run here (the reference logs are fetched from comma's CI storage). `CC.enabled` differs only while `selfdriveState` is not alive. Process replay runs `controlsd` with `SIMULATION=1`, where `SubMaster.alive` is true for any service once seen (`cereal/messaging/__init__.py:265`), and `controlsd` steps on `selfdriveState` (its poll service), so in a replay `selfdriveState` is seen and alive in every frame; before the first one, `enabled` is false either way. The same reasoning is why the existing TSR-602 gate on `selfdriveState` never shows in replay. CI confirms.
- **Simulation:** the plant study [engaged-mismatch.md](../../sim/results/engaged-mismatch.md) models the case before this change ("No cancel reaches the PCM"): its siren row is the behaviour without the cancel, and is what remains if the cancel has no effect. It is not changed here (OI-3).
- **Generated outputs:** the SW FMEA figures, cards, review page and workbook were regenerated.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Vehicle check: stop `selfdrived` while engaged with PCM cruise on (WP-S-09), confirm that cruise drops, the time from the last `selfdriveState` to PCM_CRUISE CRUISE_ACTIVE 0, and that the panda siren stays silent (with WP-W-02 OI-18 and SW FMEA SWF-ACT-049) | Vehicle tests |
| OI-2 | Independent review (I1) of the change, SWSR-303i and the tests | Reviewer, G3 |
| OI-3 | Update the plant model's `selfdrived_stop` case so that the host cancels PCM cruise at `host_stale_s` (`assurance/sim/plant/simulate.py`), regenerate `engaged-mismatch.md` and the records that quote it (WP-S-02 TSR-307 and TSR-516 status, WP-S-04, WP-A-04 MCS-02.9, fmdtools SG-02), keeping the no-cancel run as the case of a cancel without effect | Simulation owner |
