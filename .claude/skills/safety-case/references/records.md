# Case records: a field guide

The rules live in [`assurance/case-records/README.md`](../../../../assurance/case-records/README.md) §3–§4 and
[`schema/case-schema.json`](../../../../assurance/case-records/schema/case-schema.json); the validator is
[`tools/caselib.py`](../../../../assurance/case-records/tools/caselib.py) (entry point `validate.py`). This page is
the working order. Read the schema for the exact field list of a kind; do not copy it from here.

## Kinds, IDs, and where each lives in WP-K-01

| Kind | GSN element | ID pattern | File | In WP-K-01 |
|---|---|---|---|---|
| `claim` | goal | `G0`, `G1.1.4` | `claims/g<n>-*.yaml`, one file per top-level branch | the text trees of §3–§4 |
| `argument` | strategy | `S0`, `S1.1` | `arguments/strategies.yaml` | `→ S…` lines in the trees |
| `evidence` | solution | `Sn-NN` | `evidence/evidence.yaml` | §6 table (checked by X3) and `→ Sn-…` lines |
| `defeater` | counter-evidence (UL 4600, not GSN) | `DF-NN` | `defeaters/defeaters.yaml` | §7 table (X3) and `⇐ DF-…` lines |
| `action` | open item | `ACT-NNN`, `source_ref: OI-n` | `actions/actions.yaml` | §10 table (X3) |
| `configuration` | — | `CFG-NNN` | `configurations/` | context C3 |
| `baseline` | — | `BL-NNN` | `baselines/` | control header |
| `review` | — | `REV-NNN` | `reviews/reviews.yaml` | — (people only) |

Contexts and justifications (`⊙ C…`, `⊙ J…`) are not records: `gsn_diagrams.py` reads them from the `⊙` lines of
the WP-K-01 trees and attaches each to the goal or strategy above it. Assumptions are `AOU-nn` items in
`assurance/trace/items/aou.yaml` (WP-K-01 §5 shows their status); a claim names them in `related_assumptions` and the
tree shows them as `⊙ A: AOU-…`. The cybersecurity case (WP-K-03) has no records: its GSN sheets come from its
§2–§3 trees, §4 evidence table and §6 defeaters.

## Add an evidence item

1. Next free `Sn-NN` (never reuse a retired one). Add the row to WP-K-01 §6 with Status `Missing` or `Partial`,
   using the §6 rule at the top of that section, and update the §6 summary line counts.
2. Add the record: `evidence_status` matching the row, `lifecycle_area` from the schema enum, `location` a path
   that exists (V5), `related_claims`, `baseline`, `configuration: CFG-001`, `review_state: not-reviewed`, the
   three review fields `null`, `source: WP-K-01`, `source_revision: "<sha>"`.
3. Add the ID to each claim's `evidence_refs` (V4) and to the `→ Sn-…` line under that goal in the tree.

## Change an evidence item's status

- `missing` → `partial`: allowed when the artefact now exists in the repository (a drafted analysis or spec, an
  inherited result). Change the record, the §6 row, the summary line and the note ("spec drafted, not executed",
  "draft; not reviewed"), with the date.
- `partial` → `available`: **never by an AI**. It needs a review record written by the named reviewer
  (`reviews.yaml`, `outcome: accepted`, listing the item, same baseline), and then `review_state: accepted` with
  `reviewer`, `review_date`, `review_ref`. V6 rejects anything less. A passing test or CI run is an input to that
  review, not the review.
- Any → lower (`available` → `partial`, or `accepted` → `not-reviewed`): required when a change invalidates it (the
  impact analysis of WP-M-12 names the records). Do it, and say why in the description.

## Add or change a defeater

1. Next free `DF-NN`. Add the §7 row (counter-evidence, `GAP-…`, undermined claims, closure route) and the
   `⇐ DF-…` line under each undermined goal.
2. Record: `lifecycle_status: open`, `gaps`, `related_claims`, `baseline`, `source`, `source_revision`; add the
   ID to each claim's `defeaters` (V4).
3. Rewording an open defeater to match progress ("implemented, host tests pass; open until HIL `test_11` and
   review") is fine and expected. **Closing** one is not yours: a defeater closes only with evidence that removes
   it (a change plus verification, reviewed) or a changed claim with rationale, and the reviewer or lead records
   it. Put the proposed closure route and the evidence you have in the PR.

## Add a claim or strategy

1. Write the goal into the WP-K-01 tree first (`→ G…` under its strategy), then the record: `parent`, `argument`
   (the strategy that develops its parent), `lifecycle_status: draft`, `review_state: not-reviewed`, links to
   hazards, requirements and assumptions by ID.
2. Add it to the strategy's `subclaims` (V4); V8 needs one tree under `G0`.
3. Regenerate the GSN; a goal with no strategy and no evidence draws as undeveloped (diamond, grey).

## Open items (actions)

Each WP-K-01 §10 row `OI-n` has an action record with `source_ref: OI-n` and `needed_by` a gate. Close one only
when the work it names is merged (cite the commit in the row); if the item asks for a review, a verification or the
lead's decision, it stays open.

## Reading validator errors

`ERROR [V4] …` names the check. V1/V2 field or type, V3 unresolved ID (often a trace item not in
`assurance/trace/items/`), V4 one-sided link, V5 missing `location`, V6 an acceptance rule (you set something only
a review may set: undo it), V8 tree broken, X3 WP-K-01 and records disagree. `test_case.py` shows each check with
a planted defect if you need an example.
