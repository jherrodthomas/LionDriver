# WP-C-03 Hazard Analysis and Risk Assessment (HARA)

| Field | Value |
|---|---|
| Work product | WP-C-03 Hazard analysis and risk assessment, safety goals |
| Standard reference | ISO 26262-3:2018 §6 (and Annex B for E/C classification guidance); shared hazard log with ISO 21448 §6 |
| Version | 0.3 (Figures 2-1 and 6-1 added, generated from the model and this document; 2026-10-13). 0.2 (Cartesian method, 2026-10-12) |
| Status | Draft — **ratings are proposals for review. They are not approved and must not be used to argue safety until the confirmation review (I3) passes** |
| ASIL / scope | Item LD-SDA, reference configuration |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review by an independent assessor (I3) per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `3ed97c8` (code unchanged since `8b8c6ae` apart from `process_replay/ref_commit`) |

## 1. Scope and inputs

- Item: [WP-C-01 item definition](WP-C-01-item-definition.md) (functions F-01…F-09, boundary, AOU-01…AOU-11).
- ODD: [WP-C-02](WP-C-02-odd-and-intended-functionality.md).
- The HARA rates **malfunctioning behaviour of the item** (E/E faults). Hazards caused by functional insufficiencies of the intended functionality (perception and ML performance limits) and by misuse use the same hazard list, but they are evaluated in [WP-C-05](WP-C-05-sotif-hazard-identification.md) under ISO 21448.
- As ISO 26262-3 §6 requires, the item's own safety mechanisms (the panda envelope, selfdrived checks, DM) are **not** credited in the ratings. External measures and existing vehicle elements (the EPS's own LKA torque authority, the brake system, the PCM) are credited in controllability **only where an AoU states it**. If that AoU fails verification, the alternative rating shown applies.

## 2. Method

The HARA uses a **Cartesian (matrix) method**, generated with the hara-builder tool. The full matrix is in [`hara/WP-C-03-hara-cartesian.xlsx`](hara/WP-C-03-hara-cartesian.xlsx). Every analyst input is held as readable data in [`hara/hara_model.py`](hara/hara_model.py), and the step counts are in [`hara/hara-cartesian-summary.md`](hara/hara-cartesian-summary.md). For review, every hazardous-event row is also in [`hara/hara-events.csv`](hara/hara-events.csv) (one line per row, with rationale), and the function × guide-word classification is in [`hara/hara-function-guideword.csv`](hara/hara-function-guideword.csv).

1. **Functions** F-01…F-09 are taken from [WP-C-01 §2.1](WP-C-01-item-definition.md).
2. **Malfunction identification.** All 14 guide words (M01 No function, M02 Stops functioning, M03 Unrequested, M04 Stuck, M05 Excessive, M06 Partial, M07 Early, M08 Late, M09 Too short, M10 Too long, M11 Delayed, M12 Inverse, M13 Erratic, M14 Uneven) are applied to every function: 9 × 14 = 126 pairs.
   - Each pair is classified SC (safety-critical), NSC or NA, with a rationale. All 126 rows stay in the workbook (tab 11), so nothing is dropped without a reason.
   - An SC pair whose vehicle-level response is identical to another SC pair is marked *subsumed by* that pair and is not expanded twice.
3. **Situation analysis.** Each SC pair that is not subsumed is crossed with 15 operational situations (§3) and 6 weather/surface conditions (§3.1), giving 90 combinations per pair. Situations OS-14 and conditions W04–W06 are outside the ODD and are included as reasonably foreseeable misuse.
4. **Classification of every row.**
   - Severity S0–S3, using injury potential to occupants and other road users. S0 is used where the malfunction is **not hazardous in that situation**, and the row records why. This is how combinations are screened out without deleting them.
   - Exposure E0–E4 per ISO 26262-3:2018 Table B.2 (duration). The combination of a situation and a condition is rated no more frequent than the rarer of the two:

     | Class | Share of operating time |
     |---|---|
     | E4 | > 10 % |
     | E3 | 1–10 % |
     | E2 | < 1 % |
     | E1 | very rare |

     The generator's own default exposure anchors differ from Table B.2, so the workbook's exposure tab is corrected after generation (`hara_model.py --postprocess`).
   - Controllability C0–C3 for a typical attentive driver; for other road users, their ability to avoid harm. Ratings that credit an unverified AoU are flagged ⚠, and the summary also gives the result with C+1 (AoU fails).
   - S and C come from rating rules per hazard and situation (`RULES` in `hara_model.py`), adjusted for the condition (e.g. snow/ice C+1 for lateral hazards). Each rule carries its rationale into the workbook row.
5. **ASIL determination.** The ASIL is computed in the workbook with the ISO 26262-3 Table 4 lookup and checked against an independent computation in `hara_model.py`; all rows agree. An equivalent rule is to sum the numeric class levels:

   | S + E + C | ASIL |
   |---|---|
   | 10 | D |
   | 9 | C |
   | 8 | B |
   | 7 | A |
   | ≤ 6 | QM |

   Any class at 0 gives QM (S0: no ASIL).
6. **Hazardous events and safety goals.**
   - The generator groups ASIL-rated rows per (function, hazard) as candidate goals (workbook tab 13).
   - These are consolidated per vehicle-level hazard into SG-01…SG-07 (§6), each taking the highest ASIL of its rows. For each distinct worst case, §5 records a representative hazardous event (HE) with full rationale.
   - The HE rows in §5 are the governing cases. The workbook holds every combination behind them.
7. **Scope variant.** Experimental Mode (D-08) is not decided, so a second workbook ([`hara/WP-C-03-hara-cartesian_experimental.xlsx`](hara/WP-C-03-hara-cartesian_experimental.xlsx)) adds function F-02X and shows what option B would add (§5.10).

Rationale is given for every rating. Ratings that depend on unverified AoUs are flagged ⚠.

### 2.1 Counts

<!-- hara-counts:start (generated by hara/hara_model.py) -->
| Step | Reference scope (Chill only) | With Experimental Mode |
|---|---|---|
| Functions × guide words | 9 × 14 = 126 | 10 × 14 = 140 |
| Pairs classified SC / NSC / NA | 53 / 47 / 26 | 64 / 48 / 28 |
| SC pairs expanded (not subsumed) | 31 | 33 |
| Rows generated (pairs × 15 situations × 6 conditions) | 2790 | 2970 |
| Rows not hazardous in that situation (S0, reason recorded) | 852 | 936 |
| Rows rated QM | 717 | 775 |
| Rows rated ASIL A / B / C / D | 565 / 630 / 26 / 0 | 589 / 644 / 26 / 0 |
| Rows ASIL A / B / C / D if every ⚠ AoU fails | 542 / 642 / 267 / 26 | 570 / 672 / 273 / 26 |
| Distinct hazardous events (function × guide word × situation, S ≠ S0) | 323 | 339 |
| … with ASIL ≥ A in at least one condition | 287 | 299 |
<!-- hara-counts:end -->

Representative hazardous events recorded in §5: 30 (HE-01.1 … HE-08.1), plus 2 variant events for Experimental Mode (§5.10).

The table above is written by `hara_model.py`; CI runs `hara_model.py --check`, which fails if this table or [`hara-cartesian-summary.md`](hara/hara-cartesian-summary.md) no longer match the model.

![Figure 2-1: two ISO 26262-3 Table 4 matrices (S1–S3 × E1–E4 rows, C1–C3 columns) coloured by ASIL, giving the number of reference-scope hazardous-event rows per cell as rated and if every ⚠ AoU fails](hara/figures/fig-c03-2-1-asil-heatmap.svg)

*Figure 2-1.* Where the reference-scope rows fall in the ASIL matrix: left as rated, right with C+1 on every row whose controllability credits an unverified AoU (⚠). Rows rated S0 are not shown. Drawn from the rows of `hara_model.py` (the same data as [`hara-events.csv`](hara/hara-events.csv) and the table above); the per-class totals equal the §2.1 counts. Source: [`hara/figures/fig-c03-2-1-asil-heatmap.svg`](hara/figures/fig-c03-2-1-asil-heatmap.svg), generated by [`hara/hara_figures.py`](hara/hara_figures.py); change the rating rules in `hara_model.py` and regenerate, do not edit the SVG.

## 3. Operational situation catalogue

The situations come from the ODD ([WP-C-02 §3](WP-C-02-odd-and-intended-functionality.md)). OS-11 (wet road) of version 0.1 is now the weather/surface dimension (§3.1); its ID is not reused. OS-12…OS-16 are new in version 0.2. The list is held in `SITUATIONS` in [`hara_model.py`](hara/hara_model.py).

| ID | Situation | Speed (km/h) | Exposure (within ODD unless stated) |
|---|---|---|---|
| OS-01 | Limited-access highway, free flow, adjacent traffic | 90–120 | E4: Majority of engaged time (ODD-H) |
| OS-02 | Highway curve near R_ODD with barrier or adjacent traffic | 70–110 | E3: Curves of this radius at speed: 1–10 % of time |
| OS-03 | Undivided rural or arterial road, oncoming traffic | 60–90 | E4: Large share of ODD-A driving |
| OS-04 | Urban arterial, pedestrians and cyclists near the lane edge | 30–60 | E3: Secondary ODD (ODD-A) |
| OS-05 | Following a lead vehicle at a short gap, dense traffic | 30–110 | E4: Most engaged time has a lead vehicle |
| OS-06 | Stop-and-go queue or standstill behind a lead; pedestrians may cross | 0–30 | E3: Congestion share of driving |
| OS-07 | Approaching slower or stationary traffic from highway speed | 70–120 | E3: Several times per trip, short duration |
| OS-08 | Close following vehicle behind (gap < 1.5 s) | 50–120 | E4: Common in dense traffic |
| OS-09 | Imminent collision where the stock PCS/AEB would intervene | 0–120 | E2: PCS-relevant situations are rare |
| OS-10 | Driver override while engaged: braking, cancel or evasive steering | 0–120 | E3: Overrides are frequent but short; emergency cases rarer |
| OS-12 | Driver-initiated assisted lane change | 70–120 | E3: Lane changes: short duration, several per trip |
| OS-13 | Manual driving, item powered but not engaged | 0–120 | E4: Large share of onroad time with the device installed |
| OS-14 | Engaged outside the ODD (residential street, ramp, tight curve): foreseeable misuse | 15–60 | E2: Engagement is possible anywhere; misuse share assumed < 1 % |
| OS-15 | Approaching a signalised or stop-controlled intersection (ODD-A) | 30–90 | E3: Frequent on arterials, short duration |
| OS-16 | Rural or arterial curve near R_ODD with oncoming traffic | 60–90 | E3: Curves of this radius: 1–10 % of time |

### 3.1 Weather and surface conditions

| ID | Condition | Exposure | ODD |
|---|---|---|---|
| W01 | Dry, daylight | E4 | In ODD |
| W02 | Wet road or light rain | E3 | In ODD |
| W03 | Night, dry, headlights | E3 | In ODD |
| W04 | Moderate or heavy rain (outside ODD, foreseeable) | E2 | Outside ODD |
| W05 | Snow or ice (outside ODD, foreseeable) | E2 | Outside ODD |
| W06 | Fog, visibility below the ODD bound (outside ODD, foreseeable) | E1 | Outside ODD |

## 4. Hazard identification (malfunctioning behaviour → vehicle-level hazard)

All 126 function × guide-word pairs, with classification and rationale, are in workbook tab 11 and in `FM` in [`hara_model.py`](hara/hara_model.py). This table lists the SC pairs per vehicle-level hazard; every other pair is NSC or NA with a written reason.

| Hazard | Expanded SC pairs (function guide word) | Subsumed SC pairs (→ pair that covers them) |
|---|---|---|
| **H-01** Unintended or excessive lateral motion | F-01 M03, F-01 M05, F-01 M07, F-01 M12, F-01 M13, F-03 M03 | F-01 M10→M03, F-01 M14→M05, F-03 M12→M03 |
| **H-02** Unannounced loss or degradation of lateral control | F-01 M01, F-01 M02, F-01 M04, F-01 M06, F-01 M11, F-03 M02, F-08 M04 | F-01 M08→M11, F-01 M09→M02, F-03 M13→M02, F-08 M05→M04, F-08 M13→M04 |
| **H-03** Unintended acceleration | F-02 M04, F-02 M05, F-02 M12 | — |
| **H-04** Unintended or excessive deceleration | F-02 M03, F-02 M10, F-02 M13, F-04 M03, F-06 M03 | F-02 M07→M03, F-04 M05→M03, F-04 M07→M03 |
| **H-05** Driver unable to override or disengage | F-03 M01, F-03 M06, F-03 M11 | F-03 M04→M01, F-03 M08→M11, F-03 M10→M01 |
| **H-06** Unannounced loss of longitudinal deceleration | F-02 M01, F-02 M02, F-02 M06, F-02 M11 | F-02 M08→M11, F-02 M09→M02 |
| **H-07** Displayed system state differs from actual state (mode confusion) | F-05 M01, F-05 M04 | F-05 M02→M01, F-05 M06→M01, F-05 M08→M01, F-05 M09→M01, F-05 M11→M01, F-05 M12→M04 |
| **H-08** Suppression of the vehicle's stock pre-collision braking | F-08 M03 | — |

Pairs classified NSC that need a note:

| Pair | Why not a hazardous event of its own |
|---|---|
| F-04 M01/M02/M04/M06/M08/M11 (DM fails to detect inattention) | Not a vehicle-level hazard by itself. It is a latent fault of a measure that the controllability of H-02 and H-06 relies on. Handled in the FSC (FSR on DM integrity) and in SOTIF misuse analysis ([WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md)) |
| F-08 M01/M02/M06/M08/M10/M11 (envelope limits or gating not enforced) | Latent fault of a safety mechanism; hazardous only together with an F-01/F-02/F-03 malfunction (dual-point). Handled through the FSC/TSC and the hardware metrics, not rated as a separate event (ISO 26262-3 §6: safety mechanisms of the item are not credited in the HARA) |
| F-06 M01 / F-07 all (missing FCW or LDW, false LDW) | No actuation; the driver is responsible and the stock PCS gives its own warning (subject to H-08) |
| F-09 all (logging, upload, remote access, update) | No kinetic authority. Cyber-induced effects are analysed in the TARA ([WP-C-09](WP-C-09-tara.md)) and map onto H-01…H-08 |

**H-07 (mode confusion)** was reserved in version 0.1 and rated only through H-02, H-05 and H-06. The guide-word pass on F-05 (M01 missing take-over alert, M04 frozen or wrong engagement indication) makes it a hazard with its own events (§5.7). Its events are covered by SG-02 and SG-06, whose take-over-warning wording already includes a wrong state indication (§6).

## 5. Hazardous events and risk assessment

### 5.1 H-01 Unintended or excessive lateral motion

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-01.1 | OS-03 undivided road, oncoming traffic, 60–90 km/h | Departure into the oncoming lane; head-on collision | S3 | E4 | C2 ⚠ | **C** | S3: head-on at combined speeds > 100 km/h, life-threatening. E4: undivided roads make up a large share of driving. C2 ⚠: credits AOU-01/AOU-02 (EPS limits LKA torque to an overpowerable level). A supervising driver with hands near the wheel corrects a sustained limited-torque deviation within ~1 s in most cases (≥ 90%). **If AOU-01/02 are not verified: C3 → ASIL D** |
| HE-01.2 | OS-01/OS-02 highway, adjacent traffic or barrier, 90–120 km/h | Lateral departure into an adjacent vehicle or barrier | S3 | E4 | C2 ⚠ | **C** | As HE-01.1. Lateral deviation at speed with adjacent traffic can trigger loss of control or secondary collisions |
| HE-01.3 | OS-04 urban, pedestrians and cyclists near the lane edge, 30–60 km/h | Vehicle drifts into a vulnerable road user | S3 | E3 | C2 ⚠ | **B** | S3: VRU impact above 30 km/h. E3: urban VRU proximity within the ODD. C2: lower speed gives more time but less lateral margin. If AOU-01/02 fail: C3 → ASIL C |
| HE-01.4 | Torque while not engaged, OS-01/OS-03, driver steering manually | Unexpected steering disturbance during manual driving | S3 | E4 | C2 ⚠ | **C** | Driver hands on the wheel (manual driving), so C2 rather than C3. Same S/E as HE-01.1. If AOU-01/02 fail: C3 → ASIL D |

### 5.2 H-02 Unannounced loss or degradation of lateral control

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-02.1 | OS-02 highway curve, driver supervising, possibly hands off (foreseeable: openpilot does not require hands on the wheel) | Vehicle goes straight in the curve and departs the lane | S3 | E3 | C2 | **B** | S3: departure at highway speed into a barrier or adjacent traffic. E3: curves of this radius at speed. C2: a supervising driver notices the drift and corrects it. Loss without warning delays the reaction; hands-off use is foreseeable |
| HE-02.2 | OS-16 rural curve with oncoming traffic | Departure into the oncoming lane | S3 | E3 | C2 | **B** | As HE-02.1 |
| HE-02.3 | Frozen (stuck) torque command at its last value | Steering bias continues while the road changes | S3 | E3 | C2 ⚠ | **B** | A stuck request is bounded by EPS authority (AOU-01). It behaves like HE-01 at reduced magnitude |
| HE-02.4 | OS-01 highway, straight or gentle curve, 90–120 km/h; lateral control silently lost (F-01 M01/M02/M04/M06/M11, F-03 M02 unannounced disengagement, F-08 M04 envelope stuck blocking) | Slow drift out of the lane at highway speed | S3 | E4 | C1 | **B** | S3: lane departure at highway speed. E4: majority of engaged time. C1: on a straight road the drift is slow and a supervising driver notices and corrects it (≥ 99 %). New in 0.2: the Cartesian shows this governs SG-02 by frequency, not only the curve case |
| HE-02.5 | OS-12 driver-initiated assisted lane change | Lateral control lost mid-manoeuvre; vehicle straddles lanes next to traffic | S3 | E3 | C2 | **B** | S3: contact with traffic in the target or original lane. E3: lane changes are short but frequent. C2: the driver initiated the manoeuvre and is attentive, but loss without warning delays the reaction |

### 5.3 H-03 Unintended acceleration

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-03.1 | OS-05 following a lead at a short gap | Rear-end collision with the lead vehicle | S2 | E4 | C2 ⚠ | **B** | S2: moderate speed difference in following. C2 credits AOU-03 (driver braking overrides) and AOU-05 (PCM bounds the ACC acceleration request). Without AOU-05, high-magnitude acceleration is possible → C3 → ASIL C |
| HE-03.2 | OS-06 standstill in a queue, pedestrian crossing in front | Vehicle moves off and hits a pedestrian | S3 | E3 | C2 | **B** | S3: VRU. E3: stop-and-go with crossing pedestrians. C2: the driver must brake immediately; a low-speed launch is limited |
| HE-03.3 | OS-07 approaching a slower lead | Acceleration toward the lead instead of deceleration | S3 | E3 | C2 ⚠ | **B** | High closing speed. The driver supervises and can brake; credits AOU-03/AOU-05. Without them → C3 → ASIL C |
| HE-03.4 | OS-02 highway curve or OS-16 rural curve (F-02 M04 stuck positive, M05 excessive, M12 inverse) | Speed rises in the curve beyond the lateral limit; run-off or into the oncoming lane | S3 | E3 | C2 ⚠ | **B** | S3: run-off at curve speed. E3: curves near R_ODD. C2 credits AOU-03/AOU-05 (driver braking overrides; PCM bounds acceleration). Without them → C3 → ASIL C |
| HE-03.5 | OS-01 highway free flow (F-02 M04/M05/M12) | Speed rises above the set speed; moderate impacts if traffic slows | S2 | E4 | C1 ⚠ | **A** | S2: moderate speed difference. E4. C1: the driver brakes; acceleration bounded to +2.0 m/s² by the envelope. Credits AOU-03; without it → C2 → ASIL B |

### 5.4 H-04 Unintended or excessive deceleration

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-04.1 | OS-08 close following vehicle, 50–120 km/h | Rear-end impact by the following vehicle | S2 | E4 | C2 ⚠ | **B** | S2: rear impacts on a modern car are mostly S1–S2. Severe at large speed differences, but deceleration is limited by the PCM's ACC envelope (AOU-05). C2: the following driver and the ego driver (pressing gas overrides) can usually react. If the deceleration is unbounded (AOU-05 fails) → C3 → ASIL C |
| HE-04.2 | OS-02/OS-16 curve on a wet road (W02) | Instability under unexpected braking | S3 | E3 | C1 ⚠ | **A** | VSC available (AOU-10; if it fails: C2 → ASIL B). Moderate ACC deceleration on wet roads is controllable for most drivers |
| HE-04.3 | OS-08 close follower; driver monitoring escalates to forced deceleration although the driver is attentive (F-04 M03) | Rear impact by the following vehicle | S2 | E4 | C2 ⚠ | **B** | New in 0.2: DM is a source of H-04, not only a controllability measure. Same S/E/C as HE-04.1 (deceleration bounded by the PCM, AOU-05). Without AOU-05 → C3 → ASIL C |
| HE-04.4 | OS-13 manual driving, item not engaged; the item commands braking (F-02 M03) | Rear impact by the following vehicle during manual driving | S2 | E4 | C2 ⚠ | **B** | E4: most onroad time with the device installed is not engaged. C2 credits AOU-05. The envelope's engagement gating is not credited (ISO 26262-3 §6). Without AOU-05 → C3 → ASIL C |
| HE-04.5 | OS-08 close follower; false FCW provokes driver reflex braking (F-06 M03) | Rear impact by the following vehicle | S2 | E4 | C1 | **A** | New in 0.2 (version 0.1 rated false FCW QM). The warning does not actuate; most drivers glance at the scene and brake moderately or not at all (C1). The model FCW also fires when not engaged (`selfdrived.py:442`) |

### 5.5 H-05 Driver unable to override or disengage

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-05.1 | OS-10 driver emergency braking while the system keeps commanding acceleration | Longer stopping distance; collision | S3 | E3 | C2 ⚠ | **B** | Credits AOU-03 (the brake system works mechanically and the PCM cancels ACC on brake). Without AOU-03 → C3 → ASIL C |
| HE-05.2 | OS-10 driver evasive steering while the system keeps commanding counter-torque | Evasive manoeuvre impaired; collision | S3 | E3 | C2 ⚠ | **B** | Credits AOU-01/AOU-02 (driver can overpower the EPS LKA torque). Without them → C3 → ASIL C |
| HE-05.3 | Cancel or brake does not disengage; the system stays engaged when the driver believes it is off | Mode confusion, then unexpected actuation (leads to H-01 or H-03) | S3 | E3 | C2 | **B** | Rated with the effect hazards |
| HE-05.4 | OS-10 brake or cancel releases one axis only (F-03 M06 partial disengagement) | Continued lateral or longitudinal actuation during the driver's emergency action | S3 | E3 | C2 ⚠ | **B** | As HE-05.1/05.2; credits AOU-01/02/03. Without them → C3 → ASIL C |

### 5.6 H-06 Unannounced loss of longitudinal deceleration

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-06.1 | OS-07 approaching stationary or slow traffic at highway speed; the system silently stops decelerating (for example, a stale plan holds zero acceleration) | High-speed rear-end collision | S3 | E3 | C2 | **B** | S3: high closing speed. E3. C2: supervising driver, but reliance on ACC delays the reaction. The stock PCS may mitigate this but is not credited (it is a separate system, and AOU-04 is unverified) |
| HE-06.2 | OS-06 slow queue | Low-speed rear-end collision | S1 | E3 | C2 | **QM** | S1: low-speed impact, light injuries |
| HE-06.3 | OS-05 following a lead at a short gap; the lead brakes and the deceleration is silently lost (F-02 M01/M02/M06/M11) | Rear-end collision at moderate speed difference | S2 | E4 | C2 | **B** | S2: following speeds, moderate speed difference. E4: most engaged time has a lead. C2: supervising driver, but reliance on ACC delays the reaction |

### 5.7 H-07 Displayed system state differs from actual state (mode confusion)

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-07.1 | OS-02 highway curve or OS-16 rural curve; the system has disengaged but still shows engaged, or the take-over alert is missing (F-05 M01/M04) | The driver believes the system steers; departure in the curve | S3 | E3 | C2 | **B** | S3: departure into barrier, traffic or the oncoming lane. E3: curves near R_ODD. C2: the drift develops quickly and the driver's belief that the system is active delays the reaction |
| HE-07.2 | OS-01 highway, straight or gentle curve | The driver believes the system steers; slow lane departure | S3 | E4 | C1 | **B** | S3: departure at highway speed. E4. C1: slow drift on a straight road; an attentive driver notices it |
| HE-07.3 | OS-07 approaching slower or stationary traffic; the driver believes ACC is active | The driver expects the vehicle to slow; high closing speed | S3 | E3 | C2 | **B** | S3: high closing speed. E3. C2: reliance on a function that is not active |

### 5.8 H-08 Suppression of the vehicle's stock pre-collision braking

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-08.1 | OS-09 imminent collision where the stock PCS would have braked (engaged or not engaged) | Collision not mitigated | S3 | E2 | C3 | **B** | S3: PCS-relevant impacts. E2: PCS-relevant situations are rare. C3: by definition the driver did not avoid the situation. The item must not degrade a stock safety function, whether or not LD-SDA is engaged |

### 5.9 Malfunctions rated QM

| Malfunction | Rating | Rationale |
|---|---|---|
| Missing FCW (F-06) | QM | The warning supplements driver supervision. The stock PCS gives its own warning (subject to H-08) |
| False FCW (F-06) without a close follower | QM | Startle without actuation, or a moderate driver brake (S1). With a close follower it is HE-04.5 (ASIL A). Recurrent false alerts are a SOTIF and HMI concern ([WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md)) |
| Missing LDW (F-07) | QM | Manual driving with the driver in full control |
| Loss of logging or upload | QM | No effect on vehicle motion. Relevant to field monitoring and cybersecurity only |

### 5.10 Scope variant: Experimental Mode (only if D-08 option B is chosen)

Rated in [`hara/WP-C-03-hara-cartesian_experimental.xlsx`](hara/WP-C-03-hara-cartesian_experimental.xlsx). These events are **not** part of the reference HARA and have no `HE-` IDs, so they do not enter the hazard log unless the scope changes.

| Variant event | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| EX-09.1 | OS-15 approaching a signalised or stop-controlled intersection (F-02X M01 does not stop) | Vehicle enters the intersection against a red light or stop sign | S3 | E3 | C2 ⚠ | B | C2 needs evidence: Experimental Mode invites over-trust that it stops (SH-09, WP-C-05). Without it → C3 → ASIL C. Would need a new safety goal ("SG-09", ASIL B) |
| EX-04.1 | OS-05/OS-08 dense traffic, false stop for a misread signal or shadow (F-02X M03) | Rear impact by the following vehicle | S2 | E4 | C2 ⚠ | B | Same as HE-04.1; covered by SG-04 |

## 6. Safety goals

| ID | Safety goal | ASIL | Source HEs | Safe state | Preliminary FTTI | Notes |
|---|---|---|---|---|---|---|
| **SG-01** | The item shall not cause lateral motion of the vehicle that exceeds what the driver can control, including any steering actuation while the item is not engaged | **C** ⚠ (D if AOU-01/02 fail) | HE-01.1–01.4, HE-02.3 | LKA torque request zero, steer request bit cleared; driver informed | **≤ 0.5 s** (preliminary: `docs/SAFETY.md` cites 0.9 s to reach 1 m lateral deviation at maximum actuation; FTTI to be derived in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md)) | The current envelope detection times (RX ≤ 2 s, heartbeat 3–5 s) are not consistent with this FTTI (GAP-06). The envelope's continuous limiting (magnitude, rate, measured tracking) does act within one frame |
| **SG-02** | The item shall not lose or degrade lateral control while engaged without giving the driver an adequate take-over warning | **B** | HE-02.1–02.2, HE-02.4–02.5, HE-07.1–07.2 | Driver warned (visual + acoustic) and lateral control handed back with a smooth torque ramp-down | ≤ 1 s from fault to warning (preliminary) | Mode awareness (HMI) and DM integrity contribute. Covers H-07: a wrong or frozen engagement indication is a missing take-over warning |
| **SG-03** | The item shall not cause unintended vehicle acceleration | **B** ⚠ (C if AOU-05 fails) | HE-03.1–03.5 | Acceleration request ≤ 0 (no positive acceleration); ACC cancelled to the PCM | ≤ 1 s (preliminary) | |
| **SG-04** | The item shall not cause deceleration that exceeds what following traffic and the driver can control | **B** ⚠ (C if AOU-05 fails) | HE-04.1–04.5 | Deceleration limited; transition to "inactive" (no ACC command; coast) with a bounded jerk | ≤ 1 s (preliminary) | The envelope has no longitudinal jerk limit (GAP-04) |
| **SG-05** | The item shall release control immediately when the driver brakes, cancels, or overrides steering | **B** ⚠ (C if AOU-01/02/03 fail) | HE-05.1–05.4 | Disengaged: no lateral or longitudinal actuation | ≤ 0.2 s from driver input to release (preliminary) | The envelope does not monitor driver steering torque on the LKA path (GAP-02) |
| **SG-06** | The item shall not lose longitudinal deceleration capability while engaged without giving the driver an adequate take-over warning | **B** | HE-06.1, HE-06.3, HE-07.3 | Driver warned; ACC cancelled so that the driver brakes | ≤ 1 s (preliminary) | Covers the longitudinal part of H-07 |
| **SG-07** | The item shall not suppress, delay or alter the vehicle's stock pre-collision (PCS/AEB) function | **B** | HE-08.1 | Camera PCS messages forwarded unchanged; if forwarding cannot be guaranteed (e.g. harness fault), relay released to restore the stock camera link | ≤ 0.2 s for loss or delay of forwarding (preliminary, [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) §3.6); content: per frame | Verification through AOU-04 and harness fault analysis |

![Figure 6-1: hazards H-01 to H-08 with their Cartesian row statistics, connected to the representative hazardous events HE-01.1 to HE-08.1 with S, E, C and ASIL, which connect to safety goals SG-01 to SG-07 with their ASIL](hara/figures/fig-c03-6-1-hazard-sg-overview.svg)

*Figure 6-1.* From hazard to safety goal. Each hazard (§4) shows how many Cartesian rows reach ASIL A or higher and its worst case. Its representative events (§5) are connected to the goals whose "Source HEs" column above lists them. HE-02.3 goes to SG-01, the H-07 events go to SG-02 and SG-06, and HE-06.2 (QM) has no goal. Drawn from §4–§6 and `hara_model.py`. The generator fails if a goal's ASIL is not the highest ASIL of its source events, or if a rated event has no goal. Source: [`hara/figures/fig-c03-6-1-hazard-sg-overview.svg`](hara/figures/fig-c03-6-1-hazard-sg-overview.svg), generated by [`hara/hara_figures.py`](hara/hara_figures.py); change §4–§6 and regenerate.

### 6.1 Observations for the functional safety concept

1. **SG-01 sets the ASIL for the envelope.** At ASIL C (or D if the EPS assumptions fail), a single-channel STM32H7 without a working watchdog, with report-only faults and no E2E counters (GAP-01, -07, -08, -11) cannot be argued as it stands. The FSC ([WP-C-04](WP-C-04-functional-safety-concept.md)) has to choose between:
   - (a) hardening the envelope to ASIL C;
   - (b) ASIL decomposition, e.g. C(C) = B(C) on the envelope + A(C) credited to the EPS-internal limitation, which is only valid if independence and AoU evidence exist;
   - (c) reducing the actuation authority (torque limit, rate) until controllability C1 can be shown, which lowers the ASIL.

   Option (c) combined with vehicle controllability testing is the most realistic route for an aftermarket item. It also matches the ISO 11270 reasoning already present in `docs/SAFETY.md`.
2. **The ratings depend heavily on the vehicle AoUs** (AOU-01/02/03/05). Characterizing the vehicle (EPS torque authority and timeout, PCM ACC envelope, brake override) is therefore a G1 activity, not a later validation activity.
3. **Driver monitoring underpins controllability** in H-02 and H-06 (and the C2 ratings generally). The FSC must give DM integrity an ASIL attribute (inherited from SG-02/SG-06) or justify why not. Today DM runs entirely on the QM SoC, with the validity flag hard-coded `True` at the source (GAP-21).
4. **SG-07 has to hold even when LD-SDA is disengaged.** It covers the harness and relay hardware and the forwarding logic.
5. **New sources found by the Cartesian method (version 0.2).** None changes a safety goal ASIL, but each needs coverage in the FSC:
   - Driver monitoring commanding forced deceleration while the driver is attentive (HE-04.3). DM is a source of H-04 as well as a controllability measure. SG-04 therefore applies to the DM-initiated deceleration; WP-C-04 covers it with FSR-04.05 and the envelope bounds FSR-04.01/04.02, so the DM chain itself can stay QM (WP-C-04 §7).
   - The envelope stuck in a blocking state while the SoC shows "engaged" (F-08 M04, HE-02.4). SG-02 then requires that a block by the envelope is detected and announced to the driver within the SG-02 time.
   - Braking commanded while not engaged (HE-04.4). This adds to HE-01.4 (torque while not engaged): the engagement gating carries SG-01 and SG-04.
   - Mode confusion (H-07), now rated, is covered by SG-02 and SG-06. The HMI path that shows the engagement state and gives take-over alerts carries ASIL B.
   - False FCW with a close follower is ASIL A (HE-04.5), not QM as in version 0.1.
6. **AoU sensitivity.** If every ⚠ AoU fails, 26 rows reach ASIL D, all of them H-01 at E4 (OS-01, OS-03, OS-05, OS-08, OS-13), and 267 rows reach ASIL C. This confirms observation 2: AOU-01/02 (EPS torque authority) carry the SG-01 rating.

## 7. Hazard log cross-references

| Hazard | SOTIF evaluation | TARA damage scenarios | FSC |
|---|---|---|---|
| H-01 | [WP-C-05](WP-C-05-sotif-hazard-identification.md) SH-01 (model-induced lateral error) | [WP-C-09](WP-C-09-tara.md) (CAN injection, compromised SoC, malicious firmware) | FSR-01.x |
| H-02 | SH-02 (lane-detection loss, sharp curves) | DoS on SoC processes | FSR-02.x |
| H-03 | SH-03 (false lead release, e2e mode errors) | Malicious OTA / param changes | FSR-03.x |
| H-04 | SH-04 (phantom braking) | — | FSR-04.x |
| H-05 | SH-05 (override detection limits) | Mode changes over `0xdc` | FSR-05.x |
| H-06 | SH-06 (missed stationary lead) | — | FSR-06.x |
| H-07 | — (mode confusion without a malfunction is analysed in [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) MC-08, MC-09, MC-12) | Spoofed HMI state via compromised SoC | FSR-02.x, FSR-06.x |
| H-08 | SH-08 | Harness / firmware tamper; SoC transmitting `0x344`/`0x411` (GAP-42) | FSR-07.x |
| — | SOTIF-only hazards SH-09…SH-13 ([WP-C-05](WP-C-05-sotif-hazard-identification.md)); S and C ratings to be confirmed | — | — |

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Verify AOU-01/02/03/05 by vehicle characterization, then confirm or revise the ⚠ ratings | G1 |
| OI-2 | Confirm the exposure classes against real usage data (fork-owned drive logs, or published L2 usage statistics). For OS-01, -02, -03, -05, -07 and -08, the measurements of [WP-V-02 §3.4](../06-validation/WP-V-02-sotif-vv-strategy.md#34-evidence-for-pe-situation) provide the fork-owned data | G1 |
| OI-3 | Derive FTTIs from vehicle dynamics (lateral deviation vs time at envelope limits, per speed) in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | G2 |
| OI-4 | Decide the envelope strategy (harden / decompose / reduce authority) in [WP-C-04](WP-C-04-functional-safety-concept.md) | G1 |
| OI-5 | Experimental Mode is rated as a scope variant (§5.10). If D-08 chooses option B, move EX-09.1/EX-04.1 into §5 with HE IDs and add SG-09 | G1 |
| OI-6 | Independent confirmation review (I3) | G1 |
| OI-7 | SG-02 at the ODD curve bound: [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) estimates ≈ 0.7 s to 0.6 m lateral drift, shorter than driver reaction (WP-S-04 OI-2). Review the C rating of HE-02.1 for curves at the bound, or tighten R_ODD in [WP-C-02](WP-C-02-odd-and-intended-functionality.md) | G2 |
| OI-8 | I1 review of the 126-pair SC/NSC/NA classification and of the rating rules in `hara_model.py`. The skill notes the SC filter is the most consequential analyst judgement; the rules encode the same judgements as the version 0.1 rationales, but they have not been reviewed | G1 |
