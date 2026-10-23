# Reconciliation of the earlier `docs/safety/` drafts

| Field | Value |
|---|---|
| Work product | Reconciliation record (supporting document, not a registered work product) |
| Standard reference | ISO 26262-8:2018 §7 (configuration management), §8 (change management) |
| Version | 0.6 (OI-3 notes the lead's decision to allow an external monitor in principle, DQ-051 A; 2026-10-23). 0.5 (OI-5 closed: the second set is withdrawn, DQ-124 A; 2026-10-22). 0.4 (§8: second-set HARA mapped onto WP-C-03, decisions RD-1…RD-3; 2026-10-13). 0.3 (reference configuration named by generation, E210; 2026-10-12). 0.2 (status of the layer-1 measures after the firmware changes integrated 2026-10-12: TSR-501 IWDG implemented, not verified; layer 2 and OI-3 re-scoped; TSR-306, TSR-405 added to ASM-V-03…05; 2026-10-12). 0.1: initial reconciliation |
| Status | Draft |
| Author | Assurance team |
| Reviewer(s) | TBD |
| Baseline | `docs/safety/` as last present at LionDriver `14e18b3` |

## 1. Purpose

Two sets of safety drafts were written in parallel:

- `docs/safety/` on branch `claude/safety-framework-docs`: safety plan LD-SPL-001, item definition LD-ITD-001, HARA LD-HARA-001, functional safety concept LD-FSC-001 and technical safety concept LD-TSC-001, each as a JSON source, a generator script and an xlsx workbook; plus a `configurations/` folder for the Corolla reference configuration.
- `assurance/` (this tree), merged to `liondriver-dev` in pull request #2.

`assurance/` is the single source of truth. `docs/safety/` has been removed from the working tree. Its files can be recovered from commit `14e18b3` (`git show 14e18b3:docs/safety/<path>`).

This record says where each `docs/safety/` item went, what was carried over, and which differences between the two sets of drafts still need an engineering decision. **No rating, goal or requirement in `assurance/` was changed by this reconciliation.** The open differences are listed as open items in §6.

## 2. Mapping

| `docs/safety/` item | Disposition | Where in `assurance/` |
|---|---|---|
| LD-SPL-001 safety plan | Superseded | [WP-M-02](../01-management/WP-M-02-safety-plan.md), [WP-M-01](../01-management/WP-M-01-assurance-strategy.md) |
| LD-SPL-001 anomalies A01 (no independent reviewers), A03 (no interface agreement with upstream), A05 (panda MCU fault detection) | Covered | [WP-M-07](../01-management/WP-M-07-risk-management.md) R-01; [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md); GAP-07, GAP-08, GAP-11, GAP-43 |
| LD-SPL-001 anomaly A02 (XZACT compiler miscompiled valid programs) | Carried over | [WP-W-06](../05-software/WP-W-06-software-unit-verification.md) §4.8 |
| LD-SPL-001 anomaly A04 (ASIL D as a pre-HARA assumption) | Open | §6 OI-1 |
| LD-ITD-001 item definition | Superseded | [WP-C-01](../02-concept/WP-C-01-item-definition.md) |
| LD-ITD-001 vehicle assumptions ASM-V-01…08 | Covered, see §4 | WP-C-01 §7 (AOU-01…11) |
| LD-HARA-001 HARA (9 safety goals) | Superseded, with open differences | [WP-C-03](../02-concept/WP-C-03-hara.md) (7 safety goals); §3 and §6 |
| LD-FSC-001 functional safety concept | Superseded | [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) |
| LD-FSC-001 gaps G1–G5 | Covered | G1: GAP-07, GAP-08, GAP-11, TSR-501 (IWDG; implemented 2026-10-12, not verified on hardware), TSR-502, TSR-503, TSR-515 (not implemented). G2: GAP-06, [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md). G3: [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md). G4: WP-C-05 SH-04. G5: GAP-01, TSR-405, [WP-V-05](../06-validation/WP-V-05-fault-injection.md) VS-FI-01/02/05 |
| LD-TSC-001 technical safety concept | Superseded | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) |
| LD-TSC-001 G1 layer 1 (firmware measures: IWDG, latched no-output, ECC, code CRC, start-up tests) | Covered | TSR-501 (IWDG), TSR-502, TSR-503, TSR-515. Status 2026-10-12: IWDG implemented, not verified on hardware; TSR-502, TSR-503 and TSR-515 not implemented |
| LD-TSC-001 G1 layer 2 (relay supervisor) and layer 3 (monitoring MCU) | Carried over as design input | §5; §6 OI-3 |
| `configurations/toyota-corolla-2020/` parameter baseline | Covered | [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md) CD-01 and the envelope limit table |
| `configurations/toyota-corolla-2020/` XZACT equivalence evidence | Carried over | WP-W-06 §3.3 and §4.8 |
| `standards.md` (how each standard is applied) | Superseded | [README](../README.md), WP-M-01 |

## 3. Differences between the two HARAs

The two HARAs rate the same functions but reach different results. Both are unreviewed drafts.

| Topic | LD-HARA-001 (`docs/safety/`) | WP-C-03 (`assurance/`) |
|---|---|---|
| Scope | Platform as a Safety Element out of Context over a declared operating envelope; each vehicle checks the platform's assumptions | The reference configuration (E210 Corolla, TSS2) as the item; other vehicles join through impact analysis ([WP-M-12](../01-management/WP-M-12-impact-analysis.md)) |
| Highest ASIL | **D**, for five goals (lateral motion, acceleration, deceleration, failure to release, uncommanded engagement), all from one cell: motorway, dry, daylight, S3 E4 C3 | **C** for SG-01 (lateral motion), B for the rest; each ⚠ goal rises one level if the EPS, brake or PCM assumptions (AOU-01/02/03/05) fail |
| Main source of the difference | Controllability C3 at motorway speed, with no credit for OEM ECU limiting | Controllability C2, crediting the EPS and PCM limits as assumptions of use (AOU-01, AOU-02, AOU-05) |
| Uncommanded engagement | Separate goal SG-005 (ASIL D) | Rated inside H-01 (torque while not engaged) and H-03 (acceleration when not intended) |
| Driver-monitoring failure | Separate goal SG-008 (ASIL B) | Not a vehicle-level hazard; handled as a latent fault of a measure that controllability relies on (WP-C-04 §7) |
| Mode confusion | Separate goal SG-009 (ASIL B) | H-07 reserved and rated within H-02, H-05, H-06 (WP-C-08) |
| Stock PCS/AEB suppression | Not a goal | SG-07 (ASIL B) |

The decisive question is whether controllability credit for the OEM EPS and PCM limits holds. If it does not, SG-01 reaches ASIL D in WP-C-03 as well, and the two HARAs largely agree on the lateral goal.

## 4. Vehicle assumptions

| LD-ITD-001 | Meaning | `assurance/` |
|---|---|---|
| ASM-V-01 | EPS limits its own output | AOU-01 |
| ASM-V-02 | Driver can overpower maximum torque | AOU-02 |
| ASM-V-03 | Pedal state on CAN, fast and protected | AOU-03; GAP-01 (`0x226` has no checksum or counter); TSR-405(b) (brake cross-check, open: meaning of the `0x1D3` brake bit unknown) |
| ASM-V-04 | Engagement needs a deliberate driver action | FSR-01.05 (authority only on the PCM cruise rising edge); GAP-01; TSR-306 (authority only while all RX checks are valid) and TSR-405(c) (CRUISE_ACTIVE checked against MAIN_ON), both implemented in the reference build 2026-10-12, not verified on hardware |
| ASM-V-05 | Speed signals with fault indication | GAP-01 (`0xAA` has no checksum); TSR-405(a) (open: SPEED `0xB4` is not in the RX check set) |
| ASM-V-06 | All commands pass through the harness | TSR-506, TSR-701; WP-S-03 AP-4 |
| ASM-V-07 | Powertrain honors acceleration limits | AOU-05 |
| ASM-V-08 | Stock emergency braking available | AOU-04; SG-07 |

## 5. Design input carried over: independent relay disable path

LD-TSC-001 proposed three layers for panda MCU faults. Layer 1 (firmware measures) is already covered by TSR-501 (IWDG), TSR-502, TSR-503 and TSR-515. The IWDG was implemented on 2026-10-12 and is not verified on hardware; TSR-502, TSR-503 and TSR-515 are not implemented. Layers 2 and 3 have no counterpart in `assurance/` yet:

- **Layer 2, relay supervisor.** Today the panda holds the harness relay closed with a steady GPIO level, so a hang can hold it closed (GAP-43). Driving the relay through an AC-coupled stage from a toggling signal means only running, healthy firmware can keep it closed: stuck high, stuck low, hang and reset all open it, with no software involved. Opening the relay restores the stock camera path. Since 2026-10-12 an IWDG reset releases the relay after a hang (TSR-501); the supervisor would still cover a failed or unstarted IWDG, a stuck relay GPIO and a relay stuck in intercept (GAP-43 remainder).
- **Layer 3, diverse monitoring MCU.** A second microcontroller checks torque limits and brake release independently. Only needed if the panda FMEDA ([WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md)) shows that layers 1 and 2 cannot reach the hardware metrics for the assigned ASIL.

Decision rule proposed in LD-TSC-001: implement layer 1, design layer 2, then let the FMEDA decide on layer 3.

## 6. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Decide the controllability ratings at motorway speed for H-01, H-03, H-04 and H-05 (§3). Either justify the C2 credit for OEM EPS and PCM limits or re-rate to C3, and record the rationale in WP-C-03. Close LD-SPL-001 anomaly A04 with the outcome | Safety engineer, I3 reviewer | G1 |
| OI-2 | Confirm that rating uncommanded engagement, driver-monitoring failure and mode confusion inside other hazards (§3) does not lose a safety goal; record the review in WP-C-03 | Safety engineer | G1 |
| OI-3 | Evaluate the relay supervisor (§5) for the cases the IWDG reset (TSR-501) does not cover: a failed or unstarted IWDG, a stuck relay GPIO and a relay stuck in intercept (GAP-43 remainder, TSR-502), in WP-S-03 and [WP-H-02](../04-hardware/WP-H-02-hardware-design.md). The lead allows added hardware such as an external monitor in principle, decided from the [WP-H-04](../04-hardware/WP-H-04-hardware-metrics.md) results within an agreed budget limit (decision register DQ-051, A, 2026-10-14; WP-H-01 OI-6) | HW lead | G2 |
| OI-4 | Decide whether the multi-vehicle model (platform plus configurations checked against its assumptions) becomes the scope method in WP-M-01 and WP-M-12, or stays as described there today | Maintainer | G1 |

## 7. Second set: AIAG-VDA analyses (`assurance/08-analyses/fmea/`)

A third set of drafts was written on branch `claude/charming-knuth-b8nnqh`, also against BL-001 (`8b8c6ae`), before this tree was merged into it. It was kept in `docs/safety/` and was moved unchanged to [`08-analyses/fmea/`](../08-analyses/fmea/fmea-plan.md) when `liondriver-dev` was merged. It consists of:

- YAML sources validated by JSON schemas and `tools/safety/fmea_lint.py`.
- Rating tables RT-1.
- The analyses:
  - a System FMEA, a HARA (LD-HARA-001 rev 0.3) and an FSC (rev 0.2, 40 FSRs);
  - a DFA of the panda/SoC decompositions (rev 0.4);
  - a SW FMEA of the panda safety model (rev 0.3);
  - stubs for the DFMEA, PFMEA and FMEDA.
- An item definition for the platform (334 vehicles) with the Corolla E210 variant family (LD-ITEM-001).
- A design for the panda configuration lock and firmware authenticity (LD-DES-001).

`assurance/` stays the single source of truth. The second set is kept as supporting data:

| Second-set item | Disposition | Where in `assurance/` |
|---|---|---|
| SW FMEA (`analyses/sw-fmea.yaml`) | Supporting data: AIAG-VDA S/O/D/AP ratings and test evidence | [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) §3.5; new rows SWF-49, SWF-50; OI-6 |
| System FMEA (`analyses/system-fmea.yaml`) | Supporting data; links to the SW FMEA | [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md) stays the system analysis of record |
| DFMEA (`analyses/dfmea.yaml`, rev 0.2 at BL-002) | Supporting data: AIAG-VDA rating of the WP-H-03 block-level failure modes, with candidate special characteristics | [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md) stays the hardware analysis of record |
| DFA (`analyses/dfa.yaml`) | Supporting data; no finding beyond WP-A-03 (its DM-05 correction matches DFI-10) | [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md) |
| HARA, FSC, item definition | Parallel drafts, not adopted. The FMEAs link to them, so they are kept for the trace | [WP-C-01](../02-concept/WP-C-01-item-definition.md), [WP-C-03](../02-concept/WP-C-03-hara.md), [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) |
| LD-DES-001 decisions D1–D4 | Decided as D-09…D-12 | [WP-M-01 §8](../01-management/WP-M-01-assurance-strategy.md#8-strategic-decisions-required), [WP-M-07 §5](../01-management/WP-M-07-risk-management.md) |
| LD-ITEM-001 IOI-001 (Experimental Mode) | Decided as D-08 (Chill Mode) | WP-M-01 §8 |
| Platform and variant model (`item/variants.yaml`, `item/vehicle-catalog.md`) | Input to OI-4 | [WP-M-12](../01-management/WP-M-12-impact-analysis.md) |

Like LD-HARA-001, the second-set HARA rates the lateral goal ASIL D (SG-001), with C3 at motorway speed and no credit for the EPS limit. It is a second, independent argument for OI-1 and is not a new open item. Two code findings from the second set are corrected here:

- The SoC accel limit on TSS2 is +2.0 m/s² (`RAISED_ACCEL_LIMIT`), equal to the envelope, not +1.5.
- The safety and mutation tests are run in fork CI (CR-CI-05).

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-5 | **Closed 2026-10-22 (DQ-124 A):** the second-set HARA and FSC (`analyses/hara.yaml`, `fsc.yaml`, status `withdrawn`) and the item definition LD-ITEM-001 are withdrawn; WP-C-01, WP-C-03 and WP-C-04 are of record. RD-1…RD-3 (DQ-008, DQ-036, DQ-205) and OI-4 (DQ-037, DQ-369, DQ-370) were decided first. The files stay in git; FMEA and FMEDA rows keep their HZ-/SG-0nn references through [`hara-mapping.yaml`](../08-analyses/fmea/hara-mapping.yaml), checked in CI. Renaming those IDs in the FMEA data is a later task | Safety engineer | G1 |

## 8. Second-set HARA mapped onto WP-C-03 (OI-5)

The FMEA data cites second-set hazard IDs (`HZ-0nn`) in its effects. [`hara-mapping.yaml`](../08-analyses/fmea/hara-mapping.yaml) carries each of them to the WP-C-03 hazards, hazardous events and safety goals. `tools/safety/fmea_lint.py` checks the mapping in the assurance workflow:
- every second-set hazard and goal is mapped;
- every WP-C-03 ID exists in WP-C-03;
- both ASILs match their sources;
- the stated agreement matches the ASILs;
- every difference names a decision below.

The FMEA files keep their `HZ-0nn` links, so no rating changes. If the second set is withdrawn, the mapping becomes the trace from the FMEA rows to WP-C-03.

### 8.1 Hazards

| Second set | WP-C-03 hazard | WP-C-03 events | Note |
|---|---|---|---|
| HZ-001 torque while not engaged | H-01 | HE-01.4 | |
| HZ-002 excessive steering while engaged | H-01 | HE-01.1, HE-01.2, HE-01.3 | |
| HZ-003 steering toward the lane boundary at normal magnitude | H-01 | HE-01.1, HE-01.2, HE-02.3 | WP-C-03 rates it with H-01 and the frozen command |
| HZ-004 loss of lateral control without warning | H-02 | HE-02.1, HE-02.2, HE-02.4, HE-02.5 | |
| HZ-005 unintended acceleration | H-03 | HE-03.1 … HE-03.5 | |
| HZ-006 unintended or excessive deceleration | H-04 | HE-04.1 … HE-04.5 | |
| HZ-007 insufficient or late deceleration for a lead | H-06 | HE-06.1, HE-06.2, HE-06.3 | |
| HZ-008 not released on brake or cancel | H-05 | HE-05.1, HE-05.3, HE-05.4 | |
| HZ-009 resists driver steering | H-05 | HE-05.2 | |
| HZ-010 unintended engagement | H-01, H-03 | HE-01.4 | Rated inside H-01 and H-03 |
| HZ-011 stock AEB/FCW degraded | H-08 | HE-08.1 | |
| HZ-012 driver misinformed about the automation state | H-07 | HE-07.1, HE-07.2, HE-07.3 | |
| HZ-013 automated control continues with an unresponsive driver | H-09 | HE-09.1, HE-09.2 | RD-3, decided: added in WP-C-03 v0.4 |

### 8.2 Safety goals

| Second set | ASIL | WP-C-03 | ASIL | Agreement | Cause of the difference |
|---|---|---|---|---|---|
| SG-001 steering the driver cannot counteract | **D** | SG-01 | C ⚠ | Second set higher | Controllability at motorway speed: C3 against C2 (RD-1) |
| SG-002 steering out of the lane | C | SG-01 | C | Same | |
| SG-003 loss of lateral control or wrong state without warning | B | SG-02, SG-06 | C | WP-C-03 higher | WP-C-03 v0.4: curve case re-rated C3 (DQ-059) and OS-07 at E4 (DQ-036) |
| SG-004 unintended acceleration | C | SG-03 | C ⚠ | Same | RD-2 decided for E4 (DQ-036 B); WP-C-03 v0.4 |
| SG-005 unintended or excessive deceleration | B | SG-04 | B | Same | |
| SG-006 insufficient deceleration for a lead | B | SG-06 | C | WP-C-03 higher | OS-07 at E4 (DQ-036) applies to HE-06.1 too; WP-C-03 v0.4 |
| SG-007 release on brake or cancel; do not resist steering | B | SG-05 | B | Same | |
| SG-008 unintended engagement | B | SG-01, SG-03 | C | WP-C-03 higher | Covered inside SG-01 |
| SG-009 stock AEB/FCW availability | B | SG-07 | B | Same | |
| SG-010 continued automated control with an unresponsive driver | A | SG-08 | A | Same | RD-3 decided (DQ-205 A); WP-C-03 v0.4 |

Status 2026-10-16 (WP-C-03 v0.4, the lead's answers applied): six of ten goals agree, WP-C-03 is higher on three, and the second set is higher only on SG-001 (RD-1: C2 kept until measured, DQ-008). The text below is the state before the decisions.

Six of ten goals agree. The two HARAs disagree on two ratings and one hazard. Each difference is a decision for the safety engineer (OI-1, OI-5); none can be settled by analysis alone.

### 8.3 Decisions needed

**RD-1: lateral controllability at motorway speed (this is OI-1).** Both HARAs rate the situation S3 E4.
- The second set takes **C3** (HE-002). An L2 driver may be hands-off or hands-light, and without the item's limits the deviation can exceed 1 m before a typical reaction completes.
- WP-C-03 takes **C2** (HE-01.1, HE-01.2). It credits the EPS limiting LKA torque (AOU-01) and a normal driver overpowering it (AOU-02).
- WP-C-03's own HE-02.1 records that hands-off driving is foreseeable, because openpilot does not require hands on the wheel.
- Neither assumption has been verified on the reference car. WP-C-01 plans bench and vehicle characterisation of the EPS for AOU-01, and a steering-force measurement on the vehicle for AOU-02; both are "Unverified". The panda's torque limits are copied from upstream tuning rather than derived from measurement (SWF-001.C1, SFM-ACT-001).

| Option | Consequence |
|---|---|
| C3: SG-01 becomes ASIL D | The panda safety path carries ASIL D. The FMEDA SG-001 targets become SPFM ≥ 99 % and LFM ≥ 90 %, against 96.9 % / 87.7 % today with generic rates. That is a hardware-metrics gap the comma 3X design may not be able to close without an added mechanism |
| C2: SG-01 stays ASIL C | Defensible only once AOU-01 and AOU-02 are measured on the reference car: torque fade-out, override force, and lateral deviation at the panda's torque and rate limits within the reaction time (SFM-ACT-001, SWF-ACT-003) |

*Proposal for the review:*
- Keep SG-01 at C, with the measurement as an entry condition for G1.
- Until the measurement exists, design the panda path to the D measures, and claim no controllability credit in the safety case.

**RD-2: exposure of closing on a slower lead at highway speed.**
- The second set rates it E4 (HE-008, OS-011).
- WP-C-03 rates it E3 (HE-03.3, OS-07).
- With S3 and C2 the goal is C under E4, and B under E3.

ISO 26262-3 Annex B allows exposure by duration (E3: 1–10 % of operating time) or by frequency (E4: almost every drive). Closing on a slower lead happens on almost every highway drive, but it lasts only seconds each time. An unintended-acceleration fault becomes a hazard only if it coincides with that phase, which supports a duration-based E3.

*Proposal:* keep E3, and record the duration argument and the method choice in WP-C-03 §2. If the review prefers frequency-based exposure, SG-03 becomes C, and the FSC allocation of the longitudinal checks moves up with it.

**RD-3: an unresponsive driver as a vehicle-level hazard.**
- The second set has HZ-013 with SG-010 at ASIL A (HE-018: S3 E1 C3).
- WP-C-03 has no such hazard. It treats driver monitoring as a measure that controllability relies on, whose failure is a latent fault (WP-C-04 §7).
- Two other analyses reach the second set's view:
  - the STPA proposes H-STPA-1 (engaged while the driver is not supervising) with SC-8, "reach a minimal-risk behaviour";
  - the System FMEA finds that awareness reaching zero has no disable reaction (SFM-025, SFM-ACT-005).

*Proposal:*
- Add the hazard to WP-C-03 (H-09) with an ASIL A goal.
- Define its safe state together with the open decision on what the item does at zero awareness (SFM-ACT-005). That decision is needed in any case.

