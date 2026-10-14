# WP-M-04 Organization-Specific Rules, Safety Culture and Competence Management

| Field | Value |
|---|---|
| Work product | WP-M-04 Organization-specific rules, safety culture, competence management |
| Standard reference | ISO 26262-2:2018 §5 (overall safety management: rules and processes, safety culture, competence management, QMS link); ISO/SAE 21434:2021 §5 (organizational cybersecurity management, cybersecurity culture, competence); ISO 21448:2022 §4 (competence for SOTIF activities); ISO/PAS 8800:2024 (AI safety management, competence) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (organization level; FuSa, SOTIF, CS, AI) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer |
| Baseline | `8b8c6ae` |

## 1. Purpose and organization

LionDriver is an open-source project with one maintainer, Jherrod Thomas, who is also acting safety manager. Contributors take part through GitHub pull requests and issues. There is no legal entity, employment relationship or contract with contributors recorded in the repository.

This document defines the organization-level rules that apply to every project-level plan ([WP-M-02](WP-M-02-safety-plan.md), [WP-M-08](WP-M-08-sotif-plan.md), [WP-M-09](WP-M-09-cybersecurity-plan.md), [WP-M-10](WP-M-10-ai-safety-plan.md)): how decisions are made, what the safety culture requires, what competence each role needs, and how it is evidenced.

## 2. Organization-specific rules

### 2.1 Governance

| Rule | Content |
|---|---|
| OR-1 Authority | The project maintainer has final authority over scope and resources. The safety manager has authority to stop any release, merge or vehicle test on safety grounds. While one person holds both roles, a stop decision on safety grounds cannot be overridden for schedule reasons |
| OR-2 Safety-relevant code | Changes to files on the safety-relevant file list ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)) are merged only through a reviewed pull request with a safety-impact statement ([WP-P-02](../07-supporting/WP-P-02-change-management.md)) |
| OR-3 Work products | Work products live in `assurance/` as Markdown, change through pull requests, and follow the conventions in [`assurance/README.md`](../README.md) (D-07) |
| OR-4 Claims | Nobody publishes a safety, SOTIF or cybersecurity claim about LionDriver that the safety case ([WP-K-01](../10-safety-case/WP-K-01-safety-case.md)) does not support. Marketing language is not used in work products or release notes |
| OR-5 Vehicle testing | Vehicle tests follow [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md). No LionDriver public-road operation beyond upstream behaviour until G1 is passed and WP-V-07 is approved |
| OR-6 Disclosure | Security vulnerabilities are handled privately until fixed, per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md). Safety anomalies are tracked openly unless disclosure would create a security risk |
| OR-7 Records | Evidence of reviews, audits, competence and decisions is kept in the repository (or linked from it) for the life of the release plus the retention period in [WP-P-04](../07-supporting/WP-P-04-documentation-management.md) |

### 2.2 Interaction with the processes

Organization-level processes and their project-level implementation:

| Organization-level need (26262-2 §5, 21434 §5) | Implemented by |
|---|---|
| Rules and processes for functional safety and cybersecurity | This document; WP-M-02; WP-M-09 |
| Quality management | [WP-M-05](WP-M-05-quality-assurance-plan.md) |
| Safety anomaly / problem resolution | [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md); WP-M-02 §9 |
| Communication between safety, SOTIF and cybersecurity | §6 below; WP-M-01 §6 |
| Tool management | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) |
| Information security of project assets (keys, credentials) | [WP-M-09](WP-M-09-cybersecurity-plan.md); [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) |

### 2.3 Upstream fork policy as an organizational constraint

The comma.ai fork policy in `docs/SAFETY.md` ("Forks of openpilot") applies to LionDriver because it is a fork that will modify `opendbc/safety/` (envelope hardening, WP-M-01 §4.2). The policy sets out the following. These are treated as constraints, not as safety requirements.

| Upstream policy element | Consequence for LionDriver |
|---|---|
| Do not disable or weaken driver monitoring | Consistent with LionDriver's own position (driver monitoring is safety-relevant, WP-M-01 §4.2.4). Any change to DM requires SOTIF impact analysis |
| Do not disable or weaken excessive-actuation checks | Same treatment as DM |
| A fork that modifies `opendbc/safety/` cannot use the openpilot trademark | LionDriver does not use the openpilot trademark in its name, release artefacts or user information. Attribution to upstream as the source of the code is given as a factual statement only |
| Such a fork must keep the full safety test suite and all tests must pass, including new coverage for the fork's changes | LionDriver keeps the upstream safety test suite and extends it. Deleting or weakening an upstream safety test needs a recorded rationale and safety manager approval. This matches the CI quality gates in WP-M-05 |
| Non-compliance can get the fork and its users banned from comma.ai servers | Dependency on comma.ai servers (athena, connect, uploads, updates) is an availability risk to users and is assessed in the TARA (T-11) and WP-M-07. LionDriver must not depend on comma servers for any safety function |

The policy is set by a third party and may change. Changes are monitored as part of upstream management ([WP-M-11](WP-M-11-upstream-and-supplier-management.md)).

## 3. Safety and cybersecurity culture

The principles below apply to the maintainer, contributors, reviewers and test drivers. They are written for an open-source project where most participants are volunteers.

| # | Principle | How it shows in practice |
|---|---|---|
| C-1 | Safety issues come before feature work | Open `safety-anomaly` issues and open high-severity gaps are worked before new features. A feature PR is not merged while it would touch code with an unresolved safety anomaly |
| C-2 | No-blame reporting | Reports of hazards, mistakes, near misses and vulnerabilities are welcomed and credited. Problem resolution looks for causes in process and design, not people. A contributor who reports their own mistake is not penalized |
| C-3 | Right to stop | Any test driver can stop a vehicle test at any time without justification. Any reviewer can block a merge on safety grounds; the block is lifted only by resolving the concern or by a documented safety manager decision |
| C-4 | Evidence over assertion | Statements in work products are backed by code references, test results or analysis. "Upstream does it this way" is not evidence |
| C-5 | Independence is respected | Authors do not review their own work at the required independence level. Reviewers and assessors are not pressured on schedule |
| C-6 | Honest status | Work products state what has and has not been done. A Draft is not called complete. Known weaknesses go into the safety case |
| C-7 | Process is followed when inconvenient | Urgent fixes still go through change control (an expedited path is defined in WP-P-02, not a bypass) |
| C-8 | Security is part of safety | Security findings that can lead to a hazard are escalated like safety anomalies |
| C-9 | Learning | Field and test findings feed back into the analyses (HARA, SOTIF, TARA) and into this document's training plan |

Indicators that the culture is working (reviewed at gate reviews): number of anomalies reported by people other than the maintainer; time from report to triage; number of merges to safety-relevant files without the required review (target: zero); stop-test events and their follow-up.

## 4. Competence management

### 4.1 Competence areas

| Code | Area |
|---|---|
| FS | Functional safety (ISO 26262), incl. HARA, safety analyses (FMEA, FTA, DFA), safety-related embedded software |
| SO | SOTIF (ISO 21448): triggering conditions, scenario-based V&V, validation targets |
| CS | Automotive cybersecurity (ISO/SAE 21434): TARA, secure boot and signing, vulnerability management |
| ML | Machine learning safety (ISO/PAS 8800): data, model V&V, uncertainty, monitoring |
| EM | Embedded C on Cortex-M (STM32H7), MISRA C:2012, CAN/CAN FD |
| HW | Hardware safety analysis: FMEDA, metrics, component qualification |
| VT | Vehicle testing: safety-driver practice, test planning, data logging |
| PR | Process: ASPICE, configuration and change management, audits |

### 4.2 Competence requirements matrix

Levels: **A** = awareness (knows the concepts and where they apply), **P** = practitioner (has applied it under supervision or on a comparable project), **E** = expert (has led the activity on a comparable project). "—" = not required.

| Role | FS | SO | CS | ML | EM | HW | VT | PR |
|---|---|---|---|---|---|---|---|---|
| Safety manager | E | P | A | A | A | A | A | P |
| Project maintainer | P | A | A | A | P | A | A | P |
| Cybersecurity manager | A | A | E | — | P | A | — | P |
| SOTIF lead | P | E | A | P | — | — | P | A |
| AI/ML safety lead | A | P | A | E | — | — | — | A |
| Envelope software engineer | P | A | A | — | E | A | — | A |
| Hardware safety engineer | P | — | A | — | A | E | — | A |
| Verification reviewer (safety-relevant code) | P | A | A | — | P | — | — | A |
| Verification reviewer (concept/analysis WPs) | P | P | A | A | — | A | — | A |
| Quality assurance | A | A | A | — | — | — | — | P |
| HIL bench owner | A | — | A | — | P | P | — | A |
| Test / safety driver | A | A | — | — | — | — | E (safety-driver training done) | — |
| External FuSa assessor | E | P | A | A | P | P | A | P |
| External CS assessor | A | — | E | — | P | — | — | P |

Requirements for the external assessors (qualification and independence) are detailed in [WP-M-06](WP-M-06-confirmation-measures-plan.md).

### 4.3 Current state

No competence evidence for any role is recorded in the repository at baseline `8b8c6ae`. The matrix in §4.2 is a requirement, not a statement of current competence. The first competence records are a G0 action (OI-1).

### 4.4 Competence evidence record template

One record per person, stored as `assurance/01-management/competence/<github-handle>.md` (folder to be created). Personal data is limited to what is needed; certificates may be referenced rather than uploaded.

```
| Field | Value |
|---|---|
| Name / GitHub handle | |
| Roles held (WP-M-02 §3.1) | |
| Date of record | |
| Assessed by | <person other than the subject, where possible> |

| Area | Required level (§4.2) | Claimed level | Evidence (training, certificate, prior projects, reviewed work in this repo) | Gap | Action / due |
|---|---|---|---|---|---|
| FS | | | | | |
| SO | | | | | |
| CS | | | | | |
| ML | | | | | |
| EM | | | | | |
| HW | | | | | |
| VT | | | | | |
| PR | | | | | |

Declarations: independence conflicts (e.g., authored the work product to be reviewed): <...>
Next review: <at next gate or 12 months>
```

### 4.5 Rules

- A person is assigned to a role only if their record shows the required level, or a gap with a plan and a supervisor who has the required level.
- Records are reviewed at each gate and when a person takes a new role.
- Where nobody in the project meets a requirement, the activity is either supported by an external expert (recorded as such) or deferred. The gap is recorded in [WP-M-07](WP-M-07-risk-management.md).

## 5. Training plan

| # | Training | Audience | Form | When |
|---|---|---|---|---|
| TR-1 | Project induction: this document, WP-M-01, WP-M-02, assurance README, safety-relevant file list, PR rules | Everyone contributing to safety-relevant files or work products | Self-study plus checklist in the competence record | Before first safety-relevant PR |
| TR-2 | ISO 26262 fundamentals (parts 2–6, 8, 9) | Safety manager, envelope engineers, reviewers | External course or structured self-study with licensed standard | Before G1 for safety manager; before G2 for others |
| TR-3 | ISO 21448 and scenario-based validation | SOTIF lead, safety manager, reviewers of SOTIF WPs | External course or self-study | Before G1 |
| TR-4 | ISO/SAE 21434 and TARA practice | Cybersecurity manager; awareness for all | External course; awareness session | Before G1 (CSM) |
| TR-5 | ISO/PAS 8800 and ML safety | AI/ML safety lead | Self-study, external material | Before G1 |
| TR-6 | MISRA C:2012 and the project deviation process | Envelope engineers, code reviewers | Self-study with worked examples from `opendbc/safety` | Before first envelope PR |
| TR-7 | Safety-driver training (track session, takeover practice, stop rules, data logging) | Test drivers | Practical, per WP-V-07 | Before any LionDriver vehicle test |
| TR-8 | Review technique and checklists (WP-P-05) | Reviewers, QA | Short guide plus supervised first review | Before first review |
| TR-9 | Vulnerability handling and secure key management | Maintainer, CSM, release managers | Self-study | Before first signed release |

Training completion is recorded in the competence record (§4.4).

## 6. Communication

| Channel | Use | Notes |
|---|---|---|
| GitHub issues (public) | Work items, safety anomalies (`safety-anomaly`), QA findings, risks, decisions | Default channel; keeps a record |
| GitHub pull requests | Reviews and approvals of code and work products | Review comments are review records (WP-P-05) |
| Private security channel | Vulnerability reports | To be defined in `SECURITY.md` (gap §9 action 9, GAP-28); currently upstream routes to comma.ai |
| GitHub Discussions or equivalent | Questions from users and contributors | Not a record of decisions; decisions are moved to issues |
| Gate review records | Gate decisions | `10-safety-case/gates/` (WP-M-02 §10; folder to be created, WP-M-02 OI-5) |
| Assessor correspondence | Confirmation review requests and reports | Reports stored under `10-safety-case/confirmation/` (folder to be created, WP-M-06 OI-6) |
| Upstream (comma.ai) | Reporting safety or security issues found in upstream code | Best effort, no agreement; see WP-M-11 |
| Safety ↔ SOTIF ↔ CS ↔ AI interface | Shared hazard log, TARA links, model changes | Cross-discipline items are labelled with all affected disciplines; joint review at each gate |

## 7. Open items

| ID | Open item | Owner | Due |
|---|---|---|---|
| OI-1 | Create the first competence record (maintainer / acting safety manager) and have it assessed by someone other than the subject | PM | G0 |
| OI-2 | The safety manager role requires FS level E; record evidence or name an external mentor/supervisor for the gap | PM | G0 |
| OI-3 | Decide how contributors' competence is checked without making contribution impractical (proposal: TR-1 checklist for safety-relevant PRs only; reviewers carry the competence requirement) | SM | G0 |
| OI-4 | Define the private vulnerability channel and publish `SECURITY.md` | CSM | G0 |
| OI-5 | Confirm whether LionDriver will create a legal entity or other structure for contracts (assessor, pen test, insurance) | PM | G1 |
| OI-6 | Confirm the project name and release artefacts comply with the upstream trademark constraint (§2.3) | PM | G0 |
