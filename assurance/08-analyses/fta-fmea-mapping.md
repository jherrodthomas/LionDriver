# FTA ↔ FMEA cross-mapping

| Field | Value |
|---|---|
| Purpose | Link the deductive fault trees of [WP-A-04](WP-A-04-system-fta-fmea.md) with the inductive FMEAs of [fmea/analyses/](fmea/analyses/) and check each against the other (ISO 26262-9:2018 §8, combination of FTA and FMEA) |
| Data | [fta-fmea-map.yaml](fta-fmea-map.yaml), checked by `tools/safety/fmea_lint.py` in CI; drawn on the [fault tree sheets](fta/README.md) as dark tags under each event, in Figures 1 and 2 (§1.1) and on the hand-off sheets (§5) |
| Status | **All eight goals mapped** (SG-08 added 2026-10-16 with its new tree, WP-A-04 v1.3, F-37, F-38, DQ-365). (SG-02, SG-03, SG-05, SG-06 on 2026-10-16, WP-A-04 v1.2, findings F-20…F-36; five questions queued for the lead, DQ-360…DQ-364). SG-04 pilot 2026-10-13, findings F-1…F-10 resolved the same day (WP-A-04 v0.9; SW FMEA rev 0.7, DFMEA rev 0.3, System FMEA rev 0.6, PFMEA rev 0.3, HARA rev 0.4). SG-01 2026-10-16, findings F-11…F-16: tree findings resolved in WP-A-04 v1.0, FMEA findings F-14 and F-15 open for the FMEA owners. SG-07 2026-10-16, with its tree re-based on the harness box switches (WP-A-04 v1.1, RR-2026-010); findings F-17…F-19 open for the FMEA owners. 2026-10-25: the WP-A-04 §10 System FMEA table is retired, so [system-fmea.yaml](fmea/analyses/system-fmea.yaml) is the only System FMEA (DQ-127 A, §4 step 5). Draft, AI-assisted; every link needs review. |

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

### 1.1 Figures

Figure 1 shows how the two analyses meet, with one real chain. Figure 2 shows every goal's tree in its real shape and what backs each of its events. §5 has one hand-off sheet per goal.

![Figure 1: the fault tree and the FMEA as two ladders on the levels vehicle, system, element and cause. The tree runs down from the SG-04 top event through gate G4.1.1 to basic event BE-4.03; the FMEA runs up from cause DFM-019.C1 through failure mode DFM-019 to its end effect on HZ-006. The rungs are the checks: the end effect's hazard belongs to the goal, and the basic event is backed by a failure mode the tree cites](figures/fig-map-1-ladders.svg)

*Figure 1. The tree stops at the basic event, which is the top of an FMEA failure mode; the causes live only in the FMEA. The worked chain is read from the documents (`CHAIN` in the generator).*

![Figure 2: the eight fault trees drawn small, each basic event a dot coloured green (FMEA or FMEDA row), grey (by design or external) or red (no FMEA yet), with a stalk for its number of FMEA causes; SG-02, SG-05, SG-06, SG-07 and SG-08 have events without an FMEA row](figures/fig-map-2-trees.svg)

*Figure 2. Every tree, in its real shape. Red edges are single-point paths. The counts are those of `fmea_lint.py --report`.*

The figures and the hand-off sheets are drawn by [`figures/fta_fmea_figures.py`](figures/fta_fmea_figures.py) from WP-A-04, this map and the FMEAs; the System FMEA cards (fmea-plan Figure 3-17) show the same links from the FMEA side. After a change to a tree, this map or an FMEA, regenerate them with the tree sheets and the cut sets:

```bash
python3 assurance/08-analyses/fta/fta_diagrams.py && python3 assurance/08-analyses/fta/fta_cutsets.py
python3 assurance/08-analyses/figures/fta_fmea_figures.py && python3 tools/safety/fmea_cards.py
```

CI runs each with `--check`.

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

## 2c. SG-02, SG-03, SG-05 and SG-06 result

Drafted per goal from the lint's list of unmapped events and uncited modes, then reviewed and applied together, because SG-02 and SG-06 share the warning gates (G-HMI, G-SIREN) and SG-03 and SG-04 share the longitudinal envelope gate (G-LENV). `fmea_lint.py --report` with all seven goals in `scope`:

| Goal | Events (backed, by design, external, unbacked) | FMEA modes reaching the goal (in the tree, justified, tree gaps) | Cut sets (was) | Tree changes |
|---|---|---|---|---|
| SG-02 | 27 (22, 1, 3, 3) | 31 (30, 1, 0) | 100 (33) | 7 events, 5 gates (F-21, F-32, F-33) |
| SG-03 | 28 (24, 1, 3, 0) | 30 (22, 8, 0) | 22 (16) | G-LENV, G3.1.1.b, G3.6, G3.7 (F-20) |
| SG-05 | 18 (12, 0, 4, 2) | 13 (12, 1, 0) | 12 (6) | 2 events, borrowed bypass events, BE-5.06 latent (F-24, F-30) |
| SG-06 | 26 (22, 1, 3, 1) | 23 (22, 1, 0) | 85 (32) | 4 events, 4 gates (F-23, F-32, F-33) |

The cut sets of SG-02 and SG-06 triple because each cause is paired with every way the warning can fail, and v1.2 adds three such ways (masked alert, latent siren path, big-model masking). The new cut sets are of order 2 or more in form; those of effective order ≤ 1 are listed in WP-A-04 §9.1.

The warnings `fmea_lint.py` reports for these goals are F-25…F-28 below. They stay until the FMEA owners decide them.

## 2d. SG-08 result

SG-08 (ASIL A, unresponsive driver) came with WP-C-03 v0.4, so its tree (WP-A-04 §13) was drawn and mapped together. `fmea_lint.py --report`: *FTA-FMEA map SG-08: 12 events (backed 6, by design 0, external 1, unbacked 5); 3 FMEA modes reach SG-08 (in the tree 3, justified 0, tree gaps 0)*. All 11 cut sets are single points (MCS-08.1…08.8; SPF-18).

The System FMEA covers the driver-monitoring chain (SFM-022, SFM-023, SFM-025), and since SW FMEA rev 0.9 the SW FMEA does too (SWF-061…SWF-064 for `dmonitoringd` and `dmonitoringmodeld`). BE-8.04 is backed by SWF-063 and BE-8.05 by SWF-061; SWF-061 also backs BE-8.07 at unit level. Since rev 1.1, SWF-085 backs BE-8.06 and SWF-086 backs BE-8.08; only BE-8.03 (driver camera or IR, hardware) remains unbacked (F-37). By code reading, demo mode does not switch the alerts off as MCS-08.4 says: it decouples the policy from the real vehicle state and unlocks the monitored seat (SWF-085). SWF-062 (terminal state without the SG-010 safe state) backs BE-8.10 in the SG-08 tree, with SFM-025; the safe state is decided (DQ-365 A, which absorbed DQ-220) but not implemented. Of the G-HMI modes borrowed from SG-02, SWF-035 and SWF-082 cite HZ-013 since SW FMEA rev 1.1; SFM-026 and SFM-027 do not yet, and the lint warns on each (as F-26).

## 3. Findings

These were review input for WP-A-04 and the FMEAs. F-1…F-10 (SG-04) are resolved in draft; of F-11…F-16 (SG-01), the tree findings are resolved in WP-A-04 v1.0 and the FMEA findings are open; F-17…F-19 (SG-07) are open for the FMEA owners; of F-20…F-36 (SG-02, SG-03, SG-05, SG-06), the tree findings are resolved in WP-A-04 v1.2, the FMEA findings are open, and five are queued for the lead (last column). Every resolution needs the same review as the links.

| ID | Finding | Affects | Resolution (2026-10-13) |
|---|---|---|---|
| F-1 | The SG-04 branch "envelope fails to clamp" reuses SG-01's `G-ENV`, whose software event BE-1.06 is the **lateral** check defect. The longitudinal check defect (SWF-003.C2, `longitudinal_accel_checks`) has no event in any tree | WP-A-04 §5 | New gate G-LENV with BE-4.16 (longitudinal check defect, SWF-003.C2) and BE-1.07…1.09; MCS-04.9 updated. SG-03 still uses the lateral G-ENV for acceleration; fix when SG-03 is mapped |
| F-2 | SWF-003 has no cause for the lower bound −3.5 m/s² being wrong for the vehicle (BE-4.01); SWF-003.C1 covers the upper bound only | SW FMEA | SWF-003.C3 (lower bound not derived; DFI-08 / DM-10; action SWF-ACT-003) |
| F-3 | The random-hardware event BE-4.03 (frame altered after the TX check) is backed only by SG-001 FMEDA rows. There is no FMEDA for the longitudinal path, and no DFMEA failure mode for corruption after the check | FMEDA, DFMEA | DFM-019 (frame altered between the TX check and the bus; DFM-ACT-013, TSR-517); FMEDA FMD-002 and FMD-010 now trace to it. The SG-001 FMEDA rates are argued to apply, since 0x2E4 and 0x343 share the TX path. **Decided 2026-10-14** (decision register DQ-002, option A): no separate SG-04 FMEDA; FMD-002 and FMD-010 carry the SG-04 rationale. The shared path meets the ASIL B metric targets SG-04 needs (SPFM 96.9 %, LFM 87.7 %, PMHF 6.9 FIT, generic rates); it misses ASIL C on SPFM by 0.1 percentage points, which matters only if AOU-05 fails. Revisit at the hardware gate with supplier failure rates |
| F-4 | BE-4.10 (soft-disable deceleration announced only at its start) and BE-4.11 (FCW on stale input) are backed only at system level (SFM-026, SFM-009). No SW FMEA row covers `longitudinal_planner.py:84-85` or `selfdrived.py:488-493` | SW FMEA | SWF-050 (deceleration starts with the soft-disable alert; SWF-ACT-050, TSR-624) and SWF-051 (FCW from stale or invalid input; SWF-ACT-051, TSR-625) |
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

| F-17 | Six SG-07 events have no FMEA failure mode: BE-7.02 power-save `0xe7` and BE-7.03 bus configuration commands accepted in a car mode (FFI-CM-08, -09); BE-7.04 forwarding queue overflow or latency; BE-7.07 PCS IDs in the TX whitelist without a content check; BE-7.08 SoC sends PCS-relevant frames; BE-7.13 ACC request during a PCS event. They exist only as WP-A-02 FFI rows or rows of the WP-A-04 §10 table (retired 2026-10-25, DQ-127). BE-7.06 (camera-side FDCAN or transceiver) has FMEDA SG-009 rows but no DFMEA mode | SW FMEA, System FMEA, DFMEA | **Open, for the FMEA owners** (as F-10): one SW FMEA mode per event (the first five with TSR-513, TSR-707, TSR-705 as measures), a System FMEA mode for BE-7.13, and a DFMEA mode for the camera-side transceiver. `fmea_lint.py` reports each as unbacked until then. 2026-10-25 (DQ-127): System FMEA rev 0.34 takes in the camera-side FDCAN or transceiver as SFM-033.C6; the DFMEA mode is still open |
| F-18 | The SG-07 tree drew the intercept as a relay (welded contacts, a passive stock path). RR-2026-010 shows powered switches: a stuck switch, a stuck drive and an open pull-down are three different causes; a lost box supply and a shorted clamp break or load the stock path whatever the switch state; the car-side transceiver can block bus 0. Diagnostic frames from the item (SWF-015) had no branch. DFM-016 (SoC drives the MCU into the bootloader) now backs BE-7.10 but cites HZ-002/HZ-005 only | WP-A-04 §8, DFMEA | **Tree resolved 2026-10-16 (v1.1):** G7.3 split into BE-7.09, BE-7.15, BE-7.16; G7.4 adds BE-7.17 (SPF-15), BE-7.18, BE-7.19; new G7.6 (BE-7.20, BE-7.21). **Open, for the DFMEA owner:** an HZ-011 effect on DFM-016. The DFM-020 effects are derived from the drawing; the bench test (DFM-ACT-014) decides MCS-07.12 |
| F-19 | BE-7.05 (block list wrongly includes a PCS message) is a single point in the tree, but its only FMEA cause, SWF-011.C1, claims detection D=3. The rating credits the opendbc safety tests of the TX table at design time; nothing detects the fault in the field | SW FMEA | **Open, for the SW FMEA owner:** confirm that D=3 rests on design-time tests that cover every forwarded PCS ID (TSR-704), or raise it. The tree stays a single point either way (MCS-07.5) |

| F-20 | SG-03 borrowed the lateral envelope gate G-ENV (the F-1 carry-over), so the longitudinal check defect had no SG-03 event. A wrong fingerprint (SFM-032, PFM-013) had no event; a step within the bound sat under "above the bound" as a single point although it needs the host step (SWF-046, as F-8); stock ACC and the item's `0x343` together (SG-04 G4.8) had no acceleration branch | WP-A-04 §3, §5 | **Resolved 2026-10-16 (v1.2):** G-LENV defined in §3 and referenced from §5; BE-1.05 in G3.1.1.b; new G3.6 (BE-4.17 AND BE-3.03 AND UE-3.05); new G3.7 (as G4.8). MCS-03.3, -03.8 revised, MCS-03.12 added. G3.7's modes cite no HZ-005 (F-26) |
| F-21 | SG-02 lacked six real paths: the item's diagnostic frames resetting the EPS (SWF-015); a selfdrived crash with the heartbeat kept, so the heartbeat-loss siren does not sound (SWF-036, SFM-006.C1); a take-over alert masked by a less urgent one (SWF-035, SFM-027); a latent siren path fault (DFM-017.C2); diagnostics masked during the big-model fallback (BE-1.20); an EPS drop not signalled (SFM-005.C1) | WP-A-04 §4 | **Resolved 2026-10-16 (v1.2):** G2.1.2 (BE-2.20 AND BE-7.20), G2.5.1 (BE-2.21), BE-2.25 under G-HMI, BE-2.22 under G-SIREN, BE-1.20 in G2.3.1, UE-2.19 in G2.1.1. MCS-02.1, -02.3, -02.6 extended, MCS-02.9…02.11 added; SPF-17 |
| F-22 | The random-HW events of SG-02, SG-03, SG-05 and SG-06 (BE-2.06, BE-2.07, BE-2.15, BE-2.22, BE-3.04, BE-5.02, BE-6.02) have DFMEA modes but rest on SG-001/SG-009 FMEDA rows or none. DQ-002 accepted reuse for SG-04 only | FMEDA, WP-H-04 | **Resolved 2026-10-18 (DQ-362 A):** the SG-001 and SG-009 FMEDA rows are reused for SG-02, SG-03 and SG-06 (one analysis, a note per goal, applied by the hardware session); the SPFM miss of 0.16 points against the ASIL C 97 % target (96.84 %) is carried as an open hardware item for G2. fta-fmea-map.yaml: BE-2.06, BE-2.07, BE-6.02 cite the rows, BE-3.04 no longer says SG-04 only (WP-A-04 v1.11) |
| F-23 | SG-06 lacked the supply-loss branch SG-02 has (G2.7), the selfdrived crash (as F-21), the big-model masking, and a PCM that stops executing ACC without signalling it (SFM-011.C1). It also had no branch for a lead missed or seen late, although H-06 is rated from too little and too late deceleration (SFM-010, SFM-012, PFM-012) | WP-A-04 §7 | **Resolved 2026-10-16 (v1.2):** G6.8 (BE-2.07 AND UE-6.07), G6.6.1 (BE-2.21), BE-1.20 in G6.1.1, UE-6.08 in G6.3.1, G6.9 (BE-6.09 [SOTIF], BE-6.10 by design). MCS-06.1, -06.3, -06.5, -06.8 extended, MCS-06.9…06.11 added. G6.9's scope is DQ-361, UE-6.08's measure DQ-360 |
| F-24 | SG-05 held only signal and MCU causes. The envelope's own brake-edge defect or wrong brake source (SWF-008), its cruise-revocation defect (SWF-009) and a wrong safety mode or parameter (SWF-022), a replaced envelope or a debug build all defeat release with no SG-05 event | WP-A-04 §6 | **Resolved 2026-10-16 (v1.2):** BE-5.14 in G5.1.1, BE-5.15 in G5.1.2 and G5.2, BE-1.08/1.09/1.18 wherever BE-5.02 sits; MCS-05.9…05.11; SPF-16 |
| F-25 | `0x1D2` stuck at "cruise active" (BE-5.03, a single point) and GAS_RELEASED stuck "released" (BE-3.11; BE-4.24 since WP-A-04 v1.8, formerly BE-5.08) while valid frames keep arriving have no FMEA cause. Their only backing, SWF-006 and SWF-017, claims D=3 for frame loss and decoding defects. Extends F-15 | SW FMEA | **Open, for the SW FMEA owner:** causes for stuck PCM_CRUISE and GAS_RELEASED values with valid frames (TSR-401…TSR-406 as the measure, rated as undetected in the field) |
| F-26 | Modes the new trees cite reach the goal but their effects do not cite its hazard. SG-02 (HZ-004): SWF-033, SWF-043, DFM-004, DFM-016. SG-03 (HZ-005): SWF-004, SWF-005, SWF-006, SWF-008, SWF-017, SWF-052, SFM-017, SWF-031, through borrowed events DFM-005, DFM-018, SWF-022, SFM-006, SWF-033, SWF-018, SWF-020, DFM-014, through G3.7 DFM-011, SFM-034, SWF-010, SWF-012 (F-20), and the engagement modes SFM-013, SWF-030, SWF-007 (cleared by DQ-364 option A, F-34). SG-05 (HZ-008/009): DFM-001, DFM-003, SWF-013, SWF-028, PFM-001, PFM-002, DFM-016, SFM-021, SFM-028, SWF-039, SWF-017, SFM-020. SG-06 (HZ-007/012): 18 modes, mostly faults that stop every item frame and name only the steering loss | DFMEA, PFMEA, SW FMEA, System FMEA | **Open, for the FMEA owners** (as F-9, F-14): add the hazard effect where the tree's path is credible, or say why it is not. `fmea_lint.py` lists each one |
| F-27 | Single points in the trees whose FMEA claims detection: BE-5.15 (SWF-009.C1 D=3), BE-5.14 (SWF-008.C1/C2 D=4/3), BE-3.11 (SWF-017.C1, SWF-006.C1 D=3). As F-19, the ratings credit design-time tests | SW FMEA | **Open, for the SW FMEA owner:** confirm the tests behind each rating, or raise it. The trees stay single points either way |
| F-28 | Events with no FMEA mode, or only partial backing: BE-2.08 (host EPS-fault warning late; closed by SFM-038.C1/C2, System FMEA rev 0.23, and SWF-088, SW FMEA rev 1.3), BE-2.14 (siren not triggered), BE-2.24 (steerSaturated late; closed by SFM-038.C3, rev 0.23), BE-5.05 (no envelope override check; backed by SWF-087 since SW FMEA rev 1.2), BE-5.12 (MAIN_ON ignored at the baseline); BE-2.05 (no mode for a whole-SoC crash), BE-2.06 (configuration commands, as F-17), BE-6.05 (frozen longitudinal request; closed by SFM-037, System FMEA rev 0.22), BE-6.01 (radarFault has no cause; unsure it applies to the camera-ACC reference car) | SW FMEA, System FMEA, DFMEA | **Open, for the FMEA owners:** one mode or cause each, or a statement that the event is out of FMEA scope |
| F-29 | G5.4 (accelerator does not override braking) is in SG-05, but SG-05's rated events cover brake, cancel and steering only; the FMEA puts the path under HZ-006, and SG-04 G4.9 lacks the stuck gas signal that defeats both its checks | WP-A-04 §5, §6; WP-C-03 | **Resolved 2026-10-17 (DQ-363 A, WP-A-04 v1.8):** the case moves to SG-04. G4.9 gains G4.9.2 (BE-4.24 stuck gas signal with UE-4.25, MCS-04.13); G5.4 and MCS-05.6 leave SG-05. SFM-020 and SWF-017 now sit under the goal their effects name (HZ-006). SWF-057 (wrong carState decoding) stays cited in SG-05 on BE-5.06 for its steering-torque cause (HZ-009), and its gas-bit cause is on BE-4.24, where SG-04 warns that it names no HZ-006 |
| F-30 | BE-5.06 (host override check fails) is present by design below 500 units of driver torque (overriding counts as active), so MCS-05.5 rests on the EPS alone | WP-A-04 §6, §9 | **Resolved 2026-10-16 (v1.2):** BE-5.06 tagged latent; MCS-05.5 effective 0 + ext.; SPF-12 restated. Measures DQ-053 / SFM-ACT-016 and TSR-304 |
| F-31 | BE-5.10 said cruiseMismatch is raised after 6 s with no reaction; at BL-005 it alerts after 1 s (TSR-308), but SWF-039 is still rated at BL-004 | WP-A-04 §6, SW FMEA | **Tree resolved (v1.2):** dated BL-005 note. **Open, for the SW FMEA owner:** re-rate SWF-039 at BL-005 |
| F-32 | An EPS or PCM that silently stops acting on the item's requests (SFM-005.C1, SFM-011.C1) is seen by neither the host nor the envelope (UE-2.19, UE-6.08; MCS-02.10, MCS-06.11). No assumption of use covers it | WP-A-04 §4, §7; WP-C-01 | **Resolved 2026-10-18 (DQ-360 A):** an assumption of use that the EPS signals every LKA drop and the PCM every ACC non-execution, verified by forced-fault vehicle tests; a response-against-command check is revisited if a test finds a silent drop. The safety-concept session writes the assumption with TSR-626; WP-A-04 v1.11 MCS-02.10, MCS-06.11 |
| F-33 | SG-02 and SG-06 now carry performance-limit branches (G2.8 curve too tight for the limit, G6.9 lead missed or late) whose only warning comes from the same SoC | WP-A-04 §4, §7; WP-C-06 | **Resolved 2026-10-18 (DQ-361 A):** the branches stay in SG-02 and SG-06, as SG-04 keeps false braking; SOTIF (WP-C-06) evaluates the rates, and the safety case argues MCS-02.12 and MCS-06.10 as single points (WP-A-04 v1.11) |
| F-34 | Acceleration while not engaged or after a brake (TE-03, G3.3) has no rated SG-03 hazardous event: HZ-010 (unintended engagement) routes only to the steering event HE-01.4 | WP-C-03, hara-mapping.yaml | **Resolved 2026-10-19 (DQ-364 A, WP-A-04 v1.12).** WP-C-03 v0.5 adds HE-03.7 (acceleration while not engaged or just after a brake press, ASIL B) and routes HZ-010 to it, so G3.3 is a rated SG-03 event. The three tree gaps it opened are closed: BE-1.25 joins G3.3.1 (SWF-055, SWF-089; MCS-03.9) and SWF-057 joins BE-3.13. SG-03 now has 23 computed cut sets, all covered |
| F-35 | Modes justified outside the new trees: SG-02 and SG-06 PFM-015 (driver not briefed: a condition of use, AOU-06); SG-03 the four QM host monitors and four release modes (as F-16); SG-05 SWF-031 (host release on brake, QM) | — | **Justified** in `not_in_fta`. Same review as F-16 |
| F-36 | Points for the reviewer, no change made: BE-2.02 and BE-2.06 group causes of several classes under one event; SFM-017/SFM-019 list only host causes; SFM-010.C2/C3 (braking needed beyond the ACC bound, OEM brake fault) are not drawn; HE-07.3 after a disengagement is covered through BE-6.06 rather than its own branch | WP-A-04 §4, §7; System FMEA | **Open, for review** |

| F-37 | Five SG-08 events have no FMEA mode: BE-8.03 (driver camera or IR degraded, or `dmonitoringmodeld` stopped: no DFMEA or FMEDA, only SFM-022.C3), BE-8.04 (`driverStateV2` always valid at the source, GAP-21), BE-8.05 (wheel-touch reset on any input, GAP-21), BE-8.06 (DM demo mode, GAP-20), BE-8.08 (forced stop not set or not acted on). The G-HMI modes SFM-026, SFM-027 and SWF-035 reach SG-08 but cite no HZ-013 | SW FMEA, DFMEA, System FMEA | **SW part resolved:** SW FMEA rev 0.9 backs BE-8.04 (SWF-063) and BE-8.05 (SWF-061); rev 1.1 backs BE-8.06 (SWF-085) and BE-8.08 (SWF-086). **Open, for the FMEA owners:** a DFMEA scope decision for the driver camera, and ~~HZ-013 effects on the System FMEA's HMI modes SFM-026 and SFM-027~~ (resolved: System FMEA rev 0.20 adds them). SWF-035 and SWF-082 cite HZ-013 since SW FMEA rev 1.1 |
| F-38 | The records of the no-response reaction disagree with the code and with each other. In the code, about 5 s after alert level 3 `noResponseForceDecel` makes the planner stop the vehicle in lane (`policy.py:454`, `controlsd.py:236`, `longitudinal_planner.py:84`), but the item stays engaged: the level-3 alerts are `ET.PERMANENT` only, and the lockout starts only after a disengagement. SFM-025 says there is no reaction at all and does not credit the stop. TSR-611 is marked implemented for "decelerate, disengage and lock out", but disengagement is not implemented. The SG-08 safe state is not defined (WP-C-03 OI-10, SFM-ACT-005) | System FMEA, SW FMEA, WP-C-01 | **Safe state decided 2026-10-16, DQ-365 A** (stop in lane, stay stopped and held, re-engagement locked out until the driver responds; FSR-02.09, TSR-633, recorded in WP-C-04 v0.10 and WP-S-02). Applied in WP-A-04 v1.6: G8.3 now ends at the safe state, with BE-8.10 (no hold or lockout after the stop, present by design until TSR-633 is implemented) and UE-8.11 (PCM standstill hold under ACC); the SWF-062 tree gap is closed. **Open, for the System FMEA owner:** credit the forced stop in SFM-025 (SFM-ACT-005). **For the SW FMEA owner:** SWF-062.C1 still says the safe state is queued (DQ-220). The PCM standstill hold (UE-8.11) is now AOU-16 in WP-C-01, to be verified by the DQ-365 A vehicle test |

| F-39 | BE-8.06 and MCS-08.4 said the DM demo mode switches monitoring off. By code reading it does not: `run_step(demo=True)` runs the policy on a synthetic vehicle state (fixed speed, always engaged, zero calibration, no wheel-touch reset, strict thresholds), and `_update_states` drops the monitored-seat lock while engaged (`policy.py:286-291`, `431-440`). Alerts are more frequent, not absent, but the pose is judged without the mount calibration and the wrong seat can be watched (reported by the SW FMEA session, SWF-085) | WP-A-04 §13 | **Resolved 2026-10-16 (v1.5):** BE-8.06 text and MCS-08.4 corrected; still a single point. SWF-085 (SW FMEA rev 1.1, #146) now cited on BE-8.06 |

## 4. Next

1. Review the SG-04 links, the F-1…F-10 resolutions and the new FMEA rows (SWF-050…053, SWF-003.C3, DFM-019); F-3 decided 2026-10-14 (DQ-002).
2. Review the SG-01 links and F-11…F-13 (WP-A-04 v1.0). The FMEA owners decide F-14 and F-15.
3. Review the SG-07 links and the re-based tree (WP-A-04 v1.1). The FMEA owners decide F-17…F-19. DQ-209 was answered on 2026-10-16 (option A: keep comma's box and bench-test it). WP-A-04 v1.4 applies it without changing the tree: readback is not pursued, so MCS-07.8 stays undetected, and the bench tests VS-HW-22…24 decide BE-7.16 and BE-7.17.
4. Review the SG-02, SG-03, SG-05 and SG-06 links and the v1.2 tree changes. The FMEA owners decide F-25…F-28 and F-31; the lead DQ-360…DQ-364. Review the SG-08 tree (WP-A-04 §13) and its mapping; DQ-365 is decided (A, applied in WP-A-04 v1.6), and the FSC decides how SG-08's ASIL A is met on the QM DM chain (SPF-18).
5. ~~Retire the System FMEA table of WP-A-04 §10 in favour of [system-fmea.yaml](fmea/analyses/system-fmea.yaml), so the map has one System FMEA to point at.~~ **Done 2026-10-25 (DQ-127 A, WP-A-04 v1.19):** the map points at [system-fmea.yaml](fmea/analyses/system-fmea.yaml) only. WP-A-04 §10 keeps the old-to-new ID map; System FMEA rev 0.34 adds the rows that had no equivalent.

## 5. Hand-off sheets

One sheet per goal, continued where a tree is long. Each opens with the goal's single points: the events in the item that reach the top event on their own, from the gate logic, with the detection range of their FMEA causes. A single point whose causes all claim D ≤ 4 is marked, because the tree and the FMEA then disagree on detection (the third check of §1); today that is BE-3.11, BE-5.14 and BE-7.05, as `fmea_lint.py` warns. Then every event of the tree, borrowed events included, grouped under the gate it feeds: the event, the FMEA failure mode it hands off to, the worst of that mode's causes (highest AP, then highest D) and the detection that cause credits. An event with no FMEA row says why.

### SG-01

![Figure 3-SG-01-1: SG-01 hand-off sheet 1 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-01-1.svg)

![Figure 3-SG-01-2: SG-01 hand-off sheet 2 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-01-2.svg)

### SG-02

![Figure 3-SG-02-1: SG-02 hand-off sheet 1 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-02-1.svg)

![Figure 3-SG-02-2: SG-02 hand-off sheet 2 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-02-2.svg)

### SG-03

![Figure 3-SG-03-1: SG-03 hand-off sheet 1 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-03-1.svg)

![Figure 3-SG-03-2: SG-03 hand-off sheet 2 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-03-2.svg)

### SG-04

![Figure 3-SG-04-1: SG-04 hand-off sheet 1 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-04-1.svg)

![Figure 3-SG-04-2: SG-04 hand-off sheet 2 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-04-2.svg)

### SG-05

![Figure 3-SG-05-1: SG-05 hand-off sheet, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-05-1.svg)

### SG-06

![Figure 3-SG-06-1: SG-06 hand-off sheet 1 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-06-1.svg)

![Figure 3-SG-06-2: SG-06 hand-off sheet 2 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-06-2.svg)

### SG-07

![Figure 3-SG-07-1: SG-07 hand-off sheet 1 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-07-1.svg)

![Figure 3-SG-07-2: SG-07 hand-off sheet 2 of 2, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-07-2.svg)

### SG-08

![Figure 3-SG-08-1: SG-08 hand-off sheet, each event of the fault tree with the FMEA failure mode, worst cause and detection behind it](figures/fig-map-3-sg-08-1.svg)
