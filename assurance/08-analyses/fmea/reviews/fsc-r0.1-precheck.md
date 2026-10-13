# FSC rev 0.1 — Automated Pre-check

| | |
|---|---|
| **Work product** | `assurance/08-analyses/fmea/analyses/fsc.yaml` rev 0.1 (LD-FSC-001), exported with `tools/safety/export_fsc_xlsx.py` |
| **Tool** | `fsc-checklist-reviewer`, jherrodthomas/automotive-skills-suite @ `026bb63` |
| **Date** | 2026-10-10 |
| **Performed by** | Claude (AI assistant) |
| **Nature** | Automated pre-check. **Not** the ISO 26262-2 confirmation review. |

## How to reproduce

```
tools/safety/export_fsc_xlsx.py                          # -> assurance/08-analyses/fmea/exports/fsc.xlsx (git-ignored)
python3 <reviewer>/scripts/generate_checklist.py assurance/08-analyses/fmea/exports/fsc.xlsx assurance/08-analyses/fmea/exports/fsc-review-checklist.xlsx
```

The probe read 10 safety goals, 12 architecture nodes, 40 FSRs and 75 allocation rows. Architecture elements `EL-xx` appear as node IDs `Nxx` in the workbook because the reviewer only accepts node IDs starting with "N".

## Result

| Tab | Checks | FC | PC | NO | NA | Pending (human) |
|---|---|---|---|---|---|---|
| Confirmation Review | 14 | 10 | 0 | 0 | 0 | 4 |
| Functional Safety Assessment | 16 | 10 | 3 | 0 | 0 | 3 |
| Verification Assessment | 34 | 1 | 2 | 1 | 1 | 29 |

## Findings and disposition

| # | Reviewer finding | Disposition |
|---|---|---|
| FSA-7 | 14/40 FSRs have an FTTI | **Accepted.** Only SG-001 and SG-002 have a preliminary FTTI (900 ms, SAFETY.md basis). The rest wait on OI-004. Unknown FTTIs are left blank in the export so the reviewer can see them. |
| FSA-11, VA-33a | No FTA top event per safety goal | **Accepted.** FTA isn't mandatory, but nothing yet shows that the FSRs cover every cause path to each goal. → FOI-009 |
| FSA-12, VA-33c | "10 nodes referenced by FSRs missing from block diagram" | **Tool defect.** The reviewer reads a cell such as `N03, N04` as one node ID. Every allocation resolves to a defined element; `fmea_lint.py` checks this. |
| VA-33e | **NO**: "11 FSRs have ASIL inconsistent with parent SG" | **Tool defect (false NO).** The check compares the letter before the parenthesis with the goal ASIL, so every valid `QM(D)`, `QM(C)` and `QM(B)` decomposition fails. The 11 flagged FSRs are exactly those. `fmea_lint.py` checks every decomposition against ISO 26262-9 Table 1. |

## Passes not taken at face value

- **FSA-10 (decomposition independence documented): FC on text presence only.** Every decomposition states an independence argument, and every one says the DFA is still owed. Independence is *argued, not demonstrated*; no decomposition is accepted until FOI-002 closes.
- **FSA-5 (ASIL inherited): FC.** Correct, and enforced by `fmea_lint.py`. FSR ASILs are inherited or valid X(Y) decompositions.
- **FSA-15 (verification planned): FC from tab presence.** 9 FSRs cite opendbc safety tests in a submodule that is not checked out here. 15 verification entries are still `planned` only.

## Pending — proposed disposition for the human reviewer

| # | Topic | Proposed |
|---|---|---|
| FSA-2 | Item definition | **NO**: still not written (as in the HARA pre-check). |
| FSA-8 | Warning and degradation | FC: `11_Warning_Degradation` defines WD-01…WD-06 with triggers, reactions, warnings and times. |
| FSA-14 | Operating modes | FC: `10_Operating_Modes` covers off, start-up, disabled, engaged, overriding, soft disabling, lockout and dashcam. |
| CR-6 | Configuration management | FC: YAML under git; FSC pinned to HARA rev 0.2, and the linter fails if the HARA revision moves. |

## Defects found in the skills (continuing the HARA pre-check list)

6. **fsc-checklist-reviewer VA-33e** reports decomposed ASILs as inconsistent (false **NO**), contradicting its own FSA-10.
7. **fsc-checklist-reviewer FSA-12 / VA-33c** cannot parse FSRs allocated to more than one node.
8. **fsc-checklist-reviewer** ignores block-diagram rows whose ID does not start with "N".
9. **fsc-checklist-reviewer FSA-7** counts any non-empty FTTI cell as specified, so a placeholder such as "TBD" would pass.
