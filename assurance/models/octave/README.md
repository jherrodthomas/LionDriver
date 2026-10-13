# Envelope models in GNU Octave

| Field | Value |
|---|---|
| What | Models of LionDriver envelope logic in MATLAB syntax, run with GNU Octave (open-source MATLAB) |
| Status | Draft, AI-assisted (Claude), not reviewed |
| Tool | GNU Octave 8.4.0 with gnuplot, classified in [WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md) as TL-25 (TCL1, no verification credit) |
| Code read | opendbc at the pinned commit (`opendbc_repo/opendbc/safety/safety.h`, `modes/toyota.h`) |

Tool choice for all modelling work: [modelling plan](../README.md) (MD-01).

## What these are, and what they are not

The scripts model three pieces of envelope logic so their behaviour can be explored and plotted quickly:

| Script | Models | Code it is written from |
|---|---|---|
| `tx_rate_model.m` | Per-ID TX-rate supervision ([DN-01](../../05-software/design-notes/DN-01-tx-rate-supervision.md), SWSR-518) | `safety.h` `tx_rate_check` |
| `torque_envelope_model.m` | Toyota torque magnitude and rate limits | `modes/toyota.h` `TOYOTA_TORQUE_STEERING_LIMITS`, `lateral.h` |
| `run_models.m` §3 | A scripted run of the authority state machine | [`state-machines/sm-toy-auth.yaml`](../../05-software/state-machines/sm-toy-auth.yaml) |

They are **not** the C code and **not** a test of it. A passing run is not verification evidence and verifies no requirement. Evidence about the C code needs tests of the C code itself (`opendbc_repo/opendbc/safety/tests/`, and the planned back-to-back test). Octave is used here as a calculation and plotting tool only.

`ld_constants.m` reads the constants from the opendbc source at the pinned commit, and it fails if the TX-rate budget formula in `safety.h` changes. A change to the code that the models do not follow therefore fails the run instead of leaving the models silently out of date.

## Run

```sh
octave-cli --no-gui assurance/models/octave/run_models.m <output dir>
```

Needs `opendbc_repo` checked out (`git submodule update --init --depth 1 opendbc_repo`). The script prints its results, runs the model checks (exit status 1 on a failure) and writes `liondriver-octave-models.png` to the output directory. CI runs it in `.github/workflows/assurance.yaml` (job "Octave envelope models") and uploads the plot as an artifact; plots are not committed.

## Model checks

| Check | Meaning |
|---|---|
| No rejection at the nominal rate, for every row of `toyota_tx_rate_checks` | The budget formula leaves room for the nominal rate (a false-positive check on the model) |
| Revocation ≤ 0.1 s after the first rejected frame (0x2E4 at 2×) | The model meets the SWSR-518 acceptance figure |
| Torque never above `max_torque`, per-frame change within +rate_up / −rate_down | The torque model respects its limits |
| Transitions used in the scenario exist in `sm-toy-auth.yaml` | The scenario stays tied to the state-machine record |

## First results (2026-10-13, Octave 8.4.0, opendbc `7993399`)

- `0x2E4` at 2× from 0.5 s: first rejection at 0.625 s, revocation 10 ms later, 135 ms after the flood starts.
- `0x2E4` at 2× from an empty window: revocation 190 ms after the flood starts, the same as the DN-01 estimate. The 135 ms case is shorter because the frames sent just before the flood count against the budget.
- Torque step to 2000 raw: 1500 raw after 99 frames; released to 0 in 60 frames.

These are model outputs, not measurements.
