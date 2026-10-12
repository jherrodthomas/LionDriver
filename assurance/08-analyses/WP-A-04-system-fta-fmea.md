# WP-A-04 System-Level Safety Analyses (FTA, FMEA)

| Field | Value |
|---|---|
| Work product | WP-A-04 System-level safety analyses (FTA, FMEA) |
| Standard reference | ISO 26262-9:2018 §8 (safety analyses); ISO 26262-4:2018 §6 (safety analysis of the system architectural design, to support the TSC); ISO 21448:2022 §7 (input on insufficiencies, informative here); ASPICE 4.0 SYS.3 |
| Version | 0.4 (§9.1 computed minimal cut sets and findings CS-01…CS-07; BE-2.14 tagged latent at the baseline, as §4 states; fault tree diagrams in [fta/](fta/README.md); OI-9; 2026-10-12). 0.3 (SPF-09 and SPF-13 addressed at requirement level: TSR-516 trigger set, TSR-303, TSR-711; SG-07 FTTI; 2026-10-12) |
| Status | Draft |
| ASIL / scope | Fault trees for all seven safety goals: SG-01 (ASIL C ⚠), SG-02…SG-07 (ASIL B); system FMEA covering SG-01…SG-07. Qualitative only |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

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
│   │   │   │   └── BE-1.05 Wrong CarParams / fingerprint (CCF → DFI-09)
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
│   │   │   └── BE-1.14 MCU fault sets controls_allowed (BE-1.07 class)
│   │   └── BE-1.15 SoC commands non-zero torque (normally gated by its own engagement
│   │              state, which is fed by the same CAN data — CCF → DFI-10)
│   ├── G1.2.2 Authority not revoked after driver disengages                            [OR]
│   │   ├── BE-1.16 Brake 0x226 lost/stuck "not pressed" (no checksum, no counter,
│   │   │          timeout ≈2 s; GAP-01, GAP-06)
│   │   └── BE-1.17 0x1D2 stuck "cruise active" with valid checksum (GAP-01)
│   └── BE-1.18 Envelope bypass: ALLOUTPUT/debug mode in a DEBUG build
│              (panda/SConscript:12-20, GAP-25)                                         (SPF, config)
└── G1.3 Stale or frozen torque held beyond FTTI (HE-02.3)                              [AND]
    ├── G1.3.1 SoC stops updating but link stays alive                                 [OR]
    │   ├── BE-1.19 controlsd hang / stale modelV2 used up to ≈3.5 s (GAP-16)
    │   ├── BE-1.20 Diagnostics masked during big-model fallback (GAP-17; E-06 excluded
    │   │          from reference configuration)
    │   └── BE-1.21 SoC replays an old command buffer (no sequence counter, GAP-10)
    └── G1.3.2 Envelope does not remove torque within ≤ 0.5 s                          [OR]
        ├── BE-1.22 Heartbeat shows pandad liveness only; mismatch 3 s, loss 5 s
        │          (main.c:182-213; GAP-06, GAP-10)
        └── BE-1.23 Rate and RT limits accept a constant in-limit value (by design)
```

### 2.1 SG-01 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-01.1 | 1 + ext. | {BE-1.01, UE-1.11} | A wrong envelope limit is itself the failure; only the EPS (unverified) stands behind it. **Systematic single point** |
| MCS-01.2 | 1 + ext. | {BE-1.10, UE-1.11} | Random corruption after the TX hook, beyond the software queue. No second check on the item side. **Random single point** |
| MCS-01.3 | 1 (effective) | {SoC fault that both commands torque and changes mode/param or reflashes the MCU} = {BE-1.02/1.04 + BE-1.08/1.09 from one cause} | Dual-point in form, single-point in cause (DFI-13) |
| MCS-01.4 | 1 (effective) | {BE-1.13} | One stuck RX path feeds envelope and SoC; both "agree" the system is engaged (DFI-10) |
| MCS-01.5 | 1 | {BE-1.18} | Configuration single point: a debug build has no envelope. Controlled only by the release process ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) |
| MCS-01.6 | 2 | {BE-1.02 or BE-1.03, BE-1.06 or BE-1.07} | True dual-point: the intended envelope pattern. Requires BE-1.07 to be detected (latent-fault coverage, IWDG, ECC) to stay dual |
| MCS-01.7 | 2 | {BE-1.12, BE-1.15} | Needs counters on `0x1D2` or a plausibility check (TSR-403…TSR-405) to remove |
| MCS-01.8 | 2 | {BE-1.19 or BE-1.21, BE-1.22} | Removed only when the command-freshness timeout fits the FTTI (TSR-407…TSR-409, TSR-411) |

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
│   │   │   ├── BE-3.02 Planner/controller fault, wrong lead, e2e accel [SOTIF]/QM
│   │   │   └── G-ENV (as SG-01: BE-1.06…1.09)
│   │   ├── BE-3.03 No jerk limit in envelope: step to +2.0 m/s² allowed (GAP-04,
│   │   │          FSR-03.03 not implemented)
│   │   └── BE-3.04 Frame corrupted after TX hook (as BE-1.10)                          (SPF, random HW)
│   └── UE-3.05 PCM executes request without its own bound (AOU-05R fails)
├── G3.2 In-bound but unintended positive acceleration (e.g. toward a stationary lead)  [AND]
│   ├── BE-3.06 SoC requests positive accel in a closing situation [SOTIF]/QM
│   ├── BE-3.07 Envelope passes any in-bound value while authority is granted (by design)
│   └── UE-3.08 Driver does not brake in time (controllability; AOU-06R)
├── G3.3 Acceleration while not engaged or after driver brake                           [OR]
│   ├── G3.3.1 Authority falsely granted / not revoked                                 [OR]
│   │   ├── BE-1.12, BE-1.13, BE-1.14 (as SG-01)
│   │   └── BE-3.09 Brake 0x226 not detected (no checksum/counter, GAP-01) AND PCM does
│   │              not cancel ACC on brake (AOU-03R)                                   [AND]
│   └── BE-3.10 Inactive value check bypassed by mode/param change (e.g. param that
│              selects another brake signal or stock-longitudinal branch, toyota.h:216-248)
│              [FFI → FFI-CM-06]
├── G3.4 Gas override misinterpreted                                                    [AND]
│   ├── BE-3.11 Gas-pressed signal (PCM_CRUISE.GAS_RELEASED) stuck "pressed": envelope
│   │          then allows only inactive accel (safe direction) — or stuck "released"
│   │          while the driver presses: envelope allows accel (longitudinal.h:3-5)
│   └── UE-3.12 PCM adds item accel on top of driver pedal (to verify, AOU-05R)
└── G3.5 Stale positive acceleration held beyond FTTI                                   [AND]
    ├── BE-1.19 / BE-1.21 (stale SoC command)
    └── BE-1.22 (slow envelope detection)
```

### 3.1 SG-03 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-03.1 | 1 + ext. | {BE-3.01, UE-3.05} | Systematic single point; bound selection |
| MCS-03.2 | 1 + ext. | {BE-3.04, UE-3.05} | Random single point after TX hook |
| MCS-03.3 | 1 + ext. | {BE-3.03, UE-3.05} | Step acceleration within bound; jerk not limited in the envelope |
| MCS-03.4 | 2 + driver | {BE-3.06, BE-3.07, UE-3.08} | By design; managed by SOTIF and controllability of the bound |
| MCS-03.5 | 1 (effective) | {SoC fault → command + mode/param change} | DFI-13 |
| MCS-03.6 | 2 | {BE-3.09} (= {`0x226` undetected, PCM no cancel}) | Item side has no independent brake signal |
| MCS-03.7 | 2 | {BE-1.19/1.21, BE-1.22} | Freshness timing |

## 4. FTA — SG-02: loss or degradation of lateral control without adequate take-over warning

Diagram: [SG-02 sheet 1](fta/fta-SG-02-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-02**: lateral control is lost or degraded while the item is engaged, and the driver gets no perceivable take-over request within the SG-02 budget (≤ 1 s to warning, [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §3).

The warning branch has two inputs that must both fail: the SoC warning (QM) and the SoC-independent cues (panda siren, TSR-516; cluster cruise indicator, TSR-309). For most lateral losses the second input is always absent, because the siren fires only on heartbeat loss or an envelope-detected RX or platform fault, and the cluster cruise state does not change when lateral control alone is lost. Those paths therefore reduce to the SoC alone (SPF-09).

```
TE-02 Loss of lateral control without take-over request within ≤ 1 s                  [AND]
├── G2.1 Lateral control lost or degraded while engaged                                 [OR]
│   ├── BE-2.01 EPS drops LKA assistance (LKA fault state in 0x262)                  (UE: EPS internal)
│   ├── BE-2.02 Envelope blocks or revokes authority while the SoC shows engaged
│   │          (RX fault, stuck authority, safety-mode mismatch; HE-02.4)
│   ├── BE-2.03 Input of the lateral control law lost or stale (modelV2, calibration,
│   │          carState) and control continues on it (GAP-16)
│   ├── BE-2.04 Non-finite command clamped to 0 without a fault (controlsd.py:140-147,
│   │          GAP-19)
│   ├── BE-2.05 SoC crash or hang (whole SoC)                         [CCF → DFI-14]
│   ├── BE-2.06 Actuation frames stop reaching the bus: SoC configuration command
│   │          (0xe5, 0xde, 0xf1; FFI-CM-09), MCU hang (SFMEA-22), car-side bus-off
│   │          (SFMEA-26)                                             [FFI → FFI-CM-09]
│   └── BE-2.07 Loss of the 12 V supply to the device (FSC node N08)
└── G2.2 No adequate take-over request                                                  [AND]
    ├── G2.2.1 SoC warning missing or late                                              [OR]
    │   ├── BE-2.08 EPS fault seen only by the host, with 1.5 s hysteresis
    │   │          (car_events.py; not in the envelope, GAP-03)
    │   ├── BE-2.09 Envelope blocking detected by controlsMismatch after ≈2 s
    │   │          (selfdrived.py:338, 508-510) or not at all if pandaStates is
    │   │          stale with authority shown                         [CCF → DFI-24]
    │   ├── BE-2.10 Input loss handled as soft disable: actuation continues ≈3 s
    │   │          (events.py:853-856, state.py:7-8; GAP-16)
    │   ├── BE-2.11 Non-finite command logged only (GAP-19)
    │   ├── BE-2.12 HMI hang: render loop or audio stream stalled while processes
    │   │          stay alive (processNotRunning covers crashes only)  [CCF → DFI-25]
    │   ├── BE-2.13 Alert volume not audible (no defined minimum; FFI-CM-18)
    │   └── BE-2.05 (the SoC crash that removes control also removes its warning)
    └── G2.2.2 SoC-independent cue missing or late                                      [OR]
        ├── BE-2.14 Siren not triggered: at the baseline only on heartbeat loss (after
        │          5 s, for 3 s; main.c:193-205). TSR-516 v0.3 adds every envelope
        │          revocation that is not a driver action (incl. EPS fault, TSR-110)
        │          and a fault-induced disengagement whose ACC cancel had no effect
        │          (latent, baseline)
        ├── BE-2.15 Siren silenced with the SoC audio (shared codec or amplifier,
        │          unknown topology)                                   [CCF → DFI-23]
        └── BE-2.16 Cluster cruise indicator unchanged (no ACC cancel on the fault,
                   TSR-303) or not independent (AOU-12)                [CCF → DFI-15]
```

### 4.1 SG-02 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-02.1 | 2 (effective 1 + latent at the baseline) | {BE-2.01, BE-2.08, BE-2.14} | At the baseline BE-2.14 is permanently true for EPS faults, so an EPS fault plus the host hysteresis violates the ≤ 1 s budget. With TSR-110 and TSR-516(b) the envelope revokes and sounds the siren, so the cut set becomes {BE-2.01, BE-2.08, siren failure}: dual |
| MCS-02.2 | 2 | {BE-2.02, BE-2.09} | Envelope blocking with slow or self-reported detection. TSR-621; vehicle-response check has no TSR (WP-A-03 OI-8) |
| MCS-02.3 | 2 (effective 1 + latent at the baseline) | {BE-2.03, BE-2.10, BE-2.14} | Stale input with soft disable. TSR-601, TSR-602. With TSR-303 the disengagement cancels ACC, so the cluster changes (BE-2.16 must also occur); a cancel without effect triggers the siren (TSR-516(c)) |
| MCS-02.4 | 1 (effective) | {BE-2.04} | BE-2.11 is always true at the baseline: the loss is silent. TSR-604 (GAP-19) |
| MCS-02.5 | 1 (effective) | {BE-2.05} | One cause removes control and the SoC warning; the siren comes after 5 s. TSR-407, TSR-516 timing |
| MCS-02.6 | 2 | {any G2.1 event, BE-2.12 or BE-2.13} | HMI hang or mute. TSR-622, TSR-623 |
| MCS-02.7 | 1 + ext. | {BE-2.07} | The item cannot warn without power. The driver relies on the EPS ending LKA torque (AOU-01R) and the cluster cruise indicator (AOU-12) |

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
│   │   │   └── G-ENV (as SG-01: BE-1.06…1.09)
│   │   └── BE-4.03 Frame corrupted after the TX hook (as BE-1.10; TSR-517)  (SPF, random HW)
│   └── UE-4.04 PCM executes the request without its own bound (AOU-05R fails)
├── G4.2 Deceleration step within the bound                                            [AND]
│   ├── BE-4.05 No negative-jerk limit in the envelope: step to −3.5 m/s² allowed
│   │          (GAP-04; FSR-04.02 not implemented)
│   └── UE-4.04
├── G4.3 Unwarranted braking within the bound                                          [AND]
│   ├── BE-4.06 SoC requests braking without cause (phantom or false lead)   [SOTIF]/QM
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
└── G4.7 Deceleration step at the transition to the safe state (FSR-04.03)            [AND]
    ├── BE-4.14 Authority revoked: envelope accepts only the inactive value at once,
    │          with no ramp on the item side
    └── UE-4.15 PCM steps to the inactive value without its own ramp (AOU-05R)
```

### 5.1 SG-04 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-04.1 | 1 + ext. | {BE-4.01, UE-4.04} | Systematic single point (SPF-01) |
| MCS-04.2 | 1 + ext. | {BE-4.03, UE-4.04} | Random single point after the TX hook (SPF-02; TSR-517 specified, not implemented) |
| MCS-04.3 | 1 + ext. | {BE-4.05, UE-4.04} | Step deceleration within the bound. TSR-205 (GAP-04) |
| MCS-04.4 | 2 + traffic | {BE-4.06, BE-4.07, UE-4.08} | By design; managed by SOTIF and the controllability of the bound |
| MCS-04.5 | 2 | {BE-4.09, BE-4.10 or BE-2.12/2.13} | Unannounced item braking. TSR-624, TSR-622, TSR-623 |
| MCS-04.6 | 1 + driver | {BE-4.11, UE-4.12} | QM SoC only; FSR-04.06 carries ASIL A on a QM element (WP-C-04 OI-9) |
| MCS-04.7 | 2 | {BE-1.12 or BE-1.13 or BE-1.14, BE-4.13} | As MCS-01.4/01.7 for the longitudinal path |
| MCS-04.8 | 1 + ext. | {BE-4.14, UE-4.15} | Item side cannot ramp after revocation. PCM coasting behaviour to verify (TSR-208) |

## 6. FTA — SG-05: no release on driver brake, cancel or steering override

Diagram: [SG-05 sheet 1](fta/fta-SG-05-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-05**: the item keeps actuating, or opposes the driver, longer than the SG-05 FTTI (≤ 0.2 s) after a driver brake press, a cancel or main-switch-off, a steering override or an accelerator press; or the driver believes the item is disengaged while it actuates (mode confusion, H-07).

```
TE-05 Item does not release on driver action                                           [OR]
├── G5.1 No release on brake press                                                      [AND]
│   ├── G5.1.1 Envelope does not see the brake (safety.h:354-356)                       [OR]
│   │   ├── BE-5.01 0x226 lost or stuck "not pressed" (no checksum or counter, timeout
│   │   │          ≈2 s; GAP-01, GAP-06) (= BE-1.16)
│   │   └── BE-5.02 MCU fault keeps controls_allowed (BE-1.07, BE-1.14 class)
│   └── G5.1.2 Cruise-inactive path does not revoke (safety.h:520-521)                  [OR]
│       ├── BE-5.03 0x1D2 stuck "cruise active" with valid checksum (= BE-1.17)
│       ├── BE-5.02
│       └── UE-5.04 PCM does not drop cruise on brake (AOU-03R)
│   (CCF → DFI-10: one stuck RX path, BE-1.13, causes BE-5.01 and BE-5.03 together)
├── G5.2 No release on cancel or main switch off                                        [OR]
│   ├── BE-5.03
│   └── BE-5.02
├── G5.3 LKA torque opposes the driver's steering                                       [AND]
│   ├── BE-5.05 No driver-override check on the LKA path in the envelope (GAP-02;
│   │          host-only MAX_USER_TORQUE 500, carcontroller.py:33, 83)  (latent, design)
│   ├── BE-5.06 Host override check fails or SoC fault (QM)
│   └── UE-5.07 EPS does not let the driver overpower LKA torque (AOU-02R)
├── G5.4 Accelerator does not override commanded deceleration                         [AND]
│   ├── BE-5.08 GAS_RELEASED stuck "released" while the driver presses (= BE-3.11);
│   │          the envelope then allows non-inactive values (longitudinal.h:3-5)
│   └── UE-5.09 PCM does not give the driver's pedal priority (AOU-05R)
└── G5.5 Mode confusion: driver believes the item is disengaged while it actuates      [AND]
    ├── BE-5.10 Item HMI shows the wrong state, or cruiseMismatch raised after 6 s
    │          with no reaction (selfdrived.py:420-422, events.py:458-460; GAP-19)
    └── BE-5.11 Cluster cruise indicator not an independent cue (AOU-12 fails;
               item TX 0x412 affects the cluster)                     [CCF → DFI-15]
```

### 6.1 SG-05 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-05.1 | 1 (effective) | {BE-1.13} | One stuck RX path hides both brake and cruise-inactive (DFI-10). TSR-404, TSR-405(b) |
| MCS-05.2 | 2 | {BE-5.01, BE-5.03} | Two independent RX faults; E2E or plausibility needed on both (TSR-401…TSR-406) |
| MCS-05.3 | 2 | {BE-5.01, UE-5.04} | Brake undetected and PCM keeps cruise; AOU-03R |
| MCS-05.4 | 1 (effective) | {BE-5.02} | MCU execution fault. TSR-501, TSR-503 |
| MCS-05.5 | 1 + ext. | {BE-5.05 (latent), BE-5.06, UE-5.07} | The envelope adds nothing for steering override today (SPF-12). TSR-304 |
| MCS-05.6 | 1 + ext. | {BE-5.08, UE-5.09} | Single gas signal, no plausibility |
| MCS-05.7 | 2 | {BE-5.10, BE-5.11} | Mode confusion. TSR-308, TSR-309 and AOU-12 verification |

## 7. FTA — SG-06: loss of longitudinal deceleration without take-over warning

Diagram: [SG-06 sheet 1](fta/fta-SG-06-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-06**: the item stops decelerating while engaged when the situation needs it (lead ahead, stop), and the driver gets no take-over request within ≤ 1 s.

```
TE-06 Loss of longitudinal deceleration without take-over request                     [AND]
├── G6.1 Deceleration not commanded or not executed while needed                        [OR]
│   ├── BE-6.01 Plan, lead or model input lost or stale (radarFault, commIssue;
│   │          GAP-16)
│   ├── BE-6.02 Envelope blocks longitudinal authority while the SoC shows engaged
│   ├── BE-6.03 PCM does not execute ACC (ACC or cruise fault)
│   ├── BE-6.04 Non-finite accel clamped to 0 without a fault (GAP-19)
│   ├── BE-6.05 Stale zero or positive accel held (BE-1.19, BE-1.21)
│   ├── BE-2.05 SoC crash or hang                                     [CCF → DFI-14]
│   └── BE-2.06 Actuation frames stop (configuration command, MCU hang, bus-off)
└── G6.2 No adequate take-over request                                                  [AND]
    ├── G6.2.1 SoC warning missing or late                                              [OR]
    │   ├── BE-2.09, BE-2.10, BE-2.11 (as SG-02)
    │   ├── BE-2.12, BE-2.13 (HMI hang or mute)                       [CCF → DFI-25]
    │   └── BE-2.05
    └── G6.2.2 SoC-independent cue missing or late                                      [OR]
        ├── BE-2.14, BE-2.15 (siren not triggered or silenced)
        └── BE-6.06 PCM cruise stays active, so the cluster shows no change
```

### 7.1 SG-06 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-06.1 | 2 (effective 1 + latent) | {BE-6.01, BE-2.10, BE-2.14} | Soft disable keeps the stale command ≈3 s. TSR-601, TSR-602 |
| MCS-06.2 | 2 | {BE-6.02, BE-2.09} | As MCS-02.2 |
| MCS-06.3 | 2 | {BE-6.03, BE-2.12 or BE-2.13} | `accFaulted` is an immediate disable (`events.py:908`); fails only with the HMI |
| MCS-06.4 | 1 (effective) | {BE-6.04} | Silent loss. TSR-604 (GAP-19) |
| MCS-06.5 | 1 (effective) | {BE-2.05} | As MCS-02.5 |
| MCS-06.6 | 2 | {BE-6.05, BE-1.22} | As MCS-01.8 for the longitudinal path |

## 8. FTA — SG-07: suppression, delay or alteration of the stock PCS/AEB

Diagram: [SG-07 sheet 1](fta/fta-SG-07-1.svg) (all sheets: [fta/](fta/README.md)).

Top event **TE-07**: a stock PCS or AEB intervention of the Toyota system is prevented, delayed or altered because of the item. The preliminary FTTI for loss of forwarding is 0.2 s ([WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) §3.6), and content alteration is a per-frame property. The tree treats any loss of the camera-to-car path while the relay intercepts, for longer than the FTTI, as the top event.

```
TE-07 Stock PCS/AEB suppressed, delayed or altered                                     [OR]
├── G7.1 Camera-side PCS frames not forwarded while the relay intercepts                [OR]
│   ├── BE-7.01 MCU hang with the relay energised (no IWDG; GAP-07, GAP-43)    (SPF-06)
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
│   └── BE-7.08 SoC sends such a frame (QM fault or compromise)       [FFI → FFI-CM-05]
├── G7.3 Relay held in intercept while forwarding is not running                        [AND]
│   ├── BE-7.09 Relay welded or driven without forwarding (no readback; GAP-12) (SPF-07)
│   └── BE-7.10 Forwarding not running (device off, MCU in reset or bootloader)
├── G7.4 Harness cuts the stock path                                                    [OR]
│   ├── BE-7.11 Connector intermittent or partly seated (SFMEA-30; DFI-05, DFI-20)
│   └── BE-7.12 Passive camera-to-car path broken in the harness (TSR-702)
└── G7.5 PCM gives the item's ACC request priority over PCS braking                     [AND]
    ├── BE-7.13 Item sends an ACC request during a PCS event
    └── UE-7.14 PCM arbitration does not prioritise PCS (AOU-04R fails)
```

### 8.1 SG-07 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-07.1 | 1 | {BE-7.01} | Random single point. TSR-501, TSR-502, TSR-706 |
| MCS-07.2 | 1 | {BE-7.02} | One QM command. TSR-513 |
| MCS-07.3 | 1 | {BE-7.03} | As MCS-07.2 |
| MCS-07.4 | 1 | {BE-7.04} | Needs the forwarding timing analysis and overflow reaction (TSR-707) |
| MCS-07.5 | 1 | {BE-7.05} | Systematic; verified by T-HIL of the forwarding set (TSR-704) |
| MCS-07.6 | 1 | {BE-7.06} | Random single point at the baseline; forwarding supervision with relay release (TSR-711) makes it dual with the supervision |
| MCS-07.7 | 1 (effective) | {BE-7.08} | BE-7.07 is a permanent latent condition at the baseline. TSR-705 |
| MCS-07.8 | 2 | {BE-7.09, BE-7.10} | TSR-506 readback |
| MCS-07.9 | 1 | {BE-7.11} | Installation and harness design (TSR-701, TSR-703, TSR-805) |
| MCS-07.10 | 1 + ext. | {BE-7.13, UE-7.14} | AOU-04R vehicle test |

## 9. Single points of failure and cut-set observations

| ID | Observation | SG | Type | Required measure | TSR / GAP |
|---|---|---|---|---|---|
| SPF-01 | **Limit values are a systematic single point.** Nothing in the item checks that the envelope limits are themselves controllable; the controller uses the same numbers (DFI-08) | SG-01, SG-03, SG-04 | Systematic | Physically derived limits with recorded rationale; controllability test; controller margin | TSR-102, TSR-103, TSR-201, TSR-202, TSR-204, TSR-205, TSR-605; GAP-04 |
| SPF-02 | **No integrity check between the FDCAN load and the bus.** The software TX queue is covered by the packet XOR checked before loading (`panda/board/drivers/fdcan.h:100`; a failed check drops the frame). A random fault in the copy into FDCAN message RAM, the message RAM, the FDCAN core or the transceiver changes an already-approved frame undetected | SG-01, SG-03, SG-04 | Random HW | RAM/FDCAN-RAM ECC enabled with reaction; option: TX read-back of own frames from the bus (FDCAN RX of own TX) compared with the approved frame | TSR-503 (RAM ECC) only; **no TSR for post-hook TX integrity** (OI-6); FMEDA WP-H-03 |
| SPF-03 | **SoC can disable or replace its own monitor** (mode/param, boot pins, softloader). Any SoC fault (or compromise) is effectively a single point | All | Common cause / FFI | Safety-mode lock, command rejection in car modes, RDP/WRP, signature | TSR-511…TSR-514; GAP-09, GAP-24, GAP-38 |
| SPF-04 | **Single RX path for both monitor and controller.** The SoC receives vehicle CAN through the panda; a stuck RX path or stuck vehicle frame misleads both | SG-01, SG-03, SG-05 | Common cause | E2E/plausibility on gating signals in the envelope | TSR-401…TSR-406; GAP-01 |
| SPF-05 | **Debug build has no envelope** (ALLOUTPUT, debug key) | All | Configuration | Release-only firmware, build-type check at start-up reported to SoC and enforced | TSR-514, TSR-802; GAP-25 |
| SPF-06 | **MCU hang leaves the relay energised** (GAP-43) with no hardware watchdog. Torque stops (EPS timeout, AOU-01R), but the stock PCS path stays cut if forwarding stops | SG-07 (and SG-02 without warning) | Random HW | IWDG (TSR-501); fault reaction (TSR-502); relay to stock path on fault/reset (TSR-706) | GAP-07, GAP-43 |
| SPF-07 | **Relay welded in intercept position** is not detected (no readback) | SG-07 | Random HW | Relay readback (TSR-506) | GAP-12 |
| SPF-08 | **QM command `0xe7` (power save) in car mode** stops camera-side forwarding with the relay energised (by code reading, WP-A-02 FFI-CM-08) | SG-07 | FFI | Reject in car modes | TSR-513; WP-S-02 NF-05 |
| SPF-09 | **SG-02/SG-06 warnings for SoC-detected faults rested on the QM SoC alone.** At v0.2 TSR-516 named only heartbeat loss and envelope-detected RX or platform faults. **Addressed at requirement level in WP-S-02 v0.3:** TSR-516(b) sounds the siren on every envelope revocation that is not a driver action, including an EPS fault (TSR-110); TSR-303 makes every fault-induced disengagement cancel ACC, so the cluster cruise state changes; TSR-516(c) sounds the siren when that cancel has no effect. Not implemented; the cluster cue rests on AOU-12 | SG-02, SG-06 | Common cause / design | As stated; vehicle check of the cluster and PCM cues on a forced cancel (AOU-12) | TSR-516, TSR-303 (OI-7 closed) |
| SPF-10 | **Non-finite actuator command is replaced by 0 silently** | SG-02, SG-06 | Systematic (design) | Treat as a fault with take-over request | TSR-604; GAP-19 |
| SPF-11 | **SoC crash removes control and the SoC warning together**; the independent siren comes after 5 s | SG-02, SG-06 | Common cause (DFI-14) | Heartbeat timeout and siren within the warning budget | TSR-407, TSR-516; GAP-06 |
| SPF-12 | **No driver steering override check in the envelope** on the LKA path; release rests on the QM host check and the EPS (AOU-02R) | SG-05 | Design | Driver-override check and torque reduction in the envelope | TSR-304; GAP-02 |
| SPF-13 | **Camera-to-car forwarding is single-channel with no supervision that releases the relay.** An MCU hang, a camera-side bus fault, a QM configuration command or queue overflow stops PCS forwarding while the relay intercepts | SG-07 | Random HW / FFI | IWDG (≤ 0.1 s) and relay release on fault; reject configuration commands in car modes; forwarding supervision with relay release within the SG-07 budget | TSR-501, TSR-502, TSR-513, TSR-706, TSR-707, TSR-711 (added in WP-S-02 v0.3) |
| Obs-01 | MCS-01.6 is the only truly dual-point cut set that the envelope pattern intends. It stays dual only if MCU faults (BE-1.07) are detected; today there is no IWDG, MPU or ECC reaction, so latent MCU faults can accumulate | SG-01 | Latent | Latent-fault diagnostics at start-up and run time | TSR-501, TSR-503, TSR-507 |
| Obs-02 | Every SG-01, SG-03 and SG-04 path ends in an EPS or PCM AND-input (UE-1.11, UE-3.05, UE-4.04). These are unverified AoUs. The trees must not be read as "dual" until AOU-01R/AOU-05R are verified | SG-01, SG-03, SG-04 | AoU | Vehicle characterisation (WP-S-09) | GAP-05 |
| Obs-03 | SG-07 had no numeric FTTI. [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) v0.2 §3.6 sets a preliminary 0.2 s for loss of forwarding (FDTI ≤ 0.1 s, FRTI ≤ 0.1 s, zero margin), which tightened the watchdog timeout (TSR-501) to ≤ 0.1 s and added forwarding supervision (TSR-711) | SG-07 | Timing | Measure the PCS timing and confirm the FTTI (WP-S-04 OI-4, OI-7) | RR-2026-004 F-04; RR-2026-005 F-02 |
| Obs-04 | Many SG-02 and SG-06 cut sets are order 2 in form but contain a condition that is always true at the baseline (BE-2.14, BE-2.11). They are marked "effective 1 + latent": removing the latent condition is what makes them dual | SG-02, SG-06 | Latent | As SPF-09, SPF-10 | — |

### 9.1 Computed minimal cut sets (check of the tables)

The cut-set tables in §2…§8 were written by hand. [`fta/fta_cutsets.py`](fta/fta_cutsets.py) computes the minimal cut sets of each tree from its gate logic as written (OR = union, AND = product, absorption; transfers expanded, repeated events one variable) and checks every table row against them. The full result is [`fta/cut-sets.md`](fta/cut-sets.md); CI keeps it current. An event tagged `(latent, …)` or described as "by design" is taken as present at the baseline, so a row that omits only such events is accepted as an *effective* order.

| Goal | Computed cut sets | Effective order ≤ 1 | Table rows matching or effective | Rows needing attention |
|---|---|---|---|---|
| SG-01 | 30 | 8 | 5 of 8 | MCS-01.4 (argued, DFI-10), MCS-01.6 (MCS-01.3 in words) |
| SG-02 | 111 | 1 | 4 of 7 | MCS-02.4 (argued), MCS-02.6, MCS-02.7 |
| SG-03 | 16 | 10 | 6 of 7 | — (MCS-03.5 in words) |
| SG-04 | 17 | 6 | 8 of 8 | — |
| SG-05 | 6 | 5 | 5 of 7 | MCS-05.1 (DFI-10 note), MCS-05.2 |
| SG-06 | 93 | 1 | 4 of 6 | MCS-06.4 (argued), MCS-06.6 |
| SG-07 | 11 | 10 | 10 of 10 | — |

Findings. None of them changes a requirement; each needs an analyst decision on the tree or the table (OI-9).

| ID | Finding | Goal | Proposed resolution |
|---|---|---|---|
| CS-01 | **`BE-1.16` and `BE-1.17` are single-event cut sets of TE-01** (G1.2.2 is a direct OR input, with no AND on the SoC commanding torque), but they are in neither the table nor the SPF list. Physically the SoC reads the same frames (DFI-10), so it keeps commanding torque: the single point is plausible | SG-01 | Either AND G1.2.2 with BE-1.15 and argue effective order 1 through DFI-10 (as MCS-01.4), or add both as single points under SPF-04. Measure: TSR-401…TSR-406 |
| CS-02 | **G1.3.2 is always true at the baseline**: its OR input BE-1.23 (rate limits accept a constant in-limit value) is by design. A stale SoC command (BE-1.19, BE-1.20 or BE-1.21) alone therefore holds torque beyond the FTTI. MCS-01.8 states order 2 with BE-1.22 and misses this | SG-01 | BE-1.23 explains why only freshness detection (BE-1.22) can catch a stale value; make it a condition, not an OR alternative, or record the effective single point as an SPF. Measure: TSR-407…TSR-409, TSR-411 |
| CS-03 | **MCS-01.6 omits UE-1.11** (the EPS limit is an AND input to G1.1), so its order is "2 + ext.", as Obs-02 says in words. The table also lists only BE-1.02/BE-1.03 against BE-1.06/BE-1.07; the tree gives the same pattern for BE-1.04 and BE-1.05 (DFI-09) and for BE-1.08/BE-1.09 (MCS-01.3). SG-03 and SG-04 have the same G-ENV pairs (BE-3.02, BE-4.02 × BE-1.06…BE-1.09) with no table row | SG-01, SG-03, SG-04 | Correct the order and list the G-ENV pattern once per goal |
| CS-04 | **SG-03 and SG-04 model "not engaged" differently.** In SG-03, false authority (BE-1.12, BE-1.13, BE-1.14) and a mode or param bypass (BE-3.10) are single-event cut sets of TE-03 (G3.3 has no AND on the SoC sending acceleration). SG-04 G4.6 ANDs the same events with BE-4.13. Also missing from the tables: {BE-3.11, UE-3.12} (gas signal stuck "released" and the PCM adds the item's acceleration) and {BE-3.10, BE-4.13} | SG-03, SG-04 | Model both goals alike (AND with an SoC command event, effective order argued through DFI-10/DFI-13), then add the rows. Measures: TSR-401…TSR-406, TSR-513 |
| CS-05 | **The SG-02 and SG-06 trees AND two independent OR branches**, but most warning failures in G2.2.1/G6.2.1 belong to one loss cause only (BE-2.08 to an EPS fault, BE-2.10 to input loss, BE-2.11 to a non-finite command). The logic therefore yields 111 and 93 cut sets, most of them meaningless (e.g. {BE-2.01, BE-2.11, BE-2.14}). Obs-04 treats BE-2.11 as always true; in this structure that would make every lateral loss a single point, which overstates the gap. BE-2.07 (power loss) removes every warning itself, which the tree does not show (MCS-02.7) | SG-02, SG-06 | Restructure per cause: each loss cause ANDed with its own warning-failure branch, and BE-2.05/BE-2.07 linked to the warning branch as common causes. Only BE-2.14 is tagged latent in this version |
| CS-06 | **`BE-5.03` alone is a cut set of TE-05** through G5.2 (no release on cancel or main switch off), so MCS-05.2 {BE-5.01, BE-5.03} is not minimal and the single point is missing. MCS-05.1 and MCS-06.6 name events that are not in their trees (BE-1.13 through the DFI-10 note; BE-1.22, while the SG-06 tree has no envelope-detection leg for BE-6.05) | SG-05, SG-06 | Add {BE-5.03} under SPF-04 (TSR-401…TSR-406); add the detection leg to G6.1 or drop BE-1.22 from MCS-06.6 |
| CS-07 | **`BE-7.12` (passive camera-to-car path broken in the harness) is a single-event cut set** of TE-07 with no table row | SG-07 | Add the row; measure TSR-702 |

## 10. System FMEA

Severity of the vehicle effect is expressed by the affected SG. Detection = mechanism that detects the failure mode in the item today. Columns: **Mech.** = safety mechanism that reaches the safe state; **Gap** = what is missing.

| ID | Element | Failure mode | Effect (local → vehicle) | SG | Detection (today) | Mechanism (today) | Gap / required |
|---|---|---|---|---|---|---|---|
| SFMEA-01 | E-01 controlsd | Excessive torque command | Torque above intent → lateral deviation | SG-01 | Envelope per-frame limits (`lateral.h:60-151`) | Frame dropped; `controls_allowed` not cleared by TX violation alone | FSR-01.12: revoke on TX violation (TSR-108, TSR-109) |
| SFMEA-02 | E-01 controlsd | Output frozen (hang) | Last command repeated by card/pandad or no command | SG-01, SG-02 | selfdrived `processNotRunning`/`commIssue` (QM); panda heartbeat 3–5 s | Soft disable keeps actuating 3 s (GAP-16); SILENT after 5 s | Freshness check ≤ 0.3 s in envelope (TSR-408, TSR-409; host TSR-602); GAP-06, GAP-10 |
| SFMEA-03 | E-01 controlsd | Non-finite output | Clamped to 0 silently (`controlsd.py:140-147`) → loss of control without warning | SG-02, SG-06 | Logged only | None | FSR-06.04 (TSR-604); GAP-19 |
| SFMEA-04 | E-01 card | Sends `0x343` positive accel while engaged and lead close | Unintended acceleration | SG-03 | None if in bound | Envelope bound +2.0 m/s² | Jerk limit (FSR-03.03, TSR-204); bound rationale |
| SFMEA-05 | E-01 card / pandad | Sends PCS messages `0x344`/`0x411` (or DSU-only IDs, WP-S-02 NF-07) | Stock PCS altered | SG-07 | None | Whitelist allows them | FSR-07.02 (TSR-705; GAP-42) |
| SFMEA-06 | E-01 pandad | Sets wrong safety mode/param | Envelope misconfigured | All | Host cross-check after 10 s (QM, same source) | Mode change clears authority | Safety-mode lock (TSR-512); GAP-09 |
| SFMEA-07 | E-01 pandad | Heartbeat continues while controls loop is dead | Envelope keeps authority | SG-01, SG-02 | 3 s mismatch only if `engaged` flag drops | — | Heartbeat bound to control loop (TSR-409); GAP-10 |
| SFMEA-08 | E-01 selfdrived | Engaged state differs from PCM (`cruiseMismatch`) | Mode confusion | SG-05, SG-02 | Event raised after 6 s, no reaction (`events.py:458-460`) | None | FSR-05.06 (TSR-308); GAP-19 |
| SFMEA-09 | E-01 HMI (ui/soundd) | No take-over warning (crash) | Unannounced loss | SG-02, SG-06 | panda siren after heartbeat loss | Siren 3 s after 5 s | FSR-02.05 timing (TSR-516; SoC TSR-606); DFI-14 |
| SFMEA-10 | E-01 DM chain | DM inactive / demo mode | Inattention undetected | (SG-02/06 controllability) | `dmonitoringd` validity → `commIssue` | Soft disable | FSR-02.08 (QM, SOTIF); GAP-20, GAP-21 |
| SFMEA-11 | E-02 driving model | Wrong curvature / accel | Unintended manoeuvre within bounds | SG-01, SG-03 [SOTIF] | Excessive-actuation latch (2× ISO limits, `selfdrive/selfdrived/helpers.py`) | Soft disable + no-entry | SOTIF (WP-C-06); bounded by envelope |
| SFMEA-12 | E-03 safety hooks | Software defect in limit check | Excess passes | SG-01, SG-03, SG-04 | Unit/mutation tests (design-time) | — | ASIL-level verification (MC/DC, target tests) GAP-13 |
| SFMEA-13 | E-03 RX checks | Stuck/replayed `0x1D2`/`0x226` frames accepted | False authority / no revocation | SG-01, SG-03, SG-05 | Checksum (`0x1D2` only), timeout ≈2 s | `controls_allowed` cleared on checksum fail or timeout | E2E/plausibility, ≤ 0.3 s (TSR-401…TSR-406); GAP-01, GAP-06 |
| SFMEA-14 | E-03 driver-torque handling | Driver steering override not detected in envelope | Torque opposes driver | SG-05 | Host only (`carcontroller.py:33, 83`) | EPS (assumed) | FSR-05.03 (TSR-304); GAP-02 |
| SFMEA-15 | E-03 EPS status | EPS LKA fault not seen by envelope | Unannounced loss | SG-02 | Host only (`carstate.py:122-127`) | Host soft/immediate disable | FSR-02.01 (TSR-110); GAP-03 |
| SFMEA-16 | E-03 tick / heartbeat | Tick ISR starved or stopped | No timeout detection, no siren | SG-01, SG-02 | Interrupt-rate fault (report-only) | None | IWDG (TSR-501); fault reaction (TSR-502); GAP-07, GAP-08 |
| SFMEA-17 | E-03 TX path after hook | Frame bit flip in queue or message RAM | Approved frame altered | SG-01, SG-03, SG-04 | Software queue: packet XOR (host-computed, carried through the hook) checked at FDCAN load (`fdcan.h:100`), frame dropped on mismatch. FDCAN message RAM, core, transceiver: none | Frame drop (queue only) | SPF-02 measures (TSR-503 partly; no TSR, OI-6) |
| SFMEA-18 | E-03 SPI link | Corrupted command passes 8-bit XOR | Wrong CAN frame or wrong control command | All | XOR, NACK | TX hook limits (frames); none for control commands | CRC + counter (TSR-410, TSR-413); GAP-10 |
| SFMEA-19 | E-03 SPI link | Length field above buffer size | DMA overrun into SRAM1/2 | All (potential) | None | Memory-bank separation (unconfirmed) | Length bound (TSR-412; WP-S-02 NF-04); WP-A-02 FFI-SP-02 |
| SFMEA-20 | E-03 forwarding | Camera-side forwarding stops (power-save command, bus-2 fault) with relay energised | Stock PCS suppressed | SG-07 | None in envelope | — | Reject `0xe7` in car modes; forwarding supervision (TSR-513, TSR-707); WP-A-02 FFI-CM-08 |
| SFMEA-21 | E-03 relay malfunction detection | Detection 1–2 s, one direction only | Camera commands reach car / PCS path cut undetected | SG-01, SG-07 | Traffic-based (`safety.h:215-220, 372-380`) | Block all TX | Readback (TSR-506); GAP-12 |
| SFMEA-22 | E-04 MCU core | Hang (no IWDG) | Relay stays energised; TX stops | SG-07, SG-02 | None | EPS timeout (AOU-01R) | TSR-501, TSR-502, TSR-706; GAP-07, GAP-43 |
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
| SFMEA-38 | E-03 TX path | Actuation frames sent faster than nominal (in-limit burst) | Rate limits applied per frame, not per time | SG-01, SG-03, SG-04 | None | Per-frame limits | TSR-518 |
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
| OI-9 | Resolve CS-01…CS-07 (§9.1): decide the tree structure for G1.2.2, G1.3.2, G3.3 and SG-02/SG-06, then update the trees and tables and rerun `fta/fta_cutsets.py` | Safety engineer | G2 |
