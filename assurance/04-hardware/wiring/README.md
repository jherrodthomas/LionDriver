# Harness and bench wiring drawings

Text-first wiring drawings of the E-05 harness and the hardware test benches. Each drawing is a WireViz source
(`*.yaml`) in this folder; [`make_wiring.py`](make_wiring.py) draws it with WireViz and Graphviz and writes the SVG,
the Graphviz source and the bill of materials next to it. CI fails when an output is stale (§4).

LionDriver does not design PCBs ([WP-H-02](../WP-H-02-hardware-design.md) §1). These drawings record the wiring,
the interfaces and the benches of COTS hardware, the comma device E-04 and the harness E-05, as published by comma.ai.
**Nothing here was measured.** The reference unit is assumed to be the Toyota A harness with harness box v3 (the
lead's choice in [DQ-211](../../01-management/decisions/register.yaml), option C); VS-HW-02 in
[WP-H-06](../WP-H-06-hardware-integration-verification.md) checks one unit against these drawings.

## 1. Drawings

| Drawing | Source | Shows | Embedded in |
|---|---|---|---|
| `TA` | [`e05-toyota-a-harness.yaml`](e05-toyota-a-harness.yaml) | Toyota A harness: camera connector X1, car connector X2, box plug X3; pins, wire colours, gauge | WP-H-02 §3.6 |
| `HB` | [`e05-harness-box.yaml`](e05-harness-box.yaml) | Harness box v3: header J1, intercept switches U1/U2 (HE-08), release pull-down R2/R3, ignition sense Q6 (HE-10), supply diode D1, OBD-C receptacle J3, comma power J2 | WP-H-02 §3.6 |
| `OC` | [`e05-obdc-device.yaml`](e05-obdc-device.yaml) | OBD-C cable from J3 to the comma device port (HE-09), device side inferred from firmware | WP-H-02 §3.6 |
| `BB` | [`bench-box-vs-hw-22-24.yaml`](bench-box-vs-hw-22-24.yaml) | Bench for VS-HW-22…24: box tested alone, CAN interface, lab supply, SBU1 source, scope, fault-injection points FI-1…FI-4 | WP-H-06 §3.1 |
| `HIL` | [`bench-hil.yaml`](bench-hil.yaml) | HIL bench of WP-H-06 Figure 2-1 at instrument level (deferred, DQ-049) | WP-H-06 §2.1 |

![Wiring of the Toyota A harness from comma's v3 drawing: camera connector X1 (TE 1318774-1) and car connector X2 (TE 1565894-1) with the same pin positions, CAN on pins 5 and 11, radar CAN1 on 6 and 12, IGN on 7, GND on 10; a six-wire branch from each to the 18-pin box plug X3 (Molex 501646-1800), four pass-through wires PT1 to PT4 from X1 to X2, and the loopback 13 to 15 on X3; all wires UL1007 26 AWG](e05-toyota-a-harness.svg)

*Drawing TA.* Toyota A harness, read from comma's `Toyota_A_Harness.pdf` and `open_pinout.pdf`. Colour codes are
IEC 60757 (OG orange, GN green, PK pink, BU blue, BN brown, BK black, VT violet, GY grey, WH white, YE yellow).

![Harness box v3 nets: the camera CAN_H from header pin 16 enters switch U1 at COM, the car CAN_H from pin 4 sits on U1 NC; the car CAN_L from pin 6 enters U2 at COM, the camera CAN_L from pin 18 sits on U2 NC; both switch inputs IN and the pull-down R2/R3 are on SBU1 at receptacle pin A8; ignition IGN_12 from pin 2 drives Q6, which pulls SBU2 at B8, and feeds box VIN through D1 to A4; comma power J2 also feeds VIN](e05-harness-box.svg)

*Drawing HB.* Harness box v3, drawn in the undriven state: SBU1 is held low by R2/R3, both switches sit on NC, and
the camera bus joins the car bus (stock path). SBU1 at 5 V moves both switches to NO, which puts each side on a
terminated stub and leaves the device as the only link between them (intercept). Lines are board nets, not wires.

![OBD-C cable between the box receptacle J3 and the comma device port: twelve used conductors with the USB-C full-featured crossover, so the car CAN0 on A2/A3 arrives at device B11/B10 (bus 0, FDCAN1), the camera CAN2 on B2/B3 at A11/A10 (bus 2, FDCAN3), the radar CAN1 at B2/B3 (bus 1), the box SBU1 at device SBU2 (relay drive) and the box SBU2 at device SBU1 (ignition sense); VBUS and GND straight through](e05-obdc-device.svg)

*Drawing OC.* The OBD-C link in the orientation the panda firmware calls NORMAL. The device side comes from the
firmware, not from a schematic (UK-01): `panda/board/drivers/harness.h` (relay on the device's SBU2 and ignition on
its SBU1 when NORMAL) and `panda/board/drivers/can_common.h:130` (a FLIPPED plug swaps logical bus 0 and bus 2). A
wrong orientation reading therefore swaps the car and camera buses in firmware; this is the HWSR-701 case that
VS-HW-13 tests.

![Bench for VS-HW-22 to 24: CAN interface channel A on the camera connector X1 pins 5 and 11 and channel B on the car connector X2 pins 5 and 11, each with a 120 ohm termination; lab supply on X2 pin 7 (IGN) and pin 10; a 0 to 5 V low-impedance source on SBU1 at a USB-C breakout on the box receptacle; scope on the car CAN, VIN and SBU1; fault-injection points FI-1 IGN open, FI-2 VIN shorted through 1 ohm, FI-3 R2 lifted, FI-4 D2 or D3 bridged](bench-box-vs-hw-22-24.svg)

*Drawing BB.* The box-alone bench of WP-H-06 §3.1, wired as the
[bench checklist](../bench/VS-HW-22-24-checklist.md) sets it up. Bench parts WP-H-06 does not name (mating plugs,
USB-C breakout) are marked "to choose". Not built.

![HIL bench at instrument level: bench PC over USB to a panda jungle or 3-channel CAN interface, a programmable supply, the reference device and a scope; the jungle drives the car bus and radar bus at the car connector X2 and the camera bus at X1; the supply feeds IGN at X2; the device connects to the box receptacle by the OBD-C cable; scope probes on SBU1, the U1/U2 switch pins, the car CAN and NRST or BOOT0](bench-hil.svg)

*Drawing HIL.* WP-H-06 Figure 2-1 as wiring. The HIL bench is deferred by the lead
([DQ-049](../../01-management/decisions/register.yaml), option B). Probes sit on SBU1 and the switch pins: the box has
no relay coil (RR-2026-010), unlike the probes Figure 2-1 still names (OI-W-7).

## 2. Wire IDs for the FMEDA

[`wire-ends.tsv`](wire-ends.tsv) lists every wire of a cable and every line drawn between two pins, with both ends,
the signal, colour and gauge. The ID is `<drawing>.<cable>.<wire>` for a wire (for example `TA.W1.1`, the orange
camera CAN2_H wire from X1:5 to X3:16) and `<drawing>.<A>.<pin>-<B>.<pin>` for a line (for example
`HB.R2/R3.1-J3.A8`, the SBU1 pull-down). WP-H-03 FMEDA rows can cite these IDs. The FMEDA itself is not changed here; it
belongs to its owner.

IDs follow the source: renumbering a cable or moving a line changes them, so cite them only from a drawing that has
been reviewed and keep the drawing stable after that.

## 3. Box parts not drawn as nodes

The box drawing keeps to the switched and sensed nets. Part names (SBU1, R2/R3, D1, D4, D2/D3, U1/U2) are the test-point names of WP-H-06 §3.1 and the [bench checklist](../bench/VS-HW-22-24-checklist.md); keep them. These parts sit on the same nets and come from the same v3
drawing ([RR-2026-010](../reviews/RR-2026-010.md) HB-03…HB-05):

| Part | Value | Connection | Note |
|---|---|---|---|
| D2 | BAS40SDW Schottky pair | CAN0_H and CAN0_L to VIN and GND | Clamps the car bus to the box rail (F-02, F-07) |
| D3 | BAS40SDW Schottky pair | CAN2_H and CAN2_L to VIN and GND | Clamps the camera bus to the box rail (F-02, F-07) |
| D4 | SMF16A TVS, 16 V stand-off | VIN to GND | Only transient limit on VIN (F-05) |
| R6 | 120 Ω | CAN0_L′ (U2 NO) to CAN0_H″ (J1 P5) | Car-side termination in intercept, when the plug loops P3 to P5 |
| R7 | 120 Ω | CAN2_L to CAN2_H′ (U1 NO) | Camera-side termination in intercept |
| R8 | 120 Ω | CAN2_L″ (J1 P15) to CAN2_H′ | Second camera-side termination when the plug loops P13 to P15; Toyota A does, so the camera side sees 60 Ω in intercept |
| R1, R4, R5 | 1 kΩ each | Q6 drain to SBU2; IGN_12 divider to the Q6 gate | Ignition sense (HB-06) |
| U1, U2 supply | V+ = VL = VIN, V− = GND = GND | — | The stock path needs box power (F-01, F-02). DG419LE ratings against VIN are **unconfirmed** (DFM-ACT-015, [RR-2026-010](../reviews/RR-2026-010.md) §6.1) |

## 4. Regenerating and checking

```sh
sudo apt-get install graphviz                    # Ubuntu 24.04: 2.42.2 package, dot reports 2.43.0
python3 -m pip install -r requirements.txt       # WireViz 0.4.1 and its dependencies, pinned
python3 make_wiring.py                           # rebuild every output (refuses with another dot version)
python3 make_wiring.py --check                   # what CI runs
python3 test_make_wiring.py                      # pinout consistency and output tests
```

Edit only the `.yaml` sources. `--check` compares the `.gv`, `.bom.tsv` and `wire-ends.tsv` byte for byte, and the
SVGs byte for byte when `dot` is the pinned version; with another version it only parses them and says so. Rules for
sources: set `metadata.drawing` (the ID prefix); keep `<` and `>` out of labels (they break Graphviz HTML labels);
quote any label that contains a comma.

## 5. Sources and licences

| Item | Version | Licence | Use |
|---|---|---|---|
| comma.ai [`commaai/hardware`](https://github.com/commaai/hardware) `harness/`: `v3/Toyota_A_Harness.pdf` (7 Mar 2025), `v3/Harness_Box.pdf` ("car harness v3", 20 Aug 2024), `v3/open_pinout.pdf`, `OBD-C.sch.pdf`, `README.md` | commit `530b7da` | Published with "you can copy this!"; no licence file in the folder | Pinout, parts and nets, transcribed by hand into the sources, 2026-10-20 |
| panda firmware `board/drivers/harness.h`, `board/drivers/can_common.h` | submodule pin of this repository | MIT | Device-side orientation, relay and bus mapping |
| [WireViz](https://github.com/wireviz/WireViz) | 0.4.1 | GPL-3.0-only | Tool only: run to draw; nothing linked into the item |
| Graphviz `dot` | Ubuntu 24.04 package 2.42.2-9ubuntu0.1 | EPL-1.0 | Layout |
| Python packages `graphviz` 0.21, `pillow` 12.3.0, `click` 8.5.0, `PyYAML` 6.0.3 | pinned in [`requirements.txt`](requirements.txt) | MIT, MIT-CMU, BSD-3-Clause, MIT | WireViz dependencies |

## 6. Open items

| ID | Item | Closed by |
|---|---|---|
| OI-W-1 | Every pin, colour and part number here is transcribed from comma's published drawings, not measured on the reference unit | VS-HW-02 inspection plus a continuity check of the spare harness against `wire-ends.tsv` (already budgeted under DQ-209 option A) |
| OI-W-2 | Harness letter and box revision of the reference unit not recorded; Toyota A with box v3 is assumed | Open by decision (DQ-211, option C); the bench sheet records the unit tested |
| OI-W-3 | Crimp terminal of the box plug differs between comma's drawings: 501648-1000 (Toyota A drawing) and 501647-1000 (open_pinout) | Read the part on the unit (VS-HW-02) |
| OI-W-4 | Signal names of the four pass-through wires PT1…PT4 are not on the drawing; the wire lengths (dimensions 250 mm and 120 mm) are not attributed to a branch, so no lengths are given | Toyota connector pinout (service data) or measurement; lengths from the unit |
| OI-W-5 | Whether the reference configuration uses comma power (J2) is not recorded; it changes what feeds box VIN when the ignition line opens (RR-2026-010 F-02) | WP-C-01 reference configuration |
| OI-W-6 | OBD-C cable: conductor colours, gauge and which length is used not published; device-side routing to the transceivers inferred from firmware (UK-01) | comma data (WP-H-02 OI-1) or measurement |
| OI-W-7 | ~~WP-H-06 Figure 2-1 still names a contact-state probe and a coil-current probe for a relay box; the box has analog switches and no coil~~ | **Closed 2026-10-20:** WP-H-06 v0.10 redraws Figure 2-1 with probes on SBU1 and the U1/U2 switch pins |
