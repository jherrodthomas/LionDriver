# WP-A-01 ASIL Decomposition Rationale

| Field | Value |
|---|---|
| Work product | WP-A-01 ASIL decomposition rationale |
| Standard reference | ISO 26262-9:2018 §5 (requirements decomposition with respect to ASIL tailoring); ISO 26262-9 §7 (DFA, as the independence evidence §5 relies on); ISO 26262-3 §7 (FSC, where decomposition would be applied) |
| Version | 0.7 (§2 and Figure 2-1 brought in line with DQ-341 A: envelope hardened to ASIL C as one element, DEC-01 only if the ASIL C hardware metrics fail, controllability tests no longer decide the envelope target; OI-2 note; 2026-10-19). 0.6 (DQ-341 applied: the envelope is hardened to ASIL C; DEC-01 extended to SG-02, SG-03 and SG-06 only if the ASIL C hardware metrics fail; §3, OI-3; 2026-10-16). 0.5 (HARA v0.4: SG-02, SG-03 and SG-06 ASIL C, SG-08 ASIL A; §3 updated. The envelope now needs ASIL C for those goals whatever SG-01 becomes, so the §3 judgment that ASIL C on the single-channel MCU is unlikely applies to them too; whether to harden to C or plan DEC-01 for them is queued for the lead as DQ-341; 2026-10-16). 0.4 (lead decisions of 2026-10-14 recorded, register DQ-007, DQ-050, DQ-063: option (c) chosen, so no decomposition is applied; the DEC-01 fallback is decided after the controllability tests; OI-1 closed; no change to the rationale; 2026-10-16). 0.3 (Figure 2-1 decision and candidate schemes, Figure 4-1 DEC-01 independence requirements added; no change to the rationale; 2026-10-13). 0.2 (status update 2026-10-12: GAP-06/-07 partly closed, envelope configuration locked in the reference build; no change to the decomposition rationale). History: 0.1 |
| Status | Draft |
| ASIL / scope | SG-01 (ASIL C ⚠, D if AOU-01/02 fail); SG-02, SG-03, SG-06 (ASIL C); SG-04, SG-05, SG-07 (ASIL B); SG-08 (ASIL A) checked for decomposition need (WP-C-03 v0.4) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); confirmation review of any applied decomposition by an independent assessor (I3) per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `bf6ce8c` (status update 2026-10-12; opendbc `7993399`, panda `b790fca`). Analysis originally at `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document records whether LionDriver uses ASIL decomposition (ISO 26262-9 §5), and if so, on which requirements, with which redundant elements, and with which independence evidence. It is the analysis the [functional safety concept (WP-C-04)](../02-concept/WP-C-04-functional-safety-concept.md) §4.3 points to.

Inputs:

- [WP-C-03 HARA](../02-concept/WP-C-03-hara.md): SG-01…SG-08 (v0.4), ASILs, safe states, preliminary FTTIs, §6.1 options (a)/(b)/(c).
- [WP-C-04 FSC](../02-concept/WP-C-04-functional-safety-concept.md): §4 envelope strategy (option (c): reduced authority, DQ-007; envelope hardened to ASIL C since DQ-341 A); §4.3 fallback decomposition; FSR-01.01…FSR-07.05.
- [WP-A-03 DFA](WP-A-03-dependent-failure-analysis.md): dependent failure initiators and coupling factors between the envelope, the SoC, the EPS and the driver.
- [WP-A-02 coexistence / FFI](WP-A-02-coexistence-freedom-from-interference.md): interference from QM elements into the envelope.
- [WP-S-02 TSRs](../03-system/WP-S-02-technical-safety-requirements.md) (Draft v0.1): ASIL notation **B‡** = target B under option (c), C until SG-01 is re-rated (WP-S-02 §2.1); **C** = from SG-02, SG-03 or SG-06, final for the envelope (DQ-341 A). This document is consistent with that notation.

## 2. Summary decision

| Question | Answer |
|---|---|
| Is ASIL decomposition used in the current (primary) safety concept? | **No.** The envelope (E-03) is hardened to **ASIL C** as a single, non-decomposed element (DQ-341 A, 2026-10-16), because SG-02, SG-03 and SG-06 are ASIL C outright (HARA v0.4). Option (c) (WP-C-04 §4.2, DQ-007) still reduces lateral actuation authority until controllability C1 is shown, which lowers the SG-01 requirements to ASIL B, but no longer lowers the envelope's target |
| Which ASIL do the envelope requirements carry today? | Each FSR carries the ASIL of its goal: **ASIL C** for SG-02, SG-03 and SG-06, and for SG-01 until the HARA is re-rated on controllability evidence (WP-C-04 §4.2 conditions); ASIL B for SG-04, SG-05 and SG-07. The envelope element is ASIL C either way |
| Is any requirement allocated to the QM SoC credited as a decomposition partner? | **No.** SoC (E-01) measures are QM and are never credited as the "redundant" half of a decomposition. They are first-line, better-explained reactions only (WP-C-04 §5.2 note) |
| Is the Toyota EPS credited as a decomposition partner? | **No, and not recommended** (§5) |
| When would decomposition become necessary? | Only if the envelope cannot meet the ASIL C hardware metrics on its COTS single-channel MCU ([WP-H-04](../04-hardware/WP-H-04-hardware-metrics.md); DQ-341 A). Then DEC-01 covers SG-01 and is extended to the SG-02, SG-03 and SG-06 paths (OI-3). A failed controllability test (WP-C-04 OI-2, [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) §8) keeps SG-01 at ASIL C, which the envelope already carries |
| Status of the fallback | Documented option set (§4) with independence requirements (§4.3). No hardware for it exists. Activation needs a maintainer decision and a WP-C-04 update. The project lead decided on 2026-10-14 to make that decision after the controllability tests, with no work started before (register DQ-050) |
| Strategy decision | Option (c) chosen by the project lead on 2026-10-14 (register DQ-007). Until SG-01 is re-rated, hardware is designed to the ASIL C targets with the ASIL B figures shown alongside (DQ-063) |

![Figure 2-1: decomposition decision: the envelope is hardened to ASIL C (DQ-341 A); if the ASIL C hardware metrics are met there is no decomposition, otherwise the fallback DEC-01; the controllability tests of option (c) still run for SG-01; the candidate schemes DEC-01 to DEC-04 with their record status](figures/fig-a01-2-1-decomposition-decision.svg)

*Figure 2-1.* The decision of this table and §3 as a flow (redrawn in v0.7 for DQ-341 A), next to the four candidate schemes of §4.1 with their §7 record status: DEC-01 proposed, not applied; DEC-02 and DEC-04 rejected; DEC-03 not recommended. Drawn from §2, §3, §4.1 and §7. Source: [`figures/fig-a01-2-1-decomposition-decision.svg`](figures/fig-a01-2-1-decomposition-decision.svg); change it together with §2, §4.1 and §7.

## 3. Decomposition need per safety goal

ISO 26262-9 §5 allows decomposition only between sufficiently independent elements that each implement the safety requirement. The table checks whether any SG needs it.

| SG | ASIL | Primary implementation | Can a single element carry the ASIL? | Decomposition needed? |
|---|---|---|---|---|
| SG-01 | C ⚠ (D if AOU-01/02 fail) | E-03 envelope: torque magnitude, rate, measured tracking, engagement gating (FSR-01.01…01.12) | Not today (GAP-01, -06, -07, -08, -11; GAP-06/-07 partly closed 2026-10-12, not verified on hardware). After hardening, ASIL B is plausible; ASIL C on a COTS single-channel MCU with shared PCB/power is unlikely (WP-M-01 §9) | **Not if** C1 is shown (SG-01 → B). **Yes (fallback)** if C1 fails and option (a) is not reachable |
| SG-02 | C (v0.4; curve case C3, DQ-059) | E-03 backstop (FSR-01.07 stale-command removal, FSR-02.05 SoC-independent buzzer) + QM SoC warning | Only if the envelope reaches ASIL C (as SG-01 under option (a)) | **No (decided, DQ-341 A):** the envelope is hardened to C; DEC-01 extended to the warning path only if the ASIL C hardware metrics fail |
| SG-03 | C ⚠ (D if AOU-03/05 fail; v0.4, OS-07 E4, DQ-036) | E-03 accel bound, inactive value, gas block (FSR-03.01…03.05) | Only if the envelope reaches ASIL C, after the jerk limit (GAP-04) | **No (decided, DQ-341 A):** hardened to C; DEC-01 extended to the longitudinal checks only if the ASIL C hardware metrics fail (its check (4) already covers `0x343`) |
| SG-04 | B ⚠ (C if AOU-05 fails) | E-03 decel bound and onset-rate limit (FSR-04.01…04.04) | Yes, after hardening | As SG-03 |
| SG-05 | B ⚠ (C if AOU-01/02/03 fail) | E-03 brake/cancel revocation, driver-torque override (FSR-05.01…05.06) | Yes, after GAP-02 is closed | As SG-03 |
| SG-06 | C (v0.4, OS-07 E4, DQ-036; confirmation queued as DQ-210) | E-03 backstop + QM detection | Only if the envelope reaches ASIL C | **No (decided, DQ-341 A)**, as SG-02 |
| SG-07 | B | E-03 static forwarding + E-05 relay de-energise-to-stock (FSR-07.01…07.03) | Yes, if relay de-energised state is confirmed (AOU-13) | No |
| SG-08 | A (v0.4, DQ-205) | DM chain on the QM SoC (FSR-02.06…02.09, FSR-08.01) | Not today: the SoC is QM (WP-C-04 OI-11) | No decomposition proposed; an ASIL A DM chain or an ASIL A monitor on the MCU is the route (WP-C-04 OI-11) |

Observation (v0.5): HARA v0.4 raises SG-02, SG-03 and SG-06 to ASIL C outright, not only on a failed AoU. The envelope therefore needs ASIL C for them even if SG-01 drops to B, and the SG-01 judgment above (ASIL C on a COTS single-channel MCU with shared PCB and power is unlikely) applies to them as well. The lead decided on 2026-10-16 (DQ-341, A) to harden the envelope to ASIL C and to extend DEC-01 to these goals only if the ASIL C hardware metrics fail (OI-3). Earlier observation: the ⚠ ratings mean that a failed AoU verification can raise SG-03/04/05 to ASIL C as well. The fallback in §4 is therefore written so that the same independent second element can carry the A(C) half for the longitudinal and override goals, not only for SG-01.

## 4. Fallback decomposition options (WP-C-04 §4.3)

### 4.1 Candidate schemes

| ID | Scheme | Element 1 (higher half) | Element 2 (lower half) | Requirement decomposed | Assessment |
|---|---|---|---|---|---|
| DEC-01 | C(C) = B(C) + A(C) | E-03 envelope on the panda STM32H7 (TSR-101…TSR-110, TSR-301…TSR-311, TSR-401…TSR-413, TSR-501…TSR-516) | **New element E-07 "independent actuation monitor" (IAM)**: a second MCU on the harness side that observes bus 0 TX/RX and can de-energise the intercept relay (stock path) | FSR-01.01 (magnitude), FSR-01.03 (measured tracking), FSR-01.04 (no torque when not engaged), FSR-01.05 (engagement only with PCM cruise active) | **Preferred fallback.** Both elements inside LionDriver's control; independence can be designed in; safe state of E-07 (relay open) is de-energise-to-safe |
| DEC-02 | C(C) = B(C) + A(C) | E-03 envelope | Second software channel on the **same** STM32H7 (diverse re-implementation of the limit checks) | Same as DEC-01 | **Rejected.** Shares clock, power, memory, CAN peripheral, compiler and the SoC-controlled reset/boot pins (GAP-38). The DFA cannot show sufficient independence on one die without MPU partitioning or lockstep (GAP-11). Kept only as a diagnostic-coverage measure inside E-03, not as decomposition |
| DEC-03 | C(C) = B(C) + A(C) | E-03 envelope | Toyota EPS internal LKA torque limitation and timeout (EXT-EPS, AOU-01R) | FSR-01.01, FSR-01.13 | **Not recommended** (§5) |
| DEC-04 | C(C) = A(C) + B(C) | QM-to-ASIL-A upgraded SoC monitor (e.g. controlsd plausibility) | E-03 envelope at B | — | **Rejected.** The SoC is Linux/Python with no partitioning or WCET (GAP-23), could configure the envelope (GAP-09; locked in the reference build since 2026-10-12) and controls its boot pins (GAP-38). It cannot be shown independent of the failure it would monitor (it produces the command) |

### 4.2 DEC-01 element E-07 functional outline (only if activated)

E-07 is a concept, not a design. It is recorded so that the independence requirements in §4.3 have a concrete target.

| Function | Outline |
|---|---|
| Inputs | Bus 0 (car side) RX only, via its own transceiver: `0x2E4` STEERING_LKA (commanded torque, steer request), `0x260` STEER_TORQUE_SENSOR (EPS motor and driver torque), `0x1D2` PCM_CRUISE (cruise active), `0x226` BRAKE_MODULE, `0xAA` wheel speeds, `0x343` ACC_CONTROL |
| Checks (A(C) subset) | (1) `0x2E4` torque magnitude ≤ speed-dependent bound; (2) `0x2E4` non-zero or steer request set only while PCM cruise active; (3) commanded torque within bound of measured EPS torque; (4) `0x343` accel ≤ bound and = inactive value while cruise inactive (if extended to SG-03/04) |
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

![Figure 4-1: DEC-01 fallback — envelope E-03 (B(C)) on the comma device with its shared supply, clock and PCB, the concept element E-07 (A(C)) with its own supply, clock and receive-only CAN transceiver, the independence requirements IR-01 to IR-10, and the shared intercept relay E-05 with the E-07 series switch](figures/fig-a01-4-1-dec01-independence.svg)

*Figure 4-1.* What E-07 must not share with E-03 if DEC-01 is activated: the resources E-03 shares on the device (left), the requirements of this table (middle) and the own resources they give E-07 (right). The relay and connector stay shared (IR-09). E-07 is a concept (§4.2); nothing here exists. Drawn from §4.2 and this table. Source: [`figures/fig-a01-4-1-dec01-independence.svg`](figures/fig-a01-4-1-dec01-independence.svg); change it together with §4.2 and §4.3.

### 4.4 Consequences for the elements if DEC-01 is applied

- E-03 keeps the ASIL B(C) requirements. Its development stays at ASIL B process rigour, but the hardware metrics for the SG-01 path are evaluated at the level of the original ASIL C goal as required by ISO 26262-9 §5 (the decomposition does not reduce hardware metric targets for random failures of the item as a whole). This must be checked against the licensed text during review (OI-4).
- E-07 carries A(C) requirements, developed at ASIL A process rigour.
- Integration, verification of the safety goal, confirmation measures and the DFA stay at ASIL C.
- New TSRs would be needed in WP-S-02 for E-07 (no ID range is reserved yet; proposed: a TSR-52x sub-block, to be agreed with the WP-S-02 author) and a new element E-07 in [WP-C-01](../02-concept/WP-C-01-item-definition.md) and [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md).

## 5. Why crediting the Toyota EPS (DEC-03) is not recommended

| # | Reason | Basis |
|---|---|---|
| 1 | **No development evidence.** ISO 26262-9 §5 needs each decomposed requirement implemented by an element developed to its decomposed ASIL. Toyota provides no evidence that the EPS LKA limitation is ASIL A or better | WP-C-04 §4.1; T-08 (no DIA possible) in [WP-M-01](../01-management/WP-M-01-assurance-strategy.md) |
| 2 | **No independence of input.** The EPS acts on the same `0x2E4` command that the envelope passes. A wrong but in-envelope command is executed by both. The EPS limit only bounds magnitude; it does not check engagement state or driver intent the way FSR-01.04/01.05 do | WP-A-03 coupling factor "shared command" |
| 3 | **Unknown behaviour.** The torque limit, rate limit and timeout (`carstate.py:15-16` comment, ≈1.5–2 s) are reverse-engineered, not specified. Values may differ per EPS firmware (21 fingerprinted EPS versions, `opendbc_repo/opendbc/car/toyota/fingerprints.py`) | AOU-01R, GAP-05 |
| 4 | **Change outside LionDriver control.** A Toyota EPS reflash (dealer campaign) can change the behaviour without notice; no change notification exists | WP-M-11 (supplier management) |
| 5 | **Assessor acceptance risk.** A decomposition that rests on an unverified, unowned element is unlikely to pass I3 confirmation review | WP-C-04 §4.2 rationale 3 |

The EPS limitation is still **used** as an external measure (FSR-01.13, TSR-111, AOU-01R) in the controllability rating and as defence in depth. It is characterised by vehicle test ([WP-S-09](../03-system/WP-S-09-system-verification.md) VS-SQ-01, VS-SQ-02). Using it as an external measure that supports a controllability rating is different from crediting it with a decomposed ASIL.

## 6. Decomposition record template

One record per applied decomposition. Records live in this document, §7, and are referenced from WP-C-04 and WP-S-02.

| Field | Content |
|---|---|
| Record ID | DEC-nn |
| Status | Proposed / Applied / Withdrawn |
| Safety goal and ASIL | SG-xx, ASIL x |
| Original requirement(s) | FSR/TSR IDs with ASIL before decomposition |
| Decomposition scheme | e.g. C(C) = B(C) + A(C) |
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
| DEC-01 | SG-01 (and SG-03/04/05 if their AoUs fail) | C(C) = B(C) envelope + A(C) independent actuation monitor E-07 | **Proposed (fallback, not applied)** | Activate only per §2 trigger. Needs new element, new TSRs, DFA closure |
| DEC-02 | SG-01 | Two channels on one MCU | Withdrawn (rejected, §4.1) | Recorded for traceability of the decision |
| DEC-03 | SG-01 | Envelope + Toyota EPS | Withdrawn (not recommended, §5) | EPS stays an external measure only |
| DEC-04 | SG-01 | SoC monitor + envelope | Withdrawn (rejected, §4.1) | |

## 8. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Closed 2026-10-14: option (c) confirmed (DQ-007, WP-C-04 §4). This document stays "no decomposition applied" | Maintainer | G1 |
| OI-2 | After controllability tests (WP-C-04 OI-2), decide whether DEC-01 is activated (timing of the decision set by the lead on 2026-10-14, DQ-050: after the tests, not before); if yes, add E-07 to WP-C-01, WP-S-03, and request new TSRs in WP-S-02. *v0.7:* since DQ-341 A the trigger for DEC-01 is a failed ASIL C hardware metric (OI-3), not a failed controllability test | Safety engineer | G2 |
| OI-3 | If AOU-05 or AOU-03 verification fails (SG-03/04/05 → ASIL C), extend DEC-01 scope to the longitudinal and override requirements or re-plan. *v0.5:* SG-02, SG-03 and SG-06 are ASIL C since HARA v0.4 whatever the AoUs show; decided (DQ-341, A): DEC-01 is extended to them only if the ASIL C hardware metrics of WP-H-04 fail | Safety engineer | G2 |
| OI-4 | Check §4.4 statement on hardware metrics after decomposition against the licensed ISO 26262-9 §5 text | Safety engineer | G2 |
| OI-5 | Confirm AOU-13 (relay de-energised state = stock path); DEC-01 and SG-07 both depend on it | HW lead | G2 |
