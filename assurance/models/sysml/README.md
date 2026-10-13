# SysML v2 architecture model

| Field | Value |
|---|---|
| What | The LD-SDA architecture as a SysML v2 model: elements, integrity, ports, interfaces, cereal services, safety mechanisms, and the views drawn from them |
| Status | Draft, AI-assisted (Claude), not reviewed. Decisions SY-01 to SY-06 are **proposed**, not taken |
| Documents of record | [WP-C-01](../../02-concept/WP-C-01-item-definition.md) §3, [WP-S-03](../../03-system/WP-S-03-technical-safety-concept-architecture.md) §3, §6, §8, §9, [WP-W-03](../../05-software/WP-W-03-software-architecture.md) §3.1, §4.1. The model is a checked copy of them (§4) |
| Tool classification | [WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md) TL-26 (OMG pilot implementation), TL-27 (in-house reader, checks, renderer); TCL1, no verification credit |
| Explorer | [`generated/explorer.html`](generated/explorer.html): open locally in a browser |

The model is description, not code generation: LionDriver does not use model-based development for production code ([WP-W-01](../../05-software/WP-W-01-software-development-environment-guidelines.md)). Nothing here is verification evidence. A figure or check result in this folder may support a review, but it does not replace one.

## 1. Why a model

The architecture is already written down, in tables in five work products and in hand-drawn figures. Three things are missing that a model provides:

1. **One set of element names.** The 351 `allocated_to` fields in [`trace/items`](../../trace/items) use 161 different strings in four vocabularies (`E-03`, `P-SW`, `U-SAF-TOY`, `host.selfdrived`). [WP-P-06](../../07-supporting/WP-P-06-requirements-management-traceability.md) OI-4 asks for an element catalogue. The model is that catalogue, and §5 measures how much of the allocation data it already resolves.
2. **Consistency by construction.** WP-S-03 says of Figure 3-2 "change it together with §3.1, §3.3, §5 and §6". Here a table and the model are compared on every pull request (§4), and every figure is regenerated from the model, so a figure cannot drift from the tables it shows.
3. **A semi-formal notation** for architectural design. ISO 26262-6:2018 Table 2 highly recommends semi-formal notations for the software architecture from ASIL B, and ASPICE SYS.3 and SWE.2 ask for static and dynamic aspects with their interfaces. Check the clause and table numbers against your licensed copy.

## 2. Decisions (proposed)

| ID | Question | Proposal | Consequence |
|---|---|---|---|
| SY-01 | Which notation? | **SysML v2 textual notation** (OMG SysML 2.0, 2025). Plain text files reviewed in pull requests like code | No GUI tool is needed to read or change the model; diffs are reviewable |
| SY-02 | Which tool says the model is valid SysML v2? | The **OMG pilot implementation**, version 0.62.0, pinned by SHA-256 ([`tools/pilot/`](tools/pilot)), run in CI | Conformance is checked by the reference implementation, not by in-house code (WP-P-07 TL-26) |
| SY-03 | How are figures drawn? | **In-house renderer** ([`tools/render_views.py`](tools/render_views.py)) in the style of the existing work-product figures. The model says what is drawn; [`views/layout.toml`](views/layout.toml) says only where | The pilot's PlantUML rendering is not used. A layout entry that names an element the model does not have fails the build |
| SY-04 | Model or Markdown, which is the source? | For now the **work products** stay the documents of record and the model is a checked copy (§4), as for the YAML in `trace/` | Two places to edit until SY-05 is decided |
| SY-05 | Should the architecture tables be generated from the model later? | Open. Proposal: generate WP-S-03 §3.1, §3.3 and §6 and WP-W-03 §3.1 from the model once it has been reviewed (OI-5) | Removes the double edit; makes the model the record |
| SY-06 | Should generated views replace the hand-drawn figures? | Open. Candidates: WP-S-03 Figure 3-2 → V-03; WP-C-01 Figure 3-1 and the element-hierarchy figures of WP-S-03, WP-W-03 and WP-H-02 → V-02 (OI-6) | One drawing per fact |

## 3. Contents

| Path | Content |
|---|---|
| [`model/LionDriverLibrary.sysml`](model/LionDriverLibrary.sysml) | Integrity enumeration (WP-S-02 §2.1 notation), element classes, port, interface and connection definitions, metadata (`Safety`, `Source`, `Unit`, `InterfaceId`, `FfiClaim`), view definitions |
| [`model/Mechanisms.sysml`](model/Mechanisms.sysml) | SM-01 to SM-43 as `action` usages of `SafetyMechanism` with coverage, DC target and TSRs (WP-S-03 §6) |
| [`model/Architecture.sysml`](model/Architecture.sysml) | E-01 to E-05 with their parts and software units, allocation of software to hardware, interfaces IF-01 to IF-10, the 23 cereal services of WP-S-03 §9 between modelled processes, `perform` statements, the vehicle context and the allocation short forms `P-SW`, `P-HW`, `SoC`, `HAR` as aliases |
| [`model/Views.sysml`](model/Views.sysml) | Views V-01 to V-04: what each exposes and how it is rendered |
| [`views/layout.toml`](views/layout.toml) | Placement only: boxes, grids, route adjustments, display names |
| [`tools/sysml_lite.py`](tools/sysml_lite.py) | Reader for the subset of the textual notation the model uses; builds the instance tree. Refuses any other construct with its line number |
| [`tools/check_model.py`](tools/check_model.py) | Checks M1 to M8 (§4) and the allocation-resolution report |
| [`tools/render_views.py`](tools/render_views.py), [`tools/svgkit.py`](tools/svgkit.py) | View renderer and drawing kit (palette, measured Inter metrics, orthogonal routing) |
| [`tools/explorer.py`](tools/explorer.py), [`tools/explorer_assets/`](tools/explorer_assets) | Builds the interactive explorer |
| [`tools/pilot/`](tools/pilot) | Pinned download and validation with the OMG pilot implementation |
| [`tools/test_sysml.py`](tools/test_sysml.py) | Tests of the reader, checks, renderer and explorer |
| [`generated/`](generated) | Figures, explorer and the allocation-resolution report. Never edited by hand |

## 4. Checks

| Check | What it compares |
|---|---|
| M1 | Elements and integrity of WP-S-03 §3.1 |
| M2 | Firmware elements of WP-W-03 §3.1: name, unit, build scope, integrity, in both directions |
| M3 | Host components of WP-W-03 §4.1: name and integrity, in both directions |
| M4 | Interfaces of WP-S-03 §3.3: every IF exists; each item-side element in the "Between" column is an endpoint of one of its connections |
| M5 | Mechanisms of WP-S-03 §6: same set, same performing elements, same TSRs |
| M6 | Cereal services of WP-S-03 §9 between modelled processes, in both directions |
| M7 | Every element inside the item has an integrity; any connection between a QM and an ASIL element inside the item declares the FFI claims of WP-S-03 §7 it crosses (`@FfiClaim`) |
| M8 | [`generated/allocation-resolution.md`](generated/allocation-resolution.md) is up to date |

Integrity in a table cell is read as the highest level it names (`B (PCS restore), B‡ (blocking)` is B‡). Run from this folder:

```sh
python3 tools/check_model.py           # M1-M8
python3 tools/render_views.py --check  # figures match the model
python3 tools/explorer.py --check      # explorer matches the model
python3 tools/test_sysml.py
tools/pilot/validate.sh                # SysML v2 conformance (Java 17+, python3 with zstandard)
```

All of them run in CI (`.github/workflows/assurance.yaml`, job "sysml model"). Result at this baseline: M1 to M8 pass; the pilot reports 0 errors and 0 warnings for the four files.

Writing the model found one difference worth recording. WP-S-03 §3.3 defines IF-05/06 as camera images reaching E-01/E-02 and IF-07 as starting in E-01, while WP-C-01 §3.4 defines the same IDs at the item boundary (road environment and driver to the cameras and display). The model now carries both hops under one identifier; the work products should say that the identifier covers the whole path (OI-7).

## 5. Allocation resolution

[`generated/allocation-resolution.md`](generated/allocation-resolution.md) matches every `allocated_to` value against the model. At this baseline:

| Requirement kind | Allocations | Resolved | Not resolved |
|---|---|---|---|
| FSR | 54 | 53 | 1 |
| TSR | 118 | 118 | 0 |
| SWSR | 134 | 124 | 10 |
| HWSR | 45 | 3 | 42 |

HWSRs are allocated to chip-level parts (RAMECC, PVD, relay driver, codec) that no catalogue defines yet. Modelling the parts of [WP-H-02](../../04-hardware/WP-H-02-hardware-design.md) is the next increment (OI-1). The report is informational and does not fail CI. Because CI asks for it to be regenerated whenever an allocation or the model changes, a new unresolved allocation is visible in review.

## 6. Views

Every figure below is generated. The explorer shows the same four views with the model tree and an inspector (interfaces, services, mechanisms, allocated requirements per element).

**V-01 Item context:** the item boundary, components E-01 to E-05 and the elements outside the item.

![V-01: item context generated from the SysML model](generated/fig-sysml-v01-item-context.svg)

**V-03 Technical safety architecture:** the WP-S-03 Figure 3-2 content drawn from the model.

![V-03: technical safety architecture generated from the SysML model](generated/fig-sysml-v03-system-interconnection.svg)

**V-02 Element hierarchy:** every part and software unit with integrity, unit and build scope.

![V-02: element hierarchy generated from the SysML model](generated/fig-sysml-v02-element-hierarchy.svg)

**V-04 Safety mechanism allocation:** SM-01 to SM-43 against the elements that perform them.

![V-04: safety mechanism allocation generated from the SysML model](generated/fig-sysml-v04-mechanism-allocation.svg)

## 7. Changing the model

1. Change the work product and the `.sysml` file in the same pull request.
2. Run the commands of §4; regenerate with `check_model.py --write`, `render_views.py` and `explorer.py`.
3. For a new construct the reader refuses, extend `sysml_lite.py` and its tests; the pilot decides whether the construct is valid SysML v2.

Keep to SysML v2 words for names: `item`, `view`, `via`, `state`, `flow` and similar are keywords and fail the pilot parse.

## 8. Open items

| ID | Item |
|---|---|
| OI-1 | Model the hardware parts of WP-H-02 (RAMECC, PVD, CSS, relay driver, codec, transceivers) so that HWSR allocations resolve |
| OI-2 | Model the firmware interfaces SI-01 to SI-16 of WP-W-03 §3.3 and add a firmware interconnection view |
| OI-3 | Model behaviour: the state machines in [`05-software/state-machines/`](../../05-software/state-machines) as SysML `state def`, and the start-up sequence of WP-S-03 §4.1 |
| OI-4 | Link requirements to the model with `satisfy` once the allocation vocabulary is settled (WP-P-06 OI-4) |
| OI-5 | Decide SY-05 (generate the architecture tables from the model) |
| OI-6 | Decide SY-06 (replace hand-drawn figures with generated views) |
| OI-7 | State in WP-C-01 §3.4 and WP-S-03 §3.3 that IF-05, IF-06 and IF-07 cover the path from the environment or driver to E-01/E-02 |
| OI-8 | Review the model (I1) and classify TL-26 and TL-27 in a confirmation review |
