# WP-V-04 Evaluation of Unknown Hazardous Scenarios

| Field | Value |
|---|---|
| Work product | WP-V-04 Evaluation of unknown hazardous scenarios (method, residual risk estimation, results) |
| Standard reference | ISO 21448:2022 §11 (evaluation of unknown hazardous scenarios), §13 (interface to operation); ISO/PAS 8800:2024 (AI V&V, operation-phase monitoring); ASPICE 4.0 VAL.1 |
| Version | 0.1 |
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
| U-3 | Fleet-log mining | Automated queries over all LionDriver logs (test fleet now, field fleet later per [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md)) for anomaly signatures (§2.1) | Log store under LionDriver control ([WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-4); log tools in `openpilot/tools/` | LionDriver log store exists | Scales with data; finds near-misses the driver did not notice |
| U-4 | Adversarial and randomised simulation | Search over scenario parameters in MetaDrive (`openpilot/tools/sim`) for failures: random maps, curvature/bank combinations, lighting presets, injected traffic and cut-ins once supported; failure = out-of-lane (`metadrive_process.py:130-138`) or collision | MetaDrive bridge with LionDriver extensions; search scripts (random + guided, e.g., boundary refinement around first failure) | Bridge extended per WP-V-02 §5.3; failures are hypotheses until reproduced (U-6) | High volume; simulator gap — results not credited without real-world confirmation |
| U-5 | Replay perturbation search | Perturb recorded real inputs (WP-W-10 VS-ML-04 operators, at larger magnitudes) and search for minimal perturbations that flip outputs (lane choice, lead existence) | Replay harness, perturbation tools | Fork-owned replay set | Real-image base; open loop only |
| U-6 | Reproduction on closed course | Hypotheses from U-3/U-4/U-5 that look credible are rebuilt as closed-course trials | [WP-V-07](WP-V-07-vehicle-test-operations.md) closed-course level | Site available | Converts hypotheses into known scenarios |
| U-7 | External information | Upstream issues and release notes, NHTSA L2 investigations and recalls, public openpilot community reports for Toyota TSS2 | Periodic review (monthly) | None | Breadth; not specific to the LionDriver configuration |

### 2.1 Anomaly signatures for U-3

| Signature | Definition (initial) | Relevance |
|---|---|---|
| Steering override while engaged | `carState.steeringPressed` with lateral active, not during a lane change | SH-01, SH-02 |
| Brake disengagement with high deceleration | Driver brake followed by `aEgo` < −4 m/s² within 2 s | SH-06, SH-03 |
| Gas override during deceleration | Driver gas while planner decelerates > 1.5 m/s² | SH-04 |
| Envelope limit hit | Panda TX blocked or torque/accel at the limit (safety replay, `opendbc_repo/opendbc/safety/safety_replay/`) | SH-01, SH-04 |
| Lane-line proximity | Model lane-line offset < 0.3 m to either side while engaged | SH-01 |
| Phantom deceleration | `aEgo` < −2 m/s² while engaged with no lead within TTC 4 s | SH-04 |
| FCW event | `fcw` alert | SH-06 |
| Model disagreement | Large divergence between action curvature and plan curvature; lead flicker rate above AIR-11 | AE-T |
| Model uncertainty spike | Plan / lead std above the 99.9th percentile of the evaluation set | AE-O |
| DM anomaly | Long periods of model uncertainty fallback; alert level 2–3 events; lockouts | Misuse |
| System events | `steerSaturated`, `commIssue`, `modeldLagging`, soft disables, `excessiveActuation` latch | Internal degradation |

Thresholds are tuned on a held-out set (DSR-11 of [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md)) and reviewed after each block.

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
| B1 | First public-road block, primary ODD only (limited-access highway, daylight, dry) | 2 000 km engaged | G1; WP-V-07 public-road level 1 |
| B2 | Extended ODD strata (arterial roads, night with lighting, light rain) | 3 000 km engaged | B1 closed: no open class U event with S3 |
| B3 | Randomised routes and seasons | 5 000 km engaged per season | B2 closed |
| Bn | Repeated after each release or model change | ≥ 1 000 km engaged | Change control ([WP-W-10 §8](../05-software/WP-W-10-ml-engineering.md)) |

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

1. **Rate bound from exploration mileage.** With r_HB events in D km, the one-sided upper bound at confidence C is `λ_UB = χ²(C; 2·r_HB + 2) / (2·D)`. With zero events, `λ_UB = −ln(1 − C) / D` (≈ 3 / D at 95 %). This bounds the rate of **all** hazardous behaviour in the explored ODD, known and unknown, but only weakly: 10⁴ km with zero events bounds the rate at ≈ 3 × 10⁻⁴ /km, far above the targets of WP-V-02. It is reported as is.
2. **Discovery-rate trend.** Plot cumulative new scenario classes against cumulative engaged distance. A flattening curve indicates that the frequent unknowns have been found. Fit a species-richness estimator (e.g., Good–Turing: the probability that the next event belongs to an unseen class ≈ f₁ / N, where f₁ is the number of classes seen exactly once and N the number of classified events). Report the estimate and its uncertainty; it is evidence of trend, not a guarantee.
3. **Surrogate scaling.** Use near-miss signatures (§2.1) as leading indicators; estimate the ratio between surrogate events and hazardous events from triage data, then bound the hazardous rate from the more frequent surrogates. The ratio must be argued per signature (WP-V-02 OI-5).
4. **Simulation contribution.** Failures found in simulation are not counted into λ but are used to direct U-6 reproduction; a simulation family with an approved fidelity case may contribute a per-scenario p_s estimate to the decomposition of WP-V-02 §3 step 5.

### 5.3 Acceptance for release

The SOTIF release argument (WP-K-02) may claim acceptable residual risk from unknown scenarios only if all of the following hold:

| # | Criterion |
|---|---|
| R1 | All planned exploration blocks for the claimed ODD are complete |
| R2 | No open class U event with S2/S3 potential |
| R3 | Discovery trend non-increasing over the last three blocks; Good–Turing unseen-class probability reported (target value to be agreed, OI-2) |
| R4 | λ_UB from §5.2 (1) and the surrogate bound from §5.2 (3) reported with their assumptions |
| R5 | Field-monitoring triggers in WP-O-04 are defined so that a new scenario class found after release leads to restriction or withdrawal |
| R6 | The argument states explicitly that the bound is weaker than the WP-V-02 rate targets and that acceptance rests on the envelope, controllability evidence and known-scenario evidence |

## 6. Results

**Not yet executed.** No exploration block has been run. No LionDriver drive logs exist at the baseline.

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
| OI-2 | Agree the R3 discovery-trend criterion and target with the assessor |
| OI-3 | Extend the MetaDrive bridge for U-4 (traffic, scenario scripting, randomised maps) |
| OI-4 | Define the stratified route pool for U-1 once the ODD (WP-C-02) is fixed |
| OI-5 | Agree with WP-O-04 the signature set and thresholds used in both pre-release exploration and field monitoring, so that statistics are comparable |
