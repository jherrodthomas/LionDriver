# WP-T-01 Requirements and Traceability Data

| Field | Value |
|---|---|
| Work product | WP-T-01 Requirements and traceability data (machine-readable), consistency evidence |
| Standard reference | ISO 26262-8:2018 §6 (specification and management of safety requirements); ISO/SAE 21434:2021 §10; ASPICE 4.0 traceability and consistency BPs of SYS.2–SYS.5, SWE.1–SWE.6 (consistency evidence) |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All (FuSa, SOTIF, AI, CS) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` |

## 1. Purpose

This folder holds the machine-readable copy of the hazard log, safety goals, assumptions and (later) all requirements and their trace links, plus the checker that keeps them consistent. The procedure that governs it — requirement attributes, quality criteria, trace model, tagging convention and consistency checks — is [WP-P-06](../07-supporting/WP-P-06-requirements-management-traceability.md). This README describes the data as implemented and extends WP-P-06 where WP-P-06 does not yet cover an item kind (hazards, hazardous events, assumptions); those extensions are marked **[ext]** and are proposed for inclusion in WP-P-06 (OI-1).

The Markdown work products remain the documents that are reviewed and approved. The YAML files are copies that tools can check. Where both exist, the work product is the source of truth and the checker reports any difference (checks X1, X2).

## 2. Current content

| File | Content | Source | Items |
|---|---|---|---|
| `items/hazards.yaml` | Hazards H-01…H-06, H-08; hazardous events HE-01.1…HE-08.1 with S/E/C/ASIL | [WP-C-03](../02-concept/WP-C-03-hara.md) §4–§5 | 7 + 18 |
| `items/goals.yaml` | Safety goals SG-01…SG-07 with ASIL, safe state, FTTI, source HEs | [WP-C-03](../02-concept/WP-C-03-hara.md) §6 | 7 |
| `items/aou.yaml` | Assumptions of use AOU-01…AOU-11 | [WP-C-01](../02-concept/WP-C-01-item-definition.md) §7 | 11 |
| `tools/check_trace.py` | Consistency checker (§6) | — | — |

All items carry `status: proposed`: none of the source work products is approved. The HARA ratings are proposals pending the I3 confirmation review (CR-02).

Run the checker from the repository root:

```sh
python3 assurance/trace/tools/check_trace.py          # all checks incl. comparison with WP-C-01/WP-C-03
python3 assurance/trace/tools/check_trace.py --no-source-compare
```

Result at this baseline: `trace: 3 files, 43 items aou=11, hazard=7, hazardous-event=18, safety-goal=7` — `OK: all implemented checks passed`. The checker needs only the Python standard library. It uses PyYAML when available; PyYAML is **not** a direct dependency of LionDriver (`uv.lock` lists `pyyaml` only as an optional `autogen` extra of tinygrad), so a built-in parser for the YAML subset in §4.1 is used otherwise. Both paths were run and give the same result.

## 3. Trace data model

### 3.1 Artifact types

| Kind | ID prefix | Defined in | File (target layout, WP-P-06 §5.1) | Present |
|---|---|---|---|---|
| Hazard | `H-` | WP-C-03 | `items/hazards.yaml` | Yes |
| Hazardous event | `HE-` (see §7 note on `HS-`) | WP-C-03 | `items/hazards.yaml` | Yes |
| Safety goal | `SG-` | WP-C-03 | `items/goals.yaml` | Yes |
| Functional safety requirement | `FSR-<SG>.<nn>` | [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) | `items/fsr.yaml` | No (OI-2) |
| Technical safety requirement | `TSR-<nnn>` (blocks 1xx…8xx) | [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md), [WP-S-06](../03-system/WP-S-06-requirements-production-operation.md) | `items/tsr.yaml` | No |
| SW / HW safety requirement | `SWSR-<nnn>[a]`, `HWSR-<nnn>[a]` | [WP-W-02](../05-software/WP-W-02-software-safety-requirements.md), [WP-H-01](../04-hardware/WP-H-01-hardware-safety-requirements.md) | `items/swsr.yaml`, `items/hwsr.yaml` | No |
| SOTIF hazard | `SH-` | [WP-C-05](../02-concept/WP-C-05-sotif-hazard-identification.md) | `items/sotif.yaml` | No |
| Triggering condition / functional insufficiency | `TC-`, `FI-` | [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) | `items/sotif.yaml` | No |
| Functional modification | `FM-` (WP-C-05 usage) / `SOTIF-` (WP-P-06 usage), see §7 | [WP-C-07](../02-concept/WP-C-07-sotif-functional-modifications.md) | `items/sotif.yaml` | No |
| AI safety / dataset requirement | `AIR-`, `DSR-` | [WP-C-11](../02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md), [WP-W-10](../05-software/WP-W-10-ml-engineering.md) | `items/ai.yaml` | No |
| Threat scenario, CS goal, CS requirement | `TS-`, `CSG-`, `CSR-` | [WP-C-09](../02-concept/WP-C-09-tara.md), [WP-C-10](../02-concept/WP-C-10-cybersecurity-goals-and-concept.md) | `items/cs.yaml`, `items/goals.yaml` | No |
| System requirement (non-safety) | `SYS-` | [WP-S-01](../03-system/WP-S-01-system-requirements.md) | `items/sys.yaml` | No |
| Assumption of use | `AOU-` | WP-C-01, refined in WP-C-04 | `items/aou.yaml` (WP-P-06 name; the coordinator's request used `aous.yaml`) | Yes |
| Element (allocation target) | dotted name, e.g. `panda.safety.toyota` | WP-S-03, WP-W-03 | `elements.yaml` | No (WP-P-06 OI-4) |
| Test / verification link | test path | code and procedures | `links/verification.yaml` | No |

### 3.2 Link types

All links are stored on the child (or on the item that depends) as a list of IDs; reverse views are generated.

| Link | Stored as | From → to | Meaning |
|---|---|---|---|
| hazard event of | `parents` | HE → H | The hazardous event is a rated instance of the hazard |
| goal source | `parents` | SG → HE | The safety goal covers these hazardous events (ASIL = highest) |
| derives from | `parents` | FSR → SG; TSR → FSR; SWSR/HWSR → TSR | Requirement decomposition (WP-P-06 §4) |
| SOTIF cause | `parents` | TC/FI → SH; FM/SOTIF- → TC/FI | Insufficiency analysis and its treatment |
| AI | `parents` | AIR → FI; DSR → AIR | ML insufficiency treatment |
| CS | `parents` | CSG → TS; CSR → CSG | TARA-derived goals and requirements |
| CS ↔ safety | `protects` **[ext]** | CSG → SG | Attack that causes a safety hazard is covered by the CS goal |
| SOTIF ↔ HARA | `shares_event` **[ext]** | SH → HE/H | One hazard log (WP-M-01 §6) |
| assumption credited | `aou_dependency` **[ext]** | HE, SG, FSR, TSR → AOU | The rating or requirement depends on the assumption |
| allocation | `allocated_to` | requirement → element | WP-P-06 §2 |
| implementation | `@req` tag in code | code → requirement | WP-P-06 §6 |
| verification | `@req` tag in tests or `links/verification.yaml` | test → requirement | WP-P-06 §5.3, §6 |

The chains requested by the safety case are therefore: `H → HE → SG → FSR → TSR → SWSR/HWSR → code / test`; `SH → TC/FI → FM`; `TS → CSG → CSR`; `AOU ← HE / SG / FSR` (assumption credited by).

## 4. Field schema

### 4.1 YAML subset

Each file is a top-level list of flat mappings. To keep the files readable by the built-in parser and diff-friendly:

- every item starts with `- id: <ID>`; other keys are indented two spaces;
- values are one of: double-quoted single-line string (escape `"` as `\"`), bare word, integer, `true`/`false`, `null`, or a flow list of bare words `[A, B]`;
- no block scalars, no nested mappings, no inline comments after values; full-line `#` comments allowed.

Requirement items (FSR, TSR, SWSR, …) use exactly the attributes and keys of [WP-P-06 §2](../07-supporting/WP-P-06-requirements-management-traceability.md#2-requirement-attributes). WP-P-06 §5.2 shows `text`, `rationale` and `implemented_in` as YAML block scalars and block lists; in this folder they are written as quoted single-line strings and flow lists (e.g. `implemented_in: [opendbc_repo/opendbc/safety/modes/toyota.h:173, opendbc_repo/opendbc/safety/lateral.h:60-151]`). The built-in parser splits flow lists on commas, so list elements must not contain commas.

Keys common to all kinds: `id`, `kind`, `status` (WP-P-06 enum), `source` (work product ID), optional `notes`.

### 4.2 Hazard and hazardous event **[ext]**

| Key | Kind | Content |
|---|---|---|
| `title` | hazard | Hazard name as in WP-C-03 §4 |
| `functions` | hazard | Item functions (F-nn) whose malfunction leads to it |
| `parents` | hazardous-event | `[H-nn]` |
| `situation`, `effect` | hazardous-event | Verbatim from WP-C-03 §5 |
| `s`, `e`, `c` | hazardous-event | Integers 0–3 / 0–4 / 0–3 |
| `asil` | hazardous-event | `QM`, `A`…`D`; must equal the risk graph of S+E+C (R1) |
| `aou_flag` | hazardous-event | `true` where WP-C-03 marks the rating ⚠ |
| `aou_dependency` | hazardous-event | AOUs the controllability rating credits |
| `asil_if_aou_fails` | hazardous-event | Alternative ASIL stated in WP-C-03, else `null` |
| `sg_exempt_reason` | hazardous-event | Required if no SG lists this HE (e.g. QM) |

### 4.3 Safety goal

| Key | Content |
|---|---|
| `text` | Verbatim goal statement |
| `type` | `constraint` |
| `asil`, `asil_if_aou_fails`, `aou_dependency` | As WP-C-03 §6 (e.g. SG-01: C, D if AOU-01/02 fail) |
| `parents` | Source HEs |
| `safe_state` | Verbatim |
| `ftti_ms`, `ftti_text` | Preliminary FTTI in ms (`null` for "Continuous") and the original text |

### 4.4 Assumption of use **[ext]**

| Key | Content |
|---|---|
| `text`, `credited_in`, `verification_approach` | Verbatim from WP-C-01 §7 |
| `aou_status` | WP-C-01 status column (`Unverified`, `Assumption (SOTIF-managed)`, `Not started`, `Partially (calibration check exists)`, `Design constraint`). Kept separate from `status`, which is the lifecycle status of the item itself |

## 5. How tests and code reference requirements

As specified in [WP-P-06 §6](../07-supporting/WP-P-06-requirements-management-traceability.md#6-how-code-and-tests-reference-requirements), summarised:

| Artefact | Convention |
|---|---|
| Python test written for LionDriver | `@req <ID>` tag in the test method docstring, one ID per tag |
| Inherited shared test (e.g. `opendbc_repo/opendbc/safety/tests/common.py` used by `test_toyota.py`) | Entry in `links/verification.yaml` with the concrete class path, level and environment |
| C safety code (`opendbc/safety`, `panda/board`) | `// @req <ID>` on the line before the implementing statement (in the LionDriver forks, after D-01) |
| Python product code | `# @req <ID>` |
| HIL / vehicle procedure | `Requirements:` header line |

Only IDs of kind requirement (FSR, TSR, SWSR, HWSR, CSR, AIR, SYS, FM/SOTIF-) may be tagged; tagging an SG or H directly is not allowed (verification is against requirements, SG achievement is argued in [WP-K-01](../10-safety-case/WP-K-01-safety-case.md)).

## 6. Consistency checks

| Check | Description | Source | Implemented |
|---|---|---|---|
| K1 | Files parse; mandatory keys per kind present; status in enum | WP-P-06 §7 | Yes (key list per kind; JSON Schema file not yet written) |
| K2 | IDs unique and match the pattern | WP-P-06 §7 | Yes (uniqueness within the current baseline; "no ID removed vs. previous baseline" not yet) |
| K3 | `parents`, `aou_dependency` resolve, and to the right kind | WP-P-06 §7 | Yes (`allocated_to` pending `elements.yaml`) |
| K4 | Every SG ≥ 1 FSR; every FSR ≥ 1 TSR; every SW/HW-allocated TSR ≥ 1 SWSR/HWSR | WP-P-06 §7 | No (no FSR/TSR data yet) |
| K5 | Child ASIL ≥ parent ASIL unless decomposition notation | WP-P-06 §7 | No |
| K6 | Every `@req` tag refers to an existing, non-withdrawn ID | WP-P-06 §7 | No |
| K7 | Every `verified` TSR/SWSR/HWSR has a passing linked test at the baseline | WP-P-06 §7 | No |
| K8 | Every SWSR with ASIL ≥ A has an implementation tag | WP-P-06 §7 | No |
| K9 | HIL / vehicle-test requirements have a linked procedure | WP-P-06 §7 | No |
| K10 | Every SR-A source file has ≥ 1 `@req` tag | WP-P-06 §7 | No |
| K11 | Requirement tables in Markdown WPs match YAML text | WP-P-06 §7 | Partly: X1, X2 below do this for HARA and AoUs |
| K12 | Every hazardous event linked to an SG or SH, or exempt with reason | WP-P-06 §7 | Yes (SG link or `sg_exempt_reason`; SH link pending) |
| R1 **[ext]** | HE ASIL = risk graph of S, E, C (WP-C-03 §2 sum rule) | WP-C-03 §2 | Yes |
| R2 **[ext]** | SG ASIL = highest ASIL of its source HEs | WP-C-03 §2 step 5 | Yes |
| R3 **[ext]** | `asil_if_aou_fails` ≥ `asil` and only with `aou_dependency` | — | Yes |
| R4 **[ext]** | Every hazard has ≥ 1 hazardous event | — | Yes |
| X1 **[ext]** | HE situation/effect/S/E/C/ASIL/⚠ and SG text/ASIL/alternative ASIL/source HEs/safe state/FTTI match WP-C-03 tables | — | Yes |
| X2 **[ext]** | AOU text, credited-in, verification approach and status match WP-C-01 table | — | Yes |
| Planned | Every AOU with status `Unverified` that is credited by an SG is listed as an open assumption in WP-K-01 §5 | WP-K-01 | No |
| Planned | Every GAP referenced as `parents` exists in the gap assessment | gap assessment | No |
| Planned | Requirement IDs fall in the allocated TSR block ranges (1xx…8xx) | shared ID allocation | No |

CI integration (run on PRs touching `assurance/trace/**`, WP-C-01, WP-C-03 or SR-A/SR-Q paths) is WP-P-06 OI-2.

## 7. Inconsistencies noted while building the data

| # | Inconsistency | Handling here | Owner |
|---|---|---|---|
| 1 | [`assurance/README.md`](../README.md) and WP-P-06 use `HS-<nn>` for hazardous events; WP-C-03 uses `HE-nn.n` | Data follows WP-C-03 (`HE-`); checker accepts both prefixes | Align README / WP-P-06 or WP-C-03 |
| 2 | WP-P-06 §5.1 places functional modifications under the `SOTIF-` prefix; WP-C-05 refers to them as `FM-01`…`FM-06` | Both prefixes accepted by the checker | Align WP-P-06 / WP-C-05 / WP-C-07 |
| 3 | WP-C-03 defines no H-07 (H-06 → H-08) | Recorded as a comment in `hazards.yaml`; no H-07 created | WP-C-03 |
| 4 | WP-C-03 marks HE-01.3 and HE-01.4 ⚠ but states no alternative ASIL | `asil_if_aou_fails: null`, AoUs taken from the H-01 group | WP-C-03 |
| 5 | WP-C-03 HE-04.2 credits AOU-10 in its rationale but is not ⚠-flagged | `aou_flag: false`, `aou_dependency: [AOU-10]` | WP-C-03 |
| 6 | The requested file names (`hazards.yaml`, `safety_goals.yaml`, `aous.yaml` at the folder root, checker at the root) differ from WP-P-06 §5.1 (`items/hazards.yaml`, `items/goals.yaml`, `items/aou.yaml`, `tools/check_trace.py`) | WP-P-06 layout used | — |

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Add the [ext] kinds and keys (§3.2, §4.2, §4.4) and checks R1–R4, X1–X2 to WP-P-06 | G1 |
| OI-2 | Add `items/fsr.yaml` from WP-C-04 (FSR-01.01…FSR-07.05) and extend X-checks to the FSC tables | G1 |
| OI-3 | Write `schema/item.schema.json` (WP-P-06 §5.1); validate with the standard library or add a pinned dependency | G1 |
| OI-4 | Add the CI job (WP-P-06 OI-2) | G1 |
| OI-5 | Add `sotif.yaml` (SH-01…SH-13 from WP-C-05) with `shares_event` links | G1 |
| OI-6 | Implement K2 "no ID removed" by comparing with the previous baseline tag | G2 |
