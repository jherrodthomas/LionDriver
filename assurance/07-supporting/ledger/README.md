# Change ledger

One row per change merged to `liondriver-dev`, written by CI and never edited, and the work-product versions
computed from those rows. It is the change and document-control record that GitHub keeps only in its own database:
who changed what, with which checks, approved by whom, and what version each work product has as a result
([WP-P-04 §5-§6](../WP-P-04-documentation-management.md#5-document-control-header-and-status); decisions DQ-441 and
DQ-442).

| File | What it is |
|---|---|
| [`ledger.py`](ledger.py) | Builds, verifies and reads the ledger; writes the spreadsheet view |
| [`gate-approvals.yaml`](gate-approvals.yaml) | Gate approvals, the only thing that raises X |
| [`test_ledger.py`](test_ledger.py) | Tests on a throwaway repository |
| `ledger.jsonl`, `ledger.xlsx` on branch `ledger` | The ledger itself and its spreadsheet, written by [`ledger.yaml`](../../../.github/workflows/ledger.yaml) |

## How it is written

After every push to `liondriver-dev` the workflow appends a row for each new commit to `ledger.jsonl` on the
`ledger` branch. A merge of a pull request gets the PR's title, change-class labels, who merged it, who approved it
(other than the author) and the results of the checks on its head commit. A commit pushed without a pull request
gets a row too, flagged as an exception. Writing to its own branch means the ledger never adds commits to
`liondriver-dev`.

Each row stores the SHA-256 of the row before it together with its own content. Editing or deleting an old row
breaks every later hash, and `verify` also fails when a recorded commit has left the branch history (a force-push).
The workflow verifies before and after every append and stops rather than append to a broken chain.

The first run writes the history before the ledger existed from git alone (no labels, reviews or checks: GitHub's
rate limit does not allow fetching them for some 600 past pull requests), then a seed row.

## Versions: X.Y.Z, computed

| Part | Raised by | Resets |
|---|---|---|
| X approved issue | A gate approval listing the work product in `gate-approvals.yaml` (DQ-442). 0 = never approved | Y, Z |
| Y content change | Each merged change that touches the work product's file | Z |
| Z editorial change | Each merged change labelled `editorial` (never allowed with `sr-a` or `sr-q`) | |

The seed row starts every work product at the version its header carries at that commit (0.68 becomes 0.68.0), so
no history is renumbered. From then on the version is the ledger's; a number typed in a header is ignored. The
version is stamped on a document when it is output (export, snapshot, wiki), not stored in its file (DQ-441).

## Reading it

```sh
git fetch origin ledger
git show origin/ledger:ledger.jsonl > /tmp/ledger.jsonl
python3 assurance/07-supporting/ledger/ledger.py verify   --ledger /tmp/ledger.jsonl --ref origin/liondriver-dev
python3 assurance/07-supporting/ledger/ledger.py versions --ledger /tmp/ledger.jsonl --doc WP-S-02
```

`ledger.xlsx` has three tabs: **Changes** (newest first), **Documents** (current version of every work product) and
**Exceptions** (pushes without a pull request, safety-class changes without an approving review, merges with a
failed check, a missing change-class label, `editorial` on a safety-class change).

## Still to do

| Item | Status |
|---|---|
| Protect the `ledger` branch against force-push and deletion | Repository setting, for the lead |
| Stamp versions at output: header block and running footer in the snapshot and exports | Next step (WP-P-04 OI-7) |
| Remove the hand-typed `Version` from work-product headers, keeping their text as revision history | Next step (WP-P-04 OI-7) |
| Change record for selected documents in the export | Next step (WP-P-04 OI-3) |
| Ledger tabs in the workbook viewer page | Next step |
