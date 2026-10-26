# WP-S-05 Hardware-Software Interface (HSI) Specification

| Field | Value |
|---|---|
| Work product | WP-S-05 Hardware-software interface specification |
| Standard reference | ISO 26262-4:2018 §6 (HSI specification); ISO 26262-5:2018 §6 and ISO 26262-6:2018 §6 (HSI refinement, by reference); ASPICE 4.0 SYS.3 |
| Version | 0.17 (OI-2: CRC from a residual-error target, DQ-143 A; OI-3: per-mode request list derived from TSR-512/513 and CSR-011…016, DQ-144 A; 2026-10-26). 0.16 (§4.2: Figure 4-1, the control requests by required treatment and baseline gating, generated from the table; 2026-10-25). 0.15 (OI-8 closed: the network assumption is WP-C-01 AOU-18, lead decision DQ-419 A (next vehicles stay on unsigned classical CAN and ISO CAN FD passenger cars); §12.1 and §12.6 updated; I0, Claude; 2026-10-25). 0.14 (§12 added: vehicle networks and end-to-end protection, hop by hop, with OI-8…OI-12; no requirement changed; I0, Claude; 2026-10-24). 0.13 (OI-6: both boards stay in scope, DQ-011; 2026-10-23). 0.12 (§2 ASIL column: each interface carries the highest ASIL of its TSRs, C for the MCU interfaces since WP-C-03 v0.4 (the column still showed B‡), B for orientation and ignition; Figure 2-1 added, generated from §2; 2026-10-19). 0.11 (scope line: the MCU interfaces are ASIL C since WP-C-03 v0.4 raised SG-02, SG-03 and SG-06; 2026-10-16). 0.10 (§11: bit numbering defined; provisional bit positions for S-06, S-07 quality flag, S-12, S-13 MAIN_ON; LC-01, maintainer decision 2026-10-13). 0.9 (S-21: reference-build flag in the health packet, required by `pandad`; panda `6dee6fa`; 2026-10-12). 0.8 (HSI-09: IWDG1 now used, per TSR-501 v0.4; RR-2026-008; 2026-10-12). 0.7 (S-12: siren on a persistent EPS fault, panda `b790fca`; 2026-10-12). 0.6 (S-13: MAIN_ON cross-check implemented in the reference build, opendbc `875e325`; 2026-10-12). 0.5 (S-12: EPS fault reported to the host as `pandaState.epsFault`, panda `877730e`, opendbc `adcb7c2`; 2026-10-12). 0.4 (S-12: EPS fault codes evaluated by the envelope in the reference build, opendbc `242d63d`; 2026-10-12). 0.3 (S-12, S-13: `0x262` and `0x1D3` supervised in the reference build, opendbc `98404a4`; 2026-10-12). 0.2 (§11 signal catalogue, RR-2026-005 F-06; watchdog ≤ 0.1 s; 2026-10-12) |
| Status | Draft |
| ASIL / scope | Safety MCU (STM32H7 "panda") and its interfaces: ASIL C (SG-02, SG-03, SG-06 since WP-C-03 v0.4; see [WP-S-02 §2.1](WP-S-02-technical-safety-requirements.md)) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); HW lead and SW lead jointly |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (panda `92eb565`, opendbc `229dc70`) |

## 1. Purpose and scope

This document specifies the interfaces between hardware and software that the safety concept relies on:

- the SoC ↔ safety-MCU link (SPI protocol, control requests, CAN packet format, checksums), §4;
- the safety MCU ↔ CAN transceivers and vehicle buses, §5;
- harness relay drive, harness orientation and ignition sensing, §6;
- reset and boot control of the safety MCU by the SoC, watchdog and fault handling resources, §7;
- the safety-relevant memory map, §8;
- operating modes and power states, §9;
- the vehicle networks and the end-to-end protection of the information on them, §12.

All facts are taken from the firmware source at the baseline. **Pin assignments and electrical behaviour must be confirmed against the device schematic** ([WP-H-02](../04-hardware/WP-H-02-hardware-design.md) OI-1); firmware shows only what the MCU drives or reads. Both board variants are listed: "tres" (comma 3X) and "cuatro" (comma four). Which one is the reference device is open ([WP-C-01](../02-concept/WP-C-01-item-definition.md) OI-2).

Paths are under `panda/board/` unless prefixed. HSI IDs (HSI-nn) are referenced from SWSRs ([WP-W-02](../05-software/WP-W-02-software-safety-requirements.md)) and HWSRs ([WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md), whose §6 proposed the hardware entries that this document adopts).

## 2. Interface summary

| HSI | Interface | HW resource | SW owner | Safety relevance | ASIL | TSR / HWSR |
|---|---|---|---|---|---|---|
| HSI-01 | SoC ↔ MCU SPI link | SPI4, DMA2 streams 2/3, SRAM1/2 buffers | `drivers/spi.h`, `stm32h7/llspi.h`; host `openpilot/selfdrive/pandad/spi.cc` | FFI; carries commands and configuration | C | TSR-407…413; HWSR-401 |
| HSI-02 | Control requests over SPI endpoint 0 | — | `main_comms.h:63-322` | Mode set, heartbeat, relay debug, CAN config | C | TSR-407, 409, 511…513 |
| HSI-03 | CAN packet stream over SPI endpoints 1/3 | SPI4 | `can_comms.h` | Actuation commands, RX data to SoC | C | TSR-410, 411 |
| HSI-04 | FDCAN1–3 and transceivers | FDCAN, transceiver enable GPIOs | `drivers/fdcan.h`, `stm32h7/llfdcan.h`, `boards/*.h` | Actuation TX, RX for gating, forwarding | C | TSR-401…406, 508, 704, 707; HWSR-508 |
| HSI-05 | Harness relay drive | GPIO (open-drain, active-low) | `drivers/harness.h` | Blocks camera actuation; restores PCS path | C / B | TSR-506, 706; HWSR-506 |
| HSI-06 | Harness orientation sense | ADC1 ch4/ch17 on SBU1/SBU2 | `drivers/harness.h` | CAN routing, relay pin mapping | B | TSR-701; HWSR-701 |
| HSI-07 | Ignition line | SBU GPIO input | `drivers/harness.h:35-52` | Heartbeat timeout selection, power states | B | TSR-510; HWSR-510 |
| HSI-08 | Reset / boot pins from SoC | SoC GPIO → MCU NRST, BOOT0 | `openpilot/common/hardware/comma/hardware.py:400-419` | Firmware substitution; safe state on reset | C (+CS) | TSR-502, 511; HWSR-502c |
| HSI-09 | Watchdog | IWDG1 (window mode, 90 ms nominal, started at the first relay energisation; panda `3859fa8`), software timestamp check | `stm32h7/stm32h7_config.h:43`, `drivers/hw_watchdog.h`, `drivers/harness.h`, `drivers/simple_watchdog.h` | MCU hang detection | C | TSR-501; HWSR-501 |
| HSI-10 | Fault / health monitors | NVIC, RCC CSS, DTS, ADC, interrupt-rate counters | `sys/faults.h`, `drivers/interrupts.h`, `drivers/registers.h`, `stm32h7/lldts.h` | Platform fault detection | C | TSR-502…505, 509 |
| HSI-11 | Siren | DAC/DMA + codec over I2C5 (board-dependent) | `drivers/fake_siren.h`, `boards/*.h` | SoC-independent warning | C | TSR-516 |
| HSI-12 | Flash and bootstub | Flash bank 1, sector 0 bootstub, app at `0x08020000` | `bootstub.c`, `flasher.h`, `stm32h7/llflash.h` | Firmware integrity | C (+CS) | TSR-503, 511, 514 |
| HSI-13 | Supply measurement | ADC1 (input divider) | `boards/*.h` | Supply monitoring | C | TSR-505; HWSR-505b |
| HSI-14 | MPU, RAM ECC (to be added) | Cortex-M7 MPU, RAMECC | new | Memory protection | C | TSR-503, 507 |

![Figure 2-1: the safety MCU (STM32H7, E-04a hardware running the E-03 firmware, ASIL C) with its 14 hardware-software interfaces: HSI-01, -02, -03 and -08 link it to the SoC (QM); HSI-09, -10, -12, -13 and -14 are inside the MCU; HSI-04 leads to the vehicle CAN buses, HSI-05, -06 and -07 to the harness and HSI-11 to the shared speaker; 12 interfaces are ASIL C, orientation and ignition sensing are ASIL B](figures/fig-s05-2-1-hsi-overview.svg)

*Figure 2-1.* The rows of this table by where each interface leads: to the SoC (left), inside the MCU (middle), or to the vehicle buses, the harness and the speaker (right). Each card carries the ASIL and the TSR / HWSR column of its row; HSI-14 is dashed because it is not in the firmware yet. Generated from this table by [`figures/fig_s05_hsi.py`](figures/fig_s05_hsi.py), which fails CI when a row is added that the figure does not place; only the placement is fixed in the script.

## 3. Electrical and timing parameters (to be confirmed)

| Parameter | Value at baseline | Source | Confirmation |
|---|---|---|---|
| SPI clock | 50 MHz (host setting) | `openpilot/selfdrive/pandad/spi.cc:67` | Datasheet limits of SPI4 slave mode |
| SPI mode | Mode 0, 8-bit | `spi.cc:62`; `stm32h7/llspi.h:102` | — |
| SPI buffer size | MCU 4096 B (`drivers/drivers.h:216`); host 2048 B (`openpilot/selfdrive/pandad/panda_comms.h:11`) | — | Sizes differ; MCU must not rely on host limit (TSR-412) |
| CAN bit rate | 500 kbit/s default (`can_speed = 5000` in units of 100 bit/s, `drivers/can_common.h:116-120`) | — | Reference vehicle bus rates |
| Tick timer | TIM12, 8 Hz | `stm32h7/stm32h7_config.h:35-36`; `drivers/timers.h:30-32` | Must become ≥ 50 Hz safety task (WP-S-04 §5) |
| Relay drive | open-drain, low = energised | `drivers/harness.h:22-28, 98-101` | Driver circuit and coil supply (HWSR-506) |

## 4. SoC ↔ safety MCU SPI protocol (HSI-01…03)

### 4.1 Transfer format

| Phase | Direction | Bytes | Content | Check |
|---|---|---|---|---|
| Header | SoC → MCU | 7 | `0x5A` sync, endpoint (1), MOSI length (2, LE), max MISO length (2, LE), checksum (1) | XOR of all 7 bytes with seed `0xAB` = 0 (`drivers/spi.h:97-104, 121-133`) |
| Header ACK | MCU → SoC | 1 | `0x79` ACK or `0x1F` NACK | — |
| Data | SoC → MCU | MOSI length + 1 | payload + checksum | XOR seed `0xAB` (`drivers/spi.h:137`) |
| Data response | MCU → SoC | 3 + n + 1 | `0x85` DACK, length (2, LE), payload, checksum | XOR seed `0xAB` (`drivers/spi.h:192-202`); host checks (`spi.cc:383`) |
| Version request | SoC → MCU | `"VERSION"` | returns UID, HW type, bootstub flag, protocol version 2 | CRC-8 poly `0xD5` (`drivers/spi.h:44-86`) |

Endpoints (`drivers/spi.h:139-180`): 0 control request; 1/0x81 CAN read; 2 bootstub flashing write (no-op in the application, `main_comms.h:58-61`); 3 CAN write (accepted only when TX buffer space is available, else NACK); 0xAB/0xAC test endpoints.

Host behaviour: ACK timeout 500 ms per wait (`spi.cc:30, 241-276`); retries until more than 5 timeouts (`spi.cc:205-236`).

**Safety assessment.** An 8-bit XOR detects all odd-numbered bit errors in a column but misses many even-weight and burst patterns; no sequence counter, no freshness. Required (TSR-410, 411): CRC with a residual error probability meeting the target below, plus a sequence counter on endpoint 3. Lengths must be bounds-checked by the MCU (TSR-412, NF-04: `drivers/spi.h:115-116, 150, 233`).

Residual error target (proposal, OI-2): probability of an undetected corrupted actuation transfer < 10⁻⁹ per hour of operation at 100 transfers/s and an assumed raw bit error rate to be measured (M-04 of WP-S-04 provides the link stress test). A CRC-16 (Hamming distance ≥ 4 over ≤ 4096 bytes is not guaranteed) or CRC-32 is to be chosen by analysis.

### 4.2 Control requests (endpoint 0)

`ControlPacket_t` = request (1 B), param1 (2 B), param2 (2 B), length (2 B), packed (`comms_definitions.h`). Handler `comms_control_handler` (`main_comms.h:63-322`).

| Req | Function | Effect on safety | Gating at baseline | Required (release, car safety mode active) | TSR |
|---|---|---|---|---|---|
| `0xa8` | read microsecond timer | none | none | allow | — |
| `0xb0` | set IR power | none (DM camera illumination: SOTIF) | none | allow | — |
| `0xb1` / `0xb2` | fan power / rpm | thermal | none | allow | 509 |
| `0xb5` | deep sleep | enters SILENT, power save | `ALLOW_DEBUG` only (`:92-98`) | absent | 514 |
| `0xb6` | read debug log | none | none | allow | — |
| `0xc0` | reset comms buffers | may drop a partial CAN packet | none | allow (logged) | 410 |
| `0xc1`, `0xc3`, `0xd0`, `0xd3`, `0xd4`, `0xd6`, `0xdd` | read HW type, UID, serial, signature, version, packet versions | none | none | allow | 514 (version shows build type) |
| `0xc2` | CAN health | none | bounds-checked (`:117`) | allow | — |
| `0xc4` | interrupt call rate | none | bounds-checked (`:135`) | allow | — |
| **`0xc5`** | **drive relay / ignition relay** | **can release or engage relay at any time** | **none** (`:144-147`) | **reject** | 513, 506 |
| `0xc6` | read SoC GPIO | none | none | allow | — |
| **`0xd1`** | bootloader (param 0) / softloader (param 1) | firmware replacement | param 0 `ALLOW_DEBUG`; **param 1 none** (`:164-185`) | reject param 1 in car mode | 511 |
| `0xd2` | health packet | none (diagnostic input to SoC) | none | allow | 615 |
| `0xd8` | MCU reset | → SS-S after reset | none | allow (reset is safe if TSR-502 holds) | 502 |
| **`0xdb`** | OBD CAN multiplexing | changes CAN pin routing | none (`:219-221`) | reject | 513 |
| **`0xdc`** | **set safety mode and parameter** | **configures the envelope** | **none** (`:222-225`) | only reference modes; de-escalation only once TOYOTA active | 512 |
| **`0xde`** | CAN bit rate | can disable a bus | speed whitelist only (`:233-240`) | reject | 513 |
| `0xdf` | alternative experience | changes safety behaviour flags | only outside car modes (`:241-247`) | keep; release value must be 0 | 512 |
| **`0xe5`** | CAN loopback | breaks bus communication | none (`:248-252`) | reject | 513 |
| **`0xe6`** | clock-source timer parameters | timing | none (`:253-256`) | reject | 513 |
| **`0xe7`** | power save | disables transceivers and CAN IRQs | none (`:257-260`) | reject while authority possible | 513 |
| **`0xe8`** | CAN-FD auto switching | CAN config; **param1 not bounds-checked** (`:261-264`) | none | reject; bounds-check | 412, 513 |
| `0xf1` | clear CAN queues | can drop queued actuation/forwarded frames | bus index checked (`:265-276`) | reject in car mode | 513 |
| `0xf3` | **heartbeat**, param1 = engaged | resets heartbeat counter, sets `heartbeat_engaged` | none (`:277-285`) | carry control-loop evidence | 407, 409 |
| `0xf6` | siren enable | warning | none | allow | 516 |
| `0xf8` | disable heartbeat checks | removes SoC supervision | refused in car modes (`:290-295`) | keep | 407 |
| **`0xf9`**, **`0xfc`** | CAN-FD data rate / non-ISO | CAN config | bus index checked | reject | 513 |
| `0xfb` | deep sleep (host `panda.cc`) | — | not handled in application (falls to default) | — | — |

![Figure 4-1: the 28 control requests of this table grouped by the treatment a release build needs in a car mode (refused, limited, allowed, not handled), each with its function, its effect and its gating at the baseline; 9 that must be refused or limited have no gate](figures/fig-s05-4-1-control-requests.svg)

*Figure 4-1.* The rows of this table grouped by the Required column. A tile with a red border must be refused or limited in a car mode and has no gate at the baseline (its gating cell says "none", for the request or for one of its parameters): the SoC can use it today. The reference build adds the mode lock of TSR-512 for `0xdc`; the release whitelist per mode is OI-3. Generated by [`figures/fig_s05_requests.py`](figures/fig_s05_requests.py) from this table; CI fails if it is stale or a Required cell cannot be classified.

### 4.3 CAN packet format (endpoints 1 and 3)

From `can_comms.h:8-37`:

| Byte | Content |
|---|---|
| 0 | DLC[7:4], bus[3:1], FD flag[0] |
| 1–4 | (addr << 3) \| (extended << 2) \| (returned << 1) \| rejected |
| 5 | checksum = XOR over header bytes 0–4 and payload (`drivers/can_common.h:144-159`) |
| 6… | payload, up to 8 (CAN) or 64 (CAN FD) bytes |

Packets are concatenated across transfers with no per-transfer counter; partial packets are held in an overflow buffer (`can_comms.h:39-120`). The per-packet XOR is checked at FDCAN TX (`drivers/fdcan.h:100`); rejected TX packets are returned to the SoC with `rejected = 1` (`drivers/can_common.h:168-176`). Host side computes and checks the same XOR (`openpilot/selfdrive/pandad/panda.cc:189-196, 255-256, 284-289`).

## 5. Safety MCU ↔ CAN buses (HSI-04)

| Bus | MCU interface | Connected to | Use | Notes |
|---|---|---|---|---|
| 0 | FDCAN1 (or FDCAN3 when harness flipped) | vehicle side of harness | TX actuation, RX gating signals | orientation swap `drivers/can_common.h:130-135` |
| 1 | FDCAN2 | OBD / auxiliary (mux) | fingerprinting (ELM327 mode), DSU bus-1 messages | mode `CAN_MODE_OBD_CAN2` (`boards/tres.h:58-98`) |
| 2 | FDCAN3 (or FDCAN1 flipped) | camera side of harness | forwarding | — |

Transceiver enable lines (active-low per firmware): cuatro PB7, PB10, PD8, PB11 (`boards/cuatro.h:9-26`); tres PB10, PB11 plus PG11/PD7 tied (`boards/tres.h:32-56`). Transceivers are enabled after SILENT is set (`main.c:295-298`); in power save only the main bus stays enabled for ignition detection (`sys/power_saving.h:15-21`).

Processing order on RX (`drivers/fdcan.h:180-230`): packet built → forwarding decision `safety_fwd_hook` → forward with `skip_tx_hook` → `safety_rx_hook` → ignition hook → push to SoC queue. Forwarding is decided before RX validation of the same frame (GAP-11).

Reference-configuration RX set used by the envelope (`opendbc_repo/opendbc/safety/modes/toyota.h:39-46`):

| Addr | Name | Rate | Checksum | Counter | Envelope use |
|---|---|---|---|---|---|
| `0xAA` | WHEEL_SPEEDS | 83 Hz | no | no | vehicle moving, speed |
| `0x260` | STEER_TORQUE_SENSOR | 50 Hz | yes | no | EPS torque (tracking), driver torque (LTA only today) |
| `0x1D2` | PCM_CRUISE | 33 Hz | yes | no | engagement edge, gas |
| `0x226` | BRAKE_MODULE | 40 Hz | no | no | brake |
| `0x262`, `0x1D3` | EPS_STATUS, PCM_CRUISE_2 | 25 / 33 Hz nominal (former openpilot parser minimums; to be measured, OI-7) | yes (DBC) | no | RX check (checksum, timeout) in the reference build, opendbc `98404a4`; contents not used yet (TSR-110, 405) |
| `0xB4` | SPEED | TBD | yes (DBC) | no | proposed (TSR-404, 405); not added until its rate is known |

TX set: see [WP-S-02 §3–§4, TSR-705](WP-S-02-technical-safety-requirements.md).

## 6. Harness relay, orientation and ignition (HSI-05…07)

| Signal | tres | cuatro | Direction | Behaviour | Source |
|---|---|---|---|---|---|
| Relay drive SBU1 path | PA8 | PA9 | MCU out, open-drain | low = energised; init high (released) | `boards/tres.h:138-149`, `boards/cuatro.h:99-110`, `drivers/harness.h:96-107` |
| Relay drive SBU2 path | PA3 | PA3 | MCU out, open-drain | as above; which pin drives the intercept relay vs the ignition relay depends on orientation (`drivers/harness.h:22-28`) | same |
| SBU1 sense | PC4 / ADC1 ch4 | PC4 / ADC1 ch4 | in (analog/digital) | orientation by ADC < avdd/2; ignition as digital input | `drivers/harness.h:35-90` |
| SBU2 sense | PA1 / ADC1 ch17 | PA1 / ADC1 ch17 | in | as above | same |

Behaviour:

- Orientation is detected at 8 Hz (`main.c:118`) only while the relay is not driven (`drivers/harness.h:58-59`). A change re-initialises CAN and re-applies the safety mode (`main.c:131-140`).
- Relay is driven only when a harness is detected (`drivers/harness.h:10-13`) and only in car safety modes (`main.c:70-76`); SILENT/NOOUTPUT/ELM327 release it (`main.c:44-69`).
- Ignition for the Corolla comes only from the line (`opendbc_repo/opendbc/safety/ignition.h:12-63` has no Toyota case); `ignition_can` is set false after 2 s without CAN (`main.c:231-234`).
- No relay readback exists (GAP-12, GAP-43). Required: readback input (HWSR-506a) and de-energise-to-safe confirmation (AOU-13).

## 7. Reset, boot, watchdog and fault resources (HSI-08…12)

| Resource | Baseline | Required | TSR |
|---|---|---|---|
| `STM_RST_N`, `STM_BOOT0` driven by SoC GPIOs | `reset_internal_panda` pulses reset with BOOT0 low; `recover_internal_panda` pulses reset with BOOT0 high → ST ROM bootloader (`openpilot/common/hardware/comma/hardware.py:400-419`); used by `pandad.py:34-39` to flash a development bootstub | ROM bootloader entry must not give access to flash (RDP), application/bootstub write-protected (WRP); release `pandad` without development recovery path; MCU outputs safe (relay released, transceivers off) during reset and in ROM bootloader | 502, 511 |
| Bootstub | verifies SHA-1 + RSA-1024 signature of the app against the release key; debug key accepted with `ALLOW_DEBUG` (`bootstub.c:40-80`); soft flasher on failure; flasher erases sectors 1–7 only (`stm32h7/llflash.h:12-20`, `flasher.h:20-45`) | modern signature; no debug key; RDP/WRP | 511, 514 |
| IWDG1 | defined as `IND_WDG` (`stm32h7/stm32h7_config.h:43`), not initialised | started before app, window mode, serviced after safety task completion, timeout ≤ 0.1 s (SG-07, WP-S-04 §3.6) | 501 |
| Software watchdog | timestamp check from 8 Hz tick, threshold 375 ms, report-only (`main.c:301`, `drivers/simple_watchdog.h`) | keep as diagnostic only | 501 |
| Fault flags | `fault_occurred()` sets bits, `PERMANENT_FAULTS 0U`, report-only (`sys/faults.h`, `sys/sys.h:28-50`); reported in health (`main_comms.h:38-39`) | fault → SS-S per classification | 502 |
| NMI / HardFault | set a cookie, reset; reported as reset flags (`main.c:319-325`) | keep; ensure all other vectors reset (HWSR-502b) | 502 |
| Interrupt-rate monitor, register divergence | report-only (`drivers/interrupts.h`, `drivers/registers.h:56-70`) | reaction | 502, 503 |
| DTS temperature | reported (`main_comms.h:51-52`) | reaction | 509 |
| Siren | toggled at 4 Hz from tick while enabled or countdown (`main.c:113-114`); codec over I2C on some boards (`drivers/fake_siren.h:38-60`) | start-up test; DFA of shared speaker | 515, 516 |

## 8. Safety-relevant memory map

From `stm32h7/stm32h7x5_flash.ld:60-80`:

| Region | Address | Size | Content / safety relevance | Protection required |
|---|---|---|---|---|
| Flash sector 0 | `0x08000000` | 128 KiB | bootstub (signature check) | WRP; RDP (TSR-511) |
| Flash app | `0x08020000` (`_app_start`) | up to 3 × 128 KiB used (`main_comms.h:3`) | application, signature appended | WRP; CRC at start-up and periodically (TSR-503) |
| DTCM | `0x20000000` | 128 KiB | stack, safety state (`controls_allowed`, limits, samples) | MPU, ECC (TSR-503, 507) |
| AXI SRAM | `0x24000000` | 320 KiB | data | ECC |
| SRAM1/2 | `0x30000000` | 32 KiB | SPI DMA buffers (`drivers/spi.h:6-8`) — written by DMA from the SoC | MPU boundary so SPI DMA cannot reach safety state; bounds checks (TSR-412) |
| SRAM4 | `0x38000000` | 16 KiB | BDMA | ECC |
| Backup SRAM | `0x38800000` | 4 KiB | — | — |
| System memory | `0x1FF00000` | 128 KiB | ST ROM bootloader (reachable via BOOT0) | RDP (TSR-511) |

## 9. Operating modes and power states

| Mode (MCU) | Entered by | Relay | CAN TX | Heartbeat supervision | Safety relevance |
|---|---|---|---|---|---|
| Reset / ROM bootloader | power-up, NRST, BOOT0 | GPIO reset state (released, to be confirmed) | none | — | SS-S expected (HWSR-502) |
| Bootstub | reset | released | none | — | signature check |
| SILENT | start-up (`main.c:295`), heartbeat loss (`main.c:211-213`), invalid mode (`main.c:34-40`) | released | none (`can_silent`) | — | SS-S |
| NOOUTPUT | SoC request (offroad, ignition off: `openpilot/selfdrive/pandad/pandad.cc:194-207`) | released | blocked by hooks | 2 s / 5 s | safe |
| ELM327 | SoC request for fingerprinting (`openpilot/selfdrive/pandad/panda_safety.cc:23-34`) | released | diagnostic only | yes | must not allow actuation |
| TOYOTA (car mode) | SoC `0xdc` | driven (`main.c:70-76`) | filtered by `safety_tx_hook` | 3 s mismatch, 5 s loss (to tighten) | envelope active |
| ALLOUTPUT and debug modes | `ALLOW_DEBUG` builds only (`opendbc_repo/opendbc/safety/safety.h:413-422`) | driven | unfiltered | — | must be absent in release (TSR-514) |
| Power save | heartbeat loss or `0xe7` | as mode | transceivers off except main bus | — | `0xe7` must be refused in car mode |
| Stop mode | cuatro, SILENT and SoC GPIO low (`main.c:353-357`); `0xb5` debug only | released | off | — | asserted SILENT before entry |

Device-level states (offroad/onroad, engaged, soft-disabling, lockout) are in [WP-C-01 §4](../02-concept/WP-C-01-item-definition.md) and [WP-S-03 §4](WP-S-03-technical-safety-concept-architecture.md).

## 11. Signal catalogue

Added in v0.2 ([RR-2026-005](reviews/RR-2026-005.md) F-06). §2 lists the interfaces; this section lists the safety-relevant signals that cross them, one row each. CAN signal layouts are from the opendbc DBC files (`opendbc_repo/opendbc/dbc/generator/toyota/`): `_toyota_2017.dbc` for `0x2E4`, `0x1D2`, `0x1D3`, `0x260`, `0xAA`, `0xB4`, `0x412`; `_toyota_adas_standard.dbc` for `0x343`; `toyota_nodsu_pt.dbc` for `0x226` and `0x262`. Envelope limits are from `opendbc_repo/opendbc/safety/modes/toyota.h`. "Required" values come from the TSRs of [WP-S-02](WP-S-02-technical-safety-requirements.md) and are not met at the baseline where the TSR says so.

**Bit numbering.** "Bit n" of a CAN frame means byte n // 8, bit n mod 8, counted from the least significant bit of the byte (byte 0 is the first data byte). This is the numbering the envelope code uses (`GET_BIT`). For multi-bit signals the layout is given as bytes and bits. Positions marked "provisional" were taken from the DBC (`toyota_nodsu_pt_generated`) and still need to be confirmed by a bus capture on the reference vehicle (HIL bench B3), because the envelope and the host share that DBC.

Columns: **Dir** = direction across the item boundary or the HW/SW boundary. **Owner** = the hardware part and the software module responsible for the signal. **Integrity** = protection that exists in the signal itself. **Validity / liveness** = how the receiver knows the value is current. **Rate / max age** = nominal rate, then the maximum age the receiver accepts (required). **Tests** = cases in [WP-S-08](WP-S-08-system-integration-test.md) (VS-SI), [WP-H-06](../04-hardware/WP-H-06-hardware-integration-verification.md) (VS-HW) and [WP-V-05](../06-validation/WP-V-05-fault-injection.md) (VS-FI).

### 11.1 Vehicle CAN signals (HSI-04)

| ID | Signal | Dir | Owner (HW / SW) | Type / bits | Range, scale, units | Integrity | Validity / liveness | Rate / max age | Failure reaction | TSR | ASIL | Tests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S-01 | STEER_REQUEST, `0x2E4` STEERING_LKA bit 0 | MCU → EPS (TX, bus 0) | SW: E-03a envelope (`modes/toyota.h`) checks; host `card` packs | bool, 1 bit | 0 / 1 | 8-bit CHECKSUM (byte 4) | 6-bit COUNTER (checked by the EPS, not by the item) | 100 Hz (host, every control frame, `carcontroller.py:130-134`) | Frame rejected by the envelope → SS-L, authority revoked (TSR-108, 109) | 105, 108, 109 | B‡ | VS-SI-15, VS-FI-14 |
| S-02 | STEER_TORQUE_CMD, `0x2E4` | MCU → EPS | SW: E-03a envelope (`modes/toyota.h`) checks; host `card` packs | int16, signed | raw, \|cmd\| ≤ 1500; Δ ≤ 15 up / 25 down per frame; ≤ 350 above measured EPS torque (`toyota.h:173-177`) | as S-01 | as S-01 | as S-01 | as S-01 | 101…104, 108, 109 | B‡ | VS-SI-15, VS-FI-14 |
| S-03 | ACCEL_CMD, `0x343` ACC_CONTROL | MCU → PCM | SW: E-03a envelope (`modes/toyota.h`) checks; host `card` packs | int16, signed | 0.001 m/s² per bit; −3.5 … +2.0 m/s² (`toyota.h:208-209`); inactive value 0 | 8-bit CHECKSUM (byte 7) | none | 33 Hz (host, every third frame) | Frame rejected → inactive value; authority revoked on violation (TSR-108 analogue for longitudinal, TSR-203) | 201…207 | B‡ | VS-SI-16, VS-FI-14 |
| S-04 | CANCEL_REQ, `0x343` bit 24 | MCU → PCM | SW: host `controlsd`/`card` (E-01) | bool | 0 / 1 | as S-03 | none | with S-03 | Cancel without effect → siren (TSR-516(c)) | 303 | QM (B-sup) | VS-SI-02, VS-SI-24 |
| S-05 | LKAS_HUD `0x412` (cluster lane and alert display) | MCU → cluster | SW: host `card` (E-01) | 8-byte frame | DBC enumerations | none | none | 1 Hz, or at once on an alert change (`carcontroller.py:289`) | — (QM display); must not create a false engagement indication (DFI-15) | 309 (AOU-12) | QM | VS-SI-24 |
| S-06 | WHEEL_SPEED_FR/FL/RR/RL, `0xAA`: per wheel k = 0…3 (FR, FL, RR, RL), bytes 2k and 2k+1, big-endian, bits 0–6 of byte 2k (high) and byte 2k+1 (low); fault flag bit 16k+7 (provisional, from the DBC, not yet confirmed independently: [LAYOUT-CHECK-2026-10-13](../05-software/reference-models/results/LAYOUT-CHECK-2026-10-13.md) LC-01) | vehicle → MCU (RX, bus 0) | SW: E-03a envelope RX hook (`modes/toyota.h`) | 4 × 15-bit unsigned | 0.01 km/h, offset −67.67 | none | none (no checksum, no counter, `toyota.h:40`) | 83 Hz / required ≤ 5 periods (≤ 0.2 s, TSR-401) | RX fault → revoke all authority (TSR-406); frozen-payload and cross-checks (TSR-404, 405(a)) | 401, 404, 405, 406 | B‡ | VS-SI-12, VS-SI-13, VS-FI-02, VS-FI-04, VS-FI-05 |
| S-07 | STEER_TORQUE_DRIVER, `0x260` | vehicle → MCU | SW: E-03a envelope RX hook (`modes/toyota.h`) | int16, signed | raw | 8-bit additive CHECKSUM | none (no counter, `toyota.h:41`) | 50 Hz / ≤ 0.2 s; STEER_ANGLE_INITIALIZING bit 3 is the message's quality flag, checked only in LTA mode, not in the reference (LKA) configuration (provisional, from the DBC, not yet confirmed independently: [LAYOUT-CHECK-2026-10-13](../05-software/reference-models/results/LAYOUT-CHECK-2026-10-13.md) LC-01) | Driver override → torque reduction or revoke (TSR-304); RX fault → TSR-406 | 304, 401…406 | B‡ | VS-SI-03, VS-SI-14, VS-FI-02 |
| S-08 | STEER_TORQUE_EPS, `0x260` | vehicle → MCU | SW: E-03a envelope RX hook; host `selfdrived` (TSR-626) | int16, signed | raw (EPS scale param 73) | as S-07 | as S-07 | 50 Hz / ≤ 0.2 s | Measured-torque tracking (TSR-104); EPS not following command → SoC disable (TSR-626(b)) | 104, 405(d), 626 | B‡ | VS-SI-15, VS-FI-05 |
| S-09 | CRUISE_ACTIVE, `0x1D2` PCM_CRUISE bit 5 | vehicle → MCU | SW: E-03a envelope RX hook (`modes/toyota.h`) | bool | 0 / 1 | 8-bit CHECKSUM | none (no counter) | 33 Hz / ≤ 0.2 s | Rising edge grants, low revokes (TSR-301); RX fault → TSR-406 | 301, 401…406 | B‡ | VS-SI-01, VS-SI-02, VS-SI-13 |
| S-10 | GAS_RELEASED, `0x1D2` bit 4 | vehicle → MCU | SW: E-03a envelope RX hook (`modes/toyota.h`) | bool | 0 / 1 | as S-09 | as S-09 | as S-09 | Gas pressed → only the inactive acceleration (TSR-305) | 305 | B‡ | VS-SI-04 |
| S-11 | BRAKE_PRESSED, `0x226` BRAKE_MODULE bit 37 | vehicle → MCU | SW: E-03a envelope RX hook (`modes/toyota.h`) | bool | 0 / 1 | none (`toyota.h:46`, checksum ignored) | none | 40 Hz / ≤ 0.2 s | Brake → revoke (TSR-302); disagreement with S-13 → assume pressed (TSR-405(b)) | 302, 405 | B‡ | VS-SI-02, VS-SI-13, VS-FI-05 |
| S-12 | LKA_STATE, `0x262` EPS_STATUS, byte 3 bits 1–7 (provisional, from the DBC, not yet confirmed independently: [LAYOUT-CHECK-2026-10-13](../05-software/reference-models/results/LAYOUT-CHECK-2026-10-13.md) LC-01) | vehicle → MCU (reference build, opendbc `242d63d`) / SoC | SW: E-03a (presence, checksum, timeout; fault codes refuse LKA actuation); host `card` (fault codes, alert) | 7-bit unsigned | EPS state codes (`carstate.py:19-22`) | 8-bit CHECKSUM | none | 25 Hz nominal (to be measured) / ≤ 0.3 s | EPS fault → envelope refuses LKA torque and steer request and reports it (`pandaState.epsFault`) (TSR-110, implemented in the reference build); siren when the fault persists 1 s while engaged (TSR-516(b), panda `b790fca`) | 110, 607 | B (SG-02) | VS-SI-17 |
| S-13 | BRAKE_PRESSED, MAIN_ON, ACC_FAULTED, `0x1D3` PCM_CRUISE_2; MAIN_ON bit 15 (provisional, from the DBC, not yet confirmed independently: [LAYOUT-CHECK-2026-10-13](../05-software/reference-models/results/LAYOUT-CHECK-2026-10-13.md) LC-01); BRAKE_PRESSED and ACC_FAULTED positions not stated | vehicle → MCU (reference build: RX check only, opendbc `98404a4`) / SoC | SW: E-03a (presence, checksum, timeout; MAIN_ON vs CRUISE_ACTIVE, opendbc `875e325`; BRAKE_PRESSED cross-check open); host `card` | bool | 0 / 1 | 8-bit CHECKSUM | none | 33 Hz nominal (to be measured) / ≤ 0.2 s | MAIN_ON = 0 with CRUISE_ACTIVE: no engagement, revoke after 150 ms (TSR-405(c), implemented); BRAKE_PRESSED vs S-11 (TSR-405(b), open: bit semantics unknown); ACC fault → SoC disable (TSR-618) | 405, 618 | B‡ / QM | VS-SI-13, VS-FI-05 |
| S-14 | SPEED, ENCODER, `0xB4` | vehicle → MCU (proposed) | SW: E-03a envelope RX hook (`modes/toyota.h`) | 16-bit unsigned; 8-bit | 0.01 km/h; counts | 8-bit CHECKSUM | ENCODER changes while moving | TBD / ≤ 0.2 s | Cross-check with S-06 (TSR-405(a)); frozen ENCODER (TSR-404) | 404, 405 | B‡ | VS-FI-02, VS-FI-05 |
| S-15 | Camera-side frames incl. PRE_COLLISION `0x283`, PRE_COLLISION_2 `0x344`, PCS_HUD `0x411` | camera → MCU → vehicle (forwarded bus 2 → bus 0) | SW: E-03b forwarding (`drivers/fdcan.h`); HW: FDCAN, transceivers | CAN frames | unchanged | CAN CRC; OEM checksums where defined | camera-side reception supervised (TSR-711) | OEM rate (to be measured, WP-S-04 OI-4) / forwarding latency ≤ 1 ms; loss detected ≤ 0.1 s | Forwarding stopped → relay released (TSR-711, TSR-706); SoC frames with these IDs refused (TSR-705) | 704, 705, 707, 711 | B | VS-SI-20, VS-SI-21, VS-FI-24 |

### 11.2 SoC ↔ safety MCU signals (HSI-01…03)

| ID | Signal | Dir | Owner (HW / SW) | Type / bits | Range, scale, units | Integrity | Validity / liveness | Rate / max age | Failure reaction | TSR | ASIL | Tests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S-16 | SPI transfer (header, payload) | SoC ↔ MCU | SW: E-03b `drivers/spi.h`; host `pandad`; HW: SPI4, DMA2 | 7-byte header + payload ≤ 4096 B | lengths bounded by the buffer | 8-bit XOR, seed `0xAB` (§4.1); required CRC (TSR-410) | none; required sequence counter (TSR-411) | ≈ 100 Hz (pandad loop) / required ≤ 2 control periods for commands (TSR-411, TSR-614) | NACK; required: stale or corrupt command → SS-L / SS-G (TSR-410…413) | 410…413 | B‡ | VS-SI-09, VS-SI-10, VS-FI-06, VS-FI-07, VS-FI-08 |
| S-17 | CAN TX packet from SoC (endpoint 3) | SoC → MCU | SW: E-03b `can_comms.h`; host `pandad` | 6-byte header + ≤ 8 B payload | DLC, bus, address | 8-bit XOR per packet, checked at FDCAN load (§4.3) | none | per control frame | Rejected by the TX hook → returned with `rejected = 1`; violation → revoke (TSR-108) | 108, 410, 517, 518 | B‡ | VS-SI-11, VS-SI-15, VS-FI-14 |
| S-18 | Heartbeat `0xf3`, param1 = engaged | SoC → MCU | SW: E-03b `main_comms.h`; host `pandad` | control request, uint16 param | 0 / 1 | as S-16 | heartbeat counter | 10 Hz, sent with each `pandaStates` cycle (`openpilot/selfdrive/pandad/pandad.cc:278`), checked in the 1 Hz MCU tick / required ≤ 0.3 s loss detection (TSR-407) | Loss → SS-S and siren (TSR-407, TSR-516(a)); "not engaged" → revoke (TSR-307(a)) | 307, 407, 409 | B‡ | VS-SI-05, VS-SI-06, VS-FI-10 |
| S-19 | Safety mode and param `0xdc` | SoC → MCU | SW: E-03b `main_comms.h`; host `pandad` | control request, 2 × uint16 | TOYOTA mode; param 73 (EPS scale) | as S-16 | — (configuration) | at start-up | Required: any other value in a car mode refused (TSR-512) | 512, 619 | B‡ | VS-SI-07, VS-FI-11 |
| S-20 | Configuration and debug requests (`0xc5`, `0xd1`, `0xd8`, `0xdb`, `0xde`, `0xe5`…`0xe8`, `0xf1`, `0xf9`, `0xfc`) | SoC → MCU | SW: E-03b `main_comms.h`; host `pandad` | control requests | §4.2 | as S-16 | — | on request | Required: refused in a car safety mode (TSR-513) | 511, 513 | B‡ | VS-SI-08, VS-HW-05, VS-FI-11 |
| S-21 | Health packet `0xd2` (`health_t`: controls allowed, faults, safety mode and param, TX blocked and RX invalid counts, harness status, voltage, temperature; LionDriver flags: watchdog reset, EPS fault, reference build) | MCU → SoC | SW: E-03b `main_comms.h`; host `pandad`, `selfdrived` | packed struct (`panda/board/health.h`) | per field | as S-16 | `pandaStates` alive check | 10 Hz `pandaStates` / required ≤ 0.2 s (TSR-626(a)) | SoC immediate disable on fault flags or mismatch (TSR-615, 621, 626); in a reference build `pandad` sets no car safety mode without the reference-build flag (TSR-514) | 615, 621, 626 | QM (B-sup) | VS-SI-06, VS-SI-17, VS-SI-23 |

### 11.3 Safety MCU hardware signals (HSI-05…14)

| ID | Signal | Dir | Owner (HW / SW) | Type / bits | Range, scale, units | Integrity | Validity / liveness | Rate / max age | Failure reaction | TSR | ASIL | Tests |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S-22 | Relay drive (tres PA8 / cuatro PA9; PA3) | MCU → harness relay | HW: relay driver and coil (E-05); SW: E-03b `drivers/harness.h` | GPIO, open-drain | low = energised (intercept); high or reset = released | none | none at the baseline; required contact readback (TSR-506) | static / readback mismatch ≤ 0.3 s | Released on SS-S, MCU fault, reset, power loss (TSR-706); forwarding loss (TSR-711) | 506, 706, 710, 711 | B | VS-HW-01…04, VS-SI-18, VS-SI-19, VS-FI-21 |
| S-23 | SBU1 / SBU2 sense (PC4 / ADC1 ch4, PA1 / ADC1 ch17) | harness → MCU | HW: SBU divider, ADC1; SW: E-03b `drivers/harness.h` | ADC, mV (reported in `health_t`) | orientation: below avdd/2 | none | evaluated only while the relay is not driven | 8 Hz | Orientation change → CAN re-init and mode re-apply (§6); not connected → no relay drive (TSR-701) | 701 | B | VS-HW-13, VS-FI-28 |
| S-24 | Ignition line | harness → MCU | HW: ignition input; SW: E-03b `drivers/harness.h` | digital | on / off | none | — | 1 Hz (`panda/board/main.c:156`) | Heartbeat loss → SS-S within ≤ 2 s regardless of ignition (TSR-510) | 510 | B | VS-HW-14 |
| S-25 | `STM_RST_N`, `STM_BOOT0` | SoC → MCU | HW: SoC GPIO to NRST/BOOT0; SW: host `hardware.py` | GPIO | reset / ROM bootloader | none | — | on event | MCU reset → relay released (TSR-502, HWSR-502c); boot protection (TSR-511) | 502, 511 | B‡ (+CS) | VS-HW-19, VS-FI-16 |
| S-26 | Independent watchdog IWDG1 | MCU internal | HW: IWDG1 (E-04a); SW: E-03b bootstub and tick | timer | timeout ≤ 0.1 s (§7) | — | serviced after the safety task completes | — | Reset → SS-S (TSR-501, 502) | 501, 502 | B‡ | VS-HW-06, VS-HW-07, VS-FI-17 |
| S-27 | Siren output (DAC/DMA and codec over I2C5, or SAI4 amplifier) | MCU → speaker | HW: codec or amplifier, speaker; SW: E-03b `drivers/fake_siren.h` | audio | 4 Hz pattern | none | required start-up test (TSR-515) | ≤ 0.5 s after trigger | Triggers per TSR-516(a)…(c) | 515, 516 | B | VS-HW-21 |
| S-28 | Supply voltage (ADC1 input divider) | supply → MCU | HW: input divider, ADC1, BOR/PVD; SW: E-03b | ADC, mV (`health_t.voltage_pkt`) | operating range per HWSR-505 | none | — | on each health request (10 Hz) | Required: out of range → SS-S (TSR-505); BOR / PVD | 505 | B‡ | VS-HW-09, VS-HW-10, VS-FI-15 |
| S-29 | Die temperature (DTS) | MCU internal | HW: DTS (E-04a); SW: E-03b | °C (`health_t.temperature_pkt`) | specified MCU range | none | — | on each health request (10 Hz) | Required: out of range → SS-S (TSR-509) | 509 | B | VS-HW-15, VS-FI-26 |

S-12 and S-13 are envelope RX checks in the reference build since opendbc `98404a4` (presence, checksum, timeout); the fault-code revocation (TSR-110) and cross-checks (TSR-405) that use their content are not implemented. S-14 is a proposed addition. All three rates are to be measured on the reference vehicle (WP-S-04 measurement plan, OI-7).

## 12. Vehicle networks and end-to-end protection

Added in v0.14. §4 and §5 describe the links the item has today; this section asks what protects the information on them, end to end, and what changes when a configuration uses another vehicle network. It is an engineering analysis (AI-authored, I0): it proposes, it changes no requirement. The open items it raises are OI-8…OI-12; the question it raises for the project lead is in the decision register.

### 12.1 The networks, and which of them the item touches

| Network | Standard | What it is | Where it appears for LionDriver |
|---|---|---|---|
| Classical CAN | ISO 11898-1, ISO 11898-2 | Two-wire differential bus, every node hears every frame; 11- or 29-bit identifier that is also the arbitration priority; 0 to 8 data bytes; CRC-15, bit stuffing, acknowledge and error frames in the controller; typically 500 kbit/s in a car | **The reference configuration.** All three panda buses (§5) are classical CAN at 500 kbit/s (§3). Every safety-relevant vehicle signal of §11.1 travels on it |
| CAN FD | ISO 11898-1:2015 | Same arbitration, then an optional faster data phase (bit-rate switch, BRS, typically 2 to 5 Mbit/s) and up to 64 data bytes; CRC-17 (≤ 16 bytes) or CRC-21, with a stuff-bit count inside the CRC field. "Non-ISO" CAN FD is the earlier Bosch version without the stuff-bit count | **Not in the reference configuration, but in the hardware.** The panda's FDCAN controllers and the SPI packet format (§4.3, FD flag, ≤ 64 bytes) carry CAN FD; control requests `0xe8`, `0xf9`, `0xfc` switch it on (§4.2, rejected in a car mode). Upstream brands on CAN FD include the Hyundai/Kia/Genesis CAN FD platforms, Ford's newer platforms and Honda's CAN FD platforms (`hyundai_canfd.h`, `ford.h`, `honda.h` in opendbc) |
| CAN XL | ISO 11898-1 (2024 revision), CiA 610 | Up to 2048 data bytes, 10 Mbit/s and more; carries Ethernet frames | Not in any upstream configuration. Noted only so that the analysis is not surprised by it |
| SAE J1939 | SAE J1939-21, -71, -81 and others | An application layer on 29-bit CAN for heavy vehicles: the identifier holds priority, parameter group number (PGN) and source address; 250 or 500 kbit/s; addresses are claimed at start-up (J1939-81); messages over 8 bytes use a transport protocol. Engine and brake control use parameter groups such as TSC1 (torque/speed control) and XBR (external brake request, with its own message counter and checksum) | **Not supported by openpilot or opendbc, and outside the item.** A J1939 vehicle would be a new item, not a new configuration: the HARA (mass, stopping distance, articulation), the ODD and the actuators all change. The lead decided (DQ-419 A, 2026-10-25) that the next vehicles stay on CAN and ISO CAN FD passenger cars; J1939 vehicles are outside the platform (AOU-18) |
| LIN | ISO 17987 | Single-wire, one commander and up to 15 responders, ≤ 20 kbit/s; protected identifier with 2 parity bits, an 8-bit checksum (classic over the data, enhanced over the identifier and data); no counter | **Never seen by the item.** LIN sits behind a body or gateway ECU (switches, wipers, rain and light sensors, seat and mirror motors). A LIN-sourced value reaches the panda only after an ECU has re-packed it into a CAN frame, so for the item the sender is that ECU and the protection is that of the CAN frame |
| FlexRay | ISO 17458 | Time-triggered, 10 Mbit/s, dual channel | No upstream configuration actuates over FlexRay. A car whose steering or braking commands travel on FlexRay cannot be intercepted by a CAN harness |
| Automotive Ethernet | IEEE 802.3bw (100BASE-T1), 802.3bp (1000BASE-T1); SOME/IP | Switched point-to-point links in zonal architectures | Same as FlexRay: outside the interception architecture. Listed because new platforms move ADAS commands there |

The architecture rests on one property that the table makes visible: **the actuation commands must travel on a CAN or CAN FD bus that the harness can split, without authentication the item cannot produce.** On the reference car this holds. It is written as assumption of use AOU-18 in [WP-C-01](../02-concept/WP-C-01-item-definition.md) §7, which also makes it an entry criterion for admitting a vehicle (lead decision DQ-419 A, 2026-10-25). Toyota's newer platforms with authenticated actuation messages (SecOC, the `toyota_secoc` path in `modes/toyota.h`) already break it: openpilot supports them only with a key recovered from the car, which is a cybersecurity question for [WP-C-09](../02-concept/WP-C-09-tara.md), not a networking one.

### 12.2 The faults to protect against

ISO 26262-6:2018 Annex D lists the faults in the exchange of information that a software architecture has to consider: repetition, loss, delay, insertion, masquerade or incorrect addressing, incorrect sequence, corruption, asymmetric information sent to several receivers, information received by only some receivers, and blocking of the channel. ISO 26262-5:2018 Annex D, Table D.7 (communication) lists the mechanisms and the diagnostic coverage each can be credited with. The two lists meet in this matrix, for the mechanisms available on a CAN path:

| Fault | CAN controller (CRC-15/17/21, stuffing, ACK, error frames) | OEM checksum over the data | OEM checksum that includes the identifier (data ID) | Message counter | Timeout (absence) | Rate check | Frozen-value and cross-checks | Message authentication (SecOC) |
|---|---|---|---|---|---|---|---|---|
| Corruption | **yes**: the protocol CRC, per hop | yes, end to end | yes | — | — | — | partly | yes |
| Repetition (same frame again) | — | — | — | **yes** | — | partly (TSR-403) | partly (TSR-404) | with a freshness value |
| Loss | — | — | — | yes (gap in sequence) | **yes** (TSR-401) | — | — | — |
| Delay (stale value arrives late) | — | — | — | partly (only relative to other frames) | yes, if longer than the timeout | — | partly | with a freshness value |
| Insertion (extra frame) | — | — | — | yes | — | **yes** (TSR-403) | partly | yes |
| Masquerade, incorrect addressing | — | — | **yes** against an accidental wrong ID; **no** against a deliberate sender, since the checksum is no secret | — | — | partly | partly (TSR-405) | **yes** |
| Incorrect sequence | — | — | — | **yes** | — | — | — | with a freshness value |
| Asymmetric, partial reception | the CAN error frame makes reception consistent in most cases; a few last-bit cases remain | — | — | — | per receiver | — | — | — |
| Blocking of the channel (bus-off, babbling node) | error counters, bus-off (TSR-508) | — | — | — | **yes** | — | — | — |

Three conclusions follow, and they shape §12.3.

1. **The protocol CRC protects one hop, not the path.** Every CAN controller recomputes the CRC when it sends. A frame corrupted inside the panda, the SoC, or the SPI link is sent out with a fresh, valid CRC. Only a check computed by the sender and verified by the receiver, over the data, survives the hops: that is end-to-end (E2E) protection, and the links in between become a "black channel" whose own checks need no safety credit.
2. **A checksum alone answers corruption; repetition, delay and sequence need a counter, and masquerade needs a key.** A Toyota frame with a valid checksum and no counter can be replayed indefinitely and still pass every E2E check.
3. **E2E protects the channel, not the sender.** If the sender computes the checksum and counter over a wrong value, the receiver accepts it. On the actuation path the sender is openpilot on the SoC, which is QM (§12.3, hop H1 and H2). E2E can never be credited against SoC faults; only the envelope's content checks (TSR-101…108, TSR-201…207) can.

### 12.3 The reference configuration, hop by hop

| Hop | From → to | What protects it end to end today | What is missing | Requirement |
|---|---|---|---|---|
| H1 | SoC (QM) → panda, SPI (§4) | 8-bit XOR per transfer and per CAN packet | CRC with a residual-error target; sequence counter; freshness | TSR-410, 411, 412, 413 (OI-2) |
| H2 | panda → EPS and PCM, bus 0 (`0x2E4`, `0x343`) | `0x2E4`: 8-bit Toyota checksum over identifier, length and data, plus a 6-bit counter, both written by openpilot on the SoC; `0x343`: checksum only (§11, S-01, S-03). The EPS is assumed to check both; nothing in the item does | The EPS's checks are not an assumption of use yet (OI-9). The panda does not check the checksum or counter of the frames it lets through, so an SPI corruption that keeps the XOR valid but breaks the checksum is caught only by the EPS | TSR-108, 408; OI-9, OI-10 |
| H3 | car → panda, bus 0 (`0xAA`, `0x260`, `0x1D2`, `0x226`, `0x262`, `0x1D3`) | Protocol CRC; Toyota checksum on `0x260`, `0x1D2`, `0x262`, `0x1D3` (TSR-402); absence after 5 periods (TSR-401) | **No counter on any of them**, and no checksum at all on `0xAA` wheel speeds and `0x226` brake (§5, GAP-01). Repetition, delay and a stuck sender are covered only by plausibility: rate (TSR-403), frozen payload (TSR-404) and cross-checks (TSR-405), of which only TSR-405(c) is built | TSR-401…406 |
| H4 | camera → car through the panda, bus 2 → bus 0 (PCS `0x283`, `0x344`) | The camera's own checksum (and on `0x283` an 8-bit counter, DBC `_toyota_adas_standard.dbc`) passes through unchanged, because the panda forwards these frames byte for byte (TSR-704). The brake ECU checks them. For these frames the panda is a black channel | Nothing in the item needs adding, provided forwarding never alters a byte. A forwarding fault that changes data is caught by the receiver's checksum; one that drops or delays frames is TSR-707 and TSR-711 | TSR-704, 707, 711 |
| H5 | panda → SoC, SPI (health, RX frames) | As H1 | As H1, but the SoC is QM and acts only as a second, supervising channel | TSR-615, 626 |

The picture is unusual and worth stating plainly. **On the reference car, end-to-end protection in the usual sense (checksum, counter and timeout together, which Table D.7 credits with high coverage) exists only on the camera's PCS frames, which the item does not touch.** The vehicle signals the envelope gates on carry at most a checksum, and the commands the item sends are protected by a sender the safety argument cannot trust. The safety argument therefore cannot lean on E2E. It leans on three other things, and this section asks that they be named as such in WP-S-03:

- **timeout and plausibility on the receive side** (TSR-401, 403, 404, 405): these do the work a counter would do. They are mostly not built (GAP-01), which makes them the communication gap with the most weight;
- **content checks on the transmit side** (the envelope, TSR-1xx and TSR-2xx), which catch a wrong value regardless of how well it is packed;
- **a stronger link on H1** (TSR-410, 411), the only hop the item owns at both ends, and so the only one where the item can add a real E2E profile (CRC, counter, freshness) without changing the car.

### 12.4 How strong is the CAN CRC?

Classical CAN's CRC-15 has a Hamming distance of 6 over the frame, but bit stuffing weakens it: two bit errors that create or remove a stuff bit shift the rest of the frame and can escape the CRC. The residual-error figure usually quoted for classical CAN (Unruh, Mathony and Kaiser, 1990) is in the order of 10⁻¹¹ times the frame error rate; later work found the stuffing cases make it worse than that figure for some error patterns. CAN FD fixed this: the stuff-bit count is protected, fixed stuff bits are used in the CRC field, and the CRC is 17 or 21 bits. Non-ISO CAN FD does not have the fix.

For the analysis this means: the protocol CRC can be credited for corruption on one CAN hop, as the FMEDA already does ([WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md), Table D.7, "CRC, high"), but its residual error rate depends on the bit error rate of the harness, which nobody has measured. The harness adds wire and connectors between camera and car. The residual-error calculation for the vehicle hops, with a measured or bounded bit error rate, is OI-11.

### 12.5 When the next configuration is not a Toyota

Each brand protects its messages differently, and the envelope's RX checks inherit whatever the brand offers. From the opendbc safety modes at the baseline:

| Brand family (opendbc mode) | Checksum on RX messages | Counter | Comment |
|---|---|---|---|
| Toyota (`toyota.h`) | 8-bit additive, includes identifier and length | none on the RX checks | Weakest in the table; §12.3 |
| Subaru (`subaru.h`), Tesla (`tesla.h`) | 8-bit additive, includes identifier | 4-bit (Subaru), per message (Tesla) | A counter catches repetition and sequence faults |
| Honda (`honda.h`) | 4-bit nibble sum, includes identifier | 2-bit | Short: a stuck counter pattern repeats every 4 frames |
| Ford (`ford.h`) | inverted 8-bit sum over selected signals | 4-bit, with a quality flag | |
| Chrysler (`chrysler_common.h`), Rivian (`rivian.h`) | CRC-8 (polynomial `0x1D`) | 4-bit | |
| Hyundai/Kia CAN (`hyundai.h`) | per message: bit count or nibble sums | 2 to 4 bits | |
| Hyundai/Kia CAN FD (`hyundai_canfd.h`) | CRC-16 over data and identifier, length-dependent final XOR | 8-bit on long frames | Closest to a full E2E profile among the upstream brands |
| Volkswagen MQB/MEB (`volkswagen_common.h`) | CRC-8H2F (AUTOSAR) with a data ID that changes with the counter | 4-bit | This is the AUTOSAR E2E profile 2 pattern: the data ID makes a frame from one message invalid as another |

So a second vehicle can be *better* protected than the reference car, and the TSRs should not be written around Toyota's weakness. TSR-402 names the Toyota checksum; for the second configuration it becomes a per-configuration table: for each RX message, its checksum, counter, data ID and the plausibility checks that compensate for what is missing (OI-12). The table above is the starting point.

CAN FD adds three things to check for such a configuration:

- **Physical layer.** In the data phase a bit lasts 200 to 500 ns, so the harness, its stub to the device and the transceivers' ringing suppression matter in a way they do not at 500 kbit/s. The harness design and the transceiver parts need a CAN FD review against the car's data rate ([WP-H-02](../04-hardware/WP-H-02-hardware-design.md)).
- **Only ISO CAN FD.** Non-ISO operation (`0xfc`) gives up the protected stuff-bit count. A configuration that needs it needs a recorded argument.
- **The SPI link carries 64-byte payloads** under the same 8-bit XOR (§4.3). The weakness of H1 grows with the frame, which adds weight to TSR-410.

### 12.6 What a J1939 or LIN signal would mean

Neither is in scope, but the questions are predictable, so the answers are recorded here.

- **J1939.** Addresses are claimed, not fixed, so the source address in the identifier is not proof of the sender, and a masquerade check has to bind PGN, source address and, where the parameter group defines them, its own counter and checksum (XBR has both; TSC1 has them in later revisions of J1939-71). Commands over 8 bytes arrive in pieces by the transport protocol, and an envelope would have to reassemble and check them before acting. Heavy-vehicle buses also run at 250 kbit/s on many older trucks, which halves the rate budget of §3. All of this is a new item. The lead has kept such vehicles out of scope (DQ-419 A, AOU-18), so no requirement is proposed for them.
- **LIN.** If a future configuration wants a LIN-sourced signal (say the wiper state as an ODD exit, [WP-C-02](../02-concept/WP-C-02-odd-and-intended-functionality.md)), it reaches the item through a gateway ECU on CAN. The item can claim no more than the gateway's CAN frame offers, and the gateway's handling of LIN errors becomes an assumption of use. A signal from LIN can support a QM function or an ODD monitor that the driver backs up; it should not carry an ASIL claim from the item side.

### 12.7 Proposals

None of these is applied. Each is an open item below; requirement changes go through WP-P-02.

| # | Proposal | Why | Where |
|---|---|---|---|
| P-1 | Write the assumption that actuation is on CAN or CAN FD at a harness point, without authentication the item cannot produce | It holds the architecture together and is unwritten | OI-8 (closed: WP-C-01 AOU-18, DQ-419 A) |
| P-2 | Write the EPS's own checks of the `0x2E4` checksum and counter as an assumption of use, with its verification on the car | The item relies on them at H2 and nothing checks them | OI-9, WP-C-01 §7 |
| P-3 | Let the envelope verify the Toyota checksum of `0x2E4` and `0x343` before sending | Catches a corruption between the SoC's packer and the FDCAN that the SPI XOR misses; a few lines in the TX hook; becomes redundant once TSR-410 is built | OI-10 |
| P-4 | Calculate the residual error of the vehicle CAN hops with a bounded bit error rate, and measure the error counters on the car | Table D.7 credit for the protocol CRC needs the number | OI-11 |
| P-5 | Turn TSR-402 into a per-configuration E2E table when the second configuration is added | The reference car's weakness should not shape the requirements of a better-protected car | OI-12 |
| P-6 | Name timeout and plausibility, not E2E, as the communication argument in WP-S-03, and give TSR-403 and TSR-404 the priority of the communication gaps | They do the work a counter would do on H3, and they are not built | GAP-01 |

## 10. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm pin assignments, relay driver, transceiver enable pull-ups and GPIO reset behaviour against the schematic (WP-H-02 OI-1) | HW lead | G2 |
| OI-2 | Define the SPI residual-error target and select the CRC; specify the sequence-counter format (with WP-S-07). Method decided 2026-10-26 (DQ-143 A): the target comes from the ASIL C budget and the shortest CRC that meets it is chosen. Left: the analysis and the implementation | SW lead | G3 |
| OI-3 | Define the release control-request whitelist per mode (§4.2) and record it in WP-W-02. Method decided 2026-10-26 (DQ-144 A): derive it from TSR-512/513 and CSR-011…016, consistent with the reference lock and its allow-list (DQ-147 A). Left: the review of every request against each mode, and the SWSRs | SW lead | G3 |
| OI-4 | Define the MPU region map so SPI/USB DMA buffers cannot overlap safety state | SW lead | G3 |
| OI-5 | Align host and MCU SPI buffer sizes or document why they differ | SW lead | G3 |
| OI-6 | Fix the reference board variant (tres/cuatro) and drop the other column. The lead answered on 2026-10-14 (decision register DQ-011) that the comma 3X and the comma four may both need review, so both columns stay. Re-open when one device is fixed for the reference car | Maintainer | G1 |
| OI-7 | Measure the rates of `0x262`, `0x1D3`, `0xB4` and the camera-side PCS messages on the reference vehicle and fill §11 (S-12…S-15) | Test lead | G2 |
| OI-8 | ~~Write the assumption of use that the actuation commands travel on CAN or CAN FD at the harness point, without authentication the item cannot produce (§12.1, P-1)~~ **Closed 2026-10-25:** WP-C-01 AOU-18, after lead decision DQ-419 A; its verification on the car stays open in WP-C-01 §7 | Safety manager | G2 |
| OI-9 | Write the EPS's own checks of the `0x2E4` checksum and counter as an assumption of use, and verify them on the car (§12.3 H2, P-2) | Safety manager; test lead | G2 |
| OI-10 | Decide whether the envelope verifies the Toyota checksum of `0x2E4` and `0x343` before sending (§12.7 P-3); technical choice, recommended until TSR-410 is built | SW lead | G3 |
| OI-11 | Residual-error calculation for the vehicle CAN hops with a bounded bit error rate; read the FDCAN error counters on the car during the measurement drives (§12.4, P-4) | HW lead | G3 |
| OI-12 | When a second configuration is added, turn TSR-402 into a per-configuration E2E table from §12.5 (P-5) | SW lead | second configuration |
