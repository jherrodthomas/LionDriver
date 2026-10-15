# ARA-26262-2018-001 ISO 26262 documentary audit package

| Field | Value |
|---|---|
| Record | ARA-26262-2018-001; supporting assessment aid, not a new registered work product |
| Standard scope | ISO 26262:2018, Parts 1–12; authoritative requirement inventory pending |
| Revision | 0.1 |
| Status | Draft — submitted for human verification; no approval recorded |
| Author / documentary assessor | Codex (OpenAI AI assistant), I0 AI-assisted documentary assessor |
| Qualified independent third-party assessor | Not appointed by this record; competence and organizational independence are not established for an AI assistant |
| Reviewer(s) | TBD, human reviewer other than the artifact author; required independence to be confirmed by the safety manager |
| Approver | Project maintainer / acting safety manager; pending verification and approval |
| Subject baseline | LionDriver `20569e916c9359243739b71e4dc79876aec48cc0`; pinned submodules in `manifest.json` |
| Date | 2026-10-14 |
| Classification | CT-6; conservatively SR-A assurance content, with SR-T generated-view tooling |
| Review record | [RR-2026-010](../../01-management/reviews/RR-2026-010.md) — I0 pre-review input |
| Change record | [Impact analysis](../../07-supporting/impact/change-2026-10-14-iso26262-documentary-audit.md) |
| Document-control rules | [WP-P-01](../../07-supporting/WP-P-01-configuration-management-plan.md), [WP-P-02](../../07-supporting/WP-P-02-change-management.md), [WP-P-04](../../07-supporting/WP-P-04-documentation-management.md), [WP-P-05](../../07-supporting/WP-P-05-verification-review-procedure.md) |

## 1. Purpose and assessment authority

This package gives work-product authors a source-linked audit ledger, spreadsheet and diagrams for reviewing LionDriver's assurance documents. The documentary review covers the existing 88 registered work products, with targeted substantive examination of 21 key documents. The report distinguishes this examination from inventory-level review.

Codex prepared this package as an AI-assisted documentary assessor at the user's request. It is separate from authorship of the original assurance work products, but it is **not a qualified organizationally independent I3 assessor**. Under [WP-M-02 §3.3](../../01-management/WP-M-02-safety-plan.md#33-ai-assisted-authoring) and [WP-M-01 T-09](../../01-management/WP-M-01-assurance-strategy.md#5-tailoring), AI audits have I0 status. Preparing this package does not fill the human assessor role, perform a confirmation measure, accept evidence, close a gate or authorize release.

The project record does not demonstrate ISO 26262 compliance or support a release claim. This does not mean every requirement is violated. The 51 clause buckets are **project references**, not a complete authoritative standard inventory. All normative verdicts remain unassessed. The user has a licensed source, but supplied a Windows-local search link inaccessible to the review environment. No copyrighted standard text is included.

## 2. Controlled source and generated views

| Artifact | Control and purpose |
|---|---|
| [findings.csv](findings.csv) | Controlled author-action ledger: 22 findings, priorities, evidence locations, responsible roles and closure criteria |
| [clause-map.csv](clause-map.csv) | Controlled source associations: 368 document-to-reference links; authority and completeness are unverified |
| [audit_data.json](audit_data.json) | Frozen inventory, finding details, source hashes, trace records and assessed-baseline metadata; must agree with the CSV views |
| [checks.json](checks.json), [logs](logs/) | Exact commands and raw results of six checks run on the assessed baseline; local execution, not accepted safety evidence |
| [engine_review.json](engine_review.json), [synthetic run](engine_synthetic_report.json) | Four diagnostic probes and fictional-standard smoke output for compliance-checker-algo; not an ISO compliance result |
| [licensed_clause_inventory.csv](licensed_clause_inventory.csv) | Empty intake template; complete clause/table/annex and requirement-level review awaits source access |
| [Audit report](Audit_report.md) | Generated narrative view of the documentary assessment and its limitations |
| [Audit workbook](LionDriver_ISO26262_Audit.xlsx) | Generated 16-sheet author review view; Excel edits are not controlled source changes |
| [Review board](Review_board.html) | Generated offline HTML view with five embedded diagrams and searchable findings; GitHub may download rather than render it |
| [manifest.json](manifest.json) | SHA-256 binding of source work products and package artifacts; immutable subject revision and submodule gitlinks |
| [build_audit.py](build_audit.py), [regenerate.sh](regenerate.sh), [requirements](requirements.lock.txt) | Rendering source, archived-subject reproduction instructions and assessor-only dependency pins |

Diagram views: [evidence maturity](01_evidence_ladder.svg), [argument dependencies](02_argument_dependencies.svg), [all-parts coverage boundaries](03_parts_coverage.svg), [finding closure](04_closure_workflow.svg), [checker authority boundary](05_checker_boundary.svg). SVG sources are committed as text under the repository's existing assurance artwork rule; PNG exports are unnecessary duplicate views.

The CSV and JSON records form one controlled revision. A disposition change must update both representations and the report/workbook in a reviewed PR. Do not treat an edited Excel cell as approval. The renderer intentionally reconstructs this frozen assessment from the original subject revision; it does not silently audit the publication branch or accept new dispositions. A new baseline, licensed requirement inventory, or reviewer disposition needs an explicit new package revision and corresponding renderer/input update.

## 3. Reproduction and verification

From the repository root, with `uv` available:

```sh
bash assurance/00-assessment/iso26262-2018/regenerate.sh
python3 assurance/00-assessment/iso26262-2018/verify_package.py
```

The script extracts only `assurance/` from the exact assessed Git revision into a temporary directory, creates an assessor-only virtual environment, and generates a candidate package there. It preserves the working checkout. Dependencies have version pins; no application dependency declaration or lockfile is changed. The frozen command logs are preserved as historical results rather than relabeled as newly executed tests. Review and copy generated views deliberately when revising the controlled package.

The verifier checks source hashes against Git objects at the assessed revision, the CSV/JSON correspondence, counts, unapplied normative verdicts and package hashes. This is a consistency check, not tool qualification or independent acceptance. The compliance checker is advisory: documented diagnostic probes showed unqualified clause IDs, negated method statements and missing method tables can produce misleading 100% scores. No engine grade is used as an ISO verdict.

## 4. Review, approval and distribution

Changes follow WP-P-02 and the PR verification route of WP-P-05. The approval fields remain pending. No claim/evidence acceptance or review entry is added to `assurance/case/`, and this package is not stored in the human confirmation-record folder.

The Git source revision, file hashes and revision history identify the controlled master. Public XLSX, HTML, SVG and report downloads are **uncontrolled generated copies**. They are not controlled recipient copies under [WP-P-04 §9.1](../../07-supporting/WP-P-04-documentation-management.md#91-distribution-of-the-safety-case). GitHub storage and this PR do not by themselves establish QMS certification, compliance, approval or a new gate baseline.

## 5. Open items

| ID | Item | Responsible role | Closure condition |
|---|---|---|---|
| OI-1 | Make the licensed 2018 source accessible and reconcile every requirement, table, annex and ASIL-dependent condition | Standards custodian / qualified assessor | Verified complete inventory with page provenance and applicability decisions |
| OI-2 | Verify the documentary findings and their current relevance at an explicitly selected subject baseline | Independent human reviewer / safety manager | Signed disposition with competence and independence recorded |
| OI-3 | Appoint a qualified human third-party assessor if I2/I3 confirmation or FSA credit is sought | Safety manager | Named assessor, agreed scope, competence and written independence declaration |
| OI-4 | Review the custom rendering/checking tools for their intended use before crediting them as safety assessment tools | Tool qualification owner | Applicable WP-P-07 classification and error-detection/qualification evidence |

## 6. Revision history

| Revision | Date | Change request | Summary | Approval |
|---|---|---|---|---|
| 0.1 | 2026-10-14 | `codex/controlled-iso26262-audit` PR | Initial baseline-bound documentary assessment aid; CSV/JSON source, workbook, diagrams, checks and I0 attribution | Pending; no approval or baselining recorded |
