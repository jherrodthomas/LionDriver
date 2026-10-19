# Change impact: no engagement outside the assured settings or below 60 km/h (DQ-221, DQ-280)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements two decisions of the project lead from 2026-10-18: DQ-221, option A (refuse engagement outside the assured settings in the reference configuration), and DQ-280, option A (refuse to engage below a highway speed floor; road-type data later). The lead set the floor at 60 km/h on 2026-10-19.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-19** in this LionDriver PR; unit-tested; not verified in the vehicle; not reviewed independently |
| Change requests | This LionDriver PR |
| Reference configuration affected | Yes. Both checks apply only on an assured platform (`assured_config.ASSURED_PLATFORMS`, the Corolla TSS2). Other platforms are unchanged: they stay outside the assured scope, allowed and logged (CA-008) |
| Decisions | DQ-221 A; DQ-280 A, floor 60 km/h |
| Requirements | Parent TSRs for both checks are being written by the safety-concept session; the SWSRs follow once they exist. STPA CC-18 and LS-13 (DQ-280), CC-14 and SW FMEA SWF-067 / SWF-ACT-063 (DQ-221) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Assured settings gate (DQ-221) | `selfdrive/selfdrived/assured_config.py`, `selfdrived.py`, `events.py`, `cereal/log.capnp` | On the reference platform, `selfdrived` raises the new NO_ENTRY event `settingNotAssured` ("Use Relaxed Distance, Experimental Off") while any setting of `ASSURED_PARAMS` differs from its assured value: following distance other than relaxed, Experimental Mode on, alpha longitudinal on, or a debug or maneuver mode on. `AssuredConfigStatus` gains `settings_in_scope`, which covers these settings alone; platform and software deviations are still only logged. The distance button no longer changes the following distance on the reference platform; the press is logged | Unit tests in `test_assured_config.py`: each setting refuses entry, entry only (no soft or immediate disable), other platforms unchanged, distance button ignored on the reference platform and unchanged elsewhere |
| Highway speed floor (DQ-280) | `assured_config.py` (`HIGHWAY_SPEED_FLOOR` = 60 km/h), `selfdrived.py`, `events.py`, `cereal/log.capnp` | On the reference platform, the new NO_ENTRY event `belowHighwaySpeed` ("Drive above 60 km/h to engage", or 37 mph) is raised while `carState.vEgo` is below 60 km/h | Unit tests: refused at 0, 10 m/s and just below the floor; allowed at the floor; entry only; alert text in both units |

Both are entry checks only. An item already engaged is not disengaged when the speed drops below 60 km/h or when a setting changes (§3).

## 2. What the driver sees

On the reference car, pressing the cruise button below 60 km/h, or with a non-assured setting, gives the standard no-entry alert with the refuse sound, and the item does not engage. The stock cruise follows as it does for any other no-entry: the cruise-mismatch supervision cancels it (TSR-308).

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Parent TSRs (safety-concept session) and the SWSRs that refine them in WP-W-02 | G3 |
| OI-2 | An engaged item keeps going below 60 km/h, for example into highway stop-and-go traffic. DQ-280 says "refuse to engage"; whether it should also hand back below the floor is not decided | Lead (behaviour default) |
| OI-3 | A setting changed in the settings menu while engaged (following distance, Experimental Mode) takes effect at once; only the next engagement is refused. Locking the settings while engaged is not decided | Lead (behaviour default) |
| OI-4 | User information (WP-O-03): the 60 km/h floor, the fixed relaxed distance and Experimental Mode off on the reference car | WP-O-03 owner |
| OI-5 | Vehicle check: the no-entry alert and the stock-cruise cancel below 60 km/h on the reference car | Vehicle test |
| OI-6 | Process replay: if a reference segment is on the reference platform, its `selfdrived` events change; CI on this PR shows it | This PR |
