# Change impact: explicit reference release variant and reference firmware build in CI (ATC-19)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to the release tooling of safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-13** on branch `claude/inspiring-hamilton-kf8283`; CI job not yet run on GitHub; not reviewed independently |
| Change requests | WP-W-03 ATC-19; [RR-2026-009](../../05-software/reviews/RR-2026-009.md) F-33 (decision §7) |
| Range | LionDriver only: `tools/release/release_variant.sh` (new), `tools/release/build_release.sh`, `.github/workflows/safety.yaml`. No firmware source change |
| Reference configuration affected | Yes: decides which firmware a release contains |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Starting point: most of ATC-19 was already on the base

F-33 was recorded against `682f184`, where `build_release.sh` built the panda firmware as `RELEASE=1` only. Two later base changes closed most of it. This change completes it and corrects the ATC-19 status in WP-W-03.

| ATC-19 element | State before this change |
|---|---|
| Release firmware built with `LIONDRIVER_REFERENCE=1` | Yes, implicitly: the root `SConstruct` sets `LIONDRIVER_REFERENCE=1` when the variable is unset ([#36](https://github.com/jherrodthomas/LionDriver/pull/36), `e84f850`), and `build_release.sh` builds the panda through it (`scons panda/`). But a `LIONDRIVER_REFERENCE` that is set and empty, for example left over from development on another vehicle, silently produced an upstream build |
| The host can tell which firmware is installed | Yes: the panda reports `HEALTH_FLAG_REFERENCE_BUILD`, and in a reference build `pandad` refuses a car safety mode on a panda without it ([#41](https://github.com/jherrodthomas/LionDriver/pull/41), `717f0e9`, TSR-619) |
| Explicit reference-release variant; upstream variant kept | No |
| CI job that builds the reference release firmware | No |

## 2. Change

| Item | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| Release variant | `tools/release/release_variant.sh` (new), `tools/release/build_release.sh` | `RELEASE_VARIANT=reference` (default) exports `LIONDRIVER_REFERENCE=1` before the build; `RELEASE_VARIANT=upstream` exports it empty and warns; any other value stops the script. The variant is printed and recorded in the release commit message | Yes (tool qualification: the release script decides which safety mechanisms ship) | No | No | Yes (a release without the reference lock accepts any safety mode from the host) | F-33; TSR-512, 513, 518, 619; SWSR-512, 513, 518, 705 | WP-W-01 (build configuration CF-01), WP-W-03 ATC-19, WP-W-09 CD-23, WP-P-01 (release baseline) | CI step "Release variant selection" | Proposed |
| CI job `panda_reference_release_build` | `.github/workflows/safety.yaml` | Selects the variant through `release_variant.sh` as the release script does, builds the panda with `RELEASE=1` (debug signing key), and fails unless every firmware compile in `compile_commands.json` carries `-DLIONDRIVER_REFERENCE` and none `-DALLOW_DEBUG`. `safety.yaml` now also runs on changes to the two release scripts | No (evidence of build configuration) | No | No | No | F-33 | WP-W-06/WP-V-05 (build evidence), WP-W-01 ENV-01 (build manifest per job) | The job itself | Proposed |

Not changed: the panda version string. The health flag already marks the build, and `pandad` acts on it. A version-string marker would be a panda change for reporting only, so it is left for a later change if field reports need it.

## 3. Verification results (local, 2026-10-13)

| Check | Result |
|---|---|
| Variant selection: unset → reference; set-but-empty `LIONDRIVER_REFERENCE` → reference; `upstream` → empty; unknown value → error; `bash -n build_release.sh` | Pass |
| Panda reference release build at panda `a55bdfc`, opendbc `a57b667` (`RELEASE=1`, debug key), checked with `compile_commands.json` | Pass: 10 firmware compiles, all with `-DLIONDRIVER_REFERENCE`, none with `-DALLOW_DEBUG` |
| Negative check: a debug build (no `RELEASE`) through the same step | Fails as intended |
| Full `build_release.sh` run (device, release key) | **Not run**: needs the release build machine and key |
| CI job on GitHub | **Not run yet** |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Run the release script once on the release build machine and confirm the commit message and the `HEALTH_FLAG_REFERENCE_BUILD` flag on a flashed panda | Release |
| OI-2 | WP-W-01 CF-01 and WP-P-01 release baseline: name `RELEASE_VARIANT=reference` as the release configuration | Next WP-W-01 revision |
