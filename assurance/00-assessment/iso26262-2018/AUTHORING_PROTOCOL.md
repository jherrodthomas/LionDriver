# AI-authoring protocol — ARA-26262-2018-001 v0.2

| Field | Value |
|---|---|
| Status | Draft authoring aid; human verification and approval pending |
| Author | Codex, OpenAI AI assistant; I0 |
| Subject | `20569e916c9359243739b71e4dc79876aec48cc0` |
| Controlled task source | `author_tasks.json`, linked to the frozen findings and exact-source `annotations.json` |
| Authority | Existing QMS work products and the user's actual task assignment; this queue grants no approval |

## 1. Before editing

Read the assigned task, its finding, its exact source passage and the work product's open items. Read WP-P-02, WP-P-04 and WP-P-05. The annotated view is a read-only overlay, not a proposed replacement text.

Check the work product against the current checkout. Every annotation carries the assessed revision, full source hash and exact line. If the source changed, create a current-version crosswalk and re-evaluate the finding. Never apply an old line number blindly or reset the user's documents to this assessment baseline.

Identify the precise applicable requirement and licensed source page before asserting standard compliance. The current clause inventory is incomplete; no agent may reconstruct it from memory, project citations, synthetic standards or similarity scores. Preparatory documentation can proceed while normative assessment remains blocked.

## 2. Bound the assignment

Work only on the task the user assigned and the explicitly justified cross-document impacts. A task entry is unassigned by default. Dependencies coordinate preparation; they are not proof of completed gates or authority to change unrelated documents. Respect staffing, strategy, ASIL, ODD and hardware decisions reserved to the safety manager or qualified reviewer.

Three different activities must stay separate:

1. **Document correction:** clarify history, fix a stale reference, reconcile IDs or state what evidence is missing.
2. **Evidence production:** execute the actual measurement, analysis or test with correct configuration, tools and raw results. A plan is not its result.
3. **Assessment/acceptance:** evaluate evidence sufficiency and authorize the disposition at the required independence. An authoring AI does not perform this step on its own output.

Do not change a safety limit, timing-clock definition, controllability rating, ASIL target or item boundary to make the spreadsheet appear green. Propose alternatives with their consequences; obtain the required decision and evidence.

## 3. Required output from an author agent

For each assigned task, produce:

- Task and finding IDs; original and current source revisions; verified source/line crosswalk.
- Applicable requirement reference and source page, or an explicit source-access blocker.
- Proposed document changes with before/after rationale and affected work-product/requirement/AoU IDs.
- Evidence actually used or produced: configurations, commands, timestamps, raw records, results, skips and anomalies. Unknown fields remain unknown.
- WP-P-02 impact analysis, revised document-control headers and revision-history entries.
- Verification results and remaining unrun checks, external prerequisites and unresolved decisions.
- A requested human review and closure-evidence checklist. Submission is not closure.

Do not invent VINs, device identities, measurements, tool qualifications, approvals, signatures, source clauses or test results. Do not accept claims/evidence, close defeaters, approve a work product or mark a gate passed through author-side edits. An AI assistant's work remains I0 under WP-M-02 §3.3.

## 4. Visual annotation semantics

Highlighting points to the evidence location. The rounded border groups the passage with its finding, and the circled ID links it to a bounded task. Text labels accompany colors for accessibility and printing. Red means a **documented discrepancy**, not an independently verified ISO nonconformity. Amber means evidence or a decision is needed; purple means source/authority verification; blue means clarification.

The original source is immutable in these views. No strike-through or automatic replacement is applied to a requirement. A future redline must show separately labeled original text and proposed text, with a change rationale and exact version binding, and pass normal document control.

## 5. Closure and revision control

Keep findings open until the task's actual closure evidence and required human review are recorded. AI draft quality or passing consistency checks cannot supply independent confirmation. Changes to task dispositions, source baselines or normative verdicts require a new controlled package revision, synchronized source records and regenerated views.

| Revision | Date | Summary | Approval |
|---|---|---|---|
| 0.2 | 2026-10-14 | Initial bounded AI-author protocol and annotation semantics | Pending |
