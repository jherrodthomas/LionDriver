# WP-S-04 Timing Analysis: FTTI, Fault Detection and Reaction Budget

| Field | Value |
|---|---|
| Work product | WP-S-04 Timing analysis: FTTI, fault detection and reaction budget |
| Standard reference | ISO 26262-4:2018 §6 (fault tolerant time interval, fault detection and fault reaction time intervals, emergency operation); ISO 26262-3:2018 §7 (FTTI as FSC input); ISO 26262-1:2018 (definitions, by reference); ASPICE 4.0 SYS.3 |
| Version | 0.26 (§3.6, OI-7: the margin is decided after measuring, DQ-134 A; the zero margin stays on record until M-13, PCS braking timing, and M-14, watchdog clock spread, are measured; shorten the watchdog only if the measured margin is short; TSR-501 and TSR-711 unchanged; §6 adds M-13 and M-14; 2026-10-25). 0.25 (§5: Figure 5-3, each fault class by verdict, generated from the comparison table; 2026-10-25). 0.24 (§5 host/panda mismatch row: met by design in the reference build, panda `f4803c5`; 2026-10-21). 0.23 (§5 host/panda mismatch row: the plant shows no warning within the SG-02 budget when selfdrived stops (TSR-307(a), TSR-516(b)); 2026-10-20). 0.22 (T-33: the terminal DM reaction is latched until the driver takes over and ends at standstill, held (TSR-633), not verified on the vehicle; 2026-10-20). 0.21 (T-01: `0x1D2` and `0x1D3` read ≤ 0.162 s, was ≤ 0.16 s, as the timing-loop model gives 161.5 ms (§3.10); TSR-401's 0.2 s still met; no verdict changed; 2026-10-20). 0.20 (§3.10 added: the Octave timing-loop model and its animated Figure 3-1; T-01 for `0x1D2` is 161.5 ms in the model; no budget or verdict changed; 2026-10-20). 0.19 (FHTI and EOTI defined in §2 and an FHTI column added to §3.7; Figure 5-1 draws the §3.8 warning paths and the FHTI; M-06 pass criterion set to TSR-501's ≤ 0.1 s, was ≤ 0.2 s; no budget changed; 2026-10-20). 0.18.2 (T-17 and T-19 follow #51: `controlsMismatch` ≤ 0.5 s, `cruiseMismatch` 1 s; 2026-10-20). 0.18.1 (§3.8.2 and T-31: the FCW citation moved with the code to `selfdrived.py:488-493`; T-18, T-20 and T-22 citations moved likewise; no number changed; T-17 and T-19 left as written, their text predates TSR-621 and `CRUISE_MISMATCH_TIME`; 2026-10-20). 0.18 (T-34 and §5 full SoC stall: the TX-arrival revocation sounds the siren, panda `8a69ccf` / opendbc `4d1a056` (DQ-404 A), met code-derived, not verified; T-07a and T-28 simulated rows follow; 2026-10-20). 0.17 (§5 full SoC stall row: siren on a T-34 revocation decided, DQ-404 A; 2026-10-19). 0.16 (§5 SoC command stall: reference build ≤ 0.06 s for `0x2E4` (T-34), up to one task period over the 0.05 s budget, not verified; 2026-10-19). 0.15 (§6: measured fault-injection timing inside the FTTI is what lets a diagnostic close a System FMEA cause; code-derived and simulated times only rank the work (DQ-206 A); 2026-10-19). 0.14 (T-28, §3.7, §5, Figure 5-2, OI-8: EPS-fault siren persistence 0.7 s implemented at panda `bf8102a` (DQ-048), siren ≤ 0.96 s from onset; 2026-10-17). 0.13 (DQ-061 applied: TSR-516(a) reworded for heartbeat loss within 5 s after authority ended; the 1 Hz siren at 4–5 s (T-07) meets it; OI-9 closed; 2026-10-17). 0.12 (DQ-365 applied (DQ-340 merged into it): SG-08 no-response reaction decided; preliminary budget for the time to the reaction and the stop in §3.7 and §3.8.4; OI-11 narrowed; 2026-10-16). 0.11 (§3.9: steering-override row from the L2 steering-column simulation (#137): the host rule releases within 0.2 s in 18 of 36 assumed cases and never in 8; M-08 extended to the two torque scales; 2026-10-16). 0.10 (§3.9 re-based on the plant runs at the 110 km/h ODD bound (DQ-260; plant results of #136), with the 120 km/h over-speed rows as the margin case; new §3.9 row for the curve assist-loss search (97 of 120 samples leave the lane, departures from a_y ≈ 0.3–0.4 m/s²); OI-2 extended; 2026-10-16). 0.9 (HARA v0.4: SG-02, SG-03 and SG-06 ASIL C, new SG-08 ASIL A; §3.7 and §3.8.4 give the SG-08 alert budget against its preliminary FTTI of 6 s; OI-2 notes that the HARA keeps 1 s to warning for SG-02 and asks for its review here; new OI-11 for the time to the no-response reaction; 2026-10-16). 0.8 (§3.9 added: closed-loop cross-check of §3 and §4 against the fault-injection plant model of `assurance/sim` (synthetic data, no evidence credit); T-34 (TSR-408 command-arrival check) added to §4; §5 row for the full SoC stall, where the fast heartbeat siren never sounds; OI-2 extended below the ODD bound; OI-10 added; no budget changed; 2026-10-16). 0.7 (§3.8 added: FTTI and budgets for the warning paths that had none (insufficient lateral control, late or insufficient braking warning, unintended engagement, driver monitoring), System FMEA SFM-ACT-017; four rows added to §3.7; T-30…T-33 added to §4; kinematic estimates and code-derived times only; 2026-10-16). 0.6 (lead decisions of 2026-10-14 recorded, register DQ-048, DQ-062, DQ-114: EPS-fault warning persistence ≤ 0.7 s, OI-8 decided; SG-07 0.2 s accepted as the working budget; 90 ms watchdog accepted on condition; Figure 5-2 note updated; no code-derived time changed; 2026-10-16). 0.5 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.4 (§5 Figures 5-1 and 5-2 added: timing budgets per safety goal against the code-derived times, and the EPS-fault warning chain of OI-8; generated from §3.7 and §4 by `figures/fig_s04_timing.py`; no number changed; 2026-10-13). 0.3 (status update 2026-10-12: §4 code-derived times for the reference build at `bf6ce8c` (T-01, T-06a/b, T-09a, T-26…T-29), §5 verdicts, OI-8 EPS-fault warning latency; nothing verified on hardware). History: 0.2 (§3.6 preliminary SG-07 FTTI and budget, RR-2026-005 F-02; 2026-10-12) |
| Status | Draft — kinematic estimates and code-derived times, cross-checked in simulation (§3.9, synthetic, not evidence); no measurement has been performed; not reviewed independently |
| ASIL / scope | SG-01 (C until re-rated, B‡); SG-02, SG-03, SG-06 (C); SG-04, SG-05, SG-07 (B); SG-08 (A) (WP-C-03 v0.4) |
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
| FHTI | Fault handling time interval: FDTI + FRTI, fault occurrence → safe state (ISO 26262-1:2018). Given per row in the last column of §3.7 and in Figure 5-1 |
| EOTI | Emergency operation time interval: time between the end of the FHTI and the safe state when an emergency operation is needed in between. No row of §3.7 budgets one: every reaction here reaches its safe state directly. The SG-08 no-response reaction (§3.8.4) keeps the vehicle under item control until standstill; its time is budgeted there as the time to standstill |
| Budget rule | FHTI = FDTI + FRTI ≤ FTTI, with a margin of at least 20 % of the FTTI for scheduling jitter, CAN latency and EPS/PCM response |
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

- TSR-501 set the watchdog timeout to ≤ 0.2 s, which fits SG-01 (0.5 s) but not the SG-07 FDTI of 0.1 s. WP-S-02 v0.3 tightens it to ≤ 0.1 s. The alternative, releasing the relay by another path on an MCU hang, is open in WP-H-01 (HWSR-502). *Status 2026-10-12:* the IWDG is implemented with a 90 ms nominal timeout (reload 719, panda `b790fca`, T-09a); whether it stays ≤ 0.1 s depends on the LSI tolerance (watchdog impact record OI-2), so the zero margin of OI-7 is not yet shown. *Decided 2026-10-14 (DQ-114):* the 90 ms watchdog replaces the two interim SG-07 residuals once the independent reviewer has checked it and the LSI tolerance; until then the residuals stay in the safety case. *Decided 2026-10-25 (DQ-134 A):* the margin is decided after measuring. TSR-501 and TSR-711 stay at ≤ 0.1 s until the PCS braking timing (M-13) and the watchdog's clock spread (M-14) are measured; the rule is in OI-7.
- TSR-706 releases the relay ≤ 0.1 s after the fault reaction. That fits the FRTI.
- TSR-707 (forwarding latency ≤ 1 ms in normal operation) is far inside the budget.
- No TSR detected that forwarding has stopped. TSR-711 is added in [WP-S-02](WP-S-02-technical-safety-requirements.md) v0.3.

### 3.7 Summary of FTTIs and budgets

| SG / fault class | FTTI | FDTI budget | FRTI budget | Margin | FHTI (FDTI + FRTI) |
|---|---|---|---|---|---|
| SG-01 continuous limits | per frame | 0 | ≤ 10 ms (+ TSR-109) | — | ≤ 10 ms |
| SG-01 RX loss/corruption | 0.5 s | ≤ 0.2 s (TSR-401) | ≤ 0.1 s | ≥ 0.2 s | ≤ 0.3 s |
| SG-01 SoC heartbeat loss | 0.5 s | ≤ 0.3 s (TSR-407) | ≤ 0.1 s | ≥ 0.1 s | ≤ 0.4 s |
| SG-01 SoC command stall | 0.5 s | ≤ 0.05 s (TSR-408) | ≤ 0.1 s | ≥ 0.35 s | ≤ 0.15 s |
| SG-01 MCU execution fault | 0.5 s | ≤ 0.1 s (TSR-501; set by SG-07; 90 ms nominal implemented, T-09a) | ≤ 0.1 s (reset + relay release) | ≥ 0.3 s | ≤ 0.2 s |
| SG-01 relay stuck | 0.5 s | ≤ 0.3 s (TSR-506) | ≤ 0.1 s | ≥ 0.1 s | ≤ 0.4 s |
| SG-02/06 loss without warning | 1 s to warning | ≤ 0.5 s | ≤ 0.5 s | — (see §3.2). EPS-fault siren of the reference build ≤ 0.96 s worst case from fault onset since panda `bf8102a`, within this row (T-28; DQ-048; ≤ 1.26 s with the earlier 1 s persistence, OI-8). Heartbeat-loss siren ≈ 0.56 s after the last heartbeat, within this row (T-07a, all builds since panda `c33343b`; 2026-10-13). *2026-10-14 (DQ-048):* persistence to be shortened to ≤ 0.7 s, which gives ≤ 0.7 s + 10 ms + 250 ms ≈ 0.96 s from fault onset; firmware changed at panda `bf8102a` (2026-10-17) | ≤ 1 s to warning |
| SG-03/04 | 1 s | ≤ 0.5 s | ≤ 0.3 s | ≥ 0.2 s | ≤ 0.8 s |
| SG-05 brake/cancel | 0.2 s | ≤ 30 ms | ≤ 10 ms + EPS/PCM | TBD | ≤ 40 ms + EPS/PCM |
| SG-05 steering override | 0.2 s | ≤ 40 ms + t_ovr | ≤ 0.1 s | TBD | ≤ 140 ms + t_ovr |
| SG-07 content (TX gate, block list) | per frame | 0 | — | — | — |
| SG-07 forwarding loss | 0.2 s (preliminary, §3.6) | ≤ 0.1 s (TSR-711; MCU hang: TSR-501 ≤ 0.1 s, 90 ms nominal implemented, T-09a) | ≤ 0.1 s (TSR-706, incl. relay drop-out) | 0 (depends on LSI tolerance, OI-7) | ≤ 0.2 s (= FTTI) |
| SG-02 insufficient lateral control (warning path, §3.8.1) | 1.1 s to 0.6 m at a 1 m/s² deficit; 1.55 s at 0.5 m/s² | ≤ 0.4 s (steerSaturated, T-30) | ≤ 0.1 s to alert | driver needs t_r = 0.75–1.5 s after the alert: met at ≤ 0.5 m/s² deficit, **not met** at 1 m/s² | ≤ 0.5 s to alert |
| SG-06 late or insufficient braking warning (FCW, §3.8.2) | 1.6 s at 1.0 s time gap; 3.2 s at 1.5 s (lead braking 6 m/s², item limited to 3.5 m/s²) | FCW onset after the lead brakes (T-31, not derived) | ≤ 0.1 s to alert | FCW needed ≤ 0.6 s after lead braking at 1.0 s gap with t_r = 1.0 s; to be measured | TBD (FCW onset not derived) |
| SG-01 / SG-03 unintended engagement (System FMEA SG-008, §3.8.3) | 0.5 s (as SG-01) | per frame (TSR-105, TSR-301); latent panda authority while disengaged ≤ 0.3 s (TSR-630, T-32) | ≤ 0.1 s | ≥ 0.1 s | ≤ 0.4 s (latent gate fault) |
| SG-08 driver not supervising (§3.8.4) | ≤ 6 s from loss of attention to the first alert (WP-C-03 v0.4, preliminary) | first vision alert at 5 s of distraction (policy timer, T-24) + DM frame and model latency (not measured) | alert output through `selfdrived` and the UI (not measured) | 1 s less the DM latency and alert output; TBD until measured (OI-11) | TBD (DM latency and alert output not measured) |
| SG-08 no-response reaction (§3.8.4; DQ-365 A) | preliminary: reaction starts ≤ 18 s (vision) / ≤ 30 s (wheel-touch) from loss of attention; standstill about 10 s later from 110 km/h at 3 m/s² (OI-11) | terminal alert at 13 s vision / 25 s wheel-touch (T-24); DM invalid → take-over request ≤ 2 s (TSR-609) | reaction ≤ 5 s after the terminal alert (TSR-633, T-33) | TBD | TBD |

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

With t_r = 1.0 s the FCW must sound within about 0.6 s of the lead's braking onset at a 1.0 s gap, and within 2.2 s at 1.5 s. The FCW onset of the planner and model triggers (`selfdrive/selfdrived/selfdrived.py:488-493`) is not derived from the code here (T-31); it is to be measured (M-12).

#### 3.8.3 Unintended engagement (System FMEA SG-008; SFM-013.C1, C2)

Actuation without a driver engagement is refused per frame by the envelope gate (TSR-105, TSR-301), so the FTTI of SG-01 (0.5 s) applies only to a latent fault of that gate. A panda that reports authority while the item is disengaged is detected by the host within ≤ 0.3 s (TSR-630, T-32), which leaves ≥ 0.1 s after the ≤ 0.1 s reaction.

#### 3.8.4 Driver monitoring (unresponsive driver; SFM-022.C3, SFM-025.C1)

The hazard is an engaged item with nobody supervising it. HARA v0.4 rates it as H-09 with goal SG-08, ASIL A (DQ-205). Its preliminary FTTI is **≤ 6 s from the loss of attention to the first alert**, taken from the DM end-to-end alert time of WP-C-08 OI-2 (FSR-08.01). The budget: the DM policy raises the first vision alert after 5 s of distraction (T-24), which leaves 1 s for the camera frame time, the DM model latency and the alert output through `selfdrived` and the UI. None of these is measured (OI-11). The second part of the goal, the time from loss of attention to the no-response reaction, is left by the HARA to this document. The reaction was decided on 2026-10-16 (DQ-365, A): keep the lane, decelerate in lane to a standstill within the envelope limits with the alert sounding, then stay stopped and held with re-engagement locked out until the driver responds. **Preliminary budget:** the reaction starts at the latest 18 s (vision) or 30 s (wheel-touch) after the loss of attention, the sum of the policy timers and the TSR-633 delay below, and the stop then takes about 10 s from 110 km/h at 3 m/s² (TSR-202). These values describe the present design rather than a hazard-derived bound; WP-C-08 validation is to confirm or shorten them (OI-11). Today the terminal alert comes after 13 s (vision) or 25 s (wheel-touch) of inattention (T-24), DM invalid output must give a take-over request within 2 s (TSR-609), and the reaction (TSR-633) must start within 5 s of the terminal alert (T-33), so 18 s or 30 s in all.

### 3.9 Cross-check in simulation (synthetic data, not evidence)

The fault-injection plant model of [`assurance/sim`](../sim/README.md) runs the real envelope code in a closed loop: opendbc `libsafety` (reference build, Toyota mode, parameter 73), the panda heartbeat monitor, both sirens and the IWDG feed. Around it are a single-track Corolla model, an EPS and PCM lag, a stand-in SoC controller and a driver model. Its results are in [`plant-results.md`](../sim/results/plant-results.md). The conditions are 110 km/h (the ODD speed bound, DQ-260), a 1.5 m/s² curve inside the ODD and a driver t_r = 1.5 s. Each fault family also has a 120 km/h over-speed row (`-OS`, outside the ODD), kept as the margin case; its values are given in brackets below where they differ. The EPS has two frame-loss assumptions: *release*, which drops LKA torque 30 ms after the last frame, and *hold*, which keeps it 2 s (T-23).

**These results are synthetic.** The model is not validated against Corolla logs, so they earn no evidence credit (DQ-139, WP-V-02 §5.3). They do not replace a kinematic estimate or a code-derived time in this document. They show where an estimate is optimistic or pessimistic, and which measurement decides the outcome. Both values are kept side by side.

| Item | This document | Simulation (EPS release unless stated) | Reading |
|---|---|---|---|
| §3.1 step, assistance lost in a 1.5 m/s² curve: time to the lane line, 3.0 / 3.7 m lane | 0.90 / 1.13 s | 1.25–1.36 / 1.49–1.60 s (F-01a, F-04b, F-05, F-06a, F-07, F-08) [120 km/h: 1.27–1.38 / 1.51–1.62 s]; with EPS hold 3.14–3.48 s | The kinematic estimate is conservative by about 0.35–0.4 s: the EPS lag and the vehicle response delay the drift. The lane line is still reached before a 1.5 s driver correction, so this extends OI-2 below the ODD bound |
| §3.1 1 s ramp at 1.99 m/s² (hard-over within the envelope), 3.0 / 3.7 m lane | 1.23 / 1.44 s | 1.55 / 1.77 s (F-01b) [120 km/h: 1.57 / 1.80 s] | Conservative by about 0.3 s. The driver cue is drift only, at 1.14 s |
| SG-01 FTTI 0.5 s (§3.1, §3.7) | 0.5 s | Deviation at 0.5 s ≤ 0.03 m in every case | For these fault classes the hazard threshold is not reached within 0.5 s. The 0.5 s design value is conservative for envelope-limited torque. It is kept for faults that defeat the envelope (§3.1, a_y,EPS unknown) |
| T-01 RX timeout, `0x260` | ≤ 0.162 s | Revoked 0.083 s after the last frame (F-08) | Consistent |
| T-06a heartbeat revocation | ≤ 0.31 s after the last heartbeat | 0.193 s after the fault, which is within 0.3 s of the last heartbeat (F-04a) | Consistent |
| T-07a heartbeat siren | ≈ 0.56 s after the last heartbeat | 0.25 s after the fault (F-04a) | Consistent when commands continue; in a full stall the T-34 revocation sounds the same siren first (since panda `8a69ccf`) |
| T-09a IWDG | ≈ 90 ms nominal | Reset 83 ms after the hang, 90 ms after the last feed (F-05) | Consistent |
| T-28 EPS-fault siren | ≤ 0.96 s worst case | 0.75 s at the simulated speaker phase (F-07, panda `bf8102a`; 1.00 s with the 1 s persistence). Since panda `8a69ccf` the siren in F-07 comes at 0.25 s from the T-34 path: the modelled host keeps commanding through the fault, the envelope refuses its frames and the arrival check revokes after 50 ms; F-07 no longer exercises the 0.7 s persistence | Consistent (phase-dependent); the persistence path is covered by the panda host tests only |
| T-34 command-arrival revocation | — | Revoked 0.043 s after a full SoC stall (F-04b); siren 0.25 s after the stall (panda `8a69ccf`; no siren before) | The 0.3 s heartbeat check still does not fire, because authority is already revoked; the revocation itself now sounds the siren (TSR-516(b), DQ-404 A, §5) |
| §3.3 gap loss in 1 s at +2.0 m/s² | 1.00 m | 0.75 m (L-01) | Conservative (PCM lag) |
| §3.4 follower collision if t_r ≥ h | rule | No collision at h = 1.0 s (L-03) | Not a test of the rule: the ego driver ends the deceleration at 1.55 s |
| §3.6 SG-07 forwarding loss: PCS request during an MCU hang | ≤ 0.2 s (≤ 0.1 s to the IWDG reset + ≤ 0.1 s release) | Reaches the car 0.084 s after the request, 1.8 km/h of speed reduction lost (P-02). With the switch stuck in intercept it never arrives (P-03) | Within the 0.2 s working budget (DQ-062), consistent with T-09a. The switch release time is not modelled (A-PCS-2). P-03 is the degraded case of DQ-064 / TSR-712 |
| §3.5 SG-05 steering override: driver input to LKA release | ≤ 0.2 s (≤ 40 ms + t_ovr, §3.7); not in the envelope (GAP-02, TSR-304(b)) | L2 steering column with the real panda code and the host `MAX_USER_TORQUE` rule; LKA full torque and host threshold swept as assumptions ([override](../sim/results/override-l2.md)): the host drops LKA within 0.2 s in 18 of 36 runs and never in 8 of 36 (driver peak below the host threshold); after the drop the motor torque is below 5 % 0.41–0.77 s after the driver's input | The 0.2 s budget is met only when the driver pushes hard and fast, and the motor torque itself takes longer than 0.2 s to fall even then (assumed EPS lag). Supports moving the override check into the envelope (TSR-304(b)). The result depends on the N·m scales of `STEER_TORQUE_DRIVER` and of the LKA command, which M-08 measures |
| §3.8.1 saturation at the ODD curve bound | 0.5–1.0 m/s² deficit is credible | Saturated at R_ODD; 1.13 m drift; lane line reached 4.09 s (3.0 m lane) and 4.57 s (3.7 m lane) after curve entry (N-3) [120 km/h: 0.80 m, 3.0 m line at 3.71 s, 3.7 m line not reached] | Supports §3.8.1 and OI-2. At 110 km/h the no-fault curve at the bound leaves even a 3.7 m lane: the lower speed needs a tighter radius for the same a_y, and the drift grows |
| §3.2 / OI-2: assistance lost in a highway curve, how far below the bound it matters | — (§3.2 treats the bound only) | Search over 80–110 km/h, a_y 0–1.8 m/s², lane 3.0–3.9 m, t_r 0.75–1.5 s, cue 0.1–0.3 m ([search](../sim/results/search-curve-assist-loss.md), EPS fault F-07): 71 of 120 samples leave the lane since panda `8a69ccf`: the modelled host keeps commanding, the arrival check revokes on its refused frames and the siren sounds about 0.25 s after the fault (T-34; 92 of 120 with the siren after 0.7 s at `bf8102a`, 97 with the 1 s persistence); the mildest departing curve is a_y = 0.51 m/s², the sharpest held 1.05 m/s² | Departures still begin at about 0.5 m/s², far below the ODD bound of 2.5 m/s². Extends OI-2 to most highway curves. The earlier siren comes from the host model, which keeps commanding through the fault; the real host stops (change record OI-2) |

Faults that the envelope does not report, so no warning comes from the item (§5):
- **Over-limit torque (F-01a):** refused frame by frame while authority stays granted. TSR-108 latching (DQ-060) and the TSR-516(b) siren on a rejected command are not implemented.
- **Frozen command (F-03):** not detected. TSR-631 is not implemented.

**EPS frame-loss behaviour decides most outcomes** (release about 1.3–1.5 s to the line, hold about 3.1–3.5 s). Measurement M-02 is therefore the first measurement to make (OI-10).

### 3.10 Timing-loop model (Octave, model of the code, not evidence)

The [Octave timing-loop model](../models/octave/README.md#timing-loops-2026-10-20-octave-840-panda-8a69ccf-opendbc-4d1a056) recomputes the §4 detection and warning times from the pinned panda and opendbc code. It sweeps each fault over every loop phase that can delay it: the 100 Hz safety task, the 8 Hz tick (the speaker sounds only on every other tick), the 1 Hz path of the original baseline, and the LSI tolerance of the IWDG. The reaction after detection is the §3.7 FRTI budget, since the EPS and PCM response is not modelled (M-02). CI fails when a model time differs from its §4 row by more than 10 ms, or when the reference-build FDTI overruns are not exactly `0x262` (T-01) and the command stall (T-34). Like §3.9, it is not a measurement and earns no evidence credit (WP-P-07 TL-25).

![Figure 3-1: animated FTTI timing loops, one timeline per fault class from fault to safe state against the FTTI. RX loss 0x1D2 in the reference build: detected within 162 ms, safe state within the 500 ms FTTI. The same fault in the original baseline: detected after up to 2 s, FTTI exceeded. SoC heartbeat loss: detected within 300 ms, siren within 550 ms. SoC command stall: detected within 60 ms, 10 ms over its 50 ms budget but within the FTTI, siren within 310 ms. MCU hang with a 10 % slow watchdog clock: detected at exactly the 100 ms budget. EPS fault: LKA refused on the first fault frame, siren within 950 ms](../models/figures/fig-md-3-ftti-loops-anim.svg)

*Figure 3-1.* Animated: each row runs from normal operation through the fault, the detection time against the 100 Hz task and 8 Hz ticks (the detecting task run flashes), the FRTI budget and the safe state to the siren, against the FTTI. The worst case over all loop phases is drawn, from [`timing_loop_results.csv`](../models/octave/timing_loop_results.csv), by [`fig_timing_anim.py`](../models/figures/fig_timing_anim.py) (CI fails if stale).

What the model adds to §4: T-01 for `0x1D2` is 161.5 ms (5 × 30.3 ms plus one task period); §4 read ≤ 0.16 s until v0.21 and now reads ≤ 0.162 s. T-06a (≤ 0.31 s), T-07a (≈ 0.56 s) and T-28 (≤ 0.96 s) each include one 10 ms task period the code does not need: the model gives 0.300 s, 0.550 s and 0.950 s. No budget or verdict of §5 changes.

## 4. Current detection and reaction times (code-derived)

| # | Mechanism | Code | Derivation | Worst-case time |
|---|---|---|---|---|
| T-01 | RX timeout | `opendbc_repo/opendbc/safety/safety.h:321-344`; called at 1 Hz from `panda/board/main.c:241-242` | threshold max(10 × period, 1 s); for the Corolla messages 10 × period is 120 ms (`0xAA` 83 Hz), 200 ms (`0x260` 50 Hz), 303 ms (`0x1D2` 33 Hz), 250 ms (`0x226` 40 Hz), so 1 s applies; evaluated once per second | **1–2 s** (at `8b8c6ae`). *Status 2026-10-12:* 5 nominal periods (`rx_timeout_periods`, opendbc `de80b63`), evaluated by the 100 Hz safety task (panda `171fcdf`): **≤ 0.162 s** for `0x1D2` (5 × 30.3 ms + one 10 ms task period, 161.5 ms; §3.10); the reference build adds `0x262` (25 Hz, ≈ 0.21 s, slightly above TSR-401's 0.2 s if the real rate is 25 Hz) and `0x1D3` (33 Hz, ≈ 0.162 s) (opendbc `21d8dd8`). Not verified on hardware |
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
| T-17 | `controlsMismatch` (panda vs host authority) | `selfdrived.py:53-56, 361-366, 566-574`; `selfdrived/supervision.py` | 200 cycles at 100 Hz before #51. *Status 2026-10-13 (#51, TSR-621):* 2 consecutive `pandaStates` samples (10 Hz), at most 0.5 s after the first mismatched frame; samples in the first 0.3 s after engaging not counted (2026-10-14, TSR-301) | 2 s before #51; now **≤ 0.5 s**. Unit tests; not verified on hardware |
| T-18 | Safety mode/param mismatch | `selfdrived.py:351-366` | only after 10 s from start | 10 s after start |
| T-19 | `cruiseMismatch` | `selfdrived.py:57, 464-468`; `events.py:464-470` | 6 s, no reaction, before #51. *Status 2026-10-13 (#51, TSR-308):* 1 s (`CRUISE_MISMATCH_TIME`), repeating prompt; `controlsd` keeps requesting the cancel | **1 s** to the prompt. Unit tests; not verified on the vehicle |
| T-20 | `selfdrivedLagging` / Ratekeeper | `openpilot/common/realtime.py:72-74`; `selfdrived.py:157` | average dt over 100 samples > period/0.9 | ≈ 1 s averaging |
| T-21 | Excessive actuation | `selfdrive/selfdrived/helpers.py:12` | 0.25 s persistence | 0.25 s |
| T-22 | Big-model diagnostic masking | `selfdrived.py:428-430` | masked during load + 5 s | up to 5 s blind (GAP-17) |
| T-23 | EPS drop-out handling (vehicle) | comment `opendbc_repo/opendbc/car/toyota/carstate.py:15-16` | LKA_STATE 9 → 11 over ≈ 2 s, then 3 | ≈ 2 s (unverified, AOU-01R) |
| T-24 | DM escalation | `selfdrive/monitoring/policy.py:31-36, 44` | vision 5/8/13 s; wheel-touch 5/15/25 s; +5 s at alert 3 → force decel | per policy |
| T-25 | Host steering fault hysteresis | `selfdrive/car/car_events.py` (onboard review) | 1.5 s | 1.5 s |
| T-26 | Cruise active with main off (reference build, added 2026-10-12) | `opendbc_repo/opendbc/safety/modes/toyota.h` (`TOYOTA_CRUISE_MAIN_TOLERANCE_US`, opendbc `8836b65`) | CRUISE_ACTIVE (`0x1D2`) becoming active while MAIN_ON (`0x1D3`) is 0: refused on receipt; main going off while engaged: revoked once the disagreement lasts > 150 ms | refuse at once; revoke after 150 ms (+ one 30 ms frame) (TSR-405(c)). Not verified on hardware |
| T-27 | TX rate supervision (reference build, added 2026-10-12) | `opendbc_repo/opendbc/safety/safety.h` `tx_rate_check` (opendbc `951b459`) | per-ID sliding 250 ms window; 3 rejections while controls are allowed revoke | revoke ≤ 0.1 s after the first rejected frame (≤ 0.2 s from onset at 2× the rate; unit tests) (TSR-518). Not verified on hardware |
| T-28 | EPS fault (reference build, added 2026-10-12) | `modes/toyota.h` (opendbc `338f5fc`); `panda/board/drivers/eps_fault_siren.h` (panda `6a7f2fb`) | LKA_STATE fault codes on `0x262`: STEERING_LKA with torque refused from the receipt of the fault frame; siren once the fault has persisted 0.7 s (70 ticks) after it was seen while `controls_allowed` (panda `bf8102a`, DQ-048; counted on after a revocation since `3ee2796`, DQ-367), driven by the 8 Hz speaker tick on every other tick | LKA refused on receipt of the fault frame (TSR-110); siren ≤ 0.7 s + 10 ms + 2 × 125 ms ≈ **0.96 s** after fault onset worst case (TSR-516(b)); within the SG-02 1 s warning row. With the 1 s persistence before panda `bf8102a`: ≤ 1.26 s, over the row (OI-8). Not verified on hardware |
| T-30 | Controller saturation warning `steerSaturated` (added 2026-10-16) | `openpilot/selfdrive/controls/lib/latcontrol.py:8, 22-29`; `opendbc_repo/opendbc/car/toyota/interface.py:50` | saturation time accumulates to `steerLimitTimer` = 0.4 s (LKA torque cars) | 0.4 s + 1 frame |
| T-31 | Forward collision warning (added 2026-10-16) | `selfdrive/selfdrived/selfdrived.py:488-493` | model `hardBrakePredicted` or planner FCW | not derived; measure (M-12) |
| T-32 | Host check of panda authority while disengaged (added 2026-10-16) | — | not implemented (TSR-630) | not detected |
| T-33 | Terminal DM reaction (added 2026-10-16) | `selfdrive/monitoring/policy.py:44, 457`; `selfdrive/selfdrived/minimum_risk.py`; `selfdrive/controls/controlsd.py:237-239` | forced deceleration 5 s after the terminal alert, latched until the driver takes over; the vehicle stops in lane and stays held (TSR-633) | 5 s to deceleration; safe state reached at standstill, held while the PCM holds (AOU-16, not verified) |
| T-34 | SoC command arrival (TSR-408; reference build, added 2026-10-16) | `opendbc_repo/opendbc/safety/safety.h` `tx_arrival_ok`, `modes/toyota.h` (opendbc `273f44e`) | while authority is granted, the 100 Hz safety task revokes it when `0x2E4` has not reached the TX hook for > 50 ms or, with openpilot longitudinal, `0x343` for > 100 ms | ≤ 0.06 s for `0x2E4`, ≤ 0.11 s for `0x343` (one task period added). Runs in the safety task **before** the heartbeat check (`main.c` `safety_task_handler`), so in a full SoC stall it revokes first and the heartbeat check finds authority gone. Since panda `8a69ccf` / opendbc `4d1a056` the revocation sets `safety_tx_arrival_revoked` and the heartbeat siren starts in the same task (TSR-516(b), DQ-404 A): siren ≤ 0.06 s + 2 × 125 ms ≈ 0.31 s after the last `0x2E4` (the 0.06 s already holds the task period). Simulated 0.043 s, siren 0.25–0.29 s (§3.9). Not verified on hardware |

## 5. Comparison and required changes

| Fault class | Budget | Baseline | Verdict | Required change | TSR |
|---|---|---|---|---|---|
| RX loss | ≤ 0.2 s | 1–2 s (T-01) | **Not met** at `8b8c6ae`. *2026-10-12:* Met by design for the Toyota RX set (`0x262` marginal, ≈ 0.21 s), not verified (M-04) | 5 periods, evaluation ≥ 50 Hz (move timeout check out of the 1 Hz path) | TSR-401 |
| RX stuck/inserted | ≤ 0.2 s | not detected (T-03) | **Not met** | rate, frozen-content, cross-checks | TSR-403…405 |
| SoC heartbeat loss | ≤ 0.3 s | 4–5 s (T-06) | **Not met** at `8b8c6ae`. *2026-10-12:* Revoke met by design (T-06a, ≤ 0.31 s; M-05 pending); SILENT ≤ 2 s not met (T-06b, TSR-510) | evaluate at ≥ 10 Hz; revoke at 0.3 s; SILENT ≤ 2 s | TSR-407, 510 |
| SoC heartbeat loss → warning (added 2026-10-13) | warning within SG-02 1 s (§3.7) | siren at T-06: 4–5 s (T-07) | **Not met** at `8b8c6ae`. *2026-10-13:* Met by design in all builds when authority was granted at the revocation (T-07a, ≤ 0.56 s); not verified (M-05). Authority that ended within the 5 s before the loss: 4–5 s (T-07), within the ≤ 5 s of TSR-516(a) as reworded (DQ-061 A, 2026-10-17) | none (OI-9 closed) | TSR-516, 407 |
| Host/panda mismatch | ≤ 0.3 s | 2–3 s (T-05), 2 s (T-17) | **Not met**. *2026-10-20:* plant run with the real panda code: revoked 2.25–3.16 s after selfdrived stops, no siren, steering already stopped at ≈ 0.1 s, so no warning within the SG-02 1 s budget ([engaged-mismatch.md](../sim/results/engaged-mismatch.md), synthetic). *2026-10-21:* **met by design in the reference build** (panda `f4803c5`): revoked ≤ 0.31 s after the first "not engaged" heartbeat, siren 0.5 s after it if cruise stays on (TSR-516(c)); plant: revoked 0.39–0.48 s and siren 0.63–0.88 s after selfdrived stops, inside the SG-02 1 s warning budget; not verified on hardware | 0.3 s both sides | TSR-307 |
| SoC command stall | ≤ 0.05 s | 0.1 s at host (T-13), then EPS ≈ 2 s (T-23) | **Not met** at `8b8c6ae`. *2026-10-16:* the reference build revokes within ≤ 0.06 s for `0x2E4` (T-34, simulated 0.043 s), up to one 10 ms task period over the budget; not verified (M-05) | command-frame freshness in the MCU + active zero frame | TSR-408, 109 |
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
| EPS fault (added 2026-10-12) | LKA refused; warning within SG-02 1 s (§3.7) | LKA refused on receipt; siren ≤ 0.96 s worst case after onset (T-28, panda `bf8102a`) | Refusal met by design (reference build); warning latency within the 1 s budget by design, margin 0.04 s (DQ-048, OI-8 closed); not verified | — (done: persistence 0.7 s) | TSR-110, 516 |
| Full SoC stall → warning (added 2026-10-16) | warning within SG-02 1 s (§3.7); TSR-516(b) | revoke ≤ 0.06 s (T-34); siren on that revocation ≤ 0.31 s after the last `0x2E4` (panda `8a69ccf`, opendbc `4d1a056`); 1 Hz siren at 4–5 s (T-07) unchanged | **Met, code-derived** (reference build; simulated siren 0.25–0.29 s after the stall, §3.9); not verified on hardware (M-05). Before `8a69ccf` not met: the fast siren did not sound | done: siren on a T-34 revocation (DQ-404 A); HIL `test_15` stall case on the bench | TSR-516, 408 |

![Figure 5-1: timing budgets per safety goal (FDTI, FRTI, margin, FTTI) for SG-01, SG-02/06, SG-03/04, SG-05 and SG-07, with the code-derived times T-01, T-04, T-06, T-06a, T-07, T-07a, T-08, T-09, T-09a, T-13, T-23 and T-28 for the baseline and the reference build](figures/fig-s04-5-1-timing-budgets.svg)

*Figure 5-1.* Budgets of §3.7 and code-derived times of §4 on one linear time axis from fault onset (0–1.2 s; longer times are clipped and given in the right column). Grey is the original baseline `8b8c6ae`, amber the reference build `bf6ce8c` (implemented, not verified on hardware); red marks the part of a time beyond its budget. The amber heartbeat-loss siren time (T-07a) is from panda `c33343b` (2026-10-13), in all builds. Nothing has been measured (§6). The last group draws the four warning paths of §3.8 (v0.19), each against its own FTTI; the FCW (1.6 s) and driver-monitoring (6 s) FTTIs lie beyond the axis. The right column adds FHTI = FDTI + FRTI where both are numbers. Drawn from §3.7 and the T-xx rows of §4 by [`figures/fig_s04_timing.py`](figures/fig_s04_timing.py), which fails `--check` when a source value changes. Source: [`figures/fig-s04-5-1-timing-budgets.svg`](figures/fig-s04-5-1-timing-budgets.svg); change it together with §3.7, §4 and §5.

![Figure 5-2: EPS-fault warning chain T-28 — LKA refused on the first fault frame, 0.7 s persistence, up to 10 ms task period and up to 250 ms to the next sounding speaker tick, siren at up to 0.96 s within the SG-02 1 s warning budget](figures/fig-s04-5-2-eps-fault-warning.svg)

*Figure 5-2.* The T-28 chain of the reference build drawn to scale, with the persistence of 0.7 s (DQ-048, panda `bf8102a`): from fault onset ≤ 0.96 s worst case, within the §3.7 SG-02 row; from the end of the persistence ≤ 0.26 s, within TSR-516(b). With the earlier 1 s persistence the chain reached 1.26 s (OI-8). Upper bounds; the speaker sounds only on every other 8 Hz tick (corrected 2026-10-13 from ≈ 1.14 s); not verified on hardware. Generated by the same script from T-28. Source: [`figures/fig-s04-5-2-eps-fault-warning.svg`](figures/fig-s04-5-2-eps-fault-warning.svg); change it together with §4 T-28, §5 and OI-8.

![Figure 5-3: the 19 fault classes of the comparison table by verdict: 1 met in code on the envelope side, 8 met by design in the reference build, 2 partly or just over the budget, 7 not met and 1 with no derived time; each with its budget and the time in the Baseline column](figures/fig-s04-5-3-verdicts.svg)

*Figure 5-3.* The rows of the comparison table sorted by their latest verdict. "Met" is derived from the code and "by design" is implemented in the reference build and at most simulated; nothing is measured (§6). Because the Verdict cells are free text that grows a dated note per change, each row's verdict is listed in [`figures/fig_s04_verdicts.py`](figures/fig_s04_verdicts.py) with a phrase quoted from its cell; CI fails when a row is added or removed or the phrase leaves its cell, so a changed verdict is re-sorted on purpose.

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

**Use in the FMEA-MSR (decided 2026-10-19, DQ-206 A).** A diagnostic followed by a safe state can close a hazard-linked failure cause of the [System FMEA](../08-analyses/fmea/analyses/system-fmea.yaml) only when its fault-injection timing has been **measured** with the measurements below (for example M-04, M-05, M-06, M-10) and lies inside the FTTI of §3.7. A cause whose MSR priority is low or medium is closed once that measurement passes. The code-derived times of §4 and the simulated times of §3.9 rank the work; they do not close a cause.

| ID | What | Method | Setup | Pass criterion |
|---|---|---|---|---|
| M-01 | EPS torque authority and a_y vs raw request and speed | Steady-state circular / step-steer tests on a closed course; log `0x2E4`, `0x260`, IMU | Reference vehicle, [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md) | Data set for TSR-102 table and §3.1 a_y,EPS |
| M-02 | EPS behaviour on `0x2E4` drop-out and on zero-torque frame | Stop/zero frames at controlled torque; measure wheel torque decay | Vehicle on lift (wheels free) then closed course | t_EPS; decides TSR-109 option (a)/(b) |
| M-03 | PCM response to inactive value and cancel | Inject step from −3.5 m/s² to inactive; cancel bit | Closed course | Jerk within TSR-205 bound (AOU-05R) |
| M-04 | Envelope RX timeout detection | Remove each RX message on the HIL bench; measure time to `controls_allowed` false and to first rejected TX | HIL (D-04) | ≤ 0.2 s after change |
| M-05 | Heartbeat loss and command stall | Stop `0xf3`; stop `sendcan` while heartbeat continues | HIL | ≤ 0.3 s / ≤ 0.05 s to SS-L; siren ≤ 0.56 s after the last heartbeat when engaged (T-07a; by ear, `panda/tests/hitl/test_15_heartbeat_siren.py` times the revocation) |
| M-06 | MCU hang | Inject infinite loop in tick / main / ISR via debug build | HIL | reset ≤ 0.1 s after the stall (TSR-501, set by SG-07 §3.6; 0.2 s would meet SG-01 only); relay released. `panda/tests/hitl/test_10_hw_watchdog.py` allows 0.12 s from request to relay release (0.1 s + 20 ms relay drive and USB polling); a scope measurement gives the 0.1 s itself |
| M-07 | Brake/cancel → torque zero at EPS | Vehicle, brake press while engaged at constant torque | Closed course | ≤ 0.2 s to EPS torque zero |
| M-08 | Driver override | Steering force gauge, opposing torque; also the N·m scale of `STEER_TORQUE_DRIVER` (`0x260`) and of the `0x2E4` LKA command, which decide the §3.9 override result (sim SIM-OI-8) | Closed course | per TSR-304 |
| M-09 | SoC loop timing | `procLog`, per-process loop timing, model execution time, `sendcan` age histogram over ≥ 10 h of driving | Logs | p99.9 within TSR-602/614 budgets |
| M-10 | Take-over request latency | Fault injection on SoC, camera on display + audio capture | HIL/vehicle | ≤ 1 s |
| M-11 | Forwarding latency camera → car | Timestamped capture on both buses | HIL with real camera | ≤ TSR-707 bound |
| M-12 | FCW onset against a braking lead (§3.8.2) | Closed course with a soft target braking at a known rate; log FCW event time | Reference vehicle | FCW ≤ 0.6 s after lead braking onset at a 1.0 s gap |
| M-13 | PCS braking timing (§3.6; A-PCS-1; OI-4, OI-7; added 2026-10-25, DQ-134 A) | Stock PCS against a stationary soft target, item not installed and item installed but passive; log the PCS request frames on the camera-side bus and the vehicle deceleration (IMU, `carState.aEgo`). Message period also from drive logs | Reference vehicle, closed course, [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md); can share runs with KS-20 of [WP-V-03](../06-validation/WP-V-03-sotif-known-scenarios.md) | Data set: PCS message period, time from request to braking onset, a_PCS. FTTI(SG-07, forwarding loss) confirmed or replaced (OI-4); input to the OI-7 rule |
| M-14 | Watchdog clock spread (T-09a; watchdog impact record OI-2; OI-7; added 2026-10-25, DQ-134 A) | Fault-injection build that stops feeding the IWDG; scope a GPIO toggled at each feed and the reset line; time from the last feed to reset. On each board available, at room temperature and at the ends of the operating range (thermal set-up as WP-H-06 VS-HW-15) | Bench (a panda board; the full HIL bench is not needed) | Worst-case timeout ≤ 0.1 s (TSR-501) over the measured spread, and the LSI spread recorded; input to the OI-7 rule |

Results (template — **Not yet executed**):

| ID | Date | Build | Result | Pass/Fail | Evidence |
|---|---|---|---|---|---|
| M-01…M-14 | — | — | — | — | — |

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm vehicle width, lane-margin design value and a_y,EPS (M-01) and recompute §3.1 | Safety engineer | G2 |
| OI-2 | SG-02 at the ODD curve bound: physical time to departure (≈ 0.7 s) is shorter than driver reaction; HARA owner to review C rating of HE-02.1 or tighten R_ODD (tracked as WP-C-03 OI-7; noted in WP-C-04 §8). *2026-10-16:* the simulation (§3.9, synthetic) shows the same inside the ODD: with assistance lost in a 1.5 m/s² curve the lane line is reached after about 1.3–1.5 s, before a 1.5 s driver correction, even when the siren sounds at 0.25 s. The question therefore covers ordinary curves, not only the ODD bound. *HARA v0.4:* SG-02 is now ASIL C with the curve case rated C3 (DQ-059), and the HARA keeps 1 s to warning as the preliminary FTTI while noting that at the bound the 0.7 s drift is shorter; it asks for the FTTI to be reviewed here. That review is this item. *2026-10-16 (v0.10):* at the 110 km/h ODD bound the times are unchanged within about 0.02 s, and the curve search (§3.9) puts the start of departures at a_y ≈ 0.3–0.4 m/s² (97 of 120 samples leave the lane), so the review concerns most highway curves. *2026-10-17:* with the siren after 0.7 s (DQ-048) 92 of 120 leave the lane and departures start at about 0.4 m/s²; the conclusion holds. *2026-10-20:* with the siren on the arrival revocation (DQ-404 A, about 0.25 s in this host model) 71 of 120 leave the lane and departures start at about 0.5 m/s²; the conclusion holds | HARA owner | G2 |
| OI-3 | Check SG-03 standstill-launch distance assumptions with WP-C-08 | Safety engineer | G2 |
| OI-4 | Measure the PCS message period and braking profile on the reference vehicle (A-PCS-1, A-PCS-2) and confirm or replace the preliminary SG-07 FTTI of §3.6. The acceptable loss is agreed for now: 0.2 s, up to about 4 km/h, accepted until measured (DQ-062, 2026-10-14). The measurement is M-13 (§6; added 2026-10-25, DQ-134 A) | Safety engineer | G2 |
| OI-7 | SG-07 forwarding loss has zero margin (FDTI + FRTI = FTTI). **Decided 2026-10-25 (DQ-134 A): decide after measuring; shorten only if margin is needed.** The zero margin stays on record until two measurements are in: M-13, the PCS braking timing on the reference vehicle (it also confirms or replaces the 0.2 s FTTI, OI-4), and M-14, the watchdog's clock spread on the bench. Rule: the measured margin is the FTTI from M-13 less the FRTI (TSR-706, incl. relay drop-out) and less the longer of the worst-case watchdog timeout from M-14 and the forwarding-supervision time (TSR-711). If it is less than the margin needed (below zero, or below what the HARA review asks for when it agrees the acceptable loss), the watchdog and forwarding-supervision times are shortened below 0.1 s through a change to TSR-501 and TSR-711 with an impact record. Otherwise they stay, and the measured margin replaces the zero. TSR-501 and TSR-711 are not changed now | Safety engineer | G2 |
| OI-5 | Execute M-01…M-14 and fill §6 results | Test lead | G4 |
| OI-6 | Update FSC §8 budgets after this document is approved (FSC OI-4) | Safety engineer | G2 |
| OI-8 | EPS-fault siren latency ≤ 1.26 s worst case from fault onset (T-28; corrected 2026-10-13 from ≈ 1.14 s: the speaker sounds only on every other 8 Hz tick) exceeds the SG-02 1 s warning budget (§3.7). TSR-516's ≤ 0.5 s after detection is met (≤ 0.26 s) only because WP-S-02 v0.14 defines detection as the 1 s persistence; measured from the first fault frame it is not. Caused by the maintainer decision of 2026-10-12 (persistent faults only, 1 s; EPS-fault impact record §7). Options were: shorten the persistence (e.g. 0.7 s), or justify that LKA actuation is already refused from the first fault frame. **Decided 2026-10-14 (register DQ-048): shorten the persistence to about 0.7 s.** WP-S-02 v0.21 TSR-516 now measures detection from the first fault frame and caps the persistence at 0.7 s. Open: the panda firmware change and its HIL timing (M-05/M-10); T-28 stays at 1.26 s until the code changes (added 2026-10-12). **Firmware changed 2026-10-17:** panda `bf8102a` ([jherrodthomas/panda#19](https://github.com/jherrodthomas/panda/pull/19)) sets the persistence to 0.7 s; T-28 ≤ 0.96 s. Still open: the HIL timing (M-05/M-10) | Safety manager | G2 |
| OI-9 | **Closed 2026-10-17** (DQ-061, A, decided 2026-10-14): heartbeat loss when authority ended within the 5 s before it needs no fast siren, because the driver has already been told of the disengagement. TSR-516(a) (WP-S-02 v0.29) now asks for ≤ 0.5 s only while authority is granted and ≤ 5 s for this case, which the 1 Hz siren at 4–5 s (T-07) meets; no firmware change (added 2026-10-13) | Safety manager | G2 |
| OI-10 | The EPS behaviour after `0x2E4` stops (M-02) decides most simulated outcomes: release gives about 1.3–1.5 s to the lane line, hold about 3.1–3.5 s (§3.9). Make M-02 the first vehicle measurement, then re-run the simulation with the measured behaviour (added 2026-10-16) | Test lead | G2 |
| OI-11 | SG-08 (HARA v0.4): measure the DM end-to-end alert time (camera frame, `dmonitoringmodeld` latency, policy timer, alert output) against the 6 s FTTI, and confirm or shorten the preliminary time to the no-response reaction (18 s / 30 s, §3.8.4; reaction decided, DQ-365 A) with the WP-C-08 validation | Safety engineer | G2 |
