# WP-P-03 Problem Resolution Management

| Field | Value |
|---|---|
| Work product | WP-P-03 Problem resolution management |
| Standard reference | ISO 26262-2:2018 §5 (anomaly and problem handling in the safety culture and QM), §7 (field monitoring interface); ISO 21448:2022 §13; ISO/SAE 21434:2021 §8 (vulnerability analysis and management); ASPICE 4.0 SUP.9 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (FuSa, SOTIF, CS, quality) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Defines how LionDriver records, classifies, analyses, resolves, verifies and closes problems found in development, verification, vehicle testing and the field. It covers SUP.9 (currently CL0, [gap assessment §7](../00-assessment/gap-assessment.md#7-aspice-capability-baseline-estimated)) and closes the intake part of GAP-28.

Interfaces: field data comes from [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md); vulnerabilities are handled in [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) and enter this process for tracking and resolution; resolutions are implemented as changes under [WP-P-02](WP-P-02-change-management.md).

## 2. Current state

| Item | Observation | Evidence |
|---|---|---|
| Issue templates | `bug_report.yml` and `pc_bug_report.yml` are upstream templates. `bug_report.yml` says "We cannot look into bug reports from forks" and asks for a route on `useradmin.comma.ai` | `.github/ISSUE_TEMPLATE/bug_report.yml` |
| Contact links | Blank issues disabled; links point to `commaai/opendbc` issues, comma Discord and the comma wiki | `.github/ISSUE_TEMPLATE/config.yml` |
| Security contact | `adeeb@comma.ai` and `security@comma.ai` | `SECURITY.md` |
| Stale automation | Issues not touched by `stale.yaml` (`days-before-issue-stale: -1`), PRs are | `.github/workflows/stale.yaml` |

No LionDriver problem record exists yet.

## 3. Intake

### 3.1 Sources

| Source | Channel |
|---|---|
| Developer / CI finding | GitHub issue (template "Problem report") |
| Verification and review finding | Issue linked from the review record ([WP-P-05](WP-P-05-verification-review-procedure.md)) |
| Vehicle test (safety driver) | Issue from test log per [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md), with drive log reference |
| Field report (users, once released) | Issue template "Field report", plus [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) intake |
| Vulnerability report | Private channel per proposed LionDriver `SECURITY.md` (GitHub private vulnerability reporting); mirrored as a private security advisory, not a public issue, until disclosure ([WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)) |
| Upstream (comma) fix or advisory | Issue with label `upstream`, assessed for the frozen baseline |

### 3.2 Proposed issue templates

**Implemented 2026-10-10 (CR-CI-07, D-03):** `.github/ISSUE_TEMPLATE/problem_report.yml`, `field_report.yml` and `config.yml` replace comma's templates. The field list below is the design they implement. Originally proposed to replace `.github/ISSUE_TEMPLATE/bug_report.yml` and `config.yml` through CR-CI-07 in [WP-P-02 §10](WP-P-02-change-management.md#10-proposed-change-requests-for-fork-ci-d-03). Content below is a field list for a GitHub issue form (YAML), shown in condensed form.

```yaml
name: Problem report
description: Malfunction, unexpected behaviour or defect in LionDriver
labels: ["problem", "triage"]
body:
  - type: checkboxes        # safety triage, shown first
    id: safety
    attributes:
      label: Safety triage
      options:
        - label: Unintended or excessive steering, acceleration or braking occurred
        - label: The system did not release control when expected (brake, cancel, override)
        - label: A warning, alert or driver-monitoring escalation was missing or late
        - label: Someone was hurt or property was damaged   # -> also follow WP-O-04 crash procedure
  - type: dropdown
    id: config
    attributes:
      label: Configuration
      options: ["Reference config (2020 Corolla LE TSS2)", "Other vehicle (out of scope)", "PC / simulator"]
  - type: input            # LionDriver version (ld-vX.Y.Z) or commit SHA
  - type: input            # device hardware revision, panda firmware version string
  - type: textarea         # what happened, expected behaviour, steps to reproduce
  - type: input            # drive log / route reference (LionDriver-controlled storage)
  - type: dropdown         # driving mode: lateral only / openpilot long / Experimental Mode
  # SOTIF triggering-condition fields
  - type: dropdown         # road type: highway / arterial / urban / parking / other
  - type: dropdown         # lighting: day / dusk-dawn / night lit / night unlit / low sun glare
  - type: dropdown         # weather: clear / rain / snow / fog / wet road
  - type: textarea         # lane markings, road geometry (curve, merge, split, construction)
  - type: textarea         # other road users / objects involved (lead vehicle, cut-in, VRU, stationary)
  - type: input            # speed at onset (km/h or mph)
  - type: dropdown         # driver state: hands on / hands off / attentive / looking away
  - type: dropdown         # how it ended: driver override / system disengage / alert / no action needed
```

A second template, "Field report", carries the same fields plus incident date and location region. `config.yml` contact links are replaced by LionDriver links; the comma links are removed.

### 3.3 Triage time

| Triage result | Time to first triage |
|---|---|
| Any safety triage box ticked | 1 working day |
| Other | 10 working days |

## 4. Classification

### 4.1 Category

| Category | Label | Criterion | Linked artefacts |
|---|---|---|---|
| FuSa | `cat-fusa` | E/E malfunction or systematic fault (incl. in the envelope) that can violate a safety goal | SG-, TSR-, SWSR-, HWSR- |
| SOTIF | `cat-sotif` | Hazardous behaviour without malfunction: functional insufficiency or foreseeable misuse | SH-, TC-, FI-, ODD element |
| Cybersecurity | `cat-cs` | Weakness or vulnerability; handled with WP-O-05 | TS-, CSG-, CSR- |
| AI | `cat-ai` | Model output error (sub-case of SOTIF, tracked for [WP-W-10](../05-software/WP-W-10-ml-engineering.md)) | FI-, model oid |
| Quality | `cat-quality` | Defect with no safety, SOTIF or CS effect | — |
| Process | `cat-process` | Process non-conformance (missing review, missing impact analysis) | WP-M-05 QA |

A problem may carry more than one category. The highest-severity category drives the timeline.

### 4.2 Severity

| Severity | Label | Definition | Containment target |
|---|---|---|---|
| S-1 Critical | `sev-1` | Potential or actual safety goal violation, or exploitable CS weakness enabling safety impact | Same day: stop vehicle testing on affected configuration; field notification decision per [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |
| S-2 High | `sev-2` | Safety mechanism degraded but another measure still prevents harm; triggering condition that leads to hazardous behaviour within the ODD | 5 working days |
| S-3 Medium | `sev-3` | Safety-relevant defect with no current hazardous path, or verification evidence defect | Next MINOR release |
| S-4 Low | `sev-4` | Quality defect | Backlog |

For CS, the CVSS score or the TARA risk value from [WP-C-09](../02-concept/WP-C-09-tara.md) is also recorded; mapping to S-1..S-4 is in WP-O-05.

## 5. Workflow

| State (label) | Activity | Exit criterion | Who |
|---|---|---|---|
| `triage` | Check completeness, reproduce if possible, assign category and severity, decide containment | Labels set; owner assigned | Maintainer / safety reviewer |
| `analysis` | Root cause analysis (5-why, fault tree, log replay, process replay); identify affected baselines and configurations; check hazard log for missing hazard or TC | Root cause and affected items recorded | Owner |
| `resolution` | Define fix as a change (WP-P-02); for SOTIF: functional modification, ODD restriction or user information; for S-1/S-2 decide on field action | Linked PR(s) | Owner |
| `verification` | Show the fix removes the problem (regression test that fails before and passes after, tagged with requirement ID per [WP-P-06](WP-P-06-requirements-management-traceability.md)) and has no side effects | Verification evidence linked | Verifier (not the fixer for S-1/S-2) |
| `closed` | Close with `state_reason: completed` or `not_planned` + reason | Closure checklist (§6) done | Maintainer |

Problems are never deleted. Duplicates are closed with a link to the surviving issue.

## 6. Closure checklist

```markdown
- [ ] Root cause stated (or "not reproducible" with evidence of attempts)
- [ ] Category and severity final
- [ ] Fix PR(s) merged, or decision not to fix with rationale and residual risk accepted by safety manager
- [ ] Regression test added and tagged (@req ...) or reason none is possible
- [ ] Hazard log / HARA / SOTIF / TARA updated, or "no change" with reason
- [ ] Affected releases listed; field action decided (S-1/S-2)
- [ ] Similar code / other configurations checked (generalisation)
- [ ] Upstream informed if the defect is inherited (optional, per WP-M-11)
```

## 7. Escalation

| Condition | Escalate to | Action |
|---|---|---|
| S-1 | Safety manager immediately; external assessor informed at next contact | Stop vehicle testing on affected baseline; consider withdrawal of release ([WP-P-10 §8](WP-P-10-release-management.md)) |
| S-2 open beyond target | Safety manager | Recorded in [WP-M-07](../01-management/WP-M-07-risk-management.md) |
| Open S-1/S-2 at a gate | Gate review | Gate cannot pass unless the residual risk is explicitly accepted |

## 8. Trend analysis

| Measure | Frequency | Use |
|---|---|---|
| Open problems by category and severity | Monthly | Status report |
| Problems per component (path prefix) | Per gate | Identify weak areas; input to review focus |
| Recurrence (same root cause class) | Per gate | Process improvement through [WP-M-05](../01-management/WP-M-05-quality-assurance-plan.md) |
| SOTIF triggering conditions frequency (from §3.2 fields) | Per gate and per release | Input to [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) and [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md): new TCs become known scenarios |
| Disengagement / override reports from field | Per release | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |
| Time to triage / to close | Monthly | Process metric |

Trend data is generated from issue labels with the GitHub API; the script and its output are stored with the gate record (OI-3).

## 9. Records

The issue (with labels, comments, linked PRs) is the problem record. At each baseline the open and closed problem list is exported (JSON from the GitHub API) into the evidence package ([WP-P-04 §8](WP-P-04-documentation-management.md)) so that the record does not depend on GitHub availability.

## 10. Open items

| ID | Item |
|---|---|
| OI-1 | Create the label set (`problem`, `triage`, `cat-*`, `sev-*`, `upstream`, `ccb-decision`) |
| OI-2 | Raise CR-CI-07 to replace issue templates and `config.yml`; write LionDriver `SECURITY.md` and enable GitHub private vulnerability reporting |
| OI-3 | Write the issue export and trend script |
| OI-4 | Decide where drive logs referenced by problem reports are stored (LionDriver-controlled, privacy reviewed); comma routes on `useradmin.comma.ai` are not under LionDriver control |
| OI-5 | Define the field-report path for users once a release exists (depends on WP-O-04) |
