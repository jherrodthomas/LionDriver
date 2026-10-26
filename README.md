<p align="center">
  <img src="docs/assets/liondriver/hero.svg" width="100%" alt="LionDriver. Open Driving. Engineered for Safety. A geometric gold lion emblem with blue sensor eyes beside the project name, over a navy background with a perspective road grid and object-tracking brackets.">
</p>

<p align="center">
  <b>An open-source driving platform derived from openpilot, integrating functional safety, SOTIF, cybersecurity, AI safety, and transparent engineering assurance while preserving broad vehicle compatibility.</b>
</p>

<p align="center">
  <a href="docs/liondriver/README.md">Documentation</a> &nbsp;·&nbsp;
  <a href="https://github.com/jherrodthomas/LionDriver/wiki">Wiki</a> &nbsp;·&nbsp;
  <a href="#platform-architecture">Architecture</a> &nbsp;·&nbsp;
  <a href="#living-safety-case">Living Safety Case</a> &nbsp;·&nbsp;
  <a href="#300-vehicle-ecosystem">Vehicle Compatibility</a> &nbsp;·&nbsp;
  <a href="#roadmap">Roadmap</a> &nbsp;·&nbsp;
  <a href="#getting-started">Getting Started</a> &nbsp;·&nbsp;
  <a href="#contributing">Contributing</a>
</p>

> [!IMPORTANT]
> **LionDriver is research and development software.** It is a driver-assistance system: the driver must stay attentive and in control at all times. It is not certified, makes no claim of ISO 26262 compliance or ASIL capability, and is not approved for unsupervised operation.

## Living Safety Case

LionDriver publishes its safety argument as it is built: the claims, the evidence for each one, the known counter-evidence against it, and what has and has not been reviewed. Every figure is generated from the records in [`assurance/case/`](assurance/case/README.md) and checked by CI on every pull request.

<p align="center">
  <img src="docs/assets/liondriver/assurance/dashboard.svg" width="100%" alt="Living Safety Case dashboard generated from the assurance records. The same values are listed as text in the full Living Safety Case.">
</p>

<!-- BEGIN GENERATED: assurance-headline (assurance/case/tools/generate_dashboard.py) -->

[![Download the safety case snapshot (PDF)](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fjherrodthomas%2FLionDriver%2Fliondriver-dev%2Fassurance%2Fcase%2Fbadge.json)](https://github.com/jherrodthomas/LionDriver/releases/download/snapshot-latest/LionDriver-safety-case.pdf) · [all snapshots and how to verify them](https://github.com/jherrodthomas/LionDriver/releases/tag/snapshot-latest)

**Development** · baseline `BL-002` at `bf6ce8c` · 36 claims (0 with accepted evidence) · 50 evidence items (0 accepted) · 42 open defeaters · records digest `d6368d324eab`

<!-- END GENERATED: assurance-headline -->

> **Assurance status represents recorded engineering evidence and review state. It does not constitute certification or approval for unsupervised operation.**

**[Open the full Living Safety Case →](assurance/README.md#living-safety-case)** lifecycle status, values as text, what the dashboard guarantees, and how the records fit together · [safety case (WP-K-01)](assurance/10-safety-case/WP-K-01-safety-case.md) · [known gaps](assurance/00-assessment/gap-assessment.md)

## Platform Architecture

<p align="center">
  <img src="docs/assets/liondriver/architecture.svg" width="100%" alt="Platform architecture. Layer 1, core driving platform inherited from openpilot: perception, prediction, planning, control, driver monitoring, human-machine interface. Layer 2, safety envelope in the panda firmware. Layer 3, vehicle integration in the opendbc car ports. Layer 4, supported vehicle ecosystem. A cross-cutting safety and assurance column applies to every layer. Implemented, drafted and proposed elements are marked differently.">
</p>

LionDriver keeps openpilot's driving stack and its central safety design: a large, learned driving stack (the doer) whose commands pass through a small, deterministic safety layer on the panda microcontroller (the checker) before they reach the car. LionDriver adds the engineering record around it, and the [gap assessment](assurance/00-assessment/gap-assessment.md) states plainly where the inherited checker does not yet meet what the safety goals require.

| Layer | Role | State |
|---|---|---|
| Core driving platform | Perception, prediction, planning, control, driver monitoring, HMI | Implemented, inherited from openpilot |
| Safety envelope | Actuator limits, engagement and release on driver input, message checks | Implemented, inherited; hardening proposed in the [technical safety requirements](assurance/03-system/WP-S-02-technical-safety-requirements.md) |
| Vehicle integration | Vehicle interfaces, ECU compatibility, hardware configurations, calibration, diagnostics | Implemented, inherited; vehicle operating assumptions drafted |
| Safety and assurance | Functional safety, SOTIF, cybersecurity, AI safety, safety case, traceability, V&V, change impact analysis | Draft work products, not yet reviewed |

More in the [architecture overview](docs/liondriver/architecture.md).

## 300+ Vehicle Ecosystem

LionDriver is built on openpilot's vehicle support and keeps every upstream car port. The pinned upstream version lists **335 car models** in [`docs/CARS.md`](docs/CARS.md), from cars and SUVs to minivans, pickups and light commercial vans. LionDriver is a multi-vehicle platform, not a single-vehicle retrofit.

<p align="center">
  <img src="docs/assets/liondriver/assurance/ecosystem.svg" width="100%" alt="Vehicle ecosystem card generated from the records: upstream-compatible car models, LionDriver-evaluated configurations, and assurance-supported configurations.">
</p>

> **Vehicle compatibility does not imply independent safety assurance.**

| Classification | Meaning |
|---|---|
| **Upstream Compatible** | Supported by the inherited openpilot integration |
| **LionDriver Evaluated** | Undergoing or completed documented engineering evaluation |
| **Assurance Supported** | Defined configuration with accepted evidence for specific safety claims |

The first evaluated configuration is the Toyota Corolla, 12th generation (E210), with Toyota Safety Sense 2.0, the reference vehicle for the assurance work. It is a starting point, not a limit: further vehicles join through a documented impact analysis against the assumptions the analysis makes about the car. No configuration is assurance-supported yet. See [vehicle compatibility](docs/liondriver/compatibility.md).

## Standards and Engineering Framework

<p align="center">
  <img src="docs/assets/liondriver/standards.svg" width="100%" alt="Standards-informed engineering framework. ISO 26262, functional safety: what if something breaks? ISO 21448, SOTIF: what if nothing breaks but the system still gets it wrong? ISO/SAE 21434, cybersecurity: what if someone attacks it? ISO/PAS 8800, AI safety: how far can a learned component be trusted? UL 4600, safety case: is the whole argument convincing?">
</p>

LionDriver follows standards-informed development: its work products are structured after these standards and cite their clauses, but **no compliance is claimed**, because no assessment has been performed. The [assurance strategy](assurance/01-management/WP-M-01-assurance-strategy.md) explains how each one is tailored to an open-source, supervised Level 2 system.

| Supporting practice | Where it is applied |
|---|---|
| Automotive SPICE | [Capability baseline](assurance/01-management/WP-M-13-aspice-capability-baseline.md) |
| Systems engineering and requirements management | [System requirements](assurance/03-system/WP-S-01-system-requirements.md) · [traceability procedure](assurance/07-supporting/WP-P-06-requirements-management-traceability.md) · [trace data](assurance/trace/README.md) |
| Safety analysis | [ASIL decomposition](assurance/08-analyses/WP-A-01-asil-decomposition.md) · [freedom from interference](assurance/08-analyses/WP-A-02-coexistence-freedom-from-interference.md) · [dependent failures](assurance/08-analyses/WP-A-03-dependent-failure-analysis.md) · [FTA/FMEA](assurance/08-analyses/WP-A-04-system-fta-fmea.md) |
| Simulation, SIL and HIL | [Embedded software testing](assurance/05-software/WP-W-08-embedded-software-testing.md) · [SOTIF verification and validation strategy](assurance/06-validation/WP-V-02-sotif-vv-strategy.md) · [simulation track](assurance/sim/README.md) · [ASIL C hazardous events in the plant loop](assurance/sim/README.md#37-the-asil-c-hazardous-events-in-the-loop) |
| Fault injection | [Fault injection specification](assurance/06-validation/WP-V-05-fault-injection.md) |
| Independent review | [Confirmation measures plan](assurance/01-management/WP-M-06-confirmation-measures-plan.md) · [verification review procedure](assurance/07-supporting/WP-P-05-verification-review-procedure.md) |
| IEC 61508 | Referenced for supplier safety documentation of the safety microcontroller ([component qualification](assurance/04-hardware/WP-H-07-hardware-component-qualification.md)) |

## Roadmap

<p align="center">
  <img src="docs/assets/liondriver/roadmap.svg" width="100%" alt="Roadmap. Phase 1, Foundation: active. Phase 2, Safety Engineering: active. Phase 3, Implementation and Verification: planned. Phase 4, Expanded Assurance: planned.">
</p>

Status is taken from what exists in the repository. "Draft" means the work product is written but not reviewed; nothing is marked complete before its review.

| Phase | Work | Status |
|---|---|---|
| **1 · Foundation** | Project governance and [safety management plan](assurance/01-management/WP-M-02-safety-plan.md) | Draft |
| | [Upstream baseline assessment](assurance/00-assessment/gap-assessment.md) | Draft |
| | [Assurance data model](assurance/case/README.md) and [traceability data](assurance/trace/README.md) | Draft; hazards, goals, assumptions and safety case recorded, requirements not yet |
| **2 · Safety Engineering** | [Hazard analysis](assurance/02-concept/WP-C-03-hara.md) and [functional safety concept](assurance/02-concept/WP-C-04-functional-safety-concept.md) | Draft |
| | [SOTIF analysis](assurance/02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), [cybersecurity analysis](assurance/02-concept/WP-C-09-tara.md), [AI safety requirements](assurance/02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) | Draft |
| | [Architecture analysis](assurance/03-system/WP-S-03-technical-safety-concept-architecture.md) | Draft |
| | [Field monitoring, safety anomaly and root cause analysis process](docs/safety/field-monitoring/README.md), first case FI-2026-001 (NHTSA PE26007) | Draft |
| **3 · Implementation and Verification** | Safety mechanisms from the technical safety requirements | Planned |
| | [ISO 26262-6 software lifecycle](assurance/01-management/WP-M-14-iso26262-6-implementation-specification.md) (Clauses 5–11) | Specified; starts after the Part 2–4 work products and supporting processes are approved |
| | Automated verification of the inherited safety code (unit tests, coverage gate, MISRA, mutation) | Running in [CI](.github/workflows/safety.yaml); not yet reviewed as evidence |
| | Regression testing, simulation, fault injection, evidence generation | Specified, not executed |
| **4 · Expanded Assurance** | More evaluated configurations, independent review, living safety-case maturity, continuous assurance, community contributions | Planned |

## Getting Started

**For development**, LionDriver uses openpilot's toolchain unchanged (Ubuntu 24.04 or macOS; see [`tools/README.md`](tools/README.md)):

```bash
git clone https://github.com/jherrodthomas/LionDriver.git
cd LionDriver
tools/op.sh setup
source .venv/bin/activate
scons -u
```

**For the assurance records**, only Python 3 is needed:

```bash
python3 assurance/case/tools/validate.py
python3 assurance/case/tools/generate_dashboard.py --check
```

**In a car:** LionDriver publishes no release build. Development builds must not be used on public roads outside the controlled test regime in [WP-V-07](assurance/06-validation/WP-V-07-vehicle-test-operations.md). How openpilot itself is installed and used is described in the [upstream project](https://github.com/commaai/openpilot#using-openpilot-in-a-car).

## Contributing

Contributions are welcome in software, functional safety, SOTIF, cybersecurity, AI safety, verification, documentation and vehicle integration. Safety-relevant changes need a rationale, an impact analysis and appropriate verification.

| | |
|---|---|
| [Contributing to LionDriver](docs/liondriver/contributing.md) | Rules for safety-relevant changes and assurance records |
| [Issues](https://github.com/jherrodthomas/LionDriver/issues) · [Pull requests](https://github.com/jherrodthomas/LionDriver/pulls) | Questions, bugs, reviews of the analyses; pull requests target `liondriver-dev` |
| [Documentation](docs/liondriver/README.md) | Architecture, compatibility, assurance and the inherited openpilot docs |
| [Wiki](https://github.com/jherrodthomas/LionDriver/wiki) | Orientation: roadmap, glossary, how decisions are made, reading the safety case. Kept in [`wiki/`](wiki/README.md) and mirrored on merge |
| [Upstream openpilot](https://github.com/commaai/openpilot) | The driving platform LionDriver is derived from |

## Maintainer and Upstream Attribution

**Jherrod Thomas** maintains LionDriver as an open engineering initiative: a public demonstration of safety-lifecycle development, systems engineering and assurance practice on a real automotive software platform.

LionDriver is derived from [openpilot](https://github.com/commaai/openpilot) by [comma.ai](https://comma.ai) and its contributors, and builds on their work. LionDriver is distributed under the [MIT license](LICENSE), which keeps comma.ai's copyright notice alongside LionDriver's; third-party components keep their own licences. LionDriver is an independent project and is not affiliated with or endorsed by comma.ai.

Open-source licensing does not establish automotive safety certification, regulatory approval, or suitability for unsupervised vehicle operation.
