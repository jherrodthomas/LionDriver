# AI-author update queue — ARA-26262-2018-001 v0.2

Draft / I0 authoring aid. The subject is `20569e916c9359243739b71e4dc79876aec48cc0`. Complete ISO compliance is not assessed.

Read [the authoring protocol](AUTHORING_PROTOCOL.md) before using this queue. Tasks authorize no change by themselves.

| Task | Category | Proposed role | Document | Preparatory dependencies |
|---|---|---|---|---|
| TASK-A01 | Source verification | Assessor + standards custodian | WP-M-14:546 | None; task-specific external prerequisites still apply |
| TASK-A02 | Decision required | Safety manager / project maintainer | WP-M-02:275 | None; task-specific external prerequisites still apply |
| TASK-A03 | Authority boundary | Safety manager | WP-M-02:100 | None; task-specific external prerequisites still apply |
| TASK-A04 | Evidence needed | HARA owner / vehicle test lead | WP-C-03:154 | TASK-A06 |
| TASK-A05 | Decision required | Safety manager / HARA owner | WP-C-04:61 | TASK-A04 |
| TASK-A06 | Evidence needed | Configuration manager / maintainer | WP-C-01:218 | None; task-specific external prerequisites still apply |
| TASK-A07 | Evidence needed | Hardware safety lead | WP-H-04:104 | TASK-A06 |
| TASK-A08 | Evidence needed | Hardware safety lead | WP-H-03:260 | TASK-A07 |
| TASK-A09 | Documented discrepancy | Safety manager / system lead | WP-S-04:267 | None; task-specific external prerequisites still apply |
| TASK-A10 | Documented discrepancy | HARA owner / dynamics lead | WP-S-04:86 | TASK-A04 |
| TASK-A11 | Documented discrepancy | System / hardware test lead | WP-S-04:264 | None; task-specific external prerequisites still apply |
| TASK-A12 | Evidence needed | Software architect / safety analyst | WP-A-02:164 | TASK-A06 |
| TASK-A13 | Decision required | Safety manager / software lead | WP-M-14:148 | TASK-A02, TASK-A05, TASK-A12 |
| TASK-A14 | Evidence needed | Test lead / maintainer | WP-M-02:280 | None; task-specific external prerequisites still apply |
| TASK-A15 | Evidence needed | Tool qualification owner | WP-P-07:146 | None; task-specific external prerequisites still apply |
| TASK-A16 | Evidence needed | Software lead / supplier manager | WP-P-08:91 | TASK-A06 |
| TASK-A17 | Source verification | Assessor / safety manager | WP-M-06:54 | TASK-A01 |
| TASK-A18 | Editorial clarification | Configuration manager / document authors | WP-M-01:31 | None; task-specific external prerequisites still apply |
| TASK-A19 | Editorial clarification | Safety case owner | WP-K-04:17 | None; task-specific external prerequisites still apply |
| TASK-A20 | Evidence needed | Safety case owner / safety manager | WP-K-01:8 | TASK-A04, TASK-A07, TASK-A09, TASK-A12, TASK-A14 |
| TASK-A21 | Decision required | Supplier manager / operations lead | WP-M-01:132 | TASK-A01 |
| TASK-A22 | Source verification | Safety manager / assessor | WP-P-09:17 | TASK-A01 |

## TASK-A01

**Allowed preparation:** Prepare the licensed-source intake and requirement inventory; verify clause/table/annex counts after source access.

**Author action:** Obtain all 12 parts; build a verified requirement-level inventory with page provenance, normative/informative classification and ASIL applicability.

**Closure evidence:** Source verified, all inventory entries counted, and independent coverage reconciliation completed.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A02

**Allowed preparation:** Draft options reconciling staffing and the existing gate plan; retain the gate blocker until the safety manager decides.

**Author action:** Reconcile staffing decision and confirmation plan; appoint qualified reviewers and assessor or formally re-plan without claiming gate completion.

**Closure evidence:** Named roles, competence/conflict declarations, approved plan and signed confirmation records.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A03

**Allowed preparation:** Keep AI-generated findings separate from human verification and confirmation; name actual reviewers only after appointment.

**Author action:** Arrange human review appropriate to the approved ASIL and maintain a separate evidence acceptance trail.

**Closure evidence:** Qualified reviewer signs baseline-specific findings and disposition; independence is evidenced.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A04

**Allowed preparation:** Prepare a configuration-specific AoU verification matrix and failed-assumption ASIL variants; retain provisional ratings.

**Author action:** Verify assumptions per exact ECU/configuration; challenge S/E/C rationale and document both credited and failed-assumption variants.

**Closure evidence:** Approved HARA, witnessed characterization records, configuration binding and independent confirmation.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A05

**Allowed preparation:** Prepare strategy alternatives and their controllability evidence needs; distinguish re-rating from decomposition.

**Author action:** Record the strategy decision, validate limits and re-rate only after justified controllability; preserve original integrity demands until then.

**Closure evidence:** Signed strategy plus validated limit data, revised allocations and confirmed HARA.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A06

**Allowed preparation:** Create an explicit configuration record with unknown fields marked TBD; populate only identities supported by actual records.

**Author action:** Freeze an assessed configuration including hardware serial/revision, ECU firmware, software/submodules, models and calibration.

**Closure evidence:** Complete configuration record and matching manifests for every cited result.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A07

**Allowed preparation:** List BOM, rates, mission profile and diagnostic-coverage inputs needed per safety goal; retain uncomputed result fields.

**Author action:** Acquire BOM/mission profile/failure-rate evidence, validate fault classes and diagnostic coverage, compute per-goal metrics and sensitivity.

**Closure evidence:** Reviewed FMEDA and reproducible part-specific SPFM/LFM/PMHF with traceable inputs and valid targets.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A08

**Allowed preparation:** Reconcile the generic-estimate and part-specific result sections with clear provenance, assumptions and separate status labels.

**Author action:** Label estimates, planned architecture and measured results separately; reconcile WP-H-03 with WP-H-04/05 and confirm target authority.

**Closure evidence:** One configuration-consistent calculation set; planned mechanisms excluded until coverage is substantiated.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A09

**Allowed preparation:** Draft an end-to-end timing discrepancy table and remedy options; include onset, detection, reaction and warning clocks.

**Author action:** Resolve the requirement/detection-time definition and measure fault onset through actuation removal and audible warning under worst-case load.

**Closure evidence:** Approved consistent timing budget and witnessed end-to-end traces including tolerance and jitter.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A10

**Allowed preparation:** Prepare the curve-bound controllability/ODD decision with dynamics validation needs; do not silently tighten the ODD or lower ASIL.

**Author action:** Validate dynamics at the boundary; revise ODD, authority or hazard controllability and flow changes through FSC/TSRs.

**Closure evidence:** Measured validated model, updated ODD and accepted HARA/FTTI rationale.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A11

**Allowed preparation:** Document all terms and tolerances in the forwarding-loss budget and the measurement needed to establish margin.

**Author action:** Measure forwarding-loss response and PCS effects; include oscillator tolerance, scheduling, bus delay and safe-state behavior.

**Closure evidence:** Worst-case FDTI+FRTI substantiated with positive justified margin or an explicitly accepted alternative safety argument.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A12

**Allowed preparation:** Prepare an interference-channel evidence matrix at the actual pins; retain not-shown/partial verdicts until supported.

**Author action:** Reconcile analysis to current pins, bound QM-triggered paths, document separation properties and verify adverse inputs and boot integrity.

**Closure evidence:** Reviewed FFI/DFA with traceable evidence for every interference channel and justified ASIL allocation.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A13

**Allowed preparation:** Prepare the E-01…E-15 entry checklist with links to actual approvals and unresolved prerequisites; do not activate Part 6.

**Author action:** Close E-01…E-15 prerequisites and record the authorized lifecycle baseline and activation decision.

**Closure evidence:** Approved entry checklist, input baselines, confirmation records and activation decision.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A14

**Allowed preparation:** Reconcile HIL deferral with test/gate status and prepare the missing campaign specifications; retain unexecuted results.

**Author action:** Resource a controlled target bench and execute baseline-bound campaigns; if deferred, keep associated gate claims explicitly open.

**Closure evidence:** Target test logs, environment/calibration records, anomaly disposition and independent review.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A15

**Allowed preparation:** Prepare use-case-specific TI/TD/TCL and TQR completion tasks with independent error-detection criteria and version pins.

**Author action:** Complete TI/TD/TCL decisions and applicable qualification records; test error detection against independently sourced criteria and pin the toolchain.

**Closure evidence:** Reviewed use-case-specific tool qualification, known limitations, detection evidence and immutable versions.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A16

**Allowed preparation:** Prepare component-specific reuse/qualification records and trace to their real uses; initialization is not qualification.

**Author action:** Review component use cases, interfaces, failure modes and configuration; close reuse assessments and safety component evidence needs.

**Closure evidence:** Reviewed SCQ/RA records and traceable component qualification evidence for the actual use.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A17

**Allowed preparation:** Prepare the confirmation-measure/source-page comparison matrix; verify the licensed requirements before changing it.

**Author action:** Verify every measure, applicable ASIL and independence requirement directly against Part 2; reconcile the CR list and schedule.

**Closure evidence:** Source/page-referenced approved confirmation matrix with signed results at required gates.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A18

**Allowed preparation:** Make the historical starting-point baseline unmistakable and add current-status cross-references; preserve history.

**Author action:** Mark historical observations and reconcile assessment baselines, software pins, current status and impact records without rewriting history.

**Closure evidence:** Baseline crosswalk plus reviewed current-status statements and supersession links.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A19

**Allowed preparation:** Correct stale folder/coordination references after checking the source baseline; keep the assessment unperformed.

**Author action:** Update template coordination links through normal document control, leaving execution/approval fields explicitly unperformed.

**Closure evidence:** Correct reference and folder state with reviewed revision; no fabricated assessor signature or result.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A20

**Allowed preparation:** Prepare claim-to-evidence-to-defeater closure tasks and missing review links; keep release unsupported.

**Author action:** Close safety-critical defeaters with configuration-bound evidence; obtain applicable verification, confirmation and assessment before release.

**Closure evidence:** Accepted claim/evidence chains, dispositioned defeaters, FSA and signed release record.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A21

**Allowed preparation:** Prepare an obligation/responsibility allocation proposal for retrofit and supplier activities; tailoring needs approval.

**Author action:** Map each applicable Part 7/8 requirement to installer, upstream supplier or LionDriver; justify retained/allocated/tailored obligations.

**Closure evidence:** Approved obligation allocation, installation/process evidence and residual-risk disposition.

**Human control:** Required before closure; I0 drafting is not independent verification

## TASK-A22

**Allowed preparation:** Document why optional assurance routes are not used; require approved applicability before an N/A verdict.

**Author action:** Keep the alternative routes visible and justify non-use; do not count an unused route as complied with or mark it failed solely because no artifact exists.

**Closure evidence:** Source-verified applicability/tailoring decisions and no contradictory reuse/decomposition claims.

**Human control:** Required before closure; I0 drafting is not independent verification
