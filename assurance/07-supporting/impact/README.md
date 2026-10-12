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

## LionDriver change records

Impact analyses for changes LionDriver makes itself to safety-relevant code (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)), using the same template.

| File | Change | Highest class | Status |
|---|---|---|---|
| [change-2026-10-12-panda-hw-watchdog.md](change-2026-10-12-panda-hw-watchdog.md) | panda: independent hardware watchdog, [jherrodthomas/panda#1](https://github.com/jherrodthomas/panda/pull/1); 100 Hz safety task and window mode, [jherrodthomas/panda#3](https://github.com/jherrodthomas/panda/pull/3); watchdog reset reporting, [jherrodthomas/panda#6](https://github.com/jherrodthomas/panda/pull/6) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently; D-1, D-2, D-3 accepted as interim |
| [change-2026-10-12-opendbc-toyota-rx-timeout.md](change-2026-10-12-opendbc-toyota-rx-timeout.md) | opendbc: Toyota RX timeout after 5 periods, [jherrodthomas/opendbc#1](https://github.com/jherrodthomas/opendbc/pull/1); engagement gated on the RX checks, [jherrodthomas/opendbc#3](https://github.com/jherrodthomas/opendbc/pull/3) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently |
| [change-2026-10-12-opendbc-toyota-tx-whitelist.md](change-2026-10-12-opendbc-toyota-tx-whitelist.md) | opendbc: PCS and DSU messages removed from the Toyota TX whitelist, [jherrodthomas/opendbc#2](https://github.com/jherrodthomas/opendbc/pull/2) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently |
| [change-2026-10-12-panda-safety-mode-lock.md](change-2026-10-12-panda-safety-mode-lock.md) | panda: safety-mode lock in the reference build, [jherrodthomas/panda#4](https://github.com/jherrodthomas/panda/pull/4) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently |
| [change-2026-10-12-panda-fast-heartbeat.md](change-2026-10-12-panda-fast-heartbeat.md) | panda: authority revoked 0.3 s after the last SoC heartbeat (TSR-407), [jherrodthomas/panda#7](https://github.com/jherrodthomas/panda/pull/7) | SR-A | Integrated 2026-10-12; not verified on hardware; not reviewed independently (panda `c2e5d93`) |
| [change-2026-10-12-panda-irq-priorities.md](change-2026-10-12-panda-irq-priorities.md) | panda: explicit interrupt priorities and atomic safety-configuration switch (TSR-519, WP-W-03 R-1, R-8), [jherrodthomas/panda#10](https://github.com/jherrodthomas/panda/pull/10) | SR-A | Integrated 2026-10-12; not verified on hardware; not reviewed independently (panda `52cad44`) |
| [change-2026-10-12-opendbc-toyota-eps-fault.md](change-2026-10-12-opendbc-toyota-eps-fault.md) | opendbc: LKA actuation refused while the EPS reports a fault (TSR-110), [jherrodthomas/opendbc#7](https://github.com/jherrodthomas/opendbc/pull/7); reporting to the host, [opendbc#8](https://github.com/jherrodthomas/opendbc/pull/8), [panda#11](https://github.com/jherrodthomas/panda/pull/11); siren on a persistent EPS fault (TSR-516(b)), [panda#14](https://github.com/jherrodthomas/panda/pull/14) | SR-A | Integrated 2026-10-12; not verified on hardware; not reviewed independently (opendbc `242d63d`; reporting panda `877730e`, opendbc `adcb7c2`). Siren: panda `b790fca`, pinned by LionDriver PR #45, not merged at time of writing |
| [change-2026-10-12-opendbc-toyota-cruise-main.md](change-2026-10-12-opendbc-toyota-cruise-main.md) | opendbc: CRUISE_ACTIVE checked against MAIN_ON (TSR-405(c)), [jherrodthomas/opendbc#9](https://github.com/jherrodthomas/opendbc/pull/9); TSR-405(b) open | SR-A | Integrated 2026-10-12; not verified on hardware; not reviewed independently (opendbc `875e325`) |
| [change-2026-10-12-tx-rate-supervision.md](change-2026-10-12-tx-rate-supervision.md) | opendbc and panda: per-ID TX rate supervision (TSR-518, [DN-01](../../05-software/design-notes/DN-01-tx-rate-supervision.md)), [jherrodthomas/opendbc#10](https://github.com/jherrodthomas/opendbc/pull/10), [jherrodthomas/panda#13](https://github.com/jherrodthomas/panda/pull/13) | SR-A | Integrated 2026-10-12; not verified on hardware; not reviewed independently (opendbc `7993399`, panda `8aa8671`) |

The RX checks for `0x262` and `0x1D3` in the reference build (opendbc `98404a4`, [jherrodthomas/opendbc#6](https://github.com/jherrodthomas/opendbc/pull/6)) are recorded in the RX timeout record (§8) and the EPS fault record.
