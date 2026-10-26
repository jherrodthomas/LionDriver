# WP-H-06 Hardware integration and verification specification and report

| Field | Value |
|---|---|
| Work product | WP-H-06 Hardware integration and verification specification and report |
| Standard reference | ISO 26262-5:2018 §10 (hardware integration and verification); ISO 26262-8:2018 §9 (verification), §13 (qualification tests of HW components); ASPICE 4.0 HWE.3, HWE.4 |
| Version | 0.11 (VS-HW-06 points to WP-S-04 M-14, the watchdog's clock spread measured on the bench, DQ-134 A; no case or criterion changed; 2026-10-25). 0.10 (Figure 2-1 and §2.2 re-based from a relay box to the harness box v3 switches, closing wiring OI-W-7; VS-HW-13 checks logical bus 0 = car side in both orientations and a forced wrong reading; 2026-10-20). 0.9 (bench wiring drawn: Figure 2-2 HIL bench and Figure 3-1 harness box bench, WireViz, [`wiring/`](wiring/README.md); 2026-10-20). 0.8 (bench checklist and result sheet for VS-HW-02, VS-HW-22…24 linked; one reversibly modified box suffices; 2026-10-16). 0.7 (DQ-209 option A: VS-HW-02 and VS-HW-22…24 are the decided route for the harness box; 2026-10-16). 0.6 (HIL bench deferred by the lead, DQ-049: T-HIL and FI cases blocked; 2026-10-16). 0.5 (§3.1 bench procedures for VS-HW-22…24; VS-HW-24 adds the logic-threshold check and waits for the DG419LE ratings, DFM-ACT-015; RR-2026-010 F-05; 2026-10-16). 0.4 (harness box v3 drawing: VS-HW-02 re-scoped, VS-HW-22…24 added for the analog-switch failure behaviour; [RR-2026-010](reviews/RR-2026-010.md); 2026-10-15). 0.3 (§2.1 diagram redrawn as Figure 2-1; text version kept; 2026-10-13). 0.2 (verification status for the integrated envelope changes; 2026-10-12). 0.1 |
| Status | Draft (specification); results section is a template — **Not yet executed** |
| ASIL / scope | ASIL C (provisional, SG-01) / ASIL B (SG-02…SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `bf6ce8c` (status update 2026-10-12; panda `b790fca`) |

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
they are reused as a starting point where noted, but their past results are not evidence. The
LionDriver HIL script for the watchdog (`panda/tests/hitl/test_10_hw_watchdog.py`, panda `b790fca`)
is implemented and has not been run (bench not built, GAP-30; [HIL bench plan](../05-software/hil-bench/README.md)).

**HIL bench deferred (2026-10-14).** The lead chose not to buy the HIL bench parts for now ([DQ-049](../01-management/decisions/register.yaml), option B). Every case with method T-HIL or FI is therefore blocked, no change earns on-device test credit, and G4 cannot pass until the bench is built. The harness box cases VS-HW-02 and VS-HW-22…24 (§3.1) do not need the HIL bench: they need a spare box, a CAN interface, a lab supply and a scope, and their spare-box cost is part of DQ-209.

## 2. Test environment: HIL bench (decision D-04)

### 2.1 Configuration

![Figure 2-1: HW integration test configuration with the Linux bench PC, panda jungle or 3-bus CAN interface, programmable power supply, reference comma device, Toyota TSS2 harness with instrumented harness box v3, optional forward camera and additional instruments](figures/fig-h06-2-1-hil-configuration.svg)

*Figure 2-1.* The HIL bench for hardware integration: the bench PC controls the CAN interface, the supply and the reference device; the harness and harness box are instrumented with probes on the SBU1 drive and on the U1/U2 switch pins (the box has analog switches and no relay coil, [RR-2026-010](reviews/RR-2026-010.md) F-04; Figure 2-2 draws the same probes). Dashed elements are optional. Source: [`figures/fig-h06-2-1-hil-configuration.svg`](figures/fig-h06-2-1-hil-configuration.svg); change it together with the table below and §2.2.

<details><summary>Text version of Figure 2-1</summary>

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
    │ CAN pairs (car side / camera side)│ harness box v3 (probes:  │
    └───────────────────────────────────┤ SBU1 drive, U1/U2 switch │
                                        │ pins; no relay coil)     │
                                        └──────────────────────────┘
  Additional instruments: oscilloscope / logic analyser on SBU1, U1/U2, CAN lines,
  NRST and BOOT0; thermal chamber or heat gun + thermocouple; SWD probe (debug build
  only, for fault injection); optional: real forward camera on the camera-side bus.
```

</details>

![Figure 2-2: HIL bench wiring at instrument level: bench PC over USB to the panda jungle or CAN interface, the programmable supply, the reference device and a scope; jungle on the car and radar buses at the car connector X2 and on the camera bus at X1; supply on IGN at X2; device on the box receptacle by the OBD-C cable; probes on SBU1, the U1/U2 switch pins, car CAN and NRST or BOOT0](wiring/bench-hil.svg)

*Figure 2-2.* Figure 2-1 as wiring, with the harness pins of [WP-H-02](WP-H-02-hardware-design.md) §3.6. Not built
(DQ-049). Probes sit on SBU1 and the U1/U2 switch pins, since the harness box has no relay coil
([RR-2026-010](reviews/RR-2026-010.md)). Source: [`wiring/bench-hil.yaml`](wiring/bench-hil.yaml), drawn by
`wiring/make_wiring.py`.

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
| Hardware: SBU1 drive forced or opened, R2/R3 lifted, D2/D3 bridged, box VIN removed (harness box v3, §3.1) | Intercept switch failure behaviour (VS-HW-22…24) | Reversible on the spare box if done as in §3.1; destructive otherwise |
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
| VS-HW-02 | Harness box inspection against the published v3 drawing | HWSR-502a, -506, -506d, -506e, -702 | Spare harness box | Open the box; compare parts and wiring with the v3 drawing ([RR-2026-010](reviews/RR-2026-010.md) HB-01…HB-06): U1/U2 part number and marking, R2/R3 values, D1–D4, Q6, switch supply from VIN | Box matches the drawing, or the differences are recorded and the DFMEA/FMEDA updated. *Expected result for HWSR-702: fail* (two powered analog switches in the stock path, RR-2026-010 F-01) | Inspection (A) | — |
| VS-HW-03 | Relay failure detection — stuck released | HWSR-506a, -506b; FSR-01.11 | Car mode, engaged, stock camera traffic on bus 2 | Bridge the relay contacts in the stock position (or open coil) | Relay malfunction detected and all actuation TX blocked; **today**: within 1–2 s (`opendbc_repo/opendbc/safety/safety.h:372-380`); **target**: ≤ 0.3 s (HWSR-506a, after DC-03). Reported to SoC; host immediate-disable | T-HIL, FI | DC-03 for target |
| VS-HW-04 | Relay failure detection — stuck intercepting | HWSR-506a, -702; SG-07 | SILENT mode, camera PCS traffic on bus 2 | Force relay energised (coil supplied externally) while firmware commands release | Mismatch detected and reported within ≤ 0.3 s. **Expected today: not detected** (GAP-12) | T-HIL, FI | DC-03 |
| VS-HW-05 | Debug relay command gated | HWSR-506c | Release build | Send `0xc5` | Relay state unchanged; command rejected | T-HIL | DC-09 |
| VS-HW-06 | Watchdog reset behaviour (after fix) | HWSR-501, -501a–c, -502b; FSR-01.09 | Fault-injection build, car mode, relay energised, engaged | Inject: (a) infinite loop in main context; (b) infinite loop in tick ISR; (c) interrupts disabled; (d) too-early servicing (window); (e) stop servicing from the SoC side (must have no effect on IWDG) | (a)–(d): MCU reset; safe state reached within ≤ 0.2 s total (≤ 0.1 s detection + ≤ 0.1 s reaction, FSC §8); reset cause = IWDG reported after restart. (e): no reset, heartbeat path handles it | T-HIL, FI | DC-01 (implemented 2026-10-12, panda `9f60e17`, not verified on hardware). Script: `panda/tests/hitl/test_10_hw_watchdog.py` implemented, not run, covers (a)–(d) plus a safety-task hang; (e) not covered. The timeout itself, last feed to reset over the LSI spread on each board and at the ends of the temperature range (with VS-HW-15), is measurement M-14 of [WP-S-04 §6](../03-system/WP-S-04-timing-ftti-budget.md#6-measurement-plan) (added 2026-10-25, DQ-134 A); its result feeds the WP-S-04 OI-7 margin rule |
| VS-HW-07 | Watchdog cannot be disabled | HWSR-501c | Release build | Attempt every host command path, stop-mode entry, firmware update path | IWDG remains active whenever the relay can be driven; firmware update completes without spurious reset | T-HIL | DC-01 (implemented 2026-10-12, not verified on hardware); no script yet |
| VS-HW-08 | Exception and fatal-assert paths | HWSR-502b | Fault-injection build | Trigger HardFault, NMI, MemManage, unused vector, `assert_fatal` | Each ends in reset or safe state; never a hang with relay energised | T-HIL, FI | DC-08 |
| VS-HW-09 | Power brown-out and dropouts | HWSR-505, -505a, -502, -502a | Car mode, engaged | Programmable supply: (a) dropouts 1 ms–1 s to 0 V; (b) slow ramp down to 0 V and back; (c) plateau at levels between nominal and BOR; (d) cranking-type profile (ISO 16750-2 style, informative) | No actuation frame outside the envelope at any point; relay released or device operating correctly; after recovery the device starts in SILENT and needs re-engagement; PVD/BOR behaviour recorded | T-HIL | DC-07 for PVD |
| VS-HW-10 | Supply over-voltage (non-destructive) | HWSR-505b | — | Raise input within the rated range (rating from UK-08) | Reported; safe state above threshold (after DC-10) | T-HIL | DC-10 |
| VS-HW-11 | CAN bus-off and error-passive (car side) | HWSR-508, -508b, -508c | Car mode, engaged | (a) Short CAN-H/CAN-L on car side; (b) remove termination; (c) inject error frames until bus-off; (d) RX open on XCVR1 | Bus-off detected; actuation safe state; driver warning via SoC; recovery behaviour per spec; (d) RX timeout within FTTI budget | T-HIL, FI | TSR-4xx timeouts |
| VS-HW-12 | Transceiver fault does not disturb stock path | HWSR-508a | SILENT, relay released | Force panda XCVR3/XCVR1 dominant (fault-injection build or transceiver TXD forced) | Stock camera↔car traffic continues (or the fault is shown impossible by analysis of the topology, WP-H-02 OI-6) | T-HIL, A | — |
| VS-HW-13 | Harness reversed / orientation | HWSR-701, -701a | — | Connect harness normal, flipped and disconnected, with and without ignition (reuse `panda/tests/hitl/test_9_harness.py` logic); in each orientation send a frame on logical bus 0 and on bus 2 and see where it arrives; force a wrong orientation reading (SBU sense forced, debug build) with the stock camera running; disconnect harness while relay driven | Orientation detected correctly in all cases; logical bus 0 is the car side and bus 2 the camera side in both orientations (a flipped reading swaps them, `drivers/can_common.h:130-135`); the intercept drive and ignition sense follow orientation; with a forced wrong reading the switch stays in pass-through and the relay-malfunction check blocks TX (FM-HAR-02 in §4.9 of the hardware FMEA); disconnection while driving leads to safe state and warning | T-HIL | — |
| VS-HW-14 | Ignition loss and ignition-line faults | HWSR-510, -510a | Car mode, engaged | (a) Ignition line low while driving; (b) line open; (c) line shorted to the "on" level with engine off | (a)/(b): heartbeat timeout switches to the 2 s value; no actuation outside envelope; (c): behaviour documented, including power drain; matches WP-H-03 FM-IGN rows | T-HIL | — |
| VS-HW-15 | Thermal | HWSR-509, -509a | Thermal chamber or controlled heating | Raise ambient to the device rating; stall fan | DTS reported correctly vs thermocouple; safe state above the MCU threshold (after DC-10); host thermal policy acts; no actuation anomaly | T-HIL | DC-10 |
| VS-HW-16 | Clock failure (analysis + test where accessible) | HWSR-504, -504a | — | If a test pad exists, stop HSE; otherwise analyse CSS path from RM0468 and code (`panda/board/stm32h7/clock.h:119`, `panda/board/early_init.h:73-76`) | NMI → reset → safe state; documented hang in `clock_init` is with relay released | T-HIL or A | — |
| VS-HW-17 | RAM/flash ECC and flash CRC handling | HWSR-503–503c | Fault-injection build | Inject ECC errors if the silicon allows; corrupt flash image copy (spare device) | Double error → safe state; single error counted; CRC mismatch → safe state at start-up and at run time | T-HIL, FI, A | DC-05 |
| VS-HW-18 | MPU | HWSR-507 | Fault-injection build | Write to protected safety data from a comms handler; overflow stack | MemManage → safe state | T-HIL, FI | DC-06 |
| VS-HW-19 | SoC reset / boot-mode control | HWSR-502, -502c | Car mode, relay energised | Assert `STM_RST_N`; assert `STM_BOOT0` + reset (via `openpilot/common/hardware/comma/hardware.py:401-419`) | Relay released and no TX during reset and in ROM bootloader | T-HIL | — |
| VS-HW-20 | Register divergence reaction | HWSR-503d | Fault-injection build | Overwrite a monitored register (e.g. relay GPIO mode) via SWD | Detected within the check period and safe state (after DC-04); today: report-only (`panda/board/drivers/registers.h:56-70`) | T-HIL, FI | DC-04 |
| VS-HW-21 | SoC-independent warning (siren) | FSR-02.05 | Car mode, engaged | Stop the SoC heartbeat | Acoustic warning audible within the FSC timing; check whether it works with the SoC powered down (independence of the audio path, WP-H-02 UK-07) | T-HIL | — |
| VS-HW-22 | Stock path with the harness box unpowered | HWSR-502a, -702; DFM-020 | Camera and car (or bench nodes) powered; box VIN removed (ignition branch open, no comma power) | §3.1: frame exchange and bus levels with VIN normal, open, shorted to GND and with the device unpowered on the cable; VIN ramp to find the lowest working supply | Stock path works and bus levels meet the ISO 11898-2 receiver thresholds in every unpowered case, or the failure is recorded as confirming RR-2026-010 F-02 | T (bench) | VS-HW-02 |
| VS-HW-23 | Release default with the pull-down open | HWSR-506, -506e, -711a; DFM-010.C3 | Box with R2 or R3 lifted; SBU1 driven (intercept) | §3.1: release SBU1 by four routes (source open, MCU in reset, cable unplugged, device unpowered); record the switch state over 10 min at three temperatures; intact-box changeover time as reference | Pass-through restored within ≤ 20 ms in every case, or the floating-IN behaviour is recorded as confirming RR-2026-010 F-03 | T (bench, fault injection) | VS-HW-02 |
| VS-HW-24 | Switch supply stress, logic threshold and pass-through signal integrity | HWSR-506d, -711a; DFM-010.C4, DFM-011.C2, DFM-021 | Box on a programmable supply; DG419LE ratings confirmed (DFM-ACT-015) | §3.1: (a) steady VIN 9…16 V and a transient profile capped at the confirmed rating; (b) SBU1 changeover threshold vs VIN and temperature; (c) CAN signal integrity through U1/U2 with ground offset; (d) clamp diode D2, then D3, forced short | (a) switch works at every steady level and VIN at U1/U2 stays within the absolute maximum; (b) threshold at least 1 V below the SBU1 high level; (c) ISO 11898-2 thresholds met, no error frames in 10 min; (d) effect recorded against DFM-021 | T (bench) | VS-HW-02, DFM-ACT-015 |

### 3.1 Bench procedures for the harness box (VS-HW-22…24)

The lead chose to keep comma's harness box and bench-test it ([DQ-209](../01-management/decisions/register.yaml), option A, 2026-10-16), so VS-HW-02 and these three cases are now the evidence for that route: their results become the assumption of use for the stock path. Option A includes one spare box. These three cases test comma's harness box on its own, outside the vehicle, against the failure behaviour derived from the
v3 drawing in [RR-2026-010](reviews/RR-2026-010.md). They need a CAN interface, a lab supply and a scope, not the HIL bench of
§2 (DQ-049). Run them on a box that VS-HW-02 has matched to the drawing; record any difference first, because the steps name
v3 reference designators.

The steps below are run from the [bench checklist and result sheet](bench/VS-HW-22-24-checklist.md), which orders them so one spare box is enough and records every value.

**Common set-up (all three cases).**

| Item | Set-up |
|---|---|
| Unit under test | Spare Toyota harness box, inspected in VS-HW-02. VS-HW-23 and VS-HW-24 (d) modify it reversibly (R2 lifted and resoldered, D2/D3 bridged externally), so one box is enough when run in the order of the [bench checklist](bench/VS-HW-22-24-checklist.md); use a second box if one is available |
| Camera side | CAN interface channel A on the camera connector (CAN2), as the camera node, 120 Ω termination as on the car. Optional: the real camera instead |
| Car side | CAN interface channel B on the car connector (CAN0), as the car ADAS node, 120 Ω termination |
| Box supply | Lab supply on the IGN_12 pin (through D1 as on the car), current-limited to 0.5 A; comma power (J2) not connected unless the step says so |
| SBU1 drive | Lab source, 0–5 V, 1 kΩ in series (the device-side driver is unknown, WP-H-02 UK-06), or the reference device where the step says so |
| Instruments | 4-channel scope with a differential probe; DMM; thermocouple on U1; thermal chamber or heat gun for the temperature steps |
| Traffic | 500 kbit/s. Channel A sends a 10 ms frame (ID 0x343 payload pattern), channel B a 10 ms frame (ID 0x1AA); both log error counters |
| Records | Scope captures, CAN logs with error counters, supply current, box serial and harness letter (F-13), ambient temperature |

![Figure 3-1: bench wiring for VS-HW-22 to 24: CAN interface channel A on camera connector X1 pins 5 and 11 and channel B on car connector X2 pins 5 and 11, each with 120 ohm; lab supply on X2 pin 7 (IGN) and pin 10; 0 to 5 V source through 1 kohm on SBU1 at a USB-C breakout on the box receptacle; scope on car CAN, VIN and SBU1; fault-injection points FI-1 IGN open, FI-2 VIN to GND through 1 ohm, FI-3 R2/R3 open, FI-4 D2/D3 bridged](wiring/bench-box-vs-hw-22-24.svg)

*Figure 3-1.* The common set-up above as wiring, with the four box modifications of the checklist as FI-1…FI-4. Parts
this section does not name (mating plugs, USB-C breakout) are marked "to choose". Source:
[`wiring/bench-box-vs-hw-22-24.yaml`](wiring/bench-box-vs-hw-22-24.yaml).

**VS-HW-22: stock path with the box unpowered (F-02, DFM-020).**

1. Reference: VIN = 13.5 V, SBU1 open. Exchange frames for 60 s; record error counters and the differential levels at both
   connectors. This is the expected pass-through.
2. Open the IGN_12 pin (VIN floating). Repeat step 1. Also measure VIN and the CAN_H/CAN_L levels to GND on both sides, to
   see whether D2/D3 pull the buses towards the dead rail.
3. Short VIN to GND through 1 Ω (models the D4 short, DFM-020.C2). Repeat step 1.
4. Plug the reference device into the OBD-C port, unpowered. Open IGN_12 again. Repeat step 1, so that the device input also
   loads VIN.
5. Ramp VIN from 0 to 13.5 V and back at 0.1 V/s while exchanging frames. Record the VIN at which pass-through starts and
   stops working.

Pass: in steps 2–4 frames pass both ways for 60 s without error frames, and the differential levels meet the ISO 11898-2
receiver thresholds (recessive below 0.5 V, dominant above 0.9 V). A failure in any step confirms F-02: record it, keep
DFM-020 at its current rating, and add the measured values to DQ-209.

**VS-HW-23: release default with the pull-down open (F-03, DFM-010.C3).**

1. Reference on an intact box, VIN = 13.5 V: drive SBU1 to 5 V and check intercept (camera frames no longer reach channel
   B). Open SBU1 and measure the changeover time from the SBU1 edge to the first camera frame on channel B, and on the
   scope at U1 COM/NC. This also gives the HWSR-711a value.
2. On the modified box (R2 lifted at one end): drive SBU1 to 5 V, confirm intercept, then open SBU1. Record the switch state
   by frame exchange at 0 s, 1 s, 10 s, 1 min and 10 min.
3. Repeat step 2, releasing SBU1 through the reference device in three ways: MCU held in reset (NRST), OBD-C cable unplugged,
   and device power removed.
4. Repeat step 2 at −20 °C, 25 °C and +85 °C at U1.
5. With the pull-down open, start the reference device and record the harness orientation it reports. SBU1 also carries the
   orientation sense (HB-07), so this may detect an open pull-down at start-up. Analyse the result before claiming it as a
   diagnostic.

Pass: pass-through returns within ≤ 20 ms in every case in steps 2–4. Otherwise record the floating-IN behaviour as
confirming F-03; DFM-010.C3 and HWSR-506e stay open until a hardware change adds a second pull-down or readback (DQ-209).

**VS-HW-24: supply stress, logic threshold and signal integrity (F-05, F-07, F-08).**

Do not start (a) until DFM-ACT-015 has confirmed the DG419LE limits from the datasheet. The transient profile must stay below
the confirmed absolute maximum, except on a sacrificial box.

1. (a) Steady supply: VIN at 9, 12, 13.5, 14.4 and 16 V. At each level check intercept and pass-through by frame exchange,
   and record the supply current. Transients: apply an ISO 16750-2 style profile (superimposed ripple, starting profile,
   suppressed load dump) capped at the confirmed rating. Measure the peak at the U1 V+ pin and record the D4 clamp level.
2. (b) Logic threshold: at VIN 9, 14 and 16 V and at −20, 25 and +85 °C, sweep SBU1 from 0 to 5 V and back at 0.1 V/s.
   Record the level at which the switch changes over in each direction.
3. (c) Signal integrity: 500 kbit/s at about 80 % bus load from channel A through U1/U2 to channel B for 10 min. Repeat with
   the camera-side ground offset by −1 V and +1 V from the car side. Record the eye at the channel B receiver, the bit timing
   and the error counters. Compare with a direct cable between the two channels.
4. (d) Clamp short, on the second box: bridge one D2 diode (CAN0_H to GND). Record which bus fails, the device reaction
   (canError, RX timeouts) and whether the camera path still works. Repeat for D3 (CAN2).

Pass: (a) the switch works at every steady level and the U1 V+ peak stays within the absolute maximum; (b) the switch changes
over at least 1 V below the 5 V SBU1 high level at every point; (c) ISO 11898-2 receiver thresholds met and no error frames in
10 min; (d) the effect is recorded against DFM-021. A failed (a) or (b) confirms DFM-010.C4 or DFM-011.C2 and goes to DQ-209.

## 4. Integration sequence

1. Bench characterization (no device): CAN interface timing, supply profiles, scope triggers.
2. Device + harness, release firmware, no faults: VS-HW-01, -13, -14, -19, -21 (baseline behaviour).
3. Fault-injection firmware: VS-HW-06…-08, -17, -18, -20 (only after the related DC exists: DC-01 implemented 2026-10-12; DC-04…DC-08 open).
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
| 502 | 01, 09, 19 |
| 502a | 01, 09, 19, 22 |
| 502b | 08 |
| 502c | 19 |
| 503–503c | 17 |
| 503d | 20 |
| 504, 504a | 16 |
| 505–505b | 09, 10 |
| 506 | 01, 02, 23 |
| 506a | 03, 04 |
| 506b | 03 |
| 506c | 05 |
| 506d | 02, 24 |
| 506e | 02, 23 |
| 507 | 18 |
| 508–508c | 11, 12 |
| 509, 509a | 15 |
| 510, 510a | 14 |
| 701, 701a | 13 |
| 702 | 01, 02, 22 |
| 703 | 02 (inspection), 13 |
| 711a | 23, 24 |

## 7. Results (template) — Not yet executed

| VS | Date | Firmware commit | Device serial / rev | Harness | Result (Pass/Fail/Blocked) | Measured value | Evidence (log/scope file) | Deviation / PR ref |
|---|---|---|---|---|---|---|---|---|
| VS-HW-01 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-02 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-03 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-04 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-05 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-06 | — | — | — | — | **Not yet executed** (bench not built, GAP-30) | — | — | — |
| VS-HW-07 | — | — | — | — | **Not yet executed** (bench not built, GAP-30) | — | — | — |
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
| VS-HW-22 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-23 | — | — | — | — | **Not yet executed** | — | — | — |
| VS-HW-24 | — | — | — | — | **Not yet executed** | — | — | — |

Verification report summary (to be written after execution): requirements covered, failed,
blocked; deviations and their problem reports ([WP-P-03](../07-supporting/WP-P-03-problem-resolution.md)).

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Build and characterize the HIL bench (D-04; [WP-M-03](../01-management/WP-M-03-project-plan.md) task 5.1). **Deferred by the lead** (DQ-049, option B, 2026-10-14): no parts bought; reopen with the lead before G4 | G3 |
| OI-2 | Obtain spare devices and harnesses for destructive tests | G3 |
| OI-3 | Check STM32H7 ECC error-injection and IWDG test options (RM0468) for VS-HW-16/-17 | G3 |
| OI-4 | Device input voltage rating (WP-H-02 UK-08) before VS-HW-09/-10 | G3 |
| OI-5 | The upstream relay test is a TODO (`panda/tests/hitl/test_9_harness.py:7`); write VS-HW-01/-03/-04 as new automated tests in the fork | G3 |
| OI-6 | Align with system integration tests in [WP-S-08](../03-system/WP-S-08-system-integration-test.md) to avoid duplicate execution | G3 |
