# WP-M-01 Assurance Strategy and Lifecycle Tailoring

| Field | Value |
|---|---|
| Work product | WP-M-01 Assurance strategy and lifecycle tailoring |
| Standard reference | ISO 26262-2:2018 §6 (tailoring, safety plan inputs); ISO 21448:2022 §4; ISO/SAE 21434:2021 §6; ISO/PAS 8800:2024 (AI safety management, assurance argument); ASPICE 4.0 MAN.3; UL 4600 (informative, safety case structure) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (FuSa, SOTIF, CS, AI, process) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review of tailoring rationale by independent assessor (I3) |
| Approver | Project maintainer (acting safety manager). Self-approval is an accepted interim limitation until a second person takes the safety manager or reviewer role ([WP-M-02](WP-M-02-safety-plan.md) OI-2) |
| Baseline | `8b8c6ae` |

## 1. Purpose

This document is the "assurance path" for LionDriver. It sets out:

1. what LionDriver will claim, and for which configuration,
2. the safety architecture argument that makes those claims achievable on inherited openpilot hardware and software,
3. how each standard is applied and where it is tailored, with rationale,
4. the phases, gates and work products that take the project from today's baseline to a release decision,
5. the strategic decisions the project must take, and the risks to the plan.

The [safety plan (WP-M-02)](WP-M-02-safety-plan.md), [SOTIF plan (WP-M-08)](WP-M-08-sotif-plan.md), [cybersecurity plan (WP-M-09)](WP-M-09-cybersecurity-plan.md) and [AI safety plan (WP-M-10)](WP-M-10-ai-safety-plan.md) carry out this strategy for their own disciplines. The [work product register (WP-M-00)](WP-M-00-work-product-register.md) lists every output.

## 2. Starting point

From the [baseline gap assessment](../00-assessment/gap-assessment.md):

- LionDriver is upstream openpilot (≈ v0.11.2). The only change so far is to `README.md`. The safety-enforcement code (`opendbc_repo/opendbc/safety`, `panda/board`) comes in through git submodules that point at upstream `commaai` repositories.
- The engineering practice is strong where it matters most: the opendbc safety layer has MISRA C:2012 checking, a 100% line-coverage gate, mutation testing and per-brand safety tests. **These run only in upstream opendbc CI (`opendbc_repo/.github/workflows/tests.yml`), not in LionDriver's CI, so today they produce no evidence under LionDriver control.** The process work products are missing: there are no requirements, architecture, plans, traceability or review records. Most process areas are at ASPICE capability level 0.
- The hardware (comma 3X/four with an integrated STM32H7 "panda" safety MCU) is a commercial product. It was not developed to ISO 26262, and no supplier safety evidence is available.
- All hardware-in-the-loop, on-road and model-replay verification runs on comma.ai's private Jenkins device farm. **The fork currently has no HIL or on-device verification capability.**
- The driving behaviour comes from end-to-end ML models that comma.ai trained on data that is not available to LionDriver.

## 3. What LionDriver will claim

### 3.1 Reference configuration (the only scope claims apply to)

| Element | Reference configuration |
|---|---|
| Vehicle | 2020 Toyota Corolla LE, US market, ICE (non-hybrid), TSS 2.0. Platform `TOYOTA_COROLLA_TSS2`. VIN, firmware versions and options recorded in the [item definition](../02-concept/WP-C-01-item-definition.md) |
| Device | One identified comma device hardware revision (recorded in WP-C-01) with the Toyota harness |
| Software | A tagged LionDriver release that pins openpilot, opendbc, panda, msgq, rednose, tinygrad and the model weights by commit hash |
| Function | Supervised SAE Level 2: lane centring (lateral) plus openpilot longitudinal control (ACC with stop-and-go). On TSS2 without radar ACC, the Corolla runs openpilot longitudinal by default (`opendbc_repo/opendbc/car/toyota/interface.py:105`) |
| ODD | Defined in [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md) |
| User | A licensed, attentive driver who has been briefed according to [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md). During the development phase: trained safety drivers only ([WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md)) |

Any other vehicle, device, software baseline or ODD extension needs an impact analysis ([WP-M-12](WP-M-12-impact-analysis.md)) and supporting evidence before it joins the claimed scope.

### 3.2 Top-level claim

> **G0**: The LionDriver reference configuration, operated by an attentive driver within its ODD, does not pose unreasonable risk to vehicle occupants or other road users. The residual risk is no worse than manual driving of the same vehicle with its stock TSS 2.0 driver assistance.

It is supported by five sub-claims, which structure the [safety case (WP-K-01)](../10-safety-case/WP-K-01-safety-case.md):

| Sub-claim | Standard | Core argument |
|---|---|---|
| G1 Functional safety: hazards from E/E malfunctions are reduced to tolerable levels | ISO 26262 | The safety envelope (§4) enforces the safety goals regardless of what the QM driving stack commands |
| G2 SOTIF: hazards from functional insufficiencies and foreseeable misuse are acceptably low | ISO 21448 | Insufficiencies of the ML driving stack are bounded by the envelope and the driver's controllability. Driver supervision is enforced by driver monitoring. Residual risk is shown against validation targets |
| G3 AI: ML components are adequately specified, developed, validated and monitored | ISO/PAS 8800 | The models are QM components inside a safety-monitored architecture. Their contribution is handled as SOTIF insufficiency, with model lifecycle and dataset controls |
| G4 Cybersecurity: cybersecurity risks to safety and privacy are treated | ISO/SAE 21434 | TARA-driven goals cover the update path, remote access, CAN injection and panda firmware authenticity |
| G5 Process: the work was done by competent people, under controlled processes, with independent confirmation | ISO 26262-2/8, ASPICE | Plans, CM, change control, reviews and the confirmation measures defined here |

**No claim is made, now or as a target, for driverless operation, Level 3 or higher, or for configurations outside §3.1.**

## 4. Safety architecture argument (the central strategy)

### 4.1 The safety envelope pattern

openpilot already has an architecture that makes a credible ISO 26262 argument possible without re-developing the whole stack to ASIL:

```
 ┌─────────────── comma device ───────────────────────────────────────┐
 │  Application SoC (Linux/AGNOS)          Safety MCU (STM32H7 "panda")│
 │  ┌──────────────────────────────┐       ┌────────────────────────┐  │
 │  │ camerad → modeld (ML) →      │  SPI  │ opendbc safety         │  │
 │  │ plannerd → controlsd →       │──────▶│  Toyota mode:          │──┼──▶ vehicle CAN
 │  │ card → pandad                │       │  RX checks, TX filter, │  │   (EPS, ECM, brake)
 │  │ dmonitoringmodeld →          │◀──────│  torque/accel limits,  │◀─┼── vehicle CAN
 │  │ dmonitoringd → selfdrived    │       │  engagement gating,    │  │
 │  └──────────────────────────────┘       │  heartbeat timeout     │  │
 │        QM (FuSa) / SOTIF-managed        └────────────────────────┘  │
 │                                          ASIL-allocated (target)    │
 └─────────────────────────────────────────────────────────────────────┘
          Driver: supervises, overrides (brake, steering, cancel)
          Vehicle: EPS torque limiting & fault detection (AoU), brakes, PCS (AoU)
```

- **Safety element:** the opendbc safety mode running on the panda MCU. It is the only path to the actuators, and it enforces:
  - actuation limits (steering torque magnitude and rate, measured-torque tracking, acceleration bounds),
  - engagement gating (no actuation unless engaged; immediate release on driver brake, gas or cancel, depending on configuration),
  - message whitelisting, and plausibility checks on received messages (checksum, counter, timeout),
  - a heartbeat timeout that removes actuation when the SoC stops communicating.

  The detailed mechanisms and limits are in the [gap assessment §3](../00-assessment/gap-assessment.md#3-safety-enforcement-layer-panda--opendbc-safety).
- **QM stack:** everything on the application SoC, including the ML models, planner, controllers, `selfdrived` state machine and UI. ISO 26262 treats it as QM, provided freedom from interference with the safety element is shown ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md)). Its performance limitations are managed under ISO 21448 and ISO/PAS 8800.
- **Driver:** the controllability arguments in the HARA rely on a supervising driver. Envelope limits are chosen so that any command within the limits stays controllable by a normal driver (ISO 11270 / ISO 15622 basis, as `docs/SAFETY.md` states). This is the main SOTIF and FuSa interface and must be argued explicitly, not assumed.
- **Vehicle (existing elements):** the Toyota EPS, ECM, brake actuator, and the stock radar and camera. They are outside the item but carry assumptions, for example that the EPS limits LKA torque and faults safely, and that pre-collision braking (PCS) stays available. These are recorded as Assumptions of Use (AoU) in [WP-C-01](../02-concept/WP-C-01-item-definition.md) and have to be verified by vehicle testing, since Toyota provides no evidence.

### 4.2 Consequences that shape the plan

1. **ASIL work concentrates on a small codebase:** `opendbc/safety/*.h`, `opendbc/safety/modes/toyota.h`, and the panda firmware paths they rely on (CAN drivers, SPI comms, heartbeat, relay, main loop, fault handling). This is a few thousand lines of MISRA-checked C, which is a realistic size for full ISO 26262-6 treatment.
2. **Freedom from interference is the hinge.** The argument holds only if a fault or insufficiency on the SoC cannot defeat the envelope. That covers: SPI corruption, a babbling SoC, a wrong safety mode or parameter sent by the SoC at start-up, panda firmware replaced by the SoC, and shared power, clock or thermal failures. Each one needs an analysis and a mechanism ([WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md), [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md)). The **safety mode and safety parameter are selected by the SoC** (`openpilot/selfdrive/pandad/panda_safety.cc`), so a QM element configures the safety element. This is a known weakness that must be closed, for example by locking the mode in panda firmware for the reference configuration or adding an independent cross-check.
3. **Single-channel hardware.** The panda MCU is single-channel, and it shares the device PCB, power and enclosure with the SoC. Whether this meets the ASIL from the HARA depends on the hardware metrics (WP-H-04/05) and the DFA. If the HARA gives ASIL C or D for a safety goal, the likely route is ASIL decomposition onto the envelope plus vehicle-side measures (EPS limiting, driver), or plausibility checks by the EPS. That route depends on AoUs about OEM ECUs that cannot be proven without vehicle testing.
4. **Driver monitoring is safety-relevant.** If controllability ratings assume an attentive driver, then the mechanism that enforces attention (DM model, `monitoring/policy.py` timers, disengagement on unresponsiveness) is a safety measure. Under ISO 21448 it is treated as a measure against foreseeable misuse. Whether its failure is also an ISO 26262 safety goal violation is decided in the HARA ([WP-C-03](../02-concept/WP-C-03-hara.md)).
5. **Hardware evidence comes from qualification, not development.** The device is COTS. The route is hardware component qualification (ISO 26262-8 §13) together with the hardware metrics and FMEDA that LionDriver performs itself, using schematic information as far as it is available. If the evidence cannot be obtained, the gap is recorded and the residual risk is argued, never assumed away.

## 5. Tailoring

ISO 26262 assumes an OEM or supplier developing a series-production item. LionDriver is an open-source aftermarket retrofit, built from inherited software, on commercial hardware, attached to a vehicle whose internal safety concepts are unknown. The table records each tailoring decision. Each one needs confirmation review by an independent assessor (ISO 26262-2 §6 Table 1).

| # | Topic | Decision | Rationale |
|---|---|---|---|
| T-01 | Lifecycle entry | Treat LionDriver as a **modification of an existing item** (openpilot). Do an impact analysis ([WP-M-12](WP-M-12-impact-analysis.md)) and then a full concept phase. Inherited work products are not reused because none exist | ISO 26262-2 §6 allows tailoring by impact analysis. With no inherited work products, the concept phase has to be done from scratch |
| T-02 | Item boundary | The item is the comma device + harness + LionDriver software as installed. Vehicle ECUs are existing elements outside the item, with AoUs | LionDriver cannot change or obtain evidence for OEM ECUs |
| T-03 | Element development approach | The envelope (opendbc safety + the panda firmware paths it relies on) is **re-verified to the ASIL from the HARA**. Requirements, architecture and unit design are back-filled from the existing code ("reverse engineering to requirements"), followed by full verification. The QM SoC stack is handled as QM plus SOTIF | Concentrates ASIL effort where the argument needs it (§4.2.1) |
| T-04 | Hardware | Device and MCU treated as COTS hardware components qualified per ISO 26262-8 §13. HW metrics computed by LionDriver | No supplier ISO 26262 evidence |
| T-05 | Third-party and upstream software | QM components (Linux/AGNOS, msgq, capnp, tinygrad runtime, rednose) qualified per 8 §12 at QM, or argued as non-interfering. Any upstream code in the ASIL path is re-verified under T-03 | 8 §12 is suitable for QM reuse. ASIL code needs development evidence |
| T-06 | Proven in use | **Not claimed** for any element. The openpilot fleet history is evaluated in [WP-P-09](../07-supporting/WP-P-09-proven-in-use.md) as supporting evidence only | No controlled configuration history, field-problem data or service period data that meets 8 §14 |
| T-07 | Production (Part 7) | Tailored to installation, provisioning and configuration control of the retrofit ([WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md)). LionDriver does not manufacture hardware | Production is comma's. LionDriver controls installation, firmware load and configuration |
| T-08 | Distributed development | comma.ai is treated as an upstream supplier. No development interface agreement (DIA) is possible, so the "supplier" activities fall to LionDriver ([WP-M-11](WP-M-11-upstream-and-supplier-management.md)) | Upstream is under no contract |
| T-09 | Independence | Verification reviews may be done by project members (I0/I1), but never by the author of the work product. While the project has a single maintainer, I1 review needs an external reviewer, and self-review is recorded as I0 and does not count as verification. Confirmation reviews of the HARA, safety plan and safety case, and the functional safety assessment, need an **external** assessor (I2/I3, depending on ASIL) | The project currently has one maintainer, so I2/I3 cannot be met internally |
| T-10 | SOTIF scope | All of ISO 21448 applies. Of the standard's two areas, area 3 ("unknown unsafe") is the dominant one for an ML-driven function, so validation targets are a primary deliverable | End-to-end ML driving |
| T-11 | Cybersecurity scope | ISO/SAE 21434 applies to the item and its update and remote-access ecosystem. comma's back end (connect, athena server) is outside LionDriver's control, so it is treated as an external entity with cybersecurity assumptions | No control over comma servers |
| T-12 | ASPICE target | Target **CL2** for SYS.1–5, SWE.1–6, SUP.1, SUP.8–10, MAN.3 and MAN.5, and **CL1** for MLE.1–4 and HWE.1–4 (supplier-limited). Assessed by self-assessment first ([WP-M-13](WP-M-13-aspice-capability-baseline.md)) | Realistic for a small open project. HWE is supplier-limited |
| T-13 | Regulatory | US market. FMVSS self-certification does not cover aftermarket ADAS function. NHTSA Standing General Order crash reporting is used as the model for field monitoring ([WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md)). UNECE R79/R171 are informative benchmarks for HMI and DM requirements | No type approval applies to the aftermarket retrofit in the US |

## 6. How the standards fit together

| Topic | Primary | Interfaces |
|---|---|---|
| Hazards from malfunctions | ISO 26262-3 HARA | Shares the hazard list and situation catalogue with the SOTIF hazard identification, so there is one hazard log |
| Hazards from insufficiencies and misuse | ISO 21448 §6–7 | Uses the same hazardous events. Severity and controllability reuse the HARA ratings |
| ML models | ISO/PAS 8800, ASPICE MLE | Model errors feed in as SOTIF functional insufficiencies (WP-C-06). Data and model lifecycle in WP-W-10 |
| Cyber attacks that cause safety hazards | ISO/SAE 21434 TARA | TARA damage scenarios link to HARA hazards. CS goals that protect safety goals are traced both ways |
| Process capability | ASPICE | The ISO 26262 work products double as ASPICE information items. Each register entry carries its ASPICE process ID |

One shared **hazard log** (in [WP-C-03](../02-concept/WP-C-03-hara.md), with SOTIF and TARA cross-references) and one **requirements database** ([`trace/`](../trace/README.md)) hold all of this together.

## 7. Phases, gates and sequence

| Phase | Gate | Key work products | Prerequisites and notes |
|---|---|---|---|
| **P0 Governance** | G0 | M-00…M-13, P-01…P-06 | Fork opendbc and panda into LionDriver control (D-01). Freeze upstream sync (D-02). Fix CI for the fork (D-03). CODEOWNERS and branch protection |
| **P1 Concept** | G1 | C-01…C-11, V-07, K-01 (initial argument) | No public-road testing until WP-V-07 is approved. HARA confirmation review by an external assessor |
| **P2 System design** | G2 | S-01…S-07, A-01…A-04, V-02 | Envelope requirements back-filled from code. FFI and DFA analyses decide whether hardware changes are needed |
| **P3 HW/SW development** | G3 | H-01…H-05, H-07, W-01…W-06, W-09…W-11, P-07…P-09 | Includes closing gaps found in P2, for example locking the safety mode and parameter |
| **P4 Integration and verification** | G4 | S-08, S-09, H-06, W-07, W-08, V-03, V-05 | **Needs a LionDriver HIL bench** (panda + CAN simulation + Corolla DBC replay) and a fork-owned process-replay reference set |
| **P5 Validation and release** | G5 | V-01, V-04, V-06, K-02…K-06, O-01…O-03 | Validation driving under WP-V-07; SOTIF residual-risk acceptance; external FSA |
| **P6 Operation** | G6 | O-04, O-05, P-03 | Field monitoring, incident response, controlled updates |

Mapping to the README roadmap:

| README roadmap item | Phase |
|---|---|
| Governance and FSM plan | P0 |
| Reference vehicle and item boundary; HARA and safety goals; FSC; SOTIF and cybersecurity analyses | P1 |
| Technical safety architecture; assess existing software and hardware | P2 |
| Safety mechanisms and supporting hardware | P3 |
| Traceability and verification | P3–P4 |
| Living safety case | P1–P5 |
| Independent reviews | Every gate |

## 8. Strategic decisions required

These are owned by the project maintainer. Until each one is decided, it stays open in [WP-M-07](WP-M-07-risk-management.md).

| ID | Decision | Recommendation |
|---|---|---|
| D-01 | Take configuration control of the safety code | Fork `commaai/opendbc` and `commaai/panda` (and mirror `msgq`, `rednose`, `teleoprtc`, which also resolve to `commaai/*` through relative URLs) into the LionDriver GitHub account. Point `.gitmodules` at them with absolute URLs. Pin tinygrad by commit, not `branch = master`. **Status:** done — panda, opendbc, msgq, rednose and teleoprtc forked to `jherrodthomas/*` and repointed at unchanged commits; tinygrad tracked by commit only |
| D-02 | Upstream synchronization policy | Freeze on the current baseline. Pull upstream only in deliberate "sync" change requests, each with an impact analysis against the safety-relevant file list ([WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)). **Status:** in progress. The procedure is defined ([WP-M-11 §5](WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02), [WP-P-02 §9](../07-supporting/WP-P-02-change-management.md#9-upstream-synchronization-ct-3-d-02)). `tools/sync/sync_report.py` and the [`impact/`](../07-supporting/impact/README.md) record folder are in place. The first drift survey (2026-10-10) found openpilot 2 and msgq 9 commits ahead of the pins, with no sync decided |
| D-03 | CI for the fork | Disable or replace workflows that depend on comma infrastructure (`jenkins-pr-trigger`, `ui_preview`, `release`, `repo-maintenance`, `stale` auto-close). Generate fork-owned process-replay references. Enable opendbc safety tests, MISRA and mutation tests in fork CI |
| D-04 | HIL capability | Build a minimal HIL bench (a comma device or a bare panda + CAN interface + replay of Corolla logs) to replace comma's device farm for envelope verification |
| D-05 | Model update policy | Pin model weights per release. Treat any model change as a SOTIF-relevant change that re-runs the scenario evaluations (WP-V-03) |
| D-06 | External assessor | Engage an independent functional safety assessor for the HARA confirmation review at G1 |
| D-07 | Work product format | Markdown in the repository (docs-as-code), with machine-readable requirements in `trace/`. Reviewed through pull requests. Can be exported to an ALM tool later |
| D-08 | Default enablement of Experimental Mode | Upstream commit `f21bfc3` turns on Experimental Mode by default without confirmation. For the reference configuration, decide whether this is in the ODD; recommendation: disabled until validated |

## 9. Top risks to the assurance path

| Risk | Effect | Mitigation |
|---|---|---|
| No supplier evidence for the comma hardware | HW metrics and qualification cannot be completed. The ASIL claim on the envelope is limited | Derive the FMEDA from the published panda design and the STM32H7 safety manual. Argue conservatively. Consider an external, independent monitor if the metrics fall short |
| OEM ECU behaviour is unverifiable | AoUs on the EPS and PCS stay assumptions | Characterize them by vehicle testing (torque limits, fault reactions). Restrict claims to what was measured |
| Upstream velocity | The safety case goes stale with every sync | D-02 freeze plus a sync impact-analysis procedure |
| ML insufficiencies are not quantifiable without data | SOTIF area 3 residual risk cannot be shown | Set validation targets. Use fork-owned drive logs, scenario simulation and field monitoring. Bound the ODD tightly |
| Single maintainer | Independence and competence requirements are not met | External reviewers and assessor. Document competence ([WP-M-04](WP-M-04-organization-competence-safety-culture.md)) |
| Public-road testing before the analyses are done | Harm to third parties | No LionDriver public-road operation beyond upstream behaviour until G1 and WP-V-07 are complete |
