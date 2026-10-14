# System FMEA review: LionDriver L2 ACC/ALC item

> Generated from [`analyses/system-fmea.yaml`](../../analyses/system-fmea.yaml) and [`diagrams/system-fmea.yaml`](../../diagrams/system-fmea.yaml) by `tools/safety/fmea_review_md.py`. Edit the YAML and regenerate; never edit this page. A styled workbook of the same data is [`system-fmea-review.xlsx`](system-fmea-review.xlsx).

| Revision | Status | Baseline | Rating tables | Updated |
|---|---|---|---|---|
| 0.6 | draft | BL-004 | RT-1 | 2026-10-13 |

**Scope.** LionDriver as installed on a 2020 Toyota Corolla LE (US) with comma 3X and integrated panda, software BL-004 (structure and failure analysis written at BL-001, risk analysis at BL-004), while the vehicle is driven on public roads by a licensed driver. Functions F1-F7 per fmea-plan.md section 3.1, plus F8 (stock vehicle safety functions are preserved), added because the harness intercepts the stock ADAS camera.

**Team.** Jherrod Thomas (Project maintainer, safety lead (reviewer/approver)); Claude (AI assistant) (Drafting assistance; content requires human review)

![Summary](figures/system-fmea-summary.svg)

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

![LionDriver item boundary, 2020 Corolla LE](figures/system-fmea-block.svg)

**Interface matrix.** Each line in the diagram, with what crosses it.

| ID | From | To | Type | What crosses | Source |
|---|---|---|---|---|---|
| I01 | Road environment | Perception + planning | data | Road camera images | <sub>assurance/02-concept/WP-C-01-item-definition.md §3.4 IF-05</sub> |
| I02 | Driver | Supervision + DM | data | Driver camera (IR) | <sub>assurance/02-concept/WP-C-01-item-definition.md §3.4 IF-06</sub> |
| I03 | Toyota forward radar | Panda safety model | data | Radar tracks 0x180-0x19F | <sub>assurance/02-concept/WP-C-01-item-definition.md §3.4 IF-02</sub> |
| I04 | Perception + planning | Control | data | modelV2 + long. plan | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §9</sub> |
| I05 | Control | Car interface + pandad | data | carControl 100 Hz | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §9</sub> |
| I06 | Car interface + pandad | Supervision + DM | data | carState, pandaStates | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §9</sub> |
| I07 | Supervision + DM | Control | data | selfdriveState, DM | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §9</sub> |
| I08 | Supervision + DM | HMI | data | Alerts, engaged state | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §3.3 IF-07</sub> |
| I09 | HMI | Driver | data | Display, sounds | <sub>assurance/02-concept/WP-C-01-item-definition.md §3.4 IF-07</sub> |
| I10 | Car interface + pandad | Panda safety model | data ⇄  | SPI: CAN, 0xf3 heartbeat | <sub>assurance/03-system/WP-S-05-hsi-specification.md §2 HSI-01..03, §11.2 S-16..S-21</sub> |
| I11 | Panda safety model | Toyota EPS | data | 0x2E4 STEERING_LKA | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-01, S-02</sub> |
| I12 | Toyota EPS | Panda safety model | data | 0x260 torque, 0x262 EPS | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-07, S-08, S-12</sub> |
| I13 | Panda safety model | Powertrain + brake (ACC) | data | 0x343 ACC_CONTROL | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-03, S-04</sub> |
| I14 | Powertrain + brake (ACC) | Panda safety model | data | 0x1D2/0x226/0xAA status | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-06, S-09..S-11</sub> |
| I15 | Stock ADAS camera (TSS2) | Panda safety model | data | Bus 2 fwd (PCS 0x283) | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-15; WP-C-01 §3.4 IF-03</sub> |
| I16 | Panda safety model | Vehicle CAN + 12 V | data | 0x412 LKAS_HUD cluster | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-05</sub> |
| I17 | Panda safety model | Harness + relay | data | Relay drive GPIO | <sub>assurance/03-system/WP-S-05-hsi-specification.md §6, §11.3 S-22</sub> |
| I18 | Harness + relay | Vehicle CAN + 12 V | physical ⇄  | CAN intercept bus 0/2 | <sub>assurance/03-system/WP-S-05-hsi-specification.md §5</sub> |
| I19 | Vehicle CAN + 12 V | Harness + relay | energy | 12 V + ignition line | <sub>assurance/02-concept/WP-C-01-item-definition.md §3.4 IF-08; WP-S-05 §11.3 S-24</sub> |
| I20 | Panda safety model | Driver | data | Panda siren (SM-23) | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.3 S-27; WP-S-02 TSR-516</sub> |
| I21 | Driver | Toyota EPS | physical | Steering wheel torque | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §2 AP-6</sub> |
| I22 | Driver | Powertrain + brake (ACC) | physical | Brake, gas, cruise stalk | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §2 AP-6; WP-C-01 §3.2</sub> |

## 2. P-diagram

![L2 ACC + ALC on the Corolla, highway ODD](figures/system-fmea-p-diagram.svg)

| Function covered | Description |
|---|---|
| `SFM-FN-001` | F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged |
| `SFM-FN-002` | F2 Longitudinal control: request acceleration/deceleration to hold set speed and follow leads while engaged |
| `SFM-FN-003` | F3 Engagement management: engage only on driver request with entry conditions met; disengage per fault reaction (soft/immediate) |
| `SFM-FN-004` | F4 Driver override: release control on brake or cancel; yield lateral to steering input and longitudinal to accelerator |
| `SFM-FN-005` | F5 Driver monitoring: detect inattention and escalate alerts; lock out engagement after repeated non-response |
| `SFM-FN-007` | F7 Actuation limiting: bound actuator commands in magnitude and rate; detect excessive actuation |

| Control factor | Source |
|---|---|
| Torque 1500 raw, rate +15/-25 per frame | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-02; WP-S-02 TSR-101..104</sub> |
| Accel bounds -3.5..+2.0 m/s² in envelope | <sub>assurance/03-system/WP-S-05-hsi-specification.md §11.1 S-03; WP-S-02 TSR-201</sub> |
| Authority on PCM cruise edge + heartbeat | <sub>assurance/03-system/WP-S-02-technical-safety-requirements.md TSR-301; WP-S-03 §6 SM-04, SM-29</sub> |
| DM escalation 5/8/13 s, decel, lockout | <sub>assurance/02-concept/WP-C-08-driver-hmi-misuse-analysis.md §5.1; WP-S-02 TSR-608</sub> |
| Chill mode by default (Experimental off) | <sub>assurance/01-management/WP-M-07-risk-management.md D-08; WP-C-07 FM-01</sub> |
| Fail-silent fault reaction + panda siren | <sub>assurance/03-system/WP-S-03-technical-safety-concept-architecture.md §2 AP-2; WP-S-02 TSR-516</sub> |

## 3. Structure and functions

![Structure tree](../../figures/generated/fig-3-1-sfm-structure.svg)

The failure chains (element → function → failure mode → causes) are drawn in [figures/generated](../../figures/generated/README.md).

| Element | Kind | Functions |
|---|---|---|
| `SFM-SE-001` LionDriver item (L2 ACC + ALC + driver monitoring) | item | `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged<br>`SFM-FN-002` F2 Longitudinal control: request acceleration/deceleration to hold set speed and follow leads while engaged<br>`SFM-FN-003` F3 Engagement management: engage only on driver request with entry conditions met; disengage per fault reaction (soft/immediate)<br>`SFM-FN-004` F4 Driver override: release control on brake or cancel; yield lateral to steering input and longitudinal to accelerator<br>`SFM-FN-005` F5 Driver monitoring: detect inattention and escalate alerts; lock out engagement after repeated non-response<br>`SFM-FN-006` F6 Alerting: inform the driver of engagement state, takeover requests and faults (visual and audible)<br>`SFM-FN-007` F7 Actuation limiting: bound actuator commands in magnitude and rate; detect excessive actuation<br>`SFM-FN-008` F8 Stock function preservation: keep stock vehicle safety functions not replaced by the item available |
| &nbsp;&nbsp;&nbsp;`SFM-SE-002` comma 3X device | system | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-003` Integrated panda (CAN interface and safety model) | subsystem | — |
| &nbsp;&nbsp;&nbsp;`SFM-SE-004` Harness (Toyota A connector, harness box, comma power v3) | component | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-010` Perception (camerad, modeld) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-011` Localization and calibration (locationd, calibrationd, paramsd, torqued) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-012` Planning (plannerd, radard) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-013` Control (controlsd, lateral/longitudinal controllers) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-014` Supervision (selfdrived state machine, events, alert manager) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-015` Driver monitoring (dmonitoringmodeld, dmonitoringd) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-016` Car interface (card, car_events, opendbc Toyota port) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-017` Panda daemon (pandad) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-018` HMI (ui, soundd) | sw_element | — |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;`SFM-SE-019` Platform (manager, messaging, hardwared, OS) | sw_element | — |
| `SFM-SE-030` Toyota EPS | external | — |
| `SFM-SE-031` Toyota powertrain and brake control (receives ACC acceleration requests) | external | — |
| `SFM-SE-032` Toyota stock ADAS camera (TSS2) | external | — |
| `SFM-SE-033` Vehicle CAN buses and 12 V supply | external | — |
| `SFM-SE-034` Driver | external | — |

## 4. Worksheet

One table per failure mode, grouped by structure element. S is the failure mode's severity (its worst end effect); each cause has its own occurrence (O), detection (D) and action priority (AP).

### `SFM-SE-001` LionDriver item (L2 ACC + ALC + driver monitoring)

#### SFM-001 · Steering torque applied when not engaged

🔴 **H** · **S 10** · guideword *unintended* · function `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged

Effects:

- **End:** Driver surprised during manual driving; possible lane departure (HZ-001, S 10)
- **Next higher:** Unexpected steering wheel motion and lateral deviation
- **Local:** Torque request sent to EPS outside an active state

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-001.C1` State machine reports active while disabled | • Upstream code with review; ruff and ty run in fork CI static_analysis; unit tests derived from the implementation; no software requirements <sub>scripts/lint/lint.sh:45,55; .github/workflows/tests.yaml</sub> | • test_no_entry and test_no_entry_pre_enable (ENABLE with NO_ENTRY stays disabled), run by tests.yaml unit_tests on every push and PR; not proven by mutation <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 6 | 8 | 🔴 **H** | — |
| `SFM-001.C2` Panda allows steering TX without valid engagement (controls_allowed set incorrectly) | • Panda safety code: MISRA C:2012, 100% line coverage, review; rated in the SW FMEA <sub>assurance/08-analyses/fmea/analyses/sw-fmea.yaml</sub> | • opendbc safety suite with 100% line coverage and mutation tests, run by CI on every change (proven, early, test-to-fail) <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | — |
| `SFM-001.C3` Steering message packed with non-zero torque/request bit while latActive is false | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • process_replay over the CI route corpus compares outputs with the reference commit (CI 'process replay'); a regression check, not designed or proven for this cause <sub>openpilot/selfdrive/test/process_replay/test_processes.py</sub> | 6 | 9 | 🔴 **H** | — |

Safety mechanisms: controlsd only sets latActive when selfdriveState is active and no EPS fault · Panda safety model blocks steering messages unless controls are allowed (heartbeat carries engaged state from selfdriveState)

<sub>Note: HARA input: unintended steering intervention during manual driving.</sub>

#### SFM-002 · Steering torque or torque rate above limits

🔴 **H** · **S 10** · guideword *excessive* · function `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged

Effects:

- **End:** Lane departure or collision with adjacent traffic or roadside (HZ-002, S 10)
- **Next higher:** Lateral deviation faster than a driver can correct (> 1 m in 0.9 s)
- **Local:** Torque request exceeds the limits in SAFETY.md / ISO 11270

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-002.C1` Lateral controller output too high (gain, torque model, saturation logic) | • Upstream review and lint; LatControlCurvature does reset its PID (latcontrol_curvature.py:28-31), so the omission may be an oversight or deliberate upstream; no requirement states either <sub>openpilot/selfdrive/controls/lib/latcontrol_curvature.py</sub> | • test_latcontrol.py covers saturation only; test_latcontrol_torque_buffer.py covers the request buffer only; nothing checks controller state across disengagement | 7 | 10 | 🔴 **H** | SFM-ACT-001 |
| `SFM-002.C2` Model outputs excessive desired curvature | • Upstream neural network trained and validated by comma.ai; no development or validation evidence is available to LionDriver (SOTIF / ISO PAS 8800 scope, WP-C-06) <sub>openpilot/selfdrive/modeld</sub> | • No pre-release test targets this cause | 7 | 10 | 🔴 **H** | SFM-ACT-001, SFM-ACT-009 |
| `SFM-002.C3` Safety model torque/rate limits wrong for this vehicle or not enforced | • Panda limits are copied from upstream vehicle tuning (same constants as the SoC side); no independent envelope derived from vehicle measurements (FSC FOI-001) <sub>opendbc_repo/opendbc/safety/modes/toyota.h</sub><br>• Panda safety code: MISRA C:2012, 100% line coverage, review; rated in the SW FMEA <sub>assurance/08-analyses/fmea/analyses/sw-fmea.yaml</sub> | • opendbc safety suite with 100% line coverage and mutation tests, run by CI on every change (proven, early, test-to-fail) <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 6 | 9 | 🔴 **H** | SFM-ACT-001 |
| `SFM-002.C4` Wrong vehicle parameters (steer ratio, lateral accel factor, torque offsets) from online learners | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• paramsd bounds the learned steer ratio to 0.5-2x CarParams and rate-limits offsets; torqued accepts estimates only within sanity bounds of the CarParams values <sub>openpilot/selfdrive/locationd/paramsd.py:47</sub> | • paramsd and torqued unit tests (estimate bounds and convergence); targeted, not proven by fault injection <sub>openpilot/selfdrive/locationd/test/test_paramsd.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-001, SFM-ACT-002 |

Safety mechanisms: Panda/opendbc Toyota safety model limits steering torque magnitude and rate on TX · Excessive lateral acceleration check (> 2x ISO lateral accel for 0.25 s) raises excessiveActuation (SOFT_DISABLE)

<sub>Note: HARA input: excessive steering intervention while engaged.</sub>

#### SFM-003 · Steering in the wrong direction (away from lane center)

🔴 **H** · **S 10** · guideword *wrong_direction* · function `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged

Effects:

- **End:** Lane departure into oncoming/adjacent traffic or off road (HZ-003, S 10)
- **Next higher:** Vehicle steers toward lane boundary
- **Local:** Torque request sign opposite to the required correction

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-003.C1` Calibration (camera extrinsics) wrong or not converged | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• Engagement refused until calibration has converged; calibrationInvalid when out of bounds <sub>openpilot/selfdrive/locationd/calibrationd.py</sub> | • calibrationd unit tests (convergence, invalid calibration); targeted, not proven by fault injection <sub>openpilot/selfdrive/locationd/test/test_calibrationd.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |
| `SFM-003.C2` Sign convention error in steering signal parse or pack for this car | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |
| `SFM-003.C3` Model desired curvature has wrong sign (corrupted frame, wrong camera stream) | • Upstream neural network trained and validated by comma.ai; no development or validation evidence is available to LionDriver (SOTIF / ISO PAS 8800 scope, WP-C-06) <sub>openpilot/selfdrive/modeld</sub><br>• camerad frame-id and frame-drop checks; modeld raises modeldLagging and frame drops <sub>openpilot/selfdrive/modeld/modeld.py</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-009 |
| `SFM-003.C4` Device mount moved after calibration | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub><br>• Mount tolerance checked at installation (PFMEA PFM-009); calibrationd keeps recalibrating within bounds <sub>assurance/08-analyses/fmea/analyses/pfmea.yaml</sub> | • No pre-release test targets this cause | 5 | 10 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: Safety model torque/rate limits bound the deviation rate (not the direction) · Driver steering override yields lateral control (steerOverride -> OVERRIDE_LATERAL)

<sub>Note: HARA input: steering away from lane while engaged.</sub>

#### SFM-004 · Insufficient lateral control (undershoot in curves, drift toward lane edge)

🔴 **H** · **S 10** · guideword *insufficient* · function `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged

Effects:

- **End:** Lane departure if the driver does not intervene (HZ-004, S 10)
- **Next higher:** Vehicle drifts to lane edge in curves
- **Local:** Achieved curvature below desired curvature

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-004.C1` Safety model torque limit below what the curve requires (by design) | • Panda limits are copied from upstream vehicle tuning (same constants as the SoC side); no independent envelope derived from vehicle measurements (FSC FOI-001) <sub>opendbc_repo/opendbc/safety/modes/toyota.h</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-001 |
| `SFM-004.C2` EPS limits or rejects torque request (EPS fault, torque limit, lockout) | • Series-production Toyota ECU with long field exposure; assumed developed to ISO 26262 by the OEM (assumption of use, not verified by LionDriver) | • No pre-release test targets this cause | 5 | 10 | 🔴 **H** | SFM-ACT-003 |
| `SFM-004.C3` Controller tuning or torque model too weak for vehicle state | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • Lateral controller unit tests (saturation detection, torque buffer); targeted at nominal behaviour, not proven <sub>openpilot/selfdrive/controls/tests/test_latcontrol.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-002, SFM-ACT-003 |

Safety mechanisms: steerSaturated warning when undershooting > 1.2x in a turn with saturated controller · ldw (lane departure warning) alert

<sub>Note: Mostly a designed limitation: overlaps SOTIF. Kept here for the failure path (EPS/controller fault).</sub>

#### SFM-005 · Loss of lateral control without driver alert

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged

Effects:

- **End:** Driver unaware of loss; lane departure (HZ-004, S 10)
- **Next higher:** Vehicle no longer follows the lane
- **Local:** Steering requests stop or are ignored while the item shows engaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-005.C1` EPS stops accepting requests without a fault signal on CAN | • Series-production Toyota ECU with long field exposure; assumed developed to ISO 26262 by the OEM (assumption of use, not verified by LionDriver) | • No pre-release test targets this cause | 3 | 10 | 🔴 **H** | SFM-ACT-003 |
| `SFM-005.C2` pandad stops forwarding TX without the state being reported | • None specific. Whether the comma 3X ever suspends after boot while openpilot runs (offset > 0) is not established | • No test targets this cause; no test exercises the age gate | 5 | 10 | 🔴 **H** | — |
| `SFM-005.C3` Process crash or hang not detected by liveness checks | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• manager restarts and reports processes; selfdrived raises processNotRunning and commIssue from SubMaster alive/frequency checks <sub>openpilot/selfdrive/selfdrived/selfdrived.py</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-002 |

Safety mechanisms: steerUnavailable (IMMEDIATE_DISABLE) and steerTempUnavailable (SOFT_DISABLE) from EPS fault signals · Process liveness/frequency checks raise commIssue / processNotRunning (SOFT_DISABLE)

<sub>Note: With a correct alert the effect is a controlled handback (S 8 per RT-1). Without one it is a HARA candidate.</sub>

#### SFM-006 · Lateral command frozen at last value

🔴 **H** · **S 10** · guideword *stuck* · function `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged

Effects:

- **End:** Vehicle leaves the lane on a curve or straight (HZ-003, S 10)
- **Next higher:** Vehicle holds a constant steering input
- **Local:** Same torque request repeated regardless of road geometry

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-006.C1` controlsd hangs while card keeps sending the last carControl | • Upstream review, ruff, ty; excluded from fuzzing (test_fuzzy.py:13) | • No test injects non-finite lateralDelay | 6 | 10 | 🔴 **H** | — |
| `SFM-006.C2` modeld output frozen (stale frame) but still published as valid | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• modeld publishes frame drop percentage and raises modeldLagging; selfdrived checks modelV2 validity and frequency <sub>openpilot/selfdrive/modeld/modeld.py</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-002 |
| `SFM-006.C3` Messaging delivers stale data with fresh timestamps | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• msgq/cereal stamp logMonoTime at publication; SubMaster tracks arrival time and frequency <sub>openpilot/cereal/messaging/__init__.py</sub> | • No pre-release test targets this cause | 5 | 10 | 🔴 **H** | SFM-ACT-002 |

Safety mechanisms: Message liveness and frequency checks on inputs (sm.all_checks -> commIssue) · Panda heartbeat loss removes controls_allowed (firmware, to verify in SW FMEA)

<sub>Note: HARA input: constant steering command not following road.</sub>

#### SFM-007 · Oscillating lateral control

🔴 **H** · **S 7** · guideword *degraded* · function `SFM-FN-001` F1 Lateral control: request steering torque from the EPS to keep the vehicle in its lane while engaged

Effects:

- **End:** Driver discomfort; possible over-correction by driver
- **Next higher:** Vehicle weaves within the lane
- **Local:** Torque request oscillates

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-007.C1` Controller instability (gain, delay compensation, lagd estimate) | • Upstream review and lint; LatControlCurvature does reset its PID (latcontrol_curvature.py:28-31), so the omission may be an oversight or deliberate upstream; no requirement states either <sub>openpilot/selfdrive/controls/lib/latcontrol_curvature.py</sub> | • test_latcontrol.py covers saturation only; test_latcontrol_torque_buffer.py covers the request buffer only; nothing checks controller state across disengagement | 7 | 10 | 🔴 **H** | — |
| `SFM-007.C2` Control loop timing jitter (CPU load, thermal throttling) | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• Real-time scheduling priority and CPU affinity set by the control processes (config_realtime_process) <sub>openpilot/selfdrive/controls/controlsd.py:237</sub> | • No pre-release test targets this cause | 5 | 10 | 🔴 **H** | SFM-ACT-003 |

#### SFM-008 · Unintended acceleration

🔴 **H** · **S 10** · guideword *unintended* · function `SFM-FN-002` F2 Longitudinal control: request acceleration/deceleration to hold set speed and follow leads while engaged

Effects:

- **End:** Rear-end collision with lead vehicle or loss of control (HZ-005, S 10)
- **Next higher:** Vehicle accelerates unexpectedly
- **Local:** Positive acceleration requested when not required or not engaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-008.C1` Planner targets higher speed (missed lead, wrong set speed) | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• Set speed taken from the stock PCM cruise; panda caps acceleration at +2.0 m/s² (SWF-003) <sub>openpilot/selfdrive/controls/lib/longitudinal_planner.py</sub> | • Unit test of the longitudinal plan's following distance and set-speed behaviour; targeted, not proven <sub>openpilot/selfdrive/controls/tests/test_following_distance.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-001, SFM-ACT-002 |
| `SFM-008.C2` Longitudinal controller output too high | • Planner jerk and accel limits only; TSR-605 margin not implemented <sub>openpilot/selfdrive/controls/lib/longitudinal_planner.py</sub> | • test_longcontrol.py covers state transitions, not limits <sub>openpilot/selfdrive/controls/tests/test_longcontrol.py</sub> | 7 | 10 | 🔴 **H** | SFM-ACT-001 |
| `SFM-008.C3` Wrong scaling of acceleration request for this car | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub><br>• Panda checks the raw ACC_CONTROL acceleration value against its range (catches scaling errors only beyond the range) <sub>opendbc_repo/opendbc/safety/modes/toyota.h</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |
| `SFM-008.C4` Powertrain applies more acceleration than requested | • Series-production Toyota ECU with long field exposure; assumed developed to ISO 26262 by the OEM (assumption of use, not verified by LionDriver) | • No pre-release test targets this cause | 3 | 10 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: Panda/opendbc safety model limits acceleration request range and blocks when not engaged · Excessive longitudinal acceleration check (> 2x ACCEL_MAX for 0.25 s) -> excessiveActuation · Brake press -> pedalPressed (USER_DISABLE)

<sub>Note: HARA input: unintended acceleration while engaged.</sub>

#### SFM-009 · Unintended or excessive deceleration (phantom braking)

🔴 **H** · **S 10** · guideword *excessive* · function `SFM-FN-002` F2 Longitudinal control: request acceleration/deceleration to hold set speed and follow leads while engaged

Effects:

- **End:** Rear-end collision by following vehicle; occupant injury (HZ-006, S 10)
- **Next higher:** Vehicle brakes hard
- **Local:** Strong deceleration requested without a real obstacle

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-009.C1` False lead (radar ghost, model false positive) or FCW false trigger | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• Upstream neural network trained and validated by comma.ai; no development or validation evidence is available to LionDriver (SOTIF / ISO PAS 8800 scope, WP-C-06) <sub>openpilot/selfdrive/modeld</sub> | • Unit tests for lead handling and following distance; targeted at the nominal logic, not proven by fault injection <sub>openpilot/selfdrive/controls/tests/test_leads.py</sub> | 7 | 8 | 🔴 **H** | SFM-ACT-009 |
| `SFM-009.C2` Longitudinal controller overshoot | • Planner jerk and accel limits only; TSR-605 margin not implemented <sub>openpilot/selfdrive/controls/lib/longitudinal_planner.py</sub> | • test_longcontrol.py covers state transitions, not limits <sub>openpilot/selfdrive/controls/tests/test_longcontrol.py</sub> | 7 | 10 | 🔴 **H** | SFM-ACT-001 |
| `SFM-009.C3` Wrong vEgo/aEgo from CAN parse | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: Safety model limits minimum acceleration request · Excessive longitudinal deceleration check -> excessiveActuation · Accelerator press -> gasPressedOverride (OVERRIDE_LONGITUDINAL)

<sub>Note: HARA input: unexpected hard braking. False-positive perception without a fault belongs to SOTIF.</sub>

#### SFM-010 · Insufficient deceleration for lead vehicle or stop

🔴 **H** · **S 10** · guideword *insufficient* · function `SFM-FN-002` F2 Longitudinal control: request acceleration/deceleration to hold set speed and follow leads while engaged

Effects:

- **End:** Rear-end collision if the driver does not brake (HZ-007, S 10)
- **Next higher:** Closing distance to lead shrinks
- **Local:** Deceleration request below what the situation needs

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-010.C1` Lead missed due to radar/vision fusion fault | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• Upstream neural network trained and validated by comma.ai; no development or validation evidence is available to LionDriver (SOTIF / ISO PAS 8800 scope, WP-C-06) <sub>openpilot/selfdrive/modeld</sub> | • Unit tests for lead handling and following distance; targeted at the nominal logic, not proven by fault injection <sub>openpilot/selfdrive/controls/tests/test_leads.py</sub> | 7 | 8 | 🔴 **H** | SFM-ACT-009 |
| `SFM-010.C2` Safety model minimum accel limit prevents required braking (by design) | • Panda limits are copied from upstream vehicle tuning (same constants as the SoC side); no independent envelope derived from vehicle measurements (FSC FOI-001) <sub>opendbc_repo/opendbc/safety/modes/toyota.h</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-006 |
| `SFM-010.C3` Brake system does not achieve requested deceleration | • Series-production Toyota ECU with long field exposure; assumed developed to ISO 26262 by the OEM (assumption of use, not verified by LionDriver) | • No pre-release test targets this cause | 3 | 10 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: FCW from planner or model (ET.PERMANENT alert) · Radar faults raise radarFault / canError (SOFT_DISABLE / IMMEDIATE_DISABLE)

<sub>Note: HARA input: insufficient braking for lead while engaged.</sub>

#### SFM-011 · Loss of longitudinal control without driver alert

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-002` F2 Longitudinal control: request acceleration/deceleration to hold set speed and follow leads while engaged

Effects:

- **End:** Driver unaware; closing on lead (HZ-007, S 10)
- **Next higher:** Vehicle coasts or holds previous state
- **Local:** Acceleration requests stop or are ignored while engaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-011.C1` Powertrain ignores requests without fault signal | • Series-production Toyota ECU with long field exposure; assumed developed to ISO 26262 by the OEM (assumption of use, not verified by LionDriver) | • No pre-release test targets this cause | 3 | 10 | 🔴 **H** | SFM-ACT-003 |
| `SFM-011.C2` TX path to vehicle lost silently | • None specific. Whether the comma 3X ever suspends after boot while openpilot runs (offset > 0) is not established | • No test targets this cause; no test exercises the age gate | 5 | 10 | 🔴 **H** | — |

Safety mechanisms: accFaulted (IMMEDIATE_DISABLE), cruiseDisabled (IMMEDIATE_DISABLE) · canBusMissing (IMMEDIATE_DISABLE), canError

<sub>Note: With a correct alert, S 8 per RT-1. Without one, HARA candidate.</sub>

#### SFM-012 · Late reaction to lead vehicle braking

🔴 **H** · **S 10** · guideword *late* · function `SFM-FN-002` F2 Longitudinal control: request acceleration/deceleration to hold set speed and follow leads while engaged

Effects:

- **End:** Rear-end collision or harsh late braking (HZ-007, S 10)
- **Next higher:** Reduced time gap
- **Local:** Deceleration request delayed

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-012.C1` Pipeline latency (CPU overload, thermal throttle, messaging delay) | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• Real-time priorities; selfdrived raises modeldLagging, selfdrivedLagging and commIssueAvgFreq <sub>openpilot/selfdrive/selfdrived/selfdrived.py</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-003 |
| `SFM-012.C2` Lead state filtered too slowly (radard) | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • Unit tests for lead handling and following distance; targeted at the nominal logic, not proven by fault injection <sub>openpilot/selfdrive/controls/tests/test_leads.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-009 |

Safety mechanisms: modeldLagging / selfdrivedLagging (SOFT_DISABLE), commIssueAvgFreq

#### SFM-013 · Engagement without driver request or with entry conditions not met

🔴 **H** · **S 10** · guideword *unintended* · function `SFM-FN-003` F3 Engagement management: engage only on driver request with entry conditions met; disengage per fault reaction (soft/immediate)

Effects:

- **End:** Unexpected steering/acceleration; driver surprised (HZ-010, S 10)
- **Next higher:** Item starts actuating
- **Local:** State machine enters enabled without ENABLE or despite NO_ENTRY

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-013.C1` State machine transition error | • Upstream code with review; ruff and ty run in fork CI static_analysis; unit tests derived from the implementation; no software requirements <sub>scripts/lint/lint.sh:45,55; .github/workflows/tests.yaml</sub> | • test_no_entry and test_no_entry_pre_enable (ENABLE with NO_ENTRY stays disabled), run by tests.yaml unit_tests on every push and PR; not proven by mutation <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 6 | 8 | 🔴 **H** | — |
| `SFM-013.C2` Cruise state or button parsed incorrectly (spurious enable) | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: NO_ENTRY events block engagement (state.py) · Toyota uses PCM cruise; engagement follows stock cruise main/set (cruise state in carState)

<sub>Note: HARA input: unintended engagement.</sub>

#### SFM-014 · Fails to disengage when a fault requires it

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-003` F3 Engagement management: engage only on driver request with entry conditions met; disengage per fault reaction (soft/immediate)

Effects:

- **End:** Any F1/F2 hazardous effect continues (HZ-002, S 10)
- **End:** Contributes to HZ-005: Unintended acceleration (HZ-005, S 10)
- **End:** Contributes to HZ-006: Unintended or excessive deceleration (HZ-006, S 10)
- **Next higher:** Item keeps actuating with a faulty input or actuator
- **Local:** SOFT_DISABLE/IMMEDIATE_DISABLE event not acted on

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-014.C1` Event missing for the fault (no detection) | • Only relayMalfunction, safety model/param and controlsAllowed are checked (selfdrived.py:328-346) <sub>openpilot/selfdrive/selfdrived/selfdrived.py:328-346</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | — |
| `SFM-014.C2` Event mapped to wrong reaction type in events.py | • Reaction types chosen upstream; FSC WD-01 notes the 3 s must be justified per event (not done) <sub>openpilot/selfdrive/selfdrived/events.py</sub> | • test_soft_disable_timer checks that the timer is 3 s; it is not designed to show that 3 s is within the FTTI <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 8 | 9 | 🔴 **H** | SFM-ACT-010 |
| `SFM-014.C3` Catch-all commIssue suppressed by the no_system_errors logic while another event is active | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• The catch-all commIssue is suppressed only while a NO_ENTRY and a SOFT_DISABLE or IMMEDIATE_DISABLE event are already present, so a disable reaction is raised either way <sub>openpilot/selfdrive/selfdrived/selfdrived.py:384-388</sub> | • No pre-release test targets this cause | 2 | 10 | 🔴 **H** | — |

Safety mechanisms: Panda heartbeat carries engaged = selfdriveState alive, valid and enabled; panda removes controls_allowed on heartbeat loss (firmware, to verify)

<sub>Note: HARA input: continued actuation after fault detection.</sub>

#### SFM-015 · Abrupt disengagement without alert

🔴 **H** · **S 10** · guideword *unintended* · function `SFM-FN-003` F3 Engagement management: engage only on driver request with entry conditions met; disengage per fault reaction (soft/immediate)

Effects:

- **End:** Driver unaware of handback; lane departure or closing on lead (HZ-004, S 10)
- **Next higher:** Steering assist and ACC stop
- **Local:** Item drops to disabled with no alert

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-015.C1` Alert generated but not rendered or played (see SFM-026) | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • soundd unit test (alert sound selection and volume); targeted, not proven; audibility in the cabin not tested <sub>openpilot/selfdrive/ui/tests/test_soundd.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-007 |
| `SFM-015.C2` Panda drops controls_allowed on its own (e.g. safety violation) and selfdrived reacts late | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• selfdrived raises controlsMismatch (IMMEDIATE_DISABLE) when the panda reports controls not allowed while engaged, but only after 200 frames (2 s at 100 Hz) <sub>openpilot/selfdrive/selfdrived/selfdrived.py:338</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-010 |
| `SFM-015.C3` Device power loss (12 V interruption, harness connector) | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | • As rated in the DFMEA: no pre-release test of this hardware fault <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | 5 | 10 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: Every disable transition appends an alert type (USER_DISABLE / IMMEDIATE_DISABLE / SOFT_DISABLE)

#### SFM-016 · Disengagement later than required by the fault

🔴 **H** · **S 10** · guideword *late* · function `SFM-FN-003` F3 Engagement management: engage only on driver request with entry conditions met; disengage per fault reaction (soft/immediate)

Effects:

- **End:** Lateral or longitudinal deviation during the soft-disable window (HZ-002, S 10)
- **End:** Contributes to HZ-005: Unintended acceleration (HZ-005, S 10)
- **Next higher:** Faulty actuation continues up to 3 s
- **Local:** SOFT_DISABLE (3 s) used where IMMEDIATE_DISABLE is needed

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-016.C1` Reaction type for an event under-classified (soft instead of immediate) | • Reaction types chosen upstream; FSC WD-01 notes the 3 s must be justified per event (not done) <sub>openpilot/selfdrive/selfdrived/events.py</sub> | • test_soft_disable_timer checks that the timer is 3 s; it is not designed to show that 3 s is within the FTTI <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 8 | 9 | 🔴 **H** | SFM-ACT-010 |
| `SFM-016.C2` Debounce/counters too long (e.g. excessive actuation 0.25 s, mismatch counter 200 frames) | • Upstream threshold; TSR-621 records it as partial <sub>openpilot/selfdrive/selfdrived/selfdrived.py:504-514</sub> | • No test targets this cause | 8 | 10 | 🔴 **H** | SFM-ACT-010 |

<sub>Note: Needs FTTI from the HARA/FSC to judge. Each SOFT_DISABLE event should be justified against FTTI.</sub>

#### SFM-017 · Brake press does not disengage

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-004` F4 Driver override: release control on brake or cancel; yield lateral to steering input and longitudinal to accelerator

Effects:

- **End:** Driver cannot retake control as expected (SAFETY.md requirement 1 violated) (HZ-008, S 10)
- **Next higher:** Item keeps requesting acceleration/steering during driver braking
- **Local:** pedalPressed not raised or not acted on

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-017.C1` brakePressed parsed wrong or CAN signal missing | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |
| `SFM-017.C2` Car events ignored when canValid is false | • Upstream code with review; ruff and ty in fork CI; no unit test of selfdrived.py event generation; no software requirements <sub>scripts/lint/lint.sh:45,55</sub> | • test_user_disable covers the state-machine part (USER_DISABLE from every state), CI unit_tests, not proven; the pedal edge logic is exercised only by process_replay over recorded segments (generic regression, includes a Corolla TSS2 segment) <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 7 | 8 | 🔴 **H** | — |

Safety mechanisms: selfdrived raises pedalPressed (USER_DISABLE) on brake press · Panda safety model independently drops controls_allowed on brake press (firmware, to verify)

<sub>Note: HARA input: driver brake does not cancel automation. Directly tied to SAFETY.md requirement 1.</sub>

#### SFM-018 · Item resists driver steering input

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-004` F4 Driver override: release control on brake or cancel; yield lateral to steering input and longitudinal to accelerator

Effects:

- **End:** Delayed evasive maneuver or loss of control (HZ-009, S 10)
- **Next higher:** Driver must overpower the item
- **Local:** steerOverride not detected; lateral torque continues

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-018.C1` Driver torque threshold too high or signal parsed wrong | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |
| `SFM-018.C2` Controller keeps commanding torque during override | • Upstream design intent (driver overpowers a bounded torque); no LionDriver requirement analysis of the deviation <sub>openpilot/selfdrive/selfdrived/state.py:8</sub> | • test_maintain_states checks that overriding persists with OVERRIDE events; it does not check commanded torque <sub>openpilot/selfdrive/selfdrived/tests/test_state_machine.py</sub> | 8 | 9 | 🔴 **H** | — |

Safety mechanisms: steerOverride -> OVERRIDE_LATERAL state · EPS torque limit allows driver to overpower the request

<sub>Note: HARA input: automation resists evasive steering.</sub>

#### SFM-019 · Cancel button does not disengage

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-004` F4 Driver override: release control on brake or cancel; yield lateral to steering input and longitudinal to accelerator

Effects:

- **End:** Driver must use brake to disengage (HZ-008, S 10)
- **Next higher:** Item stays engaged
- **Local:** buttonCancel not raised

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-019.C1` Button message parsed wrong or missing | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: buttonCancel (USER_DISABLE); brake remains as independent path

#### SFM-020 · Accelerator override not honored

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-004` F4 Driver override: release control on brake or cancel; yield lateral to steering input and longitudinal to accelerator

Effects:

- **End:** Driver cannot accelerate out of a situation (e.g. merging) (HZ-006, S 10)
- **Next higher:** Item keeps braking while driver accelerates
- **Local:** gasPressedOverride not detected

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-020.C1` gasPressed parsed wrong or missing | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • opendbc car tests check carState against the panda safety model on recorded routes (test_models); targeted at parse and pack consistency, not proven by fault injection, and run only where the route corpus is available <sub>opendbc_repo/opendbc/car/tests/test_models.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: gasPressedOverride -> OVERRIDE_LONGITUDINAL; longActive false during override

#### SFM-021 · Stock cruise stays engaged after LionDriver disengages

🔴 **H** · **S 10** · guideword *stuck* · function `SFM-FN-004` F4 Driver override: release control on brake or cancel; yield lateral to steering input and longitudinal to accelerator

Effects:

- **End:** Driver believes automation is off (mode confusion) (HZ-012, S 10)
- **Next higher:** Vehicle continues under stock cruise
- **Local:** Cancel request not effective; PCM cruise enabled while item is disabled

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-021.C1` Cancel message not packed/sent for this car | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • process_replay over the CI route corpus compares outputs with the reference commit (CI 'process replay'); a regression check, not designed or proven for this cause <sub>openpilot/selfdrive/test/process_replay/test_processes.py</sub> | 6 | 9 | 🔴 **H** | SFM-ACT-011 |
| `SFM-021.C2` PCM ignores cancel request | • Series-production Toyota ECU with long field exposure; assumed developed to ISO 26262 by the OEM (assumption of use, not verified by LionDriver) | • No pre-release test targets this cause | 3 | 10 | 🔴 **H** | SFM-ACT-011 |

Safety mechanisms: controlsd sends cruiseControl.cancel when cruise enabled and item not enabled

<sub>Note: Observation: selfdrived raises cruiseMismatch after 6 s of mismatch, but events.py maps cruiseMismatch to no reaction (its ET.PERMANENT alert is commented out). Mismatch is logged, not alerted. Confirmed at BL-004 in the SW FMEA (SWF-039); action SFM-ACT-011.</sub>

#### SFM-022 · Inattentive driver not detected

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-005` F5 Driver monitoring: detect inattention and escalate alerts; lock out engagement after repeated non-response

Effects:

- **End:** Driver not available to handle F1/F2 failures or system limits (HZ-013, S 10)
- **Next higher:** No distraction alerts
- **Local:** Awareness not decremented

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-022.C1` DM model false negative (eyes off road classified attentive) | • Upstream neural network trained and validated by comma.ai; no development or validation evidence is available to LionDriver (SOTIF / ISO PAS 8800 scope, WP-C-06) <sub>openpilot/selfdrive/modeld</sub> | • No pre-release test targets this cause | 7 | 10 | 🔴 **H** | SFM-ACT-009 |
| `SFM-022.C2` Pose thresholds/calibration wrong for driver or mount | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • Driver-monitoring policy unit tests (alert timing, awareness recovery, exemptions) on synthetic inputs; targeted, not proven by fault injection; the model itself is not tested <sub>openpilot/selfdrive/monitoring/test_monitoring.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-009 |
| `SFM-022.C3` Driver camera or IR illumination degraded | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub><br>• selfdrived raises cameraMalfunction when driver camera frames stop <sub>openpilot/selfdrive/selfdrived/selfdrived.py</sub> | • No pre-release test targets this cause | 5 | 10 | 🔴 **H** | SFM-ACT-003 |

Safety mechanisms: Fallback from vision policy to wheel-touch policy when model is uncertain for 10 s · Driver camera liveness in camera_packets -> cameraMalfunction (SOFT_DISABLE)

<sub>Note: HARA input: loss of the driver as the fallback (L2 safety argument depends on it). DM model performance is also SOTIF/PAS 8800.</sub>

#### SFM-023 · Distraction escalation too slow

🔴 **H** · **S 10** · guideword *late* · function `SFM-FN-005` F5 Driver monitoring: detect inattention and escalate alerts; lock out engagement after repeated non-response

Effects:

- **End:** Driver not ready when takeover needed (HZ-013, S 10)
- **Next higher:** Longer eyes-off-road while engaged
- **Local:** Alert levels reached later than designed (5/8/13 s vision policy)

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-023.C1` Policy timers or recovery factor misconfigured | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • Driver-monitoring policy unit tests (alert timing, awareness recovery, exemptions) on synthetic inputs; targeted, not proven by fault injection; the model itself is not tested <sub>openpilot/selfdrive/monitoring/test_monitoring.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-002 |
| `SFM-023.C2` Low-speed or always-on exemption applied incorrectly | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • Driver-monitoring policy unit tests (alert timing, awareness recovery, exemptions) on synthetic inputs; targeted, not proven by fault injection; the model itself is not tested <sub>openpilot/selfdrive/monitoring/test_monitoring.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-002 |

#### SFM-024 · False distraction alerts

🟠 M · **S 4** · guideword *unintended* · function `SFM-FN-005` F5 Driver monitoring: detect inattention and escalate alerts; lock out engagement after repeated non-response

Effects:

- **End:** Driver annoyance; may reduce trust or prompt disabling DM in a fork
- **Next higher:** Nuisance alerts; possible lockout
- **Local:** Alerts raised for an attentive driver

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-024.C1` DM model false positive (sunglasses, lighting) | • Upstream neural network trained and validated by comma.ai; no development or validation evidence is available to LionDriver (SOTIF / ISO PAS 8800 scope, WP-C-06) <sub>openpilot/selfdrive/modeld</sub> | • No pre-release test targets this cause | 7 | 10 | 🟠 M | — |

#### SFM-025 · Terminal driver-unresponsive state does not bring the item to a safe state

🔴 **H** · **S 10** · guideword *insufficient* · function `SFM-FN-005` F5 Driver monitoring: detect inattention and escalate alerts; lock out engagement after repeated non-response

Effects:

- **End:** No fallback if the driver is incapacitated (HZ-013, S 10)
- **Next higher:** Vehicle continues under automation with an unresponsive driver
- **Local:** Alert level three shows "DISENGAGE IMMEDIATELY" but the item stays engaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-025.C1` driverDistracted3 / driverUnresponsive3 mapped only to ET.PERMANENT (no disable reaction) | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • Present by design and known; no test, because no requirement says what the reaction should be <sub>openpilot/selfdrive/selfdrived/events.py</sub> | 8 | 10 | 🔴 **H** | SFM-ACT-005 |

Safety mechanisms: Lockout after repeated non-response prevents re-engagement (1/5/15/30 min)

<sub>Note: Observation: in BL-001, events.py maps driverDistracted3 and driverUnresponsive3 only to an ET.PERMANENT alert; no SOFT_DISABLE/IMMEDIATE_DISABLE is attached, so reaching awareness 0 does not by itself disengage. This may be a deliberate design choice (avoid dropping control on an incapacitated driver). It needs an explicit safety-concept decision (SFM-ACT-005); unchanged at BL-004. HARA input: driver incapacitated while engaged.</sub>

#### SFM-026 · Takeover or disengagement alert not presented

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-006` F6 Alerting: inform the driver of engagement state, takeover requests and faults (visual and audible)

Effects:

- **End:** Driver unaware of handback; delayed response (HZ-012, S 10)
- **End:** Contributes to HZ-006: item-initiated deceleration not announced (HE-04.3) (HZ-006, S 10)
- **Next higher:** Driver not informed of state change
- **Local:** Alert selected by alertmanager but not shown or not played

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-026.C1` UI process hung or display off | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-007 |
| `SFM-026.C2` soundd failure or volume too low for cabin noise | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub><br>• soundd scales volume with ambient noise and plays alerts at a minimum level <sub>openpilot/selfdrive/ui/soundd.py</sub> | • soundd unit test (alert sound selection and volume); targeted, not proven; audibility in the cabin not tested <sub>openpilot/selfdrive/ui/tests/test_soundd.py</sub> | 6 | 8 | 🔴 **H** | SFM-ACT-007, SFM-ACT-003 |
| `SFM-026.C3` Speaker or display hardware failure | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | • No pre-release test targets this cause | 4 | 10 | 🔴 **H** | SFM-ACT-007 |

Safety mechanisms: Visual alert on device screen and audible alert through soundd (two channels)

<sub>Note: HARA input: failure to warn the driver of handback.</sub>

#### SFM-027 · Alert presented late

🔴 **H** · **S 10** · guideword *late* · function `SFM-FN-006` F6 Alerting: inform the driver of engagement state, takeover requests and faults (visual and audible)

Effects:

- **End:** Reduced takeover margin (HZ-012, S 10)
- **Next higher:** Less time for driver response
- **Local:** Alert rendered/played after a delay

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-027.C1` UI frame drops or audio buffering | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-003 |
| `SFM-027.C2` Alert creation_delay or priority hides a more urgent alert | • Upstream code with review; ruff and ty run in fork CI static_analysis; unit tests derived from the implementation; no software requirements <sub>scripts/lint/lint.sh:45,55; .github/workflows/tests.yaml</sub> | • test_alertmanager checks alert duration only; test_alerts checks text/size sanity; neither checks priority between takeover and other alerts <sub>openpilot/selfdrive/selfdrived/tests/test_alertmanager.py</sub> | 6 | 9 | 🔴 **H** | — |

#### SFM-028 · Displayed engagement state differs from actual state

🔴 **H** · **S 10** · guideword *unintended* · function `SFM-FN-006` F6 Alerting: inform the driver of engagement state, takeover requests and faults (visual and audible)

Effects:

- **End:** Driver stops steering/braking believing automation is active, or is surprised by actuation (HZ-012, S 10)
- **Next higher:** Mode confusion
- **Local:** UI shows engaged when disabled, or disabled when engaged

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-028.C1` UI renders stale selfdriveState | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-007 |
| `SFM-028.C2` Stock dashboard (HUD) state from hudControl inconsistent with item state | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub> | • process_replay over the CI route corpus compares outputs with the reference commit (CI 'process replay'); a regression check, not designed or proven for this cause <sub>openpilot/selfdrive/test/process_replay/test_processes.py</sub> | 6 | 9 | 🔴 **H** | SFM-ACT-003 |

<sub>Note: HARA input: mode confusion.</sub>

#### SFM-029 · Actuator command limits not enforced

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-007` F7 Actuation limiting: bound actuator commands in magnitude and rate; detect excessive actuation

Effects:

- **End:** Any upstream fault can produce SFM-002 / SFM-008 / SFM-009 effects (HZ-002, S 10)
- **End:** Contributes to HZ-005: Unintended acceleration (HZ-005, S 10)
- **End:** Contributes to HZ-006: Unintended or excessive deceleration (HZ-006, S 10)
- **Next higher:** Loss of the main protection against F1/F2 faults on the device
- **Local:** Out-of-limit steering or acceleration messages reach the vehicle

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-029.C1` Wrong safety model or parameter set for this car | • Panda safety code: MISRA C:2012, 100% line coverage, review; rated in the SW FMEA <sub>assurance/08-analyses/fmea/analyses/sw-fmea.yaml</sub> | • As rated in the SW FMEA: no test covers the build configuration <sub>assurance/08-analyses/fmea/analyses/sw-fmea.yaml</sub> | 8 | 9 | 🔴 **H** | — |
| `SFM-029.C2` Safety model limit defect in firmware | • Panda limits are copied from upstream vehicle tuning (same constants as the SoC side); no independent envelope derived from vehicle measurements (FSC FOI-001) <sub>opendbc_repo/opendbc/safety/modes/toyota.h</sub><br>• Panda safety code: MISRA C:2012, 100% line coverage, review; rated in the SW FMEA <sub>assurance/08-analyses/fmea/analyses/sw-fmea.yaml</sub> | • opendbc safety suite with 100% line coverage and mutation tests, run by CI on every change (proven, early, test-to-fail) <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 6 | 9 | 🔴 **H** | SFM-ACT-001 |
| `SFM-029.C3` Panda MCU hardware fault (see DFMEA/FMEDA) | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | • As rated in the DFMEA: no pre-release test of this hardware fault <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | 3 | 10 | 🔴 **H** | — |
| `SFM-029.C4` Harness allows the device to reach a bus without passing the panda filter | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub><br>• Every vehicle CAN connection of the device terminates at the panda MCU's transceivers through the harness; the SoC has no CAN transceiver of its own (to be confirmed from comma 3X hardware documentation, not available to LionDriver) | • No pre-release test targets this cause | 2 | 10 | 🔴 **H** | — |

Safety mechanisms: controlsMismatch (IMMEDIATE_DISABLE) if panda safety model/param differ from CarParams, or safety RX checks invalid

<sub>Note: Latent-fault candidate: an unenforced limit has no effect until a second fault occurs. Key input for FMEDA LFM.</sub>

#### SFM-030 · Excessive actuation not detected

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-007` F7 Actuation limiting: bound actuator commands in magnitude and rate; detect excessive actuation

Effects:

- **End:** SFM-002/008/009 effects persist (HZ-002, S 10)
- **End:** Contributes to HZ-005: Unintended acceleration (HZ-005, S 10)
- **End:** Contributes to HZ-006: Unintended or excessive deceleration (HZ-006, S 10)
- **Next higher:** Item stays engaged during excessive motion
- **Local:** excessiveActuation not raised

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-030.C1` Calibrated pose wrong (calibration or IMU fault) | • Upstream openpilot code with upstream review; ruff and type checks in CI (static analysis job); unit tests are not requirements-based; no field-exposure evidence for this configuration, so none is credited (RT-1 §2.2) <sub>scripts/lint/lint.sh</sub> | • calibrationd unit tests (convergence, invalid calibration); targeted, not proven by fault injection <sub>openpilot/selfdrive/locationd/test/test_calibrationd.py</sub> | 5 | 8 | 🔴 **H** | SFM-ACT-002 |
| `SFM-030.C2` device_motion_valid gate blocks detection when aEgo and IMU disagree | • Upstream code with review; ruff and ty in fork CI; no unit test of selfdrived.py event generation; no software requirements <sub>scripts/lint/lint.sh:45,55</sub> | • No test targets this cause | 6 | 10 | 🔴 **H** | — |

<sub>Note: Latent-fault candidate (secondary monitor).</sub>

#### SFM-031 · False excessive-actuation detection

🔴 **H** · **S 8** · guideword *unintended* · function `SFM-FN-007` F7 Actuation limiting: bound actuator commands in magnitude and rate; detect excessive actuation

Effects:

- **End:** Unneeded handback to the driver
- **Next higher:** Soft disable with alert
- **Local:** excessiveActuation raised without excessive motion

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-031.C1` IMU noise or bad mounting | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | • No pre-release test targets this cause | 5 | 10 | 🔴 **H** | SFM-ACT-003 |

#### SFM-032 · Wrong vehicle configuration active (fingerprint or car port)

🔴 **H** · **S 10** · guideword *unintended* · function `SFM-FN-007` F7 Actuation limiting: bound actuator commands in magnitude and rate; detect excessive actuation

Effects:

- **End:** Any F1/F2 effect; possible message conflicts with stock ECUs (HZ-002, S 10)
- **End:** Contributes to HZ-005: Unintended acceleration (HZ-005, S 10)
- **End:** Contributes to HZ-006: Unintended or excessive deceleration (HZ-006, S 10)
- **Next higher:** Wrong limits, scaling and message layout
- **Local:** CarParams, safety model and DBC for a different car

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-032.C1` Fuzzy fingerprint matches a similar platform | • Upstream opendbc Toyota port (DBC, carstate, carcontroller) with upstream review and route-based car tests; no LionDriver requirements; no field-exposure evidence for this configuration is credited <sub>opendbc_repo/opendbc/car/toyota</sub><br>• Exact FW-version fingerprint first, fuzzy fallback; controlsMismatch if the panda safety model or parameter differ from CarParams <sub>opendbc_repo/opendbc/car/fw_versions.py</sub> | • Fingerprinting unit tests (FW and CAN fingerprint); targeted, not proven by fault injection <sub>opendbc_repo/opendbc/car/tests/test_fw_fingerprint.py</sub> | 5 | 8 | 🔴 **H** | SFM-ACT-008 |

Safety mechanisms: carUnrecognized -> dashcam mode (no control) · controlsMismatch on safety model/param mismatch

<sub>Note: Also a PFMEA topic (car port selection, PFMEA scope item 6).</sub>

#### SFM-033 · Stock safety functions unavailable or degraded while the item is installed

🔴 **H** · **S 10** · guideword *loss* · function `SFM-FN-008` F8 Stock function preservation: keep stock vehicle safety functions not replaced by the item available

Effects:

- **End:** Driver relies on stock protections that are not present (HZ-011, S 10)
- **Next higher:** Stock AEB / FCW / lane assist not available as expected
- **Local:** Stock ADAS camera messages blocked or replaced by the harness relay

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-033.C1` Relay intercepts stock camera messages the vehicle needs for AEB | • Forwarding keeps stock pre-collision messages (0x283, 0x344) passing the relay (SWF-011); which TSS2 functions remain with openpilot longitudinal is not established <sub>opendbc_repo/opendbc/safety/modes/toyota.h</sub> | • No pre-release test targets this cause | 6 | 10 | 🔴 **H** | SFM-ACT-006 |
| `SFM-033.C2` Item does not forward or reproduce stock safety messages | • Panda safety code: MISRA C:2012, 100% line coverage, review; rated in the SW FMEA <sub>assurance/08-analyses/fmea/analyses/sw-fmea.yaml</sub> | • opendbc safety suite with 100% line coverage and mutation tests, run by CI on every change (proven, early, test-to-fail) <sub>opendbc_repo/opendbc/safety/tests/test_toyota.py</sub> | 5 | 3 | 🔴 **H** | SFM-ACT-006 |

<sub>Note: Open question: which stock TSS2 functions remain on the 2020 Corolla with openpilot longitudinal enabled. Must be established from the opendbc Toyota port and in-vehicle test before the HARA. HARA input: loss of stock AEB/FCW.</sub>

#### SFM-034 · Harness relay fault

🔴 **H** · **S 10** · guideword *intermittent* · function `SFM-FN-008` F8 Stock function preservation: keep stock vehicle safety functions not replaced by the item available

Effects:

- **End:** Erratic stock or item behavior; stock functions lost (HZ-011, S 10)
- **End:** Contributes to HZ-002: stock LKA and item steering requests combine on the bus (HZ-002, S 10)
- **End:** Contributes to HZ-006: stock and item braking requests combine on the bus (HZ-006, S 10)
- **Next higher:** Conflicting steering/ACC messages, or no camera messages
- **Local:** Relay stuck or intermittent; stock camera and item both on bus, or neither

| Cause | Prevention | Detection | O | D | AP | Actions |
|---|---|---|:-:|:-:|:-:|---|
| `SFM-034.C1` Relay contact wear or connector fault | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | • As rated in the DFMEA: no pre-release test of this hardware fault <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | 3 | 10 | 🔴 **H** | — |
| `SFM-034.C2` Relay drive output fault on panda | • Consumer-grade device hardware (comma 3X) without automotive qualification data available to LionDriver; rated in the DFMEA where a DFM row exists <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | • As rated in the DFMEA: no pre-release test of this hardware fault <sub>assurance/08-analyses/fmea/analyses/dfmea.yaml</sub> | 3 | 10 | 🔴 **H** | — |

Safety mechanisms: relayMalfunction fault from panda -> IMMEDIATE_DISABLE

## 5. Actions

| ID | Kind | Action | Owner | Status | Causes | Revised S/O/D → AP |
|---|---|---|---|---|---|---|
| SFM-ACT-001 | design_change | Derive steering and acceleration envelopes from measurements on the reference vehicle and set the panda limits from them, independently of the SoC limits (same as SWF-ACT-003, FSC FOI-001) | Jherrod Thomas | open | SFM-002.C1, SFM-002.C2, SFM-002.C3, SFM-002.C4, SFM-004.C1, SFM-008.C1, SFM-008.C2, SFM-009.C2, SFM-029.C2 | — |
| SFM-ACT-002 | detection | Requirements-based tests for the host safety-relevant functions (selfdrived, controlsd, pandad, car interface, locationd bounds, monitoring policy), proven by mutation or fault injection and run as a CI gate (see SWF host actions) | Jherrod Thomas | open | SFM-002.C4, SFM-004.C3, SFM-005.C3, SFM-006.C2, SFM-006.C3, SFM-008.C1, SFM-023.C1, SFM-023.C2, SFM-030.C1 | — |
| SFM-ACT-003 | detection | Execute system integration and vehicle verification on the reference car (WP-S-08, WP-S-09) and the HIL bench (D-04): steering sign and torque response, EPS and powertrain interface behaviour (lockouts, ignored requests), brake, accelerator and cancel paths, relay and harness faults, 12 V interruptions, alert latency and audibility, CPU-load soak | Jherrod Thomas | open | SFM-003.C1, SFM-003.C2, SFM-003.C4, SFM-004.C2, SFM-004.C3, SFM-005.C1, SFM-007.C2, SFM-008.C3, SFM-008.C4, SFM-009.C3, SFM-010.C3, SFM-011.C1, SFM-012.C1, SFM-013.C2, SFM-015.C3, SFM-017.C1, SFM-018.C1, SFM-019.C1, SFM-020.C1, SFM-022.C3, SFM-026.C2, SFM-027.C1, SFM-028.C2, SFM-031.C1 | — |
| SFM-ACT-005 | design_change | Decide in the FSC how the item reacts when driver awareness reaches zero (driverUnresponsive3 / driverDistracted3 have no disable reaction at BL-004) and implement the decision | Jherrod Thomas | decision_pending | SFM-025.C1 | — |
| SFM-ACT-006 | detection | Establish on the reference car which stock TSS2 functions (PCS/AEB, FCW) remain available with LionDriver installed and longitudinal control enabled, and verify the stock pre-collision path after installation (PFMEA PFM-014) | Jherrod Thomas | open | SFM-010.C2, SFM-033.C1, SFM-033.C2 | — |
| SFM-ACT-007 | design_change | Supervise the alert channels: treat loss of ui or soundd liveness, or a stale displayed state, as a fault that escalates (audible fallback, disengagement) instead of continuing silently | Jherrod Thomas | open | SFM-015.C1, SFM-026.C1, SFM-026.C2, SFM-026.C3, SFM-028.C1 | — |
| SFM-ACT-008 | design_change | Allow engagement only when the fingerprint, CarParams and panda safety parameter match the reference configuration AC-001 (refuse fuzzy matches in the reference build); see PFMEA PFM-013 | Jherrod Thomas | open | SFM-032.C1 | — |
| SFM-ACT-009 | prevention | Produce SOTIF / ISO PAS 8800 evidence for the neural-network elements (driving model, lead detection, driver monitoring model) per WP-V-02..04, including fault-induced inputs (corrupted or stale frames) | Jherrod Thomas | open | SFM-002.C2, SFM-003.C3, SFM-009.C1, SFM-010.C1, SFM-012.C2, SFM-022.C1, SFM-022.C2 | — |
| SFM-ACT-010 | design_change | Justify every SOFT_DISABLE reaction and debounce against the FTTI (WP-S-04) and alert at once when the panda withdraws authority while engaged (controlsMismatch debounce) | Jherrod Thomas | in_progress | SFM-014.C2, SFM-015.C2, SFM-016.C1, SFM-016.C2 | — |
| SFM-ACT-011 | design_change | Alert the driver when stock cruise stays engaged while the item is disengaged (cruiseMismatch has no alert at BL-004) | Jherrod Thomas | completed | SFM-021.C1, SFM-021.C2 | — |

## 6. Priority H causes without a completed action

| Cause | Failure mode | S/O/D | Open actions |
|---|---|---|---|
| `SFM-001.C1` | Steering torque applied when not engaged | 10/6/8 | **none** |
| `SFM-001.C2` | Steering torque applied when not engaged | 10/5/3 | **none** |
| `SFM-001.C3` | Steering torque applied when not engaged | 10/6/9 | **none** |
| `SFM-002.C1` | Steering torque or torque rate above limits | 10/7/10 | SFM-ACT-001 |
| `SFM-002.C2` | Steering torque or torque rate above limits | 10/7/10 | SFM-ACT-001, SFM-ACT-009 |
| `SFM-002.C3` | Steering torque or torque rate above limits | 10/6/9 | SFM-ACT-001 |
| `SFM-002.C4` | Steering torque or torque rate above limits | 10/6/8 | SFM-ACT-001, SFM-ACT-002 |
| `SFM-003.C1` | Steering in the wrong direction (away from lane center) | 10/6/8 | SFM-ACT-003 |
| `SFM-003.C2` | Steering in the wrong direction (away from lane center) | 10/6/8 | SFM-ACT-003 |
| `SFM-003.C3` | Steering in the wrong direction (away from lane center) | 10/6/10 | SFM-ACT-009 |
| `SFM-003.C4` | Steering in the wrong direction (away from lane center) | 10/5/10 | SFM-ACT-003 |
| `SFM-004.C1` | Insufficient lateral control (undershoot in curves, drift toward lane edge) | 10/6/10 | SFM-ACT-001 |
| `SFM-004.C2` | Insufficient lateral control (undershoot in curves, drift toward lane edge) | 10/5/10 | SFM-ACT-003 |
| `SFM-004.C3` | Insufficient lateral control (undershoot in curves, drift toward lane edge) | 10/6/8 | SFM-ACT-002, SFM-ACT-003 |
| `SFM-005.C1` | Loss of lateral control without driver alert | 10/3/10 | SFM-ACT-003 |
| `SFM-005.C2` | Loss of lateral control without driver alert | 10/5/10 | **none** |
| `SFM-005.C3` | Loss of lateral control without driver alert | 10/6/10 | SFM-ACT-002 |
| `SFM-006.C1` | Lateral command frozen at last value | 10/6/10 | **none** |
| `SFM-006.C2` | Lateral command frozen at last value | 10/6/10 | SFM-ACT-002 |
| `SFM-006.C3` | Lateral command frozen at last value | 10/5/10 | SFM-ACT-002 |
| `SFM-007.C1` | Oscillating lateral control | 7/7/10 | **none** |
| `SFM-007.C2` | Oscillating lateral control | 7/5/10 | SFM-ACT-003 |
| `SFM-008.C1` | Unintended acceleration | 10/6/8 | SFM-ACT-001, SFM-ACT-002 |
| `SFM-008.C2` | Unintended acceleration | 10/7/10 | SFM-ACT-001 |
| `SFM-008.C3` | Unintended acceleration | 10/6/8 | SFM-ACT-003 |
| `SFM-008.C4` | Unintended acceleration | 10/3/10 | SFM-ACT-003 |
| `SFM-009.C1` | Unintended or excessive deceleration (phantom braking) | 10/7/8 | SFM-ACT-009 |
| `SFM-009.C2` | Unintended or excessive deceleration (phantom braking) | 10/7/10 | SFM-ACT-001 |
| `SFM-009.C3` | Unintended or excessive deceleration (phantom braking) | 10/6/8 | SFM-ACT-003 |
| `SFM-010.C1` | Insufficient deceleration for lead vehicle or stop | 10/7/8 | SFM-ACT-009 |
| `SFM-010.C2` | Insufficient deceleration for lead vehicle or stop | 10/6/10 | SFM-ACT-006 |
| `SFM-010.C3` | Insufficient deceleration for lead vehicle or stop | 10/3/10 | SFM-ACT-003 |
| `SFM-011.C1` | Loss of longitudinal control without driver alert | 10/3/10 | SFM-ACT-003 |
| `SFM-011.C2` | Loss of longitudinal control without driver alert | 10/5/10 | **none** |
| `SFM-012.C1` | Late reaction to lead vehicle braking | 10/6/10 | SFM-ACT-003 |
| `SFM-012.C2` | Late reaction to lead vehicle braking | 10/6/8 | SFM-ACT-009 |
| `SFM-013.C1` | Engagement without driver request or with entry conditions not met | 10/6/8 | **none** |
| `SFM-013.C2` | Engagement without driver request or with entry conditions not met | 10/6/8 | SFM-ACT-003 |
| `SFM-014.C1` | Fails to disengage when a fault requires it | 10/8/10 | **none** |
| `SFM-014.C2` | Fails to disengage when a fault requires it | 10/8/9 | SFM-ACT-010 |
| `SFM-014.C3` | Fails to disengage when a fault requires it | 10/2/10 | **none** |
| `SFM-015.C1` | Abrupt disengagement without alert | 10/6/8 | SFM-ACT-007 |
| `SFM-015.C2` | Abrupt disengagement without alert | 10/6/10 | SFM-ACT-010 |
| `SFM-015.C3` | Abrupt disengagement without alert | 10/5/10 | SFM-ACT-003 |
| `SFM-016.C1` | Disengagement later than required by the fault | 10/8/9 | SFM-ACT-010 |
| `SFM-016.C2` | Disengagement later than required by the fault | 10/8/10 | SFM-ACT-010 |
| `SFM-017.C1` | Brake press does not disengage | 10/6/8 | SFM-ACT-003 |
| `SFM-017.C2` | Brake press does not disengage | 10/7/8 | **none** |
| `SFM-018.C1` | Item resists driver steering input | 10/6/8 | SFM-ACT-003 |
| `SFM-018.C2` | Item resists driver steering input | 10/8/9 | **none** |
| `SFM-019.C1` | Cancel button does not disengage | 10/6/8 | SFM-ACT-003 |
| `SFM-020.C1` | Accelerator override not honored | 10/6/8 | SFM-ACT-003 |
| `SFM-022.C1` | Inattentive driver not detected | 10/7/10 | SFM-ACT-009 |
| `SFM-022.C2` | Inattentive driver not detected | 10/6/8 | SFM-ACT-009 |
| `SFM-022.C3` | Inattentive driver not detected | 10/5/10 | SFM-ACT-003 |
| `SFM-023.C1` | Distraction escalation too slow | 10/6/8 | SFM-ACT-002 |
| `SFM-023.C2` | Distraction escalation too slow | 10/6/8 | SFM-ACT-002 |
| `SFM-025.C1` | Terminal driver-unresponsive state does not bring the item to a safe state | 10/8/10 | SFM-ACT-005 |
| `SFM-026.C1` | Takeover or disengagement alert not presented | 10/6/10 | SFM-ACT-007 |
| `SFM-026.C2` | Takeover or disengagement alert not presented | 10/6/8 | SFM-ACT-007, SFM-ACT-003 |
| `SFM-026.C3` | Takeover or disengagement alert not presented | 10/4/10 | SFM-ACT-007 |
| `SFM-027.C1` | Alert presented late | 10/6/10 | SFM-ACT-003 |
| `SFM-027.C2` | Alert presented late | 10/6/9 | **none** |
| `SFM-028.C1` | Displayed engagement state differs from actual state | 10/6/10 | SFM-ACT-007 |
| `SFM-028.C2` | Displayed engagement state differs from actual state | 10/6/9 | SFM-ACT-003 |
| `SFM-029.C1` | Actuator command limits not enforced | 10/8/9 | **none** |
| `SFM-029.C2` | Actuator command limits not enforced | 10/6/9 | SFM-ACT-001 |
| `SFM-029.C3` | Actuator command limits not enforced | 10/3/10 | **none** |
| `SFM-029.C4` | Actuator command limits not enforced | 10/2/10 | **none** |
| `SFM-030.C1` | Excessive actuation not detected | 10/5/8 | SFM-ACT-002 |
| `SFM-030.C2` | Excessive actuation not detected | 10/6/10 | **none** |
| `SFM-031.C1` | False excessive-actuation detection | 8/5/10 | SFM-ACT-003 |
| `SFM-032.C1` | Wrong vehicle configuration active (fingerprint or car port) | 10/5/8 | SFM-ACT-008 |
| `SFM-033.C1` | Stock safety functions unavailable or degraded while the item is installed | 10/6/10 | SFM-ACT-006 |
| `SFM-033.C2` | Stock safety functions unavailable or degraded while the item is installed | 10/5/3 | SFM-ACT-006 |
| `SFM-034.C1` | Harness relay fault | 10/3/10 | **none** |
| `SFM-034.C2` | Harness relay fault | 10/3/10 | **none** |
