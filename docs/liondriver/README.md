# LionDriver documentation

LionDriver is openpilot plus an open engineering assurance framework. This page is the entry point for the LionDriver-specific documentation. The inherited openpilot documentation stays where upstream keeps it, in the rest of [`docs/`](../).

<p align="center">
  <img src="../assets/liondriver/architecture.svg" width="100%" alt="LionDriver platform architecture: core driving platform, safety envelope, vehicle integration and supported vehicle ecosystem as stacked layers, with a cross-cutting safety and assurance column. A legend separates implemented, drafted and proposed elements.">
</p>

*The platform in four layers; details on the [Architecture](architecture.md) page.*

## Start here

| If you want to | Read |
|---|---|
| Understand how the platform is structured | [Architecture](architecture.md) |
| See how the stack steers and plans speed, and where the safety changes land | [Driving and path planning](driving-and-planning.md) |
| See how the speed planner keeps its distance and when it warns | [Speed planning](speed-planning.md) |
| See what the learned models see and output, and what can go wrong | [Perception models](perception-models.md) |
| See which vehicles are supported, and what that does and does not mean | [Vehicle compatibility](compatibility.md) |
| Look up the exact vehicles a configuration covers (model years, model code, firmware) | [Vehicle register](vehicles/README.md) |
| See the current assurance state and how it is computed | [Living Safety Case](../../assurance/case-records/README.md) |
| Browse every safety, SOTIF, cybersecurity and AI-safety work product | [Assurance work products](../../assurance/README.md) |
| Contribute, especially to safety-relevant code | [Contributing to LionDriver](contributing.md) |
| Get oriented: roadmap, glossary, how decisions are made | [Wiki](https://github.com/jherrodthomas/LionDriver/wiki), kept in [`wiki/`](../../wiki/README.md) and mirrored on merge |

## Engineering areas

All engineering work products are drafts under review. Each one states its own status in its document-control header.

<p align="center">
  <img src="../assets/liondriver/standards.svg" width="100%" alt="The five standards the engineering framework draws on, each with the question it answers: ISO 26262, what if something breaks; ISO 21448 SOTIF, what if nothing breaks but it still gets it wrong; ISO/SAE 21434, what if someone attacks it; ISO/PAS 8800, how far a learned component can be trusted; UL 4600, whether the whole argument is convincing. Aligned practices, not a claim of compliance.">
</p>

*One question per standard; the table below links each area's main work products.*

| Area | Main work products |
|---|---|
| Safety management | [Assurance strategy](../../assurance/01-management/WP-M-01-assurance-strategy.md) · [Safety plan](../../assurance/01-management/WP-M-02-safety-plan.md) · [Impact analysis](../../assurance/01-management/WP-M-12-impact-analysis.md) |
| Functional safety (ISO 26262) | [Item definition](../../assurance/02-concept/WP-C-01-item-definition.md) · [HARA](../../assurance/02-concept/WP-C-03-hara.md) · [Functional safety concept](../../assurance/02-concept/WP-C-04-functional-safety-concept.md) · [Technical safety concept](../../assurance/03-system/WP-S-03-technical-safety-concept-architecture.md) |
| SOTIF (ISO 21448) | [SOTIF hazards](../../assurance/02-concept/WP-C-05-sotif-hazard-identification.md) · [Insufficiencies and triggering conditions](../../assurance/02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) · [Validation strategy](../../assurance/06-validation/WP-V-02-sotif-vv-strategy.md) |
| Cybersecurity (ISO/SAE 21434) | [TARA](../../assurance/02-concept/WP-C-09-tara.md) · [Cybersecurity goals and concept](../../assurance/02-concept/WP-C-10-cybersecurity-goals-and-concept.md) · [Cybersecurity case](../../assurance/10-safety-case/WP-K-03-cybersecurity-case.md) |
| AI safety (ISO/PAS 8800) | [AI system definition and requirements](../../assurance/02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) · [ML engineering](../../assurance/05-software/WP-W-10-ml-engineering.md) |
| Verification and validation | [Unit verification](../../assurance/05-software/WP-W-06-software-unit-verification.md) · [Fault injection](../../assurance/06-validation/WP-V-05-fault-injection.md) · [Safety validation](../../assurance/06-validation/WP-V-01-safety-validation.md) |
| Safety case | [Safety case](../../assurance/10-safety-case/WP-K-01-safety-case.md) · [Machine-readable records](../../assurance/case-records/README.md) · [Traceability data](../../assurance/trace/README.md) |

## Inherited openpilot documentation

| Topic | Document |
|---|---|
| Upstream safety model and its limits | [SAFETY.md](../SAFETY.md) · [LIMITATIONS.md](../LIMITATIONS.md) |
| Supported vehicles | [CARS.md](../CARS.md) |
| Development setup and contribution rules | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Porting a car | [Add support for a car](../how-to/car-port.md) |
