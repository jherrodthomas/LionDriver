# Item Definition rev 0.1 — Automated Pre-check

| | |
|---|---|
| **Work product** | `docs/safety/item-definition.md` rev 0.1 (LD-ITEM-001), exported with `tools/safety/export_item_xlsx.py` |
| **Tool** | `item-def-checklist-reviewer`, jherrodthomas/automotive-skills-suite @ `026bb63` |
| **Date** | 2026-10-10 |
| **Performed by** | Claude (AI assistant) |
| **Nature** | Automated pre-check. **Not** the ISO 26262-2 confirmation review (IOI-006). |

## How to reproduce

```
tools/safety/export_item_xlsx.py        # -> docs/safety/exports/item-definition.xlsx (git-ignored)
python3 <reviewer>/scripts/generate_checklist.py docs/safety/exports/item-definition.xlsx docs/safety/exports/item-definition-review-checklist.xlsx
```

The exporter reads the markdown tables of LD-ITEM-001, `item/variants.yaml` and the generated vehicle catalog. A test checks that the exported functions match System FMEA F1–F8, the modes match FSC OM-01…OM-08, and the catalog has 334 vehicles.

The probe read: 8 functions, 15 non-functional requirements, the boundary (5 in item, 3 out, 2 adjacent), 7 interfaces, 8 modes, 8 allocations, 10 assumptions, 16 references.

## Gaps closed before the run

Mapping the item definition onto the reviewer's layout showed content ISO 26262-3 clause 5 expects but rev 0.1 did not yet have. It was added to the item definition itself, not only the export.

| Gap | Added |
|---|---|
| Interfaces without counterpart or integrity measures | §A.4 table with ID, counterpart, data and BL-001 integrity measures (IF-01…IF-07) |
| Operating modes without entry/exit conditions (referenced the FSC only) | §A.5 table with entry, exit and safety relevance |
| No function allocation to HW/SW/actuators | Function allocation table in §A.3 |
| Assumptions limited to the vehicle | §A.7 adds driver (DA), market (MA) and lifecycle (LA) assumptions |
| No performance limits | §A.6 PF-01…PF-06 (lateral acceleration and jerk, longitudinal acceleration, excessive actuation, soft-disable window, DM escalation), each sourced from code |
| Distinguishing notes did not distinguish | §1.3 related items: stock TSS2, upstream openpilot, other forks, platform siblings |
| Stale cross-reference | §1.2 updated to HARA rev 0.3 / FSC rev 0.2 / DFA rev 0.3 |

## Result

| Tab | Checks | FC | PC | NO | Pending (human) |
|---|---|---|---|---|---|
| Confirmation Review | 14 | 7 | 0 | 0 | 7 |
| Item Definition Assessment | 10 | 10 | 0 | 0 | 0 |
| Verification Assessment | 3 | 0 | 0 | 0 | 3 |

## Passes not taken at face value

The reviewer auto-rates most substantive checks from counts.

- **IDA-7 (assumptions cover vehicle, driver, market, lifecycle).** Rated FC from the count of 10 rows. The categories are in fact present (VA, DA, MA, LA), but the tool doesn't check categories.
- **IDA-5 (modes cover normal, degraded, fault).** Rated FC from the count of 8 modes. Degraded behavior is covered by overriding and soft disabling. There is no explicit *fault* mode for a persistent panda fault (NO_OUTPUT after a safety violation); it is handled as disabled + WD-06. Reviewer to judge.
- **IDA-10 (HARA-ready).** True in the sense that HARA rev 0.3 already uses this item definition. The HARA covers AC-001 only (§1.2).
- **IDA-3 (NFRs captured).** Now includes performance limits PF-01…PF-06. Availability and maintainability requirements are not stated; none are claimed.

## Pending — proposed disposition for the human reviewer

| # | Topic | Proposed |
|---|---|---|
| CR-2 | Template version | NA: the project format is the markdown item definition; the xlsx is a generated view |
| CR-4a | Title covers scope | FC: title names the platform, VF-001 and AC-001 |
| CR-4d | Change history | PC: one entry (rev 0.1) in Document Control; history will accumulate per revision |
| CR-5 | Current revision | FC: generated from the committed markdown |
| CR-6 | Configuration management | FC: git, baseline BL-001; catalog regenerated and checked by test |
| CR-7 | Header/footer | NA for the xlsx view |
| CR-8 | Table of contents | PC: the markdown has a section structure but no TOC; add one at rev 0.2 |
| VA-1…3 | Traceability, design, test plan | External: function → FSR traceability exists through HARA/FSC; no test plan yet |

## Observations on the tool (continuing the list in the HARA and FSC pre-checks)

10. **item-def-checklist-reviewer** reads the NFR, interface, mode, allocation, assumption and reference tabs by fixed column position from row 2, so the header row of a sheet with a title row would be counted as an entry. The export puts headers in row 1 to avoid this.
11. **item-def-checklist-reviewer** recognizes the title only from a label containing "item", "definition" and "title".
12. **item-def-checklist-reviewer** rates "change history documented" as not verifiable even when the Document Control tab has rows.
