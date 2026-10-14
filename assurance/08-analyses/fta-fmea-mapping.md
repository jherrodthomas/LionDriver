# FTA ↔ FMEA cross-mapping

| Field | Value |
|---|---|
| Purpose | Link the deductive fault trees of [WP-A-04](WP-A-04-system-fta-fmea.md) with the inductive FMEAs of [fmea/analyses/](fmea/analyses/) and check each against the other (ISO 26262-9:2018 §8, combination of FTA and FMEA) |
| Data | [fta-fmea-map.yaml](fta-fmea-map.yaml), checked by `tools/safety/fmea_lint.py` in CI; drawn on the [fault tree sheets](fta/README.md) as dark tags under each event |
| Status | **Pilot, SG-04 only, 2026-10-13; findings F-1…F-10 resolved the same day** (WP-A-04 v0.9; SW FMEA rev 0.7, DFMEA rev 0.3, System FMEA rev 0.6, PFMEA rev 0.3, HARA rev 0.4). Draft, AI-assisted; every link needs review. The other six goals are not mapped yet |

## 1. Method

The fault tree runs from the violation of a safety goal down to basic events. The FMEAs run from element failure modes up to vehicle effects. The map ties them at matching levels:

| Fault tree | FMEA |
|---|---|
| Top event (safety-goal violation) | Vehicle-level effect (`hazard:` of an FMEA effect, through [hara-mapping.yaml](fmea/hara-mapping.yaml) to the WP-C-03 hazardous events of the goal) |
| Intermediate event (gate) | System FMEA failure mode (optional `gates` entries) |
| Basic event, systematic software | SW FMEA or System FMEA failure mode |
| Basic event, systematic hardware | DFMEA failure mode |
| Basic event, random hardware | DFMEA failure mode or FMEDA row |
| Basic event, installation | PFMEA failure mode |
| Basic event, SOTIF | System FMEA failure mode (triggering conditions in WP-C-06) |
| Undeveloped event (driver, EPS, PCM, traffic) | Assumption of use or HARA rating, no FMEA |
| Event true by design | No FMEA, a reason |

The linter checks both directions for every goal in `scope`:

1. **Every event in the tree is backed.** Every basic and undeveloped event reachable in the tree, including events borrowed from other trees through transfers, is listed with its FMEA backing, or says why none is needed (by design, external), or states the gap.
2. **Every FMEA failure mode that reaches the goal is in the tree.** A failure mode whose effects cite a hazard of the goal must be cited by an event or gate of that tree, or be listed as `justified` (with the reason) or as a `tree_gap`.
3. **Consistency.** The class of an event is backed by the right analysis. A failure mode cited in a tree whose effects do not cite that goal's hazards is reported. So is a single-point event (computed from the gate logic) whose FMEA causes all claim a detection rating ≤ 4, because one of the two analyses must then be wrong.

## 2. SG-04 pilot result

After the fixes of §3, `fmea_lint.py --report`: *FTA-FMEA map SG-04: 32 events (backed 26, by design 2, external 4, unbacked 0); 32 FMEA modes reach SG-04 (in the tree 28, justified 4, tree gaps 0)*. The tree has 21 minimal cut sets (was 17), each with a row in WP-A-04 §5.1.

The lint also reports a `not_in_fta` row for a mode the tree now cites (error) and a mapped event that is no longer in any tree in scope (warning), so the map cannot go stale silently.

The table below is the first run, before the fixes: *25 events (backed 17, by design 2, external 4, unbacked 2); 18 FMEA modes reach SG-04 (in the tree 6, justified 4, tree gaps 8)*.

| | Count |
|---|---|
| Events reachable in the SG-04 tree | 25 (11 own basic, 4 own undeveloped, 10 borrowed from SG-01, SG-02 and SG-03) |
| Backed by an FMEA or FMEDA row | 17 |
| By design / external | 2 / 4 |
| No FMEA row | 2 (BE-4.13, BE-4.14) |
| FMEA failure modes whose effects cite HZ-006 (SG-04) | 18 |
| … cited in the tree | 6 |
| … justified outside the tree | 4 (host QM monitors the tree does not credit; wrong fingerprint after the reference lock) |
| … gaps in the tree | 8 |
| Single points whose FMEA claims a detection | 0 |

## 3. Findings

These were review input for WP-A-04 and the FMEAs. All ten are resolved in draft (last column); the resolutions need the same review as the links.

| ID | Finding | Affects | Resolution (2026-10-13) |
|---|---|---|---|
| F-1 | The SG-04 branch "envelope fails to clamp" reuses SG-01's `G-ENV`, whose software event BE-1.06 is the **lateral** check defect. The longitudinal check defect (SWF-003.C2, `longitudinal_accel_checks`) has no event in any tree | WP-A-04 §5 | New gate G-LENV with BE-4.16 (longitudinal check defect, SWF-003.C2) and BE-1.07…1.09; MCS-04.9 updated. SG-03 still uses the lateral G-ENV for acceleration; fix when SG-03 is mapped |
| F-2 | SWF-003 has no cause for the lower bound −3.5 m/s² being wrong for the vehicle (BE-4.01); SWF-003.C1 covers the upper bound only | SW FMEA | SWF-003.C3 (lower bound not derived; DFI-14 / DM-10; action SWF-ACT-003) |
| F-3 | The random-hardware event BE-4.03 (frame altered after the TX check) is backed only by SG-001 FMEDA rows. There is no FMEDA for the longitudinal path, and no DFMEA failure mode for corruption after the check | FMEDA, DFMEA | DFM-019 (frame altered between the TX check and the bus; DFM-ACT-013, TSR-517); FMEDA FMD-002 and FMD-010 now trace to it. The SG-001 FMEDA rates are argued to apply, since 0x2E4 and 0x343 share the TX path. **Decided 2026-10-14** (decision register DQ-002, option A): no separate SG-04 FMEDA; FMD-002 and FMD-010 carry the SG-04 rationale. The shared path meets the ASIL B metric targets SG-04 needs (SPFM 96.9 %, LFM 87.7 %, PMHF 6.9 FIT, generic rates); it misses ASIL C on SPFM by 0.1 percentage points, which matters only if AOU-05 fails. Revisit at the hardware gate with supplier failure rates |
| F-4 | BE-4.10 (soft-disable deceleration announced only at its start) and BE-4.11 (FCW on stale input) are backed only at system level (SFM-026, SFM-009). No SW FMEA row covers `longitudinal_planner.py:84-85` or `selfdrived.py:440-445` | SW FMEA | SWF-050 (deceleration starts with the soft-disable alert; SWF-ACT-050, TSR-624) and SWF-051 (FCW from stale or invalid input; SWF-ACT-051, TSR-625) |
| F-5 | Relay released while the item transmits puts stock ACC_CONTROL and the item's 0x343 on the bus together (SFM-034, DFM-011, SWF-010). No SG-04 branch covers conflicting deceleration commands | WP-A-04 §5 | New G4.8: (BE-4.19 relay released OR BE-4.20 stock 0x343 forwarded) AND BE-4.21 relay malfunction not detected in time; MCS-04.11 |
| F-6 | Item deceleration during accelerator override (SFM-020, SWF-017) has no SG-04 branch | WP-A-04 §5 | New G4.9: BE-4.22 (host, SFM-020) AND BE-4.23 (panda, SWF-017); MCS-04.12 |
| F-7 | G4.3 (unwarranted braking within the bound) lists only SOTIF causes. Stale or replayed host frames (SWF-023) and stale planner outputs (SWF-043) give the same effect from a systematic cause | WP-A-04 §5 | G4.3.1 = BE-4.06 OR BE-4.18 (stale or replayed braking, SWF-023, SWF-043); MCS-04.4; SPF-14 extended to SG-04 |
| F-8 | G4.2 has only the envelope's missing jerk limit (BE-4.05). The host-side step, where the jerk limit is bypassed by terms added after it (SWF-046), is not an event | WP-A-04 §5 | G4.2 = BE-4.17 (host step, SWF-046) AND BE-4.05 AND UE-4.04; MCS-04.3 now 2 + ext. |
| F-9 | Nine failure modes the tree shows can reach SG-04 do not cite HZ-006 in their effects: DFM-001, DFM-003, PFM-001, SFM-026, SWF-001, SWF-006, SWF-007, SWF-022, SWF-028 | System FMEA, DFMEA, SW FMEA, PFMEA | HZ-006 effects added to DFM-001, DFM-003, PFM-001, SFM-026 (also in HARA HZ-006 sfm_refs), SWF-006, SWF-007, SWF-022, SWF-028 and SWF-012; SWF-001 left out of SG-04 with BE-1.06 (F-1) |
| F-10 | BE-4.13 (deceleration request while not engaged) and BE-4.14 (no item-side ramp when authority is revoked) have no FMEA failure mode at all | System FMEA, SW FMEA | SWF-052 (negative acceleration sent while not active; SWF-ACT-052) for BE-4.13; SWF-053 (deceleration ends in one step at revocation; SWF-ACT-053, TSR-208) for BE-4.14 |

## 4. Next

1. Review the SG-04 links, the F-1…F-10 resolutions and the new FMEA rows (SWF-050…053, SWF-003.C3, DFM-019); F-3 decided 2026-10-14 (DQ-002).
2. Map SG-01 to SG-03 and SG-05 to SG-07 the same way and add them to `scope`. Draft links can be proposed from the elements and code references both sides cite, then reviewed one by one.
3. Retire the SFMEA-01…SFMEA-39 table of WP-A-04 §10 in favour of [system-fmea.yaml](fmea/analyses/system-fmea.yaml), so the map has one System FMEA to point at.
