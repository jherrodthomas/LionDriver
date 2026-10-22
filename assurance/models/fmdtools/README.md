# fmdtools fault-propagation models

| Field | Value |
|---|---|
| Plan | [TE-02](../../07-supporting/tool-evaluations/TE-02-fmdtools-fault-propagation.md) (pilot on SG-02; extended to SG-06, SG-01 and SG-03 by the lead, DQ-417) |
| Tool | [NASA fmdtools](https://github.com/nasa/fmdtools) 2.5.6, Apache-2.0, pinned in [`requirements.txt`](requirements.txt); [WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md) TL-49 |
| Status | SG-02: steps P0 (setup), P1 (model), P2 (single faults), P3 (joint faults), P4 (timing) and the P5 Fault Lab page done; the TL-49 confirmation remains. SG-06: P1 to P4 and its Fault Lab page done (DQ-417). SG-01: P1 to P3 and its Fault Lab page done (no P4: TE-01 is not a late cue). SG-03 next. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Evidence | **None.** Synthetic (DSR-12): behaviour and timing come from WP-A-04 §4, not measurement. Results point reviewers at possible gaps in the fault trees; a tree changes only after a person reviews the finding |

## What is here

| Path | Content |
|---|---|
| [`sg02/events.yaml`](sg02/events.yaml) | One failure mode per event of the SG-02 tree (25 modes, 2 events held latent), and the timing the model uses, each with its source |
| [`sg02/model.py`](sg02/model.py) | The SG-02 chain as fmdtools functions and flows: supply, SoC, envelope, EPS, the host's alert logic, HMI, siren, driver. `run(events)` injects modes together and reads TE-02 from the history |
| [`sg02/test_sg02.py`](sg02/test_sg02.py) | Mapping against the WP-A-04 tree and `fta-fmea-map.yaml`; nominal run; reference cases from the §4.1 cut-set table; road phases |
| [`sg02/sweep.py`](sg02/sweep.py) | Step P2: every mode alone in each road phase, compared with the tree; writes [`sg02/p2-single-faults.md`](sg02/p2-single-faults.md). Step P3 (`joint`): the minimal sets of up to 4 modes; writes [`sg02/p3-minimal-sets.json`](sg02/p3-minimal-sets.json) and [`sg02/p3-joint-faults.md`](sg02/p3-joint-faults.md). Step P4 (`timing`): the time to the first cue for every set of the P3 diff; writes [`sg02/p4-timing.md`](sg02/p4-timing.md) and its figure. `--check` in CI (P3: orders 1 and 2 on pull requests, the full sweep weekly in `fmdtools-sweep.yaml`) |
| [`sg02/fault_lab.py`](sg02/fault_lab.py) | Step P5: writes [`sg02/fault-lab.html`](sg02/fault-lab.html), the Fault Lab page: a still replay of plant case F-07 (EPS fault) with its event timeline, the P3 and P4 numbers, the pair matrix (model sets against tree sets) and the findings for review. Built from the P3 JSON, a fresh P4 run and [plant-results](../../sim/results/plant-results.md); `--check` in CI (DQ-409) |
| [`sg02/test_fault_lab.py`](sg02/test_fault_lab.py) | The plant parser, the drawings and the page build (sweep stubbed) |
| [`sg06/`](sg06/) | The SG-06 model (loss of deceleration without a take-over request, WP-A-04 §7), built like `sg02/`: [`events.yaml`](sg06/events.yaml), [`model.py`](sg06/model.py), [`test_sg06.py`](sg06/test_sg06.py), [`sweep.py`](sg06/sweep.py) (pages [P2](sg06/p2-single-faults.md), [P3](sg06/p3-joint-faults.md), [P4](sg06/p4-timing.md)) and the [Fault Lab page](sg06/fault-lab.html) ([`fault_lab.py`](sg06/fault_lab.py)). `--check` in CI as for SG-02 |
| [`sg01/`](sg01/) | The SG-01 model (uncontrollable torque or torque while not engaged, WP-A-04 §2): [`events.yaml`](sg01/events.yaml), [`model.py`](sg01/model.py), [`test_sg01.py`](sg01/test_sg01.py), [`sweep.py`](sg01/sweep.py) (pages [P2](sg01/p2-single-faults.md), [P3](sg01/p3-joint-faults.md)) and the [Fault Lab page](sg01/fault-lab.html) ([`fault_lab.py`](sg01/fault_lab.py)). `--check` in CI as for SG-02 |
| [`treediff.py`](treediff.py), [`faultlab_kit.py`](faultlab_kit.py) | Shared by the goals: the tree side of the sweeps (cut sets, effective sets, the diff), and the Fault Lab style, findings list and pair matrix |

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
    python3 assurance/models/fmdtools/sg02/sweep.py timing             # step P4, about 15 s
    python3 assurance/models/fmdtools/sg02/fault_lab.py                # step P5 page, about 20 s (--check: fail if stale)

## First results (single modes, step P1)

| Mode alone | Lost | First cue | TE-02 |
|---|---|---|---|
| BE-2.04 non-finite command | 0.00 s | none | **yes** (MCS-02.4) |
| BE-2.21 selfdrived stop | 0.10 s | siren 0.88 s (engaged-mismatch revocation, panda `f4803c5`; UI after 5 s) | no: needs a siren failure too (MCS-02.9) |
| BE-2.05 SoC crash | 0.00 s | siren 0.26 s | no: needs a siren failure too (the MCS-02.5 comment says the same) |
| BE-2.01 EPS drop | 0.00 s | alert 0.10 s | no |
| BE-2.07 supply loss | 0.00 s | driver 0.00 s | no: needs UE-2.18 (MCS-02.7) |

Step P1 already shows one difference from the table, pinned in the tests: {BE-2.01, BE-2.08} (MCS-02.1) and {BE-2.20, BE-7.20, BE-2.12} (MCS-02.11) do not give TE-02 in the model. The siren sounds about 0.25 s after an EPS fault (revocation siren), inside the budget, so each also needs a siren failure. Step P3 reports such differences to the FTA owner for every set.

## Single faults in three road phases (step P2)

A run takes place on a straight, at curve entry or mid-curve (`events.yaml` phases). The model has no geometry: a phase says only whether curvature is asked and whether the end of LKA torque can be felt, so curve entry and mid-curve agree; timing along a curve is the plant's. [`p2-single-faults.md`](sg02/p2-single-faults.md) has the table. Three differences from the tree:

- **BE-2.05 SoC crash**: TE-02 alone in the tree, not in the model, where the heartbeat siren sounds at 0.26 s. Same cause as the P1 finding: the tree's latent tag on BE-2.14.
- **BE-2.21 selfdrived stop**: the same since panda `f4803c5`: the engaged-mismatch revocation sounds the siren 0.88 s after the stop (0.78 s after the loss).
- **BE-2.07 supply loss on a straight**: TE-02 alone in the model. MCS-02.7 needs the driver to miss the end of LKA torque (UE-2.18); on a straight that torque is near zero, so the model gives no cue. The plant confirms it matters: with a road-crown or crosswind push of 0.1 m/s² or more, a 3.0 m lane line is crossed before the driver corrects ([straight-drift](../../sim/results/straight-drift.md)). The FTA owner takes it as an AOU-01R validation gap.

## Joint faults (step P3)

One run takes about 0.19 s. Step P3 therefore skips sets that contain no cause and supersets of sets already found: 6,297 runs instead of all 15,275 sets of 1 to 4 modes. Mid-curve, against the tree's 31 effective sets of up to 4 events (its latent events taken as present):

- **No set in the model that the tree does not predict.** A test drops the MCS-02.4 cut sets from the tree and checks that the diff then reports {BE-2.04}.
- 21 sets agree. In 10 tree sets, the model needs one more event, a siren failure (BE-2.14, BE-2.15 or BE-2.22): {BE-2.05}, {BE-2.21}, the four {BE-2.01, warning or HMI failure} sets of MCS-02.1 and MCS-02.6, and the four {BE-2.20, BE-7.20, warning or HMI failure} sets of MCS-02.11. All 10 are the same finding: since panda `8a69ccf`, the siren covers EPS faults and heartbeat loss, so the tree's latent tag on BE-2.14 holds only for the other causes.

[`p3-joint-faults.md`](sg02/p3-joint-faults.md) lists all 51 minimal sets.

MCS-02.9 (selfdrived stop) was checked against the plant ([engaged-mismatch](../../sim/results/engaged-mismatch.md)). Up to panda `8a69ccf`, no revocation sounded the siren, so the tree's single point held. Since panda `f4803c5` (TSR-307(a), TSR-516(c)), the panda revokes at 0.39–0.48 s and the siren sounds at 0.63–0.88 s after the stop. The model takes 0.88 s, 0.78 s after the loss, so {BE-2.21} now needs a siren failure too.

## Time to the first cue (step P4)

Each of the 61 sets of the P3 diff is run for 6 s, to time cues that come after the budget ([`p4-timing.md`](sg02/p4-timing.md)):

- **10 within the budget:** by the siren, at 0.26 s, or 0.78 s after the loss for {BE-2.21} (margin 0.22 s), which is the P3 finding.
- **9 late:** the three {BE-2.21 + siren failure} sets (MCS-02.9) get the System Unresponsive alert 4.9 s after the loss. The six {BE-2.08 + EPS fault + siren failure} sets (MCS-02.1, MCS-02.11) get the escalated take-over request at 1.5 s (TSR-607 (b)), 0.5 s over.
- **42 with no cue within 6 s:** the warning failures of the tree, as expected.

Two inputs exceed the budget on their own: the 1.5 s escalation after an override, and the 5 s alert after a selfdrived stop. The second is now the first cue only when the siren fails too.

## Fault Lab page (step P5)

[`fault-lab.html`](sg02/fault-lab.html) puts the results on one page for review (lead's choice, DQ-409). Every number on it comes from a record: the replay and timeline from plant case F-07 (torque below 5 % at 0.31 s, siren at 0.25 s, lane line at 1.25 s, driver correction at 1.75 s), the sweep figures from the P3 JSON and a P4 run. The page is still (no animation), works at phone width, and is marked synthetic (DSR-12), with no evidence credit. CI fails if it is stale.

## SG-06: loss of deceleration without a take-over request

The [SG-06 model](sg06/model.py) reuses the SG-02 warning chain and adds the PCM and one more cue. When `selfdrived` disengages with an immediate disable, the host sends the ACC cancel (TSR-303). PCM cruise then drops and the cluster cruise indicator changes (AOU-12). If the cancel has no effect, the panda's cancel-lag guard sounds the siren (TSR-516(c)). During a soft disable no cancel is sent until it ends, after 3 s (SWF-048.C1). The PCM cancel lag is not measured (WP-W-02 OI-18), so the model takes the latest time the guard allows (0.6 s after the disengagement).

Approaching a lead, against the tree's 23 effective sets of up to 4 events ([P3](sg06/p3-joint-faults.md)):

- **No set in the model that the tree does not predict.**
- 18 sets agree.
- **The siren covers 2 tree sets**, as in SG-02: {BE-2.05} (heartbeat loss, 0.26 s) and {BE-2.21} (engaged mismatch, 0.88 s). The tree's latent tag on BE-2.14 is out of date for them.
- **The cancel covers 3 tree sets**: a lost plan input with an HMI failure ({BE-6.01} with BE-2.12, BE-2.13 or BE-2.25). The cluster changes 0.7 s after the fault, and a failed cancel gets the guard's siren at 0.86 s. The model needs both BE-6.06 and a siren failure for TE-06. The tree's latent tag on BE-6.06 holds only during a soft disable.
- **Late cues** ([P4](sg06/p4-timing.md)): an envelope block with an HMI failure gets only the guard's siren, at 1.26 s (0.26 s over the budget), because the envelope blocks the cancel. A soft disable (BE-2.10) gets the cluster change only at 3.6 s.

No plant case covers a loss of deceleration yet, so the [Fault Lab page](sg06/fault-lab.html) replays the model's own run.

    python3 assurance/models/fmdtools/sg06/test_sg06.py
    python3 assurance/models/fmdtools/sg06/sweep.py                    # P2 (--check: fail if stale)
    python3 assurance/models/fmdtools/sg06/sweep.py joint              # P3, about 4 min on 4 cores
    python3 assurance/models/fmdtools/sg06/sweep.py timing             # P4
    python3 assurance/models/fmdtools/sg06/fault_lab.py                # Fault Lab page

## SG-01: uncontrollable torque, or torque while not engaged

SG-01 is not a warning goal, so the [SG-01 model](sg01/model.py) times torque at the wheel, not cues. A run gives TE-01 in one of four ways:
- excessive torque reaches the wheel and the EPS does not limit it;
- the item's torque outlasts the SG-05 release time (0.2 s) when the driver does not want it;
- a stale torque is held past the 0.5 s FTTI;
- the stock LKA and the item are on the car bus together past the FTTI.

The branches need different situations, so each set runs in four phases: engaged, driver brakes, driver cancels, not engaged. The envelope and the SoC read the same frames through the one RX path (DFI-10).

Against the tree's 36 effective sets of up to 3 events ([P3](sg01/p3-joint-faults.md)):

- 31 sets agree.
- **2 sets the drawn tree does not predict:** {BE-1.13} and {BE-1.17}. A stuck cruise frame reaches the SoC too, so on a cancel it stays engaged without a SoC fault. The WP-A-04 table already calls these single points ("effective 1 through DFI-10"); the drawn tree keeps BE-1.15 as a second event.
- **Tree sets the model does not reach:**
  - {BE-1.15, BE-1.16}: a brake press also drops PCM cruise, so the envelope revokes on 0x1D2 (TSR-301).
  - {BE-1.12, BE-1.15}: one corrupted frame opens the TSR-301 window, and the next genuine frame closes it.
  - {BE-1.18}: a debug build has no envelope, but the SoC still gates its own command, so the model needs a SoC fault too.
- **Stale torque stays a single point:** BE-1.19, BE-1.20 and BE-1.21. The frames keep arriving, so the heartbeat and arrival checks do not see a stale value (TSR-409 open). TSR-602 drops a stale model input only at 0.52 s, just over the FTTI.

The [Fault Lab page](sg01/fault-lab.html) replays plant case F-03 (command frozen at curve entry): nothing reacts, and the driver steers at 2.96 s.

    python3 assurance/models/fmdtools/sg01/test_sg01.py
    python3 assurance/models/fmdtools/sg01/sweep.py                    # P2 (--check: fail if stale)
    python3 assurance/models/fmdtools/sg01/sweep.py joint              # P3, about 10 min on 4 cores
    python3 assurance/models/fmdtools/sg01/fault_lab.py                # Fault Lab page
