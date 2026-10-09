# WP-K-03 Cybersecurity Case

| Field | Value |
|---|---|
| Work product | WP-K-03 Cybersecurity case |
| Standard reference | ISO/SAE 21434:2021 §6 (cybersecurity case), with evidence from §8–§15; UN R155 (informative) |
| Version | 0.1 |
| Status | Draft — argument structure written; **almost all evidence is Missing or Partial**. This case does not support a release at this version |
| ASIL / scope | CS (CAL 1–3); interface to the safety case G4 ([WP-K-01](WP-K-01-safety-case.md)) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); cybersecurity assessor ([WP-K-05](WP-K-05-cybersecurity-assessment.md)) |
| Approver | Project maintainer (acting cybersecurity manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose

The cybersecurity case argues that the cybersecurity of the LD-SDA reference configuration is adequate for a given release, by connecting the cybersecurity goals and claims of [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) to the evidence produced under the [cybersecurity plan (WP-M-09)](../01-management/WP-M-09-cybersecurity-plan.md). It is built incrementally per [WP-M-09 §7](../01-management/WP-M-09-cybersecurity-plan.md) and is the main input to the cybersecurity assessment ([WP-K-05](WP-K-05-cybersecurity-assessment.md)) and to the release record ([WP-K-06](WP-K-06-release-record.md)). It supports sub-claim G4 of the [safety case](WP-K-01-safety-case.md#44-g4-cybersecurity).

Notation follows [WP-K-01 §2](WP-K-01-safety-case.md#2-notation) with prefixes `CG` (goal/claim), `CS` (strategy), `CC` (context), `CA` (assumption, reusing CA-01…CA-05 of WP-C-10), `CJ` (justification), `CSn` (evidence) and `CDF` (defeater).

## 2. Top-level argument

```text
CG0  The cybersecurity risks of LD-SDA in its reference configuration are reduced to an
     acceptable level for release <ld-vX.Y.Z>.
 ⊙ CC1  Item, boundary and reference configuration (WP-C-01; WP-M-01 §3.1)
 ⊙ CC2  Tailoring T-11, CT-1…CT-4 (WP-M-01 §5; WP-M-09 §4)
 ⊙ CC3  Risk acceptance: TARA risk value ≤ 2 retainable; ≥ 3 treated (WP-C-09 §7)
 ⊙ CA-01…CA-05  Assumptions on external entities (WP-C-10 §2)
 → CS1  Argue over (a) completeness of risk identification, (b) achievement of each
        cybersecurity goal, (c) validity of each claim, (d) process and post-development
        readiness.
    → CG1  Risks are identified and rated completely and correctly
    → CG2  Each cybersecurity goal CSG-01…CSG-08 is achieved
    → CG3  Each retained/shared/avoided risk (CSC-01…CSC-05) is justified and its
           condition holds
    → CG4  The residual risk after validation is acceptable
    → CG5  Cybersecurity is maintained after release (monitoring, incident response,
           updates, end of support)
    → CG6  The cybersecurity process was followed and independently assessed
```

## 3. Sub-arguments

### 3.1 CG1 Risk identification

```text
CG1  Risks are identified and rated completely and correctly.
 → CS1.1 Argue over TARA method, inputs and review
    → CG1.1 Assets, threat scenarios, damage scenarios and attack paths cover all
            interfaces IF-01…IF-09 and TB-1…TB-7            → CSn-01, CSn-02
    → CG1.2 Safety impact is anchored to HARA hazards         → CSn-01, CSn-03
    → CG1.3 Ratings reviewed and preliminarily assessed       → CSn-04
    → CG1.4 TARA re-iterated after controls (residual)        → CSn-05
 ⊙ CJ1 Open source: knowledge of the item rated "public" for every path (WP-C-09 §6)
```

### 3.2 CG2 Achievement of the cybersecurity goals

Each goal is argued by the same pattern: requirements refined and allocated (WP-S-07) → implemented → verified at the CAL rigour (WP-W-11) → validated / penetration-tested (WP-V-06).

```text
CG2  Each cybersecurity goal is achieved.
 → CS2 Argue per goal over refinement, implementation, verification and validation
    → CG2.1 CSG-01 safety configuration integrity (CAL 3)
        → CSR-011…CSR-016, CSR-021…CSR-024  → CSn-10, CSn-20, CSn-21, CSn-30
    → CG2.2 CSG-02 firmware and boot-chain integrity (CAL 3)
        → CSR-021…CSR-054                    → CSn-10, CSn-11, CSn-20, CSn-22, CSn-31
        ⇐ CDF-01, CDF-02, CDF-03
    → CG2.3 CSG-03 params / IPC integrity (CAL 2)
        → CSR-061…CSR-073                    → CSn-10, CSn-12, CSn-20, CSn-32
        ⇐ CDF-04
    → CG2.4 CSG-04 model artefact integrity (CAL 2)
        → CSR-081…CSR-083                    → CSn-10, CSn-20, CSn-33
        ⇐ CDF-05
    → CG2.5 CSG-05 vehicle CAN integrity (CAL 2)
        → CSR-091…CSR-093                    → CSn-10, CSn-20, CSn-23, CSn-34
    → CG2.6 CSG-06 remote and interactive access minimized (CAL 3)
        → CSR-101…CSR-117                    → CSn-10, CSn-13, CSn-20, CSn-35
        ⇐ CDF-06
    → CG2.7 CSG-07 authenticated updates and supply chain (CAL 3)
        → CSR-121…CSR-135                    → CSn-10, CSn-14, CSn-20, CSn-24, CSn-36
        ⇐ CDF-07, CDF-08
    → CG2.8 CSG-08 personal data and identity key protected (CAL 2)
        → CSR-141…CSR-152                    → CSn-10, CSn-20, CSn-37
        ⇐ CDF-09
 ⊙ CJ2 Envelope principle: safety-relevant protection sits in the panda (Z1); SoC-side
        controls are credited for likelihood reduction only (WP-S-07 §3.2)
```

### 3.3 CG3 Claims

```text
CG3  Each cybersecurity claim is justified and its condition holds.
    → CG3.1 CSC-01 physical CAN residual retained (condition: CSG-05 implemented; CA-05)
                                                          → CSn-34, CSn-40
    → CG3.2 CSC-02 back-end security shared (condition: CSG-06 device-side constraints;
            no safety dependency, CSR-117)                → CSn-35, CSn-41
    → CG3.3 CSC-03 non-repudiation retained (condition: identity key protected, CSR-141)
                                                          → CSn-37
    → CG3.4 CSC-04 OTS supply chain shared (condition: SBOM + monitoring running)
                                                          → CSn-24, CSn-50
    → CG3.5 CSC-05 eGPU avoided (condition: excluded from reference configuration)
                                                          → CSn-42
```

### 3.4 CG4 Residual risk

```text
CG4  The residual risk after validation is acceptable.
    → CG4.1 Validation and penetration testing found no open Critical/High finding
                                                          → CSn-30…CSn-37
    → CG4.2 Every retained finding is rated, justified and listed (§5)
                                                          → CSn-05, CSn-43
    → CG4.3 Safety-relevant residuals accepted by the safety manager in the safety case
                                                          → CSn-44 (WP-K-01 G4)
```

### 3.5 CG5 Post-development

```text
CG5  Cybersecurity is maintained after release.
    → CG5.1 Monitoring, event evaluation and vulnerability management running → CSn-50
    → CG5.2 Incident response plan in place, including stop-use coordination  → CSn-50, CSn-51
    → CG5.3 Update management with integrity, impact analysis, rollback      → CSn-14, CSn-50
    → CG5.4 Production/provisioning controls (keys, firmware, option bytes)  → CSn-52
    → CG5.5 End of support and decommissioning defined                       → CSn-53
    → CG5.6 LionDriver vulnerability intake published                        → CSn-54
```

### 3.6 CG6 Process and assessment

```text
CG6  The cybersecurity process was followed and independently assessed.
    → CG6.1 Plan, tailoring and roles agreed                 → CSn-60
    → CG6.2 Reuse / OTS / OSS handled per plan               → CSn-61, CSn-24
    → CG6.3 Work products reviewed at required independence   → CSn-62
    → CG6.4 Cybersecurity assessment does not reject         → CSn-63
```

## 4. Evidence status

**Available** = the evidence exists and is usable as is (executed result or approved work product). **Partial** = exists as a draft or covers only part of the claim. **Missing** = not yet produced. Status at baseline `8b8c6ae`.

| ID | Evidence | Work product / artefact | Supports | Status | Note |
|---|---|---|---|---|---|
| CSn-01 | TARA (assets, damage, threats, attack paths, feasibility, risk) | [WP-C-09](../02-concept/WP-C-09-tara.md) | CG1.1, CG1.2 | Partial | Draft; ratings are proposals |
| CSn-02 | Item definition, CS view | [WP-C-01](../02-concept/WP-C-01-item-definition.md) | CG1.1 | Partial | Draft |
| CSn-03 | HARA | [WP-C-03](../02-concept/WP-C-03-hara.md) | CG1.2 | Partial | Draft; confirmation review pending |
| CSn-04 | Preliminary CS assessment of TARA/concept (G1) | [WP-K-05](WP-K-05-cybersecurity-assessment.md) interim | CG1.3 | Missing | No assessor engaged |
| CSn-05 | Residual-risk TARA iteration | WP-C-09 update | CG1.4, CG4.2 | Missing | WP-C-09 OI-5 |
| CSn-10 | CS goals, claims, concept; detailed CSRs and architecture | [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md), [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) | CG2.x | Partial | Drafts; CAL proposals not agreed |
| CSn-11 | Boot-chain and RDP architecture decisions CS-AD-01…04 | WP-S-07 §3.4 | CG2.2 | Missing | Decisions open (WP-S-07 OI-2, OI-4) |
| CSn-12 | FFI analysis treating SoC attacker as common cause | [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md), [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md) | CG2.3 | Missing | — |
| CSn-13 | Reference-configuration remote-feature decision | WP-C-10 OI-2; WP-M-09 OI-2 | CG2.6 | Missing | — |
| CSn-14 | Signed update design and implementation | WP-S-07 §3.6; CSR-121…126 | CG2.7, CG5.3 | Missing | GAP-26 |
| CSn-20 | Secure coding, SAST results, per-CSR verification (VS-CS) | [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) | CG2.x | Partial | Plan only; 0 of 64 CSRs verified |
| CSn-21 | Safety-mode lock tests (shared with TSR-512) | WP-W-06/WP-W-08 | CG2.1 | Missing | Mechanism not implemented (GAP-09) |
| CSn-22 | Release build-config audit report (BA-01…BA-08) | WP-W-11 §7 | CG2.2, CG2.7 | Missing | `test_release_build.py` only checks compilation (GAP-41) |
| CSn-23 | Envelope TX allow-list and relay-malfunction tests | `opendbc_repo/opendbc/safety/tests/test_toyota.py`, `common.py` (upstream) | CG2.5 | Partial | Exist upstream; not run in LionDriver CI (GAP-39); release config not tested (GAP-41) |
| CSn-24 | SBOM and vulnerability scan report for the release | WP-W-11 §5 | CG2.7, CG3.4, CG6.2 | Missing | Tooling not selected |
| CSn-30 | Validation TC-01, TC-02 (command fuzzing, mode lock) | [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md) | CG2.1, CG4.1 | Missing | Not yet executed |
| CSn-31 | Validation TC-03…TC-05 (firmware, boot pins, option bytes) | WP-V-06 | CG2.2 | Missing | Not yet executed |
| CSn-32 | Validation TC-06, TC-07 (params/IPC, envelope under SoC compromise) | WP-V-06 | CG2.3 | Missing | Not yet executed |
| CSn-33 | Validation TC-08 (model artefacts) | WP-V-06 | CG2.4 | Missing | Not yet executed |
| CSn-34 | Validation TC-09, TC-10 (CAN robustness) | WP-V-06 | CG2.5, CG3.1 | Missing | Not yet executed |
| CSn-35 | Validation TC-11…TC-13 (remote surface, back-end independence) | WP-V-06 | CG2.6, CG3.2 | Missing | Not yet executed |
| CSn-36 | Validation TC-14, TC-15 (updates, supply chain) | WP-V-06 | CG2.7 | Missing | Not yet executed |
| CSn-37 | Validation TC-16, TC-17 (data at rest, decommissioning) | WP-V-06 | CG2.8, CG3.3 | Missing | Not yet executed; encryption at rest unknown (WP-C-09 OI-3) |
| CSn-40 | Physical-access assumption recorded in user information | [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md) | CG3.1 | Partial | Draft user information |
| CSn-41 | Onroad streaming block (inherited mechanism) | `openpilot/common/params_keys.h:62`, `openpilot/system/manager/process_config.py:119`, `openpilot/system/webrtc/helpers.py:28` | CG3.2 | Partial | Implemented in code; not verified (CSR-116) |
| CSn-42 | eGPU exclusion in reference configuration | [WP-C-01](../02-concept/WP-C-01-item-definition.md) E-06 | CG3.5 | Partial | Draft |
| CSn-43 | Residual-risk list (§5) with acceptance | This document | CG4.2 | Partial | Draft list; no acceptance |
| CSn-44 | Safety manager acceptance of safety-relevant CS residuals | [WP-K-01](WP-K-01-safety-case.md) G4 | CG4.3 | Missing | — |
| CSn-50 | Monitoring, vulnerability management, incident response, update management | [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) | CG5.1–5.3, CG3.4 | Partial | Process drafted; not running |
| CSn-51 | Field-action criteria incl. stop-use for exploitable vulnerability | [WP-O-04 §9](../09-production-operation/WP-O-04-field-monitoring.md) | CG5.2 | Partial | Draft; notification channel missing |
| CSn-52 | Provisioning controls (keys, firmware, option bytes) | [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) §7 | CG5.4 | Partial | Draft; option-byte check not yet in INS-17 (CSR-043) |
| CSn-53 | End of support and decommissioning | [WP-O-02 §7](../09-production-operation/WP-O-02-operation-service-decommissioning.md), WP-O-05 §7 | CG5.5 | Partial | Key-wipe tool missing (WP-O-02 OI-5) |
| CSn-54 | Published LionDriver `SECURITY.md` and intake | Repository `SECURITY.md` | CG5.6 | Missing | Routes to comma (GAP-28); proposal in WP-O-05 §8 |
| CSn-60 | Cybersecurity plan and tailoring agreement | [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) | CG6.1 | Partial | Draft; CT-1…CT-4 not agreed |
| CSn-61 | Reuse / impact analysis of the openpilot baseline | [WP-M-12](../01-management/WP-M-12-impact-analysis.md), [WP-P-08](../07-supporting/WP-P-08-software-component-qualification.md) | CG6.2 | Partial | Draft |
| CSn-62 | Review records at required independence | PR reviews per [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) | CG6.3 | Missing | No I1 reviewer yet (T-09) |
| CSn-63 | Cybersecurity assessment report | [WP-K-05](WP-K-05-cybersecurity-assessment.md) | CG6.4 | Missing | Skeleton |

Summary: Available 0; Partial 16; Missing 21 (of 37 evidence items).

## 5. Residual risks and claims register (current view)

| ID | Residual / claim | Basis | Status |
|---|---|---|---|
| RR-01 | Physical CAN injection on a vehicle with an accessible OBD port | CSC-01 | Proposed retain; condition (CSG-05) not met |
| RR-02 | Back-end and network security | CSC-02 | Proposed share; condition (athena constrained) not met |
| RR-03 | Non-repudiation limited to per-device key | CSC-03 | Proposed retain |
| RR-04 | OTS binaries (AGNOS, toolchain wheels, eGPU firmware) not source-verified | CSC-04 | Proposed share; SBOM/monitoring not running |
| RR-05 | Firmware substitution by an SoC-root attacker through boot-pin control, if no RDP level closes it | WP-S-07 CS-AD-03 | Open; risk not yet re-rated |

## 6. Defeaters (counter-evidence)

These mirror DF-22 and DF-23 of [WP-K-01 §7](WP-K-01-safety-case.md) in more detail. Each stays until closed by evidence.

| ID | Defeater | GAP | Undermines | Closed by |
|---|---|---|---|---|
| CDF-01 | panda signing uses RSA-1024/SHA-1; comma's release key, not a LionDriver key (`panda/board/crypto/rsa.h:37`, `sha.h:45`, `panda/board/bootstub.c:63`) | GAP-24 | CG2.2 | CSR-031, CSR-032 |
| CDF-02 | Debug private key committed; builds default to DEBUG with `ALLOW_DEBUG` (`panda/SConscript:12-20`) | GAP-25 | CG2.1, CG2.2 | CSR-021…CSR-023 |
| CDF-03 | SoC controls panda boot pins; pandad flashes a development bootstub; no RDP/WRP (`openpilot/common/hardware/comma/hardware.py:410-419`, `openpilot/selfdrive/pandad/pandad.py:34-39`, `panda/board/stm32h7/llflash.h:14`) | GAP-38 | CG2.2 | CSR-041…CSR-054, CS-AD-02 |
| CDF-04 | Unauthenticated params and IPC; developer modes replace control processes; host sets any safety mode (`panda/board/main_comms.h:223-225`) | GAP-09, GAP-20 | CG2.1, CG2.3 | CSR-011…CSR-016, CSR-061…CSR-073 |
| CDF-05 | Models loaded with `pickle`, no hash check (`openpilot/selfdrive/modeld/modeld.py:150,159`) | GAP-22 | CG2.4 | CSR-081, CSR-082 |
| CDF-06 | athena RPCs: arbitrary-URL upload, SSH tunnel, authorized-key read; INTERNAL installer embeds an SSH key (`openpilot/system/athena/athenad.py:619-757`, `openpilot/selfdrive/ui/installer/installer.cc:204-213`) | GAP-27 | CG2.6 | CSR-101, CSR-111…CSR-115 |
| CDF-07 | Unsigned git-branch updater; AGNOS hashes from the same tree (`openpilot/system/updated/updated.py:205-222, 387-399`) | GAP-26 | CG2.7 | CSR-121…CSR-125 |
| CDF-08 | Submodules resolve to upstream; tinygrad and cppcheck track mutable branches; models from comma's LFS | GAP-29, GAP-34, GAP-40 | CG2.7 | CSR-131, CSR-132, CSR-083 |
| CDF-09 | Encryption at rest of personal data and identity key not confirmed | — (WP-C-09 OI-3) | CG2.8 | CSR-141, CSR-142 |
| CDF-10 | No LionDriver vulnerability intake | GAP-28 | CG5.6 | CSR-161 |

## 7. Maintenance

The case is updated at each gate (WP-M-09 §7) and for every release: the release number in CG0 is set, the evidence table is re-evaluated against the release baseline, and the residual-risk register is re-accepted. Changes classified with cybersecurity impact under [WP-P-02](../07-supporting/WP-P-02-change-management.md) must state which CG/CSn they affect.

## Open items

| ID | Item |
|---|---|
| OI-1 | Engage the assessor for the preliminary assessment of CG1 (CSn-04) |
| OI-2 | Close the architecture decisions CS-AD-01…04 and re-rate RR-05 |
| OI-3 | Agree the evidence-status definitions and the CG structure with the assessor |
| OI-4 | Link CSn items to `trace/` entries once WP-S-07 CSRs are added there |
| OI-5 | Update [WP-M-00](../01-management/WP-M-00-work-product-register.md) status for WP-K-03 (register shows Skeleton; this version is a Draft argument) |
