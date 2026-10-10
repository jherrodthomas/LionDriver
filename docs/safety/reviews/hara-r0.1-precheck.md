# HARA rev 0.1 — Automated Pre-check

| | |
|---|---|
| **Work product** | `docs/safety/analyses/hara.yaml` rev 0.1 (LD-HARA-001), exported with `tools/safety/export_hara_xlsx.py` |
| **Tool** | `hara-checklist-reviewer`, jherrodthomas/automotive-skills-suite @ `026bb63` |
| **Date** | 2026-10-10 |
| **Performed by** | Claude (AI assistant) |
| **Nature** | Automated pre-check. **Not** the confirmation review required by ISO 26262-2 (independence I3); that remains OI-007. |

## How to reproduce

```
tools/safety/export_hara_xlsx.py                         # -> docs/safety/exports/hara.xlsx (git-ignored)
python3 <reviewer>/scripts/generate_checklist.py docs/safety/exports/hara.xlsx docs/safety/exports/hara-review-checklist.xlsx
```

The exporter renders the YAML in hara-builder's tab layout without adding or changing ratings, so the reviewer sees exactly the HARA under review. The reviewer probe read all content (8 functions, 12 situations, 18 hazardous events, 10 safety goals, 1 revision-history row).

## Result

| Tab | Checks | FC | PC | NO | NA | Pending (human) |
|---|---|---|---|---|---|---|
| Confirmation Review (document quality) | 14 | 9 | 0 | 0 | 0 | 5 |
| Functional Safety Assessment (ISO 26262-3) | 24 | 14 | 2 | 0 | 2 | 6 |
| Verification Assessment (ISO 26262-8 cl. 9) | 44 | 2 | 2 | 0 | 1 | 39 |

## Findings and disposition

| # | Reviewer finding | Disposition |
|---|---|---|
| FSA-6 | Only 7 of 14 malfunction guide words used | **Accepted.** Hazards were derived from System FMEA end effects, not a systematic function × guide-word pass. → OI-009 |
| FSA-8, VA-33, VA-33d | 18 rows vs ~588 for a full function × malfunction × situation Cartesian | **Accepted in part.** A full Cartesian is not required, but ISO 26262-3 6.4.2 needs all *relevant* combinations considered, and rev 0.1 does not record why unrated hazard × situation pairs are dominated or irrelevant. → OI-010 |
| — | Weather / road surface not differentiated (not flagged by the reviewer) | **Raised by this pre-check.** The worksheet says so explicitly; the reviewer counted 12 situations as "adequate" without noticing. → OI-011 |

## Passes not taken at face value

These were auto-rated FC on thin evidence. They are kept as **reviewer to verify**:

- **VA-33e (ASIL consistency):** the finding cites "formula-driven ASIL (INDEX/MATCH)", which this export does not use. The conclusion still holds: `fmea_lint.py` recomputes every ASIL against ISO 26262-3 Table 4 and the tests pin the full table.
- **FSA-21 (combined SG takes the highest ASIL):** reviewer says "presumed". `fmea_lint.py` enforces this.
- **FSA-19, VA-33a (situation granularity / completeness):** judged only from the row count (12). See OI-011.
- **CR-10 (all sections complete):** true for populated cells. FTTI is TBD for every goal (OI-004).

## Pending items — proposed disposition for the human reviewer

| # | Topic | Proposed |
|---|---|---|
| FSA-1 | Item definition available | **NO**: no formal item definition yet (fmea-plan.md §2). Stand-in is the System FMEA scope and HA-001…HA-006. |
| FSA-9 | All consequences identified | PC: consequences recorded per HE; secondary consequences (e.g. multi-vehicle) not analyzed. |
| FSA-10 | Measures outside ISO 26262 highlighted | PC: driver (HA-001) and EPS/powertrain limits (OI-001/OI-002) are identified but not yet credited or specified. |
| FSA-14 | Exposure not based on fleet penetration | FC: HA-005 states no fleet data used; E rated on situation share. |
| FSA-17 | Unavailability hazards justified | FC: loss of function *with* warning is treated as non-hazardous (RT-1 S 8); loss *without* warning is HZ-004 / HZ-012. |
| CR-6 | Configuration management | FC: YAML under git, baseline BL-001, generated exports git-ignored. |
| CR-7 | Header/footer | NA for xlsx export. |
| VA-24…32 | Verification plan / spec / report | Not yet produced. Out of scope for rev 0.1. |

## Defects found in the skills (jherrodthomas/automotive-skills-suite)

1. **hara-builder exposure anchors are off by one class.** `references/exposure.md` and `EXPOSURE_TABLE` in `generate_hara.py` use E1 < 1%, E2 1–10%, E3 10–50%, E4 > 50%. ISO 26262-3:2018 Annex B (duration) uses E2 < 1%, E3 1–10%, E4 > 10%. Heuristic exposure, and therefore ASIL, comes out one class **low** (non-conservative). LionDriver is not affected: it uses its own ISO anchors.
2. **hara-checklist-reviewer VA-33e** asserts formula-driven ASIL consistency based on the file format, without recomputing ASIL from S/E/C.
3. **hara-checklist-reviewer FSA-23** cites ISO 26262-8:2011; the current edition is 2018.
