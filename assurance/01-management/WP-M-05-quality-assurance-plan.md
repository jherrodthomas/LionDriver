# WP-M-05 Quality Management and Quality Assurance Plan

| Field | Value |
|---|---|
| Work product | WP-M-05 Quality management and quality assurance plan |
| Standard reference | ASPICE 4.0 SUP.1 (quality assurance); ISO 26262-2:2018 §5 (quality management as a prerequisite for functional safety); ISO/SAE 21434:2021 §5 (quality management for cybersecurity); IATF 16949 (informative only) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (process) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer |
| Baseline | `8b8c6ae` |

## 1. Purpose

ISO 26262-2 §5 and ISO/SAE 21434 §5 expect functional safety and cybersecurity work to sit on top of a quality management system. LionDriver has no certified QMS and does not intend to get one (IATF 16949 is used for orientation only). This plan defines the minimum quality management the project runs instead, and the quality assurance (SUP.1) activities that give objective evidence that work products and processes follow the plans.

Current state at baseline `8b8c6ae`: no QA function, plan or audit record exists (gap assessment §7: SUP.1 CL0). CI quality gates exist upstream (see §5.3), but whether they run for LionDriver depends on D-03.

## 2. Quality objectives

| # | Objective | Indicator | Target |
|---|---|---|---|
| QO-1 | Work products conform to the README conventions and to their plan | Audit findings per WP audited | No open major finding at gate |
| QO-2 | Safety-relevant changes are reviewed and impact-analysed | Merges to safety-relevant files without required review / impact statement | Zero |
| QO-3 | CI quality gates are enforced for safety-relevant code | Safety-relevant merges with a failing or skipped required check | Zero |
| QO-4 | Non-conformances are closed in time | Open QA findings past due date | Zero at gate review |
| QO-5 | Process capability reaches the T-12 targets | Self-assessment rating ([WP-M-13](WP-M-13-aspice-capability-baseline.md)) | CL2 / CL1 per WP-M-01 T-12 by G5 |

## 3. Quality management elements

| Element | Where defined |
|---|---|
| Organization and responsibilities | [WP-M-02 §3](WP-M-02-safety-plan.md), [WP-M-04](WP-M-04-organization-competence-safety-culture.md) |
| Document control and conventions | [`assurance/README.md`](../README.md), [WP-P-04](../07-supporting/WP-P-04-documentation-management.md) |
| Configuration management | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) |
| Change management | [WP-P-02](../07-supporting/WP-P-02-change-management.md) |
| Problem resolution and non-conformance | [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) |
| Verification and review | [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) |
| Tool management | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) |
| Supplier / upstream management | [WP-M-11](WP-M-11-upstream-and-supplier-management.md) |
| Competence and training | [WP-M-04](WP-M-04-organization-competence-safety-culture.md) |
| Quality assurance | This document |

## 4. QA independence

SUP.1 expects QA to be performed objectively, by people who did not produce the work being checked and who can escalate without conflict. With one maintainer this cannot be met internally today.

| Option | Independence | Use |
|---|---|---|
| Q-A External QA reviewer (volunteer contributor or paid reviewer not authoring the audited WPs) | Adequate | **Target.** Named QA person in WP-M-02 §3.1 by G0 (OI-1) |
| Q-B Cross-audit by a contributor who authored other work products, not the audited one | Partial (acceptable per work product) | Allowed once there are at least two authors |
| Q-C External assessor's functional safety audit ([WP-M-06](WP-M-06-confirmation-measures-plan.md)) | Strong, but infrequent | Complements Q-A/Q-B at G2, G4; does not replace routine QA |
| Q-D Self-check by author using the checklist, separated in time | None (I0) | **Interim only** until Q-A exists. Recorded as self-check, never presented as QA audit |
| Q-E Automated checks in CI | Objective for what they cover | Always on for the checks they implement (§5.3) |

Rules:

- The QA person reports findings to the project maintainer and, for safety-related findings, also to the safety manager. While both are the same person, unresolved major findings are also copied to the external assessor.
- QA has the right to raise a finding against any work product or process step, including those owned by the maintainer.
- A gate cannot pass on Q-D self-checks alone for work products that WP-M-06 lists for confirmation review.

## 5. QA activities

### 5.1 Work product audits

| Aspect | Check |
|---|---|
| Form | Document control header complete and correct per README; status consistent with WP-M-00; baseline commit named |
| Links | Relative links use the file names in WP-M-00; referenced IDs exist |
| Content vs. plan | The work product covers the activities its plan and source clauses require (by reference to the licensed standard) |
| Honesty | No claim of completed activity or existing evidence that the repository does not show |
| Traceability | Requirements and analyses have IDs; trace entries exist in `trace/` where WP-P-06 requires them |
| Review evidence | Verification review record exists for any WP in status In review or later, with the right independence |
| Open items | OI list present; items have owner and due gate |

Sampling: every G0 work product is audited before G0. From G1 on, every work product due at the gate gets at least a form audit; safety-relevant analysis and requirement work products get a full audit.

### 5.2 Process audits per gate

| Gate | Processes audited | Evidence sampled |
|---|---|---|
| G0 | CM (submodules, branches), change management (PR flow, CODEOWNERS, branch protection), documentation management | Repo settings, `.gitmodules`, sample of merged PRs |
| G1 | Change management, verification and review, problem resolution, requirements management start | Review records of concept WPs; anomaly issues; trace data |
| G2 | Requirements management and traceability, review, risk management | Trace consistency; risk register updates |
| G3 | SW development process (coding guidelines, MISRA deviations, unit verification), tool qualification | Sample of envelope PRs; deviation records; coverage and mutation reports |
| G4 | Integration and test process, HIL configuration control, problem resolution | Test reports vs. specs; HIL configuration records |
| G5 | Release management, safety case completeness, all open findings | Release record; open item lists |
| G6 | Field monitoring and incident response, change control after release | Field reports; update records |

Process audits also cover the project management practices in [WP-M-03](WP-M-03-project-plan.md) and [WP-M-07](WP-M-07-risk-management.md) (tracking, re-planning, risk updates).

### 5.3 CI quality gates

These checks are the automated part of QA. Status column describes the baseline honestly.

| Gate | Scope | Criterion | Status at `8b8c6ae` |
|---|---|---|---|
| QG-1 opendbc safety unit tests | `opendbc/safety` | All tests pass | Exist in the opendbc repository's own CI (`opendbc_repo/.github/workflows/tests.yml`). LionDriver's `tests.yaml` does not run them; they run in comma's opendbc repo, not under LionDriver control (D-01, D-03) |
| QG-2 Line coverage | `opendbc/safety` | 100 % line coverage (`gcovr --fail-under-line=100`) | Same as QG-1 |
| QG-3 Structural coverage beyond line | `opendbc/safety`, panda firmware paths in the envelope | Branch coverage, MC/DC as required by the HARA ASIL (WP-W-06) | Not implemented (GAP-13) |
| QG-4 MISRA C:2012 | `opendbc/safety`, panda firmware incl. bootstub | No new violations; every suppression has a deviation record | Check exists for opendbc safety and panda (not bootstub); suppressions have no formal deviation records (GAP-13) |
| QG-5 Mutation testing | `opendbc/safety` | No new surviving mutants; existing survivors justified | Exists upstream; 3 accepted survivors without formal justification (GAP-13) |
| QG-6 Unit tests and process replay | openpilot | All pass; replay against fork-owned references | Unit tests run in LionDriver `tests.yaml` on hosted runners; replay references come from comma storage (GAP-30) |
| QG-7 Static analysis / lint | openpilot | ruff, codespell, cpplint, type check pass | Runs in `tests.yaml` (`static_analysis`); type checking weak (GAP-36) |
| QG-8 Submodule and dirty-tree checks | Repo | Submodules pinned to LionDriver-controlled commits; clean tree | `check-submodules.sh` checks against upstream master, which conflicts with D-01 |
| QG-9 Required review | Safety-relevant files | CODEOWNERS approval from a reviewer other than the author | Not implemented (GAP-32) |
| QG-10 Work product link check | `assurance/` | Relative links resolve, or point to a WP listed in WP-M-00 | Not implemented (proposed) |

QG-1, QG-2, QG-4, QG-5, QG-8 and QG-9 must be required status checks on the protected branch for safety-relevant changes by G0. QG-3 by G3.

## 6. Escalation

| Level | Trigger | Escalated to | Expected response |
|---|---|---|---|
| 1 | Finding not accepted by the author, or not closed by due date | Project maintainer | Decision within 10 working days |
| 2 | Safety-related finding not resolved at level 1, or maintainer is the author | Safety manager and, while roles coincide, the external assessor (informed) | Recorded decision; gate condition if not resolved |
| 3 | Finding indicates a potential safety goal violation | Handled as a safety anomaly (WP-M-02 §9) | Immediate; test stop rule applies |

Escalations and decisions are recorded on the finding's issue.

## 7. Non-conformance handling

1. QA records each finding as a GitHub issue with label `qa-finding`, severity (`major` / `minor` / `observation`), the work product or process, the requirement not met, and the evidence.
2. The finding is handled through problem resolution ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)): owner, cause, correction, and for majors a corrective action to prevent recurrence.
3. Corrections to work products or code go through change management ([WP-P-02](../07-supporting/WP-P-02-change-management.md)).
4. QA verifies the correction and closes the issue. The author does not close their own QA finding.
5. Severity definitions: **major** — a required activity, review or evidence is missing, or a claim is not supported; **minor** — form or consistency error with no effect on a safety argument; **observation** — improvement suggestion.
6. Open majors block the gate unless a gate condition with owner and due date is recorded.

## 8. Quality criteria per work product type

| Type | Examples | Quality criteria |
|---|---|---|
| Plan | WP-M-02…M-13, WP-P-* | Header; scope; roles; activities with responsible role; links to register; open items |
| Analysis | HARA, FMEA/FTA, DFA, FFI, TARA, SOTIF analyses | Method stated; inputs and baseline named; complete against the item definition; every result has an ID; assumptions explicit; results traced to requirements; reviewed at required independence |
| Requirements | FSR, TSR, SWSR, HWSR, CSR | Unique ID; atomic; verifiable; ASIL or CAL attribute; parent trace; allocation; verification method; status |
| Architecture / design | WP-S-03, WP-W-03, WP-H-02 | Elements and interfaces identified; ASIL allocation; FFI claims explicit; consistent with code at the baseline |
| Code (safety-relevant) | `opendbc/safety`, panda firmware | Coding guideline (WP-W-01) followed; MISRA clean or deviation recorded; reviewed per QG-9; tests and coverage per QG-1…QG-5 |
| Test specification | WP-W-06…W-08, WP-S-08/09, WP-V-* | Each test traces to a requirement; pass criteria defined; environment and configuration named |
| Test report | Same | Executed against a named baseline; results reproducible; deviations and failures linked to issues |
| Case / argument | WP-K-01…K-03 | Each claim has evidence at a named baseline; gaps and assumptions shown; consistent with the register status |
| Record | Review, audit, gate, confirmation records | Date, participants, independence, object and baseline, findings, decision |

## 9. Records

| Record | Location |
|---|---|
| QA audit reports (work product and process) | `assurance/10-safety-case/qa/` (folder to be created), one file per audit: `QA-<gate>-<nn>.md` |
| QA findings | GitHub issues labelled `qa-finding` |
| CI gate results | GitHub Actions run logs, referenced by commit; release-relevant runs archived with the release record ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) because hosted logs expire |
| Self-checks (interim, Q-D) | Same folder, file name prefixed `SELF-`, marked I0 |
| QA summary per gate | Input to the gate record (WP-M-02 §10) |

## 10. Open items

| ID | Open item | Owner | Due |
|---|---|---|---|
| OI-1 | Name a QA person independent of the author (Q-A) | PM | G0 |
| OI-2 | Make QG-1, QG-2, QG-4, QG-5 run in LionDriver-controlled CI after D-01 and D-03 | PM | G0 |
| OI-3 | Replace or reconfigure `check-submodules.sh` so QG-8 checks LionDriver forks, not upstream master | PM | G0 |
| OI-4 | Define the CI log archiving method for release evidence | PM | G3 |
| OI-5 | Write formal MISRA deviation records for existing suppressions and justifications for surviving mutants | ENG | G3 |
| OI-6 | Implement QG-10 work product link check | QA | G1 |
