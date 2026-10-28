# Change impact: clause-check register extended to ISO 21448 (SOTIF)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to assurance tooling and data. The project lead asked to extend the clause-check pilot ([first change](change-2026-10-26-clause-check-register.md), PR #486) to ISO 21448 (2026-10-26).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-26** in this LionDriver PR; checked in CI; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | Assurance data and an in-house checker (WP-P-07 TL-59); no vehicle software changes |
| Reference configuration affected | No |
| Decision | Lead's request of 2026-10-26 (chat); the obligations and their checks are reversible technical choices (`decider: claude`) |
| Requirements | None changed. The register reads the SOTIF work products and the trace data; it changes none of them |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Effect | Verification |
|---|---|---|---|
| Register | `assurance/trace/clauses/iso21448-2022.yaml` | 27 obligations of ISO 21448:2022 §4–§13 in the project's own words, against WP-M-08, WP-C-02, WP-C-05…07, WP-V-02…04, WP-K-02 and WP-O-04; no standard text; none verified against the licensed standard. Activities that must have been *carried out* (validation runs, residual-risk estimate, release evaluation, review of the targets) are manual checks, since the work products hold plans and templates | [`iso21448-2022-coverage.md`](../../trace/clauses/iso21448-2022-coverage.md): 23 pass, 4 manual |
| Checker | `assurance/trace/tools/check_clauses.py`, `test_check_clauses.py` | A register names its `id_prefix` (the 26262-3 one `O3`, this one `S`); a section check takes the heading that is exactly its text before one that only contains it ("Validation targets" had matched "Method for deriving validation targets"); withdrawn trace items are not checked for fields (SH-07) | 2 new tests (8 in all); the 26262-3 register's results are unchanged |
| Docs, CI | Register README v0.3, trace README v0.7, WP-P-07 v0.9.27 (TL-59 scope), the CI step's name | The second register listed; how manual checks are used in it | CI run on this PR |

## 2. Impact

- **Safety:** none on the item. A coverage status is not evidence of compliance; 23 "pass" mean the plans and analyses exist and the SOTIF trace data is consistent, not that the SOTIF is achieved. The 4 manual obligations say what is not done: WP-K-02's evaluation is "not executed" at this baseline.
- **Copyright:** clause numbers and our own sentences only. A reviewer should confirm that no row mirrors the standard's wording.
- **CI time:** negligible.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | A holder of the licensed ISO 21448:2022 verifies the 27 rows and fills the sub-clauses (register README §3) | Before any coverage status is cited |
| OI-2 | Clause 4's scope and title are taken from the project's own WP-M-08; confirm that clause 4 is where the standard places the management of SOTIF activities | With OI-1 |
