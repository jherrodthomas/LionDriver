# Change impact: wheel-touch reminders also bounded by distance (TSR-634)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements TSR-634 as decided by the project lead on 2026-10-14 (register DQ-077, option A), with the rule and speed table of [WP-C-08 §5.4](../../02-concept/WP-C-08-driver-hmi-misuse-analysis.md).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-17** in this LionDriver PR; unit-tested; not verified in the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Reference configuration affected | Yes; the change applies to every build that runs `dmonitoringd` |
| Decision | DQ-077 A: in the wheel-touch fallback the reminders come faster at highway speed |
| Requirements | TSR-634 (WP-S-02 v0.34 status); new SWSR-634 (WP-W-02 v0.32) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Requirements | Verification |
|---|---|---|---|---|
| openpilot driver monitoring | `selfdrive/monitoring/policy.py` | In the wheel-touch policy, alert *k* fires at T*k* = 5 / 15 / 25 s or D*k* = 150 / 240 / 395 m driven while engaged since the last driver interaction, whichever comes first. Before, only the time applied, at every speed. Wheel-touch awareness is now the lower of the old time track and a distance track. An interaction that resets awareness resets both. When awareness recovers (low-speed exemption, or a driver the vision policy sees as attentive), both tracks recover with it. Below the alert speed (10 km/h) the distance raises no alert. The vision policy, the no-response stage (5 s after alert 3) and the lockout are unchanged | TSR-634, SWSR-634 | 6 new unit tests; 5 fail on the previous logic (the sixth, no alert at low speed, guards against a regression) |
| same | `selfdrive/monitoring/test_monitoring.py` | Constant speeds 0, 30…120 km/h and 50, 57 km/h; ±1.5 m/s² ramps between 40 and 100 km/h; reset on interaction; restart after vision recovery; no distance while disengaged; no alert at low speed | — | — |
| same | `selfdrive/test/process_replay/test_processes.py`, `test_explained_diffs.py` | Explained-diff entry for the one changed process-replay segment (§3) | — | New test: the field is excluded, the alert level still compared |
| this PR | WP-W-02, WP-S-02, WP-C-08, WP-V-02, WP-A-05, `stpa-map.yaml`, register, generated trace and FMEA files | SWSR-634; status texts; `policy.py:N` line references in the living documents moved with the code (dated records unchanged) | — | — |

## 2. Timing

Measured with the unit-test harness at 20 Hz (`DT_DMON` = 0.05 s), fallback active from the first step:

| Speed (km/h) | Alert 1 / 2 / 3 (s) | Distance at alert 1 / 2 / 3 (m) | WP-C-08 §5.4 table (s) |
|---|---|---|---|
| 50 | 5.00 / 15.00 / 25.00 | 69 / 208 / 347 | 5.0 / 15.0 / 25.0 |
| 60 | 5.00 / 14.40 / 23.75 | 83 / 240 / 396 | 5.0 / 14.4 / 23.7 |
| 80 | 5.00 / 10.80 / 17.80 | 111 / 240 / 396 | 5.0 / 10.8 / 17.8 |
| 100 | 5.00 / 8.65 / 14.25 | 139 / 240 / 396 | 5.0 / 8.6 / 14.2 |
| 110 | 4.95 / 7.90 / 12.95 | 151 / 241 / 396 | 4.9 / 7.9 / 12.9 |
| 120 | 4.50 / 7.25 / 11.85 | 150 / 242 / 395 | 4.5 / 7.2 / 11.8 (§5.4 text) |

Each alert is within one DM step of the table. The bound can be exceeded by at most one step of travel, 1.7 m at 120 km/h. The no-response stage and the lockout follow alert 3 as before.

## 3. Behaviour to watch

| Change | Normal-driving risk | How it is bounded |
|---|---|---|
| Faster alerts 2 and 3 above about 57 km/h in the fallback | More reminders for drivers the camera cannot read (sunglasses, low light) at highway speed; nuisance could lead drivers to defeat the system (FM-05, DMP-04) | The criterion is WP-V-02 §4.4 (c), at most 1 alert 2 or 3 per hour with an attentive driver; if it fails, the D*k* anchor is revisited (WP-C-08 OI-8) |
| Distance kept across a switch to the vision policy | A driver who leaves the fallback and comes back gets the distance already driven, unless the vision policy saw them attentive long enough to restore awareness | The same as the time track upstream (`last_wheeltouch_awareness`); covered by `test_wheeltouch_distance_recovers_with_vision` |
| `dmonitoringd` output changes | Process replay compares `driverMonitoringState` with the upstream reference logs; segments with the fallback active at speed for more than about 5 s without driver input differ | CI process replay on `7589a83`: one of 66 segments differs, Toyota `regen218A4DCFAA1|2025-04-08--22-57-51--0`, only in `wheeltouchPolicyState.awarenessPercent` (40 frames; it falls about 0.6 instead of 0.2 points per frame, the distance track at about 27 m/s). No alert level differs. Explained in `EXPLAINED_DIFFS` (`test_processes.py`) for that field, process and segment only; `test_explained_diffs.py` checks that the alert level is still compared |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Vehicle validation per WP-V-02 §4.4: (a) T-SIL replay entry in WP-S-09, (b) driver response, (c) nuisance, (d) exposure | G3 |
| OI-2 | SW FMEA SWF-061 and System FMEA SFM-023 describe the fixed wheel-touch timers; their owners to add the distance track as a failure-mode cause (wrong distance integration, missing reset) | SW FMEA owner |
| OI-3 | `carState.vEgo` is now an input to the alert timing; an implausible speed (stuck at zero) leaves the time caps only, which is the behaviour before this change | WP-W-02 owner |
