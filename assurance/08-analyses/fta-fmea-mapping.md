# FTA ↔ FMEA cross-mapping

| Field | Value |
|---|---|
| Purpose | Link the deductive fault trees of [WP-A-04](WP-A-04-system-fta-fmea.md) with the inductive FMEAs of [fmea/analyses/](fmea/analyses/) and check each against the other (ISO 26262-9:2018 §8, combination of FTA and FMEA) |
| Data | [fta-fmea-map.yaml](fta-fmea-map.yaml), checked by `tools/safety/fmea_lint.py` in CI; drawn on the [fault tree sheets](fta/README.md) as dark tags under each event |
| Status | **SG-04, SG-01 and SG-07 mapped.** SG-04 pilot 2026-10-13, findings F-1…F-10 resolved the same day (WP-A-04 v0.9; SW FMEA rev 0.7, DFMEA rev 0.3, System FMEA rev 0.6, PFMEA rev 0.3, HARA rev 0.4). SG-01 2026-10-16, findings F-11…F-16: tree findings resolved in WP-A-04 v1.0, FMEA findings F-14 and F-15 open for the FMEA owners. SG-07 2026-10-16, with its tree re-based on the harness box switches (WP-A-04 v1.1, RR-2026-010); findings F-17…F-19 open for the FMEA owners. Draft, AI-assisted; every link needs review. SG-02, SG-03, SG-05 and SG-06 are not mapped yet |

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

## 2a. SG-01 result

`fmea_lint.py --report` after the tree changes of WP-A-04 v1.0: *FTA-FMEA map SG-01: 28 events (backed 26, by design 1, external 1, unbacked 0); 57 FMEA modes reach SG-01 (in the tree 46, justified 11, tree gaps 0)*. The tree has 36 minimal cut sets (was 27), each covered by a row of WP-A-04 §2.1.

First run, on the v0.9 tree with only the events SG-04 borrows mapped:

| | Count |
|---|---|
| Events reachable in the SG-01 tree | 23 (22 basic, 1 undeveloped; 6 already mapped for SG-04) |
| FMEA failure modes whose effects cite HZ-001, HZ-002, HZ-003 or HZ-010 (SG-01) | 57 |
| … cited in the tree before the mapping | 8 |
| … placed on an existing event or gate by the mapping | 31 |
| … that needed a new event or gate (F-11…F-13) | 7 (SWF-002; DFM-011, SFM-034, SWF-010, SWF-012; DFM-015, SWF-026 — DFM-011, SFM-034 and SWF-012 through the SG-04 events BE-4.19 and BE-4.21) |
| … justified outside the tree (F-16) | 11 |
| Single points whose FMEA claims a detection | 0 |

The justified modes are of two kinds. Five are QM host monitors that the tree does not credit, as for SG-04 (SFM-014, SFM-016, SFM-030, SWF-034, SWF-037). Six are release, installation and configuration modes (PFM-003, -004, -005, -007, -016, -017): they replace or leave unverified the item the trees analyse rather than adding an event to it, and are controlled by release management (WP-P-10) and installation (WP-O-02). The firmware part of a wrong release stays an event (BE-1.09, BE-1.18).

The eight warnings `fmea_lint.py` now reports for the map are F-14 and F-15 below. They stay until the FMEA owners decide them; the map shows the tree's view.

## 2b. SG-07 result

The SG-07 tree was re-based first on [RR-2026-010](../04-hardware/reviews/RR-2026-010.md). The intercept "relay" is two DG419LE analog switches in comma's harness box. They are powered from the box supply, driven by SBU1, pulled to pass-through by R2/R3, and clamped by D2/D3, and they give no position feedback. The DFMEA rev 0.5 modes DFM-010.C1…C3, DFM-020 and DFM-021 each became an event (WP-A-04 v1.1).

`fmea_lint.py --report`: *FTA-FMEA map SG-07: 21 events (backed 13, by design 1, external 1, unbacked 6); 17 FMEA modes reach SG-07 (in the tree 15, justified 2, tree gaps 0)*. The tree has 17 minimal cut sets (was 11), each covered by a row of WP-A-04 §8.1. Fifteen are of effective order ≤ 1: SG-07 is still mostly single points.

| | Count |
|---|---|
| Events on the v1.0 tree | 14 (13 basic, 1 undeveloped), none mapped |
| FMEA modes whose effects cite HZ-011 (SG-07) | 17 |
| … that matched an event or gate of the v1.0 tree | 10 (SFM-033 and SFM-034 on gates G7.1 and G7.3) |
| … that needed a new or re-cut event (harness box, F-18) | 5 (DFM-008; DFM-010, split into three events; DFM-020; DFM-021; SWF-015) |
| … justified outside the tree | 2 (PFM-004, PFM-007; as for SG-01) |
| Events with no FMEA mode | 6 (F-17) |
| Single points whose FMEA claims a detection | 1 (BE-7.05, F-19) |

## 3. Findings

These were review input for WP-A-04 and the FMEAs. F-1…F-10 (SG-04) are resolved in draft; of F-11…F-16 (SG-01), the tree findings are resolved in WP-A-04 v1.0 and the FMEA findings are open; F-17…F-19 (SG-07) are open for the FMEA owners (last column). Every resolution needs the same review as the links.

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

| F-11 | G1.2.1.a (false authority) listed only vehicle-data and MCU causes. A defect in the envelope's own not-allowed torque check or `controls_allowed` bookkeeping (SWF-002, `lateral.h:111-114`) had no event, and a mode or param change or replaced firmware, which removes the check, was in G-ENV only. SG-03 and SG-04 already had the bypass in their inactive-value gates (BE-3.10) | WP-A-04 §2 | **Resolved 2026-10-16 (v1.0):** BE-1.25 (SWF-002) and BE-1.08/BE-1.09 under G1.2.1.a; MCS-01.7 extended; MCS-01.10 {BE-1.08 or BE-1.09, BE-1.15}, effective 1 through DFI-13 |
| F-12 | Relay released, or stock `0x2E4` forwarded, while the item transmits puts the stock STEERING_LKA and the item's command on the bus together (DFM-011, SFM-034, SWF-010, SWF-012, all citing HZ-002). SG-04 has this branch (G4.8, F-5); SG-01 did not | WP-A-04 §2 | **Resolved 2026-10-16 (v1.0):** new G1.4 = (BE-4.19 OR BE-1.26 stock `0x2E4` forwarded) AND BE-4.21; MCS-01.11. No EPS input is ANDed in, as in G4.8: each command is in its own bound, but their combination is not one the EPS limit was assumed for |
| F-13 | A command corrupted on the SoC-to-MCU SPI link and passing both 8-bit XOR checks (DFM-015, SWF-026) had no event. The envelope still checks the frame, so it is one more way for a wrong command to reach the envelope, not a single point | WP-A-04 §2 | **Resolved 2026-10-16 (v1.0):** BE-1.24 under G-SoC (random HW); MCS-01.6 extended |
| F-14 | The mapping places eight FMEA modes on events that SG-01 and SG-04 share, but their effects do not cite that goal's hazard: on BE-1.07 (MCU execution fault) DFM-002 flash constants, DFM-005 time base, DFM-007 brown-out and DFM-018 over-temperature; on BE-1.09 (envelope replaced) DFM-016 SoC-driven boot or reflash and PFM-002 debug signing key; on BE-4.16 SWF-016 host TX skipping `safety_tx_hook`. All cite HZ-002 (or HZ-005) but not HZ-006, so they reach SG-04 through G-LENV unrecorded. SWF-005 (corrupted brake-pressed value accepted) reaches SG-01 through BE-1.16 (authority not revoked on brake) but cites only HZ-008 | DFMEA, PFMEA, SW FMEA | **Open, for the FMEA owners** (as F-9): add HZ-006 effects to DFM-002, DFM-005, DFM-007, DFM-016, DFM-018, PFM-002 and SWF-016, and an HZ-002 effect to SWF-005; or say why the tree's path is not credible. `fmea_lint.py` warns until then |
| F-15 | BE-1.17 (`0x1D2` stuck at "cruise active" with a valid checksum) is backed only by SWF-006, which covers loss of the frame and its detection time. No FMEA mode covers a stuck value while valid frames keep arriving (no counter on `0x1D2`, GAP-01). The brake case BE-1.16 has SWF-005 | SW FMEA | **Open, for the SW FMEA owner:** a cause under SWF-007 or SWF-006 for a stuck `PCM_CRUISE` value, with TSR-401…TSR-406 as the measure |
| F-16 | Eleven modes reach SG-01 but are no tree event: five QM host monitors the tree does not credit (SFM-014, SFM-016, SFM-030, SWF-034, SWF-037) and six release, installation and configuration modes (PFM-003, -004, -005, -007, -016, -017) | — | **Justified** in `not_in_fta` with the reasons of §2a. A reviewer should confirm that the trees may assume the released reference configuration and leave these to WP-P-10 and WP-O-02 |

| F-17 | Six SG-07 events have no FMEA failure mode: BE-7.02 power-save `0xe7` and BE-7.03 bus configuration commands accepted in a car mode (FFI-CM-08, -09); BE-7.04 forwarding queue overflow or latency; BE-7.07 PCS IDs in the TX whitelist without a content check; BE-7.08 SoC sends PCS-relevant frames; BE-7.13 ACC request during a PCS event. They exist only as WP-A-02 FFI rows or WP-A-04 §10 SFMEA rows. BE-7.06 (camera-side FDCAN or transceiver) has FMEDA SG-009 rows but no DFMEA mode | SW FMEA, System FMEA, DFMEA | **Open, for the FMEA owners** (as F-10): one SW FMEA mode per event (the first five with TSR-513, TSR-707, TSR-705 as measures), a System FMEA mode for BE-7.13, and a DFMEA mode for the camera-side transceiver. `fmea_lint.py` reports each as unbacked until then |
| F-18 | The SG-07 tree drew the intercept as a relay (welded contacts, a passive stock path). RR-2026-010 shows powered switches: a stuck switch, a stuck drive and an open pull-down are three different causes; a lost box supply and a shorted clamp break or load the stock path whatever the switch state; the car-side transceiver can block bus 0. Diagnostic frames from the item (SWF-015) had no branch. DFM-016 (SoC drives the MCU into the bootloader) now backs BE-7.10 but cites HZ-002/HZ-005 only | WP-A-04 §8, DFMEA | **Tree resolved 2026-10-16 (v1.1):** G7.3 split into BE-7.09, BE-7.15, BE-7.16; G7.4 adds BE-7.17 (SPF-15), BE-7.18, BE-7.19; new G7.6 (BE-7.20, BE-7.21). **Open, for the DFMEA owner:** an HZ-011 effect on DFM-016. The DFM-020 effects are derived from the drawing; the bench test (DFM-ACT-014) decides MCS-07.12 |
| F-19 | BE-7.05 (block list wrongly includes a PCS message) is a single point in the tree, but its only FMEA cause, SWF-011.C1, claims detection D=3. The rating credits the opendbc safety tests of the TX table at design time; nothing detects the fault in the field | SW FMEA | **Open, for the SW FMEA owner:** confirm that D=3 rests on design-time tests that cover every forwarded PCS ID (TSR-704), or raise it. The tree stays a single point either way (MCS-07.5) |

## 4. Next

1. Review the SG-04 links, the F-1…F-10 resolutions and the new FMEA rows (SWF-050…053, SWF-003.C3, DFM-019); F-3 decided 2026-10-14 (DQ-002).
2. Review the SG-01 links and F-11…F-13 (WP-A-04 v1.0). The FMEA owners decide F-14 and F-15.
3. Review the SG-07 links and the re-based tree (WP-A-04 v1.1). The FMEA owners decide F-17…F-19. When the lead decides DQ-209 (accept comma's box, or build a LionDriver adapter), re-draw G7.3 and G7.4 for the chosen design.
4. Map SG-02, SG-03, SG-05 and SG-06 the same way, and add each to `scope`. SG-03 still borrows the lateral G-ENV for acceleration (F-1); fix that when SG-03 is mapped.
5. Retire the SFMEA-01…SFMEA-39 table of WP-A-04 §10 in favour of [system-fmea.yaml](fmea/analyses/system-fmea.yaml), so the map has one System FMEA to point at.
