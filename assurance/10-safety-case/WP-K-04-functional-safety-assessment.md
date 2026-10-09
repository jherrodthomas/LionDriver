# WP-K-04 Functional Safety Assessment (Plan and Report)

| Field | Value |
|---|---|
| Work product | WP-K-04 Functional safety assessment report |
| Standard reference | ISO 26262-2:2018 §6 (functional safety assessment, independence per Table 1); ISO 26262-2 §6 (confirmation measures); [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) §6 (FSA-I1, FSA-I2, FSA-F) |
| Version | 0.1 |
| Status | Skeleton — plan and report template. **No assessment has been performed and no assessor has been engaged (D-06 open).** All result sections are "Not yet executed" |
| ASIL / scope | Item LD-SDA, up to ASIL C (SG-01) |
| Author | Assurance team (initial draft); report to be authored by the assessor |
| Reviewer(s) | n/a (the assessment is itself the independent confirmation measure) |
| Approver | Assessor (report); safety manager acknowledges receipt |
| Baseline | `8b8c6ae` |

## 1. Purpose

The functional safety assessment (FSA) judges whether the functional safety achieved by LD-SDA is adequate. It is performed by an assessor independent of the project at **I3** ([WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md); tailoring T-09). This file holds the plan (§2–§5) and the report template (§6–§9). Interim assessments FSA-I1 (G1) and FSA-I2 (G2) use the same template and are stored as `10-safety-case/confirmation/FSA-I1.md` and `FSA-I2.md` (folder to be created, [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) OI-6); the final FSA-F (G5) is written into this file.

## 2. Assessor and independence

| Field | Value |
|---|---|
| Assessor (person, organisation) | TBD (D-06) |
| Independence level | I3: independent of the LionDriver project in management, resources and release authority |
| Independence declaration | Template: "I have not authored, reviewed as verifier, or approved any work product in the scope of this assessment, and I have no reporting line to, or financial dependence on, the release decision." Signed and dated |
| Competence evidence | Qualification and experience in ISO 26262 assessment at ASIL C or higher; familiarity with ISO 21448 and aftermarket/retrofit items preferred ([WP-M-04](../01-management/WP-M-04-organization-competence-safety-culture.md)) |
| Access | Read access to the repository at the assessed baseline; access to vehicle test records and installation records; interviews with role holders |

## 3. Scope

| Aspect | In scope |
|---|---|
| Item and configuration | LD-SDA reference configuration ([WP-M-01 §3.1](../01-management/WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to)) at a named baseline |
| Work products | All work products in [WP-M-00](../01-management/WP-M-00-work-product-register.md) relevant to ISO 26262 (01-management, 02-concept FuSa items, 03-system, 04-hardware, 05-software, 06-validation FuSa items, 07-supporting, 08-analyses, 09-production-operation, WP-K-01, trace data) |
| Processes | Execution of the safety plan ([WP-M-02](../01-management/WP-M-02-safety-plan.md)), including results of confirmation reviews and functional safety audits |
| Safety measures | Implementation and effectiveness of the safety mechanisms of the envelope and host, and of the measures for production/installation and operation |
| Tailoring | Rationale for T-01…T-13 and its effect on the argument |
| Out of scope (separate assessments) | Cybersecurity assessment ([WP-K-05](WP-K-05-cybersecurity-assessment.md)); SOTIF release recommendation ([WP-K-02](WP-K-02-sotif-release-argument.md)) — the FSA considers their results as inputs where they affect safety goals |

## 4. Assessment plan

| Step | Activity | Input | Output |
|---|---|---|---|
| P1 | Agree scope, baseline, schedule and access | This plan | Signed plan (§2–§5) |
| P2 | Check confirmation review results CR-01…CR-12 and audit results | [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) records | Findings |
| P3 | Assess work products: completeness, correctness, consistency, traceability (sampling plan per ASIL) | Work products, `trace/` check report | Findings |
| P4 | Assess the process: plans followed, reviews done at required independence, change and problem records complete | Review records, change/problem issues, gate records | Findings |
| P5 | Assess safety measures: evidence that each safety mechanism exists, is verified (tests, fault injection, HIL) and meets its FTTI | WP-S-02, WP-S-04, WP-W-06…W-08, WP-V-05 | Findings |
| P6 | Assess the safety case: argument validity, evidence sufficiency, defeaters | [WP-K-01](WP-K-01-safety-case.md) | Findings |
| P7 | Interviews (role holders, safety drivers) and witness of selected tests (optional) | — | Notes |
| P8 | Report and recommendation | All findings | §6–§9 |

Timing: FSA-I1 at G1, FSA-I2 at G2, FSA-F at G5 ([WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md)).

## 5. Finding categories

| Category | Definition | Effect on recommendation |
|---|---|---|
| **Major** (non-conformity) | A required work product, activity or safety measure is missing or ineffective such that a safety goal may not be achieved, or the argument is invalid | Any open Major → Reject (or Conditional only if a containment makes the release safe and is part of the release) |
| **Minor** (non-conformity) | A deviation that does not by itself put a safety goal at risk (incomplete record, inconsistent ID, missing rationale) | Conditional acceptance with due date |
| **Observation** | Improvement suggestion; no non-conformity | None |
| **Positive** | Noted strength | None |

## 6. Assessment record — Not yet executed

| Field | Value |
|---|---|
| Assessment ID | FSA-F |
| Baseline assessed | `ld-vX.Y.Z` / `ld-bl-G5-YYYYMMDD` |
| Dates | |
| Documents examined | (list with versions) |
| Interviews | |

## 7. Findings — Not yet executed

| # | Category | Area (WP / process / measure) | Finding | Requirement / clause | Evidence examined | Required action | Due | Status |
|---|---|---|---|---|---|---|---|---|

## 8. Assessment of tailoring and known defeaters — Not yet executed

| Tailoring / defeater | Assessor judgement |
|---|---|
| T-01 … T-13 | |
| DF-01 … DF-28 ([WP-K-01 §7](WP-K-01-safety-case.md#7-defeaters-counter-evidence)) | |

## 9. Recommendation — Not yet executed

| Field | Value |
|---|---|
| Result | **Accept** / **Accept with conditions** / **Reject** |
| Conditions (if any) | (each condition tracked as an issue with owner and gate) |
| Statement | Template: "Based on the evidence examined at baseline `<tag>`, the functional safety achieved by LD-SDA in the reference configuration is judged `<adequate / adequate subject to conditions / not adequate>`." |
| Assessor signature, date | |

The release record ([WP-K-06](WP-K-06-release-record.md)) cites this result. A Reject blocks release ([WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md)).

## 10. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Engage the external assessor (D-06) and agree this plan | G1 |
| OI-2 | Agree the sampling depth for P3 per ASIL with the assessor | G1 |
| OI-3 | Confirm independence-level requirements against the licensed ISO 26262-2 Table 1 for the final ASILs (after the envelope strategy decision) | G1 |
