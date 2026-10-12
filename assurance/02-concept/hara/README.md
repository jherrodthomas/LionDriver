# HARA Cartesian model

This folder holds the Cartesian HARA behind [WP-C-03](../WP-C-03-hara.md) §2.

| File | What it is |
|---|---|
| [`hara_model.py`](hara_model.py) | Source of truth. It holds every analyst input: functions, the 14-guide-word classification with rationale, situations, conditions, and the S/C rating rules |
| [`hara-cartesian-summary.md`](hara-cartesian-summary.md) | Generated step counts and worst cases per hazard |
| [`WP-C-03-hara-cartesian.xlsx`](WP-C-03-hara-cartesian.xlsx) | Generated workbook, reference scope (Chill mode only) |
| [`WP-C-03-hara-cartesian_experimental.xlsx`](WP-C-03-hara-cartesian_experimental.xlsx) | Generated workbook, Experimental Mode variant (D-08 option B) |
| [`hara-events.csv`](hara-events.csv) | Generated. All 2 790 hazardous-event rows of the reference workbook (tab 12), one per line, with S/E/C rationale, ASIL, ASIL if the ⚠ AoUs fail, and safety goal. **This is the file to review on GitHub**: it renders as a searchable table, and a PR diff shows exactly which rows a rule change moves |
| [`hara-events_experimental.csv`](hara-events_experimental.csv) | Generated. The same for the Experimental Mode variant (2 970 rows) |
| [`hara-function-guideword.csv`](hara-function-guideword.csv) | Generated. The 140 function × guide-word pairs (tab 11, both variants) with class SC / NSC / NA, subsumption and the reason. This is the SC filter that decides which rows exist (RR-2026-003 F-01) |

## Regenerating

1. Write the generator inputs to `build/` (not committed), the summary, and the counts table in WP-C-03 §2.1:

   ```bash
   python3 hara_model.py
   ```

2. Generate each workbook with the hara-builder skill's generator, apply the LionDriver corrections, then recalculate the formulas (LibreOffice):

   ```bash
   python3 <hara-builder>/scripts/generate_hara.py build/hara_input.json WP-C-03-hara-cartesian.xlsx
   python3 hara_model.py --postprocess WP-C-03-hara-cartesian.xlsx
   python3 <hara-builder>/scripts/recalc.py WP-C-03-hara-cartesian.xlsx
   ```

   Repeat for `build/hara_input_experimental.json` → `WP-C-03-hara-cartesian_experimental.xlsx`.

   - Post-processing replaces the generator's exposure anchors with ISO 26262-3 Table B.2.
   - It adds the rationale column to tab 11 and the "Consolidated into" column to tab 13.
   - It has to run **before** the recalculation, because re-saving with openpyxl drops cached formula values.

3. CI runs `python3 hara_model.py --check`. It fails if the summary, the CSV files or the WP-C-03 §2.1 table no longer match the model.

## Reviewing

- Each CSV row has a stable key, `function/guide word/situation/condition` (e.g. `F-01/M04/OS-02/W02`), and the workbook row ID (`H-0001`…) for cross-reference. To comment on a row, open the CSV in a PR and comment on its line, quoting the key.
- Changing a rating means changing a rule in `hara_model.py`. Regenerate, and the CSV diff shows every row the rule affects.
- The CSVs and workbooks come from the same model; every ASIL in the CSVs equals the workbook's tab 12, row for row.

The workbooks were generated with hara-builder `generate_hara.py` (sha256 `188f7e51df06aceae7668bb6563f009b8e28189754d3eedc87f93c05f2a91a33`, after removing trailing NUL padding from the synced copy). Every ASIL in both workbooks was checked against the independent computation in `hara_model.py`, and they agree: 2 790 and 2 970 rows, 0 mismatches.
