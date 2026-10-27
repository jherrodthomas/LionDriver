# Harness box switch path: the four box faults, to look at

> **Synthetic data (DSR-12). Design aid, no evidence credit (DQ-413).** The topology is the published harness box v3
> drawing as read in [RR-2026-010](../../04-hardware/reviews/RR-2026-010.md) (HB-01…HB-07). Three values are not
> published: the DG419LE input threshold with VL tied to VIN, the device's SBU1 driver and its SBU2 pull-up. Each has
> a band in [`params.yaml`](params.yaml) until DFM-ACT-015 (datasheet limits) or the VS-HW-24 bench measurement
> replaces it.

**[Open the circuit in Falstad](../results/harness-box.md)** (the link is on the results page). It runs in a phone
browser; tap a switch to flip it and read the voltages. The numbers of record are ngspice's, in
[`results/harness-box.md`](../results/harness-box.md).

**Question.** What does each harness box fault of the DFMEA do to the voltages the parts decide on?

| Fault | DFMEA | What the circuit shows |
|---|---|---|
| Pull-down R2/R3 open while SBU1 is undriven | DFM-010.C3 | The switch input floats on its leakage and can settle above the threshold: the box stays in intercept and the stock camera stays cut off |
| Input threshold above the 5 V drive at high VIN | DFM-011.C2 | At the band's worst corner (VIN 16 V, threshold VL/2, a weak drive) the drive no longer reaches the threshold: no intercept |
| Ignition-sense Q6 shorted | DFM-014.C2 | SBU2 reads low with the car off: the device reads ignition on |
| Clamp diode D2 leaking or shorted to GND | DFM-021.C1 | A leak lowers dominant CAN_H; a short pulls the differential below 0.9 V, so frames are corrupted |

**Method.** [`harness_box.py`](harness_box.py) holds one element list with drawing coordinates. It writes the Falstad
circuit text (Falstad connects elements by coordinates) and derives the ngspice netlist from the same coordinates, so
both circuits have the same topology and values. ngspice 41 (TL-58, the environment of
[`../supply/supply-linux-64.lock`](../supply/supply-linux-64.lock)) computes the DC operating point of each scenario.
[`check_falstad.mjs`](check_falstad.mjs) runs each scenario's circuit ([`falstad/`](falstad/)) in Falstad headless
(TL-60) and compares its node voltages with ngspice's within 5 mV.

**Checks in CI** (job "simulation harness box"): [`test_harness_box.py`](test_harness_box.py) (ngspice against closed
forms for the drive divider, a floating input, the ignition sense and the clamp short; the shared netlist; the Falstad
text), `harness_box.py --check` (results current) and `check_falstad.mjs` (Falstad agrees).

**Limits.** DC only: no switching transients, CAN edges or EMC. The DG419LE is two nodes (input against a fraction of
VIN), not a device model. Q6 is a switch: R4/R5 are not published. CAN_L is held at 1.5 V. Not compared with the
real box (VS-HW-22…24).
