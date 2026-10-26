# WP-V-02 SOTIF Verification and Validation Strategy

| Field | Value |
|---|---|
| Work product | WP-V-02 SOTIF verification and validation strategy, validation targets |
| Standard reference | ISO 21448:2022 §9 (V&V strategy, validation targets), Annex C (informative, validation target derivation); ISO/PAS 8800:2024 (AI V&V); ASPICE 4.0 VAL.1 |
| Version | 0.15 (the lead's decisions applied: §2.1 B1 data set, NHTSA FARS and CRSS over FHWA travel data, Interstate against other arterials, with its limits, DQ-137 A; §2.2 B2 by paired closed-course runs, DQ-138 A; §4.5 surrogates for harm, three with draft arguments not yet checked against logs, DQ-140 A; OI-2 and OI-5 rewritten; VT-01…VT-15 keep their illustrative values and the freeze (OI-3) stays open; 2026-10-25). 0.14 (§3 step 1: the 10 % reserve for unknown scenarios is fixed by the R3 threshold the project lead approved, P̂₀ ≤ 0.10 with N ≥ 30, DQ-262 A; 2026-10-19). 0.13 (§5.3.2: KS-27 in family SF-3, with occlusion by the curve as a fidelity concern; 2026-10-19). 0.12 (§6: TC-35, lead detected late in a curve while accelerating, covered by KS-27; inputs TC-01…TC-35; 2026-10-19). 0.11 (targets are frozen by the project lead in a dated record once the B1 crash data replaces the illustrative rates, with a later assessor review, DQ-096 B; no SOTIF campaign counts before; §3 step 1 holds back a 10 % reserve for unknown scenarios, proposed with WP-V-04 R3, DQ-108; 2026-10-19). 0.10 (§3 step 3: confidence level C = 95 % one-sided for every target and for release criterion R-08, DQ-057 A; 2026-10-19). 0.9 (§6: TC-34, stock PCS interaction, covered by KS-20; inputs FI-01…FI-23 and TC-01…TC-34; 2026-10-18). 0.8 (§4.4: the rule is implemented in `policy.py` (SWSR-634); its unit tests run the check (a) speed profiles; 2026-10-17). 0.7 (§4.4 added: validation of the speed-dependent wheel-touch reminder timing, TSR-634 (DQ-077 A); VT-08 covers DMP-05; 2026-10-17). 0.6 (the lead's decisions: simulation credit per scenario family once its fidelity case is approved, DQ-139; CARLA not now, revisit at G3, DQ-261; §5.3, §5.4, OI-4; 2026-10-16). 0.5.1 (§5.3.1 simulator status brought up to date by the simulation session at the SOTIF session's request: bridge PR #124, scenario files, plant model; no plan or target changed; 2026-10-16). 0.5 (ODD speed bound 110 km/h, decision register DQ-260: §3.3, §3.4, §4; 2026-10-16). 0.4 (§5.3 fidelity-case plan written: scenario families, fidelity elements, comparison, synthetic-data labelling for DSR-12; §5.4 CARLA assessed, decision queued as DQ-261; 2026-10-16). 0.3 (the lead's decisions applied: highways only, decision register DQ-023; controllability tested to 110 km/h, DQ-091; controllability pass limits fixed before testing, DQ-042; public-road limits, DQ-046; no uploads to comma, DQ-084; 2026-10-16). 0.2 (Figure 4-1 added, generated from §3.1, §3.2 and §4; 2026-10-13). 0.1 |
| Status | Draft |
| ASIL / scope | SOTIF |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); validation targets frozen by the project lead (DQ-096 B) and reviewed later by an external assessor (D-06, [WP-M-08 §10](../01-management/WP-M-08-sotif-plan.md)) |
| Approver | Project maintainer (acting safety manager, SOTIF lead) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

This document turns the acceptance-criteria approach of the [SOTIF plan (WP-M-08 §5)](../01-management/WP-M-08-sotif-plan.md#5-acceptance-criteria-approach) into validation targets (VT-nn), shows how each target could be demonstrated, and states plainly which targets cannot be demonstrated by LionDriver driving alone. It selects the verification and validation methods for known hazardous scenarios ([WP-V-03](WP-V-03-sotif-known-scenarios.md)) and unknown hazardous scenarios ([WP-V-04](WP-V-04-sotif-unknown-scenarios.md)), and the evidence each method can and cannot provide.

Scope: reference configuration of [WP-M-01 §3.1](../01-management/WP-M-01-assurance-strategy.md#31-reference-configuration-the-only-scope-claims-apply-to), Chill longitudinal mode, AI-1 driving model, AI-3 DM model. Experimental Mode and the Chestnut big model are outside the claim (D-08, AIR-29, AIR-30) and are not validated here.

Sequencing rule ([WP-M-08 §4.1](../01-management/WP-M-08-sotif-plan.md#41-sequencing-rules)): the targets in §4 are fixed and approved **before** evidence for them is collected.

Inputs: SOTIF hazards SH-01…SH-13 and acceptance criteria ([WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md) §3, §5), functional insufficiencies FI-01…FI-23 and triggering conditions TC-01…TC-35 ([WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md)), functional modifications FM-01…FM-11 ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)), ODD part ODD-H ([WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md); highways only since 2026-10-14, decision register DQ-023 option B, so the ODD-A values kept below set no target), controllability assumptions CA-01…CA-07 and DM performance DMP-01…DMP-04 ([WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md)). [WP-C-05 §5.2](../02-concept/WP-C-05-sotif-hazard-identification.md#52-derivation-method-for-validation-targets-to-be-applied-in-wp-v-02) delegates the numeric targets to this document; §3 applies that method.

## 2. Acceptance criteria (input)

| Baseline | Use | Source ([WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-1, OI-2, closed 2026-10-25) |
|---|---|---|
| B1 human driver | Rate-level targets (per distance / per hour) | NHTSA FARS and CRSS crashes over FHWA travel data, split Interstate against other arterials (§2.1, DQ-137 A) |
| B2 stock TSS2 | Scenario-level comparison: LD-SDA shall not perform worse than the same Corolla with stock Lane Tracing Assist / Dynamic Radar Cruise Control in any validated scenario | Paired closed-course runs from the WP-V-03 known scenarios (§2.2, DQ-138 A) |

The acceptance criteria are those of [WP-C-05 §5](../02-concept/WP-C-05-sotif-hazard-identification.md#5-acceptance-criteria): (1) per SH group, the rate of harm while engaged shall not exceed the human-driver rate for comparable conditions reduced by a factor for the stock-TSS2 baseline; (2) the qualitative criteria AC-01…AC-07. This document adds the B2 scenario comparison (VT-09).

### 2.1 B1 human-driver data set (DQ-137)

Decided 2026-10-25 by the project lead (decision register DQ-137 option A). No rate has been extracted yet (OI-2). Until then, §3.1 and VT-01…VT-15 keep their illustrative values.

| Item | Choice |
|---|---|
| Crashes | NHTSA FARS (every fatal crash, a census) and CRSS (police-reported crashes of every severity, a weighted sample with standard errors) |
| Travel | FHWA travel data: vehicle-miles per year by functional class (Highway Statistics). The table and its edition are recorded at extraction |
| Year | One data year for all three sources, the latest with a final FARS file. Recorded at extraction. Other years only show the trend |
| Road-class filter | Interstate against other arterials. The Interstate rate sets the targets for ODD-H. ODD-H also includes other limited-access freeways and expressways (WP-C-02 §3.1), which fall in the other-arterial group; their rate is reported on its own where the files allow, and if it is lower, the freeze (OI-3) decides whether a target uses it. The other arterials are outside ODD-H: their rate sets no target and informs the out-of-ODD residual (SH-13) in WP-K-02 |
| Harm classes | Fatal crashes (FARS) and police-reported injury crashes (CRSS), per 10⁸ vehicle-miles. These are the harm classes of §3 step 1 and §3.5 item 1 |
| Bound | The CRSS standard errors give the one-sided 95 % bounds (§3 step 3). FARS is a census and needs none for its count |
| Recorded per value | Source and release, data year, the filter variables and codes, the counts, the travel figure, the rate and its bound. The road-class variables of each file are checked against the NHTSA manual of the release year first, as for OI-8. Where a file cannot split a class, that is recorded |

Known limits:

- **Minor crashes are undercounted.** Police-reported crashes miss many minor ones, so the CRSS injury-crash rate is lower than the true human rate. LionDriver's own events are counted in full from logs. The comparison therefore errs on the strict side. The FARS fatal rate is not affected.
- **The human car's assistance is unknown.** The data do not say whether the human-driven car had LKA or ACC. B1 is human driving in the mixed US fleet, not the stock TSS2 Corolla. No adjustment for stock LKA, ACC or PCS is derived from these data (that was option B, not chosen). The stock-TSS2 comparison is made scenario by scenario instead (B2, §2.2). The factor of [WP-C-05 §5.1](../02-concept/WP-C-05-sotif-hazard-identification.md#51-approach) item 1 therefore gets no value from B1. Whether the rate criterion carries a fixed factor is settled with the target freeze (OI-3).
- **Class, not ODD.** An Interstate rate includes conditions outside the ODD (snow, fog, work zones, night in some stretches). It is not filtered further unless a file supports it; any filter used is recorded.

### 2.2 B2 paired runs against stock TSS2 (DQ-138)

Decided 2026-10-25 by the project lead (decision register DQ-138 option A). Nothing has been run.

1. **Pairs.** Each selected known scenario of [WP-V-03](WP-V-03-sotif-known-scenarios.md) is driven twice at each parameter point: once with the stock TSS2 functions (Lane Tracing Assist, Dynamic Radar Cruise Control) and once with LD-SDA. Same course, speeds and targets. WP-V-03 §2 lists the scenarios that get a paired run, and why the others do not.
2. **Logging.** Both arms are logged on the device. In the stock arm the item is installed but passive, so the device still logs while the stock path acts. That passive mode leaves the stock camera and PCS path intact is still to be confirmed ([WP-V-07](WP-V-07-vehicle-test-operations.md) OI-3). How the arms are switched, and the time per swap, is WP-V-03 OI-4.
3. **Runs.** Several runs per arm at each point. The count follows the WP-V-03 trial-count rule and is approved with the targets (OI-3).
4. **Comparison (proposed, approved with the targets, OI-3).** At each point, LD-SDA has no more failures than stock against the scenario's pass criterion, and its scenario metric (WP-V-03 §2, B2 row) is not worse than stock beyond the spread between runs of the stock arm.
5. **Needs.** A closed-course site, soft targets for stopped and cut-in vehicles, and several runs per pair ([WP-V-07](WP-V-07-vehicle-test-operations.md) §8.1.1). Which site is a separate question still queued for the project lead (DQ-041).
6. **Limits.** Closed-course points stop at 90 km/h, or 110 km/h after the risk review (DQ-091 A). Above that, B2 has no evidence. Matched public-road segments were not chosen (option B), so public-road driving gives no B2 credit.

## 3. Method for deriving validation targets

For each SOTIF hazardous behaviour SH-nn:

1. **Harm budget.** Allocate to each SH group of WP-C-05 §5.2 step 3 (lateral SH-01/02/10; longitudinal SH-03/04/06/11; mode and override SH-05/09; SH-08) a share `k` of the road-class-specific B1 harm rate `λ_B1` for the relevant harm class (injury crash or fatality), for ODD-H (ODD-A is no longer claimed, DQ-023):  `λ_harm,SH ≤ k · λ_B1`. The targets use 90 % of each group's share. The other 10 % is a reserve for scenarios not yet known, which the stop rule R3 of [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) §5.4 checks: at most 10 % of hazardous events expected from unseen classes (P̂₀ ≤ 0.10, N ≥ 30). The project lead approved the value on 2026-10-19 (decision register DQ-108 A, DQ-262 A).
2. **Hazardous-behaviour rate.** Divide by the probability that the hazardous behaviour, once it occurs, leads to harm: `P(harm | HB) = P(E-situation) · P(not controlled) · P(severity class)`. Each factor needs evidence: P(E-situation) from LionDriver drive logs (§3.4), P(not controlled) from the controllability tests in [WP-V-01](WP-V-01-safety-validation.md) (§3.3), and P(severity class) from crash statistics (§3.5). A factor without evidence is set to 1. Some SHs cause harm in more than one situation s with different severity, such as SH-03 following (OS-05) and approaching (OS-07). For those, the probability is summed over the situations: `P(harm | HB) = Σ_s P(E_s) · P(not controlled)_s · P(severity class)_s`.
   `λ_HB,SH ≤ k · λ_B1 / P(harm | HB)`
3. **Demonstration size.** For a zero-failure demonstration at confidence C, the exposure needed is
   `n = −ln(1 − C) / λ_HB`
   (exponential/Poisson model; with r observed failures, use the χ² bound `n = χ²(C; 2r + 2) / (2 λ)`).

   **Confidence level:** C = 95 %, one-sided, for every SOTIF validation target and for release criterion R-08 of [WP-K-02](../10-safety-case/WP-K-02-sotif-release-argument.md) (decided 2026-10-19 by the project lead, decision register DQ-057 option A). Rates use the zero-failure or χ² bound above, `n ≈ 3 / λ` with no failure. Shares per scenario class use the zero-failure or Clopper–Pearson bound, as §3.3 and §3.4 already do. The C = 99 % column of §3.1 shows the cost of the stricter level only.
4. **Feasibility check.** Compare n with LionDriver's achievable exposure (§3.2). If n is out of reach, decompose (step 5) and narrow the ODD ([WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)).
5. **Scenario decomposition.** `λ_HB = Σ_s ε_s · p_s`, where ε_s is the exposure rate of scenario class s (occurrences per km, estimated from LionDriver drive logs, which needs far less mileage than observing rare failures), and p_s is the probability of hazardous behaviour given s (estimated per scenario by simulation, replay and closed-course trials). Per-scenario targets p_s,max are set so that the sum meets λ_HB. A zero-failure demonstration of `p_s ≤ p_max` at confidence C needs `N = ln(1 − C) / ln(1 − p_max)` trials (≈ 3 / p_max at C = 95 %).

### 3.1 Illustration of magnitudes

The figures below are **illustrative orders of magnitude** to show feasibility; the baseline values must be replaced by the data set of §2.1 once its rates are extracted (OI-2). Average engaged speed is assumed to be 64 km/h (40 mph) to convert distance to time. `−ln(1 − 0.95) ≈ 3.0`; `−ln(1 − 0.99) ≈ 4.6`.

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
| Public-road driving with safety driver (WP-V-07; engaged at ≤ 105 km/h, DQ-046) | 10⁴ – 2 × 10⁴ km engaged (≈ 150–300 h) | Exposure estimates ε_s for common scenarios; surrogate rates (§4.5: unrequested lane departures, envelope limit hits, take-overs with a short time to the line); **no** rate-level demonstration of cases A–D |
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
3. **Range.** The value applies only up to the highest speed tested. For the part of the ODD above it, P(not controlled) = 1. VS-VAL-10 runs up to 90 km/h, and to 110 km/h after a separate risk review, which the project lead decided to hold (decision register DQ-091 option A, 2026-10-14). The project lead capped ODD-H at that tested speed, 110 km/h (decision register DQ-260 option A, 2026-10-16), so the tested range covers the whole ODD once VS-VAL-10 has run at 110 km/h. Until then, P(not controlled) = 1 above 90 km/h.
4. **Validity.** The value holds for the release whose envelope limits and alert timing were tested. A change to either needs a re-run, or a recorded argument that the tested behaviour bounds the new one, in the impact analysis ([WP-P-02](../07-supporting/WP-P-02-change-management.md)).

What this gives: 20 valid subjects with no failure bound P(not controlled) at 0.14, not the 0.1 assumed in case D of §3.1. Reaching 0.1 needs at least 29 subjects with no failure, and 0.01 needs 299. The controllability pass criteria (override force of about 50 N, lateral margin) are fixed now from the concept drafts, before any subject test, and are not changed after testing starts (decision register DQ-042 option A, 2026-10-14; the values are recorded under [WP-V-01](WP-V-01-safety-validation.md) OI-3 and [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) OI-3). The sample size per condition is agreed with the assessor.

### 3.4 Evidence for P(E-situation)

P(E-situation) is the probability that, when the hazardous behaviour occurs, a situation in which it can cause harm is present. Step 2 takes it only from LionDriver's own drive logs. It is never taken from the HARA exposure class: E4 only says "> 10 %", and it is a share of all driving time, not of the moments when the hazardous behaviour occurs. The rule:

1. **Situation.** Each SH group uses the operational situation of the [HARA](../02-concept/WP-C-03-hara.md) in which its hazardous behaviour leads to harm, measured from log signals:

   | SH | Harm-enabling situation (HARA) | Measured as | Signal |
   |---|---|---|---|
   | SH-01, SH-02 | Vehicle or barrier on the departure side (OS-01, OS-02); oncoming lane on that side in ODD-A (OS-03) | A vehicle in the adjacent lane within ±2 s longitudinally, a barrier or an undivided road edge on either side | `radarTracks` (lateral position) where the reference radar provides tracks; otherwise offline annotation of `fcamera`. Road type and barrier from the DSR-03 tags |
   | SH-03 | Lead vehicle at a short gap (OS-05); approaching slower traffic (OS-07) | OS-05: lead in the ego lane within a 3 s time gap. OS-07: as SH-06. The two are measured and used separately (§3.5) | `radarState.leadOne` |
   | SH-06 | Approaching slower or stationary traffic (OS-07) | Lead closing within the AIR-03 range (80 m) | `radarState.leadOne` (distance, relative speed) |
   | SH-04 | Close following vehicle behind (OS-08) | Following vehicle within a 1.5 s time gap | None on the device: offline annotation of the rear-facing camera of the test vehicle ([WP-V-01](WP-V-01-safety-validation.md) §2 equipment). Until it is fitted (OI-7), P(E-situation) = 1 |
   | SH-10 | Vehicle in the target lane (OS-01) | Vehicle in the target lane within ±2 s during a lane change | As SH-01, on instances where `modelV2.meta.laneChangeState` is active |
   | SH-05, SH-08, SH-09, SH-11, SH-12, SH-13 | — | not measured | P(E-situation) = 1 |

2. **Unit and value.** The unit is the 60 s engaged instance of §4.3. An instance counts as exposed if the situation is present at any time in it, which is conservative. P(E-situation) is the one-sided 95 % upper confidence bound (Clopper–Pearson) on the share of exposed instances. It is computed per ODD stratum (DSR-03), and the least favourable stratum of the claimed ODD is used unless the target is set per stratum.
3. **Matched to the triggering condition.** The hazardous behaviour and the situation can be correlated: phantom braking happens at overpasses, and drift happens in curves. So the share is measured on instances that carry a triggering condition of the SH ([WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) TC tag, or a [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) signature) wherever at least 59 such instances exist. Below that, the ODD-wide share may be used only with a recorded argument that the situation is independent of the triggering condition; otherwise P(E-situation) = 1.
4. **Data and validity.** The data comes from engaged public-road blocks (WP-V-04 B1–B3, public-road level L5 of [WP-V-07](WP-V-07-vehicle-test-operations.md)). Engaged public-road driving is capped at 105 km/h (WP-V-07 limits adopted by the project lead, decision register DQ-046 option A), so the 105–110 km/h stratum is not observed: there the least favourable observed stratum is used with a recorded argument that the share does not grow with speed, or P(E-situation) = 1. The logs are kept in the LionDriver log store and are not uploaded to comma's servers (DQ-084 option A), which keeps them independent of comma's training data (DSR-05). Exposure is recorded as in [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) §2.2. The value is re-measured on field data after release (WP-O-04). A field share above the bound used here re-opens step 2 for that SH.
5. **HARA.** The same measurements confirm or correct the HARA exposure classes of the situations above (HARA OI-2). A measured time share below 10 % for an E4 situation is reported to the HARA owner.

What this gives: the HARA rates every one of these situations E3 or E4, so P(E-situation) is expected to be between about 0.1 and 1. At best it earns one order of magnitude in step 2, and only with enough matched instances. For SH-04 it earns nothing until the rear camera exists.

### 3.5 Evidence for P(severity class)

P(severity class) is the probability that a collision caused by the uncontrolled hazardous behaviour reaches the harm class budgeted in step 1 (injury crash or fatality).

Since DQ-023 the ODD is highways only. The ODD-A values below (head-on on undivided roads, OS-03; VRU impacts, OS-04 and OS-06; the 90 km/h ODD-A bound) are kept as computed, but set no target. They inform the residual-risk statement of WP-K-02 for engaged use outside the ODD (SH-13).

The rule:

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

   The values are part of the target set the project lead freezes (OI-3).
5. **Consistency with the HARA.** A value that implies low severity for a hazardous event rated S3 is reported to the HARA owner and explained before it is used.

What this gives: for the S2 collisions (sideswipe; rear impacts at moderate speed difference, struck from behind), fatal crashes are well under 1 % of police-reported crashes of these types, so the factor can earn about two orders of magnitude for a fatality budget. For an injury-crash budget it earns little. For the S3 collisions at highway speed (head-on, high-speed rear-end into stationary traffic, barrier impact), the factor is close to 1 for either budget. Their targets therefore rest on P(E-situation) and P(not controlled), or on narrowing the ODD. No FARS/CRSS value has been extracted yet (OI-8). The ratios are computed by [`tools/severity/`](../../tools/severity/README.md).

SH-06 is mapped to an injury-risk curve (`tools/severity/risk_curve.py`):
- **Δv** of each vehicle comes from the closing speed by conservation of momentum.
- **Driver risk** is p = (Δv / 71 mph)⁴, the Joksch (1993) rule of thumb.
- **Crash risk** is bounded over the occupants of both vehicles with the union bound, because FARS counts any death.

The worst credible lead in the ODD is a stationary heavy truck. Hitting it at the ODD speed bound (120 km/h in ODD-H, 90 km/h in ODD-A) gives a fatal-crash bound of 1. Car-to-car it is also 1 at 120 km/h, and 0.36 at 90 km/h. P(severity class) for SH-06 is therefore 1 for either budget. Its target rests on P(E-situation), P(not controlled) and the lead detection of AIR-03 and AIR-04. The curve constant is checked below; the masses and occupancies are checked under the reference-vehicle check below. Neither changes this conclusion, because the truck case stays at 1.

SH-03 uses the same curve, separately for its two situations:
- **Approaching slower traffic (OS-07, HE-03.3).** The acceleration only adds to the closing speed of SH-06, so the SH-06 value applies: 1.
- **Following at a short gap (OS-05, HE-03.1).**
  - Impact speed: the lead holds its speed, and the ego accelerates at the envelope maximum (+2.0 m/s²) over the planner's following gap (t_follow · v + 6 m, `long_mpc.py`). That gives v = √(2 · a · gap): 53–58 km/h at 120 km/h, and 47–51 km/h at 90 km/h.
  - Fatal-crash bound: worst case a fully loaded heavy truck ahead at the relaxed gap gives **0.41 in ODD-H and 0.25 in ODD-A**. Car-to-car it is 0.06 and 0.04.
  - So SH-03 earns severity credit in the following situation only, and at most a factor of about 2–4. The same unverified-input caveat applies.

SH-04 (struck from behind after phantom braking, OS-08, HE-04.1) is simulated:
- **The ego** brakes at the envelope minimum (−3.5 m/s²) to a stop, because it is not controlled.
- **The follower** at a time gap of 0.5–1.5 s holds its speed for its reaction time and then brakes. The worst credible follower is taken as reacting after 2.0 s and braking at 3.0 m/s², below the ego's deceleration. These two values are assumptions; `risk_curve.py --sensitivity` shows how the impact speed depends on them.
- **The result** is impacts at 27–35 km/h relative speed and a fatal-crash bound of **0.053 in ODD-H and 0.040 in ODD-A**, with a fully loaded heavy truck behind (0.008 and 0.006 car-to-car). This is a factor of about 19–25 of credit, matching the HARA's S2 rating of HE-04.1.
- **Not covered:** a follower that never brakes before impact is outside this bound. Whether it is credible within OS-08 is decided when the targets are frozen (OI-3) and checked in the later assessor review.
- **Rear impacts:** the SH-04 bound is driven by the ego's own occupants, struck from behind (with a heavy truck behind, 0.011 per ego occupant against 0.000 for the truck driver). The Joksch curve's use for rear-struck occupants is checked under the curve-constant check below and is conservative.

SH-01 and SH-02 (lane departure) are split by collision, and each part counts as its own situation in step 2:
- **Head-on in ODD-A (OS-03, HE-01.1, HE-02.2): curve.** The car drifts into the oncoming lane with no reaction, so the closing speed is the sum of both speeds at the ODD-A bound, 90 + 90 = 180 km/h. That is worse than the average head-on crash (item 3). The Corolla's Δv is about 105 km/h car-to-car, giving a driver risk of 0.72. With the occupant union bound, the fatal-crash bound is **1**, and it is also 1 against a truck. The head-on part of SH-01/02 therefore earns no severity credit.
- **Sideswipe and barrier impact (OS-01, OS-02): FARS/CRSS ratio.** A drift meets the adjacent vehicle or the barrier at a shallow angle, which is no worse than the average crash of those types, so item 3's condition holds. The values wait on OI-8.
- **ODD-H has no head-on case.** It is divided highway, so there only the ratio applies.
- **SH-02 departs in a curve, which is steeper than a drift.** The car goes straight while the road bends (HE-02.1).
  - **Angle.** A car leaving a curve of radius R is at θ = √(2d/R) to the road edge by the time it is d metres off the path. Take R at the controller's 3.0 m/s² limit and d = 4 m (lane margin plus shoulder, assumed). Then θ is 14° at 70 km/h, 11° at 90 km/h and 9° at 110 km/h, covering the OS-02 range (`risk_curve.py --sh02`).
  - **Why the ratio still applies.** These angles are below the 25° at which roadside barriers are crash-tested (MASH test level 3, 100 km/h), so the impact is a redirecting one. The barrier crashes in the national statistics also include loss-of-control and high-angle impacts, so the SH-02 barrier impact is argued to be no worse than their average. This argument is for the assessor to accept (OI-3).
  - **Not covered.** A barrier set back further than 4 m gives a larger angle, as does a tighter curve that is outside the ODD.
  - **Head-on in a rural curve (OS-16, HE-02.2).** This is the head-on case above: 1.
- **SH-01 barrier impact: ratio, not curve.** An SH-01 departure on a straight road follows the same geometry. With sideways acceleration a, θ = √(2·d·a)/v, the same as √(2d/R) for R = v²/a. At the controller's 3.0 m/s² limit and d = 4 m, that gives 8.4° at SH-01's 120 km/h, and up to 11° at 90 km/h (`risk_curve.py --sh01`). The first impact's Δv is a few km/h sideways, so a Δv curve would credit away almost all of the risk. The harm comes from the rebound, spin or rollover that follows, which the barrier ratio includes. As with SH-10, the SH-01 barrier impact is therefore deliberately not put on a curve.
- **SH-01/02 sideswipe: ratio, not curve.** A drift into the adjacent lane makes the same contact as an SH-10 lane change. The sideways acceleration is at most the controller's 3.0 m/s² over the lane margins to the adjacent vehicle. The `risk_curve.py --sh10` bound therefore covers it: a lateral closing speed of at most 13 km/h, about 7 km/h of Δv per car, at 6–12° between 60 and 120 km/h. It stays on the sideswipe-same-direction ratio for the same reason as SH-10.

SH-10 (lane change into an occupied lane, HE-02.5) is deliberately **not** mapped to a curve:
- **The curve would understate the risk.** The primary contact is a same-direction sideswipe: about 1 m/s sideways plus the small speed difference to the vehicle in the target lane. Its Δv is a few km/h, so a Δv curve would give almost no fatality risk. The S3 rating of HE-02.5 comes from what follows the contact (loss of control, or a spin into traffic or a barrier), which a Δv curve does not model. Using it would overstate the credit.
- **The national ratio fits.** SH-10 uses the FARS/CRSS ratio for sideswipe-same-direction crashes (item 3). The condition of item 3 holds, because a lane change into an occupied lane is the typical cause of that crash type, and its statistics include the secondary outcomes. The value waits on the FARS/CRSS extraction (OI-8).
- **Contact check (`risk_curve.py --sh10`).** This checks that an SH-10 contact belongs to the sideswipe class.
  - **Set-up.** The lane change accelerates sideways at the controller's 3.0 m/s² limit over the whole distance to contact, with no S-curve easing. That distance is the two widest lane margins, 2 × 1.06 m (WP-S-04 §3.1). Ego speeds run from openpilot's lane-change minimum, 20 mph (`desire_helper.py`), to 120 km/h.
  - **Result.** The lateral closing speed is at most 13 km/h, about 7 km/h of Δv per car. The contact angle is 6–12° at 60–120 km/h, and 22° at the 20 mph minimum.
  - **Conclusion.** That is the low-angle, low-lateral-speed contact of a same-direction sideswipe, not the near-perpendicular impact coded as an angle crash. It supports item 3's condition, which is accepted when the targets are frozen (OI-3) and checked in the later assessor review.

SH-11 (no reaction to a pedestrian or cyclist, HE-01.3, HE-03.2) moves from the FARS/CRSS ratio to a curve:
- **Why a curve.** There is no braking before impact, so the crash is worse than the average pedestrian crash (item 3).
- **Which curve.** The struck person is unprotected, so the Joksch rule does not apply. The curve is the pedestrian fatality risk of Tefft (2011, AAA Foundation for Traffic Safety): 10/25/50/75/90 % at 23/32/42/50/58 mph impact speed, interpolated linearly, and 1 above 58 mph.
- **Results.** P(severity class) is **0.38 in OS-04**, a VRU struck at the 60 km/h bound of the urban situation. It is **0.05 in OS-06**, a VRU struck after a launch from a queue at +2.0 m/s² over the 6 m standstill gap, which gives 18 km/h.
- **Not covered.** The anchor points are checked (see the curve-constant check below). The curve covers pedestrians struck by a forward-moving car, light truck, van or SUV. Its use for cyclists and its linear risk below 23 mph are checked below, and both are conservative. It is the average over struck persons; the age check below gives the values for older persons.
- **Use.** SH-11 has no rate target (§4), so these values inform the residual-risk statement of WP-K-02 rather than a target.

**Curve-constant check (2026-10-12).** Both curves were checked against search summaries of their sources. The full texts were not reachable from the project's cloud environment, so each check stops short of the primary text.
- **Joksch (1993), *Accident Analysis and Prevention* 25(1), 103–104.**
  - **Confirmed:** the citation; car-car collisions with the risk of occupant death (summaries name NASS 1980–1986, and one names its predecessor NCSS); and the fourth power.
  - **Constant:** one secondary source gives (Δv / 31.74 m/s)⁴, which is 71.0 mph, the value used here. Another quotes the constant garbled, as what reads like 61.54. With 61.54, SH-03 following rises from 0.41 to 0.73 (ODD-H) and from 0.25 to 0.44 (ODD-A), and SH-04 from 0.053 to 0.094 and from 0.040 to 0.070. The values of 1 do not change (`risk_curve.py --joksch-mph 61.54`).
  - **Rear impacts (checked 2026-10-12, search summaries).** The summaries say car-car collisions but not which impact directions the curve was fitted to. The curve is applied to rear-struck occupants: the ego in SH-04, whose occupants drive its bound, and the lead in SH-06 and SH-03. Studies that split by direction put rear impacts below frontal ones at the same speed:
    - A NASS-CDS and CIREN regression (PMC3217552, "Characteristics of crashes that increase the risk of serious injuries"): MAIS3+ risk at 30 mph Δv is 19.9 % in rear impacts against 38.9 % in frontal ones.
    - Jurewicz et al. (2016), *Transportation Research Procedia* 14: 10 % MAIS3+ at an impact speed of about 55 km/h in rear-end crashes, against about 30 km/h in head-on and right-angle crashes.
    - One NASS-CDS study reports that rear-impact occupants with MAIS 3 injuries had a median Δv of 19 km/h, against 38 km/h for belted frontal occupants, and attributes this to seat failure. That is the Δv of the injured, not the risk at a given Δv, so it does not contradict the two studies above. It does show that seatback failure is the rear-impact mechanism to watch.
    - **Conclusion:** a car-car or frontal curve overstates the risk of a rear-struck occupant, so its use in SH-04, SH-06 and SH-03 is conservative. No credit is taken for the difference: it is shown for injury (MAIS3+), not for death, and no fatality curve by direction was reachable (Viano and Parenteau 2022, SAE 2022-01-0835, gives MAIS 4+F by direction, behind a paywall).
    - **Not covered:** rear-seat occupants of the ego with intrusion from a heavy follower. Their risk depends on intrusion, which neither curve models.
  - **Impact directions (checked 2026-10-12, search summaries).** No summary of Joksch, or of Evans (1994), which uses the same NASS relation, names the directions in the data; both say two-car crashes. A curve split by direction was used to bound the question instead: Richards (2010), *Relationship between speed and risk of fatal injury: pedestrians and car occupants* (DfT Road Safety Web Publication 16, UK on-the-scene data, belted drivers).
    - **Richards constants (checked 2026-10-12 against the report's text, section 3).** This is the one source in this check whose full text was reached.
      - **Values:** frontal 3/17/60 % at 30/40/50 mph Δv and side 25/85 % at 30/40 mph, as stated in the text. They are read off the fitted curves ("approximately"); the driver-curve coefficients are not published. The fits used here go through the stated points within 0.005.
      - **Sample:** belted drivers in one significant impact with another car, rollovers excluded. On the Spot (2000–09) and CCIS (1983–2010, cars under eight years old). 620 frontal (66 fatal) and 118 side (21 fatal) drivers, weighted to the national STATS19 casualties. The report says the weighting is likely to overestimate the risk, because some slight and serious crashes are not reported to the police.
      - **Δv:** the momentum Δv used in `risk_curve.py`: two identical cars, one stationary, struck at 30 mph, each get 15 mph.
      - **Medians:** half of the frontal deaths had a Δv of 34 mph or less, and half of the side deaths 24 mph or less.
      - **Limits:** the 95 % confidence bands are drawn but not tabulated; the report says they are wide at higher speeds. UK cars under eight years old in 1983–2010 are not the US fleet of the Joksch data.
    - **Frontal:** 3/17/60 % at 30/40/50 mph Δv. A logistic fit through these points is below Joksch up to about 33 mph Δv and above it beyond: 0.17 against 0.10 at 40 mph.
    - **Side:** 25/85 % at 30/40 mph Δv, far above Joksch (0.03 at 30 mph). No curve case here has a side impact: the SH-01/02 sideswipes and barrier impacts and SH-10 are on the FARS/CRSS ratio, and the head-on is already 1.
    - **Side curve against the ratio cases (checked 2026-10-12).** The report's side sample is belted drivers on the struck side, in one significant side impact from another car; half of the drivers killed had a Δv of 24 mph (39 km/h) or less. A logistic through the two points (`richards_side`, extrapolated below 30 mph) was set against the primary contacts of the collisions kept on the ratio:
      - **SH-10 lane change (`--sh10`):** lateral Δv 7 km/h per car at every speed; side curve 0.0002.
      - **SH-01/02 barrier impact (`--sh01`/`--sh02`):** lateral Δv (1 + e) · v · sin θ, which is close to (1 + e) · √(2 · d · a) and so about 19 km/h (12 mph) at every speed, for a rigid barrier; side curve 0.002. A deforming guardrail lowers it.
      - **Conclusion:** both primary contacts are well below the 24 mph median of the side-impact deaths, so a side curve on them would credit away nearly all the risk. The deaths in these crash types come from secondary impacts, such as a spin into the side of another vehicle at highway speed, which the FARS/CRSS ratio includes and no primary-contact curve does. This confirms keeping them on the ratio.
    - **Effect (`risk_curve.py --curve richards`, the frontal fit for every occupant):** SH-03 following rises from 0.41 to 0.64 in ODD-H (ego Δv up to 61 km/h, 38 mph, into a heavy truck) and from 0.25 to 0.28 in ODD-A. SH-04 falls from 0.053 to 0.037, because its rear-struck occupants are below 33 mph. The values of 1 do not change.
    - **Decision:** Joksch stays the curve. The frontal-fit values are within the sensitivity of the lower Joksch constant (61.54 mph: SH-03 following 0.73 in ODD-H), which is already reported, so the reported range for SH-03 following, 0.25–0.41 and up to 0.73, covers both questions.
  - **Open:** the constant itself, and the impact directions in the curve's data, are to be confirmed from the full text.
- **Tefft (2011), AAA Foundation for Traffic Safety, "Impact Speed and a Pedestrian's Risk of Severe Injury or Death".**
  - **Confirmed:** the anchors 10/25/50/75/90 % at 23/32/42/50/58 mph. The data are US pedestrians struck by a forward-moving car, light truck, van or SUV, 1994–1998, weighted for oversampling. Cyclists are not covered.
  - **Cyclists (checked 2026-10-12, from search summaries).** Tefft has no cyclist data, so its use for cyclists was checked against cyclist curves. Each one puts the cyclist's risk at or below the pedestrian's at the same speed:
    - Nie, Li and Yang (2015), *Traffic Injury Prevention*, Chinese in-depth data, 371 pedestrians and 67 cyclists: 50 % fatality risk at 65.4 km/h for pedestrians and 67.6 km/h for cyclists.
    - Rosén (2013) puts 10 % fatality risk for cyclists at 67 km/h, and Jeppsson and Lubbe (2020) at 60 km/h. Tefft puts 10 % for pedestrians at 23 mph (37 km/h).
    - Lubbe, Wu and Jeppsson (2022), *Traffic Safety Research* 2, GIDAS, closing speed: 10 % risk of at least serious injury at 29 km/h for pedestrians and 44 km/h for cyclists.
    - **Conclusion:** the pedestrian curve overstates the cyclist's risk, so using it for cyclists in SH-11 is conservative. A cyclist near the lane edge in OS-04 (HE-01.3) rides in the ego's direction, so the closing speed is below the ego's speed, and using the ego's speed is conservative too. A wrong-way cyclist is outside the case; its closing speed would add the cyclist's speed. The cyclist curves are from Chinese and German data, not US data, so the check is of the ordering, not of the values.
  - **Linear risk below 23 mph (checked 2026-10-12, `risk_curve.py --low-speed`).** Tefft gives no death risk below 10 % at 23 mph, so the curve falls linearly from there to 0 at 0 mph. That segment was checked against two logistic curves:
    - a least-squares logistic fit to the five Tefft anchors (logit p = −5.108 + 0.1246 · v, v in mph), which reproduces them within 0.04. It is fitted here, because Tefft's own coefficients were not reachable;
    - Hussain et al. (2019), *Accident Analysis and Prevention* 129, 241–249, a meta-analysis of 20 studies: odds ratio 1.11 per km/h, 5 % at 30 km/h and 50 % at 59 km/h.
    - **Result:** from 2 mph to 23 mph the linear risk is above both curves. Below 2 mph it is at most 0.006 under the Tefft fit, whose non-zero risk at a standstill is an artefact of the logistic form. The only SH-11 case below 23 mph is OS-06 at 18 km/h (11 mph): linear 0.048, Tefft fit 0.023, Hussain 0.013. The linear value overstates the risk there by a factor of 2–4, so it is conservative.
    - **Limit:** both curves are for the average struck person; age is checked next.
  - **Age (checked 2026-10-12, `risk_curve.py --age`).** Tefft's anchors are the average over US pedestrians aged 15 and older, standardised to those struck in 2007–2009. The journal version (Tefft 2013) states that a 70-year-old struck at any speed has about the death risk of a 30-year-old struck 11.8 mph faster. The 2011 report, whose anchors are used here, gives 10.4 mph for death (95 % CI 5.4–15.4 mph), and its example of 25 against 35 mph is for severe injury or death.
    - **Age-by-speed tables (checked 2026-10-12).** Not reached: every copy of the report (AAA Foundation, NACTO, the NYC rules site) and the journal pages are blocked from the cloud environment, and no search summary quotes the tables. Two figures were found instead. The offset of 10.4 mph above. And a secondary source citing the report: of pedestrians struck at 30 mph, 20 % died, against 0.22 from the curve used here.
    - **Offset used:** 11.8 mph is kept, because it is above the 2011 point estimate of 10.4 mph, so it overstates the age effect slightly. The upper confidence limit is a sensitivity (`--age-offset-mph 15.4`): at age 70 it gives ≤ 0.80 in OS-04 and ≤ 0.16 in OS-06.
    - **Model:** with age additive in the logistic model, age moves the curve along the speed axis by 11.8 / 40 = 0.295 mph per year. The shift is taken from age 30, so it is an upper bound as long as the average struck pedestrian is older than 30. Age 80 is extrapolated beyond the published 30–70 comparison.
    - **Age mix (checked 2026-10-12, search summaries).** The sample is 422 pedestrians aged 15 and older from NHTSA's Pedestrian Crash Data Study (six US cities, 1994–1998; not a national sample), with a **mean age of 45**: the 2011 report adjusts its risks to "age = 45 years (mean age in sample)". The published curve is then standardised to the age mix of all US pedestrians struck in 2007–2009, whose mean was not found. For comparison, the mean age of pedestrians killed in the US was 47 in 2020 and 48 in 2023 (NHTSA Traffic Safety Facts); pedestrians struck but not killed are likely younger.
    - **Effect:** shifting from the sample mean of 45 instead of 30 gives a central estimate. At age 70 it is 0.58 in OS-04 and 0.08 in OS-06, against the bounds of 0.72 and 0.10. The bound from 30 stays the reported value until the mean age of the standardisation population is known; it can be computed from the GES person file for 2007–2009 (pedestrians, weighted mean age, 15 and older) once the NHTSA hosts are reachable (OI-8).

      | Case | Impact | Average (used) | Age 50 | Age 70 | Age 80 |
      |---|---|---|---|---|---|
      | SH-11 OS-04 | 60 km/h | 0.38 | ≤ 0.54 | ≤ 0.72 | ≤ 0.79 |
      | SH-11 OS-06 | 18 km/h | 0.05 | ≤ 0.07 | ≤ 0.10 | ≤ 0.15 |
      | Central (from age 45), OS-04 | | | 0.42 | 0.58 | 0.68 |
      | Central (from age 45), OS-06 | | | 0.05 | 0.08 | 0.09 |

    - **Against the Richards elderly curve (checked 2026-10-12 against the report's text, section 2.2.1.2 and table 4.1; `risk_curve.py --age`).** In the Ashton and Mackay data (GB, 1970s), the risk of death at 30 mph is 47 % for pedestrians aged 60 and over, 5 % for 15–59 and 14 % for all aged 15 and over. The odds ratio of 60+ against 15+ is 5.45. Applied to the Tefft average (age effect from Ashton and Mackay, level from Tefft, ratio assumed constant over speed), with the 60+ group taken to centre on about 70:

      | Case | Average (used) | 60+, Ashton and Mackay ratio | Age 70, Tefft shift 11.8 mph | Age 70, Tefft shift 15.4 mph (upper CI) |
      |---|---|---|---|---|
      | SH-11 OS-04, 60 km/h | 0.38 | 0.77 | 0.72 | 0.80 |
      | SH-11 OS-06, 18 km/h | 0.05 | 0.21 (0.11 on the logistic fit) | 0.10 | 0.16 |

      - **OS-04:** the 1970s age effect is stronger than the default Tefft shift but inside its confidence interval.
      - **OS-06:** the ratio applied to the linear segment below 23 mph gives 0.21; applied to the logistic fit of the Tefft anchors it gives 0.11, close to the shift. The linear segment already overstates the risk there by a factor of 2–4 (low-speed check above), so 0.21 compounds two conservative steps.
      - **Result:** the elderly values are stated as ranges built from both sources: **0.72–0.80 in OS-04 and 0.10–0.21 in OS-06** (WP-K-02 §5.1). The limits of the comparison: 1970s cars and medical care, the 60+ group's mean age not given, and one point per age group.
    - **Children (checked 2026-10-12 against the report's text, sections 2.2.1.2 and 4).** Tefft's sample is 15 and over, so children are outside it, while OS-04 and OS-06 include them. In the Ashton and Mackay data the risk at 30 mph is 4 % for children (0–14), against 14 % for all 15+ (odds ratio 0.26). The report finds the child risk at or below the adult risk in every dataset with children: removing them raises the fitted risk in both the 1970s and the 2000–09 data. Applied to the Tefft average, a child struck by a passenger car has **0.14 in OS-04 and 0.013 in OS-06**, below the average used (0.38 and 0.05), so the average covers children.
      - **Vehicle shape:** the reference vehicle is a passenger car (Corolla). A high-fronted SUV or light truck raises a child's odds of death by about 1.8 times (2.3 under age 10; LSHTM and Imperial College meta-analysis, *Injury Prevention* 2025, search summary). With that factor a child has 0.22 in OS-04 and 0.023 in OS-06, still below the average. A port of LionDriver to an SUV or light truck re-checks this (and the Tefft average itself, which is standardised to the US car and light-truck mix).
      - **Limits:** 1970s data, one point per age group, odds ratio assumed constant over speed.
    - **Decision:** P(severity class) stays at the average. It enters a rate of harm over all the VRUs LionDriver may strike, and the average over struck persons is the quantity that rate needs. This holds only while LionDriver's VRU exposure has about the national age mix. The residual-risk statement (WP-K-02) reports the elderly ranges beside the average, so that an older person's risk (about double in OS-04, 0.72–0.80 against 0.38) is stated, not averaged away.
    - **Not covered:** the age mix of LionDriver's own VRU encounters. A drive log with many encounters near schools, care homes or retirement areas would call for the age-shifted value in that stratum.
  - **Against the Richards pedestrian curves (checked 2026-10-12 against the report's text, section 2 and table 4.1; `risk_curve.py --pedestrian-compare`).** Richards (2010) fits three pedestrian datasets with one method, each weighted to national casualties (which the report says is likely to overestimate the risk). Ages 15 and over, to match Tefft:

    | Impact | Tefft (used) | Ashton and Mackay, GB 1970s | OTS and police fatal files, GB 2000–09 | GIDAS (Rosén and Sander), DE 1999–2007 |
    |---|---|---|---|---|
    | 30 mph | 0.22 | 0.14 | 0.09 | 0.07 |
    | 40 mph | 0.45 | 0.60 | 0.33 | 0.25 |
    | SH-11 OS-04, 60 km/h | **0.38** | 0.45 | 0.24 | 0.18 |
    | SH-11 OS-06, 18 km/h | **0.05** | 0.002 | 0.005 | 0.004 |

    - The 30 and 40 mph rows are the report's values; the SH-11 rows use a logistic through them, extrapolated at 18 km/h.
    - **Result:** Tefft is above both recent datasets in both SH-11 cases, by a factor of 1.6–2.1 in OS-04 and about 10 in OS-06. Only the 1970s data are higher in OS-04. The report attributes the fall since the 1970s to car design and medical care, and says the three curves lie within each other's confidence bands.
    - **Decision:** Tefft stays the curve. It is conservative against the recent European data, and the 1970s fleet does not represent the cars LionDriver runs on. The report's age split (Ashton and Mackay, all ages: 47 % at 30 mph for elderly pedestrians against 5 % for adults) agrees in direction with the Tefft age check above.
  - **Corrected citation:** the anchors are from this 2011 report. The earlier citation named the journal version, Tefft (2013), *Accident Analysis and Prevention* 50, 871–878, which gives about 10 % near 24 mph and 50 % near 41 mph. With the journal values, SH-11 at the OS-04 bound would be about 0.40 instead of 0.38.


**Reference-vehicle check (2026-10-12, `risk_curve.py --vehicles`).** The masses, occupancies and restitution of the vehicle cases were checked and set to the worst corner of their credible range:

| Input | Was | Evidence | Now |
|---|---|---|---|
| Ego mass | 1,400 kg (unchecked) | Reference configuration CFG-001 (Corolla E210 · ZRE212 · US, MY2020–2022; [vehicle register](../../docs/liondriver/vehicles/README.md)): 2020 LE listing curb weight 2,910–2,955 lb (1,320–1,340 kg; TrueDelta and AutoPadre listings, search summaries; Toyota's own sheet not reached). opendbc `TOYOTA_COROLLA_TSS2` CarSpecs: 3,060 lb (1,388 kg) for the whole platform, hybrids included. With five occupants about 1,720 kg. Other E210 model years and trims are not checked (WP-C-01 OI-9) | **1,320 kg**: the lightest ego has the largest Δv, and the ego's occupants drive every SH-03 and SH-04 bound |
| Ego occupants | 5 | Every E210 sedan seats 5 | 5 (confirmed) |
| Ego width | 1.78 m (WP-S-04) | 1,781 mm | Confirmed |
| Passenger car | 1,500 kg, 5 occupants | Grid 1,100–2,700 kg | Kept: the car never sets a worst case (the truck does) |
| Heavy truck | 15 t, 2 occupants | Up to the US gross limit of 80,000 lb (36.3 t) | **36.3 t**: a heavier truck gives the ego a larger Δv |
| Restitution | 0.1 | About 0.1 at closing speeds of 15 mph and above in low-speed test fits (search summary); every case here closes at 27 km/h or more | 0.1 (kept) |

- **Effect:** over the grid (ego 1,320/1,388/1,400/1,720 kg, car 1,100/1,500/2,700 kg, truck 15/36.3 t), the new defaults give the largest bound in every case. SH-03 following rises from 0.33 to **0.41** (ODD-H) and from 0.20 to **0.25** (ODD-A); SH-04 from 0.043 to **0.053** and from 0.032 to **0.040**. The truck mass causes most of the rise. The values of 1 (SH-06, SH-03 approaching, the head-on) do not change, and car-to-car values change by less than 0.003.
- **Not covered:** the occupancy of the other vehicle (2 truck occupants, 5 car occupants) does not matter here, because the other vehicle's Δv is small in every worst case.

## 4. Validation targets

**Speed bound.** The derivations above and in §4.3 were made at the earlier ODD bound of 120 km/h. They are kept, and stay conservative for the 110 km/h bound (DQ-260): stopping distances, impact speeds and the severity bounds all grow with speed. The departure angles of SH-01/02 grow as speed falls, but the range given already covers 90–120 km/h.

Targets are **proposals** until they are frozen (OI-3). The rule was decided 2026-10-19 by the project lead, decision register DQ-096 option B:

- Claude updates the derivations once the B1 crash data replaces the illustrative rates of §3.1 (OI-2).
- The project lead then freezes the targets in a dated record.
- An assessor reviews them later.
- Evidence from a SOTIF test campaign (WP-V-03, WP-V-04) counts only if it was collected after the freeze.

A later change to a frozen target needs a new dated record, and evidence collected before that change is re-assessed against it. "Demonstration" names the primary method; §5 defines the methods.

| ID | SH | Quantity | Proposed target | Derivation | Demonstration | Achievable? |
|---|---|---|---|---|---|---|
| VT-01 | SH-01 excessive / wrong lateral motion | Unrequested lane departures (AIR-02) per engaged hour | Rate-level: ≤ 5 × 10⁻⁶ /mi (case D). Scenario-level: p_s ≤ 1 % per scenario in KS-01…KS-06, KS-14 at 95 % | §3 steps 1–5; P(not controlled) per §3.3 (VS-VAL-10) | Scenario-level by SIM + CC + REPLAY; rate-level surrogate on public road | Scenario-level yes; rate-level no (reported as surrogate with upper bound) |
| VT-02 | SH-02 unannounced loss of lateral control | Lateral drift > 0.5 m without a take-over alert within 1 s | p_s ≤ 1 % per curve/marking scenario; zero occurrences in all CC trials | SG-02 budget (≤ 1 s to warning) | CC (KS-01, KS-03), SIM, REPLAY | Scenario-level yes |
| VT-03 | SH-03 unintended acceleration | Positive acceleration toward a slower or stopped lead inside the time gap | Zero occurrences in KS-07…KS-09 trials (≥ 59 per scenario) | §3 step 5, case F | SIM (`longitudinal_maneuvers` + MetaDrive), CC | Yes |
| VT-04 | SH-04 phantom braking | Decelerations < −2.0 m/s² without a relevant object (AIR-05) | Surrogate on public road: ≤ 1 per 1000 km with 95 % upper bound reported; scenario-level p_s ≤ 1 % for bridges/overpasses, metal plates, shadows (KS-10, KS-11) | §3 step 5 | REPLAY of recorded drives, PR | Partially (upper bound limited by mileage) |
| VT-05 | SH-05 override not effective | Release on brake / cancel / steering override | 100 % release within SG-05 budget in ≥ 299 trials per input type and speed band (p ≤ 1 % at 95 %) | Deterministic function, tested as a sample | CC, HIL (WP-V-05) | Yes |
| VT-06 | SH-06 missed or late stationary/slow lead | Collision or required driver braking > 5 m/s² | p_s ≤ 1 % per approach-speed band in the ODD (KS-05, KS-08); FCW at TTC ≥ 2 s (AIR-06) | §3 step 5, case E; B2 comparison | CC with soft target, SIM | Yes for the bands tested |
| VT-07 | SH-08 PCS suppression | Stock PCS activation with LD-SDA installed vs stock | Equivalent activation (same TTC ± 0.2 s) in every PCS soft-target test | B2 | CC (KS-20; VS-VAL in WP-V-01) | Yes |
| VT-08 | SH-12 prolonged unsupervised operation (DM) | Distraction, phone, sleep detection; fallback on camera blockage; reminder timing in the wheel-touch fallback | AIR-07/AIR-08 thresholds per DM stratum; DMP-01…DMP-05; AC-05; fallback timing per §4.4 | WP-C-08 §5.3, §5.4; §4.4 | EVAL (VS-ML-06), CC (WP-C-08 §8 V-5), T-SIL and PR for §4.4 | Yes, once TSR-634 is implemented |
| VT-09 | All | Comparative performance vs stock TSS2 (B2) | LD-SDA not worse than stock in any KS scenario run with both (metric per scenario in WP-V-03) | B2 | CC (paired runs, §2.2) | Yes for scenarios run |
| VT-10 | All | Unknown-scenario discovery rate | Discovery rate of new hazardous scenario classes (WP-V-04 §5) decreasing over the last 3 exploration blocks, with no class of severity S3 found in the last block | 21448 §11 | PR, SIM exploration, log mining | Yes as a trend; not as a proof |
| VT-11 | All | Field: harm-level events attributable to LD-SDA | Zero injury crashes; trigger thresholds for restriction defined in WP-O-04 | B1 (long-term) | Field monitoring | Long-term only |
| VT-12 | SH-13 operation outside the ODD | Engaged operation above the ODD speed bound or in excluded conditions | Deterministic speed bound (FM-07): 100 % prevention/disengagement in ≥ 59 trials per speed threshold; other exits covered by user information and driver procedure (AC-04) | FM-07, FM-08 | CC, inspection | Yes for speed; not for other exits |
| VT-13 | SH-10 assisted lane change into an occupied lane | Driver can abort a nudge-initiated lane change | Abort controllable in ≥ 20/20 subjects (CA-01 logic) | WP-C-06 TC-28 | CC (KS-14) | Yes |
| VT-14 | SH-01, SH-04 plan stability (AIR-11) | Steady-scene instances in which the model output asks for more than the controller passes: `modelV2.action.desiredCurvature` changes faster than the jerk bound 5 m/s³ / v² (`MAX_LATERAL_JERK`, `selfdrive/controls/lib/drive_helpers.py:13, 29-31`; FSR-01.14), or the lead existence (`prob` crossing 0.5) toggles more than once in any 1 s window for a continuously visible lead | p_s ≤ 1 % per steady-scene instance at 95 % (≥ 299 instances per ODD stratum): straight and constant-curvature segments of KS-01…KS-06 for curvature; KS-07, KS-08, KS-10, KS-11 for lead toggling | §4.2; same p_max as VT-01 | REPLAY (VS-ML-07) on evaluation data; CC for the lead scenarios | Yes |
| VT-15 | SH-01, SH-04, SH-06, SH-13 runtime monitor (AIR-14) | (a) Recall: share of instances in which the model alone fails (hazardous behaviour or AIR violation) that the monitor flags before the failure; (b) false flags per hour of nominal ODD driving | (a) ≥ 80 % per KS of the known-triggering-condition set (KS-12, KS-13, KS-16) at 95 %: ≥ 14 failing instances with no miss, or the Clopper–Pearson bound. A TC whose model-alone failure rate exceeds the §4.2 limit needs higher recall or an ODD restriction. (b) ≤ 1 false flag per hour at 95 % (χ² bound of §3 step 3), on drives disjoint from tuning data (DSR-11) | §4.2; nuisance budget equal to AIR-08 | REPLAY with KS segments; PR for false flags | Yes, after AIR-14 is implemented (GAP-22) |

SH-09 (traffic-control non-compliance) has no target: Experimental Mode is off and locked (FM-01) and KS-24 verifies the exclusion. SH-11 (no VRU response) has no rate target: [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) resolves TC-12 by ODD restriction (highways only, DQ-023) and user information; KS-22 and KS-23 only verify that the item does not move toward a VRU it cannot see.

![Figure 4-1: validation targets VT-01 to VT-15 on log scales of driving exposure (km, hours at 64 km/h) and of trials, instances or subjects per scenario, against the §3.2 capacity bands for public road, closed course and simulation](figures/fig-v02-4-1-validation-targets.svg)

*Figure 4-1.* One row per target of the table above, with the exposure it needs: in km where the target is a rate (VT-01 rate-level from case D of §3.1; VT-04 and VT-15(b) computed from their rates with §3 step 3 at C = 95 %), and as a count per scenario, input type or stratum otherwise. The shaded bands are the yearly capacities of §3.2; the closed-course band edges are read from "tens to low hundreds". Every mark is dashed because the targets are placeholders until OI-3; VT-07…VT-11 have no exposure figure. Drawn from the table above, §3.1 and §3.2. Generated by [`figures/fig_v02_validation_targets.py`](figures/fig_v02_validation_targets.py); CI fails if it is stale.

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

At the ODD speed bound, the required report distance is 33.3 + 33.3² / 6 ≈ 218 m. The 180 m given as an example in AIR-04 is for 30 m/s. Both values are confirmed. They remain proposals until the targets are frozen (OI-3).

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
| AIR-11 | Curvature rate from 5 m/s³ jerk; ≤ 1 lead toggle per second | VT-14 (field signature AS-08 in [WP-V-04](WP-V-04-sotif-unknown-scenarios.md); not a surrogate for harm, §4.5) | C | — |
| AIR-14 | Monitor recall ≥ 80 % on known triggering conditions; ≤ 1 false flag per hour | VT-15 (KS-12, KS-13, KS-16 of [WP-V-03](WP-V-03-sotif-known-scenarios.md)) | C | Per-condition recall may need to be higher (§4.2) |
| AIR-10 | Partial lens occlusion ≤ 10 % | — | N | Input-space bound of WP-C-11 §3, verified by VS-ML-04 ([WP-W-10](../05-software/WP-W-10-ml-engineering.md)) |
| AIR-13 | 90–98 % of samples within ±2σ | — | N | Calibration criterion of WP-W-10 (VS-ML-05); enables AIR-14 |
| AIR-12, AIR-26 | 2 s warm-up before use or engagement | — | N | Timing; [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) |
| AIR-17 | Inference ≤ 50 ms, output age ≤ 100 ms | — | N | Timing; WP-S-04, TSR-602, TSR-616 |
| AIR-27 | DM output invalid > 2 s | — | N | TSR-609 ([WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md)); fault injection VS-FI-25 |
| DSR-07 | ≥ 10 % double annotation | — | N | Label specification (WP-W-10) |

Result: eight values are confirmed or replaced (C). AIR-11 and AIR-14 are confirmed through VT-14 and VT-15, and AIR-01, AIR-03 and AIR-04 through the derivation of §4.3. No value is left at D or G. The remaining six take their value from timing, ML engineering or data documents, not from this one (N). Until then, every (TBC) in WP-C-11 stays (TBC).

### 4.4 Validation of the wheel-touch reminder timing (TSR-634)

[WP-C-08 §5.4](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) sets the speed-dependent reminder timing for the wheel-touch fallback: alert *k* fires at 150 / 240 / 395 m driven, or 5 / 15 / 25 s if that comes first (DMP-05, TSR-634, DQ-077 A). VT-08 covers it with the four checks below. The values are proposals for the assessor review (OI-3). The rule is implemented in `policy.py` (WP-W-02 SWSR-634, 2026-10-17). Its unit tests run the check (a) speed profiles against the policy alone: each alert falls within one DM cycle of the rule. That is unit-level evidence, not the T-SIL replay of check (a), which still needs its entry in WP-S-09. Checks (b) to (d) have not been run.

| Check | Question | Proposed criterion | Method | Where |
|---|---|---|---|---|
| (a) Conformance | Does the code implement the rule, including while speed changes? | Every alert at min(T*k*, D*k*) within one DM cycle, for constant speeds 30…120 km/h in 10 km/h steps and for acceleration and deceleration ramps of ±1.5 m/s² across 57 km/h, the speed where distance starts to govern | T-SIL replay of synthetic speed profiles | Verification entry in [WP-S-09](../03-system/WP-S-09-system-verification.md) (§7) |
| (b) Response | Do drivers in the fallback respond to the faster alerts before the no-response stage? | 20/20 valid subjects give a wheel input before the no-response stage, at 90 and 110 km/h, with the fallback forced (sunglasses) during a scripted secondary task (CA-07 sample logic) | CC: DM clinic, WP-C-08 §8 V-5; subjects per [WP-V-01](WP-V-01-safety-validation.md) §5.2 | WP-V-01 VS-VAL-17 |
| (c) Nuisance | Do the extra alerts annoy attentive drivers enough that they defeat the system? | Alert 2 or 3 in the fallback with an attentive, hands-on driver: ≤ 1 per hour at 95 %, on highway drives at 90–110 km/h. This is the χ² bound of §3 step 3 with the AIR-08 nuisance budget | PR with safety driver, fallback forced; alerts reviewed against cabin video | VT-08 result row |
| (d) Exposure | How often is the fallback active? | No criterion. The share of engaged time in the fallback is reported per DM stratum (sunglasses, night, glare) and sizes the residual of LS-09 | PR, log mining | [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) residual estimate |

If (b) or (c) fails, the anchor of D*k* is revisited (WP-C-08 OI-8). A change of D*k* goes back through WP-C-08 §5.4 and TSR-634, not into the code alone.

### 4.5 Surrogates for harm (DQ-140)

Decided 2026-10-25 by the project lead (decision register DQ-140 option A): a small set of surrogates, each with its own argument. One car cannot drive far enough to show a crash rate (§3.2), so public-road driving reports surrogate rates instead: events far more frequent than harm that lie on the path to it. A surrogate counts toward a target only once its argument has been checked against LionDriver logs. None has been: no LionDriver log exists yet ([WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-4). **The arguments below are drafts.**

Each argument has two parts: why the event precedes harm, and how often it does. "How often" is the share of events that would have ended in the SH's hazardous behaviour or harm without the driver. It is estimated from triage of the events, as in [WP-V-04](WP-V-04-sotif-unknown-scenarios.md) §5.2 (3). Until it is estimated, no scaling credit is taken: each event counts as one hazardous behaviour.

| ID | Surrogate | SH, VT | Why it precedes harm (draft) | How often it does (draft) | Detected from logs | WP-V-04 signature | Checked against logs |
|---|---|---|---|---|---|---|---|
| SU-01 | Unrequested lane departure: a front wheel crosses a lane marking with no desire active and no driver steering input (AIR-02) | SH-01, SH-02; VT-01 | A sideswipe or barrier impact of SH-01/02 (HE-01.2, HE-02.1) needs the car to leave its lane first. The departure is the hazardous behaviour itself; what stands between it and harm is §3 step 2: a vehicle or barrier on that side, a driver who does not correct, and the severity | P(harm \| HB) of §3 step 2, factor by factor from §3.3–§3.5; each factor is 1 until it has evidence | Engaged, no blinker, `modelV2` lane-change state off, `carState.steeringPressed` false; the vehicle side at or over a model lane line with probability ≥ 0.5 (vehicle width 1.781 m). The side reaches the line before the wheel does, so this counts more events than AIR-02, not fewer. Each event is confirmed on the road video, because the model's lines can be wrong | AS-05 at a gap of 0 m. The 0 m reading is not yet in the AS-05 definition (OI-5) | No |
| SU-02 | Envelope limit hit | SH-01, SH-03, SH-04; VT-01, VT-04 | The envelope caps every actuation (AC-02). A command at or past a limit means the QM stack asked for more than the controllability tests cover (§3.3); the envelope then cuts it to the bounded behaviour those tests reproduce. A hit marks the stack at the edge of what is shown controllable. It does not precede a hazardous behaviour that stays inside the limits, such as a slow drift; SU-01 covers that | Many hits are expected to be harmless: a tight curve inside the ODD, or firm braking for a real lead. The share followed within a few seconds by SU-01, a phantom deceleration (AS-06) or a take-over is estimated from triage | Safety replay of each engaged log (`opendbc_repo/opendbc/safety/safety_replay/`, method M6): TX frames blocked, and frames at the torque or acceleration limit, while engaged; per engaged km | AS-04 | No |
| SU-03 | Take-over with a short time to the line | SH-01, SH-02; VT-01, VT-02 | A driver steering correction while the car moves toward a lane line is the driver controlling an SH-01/02 departure that has already started. With little time left to the line, a driver reacting later would not have prevented the departure. It is the near-miss of SU-01 | The share that would have crossed the line without the take-over, judged from the path before it. Until estimated, each counts as a departure for VT-01 | AS-01 events (steering override while engaged, no blinker). Time to the line at the first `steeringPressed` frame: the AS-05 gap divided by the speed toward the line, from successive lane-line positions. Threshold proposed: ≤ 1.5 s, the upper end of the driver reaction time of [WP-S-04 §3.7](../03-system/WP-S-04-timing-ftti-budget.md) (t_r = 0.75–1.5 s). Fixed before block B1 with the signature thresholds (WP-V-04 §2.1.1 item 3) and approved with the targets (OI-3). Each event is confirmed on video | AS-01 with a time-to-line reading, not yet in the AS-01 definition (OI-5) | No |

Not in the set:

- **Other take-overs and disengagements** (AS-01 above the threshold, AS-02, AS-03), FCW events (AS-07), DM alerts (AS-10) and system events (AS-11). Most are routine, so their rate mixes noise with risk (option B, not chosen). They stay discovery signatures for WP-V-04 and triage classes in the field.
- **Phantom deceleration (AS-06).** VT-04's quantity is the SH-04 hazardous behaviour itself (AIR-05), counted directly. Its link to harm is §3 step 2 for SH-04 (a following vehicle, §3.4), not a surrogate argument.
- **Model disagreement (AS-08).** It stays the field signature of VT-14 (§4.1): it tracks plan stability against AIR-11 after release. §4.2 argues why an unstable plan precedes SH-01 and SH-04, but not how often, so it stands in for no harm event and earns no rate credit.

**Check against logs (OI-5).** On the first engaged blocks (WP-V-04 B1), for each surrogate:

1. **Detector.** Every event is reviewed on video; the share of false detections is recorded, and a sample of drive time without events is reviewed for missed ones.
2. **Share.** "How often" is estimated with its one-sided 95 % Clopper–Pearson bound (§3 step 3).
3. **Review.** The argument and its data are reviewed under [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md).

A surrogate whose detector or argument fails the check leaves the set. Its target is then reported without it.

## 5. Test methods

### 5.1 Methods matrix

| Method | Tooling in repo | What it shows | Fidelity / limits | Evidence credit | VTs |
|---|---|---|---|---|---|
| M1 Process replay (open loop, recorded inputs) | `openpilot/selfdrive/test/process_replay/test_processes.py`, `process_replay.py`, `compare_logs.py` | Determinism and regression of controlsd, plannerd, radard, selfdrived, dmonitoringd on recorded inputs | Open loop: vehicle response not re-simulated. References come from `commaai/ci-artifacts` (`test_processes.py:70`); one Corolla TSS2 route in the source list (`:26`) | Regression only, once fork-owned references exist (D-03) | Supports all |
| M2 Model replay | `process_replay/model_replay.py` | Model output changes between versions | One 3 s segment (`model_replay.py:23-26`); forced pass in CI (`:294-296`); comma device pool | Regression only; extended per [WP-W-10](../05-software/WP-W-10-ml-engineering.md) VS-ML-12 | Supports VT-01…06 |
| M3 Requirements-based model evaluation | To be built (WP-W-10 VS-ML-03…08) | AIR metrics per ODD stratum on LionDriver data | Open loop | Primary for perception-level AIRs | VT-01, 04, 06, 08 |
| M4 Closed-loop simulation | `openpilot/tools/sim` (MetaDrive bridge) | Closed-loop lateral behaviour of the full stack with rendered images | Fixed loop track, 2 lanes 4.5 m wide, 90° curves, **no traffic** (`metadrive_bridge.py:30-46, 84`); rendering not photorealistic; vehicle dynamics not Corolla; CI job disabled (`.github/workflows/tests.yaml:185`) and bridge test skipped (`tools/sim/tests/test_sim_bridge.py:24`); success criterion is only "stay in lane" (`metadrive_process.py:130-138`) | **No credit until the fidelity case of §5.3 is approved for the scenario family** (lead decision at G2, [WP-M-08](../01-management/WP-M-08-sotif-plan.md) OI-3, DQ-139). Use for exploration and trend data first; results labelled as synthetic (§5.3.5). Adaptation to the reference Corolla with the panda safety code in the loop in progress (§5.3.1) | VT-01, 02, 10 (after fidelity case) |
| M5 Planner maneuver tests (plant model) | `openpilot/selfdrive/test/longitudinal_maneuvers/` | Longitudinal planner response to lead/stop scenarios; crash check `d_rel < 0.4 m` (`maneuver.py:66-68`) | Point-mass plant, not Corolla; lead from synthetic radar/vision probability; no perception | Planner-level verification for VT-03/06 sub-cases | VT-03, VT-06 |
| M6 Safety replay | `opendbc_repo/opendbc/safety/safety_replay/` | Envelope limit hits in recorded drives | Needs LionDriver Corolla logs | Surrogate indicator | VT-01, 04 (surrogate) |
| M7 HIL bench | To be built (D-04) | Envelope and fault reactions with real panda firmware | Bench CAN only | FuSa (WP-V-05); SOTIF for VT-05 | VT-05 |
| M8 Closed course | Reference vehicle, test site, soft targets; `tools/longitudinal_maneuvers`, `tools/lateral_maneuvers` for characterization | Real vehicle, real sensors, controlled scenario | Limited speed, scenario set, number of trials; soft target radar signature | Primary for VT-02, 03, 05, 06, 07, 09 | as listed |
| M9 Public road with safety driver | [WP-V-07](WP-V-07-vehicle-test-operations.md) | Real ODD exposure, exposure rates ε_s, surrogates, unknown scenarios | Uncontrolled; low mileage | Exposure estimates and surrogate rates (§4.5); WP-V-04 exploration. No B2 credit (§2.2) | VT-01, 04, 10 |
| M10 Field monitoring | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) | Post-release behaviour | Small fleet | Operation phase only | VT-11 |

### 5.2 Order of application per scenario

1. M3/M1 on recorded data to check perception and planning outputs for the scenario.
2. M4/M5 to explore parameter ranges and estimate p_s where the simulator is credible.
3. M8 to confirm the worst cases from step 2 on the real vehicle, and to run scenarios the simulator cannot represent.
4. M9 to observe the scenario in the real ODD and estimate ε_s.

### 5.3 Simulation fidelity case (required before M4 gets credit)

**Rule.** A simulation result gets no credit toward any target until the fidelity case for its scenario family is approved. The project lead decided this rule on 2026-10-16 (decision register DQ-139 option A, WP-M-08 OI-3): credit is given per scenario family, and only once that family's fidelity case passes and is approved. A family without an approved case is used only for exploration and to choose closed-course parameter points. Every M4 result is labelled as synthetic data (§5.3.5).

This section is the plan for building that case. Nothing in it has been executed.

#### 5.3.1 Status of the simulator (2026-10-16)

| Item | State |
|---|---|
| Bridge `openpilot/tools/sim` (MetaDrive) | Upstream state: Honda Civic CAN, panda bypassed (`can`/`pandaStates` published directly), one loop track, no traffic. CI job disabled (`.github/workflows/tests.yaml`, `simulator_driving`, `if: false`) |
| Adaptation to the item | In progress by the simulation session (update 2026-10-16). PR #124 (draft) takes the SOTIF session's branch `claude/sotif-metadrive` (`7598c2b`) and adds: headless rendering wired into the MetaDrive process, the ego moved kinematically from the plant's curvature and acceleration instead of MetaDrive's vehicle dynamics, the Corolla TSS2 fingerprint, traffic models limited to those licensed CC-BY-4.0, and the `simulator_driving` CI job re-enabled. Checked in the cloud container without the driving model (its LFS host is not reachable there): openpilot fingerprints `TOYOTA_COROLLA_TSS2` with safety parameter 73 from the simulated CAN. Closed loop with the driving model: only in CI, not yet passed |
| Headless rendering on CPU | Works through panda3d's EGL pipe on Mesa llvmpipe with multisampling off. Measured on a 4-core cloud container: 160–230 ms per rendered frame (about 4–5 frames per second), almost all in the camera's scene pass. The device runs the road camera at 20 frames per second |
| Scenario scripting | Scenario files exist: nine WP-V-03 scenarios as OpenSCENARIO/OpenDRIVE (`assurance/sim/scenarios`), replayed headless in esmini in CI; the fault-injection plant model reads their roads. Not yet loaded by the MetaDrive bridge (update 2026-10-16) |
| Fault-injection plant model | Built (`assurance/sim`, layer 1): the panda safety code in a closed loop with a single-track Corolla, EPS, PCM and driver models; results labelled per §5.3.5; no credit |

#### 5.3.2 Scenario families

A family is a set of known scenarios ([WP-V-03](WP-V-03-sotif-known-scenarios.md)) that share what the simulator must get right. The case is made per family; one family's approval says nothing about another.

| Family | Known scenarios | What must be faithful | MetaDrive can represent it? |
|---|---|---|---|
| SF-1 Lane keeping on straights and curves | KS-01 (curve at or beyond the lateral limit), steady segments for AIR-01 and VT-14 | Lane-line rendering, lateral dynamics and EPS response, `steerSaturated` timing | Yes, once the EPS model is fitted (F-2) |
| SF-2 Lead following and lead braking | KS-08 | Lead detection by vision and radar, PCM response | Yes |
| SF-3 Stationary or slow target ahead, cut-out | KS-05, KS-09, KS-27 | Detection range of a stopped vehicle, FCW timing; for KS-27 also when the curve and roadside reveal the lead | Yes. The radar model is the weak point (F-3), and for KS-27 so is radar visibility around the curve |
| SF-4 Close cut-in | KS-07 | Lateral motion of the target, lead association | Yes |
| SF-5 Driver override and authority | KS-19 | Panda safety code (the same code), driver torque, brake and gas signals | Yes; the strongest family, because the safety code is the item's own |
| SF-6 ODD speed bound | KS-25 | Speed signals; FM-07 once built | Yes |
| SF-7 Pedestrian on the highway shoulder | KS-22 | Pedestrian rendering, lateral behaviour near it | Partly: one pedestrian model, no cyclist |
| — Not representable now | KS-02 (banking, crosswind), KS-03 (faded or ghost markings), KS-10/KS-11 (radar clutter, overpasses), KS-12/KS-15 (low sun, glare, rain), KS-16 (camera obstruction), KS-17/KS-18 (driver monitoring), KS-20 (stock PCS), KS-24, KS-26 | Rendering is not photorealistic; no radar physics, weather, driver camera or stock PCS model | No credit can be sought. §5.4 assesses CARLA for the lighting and weather families |

#### 5.3.3 Fidelity elements

Each element names what is compared and the evidence. A family needs every element it depends on.

| Element | Compared | Evidence | Families |
|---|---|---|---|
| F-1 Perception input | Model outputs on rendered frames against the same quantities on real frames of matched closed-course trials: lane-line position and probability, lead distance and probability | M8 trials of [WP-V-07](WP-V-07-vehicle-test-operations.md) at the matched points, replayed through M3 | All |
| F-2 Vehicle and actuator response | Step responses of the EPS (torque to lateral acceleration, delay) and of the PCM (ACCEL_CMD to acceleration, dead time) in the plant model against the reference vehicle | VS-VAL-08 (PCM onset) and lateral step tests in [WP-V-01](WP-V-01-safety-validation.md); the plant constants are replaced by the measured values | All |
| F-3 Radar | Track range, field of view, dropouts and latency of the simulated radar against `radarState` recorded on the reference vehicle | Recorded public-road and closed-course drives | SF-2, SF-3, SF-4 |
| F-4 Timing | Camera frame rate, model latency and control-loop timing in the simulator against the device | The run log of every simulation. **Validity floor:** a run counts only if the camera frame rate stayed at or above the floor agreed with the case (proposed 18 per second, against 20 on the device). The CPU-only CI runner (about 4–5 per second) is below it | All |
| F-5 Safety code | That the simulated panda runs the released safety code, as built for the reference vehicle | Build of `libsafety` from the pinned opendbc commit with `LIONDRIVER_REFERENCE`; the MCU's timing is not simulated | SF-5, and the authority of all families |
| F-6 Actors | Scripted target trajectories against the test specification | Exact by construction; recorded per run | SF-2…SF-4, SF-7 |

#### 5.3.4 Comparison and acceptance (proposed, approved with the targets, OI-3)

1. **Matched points.** At least 5 parameter points per family, run on the closed course (M8) and in the simulator with the same scenario parameters. The points span the family's range, and include the worst case found by M4 exploration.
2. **Quantities and acceptance.** All three must hold at every point:
   - **Outcome class:** the same (pass, alert-then-pass, fail).
   - **Alert timing:** within ±0.3 s.
   - **Lateral offset:** the RMS difference of the traces stays within 0.15 m over the scenario (SF-1, SF-4, SF-7).
   - **Minimum gap and deceleration:** within 15 % (SF-2, SF-3).
   These values are proposals, approved with the targets (OI-3).
3. **Direction of error.** Where outcomes match but the simulator is less severe than the vehicle (for example, later braking on the vehicle), the family gets no credit, or is credited only with a margin that covers the difference.
4. **Recorded.** Each point's sim and M8 log IDs, the simulator commit, the asset hash, the plant constants used and the frame rate go into the fidelity-case record, reviewed under [WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md).
5. **Validity.** An approval holds for the simulator version, plant constants and software release it was made with. A change to any of them is an impact-analysis item ([WP-P-02](../07-supporting/WP-P-02-change-management.md)); model changes re-run the matched points (D-05).
6. **Tool classification.** The bridge, plant model and scenario scripts are classified under [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) before the first approval.

#### 5.3.5 Labelling synthetic data (DSR-12)

Every simulation result (log, result file, figure) carries:
- `data_kind: synthetic`;
- the simulator and its commit;
- the asset archive hash;
- the scenario ID and family;
- the fidelity-case status of the family (`none`, `planned`, `approved <ref>`);
- the credit (`none` until approved);
- the measured camera frame rate.

Synthetic results are stored apart from real drive logs, under their own dataset IDs. They are never pooled into exposure rates ε_s, P(E-situation), surrogate rates or any other real-world rate estimate. A target may count them only as scenario-level evidence for an approved family (step 5 of §3), shown as a separate line in WP-V-03 and WP-K-02. This implements [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) DSR-12.

### 5.4 CARLA with ScenarioRunner (assessed, not built)

CARLA, with ScenarioRunner executing OpenSCENARIO scenarios, could cover what MetaDrive cannot: weather, low sun and night lighting (KS-12, KS-15), more realistic rendering for F-1, and a radar sensor model (F-3). Its scenario files are a standard format that an assessor can read and rerun.

Costs:
- **It needs a GPU** to render at the device's frame rate. LionDriver's CI runners have none, so it needs a GPU runner or cloud machine, which costs money; no quote has been obtained.
- **A new bridge:** upstream openpilot dropped its CARLA bridge in favour of MetaDrive, so LionDriver would build and maintain one, reusing the simulated car and panda of §5.3.1.
- **Its own fidelity case** under the rules above.

Recommendation: **do not build it now.** First finish MetaDrive and its fidelity case. Revisit at G3, when the fidelity case shows which families MetaDrive cannot carry and the lighting and weather scenarios are scheduled. The project lead accepted this on 2026-10-16 (decision register DQ-261 option A): no GPU and no CARLA work now; the question returns at G3.

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
| TC-35 | Lead detected late in a curve while accelerating to the set speed | KS-27 | | ○ | | ● | ● | |
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
| TC-34 | Stock PCS would act while the item is engaged or alerting | KS-20 | | | | | ● | |

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
| OI-2 | Decided 2026-10-25 (DQ-137 option A; WP-M-08 OI-1 closed): the B1 data set and filter are in §2.1. Open, the extraction: download FARS, CRSS and the FHWA travel by functional class for one data year; compute fatal-crash and injury-crash rates per 10⁸ vehicle-miles for Interstate, other freeways and expressways where the files allow, and the other arterials, with one-sided 95 % bounds from the CRSS standard errors; record each value as §2.1 requires; then replace the illustrative rates of §3.1 and update the derivations. [`tools/severity/`](../../tools/severity/README.md) reads FARS and CRSS but computes no rate over travel, so it needs extending, with its tool classification under WP-P-07. Same download as OI-8; the NHTSA hosts are not reachable from the project's cloud environment. VT-01…VT-15 keep their illustrative values until then, and the freeze (OI-3) stays open |
| OI-3 | Decided 2026-10-19 (DQ-096 option B): the project lead freezes VT-01…VT-15, the derivations of §4.2 and §4.3 and the values marked "approved with the targets" in a dated record, once the B1 data (OI-2) has replaced the illustrative rates; an assessor reviews them later. Open: update the derivations with the B1 data, then the freeze. SOTIF campaigns wait for it |
| OI-4 | Execute the fidelity-case plan of §5.3 (matched M8 points per family, plant constants from VS-VAL-08 and lateral step tests, radar comparison); credit per family once its case is approved (DQ-139 option A). CARLA: not now, revisit at G3 (§5.4, DQ-261 option A) |
| OI-5 | Decided 2026-10-25 (DQ-140 option A; WP-M-08 OI-8 closed): the surrogate set SU-01…SU-03 and its draft arguments are in §4.5; VT-04 counts the hazardous behaviour directly. Open: (a) add the 0 m reading of AS-05 and the time-to-line reading of AS-01 to WP-V-04 §2.1 as a new signature-set version, and to the extractor (`tools/field_monitoring/extract_events.py`), before block B1; (b) check each argument against LionDriver logs as §4.5 requires, once the log store exists (WP-M-08 OI-4). No surrogate rate counts toward a target before (b) |
| OI-7 | Fit the rear-facing camera now listed in the [WP-V-01](WP-V-01-safety-validation.md) §2 equipment (procurement: WP-V-01 OI-6), and annotate following vehicles from its recordings, so that P(E-situation) for SH-04 (following vehicle, OS-08) is measured (§3.4). Blocks driven before it is fitted give no SH-04 data |
| OI-8 | Extract P(severity class) per SH from FARS/CRSS (and injury-risk curves where §3.5 item 3 requires them) for the selected B1 data set (OI-2); record the values and bounds per §3.5 item 4. The extraction tool is [`tools/severity/`](../../tools/severity/README.md); its variable codes must be checked against the NHTSA manual of the release year first. The same download gives the weighted mean age of pedestrians aged 15 and older struck in 2007–2009 (GES person file), which fixes the reference age of the SH-11 age shift (§3.5). Not run yet: the NHTSA download hosts are not reachable from the project's cloud environment |
