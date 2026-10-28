# Bench checklist: harness box VS-HW-02, VS-HW-22…24

| Field | Value |
|---|---|
| Record type | Test checklist and result sheet for [WP-H-06](../WP-H-06-hardware-integration-verification.md) §3.1 |
| Covers | VS-HW-02 (inspection, prerequisite), VS-HW-22 (box unpowered), VS-HW-23 (pull-down open), VS-HW-24 (supply stress, logic threshold, signal integrity, clamp short, camera-side termination) |
| Version | 0.4 (§F: VS-HW-24 (e), camera-side termination R7/R8 in intercept, from the harness box SPICE pilot prediction, PR #510; later sections renumbered; 2026-10-27). 0.3 (§A: SBU1 source low impedance without the 1 kΩ series resistor, plus a load check; WP-H-06 0.12; 2026-10-27). 0.2 (§A: box-plug crimp part number field, wiring OI-W-3; 2026-10-20). 0.1 (first issue; 2026-10-16) |
| Status | Draft. **Not yet executed** |
| Author | Claude Code (AI-drafted from WP-H-06 §3.1; to be reviewed before first use) |
| Decision | Route chosen by the lead: keep comma's box and bench-test it ([DQ-209](../../01-management/decisions/register.yaml)). The SG-07 SPFM deviation ([DQ-320](../../01-management/decisions/register.yaml), [WP-H-04](../WP-H-04-hardware-metrics.md) §5.3) holds only if these tests pass |

## How to use this sheet

- Copy this file to `results/<date>-<box serial>.md` in this folder for each run, and fill in the copy. Leave this file blank.
- Tick a box only when the step is done. Write a measured value with its unit, never "OK".
- If a step fails, stop that case, fill in the failure row of its result table, and go on with the next case. A failure is a result, not a reason to stop the session.
- Keep the raw data (scope captures, CAN logs) in `results/<date>-<box serial>/` and name each file after its step, e.g. `22-2-levels.png`.
- **Order matters.** The run is laid out so that one spare box is enough, as DQ-209 budgeted. The box is modified only in parts E, F and G, and every modification is reversible. If a second box is available, use it for E, F and G instead.

## A. Session record

| Field | Entry |
|---|---|
| Date and start time | |
| Tester | |
| Box serial / marking | |
| Harness letter and revision (RR-2026-010 F-13) | |
| Box-plug crimp terminal part number, read off the part ([wiring](../wiring/README.md) OI-W-3: comma's drawings say 501648-1000 or 501647-1000) | |
| Reference device and serial (VS-HW-23 step 3 only) | |
| Panda firmware commit (if the device is used) | |
| CAN interface, model and serial | |
| Lab supply, model and serial | |
| Scope and differential probe, model and serial | |
| DMM, model and serial | |
| Thermocouple and reader | |
| Calibration records checked (date of each) | |
| Ambient temperature (°C) | |

## B. Before you start

- [ ] **VS-HW-02 inspection is done** on this box and its record is filed. Parts and wiring match the v3 drawing ([RR-2026-010](../reviews/RR-2026-010.md) HB-01…HB-06), or every difference is written below. *If the box differs from the drawing, stop: the steps name v3 parts.*
- [ ] **DG419LE ratings confirmed** from Vishay document 76432 (DFM-ACT-015). Absolute maximum V+ to V−: ______ V. Operating range: ______ V. *If they are not confirmed, skip D1 transients (step D1.6) and mark them "Blocked".*
- [ ] Lab supply current limit set to 0.5 A, output off.
- [ ] CAN interface at 500 kbit/s on both channels. Channel A on the camera connector (CAN2), channel B on the car connector (CAN0). 120 Ω termination on each side.
- [ ] Traffic running: channel A sends ID 0x343 every 10 ms, channel B sends ID 0x1AA every 10 ms. Both channels log frames and error counters.
- [ ] SBU1 source: 0–5 V low-impedance lab source (output impedance ≤ 10 Ω), current limit about 50 mA, **no series resistor**, output open. *R2+R3 (240 Ω) draw about 21 mA at 5 V; through 1 kΩ SBU1 would reach only 0.97 V.*
- [ ] SBU1 load check: set 5 V, connect, and read SBU1 at the breakout: ______ V (must be 4.9 V or more) and the source current: ______ mA (about 21 mA). Open the output again.
- [ ] Scope: differential probe across CAN_H/CAN_L at the car connector. Channel 2 on VIN, channel 3 on SBU1, channel 4 free for U1 pins.
- [ ] Comma power (J2) **not** connected.

Differences from the v3 drawing found in VS-HW-02:

| Part | Drawing | Found |
|---|---|---|
| | | |

## C. VS-HW-22: stock path with the box unpowered

Verifies HWSR-502a and HWSR-702; DFMEA DFM-020. Confirms or refutes RR-2026-010 F-02.

**Pass:** in steps 2, 3 and 4, frames pass both ways for 60 s with no error frames, and the differential levels meet ISO 11898-2 receiver thresholds (recessive below 0.5 V, dominant above 0.9 V).

- [ ] **1. Reference.** VIN = 13.5 V, SBU1 open. Exchange frames for 60 s.
- [ ] **2. VIN open.** Disconnect the IGN_12 pin. Exchange frames for 60 s. Measure VIN, and CAN_H and CAN_L to GND on both sides.
- [ ] **3. VIN shorted.** Short VIN to GND through 1 Ω (models a D4 short). Exchange frames for 60 s. Remove the short.
- [ ] **4. Device unpowered on the cable.** Plug the reference device into the OBD-C port, unpowered. IGN_12 open. Exchange frames for 60 s.
- [ ] **5. VIN ramp.** Ramp VIN 0 → 13.5 V → 0 at 0.1 V/s while exchanging frames. Note where pass-through starts and stops.

| Step | VIN (V) | Frames A→B / B→A in 60 s | Error frames | Recessive Vdiff (V) | Dominant Vdiff (V) | CAN_H / CAN_L to GND (V) | Pass / Fail |
|---|---|---|---|---|---|---|---|
| 1 Reference | | | | | | | |
| 2 VIN open | | | | | | | |
| 3 VIN shorted | | | | | | | |
| 4 Device unpowered | | | | | | | |

| Step 5 | Value |
|---|---|
| VIN at which pass-through starts (rising) | |
| VIN at which pass-through stops (falling) | |

- [ ] **Result VS-HW-22:** Pass / Fail. If it fails, F-02 is confirmed: keep DFM-020 as rated and add the values above to the DQ-209 record.

## D. VS-HW-24 (a)–(c): supply, logic threshold, signal integrity

Verifies HWSR-506d and HWSR-711a; DFMEA DFM-010.C4, DFM-011.C2. The box is still unmodified.

**Pass:** (a) the switch works at every steady level, and the peak at U1 V+ stays within the absolute maximum. (b) The switch changes over at least 1 V below 5 V at every point. (c) ISO 11898-2 thresholds are met with no error frames in 10 min.

**D1. Steady supply and transients (a).**

- [ ] 1. VIN 9 V: check intercept (SBU1 = 5 V) and pass-through (SBU1 open) by frame exchange. Note the supply current.
- [ ] 2. VIN 12 V: as step 1.
- [ ] 3. VIN 13.5 V: as step 1.
- [ ] 4. VIN 14.4 V: as step 1.
- [ ] 5. VIN 16 V: as step 1.
- [ ] 6. Transients, **only if part B confirmed the ratings**. Apply superimposed ripple, a starting profile and a suppressed load dump (ISO 16750-2 style), each capped at the confirmed absolute maximum. Record the peak at U1 V+ and the D4 clamp level.

| VIN (V) | Intercept works | Pass-through works | Supply current (mA) | Pass / Fail |
|---|---|---|---|---|
| 9 | | | | |
| 12 | | | | |
| 13.5 | | | | |
| 14.4 | | | | |
| 16 | | | | |

| Transient | Peak at U1 V+ (V) | D4 clamp level (V) | Switch works after | Pass / Fail / Blocked |
|---|---|---|---|---|
| Superimposed ripple | | | | |
| Starting profile | | | | |
| Suppressed load dump | | | | |

**D2. Logic threshold (b).** Sweep SBU1 0 → 5 V → 0 at 0.1 V/s. Note the SBU1 level at which the switch changes over, from the frame exchange or the scope on U1.

- [ ] 1. At 25 °C, VIN 9, 14 and 16 V.
- [ ] 2. At −20 °C (thermocouple on U1), VIN 9, 14 and 16 V.
- [ ] 3. At +85 °C (thermocouple on U1), VIN 9, 14 and 16 V.

| U1 temp (°C) | VIN (V) | Changeover rising (V) | Changeover falling (V) | ≤ 4.0 V? |
|---|---|---|---|---|
| 25 | 9 | | | |
| 25 | 14 | | | |
| 25 | 16 | | | |
| −20 | 9 | | | |
| −20 | 14 | | | |
| −20 | 16 | | | |
| +85 | 9 | | | |
| +85 | 14 | | | |
| +85 | 16 | | | |

**D3. Signal integrity (c).** VIN 13.5 V, pass-through, 500 kbit/s at about 80 % bus load from channel A to channel B, 10 min per row.

- [ ] 1. Direct cable between the two channels, as the reference.
- [ ] 2. Through the box, no ground offset.
- [ ] 3. Through the box, camera-side ground −1 V from the car side.
- [ ] 4. Through the box, camera-side ground +1 V from the car side.

| Row | Error frames in 10 min | Recessive Vdiff (V) | Dominant Vdiff (V) | Bit time / sample-point margin | Eye capture file | Pass / Fail |
|---|---|---|---|---|---|---|
| Direct cable | | | | | | |
| Box, 0 V | | | | | | |
| Box, −1 V | | | | | | |
| Box, +1 V | | | | | | |

- [ ] **Result VS-HW-24 (a)–(c):** Pass / Fail / Blocked. A failed (a) confirms DFM-010.C4 and a failed (b) confirms DFM-011.C2: report either to the lead (DQ-209, DQ-320).

## E. VS-HW-23: release default with the pull-down open

Verifies HWSR-506, HWSR-506e and HWSR-711a; DFMEA DFM-010.C3. Confirms or refutes RR-2026-010 F-03. VIN = 13.5 V throughout.

**Pass:** pass-through returns within 20 ms in every case in steps 2–4.

- [ ] **1. Reference, intact box.** Drive SBU1 to 5 V and check intercept (no camera frames reach channel B). Open SBU1. Measure the time from the SBU1 edge to the first camera frame on channel B, and to the change at U1 COM/NC on the scope. *This value also verifies HWSR-711a (≤ 20 ms).*
- [ ] **Modify:** lift one end of R2. Photograph the lifted end. Check with the DMM that SBU1 to GND is now open.
- [ ] **2. Source released.** Drive SBU1 to 5 V, confirm intercept, open SBU1. Note the switch state at 0 s, 1 s, 10 s, 1 min and 10 min.
- [ ] **3. Released by the device.** Connect the reference device. With intercept driven, release it three ways in turn: hold the MCU in reset (NRST), unplug the OBD-C cable, remove device power. Note the state at each time for each way.
- [ ] **4. Temperature.** Repeat step 2 at −20 °C and +85 °C at U1.
- [ ] **5. Orientation report.** Start the reference device with the pull-down open and note the harness orientation it reports. *SBU1 also carries orientation sense (HB-07). Do not count this as a diagnostic until it is analysed.*
- [ ] **Restore:** resolder R2. Check with the DMM that SBU1 to GND reads about 240 Ω. Repeat step 1 and check the changeover time matches.

| Step | Release | 0 s | 1 s | 10 s | 1 min | 10 min | Pass / Fail |
|---|---|---|---|---|---|---|---|
| 1 Intact (ms to pass-through) | Source open | | — | — | — | — | |
| 2 R2 open, 25 °C | Source open | | | | | | |
| 3a R2 open | MCU reset (NRST) | | | | | | |
| 3b R2 open | Cable unplugged | | | | | | |
| 3c R2 open | Device unpowered | | | | | | |
| 4a R2 open, −20 °C | Source open | | | | | | |
| 4b R2 open, +85 °C | Source open | | | | | | |

Write I (intercept) or P (pass-through) in each time column; in row 1, write the changeover time in ms.

| Step 5 | Entry |
|---|---|
| Orientation reported with the pull-down open | |
| SBU1 to GND after restore (Ω) | |
| Changeover time after restore (ms) | |

- [ ] **Result VS-HW-23:** Pass / Fail. If it fails, F-03 is confirmed and DFM-010.C3 and HWSR-506e stay open: report to the lead (DQ-320 depends on it).

## F. VS-HW-24 (e): camera-side termination in intercept

Checks the termination of the camera bus in intercept. The bus then runs from the camera through U1/U2 NO to the device, and only the box terminates it: R7, plus R8 through the harness's P13–P15 loopback, 60 Ω together. Lifting R8 has the same effect as an open loopback. VIN = 13.5 V.

**Set-up:** reference device on the OBD-C cable at the breakout, intercept driven by the device, bench SBU1 source disconnected. **Remove channel A's own 120 Ω**, so that only the box terminates the camera side. Channel A sends 0x343 every 10 ms. Scope ch 1 moves to CAN_H/CAN_L at the camera connector X1.

**Prediction** ([harness box SPICE pilot](../spice/predictions.md) §2, rows T-loop-open, T-r7-open and T-both-open; idealised model, no credit): with one resistor left, levels are OK and the recessive edge is about 0.06 µs. With both lifted, the edge is about 10 µs, which misses the 1.5 µs sample point at 500 kbit/s.

**Pass:** rows 1–3 show no error frames in 2 min, and the recessive edge stays under 1 µs. Row 4 has no pass or fail: record the effect against the prediction.

- [ ] **1. Nominal.** Check intercept: no camera frames reach channel B. Run 2 min.
- [ ] **Modify:** lift one end of R8. Photograph the lifted end.
- [ ] **2. R8 lifted** (same as the loopback open). Run 2 min.
- [ ] **Modify:** resolder R8, then lift one end of R7.
- [ ] **3. R7 lifted.** Run 2 min.
- [ ] **Modify:** lift R8 as well.
- [ ] **4. R7 and R8 lifted.** Run 2 min.
- [ ] **Restore:** resolder R7 and R8. Check with the DMM, box unpowered, that each reads about 120 Ω. Refit channel A's 120 Ω. Repeat row 1.

Measure the recessive edge from the end of a dominant bit until Vdiff falls below 0.5 V, at X1.

| Row | Termination left | Frames on device bus 2 / sent | Device error counters (TEC/REC) | Recessive edge at X1 (µs) | Dominant Vdiff (V) | Pass / Fail / Recorded |
|---|---|---|---|---|---|---|
| 1 Nominal | R7 + R8 (60 Ω) | | | | | |
| 2 R8 lifted | R7 (120 Ω) | | | | | |
| 3 R7 lifted | R8 (120 Ω) | | | | | |
| 4 Both lifted | none | | | | | |
| Restore | R7 + R8 | | | | | |

- [ ] **Result VS-HW-24 (e):** Pass / Fail. If row 2 or 3 fails, a single lost resistor stops camera frames in intercept, which is an SG-07 single-point fault not in the FMEDA: report to the lead.

## G. VS-HW-24 (d): clamp diode short

Verifies the DFM-021 effect analysis. **Bridge the diode externally with a short wire. Do not damage the part**, so the box can be restored.

- [ ] **1. D2 (car side, CAN0).** Bridge one D2 diode (CAN0_H to GND). Note which bus fails, whether the camera path still works, and the reference device's reaction (canError, RX timeouts) if it is connected. Remove the bridge.
- [ ] **2. D3 (camera side, CAN2).** Bridge one D3 diode (CAN2_H to GND). Record as step 1. Remove the bridge.
- [ ] **3. After.** Repeat C step 1 (the reference exchange) to show the box works as before.

| Step | Bus that fails | Camera path still works | Device reaction | Box works after bridge removed |
|---|---|---|---|---|
| 1 D2 bridged | | | | |
| 2 D3 bridged | | | | |

- [ ] **Result VS-HW-24 (d):** effect recorded against DFM-021. There is no pass or fail; this step records the effect.

## H. Close-out

- [ ] Box restored: R2, R7 and R8 resoldered, channel A's 120 Ω refitted, every bridge removed, reference exchange passes. Box labelled "bench-tested, modified and restored, see `results/<file>`".
- [ ] Raw data saved in `results/<date>-<box serial>/` and named after each step.
- [ ] [WP-H-06](../WP-H-06-hardware-integration-verification.md) §7 results table updated for VS-HW-02 and VS-HW-22…24: date, device, harness, result, measured value, evidence file.
- [ ] Any fail reported to the lead through the decision register, because DQ-209 and DQ-320 depend on these results.
- [ ] DFMEA DFM-ACT-014 updated with the outcome. If all cases pass, ask the hardware session to re-rate DFM-020, DFM-010.C3, DFM-010.C4 and DFM-011.C2 against the measured behaviour.

| Case | Result | Evidence folder | Problem report (if failed) |
|---|---|---|---|
| VS-HW-02 | | | |
| VS-HW-22 | | | |
| VS-HW-24 (a)–(c) | | | |
| VS-HW-23 | | | |
| VS-HW-24 (e) | | | |
| VS-HW-24 (d) | | | |

| Sign-off | Name | Date |
|---|---|---|
| Tester | | |
| Reviewer (independent of the tester) | | |
