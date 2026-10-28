# For the assessor

This page is for the person asked to look at LionDriver independently: a confirmation reviewer, a functional
safety auditor or assessor, a SOTIF or AI-safety reviewer, a cybersecurity assessor, or someone deciding whether to
take that role on. It says what state to expect, where the plans are, what you would be asked to do, what to assess
against, how independence is recorded, and how to send findings. Every line points at the record that owns it;
this page decides nothing and claims nothing.

> [!NOTE]
> **No confirmation measure has been performed, and no assessor has been engaged.** The project has one
> maintainer, so every review at independence level I2 or I3 is planned as external. The project lead decided on
> 2026-10-14 not to engage an assessor for now; the decision is recorded as revisitable. See
> [where things stand](#where-things-stand).

## Where things stand

| Fact | Where it is recorded |
|---|---|
| No confirmation review, audit or assessment has taken place | [Confirmation records folder](../assurance/10-safety-case/confirmation/README.md), [WP-M-06 §1](../assurance/01-management/WP-M-06-confirmation-measures-plan.md) |
| No gate review has been held | [Gate records folder](../assurance/10-safety-case/gates/README.md) |
| The assessor role is open; the lead chose "no assessor for now" | [WP-M-01 §8, decision D-06](../assurance/01-management/WP-M-01-assurance-strategy.md#8-strategic-decisions-required); decision register entry DQ-009 in [`register.yaml`](../assurance/01-management/decisions/register.yaml) |
| Every role in the safety plan resolves to the maintainer; roles needing independence are marked TBD | [WP-M-02 §3.1](../assurance/01-management/WP-M-02-safety-plan.md#3-roles-and-responsibilities) |
| Much of the record is AI-assisted drafting, which counts at I0 and gives no review credit | [WP-M-02 §3.3](../assurance/01-management/WP-M-02-safety-plan.md#33-ai-assisted-authoring) |
| Clause citations are marked "check against the licensed copy"; the standards are to be bought when an assessor is engaged | Decision register entry DQ-014 in [`register.yaml`](../assurance/01-management/decisions/register.yaml); [WP-M-06 OI-1](../assurance/01-management/WP-M-06-confirmation-measures-plan.md#11-open-items) |
| No work product is approved or baselined; the status of each is in the register | [WP-M-00 §3](../assurance/01-management/WP-M-00-work-product-register.md#3-register) and its generated status figure |

![Where the record stands on the system V: the system V of ASPICE 4.0, SYS.1 to SYS.3 down the left, the software, hardware and machine-learning arms at the bottom, and the verification levels up to VAL.1 on the right; each box is coloured by the register status of its work products and each verification box gives how many test cases are specified and how many have run; a band below shows the gate records G0 to G6](../assurance/trace/figures/fig-9-system-v-status.svg)

*Figure 9 of the [traceability record](../assurance/trace/README.md), generated from the WP-M-00 register and the test specifications by `trace_figures.py`. Green is kept for approved or baselined work products and passed verification.*

The dashboard on the [Home](Home.md) page shows the same picture in figures. [Reading the Living Safety
Case](Reading-the-Living-Safety-Case.md) explains why zero accepted evidence is the honest number at this stage.

## Read in this order

| Step | Work product | What to take from it |
|---|---|---|
| 1 | [WP-M-01 assurance strategy](../assurance/01-management/WP-M-01-assurance-strategy.md) | The one configuration claims apply to (§3.1), the safety-envelope argument the whole case rests on (§4), the tailoring decisions T-01 to T-13 (§5), the strategic decisions and their status (§8), the top risks (§9) |
| 2 | [WP-M-02 functional safety plan](../assurance/01-management/WP-M-02-safety-plan.md) | Roles and who holds them (§3), the lifecycle phases and gates (§4), the early-implementation rule for at-risk work (§4.1), how the plan tailors the standard (§6) |
| 3 | [WP-M-06 confirmation measures plan](../assurance/01-management/WP-M-06-confirmation-measures-plan.md) | What you would be asked to do (below), the independence scheme (§3), the assessor qualification and independence requirements (§6.1), the records and their location (§10) |
| 4 | [WP-M-00 work product register](../assurance/01-management/WP-M-00-work-product-register.md) | The gates and their exit criteria (§2), every work product with its clause, gate and status (§3) |
| 5 | [WP-K-01 safety case](../assurance/10-safety-case/WP-K-01-safety-case.md) | The argument structure, the assumptions (§5), the evidence status (§6), the defeaters (§7). The GSN diagrams are under [`gsn/`](../assurance/10-safety-case/gsn) and the machine-readable records under [`assurance/case-records/`](../assurance/case-records/README.md) |
| 6 | [WP-K-04 functional safety assessment](../assurance/10-safety-case/WP-K-04-functional-safety-assessment.md) | The assessment plan and the report template you would fill in, including the independence declaration (§2) |
| 7 | [Baseline gap assessment](../assurance/00-assessment/gap-assessment.md) | What the project itself found wanting in the inherited code and process, finding by finding |

[Standards at a glance](Standards-at-a-glance.md) lists which standard each work product answers to.
[How the repository is organized](How-the-repository-is-organized.md) maps the folders.

## What you would be asked to do

WP-M-06 plans every measure by gate. The summary table is
[WP-M-06 §9](../assurance/01-management/WP-M-06-confirmation-measures-plan.md#9-schedule-summary); the detail is in
the sections it points to.

- **Confirmation reviews** CR-01 to CR-12, each naming the work products, the planned independence level and the
  gate ([§4.1](../assurance/01-management/WP-M-06-confirmation-measures-plan.md#41-list-and-independence)). The
  procedure for one review is §4.2.
- **Functional safety audits** AUD-1 and AUD-2, checking that the plans are carried out as written (§5).
- **Functional safety assessments** FSA-I1 and FSA-I2 at the concept and system-design gates, and the final FSA-F
  before any release record (§6).
- **SOTIF and AI reviews** SR-01 to SR-04, planned at an independence equivalent to I3 because the standard sets
  none (§7).
- **Cybersecurity assessment** per [WP-M-09](../assurance/01-management/WP-M-09-cybersecurity-plan.md), with the
  report in [WP-K-05](../assurance/10-safety-case/WP-K-05-cybersecurity-assessment.md) (§8).

Who may do each is in
[§6.1](../assurance/01-management/WP-M-06-confirmation-measures-plan.md#61-assessor-qualification-and-independence):
no authorship of or contribution to the assessed work, no reporting line to the maintainer, no financial interest
beyond the fee, no involvement in upstream development of the assessed code, competence at the level
[WP-M-04 §4.2](../assurance/01-management/WP-M-04-organization-competence-safety-culture.md#42-competence-requirements-matrix)
sets, declared in writing in each report.

## What to assess against

A review is against a named state of the record, never against the moving branch.

| Thing | Where |
|---|---|
| Engineering baselines, and whether each is frozen by a tag or still under development | [`assurance/case-records/baselines/`](../assurance/case-records/baselines), rules in [WP-P-01](../assurance/07-supporting/WP-P-01-configuration-management-plan.md) |
| The reference configuration the claims apply to | [`cfg-001`](../assurance/case-records/configurations/cfg-001-toyota-corolla-e210.yaml) and the [reference vehicle](Reference-vehicle.md) page |
| A snapshot of the safety case as a PDF at a named baseline, with a manifest of hashes and a build attestation | [Snapshot releases](https://github.com/jherrodthomas/LionDriver/releases/tag/snapshot-latest) |
| A numbered controlled copy issued to you by name | [Controlled copy workflow](../.github/workflows/safety-case-controlled-copy.yaml), recorded in [`distribution.yaml`](../assurance/case-records/distribution.yaml) under [WP-P-04](../assurance/07-supporting/WP-P-04-documentation-management.md) |
| The digest that identifies the exact state of every record | The dashboard headline in the [README](../README.md#living-safety-case) |
| Which files count as safety-relevant, and in which class | [Safety-relevant paths](../assurance/07-supporting/safety-relevant-paths.txt), owned by WP-P-01 |

Everything is public. Read access is a clone of the repository at the baseline commit; the
[WP-K-04 access row](../assurance/10-safety-case/WP-K-04-functional-safety-assessment.md#2-assessor-and-independence)
adds vehicle and installation records and interviews with the role holders.

## How independence is recorded

- The levels I0 to I3 and who can reach each one today are in
  [WP-M-06 §3](../assurance/01-management/WP-M-06-confirmation-measures-plan.md#3-independence-levels).
- A confirmation record is written by the named reviewer at the required level, states that independence in
  writing, and is stored under
  [`10-safety-case/confirmation/`](../assurance/10-safety-case/confirmation/README.md) using the
  [WP-P-05 §7.2 template](../assurance/07-supporting/WP-P-05-verification-review-procedure.md#72-review-record-template-r3-inspections-confirmation-reviews-reviews-outside-github).
- Only a review record in [`case/reviews/`](../assurance/case-records/reviews/reviews.yaml) can move a claim or evidence
  item to accepted. The validator rejects an accepted object whose review reference does not point to an accepted
  review that lists it.
- **What does not count.** A passing CI run. An AI-generated pre-review such as the `RR-2026-nnn` records or the
  [ISO 26262 documentary audit package](../assurance/00-assessment/iso26262-2018/README.md): these are I0 inputs to
  a confirmation measure, and say so in their own headers. The
  [ASPICE capability baseline](../assurance/01-management/WP-M-13-aspice-capability-baseline.md) is a
  self-assessment.

## Where the known problems are listed

The project publishes its own counter-evidence. Start with these rather than hunting for it.

| List | Where |
|---|---|
| Findings against the inherited code and process, GAP-nn | [Gap assessment](../assurance/00-assessment/gap-assessment.md) |
| Defeaters attached to claims, DF-nn | [WP-K-01 §7](../assurance/10-safety-case/WP-K-01-safety-case.md#7-defeaters-counter-evidence) and [`case/defeaters/`](../assurance/case-records/defeaters) |
| Assumptions the argument rests on, AOU-nn | [WP-K-01 §5](../assurance/10-safety-case/WP-K-01-safety-case.md#5-assumptions) |
| Open items of each work product | The last section of every work product, counted per gate in the [gate skeletons](../assurance/10-safety-case/gates/skeletons) |
| Project risks, R-nn | [WP-M-07 risk register](../assurance/01-management/WP-M-07-risk-management.md) |
| Questions the lead has decided, and the ones still open | [Decision register](../assurance/01-management/decisions/README.md); see [How decisions are made](How-decisions-are-made.md) |
| The lead's recorded deviations where a measure was deferred | Decision register entries DQ-013 (gate G0 with its reviews as open conditions) and DQ-010 (independent reviewer) in [`register.yaml`](../assurance/01-management/decisions/register.yaml) |

## How to send findings

- **A finding from a confirmation measure** becomes a GitHub issue labelled `confirmation-finding`, handled under
  [WP-P-03](../assurance/07-supporting/WP-P-03-problem-resolution.md), and is listed with its ID in your record
  ([WP-M-06 §10](../assurance/01-management/WP-M-06-confirmation-measures-plan.md#10-records)).
- **A comment on a work product short of a formal review** goes to the pull request that changes it, or to an
  [issue](https://github.com/jherrodthomas/LionDriver/issues) naming the work product and section.
- **A vulnerability** goes through [SECURITY.md](../SECURITY.md), never a public issue. See
  [Reporting a safety concern](Reporting-a-safety-concern.md).
- **A question** goes to [Discussions](https://github.com/jherrodthomas/LionDriver/discussions).

## Taking the role on

Engaging an assessor is a decision of the project lead, recorded in the decision register (DQ-009 for functional
safety, DQ-024 for cybersecurity). If you are considering it, the shortest route is an issue or a discussion thread
saying so, with the competence evidence
[WP-M-04 §4.4](../assurance/01-management/WP-M-04-organization-competence-safety-culture.md#44-competence-evidence-record-template)
asks for. Whether a legal entity is needed for the contract is itself a recorded decision
([WP-M-04 OI-5](../assurance/01-management/WP-M-04-organization-competence-safety-culture.md#7-open-items)).

> Assurance status represents recorded engineering evidence and review state. It does not constitute
> certification or approval for unsupervised operation.
