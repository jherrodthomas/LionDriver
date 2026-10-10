# WP-S-02 Technical Safety Requirements Specification

| Field | Value |
|---|---|
| Work product | WP-S-02 Technical safety requirements specification |
| Standard reference | ISO 26262-4:2018 §6 (specification of technical safety requirements, safety mechanisms, requirements for production/operation by reference); ISO 26262-8:2018 §6 (requirement attributes); ISO 26262-9:2018 §5–§7 (by reference); ASPICE 4.0 SYS.2 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Up to ASIL D (SG-01, until re-rated under FSC option (c)); ASIL C (SG-03…SG-05); target ASIL B for the SG-01 part of the envelope under FSC option (c) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); safety-envelope requirements additionally reviewed by an independent reviewer (I2) per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document refines the functional safety requirements (FSR-01.01…FSR-07.05) of the [functional safety concept (WP-C-04)](../02-concept/WP-C-04-functional-safety-concept.md) into technical safety requirements (TSRs) for the LD-SDA reference configuration (2020 Corolla LE, `TOYOTA_COROLLA_TSS2`, openpilot longitudinal, comma device with STM32H7 panda, Toyota TSS2 harness).

Each TSR states one verifiable property, its ASIL, its parent FSR(s), the element it is allocated to, the type of safety mechanism, its timing (detection and reaction inside the FTTI), the verification method, and what the baseline code does today. Where the code does not meet the TSR, the GAP from the [gap assessment](../00-assessment/gap-assessment.md) or a new finding (NF-nn, §11) is named.

Related work products:

- System architecture, mechanism catalogue and allocation views: [WP-S-03](WP-S-03-technical-safety-concept-architecture.md).
- FTTI derivation and timing budgets: [WP-S-04](WP-S-04-timing-ftti-budget.md).
- Hardware-software interface: [WP-S-05](WP-S-05-hsi-specification.md).
- Production, operation, service and decommissioning requirements (TSR-8xx detail): [WP-S-06](WP-S-06-requirements-production-operation.md).
- Non-safety system requirements: [WP-S-01](WP-S-01-system-requirements.md).
- Refinement: hardware safety requirements [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md) (HWSR-5nn/7nn refine TSR-5nn/7nn with the same number and meaning as provisionally used there; HWSR-401, whose provisional parent was "TSR-4xx", refines TSR-410 and TSR-412); software safety requirements [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md) (SWSR-nnn mirror TSR numbers).
- Cybersecurity requirements that overlap TSR-511…514: [WP-S-07](WP-S-07-cybersecurity-requirements-architecture.md).

## 2. Conventions

### 2.1 ASIL attribute

The FSC ([WP-C-04 §4.2](../02-concept/WP-C-04-functional-safety-concept.md)) recommends **option (c)**: reduce actuation authority until controllability C1 is shown for HE-01.1/01.2/01.4, which lowers SG-01 to ASIL B, and harden the whole envelope to ASIL B. Until that evidence exists, SG-01 stays ASIL D (HARA 0.2, decision D-09). A C2 showing (S3 E4 C2) would only reach ASIL C. Since D-09, SG-03…SG-05 are ASIL C; mechanisms shared with the longitudinal path (FSR-03.04) need ASIL C unless those goals are also re-rated.

| Notation | Meaning |
|---|---|
| **B‡** | Target ASIL B under FSC option (c). **ASIL D applies until the HARA re-rates SG-01 on controllability evidence** (FSC OI-2). If C1 cannot be shown, ASIL D remains and the decomposition fallback of FSC §4.3 (e.g. B(D) + B(D) with a second independent limiter able to open the relay, or C(D) + A(D)) is required in addition |
| **C** | ASIL C, independent of the SG-01 decision (parents include SG-03, SG-04 or SG-05, rated C since D-09) |
| **B** | ASIL B, independent of the SG-01 decision (parents SG-02, SG-06, SG-07 only) |
| **QM (B-sup)** | Allocated to the QM SoC. It supports an ASIL B or C FSR, but the ASIL argument rests on the named envelope TSR (backstop). No ASIL claim is made for the SoC |
| **QM** | Quality-managed; no safety claim |
| **ext** | External measure or existing vehicle element, credited only through an AoU ([WP-C-04 §11](../02-concept/WP-C-04-functional-safety-concept.md)) |

### 2.2 Other attributes

| Attribute | Values |
|---|---|
| Alloc (allocation) | **P-SW** panda firmware / opendbc safety on the STM32H7 (E-03); **P-HW** panda hardware (E-04, safety MCU part); **SoC** application SoC software (E-01, QM); **HAR** harness and relay (E-05); **EXT** external element (EPS, PCM, brake); **OPS** production/operation process |
| SM type | **LIM** limiter; **GATE** authority gating; **PLB** plausibility / cross-check; **TMO** timeout / alive supervision; **E2E** integrity code / sequence; **WDG** watchdog; **FR** fault reaction; **ST** start-up or periodic self-test; **CFG** configuration lock; **ISO** spatial/temporal isolation; **WRN** driver warning; **DES** design constraint; **EXTM** external measure |
| Timing | `detect / react`: worst-case detection time and reaction time to the safe state. Budgets from [WP-C-04 §8](../02-concept/WP-C-04-functional-safety-concept.md) and [WP-S-04](WP-S-04-timing-ftti-budget.md). "frame" = one 10 ms control frame |
| Verif | **A** analysis, **R** review/inspection, **T-SIL** host-built safety test (opendbc `safety/tests`), **T-HIL** bench test with panda + CAN simulation, **T-VEH** vehicle test (closed course, [WP-V-07](../06-validation/WP-V-07-vehicle-test-operations.md)), **FI** fault injection ([WP-V-05](../06-validation/WP-V-05-fault-injection.md)), **LOG** analysis of recorded drive logs |
| Status | All TSRs are `Proposed`. The "Impl" column records what the baseline does; it is not verification evidence |

Paths: `safety.h`, `lateral.h`, `longitudinal.h`, `helpers.h`, `declarations.h`, `modes/toyota.h` are under `opendbc_repo/opendbc/safety/`. `main.c`, `main_comms.h`, `can_comms.h`, `drivers/*`, `sys/*`, `boards/*`, `stm32h7/*` are under `panda/board/`. `carcontroller.py`, `carstate.py`, `values.py`, `interface.py` are under `opendbc_repo/opendbc/car/toyota/`. Other paths are under `openpilot/`.

### 2.3 Safe states (from FSC §6)

| ID | Definition |
|---|---|
| SS-L | `0x2E4` STEERING_LKA torque 0 and STEER_REQUEST 0 reach the EPS; lateral authority revoked until a new engagement |
| SS-G | `0x343` ACC_CONTROL carries the inactive acceleration value; ACC cancel requested; longitudinal authority revoked until a new engagement |
| SS-S | Envelope silent: no actuation TX, relay released (stock camera path), siren if authority was recently granted |

## 3. TSR-1xx Lateral actuation envelope (SG-01, SG-02)

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-101 | The envelope shall reject every STEERING_LKA (`0x2E4`) frame whose STEER_TORQUE_CMD magnitude exceeds the torque bound τ_max(v) of TSR-102. Until TSR-102 is implemented, τ_max is the baseline 1500 raw. | B‡ | FSR-01.01 | P-SW | LIM | per frame / frame rejected (then TSR-108, TSR-109) | A, T-SIL, T-VEH | Partial: fixed 1500 raw (`modes/toyota.h:173`, check at `lateral.h:73-74`). No physical rationale (GAP-04) |
| TSR-102 | τ_max(v) shall be a speed-dependent lookup derived on the reference vehicle by (1) characterising the steady-state lateral acceleration and wheel torque produced by raw requests 0…1500 at speeds 10…120 km/h (AOU-01R), (2) choosing per speed the largest request whose worst-case lateral deviation over the driver intervention time stays inside the bound of [WP-S-04 §3](WP-S-04-timing-ftti-budget.md), and (3) confirming controllability C1 for that bound with the tests of [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) §8. The speed value used shall be the one that yields the smaller torque bound when the speed estimate is uncertain. | B‡ | FSR-01.01 | P-SW (+ calibration data, [WP-W-09](../05-software/WP-W-09-configuration-calibration-data.md)) | LIM | per frame | A, T-SIL, T-VEH | Not implemented for Toyota: `dynamic_max_torque` not set (`modes/toyota.h:172-186`). The mechanism exists (`lateral.h:66-71`) but uses `vehicle_speed.min − 1 m/s`, which is conservative only if τ_max increases with speed; the direction must be checked against the derived table (OI-3). Speed input integrity: TSR-405(a). GAP-04 |
| TSR-103 | The envelope shall reject `0x2E4` frames whose torque increases in magnitude by more than Δ_up, or decreases by more than Δ_down, relative to the last accepted frame, or that change by more than Δ_rt within any 250 ms window. The values shall be derived from the onset rate accepted in the controllability tests; the baseline values are 15 / 25 raw per frame and 450 raw per 250 ms. | B‡ | FSR-01.02 | P-SW | LIM | per frame | A, T-SIL | Implemented without rationale: `modes/toyota.h:174-177`; `lateral.h:49-57, 82-95`; `MAX_RT_INTERVAL` `declarations.h:71`. Host uses the same values (`values.py:45-47`), zero margin (GAP-04) |
| TSR-104 | The envelope shall reject `0x2E4` frames whose torque exceeds the measured EPS motor torque (`0x260` STEER_TORQUE_EPS scaled by the EPS factor of the safety parameter) by more than Δ_meas, using the minimum/maximum of the last 6 samples widened by 1 raw. Baseline Δ_meas = 350 raw. | B‡ | FSR-01.03 | P-SW | LIM, PLB | per frame | T-SIL | Implemented: `modes/toyota.h:98-111, 176`; `lateral.h:10-23, 82-83`; sample window `declarations.h:68`. Depends on `0x260` integrity (TSR-402…405) and on the EPS factor being locked (TSR-512) |
| TSR-105 | While lateral authority is not granted, the envelope shall reject every `0x2E4` frame with non-zero torque **or** with STEER_REQUEST set. | B‡ | FSR-01.04 | P-SW | GATE | per frame | T-SIL, T-HIL | Partial: non-zero torque rejected (`lateral.h:98-101`). STEER_REQUEST = 1 with zero torque is accepted while not engaged (`lateral.h:105` checks only the opposite mismatch). NF-01 |
| TSR-106 | While authority is granted, the envelope shall accept STEER_REQUEST = 0 with non-zero torque for at most 1 consecutive frame, only after ≥ 17 consecutive valid frames and ≥ 162 ms after the previous cut. | B‡ | FSR-01.04 | P-SW | GATE | per frame | T-SIL | Implemented: `modes/toyota.h:182-185`; `lateral.h:103-138`. Purpose: EPS fault avoidance at high steering rate (`carcontroller.py:27-30`) |
| TSR-107 | In the reference configuration (LKA torque path) the envelope shall reject any STEERING_LTA (`0x191`) frame that carries a steering request, a non-zero angle command or a non-zero torque wind-down, and shall accept `0x2E4` only with its specified length (5 bytes). | B‡ | FSR-01.04 | P-SW | GATE | per frame | T-SIL | Implemented: `modes/toyota.h:269-273` (LTA blocked), `modes/toyota.h:11` (length 5), length match `helpers.h:60-64` |
| TSR-108 | If the envelope rejects a lateral command frame while lateral authority is granted, it shall revoke lateral authority (SS-L) and keep it revoked until a new valid engagement (TSR-301), and it shall report the event and its cause to the SoC. | B‡ | FSR-01.12 | P-SW | FR | detect: same frame / react: same frame | T-SIL, FI | Not implemented: the violating frame is dropped and the rate state reset (`lateral.h:140-148`), `safety_tx_blocked` is counted and reported (`drivers/can_common.h:168-171`, `main_comms.h:27`), but `controls_allowed` is not cleared. Upstream design lets the host recover; the FSC requires latching (OI-4) |
| TSR-109 | Whenever the envelope rejects a `0x2E4` frame or revokes lateral authority, the EPS shall receive torque 0 with STEER_REQUEST 0 within ≤ 0.1 s. This shall be achieved by (a) the envelope transmitting, in place of each rejected frame, a `0x2E4` frame with zero torque, STEER_REQUEST 0, a counter continuing the host sequence and a valid checksum; or (b) only if vehicle characterisation shows that the EPS ramps LKA torque to zero within ≤ 0.1 s of a missing `0x2E4` frame, by withholding the frame. Option (a) is the recommended design. | B‡ | FSR-01.12, FSR-01.13, FSR-05.01, FSR-02.04 | P-SW (a); EXT (b) | FR | react ≤ 0.1 s | T-HIL, T-VEH, FI | **Not implemented / unverified.** Rejecting a frame drops it (`drivers/can_common.h:161-176`); the EPS then sees a message drop-out. The only available description of drop-out handling is a code comment (LKA_STATE 9 → 11 over ≈2 s, then 3; `carstate.py:15-16`), so torque may persist after rejection. NF-02, GAP-05 |
| TSR-110 | The envelope shall receive EPS_STATUS (`0x262`) and, while lateral authority is granted, shall revoke lateral authority and report the cause when LKA_STATE indicates an EPS fault or LKA unavailability, or when EPS_STATUS is missing beyond its timeout (TSR-401). The LKA_STATE fault code set shall be confirmed for the reference EPS firmware. | B (SG-02); B‡ where it gates SG-01 | FSR-02.01 | P-SW (detect); SoC (warn, TSR-606) | PLB, TMO | detect ≤ 0.3 s / react ≤ 0.1 s | T-SIL, T-VEH | Host-only: `carstate.py:122-127` (fault codes `carstate.py:19-22`, reverse-engineered) → `steerFaultTemporary/Permanent` (`selfdrive/controls/controlsd.py:100-101`). Not in the envelope RX set (`modes/toyota.h:39-46`). GAP-03 |
| TSR-111 | The EPS shall limit the LKA torque at the steering wheel to ≤ T_EPS for any `0x2E4` request and remove LKA torque within t_EPS after `0x2E4` stops or STEER_REQUEST clears. (External measure; T_EPS and t_EPS to be measured.) | ext | FSR-01.13 | EXT | EXTM | t_EPS TBD | T-VEH | Unverified (AOU-01R, GAP-05) |

## 4. TSR-2xx Longitudinal envelope (SG-03, SG-04)

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-201 | The envelope shall reject every ACC_CONTROL (`0x343`) frame whose ACCEL_CMD exceeds a_max, where a_max is derived from the controllability of HE-03.1…03.3 on the reference vehicle. Baseline a_max = +2.0 m/s² (raw 2000). | C | FSR-03.01 | P-SW | LIM | per frame | A, T-SIL, T-VEH | Implemented without rationale: `modes/toyota.h:207-210, 225`; `longitudinal.h:8-12`. Host uses 2.0 m/s² under `RAISED_ACCEL_LIMIT` (`values.py:39-43`, `interface.py:117-118`), zero margin; flag not validated for the Corolla (GAP-04) |
| TSR-202 | The envelope shall reject every `0x343` frame whose ACCEL_CMD is below a_min, derived from the controllability of HE-04.1 (following traffic). Baseline a_min = −3.5 m/s² (raw −3500). | C | FSR-04.01 | P-SW | LIM | per frame | A, T-SIL, T-VEH | Implemented without rationale: `modes/toyota.h:209` (GAP-04) |
| TSR-203 | While longitudinal authority is not granted (not engaged, or accelerator pressed per TSR-305), the envelope shall accept `0x343` only with the inactive acceleration value. | C | FSR-03.02, FSR-04.04, FSR-05.04 | P-SW | GATE | per frame | T-SIL | Implemented: `longitudinal.h:3-12` |
| TSR-204 | The envelope shall reject `0x343` frames whose ACCEL_CMD increases, relative to the last accepted value (the inactive value counting as 0 m/s² at engagement), faster than j_up, derived from controllability. | C | FSR-03.03 | P-SW | LIM | per frame | T-SIL, T-VEH | Not implemented in the envelope (GAP-04). Host-only wind-up limit 0.12 m/s² per 3-frame step ≈ 4 m/s³ (`carcontroller.py:21`) |
| TSR-205 | The envelope shall reject `0x343` frames whose ACCEL_CMD decreases (deceleration onset) faster than j_down, derived from following-traffic controllability. | C | FSR-04.02 | P-SW | LIM | per frame | T-SIL, T-VEH | Not implemented in the envelope (GAP-04). Host-only wind-down ≈ −4 m/s³ (`carcontroller.py:22`) |
| TSR-206 | On revocation of longitudinal authority the transition to SS-G shall not cause a vehicle deceleration or acceleration step beyond the jerk bounds of TSR-204/205. If the PCM response to a step from the last commanded value to the inactive value is not shown to be bounded (AOU-05R), the envelope shall accept a commanded value that winds down to the inactive value at no more than j_down/j_up for at most 1 s after revocation. | C | FSR-03.05, FSR-04.03 | P-SW, EXT | FR | react ≤ 0.3 s to SS-G start | A, T-VEH | Not specified. Today any non-inactive value is rejected at once after revocation (`longitudinal.h:8-12`); vehicle response unknown (GAP-05) |
| TSR-207 | For `0x343`, the envelope shall also check the actuation-relevant fields PERMIT_BRAKING, CANCEL_REQ, RELEASE_STANDSTILL and ACCEL_CMD_ALT against the values allowed in the current authority state, and while authority is not granted shall accept only frames that do not request acceleration, braking or standstill release. | C | FSR-03.02, FSR-03.05 | P-SW | GATE | per frame | T-SIL | Partial: in openpilot-longitudinal mode only bytes 0–1 (ACCEL_CMD) are checked (`modes/toyota.h:216-241`); field layout `opendbc_repo/opendbc/dbc/generator/toyota/_toyota_2017.dbc:178-193`. NF-03 |
| TSR-208 | The PCM shall bound ACC acceleration requests to its own ACC envelope, honour CANCEL_REQ, and produce coasting without a deceleration step on the inactive value. (External measure.) | ext | FSR-03.06, FSR-04.03 | EXT | EXTM | — | T-VEH | Unverified (AOU-05R, GAP-05) |

## 5. TSR-3xx Engagement, disengagement and driver override (SG-01, SG-03…SG-05)

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-301 | The envelope shall grant actuation authority only on the rising edge of PCM_CRUISE (`0x1D2`) CRUISE_ACTIVE and shall revoke it in the same frame in which CRUISE_ACTIVE is received false (cancel, main switch off, PCM-internal drop). | B‡ | FSR-01.05, FSR-05.02 | P-SW | GATE | detect ≤ 1 period (30 ms at 33 Hz) / same frame | T-SIL, T-VEH | Implemented: `safety.h:518-527`; `modes/toyota.h:143-146`. `0x1D2` has a checksum but no counter (GAP-01) → TSR-402…405 |
| TSR-302 | The envelope shall revoke all actuation authority when a driver brake press is received (rising edge, or pressed while the vehicle is moving). | C | FSR-05.01 | P-SW | GATE | detect ≤ 1 period (25 ms at 40 Hz) / same frame; SS-L via TSR-109 | T-SIL, T-VEH | Implemented: `safety.h:350-356`; BRAKE_MODULE (`0x226`) bit 37 `modes/toyota.h:148-150`; `vehicle_moving` from wheel speeds `modes/toyota.h:157-168`. `0x226` has no checksum and no counter (`modes/toyota.h:46`, GAP-01) → TSR-405(b) |
| TSR-303 | On every fault-induced disengagement with openpilot longitudinal active, the SoC shall set CANCEL_REQ so that the PCM drops ACC. | QM (B-sup: TSR-203, TSR-301) | FSR-03.05 | SoC | FR | ≤ 0.1 s after disengagement | T-SIL, T-VEH | Implemented on host: `carcontroller.py:253-254` (cancel in ACC_CONTROL) |
| TSR-304 | The envelope shall monitor STEER_TORQUE_DRIVER (`0x260`) on the LKA path and (a) reject `0x2E4` frames that increase torque opposing the driver beyond a driver allowance (driver-limited check in addition to the measured-torque check of TSR-104), and (b) when the driver torque exceeds T_ovr for longer than t_ovr, revoke lateral authority or force the commanded torque to zero at the Δ_down rate. T_ovr, t_ovr and the allowance shall be derived from the override behaviour accepted in [WP-C-08](../02-concept/WP-C-08-driver-hmi-misuse-analysis.md) and from the EPS override threshold (AOU-02R). | C (SG-05); B‡ (SG-01, HE-05.2) | FSR-05.03 | P-SW | PLB, GATE | detect ≤ 2 frames of `0x260` (40 ms) / torque decreasing next frame, zero ≤ 0.2 s | T-SIL, T-VEH | **Not implemented on the LKA path** (GAP-02). Driver torque is sampled (`modes/toyota.h:113-116`) but used only for LTA (`modes/toyota.h:294-298`). A driver-limited check exists (`lateral.h:26-46`, `TorqueDriverLimited`) but the Toyota mode is motor-limited (`modes/toyota.h:178`). Host-only: `MAX_USER_TORQUE` 500 (`carcontroller.py:33, 83`) |
| TSR-305 | While the accelerator is pressed (PCM_CRUISE GAS_RELEASED = 0), the envelope shall withdraw longitudinal authority (inactive value only, TSR-203). The accelerator shall not revoke lateral authority in the reference configuration unless the HMI decision in WP-C-08 changes `DisengageOnAccelerator`. | C | FSR-04.04, FSR-05.04 | P-SW | GATE | detect ≤ 1 period / same frame | T-SIL | Implemented: `modes/toyota.h:146`; `longitudinal.h:3-5`. `DisengageOnAccelerator` default `0` (`common/params_keys.h:35`) |
| TSR-306 | The envelope shall not grant actuation authority while any RX check of TSR-401…405 is failed, including timeouts not yet evaluated by the periodic check. | B‡ | FSR-01.05, FSR-01.06 | P-SW | GATE | per frame | T-SIL | Partial: the mode RX hook runs only for valid, whitelisted frames (`safety.h:202-206`) and an invalid frame clears authority (`safety.h:112-121`), but timeouts are evaluated only in the 1 Hz `safety_tick` (`safety.h:321-344`), so a rising edge can grant authority while another message is already lagging (GAP-06) |
| TSR-307 | (a) The envelope shall revoke authority when the SoC heartbeat reports "not engaged" while authority is granted, within ≤ 0.3 s. (b) The SoC shall immediately disable when the envelope's reported authority differs from its own engaged state for > 0.3 s. | (a) B‡; (b) QM (B-sup) | FSR-05.06, FSR-01.07 | P-SW (a); SoC (b) | PLB | (a) ≤ 0.3 s / same tick; (b) ≤ 0.3 s | T-HIL, FI | (a) 3 consecutive 1 Hz ticks ≈ 2–3 s (`main.c:181-189`). (b) 200 cycles at 100 Hz = 2 s (`selfdrive/selfdrived/selfdrived.py:338, 503-510`) (GAP-06) |
| TSR-308 | If PCM cruise is active while the item is not engaged, or the item is engaged while PCM cruise is inactive, for longer than 1 s, the SoC shall warn the driver and request ACC cancel. | QM (B-sup: TSR-301) | FSR-05.06 | SoC | PLB, WRN | ≤ 1 s | T-SIL | Not met: `cruiseMismatch` raised after 6 s (`selfdrive/selfdrived/selfdrived.py:420-422`) with IMMEDIATE_DISABLE commented out (`selfdrive/selfdrived/events.py:458-460`) (GAP-19) |
| TSR-309 | The engagement state enforced by the envelope shall be the PCM cruise state, so that the vehicle's cluster cruise indicator is an indication of engagement independent of the item's HMI. | C | FSR-05.05 | P-SW, EXT | DES | — | A, T-VEH | Implemented by TSR-301 design. Independence of the cluster indication unverified (AOU-12) |
| TSR-310 | Driver brake application shall produce braking regardless of `0x343` content, and the PCM shall drop ACC on brake. (External measure.) | ext | FSR-05.07 | EXT | EXTM | — | T-VEH | Unverified (AOU-03R) |
| TSR-311 | Actuation authority shall be false at MCU start-up and after every safety-mode change, and all limiter state (last torque, rate windows, samples) shall be reset. | B‡ | FSR-01.05 | P-SW | GATE | — | T-SIL | Implemented: `safety.h:57, 423-460` |

## 6. TSR-4xx Communication integrity (vehicle CAN RX, SoC ↔ panda)

### 6.1 Vehicle CAN RX: E2E strategy for messages without counters (GAP-01)

The Toyota messages the envelope uses carry no alive counter. `0x226` (brake) and `0xAA` (wheel speeds) carry no checksum; `0x260` and `0x1D2` carry an 8-bit additive checksum (`modes/toyota.h:39-46, 65-72`). The vehicle cannot be changed, so classic E2E protection (CRC + counter + timeout) is not achievable. The strategy is a combination of measures, each of which covers a subset of the communication failure modes. The diagnostic coverage of the combination is estimated in [WP-S-03 §6](WP-S-03-technical-safety-concept-architecture.md) and must be confirmed by fault injection.

| Failure mode | `0x1D2` cruise/gas | `0x226` brake | `0x260` torques | `0xAA` speed | Measure |
|---|---|---|---|---|---|
| Loss / delay | timeout | timeout | timeout | timeout | TSR-401 |
| Corruption | checksum | — (none) | checksum | wheel fault bits only | TSR-402; cross-checks TSR-405 |
| Repetition / stuck frame | — | — | frozen-content | frozen-content (when moving) | TSR-404 |
| Insertion / extra sender | rate | rate | rate | rate | TSR-403 |
| Masquerade / wrong value with valid checksum | cross-check with PCM_CRUISE_2 MAIN_ON | cross-check with PCM_CRUISE_2 BRAKE_PRESSED and cruise drop | cross-check torque response to command | cross-check with `0xB4` SPEED | TSR-405 |

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-401 | For each RX message used for gating or limiting (`0xAA`, `0x260`, `0x1D2`, `0x226`, and `0x262`, `0x1D3`, `0xB4` once added), the envelope shall detect absence longer than 5 nominal periods and shall evaluate this at ≥ 50 Hz, so that worst-case detection is ≤ 0.2 s. | B‡ | FSR-01.06 | P-SW | TMO | detect ≤ 0.2 s / react ≤ 0.1 s | T-SIL, T-HIL, FI | Not met: threshold max(10 periods, 1 s) evaluated in the 1 Hz `safety_tick` → 1–2 s (`safety.h:321-344`, called from `main.c:241-242`) (GAP-06) |
| TSR-402 | The envelope shall verify the Toyota checksum and the message length of every RX message that carries a checksum (`0x260`, `0x1D2`, and `0x262`, `0x1D3`, `0xB4` once added) and treat one failed frame as an RX fault. | B‡ | FSR-01.06 | P-SW | E2E | per frame | T-SIL | Implemented for `0x260`, `0x1D2`: `safety.h:164-197`; `modes/toyota.h:40-46, 65-77`. Residual weakness: 8-bit additive sum (GAP-01) |
| TSR-403 | The envelope shall detect when an RX message arrives at more than 1.5× its nominal rate over a 100 ms window (indicating duplicated or inserted frames) and treat it as an RX fault. | B‡ | FSR-01.06 | P-SW | PLB | detect ≤ 0.1 s | T-SIL, FI | Not implemented (GAP-01). `frequency` is only used for the timeout (`safety.h:330-336`) |
| TSR-404 | For RX signals that vary in normal operation, the envelope shall detect a frozen payload: an identical data field (excluding checksum) for longer than t_frz while the vehicle is moving (`0x260` torque/angle bytes; `0xAA` wheel speeds above a minimum speed; `0xB4` ENCODER). t_frz shall be set from fork-owned drive logs so that no false detection occurs in the reference log set. | B‡ | FSR-01.06 | P-SW | PLB | detect ≤ t_frz (target ≤ 0.2 s) | LOG, T-SIL, FI | Not implemented (GAP-01) |
| TSR-405 | The envelope shall apply these cross-checks and treat a disagreement lasting longer than its tolerance time as an RX fault: (a) wheel-speed mean (`0xAA`) vs SPEED (`0xB4`) within 2 m/s; (b) BRAKE_PRESSED in `0x226` vs PCM_CRUISE_2 (`0x1D3`) BRAKE_PRESSED — on disagreement the envelope shall assume "brake pressed" (revoke); (c) CRUISE_ACTIVE = 1 shall imply PCM_CRUISE_2 MAIN_ON = 1; (d) while authority is granted, measured EPS torque shall follow the accepted command within an EPS-response tolerance (detects frozen or replaced `0x260`). Signal availability and tolerances shall be confirmed on reference-vehicle logs. | B‡ | FSR-01.06, FSR-05.01 | P-SW | PLB (cross-channel) | detect ≤ 0.2 s | LOG, T-SIL, FI | Not implemented (GAP-01). A speed cross-check helper exists but is unused by the Toyota mode (`safety.h:529-537`). Candidate signals: `0xB4` SPEED/ENCODER (`opendbc_repo/opendbc/dbc/generator/toyota/_toyota_2017.dbc:77-80`), `0x1D3` BRAKE_PRESSED (`_toyota_2017.dbc:110-111`) |
| TSR-406 | On any RX fault of TSR-401…405, the envelope shall revoke all actuation authority within ≤ 0.1 s (SS-L via TSR-109, SS-G), report a fault-specific reason code to the SoC, and not grant authority again until all checks pass and a new PCM rising edge occurs. | B‡ | FSR-01.06, FSR-01.12 | P-SW | FR | react ≤ 0.1 s | T-SIL, FI | Partial: revocation on checksum/quality (`safety.h:112-121`) and timeout (`safety.h:337-340`); only a single flag is reported (`main_comms.h:23`) |

### 6.2 SoC ↔ panda link and command liveness

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-407 | In a car safety mode, the envelope shall detect absence of the SoC heartbeat (`0xf3`) for > 0.3 s and then revoke all actuation authority at once (SS-L, SS-G). It shall enter SS-S (SILENT, relay released) after the longer timeout of TSR-510. | B‡ | FSR-01.07 | P-SW | TMO | detect ≤ 0.3 s / react ≤ 0.1 s | T-HIL, FI | Not met: heartbeat counter incremented at 1 Hz, SILENT after 5 s with ignition (`main.c:101-103, 153-162, 191-226`). Heartbeat sent at 10 Hz (`selfdrive/pandad/pandad.cc:385-394`; `selfdrive/pandad/panda.cc:137-139`) (GAP-06) |
| TSR-408 | While lateral authority is granted, the envelope shall monitor the arrival of `0x2E4` frames from the SoC and, if no frame arrives for > 50 ms (5 frames), revoke authority and command SS-L (TSR-109). While longitudinal authority is granted, the same shall apply to `0x343` with a gap > 100 ms. | B‡ | FSR-01.07 | P-SW | TMO | detect ≤ 50 / 100 ms / react ≤ 0.1 s | T-HIL, FI | Not implemented. The heartbeat shows only that `pandad` is alive (GAP-10); `card` stops sending when `carControl` is not alive within 0.1 s (`selfdrive/car/card.py:234-238`), after which only the EPS drop-out behaviour (AOU-01R) removes torque |
| TSR-409 | The heartbeat shall carry evidence that the control loop is alive (e.g. the latest `carControl` frame counter), and the envelope shall treat a heartbeat whose evidence has not advanced for > 0.3 s as a missing heartbeat. | B‡ (panda check); QM (SoC content) | FSR-01.07 | P-SW, SoC | TMO | ≤ 0.3 s | T-HIL, FI | Not implemented: heartbeat carries only `engaged` = `selfdriveState` alive && valid && enabled (`selfdrive/pandad/pandad.cc:389-390`) (GAP-10) |
| TSR-410 | Every SPI transfer (header and data) shall be protected by a CRC whose residual error probability over the maximum transfer length meets the target set in [WP-S-05 §4](WP-S-05-hsi-specification.md), and every CAN-TX transfer shall carry a sequence counter; the envelope shall discard transfers with a failed CRC or a repeated or out-of-order counter. The per-packet XOR may remain as an additional check. | B‡ | FSR-01.08 | P-SW, SoC | E2E | per transfer | A, T-HIL, FI | Not met: 8-bit XOR seeded 0xAB on header and data (`drivers/spi.h:97-104, 122, 137`); per-CAN-packet 8-bit XOR (`drivers/can_common.h:144-159`, checked at FDCAN TX `drivers/fdcan.h:100`); no sequence counter (`can_comms.h:8-37`) (GAP-10) |
| TSR-411 | The envelope shall reject actuation frames whose transfer counter shows they are older than 2 control periods relative to the newest accepted transfer (freshness). | B‡ | FSR-01.08 | P-SW | E2E | per transfer | T-HIL, FI | Not implemented (GAP-10). Host-side age check is 1 s (`selfdrive/pandad/pandad.cc:78-79`), see TSR-614 |
| TSR-412 | The envelope shall validate every length field received over SPI against its buffer size before starting a DMA transfer or copy, and every control-request parameter used as an array index against the array bounds; a violation shall be NACKed and counted as an SPI error. | B‡ | FSR-01.08, FSR-01.10 | P-SW | ISO, PLB | per transfer | R, T-HIL, FI | **Not met (NF-04):** MOSI/MISO lengths are taken from the header (`drivers/spi.h:115-116`) and the data DMA is started with `spi_data_len_mosi + 1` into a 4096-byte buffer (`drivers/spi.h:233`, `drivers/drivers.h:216`) without a bound check; `comms_can_read` fills `spi_buf_tx` up to the requested MISO length (`drivers/spi.h:150`); request `0xe8` indexes `bus_config[param1]` without a bound check (`main_comms.h:262-264`). The nominal host keeps lengths below the buffer size (`selfdrive/pandad/spi.cc:319-320`), but freedom from interference cannot rely on the QM host |
| TSR-413 | If SPI errors (header/data checksum failures, NACKs) exceed a rate threshold while authority is granted, the envelope shall revoke authority and report. | B‡ | FSR-01.08 | P-SW | FR | ≤ 0.3 s | T-HIL, FI | Partial: counted and reported only (`drivers/spi.h:220-222`, `main_comms.h:36`) |

## 7. TSR-5xx Safety-MCU platform integrity

Numbering is aligned with the provisional TSR parents in [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md); HWSR-5nn refines TSR-5nn.

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-501 | The safety MCU shall be supervised by an independent hardware watchdog (IWDG1, LSI-clocked) that is started before the application runs, cannot be stopped by the SoC, is serviced only after the periodic safety processing has completed, and resets the MCU within ≤ 0.2 s of a stall. | B‡ | FSR-01.09 | P-HW (cfg), P-SW | WDG | detect ≤ 0.2 s / reset → SS-S | R, T-HIL, FI | **Not implemented.** `IND_WDG` defined (`stm32h7/stm32h7_config.h:43`), never used; software watchdog checked inside the tick ISR it supervises (`drivers/simple_watchdog.h`, `main.c:119, 301`) (GAP-07). HWSR-501…501d |
| TSR-502 | Every detected MCU fault (watchdog, interrupt-rate, register divergence, memory ECC, clock, supply, temperature, SPI/DMA, siren, relay) shall lead to SS-S within ≤ 0.1 s of detection. Faults shall be classified as latching until power cycle or as recoverable, by documented rationale. During and after any reset the outputs shall be in SS-S until a valid safety mode is set. | B‡ | FSR-01.09, FSR-07.03 | P-SW, P-HW | FR | react ≤ 0.1 s | R, FI | **Not implemented.** Faults are report-only (`sys/faults.h:8-27`); `PERMANENT_FAULTS 0U` (`sys/sys.h:50`); only relay malfunction blocks TX (GAP-08). Start state SILENT (`main.c:295`). A hang (default handlers, `assert_fatal`, no IWDG) leaves the relay in its last state (GAP-43). HWSR-502…502c |
| TSR-503 | Memory faults that can corrupt actuation decisions shall be detected: RAM ECC with double-error reaction, flash image CRC at start-up and periodically, and periodic check of safety-critical configuration registers, each leading to TSR-502. | B‡ | FSR-01.09 | P-HW (cfg), P-SW | ST, PLB | ≤ 0.2 s for RAM/register faults; flash: start-up + background | R, FI | Partial: register divergence check at 1 Hz, report-only (`drivers/registers.h:56-70`, `main.c:228-229`); no ECC handling, no runtime CRC (GAP-08). HWSR-503…503d |
| TSR-504 | Loss or drift of the MCU clock that would invalidate timing checks or CAN bit timing shall be detected and lead to TSR-502. | B‡ | FSR-01.09 | P-HW (cfg), P-SW | PLB | ≤ 0.2 s | FI | Partial: HSE clock security system per WP-H-01 HWSR-504; no frequency cross-check |
| TSR-505 | Supply voltage of the MCU outside its operating range shall lead to reset or SS-S (brown-out reset, programmable voltage detector), and vehicle input voltage out of range while the relay is driven shall lead to SS-S. | B‡ | FSR-01.09 | P-HW, P-SW | PLB | ≤ 0.2 s | T-HIL | Unknown / not implemented (BOR, PVD not configured; input voltage reported only, `main_comms.h:14`). HWSR-505…505b |
| TSR-506 | The intercept relay shall be de-energise-to-safe, its actual state shall be read back and compared with the commanded state in both directions within ≤ 0.3 s, and a detected relay malfunction shall inhibit all actuation TX and be latched until power cycle (not cleared by a safety-mode change). | B‡ (blocking), B (PCS restore) | FSR-01.11, FSR-07.03 | P-HW, HAR, P-SW | PLB, FR | detect ≤ 0.3 s | A, T-HIL, FI | Partial: open-drain active-low drive, released at init (`drivers/harness.h:8-33, 96-107`); indirect detection only (camera control messages on the car side) after a 1 s transition window counted at 1 Hz (`safety.h:211-220, 372-380`); cleared on every mode change (`safety.h:427, 459`), so a host can clear it with `0xdc`. No readback (GAP-12); relay stuck in intercept not detected at all (GAP-43). HWSR-506…506d |
| TSR-507 | Safety-critical data (safety mode and parameter, limits, authority state, relay state) and the stacks shall be protected against writes from communication handlers by the MPU, with a stack guard, and a MemManage fault shall lead to TSR-502. | B‡ | FSR-01.09, FSR-01.10 | P-HW (cfg), P-SW | ISO | — | R, FI | Not implemented: no MPU configuration (GAP-08, GAP-11). HWSR-507 |
| TSR-508 | The car-side CAN transceiver shall be non-transmitting from reset until enabled by firmware; bus-off or persistent TX failure on the car-side bus while authority is granted shall revoke authority and be reported. | B‡ | FSR-01.09, FSR-01.12 | P-HW, P-SW | FR | ≤ 0.3 s | T-HIL, FI | Partial: transceivers enabled after SILENT (`main.c:295-298`); bus-off counted (`drivers/fdcan.h`), host raises `canError` only. HWSR-508…508c |
| TSR-509 | MCU die temperature outside its specified range shall lead to SS-S. | B | FSR-01.09 | P-HW, P-SW | PLB | ≤ 1 s | T-HIL | Partial: DTS read and reported only (`main_comms.h:51-52`). HWSR-509 |
| TSR-510 | Ignition state shall be sensed from the harness ignition line; loss of the SoC heartbeat shall lead to SS-S after ≤ 2 s regardless of the ignition reading, and a failed ignition input shall not keep the relay driven without a heartbeat. | B | FSR-07.03 | P-HW, HAR, P-SW | TMO | SS-S ≤ 2 s | A, T-HIL | Partial: line-only ignition for Toyota (`drivers/harness.h:35-52`; `opendbc_repo/opendbc/safety/ignition.h:12-63` has no Toyota case); SILENT after 5 s (ignition on) / 2 s (off) (`main.c:101-103, 193`). HWSR-510…510a |
| TSR-511 | Only release-signed LionDriver firmware shall execute on the safety MCU: the signature scheme shall use a current algorithm and key length, flash read-out and write protection shall be set, the SoC's control of `STM_BOOT0`/`STM_RST_N` shall not allow non-release code to drive the relay, release builds of `pandad` shall not flash a development bootstub, and softloader entry (`0xd1` param 1) shall be refused in a car safety mode and while the ignition is on (CSR-024). | B‡ (+ CS) | FSR-01.10 | P-SW, P-HW (option bytes), SoC | CFG | — | R, T-HIL | **Not met.** RSA-1024/SHA-1 (`crypto/rsa.h:37`, `crypto/sha.h:45`; `bootstub.c:47-72`); only sector 0 protected from erase (`stm32h7/llflash.h:12-20`); SoC drives BOOT0/NRST (`openpilot/common/hardware/comma/hardware.py:400-419`); recovery flashes a development bootstub (`selfdrive/pandad/pandad.py:34-39`); softloader entry allowed in release at any time (`main_comms.h:176-180`) (GAP-24, GAP-38). See [WP-S-07](WP-S-07-cybersecurity-requirements-architecture.md) |
| TSR-512 | In release builds for the reference configuration the safety MCU shall accept only the modes SILENT, NOOUTPUT, ELM327 (fingerprinting, relay released) and TOYOTA with the reference safety parameter compiled into the firmware (EPS factor 73, no flags). Once TOYOTA mode is active, it shall accept only a change to NOOUTPUT or SILENT; any other request shall be rejected and reported. The alternative-experience word shall likewise be fixed to the reference value in release builds, so that it cannot be changed in a non-car mode and carried into a later TOYOTA session. | B‡ | FSR-01.10 | P-SW | CFG | per request | R, T-HIL | **Not met.** `0xdc` sets any mode and parameter at any time without check (`main_comms.h:222-225`; `main.c:31-79`); the parameter comes from the unauthenticated params store (`selfdrive/pandad/panda_safety.cc:56-69`) (GAP-09). `0xdf` sets `alternative_experience` freely in any non-car mode, and the value persists into the next car mode (`main_comms.h:242-247`) |
| TSR-513 | In release builds, control requests that can change actuation, relay, CAN configuration or comms state shall be rejected while a car safety mode is active: at least `0xc5` (relay drive), `0xe5` (CAN loopback), `0xde`/`0xf9`/`0xfc`/`0xe8` (bit rate and CAN-FD configuration), `0xdb` (OBD multiplexing), `0xe6` (clock source), `0xe7` (power save; in car mode it stops camera-side forwarding with the relay energised, SG-07, WP-A-04 SPF-08), `0xf1` (queue clear), `0xd1` param 1 (softloader entry, see also TSR-511), `0xd8` (MCU reset without fault reporting), `0xdf` (alternative experience, see TSR-512). Also `0xc0` (comms reset), `0xb0`/`0xb1` and `0xf6` (to be confirmed per WP-W-02 OI-5). | B‡ | FSR-01.10 | P-SW | CFG | per request | R, T-HIL | **Not met:** none of these is gated by mode or `ALLOW_DEBUG` (`main_comms.h:144-147, 218-221, 233-276, 296-314`) (GAP-09). `0xb5` and bootloader entry `0xd1/0` are already debug-only (`main_comms.h:92-98, 168-175`); `0xf8` is already refused in car modes (`main_comms.h:290-295`). `0xd1` param 1 and `0xd8` are accepted in release builds (`main_comms.h:176-180, 215-216`); `0xdf` is refused only while a car mode is active (`main_comms.h:242-247`). `0xe7` effect: CAN interrupts and transceivers disabled (`sys/power_saving.h:23-54`) while the relay stays driven (`main.c:71`) — GAP-49 |
| TSR-514 | Release firmware shall be built without `ALLOW_DEBUG`, with the LionDriver release key, and shall not contain the ALLOUTPUT mode, debug-only safety modes or debug-key acceptance; the build type shall be readable through the version request and recorded in the release record. | B‡ (+ CS) | FSR-01.10 | P-SW (build) | CFG | — | R | Not met by default: DEBUG + `ALLOW_DEBUG` unless `RELEASE` and `CERT` are set (`panda/SConscript:12-20`); debug modes `safety.h:413-422`; debug key `bootstub.c:66-71` (GAP-25) |
| TSR-515 | At every power-up, before the relay is first driven, the safety MCU shall run start-up tests of its safety mechanisms (flash CRC, RAM test of safety data regions, watchdog reset path at a defined interval, relay drive and readback, siren path) and stay in SS-S and report if any test fails. | B‡ | FSR-01.09, FSR-01.11, FSR-02.05 | P-SW, P-HW | ST | once per drive cycle | T-HIL, FI | Not implemented (latent-fault handling absent) |
| TSR-516 | If the SoC heartbeat is lost (TSR-407) or the envelope revokes authority for an RX or platform fault while authority was granted within the last 5 s, the safety MCU shall sound its own acoustic warning within ≤ 0.5 s of detection, without depending on SoC software. | B | FSR-02.05, FSR-06.05 | P-SW, P-HW | WRN | ≤ 0.5 s after detection | T-HIL | Partial: siren for 3 s after 5 s heartbeat loss (`main.c:169-171, 198-201`); siren path via codec over I2C on some boards, malfunction reported only (`drivers/fake_siren.h:38-52`); shared speaker with SoC audio to be analysed in DFA ([WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md)) |
| TSR-517 | Corruption of an approved actuation frame after the TX hook (copy into FDCAN message RAM, message RAM, FDCAN core, transceiver) shall be detected, e.g. by reading back the safety MCU's own transmitted frames on the car-side bus and comparing them with the approved frame, and a mismatch shall lead to TSR-502. | B‡ | FSR-01.09 | P-SW, P-HW | PLB | ≤ 2 frames / react per TSR-502 | A, FI | **Not implemented.** Packet XOR checked before the FDCAN load only (`drivers/fdcan.h:100`); no read-back after load (WP-A-04 SPF-02, SFMEA-17) |
| TSR-518 | The envelope shall supervise the transmit rate of each actuation message ID (`0x2E4`, `0x343`, `0x412`, and any other TX-whitelisted ID) against its nominal period and reject frames sent faster than the nominal rate plus a defined tolerance; persistent excess while authority is granted shall revoke authority and be reported. | B‡ | FSR-01.08, FSR-01.12 | P-SW | TMO | per frame; revoke ≤ 0.1 s | T-SIL, T-HIL | **Not implemented:** the TX hook checks content only; no per-ID TX rate check (`opendbc_repo/opendbc/safety/modes/toyota.h` TX hook; RX rate is TSR-403) |
| TSR-519 | The safety MCU shall have a documented interrupt-priority and execution-timing scheme: priorities assigned explicitly for every enabled interrupt; safety hooks, CAN TX and SoC command dispatch either moved out of interrupt context or bounded by measured WCET; and the worst-case latency of the periodic safety processing (timeouts, heartbeat, watchdog service) shown to meet the TSR-401/407/501 budgets under worst-case interrupt load. | B‡ | FSR-01.09, FSR-01.07 | P-SW, P-HW (cfg) | ISO | analysis; WCET measured on target | A, T-HIL | **Not implemented:** no `NVIC_SetPriority` outside the CMSIS header (all IRQs at priority 0); RX hook in the FDCAN interrupt (`drivers/fdcan.h:221, 245-252`); TX hook and control-request dispatch in the SPI DMA interrupt (`stm32h7/llspi.h:56-60`, `drivers/spi.h:143, 162`, `can_comms.h:97, 118`) (GAP-50) |

## 8. TSR-6xx Host-side (SoC) monitoring, DM and HMI

All TSR-6xx are allocated to the QM SoC. Those marked QM (B-sup) support an ASIL B or C FSR whose ASIL argument rests on the named envelope TSR.

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-601 | `selfdrived` shall classify faults as (i) untrusted command or input (loss or staleness of an input to the control law, model failure, CAN error, controls mismatch) → immediate disable, and (ii) trustworthy but degrading (thermal, storage, memory) → soft disable. Actuation on an input that has failed its alive or validity check shall end within ≤ 0.2 s. | QM (B-sup: TSR-407, TSR-408) | FSR-02.02, FSR-02.04, FSR-06.02 | SoC | FR | ≤ 0.2 s | T-SIL, FI | Not met: `commIssue` is SOFT_DISABLE (`selfdrive/selfdrived/events.py:853-856`), soft disable keeps actuating 3 s (`selfdrive/selfdrived/state.py:7-8`); alive allows 10 periods (`cereal/messaging/__init__.py:265`) (GAP-16). FM-03 in [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md) |
| TSR-602 | `controlsd` shall check the age of `modelV2`, `longitudinalPlan` and `carState` before use (≤ 2 nominal periods) and shall set `latActive`/`longActive` false and raise an event when an input is stale. | QM (B-sup: TSR-408) | FSR-02.02, FSR-06.01 | SoC | TMO | ≤ 0.1 s | T-SIL | Not met: no freshness check (`selfdrive/controls/controlsd.py:66` polls on `selfdriveState` only) (GAP-16) |
| TSR-603 | No diagnostic (`commIssue`, posenet, locationd, `modeldLagging`) shall be masked while the item is engaged, and the driving model shall not be switched while engaged. In the reference configuration the external big model (E-06) shall be absent and not loadable. | QM (B-sup) | FSR-02.02, FSR-06.01 | SoC | DES | — | R, T-SIL | Not met: masking during big-model load + 5 s (`selfdrive/selfdrived/selfdrived.py:382-384, 403, 457`); hot switch `selfdrive/modeld/modeld.py:411-419` (GAP-17). AIR-25, AIR-30 ([WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md)) |
| TSR-604 | Non-finite actuator commands shall be treated as a fault with immediate disable, not replaced silently. | QM (B-sup) | FSR-06.04 | SoC | FR | ≤ 1 frame | T-SIL | Not met: replaced by 0 and logged (`selfdrive/controls/controlsd.py:140-147`) (GAP-19) |
| TSR-605 | The SoC controller shall command with margin below every envelope limit: steering torque ≤ 90 % of τ_max(v), acceleration within [a_min + 0.2, a_max − 0.2] m/s² (proposed), lateral acceleration ≤ 3.0 m/s², lateral jerk ≤ 5 m/s³. | QM | FSR-01.14 | SoC | LIM | per frame | T-SIL | Partial: 3.0 m/s² and 5 m/s³ (`selfdrive/controls/lib/drive_helpers.py:9-14`); torque and accel limits equal to the envelope (`values.py:20, 39-47`) |
| TSR-606 | On every fault-induced transition to L2/L3 (FSC §12) the SoC shall give a visual and acoustic take-over request within ≤ 1 s of detection, with text that names the actual fault class. | QM (B-sup: TSR-516) | FSR-02.03, FSR-06.02 | SoC (HMI) | WRN | ≤ 1 s | T-HIL, T-VEH | Partial: alerts exist (`selfdrive/selfdrived/events.py:224-234`); `canError` shows "Unknown Vehicle Variant" (`events.py:928-936`) (GAP-19); timing not verified |
| TSR-607 | The SoC shall warn the driver when the EPS reports LKA unavailable or faulted (complements TSR-110). | QM (B-sup: TSR-110) | FSR-02.01 | SoC | WRN | ≤ 1 s | T-SIL, T-VEH | Implemented: `steerFaultTemporary/Permanent` → events with 1.5 s hysteresis (`selfdrive/car/car_events.py`, onboard review) |
| TSR-608 | Driver monitoring shall escalate warnings for an inattentive driver with the timing set in WP-C-08 §5 (baseline vision 5/8/13 s, wheel-touch 5/15/25 s). | QM | FSR-02.06 | SoC | WRN | per policy | T-SIL, T-VEH | Implemented: `selfdrive/monitoring/policy.py:31-36` |
| TSR-609 | The DM chain shall mark its output invalid when the cabin image or model output is missing or not credible, and an invalid DM output for > 2 s while engaged shall escalate to a take-over request. | QM | FSR-02.07 | SoC | PLB | ≤ 2 s | T-SIL, FI | Not met: `driverStateV2` always `valid=True` at source (`selfdrive/modeld/dmonitoringmodeld.py:99`) (GAP-21). AIR-15, AIR-27 |
| TSR-610 | DM demo mode (`IsDriverViewEnabled`) shall not be active while the item can engage. | QM | FSR-02.08 | SoC | CFG | — | R, T-SIL | Not met: `selfdrive/monitoring/dmonitoringd.py:26-38` (GAP-20) |
| TSR-611 | If the driver does not respond to the highest DM warning, the SoC shall decelerate, disengage and lock out re-engagement for 1/5/15/30 min. | QM | FSR-02.09 | SoC | FR | per policy | T-SIL, T-VEH | Implemented: `selfdrive/monitoring/policy.py:39-44`; `selfdrive/controls/controlsd.py:203-204` |
| TSR-612 | The wheel-touch fallback shall reset awareness only on a deliberate driver input above a defined threshold, not on any steering or gas input. | QM | FSR-02.07 | SoC | PLB | — | T-SIL | Not met: any steer/gas input resets (`selfdrive/monitoring/policy.py:334-335`) (GAP-21) |
| TSR-613 | Debug, joystick and maneuver modes, and the `lateralManeuverPlan` path to the actuator, shall be absent from reference-configuration builds. | QM (B-sup) | FSR-02.08, FSR-01.14 | SoC | CFG | — | R | Not met: `system/manager/process_config.py:34-47, 95-109`; `selfdrive/controls/controlsd.py:123-124` (GAP-20; WP-C-01 OI-5) |
| TSR-614 | `pandad` shall not forward `sendcan` messages older than 2 control periods (20 ms). | QM (B-sup: TSR-411) | FSR-01.08 | SoC | TMO | 20 ms | T-SIL | Not met: 1 s (`selfdrive/pandad/pandad.cc:78-79`) |
| TSR-615 | The SoC shall immediately disable on any panda fault flag, heartbeat-lost flag, rising `safetyTxBlocked` count while engaged, or SPI error burst reported in `pandaStates`. | QM (B-sup: TSR-502, TSR-108) | FSR-01.12, FSR-02.03 | SoC | FR | ≤ 0.2 s | T-SIL, FI | Partial: only `relayMalfunction` and `safetyRxChecksInvalid` react (`selfdrive/selfdrived/selfdrived.py:338-342`) |
| TSR-616 | Driving-model outputs shall be checked for non-finite values, range plausibility and age before use, per AIR-16, AIR-17 and AIR-25 of [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md). | QM | FSR-02.02, FSR-06.01 | SoC | PLB | per frame | T-SIL | Partial: non-finite check on the big model only (onboard review, `selfdrive/modeld/modeld.py:210-211`) (GAP-22) |
| TSR-617 | Excessive-actuation detection (longitudinal outside 2× ACCEL_MIN/MAX, lateral > 2× ISO lateral acceleration for > 0.25 s) shall be kept and shall latch until cleared offroad. | QM | FSR-01.14, FSR-06.04 | SoC | PLB | 0.25 s | T-SIL | Implemented: `selfdrive/selfdrived/helpers.py:12, 30, 41`; latch `selfdrive/selfdrived/selfdrived.py:305-310` |
| TSR-618 | A PCM-reported ACC fault shall cause immediate disable with a take-over request. | QM (B-sup) | FSR-06.03 | SoC | FR | ≤ 0.2 s | T-SIL | Implemented: `accFaulted` IMMEDIATE_DISABLE (`selfdrive/selfdrived/events.py:908`) |
| TSR-619 | `pandad` shall compare the panda-reported safety model, safety parameter and alternative experience with the release-record values and shall prevent engagement and raise an alert on mismatch (refines CSR-016 of [WP-S-07](WP-S-07-cybersecurity-requirements-architecture.md)). | QM (B-sup: TSR-512) | FSR-01.10 | SoC | PLB | before engagement; ≤ 1 s | T-SIL, T-HIL | Not implemented: `pandad` sets the values from `CarParams` and does not compare them with a reference (`selfdrive/pandad/panda_safety.cc:56-69`) |
| TSR-620 | The item shall not request the TOYOTA safety mode or allow engagement unless the ECU firmware versions read at start-up (EPS, engine, ABS, radar, camera) match the release record of the reference configuration; an unverified or mismatching firmware set shall keep the safety MCU in NOOUTPUT and inform the driver. The envelope cannot read ECU firmware itself, so the refusal rests on the SoC query plus the mode lock of TSR-512. | QM (B-sup: TSR-512, TSR-803) | FSR-01.10 | SoC | CFG | at start-up | T-SIL, T-VEH | Not implemented: fingerprinting accepts a fuzzy match and can be forced or skipped by environment (`opendbc_repo/opendbc/car/car_helpers.py:86-87, 144, 164`); no comparison with a release record (WP-A-03 ECU-FW row; TSR-803 is the procedural counterpart) |

## 9. TSR-7xx Stock PCS preservation and harness (SG-07, SG-01)

| ID | Requirement | ASIL | Parent | Alloc | SM | Timing | Verif | Impl (baseline) / GAP |
|---|---|---|---|---|---|---|---|---|
| TSR-701 | The harness orientation (normal, flipped, not connected) shall be detected before the relay is driven, and CAN routing and relay/ignition pin assignment shall follow it; loss or change of orientation while the relay is driven shall lead to SS-S. | B | FSR-07.03 | P-HW, HAR, P-SW | PLB | ≤ 1 s | T-HIL, FI | Partial: detection `drivers/harness.h:54-94`; re-init on change `main.c:131-140`; detection suspended while relay driven (`drivers/harness.h:59`). HWSR-701, 701a |
| TSR-702 | With the relay de-energised, the harness shall connect the forward camera to the vehicle CAN without any active component in the path. | B | FSR-07.03 | HAR | DES | continuous | A, T-HIL | Unverified (AOU-13). Comment only: `drivers/harness.h:106`. HWSR-702 |
| TSR-703 | Harness connectors shall be keyed and latched so that partial insertion is detected (not-connected status) or cannot occur. | B | FSR-07.03 | HAR | DES | — | A, R | Unknown. HWSR-703 |
| TSR-704 | The envelope shall forward every camera-side frame to the car side unchanged, except STEERING_LKA `0x2E4`, STEERING_LTA `0x191`, LKAS_HUD `0x412` and (openpilot longitudinal) ACC_CONTROL `0x343`, and shall forward every car-side frame to the camera side. | B | FSR-07.01 | P-SW | DES | continuous | T-SIL, T-HIL | Implemented: `safety.h:254-290`; `modes/toyota.h:6-36` (static blocking of `check_relay` messages); forwarding before RX validation `drivers/fdcan.h:199-221` (GAP-11) |
| TSR-705 | In the reference configuration the envelope shall not accept from the SoC any frame on the car-side bus that the stock PCS function uses or that only a DSU would send: PRE_COLLISION `0x283`, PRE_COLLISION_2 `0x344`, PCS_HUD `0x411`, and the DSU messages `0x2E6`, `0x2E7`, `0x33E`, `0x365`, `0x366`, `0x4CB` and the bus-1 DSU set; if any is kept for a documented reason, its content shall be restricted to the inactive value. | B | FSR-07.02 | P-SW | GATE | per frame | R, T-SIL | **Not met:** all are in the openpilot-longitudinal TX whitelist (`modes/toyota.h:19-32`); only `0x283` is content-checked (`modes/toyota.h:250-257`). Signal content of `0x344` (`_toyota_adas_standard.dbc:38-45`) includes PCS brake triggers. **GAP-42** (FSC FSR-07.02 finding). The DSU-only messages are an extension found here (NF-07) |
| TSR-706 | On SS-S, any MCU fault, MCU reset, loss of device power or harness supply, the relay shall return to the stock camera-to-vehicle connection. | B | FSR-07.03 | HAR, P-HW, P-SW | FR | ≤ 0.1 s after fault reaction | A, T-HIL, FI | Partial: SILENT/NOOUTPUT release the relay (`main.c:44-54`); power-loss behaviour unverified (AOU-13). **Not met for an MCU hang:** without IWDG the relay stays intercepting and forwarding stops, cutting the PCS path (GAP-43; closed by TSR-501 + TSR-502 + TSR-506 readback). HWSR-502, 502a, 506 |
| TSR-707 | Forwarded camera-side frames shall be delivered to the car side without loss and with a latency ≤ 1 ms (TBD from the PCS timing analysis) under worst-case bus and SPI load; forwarding queue overflow shall be detected and reported. | B | FSR-07.01 | P-SW | TMO, PLB | continuous | A, T-HIL | Not verified. Overflow counted (`drivers/can_common.h:165`, `main_comms.h:29`). SH-08 in [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md) |
| TSR-708 | PCS/AEB braking shall have priority over `0x343` requests in the PCM, and PCS shall work with the harness installed. (External measure.) | ext | FSR-07.04 | EXT | EXTM | — | T-VEH | Unverified (AOU-04R) |
| TSR-709 | The SoC shall inform the driver when the stock system reports an AEB or FCW event. | QM | FSR-07.05 | SoC | WRN | ≤ 0.2 s | T-SIL | Implemented: `stockAeb`, `stockFcw` (`selfdrive/car/car_events.py:120-123`) |
| TSR-710 | The envelope shall detect a relay malfunction (any `check_relay` control message seen on the car side after the relay transition window) and inhibit all actuation TX and forwarding. | B‡ | FSR-01.11 | P-SW | PLB, FR | detect: first offending frame after ≤ 1–2 s window / same frame | T-SIL, T-HIL | Implemented: `safety.h:211-220, 252, 268, 372-380`; reported `main.c:122-129`; host immediate disable `selfdrive/selfdrived/selfdrived.py:341-342`. Latching and readback per TSR-506 |

## 10. TSR-8xx Production, operation, service and decommissioning

Statements are summarised here; the full requirement text, rationale and links to the procedures of [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md), [WP-O-02](../09-production-operation/WP-O-02-operation-service-decommissioning.md) and [WP-O-03](../09-production-operation/WP-O-03-user-information-safety-warnings.md) are in [WP-S-06](WP-S-06-requirements-production-operation.md).

| ID | Requirement (summary) | ASIL | Parent | Alloc | Verif | Implemented by |
|---|---|---|---|---|---|---|
| TSR-801 | Only a released LionDriver baseline (software, AGNOS, model hashes) shall be installed | B‡ | SG-01…07 | OPS | R | WP-O-01 INS-15, INS-16, INS-18 |
| TSR-802 | Installed panda firmware shall be the release-signed, non-debug build recorded in the release record | B‡ | FSR-01.10 | OPS | R, T | INS-17 |
| TSR-803 | Vehicle ECU firmware versions shall equal the reference record before any engagement | B‡ | AOU-01…05 | OPS | R | INS-21 |
| TSR-804 | Safety mode, safety parameter and alternative experience shall be verified on the installed vehicle | B‡ | FSR-01.10 | OPS | R | INS-22, INS-23 |
| TSR-805 | Harness seating, relay intercept and PCS forwarding shall be verified at installation and after every relevant service | B | FSR-07.01, 07.03 | OPS | T | INS-11, INS-14, INS-27; SVC-04, SVC-05 |
| TSR-806 | The parameter set shall equal the release record (Experimental Mode, debug modes, DM demo, SSH) | QM (B-sup) | FSR-02.08 | OPS | R | INS-19; UPD-06 |
| TSR-807 | Device mounting and calibration shall be within the installation tolerance | QM (SOTIF) | AOU-08 | OPS | T | INS-09, INS-25 |
| TSR-808 | Vehicle service actions listed in WP-O-02 §4 shall trigger the defined re-verification before engagement | B‡ | AOU-01…05, 09 | OPS | R | SVC-01…SVC-11 |
| TSR-809 | Periodic re-verification (configuration, PCS preservation, harness) shall be performed at the defined intervals | B | SG-07, AOU-09 | OPS | R | PM-01…PM-04 |
| TSR-810 | Software updates shall follow the update policy (released baselines only, manual install until signed updates exist, re-verification) | B‡ | FSR-01.10 | OPS | R | UPD-01…UPD-08 |
| TSR-811 | Pre-drive checks shall be performed and engagement withheld on failure | QM (B-sup) | AOU-06, 09, 10 | OPS | R | OPS-01…OPS-07 |
| TSR-812 | User information and safety warnings shall be provided and acknowledged before first use | QM (B-sup) | AOU-06 | OPS | R | WP-O-03; INS-30 |
| TSR-813 | Field monitoring and incident reporting shall be operated for every installed item | QM | SG-01…07 | OPS | R | [WP-O-04](../09-production-operation/WP-O-04-field-monitoring.md) |
| TSR-814 | Decommissioning shall restore the stock camera path, verify stock TSS functions and remove data and keys | B | SG-07 | OPS | T, R | DEC-01…DEC-11 |
| TSR-815 | Only approved device/harness revisions with clean history shall be installed | B‡ | T-04 | OPS | R | INS-01…INS-04; ITS-03…ITS-05 |
| TSR-816 | Installation by a trained installer; complete, second-person-checked installation record | B‡ | ISO 26262-7 §5 | OPS | R | WP-O-01 §5 |
| TSR-817 | Item faults handled by replacement and quarantine, followed by full re-provisioning | B‡ | T-04 | OPS | R | ITS-01…ITS-05 |
| TSR-818 | Users informed of end of support with a date after which the release must not be engaged | QM | ISO/SAE 21434 §14 | OPS | R | WP-O-02 §7.3 |

## 11. New findings raised by this document

These are code facts found while writing the TSRs. They are registered in the [gap assessment](../00-assessment/gap-assessment.md) as GAP-46…GAP-49 (NF-02 → GAP-46, NF-04 → GAP-47, NF-01/03/06 → GAP-48, NF-05/07 → GAP-49; the last column gives the GAP ID). The SG-07 effect of `0xe7` in car mode (WP-A-04 SPF-08) is part of GAP-49; the ISR/priority finding behind TSR-519 is GAP-50.

| ID | Finding | Evidence | TSR |
|---|---|---|---|
| NF-01 | STEER_REQUEST = 1 with zero torque is accepted while lateral authority is not granted | `lateral.h:98-109` | TSR-105; GAP-48 |
| NF-02 | Rejecting a `0x2E4` frame does not command zero torque; the EPS sees a drop-out whose handling (≈2 s per code comment) is unverified. Safe state SS-L is therefore not guaranteed by the envelope alone | `drivers/can_common.h:161-176`; `carstate.py:15-16` | TSR-109; GAP-46 |
| NF-03 | ACC_CONTROL fields other than ACCEL_CMD (PERMIT_BRAKING, RELEASE_STANDSTILL, CANCEL_REQ, ACCEL_CMD_ALT) are not checked in openpilot-longitudinal mode | `modes/toyota.h:216-241` | TSR-207; GAP-48 |
| NF-04 | SPI length fields and control-request indices from the SoC are not bounds-checked before DMA/array access in the safety MCU | `drivers/spi.h:115-116, 150, 233`; `main_comms.h:262-264` | TSR-412; GAP-47 |
| NF-05 | Many control requests that change CAN or relay configuration (`0xe5` loopback, `0xde`, `0xf9`, `0xfc`, `0xe8`, `0xdb`, `0xe6`, `0xe7`, `0xf1`) are accepted in car safety modes in release builds; GAP-09 names only `0xdc` and `0xc5` | `main_comms.h:218-314` | TSR-513; GAP-49 |
| NF-06 | A safety-mode change (`0xdc`) clears the relay-malfunction latch | `safety.h:427, 459` | TSR-506, TSR-512; GAP-48 |
| NF-07 | Besides `0x344`/`0x411` (GAP-42), the openpilot-longitudinal TX whitelist also admits DSU-only messages (`0x2E6`, `0x2E7`, `0x33E`, `0x365`, `0x366`, `0x4CB`, bus-1 set) without content check, although the reference car has no DSU | `modes/toyota.h:21-26` | TSR-705; GAP-49 |

## 12. Traceability

### 12.1 TSR → FSR

| TSR | Parent FSR(s) | SG |
|---|---|---|
| TSR-101, 102 | FSR-01.01 | SG-01 |
| TSR-103 | FSR-01.02 | SG-01 |
| TSR-104 | FSR-01.03 | SG-01 |
| TSR-105, 106, 107 | FSR-01.04 | SG-01 |
| TSR-108 | FSR-01.12 | SG-01 |
| TSR-109 | FSR-01.12, 01.13, 02.04, 05.01 | SG-01, SG-02, SG-05 |
| TSR-110 | FSR-02.01 | SG-02 (SG-01) |
| TSR-111 | FSR-01.13 | SG-01, SG-05 |
| TSR-201 | FSR-03.01 | SG-03 |
| TSR-202 | FSR-04.01 | SG-04 |
| TSR-203 | FSR-03.02, 04.04, 05.04 | SG-03, SG-04, SG-05 |
| TSR-204 | FSR-03.03 | SG-03 |
| TSR-205 | FSR-04.02 | SG-04 |
| TSR-206 | FSR-03.05, 04.03 | SG-03, SG-04 |
| TSR-207 | FSR-03.02, 03.05 | SG-03, SG-04 |
| TSR-208 | FSR-03.06, 04.03 | SG-03, SG-04 |
| TSR-301 | FSR-01.05, 05.02 | SG-01, SG-03, SG-04, SG-05 |
| TSR-302 | FSR-05.01 | SG-05 |
| TSR-303 | FSR-03.05 | SG-03 |
| TSR-304 | FSR-05.03 | SG-05, SG-01 |
| TSR-305 | FSR-04.04, 05.04 | SG-04, SG-05 |
| TSR-306 | FSR-01.05, 01.06 | SG-01, SG-03, SG-04 |
| TSR-307 | FSR-05.06, 01.07 | SG-01, SG-05 |
| TSR-308 | FSR-05.06 | SG-02, SG-05 |
| TSR-309 | FSR-05.05 | SG-02, SG-05 |
| TSR-310 | FSR-05.07 | SG-05 |
| TSR-311 | FSR-01.05 | SG-01 |
| TSR-401…406 | FSR-01.06 (406 also 01.12; 405 also 05.01) | SG-01, SG-03, SG-04, SG-05 |
| TSR-407, 408, 409 | FSR-01.07 | SG-01…SG-04, SG-06 |
| TSR-410…413 | FSR-01.08 (412 also 01.10) | SG-01, SG-03, SG-04 |
| TSR-501, 503, 504, 505, 507, 509 | FSR-01.09 | all |
| TSR-502 | FSR-01.09, 07.03 | all |
| TSR-506 | FSR-01.11, 07.03 | SG-01, SG-07 |
| TSR-508 | FSR-01.09, 01.12 | SG-01, SG-03, SG-04 |
| TSR-510 | FSR-07.03 | SG-07 |
| TSR-511…514 | FSR-01.10 | SG-01, SG-03, SG-04, SG-05, SG-07 |
| TSR-515 | FSR-01.09, 01.11, 02.05 | all |
| TSR-516 | FSR-02.05, 06.05 | SG-02, SG-06 |
| TSR-517, 519 | FSR-01.09 (519 also 01.07) | all |
| TSR-518 | FSR-01.08, 01.12 | SG-01, SG-03, SG-04 |
| TSR-601 | FSR-02.02, 02.04, 06.02 | SG-02, SG-06 |
| TSR-602, 603, 616 | FSR-02.02, 06.01 | SG-02, SG-06 |
| TSR-604 | FSR-06.04 | SG-06 |
| TSR-605 | FSR-01.14 | SG-01 |
| TSR-606 | FSR-02.03, 06.02 | SG-02, SG-06 |
| TSR-607 | FSR-02.01 | SG-02 |
| TSR-608…612 | FSR-02.06…02.09 | SG-02, SG-06 |
| TSR-613 | FSR-02.08, 01.14 | SG-01, SG-02 |
| TSR-614 | FSR-01.08 | SG-01 |
| TSR-615 | FSR-01.12, 02.03 | SG-01, SG-02 |
| TSR-617 | FSR-01.14, 06.04 | SG-01, SG-03, SG-04 |
| TSR-618 | FSR-06.03 | SG-06 |
| TSR-619, 620 | FSR-01.10 | SG-01, SG-03, SG-04, SG-05, SG-07 |
| TSR-701, 702, 703, 706 | FSR-07.03 | SG-07 |
| TSR-704, 707 | FSR-07.01 | SG-07 |
| TSR-705 | FSR-07.02 | SG-07 |
| TSR-708 | FSR-07.04 | SG-07 |
| TSR-709 | FSR-07.05 | SG-07 |
| TSR-710 | FSR-01.11 | SG-01, SG-07 |
| TSR-801…818 | ISO 26262-4 §6 requirements for production/operation; AoUs as listed in §10 | all |

### 12.2 FSR coverage check (FSR → TSR)

| FSR | TSRs | FSR | TSRs |
|---|---|---|---|
| FSR-01.01 | 101, 102 | FSR-03.01 | 201 |
| FSR-01.02 | 103 | FSR-03.02 | 203, 207 |
| FSR-01.03 | 104 | FSR-03.03 | 204 |
| FSR-01.04 | 105, 106, 107 | FSR-03.04 | shared: 301, 306, 401–413, 501–515 |
| FSR-01.05 | 301, 306, 311 | FSR-03.05 | 206, 207, 303 |
| FSR-01.06 | 401–406, 306 | FSR-03.06 | 208 |
| FSR-01.07 | 407, 408, 409, 307 | FSR-04.01 | 202 |
| FSR-01.08 | 410–413, 614 | FSR-04.02 | 205 |
| FSR-01.09 | 501–505, 507–509, 515 | FSR-04.03 | 206, 208 |
| FSR-01.10 | 511–514, 412 | FSR-04.04 | 203, 305 |
| FSR-01.11 | 506, 710, 515 | FSR-05.01 | 302, 109, 405 |
| FSR-01.12 | 108, 109, 406, 508, 615 | FSR-05.02 | 301 |
| FSR-01.13 | 111, 109 | FSR-05.03 | 304 |
| FSR-01.14 | 605, 613, 617 | FSR-05.04 | 203, 305 |
| FSR-02.01 | 110, 607 | FSR-05.05 | 309 |
| FSR-02.02 | 601, 602, 603, 616 | FSR-05.06 | 307, 308 |
| FSR-02.03 | 606, 615 | FSR-05.07 | 310 |
| FSR-02.04 | 109, 601 | FSR-06.01 | 602, 603, 616 |
| FSR-02.05 | 516, 515 | FSR-06.02 | 601, 606 |
| FSR-02.06 | 608 | FSR-06.03 | 618 |
| FSR-02.07 | 609, 612 | FSR-06.04 | 604, 617 |
| FSR-02.08 | 610, 613 | FSR-06.05 | 516, 608–611 |
| FSR-02.09 | 611 | FSR-07.01 | 704, 707 |
| | | FSR-07.02 | 705 |
| | | FSR-07.03 | 502, 506, 510, 701, 702, 703, 706 |
| | | FSR-07.04 | 708 |
| | | FSR-07.05 | 709 |

Every FSR has at least one TSR. Machine-readable entries go to [`trace/`](../trace/) per [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) (OI-6).

### 12.3 TSRs that require code or hardware changes (summary)

| Priority | TSR | Change | GAP / NF |
|---|---|---|---|
| 1 | TSR-501, 502 | IWDG; fault → safe state, latching | GAP-07, GAP-08 |
| 2 | TSR-512, 513, 511, 619 | Lock safety mode/param/alternative experience; gate debug/config requests (incl. `0xe7`, `0xd1`/1, `0xd8`); boot integrity; SoC-side cross-check | GAP-09, GAP-38, GAP-49 (NF-05) |
| 2a | TSR-517, 518, 519 | Post-load TX integrity; per-ID TX rate supervision; interrupt-priority/ISR timing scheme | GAP-50; WP-A-04 SPF-02 |
| 3 | TSR-401, 407, 408, 307 | FTTI-consistent RX, heartbeat and command timeouts | GAP-06, GAP-10 |
| 4 | TSR-109, 108 | Active zero-torque safe state; latch on violation | NF-02 |
| 5 | TSR-304, 110 | Driver torque and EPS status in the envelope | GAP-02, GAP-03 |
| 6 | TSR-102, 204, 205 | Speed-dependent torque limit; jerk limits | GAP-04 |
| 7 | TSR-403…405 | RX plausibility for counter-less messages | GAP-01 |
| 8 | TSR-410…412 | SPI CRC, sequence counter, bounds checks | GAP-10, NF-04 |
| 9 | TSR-705, 706 | Remove PCS/DSU messages from the TX whitelist; relay released on MCU hang | GAP-42, GAP-43, NF-07 |
| 10 | TSR-601…603 | Fault classification, freshness, no masking | GAP-16, GAP-17 |

## 13. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Closed: NF-01…NF-07 registered as GAP-46…GAP-49 (the FSR-07.02 finding is GAP-42) | Safety engineer | G2 |
| OI-2 | Replace B‡ with the final ASIL after the HARA re-rating of SG-01 (FSC OI-2); WP-H-01 now uses the same B‡ notation, update both together | Safety manager | G2 |
| OI-3 | Derive the τ_max(v) table, Δ values, a_max/a_min, j_up/j_down, T_ovr from vehicle characterisation and controllability tests; check the speed-direction conservatism of `lateral.h:68` against the table | Safety engineer | G2 |
| OI-4 | Decide latching on TX violation (TSR-108) vs upstream recovery behaviour; record in WP-C-04 | Maintainer | G2 |
| OI-5 | Confirm availability and timing of `0x262`, `0x1D3`, `0xB4` on the reference vehicle and set the cross-check tolerances (TSR-110, 401, 405) from logs | SW lead | G2 |
| OI-6 | Create machine-readable TSR records and the FSR→TSR→SWSR/HWSR links in `trace/` | Safety engineer | G2 |
| OI-7 | Specify the SPI CRC polynomial and residual-error target jointly with WP-S-05 and WP-S-07 (CRC is not a security measure) | SW lead | G3 |
| OI-8 | Confirm whether the reference device is the "tres" or "cuatro" board; TSR-516 siren path differs | HW lead | G1 |
