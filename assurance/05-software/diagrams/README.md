# Design diagrams (generated)

| Field | Value |
|---|---|
| Status | Draft — AI-assisted (Claude), not reviewed. The diagrams are views; the normative content is the state-machine records and the WP-W-05 §5 tables |
| Generator | [`make_diagrams.py`](make_diagrams.py) (standard library, plus [`svgkit.py`](svgkit.py)) |
| CI | `make_diagrams.py --check` in the assurance workflow fails if a diagram is out of date |
| Tool | WP-P-07 TL-36 (TCL1: no claim rests on a figure) |

MATLAB-style figures drawn from the project data, with no MATLAB, Simulink or Stateflow licence needed ([TE-01](../../07-supporting/tool-evaluations/TE-01-modelling-tools.md)).

| File | What it shows | Source |
|---|---|---|
| [`stateflow-sm-toy-auth.svg`](stateflow-sm-toy-auth.svg) | Stateflow-style chart of the Toyota authority (`controls_allowed`) | [`sm-toy-auth.yaml`](../state-machines/sm-toy-auth.yaml) |
| [`stateflow-sm-safety-mode.svg`](stateflow-sm-safety-mode.svg) | Stateflow-style chart of the panda safety mode | [`sm-safety-mode.yaml`](../state-machines/sm-safety-mode.yaml) |
| [`stateflow-sm-selfdrived.svg`](stateflow-sm-selfdrived.svg) | Stateflow-style chart of the `selfdrived` engagement state (host, QM) | [`sm-selfdrived.yaml`](../state-machines/sm-selfdrived.yaml) |
| [`simulink-envelope.svg`](simulink-envelope.svg) | Simulink-style block diagram of the envelope signal flow (reference build), blocks citing WP-W-05 units | `BLOCKS` and `LINES` in `make_diagrams.py` (a design description) |

**Chart notation.** The charts follow Stateflow conventions:

- Each state is a rounded box, and the initial state has a default-transition dot.
- Transitions are labelled with their IDs, grouped per state pair.
- The table under the chart gives each label in Stateflow form: `event [guard] / {action}`.
- A **solid** arrow means the transition exists in the code. A **dashed** arrow means a target transition, which the record marks `not implemented`.
- The status column is the WP-W-02 Baseline status of the cited SWSRs. A transition can exist in the code and still not meet its SWSR, for example T6 and the `selfdrived` engagement transitions.

**Scope plots.** Time traces of recorded back-to-back runs are produced by [`../reference-models/scope_plots.py`](../reference-models/scope_plots.py) into [`../reference-models/results/scope/`](../reference-models/results/scope/), each with a CSV of the same samples. They need the opendbc environment and are checked in the `b2b` workflow.

**Keeping them current.** After changing a state-machine record or WP-W-02, run `check_state_machines.py --write` and then `make_diagrams.py`. Positions of states are set per record in `LAYOUT`. A new state without a position stops the generator, so a layout is never guessed.

**Dark mode.** The SVGs carry their own light and dark colours (`prefers-color-scheme`). The two trace colours of the scope plots are slots 1 and 2 of the reference categorical palette, which pass the palette checks in both modes.
