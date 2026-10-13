# HARA rev 0.2 — Automated Pre-check (re-run)

| | |
|---|---|
| **Work product** | `assurance/08-analyses/fmea/analyses/hara.yaml` rev 0.2 (LD-HARA-001) |
| **Tool** | `hara-checklist-reviewer`, jherrodthomas/automotive-skills-suite @ `026bb63` |
| **Date** | 2026-10-10 |
| **Performed by** | Claude (AI assistant) |
| **Previous** | [hara-r0.1-precheck.md](hara-r0.1-precheck.md) |
| **Nature** | Automated pre-check. **Not** the ISO 26262-2 confirmation review (OI-007 remains open). |

## What changed since rev 0.1

| Open item | Change in rev 0.2 | Checked by `fmea_lint.py` |
|---|---|---|
| OI-009 guide words | `guideword_analysis`: all 112 function × guide-word pairs (8 × 14): 93 SC, 10 NSC, 9 NA, each with rationale; 29 pairs recorded as subsumed by another guide word. Hazard `functions`/`guidewords` are now derived from the matrix. | Matrix complete; SC pairs name hazards; NSC/NA pairs don't; `subsumed_by` resolves; each hazard's functions and guide words equal the matrix |
| OI-010 situation coverage | `situation_coverage`: all 195 hazard × situation pairs: 19 rated, 112 dominated, 64 not relevant | Every pair present; rated pairs match their event; **each dominated estimate's ASIL ≤ the dominating event's ASIL**; every event rated exactly once |
| OI-011 weather | OS-013 wet road (E3), OS-014 snow/ice (E2), OS-015 night (E4), covered for all 13 hazards. New HE-019: HZ-006 on snow/ice, S3 E2 C3 → B | As OI-010 |

## What the systematic pass found

- **No new hazards.** Every SC guide-word pair maps to one of the 13 existing hazards.
- **New cause path for HZ-002 and HZ-006:** F8 / M03, a relay fault letting stock and item steering or braking commands combine. Linked to SFM-034 in System FMEA rev 0.4.
- **Primary guide word corrected for HZ-008 and HZ-009.** Rev 0.1 said M10 (applies too long). The matrix derives these hazards from no-function, partial and late override (M01, M06, M08), so M01 is now primary.
- **No safety-goal ASIL changed.** Weather does not raise any goal at US-average exposure.
- **New sensitivity on SG-005.** In snow-belt use, snow/ice exposure can exceed 1% (E3). HE-019 would then become ASIL C and raise SG-005 from B to C. Tracked in OI-006.
- **Largest dominated margins:** the incapacitated-driver situation (OS-007, E1) appears in every engaged hazard but never exceeds ASIL A against D/C/B rated events.

## Reviewer result

| Tab | Checks | FC | PC | NO | NA | Pending |
|---|---|---|---|---|---|---|
| Confirmation Review | 14 | 9 | 0 | 0 | 0 | 5 |
| Functional Safety Assessment | 24 | 14 | 2 | 0 | 2 | 6 |
| Verification Assessment | 44 | 2 | 2 | 0 | 1 | 39 |

Counts are unchanged from rev 0.1. The remaining PCs are a **tool limitation**, not open gaps:

| # | Reviewer finding | Disposition |
|---|---|---|
| FSA-6 | "Only 6 malfunction guide words used" | **Closed by evidence.** The reviewer counts the primary guide word of each worksheet row and does not read the `11_Function_x_Malfunction` tab, which holds all 14 guide words for every function (112 pairs). It reads 6, down from 7, because HZ-008/HZ-009's primary moved from M10 to M01. |
| FSA-8, VA-33, VA-33d | "19 rows; expected ~468 for full Cartesian" | **Closed by evidence.** The estimate is functions × guide words seen × situations. ISO 26262-3 6.4.2 requires relevant combinations to be considered, which `12b_Situation_Coverage` records for every hazard × situation pair, with checked estimates for dominated pairs. |

Padding the worksheet to satisfy these heuristics would weaken the HARA, so it was not done.

## Defects found in the skills (additions to rev 0.1 list)

4. **hara-checklist-reviewer** does not read the `11_Function_x_Malfunction` tab that `hara-builder` itself produces. FSA-6 can only be satisfied by putting every guide word into worksheet rows.
5. **hara-checklist-reviewer** FSA-8 / VA-33 compares the row count against a full Cartesian estimate and has no way to accept documented dominance or relevance arguments.
