# WP-P-01 Configuration Management Plan

| Field | Value |
|---|---|
| Work product | WP-P-01 Configuration management plan (incl. safety-relevant file list, baselines, submodules) |
| Standard reference | ISO 26262-8:2018 §7; ISO 26262-2:2018 §6 (release, baselines); ISO/SAE 21434:2021 §5 (configuration management); ASPICE 4.0 SUP.8 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (highest: ASIL of the envelope as set by WP-C-03) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This plan defines how LionDriver identifies, controls, records and audits its configuration items (CIs). It closes the planning part of GAP-29, GAP-35 and GAP-37 in the [gap assessment](../00-assessment/gap-assessment.md) and carries out decisions D-01, D-02 and D-07 of [WP-M-01 §8](../01-management/WP-M-01-assurance-strategy.md#8-strategic-decisions-required).

Scope: everything needed to rebuild, re-verify and re-argue a LionDriver release for the reference configuration (2020 Corolla LE, `TOYOTA_COROLLA_TSS2`, comma device with panda safety MCU). Change control is in [WP-P-02](WP-P-02-change-management.md); release baselines are in [WP-P-10](WP-P-10-release-management.md).

## 2. Current state (as found at `8b8c6ae`)

| Item | Observation | Evidence |
|---|---|---|
| Repository | `github.com/jherrodthomas/LionDriver`; branches `liondriver-dev` and `claude/*`; no `master`, no tags | `git branch -a`, `git tag` |
| Submodules | `panda`, `opendbc_repo`, `msgq_repo`, `rednose_repo`, `teleoprtc_repo` use relative URLs `../../commaai/*.git`, which resolve to `github.com/commaai/*`. `tinygrad_repo` uses an absolute upstream URL with `branch = master` | `.gitmodules` |
| Submodule pins | `opendbc_repo@229dc70`, `panda@92eb565`, `msgq_repo@0e266c1`, `rednose_repo@8671c17`, `teleoprtc_repo@1aa8fc4`, `tinygrad_repo@d3f09c9`. Only opendbc and panda are initialized in this checkout | `git submodule status` |
| Submodule check | `check-submodules.sh` fails unless each pin is on `origin/master` of the submodule remote; it skips tinygrad | `tools/release/check-submodules.sh` |
| Python dependencies | Hash-pinned lockfiles: `uv.lock` (openpilot) and `opendbc_repo/uv.lock` (opendbc tests, incl. cppcheck from a git branch) | `uv.lock`, `opendbc_repo/uv.lock` |
| Large files / models | Model files are Git LFS objects. The LFS endpoint is comma's Hugging Face repository, not a LionDriver store | `.gitattributes`, `.lfsconfig` |
| Version | `COMMA_VERSION "0.11.2"`; `pyproject.toml` version `0.1.0`, author `user@comma.ai`; release commits use the identity `Vehicle Researcher <user@comma.ai>` | `openpilot/common/version.h`, `pyproject.toml`, `tools/release/identity.sh` |
| Build reproducibility check | `check-dirty.sh` fails CI if the build changes tracked files | `tools/release/check-dirty.sh`, `.github/workflows/tests.yaml` |

## 3. Configuration items

| CI class | Members (paths) | Identification | Control level |
|---|---|---|---|
| CI-1 Source code (top-level) | `openpilot/**`, `system/**`, `tools/**`, `scripts/**`, `launch_*.sh`, `SConstruct` | Git commit SHA of LionDriver repo | Branch protection, PR review |
| CI-2 Submodules | `opendbc_repo`, `panda`, `msgq_repo`, `rednose_repo`, `teleoprtc_repo`, `tinygrad_repo` | Gitlink SHA in the superproject + `.gitmodules` URL | Forked under LionDriver control (§6) |
| CI-3 ML models | `openpilot/selfdrive/modeld/models/*.onnx`, `big_*_tinygrad.pkl` (LFS) | LFS `oid sha256` in the pointer file | Model change = SOTIF-relevant change (D-05) |
| CI-4 Parameter defaults | `openpilot/common/params_keys.h` (e.g. `ExperimentalMode` default `"1"` at line 43) | File content at commit | Safety-relevant (§4) |
| CI-5 Vehicle configuration data | `opendbc_repo/opendbc/car/toyota/{values,fingerprints,interface}.py`, `opendbc_repo/opendbc/car/torque_data/*.toml`, Toyota DBC sources and generated DBCs | File content at submodule commit | Safety-relevant; covered by [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md) |
| CI-6 Safety firmware | `panda/board/**`, `panda/SConscript` (build type), `panda/board/crypto/certs/*.pub` | Submodule SHA + built binary SHA-256 + panda version string `<builder>-<git8>-<RELEASE/DEBUG>` (`panda/SConscript` `get_version`) | ASIL path |
| CI-7 Build and CI configuration | `.github/workflows/*.yaml`, `Jenkinsfile`, `panda/Jenkinsfile`, `opendbc_repo/.github/workflows/*`, `tools/op.sh`, `tools/test_runner.py`, `tools/release/*` | File content at commit | Affects verification evidence |
| CI-8 Toolchain and dependency versions | `uv.lock`, `opendbc_repo/uv.lock`, `pyproject.toml`, `opendbc_repo/pyproject.toml`, `.python-version`, `launch_env.sh` (`AGNOS_VERSION` default 19.9) | Lockfile hashes; versions recorded in [WP-P-07](WP-P-07-tool-classification-qualification.md) | Change needs tool impact check |
| CI-9 Test references | Process-replay reference logs (today fetched from `commaai/ci-artifacts`), opendbc car-diff refs, MISRA `coverage_table` and `checkers.txt` | Ref commit + content hash | Fork-owned refs required (GAP-30) |
| CI-10 Work products | `assurance/**` | Commit SHA + document Version field | Per [WP-P-04](WP-P-04-documentation-management.md) |
| CI-11 Trace data | `assurance/trace/**` | Commit SHA | Per [WP-P-06](WP-P-06-requirements-management-traceability.md) |
| CI-12 Signing keys (public part) | `panda/board/crypto/certs/release.pub`, future LionDriver release key | Key fingerprint | Private keys never in Git (§10) |
| CI-13 Verification results | CI logs, coverage, MISRA and mutation reports, HIL and vehicle test records | Run ID + commit SHA, archived per [WP-P-10 §5](WP-P-10-release-management.md) | Retained (§10) |
| CI-14 Hardware configuration | Device hardware revision, harness type, vehicle VIN and ECU firmware versions | Recorded in [WP-C-01](../02-concept/WP-C-01-item-definition.md) | Changes need impact analysis |

## 4. Safety-relevant file list

A change that touches any path below is **safety-relevant** and follows the safety-relevant change route in [WP-P-02 §4](WP-P-02-change-management.md). All paths were checked to exist at `8b8c6ae` unless marked *(future)*.

### 4.1 Classes

| Class | Meaning | Review route |
|---|---|---|
| SR-A | Code or data in the ASIL path (envelope on the panda MCU) | Safety-relevant, ASIL; independent review per [WP-P-05](WP-P-05-verification-review-procedure.md) |
| SR-Q | QM or SOTIF element whose behaviour feeds hazards, configures the envelope, or affects FFI or cybersecurity | Safety-relevant, QM/SOTIF/CS |
| SR-T | Build, test, CI, toolchain or dependency configuration that changes verification evidence or the produced binary | Safety-relevant, tool impact |
| NSR | Anything not listed | Standard route |

### 4.2 Globs

```text
# SR-A: envelope (opendbc safety + panda firmware)
opendbc_repo/opendbc/safety/**
panda/board/**                      # excl. panda/board/body/** (comma body, not in scope) -> SR-T
panda/SConscript
panda/SConstruct

# SR-Q: Toyota port and car abstraction
opendbc_repo/opendbc/car/toyota/**
opendbc_repo/opendbc/car/interfaces.py
opendbc_repo/opendbc/car/lateral.py
opendbc_repo/opendbc/car/structs.py
opendbc_repo/opendbc/car/car.capnp
opendbc_repo/opendbc/car/values.py
opendbc_repo/opendbc/car/car_helpers.py
opendbc_repo/opendbc/car/fingerprints.py
opendbc_repo/opendbc/car/fw_versions.py
opendbc_repo/opendbc/car/fw_query_definitions.py
opendbc_repo/opendbc/car/vehicle_model.py
opendbc_repo/opendbc/car/can_definitions.py
opendbc_repo/opendbc/car/common/**
opendbc_repo/opendbc/car/torque_data/**
opendbc_repo/opendbc/can/**
opendbc_repo/opendbc/dbc/toyota_*.dbc
opendbc_repo/opendbc/dbc/generator/toyota/**

# SR-Q: onboard stack (QM / SOTIF-managed, FFI-relevant)
openpilot/selfdrive/selfdrived/**
openpilot/selfdrive/controls/**
openpilot/selfdrive/monitoring/**
openpilot/selfdrive/car/**
openpilot/selfdrive/pandad/**
openpilot/selfdrive/modeld/**       # includes models/** (LFS)
openpilot/selfdrive/locationd/**
openpilot/cereal/**
openpilot/common/params_keys.h
openpilot/common/realtime.py
openpilot/system/manager/process_config.py
openpilot/system/updated/**         # update path (CS)
openpilot/system/athena/**          # remote access (CS)
SECURITY.md

# SR-T: configuration, toolchain, verification
.gitmodules
.gitattributes
.lfsconfig
uv.lock
pyproject.toml
opendbc_repo/uv.lock
opendbc_repo/pyproject.toml
SConstruct
launch_env.sh
.github/workflows/**
opendbc_repo/.github/workflows/**
Jenkinsfile
panda/Jenkinsfile
panda/tests/**
panda/board/body/**
openpilot/selfdrive/test/process_replay/**
tools/op.sh
tools/test_runner.py
tools/release/**
.github/CODEOWNERS                  # (future)
assurance/trace/**                  # (future)
# Submodule pointer changes (gitlinks) for msgq_repo, rednose_repo, tinygrad_repo, teleoprtc_repo
```

Notes:

- `opendbc_repo/opendbc/safety/tests/**` is included under SR-A because the tests are the unit verification evidence ([WP-W-06](../05-software/WP-W-06-software-unit-verification.md)).
- A submodule bump changes every file in that submodule at once. It is classified by the highest class of any changed file inside the submodule diff.
- The list is reviewed at every gate and whenever [WP-W-03](../05-software/WP-W-03-software-architecture.md) or [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) changes the allocation (OI-2).

## 5. Branching model

| Branch | Role | Protection (to configure, see OI-3) |
|---|---|---|
| `liondriver-dev` | Integration branch. All changes enter by PR | No direct push; PR required; required status checks; CODEOWNERS review; linear history; no force push; no deletion |
| `feature/<issue>-<slug>`, `fix/<issue>-<slug>`, `claude/*` | Short-lived work branches | None |
| `sync/upstream-<YYYYMMDD>` | Upstream sync change requests (D-02) | As feature branch, but always SR route |
| `release/ld-vX.Y` | Release stabilisation, created at RC freeze | As `liondriver-dev`; only fixes cherry-picked by PR |
| `master` (submodule forks) | LionDriver-controlled line of each forked submodule | As `liondriver-dev` |

The upstream `master` branch name and the `release-*`/`nightly*` branches built by `tools/release/build_release.sh` are not used by LionDriver.

## 6. Submodule control (D-01)

| Step | Action | Closes |
|---|---|---|
| 1 | Fork `commaai/opendbc`, `commaai/panda`, `commaai/msgq`, `commaai/rednose`, `commaai/teleoprtc` and `tinygrad/tinygrad` into a LionDriver GitHub organization (today the `jherrodthomas` account; see OI-1) | GAP-29 |
| 2 | Change `.gitmodules` to absolute URLs of the forks. Remove `branch = master` from `tinygrad` | GAP-29 |
| 3 | Pin every submodule by SHA on the fork's protected default branch. The fork default branch starts at the current pin | GAP-29 |
| 4 | Replace `check-submodules.sh` logic (currently: "pin must be on `origin/master`") with a check that the pin is reachable from the protected branch of the LionDriver fork, and that the URL matches the approved list | GAP-29 |
| 5 | Apply the safety-relevant file list (§4) inside the opendbc and panda forks through their own CODEOWNERS | GAP-32 |
| 6 | Mirror LFS objects for the pinned models into a LionDriver-controlled LFS store and point `.lfsconfig` at it | CI-3 availability |

All six steps are implemented as change requests under [WP-P-02](WP-P-02-change-management.md); this plan does not modify `.gitmodules` itself.

## 7. Version scheme (closes GAP-35 when implemented)

| Element | Scheme |
|---|---|
| LionDriver release | `ld-vMAJOR.MINOR.PATCH` (SemVer). MAJOR: change of claimed scope or safety concept. MINOR: functional or safety-relevant change. PATCH: fixes with no change to safety requirements |
| Release candidate | `ld-vX.Y.Z-rcN` |
| Gate baseline | `ld-bl-G<n>-<YYYYMMDD>` (for example `ld-bl-G1-20270115`) |
| Upstream base | Recorded, not used as LionDriver version: "openpilot 0.11.2 base" |
| Version string on device | Proposed new define `LIONDRIVER_VERSION "X.Y.Z"` next to `COMMA_VERSION` in `openpilot/common/version.h`; displayed and logged. `build_release.sh` reads `version.h` with `awk`, so the change must keep that parse working (OI-4) |
| panda firmware | Built from the release tag; version string `LD-<git8>-RELEASE` by setting `BUILDER` in `panda/SConscript` (change request) |
| Work products | Document `Version` field (0.x draft, 1.0 first approval) per [WP-P-04](WP-P-04-documentation-management.md) |
| Identity | Replace `user@comma.ai` in `pyproject.toml` and `tools/release/identity.sh` with LionDriver identities (change request) |

Tags are annotated and signed (`git tag -s`). Tags are never moved or deleted; a wrong tag is superseded by the next PATCH.

## 8. Baselines

| Baseline | Content | Trigger | Record |
|---|---|---|---|
| Development baseline | `liondriver-dev` HEAD with submodule pins and lockfiles | Every merge | Git history |
| Gate baseline `ld-bl-G<n>-*` | Superproject commit + all submodule SHAs + LFS oids + `assurance/**` at the gate's approved status | Gate exit (G0–G6) | Gate record under `10-safety-case/` |
| Release baseline `ld-vX.Y.Z` | As gate baseline + built artifacts (panda firmware binary hash, model hashes) + evidence package | G5 release decision | [WP-K-06](../10-safety-case/WP-K-06-release-record.md) |

A baseline manifest (`baseline-manifest.yaml`, generated, stored with the tag's evidence package) lists: superproject SHA; each submodule path, URL and SHA; each LFS file path and oid; `uv.lock` and `opendbc_repo/uv.lock` SHA-256; toolchain versions from [WP-P-07](WP-P-07-tool-classification-qualification.md); `AGNOS_VERSION`; list of work products with version and status. Generator script: OI-5.

## 9. Status accounting

| Report | Content | Frequency | Owner |
|---|---|---|---|
| CI status | Required checks per PR | Per PR | Automated |
| Baseline manifest | §8 | Per gate and release | Configuration manager |
| Work product status | Status column of [WP-M-00](../01-management/WP-M-00-work-product-register.md) | Per merge touching `assurance/` | Author |
| Open change and problem reports | Issues by label (`change`, `problem`, `safety-relevant`) | Monthly and at gates | Configuration manager |
| Submodule drift | Distance of each fork from upstream (input to sync decisions) | Monthly | Configuration manager |

## 10. Backup, retention and access

| Item | Measure |
|---|---|
| Git repositories (superproject and forks) | Hosted on GitHub; weekly mirror (`git clone --mirror`) to a second location controlled by the maintainer; restore test at each gate |
| LFS objects | LionDriver-controlled LFS store (§6 step 6) plus offline copy of each released model |
| CI results | GitHub Actions artifacts expire (default retention is limited). Release evidence is exported to the evidence package (see [WP-P-10 §5](WP-P-10-release-management.md)) |
| Signing keys | Private release keys held offline (hardware token or encrypted offline storage), never in Git or CI secrets without a recorded decision. The committed debug key `panda/board/crypto/certs/debug` is not used for release builds (GAP-25) |
| Retention | Per [WP-P-04 §10](WP-P-04-documentation-management.md#10-retention) |
| Access | Write to protected branches: maintainers listed in CODEOWNERS only. 2FA required on the organization |

## 11. Configuration audits

| Audit | When | Checks |
|---|---|---|
| Functional configuration audit | Before G4 and G5 | Every requirement in `assurance/trace/` linked to passed verification at the baseline |
| Physical configuration audit | Before each release tag | Manifest matches repo state; submodule URLs are LionDriver forks; panda binary rebuilt from tag gives the same hash; no DEBUG panda build; models match recorded oids |
| CM process audit | Once per gate | Sample of merged PRs shows classification, impact analysis and required approvals; feeds [WP-M-05](../01-management/WP-M-05-quality-assurance-plan.md) |

## 12. Roles

| Role | Holder today |
|---|---|
| Configuration manager | Project maintainer (Jherrod Thomas) |
| Repository administrator | Project maintainer |
| Release manager | Project maintainer; second person required for release approval (see [WP-P-10](WP-P-10-release-management.md)) |

## 13. Open items

| ID | Item |
|---|---|
| OI-1 | Create the LionDriver GitHub organization and forks (D-01); decide whether the `jherrodthomas/LionDriver` repository moves into it |
| OI-2 | Keep the safety-relevant file list as a machine-readable file (proposed `assurance/trace/safety-relevant-files.txt`) so CI can classify PRs automatically |
| OI-3 | Configure and record branch protection on `liondriver-dev`; current settings were not verified from the local checkout |
| OI-4 | Change request for `LIONDRIVER_VERSION`, panda `BUILDER`, and identity replacements (GAP-35) |
| OI-5 | Write the baseline manifest generator and add it to the release procedure |
| OI-6 | Confirm that GitHub Actions artifact retention settings and the evidence export (WP-P-10 §5) together meet the retention in WP-P-04 §10 |
| OI-7 | LionDriver CI only runs `tools/test_runner.py` on `openpilot/` (`tools/op.sh test`). The opendbc safety suite, MISRA and mutation jobs live in `opendbc_repo/.github/workflows/tests.yml` and do not run in LionDriver CI. Add them to fork CI (D-03) |
| OI-8 | `tests.yaml` triggers on `push` to `master` and on `pull_request`; pushes to `liondriver-dev` are not tested. Add `liondriver-dev` to the push trigger |
