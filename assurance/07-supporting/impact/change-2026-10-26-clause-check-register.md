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
| Checker | `assurance/trace/tools/check_clauses.py`, `test_check_clauses.py` | Runs the `check_trace.py` checks in-process, finds work-product sections and item fields, writes [`iso26262-3-2018-coverage.md`](../../trace/clauses/iso26262-3-2018-coverage.md): 17 pass, 3 manual (the independent reviews), 1 open (O3-7.02, the K5 findings) | `test_check_clauses.py` (6 tests) in the `unittest discover` step; `check_clauses.py --check` in CI |
| Check K5 | `assurance/trace/tools/check_trace.py` (`check_asil_inheritance`), `test_check_trace.py`, [`links/k5-known.yaml`](../../trace/links/k5-known.yaml), trace README §6 and Figures 1 and 7 | Every FSR, TSR, SWSR and HWSR is checked against each parent's ASIL (WP-P-06 §7), reading the WP-S-02 §2.1 notations: B‡ as C; QM (X-sup) as an **[ext]** backstop convention that passes when X is not lower and its named backstops carry X; X(Y) when WP-A-01 cites the child. 51 findings today, each recorded with its owning open item; a new finding, or an entry that no longer occurs, fails CI. No ASIL was changed | 5 new tests (parsing, levels, backstops, decomposition, the ratchet); `check_trace.py` passes with 51 known findings |
| CI, tool register, trace README | `.github/workflows/assurance.yaml`, WP-P-07 v0.9.24 (TL-59), trace README v0.6 | One CI step; the tool classified; the register listed in §2 and the CI paragraph | CI run on this PR |

## 2. Impact

- **Safety:** none on the item. A coverage status is not evidence of compliance and nothing rests on it; the page says so. K5 changes no ASIL: it makes 51 existing inheritance findings visible and blocks new ones.
- **Assessment package:** [ARA-26262-2018-001](../../00-assessment/iso26262-2018/README.md) is frozen and unchanged. Its empty `licensed_clause_inventory.csv` remains the intake for verified rows.
- **Copyright:** the register holds clause numbers and our own sentences only. A reviewer should confirm that no row mirrors the standard's wording.
- **CI time:** a few seconds; the trace checks run a second time in-process.

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | A holder of the licensed standard verifies the 21 rows and fills the sub-clauses (register README §3) | Before any coverage status is cited |
| OI-2 | Disposition the 51 K5 findings in `links/k5-known.yaml` (raise the ASIL, decompose it in WP-A-01, or name the backstop as QM (X-sup)); 34 belong to WP-S-02 OI-2 (19) and WP-C-04 OI-11 (14) and OI-9 (1), and 17 QM ones with no backstop notation need an owner. Also propose the QM (X-sup) reading of K5 for WP-P-06 §7, which today exempts only decomposition | Safety manager; G2 (WP-S-02 OI-2) |
| OI-3 | The lead decides whether to keep the pilot and extend it to further parts and standards | After OI-1 |
