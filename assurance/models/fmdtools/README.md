# fmdtools fault-propagation models

| Field | Value |
|---|---|
| Plan | [TE-02](../../07-supporting/tool-evaluations/TE-02-fmdtools-fault-propagation.md) (pilot on SG-02) |
| Tool | [NASA fmdtools](https://github.com/nasa/fmdtools) 2.5.6, Apache-2.0, pinned in [`requirements.txt`](requirements.txt); [WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md) TL-49 |
| Status | Steps P0 (setup), P1 (SG-02 model), P2 (single faults) and P3 (joint faults) done; P4 and P5 open. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Evidence | **None.** Synthetic (DSR-12): behaviour and timing come from WP-A-04 §4, not measurement. Results point reviewers at possible gaps in the fault trees; a tree changes only after a person reviews the finding |

## What is here

| Path | Content |
|---|---|
| [`sg02/events.yaml`](sg02/events.yaml) | One failure mode per event of the SG-02 tree (25 modes, 2 events held latent), and the timing the model uses, each with its source |
| [`sg02/model.py`](sg02/model.py) | The SG-02 chain as fmdtools functions and flows: supply, SoC, envelope, EPS, the host's alert logic, HMI, siren, driver. `run(events)` injects modes together and reads TE-02 from the history |
| [`sg02/test_sg02.py`](sg02/test_sg02.py) | Mapping against the WP-A-04 tree and `fta-fmea-map.yaml`; nominal run; reference cases from the §4.1 cut-set table; road phases |
| [`sg02/sweep.py`](sg02/sweep.py) | Step P2: every mode alone in each road phase, compared with the tree; writes [`sg02/p2-single-faults.md`](sg02/p2-single-faults.md). Step P3 (`joint`): the minimal sets of up to 4 modes; writes [`sg02/p3-minimal-sets.json`](sg02/p3-minimal-sets.json) and [`sg02/p3-joint-faults.md`](sg02/p3-joint-faults.md). `--check` in CI (P3: orders 1 and 2 on pull requests, the full sweep weekly in `fmdtools-sweep.yaml`) |

## How it works

Time runs in 20 ms ticks, because fmdtools needs an integer step; delays round up to whole ticks, so a cue is never earlier than its source says. A cause is injected 0.5 s into the run. The run ends once the 1 s budget has passed for the latest possible loss.

TE-02 holds when lateral control is lost and no perceivable cue comes within 1 s. The cues are a delivered SoC alert, the panda siren, or, on a supply loss, the driver feeling the end of LKA torque.

Each mode realises one tree event. Two latent events of the tree are held as baseline design rather than as modes:
- BE-2.11: a non-finite command is never warned.
- BE-2.16: the cluster never changes on a lateral fault.

BE-2.14 (siren not triggered) stays a mode. Since panda `8a69ccf` the siren sounds on every revocation that is not a driver action (TSR-516(b)): about 0.25 s after a heartbeat loss or an EPS fault in the plant. So the model shows where the tree's latent tag no longer holds.

    python3 -m pip install -r assurance/models/fmdtools/requirements.txt
    python3 assurance/models/fmdtools/sg02/model.py                    # nominal run and every single mode
    python3 assurance/models/fmdtools/sg02/model.py BE-2.01 BE-2.08    # one joint-fault run
    python3 assurance/models/fmdtools/sg02/test_sg02.py
    python3 assurance/models/fmdtools/sg02/sweep.py                    # step P2 page (--check: fail if stale)
    python3 assurance/models/fmdtools/sg02/sweep.py joint              # step P3, about 4.5 min on 4 cores

## First results (single modes, step P1)

| Mode alone | Lost | First cue | TE-02 |
|---|---|---|---|
| BE-2.04 non-finite command | 0.00 s | none | **yes** (MCS-02.4) |
| BE-2.21 selfdrived stop | 0.10 s | none within 1 s (UI after 5 s) | **yes** (MCS-02.9) |
| BE-2.05 SoC crash | 0.00 s | siren 0.26 s | no: needs a siren failure too (the MCS-02.5 comment says the same) |
| BE-2.01 EPS drop | 0.00 s | alert 0.10 s | no |
| BE-2.07 supply loss | 0.00 s | driver 0.00 s | no: needs UE-2.18 (MCS-02.7) |

Step P1 already shows one difference from the table, pinned in the tests: {BE-2.01, BE-2.08} (MCS-02.1) and {BE-2.20, BE-7.20, BE-2.12} (MCS-02.11) do not give TE-02 in the model. The siren sounds about 0.25 s after an EPS fault (revocation siren), inside the budget, so each also needs a siren failure. Step P3 reports such differences to the FTA owner for every set.

## Single faults in three road phases (step P2)

A run takes place on a straight, at curve entry or mid-curve (`events.yaml` phases). The model has no geometry: a phase says only whether curvature is asked and whether the end of LKA torque can be felt, so curve entry and mid-curve agree; timing along a curve is the plant's. [`p2-single-faults.md`](sg02/p2-single-faults.md) has the table. Two differences from the tree:

- **BE-2.05 SoC crash**: TE-02 alone in the tree, not in the model, where the heartbeat siren sounds at 0.26 s. Same cause as the P1 finding: the tree's latent tag on BE-2.14.
- **BE-2.07 supply loss on a straight**: TE-02 alone in the model. MCS-02.7 needs the driver to miss the end of LKA torque (UE-2.18); on a straight that torque is near zero, so the model gives no cue. The plant confirms it matters: with a road-crown or crosswind push of 0.1 m/s² or more, a 3.0 m lane line is crossed before the driver corrects ([straight-drift](../../sim/results/straight-drift.md)). The FTA owner takes it as an AOU-01R validation gap.

## Joint faults (step P3)

One run takes about 0.19 s. Step P3 therefore skips sets that contain no cause and supersets of sets already found: 5,260 runs instead of all 15,275 sets of 1 to 4 modes. Mid-curve, against the tree's 31 effective sets of up to 4 events (its latent events taken as present):

- **No set in the model that the tree does not predict.** A test drops the MCS-02.4 cut sets from the tree and checks that the diff then reports {BE-2.04}.
- 22 sets agree. In 9 tree sets, the model needs one more event, a siren failure (BE-2.14, BE-2.15 or BE-2.22): {BE-2.05}, the four {BE-2.01, warning or HMI failure} sets of MCS-02.1 and MCS-02.6, and the four {BE-2.20, BE-7.20, warning or HMI failure} sets of MCS-02.11. All 9 are the same finding: since panda `8a69ccf`, the siren covers EPS faults and heartbeat loss, so the tree's latent tag on BE-2.14 holds only for the other causes.

[`p3-joint-faults.md`](sg02/p3-joint-faults.md) lists all 49 minimal sets.
