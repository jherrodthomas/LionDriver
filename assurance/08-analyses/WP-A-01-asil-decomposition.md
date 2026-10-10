# WP-A-01 ASIL Decomposition Rationale

| Field | Value |
|---|---|
| Work product | WP-A-01 ASIL decomposition rationale |
| Standard reference | ISO 26262-9:2018 §5 (requirements decomposition with respect to ASIL tailoring); ISO 26262-9 §7 (DFA, as the independence evidence §5 relies on); ISO 26262-3 §7 (FSC, where decomposition would be applied) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SG-01 (ASIL D); SG-03…SG-05 (ASIL C); SG-02, SG-06, SG-07 (ASIL B) checked for decomposition need (HARA 0.2, decision D-09) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review of any applied decomposition by an independent assessor (I3) per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document records whether LionDriver uses ASIL decomposition (ISO 26262-9 §5), and if so, on which requirements, with which redundant elements, and with which independence evidence. It is the analysis the [functional safety concept (WP-C-04)](../02-concept/WP-C-04-functional-safety-concept.md) §4.3 points to.

Inputs:

- [WP-C-03 HARA](../02-concept/WP-C-03-hara.md): SG-01…SG-07, ASILs, safe states, preliminary FTTIs, §6.1 options (a)/(b)/(c).
- [WP-C-04 FSC](../02-concept/WP-C-04-functional-safety-concept.md): §4 envelope strategy (recommended option (c): reduced authority + envelope hardened to ASIL B); §4.3 fallback decomposition; FSR-01.01…FSR-07.05.
- [WP-A-03 DFA](WP-A-03-dependent-failure-analysis.md): dependent failure initiators and coupling factors between the envelope, the SoC, the EPS and the driver.
- [WP-A-02 coexistence / FFI](WP-A-02-coexistence-freedom-from-interference.md): interference from QM elements into the envelope.
- [WP-S-02 TSRs](../03-system/WP-S-02-technical-safety-requirements.md) (Draft v0.1): ASIL notation **B‡** = target B under option (c), D until SG-01 is re-rated, decomposition fallback otherwise (WP-S-02 §2.1). This document is consistent with that notation.

## 2. Summary decision

| Question | Answer |
|---|---|
| Is ASIL decomposition used in the current (primary) safety concept? | **No.** The primary strategy (WP-C-04 §4.2, option (c)) reduces lateral actuation authority until controllability C1 is shown, which lowers SG-01 to ASIL B, and hardens the envelope (E-03) to ASIL B as a single, non-decomposed element |
| Which ASIL do the envelope requirements carry today? | SG-01-derived FSRs carry **ASIL D** until the HARA is re-rated on controllability evidence (WP-C-04 §4.2 conditions). SG-03…SG-05-derived FSRs carry ASIL C. All other envelope FSRs carry ASIL B |
| Is any requirement allocated to the QM SoC credited as a decomposition partner? | **No.** SoC (E-01) measures are QM and are never credited as the "redundant" half of a decomposition. They are first-line, better-explained reactions only (WP-C-04 §5.2 note) |
| Is the Toyota EPS credited as a decomposition partner? | **No, and not recommended** (§5) |
| When would decomposition become necessary? | Only if vehicle controllability tests (WP-C-04 OI-2, [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) §8) show that C1 cannot be reached at a torque level that keeps the function useful, **and** the envelope cannot be argued at ASIL D (option (a)). For SG-03…SG-05 (ASIL C), if the envelope cannot be argued at ASIL C |
| Status of the fallback | Documented option set (§4) with independence requirements (§4.3). No hardware for it exists. Activation needs a maintainer decision and a WP-C-04 update |

## 3. Decomposition need per safety goal

ISO 26262-9 §5 allows decomposition only between sufficiently independent elements that each implement the safety requirement. The table checks whether any SG needs it.

| SG | ASIL | Primary implementation | Can a single element carry the ASIL? | Decomposition needed? |
|---|---|---|---|---|
| SG-01 | D | E-03 envelope: torque magnitude, rate, measured tracking, engagement gating (FSR-01.01…01.12) | Not today (GAP-01, -06, -07, -08, -11). After hardening, ASIL B is plausible; ASIL D on a COTS single-channel MCU with shared PCB/power is not credible without an external supervisor or second channel (WP-M-01 §9, WP-H-04 §5.1) | **Not if** C1 is shown (SG-01 → B). **Yes (fallback)** if C1 fails and option (a) is not reachable |
| SG-02 | B | E-03 backstop (FSR-01.07 stale-command removal, FSR-02.05 SoC-independent buzzer) + QM SoC warning | Yes, after hardening | No |
| SG-03 | C | E-03 accel bound, inactive value, gas block (FSR-03.01…03.05) | Uncertain: ASIL C hardware metrics on the single-channel MCU are unlikely without DC-02 (WP-H-04 §5.1); jerk limit needed (GAP-04) | Possibly. If the envelope cannot be argued at ASIL C, C(C) = B(C) + A(C) with the same second element as SG-01 (see OI-3) |
| SG-04 | C | E-03 decel bound and onset-rate limit (FSR-04.01…04.04) | As SG-03 | As SG-03 |
| SG-05 | C | E-03 brake/cancel revocation, driver-torque override (FSR-05.01…05.06) | As SG-03, and only after GAP-02 is closed | As SG-03 |
| SG-06 | B | E-03 backstop + QM detection | Yes | No |
| SG-07 | B | E-03 static forwarding + E-05 relay de-energise-to-stock (FSR-07.01…07.03) | Yes, if relay de-energised state is confirmed (AOU-13) | No |

Observation: since D-09 the HARA takes no credit for the vehicle AoUs, so SG-03/04/05 are ASIL C now, not only if an AoU fails. The fallback in §4 is therefore written so that the same independent second element can carry the A(C) half for the longitudinal and override goals, not only the SG-01 half.

## 4. Fallback decomposition options (WP-C-04 §4.3)

### 4.1 Candidate schemes

| ID | Scheme | Element 1 (higher half) | Element 2 (lower half) | Requirement decomposed | Assessment |
|---|---|---|---|---|---|
| DEC-01 | D(D) = B(D) + B(D) (alternative C(D) + A(D)); C(C) = B(C) + A(C) for SG-03…SG-05 | E-03 envelope on the panda STM32H7 (TSR-101…TSR-110, TSR-301…TSR-311, TSR-401…TSR-413, TSR-501…TSR-516) | **New element E-07 "independent actuation monitor" (IAM)**: a second MCU on the harness side that observes bus 0 TX/RX and can de-energise the intercept relay (stock path) | FSR-01.01 (magnitude), FSR-01.03 (measured tracking), FSR-01.04 (no torque when not engaged), FSR-01.05 (engagement only with PCM cruise active) | **Preferred fallback.** Both elements inside LionDriver's control; independence can be designed in; safe state of E-07 (relay open) is de-energise-to-safe |
| DEC-02 | D(D) = B(D) + B(D) | E-03 envelope | Second software channel on the **same** STM32H7 (diverse re-implementation of the limit checks) | Same as DEC-01 | **Rejected.** Shares clock, power, memory, CAN peripheral, compiler and the SoC-controlled reset/boot pins (GAP-38). The DFA cannot show sufficient independence on one die without MPU partitioning or lockstep (GAP-11). Kept only as a diagnostic-coverage measure inside E-03, not as decomposition |
| DEC-03 | D(D) = C(D) + A(D) | E-03 envelope | Toyota EPS internal LKA torque limitation and timeout (EXT-EPS, AOU-01R) | FSR-01.01, FSR-01.13 | **Not recommended** (§5). Possible only once AOU-01/02 are verified |
| DEC-04 | D(D) = A(D) + C(D) | QM-to-ASIL-A upgraded SoC monitor (e.g. controlsd plausibility) | E-03 envelope at C | — | **Rejected.** The SoC is Linux/Python with no partitioning or WCET (GAP-23), configures the envelope (GAP-09) and controls its boot pins (GAP-38). It cannot be shown independent of the failure it would monitor (it produces the command) |

### 4.2 DEC-01 element E-07 functional outline (only if activated)

E-07 is a concept, not a design. It is recorded so that the independence requirements in §4.3 have a concrete target.

| Function | Outline |
|---|---|
| Inputs | Bus 0 (car side) RX only, via its own transceiver: `0x2E4` STEERING_LKA (commanded torque, steer request), `0x260` STEER_TORQUE_SENSOR (EPS motor and driver torque), `0x1D2` PCM_CRUISE (cruise active), `0x226` BRAKE_MODULE, `0xAA` wheel speeds, `0x343` ACC_CONTROL |
| Checks (B(D) subset for SG-01; A(C) for SG-03/04) | (1) `0x2E4` torque magnitude ≤ speed-dependent bound; (2) `0x2E4` non-zero or steer request set only while PCM cruise active; (3) commanded torque within bound of measured EPS torque; (4) `0x343` accel ≤ bound and = inactive value while cruise inactive (if extended to SG-03/04) |
| Reaction | De-energise the harness intercept relay coil (series switch in the relay drive), so the stock camera reconnects to the vehicle and the LKA/ACC commands from E-03 no longer reach the vehicle side |
| Safe state | Relay de-energised = stock path (requires AOU-13 confirmed) |
| Latency budget | Detection + relay drop-out within the SG-01 FTTI allocation (WP-C-04 §8: ≤ 0.5 s total; WP-S-04 to confirm). Relay drop-out time to be measured |
| Configuration | Limits fixed in E-07 firmware for the reference configuration. No configuration path from the SoC or from E-03 |

### 4.3 Independence requirements for DEC-01

These requirements must be met, and shown by the DFA ([WP-A-03](WP-A-03-dependent-failure-analysis.md)), before DEC-01 can be credited. ID prefix `IR-`.

| ID | Requirement | Dependent failure it addresses | Verification |
|---|---|---|---|
| IR-01 | E-07 shall be supplied from a power path that a single fault in the comma device supply (12 V input stage, regulators) cannot take down together with a loss of E-03 function, or E-07 shall de-energise the relay on loss of its own supply | Shared power (WP-A-03 DFI-01) | Schematic review, HIL power-dip test |
| IR-02 | E-07 shall use its own clock source, not derived from the STM32H7 or SoC clocks | Shared clock (DFI-02) | Schematic review |
| IR-03 | E-07 shall receive bus 0 through its own CAN transceiver and controller, not through panda forwarding or panda-provided data | Shared communication path | Design review, HIL bus-fault test |
| IR-04 | E-07 shall share no source code, compiled libraries, limit tables or code generators with opendbc safety or panda firmware; the limit values shall be derived and reviewed separately | Common software, upstream source and toolchain (DFI-16, DFI-17), identical constants (DFI-08) | Code and build review |
| IR-05 | E-07 shall be compiled with a different toolchain, or with the same toolchain plus a qualified independence argument (ISO 26262-8 §11) | Common compiler fault | Tool classification ([WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md)) |
| IR-06 | Neither the SoC nor E-03 shall be able to configure, reset, reflash or put E-07 into a boot mode; E-07 shall have no command interface in release builds | Configuration of one element by the other (GAP-09, GAP-38 pattern) | Design review, penetration test ([WP-V-06](../06-validation/WP-V-06-cybersecurity-validation.md)) |
| IR-07 | E-07 shall act through a de-energise-to-safe path (series switch on the relay coil). E-03 or the SoC shall not be able to override it | Common actuation path | Schematic review, HIL test |
| IR-08 | E-07 shall be physically separated from the comma device PCB (separate housing or separate board in the harness box) | Shared PCB, thermal, mechanical (DFI-03, DFI-04) | Design review, environmental test |
| IR-09 | The harness connector and relay itself remain a shared element. Its failure modes (welded contact, coil open) shall be covered by a relay-state readback seen by both E-03 and E-07, and by a latent-fault test at start-up | Shared relay / connector (DFI-05) | FMEDA ([WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md)), HIL test |
| IR-10 | E-07 limits shall be set from the controllability evidence (WP-C-04 OI-2), independently of the E-01 controller limits and the E-03 limits | Identical constants as common cause (DFI-08) | Review of limit derivation records |

### 4.4 Consequences for the elements if DEC-01 is applied

- E-03 keeps the ASIL B(D) requirements (B(C) for SG-03…SG-05). Its development stays at ASIL B process rigour, but the hardware metrics for the SG-01 path are evaluated at the level of the original ASIL D goal (ASIL C for SG-03…SG-05) as required by ISO 26262-9 §5 (the decomposition does not reduce hardware metric targets for random failures of the item as a whole). This must be checked against the licensed text during review (OI-4).
- E-07 carries B(D) requirements for SG-01 (A(D) under the C(D) + A(D) alternative) and A(C) requirements for SG-03…SG-05, developed at the matching process rigour.
- Integration, verification of the safety goal, confirmation measures and the DFA stay at the original ASIL (D for SG-01, C for SG-03…SG-05).
- New TSRs would be needed in WP-S-02 for E-07 (no ID range is reserved yet; proposed: a TSR-52x sub-block, to be agreed with the WP-S-02 author) and a new element E-07 in [WP-C-01](../02-concept/WP-C-01-item-definition.md) and [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md).

## 5. Why crediting the Toyota EPS (DEC-03) is not recommended

| # | Reason | Basis |
|---|---|---|
| 1 | **No development evidence.** ISO 26262-9 §5 needs each decomposed requirement implemented by an element developed to its decomposed ASIL. Toyota provides no evidence that the EPS LKA limitation is ASIL A or better | WP-C-04 §4.1; T-08 (no DIA possible) in [WP-M-01](../01-management/WP-M-01-assurance-strategy.md) |
| 2 | **No independence of input.** The EPS acts on the same `0x2E4` command that the envelope passes. A wrong but in-envelope command is executed by both. The EPS limit only bounds magnitude; it does not check engagement state or driver intent the way FSR-01.04/01.05 do | WP-A-03 coupling factor "shared command" |
| 3 | **Unknown behaviour.** The torque limit, rate limit and timeout (`carstate.py:15-16` comment, ≈1.5–2 s) are reverse-engineered, not specified. Values may differ per EPS firmware (21 fingerprinted EPS versions, `opendbc_repo/opendbc/car/toyota/fingerprints.py`) | AOU-01R, GAP-05 |
| 4 | **Change outside LionDriver control.** A Toyota EPS reflash (dealer campaign) can change the behaviour without notice; no change notification exists | WP-M-11 (supplier management) |
| 5 | **Assessor acceptance risk.** A decomposition that rests on an unverified, unowned element is unlikely to pass I3 confirmation review | WP-C-04 §4.2 rationale 3 |

The EPS limitation is still **used** as an external measure (FSR-01.13, TSR-111, AOU-01R) as design input and defence in depth. Since D-09 it is not credited in the HARA controllability rating. It is characterised by vehicle test ([WP-S-09](../03-system/WP-S-09-system-verification.md) VS-SQ-01, VS-SQ-02). Using it as a measured external measure that could support a future controllability re-rating is different from crediting it with a decomposed ASIL.

## 6. Decomposition record template

One record per applied decomposition. Records live in this document, §7, and are referenced from WP-C-04 and WP-S-02.

| Field | Content |
|---|---|
| Record ID | DEC-nn |
| Status | Proposed / Applied / Withdrawn |
| Safety goal and ASIL | SG-xx, ASIL x |
| Original requirement(s) | FSR/TSR IDs with ASIL before decomposition |
| Decomposition scheme | e.g. D(D) = B(D) + B(D), C(C) = B(C) + A(C) |
| Element 1 | Element ID, decomposed requirement IDs, ASIL x(Y) |
| Element 2 | Element ID, decomposed requirement IDs, ASIL x(Y) |
| Redundancy argument | Why each element on its own satisfies the original safety requirement (not just part of it) |
| Independence requirements | IR-nn list |
| DFA reference | WP-A-03 DFI- and IC- IDs and verdict |
| FFI reference | WP-A-02 interference IDs |
| Safe state of each element and how they combine | |
| Integration / verification at original ASIL | WP-S-08 / WP-S-09 spec IDs |
| HW metric evaluation | WP-H-04 / WP-H-05 reference (evaluated at original ASIL) |
| Confirmation review | Record reference (I3) |
| Approver and date | |

## 7. Decomposition records

| Record | SG | Scheme | Status | Note |
|---|---|---|---|---|
| DEC-01 | SG-01 (and SG-03/04/05 if needed) | D(D) = B(D) envelope + B(D) independent actuation monitor E-07 (or C(D) + A(D)); C(C) = B(C) + A(C) for SG-03/04/05 | **Proposed (fallback, not applied)** | Activate only per §2 trigger. Needs new element, new TSRs, DFA closure |
| DEC-02 | SG-01 | Two channels on one MCU | Withdrawn (rejected, §4.1) | Recorded for traceability of the decision |
| DEC-03 | SG-01 | Envelope + Toyota EPS | Withdrawn (not recommended, §5) | EPS stays an external measure only |
| DEC-04 | SG-01 | SoC monitor + envelope | Withdrawn (rejected, §4.1) | |

## 8. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Maintainer decision on the envelope strategy (WP-C-04 OI-1). If option (c) is confirmed, this document stays "no decomposition applied" | Maintainer | G1 |
| OI-2 | After controllability tests (WP-C-04 OI-2), decide whether DEC-01 is activated; if yes, add E-07 to WP-C-01, WP-S-03, and request new TSRs in WP-S-02 | Safety engineer | G2 |
| OI-3 | SG-03/04/05 are ASIL C since D-09. If the envelope cannot be argued at ASIL C for them, extend DEC-01 scope to the longitudinal and override requirements or re-plan | Safety engineer | G2 |
| OI-4 | Check §4.4 statement on hardware metrics after decomposition against the licensed ISO 26262-9 §5 text | Safety engineer | G2 |
| OI-5 | Confirm AOU-13 (relay de-energised state = stock path); DEC-01 and SG-07 both depend on it | HW lead | G2 |
