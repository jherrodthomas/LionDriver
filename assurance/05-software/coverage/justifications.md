# Structural coverage gaps and their justifications

Every function that the reference-configuration tests never enter, and every decision with an uncovered branch or
MC/DC condition inside a function that ran, is listed here ([WP-W-06 §4.2.1](../WP-W-06-software-unit-verification.md)).
`tools/ci/coverage/structural_coverage.py report --check` matches each measured gap to a row by unit, function and the
decision's source line (whitespace-normalized; `*` names the whole function). It fails when a gap has no row, and when a
row no longer matches a gap, so a test that closes a gap forces its row to be removed.

Measured at opendbc `e233362`, reference build (`LIONDRIVER_REFERENCE=1`), tests `test_toyota`, `test_defaults`,
`test_elm327`. Status: drafted by the author (AI-assisted), not reviewed; an I1 review of every row is needed before the
justifications count toward G3 (WP-P-05). CJ-16 and CJ-28 (reachable, test needed) were removed at the pin bump to `515b9a2`, which contains their tests (opendbc#16: `test_angle_meas_ignores_initializing_frames`, `test_tx_rate_rejected_count_saturates`); the IDs are not reused.

Class: **N** not called in the reference configuration (no caller in the Toyota, ELM327 or no-output modes);
**C** a condition fixed by the reference configuration's constant data, so one outcome cannot occur;
**I** infeasible: one outcome cannot occur for any input, given the surrounding code;
**T** reachable, a test is needed (open).

| ID | Unit | Function | Decision | Class | Rationale |
|---|---|---|---|---|---|
| CJ-01 | U-SAF-LAT | driver_limit_check | * | N | Called only from `steer_torque_cmd_checks` when `limits.type == TorqueDriverLimited`; Toyota uses `TorqueMotorLimited` (`modes/toyota.h` torque limits) |
| CJ-02 | U-SAF-LAT | rt_angle_rate_limit_check | * | N | Called only from `steer_angle_cmd_checks_vm`; the Toyota mode does not call the angle checks (CJ-07) |
| CJ-03 | U-SAF-LAT | rt_curvature_rate_limit_check | * | N | Called only from `steer_curvature_cmd_checks` (CJ-04) |
| CJ-04 | U-SAF-LAT | steer_curvature_cmd_checks | * | N | Curvature steering of other brands; `modes/toyota.h` has no call |
| CJ-05 | U-SAF-LAT | get_curvature_factor | * | N | Helper of the curvature and angle checks (CJ-04, CJ-07) |
| CJ-06 | U-SAF-LAT | get_angle_from_curvature | * | N | Helper of the curvature checks (CJ-04) |
| CJ-07 | U-SAF-LAT | steer_angle_cmd_checks_vm | * | N | Vehicle-model angle steering of other brands; Toyota LTA uses its own checks in `modes/toyota.h`, and the reference build refuses LTA frames |
| CJ-08 | U-SAF-LAT | steer_torque_cmd_checks | if (limits.dynamic_max_torque) { | C | `TOYOTA_TORQUE_STEERING_LIMITS` leaves `dynamic_max_torque` false, so the true branch cannot occur |
| CJ-09 | U-SAF-LAT | steer_torque_cmd_checks | if (limits.type == TorqueDriverLimited) { | C | Toyota limits are `.type = TorqueMotorLimited` |
| CJ-10 | U-SAF-LAT | steer_torque_cmd_checks | if (!limits.has_steer_req_tolerance) { | C | Toyota limits set `.has_steer_req_tolerance = true` |
| CJ-11 | U-SAF-LAT | steer_torque_cmd_checks | if (steer_req_mismatch) { | C | Inside the `!has_steer_req_tolerance` branch, which CJ-10 shows is not taken |
| CJ-12 | U-SAF-LAT | steer_torque_cmd_checks | if (invalid_steer_req_count >= limits.max_invalid_request_frames) { | C | Reached only when `invalid_steer_req_count != 0`; with Toyota's `.max_invalid_request_frames = 1` the comparison is then always true |
| CJ-13 | U-SAF-LONG | longitudinal_speed_checks | * | N | Called by other brands' TX hooks; `modes/toyota.h` has no call |
| CJ-14 | U-SAF-LONG | longitudinal_gas_checks | * | N | As CJ-13; Toyota checks acceleration through `longitudinal_accel_checks` |
| CJ-15 | U-SAF-LONG | longitudinal_brake_checks | * | N | As CJ-13 |
| CJ-17 | U-SAF-CORE | GET_BYTES_LE | * | N | Used by other brands' RX hooks; the Toyota mode reads bytes directly |
| CJ-18 | U-SAF-CORE | update_counter | * | N | Called only for RX checks without `ignore_counter`; every Toyota RX check sets `.ignore_counter = true` |
| CJ-19 | U-SAF-CORE | gen_crc_lookup_table_8 | * | N | CRC tables of other brands' `init`; Toyota computes its checksum without a table |
| CJ-20 | U-SAF-CORE | gen_crc_lookup_table_16 | * | N | As CJ-19 |
| CJ-21 | U-SAF-CORE | speed_mismatch_check | * | N | Called by the angle and curvature checks of other brands (CJ-04, CJ-07) |
| CJ-22 | U-SAF-CORE | is_msg_valid | if (!addr_list[index].status.valid_checksum \|\| !addr_list[index].status.valid_quality_flag \|\| (addr_list[index].status.wrong_counters >= MAX_WRONG_COUNTERS)) { | C | The `wrong_counters` condition cannot become true: no Toyota RX check counts counters (CJ-18) |
| CJ-23 | U-SAF-CORE | get_addr_check_index | for (uint8_t j = 0U; (j < MAX_ADDR_CHECK_MSGS) && (addr_list[i].msg[j].addr != 0); j++) { | C | Every Toyota RX check lists one message and ends with `{ 0 }`, so the loop always stops on `addr != 0` before the `MAX_ADDR_CHECK_MSGS` bound; the bound is defensive |
| CJ-24 | U-SAF-CORE | rx_msg_safety_check | if ((safety_hooks->get_checksum != NULL) && (safety_hooks->compute_checksum != NULL) && !cfg->rx_checks[index].msg[cfg->rx_checks[index].status.index].ignore_checksum) { | C | The Toyota hooks define both `get_checksum` and `compute_checksum`, so the first two conditions are always true; the ELM327 and no-output modes have no RX checks |
| CJ-25 | U-SAF-CORE | rx_msg_safety_check | if ((safety_hooks->get_counter != NULL) && (cfg->rx_checks[index].msg[cfg->rx_checks[index].status.index].max_counter > 0U)) { | C | The Toyota hooks define no `get_counter` |
| CJ-26 | U-SAF-CORE | rx_msg_safety_check | cfg->rx_checks[index].status.wrong_counters = cfg->rx_checks[index].msg[cfg->rx_checks[index].status.index].ignore_counter ? 0 : MAX_WRONG_COUNTERS; | C | Every Toyota RX check sets `.ignore_counter = true`, so the expression always yields 0 and the `MAX_WRONG_COUNTERS` outcome cannot occur |
| CJ-27 | U-SAF-CORE | rx_msg_safety_check | if ((safety_hooks->get_quality_flag_valid != NULL) && !cfg->rx_checks[index].msg[cfg->rx_checks[index].status.index].ignore_quality_flag) { | C | The Toyota hooks define `get_quality_flag_valid`, so the first condition is always true |
| CJ-29 | U-SAF-CORE | safety_fwd_hook | if (m->check_relay && !m->disable_static_blocking && (m->addr == addr) && (m->bus == (unsigned int)destination_bus)) { | C | No Toyota TX message sets `.disable_static_blocking`, so `!m->disable_static_blocking` is always true |
| CJ-30 | U-SAF-CORE | safety_fwd_hook | if (!blocked && (current_hooks->fwd != NULL)) { | C | The Toyota, ELM327 and no-output hooks define no `fwd` |
| CJ-31 | U-SAF-CORE | rx_check_lagging | if (current_safety_config.rx_timeout_periods > 0U) { | C | The reference build sets `rx_timeout_periods` for Toyota (TSR-401); the false branch is the upstream build's path |
| CJ-32 | U-SAF-CORE | rx_checks_allow_engagement | if (current_safety_config.rx_timeout_periods > 0U) { | C | As CJ-31 (TSR-306) |
| CJ-33 | U-SAF-CORE | safety_tick | if (lagging \|\| frequency_invalid \|\| !is_msg_valid(current_safety_config.rx_checks, i)) { | C | `frequency_invalid` is `frequency < 10`; every Toyota RX check is configured at 25 Hz or more, so it is always false |
| CJ-34 | U-SAF-CORE | generic_rx_checks | if (regen_braking && (!regen_braking_prev \|\| vehicle_moving)) { | C | `regen_braking` is set only by other brands' RX hooks |
| CJ-35 | U-SAF-CORE | generic_rx_checks | if (steering_disengage && !steering_disengage_prev) { | C | `steering_disengage` is set only by other brands' RX hooks |
| CJ-36 | U-SAF-CORE | set_safety_hooks | if ((set_status == 0) && (current_hooks->init != NULL)) { | C | The Toyota, ELM327 and no-output hooks all define `init` |
