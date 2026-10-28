# WP-C-04 Functional Safety Concept

| Field | Value |
|---|---|
| Work product | WP-C-04 Functional safety concept (FSRs, allocation, AoUs) |
| Standard reference | ISO 26262-3:2018 §7; ISO 26262-9:2018 §5 (ASIL decomposition, by reference); ASPICE 4.0 SYS.2 |
| Version | 0.31 (RX timeout bound ≤ 0.162 s, was ≤ 0.16 s, as WP-S-04 v0.21 T-01 (161.5 ms: 5 periods of 30.3 ms plus one 10 ms task period); no requirement, budget or verdict changed; 2026-10-27). 0.30 (FSR-02.12 implementation status: the start-up fault-code read is in the host software (TSR-629, DQ-132 A), not verified on the vehicle; requirement unchanged; 2026-10-25). 0.29 (Figure 10-1, the item boundary of WP-C-01 Figure 3-2 in the safety view, and Figure 12-1, the degradation ladder, added; §2 integrity of E-03 and E-05 brought to ASIL C (DQ-341, as §10 and WP-S-03 already had); §5.2, §5.3 and §5.6 headings brought to the §3 ASILs (C since HARA v0.4); no requirement changed; 2026-10-24). 0.28 (FSR-04.05: the alert comes ahead of the driver-monitoring no-response deceleration and at the latest at the onset of a fault soft-disable deceleration (DQ-407 A); no behaviour change; 2026-10-22). 0.27 (FSR-01.09 implementation status brought up to date: the IWDG is implemented (panda `hw_watchdog.h`, TSR-501, HWSR-501), not verified on hardware; other execution faults still report-only. No requirement changed; 2026-10-22). 0.26 (FSR-02.05: trigger widened to any end of granted authority that is not an observed driver action, matching TSR-516(b)/(c); found by the six-routes walk (`fsc/requirement-routes.md`), no behaviour change; 2026-10-21). 0.25 (FSR-01.02: the rate limit covers the rise; a fall toward zero is not limited (FRET pilot FF-01, matches the envelope code); 2026-10-21). 0.24 (FSR-02.05 status: siren on a "not engaged" heartbeat while cruise stays on, panda `f4803c5`; 2026-10-21). 0.23 (FSR-04.05 status follows TSR-624: the no-response deceleration is announced; the fault soft disable is open (DQ-407); 2026-10-20). 0.22 (FSR-02.09 status follows TSR-633: the stop, hold and resume lockout are implemented in software, not verified on the vehicle; 2026-10-20). 0.21 (§9: link to the generated requirement trees per goal; 2026-10-20). 0.20 (FSR-02.10 and FSR-05.06 statuses follow TSR-621 and TSR-308 (#51); 2026-10-20). 0.19 (FSR-02.05 status: the siren on the TSR-408 revocation is implemented, panda `8a69ccf`; 2026-10-20). 0.18 (FSR-02.05 status: a full SoC stall is silent today, siren on the TSR-408 revocation required by DQ-404 A; 2026-10-19). 0.17 (§4.2 recommendation marked superseded for the envelope target: ASIL C since DQ-341 A; 2026-10-19). 0.16 (FSR-07.07 implemented and unit-tested, host request and `0x343` ≤ 0 during stock AEB (`c045874`, opendbc `e233362`); not verified on the vehicle; 2026-10-19). 0.15 (FSR-07.07 status: host request capped at ≤ 0 during stock AEB, `c045874` (#292); 2026-10-19). 0.14 (§8 FTTI scene cards, one per safety goal, drawn as Figures 8-1 to 8-3 by `fsc/fsc_scenes.py`; no requirement or budget changed; 2026-10-19). 0.13 (§8 current-behaviour rows for RX loss and SoC command loss brought up to the reference build: RX timeout ≤ 0.16 s (≈ 0.21 s for `0x262`), heartbeat loss > 0.3 s and command arrival > 50 ms / 100 ms revoke authority; not verified on hardware; SG-07 forwarding-loss row: an MCU hang is caught by the 90 ms IWDG, other forwarding loss is still unsupervised; 2026-10-19). 0.12 (lead answers of 2026-10-18 applied: FSR-07.07 stock-AEB stand-down (DQ-300 A); AOU-17 EPS and PCM report every drop or non-execution, verified with forced faults (DQ-360 A); 2026-10-18). 0.11 (DQ-052 applied: the false-FCW ASIL A on the QM SoC is to be resolved by SOTIF validation and a re-rating of HE-04.5; FSR-04.06 keeps ASIL A until that evidence exists; OI-9 narrowed; 2026-10-17). 0.10 (DQ-365 applied (DQ-340 merged into it): the no-response reaction keeps the lane, decelerates to a standstill and stays stopped and held, with re-engagement locked out until the driver responds; FSR-02.09, §3, §6, §7, §8; 2026-10-16). 0.9 (DQ-341 applied: the envelope is hardened to ASIL C; DEC-01 only if the ASIL C hardware metrics fail; §4, §10; 2026-10-16). 0.8 (HARA v0.4 ratings applied: SG-02, SG-03 and SG-06 ASIL C, new SG-08 ASIL A; FSR ASILs re-derived; FSR-02.06…02.09 ASIL A for SG-08; FSR-02.09 states the SG-08 safe state; new FSR-08.01 (SG-08 alert time); §4 notes that the envelope target is ASIL C whatever SG-01 becomes, queued for the lead as DQ-341; new OI-11; 2026-10-16). 0.7 (FSR-02.09 Impl corrected: no disengagement at zero awareness; §7 notes the H-09 goal of DQ-205 and the queued reaction DQ-340; System FMEA monitoring actions refined into TSR-630…633 of WP-S-02 v0.22; 2026-10-16). 0.6 (lead decisions of 2026-10-14 applied, register DQ-007, DQ-048, DQ-050, DQ-053, DQ-054, DQ-056, DQ-060, DQ-062, DQ-063, DQ-064, DQ-114: §4 strategy decided, FSR-02.05, FSR-05.03 and FSR-07.03 amended, new FSR-02.12 and FSR-07.06, §3, §8 and §12.1 updated, OI-1 closed; 2026-10-16). 0.5 (heartbeat-loss siren, panda `c33343b`; EPS-siren worst case 1.26 s; 2026-10-13). 0.4 (Figure 5-1 added, generated from §3, §5 and §9; 2026-10-13). 0.3 (preliminary SG-07 FTTI from WP-S-04 §3.6; watchdog budget; 2026-10-12) |
| Status | Draft |
| ASIL / scope | Up to ASIL C (SG-01, SG-02, SG-03, SG-06); ASIL B for SG-04, SG-05, SG-07; ASIL A for SG-08 (WP-C-03 v0.4) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); input to G1 confirmation review (I3) per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `d17aac4` (opendbc `229dc70`, panda `92eb565`; code unchanged since `8b8c6ae` apart from `process_replay/ref_commit`) |

## 1. Purpose and inputs

This document derives functional safety requirements (FSRs) from the safety goals SG-01…SG-07 of the [HARA (WP-C-03)](WP-C-03-hara.md) and allocates them to the architectural elements of the [item definition (WP-C-01)](WP-C-01-item-definition.md). It also records the envelope strategy decision that the HARA left open (WP-C-03 §6.1, OI-4), the integrity attributes of driver monitoring (WP-C-03 §6.1 obs. 3), and the refined assumptions of use (AoU) on the vehicle and driver.

Inputs:

- [WP-C-01](WP-C-01-item-definition.md): functions F-01…F-09, elements E-01…E-06, interfaces IF-01…IF-09, AOU-01…AOU-11 (AOU-12 and AOU-13, defined in §11, were added to WP-C-01 in its v0.2).
- [WP-C-03](WP-C-03-hara.md) v0.2 (Cartesian HARA): hazards H-01…H-08; SG-01…SG-07 with ASIL, safe states and preliminary FTTIs; the new hazardous-event sources of WP-C-03 §6.1 obs. 5.
- [WP-C-02](WP-C-02-odd-and-intended-functionality.md): ODD and intended functionality.
- [Gap assessment](../00-assessment/gap-assessment.md): GAP-01…GAP-37.
- [WP-M-01 §4](../01-management/WP-M-01-assurance-strategy.md#4-safety-architecture-argument-the-central-strategy): safety envelope pattern.

Interface to cybersecurity (ISO/SAE 21434 §9.5): the cybersecurity goals that protect each safety goal against an attacker are mapped in [WP-C-10 §8](WP-C-10-cybersecurity-goals-and-concept.md#8-relation-to-safety-goals), against the FSR allocation of §5 and §10 below. A change to an FSR's allocation between the envelope (E-03) and the SoC (E-01) changes that mapping and must be reflected there.

The ASILs in this document are those proposed in the HARA. The HARA is not yet confirmed (I3). If the confirmation review changes a rating, the FSR ASILs here change with it.

## 2. Architectural elements used for allocation

| Element | Description | Integrity it can carry today | Notes |
|---|---|---|---|
| E-03 | Safety envelope: opendbc safety (Toyota mode) and the panda firmware paths it relies on, on the STM32H7 | ASIL C: hardened to C (DQ-341 A, §4); SG-01 FSRs carry ASIL C until C1 is shown (§4.2) | The only path to the actuators. Single channel (GAP-11) |
| E-01 | Application SoC software: openpilot processes (selfdrived, controlsd, plannerd, card, pandad, ...) | QM | Python, no partitioning, no WCET (GAP-23) |
| E-02 | ML models: driving model, DM model | QM (SOTIF / PAS 8800 managed) | No uncertainty gating (GAP-22) |
| E-01/DM | Driver monitoring chain: driver camera → dmonitoringmodeld → dmonitoringd → selfdrived | QM (see §7) | Source validity hard-coded (GAP-21) |
| E-04 | Device hardware hosting E-01 and E-03: SoC, panda MCU, shared power supply, clocks, CAN transceivers (WP-C-01 E-04) | Shared platform; integrity of E-03 depends on it | The QM SoC controls the panda MCU reset and boot lines (`STM_RST_N`/`STM_BOOT0`) and can force the ROM bootloader or reflash the MCU (GAP-38); shared supply and PCB (dependent-failure analysis, [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md)) |
| E-04/HMI | Device display and speaker (soundd/ui), panda buzzer ("siren"), cluster LKAS HUD (`0x412`) | QM, except the panda siren which is driven by E-03 | |
| E-05 | Harness with intercept relay | ASIL C for blocking (SG-01, SG-03 via FSR-01.11); B for the PCS path (SG-07) | Relay default state to be confirmed (OI-6) |
| EXT-EPS | Toyota EPS (external measure) | Unknown; credited through AOU-01/02 only | No supplier evidence |
| EXT-PCM | Toyota ECM/PCM and brake actuator (external measure) | Unknown; credited through AOU-03/05 only | |
| EXT-CLU | Toyota instrument cluster cruise indicator (driven by the PCM) | Unknown; used as an independent mode indication | |
| DRV | Driver | Not an E/E element; assumptions only (AOU-06, AOU-02) | |

## 3. Safety goals (summary from WP-C-03)

| SG | Statement (short) | ASIL | Safe state | Preliminary FTTI |
|---|---|---|---|---|
| SG-01 | No uncontrollable lateral motion, no steering actuation while not engaged | C ⚠ (D if AOU-01/02 fail) | LKA torque 0, steer request cleared | ≤ 0.5 s |
| SG-02 | No loss/degradation of lateral control without adequate take-over warning | C | Warning + torque ramp-down | ≤ 1 s to warning |
| SG-03 | No unintended acceleration | C ⚠ (D if AOU-03/05 fail) | Accel ≤ 0; ACC cancelled | ≤ 1 s |
| SG-04 | No deceleration beyond what following traffic and driver can control | B ⚠ (C if AOU-05 fails) | Inactive (no ACC command) with bounded jerk | ≤ 1 s |
| SG-05 | Release on driver brake, cancel, steering override | B ⚠ (C if AOU-01/02/03 fail) | Disengaged | ≤ 0.2 s |
| SG-06 | No loss of longitudinal deceleration without take-over warning | C | Warning; ACC cancelled | ≤ 1 s |
| SG-07 | No suppression, delay or alteration of stock PCS/AEB | B | Camera PCS messages forwarded; relay released if forwarding cannot be guaranteed | ≤ 0.2 s for forwarding loss (preliminary, WP-S-04 §3.6; accepted as the working budget until measured, DQ-062); content: per frame |
| SG-08 | No continued automated control while the driver is not supervising or not responding, without escalation to a minimal-risk reaction | A | Escalating alerts; on no response, controlled deceleration in lane to a standstill with steering on, then stay stopped and held with re-engagement locked out until the driver responds (DQ-365, A) | ≤ 6 s from loss of attention to the first alert (WP-C-08 OI-2); time to the no-response reaction set in WP-S-04 |

ASILs are those of [WP-C-03](WP-C-03-hara.md) v0.4: SG-02 C (curve case C3, DQ-059), SG-03 and SG-06 C (OS-07 rated E4 by frequency, DQ-036; for SG-06 also queued for confirmation as DQ-210), and the new SG-08 A (DQ-205). An FSR carries the highest ASIL of the goals it serves in §9, except where §7 argues that the DM chain carries no attribute from SG-02/SG-06.

## 4. Envelope strategy decision (HARA §6.1, OI-4)

SG-01 at ASIL C (D if the EPS assumptions fail) drives the integrity of the envelope. The HARA lists three options. This section evaluates them and recommends one.

**Decided 2026-10-14 by the project lead ([register](../01-management/decisions/register.yaml) DQ-007): option (c), reduced steering authority so that SG-01 can drop to ASIL B, with the envelope hardened to ASIL B.** The conditions of §4.2 apply unchanged: SG-01 and its FSRs stay ASIL C until the HARA owner re-rates SG-01 on controllability evidence. Hardware is designed to ASIL C until then, with the ASIL B figures shown alongside (DQ-063; WP-H-04). Whether the fallback of §4.3 is started is decided after the controllability tests, not now (DQ-050).

**HARA v0.4 consequence (2026-10-16):** the decision rested on rationale 1 of §4.2, that lowering SG-01 to B gives the whole envelope one target, ASIL B. With SG-02, SG-03 and SG-06 now at ASIL C, the envelope requirements for those goals (FSR-02.04, 02.05, 02.10, 03.01…03.05, 05.05, 05.06, 06.04) are ASIL C whatever SG-01 becomes. Option (c) still lowers the SG-01 requirements and bounds the lateral worst case, but no longer lowers the envelope's target. The hardware is already designed to C (DQ-063). Whether the envelope is now hardened to ASIL C, or a decomposition is planned for the longitudinal and warning paths, was put to the lead as DQ-341.

**Decided 2026-10-16 by the project lead (DQ-341, option A): the envelope is hardened to ASIL C now; the second independent checker (DEC-01) is started only if the ASIL C hardware metrics fail.** The controllability tests for SG-01 still go ahead: they keep SG-01 from needing ASIL D if AOU-01/02 fail, and they lower the SG-01 requirements, but no longer the envelope's target. The ASIL C hardware metrics (WP-H-04) become final targets, not interim ones, and the envelope software follows the ASIL C process.

### 4.1 Evaluation

| Criterion | (a) Harden the envelope to ASIL C | (b) ASIL decomposition C(C) = B(C) envelope + A(C) EPS | (c) Reduce actuation authority so controllability C1 can be shown, lowering SG-01 to ASIL B |
|---|---|---|---|
| What it needs | ASIL C hardware metrics (SPFM/LFM/PMHF targets) on a COTS single-channel MCU; ASIL C software process (MC/DC, GAP-13); E2E with counters on all RX (GAP-01); IWDG and fault reaction (GAP-07/08); DFA of shared SoC/MCU power and clock | Two **independent** elements that each satisfy the safety goal on their own; DFA showing independence; evidence that the EPS implements an ASIL A(C) torque limitation | Vehicle characterization of the EPS torque authority (AOU-01/02); a physically derived, speed-dependent torque limit in the envelope; controllability tests (WP-C-08 §8) showing ≥ 99 % of drivers control envelope-bounded worst-case actuation |
| Feasibility for an aftermarket retrofit | Low to medium. No supplier FMEDA data for the device; the shared PCB/power with the QM SoC makes the ASIL C hardware metrics hard to reach (WP-M-01 §9) | Low. Toyota provides no evidence of the EPS internal limitation, its ASIL or its independence. ISO 26262-9 §5 requires that independence be shown, not assumed. An external element cannot receive a decomposed ASIL without evidence of its development | Medium to high. Needs vehicle testing, which is needed anyway for AOU-01/02 (HARA OI-1). Matches the ISO 11270 reasoning in `docs/SAFETY.md` |
| Effect on availability | None | None | Less steering authority: some curves inside today's operating range can no longer be followed. Narrows the ODD (WP-C-02 §4.2) |
| Residual dependence on unverified AoUs | Low for SG-01 (the envelope alone carries the goal) | High (EPS) | Medium (EPS limit still bounds the worst case; driver controllability is measured, not assumed) |
| Effort | Highest | Medium, but blocked on evidence that LionDriver cannot obtain | Medium |

### 4.2 Recommendation

**Recommended: option (c) reduced authority, combined with hardening of the envelope to ASIL B.** Option (b) is kept as a documented fallback but is not recommended as the primary route. *The ASIL B envelope target is superseded: since 2026-10-16 the envelope is hardened to ASIL C (DQ-341 A, §4); option (c) still lowers the SG-01 requirements.*

Rationale:

1. Option (c) attacks the risk at its source. The worst-case consequence of any E/E fault on the lateral path is bounded by what the envelope lets through. If that bound is chosen so that a typical driver controls it (C1), HE-01.1/01.2/01.4 become S3 E4 C1 = ASIL B, the same level as SG-02…SG-07. The whole envelope then has one target ASIL (B). *Superseded by HARA v0.4: SG-02, SG-03 and SG-06 are now ASIL C, so the envelope target stays C (see §4, DQ-341).*
2. ASIL B hardening is needed under every option (IWDG, fault → safe state, safety-mode lock, E2E counters, FTTI-consistent timeouts). Option (c) does not add hardware-metric targets that the COTS device is unlikely to meet.
3. Option (b) requires evidence about the Toyota EPS that is not available. LionDriver cannot show the EPS was developed to ASIL A or that it is independent of the item (it consumes the item's command). A decomposition argument built on it would not survive an I3 review.
4. Option (a) remains possible later if hardware metrics turn out better than expected. Nothing in (c) prevents it.

Conditions attached to the recommendation:

- **Until the controllability evidence exists, SG-01 stays ASIL C** and the SG-01 FSRs below carry ASIL C. They are expected to drop to ASIL B once the HARA is re-rated on evidence. The HARA owner re-rates; this document does not.
- The reduced limit must be derived physically (torque at the wheel → lateral acceleration and lateral deviation over the FTTI, per speed), not tuned. That closes GAP-04 for the lateral path.
- The controller (E-01) limits must sit below the envelope limits with margin, so that normal operation never runs at the enforcement boundary (gap assessment §3.1 notes zero margin today).

### 4.3 Fallback: ASIL decomposition (if C1 cannot be shown)

No work on this fallback starts before the controllability tests report (DQ-050, decided 2026-10-14: decide after the tests; the cost accepted is a late re-plan if a test fails). If vehicle tests show that C1 cannot be reached at a torque level that keeps the function useful, the fallback is decomposition of SG-01:

- **ASIL C(C) = ASIL B(C) on the envelope (E-03) + ASIL A(C) on a second, independent limiting element.**
- The second element should be inside LionDriver's control, not the Toyota EPS: for example an independent hardware torque/request monitor on the harness side, or a second MCU checking `0x2E4` against measured EPS torque and steering state, able to open the relay.
- Independence requirements (to be analysed in [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md) and [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md)): separate power supply path or supervised supply, separate clock, separate CAN receive path, no shared software, no configuration of one element by the other, and a de-energise-to-safe actuation (relay open = stock path).
- Crediting the EPS as the A(C) element is **not recommended** for the reasons in §4.1.

## 5. Functional safety requirements

![Figure 5-1: for each safety goal SG-01 to SG-08 with its ASIL, safe state and preliminary FTTI, the FSRs of §5 with their ASIL, the other goals each serves in the §9 trace, and markers for the elements E-03, E-05, E-01, E-01/DM, E-01/HMI, E-02, EXT-EPS, EXT-PCM and EXT-CLU named in the Alloc column](fsc/figures/fig-c04-5-1-sg-fsr-allocation.svg)

*Figure 5-1.* Safety goals → FSRs → allocated elements. Each band is one goal with its ASIL, safe state and preliminary FTTI from §3. Each row is one FSR of §5 with its ASIL and the other goals that the §9 trace marks for it. A marker sits in the column of every element named in its Alloc column. A marker shows allocation only: every FSR is `Proposed`, and the Impl column gives the implementation status. Roles given in brackets in the Alloc column (detection, alert, backstop) are not drawn. Source: [`fsc/figures/fig-c04-5-1-sg-fsr-allocation.svg`](fsc/figures/fig-c04-5-1-sg-fsr-allocation.svg), generated by [`fsc/fsc_figures.py`](fsc/fsc_figures.py) from §3, §5 and §9. Change those sections and regenerate; do not edit the SVG.

Attributes: ASIL as currently derived; **Alloc** = allocation; **Verif** = verification method (A = analysis, R = review, T-SIL = software test, T-HIL = hardware-in-the-loop test, T-VEH = vehicle test, FI = fault injection). **Impl** = what the baseline code already does (file:line) or the GAP that blocks it. Paths for E-03 are under `opendbc_repo/opendbc/safety/` unless prefixed `panda/`. Paths for E-01 are under `openpilot/`. All statuses are `Proposed`.

### 5.1 SG-01 Lateral motion (ASIL C ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-01.01 | The envelope shall limit the commanded LKA torque magnitude to a speed-dependent bound derived from driver controllability (lateral acceleration and lateral deviation reached within the FTTI). | C | E-03 | A, T-SIL, T-VEH | Partial: fixed 1500 raw (`modes/toyota.h:173`); not speed-dependent, no physical rationale (GAP-04) |
| FSR-01.02 | The envelope shall limit the rate of change of the commanded LKA torque (rise per frame and over a real-time window) to bounds derived from controllability. A fall toward zero is not limited, as it is the safe direction for SG-01; a bounded ramp of torque withdrawn on a fault is FSR-02.04. | C | E-03 | A, T-SIL | Implemented without rationale: 15/25 raw per frame, 450 raw per 250 ms (`modes/toyota.h:174-177`, `lateral.h:49-57, 87-95`) (GAP-04) |
| FSR-01.03 | The envelope shall limit the commanded LKA torque to within a bounded difference of the measured EPS motor torque. | C | E-03 | T-SIL | Implemented: 350 raw (`modes/toyota.h:176`, `lateral.h:10-23`) |
| FSR-01.04 | The envelope shall block any non-zero LKA torque or set steer-request bit while lateral authority is not granted. | C | E-03 | T-SIL, T-HIL | Implemented (`lateral.h:98-101`) |
| FSR-01.05 | The envelope shall grant actuation authority only on a driver engagement action confirmed by the vehicle (rising edge of PCM cruise active) and shall revoke it when PCM cruise becomes inactive. | C | E-03 | T-SIL, T-VEH | Implemented (`safety.h:518-527`); PCM_CRUISE has no counter (GAP-01) |
| FSR-01.06 | The envelope shall detect loss, corruption, repetition and staleness of each RX signal it uses for gating or limiting (PCM cruise state, brake, gas, driver/EPS torque, wheel speed) and revoke actuation authority within the FTTI allocation of §8. | C | E-03 | T-SIL, FI | Partial: checksum on some messages, timeouts detected in ≤ ≈2 s (`safety.h:164-197, 321-344`); no counters, `0x226`/`0xAA` no checksum (`modes/toyota.h:40-46`) (GAP-01, GAP-06) |
| FSR-01.07 | The envelope shall detect missing or stale control commands from the SoC and remove actuation within the FTTI allocation of §8. | C | E-03 | T-HIL, FI | Partial: heartbeat mismatch 3 s, loss 5 s (`panda/board/main.c:182-213`); too slow for SG-01 (GAP-06); heartbeat shows pandad liveness only (GAP-10) |
| FSR-01.08 | The envelope shall detect corruption, loss and reordering of command frames received from the SoC and discard affected frames. | C | E-03 | T-HIL, FI | Partial: 8-bit XOR, no sequence counter (`panda/board/drivers/spi.h:97-138`, `can_comms.h:27`) (GAP-10) |
| FSR-01.09 | The safety MCU shall detect its own execution faults (program-flow hang, clock failure, memory corruption, register corruption) and enter the safe state (no actuation TX, relay released) within the FTTI allocation of §8. | C | E-03 (HW+SW) | A (FMEDA), FI | Partial: an independent windowed watchdog (IWDG1, LSI clock) is started when the relay is first driven and fed from the 100 Hz safety task (`panda/board/drivers/hw_watchdog.h`; TSR-501, HWSR-501: implemented, not verified on hardware, DF-01); other execution faults are still report-only, `PERMANENT_FAULTS = 0U` (`panda/board/sys/sys.h:50`) (GAP-07, GAP-08) |
| FSR-01.10 | The safety mode and safety parameter for the reference configuration shall be fixed in the envelope and shall not be changeable by the SoC while a car safety mode is active; debug-only commands shall be unavailable in release builds; and the SoC shall not be able to make the safety MCU run non-release code or drive the relay outside the envelope through its reset and boot lines (GAP-38, refined by TSR-511). | C | E-03 | R, T-HIL | Not implemented: `0xdc` sets any mode at any time; `0xc5` relay drive not gated (`panda/board/main_comms.h:144-147, 222-225`) (GAP-09, GAP-25) |
| FSR-01.11 | The envelope shall detect a harness relay malfunction (camera control messages seen on the car side) and inhibit all actuation TX. | C | E-03, E-05 | T-SIL, T-HIL | Implemented with 1–2 s grace and no contact readback (`safety.h:215-220, 372-380`) (GAP-12) |
| FSR-01.12 | On any detected fault affecting lateral actuation, the envelope shall enter the lateral safe state (torque 0, steer request cleared) and keep it until a new valid engagement. | C | E-03 | T-SIL, FI | Partial: violating frames dropped and `controls_allowed` cleared on RX faults (`lateral.h:141-148`, `safety.h:112-121`); a TX violation alone does not revoke authority. 2026-10-14: a rejected command also ends authority until re-engagement (DQ-060, TSR-108); firmware change open |
| FSR-01.13 | The EPS shall limit LKA torque to an overpowerable level and shall end LKA torque within a bounded time after `0x2E4` stops or carries the request bit cleared. (External measure, AOU-01R) | — (ext.) | EXT-EPS | T-VEH | Unverified (GAP-05) |
| FSR-01.14 | The SoC controller shall command lateral motion with a margin below every envelope limit (target: commanded lateral acceleration ≤ 3.0 m/s², jerk ≤ 5 m/s³, torque ≤ 90 % of the envelope bound). | QM | E-01 | T-SIL | Partial: 3.0 m/s², 5 m/s³ (`selfdrive/controls/lib/drive_helpers.py:9-14`); torque limits equal to envelope (`opendbc_repo/opendbc/car/toyota/values.py:20, 45-47`) |

### 5.2 SG-02 Lateral loss without warning (ASIL C)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-02.01 | The item shall detect EPS conditions that remove or reduce LKA assistance (EPS LKA fault states) while engaged. | C | E-03 (detection), E-01 (diagnosis text) | T-SIL, T-VEH | Host-only (QM): `opendbc_repo/opendbc/car/toyota/carstate.py:122-127` → `steerTempUnavailable`/`steerUnavailable`; not in envelope (GAP-03) |
| FSR-02.02 | The item shall detect loss of the inputs that the lateral command depends on (driving model output, calibration, localization, vehicle state) and shall not continue to actuate on inputs that are no longer valid. | C | E-01 (QM, see note), E-03 (FSR-01.07 as backstop) | T-SIL, FI | Not met: soft disable keeps actuating for 3 s on failed inputs (`selfdrive/selfdrived/state.py:7-8`); controlsd does not check freshness (`selfdrive/controls/controlsd.py:66, 122-127`) (GAP-16); diagnostics masked during big-model fallback (`selfdrive/selfdrived/selfdrived.py:428-430, 449, 505`) (GAP-17) |
| FSR-02.03 | On a detected loss or degradation of lateral control, the item shall give a visual and acoustic take-over request within 1 s of fault detection and before or at the start of torque reduction. | C | E-01/HMI, E-03 siren for SoC loss | T-HIL, T-VEH | Partial: soft/immediate disable alerts (`selfdrive/selfdrived/events.py:224-234`); timing not verified |
| FSR-02.04 | When torque is withdrawn because of a fault (not a driver action), the reduction shall follow a bounded ramp unless the fault makes the command itself untrusted, in which case torque shall go to zero at once. | C | E-01, E-03 | A, T-SIL | Partial: rate-down limit 25 raw/frame enforced (`modes/toyota.h:175`); no defined fault ramp |
| FSR-02.05 | When granted actuation authority ends for a reason other than a driver action that the safety MCU itself observes, the safety MCU shall give an acoustic warning that does not depend on the SoC. This covers the loss of communication with the SoC or of its commands, a fault the safety MCU detects, a disengagement reported by the SoC whose cruise cancel had no effect, and a reset of the safety MCU (watchdog or fault reset) that interrupts granted authority. The reset case was added 2026-10-14 (DQ-054: the engaged state is kept across the reset; TSR-516(d)); the trigger was widened 2026-10-21 to match TSR-516(b)/(c) (DQ-404 A; cancel-lag guard, lead 2026-10-21). | C | E-03 (panda buzzer) | T-HIL | Partial: siren 3 s after heartbeat loss (`panda/board/main.c:193-205`); depends on 5 s detection (GAP-06). 2026-10-13: siren also at the 0.3 s heartbeat revocation (TSR-407) when authority was granted, ≈ 0.56 s after the last heartbeat, all builds (panda `c33343b`, TSR-516; WP-S-04 T-07a); not verified on hardware. Since opendbc `273f44e` a full SoC stall is revoked first by the command-arrival check (TSR-408, WP-S-04 T-34), which sounded no siren until panda `8a69ccf` / opendbc `4d1a056`: since then that revocation sounds the same 3 s siren, ≤ 0.31 s after the last `0x2E4` (TSR-516(b), DQ-404 A; host-tested, not verified on hardware). Since panda `f4803c5` (#382) a heartbeat reporting "not engaged" while PCM cruise stays active also sounds it, 0.5 s after the first such heartbeat (TSR-516(c), cancel-lag guard, lead 2026-10-21); plant: 0.63–0.88 s after selfdrived stops; not verified on hardware |
| FSR-02.06 | Driver monitoring shall detect an inattentive or unresponsive driver while engaged and escalate warnings within the timing set in [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) §5. | A | E-01/DM, E-02 | T-SIL, T-VEH | Implemented: 5/8/13 s vision, 5/15/25 s wheel-touch (`selfdrive/monitoring/policy.py:31-36`) |
| FSR-02.07 | Driver monitoring shall detect its own invalidity (no driver image, camera blocked, model output missing or not credible) and fall back to a policy that is no less strict than the active policy. | A | E-01/DM | T-SIL, FI | Partial: high-uncertainty → wheel-touch fallback (`policy.py:82-83`); source validity hard-coded `True` (`selfdrive/modeld/dmonitoringmodeld.py:99`); wheel-touch awareness reset by any steer/gas input (`policy.py:375-376`) (GAP-21) |
| FSR-02.08 | Driver monitoring shall not be disabled, put into demo mode or replaced by synthetic inputs while the item can engage. | A | E-01/DM | R, T-SIL | Not met: `IsDriverViewEnabled` demo mode (`selfdrive/monitoring/dmonitoringd.py:26-27`, `policy.py:484-493`) (GAP-20) |
| FSR-02.09 | If the driver does not respond to the highest DM warning, the item shall decelerate the vehicle in a controlled way in its lane to a standstill, keep it stopped and held, and prevent the item from driving off again or being re-engaged until the driver responds; after the driver responds, the lockout period applies. This is the SG-08 safe state (WP-C-03 v0.4), decided 2026-10-16, DQ-365 A: steering stays on while the vehicle decelerates in lane to a standstill within the envelope limits with the alert sounding; the vehicle then stays stopped and held, and the item cannot drive off again: re-engagement and resumption are locked out until the driver responds. Lateral and longitudinal control shall not stay active at the set speed. | A | E-01/DM | T-SIL, T-VEH | Implemented in software, not verified on the vehicle (TSR-633): after 5 s at the terminal alert the no-response deceleration is latched in `selfdrived` until the driver takes over (`selfdrive/selfdrived/minimum_risk.py`), so the vehicle stops in lane and stays stopped with the standstill hold requested, cannot resume, and the alert keeps sounding; the lockout of 1/5/15/30 min runs from the takeover (`policy.py:368-369`). Open: the PCM standstill hold over time (AOU-16) and the vehicle test (T-VEH). Reaction decided (DQ-365, A) |
| FSR-02.10 | The item shall detect that the envelope does not grant actuation authority while the SoC is engaged (envelope blocking, stuck authority, safety-mode mismatch) and give a take-over request within the SG-02/SG-06 warning budget (§8). | C | E-01 (detection, alert), E-03 (reports authority state) | T-SIL, FI | Partial: an authority mismatch is detected within the ≤ 1 s budget, `controlsMismatch` after 2 consecutive mismatched `pandaStates` samples (10 Hz, about 0.1–0.2 s) and at most 0.5 s after the first mismatched frame (`selfdrive/selfdrived/selfdrived.py:361-366, 566-574`, `supervision.py`; TSR-621, LionDriver #51); not verified on the vehicle. Blocking that the envelope does not report in `controlsAllowed` is not detected (WP-A-03 DFI-24; TSR-626). Before #51: 200 frames, about 2 s. New in v0.2 (HE-02.4) |
| FSR-02.11 | The item shall detect failure of the HMI path that shows the engagement state and gives take-over requests (display, sound) and treat it as a fault leading to disengagement with the SoC-independent indications (FSR-02.05 buzzer, FSR-05.05 cluster cruise state). | C | E-01/HMI, E-03 | T-SIL, FI | Partial: a crashed `ui`/`soundd` raises `processNotRunning` (`selfdrive/selfdrived/selfdrived.py:398-404`); a hung but running UI, a frozen indication or muted audio is not detected. New in v0.2 (H-07, HE-07.x) |
| FSR-02.12 | Before granting engagement, and while the item can engage, the item shall read the stored diagnostic trouble codes of the EPS and of the brake and stability control, and shall not allow engagement while a code that affects lateral or longitudinal control is set; the driver shall be told why. (Decided 2026-10-14, DQ-056: replaces reliance on the driver's dashboard lamp check, WP-O-02 OPS-01.) | QM (supports FSR-02.01, FSR-06.03) | E-01 | T-SIL, T-VEH | Implemented in host software, not verified on the vehicle (DQ-132 A, 2026-10-25): TSR-629, SWSR-629…629d; any active EPS or ABS/VSC code, and a failed read, refuse engagement; the lamp check (WP-O-02 OPS-01) stays as a second barrier. Vehicle check WP-S-09 VS-SQ-20. New in v0.6 |

Note on FSR-02.02: the detection of input loss lies in the QM stack. At ASIL B this is not acceptable on its own. The ASIL B argument for SG-02 rests on FSR-01.07 (envelope removes actuation on stale commands) + FSR-02.05 (independent acoustic warning), both on E-03, with tighter timing (§8). FSR-02.02/02.03 on E-01 are QM measures that give the earlier, better-explained warning in the common case.

### 5.3 SG-03 Unintended acceleration (ASIL C ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-03.01 | The envelope shall limit the commanded acceleration to an upper bound derived from controllability for the reference vehicle. | C | E-03 | A, T-SIL, T-VEH | Implemented without rationale: +2.0 m/s² (`modes/toyota.h:208`); `RAISED_ACCEL_LIMIT` not validated for Corolla (`opendbc_repo/opendbc/car/toyota/interface.py:117-118`) (GAP-04) |
| FSR-03.02 | The envelope shall allow only the inactive acceleration value while longitudinal authority is not granted or while the driver presses the accelerator. | C | E-03 | T-SIL | Implemented (`longitudinal.h:3-12`) |
| FSR-03.03 | The envelope shall limit the rate of increase of commanded acceleration (jerk). | C | E-03 | T-SIL | Not implemented (GAP-04) |
| FSR-03.04 | FSR-01.05…01.12 apply to the longitudinal path (shared mechanisms; see trace §9). | C | E-03 | as referenced | as referenced |
| FSR-03.05 | On a detected fault affecting longitudinal control, the item shall stop requesting positive acceleration and request ACC cancel from the PCM. | C | E-03 (inactive value), E-01 (cancel) | T-SIL, T-VEH | Partial: inactive value enforced; cancel bit set by host (`opendbc_repo/opendbc/car/toyota/carcontroller.py:253-254`) |
| FSR-03.06 | The PCM shall bound ACC acceleration requests to its own envelope and honour the cancel request. (External measure, AOU-05R) | — (ext.) | EXT-PCM | T-VEH | Unverified (GAP-05) |

### 5.4 SG-04 Excessive deceleration (ASIL B ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-04.01 | The envelope shall limit the commanded deceleration to a bound derived from following-traffic controllability. | B | E-03 | A, T-SIL | Implemented without rationale: −3.5 m/s² (`modes/toyota.h:209`) (GAP-04) |
| FSR-04.02 | The envelope shall limit the onset rate of commanded deceleration (negative jerk). | B | E-03 | T-SIL | Not implemented (GAP-04) |
| FSR-04.03 | The transition to the longitudinal safe state shall not create a deceleration step larger than the jerk bound of FSR-04.02. | B | E-01, E-03 | A, T-VEH | Not specified; depends on PCM behaviour on inactive value (AOU-05R) |
| FSR-04.04 | Driver accelerator input shall override commanded deceleration. | B | E-03, EXT-PCM | T-SIL, T-VEH | Implemented in envelope (`longitudinal.h:3-5`); vehicle behaviour unverified |
| FSR-04.05 | Deceleration that the item initiates for a reason other than following traffic shall be announced by a visual and acoustic alert, ahead of its onset for the driver-monitoring no-response and at the latest at its onset for a fault soft disable (DQ-407 A: that slow-down is mild, and holding it back keeps the fault active), and shall stay within the bounds of FSR-04.01/04.02. | B | E-01 (alert), E-03 (bounds) | T-SIL, T-VEH | Partial: the DM no-response deceleration is announced 5 s ahead by a countdown in the terminal alert, and its own alert sounds through the stop (TSR-624); the fault soft-disable deceleration starts with its alert, as the requirement allows (DQ-407 A); bounds as FSR-04.01, the host ramp is ≤ 4.5 m/s³, the envelope jerk check is still missing (GAP-04). New in v0.2 (HE-04.3): DM is a source of H-04, and the deceleration path is bounded by the envelope, so DM itself stays QM (§7) |
| FSR-04.06 | Forward collision warnings shall be raised only from valid, fresh inputs, and the false-warning rate in the ODD shall be bounded so that driver reflex braking with a close follower is not a credible consequence. | A | E-01 | T-SIL, validation (WP-V-02) | Partial: FCW from model hard-brake prediction or planner (`selfdrive/selfdrived/selfdrived.py:488-493`); no false-rate target. **ASIL A on a QM element (E-01):** decided 2026-10-14, DQ-052 A: SOTIF validation shows that a false FCW is not dangerous, then HE-04.5 is re-rated (OI-9); ASIL A applies until then. New in v0.2 (HE-04.5) |

### 5.5 SG-05 Release on driver action (ASIL B ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-05.01 | The envelope shall revoke all actuation authority on a driver brake press (rising edge, or pressed while moving) within the SG-05 FTTI. | B | E-03 | T-SIL, T-VEH | Implemented (`safety.h:354-356`); brake message `0x226` has no checksum or counter (GAP-01) |
| FSR-05.02 | The envelope shall revoke all actuation authority when the PCM reports cruise inactive (cancel, main switch off). | B | E-03 | T-SIL, T-VEH | Implemented (`safety.h:520-521`) |
| FSR-05.03 | The envelope shall detect driver steering override (driver torque above a threshold) and reduce the LKA torque toward zero at a bounded rate so it does not oppose the driver, for as long as the override lasts; the item shall show the driver that the override was noticed. (Decided 2026-10-14, DQ-053: back off on override and show a cue.) | B | E-03, E-01/HMI (cue) | T-SIL, T-VEH | Not in envelope: host-only 500 raw check (`opendbc_repo/opendbc/car/toyota/carcontroller.py:33, 83`) (GAP-02); no override cue on the LKA path |
| FSR-05.04 | The envelope shall block positive acceleration while the accelerator is pressed. | B | E-03 | T-SIL | Implemented (`longitudinal.h:3-5`) |
| FSR-05.05 | The engagement state that the envelope enforces shall equal the PCM cruise state, so that the vehicle's own cruise indicator gives the driver an indication of engagement independent of the item's HMI. | C | E-03, EXT-CLU | A, T-VEH | Implemented by FSR-01.05 design; independence of the cluster indication to be confirmed by test |
| FSR-05.06 | If PCM cruise is active while the item is not engaged (or the reverse) for longer than a bounded time, the item shall warn the driver and request cancel. | C | E-01, E-03 | T-SIL | Implemented, not verified on the vehicle: `cruiseMismatch` after 1 s (`CRUISE_MISMATCH_TIME`, `selfdrive/selfdrived/selfdrived.py:57, 464-468`) with a repeating prompt (`events.py:464-470`); `controlsd` keeps requesting the cancel (TSR-308, LionDriver #51; GAP-19 closed in code). Before #51: after 6 s, no reaction |
| FSR-05.07 | Driver brake input shall produce braking regardless of ACC commands. (External measure, AOU-03R) | — (ext.) | EXT-PCM | T-VEH | Unverified |

### 5.6 SG-06 Longitudinal loss without warning (ASIL C)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-06.01 | The item shall detect loss or staleness of the longitudinal plan, lead information (radar/vision) and model output while engaged. | C | E-01 (QM), E-03 backstop via FSR-01.07 | T-SIL, FI | Partial: `commIssue`, `radarFault`, `processNotRunning` (`selfdrived.py:390-437`); masking during big-model settling (GAP-17); controlsd no freshness check (GAP-16) |
| FSR-06.02 | On detected loss, the item shall give a take-over request within 1 s and cancel ACC so that control returns to the driver; it shall not hold a stale acceleration command. | C | E-01, E-03 | T-SIL, T-VEH | Partial: soft disable with force decel (`controlsd.py:204-205`, `selfdrive/controls/lib/longitudinal_planner.py:84-85`); stale inputs used for up to ≈3.5 s (GAP-16) |
| FSR-06.03 | The item shall detect that the PCM does not execute ACC (ACC fault, cruise fault) and warn the driver. | C | E-01 | T-SIL | Implemented: `accFaulted` IMMEDIATE_DISABLE (`events.py:908`) |
| FSR-06.04 | Non-finite or out-of-range actuator commands shall be treated as faults with a fault reaction, not silently replaced. | C | E-01, E-03 | T-SIL | Not met: silently clamped to 0 (`controlsd.py:140-147`) (GAP-19) |
| FSR-06.05 | FSR-02.05 (independent acoustic warning on SoC loss) and FSR-02.06…02.09 (DM) also serve SG-06. | as ref. | as ref. | as ref. | as ref. |

### 5.7 SG-07 Stock PCS preservation (ASIL B)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-07.01 | The item shall forward all camera-side messages to the car side unchanged, except the defined set of intercepted control messages. | B | E-03 | T-SIL, T-HIL | Implemented: static block list (`safety.h:270-281`) |
| FSR-07.02 | The item shall not originate any message that the stock PCS function uses (e.g. PRE_COLLISION `0x344`, PCS_HUD `0x411`, AEB `0x283` with content) in the reference configuration. | B | E-03 | R, T-SIL | **Not met:** the openpilot-longitudinal TX whitelist allows the SoC to send `0x344` and `0x411` on bus 0 with no content check; only `0x283` is content-checked (`modes/toyota.h:19-28, 251-257`). The reference configuration host does not send them (`carcontroller.py:294-295` only with `DISABLE_RADAR`), but a QM fault could. (GAP-42) |
| FSR-07.03 | On safety-MCU fault, loss of device power, or harness fault, the relay shall return to the stock camera-to-vehicle connection. | B | E-05, E-03 | A, T-HIL | Partial: SILENT/NO_OUTPUT release relay (`panda/board/main.c:45-54`); de-energised relay state and power-loss behaviour not confirmed (OI-6) |
| FSR-07.04 | openpilot longitudinal commands shall not prevent PCS braking from taking priority in the PCM. (External measure, AOU-04R) | — (ext.) | EXT-PCM | T-VEH | Unverified |
| FSR-07.05 | The item shall inform the driver when the stock system reports an AEB or FCW event. | QM | E-01 | T-SIL | Implemented: `stockAeb`, `stockFcw` (`selfdrive/car/car_events.py:120-123`, `events.py:480`) |
| FSR-07.06 | If the harness cannot return to the stock camera-to-vehicle connection (switch or relay stuck in intercept, detected by state readback), the item shall inhibit all actuation, warn the driver that stock PCS/AEB is unavailable, and refuse engagement until the harness is repaired. (Accepted 2026-10-14 as the degraded state, DQ-064; applies once readback exists.) | B | E-03 (detection), E-05 (readback), E-01/HMI (warning) | T-HIL, FI | Not implemented: the harness box has no state feedback (RR-2026-010: two analog switches with a pull-down default); readback depends on the harness choice (DQ-209, queued). New in v0.6 |
| FSR-07.07 | While the stock system reports an AEB event, the item shall request zero acceleration from the PCM (no added drive), so that stock AEB braking does not depend on PCM arbitration alone. FSR-07.04 and its AOU-04R test still apply. (Decided 2026-10-18, DQ-300 A; System FMEA SFM-036, SFM-ACT-020; FTA MCS-07.10.) | QM (no ASIL claim; FSR-07.04 stays the measure) | E-01 | T-SIL, T-VEH | Implemented and unit-tested, not verified on the vehicle: the host request and the `0x343` command are ≤ 0 m/s² from the first frame of a stock AEB event, braking requests pass (`c045874` #292, opendbc `e233362` #311; TSR-713). Open: AOU-04R vehicle test. New in v0.12 |

### 5.8 SG-08 Driver not supervising or not responding (ASIL A)

SG-08 is new in HARA v0.4 (DQ-205). It is served by the DM requirements FSR-02.06…02.09 of §5.2, which carry ASIL A since version 0.8 (§7), and by the timing requirement below.

| ID | Requirement | ASIL | Alloc | Verif | Impl |
|---|---|---|---|---|---|
| FSR-08.01 | While engaged, the item shall give the first driver alert within 6 s of the loss of attention, measured end to end from the driver's change of state to the alert (including camera frame time, DM model latency and policy timers), and shall reach the no-response reaction of FSR-02.09 within the time set in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md). | A | E-01/DM, E-01/HMI | T-SIL, T-VEH | Partial: first vision alert at 5 s of distraction, wheel-touch at 5 s (`selfdrive/monitoring/policy.py:31-36`); latency not counted, end-to-end time not measured (WP-C-08 OI-2). New in v0.8 |

## 6. Safe states, transitions and emergency operation

| State | Definition | Entered by | Exit |
|---|---|---|---|
| SS-L (lateral safe) | `0x2E4` torque 0, steer request cleared | Any lateral fault, driver brake/cancel, authority revoked | New valid engagement (PCM rising edge) |
| SS-G (longitudinal safe) | `0x343` inactive value; ACC cancel requested | Any longitudinal fault, driver brake/cancel | New valid engagement |
| SS-S (envelope silent) | SILENT/NO_OUTPUT: no TX, relay released (stock camera path) | Heartbeat loss, MCU fault, unknown mode (`panda/board/main.c:33-54, 193-213`) | Restart / re-initialisation |

- **Emergency operation: none.** The item is fail-silent. On any fault it hands the driving task back to the driver with a warning. No minimal-risk manoeuvre is performed, apart from the DM no-response reaction (FSR-02.09), which is a misuse measure rather than a fault reaction; since HARA v0.4 it is the safe state of SG-08 (ASIL A), and its form is decided (DQ-365, A): keep the lane, decelerate to a standstill, then stay stopped and held with re-engagement locked out until the driver responds. Rationale: a supervised Level 2 system with a driver in the loop; the safe states above are reachable within one CAN frame and are controllable by an attentive driver (to be confirmed in WP-C-08 §8 tests, esp. torque removal in a curve, HE-02.1).
- **Transition rule:** a fault that makes the command untrusted (envelope fault, corrupted or stale command) → immediate SS-L/SS-G. A fault where the command is still trustworthy but the function will soon be unavailable (e.g. thermal, low disk) → warning first, then ramp to SS-L/SS-G (soft disable). The present soft disable does not make this distinction (GAP-16); FM-03 in [WP-C-07](WP-C-07-sotif-functional-modifications.md) proposes it.
- **Warning on every fault-induced transition** (FSR-02.03, FSR-06.02), with an SoC-independent fallback (FSR-02.05).

## 7. Driver monitoring integrity attributes (HARA §6.1 obs. 3)

The HARA asks the FSC to give DM an ASIL attribute inherited from SG-02/SG-06, or to justify why not.

**Proposal: DM is not assigned an ASIL from SG-02 or SG-06. For those goals its requirements (FSR-02.06…02.09) are QM, managed under ISO 21448 as measures against foreseeable misuse ([WP-C-05](WP-C-05-sotif-hazard-identification.md), [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md)), with integrity-supporting attributes listed below.**

Justification:

1. ISO 26262-3 rates controllability for a typical driver, under the assumption that the driver is in the state the item's intended use requires (AOU-06). The C2 ratings for HE-02.x and HE-06.x assume a supervising driver, not one kept attentive by DM. DM addresses misuse (inattention), which is in ISO 21448 scope.
2. A DM failure has no vehicle-level effect on its own (HARA §4). It becomes relevant only when combined with driver inattention **and** a separate hazard trigger — a multiple-point situation.
3. The DM chain is an ML model plus Python on the QM SoC. An ASIL B allocation could not be met without an independent ASIL B monitor of driver state, which does not exist in the item.

Integrity-supporting attributes (QM, but required):

| Attribute | Requirement | Covered by |
|---|---|---|
| Latent-fault detection | DM must detect loss of its own input or credibility and fall back to a stricter policy | FSR-02.07 |
| No bypass | DM cannot be disabled or demoed while engagement is possible | FSR-02.08 |
| Liveness gating | Engagement is not possible, and an engaged system soft-disables, when DM output is missing | Implemented: `dmonitoringd` invalid → `commIssue` (onboard review; `selfdrive/monitoring/dmonitoringd.py:25-33`) |
| Performance | Detection performance is validated against misuse scenarios | WP-C-08 §8, [WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md) |

**HARA v0.2 (HE-04.3):** DM is also a *source* of unintended deceleration (forced deceleration on an attentive driver). That path is covered by FSR-04.05 and the envelope bounds FSR-04.01/04.02 on E-03, which apply whatever requests the deceleration. So the conclusion above holds and the DM chain itself stays QM.

**2026-10-14, register DQ-205 (answered, option A):** the unresponsive driver becomes its own hazard H-09 with an ASIL A goal. WP-C-03 v0.4 adds it as SG-08. Since version 0.8, FSR-02.06…02.09 trace to SG-08 and carry ASIL A, and FSR-08.01 sets the SG-08 alert time. The QM SoC cannot carry ASIL A today (OI-11, as FSR-04.06 in OI-9). The reaction at zero awareness (FSR-02.09, TSR-633) was decided on 2026-10-16 (DQ-365, A; DQ-340 merged into it): decided 2026-10-16, DQ-365 A: steering stays on while the vehicle decelerates in lane to a standstill within the envelope limits with the alert sounding; the vehicle then stays stopped and held, and the item cannot drive off again: re-engagement and resumption are locked out until the driver responds.

**HARA v0.4, §6.1 observation 3** asks whether SG-02/SG-06, now ASIL C, put a further attribute on DM. They do not: the C ratings come from the curve case at the bound (C3, HE-02.1, HE-07.1) and from the E4 exposure of OS-07 (HE-06.1, HE-07.3), both rated for a supervising driver, so justification 1 above still holds. DM therefore carries ASIL A, from SG-08 only. If the assessor disagrees (OI-3), the re-rating below applies at ASIL C or D, not B.

**Condition:** the I3 confirmation review must agree that the HARA C2 ratings do not depend on DM. If the assessor disagrees, the alternative is to re-rate HE-02.1/HE-06.1 under the assumption of a distracted driver (likely C3 → ASIL C) and then decide between an ASIL-capable DM supervisor and an ODD/authority restriction. This is OI-3.

## 8. FTTI allocation (preliminary)

FTTIs are preliminary (HARA OI-3). Detailed timing belongs in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md). The allocation below sets the budget the TSRs must meet.

| SG | FTTI (prelim.) | Detection budget | Reaction budget | Current behaviour | Gap |
|---|---|---|---|---|---|
| SG-01 (continuous limiting) | ≤ 0.5 s | 0 (per-frame check) | ≤ 1 frame (10 ms) | Per-frame limits act within one frame | — |
| SG-01 (RX loss/corruption) | ≤ 0.5 s | ≤ 0.3 s | ≤ 0.1 s | Baseline: RX timeout 1–2 s. Since opendbc `de80b63` / panda `171fcdf`: 5 nominal periods checked at 100 Hz, ≤ 0.162 s (`0x262` ≈ 0.21 s); not verified on hardware (WP-S-04 T-01, M-04) | GAP-06 (partly closed), GAP-01 |
| SG-01 (SoC command loss) | ≤ 0.5 s | ≤ 0.3 s | ≤ 0.1 s | Baseline: 3 s mismatch / 5 s loss (`main.c:182-213`). Reference build: heartbeat absent > 0.3 s revokes authority (TSR-407, panda `c2e5d93`); `0x2E4` not arriving for > 50 ms (`0x343` > 100 ms) revokes it (TSR-408, opendbc `273f44e`); not verified on hardware (WP-S-04 T-06a, T-34, M-05) | GAP-06 (partly closed) |
| SG-01 (MCU execution fault) | ≤ 0.5 s | ≤ 0.1 s (HW watchdog; set by SG-07) | ≤ 0.1 s | No HW watchdog at the baseline; 90 ms IWDG in all builds since panda `3859fa8`, accepted once the independent reviewer has checked it and the LSI tolerance (DQ-114) | GAP-07 |
| SG-02, SG-06 (loss without warning) | ≤ 1 s to warning | ≤ 0.5 s | ≤ 0.5 s (warning) | Soft disable warns at once, but actuates on stale inputs up to ≈3.5 s | GAP-16 |
| SG-03, SG-04 | ≤ 1 s | ≤ 0.5 s | ≤ 0.3 s | as SG-01 detection | GAP-06 |
| SG-05 (driver brake/cancel) | ≤ 0.2 s | ≤ 1 brake message period (25 ms at 40 Hz) | ≤ 1 frame | Envelope revokes authority on the next RX frame, but a rejected `0x2E4` frame is dropped rather than replaced by zero torque, so the EPS may keep acting until its own timeout (TSR-109 in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md)) | GAP-46; verify on vehicle (T-VEH) |
| SG-05 (steering override) | ≤ 0.2 s | — | — | Not in envelope | GAP-02 |
| SG-07 (forwarding loss) | ≤ 0.2 s (preliminary, WP-S-04 §3.6; working budget accepted, DQ-062) | ≤ 0.1 s | ≤ 0.1 s (relay release) | No supervision of forwarding while the MCU runs (TSR-711 not implemented). An MCU hang is caught by the 90 ms IWDG in all builds since panda `3859fa8` (reset, relay released; WP-S-04 T-09a); not verified on hardware | GAP-43, GAP-49 (`0xe7` stops forwarding); TSR-711 |
| SG-07 (content) | per frame | 0 | — | Static forwarding; PCS IDs in the TX whitelist | GAP-42 (FSR-07.02) |
| SG-08 (driver not supervising) | ≤ 6 s from loss of attention to the first alert | ≤ 5 s (DM policy, vision) | ≤ 1 s (first alert) | First vision alert at 5 s of distraction (`selfdrive/monitoring/policy.py:31-36`), wheel-touch mode at 5 s; DM frame and model latency not counted; end-to-end time not measured (WP-C-08 OI-2); the item stays engaged after the stop and the lockout starts only after a later disengagement, so nothing holds the vehicle or prevents it driving off again (FSR-02.09, DQ-365 A) | GAP-21; time to the no-response reaction preliminary in WP-S-04 §3.8.4 |

Note on SG-02 in curves: [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) §3.2 estimates ≈ 0.7 s to a 0.6 m lateral drift at the ODD curve bound, which is shorter than driver reaction. The SG-02 budget above (≤ 0.5 s detection + ≤ 0.5 s to warning) is sufficient on straight roads and gentle curves but not alone at the ODD curve bound; SG-02 there relies on immediate warning and on torque being ramped rather than cut (FSR-02.04). Resolution (re-rate C of HE-02.1 or tighten R_ODD) is open in WP-S-04 OI-2 and [WP-C-03](WP-C-03-hara.md) OI-7.

### FTTI scenes: lateral

Sheets: **Lateral** · [Longitudinal](#ftti-scenes-longitudinal) · [Stock PCS and driver](#ftti-scenes-stock-pcs-and-driver)

![Figure 8-1: one card each for SG-01, SG-02 and SG-05, each with the §8 FTTI budget against today, a road scene of what the safety mechanism must prevent, a timeline from fault to safe state and warning, what the mechanism must do and does today, the elements that carry the goal's FSRs and how many are met](fsc/figures/fig-c04-8-1-ftti-scenes-lateral.svg)

*Figure 8-1.* FTTI scene cards for the lateral goals. Generated by [`fsc/fsc_scenes.py`](fsc/fsc_scenes.py) through `fsc/fsc_figures.py`, from §3, §5, §8 and §9: the budget bar and the "needed by" marks are the §8 row named on the card, the element tiles the §5 Alloc of the FSRs that the §9 trace links to the goal, the status bar the §5 Impl column. A QM element that carries an ASIL FSR is outlined in red. The scenes and the times shown for today are schematic, not measurements.

### FTTI scenes: longitudinal

Sheets: [Lateral](#ftti-scenes-lateral) · **Longitudinal** · [Stock PCS and driver](#ftti-scenes-stock-pcs-and-driver)

![Figure 8-2: one card each for SG-03, SG-04 and SG-06, in the same layout as Figure 8-1](fsc/figures/fig-c04-8-2-ftti-scenes-longitudinal.svg)

*Figure 8-2.* FTTI scene cards for the longitudinal goals, in the layout of Figure 8-1.

### FTTI scenes: stock PCS and driver

Sheets: [Lateral](#ftti-scenes-lateral) · [Longitudinal](#ftti-scenes-longitudinal) · **Stock PCS and driver**

![Figure 8-3: one card each for SG-07 and SG-08, in the same layout as Figure 8-1](fsc/figures/fig-c04-8-3-ftti-scenes-pcs-driver.svg)

*Figure 8-3.* FTTI scene cards for stock PCS preservation and the driver who is not supervising, in the layout of Figure 8-1.

## 9. FSR → SG trace

Each goal's FSRs with the TSRs that refine them are drawn as one tree per goal in the generated [requirements view](../03-system/requirements/README.md) of WP-S-02.

| FSR | SG-01 | SG-02 | SG-03 | SG-04 | SG-05 | SG-06 | SG-07 | SG-08 |
|---|---|---|---|---|---|---|---|---|
| FSR-01.01–01.04 | ● | | | | | | | |
| FSR-01.05 | ● | | ● | ● | ● | | | |
| FSR-01.06 | ● | | ● | ● | ● | | | |
| FSR-01.07 | ● | ● | ● | ● | | ● | | |
| FSR-01.08 | ● | | ● | ● | | | | |
| FSR-01.09 | ● | ● | ● | ● | ● | ● | ● | |
| FSR-01.10 | ● | | ● | ● | ● | | ● | |
| FSR-01.11 | ● | | ● | | | | ● | |
| FSR-01.12 | ● | | | | | | | |
| FSR-01.13 | ● | | | | ● | | | |
| FSR-01.14 | ● | | | | | | | |
| FSR-02.01–02.05 | | ● | | | | | | |
| FSR-02.06–02.08 | | ● | | | | ● | | ● |
| FSR-02.09 | | ● | | ● | | ● | | ● |
| FSR-02.10–02.11 | | ● | | | | ● | | |
| FSR-02.12 | | ● | | | | ● | | |
| FSR-03.01, 03.03–03.06 | | | ● | | | | | |
| FSR-03.02 | | | ● | ● | | | | |
| FSR-04.01–04.06 | | | | ● | | | | |
| FSR-05.01–05.04, 05.07 | | | | | ● | | | |
| FSR-05.05–05.06 | | ● | | | ● | ● | | |
| FSR-06.01–06.05 | | | | | | ● | | |
| FSR-07.01–07.07 | | | | | | | ● | |
| FSR-08.01 | | | | | | | | ● |

SG-08 (HARA v0.4, unresponsive driver, ASIL A) is served by the DM requirements FSR-02.06…02.09, which carry ASIL A since version 0.8 (§7), and by FSR-08.01.

Every SG has at least one FSR allocated to E-03 (or to an external measure plus E-03), except the warning part of SG-02/SG-06, which relies on FSR-01.07 + FSR-02.05 on E-03 as described in §5.2.

## 10. Allocation summary

| Element | FSRs | Highest ASIL |
|---|---|---|
| E-03 safety envelope | 01.01–01.12, 02.01 (detection), 02.04, 02.05, 02.10 (authority state), 03.01–03.05, 04.01–04.05, 05.01–05.06, 06.04, 07.01–07.03, 07.06 (detection) | C (decided, DQ-341: SG-02, SG-03, SG-06; SG-01 C until re-rated, §4.2) |
| E-05 harness/relay | 01.11, 07.03, 07.06 (readback) | C (SG-01, SG-03 via FSR-01.11) |
| E-01 SoC (QM) | 01.14, 02.02, 02.03, 02.06–02.12, 08.01, 05.03 (cue), 07.06 (warning), 03.05 (cancel), 04.05 (alert), 04.06, 05.06, 06.01–06.04, 07.05, 07.07 | QM (ASIL-relevant items backed by E-03); FSR-04.06 ASIL A until the DQ-052 re-rating evidence (OI-9); DM FSR-02.06…02.09 and 08.01 ASIL A open (OI-11) |
| HMI | 02.03, 02.05 (panda buzzer, via E-03) | QM / C for buzzer path |
| EXT-EPS | 01.13 | AoU |
| EXT-PCM | 03.06, 05.07, 07.04 | AoU |
| EXT-CLU | 05.05 | AoU |
| Driver | §11 AOU-06R, AOU-02R | AoU |

![Figure 10-1: the item boundary of WP-C-01 Figure 3-2 in the safety view: each element with the number of FSRs allocated to it, their highest ASIL and the safety goals they serve; the envelope E-03 carries 42 FSRs up to ASIL C, the QM SoC elements E-01, E-01/DM, E-01/HMI and E-02 are outlined red because they carry ASIL FSRs, and the EPS, PCM, cluster and driver are credited through assumptions of use](fsc/figures/fig-c04-10-1-safety-view.svg)

*Figure 10-1.* The item boundary of [WP-C-01](WP-C-01-item-definition.md) Figure 3-2, redrawn with this table on it. Each box counts the §5 FSRs whose Alloc column names the element, colours it by their highest ASIL and lists the goals they serve in §9; the element's own integrity is the §2 column. A red outline marks a QM element that carries ASIL FSRs: §10 backs those by E-03, or leaves them open (OI-9, OI-11). Generated by [`fsc/fsc_safety_view.py`](fsc/fsc_safety_view.py) through `fsc/fsc_figures.py` from §2, §5, §9 and §10.

## 11. Assumptions of use (refined)

| ID | Refines | Assumption | Needed by FSR | Verification | Status |
|---|---|---|---|---|---|
| AOU-01R | AOU-01 | The EPS limits LKA torque at the steering wheel to ≤ T_EPS (value to be measured) for any `0x2E4` request, and removes LKA torque within t_EPS (to be measured; code comment suggests ≈1.5–2 s) after `0x2E4` stops or the request bit clears | FSR-01.13 | Bench + vehicle characterization (closed course) | Unverified |
| AOU-02R | AOU-02 | A typical driver overpowers the envelope-bounded worst-case torque within the controllability criterion of WP-C-08 §7 (CA-01) | FSR-01.01, 05.03 | Controllability test (WP-C-08 §8) | Unverified |
| AOU-03R | AOU-03 | Brake pedal application produces braking regardless of `0x343` content, and the PCM drops ACC on brake | FSR-05.07 | Vehicle test | Unverified |
| AOU-04R | AOU-04 | PCS/AEB braking has priority over `0x343` requests in the PCM, and PCS works with the harness installed | FSR-07.04 | Message review + PCS target test | Unverified |
| AOU-05R | AOU-05 | The PCM clamps ACC requests to its own envelope and honours the cancel bit; the inactive value produces coasting without a deceleration step | FSR-03.06, 04.03 | Vehicle test with injected requests | Unverified |
| AOU-06R | AOU-06 | The driver supervises continuously, keeps hands near the wheel and is able to respond within the reaction times assumed in WP-C-08 §7 | All C2 ratings | WP-C-08 | Assumption |
| AOU-12 | WP-C-01 AOU-12 | The cluster cruise indicator is driven by PCM state and is not influenced by item TX messages other than `0x412` LKAS_HUD | FSR-05.05 | Vehicle test | Unverified |
| AOU-13 | WP-C-01 AOU-13 | The de-energised harness relay connects the forward camera to the vehicle CAN (stock path) | FSR-07.03 | Harness inspection / test (WP-H-02) | Unverified |
| AOU-17 | — (new; to be added to WP-C-01) | The EPS signals every drop of LKA assistance (LKA_STATE or an EPS fault state in `0x262`) and the PCM signals every non-execution of ACC requests (ACC or cruise fault state), so that neither stops acting on the item's requests without a fault the item can see (decided 2026-10-18, DQ-360 A) | FSR-02.01, 06.03 | Vehicle tests with forced faults (WP-V-07). If a test finds a silent drop, a response-versus-command check is added (TSR-626 (b), (c) extended to that case; DQ-360 option B) | Unverified |

## 12. Warning and degradation concept

### 12.1 Degradation levels

| Level | Name | Lateral | Longitudinal | Driver info | Trigger examples |
|---|---|---|---|---|---|
| L0 | Full function | Active | Active | Engaged indication (device + cluster cruise + LKAS HUD) | — |
| L1 | Override | Torque reduced toward zero while the driver steers against it (FSR-05.03, DQ-053) | Blocked while gas pressed | Override indication | Driver gas or steering (`events.py:728, 736`) |
| L2 | Take-over request, planned | Active with valid inputs, ramping down ≤ soft-disable time | Force decel to cruise 0 | Soft-disable alert, then immediate-disable form < 0.5 s | Non-critical faults (thermal, memory, calibration) |
| L3 | Immediate disengagement | SS-L | SS-G + cancel | Immediate-disable alert (visual + acoustic) | Untrusted command or input, envelope/RX fault, relay fault, CAN error |
| L4 | Envelope silent | SS-S | SS-S | Panda buzzer (SoC lost) | SoC heartbeat loss, MCU fault |
| L5 | Lockout | Not available | Not available | No-entry alert with remaining time | DM non-compliance (`policy.py:47-49`) |

There is no degraded "lateral-only" or "longitudinal-only" operating mode in the reference configuration.

![Figure 12-1: the degradation ladder: levels L0 full function, L1 override, L2 planned take-over request, L3 immediate disengagement, L4 envelope silent and L5 lockout, each with lateral and longitudinal behaviour, driver information and triggers, and the safe states SS-L, SS-G and SS-S of §6 with what they are, what enters them and what leaves them](fsc/figures/fig-c04-12-1-degradation-ladder.svg)

*Figure 12-1.* The table above as a ladder, with the safe states of §6 below it. Generated by [`fsc/fsc_degradation.py`](fsc/fsc_degradation.py) through `fsc/fsc_figures.py` from §6 and §12.1; it fails if a level names a safe state §6 does not define.

### 12.2 Warning requirements (summary)

- Every transition to L2/L3/L4 caused by a fault produces an acoustic and visual take-over request (FSR-02.03, 02.05, 06.02).
- Alert text must describe the actual fault (GAP-19: `canError` shows "Unknown Vehicle Variant", `events.py:928-936`). Alert design and timing are reviewed in [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) §4.
- `speedTooHigh` (≈149 km/h) warns without disengaging (`events.py:989-996`). This is an ODD exit, not a fault; handled in WP-C-02 §6 and FM-07 of WP-C-07.

## 13. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Closed 2026-10-14: the project lead chose option (c) + ASIL B hardening (DQ-007, §4). The strategic record in WP-M-01 / WP-M-07 is kept by the management work products | Maintainer | G1 |
| OI-2 | Derive the speed-dependent torque limit and confirm C1 by controllability tests; then request HARA re-rating of SG-01 | Safety engineer | G2 |
| OI-3 | I3 reviewer to confirm DM is not ASIL-attributed (§7) or trigger the alternative | Safety manager | G1 |
| OI-4 | Confirm FTTIs (WP-S-04) and update §8 budgets | Safety engineer | G2 |
| OI-5 | Closed: the FSR-07.02 finding (TX whitelist allows `0x344`/`0x411`) is registered as GAP-42 | Safety engineer | G1 |
| OI-6 | Confirm relay de-energised state and power-loss behaviour (AOU-13) | HW lead | G2 |
| OI-7 | Refine FSRs into TSR-1xx…7xx in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) and record FSR→TSR trace in `trace/` | Safety engineer | G2 |
| OI-8 | Closed: WP-C-03 v0.2 rates H-07 (HE-07.1…07.3, ASIL B) and assigns it to SG-02/SG-06. The FSRs for SG-02/SG-06 must cover the engagement indication and take-over alerts (WP-C-03 §6.1 obs. 5) | HARA owner | G1 |
| OI-9 | FSR-04.06 (false FCW) carries ASIL A on the QM SoC. **Route decided 2026-10-14 (DQ-052, A):** show with SOTIF validation data ([WP-V-02](../06-validation/WP-V-02-sotif-vv-strategy.md): the false-FCW rate per driving hour against its target, logged per SWSR-625, and the driver reactions to false FCWs in the planned test drives) that a false warning with a close follower does not lead to dangerous reflex braking; then WP-C-03 re-rates HE-04.5 and FSR-04.06, TSR-625 and SWSR-625 follow the new rating. Developing the trigger to ASIL A and moving the warning to the safety MCU were not chosen. Open until that evidence exists and the re-rating is done; ASIL A applies until then | Safety engineer | G2 |
| OI-10 | Implement TSR-621 (`controlsMismatch` within ≤ 0.5 s) and TSR-622/623 (HMI liveness, audible minimum) drafted in WP-S-02 v0.2 for FSR-02.10/02.11; TSR-624/625 cover FSR-04.05/04.06 | SW lead | G2 |
| OI-11 | The DM requirements FSR-02.06…02.09 and FSR-08.01 carry ASIL A (SG-08, HARA v0.4) on the QM SoC. Either develop the DM chain (camera input check, `dmonitoringmodeld`, `dmonitoringd`, policy) to ASIL A with freedom from interference on the SoC, add an ASIL A monitor of DM liveness and alert timing on the safety MCU, or show by SOTIF validation that the alert time is met (WP-C-08 OI-2). Interacts with the decided reaction (DQ-365, A: steering stays on, under ASIL A, until standstill, then the vehicle is held) and OI-3 | Safety engineer | G2 |

## 14. Completeness check (fsc-builder method)

The FSRs above were written by hand from the safety goals. Their completeness is checked with the fsc-builder method. Each safety goal is expanded into a fault tree, OR(input failure, process failure, output failure), over a block diagram of the item: 20 ASIL-relevant nodes plus 5 external nodes for context. That gives one basic event per (safety goal, node), 140 in all.

[`fsc/fsc_model.py`](fsc/fsc_model.py) records, for every basic event, the FSRs that address it, or why the node cannot violate that goal. The result is [`fsc/fsc-coverage.md`](fsc/fsc-coverage.md), and the generated workbook with the mapping in tab 09 is [`fsc/WP-C-04-fsc-completeness.xlsx`](fsc/WP-C-04-fsc-completeness.xlsx).

CI runs `fsc_model.py --check`. It fails if:

- a basic event has neither an FSR nor a reason;
- a cited FSR does not exist here;
- an FSR here is not cited by any basic event;
- the coverage table is stale.

The template FSR wording in the generated workbook (tab 05) is not the requirement set; the FSRs in §5 are.

The check found the following:

- **SoC reset and boot control of the MCU (node N13, GAP-38):** handled at TSR level (TSR-511) but not stated at FSR level. FSR-01.10 now includes it.
- **New FSRs for the new HARA v0.2 sources:** FSR-02.10 (envelope blocking while the SoC shows engaged, HE-02.4), FSR-02.11 (HMI path failure, H-07), FSR-04.05 (item-initiated deceleration, HE-04.3) and FSR-04.06 (false FCW, HE-04.5).
- **Trace extensions:**
  - FSR-03.02 now also serves SG-04 (no braking without authority, HE-04.4).
  - FSR-05.05/05.06 now also serve SG-06 (longitudinal mode confusion, HE-07.3).
  - FSR-02.09 now also serves SG-04 (DM forced deceleration).
- **Loss of the 12 V supply (node N08):** the item cannot warn. The driver is informed only by the cluster cruise indicator (FSR-05.05) and the EPS ending LKA torque (FSR-01.13), which rests on AOU-01R and AOU-12.
- **No ASIL decomposition is proposed.** No two nodes are redundant peers with disjoint shared resources. The SoC and the MCU share the device supply and PCB, and the envelope takes the SoC command stream as an input. This matches §4: the SoC is QM and the envelope is the safety mechanism, with freedom from interference argued in [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md).
