# Author-side validation — ARA-26262-2018-002 v0.1

Draft I0 record, 2026-10-15 UTC. These results check artifact integrity and consistency; they do not approve the assessment or supply safety evidence.

| Check | Observed result |
|---|---|
| `python3 assurance/00-assessment/iso26262-followup/build_followup.py --check` | PASS; all generated artifacts reproduced from immutable Git objects |
| Independent Git SHA-256 and source-line comparison | PASS; every recorded source hash and each quoted finding passage matched the subject object |
| HTMLParser comparison of decoded highlight text with Git source | PASS; all 11 highlighted passages matched exactly |
| Workbook ZIP integrity / worksheet count | PASS; 6 worksheets; no corrupt ZIP entry |
| Independently summed JSON census | 216 specified IDs; 201 explicitly unexecuted in report rows; 15 specified IDs without report rows |
| Deliberately appended invalid CSV bytes, then ran `--check` | Rejected `test_summary.csv`; original bytes restored in `finally`; subsequent reproduction PASS |
| `python3 assurance/trace/tools/check_links.py` | 3,967 relative links checked, zero broken (before adding this validation record, which has no links) |
| `python3 assurance/trace/tools/check_tables.py` | 197 Markdown files passed (before adding this validation record) |
| `python3 assurance/trace/tools/check_trace.py` | PASS; 412 items across 7 files |
| `python3 assurance/case/tools/validate.py` | PASS; 0/36 claims accepted, 0/50 evidence accepted; Development state |
| `python3 assurance/case/tools/generate_dashboard.py --check` | PASS; outputs match records |
| `python3 assurance/00-assessment/iso26262-2018/verify_package.py` | PASS; original frozen package remains internally consistent |
| `.venv/bin/ruff check` and `.venv/bin/ruff format --check` on the new generator | PASS |
| `git diff --check` | PASS |

No browser execution/rendering, vendor-datasheet authentication, target/HIL/vehicle test, normative source validation, FMEDA recalculation or human verification is claimed. The new script uses standard-library parsing plus XlsxWriter 3.2.9. Numerical range expansion is restricted to first-column VS IDs; the exact rows remain available for human interpretation. Generated files and hashes do not prove the assessment judgments correct.
