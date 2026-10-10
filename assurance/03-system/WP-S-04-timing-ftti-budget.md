# WP-S-04 Timing Analysis: FTTI, Fault Detection and Reaction Budget

| Field | Value |
|---|---|
| Work product | WP-S-04 Timing analysis: FTTI, fault detection and reaction budget |
| Standard reference | ISO 26262-4:2018 §6 (fault tolerant time interval, fault detection and fault reaction time intervals, emergency operation); ISO 26262-3:2018 §7 (FTTI as FSC input); ISO 26262-1:2018 (definitions, by reference); ASPICE 4.0 SYS.3 |
| Version | 0.1 |
| Status | Draft — kinematic estimates only; no measurement has been performed |
| ASIL / scope | SG-01 (D until re-rated, B‡), SG-03…SG-05 (C), SG-02, SG-06, SG-07 (B) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

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

Continuous. Forwarding latency (TSR-707) and relay state on MCU hang (GAP-43) matter; there is no detection budget, only a design requirement that the stock path is never interrupted for longer than the PCS can tolerate (TBD with the PCS message timing, OI-4).

### 3.7 Summary of FTTIs and budgets

| SG / fault class | FTTI | FDTI budget | FRTI budget | Margin |
|---|---|---|---|---|
| SG-01 continuous limits | per frame | 0 | ≤ 10 ms (+ TSR-109) | — |
| SG-01 RX loss/corruption | 0.5 s | ≤ 0.2 s (TSR-401) | ≤ 0.1 s | ≥ 0.2 s |
| SG-01 SoC heartbeat loss | 0.5 s | ≤ 0.3 s (TSR-407) | ≤ 0.1 s | ≥ 0.1 s |
| SG-01 SoC command stall | 0.5 s | ≤ 0.05 s (TSR-408) | ≤ 0.1 s | ≥ 0.35 s |
| SG-01 MCU execution fault | 0.5 s | ≤ 0.2 s (TSR-501) | ≤ 0.1 s (reset + relay release) | ≥ 0.2 s |
| SG-01 relay stuck | 0.5 s | ≤ 0.3 s (TSR-506) | ≤ 0.1 s | ≥ 0.1 s |
| SG-02/06 loss without warning | 1 s to warning | ≤ 0.5 s | ≤ 0.5 s | — (see §3.2) |
| SG-03/04 | 1 s | ≤ 0.5 s | ≤ 0.3 s | ≥ 0.2 s |
| SG-05 brake/cancel | 0.2 s | ≤ 30 ms | ≤ 10 ms + EPS/PCM | TBD |
| SG-05 steering override | 0.2 s | ≤ 40 ms + t_ovr | ≤ 0.1 s | TBD |

## 4. Current detection and reaction times (code-derived)

| # | Mechanism | Code | Derivation | Worst-case time |
|---|---|---|---|---|
| T-01 | RX timeout | `opendbc_repo/opendbc/safety/safety.h:321-344`; called at 1 Hz from `panda/board/main.c:241-242` | threshold max(10 × period, 1 s); for the Corolla messages 10 × period is 120 ms (`0xAA` 83 Hz), 200 ms (`0x260` 50 Hz), 303 ms (`0x1D2` 33 Hz), 250 ms (`0x226` 40 Hz), so 1 s applies; evaluated once per second | **1–2 s** |
| T-02 | RX checksum / quality | `safety.h:112-121, 164-197` | on receipt | 1 message period (12–30 ms) |
| T-03 | RX counter | — | no Toyota counters (`modes/toyota.h:39-46`) | not detected |
| T-04 | Brake / cruise revoke | `safety.h:350-356, 518-527` | on receipt | 25 ms (brake 40 Hz), 30 ms (cruise 33 Hz) |
| T-05 | Heartbeat engaged mismatch | `panda/board/main.c:181-189` | 3 consecutive 1 Hz ticks | **2–3 s** |
| T-06 | Heartbeat loss → SILENT | `main.c:101-103, 153-162, 191-213` | counter +1 per 1 Hz tick, reset by each `0xf3`; ≥ 5 with ignition, ≥ 2 without | **4–5 s** (ign on), 1–2 s (ign off) |
| T-07 | Siren after heartbeat loss | `main.c:169-171, 198-201` | 3 s siren if authority within last 5 s | starts at T-06 |
| T-08 | Relay malfunction | `safety.h:372-380` | first offending frame after `safety_mode_cnt > 1` (1 Hz) | 1–2 s after mode set; then immediate |
| T-09 | Software watchdog | `panda/board/drivers/simple_watchdog.h`; `main.c:119, 301` | 375 ms threshold, checked from the 8 Hz tick it supervises | cannot detect a tick-ISR hang |
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

## 5. Comparison and required changes

| Fault class | Budget | Baseline | Verdict | Required change | TSR |
|---|---|---|---|---|---|
| RX loss | ≤ 0.2 s | 1–2 s (T-01) | **Not met** | 5 periods, evaluation ≥ 50 Hz (move timeout check out of the 1 Hz path) | TSR-401 |
| RX stuck/inserted | ≤ 0.2 s | not detected (T-03) | **Not met** | rate, frozen-content, cross-checks | TSR-403…405 |
| SoC heartbeat loss | ≤ 0.3 s | 4–5 s (T-06) | **Not met** | evaluate at ≥ 10 Hz; revoke at 0.3 s; SILENT ≤ 2 s | TSR-407, 510 |
| Host/panda mismatch | ≤ 0.3 s | 2–3 s (T-05), 2 s (T-17) | **Not met** | 0.3 s both sides | TSR-307 |
| SoC command stall | ≤ 0.05 s | 0.1 s at host (T-13), then EPS ≈ 2 s (T-23) | **Not met** | command-frame freshness in the MCU + active zero frame | TSR-408, 109 |
| MCU hang | ≤ 0.2 s | not detected (T-09) | **Not met** | IWDG | TSR-501 |
| Relay stuck released | ≤ 0.3 s | 1–2 s window (T-08) | **Not met** | readback | TSR-506 |
| Brake / cancel | ≤ 30 ms | 25–30 ms (T-04) | Met (envelope side) | verify EPS/PCM response; TSR-109 | TSR-302, 109 |
| Steering override | ≤ 0.2 s | not in envelope | **Not met** | driver-torque monitor | TSR-304 |
| Stale SoC inputs | ≤ 0.2 s actuation on failed input | 3–3.5 s (T-14 + T-16) | **Not met** | immediate disable for untrusted inputs; freshness in controlsd | TSR-601, 602 |
| Diagnostic masking | none while engaged | 5 s (T-22) | **Not met** | remove masking / exclude E-06 | TSR-603 |
| Cruise mismatch | ≤ 1 s with reaction | 6 s, no reaction (T-19) | **Not met** | 1 s, warn + cancel | TSR-308 |
| `sendcan` age | ≤ 20 ms | 1 s (T-11) | **Not met** | 20 ms | TSR-614 |
| Take-over request | ≤ 1 s after detection | alerts immediate; timing unverified | To verify | measure | TSR-606 |

Implementation note: the panda tick handler runs at 8 Hz and the safety checks are "decimated to 1 Hz" (`main.c:105-106, 142-143`). The required budgets need a periodic safety task of at least 50 Hz (TSR-401) on a timer independent of the comms interrupts, with its completion feeding the IWDG service point (TSR-501). The architectural change is recorded in [WP-W-03](../05-software/WP-W-03-software-architecture.md).

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
| M-05 | Heartbeat loss and command stall | Stop `0xf3`; stop `sendcan` while heartbeat continues | HIL | ≤ 0.3 s / ≤ 0.05 s to SS-L |
| M-06 | MCU hang | Inject infinite loop in tick / main / ISR via debug build | HIL | reset ≤ 0.2 s; relay released |
| M-07 | Brake/cancel → torque zero at EPS | Vehicle, brake press while engaged at constant torque | Closed course | ≤ 0.2 s to EPS torque zero |
| M-08 | Driver override | Steering force gauge, opposing torque | Closed course | per TSR-304 |
| M-09 | SoC loop timing | `procLog`, per-process loop timing, model execution time, `sendcan` age histogram over ≥ 10 h of driving | Logs | p99.9 within TSR-602/614 budgets |
| M-10 | Take-over request latency | Fault injection on SoC, camera on display + audio capture | HIL/vehicle | ≤ 1 s |
| M-11 | Forwarding latency camera → car | Timestamped capture on both buses | HIL with real camera | ≤ TSR-707 bound |

Results (template — **Not yet executed**):

| ID | Date | Build | Result | Pass/Fail | Evidence |
|---|---|---|---|---|---|
| M-01…M-11 | — | — | — | — | — |

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm vehicle width, lane-margin design value and a_y,EPS (M-01) and recompute §3.1 | Safety engineer | G2 |
| OI-2 | SG-02 at the ODD curve bound: physical time to departure (≈ 0.7 s) is shorter than driver reaction; HARA owner to review C rating of HE-02.1 or tighten R_ODD (tracked as WP-C-03 OI-7; noted in WP-C-04 §8) | HARA owner | G2 |
| OI-3 | Check SG-03 standstill-launch distance assumptions with WP-C-08 | Safety engineer | G2 |
| OI-4 | Obtain PCS message timing requirements to bound forwarding latency and relay transitions (TSR-707) | Safety engineer | G2 |
| OI-5 | Execute M-01…M-11 and fill §6 results | Test lead | G4 |
| OI-6 | Update FSC §8 budgets after this document is approved (FSC OI-4) | Safety engineer | G2 |
