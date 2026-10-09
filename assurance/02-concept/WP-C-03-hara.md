# WP-C-03 Hazard Analysis and Risk Assessment (HARA)

| Field | Value |
|---|---|
| Work product | WP-C-03 Hazard analysis and risk assessment, safety goals |
| Standard reference | ISO 26262-3:2018 §6 (and Annex B for E/C classification guidance); shared hazard log with ISO 21448 §6 |
| Version | 0.1 |
| Status | Draft — **ratings are proposals for review. They are not approved and must not be used to argue safety until the confirmation review (I3) passes** |
| ASIL / scope | Item LD-SDA, reference configuration |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review by an independent assessor (I3) per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Scope and inputs

- Item: [WP-C-01 item definition](WP-C-01-item-definition.md) (functions F-01…F-09, boundary, AOU-01…AOU-11).
- ODD: [WP-C-02](WP-C-02-odd-and-intended-functionality.md).
- The HARA rates **malfunctioning behaviour of the item** (E/E faults). Hazards caused by functional insufficiencies of the intended functionality (perception and ML performance limits) and by misuse use the same hazard list, but they are evaluated in [WP-C-05](WP-C-05-sotif-hazard-identification.md) under ISO 21448.
- As ISO 26262-3 §6 requires, the item's own safety mechanisms (the panda envelope, selfdrived checks, DM) are **not** credited in the ratings. External measures and existing vehicle elements (the EPS's own LKA torque authority, the brake system, the PCM) are credited in controllability **only where an AoU states it**. If that AoU fails verification, the alternative rating shown applies.

## 2. Method

1. **Malfunction identification:** HAZOP-style guide words (*no, more, less, wrong direction, too early, too late, inadvertent, stuck*) applied to each function F-01…F-06 and F-08 at vehicle level.
2. **Situation analysis:** the malfunctioning behaviours are combined with operational situations from the situation catalogue (§3). They are rated against ODD conditions, not just the worst conceivable situation.
3. **Classification:**
   - Severity S0–S3 (injury potential to occupants and other road users).
   - Exposure E0–E4 (by duration of the situation, as share of operating time):
     | Class | Share of operating time |
     |---|---|
     | E4 | ≥ 10% |
     | E3 | 1–10% |
     | E2 | < 1% |
     | E1 | very rare |
   - Controllability C0–C3, assessed for a typical attentive driver. For other road users, assessed for their ability to avoid harm.
4. **ASIL determination:** per the ISO 26262-3 risk graph. An equivalent rule is to sum the numeric class levels:
   | S + E + C | ASIL |
   |---|---|
   | 10 | D |
   | 9 | C |
   | 8 | B |
   | 7 | A |
   | ≤ 6 | QM |

   Any class at 0 gives QM.
5. **Safety goals:** one per hazard group, taking the highest ASIL of its hazardous events, with a safe state and a preliminary FTTI.

Rationale is given for every rating. Ratings that depend on unverified AoUs are flagged ⚠.

## 3. Operational situation catalogue

| ID | Situation | Speed | Typical exposure basis (within ODD) |
|---|---|---|---|
| OS-01 | Limited-access highway, free flow, straight or gentle curve, adjacent traffic | 90–120 km/h | E4: the majority of L2 engaged time |
| OS-02 | Highway curve (radius < 500 m) with adjacent traffic or barrier | 70–110 km/h | E3 |
| OS-03 | Undivided rural or arterial road with oncoming traffic | 60–90 km/h | E4 |
| OS-04 | Urban arterial, mixed traffic, pedestrians and cyclists near the lane edge | 30–60 km/h | E3 (urban use is a secondary ODD; see WP-C-02) |
| OS-05 | Following a lead vehicle at a short gap (dense traffic) | 30–110 km/h | E4 |
| OS-06 | Stop-and-go queue, stationary lead, pedestrians possibly crossing in front | 0–30 km/h | E3 |
| OS-07 | Approaching slower or stationary traffic from highway speed | 70–120 km/h | E3 |
| OS-08 | Close following vehicle behind (time gap < 1.5 s) | 50–120 km/h | E4 |
| OS-09 | Imminent collision situation where AEB would intervene | any | E2 |
| OS-10 | Driver emergency manoeuvre (evasive steering or emergency braking) | any | E2–E3 (driver-initiated braking is frequent; true emergencies are rare). Rated E3 for override situations generally |
| OS-11 | Low-friction road (wet), within ODD limits | any | E3 |

## 4. Hazard identification (malfunctioning behaviour → vehicle-level hazard)

| Function | Guide word | Malfunctioning behaviour | Hazard |
|---|---|---|---|
| F-01 Lateral | more / wrong direction / inadvertent | Steering torque request above the intended value, in the wrong direction, or at a high rate | **H-01** Unintended or excessive lateral motion |
| F-01 Lateral | inadvertent | Torque applied when not engaged, or after disengagement | H-01 |
| F-01 Lateral | no / less / stuck | Lateral control lost or frozen while engaged, without driver warning | **H-02** Unannounced loss or degradation of lateral control |
| F-02 Longitudinal | more / inadvertent | Acceleration above intended, or acceleration from standstill when not intended | **H-03** Unintended acceleration |
| F-02 Longitudinal | more / inadvertent | Deceleration above intended, or braking with no reason | **H-04** Unintended or excessive deceleration |
| F-02 Longitudinal | no / less | Deceleration demand lost or insufficient while engaged and following a lead, without warning | **H-06** Unannounced loss of longitudinal deceleration |
| F-03 Engagement | no / too late | Control not released on driver brake, cancel, or steering intervention | **H-05** Driver unable to override or disengage |
| F-03 / F-05 | wrong | System state shown to the driver differs from the actual state (mode confusion) | ID **H-07 is reserved** for this and not rated separately: it contributes to H-02, H-05 and H-06 and is rated there. See [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) |
| F-04 DM | no | Inattention not detected, or no warning | Not a vehicle-level hazard by itself. DM failure is a latent fault of a measure that the controllability of H-02 and H-06 relies on. Handled in the FSC (FSR on DM integrity) and in SOTIF misuse analysis |
| F-05 HMI | no | Disengagement or take-over warning not given | Rated as part of H-02, H-06 |
| F-06 FCW | no / inadvertent | FCW missing or false | Missing FCW: QM (the driver is responsible; stock PCS gives FCW). False FCW: startle effect, QM (rationale in §5.8) |
| F-08 Envelope / harness | inadvertent | Stock PCS/AEB messages suppressed or overwritten by the item | **H-08** Suppression of the vehicle's stock pre-collision braking |
| F-09 Non-driving | — | Malfunctions of logging, upload or update do not act on vehicle motion directly. Cyber-induced effects are handled in the TARA ([WP-C-09](WP-C-09-tara.md)) and map to H-01…H-08 | — |

## 5. Hazardous events and risk assessment

### 5.1 H-01 Unintended or excessive lateral motion

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-01.1 | OS-03 undivided road, oncoming traffic, 60–90 km/h | Departure into the oncoming lane; head-on collision | S3 | E4 | C2 ⚠ | **C** | S3: head-on at combined speeds > 100 km/h, life-threatening. E4: undivided roads make up a large share of driving. C2 ⚠: credits AOU-01/AOU-02 (EPS limits LKA torque to an overpowerable level). A supervising driver with hands near the wheel corrects a sustained limited-torque deviation within ~1 s in most cases (≥ 90%). **If AOU-01/02 are not verified: C3 → ASIL D** |
| HE-01.2 | OS-01/OS-02 highway, adjacent traffic or barrier, 90–120 km/h | Lateral departure into an adjacent vehicle or barrier | S3 | E4 | C2 ⚠ | **C** | As HE-01.1. Lateral deviation at speed with adjacent traffic can trigger loss of control or secondary collisions |
| HE-01.3 | OS-04 urban, pedestrians and cyclists near the lane edge, 30–60 km/h | Vehicle drifts into a vulnerable road user | S3 | E3 | C2 ⚠ | **B** | S3: VRU impact above 30 km/h. E3: urban VRU proximity within the ODD. C2: lower speed gives more time but less lateral margin |
| HE-01.4 | Torque while not engaged, OS-01/OS-03, driver steering manually | Unexpected steering disturbance during manual driving | S3 | E4 | C2 ⚠ | **C** | Driver hands on the wheel (manual driving), so C2 rather than C3. Same S/E as HE-01.1 |

### 5.2 H-02 Unannounced loss or degradation of lateral control

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-02.1 | OS-02 highway curve, driver supervising, possibly hands off (foreseeable: openpilot does not require hands on the wheel) | Vehicle goes straight in the curve and departs the lane | S3 | E3 | C2 | **B** | S3: departure at highway speed into a barrier or adjacent traffic. E3: curves of this radius at speed. C2: a supervising driver notices the drift and corrects it. Loss without warning delays the reaction; hands-off use is foreseeable |
| HE-02.2 | OS-03 rural curve with oncoming traffic | Departure into the oncoming lane | S3 | E3 | C2 | **B** | As HE-02.1 |
| HE-02.3 | Frozen (stuck) torque command at its last value | Steering bias continues while the road changes | S3 | E3 | C2 ⚠ | **B** | A stuck request is bounded by EPS authority (AOU-01). It behaves like HE-01 at reduced magnitude |

### 5.3 H-03 Unintended acceleration

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-03.1 | OS-05 following a lead at a short gap | Rear-end collision with the lead vehicle | S2 | E4 | C2 ⚠ | **B** | S2: moderate speed difference in following. C2 credits AOU-03 (driver braking overrides) and AOU-05 (PCM bounds the ACC acceleration request). Without AOU-05, high-magnitude acceleration is possible → C3 → ASIL C |
| HE-03.2 | OS-06 standstill in a queue, pedestrian crossing in front | Vehicle moves off and hits a pedestrian | S3 | E3 | C2 | **B** | S3: VRU. E3: stop-and-go with crossing pedestrians. C2: the driver must brake immediately; a low-speed launch is limited |
| HE-03.3 | OS-07 approaching a slower lead | Acceleration toward the lead instead of deceleration | S3 | E3 | C2 | **B** | High closing speed. The driver supervises and can brake |

### 5.4 H-04 Unintended or excessive deceleration

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-04.1 | OS-08 close following vehicle, 50–120 km/h | Rear-end impact by the following vehicle | S2 | E4 | C2 ⚠ | **B** | S2: rear impacts on a modern car are mostly S1–S2. Severe at large speed differences, but deceleration is limited by the PCM's ACC envelope (AOU-05). C2: the following driver and the ego driver (pressing gas overrides) can usually react. If the deceleration is unbounded (AOU-05 fails) → C3 → ASIL C |
| HE-04.2 | OS-11 wet road, curve | Instability under unexpected braking | S3 | E3 | C1 | **A** | VSC available (AOU-10). Moderate ACC deceleration on wet roads is controllable for most drivers |

### 5.5 H-05 Driver unable to override or disengage

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-05.1 | OS-10 driver emergency braking while the system keeps commanding acceleration | Longer stopping distance; collision | S3 | E3 | C2 ⚠ | **B** | Credits AOU-03 (the brake system works mechanically and the PCM cancels ACC on brake). Without AOU-03 → C3 → ASIL C |
| HE-05.2 | OS-10 driver evasive steering while the system keeps commanding counter-torque | Evasive manoeuvre impaired; collision | S3 | E3 | C2 ⚠ | **B** | Credits AOU-01/AOU-02 (driver can overpower the EPS LKA torque). Without them → C3 → ASIL C |
| HE-05.3 | Cancel or brake does not disengage; the system stays engaged when the driver believes it is off | Mode confusion, then unexpected actuation (leads to H-01 or H-03) | S3 | E3 | C2 | **B** | Rated with the effect hazards |

### 5.6 H-06 Unannounced loss of longitudinal deceleration

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-06.1 | OS-07 approaching stationary or slow traffic at highway speed; the system silently stops decelerating (for example, a stale plan holds zero acceleration) | High-speed rear-end collision | S3 | E3 | C2 | **B** | S3: high closing speed. E3. C2: supervising driver, but reliance on ACC delays the reaction. The stock PCS may mitigate this but is not credited (it is a separate system, and AOU-04 is unverified) |
| HE-06.2 | OS-06 slow queue | Low-speed rear-end collision | S1 | E3 | C2 | **QM** | S1: low-speed impact, light injuries |

### 5.7 H-08 Suppression of the vehicle's stock pre-collision braking

| HE | Situation | Effect | S | E | C | ASIL | Rationale |
|---|---|---|---|---|---|---|---|
| HE-08.1 | OS-09 imminent collision where the stock PCS would have braked (engaged or not engaged) | Collision not mitigated | S3 | E2 | C3 | **B** | S3: PCS-relevant impacts. E2: PCS-relevant situations are rare. C3: by definition the driver did not avoid the situation. The item must not degrade a stock safety function, whether or not LD-SDA is engaged |

### 5.8 Malfunctions rated QM

| Malfunction | Rating | Rationale |
|---|---|---|
| Missing FCW (F-06) | QM | The warning supplements driver supervision. The stock PCS gives its own warning (subject to H-08) |
| False FCW (F-06) | QM | Startle without actuation. Rated S1 E3 C1. Recurrent false alerts are a SOTIF and HMI concern ([WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md)) |
| Missing LDW (F-07) | QM | Manual driving with the driver in full control |
| Loss of logging or upload | QM | No effect on vehicle motion. Relevant to field monitoring and cybersecurity only |

## 6. Safety goals

| ID | Safety goal | ASIL | Source HEs | Safe state | Preliminary FTTI | Notes |
|---|---|---|---|---|---|---|
| **SG-01** | The item shall not cause lateral motion of the vehicle that exceeds what the driver can control, including any steering actuation while the item is not engaged | **C** ⚠ (D if AOU-01/02 fail) | HE-01.1–01.4, HE-02.3 | LKA torque request zero, steer request bit cleared; driver informed | **≤ 0.5 s** (preliminary: `docs/SAFETY.md` cites 0.9 s to reach 1 m lateral deviation at maximum actuation; FTTI to be derived in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md)) | The current envelope detection times (RX ≤ 2 s, heartbeat 3–5 s) are not consistent with this FTTI (GAP-06). The envelope's continuous limiting (magnitude, rate, measured tracking) does act within one frame |
| **SG-02** | The item shall not lose or degrade lateral control while engaged without giving the driver an adequate take-over warning | **B** | HE-02.1, HE-02.2 | Driver warned (visual + acoustic) and lateral control handed back with a smooth torque ramp-down | ≤ 1 s from fault to warning (preliminary) | Mode awareness (HMI) and DM integrity contribute |
| **SG-03** | The item shall not cause unintended vehicle acceleration | **B** ⚠ (C if AOU-05 fails) | HE-03.1–03.3 | Acceleration request ≤ 0 (no positive acceleration); ACC cancelled to the PCM | ≤ 1 s (preliminary) | |
| **SG-04** | The item shall not cause deceleration that exceeds what following traffic and the driver can control | **B** ⚠ (C if AOU-05 fails) | HE-04.1, HE-04.2 | Deceleration limited; transition to "inactive" (no ACC command; coast) with a bounded jerk | ≤ 1 s (preliminary) | The envelope has no longitudinal jerk limit (GAP-04) |
| **SG-05** | The item shall release control immediately when the driver brakes, cancels, or overrides steering | **B** ⚠ (C if AOU-01/02/03 fail) | HE-05.1–05.3 | Disengaged: no lateral or longitudinal actuation | ≤ 0.2 s from driver input to release (preliminary) | The envelope does not monitor driver steering torque on the LKA path (GAP-02) |
| **SG-06** | The item shall not lose longitudinal deceleration capability while engaged without giving the driver an adequate take-over warning | **B** | HE-06.1 | Driver warned; ACC cancelled so that the driver brakes | ≤ 1 s (preliminary) | |
| **SG-07** | The item shall not suppress, delay or alter the vehicle's stock pre-collision (PCS/AEB) function | **B** | HE-08.1 | Camera PCS messages forwarded unchanged; if forwarding cannot be guaranteed (e.g. harness fault), relay released to restore the stock camera link | Continuous | Verification through AOU-04 and harness fault analysis |

### 6.1 Observations for the functional safety concept

1. **SG-01 sets the ASIL for the envelope.** At ASIL C (or D if the EPS assumptions fail), a single-channel STM32H7 without a working watchdog, with report-only faults and no E2E counters (GAP-01, -07, -08, -11) cannot be argued as it stands. The FSC ([WP-C-04](WP-C-04-functional-safety-concept.md)) has to choose between:
   - (a) hardening the envelope to ASIL C;
   - (b) ASIL decomposition, e.g. C(C) = B(C) on the envelope + A(C) credited to the EPS-internal limitation, which is only valid if independence and AoU evidence exist;
   - (c) reducing the actuation authority (torque limit, rate) until controllability C1 can be shown, which lowers the ASIL.

   Option (c) combined with vehicle controllability testing is the most realistic route for an aftermarket item. It also matches the ISO 11270 reasoning already present in `docs/SAFETY.md`.
2. **The ratings depend heavily on the vehicle AoUs** (AOU-01/02/03/05). Characterizing the vehicle (EPS torque authority and timeout, PCM ACC envelope, brake override) is therefore a G1 activity, not a later validation activity.
3. **Driver monitoring underpins controllability** in H-02 and H-06 (and the C2 ratings generally). The FSC must give DM integrity an ASIL attribute (inherited from SG-02/SG-06) or justify why not. Today DM runs entirely on the QM SoC, with the validity flag hard-coded `True` at the source (GAP-21).
4. **SG-07 has to hold even when LD-SDA is disengaged.** It covers the harness and relay hardware and the forwarding logic.

## 7. Hazard log cross-references

| Hazard | SOTIF evaluation | TARA damage scenarios | FSC |
|---|---|---|---|
| H-01 | [WP-C-05](WP-C-05-sotif-hazard-identification.md) SH-01 (model-induced lateral error) | [WP-C-09](WP-C-09-tara.md) (CAN injection, compromised SoC, malicious firmware) | FSR-01.x |
| H-02 | SH-02 (lane-detection loss, sharp curves) | DoS on SoC processes | FSR-02.x |
| H-03 | SH-03 (false lead release, e2e mode errors) | Malicious OTA / param changes | FSR-03.x |
| H-04 | SH-04 (phantom braking) | — | FSR-04.x |
| H-05 | SH-05 (override detection limits) | Mode changes over `0xdc` | FSR-05.x |
| H-06 | SH-06 (missed stationary lead) | — | FSR-06.x |
| H-08 | SH-08 | Harness / firmware tamper; SoC transmitting `0x344`/`0x411` (GAP-42) | FSR-07.x |
| — | SOTIF-only hazards SH-09…SH-13 ([WP-C-05](WP-C-05-sotif-hazard-identification.md)); S and C ratings to be confirmed | — | — |

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Verify AOU-01/02/03/05 by vehicle characterization, then confirm or revise the ⚠ ratings | G1 |
| OI-2 | Confirm the exposure classes against real usage data (fork-owned drive logs, or published L2 usage statistics) | G1 |
| OI-3 | Derive FTTIs from vehicle dynamics (lateral deviation vs time at envelope limits, per speed) in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | G2 |
| OI-4 | Decide the envelope strategy (harden / decompose / reduce authority) in [WP-C-04](WP-C-04-functional-safety-concept.md) | G1 |
| OI-5 | Rate Experimental Mode specific hazardous events (red-light and stop-sign stopping, false stops) once the ODD decision (WP-C-01 OI-8) is made | G1 |
| OI-6 | Independent confirmation review (I3) | G1 |
