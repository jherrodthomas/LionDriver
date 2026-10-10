# WP-M-06 Confirmation Measures Plan

| Field | Value |
|---|---|
| Work product | WP-M-06 Confirmation measures plan (reviews, audit, assessment, independence) |
| Standard reference | ISO 26262-2:2018 §6 (confirmation measures; Table 1 independence scheme); ISO 21448:2022 §4 (SOTIF management, release argument review); ISO/SAE 21434:2021 §6 (cybersecurity assessment); ISO/PAS 8800:2024 (assurance argument review, informative) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All. Planned to ASIL D until the HARA ([WP-C-03](../02-concept/WP-C-03-hara.md)) is approved |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review of this plan by external assessor (I3 planned) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose

This plan defines the confirmation measures for LionDriver: which work products get a confirmation review and at what independence, when the functional safety audits and assessments take place, who may perform them, and where the records go. It also covers the equivalent independent evaluations for SOTIF and cybersecurity.

No confirmation measure has been performed at baseline `8b8c6ae`. No assessor has been engaged (D-06 open).

Confirmation measures are separate from verification reviews. Verification reviews (normally by pull request, per [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md)) check a work product against its inputs and requirements. Confirmation measures check that the work product, the process and the overall result meet ISO 26262 and are adequate for the safety argument.

## 2. Planning assumptions

- **ASIL.** The HARA is not done. For planning, every safety goal is assumed to be ASIL D, and every confirmation measure is planned at the independence level ISO 26262-2 Table 1 sets for ASIL D. When the HARA is approved, the safety manager re-plans (OI-2). Lowering independence needs a recorded rationale.
- **Tailoring.** WP-M-01 T-09: verification reviews may be done by project members at I0/I1. Confirmation measures at I2 and I3 are performed by an external party because the project has one maintainer.
- **Scope.** Confirmation measures apply to the reference configuration ([WP-M-01 §3.1](WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to)).

## 3. Independence levels

Summary in our own words. The licensed standard is authoritative.

| Level | Meaning (summary) | Who can do it in LionDriver today |
|---|---|---|
| I0 | The measure should be performed; it may be done by the same person who produced the work | Maintainer (self-check) |
| I1 | Performed by a person other than the one who produced the work product | Any competent contributor other than the author. Nobody available yet |
| I2 | Performed by a person independent of the team responsible for the work product (not reporting to the same direct line) | External reviewer only (single-maintainer project) |
| I3 | Performed by a person independent, in management, resources and release authority, from the department responsible for the work product | External assessor only |

## 4. Confirmation reviews

### 4.1 List and independence

Rows follow the structure of ISO 26262-2 Table 1. The "ASIL dependency" column is an indicative summary of how the required level changes with ASIL; check each row against the licensed copy before the first review (OI-1). The "Planned" column is what LionDriver will do under the ASIL D assumption, and in every case is at least as strict as the indicative requirement.

| # | Confirmation review of | LionDriver work product(s) | ASIL dependency (indicative, verify) | Planned | Performed by | Gate |
|---|---|---|---|---|---|---|
| CR-01 | Impact analysis of the modified item and reuse of existing elements | [WP-M-12](WP-M-12-impact-analysis.md) | High independence regardless of ASIL | I3 | External FuSa assessor | G0 |
| CR-02 | Hazard analysis and risk assessment, including safety goals | [WP-C-03](../02-concept/WP-C-03-hara.md) (with [WP-C-01](../02-concept/WP-C-01-item-definition.md), [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) as inputs) | Highest level (I3) at every ASIL | I3 | External FuSa assessor | G1 |
| CR-03 | Safety plan (incl. tailoring rationale) | [WP-M-02](WP-M-02-safety-plan.md), [WP-M-01 §5](WP-M-01-assurance-strategy.md#5-tailoring), this plan | Rises with ASIL; I3 at ASIL D | I3 | External FuSa assessor | G0 (re-confirm at G1 after HARA) |
| CR-04 | Functional safety concept | [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) | Rises with ASIL; I3 at ASIL D | I3 | External FuSa assessor | G1 |
| CR-05 | Technical safety concept | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md), [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md), [WP-S-05](../03-system/WP-S-05-hsi-specification.md) | Rises with ASIL; I3 at ASIL D | I3 | External FuSa assessor | G2 |
| CR-06 | Safety analyses and dependent failure analyses (system, HW, SW) | [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md)…[WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md), [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md), [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) | Rises with ASIL; I3 at ASIL D | I3 | External FuSa assessor | G2 (system), G3 (HW, SW) |
| CR-07 | Evaluation of hardware architectural metrics and random HW failure targets | [WP-H-04](../04-hardware/WP-H-04-hardware-metrics.md), [WP-H-05](../04-hardware/WP-H-05-random-hardware-failures-pmhf.md) | Check whether a separate row exists in the licensed edition; otherwise covered by CR-06 and the FSA | I3 | External FuSa assessor | G3 |
| CR-08 | Qualification of hardware components | [WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md) | Rises with ASIL; may be below I3 at ASIL D (verify) | I3 | External FuSa assessor | G3 |
| CR-09 | Software tool qualification (completeness of documentation) | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) | Rises with ASIL; may be below I3 at ASIL D (verify) | I2 minimum, I3 if combined with CR-08 session | External reviewer or assessor | G3 |
| CR-10 | Qualification of software components | [WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md) | Check whether listed in the licensed edition; planned regardless because upstream reuse is central (T-05) | I2 minimum | External reviewer or assessor | G3 |
| CR-11 | Proven-in-use argument | [WP-P-09](../07-supporting/WP-P-09-proven-in-use.md) | Rises with ASIL; I3 at ASIL D | **Not planned while no proven-in-use claim is made (T-06).** Becomes I3 if a claim is introduced | — | — |
| CR-12 | Safety case (completeness) | [WP-K-01](../10-safety-case/WP-K-01-safety-case.md) | Rises with ASIL; I3 at ASIL D | I3 | External FuSa assessor | G5 (interim look at G1, G2 as part of the interim FSA) |

Integration, verification and validation plans and reports are not listed as separate confirmation reviews here; they are examined by the functional safety assessment (§6) and audits (§5). If the licensed edition requires them as confirmation reviews at the applicable ASIL, rows are added (OI-1).

### 4.2 Procedure

1. The safety manager opens an issue `CR-nn <WP-ID>` in the gate milestone, naming the work product version and baseline commit.
2. Entry criteria: the work product is at least `Draft`, its verification review per WP-P-05 is complete, and its open items are listed.
3. The reviewer evaluates compliance with ISO 26262 (and, for CR-03, with this project's tailoring) and adequacy for the safety argument.
4. Outcome: `Confirmed`, `Confirmed with findings` (findings tracked as issues), or `Not confirmed`.
5. Record stored as `10-safety-case/confirmation/CR-nn-<WP-ID>-v<version>.md` (folder to be created, OI-6).
6. If the work product changes after confirmation in a way that the change impact analysis ([WP-P-02](../07-supporting/WP-P-02-change-management.md)) classifies as safety-relevant, the confirmation review is repeated or its scope is extended.

## 5. Functional safety audit

**Purpose:** check that the processes in the safety plan are actually carried out as planned.

| Item | Plan |
|---|---|
| Independence | I3 planned (ASIL D assumption). Performed by the external FuSa assessor or an auditor of equivalent independence |
| Timing | AUD-1 after G2 entry (process in use for concept and system design); AUD-2 before G4 (development, verification, tool use). Additional audit if a major process change occurs |
| Scope | Implementation of WP-M-02 and the supporting procedures WP-P-01…P-10; change control on safety-relevant files; review independence actually achieved; anomaly handling; tool use vs. WP-P-07; adherence to the upstream sync freeze (D-02) |
| Inputs | WP-M-02, WP-M-05 QA reports, sample of PRs and issues, CI records, gate records |
| Output | Audit report with findings; findings handled through WP-P-03 |
| Record | `10-safety-case/confirmation/AUD-<n>.md` |

Routine QA audits ([WP-M-05](WP-M-05-quality-assurance-plan.md)) are separate and more frequent. The functional safety audit may sample their results but does not replace them, and vice versa.

## 6. Functional safety assessment

**Purpose:** judge whether the functional safety achieved by the item is adequate.

| Item | Plan |
|---|---|
| Scope | The item in its reference configuration; the work products in WP-M-00 with an ISO 26262 reference; the confirmation review and audit results; the safety case; the implementation of the safety measures in the released code and firmware |
| Interim assessment FSA-I1 | At G1: concept-phase work products (item definition, HARA, FSC), tailoring, planning. Purpose: early agreement on the safety argument before system design |
| Interim assessment FSA-I2 | At G2: TSC, FFI/DFA, the decision on the hardware route (single-channel panda, possible decomposition or external monitor) |
| Final assessment FSA-F | At G5, before the release record ([WP-K-06](../10-safety-case/WP-K-06-release-record.md)) is signed. Result: recommendation for acceptance, conditional acceptance, or rejection |
| Report | [WP-K-04](../10-safety-case/WP-K-04-functional-safety-assessment.md) (final); interim reports `10-safety-case/confirmation/FSA-I1.md`, `FSA-I2.md` |
| Independence | I3, external (T-09) |
| Use of results | The release record cites the FSA result. A rejection blocks release. Conditions become tracked issues with owners |

### 6.1 Assessor qualification and independence

| Requirement | Detail |
|---|---|
| Independence | No authorship of, and no contribution to, the assessed work products; no reporting line to the project maintainer; no financial interest in LionDriver release beyond the assessment fee; not involved in upstream comma.ai development of the assessed code. Declared in writing in each report |
| Competence | Functional safety at expert level (WP-M-04 §4.2): demonstrated by prior ISO 26262 assessments of road-vehicle E/E systems, ideally including driver assistance with ML-based perception and retrofit or COTS hardware. A recognized FuSa certification is preferred but not by itself sufficient |
| Breadth | Able to judge the SOTIF interface (WP-M-01 §4.1 driver and DM argument). If not, a SOTIF reviewer is added (§7) |
| Continuity | The same assessor (or organization) for interim and final assessments where possible |
| Conflicts | If the same person performs confirmation reviews, audits and the assessment, this is acceptable under ISO 26262 as long as independence from the project holds; it is declared |

## 7. SOTIF and AI evaluation

ISO 21448 does not define independence levels like ISO 26262-2 Table 1. LionDriver plans an equivalent independent evaluation because the SOTIF argument (G2 in WP-M-01 §3.2) is at least as critical as the FuSa argument for an ML-driven function.

| Measure | Object | Independence (planned) | Gate | Record |
|---|---|---|---|---|
| SR-01 Review of SOTIF hazard identification and acceptance criteria | [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md), [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) | External reviewer with SOTIF competence (equivalent to I3) | G1 | `10-safety-case/confirmation/SR-01.md` |
| SR-02 Review of V&V strategy and validation targets | [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) | Same | G2 | `SR-02.md` |
| SR-03 Review of SOTIF release argument and residual risk | [WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md), [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md), [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md) | Same | G5 | `SR-03.md` |
| SR-04 Review of AI assurance argument (PAS 8800) | [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md), [WP-W-10](../05-software/WP-W-10-ml-engineering.md), AI part of WP-K-01 | External reviewer with ML safety competence | G3, G5 | `SR-04-<gate>.md` |

These may be performed by the FuSa assessor if they meet the competence requirement (§6.1); otherwise by a separate reviewer.

## 8. Cybersecurity assessment

Per ISO/SAE 21434 §6 and [WP-M-09](WP-M-09-cybersecurity-plan.md).

| Item | Plan |
|---|---|
| Scope | Cybersecurity plan execution; TARA ([WP-C-09](../02-concept/WP-C-09-tara.md)); goals and concept ([WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md)); requirements and architecture ([WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md)); implementation and verification ([WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md)); validation and pen test ([WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md)); incident response ([WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)); cybersecurity case ([WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md)) |
| Interim review CS-I1 | At G1: TARA and cybersecurity goals, including links to safety goals |
| Final assessment | At G5: [WP-K-05](../10-safety-case/WP-K-05-cybersecurity-assessment.md); input to the release for post-development |
| Independence | External assessor independent of the project; independence rigor scaled to the highest CAL in the TARA, using the ISO 26262 scheme as guidance. Planned as fully external |
| Competence | CS expert per WP-M-04 §4.2, with embedded firmware signing and OTA experience |
| Pen tester | Separate from the assessor where possible; results feed WP-V-06 |

## 9. Schedule summary

| Gate | Confirmation measures due |
|---|---|
| G0 | CR-01, CR-03 |
| G1 | CR-02, CR-03 (re-confirm), CR-04; FSA-I1; SR-01; CS-I1 |
| G2 | CR-05, CR-06 (system); FSA-I2; AUD-1; SR-02 |
| G3 | CR-06 (HW, SW), CR-07, CR-08, CR-09, CR-10; SR-04 |
| G4 | AUD-2 |
| G5 | CR-12; FSA-F (WP-K-04); SR-03, SR-04; CS assessment (WP-K-05) |

## 10. Records

All confirmation records are stored in `assurance/10-safety-case/confirmation/` (folder to be created). Each record contains: identifier; object (work product ID, version, baseline commit); reviewer name and independence declaration; date; method; findings with IDs; outcome. Findings are tracked as GitHub issues labelled `confirmation-finding` and resolved via [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md). The register (WP-M-00 §4) points here for confirmation review and audit reports.

## 11. Open items

| ID | Open item | Owner | Due |
|---|---|---|---|
| OI-1 | Check every row of §4.1 against ISO 26262-2:2018 Table 1 in the licensed copy (rows present, independence per ASIL) and correct the indicative column | SM | G0 |
| OI-2 | Re-plan independence after HARA approval; record rationale for any reduction from the ASIL D assumption | SM | G1 |
| OI-3 | Engage the external FuSa assessor (D-06) and agree whether SOTIF/AI reviews (§7) are in their scope | PM | G0 |
| OI-4 | Identify a cybersecurity assessor and a pen tester; agree independence statement | CSM | G1 |
| OI-5 | CR-01 and CR-03 are due at G0 but no assessor is engaged; decide whether G0 can pass with them scheduled rather than performed | SM | G0 |
| OI-6 | Create `10-safety-case/confirmation/` and a record template | SM | G0 |
