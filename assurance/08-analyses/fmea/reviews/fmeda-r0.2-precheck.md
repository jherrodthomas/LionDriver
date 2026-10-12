# FMEDA rev 0.2 (SG-001, SG-009) — Automated Pre-check

| | |
|---|---|
| **Work product** | `assurance/08-analyses/fmea/analyses/fmeda-sg001.yaml` and `fmeda-sg009.yaml` rev 0.2 at BL-002 (generic failure rates), exported with `tools/safety/export_fmeda_xlsx.py` |
| **Tool** | `fmeda-checklist-reviewer` from the claude.ai skill library. Script hashes (sha256, first 12): `generate_checklist.py` 319c115e60d4, `fmeda_probe.py` 0bc4c1784fac, `check_definitions.py` 8d7fbb77d41f |
| **Date** | 2026-10-12 |
| **Performed by** | Claude (AI assistant) |
| **Nature** | Automated pre-check. **Not** the ISO 26262-2 confirmation review or the hardware verification review. |

## How to reproduce

```
tools/safety/export_fmeda_xlsx.py fmeda-sg001        # -> exports/fmeda-sg001.xlsx (git-ignored); needs LibreOffice to store calculated values
python3 <reviewer>/scripts/generate_checklist.py assurance/08-analyses/fmea/exports/fmeda-sg001.xlsx assurance/08-analyses/fmea/exports/fmeda-sg001-review-checklist.xlsx
```

Same for `fmeda-sg009`.

## Why not fmeda-builder

The workbooks are not made by `fmeda-builder` (`generate_fmeda.py` 7a8e2173e287). Its worksheet formulas disagree with ISO 26262-5:
- `λ_SPF = IF(safety_related="No", λ, …)` counts the failure rate of non-safety-related elements as single-point.
- `λ_RF` and `λ_MPF_L` use the same formula, so every residual fault is also counted as latent.
- It has no input for whether a fault violates the goal directly or only as part of a multiple-point fault.

The exporter keeps the builder's tab names, so the reviewer can read the workbook. It uses the classification of rating-tables §6.1, and its formulas give the same metrics as `fmea_lint.fmeda_metrics` (checked after recalculation).

## Result

| Workbook | Confirmation Review (18) | FMEDA Assessment (14) | Verification (4) |
|---|---|---|---|
| SG-001 | 13 FC, 5 pending | 8 FC, 2 NO, 1 PC, 2 LC, 1 pending | 4 pending |
| SG-009 | 13 FC, 5 pending | 9 FC, 1 NO, 1 PC, 2 LC, 1 pending | 4 pending |

The first run also gave NO on distribution sums, PC on classification and PC on mechanism allocation for both workbooks. These were layout mismatches: fractions instead of percent, combined labels such as "RF + MPF_D", and a second mechanism column for latent coverage. The exporter now writes percent, one label per row and one mechanism/DC column; the results above are from the second run.

## Findings and disposition

| # | Reviewer finding | Disposition |
|---|---|---|
| FMEDAA-8 (SG-001) | NO: SPFM 96.9 % < 99 % (ASIL D) | **Accepted.** Also 0.1 point short of ASIL C (97 %), the rating in WP-C-03. Main gaps are the brown-out zone (no BOR/PVD reaction) and frame corruption after the TX check. See WP-H-03 §6.3 for the effect of the planned measures |
| FMEDAA-9 (SG-001) | NO: LFM 87.7 % < 90 % (ASIL D) | **Accepted.** Meets ASIL C (80 %). Main gaps: CPU check faults with no self-test, clock drift with no cross-check, double-bit RAM errors not handled |
| FMEDAA-8 (SG-009) | NO: SPFM 86.8 % < 90 % (ASIL B) | **Accepted.** Transceiver faults with the relay driven, relay welded or driver stuck, and stock-path opens have no mechanism; relay readback (DC-03) is the main fix |
| FMEDAA-6 | PC: 9/14 (SG-001) and 8/17 (SG-009) safety-relevant rows have a mechanism | **Accepted.** The rows without one are the single-point and fully latent faults listed in `11_Open_Items`; they are the actions of the DFMEA |
| FMEDAA-12, -14 | LC: open items; FIT source generic | **Accepted.** Generic rates are the declared basis of this revision (WP-H-03 OI-10) |

## Passes not taken at face value

- **FMEDAA-10 (PMHF): FC for both.** The value is λSPF + λRF only; the dual-point term is not computed. With generic rates it says little.
- **FMEDAA-11 (total FIT reasonable): FC.** The check only tests a range; 220/242 FIT is an estimate.
- **SPFM depends strongly on the assumed SRAM soft-error rate** (WP-H-03 §6.3). Corrected single-bit upsets raise the denominator, so a higher SER makes SPFM look better.

## Reviewer-tool defects recorded

| ID | Defect | Effect |
|---|---|---|
| TD-6 | Column lookup by partial name, first hit wins: "lambda s" also matches "Lambda SPF" | The exporter places "Lambda S" before "Lambda SPF" |
| TD-7 | Classification accepts only the five exact labels, so a row with both a residual and a detected part cannot be shown as such | One label per row in the export (RF for a covered direct fault) |
| TD-8 | Metrics read from a single dashboard, so one workbook can hold one safety goal only | One workbook per goal |
| TD-9 | fmeda-builder formulas (see "Why not fmeda-builder") | Builder not used |
