# WP-M-11 Upstream and Supplier Management

| Field | Value |
|---|---|
| Work product | WP-M-11 Upstream (comma.ai) and supplier management, development interface agreements |
| Standard reference | ISO 26262-8:2018 §5 (interfaces within distributed developments), with references to 8 §12, §13; ISO/SAE 21434:2021 §7 (distributed cybersecurity activities), §6 (reuse, off-the-shelf); ASPICE 4.0 ACQ.4 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (safety, SOTIF, CS) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose

LionDriver ships software, firmware, models and hardware that it did not develop. The normal ISO 26262-8 §5 and ISO/SAE 21434 §7 mechanism — a development interface agreement (DIA) or cybersecurity interface agreement with each supplier — is not available, because none of the upstream parties has a contract with LionDriver (tailoring **T-08**). This document:

1. lists every upstream source and supplier,
2. records what LionDriver consumes from each and why it matters,
3. states the evidence each one makes available,
4. assigns the supplier-side responsibilities to LionDriver,
5. defines the upstream synchronization procedure (decision **D-02**) and advisory monitoring,
6. records the constraints from comma.ai's fork policy and licences.

## 2. Principle: LionDriver assumes supplier responsibilities

Where a supplier would normally produce safety or cybersecurity work products under a DIA, LionDriver produces them itself, from the supplier's public artefacts, or records that they cannot be produced and argues the residual risk. No upstream statement (for example `docs/SAFETY.md:14-22`, which refers to a HARA and FMEA that are not published) is used as evidence unless the underlying work product is available and reviewed.

## 3. Inventory

Pins are from `.gitmodules`, `git submodule status` and the files named. Submodules marked "not initialized" were not present in the reviewed checkout ([gap assessment §1](../00-assessment/gap-assessment.md#1-scope-and-method)).

### 3.1 Software, firmware and models

| # | Upstream | Pin at baseline | What LionDriver consumes | Safety / SOTIF relevance | CS relevance | Evidence available | Qualification route |
|---|---|---|---|---|---|---|---|
| U-1 | comma.ai **openpilot** (`commaai/openpilot`) | LionDriver repo = upstream ≈ v0.11.2 (`openpilot/common/version.h`) + README change `8b8c6ae` | Entire application stack on the SoC: selfdrived, controls, planners, monitoring, modeld, pandad, card, manager, UI, updated, athenad, loggerd | QM stack, SOTIF-managed; DM is safety-relevant for controllability | High: update path, remote access, IPC, parameters (GAP-20, GAP-26, GAP-27) | Public source; CI workflows (`.github/workflows/tests.yaml`); unit, replay and onroad tests (onroad only on comma's Jenkins, `Jenkinsfile`); `RELEASES.md`; `docs/SAFETY.md`, `docs/LIMITATIONS.md` | Developed further by LionDriver under its own lifecycle (T-01); QM parts under 8 §12 or as part of LionDriver development ([WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md)) |
| U-2 | comma.ai **opendbc** (`commaai/opendbc`) | `opendbc_repo@229dc70` | Safety modes (`opendbc/safety/`), Toyota car port (`opendbc/car/toyota/`), DBC files, car interface library | **ASIL target**: safety envelope logic ([WP-M-01 §4](WP-M-01-assurance-strategy.md#4-safety-architecture-argument-the-central-strategy)) | Medium: message whitelists, SecOC handling | MISRA C:2012 checking, 100 % line-coverage gate (`opendbc/safety/tests/test.sh:36-43`), mutation testing (`opendbc/safety/tests/mutation.py`), Toyota safety tests (`opendbc/safety/tests/test_toyota.py`) | Re-verified to the HARA ASIL under T-03 (requirements back-filled, full verification) |
| U-3 | comma.ai **panda** (`commaai/panda`) | `panda@92eb565` | Safety MCU firmware (STM32H7): main loop, CAN/SPI drivers, heartbeat, relay, fault handling, bootstub, signing | **ASIL target**: the paths the envelope relies on | **High**: firmware authenticity (GAP-24, GAP-25), unauthenticated mode change (GAP-09) | MISRA on `board/main.c` (bootstub excluded, `panda/tests/misra/test_misra.sh:35`); HITL tests (`panda/tests/hitl/`) runnable only on hardware | Re-verified under T-03; firmware security reworked under [WP-M-09](WP-M-09-cybersecurity-plan.md) |
| U-4 | comma.ai **msgq** (`commaai/msgq`) | `msgq_repo@0e266c1` (not initialized) | Shared-memory IPC and VisionIPC between all processes | Freedom-from-interference relevance (corruption, stale data) | Medium: no authentication between local processes (GAP-20) | Public source, upstream tests | QM, 8 §12 ([WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md)); FFI analysis in [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) |
| U-5 | comma.ai **rednose** (`commaai/rednose`) | `rednose_repo@8671c17` (not initialized) | Kalman-filter library used by `locationd` (`openpilot/selfdrive/locationd/models/pose_kf.py:8-13`) | QM; localization feeds calibration and control | Low | Public source | QM, 8 §12 |
| U-6 | comma.ai **teleoprtc** (`commaai/teleoprtc`) | `teleoprtc_repo@1aa8fc4` (not initialized) | WebRTC session building for `webrtcd` (`openpilot/system/webrtc/webrtcd.py:232, 594`) | None if streaming is disabled | Medium: camera streaming, remote input path | Public source | QM; candidate for removal from the reference configuration ([WP-M-09](WP-M-09-cybersecurity-plan.md) OI-2) |
| U-7 | **tinygrad** (`tinygrad/tinygrad`, not a comma repository) | `tinygrad_repo@d3f09c9`, **tracks `branch = master`** in `.gitmodules` | Model compiler (`compile_onnx.py`, `compile_warp.py`) and inference runtime; model pickle loader | Tool and runtime for all AI components ([WP-M-10](WP-M-10-ai-safety-plan.md)); TCL candidate 2–3 (GAP-34) | Medium: pickle deserialization (GAP-22) | Public source and tests; no release discipline relied upon | Pin by commit (D-01); tool classification [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md); runtime as QM component |
| U-8 | comma.ai **model artefacts** | LFS pointers in `openpilot/selfdrive/modeld/models/` | Driving (standard and big) and DM models | See [WP-M-10 §3](WP-M-10-ai-safety-plan.md#3-allocation-and-safety-relevance) | Integrity of artefacts | LFS hashes only; no model card, data description or evaluation report | Acquired pre-trained model route ([WP-M-10 §5](WP-M-10-ai-safety-plan.md#5-the-acquired-pre-trained-model-route)) |
| U-9 | **comma-deps** toolchain and native wheels | Pinned by hash in `uv.lock`; listed in `pyproject.toml:29-69` | `gcc-arm-none-eabi` 13.2.1 (panda firmware compiler), capnproto, acados, ffmpeg, zstd, zeromq, raylib and others | Compiler for ASIL code: TCL 2–3 (GAP-34) | Supply-chain integrity | Hash pins; no qualification evidence | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md); consider an independently sourced compiler build for cross-checking |
| U-10 | **cppcheck** fork for MISRA checking | `cppcheck @ git+https://github.com/commaai/dependencies.git@release-cppcheck` (`opendbc_repo/pyproject.toml:45`) — mutable branch | Static analysis for MISRA evidence | Verification tool for ASIL code | Supply-chain | None beyond upstream use | Pin to a commit; WP-P-07 |
| U-11 | **AGNOS** operating system | 19.9 (`launch_env.sh:19`); images and hashes in `openpilot/system/hardware/comma/agnos.json` (path read by the updater, `openpilot/system/updated/updated.py:221`; symlink to `openpilot/common/hardware/comma/agnos.json`); updater binary `openpilot/common/hardware/comma/updater` (LFS) | Linux kernel, drivers, bootloader chain, system services on the SoC | Platform for the QM stack; timing and FFI | High: privileged OS, update mechanism | Image hashes and download URLs (`commadist.azureedge.net`); no published security documentation reviewed | Off-the-shelf component with CS assumptions ([WP-M-09 §6](WP-M-09-cybersecurity-plan.md#6-reuse-open-source-and-off-the-shelf-components)); version pinned per release |
| U-12 | Third-party open-source Python/native packages | `uv.lock` (hash-pinned) | Runtime libraries (numpy, pycapnp, etc.) and development tools | QM | Vulnerability exposure | Hash pins | SBOM and vulnerability scanning (WP-M-09); QM 8 §12 where safety-relevant processes use them |

### 3.2 Hardware

| # | Supplier / product | What LionDriver consumes | Safety relevance | Evidence available | Route |
|---|---|---|---|---|---|
| HW-1 | comma.ai **comma 3X** (panda board file `panda/board/boards/tres.h`) or **comma four** (`panda/board/boards/cuatro.h`) — one revision to be fixed in [WP-C-01](../02-concept/WP-C-01-item-definition.md) | SoC, cameras, integrated STM32H7 safety MCU, power, relay, enclosure | Hosts the ASIL-target envelope; single channel with shared power and PCB (WP-M-01 §4.2) | Board configuration in firmware source; no schematics, FMEDA or reliability data reviewed | 8 §13 hardware component qualification ([WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md)) with LionDriver FMEDA ([WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md)) — T-04 |
| HW-2 | comma.ai **Toyota harness** | Connection to camera-ECU CAN, relay insertion | Relay and wiring faults (GAP-12) | None | WP-H-07 |
| HW-3 | STMicroelectronics **STM32H7** (via the comma device) | MCU safety features | Basis of HW metrics | Public datasheet and reference manual; safety manual availability to be confirmed | Input to WP-H-03/H-04; 26262-11 informative |
| HW-4 | comma.ai **Chestnut** external GPU and its firmware (`openpilot/system/hardware/chestnut/firmware_wrapped.bin`, version in `openpilot/common/hardware/usb.py`) | Big-model inference (optional accessory) | Fallback hazard (GAP-17) | None | Proposed exclusion from the reference configuration ([WP-M-10](WP-M-10-ai-safety-plan.md) OI-2) |

### 3.3 Services

| # | Service | Used for | Relevance | Route |
|---|---|---|---|---|
| SV-1 | comma **athena** server (`wss://athena.comma.ai`, `openpilot/system/athena/athenad.py:51`) | Remote RPC, SSH tunnel, streaming | CS (GAP-27) | External entity with assumptions (T-11); disable or constrain ([WP-M-09](WP-M-09-cybersecurity-plan.md) OI-2) |
| SV-2 | comma **API / connect** (`https://api.commadotai.com`, `openpilot/common/api.py:8`) and uploader | Device registration, log upload | CS and privacy; field-data ownership | As SV-1; LionDriver log store ([WP-M-08](WP-M-08-sotif-plan.md) OI-4) |
| SV-3 | comma **CDN** (`commadist.azureedge.net`) | AGNOS images | CS (update integrity) | Hash-verified images; mirror under LionDriver control to be considered |
| SV-4 | comma **CI artefacts** (`commaai/ci-artifacts`, `openpilot/selfdrive/test/process_replay/test_processes.py:70`) and test routes (`openpilot/tools/lib/openpilotci.py`) | Process-replay references and test routes | Verification evidence depends on them (GAP-30) | Replace with fork-owned references (D-03) |
| SV-5 | **GitHub** | Code hosting, CI runners, update source for `updated` | CM and CS | Configuration in [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md); update source replaced per WP-M-09 OI-3 |

### 3.4 Not suppliers

Toyota and the vehicle's ECUs (EPS, ECM, brake, radar, camera) are **existing elements outside the item** (T-02). They are handled by Assumptions of Use in [WP-C-01](../02-concept/WP-C-01-item-definition.md) and vehicle testing, not by supplier management.

## 4. Why no DIA is possible, and what replaces it

| DIA element (ISO 26262-8 §5 / 21434 §7) | Normal content | Status with upstreams | LionDriver replacement |
|---|---|---|---|
| Supplier selection and capability evaluation | Evaluate supplier process capability | Upstreams are open-source projects or a vendor with no contract. comma.ai publishes no safety or CS process | One-time capability note per upstream (this document §3) and the [ASPICE baseline (WP-M-13)](WP-M-13-aspice-capability-baseline.md) for the code LionDriver inherits |
| Appointment of safety / CS managers on both sides | Named counterparts | None upstream | LionDriver's safety manager and CS manager act for both sides |
| Tailored lifecycle and work products to exchange | Agreed list | Nothing is delivered except source, binaries and commit history | LionDriver produces all work products in [WP-M-00](WP-M-00-work-product-register.md) |
| Target values, ASIL and requirements on the supplier's element | Communicated by customer | Upstream has no knowledge of LionDriver requirements | Requirements apply to LionDriver's fork of the element; verified by LionDriver |
| Joint change management and notification | Supplier notifies changes | Upstream changes daily without notice ([WP-M-12 §6](WP-M-12-impact-analysis.md)) | Sync procedure §5 |
| Problem and vulnerability notification | Contractual | Best effort via public issue trackers and `SECURITY.md` (routes to comma) | Advisory monitoring §6 |
| Confirmation measures at supplier | Supplier audit/assessment | Not possible | External assessor reviews LionDriver's handling instead |

### 4.1 Responsibility split

| Activity | comma.ai / other upstream | LionDriver |
|---|---|---|
| Hazard analysis, safety goals, FSC, TSC | — | R (performs and owns) |
| Requirements for envelope code (opendbc safety, panda) | — | R |
| Implementation of upstream features | Performs for its own purposes, no obligation | Selects which changes to take (§5) |
| Verification of the LionDriver baseline (safety tests, MISRA, mutation, HIL, replay) | Upstream CI results are informative only | R |
| Hardware qualification and FMEDA | — | R |
| Tool qualification | — | R |
| Vulnerability monitoring and response | Publishes fixes at its discretion | R (monitor, triage, patch, release) |
| Field monitoring of LionDriver users | — | R |

## 5. Upstream synchronization procedure (D-02)

Upstream is **frozen** at the baseline. Upstream code enters LionDriver only through a deliberate "sync" change request ([WP-P-02](../07-supporting/WP-P-02-change-management.md)).

| Step | Action | Output |
|---|---|---|
| 1 | Open a sync change request naming the upstream repository and target commit (never a branch head) | Change request |
| 2 | Produce the commit list and full diff between the current pin and the target, including submodule diffs. Fetch enough history to inspect submodule ranges (the baseline checkout is shallow; see [WP-M-12](WP-M-12-impact-analysis.md) OI-2) | Diff record |
| 3 | Classify every changed file against the safety-relevant file list in [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md). Inspect at diff level: commit titles are not sufficient (example: `d05c2d9` "bump tinygrad" also reverted `a0d47bc` and rebuilt the big models) | Classified file list |
| 4 | Complete the impact analysis template ([WP-M-12 §7](WP-M-12-impact-analysis.md)): safety, SOTIF, AI, CS relevance; affected hazards and work products; required actions | Impact analysis |
| 5 | Decide per change: take, take with modification, or reject. Cherry-picking is allowed; the record says which upstream commits are and are not included | Decision record |
| 6 | Re-run verification: opendbc safety tests with coverage gate, MISRA, mutation tests, panda MISRA; fork-owned process replay and model replay; HIL bench once available (D-04); for model changes, the [WP-M-10 §9](WP-M-10-ai-safety-plan.md#9-model-change-control-d-05) steps | Verification results attached to the change request |
| 7 | Update the affected work products (requirements, analyses, hazard log, CS case, safety case) or record why none are affected | Updated WPs |
| 8 | Review and approve per [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md); merge; update the baseline record | Approved sync, new baseline |

**Tooling.** `tools/sync/sync_report.py <repo> --to <upstream commit>` does steps 2 and 3. It fetches upstream history without file contents, lists every commit and changed file in the range, classifies each file against [`safety-relevant-paths.txt`](../07-supporting/safety-relevant-paths.txt), and writes a step-4 skeleton (the WP-M-12 §7.3 template) to [`07-supporting/impact/`](../07-supporting/impact/README.md). The generated report does not replace reading the diffs.

**Sync cadence (D-02, decided 2026-10-10).**

- **Planned sync: once per MINOR release** (`ld-vX.Y.0`). It is done before the release-candidate freeze ([WP-P-10](../07-supporting/WP-P-10-release-management.md)), so the sync's verification and work-product updates are part of that release's evidence.
- **Planned sync scope:** every forked submodule and the superproject. Run `tools/sync/sync_report.py` for each against an exact upstream commit, then take, modify or reject each change according to steps 4–5 above.
- **No change taken:** a planned sync may conclude that nothing is taken. The report is still recorded.
- **Only out-of-cycle exception:** a targeted cherry-pick when a security advisory affects a pinned component (§6), or when upstream fixes a safety-relevant defect that affects the reference configuration. It follows the same procedure.
- **Outside these:** no upstream code is pulled, including to stay current or to pick up features.

**Initial proposal for the safety-relevant file classes** (authoritative list in WP-P-01): `opendbc_repo/opendbc/safety/**`, `opendbc_repo/opendbc/car/toyota/**`, `opendbc_repo/opendbc/car/{interfaces,lateral}.py`, `panda/board/**`, `openpilot/selfdrive/{selfdrived,controls,monitoring,modeld,pandad,car}/**`, `openpilot/common/params_keys.h`, `openpilot/cereal/log.capnp`, `openpilot/system/manager/process_config.py`, `openpilot/system/{updated,athena,webrtc}/**`, `openpilot/selfdrive/ui/soundd.py`, alert definitions (`openpilot/selfdrive/selfdrived/events.py`), model artefacts, `tinygrad_repo` pin, `uv.lock`, `openpilot/system/hardware/comma/agnos.json` (path read by the updater, `openpilot/system/updated/updated.py:221`; symlink to `openpilot/common/hardware/comma/agnos.json`), `launch_env.sh`, `.gitmodules`.

## 6. Monitoring upstream security advisories and safety-relevant changes

| What | Where | Frequency | Action |
|---|---|---|---|
| Security advisories and security-labelled fixes | GitHub repositories of U-1…U-7, U-10 | Weekly automated advisory watch ([WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) SCAN-04), monthly manual review, plus immediately on notification | Triage under [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md); a sync change request if affected |
| Safety-relevant upstream changes (safety modes, Toyota port, panda firmware, DM policy) | Commit history of U-1…U-3 | Monthly | Log in the upstream watch list; may trigger a sync |
| Reverts of earlier fixes | Commit history | Monthly | Check whether LionDriver took the original fix |
| Vulnerabilities in pinned third-party packages and AGNOS components | Public vulnerability databases against the SBOM | Weekly automated scan (WP-W-11 SCAN-03), monthly manual review, and per release | WP-O-05 |
| Changes to comma's fork policy or service terms | `docs/SAFETY.md`, comma terms | Per sync | Re-check §7 |

The watch list and its review records are kept under `01-management/` (format to be decided, OI-3).

## 7. Fork policy, trademark and licence constraints

`docs/SAFETY.md:36-46` sets conditions for forks:

| Upstream condition | Effect on LionDriver | LionDriver position |
|---|---|---|
| Do not disable or weaken driver monitoring (`docs/SAFETY.md:38`) | DM changes must strengthen, not relax | Consistent with LionDriver goals. DM changes (e.g. GAP-21 fixes) are reviewed against this condition |
| Do not disable or weaken excessive-actuation checks (`docs/SAFETY.md:39`) | Same | Same |
| A fork that modifies `opendbc/safety/` cannot use the openpilot trademark (`docs/SAFETY.md:40-41`) | The envelope hardening backlog (GAP-01…GAP-09) modifies `opendbc/safety/` | LionDriver uses its own name. User-facing text, release names and the README must not present LionDriver as openpilot. Factual attribution ("derived from openpilot") is kept |
| Such a fork must keep the full safety test suite and all tests must pass, including new coverage for the fork's changes (`docs/SAFETY.md:42`) | Constrains how tests may be changed | Adopted as a LionDriver rule: no safety test is removed; every safety-code change adds tests; the coverage gate stays at 100 % line (and LionDriver adds branch/MC/DC per [WP-W-06](../05-software/WP-W-06-software-unit-verification.md)) |
| Non-compliance may get the fork and its users banned from comma.ai servers (`docs/SAFETY.md:44`) | Loss of athena, connect, uploads | LionDriver must not depend on comma servers for any safety, SOTIF or CS function; consistent with T-11 and the CS plan |

**Licences.** The repository is under the MIT licence (`LICENSE`, "Copyright (c) 2018, Comma.ai, Inc."). LionDriver keeps the copyright and permission notices in all copies. Licences of each submodule and of model artefacts are to be confirmed (OI-4). The MIT licence's "as is" terms confirm that no warranty or supplier obligation exists.

## 8. Records

| Record | Location |
|---|---|
| Inventory (this document) | `01-management/WP-M-11-upstream-and-supplier-management.md` |
| Sync change requests and impact analyses | Pull requests per WP-P-02, with analyses per WP-M-12 §7 |
| Upstream watch list and review log | `01-management/` (OI-3) |
| Baseline pins | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md) |

## Open items

| ID | Item |
|---|---|
| OI-1 | Fork opendbc and panda under LionDriver control and change `.gitmodules` to absolute URLs (D-01). Decide whether msgq, rednose and teleoprtc are also forked, since their relative URLs resolve to `commaai/*` as well |
| OI-2 | Pin tinygrad by commit and cppcheck (`release-cppcheck` branch) by commit |
| OI-3 | Define the format and location of the upstream watch list and its review log |
| OI-4 | Confirm the licences of all submodules and of the model artefacts, and record any redistribution constraints |
| OI-5 | Fix the comma device type and hardware revision for the reference configuration (WP-C-01) and request any available hardware documentation from comma.ai; record the answer |
| OI-6 | Ask comma.ai whether any safety, CS or model documentation can be shared; record the answer (shared with [WP-M-10](WP-M-10-ai-safety-plan.md) OI-7) |
| OI-7 | Decide whether to mirror AGNOS images and the toolchain wheels under LionDriver control |
