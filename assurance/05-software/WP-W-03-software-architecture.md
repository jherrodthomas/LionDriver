# WP-W-03 Software Architectural Design

| Field | Value |
|---|---|
| Work product | WP-W-03 Software architectural design |
| Standard reference | ISO 26262-6:2018 §7 (software architectural design: notation, design principles, static and dynamic aspects, ASIL attribution, resource usage); ISO 26262-9:2018 §6 (coexistence, by reference to WP-A-02); ASPICE 4.0 SWE.2 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Envelope (E-03a/E-03b): B‡ (ASIL C until SG-01 re-rating, [WP-S-02 §2.1](../03-system/WP-S-02-technical-safety-requirements.md)); host (E-01): QM / QM (B-sup) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); I2 for §6 and §8 |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document describes the software architecture of LD-SDA as it exists at the baseline and marks the changes the SWSRs of [WP-W-02](WP-W-02-software-safety-requirements.md) require. It covers:

- (a) the panda firmware with the opendbc safety layer (E-03a/E-03b), which runs the safety envelope on the STM32H7;
- (b) the host stack on the SoC (E-01): the openpilot processes and cereal services that matter to safety.

It is the reference for the element catalogue used in allocations (`assurance/trace/elements.yaml`, [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md) OI-4), for the software safety analysis ([WP-W-04](WP-W-04-software-safety-analysis.md)), the unit design ([WP-W-05](WP-W-05-software-unit-design.md)) and the shared-data documentation required by [WP-W-01](WP-W-01-software-development-environment-guidelines.md) ENV-R-12 (OI-6 there; §6.3 here). System context: [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md). HSI: [WP-S-05](../03-system/WP-S-05-hsi-specification.md).

Notation (WP-W-01 §14): component tables, ASCII block diagrams, state-transition tables, data-flow tables. Paths as in WP-W-02 §2.2.

## 2. Architectural drivers

| Driver | Source | Consequence |
|---|---|---|
| Envelope independent of QM commands | AP-1, AP-5 (WP-S-03 §2) | All actuation passes `safety_tx_hook`; configuration must be locked (SWSR-512) |
| Fail-silent | AP-2 | One safe state SS-S reachable from every fault (SWSR-502) |
| Timing budgets 0.05–0.3 s | [WP-S-04](../03-system/WP-S-04-timing-ftti-budget.md) | Periodic safety task ≥ 50 Hz (SWSR-401a); current 1 Hz evaluation does not meet them |
| Single MCU, single address space | GAP-11 | FFI must be argued by software means and MPU (SWSR-507) |
| Reuse of upstream code | T-03 | Architecture back-filled; minimal structural change preferred |

## 3. Static architecture: panda firmware (E-03)

### 3.1 Component catalogue

Unit IDs U-xxx follow [WP-W-06 §2](WP-W-06-software-unit-verification.md). U-PND-USB, U-PND-PWR, U-PND-HK and U-PND-PLAT are new here (OI-1).

| Element name | Unit | Files | Responsibility | ASIL attribution |
|---|---|---|---|---|
| `panda.safety.core` | U-SAF-CORE | `safety.h` | Hook dispatch, RX checks, authority (`controls_allowed`), generic brake/gas edges, relay-malfunction detection, TX whitelist, forwarding rules, mode switching (`set_safety_hooks`), `safety_tick` | B‡ |
| `panda.safety.lateral` | U-SAF-LAT | `lateral.h` | Torque limit, rate, measured-torque, RT window, steer-request tolerance (angle/curvature checks unused in ref. config) | B‡ |
| `panda.safety.longitudinal` | U-SAF-LONG | `longitudinal.h` | Longitudinal allowed, accel bounds, inactive value | B |
| `panda.safety.helpers` | U-SAF-HELP | `helpers.h`, `declarations.h`, `can.h` | Macros, CRC8, message matching, timestamps, interpolation, packet type | B‡ |
| `panda.safety.toyota` | U-SAF-TOY | `modes/toyota.h` | Toyota RX parsing, TX checks, limits, init/param decoding | B‡ |
| `panda.safety.defaults` | U-SAF-DEF | `modes/defaults.h`, `modes/elm327.h` | SILENT/NOOUTPUT/ELM327 hooks | B‡ (safe-state modes) |
| `panda.safety.ignition` | U-SAF-IGN | `ignition.h` | CAN ignition detection | B (feeds heartbeat timeout choice, TSR-510) |
| `panda.safety.other_modes` | — | `modes/*.h` other brands | Not used by the reference configuration but linked and selectable via `0xdc` | Interference source until SWSR-512 locks the mode; then dead code to be removed or justified (OI-2) |
| `panda.main` | U-PND-MAIN | `main.c` | Start-up, `set_safety_mode`, tick ISR (8 Hz/1 Hz), heartbeat supervision, siren control, main idle loop | B‡ |
| `panda.main.safety_task` | U-PND-MAIN | (new) | Periodic safety task ≥ 50 Hz with watchdog checkpoint (SWSR-401a, 501) | B‡ (to be created) |
| `panda.comms` | U-PND-COMMS | `main_comms.h`, `can_comms.h` | Control-request dispatcher, health packet, CAN stream packing/unpacking | B‡ (it calls envelope APIs and can change configuration) |
| `panda.drivers.spi` | U-PND-SPI | `drivers/spi.h`, `stm32h7/llspi.h` | SPI framing, checksum, DMA control | B‡ |
| `panda.drivers.usb` | U-PND-USB | `drivers/usb.h`, `stm32h7/llusb.h` | USB endpoint handling; reaches the same comms handlers (`drivers/usb.h:575, 616, 700`) | Not needed by the reference device (SPI); interference source (OI-3) |
| `panda.drivers.fdcan` | U-PND-FDCAN | `drivers/fdcan.h`, `drivers/can_common.h`, `stm32h7/llfdcan.h` | CAN RX ISR (forward, RX hook, queue), TX path (`can_send` → TX hook → queue → FIFO), error handling | B‡ |
| `panda.drivers.harness` | U-PND-HARN | `drivers/harness.h` | Relay drive, orientation and ignition sense | B‡ (blocking) / B (PCS restore) |
| `panda.sys.faults` | U-PND-FLT | `sys/faults.h`, `drivers/simple_watchdog.h`, `drivers/registers.h`, `drivers/interrupts.h` | Fault recording, software watchdog, register check, interrupt-rate supervision | B‡ |
| `panda.sys.power_saving` | U-PND-PWR | `sys/power_saving.h` | Power-save: CAN IRQ and transceiver disable | B‡ (can stop camera-side forwarding, WP-A-02 FFI-CM-08) |
| `panda.drivers.siren` / housekeeping | U-PND-HK | `drivers/fake_siren.h`, `stm32h7/sound.h`, `drivers/{fan,led,bootkick,clock_source,pwm}.h`, `stm32h7/lldts.h`, ADC | Siren (B, TSR-516); others QM | Mixed: siren B, rest QM |
| `panda.platform` | U-PND-PLAT | `stm32h7/startup_stm32h7x5xx.s`, `early_init.h`, `stm32h7/{clock,peripherals,interrupt_handlers,llflash}.h`, `drivers/timers.h`, `sys/critical.h` | Reset, exception handlers, clocks, vectors, timers, critical sections | B‡ |
| `panda.bootstub` | U-PND-BOOT | `bootstub.c`, `crypto/*`, `flasher.h` | Signature check, soft flasher | B‡ + CS |

### 3.2 Block diagram

```
          SoC (pandad)                       panda STM32H7 (one address space, no MPU)
   ───────────────────────────    ┌───────────────────────────────────────────────────────────────┐
     SPI4 transfers  ─────────────┼─▶ U-PND-SPI ──ctrl──▶ U-PND-COMMS comms_control_handler        │
     (hdr+data, XOR)              │     │                    │ 0xdc ─▶ U-PND-MAIN set_safety_mode  │
                                  │     │                    │           └▶ U-SAF-CORE set_safety_hooks
                                  │     │                    │ 0xf3 ─▶ heartbeat vars               │
                                  │     │                    └ 0xc5 ─▶ U-PND-HARN relay (ungated)   │
                                  │     └─can write─▶ comms_can_write ─▶ can_send ─▶ safety_tx_hook │
                                  │                                        (U-SAF-CORE→U-SAF-TOY→  │
                                  │                                         U-SAF-LAT/LONG)        │
                                  │                                          │ accept   │ reject   │
                                  │                       can_queues[bus] ◀──┘          └▶ rx_q    │
                                  │                            │ process_can (XOR check)            │
   bus 0 car side ◀═══════════════╪══ FDCAN1/3 TX FIFO ◀───────┘                                   │
   bus 0/2 RX ════════════════════╪══▶ can_rx: safety_fwd_hook ─▶ can_send(skip hook) other bus    │
                                  │            safety_rx_hook ─▶ U-SAF-TOY rx ─▶ controls_allowed   │
                                  │            can_push(rx_q) ─▶ comms_can_read ─▶ SPI to SoC      │
                                  │  TIM12 tick ISR 8 Hz: harness_tick, simple_watchdog_kick, siren │
                                  │     └ 1 Hz: heartbeat checks, check_registers, safety_tick     │
                                  │  TIM6 1 Hz: interrupt-rate statistics                           │
                                  │  main loop: LED fade / WFI only                                 │
                                  └───────────────────────────────────────────────────────────────┘
```

### 3.3 Interfaces between components

| ID | Provider → user | Interface | Data | Safety relevance |
|---|---|---|---|---|
| SI-01 | U-SAF-CORE → U-PND-FDCAN | `safety_rx_hook(const CANPacket_t*)`, `safety_fwd_hook(bus, addr)` | RX frame; return validity / destination bus | B‡ |
| SI-02 | U-SAF-CORE → U-PND-FDCAN (`can_send`) | `safety_tx_hook(CANPacket_t*)` | TX frame; accept/reject | B‡ |
| SI-03 | U-SAF-CORE → U-PND-MAIN | `set_safety_hooks(mode, param)`, `safety_tick()` | mode, param; return status | B‡ |
| SI-04 | U-SAF-CORE → U-PND-COMMS/MAIN | globals: `controls_allowed`, `relay_malfunction`, `safety_rx_checks_invalid`, `heartbeat_engaged`, `heartbeat_engaged_mismatches`, `current_safety_mode/param`, `safety_mode_cnt`, `alternative_experience` | shared state (§6.3) | B‡ |
| SI-05 | U-SAF-TOY → U-SAF-CORE | `toyota_hooks` table (`modes/toyota.h:431-438`) | function pointers init/rx/tx/checksum/quality | B‡ (ENV-R-06: constant table) |
| SI-06 | U-SAF-LAT/LONG → U-SAF-TOY | `steer_torque_cmd_checks`, `longitudinal_accel_checks` | value, limits struct; violation flag | B‡ |
| SI-07 | U-PND-SPI → U-PND-COMMS | `comms_control_handler`, `comms_can_write`, `comms_can_read` | `ControlPacket_t`; byte streams | B‡ |
| SI-08 | U-PND-COMMS → U-PND-MAIN | `set_safety_mode` prototype (`main_comms.h:6`) | mode/param | B‡ |
| SI-09 | U-PND-FDCAN ↔ U-PND-COMMS | `can_rx_q`, `can_queues[]` ring buffers with `can_push`/`can_pop` | `CANPacket_t` | B‡ |
| SI-10 | U-PND-HARN → U-PND-MAIN/COMMS | `set_intercept_relay`, `harness.status`, `harness_check_ignition` | relay, orientation | B‡/B |
| SI-11 | U-PND-FLT → all | `fault_occurred`, `fault_recovered`, `faults`, `REGISTER_INTERRUPT` | fault bits | B‡ (report-only today) |
| SI-12 | Platform → all | `microsecond_timer_get` (TIM2-based µs counter), `ENTER_CRITICAL/EXIT_CRITICAL` | time base, IRQ masking | B‡ |
| SI-13 | U-PND-COMMS → SoC | health packet `0xd2` (`main_comms.h:9-55`) | flags, counters, faults | QM consumer (SWSR-615) |

## 4. Static architecture: host stack (E-01)

### 4.1 Components relevant to safety

| Element name | Process / module | Role | Class | SWSRs |
|---|---|---|---|---|
| `host.pandad` | `selfdrive/pandad/{pandad.py, pandad.cc, panda.cc, spi.cc, panda_safety.cc}` | Firmware check/flash, SPI link, CAN in/out, heartbeat, safety-mode set | QM (B-sup); FFI interface | 409h, 410h, 414h, 514h |
| `host.card` | `selfdrive/car/card.py` + `opendbc/car/toyota/{carcontroller,carstate,interface,values}.py` | CAN parse → `carState`; `carControl` → `sendcan`; CarParams/fingerprint | QM (B-sup) | 303h, 605, 607 |
| `host.controlsd` | `selfdrive/controls/controlsd.py` | Lateral/longitudinal control law | QM (B-sup) | 602, 604, 605 |
| `host.selfdrived` | `selfdrive/selfdrived/{selfdrived,events,state}.py` | Engagement state machine, event classification, alerts | QM (B-sup) | 307h, 308h, 601, 603, 606, 615, 617, 618 |
| `host.plannerd`, `host.radard` | `selfdrive/controls/plannerd.py`, `radard.py` | Longitudinal plan, lead fusion | QM (SOTIF) | — |
| `host.modeld` | `selfdrive/modeld/modeld.py` | Driving model | QM (SOTIF / PAS 8800) | 603, 616 |
| `host.dm` | `dmonitoringmodeld.py`, `selfdrive/monitoring/{dmonitoringd,policy}.py` | Driver monitoring | QM (SOTIF) | 608–612 |
| `host.hmi` | `ui`, `soundd` | Alerts | QM (B-sup) | 606 |
| `host.manager` | `system/manager/{manager,process_config}.py` | Process start/stop by run condition | QM | 613 |
| `host.cereal` | `cereal/`, `msgq` | Pub/sub, alive/valid/freq checks | QM | 601a |

### 4.2 Data flow (per control frame)

Rates from `cereal/services.py`. Consumers and alive limits as in [WP-S-03 §9](../03-system/WP-S-03-technical-safety-concept-architecture.md).

| Producer → service → consumer | Rate | Safety use | Freshness today | Required |
|---|---|---|---|---|
| modeld → `modelV2` → controlsd, plannerd, selfdrived | 20 Hz | desired path/curvature | alive 0.5 s | ≤ 100 ms (SWSR-602) |
| plannerd → `longitudinalPlan` → controlsd | 20 Hz | accel target | 0.5 s | ≤ 100 ms |
| card → `carState` → controlsd, selfdrived | 100 Hz | vehicle state | 0.1 s | ≤ 20 ms |
| selfdrived → `selfdriveState` → controlsd, pandad | 100 Hz | enabled/active | 0.1 s | — |
| controlsd → `carControl` → card | 100 Hz | actuator request | card sends only if alive (`selfdrive/car/card.py:234-238`) | — |
| card → `sendcan` → pandad → SPI → panda | 100 Hz | CAN frames | pandad drops > 1 s (`pandad.cc:78-79`) | 20 ms (SWSR-414h) |
| pandad → `0xf3` heartbeat → panda | 10 Hz | engaged flag | panda 1 Hz evaluation | 0.3 s + loop counter (SWSR-407, 409) |
| panda → health → pandad → `pandaStates` → selfdrived | 10 Hz | authority, faults | mismatch 2 s | 0.3 s (SWSR-307h) |

## 5. Dynamic behaviour

### 5.1 Execution model of the panda firmware

All envelope processing runs in **interrupt context**. The main loop (`main.c:331-362`) only fades the LED or waits in `__WFI()`.

| Context | Trigger | Code executed | Envelope functions called |
|---|---|---|---|
| FDCANx IT0 (RX) | frame received, per bus | `can_rx` (`drivers/fdcan.h:154-243`) | `safety_fwd_hook`, `safety_rx_hook`, `ignition_can_hook` |
| FDCANx IT1 (TX) | TX FIFO empty / `process_can` | `process_can` (`drivers/fdcan.h:88-150`) | none (XOR check only) |
| DMA2 Stream2 (SPI RX done) | end of MOSI DMA | `spi_rx_done` (`drivers/spi.h:106-223`) via `stm32h7/llspi.h:56-61` | via `comms_control_handler`: `set_safety_mode` → `set_safety_hooks`; via `comms_can_write`: `safety_tx_hook` |
| DMA2 Stream3, SPI4 | MISO done | `spi_tx_done` | none |
| USB OTG | USB transfer | `drivers/usb.h` | same comms handlers |
| TIM12 tick | 8 Hz (`drivers/timers.h:30-31`) | `tick_handler` (`main.c:106-249`) | 1 Hz: heartbeat logic, `check_registers`, `safety_tick`; 8 Hz: harness, watchdog kick, siren |
| TIM6 | 1 Hz | `interrupt_timer_handler` (`drivers/interrupts.h:50-72`) | rate statistics |
| NMI / HardFault | exception | `early_init.h:73-81` | reset |

**Priorities.** No `NVIC_SetPriority` call exists in `panda/board`, so all peripheral interrupts run at the reset-default priority. Equal priority means no preemption between them: each handler runs to completion and pending handlers are served in exception-number order. Consequences: (i) envelope state is never accessed concurrently, which makes the single-writer argument of §6.3 simple; (ii) a long handler (e.g. a CAN burst or `set_safety_mode` → `can_init_all`) delays every other handler, including the tick; (iii) the tick cannot preempt a hung handler, so only a hardware watchdog can detect it (SWSR-501). `ENTER_CRITICAL` masks all interrupts (`sys/sys.h:11-22`). This finding matches [WP-A-02](../08-analyses/WP-A-02-coexistence-freedom-from-interference.md) FFI-SP-04 and GAP-50; TSR-519 / SWSR-519 require an explicit priority and timing scheme.

### 5.2 Tick schedule (baseline)

| Period | Activity | Lines |
|---|---|---|
| 125 ms | siren toggle, `fan_tick`, `harness_tick` (ADC orientation when relay not driven), `simple_watchdog_kick`, `sound_tick`, relay-fault reporting, harness re-init on change | `main.c:113-140` |
| 1 s | LEDs, ignition, `bootkick_tick`, heartbeat counter, `heartbeat_engaged` mismatch (3 ticks), heartbeat loss → SILENT (5 s ign on / 2 s off), siren countdown, `check_registers`, CAN ignition timeout, counters, `safety_tick` (RX timeouts) | `main.c:143-243` |

Required schedule (SWSR-401a, 501): a dedicated timer at ≥ 50 Hz running `safety_tick`, heartbeat, command freshness, SPI error rate, relay readback, platform monitors; IWDG serviced at its end. The 8 Hz/1 Hz tick keeps housekeeping only. The safety task's interrupt priority shall be higher than the comms interrupts, which requires the shared-data scheme of §6.3 to be revisited (OI-4).

### 5.3 Message flow per control frame (lateral, 10 ms)

1. `card` packs `0x2E4` into `sendcan`; `pandad` send thread checks age < 1 s and writes it over SPI endpoint 3.
2. DMA2 Stream2 IRQ → `spi_rx_done`: header XOR checked (`drivers/spi.h:122`), then data DMA of `spi_data_len_mosi + 1` bytes (`:233`), then data XOR (`:137`).
3. `comms_can_write` reassembles `CANPacket_t` (`can_comms.h:83-129`) → `can_send(…, false)` (`drivers/can_common.h:161`).
4. `safety_tx_hook`: whitelist (`safety.h:230-239`) → `toyota_tx_hook` → `steer_torque_cmd_checks` (`lateral.h:60-151`) → relay check (`safety.h:252`).
5. Accept: `can_push(can_queues[0])`, `process_can` writes the FDCAN TX FIFO after the packet XOR check (`drivers/fdcan.h:100`) and echoes the frame to `rx_q`. Reject: `safety_tx_blocked++`, frame returned to `rx_q` with `rejected=1`.
6. EPS answers on `0x260` at 50 Hz → FDCAN RX ISR → forwarded to bus 2 → `safety_rx_hook` updates `torque_meas` used by the next check.

Worst-case latency step 2→5 is to be measured (VS-SWI-15, VS-SWQ-23).

### 5.4 Start-up and mode-set sequence

| Step | Actor | Action | Lines |
|---|---|---|---|
| 1 | bootstub | length, SHA-1, RSA-1024 check, jump or soft flasher | `bootstub.c:33-82` |
| 2 | main | interrupt table, clocks, peripherals, board detect, ADC, DTS | `main.c:253-267` |
| 3 | main | board init, `harness_init` (relay released) | `main.c:280-282` |
| 4 | main | `set_safety_mode(SILENT)`; CAN transceivers on; software watchdog; tick timer; USB; SPI | `main.c:295-313` |
| 5 | main | interrupts enabled; idle loop | `main.c:328-362` |
| 6 | pandad | SILENT → NOOUTPUT; onroad → ELM327 (fingerprinting) | `selfdrive/pandad/panda_safety.cc:23-34` |
| 7 | card / pandad | CarParams → `0xdc` TOYOTA, param 73 | `panda_safety.cc:56-69` |
| 8 | panda | `set_safety_hooks` resets state; relay driven; CAN re-init | `main.c:70-78`; `safety.h:391-482` |
| 9 | PCM | CRUISE_ACTIVE rising edge → `controls_allowed = true` | `safety.h:518-527` |

Required: start-up tests (SWSR-515) between steps 4 and 8; IWDG started in step 1 (SWSR-501b); step 7 restricted by the mode lock (SWSR-512).

### 5.5 Safety-mode state machine (panda)

| State | Relay | CAN | Entry | Exit |
|---|---|---|---|---|
| SILENT | released | silent | reset, heartbeat loss, failed mode set | `0xdc` any mode |
| NOOUTPUT | released | normal, TX hook rejects all | `0xdc` | `0xdc` |
| ELM327 | released | OBD mux per param | `0xdc` | `0xdc` |
| TOYOTA | driven | normal | `0xdc` 2/73 | `0xdc` (any, today); heartbeat loss → SILENT |

Required (SWSR-512): TOYOTA exits only to SILENT/NOOUTPUT; new fault state SS-S (= SILENT + latch) reachable from every state (SWSR-502).

## 6. Partitioning and freedom from interference at software level

### 6.1 Mechanisms present

| Mechanism | Effect | Evidence |
|---|---|---|
| Single entry for actuation | Every SoC frame passes `safety_tx_hook`; forwarded frames skip it but use the static block list | `drivers/can_common.h:161-162`; `drivers/fdcan.h:213`; `safety.h:267-288` |
| Constant hook table | Brand behaviour selected only through `set_safety_hooks` | `safety.h:391-482` |
| Run-to-completion ISRs at one priority | No concurrent access to envelope state | §5.1 |
| Critical sections on ring buffers | Queue integrity | `drivers/can_common.h:42-103` |
| Packet XOR from TX hook to FIFO | Detects corruption in the TX queue | `drivers/fdcan.h:100` |
| Memory placement | SPI buffers in SRAM1/2, RX queue in AXI SRAM, TX queues 1–2 in ITCM | `drivers/spi.h:7-8`; `drivers/can_common.h:27-35` |

### 6.2 Mechanisms missing

| Missing | Consequence | SWSR |
|---|---|---|
| MPU configuration | Any comms defect can overwrite envelope state | 507 |
| Bounds checks on SoC lengths/indices | DMA/array overrun from the QM SoC | 412, 412a, 412b |
| Hardware watchdog with logical checkpoint | Hangs undetected | 501, 501b |
| Temporal isolation | Comms interrupt load can delay safety checks without bound | 401a, 502b |
| Configuration lock and command gating | QM SoC configures the envelope | 512, 513 |
| Removal of unused brand modes and USB path | Larger interference surface | OI-2, OI-3 |

### 6.3 Shared data between contexts (ENV-R-12)

| Data | Writers (context) | Readers | Protection today | Required |
|---|---|---|---|---|
| `controls_allowed` | RX ISR (`pcm_cruise_check`, `generic_rx_checks`, `is_msg_valid`), tick ISR (`safety_tick`, `main.c:185`), SPI ISR via `set_safety_hooks` | TX hook (SPI ISR), health | Equal priority (no preemption) | Single writer API `safety_revoke(reason)` / grant only in RX path; keep under any new priority scheme |
| `heartbeat_engaged`, `heartbeat_counter`, `heartbeat_lost` | SPI ISR (`0xf3`), tick ISR | tick ISR | Equal priority | As above; counter in safety task |
| `current_safety_mode/param`, `current_hooks`, `current_safety_config` | SPI ISR (`0xdc`), tick ISR (heartbeat loss) | all hooks | Equal priority | MPU-protected after lock (SWSR-507, 512) |
| `relay_malfunction` | RX ISR, `set_safety_hooks` | TX hook, fwd hook, tick | Equal priority | Latch not clearable by `0xdc` (SWSR-506a) |
| `torque_meas`, `torque_driver`, `vehicle_speed`, `desired_torque_last`, `rt_torque_last` | RX ISR / TX path | TX path | Equal priority | — |
| `can_rx_q`, `can_queues[]` | RX ISR, TX path, SPI ISR | SPI ISR, FDCAN IT1 | Critical sections | Overflow → fault (SWSR-707) |
| `faults`, `fault_status` | any ISR | health | none (bit OR) | Fault reaction (SWSR-502) |
| `spi_buf_rx/tx` | DMA, SPI ISR | SPI ISR | state machine | Length bounds (SWSR-412) |

## 7. Resource usage (estimates, to be measured)

Values computed from source and linker script; **not measured**. Measurement: VS-SWI-15 and VS-SWQ-23.

| Resource | Estimate | Basis |
|---|---|---|
| `CANPacket_t` | 72 B (70 B packed, aligned 4) | `can.h:8-18` |
| CAN RX queue | 4096 × 72 B ≈ 288 KiB of 320 KiB AXI SRAM | `drivers/can_common.h:22, 27`; `stm32h7/stm32h7x5_flash.ld:73` |
| CAN TX queues 1, 2 | 2 × 416 × 72 B ≈ 58.5 KiB of 64 KiB ITCM | `drivers/can_common.h:23, 28-29`; `.ld:79` |
| SPI buffers | 2 × 4096 B in 32 KiB SRAM1/2 | `drivers/drivers.h:216`; `.ld:72` |
| Stack | single main stack, minimum 1 KiB checked by linker; actual usage unknown | `.ld:64`; WP-W-01 ENV-R-14 |
| CPU load | `interrupt_load` measured by firmware and reported in health | `drivers/interrupts.h:63-67`; `main_comms.h:41-42` |
| Interrupt-rate limits | CAN 16000/s, SPI 16000/s (SPI4 32000/s), tick 10/s | `stm32h7/stm32h7_config.h:28`; `drivers/drivers.h:214`; `main.c:304` |
| WCET of hooks | unknown | VS-UV-21 |

## 8. Architectural design principles assessment

ISO 26262-6 §7 lists design principles with recommendation levels per ASIL; the levels are taken from the licensed copy (OI-5). Assessment for E-03:

| Principle | Assessment at baseline | Rating | Action |
|---|---|---|---|
| Appropriate hierarchical structure | Two layers (safety layer vs platform) are clear; inside the platform, `main_comms.h` mixes safety-relevant and housekeeping requests | Partial | Split control requests into safety-relevant and QM groups (SWSR-513) |
| Restricted size and complexity of components | Safety layer ≈ 1.4 kLOC for the reference path (`safety.h` 537, `lateral.h` 409, `toyota.h` 438 lines); `comms_control_handler` is one 260-line switch; `tick_handler` 144 lines | Partial | Complexity metric (WP-W-01 OI-5); split `tick_handler` |
| Restricted size of interfaces | Hooks have narrow signatures, but much state is shared as globals (§6.3) | Partial | Accessor functions for authority |
| Strong cohesion | Safety layer cohesive; `tick_handler` mixes housekeeping with safety supervision | Partial | Separate safety task (SWSR-401a) |
| Loose coupling | Safety core coupled to all brand modes via compile-time inclusion | Partial | Build only required modes (OI-2) |
| Appropriate scheduling properties | No periodic safety task; 1 Hz timeout evaluation; equal priorities (GAP-50) | **No** | SWSR-401a, 501, 519 |
| Restricted use of interrupts | Whole envelope runs in ISRs; no priorities | **No** (to be justified or changed) | Documented priority scheme (OI-4) |
| Appropriate spatial isolation | No MPU | **No** | SWSR-507 |
| Appropriate management of shared resources | Ring buffers protected; globals rely on equal priority | Partial | §6.3 |

## 9. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Add U-PND-USB, U-PND-PWR, U-PND-HK, U-PND-PLAT to the WP-W-06 unit list | Safety engineer | G3 |
| OI-2 | Remove unused brand modes from the reference firmware build or justify them (WP-A-02 OI-2) | SW lead | G3 |
| OI-3 | Decide whether USB comms are disabled in the reference build | SW lead | G3 |
| OI-4 | Define the NVIC priority scheme for the new safety task (SWSR-519) and re-assess §6.3 | SW architect | G3 |
| OI-5 | Check principle recommendation levels against the licensed ISO 26262-6 | Safety engineer | G3 |
| OI-6 | Measure the resource estimates of §7 from the map file and on target | Maintainer | G4 |
| OI-7 | Create `elements.yaml` from §3.1 and §4.1 (WP-P-06 OI-4) | Safety engineer | G3 |
