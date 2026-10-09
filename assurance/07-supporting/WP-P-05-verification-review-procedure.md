# WP-P-05 Verification and Review Procedure

| Field | Value |
|---|---|
| Work product | WP-P-05 Verification and review procedure |
| Standard reference | ISO 26262-8:2018 §9; ISO 26262-2:2018 §6 (independence, confirmation measures interface); ASPICE 4.0 SUP.2 (informative), SUP.1 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Defines how work products and code are verified by review: review types, entry and exit criteria, checklists per work product type, independence, and records. Verification by test and analysis is planned in the verification work products ([WP-W-06](../05-software/WP-W-06-software-unit-verification.md), [WP-W-07](../05-software/WP-W-07-software-integration-verification.md), [WP-S-08](../03-system/WP-S-08-system-integration-test.md), [WP-S-09](../03-system/WP-S-09-system-verification.md)). Confirmation reviews, audits and assessment are in [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md); this procedure provides their record format.

Current state: no review records exist; upstream "review" is labelling only (GAP-32, [gap assessment](../00-assessment/gap-assessment.md)).

## 2. Review types

| Type | Purpose | Participants | Use for |
|---|---|---|---|
| R1 Desk check | One reviewer reads the change with the checklist | Author + 1 reviewer | NSR changes, SR-T changes, Draft WPs |
| R2 Walkthrough | Author presents; reviewers question; good for understanding and early feedback | Author + ≥1 reviewer (call or async PR thread) | Concept-level WPs before submission, large upstream syncs |
| R3 Inspection | Formal: prepared reviewers, checklist-driven, findings logged with severity, re-inspection on major findings | Moderator (not author) + author + ≥1 inspector | SR-A code; HARA, FSC, TSC, SW/HW safety requirements, safety analyses, safety case |
| R4 Tool-assisted analysis review | Review of static analysis, coverage and mutation reports for completeness and justified deviations | 1 reviewer | Each SR-A PR, each MISRA deviation |

Async inspection in a GitHub PR is allowed if every checklist item is answered in a review comment and every finding is a resolved review thread.

## 3. Independence levels

Defined for LionDriver in line with ISO 26262-2 §6 (Table 1) and the tailoring T-09 in [WP-M-01](../01-management/WP-M-01-assurance-strategy.md#5-tailoring).

| Level | Meaning in LionDriver |
|---|---|
| I0 | Review recommended; may be done by the author's peer or by the author with a checklist |
| I1 | Done by a person other than the author |
| I2 | Done by a person not in the team responsible for the work product (e.g. an external contributor who did not write or direct it) |
| I3 | Done by a person organizationally independent of the project (external assessor) |

Verification reviews require at least I1 for SR-A and SR-Q items. With a single maintainer this requires an external reviewer ([WP-P-02 OI-1](WP-P-02-change-management.md#13-open-items)). Self-review is recorded as I0 and does not satisfy an I1 requirement.

## 4. Entry and exit criteria

| | Entry | Exit |
|---|---|---|
| All reviews | PR open; CI green; author self-check done (checklist ticked by author); classification label set; linked CR/problem issue | All findings resolved or converted to tracked issues with agreed severity; required approvals given; record complete (§7) |
| Code (SR-A) | Unit tests, coverage gate, MISRA and mutation pass; impact analysis present | No open major finding; trace updated |
| Work product | Header complete; status "In review"; links resolve; trace IDs exist in `assurance/trace/` | Status set to Approved in the merge; register updated |
| Inspection (R3) | Reviewers had the material ≥ 2 working days | Re-inspection done if any major finding changed > 20% of the item |

Finding severity: **Major** (wrong, missing, or unverifiable safety content; must fix before approval), **Minor** (unclear or incomplete; fix before approval or track), **Note** (suggestion).

## 5. Checklists

Use the checklist for the WP type; the reviewer pastes it into the review with each item answered Y / N / N/A plus comment. Items are written in LionDriver's own words.

### 5.1 HARA ([WP-C-03](../02-concept/WP-C-03-hara.md))

| # | Check |
|---|---|
| H1 | Item functions and boundary match [WP-C-01](../02-concept/WP-C-01-item-definition.md) and the reference configuration |
| H2 | Malfunctioning behaviours derived systematically for every function (lateral, longitudinal, engagement, driver monitoring, HMI) |
| H3 | Operational situations cover the ODD in [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md), including situations at ODD edges |
| H4 | Each S, E, C rating has a rationale; C ratings that assume an attentive driver say so explicitly |
| H5 | ASIL determination consistent with the ratings |
| H6 | Safety goals have ASIL, safe state, FTTI where known, and cover every rated hazardous event |
| H7 | Shared hazard log cross-references SOTIF and TARA entries |
| H8 | No hazard rated QM without written reason |

### 5.2 Functional safety concept ([WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md))

| # | Check |
|---|---|
| F1 | Each FSR traces to a safety goal; each safety goal is covered by FSRs |
| F2 | FSRs allocated to elements of the preliminary architecture, incl. the envelope, driver and external measures |
| F3 | Fault detection, reaction, safe state and warning concepts stated with timing vs FTTI |
| F4 | AoUs on vehicle ECUs (EPS, PCS) explicit and verifiable |
| F5 | ASIL decomposition, if used, documented in [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md) with independence argument |
| F6 | Requirements meet quality criteria of [WP-P-06 §3](WP-P-06-requirements-management-traceability.md#3-quality-criteria) |

### 5.3 Technical safety concept / system architecture ([WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md))

| # | Check |
|---|---|
| T1 | Each TSR traces to an FSR; no FSR without TSR |
| T2 | Safety mechanisms specified with detection coverage intent, reaction, and time budget ([WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md)) |
| T3 | HW/SW allocation and HSI consistent ([WP-S-05](../03-system/WP-S-05-hsi-specification.md)) |
| T4 | FFI and DFA findings ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md), [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md)) reflected in the architecture |
| T5 | Envelope limits have physical units and controllability rationale (GAP-04) |
| T6 | Configuration of the envelope by the QM host addressed (GAP-09) |

### 5.4 Requirements (any level: FSR, TSR, SWSR, HWSR, CSR, SOTIF)

| # | Check |
|---|---|
| Q1 | All attributes of [WP-P-06 §2](WP-P-06-requirements-management-traceability.md#2-requirement-attributes) present |
| Q2 | Unambiguous, atomic, verifiable, feasible, consistent (no conflicts with siblings) |
| Q3 | Parent link correct; ASIL inherited or decomposition referenced |
| Q4 | Verification method appropriate for the ASIL |
| Q5 | Units, ranges, tolerances, timing stated |
| Q6 | YAML in `assurance/trace/` matches the Markdown text; consistency check passes |

### 5.5 Software / hardware architecture ([WP-W-03](../05-software/WP-W-03-software-architecture.md), [WP-H-02](../04-hardware/WP-H-02-hardware-design.md))

| # | Check |
|---|---|
| A1 | Every SWSR/HWSR allocated to an architectural element |
| A2 | Static and dynamic views; interfaces with data types, ranges, timing |
| A3 | Safety-related and non-safety-related parts identified; partitioning and FFI mechanisms named |
| A4 | Error handling, startup and shutdown behaviour described (incl. watchdog, fault → safe state) |
| A5 | Resource use (CPU, memory, interrupt load) estimated for the panda MCU |
| A6 | Architecture matches the code at the baseline (spot-check named files) |

### 5.6 Code (SR-A; also used for SR-Q with judgement)

| # | Check |
|---|---|
| C1 | Change implements the referenced requirement(s) and nothing else |
| C2 | Coding guidelines of [WP-W-01](../05-software/WP-W-01-software-development-environment-guidelines.md) followed; MISRA result clean; any new deviation has a record |
| C3 | No new global suppressions in `opendbc_repo/opendbc/safety/tests/misra/suppressions.txt` or `panda/tests/misra/suppressions.txt` without CCB decision |
| C4 | Integer overflow, sign, division, array bounds, and uninitialised data checked |
| C5 | Limits and timing constants match requirements; units documented |
| C6 | Every new branch covered by a test; coverage gate passes; new surviving mutants justified |
| C7 | No debug-only behaviour reachable in release builds (`ALLOW_DEBUG` gating, cf. GAP-09, GAP-25) |
| C8 | Concurrency: ISR vs main-loop shared data protected |
| C9 | Tests reference requirement IDs (`@req`) |

### 5.7 Test specification

| # | Check |
|---|---|
| V1 | Each test case lists requirement IDs, preconditions, inputs, expected results, pass criteria |
| V2 | Methods derived per ASIL (requirements-based, boundary values, equivalence classes, error guessing, fault injection) |
| V3 | Every requirement has ≥ 1 test or a justified other verification method |
| V4 | Test environment stated (host x86 build vs Cortex-M7 target vs HIL vs vehicle) and its limits for the claim |
| V5 | Expected results independent of the implementation (not derived by running the code) |
| V6 | Regression set and tool versions recorded |

### 5.8 Safety analyses (FMEA, FTA, DFA, FMEDA)

| # | Check |
|---|---|
| S1 | Scope and architecture version stated |
| S2 | Failure modes systematically derived (guide words / component failure modes) |
| S3 | Each effect traced to a safety goal or shown harmless |
| S4 | Measures traced to requirements; open measures tracked as issues |

## 6. Roles

| Role | Responsibility |
|---|---|
| Author | Self-check, submits, resolves findings |
| Reviewer / inspector | Applies checklist, records findings |
| Moderator (R3) | Ensures preparation, logs findings, decides re-inspection; not the author |
| Approver | Approves the PR per the WP header |

## 7. Records

### 7.1 PR-based record (default)

The merged PR is the record when it contains: the checklist with answers; findings as review threads, each resolved; the approval(s) with reviewer identity; the reviewer's independence level stated in the approving review text (`Independence: I1`); and the CI results. Records are exported at baselines ([WP-P-04 §8](WP-P-04-documentation-management.md#8-storage-backup-and-export)).

### 7.2 Review record template (R3 inspections, confirmation reviews, reviews outside GitHub)

Stored as `assurance/<folder>/reviews/RR-<YYYY>-<nnn>.md` (confirmation reviews under `10-safety-case/confirmation/`).

```markdown
# RR-<YYYY>-<nnn> Review record
| Field | Value |
|---|---|
| Item reviewed | WP-x-nn vX.Y / PR #n / file list |
| Baseline | <commit SHA> |
| Review type | R1 / R2 / R3 / R4 / confirmation |
| Checklist | WP-P-05 §5.x |
| Date(s) | |
| Moderator | |
| Author | |
| Reviewer(s) and independence | name - I1/I2/I3 |
| Preparation time | |

## Findings
| # | Location | Description | Severity (Major/Minor/Note) | Disposition | Issue / commit |
|---|---|---|---|---|---|

## Result
- [ ] Accepted  - [ ] Accepted with minor changes  - [ ] Re-review required
Signature / approving GitHub review link:
```

## 8. Metrics

Findings per review by severity; preparation time; share of SR-A PRs with complete checklist (target 100%); escaped defects (problem reports whose root cause was in a reviewed item). Reported to [WP-M-05](../01-management/WP-M-05-quality-assurance-plan.md).

## 9. Open items

| ID | Item |
|---|---|
| OI-1 | Name reviewers who can provide I1 and I2 for SR-A items |
| OI-2 | Create `reviews/` folders as needed and add RR records to the export |
| OI-3 | Checklists for SOTIF, TARA and ML work products (WP-C-05..C-11, WP-W-10) still to be written |
| OI-4 | Decide the review method for the large back-filled envelope requirement set (T-03): one inspection per safety mode file and per panda driver file is proposed |
