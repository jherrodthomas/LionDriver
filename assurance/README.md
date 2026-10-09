# LionDriver Assurance Repository

This tree holds the engineering assurance work products for LionDriver: functional
safety (ISO 26262:2018), SOTIF (ISO 21448:2022), cybersecurity (ISO/SAE 21434:2021),
AI safety (ISO/PAS 8800:2024) and process capability (Automotive SPICE 4.0). Safety-case
structure follows UL 4600 principles where they apply to a supervised Level 2 system.

> [!WARNING]
> Everything here is a **draft prepared for engineering review**. None of it has passed
> verification review, confirmation review or functional safety assessment. A document
> existing here does not mean the activity behind it is complete. Read the `Status` field
> of each work product and the register in [`01-management/WP-M-00-work-product-register.md`](01-management/WP-M-00-work-product-register.md).

## Start here

| Document | Why read it |
|---|---|
| [00-assessment/gap-assessment.md](00-assessment/gap-assessment.md) | Baseline review of the inherited openpilot code and process against the target standards |
| [01-management/WP-M-01-assurance-strategy.md](01-management/WP-M-01-assurance-strategy.md) | The assurance path: tailoring, safety architecture argument, phases and gates |
| [01-management/WP-M-00-work-product-register.md](01-management/WP-M-00-work-product-register.md) | Every required work product, its source clause, owner, gate and status |
| [02-concept/WP-C-01-item-definition.md](02-concept/WP-C-01-item-definition.md) | What the item is, where its boundary is, and what it assumes about the vehicle |
| [02-concept/WP-C-03-hara.md](02-concept/WP-C-03-hara.md) | Hazards, ASILs and safety goals |

## Layout

| Folder | Content | Primary standard clauses |
|---|---|---|
| `00-assessment/` | Baseline gap assessments | n/a |
| `01-management/` | Plans, safety management, supplier and upstream management | 26262-2, 21434 §5–8, 21448 §4, MAN.3/5, ACQ.4 |
| `02-concept/` | Item definition, HARA, FSC, SOTIF hazard and insufficiency analysis, TARA | 26262-3, 21448 §5–8, 21434 §9/§15, PAS 8800 |
| `03-system/` | Technical safety requirements and concept, system architecture, HSI, system integration and qualification | 26262-4, SYS.1–5 |
| `04-hardware/` | Hardware safety requirements, design, metrics, component qualification | 26262-5, 26262-8 §13, HWE.1–4 |
| `05-software/` | Software requirements, architecture, units, verification, ML engineering | 26262-6, SWE.1–6, MLE.1–4, SUP.11 |
| `06-validation/` | Safety validation, SOTIF known/unknown scenario evaluation, pen testing, vehicle test operations | 26262-4 §8, 21448 §9–11, 21434 §11, VAL.1 |
| `07-supporting/` | CM, change, problem resolution, documentation, tool and software-component qualification | 26262-8, SUP.1/8/9/10 |
| `08-analyses/` | ASIL decomposition, coexistence, DFA, system FTA/FMEA | 26262-9 |
| `09-production-operation/` | Installation, operation, field monitoring, incident response | 26262-7, 21448 §13, 21434 §12–14 |
| `10-safety-case/` | Safety, SOTIF and cybersecurity cases; assessment and release records | 26262-2 §6, 21448 §12, 21434 §6, UL 4600 |
| `trace/` | Machine-readable requirement and trace data | 26262-8 §6, ASPICE traceability BPs |

## Conventions

### Identifiers

| Prefix | Meaning | Example |
|---|---|---|
| `WP-<area>-<nn>` | Work product | `WP-C-03` (HARA) |
| `H-<nn>` | Hazard (functional safety, HARA) | `H-01` |
| `HS-<nn>` | Hazardous event / rated situation | `HS-01.2` |
| `SG-<nn>` | Safety goal | `SG-01` |
| `FSR-<nn>` | Functional safety requirement | `FSR-01.03` |
| `TSR-<nn>` | Technical safety requirement | `TSR-014` |
| `SWSR-<nn>` / `HWSR-<nn>` | Software / hardware safety requirement | `SWSR-031` |
| `SH-<nn>` | SOTIF hazard (hazardous behaviour from insufficiency) | `SH-04` |
| `TC-<nn>` | SOTIF triggering condition | `TC-12` |
| `FI-<nn>` | Functional insufficiency | `FI-07` |
| `TS-<nn>` / `CSG-<nn>` / `CSR-<nn>` | Threat scenario / cybersecurity goal / cybersecurity requirement | `CSG-02` |
| `AOU-<nn>` | Assumption of use (on the vehicle, driver or environment) | `AOU-05` |
| `GAP-<nn>` | Gap finding from an assessment | `GAP-17` |
| `OI-<nn>` | Open item to resolve before the next gate (per document) | `OI-3` |

Requirement IDs never get reused. A withdrawn requirement keeps its ID and is marked `Withdrawn`.

### Document control header

Every work product starts with this block:

```
| Field | Value |
|---|---|
| Work product | WP-x-nn <name> |
| Standard reference | <clause list> |
| Version | 0.1 |
| Status | Skeleton / Draft / In review / Approved / Baselined |
| ASIL / scope | <highest ASIL addressed, or QM / SOTIF / CS> |
| Author | <name> |
| Reviewer(s) | <name, independence level I0–I3> |
| Approver | <name> |
| Baseline | <git commit or tag the content refers to> |
```

### Status meanings

| Status | Meaning |
|---|---|
| Skeleton | Structure and clause mapping exist; content still to be written |
| Draft | Content written, derived from code review and engineering judgement; not yet verified |
| In review | Verification review open (pull request) |
| Approved | Verification review passed and approved by the approver named in the safety plan |
| Baselined | Approved and frozen in a tagged configuration baseline |

### Changing a work product

Work products change through pull requests in the same way code does (see
[WP-P-02 change management](07-supporting/WP-P-02-change-management.md)). If a pull request touches safety-relevant code
(see the safety-relevant file list in [WP-P-01 configuration management](07-supporting/WP-P-01-configuration-management-plan.md)),
it updates the affected work products or records an impact analysis that says why none are affected.

### Standards text

The standards are copyrighted and are not reproduced here. Clause references point to the
editions named above. Check each work-product clause number against your licensed copy
before an audit.
