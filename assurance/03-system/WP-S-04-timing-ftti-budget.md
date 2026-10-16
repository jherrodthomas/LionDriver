# WP-S-04 Timing Analysis: FTTI, Fault Detection and Reaction Budget

| Field | Value |
|---|---|
| Work product | WP-S-04 Timing analysis: FTTI, fault detection and reaction budget |
| Standard reference | ISO 26262-4:2018 §6 (fault tolerant time interval, fault detection and fault reaction time intervals, emergency operation); ISO 26262-3:2018 §7 (FTTI as FSC input); ISO 26262-1:2018 (definitions, by reference); ASPICE 4.0 SYS.3 |
| Version | 0.8 (§3.9 added: closed-loop cross-check of §3 and §4 against the fault-injection plant model of `assurance/sim` (synthetic data, no evidence credit); T-34 (TSR-408 command-arrival check) added to §4; §5 row for the full SoC stall, where the fast heartbeat siren never sounds; OI-2 extended below the ODD bound; OI-10 added; no budget changed; 2026-10-16). 0.7 (§3.8 added: FTTI and budgets for the warning paths that had none (insufficient lateral control, late or insufficient braking warning, unintended engagement, driver monitoring), System FMEA SFM-ACT-017; four rows added to §3.7; T-30…T-33 added to §4; kinematic estimates and code-derived times only; 2026-10-16). 0.6 (lead decisions of 2026-10-14 recorded, register DQ-048, DQ-062, DQ-114: EPS-fault warning persistence ≤ 0.7 s, OI-8 decided; SG-07 0.2 s accepted as the working budget; 90 ms watchdog accepted on condition; Figure 5-2 note updated; no code-derived time changed; 2026-10-16). 0.5 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.4 (§5 Figures 5-1 and 5-2 added: timing budgets per safety goal against the code-derived times, and the EPS-fault warning chain of OI-8; generated from §3.7 and §4 by `figures/fig_s04_timing.py`; no number changed; 2026-10-13). 0.3 (status update 2026-10-12: §4 code-derived times for the reference build at `bf6ce8c` (T-01, T-06a/b, T-09a, T-26…T-29), §5 verdicts, OI-8 EPS-fault warning latency; nothing verified on hardware). History: 0.2 (§3.6 preliminary SG-07 FTTI and budget, RR-2026-005 F-02; 2026-10-12) |
| Status | Draft — kinematic estimates and code-derived times, cross-checked in simulation (§3.9, synthetic, not evidence); no measurement has been performed; not reviewed independently |
| ASIL / scope | SG-01 (C until re-rated, B‡), SG-02…SG-07 (B) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `bf6ce8c` (status update 2026-10-12; opendbc `7993399`, panda `b790fca`). Original analysis at `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose

The HARA gives preliminary FTTIs ([WP-C-03 §6](../02-concept/WP-C-03-hara.md)) and the FSC splits them into detection and reaction budgets ([WP-C-04 §8](../02-concept/WP-C-04-functional-safety-concept.md)). This document:

1. defines the method used to derive each FTTI from vehicle dynamics (§2, §3);
2. gives first kinematic estimates, parameterised where vehicle data is missing (§3);
3. lists the detection and reaction times of the baseline code, derived from the source (§4);
4. compares them with the budgets and lists the required changes (§5);
5. specifies how the times will be measured (§6).

It closes GAP-06 at specification level. HARA OI-3 and FSC OI-4 depend on it.

## 2. Definitions and method

| Term | Use in this document |
|---|---|
| FTTI | Time from the occurrence of a fault in the item to the earliest possible occurrence of the hazardous event, if no safety mechanism acts |
| FDTI | Fault detection time interval: fault occurrence → detection |
| FRTI | Fault reaction time interval: detection → safe state reached at the actuator (EPS torque 0, PCM inactive) |
| Budget rule | FDTI + FRTI ≤ FTTI, with a margin of at least 20 % of the FTTI for scheduling jitter, CAN latency and EPS/PCM response |
| Driver reaction t_r | Not part of the FTTI. Used separately for controllability (C class) and for warning budgets (SG-02, SG-06) |

Method per safety goal:

1. Take the worst credible malfunctioning behaviour that the fault class can produce **without** the mechanism under analysis (e.g. EPS at its own LKA authority limit T_EPS when the envelope is defeated; envelope-limited torque when only the detection is missing).
2. Integrate the vehicle response (lateral deviation, gap closure) from fault onset.
3. FTTI = time until the response reaches the hazard threshold (lateral margin to the adjacent lane, minimum safe gap).
4. Split into FDTI and FRTI per mechanism; compare with code-derived and measured times.

Faults whose effect stays inside the envelope limits (e.g. a wrong but limited command from the QM SoC) are handled by the limits acting every frame and by driver controllability; they do not need detection within the FTTI. The FTTI matters for faults that **defeat** a limit or gate: lost or wrong RX data, SoC command path stalls with the EPS holding torque, MCU faults, relay faults.

## 3. FTTI derivation per safety goal

### 3.1 SG-01 lateral (lateral deviation vs time)

Model: lateral acceleration error a_y builds either (i) as a step, (ii) with jerk j = 5 m/s³ (controller jerk limit, `openpilot/selfdrive/controls/lib/drive_helpers.py:9-14`), or (iii) as a linear ramp over 1.0 s, which is the envelope torque rate limit (15 raw/frame → 1500 raw in 100 frames, `opendbc_repo/opendbc/safety/modes/toyota.h:174`; host comment "1.0s time to peak torque", `opendbc_repo/opendbc/car/toyota/values.py:46`). Lateral deviation y(t) is integrated from rest relative to the lane. Speed does not appear because a_y is the input; the speed dependence enters through how much a_y a given torque produces (TSR-102).

Time (s) to reach lateral deviation d:

| d | a_y = 1 m/s² | 2 m/s² | 3 m/s² | 4 m/s² | 5 m/s² | Profile |
|---|---|---|---|---|---|---|
| 0.3 m | 0.77 | 0.55 | 0.45 | 0.39 | 0.35 | step |
| 0.6 m | 1.10 | 0.77 | 0.63 | 0.55 | 0.49 | step |
| 0.9 m | 1.34 | 0.95 | 0.77 | 0.67 | 0.60 | step |
| 0.6 m | 1.19 | 0.97 | 0.91 | 0.90 | 0.90 | jerk 5 m/s³ |
| 0.9 m | 1.44 | 1.14 | 1.05 | 1.03 | 1.03 | jerk 5 m/s³ |
| 0.6 m | 1.56 | 1.22 | 1.06 | 0.97 | 0.90 | 1 s ramp (envelope rate) |
| 0.9 m | 1.81 | 1.40 | 1.22 | 1.11 | 1.03 | 1 s ramp (envelope rate) |

Hazard threshold: the lateral margin from lane centre to the adjacent lane boundary, (lane width − vehicle width)/2. With the Corolla width ≈ 1.78 m (to be confirmed from the reference vehicle record) and the ODD lane widths (2.9–3.9 m, [WP-C-02 §3.1](../02-concept/WP-C-02-odd-and-intended-functionality.md)): 0.56–1.06 m. The design value is **0.6 m** (narrow arterial lane), which is conservative for highways. For comparison, `docs/SAFETY.md:32` cites 0.9 s to 1 m at maximum actuation.

Estimates:

| Fault class | Worst behaviour | a_y assumption | FTTI estimate | Note |
|---|---|---|---|---|
| Envelope defeated (MCU fault, wrong mode, relay fault letting camera/SoC frames through unchecked) | EPS at its own authority T_EPS, step onset | a_y,EPS unknown (AOU-01R); 3–5 m/s² assumed | **0.5–0.6 s** | Supports the preliminary ≤ 0.5 s of the HARA |
| Gate defeated (stale `0x1D2`/`0x226`, authority not revoked), limits intact | envelope-limited torque, 1 s ramp | a_y at τ_max: today unknown; after TSR-102 ≤ target (e.g. 2 m/s²) | 1.2 s at 2 m/s²; 0.9–1.1 s at 3–5 m/s² | Applies to SG-05 too (driver override not honoured) |
| SoC command path stalls with EPS holding last torque | constant a_y at last torque (≤ τ_max) | as above, step from steady state | 0.6–0.8 s at 2–3 m/s² | Only if the EPS holds torque during drop-out (NF-02) |

Conclusion: **FTTI(SG-01) = 0.5 s** is kept as the design value for faults that defeat the envelope; the budget of FSC §8 (detect ≤ 0.3 s, react ≤ 0.1 s, margin 0.1 s) holds. The value must be confirmed once a_y,EPS and τ_max(v) are measured (§6).

### 3.2 SG-02 / SG-06 loss without warning

Hazard: departure (SG-02) or failure to decelerate (SG-06) before the driver takes over. The relevant time is fault → take-over request, plus driver reaction.

| Item | Value | Basis |
|---|---|---|
| Lateral drift when assistance is lost in a curve | Loss of the curvature-holding a_y, up to 2.5–3.0 m/s² at the ODD curve bound (R_ODD = v²/2.5 m/s²) | WP-C-02 §3.2 |
| Time to 0.6 m at 2.5 m/s² step | ≈ 0.69 s | §3.1 kinematics |
| Driver reaction to an acoustic take-over request (attentive, hands near wheel) | 0.75–1.5 s (to be confirmed in [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) §8) | assumption |

The physical time to departure in a curve (≈ 0.7 s) is shorter than driver reaction, so SG-02 in curves at the ODD bound relies on the warning being given at once and on torque being ramped rather than cut (FSR-02.04). **Warning budget: ≤ 0.5 s detection + ≤ 0.5 s to warning (FSC §8) is not sufficient alone for curves at the ODD bound;** it is sufficient on straight roads and gentle curves. This is a controllability and ODD question (OI-2), recorded for the HARA owner. For SG-06 (stationary lead at 30 m/s, decel need 3.5 m/s²), the margin depends on distance; the 1 s budget is kept.

### 3.3 SG-03 unintended acceleration

Gap closure with ego acceleration error a relative to a lead at constant speed: Δs = ½·a·t².

| a | 0.5 s | 1.0 s | 1.5 s | 2.0 s |
|---|---|---|---|---|
| 1.0 m/s² | 0.12 m | 0.50 m | 1.12 m | 2.0 m |
| 2.0 m/s² | 0.25 m | 1.0 m | 2.25 m | 4.0 m |

At typical following gaps (time gap ≥ 1.0 s → ≥ 20 m at 20 m/s) the gap loss within 1 s is ≤ 1 m at the envelope bound (+2.0 m/s²). HE-03.2 (launch toward a pedestrian from standstill) is the governing case: at 2.0 m/s² the vehicle moves 1 m in 1 s. **FTTI(SG-03) = 1 s** is kept; the standstill-launch case should be checked with the actual pedestrian distance assumptions in WP-C-08 (OI-3).

### 3.4 SG-04 excessive deceleration

Following vehicle at time gap h, same speed v, reacting after t_r with equal deceleration: gap reduction ≈ v·t_r (independent of the deceleration level once both brake equally); collision if v·t_r ≥ h·v, i.e. t_r ≥ h. The hazard depends on the follower, not on detection time, so SG-04 is governed by the **deceleration onset limit and magnitude** (TSR-202, TSR-205) rather than by an FTTI for detection. For faults that defeat the bound (e.g. inactive transition step), FTTI(SG-04) = 1 s is kept as preliminary.

### 3.5 SG-05 release on driver action

Requirement-based: the driver expects release within the time of their own action. The HARA sets ≤ 0.2 s from driver input to release. Budget: brake/cruise message period (25–30 ms) + envelope reaction (1 frame) + EPS/PCM response (TBD, AOU-01R/03R). Steering override: driver torque message period (20 ms at 50 Hz) + t_ovr (TSR-304).

### 3.6 SG-07 PCS preservation

SG-07 has two parts with different timing.

- **Content.** The item must not originate or alter a PCS-relevant frame. This is a per-frame property of the TX gate (TSR-705) and the forwarding block list (TSR-704). It has no detection budget: a wrong frame is either never sent or the design is wrong.
- **Forwarding loss or delay.** While the relay intercepts, the stock camera frames that carry the PCS request reach the car only through the safety MCU. If forwarding stops (MCU hang, camera-side bus fault, a QM configuration command, queue overflow; WP-A-04 §8), the PCS braking request is delayed until the fault is detected and the relay returns the stock path. This part needs an FTTI.

Hazard: the stock PCS brakes later than it would without the item, so less speed is removed before impact. If braking starts d seconds late and would otherwise have continued until impact, the speed reduction lost is at most a_PCS · d.

| Item | Value | Basis |
|---|---|---|
| PCS braking deceleration a_PCS | ≈ 6 m/s² (assumed full PCS braking on dry road) | assumption A-PCS-1, to be measured (§6) |
| Speed reduction lost for d = 0.2 s | 6 × 0.2 = 1.2 m/s ≈ 4.3 km/h | kinematics |
| Speed reduction lost for d = 0.5 s | 3.0 m/s ≈ 10.8 km/h | kinematics |
| PCS message period on the camera-side bus | not known | to be measured from drive logs (§6, OI-4) |
| Relay drop-out time after the coil is released | ≈ 10–20 ms for typical automotive relays | assumption A-PCS-2; datasheet (WP-H-02) |

**Preliminary FTTI(SG-07, forwarding loss) = 0.2 s.** A delay of 0.2 s removes at most about 4 km/h of the speed reduction the stock PCS would achieve, which is small next to the reductions an AEB function is designed for. A delay of 0.5 s or more (10 km/h or more) is not. This is engineering judgement on assumed values, recorded so the budget can be checked. It is replaced once the PCS braking profile and message timing are measured on the reference vehicle and the acceptable loss is agreed in the HARA review. *Decided 2026-10-14 (register DQ-062):* the project lead accepted 0.2 s as the working budget until it is measured, with the zero margin of OI-7.

Budget: **FDTI ≤ 0.1 s** to detect that forwarding has stopped (forwarding supervision, TSR-711; MCU hang through the hardware watchdog, TSR-501) and **FRTI ≤ 0.1 s** to release the relay (TSR-706) including relay drop-out.

Consequences for the TSRs:

- TSR-501 set the watchdog timeout to ≤ 0.2 s, which fits SG-01 (0.5 s) but not the SG-07 FDTI of 0.1 s. WP-S-02 v0.3 tightens it to ≤ 0.1 s. The alternative, releasing the relay by another path on an MCU hang, is open in WP-H-01 (HWSR-502). *Status 2026-10-12:* the IWDG is implemented with a 90 ms nominal timeout (reload 719, panda `b790fca`, T-09a); whether it stays ≤ 0.1 s depends on the LSI tolerance (watchdog impact record OI-2), so the zero margin of OI-7 is not yet shown. *Decided 2026-10-14 (DQ-114):* the 90 ms watchdog replaces the two interim SG-07 residuals once the independent reviewer has checked it and the LSI tolerance; until then the residuals stay in the safety case.
- TSR-706 releases the relay ≤ 0.1 s after the fault reaction. That fits the FRTI.
- TSR-707 (forwarding latency ≤ 1 ms in normal operation) is far inside the budget.
- No TSR detected that forwarding has stopped. TSR-711 is added in [WP-S-02](WP-S-02-technical-safety-requirements.md) v0.3.

### 3.7 Summary of FTTIs and budgets

| SG / fault class | FTTI | FDTI budget | FRTI budget | Margin |
|---|---|---|---|---|
| SG-01 continuous limits | per frame | 0 | ≤ 10 ms (+ TSR-109) | — |
| SG-01 RX loss/corruption | 0.5 s | ≤ 0.2 s (TSR-401) | ≤ 0.1 s | ≥ 0.2 s |
| SG-01 SoC heartbeat loss | 0.5 s | ≤ 0.3 s (TSR-407) | ≤ 0.1 s | ≥ 0.1 s |
| SG-01 SoC command stall | 0.5 s | ≤ 0.05 s (TSR-408) | ≤ 0.1 s | ≥ 0.35 s |
| SG-01 MCU execution fault | 0.5 s | ≤ 0.1 s (TSR-501; set by SG-07; 90 ms nominal implemented, T-09a) | ≤ 0.1 s (reset + relay release) | ≥ 0.3 s |
| SG-01 relay stuck | 0.5 s | ≤ 0.3 s (TSR-506) | ≤ 0.1 s | ≥ 0.1 s |
| SG-02/06 loss without warning | 1 s to warning | ≤ 0.5 s | ≤ 0.5 s | — (see §3.2). EPS-fault siren of the reference build ≤ 1.26 s worst case from fault onset exceeds this row (T-28, OI-8). Heartbeat-loss siren ≈ 0.56 s after the last heartbeat, within this row (T-07a, all builds since panda `c33343b`; 2026-10-13). *2026-10-14 (DQ-048):* persistence to be shortened to ≤ 0.7 s, which gives ≤ 0.7 s + 10 ms + 250 ms ≈ 0.96 s from fault onset; firmware not yet changed |
| SG-03/04 | 1 s | ≤ 0.5 s | ≤ 0.3 s | ≥ 0.2 s |
| SG-05 brake/cancel | 0.2 s | ≤ 30 ms | ≤ 10 ms + EPS/PCM | TBD |
| SG-05 steering override | 0.2 s | ≤ 40 ms + t_ovr | ≤ 0.1 s | TBD |
| SG-07 content (TX gate, block list) | per frame | 0 | — | — |
| SG-07 forwarding loss | 0.2 s (preliminary, §3.6) | ≤ 0.1 s (TSR-711; MCU hang: TSR-501 ≤ 0.1 s, 90 ms nominal implemented, T-09a) | ≤ 0.1 s (TSR-706, incl. relay drop-out) | 0 (depends on LSI tolerance, OI-7) |
| SG-02 insufficient lateral control (warning path, §3.8.1) | 1.1 s to 0.6 m at a 1 m/s² deficit; 1.55 s at 0.5 m/s² | ≤ 0.4 s (steerSaturated, T-30) | ≤ 0.1 s to alert | driver needs t_r = 0.75–1.5 s after the alert: met at ≤ 0.5 m/s² deficit, **not met** at 1 m/s² |
| SG-06 late or insufficient braking warning (FCW, §3.8.2) | 1.6 s at 1.0 s time gap; 3.2 s at 1.5 s (lead braking 6 m/s², item limited to 3.5 m/s²) | FCW onset after the lead brakes (T-31, not derived) | ≤ 0.1 s to alert | FCW needed ≤ 0.6 s after lead braking at 1.0 s gap with t_r = 1.0 s; to be measured |
| SG-01 / SG-03 unintended engagement (System FMEA SG-008, §3.8.3) | 0.5 s (as SG-01) | per frame (TSR-105, TSR-301); latent panda authority while disengaged ≤ 0.3 s (TSR-630, T-32) | ≤ 0.1 s | ≥ 0.1 s |
| Driver monitoring (unresponsive driver, H-09 proposed, §3.8.4) | not defined until the H-09 goal exists (DQ-205) | DM invalid → take-over request ≤ 2 s (TSR-609); terminal alert at 13 s vision / 25 s wheel-touch (T-24) | reaction ≤ 5 s after the terminal alert (TSR-633, T-33) | TBD |

### 3.8 Warning paths without a fault reaction (System FMEA SFM-ACT-017)

The System FMEA (FMEA-MSR, [msr-plan.md](../08-analyses/fmea/msr-plan.md)) credits several warnings whose time budget was not defined here, so their monitoring rating could not be compared with a time. This section gives each a budget. In all four the hazard is avoided by the driver after a warning, so the budget is the time from onset to the warning, and the remaining time must cover the driver reaction t_r = 0.75–1.5 s (§3.2; WP-C-08 §8 to confirm).

#### 3.8.1 Insufficient lateral control (SG-02; SFM-004.C1…C3)

The controller or the envelope limits the torque below what the curve needs (torque bound, EPS limit, weak tuning). The lateral acceleration deficit Δa_y acts as a step; the deviation follows the §3.1 step profile.

| Δa_y | Time to 0.6 m | Latest warning for t_r = 1.0 s | Latest warning for t_r = 1.5 s |
|---|---|---|---|
| 0.5 m/s² | 1.55 s | 0.55 s | 0.05 s |
| 1.0 m/s² | 1.10 s | 0.10 s | not possible |

`steerSaturated` is raised when saturation has lasted `steerLimitTimer` = 0.4 s for the Corolla (T-30). It warns in time only at a deficit of about 0.5 m/s² or less, and only for a fast driver. At the ODD curve bound the full envelope torque gives about 1.99 m/s² (openpilot torque model, `opendbc_repo/opendbc/car/torque_data/params.toml`, `LAT_ACCEL_FACTOR`), against 2.5–3.0 m/s² needed (§3.2), so a deficit of 0.5–1.0 m/s² is credible. This is the same ODD question as OI-2 and is not resolved by a faster warning alone.

#### 3.8.2 Late or insufficient braking warning (SG-06; SFM-010.C2, C3, SFM-012.C1)

The item cannot brake harder than a_min = −3.5 m/s² (TSR-202), so a lead that brakes harder must be handled by the driver after the forward collision warning. Kinematics: both vehicles at v₀ with time gap h, lead braking at 6 m/s², the item braking at 3.5 m/s² from 0.3 s, actuator lag 0.2 s, the driver adding braking to 6 m/s² at time t_d. The latest t_d that avoids impact (bisection on a 1 ms integration):

| v₀ | h = 1.0 s | h = 1.5 s |
|---|---|---|
| 20 m/s | 1.68 s | 3.77 s |
| 30 m/s | 1.61 s | 3.20 s |

With t_r = 1.0 s the FCW must sound within about 0.6 s of the lead's braking onset at a 1.0 s gap, and within 2.2 s at 1.5 s. The FCW onset of the planner and model triggers (`selfdrive/selfdrived/selfdrived.py:440-445`) is not derived from the code here (T-31); it is to be measured (M-12).

#### 3.8.3 Unintended engagement (System FMEA SG-008; SFM-013.C1, C2)

Actuation without a driver engagement is refused per frame by the envelope gate (TSR-105, TSR-301), so the FTTI of SG-01 (0.5 s) applies only to a latent fault of that gate. A panda that reports authority while the item is disengaged is detected by the host within ≤ 0.3 s (TSR-630, T-32), which leaves ≥ 0.1 s after the ≤ 0.1 s reaction.

#### 3.8.4 Driver monitoring (unresponsive driver; SFM-022.C3, SFM-025.C1)

The hazard is an engaged item with nobody supervising it. The lead decided on 2026-10-14 (DQ-205) that this becomes hazard H-09 with an ASIL A goal; its FTTI is set with that goal by the HARA owner and is not estimated here. The timing that exists: DM escalation reaches the terminal alert after 13 s (vision) or 25 s (wheel-touch) of inattention (T-24), DM invalid output must give a take-over request within 2 s (TSR-609), and the terminal reaction (TSR-633) must start within 5 s of the terminal alert (T-33). These three are the rows to compare once the H-09 FTTI exists.

### 3.9 Cross-check in simulation (synthetic data, not evidence)

The fault-injection plant model of [`assurance/sim`](../sim/README.md) runs the real envelope code in a closed loop: opendbc `libsafety` (reference build, Toyota mode, parameter 73), the panda heartbeat monitor, both sirens and the IWDG feed. Around it are a single-track Corolla model, an EPS and PCM lag, a stand-in SoC controller and a driver model. Its results are in [`plant-results.md`](../sim/results/plant-results.md). The conditions are 120 km/h, a 1.5 m/s² curve inside the ODD and a driver t_r = 1.5 s. The EPS has two frame-loss assumptions: *release*, which drops LKA torque 30 ms after the last frame, and *hold*, which keeps it 2 s (T-23).

**These results are synthetic.** The model is not validated against Corolla logs, so they earn no evidence credit (DQ-139, WP-V-02 §5.3). They do not replace a kinematic estimate or a code-derived time in this document. They show where an estimate is optimistic or pessimistic, and which measurement decides the outcome. Both values are kept side by side.

| Item | This document | Simulation (EPS release unless stated) | Reading |
|---|---|---|---|
| §3.1 step, assistance lost in a 1.5 m/s² curve: time to the lane line, 3.0 / 3.7 m lane | 0.90 / 1.13 s | 1.27–1.38 / 1.51–1.62 s (F-01a, F-04b, F-05, F-06a, F-07, F-08); with EPS hold 3.14–3.49 s | The kinematic estimate is conservative by about 0.4 s: the EPS lag and the vehicle response delay the drift. The lane line is still reached before a 1.5 s driver correction, so this extends OI-2 below the ODD bound |
| §3.1 1 s ramp at 1.99 m/s² (hard-over within the envelope), 3.0 / 3.7 m lane | 1.23 / 1.44 s | 1.57 / 1.80 s (F-01b) | Conservative by about 0.35 s. The driver cue is drift only, at 1.17 s |
| SG-01 FTTI 0.5 s (§3.1, §3.7) | 0.5 s | Deviation at 0.5 s ≤ 0.03 m in every case | For these fault classes the hazard threshold is not reached within 0.5 s. The 0.5 s design value is conservative for envelope-limited torque. It is kept for faults that defeat the envelope (§3.1, a_y,EPS unknown) |
| T-01 RX timeout, `0x260` | ≤ 0.16 s | Revoked 0.083 s after the last frame (F-08) | Consistent |
| T-06a heartbeat revocation | ≤ 0.31 s after the last heartbeat | 0.193 s after the fault, which is within 0.3 s of the last heartbeat (F-04a) | Consistent |
| T-07a heartbeat siren | ≈ 0.56 s after the last heartbeat | 0.25 s after the fault (F-04a) | Consistent, **but only when commands continue**: see T-34 |
| T-09a IWDG | ≈ 90 ms nominal | Reset 83 ms after the hang, 90 ms after the last feed (F-05) | Consistent |
| T-28 EPS-fault siren | ≤ 1.26 s worst case | 1.00 s at the simulated speaker phase (F-07) | Consistent (phase-dependent) |
| T-34 command-arrival revocation (new) | — | Revoked 0.043 s after a full SoC stall (F-04b); no siren | New §4 row. The 0.3 s heartbeat check does not fire because authority is already revoked, so T-07a does not sound (§5) |
| §3.3 gap loss in 1 s at +2.0 m/s² | 1.00 m | 0.75 m (L-01) | Conservative (PCM lag) |
| §3.4 follower collision if t_r ≥ h | rule | No collision at h = 1.0 s (L-03) | Not a test of the rule: the ego driver ends the deceleration at 1.55 s |
| §3.8.1 saturation at the ODD curve bound | 0.5–1.0 m/s² deficit is credible | Saturated at R_ODD; 0.80 m drift; 3.0 m lane line reached 3.71 s after curve entry (N-3) | Supports §3.8.1 and OI-2 |

Faults that the envelope does not report, so no warning comes from the item (§5):
- **Over-limit torque (F-01a):** refused frame by frame while authority stays granted. TSR-108 latching (DQ-060) and the TSR-516(b) siren on a rejected command are not implemented.
- **Frozen command (F-03):** not detected. TSR-631 is not implemented.

**EPS frame-loss behaviour decides most outcomes** (release about 1.3–1.5 s to the line, hold about 3.1–3.5 s). Measurement M-02 is therefore the first measurement to make (OI-10).

## 4. Current detection and reaction times (code-derived)

| # | Mechanism | Code | Derivation | Worst-case time |
|---|---|---|---|---|
| T-01 | RX timeout | `opendbc_repo/opendbc/safety/safety.h:321-344`; called at 1 Hz from `panda/board/main.c:241-242` | threshold max(10 × period, 1 s); for the Corolla messages 10 × period is 120 ms (`0xAA` 83 Hz), 200 ms (`0x260` 50 Hz), 303 ms (`0x1D2` 33 Hz), 250 ms (`0x226` 40 Hz), so 1 s applies; evaluated once per second | **1–2 s** (at `8b8c6ae`). *Status 2026-10-12:* 5 nominal periods (`rx_timeout_periods`, opendbc `de80b63`), evaluated by the 100 Hz safety task (panda `171fcdf`): **≤ 0.16 s** for `0x1D2`; the reference build adds `0x262` (25 Hz, ≈ 0.21 s, slightly above TSR-401's 0.2 s if the real rate is 25 Hz) and `0x1D3` (33 Hz, ≈ 0.16 s) (opendbc `21d8dd8`). Not verified on hardware |
| T-02 | RX checksum / quality | `safety.h:112-121, 164-197` | on receipt | 1 message period (12–30 ms) |
| T-03 | RX counter | — | no Toyota counters (`modes/toyota.h:39-46`) | not detected |
| T-04 | Brake / cruise revoke | `safety.h:350-356, 518-527` | on receipt | 25 ms (brake 40 Hz), 30 ms (cruise 33 Hz) |
| T-05 | Heartbeat engaged mismatch | `panda/board/main.c:181-189` | 3 consecutive 1 Hz ticks | **2–3 s** |
| T-06 | Heartbeat loss → SILENT | `main.c:101-103, 153-162, 191-213` | counter +1 per 1 Hz tick, reset by each `0xf3`; ≥ 5 with ignition, ≥ 2 without | **4–5 s** (ign on), 1–2 s (ign off) (at `8b8c6ae`; split into T-06a/T-06b below) |
| T-06a | Heartbeat loss → authority revoked (added 2026-10-12) | `panda/board/drivers/heartbeat_monitor.h`; `main.c` `safety_task_handler` (panda `b87197f`, pin `c2e5d93`) | 100 Hz safety task counts ticks since the last `0xf3`; in a car mode clears `controls_allowed` at 30 ticks | **≤ 0.31 s** (0.3 s + one task period). Not verified on hardware |
| T-06b | Heartbeat loss → SILENT (2026-10-12) | as T-06 | unchanged | 4–5 s (ign on), 1–2 s (ign off); TSR-510 (SILENT ≤ 2 s) not met |
| T-07 | Siren after heartbeat loss | `main.c:169-171, 198-201` | 3 s siren if authority within last 5 s | starts at T-06 |
| T-07a | Siren when heartbeat loss revokes granted authority (added 2026-10-13) | `panda/board/drivers/heartbeat_siren.h`; `main.c` `safety_task_handler` and `tick_handler` (panda `7dd0c4b`, pin `c33343b`; all builds) | when the T-06a revocation in a car mode finds `controls_allowed` set, the 100 Hz safety task requests the siren at once for 3 s (300 ticks); none if authority was not granted at that moment; the 8 Hz tick drives the speaker only on every other tick (`set_siren((loop_counter & 1U) && ...)`), so it sounds within 2 × 125 ms of the request; the T-07 path is unchanged | siren ≤ 0.3 s + 10 ms + 250 ms ≈ **0.56 s** after the last heartbeat (≤ 0.26 s after the T-06a detection) (TSR-516(a), and (b) for this revocation). T-07 (4–5 s) still sounds when it fires and alone covers authority that ended within the 5 s before the loss (OI-9). Not verified on hardware |
| T-08 | Relay malfunction | `safety.h:372-380` | first offending frame after `safety_mode_cnt > 1` (1 Hz) | 1–2 s after mode set; then immediate |
| T-09 | Software watchdog | `panda/board/drivers/simple_watchdog.h`; `main.c:119, 301` | 375 ms threshold, checked from the 8 Hz tick it supervises | cannot detect a tick-ISR hang |
| T-09a | Hardware watchdog IWDG1 (added 2026-10-12) | `panda/board/drivers/hw_watchdog.h` (PR /4, RLR 719, WINR 679); fed from `safety_task_handler` (panda `171fcdf`, `a35d1c6`) | timeout 4 × (719 + 1) / f_LSI ≈ 90 ms nominal; window: a feed earlier than ≈ 5 ms after the previous one resets; fed by the 100 Hz task only after main-loop progress; started at the first relay drive after reset | **≈ 90 ms** nominal; ≤ 0.1 s only if the LSI is at most 10 % slow (watchdog impact record OI-2). Hangs before the first relay drive not covered. Not verified on hardware (M-06) |
| T-10 | Heartbeat send rate | `openpilot/selfdrive/pandad/pandad.cc:385-394` | every 10th frame of the 100 Hz loop | 100 ms period |
| T-11 | `sendcan` age limit | `pandad.cc:78-79` | logMonoTime age | 1 s |
| T-12 | SPI ACK timeout | `openpilot/selfdrive/pandad/spi.cc:30, 216, 246` | 500 ms per wait, retries until > 5 timeouts | up to seconds |
| T-13 | `card` sends only if `carControl` alive | `openpilot/selfdrive/car/card.py:234-238` | 10 × 10 ms | 0.1 s |
| T-14 | Inter-process alive | `openpilot/cereal/messaging/__init__.py:265` | 10 × period | 0.1 s (100 Hz), 0.5 s (20 Hz: `modelV2`, `longitudinalPlan`, `radarState`, DM) |
| T-15 | Frequency check | `cereal/messaging/__init__.py:152-153` | average rate outside 0.8–1.2 × nominal over moving windows of 1–10 s | ≈ 1–10 s |
| T-16 | Soft disable | `openpilot/selfdrive/selfdrived/state.py:7` | actuation continues during countdown | **3 s** (+ up to 0.5 s alive window = 3.5 s) |
| T-17 | `controlsMismatch` (panda vs host authority) | `selfdrived.py:338, 503-510` | 200 cycles at 100 Hz | 2 s |
| T-18 | Safety mode/param mismatch | `selfdrived.py:331-339` | only after 10 s from start | 10 s after start |
| T-19 | `cruiseMismatch` | `selfdrived.py:420-422`; `events.py:458-460` | 6 s; no reaction | not reacted |
| T-20 | `selfdrivedLagging` / Ratekeeper | `openpilot/common/realtime.py:72-74`; `selfdrived.py:134` | average dt over 100 samples > period/0.9 | ≈ 1 s averaging |
| T-21 | Excessive actuation | `selfdrive/selfdrived/helpers.py:12` | 0.25 s persistence | 0.25 s |
| T-22 | Big-model diagnostic masking | `selfdrived.py:382-384` | masked during load + 5 s | up to 5 s blind (GAP-17) |
| T-23 | EPS drop-out handling (vehicle) | comment `opendbc_repo/opendbc/car/toyota/carstate.py:15-16` | LKA_STATE 9 → 11 over ≈ 2 s, then 3 | ≈ 2 s (unverified, AOU-01R) |
| T-24 | DM escalation | `selfdrive/monitoring/policy.py:31-36, 39` | vision 5/8/13 s; wheel-touch 5/15/25 s; +5 s at alert 3 → force decel | per policy |
| T-25 | Host steering fault hysteresis | `selfdrive/car/car_events.py` (onboard review) | 1.5 s | 1.5 s |
| T-26 | Cruise active with main off (reference build, added 2026-10-12) | `opendbc_repo/opendbc/safety/modes/toyota.h` (`TOYOTA_CRUISE_MAIN_TOLERANCE_US`, opendbc `8836b65`) | CRUISE_ACTIVE (`0x1D2`) becoming active while MAIN_ON (`0x1D3`) is 0: refused on receipt; main going off while engaged: revoked once the disagreement lasts > 150 ms | refuse at once; revoke after 150 ms (+ one 30 ms frame) (TSR-405(c)). Not verified on hardware |
| T-27 | TX rate supervision (reference build, added 2026-10-12) | `opendbc_repo/opendbc/safety/safety.h` `tx_rate_check` (opendbc `951b459`) | per-ID sliding 250 ms window; 3 rejections while controls are allowed revoke | revoke ≤ 0.1 s after the first rejected frame (≤ 0.2 s from onset at 2× the rate; unit tests) (TSR-518). Not verified on hardware |
| T-28 | EPS fault (reference build, added 2026-10-12) | `modes/toyota.h` (opendbc `338f5fc`); `panda/board/drivers/eps_fault_siren.h` (panda `6a7f2fb`) | LKA_STATE fault codes on `0x262`: STEERING_LKA with torque refused from the receipt of the fault frame; siren once the fault has persisted 1 s (100 ticks) while `controls_allowed`, driven by the 8 Hz speaker tick on every other tick | LKA refused on receipt of the fault frame (TSR-110); siren ≤ 1 s + 10 ms + 2 × 125 ms ≈ **1.26 s** after fault onset worst case (TSR-516(b)); exceeds the SG-02 1 s warning row (OI-8). Corrected 2026-10-13 from ≈ 1.14 s: the speaker sounds only on every other 8 Hz tick. Not verified on hardware |
| T-30 | Controller saturation warning `steerSaturated` (added 2026-10-16) | `openpilot/selfdrive/controls/lib/latcontrol.py:8, 22-29`; `opendbc_repo/opendbc/car/toyota/interface.py:50` | saturation time accumulates to `steerLimitTimer` = 0.4 s (LKA torque cars) | 0.4 s + 1 frame |
| T-31 | Forward collision warning (added 2026-10-16) | `selfdrive/selfdrived/selfdrived.py:440-445` | model `hardBrakePredicted` or planner FCW | not derived; measure (M-12) |
| T-32 | Host check of panda authority while disengaged (added 2026-10-16) | — | not implemented (TSR-630) | not detected |
| T-33 | Terminal DM reaction (added 2026-10-16) | `selfdrive/monitoring/policy.py:39, 398`; `selfdrive/controls/controlsd.py:235` | forced deceleration 5 s after the terminal alert; no disengagement | 5 s to deceleration; no safe state (TSR-633) |
| T-34 | SoC command arrival (TSR-408; reference build, added 2026-10-16) | `opendbc_repo/opendbc/safety/safety.h` `tx_arrival_ok`, `modes/toyota.h` (opendbc `273f44e`) | while authority is granted, the 100 Hz safety task revokes it when `0x2E4` has not reached the TX hook for > 50 ms or, with openpilot longitudinal, `0x343` for > 100 ms | ≤ 0.06 s for `0x2E4`, ≤ 0.11 s for `0x343` (one task period added). Runs in the safety task **before** the heartbeat check (`main.c` `safety_task_handler`), so in a full SoC stall it revokes first and T-07a does not sound. Simulated 0.043 s (§3.9). Not verified on hardware |

## 5. Comparison and required changes

| Fault class | Budget | Baseline | Verdict | Required change | TSR |
|---|---|---|---|---|---|
| RX loss | ≤ 0.2 s | 1–2 s (T-01) | **Not met** at `8b8c6ae`. *2026-10-12:* Met by design for the Toyota RX set (`0x262` marginal, ≈ 0.21 s), not verified (M-04) | 5 periods, evaluation ≥ 50 Hz (move timeout check out of the 1 Hz path) | TSR-401 |
| RX stuck/inserted | ≤ 0.2 s | not detected (T-03) | **Not met** | rate, frozen-content, cross-checks | TSR-403…405 |
| SoC heartbeat loss | ≤ 0.3 s | 4–5 s (T-06) | **Not met** at `8b8c6ae`. *2026-10-12:* Revoke met by design (T-06a, ≤ 0.31 s; M-05 pending); SILENT ≤ 2 s not met (T-06b, TSR-510) | evaluate at ≥ 10 Hz; revoke at 0.3 s; SILENT ≤ 2 s | TSR-407, 510 |
| SoC heartbeat loss → warning (added 2026-10-13) | warning within SG-02 1 s (§3.7) | siren at T-06: 4–5 s (T-07) | **Not met** at `8b8c6ae`. *2026-10-13:* Met by design in all builds when authority was granted at the revocation (T-07a, ≤ 0.56 s); not verified (M-05). Authority that ended within the 5 s before the loss: 4–5 s (T-07) | decide on the T-07 case (OI-9) | TSR-516, 407 |
| Host/panda mismatch | ≤ 0.3 s | 2–3 s (T-05), 2 s (T-17) | **Not met** | 0.3 s both sides | TSR-307 |
| SoC command stall | ≤ 0.05 s | 0.1 s at host (T-13), then EPS ≈ 2 s (T-23) | **Not met** | command-frame freshness in the MCU + active zero frame | TSR-408, 109 |
| MCU hang | ≤ 0.1 s | not detected (T-09) | **Not met** at `8b8c6ae`. *2026-10-12:* Met by design if the LSI tolerance holds (T-09a, ≈ 90 ms; watchdog impact record OI-2); M-06 pending | IWDG | TSR-501 |
| Relay stuck released | ≤ 0.3 s | 1–2 s window (T-08) | **Not met** | readback | TSR-506 |
| Brake / cancel | ≤ 30 ms | 25–30 ms (T-04) | Met (envelope side) | verify EPS/PCM response; TSR-109 | TSR-302, 109 |
| Steering override | ≤ 0.2 s | not in envelope | **Not met** | driver-torque monitor | TSR-304 |
| Stale SoC inputs | ≤ 0.2 s actuation on failed input | 3–3.5 s (T-14 + T-16) | **Not met** | immediate disable for untrusted inputs; freshness in controlsd | TSR-601, 602 |
| Diagnostic masking | none while engaged | 5 s (T-22) | **Not met** | remove masking / exclude E-06 | TSR-603 |
| Cruise mismatch | ≤ 1 s with reaction | 6 s, no reaction (T-19) | **Not met** | 1 s, warn + cancel | TSR-308 |
| `sendcan` age | ≤ 20 ms | 1 s (T-11) | **Not met** | 20 ms | TSR-614 |
| Take-over request | ≤ 1 s after detection | alerts immediate; timing unverified | To verify | measure | TSR-606 |
| Cruise active with main off (added 2026-10-12) | ≤ 0.2 s | refuse at once; revoke after 150 ms (T-26) | Met by design (reference build), not verified | — | TSR-405(c) |
| SoC TX rate above budget (added 2026-10-12) | revoke | ≤ 0.1 s after first rejected frame, ≤ 0.2 s from onset at 2× (T-27) | Met by design (reference build), not verified; budgets to be confirmed on logs | — | TSR-518 |
| EPS fault (added 2026-10-12) | LKA refused; warning within SG-02 1 s (§3.7) | LKA refused on receipt; siren ≤ 1.26 s worst case after onset (T-28) | Refusal met by design (reference build); **warning latency exceeds the 1 s budget** (OI-8); not verified | persistence ≤ 0.7 s (DQ-048): siren ≤ 0.96 s from onset | TSR-110, 516 |
| Full SoC stall → warning (added 2026-10-16) | warning within SG-02 1 s (§3.7); TSR-516(b) | revoke ≤ 0.06 s (T-34); fast siren does not sound because authority is already revoked when the heartbeat check fires; 1 Hz siren at 4–5 s (T-07) | **Not met** in all builds since opendbc `273f44e` (code-derived, confirmed in simulation, §3.9); not verified | sound the siren on a T-34 revocation, as TSR-516(b) already requires for any revocation that is not a driver action | TSR-516, 408 |

![Figure 5-1: timing budgets per safety goal (FDTI, FRTI, margin, FTTI) for SG-01, SG-02/06, SG-03/04, SG-05 and SG-07, with the code-derived times T-01, T-04, T-06, T-06a, T-07, T-07a, T-08, T-09, T-09a, T-13, T-23 and T-28 for the baseline and the reference build](figures/fig-s04-5-1-timing-budgets.svg)

*Figure 5-1.* Budgets of §3.7 and code-derived times of §4 on one linear time axis from fault onset (0–1.2 s; longer times are clipped and given in the right column). Grey is the original baseline `8b8c6ae`, amber the reference build `bf6ce8c` (implemented, not verified on hardware); red marks the part of a time beyond its budget. The amber heartbeat-loss siren time (T-07a) is from panda `c33343b` (2026-10-13), in all builds. Nothing has been measured (§6). The four warning-path rows added to §3.7 in v0.7 (§3.8) are not drawn. Drawn from §3.7 and the T-xx rows of §4 by [`figures/fig_s04_timing.py`](figures/fig_s04_timing.py), which fails `--check` when a source value changes. Source: [`figures/fig-s04-5-1-timing-budgets.svg`](figures/fig-s04-5-1-timing-budgets.svg); change it together with §3.7, §4 and §5.

![Figure 5-2: EPS-fault warning chain T-28 — LKA refused on the first fault frame, 1 s persistence, up to 10 ms task period and up to 250 ms to the next sounding speaker tick, siren at up to 1.26 s against the SG-02 1 s warning budget](figures/fig-s04-5-2-eps-fault-warning.svg)

*Figure 5-2.* The T-28 chain of the reference build drawn to scale, with the two ways of measuring it that OI-8 weighed (decided 2026-10-14, DQ-048: shorten the persistence to about 0.7 s): from fault onset (≤ 1.26 s worst case, over the §3.7 SG-02 row) and from detection as WP-S-02 v0.14 defines it (≤ 0.26 s, within TSR-516(b)). Upper bounds; the speaker sounds only on every other 8 Hz tick (corrected 2026-10-13 from ≈ 1.14 s); not verified on hardware. Generated by the same script from T-28. Source: [`figures/fig-s04-5-2-eps-fault-warning.svg`](figures/fig-s04-5-2-eps-fault-warning.svg); change it together with §4 T-28, §5 and OI-8.

Implementation note: the panda tick handler runs at 8 Hz and the safety checks are "decimated to 1 Hz" (`main.c:105-106, 142-143`). The required budgets need a periodic safety task of at least 50 Hz (TSR-401) on a timer independent of the comms interrupts, with its completion feeding the IWDG service point (TSR-501). The architectural change is recorded in [WP-W-03](../05-software/WP-W-03-software-architecture.md).

*Status 2026-10-12:* since panda `9f60e17` a 100 Hz safety task on TIM4 runs `safety_tick()`, the heartbeat monitor, the EPS-fault siren timer and the IWDG feed (`main.c` `safety_task_handler`). All interrupts are at one priority level (`irq_priorities.h`, panda `52cad44`), so the task can be delayed by other handlers; its latency under load is not measured ([WP-W-03](../05-software/WP-W-03-software-architecture.md) §5.4.5). *2026-10-13:* the safety task also runs the heartbeat-loss siren timer (panda `c33343b`, T-07a). The 8 Hz / 1 Hz tick keeps the SILENT transition (T-06b), the engaged-mismatch check (T-05) and the relay grace counter (T-08).

Additional timing requirements from other work products:

| Source | Requirement | Status here |
|---|---|---|
| [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) AIR-17 | Model inference ≤ 50 ms per frame; output older than 100 ms not used for actuation (TBC from WP-S-04) | Consistent with TSR-602 (≤ 2 periods = 100 ms at 20 Hz). Inference time to be measured (§6, M-09) |
| AIR-12 / AIR-26 | 2 s of valid outputs after (re)initialisation before actuation | Accepted; affects start-up only |
| AIR-27 | DM output invalid > 2 s → take-over alert | Adopted as TSR-609 |

## 6. Measurement plan

No measurement has been performed. Results tables are templates.

| ID | What | Method | Setup | Pass criterion |
|---|---|---|---|---|
| M-01 | EPS torque authority and a_y vs raw request and speed | Steady-state circular / step-steer tests on a closed course; log `0x2E4`, `0x260`, IMU | Reference vehicle, [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) | Data set for TSR-102 table and §3.1 a_y,EPS |
| M-02 | EPS behaviour on `0x2E4` drop-out and on zero-torque frame | Stop/zero frames at controlled torque; measure wheel torque decay | Vehicle on lift (wheels free) then closed course | t_EPS; decides TSR-109 option (a)/(b) |
| M-03 | PCM response to inactive value and cancel | Inject step from −3.5 m/s² to inactive; cancel bit | Closed course | Jerk within TSR-205 bound (AOU-05R) |
| M-04 | Envelope RX timeout detection | Remove each RX message on the HIL bench; measure time to `controls_allowed` false and to first rejected TX | HIL (D-04) | ≤ 0.2 s after change |
| M-05 | Heartbeat loss and command stall | Stop `0xf3`; stop `sendcan` while heartbeat continues | HIL | ≤ 0.3 s / ≤ 0.05 s to SS-L; siren ≤ 0.56 s after the last heartbeat when engaged (T-07a; by ear, `panda/tests/hitl/test_15_heartbeat_siren.py` times the revocation) |
| M-06 | MCU hang | Inject infinite loop in tick / main / ISR via debug build | HIL | reset ≤ 0.2 s; relay released |
| M-07 | Brake/cancel → torque zero at EPS | Vehicle, brake press while engaged at constant torque | Closed course | ≤ 0.2 s to EPS torque zero |
| M-08 | Driver override | Steering force gauge, opposing torque | Closed course | per TSR-304 |
| M-09 | SoC loop timing | `procLog`, per-process loop timing, model execution time, `sendcan` age histogram over ≥ 10 h of driving | Logs | p99.9 within TSR-602/614 budgets |
| M-10 | Take-over request latency | Fault injection on SoC, camera on display + audio capture | HIL/vehicle | ≤ 1 s |
| M-11 | Forwarding latency camera → car | Timestamped capture on both buses | HIL with real camera | ≤ TSR-707 bound |
| M-12 | FCW onset against a braking lead (§3.8.2) | Closed course with a soft target braking at a known rate; log FCW event time | Reference vehicle | FCW ≤ 0.6 s after lead braking onset at a 1.0 s gap |

Results (template — **Not yet executed**):

| ID | Date | Build | Result | Pass/Fail | Evidence |
|---|---|---|---|---|---|
| M-01…M-12 | — | — | — | — | — |

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm vehicle width, lane-margin design value and a_y,EPS (M-01) and recompute §3.1 | Safety engineer | G2 |
| OI-2 | SG-02 at the ODD curve bound: physical time to departure (≈ 0.7 s) is shorter than driver reaction; HARA owner to review C rating of HE-02.1 or tighten R_ODD (tracked as WP-C-03 OI-7; noted in WP-C-04 §8). *2026-10-16:* the simulation (§3.9, synthetic) shows the same inside the ODD: with assistance lost in a 1.5 m/s² curve the lane line is reached after about 1.3–1.5 s, before a 1.5 s driver correction, even when the siren sounds at 0.25 s. The question therefore covers ordinary curves, not only the ODD bound | HARA owner | G2 |
| OI-3 | Check SG-03 standstill-launch distance assumptions with WP-C-08 | Safety engineer | G2 |
| OI-4 | Measure the PCS message period and braking profile on the reference vehicle (A-PCS-1, A-PCS-2) and confirm or replace the preliminary SG-07 FTTI of §3.6. The acceptable loss is agreed for now: 0.2 s, up to about 4 km/h, accepted until measured (DQ-062, 2026-10-14) | Safety engineer | G2 |
| OI-7 | SG-07 forwarding loss has zero margin (FDTI + FRTI = FTTI). Decide whether to shorten the watchdog and forwarding-supervision times below 0.1 s once the PCS timing is measured | Safety engineer | G2 |
| OI-5 | Execute M-01…M-12 and fill §6 results | Test lead | G4 |
| OI-6 | Update FSC §8 budgets after this document is approved (FSC OI-4) | Safety engineer | G2 |
| OI-8 | EPS-fault siren latency ≤ 1.26 s worst case from fault onset (T-28; corrected 2026-10-13 from ≈ 1.14 s: the speaker sounds only on every other 8 Hz tick) exceeds the SG-02 1 s warning budget (§3.7). TSR-516's ≤ 0.5 s after detection is met (≤ 0.26 s) only because WP-S-02 v0.14 defines detection as the 1 s persistence; measured from the first fault frame it is not. Caused by the maintainer decision of 2026-10-12 (persistent faults only, 1 s; EPS-fault impact record §7). Options were: shorten the persistence (e.g. 0.7 s), or justify that LKA actuation is already refused from the first fault frame. **Decided 2026-10-14 (register DQ-048): shorten the persistence to about 0.7 s.** WP-S-02 v0.21 TSR-516 now measures detection from the first fault frame and caps the persistence at 0.7 s. Open: the panda firmware change and its HIL timing (M-05/M-10); T-28 stays at 1.26 s until the code changes (added 2026-10-12) | Safety manager | G2 |
| OI-9 | Heartbeat loss when authority ended within the 5 s before it: TSR-516(a) asks for the siren ≤ 0.5 s after detection, but the fast siren (T-07a) sounds only when authority is granted at the revocation; this case keeps the 1 Hz siren at 4–5 s (T-07). Decide whether the case needs a warning within the SG-02 budget (the driver has already seen the disengagement) and align TSR-516(a) or the firmware. No requirement changed here (added 2026-10-13) | Safety manager | G2 |
| OI-10 | The EPS behaviour after `0x2E4` stops (M-02) decides most simulated outcomes: release gives about 1.3–1.5 s to the lane line, hold about 3.1–3.5 s (§3.9). Make M-02 the first vehicle measurement, then re-run the simulation with the measured behaviour (added 2026-10-16) | Test lead | G2 |
