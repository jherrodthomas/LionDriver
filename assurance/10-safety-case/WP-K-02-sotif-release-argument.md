# WP-K-02 SOTIF Achievement Evaluation and Release Argument

| Field | Value |
|---|---|
| Work product | WP-K-02 SOTIF achievement evaluation and release recommendation |
| Standard reference | ISO 21448:2022 §12 (evaluation of the achievement of the SOTIF, release); inputs from §6–§11, §13 |
| Version | 0.1 |
| Status | Skeleton — structure, criteria and evidence checklist only. **The evaluation has not been performed.** Results sections are templates marked "Not yet executed" |
| ASIL / scope | SOTIF (G2 of [WP-K-01](WP-K-01-safety-case.md)); AI contribution (G3) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); SOTIF lead; external assessor per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | SOTIF lead and safety manager (joint recommendation); release decision in [WP-K-06](WP-K-06-release-record.md) |
| Baseline | `8b8c6ae` |

## 1. Purpose

This document evaluates, at gate G5, whether the SOTIF of the LD-SDA reference configuration has been achieved, and gives one of three recommendations for the release record ([WP-K-06](WP-K-06-release-record.md)):

| Recommendation | Meaning |
|---|---|
| **Accept** | All criteria in §3 met; residual risk acceptable |
| **Accept with conditions** | Residual risk acceptable only with stated restrictions (ODD limits, feature disabled, user information, field-monitoring obligations) that are part of the release |
| **Reject** | Criteria not met; no release |

It is the detailed form of claim G2 (and the SOTIF-relevant part of G3) in the [safety case](WP-K-01-safety-case.md#42-g2-sotif).

## 2. Argument structure

```text
G2   Hazards from functional insufficiencies and reasonably foreseeable misuse are
     acceptably low for the reference configuration in its ODD.
 ⊙ C  ODD [WP-C-02]; SOTIF hazards SH-01…SH-13 and acceptance criteria AC-01…AC-06
      [WP-C-05]; validation targets [WP-V-02]; release baseline [WP-K-06]
 → S-K2  Argue over the specification, the known area, the unknown area, misuse, AI
         components and operation (21448 §12 evaluation aspects)
     → G2.A  Specification and ODD are complete and consistent with the implemented
             function at the release baseline                         (§3 R-01, R-02)
     → G2.B  Every known triggering condition and functional insufficiency is
             evaluated and treated (accept / modify / restrict / inform)  (R-03…R-05)
     → G2.C  Known hazardous scenarios are verified with acceptable results (R-06)
     → G2.D  Residual risk from unknown hazardous scenarios meets the validation
             targets                                                  (R-07, R-08)
     → G2.E  Foreseeable misuse is addressed to the level the ratings assume (R-09)
     → G2.F  ML components' contribution is bounded and evaluated     (R-10)
     → G2.G  Field monitoring is ready to detect residual insufficiencies after
             release                                                  (R-11)
     → G2.H  No open SOTIF problem of severity S-1/S-2 without accepted rationale (R-12)
```

## 3. Release criteria

| ID | Criterion | Evidence (§4) | Source clause / WP |
|---|---|---|---|
| R-01 | ODD and intended functionality are specified and approved; the release configuration enforces or informs about every ODD boundary | E-01, E-02 | 21448 §5; [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) |
| R-02 | Functions active by default are exactly those evaluated (AC-04: Experimental Mode, debug modes) | E-03 | [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md) AC-04; D-08 |
| R-03 | SOTIF hazards identified and rated; acceptance criteria approved | E-04 | 21448 §6; WP-C-05 |
| R-04 | Triggering conditions and insufficiencies analysed for all SH (AC-01) | E-05 | 21448 §7; [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) |
| R-05 | Functional modifications implemented and verified, or the residual risk accepted with rationale | E-06 | 21448 §8; [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md) |
| R-06 | Known hazardous scenarios evaluated with results within acceptance criteria (AC-02, AC-03, AC-06) | E-07, E-08 | 21448 §10; [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) |
| R-07 | Validation targets derived and justified | E-09 | 21448 §9; [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) |
| R-08 | Unknown-scenario evaluation meets the validation targets with stated confidence; exposure and conditions of the validation driving are representative of the ODD | E-10 | 21448 §11; [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md) |
| R-09 | Misuse analysis complete; DM meets its performance targets (AC-05); user information reviewed and its effectiveness checked | E-11, E-12, E-13 | 21448 §6, Annex B; [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md); [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md) |
| R-10 | ML models identified by hash in the release; model-level evaluation done; model insufficiencies fed into R-04 | E-14, E-15 | PAS 8800; [WP-W-10](../05-software/WP-W-10-ml-engineering.md); [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) |
| R-11 | Field monitoring process, data path and field-action channel in place | E-16 | 21448 §13; [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |
| R-12 | Open SOTIF problems reviewed; none of S-1/S-2 open without accepted rationale | E-17 | [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) |

## 4. Evidence checklist

| E | Evidence | WP | Status at `8b8c6ae` | Status at evaluation |
|---|---|---|---|---|
| E-01 | Approved ODD specification | WP-C-02 | Draft | Not yet executed |
| E-02 | ODD enforcement / information review | WP-C-07, WP-O-03 | Missing | Not yet executed |
| E-03 | Release configuration review (params dump vs. evaluated functions) | WP-K-06, [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-19 | Missing | Not yet executed |
| E-04 | Approved SOTIF hazard identification and acceptance criteria | WP-C-05 | Draft | Not yet executed |
| E-05 | Approved TC/FI analysis | WP-C-06 | Missing | Not yet executed |
| E-06 | Functional modification verification records | WP-C-07, WP-S-09 | Missing | Not yet executed |
| E-07 | Known-scenario evaluation report | WP-V-03 | Missing | Not yet executed |
| E-08 | Stock PCS preservation test report (AC-06) | WP-V-01 | Missing | Not yet executed |
| E-09 | Validation target derivation | WP-V-02 | Missing | Not yet executed |
| E-10 | Unknown-scenario evaluation report (driving log summary, exposure, events) | WP-V-04 | Missing | Not yet executed |
| E-11 | Misuse analysis | WP-C-08 | Missing | Not yet executed |
| E-12 | DM performance test report | WP-V-03 / WP-W-10 | Missing (13 inherited scenario tests only) | Not yet executed |
| E-13 | User information review and comprehension check | WP-O-03 | Draft text | Not yet executed |
| E-14 | Model identity (hashes) in release record | WP-K-06 | Missing | Not yet executed |
| E-15 | Model evaluation report | WP-W-10 | Missing | Not yet executed |
| E-16 | Field monitoring readiness check | WP-O-04 | Draft process; no data path | Not yet executed |
| E-17 | Open problem list (cat-sotif, cat-ai) | WP-P-03 | No LionDriver problems recorded | Not yet executed |

## 5. Evaluation results — Not yet executed

| Criterion | Met / Not met / Met with condition | Rationale | Evaluator |
|---|---|---|---|
| R-01 … R-12 | | | |

### 5.1 Residual risk statement — Not yet executed

Template: "At baseline `<tag>`, the residual risk from SOTIF hazards SH-01…SH-13 in the ODD of WP-C-02 is estimated as `<value / qualitative statement>` against the validation targets `<VT-nn>` with `<confidence>`. Known limitations communicated to users: `<list>`."

### 5.2 Conditions for release — Not yet executed

| # | Condition | Owner | Verification |
|---|---|---|---|

### 5.3 Recommendation — Not yet executed

| Field | Value |
|---|---|
| Recommendation | Accept / Accept with conditions / Reject |
| Release baseline | `ld-vX.Y.Z` |
| SOTIF lead | name, date |
| Safety manager | name, date |

## 6. Known obstacles at this baseline

These are expected to block R-criteria unless closed (see defeaters in [WP-K-01 §7](WP-K-01-safety-case.md#7-defeaters-counter-evidence)): Experimental Mode default (GAP-18, R-02), soft-disable actuation and diagnostic masking (GAP-16, GAP-17, R-05), no fork-owned driving data or replay (GAP-30, R-08), DM validity and bypass (GAP-20, GAP-21, R-09), no model identity check and no training-data ODD (GAP-22, R-10), no LionDriver field data path (R-11).

## 7. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Confirm the evaluation aspects against the licensed text of ISO 21448 §12 and adjust R-01…R-12 | G2 |
| OI-2 | Define the confidence level and statistical method for R-08 in WP-V-02 | G2 |
| OI-3 | Define who may sign the SOTIF recommendation (SOTIF lead role is TBD in WP-M-02) | G1 |
