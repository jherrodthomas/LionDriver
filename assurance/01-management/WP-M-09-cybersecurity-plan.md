# WP-M-09 Cybersecurity Plan

| Field | Value |
|---|---|
| Work product | WP-M-09 Cybersecurity plan |
| Standard reference | ISO/SAE 21434:2021 §6 (project dependent cybersecurity management), with activity references to §7–§15; UN R155 / R156 (informative); ASPICE 4.0 MAN.7, SEC.1–SEC.4 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | CS |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); cybersecurity assessment by an independent assessor (see §8) |
| Approver | Project maintainer (acting cybersecurity manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This plan implements sub-claim **G4** of the [assurance strategy](WP-M-01-assurance-strategy.md#32-top-level-claim) and tailoring decision **T-11**. It is the ISO/SAE 21434 §6 cybersecurity plan for the LionDriver reference configuration ([WP-M-01 §3.1](WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to)).

**Item for cybersecurity purposes:** the comma device (application SoC running AGNOS + LionDriver software), the panda safety MCU and its firmware, the Toyota harness, and the interfaces the item exposes: vehicle CAN, USB/SPI between SoC and panda, Wi-Fi/cellular, the software update path, remote access (athena, SSH, WebRTC streaming) and the local parameter store.

**External entities (not under LionDriver control, T-11):** comma.ai back-end services (athena server at `wss://athena.comma.ai`, `openpilot/system/athena/athenad.py:51`; connect; upload endpoints; AGNOS image CDN referenced in `openpilot/system/hardware/comma/agnos.json` (path read by the updater, `openpilot/system/updated/updated.py:221`; symlink to `openpilot/common/hardware/comma/agnos.json`)), GitHub (code hosting and the git-based update source), Toyota ECUs on the vehicle bus. They are covered by cybersecurity assumptions recorded in [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md).

Organizational cybersecurity management (21434 §5) is in [WP-M-04](WP-M-04-organization-competence-safety-culture.md) and [WP-M-05](WP-M-05-quality-assurance-plan.md).

## 2. Known inputs (baseline findings)

The [gap assessment §5](../00-assessment/gap-assessment.md#5-cybersecurity) gives the starting threat picture. These findings are inputs to the TARA; they are not yet risk-rated.

| Finding | Summary | Evidence | First WP to act |
|---|---|---|---|
| GAP-24 | Panda firmware signing uses RSA-1024 with SHA-1; no RDP/WRP option-byte setup in code; no runtime flash integrity check; softloader entry allowed in release builds | `panda/board/crypto/rsa.h:37`, `panda/board/crypto/sha.h:45`, `panda/board/bootstub.c:47-72`, `panda/board/main_comms.h:176-179` | [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) |
| GAP-25 | Debug RSA private key committed; firmware builds default to DEBUG with `ALLOW_DEBUG` unless `RELEASE` and `CERT` are set | `panda/board/crypto/certs/debug`, `panda/SConscript:12-20` | [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md), [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) |
| GAP-26 | OTA updates are git fetches from a configurable branch, staged with sudo; no signature verification beyond TLS and commit hashes | `openpilot/system/updated/updated.py:238, 387` | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |
| GAP-27 | Persistent remote connection to comma's server; RPCs to read live services, upload files to arbitrary URLs, tunnel SSH, read authorized keys, start camera streaming while onroad | `openpilot/system/athena/athenad.py:355, 620, 710, 757, 792` | [WP-C-09](../02-concept/WP-C-09-tara.md) |
| GAP-28 | Vulnerability reports route to comma.ai; LionDriver has no intake | `SECURITY.md:5`; `.github/ISSUE_TEMPLATE/*` | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |

Related findings with a cybersecurity aspect: GAP-09 (unauthenticated safety-mode change, `panda/board/main_comms.h:222-225`), GAP-20 (unauthenticated parameters and IPC), GAP-22 (models loaded with `pickle`, `openpilot/selfdrive/modeld/modeld.py:150, 159`), GAP-29 (submodules resolve to upstream repositories).

**Signing constraint to resolve early.** Release panda firmware is verified against comma's release key (`panda/board/bootstub.c:47-65`). LionDriver cannot sign with that key. Any LionDriver-modified panda firmware therefore needs either a debug-key path (which GAP-25 says must not ship) or a LionDriver-controlled boot chain. This decision shapes WP-S-07 and is tracked as OI-1.

## 3. Roles and responsibilities

| Role | Holder (today) | Responsibilities |
|---|---|---|
| Cybersecurity manager (acting) | Jherrod Thomas (maintainer) | Owns this plan; approves TARA risk treatment decisions; maintains the CS case |
| TARA / CS engineer | Jherrod Thomas | WP-C-09, WP-C-10, WP-S-07, WP-W-11 |
| Vulnerability management owner | Jherrod Thomas | Monitoring, triage and disclosure (WP-O-05); upstream advisory watch (§6, [WP-M-11](WP-M-11-upstream-and-supplier-management.md)) |
| Penetration tester | External, TBD | WP-V-06; must be independent of the implementer |
| Cybersecurity assessor | External, TBD | WP-K-05 |

Competence evidence for these roles is recorded in [WP-M-04](WP-M-04-organization-competence-safety-culture.md). With a single maintainer, independence for the assessment and penetration testing can only be achieved externally.

## 4. Tailoring

| # | Tailoring | Rationale |
|---|---|---|
| CT-1 | Production (§12) is limited to installation, provisioning, key and firmware loading of a retrofit ([WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md)) | LionDriver does not manufacture hardware (T-07) |
| CT-2 | comma back-end services are external entities with assumptions; LionDriver does not perform a TARA of the back end itself | No control or visibility (T-11) |
| CT-3 | Distributed activities (§7) are performed without a cybersecurity interface agreement; LionDriver takes the supplier responsibilities ([WP-M-11](WP-M-11-upstream-and-supplier-management.md)) | No contract with comma.ai or other upstreams (T-08) |
| CT-4 | Reference configuration may disable remote features (athena RPCs, SSH, live streaming, comma-hosted updates) rather than secure them | Reduces attack surface to what one maintainer can assure; decided in WP-C-10 |

Each tailoring entry needs the assessor's agreement before G1.

## 5. Activities by clause

| 21434 clause | Activity | Work products | Gate | Status today |
|---|---|---|---|---|
| §6 | Plan, tailor, reuse analysis, off-the-shelf handling, CS case, CS assessment, release for post-development | This plan; [WP-M-12](WP-M-12-impact-analysis.md) (reuse analysis); [WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md); [WP-K-05](../10-safety-case/WP-K-05-cybersecurity-assessment.md); [WP-P-10](../07-supporting/WP-P-10-release-management.md) | G0, G5 | This draft |
| §7 | Distributed activities: supplier capability, responsibilities, CS interface | [WP-M-11](WP-M-11-upstream-and-supplier-management.md) | G0 | Draft in parallel |
| §8 | Continual activities: cybersecurity monitoring, event evaluation, vulnerability analysis and management | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md), [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) | G0 (process running), G6 | Not running. `SECURITY.md` routes to comma (GAP-28) |
| §9 | Concept: item definition (CS view), cybersecurity goals, claims, concept | [WP-C-01](../02-concept/WP-C-01-item-definition.md), [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) | G1 | Not started |
| §15 | TARA methods: asset identification, threat scenarios, impact rating (safety, financial, operational, privacy), attack paths, feasibility, risk values, treatment decisions | [WP-C-09](../02-concept/WP-C-09-tara.md) | G1 (initial), updated each gate | Not started |
| §10 | Product development: CS requirements and architecture, implementation, integration and verification | [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md), [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md), [WP-W-01](../05-software/WP-W-01-software-development-environment-guidelines.md) | G2, G3 | Not started |
| §11 | Cybersecurity validation of the item, including penetration testing | [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md) | G5 | Not started |
| §12 | Production control (key handling, firmware loading, configuration lock) | [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md), [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md) | G5 | Not started |
| §13 | Operations and maintenance: incident response, updates | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) | G6 | Not started. Update path is upstream git-based (GAP-26) |
| §14 | End of cybersecurity support and decommissioning (user notice, key revocation, data wipe) | [WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) | G5 | Not started |

### 5.1 TARA scope priorities

The first TARA iteration covers, in this order: (1) paths that can defeat the safety envelope — panda firmware replacement (GAP-24/25), safety-mode change by the host (GAP-09), CAN injection; (2) the update path (GAP-26); (3) remote access (GAP-27); (4) local tampering with parameters, models and IPC (GAP-20, GAP-22); (5) privacy of camera, location and driver-camera data. Damage scenarios with safety impact are linked to HARA hazards in the shared hazard log ([WP-C-03](../02-concept/WP-C-03-hara.md)).

### 5.2 Cybersecurity assurance levels

CAL is assigned per cybersecurity goal in WP-C-10, based on the impact and attack-vector analysis of the TARA. CAL determines the rigour of verification in WP-W-11 and the depth of testing in WP-V-06. No CAL is assumed before the TARA exists.

## 6. Reuse, open-source and off-the-shelf components

LionDriver writes almost none of the code it ships. The approach per component class:

| Class | Components | Handling |
|---|---|---|
| Reused upstream source (modifiable) | openpilot (whole tree), opendbc, panda, msgq, rednose, teleoprtc | Reuse analysis in WP-M-12: identify CS-relevant changes since the last analysed baseline; include in TARA scope; CS requirements allocated to them in WP-S-07; vulnerability monitoring in WP-O-05 |
| Third-party open-source libraries | Python and native dependencies pinned in `uv.lock`; tinygrad (`tinygrad/tinygrad`, `.gitmodules` `branch = master`) | Software bill of materials (SBOM) generated per release; vulnerability scanning against public databases; pin by hash (already the case for `uv.lock`); pin tinygrad by commit (D-01) |
| Off-the-shelf components (binary, not modifiable by LionDriver) | AGNOS OS images (`openpilot/system/hardware/comma/agnos.json` (path read by the updater, `openpilot/system/updated/updated.py:221`; symlink to `openpilot/common/hardware/comma/agnos.json`)), AGNOS updater binary (`openpilot/common/hardware/comma/updater`, LFS), comma device hardware and panda bootloader as shipped, Chestnut eGPU firmware (`openpilot/system/hardware/chestnut/firmware_wrapped.bin`), comma-deps toolchain wheels (`pyproject.toml:29-69`), pre-compiled model pickles | Record identity (hash) and source; collect any available cybersecurity documentation; state cybersecurity assumptions on them in WP-C-10; treat as untrusted where the TARA requires; monitor for advisories |
| Component out of context | None planned | — |

Supplier-side activities for all of these fall to LionDriver ([WP-M-11](WP-M-11-upstream-and-supplier-management.md)).

## 7. Cybersecurity case

[WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md) argues that the cybersecurity goals of WP-C-10 are achieved for a given release. It is built incrementally:

| Gate | Content added to the CS case |
|---|---|
| G1 | TARA, goals, claims, concept, assumptions on external entities |
| G2–G3 | CS requirements, architecture, implementation evidence, verification results per CAL |
| G5 | Validation and penetration test results, residual risk statement, open vulnerabilities and their rationale, post-development readiness |
| G6 | Monitoring evidence, incidents and updates since release |

## 8. Cybersecurity assessment

- **Approach.** An independent assessor (external, not involved in development) reviews the CS case, the work products and the process evidence, and issues [WP-K-05](../10-safety-case/WP-K-05-cybersecurity-assessment.md) with an acceptance, conditional acceptance or rejection.
- **Timing.** A preliminary review of TARA and concept at G1 (combined with the functional safety confirmation review where the assessor has both competences); the full assessment at G5.
- **Scope.** All §6 work products, plus sampling of §10 evidence weighted by CAL.
- **Independence.** Cannot be met internally with a single maintainer (T-09 applies equally to cybersecurity).

## 9. Release for post-development

A release may move to post-development only when the [release record (WP-K-06)](../10-safety-case/WP-K-06-release-record.md) shows:

1. WP-K-03 complete for the release, with WP-K-05 not rejecting it;
2. the post-development requirements of WP-S-06 implemented (update mechanism, key management, decommissioning procedure);
3. vulnerability intake and incident response running ([WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)), including a LionDriver `SECURITY.md`;
4. the release configuration identified by hashes of all components, including AGNOS, panda firmware and model artefacts ([WP-P-10](../07-supporting/WP-P-10-release-management.md)).

## 10. Monitoring sources (input to §8 activities)

| Source | What is watched | Owner |
|---|---|---|
| Upstream repositories (`commaai/openpilot`, `commaai/panda`, `commaai/opendbc`, `commaai/msgq`, `commaai/rednose`, `commaai/teleoprtc`, `tinygrad/tinygrad`) | Security advisories, security-tagged commits, reverts of security fixes | Vulnerability management owner, via [WP-M-11](WP-M-11-upstream-and-supplier-management.md) §6 |
| Public vulnerability databases | Entries matching the SBOM (Python packages, native libraries, Linux kernel and userland in AGNOS) | Vulnerability management owner |
| LionDriver vulnerability intake | Reports from users and researchers | Vulnerability management owner |
| Field data | Anomalies in logs that suggest tampering (unexpected safety mode, debug firmware) | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |

Tooling for SBOM generation and scanning is not in the repository today; selection is OI-4.

## Open items

| ID | Item |
|---|---|
| OI-1 | Decide the panda firmware signing and boot-chain approach for LionDriver-modified firmware (comma release key unavailable; debug key must not ship) |
| OI-2 | Decide which remote features are disabled in the reference configuration (athena RPCs, SSH, live streaming, comma-hosted uploads) — WP-C-10 |
| OI-3 | Define the LionDriver update mechanism replacing the git-branch updater, with signature verification (GAP-26) |
| OI-4 | Select SBOM and vulnerability-scanning tooling; classify it under WP-P-07 |
| OI-5 | Publish a LionDriver `SECURITY.md` and intake channel (GAP-28) |
| OI-6 | Engage an independent cybersecurity assessor and penetration tester |
| OI-7 | Agree with the assessor the tailoring entries CT-1…CT-4 |
| OI-8 | Determine whether driver-camera and location data handling needs a privacy impact assessment beyond the TARA privacy impact category |
