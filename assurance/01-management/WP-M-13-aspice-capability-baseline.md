# WP-M-13 ASPICE Capability Baseline (Self-Assessment)

| Field | Value |
|---|---|
| Work product | WP-M-13 ASPICE capability baseline (self-assessment) |
| Standard reference | Automotive SPICE PAM 4.0: process capability levels 1–2 (PA 1.1, PA 2.1, PA 2.2); processes per WP-M-01 T-12 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Process (all) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1). Not reviewed by a certified assessor |
| Approver | Project maintainer |
| Baseline | `8b8c6ae` |

## 1. Purpose

This is the process capability baseline for LionDriver at `8b8c6ae`. It refines the estimate in the [gap assessment §7](../00-assessment/gap-assessment.md#7-aspice-capability-baseline-estimated), sets the gap to the targets in tailoring decision **T-12** ([WP-M-01 §5](WP-M-01-assurance-strategy.md#5-tailoring)), and maps improvement actions to work products. It is re-run at each gate.

## 2. Method

| Aspect | Approach |
|---|---|
| Type | **Self-assessment**, not a formal ASPICE assessment. No certified assessor, no assessment sponsor agreement, no interviews. Ratings are indicative and cannot be quoted as an ASPICE result |
| Evidence | Repository content at `8b8c6ae` (code, tests, CI workflows, docs, git history) and the process review notes. The draft work products under `assurance/` are **not** counted: they are untracked at the baseline and describe intended practice, not performed practice |
| Organizational unit | The LionDriver fork. Practices performed only by comma.ai upstream (e.g. Jenkins device tests) are noted but rated as not performed by the fork, because the fork cannot execute or retain them (GAP-30) |
| Rating scale | N (0–15 %), P (>15–50 %), L (>50–85 %), F (>85–100 %) achievement of the process attribute |
| Capability level rule | CL1 needs PA 1.1 rated L or F. CL2 additionally needs PA 1.1 = F and PA 2.1, PA 2.2 rated L or F |
| Base practices | Described in words; base-practice numbers are not cited (check against the licensed PAM 4.0 before an audit) |

## 3. Scope

| Group | Processes | Target (T-12) |
|---|---|---|
| A | SYS.1, SYS.2, SYS.3, SYS.4, SYS.5, SWE.1–SWE.6, SUP.1, SUP.8, SUP.9, SUP.10, MAN.3, MAN.5 | **CL2** |
| B | MLE.1–MLE.4, HWE.1–HWE.4 | **CL1** (supplier-limited) |
| C (informative) | SEC.1–SEC.4, SUP.11 | No target set yet (OI-2) |

Where a process applies to two very different parts of the code, the rating states both: "safety code" = `opendbc_repo/opendbc/safety` (+ panda firmware where stated); "rest" = the openpilot application stack.

## 4. Capability level 1 ratings (PA 1.1)

### 4.1 System engineering

| Process | PA 1.1 | Evidence of performed practice | Main weaknesses | CL |
|---|---|---|---|---|
| SYS.1 Requirements elicitation | N | Mission statement in `README.md`; upstream prose (`docs/SAFETY.md`, `docs/LIMITATIONS.md`) | No stakeholder identification, no agreed stakeholder requirements, no change handling | 0 |
| SYS.2 System requirements analysis | N | Two informal top-level safety requirements (`docs/SAFETY.md:24-28`) | No system requirements specification, no structuring, no analysis, no traceability to stakeholder needs | 0 |
| SYS.3 System architectural design | P | Implicit architecture in code: process list (`openpilot/system/manager/process_config.py`), interfaces as capnp schemas (`openpilot/cereal/log.capnp`) | `docs/contributing/architecture.md` is empty; no static/dynamic architecture description, no evaluation of alternatives, no allocation of requirements | 0 |
| SYS.4 System integration and integration verification | P | Upstream device-level tests exist (`openpilot/selfdrive/test/test_onroad.py`, pandad/SPI stages in `Jenkinsfile`) | Run only on comma's Jenkins device pools; fork cannot execute them; no integration strategy or specification; results not retained | 0 |
| SYS.5 System verification | P | Longitudinal maneuver tests on a plant model (`openpilot/selfdrive/test/longitudinal_maneuvers/test_longitudinal.py`); release checklist practice implied by `RELEASES.md` | No verification measures derived from system requirements (none exist); no results records; simulator job disabled (`.github/workflows/tests.yaml:185`) | 0 |

### 4.2 Software engineering

| Process | PA 1.1 | Evidence of performed practice | Main weaknesses | CL |
|---|---|---|---|---|
| SWE.1 Software requirements analysis | N | Requirements are implicit in constants and test assertions (e.g. `opendbc_repo/opendbc/safety/modes/toyota.h:173-210`) | No requirements, IDs or traceability (GAP-14) | 0 |
| SWE.2 Software architectural design | N | Module structure visible in code only | No architecture description, no interface/dynamic behaviour description, no resource or timing budgets (GAP-23) | 0 |
| SWE.3 Software detailed design and unit construction | L (safety code) / P (rest) | Units constructed under MISRA C:2012 checking (`opendbc_repo/opendbc/safety/tests/misra/test_misra.sh`), compiler warnings as errors (`SConstruct`), lint rules (`pyproject.toml`) | No detailed design documentation; dynamic behaviour only in code; no design-to-requirement consistency; 6 global MISRA suppressions plus undocumented inline deviations (`tests/misra/suppressions.txt`; GAP-13) | 1 (safety code) / 0 |
| SWE.4 Software unit verification | L (safety code) / P (rest) | Safety code: 100 % line coverage gate (`opendbc_repo/opendbc/safety/tests/test.sh:36-43`), mutation testing (`tests/mutation.py`, CI job), UBSan, MISRA static analysis, per-brand tests (`tests/test_toyota.py`). Rest: unit tests across controls, locationd, selfdrived, monitoring | No unit verification strategy or specification separate from code; criteria are line coverage only (no branch/MC/DC); tests run on x86 host builds, not the target; results not retained; openpilot Python/C++ has no coverage threshold (GAP-36) | 1 (safety code) / 0 |
| SWE.5 Software component verification and integration verification | L | Process replay of controlsd, plannerd, radard, dmonitoringd, locationd and others against reference logs (`openpilot/selfdrive/test/process_replay/test_processes.py`), runnable on GitHub-hosted runners; fuzzy tests (`test_fuzzy.py`) | Reference logs are comma-hosted (`test_processes.py:70`); replay job is `continue-on-error` on master (`.github/workflows/tests.yaml:128`); no integration strategy; model replay only on comma Jenkins (`Jenkinsfile:297-299`) | 1 |
| SWE.6 Software verification | P | `test_onroad.py` checks timing, resource use and service frequencies on device | Runs only on comma devices; not against software requirements; no results in the fork | 0 |

### 4.3 Machine learning engineering (group B)

| Process | PA 1.1 | Evidence | Main weaknesses | CL |
|---|---|---|---|---|
| MLE.1 ML requirements analysis | N | None | No ML requirements; no ODD/input-space definition | 0 |
| MLE.2 ML architecture | N | Model I/O visible in `openpilot/selfdrive/modeld/parse_model_outputs.py`, `modeld.py` | No ML architecture description; hyperparameters and design rationale unknown | 0 |
| MLE.3 ML training | N | Training performed by comma.ai, not visible | Not performed by the fork; no provenance beyond LFS hashes ([WP-M-10 §5](WP-M-10-ai-safety-plan.md#5-the-acquired-pre-trained-model-route)) | 0 |
| MLE.4 ML model testing | P | Model replay compares outputs against reference (`process_replay/model_replay.py`) | Regression comparison only; not against ML requirements; no independent test data; runs only on comma Jenkins | 0 |

### 4.4 Hardware engineering (group B)

| Process | PA 1.1 | Evidence | Main weaknesses | CL |
|---|---|---|---|---|
| HWE.1 HW requirements analysis | N | None | COTS device; no HW requirements | 0 |
| HWE.2 HW design | N | Board configuration headers only (`panda/board/boards/*.h`) | No design documentation available to the fork | 0 |
| HWE.3 Verification against HW design | N | None | — | 0 |
| HWE.4 Verification against HW requirements | P | panda HITL test suite (`panda/tests/hitl/`: health, SPI, CAN loopback, harness) | Needs comma hardware and jungles; no HW requirements to verify against; no results in fork | 0 |

### 4.5 Support and management

| Process | PA 1.1 | Evidence | Main weaknesses | CL |
|---|---|---|---|---|
| SUP.1 Quality assurance | N | CI gates in `.github/workflows/tests.yaml`; `tools/release/check-dirty.sh` | No QA strategy, no independent QA function, no non-conformance handling | 0 |
| SUP.8 Configuration management | L | git; submodules pinned by SHA; hash-pinned `uv.lock`; `tools/release/check-submodules.sh`; LFS for models; release scripts | No CM plan or baselines/tags in the fork; submodule URLs resolve to upstream (GAP-29); tinygrad tracks `master`; mutable cppcheck branch; version still `0.11.2` (GAP-35) | 1 |
| SUP.9 Problem resolution management | N | Issue templates exist but route to comma (`.github/ISSUE_TEMPLATE/*`) | No fork problem recording, analysis or tracking; `stale.yaml` auto-closes items | 0 |
| SUP.10 Change request management | P | Pull-request flow; labeler (`auto_pr_review.yaml`) | No change request records with impact analysis; no CODEOWNERS or PR template (GAP-32); stale auto-close (GAP-31) | 0 |
| MAN.3 Project management | N | README roadmap | No scope definition, estimates, schedule or monitoring at the baseline | 0 |
| MAN.5 Risk management | N | None | No risk identification or tracking at the baseline | 0 |

### 4.6 Informative processes (group C)

| Process | PA 1.1 | Note |
|---|---|---|
| SEC.1 Cybersecurity requirement elicitation | N | No TARA, goals or requirements |
| SEC.2 Cybersecurity implementation | P | Some controls exist (panda firmware signature check, TLS transport) but are not derived from requirements and have known weaknesses (GAP-24…GAP-26) |
| SEC.3 Risk treatment verification | N | None |
| SEC.4 Risk treatment validation | N | No penetration testing |
| SUP.11 ML data management | N | No datasets under fork control |

## 5. Capability level 2 (PA 2.1, PA 2.2)

**All processes in scope are rated N for PA 2.1 and PA 2.2.**

| Attribute | Rating | Reason (applies to every process) |
|---|---|---|
| PA 2.1 Performance management | N | No process objectives, plans, schedules, responsibilities or resources are defined for any process at the baseline; performance is not monitored or adjusted; interfaces between parties are not managed. The fork has one maintainer and no recorded planning |
| PA 2.2 Work product management | N | No requirements for work products (content, structure, quality criteria) exist; work products are not identified, reviewed against criteria or controlled as such; review evidence beyond labelling is absent (GAP-32) |

Even the processes with CL1 (SWE.3/SWE.4 safety code, SWE.5, SUP.8) do not reach CL2: PA 1.1 is L, not F, and PA 2.x is N.

## 6. Summary and gap to target

| Process | Current CL | Target CL | Gap | Key gap drivers |
|---|---|---|---|---|
| SYS.1 | 0 | 2 | 2 | Stakeholder requirements, change handling |
| SYS.2 | 0 | 2 | 2 | System requirements, traceability |
| SYS.3 | 0 | 2 | 2 | Architecture description and allocation |
| SYS.4 | 0 | 2 | 2 | Fork-owned integration environment (HIL, D-04) |
| SYS.5 | 0 | 2 | 2 | Requirement-based system verification |
| SWE.1 | 0 | 2 | 2 | Software requirements with IDs |
| SWE.2 | 0 | 2 | 2 | Architecture, timing budgets |
| SWE.3 | 1 / 0 | 2 | 1–2 | Detailed design, MISRA deviation records |
| SWE.4 | 1 / 0 | 2 | 1–2 | Verification specification, branch/MC/DC, results retention |
| SWE.5 | 1 | 2 | 1 | Fork-owned references, strategy, results |
| SWE.6 | 0 | 2 | 2 | On-device verification in the fork |
| SUP.1 | 0 | 2 | 2 | QA plan and independent QA |
| SUP.8 | 1 | 2 | 1 | CM plan, fork control of submodules, baselines |
| SUP.9 | 0 | 2 | 2 | Fork problem resolution |
| SUP.10 | 0 | 2 | 2 | Change requests with impact analysis, review gates |
| MAN.3 | 0 | 2 | 2 | Project plan and monitoring |
| MAN.5 | 0 | 2 | 2 | Risk management |
| MLE.1–MLE.4 | 0 | 1 | 1 | Acquired-model route ([WP-M-10](WP-M-10-ai-safety-plan.md)); MLE.3 can only be met by substitute evidence |
| HWE.1–HWE.4 | 0 | 1 | 1 | COTS hardware; requirements and verification by LionDriver |

## 7. Improvement actions

| # | Action | Processes | Work products |
|---|---|---|---|
| IA-1 | Write and approve plans; assign roles; start monitoring against the plan | MAN.3, MAN.5, all PA 2.1 | [WP-M-02](WP-M-02-safety-plan.md), [WP-M-03](WP-M-03-project-plan.md), [WP-M-07](WP-M-07-risk-management.md) |
| IA-2 | Define work-product requirements and review criteria; review through pull requests with records | All PA 2.2, SUP.1 | [WP-M-05](WP-M-05-quality-assurance-plan.md), [WP-P-04](../07-supporting/WP-P-04-documentation-management.md), [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) |
| IA-3 | Take configuration control of submodules, pin tinygrad and cppcheck, tag baselines, LionDriver versioning | SUP.8 | [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md), [WP-M-11](WP-M-11-upstream-and-supplier-management.md), [WP-P-10](../07-supporting/WP-P-10-release-management.md) |
| IA-4 | CODEOWNERS, PR template with impact checklist, branch protection, remove stale auto-close; impact analysis per change | SUP.10 | [WP-P-02](../07-supporting/WP-P-02-change-management.md), [WP-M-12](WP-M-12-impact-analysis.md) |
| IA-5 | Fork issue tracking and vulnerability intake | SUP.9 | [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md), [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |
| IA-6 | Stakeholder, system and software requirements with IDs and traceability | SYS.1, SYS.2, SWE.1 | [WP-C-01](../02-concept/WP-C-01-item-definition.md), [WP-S-01](../03-system/WP-S-01-system-requirements.md), [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md), [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md), [WP-T-01](../trace/README.md) |
| IA-7 | System and software architecture descriptions, including timing budgets | SYS.3, SWE.2 | [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md), [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md), [WP-W-03](../05-software/WP-W-03-software-architecture.md) |
| IA-8 | Detailed design for the safety code; MISRA deviation records | SWE.3 | [WP-W-05](../05-software/WP-W-05-software-unit-design.md), [WP-W-01](../05-software/WP-W-01-software-development-environment-guidelines.md) |
| IA-9 | Unit verification specification, branch/MC/DC coverage, retained results, target-based testing | SWE.4 | [WP-W-06](../05-software/WP-W-06-software-unit-verification.md) |
| IA-10 | Fork-owned process-replay references; integration strategy; enable replay as a blocking gate | SWE.5 | [WP-W-07](../05-software/WP-W-07-software-integration-verification.md) |
| IA-11 | LionDriver HIL bench and on-device verification | SYS.4, SWE.6, HWE.4 | [WP-S-08](../03-system/WP-S-08-system-integration-test.md), [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md), [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) |
| IA-12 | Requirement-based system verification | SYS.5 | [WP-S-09](../03-system/WP-S-09-system-verification.md) |
| IA-13 | ML requirements, architecture-as-received, provenance, requirement-based model testing, evaluation data control | MLE.1–4, SUP.11 | [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md), [WP-W-10](../05-software/WP-W-10-ml-engineering.md) |
| IA-14 | HW requirements and qualification of the COTS device | HWE.1–4 | [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md), [WP-H-02](../04-hardware/WP-H-02-hardware-design.md), [WP-H-07](../04-hardware/WP-H-07-hardware-component-qualification.md) |
| IA-15 | TARA-driven cybersecurity requirements, implementation, verification and validation | SEC.1–4 | [WP-C-09](../02-concept/WP-C-09-tara.md), [WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md), [WP-W-11](../05-software/WP-W-11-cybersecurity-implementation-verification.md), [WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md) |

## 8. Re-assessment

The self-assessment is repeated at each gate (G0…G5) and its result recorded as a new version of this document. Before any capability claim is made externally, a formal assessment by a certified assessor is required (OI-1).

## Open items

| ID | Item |
|---|---|
| OI-1 | Decide whether and when to commission a formal ASPICE assessment, and by whom |
| OI-2 | Set targets for the informative processes SEC.1–SEC.4 and SUP.11 (and decide whether VAL.1, ACQ.4 and MAN.7 join the scope) |
| OI-3 | Verify process names and base-practice content against the licensed PAM 4.0 |
| OI-4 | Agree how upstream-only practices (comma Jenkins tests) are treated once the fork has its own equivalents |
| OI-5 | MLE.3 cannot be performed by LionDriver; agree with the assessor whether the CL1 target for MLE.3 is achievable with substitute evidence or must be tailored |
