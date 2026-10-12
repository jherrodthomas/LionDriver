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

Inputs: SOTIF hazards SH-01…SH-13 and acceptance criteria ([WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md) §3, §5), functional insufficiencies FI-01…FI-22 and triggering conditions TC-01…TC-33 ([WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md)), functional modifications FM-01…FM-11 ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)), ODD parts ODD-H and ODD-A ([WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md)), controllability assumptions CA-01…CA-07 and DM performance DMP-01…DMP-04 ([WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)). [WP-C-05 §5.2](../02-concept/WP-C-05-sotif-hazard-identification.md#52-derivation-method-for-validation-targets-to-be-applied-in-wp-v-02) delegates the numeric targets to this document; §3 applies that method.

## 2. Acceptance criteria (input)

| Baseline | Use | Source (to be confirmed, [WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-1, OI-2) |
|---|---|---|
| B1 human driver | Rate-level targets (per distance / per hour) | US crash, injury and fatality rates (NHTSA FARS, CRSS) filtered to the ODD road types |
| B2 stock TSS2 | Scenario-level comparison: LD-SDA shall not perform worse than the same Corolla with stock Lane Tracing Assist / Dynamic Radar Cruise Control in any validated scenario | Comparative closed-course tests on the reference vehicle |

The acceptance criteria are those of [WP-C-05 §5](../02-concept/WP-C-05-sotif-hazard-identification.md#5-acceptance-criteria): (1) per SH group, the rate of harm while engaged shall not exceed the human-driver rate for comparable conditions reduced by a factor for the stock-TSS2 baseline; (2) the qualitative criteria AC-01…AC-07. This document adds the B2 scenario comparison (VT-09).

## 3. Method for deriving validation targets

For each SOTIF hazardous behaviour SH-nn:

1. **Harm budget.** Allocate to each SH group of WP-C-05 §5.2 step 3 (lateral SH-01/02/10; longitudinal SH-03/04/06/11; mode and override SH-05/09; SH-08) a share `k` of the road-class-specific B1 harm rate `λ_B1` for the relevant harm class (injury crash or fatality), separately for ODD-H and ODD-A:  `λ_harm,SH ≤ k · λ_B1`.
2. **Hazardous-behaviour rate.** Divide by the probability that the hazardous behaviour, once it occurs, leads to harm: `P(harm | HB) = P(E-situation) · P(not controlled) · P(severity class)`. Each factor needs evidence: P(E-situation) from LionDriver drive logs (§3.4), P(not controlled) from the controllability tests in [WP-V-01](WP-V-01-safety-validation.md) (§3.3), and P(severity class) from crash statistics (§3.5). A factor without evidence is set to 1.
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

### 3.3 Evidence for P(not controlled)

Step 2 takes P(not controlled) only from driver controllability tests with test subjects. It is never taken from the HARA controllability class or from literature. The rule:

1. **Source.** Each SH group uses the subject test that reproduces its worst envelope-bounded hazardous behaviour:

   | SH | Controllability test | Parent |
   |---|---|---|
   | SH-01 | [WP-V-01](WP-V-01-safety-validation.md) VS-VAL-10 | CA-01 |
   | SH-02 | WP-V-01 VS-VAL-12 | CA-02 |
   | SH-03 | WP-V-01 VS-VAL-13 | CA-03 |
   | SH-04 | WP-V-01 VS-VAL-14 | CA-04 |
   | SH-06 | WP-V-01 VS-VAL-16 | CA-03 |
   | SH-10 | [WP-V-03](WP-V-03-sotif-known-scenarios.md) KS-14 abort trials (VT-13) | CA-01 logic |
   | SH-05, SH-08, SH-09, SH-11, SH-12, SH-13 | none | P(not controlled) = 1 |

2. **Value.** P(not controlled) is the one-sided 95 % upper confidence bound on the share of valid subjects who did not control the event, taken at the least favourable tested condition (speed, direction, hands-on or hands-off). With n valid subjects and no failure, the bound is `1 − 0.05^(1/n)`. With failures, it is the Clopper–Pearson bound. The point estimate is not used.
3. **Range.** The value applies only up to the highest speed tested. For the part of the ODD above it, P(not controlled) = 1. VS-VAL-10 runs up to 90 km/h, and 110 km/h only after a separate risk review, while ODD-H extends to 120 km/h ([WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md)).
4. **Validity.** The value holds for the release whose envelope limits and alert timing were tested. A change to either needs a re-run, or a recorded argument that the tested behaviour bounds the new one, in the impact analysis ([WP-P-02](../07-supporting/WP-P-02-change-management.md)).

What this gives: 20 valid subjects with no failure bound P(not controlled) at 0.14, not the 0.1 assumed in case D of §3.1. Reaching 0.1 needs at least 29 subjects with no failure, and 0.01 needs 299. The sample size per condition is agreed with the assessor together with the controllability pass criteria ([WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) OI-3).

### 3.4 Evidence for P(E-situation)

P(E-situation) is the probability that, when the hazardous behaviour occurs, a situation in which it can cause harm is present. Step 2 takes it only from LionDriver's own drive logs. It is never taken from the HARA exposure class: E4 only says "> 10 %", and it is a share of all driving time, not of the moments when the hazardous behaviour occurs. The rule:

1. **Situation.** Each SH group uses the operational situation of the [HARA](../02-concept/WP-C-03-hara.md) in which its hazardous behaviour leads to harm, measured from log signals:

   | SH | Harm-enabling situation (HARA) | Measured as | Signal |
   |---|---|---|---|
   | SH-01, SH-02 | Vehicle or barrier on the departure side (OS-01, OS-02); oncoming lane on that side in ODD-A (OS-03) | A vehicle in the adjacent lane within ±2 s longitudinally, a barrier or an undivided road edge on either side | `radarTracks` (lateral position) where the reference radar provides tracks; otherwise offline annotation of `fcamera`. Road type and barrier from the DSR-03 tags |
   | SH-03 | Lead vehicle at a short gap (OS-05) | Lead in the ego lane within a 3 s time gap | `radarState.leadOne` |
   | SH-06 | Approaching slower or stationary traffic (OS-07) | Lead closing within the AIR-03 range (80 m) | `radarState.leadOne` (distance, relative speed) |
   | SH-04 | Close following vehicle behind (OS-08) | Following vehicle within a 1.5 s time gap | None on the device: offline annotation of the rear-facing camera of the test vehicle ([WP-V-01](WP-V-01-safety-validation.md) §2 equipment). Until it is fitted (OI-7), P(E-situation) = 1 |
   | SH-10 | Vehicle in the target lane (OS-01) | Vehicle in the target lane within ±2 s during a lane change | As SH-01, on instances where `modelV2.meta.laneChangeState` is active |
   | SH-05, SH-08, SH-09, SH-11, SH-12, SH-13 | — | not measured | P(E-situation) = 1 |

2. **Unit and value.** The unit is the 60 s engaged instance of §4.3. An instance counts as exposed if the situation is present at any time in it, which is conservative. P(E-situation) is the one-sided 95 % upper confidence bound (Clopper–Pearson) on the share of exposed instances. It is computed per ODD stratum (DSR-03), and the least favourable stratum of the claimed ODD is used unless the target is set per stratum.
3. **Matched to the triggering condition.** The hazardous behaviour and the situation can be correlated: phantom braking happens at overpasses, and drift happens in curves. So the share is measured on instances that carry a triggering condition of the SH ([WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) TC tag, or a [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) signature) wherever at least 59 such instances exist. Below that, the ODD-wide share may be used only with a recorded argument that the situation is independent of the triggering condition; otherwise P(E-situation) = 1.
4. **Data and validity.** The data comes from engaged public-road blocks (WP-V-04 B1–B3, public-road level L5 of [WP-V-07](WP-V-07-vehicle-test-operations.md)). Exposure is recorded as in [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) §2.2. The value is re-measured on field data after release (WP-O-04). A field share above the bound used here re-opens step 2 for that SH.
5. **HARA.** The same measurements confirm or correct the HARA exposure classes of the situations above (HARA OI-2). A measured time share below 10 % for an E4 situation is reported to the HARA owner.

What this gives: the HARA rates every one of these situations E3 or E4, so P(E-situation) is expected to be between about 0.1 and 1. At best it earns one order of magnitude in step 2, and only with enough matched instances. For SH-04 it earns nothing until the rear camera exists.

### 3.5 Evidence for P(severity class)

P(severity class) is the probability that a collision caused by the uncontrolled hazardous behaviour reaches the harm class budgeted in step 1 (injury crash or fatality). The rule:

1. **Same definition as the budget.** The harm class and its definition are those of λ_B1 in step 1. If the budget is fatalities from FARS, P(severity class) is P(fatality | collision). If the budget is injury crashes from CRSS, it is P(police-reported injury | collision). A ratio from a source with another injury definition (for example MAIS3+) is not combined with that budget.
2. **Collision type and impact speed per SH.** Each SH group uses the collision of its HARA hazardous events, at the worst credible impact speed in the claimed ODD. Because the factor applies after P(not controlled), no braking or steering by the driver is credited before impact:

   | SH | Collision (HARA) | Worst credible impact |
   |---|---|---|
   | SH-01, SH-02 | Sideswipe or barrier impact at 90–120 km/h (HE-01.2, HE-02.1); head-on in ODD-A at combined speeds > 100 km/h (HE-01.1, HE-02.2) | Travel speed; closing speed for head-on |
   | SH-03 | Rear-end into the lead: moderate speed difference (HE-03.1), high closing speed (HE-03.3) | Speed difference reached with the envelope's +2.0 m/s² from the OS-05 / OS-07 gap |
   | SH-04 | Struck from behind (HE-04.1) | Speed loss at the envelope's −3.5 m/s² before the follower reacts |
   | SH-06 | Rear-end into slow or stationary traffic (HE-06.1, HE-06.3) | Full closing speed, up to the ODD speed bound for a stationary lead |
   | SH-10 | Sideswipe in the target lane (HE-02.5) | Lateral contact at travel speed |
   | SH-11 | VRU impact, ODD-A only (HE-01.3, HE-03.2) | Travel speed |
   | SH-05, SH-08, SH-09, SH-12, SH-13 | — | P(severity class) = 1 |

3. **Source, in order of preference:**
   - **National ratio.** Use the ratio of FARS to CRSS counts for the same manner of collision (rear-end, sideswipe same direction, head-on, angle, pedestrian) and the ODD road class and speed-limit band. These are the databases λ_B1 is filtered from (§2). The one-sided 95 % upper bound is taken, using the CRSS standard errors. This applies only where the LD-SDA collision is argued to be no more severe than the average crash of that type and band.
   - **Injury-risk curve.** Where the LD-SDA collision is more severe than the average crash of its type (for example SH-06 with no braking before impact), use a published injury-risk curve for the collision type, read at the worst credible impact speed of item 2. The curve is from NHTSA crash-investigation data (NASS-CDS, CISS), or GIDAS for European data, with its harm definition matching item 1.
   - **Otherwise.** If neither source fits, P(severity class) = 1.
4. **Record.** For every value, record:
   - the database and its release year, the filters and the counts;
   - the curve and the impact speed used;
   - the upper bound.

   The values are part of the target set the assessor approves (OI-3).
5. **Consistency with the HARA.** A value that implies low severity for a hazardous event rated S3 is reported to the HARA owner and explained before it is used.

What this gives: for the S2 collisions (sideswipe; rear impacts at moderate speed difference, struck from behind), fatal crashes are well under 1 % of police-reported crashes of these types, so the factor can earn about two orders of magnitude for a fatality budget. For an injury-crash budget it earns little. For the S3 collisions at highway speed (head-on, high-speed rear-end into stationary traffic, barrier impact), the factor is close to 1 for either budget. Their targets therefore rest on P(E-situation) and P(not controlled), or on narrowing the ODD. No value has been extracted yet (OI-8).

## 4. Validation targets

Targets are **proposals**: numeric values are placeholders for the assessor review and WP-C-05 acceptance criteria (OI-3). "Demonstration" names the primary method; §5 defines the methods.

| ID | SH | Quantity | Proposed target | Derivation | Demonstration | Achievable? |
|---|---|---|---|---|---|---|
| VT-01 | SH-01 excessive / wrong lateral motion | Unrequested lane departures (AIR-02) per engaged hour | Rate-level: ≤ 5 × 10⁻⁶ /mi (case D). Scenario-level: p_s ≤ 1 % per scenario in KS-01…KS-06, KS-14 at 95 % | §3 steps 1–5; P(not controlled) per §3.3 (VS-VAL-10) | Scenario-level by SIM + CC + REPLAY; rate-level surrogate on public road | Scenario-level yes; rate-level no (reported as surrogate with upper bound) |
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
| VT-14 | SH-01, SH-04 plan stability (AIR-11) | Steady-scene instances in which the model output asks for more than the controller passes: `modelV2.action.desiredCurvature` changes faster than the jerk bound 5 m/s³ / v² (`MAX_LATERAL_JERK`, `selfdrive/controls/lib/drive_helpers.py:13, 29-31`; FSR-01.14), or the lead existence (`prob` crossing 0.5) toggles more than once in any 1 s window for a continuously visible lead | p_s ≤ 1 % per steady-scene instance at 95 % (≥ 299 instances per ODD stratum): straight and constant-curvature segments of KS-01…KS-06 for curvature; KS-07, KS-08, KS-10, KS-11 for lead toggling | §4.2; same p_max as VT-01 | REPLAY (VS-ML-07) on evaluation data; CC for the lead scenarios | Yes |
| VT-15 | SH-01, SH-04, SH-06, SH-13 runtime monitor (AIR-14) | (a) Recall: share of instances in which the model alone fails (hazardous behaviour or AIR violation) that the monitor flags before the failure; (b) false flags per hour of nominal ODD driving | (a) ≥ 80 % per KS of the known-triggering-condition set (KS-12, KS-13, KS-16) at 95 %: ≥ 14 failing instances with no miss, or the Clopper–Pearson bound. A TC whose model-alone failure rate exceeds the §4.2 limit needs higher recall or an ODD restriction. (b) ≤ 1 false flag per hour at 95 % (χ² bound of §3 step 3), on drives disjoint from tuning data (DSR-11) | §4.2; nuisance budget equal to AIR-08 | REPLAY with KS segments; PR for false flags | Yes, after AIR-14 is implemented (GAP-22) |

SH-09 (traffic-control non-compliance) has no target: Experimental Mode is off and locked (FM-01) and KS-24 verifies the exclusion. SH-11 (no VRU response) has no rate target: [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) resolves TC-12 by ODD restriction and user information; KS-22 and KS-23 only verify that the item does not move toward a VRU it cannot see.

### 4.2 Derivation of VT-14 and VT-15

**VT-14.** The SoC controller limits the commanded curvature rate to 5 m/s³ / v² (`clip_curvature`) and lateral acceleration to 3.0 m/s² (FSR-01.14). A model output that exceeds that rate in a steady scene is therefore cut by the controller, so the vehicle does not follow it. That makes it a sign of an unstable plan rather than a hazard in itself: repeated cuts, or a lead that appears and disappears, are what precede SH-01 (wrong lateral motion) and SH-04 (phantom braking). The target therefore counts scenario instances with any exceedance and gives them the same budget as VT-01: p_s ≤ 1 %. The thresholds are those of AIR-11.

**VT-15.** A flag from the monitor turns a model failure into a take-over alert. The residual per instance of a triggering condition is then

`p_s,res = p_s,model · [(1 − r) + r · P(not controlled | alert)]`

where r is the monitor recall and P(not controlled | alert) is taken from the take-over test VS-VAL-12 under §3.3. With r = 0.8 and P(not controlled) = 0.14 (20 subjects, no failure), p_s,res ≤ 1 % holds only if the model alone fails in at most 3.2 % of instances. A triggering condition with a higher model-alone failure rate needs higher recall, a larger subject sample, or removal from the ODD (WP-C-02 §3.3). The 80 % recall in VT-15 is therefore a floor, and the per-condition recall follows from this formula once p_s,model is measured. Each false flag raises a take-over alert, so false flags are capped with the same nuisance budget the DM chain has (AIR-08: ≤ 1 false alert per hour). Together, nominal driving can produce at most two unnecessary alerts per hour.

### 4.3 Derivation of the AIR-01, AIR-03 and AIR-04 values

**AIR-01 (lateral offset).** The lateral margin from lane centre to the lane boundary is (lane width − vehicle width)/2. With the ODD lane widths of 2.9–3.9 m and the Corolla at ≈ 1.78 m, it is 0.56–1.06 m ([WP-S-04 §3.1](../03-system/WP-S-04-timing-ftti-budget.md)). An offset within ±0.5 m therefore stays inside the lane in every ODD lane width, with at least 0.06 m to spare in the narrowest. This is also the drift threshold of VT-02. The ±0.5 m value is confirmed.

The time share (≥ 99.5 % of engaged time) cannot be derived from VT-01. VT-01 counts departures per scenario instance, and a time share depends on how long each excursion lasts. The time share is therefore **replaced** by an instance criterion with the VT-01 budget:

- **Pass condition:** |offset| stays ≤ 0.5 m throughout a 60 s nominal lane-keeping instance.
- **Target:** the share of failing instances is p ≤ 1 % at 95 %, which needs ≥ 299 instances (≈ 5 h) per ODD stratum.
- **Instance length:** 60 s keeps that sample within the public-road capacity of §3.2, and is long enough to include curvature changes.

The time share is still reported, as a KPI without a pass value.

**AIR-03 (lead detection).** All three values follow from the longitudinal plan and the envelope:

- **Range 80 m.** At the ODD speed bound (120 km/h, 33.3 m/s), the planner follows a lead at t_follow · v + 6 m. That is 54 m with the standard personality and 64 m with the relaxed one (`selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py`: T_FOLLOW 1.45 / 1.75 s, STOP_DISTANCE 6 m). 80 m covers both gaps, with the 10 % distance error added.
  For a lead closing at Δv, the distance needed to react and brake is Δv · t_r + Δv² / (2 · a_lim), using t_r and a_lim from AIR-04. With 80 m, this covers closing speeds up to 19 m/s (≈ 69 km/h). Faster closing (stationary or much slower leads) is covered by AIR-04, applied with the closing speed in place of v.
- **Latency 0.5 s.** This is half of the AIR-04 reaction time t_r = 1.0 s. The other half is for planning (20 Hz), control and the PCM's response onset. VS-VAL-08 of [WP-V-01](WP-V-01-safety-validation.md) measures this share: the time from the plan to the `ACC_CONTROL` frame and from the frame to the onset of the vehicle's response. Until it has run, the 0.5 s is an assumption. VS-VAL-08 is an entry criterion for public-road level L5 ([WP-V-07](WP-V-07-vehicle-test-operations.md) §4), so engaged public-road driving does not start on the assumption. If the worst measured value is larger, t_r and this latency are re-derived before L5.
- **Distance error max(2 m, 10 %).** The plan brakes at a_lim = 3.0 m/s². If the lead is ε closer than reported, the deceleration actually needed is a_lim · (1 + ε). With ε = 10 % that is 3.3 m/s², inside the envelope minimum of −3.5 m/s² (`ACCEL_MIN`, [WP-C-02 §2](../02-concept/WP-C-02-odd-and-intended-functionality.md)). The limit would be ε ≤ 16.7 %. At short range, the 2 m floor leaves 4 m of the 6 m standstill gap.

**AIR-04 (stationary lead).**

- **a_lim = 3.0 m/s².** This sits between the planner's comfort braking (COMFORT_BRAKE 2.5 m/s²) and the envelope minimum (3.5 m/s²). The 0.5 m/s² left before the envelope minimum covers the AIR-03 distance error above.
- **t_r = 1.0 s.** This is the AIR-03 detection latency (0.5 s) plus the planning-to-actuation share (0.5 s), as above.

At the ODD speed bound, the required report distance is 33.3 + 33.3² / 6 ≈ 218 m. The 180 m given as an example in AIR-04 is for 30 m/s. Both values are confirmed. They remain proposals until the assessor approves them (OI-3).

### 4.1 (TBC) values of WP-C-11 and the targets that confirm them

[WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) marks the performance values of its AI safety requirements **(TBC)**. Its OI-2 says each is to be confirmed or replaced through the target derivation here. The table records, for each (TBC) value, which target confirms it. **Kind** is one of:

- **C:** a target here states the same value.
- **D:** a target here covers the quantity, but the value is not yet derived from it.
- **G:** a SOTIF target should cover it, and none does.
- **N:** the value does not come from a SOTIF target; the source document is named.

| Requirement | (TBC) value | Target | Kind | Action |
|---|---|---|---|---|
| AIR-01 | Lateral offset ±0.5 m | VT-02 (drift > 0.5 m) | C | — |
| AIR-01 | ≥ 99.5 % of engaged time within ±0.5 m | VT-01 (instance budget p ≤ 1 %) | C | Replaced by the instance criterion of §4.3; the time share is reported as a KPI |
| AIR-03 | Lead detection range 80 m, latency 0.5 s, distance error max(2 m, 10 %) | VT-06 (p_s per approach-speed band) | C | Derived in §4.3 |
| AIR-04 | t_r = 1.0 s, a_lim = 3.0 m/s² | VT-06 (KS-05) | C | Derived in §4.3 |
| AIR-05 | Phantom deceleration below −2.0 m/s² | VT-04 (−2.0 m/s²) | C | — |
| AIR-06 | `hardBrakePredicted` at TTC ≥ 2.0 s | VT-06 (FCW at TTC ≥ 2 s) | C | — |
| AIR-11 | Curvature rate from 5 m/s³ jerk; ≤ 1 lead toggle per second | VT-14 (field surrogate AS-08 in [WP-V-04](WP-V-04-sotif-unknown-scenarios.md)) | C | — |
| AIR-14 | Monitor recall ≥ 80 % on known triggering conditions; ≤ 1 false flag per hour | VT-15 (KS-12, KS-13, KS-16 of [WP-V-03](WP-V-03-sotif-known-scenarios.md)) | C | Per-condition recall may need to be higher (§4.2) |
| AIR-10 | Partial lens occlusion ≤ 10 % | — | N | Input-space bound of WP-C-11 §3, verified by VS-ML-04 ([WP-W-10](../05-software/WP-W-10-ml-engineering.md)) |
| AIR-13 | 90–98 % of samples within ±2σ | — | N | Calibration criterion of WP-W-10 (VS-ML-05); enables AIR-14 |
| AIR-12, AIR-26 | 2 s warm-up before use or engagement | — | N | Timing; [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) |
| AIR-17 | Inference ≤ 50 ms, output age ≤ 100 ms | — | N | Timing; WP-S-04, TSR-602, TSR-616 |
| AIR-27 | DM output invalid > 2 s | — | N | TSR-609 ([WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md)); fault injection VS-FI-25 |
| DSR-07 | ≥ 10 % double annotation | — | N | Label specification (WP-W-10) |

Result: eight values are confirmed or replaced (C). AIR-11 and AIR-14 are confirmed through VT-14 and VT-15, and AIR-01, AIR-03 and AIR-04 through the derivation of §4.3. No value is left at D or G. The remaining six take their value from timing, ML engineering or data documents, not from this one (N). Until then, every (TBC) in WP-C-11 stays (TBC).

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
| TC-32 | Narrow lane next to large vehicle / barrier | KS-06 | | ● | | | | ● |
| TC-33 | Lead braking beyond the deceleration bound | KS-08 | | ○ | | ● | ● | |

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
| OI-3 | Approve numeric targets VT-01…VT-15 with the assessor before collecting evidence, together with the derivations of §4.2 and §4.3 |
| OI-4 | Build the simulation fidelity case (§5.3) and decide which families get credit (WP-M-08 OI-3) |
| OI-5 | Define the surrogate-to-harm argument for VT-04 and the takeover-based surrogates (WP-M-08 OI-8) |
| OI-7 | Fit the rear-facing camera now listed in the [WP-V-01](WP-V-01-safety-validation.md) §2 equipment (procurement: WP-V-01 OI-6), and annotate following vehicles from its recordings, so that P(E-situation) for SH-04 (following vehicle, OS-08) is measured (§3.4). Blocks driven before it is fitted give no SH-04 data |
| OI-8 | Extract P(severity class) per SH from FARS/CRSS (and injury-risk curves where §3.5 item 3 requires them) for the selected B1 data set (OI-2); record the values and bounds per §3.5 item 4 |
