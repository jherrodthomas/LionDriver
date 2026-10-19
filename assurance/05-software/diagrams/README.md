# Design diagrams (generated)

| Field | Value |
|---|---|
| Status | Draft — AI-assisted (Claude), not reviewed. The diagrams are views; the normative content is the state-machine records and the WP-W-05 §5 tables |
| Generator | [`make_diagrams.py`](make_diagrams.py) (standard library, plus [`svgkit.py`](svgkit.py)) |
| CI | `make_diagrams.py --check` in the assurance workflow fails if a diagram is out of date |
| Tool | WP-P-07 TL-41 (TCL1: no claim rests on a figure) |

MATLAB-style figures drawn from the project data, with no MATLAB, Simulink or Stateflow licence needed ([TE-01](../../07-supporting/tool-evaluations/TE-01-modelling-tools.md)).

| File | What it shows | Source |
|---|---|---|
| [`stateflow-sm-toy-auth.svg`](stateflow-sm-toy-auth.svg) | Stateflow-style chart of the Toyota authority (`controls_allowed`), with the engagement window and the revocations by cause | [`sm-toy-auth.yaml`](../state-machines/sm-toy-auth.yaml) |
| [`stateflow-sm-safety-mode-reference.svg`](stateflow-sm-safety-mode-reference.svg), [`stateflow-sm-safety-mode-upstream.svg`](stateflow-sm-safety-mode-upstream.svg) | Stateflow-style charts of the panda safety mode, one per build; the non-car modes as a superstate | [`sm-safety-mode.yaml`](../state-machines/sm-safety-mode.yaml) |
| [`stateflow-sm-selfdrived.svg`](stateflow-sm-selfdrived.svg) | Stateflow-style chart of the `selfdrived` engagement state (host, QM), with the `active` superstate | [`sm-selfdrived.yaml`](../state-machines/sm-selfdrived.yaml) |
| [`stateflow-system-engagement.svg`](stateflow-system-engagement.svg) | How SM-SELFDRIVED, the heartbeat, SM-SAFETY-MODE and SM-TOY-AUTH couple at engagement, with a timeline (explanatory view) | `SYSTEM` in `make_diagrams.py`; state names checked against the records |
| [`../state-machines/README.md`](../state-machines/README.md) | Landing page of the state-machines folder: counts per record and the charts | the records |
| [`simulink-envelope.svg`](simulink-envelope.svg) | Simulink-style block diagram of the envelope signal flow (reference build), blocks citing WP-W-05 units | `BLOCKS` and `LINES` in `make_diagrams.py` (a design description) |
| [`simulink-panda-firmware.svg`](simulink-panda-firmware.svg) | Simulink-style block diagram of the panda firmware grouped by interrupt context, with the shared `controls_allowed` flag as a data store (WP-W-03 §3.2) | `PANDA` in `make_diagrams.py`, from WP-W-03 §3.1, §3.2, §5.1 |
| [`simulink-host.svg`](simulink-host.svg) | Simulink-style block diagram of the host engagement and control path, modeld → controlsd / selfdrived → card → pandad → panda, with service rates (WP-W-03 §4.2) | `HOST` in `make_diagrams.py`, from WP-W-03 §4.1, §4.2 |

![Coupling of the engagement state machines: selfdrived enabling sends the heartbeat engaged flag, the panda's engagement window waits for it before granting controls_allowed in the Toyota car mode, and the panda reports controlsAllowed back to selfdrived; a timeline below shows the order of events at engagement](stateflow-system-engagement.svg)

*The state machines that meet at engagement (`stateflow-system-engagement.svg`), an explanatory view.*

![Panda firmware block diagram by execution context: the SPI DMA interrupt takes control requests and SoC CAN frames through the TX hook, the FDCAN interrupts forward frames and run the RX hook, the 100 Hz safety task and the 8 Hz tick supervise, the main loop only marks progress, and controls_allowed is a shared data store with its writers](simulink-panda-firmware.svg)

*The panda firmware as a Simulink-style block diagram (`simulink-panda-firmware.svg`, WP-W-03 §3.2).*

**Chart notation.** The charts follow Stateflow conventions:

- Each state is a rounded box, and the initial state has a default-transition dot.
- Transitions are labelled with their IDs, grouped per state pair.
- The table under the chart gives each label in Stateflow form: `event [guard] / {action}`.
- A **solid grey** arrow means the transition exists in the code. A **dashed orange** arrow means a target transition, which the record marks `not implemented`; its table row is shaded in the same orange.
- State fills give the state's role (for example authority granted, engaged, diagnostic), set per record in `LAYOUT`; the legend under each chart names them.
- The status column is the WP-W-02 Baseline status of the cited SWSRs. A transition can exist in the code and still not meet its SWSR, for example T6 and the `selfdrived` engagement transitions.
- A **superstate** (`super` in `LAYOUT`) is a frame around states: a transition from every member is drawn once from its border (X1/X2 of `selfdrived`), and an arrow ending on the border goes to one of the members, chosen by the request (the safety mode's `m`).
- **Badges** on a label give the requirement status of a transition that is in the code: red "no SWSR" (checker finding S7), yellow "SWSR not met" (S5). The line style says whether the code exists; the badge says whether the requirement is met.
- **Per build** (`builds` in `LAYOUT`): one chart per build, without the other build's transitions. A state that cannot be reached from the initial state in that build is drawn dashed as "unreachable", and the transitions out of it are named under the chart.
- Transitions **from "any"** state (`any: note`) are listed under the chart instead of being drawn from every state; the table has them in full.
- The SM-TOY-AUTH revocations are a **panel by cause** instead of one label. Each row has its line style, a badge and a green chip with the directed back-to-back scenarios that name the transition, read from the scenario names in `reference-models/b2b_toy_auth.py`.

**Block colours.** Simulink-style diagrams colour blocks by kind: input port aqua, output port orange, function blue, Stateflow chart violet, Data Store Memory yellow, subsystem green; reference-build-only blocks stay white with a dashed border. Each diagram has a legend, and the kind is also shown by shape and glyph, so colour is never the only cue.

**Scope plots.** Time traces of recorded back-to-back runs are produced by [`../reference-models/scope_plots.py`](../reference-models/scope_plots.py) into [`../reference-models/results/scope/`](../reference-models/results/scope/), each with a CSV of the same samples. They need the opendbc environment and are checked in the `b2b` workflow.

**Keeping them current.** After changing a state-machine record or WP-W-02, run `check_state_machines.py --write` and then `make_diagrams.py`. Positions of states are set per record in `LAYOUT`. A new state without a position stops the generator, so a layout is never guessed.

**Dark mode.** The SVGs carry their own light and dark colours (`prefers-color-scheme`). All colours are slots of the reference categorical palette; fills are tints of a slot (`SLOTS` in `svgkit.py`). The three trace colours of the scope plots (C blue, model orange, inputs aqua) pass the palette checks all-pairs in both modes; light-mode aqua is below 3:1 contrast, which the strip labels and the CSV beside each plot cover.
