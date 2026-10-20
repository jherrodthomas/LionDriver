# Change impact: driver-monitoring countdown in elapsed time, and an uncertain DM output no longer stops it (SWSR-635a, 635b)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements SWSR-635a and SWSR-635b ([WP-W-02](../../05-software/WP-W-02-software-safety-requirements.md) v0.38), refined from TSR-635: the first driver-monitoring alert within 6 s end to end (FSR-08.01, SG-08).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-20** in this LionDriver PR; unit-tested; not verified on the device or in the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Reference configuration affected | Yes, all platforms: the DM policy is shared |
| Decision | The lead asked for the fix in chat on 2026-10-20 ("go ahead and fix SWSR-635a and 635b"), which accepts that time with an uncertain DM output now counts toward an alert (WP-W-02 OI-17) |
| Requirements | TSR-635; SWSR-635, 635a, 635b. TSR-608 / SWSR-608 escalation affected (§2) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Countdown in elapsed time (SWSR-635a) | `selfdrive/monitoring/policy.py` (`_frame_dt`, `run_step`, `_update_events`) | The awareness step, the distraction filter and the wheel-touch distance follow the time since the previous evaluated cabin frame, from the frame index (0.05 s per index), capped at 2 s (the SWSR-609 window). Before, each evaluated frame counted 0.05 s, so a DM model that skipped frames lengthened every timer: alert 1 at 10.6 s at 10 Hz and 21.2 s at 5 Hz instead of 5.3 s | `TestFirstAlertTime.test_alert_1_in_real_time_at_any_dm_rate`, `test_frame_gap_capped` |
| Uncertain pose counts as not attentive (SWSR-635b) | `policy.py` (`_update_events`) | A detected face whose pose output is uncertain now runs the countdown at once, as a lost face does. Before, it neither counted down nor recovered until the model had been uncertain for 10 s and the policy fell back to wheel-touch: alert 1 after 15.0 s | `test_uncertain_pose_alert_1_without_fallback_delay`, `test_attentive_certain_driver_still_recovers`; `test_somehow_indecisive_model` updated to the new expectation (vision timers 5 / 8 / 13 s) |
| Escalation past orange (SWSR-635b) | `policy.py` (`_set_policy`) | Past orange the policy still stays vision ("no exploit after orange alert"), but the vision countdown now keeps running when the face is lost or the pose turns uncertain. Before, its step was set to 0, so the alert stayed orange for good and the terminal alert and the no-response reaction never came | `test_escalation_does_not_stop_at_orange` |

## 2. Effect on the driver

- **Earlier alerts with an uncertain DM output.** A driver whose pose the model cannot estimate with confidence now gets alert 1 after 5.05 s, the vision time, instead of after 15.0 s. This also applies when the driver is in fact attentive, for example with glare or an unusual seating position. That is the trade-off the lead accepted; how often it happens is to be measured in reference logs (WP-W-02 OI-17).
- **Escalation no longer stops at orange.** A driver who has reached orange and then turns away (face lost) or whose pose becomes uncertain now reaches the terminal alert at 13 s and the no-response reaction after it (TSR-611, TSR-633), as a visibly distracted driver does. Before, the alert stayed orange without escalating. This changes the TSR-608 escalation in a case where it had stopped; it is in the direction of the SG-08 goal.
- **No change** for a driver the model sees clearly: alert 1 still 5.30 s after the first distracted output at 20 Hz. No change to the wheel-touch policy timers or distances, the lockout or the low-speed and always-on exemptions.

## 3. Verification results

| Check | Result |
|---|---|
| Unit tests (local) | `selfdrive/monitoring/test_monitoring.py`: 24 pass. Without the change, 6 fail: the five new tests and the updated `test_somehow_indecisive_model` |
| Probe of the policy code (local) | Distracted, certain pose: alert 1 at 5.30 s (unchanged). Distracted, uncertain pose: 5.05 s (15.0 s before). Face lost: 5.0 s (unchanged). Orange at 9 s, then face lost or pose uncertain: terminal alert at 13.3 s (none before) |
| Process replay | In CI. Segments in which the DM model skipped frames or its pose output was uncertain are expected to show `driverMonitoringState` differences (awareness, alert level); to be explained from the CI report |
| Device and vehicle | **Not run.** End-to-end measurement and VT-08 remain under SWSR-635 and WP-S-04 OI-11 |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Measure in reference logs how often the pose output is uncertain while the driver is attentive (WP-W-02 OI-17); if the resulting alerts are frequent, put the trade-off to the lead | Release |
| OI-2 | Explain the process-replay differences of this change from the CI report | This PR |
| OI-3 | SW FMEA: the causes "DM output uncertain, countdown stopped" and "escalation stops at orange" now have a control (SW FMEA owner) | SW FMEA revision |
| OI-4 | The no-response timeout and the lockout timer still count evaluated frames, not elapsed time (outside TSR-635; WP-W-02 OI-17) | G2 |
