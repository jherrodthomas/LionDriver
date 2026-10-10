# LionDriver documentation

LionDriver is openpilot plus an open engineering assurance framework. This page is the entry point for the LionDriver-specific documentation. The inherited openpilot documentation stays where upstream keeps it, in the rest of [`docs/`](../).

## Start here

| If you want to | Read |
|---|---|
| Understand how the platform is structured | [Architecture](architecture.md) |
| See which vehicles are supported, and what that does and does not mean | [Vehicle compatibility](compatibility.md) |
| See the current assurance state and how it is computed | [Living Safety Case](../../assurance/case/README.md) |
| Browse every safety, SOTIF, cybersecurity and AI-safety work product | [Assurance work products](../../assurance/README.md) |
| Contribute, especially to safety-relevant code | [Contributing to LionDriver](contributing.md) |

## Engineering areas

All engineering work products are drafts under review. Each one states its own status in its document-control header.

| Area | Main work products |
|---|---|
| Safety management | [Assurance strategy](../../assurance/01-management/WP-M-01-assurance-strategy.md) · [Safety plan](../../assurance/01-management/WP-M-02-safety-plan.md) · [Impact analysis](../../assurance/01-management/WP-M-12-impact-analysis.md) |
| Functional safety (ISO 26262) | [Item definition](../../assurance/02-concept/WP-C-01-item-definition.md) · [HARA](../../assurance/02-concept/WP-C-03-hara.md) · [Functional safety concept](../../assurance/02-concept/WP-C-04-functional-safety-concept.md) · [Technical safety concept](../../assurance/03-system/WP-S-03-technical-safety-concept-architecture.md) |
| SOTIF (ISO 21448) | [SOTIF hazards](../../assurance/02-concept/WP-C-05-sotif-hazard-identification.md) · [Insufficiencies and triggering conditions](../../assurance/02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) · [Validation strategy](../../assurance/06-validation/WP-V-02-sotif-vv-strategy.md) |
| Cybersecurity (ISO/SAE 21434) | [TARA](../../assurance/02-concept/WP-C-09-tara.md) · [Cybersecurity goals and concept](../../assurance/02-concept/WP-C-10-cybersecurity-goals-and-concept.md) · [Cybersecurity case](../../assurance/10-safety-case/WP-K-03-cybersecurity-case.md) |
| AI safety (ISO/PAS 8800) | [AI system definition and requirements](../../assurance/02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md) · [ML engineering](../../assurance/05-software/WP-W-10-ml-engineering.md) |
| Verification and validation | [Unit verification](../../assurance/05-software/WP-W-06-software-unit-verification.md) · [Fault injection](../../assurance/06-validation/WP-V-05-fault-injection.md) · [Safety validation](../../assurance/06-validation/WP-V-01-safety-validation.md) |
| Safety case | [Safety case](../../assurance/10-safety-case/WP-K-01-safety-case.md) · [Machine-readable records](../../assurance/case/README.md) · [Traceability data](../../assurance/trace/README.md) |

## Inherited openpilot documentation

| Topic | Document |
|---|---|
| Upstream safety model and its limits | [SAFETY.md](../SAFETY.md) · [LIMITATIONS.md](../LIMITATIONS.md) |
| Supported vehicles | [CARS.md](../CARS.md) |
| Development setup and contribution rules | [CONTRIBUTING.md](../CONTRIBUTING.md) |
| Porting a car | [Add support for a car](../how-to/car-port.md) |
