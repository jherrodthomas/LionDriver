# WP-V-06 Cybersecurity Validation and Penetration Testing

| Field | Value |
|---|---|
| Work product | WP-V-06 Cybersecurity validation and penetration testing (plan, specification, report) |
| Standard reference | ISO/SAE 21434:2021 §11 (cybersecurity validation of the item at vehicle level), §10 (verification inputs), §15 (TARA as basis); UN R155 (informative); ASPICE 4.0 SEC.4 |
| Version | 0.1 |
| Status | Draft — plan and specification written; **no validation or penetration test has been executed and no tester is engaged** ([WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-6). All result sections are "Not yet executed" |
| ASIL / scope | CS (CAL 1–3); safety relation to SG-01…SG-07 |
| Author | Assurance team (initial draft); report to be authored by the penetration tester |
| Reviewer(s) | TBD (I1); results reviewed by the cybersecurity assessor ([WP-K-05](../10-safety-case/WP-K-05-cybersecurity-assessment.md)) |
| Approver | Project maintainer (acting cybersecurity manager); safety manager for rules of engagement |
| Baseline | `8b8c6ae` (plan); tests run on a named release candidate |

> This is a test plan for defensive validation. It describes test objectives and categories at
> the level a validation plan needs. It contains no exploit procedures, payloads or key material.
> Detailed test procedures are produced by the independent tester under the rules of
> engagement in §5 and stored with access restricted to the project and the assessor.

## 1. Purpose

Cybersecurity validation confirms, on the integrated item in its reference configuration, that the cybersecurity goals CSG-01…CSG-08 of [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) are achieved, that the cybersecurity claims CSC-01…CSC-05 are valid, and that no unreasonable residual risk remains. Penetration testing provides independent evidence that the controls specified in [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) and verified in [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md) are effective against the attack paths AP-01…AP-13 of the [TARA](../02-concept/WP-C-09-tara.md).

## 2. Scope

| In scope | Out of scope |
|---|---|
| comma device (SoC + AGNOS + LionDriver release) and panda STM32H7 firmware of the release candidate | comma.ai back-end services, GitHub, AGNOS CDN (external entities, CT-2; tested only as the device sees them) |
| Interfaces TB-1…TB-7 ([WP-S-07 §3.2](../03-system/WP-S-07-cybersecurity-requirements-architecture.md)) | Toyota ECU internals (CA-03) |
| Update path, provisioning and decommissioning procedures | Attacks on public infrastructure or third-party systems |
| Reference vehicle (2020 Corolla LE) on bench or closed course for CAN-level tests | Any test on public roads |
| Release build configuration only (GAP-41) | DEBUG builds, except as the negative control on the bench |

Configuration under test: the release candidate identified by tag, panda image hash, AGNOS version and model hashes ([WP-P-10](../07-supporting/WP-P-10-release-management.md)); parameters per [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md) INS-19/20.

## 3. Objectives per cybersecurity goal

| CSG | CAL | Validation objective | Main attack paths | Evidence expected |
|---|---|---|---|---|
| CSG-01 | 3 | Show that no command from a fully compromised SoC can place the panda in a non-locked safety configuration or drive the relay in car mode | AP-02 | Command-interface fuzzing and allow-list tests (TC-01, TC-02) |
| CSG-02 | 3 | Show that only LionDriver-release-signed firmware runs on the panda, including after SoC-driven reset/boot-mode sequences, and that option bytes match provisioning | AP-03, AP-05 | Firmware authenticity tests (TC-03…TC-05) |
| CSG-03 | 2 | Show that tampering with safety-relevant params or IPC from a non-root foothold cannot change actuation limits, disable DM or start developer modes; and that the envelope bounds actuation even with root on the SoC | AP-04, AP-12 | Local-integrity tests (TC-06, TC-07) |
| CSG-04 | 2 | Show that a modified model artefact is not loaded and cannot execute code | AP-09 | Artefact integrity tests (TC-08) |
| CSG-05 | 2 | Show robustness of the envelope against injected or replayed CAN traffic within the physical-access threat, and that CSC-01 residual is as claimed | AP-01 | CAN robustness tests (TC-09, TC-10) |
| CSG-06 | 3 | Show that the reference configuration exposes no remote or interactive access beyond the approved set, and that opted-in features are restricted | AP-07, AP-08, AP-13 | Remote-interface hardening review and tests (TC-11…TC-13) |
| CSG-07 | 3 | Show that only authenticated updates are installed, downgrades are refused, and the supply-chain controls hold for the release | AP-06, AP-10 | Update integrity tests (TC-14, TC-15) |
| CSG-08 | 2 | Show that personal data and the identity key are protected at rest and in transit and removed by decommissioning | AP-11, AP-13 | Data-protection and decommissioning tests (TC-16, TC-17) |

## 4. Test categories

Each test case (TC) states the objective, the CSRs covered, the environment and the pass criterion. Procedures are written by the tester. Test depth follows the CAL ([WP-W-11 §2](../05-software/WP-W-11-cybersecurity-implementation-verification.md)).

| TC | Category | Objective (high level) | CSRs | Environment | Pass criterion |
|---|---|---|---|---|---|
| TC-01 | Interface fuzzing — SPI/USB command handler | Coverage-guided and grammar-based fuzzing of the host→panda request set and CAN-send path on a bench panda running release firmware; monitor for crash, hang, reset, unexpected mode or relay change | CSR-011…CSR-015, CSR-023, CSR-024 | Bench panda (no vehicle), release image; also libpanda host build for coverage | No state change outside the allow-list; no crash/hang that leaves the relay driven or TX enabled; all faults end in the safe state |
| TC-02 | Safety-configuration lock | Attempt every safety model, parameter and alternative-experience value and every mode sequence from the SoC | CSR-011…CSR-016 | Bench device with panda | Only the locked configuration and non-actuating modes reachable; rejection reported |
| TC-03 | Firmware authenticity | Present unsigned, debug-signed, tampered and older signed images through every flashing route available to the SoC | CSR-021, CSR-022, CSR-031…CSR-033 | Bench panda | Only current LionDriver-signed image boots |
| TC-04 | Boot-pin and recovery path | Exercise SoC-driven reset/boot-mode sequences and pandad recovery; verify what firmware runs afterwards and that recovery never installs development firmware | CSR-051…CSR-054 | Bench device | Matches the CS-AD-02/03 decision; no development bootstub installed; events logged |
| TC-05 | Option bytes and read-out protection | Read option bytes and attempt debug-port access per the chosen RDP level | CSR-041…CSR-043 | Bench panda (sacrificial unit if RDP regression is tested) | Option bytes equal provisioning record; protection effective as specified |
| TC-06 | Params / IPC integrity | From a non-root foothold representing a compromised network-facing process, attempt to change safety-relevant params and publish safety-relevant topics | CSR-062…CSR-064, CSR-071, CSR-072 | Bench device, offroad and simulated onroad (replay) | Writes and foreign publishers denied or detected; engagement blocked on mismatch |
| TC-07 | Envelope independence under SoC compromise | With root on the SoC (assumed), command maximal actuation through the normal path | CSR-061; TSR-1xx/2xx (envelope) | HIL bench with replayed Corolla CAN | Panda TX never exceeds the envelope limits ([WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md)) |
| TC-08 | Model artefact integrity | Replace or modify model artefacts and metadata | CSR-081, CSR-082 | Bench device | Modified artefact refused; no code execution from artefact; engagement blocked |
| TC-09 | CAN robustness — injection and replay | Inject, replay and flood frames on the car-side and camera-side buses within the physical-access threat; observe envelope and relay-malfunction reaction | CSR-091…CSR-093 | Bench with CAN interface first; then **closed course** with the reference vehicle, safety driver, ignition-on/stationary before any motion | No actuation outside the envelope; injected actuation IDs detected; PCS forwarding unaltered; no reaction worse than the stock vehicle with an OBD device (CSC-01) |
| TC-10 | CAN availability | Bus-load and error-frame conditions | CSR-091; TSR-508 | Bench | Safe-state reaction and driver warning as specified |
| TC-11 | Remote interface hardening review | Port scan and service enumeration on Wi-Fi/LTE; configuration review of sshd, athenad, webrtcd, uploader; TLS configuration | CSR-101…CSR-104, CSR-111, CSR-115, CSR-116, CSR-143 | Bench device on an isolated test network | Only approved listeners; loopback-only webrtcd; no SSH unless owner opt-in; TLS validated |
| TC-12 | Opt-in remote features | With athenad opted in, against a test server controlled by the tester: attempt non-allow-listed uploads, tunnel and key RPCs, non-allow-listed services, onroad streaming | CSR-112…CSR-114, CSR-116 | Isolated test network with tester-run server | All refused |
| TC-13 | Back-end independence | Disable network and back end during engagement on the HIL bench | CSR-117 | HIL bench | No effect on envelope or engagement logic |
| TC-14 | Update integrity | Offer unsigned, altered, wrongly-keyed, downgraded and partially downloaded updates from a tester-controlled update origin | CSR-121…CSR-125 | Bench device, isolated update server | Only valid signed newer (or signed rollback) releases staged; interrupted update leaves a bootable release |
| TC-15 | Supply-chain configuration audit | Verify SBOM completeness, pins and scan report of the release candidate | CSR-131…CSR-135 | Desk review | BA-07/BA-08 pass; no untreated reachable finding with risk ≥ 3 |
| TC-16 | Data at rest and identity key | With physical possession of a bench device, check protection of stored video, location logs and identity key; check key permissions and log exposure | CSR-141, CSR-142, CSR-144 | Bench device (no owner data) | Meets the CSR-142 decision; key not exposed |
| TC-17 | Decommissioning | Execute WP-O-02 DEC-06…DEC-10 and check residual data and keys | CSR-151, CSR-152 | Bench device | No user data or identity key recoverable by the defined method |
| TC-18 | Vulnerability intake | Submit a test report through the published channel | CSR-161, CSR-162 | Desk | Acknowledged within the [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) target |

## 5. Rules of engagement

| Rule | Detail |
|---|---|
| RoE-1 Location | Bench, HIL bench, or **closed course only**. No cybersecurity test on public roads under any circumstance. Vehicle-level tests follow [WP-V-07](WP-V-07-vehicle-test-operations.md) (safety driver, closed course, abort procedures) |
| RoE-2 Vehicle | CAN tests on the vehicle start with ignition on and the vehicle stationary; motion only on a closed course after the bench results for the same TC passed; safety driver can disconnect the harness (stock path) at any time |
| RoE-3 Targets | Only LionDriver-owned devices, vehicles and tester-controlled servers. No testing against comma.ai, GitHub, Hugging Face, AGNOS CDN or any third-party service; their endpoints are replaced by tester-controlled stand-ins |
| RoE-4 Network isolation | Remote-interface tests on an isolated network; no traffic to the internet from the device under test during TC-11…TC-14 |
| RoE-5 Data | Bench devices carry no personal data of real occupants; test data only |
| RoE-6 Keys | Testers never receive LionDriver release or update private keys; test keys are generated for the test and destroyed afterwards |
| RoE-7 Hardware risk | Tests that may permanently alter option bytes or brick a unit use sacrificial units, agreed in advance |
| RoE-8 Findings confidentiality | Findings are handled as embargoed vulnerabilities per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) until fixed or accepted; procedures and tooling are not published |
| RoE-9 Stop conditions | Any unexpected actuation or loss of the stock path on the vehicle stops testing immediately and opens an S-1 problem report ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)) |
| RoE-10 Independence | The penetration tester is independent of the implementer of the controls under test ([WP-M-09 §3](../01-management/WP-M-09-cybersecurity-plan.md)) |

## 6. Entry criteria

1. TARA, goals and concept ([WP-C-09](../02-concept/WP-C-09-tara.md), [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md)) approved after the preliminary assessment.
2. [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) approved; architecture decisions CS-AD-01…CS-AD-04 recorded.
3. Release candidate built in release configuration; build-config audit BA-01…BA-08 passed ([WP-W-11 §7](../05-software/WP-W-11-cybersecurity-implementation-verification.md)).
4. VS-CS verification for CAL 3 CSRs executed with no open failure, or each open failure accepted for test by the CS manager.
5. Bench, HIL bench (D-04) and closed-course arrangements available; RoE signed by tester, maintainer and safety manager.
6. Tester engaged with independence and competence evidence ([WP-M-04](../01-management/WP-M-04-organization-competence-safety-culture.md)).

## 7. Exit criteria

1. Every TC executed, or not executed with a written rationale accepted by the CS manager and the assessor.
2. No open finding rated **Critical** or **High**; each Medium/Low finding fixed, or accepted as residual risk with a TARA re-rating ([WP-C-09](../02-concept/WP-C-09-tara.md) OI-5) and a CS case entry ([WP-K-03](../10-safety-case/WP-K-03-cybersecurity-case.md)).
3. Every CSG has validation evidence or a recorded claim; CSC-01…CSC-05 confirmed valid.
4. Safety-impacting findings evaluated by the safety manager for the safety case ([WP-K-01](../10-safety-case/WP-K-01-safety-case.md) G4).
5. Report reviewed by the cybersecurity assessor.

## 8. Finding rating

| Rating | Definition | Release effect |
|---|---|---|
| Critical | A path to a safety-goal violation (DS-01…DS-07, DS-11) with feasibility High or Medium | Blocks release |
| High | A path to a safety-goal violation with feasibility Low, or to DS-08/DS-12 with feasibility High/Medium | Blocks release unless risk treated |
| Medium | Weakness that requires another weakness to reach an asset, or privacy impact with Low feasibility | Fix or accept with rationale |
| Low / Info | Hardening recommendation | Backlog |

The rating is mapped to the TARA risk value and to problem severity S-1…S-4 per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md).

## 9. Results — Not yet executed

### 9.1 Execution record template

| Field | Value |
|---|---|
| Release candidate (tag, panda hash, AGNOS, models) | Not yet executed |
| Tester (organisation, independence statement) | Not yet executed |
| Dates and locations (bench / HIL / closed course) | Not yet executed |
| RoE sign-off reference | Not yet executed |
| Deviations from this plan | Not yet executed |

### 9.2 Results per test case

| TC | Executed (Y/N) | Result (Pass / Fail / Partial / N/A) | Findings | Evidence reference |
|---|---|---|---|---|
| TC-01 … TC-18 | Not yet executed | — | — | — |

### 9.3 Findings

| Finding ID | TC | Rating | Asset / CSG | Summary (no exploit detail) | Status | WP-O-05 ref |
|---|---|---|---|---|---|---|
| — | — | — | — | Not yet executed | — | — |

### 9.4 Conclusion per CSG

| CSG | Achieved? | Residual risk statement | Reference |
|---|---|---|---|
| CSG-01 … CSG-08 | Not yet executed | — | — |

## Open items

| ID | Item |
|---|---|
| OI-1 | Engage an independent penetration tester ([WP-M-09](../01-management/WP-M-09-cybersecurity-plan.md) OI-6) |
| OI-2 | Build the HIL bench (D-04) and a bench panda setup able to run release images with a LionDriver test key |
| OI-3 | Decide sacrificial-unit budget for TC-05 (option bytes / RDP) |
| OI-4 | Define tester-controlled stand-ins for the athena server and update origin (TC-12, TC-14) |
| OI-5 | Agree with the safety manager the closed-course procedure additions for TC-09 in [WP-V-07](WP-V-07-vehicle-test-operations.md) |
| OI-6 | Agree the finding rating scheme (§8) with the assessor |
