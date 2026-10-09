# WP-P-06 Requirements Management and Traceability Procedure

| Field | Value |
|---|---|
| Work product | WP-P-06 Requirements management and traceability procedure |
| Standard reference | ISO 26262-8:2018 §6; ISO 21448:2022 §5, §7–8 (requirements from SOTIF analyses); ISO/SAE 21434:2021 §9–10 (cybersecurity goals and requirements); ASPICE 4.0 SYS.2–5, SWE.1–6 traceability and consistency BPs |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Defines how safety, SOTIF, cybersecurity and system requirements are written, identified, managed and traced, and the machine-readable format under `assurance/trace/` ([WP-T-01](../trace/README.md)). Closes the planning side of GAP-14 ([gap assessment](../00-assessment/gap-assessment.md)): today limits live as commented constants (for example `opendbc_repo/opendbc/safety/modes/toyota.h:173-210`) and tests reference constants, not requirements.

`assurance/trace/` does not exist at the baseline; this document specifies what it will contain (OI-1).

## 2. Requirement attributes

| Attribute | YAML key | Mandatory | Content |
|---|---|---|---|
| Identifier | `id` | Yes | Prefix per [`assurance/README.md`](../README.md#identifiers): `SG-`, `FSR-`, `TSR-`, `SWSR-`, `HWSR-`, `CSG-`, `CSR-`, `SYS-` (non-safety system requirement, [WP-S-01](../03-system/WP-S-01-system-requirements.md)), `SOTIF-` (functional modification requirement, [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md)), `AIR-` (AI safety requirement, [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md)). Never reused |
| Title | `title` | Yes | ≤ 10 words |
| Statement | `text` | Yes | "The <element> shall <behaviour> [condition] [within <time>]" |
| Type | `type` | Yes | `functional`, `performance`, `timing`, `interface`, `safety-mechanism`, `constraint`, `production-operation` |
| ASIL / class | `asil` | Yes for FuSa | `QM`, `A`, `B`, `C`, `D`, or decomposed form `B(D)`; `n/a` for SOTIF/CS/SYS |
| CAL | `cal` | CS only | `CAL1`–`CAL4` per [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) |
| Rationale | `rationale` | Yes | Why this requirement and value; physical basis for limits |
| Source / parent | `parents` | Yes (except SG/CSG) | List of parent IDs (SG, FSR, H, SH, TC, FI, TS, AOU, GAP) |
| Allocation | `allocated_to` | Yes | Architectural element from [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) / [WP-W-03](../05-software/WP-W-03-software-architecture.md), e.g. `panda.safety.toyota`, `panda.main.heartbeat`, `host.selfdrived`, `driver`, `vehicle.eps` |
| Verification method | `verification` | Yes | One or more of `review`, `analysis`, `unit-test`, `integration-test`, `hil`, `fault-injection`, `vehicle-test`, `replay` |
| Verification criteria | `acceptance` | Yes for TSR/SWSR/HWSR | Measurable pass criterion |
| Status | `status` | Yes | `proposed`, `agreed`, `implemented`, `verified`, `withdrawn` |
| Safe state / FTTI | `safe_state`, `ftti_ms` | Where applicable | |
| Code evidence (as-is) | `implemented_in` | Optional | Paths with lines, for back-filled requirements (T-03) |
| Notes | `notes` | No | |

## 3. Quality criteria

Each requirement is checked against these criteria in review ([WP-P-05 §5.4](WP-P-05-verification-review-procedure.md#54-requirements-any-level-fsr-tsr-swsr-hwsr-csr-sotif)).

| Criterion | Test |
|---|---|
| Unambiguous | One interpretation; no "fast", "appropriate", "normally", "etc." |
| Atomic | One behaviour per requirement; no "and/or" joining separate behaviours |
| Verifiable | A pass/fail criterion exists with stated method |
| Feasible | Achievable with the allocated element (e.g. panda MCU resources) |
| Consistent | No conflict with siblings, parents, or the code at the baseline (or a change request exists) |
| Complete | Units, ranges, tolerances, timing, operating mode and condition stated |
| Traceable | Parent and allocation exist and are valid IDs |
| Hierarchically correct | Content belongs to its level (no implementation detail in an FSR) |
| Comprehensible | Understandable by a reviewer at the next level down |

Back-filled requirements from existing code (T-03) also need: the value as implemented, its units (raw counts converted to physical units where possible), and a gap note if the value has no rationale yet (GAP-04).

## 4. Trace model

```text
FuSa:   H / HS ──> SG ──> FSR ──> TSR ──┬──> SWSR ──> code (C/Python) ──> unit test
                                        │              └─> SW integration test
                                        ├──> HWSR ──> HW design ──> HW test
                                        └──> TSR ──> system test / HIL / vehicle test
        AOU <── FSR, TSR (assumptions on driver / vehicle ECUs)
SOTIF:  SH ──> TC / FI ──> SOTIF- (functional modification) ──> SYS/TSR/AIR ──> V&V scenario (WP-V-03/04)
        SH shares HS rows with the HARA (one hazard log)
AI:     FI ──> AIR ──> model / dataset requirement ──> model test (WP-W-10)
CS:     TS ──> CSG ──> CSR ──> SWSR/HWSR or CSR(impl) ──> code ──> CS test / pen test (WP-V-06)
        CSG <──> SG (where an attack causes a safety hazard)
Problems and changes:  issue #n ──> requirement IDs affected (WP-P-02, WP-P-03)
```

| Link | Direction stored | Cardinality |
|---|---|---|
| parent | child → parent (`parents`) | n:m |
| allocation | requirement → element (`allocated_to`) | n:m |
| implementation | code → requirement (`@req` tag in code comment, §6) | n:m |
| verification | test → requirement (`@req` tag or `verification.yaml`) | n:m |
| result | test run → test (generated from CI output) | n:1 |

Bidirectional views (requirement → children, requirement → tests) are generated, never hand-maintained.

## 5. Machine-readable format (`assurance/trace/`)

### 5.1 Layout

```text
assurance/trace/
  README.md                 # WP-T-01: overview, how to run checks
  schema/
    item.schema.json        # JSON Schema for all items (validated in CI)
  items/
    hazards.yaml            # H-, HS-
    goals.yaml              # SG-, CSG-
    fsr.yaml  tsr.yaml  swsr.yaml  hwsr.yaml
    sotif.yaml              # SH-, TC-, FI-, SOTIF-
    ai.yaml                 # AIR-
    cs.yaml                 # TS-, CSR-
    sys.yaml                # SYS-
    aou.yaml                # AOU-
  links/
    verification.yaml       # explicit test -> requirement links (for inherited/shared tests)
  elements.yaml             # allowed allocation targets, with paths
  safety-relevant-files.txt # machine copy of WP-P-01 §4 (proposed)
  tools/check_trace.py      # consistency checker (§7)
```

Reports (trace matrix, coverage of requirements by tests) are generated in CI and archived with the evidence package; they are not committed.

### 5.2 Item schema (YAML)

```yaml
# items/swsr.yaml
- id: SWSR-031
  title: Toyota LKA steering torque magnitude limit
  type: safety-mechanism
  text: >-
    The Toyota safety mode shall block any STEERING_LKA (0x2E4) frame whose
    commanded torque magnitude exceeds 1500 raw units.
  asil: TBD            # from WP-C-03 / WP-S-02
  rationale: >-
    Bounds lateral actuation to a controllable level. Physical value (Nm) and
    controllability basis to be established (GAP-04).
  parents: [TSR-014]
  allocated_to: [panda.safety.toyota]
  verification: [unit-test, hil]
  acceptance: Frames with |torque| > 1500 are not transmitted; counter safety_tx_blocked increments.
  status: proposed
  implemented_in:
    - opendbc_repo/opendbc/safety/modes/toyota.h:173
    - opendbc_repo/opendbc/safety/lateral.h:60-151
  notes: Example only. Not an agreed requirement.
```

Schema rules: `id` matches `^(H|HS|SG|FSR|TSR|SWSR|HWSR|SH|TC|FI|SOTIF|AIR|TS|CSG|CSR|SYS|AOU)-[0-9]{2,3}(\.[0-9]{1,2})?$`; `status` from the enum in §2; `parents` and `allocated_to` must resolve; withdrawn items stay in the file.

### 5.3 Verification link file

```yaml
# links/verification.yaml
- test: opendbc_repo/opendbc/safety/tests/test_toyota.py::TestToyotaSafetyTorque::test_steer_safety_check
  reqs: [SWSR-031]
  level: unit          # unit | integration | hil | vehicle | replay | review
  environment: host-x86   # host-x86 | cortex-m7 | hil-bench | vehicle
```

## 6. How code and tests reference requirements

The test runners at the baseline are `unittest`-based: `tools/test_runner.py` (openpilot) and `python -m unittest discover` in `opendbc_repo/opendbc/safety/tests/test.sh`. No pytest is used, so pytest markers are not an option without changing the runner. The convention therefore uses plain text tags that any runner preserves.

| Artefact | Convention | Example |
|---|---|---|
| Python test method (own test) | Tag line in the docstring | `"""Torque above limit is blocked. @req SWSR-031 @req SWSR-032"""` |
| Python test inherited from a shared base (e.g. `opendbc_repo/opendbc/safety/tests/common.py`, which `test_toyota.py` classes inherit) | Link in `links/verification.yaml` with the concrete class path, because a tag in the shared base would apply to every brand | see §5.3 |
| C safety code | Comment on the line before the implementing statement | `// @req SWSR-031` |
| Python product code | Comment | `# @req TSR-020` |
| Vehicle / HIL test procedure | Header field `Requirements:` in the procedure Markdown | `Requirements: TSR-014, TSR-015` |

Tag grammar: `@req <ID>` with one ID per tag; multiple tags allowed. Tags inside `opendbc_repo` and `panda` are added in the LionDriver forks (requires D-01).

## 7. Consistency checks to automate

Run by `assurance/trace/tools/check_trace.py` in CI on every PR that touches `assurance/trace/**` or any SR-A/SR-Q path (OI-2).

| # | Check | Severity |
|---|---|---|
| K1 | All YAML files validate against the schema | Error |
| K2 | IDs unique across all files; no ID removed compared with the previous baseline (withdrawn instead) | Error |
| K3 | Every `parents` and `allocated_to` value resolves | Error |
| K4 | Every SG has ≥ 1 FSR; every FSR ≥ 1 TSR; every TSR allocated to SW or HW has ≥ 1 SWSR/HWSR | Error at G2/G3, warning before |
| K5 | ASIL of child ≥ parent ASIL, unless decomposition notation is used and referenced in WP-A-01 | Error |
| K6 | Every `@req` tag in code and tests refers to an existing, non-withdrawn ID | Error |
| K7 | Every TSR/SWSR/HWSR with `status: verified` has ≥ 1 linked test whose latest CI result at the baseline is pass | Error |
| K8 | Every SWSR with ASIL ≥ A has ≥ 1 `@req` implementation tag | Warning until G3, then error |
| K9 | Requirements with `verification: hil` or `vehicle-test` have a linked procedure | Warning |
| K10 | Every SR-A source file contains ≥ 1 `@req` tag (unreferenced safety code) | Warning until G3, then error |
| K11 | Markdown requirement tables in WPs match YAML text (hash compare on `id` + `text`) | Error |
| K12 | Each hazard HS- is linked to an SG or SH, or marked as not hazardous with reason | Error at G1 |

## 8. Requirements change

Requirements change through [WP-P-02](WP-P-02-change-management.md). A change to `text`, `asil` or `parents` of an `agreed` or later requirement resets the status of linked children and tests to `proposed` / unverified until re-reviewed (implemented in K7 by comparing hashes with the previous baseline).

## 9. Roles

| Role | Responsibility |
|---|---|
| Requirement owner (per level) | Writes and maintains requirements of the WP they author |
| Safety reviewer | Reviews per WP-P-05 §5.4 |
| Configuration manager | Ensures trace data is in each baseline |

## 10. Open items

| ID | Item |
|---|---|
| OI-1 | Create `assurance/trace/` with `README.md` (WP-T-01), schema and empty item files |
| OI-2 | Implement `check_trace.py` and the CI job |
| OI-3 | Decide whether to add a small `req` decorator helper for unittest in addition to docstring tags (needs a module in each fork) |
| OI-4 | Define the element catalogue (`elements.yaml`) from WP-S-03 and WP-W-03 |
| OI-5 | Back-fill envelope requirements from `toyota.h`, `safety.h`, `lateral.h`, `longitudinal.h` and `panda/board/main.c` (T-03); the example SWSR-031 above is illustrative only |
