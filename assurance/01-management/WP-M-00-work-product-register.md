# WP-M-00 Work Product Register

| Field | Value |
|---|---|
| Work product | WP-M-00 Work product register |
| Standard reference | ISO 26262-2:2018 §6 (safety plan, work product list); ASPICE 4.0 MAN.3 (BP: define work products), SUP.8 (configuration items) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (openpilot-derived baseline, 2026-10-09) |

## 1. Purpose

This register lists every work product that the LionDriver assurance path requires. For each one it records the source clauses, the gate that needs it, and its current status. The [safety plan (WP-M-02)](WP-M-02-safety-plan.md) refers to this register as its list of work products, and [configuration management (WP-P-01)](../07-supporting/WP-P-01-configuration-management-plan.md) puts each entry under configuration control.

Tailoring decisions are recorded in [WP-M-01 §5](WP-M-01-assurance-strategy.md#5-tailoring). If a work product is tailored out, it stays in this register with status `N/A (tailored)` and a reference to its rationale.

## 2. Gates

| Gate | Name | Exit criterion (summary) |
|---|---|---|
| G0 | Governance | Plans approved; roles assigned; CM and change control running |
| G1 | Concept | Item definition, HARA, FSC, SOTIF hazard and insufficiency analysis, TARA and CS concept approved; confirmation review of HARA (I3) passed |
| G2 | System design | TSC, system architecture, HSI and system-level safety analyses approved |
| G3 | HW/SW development | HW and SW safety requirements, architecture, units and unit verification approved for every safety-relevant element |
| G4 | Integration and verification | SW, HW and system integration and qualification evidence complete; fault injection campaign closed |
| G5 | Validation and release | Safety validation, SOTIF residual risk acceptance, CS validation, safety case, FSA and CS assessment complete; release record signed |
| G6 | Operation | Field monitoring, incident response and update processes running |

## 3. Register

Legend for **ASPICE**: process IDs from ASPICE PAM 4.0, including the ML (MLE), validation (VAL.1) and cybersecurity (SEC) extensions.
**Status**: S = Skeleton, D = Draft, R = In review, A = Approved, B = Baselined, N/A = tailored out.

### 3.1 Management (`01-management/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-M-00](WP-M-00-work-product-register.md) | Work product register | 2 §6 | | | | MAN.3 | G0 | D |
| [WP-M-01](WP-M-01-assurance-strategy.md) | Assurance strategy and lifecycle tailoring | 2 §6 (tailoring) | §4 | §6 | PAS 8800 (AI safety management), UL 4600 §5 | MAN.3 | G0 | D |
| [WP-M-02](WP-M-02-safety-plan.md) | Functional safety plan | 2 §6 | | | | MAN.3 | G0 | D |
| [WP-M-03](WP-M-03-project-plan.md) | Project plan (scope, WBS, schedule, resources) | | | | | MAN.3 | G0 | D |
| [WP-M-04](WP-M-04-organization-competence-safety-culture.md) | Organization-specific rules, safety culture, competence management | 2 §5 | | §5 | | — | G0 | D |
| [WP-M-05](WP-M-05-quality-assurance-plan.md) | Quality management and quality assurance plan | 2 §5 (QMS) | | §5 | IATF 16949 (informative) | SUP.1 | G0 | D |
| [WP-M-06](WP-M-06-confirmation-measures-plan.md) | Confirmation measures plan (reviews, audit, assessment, independence) | 2 §6 Table 1 | §4 | §6 (assessment) | | — | G0 | D |
| [WP-M-07](WP-M-07-risk-management.md) | Project risk management plan and register | | | | | MAN.5 | G0 | D |
| [WP-M-08](WP-M-08-sotif-plan.md) | SOTIF plan | | §4, Clause 5–13 activities | | | MAN.3 | G0 | D |
| [WP-M-09](WP-M-09-cybersecurity-plan.md) | Cybersecurity plan | | | §6 | | MAN.7 (CS) | G0 | D |
| [WP-M-10](WP-M-10-ai-safety-plan.md) | AI safety management plan | | | | PAS 8800 (AI safety management, assurance argument) | MLE.1–4, SUP.11 | G0 | D |
| [WP-M-11](WP-M-11-upstream-and-supplier-management.md) | Upstream (comma.ai) and supplier management, development interface agreements | 8 §5 | | §7 | | ACQ.4 | G0 | D |
| [WP-M-12](WP-M-12-impact-analysis.md) | Impact analysis of the openpilot-derived baseline (modification of existing item) | 2 §6 (impact analysis), 8 §8 | | §6 (reuse analysis) | | SUP.10 | G0 | D |
| [WP-M-13](WP-M-13-aspice-capability-baseline.md) | ASPICE capability baseline (self-assessment) | | | | | All in scope | G0 | D |
| [WP-M-14](WP-M-14-iso26262-6-implementation-specification.md) | ISO 26262-6 software lifecycle implementation specification (future work; activation deferred, D-09) | 6 §5–11, Annex C; 8 §6–12 | | | | MAN.3, SWE.1–6 | G2 (activation), G3–G4 (use) | D |

### 3.2 Concept phase (`02-concept/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-C-01](../02-concept/WP-C-01-item-definition.md) | Item definition | 3 §5 | §5 (functionality, system) | §9.3 | | SYS.1 | G1 | D |
| [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) | ODD and intended functionality specification | 3 §5 | §5 | | PAS 8800 (input space definition) | SYS.1 | G1 | D |
| [WP-C-03](../02-concept/WP-C-03-hara.md) | Hazard analysis and risk assessment, safety goals | 3 §6 | | | | — | G1 | D |
| [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) | Functional safety concept (FSRs, allocation, AoUs) | 3 §7 | | | | SYS.2 | G1 | D |
| [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md) | SOTIF hazard identification and risk evaluation, acceptance criteria | | §6 | | | — | G1 | D |
| [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) | Functional insufficiencies and triggering conditions analysis | | §7 | | PAS 8800 (AI error causes) | — | G1 | D |
| [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md) | Functional modifications addressing SOTIF risk | | §8 | | | SYS.2 | G1 | D |
| [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) | Driver interaction, HMI and reasonably foreseeable misuse analysis | 3 §6 (controllability) | §6, Annex B | | | — | G1 | D |
| [WP-C-09](../02-concept/WP-C-09-tara.md) | Threat analysis and risk assessment (TARA) | | | §15, §9.4 | UN R155 Annex 5 (informative) | SEC.1 | G1 | D |
| [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) | Cybersecurity goals, claims and concept | | | §9.4, §9.5 | | SEC.1 | G1 | D |
| [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) | AI system definition and AI safety requirements | | §7 | | PAS 8800 (AI safety requirements) | MLE.1 | G1 | D |

### 3.3 System level (`03-system/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-S-01](../03-system/WP-S-01-system-requirements.md) | System requirements specification (functional, non-safety) | | §5 | | | SYS.2 | G2 | D |
| [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) | Technical safety requirements specification | 4 §6 | | | | SYS.2 | G2 | D |
| [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) | Technical safety concept and system architectural design | 4 §6 | §8 | | | SYS.3 | G2 | D |
| [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | Timing analysis: FTTI, fault detection and reaction budget | 4 §6 | | | | SYS.3 | G2 | D |
| [WP-S-05](../03-system/WP-S-05-hsi-specification.md) | Hardware-software interface specification | 4 §6 | | | | SYS.3 | G2 | D |
| [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md) | Requirements for production, operation, service and decommissioning | 4 §6 | §13 | §10 | | SYS.2 | G2 | D |
| [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) | Cybersecurity requirements and architectural design | | | §10 | | SEC.1, SYS.3 | G2 | D |
| [WP-S-08](../03-system/WP-S-08-system-integration-test.md) | System integration and test strategy, specification and report | 4 §7 | | | | SYS.4 | G4 | D |
| [WP-S-09](../03-system/WP-S-09-system-verification.md) | System verification (qualification) specification and report | 4 §7 | §10 | | | SYS.5 | G4 | D |

### 3.4 Hardware level (`04-hardware/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md) | Hardware safety requirements specification | 5 §6 | | | | HWE.1 | G3 | D |
| [WP-H-02](../04-hardware/WP-H-02-hardware-design.md) | Hardware architectural and detailed design (device, panda MCU, harness, relay) | 5 §7 | | | | HWE.2 | G3 | D |
| [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md) | Hardware safety analysis (FMEA/FMEDA) | 5 §7, §8 | | | | HWE.2 | G3 | D |
| [WP-H-04](../04-hardware/WP-H-04-hardware-metrics.md) | Hardware architectural metrics (SPFM, LFM) | 5 §8 | | | | — | G3 | D |
| [WP-H-05](../04-hardware/WP-H-05-random-hardware-failures-pmhf.md) | Evaluation of safety goal violations due to random HW failures (PMHF) | 5 §9 | | | | — | G3 | D |
| [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) | Hardware integration and verification specification and report | 5 §10 | | | | HWE.3, HWE.4 | G4 | D |
| [WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md) | Qualification of hardware components (comma device, STM32H7, harness) | 8 §13 | | | 26262-11 (semiconductors, informative) | — | G3 | D |

### 3.5 Software level (`05-software/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-W-01](../05-software/WP-W-01-software-development-environment-guidelines.md) | SW development environment, languages and coding guidelines | 6 §5 | | §10 | MISRA C:2012 | SWE.3 | G3 | D |
| [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) | Software safety requirements specification | 6 §6 | | | | SWE.1 | G3 | D |
| [WP-W-03](../05-software/WP-W-03-software-architecture.md) | Software architectural design | 6 §7 | | | | SWE.2 | G3 | D |
| [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) | Software safety analysis and software-level DFA | 6 §7, 9 §7–8 | | | | SWE.2 | G3 | D |
| [WP-W-05](../05-software/WP-W-05-software-unit-design.md) | Software unit design and implementation | 6 §8 | | §10 | | SWE.3 | G3 | D |
| [WP-W-06](../05-software/WP-W-06-software-unit-verification.md) | Software unit verification specification and report (static analysis, MISRA, coverage, mutation) | 6 §9 | | §10 | | SWE.4 | G3 | D |
| [WP-W-07](../05-software/WP-W-07-software-integration-verification.md) | Software integration and verification specification and report | 6 §10 | | | | SWE.5 | G4 | D |
| [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md) | Testing of the embedded software (SW qualification, HIL) | 6 §11 | | | | SWE.6 | G4 | D |
| [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md) | Safety-related configuration and calibration data (car params, fingerprints, limits, model weights) | 6 Annex C | | | | SWE.3 | G3 | D |
| [WP-W-10](../05-software/WP-W-10-ml-engineering.md) | ML engineering: model requirements, data management, training, testing, deployment | | §7, §10 | | PAS 8800 (data, V&V, AI architecture) | MLE.1–4, SUP.11 | G3 | D |
| [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) | Cybersecurity implementation and verification | | | §10 | | SEC.2, SEC.3 | G3 | D |

### 3.6 Validation (`06-validation/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-V-01](../06-validation/WP-V-01-safety-validation.md) | Safety validation plan, specification and report | 4 §8 | | | | VAL.1 | G5 | D |
| [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) | SOTIF verification and validation strategy, validation targets | | §9 | | PAS 8800 (AI V&V) | VAL.1 | G2 | D |
| [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) | Evaluation of known hazardous scenarios | | §10 | | | SYS.5, VAL.1 | G4 | D |
| [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md) | Evaluation of unknown hazardous scenarios | | §11 | | | VAL.1 | G5 | D |
| [WP-V-05](../06-validation/WP-V-05-fault-injection.md) | Fault injection test specification and report | 4 §7, 5 §10, 6 §10–11 | | | | SYS.4, SWE.6 | G4 | D |
| [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md) | Cybersecurity validation and penetration testing | | | §11 | | SEC.4 | G5 | D |
| [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) | Vehicle test operations and safety-driver procedures | 4 §8 | §10–11 | | SAE J3018 (informative) | VAL.1 | G1 | D |

### 3.7 Supporting processes (`07-supporting/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) | Configuration management plan (incl. safety-relevant file list, baselines, submodules) | 8 §7 | | §5 | | SUP.8 | G0 | D |
| [WP-P-02](../07-supporting/WP-P-02-change-management.md) | Change management plan | 8 §8 | | §6 | | SUP.10 | G0 | D |
| [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) | Problem resolution management | 2 §5 (anomaly handling) | §13 | §8 | | SUP.9 | G0 | D |
| [WP-P-04](../07-supporting/WP-P-04-documentation-management.md) | Documentation management | 8 §10 | | §5 | | SUP.7 (informative) | G0 | D |
| [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) | Verification and review procedure | 8 §9 | | | | SUP.2 (informative) | G0 | D |
| [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) | Requirements management and traceability procedure | 8 §6 | | | | SYS.2, SWE.1 (traceability BPs) | G0 | D |
| [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) | Software tool classification and qualification | 8 §11 | | §5 (tool management) | | — | G3 | D |
| [WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md) | Qualification of software components (third-party and upstream software) | 8 §12 | | §10 (reuse, OSS) | | — | G3 | D |
| [WP-P-09](../07-supporting/WP-P-09-proven-in-use.md) | Proven-in-use argument evaluation | 8 §14 | | | | — | G3 | D |
| [WP-P-10](../07-supporting/WP-P-10-release-management.md) | Release management and baseline procedure | 2 §6 (release), 8 §7 | | §6 (release for post-development) | | SUP.8 | G5 | D |

### 3.8 Safety analyses (`08-analyses/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md) | ASIL decomposition rationale | 9 §5 | | | | — | G2 | D |
| [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) | Coexistence of elements and freedom from interference | 9 §6 | | | | — | G2 | D |
| [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md) | Dependent failure analysis | 9 §7 | | | | — | G2 | D |
| [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md) | System-level safety analyses (FTA, FMEA) | 9 §8, 4 §6 | §7 | | | — | G2 | D |

### 3.9 Production, operation and decommissioning (`09-production-operation/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) | Installation, provisioning and production control | 7 §5 | | §12 | | — | G5 | D |
| [WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) | Operation, service (maintenance, repair) and decommissioning | 7 §6 | | §14 | | — | G5 | D |
| [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md) | User information and safety warnings | 7 §6 | §6 (misuse), §13 | | | — | G5 | D |
| [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) | Field monitoring (safety, SOTIF and AI) and crash reporting | 2 §7 | §13 | §8 | PAS 8800 (operation phase), NHTSA SGO (US) | — | G6 | D |
| [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) | Cybersecurity incident response, vulnerability management and software updates | | | §8, §13 | UN R156 (informative) | SEC.* | G6 | D |

### 3.10 Assurance cases and release (`10-safety-case/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-K-01](../10-safety-case/WP-K-01-safety-case.md) | Safety case (GSN, integrated FuSa, SOTIF and AI argument) | 2 §6 | §12 | | UL 4600, PAS 8800 (assurance argument) | — | G1→G5 (living) | D |
| [WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md) | SOTIF achievement evaluation and release recommendation | | §12 | | | — | G5 | S |
| [WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md) | Cybersecurity case | | | §6 | | — | G5 | D |
| [WP-K-04](../10-safety-case/WP-K-04-functional-safety-assessment.md) | Functional safety assessment report (performed independently, I3) | 2 §6 | | | | — | G5 | S |
| [WP-K-05](../10-safety-case/WP-K-05-cybersecurity-assessment.md) | Cybersecurity assessment report (performed independently) | | | §6 | | — | G5 | S |
| [WP-K-06](../10-safety-case/WP-K-06-release-record.md) | Release for production / release record | 2 §6, 4 §9 | §12 | §6 | | SUP.8 | G5 | S |

### 3.11 Traceability (`trace/`)

| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |
|---|---|---|---|---|---|---|---|---|
| [WP-T-01](../trace/README.md) | Requirements and traceability data (machine-readable), consistency evidence | 8 §6 | | §10 | | 13-51 consistency evidence (SYS.2–5, SWE.1–6) | G1→G5 | D |

## 4. Work products the standards define that are covered elsewhere

| Standard work product | Where it is covered |
|---|---|
| Safety goals (26262-3 §6) | [WP-C-03 HARA §6](../02-concept/WP-C-03-hara.md) |
| Verification review reports (26262-3 §6–7, 4 §6, etc.) | Pull request review records, logged through [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) |
| Confirmation review reports (26262-2 §6) | Records under `10-safety-case/confirmation/` (folder to be created), created per [WP-M-06](WP-M-06-confirmation-measures-plan.md) |
| Functional safety audit report (26262-2 §6) | [WP-M-06](WP-M-06-confirmation-measures-plan.md) §audit; record under `10-safety-case/confirmation/` (folder to be created) |
| Safety analysis at HW level (26262-5 §7) | [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md) |
| Specification of requirements for production, operation, service, decommissioning (26262-4 §6) | [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md) |
| Cybersecurity claims (21434 §9.4) | [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) |
| Vulnerability analysis and management (21434 §8) | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |

## 5. Not applicable

| Standard part | Rationale |
|---|---|
| ISO 26262-12 (motorcycles) | The item is fitted to a passenger car (M1) |
| ISO 26262-11 (semiconductors) as a source of required work products | Informative guidance only. Used as input to WP-H-07 for the STM32H7 safety MCU and the SoC |
| ISO 26262-10 | Informative guideline; produces no work products |
| UL 4600 conformance | UL 4600 covers autonomous products without a human driver. LionDriver is a supervised Level 2 system, so UL 4600 is used only as guidance for structuring the safety case (WP-K-01). No conformance claim is made |
