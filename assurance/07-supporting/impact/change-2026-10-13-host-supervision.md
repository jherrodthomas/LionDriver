# Change impact: host supervision of the panda's reports and of controlsd inputs

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver change to safety-relevant host software (SR-Q paths `openpilot/selfdrive/selfdrived/**`, `openpilot/selfdrive/controls/**`, `openpilot/cereal/**`).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Integrated 2026-10-13 (LionDriver #51, `824a0b0`): unit-tested, process replay run in CI; not verified on the vehicle or the HIL bench; not reviewed independently** |
| Change request | Pull request from branch `claude/host-supervision` to `liondriver-dev` |
| Origin | SW FMEA rev 0.6 host rows (SWF-032, SWF-034, SWF-039, SWF-040, SWF-043, SWF-045) and System FMEA actions SFM-ACT-010 / SFM-ACT-011 |
| Reference configuration affected | Yes: the item disengages, with an alert, in fault cases where it previously continued or reacted later |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Area | Before (BL-004) | After | Requirement | FMEA |
|---|---|---|---|---|
| `controlsMismatch` (panda reports `controlsAllowed` false while engaged) | After 200 cumulative mismatched samples, about 2 s, counted over the whole engagement | After 2 **consecutive** `pandaStates` samples, and at most 0.5 s after the first mismatched frame (`selfdrived/supervision.py`) | TSR-621, SWSR-621 | SWF-034, SFM-016.C2, SFM-ACT-010 |
| Panda health flags | Only `relayMalfunction` and `safetyRxChecksInvalid` reacted | `txRateExceeded` → `pandaTxRateExceeded`, `heartbeatLost` → `pandaHeartbeatLost` (immediate disable, no entry); a rise of `safetyTxBlocked` while engaged → `pandaTxBlocked` (immediate disable) | TSR-615, SWSR-615 | SWF-032.C1 |
| `cruiseMismatch` (stock cruise engaged while the item is not) | After 6 s, no reaction (alert commented out) | After 1 s, "Stock Cruise Still Engaged / Press Cancel or Brake" with a repeating prompt; `controlsd` keeps requesting the cancel as before | TSR-308, SWSR-308h | SWF-039, SFM-021, SFM-ACT-011 |
| `controlsd` input freshness | `selfdriveState`, `carState`, `modelV2`, `longitudinalPlan` used with no age check | `latActive` needs fresh `selfdriveState`, `carState`, `modelV2`; `longActive` needs fresh `selfdriveState`, `carState`, `longitudinalPlan` (`controls/lib/input_freshness.py`) | TSR-602, SWSR-602 | SWF-040, SWF-043 |
| Non-finite values in `controlsd` | One NaN desired curvature or roll latched `desired_curvature` and the torque controller for the drive; NaN `lateralDelay` crashed `controlsd` | A non-finite desired curvature, roll or `aTarget` turns lateral or longitudinal control off for that step only; `desired_curvature` is reset if it ever becomes non-finite; a non-finite `lateralDelay` falls back to `CarParams.steerActuatorDelay` | TSR-604 (partly) | SWF-045 |

Freshness is judged on two clocks. `selfdriveState` drives the `controlsd` loop, so it is checked on the wall clock (`SubMaster.alive`, 10 periods = 0.1 s). The other inputs are compared with `selfdriveState` on the log clock (`logMonoTime`, 10 periods: `carState` 0.1 s, `modelV2` and `longitudinalPlan` 0.5 s). A process replay therefore gives the same result as the drive, however fast it runs. An input that has not been received yet is left to `selfdrived`'s engagement checks.

## 2. Behaviour to watch (possible nuisance disengagements)

| Change | Normal-driving risk | How it is bounded |
|---|---|---|
| `controlsMismatch` at 2 samples | A `pandaStates` sample taken just before the panda saw the PCM cruise edge at engagement | One stale sample is absorbed; the next sample (100 ms later) resets the count |
| `pandaTxBlocked` | The panda blocks a frame that `card` sends within the CarController limits (rounding, timing) | CarController and panda limits are designed to agree; replay of reference logs to confirm (OI-3) |
| `cruiseMismatch` at 1 s | PCM cruise drops later than 1 s after a host disengagement | Only an alert, no change to control; vehicle check (SWF-ACT-049) |
| Freshness gate | A modeld frame-drop burst longer than 0.5 s | Same bound as `selfdrived`'s existing `commIssue` / `modeldLagging` soft disable, so no new disengagement case; it only stops actuating on the stale value |

## 3. Verification

| Check | Result |
|---|---|
| `selfdrive/selfdrived/tests/test_supervision.py` (10 tests: consecutive samples, single-sample absorption, 0.5 s bound with stale samples, `safetyTxBlocked` baseline and panda reset) | Pass (local) |
| `selfdrive/controls/tests/test_input_freshness.py` (6 tests: bounds per service, wall clock for `selfdriveState`, unseen inputs) | Pass (local) |
| ruff on the changed files | Clean |
| CI: unit tests, static analysis (ruff, ty, codespell), process replay | On the pull request |
| HIL fault injection (stop `selfdrived` / `modeld` / `plannerd` while engaged), vehicle check of the alerts | Not run (SWF-ACT-048, SWF-ACT-049, D-04) |

## 4. Open items

| ID | Item |
|---|---|
| OI-1 | TSR-602 asks for 2 nominal periods; this change uses 10, the same bound as `commIssue`, until reference logs show the input jitter. The stale-input event is `commIssue` (SOFT_DISABLE), not a new immediate disable (SWF-ACT-040). **Accepted for now** by the lead 2026-10-14 (register DQ-115 A): 10 periods stay until the logs show the jitter, then the bound is tightened |
| OI-2 | TSR-615: panda fault flags other than `relayMalfunction` and SPI error bursts still have no reaction; the EPS-fault flag is covered by the EPS status events from `card` |
| OI-3 | Replay the reference-vehicle logs for `safetyTxBlocked` increments and `controlsAllowed` mismatches while engaged to confirm no nuisance disengagements |
| OI-4 | Non-finite values skip a step without an event or alert (SWF-ACT-041 asks for an immediate disable with alert) |
