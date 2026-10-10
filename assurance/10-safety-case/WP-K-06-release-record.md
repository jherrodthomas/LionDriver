# WP-K-06 Release Record

| Field | Value |
|---|---|
| Work product | WP-K-06 Release for production / release record |
| Standard reference | ISO 26262-2:2018 §6 (release for production, documentation); ISO 26262-4:2018 §9 (release for production); ISO 21448:2022 §12 (release); ISO/SAE 21434:2021 §6 (release for post-development); ASPICE 4.0 SUP.8 |
| Version | 0.1 |
| Status | Skeleton — template. **No LionDriver release has been made.** One copy of §2–§8 is filled per release |
| ASIL / scope | All (FuSa, SOTIF, CS) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | Configuration manager (completeness); QA (I1) |
| Approver | Signatories in §8 |
| Baseline | `8b8c6ae` |

## 1. Purpose and rules

The release record is the single document that authorises a LionDriver baseline to be installed on the reference vehicle outside controlled testing. It is created by the release procedure in [WP-P-10](../07-supporting/WP-P-10-release-management.md), stored with the release tag's evidence package, and referenced by installation ([WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-15…INS-19).

Rules:

1. A release is valid only if every field in §2–§7 is filled and all signatures in §8 are present.
2. The values in §3 are the **reference values** that installation and field monitoring compare against (WP-O-01 SPC-04…SPC-07; [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) MON-16).
3. Any open issue accepted for release appears in §6 with a rationale and a signatory who accepted it.
4. A record is never edited after signature. Corrections are made by a new release (PATCH) per [WP-P-01 §7](../07-supporting/WP-P-01-configuration-management-plan.md).

## 2. Release identification — template

| Field | Value |
|---|---|
| Release | `ld-vX.Y.Z` |
| Release type | MAJOR / MINOR / PATCH ([WP-P-01 §7](../07-supporting/WP-P-01-configuration-management-plan.md)) |
| Previous release | |
| Scope (reference configuration) | 2020 Toyota Corolla LE, US, ICE, TSS2 (`TOYOTA_COROLLA_TSS2`); device revision `<…>`; harness `<…>` |
| ODD version | [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) v`<…>` |
| Release date | |

## 3. Configuration baseline — template

| Item | Reference value |
|---|---|
| Superproject commit (signed tag) | |
| Submodule SHAs and URLs (`opendbc_repo`, `panda`, `msgq_repo`, `rednose_repo`, `tinygrad_repo`, `teleoprtc_repo`) | |
| Baseline manifest (`baseline-manifest.yaml`) SHA-256 | |
| `uv.lock` / `opendbc_repo/uv.lock` SHA-256 | |
| AGNOS version and image hashes | |
| panda firmware version string and signature (hex) | |
| panda firmware binary SHA-256 (reproducible from tag: yes/no) | |
| Panda build type | RELEASE (not DEBUG; no `ALLOW_DEBUG`) |
| Model files and hashes (driving, DM) | |
| Parameter set (Experimental Mode, DisengageOnAccelerator, IsLdwEnabled, SshEnabled, RecordFront, debug modes absent) | |
| Expected `carParams` values (fingerprint, fuzzy = false, safetyModel, safetyParam, alternativeExperience, openpilotLongitudinalControl) | |
| Reference vehicle ECU FW versions (engine, EPS, ABS, radar, camera) | |
| Toolchain versions ([WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md)) | |

## 4. Evidence package — template

| Evidence | Work product | Version / status | Location in package |
|---|---|---|---|
| Safety case | [WP-K-01](WP-K-01-safety-case.md) | | |
| SOTIF release recommendation | [WP-K-02](WP-K-02-sotif-release-argument.md) | | |
| Cybersecurity case | [WP-K-03](WP-K-03-cybersecurity-case.md) | | |
| Functional safety assessment (FSA-F) | [WP-K-04](WP-K-04-functional-safety-assessment.md) | | |
| Cybersecurity assessment | [WP-K-05](WP-K-05-cybersecurity-assessment.md) | | |
| Safety validation report | [WP-V-01](../06-validation/WP-V-01-safety-validation.md) | | |
| System, SW and HW verification reports | WP-S-08, WP-S-09, WP-W-06…W-08, WP-H-06 | | |
| Fault injection report | [WP-V-05](../06-validation/WP-V-05-fault-injection.md) | | |
| Trace consistency report (all checks K1–K12 pass) | [WP-T-01](../trace/README.md) | | |
| CI run records at the release commit | | | |
| Physical and functional configuration audits | [WP-P-01 §11](../07-supporting/WP-P-01-configuration-management-plan.md) | | |
| Installation, operation and user information | [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md)…[WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md) | | |
| Field monitoring and incident response readiness | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md), [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) | | |
| Work product register snapshot | [WP-M-00](../01-management/WP-M-00-work-product-register.md) | | |

## 5. Changes since previous release — template

| Change request / PR | Summary | Safety-relevant class | Impact analysis | Re-verification |
|---|---|---|---|---|

## 6. Open issues accepted for release — template

| Issue | Category / severity ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)) | Description | Rationale for acceptance | Containment (ODD restriction, user information, monitoring) | Accepted by |
|---|---|---|---|---|---|

Rule: no S-1 issue may be accepted. An S-2 issue needs the safety manager's acceptance and the assessor informed ([WP-M-02 §9](../01-management/WP-M-02-safety-plan.md#9-safety-anomaly-handling)).

## 7. Release conditions — template

| # | Condition (from FSA, SOTIF recommendation, CS assessment) | Owner | Due | Tracking issue |
|---|---|---|---|---|

## 8. Signatures — template

| Role | Statement | Name | Signature / signed tag or commit | Date |
|---|---|---|---|---|
| Safety manager (FuSa) | Functional safety achieved per WP-K-01; FSA result: `<…>` | | | |
| SOTIF lead | SOTIF recommendation per WP-K-02: `<…>` | | | |
| Cybersecurity manager | Cybersecurity case and assessment per WP-K-03/K-05: `<…>` | | | |
| Configuration manager | Baseline in §3 matches the tagged repository state | | | |
| Project maintainer | Release authorised | | | |

The same person may not sign for a role whose independence requirement they do not meet ([WP-M-02 §3.1](../01-management/WP-M-02-safety-plan.md#31-role-assignments)). With one maintainer today, at least the FSA (I3) and CS assessment are external.

## 9. Release history

| Release | Date | Result | Record |
|---|---|---|---|
| — | — | No release made at `8b8c6ae` | — |

## 10. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Align §3 fields with the baseline manifest generator (WP-P-01 OI-5) so §3 can be filled automatically | G5 |
| OI-2 | Decide how signatures are recorded (signed git tag plus signed commit of the filled record) | G5 |
| OI-3 | Fill the SOTIF lead and cybersecurity manager roles ([WP-M-02](../01-management/WP-M-02-safety-plan.md)) before the first release | G5 |
