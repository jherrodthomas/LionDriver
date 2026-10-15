# LionDriver ISO 26262:2018 documentary audit

| Field | Value |
|---|---|
| Record | ARA-26262-2018-001 (supporting assessment aid) |
| Revision | 0.2 |
| Status | Draft — awaiting human verification |
| Author / documentary assessor | Codex (OpenAI AI assistant), I0 |
| Qualified independent assessor | Not appointed by this record |
| Approver | Project maintainer / safety manager; approval pending |
| Distribution | Uncontrolled generated public view |
| Document control | Package README, findings.csv, clause-map.csv, audit_data.json and manifest.json |

Assessment subject: `20569e916c9359243739b71e4dc79876aec48cc0` (`liondriver-dev` checkout). User-requested scope: all 12 parts, ISO 26262:2018. Artifacts are outside the subject checkout; no source, work-product or acceptance records were changed.

## Overall judgment

The documentary record does **not demonstrate ISO 26262 compliance or support a release claim**. This is not a finding that every clause is violated. The available record contains substantive drafts and reproducible consistency tools, but the central configuration, assumptions, quantitative hardware evidence, end-to-end timing, interference argument and independent confirmation remain unresolved.

**Every-clause completeness is pending**: the user confirms a licensed source exists, but the supplied Windows search link is not accessible from this cloud machine and no standards source has been accessed during this pass. The workbook contains 51 project-referenced clause buckets and 368 source associations. These are not the total standard requirements. No compliance percentage is calculated and no normative verdict is set to compliant, non-compliant or N/A.

## What was examined

All 88 work-product files were inventoried for headers, declared references and open items. The register was reconciled to 88 rows. Explicit ISO references were extracted across 185 assurance Markdown files. 21 key work products received targeted substantive examination, alongside current case records, selected pre-review records, the decision register and trace records. Remaining documents have inventory-level review; the workbook makes this distinction explicit. This was not an exhaustive sentence-level or requirement-level audit.

The case records report 36 claims, 0 accepted claims, 50 evidence items (35 partial, 15 missing, 0 accepted), and 41 open defeaters. These values are project-declared, checker-validated status, not new acceptance decisions.

## Priority judgment

The chain of dependencies matters more than the number of documents. An unfrozen device/ECU configuration prevents evidence binding. Unverified OEM assumptions can increase the required ASIL. The resulting integrity demand drives hardware metrics, FFI, software scope and independence. A lower target chosen before the assumptions are validated can make later apparently passing results irrelevant. HIL deferral and no-assessor decisions are incompatible with closure under the project's current gate plan; retain open status or formally re-plan.

The explicit timing issues need resolution before approval: the 1.26 s EPS-warning analysis exceeds the 1 s budget; the curve-bound estimate is about 0.7 s before departure; PCS forwarding-loss timing has zero margin. These are documentary analyses and discrepancies, not witnessed hardware measurements. Planned hardware-measure results and generic failure rates must never be presented as demonstrated metrics. WP-H-03 explicitly says its generic estimates are not compliance evidence.

## Findings and author actions

### A01 · P0 · Authoritative clause universe is not yet accessible

Repository cross-references cannot establish that every requirement, table and annex is covered. User confirms licensed 2018 source exists; the supplied Windows search link is not accessible from this cloud machine.

Source: [WP-M-14:546](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-14-iso26262-6-implementation-specification.md#L546).

Action (Assessor + standards custodian; Before normative verdicts): Obtain all 12 parts; build a verified requirement-level inventory with page provenance, normative/informative classification and ASIL applicability.

Closure: Source verified, all inventory entries counted, and independent coverage reconciliation completed.

### A02 · P0 · The current staffing decision blocks the planned governance gate

The safety plan explicitly says the no-assessor decision prevents G0 under its existing CR-01/CR-03 plan. AI review cannot silently satisfy that requirement.

Source: [WP-M-02:275](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-02-safety-plan.md#L275).

Action (Safety manager / project maintainer; G0): Reconcile staffing decision and confirmation plan; appoint qualified reviewers and assessor or formally re-plan without claiming gate completion.

Closure: Named roles, competence/conflict declarations, approved plan and signed confirmation records.

### A03 · P0 · AI-generated review has no independent verification credit under the project rules

This workbook is an assessment aid. The project explicitly assigns AI audits I0; this deliverable cannot be counted as an I1/I3 confirmation or signed FSA.

Source: [WP-M-02:100](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-02-safety-plan.md#L100).

Action (Safety manager; G0–G5): Arrange human review appropriate to the approved ASIL and maintain a separate evidence acceptance trail.

Closure: Qualified reviewer signs baseline-specific findings and disposition; independence is evidenced.

### A04 · P0 · Safety integrity ratings depend on unverified OEM/driver assumptions

The HARA explicitly increases the steering case from C to D if credited EPS assumptions are not verified. Current lower targets cannot be treated as established.

Source: [WP-C-03:154](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/02-concept/WP-C-03-hara.md#L154).

Action (HARA owner / vehicle test lead; G1): Verify assumptions per exact ECU/configuration; challenge S/E/C rationale and document both credited and failed-assumption variants.

Closure: Approved HARA, witnessed characterization records, configuration binding and independent confirmation.

### A05 · P0 · Reduced-authority strategy is a recommendation rather than an approved safety basis

Option (c) requires measured controllability and speed-dependent limits before re-rating; ASIL reduction and decomposition are different arguments.

Source: [WP-C-04:61](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/02-concept/WP-C-04-functional-safety-concept.md#L61).

Action (Safety manager / HARA owner; G1–G2): Record the strategy decision, validate limits and re-rate only after justified controllability; preserve original integrity demands until then.

Closure: Signed strategy plus validated limit data, revised allocations and confirmed HARA.

### A06 · P0 · Assessment configuration is not fully identified

VIN, ECU firmware, device revision and harness identity are still open items. A generation-level vehicle label is insufficient to bind physical evidence.

Source: [WP-C-01:218](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/02-concept/WP-C-01-item-definition.md#L218).

Action (Configuration manager / maintainer; G1): Freeze an assessed configuration including hardware serial/revision, ECU firmware, software/submodules, models and calibration.

Closure: Complete configuration record and matching manifests for every cited result.

### A07 · P0 · Part-specific hardware metrics are not demonstrated

WP-H-04 lacks BOM-based calculation; WP-H-03 has generic estimates, not part-specific compliance evidence. Generic results cannot close the metric obligation.

Source: [WP-H-04:104](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/04-hardware/WP-H-04-hardware-metrics.md#L104).

Action (Hardware safety lead; G3): Acquire BOM/mission profile/failure-rate evidence, validate fault classes and diagnostic coverage, compute per-goal metrics and sensitivity.

Closure: Reviewed FMEDA and reproducible part-specific SPFM/LFM/PMHF with traceable inputs and valid targets.

### A08 · P1 · Generic FMEDA values must remain separated from demonstrated metrics

Generic SG-01 SPFM 96.9% and SG-07 86.8% miss the document targets; improved planned-measure values assume implementation and coverage. These are planning warnings, not verified pass/fail results.

Source: [WP-H-03:260](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md#L260).

Action (Hardware safety lead; G2–G3): Label estimates, planned architecture and measured results separately; reconcile WP-H-03 with WP-H-04/05 and confirm target authority.

Closure: One configuration-consistent calculation set; planned mechanisms excluded until coverage is substantiated.

### A09 · P0 · Documented warning latency exceeds the stated warning budget

The document records up to 1.26 s against SG-02 1 s; starting the clock after 1 s persistence can conceal end-to-end delay. This is a documented requirement discrepancy, not a new hardware measurement.

Source: [WP-S-04:267](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/03-system/WP-S-04-timing-ftti-budget.md#L267).

Action (Safety manager / system lead; G2): Resolve the requirement/detection-time definition and measure fault onset through actuation removal and audible warning under worst-case load.

Closure: Approved consistent timing budget and witnessed end-to-end traces including tolerance and jitter.

### A10 · P0 · Curve-bound time to departure is shorter than assumed driver reaction

The repository estimates roughly 0.7 s at the ODD bound and itself requests a controllability re-rating or tighter ODD. Driver supervision is not an automatic mitigation.

Source: [WP-S-04:86](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/03-system/WP-S-04-timing-ftti-budget.md#L86).

Action (HARA owner / dynamics lead; G2): Validate dynamics at the boundary; revise ODD, authority or hazard controllability and flow changes through FSC/TSRs.

Closure: Measured validated model, updated ODD and accepted HARA/FTTI rationale.

### A11 · P0 · Stock PCS forwarding-loss budget has zero timing margin

The stated sum of detection and reaction equals FTTI before measured PCS timing. A watchdog nominal setting is insufficient to prove the end-to-end budget.

Source: [WP-S-04:264](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/03-system/WP-S-04-timing-ftti-budget.md#L264).

Action (System / hardware test lead; G2–G4): Measure forwarding-loss response and PCS effects; include oscillator tolerance, scheduling, bus delay and safe-state behavior.

Closure: Worst-case FDTI+FRTI substantiated with positive justified margin or an explicitly accepted alternative safety argument.

### A12 · P0 · Freedom from interference is not established

The current verdicts include not shown and partially shown; the envelope-only ASIL allocation depends on resolving spatial, timing, communication and boot interference.

Source: [WP-A-02:164](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/08-analyses/WP-A-02-coexistence-freedom-from-interference.md#L164).

Action (Software architect / safety analyst; G2): Reconcile analysis to current pins, bound QM-triggered paths, document separation properties and verify adverse inputs and boot integrity.

Closure: Reviewed FFI/DFA with traceable evidence for every interference channel and justified ASIL allocation.

### A13 · P0 · The controlled Part 6 lifecycle has not been activated

The specification explicitly says entry prerequisites are draft/unapproved and Part 6 stays deferred. Existing code and host tests do not establish lifecycle completion.

Source: [WP-M-14:148](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-14-iso26262-6-implementation-specification.md#L148).

Action (Safety manager / software lead; G2): Close E-01…E-15 prerequisites and record the authorized lifecycle baseline and activation decision.

Closure: Approved entry checklist, input baselines, confirmation records and activation decision.

### A14 · P0 · HIL deferral prevents the stated verification closure

The safety plan records deferred HIL and says early-implementation credit cannot be earned until its conditions are met. Plans and host unit tests cannot replace target timing/fault-injection evidence.

Source: [WP-M-02:280](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-02-safety-plan.md#L280).

Action (Test lead / maintainer; G2–G4): Resource a controlled target bench and execute baseline-bound campaigns; if deferred, keep associated gate claims explicitly open.

Closure: Target test logs, environment/calibration records, anomaly disposition and independent review.

### A15 · P1 · Tool self-tests and classification do not complete qualification

In-house safety-relevant tools have open TQR records and review work; compiler/runner pinning is also open. Agreement between tools sharing assumptions does not authenticate the standard.

Source: [WP-P-07:146](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/07-supporting/WP-P-07-tool-classification-qualification.md#L146).

Action (Tool qualification owner; G3): Complete TI/TD/TCL decisions and applicable qualification records; test error detection against independently sourced criteria and pin the toolchain.

Closure: Reviewed use-case-specific tool qualification, known limitations, detection evidence and immutable versions.

### A16 · P1 · Reuse/qualification conclusions remain unconfirmed

The work product requests review of RA-01…RA-09 and records for remaining safety-relevant components; initialized submodules establish access, not qualification.

Source: [WP-P-08:91](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/07-supporting/WP-P-08-software-component-qualification.md#L91).

Action (Software lead / supplier manager; G3): Review component use cases, interfaces, failure modes and configuration; close reuse assessments and safety component evidence needs.

Closure: Reviewed SCQ/RA records and traceable component qualification evidence for the actual use.

### A17 · P1 · Confirmation-measure coverage and independence still require source verification

The plan itself questions whether several rows are required in the licensed edition. Planned I3 rigor does not validate the underlying table transcription.

Source: [WP-M-06:54](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-06-confirmation-measures-plan.md#L54).

Action (Assessor / safety manager; G0–G1): Verify every measure, applicable ASIL and independence requirement directly against Part 2; reconcile the CR list and schedule.

Closure: Source/page-referenced approved confirmation matrix with signed results at required gates.

### A18 · P2 · Historical baseline statements can be mistaken for current status

WP-M-01 already identifies this as a historical starting point, but its old facts could be read as current status. Current assurance records and safety.yaml differ. This is a clarity observation, not proof of an incorrect historical assessment.

Source: [WP-M-01:31](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-01-assurance-strategy.md#L31).

Action (Configuration manager / document authors; G0–G2): Mark historical observations and reconcile assessment baselines, software pins, current status and impact records without rewriting history.

Closure: Baseline crosswalk plus reviewed current-status statements and supersession links.

### A19 · P1 · Assessment template contains stale status/coordination references

WP-K-04 says the confirmation folder is to be created via OI-6, although the folder exists and WP-M-02 OI-5 reports closure; no FSA is actually executed.

Source: [WP-K-04:17](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/10-safety-case/WP-K-04-functional-safety-assessment.md#L17).

Action (Safety case owner; Before assessment kickoff): Update template coordination links through normal document control, leaving execution/approval fields explicitly unperformed.

Closure: Correct reference and folder state with reviewed revision; no fabricated assessor signature or result.

### A20 · P0 · The current safety case does not support release

The work product explicitly disclaims a release claim; machine-readable records show 0 accepted claims, 0 accepted evidence and 41 open defeaters. Structural validity is not evidence sufficiency.

Source: [WP-K-01:8](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/10-safety-case/WP-K-01-safety-case.md#L8).

Action (Safety case owner / safety manager; G5): Close safety-critical defeaters with configuration-bound evidence; obtain applicable verification, confirmation and assessment before release.

Closure: Accepted claim/evidence chains, dispositioned defeaters, FSA and signed release record.

### A21 · P1 · Retrofit tailoring must cover residual production/supplier responsibilities

The strategy tails production to installation and distributed development to upstream reuse. These are proposed project arguments; supplier responsibilities and applicable obligations need source-based review.

Source: [WP-M-01:132](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/01-management/WP-M-01-assurance-strategy.md#L132).

Action (Supplier manager / operations lead; G0–G5): Map each applicable Part 7/8 requirement to installer, upstream supplier or LionDriver; justify retained/allocated/tailored obligations.

Closure: Approved obligation allocation, installation/process evidence and residual-risk disposition.

### A22 · P2 · Proven-in-use non-use is a declared strategy, not a blanket compliance failure

The project deliberately makes no proven-in-use claim. Likewise, ASIL decomposition is not automatically mandatory. Requirement applicability needs an approved rationale.

Source: [WP-P-09:17](https://github.com/jherrodthomas/LionDriver/blob/20569e916c9359243739b71e4dc79876aec48cc0/assurance/07-supporting/WP-P-09-proven-in-use.md#L17).

Action (Safety manager / assessor; G1–G3): Keep the alternative routes visible and justify non-use; do not count an unused route as complied with or mark it failed solely because no artifact exists.

Closure: Source-verified applicability/tailoring decisions and no contradictory reuse/decomposition claims.

## Review of compliance-checker-algo

The user-supplied repository was inspected read-only at `80547e3e544eb3727489093f752f95875c8ea091`. It contains fictional example standards only; it does not supply the licensed ISO 26262 source. Its standard/artifact normalization and candidate matching may help navigation, but its automatic compliance labels are not used in this audit.

The synthetic example completed. Four targeted diagnostic probes demonstrated that (E01) one unqualified clause ID can cover two different standard parts; (E02) text explicitly saying MC/DC was not performed scores the method as matched; (E03) no parsed method tables scores 100%; and (E04) a generic aggregate grade of 90 becomes A — Compliant. Static review additionally found that unmapped artifacts become N/A and that a hardcoded confirmation/independence model is presented inside the agnostic engine. Source lines, observed results and controls are in the Engine review sheet and `engine_review.json`.

Use this engine only for candidate cross-references until these behaviors are controlled and its intended safety use is independently validated. Use edition+part+clause+requirement-qualified IDs; preserve negation and unperformed status; distinguish missing parsing from N/A; require source-based applicability and evidence/independence before any normative verdict. The prototype has not been modified.

## Local verification and its limits

Six checks were rerun with exact commands and logs on the assessed checkout. They validate record consistency, generated views, trace relationships and checker tests. They do not establish semantic correctness of the requirements, validity of all HARA judgments, authoritative ASIL-table accuracy, target timing, hardware fault coverage, supplier evidence, or independence. Skips and advisory state-machine findings remain visible in the raw logs.

| Check | Exit code | Outcome |
|---|---|---|
| case_validation | 0 | OK: assurance case records are valid |
| dashboard_consistency | 0 | OK: dashboard outputs match the records |
| requirements_trace | 0 | OK: all implemented checks passed |
| state_machine_consistency | 0 | OK: state machines consistent |
| trace_tool_tests | 0 | OK (skipped=2) |
| hara_model_tests | 0 | OK |

## Finishing the normative audit

1. Provide the location of the licensed ISO 26262:2018 source for all parts. Read normative requirements, tables, annexes and ASIL-dependent method requirements directly; do not reconstruct them from project citations or memory.
2. Populate the authoritative inventory at requirement granularity, recording edition, part, clause/table/annex, requirement identifier, paraphrase, normative/informative kind, ASIL applicability and source page. Compare the inventory against the standard's own contents and every normative requirement. A clause can contain multiple separately auditable obligations.
3. Determine applicability for the actual Corolla configuration. Vocabulary/guidance and motorcycle adaptations require appropriate treatment; do not blanket-mark them as applicable or non-compliant.
4. Map each applicable obligation to its work products, actual results and acceptance/review records. Assess correctness and sufficiency, not merely existence. Evaluate tailoring and supplier allocations against exact authority.
5. Issue evidence-linked normative findings and have qualified independent reviewers disposition them. Close only when the acceptance criteria and required independence are met.

No work-product status, evidence acceptance, gate record, FSA recommendation or release authorization has been changed by this deliverable.
