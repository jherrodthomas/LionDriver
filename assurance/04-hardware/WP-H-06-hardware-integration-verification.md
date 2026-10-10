# WP-H-06 Hardware integration and verification specification and report

| Field | Value |
|---|---|
| Work product | WP-H-06 Hardware integration and verification specification and report |
| Standard reference | ISO 26262-5:2018 §10 (hardware integration and verification); ISO 26262-8:2018 §9 (verification), §13 (qualification tests of HW components); ASPICE 4.0 HWE.3, HWE.4 |
| Version | 0.1 |
| Status | Draft (specification); results section is a template — **Not yet executed** |
| ASIL / scope | ASIL C (provisional, SG-01) / ASIL B (SG-02…SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Specifies the hardware-level verification of the safety-relevant hardware of LD-SDA
([WP-H-02](WP-H-02-hardware-design.md) §3.2) against the hardware safety requirements
([WP-H-01](WP-H-01-hardware-safety-requirements.md)), including the fault-injection tests that
justify the diagnostic-coverage claims of [WP-H-03](WP-H-03-hardware-safety-analysis-fmeda.md).

LionDriver does not design or manufacture the hardware (T-04, T-07). "Hardware integration" here
means: the comma device with the LionDriver panda firmware, integrated with the harness and a
vehicle-representative CAN environment. Hardware design verification activities that need the
manufacturer (environmental, EMC, durability) are covered by supplier evidence through
[WP-H-07](WP-H-07-hardware-component-qualification.md) and are **out of scope of LionDriver testing**
(§5).

No test in this document has been executed. The upstream panda HITL tests
(`panda/tests/hitl/test_*.py`) ran on comma's device farm, which the fork cannot use (GAP-30);
they are reused as a starting point where noted, but their past results are not evidence.

## 2. Test environment: HIL bench (decision D-04)

### 2.1 Configuration

```
 ┌───────────── Bench PC (Linux) ─────────────┐
 │ test runner (pytest), log capture,          │
 │ Corolla log replay (opendbc/safety replay), │
 │ fault-injection control                     │
 └──┬─────────────┬───────────────┬────────────┘
    │ USB         │ USB/GPIO      │ USB
 ┌──┴────────┐ ┌──┴────────────┐ ┌┴──────────────────────────┐
 │ Panda     │ │ Programmable  │ │ Reference comma device     │
 │ jungle or │ │ power supply  │ │ (fixed revision, LionDriver│
 │ CAN I/F   │ │ (0–20 V, slew,│ │  panda FW + openpilot)     │
 │ (3 buses: │ │  dropouts)    │ └──────┬─────────────────────┘
 │  car, cam,│ └──────┬────────┘        │ harness connector
 │  OBD)     │        │ 12 V           ┌┴─────────────────────────┐
 └──┬────────┘        └────────────────┤ Toyota TSS2 harness +    │
    │ CAN pairs (car side / camera side)│ relay box (instrumented: │
    └───────────────────────────────────┤ contact state probe,     │
                                        │ coil current probe)      │
                                        └──────────────────────────┘
  Additional instruments: oscilloscope / logic analyser on relay coil, CAN lines,
  NRST and BOOT0; thermal chamber or heat gun + thermocouple; SWD probe (debug build
  only, for fault injection); optional: real forward camera on the camera-side bus.
```

| Item | Requirement |
|---|---|
| Device | One reference comma device of the revision fixed in WP-C-01, plus one spare for destructive tests |
| Harness | The Toyota harness part used in the reference configuration; second unit to open for inspection (VS-HW-02) |
| CAN | Panda jungle (supports harness orientation and ignition simulation, as used by `panda/tests/hitl/test_9_harness.py`) or an equivalent 3-channel CAN interface |
| Firmware | Release build of the LionDriver panda fork; separate fault-injection build with documented differences (configuration item per [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)) |
| Calibration | Instruments with calibration records; bench characterization report before first use |
| Tool qualification | Bench software classified per [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) |

### 2.2 Fault-injection techniques

| Technique | Used for | Limitation |
|---|---|---|
| Firmware fault-injection build (forced hang, forced exception, corrupted variable, stopped service of the watchdog) | IWDG, exception paths, fault reactions | Changes the software under test; must be argued representative |
| SWD debugger writes (halt core, flip RAM/register bits) | Hang, data corruption, register divergence | Halting the core also stops some peripherals; debug must be enabled |
| Hardware: hold NRST, assert BOOT0 | Reset safe state, bootloader state | Needs access to the SoC-side GPIO or test pads |
| Hardware: relay coil open/short (in the harness box), contact bridging | Relay failure detection | Destructive on the harness unit |
| Hardware: CAN line short (CAN-H to CAN-L, to GND), open, termination removal | Transceiver/bus faults | Must not damage vehicle-representative nodes |
| Power: dropouts, slow ramps, brown-out plateau, over-voltage within safe limits | Supply monitoring | Device input rating unknown (WP-H-02 UK-08) |
| Clock: HSE disturbance (only if a test pad exists) | CSS | Probably not accessible on COTS PCB — fall back to analysis |
| ECC: STM32H7 test features for ECC error injection, if any | RAM/flash ECC handling | Availability to verify in RM0468; otherwise analysis |

## 3. Verification specifications

Common pass criteria terms: **safe state** = relay released (stock path, measured at the
contacts), no item-originated actuation frame (`0x2E4`, `0x343`, `0x191`, `0x412`, `0x1D2`) on the
car-side bus, and the fault reported in health. Timing is measured from fault injection to the
safe state on the scope/CAN log.

| ID | Title | Verifies | Preconditions | Procedure (summary) | Pass criteria | Method | Depends on |
|---|---|---|---|---|---|---|---|
| VS-HW-01 | Relay switching and default state | HWSR-502, -502a, -506, -702; AOU-13 | Device in harness, bench powered | (1) Unpowered: measure camera↔car continuity. (2) Power on, SILENT: measure. (3) Car safety mode: measure. (4) Remove device power while relay energised. (5) Hold MCU in reset (NRST) while relay energised | (1),(2),(4),(5): stock path closed, camera↔car continuity. (3): stock path open, camera↔panda bus 2 and panda bus 0↔car closed. Switching time recorded | T-HIL | — |
| VS-HW-02 | Harness relay inspection | HWSR-502a, -506, -506d, -702 | Spare harness | Open relay box; identify relay part number, contact form, coil drive, any other active parts in the stock path | Relay type, ratings and de-energised state documented; no active part in the stock path | Inspection (A) | — |
| VS-HW-03 | Relay failure detection — stuck released | HWSR-506a, -506b; FSR-01.11 | Car mode, engaged, stock camera traffic on bus 2 | Bridge the relay contacts in the stock position (or open coil) | Relay malfunction detected and all actuation TX blocked; **today**: within 1–2 s (`opendbc_repo/opendbc/safety/safety.h:372-380`); **target**: ≤ 0.3 s (HWSR-506a, after DC-03). Reported to SoC; host immediate-disable | T-HIL, FI | DC-03 for target |
| VS-HW-04 | Relay failure detection — stuck intercepting | HWSR-506a, -702; SG-07 | SILENT mode, camera PCS traffic on bus 2 | Force relay energised (coil supplied externally) while firmware commands release | Mismatch detected and reported within ≤ 0.3 s. **Expected today: not detected** (GAP-12) | T-HIL, FI | DC-03 |
| VS-HW-05 | Debug relay command gated | HWSR-506c | Release build | Send `0xc5` | Relay state unchanged; command rejected | T-HIL | DC-09 |
| VS-HW-06 | Watchdog reset behaviour (after fix) | HWSR-501, -501a–c, -502b; FSR-01.09 | Fault-injection build, car mode, relay energised, engaged | Inject: (a) infinite loop in main context; (b) infinite loop in tick ISR; (c) interrupts disabled; (d) too-early servicing (window); (e) stop servicing from the SoC side (must have no effect on IWDG) | (a)–(d): MCU reset; safe state reached within ≤ 0.3 s total (≤ 0.2 s detection + ≤ 0.1 s reaction, FSC §8); reset cause = IWDG reported after restart. (e): no reset, heartbeat path handles it | T-HIL, FI | DC-01 |
| VS-HW-07 | Watchdog cannot be disabled | HWSR-501c | Release build | Attempt every host command path, stop-mode entry, firmware update path | IWDG remains active whenever the relay can be driven; firmware update completes without spurious reset | T-HIL | DC-01 |
| VS-HW-08 | Exception and fatal-assert paths | HWSR-502b | Fault-injection build | Trigger HardFault, NMI, MemManage, unused vector, `assert_fatal` | Each ends in reset or safe state; never a hang with relay energised | T-HIL, FI | DC-08 |
| VS-HW-09 | Power brown-out and dropouts | HWSR-505, -505a, -502, -502a | Car mode, engaged | Programmable supply: (a) dropouts 1 ms–1 s to 0 V; (b) slow ramp down to 0 V and back; (c) plateau at levels between nominal and BOR; (d) cranking-type profile (ISO 16750-2 style, informative) | No actuation frame outside the envelope at any point; relay released or device operating correctly; after recovery the device starts in SILENT and needs re-engagement; PVD/BOR behaviour recorded | T-HIL | DC-07 for PVD |
| VS-HW-10 | Supply over-voltage (non-destructive) | HWSR-505b | — | Raise input within the rated range (rating from UK-08) | Reported; safe state above threshold (after DC-10) | T-HIL | DC-10 |
| VS-HW-11 | CAN bus-off and error-passive (car side) | HWSR-508, -508b, -508c | Car mode, engaged | (a) Short CAN-H/CAN-L on car side; (b) remove termination; (c) inject error frames until bus-off; (d) RX open on XCVR1 | Bus-off detected; actuation safe state; driver warning via SoC; recovery behaviour per spec; (d) RX timeout within FTTI budget | T-HIL, FI | TSR-4xx timeouts |
| VS-HW-12 | Transceiver fault does not disturb stock path | HWSR-508a | SILENT, relay released | Force panda XCVR3/XCVR1 dominant (fault-injection build or transceiver TXD forced) | Stock camera↔car traffic continues (or the fault is shown impossible by analysis of the topology, WP-H-02 OI-6) | T-HIL, A | — |
| VS-HW-13 | Harness reversed / orientation | HWSR-701, -701a | — | Connect harness normal, flipped and disconnected, with and without ignition (reuse `panda/tests/hitl/test_9_harness.py` logic); disconnect harness while relay driven | Orientation detected correctly in all cases; CAN routing correct; relay pin follows orientation; disconnection while driving leads to safe state and warning | T-HIL | — |
| VS-HW-14 | Ignition loss and ignition-line faults | HWSR-510, -510a | Car mode, engaged | (a) Ignition line low while driving; (b) line open; (c) line shorted to the "on" level with engine off | (a)/(b): heartbeat timeout switches to the 2 s value; no actuation outside envelope; (c): behaviour documented, including power drain; matches WP-H-03 FM-IGN rows | T-HIL | — |
| VS-HW-15 | Thermal | HWSR-509, -509a | Thermal chamber or controlled heating | Raise ambient to the device rating; stall fan | DTS reported correctly vs thermocouple; safe state above the MCU threshold (after DC-10); host thermal policy acts; no actuation anomaly | T-HIL | DC-10 |
| VS-HW-16 | Clock failure (analysis + test where accessible) | HWSR-504, -504a | — | If a test pad exists, stop HSE; otherwise analyse CSS path from RM0468 and code (`panda/board/stm32h7/clock.h:119`, `panda/board/early_init.h:73-76`) | NMI → reset → safe state; documented hang in `clock_init` is with relay released | T-HIL or A | — |
| VS-HW-17 | RAM/flash ECC and flash CRC handling | HWSR-503–503c | Fault-injection build | Inject ECC errors if the silicon allows; corrupt flash image copy (spare device) | Double error → safe state; single error counted; CRC mismatch → safe state at start-up and at run time | T-HIL, FI, A | DC-05 |
| VS-HW-18 | MPU | HWSR-507 | Fault-injection build | Write to protected safety data from a comms handler; overflow stack | MemManage → safe state | T-HIL, FI | DC-06 |
| VS-HW-19 | SoC reset / boot-mode control | HWSR-502, -502c | Car mode, relay energised | Assert `STM_RST_N`; assert `STM_BOOT0` + reset (via `openpilot/common/hardware/comma/hardware.py:401-419`) | Relay released and no TX during reset and in ROM bootloader | T-HIL | — |
| VS-HW-20 | Register divergence reaction | HWSR-503d | Fault-injection build | Overwrite a monitored register (e.g. relay GPIO mode) via SWD | Detected within the check period and safe state (after DC-04); today: report-only (`panda/board/drivers/registers.h:56-70`) | T-HIL, FI | DC-04 |
| VS-HW-21 | SoC-independent warning (siren) | FSR-02.05 | Car mode, engaged | Stop the SoC heartbeat | Acoustic warning audible within the FSC timing; check whether it works with the SoC powered down (independence of the audio path, WP-H-02 UK-07) | T-HIL | — |

## 4. Integration sequence

1. Bench characterization (no device): CAN interface timing, supply profiles, scope triggers.
2. Device + harness, release firmware, no faults: VS-HW-01, -13, -14, -19, -21 (baseline behaviour).
3. Fault-injection firmware: VS-HW-06…-08, -17, -18, -20 (only after DC-01, DC-04…DC-08 exist).
4. Hardware fault injection on spare units: VS-HW-03, -04, -09…-12, -15, -16.
5. Regression subset on every panda firmware change touching `panda/board/**` (selection rule in
   [WP-P-02](../07-supporting/WP-P-02-change-management.md)).

## 5. Out of scope: EMC, environmental and durability

| Topic | Position |
|---|---|
| EMC (emission and immunity, e.g. CISPR 25, ISO 11452, ISO 7637 transients) | Not tested by LionDriver. Rely on supplier evidence (WP-H-07 QE-07). If none exists, record as residual risk; immunity of the safety mechanisms (watchdog, ECC) to disturbances is argued by design |
| Environmental (temperature cycling, humidity, vibration, ISO 16750-3/-4 style) | Supplier evidence; LionDriver performs only the operating-temperature check VS-HW-15 |
| Durability / relay life | Analysis from relay datasheet (VS-HW-02) and field data if available |
| ESD at the harness connector | Supplier evidence |

## 6. Coverage of requirements

| HWSR | VS |
|---|---|
| 401 | Covered by SPI tests in [WP-W-08](../05-software/WP-W-08-embedded-software-testing.md) |
| 501–501c | 06, 07 |
| 501d | Analysis only until DC-02 exists |
| 502, 502a | 01, 09, 19 |
| 502b | 08 |
| 502c | 19 |
| 503–503c | 17 |
| 503d | 20 |
| 504, 504a | 16 |
| 505–505b | 09, 10 |
| 506, 506d | 01, 02 |
| 506a | 03, 04 |
| 506b | 03 |
| 506c | 05 |
| 507 | 18 |
| 508–508c | 11, 12 |
| 509, 509a | 15 |
| 510, 510a | 14 |
| 701, 701a | 13 |
| 702 | 01, 02 |
| 703 | 02 (inspection), 13 |

## 7. Results (template) — Not yet executed

| VS | Date | Firmware commit | Device serial / rev | Harness | Result (Pass/Fail/Blocked) | Measured value | Evidence (log/scope file) | Deviation / PR ref |
|---|---|---|---|---|---|---|---|---|
| VS-HW-01 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-02 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-03 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-04 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-05 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-06 | — | — | — | — | **Not yet executed** (blocked by DC-01) | — | — | — |
| VS-HW-07 | — | — | — | — | **Not yet executed** (blocked by DC-01) | — | — | — |
| VS-HW-08 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-09 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-10 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-11 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-12 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-13 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-14 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-15 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-16 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-17 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-18 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-19 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-20 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-21 | — | — | — | — | **Not yet executed** | — | — | — |

Verification report summary (to be written after execution): requirements covered, failed,
blocked; deviations and their problem reports ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)).

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Build and characterize the HIL bench (D-04; [WP-M-03](../01-management/WP-M-03-project-plan.md) task 5.1) | G3 |
| OI-2 | Obtain spare devices and harnesses for destructive tests | G3 |
| OI-3 | Check STM32H7 ECC error-injection and IWDG test options (RM0468) for VS-HW-16/-17 | G3 |
| OI-4 | Device input voltage rating (WP-H-02 UK-08) before VS-HW-09/-10 | G3 |
| OI-5 | The upstream relay test is a TODO (`panda/tests/hitl/test_9_harness.py:7`); write VS-HW-01/-03/-04 as new automated tests in the fork | G3 |
| OI-6 | Align with system integration tests in [WP-S-08](../03-system/WP-S-08-system-integration-test.md) to avoid duplicate execution | G3 |
