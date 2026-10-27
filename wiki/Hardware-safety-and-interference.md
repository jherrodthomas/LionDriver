# Hardware safety and interference

Two questions an assessor asks of every safety-related element, explained for someone who has not met them before:
how often can the hardware fail in a way that breaks a safety goal, and can the parts that are not safety-rated
disturb the parts that are? This page explains and links. The analyses are
[WP-H-03](../assurance/04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md) (FMEDA),
[WP-H-04](../assurance/04-hardware/WP-H-04-hardware-metrics.md) (SPFM and LFM),
[WP-H-05](../assurance/04-hardware/WP-H-05-random-hardware-failures-pmhf.md) (PMHF) and
[WP-A-02](../assurance/08-analyses/WP-A-02-coexistence-freedom-from-interference.md) (freedom from interference);
nothing here is an analysis result.

Both figures are drawn at each wiki sync by [`tools/wiki/hw_animations.py`](../tools/wiki/hw_animations.py). The
metrics are computed from the FMEDA records
([`fmeda-sg001.yaml`](../assurance/08-analyses/fmea/analyses/fmeda-sg001.yaml)) with the same formulas as
`tools/safety/fmea_lint.py`, and the interference verdicts are read from WP-A-02 §8, so the figures follow the
records.

> [!IMPORTANT]
> The failure rates are **generic estimates for each part type**, not values for the actual parts: the device's bill
> of materials is not available yet. The numbers show where the architecture stands; they are not evidence.

## 1. Hardware safety in numbers

![Animated: FIT, the SG-01 failure rate sorted into safe or detected, latent and single-point plus residual, the SPFM and LFM gauges against the ASIL targets, the largest contributors and the PMHF target](hw-numbers.svg)

| Term | Meaning |
|---|---|
| **FIT** | Failures in time: one failure in 10⁹ device-hours. |
| **FMEDA** | Failure modes, effects and diagnostic analysis: every hardware part's failure rate, split by how it fails, and whether a safety mechanism catches it. |
| **Single-point fault** | One fault that violates the safety goal and that no safety mechanism catches. |
| **Residual fault** | The part of a fault that a safety mechanism is meant to catch but misses. |
| **Latent fault** | A fault that does no harm alone and is not detected, but leaves a safety mechanism unable to act when a second fault comes. |
| **SPFM** | Single-point fault metric: the share of failures that are not single-point or residual. |
| **LFM** | Latent fault metric: the share of the remaining failures that are not latent. |
| **PMHF** | Probabilistic metric for random hardware failures: the rate per hour at which hardware failures violate the goal. |

Each ASIL sets a target for each metric ([WP-H-04 §4](../assurance/04-hardware/WP-H-04-hardware-metrics.md)). The
fixes are safety mechanisms with higher diagnostic coverage, better failure rates for the real parts, or a different
architecture. The open items and the lead's decisions on them are in WP-H-04.

## 2. Freedom from interference

![Animated: the panda chip runs the ASIL C safety envelope next to QM firmware, sharing memory and CPU time, with the openpilot computer outside; interference by memory, time and messages; the verdict of each channel from WP-A-02](hw-ffi.svg)

When parts of different ASILs share a chip, the higher-rated part must be shown to be free from interference by the
lower-rated ones: through **memory** (spatial), **time** (temporal) and **messages** (communication). Otherwise a
fault in QM code could break the ASIL C envelope that the safety concept relies on.

Two related ideas belong with it, and are analysed in the
[dependent failure analysis](../assurance/08-analyses/WP-A-03-dependent-failure-analysis.md):

- **Cascading failure:** one failure causing another, for example a QM process flooding the link and starving the
  envelope of commands.
- **Common-cause failure:** one root cause breaking two parts at once, for example one power supply feeding both the
  openpilot computer and the safety chip. The fault-tree AND gates and the shared resources behind them are checked
  in [`dfa-gates.md`](../assurance/08-analyses/dfa/dfa-gates.md).

## Try it: the harness box faults

The harness box decides whether the stock camera reaches the car or the item intercepts it. Its switch path is a
circuit you can open in the browser and break: the
[harness box results page](../assurance/sim/results/harness-box.md) has a Falstad link where each DFMEA fault of the
box (pull-down open, switch threshold too high, ignition-sense transistor shorted, clamp diode leaking) is a switch to
flip. The numbers of record are ngspice's, on the same page, and CI checks the two agree. Synthetic, no evidence
credit; three part values are still estimates.

## Where next

- [From hazard to test](From-hazard-to-test.md): where these hardware requirements come from.
- [Building a fault tree](Building-a-fault-tree.md): the traps of common causes and latent faults, in fault-tree form.
