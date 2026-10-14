# LionDriver architecture

<p align="center">
  <img src="../assets/liondriver/architecture.svg" width="100%" alt="LionDriver platform architecture: core driving platform, safety envelope, vehicle integration and supported vehicle ecosystem as stacked layers, with a cross-cutting safety and assurance column. A legend separates implemented, drafted and proposed elements.">
</p>

LionDriver keeps openpilot's architecture and adds an assurance layer around it. The driving software is not replaced. What changes is the engineering record: every safety-relevant element is analysed, its requirements are written down, and the evidence that it meets them is tracked.

## Layers

| Layer | What it does | Where it lives | State |
|---|---|---|---|
| **Core driving platform** | Perception and prediction in the driving model, planning, lateral and longitudinal control, driver monitoring, user interface | [`openpilot/selfdrive/modeld`](../../openpilot/selfdrive/modeld), [`controls`](../../openpilot/selfdrive/controls), [`monitoring`](../../openpilot/selfdrive/monitoring), [`selfdrived`](../../openpilot/selfdrive/selfdrived), [`ui`](../../openpilot/selfdrive/ui) | Inherited from openpilot |
| **Safety envelope** | Decides which commands may reach the car: actuator limits, engagement and release on driver input, message checks, relay supervision | panda firmware ([`commaai/panda`](https://github.com/commaai/panda/tree/92eb565169fd553f4dfaf508c1a3f8dbc14fbfbf/board)) running the brand safety modes from [`opendbc/safety`](https://github.com/commaai/opendbc/tree/229dc7062d8986b4f954c7c97875b4ffd0044d12/opendbc/safety) | Inherited; hardening proposed in the [technical safety requirements](../../assurance/03-system/WP-S-02-technical-safety-requirements.md) |
| **Vehicle integration** | Vehicle interfaces, ECU fingerprinting, harness and hardware configurations, calibration, diagnostics | [`opendbc/car`](https://github.com/commaai/opendbc/tree/229dc7062d8986b4f954c7c97875b4ffd0044d12/opendbc/car) | Inherited; vehicle operating assumptions drafted in the [item definition](../../assurance/02-concept/WP-C-01-item-definition.md) |
| **Vehicle ecosystem** | Cars, SUVs and crossovers, minivans, pickups and commercial vans listed in the pinned compatibility list | [`docs/CARS.md`](../CARS.md) | Inherited; see [vehicle compatibility](compatibility.md) |
| **Safety and assurance** | Functional safety, SOTIF, cybersecurity, AI safety, safety case, traceability, verification and validation, change impact analysis | [`assurance/`](../../assurance/README.md) | Draft work products, not yet reviewed |

The opendbc and panda links point at the exact commits the `opendbc_repo` and `panda` submodules pin.

## The doer and the checker

openpilot already separates a large, learned, QM "doer" (the driving stack on the application processor) from a small, deterministic "checker" (the safety mode on the panda microcontroller). The checker bounds what the doer can make the car do, whatever the doer computes. LionDriver's safety argument is built on that split; the strategy and its open questions are in the [assurance strategy](../../assurance/01-management/WP-M-01-assurance-strategy.md) and the [functional safety concept](../../assurance/02-concept/WP-C-04-functional-safety-concept.md).

The [gap assessment](../../assurance/00-assessment/gap-assessment.md) lists where the inherited checker falls short of what the safety goals need (for example, no independent hardware watchdog and report-only fault handling). Those gaps are recorded as defeaters in the [Living Safety Case](../../assurance/case/README.md) until evidence closes them.

## What "multi-vehicle" means here

The platform keeps every upstream car port. The assurance work is carried out on one reference configuration first, and each further configuration joins the claimed scope through a documented [impact analysis](../../assurance/01-management/WP-M-12-impact-analysis.md) against the assumptions the analysis made about the vehicle. The [compatibility page](compatibility.md) explains the three classifications.
