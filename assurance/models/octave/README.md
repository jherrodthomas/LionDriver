# Envelope models in GNU Octave

| Field | Value |
|---|---|
| What | Models of LionDriver envelope logic in MATLAB syntax, run with GNU Octave (open-source MATLAB) |
| Status | Draft, AI-assisted (Claude), not reviewed |
| Tool | GNU Octave 8.4.0 with gnuplot, classified in [WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md) as TL-25 (TCL1, no verification credit) |
| Code read | opendbc and panda at the pinned commits (`opendbc_repo/opendbc/safety/safety.h`, `modes/toyota.h`; `panda/board/main.c`, `drivers/heartbeat_monitor.h`, `hw_watchdog.h`, `eps_fault_siren.h`, `stm32h7/stm32h7_config.h`) and `openpilot/selfdrive/pandad/pandad.cc` |

Tool choice for all modelling work: [modelling plan](../README.md) (MD-01).

## What these are, and what they are not

The scripts model envelope logic and the panda timing loops so their behaviour can be explored and plotted quickly:

| Script | Models | Code it is written from |
|---|---|---|
| `tx_rate_model.m` | Per-ID TX-rate supervision ([DN-01](../../05-software/design-notes/DN-01-tx-rate-supervision.md), SWSR-518) | `safety.h` `tx_rate_check` |
| `torque_envelope_model.m` | Toyota torque magnitude and rate limits | `modes/toyota.h` `TOYOTA_TORQUE_STEERING_LIMITS`, `lateral.h` |
| `run_models.m` §3 | A scripted run of the authority state machine | [`state-machines/sm-toy-auth.yaml`](../../05-software/state-machines/sm-toy-auth.yaml) |
| `timing_loop_model.m` (`run_models.m` §4) | Fault detection and warning times of the panda loops against the [WP-S-04](../../03-system/WP-S-04-timing-ftti-budget.md) §3.7 budgets: RX timeout (TSR-401), heartbeat loss (TSR-407), SoC command stall (TSR-408), IWDG (TSR-501), EPS-fault siren (TSR-516(b)), and the original baseline's 1 Hz path | `main.c` (100 Hz safety task, 8 Hz tick, speaker on odd ticks, 1 Hz path), `heartbeat_monitor.h`, `hw_watchdog.h`, `eps_fault_siren.h`, `safety.h` `rx_check_lagging` and `tx_arrival_ok`, `modes/toyota.h`, `pandad.cc` (10 Hz heartbeat) |

They are **not** the C code and **not** a test of it. A passing run is not verification evidence and verifies no requirement. Evidence about the C code needs tests of the C code itself (`opendbc_repo/opendbc/safety/tests/`, and the planned back-to-back test). Octave is used here as a calculation and plotting tool only.

`ld_constants.m` reads the constants from the opendbc source at the pinned commit, and it fails if the TX-rate budget formula in `safety.h` changes. A change to the code that the models do not follow therefore fails the run instead of leaving the models silently out of date.

## Run

```sh
octave-cli --no-gui assurance/models/octave/run_models.m <output dir>
```

Needs `opendbc_repo` and `panda` checked out (`git submodule update --init --depth 1 opendbc_repo panda`). The script prints its results, runs the model checks (exit status 1 on a failure) and writes `liondriver-octave-models.png` and `liondriver-timing-loops.png` to the output directory. CI runs it in `.github/workflows/assurance.yaml` (job "Octave envelope models") and uploads the plot as an artifact; plots are not committed.

## Model checks

| Check | Meaning |
|---|---|
| No rejection at the nominal rate, for every row of `toyota_tx_rate_checks` | The budget formula leaves room for the nominal rate (a false-positive check on the model) |
| Revocation ≤ 0.1 s after the first rejected frame (0x2E4 at 2×) | The model meets the SWSR-518 acceptance figure |
| Torque never above `max_torque`, per-frame change within +rate_up / −rate_down | The torque model respects its limits |
| Transitions used in the scenario exist in `sm-toy-auth.yaml` | The scenario stays tied to the state-machine record |
| Each timing-loop result agrees with the WP-S-04 §4 code-derived time within 10 ms (T-01, T-06, T-06a, T-07a, T-09a, T-28, T-34) | The model, the code and the document have not drifted apart |
| The reference-build FDTI overruns are exactly the documented ones (`0x262`, T-01; command stall, T-34) | A new overrun, or one that is fixed, fails the run so the document is updated |
| IWDG reaches 0.1 s exactly at a 10 % slow LSI; every reference-build FHTI within its FTTI | T-09a and the §3.7 budget rule |
| `timing_loop_results.csv` is current | The committed results, which the animation draws, match the model (`LD_TIMING_UPDATE=1` rewrites them) |

## First results (2026-10-13, Octave 8.4.0, opendbc `7993399`)

- `0x2E4` at 2× from 0.5 s: first rejection at 0.625 s, revocation 10 ms later, 135 ms after the flood starts.
- `0x2E4` at 2× from an empty window: revocation 190 ms after the flood starts, the same as the DN-01 estimate. The 135 ms case is shorter because the frames sent just before the flood count against the budget.
- Torque step to 2000 raw: 1500 raw after 99 frames; released to 0 in 60 frames.

These are model outputs, not measurements.

## Timing loops (2026-10-20, Octave 8.4.0, panda `8a69ccf`, opendbc `4d1a056`)

`timing_loop_model.m` sweeps each fault against every loop phase that can delay it: the 100 Hz safety task, the 8 Hz tick and its speaker parity (the speaker sounds only on every other tick), the 1 Hz path of the original baseline, and the LSI tolerance of the watchdog. t = 0 is the last valid event (frame, heartbeat, feed, first EPS fault frame), as WP-S-04 §4 states its times. The reaction after detection is the §3.7 FRTI budget: the EPS and PCM response is not modelled (M-02). Results are in [`timing_loop_results.csv`](timing_loop_results.csv).

![Animated FTTI timing loops, one looping timeline per fault class: normal operation, the fault, the detection time growing against the 100 Hz task and 8 Hz ticks, the reaction budget, the safe state and the siren, against the FTTI. RX loss 0x1D2 in the reference build is detected within 162 ms and reaches the safe state within the 500 ms FTTI; the same fault in the original baseline is detected after up to 2 s and exceeds the FTTI; heartbeat loss is detected within 300 ms with the siren within 550 ms; a SoC command stall is detected within 60 ms, 10 ms over its 50 ms budget but within the FTTI, with the siren within 310 ms; an MCU hang with a 10 % slow watchdog clock is detected at exactly the 100 ms budget; an EPS fault refuses actuation on the first frame and sounds the siren within 950 ms](../figures/fig-md-3-ftti-loops-anim.svg)

*Figure 1. Animated: worst case over all loop phases, drawn from `timing_loop_results.csv` by [`../figures/fig_timing_anim.py`](../figures/fig_timing_anim.py) (CI fails if stale).*

| Case | Worst FDTI | Budget | Model vs WP-S-04 §4 |
|---|---|---|---|
| RX loss `0x1D2` (33 Hz), reference | 161.5 ms | 200 ms | T-01 states ≤ 0.16 s; the model gives 1.5 ms more (5 × 30.3 ms + one task period) |
| RX loss `0x262` (25 Hz), reference | 210 ms | 200 ms | T-01: ≈ 0.21 s, over TSR-401's 0.2 s if the real rate is 25 Hz; the FHTI (310 ms) is within the 0.5 s FTTI |
| RX loss `0x260`, original baseline | 1.0–2.0 s | 200 ms | T-01: 1–2 s; FTTI exceeded |
| Heartbeat loss, reference | 300 ms; siren ≤ 550 ms | 300 ms; warning 1 s | T-06a ≤ 0.31 s and T-07a ≈ 0.56 s add one task period the code does not need |
| Heartbeat loss, original baseline | 4.0–5.0 s | 300 ms | T-06: 4–5 s |
| SoC command stall, reference | 60 ms; siren ≤ 310 ms | 50 ms; warning 1 s | T-34: ≤ 0.06 s, one task period over the budget |
| MCU hang, IWDG | 90 ms nominal, 100 ms at a 10 % slow LSI | 100 ms | T-09a; OI-2 of the watchdog impact record |
| EPS fault | siren ≤ 950 ms | warning 1 s | T-28 ≤ 0.96 s adds one task period the code does not need |

These are model outputs, not measurements (WP-S-04 §6, M-04…M-06).
