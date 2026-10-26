# LionDriver — FMEA Program Plan

**Status:** Draft v0.31 (System FMEA rev 0.33: SFM-005.C2 and SFM-006.C1 record the panda siren on a SoC stall, DQ-404, after BL-006, ratings unchanged; 2026-10-21). v0.30 (SW FMEA rev 1.8: engaged-mismatch 0.3 s and siren cases TSR-516(b)/(c) since panda f4803c5, text only, re-rating pending against the next baseline; 2026-10-21). v0.28 (FMEDA rev 0.7: targets per goal, SG-05 estimate, review pages and committed workbooks; Figures 3-10/3-11 per goal; 2026-10-20). v0.27 (§3.1 Figure 3-17: each card also names the fault-tree events and gates it backs, per goal, from [fta-fmea-map.yaml](../fta-fmea-map.yaml); no analysis content changed; 2026-10-19). v0.26 (§3.1 Figure 3-17: one card per System FMEA failure mode, three sheets, drawn by `tools/safety/fmea_cards.py`; no analysis content changed; 2026-10-19). v0.25 (System FMEA rev 0.32: SFM-ACT-020 evidence cites the CI unit-test run and the opendbc e233362 cap, ratings unchanged; 2026-10-19). v0.24 (System FMEA rev 0.31: SFM-ACT-020 completed for the host code by #292, not in BL-006, ratings unchanged; 2026-10-19). v0.23 (RT-3: handbook MSR AP table for S 9–10, DQ-207 A; System FMEA rev 0.30 and DFMEA rev 0.10 re-rate five F 2 MSR rows H → M; 2026-10-19). v0.22 (msr-plan v0.10 and rating-tables §7.4: DQ-206 A, an MSR row closes a cause only with measured timing inside the FTTI; 2026-10-19). v0.21 (System FMEA rev 0.29: SFM-ACT-020 open per DQ-300 A; 2026-10-18). v0.20 (System FMEA rev 0.28: SFM-034 cites SWF-090, SFM-038.C1 matches SWF-088 at BL-006; 2026-10-17). v0.19 (baseline BL-006 proposed: liondriver-dev `c61e31b`, panda `0a7da85`, opendbc `62b89a3`; System FMEA rev 0.27 moves to BL-006 and re-rates SFM-038.C1, the other analyses stay on their baselines; 2026-10-17). v0.18 (System FMEA rev 0.26: SFM-018.C3, the panda-side override cause, linked to SWF-087; 2026-10-17). v0.17 (System FMEA rev 0.25: SFM-ACT-023 completed for the code by #174, predicted ratings only; host part split into SFM-ACT-024; 2026-10-17). v0.16 (System FMEA rev 0.19: steering-override and N-3 simulation evidence, no rating credit; 2026-10-16). v0.15 (System FMEA rev 0.18: SFM-025.C1 linked to SWF-062.C1; 2026-10-16). v0.14 (System FMEA rev 0.17: 17 host-software causes linked to the SW FMEA P2/P3 rows and their BL-005 ratings; 2026-10-16). v0.13 (System FMEA rev 0.16: SFM-016.C2 and SFM-029.C1 follow the SW FMEA BL-005 ratings; ODD up to 110 km/h; 2026-10-16). v0.12 (System FMEA rev 0.15: monitoring actions linked to their TSRs, warning paths compared with WP-S-04 §3.8; 2026-10-16). v0.11 (Figure 4-2, the FMEA-MSR overview, msr-plan M3; 2026-10-16). v0.10 (baseline BL-005 proposed: liondriver-dev `1033d98`, the reference build the default; System FMEA rev 0.9 re-rates its MSR rows at BL-005, the other analyses stay on their baselines; 2026-10-16). v0.9 (SG-04 FTA↔FMEA findings F-1…F-10 resolved: SW FMEA rev 0.7 adds SWF-003.C3 and SWF-050…053, DFMEA rev 0.3 adds DFM-019, System FMEA rev 0.6 and PFMEA rev 0.3 add HZ-006 effects, HARA rev 0.4 back-links SFM-026, FSC rev 0.3 re-based; [fta-fmea-mapping.md](../fta-fmea-mapping.md); 2026-10-13). v0.8 (DFA rev 0.5: the seven insufficient initiators re-checked against the reference build; 2026-10-13). v0.7 (generated FMEA, FMEDA and DFA figures, Figures 2-1, 3-1…3-11, 4-1; 2026-10-13). v0.6 (§1 flow diagram redrawn as Figure 1-1; text version kept; 2026-10-13) — Phase 0 complete; System FMEA rated (rev 0.5, BL-004); SW FMEA P1 elements rated (rev 0.6, BL-004); HARA draft rev 0.3
**Scope:** reference configuration CFG-001 (AC-001), Corolla E210 · ZRE212 · US: US sedan, model years 2020–2022, 1.8 L CVT ([vehicle register](../../../docs/liondriver/vehicles/README.md)); comma 3X (`system/hardware/tici`) with integrated panda, current LionDriver software baseline
**Covers:** System FMEA, DFMEA, PFMEA, SW FMEA, FMEDA

> **Location:** moved from `docs/safety/` on 2026-10-10. `assurance/` is the source of truth. This folder is supporting data for [WP-W-04](../../05-software/WP-W-04-software-safety-analysis.md), [WP-A-03](../WP-A-03-dependent-failure-analysis.md) and [WP-A-04](../WP-A-04-system-fta-fmea.md). Its HARA, FSC and item definition are parallel drafts that were not adopted; see the [reconciliation §7](../../00-assessment/docs-safety-reconciliation.md#7-second-set-aiag-vda-analyses-assurance08-analysesfmea).

> No safety claim is made by this plan. It defines *how* the failure analyses will be performed, what they consume, and what they produce.

---

## 1. Why five analyses, and how they relate

| Analysis | Question it answers | Level | Method basis | Primary output |
|---|---|---|---|---|
| **System FMEA** (the "FMEA") | How can the *function* (ACC + ALC + DM) fail, and what does the vehicle/driver experience? | Item / vehicle | AIAG-VDA 2019 (7-step), ISO 26262-9 §8 (qualitative) | Functional failure modes → effects → link to hazards (HARA) |
| **DFMEA** | How can the *hardware design* fail? | comma 3X, panda, harness, vehicle interfaces | AIAG-VDA 2019 DFMEA | HW failure modes, design controls, actions |
| **SW FMEA** | How can *software elements* fail (value, timing, omission, commission)? | Processes / modules / safety code | AIAG-VDA 2019 adapted + SAE J1739 SW guidewords, ISO 26262-6 §7.4.10 | SW failure modes, required safety mechanisms, test cases |
| **PFMEA** | How can the *process* that produces the deployed configuration fail? | Build → release → install → calibration → OTA | AIAG-VDA 2019 PFMEA | Process controls, install/release checklist (control plan) |
| **FMEDA** | Do the HW safety mechanisms achieve the ASIL target quantitatively? | Safety-relevant HW parts (panda MCU path first) | ISO 26262-5 §8–9, ISO 26262-11 | λ per part, SPFM, LFM, PMHF |

**Flow of information**

![Figure 1-1: flow of information from Item Definition, HARA, Safety Goals, FSC and TSC to System FMEA, DFMEA, SW FMEA, FMEDA and DFA/FTA, and from PFMEA to the release and install control plan](figures/fig-plan-1-1-analysis-flow.svg)

*Figure 1-1.* The concept chain runs along the top; the five analyses of this plan have dark outlines and the teal arrows carry information between them. Source: [`figures/fig-plan-1-1-analysis-flow.svg`](figures/fig-plan-1-1-analysis-flow.svg); change it together with the table above and §3.

<details><summary>Text version of Figure 1-1</summary>

```
Item Definition ─► HARA ─► Safety Goals (ASIL) ─► FSC ─► TSC / Architecture
                     ▲                                      │
                     │ effects                              ▼
               System FMEA ◄──────── causes ──────── DFMEA   SW FMEA
                                                      │         │
                                                      ▼         ▼
                                                    FMEDA     DFA / FTA
PFMEA ─► Release / install control plan  (feeds "configuration as assured")
```

</details>

- System FMEA **effects** must trace to HARA hazards; its **causes** become the failure modes of DFMEA / SW FMEA.
- FMEDA reuses DFMEA hardware failure modes but **requires safety goals and ASIL** — it cannot be finalized before HARA.
- SW FMEA findings that share a root cause across redundant paths feed the Dependent Failure Analysis.

---

## 2. Prerequisites (gating)

| Prereq | Needed by | Status |
|---|---|---|
| Item definition & boundary (README roadmap item 2) | All | **Withdrawn** 2026-10-22 (DQ-124 A; WP-C-01 is of record). Was: draft LD-ITEM-001 rev 0.2 (`item-definition.md`): platform (334 vehicles), variant family VF-001 Corolla E210, assured configuration AC-001 |
| HARA + safety goals | System FMEA severity, FMEDA | **Withdrawn** 2026-10-22 (DQ-124 A; WP-C-03 is of record, `hara-mapping.yaml` carries the IDs). Was: draft rev 0.3 (`analyses/hara.yaml`): 13 hazards, 15 situations, 19 hazardous events, 10 safety goals (SG-001 ASIL D); guide-word matrix and situation coverage complete; pre-checks in `reviews/`; mapped onto WP-C-03, the HARA of record, in `hara-mapping.yaml` (checked by `fmea_lint.py`; [reconciliation §8](../../00-assessment/docs-safety-reconciliation.md#8-second-set-hara-mapped-onto-wp-c-03-oi-5)) |
| Functional / technical safety concept | DFMEA, SW FMEA, FMEDA | **Withdrawn** 2026-10-22 (DQ-124 A; WP-C-04 is of record). Was: FSC draft rev 0.2 (`analyses/fsc.yaml`): 40 FSRs, 12 elements, 11 panda/SoC decompositions; DFA rev 0.5 accepts none of them yet (`analyses/dfa.yaml`; 4 initiators insufficient; the configuration lock, diagnostic-mode gate and HUD check implemented, awaiting HIL); TSC not started |
| HW/SW baseline frozen (commit SHA + submodule SHAs + AGNOS version) | All | BL-001 proposed in `baseline.yaml`; freeze at Phase 1 start |
| Panda schematic + BOM (open hardware) | DFMEA, FMEDA | To collect |
| comma 3X schematic / SoC failure data | DFMEA, FMEDA | Likely unavailable — see §7 |

**Recommendation:** System FMEA, DFMEA (structure + function steps) and SW FMEA can start in parallel with HARA, because steps 1–3 of AIAG-VDA (scope, structure, function) don't need severity. Ratings (step 5) and FMEDA wait for safety goals.

---

![Figure 2-1: DFA initiators by category against the 11 panda/SoC ASIL decompositions, with measures DM-01..DM-20 and open items](figures/generated/fig-2-1-dfa-initiators.svg)

*Figure 2-1.* Dependent failure initiators against the FSC decompositions, coloured by assessment; measures by status (green only for `existing`). Drawn from `analyses/dfa.yaml` by `tools/safety/fmea_diagrams.py`; index of all generated figures: [figures/generated/README.md](figures/generated/README.md).

## 3. Analysis scopes

### 3.1 System FMEA
Functions under analysis (from `docs/SAFETY.md` and `selfdrived`/`controlsd`):

- F1 Lateral control (ALC) — steering torque request to Toyota EPS
- F2 Longitudinal control (ACC) — accel request to Toyota ADAS/PCM
- F3 Engagement / disengagement state machine (`selfdrive/selfdrived/state.py`)
- F4 Driver override: brake, gas, steering, cancel button
- F5 Driver monitoring & escalation (`selfdrive/monitoring/`)
- F6 Alerting (visual / audible) (`selfdrived/alertmanager.py`, soundd)
- F7 Actuation limiting / excessive-actuation detection (`selfdrived/helpers.py`, opendbc safety)
- F8 Stock function preservation — stock AEB/FCW/lane assist stay available with the harness installed (added in System FMEA rev 0.2)

Failure modes per function: loss, unintended, too much, too little, too early/late, stuck, wrong direction.

![Figure 3-1: System FMEA structure tree SFM-SE-001..034 with functions SFM-FN-001..008](figures/generated/fig-3-1-sfm-structure.svg)

*Figure 3-1.* System FMEA structure and functions (steps 2–3). *Figure 3-2.* Failure chains, sheets [1](figures/generated/fig-3-2-sfm-failure-chains-1.svg) [2](figures/generated/fig-3-2-sfm-failure-chains-2.svg) [3](figures/generated/fig-3-2-sfm-failure-chains-3.svg) [4](figures/generated/fig-3-2-sfm-failure-chains-4.svg) [5](figures/generated/fig-3-2-sfm-failure-chains-5.svg) [6](figures/generated/fig-3-2-sfm-failure-chains-6.svg). Drawn from `analyses/system-fmea.yaml`.

Each System FMEA failure mode from its causes to the road. Every card gives the effect chain (local, next level, end effect), a looping scene of the end effect, the WP-C-03 hazards through [hara-mapping.yaml](hara-mapping.yaml), every cause with its occurrence, detection and FMEA-MSR monitoring meters, its AP and its MSR AP, and the actions with their status. The monitoring meter follows the M table ([rating-tables §7.3](rating-tables.md), DQ-206 A): green for M 1–4 (within the FTTI on measured timing, the only band that can close a cause), amber for M 5–7 (the diagnostic targets the cause, with the FTTI met on code-derived timing only, or untimed), red for M 8–10 (late, not designed for this cause, or none) and grey where the cause has no MSR rating. A completed action with a predicted (`revised`) rating that none of its causes has reached yet reads "completed, not yet credited" until the next baseline re-rates them. Everything but the scene is read from `analyses/system-fmea.yaml`.

![Figure 3-17a: System FMEA failure-mode cards for lateral and longitudinal control, SFM-001 to SFM-012, SFM-037 and SFM-038](figures/cards/fig-3-17-sfm-cards-1.svg)

![Figure 3-17b: System FMEA failure-mode cards for engagement, disengagement, driver monitoring and alerts, SFM-013 to SFM-028](figures/cards/fig-3-17-sfm-cards-2.svg)

![Figure 3-17c: System FMEA failure-mode cards for limits, configuration and the stock functions, SFM-029 to SFM-036](figures/cards/fig-3-17-sfm-cards-3.svg)

*Figure 3-17.* System FMEA failure-mode cards, drawn by [`tools/safety/fmea_cards.py`](../../../tools/safety/fmea_cards.py) (CI fails if stale; after a change to `system-fmea.yaml`, `hara-mapping.yaml`, a WP-A-04 tree or `fta-fmea-map.yaml`, run it). Scenes are drawings, not data. The *Fault trees* line names, per goal, the basic events (red if a single point: one item event that reaches the top event with the events outside the item assumed to occur, as BE-7.13 with UE-7.14) and gates this failure mode backs, or says the map lists it outside that goal's tree; the tree side is in [fta-fmea-mapping.md](../fta-fmea-mapping.md) §5.

### 3.2 DFMEA (hardware)
Structure tree:

1. **comma 3X** — SoC/compute, cameras (road, wide, driver), IMU, GNSS, power, thermal, display/speaker
2. **Integrated panda** — STM32H7 MCU, CAN/CAN-FD transceivers, SPI link to SoC, watchdog, power-on/relay control
3. **Harness / harness box** — Toyota TSS2 camera connector, relay that intercepts the stock camera's CAN, connectors
4. **Vehicle interfaces** (boundary, analysed as interfaces only) — EPS, ADAS ECU, gateway, power (12 V), mount/windshield

![Figure 3-3: DFMEA structure tree DFM-SE-001..010 with functions](figures/generated/fig-3-3-dfm-structure.svg)

*Figure 3-3.* DFMEA structure and functions. *Figure 3-4.* Failure chains, sheets [1](figures/generated/fig-3-4-dfm-failure-chains-1.svg) [2](figures/generated/fig-3-4-dfm-failure-chains-2.svg). Drawn from `analyses/dfmea.yaml`.

### 3.3 SW FMEA
Prioritised by safety relevance (path from perception to actuator):

| Priority | Element | Path |
|---|---|---|
| P1 | Safety model / CAN TX filtering & limits (panda firmware, `opendbc/safety/`) | submodules |
| P1 | `pandad` (SoC↔panda comms, safety mode set, heartbeat) | `openpilot/selfdrive/pandad/` |
| P1 | `selfdrived` (state machine, events, alerts) | `openpilot/selfdrive/selfdrived/` |
| P1 | `controlsd` + lateral/longitudinal controllers | `openpilot/selfdrive/controls/` |
| P2 | `card` (car interface, CAN parse/pack, Toyota port) | `openpilot/selfdrive/car/`, opendbc |
| P2 | `dmonitoringd` / driver monitoring model | `openpilot/selfdrive/monitoring/` |
| P2 | `plannerd`, `radard` | `openpilot/selfdrive/controls/` |
| P3 | `modeld` (driving model — failure modes overlap SOTIF/ISO PAS 8800) | `openpilot/selfdrive/modeld/` |
| P3 | `locationd`, calibration, `camerad`, `sensord` | various |
| P3 | Messaging (`cereal`/msgq), `manager`, `updated` | `openpilot/cereal`, `openpilot/system/` |

**Status (rev 0.5, `analyses/sw-fmea.yaml`):** the panda safety model was re-rated at BL-003 (panda `c2e5d93`, opendbc `5b5a4ba`). It has 19 failure modes, 25 causes (21 AP H, 4 AP L) and 11 actions.

- **Firmware changes credited:**
  - RX timeout after 5 periods at 100 Hz (SWF-006: O4/D3);
  - grant-time RX check (SWF-007);
  - reference-build mode lock (SWF-001.C3, SWF-008.C1, SWF-013.C1: AP L);
  - hardware watchdog (new SWF-018, plus SWF-019 for spurious resets);
  - heartbeat loss revoked in 0.3 s (SWF-014.C1: AP L).
- **Still open:**
  - the lock is only in a `LIONDRIVER_REFERENCE=1` build, and nothing builds that yet (SWF-013.C2, AP H);
  - limits equal to the SoC limits;
  - no jerk check;
  - BRAKE_MODULE without end-to-end protection;
  - a control-loop stall behind a live heartbeat, caught only by the 3 s engaged mismatch (SWF-014.C2);
  - unrestricted ELM327 content.
- **Implementation defects** in the opendbc core are O5/D3 (CI gate with mutation tests).

**Host P1 elements (rev 0.6, BL-004):** pandad (SWF-020..029), selfdrived (SWF-030..039) and controlsd with the Toyota CarController hand-off (SWF-040..049): 30 failure modes, 51 causes, all AP H, 30 actions (SWF-ACT-020..049). The panda rows keep their BL-003 ratings, because every BL-004 firmware change except the IRQ priorities is compiled only into the reference build. Main findings:
  - pandad fills `pandaStates.faults` for bits 0..26 only; panda fault bit 27 leaves an entry at 0 = relayMalfunction, a false immediate disable (SWF-025);
  - the heartbeat's engaged flag reflects only selfdriveState, and controlsd uses selfdriveState, modelV2 and longitudinalPlan with no freshness check (SWF-020, SWF-040, SWF-043);
  - selfdrived reads none of the panda health flags (heartbeatLost, safetyTxBlocked, txRateExceeded, epsFault) and raises controlsMismatch only after 200 cycles (SWF-032, SWF-034);
  - a single non-finite input latches LatControlTorque and silently zeroes lateral output for the drive (SWF-045);
  - cruiseMismatch has no reaction, and lateral torque continues while the driver overrides (SWF-039, SWF-038/044).

**Re-baseline at BL-005 (SW FMEA rev 0.8, liondriver-dev `1033d98`, panda `a55bdfc`, opendbc `9a13f60`):** the reference build is the default since #36/#41, so its firmware features are credited. SWF-013.C2 (build without the lock) and SWF-014.C2 (control-loop stall behind a live heartbeat, now caught by TX arrival supervision, TSR-408) drop from AP H to L. Host supervision (#51: TSR-615, TSR-621, TSR-602, TSR-308, TSR-604 in part) lowers occurrence on SWF-032, -034, -039, -040, -043, -045; those rows stay AP H because the new code has targeted but unproven tests. New SWF-054 and SWF-055 record decisions DQ-079 and DQ-080, whose code (opendbc#15) is not pinned (SWF-ACT-054). 55 failure modes, 84 causes: 77 AP H, 1 M, 6 L.

**P2 elements (SW FMEA rev 0.9, BL-005):** card and the Toyota port (SWF-056..060), driver monitoring (SWF-061..064), plannerd (SWF-065..069) and radard (SWF-070, SWF-071): 16 failure modes, 29 causes, all AP H, actions SWF-ACT-056..064. Upstream code; the opendbc car and CAN tests are not run by LionDriver CI, and the driver-monitoring model, plannerd and card are not fuzzed. Main findings: no Toyota RX message has a counter and CAN timeouts are learned from a 10 s default; driver-monitoring timers count frames, a NaN pose reads as attentive, and the terminal alert does not disengage (DQ-365, which absorbed DQ-220); plannerd uses invalid leads and controlsd does not read `longitudinalPlan.valid`; the final acceleration target has no rate limit; the driver can leave the assured configuration while driving (DQ-221). Perception and model performance stay with SOTIF (§7.3). Totals: 71 failure modes, 113 causes: 106 AP H, 1 M, 6 L.

**P3 elements (SW FMEA rev 1.0, BL-005):** modeld as a software element (SWF-072..074), localization and calibration (SWF-075..077), camerad (SWF-078), sensord (SWF-079), messaging (SWF-080, SWF-081), manager (SWF-082, SWF-083) and updated (SWF-084): 13 failure modes, 18 causes, all AP H, actions SWF-ACT-065..071. The SOTIF / ISO PAS 8800 boundary of §7.3 holds: modeld is rated only for output validity, frame accounting, calibration input, crash and the model file, not for whether its outputs are right. Main findings: `modelV2.valid` means only "calibration seen" and the small model has no finiteness check; a repeated camera frame counts as no drop; a road camera absent at start is ignored for the drive; IMU loss reaches selfdrived after 10 s; msgq skips lapped messages silently and has no payload checksum; manager never restarts a process and does not report a blocked one; updates are not signed. With this the SW FMEA covers every element of §3.3 (P1–P3).

**FTA finding F-37 (SW FMEA rev 1.1, BL-005):** SWF-085 (driver monitoring evaluates the driver in demo mode while the item is engaged, BE-8.06) and SWF-086 (forced deceleration not requested, not passed on, or too weak after the terminal alert, BE-8.08): 4 causes, all AP H, actions SWF-ACT-072 and SWF-ACT-073. By code reading demo mode does not switch the alerts off; it decouples the policy from the real vehicle state and unlocks the monitored seat. The forced stop crosses three processes with no freshness check on the flag and slows at only −1.2 m/s². Totals: 86 failure modes, 135 causes: 128 AP H, 1 M, 6 L.

**Data for further figures (schema, 2026-10-16):** three optional fields, checked by `fmea_lint`. `previous` on a cause keeps its rating at an earlier baseline (the BL-004 → BL-005 delta); `layer`, `reaction_s`, `timing_basis` and `timing_ref` on a safety mechanism give the defence layer it acts in (host, envelope, alert, siren, vehicle) and its reaction time, with a `code_derived` or `measured` time needing its source; `sotif` on a structure element records the SOTIF / ISO PAS 8800 boundary (functional_safety, split, sotif) and what belongs to SOTIF. The SW FMEA fills them where the evidence exists: 11 previous ratings, 15 element boundaries, 11 mechanism times. The figures that draw them are not built yet.

**FTA finding F-28 (SW FMEA rev 1.2, BL-005):** SWF-087, the envelope passes LKA torque that opposes the driver while the driver overrides: `toyota.h` has no driver-override check on the LKA path (GAP-02; TSR-304 not implemented), O 8 D 10 AP H, action SWF-ACT-074. Totals: 87 failure modes, 136 causes: 129 AP H, 1 M, 6 L.

**Lead answers applied (SW FMEA rev 1.3, BL-005):** SWF-088 (`card`, `car_events.py`), the EPS-fault warning held at the low-priority prompt after an override or at standstill (C1, TSR-607 (b), DQ-342 A) or not given while the driver keeps steering (C2, TSR-607 (c), DQ-366 A); O 8 D 10 AP H at BL-005, the software counterpart of SFM-038.C1 and backing for BE-2.08. SWF-ACT-077 is completed after BL-005 (#174, #179: unit-tested in CI, not verified on the vehicle); its revised O 3 D 8 is a prediction and stays AP H. SWF-062.C1 now records the decided SG-010 safe state (DQ-365 A, TSR-633), which the code does not yet meet; SWF-ACT-059 is open. SWF-ACT-055 is in progress: the host supervision tests run in CI since #179, and D stays 8 until mutation proves them. Totals: 88 failure modes, 138 causes: 131 AP H, 1 M, 6 L.

**Baseline BL-006 (SW FMEA rev 1.4, proposed BL-006: `c61e31b`, panda `0a7da85`, opendbc `62b89a3`):** only `car_events.py`, opendbc #15…#18 and panda#17 changed since BL-005, so the other rows keep their BL-005 ratings. SWF-054.C1 and SWF-055.C1 drop from O 8 D 9 AP H to O 3 D 4 AP L (opendbc#15 in the pin, reference-variant tests and mutation in CI; SWF-ACT-054 completed). SWF-088.C1/C2 move from O 8 D 10 to O 5 D 8, still AP H (TSR-607 (b), (c) implemented with targeted tests in CI, not proven by mutation; new SWF-ACT-078 for the mutation run, which System FMEA SFM-ACT-023 also points to). New SWF-089 (engagement window left open by a MAIN_ON = 0 refusal, SM-F1, opendbc#17) and SWF-090 (relay-malfunction reaction cleared by a mode change, DFA DM-25, panda#17), both found after BL-005 and O 3 D 4 AP L at BL-006. opendbc#18 (a wrong-length RX frame is an RX fault in the reference build) is a new safety mechanism of SWF-005 and SWF-057. Figure 3-14 now compares BL-005 with BL-006. Totals: 90 failure modes, 140 causes: 129 AP H, 1 M, 10 L.

**Lead answer DQ-221 applied (SW FMEA rev 1.5, BL-006):** #287 (`69cddaa`, after BL-006) refuses engagement outside the assured settings on the reference platform and ignores the distance button there. SWF-067.C1 is now a defect in that gate, O 6 → 5, D 9 (still AP H): its targeted tests in `test_assured_config.py` have run only locally while the CI scons jobs fail on the git-lfs 404, and D drops to 8 once CI runs them (SWF-ACT-063 in progress). New SWF-067.C2: a setting changed in the settings menu while engaged still takes effect, O 8 D 10 AP H, queued for the lead as DQ-403 (SWF-ACT-079). Totals: 90 failure modes, 141 causes: 130 AP H, 1 M, 10 L. **Rev 1.6:** the CI unit_tests job runs again and is green with these tests (tests run 39296172878 at `6126485`), so SWF-067.C1 moves to D 8 (still AP H) and SWF-ACT-063 is completed. **Rev 1.7 (DQ-403 A, #342):** a menu change of Experimental Mode or the following distance while engaged is held until disengagement on the reference platform; SWF-067.C2 is now a defect in that hold, O 8 D 10 → O 5 D 8 (still AP H, tests in CI, not proven by mutation), and SWF-ACT-079 is completed.

**System FMEA (rev 0.5, BL-004):** all 80 causes rated: 79 AP H, 1 AP M (SFM-024.C1). Causes on the panda, host, harness and hardware elements inherit the linked SW FMEA or DFMEA rows; actions SFM-ACT-001..011.

**System FMEA (rev 0.9, BL-005):** baseline moved to BL-005. S, O and AP unchanged; D of SFM-015.C2 10 → 8 (host unit test). The MSR rows credit the host supervision and the reference-build checks that BL-004 lacked (TSR-408, TSR-615, TSR-621, TSR-308, reference lock): monitoring M 5–6 on 15 causes, M 7–8 on 16, M 9–10 on 29 ([msr-plan.md §4.7](msr-plan.md#47-pilot-result-m1)). The SW FMEA (BL-004) and DFMEA (BL-002) rows it inherits are not re-rated here.

**DFMEA (rev 0.9, BL-005, `analyses/dfmea.yaml`):** 21 failure modes and 30 causes across 10 hardware elements of the comma 3X panda section, harness and relay box, based on WP-H-02/WP-H-03. Every row is S10, AP H, and most have no LionDriver hardware verification (D9–D10). The watchdog (DFM-004) is the only cause whose occurrence the BL-002 firmware lowers. At BL-005 the hardware is unchanged; the MSR rows credit the host controlsMismatch timing (DFM-009.C1, M 6) and list the panda siren on heartbeat loss and EPS fault (DFM-017) (msr-plan §4.7). Rev 0.8: EPS-fault siren persistence 0.7 s (DQ-048, panda `bf8102a`); HIL timing of the chain is open (DFM-ACT-016). Rev 0.9: own CPU self-test, low coverage (DQ-069 B, DFM-ACT-001).

**FMEDA (rev 0.7, `analyses/fmeda-sg001.yaml`, `fmeda-sg009.yaml`):** block-level, **generic failure rates**, except the harness box switches U1/U2 at the SN 29500-2 reference value from a secondary source (WP-H-03 §6.3). Since rev 0.7 the goals and ASIL targets of WP-H-04 §4 are data (`analysis.targets`), and a row that another goal classifies differently carries a `per_goal` entry. Results per goal:
- SG-01 (C, B alongside), SG-02 (C), SG-03 (C), SG-04 (B), SG-06 (C): 255 FIT, SPFM 96.84 %, LFM 88.94 %, λSPF + λRF 8.1 FIT. Misses C on SPFM by 0.16 points (WP-H-04 OI-6, G2); meets B.
- SG-05 (B): SPFM 90.38 %, LFM 95.30 %, λSPF + λRF 24.6 FIT, with FMD-001 and FMD-009 single-point for this goal (FTA BE-5.02). Meets B by 0.38 points.
- SG-07 (B, file SG-009): 287 FIT, SPFM 78.1 %, LFM 97.7 %, λSPF + λRF 62.9 FIT. Misses B; recorded deviation (DQ-320).

The effect of the planned DFMEA measures and the soft-error sensitivity are in WP-H-03 §6.3. Review pages [`exports/review/fmeda-sg001.md`](exports/review/fmeda-sg001.md) and [`fmeda-sg009.md`](exports/review/fmeda-sg009.md) with committed workbooks (`tools/safety/fmeda_review_md.py`, `tools/safety/export_fmeda_xlsx.py --all`; CI checks both).

**PFMEA (rev 0.2, `analyses/pfmea.yaml`):** 17 failure modes over 11 process steps:
- release: freeze, build, verification, publication (WP-P-10);
- installation and provisioning: WP-O-01 INS-01..30;
- update and rollback.

16 causes are AP H and 1 is AP L. The procedures are drafts not yet in use, so prevention is rated as documented-but-unpractised (O7–O8) and detection mostly as unproven human checks (D7–D8). Special characteristics SPC-01..09 come from WP-O-01 §4, and the workbook links each row to its control-plan step.

**Workbooks** (git-ignored, regenerate from the YAML):

| Analysis | Command | Builder layout |
|---|---|---|
| System FMEA | `tools/safety/export_fmea_xlsx.py system --generator <dfmea-builder>/scripts/generate_dfmea.py` | dfmea-builder; unrated rows show "Not rated" |
| DFMEA | `tools/safety/export_fmea_xlsx.py dfmea --generator <dfmea-builder>/scripts/generate_dfmea.py` | dfmea-builder |
| SW FMEA | `tools/safety/export_fmea_xlsx.py sw --generator <sw-fmea-builder>/scripts/generate_sw_fmea.py` | sw-fmea-builder |
| PFMEA | `tools/safety/export_pfmea_xlsx.py --generator <pfmea-builder>/scripts/generate_pfmea.py` | pfmea-builder |
| FMEDA | `tools/safety/export_fmeda_xlsx.py --all` (committed under `exports/review/`, checked in CI) | own formulas, fmeda-builder tab names, one metric row per goal |

AP always comes from the RT-1 table. The builders' own AP rules disagree with it, and the pfmea-builder's rule is inverted on detection.

This file supports the narrative analysis in [WP-W-04](../../05-software/WP-W-04-software-safety-analysis.md) with AIAG-VDA ratings (WP-W-04 §3.5).

SW failure-mode guidewords: omission, commission, early, late, incorrect value (high/low/stale/frozen), corrupted, out-of-sequence, wrong mode.
Model-level performance limitations go to the **SOTIF** analysis, not SW FMEA — SW FMEA covers the model as a software element (crash, stale output, wrong tensor shape, timeout).

![Figure 3-5: SW FMEA structure tree SWF-SE-001..046 with functions and the number of failure modes per function](figures/generated/fig-3-5-swf-structure.svg)

*Figure 3-5.* SW FMEA structure and functions. *Figure 3-6.* Failure chains, sheets [1](figures/generated/fig-3-6-swf-failure-chains-1.svg) [2](figures/generated/fig-3-6-swf-failure-chains-2.svg) [3](figures/generated/fig-3-6-swf-failure-chains-3.svg) [4](figures/generated/fig-3-6-swf-failure-chains-4.svg) [5](figures/generated/fig-3-6-swf-failure-chains-5.svg) [6](figures/generated/fig-3-6-swf-failure-chains-6.svg) [7](figures/generated/fig-3-6-swf-failure-chains-7.svg) [8](figures/generated/fig-3-6-swf-failure-chains-8.svg) [9](figures/generated/fig-3-6-swf-failure-chains-9.svg) [10](figures/generated/fig-3-6-swf-failure-chains-10.svg) [11](figures/generated/fig-3-6-swf-failure-chains-11.svg) [12](figures/generated/fig-3-6-swf-failure-chains-12.svg) [13](figures/generated/fig-3-6-swf-failure-chains-13.svg). *Figure 3-7.* [AP as rated vs. predicted after planned actions (not achieved)](figures/generated/fig-3-7-swf-action-effect.svg). *Figure 3-12.* [Occurrence × detection per element, with the predicted moves](figures/generated/fig-3-12-swf-od-elements.svg). *Figure 3-13.* [What each detection rating rests on: cited test run in CI, hardware only, not run, or none](figures/generated/fig-3-13-swf-detection-evidence.svg); how CI treats each test file is worked out from the workflows and `tools/test_runner.py`, not from the analysis text. *Figure 3-14.* [What the last baseline changed: occurrence, detection and AP of each re-rated cause, before and after](figures/generated/fig-3-14-swf-baseline-delta.svg), from the causes' `previous` records. *Figure 3-15.* [Reaction time by defence layer](figures/generated/fig-3-15-swf-reaction-layers.svg) for the safety mechanisms that record `reaction_s`; the times are code-derived, not measured, and are not checked against an FTTI. *Figure 3-16.* [Where the SW FMEA stops and SOTIF starts](figures/generated/fig-3-16-swf-sotif-boundary.svg): per top-level element, the causes rated here and the performance part left to SOTIF (`sotif` on the element). Drawn from `analyses/sw-fmea.yaml`.

### 3.4 PFMEA
LionDriver doesn't manufacture hardware, so "process" means the steps that produce the as-driven configuration:

1. Source build & release (`tools/release/`, `SConstruct`, CI, submodule pinning)
2. Device provisioning / OS (AGNOS) / software install
3. In-vehicle installation (harness, mount, camera placement, connectors)
4. Calibration (camera extrinsics, `locationd` calibration convergence)
5. OTA update (`system/updated`) and rollback
6. Car fingerprinting / correct car port selection

Output: a **release & install control plan** (checklist) — this is the practical deliverable.

![Figure 3-8: PFMEA process tree PFM-SE-001..030 with functions](figures/generated/fig-3-8-pfm-structure.svg)

*Figure 3-8.* PFMEA process structure and functions. *Figure 3-9.* Failure chains, sheets [1](figures/generated/fig-3-9-pfm-failure-chains-1.svg) [2](figures/generated/fig-3-9-pfm-failure-chains-2.svg). Drawn from `analyses/pfmea.yaml`.

### 3.5 FMEDA
- **Phase A (feasible now):** panda safety path — MCU, CAN transceivers, relay, watchdog, power supervision. Open schematic allows component-level analysis.
- **Phase B (data-limited):** comma 3X compute — treat as QM or use a top-down/budget approach; document the gap rather than invent failure rates.
- Failure rate sources: IEC 61709 / SN 29500 / IEC TR 62380, ISO 26262-11 for MCU; record source per row.
- Metrics: SPFM, LFM, PMHF per safety goal, with diagnostic coverage justified per safety mechanism (ISO 26262-5 Annex D).

---

![Figure 3-10: FMEDA SG-001 SPFM, LFM and λSPF+λRF per safety goal against the WP-H-04 targets (SG-01 C with B alongside, SG-02/03/06 C, SG-04/05 B), generic estimates, not verified](figures/generated/fig-3-10-fmeda-sg001-metrics.svg)

*Figure 3-10.* FMEDA SG-001 and *Figure 3-11* [SG-009](figures/generated/fig-3-11-fmeda-sg009-metrics.svg): metrics per safety goal against the WP-H-04 §4 targets (rating-tables §6.3; goals with the same numbers share a row), split per component and failure mode, and safety-mechanism coverage. Failure rates are generic estimates; nothing here is verified. Drawn from `analyses/fmeda-sg001.yaml` and `analyses/fmeda-sg009.yaml`.

## 4. Method decisions

- **Rating scheme:** AIAG-VDA S/O/D 1–10 with **Action Priority (H/M/L)**, not RPN.
- **Severity** for System FMEA effects is derived from HARA severity (S0–S3) mapping, recorded in the rating tables.
- **Occurrence** for SW: based on prevention controls (MISRA, static analysis, code review, coverage), not field statistics.
- **Detection** credits only controls that exist in the repo/CI today (e.g. `opendbc/safety/tests`, `selfdrive/test/process_replay`, `controls/tests`) — each detection claim must reference a test path.
- **Severity 9–10 or AP=H** items require an action with owner and due date, or a documented rationale.
- **In-field monitoring and system response** (diagnostics plus safe-state reaction while driving) is rated by a supplementary FMEA-MSR on System FMEA and DFMEA causes, never as Detection: audit and plan in [msr-plan.md](msr-plan.md).

---

![Figure 4-1: Action Priority overview of the System FMEA, DFMEA, SW FMEA and PFMEA](figures/generated/fig-4-1-action-priority-overview.svg)

*Figure 4-1.* AP counts as rated, where the causes sit in the AIAG-VDA AP table, and how AP H is treated (action status or rationale). Drawn from the four FMEA YAML files.

![Figure 4-2: FMEA-MSR overview of the System FMEA and DFMEA](figures/generated/fig-4-2-msr-overview.svg)

*Figure 4-2.* FMEA-MSR ([msr-plan.md](msr-plan.md)): where the System FMEA and DFMEA causes sit by frequency F and monitoring M over the provisional MSR AP table, how many fall in each monitoring band, the timing basis, how many responses lower the severity, and the status of the actions the MSR rows name. While every MSR AP is H, M is what ranks the work.

## 5. Repository format & traceability

```
assurance/08-analyses/fmea/
  fmea-plan.md                 (this document)
  item-definition.md           (LD-ITEM-001: platform, variant families, assured configurations)
  item/                        (variants.yaml; vehicle-catalog.md generated by tools/safety/gen_vehicle_catalog.py)
  rating-tables.md             (S/O/D tables, AP table, FMEDA targets — version RT-n)
  msr-plan.md                  (FMEA-MSR audit and plan: monitoring and system response, RT-2)
  baseline.yaml                (analyzed configurations: vehicle, HW, repo + submodule SHAs, OS)
  schema/
    fmea.schema.json           (System FMEA, DFMEA, SW FMEA, PFMEA)
    fmeda.schema.json
    hara.schema.json           (ASIL checked against ISO 26262-3 Table 4)
    fsc.schema.json            (decompositions checked against ISO 26262-9 Table 1)
    dfa.schema.json            (decomposition status derived from its dependent failure initiators)
    baseline.schema.json
  analyses/
    hara.yaml
    fsc.yaml
    dfa.yaml
    system-fmea.yaml
    dfmea.yaml
    sw-fmea.yaml
    pfmea.yaml
    fmeda-<goal>.yaml          (one FMEDA per safety goal: fmeda-sg001.yaml lateral, fmeda-sg009.yaml stock AEB)
  exports/                     (generated .xlsx; git-ignored, regenerate)
  exports/review/              (review pages that read in GitHub: Markdown + SVG per FMEA, tools/safety/fmea_review_md.py;
                                and reviewer workbooks, tools/safety/fmea_review_xlsx.py; committed, checked in CI)
  diagrams/                    (block/boundary diagram or process flow, P-diagram per FMEA; drawn into the review pages)
  reviews/                     (review records, e.g. hara-r0.1-precheck.md)
  design/                      (safety design specifications, e.g. LD-DES-001 panda configuration lock)
tools/safety/
  fmea_lint.py                 (validator)
  test_fmea_lint.py
  export_hara_xlsx.py          (HARA -> xlsx in hara-builder layout, for hara-checklist-reviewer)
  export_fsc_xlsx.py           (FSC -> xlsx in fsc-builder layout, for fsc-checklist-reviewer)
  export_item_xlsx.py          (item definition -> xlsx in item-definition-builder layout, for item-def-checklist-reviewer)
  gen_vehicle_catalog.py       (vehicle catalog from docs/CARS.md and item/variants.yaml)
  fmea_diagrams.py             (figures/generated/*.svg + README.md from the YAML; --check)
  test_fmea_diagrams.py
```

Review workbooks come from the builder/reviewer skills in jherrodthomas/automotive-skills-suite. Exports render the YAML as-is; the skills' heuristic ratings are never written back into the analyses.

- Source of truth is YAML (diffable, reviewable in PRs); spreadsheets are generated.
- IDs: `SFM-`, `DFM-`, `SWF-`, `PFM-` prefixes for structure (`-SE-###`), functions (`-FN-###`), failure modes (`-###`), causes (`-###.C#`), actions (`-ACT-###`). FMEA ids are unique across all files; FMEDA ids (`FMD-…`) only within their file.
- Each row links upward (`hazard`, `requirements`) and downward (`paths`, `test`, `linked_failure_mode`).
- Every analysis names its `baseline` (from `baseline.yaml`) and the `rating_tables` version it was rated against.

**Validation** (needs the pinned packages of `assurance/trace/requirements.txt`, DQ-123 A; not added to openpilot runtime deps):

```
tools/safety/fmea_lint.py --report            # validate all analyses
python3 -m unittest discover -s tools/safety  # linter tests
```

The linter checks: schema; unique and resolvable ids; failure-mode severity = max effect severity; hazard-linked effects rated 10; stored AP = AP table; AP=H has an action or rationale; detection ≤ 8 names a `test` path that exists (warning only inside an uninitialized submodule); released analyses fully rated; HARA ASIL = Table 4, safety-goal ASIL = highest hazardous event, every ASIL hazard covered by a goal, FMEA↔HARA links consistent both ways; a System FMEA cause with `linked_failure_mode` rated within the O and D range of the linked mode's causes (warning; stale after the lower-level analysis is re-rated); FMEDA distributions sum to 1, mechanisms have DC, SPFM/LFM/λSPF+λRF against the ASIL target. Wiring it into CI is a follow-up.

---

## 6. Phasing

| Phase | Deliverable | Depends on |
|---|---|---|
| 0 | This plan + rating tables + YAML schema + baseline SHAs | — |
| 1 | System FMEA steps 1–4 (structure, functions, failure modes, effects, causes) — **draft rev 0.2 done** | Item definition draft |
| 2 | SW FMEA P1 elements + DFMEA structure/function — **SW FMEA rev 0.6: panda safety model, pandad, selfdrived and controlsd done (49 failure modes, all rated)** | Phase 1 |
| 3 | HARA → apply severities (**HARA draft + System FMEA severities done**); risk analysis & AP for System/SW/DFMEA (**done at BL-004: System FMEA rev 0.5, SW FMEA rev 0.6, DFMEA rev 0.2**) | HARA |
| 4 | PFMEA + release/install control plan — **PFMEA rev 0.2 done; control plan = WP-O-01 §3–§4** | Phase 0 |
| 5 | FMEDA Phase A (panda) | Safety goals, TSC, panda BOM |
| 6 | SW FMEA P2/P3, DFMEA comma 3X, FMEDA Phase B gap report | Phase 3 |
| 7 | Independent review (checklist), action closure, feed safety case | All |

---

## 7. Known risks to the plan

1. **Upstream code isn't ours.** Safety-critical logic lives in `panda` and `opendbc` submodules tracking comma.ai. Each upstream bump invalidates parts of SW FMEA → need an impact-analysis trigger on submodule changes.
2. **No supplier data for comma 3X.** FMEDA on the compute module will be incomplete; the architecture likely has to argue that the panda safety model bounds what a faulty SoC can command.
3. **ML model failures.** Most driving-model "failures" are performance limitations (SOTIF/PAS 8800), not random or systematic SW faults — keep the boundary explicit to avoid double counting or gaps.
4. **Vehicle ECUs are black boxes.** Toyota EPS/ADAS internal failures are outside the item; analyze only the interface and stock-system fallback behavior.

---

## 8. Decisions

| # | Decision | Resolution |
|---|---|---|
| 1 | Start FMEAs in parallel with HARA? | **Yes** — steps 1–4 now; ratings after HARA |
| 2 | Pin `panda` / `opendbc` into the analyzed baseline? | **Yes** — SHAs recorded in `baseline.yaml` (BL-001) |
| 3 | YAML source vs spreadsheets? | **YAML source**, xlsx generated |
| 4 | PFMEA scope per §3.4? | **Confirmed** |

| 5 | Reference device | **comma 3X** (recorded in BL-001) |
