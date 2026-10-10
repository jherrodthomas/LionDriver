# Upstream sync impact analyses

This folder holds the impact analysis record for each upstream sync (change type CT-3,
[WP-P-02 §9](../WP-P-02-change-management.md#9-upstream-synchronization-ct-3-d-02)), produced
under the sync procedure in [WP-M-11 §5](../../01-management/WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02)
with the template in [WP-M-12 §7.3](../../01-management/WP-M-12-impact-analysis.md#73-template).

## When syncs happen

Syncs happen once per MINOR release, before the release-candidate freeze. The only out-of-cycle exception is a targeted security or safety fix. See [WP-M-11 §5](../../01-management/WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02) (D-02, decided 2026-10-10).

## Generating a report

```sh
tools/sync/sync_report.py <repo> [--to <upstream commit|branch|tag>] [--from <commit>]
```

`<repo>` is `openpilot` (the superproject) or one of `panda`, `opendbc_repo`, `msgq_repo`,
`rednose_repo`, `teleoprtc_repo`, `tinygrad_repo`. Defaults:

- `--from`: the current LionDriver pin. For a submodule that is its gitlink commit in `HEAD`. For
  `openpilot` it is the upstream baseline recorded in
  `openpilot/selfdrive/test/process_replay/ref_commit`.
- `--to`: upstream `master`. Name an exact commit before opening a sync change request; the
  procedure never syncs to a moving branch head.

The tool fetches upstream history without file contents and lists every commit and changed
file in the range. It classifies each file against
[`safety-relevant-paths.txt`](../safety-relevant-paths.txt) and writes
`sync-<date>-<repo>-<target>.md` here. It never changes pins and never pushes.

## From generated report to record

A generated report covers procedure steps 2–3 (range, commits, classification) and lays out
step 4. Before it becomes a record:

1. Read every diff in an SR-A or SR-Q file. Commit titles are not enough.
2. Fill in FuSa / SOTIF / AI / CS, the affected hazards and work products, and the decision
   (take / modify / reject) for every safety-relevant commit.
3. Assign the `IA-<yyyy>-<nn>` number, link the change request, and record the author and
   reviewer with their independence level.
4. Attach the verification re-run results and list the updated work products.
5. Set `Status` to `In review`. Merge only after the review in
   [WP-P-05](../WP-P-05-verification-review-procedure.md) is done.

A report with `Status: Draft: generated, not reviewed` documents upstream drift. It is not
a sync decision.

## Records

| File | Range | Highest class | Status |
|---|---|---|---|
| [sync-2026-10-10-openpilot-b9c815d.md](sync-2026-10-10-openpilot-b9c815d.md) | openpilot `655bfde..b9c815d` (2 commits) | SR-Q | Draft: drift survey, no sync decided |
| [sync-2026-10-10-msgq-326a9f5.md](sync-2026-10-10-msgq-326a9f5.md) | msgq `0e266c1..326a9f5` (9 commits) | SR-Q | Draft: drift survey, no sync decided |

On 2026-10-10, upstream `panda`, `opendbc`, `rednose` and `teleoprtc` `master` were identical
to the LionDriver pins, so no report was generated for them.
