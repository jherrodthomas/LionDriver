# WP-S-05 Hardware-Software Interface (HSI) Specification

| Field | Value |
|---|---|
| Work product | WP-S-05 Hardware-software interface specification |
| Standard reference | ISO 26262-4:2018 §6 (HSI specification); ISO 26262-5:2018 §6 and ISO 26262-6:2018 §6 (HSI refinement, by reference); ASPICE 4.0 SYS.3 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | Safety MCU (STM32H7 "panda") and its interfaces: B‡ (see [WP-S-02 §2.1](WP-S-02-technical-safety-requirements.md)) |
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
- operating modes and power states, §9.

All facts are taken from the firmware source at the baseline. **Pin assignments and electrical behaviour must be confirmed against the device schematic** ([WP-H-02](../04-hardware/WP-H-02-hardware-design.md) OI-1); firmware shows only what the MCU drives or reads. Both board variants are listed: "tres" (comma 3X) and "cuatro" (comma four). Which one is the reference device is open ([WP-C-01](../02-concept/WP-C-01-item-definition.md) OI-2).

Paths are under `panda/board/` unless prefixed. HSI IDs (HSI-nn) are referenced from SWSRs ([WP-W-02](../05-software/WP-W-02-software-safety-requirements.md)) and HWSRs ([WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md), whose §6 proposed the hardware entries that this document adopts).

## 2. Interface summary

| HSI | Interface | HW resource | SW owner | Safety relevance | ASIL | TSR / HWSR |
|---|---|---|---|---|---|---|
| HSI-01 | SoC ↔ MCU SPI link | SPI4, DMA2 streams 2/3, SRAM1/2 buffers | `drivers/spi.h`, `stm32h7/llspi.h`; host `openpilot/selfdrive/pandad/spi.cc` | FFI; carries commands and configuration | B‡ | TSR-407…413; HWSR-401 |
| HSI-02 | Control requests over SPI endpoint 0 | — | `main_comms.h:63-322` | Mode set, heartbeat, relay debug, CAN config | B‡ | TSR-407, 409, 511…513 |
| HSI-03 | CAN packet stream over SPI endpoints 1/3 | SPI4 | `can_comms.h` | Actuation commands, RX data to SoC | B‡ | TSR-410, 411 |
| HSI-04 | FDCAN1–3 and transceivers | FDCAN, transceiver enable GPIOs | `drivers/fdcan.h`, `stm32h7/llfdcan.h`, `boards/*.h` | Actuation TX, RX for gating, forwarding | B‡ | TSR-401…406, 508, 704, 707; HWSR-508 |
| HSI-05 | Harness relay drive | GPIO (open-drain, active-low) | `drivers/harness.h` | Blocks camera actuation; restores PCS path | B‡ / B | TSR-506, 706; HWSR-506 |
| HSI-06 | Harness orientation sense | ADC1 ch4/ch17 on SBU1/SBU2 | `drivers/harness.h` | CAN routing, relay pin mapping | B | TSR-701; HWSR-701 |
| HSI-07 | Ignition line | SBU GPIO input | `drivers/harness.h:35-52` | Heartbeat timeout selection, power states | B | TSR-510; HWSR-510 |
| HSI-08 | Reset / boot pins from SoC | SoC GPIO → MCU NRST, BOOT0 | `openpilot/common/hardware/comma/hardware.py:400-419` | Firmware substitution; safe state on reset | B‡ (+CS) | TSR-502, 511; HWSR-502c |
| HSI-09 | Watchdog | IWDG1 (unused), software timestamp check | `stm32h7/stm32h7_config.h:43`, `drivers/simple_watchdog.h` | MCU hang detection | B‡ | TSR-501; HWSR-501 |
| HSI-10 | Fault / health monitors | NVIC, RCC CSS, DTS, ADC, interrupt-rate counters | `sys/faults.h`, `drivers/interrupts.h`, `drivers/registers.h`, `stm32h7/lldts.h` | Platform fault detection | B‡ | TSR-502…505, 509 |
| HSI-11 | Siren | DAC/DMA + codec over I2C5 (board-dependent) | `drivers/fake_siren.h`, `boards/*.h` | SoC-independent warning | B | TSR-516 |
| HSI-12 | Flash and bootstub | Flash bank 1, sector 0 bootstub, app at `0x08020000` | `bootstub.c`, `flasher.h`, `stm32h7/llflash.h` | Firmware integrity | B‡ (+CS) | TSR-503, 511, 514 |
| HSI-13 | Supply measurement | ADC1 (input divider) | `boards/*.h` | Supply monitoring | B | TSR-505; HWSR-505b |
| HSI-14 | MPU, RAM ECC (to be added) | Cortex-M7 MPU, RAMECC | new | Memory protection | B‡ | TSR-503, 507 |

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
| `0x262`, `0x1D3`, `0xB4` | EPS_STATUS, PCM_CRUISE_2, SPEED | TBD | yes (DBC) | no | proposed (TSR-110, 405) |

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
| IWDG1 | defined as `IND_WDG` (`stm32h7/stm32h7_config.h:43`), not initialised | started before app, window mode, serviced after safety task completion, timeout ≤ 0.2 s | 501 |
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

## 10. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Confirm pin assignments, relay driver, transceiver enable pull-ups and GPIO reset behaviour against the schematic (WP-H-02 OI-1) | HW lead | G2 |
| OI-2 | Define the SPI residual-error target and select the CRC; specify the sequence-counter format (with WP-S-07) | SW lead | G3 |
| OI-3 | Define the release control-request whitelist per mode (§4.2) and record it in WP-W-02 | SW lead | G3 |
| OI-4 | Define the MPU region map so SPI/USB DMA buffers cannot overlap safety state | SW lead | G3 |
| OI-5 | Align host and MCU SPI buffer sizes or document why they differ | SW lead | G3 |
| OI-6 | Fix the reference board variant (tres/cuatro) and drop the other column | Maintainer | G1 |
