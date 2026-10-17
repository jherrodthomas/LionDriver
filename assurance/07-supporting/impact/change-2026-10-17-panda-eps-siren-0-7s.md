# Change impact: panda pin to `bf8102a`, EPS-fault siren persistence 0.7 s instead of 1 s (DQ-048)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-17** in this LionDriver PR; not verified on hardware; not reviewed independently |
| Pin | panda `3ee2796` → `bf8102a` (merge commit of [jherrodthomas/panda#19](https://github.com/jherrodthomas/panda/pull/19), fix commit `7d9210a`) |
| Decision | Register DQ-048, project lead, 2026-10-14, option A: shorten the persistence to about 0.7 s. The documents were changed on 2026-10-16 (WP-S-02 TSR-516(b), WP-S-04 OI-8); the firmware change was open. Implementation requested 2026-10-17 ("go ahead with DQ-048"). 0.7 s is the largest value that meets the budget, so the siren still ignores as many short EPS blips as it can (Claude's choice of value; reversible) |
| Requirement | TSR-516(b): persistence filter ≤ 0.7 s, so the siren sounds within the SG-02 1 s warning budget (WP-S-04 §3.7); SWSR-516 |
| Reference configuration affected | Yes: every build that runs the EPS-fault siren (only the reference build sets `safety_eps_fault`) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| panda `7d9210a` | `board/drivers/eps_fault_siren.h`, `tests/eps_fault_siren/test_eps_fault_siren.py` | `EPS_FAULT_SIREN_PERSIST_TICKS` 100 → 70: the siren sounds once an EPS fault has persisted 0.7 s (from when it was first seen with authority granted, DQ-367) instead of 1 s. Worst case from the first fault frame 0.7 s + 10 ms + 2 × 125 ms ≈ 0.96 s instead of 1.26 s | Yes (the warning now meets the SG-02 1 s budget; LKA torque was and is refused from the first fault frame) | Yes (more sirens on EPS faults lasting 0.7–1 s; accepted in DQ-048) | No | No | SG-02, SG-06; WP-S-04 OI-8; WP-M-02 OI-9 | WP-S-04 (T-28, §3.7, §5, Figure 5-2, OI-8), WP-S-02 TSR-516, WP-W-02 SWSR-516, WP-W-03, WP-W-05, WP-W-08 VS-SWQ-26, WP-W-09 CD-03, WP-M-02 OI-9, WP-M-11 | panda host tests, panda MISRA, plant simulation | DQ-048 A |
| this PR | `panda`, the work products above, `assurance/sim/faults.yaml`, `assurance/sim/search/search.py` (text), sim and failure-search results, register | Pin; records state 0.7 s and ≤ 0.96 s; Figure 5-2 regenerated | — | — | — | — | — | — | — | — |

## 2. Verification results

| Check | Result |
|---|---|
| panda host tests (local) | `tests/eps_fault_siren`: 9 tests pass; `test_constants` pins 0.7 s and fails on the old constant |
| LionDriver CI probe, panda `7d9210a` with opendbc `27f20db` (throwaway branch `claude/probe-sm-f1`) | `safety` run [39005055054](https://github.com/jherrodthomas/LionDriver/actions/runs/39005055054): all 8 jobs pass (safety and panda MISRA C:2012, panda host tests with the 0.7 s siren tests, safety tests and coverage, mutation in both variants, structural coverage, reference release build) |
| Plant simulation (local) | F-07, F-07-KS01 and F-07-OS: siren at 0.753 s instead of 1.003 s. In F-07 and F-07-OS the simulated driver now takes the siren as the cue (0.75 s, before the drift cue at 0.875 s) and corrects at 2.253 s instead of 2.375 s; in F-07-KS01 the drift cue (0.710 s) still comes first. No other result changes |
| Failure search (local, `sim/search`) | Curve assist-loss search: 92 of 120 samples leave the lane instead of 97; departures now start at a_y ≈ 0.44 m/s² (0.28 before), the sharpest curve held is 0.42 m/s²; WP-S-04 §3.9 row and OI-2 updated. The search text now says 0.7 s |
| WP-S-04 figures (local) | Figure 5-2 regenerated with the 0.7 s chain (siren ≤ 0.96 s, margin 0.04 s to the 1 s budget); Figure 5-1 EPS row 0.96 s; `fig_s04_timing.py --check` and its tests pass |
| HIL | **Not run** (D-04); the speaker timing (WP-S-04 M-05/M-10) stays open |

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | HIL: EPS fault while engaged, siren within 0.96 s of the first fault frame (WP-S-04 M-05/M-10) | HIL bench (D-04) |
| OI-2 | Reference logs: how often EPS faults last 0.7–1 s, the new sirens this change adds (EPS-fault impact record OI-4 still names 1 s) | Release |
| OI-3 | Analyses that still state the 1 s persistence or the 1.26 s worst case, for their owners: SW FMEA (`sw-fmea.yaml`, the EPS-fault siren cause), DFMEA (`dfmea.yaml`), WP-A-04 §5 fault tree note, `fta-fmea-map.yaml`, FMEA MSR plan | Analysis revisions |
