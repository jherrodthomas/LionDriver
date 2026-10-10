# WP-M-02 Functional Safety Plan

| Field | Value |
|---|---|
| Work product | WP-M-02 Functional safety plan |
| Standard reference | ISO 26262-2:2018 §6 (project-dependent safety management: roles, planning, tailoring, safety case, confirmation measures); ISO 26262-2 §5 (anomaly handling, interfaces to overall safety management); ISO 26262-8 §5–§12 (supporting processes, by reference); ASPICE 4.0 MAN.3 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All. Planned to ASIL D until the HARA ([WP-C-03](../02-concept/WP-C-03-hara.md)) is approved |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review TBD (external assessor, I3 planned, see [WP-M-06](WP-M-06-confirmation-measures-plan.md)) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This plan sets out how functional safety is managed for the LionDriver reference configuration defined in [WP-M-01 §3.1](WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to): 2020 Toyota Corolla LE (US, ICE, TSS 2.0, `TOYOTA_COROLLA_TSS2`), one identified comma device revision with panda safety MCU, and a tagged LionDriver release.

It implements the [assurance strategy (WP-M-01)](WP-M-01-assurance-strategy.md) for ISO 26262. It does not repeat the strategy. The companion plans cover the other disciplines:

| Discipline | Plan |
|---|---|
| SOTIF | [WP-M-08](WP-M-08-sotif-plan.md) |
| Cybersecurity | [WP-M-09](WP-M-09-cybersecurity-plan.md) |
| AI safety | [WP-M-10](WP-M-10-ai-safety-plan.md) |
| Project scope, effort, schedule | [WP-M-03](WP-M-03-project-plan.md) |

This plan is a living document. It is updated at every gate review (§8) and whenever an approved change alters scope, ASIL, roles or tailoring.

## 2. Safety objectives

| # | Objective | Measured by |
|---|---|---|
| SO-1 | Identify the hazards of the item caused by E/E malfunctions and derive safety goals with ASILs | Approved HARA ([WP-C-03](../02-concept/WP-C-03-hara.md)) with I3 confirmation review |
| SO-2 | Show that the safety envelope (opendbc safety mode on the panda MCU, plus the firmware paths it relies on) meets the safety goals regardless of what the QM driving stack commands | FSC, TSC, FFI and DFA analyses; verification evidence for the envelope (WP-M-01 §4) |
| SO-3 | Back-fill requirements, architecture and unit design for the inherited envelope code and verify them to the HARA ASIL | WP-W-02…WP-W-08 approved; traceability complete in [`trace/`](../trace/README.md) |
| SO-4 | Close the high-severity envelope gaps from the gap assessment (GAP-01…GAP-09) or argue their residual risk | Change requests closed; safety case argument |
| SO-5 | Keep every safety-relevant change under configuration and change control, with impact analysis | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md), [WP-P-02](../07-supporting/WP-P-02-change-management.md) records |
| SO-6 | Provide independent confirmation that the work and its results are adequate | Confirmation reviews, audit and assessment per [WP-M-06](WP-M-06-confirmation-measures-plan.md) |
| SO-7 | Make no claim that the evidence does not support | Safety case ([WP-K-01](../10-safety-case/WP-K-01-safety-case.md)) reviewed against this plan at each gate |

## 3. Roles and responsibilities

### 3.1 Role assignments

The project has one maintainer today. One person holding several roles is allowed for planning and authoring. It is not allowed where independence is required (verification review of own work at I1 or higher, confirmation measures, QA audits). Roles marked TBD must be filled before the gate shown.

| Role | Responsibilities | Assigned to | Needed by |
|---|---|---|---|
| Safety manager | Owns this plan; plans and coordinates safety activities; tracks progress; approves safety work products (except own-authored ones that need independent approval); maintains the safety case; initiates confirmation measures; decides on safety anomaly escalation | Jherrod Thomas (acting) | G0 |
| Project maintainer | Overall project responsibility; resource and scope decisions; strategic decisions D-01…D-12; release decision (with safety manager) | Jherrod Thomas | G0 |
| Configuration and change manager | CM plan, baselines, submodule control, change board | Jherrod Thomas (acting) | G0 |
| Cybersecurity manager | Owns [WP-M-09](WP-M-09-cybersecurity-plan.md); TARA; interface to safety on safety-relevant threats | Jherrod Thomas (acting); permanent holder TBD | G1 |
| SOTIF lead | Owns [WP-M-08](WP-M-08-sotif-plan.md); validation targets; scenario evaluation | TBD | G1 |
| AI/ML safety lead | Owns [WP-M-10](WP-M-10-ai-safety-plan.md); model pinning and model lifecycle evidence | TBD | G1 |
| Envelope software engineer(s) | Requirements back-fill, design, implementation and unit verification of opendbc safety and panda firmware changes | Jherrod Thomas; additional contributors TBD | G2 |
| Hardware safety engineer | Hardware FMEDA, metrics, component qualification (WP-H-*) | TBD (likely external) | G2 |
| Verification reviewer(s) | Verification reviews of work products and code (PR reviews) at the independence level set in [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) | TBD (at least one person other than the author) | G0 |
| Quality assurance | Process and work product audits per [WP-M-05](WP-M-05-quality-assurance-plan.md) | TBD (independent of the author) | G0 |
| HIL bench owner | Builds and maintains the HIL bench (D-04) | TBD | G3 |
| Test / safety driver(s) | Vehicle tests under [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) | TBD (trained per WP-M-04) | G1 (before any LionDriver public-road test) |
| External functional safety assessor | Confirmation reviews at I3, functional safety audit, functional safety assessment | TBD (D-06) | G1 |
| External cybersecurity assessor | Cybersecurity assessment ([WP-K-05](../10-safety-case/WP-K-05-cybersecurity-assessment.md)) | TBD | G5 (interim earlier, see WP-M-06) |

Competence requirements and evidence for each role are in [WP-M-04](WP-M-04-organization-competence-safety-culture.md).

### 3.2 RACI per activity

R = responsible, A = accountable, C = consulted, I = informed. SM = safety manager, PM = project maintainer, CSM = cybersecurity manager, SL = SOTIF lead, ML = AI/ML safety lead, ENG = envelope engineer, HW = hardware safety engineer, VR = verification reviewer, QA = quality assurance, EA = external FuSa assessor.

| Activity | SM | PM | CSM | SL | ML | ENG | HW | VR | QA | EA |
|---|---|---|---|---|---|---|---|---|---|---|
| Safety plan and updates | A/R | C | C | C | C | I | I | R (review) | C | C (CR) |
| Impact analysis (WP-M-12) | A | R | C | C | C | C | C | R | I | R (CR) |
| Item definition, HARA | A/R | C | C | C | I | C | I | R | I | R (CR) |
| FSC / TSC | A | I | C | C | I | R | C | R | I | R (CR) |
| Safety analyses (FFI, DFA, FTA/FMEA) | A | I | C | C | C | R | R | R | I | R (CR) |
| Envelope SW requirements, design, code, unit verification | A | I | C | I | I | R | I | R | I | I |
| HW FMEDA, metrics, qualification | A | C | I | I | I | C | R | R | I | R (CR) |
| Integration, HIL, fault injection | A | C | C | C | I | R | C | R | I | I |
| Safety validation (vehicle) | A | C | I | R | C | C | I | R | I | I |
| CM, change control | C | A | C | I | I | R | I | I | C | I |
| QA audits | I | A | I | I | I | I | I | I | R | I |
| Safety case | A/R | C | C | R | R | C | C | R | I | R (CR) |
| Functional safety audit and assessment | C | A | I | I | I | I | I | I | C | R |
| Release decision | R | A | R | C | C | I | I | I | C | C |

"CR" means the assessor performs the confirmation review. The assessor is never responsible for producing a work product.

## 4. Lifecycle activities per phase

Phases and gates are defined in [WP-M-01 §7](WP-M-01-assurance-strategy.md#7-phases-gates-and-sequence) and [WP-M-00 §2](WP-M-00-work-product-register.md#2-gates). This table assigns the safety activities in each phase. Work product IDs refer to the register.

| Phase | Safety activities | Responsible | Key outputs | Gate entry criteria |
|---|---|---|---|---|
| P0 Governance | Approve plans; assign roles; take configuration control of opendbc and panda (D-01); freeze upstream sync (D-02); make fork CI meaningful (D-03); set up review rules, CODEOWNERS, branch protection; impact analysis of the inherited baseline; engage an external assessor (D-06) | SM, PM | WP-M-00…M-13, WP-P-01…P-06 | — |
| P1 Concept | Item definition and AoUs on Toyota ECUs; ODD; HARA and safety goals; driver/HMI misuse analysis; FSC with FSR allocation; vehicle test procedures before any LionDriver-specific road test; initial safety case argument | SM (HARA, FSC), SL (SOTIF inputs), CSM (TARA link) | WP-C-01…C-11, WP-V-07, WP-K-01 v1 | G0 passed |
| P2 System design | Back-fill TSRs from envelope code; TSC and architecture; FTTI and detection-time budget (GAP-06); HSI; FFI and DFA, including the SoC-configures-panda weakness (GAP-09); system FTA/FMEA; ASIL decomposition if needed | ENG, SM, HW | WP-S-01…S-07, WP-A-01…A-04, WP-V-02 | G1 passed incl. HARA confirmation review |
| P3 HW/SW development | HW safety requirements, FMEDA, metrics and PMHF; component qualification of the comma device and STM32H7; SW safety requirements, architecture, safety analysis, unit design; envelope hardening (IWDG, fault → safe state, mode lock, E2E, driver-torque and EPS-status monitoring); unit verification incl. structural coverage beyond line coverage (GAP-13); tool and SW component qualification | ENG, HW, SM | WP-H-01…H-05, H-07, WP-W-01…W-06, W-09…W-11, WP-P-07…P-09 | G2 passed |
| P4 Integration and verification | Build the HIL bench (D-04); SW and HW integration tests on the Cortex-M7 target; system integration; fault injection campaign; fork-owned process-replay references | ENG, HIL bench owner | WP-S-08, S-09, H-06, W-07, W-08, WP-V-03, V-05 | G3 passed; HIL bench available |
| P5 Validation and release | Safety validation in the vehicle under WP-V-07; SOTIF residual risk acceptance (with SL); safety case completion; functional safety assessment; release record | SM, SL, EA | WP-V-01, V-04, V-06, WP-K-01…K-06, WP-O-01…O-03 | G4 passed |
| P6 Operation | Field monitoring, safety anomaly handling after release, controlled updates, incident response | SM, CSM | WP-O-04, O-05, WP-P-03 | G5 passed; release record signed |

**Hold point.** No LionDriver public-road operation beyond upstream behaviour until G1 is passed and WP-V-07 is approved (gap assessment §9 action 10; WP-M-01 §9).

## 5. Work products

The list of work products, their source clauses, gates and status is the [work product register (WP-M-00)](WP-M-00-work-product-register.md). This plan does not duplicate it. Rules:

- Every work product in WP-M-00 is either produced, or marked `N/A (tailored)` with a reference to WP-M-01 §5.
- The status in WP-M-00 is the authoritative status. A work product moves to `Approved` only after its verification review per [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) and, where WP-M-06 requires it, its confirmation review.
- A work product's `Baseline` field names the commit its content refers to. If the referenced code changes, the change process ([WP-P-02](../07-supporting/WP-P-02-change-management.md)) decides whether the work product must be updated.

## 6. Tailoring

Tailoring decisions T-01…T-13 and their rationale are in [WP-M-01 §5](WP-M-01-assurance-strategy.md#5-tailoring). The safety-relevant consequences for this plan are:

| Tailoring | Effect on this plan |
|---|---|
| T-01 Modification of an existing item | Impact analysis (WP-M-12) is a P0 activity; full concept phase follows |
| T-03 Envelope re-verified to HARA ASIL | ASIL activities in P2–P4 apply to the envelope code only; the SoC stack is QM plus SOTIF |
| T-04 COTS hardware | Hardware activities are qualification plus LionDriver-performed analyses, not HW development |
| T-06 No proven-in-use claim | WP-P-09 is supporting evidence only |
| T-08 comma.ai as upstream supplier without DIA | Supplier-side activities fall to LionDriver (WP-M-11) |
| T-09 Independence | Confirmation measures at I2/I3 need an external party (WP-M-06) |

Each tailoring decision is subject to confirmation review (WP-M-06).

## 7. Supporting processes

| Process | Work product |
|---|---|
| Configuration management (incl. safety-relevant file list, submodules, baselines) | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) |
| Change management and impact analysis | [WP-P-02](../07-supporting/WP-P-02-change-management.md) |
| Problem resolution and safety anomaly handling | [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) |
| Documentation management | [WP-P-04](../07-supporting/WP-P-04-documentation-management.md) |
| Verification and review | [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) |
| Requirements management and traceability | [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) |
| Tool classification and qualification | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) |
| Software component qualification | [WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md) |
| Proven-in-use evaluation (supporting only) | [WP-P-09](../07-supporting/WP-P-09-proven-in-use.md) |
| Release management | [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| Quality assurance | [WP-M-05](WP-M-05-quality-assurance-plan.md) |
| Project risk management | [WP-M-07](WP-M-07-risk-management.md) |

## 8. Confirmation measures

Confirmation reviews, the functional safety audit and the functional safety assessment, including their independence levels, timing and records, are planned in [WP-M-06](WP-M-06-confirmation-measures-plan.md). Summary for gate planning:

| Gate | Confirmation measure (summary) |
|---|---|
| G0 | Confirmation review of this plan, the impact analysis and the tailoring rationale |
| G1 | Confirmation review of the HARA (I3) and the FSC; interim functional safety assessment |
| G2 | Confirmation review of the TSC and safety analyses; interim assessment; first functional safety audit |
| G3–G4 | Confirmation reviews of HW/SW analyses, tool qualification, component qualification; audit |
| G5 | Confirmation review of the safety case; final functional safety assessment |

## 9. Safety anomaly handling

A safety anomaly is any observation that may indicate a safety goal violation, an error in a safety work product, or a deviation from this plan. Sources include CI failures in safety tests, review findings, test and HIL results, vehicle-test events, upstream security or safety fixes, user reports and field data.

| Step | Rule |
|---|---|
| Report | Anyone can report. Use the GitHub issue label `safety-anomaly` (or a private channel for security-sensitive reports, per [WP-M-09](WP-M-09-cybersecurity-plan.md)). No-blame reporting applies ([WP-M-04](WP-M-04-organization-competence-safety-culture.md)) |
| Triage | Safety manager triages within 5 working days (target; not yet demonstrated). Classifies as: potential safety goal violation / work product error / process deviation / not safety-relevant |
| Immediate action | A potential safety goal violation stops vehicle testing on the affected configuration until the safety manager releases it. Any test driver may stop testing at any time |
| Resolution | Through [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md), with impact analysis through [WP-P-02](../07-supporting/WP-P-02-change-management.md) |
| Closure | Closure needs verification evidence and, for safety goal violations, review by someone other than the person who fixed it |
| Gate rule | No gate passes with an open anomaly classified as potential safety goal violation unless the safety manager records an accepted rationale and the assessor is informed |

## 10. Progress tracking and gate reviews

- Each gate G0…G6 has a GitHub milestone. Each work product and each gap action has an issue linked to its milestone ([WP-M-03 §8](WP-M-03-project-plan.md)).
- The safety manager reviews progress against this plan at least monthly and records the result in the milestone tracking issue.
- A gate review is held at the end of each phase. Inputs: WP-M-00 status, open anomalies, open risks (WP-M-07), confirmation measure results (WP-M-06), QA findings (WP-M-05), open items of the phase's work products.
- Gate outcome: `Pass`, `Pass with conditions` (conditions tracked as issues with owners and due gate), or `Fail`. The record is stored under `10-safety-case/gates/` (folder to be created).
- A gate cannot pass if a confirmation review that WP-M-06 assigns to it has not been performed, unless the safety manager and assessor agree a documented deferral.

## 11. Safety case planning

The safety case ([WP-K-01](../10-safety-case/WP-K-01-safety-case.md)) is built incrementally, following the claim structure G0–G5 in [WP-M-01 §3.2](WP-M-01-assurance-strategy.md#32-top-level-claim).

| Gate | Safety case content |
|---|---|
| G1 | Argument structure (GSN) for G0 and G1–G5; safety goals; evidence slots linked to planned work products; explicit assumptions and AoUs |
| G2 | Envelope argument (FFI, DFA, TSC) with evidence for the architecture |
| G3–G4 | Verification and qualification evidence linked; residual gaps recorded as counter-evidence or assumptions |
| G5 | Complete argument incl. SOTIF ([WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md)) and cybersecurity ([WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md)) links; input to the FSA |

Rules: every claim points to evidence that exists in the repository at a named baseline; missing evidence is shown as missing; known weaknesses (for example single-channel hardware, unverifiable OEM ECU behaviour) are stated in the argument, not omitted.

## 12. Reuse of upstream openpilot

LionDriver inherits all of its code from upstream openpilot (gap assessment §1). Rules:

| Rule | Detail |
|---|---|
| U-1 No inherited safety credit | Upstream claims (`docs/SAFETY.md` mentions HARA, FMEA, HIL tests) are not used as evidence. Those artefacts are not in the repository |
| U-2 Configuration control first | Safety-relevant upstream code is used only from LionDriver-controlled forks pinned by commit (D-01) |
| U-3 Deliberate sync | Upstream changes enter only through a sync change request with impact analysis against the safety-relevant file list (D-02, WP-P-02). Upstream safety and security fixes are monitored and assessed as anomalies (§9) |
| U-4 Envelope code | Upstream code in the ASIL path is re-verified under T-03; it is treated as LionDriver-owned once forked |
| U-5 QM code | Upstream QM code is qualified per ISO 26262-8 §12 at QM or argued as non-interfering (T-05, [WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md)) |
| U-6 Upstream tests | Upstream tests are reused as verification assets after review against LionDriver requirements; their pass/fail results are evidence only when run in LionDriver-controlled CI at a recorded baseline |
| U-7 Fork policy | The comma.ai fork policy in `docs/SAFETY.md` is an organizational constraint ([WP-M-04 §2.3](WP-M-04-organization-competence-safety-culture.md)) |
| U-8 Models | Model weights are pinned per release; any model change is SOTIF-relevant (D-05, [WP-M-10](WP-M-10-ai-safety-plan.md)) |

Upstream management and the absence of a DIA are handled in [WP-M-11](WP-M-11-upstream-and-supplier-management.md).

## 13. Open items

| ID | Open item | Owner | Due |
|---|---|---|---|
| OI-1 | Fill TBD roles in §3.1, at minimum one verification reviewer and a QA person independent of the author | PM | G0 |
| OI-2 | The safety manager and the project maintainer are the same person, who also authors most work products. Define who approves work products the safety manager authored (proposal: approval after external confirmation review for I3 items; second reviewer for others) | PM | G0 |
| OI-3 | Engage an external functional safety assessor (D-06) and agree scope and schedule | PM | G0 |
| OI-4 | Confirm the anomaly triage target (5 working days) is achievable with current staffing | SM | G0 |
| OI-5 | Create the `10-safety-case/gates/` and `10-safety-case/confirmation/` folders and the gate record template | SM | G0 |
| OI-6 | Revisit the ASIL D planning assumption once the HARA is approved; adjust independence and method selection | SM | G1 |
