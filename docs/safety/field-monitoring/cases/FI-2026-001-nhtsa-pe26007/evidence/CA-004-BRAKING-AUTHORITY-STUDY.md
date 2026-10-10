# CA-004 — Braking Authority Study

| Field | Value |
|---|---|
| Corrective action | CA-004 (FI-2026-001, RC-02) |
| Status | Study complete; **decision pending safety manager approval** |
| Tools | `openpilot/selfdrive/test/stopped_vehicle/` (`braking_authority_study.py`, `emergency_brake.py`, `test_braking_authority.py`) |
| Regenerate | `python openpilot/selfdrive/test/stopped_vehicle/braking_authority_study.py` |
| Harness limits | As in [CA-002 baseline](CA-002-BASELINE-RESULTS.md): idealized perception, perfect actuation after the actuator delay, straight road, no driver, no stock AEB. All results are optimistic. |

## 1. Question

The RCA found that openpilot's braking authority of -3.5 m/s² (opendbc `ACCEL_MIN`, plus the panda Toyota limit) can make collision avoidance impossible once a stopped or slow vehicle is confirmed late. CA-004 asks which control should close that gap:

- **(a)** Keep -3.5 m/s² and require detection early enough (requirement LD-SOTIF-001).
- **(b)** Add an *emergency-only* higher deceleration, gated on high-confidence fused detection and an imminent collision.
- **(c)** Restrict the operating domain (a speed cap for openpilot longitudinal) to what the confirmed detection range supports.

## 2. Method

- The CA-002 closed-loop harness (real `RadarD` and `LongitudinalPlanner` / MPC, Corolla TSS2) was run for each option.
- Option (b) is a **study-only prototype** (`emergency_brake.py`), not wired into openpilot. It triggers only when all of these hold:
  - the lead is confirmed by vision **and** radar;
  - model prob ≥ 0.9;
  - stopping behind the lead needs more than -3.5 m/s².

  It then ramps at 20 m/s³ to -6 or -8 m/s².
- Following-traffic exposure (HZ-007) uses a separate point-mass model (S5).

## 3. Findings

1. **Required confirmation range (S1).** Option (b) at -8 m/s² cuts the range a stopped vehicle must be confirmed at by about half: 166 → 79 m at 120 km/h, and 118 → 58 m at 100 km/h. This is the single biggest lever on RC-02.
2. **Cut-out reveals (S2).** Of the 25 cut-out cases, (a) collides in 11, (b)-6 in 6 and (b)-8 in 5. Where (b) can't avoid the crash, it still lowers the impact speed. Example: 120 km/h revealed at 80 m drops from 88 km/h to 0.
3. **New finding: a lead vehicle braking hard (S3, HZ-008).** At the standard following distance, a lead braking at **4 m/s²**, which is ordinary hard braking and not an emergency, is hit from 100 km/h (14 km/h) and 120 km/h (29 km/h). The ego reaches -3.5 m/s² about 1.5 s after the lead starts braking (lead deceleration is estimated through the radar Kalman filter), and then the lead simply out-brakes it.
   - The **relaxed** following distance removes the 4 m/s² collisions up to 100 km/h (4 km/h at 120 km/h).
   - Only (b)-8 handles lead *emergency* stops: it avoids 6 m/s² stops up to 100 km/h, and cuts an 8 m/s² stop from 100 km/h to 3 km/h contact.
   - This is a new triggering condition, **TC-07**, not in the original RCA. It is kept as an `expectedFailure` test.
4. **Option (c) speed caps (S4).** If the vision confirmation range is 90 m, the highest collision-free speed is 87 km/h under (a), versus 128 km/h under (b)-8. The real confirmation range is **unknown until CA-003 measures it**, so (c) cannot be set yet.
5. **Following traffic (S5, HZ-007).** Braking at -8 m/s² from 100 km/h creates rear-end impacts of up to about 52 km/h, for following drivers with a 1.5 s reaction and short headways (0.8–1.5 s). -3.5 m/s² creates none. But (b) only fires when a frontal collision is otherwise unavoidable. Without it, the ego would hit the obstacle and stop even more abruptly. So the comparison that matters is (b) against a frontal crash, not (b) against a gentle stop.
6. **No nuisance triggers in the scenarios run.** The prototype stayed off in every scenario where -3.5 m/s² was enough: lead braking at ≤ 3 m/s², targets visible from range, and the no-target case. It also stayed off with radar-only targets, by design. **This says nothing about field false-trigger rates (HZ-006)**, which need replay over logged drives.

## 4. What is still unknown, and blocks option (b)

| # | Unknown | Why it matters | How to resolve |
|---|---|---|---|
| U1 | Does the Corolla TSS2 ECU honor `ACC_CONTROL.ACCEL_CMD` below -3.5 m/s²? The DBC encodes ±20 m/s²; ECU behavior is unverified | (b) may be physically impossible through the ACC interface | Bench/closed-course test |
| U2 | How well does the stock PCS/AEB perform in the S2/S3 scenarios **while openpilot longitudinal is engaged**? | The OEM already provides an emergency braking layer, validated by the OEM and kept by CA-001. If it works, (b) duplicates it | Closed-course test (new CA-010) |
| U3 | False-trigger rate of the (b) trigger on real drives | HZ-006 phantom braking at -8 m/s² is a severe hazard | Run the trigger logic over logged drives; target set by the HARA (SPI-06) |
| U4 | Real vision confirmation range by target type and lighting | Sets the (a) requirement and the (c) cap | CA-003 |
| U5 | Integrity level of an openpilot emergency-braking function | (b) makes openpilot an AEB function: panda safety-limit change (opendbc fork), likely higher ASIL, FMVSS 127-style performance expectations | HARA (PA-01), functional safety concept |

**Regulatory context.** FMVSS No. 127 requires AEB to avoid a stopped lead vehicle at up to 100 km/h, with compliance by September 1, 2029. That is the performance bar an emergency layer on public roads is measured against.

## 5. Recommendation (decision proposal)

**Do not adopt option (b) into the product now.** It's the most effective option in simulation, but U1–U3 and U5 are open, and it would duplicate the OEM's emergency layer before that layer has been measured (U2). Instead:

1. **Adopt requirement LD-SOTIF-001** with the simulated values. With openpilot longitudinal engaged, a stopped or slow in-lane vehicle must be confirmed at ≥ 1.2 × D_req(v), where D_req is S1 column (a): 21 / 45 / 76 / 118 / 166 m at 40 / 60 / 80 / 100 / 120 km/h. CA-002 AC-1 already verifies this in SIL.
2. **New CA-011: relaxed following distance by default** in the LionDriver assured configuration. This is a tier 2 control within the current authority, and it removes the TC-07 collisions at 4 m/s² up to 100 km/h (S3).
3. **New CA-010: measure stock PCS** on the 2020 Corolla in the S2/S3 scenarios with openpilot longitudinal engaged, on a closed course with soft targets (resolves U2).
4. **New CA-012: operating-domain speed cap** for openpilot longitudinal, derived from S4 once CA-003 provides the verified confirmation range (U4). Until then, containment C-1 (no openpilot longitudinal above 40 km/h on public roads without the C-2 protocol) stays in force.
5. **Keep option (b) as a candidate.** Reopen it if CA-010 shows stock PCS does not cover S2/S3. Before it could go into the product, U1, U3 and U5 must be resolved.

## 6. Generated results

Generated by `openpilot/selfdrive/test/stopped_vehicle/braking_authority_study.py` at commit `646efd5`, reference car `TOYOTA_COROLLA_TSS2`. Impact speeds in km/h; **bold** = collision.

### S1. Required confirmation range, stopped vehicle (m)

| Ego speed (km/h) | (a) -3.5 m/s² (current) | (b) emergency -6 m/s² | (b) emergency -8 m/s² |
|---|---|---|---|
| 40 | 21 | 13 | 11 |
| 60 | 45 | 27 | 23 |
| 80 | 76 | 47 | 38 |
| 100 | 118 | 72 | 58 |
| 120 | 166 | 100 | 79 |

### S2. Cut-out reveal of a stopped vehicle: impact speed

| Ego speed (km/h) | Reveal gap (m) | (a) -3.5 m/s² (current) | (b) emergency -6 m/s² | (b) emergency -8 m/s² |
|---|---|---|---|---|
| 40 | 30 | 0 | 0 | 0 |
| 40 | 50 | 0 | 0 | 0 |
| 40 | 80 | 0 | 0 | 0 |
| 40 | 120 | 0 | 0 | 0 |
| 40 | 160 | 0 | 0 | 0 |
| 60 | 30 | **35** | 0 | 0 |
| 60 | 50 | 0 | 0 | 0 |
| 60 | 80 | 0 | 0 | 0 |
| 60 | 120 | 0 | 0 | 0 |
| 60 | 160 | 0 | 0 | 0 |
| 80 | 30 | **64** | **51** | **39** |
| 80 | 50 | **48** | 0 | 0 |
| 80 | 80 | 0 | 0 | 0 |
| 80 | 120 | 0 | 0 | 0 |
| 80 | 160 | 0 | 0 | 0 |
| 100 | 30 | **88** | **80** | **73** |
| 100 | 50 | **77** | **57** | **35** |
| 100 | 80 | **57** | 0 | 0 |
| 100 | 120 | 0 | 0 | 0 |
| 100 | 160 | 0 | 0 | 0 |
| 120 | 30 | **111** | **105** | **100** |
| 120 | 50 | **102** | **89** | **77** |
| 120 | 80 | **88** | **56** | 0 |
| 120 | 120 | **64** | 0 | 0 |
| 120 | 160 | **22** | 0 | 0 |

### S3. Lead vehicle brakes to a stop: impact speed

Steady following at the standard personality's distance, plus the current authority at the relaxed distance.

| Ego speed (km/h) | Lead decel (m/s²) | (a) -3.5 m/s² (current) | (b) emergency -6 m/s² | (b) emergency -8 m/s² | (a) at relaxed distance |
|---|---|---|---|---|---|
| 60 | 3 | 0 | 0 | 0 | 0 |
| 60 | 4 | 0 | 0 | 0 | 0 |
| 60 | 6 | **10** | 0 | 0 | 0 |
| 60 | 8 | **20** | 0 | 0 | **4** |
| 100 | 3 | 0 | 0 | 0 | 0 |
| 100 | 4 | **14** | 0 | 0 | 0 |
| 100 | 6 | **48** | **27** | 0 | **40** |
| 100 | 8 | **58** | **39** | **3** | **52** |
| 120 | 3 | 0 | 0 | 0 | 0 |
| 120 | 4 | **29** | 0 | 0 | **4** |
| 120 | 6 | **61** | **44** | **17** | **56** |
| 120 | 8 | **75** | **55** | **34** | **69** |

### S4. Option (c): highest speed without collision for a given confirmation range (km/h)

| Confirmation range (m) | (a) -3.5 m/s² (current) | (b) emergency -6 m/s² | (b) emergency -8 m/s² |
|---|---|---|---|
| 60 | 69 | 91 | 102 |
| 90 | 87 | 113 | 128 |
| 120 | 101 | 131 | 154 |
| 150 | 114 | 152 | 173 |

### S5. Rear-end exposure (HZ-007): impact speed of a following car, ego braking to a stop from 100 km/h

Following driver reacts after 1.5 s, then brakes at 6 m/s² (8 m/s² in brackets). Jerk 20 m/s³ for both.

| Follower headway (s) | Ego -3.5 m/s² | Ego -6 m/s² | Ego -8 m/s² |
|---|---|---|---|
| 0.8 | 0 (0) | 32 (18) | 50 (43) |
| 1.0 | 0 (0) | 32 (0) | 52 (43) |
| 1.5 | 0 (0) | 0 (0) | 48 (0) |
| 2.0 | 0 (0) | 0 (0) | 11 (0) |
