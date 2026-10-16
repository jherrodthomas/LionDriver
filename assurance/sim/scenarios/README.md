# Known scenarios as data

| Field | Value |
|---|---|
| Scope | Layer 2 of the [simulation track](../README.md) (roadmap phase S2): the [WP-V-03](../../06-validation/WP-V-03-sotif-known-scenarios.md) known scenarios that simulation can represent, as ASAM OpenSCENARIO 1.3 (`xosc/`) and OpenDRIVE 1.5 (`xodr/`) files named by scenario ID |
| Version | 0.1 (2026-10-16) |
| Status | Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed. Synthetic scenarios (DSR-12); **no evidence credit** |

The files fix the road and the other road users of each scenario. The ego vehicle is the item under test: a file gives
it only a start position and speed (and, in KS-14 and KS-25, the driver's own action), and the harness drives it. The
fault-injection plant model (layer 1) reads the scenario roads directly ([`../plant/roads.py`](../plant/roads.py)
`from_xodr`; case F-07-KS01) and takes the KS-08 time gap for its longitudinal cases from `KS-08.xosc`; MetaDrive
(layer 3) and the unknown-scenario search (layer 4) are to use the same files.

Highway only (ODD-H; DQ-023 answered B): three lanes, OpenDRIVE lane IDs −1 (left) to −3 (right), the ego in lane −2
unless stated. WP-V-03 parameters are scenario parameters: their defaults are in the file, their sweep values below.

```sh
python3 assurance/sim/scenarios/generate.py           # write the files (scenariogeneration, MPL-2.0)
python3 assurance/sim/scenarios/generate.py --check   # CI: committed files equal a fresh generation
python3 assurance/sim/scenarios/replay.py --check     # CI: replay headless in esmini v3.9.0, check, compare the table
python3 assurance/sim/scenarios/test_scenarios.py
```

## 1. Scenarios written as files

| ID | Scenario | Files | Parameters: default (sweep) | What the replay checks |
|---|---|---|---|---|
| KS-01 | Curve at or beyond the lateral capability | [`KS-01.xosc`](xosc/KS-01.xosc), [`KS-01.xodr`](xodr/KS-01.xodr) | `EgoSpeed` 27.386 (24.495, 27.386, 30, 32.404) m/s | ego stays in lane -2; steady-state lateral acceleration v²/R equals the parameter's within 5 % |
| KS-05 | Stationary vehicle in lane at highway approach | [`KS-05.xosc`](xosc/KS-05.xosc), [`KS-05.xodr`](xodr/KS-05.xodr) | `EgoSpeed` 22.222 (11.111, 16.667, 22.222, 33.333) m/s; `TargetS` 500 (500) m; `TargetOffset` 0 (-0.5, 0, 0.5) m | stationary vehicle stays at speed 0 in lane -2 at its offset |
| KS-06 | Narrow lane with an adjacent truck | [`KS-06.xosc`](xosc/KS-06.xosc), [`KS-06.xodr`](xodr/KS-06.xodr) | `EgoSpeed` 27.778 (25, 27.778, 33.333) m/s | truck stays in lane -3 alongside the ego; lane width 3.3 m |
| KS-07 | Close cut-in | [`KS-07.xosc`](xosc/KS-07.xosc), [`KS-07.xodr`](xodr/KS-07.xodr) | `EgoSpeed` 27.778 (27.778, 33.333) m/s; `CutInDistance` 15 (10, 15, 20) m; `ClosingSpeed` 1.389 (0, 1.389, 2.778) m/s; `LaneChangeTime` 2 (2) s | cut-in car is in lane -2 after the lane change; gap at the start of the lane change equals CutInDistance within 0.5 m |
| KS-08 | Lead decelerating hard | [`KS-08.xosc`](xosc/KS-08.xosc), [`KS-08.xodr`](xodr/KS-08.xodr) | `EgoSpeed` 22.222 (13.889, 22.222) m/s; `TimeGap` 1.5 (1.5) s; `LeadDecel` 5 (3, 5, 7) m/s² | lead decelerates at LeadDecel within 5 % and stops in lane -2 |
| KS-09 | Cut-out revealing a stopped vehicle | [`KS-09.xosc`](xosc/KS-09.xosc), [`KS-09.xodr`](xodr/KS-09.xodr) | `EgoSpeed` 13.889 (13.889) m/s; `CutOutDistance` 45 (30, 45, 60) m | lead is in lane -1 after the cut-out; stopped vehicle stays at speed 0 in lane -2 |
| KS-14 | Driver-initiated lane change | [`KS-14.xosc`](xosc/KS-14.xosc), [`KS-14.xodr`](xodr/KS-14.xodr) | `EgoSpeed` 27.778 (27.778) m/s; `TargetGap` 2.5 (2, 2.5, 3, 20) s | ego is in lane -3 after the lane change (scripted here: in a closed loop the driver's nudge starts it) |
| KS-23 | Stop-and-go queue and resume | [`KS-23.xosc`](xosc/KS-23.xosc), [`KS-23.xodr`](xodr/KS-23.xodr) | `StandTime` 5 (3, 5) s | lead leaves at 1.5 m/s² after StandTime; ego starts at standstill |
| KS-25 | Speed above the ODD bound | [`KS-25.xosc`](xosc/KS-25.xosc), [`KS-25.xodr`](xodr/KS-25.xodr) | `StartSpeed` 31.944 (31.944) m/s; `EndSpeed` 36.111 (36.111) m/s | ego speed crosses 120 km/h |

KS-01 is the one scenario whose sweep goes past the ODD curve bound on purpose (3.0 and 3.5 m/s² at R = 300 m):
WP-V-03 asks for behaviour at and beyond the lateral capability. KS-25 crosses the 120 km/h ODD-H speed bound on
purpose.

## 2. Scenarios not written as files

| ID | Why not |
|---|---|
| KS-02 | bank and crosswind: OpenSCENARIO 1.x has no wind, and esmini does not use superelevation; plant model (layer 1) later |
| KS-03 | lane-marking visibility is a perception condition: recorded data and the closed course (M3, M8) |
| KS-04 | lane split and merge: representable with a junction or a lane-width polynomial; deferred (SIM-OI-5) |
| KS-10 | overpass and shadow false braking is a perception condition (M3, M9) |
| KS-11 | radar clutter and metal plates are perception conditions (M3, M8, M9) |
| KS-12 | sun, headlights, tunnels are perception conditions (M3, M9) |
| KS-13 | work zones are outside the ODD; procedure check (M3, M8, M9) |
| KS-15 | rain and wet-road reflections are perception conditions (M3, M9) |
| KS-16 | camera obstruction and calibration are perception conditions (M3, M8) |
| KS-17 | driver-monitoring conditions (VS-ML-06, M8) |
| KS-18 | driver-monitoring conditions (VS-ML-06, M8) |
| KS-19 | driver override forces: plant model fidelity level L2 (Modelica steering), then M8 |
| KS-20 | stock PCS: plant model cases P-01…P-03 for the forwarding path; the braking itself only on the car (M8) |
| KS-21 | internal degradation: plant model fault cases (layer 1) and M1/M8 |
| KS-22 | pedestrians and cyclists at the lane edge are outside the highway-only ODD (DQ-023 answered B) |
| KS-24 | inspection |
| KS-26 | PCM cruise after disengagement: HIL and closed course (M1, M8) |

## 3. Replay

[`replay.py`](replay.py) runs each file headless in esmini v3.9.0 (MPL-2.0; fetched and checked against its SHA-256
by [`fetch_esmini.py`](fetch_esmini.py)) with a fixed 50 ms step, at the defaults and at each sweep value of one
parameter at a time, and checks from esmini's recording that the scenario happened as specified: lanes, gaps,
decelerations, speeds. esmini 3.9 has no command-line parameter override, so the replay writes a temporary copy with
the parameter defaults changed. esmini's default controller drives the ego, so the replay says nothing about
LionDriver: it only shows that the files are unambiguous and executable. Result: [`../results/scenario-replay.md`](../results/scenario-replay.md).

The files are not validated against the ASAM XML schemas: scenariogeneration's wheel does not ship them and their
redistribution terms are not checked here. esmini's parser loads every file without an error, which the replay
requires.

