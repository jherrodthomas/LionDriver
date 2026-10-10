# WP-M-12 Impact Analysis of the openpilot-Derived Baseline

| Field | Value |
|---|---|
| Work product | WP-M-12 Impact analysis of the openpilot-derived baseline (modification of existing item) |
| Standard reference | ISO 26262-2:2018 §6 (impact analysis, tailoring); ISO 26262-8:2018 §8 (change management); ISO/SAE 21434:2021 §6 (reuse analysis); ISO 21448:2022 §4 (interface); ASPICE 4.0 SUP.10 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (FuSa, SOTIF, AI, CS) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review of the tailoring conclusion (§5) by the external assessor |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose

Tailoring decision **T-01** treats LionDriver as a **modification of an existing item** (openpilot). ISO 26262-2 §6 requires an impact analysis to decide which lifecycle activities are needed. This document:

1. identifies the existing item and its configuration (§2),
2. lists the intended LionDriver modifications (§3) and differences in operational environment (§4),
3. concludes which work products can be reused (§5),
4. analyses the upstream changes visible in the baseline history (§6),
5. defines the procedure and template for future impact analyses, used for every upstream sync ([WP-M-11 §5](WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02)) and every safety-relevant change ([WP-P-02](../07-supporting/WP-P-02-change-management.md)) (§7).

It also serves as the ISO/SAE 21434 §6 reuse analysis for the inherited code.

## 2. The existing item

| Attribute | Value | Source |
|---|---|---|
| Name | openpilot (comma.ai), supervised Level 2 ACC + ALC system | `docs/SAFETY.md:3-5` |
| Version | ≈ 0.11.2 (release notes dated 2026-08-12), plus upstream master commits to 2026-10-08 | `openpilot/common/version.h`; `RELEASES.md:1`; `git log` |
| Repository commit | `655bfde` (last upstream commit); LionDriver `8b8c6ae` changes only `README.md` | `git log` |
| Submodules | `opendbc_repo@229dc70`, `panda@92eb565`, `msgq_repo@0e266c1`, `rednose_repo@8671c17`, `teleoprtc_repo@1aa8fc4`, `tinygrad_repo@d3f09c9` | `git submodule status` |
| OS | AGNOS 19.9 | `launch_env.sh:19` |
| Hardware | comma 3X / comma four with integrated panda (STM32H7) | `panda/board/boards/tres.h`, `cuatro.h` |
| Vehicle scope upstream | All supported brands and models (`docs/CARS.md`), worldwide | — |
| Available safety work products | None. `docs/SAFETY.md:21-28` refers to a HARA and FMEA that are not published; two informal safety requirements are stated | [Gap assessment §2](../00-assessment/gap-assessment.md#2-summary) |
| Available verification evidence | Source-level tests in the repository; upstream CI logs (not retained by LionDriver); device/HIL results exist only on comma's Jenkins | GAP-30 |

**History visibility.** The checkout is shallow (`.git/shallow` = `8377c40`). Commit `8377c40` is a graft root that imports the whole tree, so only the 48 upstream commits after it (2026-09-22 … 2026-10-08) can be analysed as deltas. Everything before is analysed as one unit: the baseline itself.

## 3. Intended modifications (fork-specific)

| # | Modification | Category | Affected elements | Planned in |
|---|---|---|---|---|
| M-1 | Scope claims to the reference configuration: one vehicle (`TOYOTA_COROLLA_TSS2`), one device revision, pinned software, defined ODD | Scope restriction | Item definition, configuration | [WP-C-01](../02-concept/WP-C-01-item-definition.md), [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) |
| M-2 | Lock the safety mode and parameter for the reference configuration in panda firmware or add an independent cross-check | Safety mechanism (envelope) | `panda/board/main_comms.h:222-225` | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (GAP-09) |
| M-3 | Envelope hardening backlog: IWDG, fault → safe state, gate debug relay command, driver-torque and EPS-status monitoring, RX E2E strategy, limit rationale | Safety mechanisms | `opendbc_repo/opendbc/safety/**`, `panda/board/**` | WP-S-02, [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) (GAP-01…GAP-08) |
| M-4 | Change defaults: Experimental Mode off; possibly exclude Chestnut big model | SOTIF functional modification | `openpilot/common/params_keys.h:43`, release build flags | [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md) (D-08, GAP-17, GAP-18) |
| M-5 | Fix soft-disable window, missing event reactions and DM weaknesses | SOTIF / FuSa | `openpilot/selfdrive/selfdrived/`, `monitoring/` | WP-C-07 (GAP-16, GAP-19, GAP-21) |
| M-6 | AI runtime monitors and model integrity check | SOTIF / AI / CS | `openpilot/selfdrive/modeld/` | [WP-M-10 §7](WP-M-10-ai-safety-plan.md#7-runtime-monitoring-gap-22) |
| M-7 | Firmware security: LionDriver release build and signing, no debug key in release, RDP/WRP | CS | `panda/board/crypto/`, `panda/SConscript`, bootstub | [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) (GAP-24, GAP-25) |
| M-8 | Replace or constrain update path and remote access; LionDriver vulnerability intake | CS | `openpilot/system/updated/`, `openpilot/system/athena/`, `SECURITY.md` | [WP-M-09](WP-M-09-cybersecurity-plan.md) (GAP-26…GAP-28) |
| M-9 | Configuration control and CI for the fork | Process | `.gitmodules`, `.github/workflows/*`, `Jenkinsfile` | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md), D-01, D-03 (GAP-29…GAP-32) |
| M-10 | LionDriver versioning and identity | Process | `openpilot/common/version.h`, `pyproject.toml` | WP-P-01 (GAP-35) |

## 4. Differences in operational environment and use

| Aspect | Upstream openpilot | LionDriver reference configuration | Consequence |
|---|---|---|---|
| Vehicles | Hundreds of models, many brands | One model, one trim | Claims and evidence only for the Corolla; other car ports are dead code for claims |
| Market | Worldwide | US only | US regulations and crash baselines (T-13) |
| ODD | Not specified | Specified and restricted (WP-C-02) | Behaviour outside ODD must be detected or the driver informed |
| Users | General public, self-installed | Development phase: trained safety drivers only (WP-V-07) | Different misuse profile; WP-C-08 addresses both phases |
| Defaults | Experimental Mode on (`f21bfc3`) | Proposed off | Different longitudinal behaviour from upstream |
| Back end | comma servers (athena, connect, uploads, updates) | Independent of comma servers for any safety, SOTIF or CS function | Field data and updates must be provided by LionDriver |
| Verification infrastructure | comma device farm, private routes | None today (GAP-30) | Fork must build HIL bench and own references (D-03, D-04) |
| Hardware accessories | Chestnut eGPU supported | Proposed excluded | Removes fallback hazard path |

## 5. Conclusion on reuse of work products

No ISO 26262, ISO 21448, ISO/SAE 21434 or ISO/PAS 8800 work products exist for the existing item. The impact analysis therefore cannot limit the lifecycle to the modified parts. **The full lifecycle applies** (concept → validation and release) for the reference configuration, as already recorded in T-01.

| Inherited artefact | Reuse status |
|---|---|
| `docs/SAFETY.md` safety requirements | Input to WP-C-04/WP-S-02 only; not reused as a work product |
| `docs/LIMITATIONS.md`, `docs/INTEGRATION.md` | Input to WP-C-02, WP-C-06, WP-O-03 |
| opendbc safety tests, MISRA configuration, mutation tests | Reused as verification **means**; results must be regenerated by LionDriver and traced to requirements (WP-W-06) |
| Process replay, model replay, maneuver tests, simulator bridge | Reused as tools after classification (WP-P-07) and with fork-owned references |
| Upstream CI results | Informative only; not evidence |
| openpilot fleet history | Supporting evidence only (T-06, [WP-P-09](../07-supporting/WP-P-09-proven-in-use.md)) |

## 6. Initial impact analysis of upstream changes in the baseline window

Range: `8377c40..655bfde` (48 upstream commits, 2026-09-22 … 2026-10-08), excluding the LionDriver README commit `8b8c6ae`. Each commit's diff was inspected with `git show`. "SR" = safety-relevant (FuSa, SOTIF, AI or CS) **for the reference configuration**.

### 6.1 Safety-relevant changes

| Commit | Change | SR | Affected hazards / findings | Affected WPs | Required action |
|---|---|---|---|---|---|
| `f21bfc3` | Experimental Mode default `"1"` (`openpilot/common/params_keys.h:43`); confirmation dialogs removed (`selfdrive/ui/layouts/settings/toggles.py`, `selfdrive/ui/mici/layouts/settings/toggles.py`); onroad button toggles without confirmation (`selfdrive/ui/onroad/exp_button.py`). The description no longer says "alpha quality" but keeps "Mistakes should be expected" | Yes (SOTIF, HMI) | Model-controlled longitudinal behaviour becomes default: unexpected braking, failure to stop, red-light/stop-sign handling contrary to `docs/LIMITATIONS.md:35`; mode confusion. GAP-18 | WP-C-02, C-05, C-06, C-07, C-08, O-03, V-03 | Revert default for the reference configuration pending SOTIF evaluation (M-4, D-08) |
| `ab8c84c` | Gas-override acceleration boost: adds up to +0.2 m/s² to the end-to-end acceleration target after driver gas overrides (`selfdrive/controls/lib/accel_boost.py:5-8`), applied in the planner (`longitudinal_planner.py:140`). Eligibility requires Experimental Mode (`accel_boost.py:23-24`). Final target still clipped to `ACCEL_MIN/ACCEL_MAX` (`longitudinal_planner.py:149`) and the panda bound +2.0 m/s² (`toyota.h:207-210`) | Yes (SOTIF) | Higher acceleration than the model requested; learned behaviour from driver input persists while engaged; behavioural adaptation | WP-C-06, C-08, V-03 | If Experimental Mode is off (M-4), show by test that boost stays 0; otherwise analyse as FI and validate |
| `948ad05` | After `bigModelFailed`, resets `big_model_ready_t` (`selfdrive/selfdrived/selfdrived.py:175`), which extends the 5 s window in which `commIssue`, localization and `modeldLagging` checks are suppressed (`selfdrived.py:382-384, 403, 457`); `modeldLagging` newly masked during settling | Yes (FuSa/SOTIF) | Diagnostics masked right after a model failure while actuating on a cold small model. GAP-17 | WP-C-06, C-07, S-04, W-04 | Exclude Chestnut (M-4) or remove suppression after failure |
| `a0d47bc`, `d05c2d9` | `a0d47bc` added `drop_chestnut()` on fallback; `d05c2d9` ("bump tinygrad") silently reverts it, bumps `tinygrad_repo` `9d0446a → d3f09c9`, changes `input_view` in `modeld.py`, and rebuilds all three big-model artefacts (new LFS hashes) | Yes (AI, model runtime) | Model runtime change affects AI-1 and AI-3 as well (shared tinygrad); big-model behaviour changes | WP-M-10, W-10, V-03, P-07 | Treat as model change (D-05): replay comparison, re-run model tests. Process lesson: bump commits must be read at diff level (§7) |
| `4bcf732`, `0e0c7c7`, `f59056e` | Big-model weights replaced ("ResAction"), replaced again ("Mountain Dew"), reverted the same day | Yes (AI) if Chestnut in scope | Changed driving behaviour without accompanying evidence in the repository | WP-M-10, C-06, V-03 | D-05 process; no action if Chestnut excluded |
| `c5543b1` | `modeld` real-time scheduling moved after model load; `gc.disable()` earlier (`modeld.py`) | Yes (timing, low) | Applies to the standard model path too; affects start-up timing only | WP-S-04 | Confirm in timing analysis |
| `bbabd94`, `027770d`, `afa4703` | Chestnut enabled when a USB cable is connected even before enumeration, with a 10 s wait (`helpers.py` `wait_for_chestnut`); timeout mechanism changed; fallback condition now `model.chestnut` | Yes if Chestnut in scope | Start-up and fallback behaviour of AI-2 | WP-M-10, C-06 | Covered by Chestnut decision |
| `910c08e` | Reverts an SPI turnaround delay in `selfdrive/pandad/spi.cc` (code that carried a TODO to fix turnaround synchronization at protocol level). Rationale of the original change (#38464) and of the revert is not visible | Yes (FFI, host–safety-MCU comms) | SPI errors between host and panda; relates to GAP-10 | WP-A-02, S-05, W-07 | Record `spiErrorCount` in test drives; analyse in WP-A-02; obtain upstream rationale (OI-3) |
| `28917bb`, `f00d226` | Louder alerts (`AMBIENT_DB` 26 → 22 in `selfdrive/ui/soundd.py`); new max critical sound after 8 s; ramp extended to `warningSoft` | Yes (HMI, controllability) — expected to be beneficial | Driver warning effectiveness | WP-C-08, O-03 | Include in HMI analysis; verify audibility in the reference cabin |
| `d2c0ce9` | `pandad` reports NMI and hard-fault resets of the panda (`cereal/log.capnp`, `pandad.cc`) | Yes (diagnostic observability, beneficial) | Visibility of panda resets; no reaction added | WP-O-04, V-05 | Use in field monitoring and fault-injection evidence |
| `ec95db3`, `0e57181` | opendbc bumped `4134c0d → 35f7e08 → 229dc70` | **Unknown** — opendbc contains the safety modes and Toyota port | Possibly envelope or Toyota changes | WP-W-02…W-06 | Cannot inspect: the submodule clone is shallow and the earlier commits are absent. Fetch and diff `opendbc/safety/` and `opendbc/car/toyota/` (OI-2). `229dc70` is titled "VW MEB: use HMS_Status for hold" |
| `134517c` | AGNOS 19.8 → 19.9: new boot and system images (`agnos.json`, `launch_env.sh`) | Yes (CS, platform) | OS/kernel change; content not visible | WP-M-09, S-04 | Record OS version in release manifest; review AGNOS change notes if available (OI-4) |
| `4dbdd66` | AGNOS updater binary replaced (LFS blob `openpilot/common/hardware/comma/updater`) | Yes (CS) | Privileged binary from upstream | WP-M-09 | Record hash; off-the-shelf component handling |
| `a742df6` | Chestnut firmware binary updated (`firmware_wrapped.bin`, `CHESTNUT_FW_VERSION`) | Yes (CS) if Chestnut in scope | Opaque firmware | WP-M-09 | Covered by Chestnut decision |

### 6.2 Changes classified not safety-relevant for the reference configuration

| Commits | Change | Reason |
|---|---|---|
| `7ee974a` | Curvature saturation alert in `latcontrol_curvature.py` | Only used by curvature-controlled cars (`controlsd.py:58-59`); the Corolla uses the torque controller (`opendbc_repo/opendbc/car/toyota/interface.py:47`) |
| `3f06ed3`, `f89ce23`, `b78331e`, `0c464e5`, `8d1865b`, `c8fb906`, `043759d` | Chestnut offroad alerts, UI icon, nightly build jobs (note `c8fb906` builds `nightly-chestnut-dev` with `PANDA_DEBUG_BUILD=1`), onroad fallback test | Chestnut-only or comma CI; no effect if Chestnut is excluded. `043759d` adds evidence only runnable on comma hardware |
| `035a447`, `5b2a59d`, `78dccf0`, `46b97e6`, `01a670d` | UI visual changes (longitudinal indicator, lead bar, bookmark, camera speed gates, keyboard) | Informational HMI only. Re-check in WP-C-08 if the comma four (`mici`) UI is in the reference configuration |
| `9b585d5` | Metered-network detection for comma SIM | Connectivity only |
| `cce54f2` | Log schema: deprecated `initData` fields | Logging; check log tooling compatibility |
| `f804d34`, `6846d73`, `c933446`, `2b7c34a`, `fc61640`, `84f9bdb` | jotpluggler log viewer | Tools; relevant only if used to produce evidence (WP-P-07) |
| `655bfde`, `a86351c`, `657d3a4`, `49bbba3`, `f474f05` | Model-replay PR bot, process-replay route, athena test fix, build messages | Test/build tooling; process-replay references are comma-hosted |

### 6.3 Observations

- In 17 days upstream changed the default driving mode, added a behaviour-learning acceleration term, changed model weights four times, bumped the model runtime, reverted a host–panda comms change, and bumped the safety-code submodule twice. This confirms GAP-37 and the need for the D-02 freeze.
- Two of the safety-relevant changes were hidden behind unrelated titles (`d05c2d9` reverted `a0d47bc`; `948ad05` "fix offroad alert" extended diagnostic suppression).
- No commit in the window touched `driving_supercombo.onnx` or `dmonitoring_model.onnx`.

## 7. Procedure and template for future impact analyses

### 7.1 When an impact analysis is required

1. Every upstream sync ([WP-M-11 §5](WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02)).
2. Every change request that touches a file on the safety-relevant file list ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)).
3. Any change to the reference configuration (vehicle, device, ODD, defaults).
4. Any model, model-runtime or AI-toolchain change (D-05).

A pull request touching safety-relevant code without an impact analysis is not merged ([README](../README.md#changing-a-work-product)).

### 7.2 Procedure

1. Identify the range (from-pin → to-pin) for the repository and each submodule. Ensure enough history is fetched to diff submodules.
2. List commits and changed files; classify files against the safety-relevant list.
3. Read every diff in a safety-relevant file. Do not rely on commit titles.
4. Fill in one row of the template per commit (or per coherent group).
5. Decide the required action; open follow-up change requests or problem reports.
6. Have the analysis reviewed (I1 minimum; I2 for changes to ASIL-allocated code once WP-M-06 requires it).
7. Store the analysis with the change request; link it from the affected work products.

### 7.3 Template

```
## Impact analysis IA-<yyyy>-<nn>

| Field | Value |
|---|---|
| Change request | <PR / CR link> |
| Range | <repo>: <from>..<to>; submodules: <name>: <from>..<to> |
| Reference configuration affected | yes / no (why) |
| Author / reviewer (independence) | <name> / <name, I-level> |

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision (take / modify / reject) |
|---|---|---|---|---|---|---|---|---|---|---|

Verification re-run results: <links: safety tests + coverage, MISRA, mutation, process replay, model replay, HIL, scenario suite>
Work products updated: <list, or "none — because ...">
Residual concerns / open items: <list>
```

## Open items

| ID | Item |
|---|---|
| OI-1 | Obtain unshallow history (or upstream release tags) to bound what changed before `8377c40`, for the record of the existing item |
| OI-2 | Fetch opendbc history for `4134c0d..229dc70` and analyse changes in `opendbc/safety/` and `opendbc/car/toyota/` |
| OI-3 | Obtain the rationale for upstream PR #38464 and its revert `910c08e` (SPI turnaround) |
| OI-4 | Obtain AGNOS 19.8 → 19.9 change notes, if published |
| OI-5 | Confirm the device type (comma 3X or four) so the UI-only rows in §6.2 can be closed |
| OI-6 | Agree with the assessor that the full-lifecycle conclusion (§5) and the scope restriction (M-1) are acceptable |
