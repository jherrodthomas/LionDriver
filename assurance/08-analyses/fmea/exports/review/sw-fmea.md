# SW FMEA review: safety-relevant software elements

> Generated from [`analyses/sw-fmea.yaml`](../../analyses/sw-fmea.yaml) and [`diagrams/sw-fmea.yaml`](../../diagrams/sw-fmea.yaml) by `tools/safety/fmea_review_md.py`. Edit the YAML and regenerate; never edit this page. A styled workbook of the same data is [`sw-fmea-review.xlsx`](sw-fmea-review.xlsx).

| Revision | Status | Baseline | Rating tables | Updated |
|---|---|---|---|---|
| 0.7 | draft | BL-004 | RT-1 | 2026-10-13 |

**Scope.** P1 elements for AC-001 at BL-004 (liondriver-dev 682f184, panda 8aa8671, opendbc 7993399): panda safety model (opendbc safety core, Toyota mode, panda firmware integration incl. hardware watchdog; rated at BL-003, unchanged at BL-004 outside the reference build), pandad (SWF-020..029), selfdrived (SWF-030..039), controlsd with the Toyota CarController hand-off (SWF-040..049).

**Team.** Jherrod Thomas (Project maintainer, safety lead (reviewer/approver)); Claude (AI assistant) (Drafting assistance; ratings require human review)

![Summary](figures/sw-fmea-summary.svg)

## How to review

Read the diagrams first, then the worksheet. Comment on this page's lines in a pull request, or open an issue that names the failure mode or cause ID. For a rating, say which value you would give and why; the scales are in [rating-tables.md](../../rating-tables.md). Action priority follows the AIAG-VDA table and is checked by `fmea_lint.py`, so challenge S, O or D, not the AP.

## Contents

- [Block and boundary diagram](#1-block-and-boundary-diagram)
- [P-diagram](#2-p-diagram)
- [Structure and functions](#3-structure-and-functions)
- [Worksheet](#4-worksheet)
- [Actions](#5-actions)
- [Priority H causes without a completed action](#6-priority-h-causes-without-a-completed-action)

## 1. Block and boundary diagram

![Software architecture: engagement and actuation path](figures/sw-fmea-block.svg)

**Interface matrix.** Each line in the diagram, with what crosses it.

| ID | From | To | Type | What crosses | Source |
|---|---|---|---|---|---|
| I01 | modeld | Control + Toyota CarCtrl | data | modelV2 (20 Hz) | <sub>assurance/05-software/WP-W-03-software-architecture.md §4.2; openpilot/selfdrive/controls/controlsd.py:35</sub> |
| I02 | modeld | selfdrived | data | modelV2 (alive check) | <sub>openpilot/selfdrive/selfdrived/selfdrived.py:98, 179</sub> |
| I03 | plannerd | Control + Toyota CarCtrl | data | longitudinalPlan | <sub>assurance/05-software/WP-W-03-software-architecture.md §4.2; openpilot/selfdrive/controls/controlsd.py:36</sub> |
| I04 | dmonitoringd | selfdrived | data | driverMonitoringState | <sub>openpilot/selfdrive/selfdrived/selfdrived.py:98-99</sub> |
| I05 | selfdrived | Control + Toyota CarCtrl | data | selfdriveState (100 Hz) | <sub>assurance/05-software/WP-W-03-software-architecture.md §4.2; openpilot/selfdrive/controls/controlsd.py:110-114</sub> |
| I06 | Control + Toyota CarCtrl | selfdrived | data | controlsState+carControl | <sub>openpilot/selfdrive/controls/controlsd.py:52; openpilot/selfdrive/selfdrived/selfdrived.py:101</sub> |
| I07 | selfdrived | pandad | data | selfdriveState.enabled | <sub>openpilot/selfdrive/pandad/pandad.cc:421, 439</sub> |
| I08 | Control + Toyota CarCtrl | pandad | data | sendcan (100 Hz) | <sub>openpilot/selfdrive/car/card.py:234-238; openpilot/selfdrive/pandad/pandad.cc:64, 79</sub> |
| I09 | pandad | card (CAN parse) | data | can (RX frames) | <sub>openpilot/selfdrive/pandad/pandad.cc:104</sub> |
| I10 | card (CAN parse) | Control + Toyota CarCtrl | data | carState (100 Hz) | <sub>assurance/05-software/WP-W-03-software-architecture.md §4.2; openpilot/selfdrive/car/card.py:69</sub> |
| I11 | card (CAN parse) | selfdrived | data | carState (events) | <sub>assurance/05-software/WP-W-03-software-architecture.md §4.2; openpilot/selfdrive/selfdrived/selfdrived.py:161</sub> |
| I12 | pandad | selfdrived | data | pandaStates (10 Hz) | <sub>openpilot/selfdrive/pandad/pandad.cc:285; openpilot/selfdrive/selfdrived/selfdrived.py:339-351, 537</sub> |
| I13 | pandad | Panda safety model | data ⇄  | SPI CAN ep 1/3 | <sub>assurance/03-system/WP-S-05-hsi-specification.md §2 HSI-03, §11.2 S-16/S-17; openpilot/selfdrive/pandad/panda.cc:189-196</sub> |
| I14 | pandad | Panda safety model | data | heartbeat 0xf3 engaged | <sub>openpilot/selfdrive/pandad/pandad.cc:328; panda/board/main_comms.h:299-305; WP-S-05 §11.2 S-18</sub> |
| I15 | pandad | Panda safety model | data | safety mode 0xdc | <sub>openpilot/selfdrive/pandad/panda_safety.cc:80, 87; WP-S-05 §4.2, §11.2 S-19</sub> |
| I16 | Panda safety model | pandad | data | health 0xd2 | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.2 S-21; WP-W-03 §3.3 SI-13</sub> |
| I17 | Panda safety model | Panda HW / FDCAN | data ⇄  | tx/rx/fwd hooks | <sub>assurance/05-software/WP-W-03-software-architecture.md §3.3 SI-01/SI-02; opendbc_repo/opendbc/safety/safety.h:201, 293</sub> |
| I18 | Panda HW / FDCAN | Vehicle (Corolla TSS2) | data ⇄  | CAN 0x2E4/0x343, RX | <sub>assurance/03-system/WP-S-05-hsi-specification.md §2 HSI-04, §11.1; opendbc_repo/opendbc/safety/modes/toyota.h:11-17, 48</sub> |
| I19 | selfdrived | ui / soundd | data | selfdriveState alerts | <sub>openpilot/selfdrive/ui/soundd.py:56-59, 149; WP-W-03 §4.1 host.hmi</sub> |

## 2. P-diagram

![P-diagram: engagement and actuation authority](figures/sw-fmea-p-diagram.svg)

| Function covered | Description |
|---|---|
| `SWF-FN-002` | Block steering requests outside torque magnitude, rate and measured-torque-error limits, and any torque while controls are not allowed |
| `SWF-FN-004` | Allow controls on rising edge of PCM cruise; withdraw on cruise off, brake press, invalid or lagging safety messages |
| `SWF-FN-010` | Withdraw controls when the host heartbeat is lost or reports not engaged |
| `SWF-FN-012` | Route every host transmission through the safety check |
| `SWF-FN-020` | Send the heartbeat at 10 Hz. It reports engaged only while the SoC is engaged and actively commanding, so that the panda can withdraw authority when the host stops (supports FSR-005 and FSR-007, which are allocated to EL-07) |
| `SWF-FN-021` | Put the panda in the safety model, parameter and alternative experience for the identified vehicle, only when onroad, and in NO_OUTPUT when offroad, with ignition off or on exit |
| `SWF-FN-022` | Forward each sendcan batch to the panda once, in order, only while it is fresh, and make any failure to forward visible to the SoC |
| `SWF-FN-031` | Go to disabled in the same cycle on USER_DISABLE or IMMEDIATE_DISABLE, and within SOFT_DISABLE_TIME on a persisting SOFT_DISABLE |
| `SWF-FN-032` | Raise fault and driver-action events from carState, pandaStates and process/message supervision, including controlsMismatch when the panda safety model, parameter or controls-allowed disagrees |
| `SWF-FN-040` | Request lateral control only while selfdriveState is active, no EPS fault is reported and the car is above the minimum steer speed; request longitudinal control only while enabled and not overridden |
| `SWF-FN-041` | Compute actuation only from fresh, valid and finite inputs (selfdriveState, modelV2, longitudinalPlan, vehicleParameters, lateralTorqueParameters, deviceMotion), and stop actuating otherwise |
| `SWF-FN-045` | Apply torque magnitude, rate and measured-torque limits; send zero torque with the request bit cleared when lateral control is not active; send the ACC command within the acceleration range |

| Control factor | Source |
|---|---|
| Heartbeat 0xf3 + engaged flag, 0.3 s revoke | <sub>openpilot/selfdrive/pandad/pandad.cc:328, 439; panda/board/drivers/heartbeat_monitor.h:15; panda/board/main.c:240-242</sub> |
| TX whitelist and Toyota TX checks | <sub>opendbc_repo/opendbc/safety/safety.h:232-241, 293; opendbc_repo/opendbc/safety/modes/toyota.h:297</sub> |
| controls_allowed gated on PCM rising edge | <sub>opendbc_repo/opendbc/safety/safety.h:683-711 (pcm_cruise_check), 500-520 (generic_rx_checks)</sub> |
| ControlsMismatch 2 samples, 0.5 s, grace | <sub>openpilot/selfdrive/selfdrived/selfdrived.py:50-52, 127, 537-539; openpilot/selfdrive/selfdrived/supervision.py:4 (TSR-621)</sub> |
| Stale-input checks (inputs_fresh, age < 1 s) | <sub>openpilot/selfdrive/controls/controlsd.py:34-36, 119-120; openpilot/selfdrive/pandad/pandad.cc:79; openpilot/selfdrive/car/card.py:234</sub> |
| Firmware torque and accel limit checks | <sub>opendbc_repo/opendbc/safety/lateral.h:10-150; opendbc_repo/opendbc/safety/longitudinal.h:3-12 (SWF-FN-002/003)</sub> |

## 3. Structure and functions

![Structure tree](../../figures/generated/fig-3-5-swf-structure.svg)

The failure chains (element → function → failure mode → causes) are drawn in [figures/generated](../../figures/generated/README.md).

| Element | Kind | Functions |
|---|---|---|
| `SWF-SE-001` Panda safety model (opendbc safety + panda firmware integration) | sw_element | — |
| &nbsp;&nbsp;&nbsp;`SWF-SE-002` RX validation and RX timing checks | sw_unit | `SWF-FN-005` Validate safety-relevant RX messages (checksum, counter, quality flag, timing) |
| &nbsp;&nbsp;&nbsp;`SWF-SE-003` TX whitelist and dispatch | sw_unit | `SWF-FN-001` Transmit only whitelisted messages, each passed through the mode-specific check |
| &nbsp;&nbsp;&nbsp;`SWF-SE-004` Forwarding hook | sw_unit | `SWF-FN-007` Block stock-camera messages the item replaces; forward all others, including stock pre-collision messages |
| &nbsp;&nbsp;&nbsp;`SWF-SE-005` Controls-allowed logic | sw_unit | `SWF-FN-004` Allow controls on rising edge of PCM cruise; withdraw on cruise off, brake press, invalid or lagging safety messages |
| &nbsp;&nbsp;&nbsp;`SWF-SE-006` Steering torque checks | sw_unit | `SWF-FN-002` Block steering requests outside torque magnitude, rate and measured-torque-error limits, and any torque while controls are not allowed |
| &nbsp;&nbsp;&nbsp;`SWF-SE-007` Longitudinal checks | sw_unit | `SWF-FN-003` Block acceleration outside the range, and any non-inactive acceleration while controls are not allowed or the accelerator is pressed |
| &nbsp;&nbsp;&nbsp;`SWF-SE-008` Toyota safety mode | sw_unit | `SWF-FN-006` Decode Toyota vehicle state: EPS torque, cruise state, brake, accelerator, wheel speeds |
| &nbsp;&nbsp;&nbsp;`SWF-SE-009` Relay malfunction detection | sw_unit | `SWF-FN-008` Detect a relay malfunction and block all item transmission |
| &nbsp;&nbsp;&nbsp;`SWF-SE-010` Safety mode registry and initialization | sw_unit | `SWF-FN-009` Install only the safety model and parameter intended for the vehicle |
| &nbsp;&nbsp;&nbsp;`SWF-SE-011` Panda main loop: safety mode and heartbeat | sw_unit | `SWF-FN-010` Withdraw controls when the host heartbeat is lost or reports not engaged |
| &nbsp;&nbsp;&nbsp;`SWF-SE-012` Panda host command handler | sw_unit | `SWF-FN-011` Accept host configuration commands only when they cannot widen what is transmitted |
| &nbsp;&nbsp;&nbsp;`SWF-SE-013` Panda CAN send path | sw_unit | `SWF-FN-012` Route every host transmission through the safety check |
| &nbsp;&nbsp;&nbsp;`SWF-SE-014` Panda hardware watchdog and 100 Hz safety task | sw_unit | `SWF-FN-013` Reset the MCU, which releases the relay, within 0.1 s when the safety task or main loop stops; never reset while both run normally |
| `SWF-SE-020` pandad (panda daemon and SoC-panda link) | sw_element | — |
| &nbsp;&nbsp;&nbsp;`SWF-SE-021` Main loop and heartbeat | sw_unit | `SWF-FN-020` Send the heartbeat at 10 Hz. It reports engaged only while the SoC is engaged and actively commanding, so that the panda can withdraw authority when the host stops (supports FSR-005 and FSR-007, which are allocated to EL-07) |
| &nbsp;&nbsp;&nbsp;`SWF-SE-022` Safety mode setter | sw_unit | `SWF-FN-021` Put the panda in the safety model, parameter and alternative experience for the identified vehicle, only when onroad, and in NO_OUTPUT when offroad, with ignition off or on exit |
| &nbsp;&nbsp;&nbsp;`SWF-SE-023` sendcan forwarding thread | sw_unit | `SWF-FN-022` Forward each sendcan batch to the panda once, in order, only while it is fresh, and make any failure to forward visible to the SoC |
| &nbsp;&nbsp;&nbsp;`SWF-SE-024` CAN RX and panda state publishing | sw_unit | `SWF-FN-023` Publish received CAN and the panda state (mode, parameter, controlsAllowed, RX-check validity, faults) correctly and on time, so the SoC can detect a mismatch or fault and disable |
| &nbsp;&nbsp;&nbsp;`SWF-SE-025` SPI transport | sw_unit | `SWF-FN-024` Transfer commands and data between SoC and panda without undetected corruption. Detect link failure in bounded time and report it |
| &nbsp;&nbsp;&nbsp;`SWF-SE-026` Launcher and firmware check | sw_unit | `SWF-FN-025` Run pandad only against the intended panda firmware. Recover a panda in DFU or bootstub without disturbing an active drive |
| `SWF-SE-030` selfdrived (engagement supervision) | sw_element | — |
| &nbsp;&nbsp;&nbsp;`SWF-SE-031` Engagement state machine | sw_unit | `SWF-FN-030` Engage only on an ENABLE event with no NO_ENTRY event active<br>`SWF-FN-031` Go to disabled in the same cycle on USER_DISABLE or IMMEDIATE_DISABLE, and within SOFT_DISABLE_TIME on a persisting SOFT_DISABLE<br>`SWF-FN-037` Enter overriding while the driver steers and yield lateral control |
| &nbsp;&nbsp;&nbsp;`SWF-SE-032` Input sampling and event generation | sw_unit | `SWF-FN-032` Raise fault and driver-action events from carState, pandaStates and process/message supervision, including controlsMismatch when the panda safety model, parameter or controls-allowed disagrees<br>`SWF-FN-038` Detect PCM cruise active while not engaged and warn the driver<br>`SWF-FN-049` Raise the forward collision warning only from fresh and valid modelV2 and longitudinalPlan inputs (TSR-625) |
| &nbsp;&nbsp;&nbsp;`SWF-SE-033` Event catalogue and reaction mapping | sw_unit | `SWF-FN-033` Give each event the reaction type (no entry, soft or immediate disable, user disable) and alert its fault requires |
| &nbsp;&nbsp;&nbsp;`SWF-SE-034` Alert manager | sw_unit | `SWF-FN-034` Present the most urgent alert; every takeover request visual and audible |
| &nbsp;&nbsp;&nbsp;`SWF-SE-035` Excessive actuation check | sw_unit | `SWF-FN-035` Detect excessive longitudinal or lateral vehicle response while engaged and soft-disable |
| &nbsp;&nbsp;&nbsp;`SWF-SE-036` selfdriveState publication and main loop | sw_unit | `SWF-FN-036` Publish selfdriveState (enabled, active, alert) every 10 ms cycle, consistent with the state machine |
| `SWF-SE-040` Control (controlsd, lateral/longitudinal controllers, Toyota CarController hand-off) | sw_element | — |
| &nbsp;&nbsp;&nbsp;`SWF-SE-041` controlsd main loop, input handling and actuator gating | sw_unit | `SWF-FN-040` Request lateral control only while selfdriveState is active, no EPS fault is reported and the car is above the minimum steer speed; request longitudinal control only while enabled and not overridden<br>`SWF-FN-041` Compute actuation only from fresh, valid and finite inputs (selfdriveState, modelV2, longitudinalPlan, vehicleParameters, lateralTorqueParameters, deviceMotion), and stop actuating otherwise<br>`SWF-FN-046` Request PCM cruise cancel whenever PCM cruise is engaged and the item is not enabled<br>`SWF-FN-048` Command deceleration that traffic does not require (driver-monitoring no-response, soft-disable force deceleration) only after it has been announced, and keep it announced while it lasts (TSR-624) |
| &nbsp;&nbsp;&nbsp;`SWF-SE-042` Lateral torque controller | sw_unit | `SWF-FN-042` Generate a steering torque request that tracks the limited desired curvature within the envelope and yields while the driver steers |
| &nbsp;&nbsp;&nbsp;`SWF-SE-043` Longitudinal controller | sw_unit | `SWF-FN-044` Generate an acceleration request within the range and rate envelope from the longitudinal plan |
| &nbsp;&nbsp;&nbsp;`SWF-SE-044` Curvature limiter | sw_unit | `SWF-FN-043` Limit desired curvature to the lateral acceleration, lateral jerk and curvature bounds |
| &nbsp;&nbsp;&nbsp;`SWF-SE-045` Toyota CarController | sw_unit | `SWF-FN-045` Apply torque magnitude, rate and measured-torque limits; send zero torque with the request bit cleared when lateral control is not active; send the ACC command within the acceleration range<br>`SWF-FN-050` Send the inactive acceleration in ACC_CONTROL whenever longitudinal control is not active |
| &nbsp;&nbsp;&nbsp;`SWF-SE-046` card actuation hand-off | sw_unit | `SWF-FN-047` Deliver every 10 ms control step to the vehicle, and stop sending item frames when carControl is no longer received |

## 4. Worksheet

One table per failure mode, grouped by structure element. S is the failure mode's severity (its worst end effect); each cause has its own occurrence (O), detection (D) and action priority (AP).

### `SWF-SE-002` RX validation and RX timing checks

#### SWF-005 · Corrupted brake-pressed value accepted

🔴 **H** · **S 10** · guideword *corrupted* · function `SWF-FN-005` Validate safety-relevant RX messages (checksum, counter, quality flag, timing)

Effects:

- **End:** Automation not released on brake (HZ-008, S 10)
- **Next higher:** Controls not withdrawn on driver braking
- **Local:** Brake press read as released

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-005.C1` BRAKE_MODULE (0x226) has no checksum or counter in the vehicle DBC; the RX check ignores checksum, counter and quality and checks timing only | • CAN CRC protects the transport; the vehicle message itself has no end-to-end protection (toyota_nodsu_pt.dbc:18-21; toyota.h:46) <sub>opendbc_repo/opendbc/dbc/generator/toyota/toyota_nodsu_pt.dbc</sub> | • No test targets this cause | 3 | 9 | 🔴 **H** | SWF-ACT-006 |

Safety mechanisms: PCM cancels cruise on its own brake input and the panda follows PCM_CRUISE (checksum-checked); credit needs FSC FOI-006

<sub>Note: Diverse path: the PCM cancels cruise on its own brake input and the panda follows PCM_CRUISE (checksum-checked). That credit needs FSC FOI-006.</sub>

#### SWF-006 · Stale brake, cruise or EPS data used beyond the detection budget

🔴 **H** · **S 10** · guideword *value_stale* · function `SWF-FN-005` Validate safety-relevant RX messages (checksum, counter, quality flag, timing)

Effects:

- **End:** Automation not released, or limits computed from stale data (HZ-008, S 10)
- **End:** Contributes to HZ-002 (HZ-002, S 10)
- **End:** Contributes to HZ-006 (stale cruise state keeps authority; braking while not engaged, HE-04.4) (HZ-006, S 10)
- **Next higher:** Brake press or cruise-off not seen; torque measurement stale
- **Local:** Safety decisions based on old messages

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-006.C1` An RX check lags only after 5 nominal periods plus one 10 ms safety-task period (0x1D2 about 0.16 s, 0x226 about 0.14 s, 0x260 0.11 s, 0xAA about 0.07 s); the budget is not yet confirmed against an FTTI (HARA OI-004) or against real inter-frame gaps (tools/can_gaps) | • Toyota rx_timeout_periods = 5 (TSR-401, opendbc#1); safety_tick moved to a 100 Hz safety task (panda#3, SWSR-401a) <sub>opendbc_repo/opendbc/safety/safety.h</sub> | • Per-message 5-period timeout test for every Toyota RX check, in the CI safety suite <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 4 | 3 | 🔴 **H** | SWF-ACT-007 |

Safety mechanisms: RX timeout after 5 periods withdraws controls (TSR-401); SoC alerts on panda state

### `SWF-SE-004` Forwarding hook

#### SWF-010 · Stock camera steering or ACC messages forwarded while the item transmits

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-007` Block stock-camera messages the item replaces; forward all others, including stock pre-collision messages

Effects:

- **End:** Erratic or excessive steering or braking (HZ-002, S 10)
- **End:** Contributes to HZ-006 (HZ-006, S 10)
- **Next higher:** Combined or alternating commands
- **Local:** Stock and item commands both on the vehicle bus

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-010.C1` check_relay flag missing for a replaced message in the TX table, or defect in safety_fwd_hook | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: check_relay entries block forwarding of every message the item replaces

#### SWF-011 · Stock pre-collision (AEB) messages blocked

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-007` Block stock-camera messages the item replaces; forward all others, including stock pre-collision messages

Effects:

- **End:** Loss of stock AEB (HZ-011, S 10)
- **Next higher:** Stock AEB cannot act
- **Local:** PRE_COLLISION 0x283 / 0x344 from the stock camera do not reach the vehicle

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-011.C1` TX table change marks 0x283/0x344 check_relay, or a forwarding defect; at BL-001 both are check_relay=false and forwarded (toyota.h:22-23) | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: Only messages the item replaces are blocked; 0x283/0x344 are forwarded

<sub>Note: Partial answer to HARA OI-003: the panda does not block stock pre-collision messages from the camera. BL-002 removes 0x344 and the DSU messages from the TX whitelist (TSR-705, opendbc#2), so the SoC can no longer send them; 0x283 is allowed with a zero payload only. Forwarding is unchanged. In-vehicle confirmation of stock AEB is still needed.</sub>

### `SWF-SE-005` Controls-allowed logic

#### SWF-007 · Controls allowed without a driver engagement

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-004` Allow controls on rising edge of PCM cruise; withdraw on cruise off, brake press, invalid or lagging safety messages

Effects:

- **End:** Unintended engagement (HZ-010, S 10)
- **End:** Contributes to HZ-006 (braking while not engaged, HE-04.4) (HZ-006, S 10)
- **Next higher:** Item actuation permitted
- **Local:** controls_allowed true without a cruise rising edge

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-007.C1` Defect in pcm_cruise_check or PCM_CRUISE decoding (toyota.h rx hook, 0x1D2 bit 5) | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: Controls granted only on a PCM cruise rising edge with every RX check valid (TSR-306)

<sub>Note: BL-002: a cruise rising edge grants controls only if every RX check is valid and not lagging at that moment (rx_checks_allow_engagement, TSR-306, opendbc#3).</sub>

#### SWF-008 · Controls not withdrawn on brake press

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-004` Allow controls on rising edge of PCM cruise; withdraw on cruise off, brake press, invalid or lagging safety messages

Effects:

- **End:** Automation not released on brake (HZ-008, S 10)
- **Next higher:** Item keeps actuating
- **Local:** controls_allowed stays true while the driver brakes

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-008.C1` Host-supplied safety parameter selects the wrong brake message (ALT_BRAKE flag), so brake presses are never seen | • Reference-build lock: 0xdc accepts TOYOTA only with parameter 73 (no flags) and, once TOYOTA is active, only NOOUTPUT or SILENT; 0xdf refused (reference_lock.h, panda#4, TSR-512/513). Effective only in a LIONDRIVER_REFERENCE build, see SWF-013.C2 <sub>panda/board/reference_lock.h</sub> | • Host unit tests compiled against the real firmware headers, run by panda CI (test.sh): reference_lock and hw_watchdog, 14 tests, pass at BL-002 locally. Not on target hardware <sub>panda/tests/reference_lock/test_reference_lock.py</sub> | 3 | 4 | 🟢 L | SWF-ACT-009 |
| `SWF-008.C2` Defect in generic_rx_checks brake edge logic (safety.h:354-357) | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: Brake rising edge withdraws controls; PCM cruise cancel as diverse path

#### SWF-009 · Controls not withdrawn when PCM cruise disengages

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-004` Allow controls on rising edge of PCM cruise; withdraw on cruise off, brake press, invalid or lagging safety messages

Effects:

- **End:** Automation not released on cancel (HZ-008, S 10)
- **Next higher:** Item keeps actuating after the driver cancels
- **Local:** controls_allowed stays true after cruise off

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-009.C1` Defect in pcm_cruise_check (safety.h:518-527) | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: Cruise off withdraws controls in pcm_cruise_check

### `SWF-SE-006` Steering torque checks

#### SWF-001 · Steering request above the torque or torque-rate limit for the vehicle is passed

🔴 **H** · **S 10** · guideword *value_high* · function `SWF-FN-002` Block steering requests outside torque magnitude, rate and measured-torque-error limits, and any torque while controls are not allowed

Effects:

- **End:** Uncontrollable steering intervention (HZ-002, S 10)
- **Next higher:** Lateral deviation faster than the driver can correct
- **Local:** Out-of-envelope torque request reaches the EPS

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-001.C1` Panda torque limits (max 1500, rate up 15 / down 25, error 350) are the same constants as the SoC controller's and are not derived from a vehicle envelope | • Limits copied from upstream vehicle tuning; no independent envelope (FSC FOI-001, DFA DFI-14) <sub>opendbc_repo/opendbc/safety/modes/toyota.h:172-177; opendbc_repo/opendbc/car/toyota/values.py:20-50</sub> | • No test targets this cause | 6 | 9 | 🔴 **H** | SWF-ACT-003 |
| `SWF-001.C2` Implementation defect in steer_torque_cmd_checks or dist_to_meas_check | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |
| `SWF-001.C3` Wrong EPS torque factor in the host-supplied safety parameter scales measured torque, widening the measured-torque-error check | • Reference-build lock: 0xdc accepts TOYOTA only with parameter 73 (no flags) and, once TOYOTA is active, only NOOUTPUT or SILENT; 0xdf refused (reference_lock.h, panda#4, TSR-512/513). Effective only in a LIONDRIVER_REFERENCE build, see SWF-013.C2 <sub>panda/board/reference_lock.h</sub> | • Host unit tests compiled against the real firmware headers, run by panda CI (test.sh): reference_lock and hw_watchdog, 14 tests, pass at BL-002 locally. Not on target hardware <sub>panda/tests/reference_lock/test_reference_lock.py</sub> | 3 | 4 | 🟢 L | SWF-ACT-009 |

Safety mechanisms: Panda torque magnitude, rate and measured-torque-error checks block the frame · EPS limits LKA torque itself (external measure, AOU-01, unverified)

#### SWF-002 · Steering torque passed while controls are not allowed

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-002` Block steering requests outside torque magnitude, rate and measured-torque-error limits, and any torque while controls are not allowed

Effects:

- **End:** Unintended steering while not engaged (HZ-001, S 10)
- **Next higher:** Unexpected steering input
- **Local:** Torque request reaches the EPS outside an engagement

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-002.C1` Defect in the not-allowed torque check (lateral.h:111-114) or in controls_allowed bookkeeping | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: Panda blocks non-zero torque and the steer-request bit while controls are not allowed

<sub>Note: Depends on controls_allowed being correct; see SWF-007..SWF-009.</sub>

### `SWF-SE-007` Longitudinal checks

#### SWF-003 · Acceleration request outside the intended envelope is passed

🔴 **H** · **S 10** · guideword *value_high* · function `SWF-FN-003` Block acceleration outside the range, and any non-inactive acceleration while controls are not allowed or the accelerator is pressed

Effects:

- **End:** Unintended acceleration or excessive deceleration (HZ-005, S 10)
- **End:** Contributes to HZ-006 (HZ-006, S 10)
- **Next higher:** Vehicle accelerates or brakes harder than designed
- **Local:** Acceleration request beyond the item design reaches the powertrain

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-003.C1` Panda upper bound +2.0 m/s² equals the SoC limit (RAISED_ACCEL_LIMIT is set for every TSS2 car, values.py:39-43) and is not derived from a validated Corolla envelope; no margin between controller and envelope | • Panda limit taken from the platform maximum, not a vehicle envelope (assurance GAP-04, WP-A-03 DFI-08) <sub>opendbc_repo/opendbc/safety/modes/toyota.h:207-210</sub> | • No test targets this cause | 6 | 9 | 🔴 **H** | SWF-ACT-003 |
| `SWF-003.C2` Implementation defect in longitudinal_accel_checks | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |
| `SWF-003.C3` Panda lower bound -3.5 m/s² (toyota.h:335) equals the SoC ACCEL_MIN and is not derived from the controllability of following traffic (HE-04.1) or a validated Corolla deceleration envelope; no margin between controller and envelope | • Panda limit taken from the platform minimum, not a vehicle envelope (assurance GAP-04, TSR-202 without rationale, WP-A-03 DFI-14 / DM-10) <sub>opendbc_repo/opendbc/safety/modes/toyota.h:333-336</sub> | • No test targets this cause | 6 | 9 | 🔴 **H** | SWF-ACT-003 |

Safety mechanisms: Panda acceleration range check blocks the frame · PCM limits requested acceleration (external measure, AOU-05, unverified)

#### SWF-004 · Step change of deceleration request to the minimum is passed

🔴 **H** · **S 10** · guideword *early* · function `SWF-FN-003` Block acceleration outside the range, and any non-inactive acceleration while controls are not allowed or the accelerator is pressed

Effects:

- **End:** Unexpected hard braking; rear-end collision by following traffic (HZ-006, S 10)
- **Next higher:** Hard braking without onset
- **Local:** Request jumps from 0 to -3.5 m/s² in one frame

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-004.C1` longitudinal_accel_checks checks the range only; no rate or jerk limit on acceleration requests | • Range check only (longitudinal.h:8-12); FSC FSR-021 asks for a jerk envelope <sub>opendbc_repo/opendbc/safety/longitudinal.h</sub> | • No test targets this cause | 8 | 9 | 🔴 **H** | SWF-ACT-005 |

Safety mechanisms: None in the panda (no rate or jerk check); PCM rate limiting assumed, not characterised (OI-002)

#### SWF-017 · Item deceleration passed while the driver presses the accelerator

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-003` Block acceleration outside the range, and any non-inactive acceleration while controls are not allowed or the accelerator is pressed

Effects:

- **End:** Braking against driver input (HZ-006, S 10)
- **Next higher:** Item brakes against the driver
- **Local:** Braking request passes during accelerator override

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-017.C1` Defect in get_longitudinal_allowed (controls_allowed && !gas_pressed_prev) or GAS_RELEASED decoding (0x1D2 bit 4) | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: Non-inactive acceleration refused while the accelerator is pressed (get_longitudinal_allowed)

<sub>Note: FSC FSR-024 is verified in code at BL-001: only the inactive acceleration passes while the accelerator is pressed.</sub>

#### SWF-053 · Active deceleration request ends in one step when authority is revoked

🔴 **H** · **S 10** · guideword *early* · function `SWF-FN-003` Block acceleration outside the range, and any non-inactive acceleration while controls are not allowed or the accelerator is pressed

Effects:

- **End:** Uncontrolled change of deceleration at disengagement (FSR-04.03) (HZ-006, S 10)
- **Next higher:** Step in the requested acceleration at the transition to the safe state; the PCM's own ramp is not characterised (AOU-05R)
- **Local:** Once controls_allowed clears, only the inactive acceleration passes (longitudinal.h:8-12, toyota.h:349), so the request goes from the active deceleration to the inactive value in one frame

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-053.C1` By design, the envelope has no ramp-out state after revocation, and the host stops its own request in the same cycle (LongControl off); FSR-04.03 relies on the PCM (TSR-208) | • None in the item; PCM coasting behaviour assumed (TSR-208, AOU-05R, unverified) <sub>opendbc_repo/opendbc/safety/longitudinal.h</sub> | • No test targets this cause | 8 | 9 | 🔴 **H** | SWF-ACT-053 |

Safety mechanisms: None in the item; PCM ramp to coasting assumed (TSR-208)

<sub>Note: WP-A-04 BE-4.14 (SG-04 G4.7).</sub>

### `SWF-SE-009` Relay malfunction detection

#### SWF-012 · Relay malfunction not detected

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-008` Detect a relay malfunction and block all item transmission

Effects:

- **End:** Erratic or excessive steering (HZ-002, S 10)
- **End:** Contributes to HZ-006 (stock ACC and item 0x343 combine on the bus) (HZ-006, S 10)
- **Next higher:** Conflicting steering commands
- **Local:** Stock camera stays on the bus while the item transmits

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-012.C1` Defect in stock_ecu_check, or a replaced message without check_relay; detection starts 1 s after a mode change (safety.h:372-380) | • MISRA C:2012 checks on the safety code <sub>opendbc_repo/opendbc/safety/tests/misra</sub><br>• 100% line coverage enforced by the safety test runner <sub>opendbc_repo/opendbc/safety/tests/test.sh</sub><br>• Upstream code review; no documented safety requirements for the safety model (tests derived from implementation) | • opendbc safety suite with 100% line coverage and mutation tests, run by fork CI on every change (.github/workflows/safety.yaml, CR-CI-05). At BL-002 the Toyota tests pass locally (287, 34 skipped); mutation was last run locally at BL-001 (2705/2705 killed). Tests are derived from the implementation, not from requirements <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SWF-ACT-002 |

Safety mechanisms: Relay malfunction detection blocks all TX after a stock message appears on the car side

### `SWF-SE-011` Panda main loop: safety mode and heartbeat

#### SWF-014 · Controls withdrawn later than the FTTI after host loss

🔴 **H** · **S 10** · guideword *late* · function `SWF-FN-010` Withdraw controls when the host heartbeat is lost or reports not engaged

Effects:

- **End:** Continued actuation without a supervising SoC (HZ-002, S 10)
- **End:** Contributes to HZ-005 (HZ-005, S 10)
- **Next higher:** Last SoC messages can keep passing if still sent
- **Local:** controls_allowed persists several seconds without a valid heartbeat

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-014.C1` Heartbeat from pandad missing (pandad, SPI or SoC down): authority revoked after 0.3 s, checked at 100 Hz (TSR-407, panda#7) | • heartbeat_monitor: no 0xf3 for > 0.3 s in a car mode clears controls_allowed (panda c2e5d93); SILENT after 5 s unchanged (TSR-510) <sub>panda/board/drivers/heartbeat_monitor.h</sub> | • Host unit test of the heartbeat monitor in panda CI (test.sh); HITL RX/heartbeat test not run (no bench, D-04) <sub>panda/tests/heartbeat_monitor/test_heartbeat_monitor.py</sub> | 3 | 4 | 🟢 L | SWF-ACT-007 |
| `SWF-014.C2` controlsd or selfdrived stalls while pandad keeps sending heartbeats with engaged=1: the heartbeat shows pandad liveness only; authority is withdrawn only by the engaged-mismatch counter after 3 ticks at 1 Hz (about 3 s), and only if engaged drops | • Heartbeat carries no freshness of the control loop (TSR-307a asks for 0.3 s on mismatch; TSR-408/409 for command freshness) <sub>panda/board/main.c</sub> | • Panda HITL health and safety tests (hardware needed; not run here) <sub>panda/tests/hitl/test_2_health.py</sub> | 8 | 8 | 🔴 **H** | SWF-ACT-007 |

Safety mechanisms: Heartbeat loss: authority revoked after 0.3 s (TSR-407); SILENT after 5 s; engaged mismatch after about 3 s; siren for 3 s if engaged (since panda c33343b, 2026-10-13, at the 0.3 s revocation, not credited in the ratings)

### `SWF-SE-012` Panda host command handler

#### SWF-013 · Wrong or permissive safety mode accepted from the host

🔴 **H** · **S 10** · guideword *wrong_mode* · function `SWF-FN-011` Accept host configuration commands only when they cannot widen what is transmitted

Effects:

- **End:** Any actuation hazard (HZ-002, S 10)
- **End:** Contributes to HZ-005 (HZ-005, S 10)
- **End:** Contributes to HZ-006 (HZ-006, S 10)
- **Next higher:** Item messages unchecked or checked against wrong limits
- **Local:** Panda enforces a different model or none (ALLOUTPUT)

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-013.C1` Defect in the reference-build allow-list for 0xdc/0xdf and the car-mode request gate | • Reference-build lock: 0xdc accepts TOYOTA only with parameter 73 (no flags) and, once TOYOTA is active, only NOOUTPUT or SILENT; 0xdf refused (reference_lock.h, panda#4, TSR-512/513). Effective only in a LIONDRIVER_REFERENCE build, see SWF-013.C2 <sub>panda/board/reference_lock.h</sub> | • Host unit tests compiled against the real firmware headers, run by panda CI (test.sh): reference_lock and hw_watchdog, 14 tests, pass at BL-002 locally. Not on target hardware <sub>panda/tests/reference_lock/test_reference_lock.py</sub> | 3 | 4 | 🟢 L | SWF-ACT-004 |
| `SWF-013.C2` Firmware built without LIONDRIVER_REFERENCE: no build path sets it (openpilot panda build, release procedure), so set_safety_mode accepts any mode and parameter and debug builds include SAFETY_ALLOUTPUT | • Lock is opt-in at build time (panda/SConscript:21-26); release procedure not yet defined (IA mode lock OI-2) <sub>panda/SConscript</sub> | • No test targets this cause | 8 | 9 | 🔴 **H** | SWF-ACT-009 |

Safety mechanisms: Reference-build mode and parameter lock (panda#4); SoC cross-checks the panda mode after 10 s (QM)

#### SWF-015 · Diagnostic (ELM327) mode accepted while driving

🔴 **H** · **S 10** · guideword *wrong_mode* · function `SWF-FN-011` Accept host configuration commands only when they cannot widen what is transmitted

Effects:

- **End:** Loss of assist or stock function while driving (HZ-004, S 10)
- **End:** Contributes to HZ-011 (HZ-011, S 10)
- **Next higher:** ECU reset or diagnostic session on EPS/ADAS
- **Local:** Diagnostic frames allowed to vehicle ECUs

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-015.C1` ELM327 TX hook allows any ISO 15765 diagnostic frame with no service, ignition or motion condition. In a reference build ELM327 can no longer be selected while TOYOTA is active, but before engagement (fingerprinting, radar disable) the content is unrestricted | • No vehicle-state or service condition (elm327.h:6-35); reference lock limits the phase only <sub>opendbc_repo/opendbc/safety/modes/elm327.h</sub> | • No test targets this cause | 5 | 9 | 🔴 **H** | SWF-ACT-010 |

Safety mechanisms: None for frame content; the reference lock only blocks ELM327 while TOYOTA is active

### `SWF-SE-013` Panda CAN send path

#### SWF-016 · Host transmission bypasses the safety check

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-012` Route every host transmission through the safety check

Effects:

- **End:** Any actuation hazard (HZ-002, S 10)
- **End:** Contributes to HZ-005 (HZ-005, S 10)
- **Next higher:** Unchecked message on the bus
- **Local:** Host message sent without safety_tx_hook

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-016.C1` A host TX path calls can_send with skip_tx_hook=true | • Both host TX entries pass skip_tx_hook=false (can_comms.h:97,118); only forwarding and the body use skip=true <sub>panda/board/can_comms.h</sub><br>• MISRA C checks on panda firmware <sub>panda/tests/misra</sub><br>• Upstream code review; no coverage gate on panda board code | • Panda HITL safety tests (hardware needed; not run here) <sub>panda/tests/hitl/test_6_safety.py</sub> | 3 | 8 | 🔴 **H** | SWF-ACT-008 |

Safety mechanisms: None at run time; correctness of the two host TX entries by inspection

### `SWF-SE-014` Panda hardware watchdog and 100 Hz safety task

#### SWF-018 · Safety checks stop running while the relay is driven

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-013` Reset the MCU, which releases the relay, within 0.1 s when the safety task or main loop stops; never reset while both run normally

Effects:

- **End:** Continued actuation without supervision; stock AEB unavailable (HZ-002, S 10)
- **End:** Contributes to HZ-011 (HZ-011, S 10)
- **Next higher:** Stale authority kept; stock camera path stays cut
- **Local:** RX timeout, heartbeat and TX checks no longer evaluated; relay held energised

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-018.C1` Main loop or safety task hangs or is starved (defect, interrupt storm, peripheral lock-up) after the relay has been driven | • IWDG from LSI, 90 ms nominal timeout, window mode (5 ms closed), fed only from the 100 Hz safety task after main-loop progress; started on every path that drives the relay (TSR-501/502, HWSR-501b, panda#1, #3). A reset floats the relay GPIO <sub>panda/board/drivers/hw_watchdog.h</sub> | • Host unit tests compiled against the real firmware headers, run by panda CI (test.sh): reference_lock and hw_watchdog, 14 tests, pass at BL-002 locally. Not on target hardware <sub>panda/tests/reference_lock/test_reference_lock.py</sub><br>• HIL test of the watchdog with injected hangs (FAULT_INJECTION debug build); not run, no HIL bench yet (D-04) <sub>panda/tests/hitl/test_10_hw_watchdog.py</sub> | 4 | 7 | 🔴 **H** | SWF-ACT-011 |

Safety mechanisms: IWDG window watchdog resets the MCU within about 90 ms; reset releases the relay

<sub>Note: New in BL-002. Before BL-002 a hang left the relay driven with no reset (assurance GAP-43).</sub>

#### SWF-019 · Spurious MCU reset while engaged

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-013` Reset the MCU, which releases the relay, within 0.1 s when the safety task or main loop stops; never reset while both run normally

Effects:

- **End:** Loss of lateral and longitudinal control without the item's own handback warning (HZ-004, S 10)
- **End:** Contributes to HZ-012 (HZ-012, S 10)
- **Next higher:** Item steering and ACC end abruptly; stock camera path returns
- **Local:** Panda resets and restarts in SILENT; relay drops

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-019.C1` LSI frequency outside the range assumed for the 5 ms closed window and the 90 ms timeout, or safety-task jitter, makes a normal feed early or late | • Timing chosen with margin at nominal f_LSI = 32 kHz; the LSI range is still to be confirmed from the STM32H725 datasheet (IA watchdog open item) <sub>panda/board/drivers/hw_watchdog.h</sub> | • Host unit tests compiled against the real firmware headers, run by panda CI (test.sh): reference_lock and hw_watchdog, 14 tests, pass at BL-002 locally. Not on target hardware <sub>panda/tests/reference_lock/test_reference_lock.py</sub><br>• HIL test of the watchdog with injected hangs (FAULT_INJECTION debug build); not run, no HIL bench yet (D-04) <sub>panda/tests/hitl/test_10_hw_watchdog.py</sub> | 5 | 8 | 🔴 **H** | SWF-ACT-011 |

Safety mechanisms: None in the panda; the SoC raises an alert when it loses the panda (QM)

<sub>Note: New failure mode introduced by the watchdog (WP-W-04 OI-3). The SoC's own disengagement alert depends on it noticing the panda reset.</sub>

### `SWF-SE-021` Main loop and heartbeat

#### SWF-020 · Heartbeat reports engaged while no fresh command reaches the panda

🔴 **H** · **S 10** · guideword *value_stale* · function `SWF-FN-020` Send the heartbeat at 10 Hz. It reports engaged only while the SoC is engaged and actively commanding, so that the panda can withdraw authority when the host stops (supports FSR-005 and FSR-007, which are allocated to EL-07)

Effects:

- **End:** Actuation authority held without a supervising control loop; stale in-limit command replayed (HZ-002, S 10)
- **End:** Steering or ACC commands stop while the device and panda still show engaged (HZ-004, S 10)
- **Next higher:** Panda keeps controls_allowed. The engaged-mismatch counter never runs. Queued frames up to 1 s old can still pass (SWF-023), or none arrive
- **Local:** 0xf3 carries engaged=1 while card/controlsd have stalled or sendcan is not forwarded

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-020.C1` engaged is derived only from selfdriveState alive (<0.1 s), valid and enabled (pandad.cc:424). Neither carControl/sendcan freshness nor the forwarding thread's progress goes into the heartbeat, which is sent from the main thread (pandad.cc:313), so the heartbeat shows pandad and selfdrived liveness only (host side of SWF-014.C2; TSR-409 / TSR-602 not implemented) | • Upstream design, reviewed; no requirement binds the heartbeat to command freshness at BL-004 (WP-A-04 BE-1.22, GAP-10) <sub>openpilot/selfdrive/pandad/pandad.cc:421-430</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | SWF-ACT-020, SWF-ACT-029 |

Safety mechanisms: Panda torque, rate and real-time delta limits (max_rt_delta 450 per 250 ms) and the acceleration range bound the magnitude of a replayed command. They do not detect an in-limit stale value (WP-A-04 SPF-14) · selfdrived commIssue/processNotRunning (SOFT_DISABLE, QM) drops enabled. pandad then sends engaged=0, and the panda withdraws authority after 3 mismatches at 1 Hz, about 3 s (SWF-014.C2)

<sub>Note: card stops sending once carControl is older than 0.1 s (card.py:234), so after a controlsd stall frames usually stop rather than freeze. The stale-replay path needs a stall of pandad or card shorter than 1 s (SWF-023). Within that window the panda cannot tell a dead control loop from a live one.</sub>

#### SWF-021 · Heartbeat gap longer than the 0.3 s panda budget while engaged

🔴 **H** · **S 10** · guideword *late* · function `SWF-FN-020` Send the heartbeat at 10 Hz. It reports engaged only while the SoC is engaged and actively commanding, so that the panda can withdraw authority when the host stops (supports FSR-005 and FSR-007, which are allocated to EL-07)

Effects:

- **End:** Loss of lateral and longitudinal control. The SoC alert follows only after the controlsAllowed mismatch counter reaches 200 frames (about 2 s) (HZ-004, S 10)
- **End:** Contributes to HZ-007 (ACC requests blocked while shown engaged) (HZ-007, S 10)
- **Next higher:** Panda revokes controls_allowed (TSR-407) and blocks item frames, while selfdrived still shows engaged and controlsd keeps commanding
- **Local:** Three or more 10 Hz heartbeats missing

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-021.C1` The heartbeat is skipped whenever the health read fails: process_panda_state returns before send_heartbeat (pandad.cc:299-303, 313). A control transfer that cannot complete retries without bound (SWF-027.C1), so the main loop stops sending heartbeats while it waits | • Upstream code, reviewed, -Werror. The 0.3 s panda budget is new in panda#7 (changed operating condition). pandad heartbeat jitter under SPI errors has not been characterised against it <sub>panda/board/drivers/heartbeat_monitor.h</sub> | • Hardware test with SPI error injection (SPI_ERR_PROB=0.001). It checks that pandaStates intervals stay below 8 periods (0.8 s), which does not cover the 0.3 s budget. It is not designed for this cause and was not run for BL-004 <sub>openpilot/selfdrive/pandad/tests/test_pandad_spi.py</sub> | 7 | 9 | 🔴 **H** | SWF-ACT-021, SWF-ACT-029 |
| `SWF-021.C2` The heartbeat shares the 100 Hz loop with CAN RX, three get_can_state reads, fan/IR writes and serial_read, which loops until the panda log is empty (pandad.cc:414-448, panda.cc:47-60). A loop overrun delays the heartbeat | • Real-time priority 54 on isolated core 3 (main.cc:107-113); RateKeeper; upstream review <sub>openpilot/selfdrive/pandad/main.cc</sub> | • As SWF-021.C1 (timing report in the hardware SPI test, not designed for the 0.3 s budget, not run) <sub>openpilot/selfdrive/pandad/tests/test_pandad_spi.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-021, SWF-ACT-029 |

Safety mechanisms: selfdrived controlsMismatch (IMMEDIATE_DISABLE, QM) once mismatch_counter >= 200. The counter increments at 100 Hz while any pandaState shows !controlsAllowed, so the delay is about 2 s, not "two samples" as the code comment says · Panda siren for 3 s only after the 1 Hz heartbeat counter times out (SILENT), not at the 0.3 s revocation. 2026-10-13 (panda c33343b, all builds, not credited in the ratings): the siren also sounds at the 0.3 s revocation when authority was granted, about 0.56 s after the last heartbeat (WP-S-04 T-07a)

<sub>Note: Revocation is the safe direction for authority. The hazard is the silent gap: the panda blocks frames while the SoC shows engaged, for about 2 s. The mismatch timing belongs to EL-04 (selfdrived), and SWF-ACT-021 asks for it to be shortened as well.</sub>

### `SWF-SE-022` Safety mode setter

#### SWF-022 · Wrong safety model, parameter or alternative experience written to the panda

🔴 **H** · **S 10** · guideword *wrong_mode* · function `SWF-FN-021` Put the panda in the safety model, parameter and alternative experience for the identified vehicle, only when onroad, and in NO_OUTPUT when offroad, with ignition off or on exit

Effects:

- **End:** Any actuation hazard within the wrongly configured envelope (HZ-002, S 10)
- **End:** Contributes to HZ-008 (wrong brake source via the ALT_BRAKE flag, SWF-008.C1) (HZ-008, S 10)
- **End:** Contributes to HZ-006 (deceleration checked against a wrong envelope) (HZ-006, S 10)
- **Next higher:** Item frames checked against wrong limits, wrong brake message or no car model
- **Local:** Panda enforces a model or parameter other than the reference (TOYOTA, 73, alternative experience 0), or stays in ELM327

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-022.C1` setSafetyMode writes safety_configs[0] model and param and alternative_experience exactly as found in CarParams (panda_safety.cc:56-70). There is no allow-list for the reference configuration. A fingerprinting or CarParams error, such as a wrong EPS factor or flags, reaches the panda, which accepts any mode at BL-004 | • Upstream code, reviewed. FirmwareQueryDone and ControlsReady are cleared on every onroad transition (common/params_keys.h:28, 44), so a previous drive's CarParams is not reused. No documented requirement for the host check <sub>openpilot/selfdrive/pandad/panda_safety.cc</sub> | • No test targets this cause; test_pandad.py (hardware) checks only that pandad starts | 7 | 10 | 🔴 **H** | SWF-ACT-022, SWF-ACT-028 |
| `SWF-022.C2` set_safety_model, set_alternative_experience and the OBD multiplexing switch ignore the control_write result and never read the mode back (panda.cc:39-45, panda_safety.cc:33-36, 68-69). safety_configured_ is set true unconditionally (panda_safety.cc:12-13), so a write the panda drops or refuses is not retried during the drive. ObdMultiplexingChanged is acknowledged before the panda has confirmed the mode | • Upstream code, reviewed. A failed SPI write retries without bound (TIMEOUT 0), so a lost write shows up as a hang (SWF-027), not a silent loss. A refusal by the panda (reference lock, or 0xdf in a car mode, main_comms.h:262-267) is silent <sub>openpilot/selfdrive/pandad/spi.cc:205-239</sub> | • No test targets this cause | 4 | 10 | 🔴 **H** | SWF-ACT-022 |

Safety mechanisms: selfdrived controlsMismatch after 10 s compares pandaStates mode, param and alternative experience against CarParams (QM). Both come from the same CarParams, so it detects a lost or altered write but not a wrong CarParams · Panda reference-build lock (TOYOTA with parameter 73 only). Not active at BL-004 (SWF-013.C2)

<sub>Note: The setting order is correct: ELM327 first (a non-car mode, so 0xdf is accepted), then alternative experience, then the car mode. In the safe direction (mode never set), the item stays unavailable with a controlsMismatch alert. In the unsafe direction (wrong car mode or param accepted), the panda is the only barrier, and it is not locked at BL-004.</sub>

### `SWF-SE-023` sendcan forwarding thread

#### SWF-023 · Stale or burst-replayed sendcan frames forwarded to the panda

🔴 **H** · **S 10** · guideword *value_stale* · function `SWF-FN-022` Forward each sendcan batch to the panda once, in order, only while it is fresh, and make any failure to forward visible to the SoC

Effects:

- **End:** Stale in-limit steering command applied after the situation changed (HZ-003, S 10)
- **End:** Contributes to HZ-002 (torque change compressed in time, bounded by the panda real-time delta) (HZ-002, S 10)
- **End:** Contributes to HZ-005 (stale positive acceleration request) (HZ-005, S 10)
- **End:** Contributes to HZ-006 (stale deceleration request) (HZ-006, S 10)
- **Next higher:** Panda receives commands that no longer match the vehicle state, compressed in time
- **Local:** Frames up to 1 s old forwarded, or a backlog sent back-to-back after a pandad or SPI stall

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-023.C1` The age gate is 1 s (pandad.cc:78-79). That exceeds the 0.9 s preliminary SG-001 FTTI and is 100 control periods long. The sendcan subscriber is a non-conflated FIFO (pandad.cc:64; services.py sendcan MEDIUM queue), so a backlog of up to 1 s is forwarded in order but back-to-back. No newest-only policy applies per address (WP-W-04 SWF-47, SWSR-411) | • Upstream design, reviewed; no derived freshness requirement at BL-004 <sub>openpilot/selfdrive/pandad/pandad.cc:59-87</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | SWF-ACT-023, SWF-ACT-024 |

Safety mechanisms: Panda per-frame torque rate (up 15 / down 25) and real-time delta (450 per 250 ms) checks limit how fast a burst can change torque. The acceleration range check applies. The per-ID TX rate supervision (TSR-518) is compiled only in the reference build and is not credited · Heartbeat revocation after 0.3 s bounds replay after a pandad stall of more than 0.3 s, because the main loop stalls with the same SPI lock

<sub>Note: pandad also ignores the sendcan valid flag (card sets valid=CS.canValid, card.py:238), so frames built on invalid CAN input are forwarded. The window is short because selfdrived disables on canError, but the flag is not used as a barrier.</sub>

#### SWF-024 · sendcan frames silently not forwarded while engaged

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-022` Forward each sendcan batch to the panda once, in order, only while it is fresh, and make any failure to forward visible to the SoC

Effects:

- **End:** Loss of lateral control without a timely item alert (System FMEA SFM-005.C2) (HZ-004, S 10)
- **End:** Loss of ACC deceleration without a timely item alert (System FMEA SFM-011.C2) (HZ-007, S 10)
- **Next higher:** No steering or ACC messages on the bus while selfdrived, controlsd and the panda all show engaged
- **Local:** Frames dropped in pandad with only a log line (pandad.cc:83-85) or a failed bulk write

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-024.C1` Clock-domain mismatch. card stamps sendcan logMonoTime with Python time.monotonic(), which is CLOCK_MONOTONIC (pandad_api_impl.py:42, card.py:236-238). pandad compares it with nanos_since_boot(), which is CLOCK_BOOTTIME (common/timing.h:10-14). The two differ by the time spent suspended since boot. If that exceeds 1 s, every frame is dropped and only a LOGE is written. The check can only become stricter, never more permissive | • None specific. Whether the comma 3X ever suspends after boot while openpilot runs (offset > 0) is not established | • No test targets this cause; no test exercises the age gate | 5 | 10 | 🔴 **H** | SWF-ACT-023, SWF-ACT-026, SWF-ACT-024 |
| `SWF-024.C2` A bulk write that fails after its retries (5 ms timeout, clamped to 20 ms per ACK wait) drops the rest of the batch. can_send ignores the result (spi.cc:149-177, panda.cc:210-214) | • Upstream code, reviewed; the failure latches comms_healthy, which leads to canError (in-field mechanism above) <sub>openpilot/selfdrive/pandad/spi.cc:164-167</sub> | • Hardware SPI corruption test (SPI_ERR_PROB). It checks received frames, not dropped TX, and was not run for BL-004 <sub>openpilot/selfdrive/pandad/tests/test_pandad_spi.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-026, SWF-ACT-029 |

Safety mechanisms: For SPI write failures only: comms_healthy latches false (spi.cc:166). can is then published invalid (pandad.cc:93-97), card reports canValid false, and selfdrived raises canError (IMMEDIATE_DISABLE, QM) · EPS/PCM fault signals on missing messages (steerTempUnavailable, accFaulted); stock behaviour on missing LKA/ACC frames not characterised (XM-02)

<sub>Note: FAKESEND (pandad.cc:400) also drops every frame. It is a test hook that no launch path sets (SWF-028.C2).</sub>

### `SWF-SE-024` CAN RX and panda state publishing

#### SWF-025 · pandaStates.faults reports a relay malfunction that did not occur

🟠 M · **S 8** · guideword *corrupted* · function `SWF-FN-023` Publish received CAN and the panda state (mode, parameter, controlsAllowed, RX-check validity, faults) correctly and on time, so the SoC can detect a mismatch or fault and disable

Effects:

- **End:** Immediate disengagement while engaged, with a take-control alert; item unavailable for the drive
- **Next higher:** selfdrived relayMalfunction (IMMEDIATE_DISABLE, permanent NO_ENTRY)
- **Local:** faults list sized from all set bits, with an unfilled entry left at enum value 0 (relayMalfunction)

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-025.C1` initFaults(fault_bits.count()) counts every set bit of faults_pkt, but the fill loop maps only bits 0..26 (relayMalfunction..heartbeatLoopWatchdog, pandad.cc:257-268). The panda defines bit 27 FAULT_INTERRUPT_RATE_SOUND_DMA (panda/board/sys/sys.h:47, used in stm32h7/sound.h:162-163), and cereal FaultType has no entry for it (log.capnp:596-625). When bit 27 is set, the last list entry stays 0 = relayMalfunction | • Fixed in #48 (3534bc2): fill_panda_faults sizes the list from the bits that have a FaultType (mask up to PANDA_FAULT_TYPE_MAX) and returns the rest, which are logged, so no entry is left at the default; interruptRateSoundDma @27 added. New C++ with a unit test, -Werror build, merged by the owner; no independent review, no C++ static analysis, no documented pandad requirements <sub>openpilot/selfdrive/pandad/pandad.cc</sub> | • tests/test_pandad_faults (bit 27 alone and with unknown bits 28/31, only unknown bits, every bit but bit 0, a real relay fault; PANDA_FAULT_TYPE_MAX equals the last FaultType in the schema). Built with extras and run by test_native.py in CI unit_tests on every PR. Proven: fails with the old sizing (mutation in the impact record). Pass-fail <sub>openpilot/selfdrive/pandad/tests/test_pandad_faults.cc</sub> | 5 | 4 | 🟠 M | SWF-ACT-025, SWF-ACT-024 |

Safety mechanisms: None; the alert itself is correct in form, only its cause is false

<sub>Note: Found by code inspection. How often the sound DMA interrupt-rate fault fires on the 3X is unknown; the defect is certain. Related observation: pandad publishes the LionDriver fields epsFault, txRateExceeded and requestsRejected (pandad.cc:136-139), but no SoC process reads them (grep over openpilot/*.py), so an EPS-fault refusal by the panda reaches the driver only through the stock EPS fault path. That is for EL-04 to decide.</sub>

#### SWF-029 · Item unavailable for the rest of the drive after a transient link error or a panda reset

🔴 **H** · **S 8** · guideword *omission* · function `SWF-FN-023` Publish received CAN and the panda state (mode, parameter, controlsAllowed, RX-check validity, faults) correctly and on time, so the SoC can detect a mismatch or fault and disable

Effects:

- **End:** Immediate disengagement with a take-control alert, then no re-engagement until the next drive
- **Next higher:** canError or controlsMismatch, with permanent NO_ENTRY for the drive
- **Local:** can published empty and invalid until ignition off, or the panda held in NO_OUTPUT until offroad

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-029.C1` One failed bulk transfer latches comms_healthy false (spi.cc:166), and nothing resets it. can_receive then discards every read (panda.cc:221-223), and pandad reconnects only when ignition is off (pandad.cc:305-311) | • Upstream design, intended fail-safe; reviewed <sub>openpilot/selfdrive/pandad/pandad.cc:305-311</sub> | • No test targets this cause | 6 | 10 | 🔴 **H** | SWF-ACT-029 |
| `SWF-029.C2` After a panda reset while onroad (watchdog, SWF-019), the panda boots in SILENT (panda main.c:339). pandad switches it to NO_OUTPUT (pandad.cc:229-232), and because safety_configured_ stays true (panda_safety.cc:6-14) the car mode is never re-applied during that drive | • Upstream design, reviewed; safe direction (no actuation) <sub>openpilot/selfdrive/pandad/panda_safety.cc</sub> | • No test targets this cause | 6 | 10 | 🔴 **H** | SWF-ACT-029 |

Safety mechanisms: canError and controlsMismatch alerts (IMMEDIATE_DISABLE, QM) make the loss visible

### `SWF-SE-025` SPI transport

#### SWF-026 · Corrupted command or vehicle data accepted across the SPI link

🔴 **H** · **S 10** · guideword *corrupted* · function `SWF-FN-024` Transfer commands and data between SoC and panda without undetected corruption. Detect link failure in bounded time and report it

Effects:

- **End:** Wrong in-limit steering or acceleration command reaches the vehicle if its Toyota checksum also passes (HZ-003, S 10)
- **Next higher:** The panda checks a corrupted command, or the SoC uses corrupted vehicle state or panda state
- **Local:** A frame or health packet with bit errors passes both link checks

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-026.C1` Both integrity checks are 8-bit XOR over the same bytes: the SPI frame checksum (spi.cc:189-202) and the CAN header checksum (panda.cc:284-290). Any even number of bit errors in the same bit position passes both, so they are not independent | • Upstream protocol with two XOR checks; the SPI layer re-syncs on error (spi.cc:394-404); spi_error_count is reported in pandaStates <sub>openpilot/selfdrive/pandad/spi.cc</sub> | • Hardware test injects random TX/RX corruption (SPI_ERR_PROB) and checks that received CAN frames were sent. It does not measure the residual undetected-error rate. Not run for BL-004 <sub>openpilot/selfdrive/pandad/tests/test_pandad_spi.py</sub> | 4 | 9 | 🔴 **H** | SWF-ACT-027 |

Safety mechanisms: Panda safety checks (limits, controls_allowed, TX whitelist) apply to the frame as received · Toyota message checksum, computed on the SoC before SPI and verified by the EPS/PCM. Diverse from XOR, but credited only if XM-02 is confirmed · Panda RX checks on its own CAN view are independent of the SoC's RX path

<sub>Note: The hardware corruption rate on the 3X SPI bus is a DFMEA/FMEDA input. Here the cause is the weak software detection.</sub>

#### SWF-027 · pandad hangs or restarts while engaged

🔴 **H** · **S 10** · guideword *hang* · function `SWF-FN-024` Transfer commands and data between SoC and panda without undetected corruption. Detect link failure in bounded time and report it

Effects:

- **End:** Loss of lateral and longitudinal control. The SoC alert depends on selfdrived noticing missing pandaStates or CAN (HZ-004, S 10)
- **End:** Contributes to HZ-012 (driver misinformed while the device still shows engaged) (HZ-012, S 10)
- **Next higher:** Panda revokes authority after 0.3 s or is reset and releases the relay; steering and ACC end abruptly
- **Local:** No heartbeat, no can and no pandaStates. On restart, pandad.py resets or DFU-recovers the panda

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-027.C1` Unbounded SPI blocking. Control transfers use TIMEOUT 0, so spi_transfer_retry never times out (spi.cc:205-232). The loop also ends when connected becomes false, but no code ever clears connected (panda_comms.h:17). The fail-recovery loop waits for three NACKs without a limit (spi.cc:394-404). A panda that stops answering therefore blocks pandad, with the SPI lock held for both threads | • Upstream code, reviewed, -Werror; no requirement for bounded link-failure detection <sub>openpilot/selfdrive/pandad/spi.cc</sub> | • Hardware tests start pandad with the panda in reset, DFU or bootstub (startup recovery only, not a loss during a drive). Not run for BL-004 <sub>openpilot/selfdrive/pandad/tests/test_pandad.py</sub> | 7 | 9 | 🔴 **H** | SWF-ACT-021, SWF-ACT-029 |
| `SWF-027.C2` pandad crashes: asserts on a sendcan frame longer than 64 bytes or with a non-DLC length (panda.cc:181-182), asserts in spi_transfer (spi.cc:319-320), or the uncaught runtime_error from connect() when the firmware is out of date (pandad.cc:52-54). pandad.py then resets or DFU-recovers the internal panda on every restart (pandad.py:79-91). The new pandad briefly sets ELM327 param 1 while driving before it restores the car mode (panda_safety.cc:24-27) | • Upstream code, reviewed, ruff/ty on pandad.py; sendcan contents come from opendbc packers (fixed DLCs) <sub>openpilot/selfdrive/pandad/pandad.py</sub> | • Startup-recovery hardware tests only (not a crash while driving); not run for BL-004 <sub>openpilot/selfdrive/pandad/tests/test_pandad.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-021, SWF-ACT-029 |

Safety mechanisms: Panda heartbeat monitor revokes authority after 0.3 s (TSR-407). SILENT and a 3 s siren follow after the 1 Hz heartbeat timeout. 2026-10-13 (panda c33343b, all builds, not credited in the ratings): the siren also sounds at the revocation when authority was granted, about 0.56 s after the last heartbeat · selfdrived commIssue (SOFT_DISABLE) and canError (IMMEDIATE_DISABLE) when pandaStates or can stop (QM). manager does not flag a hung pandad, because the process is still running

<sub>Note: pandad.py also exits the setup loop with an AssertionError if more than one panda is listed (pandad.py:96), for example an external USB panda. The item is then unavailable but not hazardous. pandad leaves the panda in NO_OUTPUT on exit only when onroad and not engaged (pandad.cc:451-456). When engaged, it relies on the panda heartbeat timeout.</sub>

### `SWF-SE-026` Launcher and firmware check

#### SWF-028 · pandad runs against panda firmware that is not the assured reference build

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-025` Run pandad only against the intended panda firmware. Recover a panda in DFU or bootstub without disturbing an active drive

Effects:

- **End:** Any actuation hazard within an unlocked envelope (HZ-002, S 10)
- **End:** Contributes to HZ-005 (HZ-005, S 10)
- **End:** Contributes to HZ-006 (deceleration checked by an unlocked envelope) (HZ-006, S 10)
- **Next higher:** A wrong mode or param from the host (SWF-022) is accepted. TX rate and whitelist restrictions are absent
- **Local:** Panda runs firmware without the reference mode lock, the Toyota TX rate checks or the reference TX whitelist

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-028.C1` pandad.py and up_to_date() compare the panda signature with the panda_h7.bin.signed built from the checkout (pandad.py:16-18, 29-49; panda.cc:116-127). At BL-004 that build is not LIONDRIVER_REFERENCE, so the check passes a non-reference firmware. The host does not check a reference-build flag | • No build path sets LIONDRIVER_REFERENCE (SWF-013.C2); the release procedure is not defined <sub>panda/SConscript</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | SWF-ACT-028 |
| `SWF-028.C2` Test hooks are read from the environment in the production binary. BOARDD_SKIP_FW_CHECK skips the firmware check (pandad.cc:52), STARTED spoofs ignition so the car mode is kept with ignition off (pandad.cc:223-225), FAKESEND drops TX, and SPI_ERR_PROB corrupts transfers (spi.cc:280) | • No launch path sets these variables (grep over launch scripts, manager and tests; only tests set SPI_ERR_PROB and BOARDD_LOOPBACK). Setting them needs a shell on the device, which is a cybersecurity and PFMEA concern <sub>openpilot/system/manager/process_config.py</sub> | • No test targets this cause | 2 | 10 | 🔴 **H** | SWF-ACT-028 |

Safety mechanisms: The signature check confirms only that the panda matches the firmware in panda/board/obj, not that it is a reference build

### `SWF-SE-031` Engagement state machine

#### SWF-030 · selfdrived enters an engaged state with a NO_ENTRY condition active or without an ENABLE event

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-030` Engage only on an ENABLE event with no NO_ENTRY event active

Effects:

- **End:** Unintended engagement (bounded by the panda grant on a PCM cruise rising edge) (HZ-010, S 10)
- **Next higher:** controlsd sets latActive/longActive; pandad heartbeat reports engaged
- **Local:** selfdriveState.enabled/active true although entry conditions are not met

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-030.C1` Defect in the DISABLED branch of the state machine (ENABLE checked before NO_ENTRY, state.py:78-90) or in Events.contains (events.py:74-75) | • Upstream code with review; ruff and ty run in fork CI static_analysis; unit tests derived from the implementation; no software requirements <sub>scripts/lint/lint.sh:45,55; .github/workflows/tests.yaml</sub> | • test_no_entry and test_no_entry_pre_enable (ENABLE with NO_ENTRY stays disabled), run by tests.yaml unit_tests on every push and PR; not proven by mutation <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 6 | 8 | 🔴 **H** | SWF-ACT-030 |
| `SWF-030.C2` Test-only environment flags reach the vehicle: REPLAY sets the state to enabled when a panda reports controlsAllowed, bypassing ENABLE/NO_ENTRY (selfdrived.py:489-490); SIMULATION ignores cabinCameraState and managerState and makes every SubMaster alive/freq check pass once seen (selfdrived.py:86-87; cereal/messaging/__init__.py:211,265-266) | • Neither flag is set by the launch scripts or the manager (launch_*.sh, system/manager); nothing refuses to run or engage with them set <sub>openpilot/selfdrive/selfdrived/selfdrived.py:29-31</sub> | • No test targets this cause | 2 | 10 | 🔴 **H** | SWF-ACT-031 |

Safety mechanisms: Panda grants controls only on a PCM cruise rising edge with all RX checks valid (SWF-007, FSR-035); TX blocked otherwise · Panda withdraws controls on heartbeat engaged mismatch (about 3 s, SWF-014)

<sub>Note: test_state_machine covers the state machine only; the generation of NO_ENTRY events is not unit tested (see SWF-032, SWF-034). REPLAY still needs the panda to have granted controls, so the PCM rising edge remains required.</sub>

#### SWF-033 · Disengagement later than the fault tolerance time

🔴 **H** · **S 10** · guideword *late* · function `SWF-FN-031` Go to disabled in the same cycle on USER_DISABLE or IMMEDIATE_DISABLE, and within SOFT_DISABLE_TIME on a persisting SOFT_DISABLE

Effects:

- **End:** Lateral control continues on stale input (HZ-003, S 10)
- **End:** Longitudinal control continues on stale input (late deceleration for a lead) (HZ-007, S 10)
- **Next higher:** controlsd keeps actuating on stale or missing model, plan, calibration or panda data
- **Local:** State stays softDisabling (active) for 3 s or longer after an input is lost or stale

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-033.C1` Loss or staleness of an input to the control law is handled as SOFT_DISABLE (commIssue, commIssueAvgFreq, processNotRunning, modeldLagging, selfdrivedLagging; events.py:853-872, 886-896), i.e. 3 s of continued actuation (state.py:7, 38-41); sensorDataInvalid only after 10 s without IMU data (selfdrived.py:418-419). TSR-601 asks immediate disable; no event is justified against an FTTI (SFM-016, GAP-16) | • Reaction types chosen upstream; FSC WD-01 notes the 3 s must be justified per event (not done) <sub>openpilot/selfdrive/selfdrived/events.py</sub> | • test_soft_disable_timer checks that the timer is 3 s; it is not designed to show that 3 s is within the FTTI <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 8 | 9 | 🔴 **H** | SWF-ACT-035 |
| `SWF-033.C2` Every timer counts loop iterations, not time: soft_disable_timer (state.py:20, 40), mismatch_counter, cruise_mismatch_counter and the sm.frame gates (selfdrived.py:338, 418, 425). The loop is paced by the carState receive (20 ms timeout) with monitor_time only (selfdrived.py:83, 586-588) and does blocking Params writes (selfdrived.py:220, 306, 468), so when it slows, every timeout stretches (3 s soft disable is 6 s at 50 Hz) | • Upstream code with review; ruff and ty in fork CI; no unit test of selfdrived.py event generation; no software requirements <sub>scripts/lint/lint.sh:45,55</sub> | • No test targets this cause | 6 | 10 | 🔴 **H** | SWF-ACT-035 |

Safety mechanisms: Takeover alert with sound during soft disable (SoftDisableAlert, events.py:161-166) · Panda bounds torque and acceleration (SWF-001, SWF-003); no panda check of command freshness (SWF-014.C2)

#### SWF-038 · Lateral control keeps commanding torque while the driver steers

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-037` Enter overriding while the driver steers and yield lateral control

Effects:

- **End:** Item resists the driver's steering within the panda torque bound (HZ-009, S 10)
- **Next higher:** controlsd keeps latActive true; the torque controller only freezes its integrator
- **Local:** State overriding is in ACTIVE_STATES, so selfdriveState.active stays true

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-038.C1` By design, overriding counts as active (state.py:8, 43-45); controlsd sets latActive from selfdriveState.active (controlsd.py:100-101) and latcontrol_torque freezes only the integrator on steeringPressed (latcontrol_torque.py:92). FSR-033 ("stop commanding torque while driver steering input is detected") is not implemented as written | • Upstream design intent (driver overpowers a bounded torque); no LionDriver requirement analysis of the deviation <sub>openpilot/selfdrive/selfdrived/state.py:8</sub> | • test_maintain_states checks that overriding persists with OVERRIDE events; it does not check commanded torque <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 8 | 9 | 🔴 **H** | SWF-ACT-039 |

Safety mechanisms: Panda torque magnitude, rate and measured-torque-error limits (SWF-001, FSR-032) · Driver can overpower the EPS LKA torque (assumed; FSR-031 vehicle test planned, not done)

<sub>Note: FSC FSR-033 cites test_state_machine.py as verification; that test cannot show the torque is withdrawn. Whether this is hazardous depends on the measured override force (FSR-031).</sub>

### `SWF-SE-032` Input sampling and event generation

#### SWF-031 · selfdrived does not disengage on driver brake or cancel

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-031` Go to disabled in the same cycle on USER_DISABLE or IMMEDIATE_DISABLE, and within SOFT_DISABLE_TIME on a persisting SOFT_DISABLE

Effects:

- **End:** Automation not released on brake or cancel by the SoC (panda withdraws independently) (HZ-008, S 10)
- **Next higher:** controlsd keeps latActive/longActive; heartbeat keeps engaged=1
- **Local:** No pedalPressed / pcmDisable / buttonCancel event, state stays engaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-031.C1` carState is read from its own socket with a 20 ms timeout and the previous carState is reused when nothing arrives (selfdrived.py:83, 472-473); carState is not in the SubMaster, so it has no alive/freq check. A card stall freezes brakePressed, cruiseState and canValid, so no driver-action event is raised; the stall is only seen indirectly (selfdrivedLagging after about 0.2 s, carOutput commIssue after 0.1 s), both SOFT_DISABLE (3 s or longer, SWF-033.C2) | • Upstream design (TODO at selfdrived.py:82); ruff + ty; no freshness check on carState (TSR-602 asks it of controlsd only) <sub>openpilot/selfdrive/selfdrived/selfdrived.py:82-83</sub> | • No test targets this cause | 6 | 10 | 🔴 **H** | SWF-ACT-032 |
| `SWF-031.C2` Defect in the brake/gas rising-edge logic (selfdrived.py:253-256), in the canValid gate on car events (selfdrived.py:242-244), or in the USER_DISABLE priority of the state machine (state.py:31-33) | • Upstream code with review; ruff and ty in fork CI; no unit test of selfdrived.py event generation; no software requirements <sub>scripts/lint/lint.sh:45,55</sub> | • test_user_disable covers the state-machine part (USER_DISABLE from every state), CI unit_tests, not proven; the pedal edge logic is exercised only by process_replay over recorded segments (generic regression, includes a Corolla TSS2 segment) <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 7 | 8 | 🔴 **H** | SWF-ACT-030 |

Safety mechanisms: Panda withdraws controls on brake rising edge and PCM cruise off from vehicle CAN, independently of the SoC (SWF-008, SWF-009, FSR-029) · PCM cancels cruise on its own brake input (XM-03, FOI-006, unverified) · A card stall also stops sendcan, so no new item frames reach the panda (card.py:234-240)

<sub>Note: With canValid false, car events are skipped but canError (IMMEDIATE_DISABLE) is raised (selfdrived.py:378-381), so that branch is not a cause. FSR-030 verification cites test_state_machine, which does not exercise brake detection.</sub>

#### SWF-034 · Panda/host disagreement on safety mode or controls-allowed detected late or not at all

🔴 **H** · **S 10** · guideword *late* · function `SWF-FN-032` Raise fault and driver-action events from carState, pandaStates and process/message supervision, including controlsMismatch when the panda safety model, parameter or controls-allowed disagrees

Effects:

- **End:** Steering or ACC stops while the device shows engaged; no takeover request (HZ-004, S 10)
- **End:** Driver misinformed about the automation state (HZ-012, S 10)
- **End:** Contributes to HZ-002 through a wrong safety parameter not detected (HZ-002, S 10)
- **Next higher:** Panda blocks item frames while the device and pandad report engaged; or the panda runs a wrong model or parameter unnoticed
- **Local:** controlsMismatch raised late; state stays engaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-034.C1` controlsMismatch needs 200 cycles (about 2 s, cumulative per engagement) with a panda reporting controlsAllowed false; the comment says two samples (selfdrived.py:338, 504-514). TSR-621 asks at most 2 samples and 0.5 s | • Upstream threshold; TSR-621 records it as partial <sub>openpilot/selfdrive/selfdrived/selfdrived.py:504-514</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | SWF-ACT-033 |
| `SWF-034.C2` Safety model, parameter and alternative-experience mismatch is ignored for the first 10 s after selfdrived starts (sm.frame*DT_CTRL > 10, selfdrived.py:338), so an engagement in that window with a wrong mode or parameter that still grants controls is not refused | • Initialization takes up to 6 s (selfdrived.py:477-480); the wrong mode itself needs SWF-013 (reference lock not built at BL-004) <sub>openpilot/selfdrive/selfdrived/selfdrived.py:337-339</sub> | • No test targets this cause | 4 | 10 | 🔴 **H** | SWF-ACT-033 |
| `SWF-034.C3` Stale pandaStates (pandad stalled): the last message, with controlsAllowed true, is reused, so the mismatch counter does not count; only commIssue after the 1 s alive window (10 Hz service), then a 3 s soft disable (TSR-626a asks 0.2 s) | • Upstream code with review; ruff and ty in fork CI; no unit test of selfdrived.py event generation; no software requirements <sub>scripts/lint/lint.sh:45,55</sub> | • No test targets this cause | 6 | 10 | 🔴 **H** | SWF-ACT-033 |

Safety mechanisms: Panda itself blocks the item frames, so the mismatch is a loss of control, not extra actuation · Cluster shows LKA/ACC state from stock ECUs once item frames stop (XM-04, FOI-005, unverified)

#### SWF-039 · PCM cruise active while selfdrived is not engaged, without warning or reaction

🔴 **H** · **S 10** · guideword *wrong_mode* · function `SWF-FN-038` Detect PCM cruise active while not engaged and warn the driver

Effects:

- **End:** Stock cruise active without the driver knowing (HZ-012, S 10)
- **Next higher:** Device shows disengaged while the cluster shows cruise on; panda controls_allowed may be granted until the heartbeat mismatch revokes it
- **Local:** cruiseMismatch raised after 6 s and ignored

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-039.C1` cruiseMismatch has no reaction or alert (events.py:458-460, alert commented out) and is raised only after 6 s (selfdrived.py:421-426); it covers the case where the cancel request from controlsd (controlsd.py:162) does not take effect. TSR-308 asks a warning and cancel request within 1 s (GAP-19) | • controlsd requests ACC cancel while PCM cruise is on and the item is not enabled (EL-03) <sub>openpilot/selfdrive/controls/controlsd.py:162</sub> | • test_events_defined only checks that the event exists (passes with an empty reaction) <sub>openpilot/selfdrive/selfdrived/tests/test_alerts.py</sub> | 8 | 9 | 🔴 **H** | SWF-ACT-034 |

Safety mechanisms: Panda engaged-mismatch counter revokes controls after about 3 s when the heartbeat says not engaged (SWF-014)

<sub>Note: Vehicle behaviour with PCM cruise on and the item not sending a valid ACC command is not characterised for the Corolla (uncertain).</sub>

#### SWF-051 · Forward collision warning raised from stale or invalid model or planner input

🔴 **H** · **S 10** · guideword *value_stale* · function `SWF-FN-049` Raise the forward collision warning only from fresh and valid modelV2 and longitudinalPlan inputs (TSR-625)

Effects:

- **End:** Reflex hard braking by the driver with a close follower (HE-04.5) (HZ-006, S 10)
- **Next higher:** False forward collision warning
- **Local:** fcw event from modelV2.meta.hardBrakePredicted or longitudinalPlan.fcw with no alive, valid or age check of its own (selfdrived.py:470-475)

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-051.C1` The FCW condition reads the last received modelV2 and longitudinalPlan; a held or invalid message keeps raising FCW in the same cycle in which commIssue is raised (TSR-625 freshness gate not implemented) | • Upstream design, reviewed; no derived freshness requirement for FCW inputs at BL-004 <sub>openpilot/selfdrive/selfdrived/selfdrived.py</sub> | • No test targets this cause | 7 | 10 | 🔴 **H** | SWF-ACT-051 |

Safety mechanisms: None for FCW; commIssue soft-disables control when modelV2 or longitudinalPlan is not alive or not valid

<sub>Note: WP-A-04 BE-4.11 (SG-04 G4.5). False leads that trigger a valid FCW are SOTIF (SFM-009.C1, WP-C-06).</sub>

### `SWF-SE-033` Event catalogue and reaction mapping

#### SWF-032 · A detected or reportable fault leads to no disable reaction while engaged

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-033` Give each event the reaction type (no entry, soft or immediate disable, user disable) and alert its fault requires

Effects:

- **End:** Item continues, or the panda stops it while the driver is told it is engaged (HZ-012, S 10)
- **End:** Contributes to HZ-004 (loss of lateral control without timely warning) (HZ-004, S 10)
- **Next higher:** State stays enabled; device shows engaged
- **Local:** No event, or an event without a disable type, for a fault condition

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-032.C1` Panda health flags are published by pandad but not read by selfdrived: heartbeatLost, safetyTxBlocked, txRateExceeded (LionDriver #43) and every fault other than relayMalfunction (pandad.cc:112,124,139; selfdrived.py:328-346). TSR-615 asks for an immediate disable on each | • Only relayMalfunction, safety model/param and controlsAllowed are checked (selfdrived.py:328-346) <sub>openpilot/selfdrive/selfdrived/selfdrived.py:328-346</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | SWF-ACT-033 |
| `SWF-032.C2` Diagnostics masked on the big-model path: commIssue is suppressed for every service while ChestnutLoading is set and for 5 s after, and posenet, locationd, paramsd and modeldLagging checks are skipped (selfdrived.py:384-388, 407, 461; GAP-17, TSR-603). Active only when the chestnut models are compiled and the accelerator or a USB-C cable is detected (modeld.py:232); nothing enforces its absence in the reference configuration | • bigModelLoading is NO_ENTRY (events.py:407-409), so masking at start-up blocks engagement until load ends; the 5 s settling window has no NO_ENTRY <sub>openpilot/selfdrive/selfdrived/events.py:407-414</sub> | • No test targets this cause (test_onroad checks ChestnutActive on device only) | 4 | 10 | 🔴 **H** | SWF-ACT-031 |

Safety mechanisms: Panda blocks TX on its own faults, heartbeat loss (0.3 s) and TX violations (SWF-014, SWF-016); the host may then show engaged until controlsMismatch (SWF-034)

<sub>Note: SFM-014.C3 (commIssue suppressed by no_system_errors, selfdrived.py:384-385) was checked: suppression needs another NO_ENTRY and SOFT/IMMEDIATE event in the same cycle, so a disable reaction is still present; only the alert text and log name the wrong fault. Not rated as a cause. The canError alert reads "Unknown Vehicle Variant" for any CAN validity loss (events.py:928-936), against TSR-606 (fault class in the text); HMI quality issue, noted only.</sub>

### `SWF-SE-034` Alert manager

#### SWF-035 · Takeover request masked by a lower-urgency alert

🔴 **H** · **S 10** · guideword *wrong_mode* · function `SWF-FN-034` Present the most urgent alert; every takeover request visual and audible

Effects:

- **End:** Missing or late handback warning (HZ-012, S 10)
- **End:** Contributes to HZ-004 (HZ-004, S 10)
- **Next higher:** Driver not told to take over during the soft-disable period
- **Local:** Another alert is selected instead of the soft-disable takeover alert; soundd plays that alert's sound

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-035.C1` Selection is by priority, then start frame (alertmanager.py:63). SoftDisableAlert is Priority.MID (events.py:161-166), below speedTooHigh (WARNING, HIGH, promptRepeat, events.py:995-1000), aeb/stockAeb (PERMANENT, HIGHEST, no sound, events.py:471-485) and driverDistracted3/driverUnresponsive3 (HIGH); the takeover text and warningSoft can be hidden for the first 2.5 s and only the last 0.5 s becomes ImmediateDisableAlert (events.py:224-228) | • Upstream code with review; ruff and ty run in fork CI static_analysis; unit tests derived from the implementation; no software requirements <sub>scripts/lint/lint.sh:45,55; .github/workflows/tests.yaml</sub> | • test_alertmanager checks alert duration only; test_alerts checks text/size sanity; neither checks priority between takeover and other alerts <sub>openpilot/selfdrive/selfdrived/tests/test_alertmanager.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-036 |

Safety mechanisms: The masking alerts are themselves visual (driverDistracted3 also audible, warningImmediate); ImmediateDisableAlert is HIGHEST · Cluster indication once the item stops (XM-04, unverified)

<sub>Note: speedTooHigh needs vEgo above MAX_CTRL_SPEED (149 km/h, opendbc interfaces.py:23-24); aeb/stockAeb coincide with an emergency, where the AEB alert may be the right one but its lack of sound also removes the takeover sound. driverDistracted3 masking is benign (also a takeover-type alert).</sub>

### `SWF-SE-035` Excessive actuation check

#### SWF-037 · Excessive vehicle response while engaged not detected

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-035` Detect excessive longitudinal or lateral vehicle response while engaged and soft-disable

Effects:

- **End:** Excessive acceleration caused by another fault continues (multiple-point with the primary cause) (HZ-005, S 10)
- **End:** Excessive deceleration continues (HZ-006, S 10)
- **End:** Excessive lateral response continues (HZ-002, S 10)
- **Next higher:** No soft disable from the secondary monitor
- **Local:** excessiveActuation not latched

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-037.C1` Thresholds at twice the envelope: longitudinal above 2*ACCEL_MAX (4 m/s²) or below 2*ACCEL_MIN (-7 m/s²), lateral above 2*ISO_LATERAL_ACCEL (6 m/s²), for more than 0.25 s, lateral only after 1 s of latActive without steering input (helpers.py:12-13, 30, 39-41, 49); reaction is SOFT_DISABLE (events.py:795-798). Responses between the envelope and twice the envelope are never detected; matches TSR-617 as written | • Upstream thresholds, kept by TSR-617; not derived from a vehicle envelope (FSC FOI-001) <sub>openpilot/selfdrive/selfdrived/helpers.py:12-13</sub> | • No test targets this cause (no unit test of helpers.py) | 8 | 10 | 🔴 **H** | SWF-ACT-038 |
| `SWF-037.C2` The counter is reset whenever \|aEgo - IMU acceleration\| >= 2 m/s² (device_motion_valid, helpers.py:45-46), which also holds in wheel slip or lock during a gross event (SFM-030.C2); no check until a calibrated pose exists (selfdrived.py:303); latched pose reused when deviceMotion stops (selfdrived.py:299-301) | • Upstream code with review; ruff and ty in fork CI; no unit test of selfdrived.py event generation; no software requirements <sub>scripts/lint/lint.sh:45,55</sub> | • No test targets this cause | 6 | 10 | 🔴 **H** | SWF-ACT-038 |

Safety mechanisms: Panda acceleration range and torque limits are the primary bound (SWF-001, SWF-003)

<sub>Note: Secondary monitor (latent-fault candidate, SFM-030). The longitudinal check is gated by carControl.longActive, so braking during an override is not checked.</sub>

### `SWF-SE-036` selfdriveState publication and main loop

#### SWF-036 · selfdrived stops publishing selfdriveState (crash or hang) while engaged

🔴 **H** · **S 10** · guideword *crash* · function `SWF-FN-036` Publish selfdriveState (enabled, active, alert) every 10 ms cycle, consistent with the state machine

Effects:

- **End:** Steering and ACC stop within about 0.1 s with no device takeover warning for 5 s (HZ-004, S 10)
- **End:** Driver misinformed about the automation state (HZ-012, S 10)
- **Next higher:** pandad sends heartbeat engaged=0 after about 0.1 s (pandad.cc:424); controlsd blocks on poll (controlsd.py:43); card stops sendcan once carControl is not alive (card.py:234); ui and soundd show the critical "System Unresponsive" alert only after 5 s (ui/onroad/alert_renderer.py:30, 100-102; soundd.py:23, 56-59)
- **Local:** No selfdriveState; no alerts generated

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-036.C1` Unhandled exception on unexpected input content or state (e.g. callback alerts, events from car_events); selfdrived is excluded from the fuzz test (test_fuzzy.py:13 NOT_TESTED) | • Upstream code with review; ruff and ty in fork CI; no unit test of selfdrived.py event generation; no software requirements <sub>scripts/lint/lint.sh:45,55</sub> | • process_replay runs selfdrived over recorded segments in CI (generic; would catch a crash on those inputs only) <sub>openpilot/selfdrive/test/process_replay/test_processes.py</sub> | 7 | 9 | 🔴 **H** | SWF-ACT-037 |
| `SWF-036.C2` Hang or starvation of the Python process (blocking Params writes in the 100 Hz loop, selfdrived.py:220, 306, 468; GIL contention with params_thread; CPU load); no process watchdog for selfdrived (process_config.py:97) | • Real-time priority CTRL_HIGH on core 4 (selfdrived.py:595); manager restarts a dead process but not a hung one (system/manager/process.py:223-238) <sub>openpilot/selfdrive/selfdrived/selfdrived.py:594-597</sub> | • No test targets this cause | 5 | 10 | 🔴 **H** | SWF-ACT-037 |

Safety mechanisms: Panda withdraws controls on engaged mismatch (about 3 s) and heartbeat loss (0.3 s) (SWF-014) · UI and soundd critical alert after 5 s without selfdriveState (EL-05, QM) · Cluster indication from stock ECUs when item frames stop (XM-04, unverified)

### `SWF-SE-041` controlsd main loop, input handling and actuator gating

#### SWF-040 · Actuation continues on a stale engagement state after selfdrived stops publishing

🔴 **H** · **S 10** · guideword *value_stale* · function `SWF-FN-040` Request lateral control only while selfdriveState is active, no EPS fault is reported and the car is above the minimum steer speed; request longitudinal control only while enabled and not overridden

Effects:

- **End:** About 3 s of unsupervised lateral control; a model or input fault in that window is not acted on (HZ-003, S 10)
- **End:** Unsupervised longitudinal control for the same window (HZ-005, S 10)
- **Next higher:** Steering and acceleration continue with no supervision of model, localizer or comm faults; pandad drops heartbeat engaged after 0.1 s (pandad.cc:424) but the panda withdraws only after the engaged-mismatch count, about 3 s (panda main.c:226-232, SWF-014.C2)
- **Local:** sm.update(15) times out and the loop keeps running on the last selfdriveState (active=True); latActive and longActive stay true and carControl keeps being published

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-040.C1` controlsd reads selfdriveState.enabled/active with no alive, valid or age check (controlsd.py:96-102); the SubMaster keeps the last message and the poll only bounds the wait to 15 ms (controlsd.py:41-43, 66; cereal/messaging/__init__.py:235-266). carControl.valid is CS.canValid only (controlsd.py:187-188, 223), so card cannot see that the inputs are stale and checks only that carControl is alive (card.py:234) | • Upstream design relies on selfdrived and the panda; TSR-602 (freshness check in controlsd) recorded as not met (GAP-16). Review and lint only <sub>assurance/03-system/WP-S-02-technical-safety-requirements.md (TSR-602)</sub> | • No test stops selfdrived while engaged; process_replay feeds recorded selfdriveState only | 7 | 10 | 🔴 **H** | SWF-ACT-040, SWF-ACT-047 |

Safety mechanisms: pandad sends heartbeat engaged=false 0.1 s after selfdriveState stops; panda withdraws controls after 3 mismatches at 1 Hz (about 3 s); panda withdraws on brake and PCM cruise off independently (SWF-008, SWF-009) · Torque magnitude/rate and acceleration range limits in the panda and CarController bound the actuation (SWF-001, SWF-003)

<sub>Note: Host counterpart of SWF-014.C2. If selfdrived dies, selfdrived's own commIssue/processNotRunning cannot be raised, so no device alert is given either (manager does not alert). The 3 s figure is the panda mismatch path at BL-004; TSR-307a (0.3 s) is not implemented.</sub>

#### SWF-043 · Lateral and longitudinal commands computed from stale or frozen model and planner outputs

🔴 **H** · **S 10** · guideword *value_frozen* · function `SWF-FN-041` Compute actuation only from fresh, valid and finite inputs (selfdriveState, modelV2, longitudinalPlan, vehicleParameters, lateralTorqueParameters, deviceMotion), and stop actuating otherwise

Effects:

- **End:** Vehicle follows a frozen curvature out of the lane (HZ-003, S 10)
- **End:** Frozen positive acceleration toward a lead (HZ-005, S 10)
- **End:** Frozen deceleration request (HZ-006, S 10)
- **End:** No response to a slowing lead during the frozen window (HZ-007, S 10)
- **Next higher:** Constant curvature and acceleration commanded through the alive window (0.5 s for modelV2/longitudinalPlan at 20 Hz) and the 3 s soft-disable that follows, since softDisabling is an active state (state.py:7-8)
- **Local:** desiredCurvature and aTarget held at their last values while the publisher is stopped or lagging

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-043.C1` modelV2 and longitudinalPlan used with no alive, valid or age check (controlsd.py:92-93, 119, 126); cs.lateralPlanMonoTime and longitudinalPlanMonoTime are logged only (196-197). The only reaction is selfdrived commIssue/modeldLagging, which are SOFT_DISABLE (3 s of continued control) | • TSR-602 (age check, ≤ 2 periods, latActive/longActive false) recorded as not met (GAP-16); review and lint only <sub>assurance/03-system/WP-S-02-technical-safety-requirements.md (TSR-602)</sub> | • No test stops modeld or plannerd while engaged | 7 | 10 | 🔴 **H** | SWF-ACT-040, SWF-ACT-048 |
| `SWF-043.C2` selfdrived suppresses commIssue while the big model is loading or settling (selfdrived.py:386-388), so held modelV2 reaches controlsd without any reaction for that window (selfdrived element; recorded here because controlsd has no check of its own) | • TSR-603 (no masking while engaged) not met (WP-W-04 SWF-44, GAP-17) | • test_onroad TestChestnutOnroad needs device hardware; not run | 7 | 10 | 🔴 **H** | SWF-ACT-040 |

Safety mechanisms: selfdrived commIssue (alive window 10 periods) and modeldLagging soft-disable with a 3 s audible take-over warning · Panda bounds torque and acceleration range only; clip_curvature bounds rate of change of a frozen value to zero, not its level

#### SWF-045 · A non-finite input latches the controller state and silently zeroes lateral (or longitudinal) output while engaged

🔴 **H** · **S 10** · guideword *corrupted* · function `SWF-FN-041` Compute actuation only from fresh, valid and finite inputs (selfdriveState, modelV2, longitudinalPlan, vehicleParameters, lateralTorqueParameters, deviceMotion), and stop actuating otherwise

Effects:

- **End:** Loss of lateral control while engaged without a driver warning, for the rest of the drive (HZ-004, S 10)
- **End:** No deceleration for a lead while ACC is shown engaged (HZ-007, S 10)
- **End:** Driver misinformed about automation state (HZ-012, S 10)
- **Next higher:** Zero torque (and, for aTarget, zero acceleration) commanded with latActive/longActive true and no event; the HMI and cluster still show the item engaged
- **Local:** self.desired_curvature and the torque PID integrator become NaN and stay NaN; the sanitiser replaces the outputs with 0 and only logs (controlsd.py:139-147)

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-045.C1` A NaN desired curvature (modelV2 or lateralManeuverPlan) or roll passes clip_curvature (np.clip propagates NaN, drive_helpers.py:32-41) into self.desired_curvature, which is the clip reference for every later frame (controlsd.py:127), so it never recovers, even while disengaged; the PID integrator also becomes NaN (pid.py:48-55) and is never reset (SWF-042.C1). Reproduced with the BL-004 clip_curvature and PIDController in isolation (scratch probe, not a repo test) | • Upstream sanitiser replaces non-finite actuators by 0 and logs; TSR-604 (non-finite = fault, immediate disable) not met (GAP-19); modeld checks finiteness only for the big model (modeld.py:210) <sub>assurance/03-system/WP-S-02-technical-safety-requirements.md (TSR-604)</sub> | • controlsd and card are excluded from the process fuzz test because NaN/inf break them (test_fuzzy.py:10-13); no NaN injection test <sub>openpilot/selfdrive/test/process_replay/test_fuzzy.py</sub> | 6 | 10 | 🔴 **H** | SWF-ACT-041, SWF-ACT-044 |
| `SWF-045.C2` A NaN aTarget makes the LongControl PID integrator NaN even with ki=0 (0·NaN), so accel stays NaN, sanitised to 0, until the state machine leaves pid (longcontrol.py:56-71) | • Planner clips aTarget (longitudinal_planner.py:149) but np.clip keeps NaN; no finiteness check | • test_longcontrol.py covers state transitions only <sub>openpilot/selfdrive/controls/tests/test_longcontrol.py</sub> | 6 | 10 | 🔴 **H** | SWF-ACT-041, SWF-ACT-044 |

Safety mechanisms: None that detects the latch; steerSaturated cannot fire (abs(NaN) comparisons are false); FCW from the planner remains

<sub>Note: Occurrence of a NaN at the inputs is not evidenced; the rating reflects the absence of any guard rather than an observed rate.</sub>

#### SWF-048 · PCM cruise cancel not requested, or not effective, when the item is not enabled

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-046` Request PCM cruise cancel whenever PCM cruise is engaged and the item is not enabled

Effects:

- **End:** Stock/PCM cruise active while the driver believes the item is off (HZ-012, S 10)
- **End:** Control not released when the driver cancels through the device (HZ-008, S 10)
- **Next higher:** PCM cruise stays engaged; the panda keeps controls allowed until the heartbeat-mismatch revoke (about 3 s)
- **Local:** CANCEL_REQ not set while CS.cruiseState.enabled and the item is disengaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-048.C1` cancel = CS.cruiseState.enabled and not CC.enabled (controlsd.py:162), where CC.enabled is the unchecked selfdriveState (SWF-040.C1), and it is sent only inside the 33 Hz ACC_CONTROL frame (carcontroller.py:187, 253) while card is actuating. The selfdrived backstop does nothing: cruiseMismatch fires after 6 s (selfdrived.py:423-426) but has no alert or disable type (events.py:458-460, commented out) | • Upstream review and lint | • opendbc test_models checks that a cancel frame passes the panda model, not that cancel is requested on each disengagement path; not run in LionDriver CI <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-040, SWF-ACT-049 |

Safety mechanisms: PCM cancels on brake (XM-03, external); panda withdraws controls on brake and PCM cruise off, and on heartbeat mismatch after about 3 s

#### SWF-049 · Desired curvature taken from the developer lateral-maneuver plan instead of the driving model

🔴 **H** · **S 10** · guideword *wrong_mode* · function `SWF-FN-041` Compute actuation only from fresh, valid and finite inputs (selfdriveState, modelV2, longitudinalPlan, vehicleParameters, lateralTorqueParameters, deviceMotion), and stop actuating otherwise

Effects:

- **End:** Vehicle steered off the lane path at normal magnitude (HZ-003, S 10)
- **Next higher:** Lateral control no longer follows the lane
- **Local:** Scripted curvature steps and sine/jitter maneuvers (±0.5 m/s² and more) are commanded; a stopped publisher leaves its last curvature in use

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-049.C1` controlsd uses lateralManeuverPlan whenever its last message was valid (controlsd.py:123-124), with no alive check (SubMaster valid changes only on receipt, cereal/messaging/__init__.py:261) and no check of the mode; selfdrived ignores lateralManeuverPlan in its alive/valid checks (selfdrived.py:85). The path is enabled by the LateralManeuverMode developer toggle (process_config.py:43-44, 109; developer.py:134, offroad only; cleared at manager start and offroad, params_keys.h:87) | • Operational rule only (WP-V-07 bans developer modes; INS-19 reference parameters); TSR-613 (path absent from reference builds) not met (GAP-20). Permanent "Lateral Maneuver Mode" banner when active (selfdrived.py:184-186) <sub>assurance/03-system/WP-S-02-technical-safety-requirements.md (TSR-613)</sub> | • No test checks that the path is absent or inactive in the shipped configuration | 7 | 10 | 🔴 **H** | SWF-ACT-047 |

Safety mechanisms: lateral_maneuversd aborts on steering or gas press; processNotRunning soft-disable if it crashes while the toggle is set; panda torque limits

<sub>Note: Occurrence rated on the prevention controls (none technical), not on how often a user enables developer mode.</sub>

#### SWF-050 · Item-initiated deceleration starts without a prior announcement

🔴 **H** · **S 10** · guideword *omission* · function `SWF-FN-048` Command deceleration that traffic does not require (driver-monitoring no-response, soft-disable force deceleration) only after it has been announced, and keep it announced while it lasts (TSR-624)

Effects:

- **End:** Unannounced item-initiated deceleration; rear-end collision by following traffic (HE-04.3) (HZ-006, S 10)
- **Next higher:** Vehicle slows toward standstill; the soft-disable alert and the deceleration begin together
- **Local:** forceDecel set in the same cycle as softDisabling or noResponseForceDecel (controlsd.py:235-236); the planner sets the cruise target to 0 at once (longitudinal_planner.py:84-85)

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-050.C1` No lead time between the announcement and the onset of a fault soft-disable deceleration. Only the driver-monitoring no-response deceleration is preceded by escalating alerts (driverUnresponsive1..3); TSR-624 is recorded as partial | • DM escalation alerts precede the no-response deceleration; nothing precedes a fault soft-disable deceleration <sub>openpilot/selfdrive/monitoring/policy.py</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | SWF-ACT-050 |

Safety mechanisms: Soft-disable alert (audible, 3 s) at onset; panda deceleration bound -3.5 m/s² (SWF-003). No jerk bound (SWF-004)

<sub>Note: WP-A-04 BE-4.10 (SG-04 G4.4); SFM-026 covers an alert that is not presented at all.</sub>

### `SWF-SE-042` Lateral torque controller

#### SWF-042 · Steering torque request too high, biased or overshooting within the CarController and panda limits

🔴 **H** · **S 10** · guideword *value_high* · function `SWF-FN-042` Generate a steering torque request that tracks the limited desired curvature within the envelope and yields while the driver steers

Effects:

- **End:** Vehicle steered toward or across the lane boundary at normal intervention magnitude (HZ-003, S 10)
- **End:** Abrupt steering pull at engagement (HZ-002, S 10)
- **Next higher:** Lateral pull or overshoot within 1500 units and 15/25 units per frame
- **Local:** Torque request differs from what the desired curvature needs (step on engagement, steady bias or overshoot)

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-042.C1` LatControlTorque does not reset its PID integrator when lateral control ends: controlsd calls LaC.reset() when not latActive (controlsd.py:112-113), but LatControlTorque has no reset() override and the base class clears only sat_time (latcontrol.py:19-20); the inactive branch skips pid.update (latcontrol_torque.py:114-116). The integrator from the last engagement (bounded by the lat-accel limits, pid.py:48-55) is added on the next engagement | • Upstream review and lint; LatControlCurvature does reset its PID (latcontrol_curvature.py:28-31), so the omission may be an oversight or deliberate upstream; no requirement states either <sub>openpilot/selfdrive/controls/lib/latcontrol_curvature.py</sub> | • test_latcontrol.py covers saturation only; test_latcontrol_torque_buffer.py covers the request buffer only; nothing checks controller state across disengagement | 7 | 10 | 🔴 **H** | SWF-ACT-042, SWF-ACT-043 |
| `SWF-042.C2` lateralTorqueParameters applied when all_checks and useParams pass with no plausibility bound in controlsd (controlsd.py:86-90); torqued clips latAccelFactor (±30 %) and friction but not latAccelOffset (torqued.py:229-232), which enters the feed-forward directly (latcontrol_torque.py:111) as a steady lateral bias | • torqued factor/friction sanity bounds and filtering; offset estimator tested for accuracy, not bounded <sub>openpilot/selfdrive/locationd/torqued.py</sub> | • test_torqued_lat_accel_offset.py checks the estimate on synthetic data, not a bound on what controlsd applies <sub>openpilot/selfdrive/controls/tests/test_torqued_lat_accel_offset.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-045 |
| `SWF-042.C3` vehicleParameters (steerRatio, stiffness, angleOffset, roll) used with no alive or valid check, only a 0.1 floor (controlsd.py:77-83); roll also widens the clip_curvature lateral-acceleration bound by roll·g (drive_helpers.py:36-39), up to about ±1.7 m/s² at the paramsd roll limit of ±10° (paramsd.py:18) | • paramsd rate limits and bounds roll and angle offset (paramsd.py:16-19, 143-147) and publishes valid; selfdrived soft-disables on paramsdTemporaryError. controlsd itself does not check <sub>openpilot/selfdrive/locationd/paramsd.py</sub> | • process_replay runs controlsd with recorded vehicleParameters; not designed for implausible values <sub>openpilot/selfdrive/test/process_replay/test_processes.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-040, SWF-ACT-045 |

Safety mechanisms: clip_curvature limits desired curvature to 5 m/s³ lateral jerk and 3.0 m/s² (+ roll) lateral acceleration · CarController torque limits: 1500, 15 up / 25 down per frame, 350 from measured EPS torque (same constants as the panda, SWF-001.C1) · Panda torque magnitude, rate and measured-error checks (SWF-001); steerSaturated warning in selfdrived (driver alert only) · No independent lane-departure monitor (FSR-014 gap, FOI-004); nothing bounds lane-keeping error

#### SWF-044 · Steering torque kept up while the driver steers against the item

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-042` Generate a steering torque request that tracks the limited desired curvature within the envelope and yields while the driver steers

Effects:

- **End:** Item resists driver steering input (HZ-009, S 10)
- **Next higher:** Driver fights up to 1500 units of item torque
- **Local:** Torque command continues during a driver override below 500 units of driver torque

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-044.C1` overriding is an active state (state.py:8), so latActive stays true (controlsd.py:100); steeringPressed (driver torque > 100, values.py:585) only freezes the integrator (latcontrol_torque.py:121); CarController cuts torque only above 500 units of driver torque (carcontroller.py:33, 83) | • No SoC requirement to reduce torque on override (STPA LS-01, OI-2; TSR-304 envelope counterpart not implemented, GAP-02) <sub>assurance/08-analyses/WP-A-05-stpa.md</sub> | • No test | 7 | 10 | 🔴 **H** | SWF-ACT-046 |

Safety mechanisms: Panda torque limit 1500 and rate limits; driver can overpower the EPS (AOU-02, unverified on the Corolla) · CarController drops lat_active above 500 units of driver torque

<sub>Note: STPA cites latcontrol_torque.py:92 for the integrator freeze; at BL-004 the line is 121.</sub>

### `SWF-SE-045` Toyota CarController

#### SWF-041 · Non-zero steering torque or the steer request bit sent while lateral control is not active

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-045` Apply torque magnitude, rate and measured-torque limits; send zero torque with the request bit cleared when lateral control is not active; send the ACC command within the acceleration range

Effects:

- **End:** Unintended steering while the item is not engaged (HZ-001, S 10)
- **Next higher:** Blocked by the panda when controls are not allowed; passed when PCM cruise is still engaged (e.g. after a host disable before the cancel takes effect, or within the 3 s heartbeat-mismatch window)
- **Local:** STEERING_LKA carries torque or STEER_REQUEST=1 while latActive is false

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-041.C1` Defect in the disengaged-output path; apply_torque is forced to 0 and the request bit follows lat_active only through carcontroller.py:83, 109-113 and common_fault_avoidance (lateral.py:174-195), with last_torque reset so re-engagement ramps from 0 | • Upstream review; ruff and ty; simple explicit gating. No requirement-based test; opendbc test_models checks TX frames pass the panda only for a default, cancel and resume CarControl (test_models.py:284-321) and is not run by LionDriver CI <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | • openpilot test_car_interfaces runs CarController.apply with random CarControl but asserts nothing about the output; process_replay covers card on the Corolla segment against refs from the same code <sub>openpilot/selfdrive/car/tests/test_car_interfaces.py; .github/workflows/tests.yaml</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-043 |

Safety mechanisms: Panda blocks non-zero torque and the request bit while controls are not allowed (SWF-002) · Host cancels PCM cruise when not enabled (SWF-046 analysis), which removes controls-allowed in the panda

#### SWF-046 · ACC acceleration command differs from controlsd's request (higher, lower or faster changing) within the panda range

🔴 **H** · **S 10** · guideword *value_high* · function `SWF-FN-045` Apply torque magnitude, rate and measured-torque limits; send zero torque with the request bit cleared when lateral control is not active; send the ACC command within the acceleration range

Effects:

- **End:** Unintended acceleration (HZ-005, S 10)
- **End:** Unintended or excessive deceleration (HZ-006, S 10)
- **Next higher:** Acceleration or braking stronger than planned, with the jerk limit bypassed by the terms added after it
- **Local:** ACCEL_CMD = request + up to ±1.5 m/s² pitch compensation + CarController PID, clipped to [-3.5, +2.0]

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-046.C1` The 4 m/s³ windup/winddown limit is applied before the pitch compensation and the PID (carcontroller.py:197-238), so the sent command has no rate limit; pitch comes from CC.orientationNED, which controlsd fills from deviceMotion with no validity check (controlsd.py:69-71, 157-159) | • Pitch compensation clipped to ±1.5 m/s² and high-pass filtered; final clip to the panda range (carcontroller.py:231-232, 250). No margin below the envelope (TSR-605 partial) <sub>opendbc_repo/opendbc/car/toyota/carcontroller.py</sub> | • process_replay covers card on the Corolla segment; not designed for implausible pitch or step requests <sub>openpilot/selfdrive/test/process_replay/test_processes.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-045 |
| `SWF-046.C2` controlsd passes aTarget through unchanged up to the panda limits (LongControl is feed-forward for Toyota, ki=kp=0, interfaces.py:212-214; limits = ACCEL_MIN/MAX, toyota/interface.py:21-22), so the host adds no margin or jerk bound of its own | • Planner jerk and accel limits only; TSR-605 margin not implemented <sub>openpilot/selfdrive/controls/lib/longitudinal_planner.py</sub> | • test_longcontrol.py covers state transitions, not limits <sub>openpilot/selfdrive/controls/tests/test_longcontrol.py</sub> | 7 | 10 | 🔴 **H** | SWF-ACT-045 |

Safety mechanisms: Panda acceleration range check [-3.5, +2.0] (SWF-003); no jerk check in the panda (SWF-004) · PCM limits requested acceleration (AOU-05, unverified); selfdrived ExcessiveActuationCheck soft-disable

#### SWF-052 · Negative acceleration sent in ACC_CONTROL while longitudinal control is not active

🔴 **H** · **S 10** · guideword *commission* · function `SWF-FN-050` Send the inactive acceleration in ACC_CONTROL whenever longitudinal control is not active

Effects:

- **End:** Braking while not engaged (HE-04.4) (HZ-006, S 10)
- **Next higher:** The panda refuses it while controls are not allowed (SWF-FN-003); with a false authority (SWF-006, SWF-007, SWF-013) the PCM brakes
- **Local:** 0x343 ACCEL_CMD below 0 while CC.longActive is false

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-052.C1` The Toyota CarController takes pcm_accel_cmd from actuators.accel with no longActive gate (carcontroller.py:197-250); the inactive value relies on LongControl returning 0 in its off state (longcontrol.py:56-58), so a defect or stale carControl upstream passes through | • Upstream review, ruff and ty in CI; no requirement for the inactive value on the host <sub>opendbc_repo/opendbc/car/toyota/carcontroller.py</sub> | • process_replay covers card on the Corolla segment; not designed for a non-zero request while not engaged <sub>openpilot/selfdrive/test/process_replay/test_processes.py</sub> | 6 | 9 | 🔴 **H** | SWF-ACT-052 |

Safety mechanisms: Panda refuses any acceleration other than the inactive value while controls are not allowed (longitudinal_accel_checks)

<sub>Note: WP-A-04 BE-4.13 (SG-04 G4.6).</sub>

### `SWF-SE-046` card actuation hand-off

#### SWF-047 · Control step late, repeated or missing, or item frames dropped, while engaged

🔴 **H** · **S 10** · guideword *late* · function `SWF-FN-047` Deliver every 10 ms control step to the vehicle, and stop sending item frames when carControl is no longer received

Effects:

- **End:** Abrupt loss of steering assist in a curve; the soft-disable alert comes at the same time, not before (HZ-004, S 10)
- **Next higher:** Stale torque target applied for up to 10 frames, then STEERING_LKA/ACC_CONTROL stop and the EPS/PCM time out
- **Local:** card reuses the last carControl for up to 0.1 s, then sends no item frames; or the panda blocks frames the host believes sent

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SWF-047.C1` controlsd raises on input it does not guard, e.g. int(NaN) when lateralDelay is not finite (latcontrol_torque.py:100), and exits; the 100 Hz loop has no exception handling (controlsd.py:227-233) | • Upstream review, ruff, ty; excluded from fuzzing (test_fuzzy.py:13) | • No test injects non-finite lateralDelay | 6 | 10 | 🔴 **H** | SWF-ACT-041, SWF-ACT-044 |
| `SWF-047.C2` Loop overrun or scheduling delay (Python, CTRL_HIGH on core 4, controlsd.py:237); Ratekeeper only monitors (228-233) and the loop is paced by selfdriveState; card actuates the latest carControl each CAN cycle as long as it is alive within 10 periods (card.py:234; cereal/messaging/__init__.py:265) | • Real-time priority and core pinning; upstream CPU budget (test_onroad.py:46, 16 % for controlsd) <sub>openpilot/selfdrive/test/test_onroad.py</sub> | • test_onroad test_timings checks carControl/controlsState period (max/min and RSD); targeted at this cause but needs device hardware (Jenkinsfile:265) and is not run by LionDriver CI <sub>openpilot/selfdrive/test/test_onroad.py</sub> | 6 | 8 | 🔴 **H** | SWF-ACT-048 |
| `SWF-047.C3` CarController torque limits equal the panda limits (values.py:20-21, 46-47 vs safety/modes/toyota.h:269-274), so any rounding or future change of one side (SWF-ACT-003) makes the panda block frames; the host never reads pandaState.safetyTxBlocked (published at pandad.cc:112, no consumer), so blocked frames show only as EPS LKA time-outs | • Constants copied from the same source; no consistency check between host and panda limits <sub>opendbc_repo/opendbc/car/toyota/values.py</sub> | • opendbc test_models::test_panda_safety_tx_cases sends only inactive, cancel and resume CarControl through the panda model and is not run in LionDriver CI <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 5 | 10 | 🔴 **H** | SWF-ACT-043, SWF-ACT-044 |

Safety mechanisms: card stops actuating 0.1 s after carControl stops (card.py:234); selfdrived commIssue/processNotRunning soft-disable alert; EPS LKA message time-out (vehicle) · Per-ID TX rate supervision exists only in the reference build (opendbc#10, panda#13) and is not credited at BL-004

## 5. Actions

| ID | Kind | Action | Owner | Status | Causes | Revised S/O/D → AP |
|---|---|---|---|---|---|---|
| SWF-ACT-001 | detection | Run the opendbc safety suite and the mutation tests as a blocking gate in LionDriver CI for every change and submodule bump | Jherrod Thomas | completed | — | 10/5/3 → 🔴 **H** |
| SWF-ACT-002 | prevention | Requirements-based tests for the panda safety model, traced to the draft TSRs and SWSRs (assurance WP-S-02, WP-W-02); the requirements exist as drafts, the tests do not | Jherrod Thomas | open | SWF-001.C2, SWF-002.C1, SWF-003.C2, SWF-007.C1, SWF-008.C2, SWF-009.C1, SWF-010.C1, SWF-011.C1, SWF-012.C1, SWF-017.C1 | 10/3/3 → 🟢 L |
| SWF-ACT-003 | design_change | Derive steering and acceleration envelopes from vehicle measurements (FSC FOI-001, DFA DM-10) and set panda limits from them, independently of the SoC limits | Jherrod Thomas | open | SWF-001.C1, SWF-003.C1, SWF-003.C3 | — |
| SWF-ACT-004 | design_change | Implement the panda configuration lock (LD-DES-001 DR-01..DR-07, DR-05 for ELM327) | Jherrod Thomas | in_progress | SWF-013.C1 | — |
| SWF-ACT-005 | design_change | Add an acceleration-rate (jerk) check to the panda longitudinal checks, or justify the absence with characterized powertrain rate limits (OI-002) | Jherrod Thomas | open | SWF-004.C1 | — |
| SWF-ACT-006 | detection | Verify on the vehicle that the PCM cancels cruise on brake (FSC FOI-006) so PCM_CRUISE can be credited as the diverse brake path; add a safety test for brake-without-cruise-cancel | Jherrod Thomas | open | SWF-005.C1 | — |
| SWF-ACT-007 | design_change | Derive RX-lag and heartbeat timeouts from the FTTI and check them at 8 Hz or faster while controls are allowed (LD-DES-001 DR-20) | Jherrod Thomas | in_progress | SWF-006.C1, SWF-014.C1, SWF-014.C2 | — |
| SWF-ACT-008 | detection | Add a unit or static check that every host TX path calls can_send with skip_tx_hook=false | Jherrod Thomas | open | SWF-016.C1 | — |
| SWF-ACT-009 | design_change | Make LIONDRIVER_REFERENCE=1 (with RELEASE=1) the only firmware build used for the reference configuration: set it in openpilot's panda build and the release procedure, and have the host check it (e.g. a version or health flag) before engaging | Jherrod Thomas | open | SWF-001.C3, SWF-008.C1, SWF-013.C2 | — |
| SWF-ACT-010 | design_change | Restrict ELM327 TX to the UDS services fingerprinting and radar disable need, and refuse it above standstill (WP-W-04 OI-6) | Jherrod Thomas | open | SWF-015.C1 | — |
| SWF-ACT-011 | detection | Confirm the LSI range from the STM32H725 datasheet and run the watchdog HIL test (test_10_hw_watchdog) on the bench, including a long soak for spurious resets (D-04) | Jherrod Thomas | open | SWF-018.C1, SWF-019.C1 | — |
| SWF-ACT-020 | design_change | Bind the heartbeat to the command path. Send engaged=1 only while selfdriveState is enabled and the forwarding thread has sent a sendcan batch less than 0.1 s ago, or add a sequence or age field the panda checks (TSR-409, TSR-602). Coordinate with SWF-ACT-007 (panda engaged-mismatch at 0.3 s) | Jherrod Thomas | open | SWF-020.C1 | — |
| SWF-ACT-021 | design_change | Make link failure bounded and visible. Send the heartbeat independently of the health read. Give control transfers a finite timeout and bound the fail-recovery loop. Clear connected and exit on a persistent failure. Do not reset or DFU-recover the internal panda from pandad.py while onroad unless needed. In selfdrived (EL-04), raise the controlsAllowed-mismatch alert within 0.1-0.2 s instead of 200 frames | Jherrod Thomas | open | SWF-021.C1, SWF-021.C2, SWF-027.C1, SWF-027.C2 | — |
| SWF-ACT-022 | design_change | Host allow-list for the reference configuration (TOYOTA, param 73, alternative experience 0) before 0xdc/0xdf. Read back the mode, param and alternative experience from health, and set safety_configured_ only on a match. Retry or refuse ControlsReady on a mismatch | Jherrod Thomas | open | SWF-022.C1, SWF-022.C2 | — |
| SWF-ACT-023 | design_change | Derive the sendcan maximum age from the FTTI and the control period (e.g. 0.1 s). Compare it in one clock domain (stamp with CLOCK_BOOTTIME, or compare with CLOCK_MONOTONIC). After a stall, keep only the newest frame per address instead of replaying the backlog. Decide whether events with valid=false are forwarded | Jherrod Thomas | open | SWF-023.C1, SWF-024.C1 | — |
| SWF-ACT-024 | detection | Add host unit tests for the pandad logic, run in CI (unit_tests via test_native.py): the sendcan age gate including the clock domain, the heartbeat engaged derivation, the fault-bit mapping, and the safety setter sequence and readback, using a fake Panda. Show they fail on mutated gates so D can be rated as proven | Jherrod Thomas | open | SWF-023.C1, SWF-024.C1, SWF-025.C1 | — |
| SWF-ACT-025 | design_change | Fix the faults mapping. Size the list from the mapped bits only, log unknown bits, and add the panda bit 27 (interruptRateSoundDma) to cereal FaultType (log.capnp, pandad.cc:257-268) | Jherrod Thomas | completed | SWF-025.C1 | 8/5/4 → 🟠 M |
| SWF-ACT-026 | design_change | Report frames that pandad drops (age gate, failed bulk write) in pandaStates or a pandad event, and have selfdrived disable with an alert while engaged (closes System FMEA SFM-005.C2 and SFM-011.C2 on the host side) | Jherrod Thomas | open | SWF-024.C1, SWF-024.C2 | — |
| SWF-ACT-027 | design_change | Replace the XOR checksums on the SPI link with a CRC (host spi.cc and panda firmware), or justify XOR with a residual-error analysis that uses the measured SPI error rate (spi_error_count) and the Toyota message checksum as a diverse check | Jherrod Thomas | open | SWF-026.C1 | — |
| SWF-ACT-028 | design_change | Build and flash only the LIONDRIVER_REFERENCE firmware for the reference configuration, and have pandad check a reference-build flag or version before setting a car mode (with SWF-ACT-009). Compile out BOARDD_SKIP_FW_CHECK, STARTED, FAKESEND, SPI_ERR_PROB and BOARDD_LOOPBACK in release builds | Jherrod Thomas | open | SWF-022.C1, SWF-028.C1, SWF-028.C2 | — |
| SWF-ACT-029 | detection | Run the pandad hardware tests (test_pandad.py, test_pandad_spi.py, test_pandad_loopback.py) on a comma 3X before release. While engaged on a bench, inject: stopping selfdrived, controlsd and card; killing or hanging pandad; SPI errors; and a panda reset. Measure the time to no output and to the SoC alert (FSR-007 verification, D-04) | Jherrod Thomas | open | SWF-020.C1, SWF-021.C1, SWF-021.C2, SWF-024.C2, SWF-027.C1, SWF-027.C2, SWF-029.C1, SWF-029.C2 | — |
| SWF-ACT-030 | prevention | Requirements-based tests for selfdrived traced to FSR-030/033/034/036 and TSR-601/606/617/621: state machine, data_sample/update_events with synthetic carState, pandaStates and SubMaster faults (brake, cancel, stale or missing services, panda mismatch), helpers.py and alert priority; prove them with a mutation run on state.py, selfdrived.py and helpers.py | Jherrod Thomas | open | SWF-030.C1, SWF-031.C2 | 10/5/4 → 🔴 **H** |
| SWF-ACT-031 | design_change | Reference-configuration guard: refuse engagement (permanent NO_ENTRY) when REPLAY, SIMULATION or TESTING_CLOSET is set or the big-model (chestnut) path is active, and exclude that path from reference builds (TSR-603, TSR-613) | Jherrod Thomas | open | SWF-030.C2, SWF-032.C2 | — |
| SWF-ACT-032 | design_change | Supervise carState freshness in selfdrived (age of the last message, at most 2 periods) and raise an immediate disable when it is stale, instead of reusing the previous carState | Jherrod Thomas | open | SWF-031.C1 | — |
| SWF-ACT-033 | design_change | Panda status supervision per TSR-615, TSR-621 and TSR-626a: controlsMismatch within 2 samples and 0.5 s (time-based); safety model/parameter mismatch as NO_ENTRY from start instead of a 10 s grace; pandaStates older than 0.2 s treated as mismatch; immediate disable on heartbeatLost, rising safetyTxBlocked, txRateExceeded and any panda fault flag | Jherrod Thomas | in_progress | SWF-032.C1, SWF-034.C1, SWF-034.C2, SWF-034.C3 | — |
| SWF-ACT-034 | design_change | Give cruiseMismatch a warning and an ACC cancel retry within 1 s (TSR-308, GAP-19) | Jherrod Thomas | completed | SWF-039.C1 | — |
| SWF-ACT-035 | design_change | Classify reactions per TSR-601 (immediate disable for loss or staleness of a control-law input) and justify each remaining SOFT_DISABLE against the FTTI (SFM-016, GAP-16); make soft-disable and mismatch timers time-based (monotonic clock); move blocking Params writes out of the 100 Hz loop | Jherrod Thomas | open | SWF-033.C1, SWF-033.C2 | — |
| SWF-ACT-036 | design_change | Rank soft and immediate disable takeover alerts above every WARNING and PERMANENT alert except FCW, keep the takeover sound when an AEB alert is shown, name the fault class in the text (canError, TSR-606), and add a test of the ordering | Jherrod Thomas | open | SWF-035.C1 | — |
| SWF-ACT-037 | design_change | selfdrived liveness: ui and soundd raise the critical takeover alert within 0.5 s of missing selfdriveState while engaged (EL-05 change, TSR-622); add a process watchdog for selfdrived; remove selfdrived from the fuzz NOT_TESTED list | Jherrod Thomas | open | SWF-036.C1, SWF-036.C2 | — |
| SWF-ACT-038 | design_change | Revisit TSR-617: set excessive-actuation thresholds from the vehicle envelope and fork drive logs, bound the device_motion_valid reset, check longitudinal response during override, and add unit tests for helpers.py | Jherrod Thomas | open | SWF-037.C1, SWF-037.C2 | — |
| SWF-ACT-039 | design_change | Resolve FSR-033 against the implementation: either revise FSR-033 to the actual yield strategy (integrator freeze, panda bound, override force verified by the FSR-031 vehicle test) or ramp the torque request down while steeringPressed | Jherrod Thomas | open | SWF-038.C1 | — |
| SWF-ACT-040 | design_change | Implement TSR-602 in controlsd: check age and valid of selfdriveState, carState, modelV2, longitudinalPlan, vehicleParameters and deviceMotion before use (≤ 2 periods); set latActive/longActive false and raise an immediate-disable event when stale; derive carControl.valid from these checks and have card stop actuating on carControl.valid false; give cruiseMismatch a disable type | Jherrod Thomas | in_progress | SWF-040.C1, SWF-042.C3, SWF-043.C1, SWF-043.C2, SWF-048.C1 | 10/3/4 → 🟢 L |
| SWF-ACT-041 | design_change | Implement TSR-604: treat any non-finite input or actuator value as a fault (immediate disable with alert), reset desired_curvature and both controllers' state, and guard lateralDelay before the int() conversion | Jherrod Thomas | in_progress | SWF-045.C1, SWF-045.C2, SWF-047.C1 | 10/3/4 → 🟢 L |
| SWF-ACT-042 | design_change | Reset the LatControlTorque PID (and LatControlPID) in reset(), or record why upstream carries the integrator over engagements; check against current upstream openpilot | Jherrod Thomas | open | SWF-042.C1 | — |
| SWF-ACT-043 | detection | Requirements-based unit tests for controlsd and the Toyota CarController (latActive/longActive gating table per FSR-006, zero torque and request bit off when not active, controller reset across disengagement, cancel on every disengagement path, active-torque frames accepted by the panda model at the limits), run in LionDriver CI and proven by mutation | Jherrod Thomas | open | SWF-041.C1, SWF-042.C1, SWF-047.C3 | — |
| SWF-ACT-044 | detection | Add NaN/inf and stale-input injection for controlsd and card (enable them in test_fuzzy.py with the Corolla fingerprint, or a dedicated test), and run the opendbc car tests (test_models, test_car_interfaces, test_lateral_limits) for Toyota in LionDriver CI | Jherrod Thomas | open | SWF-045.C1, SWF-045.C2, SWF-047.C1, SWF-047.C3 | — |
| SWF-ACT-045 | design_change | Implement TSR-605 margins on the host: bound latAccelOffset and torque parameters in controlsd, apply the acceleration rate limit after pitch compensation and the CarController PID, gate pitch compensation on a valid calibrated pose, and keep host torque/accel limits below the panda limits | Jherrod Thomas | open | SWF-042.C2, SWF-042.C3, SWF-046.C1, SWF-046.C2 | — |
| SWF-ACT-046 | design_change | SoC counterpart of TSR-304 (STPA OI-2, FSR-033) - ramp commanded torque toward zero while steeringPressed, or leave latActive during a lateral override, with the override threshold taken from WP-C-08 | Jherrod Thomas | open | SWF-044.C1 | — |
| SWF-ACT-047 | design_change | Implement TSR-613: remove the lateralManeuverPlan subscription and the maneuver/joystick processes from the reference build | Jherrod Thomas | open | SWF-040.C1, SWF-049.C1 | — |
| SWF-ACT-048 | detection | Bench or HIL fault injection (WP-V-05) - stop or stall selfdrived, modeld, plannerd and controlsd while engaged and measure time to zero torque/acceleration and to the alert; run test_onroad timing tests on a comma 3X for each release | Jherrod Thomas | open | SWF-043.C1, SWF-047.C2 | — |
| SWF-ACT-049 | detection | Vehicle test of PCM cancel and cluster state on each host disengagement path (fault disable, cancel button, brake, selfdrived loss) | Jherrod Thomas | open | SWF-048.C1 | — |
| SWF-ACT-050 | design_change | Implement TSR-624: announce deceleration that traffic does not require at least 1 s before its onset, and ramp it within a_min and j_down | Jherrod Thomas | open | SWF-050.C1 | — |
| SWF-ACT-051 | design_change | Implement TSR-625: gate FCW on fresh and valid modelV2 and longitudinalPlan, with a unit test for a stale and an invalid input | Jherrod Thomas | open | SWF-051.C1 | — |
| SWF-ACT-052 | design_change | Send the inactive acceleration from the Toyota CarController whenever CC.longActive is false, with a unit test | Jherrod Thomas | open | SWF-052.C1 | — |
| SWF-ACT-053 | detection | Vehicle test of the PCM response when the inactive value replaces an active deceleration (TSR-208, AOU-05R); if the PCM steps, specify an item-side ramp after revocation (FSR-04.03) | Jherrod Thomas | open | SWF-053.C1 | — |

## 6. Priority H causes without a completed action

| Cause | Failure mode | S/O/D | Open actions |
|---|---|---|---|
| `SWF-001.C1` | Steering request above the torque or torque-rate limit for the vehicle is passed | 10/6/9 | SWF-ACT-003 |
| `SWF-001.C2` | Steering request above the torque or torque-rate limit for the vehicle is passed | 10/5/3 | SWF-ACT-002 |
| `SWF-002.C1` | Steering torque passed while controls are not allowed | 10/5/3 | SWF-ACT-002 |
| `SWF-003.C1` | Acceleration request outside the intended envelope is passed | 10/6/9 | SWF-ACT-003 |
| `SWF-003.C2` | Acceleration request outside the intended envelope is passed | 10/5/3 | SWF-ACT-002 |
| `SWF-003.C3` | Acceleration request outside the intended envelope is passed | 10/6/9 | SWF-ACT-003 |
| `SWF-004.C1` | Step change of deceleration request to the minimum is passed | 10/8/9 | SWF-ACT-005 |
| `SWF-005.C1` | Corrupted brake-pressed value accepted | 10/3/9 | SWF-ACT-006 |
| `SWF-006.C1` | Stale brake, cruise or EPS data used beyond the detection budget | 10/4/3 | SWF-ACT-007 |
| `SWF-007.C1` | Controls allowed without a driver engagement | 10/5/3 | SWF-ACT-002 |
| `SWF-008.C2` | Controls not withdrawn on brake press | 10/5/3 | SWF-ACT-002 |
| `SWF-009.C1` | Controls not withdrawn when PCM cruise disengages | 10/5/3 | SWF-ACT-002 |
| `SWF-010.C1` | Stock camera steering or ACC messages forwarded while the item transmits | 10/5/3 | SWF-ACT-002 |
| `SWF-011.C1` | Stock pre-collision (AEB) messages blocked | 10/5/3 | SWF-ACT-002 |
| `SWF-012.C1` | Relay malfunction not detected | 10/5/3 | SWF-ACT-002 |
| `SWF-013.C2` | Wrong or permissive safety mode accepted from the host | 10/8/9 | SWF-ACT-009 |
| `SWF-014.C2` | Controls withdrawn later than the FTTI after host loss | 10/8/8 | SWF-ACT-007 |
| `SWF-015.C1` | Diagnostic (ELM327) mode accepted while driving | 10/5/9 | SWF-ACT-010 |
| `SWF-016.C1` | Host transmission bypasses the safety check | 10/3/8 | SWF-ACT-008 |
| `SWF-017.C1` | Item deceleration passed while the driver presses the accelerator | 10/5/3 | SWF-ACT-002 |
| `SWF-018.C1` | Safety checks stop running while the relay is driven | 10/4/7 | SWF-ACT-011 |
| `SWF-019.C1` | Spurious MCU reset while engaged | 10/5/8 | SWF-ACT-011 |
| `SWF-020.C1` | Heartbeat reports engaged while no fresh command reaches the panda | 10/8/10 | SWF-ACT-020, SWF-ACT-029 |
| `SWF-021.C1` | Heartbeat gap longer than the 0.3 s panda budget while engaged | 10/7/9 | SWF-ACT-021, SWF-ACT-029 |
| `SWF-021.C2` | Heartbeat gap longer than the 0.3 s panda budget while engaged | 10/6/9 | SWF-ACT-021, SWF-ACT-029 |
| `SWF-022.C1` | Wrong safety model, parameter or alternative experience written to the panda | 10/7/10 | SWF-ACT-022, SWF-ACT-028 |
| `SWF-022.C2` | Wrong safety model, parameter or alternative experience written to the panda | 10/4/10 | SWF-ACT-022 |
| `SWF-023.C1` | Stale or burst-replayed sendcan frames forwarded to the panda | 10/8/10 | SWF-ACT-023, SWF-ACT-024 |
| `SWF-024.C1` | sendcan frames silently not forwarded while engaged | 10/5/10 | SWF-ACT-023, SWF-ACT-026, SWF-ACT-024 |
| `SWF-024.C2` | sendcan frames silently not forwarded while engaged | 10/6/9 | SWF-ACT-026, SWF-ACT-029 |
| `SWF-026.C1` | Corrupted command or vehicle data accepted across the SPI link | 10/4/9 | SWF-ACT-027 |
| `SWF-027.C1` | pandad hangs or restarts while engaged | 10/7/9 | SWF-ACT-021, SWF-ACT-029 |
| `SWF-027.C2` | pandad hangs or restarts while engaged | 10/6/9 | SWF-ACT-021, SWF-ACT-029 |
| `SWF-028.C1` | pandad runs against panda firmware that is not the assured reference build | 10/8/10 | SWF-ACT-028 |
| `SWF-028.C2` | pandad runs against panda firmware that is not the assured reference build | 10/2/10 | SWF-ACT-028 |
| `SWF-029.C1` | Item unavailable for the rest of the drive after a transient link error or a panda reset | 8/6/10 | SWF-ACT-029 |
| `SWF-029.C2` | Item unavailable for the rest of the drive after a transient link error or a panda reset | 8/6/10 | SWF-ACT-029 |
| `SWF-030.C1` | selfdrived enters an engaged state with a NO_ENTRY condition active or without an ENABLE event | 10/6/8 | SWF-ACT-030 |
| `SWF-030.C2` | selfdrived enters an engaged state with a NO_ENTRY condition active or without an ENABLE event | 10/2/10 | SWF-ACT-031 |
| `SWF-031.C1` | selfdrived does not disengage on driver brake or cancel | 10/6/10 | SWF-ACT-032 |
| `SWF-031.C2` | selfdrived does not disengage on driver brake or cancel | 10/7/8 | SWF-ACT-030 |
| `SWF-032.C1` | A detected or reportable fault leads to no disable reaction while engaged | 10/8/10 | SWF-ACT-033 |
| `SWF-032.C2` | A detected or reportable fault leads to no disable reaction while engaged | 10/4/10 | SWF-ACT-031 |
| `SWF-033.C1` | Disengagement later than the fault tolerance time | 10/8/9 | SWF-ACT-035 |
| `SWF-033.C2` | Disengagement later than the fault tolerance time | 10/6/10 | SWF-ACT-035 |
| `SWF-034.C1` | Panda/host disagreement on safety mode or controls-allowed detected late or not at all | 10/8/10 | SWF-ACT-033 |
| `SWF-034.C2` | Panda/host disagreement on safety mode or controls-allowed detected late or not at all | 10/4/10 | SWF-ACT-033 |
| `SWF-034.C3` | Panda/host disagreement on safety mode or controls-allowed detected late or not at all | 10/6/10 | SWF-ACT-033 |
| `SWF-035.C1` | Takeover request masked by a lower-urgency alert | 10/6/9 | SWF-ACT-036 |
| `SWF-036.C1` | selfdrived stops publishing selfdriveState (crash or hang) while engaged | 10/7/9 | SWF-ACT-037 |
| `SWF-036.C2` | selfdrived stops publishing selfdriveState (crash or hang) while engaged | 10/5/10 | SWF-ACT-037 |
| `SWF-037.C1` | Excessive vehicle response while engaged not detected | 10/8/10 | SWF-ACT-038 |
| `SWF-037.C2` | Excessive vehicle response while engaged not detected | 10/6/10 | SWF-ACT-038 |
| `SWF-038.C1` | Lateral control keeps commanding torque while the driver steers | 10/8/9 | SWF-ACT-039 |
| `SWF-040.C1` | Actuation continues on a stale engagement state after selfdrived stops publishing | 10/7/10 | SWF-ACT-040, SWF-ACT-047 |
| `SWF-041.C1` | Non-zero steering torque or the steer request bit sent while lateral control is not active | 10/6/9 | SWF-ACT-043 |
| `SWF-042.C1` | Steering torque request too high, biased or overshooting within the CarController and panda limits | 10/7/10 | SWF-ACT-042, SWF-ACT-043 |
| `SWF-042.C2` | Steering torque request too high, biased or overshooting within the CarController and panda limits | 10/6/9 | SWF-ACT-045 |
| `SWF-042.C3` | Steering torque request too high, biased or overshooting within the CarController and panda limits | 10/6/9 | SWF-ACT-040, SWF-ACT-045 |
| `SWF-043.C1` | Lateral and longitudinal commands computed from stale or frozen model and planner outputs | 10/7/10 | SWF-ACT-040, SWF-ACT-048 |
| `SWF-043.C2` | Lateral and longitudinal commands computed from stale or frozen model and planner outputs | 10/7/10 | SWF-ACT-040 |
| `SWF-044.C1` | Steering torque kept up while the driver steers against the item | 10/7/10 | SWF-ACT-046 |
| `SWF-045.C1` | A non-finite input latches the controller state and silently zeroes lateral (or longitudinal) output while engaged | 10/6/10 | SWF-ACT-041, SWF-ACT-044 |
| `SWF-045.C2` | A non-finite input latches the controller state and silently zeroes lateral (or longitudinal) output while engaged | 10/6/10 | SWF-ACT-041, SWF-ACT-044 |
| `SWF-046.C1` | ACC acceleration command differs from controlsd's request (higher, lower or faster changing) within the panda range | 10/6/9 | SWF-ACT-045 |
| `SWF-046.C2` | ACC acceleration command differs from controlsd's request (higher, lower or faster changing) within the panda range | 10/7/10 | SWF-ACT-045 |
| `SWF-047.C1` | Control step late, repeated or missing, or item frames dropped, while engaged | 10/6/10 | SWF-ACT-041, SWF-ACT-044 |
| `SWF-047.C2` | Control step late, repeated or missing, or item frames dropped, while engaged | 10/6/8 | SWF-ACT-048 |
| `SWF-047.C3` | Control step late, repeated or missing, or item frames dropped, while engaged | 10/5/10 | SWF-ACT-043, SWF-ACT-044 |
| `SWF-048.C1` | PCM cruise cancel not requested, or not effective, when the item is not enabled | 10/6/9 | SWF-ACT-040, SWF-ACT-049 |
| `SWF-049.C1` | Desired curvature taken from the developer lateral-maneuver plan instead of the driving model | 10/7/10 | SWF-ACT-047 |
| `SWF-050.C1` | Item-initiated deceleration starts without a prior announcement | 10/8/10 | SWF-ACT-050 |
| `SWF-051.C1` | Forward collision warning raised from stale or invalid model or planner input | 10/7/10 | SWF-ACT-051 |
| `SWF-052.C1` | Negative acceleration sent in ACC_CONTROL while longitudinal control is not active | 10/6/9 | SWF-ACT-052 |
| `SWF-053.C1` | Active deceleration request ends in one step when authority is revoked | 10/8/9 | SWF-ACT-053 |
