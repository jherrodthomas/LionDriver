# Change impact: alpha longitudinal refused on vehicles (stock AEB interlock)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host code (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-14; unit-tested; not verified on a vehicle; not reviewed independently** |
| Change request | [jherrodthomas/LionDriver#79](https://github.com/jherrodthomas/LionDriver/pull/79) (CA-001 of field issue FI-2026-001) |
| Reference configuration affected | No behaviour change: the reference Corolla TSS2 is camera-ACC and gets openpilot longitudinal without the alpha toggle |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|
| `openpilot/selfdrive/car/stock_aeb_interlock.py`, `openpilot/selfdrive/car/card.py`, `openpilot/selfdrive/ui/layouts/settings/developer.py`, `openpilot/selfdrive/ui/mici/layouts/settings/developer.py` | Alpha longitudinal is refused on every vehicle; it stays available only in the simulator (`SIMULATION` and `NOBOARD`). If the car interface still returns openpilot longitudinal on an alpha-capable platform, card goes passive (`noOutput`) and skips `CI.init()`, where radar/ADAS ECU knockouts happen. The settings toggle is hidden. On radar-ACC Toyotas, alpha longitudinal disables the radar ECU and reports PCS off, so this keeps the stock AEB/PCS barrier. 90 of 254 platforms lose alpha longitudinal | Yes | No | No | No | FI-2026-001 RC-01, HZ-002 (field-monitoring hazard log); requirement LD-FSR-001 | Field-monitoring CA-001 record; the HARA and FSC in `assurance/02-concept/` should reference LD-FSR-001 (not yet done) | `openpilot/selfdrive/car/tests/test_stock_aeb_interlock.py` (516 cases over all platforms); process replay | Take; the explained replay diff in §2 was decided by the project maintainer on 2026-10-14 |

## 2. Process replay: explained diff

Process replay compares against comma's reference logs for upstream `655bfde`. LionDriver can't re-baseline those yet (GAP-30). This change alters one replayed result, and that diff is expected:

| Segment | Process | Reference | With this change | Why |
|---|---|---|---|---|
| TESLA `aebd8f1d4ea16066\|000002d8--5850d3ea5c--2` | card | `carParams.openpilotLongitudinalControl` true; `safetyConfigs[0].safetyParam` 1 (`LONG_CONTROL`); `sendcan` frames to `0x2B9` | false; 0; no `0x2B9` frames | Replay sets `AlphaLongitudinalEnabled` because the route was driven with openpilot longitudinal, and on Tesla that exists only through alpha longitudinal. The interlock refuses it, so card runs stock longitudinal |

**Decision (2026-10-14, project maintainer):** exclude exactly these items for this process and segment, documented, until fork-owned references exist. Implemented as the `EXPLAINED_DIFFS` entry in `openpilot/selfdrive/test/process_replay/test_processes.py`:
- the two `carParams` fields are ignored;
- `sendcan` frames to `0x2B9` are dropped from both logs before comparison.

Every other field and CAN frame on this route, and every other route and process, is still compared. `test_explained_diffs.py` checks that the exclusion removes this diff and still reports a changed steering frame or another `carParams` field. The replay bot's diff report still shows the diff, so it stays visible.

**Remove the entry** when LionDriver hosts its own reference logs (GAP-30), or when the interlock changes.

## 3. Verification results

| Check | Result |
|---|---|
| `test_stock_aeb_interlock.py` | 516 passed; mutation (gate always allows) → 94 failures |
| `test_explained_diffs.py` | 3 passed |
| Process replay (CI) | Before the exclusion: 1 changed (this segment), 65 passed. After: CI on the PR head |
| Vehicle or bench check that PCS stays available on a radar-ACC Toyota | Not done (CA-001 AC-3) |
| Panda envelope refusing the radar knockout (CA-001 AC-2) | Not done; the forks are now LionDriver-owned, so this can go into `jherrodthomas/panda` / `opendbc` |
