# How the repository is organized

Two kinds of content live side by side: the driving software inherited from openpilot, and the engineering record
LionDriver adds around it.

![Platform architecture. Layer 1, core driving platform inherited from openpilot. Layer 2, safety envelope in the panda firmware. Layer 3, vehicle integration in the opendbc car ports. Layer 4, supported vehicle ecosystem. A cross-cutting safety and assurance column applies to every layer. Implemented, drafted and proposed elements are marked differently.](../docs/assets/liondriver/architecture.svg)

*The README architecture figure. Layers 1 to 4 are the inherited code below; the cross-cutting column is what LionDriver adds.*

## Inherited from openpilot

| Path | What it is |
|---|---|
| [`openpilot/`](../openpilot) | Perception, planning, control, driver monitoring, HMI: the application stack |
| [`panda/`](../panda) | The safety layer on the panda microcontroller that checks every actuator command |
| [`opendbc_repo/`](../opendbc_repo) | Vehicle interfaces, safety modes and car ports, listed in [CARS.md](../docs/CARS.md) |
| `msgq_repo/`, `rednose_repo/`, `tinygrad_repo/`, `teleoprtc_repo/` | Upstream libraries |
| [`docs/`](../docs) | Upstream documentation, kept where upstream keeps it |

Changed only by merging upstream or through a documented impact analysis. The pinned versions, and which
submodules point at LionDriver forks, are recorded in
[WP-M-11, upstream and supplier management](../assurance/01-management/WP-M-11-upstream-and-supplier-management.md).

## Added by LionDriver

| Path | What it is |
|---|---|
| [`assurance/`](../assurance/README.md) | Every work product, analysis, decision and review |
| [`assurance/case-records/`](../assurance/case-records/README.md) | Machine-readable claims, evidence, defeaters, baselines and reviews; the dashboard is generated from here |
| [`assurance/trace/`](../assurance/trace/README.md) | Traceability data between hazards, goals, requirements and tests |
| [`docs/liondriver/`](../docs/liondriver/README.md) | Architecture, vehicle compatibility, vehicle register, contributing |
| [`docs/safety/field-monitoring/`](../docs/safety/field-monitoring/README.md) | Hazard log, case register and the root cause process |
| [`tools/`](../tools) | LionDriver tooling that the workflows run: sync reports, severity, field monitoring, vehicles, CI manifests |
| [`wiki/`](../wiki/README.md) | These pages |

Changed by pull request to `liondriver-dev` and checked by the workflows below.

## The assurance tree, folder by folder

Folders are numbered in lifecycle order. Each work product is named `WP`, a letter for its area, and a number;
the [glossary](Glossary.md) decodes the letters. The authoritative table, with the standard clauses each folder
answers to, is in [`assurance/README.md`](../assurance/README.md#layout).

| Folder | Prefix | What it holds |
|---|---|---|
| `00-assessment/` | | Gap assessment of the inherited openpilot baseline against the safety goals; ISO 26262:2018 clause map |
| `01-management/` | `WP-M` | Plans: assurance strategy, safety, SOTIF, cybersecurity, AI safety; impact analysis; the decision register |
| `02-concept/` | `WP-C` | Item definition, ODD, HARA, functional safety concept, SOTIF hazards and triggering conditions, TARA, AI system definition |
| `03-system/` | `WP-S` | System and technical safety requirements, technical safety concept, timing budget, HSI, system verification |
| `04-hardware/` | `WP-H` | Hardware safety requirements, design, FMEDA, metrics, PMHF, component qualification |
| `05-software/` | `WP-W` | Software safety requirements, architecture, safety analysis, unit design and verification, ML engineering |
| `06-validation/` | `WP-V` | Safety validation, SOTIF known and unknown scenarios, fault injection, cybersecurity validation, vehicle test operations |
| `07-supporting/` | `WP-P` | Configuration, change and problem management, documentation, reviews, tool and component qualification, release |
| `08-analyses/` | `WP-A` | ASIL decomposition, freedom from interference, dependent failure analysis, FTA and FMEA, STPA |
| `09-production-operation/` | `WP-O` | Installation and provisioning, operation and service, user information, field monitoring, cybersecurity incident response |
| `10-safety-case/` | `WP-K` | The safety case, the cybersecurity case, assessment and release records |
| `case-records/`, `trace/`, `process/`, `models/`, `sim/` | | Machine-readable records, traceability, the integrated process model, reference models and simulation |

## What checks a change

Every workflow lives in [`.github/workflows/`](../.github/workflows).

| Workflow | Runs when | What it checks |
|---|---|---|
| [assurance](../.github/workflows/assurance.yaml) | A change touches `assurance/`, the README, `docs/liondriver/` or the tools | Trace consistency, relative links, every generated figure and page current, the decision register's lifecycle rules, Markdown tables, HARA and FSC consistency, FMEA data lint |
| [safety](../.github/workflows/safety.yaml) | A change touches the panda or opendbc submodule pins or the coverage tooling | Safety tests with UBSan and a 100 % line-coverage gate, MISRA C:2012 on the opendbc safety code and on panda, the reference release build, build manifests |
| [b2b](../.github/workflows/b2b.yaml) | A change touches the reference models or the safety code | Back-to-back run of the reference model against the safety C, both build variants |
| [safety case snapshot](../.github/workflows/safety-case-snapshot.yaml) | A push to `liondriver-dev` touches `assurance/`, or a `bl-*` tag | Builds, attests and publishes the PDF snapshot as a release |
| [safety case controlled copy](../.github/workflows/safety-case-controlled-copy.yaml) | Started by hand | Issues a numbered controlled copy of the safety case for a named recipient and records it |
| [wiki](../.github/workflows/wiki.yaml) | Every pull request, and every push to `liondriver-dev` | Builds these pages and checks that every link target still exists; on a push, syncs them and the generated figures to the GitHub wiki |
| [PR review](../.github/workflows/auto_pr_review.yaml), [diff report](../.github/workflows/diff_report.yaml), [tests](../.github/workflows/tests.yaml), [docs](../.github/workflows/docs.yaml) | Inherited from openpilot | Labels pull requests by the paths they touch, posts the process-replay diff, runs the upstream unit tests and documentation build |

A passing workflow accepts nothing on its own. It can be evidence that a reviewer accepts; see
[contributing to LionDriver](../docs/liondriver/contributing.md).
