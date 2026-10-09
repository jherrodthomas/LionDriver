# WP-W-05 Software Unit Design and Implementation

| Field | Value |
|---|---|
| Work product | WP-W-05 Software unit design and implementation |
| Standard reference | ISO 26262-6:2018 §8 (software unit design and implementation: notation, design principles for unit design and implementation); ISO/SAE 21434:2021 §10 (by reference to WP-W-11); ASPICE 4.0 SWE.3 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Envelope units (E-03a/E-03b): B‡ (ASIL C until SG-01 re-rating) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document describes the software units of the safety envelope as implemented at the baseline: purpose, inputs, outputs, state, algorithm, limits and error handling. It records compliance with the unit design principles of [WP-W-01 §6](WP-W-01-software-development-environment-guidelines.md) (ENV-R-01…15) and lists the changes each SWSR of [WP-W-02](WP-W-02-software-safety-requirements.md) requires. Units belong to the components of [WP-W-03 §3.1](WP-W-03-software-architecture.md); unit verification is in [WP-W-06](WP-W-06-software-unit-verification.md).

The design is back-filled from code (T-03). The code is the implementation; this document is the design description against which it is reviewed.

**Unit granularity.** A unit is one C function (or a small group of static helpers used by one public function). Module-level groupings (U-SAF-CORE etc.) are the components used by WP-W-06.

**Notation.** Function tables, state-transition tables (normative), pseudo-code only where the code is not self-explanatory (WP-W-01 §14). Paths as in WP-W-02 §2.2.

## 2. Unit inventory

| Unit | Function(s) | File:lines | Component | Context | SWSRs |
|---|---|---|---|---|---|
| UN-01 | `safety_rx_hook` | `safety.h:199-228` | U-SAF-CORE | FDCAN RX ISR | 301, 302, 402, 406, 710 |
| UN-02 | `rx_msg_safety_check`, `get_addr_check_index`, `update_addr_timestamp`, `update_counter`, `is_msg_valid` | `safety.h:112-197` | U-SAF-CORE | RX ISR, tick | 402, 406 |
| UN-03 | `safety_tx_hook`, `tx_msg_safety_check` | `safety.h:230-253` | U-SAF-CORE | SPI/USB ISR | 101–107, 201–207, 705, 710 |
| UN-04 | `safety_fwd_hook`, `get_fwd_bus` | `safety.h:255-288` | U-SAF-CORE | RX ISR | 704, 710 |
| UN-05 | `safety_tick` | `safety.h:321-344` | U-SAF-CORE | tick ISR (1 Hz) | 401, 406 |
| UN-06 | `generic_rx_checks`, `stock_ecu_check`, `relay_malfunction_set/reset` | `safety.h:346-384` | U-SAF-CORE | RX ISR | 302, 710 |
| UN-07 | `set_safety_hooks`, `reset_sample` | `safety.h:386-482` | U-SAF-CORE | SPI ISR, tick ISR | 311, 512 |
| UN-08 | `pcm_cruise_check` | `safety.h:518-527` | U-SAF-CORE | RX ISR | 301, 309 |
| UN-09 | `to_signed`, `update_sample`, `ROUND`, `GET_BYTES_LE`, `GET_BYTES_64_LE`, `speed_mismatch_check` | `safety.h:35-52, 484-537` | U-SAF-CORE / HELP | all | 101a, 104 |
| UN-10 | `steer_torque_cmd_checks` | `lateral.h:60-151` | U-SAF-LAT | TX path | 101–106, 108 |
| UN-11 | `dist_to_meas_check`, `driver_limit_check`, `rt_torque_rate_limit_check` | `lateral.h:10-57` | U-SAF-LAT | TX path | 103, 103a, 104, 304 |
| UN-12 | `get_longitudinal_allowed`, `longitudinal_accel_checks` | `longitudinal.h:3-12` | U-SAF-LONG | TX path | 201–203, 305 |
| UN-13 | `SAFETY_MIN/MAX/CLAMP/ABS`, `crc8_update`, `msg_matches_*`, `safety_get_ts_elapsed`, `safety_max_limit_check`, `safety_interpolate` | `helpers.h:7-104` | U-SAF-HELP | all | all |
| UN-14 | `toyota_rx_hook` | `modes/toyota.h:97-169` | U-SAF-TOY | RX ISR | 104, 301, 302, 305 |
| UN-15 | `toyota_tx_hook` | `modes/toyota.h:171-348` | U-SAF-TOY | TX path | 101, 101a, 103–107, 201–207, 705 |
| UN-16 | `toyota_init` | `modes/toyota.h:350-429` | U-SAF-TOY | SPI ISR | 104a, 512, 705 |
| UN-17 | `toyota_compute_checksum`, `toyota_get_checksum`, `toyota_get_quality_flag_valid` | `modes/toyota.h:65-95` | U-SAF-TOY | RX ISR | 402 |
| UN-18 | `set_safety_mode`, `is_car_safety_mode` | `main.c:31-86` | U-PND-MAIN | SPI ISR, tick | 311, 512, 706 |
| UN-19 | `tick_handler` | `main.c:106-249` | U-PND-MAIN | tick ISR | 307, 401a, 407, 510, 516 |
| UN-20 | `main` | `main.c:251-365` | U-PND-MAIN | thread | 502c, 515 |
| UN-21 | `comms_control_handler`, `get_health_pkt` | `main_comms.h:9-322` | U-PND-COMMS | SPI/USB ISR | 108a, 409, 412a, 511a, 512, 513 |
| UN-22 | `comms_can_write`, `comms_can_read`, `comms_can_reset`, `refresh_can_tx_slots_available` | `can_comms.h:47-146` | U-PND-COMMS | SPI/USB ISR | 410a, 411, 412b |
| UN-23 | `spi_rx_done`, `spi_tx_done`, `validate_checksum`, `spi_version_packet` | `drivers/spi.h:44-243` | U-PND-SPI | DMA/SPI ISR | 410, 412, 413 |
| UN-24 | `llspi_mosi_dma`, `llspi_miso_dma`, DMA/SPI IRQ handlers, `llspi_init` | `stm32h7/llspi.h:5-110` | U-PND-SPI | ISR | 410b, 412 |
| UN-25 | `can_rx` | `drivers/fdcan.h:154-243` | U-PND-FDCAN | FDCAN IT0 | 704, 707 |
| UN-26 | `process_can`, `update_can_health_pkt`, `can_clear_send`, `can_init` | `drivers/fdcan.h:7-150, 254-272` | U-PND-FDCAN | FDCAN IT1, any | 508, 707 |
| UN-27 | `can_send`, `can_push`, `can_pop`, `can_slots_empty`, `can_clear`, `can_set_checksum`, `can_check_checksum`, `can_init_all`, `can_set_orientation` | `drivers/can_common.h:42-177` | U-PND-FDCAN | any | 109, 707 |
| UN-28 | `set_intercept_relay`, `harness_check_ignition`, `harness_detect_orientation`, `harness_tick`, `harness_init` | `drivers/harness.h:8-107` | U-PND-HARN | tick, SPI ISR | 506, 701, 706 |
| UN-29 | `fault_occurred`, `fault_recovered` | `sys/faults.h:8-27` | U-PND-FLT | any | 502 |
| UN-30 | `simple_watchdog_kick/init` | `drivers/simple_watchdog.h` | U-PND-FLT | tick | 501 (to be replaced) |
| UN-31 | `handle_interrupt`, `interrupt_timer_handler`, `init_interrupts`, `unused_interrupt_handler` | `drivers/interrupts.h:5-83` | U-PND-FLT | all ISRs | 502a, 502b |
| UN-32 | `register_set*`, `check_registers` | `drivers/registers.h:24-77` | U-PND-FLT | any, tick | 503a |
| UN-33 | `set_power_save_state`, `enable_can_transceivers` | `sys/power_saving.h:15-55` | U-PND-PWR | SPI ISR, tick | 508a, 513 |
| UN-34 | `NMI_Handler`, `HardFault_Handler`, early init | `early_init.h:60-81` | U-PND-PLAT | exception | 502a |
| UN-35 | bootstub `main` | `bootstub.c:33-82` | U-PND-BOOT | thread | 511 |
| UN-N1 | (new) periodic safety task | — | U-PND-MAIN | new timer ISR | 401a, 407, 408, 413, 501, 506 |
| UN-N2 | (new) fault reaction `enter_safe_state(reason)` | — | U-PND-FLT | any | 502, 108a |
| UN-N3 | (new) zero-torque frame generator | — | U-SAF-TOY | TX path, safety task | 109, 109a |
| UN-N4 | (new) RX plausibility (rate, frozen, cross-checks) | — | U-SAF-CORE/TOY | RX ISR, safety task | 403–405 |
| UN-N5 | (new) start-up tests | — | U-PND-PLAT | thread before IRQs | 515 |
| UN-N6 | (new) SPI CRC and sequence check | — | U-PND-SPI/COMMS | ISR | 410, 410a, 411 |

## 3. Unit design descriptions (safety layer)

### UN-01 `safety_rx_hook`

| Item | Description |
|---|---|
| Purpose | Validate one received frame and update envelope state |
| Inputs | `CANPacket_t` (addr, bus, DLC, data); `current_safety_config`, `current_hooks` |
| Outputs | Return: frame valid; side effects on `controls_allowed`, brand state, `relay_malfunction`, `heartbeat_engaged_mismatches` |
| State | via UN-02, UN-06, brand hook |
| Algorithm | (1) `rx_msg_safety_check`; (2) brand RX hook only if valid **and** in the RX check list; (3) `generic_rx_checks` (brake/regen/steering edges) always; (4) for each TX message with `check_relay`, `stock_ecu_check(addr/bus match)`; (5) reset mismatch counter on authority rising edge |
| Limits | none directly |
| Error handling | invalid checksum/quality/counter → `controls_allowed = false` in `is_msg_valid` |
| Remarks | Step (3) runs for every frame, so a brake edge from a frame that fails validation is still processed through the previous `brake_pressed` value only (brand hook not run). Correct direction (revocation not lost) to be confirmed by test |

### UN-02 RX checks

| Item | Description |
|---|---|
| Purpose | Match a frame to an RX check entry; verify checksum, counter, quality; time-stamp |
| Inputs | frame, `RxCheck[]` table (Toyota: `0xAA` 83 Hz, `0x260` 50 Hz, `0x1D2` 33 Hz, `0x226` 40 Hz; `modes/toyota.h:39-46`) |
| Outputs | index; `status.valid_checksum`, `wrong_counters`, `valid_quality_flag`, `last_timestamp` |
| Algorithm | Linear search with first-match latch of the alternative address (`msg_seen`); checksum via brand callbacks unless `ignore_checksum`; counter compares expected `(last+1) mod (max+1)` and keeps a clamped 0…5 score; quality flag via callback |
| Limits | `MAX_WRONG_COUNTERS = 5` (`safety.h:54`); `MAX_ADDR_CHECK_MSGS = 3` |
| Error handling | invalid → authority cleared (`safety.h:115-118`) |
| Change | Add `0x262`, `0x1D3`, `0xB4` entries (SWSR-110, 405); rate and frozen checks (UN-N4) |

### UN-03 `safety_tx_hook`

| Item | Description |
|---|---|
| Purpose | Decide whether a SoC frame may be transmitted |
| Inputs | frame; TX whitelist; `relay_malfunction`; current mode |
| Outputs | true = transmit |
| Algorithm | whitelist by (addr, bus, length) → brand TX hook → AND with `!relay_malfunction`; ALLOUTPUT and ELM327 bypass the whitelist |
| Error handling | caller (`can_send`) counts rejection and echoes frame with `rejected=1` |
| Change | On rejection of a lateral frame while engaged: revoke and request substitute frame (SWSR-108, 109) |

### UN-04 `safety_fwd_hook`

Purpose: return the destination bus (0↔2) or −1. Blocked when `relay_malfunction` or `disable_forwarding`, or when the address is a `check_relay` TX message destined for that bus (static block: `0x191`, `0x412`, `0x2E4`, `0x343` towards bus 0). Runs before `safety_rx_hook` for the same frame (`drivers/fdcan.h:199, 221`), deliberately independent of RX validation (GAP-11).

### UN-05 `safety_tick`

| Item | Description |
|---|---|
| Purpose | Detect lagging RX messages |
| Algorithm | For each RX entry: lagging if `elapsed > max(10 × period, 1 s)`; invalid if frequency < 10 Hz or `is_msg_valid` false → `controls_allowed = false`, `safety_rx_checks_invalid = true` |
| Timing | Called at 1 Hz → detection 1–2 s |
| Change | 5 periods, called from UN-N1 at ≥ 50 Hz (SWSR-401, 401a) |

### UN-07 `set_safety_hooks`

Purpose: select brand hooks, reset all state. Algorithm: reset every state variable (`safety.h:425-460`), including `controls_allowed = false` and `relay_malfunction = false`; linear search of the registry (debug-only modes under `ALLOW_DEBUG`, `safety.h:413-422`); call brand `init(param)`; zero all RX status. Returns −1 for an unknown mode, after the state reset, with `current_hooks` unchanged; the caller then sets SILENT (`main.c:33-40`). Changes: do not clear the relay latch (SWSR-506a); accept only the locked configuration (SWSR-512).

### UN-08 `pcm_cruise_check` and engagement state machine

See §5.2.

### UN-10 `steer_torque_cmd_checks`

| Item | Description |
|---|---|
| Purpose | Check one lateral torque command |
| Inputs | `desired_torque` (raw), `steer_req`, `TorqueSteeringLimits` (Toyota: `modes/toyota.h:172-186`); state `desired_torque_last`, `rt_torque_last`, `ts_torque_check_last`, `valid/invalid_steer_req_count`, `ts_steer_req_mismatch_last`; `torque_meas`; `controls_allowed`; µs timer |
| Outputs | violation flag; updated state |
| Algorithm | If engaged: (1) max-torque (optionally speed-dependent); (2) motor-limited check `dist_to_meas_check` (rate up/down relative to last, and ≤ meas ± 350); (3) store last; (4) RT window ±450 vs `rt_torque_last`, window restarted after 250 ms. Always: (5) torque ≠ 0 while not engaged → violation; (6) steer-request tolerance (17 valid frames, 1 invalid, 162 ms); (7) on violation or not engaged: reset all state |
| Limits | 1500, 15, 25, 350, 450 / 250 ms, 17, 1, 162 ms (raw) |
| Error handling | returns violation; caller drops frame |
| Remarks | Rate state is updated before the RT check so a rejected frame still sets `desired_torque_last`; step (7) resets it to 0 on violation. Rate limit relative to `max(last, 0)` makes the allowed range asymmetric around 0 by design |
| Changes | SWSR-105 (reject `steer_req` without authority), SWSR-108 (revoke), SWSR-102 (table), SWSR-304 (driver check in addition to motor check) |

### UN-11 limit helpers

`dist_to_meas_check` (`lateral.h:10-23`): allowed band = intersection of rate band `[min(last,0) − up, max(last,0) + up]` and a measured band that allows moving towards zero at `down`. `driver_limit_check` (`lateral.h:26-46`): same structure with driver-torque-based band; unused by Toyota today. `rt_torque_rate_limit_check` (`lateral.h:49-57`): ±450 band around `rt_torque_last`.

### UN-12 longitudinal

`get_longitudinal_allowed = controls_allowed && !gas_pressed_prev`. `longitudinal_accel_checks` returns violation unless (allowed and within [min, max]) or equal to `inactive_accel` (0 for Toyota, implicit). Changes: jerk limits (SWSR-204/205), wind-down (206), explicit inactive constant (203).

### UN-13 helpers

Statement-expression macros (GNU extension, WP-W-01 DEV records); `safety_interpolate` holds end values and protects `dx` from zero (`helpers.h:80-104`), 3-point tables; `safety_get_ts_elapsed` relies on unsigned wrap-around (correct for 32-bit µs counter, wrap ≈ 71.6 min).

### UN-14 `toyota_rx_hook`

| Signal | Frame / bits | Use |
|---|---|---|
| EPS motor torque | `0x260` bytes 5–6, signed, × factor/100, then min−1 / max+1 | `torque_meas` (UN-10) |
| Driver torque | `0x260` bytes 1–2 | `torque_driver` (LTA only today) |
| CRUISE_ACTIVE | `0x1D2` bit 5 | `pcm_cruise_check` |
| GAS_RELEASED | `0x1D2` bit 4 (inverted) | `gas_pressed` |
| BRAKE_PRESSED | `0x226` bit 37 | `brake_pressed` |
| Wheel speeds | `0xAA` 4 × 15 bit, offset 6767 | `vehicle_moving`, `vehicle_speed` |

Runs only for valid, whitelisted frames. Changes: driver override (SWSR-304a), EPS status (SWSR-110), cross-checks (SWSR-405).

### UN-15 `toyota_tx_hook`

Per-address checks: `0x343` ACCEL_CMD bounds/inactive (+ stock-long cancel-only branch); `0x183` (SecOC, unused); `0x283` zero payload; `0x191` no actuation in LKA config; `0x131` (SecOC); `0x2E4` → UN-10; `0x750` tester present only. Default: frames on the whitelist without a specific check pass (e.g. `0x412`, `0x1D2`, `0x344`, `0x411`, DSU set). Changes: SWSR-207, 705, 109.

### UN-16 `toyota_init`

Decodes `param`: low byte = EPS factor, bit 8 ALT_BRAKE, bit 9 STOCK_LONGITUDINAL, bit 10 LTA, bit 11 SECOC (debug only); selects TX list and RX check table. No range check (GAP-44). Change: accept only 73 with no flags in the reference build (SWSR-104a, 512).

## 4. Unit design descriptions (panda platform)

### UN-18 `set_safety_mode`

Calls UN-07; on failure falls back to SILENT and `assert_fatal`s if SILENT fails (`main.c:33-40`); clears `safety_tx_blocked` and `safety_rx_invalid`; sets relay and CAN mode per mode (§5.1); re-initialises all CAN cores (`can_init_all`). Changes: reject non-locked requests (SWSR-512); replace `assert_fatal` hang by reset (SWSR-502a).

### UN-19 `tick_handler`

Described in [WP-W-03 §5.2](WP-W-03-software-architecture.md). Heartbeat logic at 1 Hz: `heartbeat_counter` incremented every second and cleared by `0xf3`; mismatch of authority and `heartbeat_engaged` for 3 ticks clears authority; counter ≥ 5 (ignition) / 2 → `heartbeat_lost`, siren 3 s if authority was recent, SILENT, power save. Changes: move supervision into UN-N1 with 0.3 s limits (SWSR-307, 407, 510).

### UN-21 `comms_control_handler`

One switch over the request byte. Safety-relevant cases and their gating:

| Request | Effect | Gating today | Required |
|---|---|---|---|
| `0xdc` | set mode/param | none | SWSR-512 |
| `0xf3` | heartbeat | none | + loop counter (SWSR-409) |
| `0xc5` | drive relay | none | SWSR-513 |
| `0xd1` | bootloader (0, debug only) / softloader (1) | partial | SWSR-511a |
| `0xd8` | MCU reset | none | WP-W-02 OI-5 |
| `0xdb`, `0xde`, `0xe5`, `0xe6`, `0xe7`, `0xe8`, `0xf1`, `0xf9`, `0xfc` | CAN/clock/power config | none (`0xe8` no bound) | SWSR-513, 412a |
| `0xdf`, `0xf8` | alt. experience, disable heartbeat | rejected in car modes | keep |
| `0xd2` | health | — | add reason code (SWSR-108a) |

### UN-22 CAN stream packing

`comms_can_write` reassembles packets that span transfers using a 72-byte buffer and `dlc_to_len[data[pos] >> 4]` (max 70 bytes); complete packets go to `can_send(…, false)`. `comms_can_read` drains `can_rx_q` into the MISO buffer. No sequence counter. Changes: SWSR-410a, 411, 412b.

### UN-23 SPI protocol state machine

| State | Event | Guard | Action | Next |
|---|---|---|---|---|
| HEADER | 7 bytes received | "VERSION" | version response | HEADER_NACK |
| HEADER | 7 bytes | sync 0x5A and XOR ok | send HACK | HEADER_ACK |
| HEADER | 7 bytes | else | send NACK | HEADER_NACK |
| HEADER_ACK | ACK sent | — | DMA `len_mosi + 1` bytes | DATA_RX |
| DATA_RX | data received | XOR ok and endpoint handler ACKs | DACK + response + XOR | DATA_TX |
| DATA_RX | data received | else | NACK | HEADER_NACK |
| DATA_TX / HEADER_NACK | TX complete | — | DMA 7 bytes | HEADER |

`spi_error_count` incremented when the checksum is invalid (`drivers/spi.h:220-222`). Changes: length guard in HEADER (SWSR-412), CRC (410), DMA error flags (410b).

### UN-25 `can_rx`

Per frame in FIFO 0: build `CANPacket_t`, forward (UN-04, `can_send` with `skip_tx_hook = true`), `safety_rx_hook`, `ignition_can_hook`, push to `rx_q`, enable CAN-FD/BRS if seen. Errors → `update_can_health_pkt`, bus-off → core reset.

### UN-27 `can_send`

If TX hook passes (or skipped): push to the bus queue (overflow counted) and call `process_can`; else count `safety_tx_blocked`, mark `rejected`, echo to `rx_q`. Change: on rejected lateral frame, push the substitute zero-torque frame (SWSR-109).

### UN-28 harness

Relay outputs open-drain, active low; `set_intercept_relay` busy-waits on `sbu_adc_lock`. Orientation via SBU ADC compared with AVDD/2 only while the relay is not driven. Changes: readback (SWSR-506), orientation loss reaction (SWSR-701).

### UN-29…32 fault units

`fault_occurred` sets a bit and status; `PERMANENT_FAULTS = 0` so no fault is permanent; nothing reacts. Software watchdog compares tick intervals inside the tick ISR (threshold 375 ms, `main.c:301`). Interrupt-rate fault raised when a handler is called more often than its limit in a second. Register check compares masked register values at 1 Hz. Change: UN-N2 `enter_safe_state(reason)` called by all of them (SWSR-502).

### UN-35 bootstub

Soft flasher if the softloader magic is set; else length check, SHA-1 over the image, version tag, RSA-1024 against the release key (debug key only under `ALLOW_DEBUG`), jump or `fail()`. Change: SWSR-511, 501b (start IWDG).

## 5. Normative state tables

### 5.1 Safety-mode transitions (UN-18/UN-07)

| Current | Event | Guard | Action | Next |
|---|---|---|---|---|
| any | reset | — | `set_safety_mode(SILENT)` | SILENT |
| any | `0xdc` (m, p) | m in registry | reset state; relay per m; CAN re-init | m |
| any | `0xdc` (m, p) | m unknown | state reset; SILENT | SILENT |
| car mode | 1 Hz tick | heartbeat counter ≥ 5 (ign) / 2 | siren if recent authority; `heartbeat_lost` | SILENT |
| any | harness status change | — | `set_safety_mode(current)` (state reset) | same |

### 5.2 Authority (`controls_allowed`) for the Toyota mode

| # | Current | Event | Guard | Action | Next |
|---|---|---|---|---|---|
| T1 | NOT_ALLOWED | `0x1D2` valid | CRUISE_ACTIVE = 1 and previous = 0 | set | ALLOWED |
| T2 | ALLOWED | `0x1D2` valid | CRUISE_ACTIVE = 0 | clear | NOT_ALLOWED |
| T3 | ALLOWED | any RX | `brake_pressed` and (not previously pressed or vehicle moving) | clear | NOT_ALLOWED |
| T4 | ALLOWED | RX of checked message | checksum or quality invalid | clear | NOT_ALLOWED |
| T5 | ALLOWED | `safety_tick` | any message lagging or invalid | clear | NOT_ALLOWED |
| T6 | ALLOWED | 1 Hz tick | `!heartbeat_engaged` for 3 ticks | clear | NOT_ALLOWED |
| T7 | any | mode change | — | clear | NOT_ALLOWED |
| T8 | NOT_ALLOWED | `0x1D2` | CRUISE_ACTIVE = 1 and previous = 1 | none | NOT_ALLOWED |
| T9 (new) | ALLOWED | TX violation | — | clear, reason | NOT_ALLOWED (SWSR-108) |
| T10 (new) | ALLOWED | heartbeat > 0.3 s / command stall / RX plausibility / platform fault / driver override / EPS fault | — | clear, reason | NOT_ALLOWED |

Gas pressed does not change the state; it gates longitudinal only (UN-12). This table is the reference for WP-W-06 VS-UV-06.

## 6. Error handling and fault classification (target design)

### 6.1 Fault table for SWSR-502

| Fault | Source unit | Class (proposed) | Reaction |
|---|---|---|---|
| Relay malfunction | UN-06, SWSR-506 | latched until power cycle | TX + forwarding blocked; relay released if readback shows stuck |
| Watchdog / hang | IWDG | reset | SS-S after reset |
| Interrupt rate (CAN, SPI, tick) | UN-31 | latched for drive cycle | SS-S |
| Register divergence | UN-32 | latched | SS-S |
| RAM/flash ECC double error, image CRC | new | latched | SS-S |
| Clock drift, supply (PVD), temperature | new | recoverable with hysteresis | SS-S while active |
| SPI error burst | UN-23 | recoverable | revoke (SWSR-413) |
| Siren malfunction | U-PND-HK | report | warning only |
| Unused interrupt | UN-31 | latched | SS-S |


## 7. Compliance with unit design principles (WP-W-01 §6)

| Rule | U-SAF-* units | U-PND-* units | Finding |
|---|---|---|---|
| ENV-R-01 no dynamic memory | Yes | Yes (`-nostdlib`) | — |
| ENV-R-02 no recursion | Yes | Yes | — |
| ENV-R-03 bounded loops | Yes | Not all: `while (harness.sbu_adc_lock) {}` (`drivers/harness.h:20, 39`), SPI drain loop (`stm32h7/llspi.h:12-15`), main idle loop | Bounded waits or argued (WP-W-04 SDF-03) |
| ENV-R-04 single exit | Mostly | Mostly (switch with `break`) | Review (WP-W-01 OI-4) |
| ENV-R-05 no implicit conversion / unions | `to_signed` explicit; float in `ROUND`, `safety_interpolate` | `(uint16_t)req->param2` explicit | DEV-04 review |
| ENV-R-06 no hidden control flow | Hook table via pointer | `interrupts[].handler` pointer table | Tables constant after init; protect by MPU (SWSR-507) |
| ENV-R-07 complexity | `toyota_tx_hook` 178 lines; `steer_torque_cmd_checks` 92 lines | `comms_control_handler` 260 lines; `tick_handler` 144 lines; `spi_rx_done` 118 lines | Exceed 60-line rule; split or justify |
| ENV-R-08 range checks | EPS factor not checked | SPI lengths, `0xe8` index not checked | SWSR-104a, 412, 412a |
| ENV-R-09 plausibility | No counters (vehicle limitation) | XOR only | SWSR-403…405, 410 |
| ENV-R-10 fail-silent default | Yes | Unknown mode → SILENT | — |
| ENV-R-11 faults drive reaction | Partly | No | SWSR-502 |
| ENV-R-12 shared data documented | — | — | Done in WP-W-03 §6.3 |
| ENV-R-13 no decision before validation | — | forwarding before RX validation | Accepted by design (UN-04) |
| ENV-R-14 stack bounded | Not measured | Not measured | VS-UV-21 |
| ENV-R-15 separation | — | No MPU | SWSR-507 |

## 8. Required changes per SWSR (implementation backlog)

| SWSR | Unit(s) | Change |
|---|---|---|
| 102, 102a | UN-10, UN-16, build | Speed table for Toyota; build-time check; extend `lookup_t` if needed |
| 104a, 512 | UN-16, UN-21, UN-18 | Compiled reference configuration; reject other `0xdc` |
| 105 | UN-10 | Reject `steer_req` without authority |
| 108, 108a | UN-10/UN-03, UN-N2, UN-21 | Revoke on TX violation; reason codes in health |
| 109, 109a | UN-N3, UN-27, UN-N1 | Substitute and autonomous zero-torque frames |
| 110, 405 | UN-02, UN-14, UN-N4 | Add `0x262`, `0x1D3`, `0xB4`; cross-checks |
| 204–207 | UN-12, UN-15 | Jerk, wind-down, field checks |
| 304, 304a | UN-10, UN-14 | Driver-torque checks |
| 306, 401, 401a, 403, 404, 407, 408, 413 | UN-N1, UN-05, UN-N4 | Periodic safety task ≥ 50 Hz |
| 409, 410, 410a, 411 | UN-21, UN-22, UN-N6 | Loop counter, CRC, sequence |
| 412, 412a, 412b | UN-23, UN-21, UN-22 | Bounds checks |
| 501, 501b | UN-N1, UN-35 | IWDG |
| 502, 502a, 502b, 503a | UN-29…34, UN-N2 | Fault reaction |
| 503, 515 | UN-N5 | Start-up tests, image CRC |
| 506, 506a | UN-28, UN-07 | Readback; latch not cleared by mode change |
| 507 | UN-20 | MPU configuration |
| 511a, 513 | UN-21 | Gating in car modes |
| 705 | UN-16 | Reduced whitelist |

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm by test the behaviour noted in UN-01 (brake edge when the brake frame fails validation) | Maintainer | G3 |
| OI-2 | Decide function size limits for the large switch/ISR functions (ENV-R-07) | SW lead | G3 |
| OI-3 | Complete unit descriptions for the new units UN-N1…N6 when designed | SW lead | G3 |
| OI-4 | Review this document against the code at the next baseline (line numbers drift) | Reviewer | G3 |
