# Audit package

Open `LionDriver_ISO26262_Audit.xlsx` for the filterable workbook, or `Review_board.html` for the offline interactive diagrams and finding ledger. Read `Audit_report.md` for scope, substantive findings and limits. SVG and PNG files are standalone exportable diagrams.

The workbook intentionally contains no verified compliant/non-compliant verdicts and no guessed complete standard inventory. User-provided licensed source access is pending. `licensed_clause_inventory.csv` is the source inventory input template; a non-empty input makes the generator stop for explicit normative integration instead of silently ignoring it.

Use the controlled package README and `regenerate.sh` to render the archived subject revision. Dependencies are recorded in `requirements.lock.txt`. The source root, source Git repository, subject revision and output directory are supplied by the reproduction script. Fresh checks and raw logs are in `checks.json` and `logs/`. Source hashes and exact checkout identity are in `audit_data.json` and `manifest.json`. This workbook is an AI-assisted review aid and has not been independently qualified as a safety assessment tool.
