# fmdtools fault-propagation models

| Field | Value |
|---|---|
| Plan | [TE-02](../../07-supporting/tool-evaluations/TE-02-fmdtools-fault-propagation.md) (pilot on SG-02) |
| Tool | [NASA fmdtools](https://github.com/nasa/fmdtools) 2.5.6, Apache-2.0, pinned in [`requirements.txt`](requirements.txt); [WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md) TL-49 |
| Status | Steps P0 (setup) and P1 (SG-02 model) done; P2 to P5 open. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Evidence | **None.** Synthetic (DSR-12): behaviour and timing come from WP-A-04 §4, not measurement. Results point reviewers at possible gaps in the fault trees; a tree changes only after a person reviews the finding |

## What is here

| Path | Content |
|---|---|
| [`sg02/events.yaml`](sg02/events.yaml) | One failure mode per event of the SG-02 tree (25 modes, 2 events held latent), and the timing the model uses, each with its source |
| [`sg02/model.py`](sg02/model.py) | The SG-02 chain as fmdtools functions and flows: supply, SoC, envelope, EPS, the host's alert logic, HMI, siren, driver. `run(events)` injects modes together and reads TE-02 from the history |
| [`sg02/test_sg02.py`](sg02/test_sg02.py) | Mapping against the WP-A-04 tree and `fta-fmea-map.yaml`; nominal run; reference cases from the §4.1 cut-set table |

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

## First results (single modes, step P1)

| Mode alone | Lost | First cue | TE-02 |
|---|---|---|---|
| BE-2.04 non-finite command | 0.00 s | none | **yes** (MCS-02.4) |
| BE-2.21 selfdrived stop | 0.10 s | none within 1 s (UI after 5 s) | **yes** (MCS-02.9) |
| BE-2.05 SoC crash | 0.00 s | siren 0.26 s | no: needs a siren failure too (the MCS-02.5 comment says the same) |
| BE-2.01 EPS drop | 0.00 s | alert 0.10 s | no |
| BE-2.07 supply loss | 0.00 s | driver 0.00 s | no: needs UE-2.18 (MCS-02.7) |

Step P1 already shows one difference from the table, pinned in the tests: {BE-2.01, BE-2.08} (MCS-02.1) and {BE-2.20, BE-7.20, BE-2.12} (MCS-02.11) do not give TE-02 in the model. The siren sounds about 0.25 s after an EPS fault (revocation siren), inside the budget, so each also needs a siren failure. Step P3 reports such differences to the FTA owner for every set.

One run takes about 0.19 s. Step P3 therefore skips sets that contain no cause and supersets of sets already found, rather than running all 15,250 combinations of 2 to 4 modes.
