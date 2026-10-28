# Glossary

The codes that appear in file names, commit messages, the records and the dashboard, decoded in one place. Every abbreviation and record code used on the assurance pages and figures is also listed, one line each, in [assurance/terms.md](../assurance/terms.md), the list those pages and figures are checked against.

## Work product prefixes

Each work product is named `WP`, a letter for its area, and a number, for example `WP-C-03` is the HARA. The
[work product register](../assurance/01-management/WP-M-00-work-product-register.md) lists every one with its
revision and status.

| Prefix | Area | Folder |
|---|---|---|
| `WP-M` | Management: plans, strategy, impact analysis | `01-management/` |
| `WP-C` | Concept: item definition, HARA, safety concepts, TARA | `02-concept/` |
| `WP-S` | System: requirements, technical safety concept, HSI | `03-system/` |
| `WP-H` | Hardware: requirements, FMEDA, metrics | `04-hardware/` |
| `WP-W` | Software: requirements, architecture, verification, ML | `05-software/` |
| `WP-V` | Validation: safety validation, SOTIF scenarios, fault injection | `06-validation/` |
| `WP-P` | Supporting processes: configuration, change, tools, release | `07-supporting/` |
| `WP-A` | Analyses: decomposition, DFA, FTA and FMEA, STPA | `08-analyses/` |
| `WP-O` | Operation: installation, user information, field monitoring, incident response | `09-production-operation/` |
| `WP-K` | Safety case and cybersecurity case | `10-safety-case/` |

## Record identifiers

| Code | Reads as | Where it lives |
|---|---|---|
| `H-`, `HE-` | Hazard, hazardous event | [HARA, WP-C-03](../assurance/02-concept/WP-C-03-hara.md) |
| `SG-` | Safety goal, with its ASIL | HARA; recorded in [`assurance/case-records/`](../assurance/case-records/README.md) |
| `FSR-` | Functional safety requirement | [Functional safety concept, WP-C-04](../assurance/02-concept/WP-C-04-functional-safety-concept.md) |
| `TSR-` | Technical safety requirement | [WP-S-02](../assurance/03-system/WP-S-02-technical-safety-requirements.md) |
| `HWSR-`, `SWSR-` | Hardware and software safety requirement | [WP-H-01](../assurance/04-hardware/WP-H-01-hardware-safety-requirements.md), [WP-W-02](../assurance/05-software/WP-W-02-software-safety-requirements.md); trace data in [`assurance/trace/`](../assurance/trace/README.md) |
| `AOU-` | Assumption of use: what the analysis assumes about the car, the driver or the environment | [`assurance/case-records/`](../assurance/case-records/README.md) |
| `SM-` | Safety mechanism | [Technical safety concept, WP-S-03](../assurance/03-system/WP-S-03-technical-safety-concept-architecture.md) |
| `SFM-` | System failure mode | [System FTA and FMEA, WP-A-04](../assurance/08-analyses/WP-A-04-system-fta-fmea.md) |
| `SWF-` | Software failure mode | [Software safety analysis, WP-W-04](../assurance/05-software/WP-W-04-software-safety-analysis.md) |
| `DFI-` | Dependent failure initiator | [Dependent failure analysis, WP-A-03](../assurance/08-analyses/WP-A-03-dependent-failure-analysis.md) |
| `DF-` | Defeater: known counter-evidence against a claim | [`assurance/case-records/defeaters/`](../assurance/case-records/defeaters) |
| `ACT-` | Action recorded against the safety case | [`assurance/case-records/actions/`](../assurance/case-records/actions) |
| `BL-` | Baseline: a frozen, named state of the record. The dashboard names the baseline and the commit it was taken at | [`assurance/case-records/baselines/`](../assurance/case-records/baselines) |
| `CFG-` | Vehicle configuration | [`assurance/case-records/configurations/`](../assurance/case-records/configurations), [vehicle register](../docs/liondriver/vehicles/README.md) |
| `DQ-` | Decision question for the project lead | [Decision register](How-decisions-are-made.md) |
| `DEC-`, `IR-` | ASIL decomposition record and independence requirement; `B(C)` is an element developed to ASIL B for an ASIL C goal ([explained](ASIL-decomposition.md)) | [WP-A-01](../assurance/08-analyses/WP-A-01-asil-decomposition.md) |
| `GAP-` | A gap between the inherited baseline and what the safety goals need | [Gap assessment](../assurance/00-assessment/gap-assessment.md) |
| `TL-` | A tool, with its classification | [WP-P-07](../assurance/07-supporting/WP-P-07-tool-classification-qualification.md) |
| `FI-` | Field incident case, for example `FI-2026-001` | [Field monitoring register](../docs/safety/field-monitoring/REGISTER.md) |
| `G0` to `G6` | Lifecycle gates | [Project plan, WP-M-03](../assurance/01-management/WP-M-03-project-plan.md) |

## Safety-case vocabulary

| Term | Meaning |
|---|---|
| **Claim** | A statement the safety case argues is true. |
| **Evidence item** | A test result, analysis or review that supports a claim. Each one carries a review state; it is *accepted* only after confirmation review. |
| **Defeater** | Known counter-evidence, or a reason the argument might not hold. Open defeaters are published, not hidden. |
| **Confirmation review** | An independent check that a work product does what its standard asks. Nothing leaves draft without one ([WP-P-05](../assurance/07-supporting/WP-P-05-verification-review-procedure.md)). |
| **Baseline** | A frozen, named state of the whole record against which the dashboard is computed. |
| **Doer and checker** | The learned driving stack proposes; the small deterministic panda safety layer checks before anything reaches the car. |
| **Upstream compatible, LionDriver evaluated, assurance supported** | The three vehicle classifications, from "openpilot supports it" to "accepted evidence for specific claims on this configuration". See [vehicle compatibility](../docs/liondriver/compatibility.md). |
| **ODD** | Operational design domain: the conditions under which the system is meant to operate ([WP-C-02](../assurance/02-concept/WP-C-02-odd-and-intended-functionality.md)). |

## Standards named in the record

| Standard | The question it answers | Main work products |
|---|---|---|
| ISO 26262 | What if something breaks? | HARA, functional and technical safety concepts, hardware and software requirements |
| ISO 21448 (SOTIF) | What if nothing breaks but the system still gets it wrong? | [WP-C-05](../assurance/02-concept/WP-C-05-sotif-hazard-identification.md), [WP-C-06](../assurance/02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), [WP-V-02](../assurance/06-validation/WP-V-02-sotif-vv-strategy.md) |
| ISO/SAE 21434 | What if someone attacks it? | [TARA, WP-C-09](../assurance/02-concept/WP-C-09-tara.md), [cybersecurity case, WP-K-03](../assurance/10-safety-case/WP-K-03-cybersecurity-case.md) |
| ISO/PAS 8800 | How far can a learned component be trusted? | [WP-C-11](../assurance/02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md), [ML engineering, WP-W-10](../assurance/05-software/WP-W-10-ml-engineering.md) |
| UL 4600 | Is the whole argument convincing? | [Safety case, WP-K-01](../assurance/10-safety-case/WP-K-01-safety-case.md) |
| Automotive SPICE | Are the processes capable? | [WP-M-13](../assurance/01-management/WP-M-13-aspice-capability-baseline.md) |
