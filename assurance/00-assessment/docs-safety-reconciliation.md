# Reconciliation of the earlier `docs/safety/` drafts

| Field | Value |
|---|---|
| Work product | Reconciliation record (supporting document, not a registered work product) |
| Standard reference | ISO 26262-8:2018 §7 (configuration management), §8 (change management) |
| Version | 0.2 |
| Status | Draft |
| Author | Assurance team |
| Reviewer(s) | TBD |
| Baseline | `docs/safety/` as last present at LionDriver `14e18b3` |

## 1. Purpose

Two sets of safety drafts were written in parallel:

- `docs/safety/` on branch `claude/safety-framework-docs`: safety plan LD-SPL-001, item definition LD-ITD-001, HARA LD-HARA-001, functional safety concept LD-FSC-001 and technical safety concept LD-TSC-001, each as a JSON source, a generator script and an xlsx workbook; plus a `configurations/` folder for the 2020 Corolla.
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
| LD-FSC-001 gaps G1–G5 | Covered | G1: GAP-07, GAP-08, GAP-11, TSR-502, TSR-503, TSR-515. G2: GAP-06, [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md). G3: [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md). G4: WP-C-05 SH-04. G5: GAP-01, TSR-405, [WP-V-05](../06-validation/WP-V-05-fault-injection.md) VS-FI-01/02/05 |
| LD-TSC-001 technical safety concept | Superseded | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) |
| LD-TSC-001 G1 layer 1 (firmware measures: IWDG, latched no-output, ECC, code CRC, start-up tests) | Covered | TSR-502, TSR-503, TSR-515 |
| LD-TSC-001 G1 layer 2 (relay supervisor) and layer 3 (monitoring MCU) | Carried over as design input | §5; §6 OI-3 |
| `configurations/toyota-corolla-2020/` parameter baseline | Covered | [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md) CD-01 and the envelope limit table |
| `configurations/toyota-corolla-2020/` XZACT equivalence evidence | Carried over | WP-W-06 §3.3 and §4.8 |
| `standards.md` (how each standard is applied) | Superseded | [README](../README.md), WP-M-01 |

## 3. Differences between the two HARAs

The two HARAs rate the same functions but reach different results. Both are unreviewed drafts.

| Topic | LD-HARA-001 (`docs/safety/`) | WP-C-03 (`assurance/`) |
|---|---|---|
| Scope | Platform as a Safety Element out of Context over a declared operating envelope; each vehicle checks the platform's assumptions | The reference configuration (2020 Corolla LE, TSS2) as the item; other vehicles join through impact analysis ([WP-M-12](../01-management/WP-M-12-impact-analysis.md)) |
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
| ASM-V-03 | Pedal state on CAN, fast and protected | AOU-03; GAP-01 (`0x226` has no checksum or counter) |
| ASM-V-04 | Engagement needs a deliberate driver action | FSR-01.05 (authority only on the PCM cruise rising edge); GAP-01 |
| ASM-V-05 | Speed signals with fault indication | GAP-01 (`0xAA` has no checksum); TSR-405 |
| ASM-V-06 | All commands pass through the harness | TSR-506, TSR-701; WP-S-03 AP-4 |
| ASM-V-07 | Powertrain honors acceleration limits | AOU-05 |
| ASM-V-08 | Stock emergency braking available | AOU-04; SG-07 |

## 5. Design input carried over: independent relay disable path

LD-TSC-001 proposed three layers for panda MCU faults. Layer 1 (firmware measures) is already covered by TSR-502, TSR-503 and TSR-515. Layers 2 and 3 have no counterpart in `assurance/` yet:

- **Layer 2, relay supervisor.** Today the panda holds the harness relay closed with a steady GPIO level, so a hang can hold it closed (GAP-43). Driving the relay through an AC-coupled stage from a toggling signal means only running, healthy firmware can keep it closed: stuck high, stuck low, hang and reset all open it, with no software involved. Opening the relay restores the stock camera path.
- **Layer 3, diverse monitoring MCU.** A second microcontroller checks torque limits and brake release independently. Only needed if the panda FMEDA ([WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md)) shows that layers 1 and 2 cannot reach the hardware metrics for the assigned ASIL.

Decision rule proposed in LD-TSC-001: implement layer 1, design layer 2, then let the FMEDA decide on layer 3.

## 6. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Decide the controllability ratings at motorway speed for H-01, H-03, H-04 and H-05 (§3). Either justify the C2 credit for OEM EPS and PCM limits or re-rate to C3, and record the rationale in WP-C-03. Close LD-SPL-001 anomaly A04 with the outcome | Safety engineer, I3 reviewer | G1 |
| OI-2 | Confirm that rating uncommanded engagement, driver-monitoring failure and mode confusion inside other hazards (§3) does not lose a safety goal; record the review in WP-C-03 | Safety engineer | G1 |
| OI-3 | Evaluate the relay supervisor (§5) as a mechanism for GAP-43 and TSR-502 in WP-S-03 and [WP-H-02](../04-hardware/WP-H-02-hardware-design.md) | HW lead | G2 |
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
| SW FMEA (`analyses/sw-fmea.yaml`) | Supporting data: AIAG-VDA S/O/D/AP ratings and test evidence | [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) §3.5; new rows SWF-48, SWF-49; OI-6 |
| System FMEA (`analyses/system-fmea.yaml`) | Supporting data; links to the SW FMEA | [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md) stays the system analysis of record |
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
| OI-5 | Decide whether the second-set HARA, FSC and item definition are withdrawn once WP-C-01/03/04 settle OI-1, OI-2 and OI-4, and re-point the FMEA data at WP-C-03 hazard IDs | Safety engineer | G1 |
