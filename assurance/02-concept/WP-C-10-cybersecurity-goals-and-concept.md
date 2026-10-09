# WP-C-10 Cybersecurity Goals, Claims and Concept

| Field | Value |
|---|---|
| Work product | WP-C-10 Cybersecurity goals, claims and concept |
| Standard reference | ISO/SAE 21434:2021 §9.4 (cybersecurity goals and claims), §9.5 (cybersecurity concept); ASPICE 4.0 SEC.1 |
| Version | 0.1 |
| Status | Draft — goals and CAL proposals are for review; not approved until the preliminary cybersecurity assessment passes |
| ASIL / scope | CS (cybersecurity); safety relation traced to SG-01…SG-07 |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); preliminary cybersecurity assessment by an independent assessor |
| Approver | Project maintainer (acting cybersecurity manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

> Defensive concept document. It states cybersecurity goals, claims and the controls that
> meet them. It contains no exploitation detail or key material.

## 1. Purpose and inputs

This work product derives the cybersecurity goals (CSG-nn) from the threat scenarios rated at risk ≥ 3 in the [TARA (WP-C-09)](WP-C-09-tara.md), states cybersecurity claims (CSC-nn) for risks that are retained or shared, and gives a concept-level set of controls and requirements (CSR-C-nn) allocated to architectural elements. It implements §9 of the [cybersecurity plan (WP-M-09)](../01-management/WP-M-09-cybersecurity-plan.md) and feeds [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md), which refines CSR-C-nn into detailed requirements CSR-nnn.

Inputs: [WP-C-09](WP-C-09-tara.md) (assets AS-nn, damage scenarios DS-nn, threat scenarios TS-nn, risk values); [WP-C-01](WP-C-01-item-definition.md) (elements E-01…E-06, interfaces IF-01…IF-09); [WP-C-03](WP-C-03-hara.md) (safety goals SG-01…SG-07); gap assessment GAP-09, GAP-20, GAP-22, GAP-24…GAP-28, GAP-38.

## 2. Cybersecurity assumptions on external entities

Per tailoring T-11 and CT-2, these entities are outside the item; the concept depends on the assumptions below and does not claim to secure them. They mirror AOU-11 in [WP-C-01](WP-C-01-item-definition.md).

| ID | Assumption | Entity | If it fails |
|---|---|---|---|
| CA-01 | No safety function depends on the comma.ai back end, connect or athena server being trustworthy or available | comma.ai services | Covered by CSG-06 (remote-access attack surface reduced) |
| CA-02 | The GitHub-hosted source and the update origin can be compromised; LionDriver must authenticate code and updates itself | GitHub / update origin | Covered by CSG-04, CSG-07 |
| CA-03 | The vehicle bus is accessible to anyone with physical access; Toyota ECUs apply their own internal plausibility only | Toyota ECUs, bus | Covered by CSG-01, CSG-05 |
| CA-04 | The network (Wi-Fi/LTE) is untrusted | network | Covered by CSG-06 |
| CA-05 | The owner physically controls the device in normal operation; theft/loss is a bounded, reportable event | owner / device | Covered by CSG-08 |

## 3. Cybersecurity assurance level (CAL) scheme

CAL 1–4 per ISO/SAE 21434 Annex, proposed from the risk value and the attack-vector/feasibility of the driving threat scenario. Higher risk and more remote/feasible vectors raise the CAL, which sets verification rigour in [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) and test depth in [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md).

| Risk | Dominant vector | CAL proposal |
|---|---|---|
| 5, safety impact | local-to-safety-element or physical-fleet | CAL 3 |
| 4, safety impact, remote/network-reachable | network or update | CAL 3 |
| 4, safety impact, local/physical only | local/physical | CAL 2 |
| 4, privacy impact | physical/remote | CAL 2 |
| 3 | any | CAL 1–2 |

No CAL is claimed as achieved here; these are proposals for the assessor (WP-M-09 §8).

## 4. Cybersecurity goals

Each goal traces to the TARA threat scenario(s) at risk ≥ 3 that it addresses. A goal is a top-level cybersecurity requirement on the item (§9.4): it states the property to be preserved, not the mechanism.

| ID | Cybersecurity goal | Addresses TS (risk) | CAL proposal | CAL rationale |
|---|---|---|---|---|
| **CSG-01** | The integrity and authenticity of the panda safety configuration (safety mode and parameter) shall be protected so that no unauthenticated SoC-side command can place the envelope in an unsafe configuration | TS-02 (5) | **CAL 3** | Directly defeats the ASIL-C safety envelope from an always-present local interface (GAP-09); highest risk |
| **CSG-02** | The integrity and authenticity of the panda firmware and its boot chain shall be protected so that only authorized firmware runs on the safety MCU | TS-03 (5), TS-05 (4) | **CAL 3** | Firmware *is* the envelope; boot-pin + dev-bootstub path and weak signing both reach it (GAP-38/24/25) |
| **CSG-03** | Safety-relevant parameters and inter-process messages shall not alter actuation, model output or driver-monitoring behaviour without integrity and authenticity protection | TS-04 (5), TS-12 (4) | **CAL 2** | Local access required, but unauthenticated and directly safety-affecting (GAP-20/23) |
| **CSG-04** | ML model artefacts shall be loaded only after their integrity and authenticity are verified, and loading shall not permit code execution from the artefact | TS-09 (4) | **CAL 2** | `pickle` load is code execution; delivery needs another channel (GAP-22) |
| **CSG-05** | The integrity and authenticity of safety-relevant vehicle-CAN messages (received plausibility inputs and transmitted actuation) shall be protected against injection consistent with the physical-access threat | TS-01 (4) | **CAL 2** | Physical access needed; no RX E2E today (GAP-01) |
| **CSG-06** | Remote access and interactive access to the device shall be minimized and authenticated so that a compromised back end or network cannot reach safety functions or exfiltrate personal data | TS-07 (4), TS-08 (4), TS-13 (3) | **CAL 3** | Network-reachable; SSH/RPC can reach root and personal data (GAP-27, installer SSH) |
| **CSG-07** | Software updates shall be installed only after their integrity and authenticity are verified end-to-end | TS-06 (4), TS-10 (4) | **CAL 3** | Network-reachable fleet vector; unsigned git-branch path and supply chain (GAP-26/29/34) |
| **CSG-08** | Personal data (driver-facing video, cabin imagery, location/trajectory) and the device identity key shall be protected in confidentiality, in transit and at rest, including after loss or decommissioning | TS-11 (5), TS-07 (4) | **CAL 2** | Privacy-dominant; physical/remote vectors (DS-08/09/12) |

## 5. Cybersecurity claims (retained / shared risks)

Claims (§9.4) record risks that are **not** reduced to zero by a goal — they are retained with rationale, or shared with another party — and the condition under which the claim holds.

| ID | Claim | Risk basis | Type | Condition |
|---|---|---|---|---|
| **CSC-01** | Residual risk of physical CAN injection (TS-01) after CSG-05 is retained to the level of any vehicle with an accessible OBD port; it is not raised by the item beyond adding one more connector | TS-01 residual | Retain | CSG-05 E2E implemented; physical access to the cabin assumed controlled (CA-05) |
| **CSC-02** | The security of the comma.ai back end and network transport is shared with comma.ai and the network operator; LionDriver claims only that no safety function depends on them (CA-01/CA-04) | TS-07 external part | Share | CSG-06 constrains/disables the device-side interface |
| **CSC-03** | Non-repudiation of device-origin data (TS-13) is retained at the level provided by the per-device identity key; stronger non-repudiation is out of scope for the reference configuration | TS-13 (3) | Retain | CSG-08 protects the identity key; per-device keys in use |
| **CSC-04** | Supply-chain assurance for off-the-shelf binaries (AGNOS, eGPU firmware, toolchain wheels) is shared with their suppliers; LionDriver claims identity (hash) pinning and advisory monitoring, not source-level verification | TS-10 OTS part | Share | SBOM + monitoring running ([WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)); pins by hash |
| **CSC-05** | Risk from the optional Chestnut eGPU is avoided in the reference configuration by excluding it (consistent with WP-C-01 E-06) | TS-09/TS-12 eGPU part | Avoid | eGPU excluded until GAP-17/GAP-22 analysis completes |

## 6. Cybersecurity concept — controls allocated to elements

The concept assigns controls to the architectural elements of [WP-C-01 §3.1](WP-C-01-item-definition.md): **panda FW (E-03)**, **SoC (E-01/E-02)**, **back end / operational environment** (external, CT-2), and **user** (owner/installer). "Avoid" controls remove an entity or feature from the reference configuration (decided here under CT-4 and WP-M-09 OI-2).

| Goal | Control (concept level) | Allocated to |
|---|---|---|
| CSG-01 | Lock the safety mode/parameter in panda FW for the reference configuration, or add an independent in-FW cross-check that rejects unexpected mode/param; remove/gate debug relay drive `0xc5` and softloader entry in release | panda FW |
| CSG-02 | LionDriver-controlled boot chain with a modern signature algorithm; enable RDP/WRP option bytes; remove debug-key acceptance from release; remove or authenticate the pandad dev-bootstub recovery path; constrain SoC control of boot pins | panda FW; SoC (pandad); user (provisioning, WP-O-01) |
| CSG-03 | Integrity/authenticity on safety-relevant params and msgq topics consumed by control/DM, or architect the envelope to not depend on SoC-supplied params; disable debug/maneuver/joystick process-replacement modes in release builds | SoC; panda FW (independence) |
| CSG-04 | Replace `pickle` model loading with a non-executable format; verify model hash/signature at load against a release manifest | SoC (modeld, dmonitoringmodeld) |
| CSG-05 | Add E2E (rolling counter + CRC) to RX plausibility (including brake `0x226`, wheel-speed `0xAA`) and TX actuation; keep physical-access assumption recorded | panda FW; back end (none); user (physical control) |
| CSG-06 | Disable SSH by default and remove the embedded-key installer path from LionDriver builds; disable or scope-restrict athena RPCs (no arbitrary-URL upload, no SSH tunnel, no key read) in the reference configuration; keep onroad streaming blocked | SoC (athenad, installer); user (opt-in) |
| CSG-07 | Replace the git-branch updater with a signed update package verified end-to-end (not only TLS + in-tree hashes); fork and commit-pin safety submodules; generate an SBOM and scan dependencies; pin mutable tool/model branches | SoC (updated); back end (signing infra); user |
| CSG-08 | Encrypt personal data and the identity key at rest; protect the key in use; provide a decommissioning wipe and a key-revocation step ([WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md)); minimize uploaded personal data | SoC; back end (transport); user (decommissioning) |

## 7. Concept-level cybersecurity requirements (CSR-C-nn)

These are concept-level requirements. [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) refines each into detailed requirements CSR-nnn allocated to design elements and verified in [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md). Status reflects baseline `8b8c6ae`.

| ID | Requirement (one statement) | Parent CSG | CAL | Allocation | Verification method | Status / evidence |
|---|---|---|---|---|---|---|
| CSR-C-01 | The panda firmware shall enforce the Toyota safety mode and reject any mode/parameter change from the SoC that is not authorized for the reference configuration | CSG-01 | 3 | panda FW | Review + test (fault injection) | Not implemented; `0xdc` unauthenticated (GAP-09, `main_comms.h:222-225`) |
| CSR-C-02 | Release panda firmware shall not accept a debug signing key and shall not enable debug-only capabilities (ALLOUTPUT, unrestricted relay drive, softloader) | CSG-01, CSG-02 | 3 | panda FW | Review + build-config audit | Not implemented; DEBUG+`ALLOW_DEBUG` default (GAP-25, `SConscript:12-20`) |
| CSR-C-03 | The safety MCU shall boot only firmware whose integrity and authenticity are verified with a current cryptographic algorithm | CSG-02 | 3 | panda FW | Review + test | Not implemented; RSA-1024/SHA-1 (GAP-24, `rsa.h:37`, `sha.h:45`) |
| CSR-C-04 | Flash read/write protection (RDP/WRP) shall be configured so the running safety firmware cannot be replaced or read out without authorization | CSG-02 | 3 | panda FW; user (provisioning) | Option-byte inspection | Not implemented; no RDP/WRP in code (GAP-38, `llflash.h:14`) |
| CSR-C-05 | The recovery/bootloader path reachable from the SoC shall not flash unauthenticated (development) firmware in the reference configuration | CSG-02 | 3 | panda FW; SoC (pandad) | Review + test | Not implemented; dev bootstub flashed on boot failure (GAP-38, `pandad.py:34-39`) |
| CSR-C-06 | Safety-relevant parameters and IPC messages shall be integrity- and authenticity-protected, or the safety envelope shall not depend on them | CSG-03 | 2 | SoC; panda FW | Review + FFI analysis ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) | Not implemented; unauthenticated params/IPC (GAP-20) |
| CSR-C-07 | Developer process-replacement modes (debug, maneuver, joystick) shall be absent or disabled in reference-configuration builds | CSG-03 | 2 | SoC | Build-config audit | Not implemented (GAP-20, `process_config.py:34-47`) |
| CSR-C-08 | ML model artefacts shall be loaded without executing code from the artefact, and only after an integrity/authenticity check against a release manifest | CSG-04 | 2 | SoC (modeld, dmonitoringmodeld) | Review + test | Not implemented; `pickle` load, no hash check (GAP-22, `modeld.py:150,159`) |
| CSR-C-09 | Received safety-relevant CAN messages and transmitted actuation shall carry freshness and integrity protection (counter + CRC) sufficient for the physical-access threat | CSG-05 | 2 | panda FW | Review + test | Not implemented; no RX E2E (GAP-01) |
| CSR-C-10 | SSH shall be disabled by default and shall not ship with an embedded authorized key; if enabled, access shall use owner-managed keys | CSG-06 | 3 | SoC (installer, athenad) | Build-config audit + test | Not met; INTERNAL build pre-enables SSH with an embedded key (`installer.cc:204-223`) |
| CSR-C-11 | Remote RPCs in the reference configuration shall not permit arbitrary-URL upload, SSH tunnelling or authorized-key disclosure, and onroad camera streaming shall remain blocked | CSG-06 | 3 | SoC (athenad); back end | Review + test | Partially: onroad streaming blocked (`helpers.py:28`); RPCs otherwise unrestricted (GAP-27, `athenad.py:355-807`) |
| CSR-C-12 | Software updates shall be installed only after end-to-end integrity and authenticity verification of the complete package, independent of the transport | CSG-07 | 3 | SoC (updated); back end (signing) | Review + test | Not implemented; git force-checkout, in-tree hashes (GAP-26, `updated.py:238,387-399`) |
| CSR-C-13 | Safety-relevant source components shall be under LionDriver configuration control, pinned by commit, with an SBOM and dependency vulnerability scanning | CSG-07 | 3 | SoC build; user (process) | CM audit ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)) | Not met; submodules resolve upstream, tinygrad tracks master (GAP-29, `.gitmodules`) |
| CSR-C-14 | Driver-facing video, cabin imagery, location data and the device identity key shall be protected in confidentiality in transit and at rest | CSG-08 | 2 | SoC; back end (transport) | Review + test | Not confirmed; encryption at rest unverified (OI-3) |
| CSR-C-15 | Decommissioning shall wipe personal data and revoke/retire the device identity key | CSG-08 | 2 | SoC; user ([WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md)) | Procedure review | Not implemented |
| CSR-C-16 | A LionDriver vulnerability intake and incident-response process shall exist | — (supports all) | 1 | user / operational env. | Process review | Not met; routes to comma (GAP-28, [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)) |

## 8. Relation to safety goals

Cybersecurity goals protect the HARA safety goals by preventing an attacker from inducing the same hazards the safety goals address. This is the §9.5 interface between the cybersecurity concept and the functional safety concept ([WP-C-04](WP-C-04-functional-safety-concept.md)).

| Safety goal (ASIL) | Protected by CSG | How |
|---|---|---|
| SG-01 lateral authority (C/D) | CSG-01, CSG-02, CSG-03, CSG-05 | Safety-mode integrity, firmware authenticity, param/IPC integrity and CAN integrity keep an attacker from commanding excess lateral torque (H-01) |
| SG-02 no silent loss of lateral control (B) | CSG-02, CSG-03, CSG-06 | Firmware authenticity and DoS resistance prevent silent lateral-control loss (H-02); remote-access reduction removes a DoS vector |
| SG-03 no unintended acceleration (B/C) | CSG-01, CSG-02, CSG-03, CSG-05 | Same envelope-integrity chain applied to the longitudinal command (H-03) |
| SG-04 bounded deceleration (B/C) | CSG-01, CSG-02, CSG-03, CSG-05 | Envelope integrity bounds attacker-induced deceleration (H-04) |
| SG-05 override/disengage (B/C) | CSG-01, CSG-03, CSG-05 | Protecting engagement/override logic and its inputs keeps the driver able to override (H-05) |
| SG-06 no silent loss of deceleration (B) | CSG-02, CSG-03, CSG-06 | Firmware authenticity and DoS resistance prevent silent longitudinal-control loss (H-06) |
| SG-07 stock PCS preserved (B) | CSG-02, CSG-05 | Firmware and CAN integrity keep the item from suppressing/altering forwarded PCS messages (H-08) |

Two cross-cutting dependencies: **safety-mode integrity** (CSG-01) and **firmware authenticity** (CSG-02) protect every safety goal, because they are the common point where a cybersecurity attack and a functional-safety failure converge on the envelope. The freedom-from-interference argument in [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) and the dependent-failure analysis in [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md) must treat an attacker on the SoC as a credible common-cause source, not only random SoC faults.

## Open items

| ID | Item |
|---|---|
| OI-1 | Resolve the panda signing/boot-chain decision (shared [WP-M-09 OI-1](../01-management/WP-M-09-cybersecurity-plan.md)); it fixes the achievable CAL for CSG-01/CSG-02 |
| OI-2 | Confirm the reference-configuration feature set (SSH off, athena RPC scope, developer modes off, Experimental Mode) so CSG-03/CSG-06 become firm requirements (CT-4, [WP-M-09 OI-2](../01-management/WP-M-09-cybersecurity-plan.md)) |
| OI-3 | Confirm whether encryption at rest exists on AGNOS for personal data and the identity key (dimensions CSG-08/CSR-C-14) |
| OI-4 | Agree the CAL proposals in §3–§4 with the independent assessor |
| OI-5 | Decide the signed-update design (CSG-07/CSR-C-12), replacing the git-branch updater ([WP-M-09 OI-3](../01-management/WP-M-09-cybersecurity-plan.md)) |
| OI-6 | Confirm the SG↔CSG mapping in §8 with the FSC author once [WP-C-04](WP-C-04-functional-safety-concept.md) exists; today it depends on the HARA only |
| OI-7 | Hand CSR-C-01…CSR-C-16 to [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) for refinement into CSR-nnn; keep the CAL and allocation attributes consistent |
