# WP-W-11 Cybersecurity Implementation and Verification

| Field | Value |
|---|---|
| Work product | WP-W-11 Cybersecurity implementation and verification |
| Standard reference | ISO/SAE 21434:2021 §10 (product development: implementation, integration and verification; weakness analysis), §6 (off-the-shelf and open-source components); ISO 26262-6:2018 §5 (coding guidelines, as shared base); ASPICE 4.0 SEC.2, SEC.3 |
| Version | 0.2 (RR-2026-008 F-20: §8 CSR status and summary counts at `682f184`, BA-01 reference-build check, CSR-136 citation resolved in WP-S-07; F-28: author and baseline; 2026-10-12) |
| Status | Draft — rules and plan proposed; no verification activity of this plan (VS-CS-nnn, BA, SAST, FZ, PT) has been executed. The §8 status column records code review at `682f184` and, for CSR-011…CSR-015 and CSR-024, the host unit-test runs recorded in the change records (UT executed, not reviewed); nothing is verified on hardware |
| ASIL / scope | CS (CAL 1–3); shared coding rules apply to the envelope code (B‡ per WP-S-02: ASIL C until SG-01 is re-rated) |
| Author | Assurance team (AI-assisted draft, Claude) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting cybersecurity manager) |
| Baseline | `682f184` (opendbc `7993399`, panda `8aa8671`) |

> [!NOTE]
> **Status at `682f184` (opendbc `7993399`, panda `8aa8671`).** This document describes the code at `8b8c6ae` unless a statement names a later pin. Safety mechanisms integrated since then (hardware watchdog and 100 Hz safety task, RX timeout, TX whitelist, safety-mode lock, 0.3 s heartbeat, IRQ priorities, EPS fault, cruise-main check, TX rate supervision) are recorded in the [WP-W-02](WP-W-02-software-safety-requirements.md) Baseline column and the [change records](../07-supporting/impact/README.md). The sections of this document that still describe the earlier behaviour are listed in [RR-2026-008](reviews/RR-2026-008.md) and are to be updated ([WP-M-14 §2.3](../01-management/WP-M-14-iso26262-6-implementation-specification.md#23-pre-entry-engineering-track) P-03).

> Defensive engineering document. It defines coding rules, analysis tooling and verification
> of protection mechanisms. It contains no exploitation detail and reproduces no key material.

## 1. Purpose and scope

This work product sets the secure-coding rules, static analysis (SAST) plan, software bill of materials (SBOM) and dependency vulnerability scanning, secrets handling, and the verification plan for every detailed cybersecurity requirement CSR-nnn of [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md). Verification rigour scales with the CAL proposed in [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) §3–§4.

Scope by code area:

| Area | Language | Paths | Highest CAL | Shared with safety |
|---|---|---|---|---|
| panda firmware and bootstub | C | `panda/board/**` | 3 | B‡ ([WP-W-05](WP-W-05-software-unit-design.md), [WP-W-06](WP-W-06-software-unit-verification.md)) |
| opendbc safety | C | `opendbc_repo/opendbc/safety/**` | 3 | B‡ |
| Host safety-relevant processes | Python, C++ | `openpilot/selfdrive/**`, `openpilot/system/**`, `openpilot/common/**` | 2–3 | QM / QM (B-sup) (TSR-6xx) |
| Network-facing processes | Python, C++ | `openpilot/system/athena/**`, `openpilot/system/updated/**`, `openpilot/system/loggerd/uploader.py`, `openpilot/system/webrtc/**`, `openpilot/selfdrive/ui/installer/**` | 3 | QM |
| Build, release and CI | Python, shell, YAML | `panda/SConscript`, `SConstruct`, `tools/release/**`, `.github/workflows/**`, `uv.lock`, `.gitmodules`, `.lfsconfig` | 3 | Tool qualification ([WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md)) |

## 2. Rigour per CAL

| Activity | CAL 1 | CAL 2 | CAL 3 |
|---|---|---|---|
| Secure coding rules (§3) | Applied | Applied, deviations recorded | Applied, deviations recorded and reviewed by a second person (I1) |
| SAST (§4) | Python lint security rules | + C/C++ analyser with security rules | + MISRA C:2012 and selected CERT C rules with zero unjustified findings |
| Code review focus | General | Security checklist (§3.4) | Security checklist + review of every change to a CAL 3 path by someone other than the author |
| Requirements-based tests | Positive | Positive + negative (rejection) | Positive + negative + boundary + interface fuzzing (bench) |
| Vulnerability scanning | Per release | Per release + weekly | Per release + weekly + before every merge touching dependencies |
| Penetration testing | — | Targeted ([WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md)) | Full scope of the CSG ([WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md)) |

## 3. Secure coding rules

### 3.1 C (panda firmware, bootstub, opendbc safety)

Base: **MISRA C:2012** as already used for the envelope (`panda/tests/misra/test_misra.sh`, `panda/tests/misra/suppressions.txt`; opendbc `opendbc_repo/opendbc/safety/tests/misra/`). The gap assessment records that the bootstub is not MISRA-checked and that global suppressions lack deviation records (GAP-13). Those deviations are handled in [WP-W-01](WP-W-01-software-development-environment-guidelines.md); this section adds security rules.

| ID | Rule | Source | Applies to | Why here |
|---|---|---|---|---|
| SC-C-01 | MISRA C:2012 mandatory and required rules, with recorded deviations; extend the check to the bootstub and the host command handler (`main_comms.h`) | MISRA C:2012 | FW, opendbc | GAP-13; bootstub is the CSG-02 root of trust |
| SC-C-02 | Validate every length and index taken from a host or bus message before use; reject out-of-range values explicitly | CERT C ARR30-C, ARR38-C, INT30-C/INT31-C | `main_comms.h`, `drivers/spi.h`, `can_comms.h`, bootstub image length | TB-1 is the main attack surface on Z1 |
| SC-C-03 | No unbounded copies; `memcpy` sizes derived from validated lengths only | CERT C STR31-C, ARR38-C | FW | — |
| SC-C-04 | Integer conversions and arithmetic on externally supplied values checked for wrap and truncation | CERT C INT30-C, INT31-C, INT32-C | FW, opendbc | Command parameters are 16-bit and cast |
| SC-C-05 | Every `switch` over a host command has an explicit `default` that rejects, and every command is listed in the per-mode allow-list (CSR-014) | MISRA 16.4, CSR-014 | `main_comms.h` | Undocumented commands are attack surface |
| SC-C-06 | Debug-only code is enclosed in `#ifdef ALLOW_DEBUG` (or removed); no debug path is reachable in a release build | Project rule; CSR-021, CSR-023 | FW, opendbc | GAP-09 (`0xc5` ungated at `8b8c6ae`; gated in the reference build since panda `9f60e17`, SWSR-513), GAP-25 |
| SC-C-07 | Signature and hash verification uses one reviewed library; comparison of digests and signatures does not short-circuit on secret-dependent data where timing could leak (verify-only use still reviewed) | CERT C MSC (crypto), project rule | bootstub | CSR-031 |
| SC-C-08 | No use of uninitialised memory; all security-relevant state has a defined value at reset | CERT C EXP33-C | FW | Safe state after reset (HWSR-502) |
| SC-C-09 | Compiler warnings treated as errors for release builds; release build configuration verified by the build-config audit (§7) | Project rule | FW | GAP-41 (tested ≠ shipped config) |

### 3.2 Python (host)

| ID | Rule | Applies to | Current state / note |
|---|---|---|---|
| SC-PY-01 | Do not use `pickle`, `marshal`, `shelve` or `yaml.load` without `SafeLoader` on data that crosses a trust boundary or comes from a file that is not covered by the authenticated release manifest | All host code | Violated for model artefacts: `openpilot/selfdrive/modeld/modeld.py:150,159`, `dmonitoringmodeld.py:33,48`, `helpers.py:19-20` (GAP-22, CSR-081). Until fixed, CSR-082 hash verification is the compensating control |
| SC-PY-02 | `subprocess` calls pass an argument list; `shell=True` is not used with any value that is not a compile-time constant | All host code | 9 non-test files under `openpilot/system`, `openpilot/selfdrive`, `openpilot/common` use `shell=True` (e.g. `openpilot/common/hardware/comma/hardware.py`, `agnos.py`, `openpilot/system/timed.py`, `tombstoned.py`). Each needs triage: constant command → record; interpolated value → fix (OI-3) |
| SC-PY-03 | Paths built from external input are resolved (`os.path.realpath`) and checked to stay under the intended root (`os.path.commonpath`); symlinks are not followed out of the root | athenad, uploader, loggerd, UI file pickers | athena upload validation is string-based (rejects leading `/` and `..`, `openpilot/system/athena/athenad.py:637`); symlink handling under the log root to be reviewed (OI-4) |
| SC-PY-04 | Network clients verify TLS certificates; no `verify=False`; endpoints taken from release configuration, not environment variables, in release builds | athenad, uploader, api, updated | `ATHENA_HOST` env override (`athenad.py:51`, CSR-115) |
| SC-PY-05 | RPC handlers validate parameter types and ranges before acting and expose only allow-listed operations | athenad | CSR-112…CSR-114 |
| SC-PY-06 | Files containing secrets (identity key, SSH keys) are opened with least privilege and never logged; params holding secrets use `DONT_LOG` | api, athenad, params | `SecOCKey` already `DONT_LOG` (`openpilot/common/params_keys.h:120`); identity key handling CSR-141 |
| SC-PY-07 | No `eval`/`exec` on external data | All | No production use found by a repository grep at the baseline (test code excluded) |
| SC-PY-08 | Writes to safety-relevant params go only through the designated writer (CSR-062) | Host | Not enforced today (GAP-20) |

### 3.3 C++ (host) and shell

C++ host code (pandad, UI, installer, loggerd) follows the C rules SC-C-02…SC-C-04 for any externally supplied buffer and SC-PY-02 for process execution (`run()` with formatted strings, e.g. `openpilot/selfdrive/ui/installer/installer.cc:200-202`). Shell scripts keep the existing `check_shell` lint (`scripts/lint/lint.sh`) and quote all expansions.

### 3.4 Security review checklist (CAL 2–3 changes)

1. Does the change add or modify a host command, RPC, param, msgq topic, file path or network endpoint? If yes, update the TB tables in WP-S-07 §3.2/§6 and the allow-lists.
2. Does it touch a CAL 3 path (bootstub, `main_comms.h`, `safety.h`, pandad flashing, updated, athenad, installer)? If yes, a second reviewer is required.
3. Are all external inputs validated (§3.1 SC-C-02, §3.2 SC-PY-03/05)?
4. Is any debug capability reachable in the release configuration?
5. Does it add a dependency or change `uv.lock`, `.gitmodules`, `.lfsconfig`? If yes, SBOM and scan (§5) before merge.
6. Does it add or move secret material? (Never in Git; §6.)

The checklist becomes part of the PR template proposed in [WP-P-02 §8](../07-supporting/WP-P-02-change-management.md) (OI-5).

## 4. Static analysis (SAST) plan

| ID | Tool class | Target | Configuration | Gate | Status at baseline |
|---|---|---|---|---|---|
| SAST-01 | cppcheck with MISRA addon | `panda/board/**`, `opendbc_repo/opendbc/safety/**` | Existing MISRA scripts; add bootstub and command handler; record deviations | CAL 3 paths: zero unjustified findings | Exists for panda/opendbc envelope; in LionDriver CI since D-03 (`safety.yaml`; GAP-39 mitigated); cppcheck from a mutable branch (`uv.lock:586`, GAP-34) |
| SAST-02 | C security rule set (cppcheck CERT addon or clang-tidy `cert-*`/`bugprone-*` checks) | Same as SAST-01 + pandad, installer | Selected CERT C rules from §3.1 | CAL 3: zero unjustified findings | Not configured |
| SAST-03 | Python security lint (ruff `S` rules, flake8-bandit equivalent) | `openpilot/**` | Enable `S` rule family; per-file ignores with rationale for tests | CAL 2–3 paths: no new findings | Not enabled: current ruff selection has no `S` rules (`pyproject.toml:114-125`) |
| SAST-04 | Semantic code scanning (e.g. CodeQL or Semgrep) for C/C++ and Python | Whole tree | Default security queries + custom queries for `pickle.load`, `shell=True`, unvalidated `os.path.join` with RPC input | Findings triaged per release | Not configured |
| SAST-05 | Secret scanning | Whole history and every PR | Repository secret scanning plus a pre-merge scanner; documented allow-list entry only for the known-public panda debug key (§6) | Block on new secrets | Not configured |
| SAST-06 | Workflow and CI hardening lint | `.github/workflows/**` | Check pinned action versions by SHA, no secrets to fork PRs, least-privilege tokens | Block on high findings | Not configured (GAP-31) |

Tool classification and qualification of SAST tools is done under [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md). Results are stored per release in the evidence package ([WP-P-10 §5](../07-supporting/WP-P-10-release-management.md)).

Finding handling: each finding is fixed, or justified as a recorded deviation, or raised as a problem report labelled `cat-cs` ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)). Weaknesses that may be exploitable go to vulnerability analysis in [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md).

## 5. SBOM and dependency vulnerability scanning

### 5.1 Inventory sources

| Component class | Source of truth | SBOM content | Notes |
|---|---|---|---|
| Python and native wheels | `uv.lock` (hash-pinned) | Name, version, hash, source index | comma-deps toolchain wheels included; cppcheck resolved from a git branch (`uv.lock:586`) must be pinned by commit (CSR-132) |
| Submodules | `.gitmodules` + gitlinks | Repository URL, commit | Today relative URLs to `commaai/*`, tinygrad `branch = master` (GAP-29, CSR-131) |
| Git LFS artefacts (models, binaries) | `.lfsconfig`, LFS pointers | Path, OID (SHA-256), size, store URL | Store is comma's (GAP-40, CSR-083) |
| OS image | `openpilot/system/hardware/comma/agnos.json`, `AGNOS_VERSION` in `launch_env.sh` | Version, image hashes | Off-the-shelf; package-level content not visible (CSC-04) |
| panda toolchain and firmware | Toolchain wheel version; built image hash | Compiler version, image hash, signing key ID | — |
| Vendored code in tree | Directory scan | Name, version where known | e.g. vendored CMSIS headers in `panda/board/stm32h7/inc/` |

Format: CycloneDX or SPDX JSON, one per release, stored with the release record ([WP-K-06](../10-safety-case/WP-K-06-release-record.md)). Tool selection is [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-4.

### 5.2 Scanning

| Activity | Trigger | Data sources | Output |
|---|---|---|---|
| SCAN-01 Dependency scan | Every PR changing `uv.lock`, `pyproject.toml`, `.gitmodules`, `.lfsconfig` (CT-4 changes, [WP-P-02](../07-supporting/WP-P-02-change-management.md)) | OSV / GitHub Advisory Database / NVD for the SBOM ecosystem entries | Findings attached to the PR |
| SCAN-02 Release scan | Release candidate | Same | Release scan report in the evidence package; each finding assessed (affected? reachable? CAL?) |
| SCAN-03 Continuous scan | Weekly on the current release SBOM | Same | New findings → event evaluation in [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) §3 |
| SCAN-04 Upstream advisory watch | Weekly | `commaai/*` and `tinygrad/tinygrad` security advisories and security-tagged commits | Per [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md) §6 |

Release criterion: no known vulnerability in a shipped component that is assessed as reachable with risk value ≥ 3 (TARA scale, [WP-C-09 §7](../02-concept/WP-C-09-tara.md)) remains untreated; retained findings are listed in the CS case ([WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md)).

## 6. Secrets handling

| ID | Secret / sensitive item | Location | Finding | Required handling |
|---|---|---|---|---|
| SEC-01 | panda debug signing private key | `panda/board/crypto/certs/` (committed; contents not reproduced here) | Public by publication; any image signed with it must be treated as untrusted (GAP-25) | Treat as **compromised**. Exclude from release acceptance (CSR-021/CSR-022: release bootstub built without `ALLOW_DEBUG`, debug key not compiled in). For development, a LionDriver development key may replace it, labelled as non-secret and never accepted by release bootstubs. Record the file as a known-public test key in the secret-scanner allow-list so that any other key is still blocked |
| SEC-02 | LionDriver panda release private key | Offline media (to be created) | Does not exist yet | Generated offline; never in Git, CI, logs or the release host's persistent storage; use logged in a key-ceremony record ([WP-P-10 §6](../07-supporting/WP-P-10-release-management.md)); re-key procedure in [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |
| SEC-03 | LionDriver update-signing private key | Offline media (to be created) | Does not exist yet | Separate from SEC-02 (CSR-126); same handling |
| SEC-04 | Embedded authorized SSH key in INTERNAL installer | `openpilot/selfdrive/ui/installer/installer.cc:204-213` | Public key of a third party grants access when INTERNAL is defined | Remove the INTERNAL block from LionDriver builds (CSR-101); build-config audit checks `INTERNAL` is undefined |
| SEC-05 | Device identity key pair | `/persist/comma/` on the device (`openpilot/common/api.py:61-62`) | Not in Git; at-rest protection unknown | CSR-141, CSR-142; wipe on decommissioning (CSR-151) |
| SEC-06 | CI credentials | GitHub Actions secrets | Upstream workflows reference comma infrastructure (GAP-30/31) | No signing keys in CI (CSR-135); fork PRs get no secrets; tokens least-privilege |
| SEC-07 | `SecOCKey` param | `params_keys.h:120` | Not used on the reference vehicle | Keep `DONT_LOG`; out of scope |

History check: run the secret scanner over the full Git history once (SAST-05) and record the result; any further secret found is rotated, not only deleted (OI-6).

## 7. Build-configuration audit (release)

A scripted check run on every release build; it produces a signed-off report in the evidence package. Checks:

| Check | Requirement | Method |
|---|---|---|
| BA-01 panda built with `RELEASE` and LionDriver cert; `ALLOW_DEBUG` not defined in any object; the reference release built with `LIONDRIVER_REFERENCE=1` (so `-DLIONDRIVER_REFERENCE` is in the compile flags and the reference lock `board/reference_lock.h` is compiled in) | CSR-021; CSR-011…CSR-015, CSR-024, CSR-092 (reference-build only) | Build log (environment and compile flags) + symbol/string check of the image (e.g. the reference-lock rejection message, panda `8aa8671`, `board/reference_lock.h:57`) |
| BA-02 Release bootstub contains only the LionDriver public key | CSR-022 | Compare embedded key header with the release-record key ID |
| BA-03 Debug commands absent | CSR-023 | Static check of the release command table |
| BA-04 Installer built without `INTERNAL`; no embedded key | CSR-101 | Build flags + binary string check for authorized-key format |
| BA-05 Developer-mode processes unreachable | CSR-071, CSR-073 | Process table inspection in release build |
| BA-06 `ATHENA_HOST` override ignored; athenad disabled by default | CSR-111, CSR-115 | Unit test on release configuration |
| BA-07 All submodules and dependencies pinned by commit/hash from approved URLs | CSR-131, CSR-132 | Parse `.gitmodules`, `uv.lock` |
| BA-08 SBOM generated and scan report attached | CSR-133, CSR-134 | Evidence package check |

The existing `opendbc_repo/opendbc/safety/tests/test_release_build.py` only checks that a release build compiles; it does not check BA-01…BA-03 (GAP-41).

Where `LIONDRIVER_REFERENCE` is set (BA-01): only from the build environment. `panda/SConscript:22-26` (panda `8aa8671`) adds `-DLIONDRIVER_REFERENCE` when the variable is set and names the reference release build as `RELEASE=1 LIONDRIVER_REFERENCE=1`; it is independent of `RELEASE`. The release script `tools/release/build_release.sh:56` (`682f184`) builds panda with `CERT=… RELEASE=1 scons panda/` and does not set it, so a release built by that script would not contain the reference lock, the reduced Toyota TX allow-list or the TX rate supervision. BA-01 would therefore fail on that script today; the release procedure is open in the [safety-mode-lock change record](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) OI-2 (OI-9). In LionDriver CI the flag is set only for the opendbc safety test variant (`.github/workflows/safety.yaml:39-43`) and in the panda MISRA run (`panda/tests/misra/test_misra.sh:68`).

## 8. Verification specification per CSR

Verification specs use IDs `VS-CS-nnn` matching the CSR number. Status is at `682f184` (opendbc `7993399`, panda `8aa8671`), from code review, the [WP-W-02](WP-W-02-software-safety-requirements.md) Baseline column and the [change records](../07-supporting/impact/README.md); **no VS-CS verification has been executed and nothing is verified on hardware**. Where the status depends on the reference build it says so; the reference build is `LIONDRIVER_REFERENCE=1` (§7 BA-01). Test-evidence wording: *UT executed, not reviewed* = a run is recorded in a change record but the test and its result are not independently reviewed; *UT exists, run not recorded* = no run is recorded. Legend for *Status*: **Not met** (code review shows the requirement is not implemented); **Partial**; **Implemented, not verified**; **Process** (depends on a procedure not yet run); **Open** (needs a decision or investigation first).

| CSR | CAL | VS | Method | Pass criterion (summary) | Status |
|---|---|---|---|---|---|
| CSR-011 | 3 | VS-CS-011 | UT (libpanda) + HIL | Every non-locked mode/param/alt-exp request rejected; locked config accepted | Implemented, not verified — `LIONDRIVER_REFERENCE=1` build only (BA-01): `0xdc` accepts only SILENT, NOOUTPUT, ELM327 and TOYOTA with param 73, and from TOYOTA only NOOUTPUT/SILENT (panda `8aa8671`, `board/reference_lock.h:14, 22-29`); `0xdf` refused in every mode (`:30-32`); a refused request is mapped to `0x00`, which has no handler (`board/main_comms.h:74-79, 336-340`). Locked values are compile-time constants, not read from the release record. UT exists (`panda/tests/reference_lock/test_reference_lock.py`), executed per the change records ([mode lock](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §4, [IRQ priorities](../07-supporting/impact/change-2026-10-12-panda-irq-priorities.md) §3: pass), not reviewed; not run in LionDriver CI. Other builds: not met (`main_comms.h:243-245`) |
| CSR-012 | 3 | VS-CS-012 | UT + HIL | After rejection: non-actuating mode, fault bit set in health | Partial — `LIONDRIVER_REFERENCE=1` build only (BA-01): a refused request has no effect, so the panda stays in its previous mode, which is TOYOTA (actuating) when the request came in TOYOTA (`board/reference_lock.h:22-24`, `board/main_comms.h:76-78`); it does not go to a non-actuating mode. The refusal is reported as a saturating counter `requests_rejected_pkt` in the health packet (`board/reference_lock.h:15-16, 53-56`; `board/main_comms.h:27-31`; `board/health.h:16, 40`), not as a fault bit; pandad publishes it and logs increases (`682f184`, `openpilot/selfdrive/pandad/pandad.cc:137, 185-193`) with no alert. UT exists (`panda/tests/reference_lock/test_reference_lock.py`), executed per the change records ([mode lock](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §4, [IRQ priorities](../07-supporting/impact/change-2026-10-12-panda-irq-priorities.md) §3: pass), not reviewed; not run in LionDriver CI |
| CSR-013 | 3 | VS-CS-013 | UT | SILENT/NOOUTPUT reachable from locked mode | Implemented, not verified — `LIONDRIVER_REFERENCE=1` build only (BA-01): allowed from TOYOTA (panda `8aa8671`, `board/reference_lock.h:23-24`); other builds: `set_safety_mode` accepts any mode (`board/main_comms.h:243-245`). UT exists (`panda/tests/reference_lock/test_reference_lock.py`), executed per the change records ([mode lock](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §4, [IRQ priorities](../07-supporting/impact/change-2026-10-12-panda-irq-priorities.md) §3: pass), not reviewed; not run in LionDriver CI |
| CSR-014 | 3 | VS-CS-014 | R + UT + FZ (bench) | Commands outside allow-list rejected in car mode; fuzzing of the command handler finds no crash, hang or state change outside the allow-list | Partial — `LIONDRIVER_REFERENCE=1` build only (BA-01): the gate is a deny-list, not an allow-list: in a car mode it refuses `0xc5`, `0xd8`, `0xdb`, `0xde`, `0xe5`, `0xe6`, `0xe7`, `0xe8`, `0xf1`, `0xf9`, `0xfc` (panda `8aa8671`, `board/reference_lock.h:37-49`), `0xdf` and `0xd1` param 1 (`:30-36`); every other request passes (`:50-51`); `0xc0`, `0xb0`, `0xb1`, `0xf6` still to be confirmed (mode-lock change record OI-4). Request IDs without a handler fall to `default` with no effect (`board/main_comms.h:336-340`). No fuzzing done. UT exists (`panda/tests/reference_lock/test_reference_lock.py`), executed per the change records ([mode lock](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §4, [IRQ priorities](../07-supporting/impact/change-2026-10-12-panda-irq-priorities.md) §3: pass), not reviewed; not run in LionDriver CI |
| CSR-015 | 3 | VS-CS-015 | UT | Alt-exp unchanged across any mode sequence | Implemented, not verified — `LIONDRIVER_REFERENCE=1` build only (BA-01): `0xdf` refused in every mode (panda `8aa8671`, `board/reference_lock.h:30-32`), so `alternative_experience` keeps its reset value 0 (opendbc `7993399`, `safety.h:101`; the only writer is `board/main_comms.h:262-267`). UT exists (`panda/tests/reference_lock/test_reference_lock.py`), executed per the change records ([mode lock](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §4, [IRQ priorities](../07-supporting/impact/change-2026-10-12-panda-irq-priorities.md) §3: pass), not reviewed; not run in LionDriver CI. Other builds: partial, settable in a non-car mode (`main_comms.h:262-267`) |
| CSR-016 | 2* | VS-CS-016 | UT + HIL | Mismatch blocks engagement and alerts | Not met |
| CSR-021 | 3 | VS-CS-021 | BA-01 | Release build refuses `ALLOW_DEBUG` | Not met |
| CSR-022 | 3 | VS-CS-022 | BA-02 + HIL | Debug-signed and tampered images rejected on bench | Partial (conditional on CSR-021) |
| CSR-023 | 3 | VS-CS-023 | BA-03 + FZ | No debug command effective in release image | Partial |
| CSR-024 | 3 | VS-CS-024 | UT + HIL | Softloader entry refused in car mode / ignition on | Partial — `LIONDRIVER_REFERENCE=1` build only (BA-01): `0xd1` param 1 refused in a car mode (panda `8aa8671`, `board/reference_lock.h:33-35`); there is no ignition condition, so entry is still accepted in a non-car mode with the ignition on (GAP-24; WP-S-07 OI-1). UT exists (`panda/tests/reference_lock/test_reference_lock.py`), executed per the change records ([mode lock](../07-supporting/impact/change-2026-10-12-panda-safety-mode-lock.md) §4, [IRQ priorities](../07-supporting/impact/change-2026-10-12-panda-irq-priorities.md) §3: pass), not reviewed; not run in LionDriver CI. Other builds: accepted at any time (`board/main_comms.h:196-199`) |
| CSR-031 | 3 | VS-CS-031 | R + HIL | Bootstub verifies with selected scheme; known-answer tests pass; invalid signatures rejected | Not met |
| CSR-032 | 3 | VS-CS-032 | CM + PR | Key ceremony record; key absent from repo/CI | Not met |
| CSR-033 | 3 | VS-CS-033 | UT + HIL | Lower-version signed image rejected | Partial |
| CSR-034 | 3 | VS-CS-034 | HIL + FI | Corrupted flash detected → safe state | Not met |
| CSR-041 | 3 | VS-CS-041 | HIL | Option bytes read back equal provisioning record | Not met |
| CSR-042 | 3 | VS-CS-042 | HIL | Bootstub sectors not writable from application/softloader | Not met |
| CSR-043 | 3 | VS-CS-043 | PR | Installation record contains option bytes and hashes | Process |
| CSR-051 | 3 | VS-CS-051 | R + HIL | Release pandad never flashes a development bootstub | Not met |
| CSR-052 | 3 | VS-CS-052 | R + HIL | BOOT0 asserted only on owner action, offroad, logged | Not met |
| CSR-053 | 2* | VS-CS-053 | UT + HIL | No car mode set with unrecorded firmware | Partial |
| CSR-054 | 3 | VS-CS-054 | A + HIL | Analysis per CS-AD-02/03 accepted by assessor | Open |
| CSR-061 | 2 | VS-CS-061 | R + A (FFI) | No envelope dependency on params/IPC beyond CSR-011 | Partial |
| CSR-062 | 2 | VS-CS-062 | R + UT | Unauthorized writer denied; mismatch blocks engagement | Not met |
| CSR-063 | 2 | VS-CS-063 | R + UT | Second publisher detected | Not met |
| CSR-064 | 2 | VS-CS-064 | R + PT | Network-facing processes lack write access | Open |
| CSR-071 | 2 | VS-CS-071 | BA-05 + UT | Developer processes never start in release | Not met |
| CSR-072 | 2 | VS-CS-072 | UT | Driver view has no effect onroad | Not met |
| CSR-073 | 2 | VS-CS-073 | BA-05 | Check fails on a seeded developer entry point | Not met |
| CSR-081 | 2 | VS-CS-081 | R + SAST-04 | No `pickle` load of artefact content | Not met |
| CSR-082 | 2 | VS-CS-082 | UT + HIL | Modified artefact → process refuses, engagement blocked | Not met |
| CSR-083 | 2 | VS-CS-083 | CM | LFS store under LionDriver control; hashes in release record | Not met |
| CSR-091 | 2 | VS-CS-091 | R + UT + HIL | Checksum/counter checks where available; plausibility for the rest | Partial |
| CSR-092 | 2 | VS-CS-092 | R + UT | TX outside allow-list blocked; PCS forwarding unaltered | Partial — TX allow-list reduced: `0x344` and the DSU bus-0/bus-1 sets removed in every build, `0x411` PCS_HUD also removed in the `LIONDRIVER_REFERENCE=1` build (opendbc `7993399`, `opendbc/safety/modes/toyota.h:19-39`; SWSR-705, [TX whitelist change record](../07-supporting/impact/change-2026-10-12-opendbc-toyota-tx-whitelist.md)). UT exists (`opendbc/safety/tests/test_toyota.py`) and runs in LionDriver CI in the standard and reference variants (`.github/workflows/safety.yaml:37-43`); no CI run result is cited here (UT exists, run not recorded in this document). PCS forwarding unaltered: not verified |
| CSR-093 | 2 | VS-CS-093 | UT + HIL | Foreign actuation ID on car side → inhibit | Partial |
| CSR-101 | 3 | VS-CS-101 | BA-04 | No embedded key; `INTERNAL` undefined | Not met for INTERNAL builds |
| CSR-102 | 3 | VS-CS-102 | PR | INS-19 record shows `SshEnabled` off | Process |
| CSR-103 | 3 | VS-CS-103 | R + PT | Password auth disabled; only owner keys | Open |
| CSR-104 | 3 | VS-CS-104 | HIL + PT | No new SSH session onroad | Open (decision) |
| CSR-111 | 3 | VS-CS-111 | BA-06 + PR | athenad not running by default | Not met |
| CSR-112 | 3 | VS-CS-112 | UT + PT | Non-allow-listed upload destination refused | Not met |
| CSR-113 | 3 | VS-CS-113 | UT + PT | Tunnel and key RPCs absent | Not met |
| CSR-114 | 3 | VS-CS-114 | UT | Non-allow-listed service refused | Not met |
| CSR-115 | 3 | VS-CS-115 | BA-06 | Env override ignored | Not met |
| CSR-116 | 3 | VS-CS-116 | UT + PT | Onroad stream request refused; loopback-only bind | Implemented, not verified |
| CSR-117 | 3 | VS-CS-117 | HIL (network off) | Engagement and envelope unaffected without network | Implemented, not verified |
| CSR-121 | 3 | VS-CS-121 | R + UT + PT | Unsigned/altered manifest or artefact never staged | Not met |
| CSR-122 | 3 | VS-CS-122 | UT | Non-release branch request ignored | Not met |
| CSR-123 | 3 | VS-CS-123 | UT | Downgrade refused unless signed rollback | Not met |
| CSR-124 | 3 | VS-CS-124 | PR | `DisableUpdates` set on reference vehicle | Process |
| CSR-125 | 3 | VS-CS-125 | R + HIL | Interrupted install leaves previous release bootable | Partial |
| CSR-126 | 3 | VS-CS-126 | PR | Separate offline key; re-key procedure exists | Not met |
| CSR-131 | 3 | VS-CS-131 | BA-07 | All submodules on LionDriver forks, commit-pinned | Not met |
| CSR-132 | 3 | VS-CS-132 | BA-07 | No mutable references | Not met |
| CSR-133 | 3 | VS-CS-133 | BA-08 | SBOM complete per §5.1 | Not met |
| CSR-134 | 3 | VS-CS-134 | BA-08 | Scan report with assessed findings | Not met |
| CSR-135 | 3 | VS-CS-135 | CM + R | No signing material reachable from PR CI | Open |
| CSR-141 | 2 | VS-CS-141 | R + PT | Key file permissions; no exposure via RPC/log | Open |
| CSR-142 | 2 | VS-CS-142 | R + HIL | Encryption at rest or recording-off default confirmed | Open (WP-C-09 OI-3) |
| CSR-143 | 2 | VS-CS-143 | R + PT | TLS with validation on every upload path | Open |
| CSR-144 | 2 | VS-CS-144 | R + PR | Driver camera not uploaded without opt-in | Open |
| CSR-151 | 2 | VS-CS-151 | PR + HIL | Keys and data absent after procedure | Process (tool missing) |
| CSR-152 | 2 | VS-CS-152 | PR | Revocation recorded | Process |
| CSR-161 | 1 | VS-CS-161 | PR | LionDriver security policy published | Not met (GAP-28) |
| CSR-162 | 1 | VS-CS-162 | PR | WP-O-05 process records exist | Not met |

\* CSR-016 and CSR-053 inherit CAL 3 from their parents but are SoC-side detection measures (defence in depth); they are verified at CAL 2 rigour because they are not credited as the protection for CSG-01/CSG-02 (WP-S-07 §3.2). This deviation from the parent CAL needs assessor agreement (OI-7).

Summary at `682f184` (opendbc `7993399`, panda `8aa8671`): of 64 CSRs, 0 verified; 5 implemented but not verified (CSR-011, CSR-015 in the reference build only); 12 partial; 5 process-dependent; 9 open; 33 not met. At `8b8c6ae`: 3 implemented but not verified; 10 partial; 5 process-dependent; 9 open; 37 not met. CSR-136, cited in WP-S-07 v0.1 §3.2, was not defined and is not counted (resolved in WP-S-07 v0.2).

## 9. Integration and weakness analysis

- **Integration.** CSRs on the SoC–panda interface (CSR-011…CSR-054) are integration-tested on the HIL bench ([WP-W-07](WP-W-07-software-integration-verification.md), [WP-W-08](WP-W-08-embedded-software-testing.md); D-04) using the release build configuration (GAP-41).
- **Weakness analysis (§10).** Each SAST and review finding is classified as weakness or not; weaknesses are mapped to the TARA attack paths (AP-nn) and, where they open a new path, the TARA is updated ([WP-C-09](../02-concept/WP-C-09-tara.md) OI-5).
- **Regression.** VS-CS tests for implemented CSRs run in LionDriver CI on every PR that touches a CAL 2–3 path (after GAP-39 is closed).

## Open items

| ID | Item |
|---|---|
| OI-1 | Select and qualify SAST, SBOM and scanning tools (WP-P-07; [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-4) |
| OI-2 | Choose the CERT C rule subset for SAST-02 and record it in [WP-W-01](WP-W-01-software-development-environment-guidelines.md) |
| OI-3 | Triage each `shell=True` call in non-test host code (SC-PY-02) |
| OI-4 | Review athena/uploader path handling for symlinks under the log root (SC-PY-03) |
| OI-5 | Add the §3.4 checklist to the PR template in [WP-P-02](../07-supporting/WP-P-02-change-management.md) |
| OI-6 | Run a full-history secret scan once and record the result (SAST-05, §6) |
| OI-7 | Agree with the assessor the CAL-2 rigour for SoC-side defence-in-depth CSRs (CSR-016, CSR-053) |
| OI-8 | Write the VS-CS-nnn test procedures and add them to `trace/` once WP-S-07 is approved |
| OI-9 | Release procedure and BA-01: the reference release must be built with `RELEASE=1 LIONDRIVER_REFERENCE=1`; `tools/release/build_release.sh:56` does not set `LIONDRIVER_REFERENCE` (§7). Also run `panda/tests/reference_lock` in LionDriver CI (today not in `.github/workflows/*.yaml`) |
