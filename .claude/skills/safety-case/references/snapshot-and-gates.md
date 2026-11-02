# Snapshot, controlled copies and gates

Source of truth: [`assurance/case-records/README.md`](../../../../assurance/case-records/README.md) §5.1,
[`gates/README.md`](../../../../assurance/10-safety-case/gates/README.md), and the two workflows
`.github/workflows/safety-case-snapshot.yaml` and `.github/workflows/safety-case-controlled-copy.yaml`.

## Who triggers what

| Output | Trigger | Who | You (AI) |
|---|---|---|---|
| Living snapshot `snapshot-latest`, ID `SC-<date>-<sha>` | Merge to `liondriver-dev` touching `assurance/**` or `README.md` | Automatic | Nothing to do; a PR touching `case-records/**` builds and renders it without publishing, so a broken build fails before merge |
| Baseline release `bl-NNN` (kept permanently) | Pushed tag `bl-NNN` | The lead, after the baseline is frozen under WP-P-01 | Never push the tag or set a baseline `frozen` |
| Controlled copy `CC-YYYY-NNN` | `workflow_dispatch` of the controlled-copy workflow with recipient and purpose; runs only on `liondriver-dev` | A person with write access | Never run it, never run `distribution.py issue`, never edit `distribution.yaml` (append-only, public, entries never deleted) |
| Gate skeleton `gates/skeletons/G<n>-skeleton.md` | `process_model.py` | Generated; CI checks it | Regenerate when its sources change |
| Gate record `gates/G<n>-<YYYY-MM-DD>.md` | A held gate review | The chair (safety manager) and participants | Never create or edit one. `caselib` counts any file with that name and Pass ticked as a passed gate; with a frozen, tagged baseline the release then shows "APPROVED" |

Both workflows refuse to publish if `validate.py`, `check_trace.py`, `check_links.py`,
`generate_dashboard.py --check` (snapshot only) or `distribution.py --check` fails.

## Status on the snapshot

`caselib.release_status` is the only source of DRAFT or APPROVED on the badge, cover, watermark and approval page:
APPROVED needs a gate record with Pass ticked **and** the current baseline `frozen` with a `tag`. A living snapshot
is always DRAFT. Never work around this rule; `test_snapshot.py` tests it.

## Build one locally (to look at it)

```bash
python3 assurance/case-records/tools/build_snapshot.py --out <scratchpad>/snap      # HTML + manifest.json
NODE_PATH=/opt/node-tools/node_modules node assurance/case-records/tools/render_snapshot.cjs <scratchpad>/snap
```

Write to the scratchpad, not `build/` in the repository. The first line prints the ID and status, for example
`OK: SC-2026.11.02-656641d (DRAFT: no gate passed)`. The PDF needs Playwright with its Chromium; in the cloud
container the pre-installed copy is under `/opt/node-tools/node_modules` (a different Playwright, such as the one in
`assurance/sim/interactive/node_modules`, may look for a browser that is not installed). Without the `qrcode`
package the footer prints the URL instead of a QR code; that is fine locally.

Read a few PDF pages with the Read tool (`pages: "1-3"`): the cover says DRAFT, the approval page lists no gate
passed, and every page has the running header and footer. Do not use `--copy` locally; it refuses a copy number
without a distribution record, by design.

## Preparing a gate review

1. `python3 assurance/process/tools/process_model.py` regenerates the skeletons from WP-M-00, WP-M-02, WP-M-06 and
   `trace/items/ifr.yaml`; `--check` fails if one is stale. Never edit a skeleton by hand: fix the source document.
2. You may summarise for the lead what a skeleton shows (open items, missing roles, interfaces not agreed,
   confirmation measures without a record) and what blocks each exit criterion.
3. Go/no-go is the lead's decision. Put it in the decision register with the `decision-inbox` skill, as a question
   that stands on its own, not "pass G1?".

## Local gotcha

`assurance/trace/tools/check_links.py` also scans git-ignored `node_modules` folders on disk. If it reports a broken
link inside `assurance/sim/interactive/node_modules/`, that is the local install, not the repository; CI checks out
clean and does not see it.
