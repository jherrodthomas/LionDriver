# Living Safety Case records

| Field | Value |
|---|---|
| Work product | Living Safety Case data (machine-readable copy of [WP-K-01](../10-safety-case/WP-K-01-safety-case.md)), validator and dashboard generator |
| Standard reference | ISO 26262-2:2018 §6.4.8 (safety case); ISO 26262-8:2018 §10 (documentation management); UL 4600 principles (living safety case, defeaters) |
| Version | 0.1 |
| Status | Draft |
| Author | Assurance team |
| Reviewer(s) | TBD (I1) |
| Baseline | `BL-001` (`8b8c6ae`) |

## 1. Purpose

This folder holds the structured records behind the README's Living Safety Case dashboard: the claims, arguments, evidence, defeaters, open actions, vehicle configurations, baselines and reviews of the LionDriver safety case. A validator checks them, and a generator turns them into the dashboard, so every published figure comes from a record that can be read, reviewed and diffed.

[WP-K-01](../10-safety-case/WP-K-01-safety-case.md) stays the reviewed document. The records are a copy of it, and the validator fails if the two disagree on the evidence, defeater or open-item tables (check X3).

> **Assurance status represents recorded engineering evidence and review state. It does not constitute certification or approval for unsupervised operation.**

## 2. Layout

| Folder | Kind | IDs | Content at `BL-001` |
|---|---|---|---|
| [`claims/`](claims/) | `claim` | `G0`, `G1.1.4`, … (GSN goals) | 36 claims from WP-K-01 §3–§4, one file per top-level branch |
| [`arguments/`](arguments/) | `argument` | `S0`, `S1.1`, … (GSN strategies) | 6 strategies |
| [`evidence/`](evidence/) | `evidence` | `Sn-01`, … (GSN solutions) | 49 evidence items from WP-K-01 §6 |
| [`defeaters/`](defeaters/) | `defeater` | `DF-01`, … | 41 open defeaters from WP-K-01 §7 |
| [`actions/`](actions/) | `action` | `ACT-001`, … | Open items of WP-K-01 §10 |
| [`configurations/`](configurations/) | `configuration` | `CFG-001`, … | One record per evaluated vehicle configuration |
| [`baselines/`](baselines/) | `baseline` | `BL-001`, … | Engineering baselines the records refer to |
| [`reviews/`](reviews/reviews.yaml) | `review` | `REV-001`, … | Review records; none at `BL-001` |
| [`schema/case-schema.json`](schema/case-schema.json) | — | — | Fields, types, enumerations and reference rules per kind |
| [`tools/`](tools/) | — | — | Validator, generator and their self-tests |
| `status.json` | — | — | Generated summary (do not edit) |

Hazards, hazardous events, safety goals and assumptions of use are not duplicated here. Records reference them by ID, and the validator resolves those IDs against [`assurance/trace/items/`](../trace/items/), the machine-readable hazard log ([WP-T-01](../trace/README.md)). Requirements (FSR, TSR, …) will be referenced the same way once they are added to `trace/`.

## 3. Record format

Files use the restricted YAML subset of [WP-T-01 §4.1](../trace/README.md#41-yaml-subset): a top-level list of flat mappings; values are quoted single-line strings, bare words, `null` or flow lists of bare identifiers. Dates and git revisions are always quoted. The validator always uses the built-in subset parser, never PyYAML, so the result does not depend on what is installed.

Fields shared by most kinds:

| Field | Meaning |
|---|---|
| `id`, `kind` | Stable identifier and object type. IDs are never reused |
| `title`, `description` | Short name and full statement |
| `lifecycle_status` | Where the object is in its own lifecycle (per kind, see the schema) |
| `baseline`, `configuration` | The engineering baseline and vehicle configuration the object applies to |
| `related_hazards`, `related_requirements`, `related_assumptions`, `related_claims` | Links to the hazard log, requirements, assumptions of use and claims |
| `evidence_refs`, `defeaters` | Evidence supporting a claim; counter-evidence currently undermining it |
| `review_state`, `reviewer`, `review_date`, `review_ref` | Review state and the review record that set it |
| `source`, `source_revision` | Work product the record copies, and the git revision it describes |

## 4. Rules

The validator ([`tools/validate.py`](tools/validate.py)) enforces these. CI runs it on every pull request that touches the records.

| Check | Rule |
|---|---|
| V1 | Every record sits in the folder of its kind, has every schema field and no others |
| V2 | IDs match their pattern and are unique; field types and enumerations are valid |
| V3 | Every reference resolves to a record, or trace item, of the right kind |
| V4 | Links agree in both directions: claim ↔ evidence, claim ↔ defeater, claim ↔ argument |
| V5 | Every evidence location exists in the repository |
| V6 | **Acceptance rules**, below |
| V8 | Claims form one tree under a single top-level claim |
| X3 | The evidence, defeater and open-item tables of WP-K-01 match the records |

Acceptance rules (V6):

- `review_state: accepted` needs `reviewer`, `review_date` and a `review_ref` pointing to an accepted review record that lists the object, at the same baseline.
- `evidence_status: available` means performed and approved (the WP-K-01 §6 rule), so it needs `review_state: accepted`. Missing evidence cannot be accepted.
- A claim can be `accepted` only if its own review is accepted, every evidence item it cites is available and accepted, every sub-claim is accepted, and no defeater attached to it is open.
- A configuration can be `assurance-supported` only if it is accepted and at least one accepted claim applies to it.

What never accepts anything: a passing CI run, a passing test, the existence of a file, or an AI-generated review. These can be inputs to a review; only a review record written by the named reviewer, at the independence level the [confirmation measures plan](../01-management/WP-M-06-confirmation-measures-plan.md) requires, changes a review state.

A change to safety-relevant code must come with an impact analysis ([WP-M-12](../01-management/WP-M-12-impact-analysis.md)) that names the affected records. Accepted records affected by a change go back to `not-reviewed` until they are reviewed again.

## 5. Dashboard figures

[`tools/generate_dashboard.py`](tools/generate_dashboard.py) computes every figure from the records and writes `status.json`, the three SVG cards under [`docs/assets/liondriver/assurance/`](../../docs/assets/liondriver/assurance/) and the text table between the `assurance-summary` markers in the [README](../../README.md). `--check` fails if any of them is out of date. The output is deterministic: it carries a digest of the record files instead of a timestamp, so it changes only when the records change.

| Figure | Definition |
|---|---|
| Assurance state | `Evidence Supported` if any configuration is assurance-supported; `Under Review` if any review record exists or any object is in review; otherwise `Development` |
| Registered safety claims | Number of claim records |
| Claims with accepted supporting evidence | Claims that cite evidence and whose evidence is all accepted |
| Registered evidence items | Number of evidence records, split by `evidence_status` |
| Evidence requiring review | Evidence with drafted or complete content (`partial` or `available`) that is not accepted |
| Open assurance actions | Action records with `lifecycle_status: open` |
| Open defeaters | Defeater records with `lifecycle_status: open` |
| Evaluated configurations | Configurations classified `liondriver-evaluated` or `assurance-supported` |
| Assurance-supported configurations | Configurations classified `assurance-supported` (see V6) |
| Upstream compatible | The model count stated in the main table of [`docs/CARS.md`](../../docs/CARS.md), and the number of vehicle makes in it |

Lifecycle-area status, from the evidence items assigned to the area (`lifecycle_area`):

| Status | Condition |
|---|---|
| Blocked | A claim citing evidence in the area has `lifecycle_status: blocked` |
| Not Started | Every evidence item in the area is `missing` |
| Accepted for Defined Baseline | Every evidence item in the area is `available` and accepted |
| Review Required | No evidence item is missing, and every item not yet accepted is in review |
| In Progress | Anything else |

## 6. Updating the records

```sh
python3 assurance/case/tools/validate.py              # check the records
python3 assurance/case/tools/generate_dashboard.py    # regenerate status.json, the SVG cards and the README table
python3 assurance/case/tools/test_case.py             # self-tests of the validator rules
```

When WP-K-01 changes, update the matching records in the same pull request; check X3 fails otherwise.

## 7. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Add the requirement IDs (FSR, TSR) to `related_requirements` once `trace/items/fsr.yaml` and `tsr.yaml` exist (WP-T-01 OI-2) | G2 |
| OI-2 | Add a configuration-independent claim layer once a second configuration is evaluated, so platform evidence can be reused across configurations | G4 |
| OI-3 | Generate the WP-K-01 GSN diagrams from these records (WP-K-01 OI-4) | G2 |
