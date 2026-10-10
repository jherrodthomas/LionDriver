# WP-M-14 ISO 26262-6 Software Lifecycle Implementation Specification

| Field | Value |
|---|---|
| Work product | WP-M-14 ISO 26262-6 software lifecycle implementation specification (future work) |
| Standard reference | ISO 26262-6:2018 Clauses 5–11 and Annex C; interfaces to ISO 26262-2, -3, -4, -8, -9. Informative links to ISO 21448:2022, ISO/SAE 21434:2021, ISO/PAS 8800:2024, UL 4600 |
| Version | 0.1 |
| Status | Draft — **implementation deferred.** This is a plan. It does not authorize, start or evidence any Part 6 activity |
| Activation | Not authorized. Needs decision D-09 ([WP-M-01 §8](WP-M-01-assurance-strategy.md#8-strategic-decisions-required)) and an approved entry baseline (§3) |
| ASIL / scope | Software of the item. Highest proposed ASIL is C (SG-01, [WP-C-03](../02-concept/WP-C-03-hara.md)); ratings are unconfirmed until CR-02 |
| Author | Project maintainer (specification). Adapted to this repository with AI assistance (Claude Code); the adaptation is AI-generated and has not been reviewed |
| Reviewer(s) | TBD (I1, external while the project has a single maintainer; [WP-M-01 T-09](WP-M-01-assurance-strategy.md#5-tailoring)) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `3ed97c8` (repository state inspected for §3.2) |

> [!IMPORTANT]
> This document describes **how** the software-level lifecycle will be implemented once its prerequisites are mature. It records no completed activity. Nothing here is evidence of ISO 26262-6 conformity, ASIL capability or safety. The drafts that already exist in [`05-software/`](../05-software/) are pre-entry drafts (§2.3), not Part 6 execution.

## 1. Purpose and scope

LionDriver already has draft software work products WP-W-01…WP-W-11, written by back-filling from the inherited openpilot, opendbc and panda code ([WP-M-01 T-03](WP-M-01-assurance-strategy.md#5-tailoring)). What it does not yet have is a controlled way to run the ISO 26262-6 lifecycle on them. That means records rather than prose, enforced trace links, evidence bound to exact builds and configurations, review controls, and a link into the Living Safety Case.

This specification fixes that blueprint before work starts. It:

1. sets the engineering principles that govern the software lifecycle (§2),
2. defines entry criteria and records a preliminary readiness snapshot of the prerequisites (§3),
3. specifies each Clause 5–11 activity against the existing repository (§4),
4. defines interfaces to the supporting processes and other parts of the standard (§5),
5. specifies reuse assessment (§6), configuration-specific assurance (§7), traceability (§8), Living Safety Case integration (§9), repository layout (§10), the register extension (§11), automation (§12) and the dashboard (§13),
6. sets acceptance criteria (§14) and the phase sequence (§15),
7. lists what may and may not be done before activation (§16).

Out of scope: the content of software safety requirements, architecture, analyses or verification results. Those come from the activities this document plans. They are not produced by this document.

The licensed text of ISO 26262 is authoritative. No standard text is reproduced here. Clause references are to the 2018 edition and must be checked against the licensed copy before use in an audit.

## 2. Engineering principles

### 2.1 Evidence, not documentation theatre

| Rule | Consequence in this repository |
|---|---|
| A template is not evidence | Templates live in a template location (§10) and carry no status. A work product copied from a template starts at `Planned` or `Skeleton` |
| A passing CI run is not approval | CI results are evidence inputs. They never change a `review_state` ([`case/README.md` §4](../case/README.md)) |
| A test is not verification of a requirement | A requirement is verified only when a reviewed verification record links that requirement to a result on an identified build and configuration (§8) |
| No invented numbers | Coverage, timing, resource figures and metrics appear only when measured, with the build, tool version and command recorded. Otherwise the record says `Not established` |
| Drafts stay drafts | AI- or tool-generated content is marked as such and stays below `Approved` until a named human reviewer accepts it (§2.5) |

### 2.2 Status vocabulary

The specification calls for more statuses than the current work product convention ([`assurance/README.md`](../README.md): Skeleton, Draft, In review, Approved, Baselined). The proposed mapping below is adopted in Phase B (§15). It is not applied to existing documents yet.

| Specification status | Current convention | Requirement `status` ([WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md)) | Case record ([schema](../case/schema/case-schema.json)) | Meaning |
|---|---|---|---|---|
| Planned | (none; propose adding) | — | — | Identified in the register; no content |
| Draft | Skeleton / Draft | `proposed` | `draft` | Content exists; not reviewed |
| In development | Draft | `agreed` → `implemented` | `in-progress` | Being worked against an approved input |
| In review | In review | — | `review-required` / `in-review` | Verification review open |
| Approved | Approved | `agreed` | `accepted` | Review passed at the independence level required by [WP-M-06](WP-M-06-confirmation-measures-plan.md) |
| Verified | (none; propose adding) | `verified` | evidence `available` + review `accepted` | Approved, and its verification records are accepted for a named baseline and configuration |
| Superseded | (none; propose adding) | `withdrawn` (requirements) | baseline `superseded` | Replaced; kept for history |
| Not applicable | N/A (tailored) | `withdrawn` | `withdrawn` | Tailored out, with rationale ([WP-M-01 §5](WP-M-01-assurance-strategy.md#5-tailoring)) |

Allowed transitions are checked by tooling (§12). Leaving out a state is not allowed. For example, a record cannot go from `Draft` to `Verified`.

### 2.3 Treatment of the existing WP-W drafts

WP-W-01…WP-W-11 were written before the system-level inputs were approved. When Part 6 is activated:

- they stay at `Draft` and act as **inputs** to Phase A (§15), not as completed Clause 5–11 outputs;
- every SWSR in [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) keeps its ID, but stays `proposed` until its parent TSR is approved (CR-05) and the SWSR itself is reviewed;
- statements about the code at `8b8c6ae` are rechecked against the entry baseline before they are reused.

### 2.4 Upstream compatibility

LionDriver keeps upstream openpilot behaviour and the upstream vehicle list unless a safety requirement forces a change. Part 6 work must not restructure application code for documentation convenience. Code changes come only from approved software safety requirements, through [WP-P-02](../07-supporting/WP-P-02-change-management.md) change requests. Each change records its effect on upstream functionality and on configurations outside the claimed scope. Supporting a vehicle is not the same as having assurance evidence for it (§7).

### 2.5 Human-controlled decisions

| Activity | Automation may | Only an authorized human may |
|---|---|---|
| Requirements | Check syntax, attributes, uniqueness, links; propose wording | Accept, allocate an ASIL, approve |
| Trace links | Propose candidate links, flagged `proposed-by: tool` | Record a link as approved |
| Analyses (FMEA, FTA, DFA, FFI) | Generate worksheets, check completeness | Rate, conclude, approve |
| Verification | Run tests, collect results, compute coverage | Judge pass/fail of a requirement, accept anomalies, approve reports |
| Safety case | Compute status, flag stale evidence | Accept a claim, change a review state |

Reviewers and independence levels are those of [WP-M-06](WP-M-06-confirmation-measures-plan.md) and [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md).

## 3. Entry criteria and readiness

### 3.1 Entry criteria

Part 6 implementation (Phases B–F, §15) starts only when the project maintainer has recorded, as decision D-09, approval of an **entry baseline**. The entry baseline is a git revision plus the approved versions of the work products below, with any exception justified in writing.

| # | Prerequisite | Work product | Minimum state for entry | Confirmation measure |
|---|---|---|---|---|
| E-01 | Safety plan, tailoring | [WP-M-02](WP-M-02-safety-plan.md), [WP-M-01 §5](WP-M-01-assurance-strategy.md#5-tailoring) | Approved | CR-03 passed |
| E-02 | Item definition | [WP-C-01](../02-concept/WP-C-01-item-definition.md) | Approved | — |
| E-03 | HARA and safety goals | [WP-C-03](../02-concept/WP-C-03-hara.md) | Approved | CR-02 passed (I3) |
| E-04 | Functional safety concept, FSRs | [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) | Approved | CR-04 passed |
| E-05 | TSRs, technical safety concept, system architecture | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) | Approved for the software-allocated TSRs | CR-05 passed |
| E-06 | Timing budget (FTTI) | [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | Approved, with measured values where software timing is credited | Part of CR-05 |
| E-07 | HSI | [WP-S-05](../03-system/WP-S-05-hsi-specification.md) | Approved | Part of CR-05 |
| E-08 | ASIL allocation and decomposition | [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md) | Approved | Part of CR-06 (system) |
| E-09 | System FFI and DFA | [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md), [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md) | Approved at system level | CR-06 (system) |
| E-10 | Configuration management | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) | Approved and in use | — |
| E-11 | Change management | [WP-P-02](../07-supporting/WP-P-02-change-management.md) | Approved and in use | — |
| E-12 | Requirements management and traceability | [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md), [`trace/`](../trace/README.md) | Approved; TSR records present in `trace/` | — |
| E-13 | Verification and review procedure | [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) | Approved | — |
| E-14 | Tool classification | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) | Classification done for the software toolchain (qualification may follow in Phase D) | — |
| E-15 | Reviewer availability | [WP-M-04](WP-M-04-organization-competence-safety-culture.md), [WP-M-06](WP-M-06-confirmation-measures-plan.md) | At least one named reviewer other than the author for I1 software reviews | — |

Missing upstream inputs are **not** to be filled in by the software lifecycle. If a TSR, ASIL or allocation is missing, the gap is recorded as an open action against the system-level owner. No SWSR is invented to cover it.

### 3.2 Readiness snapshot at `3ed97c8`

This is an inventory of what exists. It is **not** the Phase A gap assessment, and it rates nothing as adequate.

| Prerequisite | Present | Current status | Observation |
|---|---|---|---|
| Item definition, HARA, safety goals | Yes | Draft | 7 safety goals (SG-01 ASIL C, SG-02…SG-07 ASIL B) are proposals. CR-02 not held |
| FSC / FSRs | Yes | Draft | FSRs are not yet in `trace/` (WP-T-01 OI-2) |
| TSRs, TSC, system architecture | Yes | Draft | All TSRs `Proposed`; not in `trace/` |
| Timing / FTTI | Yes | Draft | Kinematic estimates only; nothing measured |
| HSI | Yes | Draft | — |
| ASIL decomposition, FFI, DFA (system) | Yes | Draft | — |
| Safety plan, CM, change, requirements management, review procedure | Yes | Draft | Single maintainer; I1 needs an external reviewer (T-09) |
| Tool classification | Yes | Draft | GAP-34: no tool qualified |
| Existing software architecture description | Yes ([WP-W-03](../05-software/WP-W-03-software-architecture.md)) | Draft | Back-filled from code |
| Existing software tests | Yes, upstream assets | Not reviewed as evidence | Safety tests, MISRA and mutation run in fork CI ([`safety.yaml`](../../.github/workflows/safety.yaml)); line coverage only (GAP-13); host builds, not target (GAP-13, GAP-41); no HIL (GAP-30) |
| Existing software safety analyses | Yes ([WP-W-04](../05-software/WP-W-04-software-safety-analysis.md)) | Draft | — |
| Machine-readable trace data | Partial | Draft | Hazards, hazardous events, goals, AoUs only (43 items). No FSR, TSR, SWSR or verification records |
| Living Safety Case | Yes ([`case/`](../case/README.md)) | Development | No claim has accepted evidence |

Conclusion of the snapshot: **no entry criterion is met.** Every prerequisite exists as a draft and none has been approved or confirmed. Part 6 stays deferred.

## 4. Lifecycle specification, Clauses 5–11

For each clause, the table gives the work products in two classes:

- **Principal**: work products the standard expects for the clause (check the exact list and the ASIL-dependent tables against the licensed copy);
- **Supporting**: engineering artifacts LionDriver uses to produce or support the principal work products. Not every supporting artifact is an individually required ISO 26262 work product.

Existing homes are given so nothing is duplicated. "Exists at baseline" says what is in the repository today. It never means that the activity is done.

### 4.1 Clause 5 — General topics for software development

**Objective (paraphrased):** a suitable, controlled development environment, a defined lifecycle, and appropriate languages, guidelines, methods and tools for the ASIL.

| Class | Artifact | Home | Exists at baseline |
|---|---|---|---|
| Principal | Documentation of the software development environment, including guidelines and methods | [WP-W-01](../05-software/WP-W-01-software-development-environment-guidelines.md) | Draft |
| Supporting | Software lifecycle definition and development procedures | WP-W-01 + this document §15 | Partial |
| Supporting | Language selection rationale (C for the safety MCU; Python, C++ for the QM host) | WP-W-01 §2 | Draft |
| Supporting | Coding guidelines (MISRA C:2012 for envelope C; Python and C++ host guidance) and design guidelines | WP-W-01 §5–6, §10–12 | Draft |
| Supporting | Deviation register | WP-W-01 §9 (`DEV-` IDs) | Draft; 6 global MISRA suppressions without records (GAP-13) |
| Supporting | Toolchain inventory, compiler and build configuration records | WP-W-01 §7; [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) | Draft |
| Supporting | Software dependency inventory (SBOM) | [WP-W-11 §5](../05-software/WP-W-11-cybersecurity-implementation-verification.md); submodule pins in [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) | Planned |
| Supporting | Static analysis configuration | `opendbc_repo/opendbc/safety/tests/misra/`, `panda/tests/misra/` | Upstream config, under fork CI |
| Supporting | Build reproducibility procedure and records | New record set (§10) | Not established |
| Supporting | Configuration and calibration data approach | [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md) | Draft |
| Supporting | Development environment verification records | New record set (§10) | Not established |
| Supporting | Tool confidence and qualification references | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) | Draft; nothing qualified (GAP-34) |
| Supporting | Engineering review records | PR reviews logged per [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md); `case/reviews/` | No software review records |

Phase A must inspect the actual toolchain (compiler versions and flags, the `ALLOW_DEBUG` test build in GAP-41, the mutable cppcheck branch in GAP-34) instead of assuming that upstream practice is enough for the allocated ASIL.

### 4.2 Clause 6 — Specification of software safety requirements

**Objective (paraphrased):** derive software safety requirements from the technical safety requirements and system design, refine the HSI, and verify that the requirements are consistent and complete.

| Class | Artifact | Home |
|---|---|---|
| Principal | Software safety requirements specification | [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) (document) + `trace/items/swsr.yaml` (records) |
| Principal | Refined hardware-software interface specification | [WP-S-05](../03-system/WP-S-05-hsi-specification.md) refined; software part in WP-W-02 §11 |
| Supporting | TSR-to-software allocation | `trace/items/tsr.yaml` `allocated_to` |
| Supporting | ASIL attribute and allocation rationale; timing, fault detection, fault reaction, degraded-operation and interface constraints | Attributes on each SWSR record |
| Supporting | Configuration applicability | `applies_to` attribute (§7) |
| Supporting | Verification method and acceptance criteria | Attributes on each SWSR record |
| Supporting | Requirements quality analysis | Checker output + review record |
| Supporting | Review and approval evidence | `case/reviews/` records linked to the SWSR baseline |

**SWSR record.** Extends the [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) attribute set. Proposed fields (final schema in Phase B):

| Field | Required | Notes |
|---|---|---|
| `id` | Yes | `SWSR-<nnn>[a]`; never reused |
| `title`, `text` | Yes | One requirement per record |
| `parents` | Yes | TSR IDs. A SWSR without an approved parent is `proposed` only |
| `rationale` | Yes | |
| `asil` | Yes | Inherited or decomposed; decomposition needs a [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md) reference |
| `allocated_to` | Yes | Architecture element ID(s) (§4.3) |
| `applies_to` | Yes | Configuration IDs or a platform scope (§7) |
| `category` | Yes | functional, timing, fault-detection, fault-reaction, degraded-mode, interface, data |
| `verification_method`, `acceptance_criteria` | Yes | |
| `status` | Yes | Per §2.2 |
| `version`, `baseline` | Yes | |
| `review_ref`, `approved_by`, `approved_date` | When approved | Must point to a review record |
| `proposed_by` | When tool-generated | `tool` or `ai`; blocks approval until a human review is recorded |

### 4.3 Clause 7 — Software architectural design

**Objective (paraphrased):** an architecture that meets the software safety requirements, supports safety analysis, and is verified against them.

| Class | Artifact | Home |
|---|---|---|
| Principal | Software architectural design specification | [WP-W-03](../05-software/WP-W-03-software-architecture.md) + `trace/items/arch.yaml` (element records, proposed) |
| Principal | Software safety analysis report | [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) |
| Principal (where applicable) | Dependent failures analysis report, software level | WP-W-04 §4, consistent with [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md) |
| Supporting | Component decomposition, interfaces, data-flow, control-flow, scheduling and execution models | WP-W-03 §3–5; diagrams as code |
| Supporting | Timing and resource analysis, memory allocation analysis | WP-W-03 §7 (estimates; **to be measured**) |
| Supporting | Safety mechanism design, fault-handling architecture | WP-W-03, [WP-W-05 §6](../05-software/WP-W-05-software-unit-design.md) |
| Supporting | Freedom-from-interference analysis | WP-W-03 §6, consistent with [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) |
| Supporting | Software FMEA, software FTA where useful | WP-W-04 §3; FTA links to [WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md) |
| Supporting | Design rationale; architectural verification and review records | WP-W-03 §8; `case/reviews/` |

The architecture describes the code as it is: the opendbc safety layer and panda firmware (E-03) and the host stack (E-01). An element is safety-related only through an allocated SWSR or an interference path found by the FFI analysis. Target-state changes (for example IWDG initialization, GAP-07) are recorded as change requests against approved SWSRs, never as current architecture. Every architecture change is assessed for its effect on upstream functionality and on all supported platforms that share the changed code (for example `opendbc/safety/lateral.h` is shared across brands).

### 4.4 Clause 8 — Software unit design and implementation

**Objective (paraphrased):** unit designs and code that implement the allocated requirements and follow the design and coding guidelines, in a form that can be verified.

| Class | Artifact | Home |
|---|---|---|
| Principal | Software unit design specification | [WP-W-05](../05-software/WP-W-05-software-unit-design.md) + `trace/items/units.yaml` (proposed) |
| Principal | Software unit implementation | Source at a pinned submodule commit (`opendbc_repo`, `panda`) |
| Supporting | Unit interfaces, algorithms, state machines (WP-W-05 §5), design constraints | WP-W-05 |
| Supporting | Coding-rule compliance records, static analysis findings, complexity analysis | CI artifacts bound to a build ID (§8.3) |
| Supporting | Generated code records | WP-W-01 §11 (capnp, acados and tinygrad outputs; QM unless allocated) |
| Supporting | Code review evidence, implementation trace tags | PR reviews; requirement tags in code per WP-P-06 |
| Supporting | Controlled software baselines | `case/baselines/`, release tags ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) |

**Inherited code.** Each reused unit gets a reuse assessment (§6). Wide deployment, test coverage and community use count as supporting information, never as design or verification evidence ([WP-M-01 T-06](WP-M-01-assurance-strategy.md#5-tailoring)).

### 4.5 Clause 9 — Software unit verification

**Objective (paraphrased):** show that units meet their design and requirements, contain no unintended functionality, and are verified with the methods and structural coverage the ASIL calls for.

| Class | Artifact | Home |
|---|---|---|
| Principal | Software verification specification (unit level) | [WP-W-06 §6](../05-software/WP-W-06-software-unit-verification.md) (`VS-UV-` cases) |
| Principal | Software verification report (unit level) | WP-W-06 §8 + result records (§8.3) |
| Supporting | Strategy; test specifications, cases, harnesses and scripts | WP-W-06 §3; `opendbc_repo/opendbc/safety/tests/` |
| Supporting | Requirements-based, boundary, robustness and fault-injection tests | `VS-UV-` cases linked to SWSRs |
| Supporting | Static verification results | MISRA and cppcheck outputs per build |
| Supporting | Structural coverage: statement, branch, MC/DC where the ASIL calls for it; coverage gap analysis | Coverage records per build (§8.3) |
| Supporting | Execution records, anomaly records, corrective actions | Result records; [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) |
| Supporting | Verification review and approval | `case/reviews/` |

Methods and coverage objectives are chosen from the ASIL-dependent tables of the licensed standard for the **approved** ASIL of each unit. Today only line coverage is measured, on host builds with `ALLOW_DEBUG` (GAP-13, GAP-41). No branch or MC/DC figure exists and none may be shown until one is measured. Passing unit tests does not show that the software is safe.

### 4.6 Clause 10 — Software integration and verification

**Objective (paraphrased):** integrate the software units in a defined sequence and show that the integrated software meets the architectural design, interfaces, timing and resource constraints, and that the safety mechanisms work.

| Class | Artifact | Home |
|---|---|---|
| Principal | Refined software verification specification (integration) | [WP-W-07 §5](../05-software/WP-W-07-software-integration-verification.md) (`VS-SWI-`) |
| Principal | Integrated embedded software | Firmware and host build identified by build ID and commit set |
| Principal | Refined software verification report (integration) | WP-W-07 §8 + result records |
| Supporting | Integration strategy, sequence, dependency records | WP-W-07 §2 |
| Supporting | Integration build manifests | New: manifest per build (commits of all submodules, toolchain versions, flags, configuration ID) |
| Supporting | Interface, inter-component, timing, resource and safety-mechanism tests | `VS-SWI-` cases |
| Supporting | Fault-handling verification | Links to [WP-V-05](../06-validation/WP-V-05-fault-injection.md) |
| Supporting | Regression, anomaly tracking, configuration-specific evidence, reviews | Result records; WP-P-03; `case/reviews/` |

Every integration result names the build manifest, the configuration ID, the test environment ID and the requirements covered. A result without these is not admitted as evidence.

### 4.7 Clause 11 — Testing of the embedded software

**Objective (paraphrased):** show that the embedded software, in its target environment, meets the software safety requirements.

| Class | Artifact | Home |
|---|---|---|
| Principal | Refined software verification specification (embedded) | [WP-W-08 §5](../05-software/WP-W-08-embedded-software-testing.md) (`VS-SWQ-`) |
| Principal | Refined software verification report (embedded) | WP-W-08 §7 + result records |
| Supporting | Test strategy, target-environment test plan | WP-W-08 §2–3 |
| Supporting | SWSR verification matrix | Generated from `trace/` (§8); WP-W-08 §6 becomes a generated view |
| Supporting | Functional, robustness, fault detection and reaction, boundary, timing and resource, configuration-specific and regression tests | `VS-SWQ-` cases |
| Supporting | Test environment configuration records | HIL bench record (D-04) |
| Supporting | Execution records, residual anomaly assessments, reviews | Result records; WP-P-03; `case/reviews/` |

Precondition: a LionDriver-controlled target environment (HIL bench, D-04; GAP-30). Clause 11 testing verifies the software against SWSRs. It is not item-level safety validation ([WP-V-01](../06-validation/WP-V-01-safety-validation.md), Part 4) and does not show that the vehicle is safe.

## 5. Interfaces to supporting processes and other parts

| Interface | Provides to Part 6 | Receives from Part 6 | Owning work product |
|---|---|---|---|
| Part 2 — safety management | Safety plan, tailoring, roles, independence, confirmation measures | Work product status, evidence for the safety case and FSA | [WP-M-02](WP-M-02-safety-plan.md), [WP-M-06](WP-M-06-confirmation-measures-plan.md), [WP-K-01](../10-safety-case/WP-K-01-safety-case.md) |
| Part 3 — concept | Safety goals, FSRs, AoUs | Feedback when software cannot meet an FSR | [WP-C-03](../02-concept/WP-C-03-hara.md), [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) |
| Part 4 — system | TSRs, system architecture, HSI, FTTI | Software verification results for system integration | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md)…[WP-S-05](../03-system/WP-S-05-hsi-specification.md), [WP-S-08](../03-system/WP-S-08-system-integration-test.md) |
| Part 8 §6 — requirements management | Attribute set, trace model | SWSR records | [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) |
| Part 8 §7 — configuration management | Baselines, safety-relevant file list | Build manifests | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) |
| Part 8 §8 — change management | Change requests, impact analysis | Affected software records | [WP-P-02](../07-supporting/WP-P-02-change-management.md), [WP-M-12](WP-M-12-impact-analysis.md) |
| Part 8 §9 — verification | Review procedure | Review records | [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) |
| Part 8 §10 — documentation | Document control | — | [WP-P-04](../07-supporting/WP-P-04-documentation-management.md) |
| Part 8 §11 — tool confidence | TCL and qualification | Tool list and use cases | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) |
| Part 8 §12 — software component qualification | Qualification method | Reuse assessments (§6) | [WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md) |
| Part 9 — ASIL decomposition, FFI, DFA, safety analyses | System-level analyses | Software-level analyses | [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md)…[WP-A-04](../08-analyses/WP-A-04-system-fta-fmea.md), [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) |
| Problem resolution | Anomaly process | Anomaly records | [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) |
| ISO/SAE 21434 | CSRs allocated to software | Security implementation and verification | [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) |
| ISO 21448, ISO/PAS 8800 | SOTIF and AI requirements, ML lifecycle | Software-side links | [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md), [WP-W-10](../05-software/WP-W-10-ml-engineering.md) |

Each authoritative record has one owner. Part 6 records refer to the records above. They do not copy them.

## 6. Existing software and reuse assessment

LionDriver's software is almost all inherited. The assessment method lives in [WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md), within the strategy of [WP-M-01 T-03, T-05, T-06](WP-M-01-assurance-strategy.md#5-tailoring) and [WP-M-12](WP-M-12-impact-analysis.md). This section fixes the record each assessment produces.

| Field | Content |
|---|---|
| Component, source, owner | Repository, path, upstream owner, fork |
| Version and baseline | Pinned commit; upstream tag if any |
| Intended function; safety relevance | Allocated SWSRs or interference paths; ASIL or QM |
| Existing development evidence | Requirements, design, reviews found (usually none) |
| Existing verification evidence | Tests, coverage type, static analysis, mutation; where it runs |
| Operational assumptions | Configuration, platform, environment assumed by upstream |
| Known defects and limitations | Upstream issues, GAP findings |
| Dependencies | Software, toolchain, configuration |
| Gaps | Requirements, architecture, verification |
| Strategy | Re-verify to ASIL (T-03), qualify at QM (T-05), argue non-interference, or replace |
| Additional engineering needed | Concrete actions, with owner |
| Review | Reviewer, independence, date, outcome |

Assessment candidates, from the safety-relevant file list ([`safety-relevant-paths.txt`](../07-supporting/safety-relevant-paths.txt)): the opendbc safety layer and Toyota mode, panda firmware paths the envelope relies on, the host processes in the actuation path, and QM libraries (msgq, capnp, rednose, tinygrad runtime). Upstream maturity, deployment history and test counts do not on their own satisfy any ISO 26262 objective.

## 7. Multi-vehicle configuration management

The Part 6 lifecycle runs once at platform level. Configuration-specific assurance is added on top of it, so the lifecycle is not repeated for every vehicle. The approach follows the configurable-software guidance of ISO 26262-6 Annex C and builds on [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md) and the configuration records in [`case/configurations/`](../case/configurations/).

### 7.1 Three tiers

| Tier | Record classification | Meaning |
|---|---|---|
| Upstream-compatible | `upstream-compatible` | Supported by the upstream code. No LionDriver evaluation. **No assurance claim** |
| LionDriver-evaluated | `liondriver-evaluated` | Analysed by LionDriver. Evidence in progress. Today only CFG-001 (2020 Corolla, TSS2), `in-progress` |
| Assurance-supported | `assurance-supported` | Has at least one claim with accepted evidence ([`case/README.md` §5](../case/README.md)). None today |

### 7.2 Records

| Record | Content | Home |
|---|---|---|
| Common platform component | Shared code (e.g. `safety.h`, `lateral.h`), with every configuration that uses it | `trace/items/arch.yaml` |
| Vehicle-specific interface | Brand safety mode, DBC, messages, limits | `trace/items/arch.yaml` + WP-W-09 |
| Hardware configuration | Device revision, harness | `case/configurations/` |
| Software variant | Build flags, safety mode, `ALLOW_DEBUG` state | Build manifest (§8.3) |
| Calibration variant | Car params, fingerprints, limits, model weights | WP-W-09 `DVR-` records |
| Feature configuration | e.g. openpilot longitudinal, Experimental Mode (D-08) | `case/configurations/` |
| Safety assumptions, constraints, known limitations | AoUs and limits per configuration | `trace/items/aou.yaml`; configuration record |
| Build identifiers | Firmware and host build IDs | Build manifest |
| Verification and evidence applicability | Which configurations a result covers | `applies_to` on every verification result and evidence record |

**Rule:** every safety claim and every evidence item names the configurations it covers. Evidence for shared code covers another configuration only after an applicability analysis for that configuration has been reviewed. Compatibility does not imply assurance.

## 8. Requirements and evidence traceability

### 8.1 Trace chain

| Link | From → to | ID forms |
|---|---|---|
| 1 | Technical safety requirement → software safety requirement | `TSR-` → `SWSR-` |
| 2 | SWSR → architecture element | `SWSR-` → `SWA-` (proposed prefix) |
| 3 | Architecture element → software unit | `SWA-` → `SWU-` (proposed prefix) |
| 4 | Unit / SWSR → verification case | → `VS-UV-`, `VS-SWI-`, `VS-SWQ-` |
| 5 | Verification case → verification result | → `VR-` (proposed), bound to a build manifest |
| 6 | Result → assurance evidence | → `case/evidence` record |
| 7 | Evidence → safety case claim | → `case/claims` record |

Further links: hazards and safety goals (`H-`, `SG-`), FSRs, safety mechanisms, anomalies (WP-P-03), change requests (WP-P-02), baselines, reviews, and cross-discipline requirements (`CSR-`, `SOTIF-`/`FM-`, `AIR-`). New prefixes must be added to the checker's ID pattern and to [`assurance/README.md`](../README.md) in Phase B.

### 8.2 Engine capabilities

Builds on [`trace/tools/check_trace.py`](../trace/tools/check_trace.py) (checks K1–K3, K12, R1–R4, X1–X2 exist) and the case validator.

| Capability | Basis | State |
|---|---|---|
| Missing-link and broken-reference detection | K3 | Exists for current kinds; extend to new kinds |
| Orphan detection (SWSR without TSR, unit without SWSR) | New | Planned |
| Unverified requirement detection | New | Planned |
| Stale evidence (result older than the last change to its subject) | New, uses git history of linked paths | Planned |
| Change impact analysis | Extends `tools/sync/sync_report.py` and [WP-M-12](WP-M-12-impact-analysis.md) | Planned |
| Configuration applicability analysis | `applies_to` (§7) | Planned |
| Baseline comparison | `case/baselines/` + git | Planned |
| Review status reporting | `case/reviews/` | Partial (case records only) |

Trace links are explicit fields in reviewed records. An AI or tool may propose a link (`proposed_by`). The link counts only when a human review accepts it. Links are never inferred at report time.

### 8.3 Evidence binding

A verification result record carries at least: result ID, verification case ID, requirement IDs, build manifest ID (all submodule commits, toolchain and flags), configuration ID, test environment ID, tool versions, execution date, outcome, raw artifact location, anomaly references, reviewer and review state. Coverage figures carry the tool, the metric (statement, branch, MC/DC) and the exact scope measured.

## 9. Living Safety Case integration

Part 6 evidence enters the safety case through the existing records in [`case/`](../case/README.md). The case already enforces that only a recorded human review accepts anything.

The integration exposes, per claim: the supporting arguments, linked evidence with version and source baseline, applicable configurations, verification and review status, open issues and defeaters, change impacts, and approval history.

When code, requirements, tests or configurations change:

1. affected records are found through explicit links (§8), never through text search or AI inference;
2. linked evidence is flagged stale and drops to `partial` until re-run or re-justified;
3. a review obligation (an action record) is created for each affected claim;
4. the previous approved baseline is kept unchanged (`superseded`, not edited);
5. a claim's conclusion changes only through a new review record by an authorized reviewer.

Automated workflows never accept claims and never display completion or coverage values that were not measured.

## 10. Repository layout

The structure proposed in the source specification is mapped onto the existing tree. No parallel `assurance/software/` hierarchy is created.

| Proposed location | Existing or planned home | Decision |
|---|---|---|
| `management/software-safety-plan/` | [WP-M-02](WP-M-02-safety-plan.md) + this document | Reuse; no new folder |
| `software/05-development-environment/` … `11-embedded-software-testing/` | [`05-software/`](../05-software/) WP-W-01, -02, -03/-04, -05, -06, -07, -08 | Reuse. Clause-specific records go in `trace/items/` (requirements, architecture, units) and in a results store (below) |
| `software/configuration-profiles/` | [`case/configurations/`](../case/configurations/) + WP-W-09 | Reuse |
| `analyses/software-fmea/`, `software-fta/` | [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md); system level in [`08-analyses/`](../08-analyses/) | Reuse; structured worksheets may be added under `05-software/analyses/` in Phase C if the Markdown tables become unmanageable |
| `analyses/dependent-failures/`, `freedom-from-interference/` | [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md), [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md), WP-W-04 §4, WP-W-03 §6 | Reuse |
| `traceability/` | [`trace/`](../trace/README.md) | Reuse; add item kinds |
| `evidence/` | [`case/evidence/`](../case/evidence/) for evidence records; raw results as CI artifacts or a results folder decided in Phase B | Reuse + decide |
| `reviews/` | [`case/reviews/`](../case/reviews/) | Reuse |
| `baselines/` | [`case/baselines/`](../case/baselines/) + git tags ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) | Reuse |
| `reports/` | Generated outputs only (dashboard SVGs under `docs/assets/liondriver/assurance/`) | Reuse; generated files are never authoritative |
| `templates/` | New `assurance/templates/` in Phase B | Create when needed |

Sensitive vulnerability information is not published automatically; it follows [`SECURITY.md`](../../SECURITY.md) and [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md).

## 11. Work product register extension

[WP-M-00](WP-M-00-work-product-register.md) remains the master register. Phase B adds a machine-readable Part 6 register (proposed `assurance/trace/items/register-part6.yaml`, or a `case/` kind, decided in Phase B) generated into WP-M-00 §3.5 so the two cannot drift.

Fields per record: work product ID, name, ISO 26262 clause, governing process, owner, ASIL applicability, component, configuration, source requirements, required inputs, expected outputs, verification obligations, review authority, status (§2.2), version, baseline, evidence references, open findings, approval record, and **classification**:

| Classification | Meaning |
|---|---|
| `required` | Expected by the standard for the applicable ASIL, per the licensed text |
| `supporting` | Engineering artifact supporting a required work product |
| `tailored` | Optional or tailored, with a reference to the tailoring rationale |
| `not-applicable` | With rationale |

The register does not claim that every supporting artifact in §4 is an individually required ISO 26262 work product.

## 12. Automation and CI

Extends [`.github/workflows/assurance.yaml`](../../.github/workflows/assurance.yaml). The jobs stay read-only.

| Check | Basis |
|---|---|
| Schema validation; missing required fields; invalid identifiers; duplicates | Extend K1, K2 and `case/tools/validate.py` |
| Broken trace links | K3 extended |
| Missing verification evidence for approved SWSRs | New |
| Stale evidence references | New (§8.2) |
| Unreviewed changes to approved records | New; compares against the last review record's revision |
| Inconsistent configuration applicability | New (§7) |
| Missing baseline references | Extend `validate.py` |
| Invalid lifecycle transitions | New (§2.2) |
| Incomplete release evidence | New; input to [WP-P-10](../07-supporting/WP-P-10-release-management.md) |

Each check produces a machine-readable result (JSON) and a readable summary. The output separates **structural completeness** (records and links present) from **demonstrated safety** (accepted reviews of evidence). A green CI run is reported as "records consistent" and never as ISO 26262 compliance.

## 13. Software engineering dashboard

Extends [`case/tools/generate_dashboard.py`](../case/tools/generate_dashboard.py) and keeps its rules: values come from records, generated files are checked for freshness in CI, and no value is typed by hand.

- **Design:** deep navy and charcoal surfaces, metallic gold for headings and accents, electric blue for interactive and link elements, white and neutral text, restrained engineering visuals. Follow the existing LionDriver assets in `docs/assets/liondriver/`.
- **Views:** Clause 5–11 lifecycle overview; work product register and maturity; requirements traceability; architecture relationships; verification results; coverage where measured; open findings; review obligations; configuration applicability; baseline history; links to the Living Safety Case.
- **Drill-down:** lifecycle stage → work products → records → evidence → review.
- **Missing data:** show `Not established`, `Not assessed` or `No evidence recorded`. Never show an estimated percentage.

## 14. Acceptance criteria for the framework

The implemented framework is ready for engineering review when:

1. all applicable Part 6 activities are in the register (§11);
2. clause-specific templates and schemas exist;
3. SWSRs have controlled, checked trace links;
4. architecture elements link to requirements and units;
5. verification evidence links to exact build manifests;
6. configuration applicability is explicit on claims, evidence and results;
7. change impact analysis lists affected records;
8. human review and approval controls are enforced by tooling;
9. CI detects structural and trace inconsistencies;
10. the Living Safety Case can reference approved evidence;
11. upstream functionality and licence obligations ([`LICENSE`](../../LICENSE)) are kept;
12. no tool output makes an unsupported safety or compliance claim.

Meeting these criteria shows that the **framework** exists. It does not show ISO 26262-6 compliance. Compliance depends on doing the lifecycle activities, producing the evidence, and having it assessed (CR-06, CR-09, CR-10, FSA).

## 15. Implementation phases

| Phase | Content | Entry condition | Maps to |
|---|---|---|---|
| A — Readiness and gap assessment | Inspect the repository, prerequisites, architecture, toolchain and verification evidence at the entry baseline; produce the Part 6 gap assessment and the implementation plan | D-09 authorizes Phase A; §3.1 E-01…E-05 at least `In review` | Late P2 / G2 |
| B — Work product infrastructure | Register, schemas, templates, status model, baselines, trace kinds, CI checks | Phase A report approved; entry baseline approved (all of §3.1, or justified exceptions) | P3 / G3 |
| C — Requirements and architecture | Clauses 6 and 7 with approved system inputs | Phase B acceptance criteria 1–3 met | P3 / G3 |
| D — Unit design and verification | Clauses 8 and 9 | SWSRs and architecture approved for the units in scope | P3 / G3 |
| E — Integration and embedded testing | Clauses 10 and 11 | HIL bench available (D-04); units verified | P4 / G4 |
| F — Living assurance integration | Status, trace, results, change impacts and approved evidence wired into the safety case | Runs alongside C–E; completed before G4 | P4–P5 |

Phases advance on approved outputs, never because templates or scripts exist. Phase dependencies on Parts 2, 3 and 4 are carried in [WP-M-01 §7](WP-M-01-assurance-strategy.md#7-phases-gates-and-sequence) and [WP-M-03 §3](WP-M-03-project-plan.md#3-work-breakdown-structure).

## 16. Rules until activation

Until D-09 is recorded:

1. This document is kept and maintained as the Part 6 implementation specification.
2. No new software safety requirements, architecture records, analyses, verification results or approvals are created to look like Part 6 progress. Corrections to the existing WP-W drafts are allowed and stay `Draft`.
3. Application code is not restructured for Part 6.
4. Upstream-tracking branches and submodule pins are not changed for Part 6 (sync follows [WP-M-11 §5](WP-M-11-upstream-and-supplier-management.md)).
5. Work on the prerequisites (§3.1) proceeds normally and is what brings activation closer.

## 17. Open items

| ID | Item | Owner |
|---|---|---|
| OI-1 | Record decision D-09 (authorize Phase A) when E-01…E-05 reach `In review` | Project maintainer |
| OI-2 | Check every clause reference and the principal work product lists in §4 against the licensed ISO 26262-6:2018 | Reviewer |
| OI-3 | Decide whether to adopt the §2.2 status extension (Planned, Verified, Superseded) project-wide or for Part 6 records only | Project maintainer |
| OI-4 | Decide the store for raw verification results (CI artifacts with retention vs a committed results folder) | Project maintainer |
| OI-5 | Independent (I1) review of this specification | External reviewer |
