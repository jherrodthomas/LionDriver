# Change impact: a setting changed while engaged is held until disengagement (DQ-403)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements the project lead's decision on DQ-403, option A. On the reference platform, a change made in the settings menu while engaged is stored but used only after the driver disengages, and the next engagement is still refused while the stored setting is outside the assured configuration (DQ-221). It closes OI-3 of [change-2026-10-19-reference-entry-checks](change-2026-10-19-reference-entry-checks.md).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-20** in this LionDriver PR; unit-tested; not verified in the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Reference configuration affected | Yes, the reference platform only (`assured_config.ASSURED_PLATFORMS`, the Corolla TSS2). On other platforms a setting takes effect at once, as before |
| Decision | DQ-403 A (lead, 2026-10-19). DQ-402 A, decided the same day, needs no code: it keeps the behaviour of #287 and is recorded in the entry-checks record |
| Requirements | Parent TSR to be written by the safety-concept session, with the TSRs of DQ-221 (entry-checks record OI-1); SW FMEA SWF-067.C2 and action SWF-ACT-079 by the SW FMEA owner |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Hold settings while engaged | `selfdrive/selfdrived/selfdrived.py` (`apply_settings`, called in `step` after the state machine) | The params thread now stores `ExperimentalMode` and `LongitudinalPersonality` as the stored settings. Each control step applies them to `selfdriveState.experimentalMode` and `.personality`, which the longitudinal planner and `controlsd` read, unless the item is engaged on the reference platform. Then it keeps the values it engaged with. When the driver disengages, the stored settings apply at once. The entry check of DQ-221 still refuses the next engagement while a stored setting is outside the assured configuration | 5 unit tests in `selfdrive/selfdrived/tests/test_assured_config.py` (`TestSettingsHeldWhileEngaged`): held while engaged, applied after disengagement, next engagement refused, applied at once while disengaged, other platforms unchanged. 4 of them fail on the previous code; the fifth (next engagement refused) guards the entry check |
| Distance button, other platforms | same | The stored following distance follows a distance-button press, so the next step does not undo it before the params thread re-reads the setting | Existing distance-button tests |

## 2. Limits of this change

- It covers the two settings the planner reads through `selfdriveState`: Experimental Mode and the following distance.
- The other settings of `ASSURED_PARAMS` work differently:
  - `AlphaLongitudinalEnabled` is read once when `card` starts, so it already takes effect only at the next start.
  - The three debug modes (`JoystickDebugMode`, `LongitudinalManeuverMode`, `LateralManeuverMode`) are read by the process manager (`system/manager/process_config.py`), which starts and stops processes when they change. Holding them is not part of this change (OI-2).
- The settings screen shows the new choice at once, but the item drives with the old one until disengagement. The driver gets no cue that a change is waiting (OI-1).

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | User information (WP-O-03) and, if wanted, a cue on the settings screen that a change applies after disengagement | WP-O-03 owner |
| OI-2 | Debug-mode settings changed while engaged: the process manager acts on them at once. Confirm they cannot be changed from the menu while onroad, or hold them too | SW lead |
| OI-3 | Parent TSR, and SWF-067.C2 / SWF-ACT-079 status in the SW FMEA | Their owners |
| OI-4 | Vehicle check: change Experimental Mode and the following distance while engaged on the reference car; no change in behaviour until disengagement | Vehicle test |
