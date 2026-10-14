# FMEA diagram data

One file per FMEA holding the diagrams that frame its worksheet. `tools/safety/fmea_review_md.py` draws them into the
review pages under [`../exports/review/`](../exports/review/README.md) and checks every ID against the analysis.

| File | Diagrams |
|---|---|
| [`system-fmea.yaml`](system-fmea.yaml) | Item block and boundary diagram, P-diagram of the L2 function |
| [`sw-fmea.yaml`](sw-fmea.yaml) | Software architecture block diagram (cereal topics, SPI, hooks), P-diagram of engagement and actuation authority |
| [`dfmea.yaml`](dfmea.yaml) | Hardware block and boundary diagram (panda MCU, clock, supply, transceivers, relay, harness), P-diagram of the safety path |
| [`pfmea.yaml`](pfmea.yaml) | Process flow in swimlanes (release, installation, update), P-diagram of producing the reference configuration |

Each file has a `block_diagram` (or, for the PFMEA, a `process_flow`) and a `p_diagram`:

- **Block diagram.** `blocks` with an `inside` flag (inside the analysis boundary or not), an optional structure
  `element`, and a `column`/`row` layout hint; `interfaces` between blocks, typed `data`, `energy`, `physical` or
  `material`, each with the source it was taken from. The page lists them as the interface matrix.
- **P-diagram.** The `focus` and the `functions` it covers; `inputs`; `ideal_outputs`; `error_states`, each linked to
  the failure modes it shows up as; `noise_factors` in the five AIAG-VDA categories; `control_factors` with sources.
- **Process flow.** `lanes`, and `steps` with a `kind` (operation, inspection, decision, handover), the process
  element and the `next` steps.

Facts the source documents leave open are marked as such in the labels ("shared?", "UK-05") rather than guessed.
