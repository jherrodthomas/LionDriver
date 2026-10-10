# WP-W-02 Software Safety Requirements Specification

| Field | Value |
|---|---|
| Work product | WP-W-02 Software safety requirements specification |
| Standard reference | ISO 26262-6:2018 §6 (specification of software safety requirements, incl. HSI refinement); ISO 26262-8:2018 §6 (requirement attributes and management); ISO 26262-4:2018 §6 (HSI, by reference to WP-S-05); ASPICE 4.0 SWE.1 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Envelope software (E-03a/E-03b): B‡ (ASIL D applies until SG-01 is re-rated, [WP-S-02 §2.1](../03-system/WP-S-02-technical-safety-requirements.md)) and C (SG-03…SG-05, longitudinal and release); host software (E-01): QM / QM (B-sup) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); envelope SWSRs additionally I2 per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document refines the technical safety requirements (TSRs) of [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) that are allocated to software into software safety requirements (SWSRs). It covers:

- the safety envelope software on the panda STM32H7: opendbc safety core and Toyota mode (E-03a) and the panda firmware paths they rely on (E-03b), allocated at the envelope ASIL;
- the host (SoC, E-01) software requirements that S-02 allocates to the SoC as QM or QM (B-sup), including QM behaviour that affects safety (stale-input handling, diagnostic masking during the Chestnut big-model path, debug modes);
- software-hardware interface requirements that refine [WP-S-05](../03-system/WP-S-05-hsi-specification.md) and pair with the HWSRs of [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md).

Requirements are back-filled from the baseline code where the code already implements them (tailoring T-03, [WP-M-01](../01-management/WP-M-01-assurance-strategy.md)) and written as new requirements where it does not. The "Baseline" column states what the code does at the baseline. It is **not** verification evidence. All SWSRs have status `proposed` ([WP-P-06 §2](../07-supporting/WP-P-06-requirements-management-traceability.md)).

Architecture elements used in the allocation column are defined in [WP-W-03](WP-W-03-software-architecture.md) §3. Unit IDs (U-xxx) match [WP-W-06 §2](WP-W-06-software-unit-verification.md) and [WP-W-05](WP-W-05-software-unit-design.md).

## 2. Conventions

### 2.1 Identifiers

- `SWSR-nnn` refines `TSR-nnn` one-to-one. Additional SWSRs refining the same TSR get a suffix letter (`SWSR-101a`).
- Host-side refinements of a TSR whose envelope part is also an SWSR get the suffix `h` (`SWSR-409h`).
- SW-HW interface requirements are SWSRs with a suffix and are listed again in §11 with their HSI and HWSR partners.

### 2.2 Attributes

| Attribute | Values |
|---|---|
| ASIL | As in WP-S-02 §2.1: **B‡** (target B, ASIL D until SG-01 re-rating), **C**, **B**, **QM (B-sup)**, **QM**. A child never has a lower ASIL than its parent (WP-P-06 K5). [WP-W-01](WP-W-01-software-development-environment-guidelines.md) and [WP-W-06](WP-W-06-software-unit-verification.md) say "ASIL D provisional" for the same thing |
| Allocation | Element name from WP-W-03 §3 (e.g. `panda.safety.lateral`) and unit ID |
| Verification | **R** review/inspection, **A** analysis, **UT** unit test on host `libsafety`/`libpanda` ([WP-W-06](WP-W-06-software-unit-verification.md), VS-UV), **IT** software integration test ([WP-W-07](WP-W-07-software-integration-verification.md), VS-SWI), **HIL** embedded software test on target ([WP-W-08](WP-W-08-embedded-software-testing.md), VS-SWQ), **FI** fault injection, **RP** drive-log replay, **VT** vehicle test |
| Acceptance | Measurable pass criterion. "raw" = CAN raw units as decoded by the envelope |
| Baseline | `Impl` (implemented as stated), `Partial`, `Not impl`, with file:line and GAP |

Paths: `safety.h`, `lateral.h`, `longitudinal.h`, `helpers.h`, `declarations.h`, `can.h`, `modes/toyota.h` are under `opendbc_repo/opendbc/safety/`. `main.c`, `main_comms.h`, `can_comms.h`, `early_init.h`, `bootstub.c`, `drivers/*`, `sys/*`, `stm32h7/*` are under `panda/board/`. Host paths are under `openpilot/` unless stated; Toyota port files under `opendbc_repo/opendbc/car/toyota/`.

### 2.3 General software safety requirements (all E-03 SWSRs)

These apply to every SWSR allocated to E-03 and are not repeated per row. They come from [WP-W-01 §5–§6](WP-W-01-software-development-environment-guidelines.md).

| ID | Requirement | Source |
|---|---|---|
| G-01 | Every limit, threshold and timeout used by an E-03 SWSR shall be a named constant with physical unit, raw scale and a `@req SWSR-nnn` tag at its definition | W-01 C-13, [WP-W-09](WP-W-09-configuration-calibration-data.md) DVR-03, GAP-14 |
| G-02 | Every value received from the SoC or the vehicle bus shall be range-checked before use | W-01 ENV-R-08 |
| G-03 | Every detected fault shall drive a defined reaction, not only a report | W-01 ENV-R-11, GAP-08 |
| G-04 | Data shared between interrupt contexts shall be listed in WP-W-03 §6.3 and accessed only under the documented scheme | W-01 ENV-R-12 |
| G-05 | The release configuration (no `ALLOW_DEBUG`) is the configuration that is verified | GAP-41 |

## 3. SWSR-1xx Lateral actuation envelope

Refines TSR-101…110. All allocated to E-03a. Parent SGs: SG-01, SG-02, SG-05.

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-101 | The Toyota TX hook shall reject every STEERING_LKA (`0x2E4`, bus 0) frame whose decoded STEER_TORQUE_CMD magnitude exceeds τ_max, where τ_max is 1500 raw until SWSR-102 is implemented. | B‡ | TSR-101 | `panda.safety.lateral` (U-SAF-LAT), `panda.safety.toyota` (U-SAF-TOY) | UT, HIL | \|τ\| = τ_max accepted, τ_max + 1 rejected, both signs, extreme int16 rejected | Impl: `modes/toyota.h:173`, check `lateral.h:73-74`. No physical rationale (GAP-04) |
| SWSR-101a | The Toyota TX hook shall decode `0x2E4` as STEER_REQUEST = bit 0 and STEER_TORQUE_CMD = signed 16-bit from data bytes 1–2 (big-endian), and shall evaluate it only for frames on bus 0 with length 5. | B‡ | TSR-101, TSR-107 | U-SAF-TOY | UT, R | Decoding matches the DBC for all 2^16 torque values; other lengths not whitelisted | Impl: `modes/toyota.h:11, 322-325`; length match `helpers.h:60-64` |
| SWSR-102 | When a speed-dependent bound is configured, the lateral check shall use τ_max(v) from the calibration table CD-22 and the speed value that yields the smaller bound under speed uncertainty. | B‡ | TSR-102 | U-SAF-LAT, U-SAF-TOY, data CD-22 | UT, A, VT | Bound at every breakpoint and midpoint equals the table; uncertainty direction verified against the table shape | Not impl: `dynamic_max_torque` unset for Toyota (`modes/toyota.h:172-186`); mechanism `lateral.h:66-71` uses `vehicle_speed.min − 1 m/s`, conservative only for increasing tables; `struct lookup_t` holds 3 breakpoints only (`declarations.h`) (GAP-04, WP-S-02 OI-3) |
| SWSR-102a | The τ_max(v) table shall be checked at build time for monotonic speed breakpoints and values within [0, 1500] raw; a failed check shall fail the build. | B‡ | TSR-102 | build of `panda.safety.toyota` | R, A | Build fails on a non-monotonic or out-of-range table | Not impl; [WP-W-09](WP-W-09-configuration-calibration-data.md) DVR-22 |
| SWSR-103 | The lateral check shall reject a `0x2E4` frame whose torque magnitude increases by more than Δ_up = 15 raw, or decreases by more than Δ_down = 25 raw, relative to the last accepted torque. | B‡ | TSR-103 | U-SAF-LAT | UT, HIL | Violation exactly at Δ + 1 raw for up and down, both signs | Impl: `modes/toyota.h:174-175`; `lateral.h:14-19` (inside `dist_to_meas_check`). Values without rationale (GAP-04) |
| SWSR-103a | The lateral check shall reject a `0x2E4` frame whose torque differs by more than 450 raw from the reference torque stored at the start of the current 250 ms window, and shall restart the window after 250 ms. | B‡ | TSR-103 | U-SAF-LAT | UT, HIL | Rejection at 451 raw; window restart at 250 ms with timer resolution 1 µs | Impl: `modes/toyota.h:177`; `lateral.h:49-57, 87-95`; `MAX_RT_INTERVAL` `declarations.h:71` |
| SWSR-104 | The lateral check shall reject a `0x2E4` frame whose torque exceeds the maximum (or is below the minimum) of the last 6 scaled EPS motor-torque samples widened by 1 raw by more than Δ_meas = 350 raw, with the downward-rate exception of the baseline algorithm. | B‡ | TSR-104 | U-SAF-LAT, U-SAF-TOY | UT, HIL | Rejection at meas.max + 1 + 351 raw; window of exactly 6 samples | Impl: `modes/toyota.h:98-111, 176`; `lateral.h:10-23, 82-83`; `MAX_SAMPLE_VALS` `declarations.h:68` |
| SWSR-104a | The EPS torque scale factor used by SWSR-104 shall be the reference value 73 compiled into the firmware; a safety parameter carrying a different factor shall be rejected per SWSR-512. | B‡ | TSR-104, TSR-512 | U-SAF-TOY | UT, HIL | Only `param & 0xFF == 73` accepted in the reference build | Not impl: any 0–255 accepted (`modes/toyota.h:383`) (GAP-44, GAP-09) |
| SWSR-105 | While lateral authority is not granted, the lateral check shall reject every `0x2E4` frame with non-zero torque or with STEER_REQUEST = 1. | B‡ | TSR-105 | U-SAF-LAT | UT, HIL | All four combinations of (torque≠0, request) rejected except (0, 0) | Partial: non-zero torque rejected (`lateral.h:98-101`); request = 1 with zero torque accepted (`lateral.h:105`) (GAP-48) |
| SWSR-106 | While authority is granted, the lateral check shall accept STEER_REQUEST = 0 with non-zero torque for at most 1 consecutive frame, only after ≥ 17 consecutive valid frames and ≥ 162 ms after the previous such frame. | B‡ | TSR-106 | U-SAF-LAT | UT | Boundary at 16/17 frames, 2 consecutive cuts, 161/162 ms | Impl: `modes/toyota.h:182-185`; `lateral.h:111-138` |
| SWSR-107 | In the LKA configuration the Toyota TX hook shall reject any STEERING_LTA (`0x191`) frame with STEER_REQUEST, STEER_REQUEST_2, a non-zero angle command or a non-zero TORQUE_WIND_DOWN. | B‡ | TSR-107 | U-SAF-TOY | UT | Each field set alone → rejected | Impl: `modes/toyota.h:260-273` |
| SWSR-108 | If a `0x2E4` frame is rejected while lateral authority is granted, the envelope shall clear lateral authority in the same call and keep it cleared until the next valid engagement per SWSR-301. | B‡ | TSR-108 | U-SAF-LAT, `panda.safety.core` (U-SAF-CORE) | UT, FI | `controls_allowed` false after the first violating frame; no frame accepted until a new PCM rising edge | Not impl: frame dropped and limiter state reset (`lateral.h:140-148`), `controls_allowed` unchanged (WP-S-02 OI-4) |
| SWSR-108a | The envelope shall record the cause of every authority revocation as a reason code (at least: TX violation, RX checksum, RX timeout, RX plausibility, brake, cruise off, heartbeat, command stall, platform fault) and report the latest code and a per-cause counter in the health packet. | B‡ | TSR-108, TSR-406 | U-SAF-CORE, `panda.comms` (U-PND-COMMS) | UT, HIL | Each cause produces its distinct code in `0xd2` health within one health period | Not impl: only `safety_tx_blocked` count and one RX-invalid flag (`main_comms.h:23, 27`); interface change in [WP-S-05 §4.2](../03-system/WP-S-05-hsi-specification.md) |
| SWSR-109 | When the envelope rejects a `0x2E4` frame, it shall transmit in its place a `0x2E4` frame with torque 0, STEER_REQUEST 0, the message counter continuing the SoC sequence and a valid Toyota checksum. | B‡ | TSR-109 | U-SAF-TOY, `panda.drivers.fdcan` (U-PND-FDCAN) | UT, HIL, VT | Substitute frame on bus 0 within one frame period of the rejected frame; EPS torque at zero ≤ 0.1 s (VT, WP-S-04 M-02) | Not impl: rejected frame is only counted and returned to the SoC (`drivers/can_common.h:161-176`) (GAP-46) |
| SWSR-109a | After lateral authority is revoked for a reason that stops SoC frames (heartbeat loss, command stall, platform fault), the envelope shall transmit zero-torque `0x2E4` frames autonomously at 100 Hz until the EPS reports LKA inactive or for 1 s, whichever is earlier, unless the relay is released. | B‡ | TSR-109, TSR-408 | `panda.main.safety_task` (U-PND-MAIN), U-SAF-TOY | HIL, FI, VT | Zero frames present on bus 0 from ≤ 10 ms after revocation | Not impl; needs the periodic task of SWSR-401a and a design decision on frame ownership (OI-3) |
| SWSR-110 | The Toyota RX configuration shall include EPS_STATUS (`0x262`) with checksum and timeout supervision, and while lateral authority is granted the envelope shall revoke it when LKA_STATE is in the confirmed fault set or `0x262` times out. | B (SG-02); B‡ (SG-01) | TSR-110 | U-SAF-TOY, U-SAF-CORE | UT, RP, VT | Revocation within 1 frame of a fault code; fault set confirmed on reference EPS logs | Not impl: host only (`carstate.py:122-127`, codes `:19-22`); not in RX checks (`modes/toyota.h:39-46`) (GAP-03) |

## 4. SWSR-2xx Longitudinal envelope

Refines TSR-201…207. E-03a. Parent SGs: SG-03, SG-04, SG-05.

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-201 | The Toyota TX hook shall reject every ACC_CONTROL (`0x343`, bus 0) frame whose ACCEL_CMD exceeds a_max = 2000 raw (+2.0 m/s²). | C | TSR-201 | `panda.safety.longitudinal` (U-SAF-LONG), U-SAF-TOY | UT, HIL | 2000 accepted, 2001 rejected | Impl: `modes/toyota.h:207-210, 225`; `longitudinal.h:8-12` (GAP-04) |
| SWSR-201a | The Toyota TX hook shall decode ACCEL_CMD as signed 16-bit from data bytes 0–1 (big-endian, 0.001 m/s² per raw). | C | TSR-201, TSR-202 | U-SAF-TOY | UT, R | Decoding matches DBC over full range | Impl: `modes/toyota.h:217-218` |
| SWSR-202 | The Toyota TX hook shall reject every `0x343` frame whose ACCEL_CMD is below a_min = −3500 raw (−3.5 m/s²). | C | TSR-202 | U-SAF-LONG, U-SAF-TOY | UT, HIL | −3500 accepted, −3501 rejected | Impl: `modes/toyota.h:209` |
| SWSR-203 | While longitudinal authority is not granted (not engaged, or gas pressed in the previous RX frame), the TX hook shall accept `0x343` only with ACCEL_CMD equal to the inactive value 0, defined as a named constant. | C | TSR-203 | U-SAF-LONG | UT | Any non-zero value rejected in each non-granted state | Impl: `longitudinal.h:3-12`; inactive value is the implicit zero-initialised field of `TOYOTA_LONG_LIMITS` (`modes/toyota.h:207-210`) — make explicit (G-01) |
| SWSR-204 | The TX hook shall reject a `0x343` frame whose ACCEL_CMD increases relative to the last accepted value faster than j_up (raw per frame; 0 m/s² taken as last value at engagement). | C | TSR-204 | U-SAF-LONG | UT, VT | Rejection at j_up + 1 raw per frame | Not impl (GAP-04); host wind-up only (`carcontroller.py:21`) |
| SWSR-205 | The TX hook shall reject a `0x343` frame whose ACCEL_CMD decreases faster than j_down. | C | TSR-205 | U-SAF-LONG | UT, VT | Rejection at j_down + 1 raw per frame | Not impl (GAP-04); host only (`carcontroller.py:22`) |
| SWSR-206 | If vehicle characterisation does not show a bounded PCM response to a step to the inactive value, the TX hook shall, for at most 1 s after revocation, accept `0x343` values that move monotonically towards 0 at no more than j_down/j_up. | C | TSR-206 | U-SAF-LONG | UT, VT | Wind-down accepted, any increase in magnitude rejected, all non-zero rejected after 1 s | Not impl; decision depends on WP-S-04 M-03 (AOU-05R) |
| SWSR-207 | The TX hook shall check PERMIT_BRAKING, CANCEL_REQ, RELEASE_STANDSTILL and ACCEL_CMD_ALT of `0x343` against the values allowed in the current authority state; without authority, only frames that request no acceleration, no braking and no standstill release shall pass. | C | TSR-207 | U-SAF-TOY | UT | Each field set alone without authority → rejected | Partial: only ACCEL_CMD checked (`modes/toyota.h:216-241`) (GAP-48) |

## 5. SWSR-3xx Engagement, disengagement and driver override

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-301 | The envelope shall set authority only on a rising edge of PCM_CRUISE (`0x1D2`) CRUISE_ACTIVE (bit 5) and clear it in the RX call in which CRUISE_ACTIVE = 0 is received. | B‡ | TSR-301 | U-SAF-CORE, U-SAF-TOY | UT, HIL | State table of WP-W-05 §5.2 fully covered | Impl: `safety.h:518-527`; `modes/toyota.h:143-146` |
| SWSR-302 | The envelope shall clear authority when BRAKE_PRESSED (`0x226` bit 37) rises, or is set while any wheel speed is non-zero. | C | TSR-302 | U-SAF-CORE, U-SAF-TOY | UT, HIL | Clear in the same RX call | Impl: `safety.h:350-357`; `modes/toyota.h:148-150, 157-168`. `0x226` without checksum (GAP-01) → SWSR-405 |
| SWSR-303h | `card`/Toyota carcontroller shall set CANCEL_REQ in ACC_CONTROL on every fault-induced disengagement with openpilot longitudinal. | QM (B-sup) | TSR-303 | `host.card` | UT, VT | CANCEL_REQ = 1 within 0.1 s | Impl: `carcontroller.py:253-254` |
| SWSR-304 | The lateral check shall reject `0x2E4` frames that increase torque opposing a driver torque beyond the driver allowance, using the last 6 STEER_TORQUE_DRIVER samples of `0x260`. | C (SG-05); B‡ | TSR-304 | U-SAF-LAT, U-SAF-TOY | UT, VT | Boundary at allowance ± 1 raw | Not impl on LKA path: Toyota uses `TorqueMotorLimited` (`modes/toyota.h:178`); driver samples used for LTA only (`:113-116, 294-298`); `driver_limit_check` exists (`lateral.h:26-46`) (GAP-02) |
| SWSR-304a | When \|driver torque\| exceeds T_ovr for longer than t_ovr while lateral authority is granted, the envelope shall clear lateral authority (via `steering_disengage`). | C (SG-05); B‡ | TSR-304 | U-SAF-TOY, U-SAF-CORE | UT, VT | Clear at t_ovr + 1 frame; values from WP-C-08 | Not impl: `steering_disengage` edge handling exists (`safety.h:365-369`), not set by Toyota (GAP-02) |
| SWSR-305 | While GAS_RELEASED (`0x1D2` bit 4) = 0 the envelope shall treat longitudinal authority as not granted and shall not clear lateral authority. | C | TSR-305 | U-SAF-TOY, U-SAF-LONG | UT | Lateral accepted, `0x343` non-inactive rejected while gas pressed | Impl: `modes/toyota.h:146`; `longitudinal.h:3-5` |
| SWSR-306 | The envelope shall not set authority on a PCM rising edge while any RX check (checksum, timeout, rate, frozen, cross-check, quality) of the configured RX set is failed or has not yet been evaluated since its last frame. | B‡ | TSR-306 | U-SAF-CORE | UT, FI | Rising edge ignored while any message lags > 5 periods | Partial: timeouts only evaluated in 1 Hz `safety_tick` (`safety.h:321-344`) (GAP-06) |
| SWSR-307 | When authority is granted and the SoC heartbeat reports "not engaged" for > 0.3 s, the envelope shall clear authority. | B‡ | TSR-307(a) | U-PND-MAIN | UT, HIL | Clear within 0.3 s + one task period | Not met: 3 consecutive 1 Hz ticks (`main.c:181-189`) (GAP-06) |
| SWSR-307h | `selfdrived` shall immediately disable when the panda-reported authority differs from its engaged state for > 0.3 s. | QM (B-sup) | TSR-307(b) | `host.selfdrived` | UT | Event within 30 frames | Not met: 200 frames (`selfdrive/selfdrived/selfdrived.py:338, 503-510`) |
| SWSR-308h | If PCM cruise is active while not engaged, or engaged while PCM cruise is inactive, for > 1 s, `selfdrived` shall warn and `card` shall request ACC cancel. | QM (B-sup) | TSR-308 | `host.selfdrived`, `host.card` | UT | Warning and cancel within 1 s | Not met: 6 s, reaction commented out (`selfdrived.py:420-422`, `events.py:458-460`) (GAP-19) |
| SWSR-309 | `controls_allowed` shall be set true only by the PCM rising-edge logic of SWSR-301; no comms handler, heartbeat or mode-setting path shall set it true. | C | TSR-309 | U-SAF-CORE, U-PND-COMMS | R, A | Code inspection: single write of `true` | Impl: only write of `true` is `safety.h:524` (in E-03 code; test harness excepted) |
| SWSR-311 | Authority shall be false and all limiter, sample and edge state reset at MCU start-up and on every safety-mode change. | B‡ | TSR-311 | U-SAF-CORE | UT | All state variables of WP-W-05 §5.1 at reset values after `set_safety_hooks` | Impl: `safety.h:57, 425-460` |

## 6. SWSR-4xx Communication integrity

### 6.1 Vehicle CAN RX

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-401 | For every message in the Toyota RX check set, the envelope shall flag a timeout when no frame was received for more than 5 nominal periods, and shall clear authority on the flag. | B‡ | TSR-401 | U-SAF-CORE | UT, HIL, FI | Detection ≤ 5 periods + one task period (≤ 0.2 s for 33 Hz `0x1D2`) | Not met: max(10 periods, 1 s) (`safety.h:322, 332`) |
| SWSR-401a | The RX timeout evaluation (and the other periodic checks of SWSR-307, 403, 404, 405, 407, 408, 413, 506) shall run in a periodic safety task at ≥ 50 Hz on a timer interrupt separate from the comms interrupts. | B‡ | TSR-401, TSR-407 | `panda.main.safety_task` (U-PND-MAIN) | HIL, A | Measured period ≤ 20 ms, jitter recorded | Not met: `safety_tick` called at 1 Hz from the 8 Hz tick ISR (`main.c:142-143, 241-242`) (GAP-06); [WP-S-04 §5](../03-system/WP-S-04-timing-ftti-budget.md) |
| SWSR-402 | The envelope shall verify the Toyota additive checksum and length of `0x260` and `0x1D2` (and `0x262`, `0x1D3`, `0xB4` once added) on every frame and treat one failure as an RX fault. | B‡ | TSR-402 | U-SAF-CORE, U-SAF-TOY | UT | Single bit flip in data or checksum → fault | Impl: `safety.h:164-197`; `modes/toyota.h:40-46, 65-77`; 8-bit additive (GAP-01) |
| SWSR-403 | The envelope shall flag an RX fault when a configured message arrives at more than 1.5× its nominal rate over a 100 ms window. | B‡ | TSR-403 | U-SAF-CORE | UT, FI | Fault at injected 1.5× + 1 frame per window; no fault on reference logs (RP) | Not impl (GAP-01) |
| SWSR-404 | The envelope shall flag an RX fault when the data field (excluding checksum) of `0x260` torque/angle bytes, of `0xAA` (vehicle moving above v_min) or of `0xB4` ENCODER stays identical for longer than t_frz. | B‡ | TSR-404 | U-SAF-CORE, U-SAF-TOY | UT, RP, FI | Detection ≤ t_frz; no false detection on the reference log set | Not impl (GAP-01) |
| SWSR-405 | The envelope shall flag an RX fault when (a) mean wheel speed from `0xAA` and SPEED from `0xB4` differ by > 2 m/s, (b) BRAKE_PRESSED in `0x226` and in `0x1D3` disagree (the envelope then treats the brake as pressed), (c) CRUISE_ACTIVE = 1 with `0x1D3` MAIN_ON = 0, or (d) with authority granted, measured EPS torque does not follow the accepted command within the EPS-response tolerance, each for longer than its tolerance time. | B‡ | TSR-405 | U-SAF-CORE, U-SAF-TOY | UT, RP, FI | Each disagreement detected ≤ 0.2 s; no false detection on reference logs | Not impl: `speed_mismatch_check` exists, unused (`safety.h:529-537`) (GAP-01) |
| SWSR-406 | On any RX fault the envelope shall clear all authority in the same call, report the reason (SWSR-108a), and not set authority again until all RX checks pass and a new PCM rising edge occurs. | B‡ | TSR-406 | U-SAF-CORE | UT, FI | Reaction in same call; re-engage only after edge | Partial: `safety.h:112-121, 337-340`; single flag `main_comms.h:23` |

### 6.2 SoC ↔ MCU link and command liveness

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-407 | In a car safety mode the envelope shall clear all authority when no heartbeat (`0xf3`) has been received for > 0.3 s. | B‡ | TSR-407 | U-PND-MAIN | HIL, FI | Clear ≤ 0.3 s + one task period | Not met: 1 Hz counter, SILENT after 5 s with ignition (`main.c:101-103, 153-162, 191-226`) (GAP-06) |
| SWSR-408 | While lateral authority is granted, the envelope shall clear authority when no `0x2E4` frame has been accepted for > 50 ms; while longitudinal authority is granted, the same for `0x343` with > 100 ms. | B‡ | TSR-408 | U-PND-MAIN, U-SAF-CORE | HIL, FI | Clear at 50/100 ms + task period; SS-L via SWSR-109a | Not impl (GAP-10) |
| SWSR-409 | The envelope shall treat a heartbeat whose control-loop counter has not advanced for > 0.3 s as missing (SWSR-407). | B‡ | TSR-409 | U-PND-COMMS, U-PND-MAIN | HIL, FI | Frozen counter with live heartbeat → revocation ≤ 0.3 s | Not impl: heartbeat carries only `engaged` (`main_comms.h:277-285`) |
| SWSR-409h | `pandad` shall send in each heartbeat the frame counter of the latest `carControl` received by `card`/`pandad`. | QM | TSR-409 | `host.pandad` | UT, IT | Counter equals `carControl` frame | Not impl: `engaged` only (`selfdrive/pandad/pandad.cc:389-390`; `panda.cc:137-139`) (GAP-10) |
| SWSR-410 | The SPI driver shall verify a CRC (polynomial per WP-S-05 §4, OI-7 of WP-S-02) over header and data of every transfer and NACK and discard transfers with a CRC error. | B‡ | TSR-410 | `panda.drivers.spi` (U-PND-SPI) | UT, HIL, FI | All injected 1–3 bit errors and burst errors ≤ CRC width detected | Not met: 8-bit XOR seeded 0xAB (`drivers/spi.h:97-104, 122, 137`) (GAP-10) |
| SWSR-410a | Each CAN-TX transfer (endpoint 3) shall carry a sequence counter; the envelope shall discard a transfer with a repeated or out-of-order counter and count it as an SPI error. | B‡ | TSR-410 | U-PND-SPI, U-PND-COMMS | UT, HIL, FI | Replayed, dropped and reordered transfers detected | Not impl (`can_comms.h:8-37`) |
| SWSR-410h | `pandad` (`spi.cc`) shall compute the CRC and sequence counter of SWSR-410/410a on every transfer. | QM (B-sup) | TSR-410 | `host.pandad` | IT | Interface test VS-SWI | Not impl (`selfdrive/pandad/spi.cc`) |
| SWSR-411 | The envelope shall reject actuation frames whose transfer counter is more than 2 control periods older than the newest accepted transfer. | B‡ | TSR-411 | U-PND-COMMS | HIL, FI | Stale transfer rejected | Not impl |
| SWSR-412 | The SPI driver shall reject (NACK) a header whose MOSI length exceeds `SPI_BUF_SIZE − SPI_HEADER_SIZE − 1` or whose MISO length exceeds `SPI_BUF_SIZE − 4`, before starting any DMA. | B‡ | TSR-412 | U-PND-SPI | UT, HIL, FI | Length = bound accepted; bound + 1 NACKed, no write outside `spi_buf_rx` | Not met: lengths from header (`drivers/spi.h:115-116`) used for DMA (`:233`) and read (`:150`) unchecked (GAP-47) |
| SWSR-412a | Every control-request parameter used as an array index shall be checked against the array bound before use; a violation shall be ignored and counted. | B‡ | TSR-412 | U-PND-COMMS | UT, R | `0xe8` with param1 ≥ `PANDA_CAN_CNT` has no effect | Not met: `bus_config[param1]` (`main_comms.h:262-264`) (GAP-47); others checked (`:117, 135, 235, 298, 309`) |
| SWSR-412b | `comms_can_write` shall discard a packet whose length from the DLC exceeds the remaining transfer or reassembly buffer and shall resynchronise at the next transfer. | B‡ | TSR-412 | U-PND-COMMS | UT, FI | Fuzzed transfers never write outside `can_write_buffer.data` | Partial: bounded by DLC table (`can_comms.h:113-125`); no resync rule; WP-A-02 FFI-SP-03 |
| SWSR-413 | When SPI errors exceed N_spi within 100 ms while authority is granted, the envelope shall clear authority and report. | B‡ | TSR-413 | U-PND-SPI, U-PND-MAIN | HIL, FI | Clear on N_spi + 1 errors | Partial: counted only (`drivers/spi.h:220-222`, `main_comms.h:36`) |
| SWSR-414h | `pandad` shall not forward `sendcan` messages older than 20 ms. | QM (B-sup) | TSR-614 | `host.pandad` | UT | 21 ms message dropped | Not met: 1 s (`selfdrive/pandad/pandad.cc:78-79`) — listed here and as SWSR-614 |

## 7. SWSR-5xx Safety-MCU platform software

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-501 | The firmware shall service the independent watchdog only at the end of a periodic safety task cycle in which all periodic checks completed (logical checkpoint), never from a comms ISR. | B‡ | TSR-501 | U-PND-MAIN, `panda.sys.faults` (U-PND-FLT) | R, HIL, FI | Stall of task, comms ISR storm or main-loop hang → reset ≤ 0.2 s | Not impl: `IND_WDG` unused (`stm32h7/stm32h7_config.h:43`); software watchdog kicked in the ISR it supervises (`main.c:119`, `drivers/simple_watchdog.h`) (GAP-07) |
| SWSR-502 | Every detected fault in the fault table of WP-W-05 §6.1 shall lead to SS-S (SILENT, relay released, CAN TX disabled) within 0.1 s, latched until power cycle or recovered per its documented class. | B‡ | TSR-502 | U-PND-FLT, U-PND-MAIN | R, FI | Each fault injected → SS-S ≤ 0.1 s | Not impl: report-only (`sys/faults.h:8-27`), `PERMANENT_FAULTS 0U` (`sys/sys.h:50`) (GAP-08) |
| SWSR-502a | Every exception handler (HardFault, NMI, MemManage, BusFault, UsageFault), the unused-interrupt handler and `assert_fatal` shall end in an MCU reset or in SS-S; none shall loop forever with the relay driven. | B‡ | TSR-502 | `panda.platform` (U-PND-PLAT) | R, FI | Each path injected → reset or SS-S | Partial: NMI/HardFault reset (`early_init.h:73-81`); unused IRQ report-only (`drivers/interrupts.h:5-9`); `assert_fatal` hangs (`main.c:39, 354-356`) (GAP-43) |
| SWSR-502b | Interrupt-rate violations of the CAN, SPI and tick interrupts shall be classified as faults under SWSR-502 when authority is granted. | B‡ | TSR-502, TSR-508 | U-PND-FLT | FI | ISR storm → SS-S | Partial: detected, report-only (`drivers/interrupts.h:35-37`) |
| SWSR-503 | At start-up and periodically within the latent-fault interval the firmware shall compute a CRC over the application image and enter SS-S on mismatch. | B‡ | TSR-503 | U-PND-FLT, U-PND-PLAT | HIL, FI | Flipped image byte → SS-S, relay never driven | Not impl (GAP-08) |
| SWSR-503a | `check_registers()` divergence shall be a fault under SWSR-502 and shall run in the periodic safety task. | B‡ | TSR-503 | U-PND-FLT | FI | Divergent register → SS-S within one check period | Partial: 1 Hz, report-only (`drivers/registers.h:56-70`, `main.c:229`) |
| SWSR-503b | The firmware shall handle RAM-ECC and flash-ECC double-error events as faults under SWSR-502 and count single-error events in health. | B‡ | TSR-503 | U-PND-FLT | FI | Injected ECC event → reaction/count | Not impl (HWSR-503…503b) |
| SWSR-504 | The firmware shall cross-check the core clock against the LSI (or another independent clock) and treat a deviation beyond tolerance as a fault under SWSR-502. | B‡ | TSR-504 | U-PND-FLT | FI | ±tolerance drift detected | Not impl; CSS → NMI → reset exists (`early_init.h:73-76`) |
| SWSR-505 | The firmware shall handle the programmable voltage detector event and an out-of-range device input voltage while the relay is driven as faults under SWSR-502. | B‡ | TSR-505 | U-PND-FLT | HIL | Supply ramp → SS-S before brown-out | Not impl: voltage reported only (`main_comms.h:14`) |
| SWSR-506 | The firmware shall compare the commanded relay state with the read-back state in the periodic safety task and, on a mismatch persisting > 0.3 s in either direction, latch relay malfunction until power cycle. | B‡ | TSR-506 | `panda.drivers.harness` (U-PND-HARN), U-PND-FLT | HIL, FI | Stuck-released and stuck-intercept each detected ≤ 0.3 s | Not impl: no readback (GAP-12) |
| SWSR-506a | The relay-malfunction latch shall not be cleared by a safety-mode change. | B‡ | TSR-506 | U-SAF-CORE | UT | Latch survives `0xdc` | Not met: cleared in `set_safety_hooks` (`safety.h:427, 459`) (GAP-48) |
| SWSR-507 | The firmware shall configure the MPU so that comms handlers (SPI/USB/control) cannot write the envelope state, configuration and stacks, with a stack guard region, and shall treat a MemManage fault as SWSR-502a. | B‡ | TSR-507 | U-PND-PLAT | R, FI | Injected write from comms context → MemManage → reset | Not impl (GAP-08, GAP-11) |
| SWSR-508 | Bus-off or persistent TX failure on the car-side bus while authority is granted shall clear authority and be reported. | B‡ | TSR-508 | U-PND-FDCAN, U-SAF-CORE | HIL, FI | Clear ≤ 0.3 s after bus-off | Partial: counted (`drivers/fdcan.h:47-48, 76-83`), no reaction |
| SWSR-509 | MCU die temperature outside the specified range shall be a fault under SWSR-502. | B | TSR-509 | U-PND-FLT | HIL | SS-S ≤ 1 s | Partial: reported only (`main_comms.h:51-52`) |
| SWSR-510 | Heartbeat loss in a car safety mode shall lead to SILENT with relay released after ≤ 2 s regardless of the ignition reading. | B | TSR-510 | U-PND-MAIN | HIL | SILENT ≤ 2 s with ignition on and off | Not met: 5 s with ignition (`main.c:101-103, 193`) |
| SWSR-511 | The bootstub shall execute the application only after verifying its signature with a current algorithm and key length against the release key; release bootstubs shall not accept the debug key. | B‡ (+ CS) | TSR-511 | `panda.bootstub` (U-PND-BOOT) | HIL, FI | Tampered image or debug-signed image not executed | Partial: RSA-1024/SHA-1 (`bootstub.c:47-72`); debug key only with `ALLOW_DEBUG` (`:67-72`) (GAP-24) |
| SWSR-511a | Request `0xd1` param 1 (softloader entry) shall be rejected while a car safety mode is active or the ignition is on; `0xd1` param 0 shall stay debug-only. | B‡ (+ CS) | TSR-511 | U-PND-COMMS | UT, HIL | No reset into softloader from car mode | Not met: softloader allowed (`main_comms.h:176-180`) (GAP-24) |
| SWSR-512 | In the reference release build, request `0xdc` shall accept only SILENT, NOOUTPUT, ELM327 and TOYOTA with parameter 73 (no flag bits); once TOYOTA is active only NOOUTPUT or SILENT shall be accepted; any other request shall be rejected and reported. | B‡ | TSR-512 | U-PND-COMMS, U-PND-MAIN | UT, HIL | All other (mode, param) pairs rejected, state unchanged | Not met: any mode/param any time (`main_comms.h:222-225`; `main.c:31-79`) (GAP-09, GAP-44); W-09 DVR-01/02 |
| SWSR-513 | In release builds, requests `0xc5`, `0xe5`, `0xde`, `0xf9`, `0xfc`, `0xe8`, `0xdb`, `0xe6`, `0xe7`, `0xf1`, `0xd8` and `0xdf` shall be rejected while a car safety mode is active (`0xd1` param 1: SWSR-511a). | B‡ | TSR-513 | U-PND-COMMS | UT, HIL | Each request has no effect in TOYOTA mode | Not met (`main_comms.h:144-147, 214-221, 233-276, 296-314`) (GAP-09, GAP-49); `0xdf` already refused in car modes (`:241-247`) |
| SWSR-512a | In the reference release build, the alternative-experience word shall be fixed to the reference value; request `0xdf` shall not change it in any mode. | B‡ | TSR-512 | U-PND-COMMS | UT, HIL | `0xdf` in NOOUTPUT followed by TOYOTA leaves the reference value | Not met: settable outside car modes and carried into the next car mode (`main_comms.h:241-247`) |
| SWSR-514 | Release firmware shall be built without `ALLOW_DEBUG`, and the version request `0xd6` shall report the build type. | B‡ (+ CS) | TSR-514 | build, U-PND-COMMS | R, HIL | Release image contains no ALLOUTPUT/debug modes (symbol check); build type readable | Not met by default (`panda/SConscript:12-20`; `safety.h:413-422`) (GAP-25) |
| SWSR-514h | The host shall refuse engagement when the panda reports a non-release build. | QM (B-sup) | TSR-514, TSR-802 | `host.pandad`, `host.selfdrived` | UT | No engagement with debug FW | Not impl; W-09 DVR-05 |
| SWSR-515 | Before first driving the relay after power-up, the firmware shall run start-up tests (image CRC, RAM test of safety data regions, watchdog reset path at the defined interval, relay drive/readback, siren path) and stay in SS-S on failure. | B‡ | TSR-515 | U-PND-PLAT, U-PND-MAIN | HIL, FI | Each injected start-up failure → no relay drive | Not impl |
| SWSR-517 | The firmware shall read back its own transmitted actuation frames on the car-side bus (FDCAN TX event or loop-back reception) and compare them with the frame approved by the TX hook; a mismatch within 2 frames shall be a fault under SWSR-502. | B‡ | TSR-517 | U-PND-FDCAN, U-PND-FLT | FI, HIL | Injected corruption after the TX hook detected ≤ 2 frames | Not impl: XOR check before FIFO load only (`drivers/fdcan.h:100`) |
| SWSR-518 | The TX hook shall reject frames of each whitelisted ID sent faster than its nominal period minus a tolerance, and shall revoke authority and report when the excess persists while authority is granted. | B‡ | TSR-518 | U-SAF-CORE, U-SAF-TOY | UT, HIL | `0x2E4` at 2× rate: excess frames rejected; persistent excess → revocation ≤ 0.1 s | Not impl (content checks only) |
| SWSR-519 | The firmware shall assign an explicit NVIC priority to every enabled interrupt per the scheme of WP-W-03 §5.1/OI-4, and the measured worst-case latency of the periodic safety task under worst-case interrupt load shall meet the SWSR-401a/407/501 budgets. | B‡ | TSR-519 | U-PND-PLAT, U-PND-MAIN | A, HIL | Every enabled IRQ has a documented priority; measured latency within budget | Not impl: no `NVIC_SetPriority` in `panda/board` (all at default priority); RX hook in FDCAN ISR (`drivers/fdcan.h:221`), TX hook and dispatcher in SPI DMA ISR (`stm32h7/llspi.h:56-61`) (GAP-50) |
| SWSR-516 | On heartbeat loss (SWSR-407) or a platform/RX fault revocation within 5 s after authority was granted, the firmware shall activate its siren within 0.5 s without SoC involvement. | B | TSR-516 | U-PND-MAIN, `panda.drivers.siren` (U-PND-HK) | HIL | Siren ≤ 0.5 s | Partial: 3 s siren after 5 s heartbeat loss (`main.c:169-171, 198-201`) |

## 8. SWSR-6xx Host software (SoC, QM)

Host requirements are QM. Those marked QM (B-sup) support an envelope SWSR; no ASIL claim is made for them. They include QM behaviour that affects safety and that the SOTIF and FFI arguments rely on.

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-601 | `selfdrived` shall map loss or staleness of a control input (`commIssue`, model failure, `canError`, `controlsMismatch`) to immediate disable, and thermal/storage/memory events to soft disable. | QM (B-sup) | TSR-601 | `host.selfdrived` | UT, FI | Actuation on a failed input ends ≤ 0.2 s | Not met: `commIssue` SOFT_DISABLE (`selfdrive/selfdrived/events.py:853-856`), 3 s (`state.py:7-8`) (GAP-16) |
| SWSR-601a | The messaging "alive" criterion for control inputs shall be ≤ 2 nominal periods. | QM (B-sup) | TSR-601 | `host.cereal` | UT | Alive false at 2 periods + 1 | Not met: 10 periods (`cereal/messaging/__init__.py:265`) |
| SWSR-602 | `controlsd` shall check the age of `modelV2`, `longitudinalPlan` and `carState` (≤ 2 nominal periods) and set `latActive`/`longActive` false with an event when stale. | QM (B-sup) | TSR-602 | `host.controlsd` | UT | Stale input → inactive next frame | Not met (`selfdrive/controls/controlsd.py:66`) (GAP-16) |
| SWSR-603 | `selfdrived` shall not mask `commIssue`, localizer, posenet or `modeldLagging` checks while engaged, and `modeld` shall not switch models while engaged; the reference build shall not contain the big model (Chestnut). | QM (B-sup) | TSR-603 | `host.selfdrived`, `host.modeld` | R, UT | No suppression path reachable while engaged | Not met: `selfdrived.py:382-384, 403, 457`; `modeld.py:411-419` (GAP-17) |
| SWSR-604 | A non-finite actuator value shall raise an immediate-disable event. | QM (B-sup) | TSR-604 | `host.controlsd` | UT | NaN → event in same frame | Not met: replaced by 0 (`controlsd.py:140-147`) (GAP-19) |
| SWSR-605 | Controller limits shall stay ≥ margin below envelope limits (torque ≤ 90 % τ_max(v), accel within [a_min + 0.2, a_max − 0.2] m/s²). | QM | TSR-605 | `host.card` (CarControllerParams) | UT, A | Automated check passes | Not met: equal values (`values.py:20, 39-47`) |
| SWSR-605a | A CI check shall compare host controller limits with the envelope constants and fail on insufficient margin. | QM | TSR-605 | CI | R | Check runs on every SR-Q PR | Not impl; W-09 DVR-06 |
| SWSR-606 | On every fault-induced disengagement the HMI shall give a visual and acoustic take-over request ≤ 1 s, naming the fault class. | QM (B-sup) | TSR-606 | `host.selfdrived`, `host.hmi` | IT, HIL | Latency ≤ 1 s; text matches class | Partial: `canError` text wrong (`events.py:928-936`) (GAP-19) |
| SWSR-607 | The HMI shall warn when the EPS reports LKA unavailable or faulted. | QM (B-sup) | TSR-607 | `host.card`, `host.selfdrived` | UT | Warning ≤ 1 s | Impl: `steerFaultTemporary/Permanent` |
| SWSR-608 | DM shall escalate warnings with the WP-C-08 §5 timing. | QM | TSR-608 | `host.dm` | UT | Timers match | Impl: `selfdrive/monitoring/policy.py:31-36` |
| SWSR-609 | The DM model output shall be marked invalid when input or output is missing or not credible; invalid > 2 s while engaged shall escalate to a take-over request. | QM | TSR-609 | `host.dm` | UT, FI | Escalation ≤ 2 s | Not met: `valid=True` always (`selfdrive/modeld/dmonitoringmodeld.py:99`) (GAP-21) |
| SWSR-610 | `IsDriverViewEnabled` and other debug/demo parameters shall block engagement. | QM | TSR-610 | `host.selfdrived`, `host.dm` | UT | No engagement with key set | Not met (`dmonitoringd.py:26-38`) (GAP-20); W-09 DVR-12 |
| SWSR-611 | Unresponsive driver → decel, disengage, lockout 1/5/15/30 min. | QM | TSR-611 | `host.dm`, `host.controlsd` | UT | As specified | Impl: `policy.py:39-44`; `controlsd.py:203-204` |
| SWSR-612 | Wheel-touch fallback shall reset awareness only on a deliberate input above threshold. | QM | TSR-612 | `host.dm` | UT | Small inputs do not reset | Not met (`policy.py:334-335`) (GAP-21) |
| SWSR-613 | Joystick, maneuver and debug processes and the `lateralManeuverPlan` path shall be absent from reference builds. | QM (B-sup) | TSR-613 | `host.manager`, `host.controlsd` | R | Not present in release manifest | Not met (`system/manager/process_config.py:34-47, 95-109`; `controlsd.py:123-124`) (GAP-20) |
| SWSR-614 | `pandad` shall drop `sendcan` older than 20 ms (same as SWSR-414h). | QM (B-sup) | TSR-614 | `host.pandad` | UT | 21 ms dropped | Not met (`pandad.cc:78-79`) |
| SWSR-615 | `selfdrived` shall immediately disable on any panda fault flag, heartbeat-lost flag, rising `safetyTxBlocked` while engaged, revocation reason code or SPI error burst. | QM (B-sup) | TSR-615 | `host.selfdrived` | UT, FI | Event ≤ 0.2 s | Partial: `relayMalfunction`, `safetyRxChecksInvalid` only (`selfdrived.py:338-342`) |
| SWSR-616 | Driving-model outputs shall be checked for non-finite values, range and age before use (AIR-16, AIR-17, AIR-25). | QM | TSR-616 | `host.modeld`, `host.controlsd` | UT | Injected invalid output → event | Partial (`modeld.py:210-211`) (GAP-22) |
| SWSR-617 | Excessive-actuation detection (2× limits, 0.25 s) shall latch until offroad. | QM | TSR-617 | `host.selfdrived` | UT | Latch | Impl: `selfdrived/helpers.py:12, 30, 41`; `selfdrived.py:305-310` |
| SWSR-618 | PCM ACC fault → immediate disable. | QM (B-sup) | TSR-618 | `host.selfdrived` | UT | Event | Impl: `events.py:908` |
| SWSR-619 | `pandad` shall compare panda-reported safety model, parameter and alternative experience with the release-record values and block engagement with an alert on mismatch. | QM (B-sup) | TSR-619 | `host.pandad`, `host.selfdrived` | UT, IT | Mismatch → no engagement ≤ 1 s | Not impl (`selfdrive/pandad/panda_safety.cc:56-69`); host check vs CarParams only (`selfdrived.py:330-339`) |
| SWSR-620 | The host shall request TOYOTA mode and allow engagement only when the ECU firmware versions read at start-up match the release record; otherwise it shall keep NOOUTPUT and inform the driver. | QM (B-sup) | TSR-620 | `host.card`, `host.pandad` | UT, VT | Mismatching FW set → NOOUTPUT | Not impl: fuzzy fingerprinting (`opendbc_repo/opendbc/car/car_helpers.py:86-87, 144, 164`); W-09 DVR-10 |

## 9. SWSR-7xx Stock PCS preservation (software part)

| ID | Requirement | ASIL | Parent | Allocation | Verif | Acceptance | Baseline / GAP |
|---|---|---|---|---|---|---|---|
| SWSR-701 | The firmware shall detect harness orientation before the first relay drive, route CAN accordingly, and enter SS-S if orientation is lost or changes while the relay is driven. | B | TSR-701 | U-PND-HARN, U-PND-MAIN | HIL, FI | Orientation change while driven → SS-S ≤ 1 s | Partial: detection `drivers/harness.h:54-94`, suspended while driven (`:59`); re-init only (`main.c:132-140`) |
| SWSR-704 | The forwarding hook shall forward every camera-side frame to the car side except `0x2E4`, `0x191`, `0x412` and `0x343`, and every car-side frame to the camera side; all forwarding shall stop on relay malfunction. | B | TSR-704 | U-SAF-CORE, U-PND-FDCAN | UT, HIL | Forwarding matrix fully tested | Impl: `safety.h:254-290`; `drivers/fdcan.h:199-215` |
| SWSR-705 | The reference Toyota TX whitelist shall not contain `0x344`, `0x411`, `0x2E6`, `0x2E7`, `0x33E`, `0x365`, `0x366`, `0x4CB` or the bus-1 DSU set; `0x283` shall pass only with zero payload. | B | TSR-705 | U-SAF-TOY | UT, R | Each ID rejected; `0x283` non-zero rejected | Not met (`modes/toyota.h:19-32`); `0x283` impl `:251-257` (GAP-42, GAP-49) |
| SWSR-706 | Every entry to SILENT/NOOUTPUT and every fault reaction shall release the relay before returning. | B | TSR-706 | U-PND-MAIN, U-PND-HARN | UT, HIL | Relay output released after each path | Partial: `main.c:44-54`; hang path → SWSR-501/502a (GAP-43) |
| SWSR-707 | Forwarding latency camera → car shall be ≤ 1 ms (TBD) under worst-case load, and TX queue overflow on the forwarding path shall be a reported fault. | B | TSR-707 | U-PND-FDCAN | HIL, A | Measured p100 latency ≤ bound | Not verified; overflow counted (`drivers/can_common.h:165`) |
| SWSR-710 | The envelope shall latch relay malfunction when a `check_relay` message is seen on the car side more than 1 s after the last mode change, and then block all TX and forwarding. | B‡ | TSR-710 | U-SAF-CORE | UT, HIL | Latch, TX and forwarding blocked | Impl: `safety.h:211-220, 252, 268, 372-380` |
| SWSR-709h | The HMI shall inform the driver of stock AEB/FCW events. | QM | TSR-709 | `host.card` | UT | Event | Impl: `selfdrive/car/car_events.py:120-123` |

## 10. TSRs not refined into software

| TSR | Reason |
|---|---|
| TSR-111, 208, 310, 708 | External measures (EPS, PCM); verified by vehicle test |
| TSR-702, 703 | Harness hardware only (HWSR-702, 703) |
| TSR-801…818 | Production/operation ([WP-S-06](../03-system/WP-S-06-requirements-production-operation.md)); software support via SWSR-514, 514h |

## 11. Software-hardware interface requirements

These SWSRs depend on a hardware resource. They refine the HSI of [WP-S-05](../03-system/WP-S-05-hsi-specification.md) and pair with the HWSRs of [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md).

| ID | Requirement | HW resource | HSI ([WP-S-05](../03-system/WP-S-05-hsi-specification.md)) | HWSR | Baseline |
|---|---|---|---|---|---|
| SWSR-501b | The bootstub shall configure and start IWDG1 in window mode (timeout ≤ 0.2 s including reset) before jumping to the application; no software path shall be able to stop it. | IWDG1, LSI | §7 (HSI-08…12) | HWSR-501, 501b, 501c | Not impl |
| SWSR-502c | The first actions after reset shall put both relay drive outputs in the released level and leave the car-side transceivers disabled until a car mode is set. | GPIO (relay SBU1/SBU2), transceiver enable | §6, §7 | HWSR-502, 508 | Partial: relay released in `harness_init` (`drivers/harness.h:96-107`) after clock/peripheral init (`main.c:259-282`); transceivers enabled after SILENT (`main.c:295-298`) |
| SWSR-503c | The firmware shall enable RAMECC monitoring of all SRAM regions holding safety data and route uncorrectable-error events to SWSR-502. | RAMECC, flash ECC | §8 | HWSR-503, 503a, 503b | Not impl |
| SWSR-504a | The clock cross-check of SWSR-504 shall use an oscillator independent of HSE. | LSI/HSI, timers | §7 | HWSR-504, 504a | Not impl |
| SWSR-505a | The firmware shall configure the PVD threshold and handle its interrupt; it shall sample the input voltage ADC in the safety task. | PWR PVD, ADC | §6, §7 | HWSR-505, 505a, 505b | Not impl |
| SWSR-506b | The firmware shall read the relay feedback input defined in WP-S-05 in the safety task (SWSR-506). | Relay readback input (to be added) | §6 | HWSR-506a | Not impl (no HW signal) |
| SWSR-507a | MPU regions shall follow the memory map of WP-S-05 §8 (`stm32h7/stm32h7x5_flash.ld:70-79`). | Cortex-M7 MPU | §8 | HWSR-507 | Not impl |
| SWSR-508a | The firmware shall disable the car-side transceivers as part of SS-S. | Transceiver enable GPIO | §5 | HWSR-508 | Partial: `enable_can_transceivers` (`sys/power_saving.h:15-21`) used for power save, not as safe state |
| SWSR-410b | The SPI driver shall treat DMA transfer-error, SPI overrun and mode-fault flags as SPI errors (SWSR-413). | SPI4, DMA2 streams 2/3 | §4 (HSI-01…03) | HWSR-401 | Not impl (`stm32h7/llspi.h:56-82` handle completion only) |
| SWSR-516a | The siren shall be driven through a path that does not depend on the SoC audio stack. | DAC/codec (board dependent) | §6/§7 | — (WP-S-02 OI-8) | Partial (`drivers/fake_siren.h:38-52`) |
| SWSR-701a | Orientation detection shall use the SBU ADC inputs only while the relay is not driven, and the relay state shall not be changed while an ADC conversion holds the lock. | SBU ADC | §6 (HSI-05…07) | HWSR-701, 701a | Impl: `drivers/harness.h:20, 39, 59-85` (busy-wait, WP-A-02 FFI-TM-03) |

## 12. Mapping of WP-W-09 data verification requirements

[WP-W-09](WP-W-09-configuration-calibration-data.md) OI-1 asks for migration of DVR-nn. Software-implementable DVRs are covered as follows; the rest stay in WP-W-09 as data/process requirements.

| DVR | Covered by | Remark |
|---|---|---|
| DVR-01, DVR-02 | SWSR-512, SWSR-104a | |
| DVR-03, DVR-04 | General rule G-01 (§2.3) | Remain data requirements |
| DVR-05 | SWSR-514, SWSR-514h | |
| DVR-06 | SWSR-605a | |
| DVR-12 | SWSR-610, SWSR-613 | |
| DVR-22 | SWSR-102, SWSR-102a | |
| DVR-07…11, 13…21 | Not SWSRs | Host QM data, model and learning requirements; candidates for WP-S-01, WP-W-10 |

## 13. Traceability

### 13.1 SWSR → TSR (and TSR → SWSR coverage)

| TSR | SWSRs | TSR | SWSRs |
|---|---|---|---|
| TSR-101 | 101, 101a | TSR-409 | 409, 409h |
| TSR-102 | 102, 102a | TSR-410 | 410, 410a, 410b, 410h |
| TSR-103 | 103, 103a | TSR-411 | 411 |
| TSR-104 | 104, 104a | TSR-412 | 412, 412a, 412b |
| TSR-105 | 105 | TSR-413 | 413 |
| TSR-106 | 106 | TSR-501 | 501, 501b |
| TSR-107 | 107, 101a | TSR-502 | 502, 502a, 502b, 502c |
| TSR-108 | 108, 108a | TSR-503 | 503, 503a, 503b, 503c |
| TSR-109 | 109, 109a | TSR-504 | 504, 504a |
| TSR-110 | 110 | TSR-505 | 505, 505a |
| TSR-201 | 201, 201a | TSR-506 | 506, 506a, 506b |
| TSR-202 | 202 | TSR-507 | 507, 507a |
| TSR-203 | 203 | TSR-508 | 508, 508a, 502b |
| TSR-204 | 204 | TSR-509 | 509 |
| TSR-205 | 205 | TSR-510 | 510 |
| TSR-206 | 206 | TSR-511 | 511, 511a |
| TSR-207 | 207 | TSR-512 | 512, 512a, 104a |
| TSR-301 | 301 | TSR-513 | 513 |
| TSR-302 | 302 | TSR-514 | 514, 514h |
| TSR-303 | 303h | TSR-515 | 515 |
| TSR-304 | 304, 304a | TSR-516 | 516, 516a |
| TSR-517 | 517 | TSR-518 | 518 |
| TSR-519 | 519 | | |
| TSR-305 | 305 | TSR-601…620 | 601…620 (601a, 605a); 614 = 414h |
| TSR-306 | 306 | TSR-701 | 701, 701a |
| TSR-307 | 307, 307h | TSR-704 | 704 |
| TSR-308 | 308h | TSR-705 | 705 |
| TSR-309 | 309 | TSR-706 | 706 |
| TSR-311 | 311 | TSR-707 | 707 |
| TSR-401 | 401, 401a | TSR-709 | 709h |
| TSR-402 | 402 | TSR-710 | 710 |
| TSR-403 | 403 | | |
| TSR-404 | 404 | | |
| TSR-405 | 405 | | |
| TSR-406 | 406, 108a | | |
| TSR-407 | 407, 401a | | |
| TSR-408 | 408, 109a | | |

Every TSR allocated to P-SW or SoC in WP-S-02 has at least one SWSR. TSRs not refined into software are in §10.

### 13.2 Count

| Block | Envelope (B‡/B) | Host (QM, QM (B-sup)) |
|---|---|---|
| 1xx | 16 | — |
| 2xx | 8 | — |
| 3xx | 9 | 3 (303h, 307h, 308h) |
| 4xx | 18 | 3 (409h, 410h, 414h) |
| 5xx | 35 (incl. HSI) | 1 (514h) |
| 6xx | — | 22 |
| 7xx | 7 (incl. 701a) | 1 (709h) |
| **Total** | **93** | **30** |

**Total SWSRs: 123.** Machine-readable records go to `assurance/trace/items/swsr.yaml` (OI-1).

### 13.3 SWSR → verification

| SWSR group | Unit (WP-W-06) | Integration (WP-W-07) | Embedded (WP-W-08) |
|---|---|---|---|
| 101–110 | VS-UV-02…05, 17 | VS-SWI-01, 02, 09 | VS-SWQ-01…04, 13 |
| 201–207 | VS-UV-07, 08 | VS-SWI-01 | VS-SWQ-05 |
| 301–311 | VS-UV-06 | VS-SWI-02, 10 | VS-SWQ-06, 07 |
| 401–406 | VS-UV-09, 10 | VS-SWI-03, 04 | VS-SWQ-08, 09 |
| 407–414h | VS-UV-14, 15 | VS-SWI-05…08, 11, 12 | VS-SWQ-10…12 |
| 501–519 | VS-UV-13, 16, 21, 22 | VS-SWI-12…15 | VS-SWQ-14…19, 23, 25 |
| 601–620 | host unit tests (WP-W-06 §4.7) | VS-SWI-16, 17 | VS-SWQ-20 |
| 701–710 | VS-UV-11, 18 | VS-SWI-09 | VS-SWQ-21, 22 |

## 14. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Create `trace/items/swsr.yaml` from this document; add `@req` tags in the forks (D-01) | Safety engineer | G3 |
| OI-2 | Replace B‡ with the final ASIL after SG-01 re-rating (WP-S-02 OI-2) | Safety manager | G2 |
| OI-3 | Decide frame ownership for SWSR-109/109a: envelope-generated `0x2E4` needs the counter/checksum layout from the DBC and must not conflict with SoC frames; alternative (b) of TSR-109 needs WP-S-04 M-02 | SW lead | G3 |
| OI-4 | Set numeric values for j_up, j_down, T_ovr, t_ovr, t_frz, N_spi, driver allowance and tolerances of SWSR-405 (WP-S-02 OI-3, OI-5) | Safety engineer | G3 |
| OI-5 | Decide whether `0xc0` (comms reset), `0xb0`/`0xb1` and `0xf6` need gating in car modes; TSR-513 does not list them (see WP-W-04 SWF-24) | Safety engineer | G3 |
| OI-6 | Extend `struct lookup_t` beyond 3 breakpoints if the τ_max(v) table needs more (SWSR-102) | SW lead | G3 |
| OI-7 | Re-check SWSR parents after WP-S-02 approval; this draft follows WP-S-02 including TSR-517…519 and TSR-619/620 | Safety engineer | G3 |
| OI-8 | Agree the reason-code field layout of SWSR-108a with WP-S-05 §4.2 and `cereal` `pandaStates` | SW lead | G3 |
