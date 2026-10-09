# WP-K-05 Cybersecurity Assessment (Plan and Report)

| Field | Value |
|---|---|
| Work product | WP-K-05 Cybersecurity assessment report |
| Standard reference | ISO/SAE 21434:2021 §6 (cybersecurity assessment; cybersecurity case as input; release for post-development); [WP-M-09 §8](../01-management/WP-M-09-cybersecurity-plan.md); [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) (confirmation measures, independence) |
| Version | 0.1 |
| Status | Skeleton — plan and report template. **No assessment has been performed and no assessor has been engaged ([WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-6).** All result sections are "Not yet executed" |
| ASIL / scope | CS (CAL 1–3) for item LD-SDA, reference configuration |
| Author | Assurance team (initial draft); report to be authored by the assessor |
| Reviewer(s) | n/a (the assessment is itself the independent judgement) |
| Approver | Assessor (report); cybersecurity manager acknowledges receipt |
| Baseline | `8b8c6ae` |

## 1. Purpose

The cybersecurity assessment judges whether the cybersecurity of LD-SDA is adequate, based on the cybersecurity case ([WP-K-03](WP-K-03-cybersecurity-case.md)), the work products and the process evidence. Its recommendation (accept / conditionally accept / reject) is a precondition for release for post-development ([WP-M-09 §9](../01-management/WP-M-09-cybersecurity-plan.md); [WP-K-06](WP-K-06-release-record.md)). This file holds the plan (§2–§5) and the report template (§6–§9). The preliminary assessment at G1 (CSA-I1) uses the same template and is stored as `10-safety-case/confirmation/CSA-I1.md`; the final assessment (CSA-F, G5) is written into this file.

## 2. Assessor and independence

| Field | Value |
|---|---|
| Assessor (person, organisation) | TBD (WP-M-09 OI-6) |
| Independence | Independent of the LionDriver project: has not authored, verified, implemented or penetration-tested any item in scope, and has no reporting line to or financial dependence on the release decision. With a single maintainer this can only be met externally (T-09, WP-M-09 §8) |
| Independence declaration | Template: "I have not authored, reviewed as verifier, implemented, tested or approved any work product or control in the scope of this assessment, and I have no reporting line to, or financial dependence on, the release decision." Signed and dated |
| Competence evidence | Experience in ISO/SAE 21434 assessment or audit; embedded/firmware security (secure boot, MCU option-byte protection); Linux device security; familiarity with ISO 26262 interfaces preferred ([WP-M-04](../01-management/WP-M-04-organization-competence-safety-culture.md)) |
| Access | Repository at the assessed baseline; restricted vulnerability register and penetration-test report ([WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md), [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md)); interviews with role holders |
| Combination with FSA | Permitted where the same assessor has both competences ([WP-M-09 §8](../01-management/WP-M-09-cybersecurity-plan.md)); findings are recorded separately from [WP-K-04](WP-K-04-functional-safety-assessment.md) |

## 3. Scope

| Aspect | In scope |
|---|---|
| Item and configuration | LD-SDA reference configuration ([WP-M-01 §3.1](../01-management/WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to)) at a named release baseline |
| Work products (§6 of the standard) | [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md), [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md), [WP-M-12](../01-management/WP-M-12-impact-analysis.md), [WP-C-09](../02-concept/WP-C-09-tara.md), [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md), [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md), [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md), [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md), [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) §7, [WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) §6–§7, [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md), [WP-K-03](WP-K-03-cybersecurity-case.md), [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| Evidence sampling | §10 evidence (requirements, implementation, verification) sampled with weight by CAL: all CAL 3 CSRs, a sample of CAL 2 and CAL 1 CSRs |
| Process | Execution of the cybersecurity plan; change, problem and release records with `cat-cs`; review independence |
| Tailoring | CT-1…CT-4 and T-11 rationale and effect on the argument |
| Out of scope | Functional safety assessment ([WP-K-04](WP-K-04-functional-safety-assessment.md)); SOTIF release ([WP-K-02](WP-K-02-sotif-release-argument.md)); comma.ai back-end (external entity) — considered only as assumptions CA-01…CA-05 and claims CSC-02/CSC-04 |

## 4. Assessment plan

| Step | Activity | Input | Output |
|---|---|---|---|
| A1 | Agree scope, baseline, schedule, access and finding categories | This plan | Signed plan |
| A2 | Assess the TARA: completeness of assets/threats, rating consistency, safety anchoring, treatment decisions | WP-C-09 | Findings |
| A3 | Assess goals, claims, CAL determination and the concept; agree or reject CAL proposals | WP-C-10 | Findings |
| A4 | Assess requirements and architecture: refinement and allocation of CSR-C to CSR, trust boundaries, architecture decisions CS-AD-01…04, relation to TSRs | WP-S-07 | Findings |
| A5 | Assess implementation and verification evidence per CAL (sampling); build-config audit; SAST; SBOM and scan | WP-W-11, evidence package | Findings |
| A6 | Assess validation and penetration test results; residual-risk acceptance | WP-V-06, WP-K-03 §5 | Findings |
| A7 | Assess post-development readiness: monitoring, vulnerability management, incident response, update management, provisioning, end of support | WP-O-05, WP-O-01, WP-O-02 | Findings |
| A8 | Assess the cybersecurity case: argument validity, evidence sufficiency, defeaters CDF-01…CDF-10 | WP-K-03 | Findings |
| A9 | Interviews and optional witness of selected tests | — | Notes |
| A10 | Report and recommendation | All findings | §6–§9 |

Timing: CSA-I1 at G1 (A1–A3, partial A8); CSA-F at G5 (A1–A10). Further interim assessments on request of the cybersecurity manager.

## 5. Criteria and finding categories

Assessment criteria: the objectives of ISO/SAE 21434 for each clause in scope (checked against the assessor's licensed copy), the project's own plan ([WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md)) and the acceptance rules of the TARA ([WP-C-09 §7](../02-concept/WP-C-09-tara.md)).

| Category | Definition | Effect on recommendation |
|---|---|---|
| **Major** | A required activity, work product or control is missing or ineffective such that a cybersecurity goal may not be achieved, or a residual risk with safety impact is unjustified | Any open Major → Reject (or Conditional only if a containment, e.g. feature disabled, is part of the release) |
| **Minor** | Deviation that does not by itself put a goal at risk (incomplete record, inconsistent ID, missing rationale) | Conditional acceptance with due date |
| **Observation** | Improvement recommendation | No effect |

Recommendation values: **Accept**; **Conditional accept** (conditions and due dates listed); **Reject**.

## 6. Assessment record — Not yet executed

| Field | Value |
|---|---|
| Assessment ID (CSA-I1 / CSA-F) | Not yet executed |
| Release / baseline assessed | Not yet executed |
| Dates, method (desk review, interviews, witness) | Not yet executed |
| Work products and versions assessed | Not yet executed |
| Sampling performed (CSR IDs per CAL) | Not yet executed |
| Deviations from the plan | Not yet executed |

## 7. Findings — Not yet executed

| Finding ID | Step (A2…A8) | Category | Work product / evidence | Finding | Required action | Due | Status |
|---|---|---|---|---|---|---|---|
| — | — | — | — | Not yet executed | — | — | — |

## 8. Assessment of tailoring, claims and known defeaters — Not yet executed

| Item | Assessor judgement | Reference |
|---|---|---|
| CT-1…CT-4, T-11 | Not yet executed | WP-M-09 §4 |
| CSC-01…CSC-05 | Not yet executed | WP-C-10 §5 |
| CAL proposals for CSG-01…CSG-08 | Not yet executed | WP-C-10 §4 |
| CDF-01…CDF-10 | Not yet executed | WP-K-03 §6 |
| Residual risks RR-01…RR-05 | Not yet executed | WP-K-03 §5 |

## 9. Recommendation — Not yet executed

| Field | Value |
|---|---|
| Recommendation (Accept / Conditional accept / Reject) | Not yet executed |
| Conditions and due dates | Not yet executed |
| Statement on release for post-development | Not yet executed |
| Assessor signature and date | Not yet executed |
| Acknowledgement by cybersecurity manager | Not yet executed |

## Open items

| ID | Item |
|---|---|
| OI-1 | Engage an independent cybersecurity assessor (WP-M-09 OI-6) and agree this plan |
| OI-2 | Decide whether CSA-I1 is combined with the G1 functional safety confirmation review (same assessor) |
| OI-3 | Define the CAL-weighted sampling rule (number of CAL 2/CAL 1 CSRs sampled) with the assessor |
| OI-4 | Create `10-safety-case/confirmation/` storage for interim assessment records (shared with WP-K-04) |
