# Change impact: clause-check register, ISO 26262-3 pilot

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to assurance tooling and data. The project lead asked for a pilot of a check engine built from the standard's requirements in the project's own words, for continuous assurance (2026-10-26). It follows a review of an external engine, `TomcoGame/isowizmcp`, which was not adopted: its rules were never evaluated, its ASIL tables were wrong in 22 and 34 of 80 cases, and its data reproduced about 420 KB of standard text.

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-26** in this LionDriver PR; checked in CI; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | Assurance data and an in-house checker (WP-P-07 TL-59, TCL2 proposed); no vehicle software changes |
| Reference configuration affected | No |
| Decision | Lead's request of 2026-10-26 (chat); placement and design are reversible technical choices (`decider: claude`) |
| Requirements | None changed. The register reads WP-C-01, WP-C-03, WP-C-04 and the trace data; it changes none of them |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Effect | Verification |
|---|---|---|---|
| Register | `assurance/trace/clauses/iso26262-3-2018.yaml`, [`README.md`](../../trace/clauses/README.md) | 21 obligations of ISO 26262-3:2018 §5–§7 in the project's own words, each with the work product and the checks that evidence it; no standard text; none verified against the licensed standard | Read-through; `check_clauses.py` rejects malformed rows |
| Checker | `assurance/trace/tools/check_clauses.py`, `test_check_clauses.py` | Runs the `check_trace.py` checks in-process, finds work-product sections and item fields, writes [`iso26262-3-2018-coverage.md`](../../trace/clauses/iso26262-3-2018-coverage.md): 17 pass, 3 manual (the independent reviews), 1 gap (trace check K5 not implemented) | `test_check_clauses.py` (6 tests) in the `unittest discover` step; `check_clauses.py --check` in CI |
| CI, tool register, trace README | `.github/workflows/assurance.yaml`, WP-P-07 v0.9.24 (TL-59), trace README v0.5 | One CI step; the tool classified; the register listed in §2 and the CI paragraph | CI run on this PR |

## 2. Impact

- **Safety:** none on the item. A coverage status is not evidence of compliance and nothing rests on it; the page says so.
- **Assessment package:** [ARA-26262-2018-001](../../00-assessment/iso26262-2018/README.md) is frozen and unchanged. Its empty `licensed_clause_inventory.csv` remains the intake for verified rows.
- **Copyright:** the register holds clause numbers and our own sentences only. A reviewer should confirm that no row mirrors the standard's wording.
- **CI time:** a few seconds; the trace checks run a second time in-process.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | A holder of the licensed standard verifies the 21 rows and fills the sub-clauses (register README §3) | Before any coverage status is cited |
| OI-2 | Implement trace check K5, closing obligation O3-7.02's gap | Next tooling change to `check_trace.py` |
| OI-3 | The lead decides whether to keep the pilot and extend it to further parts and standards | After OI-1 |
