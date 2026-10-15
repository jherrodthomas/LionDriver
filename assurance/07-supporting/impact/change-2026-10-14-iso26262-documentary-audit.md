# Change record — ISO 26262 documentary audit package

| Field | Value |
|---|---|
| Record | Change request carried by the `codex/controlled-iso26262-audit` PR |
| Type / classification | CT-6; conservative SR-A assurance content and SR-T generated-view tooling |
| Revision / status | 0.2 / Draft — approval pending |
| Author | Codex (OpenAI AI assistant), I0 |
| Subject baseline | `20569e916c9359243739b71e4dc79876aec48cc0` |
| Package | [ARA-26262-2018-001](../../00-assessment/iso26262-2018/README.md) |
| Review record | [RR-2026-010](../../01-management/reviews/RR-2026-010.md) |
| Required verifier / approver | Human reviewer other than the artifact author; project maintainer / safety manager; required independence to be confirmed |

## 1. Reason and scope

The user requested a GitHub-hosted spreadsheet and diagrams for assessing the assurance documents against ISO 26262:2018, with QMS revision and document control. This change publishes the completed documentary review as a supporting assessment package, not a replacement safety case or a signed functional safety assessment.

The user also requested independent third-party assessor attribution. Codex is identified truthfully as the AI-assisted documentary assessor and artifact author at I0. Organizational independence, human competence and I3 confirmation are not claimed. The existing rules of WP-M-02 §3.3, WP-M-01 T-09 and WP-M-06 remain authoritative.

Revision 0.2 adds a bounded authoring-agent protocol, unassigned task/dependency records and read-only visual markup over the frozen source. Agent instructions apply to future assigned assurance edits; they do not initiate remediation, override human decisions or accept findings. Annotation hashes and exact quotes must match the assessed Git objects; current-version source drift must be evaluated before an author uses the proposed task.

## 2. Impact analysis

| Area | Impact and disposition |
|---|---|
| Software, firmware, models, submodule pins | No behavioral or configuration change; the package cites the existing immutable subject revision |
| Hazards, safety goals, ASIL ratings, AoUs | No definition, rating or allocation changed. Findings identify proposed author actions; those actions require separate controlled changes |
| Requirements and trace data | Existing FSR/TSR/HWSR/SWSR records remain unchanged; exported snapshot is an assessment view |
| Safety case and defeaters | No evidence or claim accepted, defeater closed, gate passed, assessor appointed or release authorized |
| SOTIF / cybersecurity / AI | No normative conclusion issued for these standards. The workbook exposes supporting project records without treating the ISO 26262 audit as their assessment |
| Document/configuration control | Adds one supporting record, a revision history, frozen JSON/CSV source, commit-pinned citations, reproduction tooling, hashes and a review record |
| Tooling | New assessor-only dependencies and scripts; no root dependency or CI configuration changed. Custom tools are unqualified and advisory |
| Standards coverage | Complete normative coverage is blocked on access to the licensed source; 51 referenced buckets are not the official clause universe |
| Existing registered work products | Content and approval states remain unchanged; supporting-package navigation added to the assurance index |
| Public distribution | No standards text, secret, credential value or private vehicle record included; generated public views are uncontrolled copies |

## 3. Verification and approval criteria

Package verification covers source hashes at the subject revision, CSV/JSON agreement, source associations, complete package hashes and generated-workbook counts. Existing assurance checks must pass: links, Markdown tables, trace consistency, case validation and dashboard consistency. The original six execution checks are retained with commands, timestamps and raw logs; they are not relabeled as accepted evidence.

Human verification must confirm the package's evidence interpretation, source authority, applicability treatment, attribution and limitations before approval. A passing generator or CI check is insufficient. Any approved finding disposition or new subject baseline is a revision, never a silent Excel edit.

## 4. Result

Implementation submitted for review. Approval, independent confirmation and normative assessment remain pending.

## 5. Revision history

| Revision | Date | Change request | Summary | Approval |
|---|---|---|---|---|
| 0.1 | 2026-10-14 | `codex/controlled-iso26262-audit` PR | Initial impact analysis for publication of ARA-26262-2018-001 | Pending |
| 0.2 | 2026-10-14 | `codex/controlled-iso26262-audit` PR | Bounded author-agent guidance and exact-source visual annotation views | Pending |
