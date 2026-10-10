# WP-C-04 Functional Safety Concept

| Field | Value |
|---|---|
| Work product | WP-C-04 Functional safety concept (FSRs, allocation, AoUs) |
| Standard reference | ISO 26262-3:2018 §7; ISO 26262-9:2018 §5 (ASIL decomposition, by reference); ASPICE 4.0 SYS.2 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Up to ASIL C (SG-01); ASIL B for SG-02…SG-07 |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); input to G1 confirmation review (I3) per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and inputs

This document derives functional safety requirements (FSRs) from the safety goals SG-01…SG-07 of the [HARA (WP-C-03)](WP-C-03-hara.md) and allocates them to the architectural elements of the [item definition (WP-C-01)](WP-C-01-item-definition.md). It also records the envelope strategy decision that the HARA left open (WP-C-03 §6.1, OI-4), the integrity attributes of driver monitoring (WP-C-03 §6.1 obs. 3), and the refined assumptions of use (AoU) on the vehicle and driver.

Inputs:

- [WP-C-01](WP-C-01-item-definition.md): functions F-01…F-09, elements E-01…E-06, interfaces IF-01…IF-09, AOU-01…AOU-11.
- [WP-C-03](WP-C-03-hara.md): hazards H-01…H-06, H-08; SG-01…SG-07 with ASIL, safe states and preliminary FTTIs.
- [WP-C-02](WP-C-02-odd-and-intended-functionality.md): ODD and intended functionality.
- [Gap assessment](../00-assessment/gap-assessment.md): GAP-01…GAP-37.
- [WP-M-01 §4](../01-management/WP-M-01-assurance-strategy.md#4-safety-architecture-argument-the-central-strategy): safety envelope pattern.

The ASILs in this document are those proposed in the HARA. The HARA is not yet confirmed (I3). If the confirmation review changes a rating, the FSR ASILs here change with it.

## 2. Architectural elements used for allocation

| Element | Description | Integrity it can carry today | Notes |
|---|---|---|---|
| E-03 | Safety envelope: opendbc safety (Toyota mode) and the panda firmware paths it relies on, on the STM32H7 | Target ASIL B after hardening (§4.2); SG-01 FSRs carry ASIL C until C1 is shown | The only path to the actuators. Single channel (GAP-11) |
| E-01 | Application SoC software: openpilot processes (selfdrived, controlsd, plannerd, card, pandad, ...) | QM | Python, no partitioning, no WCET (GAP-23) |
| E-02 | ML models: driving model, DM model | QM (SOTIF / PAS 8800 managed) | No uncertainty gating (GAP-22) |
| E-01/DM | Driver monitoring chain: driver camera → dmonitoringmodeld → dmonitoringd → selfdrived | QM (see §7) | Source validity hard-coded (GAP-21) |
| E-04 | Device hardware hosting E-01 and E-03: SoC, panda MCU, shared power supply, clocks, CAN transceivers (WP-C-01 E-04) | Shared platform; integrity of E-03 depends on it | The QM SoC controls the panda MCU reset and boot lines (`STM_RST_N`/`STM_BOOT0`) and can force the ROM bootloader or reflash the MCU (GAP-38); shared supply and PCB (dependent-failure analysis, [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md)) |
| E-04/HMI | Device display and speaker (soundd/ui), panda buzzer ("siren"), cluster LKAS HUD (`0x412`) | QM, except the panda siren which is driven by E-03 | |
| E-05 | Harness with intercept relay | Target ASIL B (SG-07) | Relay default state to be confirmed (OI-6) |
| EXT-EPS | Toyota EPS (external measure) | Unknown; credited through AOU-01/02 only | No supplier evidence |
| EXT-PCM | Toyota ECM/PCM and brake actuator (external measure) | Unknown; credited through AOU-03/05 only | |
| EXT-CLU | Toyota instrument cluster cruise indicator (driven by the PCM) | Unknown; used as an independent mode indication | |
| DRV | Driver | Not an E/E element; assumptions only (AOU-06, AOU-02) | |

## 3. Safety goals (summary from WP-C-03)

| SG | Statement (short) | ASIL | Safe state | Preliminary FTTI |
|---|---|---|---|---|
| SG-01 | No uncontrollable lateral motion, no steering actuation while not engaged | C ⚠ (D if AOU-01/02 fail) | LKA torque 0, steer request cleared | ≤ 0.5 s |
| SG-02 | No loss/degradation of lateral control without adequate take-over warning | B | Warning + torque ramp-down | ≤ 1 s to warning |
| SG-03 | No unintended acceleration | B ⚠ | Accel ≤ 0; ACC cancelled | ≤ 1 s |
| SG-04 | No deceleration beyond what following traffic and driver can control | B ⚠ | Inactive (no ACC command) with bounded jerk | ≤ 1 s |
| SG-05 | Release on driver brake, cancel, steering override | B ⚠ | Disengaged | ≤ 0.2 s |
| SG-06 | No loss of longitudinal deceleration without take-over warning | B | Warning; ACC cancelled | ≤ 1 s |
| SG-07 | No suppression, delay or alteration of stock PCS/AEB | B | Camera PCS messages forwarded; relay released if forwarding cannot be guaranteed | Continuous |

## 4. Envelope strategy decision (HARA §6.1, OI-4)

SG-01 at ASIL C (D if the EPS assumptions fail) drives the integrity of the envelope. The HARA lists three options. This section evaluates them and recommends one. **The decision belongs to the maintainer (acting safety manager); this section is a recommendation.**

### 4.1 Evaluation

| Criterion | (a) Harden the envelope to ASIL C | (b) ASIL decomposition C(C) = B(C) envelope + A(C) EPS | (c) Reduce actuation authority so controllability C1 can be shown, lowering SG-01 to ASIL B |
|---|---|---|---|
| What it needs | ASIL C hardware metrics (SPFM/LFM/PMHF targets) on a COTS single-channel MCU; ASIL C software process (MC/DC, GAP-13); E2E with counters on all RX (GAP-01); IWDG and fault reaction (GAP-07/08); DFA of shared SoC/MCU power and clock | Two **independent** elements that each satisfy the safety goal on their own; DFA showing independence; evidence that the EPS implements an ASIL A(C) torque limitation | Vehicle characterization of the EPS torque authority (AOU-01/02); a physically derived, speed-dependent torque limit in the envelope; controllability tests (WP-C-08 §8) showing ≥ 99 % of drivers control envelope-bounded worst-case actuation |
| Feasibility for an aftermarket retrofit | Low to medium. No supplier FMEDA data for the device; the shared PCB/power with the QM SoC makes the ASIL C hardware metrics hard to reach (WP-M-01 §9) | Low. Toyota provides no evidence of the EPS internal limitation, its ASIL or its independence. ISO 26262-9 §5 requires that independence be shown, not assumed. An external element cannot receive a decomposed ASIL without evidence of its development | Medium to high. Needs vehicle testing, which is needed anyway for AOU-01/02 (HARA OI-1). Matches the ISO 11270 reasoning in `docs/SAFETY.md` |
| Effect on availability | None | None | Less steering authority: some curves inside today's operating range can no longer be followed. Narrows the ODD (WP-C-02 §4.2) |
| Residual dependence on unverified AoUs | Low for SG-01 (the envelope alone carries the goal) | High (EPS) | Medium (EPS limit still bounds the worst case; driver controllability is measured, not assumed) |
| Effort | Highest | Medium, but blocked on evidence that LionDriver cannot obtain | Medium |

### 4.2 Recommendation

**Recommended: option (c) reduced authority, combined with hardening of the envelope to ASIL B.** Option (b) is kept as a documented fallback but is not recommended as the primary route.

Rationale:

1. Option (c) attacks the risk at its source. The worst-case consequence of any E/E fault on the lateral path is bounded by what the envelope lets through. If that bound is chosen so that a typical driver controls it (C1), HE-01.1/01.2/01.4 become S3 E4 C1 = ASIL B, the same level as SG-02…SG-07. The whole envelope then has one target ASIL (B).
2. ASIL B hardening is needed under every option (IWDG, fault → safe state, safety-mode lock, E2E counters, FTTI-consistent timeouts). Option (c) does not add hardware-metric targets that the COTS device is unlikely to meet.
3. Option (b) requires evidence about the Toyota EPS that is not available. LionDriver cannot show the EPS was developed to ASIL A or that it is independent of the item (it consumes the item's command). A decomposition argument built on it would not survive an I3 review.
4. Option (a) remains possible later if hardware metrics turn out better than expected. Nothing in (c) prevents it.

Conditions attached to the recommendation:

- **Until the controllability evidence exists, SG-01 stays ASIL C** and the SG-01 FSRs below carry ASIL C. They are expected to drop to ASIL B once the HARA is re-rated on evidence. The HARA owner re-rates; this document does not.
- The reduced limit must be derived physically (torque at the wheel → lateral acceleration and lateral deviation over the FTTI, per speed), not tuned. That closes GAP-04 for the lateral path.
- The controller (E-01) limits must sit below the envelope limits with margin, so that normal operation never runs at the enforcement boundary (gap assessment §3.1 notes zero margin today).

### 4.3 Fallback: ASIL decomposition (if C1 cannot be shown)

If vehicle tests show that C1 cannot be reached at a torque level that keeps the function useful, the fallback is decomposition of SG-01:

- **ASIL C(C) = ASIL B(C) on the envelope (E-03) + ASIL A(C) on a second, independent limiting element.**
- The second element should be inside LionDriver's control, not the Toyota EPS: for example an independent hardware torque/request monitor on the harness side, or a second MCU checking `0x2E4` against measured EPS torque and steering state, able to open the relay.
- Independence requirements (to be analysed in [WP-A-01](../08-analyses/WP-A-01-asil-decomposition.md) and [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md)): separate power supply path or supervised supply, separate clock, separate CAN receive path, no shared software, no configuration of one element by the other, and a de-energise-to-safe actuation (relay open = stock path).
- Crediting the EPS as the A(C) element is **not recommended** for the reasons in §4.1.

## 5. Functional safety requirements

Attributes: ASIL as currently derived; **Alloc** = allocation; **Verif** = verification method (A = analysis, R = review, T-SIL = software test, T-HIL = hardware-in-the-loop test, T-VEH = vehicle test, FI = fault injection). **Impl** = what the baseline code already does (file:line) or the GAP that blocks it. Paths for E-03 are under `opendbc_repo/opendbc/safety/` unless prefixed `panda/`. Paths for E-01 are under `openpilot/`. All statuses are `Proposed`.

### 5.1 SG-01 Lateral motion (ASIL C ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-01.01 | The envelope shall limit the commanded LKA torque magnitude to a speed-dependent bound derived from driver controllability (lateral acceleration and lateral deviation reached within the FTTI). | C | E-03 | A, T-SIL, T-VEH | Partial: fixed 1500 raw (`modes/toyota.h:173`); not speed-dependent, no physical rationale (GAP-04) |
| FSR-01.02 | The envelope shall limit the rate of change of the commanded LKA torque (rise, fall and real-time window) to bounds derived from controllability. | C | E-03 | A, T-SIL | Implemented without rationale: 15/25 raw per frame, 450 raw per 250 ms (`modes/toyota.h:174-177`, `lateral.h:49-57, 87-95`) (GAP-04) |
| FSR-01.03 | The envelope shall limit the commanded LKA torque to within a bounded difference of the measured EPS motor torque. | C | E-03 | T-SIL | Implemented: 350 raw (`modes/toyota.h:176`, `lateral.h:10-23`) |
| FSR-01.04 | The envelope shall block any non-zero LKA torque or set steer-request bit while lateral authority is not granted. | C | E-03 | T-SIL, T-HIL | Implemented (`lateral.h:98-101`) |
| FSR-01.05 | The envelope shall grant actuation authority only on a driver engagement action confirmed by the vehicle (rising edge of PCM cruise active) and shall revoke it when PCM cruise becomes inactive. | C | E-03 | T-SIL, T-VEH | Implemented (`safety.h:518-527`); PCM_CRUISE has no counter (GAP-01) |
| FSR-01.06 | The envelope shall detect loss, corruption, repetition and staleness of each RX signal it uses for gating or limiting (PCM cruise state, brake, gas, driver/EPS torque, wheel speed) and revoke actuation authority within the FTTI allocation of §8. | C | E-03 | T-SIL, FI | Partial: checksum on some messages, timeouts detected in ≤ ≈2 s (`safety.h:164-197, 321-344`); no counters, `0x226`/`0xAA` no checksum (`modes/toyota.h:40-46`) (GAP-01, GAP-06) |
| FSR-01.07 | The envelope shall detect missing or stale control commands from the SoC and remove actuation within the FTTI allocation of §8. | C | E-03 | T-HIL, FI | Partial: heartbeat mismatch 3 s, loss 5 s (`panda/board/main.c:182-213`); too slow for SG-01 (GAP-06); heartbeat shows pandad liveness only (GAP-10) |
| FSR-01.08 | The envelope shall detect corruption, loss and reordering of command frames received from the SoC and discard affected frames. | C | E-03 | T-HIL, FI | Partial: 8-bit XOR, no sequence counter (`panda/board/drivers/spi.h:97-138`, `can_comms.h:27`) (GAP-10) |
| FSR-01.09 | The safety MCU shall detect its own execution faults (program-flow hang, clock failure, memory corruption, register corruption) and enter the safe state (no actuation TX, relay released) within the FTTI allocation of §8. | C | E-03 (HW+SW) | A (FMEDA), FI | Not implemented: IWDG never initialised (`panda/board/stm32h7/stm32h7_config.h:43`), software watchdog in same ISR (`main.c:301`), faults report-only, `PERMANENT_FAULTS = 0U` (`panda/board/sys/sys.h:50`) (GAP-07, GAP-08) |
| FSR-01.10 | The safety mode and safety parameter for the reference configuration shall be fixed in the envelope and shall not be changeable by the SoC while a car safety mode is active; debug-only commands shall be unavailable in release builds. | C | E-03 | R, T-HIL | Not implemented: `0xdc` sets any mode at any time; `0xc5` relay drive not gated (`panda/board/main_comms.h:144-147, 222-225`) (GAP-09, GAP-25) |
| FSR-01.11 | The envelope shall detect a harness relay malfunction (camera control messages seen on the car side) and inhibit all actuation TX. | C | E-03, E-05 | T-SIL, T-HIL | Implemented with 1–2 s grace and no contact readback (`safety.h:215-220, 372-380`) (GAP-12) |
| FSR-01.12 | On any detected fault affecting lateral actuation, the envelope shall enter the lateral safe state (torque 0, steer request cleared) and keep it until a new valid engagement. | C | E-03 | T-SIL, FI | Partial: violating frames dropped and `controls_allowed` cleared on RX faults (`lateral.h:141-148`, `safety.h:112-121`); a TX violation alone does not revoke authority |
| FSR-01.13 | The EPS shall limit LKA torque to an overpowerable level and shall end LKA torque within a bounded time after `0x2E4` stops or carries the request bit cleared. (External measure, AOU-01R) | — (ext.) | EXT-EPS | T-VEH | Unverified (GAP-05) |
| FSR-01.14 | The SoC controller shall command lateral motion with a margin below every envelope limit (target: commanded lateral acceleration ≤ 3.0 m/s², jerk ≤ 5 m/s³, torque ≤ 90 % of the envelope bound). | QM | E-01 | T-SIL | Partial: 3.0 m/s², 5 m/s³ (`selfdrive/controls/lib/drive_helpers.py:9-14`); torque limits equal to envelope (`opendbc_repo/opendbc/car/toyota/values.py:20, 45-47`) |

### 5.2 SG-02 Lateral loss without warning (ASIL B)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-02.01 | The item shall detect EPS conditions that remove or reduce LKA assistance (EPS LKA fault states) while engaged. | B | E-03 (detection), E-01 (diagnosis text) | T-SIL, T-VEH | Host-only (QM): `opendbc_repo/opendbc/car/toyota/carstate.py:122-127` → `steerTempUnavailable`/`steerUnavailable`; not in envelope (GAP-03) |
| FSR-02.02 | The item shall detect loss of the inputs that the lateral command depends on (driving model output, calibration, localization, vehicle state) and shall not continue to actuate on inputs that are no longer valid. | B | E-01 (QM, see note), E-03 (FSR-01.07 as backstop) | T-SIL, FI | Not met: soft disable keeps actuating for 3 s on failed inputs (`selfdrive/selfdrived/state.py:7-8`); controlsd does not check freshness (`selfdrive/controls/controlsd.py:66, 122-127`) (GAP-16); diagnostics masked during big-model fallback (`selfdrive/selfdrived/selfdrived.py:382-384, 403, 457`) (GAP-17) |
| FSR-02.03 | On a detected loss or degradation of lateral control, the item shall give a visual and acoustic take-over request within 1 s of fault detection and before or at the start of torque reduction. | B | E-01/HMI, E-03 siren for SoC loss | T-HIL, T-VEH | Partial: soft/immediate disable alerts (`selfdrive/selfdrived/events.py:224-234`); timing not verified |
| FSR-02.04 | When torque is withdrawn because of a fault (not a driver action), the reduction shall follow a bounded ramp unless the fault makes the command itself untrusted, in which case torque shall go to zero at once. | B | E-01, E-03 | A, T-SIL | Partial: rate-down limit 25 raw/frame enforced (`modes/toyota.h:175`); no defined fault ramp |
| FSR-02.05 | On loss of communication with the SoC while engaged, the safety MCU shall give an acoustic warning that does not depend on the SoC. | B | E-03 (panda buzzer) | T-HIL | Partial: siren 3 s after heartbeat loss (`panda/board/main.c:193-205`); depends on 5 s detection (GAP-06) |
| FSR-02.06 | Driver monitoring shall detect an inattentive or unresponsive driver while engaged and escalate warnings within the timing set in [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) §5. | QM (see §7) | E-01/DM, E-02 | T-SIL, T-VEH | Implemented: 5/8/13 s vision, 5/15/25 s wheel-touch (`selfdrive/monitoring/policy.py:31-36`) |
| FSR-02.07 | Driver monitoring shall detect its own invalidity (no driver image, camera blocked, model output missing or not credible) and fall back to a policy that is no less strict than the active policy. | QM (see §7) | E-01/DM | T-SIL, FI | Partial: high-uncertainty → wheel-touch fallback (`policy.py:77-78`); source validity hard-coded `True` (`selfdrive/modeld/dmonitoringmodeld.py:99`); wheel-touch awareness reset by any steer/gas input (`policy.py:334-335`) (GAP-21) |
| FSR-02.08 | Driver monitoring shall not be disabled, put into demo mode or replaced by synthetic inputs while the item can engage. | QM (see §7) | E-01/DM | R, T-SIL | Not met: `IsDriverViewEnabled` demo mode (`selfdrive/monitoring/dmonitoringd.py:26-27`, `policy.py:428-437`) (GAP-20) |
| FSR-02.09 | If the driver does not respond to the highest DM warning, the item shall decelerate the vehicle, disengage and prevent re-engagement for a lockout period. | QM (see §7) | E-01/DM | T-SIL, T-VEH | Implemented: no-response force decel and lockout 1/5/15/30 min (`policy.py:39-44, 398`; `selfdrive/controls/controlsd.py:203-204`) |

Note on FSR-02.02: the detection of input loss lies in the QM stack. At ASIL B this is not acceptable on its own. The ASIL B argument for SG-02 rests on FSR-01.07 (envelope removes actuation on stale commands) + FSR-02.05 (independent acoustic warning), both on E-03, with tighter timing (§8). FSR-02.02/02.03 on E-01 are QM measures that give the earlier, better-explained warning in the common case.

### 5.3 SG-03 Unintended acceleration (ASIL B ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-03.01 | The envelope shall limit the commanded acceleration to an upper bound derived from controllability for the reference vehicle. | B | E-03 | A, T-SIL, T-VEH | Implemented without rationale: +2.0 m/s² (`modes/toyota.h:208`); `RAISED_ACCEL_LIMIT` not validated for Corolla (`opendbc_repo/opendbc/car/toyota/interface.py:117-118`) (GAP-04) |
| FSR-03.02 | The envelope shall allow only the inactive acceleration value while longitudinal authority is not granted or while the driver presses the accelerator. | B | E-03 | T-SIL | Implemented (`longitudinal.h:3-12`) |
| FSR-03.03 | The envelope shall limit the rate of increase of commanded acceleration (jerk). | B | E-03 | T-SIL | Not implemented (GAP-04) |
| FSR-03.04 | FSR-01.05…01.12 apply to the longitudinal path (shared mechanisms; see trace §9). | B | E-03 | as referenced | as referenced |
| FSR-03.05 | On a detected fault affecting longitudinal control, the item shall stop requesting positive acceleration and request ACC cancel from the PCM. | B | E-03 (inactive value), E-01 (cancel) | T-SIL, T-VEH | Partial: inactive value enforced; cancel bit set by host (`opendbc_repo/opendbc/car/toyota/carcontroller.py:253-254`) |
| FSR-03.06 | The PCM shall bound ACC acceleration requests to its own envelope and honour the cancel request. (External measure, AOU-05R) | — (ext.) | EXT-PCM | T-VEH | Unverified (GAP-05) |

### 5.4 SG-04 Excessive deceleration (ASIL B ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-04.01 | The envelope shall limit the commanded deceleration to a bound derived from following-traffic controllability. | B | E-03 | A, T-SIL | Implemented without rationale: −3.5 m/s² (`modes/toyota.h:209`) (GAP-04) |
| FSR-04.02 | The envelope shall limit the onset rate of commanded deceleration (negative jerk). | B | E-03 | T-SIL | Not implemented (GAP-04) |
| FSR-04.03 | The transition to the longitudinal safe state shall not create a deceleration step larger than the jerk bound of FSR-04.02. | B | E-01, E-03 | A, T-VEH | Not specified; depends on PCM behaviour on inactive value (AOU-05R) |
| FSR-04.04 | Driver accelerator input shall override commanded deceleration. | B | E-03, EXT-PCM | T-SIL, T-VEH | Implemented in envelope (`longitudinal.h:3-5`); vehicle behaviour unverified |

### 5.5 SG-05 Release on driver action (ASIL B ⚠)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-05.01 | The envelope shall revoke all actuation authority on a driver brake press (rising edge, or pressed while moving) within the SG-05 FTTI. | B | E-03 | T-SIL, T-VEH | Implemented (`safety.h:354-356`); brake message `0x226` has no checksum or counter (GAP-01) |
| FSR-05.02 | The envelope shall revoke all actuation authority when the PCM reports cruise inactive (cancel, main switch off). | B | E-03 | T-SIL, T-VEH | Implemented (`safety.h:520-521`) |
| FSR-05.03 | The envelope shall detect driver steering override (driver torque above a threshold) and reduce the LKA torque so it does not oppose the driver. | B | E-03 | T-SIL, T-VEH | Not in envelope: host-only 500 raw check (`opendbc_repo/opendbc/car/toyota/carcontroller.py:33, 83`) (GAP-02) |
| FSR-05.04 | The envelope shall block positive acceleration while the accelerator is pressed. | B | E-03 | T-SIL | Implemented (`longitudinal.h:3-5`) |
| FSR-05.05 | The engagement state that the envelope enforces shall equal the PCM cruise state, so that the vehicle's own cruise indicator gives the driver an indication of engagement independent of the item's HMI. | B | E-03, EXT-CLU | A, T-VEH | Implemented by FSR-01.05 design; independence of the cluster indication to be confirmed by test |
| FSR-05.06 | If PCM cruise is active while the item is not engaged (or the reverse) for longer than a bounded time, the item shall warn the driver and request cancel. | B | E-01, E-03 | T-SIL | Not met: `cruiseMismatch` raised after 6 s with no reaction (`selfdrive/selfdrived/selfdrived.py:421`, `events.py:458-460`) (GAP-19) |
| FSR-05.07 | Driver brake input shall produce braking regardless of ACC commands. (External measure, AOU-03R) | — (ext.) | EXT-PCM | T-VEH | Unverified |

### 5.6 SG-06 Longitudinal loss without warning (ASIL B)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-06.01 | The item shall detect loss or staleness of the longitudinal plan, lead information (radar/vision) and model output while engaged. | B | E-01 (QM), E-03 backstop via FSR-01.07 | T-SIL, FI | Partial: `commIssue`, `radarFault`, `processNotRunning` (`selfdrived.py:352-390`); masking during big-model settling (GAP-17); controlsd no freshness check (GAP-16) |
| FSR-06.02 | On detected loss, the item shall give a take-over request within 1 s and cancel ACC so that control returns to the driver; it shall not hold a stale acceleration command. | B | E-01, E-03 | T-SIL, T-VEH | Partial: soft disable with force decel (`controlsd.py:203-204`, `selfdrive/controls/lib/longitudinal_planner.py:84-85`); stale inputs used for up to ≈3.5 s (GAP-16) |
| FSR-06.03 | The item shall detect that the PCM does not execute ACC (ACC fault, cruise fault) and warn the driver. | B | E-01 | T-SIL | Implemented: `accFaulted` IMMEDIATE_DISABLE (`events.py:908`) |
| FSR-06.04 | Non-finite or out-of-range actuator commands shall be treated as faults with a fault reaction, not silently replaced. | B | E-01, E-03 | T-SIL | Not met: silently clamped to 0 (`controlsd.py:140-147`) (GAP-19) |
| FSR-06.05 | FSR-02.05 (independent acoustic warning on SoC loss) and FSR-02.06…02.09 (DM) also serve SG-06. | as ref. | as ref. | as ref. | as ref. |

### 5.7 SG-07 Stock PCS preservation (ASIL B)

| ID | Requirement | ASIL | Alloc | Verif | Impl / GAP |
|---|---|---|---|---|---|
| FSR-07.01 | The item shall forward all camera-side messages to the car side unchanged, except the defined set of intercepted control messages. | B | E-03 | T-SIL, T-HIL | Implemented: static block list (`safety.h:270-281`) |
| FSR-07.02 | The item shall not originate any message that the stock PCS function uses (e.g. PRE_COLLISION `0x344`, PCS_HUD `0x411`, AEB `0x283` with content) in the reference configuration. | B | E-03 | R, T-SIL | **Not met:** the openpilot-longitudinal TX whitelist allows the SoC to send `0x344` and `0x411` on bus 0 with no content check; only `0x283` is content-checked (`modes/toyota.h:19-28, 251-257`). The reference configuration host does not send them (`carcontroller.py:294-295` only with `DISABLE_RADAR`), but a QM fault could. (GAP-42) |
| FSR-07.03 | On safety-MCU fault, loss of device power, or harness fault, the relay shall return to the stock camera-to-vehicle connection. | B | E-05, E-03 | A, T-HIL | Partial: SILENT/NO_OUTPUT release relay (`panda/board/main.c:45-54`); de-energised relay state and power-loss behaviour not confirmed (OI-6) |
| FSR-07.04 | openpilot longitudinal commands shall not prevent PCS braking from taking priority in the PCM. (External measure, AOU-04R) | — (ext.) | EXT-PCM | T-VEH | Unverified |
| FSR-07.05 | The item shall inform the driver when the stock system reports an AEB or FCW event. | QM | E-01 | T-SIL | Implemented: `stockAeb`, `stockFcw` (`selfdrive/car/car_events.py:120-123`, `events.py:480`) |

## 6. Safe states, transitions and emergency operation

| State | Definition | Entered by | Exit |
|---|---|---|---|
| SS-L (lateral safe) | `0x2E4` torque 0, steer request cleared | Any lateral fault, driver brake/cancel, authority revoked | New valid engagement (PCM rising edge) |
| SS-G (longitudinal safe) | `0x343` inactive value; ACC cancel requested | Any longitudinal fault, driver brake/cancel | New valid engagement |
| SS-S (envelope silent) | SILENT/NO_OUTPUT: no TX, relay released (stock camera path) | Heartbeat loss, MCU fault, unknown mode (`panda/board/main.c:33-54, 193-213`) | Restart / re-initialisation |

- **Emergency operation: none.** The item is fail-silent. On any fault it hands the driving task back to the driver with a warning. No minimal-risk manoeuvre is performed, apart from the DM no-response force deceleration (FSR-02.09), which is a misuse measure rather than a fault reaction. Rationale: a supervised Level 2 system with a driver in the loop; the safe states above are reachable within one CAN frame and are controllable by an attentive driver (to be confirmed in WP-C-08 §8 tests, esp. torque removal in a curve, HE-02.1).
- **Transition rule:** a fault that makes the command untrusted (envelope fault, corrupted or stale command) → immediate SS-L/SS-G. A fault where the command is still trustworthy but the function will soon be unavailable (e.g. thermal, low disk) → warning first, then ramp to SS-L/SS-G (soft disable). The present soft disable does not make this distinction (GAP-16); FM-03 in [WP-C-07](WP-C-07-sotif-functional-modifications.md) proposes it.
- **Warning on every fault-induced transition** (FSR-02.03, FSR-06.02), with an SoC-independent fallback (FSR-02.05).

## 7. Driver monitoring integrity attributes (HARA §6.1 obs. 3)

The HARA asks the FSC to give DM an ASIL attribute inherited from SG-02/SG-06, or to justify why not.

**Proposal: DM is not assigned an ASIL. Its requirements (FSR-02.06…02.09) are QM, managed under ISO 21448 as measures against foreseeable misuse ([WP-C-05](WP-C-05-sotif-hazard-identification.md), [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md)), with integrity-supporting attributes listed below.**

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

**Condition:** the I3 confirmation review must agree that the HARA C2 ratings do not depend on DM. If the assessor disagrees, the alternative is to re-rate HE-02.1/HE-06.1 under the assumption of a distracted driver (likely C3 → ASIL C) and then decide between an ASIL-capable DM supervisor and an ODD/authority restriction. This is OI-3.

## 8. FTTI allocation (preliminary)

FTTIs are preliminary (HARA OI-3). Detailed timing belongs in [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md). The allocation below sets the budget the TSRs must meet.

| SG | FTTI (prelim.) | Detection budget | Reaction budget | Current behaviour | Gap |
|---|---|---|---|---|---|
| SG-01 (continuous limiting) | ≤ 0.5 s | 0 (per-frame check) | ≤ 1 frame (10 ms) | Per-frame limits act within one frame | — |
| SG-01 (RX loss/corruption) | ≤ 0.5 s | ≤ 0.3 s | ≤ 0.1 s | RX timeout up to ≈2 s (`safety.h:321-344`) | GAP-06, GAP-01 |
| SG-01 (SoC command loss) | ≤ 0.5 s | ≤ 0.3 s | ≤ 0.1 s | 3 s mismatch / 5 s loss (`main.c:182-213`) | GAP-06 |
| SG-01 (MCU execution fault) | ≤ 0.5 s | ≤ 0.2 s (HW watchdog) | ≤ 0.1 s | No HW watchdog | GAP-07 |
| SG-02, SG-06 (loss without warning) | ≤ 1 s to warning | ≤ 0.5 s | ≤ 0.5 s (warning) | Soft disable warns at once, but actuates on stale inputs up to ≈3.5 s | GAP-16 |
| SG-03, SG-04 | ≤ 1 s | ≤ 0.5 s | ≤ 0.3 s | as SG-01 detection | GAP-06 |
| SG-05 (driver brake/cancel) | ≤ 0.2 s | ≤ 1 brake message period (25 ms at 40 Hz) | ≤ 1 frame | Envelope revokes authority on the next RX frame, but a rejected `0x2E4` frame is dropped rather than replaced by zero torque, so the EPS may keep acting until its own timeout (TSR-109 in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md)) | GAP-46; verify on vehicle (T-VEH) |
| SG-05 (steering override) | ≤ 0.2 s | — | — | Not in envelope | GAP-02 |
| SG-07 | Continuous | n/a | n/a | Static forwarding | GAP-42 (FSR-07.02); GAP-49 (`0xe7` stops forwarding) |

Note on SG-02 in curves: [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) §3.2 estimates ≈ 0.7 s to a 0.6 m lateral drift at the ODD curve bound, which is shorter than driver reaction. The SG-02 budget above (≤ 0.5 s detection + ≤ 0.5 s to warning) is sufficient on straight roads and gentle curves but not alone at the ODD curve bound; SG-02 there relies on immediate warning and on torque being ramped rather than cut (FSR-02.04). Resolution (re-rate C of HE-02.1 or tighten R_ODD) is open in WP-S-04 OI-2 and [WP-C-03](WP-C-03-hara.md) OI-7.

## 9. FSR → SG trace

| FSR | SG-01 | SG-02 | SG-03 | SG-04 | SG-05 | SG-06 | SG-07 |
|---|---|---|---|---|---|---|---|
| FSR-01.01–01.04 | ● | | | | | | |
| FSR-01.05 | ● | | ● | ● | ● | | |
| FSR-01.06 | ● | | ● | ● | ● | | |
| FSR-01.07 | ● | ● | ● | ● | | ● | |
| FSR-01.08 | ● | | ● | ● | | | |
| FSR-01.09 | ● | ● | ● | ● | ● | ● | ● |
| FSR-01.10 | ● | | ● | ● | ● | | ● |
| FSR-01.11 | ● | | ● | | | | ● |
| FSR-01.12 | ● | | | | | | |
| FSR-01.13 | ● | | | | ● | | |
| FSR-01.14 | ● | | | | | | |
| FSR-02.01–02.05 | | ● | | | | | |
| FSR-02.06–02.09 | | ● | | | | ● | |
| FSR-03.01–03.06 | | | ● | | | | |
| FSR-04.01–04.04 | | | | ● | | | |
| FSR-05.01–05.04, 05.07 | | | | | ● | | |
| FSR-05.05–05.06 | | ● | | | ● | | |
| FSR-06.01–06.05 | | | | | | ● | |
| FSR-07.01–07.05 | | | | | | | ● |

Every SG has at least one FSR allocated to E-03 (or to an external measure plus E-03), except the warning part of SG-02/SG-06, which relies on FSR-01.07 + FSR-02.05 on E-03 as described in §5.2.

## 10. Allocation summary

| Element | FSRs | Highest ASIL |
|---|---|---|
| E-03 safety envelope | 01.01–01.12, 02.01 (detection), 02.04, 02.05, 03.01–03.05, 04.01–04.04, 05.01–05.06, 06.04, 07.01–07.03 | C (B after re-rating, §4.2) |
| E-05 harness/relay | 01.11, 07.03 | C/B |
| E-01 SoC (QM) | 01.14, 02.02, 02.03, 02.06–02.09, 03.05 (cancel), 05.06, 06.01–06.04, 07.05 | QM (ASIL-relevant items backed by E-03) |
| HMI | 02.03, 02.05 (panda buzzer, via E-03) | QM / B for buzzer path |
| EXT-EPS | 01.13 | AoU |
| EXT-PCM | 03.06, 05.07, 07.04 | AoU |
| EXT-CLU | 05.05 | AoU |
| Driver | §11 AOU-06R, AOU-02R | AoU |

## 11. Assumptions of use (refined)

| ID | Refines | Assumption | Needed by FSR | Verification | Status |
|---|---|---|---|---|---|
| AOU-01R | AOU-01 | The EPS limits LKA torque at the steering wheel to ≤ T_EPS (value to be measured) for any `0x2E4` request, and removes LKA torque within t_EPS (to be measured; code comment suggests ≈1.5–2 s) after `0x2E4` stops or the request bit clears | FSR-01.13 | Bench + vehicle characterization (closed course) | Unverified |
| AOU-02R | AOU-02 | A typical driver overpowers the envelope-bounded worst-case torque within the controllability criterion of WP-C-08 §7 (CA-01) | FSR-01.01, 05.03 | Controllability test (WP-C-08 §8) | Unverified |
| AOU-03R | AOU-03 | Brake pedal application produces braking regardless of `0x343` content, and the PCM drops ACC on brake | FSR-05.07 | Vehicle test | Unverified |
| AOU-04R | AOU-04 | PCS/AEB braking has priority over `0x343` requests in the PCM, and PCS works with the harness installed | FSR-07.04 | Message review + PCS target test | Unverified |
| AOU-05R | AOU-05 | The PCM clamps ACC requests to its own envelope and honours the cancel bit; the inactive value produces coasting without a deceleration step | FSR-03.06, 04.03 | Vehicle test with injected requests | Unverified |
| AOU-06R | AOU-06 | The driver supervises continuously, keeps hands near the wheel and is able to respond within the reaction times assumed in WP-C-08 §7 | All C2 ratings | WP-C-08 | Assumption |
| AOU-12 | new | The cluster cruise indicator is driven by PCM state and is not influenced by item TX messages other than `0x412` LKAS_HUD | FSR-05.05 | Vehicle test | Unverified |
| AOU-13 | new | The de-energised harness relay connects the forward camera to the vehicle CAN (stock path) | FSR-07.03 | Harness inspection / test (WP-H-02) | Unverified |

## 12. Warning and degradation concept

### 12.1 Degradation levels

| Level | Name | Lateral | Longitudinal | Driver info | Trigger examples |
|---|---|---|---|---|---|
| L0 | Full function | Active | Active | Engaged indication (device + cluster cruise + LKAS HUD) | — |
| L1 | Override | Active (driver torque dominates) / blocked | Blocked while gas pressed | Override indication | Driver gas or steering (`events.py:728, 736`) |
| L2 | Take-over request, planned | Active with valid inputs, ramping down ≤ soft-disable time | Force decel to cruise 0 | Soft-disable alert, then immediate-disable form < 0.5 s | Non-critical faults (thermal, memory, calibration) |
| L3 | Immediate disengagement | SS-L | SS-G + cancel | Immediate-disable alert (visual + acoustic) | Untrusted command or input, envelope/RX fault, relay fault, CAN error |
| L4 | Envelope silent | SS-S | SS-S | Panda buzzer (SoC lost) | SoC heartbeat loss, MCU fault |
| L5 | Lockout | Not available | Not available | No-entry alert with remaining time | DM non-compliance (`policy.py:42-44`) |

There is no degraded "lateral-only" or "longitudinal-only" operating mode in the reference configuration.

### 12.2 Warning requirements (summary)

- Every transition to L2/L3/L4 caused by a fault produces an acoustic and visual take-over request (FSR-02.03, 02.05, 06.02).
- Alert text must describe the actual fault (GAP-19: `canError` shows "Unknown Vehicle Variant", `events.py:928-936`). Alert design and timing are reviewed in [WP-C-08](WP-C-08-driver-hmi-misuse-analysis.md) §4.
- `speedTooHigh` (≈149 km/h) warns without disengaging (`events.py:989-996`). This is an ODD exit, not a fault; handled in WP-C-02 §6 and FM-07 of WP-C-07.

## 13. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Maintainer decision on the envelope strategy (§4.2: option (c) + ASIL B hardening recommended); record in WP-M-01 §8 as a new decision | Maintainer | G1 |
| OI-2 | Derive the speed-dependent torque limit and confirm C1 by controllability tests; then request HARA re-rating of SG-01 | Safety engineer | G2 |
| OI-3 | I3 reviewer to confirm DM is not ASIL-attributed (§7) or trigger the alternative | Safety manager | G1 |
| OI-4 | Confirm FTTIs (WP-S-04) and update §8 budgets | Safety engineer | G2 |
| OI-5 | Closed: the FSR-07.02 finding (TX whitelist allows `0x344`/`0x411`) is registered as GAP-42 | Safety engineer | G1 |
| OI-6 | Confirm relay de-energised state and power-loss behaviour (AOU-13) | HW lead | G2 |
| OI-7 | Refine FSRs into TSR-1xx…7xx in [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) and record FSR→TSR trace in `trace/` | Safety engineer | G2 |
| OI-8 | HARA has no H-07 / SG for H-07; confirm the numbering gap is intentional | HARA owner | G1 |
