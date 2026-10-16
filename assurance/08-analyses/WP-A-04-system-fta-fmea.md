# WP-A-04 System-Level Safety Analyses (FTA, FMEA)

| Field | Value |
|---|---|
| Work product | WP-A-04 System-level safety analyses (FTA, FMEA) |
| Standard reference | ISO 26262-9:2018 §8 (safety analyses); ISO 26262-4:2018 §6 (safety analysis of the system architectural design, to support the TSC); ISO 21448:2022 §7 (input on insufficiencies, informative here); ASPICE 4.0 SYS.3 |
| Version | 1.5 (§13 BE-8.06 and MCS-08.4 corrected: DM demo mode does not switch monitoring off; it runs the policy on a synthetic vehicle state without the mount calibration and the monitored-seat lock (finding passed on from the SW FMEA, SWF-085); cut sets unchanged; 2026-10-16). 1.4 (§8 SG-07 events, cut sets and SPF-07/SPF-15 updated for the lead's decision to keep comma's harness box and bench-test it (DQ-209 option A, 2026-10-16): readback not pursued, so the stuck-switch cut set MCS-07.8 stays undetected; bench tests VS-HW-22…24 decide BE-7.16 and BE-7.17; the SG-009 metric shortfall is an accepted deviation (DQ-320). Tree structure and cut sets unchanged; 2026-10-16). 1.3 (§13 new fault tree for SG-08, the unresponsive-driver goal of WP-C-03 v0.4 (ASIL A): DM model miss [SOTIF], wrong thresholds, degraded camera never flagged invalid or reset by any input, demo mode, slow or undelivered escalation, forced stop not set or not executed; 11 cut sets, all single points, all covered; SPF-18; mapped (F-37, F-38; DQ-365 queued); 2026-10-16). 1.2 (FTA↔FMEA mapping of SG-02, SG-03, SG-05 and SG-06, findings F-20…F-36 of [fta-fmea-mapping.md](fta-fmea-mapping.md); 2026-10-16. §3 SG-03: G-LENV now defined here (the longitudinal check replaces the lateral G-ENV, F-1 carried over), BE-1.05 in new G3.1.1.b, step within the bound moved to new G3.6 with the host step BE-4.17, new G3.7 stock ACC and item `0x343` together; MCS-03.3, -03.8 revised, MCS-03.12 added; 22 cut sets. §4 SG-02: diagnostics reset the EPS (G2.1.2, BE-2.20 with BE-7.20), silent EPS drop UE-2.19, masked take-over alert BE-2.25, latent siren path BE-2.22, BE-1.20 in G2.3.1, selfdrived crash with the heartbeat kept (G2.5.1, BE-2.21), new G2.8 insufficient lateral control (BE-2.23 [SOTIF], BE-2.24); MCS-02.1, -02.3, -02.6 extended, MCS-02.9…02.12 added; 100 cut sets. §6 SG-05: envelope brake-edge defect BE-5.14, cruise-revocation defect BE-5.15, mode/firmware/debug-build bypass BE-1.08, BE-1.09, BE-1.18; BE-5.06 latent below 500 units of driver torque; BL-005 note on BE-5.10; MCS-05.5 restated, MCS-05.9…05.11 added; 12 cut sets. §7 SG-06: BE-1.20 in G6.1.1, silent PCM non-execution UE-6.08 (G6.3.1), G6.6.1 with BE-2.21, new G6.8 supply loss, new G6.9 lead missed or late (BE-6.09 [SOTIF], BE-6.10); MCS-06.1, -06.3, -06.5, -06.8 extended, MCS-06.9…06.11 added; 85 cut sets. SPF-15 unchanged; SPF-16 and SPF-17 added; every computed cut set of every goal covered). 1.1 (§8 SG-07 tree re-based on the harness box as built, [RR-2026-010](../04-hardware/reviews/RR-2026-010.md): the intercept element is two powered DG419LE analog switches, not a relay. G7.3 split by cause: switch stuck in intercept BE-7.09, SBU1 stuck high BE-7.15, pull-down open BE-7.16 (latent; DFM-010.C1…C3); G7.4 adds box supply lost BE-7.17 (DFM-020, new SPF-15), clamp diode short BE-7.18 (DFM-021) and car-side bus held dominant BE-7.19 (DFM-008); new G7.6 diagnostics to the stock ADAS ECU (BE-7.20, BE-7.21; SWF-015), found by the SG-07 FTA↔FMEA mapping; MCS-07.8, -07.11 and SPF-07 revised for DQ-064 and DQ-209, MCS-07.12…07.16 added; 17 computed cut sets, 16 rows, all covered; 2026-10-16). 1.0 (§2 SG-01 tree and §2.1 cut sets corrected from the SG-01 FTA↔FMEA mapping, findings F-11…F-13 of [fta-fmea-mapping.md](fta-fmea-mapping.md): G1.2.1.a adds the envelope's own not-allowed check defect BE-1.25 and the mode, param or firmware bypass BE-1.08/BE-1.09; G-SoC adds BE-1.24 (command corrupted on the SPI link); new G1.4 (stock LKA and item `0x2E4` together) with BE-1.26 and the SG-04 events BE-4.19, BE-4.21; MCS-01.6, -01.7 extended, MCS-01.10 and -01.11 added; 36 computed cut sets, 11 rows, all covered; 2026-10-16). 0.9 (§5 SG-04 tree and §5.1 cut sets corrected from the FTA↔FMEA pilot findings F-1, F-5…F-8: own longitudinal envelope gate G-LENV with BE-4.16; G4.2 needs the host step BE-4.17; G4.3.1 adds stale or replayed braking BE-4.18; new G4.8 (stock ACC and item 0x343 together) and G4.9 (braking during accelerator override); MCS-04.3, -04.4, -04.9 revised, MCS-04.11 and -04.12 added; SPF-14 extended to SG-04; 21 computed cut sets, 12 rows, all match; 2026-10-13). 0.8 (§11: basic events linked to the FMEAs, SG-04 pilot, [fta-fmea-mapping.md](fta-fmea-mapping.md); 2026-10-13). 0.7 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.6 (2026-10-12 reference-build status notes, drafted on a parallel branch as 0.4, re-applied to the 0.5 trees: G5.2.1 with UE-5.13 and MCS-05.8 for BE-5.12 (found by `fta_cutsets.py`: BE-5.12 under the G5.2 OR was a single-event cut set), BE-1.16, BE-1.22 (incl. TSR-408), BE-2.08, BE-2.14, MCS-01.8, MCS-02.1, Obs-01; BE-5.12, cut sets and SFMEA notes kept; 2026-10-13). 0.5 (trees restructured to resolve CS-01…CS-07: SG-01 G1.2.2/G1.3.2, SG-03 G3.3, SG-02 and SG-06 per cause; tables completed; SPF-14; OI-9 closed, OI-10; 2026-10-12). 0.4 (§9.1 computed minimal cut sets and findings CS-01…CS-07; BE-2.14 tagged latent at the baseline, as §4 states; fault tree diagrams in [fta/](fta/README.md); OI-9; 2026-10-12). 0.3 (SPF-09 and SPF-13 addressed at requirement level: TSR-516 trigger set, TSR-303, TSR-711; SG-07 FTTI; 2026-10-12) |
| Status | Draft |
| ASIL / scope | Fault trees for SG-01…SG-08: SG-01 (ASIL C ⚠), SG-02 and SG-06 (ASIL C), SG-03 (ASIL C ⚠, D if AOU-03/05 fail), SG-04, SG-05, SG-07 (ASIL B), as of WP-C-03 v0.4. SG-08 (ASIL A, unresponsive driver, WP-C-03 v0.4) in §13 since v1.3. System FMEA covering SG-01…SG-07. Qualitative only |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `bf6ce8c` (status update 2026-10-12; opendbc `7993399`, panda `b790fca`). Trees, cut sets and FMEA were derived at `8b8c6ae` (opendbc `229dc70`, panda `92eb565`); events and cells describe that baseline unless a dated note ("2026-10-12") says otherwise |

## 1. Purpose and scope

This document provides the system-level deductive (FTA) and inductive (FMEA) safety analyses that ISO 26262-4 §6 asks for to support the technical safety concept. It works on the architecture of [WP-C-01](../02-concept/WP-C-01-item-definition.md) §3 and [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §2 as built at the baseline, so that it shows **where the inherited design has single points of failure today**. When [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) defines the target architecture, this analysis is repeated on it (OI-1).

- Qualitative only. Quantitative evaluation of random hardware failures belongs to [WP-H-04](../04-hardware/WP-H-04-hardware-metrics.md) and [WP-H-05](../04-hardware/WP-H-05-random-hardware-failures-pmhf.md).
- Functional insufficiencies of the ML stack (SOTIF) appear as basic events labelled **[SOTIF]** so the trees are complete. They are evaluated in [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), not here.
- Dependent failures (common cause) are marked **[CCF → DFI-nn]** and refer to [WP-A-03](WP-A-03-dependent-failure-analysis.md). Interference from QM elements is marked **[FFI → id]** and refers to [WP-A-02](WP-A-02-coexistence-freedom-from-interference.md).
- TSR references are to [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (Draft v0.3); where no TSR covers a measure this is stated.
- Basic events are reused across trees by ID (e.g. BE-1.13 in SG-03, SG-04 and SG-05). The fault trees use the block diagram of the FSC completeness check ([WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §14) as a check that every node is considered for every goal.

Diagrams: every tree below is also drawn as a conventional fault tree (IEC 61025 symbols) in [fta/](fta/README.md). The diagrams are generated from the text trees in this document by `fta/fta_diagrams.py`, and CI fails if they are out of date; the text stays the analysis of record.

Notation: `[OR]`, `[AND]` gates; `BE-` basic event; `UE-` undeveloped event (outside the item or analysed elsewhere); `(SPF)` marks an event that alone leads to the top event in the baseline design.

## 2. FTA — SG-01: uncontrollable lateral motion, or steering actuation while not engaged

Diagram: [SG-01 sheet 1](fta/fta-SG-01-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-01**: LKA torque applied at the steering wheel that exceeds what the driver can control, or any LKA torque while the item is not engaged.

```
TE-01 Uncontrollable lateral motion / torque while not engaged                          [OR]
├── G1.1 Torque above the controllable bound reaches the wheel while engaged            [AND]
│   ├── G1.1.1 Command above controllable bound transmitted on bus 0 (0x2E4)           [OR]
│   │   ├── BE-1.01 Envelope torque limits set above the controllable bound
│   │   │          (raw 1500/15/25/450 not derived, GAP-04; identical in controller,
│   │   │          CCF → DFI-08)                                                        (SPF, systematic)
│   │   ├── G1.1.1.a SoC commands excessive torque AND envelope fails to clamp          [AND]
│   │   │   ├── G-SoC SoC command excessive or wrong                                    [OR]
│   │   │   │   ├── BE-1.02 controlsd/card software fault (QM)
│   │   │   │   ├── BE-1.03 Wrong desired curvature from model                     [SOTIF]
│   │   │   │   ├── BE-1.04 Debug/maneuver process replaces controller
│   │   │   │   │          (process_config.py:34-47, GAP-20)
│   │   │   │   ├── BE-1.05 Wrong CarParams / fingerprint (CCF → DFI-09)
│   │   │   │   └── BE-1.24 Command corrupted on the SoC-to-MCU SPI link and accepted:
│   │   │   │              both checks are 8-bit XOR over the same bytes, no counter
│   │   │   │              (spi.cc:189-202, panda.cc:284-290)                  (random HW)
│   │   │   └── G-ENV Envelope does not clamp                                           [OR]
│   │   │       ├── BE-1.06 Envelope software defect in lateral checks (lateral.h:60-151)
│   │   │       ├── BE-1.07 MCU execution fault (RAM/register/CPU) corrupts limit or
│   │   │       │          check, not detected (no MPU, no ECC handling, faults
│   │   │       │          report-only; GAP-08)
│   │   │       ├── BE-1.08 Safety mode/param changed by SoC (0xdc, GAP-09)
│   │   │       │          [FFI → FFI-CM-06; CCF → DFI-13: same SoC fault can cause
│   │   │       │          G-SoC and BE-1.08]
│   │   │       └── BE-1.09 Envelope firmware replaced via boot pins / softloader
│   │   │                  (GAP-38, GAP-24) [FFI → FFI-CM-12; CCF → DFI-13]
│   │   └── BE-1.10 Frame corrupted after safety_tx_hook in a part not covered by
│   │              the packet XOR: copy into FDCAN message RAM, message RAM itself,
│   │              FDCAN core, transceiver (the 8-bit XOR checked before loading,
│   │              fdcan.h:100, covers only the software TX queue)                      (SPF, random HW)
│   └── UE-1.11 EPS does not limit LKA torque to an overpowerable level (AOU-01R fails)
├── G1.2 Torque while not engaged                                                       [OR]
│   ├── G1.2.1 Authority falsely granted AND SoC commands torque                       [AND]
│   │   ├── G1.2.1.a False authority                                                    [OR]
│   │   │   ├── BE-1.12 Corrupted/replayed 0x1D2 creates false cruise rising edge with
│   │   │   │          valid 8-bit checksum (no counter, GAP-01)
│   │   │   ├── BE-1.13 Panda RX path delivers stale/stuck cruise frame to both
│   │   │   │          envelope and SoC (single RX path; CCF → DFI-10)
│   │   │   ├── BE-1.14 MCU fault sets controls_allowed (BE-1.07 class)
│   │   │   ├── BE-1.25 Envelope software defect in the not-allowed torque check or the
│   │   │   │          controls_allowed bookkeeping (lateral.h:111-114)
│   │   │   └── BE-1.08, BE-1.09 (mode or param change, or envelope replaced, removes the
│   │   │              not-allowed check; as G-ENV)
│   │   └── BE-1.15 SoC commands non-zero torque (normally gated by its own engagement
│   │              state, which is fed by the same CAN data — CCF → DFI-10)
│   ├── G1.2.2 Authority not revoked after the driver disengages AND SoC keeps commanding [AND]
│   │   ├── G1.2.2.a Disengagement not seen by the envelope                              [OR]
│   │   │   ├── BE-1.16 Brake 0x226 lost/stuck "not pressed" (no checksum, no counter,
│   │   │   │          timeout ≈2 s; GAP-01, GAP-06). 2026-10-12: loss detected
│   │   │   │          ≤ 0.16 s (5 periods, 100 Hz; WP-S-04 T-01); stuck undetected
│   │   │   └── BE-1.17 0x1D2 stuck "cruise active" with valid checksum (GAP-01)
│   │   └── BE-1.15 (the SoC reads the same frames, so it keeps commanding; CCF → DFI-10)
│   └── BE-1.18 Envelope bypass: ALLOUTPUT/debug mode in a DEBUG build
│              (panda/SConscript:12-20, GAP-25)                                         (SPF, config)
├── G1.3 Stale or frozen torque held beyond FTTI (HE-02.3)                              [AND]
│   ├── G1.3.1 SoC stops updating but link stays alive                                 [OR]
│   │   ├── BE-1.19 controlsd hang / stale modelV2 used up to ≈3.5 s (GAP-16)
│   │   ├── BE-1.20 Diagnostics masked during big-model fallback (GAP-17; E-06 excluded
│   │   │          from reference configuration)
│   │   └── BE-1.21 SoC replays an old command buffer (no sequence counter, GAP-10)
│   └── G1.3.2 Envelope does not remove torque within ≤ 0.5 s                          [AND]
│       ├── BE-1.22 Command freshness not supervised: heartbeat shows pandad liveness
│       │          only; mismatch 3 s, loss 5 s (main.c:182-213; GAP-06, GAP-10)
│       │          (latent, baseline). 2026-10-12, reference build: heartbeat loss
│       │          revokes at 0.3 s (TSR-407); actuation-frame arrival supervised
│       │          (TSR-408, opendbc 273f44e); value freshness (TSR-409) open
│       └── BE-1.23 Rate and RT limits accept a constant in-limit value (by design)
└── G1.4 Stock LKA and item 0x2E4 on the car bus together while engaged                 [AND]
    ├── G1.4.1 Stock camera STEERING_LKA reaches the car side                           [OR]
    │   ├── BE-4.19 (relay stays released; as SG-04)
    │   └── BE-1.26 Stock 0x2E4 forwarded from the camera side while the item
    │              transmits (check_relay entry or forwarding hook defect)
    └── BE-4.21 (relay malfunction detected after 1–2 s or not at all; as SG-04)
```

### 2.1 SG-01 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-01.1 | 1 + ext. | {BE-1.01, UE-1.11} | A wrong envelope limit is itself the failure; only the EPS (unverified) stands behind it. **Systematic single point** |
| MCS-01.2 | 1 + ext. | {BE-1.10, UE-1.11} | Random corruption after the TX hook, beyond the software queue. No second check on the item side. **Random single point** |
| MCS-01.3 | 1 (effective, DFI-13) | {BE-1.02 or BE-1.04, BE-1.08 or BE-1.09, UE-1.11} (one SoC fault that both commands torque and changes mode/param or reflashes the MCU) | Dual-point in form, single-point in cause (DFI-13) |
| MCS-01.4 | 1 (effective) | {BE-1.13} | One stuck RX path feeds envelope and SoC; both "agree" the system is engaged (DFI-10) |
| MCS-01.5 | 1 | {BE-1.18} | Configuration single point: a debug build has no envelope. Controlled only by the release process ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) |
| MCS-01.6 | 2 + ext. | {BE-1.02 or BE-1.03 or BE-1.04 or BE-1.05 or BE-1.24, BE-1.06 or BE-1.07 or BE-1.08 or BE-1.09, UE-1.11} | True dual-point: the intended envelope pattern (BE-1.05 may also set the envelope parameter, DFI-09; BE-1.02/BE-1.04 with BE-1.08/BE-1.09 can share one cause, MCS-01.3). Requires BE-1.07 to be detected (latent-fault coverage, IWDG, ECC) to stay dual. v1.0: BE-1.24 (command corrupted on the SPI link, DFM-015, SWF-026) is a further way for a wrong command to reach the envelope, which still clamps it |
| MCS-01.7 | 2 | {BE-1.12 or BE-1.14 or BE-1.25, BE-1.15} | Needs counters on `0x1D2` or a plausibility check (TSR-403…TSR-405) to remove. v1.0: BE-1.25, a defect in the not-allowed torque check itself (SWF-002), is the software way to the same pair; verified by the opendbc safety tests |
| MCS-01.8 | 2 (effective 1 + latent at the baseline) | {BE-1.19 or BE-1.20 or BE-1.21, BE-1.22} | Removed only when the command-freshness timeout fits the FTTI (TSR-407…TSR-409, TSR-411). At the baseline nothing supervises command freshness (BE-1.22) and the value checks cannot see a stale in-limit value (BE-1.23, by design), so a stale SoC command alone holds torque (SPF-14). 2026-10-12, reference build: heartbeat loss revokes at 0.3 s (TSR-407) and actuation-frame arrival is supervised (TSR-408, opendbc `273f44e`); a frozen in-limit value with frames still arriving remains (TSR-409, TSR-411) |
| MCS-01.9 | 2 (effective 1 through DFI-10) | {BE-1.16 or BE-1.17, BE-1.15} | Brake or cruise-inactive not seen by the envelope; the SoC reads the same frames and keeps commanding. SPF-04; TSR-401…TSR-406 |
| MCS-01.10 | 2 (effective 1 through DFI-13) | {BE-1.08 or BE-1.09, BE-1.15} | A mode or param change, or replaced firmware, removes the not-allowed check while the SoC commands torque; one SoC fault can do both (DFI-13). Lateral case of MCS-04.10 (v1.0). TSR-511…TSR-514 |
| MCS-01.11 | 2 | {BE-4.19 or BE-1.26, BE-4.21} | Stock STEERING_LKA and the item's `0x2E4` combine on the car bus: the lateral case of MCS-04.11 (v1.0). The relay-malfunction check acts only after 1–2 s, so the commands combine until then. TSR-506 (relay readback), GAP-12 |

## 3. FTA — SG-03: unintended acceleration

Diagram: [SG-03 sheet 1](fta/fta-SG-03-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-03**: vehicle acceleration that the driver did not intend (positive acceleration request executed beyond the intended value, while not engaged, or after the driver brakes).

```
TE-03 Unintended acceleration                                                           [OR]
├── G3.1 Positive acceleration above controllable bound executed while engaged          [AND]
│   ├── G3.1.1 0x343 ACC_CONTROL accel above controllable bound on bus 0               [OR]
│   │   ├── BE-3.01 Envelope accel upper bound (+2.0 m/s², toyota.h:208) above the
│   │   │          controllable value; RAISED_ACCEL_LIMIT not validated for Corolla
│   │   │          (toyota/interface.py:117-118; GAP-04; CCF → DFI-08)             (SPF, systematic)
│   │   ├── G3.1.1.a SoC excessive accel AND envelope fails to clamp                  [AND]
│   │   │   ├── G3.1.1.b SoC commands excessive acceleration                            [OR]
│   │   │   │   ├── BE-3.02 Planner/controller fault, wrong lead, e2e accel [SOTIF]/QM
│   │   │   │   └── BE-1.05 (wrong CarParams / fingerprint; as SG-01)       [CCF → DFI-09]
│   │   │   └── G-LENV Longitudinal envelope does not clamp                             [OR]
│   │   │       ├── BE-4.16 Envelope software defect in the longitudinal checks
│   │   │       │          (longitudinal_accel_checks, longitudinal.h:8-12)
│   │   │       └── BE-1.07, BE-1.08, BE-1.09 (MCU fault, mode/param change, envelope
│   │   │                  replaced; as SG-01)
│   │   └── BE-3.04 Frame corrupted after TX hook (as BE-1.10)                          (SPF, random HW)
│   └── UE-3.05 PCM executes request without its own bound (AOU-05R fails)
├── G3.6 Acceleration step within the bound                                            [AND]
│   ├── BE-4.17 Host sends a step: the CarController jerk limit is applied before
│   │          pitch compensation and the PID (carcontroller.py:197-238)
│   ├── BE-3.03 No jerk limit in envelope: step to +2.0 m/s² allowed (GAP-04,
│   │          FSR-03.03 not implemented)
│   └── UE-3.05
├── G3.2 In-bound but unintended positive acceleration (e.g. toward a stationary lead)  [AND]
│   ├── BE-3.06 SoC requests positive accel in a closing situation [SOTIF]/QM
│   ├── BE-3.07 Envelope passes any in-bound value while authority is granted (by design)
│   └── UE-3.08 Driver does not brake in time (controllability; AOU-06R)
├── G3.3 Acceleration while not engaged or after driver brake                           [AND]
│   ├── G3.3.1 Inactive-value check not effective                                      [OR]
│   │   ├── BE-1.12, BE-1.13, BE-1.14 (false authority, as SG-01)
│   │   ├── BE-3.09 Brake 0x226 not detected (no checksum/counter, GAP-01) AND PCM does
│   │   │          not cancel ACC on brake (AOU-03R)                                   [AND]
│   │   └── BE-3.10 Inactive value check bypassed by mode/param change (e.g. param that
│   │              selects another brake signal or stock-longitudinal branch, toyota.h:216-248)
│   │              [FFI → FFI-CM-06]
│   └── BE-3.13 SoC sends a positive acceleration while not engaged (QM; its engagement
│              state is fed by the same CAN data)                     [CCF → DFI-10]
├── G3.4 Gas override misinterpreted                                                    [AND]
│   ├── BE-3.11 Gas-pressed signal (PCM_CRUISE.GAS_RELEASED) stuck "pressed": envelope
│   │          then allows only inactive accel (safe direction) — or stuck "released"
│   │          while the driver presses: envelope allows accel (longitudinal.h:3-5)
│   └── UE-3.12 PCM adds item accel on top of driver pedal (to verify, AOU-05R)
├── G3.5 Stale positive acceleration held beyond FTTI                                   [AND]
│   ├── BE-1.19 / BE-1.21 (stale SoC command)
│   └── BE-1.22 (slow envelope detection)
└── G3.7 Stock ACC and item 0x343 on the car bus together while engaged                 [AND]
    ├── G3.7.1 Stock camera ACC_CONTROL reaches the car side                            [OR]
    │   ├── BE-4.19 (relay stays released; as SG-04)
    │   └── BE-4.20 (stock 0x343 forwarded while the item transmits; as SG-04)
    └── BE-4.21 (relay malfunction detected after 1–2 s or not at all; as SG-04)
```

### 3.1 SG-03 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-03.1 | 1 + ext. | {BE-3.01, UE-3.05} | Systematic single point; bound selection |
| MCS-03.2 | 1 + ext. | {BE-3.04, UE-3.05} | Random single point after TX hook |
| MCS-03.3 | 2 + ext. | {BE-4.17, BE-3.03, UE-3.05} | Step acceleration within the bound: the host sends a step (jerk limit applied before pitch compensation and the PID, SWF-046.C1) and the envelope has no jerk limit (SWF-004.C1). As MCS-04.3: the host step is a design property, so the envelope limit is the barrier that is missing. TSR-205 (GAP-04), TSR-605 |
| MCS-03.4 | 2 + driver | {BE-3.06, BE-3.07, UE-3.08} | By design; managed by SOTIF and controllability of the bound |
| MCS-03.5 | 1 (effective, DFI-13) | {BE-3.02, BE-1.08 or BE-1.09, UE-3.05} (one SoC fault → command + mode/param change) | DFI-13 |
| MCS-03.6 | 2 (BE-3.09 is two conditions; BE-3.13 effective through DFI-10) | {BE-3.09, BE-3.13} (BE-3.09 = {`0x226` undetected, PCM no cancel}) | Item side has no independent brake signal |
| MCS-03.7 | 2 (effective 1 + latent at the baseline) | {BE-1.19/1.21, BE-1.22} | Freshness timing; SPF-14 |
| MCS-03.8 | 2 + ext. | {BE-3.02 or BE-1.05, BE-4.16 or BE-1.07 or BE-1.08 or BE-1.09, UE-3.05} | Intended envelope pattern, as MCS-04.9, with the longitudinal check defect BE-4.16 in place of the lateral BE-1.06 (F-1). BE-1.05 (wrong CarParams, SFM-032, PFM-013) may also set the envelope parameter (DFI-09), as MCS-01.6; the pairs of BE-3.02 with BE-1.08/BE-1.09 are MCS-03.5 (DFI-13) |
| MCS-03.9 | 2 (effective 1 through DFI-10 for BE-1.13) | {BE-1.12 or BE-1.13 or BE-1.14, BE-3.13} | False authority, as MCS-01.4/01.7 and MCS-04.7 |
| MCS-03.10 | 2 | {BE-3.10, BE-3.13} | Mode or param change bypasses the inactive-value check, as MCS-04.10. TSR-513 |
| MCS-03.11 | 1 + ext. | {BE-3.11, UE-3.12} | Single gas signal, no plausibility (as MCS-05.6); AOU-05R |
| MCS-03.12 | 2 | {BE-4.19 or BE-4.20, BE-4.21} | Stock ACC_CONTROL and the item's `0x343` combine on the car bus: the acceleration case of MCS-04.11 and MCS-01.11 (v1.2). The stock ACC may request acceleration (resume towards its set speed) while the item does not. TSR-506 (readback), GAP-12 |

## 4. FTA — SG-02: loss or degradation of lateral control without adequate take-over warning

Diagram: [SG-02 sheet 1](fta/fta-SG-02-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-02**: lateral control is lost or degraded while the item is engaged, and the driver gets no perceivable take-over request within the SG-02 budget (≤ 1 s to warning, [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §3).

The tree has one branch per cause of the loss (v0.5, §9.1 CS-05). Each branch needs the cause, the failure of the SoC warning *for that cause* (QM), and the failure of the SoC-independent cues (panda siren, TSR-516; cluster cruise indicator, TSR-309). The cues fail only if both the siren and the cluster fail (G-LATCUE is an AND). For most lateral losses the cues are always absent at the baseline: the siren fires only on heartbeat loss or an envelope-detected RX or platform fault, and the cluster cruise state does not change when lateral control alone is lost. BE-2.14 and BE-2.16 are therefore tagged latent, and those paths reduce to the SoC alone (SPF-09). A SoC crash (G2.5) and a loss of supply (G2.7) remove the SoC warning together with control.

```
TE-02 Loss of lateral control without take-over request within ≤ 1 s                  [OR]
├── G2.1 EPS drops LKA assistance and no adequate take-over request                     [AND]
│   ├── G2.1.0 EPS drops LKA assistance                                                 [OR]
│   │   ├── BE-2.01 EPS drops LKA assistance (LKA fault state in 0x262)              (UE: EPS internal)
│   │   └── G2.1.2 Item diagnostics reset the EPS or open a session on it               [AND]
│   │       ├── BE-7.20 (diagnostic TX hook passes any ISO 15765 frame; as SG-07)
│   │       └── BE-2.20 SoC sends a diagnostic request that resets the EPS or opens a
│   │                  session on it while engaged (QM fault)          [FFI → FFI-CM-09]
│   ├── G2.1.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.08 EPS fault seen only by the host, with 1.5 s hysteresis
│   │   │          (car_events.py; not in the envelope, GAP-03). 2026-10-12, reference
│   │   │          build: envelope refuses LKA torque on a fault code and reports
│   │   │          epsFault (TSR-110); the SoC warning keeps the host hysteresis
│   │   ├── UE-2.19 EPS stops accepting LKA requests without a fault state in 0x262:
│   │   │          neither the host nor the envelope sees it; no check of EPS
│   │   │          acceptance against the command (SFM-005.C1; TSR-626, WP-A-03 OI-8)
│   │   └── G-HMI HMI does not deliver the warning                                      [OR]
│   │       ├── BE-2.12 HMI hang: render loop or audio stream stalled while processes
│   │       │          stay alive (processNotRunning covers crashes only)  [CCF → DFI-25]
│   │       ├── BE-2.13 Alert volume not audible (no defined minimum; FFI-CM-18)
│   │       └── BE-2.25 Take-over alert masked by an alert of higher priority but lower
│   │                  urgency (SoftDisableAlert is Priority.MID; alertmanager.py:63)
│   └── G-LATCUE SoC-independent cue missing or late (lateral loss)                     [AND]
│       ├── G-SIREN Siren missing or late                                               [OR]
│       │   ├── BE-2.14 Siren not triggered: at the baseline only on heartbeat loss (after
│       │   │          5 s, for 3 s; main.c:193-205). TSR-516 v0.3 adds every envelope
│       │   │          revocation that is not a driver action (incl. EPS fault, TSR-110)
│       │   │          and a fault-induced disengagement whose ACC cancel had no effect
│       │   │          (latent, baseline). 2026-10-12: siren on an EPS fault persisting
│       │   │          1 s while engaged (panda b790fca), ≤ 1.26 s after onset worst
│       │   │          case, above the 1 s budget (WP-S-04 OI-8). 2026-10-13: siren when
│       │   │          heartbeat loss revokes granted authority, ≈ 0.56 s after the last
│       │   │          heartbeat, all builds (panda c33343b; WP-S-04 T-07a); other
│       │   │          triggers not implemented
│       │   ├── BE-2.15 Siren silenced with the SoC audio (shared codec or amplifier,
│       │   │          unknown topology)                                   [CCF → DFI-23]
│       │   └── BE-2.22 Siren path fault (driver, amplifier or speaker) latent: no siren
│       │              self-test (DFM-017.C2; DFM-ACT-011)                     (random HW)
│       └── BE-2.16 Cluster cruise indicator unchanged (no ACC cancel on the fault,
│                  TSR-303) or not independent (AOU-12)  (latent, baseline) [CCF → DFI-15]
├── G2.2 Envelope blocks or revokes authority and no adequate take-over request         [AND]
│   ├── BE-2.02 Envelope blocks or revokes authority while the SoC shows engaged
│   │          (RX fault, stuck authority, safety-mode mismatch; HE-02.4)
│   ├── G2.2.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.09 Envelope blocking detected by controlsMismatch after ≈2 s
│   │   │          (selfdrived.py:338, 508-510) or not at all if pandaStates is
│   │   │          stale with authority shown                         [CCF → DFI-24]
│   │   └── G-HMI
│   └── G-LATCUE
├── G2.3 Control-law input lost and no adequate take-over request                       [AND]
│   ├── BE-2.03 Input of the lateral control law lost or stale (modelV2, calibration,
│   │          carState) and control continues on it (GAP-16)
│   ├── G2.3.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.10 Input loss handled as soft disable: actuation continues ≈3 s
│   │   │          (events.py:853-856, state.py:7-8; GAP-16)
│   │   ├── BE-1.20 (diagnostics masked during big-model fallback; as SG-01)
│   │   └── G-HMI
│   └── G-LATCUE
├── G2.4 Non-finite command and no adequate take-over request                           [AND]
│   ├── BE-2.04 Non-finite command clamped to 0 without a fault (controlsd.py:140-147,
│   │          GAP-19)
│   ├── G2.4.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.11 Non-finite command logged only (GAP-19)                  (latent, baseline)
│   │   └── G-HMI
│   └── G-LATCUE
├── G2.5 SoC crash or hang: control and the SoC warning are lost together               [AND]
│   ├── G2.5.1 Control and the SoC warning lost by one SoC fault                        [OR]
│   │   ├── BE-2.05 SoC crash or hang (whole SoC)                         [CCF → DFI-14]
│   │   └── BE-2.21 selfdrived crash or hang: controlsd and card stop within ≈ 0.1 s,
│   │              ui/soundd show "System Unresponsive" only after 5 s; pandad keeps
│   │              the heartbeat (engaged = 0), so no heartbeat-loss siren (SFMEA-07)
│   └── G-LATCUE
├── G2.6 Actuation frames stop and no adequate take-over request                        [AND]
│   ├── BE-2.06 Actuation frames stop reaching the bus: SoC configuration command
│   │          (0xe5, 0xde, 0xf1; FFI-CM-09), MCU hang (SFMEA-22), car-side bus-off
│   │          (SFMEA-26)                                             [FFI → FFI-CM-09]
│   ├── G2.6.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.17 Loss of the actuation frames not reported in time by the SoC: no
│   │   │          check that the frames reach the bus; seen only indirectly (pandaStates,
│   │   │          canError) with timing not analysed (to confirm, OI-10)
│   │   └── G-HMI
│   └── G-LATCUE
├── G2.7 Loss of the 12 V supply: the SoC warning and the siren are lost with control  [AND]
│   ├── BE-2.07 Loss of the 12 V supply to the device (FSC node N08)
│   └── UE-2.18 Driver does not notice the end of LKA torque or the cluster cruise
│              indicator (AOU-01R, AOU-12)
└── G2.8 Lateral control insufficient for the road and no adequate take-over request   [AND]
    ├── BE-2.23 Achieved curvature below the desired: envelope torque limit below what
    │          the curve needs, or controller or torque model too weak (SFM-004.C1,
    │          C3; ODD curve bound, WP-C-03 OI-7)                              [SOTIF]
    ├── G2.8.1 SoC warning missing or late                                              [OR]
    │   ├── BE-2.24 steerSaturated needs a saturated controller and > 1.2x undershoot;
    │   │          its timing is not analysed against the 1 s budget (SFM-ACT-017)
    │   └── G-HMI
    └── G-LATCUE
```

### 4.1 SG-02 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-02.1 | 2 (effective 1 + latent at the baseline) | {BE-2.01, BE-2.08, BE-2.14 or BE-2.15 or BE-2.22} | At the baseline BE-2.14 is permanently true for EPS faults, so an EPS fault plus the host hysteresis violates the ≤ 1 s budget. With TSR-110 and TSR-516(b) the envelope revokes and sounds the siren, so the cut set becomes {BE-2.01, BE-2.08, siren failure}: dual. 2026-10-12: TSR-110 implemented and the EPS-fault siren in the reference build (panda `b790fca`), but the siren comes ≤ 1.26 s worst case after onset (WP-S-04 OI-8; corrected 2026-10-13 from ≈ 1.14 s: the speaker sounds only on every other 8 Hz tick), so the 1 s budget is not yet met; not verified on hardware. v1.2: a latent siren path fault (BE-2.22, DFM-017.C2) also removes the siren; a start-up self-test (DFM-ACT-011) makes it detectable |
| MCS-02.2 | 2 | {BE-2.02, BE-2.09} | Envelope blocking with slow or self-reported detection. TSR-621; vehicle-response check has no TSR (WP-A-03 OI-8) |
| MCS-02.3 | 2 (effective 1 + latent at the baseline) | {BE-2.03, BE-2.10 or BE-1.20, BE-2.14 or BE-2.15 or BE-2.22} | Stale input with soft disable. TSR-601, TSR-602. With TSR-303 the disengagement cancels ACC, so the cluster changes (BE-2.16 must also occur); a cancel without effect triggers the siren (TSR-516(c)). v1.2: with diagnostics masked during the big-model fallback (BE-1.20, GAP-17) the stale input gets no SoC reaction at all. E-06 is excluded from the reference configuration, but nothing enforces it (SWF-032.C2) |
| MCS-02.4 | 1 (effective) | {BE-2.04} | BE-2.11 is always true at the baseline: the loss is silent. TSR-604 (GAP-19) |
| MCS-02.5 | 1 (effective) | {BE-2.05} | One cause removes control and the SoC warning; the siren comes after 5 s. TSR-407, TSR-516 timing. 2026-10-13: a crash or hang that stops the heartbeat now sounds the siren ≈ 0.56 s after the last heartbeat when authority was granted, in all builds (panda `c33343b`; WP-S-04 T-07a), within the 1 s budget; by design the cut set becomes {BE-2.05, BE-2.15 or another siren failure} (dual). Not verified on hardware, so the order is not reduced here. A hang that keeps `pandad` sending the heartbeat is not covered (SFMEA-07) |
| MCS-02.6 | 2 | {BE-2.01 or BE-2.02 or BE-2.03 or BE-2.06 or BE-2.23, BE-2.12 or BE-2.13 or BE-2.25} | HMI hang or mute. TSR-622, TSR-623. v1.2: a take-over alert masked by a higher-priority, lower-urgency alert (BE-2.25, SWF-035) is a third way for the HMI to fail (SWF-ACT-036, alert ordering); insufficient lateral control (BE-2.23) is a further cause |
| MCS-02.7 | 1 + ext. | {BE-2.07, UE-2.18} | The item cannot warn without power. The driver relies on the EPS ending LKA torque (AOU-01R) and the cluster cruise indicator (AOU-12) |
| MCS-02.8 | 2 | {BE-2.06, BE-2.17} | Actuation frames stop and the SoC does not report it in time; the envelope sees no fault. FFI-CM-09, TSR-711 for the forwarding side; host-side check to confirm (OI-10) |
| MCS-02.9 | 1 (effective) | {BE-2.21} | selfdrived crash or hang (SWF-036): controlsd and card stop within ≈ 0.1 s, and ui/soundd show "System Unresponsive" only after 5 s. pandad keeps sending the heartbeat with engaged = 0, so the heartbeat-loss siren (panda `c33343b`) does not sound; the panda revokes authority after ≈ 3 s on the engaged mismatch. The siren and the cluster cue are latent (BE-2.14, BE-2.16). TSR-622 (critical alert within 0.5 s of a missing selfdriveState); TSR-516 trigger on any revocation that is not a driver action |
| MCS-02.10 | 1 + ext. (effective) | {BE-2.01, UE-2.19} | An EPS drop that the EPS does not signal in `0x262` (SFM-005.C1) cannot be seen by the host or the envelope; only the driver notices (BE-2.14 and BE-2.16 latent). Needs either an assumption of use that the EPS signals every LKA drop, or a check of EPS acceptance against the command (SFM-ACT-018, TSR-626; WP-A-03 OI-8). Lead decision DQ-360 |
| MCS-02.11 | 2 (effective 1 + latent) | {BE-2.20, BE-7.20, BE-2.08 or BE-2.12 or BE-2.13 or BE-2.25 or UE-2.19} | Item diagnostics reset the EPS or open a session on it (SWF-015). BE-7.20 is the standing condition from SG-07. In the reference build ELM327 cannot be selected while TOYOTA is active, so the residual is the pre-engagement phase and the pandad restart window (SWF-027.C2 sets ELM327 briefly while driving). TSR-513 |
| MCS-02.12 | 2 | {BE-2.23, BE-2.24} | Insufficient lateral control: the torque limit or the controller cannot hold the curve (SOTIF, SFM-004.C1/C3), and the steerSaturated warning is late or missing. Effective with BE-2.14 and BE-2.16 latent: no siren trigger exists for saturation. WP-C-03 OI-7 (ODD curve bound); SFM-ACT-017 (FTTI row for the warning path). Whether SG-02 covers by-design degradation: lead decision DQ-361 |

## 5. FTA — SG-04: deceleration beyond what following traffic and the driver can control

Diagram: [SG-04 sheet 1](fta/fta-SG-04-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-04**: vehicle deceleration that a following driver cannot avoid, or that the driver of the reference vehicle cannot override in time: excessive magnitude, step onset, unwarranted braking, unannounced item-initiated braking, or braking while not engaged.

```
TE-04 Uncontrollable deceleration                                                      [OR]
├── G4.1 Deceleration above the controllable bound executed while engaged              [AND]
│   ├── G4.1.1 0x343 accel below the controllable bound on bus 0                       [OR]
│   │   ├── BE-4.01 Envelope bound −3.5 m/s² (toyota.h:209) not derived (GAP-04;
│   │   │          CCF → DFI-08)                                    (SPF, systematic)
│   │   ├── G4.1.1.a SoC excessive deceleration AND envelope fails to clamp           [AND]
│   │   │   ├── BE-4.02 Planner or controller fault (QM), false lead [SOTIF]
│   │   │   └── G-LENV (as SG-03: BE-4.16, BE-1.07…1.09)
│   │   └── BE-4.03 Frame corrupted after the TX hook (as BE-1.10; TSR-517)  (SPF, random HW)
│   └── UE-4.04 PCM executes the request without its own bound (AOU-05R fails)
├── G4.2 Deceleration step within the bound                                            [AND]
│   ├── BE-4.17 Host sends a step: the CarController jerk limit is applied before
│   │          pitch compensation and the PID (carcontroller.py:197-238)
│   ├── BE-4.05 No negative-jerk limit in the envelope: step to −3.5 m/s² allowed
│   │          (GAP-04; FSR-04.02 not implemented)
│   └── UE-4.04
├── G4.3 Unwarranted braking within the bound                                          [AND]
│   ├── G4.3.1 SoC requests braking without cause                                       [OR]
│   │   ├── BE-4.06 Phantom braking or false lead                              [SOTIF]/QM
│   │   └── BE-4.18 Stale or replayed command, or a frozen planner output, held as
│   │              braking (sendcan age gate 1 s, no freshness check in controlsd;
│   │              GAP-10, GAP-16)
│   ├── BE-4.07 Envelope passes any in-bound value while authority is granted (by design)
│   └── UE-4.08 Following traffic closer than the controllability assumption
├── G4.4 Item-initiated deceleration not announced                                     [AND]
│   ├── BE-4.09 DM no-response or fault soft-disable deceleration (HE-04.3; intended)
│   └── G4.4.1 Announcement missing or not perceived                                    [OR]
│       ├── BE-4.10 Soft-disable deceleration announced only at its start
│       │          (longitudinal_planner.py:84-85; TSR-624)
│       └── BE-2.12 / BE-2.13 (HMI hang or mute)                      [CCF → DFI-25]
├── G4.5 False FCW causes reflex braking (HE-04.5)                                     [AND]
│   ├── BE-4.11 FCW raised from stale or invalid input, or from a false lead
│   │          (no freshness gate, selfdrived.py:440-445)             [SOTIF]/QM
│   ├── UE-4.12 Driver brakes hard with a close follower
│   └── (CCF → DFI-26: the same false lead also makes the planner brake, BE-4.06)
├── G4.6 Braking while not engaged (HE-04.4)                                           [AND]
│   ├── G4.6.1 Inactive-value check not effective                                       [OR]
│   │   ├── BE-1.12, BE-1.13, BE-1.14 (false authority, as SG-01)
│   │   └── BE-3.10 (mode or param change bypasses the check)        [FFI → FFI-CM-06]
│   └── BE-4.13 SoC sends a negative acceleration while not engaged (QM)
├── G4.7 Deceleration step at the transition to the safe state (FSR-04.03)            [AND]
│   ├── BE-4.14 Authority revoked: envelope accepts only the inactive value at once,
│   │          with no ramp on the item side
│   └── UE-4.15 PCM steps to the inactive value without its own ramp (AOU-05R)
├── G4.8 Stock ACC and item 0x343 on the car bus together while engaged                 [AND]
│   ├── G4.8.1 Stock camera ACC_CONTROL reaches the car side                            [OR]
│   │   ├── BE-4.19 Relay stays released when commanded to intercept      (random HW)
│   │   └── BE-4.20 Stock 0x343 forwarded from the camera side while the item
│   │              transmits (check_relay entry or forwarding hook defect)
│   └── BE-4.21 Relay malfunction not detected, or detected after the stock and
│              item commands have combined (detection 1–2 s; GAP-12)
└── G4.9 Item deceleration during accelerator override                                  [AND]
    ├── BE-4.22 Host keeps commanding deceleration while the driver presses the
    │          accelerator (gasPressed parsed wrong or override not applied)
    └── BE-4.23 Envelope passes a non-inactive acceleration while the accelerator
               is pressed (get_longitudinal_allowed or GAS_RELEASED decoding defect)
```

### 5.1 SG-04 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-04.1 | 1 + ext. | {BE-4.01, UE-4.04} | Systematic single point (SPF-01) |
| MCS-04.2 | 1 + ext. | {BE-4.03, UE-4.04} | Random single point after the TX hook (SPF-02; TSR-517 specified, not implemented) |
| MCS-04.3 | 2 + ext. | {BE-4.17, BE-4.05, UE-4.04} | Step deceleration within the bound: the host sends a step (jerk limit applied before pitch compensation and the PID, SWF-046) and the envelope has no jerk limit. TSR-205 (GAP-04), TSR-605. The host step is a design property (SWF-046.C1), so the envelope limit is the barrier that is missing |
| MCS-04.4 | 2 + traffic | {BE-4.06 or BE-4.18, BE-4.07, UE-4.08} | By design (BE-4.07); phantom braking is managed by SOTIF and the controllability of the bound. A stale or replayed braking command (BE-4.18) is the SG-04 case of SPF-14: TSR-407…TSR-409, TSR-411, TSR-602 |
| MCS-04.5 | 2 | {BE-4.09, BE-4.10 or BE-2.12/2.13} | Unannounced item braking. TSR-624, TSR-622, TSR-623 |
| MCS-04.6 | 1 + driver | {BE-4.11, UE-4.12} | QM SoC only; FSR-04.06 carries ASIL A on a QM element (WP-C-04 OI-9) |
| MCS-04.7 | 2 | {BE-1.12 or BE-1.13 or BE-1.14, BE-4.13} | As MCS-01.4/01.7 for the longitudinal path |
| MCS-04.8 | 1 + ext. | {BE-4.14, UE-4.15} | Item side cannot ramp after revocation. PCM coasting behaviour to verify (TSR-208) |
| MCS-04.9 | 2 + ext. | {BE-4.02, BE-4.16 or BE-1.07 or BE-1.08 or BE-1.09, UE-4.04} | Intended envelope pattern, as MCS-01.6, with the longitudinal check defect BE-4.16 in place of the lateral BE-1.06 (v0.9); with BE-1.08/BE-1.09 effective 1 through DFI-13 |
| MCS-04.10 | 2 | {BE-3.10, BE-4.13} | Mode or param change bypasses the inactive-value check while the SoC brakes. TSR-513 |
| MCS-04.11 | 2 | {BE-4.19 or BE-4.20, BE-4.21} | Stock ACC_CONTROL and the item's 0x343 combine on the car bus. The relay-malfunction check acts only after 1–2 s and in one direction, so the commands combine until then: TSR-506 (relay readback), GAP-12 |
| MCS-04.12 | 2 | {BE-4.22, BE-4.23} | Item braking against the driver's accelerator input. The panda refuses non-inactive acceleration while the accelerator is pressed (FSR-024, SWF-017) |

## 6. FTA — SG-05: no release on driver brake, cancel or steering override

Diagram: [SG-05 sheet 1](fta/fta-SG-05-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-05**: the item keeps actuating, or opposes the driver, longer than the SG-05 FTTI (≤ 0.2 s) after a driver brake press, a cancel or main-switch-off, a steering override or an accelerator press; or the driver believes the item is disengaged while it actuates (mode confusion, H-07).

```
TE-05 Item does not release on driver action                                           [OR]
├── G5.1 No release on brake press                                                      [AND]
│   ├── G5.1.1 Envelope does not see the brake (safety.h:354-356)                       [OR]
│   │   ├── BE-5.01 0x226 lost or stuck "not pressed" (no checksum or counter, timeout
│   │   │          ≈2 s; GAP-01, GAP-06) (= BE-1.16). 2026-10-12: loss detected
│   │   │          ≤ 0.16 s; stuck still undetected
│   │   ├── BE-5.02 MCU fault keeps controls_allowed (BE-1.07, BE-1.14 class)
│   │   ├── BE-5.14 Envelope software defect in the brake edge logic (generic_rx_checks,
│   │   │          safety.h:354-357), or the safety parameter selects the wrong brake
│   │   │          message (ALT_BRAKE)
│   │   └── BE-1.08, BE-1.09, BE-1.18 (mode or param change, envelope replaced, or a
│   │              DEBUG/ALLOUTPUT build removes the release checks; as G1.2.1.a)
│   └── G5.1.2 Cruise-inactive path does not revoke (safety.h:520-521)                  [OR]
│       ├── BE-5.03 0x1D2 stuck "cruise active" with valid checksum (= BE-1.17)
│       ├── BE-5.02
│       ├── BE-5.15 Envelope software defect in the cruise-inactive revocation
│       │          (pcm_cruise_check, safety.h:518-527)
│       ├── BE-1.08, BE-1.09, BE-1.18 (as G5.1.1)
│       └── UE-5.04 PCM does not drop cruise on brake (AOU-03R)
│   (CCF → DFI-10: one stuck RX path, BE-1.13, causes BE-5.01 and BE-5.03 together)
├── G5.2 No release on cancel or main switch off                                        [OR]
│   ├── BE-5.03
│   ├── BE-5.02
│   ├── BE-5.15
│   ├── BE-1.08, BE-1.09, BE-1.18 (as G5.1.1)
│   └── G5.2.1 Main switch off with CRUISE_ACTIVE still set, not seen                 [AND]
│       ├── UE-5.13 PCM keeps CRUISE_ACTIVE set after the main switch is turned off
│       │          (AOU-05R)
│       └── BE-5.12 The envelope ignores PCM_CRUISE_2 MAIN_ON (0x1D3)  (latent, baseline)
│                  2026-10-12, reference build: cruise active with main off refused at
│                  once, revoked after 150 ms (TSR-405(c), opendbc 8836b65)
├── G5.3 LKA torque opposes the driver's steering                                       [AND]
│   ├── BE-5.05 No driver-override check on the LKA path in the envelope (GAP-02;
│   │          host-only MAX_USER_TORQUE 500, carcontroller.py:33, 83)  (latent, design)
│   ├── BE-5.06 Host override check fails or SoC fault (QM); below 500 units of driver
│   │          torque the host keeps torque by design: overriding counts as active
│   │          (SWF-038.C1, SWF-044.C1)                                (latent, design)
│   └── UE-5.07 EPS does not let the driver overpower LKA torque (AOU-02R)
├── G5.4 Accelerator does not override commanded deceleration                         [AND]
│   ├── BE-5.08 GAS_RELEASED stuck "released" while the driver presses (= BE-3.11);
│   │          the envelope then allows non-inactive values (longitudinal.h:3-5)
│   └── UE-5.09 PCM does not give the driver's pedal priority (AOU-05R)
└── G5.5 Mode confusion: driver believes the item is disengaged while it actuates      [AND]
    ├── BE-5.10 Item HMI shows the wrong state, or cruiseMismatch raised after 6 s
    │          with no reaction (selfdrived.py:420-422, events.py:458-460; GAP-19).
    │          BL-005: cruiseMismatch alerts after 1 s (TSR-308); not re-rated in the
    │          SW FMEA (SWF-039)
    └── BE-5.11 Cluster cruise indicator not an independent cue (AOU-12 fails;
               item TX 0x412 affects the cluster)                     [CCF → DFI-15]
```

### 6.1 SG-05 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-05.1 | 1 (effective) | {BE-1.13} | One stuck RX path hides both brake and cruise-inactive (DFI-10). TSR-404, TSR-405(b) |
| MCS-05.2 | 1 | {BE-5.03} | A stuck cruise frame alone defeats release on cancel or main switch off (G5.2), and together with BE-5.01 also release on brake. E2E or plausibility on `0x1D2` (TSR-401…TSR-406); SPF-04 |
| MCS-05.3 | 2 | {BE-5.01, UE-5.04} | Brake undetected and PCM keeps cruise; AOU-03R |
| MCS-05.4 | 1 (effective) | {BE-5.02} | MCU execution fault. TSR-501, TSR-503 |
| MCS-05.5 | 0 + ext. (effective: both item events latent) | {BE-5.05 (latent), BE-5.06, UE-5.07} | The envelope adds nothing for steering override today (SPF-12). TSR-304. v1.2: below 500 units of driver torque the host also keeps torque by design (overriding counts as active, SWF-038.C1, SWF-044.C1), so release against a driver who steers lightly rests on the EPS alone (AOU-02R, verified by VS-VAL-03). Measures: DQ-053 / SFM-ACT-016 (host backs off) and TSR-304 (envelope) |
| MCS-05.6 | 1 + ext. | {BE-5.08, UE-5.09} | Single gas signal, no plausibility |
| MCS-05.7 | 2 | {BE-5.10, BE-5.11} | Mode confusion. TSR-308, TSR-309 and AOU-12 verification |
| MCS-05.8 | 1 + ext. (latent at the baseline) | {UE-5.13, BE-5.12} | Main switch off while the PCM keeps CRUISE_ACTIVE set: at the baseline the envelope does not read MAIN_ON. Removed in the reference build by TSR-405(c) (opendbc `875e325`; not verified on hardware). A stuck `0x1D2` with main off is already MCS-05.2 |
| MCS-05.9 | 1 | {BE-5.15} | An envelope defect in the cruise-inactive revocation alone defeats release on cancel or main switch off (G5.2), and through G5.1.2 every brake case with it. Systematic single point; SWF-009.C1 claims D=3 from the opendbc safety tests (F-27) |
| MCS-05.10 | 1 (effective) | {BE-1.08 or BE-1.09 or BE-1.18} | A mode or param change, a replaced envelope or a DEBUG/ALLOUTPUT build removes every release check; the host's own release is QM and not credited, as for MCS-05.4. SPF-03, SPF-05; TSR-511…TSR-514, TSR-802 |
| MCS-05.11 | 1 + ext. | {BE-5.14, UE-5.04} | The envelope ignores the brake (edge logic defect, or ALT_BRAKE selects the wrong message) and the PCM keeps cruise. AOU-03R; as MCS-05.3 |

## 7. FTA — SG-06: loss of longitudinal deceleration without take-over warning

Diagram: [SG-06 sheet 1](fta/fta-SG-06-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-06**: the item stops decelerating while engaged when the situation needs it (lead ahead, stop), and the driver gets no take-over request within ≤ 1 s.

```
TE-06 Loss of longitudinal deceleration without take-over request                     [OR]
├── G6.1 Plan or lead input lost and no adequate take-over request                      [AND]
│   ├── BE-6.01 Plan, lead or model input lost or stale (radarFault, commIssue;
│   │          GAP-16)
│   ├── G6.1.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.10 (input loss handled as soft disable, as SG-02)
│   │   ├── BE-1.20 (diagnostics masked during big-model fallback; as SG-01)
│   │   └── G-HMI
│   └── G-LONCUE SoC-independent cue missing or late (longitudinal loss)                [AND]
│       ├── G-SIREN
│       └── BE-6.06 PCM cruise stays active, so the cluster shows no change
│                  (no ACC cancel on the fault, TSR-303)               (latent, baseline)
├── G6.2 Envelope blocks longitudinal authority and no adequate take-over request      [AND]
│   ├── BE-6.02 Envelope blocks longitudinal authority while the SoC shows engaged
│   ├── G6.2.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.09 (controlsMismatch after ≈2 s, as SG-02)
│   │   └── G-HMI
│   └── G-LONCUE
├── G6.3 PCM does not execute ACC and the warning is not delivered                     [AND]
│   ├── BE-6.03 PCM does not execute ACC (ACC or cruise fault); accFaulted is an
│   │          immediate disable (events.py:908)
│   ├── G6.3.1 SoC warning missing or late                                              [OR]
│   │   ├── UE-6.08 PCM does not signal the ACC non-execution: no accFaulted, and no
│   │   │          check of the vehicle response against the request (SFM-011.C1;
│   │   │          WP-A-03 OI-8)
│   │   └── G-HMI
│   └── G-LONCUE
├── G6.4 Non-finite accel and no adequate take-over request                            [AND]
│   ├── BE-6.04 Non-finite accel clamped to 0 without a fault (GAP-19)
│   ├── G6.4.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.11 (logged only, as SG-02)
│   │   └── G-HMI
│   └── G-LONCUE
├── G6.5 Stale accel held and not removed by the envelope                              [AND]
│   ├── BE-6.05 Stale zero or positive accel held (BE-1.19, BE-1.21)
│   ├── BE-1.22 (no command-freshness supervision, as SG-01)
│   └── G-LONCUE
├── G6.6 SoC crash or hang: control and the SoC warning are lost together               [AND]
│   ├── G6.6.1 Control and the SoC warning lost by one SoC fault                        [OR]
│   │   ├── BE-2.05 (as SG-02)                                        [CCF → DFI-14]
│   │   └── BE-2.21 (selfdrived crash or hang, heartbeat kept; as SG-02)
│   └── G-LONCUE
├── G6.7 Actuation frames stop and no adequate take-over request                       [AND]
│   ├── BE-2.06 (configuration command, MCU hang, bus-off; as SG-02)
│   ├── G6.7.1 SoC warning missing or late                                              [OR]
│   │   ├── BE-2.17 (as SG-02)
│   │   └── G-HMI
│   └── G-LONCUE
├── G6.8 Loss of the 12 V supply: the SoC warning and the siren are lost with control  [AND]
│   ├── BE-2.07 (as SG-02)
│   └── UE-6.07 Driver does not notice the end of ACC deceleration or the cluster
│              cruise change (AOU-12; PCM response to missing ACC_CONTROL, XM-02)
└── G6.9 Lead missed or late and no adequate take-over request                         [AND]
    ├── BE-6.09 Lead missed, detected late or tracked too slowly: the plan asks for
    │          too little or late deceleration (SFM-010.C1, SFM-012.C2; SH-06)  [SOTIF]
    ├── G6.9.1 Forward collision warning missing or late                                [OR]
    │   ├── BE-6.10 FCW comes from the same model and lead as the plan: no independent
    │   │          source for a missed lead                          (latent, by design)
    │   └── G-HMI
    └── G-LONCUE
```

### 7.1 SG-06 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-06.1 | 2 (effective 1 + latent) | {BE-6.01, BE-2.10 or BE-1.20, BE-2.14 or BE-2.15 or BE-2.22} | Soft disable keeps the stale command ≈3 s. TSR-601, TSR-602. With diagnostics masked during the big-model fallback (BE-1.20, GAP-17; SWF-032.C2, SWF-043.C2) the stale input gets no SoC reaction at all. A latent siren path fault (BE-2.22, DFM-017.C2) also removes the siren |
| MCS-06.2 | 2 | {BE-6.02, BE-2.09} | As MCS-02.2 |
| MCS-06.3 | 2 | {BE-6.03, BE-2.12 or BE-2.13 or BE-2.25} | `accFaulted` is an immediate disable (`events.py:908`); fails only with the HMI, including a take-over alert masked by a higher-priority alert (BE-2.25, SWF-035) |
| MCS-06.4 | 1 (effective) | {BE-6.04} | Silent loss. TSR-604 (GAP-19) |
| MCS-06.5 | 1 (effective) | {BE-2.05 or BE-2.21} | As MCS-02.5. A selfdrived crash or hang (BE-2.21, SWF-036) stops control within ≈ 0.1 s while pandad keeps the heartbeat, so the heartbeat-loss siren (panda `c33343b`) does not sound; as MCS-02.9 |
| MCS-06.6 | 2 (effective 1 + latent at the baseline) | {BE-6.05, BE-1.22} | As MCS-01.8 for the longitudinal path; SPF-14 |
| MCS-06.7 | 2 | {BE-2.06, BE-2.17} | As MCS-02.8 |
| MCS-06.8 | 2 | {BE-6.01 or BE-6.02 or BE-2.06 or BE-6.09, BE-2.12 or BE-2.13 or BE-2.25} | HMI hang, mute or masked alert, as MCS-02.6. TSR-622, TSR-623. For BE-6.09 the cut set is not minimal in effect: MCS-06.10 already holds with the FCW latent |
| MCS-06.9 | 1 + ext. | {BE-2.07, UE-6.07} | As MCS-02.7. The item cannot warn without power; ACC_CONTROL stops and the driver relies on the PCM's reaction to the missing frames (not characterised, XM-02) and the cluster cruise indicator (AOU-12) |
| MCS-06.10 | 1 (effective) | {BE-6.09} | SOTIF: a missed or late lead is missed or late for the FCW too (BE-6.10 by design), and no SoC-independent cue exists for it (BE-2.14, BE-6.06 latent). Evaluated in WP-C-06 (SH-06); the stock PCS may mitigate but is not credited (WP-C-03 HE-06.1) |
| MCS-06.11 | 1 + ext. (effective) | {BE-6.03, UE-6.08} | As MCS-02.10 for the PCM: a PCM that stops executing ACC without signalling it (SFM-011.C1) is seen by neither the host nor the envelope. Needs an assumption of use that the PCM signals every ACC non-execution, or a check of the vehicle response against the request (WP-A-03 OI-8) |

## 8. FTA — SG-07: suppression, delay or alteration of the stock PCS/AEB

Diagram: [SG-07 sheet 1](fta/fta-SG-07-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-07**: a stock PCS or AEB intervention of the Toyota system is prevented, delayed or altered because of the item. The preliminary FTTI for loss of forwarding is 0.2 s ([WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) §3.6), and content alteration is a per-frame property. The tree treats any loss of the camera-to-car path while the relay intercepts, for longer than the FTTI, as the top event. Since v1.1 the intercept element is drawn as built: two DG419LE analog switches (U1 CAN_H, U2 CAN_L) in comma's harness box, powered from the box supply, driven by SBU1 and pulled to pass-through by R2/R3, with clamp diodes D2/D3 and no position feedback ([RR-2026-010](../04-hardware/reviews/RR-2026-010.md)). "Relay" in event text means these switches.

```
TE-07 Stock PCS/AEB suppressed, delayed or altered                                     [OR]
├── G7.1 Camera-side PCS frames not forwarded while the relay intercepts                [OR]
│   ├── BE-7.01 MCU hang with the relay energised (no IWDG; GAP-07, GAP-43)    (SPF-06)
│   │          2026-10-12: IWDG reset ≤ ≈ 90 ms nominal (TSR-501); residual:
│   │          hang-to-reset plus relay drop-out against the 0.2 s FTTI
│   ├── BE-7.02 Power-save command 0xe7 in car mode stops the camera-side bus
│   │          (FFI-CM-08)                                          (SPF-08) [FFI]
│   ├── BE-7.03 Other SoC configuration commands disturb bus 2 (0xe5, 0xde, 0xf1;
│   │          FFI-CM-09)                                                     [FFI]
│   ├── BE-7.04 Forwarding queue overflow or latency under worst-case load
│   │          (TSR-707 not verified; overflow counted only, can_common.h:165)
│   ├── BE-7.05 Block list wrongly includes a PCS message (systematic; static list
│   │          safety.h:270-281)
│   └── BE-7.06 Camera-side FDCAN or transceiver fault (random HW)
├── G7.2 Item originates or alters PCS-relevant frames                                  [AND]
│   ├── BE-7.07 0x344, 0x411 and DSU IDs in the TX whitelist without a content check
│   │          (modes/toyota.h:19-32; GAP-42)                       (latent, design)
│   │          2026-10-12: removed in the reference build (TSR-705; 0x411
│   │          kept in other builds)
│   └── BE-7.08 SoC sends such a frame (QM fault or compromise)       [FFI → FFI-CM-05]
├── G7.3 Intercept switches held in intercept while forwarding is not running            [AND]
│   ├── G7.3.1 U1/U2 stay in intercept when the device stops driving SBU1             [OR]
│   │   ├── BE-7.09 Analog switch U1 or U2 stuck in intercept, or its IN input damaged
│   │   │          high; no switch-position feedback, readback not pursued (GAP-12;
│   │   │          RR-2026-010 F-06; DQ-209 A)                                  (SPF-07)
│   │   ├── BE-7.15 SBU1 drive stuck high (device-side driver or MCU pin, UK-06)
│   │   └── BE-7.16 Pull-down R2 or R3 open: IN floats when SBU1 is undriven, so the
│   │              switches may stay in intercept (RR-2026-010 F-03; bench test
│   │              VS-HW-23)                                          (latent, design)
│   └── BE-7.10 Forwarding not running (device off, MCU in reset or bootloader)
├── G7.4 Stock path cut or a vehicle bus blocked in the harness or at the car side      [OR]
│   ├── BE-7.11 Connector intermittent or partly seated (SFMEA-30; DFI-05, DFI-20)
│   ├── BE-7.12 Stock camera path open inside the harness box (U1/U2 channel open,
│   │          solder joint, contact; the path is not passive, accepted with
│   │          comma's box, DQ-209 A; RR-2026-010 F-01)
│   ├── BE-7.17 Harness box loses its supply while the car is on: U1/U2 unpowered,
│   │          pass-through not guaranteed, D2/D3 clamp CAN0/CAN2 to the dead rail
│   │          (derived from the v3 drawing; bench test VS-HW-22, DQ-209 A;
│   │          RR-2026-010 F-02)                                            (SPF-15)
│   ├── BE-7.18 Clamp diode D2 or D3 short or leaky: loads or grounds a vehicle bus in
│   │          either switch state (RR-2026-010 F-07)
│   └── BE-7.19 Car-side transceiver holds bus 0 dominant (TXD stuck low)
├── G7.6 Item disturbs the stock ADAS ECU by diagnostics                               [AND]
│   ├── BE-7.20 Diagnostic (ELM327 or pre-engagement) TX hook passes any ISO 15765
│   │          frame, with no service, ignition or motion condition    (latent, design)
│   └── BE-7.21 SoC sends a diagnostic request that resets or opens a session on the
│              stock camera or radar while driving (QM fault)          [FFI → FFI-CM-09]
└── G7.5 PCM gives the item's ACC request priority over PCS braking                     [AND]
    ├── BE-7.13 Item sends an ACC request during a PCS event
    └── UE-7.14 PCM arbitration does not prioritise PCS (AOU-04R fails)
```

### 8.1 SG-07 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-07.1 | 1 | {BE-7.01} | Random single point. TSR-501, TSR-502, TSR-706. 2026-10-12: still a single point, now bounded in time by the IWDG (≈ 90 ms nominal, LSI tolerance open); not verified on hardware |
| MCS-07.2 | 1 | {BE-7.02} | One QM command. TSR-513 |
| MCS-07.3 | 1 | {BE-7.03} | As MCS-07.2 |
| MCS-07.4 | 1 | {BE-7.04} | Needs the forwarding timing analysis and overflow reaction (TSR-707) |
| MCS-07.5 | 1 | {BE-7.05} | Systematic; verified by T-HIL of the forwarding set (TSR-704) |
| MCS-07.6 | 1 | {BE-7.06} | Random single point at the baseline; forwarding supervision with relay release (TSR-711) makes it dual with the supervision |
| MCS-07.7 | 1 (effective) | {BE-7.08} | BE-7.07 is a permanent latent condition at the baseline. TSR-705. 2026-10-12: not applicable for the reference build (BE-7.07 removed); remains for other builds through `0x411` |
| MCS-07.8 | 2 | {BE-7.09, BE-7.10} | Switch stuck in intercept when forwarding stops. TSR-506 readback; comma's box has no position feedback (RR-2026-010 F-06), and the lead kept comma's box without readback (DQ-209 A, 2026-10-16). So the warn-and-refuse reaction decided for a detected stuck switch (DQ-064) has nothing to act on, and the cut set stays undetected. v1.4: the residual is argued from the bench tests of the release behaviour (VS-HW-23) and the accepted SG-009 metric deviation (DQ-320, conditional on the bench tests) |
| MCS-07.9 | 1 | {BE-7.11} | Installation and harness design (TSR-701, TSR-703, TSR-805) |
| MCS-07.10 | 1 + ext. | {BE-7.13, UE-7.14} | AOU-04R vehicle test |
| MCS-07.11 | 1 | {BE-7.12} | Stock path open inside the harness box. v1.1: the path runs through the U1/U2 channels, so it is not passive and TSR-702 cannot be met with comma's box (RR-2026-010 F-01). v1.4: accepted with comma's box (DQ-209 A); stock-path continuity is checked by VS-HW-02 and VS-HW-22 and at end of line (PFM-014) |
| MCS-07.12 | 1 | {BE-7.17} | Harness box loses its supply while the car runs: the switches are unpowered, pass-through is not guaranteed, and the clamps load both buses. Random single point (SPF-15), derived from the drawing. v1.4: kept with comma's box (DQ-209 A); the bench test VS-HW-22 (box VIN open and shorted, device unpowered; DFM-ACT-014) decides the effect, and the tested behaviour becomes an assumption of use. HWSR-502a not met |
| MCS-07.13 | 1 | {BE-7.18} | Clamp diode short loads or grounds a bus in either switch state. Random single point; FMEDA SG-009 FMD-033 |
| MCS-07.14 | 1 | {BE-7.19} | Car-side transceiver holds bus 0 dominant; nothing reaches the car. Random single point, independent of the switch position; FMEDA SG-009 FMD-016 |
| MCS-07.15 | 2 (BE-7.16 effective 1 + latent) | {BE-7.15 or BE-7.16, BE-7.10} | The release default fails: SBU1 driven high, or a pull-down open so IN floats, when forwarding stops. An open R2/R3 is latent until the device stops driving SBU1 (RR-2026-010 F-03); no monitor (HWSR-506e). v1.4: bench test VS-HW-23 (pull-down forced open, four release routes, three temperatures) under DQ-209 A |
| MCS-07.16 | 2 (effective 1 + latent) | {BE-7.20, BE-7.21} | Diagnostic frames reset or take over the stock camera or radar (SWF-015). The permissive diagnostic TX hook is a standing condition; in the reference build ELM327 cannot be selected while TOYOTA is active, so it remains before engagement. TSR-513 |

## 9. Single points of failure and cut-set observations

| ID | Observation | SG | Type | Required measure | TSR / GAP |
|---|---|---|---|---|---|
| SPF-01 | **Limit values are a systematic single point.** Nothing in the item checks that the envelope limits are themselves controllable; the controller uses the same numbers (DFI-08) | SG-01, SG-03, SG-04 | Systematic | Physically derived limits with recorded rationale; controllability test; controller margin | TSR-102, TSR-103, TSR-201, TSR-202, TSR-204, TSR-205, TSR-605; GAP-04 |
| SPF-02 | **No integrity check between the FDCAN load and the bus.** The software TX queue is covered by the packet XOR checked before loading (`panda/board/drivers/fdcan.h:100`; a failed check drops the frame). A random fault in the copy into FDCAN message RAM, the message RAM, the FDCAN core or the transceiver changes an already-approved frame undetected | SG-01, SG-03, SG-04 | Random HW | RAM/FDCAN-RAM ECC enabled with reaction; option: TX read-back of own frames from the bus (FDCAN RX of own TX) compared with the approved frame | TSR-503 (RAM ECC) only; **no TSR for post-hook TX integrity** (OI-6); FMEDA WP-H-03 |
| SPF-03 | **SoC can disable or replace its own monitor** (mode/param, boot pins, softloader). Any SoC fault (or compromise) is effectively a single point | All | Common cause / FFI | Safety-mode lock, command rejection in car modes, RDP/WRP, signature | TSR-511…TSR-514; GAP-09, GAP-24, GAP-38 |
| SPF-04 | **Single RX path for both monitor and controller.** The SoC receives vehicle CAN through the panda; a stuck RX path or stuck vehicle frame misleads both | SG-01, SG-03, SG-05 | Common cause | E2E/plausibility on gating signals in the envelope | TSR-401…TSR-406; GAP-01 |
| SPF-05 | **Debug build has no envelope** (ALLOUTPUT, debug key) | All | Configuration | Release-only firmware, build-type check at start-up reported to SoC and enforced | TSR-514, TSR-802; GAP-25 |
| SPF-06 | **MCU hang leaves the relay energised** (GAP-43) with no hardware watchdog. Torque stops (EPS timeout, AOU-01R), but the stock PCS path stays cut if forwarding stops | SG-07 (and SG-02 without warning) | Random HW | IWDG (TSR-501); fault reaction (TSR-502); relay to stock path on fault/reset (TSR-706). 2026-10-12: IWDG implemented (≈ 90 ms nominal, window, started at the first relay drive; panda `b790fca`), not verified on hardware; TSR-502 and TSR-706 open | GAP-07, GAP-43 |
| SPF-07 | **Intercept switch stuck in intercept** (v1.1: U1/U2 analog switches, not a relay) is not detected: no position feedback in comma's box (RR-2026-010 F-06). An open pull-down (BE-7.16) makes the release default fail the same way, latently | SG-07 | Random HW | v1.4: readback not pursued (DQ-209 A, comma's box kept), so DQ-064's warn-and-refuse reaction has no detection to act on. The residual is argued from bench tests VS-HW-23 and the accepted SG-009 deviation (DQ-320) | GAP-12; HWSR-506a, -506e |
| SPF-08 | **QM command `0xe7` (power save) in car mode** stops camera-side forwarding with the relay energised (by code reading, WP-A-02 FFI-CM-08) | SG-07 | FFI | Reject in car modes | TSR-513; WP-S-02 NF-05 |
| SPF-09 | **SG-02/SG-06 warnings for SoC-detected faults rested on the QM SoC alone.** At v0.2 TSR-516 named only heartbeat loss and envelope-detected RX or platform faults. **Addressed at requirement level in WP-S-02 v0.3:** TSR-516(b) sounds the siren on every envelope revocation that is not a driver action, including an EPS fault (TSR-110); TSR-303 makes every fault-induced disengagement cancel ACC, so the cluster cruise state changes; TSR-516(c) sounds the siren when that cancel has no effect. Not implemented; the cluster cue rests on AOU-12. 2026-10-12, reference build: the EPS-fault part is implemented (LKA refused on the fault frame, TSR-110; siren after 1 s persistence, panda `b790fca`), warning ≤ 1.26 s worst case after onset, above the 1 s budget (WP-S-04 OI-8). 2026-10-13: the heartbeat-loss trigger is implemented in all builds: siren when heartbeat loss revokes granted authority, ≈ 0.56 s after the last heartbeat (panda `c33343b`; WP-S-04 T-07a); the other (b) triggers, (c) and TSR-303 not implemented | SG-02, SG-06 | Common cause / design | As stated; vehicle check of the cluster and PCM cues on a forced cancel (AOU-12) | TSR-516, TSR-303 (OI-7 closed) |
| SPF-10 | **Non-finite actuator command is replaced by 0 silently** | SG-02, SG-06 | Systematic (design) | Treat as a fault with take-over request | TSR-604; GAP-19 |
| SPF-11 | **SoC crash removes control and the SoC warning together**; the independent siren comes after 5 s. 2026-10-13: when the crash stops the heartbeat and authority was granted, the siren now sounds ≈ 0.56 s after the last heartbeat, in all builds (panda `c33343b`; WP-S-04 T-07a); not verified on hardware | SG-02, SG-06 | Common cause (DFI-14) | Heartbeat timeout and siren within the warning budget (implemented 2026-10-13, not verified) | TSR-407, TSR-516; GAP-06 |
| SPF-12 | **No driver steering override check in the envelope** on the LKA path; release rests on the QM host check and the EPS (AOU-02R). v1.2: below 500 units of driver torque the host keeps torque by design too (BE-5.06 latent), so MCS-05.5 rests on the EPS alone | SG-05 | Design | Driver-override check and torque reduction in the envelope | TSR-304; GAP-02 |
| SPF-13 | **Camera-to-car forwarding is single-channel with no supervision that releases the relay.** An MCU hang, a camera-side bus fault, a QM configuration command or queue overflow stops PCS forwarding while the relay intercepts | SG-07 | Random HW / FFI | IWDG (≤ 0.1 s) and relay release on fault; reject configuration commands in car modes; forwarding supervision with relay release within the SG-07 budget | TSR-501, TSR-502, TSR-513, TSR-706, TSR-707, TSR-711 (added in WP-S-02 v0.3) |
| SPF-14 | **A stale SoC command is held.** Nothing in the envelope supervises command freshness at the baseline (BE-1.22: the heartbeat shows only pandad liveness), and the value checks cannot see a stale in-limit value (BE-1.23). A SoC that stops updating while its link stays alive (BE-1.19…BE-1.21, BE-6.05) holds torque or acceleration beyond the FTTI; a stale or replayed braking command (BE-4.18, v0.9) holds deceleration | SG-01, SG-03, SG-04, SG-06 | Systematic (design) | Command freshness supervised in the envelope within the FTTI (sequence counter or age) | TSR-407…TSR-409, TSR-411; GAP-06, GAP-10, GAP-16 |
| SPF-15 | **Harness box supply is a single point for the stock path** (v1.1, RR-2026-010 F-02). U1/U2 are powered from the box VIN; when it is lost while the car runs, pass-through is not guaranteed and D2/D3 clamp both buses towards the dead rail. Derived from the drawing, not yet tested | SG-07 (and SG-02 without warning) | Random HW | v1.4: comma's box kept (DQ-209 A); bench test VS-HW-22 (DFM-ACT-014) and the tested behaviour recorded as an assumption of use; the SG-009 metric shortfall accepted as a deviation conditional on the bench tests (DQ-320) | HWSR-502a, HWSR-702 |
| SPF-16 | **The envelope's cruise-inactive revocation is a systematic single point for release** (v1.2). A defect in `pcm_cruise_check` (BE-5.15, SWF-009) alone defeats release on cancel or main switch off, and every brake case through G5.1.2 | SG-05 | Systematic | Envelope revocation verified by the safety tests of the reference build; a second, independent revocation path (brake edge) already exists only for the brake | TSR-401…TSR-406; SWF-009 (F-27) |
| SPF-17 | **A selfdrived crash or hang removes control and the SoC warning while the heartbeat continues** (v1.2). pandad keeps the heartbeat with engaged = 0, so the heartbeat-loss siren does not sound; the panda revokes after ≈ 3 s on the engaged mismatch, and the UI shows "System Unresponsive" after 5 s (BE-2.21, SWF-036) | SG-02, SG-06 | Systematic / common cause | Critical alert within 0.5 s of a missing selfdriveState; siren on any revocation that is not a driver action | TSR-622, TSR-516; SFMEA-07 |
| SPF-18 | **Driver monitoring is one QM channel with no independent check** (v1.3). A model miss, wrong thresholds, a degraded camera that is never flagged invalid, the demo mode, wrong escalation timing or a missing forced stop each defeats SG-08 alone (MCS-08.1…08.7) | SG-08 | Systematic / random HW / SOTIF | ASIL A measures on the DM chain or an independent monitor (FSC); DM output validity (TSR-609), deliberate-input wheel-touch reset (TSR-612), demo mode removed (TSR-610); the no-response reaction defined (DQ-365) | TSR-608…TSR-612; GAP-20, GAP-21 |
| Obs-01 | MCS-01.6 is the only truly dual-point cut set that the envelope pattern intends. It stays dual only if MCU faults (BE-1.07) are detected; today there is no IWDG, MPU or ECC reaction, so latent MCU faults can accumulate. 2026-10-12: IWDG implemented (TSR-501, hangs only); MPU and ECC reactions still open | SG-01 | Latent | Latent-fault diagnostics at start-up and run time | TSR-501, TSR-503, TSR-507 |
| Obs-02 | Every SG-01, SG-03 and SG-04 path ends in an EPS or PCM AND-input (UE-1.11, UE-3.05, UE-4.04). These are unverified AoUs. The trees must not be read as "dual" until AOU-01R/AOU-05R are verified | SG-01, SG-03, SG-04 | AoU | Vehicle characterisation (WP-S-09) | GAP-05 |
| Obs-03 | SG-07 had no numeric FTTI. [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) v0.2 §3.6 sets a preliminary 0.2 s for loss of forwarding (FDTI ≤ 0.1 s, FRTI ≤ 0.1 s, zero margin), which tightened the watchdog timeout (TSR-501) to ≤ 0.1 s and added forwarding supervision (TSR-711) | SG-07 | Timing | Measure the PCS timing and confirm the FTTI (WP-S-04 OI-4, OI-7) | RR-2026-004 F-04; RR-2026-005 F-02 |
| Obs-04 | Many SG-01, SG-02, SG-03 and SG-06 cut sets are order 2 or more in form but contain conditions that are always true at the baseline. These are tagged `(latent, baseline)` in the trees: BE-1.22, BE-2.11, BE-2.14, BE-2.16, BE-6.06 (and the by-design BE-1.23, BE-3.07, BE-4.07). The rows mark them "effective n + latent": removing the latent condition is what makes them dual | SG-01, SG-02, SG-03, SG-06 | Latent | As SPF-09, SPF-10, SPF-14 | — |

### 9.1 Computed minimal cut sets (check of the tables)

The cut-set tables in §2…§8 are written by hand. [`fta/fta_cutsets.py`](fta/fta_cutsets.py) computes the minimal cut sets of each tree from its gate logic as written (OR = union, AND = product, absorption; transfers expanded, repeated events one variable) and checks every table row against them. The full result is [`fta/cut-sets.md`](fta/cut-sets.md); CI keeps it current. An event tagged `(latent, …)` or described as "by design" is taken as present at the baseline, so a row that omits only such events is accepted as an *effective* order.

v0.4 ran the check on the trees as they were and found CS-01…CS-07. v0.5 restructures the trees and completes the tables. Result at v0.5:

| Goal | Computed cut sets (v0.4 → v0.5) | Effective order ≤ 1 | Table rows | Match or effective | Argued from common cause | Cut sets not in a table |
|---|---|---|---|---|---|---|
| SG-01 | 30 → 27 | 6 | 9 | 8 | MCS-01.4 (DFI-10) | 0 |
| SG-02 | 111 → 33 | 3 | 8 | 8 | — | 0 |
| SG-03 | 16 → 16 | 7 | 11 | 11 | — | 0 |
| SG-04 | 17 → 17 | 6 | 10 | 10 | — | 0 |
| SG-05 | 6 → 6 | 5 | 7 | 6 | MCS-05.1 (DFI-10 note; BE-1.13 is not in the SG-05 tree) | 0 |
| SG-06 | 93 → 32 | 3 | 8 | 8 | — | 0 |
| SG-07 | 11 → 11 | 10 | 11 | 11 | — | 0 |

| ID | Finding (v0.4) | Resolution (v0.5) |
|---|---|---|
| CS-01 | `BE-1.16` and `BE-1.17` were single-event cut sets of TE-01: G1.2.2 had no AND on the SoC commanding torque, and they were in neither the table nor the SPF list | G1.2.2 is now an AND with BE-1.15, as G1.2.1. New MCS-01.9 {BE-1.16 or BE-1.17, BE-1.15}, effective 1 through DFI-10 (the SoC reads the same frames); SPF-04 |
| CS-02 | G1.3.2 was always true: its OR input BE-1.23 is by design, so a stale SoC command alone held torque, while MCS-01.8 said order 2 | G1.3.2 is an AND of BE-1.22 (no freshness supervision, latent at the baseline) and BE-1.23. MCS-01.8, MCS-03.7 and MCS-06.6 state "effective 1 + latent"; the single point is recorded as **SPF-14** |
| CS-03 | MCS-01.6 omitted UE-1.11 and the BE-1.04/BE-1.05 pairs; SG-03/SG-04 had no row for the G-ENV pattern; MCS-01.3 and MCS-03.5 were in words | MCS-01.6 is "2 + ext." with all SoC and envelope alternatives; MCS-01.3 and MCS-03.5 are written as event sets (their wording kept); new MCS-03.8 and MCS-04.9 |
| CS-04 | SG-03 treated false authority and a mode or param bypass as sufficient for acceleration while not engaged; SG-04 G4.6 needed the SoC to send a command | G3.3 is now an AND of G3.3.1 (inactive-value check not effective) and the new BE-3.13 (SoC sends acceleration while not engaged; DFI-10), as G4.6. New MCS-03.9, MCS-03.10, MCS-03.11 and MCS-04.10; MCS-03.6 includes BE-3.13 |
| CS-05 | SG-02 and SG-06 ANDed two independent OR branches, which paired warning failures with unrelated causes; the independent cues were an OR, so one missing cue counted as no take-over request; a loss of supply did not remove the warning | Both trees have one branch per cause, each ANDed with that cause's SoC warning failure and the shared HMI gate (G-HMI). The independent cue is an AND of the siren (G-SIREN) and the cluster (G-LATCUE, G-LONCUE). G2.5/G6.6 and G2.7 remove the SoC warning with control. New events BE-2.17 and UE-2.18 (OI-10). Cut sets fall from 111 to 33 and from 93 to 32 |
| CS-06 | `BE-5.03` alone was a cut set of TE-05 through G5.2, so MCS-05.2 was not minimal; MCS-06.6 named BE-1.22, which was not in the SG-06 tree | MCS-05.2 is now {BE-5.03}, order 1 (SPF-04, TSR-401…TSR-406). G6.5 contains BE-1.22 |
| CS-07 | `BE-7.12` was a single-event cut set with no row | New MCS-07.11 (TSR-702) |

Every cut set of effective order ≤ 1 at v0.5 has a table row:

- **SG-01:** MCS-01.1, 01.2 (+ EPS), 01.5, 01.8 (stale command, SPF-14).
- **SG-02:** MCS-02.4, 02.5, 02.7 (+ driver).
- **SG-03:** MCS-03.1…03.4 (+ PCM or driver), 03.7 (SPF-14), 03.11 (+ PCM).
- **SG-04:** MCS-04.1, 04.2, 04.4 (incl. the stale command BE-4.18, SPF-14), 04.6, 04.8 (+ PCM, driver or traffic). v0.9: MCS-04.3 is order 2 + ext., since the tree now needs the host step BE-4.17.
- **SG-05:** MCS-05.2…05.6.
- **SG-06:** MCS-06.4…06.6.
- **SG-07:** MCS-07.1…07.7, 07.9…07.11.

The rows with no external event are the single points of §9.

v0.9 changes only SG-04: 21 computed cut sets (was 17), 6 of effective order ≤ 1, 12 table rows, all match ([`fta/cut-sets.md`](fta/cut-sets.md)).

v1.0 changes only SG-01: 36 computed cut sets (was 27), still 6 of effective order ≤ 1, 11 table rows, every cut set covered. The new cut sets are order 2: MCS-01.10 (effective 1 through DFI-13, like MCS-01.3) and MCS-01.11; MCS-01.6 and MCS-01.7 gain BE-1.24 and BE-1.25 ([`fta/cut-sets.md`](fta/cut-sets.md)).

v1.1 changes only SG-07: 17 computed cut sets (was 11), 15 of effective order ≤ 1, 16 table rows, every cut set covered. The new single points are random hardware in comma's harness box and at the car-side transceiver (MCS-07.12…07.14; SPF-15); MCS-07.15 and MCS-07.16 are order 2 with a latent condition ([`fta/cut-sets.md`](fta/cut-sets.md)).


v1.2 maps the last four goals and changes their trees (fta-fmea-mapping.md §2c). Computed cut sets: SG-02 33 → 100, SG-03 16 → 22, SG-05 6 → 12, SG-06 32 → 85; every one is covered by a table row. Most of the growth is SG-02 and SG-06 pairing each cause with more ways the warning can fail (masked alert, latent siren path, big-model masking). New cut sets of effective order ≤ 1: MCS-02.9 (selfdrived crash with the heartbeat kept), MCS-02.10 and MCS-06.11 (silent EPS or PCM, + ext.; DQ-360), MCS-05.9 (cruise-revocation defect, SPF-16), MCS-05.10 (mode, firmware or debug build), MCS-06.9 (supply loss, + ext.), MCS-06.10 (lead missed or late, SOTIF; DQ-361). MCS-05.5 drops to effective 0 + ext. (SPF-12).

v1.3 adds SG-08 (§13): 11 computed cut sets, all of effective order ≤ 1 (MCS-08.1…08.8), because the DM chain is a single QM channel (SPF-18).
## 10. System FMEA

Severity of the vehicle effect is expressed by the affected SG. Detection = mechanism that detects the failure mode in the item today. Columns: **Mech.** = safety mechanism that reaches the safe state; **Gap** = what is missing.

| ID | Element | Failure mode | Effect (local → vehicle) | SG | Detection (today) | Mechanism (today) | Gap / required |
|---|---|---|---|---|---|---|---|
| SFMEA-01 | E-01 controlsd | Excessive torque command | Torque above intent → lateral deviation | SG-01 | Envelope per-frame limits (`lateral.h:60-151`) | Frame dropped; `controls_allowed` not cleared by TX violation alone | FSR-01.12: revoke on TX violation (TSR-108, TSR-109) |
| SFMEA-02 | E-01 controlsd | Output frozen (hang) | Last command repeated by card/pandad or no command | SG-01, SG-02 | selfdrived `processNotRunning`/`commIssue` (QM); panda heartbeat 3–5 s | Soft disable keeps actuating 3 s (GAP-16); SILENT after 5 s | Freshness check ≤ 0.3 s in envelope (TSR-408, TSR-409; host TSR-602); GAP-06, GAP-10 |
| SFMEA-03 | E-01 controlsd | Non-finite output | Clamped to 0 silently (`controlsd.py:140-147`) → loss of control without warning | SG-02, SG-06 | Logged only | None | FSR-06.04 (TSR-604); GAP-19 |
| SFMEA-04 | E-01 card | Sends `0x343` positive accel while engaged and lead close | Unintended acceleration | SG-03 | None if in bound | Envelope bound +2.0 m/s² | Jerk limit (FSR-03.03, TSR-204); bound rationale |
| SFMEA-05 | E-01 card / pandad | Sends PCS messages `0x344`/`0x411` (or DSU-only IDs, WP-S-02 NF-07) | Stock PCS altered | SG-07 | None | Whitelist allows them. 2026-10-12: `0x344` and the DSU IDs refused in every build; `0x411` refused in the reference build (TSR-705) | FSR-07.02 (TSR-705; GAP-42) |
| SFMEA-06 | E-01 pandad | Sets wrong safety mode/param | Envelope misconfigured | All | Host cross-check after 10 s (QM, same source) | Mode change clears authority. 2026-10-12, reference build: any mode other than SILENT, NOOUTPUT, ELM327 or TOYOTA/73 refused, and in TOYOTA only NOOUTPUT/SILENT (TSR-512); counted as `requestsRejected` | Safety-mode lock (TSR-512); GAP-09 |
| SFMEA-07 | E-01 pandad | Heartbeat continues while controls loop is dead | Envelope keeps authority | SG-01, SG-02 | 3 s mismatch only if `engaged` flag drops. 2026-10-12: unchanged; the 0.3 s heartbeat timeout (TSR-407) does not act while heartbeats continue | — | Heartbeat bound to control loop (TSR-409); GAP-10 |
| SFMEA-08 | E-01 selfdrived | Engaged state differs from PCM (`cruiseMismatch`) | Mode confusion | SG-05, SG-02 | Event raised after 6 s, no reaction (`events.py:458-460`) | None | FSR-05.06 (TSR-308); GAP-19 |
| SFMEA-09 | E-01 HMI (ui/soundd) | No take-over warning (crash) | Unannounced loss | SG-02, SG-06 | panda siren after heartbeat loss | Siren 3 s after 5 s. 2026-10-13: siren ≈ 0.56 s after the last heartbeat when authority was granted, all builds (panda `c33343b`; WP-S-04 T-07a), only if the crash also stops the heartbeat (a `ui`/`soundd` crash alone does not) | FSR-02.05 timing (TSR-516; SoC TSR-606); DFI-14 |
| SFMEA-10 | E-01 DM chain | DM inactive / demo mode | Inattention undetected | (SG-02/06 controllability) | `dmonitoringd` validity → `commIssue` | Soft disable | FSR-02.08 (QM, SOTIF); GAP-20, GAP-21 |
| SFMEA-11 | E-02 driving model | Wrong curvature / accel | Unintended manoeuvre within bounds | SG-01, SG-03 [SOTIF] | Excessive-actuation latch (2× ISO limits, `selfdrive/selfdrived/helpers.py`) | Soft disable + no-entry | SOTIF (WP-C-06); bounded by envelope |
| SFMEA-12 | E-03 safety hooks | Software defect in limit check | Excess passes | SG-01, SG-03, SG-04 | Unit/mutation tests (design-time) | — | ASIL-level verification (MC/DC, target tests) GAP-13 |
| SFMEA-13 | E-03 RX checks | Stuck/replayed `0x1D2`/`0x226` frames accepted | False authority / no revocation | SG-01, SG-03, SG-05 | Checksum (`0x1D2` only), timeout ≈2 s. 2026-10-12: timeout 5 periods, ≤ 0.16 s (TSR-401); reference build: CRUISE_ACTIVE with MAIN_ON = 0 refused or revoked after 150 ms (TSR-405(c)); stuck or replayed frames with valid content still accepted | `controls_allowed` cleared on checksum fail or timeout | E2E/plausibility, ≤ 0.3 s (TSR-401…TSR-406); GAP-01, GAP-06 |
| SFMEA-14 | E-03 driver-torque handling | Driver steering override not detected in envelope | Torque opposes driver | SG-05 | Host only (`carcontroller.py:33, 83`) | EPS (assumed) | FSR-05.03 (TSR-304); GAP-02 |
| SFMEA-15 | E-03 EPS status | EPS LKA fault not seen by envelope | Unannounced loss | SG-02 | Host only (`carstate.py:122-127`). 2026-10-12, reference build: envelope reads LKA_STATE (`0x262`), reports `epsFault` | Host soft/immediate disable. 2026-10-12, reference build: STEERING_LKA with torque refused on a fault code (TSR-110); siren after 1 s persistence (TSR-516(b)), ≤ 1.26 s worst case after onset (WP-S-04 OI-8) | FSR-02.01 (TSR-110); GAP-03 |
| SFMEA-16 | E-03 tick / heartbeat | Tick ISR starved or stopped | No timeout detection, no siren | SG-01, SG-02 | Interrupt-rate fault (report-only). 2026-10-12: timeouts and heartbeat supervision run in the 100 Hz safety task (TIM4, rate fault at 110 Hz, report-only) | None. 2026-10-12: IWDG fed only by the safety task after main-loop progress; a stopped task resets the MCU in ≈ 90 ms (TSR-501); a starved but running task is not detected (no WCET) | IWDG (TSR-501); fault reaction (TSR-502); GAP-07, GAP-08 |
| SFMEA-17 | E-03 TX path after hook | Frame bit flip in queue or message RAM | Approved frame altered | SG-01, SG-03, SG-04 | Software queue: packet XOR (host-computed, carried through the hook) checked at FDCAN load (`fdcan.h:100`), frame dropped on mismatch. FDCAN message RAM, core, transceiver: none | Frame drop (queue only) | SPF-02 measures (TSR-503 partly; no TSR, OI-6) |
| SFMEA-18 | E-03 SPI link | Corrupted command passes 8-bit XOR | Wrong CAN frame or wrong control command | All | XOR, NACK | TX hook limits (frames); none for control commands | CRC + counter (TSR-410, TSR-413); GAP-10 |
| SFMEA-19 | E-03 SPI link | Length field above buffer size | DMA overrun into SRAM1/2 | All (potential) | None | Memory-bank separation (unconfirmed) | Length bound (TSR-412; WP-S-02 NF-04); WP-A-02 FFI-SP-02 |
| SFMEA-20 | E-03 forwarding | Camera-side forwarding stops (power-save command, bus-2 fault) with relay energised | Stock PCS suppressed | SG-07 | None in envelope | —. 2026-10-12, reference build: `0xe7` refused in a car mode (TSR-513); bus-2 fault still without reaction | Reject `0xe7` in car modes; forwarding supervision (TSR-513, TSR-707); WP-A-02 FFI-CM-08 |
| SFMEA-21 | E-03 relay malfunction detection | Detection 1–2 s, one direction only | Camera commands reach car / PCS path cut undetected | SG-01, SG-07 | Traffic-based (`safety.h:215-220, 372-380`) | Block all TX | Readback (TSR-506); GAP-12 |
| SFMEA-22 | E-04 MCU core | Hang (no IWDG) | Relay stays energised; TX stops | SG-07, SG-02 | None. 2026-10-12: IWDG (TSR-501), ≈ 90 ms nominal after the first relay drive | EPS timeout (AOU-01R). 2026-10-12: watchdog reset releases the relay; reset reported as `watchdogReset`; not verified on hardware | TSR-501, TSR-502, TSR-706; GAP-07, GAP-43 |
| SFMEA-23 | E-04 MCU RAM | Bit flip in `controls_allowed`/limits | Authority or limit wrong | SG-01, SG-03 | None (no ECC handling) | — | TSR-503, TSR-507; GAP-08 |
| SFMEA-24 | E-04 MCU clock | HSE failure | Clock loss | All | CSS → NMI → reset (`clock.h:118-119`, `early_init.h:73-76`) | Reset (relay expected released) | Confirm reset-state relay (TSR-706); drift detection (TSR-504) |
| SFMEA-25 | E-04 power | Supply dip / brown-out | Erratic MCU and SoC | All | Voltage reported only | NMI/HardFault reset | BOR/PVD (TSR-505); DFI-01 |
| SFMEA-26 | E-04 CAN transceiver (bus 0) | Dominant-stuck / babbling | Vehicle bus disturbed; EPS/PCM lose messages | SG-02, SG-06, SG-07 | Error counters, bus-off reset (`fdcan.h:76-84`) | None in firmware | TSR-508 |
| SFMEA-27 | E-04 SoC GPIO | BOOT0/RST asserted while driving | MCU in ROM bootloader; relay released (expected) | SG-02 (loss), cybersecurity | pandad recovery logs | Relay release (reset state) | TSR-706, TSR-511; GAP-38 |
| SFMEA-28 | E-05 relay | Welded in intercept | Stock path cut while item off | SG-07 | None | — | TSR-506; GAP-12 |
| SFMEA-29 | E-05 relay | Open coil / released while engaged | Camera LKA/ACC reach car together with item commands | SG-01 (conflicting commands) | Relay malfunction latch 1–2 s | Block all TX | TSR-506 timing |
| SFMEA-30 | E-05 connector | Intermittent contact | CAN errors, ignition flicker, relay chatter | All | Harness status (suspended while relay driven, `harness.h:59`) | Indirect (CAN timeouts) | TSR-701, TSR-703 |
| SFMEA-31 | EXT-EPS | Misreports motor torque | Measured-tracking check misled | SG-01 | None | Magnitude/rate limits still apply | DFI-11; TSR-101, TSR-103, TSR-110 |
| SFMEA-32 | EXT-PCM | Ignores cancel / inactive value | Accel continues | SG-03, SG-05 | `accFaulted` (host) | — | AOU-05R vehicle test (WP-S-09) |
| SFMEA-33 | E-01 selfdrived | Envelope blocking detected late or not at all (`controlsMismatch` after 200 samples; stale `pandaStates`) | Control lost while the SoC shows engaged | SG-02, SG-06 | `controlsMismatch` ≈2 s (`selfdrived.py:338, 508-510`); `pandaStates` alive 1 s | Immediate disable after detection | TSR-621; vehicle-response check (WP-A-03 DFI-24, OI-8) |
| SFMEA-34 | E-01 HMI (ui) | Render loop hung, process alive | Take-over request and engagement state not shown | SG-02, SG-06, SG-05 (mode confusion) | None (`processNotRunning` on crash only, `selfdrived.py:351-357`) | — | TSR-622; WP-A-03 DFI-25 |
| SFMEA-35 | E-01 HMI (soundd) | Audio stream stalled, or volume below audible | Alert not heard | SG-02, SG-06 | None | Critical alerts ramp to maximum over 4 s (`soundd.py:21`) | TSR-622, TSR-623; WP-A-02 FFI-CM-17, -18 |
| SFMEA-36 | E-01 DM and planner | No-response or soft-disable deceleration | Braking announced only at its start; jerk not bounded | SG-04 | DM escalation alerts precede the no-response deceleration | Envelope decel bound | TSR-624, TSR-205; GAP-04 |
| SFMEA-37 | E-01 selfdrived (FCW) | FCW from stale input or a false lead | False FCW → reflex braking with a close follower | SG-04 | None (no freshness gate, `selfdrived.py:440-445`) | — | TSR-625 (ASIL A on QM, WP-C-04 OI-9); WP-A-03 DFI-26 |
| SFMEA-38 | E-03 TX path | Actuation frames sent faster than nominal (in-limit burst) | Rate limits applied per frame, not per time | SG-01, SG-03, SG-04 | None. 2026-10-12, reference build: per-ID count over a 250 ms window (TSR-518) | Per-frame limits. 2026-10-12, reference build: frames beyond the budget rejected; 3 rejections revoke authority, reported as `txRateExceeded`; budgets to be confirmed on logs | TSR-518 |
| SFMEA-39 | E-04 camera-side FDCAN / transceiver | Stuck or error-passive; camera-side RX stops | PCS frames not forwarded while the relay intercepts | SG-07 | Error counters, bus-off recovery (`fdcan.h:76-84`) | None that releases the relay | Forwarding supervision with relay release (TSR-707, TSR-706); SPF-13 |
| SFMEA-40 | E-03 forwarding block list | Wrong entry (a PCS message blocked) | Stock PCS frame not delivered | SG-07 | Design review only | — | T-HIL of the full forwarding set (TSR-704) |

## 11. Feedback to other work products

| To | Item |
|---|---|
| [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) | SPF-01…-13 map to TSRs (§9). SPF-02 is now covered by TSR-517 (post-load TX read-back; OI-6 closed). TSR-516 must state its trigger set (SPF-09, OI-7) |
| [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) | SPF-02 and SPF-08 are not covered by an FSR; FSR-01.09 covers MCU execution faults but not post-hook frame corruption explicitly. SG-07 needs a numeric FTTI (Obs-03) |
| [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md) | SFMEA-17, -22…-26, -39 as FMEDA inputs |
| [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) | SFMEA-12, -13, -16, -18, -19, -38, -40 as software safety analysis inputs |
| [WP-V-05](../06-validation/WP-V-05-fault-injection.md) | Every BE marked SPF and every SFMEA row with a mechanism gets a fault-injection case |
| [FMEAs](fmea/analyses/) | Basic events are linked to FMEA failure modes in [fta-fmea-map.yaml](fta-fmea-map.yaml) and checked both ways; SG-04 pilot findings F-1…F-10 in [fta-fmea-mapping.md](fta-fmea-mapping.md) §3 (2026-10-13), resolved in v0.9 (tree) and SW FMEA rev 0.7, DFMEA rev 0.3, System FMEA rev 0.6, PFMEA rev 0.3. SG-01 mapped 2026-10-16 (F-11…F-16): F-11…F-13 resolved in v1.0 (tree); F-14 (eight FMEA modes that reach SG-01 or SG-04 through shared events but do not cite the hazard) and F-15 (no FMEA mode for `0x1D2` stuck at cruise active) are open for the FMEA owners. SG-07 mapped 2026-10-16 with the harness-box re-base (v1.1): F-17…F-19 open for the FMEA owners. SG-02, SG-03, SG-05 and SG-06 mapped 2026-10-16 (v1.2), so every goal is now in the map: tree findings resolved; F-25…F-28, F-31 open for the FMEA owners; F-22, F-29, F-32…F-34 queued for the lead (DQ-360…DQ-364). SG-08 tree and mapping 2026-10-16 (v1.3): F-37 open for the FMEA owners, F-38 queued for the lead (DQ-365) |

## 12. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Repeat FTA and FMEA on the target architecture of WP-S-03 and show that SPF-01…SPF-13 are removed or argued | Safety engineer | G2 |
| OI-2 | Re-check TSR references when WP-S-02 leaves Draft | Safety engineer | G2 |
| OI-3 | ~~Develop FTAs for SG-02, SG-04, SG-05, SG-06, SG-07~~ **Closed** in v0.2 (§4…§8) | Safety engineer | G2 |
| OI-4 | Confirm whether STM32H7 FDCAN message RAM has ECC and whether it is enabled (SPF-02) | HW lead | G2 |
| OI-5 | Confirm by HIL test that an MCU hang leaves the relay energised (SPF-06) and that `0xe7` stops forwarding (SPF-08) | Test lead | G4 |
| OI-6 | ~~Report to the WP-S-02 author: no TSR covers frame integrity between `safety_tx_hook` and the bus (SPF-02)~~ **Closed:** TSR-517 | Safety engineer | G2 |
| OI-7 | ~~Report to the WP-S-02 author: TSR-516 should name its triggers so that every envelope revocation while engaged, including an EPS-fault revocation (TSR-110), sounds the siren (SPF-09)~~ **Closed:** WP-S-02 v0.3 TSR-516(a)…(c), TSR-303 | Safety engineer | G2 |
| OI-8 | Confirm by HIL test that a camera-side bus fault stops forwarding with the relay energised (SFMEA-39) | Test lead | G4 |
| OI-9 | ~~Resolve CS-01…CS-07 (§9.1)~~ **Closed** in v0.5: trees restructured and tables completed; every computed cut set is in a table | Safety engineer | G2 |
| OI-10 | Confirm the events added in v0.5: how and when the SoC reports lost actuation frames (BE-2.17), the driver cue on supply loss (UE-2.18), and whether the cluster cruise indicator counts as a take-over request (BE-2.16, BE-6.06; AOU-12) | Safety engineer, test lead | G3 |

## 13. FTA — SG-08: automated control continues with a driver who is not supervising or not responding

Diagram: [SG-08 sheet 1](fta/fta-SG-08-1.svg) (all sheets: [fta/](fta/README.md)).

New in v1.3 for SG-08 (ASIL A), which [WP-C-03](../02-concept/WP-C-03-hara.md) v0.4 adds for hazard H-09 (HE-09.1 driver not supervising, HE-09.2 driver asleep or incapacitated; decision register DQ-205). Numbered §13 rather than §9 so that the references to §9…§12 elsewhere stay valid.

Top event **TE-08**: the item keeps driving while the driver is not supervising or not responding, and neither escalates the take-over alerts in time nor brings the vehicle to its no-response reaction.

The driver-monitoring (DM) chain runs on the QM SoC: `dmonitoringmodeld` (driver camera and model) → `dmonitoringd` (policy: vision 5/8/13 s, wheel-touch 5/15/25 s; TSR-608) → `selfdrived` alerts and `controlsd`. At alert level 3, `noResponseForceDecel` is set after a further 5 s (`selfdrive/monitoring/policy.py:39, 398`). `controlsd` turns it into `forceDecel` (`controlsd.py:235`), and the planner then targets 0 km/h (`longitudinal_planner.py:84`), so the vehicle decelerates to a stop in lane. **The item does not disengage**: the level-3 alerts are `ET.PERMANENT` only (`events.py:540-567`), and the lockout of TSR-611 acts only after a disengagement. Whether a stop in lane while still engaged is the SG-08 safe state is open (WP-C-03 OI-10, System FMEA SFM-ACT-005). This tree takes the forced stop as the no-response reaction, and the fact that the item stays engaged is recorded as finding F-38, not as an event.

```
TE-08 Automated control continues with an inattentive or unresponsive driver           [OR]
├── G8.1 Inattentive or unresponsive driver not detected while engaged                  [OR]
│   ├── BE-8.01 DM model false negative: eyes off the road or eyes closed classified
│   │          attentive                                                      [SOTIF]
│   ├── BE-8.02 Pose thresholds or the pose calibration wrong for the driver or the
│   │          mount (policy.py:55-83)
│   ├── G8.1.1 DM input degraded and not escalated                                      [AND]
│   │   ├── BE-8.03 Driver camera or IR illumination degraded, covered or failed, or
│   │   │          dmonitoringmodeld stopped                              (random HW)
│   │   └── G8.1.2 Degraded input does not lead to an alert                             [OR]
│   │       ├── BE-8.04 driverStateV2 always valid=True at the source
│   │       │          (dmonitoringmodeld.py:99; GAP-21, TSR-609 not met) (latent, design)
│   │       └── BE-8.05 Wheel-touch fallback resets awareness on any steering or gas
│   │                  input (policy.py:334-335; GAP-21, TSR-612 not met) (latent, design)
│   └── BE-8.06 DM demo mode (IsDriverViewEnabled) active while the item can engage:
│              the policy runs on a synthetic vehicle state (zero calibration, fixed
│              speed) and may switch the monitored seat while engaged, so a distracted
│              driver can be judged against the wrong pose reference or seat
│              (dmonitoringd.py:26-38, policy.py:256-261, 431-440; GAP-20, TSR-610)
├── G8.2 Take-over escalation too slow or not delivered                                 [OR]
│   ├── BE-8.07 Policy timers, recovery factor or exemptions misconfigured (alerts
│   │          later than 5/8/13 s; no monitoring below 10 km/h)
│   └── G-HMI (HMI hang, mute or masked alert; as SG-02)                  [CCF → DFI-25]
└── G8.3 No-response reaction does not stop the vehicle                                 [OR]
    ├── BE-8.08 noResponseForceDecel not set, or not turned into a stop: defect in the
    │          policy, controlsd or the planner (policy.py:398, controlsd.py:235,
    │          longitudinal_planner.py:84)
    └── UE-8.09 PCM does not execute the stop request (AOU-05R)
```

### 13.1 SG-08 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-08.1 | 1 | {BE-8.01} | SOTIF: a confident false negative of the DM model is not caught; the wheel-touch fallback acts only when the model is uncertain. Evaluated in WP-C-06 (SH-12), DM performance targets DMP-01…DMP-04 (WP-C-08 §5.3) |
| MCS-08.2 | 1 | {BE-8.02} | Thresholds or calibration wrong for the driver or the mount; policy unit tests use synthetic inputs only (SFM-022.C2). SFM-ACT-009 |
| MCS-08.3 | 1 (effective, both inputs of G8.1.2 latent) | {BE-8.03, BE-8.04 or BE-8.05} | A degraded or failed driver camera is never flagged invalid (GAP-21), and when the policy falls back to wheel-touch, any steering or gas input resets awareness. TSR-609, TSR-612; fault injection VS-FI-25 |
| MCS-08.4 | 1 | {BE-8.06} | Configuration single point. Corrected in v1.5: demo mode does not switch monitoring off. It runs the policy on a synthetic vehicle state with strict thresholds and no wheel-touch reset (more alerts, not fewer), but with zero calibration and without the monitored-seat lock, so the pose is judged against the wrong reference or the wrong seat can be watched (SW FMEA SWF-085). TSR-610 (GAP-20) |
| MCS-08.5 | 1 | {BE-8.07} | Escalation timing is configuration; nothing checks it at run time. TSR-608; SFM-ACT-002 |
| MCS-08.6 | 1 | {BE-2.12 or BE-2.13 or BE-2.25} | The escalation alerts are not delivered. The forced stop of G8.3 still follows, about 5 s after alert level 3, because it does not depend on the HMI. TSR-622, TSR-623 |
| MCS-08.7 | 1 | {BE-8.08} | The forced stop is software on the QM SoC with no SW FMEA mode and no test of the full path (F-37) |
| MCS-08.8 | 0 + ext. | {UE-8.09} | The PCM must execute the stop request; AOU-05R |

Every SG-08 cut set is a single point: the DM chain is one QM channel with no independent check. That is what ASIL A on a QM element (WP-C-03 §6.1 observation 3) has to address in the FSC: either ASIL A measures on the DM chain itself or an independent monitor. The FTTI of SG-08 (time from loss of attention to the no-response reaction) is not set yet (WP-C-03 OI-10); at the baseline the forced stop starts about 18 s after the driver looks away (13 s to alert 3, then 5 s).
