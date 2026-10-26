# WP-O-05 Cybersecurity Incident Response, Vulnerability Management and Software Updates

| Field | Value |
|---|---|
| Work product | WP-O-05 Cybersecurity incident response, vulnerability management and software updates |
| Standard reference | ISO/SAE 21434:2021 §8 (continual cybersecurity activities: monitoring, event evaluation, vulnerability analysis, vulnerability management), §13 (operations and maintenance: incident response, updates), §14 (end of cybersecurity support and decommissioning); UN R156 (informative, software update management); ASPICE 4.0 SEC.* |
| Version | 0.4 (§4.4 items 5 to 8: weaknesses the project finds itself are embargoed until their control is verified; details in the private repository as GD records; DQ-421 A; 2026-10-26). 0.3 (§6: Figures 6-1 to 6-3, the update path today and the target, five update threats with their gates, and an update's states, generated from WP-S-07 §3.6 and §4.12 and this section; no change to the process or the requirements; 2026-10-24). 0.2 (§2 and OI-1: only the maintainer's own installation is supported until a deputy is named (DQ-101 A); OI-4: the timelines of §4.3 and §5.3 and the support period of §7 agreed as proposed (DQ-102 A); 2026-10-23). 0.1 |
| Status | Draft — process defined; **not running**. No monitoring, intake or incident record exists yet (GAP-28) |
| ASIL / scope | CS; safety coordination for SG-01…SG-08 |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting cybersecurity manager); safety manager for §5.4 |
| Baseline | `8b8c6ae` |

> Defensive process document. Vulnerability details handled under this process are embargoed
> (§4.4) and are never written into this file.

## 1. Purpose and scope

This work product defines how LionDriver monitors for cybersecurity information, evaluates events, analyses and manages vulnerabilities, responds to incidents, manages software updates in the field and ends cybersecurity support. It applies to every LionDriver release of the reference configuration after release for post-development ([WP-M-09 §9](../01-management/WP-M-09-cybersecurity-plan.md)) and to the development baseline (vulnerabilities found during development go through the same analysis). It closes GAP-28 when running and implements CSR-161/CSR-162 of [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md).

Interfaces: field monitoring of safety events [WP-O-04](WP-O-04-field-monitoring.md); problem resolution [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) (category `cat-cs`); change management [WP-P-02](../07-supporting/WP-P-02-change-management.md) (CT-8 security fix); release management [WP-P-10](../07-supporting/WP-P-10-release-management.md); upstream monitoring [WP-M-11 §6](../01-management/WP-M-11-upstream-and-supplier-management.md); decommissioning [WP-O-02](WP-O-02-operation-service-decommissioning.md).

## 2. Roles

With a single maintainer, one person holds most roles. The table records the role, not the person, so that responsibilities transfer when the project grows.

| Role | Holder (today) | Responsibilities |
|---|---|---|
| Cybersecurity manager (CSM) | Maintainer (acting) | Owns this process; decides event classification, treatment and disclosure; declares incidents |
| Vulnerability management owner (VMO) | Maintainer | Runs monitoring (§3.1), triage, SBOM scans, advisory watch; keeps the vulnerability register |
| Safety manager (SM) | Maintainer (acting) | Assesses safety impact; decides field actions (stop-use, restriction) per [WP-O-04 §9](WP-O-04-field-monitoring.md) |
| Release manager | Maintainer | Builds, signs and publishes fixes; rollback ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) |
| Key custodian | Maintainer | Holds offline panda release key and update key; executes re-keying |
| External reviewer / assessor | External, TBD | Independent review of incident closure for Critical incidents ([WP-K-05](../10-safety-case/WP-K-05-cybersecurity-assessment.md)) |
| Reporter | Users, researchers, upstream | Report through the channel in §8 |

Backup: a named deputy with repository and key-access instructions is required before more than the maintainer's own installations are supported (OI-1). Until one is named, LionDriver supports only the maintainer's own installation (decided 2026-10-23, DQ-101 option A).

## 3. Cybersecurity monitoring and event evaluation (21434 §8)

### 3.1 Monitoring sources

| ID | Source | What is watched | Method | Frequency |
|---|---|---|---|---|
| MS-01 | Upstream comma repositories: `commaai/openpilot`, `commaai/panda`, `commaai/opendbc`, `commaai/msgq`, `commaai/rednose`, `commaai/teleoprtc` | Published security advisories (GitHub Security Advisories), security-labelled issues/PRs, fixes touching CAL 3 paths (bootstub, `main_comms.h`, pandad flashing, updated, athenad, installer), reverts | Watch notifications + review per [WP-M-11 §6](../01-management/WP-M-11-upstream-and-supplier-management.md) | Immediately on notification; weekly automated watch (WP-W-11 SCAN-04); monthly manual review |
| MS-02 | `tinygrad/tinygrad` | Advisories and fixes affecting model loading/compilation | Same as MS-01 | Same as MS-01 |
| MS-03 | GitHub Advisory Database / OSV | Entries matching the release SBOM (`uv.lock` packages, submodules) | Automated scan (SCAN-03, [WP-W-11 §5.2](../05-software/WP-W-11-cybersecurity-implementation-verification.md)) | Weekly |
| MS-04 | NVD / CVE feeds | CVEs for the `uv.lock` dependency set, the Linux kernel and userland in AGNOS, STM32H7 silicon/ROM bootloader, toolchain | Automated scan where the SBOM allows; manual search for OTS components | Weekly (automated); monthly (manual) |
| MS-05 | comma.ai announcements and AGNOS release notes | Security fixes in AGNOS images | Manual | Per AGNOS release |
| MS-06 | STMicroelectronics security bulletins | STM32H7 bootloader, RDP, crypto issues | Manual | Monthly |
| MS-07 | LionDriver vulnerability intake (§8) | Reports from users and researchers | Private reporting channel | Continuous; acknowledgement target §5.3 |
| MS-08 | Field data ([WP-O-04](WP-O-04-field-monitoring.md)) | Indicators of tampering: unexpected safety mode/param in `pandaStates`, non-release panda firmware version or signature, unexpected `SshEnabled`, unknown processes | Field event review; installation records | Per review cycle of WP-O-04 |
| MS-09 | Security research and conferences on openpilot/comma devices and automotive CAN | Public research on the platform | Manual | Quarterly |

Each monitored item that may concern LionDriver becomes a **cybersecurity event** with an ID `CSE-<yyyy>-<nnn>` in the vulnerability register (§3.3).

### 3.2 Event evaluation

| Step | Question | Output |
|---|---|---|
| E1 Relevance | Does the event concern a component, version or configuration in a supported LionDriver release (check SBOM and release record)? | Not relevant → close with rationale |
| E2 Asset mapping | Which assets (AS-01…AS-16) and threat scenarios (TS-01…TS-13) of the [TARA](../02-concept/WP-C-09-tara.md) are affected? Is it a new threat scenario? | Mapping; new TS → TARA update |
| E3 Weakness or vulnerability | Is there a weakness? Is there an attack path that makes it exploitable in the reference configuration (consider controls of [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md))? | Weakness / vulnerability / neither |
| E4 Safety relevance | Can exploitation lead to DS-01…DS-07 or DS-11 (safety goal violation)? | Yes → SM informed same day (§5.4) |

Target: E1–E4 complete within **5 working days** of the event (2 working days for intake reports and for events tagged safety-relevant).

### 3.3 Vulnerability register

Kept as private GitHub security advisories of the LionDriver repository (one per vulnerability) plus a register index under restricted access (OI-2). Fields: CSE/vulnerability ID, source, date, affected releases and components, TS/AP mapping, attack-feasibility rating, impact rating, risk value, CVSS (if available), treatment decision, linked problem report (`cat-cs`), fix release, disclosure date, closure evidence.

## 4. Vulnerability analysis and management

### 4.1 Analysis

For each vulnerability: rate impact (S/F/O/P per [WP-C-09 §3](../02-concept/WP-C-09-tara.md)), rate attack feasibility with the attack-potential factors ([WP-C-09 §6](../02-concept/WP-C-09-tara.md)), and determine the risk value with the matrix of [WP-C-09 §7](../02-concept/WP-C-09-tara.md). External scores (CVSS) are recorded but do not replace the TARA rating.

### 4.2 Severity mapping

| Severity | Criterion | Problem severity ([WP-P-03 §4.2](../07-supporting/WP-P-03-problem-resolution.md)) |
|---|---|---|
| **Critical** | Risk value 5, or any exploitable path to a safety-goal violation (DS-01…DS-07, DS-11) in a supported release | S-1 |
| **High** | Risk value 4, or privacy damage rated Severe (DS-08, DS-12) with feasibility High/Medium | S-1 if safety-relevant, else S-2 |
| **Medium** | Risk value 3 | S-3 |
| **Low** | Risk value ≤ 2 | S-4 |

### 4.3 Treatment and timelines

| Severity | Containment target | Fix target | Treatment options |
|---|---|---|---|
| Critical | **24 h**: safety decision on stop-use / restriction (§5.4); configuration mitigation where possible (e.g. disable athenad, SSH, updates) | Fix release within **14 days** or documented reason | Reduce (fix); avoid (disable feature); no retention of safety-relevant Critical risk |
| High | 5 working days | 30 days | Reduce; avoid; retain only with CSM + SM sign-off and CS case entry |
| Medium | — | Next planned release (≤ 90 days) | Reduce; retain with rationale |
| Low | — | Backlog | Retain with rationale |

Retained or shared risks are added to the CS case ([WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md)) as residual risk and, where they create a new long-term condition, as a new cybersecurity claim in [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md).

### 4.4 Embargo and disclosure

1. Fixes for undisclosed vulnerabilities are developed in a private fork or private advisory branch (WP-P-02 CT-8) and reviewed there.
2. Coordinated disclosure: LionDriver publishes an advisory when the fix release is available, or at **90 days** after the report, whichever is first, unless the reporter agrees an extension. Safety-relevant issues may be disclosed earlier as a stop-use notice without technical detail.
3. If the vulnerability is in upstream code, LionDriver reports it to the upstream owner (comma.ai `SECURITY.md` contacts, or the tinygrad / dependency maintainers) under the same embargo before publishing.
4. Advisories state affected releases, impact, fix release and workaround; they contain no exploit detail.
5. **Weaknesses the project finds itself** (TARA, review, test, simulation) are embargoed like reported ones, until their control is verified (decision register DQ-421 A, 2026-10-25). Their code locations and mechanisms, and attack-path simulations, mocks and clips, live only in the private repository `jherrodthomas/LionDriver-security`, as GD records (GD-nn). The public documents keep the threat, the asset, the damage, the risk ratings, the goal and requirement text, the status, a one-line statement of the weakness, and the pointer `(details: private record GD-nn)`.
6. When a GD record's controls are verified, its text goes back into the public documents in one commit, and the record is marked `published` with that commit. A GD ID is never reused.
7. Every edit to a public document follows items 5 and 6. A reviewer who finds an unfixed weakness's code location or mechanism in a public pull request asks for it to be moved before merge. What was public before 2026-10-26 stays in the public history; the rule reduces exposure from then on.
8. The abstraction rule applies in both repositories: no exploits, payloads, keys or procedures.

## 5. Incident response plan

An **incident** is a vulnerability under active exploitation, a confirmed compromise of a LionDriver device, signing key, repository or release artefact, or field evidence of tampering (MS-08).

### 5.1 Incident classes

| Class | Examples | Lead |
|---|---|---|
| IC-1 Key compromise | panda release key or update key exposed or suspected | CSM + key custodian |
| IC-2 Supply-chain / repository compromise | Malicious commit, release artefact or dependency in a LionDriver release; compromised maintainer account | CSM |
| IC-3 Device compromise in the field | Tampered device found (non-release firmware, unexpected safety mode, unknown access) | CSM + SM |
| IC-4 Active exploitation of a known vulnerability | Report or evidence of use against LionDriver devices | CSM + SM |
| IC-5 Data exposure | Personal data or identity keys exposed | CSM |

### 5.2 Response phases

| Phase | Activities | Record |
|---|---|---|
| R1 Detect and declare | Event evaluated (§3.2) and declared an incident by the CSM; incident ID assigned | Incident issue (private) |
| R2 Safety triage | SM decides within **24 h** on stop-use / restriction notice (§5.4) | Decision record |
| R3 Contain | Disable the affected feature by configuration where possible; revoke compromised credentials; freeze releases; for IC-1, stop signing with the affected key | Containment log |
| R4 Eradicate and fix | Root cause analysis ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)); fix via CT-8 change; for IC-1, re-key (§5.5) | Problem report, PR |
| R5 Recover | Fix release per §6; verify installed base (WP-O-01 INS-15…INS-23 equivalent checks) | Release record addendum |
| R6 Lessons learned | Update TARA, WP-S-07, this process; CS case entry; independent review for Critical | Post-incident report |

### 5.3 Timelines

| Item | Target |
|---|---|
| Acknowledge an intake report | 3 working days |
| Event evaluation (E1–E4) | 5 working days (2 for intake and safety-tagged events) |
| Safety decision for safety-relevant Critical/High | 24 h from E4 = yes |
| User notification after a stop-use decision | Within 24 h to every known installation (channel per [WP-O-04 §9](WP-O-04-field-monitoring.md), OI-7 there) |
| Advisory publication | With the fix release, or ≤ 90 days |

### 5.4 Safety coordination

- Every vulnerability or incident with E4 = yes is also raised as a safety anomaly ([WP-M-02 §9](../01-management/WP-M-02-safety-plan.md)) and a `cat-fusa` + `cat-cs` problem report.
- The SM applies the field action criteria of [WP-O-04 §9](WP-O-04-field-monitoring.md). "A confirmed exploitable vulnerability with safety impact" is a trigger for a **stop-use notice**: all users of the affected release stop engaging LD-SDA immediately ([WP-O-03](WP-O-03-user-information-safety-warnings.md) UI-42); the vehicle remains drivable with LD-SDA off or the device removed (stock path).
- Where a configuration change removes the attack path without affecting safety functions (e.g. turning off athenad or SSH), a **restriction notice** may be used instead; the SM records why the residual is acceptable.
- Vehicle testing on the affected configuration stops until the SM releases it (S-1 handling, [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)).

### 5.5 Key compromise and re-keying

| Step | Action |
|---|---|
| K1 | Stop signing with the affected key; mark all releases signed after the suspected compromise date as untrusted |
| K2 | Generate a new key offline (key ceremony record, [WP-P-10 §6](../07-supporting/WP-P-10-release-management.md)) |
| K3 | panda key: build a bootstub with the new public key; reprovisioning is a bench step on each device because bootstub sectors are write-protected (CSR-042); issue stop-use until reprovisioned if the old key can sign an unsafe envelope |
| K4 | Update key: publish a key-rotation manifest signed by the old key only if the old key is not compromised; otherwise manual reinstallation per WP-O-01 |
| K5 | Revoke and record; update the CS case |

The committed upstream debug key (`panda/board/crypto/certs/`) is treated as permanently compromised and is never accepted by a LionDriver release bootstub (CSR-022; [WP-W-11 §6](../05-software/WP-W-11-cybersecurity-implementation-verification.md) SEC-01).

## 6. Software update management (21434 §13; UN R156 informative)

### 6.1 Current state

The inherited updater fetches a git branch and force-checks it out, with no verification beyond TLS and in-tree hashes (`openpilot/system/updated/updated.py:205-222, 237-245, 387-399`; GAP-26). Until the signed update path of [WP-S-07 §3.6](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) (CSR-121…CSR-126) exists, automatic updates are disabled (`DisableUpdates`, `updated.py:416`) and the maintainer installs releases manually ([WP-O-02](WP-O-02-operation-service-decommissioning.md) UPD-02).

![Figure 6-1: the update path in two columns, today's inherited updater and the signed-release target, row by row: where the update comes from, the check before staging, the code, the system images and an older release; each target row with the status of its requirement, all not implemented or not met; below, the manual installation in force until then and the fields the signed manifest will list](figures/fig-o05-6-1-update-path.svg)

*Figure 6-1.* What the device trusts before it stages an update, today and in the target of WP-S-07 §3.6; chips give the WP-S-07 §4.12 status of each requirement. Generated by [`figures/fig_o05_updates.py`](figures/fig_o05_updates.py) from WP-S-07 §3.6 and §4.12 and this section; CI fails if a quoted text or a status changes, or the figure is stale.

![Figure 6-2: five update threats on one topology of signing key, release origin, network, device and panda: a forged release at the source, the device sent to another origin, an older release replayed, an install cut short and a stolen signing key; each with its entry point and its gate, four with no control yet and one partly built](figures/fig-o05-6-2-update-attacks.svg)

*Figure 6-2.* Five update threats at the level of WP-C-09, each with where it enters and the requirement that would stop it, drawn as built: no barrier while a requirement is not implemented, dashed while partial or not verified, solid once verified. UN R155 Annex 5 and UN R156 labels are informative, not claimed. Same generator.

### 6.2 Update process

| Step | Activity | Reference |
|---|---|---|
| U1 Change and impact | Every update is a change under [WP-P-02](../07-supporting/WP-P-02-change-management.md) with the impact analysis checklist (§6 there), including cybersecurity impact (TS, CSG, CSR, attack-surface change) and **safety impact** (SG, TSR, envelope limits, panda firmware, models) | WP-P-02 §5–§6 |
| U2 Verification | Verification required by the impact analysis; for security fixes, the VS-CS tests of affected CSRs and the build-config audit ([WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) §7–§8) | WP-W-11 |
| U3 Release | Release per [WP-P-10](../07-supporting/WP-P-10-release-management.md): evidence package, SBOM and scan report, release record with all hashes, CS case update | WP-P-10, WP-K-06 |
| U4 Integrity | Release manifest signed with the offline update key; panda image signed with the panda release key; devices verify before staging (CSR-121). Until then: manual installation with hash comparison against the release record | CSR-121, CSR-124 |
| U5 Staged rollout | Stage 1: maintainer's bench device and reference vehicle (closed course / offroad checks); Stage 2: up to 10 % of known installations or 3 vehicles; Stage 3: all. Minimum soak per stage: 1 week of normal use for routine releases; for Critical fixes the SM may shorten stages to 24 h each | — |
| U6 Installation conditions | Offroad only (`process_config.py:114`); post-update parameter check against the release record (UPD-06) | WP-O-02 UPD-05, UPD-06 |
| U7 Rollback | Rollback only to a release whose evidence is valid for the installed device; signed rollback manifest (CSR-123); rollback that changes panda firmware tested on the bench first | WP-P-10 §8 |
| U8 User notification | Release notes stating security-relevant content at a level that does not aid exploitation; required user actions; for safety-relevant fixes, the stop-use/restriction status | WP-O-03; WP-O-04 §9 |
| U9 Records | Per installation: release installed, date, method, verification result | WP-O-01 records |

![Figure 6-3: an update's states from release published through receipt, the verify gate, install, activate and confirm to running the new release; a release refused at the gate is not staged; a failure while installing, starting or confirming falls back to the previous release, which remains bootable, or to a safe state that is not defined for LionDriver](figures/fig-o05-6-3-update-states.svg)

*Figure 6-3.* An update's states, with the requirement status at each and where a failure goes (animated, 14 s; [still version](figures/fig-o05-6-3-update-states-still.svg)). The verify gate is a gate, not a step; ISO 24089 terms and the UN R156 safe-state alternative are informative. Same generator.

Model weight changes in an update are SOTIF-relevant (D-05; [WP-O-02](WP-O-02-operation-service-decommissioning.md) UPD-03) and panda firmware/opendbc changes need envelope evidence (UPD-04); these checks are part of U1/U2.

### 6.3 Upstream security fixes

An upstream security fix is pulled through a sync change (WP-P-02 CT-3) with impact analysis. If the upstream fix is not yet public, LionDriver applies an equivalent private fix (CT-8) and syncs later.

## 7. End of cybersecurity support and decommissioning (21434 §14)

| Item | Rule |
|---|---|
| Support period | Each release is supported until the next release plus **90 days**, or until a stop-use/withdrawal. Only the latest release receives fixes; older releases are fixed by upgrading |
| End-of-support decision | CSM decides; recorded in the release record addendum ([WP-K-06](../10-safety-case/WP-K-06-release-record.md)) |
| Communication | Users informed through the field-action channel ([WP-O-04 §9](WP-O-04-field-monitoring.md)) at least 30 days before end of support (unless a Critical issue forces earlier action), with the date after which the release must not be engaged ([WP-O-02 §7.3](WP-O-02-operation-service-decommissioning.md)) |
| End of project support | If LionDriver as a project stops supporting the reference configuration: final notice to all users that LD-SDA must not be engaged after a stated date; final advisory; publication of the vulnerability register summary; keys destroyed after the last signed release is withdrawn |
| Decommissioning | Device-level data and key wiping, credential revocation and stock restoration per [WP-O-02 §7](WP-O-02-operation-service-decommissioning.md) DEC-01…DEC-11 (CSR-151, CSR-152) |

## 8. Proposed LionDriver `SECURITY.md` content

At `8b8c6ae` the repository's `SECURITY.md` routed all reports to comma.ai (GAP-28). The maintainer has since replaced it with a LionDriver cybersecurity statement, and the reporting part of the content below was added to the top of it (RR-2026-002 F-04). The e-mail alternative is not adopted until a LionDriver-controlled security address exists (OI-3).

```markdown
# Security Policy

LionDriver is a driver-assistance software fork of openpilot. Security issues can
affect vehicle safety, so please report them privately.

## Reporting a vulnerability

- Preferred: use GitHub private vulnerability reporting on this repository
  ("Security" tab -> "Report a vulnerability").
- Alternative: email <security contact address controlled by LionDriver>.
  <Optional: PGP key fingerprint>.
- Do not open public issues, pull requests or discussions for security problems.

Please include: affected LionDriver release or commit, device type, a description of the
issue and its impact, and how you found it. Proof-of-concept material is welcome but not
required; do not send personal data of other people.

## What to expect

- Acknowledgement within 3 working days.
- Initial assessment within 5 working days (2 if the issue may affect vehicle safety).
- If the issue can affect safety, we may tell users to stop using the driving functions
  before a fix is ready. Such notices contain no technical detail.
- We aim to release a fix and publish an advisory within 90 days, and we coordinate
  disclosure timing with you. We credit reporters who wish to be credited.

## Scope

In scope: this repository and its LionDriver-controlled submodules, LionDriver release
builds, the panda firmware built by LionDriver, and the LionDriver update and release process.

Out of scope here: comma.ai services and hardware, upstream openpilot, and third-party
services. Report those to their owners (for comma.ai see the upstream openpilot
SECURITY.md). If you are unsure, report to us and we will route it.

## Testing rules

Test only on equipment you own. Never test on public roads or in a moving vehicle outside a
closed course. Do not access other people's devices, data or accounts. Do not attack comma.ai
or other third-party infrastructure.

## Supported releases

Only the latest LionDriver release receives security fixes. See the release notes for the
end-of-support date of each release.
```

## 9. Records

| Record | Location | Retention |
|---|---|---|
| Vulnerability register and advisories | Private GitHub security advisories + restricted index (OI-2) | Per [WP-P-04 §10](../07-supporting/WP-P-04-documentation-management.md#10-retention) (released-baseline records) |
| Incident records | Private incident issues | Same as above |
| Monitoring review log (MS-01…MS-09) | Under `01-management/` per WP-M-11 OI-3 | Same as above |
| Update and notification records | Release record addenda; installation records | Same as above |

## 10. Current capability (honest status)

| Capability | Status at `8b8c6ae` |
|---|---|
| LionDriver vulnerability intake | **Not available** (GAP-28) |
| SBOM and automated scanning | Not available ([WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-4) |
| Upstream advisory watch | Not started (WP-M-11 §6) |
| Signed updates | Not available (GAP-26); manual updates only |
| Field-action notification channel | Not available ([WP-O-04](WP-O-04-field-monitoring.md) OI-7) |
| Offline signing keys | Not generated |
| Incident records | None |

## Open items

| ID | Item |
|---|---|
| OI-1 | Name a deputy for the CSM/VMO roles with documented access, before supporting installations beyond the maintainer's own. Decided 2026-10-23 (DQ-101, option A): until a deputy is named, only the maintainer's own installation is supported; no other users are supported. Open: name the deputy; revisit before release (G5) |
| OI-2 | Set up private vulnerability reporting and the restricted register index |
| OI-3 | `SECURITY.md` reporting section adopted (GitHub private vulnerability reporting). Remaining: enable private vulnerability reporting in the repository settings; obtain a LionDriver-controlled security contact address |
| OI-4 | Closed 2026-10-23 (DQ-102, option A): the project lead, as safety manager, agreed the timelines of §4.3 and §5.3 and the support period of §7 as proposed (acknowledge within 3 working days; assess within 5, 2 if safety-relevant; High fixes within 30 days; advisory with the fix or by 90 days; each release supported until the next plus 90 days). No assessor is engaged (DQ-009 C) |
| OI-5 | Define the staged-rollout mechanism once signed updates exist (U5 needs per-installation release targeting) |
| OI-6 | Closed: monitoring cadence harmonised as weekly automated scan/watch (WP-W-11 SCAN-03/SCAN-04) plus monthly manual review (WP-M-11 §6, this document §2) |
| OI-7 | Write the key-rotation manifest format (K4) together with the update manifest (WP-S-07 OI-4) |
