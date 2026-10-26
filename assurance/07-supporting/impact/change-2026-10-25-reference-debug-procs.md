# Change impact: no debug, maneuver or joystick processes in the reference build (DQ-131)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant host software and to the release tooling (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements the project lead's answer to DQ-131, option A (2026-10-25): leave the debug, maneuver and joystick modes out of the reference build; the release script builds the reference variant without the joystick and maneuver processes, a test checks they are absent, and the engagement refusal of [change-2026-10-19-reference-entry-checks](change-2026-10-19-reference-entry-checks.md) (DQ-221) stays as a second barrier. Until now the item refused to engage while `JoystickDebugMode`, `LongitudinalManeuverMode` or `LateralManeuverMode` was set, but the process manager still started the processes of these modes when the param changed, so a param changed over SSH or by a bug started a process that sends commands.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-25** in this LionDriver PR; checked by a unit test and a release-list check in CI; not verified on the device; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/system/manager/process_config.py`); SR-T (`SConstruct`, `tools/release/**`, `.github/workflows/safety.yaml`) ([safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Yes: every build made with `LIONDRIVER_REFERENCE` set or unset (the default). A build with `LIONDRIVER_REFERENCE=` (empty) and the `RELEASE_VARIANT=upstream` release keep the upstream process set |
| Decision | DQ-131 A (lead, 2026-10-25) |
| Requirements | [WP-C-07](../../02-concept/WP-C-07-sotif-functional-modifications.md) FM-06 (debug, maneuver and joystick part); [WP-C-01](../../02-concept/WP-C-01-item-definition.md) OI-5 (closed); [WP-C-10](../../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) CSG-03, CSR-C-07; [WP-S-07](../../03-system/WP-S-07-cybersecurity-requirements-architecture.md) CSR-071 (implemented), CSR-073 (partly); TSR-806 ([WP-S-06](../../03-system/WP-S-06-requirements-production-operation.md), "debug/maneuver/joystick modes absent"); TSR-613 ([WP-S-02](../../03-system/WP-S-02-technical-safety-requirements.md)) and SWSR-613 ([WP-W-02](../../05-software/WP-W-02-software-safety-requirements.md)) partial, the `lateralManeuverPlan` path open (OI-2); HATARA IX-02 (CSR-C-07 partial); GAP-20 |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| Build variant decides the process set | `SConstruct`, `.gitignore` | The setting that builds the reference panda firmware and `pandad` (`liondriver_reference`) now also decides the process set. A non-reference build writes the untracked marker `openpilot/system/manager/upstream_build`; a reference build removes it. A release copies only tracked files, so it carries the marker only when it was built non-reference | The exact `SConstruct` block run in scons 4.11.1: unset → no marker; empty → marker written; `1` after empty → marker removed. The full openpilot build was not run locally; CI builds it |
| Debug processes not registered | `openpilot/system/manager/process_config.py` | Without the marker (`REFERENCE_BUILD`): `joystick`, `maneuversd` and `lateral_maneuversd` are not registered; `joystickd` runs for notCar only (in joystick mode it sends `carControl` in place of `controlsd`); `controlsd` and `plannerd` run whatever the three params say. With the marker the upstream conditions are unchanged | `openpilot/system/manager/test/test_reference_build.py`: the three processes are absent; no debug param changes which processes run on a car, and `controlsd` and `plannerd` run; `joystickd` still runs for notCar; the upstream variant keeps every debug process and condition; in CI the default build is the reference build. Run locally with the compiled modules stubbed (no scons build of `libparams` or msgq here): 6 passed. Mutations: the filter removed → 2 failures; `controlsd` gated on joystick mode again → 1 failure. Runs in the `unit tests` job (`tools/op.sh test`) |
| Reference release ships without them | `tools/release/release_files.py`, `tools/release/build_release.sh`, `tools/release/release_variant.sh` (comment), `.github/workflows/safety.yaml` | With `RELEASE_VARIANT=reference` (the default, also when unset) the release file list leaves out `openpilot/tools/joystick/joystick_control.py`, `openpilot/tools/longitudinal_maneuvers/` and `openpilot/tools/lateral_maneuvers/`; `joystickd.py` stays. After `scons`, `build_release.sh` stops a reference release that has the marker or any of the three modules. CI job `panda_reference_release_build`, step "Release variant selection", fails if the reference list contains one of them or the upstream list none, and now also runs on changes to `release_files.py` | The CI step's commands run locally: reference list 3661 files, none matched; upstream list 3672, 11 matched; `bash -n build_release.sh` passes. The unit test above checks `released()` for each left-out process module |

Records: the status cells above, regenerated from them the trace items (`tsr.yaml`, `swsr.yaml`, `cs.yaml`), the TSR list and its figures, WP-S-03 Figure 6-1, WP-C-10 Figure 7-1 (CSG-03 card: barrier part built) and the HATARA interaction table and figure.

The engagement refusal of DQ-221 is unchanged: on the reference platform `selfdrived` still raises `settingNotAssured` while one of the three params is set, so the toggles in the developer settings have no effect beyond refusing entry.

## 2. Impact

- **Safety:** removes a path by which one local param starts a process that commands actuation (FI-20, TC-26; HATARA IX-02): `joystickd` in place of `controlsd`, `maneuversd` in place of `plannerd`, `lateral_maneuversd` feeding `controlsd`. Nothing in the normal control path changes: on a car with the params clear, the reference process set is the same as before.
- **Cybersecurity:** CSG-03 / CSR-071 met for these three modes in the reference build. An attacker with local write access to the code or able to publish on msgq is not stopped by this (CSR-C-06, GAP-20); `controlsd` still subscribes to `lateralManeuverPlan`.
- **Development:** a developer who needs the modes on the reference car builds with `LIONDRIVER_REFERENCE=` (empty), which also builds the panda firmware and `pandad` without the reference lock; such a build is outside the safety claims, as before. A source checkout run without `scons` has no marker and gets the reference process set.
- **Upstream:** a build variant to keep at each openpilot sync (WP-M-11): new upstream debug processes or a changed `process_config.py` need the same treatment, and the unit test fails if a debug param changes the reference process set.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | DM demo mode (`IsDriverViewEnabled`) of FM-06 and CSR-072 is not covered by this change | G2 (FM-06) |
| OI-2 | `controlsd` still subscribes to `lateralManeuverPlan` (FM-06); in the reference build nothing publishes it. Drop the subscription in the reference build, or record why it stays | G2 |
| OI-3 | Check on the reference device: set each of the three params over SSH while onroad; no new process starts (`ps`), `controlsd` and `plannerd` keep running, and entry is refused | Vehicle test (WP-V-07); WP-V-05 VS-FI-23 |
| OI-4 | The developer settings still show the three toggles in the reference build; hide them or label them as without effect (WP-O-03) | WP-O-03 owner |
| OI-5 | Carry the variant at each upstream sync (sync report, WP-M-11) | Each sync |
