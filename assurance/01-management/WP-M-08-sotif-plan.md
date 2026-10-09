# WP-M-08 SOTIF Plan

| Field | Value |
|---|---|
| Work product | WP-M-08 SOTIF plan |
| Standard reference | ISO 21448:2022 §4 (management of SOTIF activities), §5–§13; ISO/PAS 8800:2024 (interface for AI-related insufficiencies); ASPICE 4.0 MAN.3 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); SOTIF acceptance criteria and validation targets also reviewed by the external assessor (D-06) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This plan says how LionDriver carries out the ISO 21448 activities for the reference configuration defined in [WP-M-01 §3.1](WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to): supervised Level 2 lane centring plus openpilot longitudinal control on a 2020 Toyota Corolla LE (TSS2, US, ICE), comma device and panda safety MCU.

It implements sub-claim **G2** of the [assurance strategy](WP-M-01-assurance-strategy.md#32-top-level-claim) and tailoring decision **T-10** (all of ISO 21448 applies; the "unknown unsafe" area dominates for an ML-driven function). It does not repeat the strategy; it assigns activities, owners, gates and work products.

Out of scope: hazards caused by E/E malfunctions (handled by the [functional safety plan, WP-M-02](WP-M-02-safety-plan.md)) and attacks (handled by the [cybersecurity plan, WP-M-09](WP-M-09-cybersecurity-plan.md)). Both share the hazard log described in §6.

## 2. Why SOTIF is a primary concern for LionDriver

The inherited stack has no SOTIF work products. The [gap assessment](../00-assessment/gap-assessment.md) records:

| Finding | SOTIF relevance |
|---|---|
| End-to-end ML driving (`openpilot/selfdrive/modeld/modeld.py`), trained by comma.ai on data LionDriver cannot see | Functional insufficiencies cannot be bounded from the training side; only black-box evaluation and architecture can bound them ([WP-M-10](WP-M-10-ai-safety-plan.md)) |
| GAP-18: Experimental Mode on by default (`openpilot/common/params_keys.h:43`, upstream `f21bfc3`) | Makes model-controlled longitudinal behaviour the default, with no recorded hazard re-assessment. Conflicts with `docs/LIMITATIONS.md:35` |
| GAP-16: 3 s soft disable that keeps actuating on failed inputs (`openpilot/selfdrive/selfdrived/state.py:7`) | Exposure window for degraded inputs |
| GAP-17: diagnostics suppressed around the big-model fallback (`openpilot/selfdrive/selfdrived/selfdrived.py:383-384, 403, 457`) | Insufficiency of the monitoring function |
| GAP-21: driver-monitoring weaknesses (`openpilot/selfdrive/monitoring/policy.py:29, 335`) | Controllability assumptions in HARA and SOTIF depend on an attentive driver |
| GAP-22: no uncertainty or OOD gating of the control action | No runtime detection of triggering conditions |
| No ODD, no validation targets, no scenario catalogue | Nothing to evaluate residual risk against |

## 3. Roles and responsibilities

The project has one maintainer today (WP-M-01 §9). Roles are listed separately so that they can be reassigned as the team grows. Independence requirements come from [WP-M-06](WP-M-06-confirmation-measures-plan.md).

| Role | Holder (today) | Responsibilities in this plan |
|---|---|---|
| SOTIF lead | Jherrod Thomas (maintainer) | Owns this plan, WP-C-05…C-08, WP-V-02…V-04, WP-K-02. Maintains the shared hazard log entries for SH-/TC-/FI- items |
| Safety manager (acting) | Jherrod Thomas | Approves this plan and the acceptance criteria; signs the SOTIF release recommendation input to WP-K-06 |
| AI safety lead | Jherrod Thomas | Supplies model-related insufficiencies and evaluation data ([WP-M-10](WP-M-10-ai-safety-plan.md)) |
| Safety driver(s) | To be appointed under [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) | Execute validation drives, log events, report anomalies |
| HMI / human-factors reviewer | External, TBD | Reviews WP-C-08 (driver interaction, misuse) — the maintainer has no human-factors competence record yet ([WP-M-04](WP-M-04-organization-competence-safety-culture.md)) |
| Independent reviewer / assessor | External, TBD (D-06) | Reviews acceptance criteria, validation targets and the SOTIF release argument |

## 4. SOTIF activities by clause

Gates are defined in [WP-M-00 §2](WP-M-00-work-product-register.md#2-gates). "Status today" describes the baseline `8b8c6ae`, not intent.

| ISO 21448 clause | Activity | Output work products | Gate | Inputs | Status today |
|---|---|---|---|---|---|
| §4 | Plan and manage SOTIF activities; integrate with FuSa and CS plans; define acceptance criteria approach | This plan (WP-M-08) | G0 | WP-M-01 | This draft |
| §5 | Specify the intended functionality, the ODD, system and element functions, known performance limitations, and the driver's role | [WP-C-01](../02-concept/WP-C-01-item-definition.md), [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md), [WP-S-01](../03-system/WP-S-01-system-requirements.md) | G1 | `docs/LIMITATIONS.md`, `docs/SAFETY.md`, `docs/INTEGRATION.md`, code behaviour | Not started. Only upstream prose exists |
| §6 | Identify hazards from insufficiencies and misuse; evaluate severity and controllability (reusing HARA ratings); set acceptance criteria | [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md), [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md); hazard log in [WP-C-03](../02-concept/WP-C-03-hara.md) | G1 | WP-C-02, WP-C-03 | Not started |
| §7 | Identify functional insufficiencies (specification and performance) and triggering conditions, including ML error causes; estimate acceptability of system response | [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) | G1 (initial), refined at G2 and G4 | WP-C-05, WP-A-04, model output description in `openpilot/selfdrive/modeld/parse_model_outputs.py` | Not started |
| §8 | Define functional modifications that reduce SOTIF risk (restrict ODD, change defaults, add monitors, change HMI) | [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md), reflected in [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) | G1 / G2 | WP-C-06; gap actions 3 and 8 | Candidate modifications listed in §8 below |
| §9 | Define the verification and validation strategy, validation targets and their rationale | [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) | G2 | Acceptance criteria (§5 of this plan), WP-C-06 | Not started |
| §10 | Evaluate known hazardous scenarios (verification of the modifications, scenario-based testing) | [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) | G4 | WP-V-02, scenario catalogue | Not started. Upstream maneuver tests exist (`openpilot/selfdrive/test/longitudinal_maneuvers/test_longitudinal.py`) but have no link to hazards |
| §11 | Evaluate unknown hazardous scenarios (exploratory driving, log mining, randomized simulation) | [WP-V-04](../06-validation/WP-V-04-sotif-unknown-scenarios.md) | G5 | WP-V-02, WP-V-07 | Not started |
| §12 | Evaluate SOTIF achievement; recommend release (or release with restrictions, or no release) | [WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md), contributes to [WP-K-01](../10-safety-case/WP-K-01-safety-case.md) and [WP-K-06](../10-safety-case/WP-K-06-release-record.md) | G5 | WP-V-03, WP-V-04, open-issue list | Skeleton only |
| §13 | Operation phase: field monitoring, re-evaluation on new triggering conditions, user information | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md), [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md), [WP-P-03](../07-supporting/WP-P-03-problem-resolution.md) | G6 | Fleet logs (LionDriver-owned only) | Not started |

### 4.1 Sequencing rules

1. No LionDriver-specific behaviour change goes onto public roads before WP-V-07 is approved (WP-M-01 §9).
2. §6 and the HARA (WP-C-03) are done in the same review cycle so that severity and controllability ratings are shared, not duplicated.
3. §9 targets are set before any §10/§11 evidence is collected. Evidence collected before the targets exist may be used only if the target derivation does not depend on it (to avoid fitting targets to data).
4. §7 is revisited after each G2–G4 iteration and after every model change (§9 of this plan).

## 5. Acceptance criteria approach

Acceptance criteria are owned by WP-C-05. Numerical validation targets are owned by WP-V-02. This section fixes only the approach.

### 5.1 Principle

The top-level claim G0 states that residual risk is **no worse than manual driving of the same vehicle with its stock TSS 2.0 driver assistance**. The SOTIF acceptance criterion therefore uses a positive-risk-balance / GAMAB-style comparison against two baselines:

| Baseline | What it represents | Candidate data sources (to be confirmed in WP-V-02) |
|---|---|---|
| B1 Human driver | US human-driven crash and injury rates per distance, filtered to road types and conditions inside the ODD | Public US crash statistics (e.g. NHTSA FARS/CRSS) combined with exposure data. Selection and filtering to be justified |
| B2 Stock TSS2 | The same Corolla driven with Toyota's own lane tracing / lane keeping and dynamic radar cruise control | No public per-feature rate exists. Expected route: comparative scenario testing (same scenarios, stock vs LionDriver) on the reference vehicle rather than a fleet rate |

B1 gives an overall rate target. B2 is a per-scenario comparison and guards against the case where LionDriver meets B1 overall but performs worse than the stock system in specific scenarios (for example, stopped-vehicle approach, cut-ins).

### 5.2 How targets are derived (method only)

For each SOTIF hazardous behaviour SH-nn in WP-C-05:

1. Take the acceptable rate of harm from the baseline (B1), apportioned to the hazard.
2. Divide by the probability that the hazardous behaviour leads to harm, using the controllability and exposure assumptions shared with the HARA. Each such factor needs its own evidence or is set to 1 (conservative).
3. The result is a target rate for the hazardous behaviour, from which a test-distance or test-count target follows with a stated confidence level.
4. Where a target is not achievable by LionDriver-owned driving (expected for most targets, given one vehicle and one maintainer), the target is decomposed into scenario-level targets that can be evaluated by replay and simulation, and the ODD is narrowed (§8). The rationale for each decomposition is recorded in WP-V-02.

Surrogate measures (driver takeovers, disengagements, FCW events, envelope limit hits, DM alerts) may be used as leading indicators. Their relationship to harm must be argued, not assumed.

### 5.3 What LionDriver cannot claim

- No claim can be built on comma.ai's fleet mileage or internal validation: LionDriver has no access to that data and T-06 rules out proven-in-use credit.
- No claim covers configurations outside WP-M-01 §3.1. In particular, Experimental Mode and the Chestnut big-model path are excluded from claims until WP-C-07 decides otherwise (D-08; gap action 8).

## 6. Interface with the HARA and other analyses

| Interface | Rule |
|---|---|
| Shared hazard log | One hazard log lives in [WP-C-03](../02-concept/WP-C-03-hara.md). SOTIF hazardous behaviours (SH-nn), triggering conditions (TC-nn) and functional insufficiencies (FI-nn) are added there and cross-referenced to H-nn / HS-nn. A hazardous event is rated once; SOTIF reuses the severity and controllability ratings |
| Controllability and misuse | WP-C-08 provides the driver-interaction basis for both the HARA controllability ratings and the SOTIF misuse analysis. DM effectiveness (GAP-21) is analysed once and referenced from both |
| Safety envelope | Envelope limits (`opendbc_repo/opendbc/safety/modes/toyota.h:173-210`) bound the consequence of any insufficiency of the QM stack. WP-C-06 records, for each FI, whether the envelope bounds it and whether the bounded behaviour is still controllable (GAP-04 must be closed for this to hold) |
| TARA | Attacks that produce a SOTIF-type hazardous behaviour (e.g. manipulated parameters, GAP-20) are analysed in [WP-C-09](../02-concept/WP-C-09-tara.md) and linked to the same SH-nn |
| AI | ML error causes (data coverage, distribution shift, robustness) enter WP-C-06 as FI-nn via [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) |
| System safety analyses | WP-A-04 (FTA/FMEA) includes insufficiency-driven branches so that the same top events serve FuSa and SOTIF |

## 7. Methods and tools

All tools below need classification under [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) before their results count as evidence.

| Method | Tool / source in the repository | Use in SOTIF | Fork limitation today |
|---|---|---|---|
| Process replay | `openpilot/selfdrive/test/process_replay/test_processes.py`, `process_replay.py`, `compare_logs.py` | Regression oracle: shows that a change does not alter control outputs on recorded routes | Reference logs come from `commaai/ci-artifacts` (`test_processes.py:70`). LionDriver needs fork-owned references including Corolla routes |
| Model replay | `openpilot/selfdrive/test/process_replay/model_replay.py` | Compares model outputs before/after a model or runtime change (§9) | Runs upstream only on comma's Jenkins device pool (`Jenkinsfile:297-299`, `tizi-replay`); test route fetched via `openpilot/tools/lib/openpilotci.py` (`model_replay.py:222-239`). Needs a fork-owned route set and runner |
| Closed-loop simulation | `openpilot/tools/sim/` (MetaDrive bridge, `run_bridge.py`) | Scenario-based testing of known scenarios (§10), randomized exploration for §11 | CI job disabled upstream (`.github/workflows/tests.yaml:185`, `if: false  # FIXME`). Scenario fidelity (camera rendering, vehicle dynamics vs Corolla) must be argued before use as evidence |
| Longitudinal maneuver tests | `openpilot/selfdrive/test/longitudinal_maneuvers/` (plant model) | Planner-level checks for lead/stop scenarios | No traceability to hazards; plant is not a Corolla model |
| Safety replay | `opendbc_repo/opendbc/safety/safety_replay/` | Checks recorded drives against the envelope; detects envelope limit hits in real drives | Needs LionDriver-recorded Corolla logs |
| Drive-log mining | Logs recorded by `openpilot/system/loggerd`; log tools in `openpilot/tools/` (e.g. jotpluggler) | Search for takeovers, near misses, FCW, envelope hits, DM events to discover unknown scenarios (§11) and monitor the field (§13) | LionDriver has no log store; logs today upload to comma's servers. A LionDriver-controlled log pipeline is required ([WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md)) |
| Vehicle testing | Reference Corolla, safety drivers under WP-V-07 | Known-scenario tests on closed course; validation drives within ODD | Requires approved WP-V-07 |
| Analysis methods | Scenario catalogues, STPA-style control-structure analysis, FTA branches for insufficiencies | §6, §7 | Method choice recorded in WP-C-06 |

## 8. Candidate functional modifications (input to WP-C-07)

These are candidates only. WP-C-07 decides each one with rationale.

| # | Candidate | Addresses |
|---|---|---|
| FM-1 | Restore Experimental Mode default to off (or remove the toggle) for the reference configuration | GAP-18, D-08 |
| FM-2 | Exclude the Chestnut big-model path from the reference configuration, or remove the diagnostic suppression around fallback | GAP-17 |
| FM-3 | Shorten or condition the soft-disable actuation window when the failed input is the one being acted on | GAP-16 |
| FM-4 | Add a runtime monitor on model uncertainty / output plausibility that degrades to driver handover | GAP-22 |
| FM-5 | Strengthen DM: do not fully reset awareness on any wheel/gas input; derive DM validity from model uncertainty | GAP-21 |
| FM-6 | Narrow the ODD (e.g. road class, speed range, weather, daylight) to what validation can cover | §5.2 step 4 |
| FM-7 | Add reactions where events have none (`cruiseMismatch`, `speedTooHigh`) and correct the `canError` HMI text | GAP-19 |

## 9. Change-triggered re-evaluation (including model changes)

Decision D-05 makes every model change SOTIF-relevant. The trigger list below is applied by the impact-analysis procedure in [WP-M-12 §7](WP-M-12-impact-analysis.md) and by [change management (WP-P-02)](../07-supporting/WP-P-02-change-management.md).

| Change type | Examples from the baseline history | Required SOTIF re-evaluation |
|---|---|---|
| Model weights or compiled model artefacts (`openpilot/selfdrive/modeld/models/*`) | `4bcf732` (ResAction), `0e0c7c7` / `f59056e` (model swapped and reverted the same day), `d05c2d9` (big models rebuilt) | Update WP-C-06 for changed behaviour; model replay against the previous pin; re-run WP-V-03 known-scenario suite; check validation-target status in WP-V-02; record in WP-K-02 |
| Model runtime / compiler (`tinygrad_repo` pin, `modeld.py`, `parse_model_outputs.py`, `fill_model_msg.py`, `modeld/SConscript` flags) | `d05c2d9` (tinygrad bump, `input_view` change) | As above. Bit-level output comparison on a fixed input set |
| Default or mode changes that alter driving behaviour (`openpilot/common/params_keys.h`, planner, controller) | `f21bfc3` (Experimental Mode default), `ab8c84c` (gas override acceleration boost) | Re-run §6/§7 for affected hazards; decide functional modification (§8); re-verify affected scenarios |
| HMI and alert changes | `28917bb`, `f00d226` (alert sound level and escalation) | Update WP-C-08; check audibility in the reference cabin |
| Diagnostic / monitoring changes | `948ad05` (extends suppression after big-model failure) | Update WP-C-06 and FuSa analyses; check monitoring coverage |
| Field finding (new triggering condition) | n/a | §13 loop: WP-P-03 problem report → WP-C-06 update → decide modification or ODD restriction |

A model or behaviour change cannot be released until the re-evaluation is recorded in the change request and the SOTIF lead has signed it off.

## 10. Verification of SOTIF work products

- Verification reviews of WP-C-05…C-08 and WP-V-02…V-04 follow [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md) through pull requests.
- The acceptance criteria (WP-C-05), validation targets (WP-V-02) and release argument (WP-K-02) are additionally reviewed by the external assessor ([WP-M-06](WP-M-06-confirmation-measures-plan.md)).
- Traceability SH → TC/FI → modification → verification evidence is held in [`trace/`](../trace/README.md) (WP-T-01).

## 11. Schedule

Dates are set in [WP-M-03](WP-M-03-project-plan.md). The ordering is: §4 (G0) → §5–§8 (G1) → §9 (G2) → §10 (G4) → §11, §12 (G5) → §13 (G6).

## Open items

| ID | Item |
|---|---|
| OI-1 | Select and justify the B1 human-driver baseline data set and filtering to the ODD (WP-V-02) |
| OI-2 | Define how the B2 stock-TSS2 comparison is executed on the reference vehicle (scenario list, test site, measurement) |
| OI-3 | Decide whether MetaDrive-based simulation (`openpilot/tools/sim`) has sufficient fidelity to count as evidence, and on which scenarios; re-enable the CI job in the fork |
| OI-4 | Build a LionDriver-controlled log store so that drive logs do not depend on comma servers (shared with WP-O-04, WP-M-09) |
| OI-5 | Generate fork-owned process-replay and model-replay reference sets, including Corolla routes (shared with D-03) |
| OI-6 | Appoint an external HMI / human-factors reviewer for WP-C-08 |
| OI-7 | Confirm with the assessor that excluding Experimental Mode and Chestnut from claims is an acceptable scoping (D-08) |
| OI-8 | Agree which surrogate measures may stand in for harm events, and the argument linking them |
