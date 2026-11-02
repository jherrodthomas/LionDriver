---
name: safety-case
description: Work on LionDriver's living safety case. It covers the case records in assurance/case-records (claims or GSN goals, strategies, evidence or solutions, defeaters, actions, configurations, baselines, reviews), their schema and validate.py, WP-K-01 and its X3 cross-check, the GSN diagrams (gsn_diagrams.py), the dashboard and README status strip (generate_dashboard.py), the downloadable and controlled-copy snapshot (build_snapshot.py, the safety-case-snapshot and safety-case-controlled-copy workflows), the gate skeletons (process_model.py) and the "living safety case" CI job. Use it whenever someone adds or changes a claim, evidence item, defeater, open item or assumption link, asks "what is the status of the safety case", "is Sn-xx done", "add a defeater", "update WP-K-01", "regenerate the GSN or dashboard", "the safety case job failed", "X3 failed", "build or download the snapshot", "issue a controlled copy", or "prepare a gate review", even if nobody says "case records".
---

# Safety case

The safety case is [WP-K-01](../../../assurance/10-safety-case/WP-K-01-safety-case.md), which stays the reviewed
document. Its machine-readable copy is in
[`assurance/case-records/`](../../../assurance/case-records/README.md) (read its §3 and §4 once per session). Every
dashboard number, GSN sheet, status strip and snapshot page is **generated from these records**. You never type a
status or count anywhere: you change the record and the document, then regenerate.

> Assurance status is recorded evidence and review state. It is not certification or approval.

## What you may and may not change (AI work is I0, WP-M-02 §3.3)

| You may | You may not |
|---|---|
| Add a claim, strategy, evidence item, action or **open** defeater, mirrored in WP-K-01 | Set `review_state: accepted` (or `in-review`) on anything, or fill in `reviewer`, `review_date`, `review_ref` |
| Change `evidence_status` from `missing` to `partial` when the artefact now exists in the repository (drafted, or inherited result) | Set `evidence_status: available`. It means performed **and approved** at a baseline, so V6 needs an accepted review |
| Set an accepted record back to `not-reviewed` when a change affects it (WP-M-12 impact analysis) | Set a defeater to `closed`, or a claim to `accepted`, or delete a defeater to make a goal go green |
| Reword titles, descriptions and notes so they say what is true now, with the date | Write a review record (`reviews.yaml`) or a confirmation record. An AI review is not a review record |
| Regenerate diagrams, dashboard, skeletons; build a snapshot locally | Create a gate record `gates/G<n>-<date>.md` or tick its Pass box. The snapshot counts it as a passed gate |
| Propose a defeater closure (evidence + change + verification) in the PR text | Freeze a baseline, push a `bl-NNN` tag, or run the controlled-copy workflow or `distribution.py issue` |

Never lower an ASIL, move a safety limit or change a timing clock to clear a defeater or a red goal. Never reuse
an ID. When a record and a skill disagree, the record wins.

When the step needs a person, say so in the PR and in chat: the named reviewer writes the review record, at the
independence WP-M-06 requires. Gate go/no-go, risk acceptance and accepting a defeater as tolerable are the
lead's questions: use the `decision-inbox` skill, never a bare ID.

## Changing a record

Details and a field-by-field guide: [`references/records.md`](references/records.md).

1. **WP-K-01 first, records in the same change.** Evidence lives in WP-K-01 §6, defeaters in §7, open items in
   §10; claims and strategies in the trees of §3–§4. Validator check X3 compares the §6, §7 and §10 tables (IDs,
   the §6 Status column, the §6 summary line "**Available N, Partial N, Missing N** (N evidence items)") with the
   records, so update both or CI fails.
2. **Edit the YAML** in the folder of its kind (`claims/`, `arguments/`, `evidence/`, `defeaters/`, `actions/`,
   …). Use the restricted subset: a list of flat mappings, quoted single-line strings, bare words, `null`, flow
   lists of bare IDs; dates and git revisions always quoted. Every schema field present, no others
   ([`schema/case-schema.json`](../../../assurance/case-records/schema/case-schema.json)).
3. **Link both ways** (V4): a claim's `evidence_refs` and the evidence's `related_claims`; a claim's `defeaters`
   and the defeater's `related_claims`; an argument's `subclaims` and each child's `parent`/`argument`. Hazards,
   SGs, requirements and assumptions (`AOU-nn`) are referenced by ID from `assurance/trace/items/`, never copied.
4. **Set `source_revision`** to the commit the record describes (quoted). Leave `baseline` as is unless the lead
   re-baselines.
5. **Validate, regenerate, check** (next section). Bump WP-K-01's version and history line (WP-P-04).

## Commands

Run from the repository root. These are the steps of the `living safety case` job in
`.github/workflows/assurance.yaml`; all passed on 2026-11-02.

```bash
python3 assurance/case-records/tools/validate.py                  # V1–V8 and X3; prints counts, exit 1 on any error
python3 assurance/case-records/tools/generate_dashboard.py        # write status.json, badge.json, 3 SVG cards, README strip and table
python3 assurance/case-records/tools/gsn_diagrams.py              # write the GSN sheets and gsn/README.md
python3 assurance/case-records/tools/generate_dashboard.py --check
python3 assurance/case-records/tools/gsn_diagrams.py --check
python3 assurance/case-records/tools/test_case.py                 # validator self-tests
python3 assurance/case-records/tools/test_gsn.py
python3 assurance/case-records/tools/test_snapshot.py             # snapshot builder and the release-status rule (slow, ~15 s)
python3 assurance/case-records/tools/check_pages.py               # README and docs links and SVG safety
python3 assurance/process/tools/process_model.py --check          # gate skeletons and process maps current
```

Both generators validate first and write nothing from invalid records. The outputs are deterministic (a digest of
the records, no timestamp), so commit them in the same change. `generate_dashboard.py` rewrites the text between
the `assurance-summary` markers in `assurance/README.md` and the `assurance-headline` markers in the front-page
`README.md`: never edit between the markers by hand.

If a generator fails, fix the record or WP-K-01 (an unknown ID, a context line `gsn_diagrams.py` cannot attach, a
§4 table row missing in WP-K-03). Never loosen a check or edit a generated SVG.

## How evidence status is shown

| Where | What you see |
|---|---|
| Record | `evidence_status` (missing / partial / available) and, separately, `review_state` |
| WP-K-01 §6 | Status column and the summary line; must equal the records (X3) |
| GSN sheet | Solution circle green available, amber partial, white dashed missing; a goal takes the **worst** status below it (grey = not developed); open defeaters in red on the goal they undermine |
| GSN phone view (`*-phone.svg`) | The same as an indented outline; missing is red |
| Dashboard cards | Counts by status, "evidence requiring review" (partial or available, not accepted), lifecycle-area status (rules in the case-records README §5) |
| Snapshot | DRAFT or APPROVED from `caselib.release_status` only: APPROVED needs a gate record with Pass ticked **and** a frozen, tagged baseline |

## Look at the output

After regenerating, render what changed and Read the PNGs (the full sheet and the 390 px phone width):

```bash
node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png \
  assurance/10-safety-case/gsn/gsn-2-G1-phone.svg docs/assets/liondriver/assurance/dashboard.svg --width 390
```

Check the goal you touched has the colour the rule predicts, the defeater appears on the right goal, and the
dashboard counts match the validator's printed counts. `git diff --stat` should list only the records, WP-K-01 and
generated files you expected.

## Snapshot, controlled copies and gates

Who triggers what, and how to build a snapshot locally: [`references/snapshot-and-gates.md`](references/snapshot-and-gates.md).
In short: living snapshots publish themselves on merge; baseline releases and controlled copies are human acts;
gate skeletons are generated and are never a gate record.

## Before you hand over

- The validator and every `--check` above pass; generated files are committed with the change.
- WP-K-01 version and history bumped; the PR names which records changed and says it is I0 work needing review.
- If the change touches `.github/workflows/**` or `assurance/trace/**` (SR-T in
  `assurance/07-supporting/safety-relevant-paths.txt`), follow the WP-P-02 safety-relevant route.
- New abbreviations go in `assurance/trace/tools/terms.py` (`terms.py --check`).
