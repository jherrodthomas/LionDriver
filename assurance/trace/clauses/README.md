# Clause-check register (pilot: ISO 26262-3:2018)

| Field | Value |
|---|---|
| Record | Part of WP-T-01 (requirements and traceability data, [../README.md](../README.md)); supporting assessment aid, not a new registered work product |
| Scope | Pilot: ISO 26262-3:2018 clauses 5 (item definition), 6 (hazard analysis and risk assessment) and 7 (functional safety concept), against WP-C-01, WP-C-03 and WP-C-04 |
| Version | 0.2 (2026-10-26): trace check K5 implemented, O3-7.02 open with 51 recorded findings (OI-2 closed). 0.1 (2026-10-26): initial pilot, 21 obligations; I0, Claude |
| Status | Draft. **No row is verified against the licensed standard**; every row is a proposal |
| Author | Claude (AI-assisted draft, I0 under WP-M-02 §3.3) |
| Reviewer(s) | TBD: a holder of the licensed standard verifies each row (§3) |
| Approver | Safety manager |
| Change record | [Impact analysis](../../07-supporting/impact/change-2026-10-26-clause-check-register.md) |

## 1. What it is

Each obligation names a clause of a standard and states, in one sentence of the project's own words, what must be
true of a LionDriver work product. It also names the checks that show whether that holds. [`../tools/check_clauses.py`](../tools/check_clauses.py)
runs the checks on every pull request that touches `assurance/` and regenerates the coverage page,
[`iso26262-3-2018-coverage.md`](iso26262-3-2018-coverage.md). A change in any obligation's status therefore shows
up in review: continuous assurance at clause level.

| Check | What it does |
|---|---|
| `trace:<ID>` | Runs the check of [`check_trace.py`](../tools/check_trace.py) with that ID ([trace README §6](../README.md#6-consistency-checks)) and counts its errors |
| `section:<text>` | The work product has a heading containing the text, with content under it (presence only: a reviewer judges adequacy) |
| `items:<kind>:<fields>` | Every trace item of that kind has those fields filled |
| `manual:<what>` | A human judgement, such as an independent review; reported as open until a record exists |

| Status | Meaning |
|---|---|
| ✅ pass | Every automated check passes |
| 🟡 partial | It passes, but rests on a trace check that is only partly implemented |
| 👤 manual | The automated checks pass (or there are none), and a human judgement remains |
| ⬜ gap | A check it needs is not implemented (none today: K5 was the last one the pilot needed) |
| ❌ open | An automated check finds a defect in the work products, including findings recorded with an owner (the K5 baseline, [`../links/k5-known.yaml`](../links/k5-known.yaml)) |

The script fails CI on a broken register: a malformed row, an unknown check, a work product or section that does not
exist, or a stale coverage page. An `open` obligation does not fail it. The coverage page records the status, and
`check_trace.py` fails CI on its own errors.

A pass shows that the evidence is present and consistent. It is not an ISO 26262 compliance verdict, an assessment
or an acceptance. The checks are unqualified tools ([WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md)).

## 2. The standard's text is never copied

The ISO standards are copyrighted. The register holds clause numbers and the project's own one-sentence statements
of what to check; it never holds the standard's wording, tables, notes or examples, not even reworded sentence by
sentence. A row is written from an understanding of the clause, short, and in the vocabulary of LionDriver's work
products. The same rule applies to [`00-assessment/iso26262-2018/licensed_clause_inventory.csv`](../../00-assessment/iso26262-2018/licensed_clause_inventory.csv),
whose verified rows can later feed this register.

## 3. Verifying a row

The rows were drafted (I0) from the clause structure of the standard, without the licensed text, so their clause
references are unconfirmed and their sub-clauses empty. A holder of the licensed ISO 26262-3:2018 checks each row:

1. the clause is right, and the sub-clause is filled in `subclause`;
2. the obligation is a fair statement of what that sub-clause requires (in our words, §2);
3. the checks named show that it holds, as far as automation can.

They then fill `source_verified_by` (name and role) and `source_verified_date`. A missing obligation is added as a new
row; a wrong one is corrected or withdrawn. The coverage page counts the verified rows.

## 4. Next steps

| ID | Item | Responsible role |
|---|---|---|
| OI-1 | Verify the 21 rows against the licensed standard (§3) | Standards custodian / safety manager |
| OI-2 | Closed 2026-10-26: trace check K5 implemented. O3-7.02 is now open, not a gap: 51 requirements are rated below a parent, each recorded with its owner in [`../links/k5-known.yaml`](../links/k5-known.yaml) (34 owned by WP-S-02 OI-2 and WP-C-04 OI-9 and OI-11; 17 QM ones without backstop notation have no open item yet) | Safety manager (the findings) |
| OI-3 | Link the manual obligations to their review records once CR-02 and the WP-C-04 review exist, so they read as evidence | Safety manager |
| OI-4 | If the pilot is kept, extend it to ISO 26262-4 to -6, ISO 21448 and ISO/SAE 21434 (identifiers only for the work products of 21434) | Safety manager (decision) |
