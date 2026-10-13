# DFMEA rev 0.2 — Automated Pre-check

| | |
|---|---|
| **Work product** | `assurance/08-analyses/fmea/analyses/dfmea.yaml` rev 0.2 at BL-002, exported with `tools/safety/export_fmea_xlsx.py dfmea` (dfmea-builder layout) |
| **Tool** | `dfmea-checklist-reviewer` from the claude.ai skill library (not in jherrodthomas/automotive-skills-suite @ `026bb63`). Script hashes (sha256, first 12): `generate_checklist.py` cfa1cef356d2, `dfmea_probe.py` 164a983cafef, `check_definitions.py` ae4823f93b40; builder `generate_dfmea.py` 4c549641fdf3 |
| **Date** | 2026-10-12 |
| **Performed by** | Claude (AI assistant) |
| **Nature** | Automated pre-check. **Not** the AIAG-VDA confirmation review or an ISO 26262-2 confirmation measure. |

## How to reproduce

```
tools/safety/export_fmea_xlsx.py dfmea --generator <dfmea-builder>/scripts/generate_dfmea.py   # -> exports/dfmea.xlsx (git-ignored)
python3 <reviewer>/scripts/generate_checklist.py assurance/08-analyses/fmea/exports/dfmea.xlsx assurance/08-analyses/fmea/exports/dfmea-review-checklist.xlsx
```

The probe read 10 structure elements, 9 functions and 21 worksheet rows (one per cause).

## Result

| Tab | Checks | FC | PC | NO | Pending (human) |
|---|---|---|---|---|---|
| Confirmation Review | 18 | 14 | 0 | 0 | 4 |
| DFMEA Assessment | 14 | 10 | 2 | 1 | 1 |
| Verification Assessment | 4 | 0 | 0 | 0 | 4 |

Overall: 24 FC, 2 PC, 1 NO, 9 Pending; the reviewer reports "REJECTED" (66.7 %).

The first run had 3 more findings that came from gaps between the builder's layout and the reviewer's probe, not from the analysis. The exporter now fills them from the YAML (`postprocess`), and the run above is the second one:

| First-run finding | Cause | Fix in the export |
|---|---|---|
| CR-4e "Status field not populated", CR-11 and DFMEAA-1 "FMEA ID not populated", CR-12 "Project name not detected" | The builder writes the FMEA ID only in the header block and has no status field; the probe reads ID, status and project only from the title page (labels "FMEA ID", "Status", "Project") | Title page gets FMEA ID, Status and Project rows |
| DFMEAA-14 "No High-AP items pending" (FC) | The builder leaves the worksheet Status column blank, and the check counts only rows with a non-empty status, so an empty column reads as "nothing pending" | Status column filled from the YAML action statuses |

## Findings and disposition

| # | Reviewer finding | Disposition |
|---|---|---|
| DFMEAA-14 | **NO (headline)**: 21 High-AP items pending | **Accepted.** All 12 DFMEA actions are open. Every row is S10, and LionDriver has no hardware verification yet, so AP H is expected at this stage. Closing order that moves most rows: DFM-ACT-003 (watchdog HIL), -007 (relay readback), -002 (G1 layer 1 MCU measures), -005 (BOR/PVD). |
| DFMEAA-10 | 21/21 actions have an owner, 0 have a due date | **Accepted.** The YAML actions have no `due`. Dates depend on the HIL bench (D-04) and the G2/G3 gate plan (WP-M-03); to be set by the maintainer, not invented here. |
| DFMEAA-7 | **PC**: "0/21 have Detection rated" | **Tool defect (false PC).** The probe maps the column by partial match on "detection" and takes the first hit, "Detection Control (DC)" (text), instead of "Detection (1-10)". All 21 rows have D (8–10); `fmea_lint.py` requires it. |

## Passes not taken at face value

- **DFMEAA-2 (structure): FC, but the counts are wrong.** The probe reports "2 systems, 0 subsystems" because "subsystem" contains "system" and is tested first. The structure is 1 system, 1 subsystem, 8 components/interfaces.
- **DFMEAA-9 (High-AP items have actions): FC.** True, but each action is a plan, not a measure in place. 9 of 21 causes depend on information LionDriver does not have (schematic, BOM, relay and harness data, option bytes: WP-H-02 UK-01..UK-08).
- **DFMEAA-11 (special characteristics): FC on presence.** The 5 entries are *candidate* characteristics for integration and installation. LionDriver does not own the comma 3X drawings, so none is a design SC in the AIAG sense yet.
- **DFMEAA-5/6/8 (S, O, AP): FC.** Correct, and AP is the RT-1 AIAG-VDA table, not the builder's simplified rule (see the exporter docstring). The occurrence values are judgements without failure-rate data (header comment of `dfmea.yaml`).

## Pending items for the human reviewer

- CR-4a scope, CR-6 configuration management, CR-7 headers/footers, CR-13 and DFMEAA-13 references: the workbook is generated from git-controlled YAML (`assurance/` is under configuration management per WP-P-01); the references tab lists AIAG-VDA 2019, ISO 26262-5/-9 and the project documents.
- VA-1…4: need a hardware verification plan and report. None exists (WP-H-06, WP-S-09 not started); these stay Pending until then.

## Reviewer-tool defects recorded

| ID | Defect | Effect |
|---|---|---|
| TD-1 | Detection column matched by partial name, first hit wins ("Detection Control" before "Detection") | False PC on DFMEAA-7 for any dfmea-builder workbook |
| TD-2 | Pending check ignores rows with an empty status | False FC on the headline check for any dfmea-builder workbook, because the builder never fills Status |
| TD-3 | FMEA ID, status and project read only from the title page | False NO/PC on CR-4e, CR-11, CR-12, DFMEAA-1 for dfmea-builder output |
| TD-4 | "subsystem" classified as "system" | Wrong structure counts (no rating effect) |
| TD-5 | Builders (dfmea-builder, sw-fmea-builder) use a simplified AP rule (S ≥ 9 always H) and write placeholder revision history | Worked around in `export_fmea_xlsx.py` |

Defects of the other reviewers are recorded in the findings tables of the earlier pre-check records in this folder.
