# WP-V-02 SOTIF Verification and Validation Strategy

| Field | Value |
|---|---|
| Work product | WP-V-02 SOTIF verification and validation strategy, validation targets |
| Standard reference | ISO 21448:2022 §9 (V&V strategy, validation targets), Annex C (informative, validation target derivation); ISO/PAS 8800:2024 (AI V&V); ASPICE 4.0 VAL.1 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); validation targets reviewed by the external assessor (D-06, [WP-M-08 §10](../01-management/WP-M-08-sotif-plan.md)) |
| Approver | Project maintainer (acting safety manager, SOTIF lead) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document turns the acceptance-criteria approach of the [SOTIF plan (WP-M-08 §5)](../01-management/WP-M-08-sotif-plan.md#5-acceptance-criteria-approach) into validation targets (VT-nn), shows how each target could be demonstrated, and states plainly which targets cannot be demonstrated by LionDriver driving alone. It selects the verification and validation methods for known hazardous scenarios ([WP-V-03](WP-V-03-sotif-known-scenarios.md)) and unknown hazardous scenarios ([WP-V-04](WP-V-04-sotif-unknown-scenarios.md)), and the evidence each method can and cannot provide.

Scope: reference configuration of [WP-M-01 §3.1](../01-management/WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to), Chill longitudinal mode, AI-1 driving model, AI-3 DM model. Experimental Mode and the Chestnut big model are outside the claim (D-08, AIR-29, AIR-30) and are not validated here.

Sequencing rule ([WP-M-08 §4.1](../01-management/WP-M-08-sotif-plan.md#41-sequencing-rules)): the targets in §4 are fixed and approved **before** evidence for them is collected.

Inputs: SOTIF hazards SH-01…SH-13 and acceptance criteria ([WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md) §3, §5), functional insufficiencies FI-01…FI-22 and triggering conditions TC-01…TC-31 ([WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md)), functional modifications FM-01…FM-11 ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)), ODD parts ODD-H and ODD-A ([WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md)), controllability assumptions CA-01…CA-07 and DM performance DMP-01…DMP-04 ([WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)). [WP-C-05 §5.2](../02-concept/WP-C-05-sotif-hazard-identification.md#52-derivation-method-for-validation-targets-to-be-applied-in-wp-v-02) delegates the numeric targets to this document; §3 applies that method.

## 2. Acceptance criteria (input)

| Baseline | Use | Source (to be confirmed, [WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-1, OI-2) |
|---|---|---|
| B1 human driver | Rate-level targets (per distance / per hour) | US crash, injury and fatality rates (NHTSA FARS, CRSS) filtered to the ODD road types |
| B2 stock TSS2 | Scenario-level comparison: LD-SDA shall not perform worse than the same Corolla with stock Lane Tracing Assist / Dynamic Radar Cruise Control in any validated scenario | Comparative closed-course tests on the reference vehicle |

The acceptance criteria are those of [WP-C-05 §5](../02-concept/WP-C-05-sotif-hazard-identification.md#5-acceptance-criteria): (1) per SH group, the rate of harm while engaged shall not exceed the human-driver rate for comparable conditions reduced by a factor for the stock-TSS2 baseline; (2) the qualitative criteria AC-01…AC-07. This document adds the B2 scenario comparison (VT-09).

## 3. Method for deriving validation targets

For each SOTIF hazardous behaviour SH-nn:

1. **Harm budget.** Allocate to each SH group of WP-C-05 §5.2 step 3 (lateral SH-01/02/10; longitudinal SH-03/04/06/11; mode and override SH-05/09; SH-08) a share `k` of the road-class-specific B1 harm rate `λ_B1` for the relevant harm class (injury crash or fatality), separately for ODD-H and ODD-A:  `λ_harm,SH ≤ k · λ_B1`.
2. **Hazardous-behaviour rate.** Divide by the probability that the hazardous behaviour, once it occurs, leads to harm: `P(harm | HB) = P(E-situation) · P(not controlled) · P(severity class)`. Each factor needs evidence (HARA exposure, controllability tests in [WP-V-01](WP-V-01-safety-validation.md), crash statistics). A factor without evidence is set to 1.
   `λ_HB,SH ≤ k · λ_B1 / P(harm | HB)`
3. **Demonstration size.** For a zero-failure demonstration at confidence C, the exposure needed is
   `n = −ln(1 − C) / λ_HB`
   (exponential/Poisson model; with r observed failures, use the χ² bound `n = χ²(C; 2r + 2) / (2 λ)`).
4. **Feasibility check.** Compare n with LionDriver's achievable exposure (§3.2). If n is out of reach, decompose (step 5) and narrow the ODD ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)).
5. **Scenario decomposition.** `λ_HB = Σ_s ε_s · p_s`, where ε_s is the exposure rate of scenario class s (occurrences per km, estimated from LionDriver drive logs, which needs far less mileage than observing rare failures), and p_s is the probability of hazardous behaviour given s (estimated per scenario by simulation, replay and closed-course trials). Per-scenario targets p_s,max are set so that the sum meets λ_HB. A zero-failure demonstration of `p_s ≤ p_max` at confidence C needs `N = ln(1 − C) / ln(1 − p_max)` trials (≈ 3 / p_max at C = 95 %).

### 3.1 Illustration of magnitudes

The figures below are **illustrative orders of magnitude** to show feasibility; the baseline values must be replaced by the selected and filtered data set (OI-2). Average engaged speed is assumed to be 64 km/h (40 mph) to convert distance to time. `−ln(1 − 0.95) ≈ 3.0`; `−ln(1 − 0.99) ≈ 4.6`.

| Case | Assumed rate λ | Zero-failure exposure at C = 95 % | Same in hours | C = 99 % |
|---|---|---|---|---|
| A. Match US fatality rate (≈ 1.3 per 10⁸ vehicle-miles, all roads) | 1.3 × 10⁻⁸ /mi | ≈ 2.3 × 10⁸ mi (3.7 × 10⁸ km) | ≈ 5.8 × 10⁶ h | ≈ 3.5 × 10⁸ mi |
| B. Case A with only 10 % of the human fatality rate allocated to LD-SDA SOTIF hazards (k = 0.1) | 1.3 × 10⁻⁹ /mi | ≈ 2.3 × 10⁹ mi | ≈ 5.8 × 10⁷ h | ≈ 3.5 × 10⁹ mi |
| C. Match an injury-crash rate of ≈ 1 per 2 × 10⁶ mi | 5 × 10⁻⁷ /mi | ≈ 6 × 10⁶ mi | ≈ 1.5 × 10⁵ h | ≈ 9 × 10⁶ mi |
| D. Hazardous-behaviour rate for SH-01 with k = 0.1 of case C and P(harm \| HB) = 0.01 (controllability 0.9 × harmful situation 0.1, both needing evidence) | 5 × 10⁻⁶ /mi | ≈ 6 × 10⁵ mi | ≈ 1.5 × 10⁴ h | ≈ 9 × 10⁵ mi |
| E. Per-scenario: stationary-lead approach, p_max = 1 % | — | 299 trials | — | 459 trials |
| F. Per-scenario: p_max = 5 % | — | 59 trials | — | 90 trials |

### 3.2 What LionDriver can achieve

| Means | Plausible capacity per year (one reference vehicle, one maintainer plus safety drivers) | Reaches |
|---|---|---|
| Public-road driving with safety driver (WP-V-07) | 10⁴ – 2 × 10⁴ km engaged (≈ 150–300 h) | Exposure estimates ε_s for common scenarios; surrogate rates (takeovers, envelope hits); **no** rate-level demonstration of cases A–D |
| Closed-course trials | Tens to low hundreds of trials per scenario per campaign | Case F; case E for a few scenarios |
| Replay of recorded drives (process/model replay, open loop) | All recorded data, repeatedly, per software change | Perception and planner outputs on real inputs; no closed-loop consequence |
| Simulation (MetaDrive, closed loop) | 10³ – 10⁵ runs per scenario family (compute-bound) | Case E and below for scenario families that the simulator can represent credibly (§5.3) |
| Field monitoring (WP-O-04) | Grows with the LionDriver fleet (initially one vehicle) | Long-term confirmation; not a pre-release argument |

**Conclusion.** Cases A–C are out of reach of LionDriver driving by roughly three to five orders of magnitude, and remain unachievable at any realistic fleet size for this project. Case D is out of reach by roughly two orders of magnitude. LionDriver therefore **does not claim a rate-level demonstration** of AC-0. The release argument (WP-K-02) rests on:

1. the safety envelope bounding the magnitude of every hazardous behaviour, so that controllability is shown by test ([WP-V-01](WP-V-01-safety-validation.md)) rather than assumed;
2. scenario-decomposed targets (step 5) demonstrated by simulation, replay and closed-course trials (cases E/F);
3. exposure rates ε_s and surrogate indicators measured on public roads;
4. B2 comparison: no validated scenario worse than the stock system;
5. an ODD narrowed to what 1–4 cover;
6. field monitoring with predefined triggers to restrict or withdraw the function.

The residual uncertainty that cannot be closed this way is stated in WP-K-02, not hidden.

## 4. Validation targets

Targets are **proposals**: numeric values are placeholders for the assessor review and WP-C-05 acceptance criteria (OI-3). "Demonstration" names the primary method; §5 defines the methods.

| ID | SH | Quantity | Proposed target | Derivation | Demonstration | Achievable? |
|---|---|---|---|---|---|---|
| VT-01 | SH-01 excessive / wrong lateral motion | Unrequested lane departures (AIR-02) per engaged hour | Rate-level: ≤ 5 × 10⁻⁶ /mi (case D). Scenario-level: p_s ≤ 1 % per scenario in KS-01…KS-06, KS-14 at 95 % | §3 steps 1–5; P(not controlled) from VS-VAL controllability tests | Scenario-level by SIM + CC + REPLAY; rate-level surrogate on public road | Scenario-level yes; rate-level no (reported as surrogate with upper bound) |
| VT-02 | SH-02 unannounced loss of lateral control | Lateral drift > 0.5 m without a take-over alert within 1 s | p_s ≤ 1 % per curve/marking scenario; zero occurrences in all CC trials | SG-02 budget (≤ 1 s to warning) | CC (KS-01, KS-03), SIM, REPLAY | Scenario-level yes |
| VT-03 | SH-03 unintended acceleration | Positive acceleration toward a slower or stopped lead inside the time gap | Zero occurrences in KS-07…KS-09 trials (≥ 59 per scenario) | §3 step 5, case F | SIM (`longitudinal_maneuvers` + MetaDrive), CC | Yes |
| VT-04 | SH-04 phantom braking | Decelerations < −2.0 m/s² without a relevant object (AIR-05) | Surrogate on public road: ≤ 1 per 1000 km with 95 % upper bound reported; scenario-level p_s ≤ 1 % for bridges/overpasses, metal plates, shadows (KS-10, KS-11) | §3 step 5 | REPLAY of recorded drives, PR | Partially (upper bound limited by mileage) |
| VT-05 | SH-05 override not effective | Release on brake / cancel / steering override | 100 % release within SG-05 budget in ≥ 299 trials per input type and speed band (p ≤ 1 % at 95 %) | Deterministic function, tested as a sample | CC, HIL (WP-V-05) | Yes |
| VT-06 | SH-06 missed or late stationary/slow lead | Collision or required driver braking > 5 m/s² | p_s ≤ 1 % per approach-speed band in the ODD (KS-05, KS-08); FCW at TTC ≥ 2 s (AIR-06) | §3 step 5, case E; B2 comparison | CC with soft target, SIM | Yes for the bands tested |
| VT-07 | SH-08 PCS suppression | Stock PCS activation with LD-SDA installed vs stock | Equivalent activation (same TTC ± 0.2 s) in every PCS soft-target test | B2 | CC (KS-20; VS-VAL in WP-V-01) | Yes |
| VT-08 | SH-12 prolonged unsupervised operation (DM) | Distraction, phone, sleep detection; fallback on camera blockage | AIR-07/AIR-08 thresholds per DM stratum; DMP-01…DMP-04; AC-05 | WP-C-08 §5.3 | EVAL (VS-ML-06), CC (WP-C-08 §8 V-5) | Yes |
| VT-09 | All | Comparative performance vs stock TSS2 (B2) | LD-SDA not worse than stock in any KS scenario run with both (metric per scenario in WP-V-03) | B2 | CC, PR (paired routes) | Yes for scenarios run |
| VT-10 | All | Unknown-scenario discovery rate | Discovery rate of new hazardous scenario classes (WP-V-04 §5) decreasing over the last 3 exploration blocks, with no class of severity S3 found in the last block | 21448 §11 | PR, SIM exploration, log mining | Yes as a trend; not as a proof |
| VT-11 | All | Field: harm-level events attributable to LD-SDA | Zero injury crashes; trigger thresholds for restriction defined in WP-O-04 | B1 (long-term) | Field monitoring | Long-term only |
| VT-12 | SH-13 operation outside the ODD | Engaged operation above the ODD speed bound or in excluded conditions | Deterministic speed bound (FM-07): 100 % prevention/disengagement in ≥ 59 trials per speed threshold; other exits covered by user information and driver procedure (AC-04) | FM-07, FM-08 | CC, inspection | Yes for speed; not for other exits |
| VT-13 | SH-10 assisted lane change into an occupied lane | Driver can abort a nudge-initiated lane change | Abort controllable in ≥ 20/20 subjects (CA-01 logic) | WP-C-06 TC-28 | CC (KS-14) | Yes |

SH-09 (traffic-control non-compliance) has no target: Experimental Mode is off and locked (FM-01) and KS-24 verifies the exclusion. SH-11 (no VRU response) has no rate target: [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) resolves TC-12 by ODD restriction and user information; KS-22 and KS-23 only verify that the item does not move toward a VRU it cannot see.

## 5. Test methods

### 5.1 Methods matrix

| Method | Tooling in repo | What it shows | Fidelity / limits | Evidence credit | VTs |
|---|---|---|---|---|---|
| M1 Process replay (open loop, recorded inputs) | `openpilot/selfdrive/test/process_replay/test_processes.py`, `process_replay.py`, `compare_logs.py` | Determinism and regression of controlsd, plannerd, radard, selfdrived, dmonitoringd on recorded inputs | Open loop: vehicle response not re-simulated. References come from `commaai/ci-artifacts` (`test_processes.py:70`); one Corolla TSS2 route in the source list (`:26`) | Regression only, once fork-owned references exist (D-03) | Supports all |
| M2 Model replay | `process_replay/model_replay.py` | Model output changes between versions | One 3 s segment (`model_replay.py:23-26`); forced pass in CI (`:294-296`); comma device pool | Regression only; extended per [WP-W-10](../05-software/WP-W-10-ml-engineering.md) VS-ML-12 | Supports VT-01…06 |
| M3 Requirements-based model evaluation | To be built (WP-W-10 VS-ML-03…08) | AIR metrics per ODD stratum on LionDriver data | Open loop | Primary for perception-level AIRs | VT-01, 04, 06, 08 |
| M4 Closed-loop simulation | `openpilot/tools/sim` (MetaDrive bridge) | Closed-loop lateral behaviour of the full stack with rendered images | Fixed loop track, 2 lanes 4.5 m wide, 90° curves, **no traffic** (`metadrive_bridge.py:30-46, 84`); rendering not photorealistic; vehicle dynamics not Corolla; CI job disabled (`.github/workflows/tests.yaml:185`) and bridge test skipped (`tools/sim/tests/test_sim_bridge.py:24`); success criterion is only "stay in lane" (`metadrive_process.py:130-138`) | **No credit until fidelity is argued per scenario family** ([WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-3). Use for exploration and trend data first | VT-01, 02, 10 (after fidelity case) |
| M5 Planner maneuver tests (plant model) | `openpilot/selfdrive/test/longitudinal_maneuvers/` | Longitudinal planner response to lead/stop scenarios; crash check `d_rel < 0.4 m` (`maneuver.py:66-68`) | Point-mass plant, not Corolla; lead from synthetic radar/vision probability; no perception | Planner-level verification for VT-03/06 sub-cases | VT-03, VT-06 |
| M6 Safety replay | `opendbc_repo/opendbc/safety/safety_replay/` | Envelope limit hits in recorded drives | Needs LionDriver Corolla logs | Surrogate indicator | VT-01, 04 (surrogate) |
| M7 HIL bench | To be built (D-04) | Envelope and fault reactions with real panda firmware | Bench CAN only | FuSa (WP-V-05); SOTIF for VT-05 | VT-05 |
| M8 Closed course | Reference vehicle, test site, soft targets; `tools/longitudinal_maneuvers`, `tools/lateral_maneuvers` for characterization | Real vehicle, real sensors, controlled scenario | Limited speed, scenario set, number of trials; soft target radar signature | Primary for VT-02, 03, 05, 06, 07, 09 | as listed |
| M9 Public road with safety driver | [WP-V-07](WP-V-07-vehicle-test-operations.md) | Real ODD exposure, exposure rates ε_s, surrogates, unknown scenarios | Uncontrolled; low mileage | Exposure estimates and surrogate rates; WP-V-04 exploration | VT-01, 04, 09, 10 |
| M10 Field monitoring | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) | Post-release behaviour | Small fleet | Operation phase only | VT-11 |

### 5.2 Order of application per scenario

1. M3/M1 on recorded data to check perception and planning outputs for the scenario.
2. M4/M5 to explore parameter ranges and estimate p_s where the simulator is credible.
3. M8 to confirm the worst cases from step 2 on the real vehicle, and to run scenarios the simulator cannot represent.
4. M9 to observe the scenario in the real ODD and estimate ε_s.

### 5.3 Simulation fidelity case (required before M4 gets credit)

For each scenario family, the fidelity case shall compare MetaDrive results with M8 results for at least 5 matched parameter points: lateral offset trace, alert timing and outcome class. Credit is given only to families where outcomes match. Required extensions before any family qualifies: Corolla-like vehicle dynamics and actuator delay; traffic agents for lead/cut-in scenarios; map variety beyond the fixed loop; scenario scripting with recorded pass/fail; a re-enabled, fork-owned CI job.

## 6. Coverage of triggering conditions

Triggering conditions from [WP-C-06 §4](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), the known scenarios that cover them ([WP-V-03](WP-V-03-sotif-known-scenarios.md)) and the methods used. TCs that WP-C-06 resolves by ODD exclusion are covered by an ODD-exit check rather than a performance test.

| TC | Short name | KS | M1 | M3 | M4 | M5 | M8 | M9 |
|---|---|---|---|---|---|---|---|---|
| TC-01, TC-02 | Low sun, oncoming headlights | KS-12 | | ● | | | ○ | ● |
| TC-03 | Rain, spray, wet reflections | KS-15 | | ● | | | ○ | ● |
| TC-04 | Fog, snow (outside ODD) | KS-15 (ODD-exit check) | | | | | | ○ |
| TC-05 | Faded / doubled markings, tar seams | KS-03 | | ● | ○ | | ● | ● |
| TC-06 | Work zone (outside ODD) | KS-13 (ODD-exit check) | | ● | | | ● | ○ |
| TC-07 | Close cut-in | KS-07 | | ● | ○ | ● | ● | ● |
| TC-08 | Stationary vehicle in lane | KS-05 | | ● | ○ | ● | ● | ● |
| TC-09 | Cut-out revealing stopped vehicle | KS-09 | | ● | | ● | ● | |
| TC-10, TC-11 | Overhead structures, metal plates, radar emitters | KS-10, KS-11 | | ● | | | ● | ● |
| TC-12 | VRU at road edge or crossing | KS-22 | | ● | | | ● | ○ |
| TC-13 | Signals / stop signs (Experimental only) | KS-24 (exclusion check) | | | | | | |
| TC-14 | Curve tighter than R_ODD, ramps | KS-01 | | ● | ● | | ● | ● |
| TC-15, TC-16 | Banking, crown, cross-wind, grades | KS-02 | | ● | ○ | | ○ | ● |
| TC-17 | Crest with limited sight distance | KS-05 (crest variant) | | ● | | ● | ○ | ● |
| TC-18 | Tunnel (not validated, excluded) | KS-12 (ODD-exit check) | | ○ | | | | ○ |
| TC-19 | Mount disturbed, dirty windscreen | KS-16 | | ● | | | ● | |
| TC-20 | Speed above ODD | KS-25 | ● | | | | ● | |
| TC-21 | Extreme ambient temperature | KS-21 (overheat path) | ● | | | | ○ | ○ |
| TC-22 | Big model load/fail (excluded, FM-02) | KS-24 (exclusion check) | | | | | | |
| TC-23 | Message delays / process restart | KS-21 | ● | | ● | | ● | |
| TC-24 | Sunglasses, low light, face out of view | KS-17 | | ● | | | ● | ● |
| TC-25 | Periodic small inputs while inattentive | KS-18 | | ● | | | ● | |
| TC-26 | Debug / DM demo parameters | KS-24 (configuration check) | | | | | | |
| TC-27 | Resume with pedestrian between ego and lead | KS-23 | | | | ● | ● | |
| TC-28 | Lane-change nudge with vehicle in blind spot | KS-14 | | | | | ● | ○ |
| TC-29 | Gas override mistaken for disengagement | KS-19 | | | | | ● | ● |
| TC-30 | PCM cruise stays active after disengagement | KS-26 | ● | | | | ● | |
| TC-31 | Exit lane / lane split | KS-04 | | ● | | | | ● |

M1 process replay, M3 model evaluation, M4 simulation, M5 planner maneuver tests, M8 closed course, M9 public road. ● primary, ○ supporting. Every TC has at least one KS; AC-01 of WP-C-05 is checked against this table.

## 7. Verification of SOTIF functional modifications

Each functional modification decided in [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md) (FM-01…FM-11) gets a verification entry in [WP-S-09](../03-system/WP-S-09-system-verification.md) and is re-checked in the WP-V-03 scenarios it targets. A modification is credited in the residual-risk argument only after both.

## 8. Outputs

| Output | Where |
|---|---|
| Known-scenario specifications and results | [WP-V-03](WP-V-03-sotif-known-scenarios.md) |
| Unknown-scenario exploration and residual-risk estimate | [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) |
| Controllability and vehicle-level validation | [WP-V-01](WP-V-01-safety-validation.md) |
| ML evaluation | [WP-W-10](../05-software/WP-W-10-ml-engineering.md) |
| Target status and release recommendation | [WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md) |

## Open items

| ID | Item |
|---|---|
| OI-1 | Keep the §6 TC table in step with WP-C-06 revisions (new TCs need a KS entry) |
| OI-2 | Select B1 data set and filter to the ODD; replace the illustrative rates of §3.1 (shared with WP-M-08 OI-1) |
| OI-3 | Approve numeric targets VT-01…VT-11 with the assessor before collecting evidence |
| OI-4 | Build the simulation fidelity case (§5.3) and decide which families get credit (WP-M-08 OI-3) |
| OI-5 | Define the surrogate-to-harm argument for VT-04 and the takeover-based surrogates (WP-M-08 OI-8) |
| OI-6 | Decide the evidence route for P(not controlled) in step 2 (WP-V-01 controllability tests) and for P(E-situation) (HARA OI-2) |
