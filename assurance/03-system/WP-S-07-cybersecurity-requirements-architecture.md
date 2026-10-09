# WP-S-07 Cybersecurity Requirements and Architectural Design

| Field | Value |
|---|---|
| Work product | WP-S-07 Cybersecurity requirements and architectural design |
| Standard reference | ISO/SAE 21434:2021 §10 (product development: refinement of cybersecurity requirements, architectural design, cybersecurity controls); §9.5 (concept, as input); ASPICE 4.0 SEC.1, SYS.3 |
| Version | 0.1 |
| Status | Draft — requirements are proposals derived from code review and the concept; not verified, not approved |
| ASIL / scope | CS (CAL 1–3); requirements with a safety relation reference the provisional TSR-5xx/TSR-4xx parents (up to ASIL C) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); CS assessor sampling per [WP-M-09 §8](../01-management/WP-M-09-cybersecurity-plan.md) |
| Approver | Project maintainer (acting cybersecurity manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

> Defensive engineering document. It states requirements and architecture for protection
> mechanisms. It contains no exploitation procedures, payloads or key material.

## 1. Purpose and inputs

This work product refines the concept-level requirements CSR-C-01…CSR-C-16 of [WP-C-10 §7](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) into detailed cybersecurity requirements CSR-nnn, allocates them to architectural elements, and describes the security architecture (trust boundaries, secure boot chain, safety-mode lock, update path, remote surface, local integrity). Verification of each CSR is specified and tracked in [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md); validation in [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md).

| Input | Used for |
|---|---|
| [WP-C-09 TARA](../02-concept/WP-C-09-tara.md) | AS-01…AS-16, DS-01…DS-12, TS-01…TS-13, AP-01…AP-13, risk values |
| [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) | CSG-01…CSG-08, CSC-01…CSC-05, CA-01…CA-05, CSR-C-01…CSR-C-16, CAL proposals |
| [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) | Scope, tailoring CT-1…CT-4, OI-1 (signing), OI-2 (remote features), OI-3 (updater) |
| [WP-C-04 FSC](../02-concept/WP-C-04-functional-safety-concept.md) | FSR-01.08 (SoC→panda frame integrity), FSR-01.10 (safety-mode lock, debug gating) |
| [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md) | HWSR-502c (boot pins), HWSR-503c (flash integrity), HWSR-506c (relay debug drive) |
| [WP-S-02 TSR](../03-system/WP-S-02-technical-safety-requirements.md) | **Does not exist yet.** TSR parents below are provisional (see §8) |
| Gap assessment | GAP-01, GAP-09, GAP-10, GAP-18, GAP-20, GAP-22, GAP-24…GAP-29, GAP-34, GAP-38, GAP-40, GAP-41 |

## 2. Conventions

**Numbering.** `CSR-<cc><n>`: the two digits `cc` are the number of the parent CSR-C, `n` is a sequence 1–9. Example: CSR-011 is the first refinement of CSR-C-01. IDs are never reused.

**Attributes.** ID, statement (one "shall"), parent CSR-C (and CSG), CAL (inherited from the parent unless stated), allocation, safety relation (provisional TSR / FSR / HWSR and ASIL where the CSR also protects a safety goal), verification method, status, and current implementation evidence or GAP.

**Allocation classes** (per [WP-C-10 §6](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md)): **FW** = panda firmware incl. bootstub (E-03); **SoC** = AGNOS userland and LionDriver host software (E-01/E-02); **ENV** = back end / build and release environment / operational environment (external or project infrastructure); **USR** = owner, installer, maintainer acting under a procedure.

**Verification methods.** R = design/code review; BA = build-configuration audit (automated check on the release build); UT = unit test (libpanda / libsafety / pytest); HIL = bench test on panda or comma device ([WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md) bench rules); FZ = interface fuzzing (bench); A = analysis; PR = procedure review; CM = configuration audit; PT = penetration test ([WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md)).

**Status values.** `Proposed` (all CSRs at this version). The *Evidence* column records what the baseline does today.

Paths are relative to the repository root. `safety.h` is `opendbc_repo/opendbc/safety/safety.h`.

## 3. Security architecture

### 3.1 Elements and security zones

| Zone | Elements | Trust level | Basis |
|---|---|---|---|
| Z1 Safety MCU | panda STM32H7: bootstub (flash sector 0), application firmware, option bytes, opendbc safety code (E-03) | Trusted; the only element that must stay intact under attack (envelope pattern, [WP-M-01 §4](../01-management/WP-M-01-assurance-strategy.md)) | CSG-01, CSG-02 |
| Z2 SoC — safety-relevant host | pandad, card/controlsd, selfdrived, modeld, dmonitoringmodeld, plannerd, params store, msgq | QM; **assumed compromisable**; must not be able to defeat Z1 | CSG-03, CSG-04 |
| Z3 SoC — network-facing | athenad, uploader, updated, sshd, webrtcd, UI, installer | Untrusted input handlers | CSG-06, CSG-07, CSG-08 |
| Z4 External network and back end | comma athena/connect, GitHub, LFS store, AGNOS CDN, Wi-Fi/LTE | Untrusted (CA-01, CA-02, CA-04) | CSC-02, CSC-04 |
| Z5 Vehicle bus | Toyota ECUs, OBD-II port, harness | Untrusted for injection (CA-03) | CSG-05, CSC-01 |
| Z6 Release environment | LionDriver signing keys (offline), release build host, release record | Trusted, outside the device | CSG-02, CSG-07 |
| Z7 Physical device | eMMC/UFS storage, `/persist`, `/data`, debug ports | Owner-controlled (CA-05) | CSG-08 |

### 3.2 Trust boundaries

```text
              Z6 Release environment (offline keys, release build, release record)
                    |  signed panda image + signed update manifest (TB-6)
                    v
 Z4 Network / back end  ==TB-3==>  +------------------- comma device ---------------------+
 (athena, GitHub, LFS,             |  Z3 network-facing QM: athenad, updated, uploader,     |
  AGNOS CDN; untrusted)            |     sshd, webrtcd(127.0.0.1), installer, UI            |
                                   |        |  params / msgq / filesystem (TB-4)            |
                                   |        v                                               |
                                   |  Z2 safety-relevant host (QM): pandad, card, controlsd,|
                                   |     selfdrived, modeld, dmonitoringmodeld, plannerd    |
                                   |        |                                               |
                                   |        |  TB-1: SPI/USB command channel                 |
                                   |        |  TB-2: BOOT0 / NRST GPIO lines                 |
                                   |        v                                               |
                                   |  Z1 panda STM32H7: ROM BL -> bootstub -> app (envelope)|
                                   |     option bytes RDP/WRP                               |
                                   +-------------|------------------------------------------+
                                                 | TB-5: vehicle CAN (bus 0 car side,
                                                 |       bus 2 camera side, relay)
                                                 v
                                   Z5 Toyota ECUs, OBD-II port, forward camera (PCS)
 Z7 physical: storage at rest, /persist identity key  ==TB-7== (theft, loss, resale)
```

| ID | Boundary | Data / control crossing | Threats (TS) | Controls (CSR) |
|---|---|---|---|---|
| TB-1 | Z2 → Z1 command channel (SPI/USB) | Safety mode/param `0xdc`, alternative experience `0xdf`, bus config `0xdb`/`0xde`, relay debug `0xc5`, softloader `0xd1`, CAN TX frames | TS-02, TS-05, TS-12 | CSR-011…CSR-016, CSR-021…CSR-024, CSR-061 |
| TB-2 | Z2 → Z1 boot control (GPIO) | `STM_BOOT0`, `STM_RST_N` (`openpilot/common/hardware/comma/hardware.py:401-419`) | TS-03 | CSR-041…CSR-043, CSR-051…CSR-054 |
| TB-3 | Z4 ↔ Z3 network | athena RPCs, uploads, SSH, git updates, AGNOS images, LFS objects | TS-06, TS-07, TS-08, TS-10 | CSR-101…CSR-104, CSR-111…CSR-117, CSR-121…CSR-126, CSR-131…CSR-136 |
| TB-4 | Z3 → Z2 local integrity | Params, msgq, model files, filesystem | TS-04, TS-09, TS-12 | CSR-062…CSR-064, CSR-071…CSR-073, CSR-081…CSR-083 |
| TB-5 | Z1 ↔ Z5 vehicle CAN | RX plausibility inputs, TX actuation, PCS forwarding | TS-01 | CSR-091…CSR-093 |
| TB-6 | Z6 → device | Signed images and manifests; release key material never crosses | TS-05, TS-06, TS-10 | CSR-031…CSR-034, CSR-121, CSR-126, CSR-136 |
| TB-7 | Z7 physical | Data and keys at rest | TS-11, TS-13 | CSR-141…CSR-144, CSR-151, CSR-152 |

**Architectural principle (from the safety envelope pattern).** Every safety-relevant protection is placed at Z1 or below it in the trust order, so that the safety argument does not depend on the SoC being uncompromised. SoC-side controls (Z2/Z3) reduce the likelihood of SoC compromise and protect privacy; they are not credited as the last line of defence for any safety goal. The single exception, which is not yet resolved, is SoC control of the boot pins (TB-2, §3.4).

### 3.3 Secure boot chain (recommendation)

Current chain at the baseline: ST ROM bootloader (immutable) → panda bootstub in flash sector 0 → application. The bootstub checks a length/version tag (`panda/board/bootstub.c:47-60`) and an RSA-1024 signature over a SHA-1 digest against `release_rsa_key` (`bootstub.c:63`; `panda/board/crypto/rsa.h:37`, `sha.h:45`), and in DEBUG builds also against the committed debug key (`bootstub.c:67-72`). The key-header generator asserts a 1024-bit modulus (`panda/SConscript:32-46`). Builds default to DEBUG with `-DALLOW_DEBUG` unless `RELEASE` and `CERT` are set (`panda/SConscript:12-20`). No RDP/WRP option bytes are set anywhere in the code; the in-application flasher only refuses to erase sector 0 (`panda/board/stm32h7/llflash.h:14`).

Target chain for the reference configuration:

| Stage | Recommendation | CSR |
|---|---|---|
| Key | LionDriver panda release key pair generated offline by the maintainer; private key on offline media, never in Git, CI or the release host's persistent storage; public key replaces `release.pub` in the panda fork. Separate key pair from the update-signing key (CSR-126) | CSR-032, CSR-126 |
| Algorithm | Modern signature scheme with ≥ 128-bit security (Ed25519 or ECDSA P-256) and SHA-256 or stronger, using a small, widely reviewed implementation suitable for a bootstub. Selection is a CCB decision ([WP-P-10 §6](../07-supporting/WP-P-10-release-management.md): bootstub changes need a separate CCB decision) | CSR-031 |
| Release-only key acceptance | Release bootstub is built without `ALLOW_DEBUG`, so the debug key is not compiled in and is never accepted; the build fails if `RELEASE`/`CERT` are missing for a release target; the committed debug key is treated as public | CSR-021, CSR-022 |
| Anti-rollback | Minimum accepted firmware version stored in protected flash/option bytes, not only as a compile-time constant | CSR-033 |
| Bootstub immutability | WRP on the bootstub sector(s) set at provisioning | CSR-042 |
| Read-out / debug protection | RDP set at provisioning; level decided per CS-AD-02 | CSR-041 |
| First provisioning | Devices arrive with comma's bootstub and key. Installing the LionDriver bootstub is a one-time, bench-only provisioning step under [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md), followed by setting WRP/RDP and recording option bytes and image hashes | CSR-043 |
| Runtime integrity | Application CRC/hash at start-up and periodically (safety requirement HWSR-503c); complements, does not replace, the boot signature | CSR-034 |

### 3.4 SoC control of the panda boot pins

The SoC can drive `STM_BOOT0`/`STM_RST_N` and so start the STM32 ROM bootloader (`hardware.py:410-419`), and `pandad` automatically flashes a development bootstub when the firmware does not boot (`openpilot/selfdrive/pandad/pandad.py:34-39`). With the ROM bootloader reachable, signature checks in the bootstub do not protect against an SoC-root attacker who can erase and reprogram the MCU (GAP-38, TS-03, risk 5). WP-H-01 HWSR-502c states the same from the safety side.

Architecture decisions (proposed, for CCB and assessor agreement):

| ID | Decision | Rationale | Residual |
|---|---|---|---|
| CS-AD-01 | Remove the automatic development-bootstub recovery from release builds of pandad; recovery flashes only the release-signed image from the installed release and requires an explicit offroad owner action | Removes the automatic unsigned-firmware path | SoC root can still drive GPIOs directly |
| CS-AD-02 | Evaluate the STM32H7 RDP levels against RM0468 for whether the ROM bootloader can still erase/program flash at each level. Choose the level that prevents ROM-bootloader reprogramming if one exists, accepting the loss of field recovery (irreversible levels must be a recorded decision) | Only a hardware-enforced setting closes TB-2 without a PCB change | To be determined (OI-2) |
| CS-AD-03 | If no RDP level closes TB-2, record a cybersecurity claim (retain) that firmware substitution requires SoC root, and credit SoC hardening (CSR-062…CSR-064, CSR-101…CSR-117, CSR-121) as likelihood reduction only; feed the residual into the TARA iteration ([WP-C-09](../02-concept/WP-C-09-tara.md) OI-5) and the CS case as a defeater | Honest residual; a PCB change (removing SoC control of BOOT0) is outside LionDriver's control (T-04) | Risk not below 3 until re-rated |
| CS-AD-04 | Safety direction: in the ROM bootloader the GPIOs are at reset state and the relay is expected to be released (HWSR-502), which is the safe direction for SG-01/SG-07. The threat is substitution, not the bootloader state itself | Confirms the hazard is integrity, not availability | Depends on HWSR-502 being confirmed |

### 3.5 Safety-mode lock

Today `0xdc` calls `set_safety_mode(param1, param2)` with no check (`panda/board/main_comms.h:223-225`); pandad takes the mode and parameter from `CarParams` in the unauthenticated params store (`openpilot/selfdrive/pandad/panda_safety.cc:56-69`). Alternative experience (`0xdf`) is settable only in a non-car mode (`main_comms.h:242-247`), but the SoC can switch to a non-car mode, set it and switch back.

Design for the release firmware of the reference configuration:

1. The permitted car configuration is a compile-time constant of the release build: safety model `toyota`, safety parameter as recorded in the release record (73 at this baseline, per [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-23), alternative experience 0.
2. Permitted transitions: non-actuating modes (SILENT, NOOUTPUT) ↔ the locked car configuration. Any request for another mode, parameter or alternative-experience value is rejected, leaves the panda in a non-actuating mode, and sets a reported fault.
3. Commands that change bus configuration or relay state (`0xc5`, `0xdb`, `0xde`, loopback) are rejected while a car mode is active (command allow-list).
4. SoC-side cross-check (defence in depth, QM): pandad compares the panda-reported mode/param with the release record and blocks engagement on mismatch.

This design serves CSG-01 and FSR-01.10 at the same time; the safety requirement is the provisional TSR-512 (§8).

### 3.6 Authenticated update path

Today: `updated` fetches a branch chosen by the `UpdaterTargetBranch` param or the current branch (`openpilot/system/updated/updated.py:237-245`), force-checks out `FETCH_HEAD`, resets, cleans and updates submodules (`:387-399`); AGNOS images are checked against hashes in `agnos.json` taken from the same unsigned tree (`:205-222`). `DisableUpdates` stops the updater (`:416`).

Target: a LionDriver release manifest (release ID, git tree commit including submodule pins, AGNOS version and image hashes, panda image hash, model artefact hashes, minimum version) signed with the offline update key. The device verifies the manifest signature with a pinned public key before staging, verifies the fetched tree against the manifest commit, and verifies every artefact hash before use. Until it exists, automatic updates are disabled and updates are installed manually ([WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) UPD-02). The process side (staged rollout, rollback, notification) is in [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md).

### 3.7 Reduced remote surface (reference configuration)

| Feature | Baseline | Reference configuration (proposed under CT-4) |
|---|---|---|
| athenad | Always running daemon (`openpilot/system/manager/process_config.py:71`); server from `ATHENA_HOST` env (`athenad.py:51`); RPCs `athenad.py:354-807` | **Disabled** by default. If the owner opts in: `ATHENA_HOST` override ignored in release, upload destinations allow-listed, SSH tunnel and authorized-key RPCs removed, `getMessage` allow-listed |
| SSH | Off by default (`SshEnabled`, `openpilot/common/params_keys.h:124`); INTERNAL installer enables it with an embedded CI key (`openpilot/selfdrive/ui/installer/installer.cc:204-213`) | Off; INTERNAL path excluded from LionDriver builds; owner-managed keys only if enabled |
| Live streaming | webrtcd only when `IsLiveStreaming` or not a car (`process_config.py:119`); flag cleared on ignition-on (`params_keys.h:62`); onroad requests refused (`openpilot/system/webrtc/helpers.py:28`); binds 127.0.0.1:5001 (`webrtcd.py:640-641`) | Keep as is; regression test |
| Updates | git branch updater | Disabled until CSR-121 (manual updates) |
| Uploads to comma | Uploader / athena | Off unless the owner opts in; driver camera not uploaded by default |

### 3.8 Params and IPC integrity for safety-relevant keys

The params store is unauthenticated flat files and msgq shared memory has no publisher authentication (GAP-20). The architecture does **not** try to make SoC-local IPC secure against a root attacker; it (a) makes the envelope independent of params/IPC (CSR-061), (b) restricts who can write safety-relevant keys and publish safety-relevant topics against non-root compromise of network-facing processes (CSR-062…CSR-064), and (c) removes developer modes from release builds (CSR-071…CSR-073).

Safety-relevant keys (initial list; maintained with [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md)): `CarParams`, `CarParamsCache`, `ExperimentalMode` (default "1", `params_keys.h:43`, GAP-18), `DisengageOnAccelerator`, `IsDriverViewEnabled`, `JoystickDebugMode`, `LongitudinalManeuverMode`, `LateralManeuverMode`, `DisableUpdates`, `UpdaterTargetBranch`, `SshEnabled`, `GithubSshKeys`. `SecOCKey` (`params_keys.h:120`) is not used on the 2020 Corolla (no SecOC flag) and is out of scope for the reference configuration.

## 4. Detailed cybersecurity requirements

### 4.1 CSR-C-01 Safety configuration lock (CSG-01, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-011 | Release panda firmware for the reference configuration shall accept a car safety mode only if model, parameter and alternative experience equal the compile-time locked values recorded in the release record. | FW | TSR-512 (prov.), FSR-01.10, ASIL C | R, UT, HIL | Not implemented: `0xdc` unconditional (`main_comms.h:223-225`) (GAP-09) |
| CSR-012 | A rejected safety-configuration request shall leave the panda in a non-actuating mode and set a fault flag reported to the SoC in the health packet. | FW | TSR-512, ASIL C | UT, HIL | Not implemented |
| CSR-013 | Transitions from the locked car mode to SILENT or NOOUTPUT shall remain permitted at all times. | FW | TSR-512 (availability of safe state) | UT, HIL | Implemented generically (`set_safety_mode` accepts any mode); keep under the lock |
| CSR-014 | While a car safety mode is active, release firmware shall reject host commands outside a documented allow-list, including relay drive (`0xc5`), CAN mode/speed changes (`0xdb`, `0xde`) and loopback. | FW | TSR-512, TSR-513 (prov.) | R, UT, FZ | Not implemented; `0xc5` ungated (`main_comms.h:144-147`), `0xdb`/`0xde` ungated (`:219-240`) |
| CSR-015 | Alternative experience shall not be changeable in release firmware for the reference configuration. | FW | TSR-512 | UT | Partial: only in non-car mode (`main_comms.h:242-247`), bypassable by mode switching |
| CSR-016 | pandad shall compare the panda-reported safety model, parameter and alternative experience with the release-record values and prevent engagement and raise an alert on mismatch. | SoC | TSR-6xx (QM, defence in depth) | UT, HIL | Not implemented; pandad takes values from `CarParams` (`panda_safety.cc:56-69`) |

### 4.2 CSR-C-02 No debug capability in release firmware (CSG-01/CSG-02, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-021 | The release panda firmware and bootstub shall be built with `RELEASE` and the LionDriver certificate, and the release build shall fail if `ALLOW_DEBUG` is defined. | FW; ENV | TSR-513 (prov.), FSR-01.10 | BA | Not met: DEBUG + `ALLOW_DEBUG` is the default (`panda/SConscript:12-20`) (GAP-25) |
| CSR-022 | The release bootstub shall not contain the debug public key and shall accept no key other than the LionDriver release key. | FW | TSR-511 (prov.) | BA, HIL | Conditional: debug key accepted only under `ALLOW_DEBUG` (`bootstub.c:67-72`); correct only if CSR-021 holds |
| CSR-023 | Debug-only host commands (relay drive `0xc5`, ALLOUTPUT mode, bootloader entry, debug sleep) shall be absent from release firmware. | FW | TSR-513, HWSR-506c | BA, R, FZ | Partial: ALLOUTPUT (`safety.h:413-422`), `0xd1` param 0 (`main_comms.h:170`), `0xb5` (`:92`) gated; `0xc5` not gated (GAP-09) |
| CSR-024 | Softloader entry (`0xd1` param 1) shall be accepted only while the panda is in a non-actuating mode and the vehicle ignition is off. | FW | TSR-513; H-02/H-06 (loss of function) | UT, HIL | Not implemented: allowed in release at any time (`main_comms.h:176-179`) (GAP-24) |

### 4.3 CSR-C-03 Authenticated firmware boot (CSG-02, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-031 | The bootstub shall verify the application image with a signature scheme of at least 128-bit security strength and a SHA-256-or-stronger digest before transferring control. | FW | TSR-511 (prov.), ASIL C | R, HIL | Not met: RSA-1024 / SHA-1 (`rsa.h:37`, `sha.h:45`; 1024-bit assert `SConscript:32-46`) (GAP-24) |
| CSR-032 | The verifying public key shall be the LionDriver panda release key, whose private key is generated and held offline and never stored in the repository, CI or logs. | FW; ENV | TSR-511 | CM, PR | Not met: `release.pub` is comma's (`bootstub.c:63`); LionDriver key not yet generated ([WP-P-10 §6](../07-supporting/WP-P-10-release-management.md)) |
| CSR-033 | The bootstub shall reject an image whose version is below a minimum version held in write-protected storage. | FW | TSR-511 | UT, HIL | Partial: `MIN_VERSION` compile-time check (`bootstub.c:2, 58`); not field-updatable or protected |
| CSR-034 | The application image integrity shall be re-checked at start-up and periodically at run time, with mismatch leading to the safe state. | FW | HWSR-503c / TSR-503, ASIL C | HIL, FI | Not implemented (GAP-24) |

### 4.4 CSR-C-04 Flash protection (CSG-02, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-041 | The panda option bytes shall be set at provisioning to an RDP level chosen by CS-AD-02 that prevents read-out and debug-port access to the firmware. | FW; USR | TSR-511, HWSR-502c | HIL (option-byte read), PR | Not implemented (GAP-38) |
| CSR-042 | Write protection shall be set on the bootstub sector(s) so that neither the application nor the softloader can modify them. | FW; USR | TSR-511 | HIL | Not implemented; only a software refusal to erase sector 0 (`llflash.h:14`) |
| CSR-043 | Installation shall record the option-byte values and the bootstub and application hashes, and compare them with the release record. | USR | TSR-8xx (prov.) | PR | Not in [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-17 today (version/signature only) |

### 4.5 CSR-C-05 No unauthenticated recovery path (CSG-02, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-051 | Release pandad shall not flash a development bootstub; recovery shall flash only the release-signed bootstub and application of the installed release. | SoC | TSR-511 | R, HIL | Not met: development bootstub flashed on boot failure (`pandad.py:34-39`) (GAP-38) |
| CSR-052 | SoC use of `STM_BOOT0` for recovery shall occur only on explicit offroad owner action and shall be logged as a security event. | SoC; USR | TSR-511 | R, HIL | Not met: automatic (`hardware.py:410-419` via `pandad.py:37-38`) |
| CSR-053 | pandad shall not set a car safety mode unless the panda reports the firmware version and signature recorded in the release record. | SoC | TSR-6xx (QM, detection) | UT, HIL | Partial: pandad checks the signature against the locally built image (`pandad.py:18-31`); not against a release record |
| CSR-054 | The architecture shall prevent SoC control of `STM_BOOT0`/`STM_RST_N` from resulting in execution of firmware not signed with the LionDriver release key, or the residual shall be recorded as a cybersecurity claim per CS-AD-03. | FW; SoC; USR | HWSR-502c, TSR-511 | A, HIL | Not met (GAP-38); depends on CS-AD-02 |

### 4.6 CSR-C-06 Params and IPC (CSG-03, CAL 2)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-061 | The panda envelope limits and checks shall not depend on any value from the SoC params store or msgq other than the locked safety configuration of CSR-011. | FW | TSR-1xx/2xx/3xx, FFI ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)) | R, A | Partly met by design (limits are compile-time constants in opendbc safety); the configuration itself is the gap (GAP-09) |
| CSR-062 | Safety-relevant params (§3.8) shall be writable only by their designated writer processes, enforced by OS file permissions, and their values shall be checked against the release record at manager start with engagement blocked on mismatch. | SoC | TSR-6xx (QM) | R, UT | Not implemented (GAP-20) |
| CSR-063 | Each safety-relevant msgq topic consumed by controlsd, selfdrived, plannerd or dmonitoringd shall be publishable only by its designated process, and a second publisher shall be detected and reported. | SoC | TSR-6xx (QM) | R, UT | Not implemented (GAP-20) |
| CSR-064 | Network-facing processes (athenad, uploader, updated, webrtcd, UI) shall run without permission to write safety-relevant params or publish safety-relevant topics. | SoC | — (likelihood reduction) | R, PT | Not determined: process user/privilege model on AGNOS to be reviewed (OI-5) |

### 4.7 CSR-C-07 Developer modes (CSG-03, CAL 2)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-071 | Release builds shall not start the joystick, longitudinal-maneuver or lateral-maneuver replacement processes regardless of params. | SoC | TSR-6xx; GAP-20 | BA, UT | Not met: param-gated only (`process_config.py:34-47`) |
| CSR-072 | Driver-view demo mode (`IsDriverViewEnabled`) shall not affect driver-monitoring output while onroad. | SoC | TSR-6xx (DM) | UT | Not implemented (GAP-20) |
| CSR-073 | The release build check shall fail if any developer-mode entry point is reachable in the release configuration. | ENV | — | BA | Not implemented |

### 4.8 CSR-C-08 Model artefacts (CSG-04, CAL 2)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-081 | modeld and dmonitoringmodeld shall load model artefacts and metadata without deserializing executable objects (no `pickle` of artefact content). | SoC | AIR (WP-C-11), GAP-22 | R, UT | Not met: `pickle` at `modeld.py:150,159`, `dmonitoringmodeld.py:33,48`; `helpers.py:19-20` |
| CSR-082 | Before loading, every model artefact shall be verified against a SHA-256 hash in the authenticated release manifest, and the process shall refuse to run on mismatch so that engagement is blocked. | SoC | AIR; TSR-6xx | UT, HIL | Not implemented (GAP-22) |
| CSR-083 | Model artefacts shall be fetched from LionDriver-controlled storage and their hashes recorded in the release record. | ENV; USR | D-05 | CM | Not met: `.lfsconfig` points to comma's store (GAP-40); INS-18 records hashes manually |

### 4.9 CSR-C-09 Vehicle CAN (CSG-05, CAL 2)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-091 | Panda firmware shall verify every checksum and counter that the vehicle provides on safety-relevant RX messages, and shall cross-check messages that carry none (brake `0x226`, wheel speed `0xAA`) for plausibility against independent signals. | FW | TSR-4xx (prov.), GAP-01 | R, UT, HIL | Partial: 8-bit checksums on some messages; none on `0x226`/`0xAA`; no counters (GAP-01) |
| CSR-092 | Panda firmware shall transmit only allow-listed actuation messages on the car-side bus and shall not alter camera-originated PCS messages it forwards. | FW | TSR-7xx, SG-07 | R, UT | Implemented in part: Toyota TX allow-list (`opendbc_repo/opendbc/safety/modes/toyota.h:6-19`); forwarding verification per TSR-7xx |
| CSR-093 | Reception on the car-side bus of an actuation message ID that the panda transmits, while the relay intercepts, shall be detected and lead to actuation inhibit. | FW | TSR-506, HWSR-506b | UT, HIL | Partial: relay-malfunction detection on intercepted IDs (`safety.h:372-380`); timing per HWSR-506a |

Residual risk of physical injection after CSR-091…093 is retained under CSC-01.

### 4.10 CSR-C-10 SSH (CSG-06, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-101 | LionDriver installer and image builds shall not contain an embedded authorized SSH key or set `SshEnabled`. | SoC; ENV | — | BA | Not met for INTERNAL builds (`installer.cc:204-213`) |
| CSR-102 | `SshEnabled` shall be false in the reference configuration and checked at installation. | USR | — | PR | Process exists: [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-19 |
| CSR-103 | When the owner enables SSH, only key authentication with owner-provided keys shall be accepted. | SoC | — | R, PT | To verify against AGNOS sshd configuration (OI-5) |
| CSR-104 | SSH shall not accept new sessions while the vehicle is onroad. | SoC | — | HIL, PT | Not implemented (proposal; decision OI-3) |

### 4.11 CSR-C-11 Remote RPC (CSG-06, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-111 | athenad shall not run in the reference configuration unless the owner opts in. | SoC; USR | — | BA, PR | Not met: daemon always started (`process_config.py:71`) |
| CSR-112 | If enabled, file uploads requested over athena shall go only to allow-listed destination hosts over TLS with certificate validation. | SoC | — | UT, PT | Not met: arbitrary URL (`athenad.py:619-672`) (GAP-27) |
| CSR-113 | If enabled, the SSH-tunnel and authorized-key RPCs shall be absent. | SoC | — | UT, PT | Not met (`athenad.py:710-757`) |
| CSR-114 | If enabled, `getMessage` shall serve only allow-listed, non-personal services. | SoC | — | UT | Not met: any service (`athenad.py:354-370`) |
| CSR-115 | Release builds shall ignore the `ATHENA_HOST` environment override. | SoC | — | BA, UT | Not met (`athenad.py:51`) |
| CSR-116 | Onroad camera streaming shall remain impossible, and webrtcd shall bind only to the loopback interface. | SoC | — | UT, PT | Implemented: `params_keys.h:62`, `process_config.py:119`, `helpers.py:28`, `webrtcd.py:640-641`; regression test needed |
| CSR-117 | No safety function shall depend on athena or any back-end availability. | SoC | CA-01 | HIL (network off) | Believed met (athenad is not in the control path); not verified |

### 4.12 CSR-C-12 Software updates (CSG-07, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-121 | The updater shall stage an update only after verifying a LionDriver-signed release manifest (§3.6) and every artefact against it. | SoC; ENV | TSR-8xx (prov.) | R, UT, PT | Not implemented: TLS + in-tree hashes (`updated.py:205-222, 387-399`) (GAP-26) |
| CSR-122 | Release builds shall fix the update origin and accept only release-channel branches, ignoring `UpdaterTargetBranch` values outside it. | SoC | TSR-8xx | UT | Not met (`updated.py:237-245`) |
| CSR-123 | The updater shall reject a manifest whose release version is lower than the installed one unless the manifest is a signed rollback release. | SoC; ENV | — | UT | Not implemented |
| CSR-124 | Until CSR-121 is implemented, `DisableUpdates` shall be set in the reference configuration and updates installed manually per WP-O-02 UPD-02. | USR | — | PR | Mechanism exists (`updated.py:416`); procedure in [WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) |
| CSR-125 | Update installation shall be offroad-only and atomic, with the previous release remaining bootable if finalization fails. | SoC | UPD-05 | R, HIL | Partial: offroad-only (`process_config.py:114`); overlay and consistency flag (`updated.py:201, 217`); rollback not specified |
| CSR-126 | The update-signing key shall be distinct from the panda release key, held offline, and covered by a re-keying procedure. | ENV | — | PR | Not implemented ([WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)) |

### 4.13 CSR-C-13 Supply chain (CSG-07, CAL 3)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-131 | All submodules shall point to LionDriver-controlled forks and be pinned by commit. | ENV | D-01 | CM | Not met: relative URLs to `commaai/*`; tinygrad `branch = master` (`.gitmodules`) (GAP-29) |
| CSR-132 | No release dependency or tool shall be resolved from a mutable reference (branch or tag without hash). | ENV | GAP-34 | CM, BA | Not met: cppcheck from `rev=release-cppcheck` (`uv.lock:586`); tinygrad master |
| CSR-133 | Every release shall have an SBOM covering `uv.lock` packages, submodule commits, LFS artefacts, AGNOS version and images, comma-deps wheels and the panda toolchain. | ENV | — | CM | Not implemented ([WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-4) |
| CSR-134 | Every release and the current release weekly shall be scanned against public vulnerability data, with each finding assessed before release. | ENV | — | CM | Not implemented ([WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md), [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)) |
| CSR-135 | Release signing material shall never be available to CI jobs triggered from pull requests or forks. | ENV | — | CM, R | No LionDriver signing in CI yet; comma's `Jenkinsfile` uses comma certificates (GAP-30) |

### 4.14 CSR-C-14 Personal data and identity key (CSG-08, CAL 2)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-141 | The device identity private key shall be readable only by the processes that sign with it and shall not be exposed through any RPC, log or upload. | SoC | — | R, PT | To verify: key at `/persist/comma/` (`openpilot/common/api.py:61-62`) |
| CSR-142 | Driver-facing video, cabin imagery and location logs shall be encrypted at rest, or, if AGNOS cannot provide this, driver-camera recording shall be off by default and retention bounded. | SoC; USR | — | R, HIL | Unknown (WP-C-09 OI-3) |
| CSR-143 | Any data upload shall use TLS with certificate validation to an approved endpoint. | SoC; ENV | — | R, PT | To verify per uploader |
| CSR-144 | Driver-camera video shall not be uploaded unless the owner opts in. | SoC; USR | — | R, PR | Depends on `RecordFront` and uploader policy (WP-O-01 INS-19) |

### 4.15 CSR-C-15 Decommissioning (CSG-08, CAL 2)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-151 | The decommissioning procedure shall erase user data and the device identity keys in `/persist/comma/`. | USR; SoC | TSR-8xx | PR, HIL | Procedure drafted ([WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) DEC-07, DEC-08); tool not defined (WP-O-02 OI-5) |
| CSR-152 | Decommissioning shall revoke the device's credentials at every LionDriver endpoint and remove owner SSH keys. | USR; ENV | — | PR | Procedure drafted (DEC-09, DEC-10) |

### 4.16 CSR-C-16 Vulnerability handling (CAL 1)

| ID | Statement | Alloc | Safety relation | Verif | Evidence at baseline |
|---|---|---|---|---|---|
| CSR-161 | LionDriver shall publish a security policy with a private reporting channel it controls. | USR; ENV | — | PR | Not met: `SECURITY.md:5` routes to comma (GAP-28) |
| CSR-162 | Vulnerability analysis, incident response and update management shall run per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) from G6. | USR | WP-O-04 field actions | PR | Not running |

## 5. Requirement summary

| Parent | CSG | CAL | CSRs | Count |
|---|---|---|---|---|
| CSR-C-01 | CSG-01 | 3 | CSR-011…016 | 6 |
| CSR-C-02 | CSG-01, CSG-02 | 3 | CSR-021…024 | 4 |
| CSR-C-03 | CSG-02 | 3 | CSR-031…034 | 4 |
| CSR-C-04 | CSG-02 | 3 | CSR-041…043 | 3 |
| CSR-C-05 | CSG-02 | 3 | CSR-051…054 | 4 |
| CSR-C-06 | CSG-03 | 2 | CSR-061…064 | 4 |
| CSR-C-07 | CSG-03 | 2 | CSR-071…073 | 3 |
| CSR-C-08 | CSG-04 | 2 | CSR-081…083 | 3 |
| CSR-C-09 | CSG-05 | 2 | CSR-091…093 | 3 |
| CSR-C-10 | CSG-06 | 3 | CSR-101…104 | 4 |
| CSR-C-11 | CSG-06 | 3 | CSR-111…117 | 7 |
| CSR-C-12 | CSG-07 | 3 | CSR-121…126 | 6 |
| CSR-C-13 | CSG-07 | 3 | CSR-131…135 | 5 |
| CSR-C-14 | CSG-08 | 2 | CSR-141…144 | 4 |
| CSR-C-15 | CSG-08 | 2 | CSR-151…152 | 2 |
| CSR-C-16 | — | 1 | CSR-161…162 | 2 |
| | | | **Total** | **64** |

Allocation totals: FW 20, SoC 31, ENV 16, USR 15 (a CSR may have more than one allocation).

## 6. Cybersecurity specifications for the interfaces

| Interface | Specification needed (owner WP) | Content |
|---|---|---|
| TB-1 host command set | Command allow-list table per safety mode ([WP-S-05 HSI](../03-system/WP-S-05-hsi-specification.md)) | Each `0xNN` request: permitted in SILENT / NOOUTPUT / car mode; release vs debug; parameter ranges; reaction to violation |
| TB-2 boot control | Boot-pin use policy (WP-S-05, WP-O-01) | When the SoC may assert BOOT0/NRST; logging; provisioning-only operations |
| TB-3 update manifest | Manifest format and key handling (WP-O-05, WP-P-10) | Fields in §3.6, signature scheme, key IDs, rotation |
| TB-4 params/IPC | Writer/publisher table (WP-W-03) | Key or topic → designated writer → consumers → safety relevance |
| TB-6 signing | Key ceremony record (WP-P-10) | Generation, storage, use log, revocation |

## 7. Relation to the cybersecurity concept and claims

| Claim / assumption | How this WP supports it |
|---|---|
| CSC-01 (retain physical CAN residual) | CSR-091…CSR-093 implement CSG-05 to the extent the vehicle allows |
| CSC-02 (share back-end security) | CSR-111…CSR-117 minimize the device-side surface; CSR-117 ensures no safety dependency |
| CSC-03 (retain non-repudiation) | CSR-141 protects the identity key |
| CSC-04 (share OTS supply chain) | CSR-131…CSR-134 pin, inventory and monitor |
| CSC-05 (avoid eGPU) | Not refined here; eGPU excluded from the reference configuration (WP-C-01 E-06) |

## 8. Relation to technical safety requirements

[WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) does not exist yet. The brief reserves TSR-5xx for safety-MCU platform integrity including safety-mode lock, debug gating and boot integrity; [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md) already uses TSR-501…TSR-510 and references TSR-511 for boot-pin control. This document uses the following **provisional** parents and must be re-aligned when WP-S-02 is written (OI-1):

| Provisional TSR | Topic | Upstream FSR / HWSR | CSRs that implement or support it |
|---|---|---|---|
| TSR-511 | Firmware and boot integrity; SoC boot-pin control | FSR-01.10; HWSR-502c, HWSR-503c | CSR-022, CSR-031…CSR-034, CSR-041…CSR-043, CSR-051…CSR-054 |
| TSR-512 | Safety-mode and parameter lock | FSR-01.10 | CSR-011…CSR-015, CSR-061 |
| TSR-513 | Debug capability absent in release | FSR-01.10; HWSR-506c | CSR-014, CSR-021, CSR-023, CSR-024 |
| TSR-503 | Memory/flash integrity | HWSR-503c | CSR-034 |
| TSR-4xx | SoC↔panda and vehicle CAN integrity | FSR-01.08; GAP-01, GAP-10 | CSR-091 (vehicle side); SPI integrity is a safety requirement only (a compromised SoC computes valid CRCs, so it gives no security) |
| TSR-6xx | Host-side monitoring (QM) | — | CSR-016, CSR-053, CSR-062, CSR-063, CSR-071, CSR-072, CSR-082 |
| TSR-8xx | Production, operation, decommissioning | WP-S-06 | CSR-043, CSR-121, CSR-122, CSR-151 |

Consistency rule: where a CSR and a TSR state the same mechanism (e.g. CSR-011 and TSR-512), the stricter verification applies (ASIL C methods per ISO 26262-6 plus CAL 3 methods per [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md)), and one implementation satisfies both. Conflicts between safety and security (e.g. RDP level vs field recovery, CSR-024 vs firmware update availability) are resolved by the CCB with the safety manager and recorded as CS-AD decisions.

## 9. Traceability

| From | To |
|---|---|
| TS-02 → CSG-01 → CSR-C-01, CSR-C-02 | CSR-011…CSR-016, CSR-021…CSR-024 |
| TS-03, TS-05 → CSG-02 → CSR-C-02…CSR-C-05 | CSR-021…CSR-054 |
| TS-04, TS-12 → CSG-03 → CSR-C-06, CSR-C-07 | CSR-061…CSR-073 |
| TS-09 → CSG-04 → CSR-C-08 | CSR-081…CSR-083 |
| TS-01 → CSG-05 → CSR-C-09 | CSR-091…CSR-093 |
| TS-07, TS-08, TS-13 → CSG-06 → CSR-C-10, CSR-C-11 | CSR-101…CSR-117 |
| TS-06, TS-10 → CSG-07 → CSR-C-12, CSR-C-13 | CSR-121…CSR-135 |
| TS-11, TS-07 → CSG-08 → CSR-C-14, CSR-C-15 | CSR-141…CSR-152 |
| (process) → CSR-C-16 | CSR-161, CSR-162 |

Machine-readable trace entries go to `trace/` per [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) (OI-6).

## Open items

| ID | Item |
|---|---|
| OI-1 | Re-align provisional parents TSR-511/512/513 (and TSR-4xx/6xx/8xx) with WP-S-02 when it is written; mirror any renumbering in WP-H-01 OI-1 |
| OI-2 | CS-AD-02: determine from RM0468 which STM32H7 RDP level, if any, prevents ROM-bootloader reprogramming; decide the level with the safety manager (irreversibility, field recovery) |
| OI-3 | Decide CSR-104 (SSH blocked onroad) and the opt-in policy for athenad (CSR-111) under CT-4 / [WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-2 |
| OI-4 | Select the bootstub signature scheme and implementation (CSR-031) and the update manifest format (CSR-121); CCB decision required |
| OI-5 | Review the AGNOS process user/privilege model and sshd configuration (CSR-064, CSR-103) |
| OI-6 | Add CSR-nnn to `trace/` with parent, CAL and allocation attributes |
| OI-7 | Confirm the safety-relevant params list (§3.8) with WP-W-09 and the host-side TSR-6xx author |
| OI-8 | Assessor agreement that SoC-side controls are credited for likelihood reduction only (§3.2 principle, CS-AD-03) |
