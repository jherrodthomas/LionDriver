# WP-V-04 Evaluation of Unknown Hazardous Scenarios

| Field | Value |
|---|---|
| Work product | WP-V-04 Evaluation of unknown hazardous scenarios (method, residual risk estimation, results) |
| Standard reference | ISO 21448:2022 §11 (evaluation of unknown hazardous scenarios), §13 (interface to operation); ISO/PAS 8800:2024 (AI V&V, operation-phase monitoring); ASPICE 4.0 VAL.1 |
| Version | 0.10 (§2.1, §5.2 (3): three signatures, or readings of them, are the surrogates for harm of WP-V-02 §4.5, SU-01…SU-03, DQ-140 A; their arguments are drafts, not yet checked against logs; no signature definition changed; 2026-10-25). 0.9 (§6: finding EC-N1 fed back: the HARA rates the lane change that does not stop in the target lane as HE-01.6 (WP-C-03 v0.8, DQ-406 A), the catalogue maps rows EC-11 and EC-13 to it, and WP-V-05 gains case VS-FI-32; 2026-10-22). 0.8 (§6: the U-4 prototype adds six longitudinal and hand-over families (loss of deceleration with a braking or stopped lead, acceleration toward a slower lead, a deceleration step with a close follower, the soft disable and DM stop against a close follower and a slower lead); no new-hazard finding among them; synthetic, no credit; 2026-10-21). 0.7 (§6: the U-4 prototype over the layer-1 plant now searches eight lateral families and writes an edge-case catalogue mapped to the HARA; its one new-hazard finding is queued as DQ-406; synthetic, no credit; 2026-10-20). 0.6 (R3 threshold approved by the project lead: P̂₀ ≤ 0.10 with N ≥ 30, DQ-262 A; §5.4 retitled; OI-2 closed; 2026-10-19). 0.5 (R3 stop rule: a numeric Good–Turing threshold plus the three-block trend rule, DQ-108 A; value proposed in §5.4 and queued for the lead as DQ-262; OI-2; 2026-10-19). 0.4 (§5.2: confidence level C = 95 % one-sided, DQ-057 A; 2026-10-19). 0.3 (U-4 status and synthetic-data labelling per WP-V-02 §5.3; 2026-10-16). 0.2 (exploration blocks follow the highway-only ODD, decision register DQ-023, and the 105 km/h public-road cap, DQ-046; block Bn after every model change, DQ-038; log store without uploads to comma, DQ-084; 2026-10-16). 0.1 |
| Status | Draft (method). Results section is a template: **Not yet executed** |
| ASIL / scope | SOTIF |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); residual-risk method reviewed by the external assessor (D-06) |
| Approver | Project maintainer (SOTIF lead) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Known hazardous scenarios are tested in [WP-V-03](WP-V-03-sotif-known-scenarios.md). This document defines how LionDriver searches for hazardous scenarios that are **not yet known** (ISO 21448 area 3), how discoveries are fed back, and how the residual risk from still-unknown scenarios is estimated for the release argument ([WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md)).

For an end-to-end ML driving model trained on data LionDriver cannot see, area 3 is the dominant SOTIF concern (tailoring T-10, [WP-M-01](../01-management/WP-M-01-assurance-strategy.md)). The method has to work with one reference vehicle, a small number of safety drivers and no access to comma.ai fleet data. It cannot prove that no unknown hazardous scenario remains. It aims to (a) find the most frequent ones early, (b) show a declining discovery trend, and (c) give a stated, conservative estimate of what remains.

## 2. Discovery methods

| ID | Method | Description | Tooling | Preconditions | Strength / limitation |
|---|---|---|---|---|---|
| U-1 | Randomised long-tail driving | Public-road drives on routes chosen at random from a stratified pool covering the ODD (road types, times of day, seasons, weather inside ODD), instead of a fixed commute route. At least 30 % **(TBC)** of mileage on roads not driven before | Route pool + random selection log; [WP-V-07](WP-V-07-vehicle-test-operations.md) operations | G1 passed; WP-V-07 approved | Real inputs; slow; exposure limited to ≈ 10⁴ km/yr ([WP-V-02 §3.2](WP-V-02-sotif-vv-strategy.md#32-what-liondriver-can-achieve)) |
| U-2 | Disengagement and takeover analysis | Every disengagement, driver override, alert and bookmark is classified (§3). Unexplained ones are reviewed on video | Drive logs; `selfdriveState`, `carState`, `onroadEvents`; bookmark flag (`userBookmark`) | U-1 running | Cheap and systematic; depends on the safety driver intervening (conservative) |
| U-3 | Fleet-log mining | Automated queries over all LionDriver logs (test fleet now, field fleet later per [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md)) for anomaly signatures (§2.1) | Log store under LionDriver control ([WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-4; no uploads to comma's servers, DQ-084 option A); log tools in `openpilot/tools/` | LionDriver log store exists | Scales with data; finds near-misses the driver did not notice |
| U-4 | Adversarial and randomised simulation | Search over scenario parameters in MetaDrive (`openpilot/tools/sim`) for failures: random maps, curvature/bank combinations, lighting presets, injected traffic and cut-ins once supported; failure = out-of-lane (`metadrive_process.py:130-138`) or collision | MetaDrive bridge with LionDriver extensions; search scripts (random + guided, e.g., boundary refinement around first failure) | Bridge extended per WP-V-02 §5.3.1 (adaptation to the reference Corolla in progress); results labelled as synthetic (WP-V-02 §5.3.5); failures are hypotheses until reproduced (U-6) | High volume; simulator gap — results not credited without real-world confirmation |
| U-5 | Replay perturbation search | Perturb recorded real inputs (WP-W-10 VS-ML-04 operators, at larger magnitudes) and search for minimal perturbations that flip outputs (lane choice, lead existence) | Replay harness, perturbation tools | Fork-owned replay set | Real-image base; open loop only |
| U-6 | Reproduction on closed course | Hypotheses from U-3/U-4/U-5 that look credible are rebuilt as closed-course trials | [WP-V-07](WP-V-07-vehicle-test-operations.md) closed-course level | Site available | Converts hypotheses into known scenarios |
| U-7 | External information | Upstream issues and release notes, NHTSA L2 investigations and recalls, public openpilot community reports for Toyota TSS2 | Periodic review (monthly) | None | Breadth; not specific to the LionDriver configuration |

### 2.1 Anomaly signatures for U-3

| ID | Signature | Definition (initial) | Relevance | Field event ([WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) §2.1) |
|---|---|---|---|---|
| AS-01 | Steering override while engaged | `carState.steeringPressed` with lateral active, not during a lane change (no blinker on) | SH-01, SH-02 | MON-01 |
| AS-02 | Brake disengagement with high deceleration | Driver brake followed by `aEgo` < −4 m/s² within 2 s | SH-06, SH-03 | MON-01 |
| AS-03 | Gas override during deceleration | Driver gas while planner decelerates > 1.5 m/s² | SH-04 | MON-17 |
| AS-04 | Envelope limit hit | Panda TX blocked or torque/accel at the limit (safety replay, `opendbc_repo/opendbc/safety/safety_replay/`) | SH-01, SH-04 | MON-06 |
| AS-05 | Lane-line proximity | Gap between the vehicle side and a model lane line < 0.3 m to either side while engaged; vehicle width 1.781 m (reference Corolla); only lines with probability ≥ 0.5 count | SH-01 | MON-17 |
| AS-06 | Phantom deceleration | `aEgo` < −2 m/s² while engaged with no closing radar lead (`radarState.leadOne`) within TTC 4 s | SH-04 | MON-17 |
| AS-07 | FCW event | `fcw` alert | SH-06 | MON-08 |
| AS-08 | Model disagreement | Large divergence between action curvature and plan curvature; lead flicker rate above AIR-11 | AE-T | MON-13 |
| AS-09 | Model uncertainty spike | Plan / lead std above the 99.9th percentile of the evaluation set | AE-O | MON-13 |
| AS-10 | DM anomaly | DM alert level 2–3 events; lockouts. Periods of model uncertainty fallback are not scored | SH-12 | MON-07 |
| AS-11 | System events | `steerSaturated`, `commIssue`, `modeldLagging`, soft disables, `excessiveActuation` latch | SH-02, SH-06 (TC-23) | MON-09, MON-10, MON-02, MON-05 |

Thresholds are tuned on a held-out set (DSR-11 of [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md)) and reviewed after each block.

The readings in brackets for AS-01, AS-05, AS-06 and AS-10 were confirmed by the project maintainer on 2026-10-13. They are the choices the extraction script (`tools/field_monitoring/extract_events.py`) makes where the original wording left one open, and they are part of signature-set version `WP-V-04-2.1/2026-10-13`.

Three of these signatures, or readings of them, are the surrogates for harm chosen by the project lead (decision register DQ-140 option A, 2026-10-25), argued in [WP-V-02 §4.5](WP-V-02-sotif-vv-strategy.md#45-surrogates-for-harm-dq-140): AS-05 at a gap of 0 m (SU-01, unrequested lane departure), AS-04 (SU-02, envelope limit hit) and AS-01 with a short time to the line (SU-03). The 0 m and time-to-line readings are not yet in this table. They enter as a new signature-set version, with the extractor, before block B1 (WP-V-02 OI-5). The other signatures are not surrogates for harm; AS-08 stays the field signature of VT-14.

#### 2.1.1 One signature set before and after release

Pre-release exploration and field monitoring use the same signature set, so that discovery rates and surrogate rates before and after release can be compared:

1. **One definition.** This table is the only definition of AS-01…AS-11, including thresholds. WP-O-04 extracts the same signatures from field logs and does not redefine them. Its MON events are the field triage classes that contain them.
2. **One extractor.** Development and field logs are scored by the same extraction script ([WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) OI-4) at the same signature-set version. The version is recorded with every block summary (§6.1) and every field KPI report.
3. **Frozen thresholds.** Thresholds are tuned once on the held-out set before block B1 and are then fixed for a signature-set version. A change of definition or threshold creates a new version. Earlier blocks and field periods are re-scored with it before any comparison.
4. **Same denominator.** Rates are per engaged km inside the ODD, from the exposure data of WP-O-04 §2.2. Engaged km outside the ODD (MON-15) is counted separately and not mixed in.
5. **Same discovery rate.** "Discovery rate" means new class-U scenario classes (§3) per 1 000 engaged km in the ODD, both here (§5.2) and in WP-O-04 §6.

## 3. Event triage and feedback

Each candidate event from U-1…U-7 goes through:

1. **Screening** (within 7 days of the drive): automatic signature plus video review by the SOTIF lead.
2. **Classification:**
   | Class | Meaning | Action |
   |---|---|---|
   | N | Nominal; driver preference or test procedure | Close |
   | K | Instance of a known scenario KS-nn | Add to WP-V-03 statistics |
   | U | New hazardous scenario or triggering condition | Problem report ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)); new TC in [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md); new KS in WP-V-03; decision on functional modification or ODD restriction ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)) |
   | F | Malfunction (E/E fault, software bug) rather than insufficiency | Problem report; FuSa analysis |
3. **Severity estimate** for class U: worst credible outcome using HARA S-classes, assuming no driver intervention.
4. **Record** in the discovery log (§6.2).

A class U event with S3 potential triggers an immediate review of whether testing continues under the current ODD (WP-V-07 §8.5 stop rule S-05).

## 4. Exploration plan

| Block | Content | Size (proposed) | Entry |
|---|---|---|---|
| B0 | Simulation and replay search (U-4, U-5) on the current baseline | 10⁴ simulated km; full replay set | Fidelity extensions in progress; results are hypotheses |
| B1 | First public-road block, primary ODD only (limited-access highway, daylight, dry; engaged at ≤ 105 km/h, DQ-046) | 2 000 km engaged | G1; WP-V-07 public-road level 1 |
| B2 | Extended ODD strata (night with lighting, light rain; arterial roads left the ODD with DQ-023) | 3 000 km engaged | B1 closed: no open class U event with S3 |
| B3 | Randomised routes and seasons | 5 000 km engaged per season | B2 closed |
| Bn | Repeated after each release and after every model or tinygrad change (D-05, adopted by the project lead, DQ-038) | ≥ 1 000 km engaged | Change control ([WP-W-10 §8](../05-software/WP-W-10-ml-engineering.md)) |

Block sizes are planning values; they are set against WP-V-02 targets and achievable capacity.

## 5. Residual risk estimation

### 5.1 Quantities

| Symbol | Meaning | Source |
|---|---|---|
| D | Engaged distance in exploration blocks (real world only) | Logs |
| n_U(b) | Number of new class-U scenario classes found in block b | Discovery log |
| r_HB | Observed hazardous-behaviour events (class K or U with harm potential, driver intervention needed) | Triage |
| λ_HB^UB | Upper confidence bound of the hazardous-behaviour rate | χ² bound (below) |

### 5.2 Methods

1. **Rate bound from exploration mileage.** With r_HB events in D km, the one-sided upper bound at confidence C is `λ_UB = χ²(C; 2·r_HB + 2) / (2·D)`. With zero events, `λ_UB = −ln(1 − C) / D` (≈ 3 / D at 95 %). C = 95 %, one-sided, as for every SOTIF target (WP-V-02 §3 step 3; decided 2026-10-19 by the project lead, decision register DQ-057 option A). This bounds the rate of **all** hazardous behaviour in the explored ODD, known and unknown, but only weakly: 10⁴ km with zero events bounds the rate at ≈ 3 × 10⁻⁴ /km, far above the targets of WP-V-02. It is reported as is.
2. **Discovery-rate trend.** Plot cumulative new scenario classes against cumulative engaged distance. A flattening curve indicates that the frequent unknowns have been found. Fit a species-richness estimator (e.g., Good–Turing: the probability that the next event belongs to an unseen class ≈ f₁ / N, where f₁ is the number of classes seen exactly once and N the number of classified events). Report the estimate and its uncertainty; it is evidence of trend, not a guarantee.
3. **Surrogate scaling.** Use near-miss signatures (§2.1) as leading indicators; estimate the ratio between surrogate events and hazardous events from triage data, then bound the hazardous rate from the more frequent surrogates. The ratio must be argued per signature: only SU-01…SU-03 of [WP-V-02 §4.5](WP-V-02-sotif-vv-strategy.md#45-surrogates-for-harm-dq-140) are used this way (DQ-140 A), and only once their arguments have been checked against logs (WP-V-02 OI-5).
4. **Simulation contribution.** Failures found in simulation are not counted into λ but are used to direct U-6 reproduction; a simulation family with an approved fidelity case may contribute a per-scenario p_s estimate to the decomposition of WP-V-02 §3 step 5.

### 5.3 Acceptance for release

The SOTIF release argument (WP-K-02) may claim acceptable residual risk from unknown scenarios, and acceptance criterion AC-07 of [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md#53-qualitative-acceptance-criteria) is met, only if all of the following hold:

| # | Criterion |
|---|---|
| R1 | All planned exploration blocks for the claimed ODD are complete |
| R2 | No open class U event with S2/S3 potential |
| R3 | Discovery trend non-increasing over the last three blocks, **and** the Good–Turing unseen-class probability at or below 0.10 with at least 30 classified events (§5.4; DQ-108 A, value DQ-262 A) |
| R4 | λ_UB from §5.2 (1) and the surrogate bound from §5.2 (3) reported with their assumptions |
| R5 | Field-monitoring triggers in WP-O-04 are defined so that a new scenario class found after release leads to restriction or withdrawal |
| R6 | The argument states explicitly that the bound is weaker than the WP-V-02 rate targets and that acceptance rests on the envelope, controllability evidence and known-scenario evidence |

### 5.4 R3 threshold

The project lead decided on 2026-10-19 that the search for unknown hazardous scenarios stops on a numeric threshold plus the three-block trend rule (decision register DQ-108, option A). On the same day, before block B1, the lead approved the value below as proposed (DQ-262, option A). It is fixed before any block data exists, so the result cannot be fitted to it.

**Estimator.** `P̂₀ = f₁ / N`, computed over the real-world blocks (simulation and replay findings are not counted, §5.2 (4)).

- **N** is the number of classified hazardous-scenario events: r_HB of §5.1, classes K and U. N and F events are excluded, because they are not insufficiencies.
- **f₁** is the number of scenario classes met exactly once. A class is a KS-nn of WP-V-03 or a new class U.

The expected rate of events from classes not yet seen is then `P̂₀ · N / D = f₁ / D` per engaged km.

**Threshold: P̂₀ ≤ 0.10, with N ≥ 30** (DQ-262 A).

1. **Why 0.10.** WP-V-02 §3 step 1 sets the targets on 90 % of each group's harm budget and holds back 10 % for scenarios not yet known. Assume an event from an unseen class is no more harmful than one from a seen class; R2 checks the severity of every class U event found. Then events from unseen classes stay inside that reserve when at most 10 % of events are expected to come from unseen classes.
2. **Why N ≥ 30.** With fewer events, one more single-occurrence class moves P̂₀ by more than 0.03, and the estimate says little. At N = 30 the threshold allows at most three classes seen once.
3. **When the count is not reached.** If the planned blocks (B1–B3) end with N < 30, R3 is not met by count. The SOTIF lead reports this with λ_UB (R4). Choosing between more blocks and a release that states the shortfall is then a new decision for the lead (the cost named in DQ-262 A).
4. **What it does not show.** The estimate assumes events are independent and the classes are stable over the blocks. It says nothing about classes that the ODD, routes and seasons of the blocks never reach. R1 and the stratified route pool (OI-4) cover that.

The value is fixed before the blocks start, so the result cannot be fitted to it. A change after the blocks start needs a new dated decision.

## 6. Results

**Not yet executed.** No exploration block has been run. No LionDriver drive logs exist at the baseline.

**U-4 prototype (synthetic, DSR-12, no evidence credit).** Before MetaDrive runs end to end, the failure search runs
over the layer-1 fault-injection plant ([`sim/search/`](../sim/search/families.yaml)): eight lateral families (loss of
assist in a curve; fault timing at curve entry, mid-curve and exit, during an assisted lane change and after the
driver's correction starts, and a fault that clears and returns; driver edge cases; a fault in a curve at R_ODD near
the ODD speed bound; a hard-over in a narrow lane with crosswind) and six longitudinal and hand-over families (loss of
deceleration while the lead brakes or with a stopped vehicle ahead, acceleration toward a slower lead, a deceleration
step with a close follower, and the fault soft disable and driver-monitoring stop against a close follower and a
slower lead, in each order of alert and slow-down that register DQ-407 offers). Its
[edge-case catalogue](../sim/results/edge-cases.md) lists the worst case of each, which stated assumption decides it,
and the HARA hazardous event it falls under. Two lateral rows matched no hazardous event (EC-N1, an assisted lane change
that does not stop at the target lane). That finding went to the project lead as DQ-406; on the lead's answer
(option A, 2026-10-22) the HARA rates it as HE-01.6 ([WP-C-03](../02-concept/WP-C-03-hara.md) v0.8), the catalogue
maps both rows to it, and [WP-V-05](WP-V-05-fault-injection.md) VS-FI-32 injects the fault late in a lane change. Every longitudinal contact falls under a hazardous event (HE-04.1, HE-06.3). These are hypotheses
for U-6, not exploration-block results: the plant has no tyre friction limit and no perception (its ACC sees every
lead at once and at any range).

### 6.1 Block summary template

| Block | Dates | Software / model hashes | Engaged km | Hours | Routes (new %) | Events screened | N | K | U | F | λ_UB (95 %) | New classes | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | | | (sim) | | | | | | | | n/a | | Not yet executed |
| B1 | | | | | | | | | | | | | Not yet executed |
| B2 | | | | | | | | | | | | | Not yet executed |
| B3 | | | | | | | | | | | | | Not yet executed |

### 6.2 Discovery log template

| UID | Date | Block / method | Log ID | Description | Class | Severity estimate | Linked TC / KS | Problem report | Decision | Closed |
|---|---|---|---|---|---|---|---|---|---|---|
| U-0001 | | | | | | | | | | |

### 6.3 Residual-risk estimate template

| Item | Value | Assumptions |
|---|---|---|
| Total real-world engaged distance D | | |
| Hazardous-behaviour events r_HB | | |
| λ_UB (95 %) | | |
| Good–Turing unseen-class probability | | |
| Surrogate-scaled bound | | |
| Conclusion | Not yet executed | |

## Open items

| ID | Item |
|---|---|
| OI-1 | Build the LionDriver log store and query tooling for U-3 (shared with WP-M-08 OI-4, WP-O-04) |
| OI-2 | **Closed 2026-10-19.** R3 rule decided by the project lead (DQ-108 option A): numeric Good–Turing threshold plus the three-block trend rule. Value P̂₀ ≤ 0.10 with N ≥ 30 approved before B1 (DQ-262 option A, §5.4). An assessor reviews it later (I1) |
| OI-3 | Extend the MetaDrive bridge for U-4 (traffic, scenario scripting, randomised maps). In progress by the simulation session (WP-V-02 §5.3.1): traffic and pedestrian models and headless rendering work; scenario scripting and randomised maps are not built |
| OI-4 | Define the stratified route pool for U-1 once the ODD (WP-C-02) is fixed |
