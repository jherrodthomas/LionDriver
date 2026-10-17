# Pre-check refresh: HARA and item definition (2026-10-16)

| | |
|---|---|
| **Covers** | [hara-r0.1-precheck.md](hara-r0.1-precheck.md), [hara-r0.2-precheck.md](hara-r0.2-precheck.md), [item-definition-r0.1-precheck.md](item-definition-r0.1-precheck.md) |
| **Why** | Decision register DQ-028, option A: Claude refreshes the stale pre-check items and lists what needs the lead's rating |
| **Performed by** | Claude (AI assistant). Not re-run with the checklist tool: the items below were re-read against the current work products |
| **Nature** | Input to the human reviews. **Not** a review, and not the ISO 26262-2 confirmation review (HARA OI-007, item definition IOI-006) |
| **Not covered** | The FSC and DFMEA pre-checks ([fsc-r0.1-precheck.md](fsc-r0.1-precheck.md), [dfmea-r0.2-precheck.md](dfmea-r0.2-precheck.md)), which belong to the safety-concept and DFMEA sessions |

## 1. What the pre-checks looked at

The HARA pre-checks ran on the second-set HARA `analyses/hara.yaml` (LD-HARA-001) at rev 0.1 and 0.2. Since then:

- LD-HARA-001 is at rev 0.4;
- the HARA of record is [WP-C-03](../../../02-concept/WP-C-03-hara.md) (v0.4.2). The second set is mapped onto it in [`hara-mapping.yaml`](../hara-mapping.yaml), and its withdrawal waits on DQ-124.

So a rating given below rates the second set, not the HARA the safety case rests on. The checklist tool has not been run on WP-C-03. Running it on the WP-C-03 workbook would give the reviews a pre-check of the HARA of record (§4).

The item-definition pre-check ran on LD-ITEM-001 rev 0.1. That document is now at rev 0.4, and [WP-C-01](../../../02-concept/WP-C-01-item-definition.md) (v0.12) is the item definition for the reference configuration.

## 2. Stale items, refreshed

| Pre-check | Item | Was | Now |
|---|---|---|---|
| HARA r0.1 | FSA-1 Item definition available | NO: no formal item definition | **FC proposed.** LD-ITEM-001 rev 0.4 and WP-C-01 v0.12 exist. Neither has had its human review yet (IOI-006, DQ-027) |
| HARA r0.1 | FSA-19, VA-33a situation granularity | Judged from 12 situations; weather not differentiated (OI-011) | **FC proposed.** Rev 0.2 added wet, snow/ice and night (OS-013…015), and `situation_coverage` records all hazard × situation pairs; OI-011 is closed |
| HARA r0.1 | FSA-6, FSA-8, VA-33, VA-33d | PC (guide words, Cartesian size) | Closed by evidence in r0.2 (all 112 pairs; coverage table). No rating needed |
| HARA r0.1 | CR-10 all sections complete | FTTI TBD for every goal (OI-004) | **Still PC.** `ftti_ms` is still null for all ten goals of LD-HARA-001. WP-C-03 gives a preliminary FTTI per goal |
| HARA r0.1 | FSA-10 measures outside ISO 26262 | PC: EPS and powertrain limits not yet credited (OI-001, OI-002) | **Still PC.** Same AoUs as WP-C-03 AOU-01/02/05, all unverified; the measurement is a G1 entry condition (DQ-008) |
| Item def r0.1 | CR-4d change history | PC: one entry | **FC proposed.** Document control now lists rev 0.1…0.4 |
| Item def r0.1 | CR-8 table of contents | PC: no TOC | **Still PC.** Sections are numbered but there is no TOC |
| Item def r0.1 | IDA-10 HARA-ready | "HARA rev 0.3 already uses this item definition" | **FC, reworded:** LD-HARA-001 rev 0.4 and WP-C-03 v0.4.2 both use it; the HARA covers AC-001 only |
| Item def r0.1 | Gap list, stale cross-reference | "§1.2 updated to HARA rev 0.3 / FSC rev 0.2 / DFA rev 0.3" | Overtaken: Part C now cites HARA rev 0.4, FSC rev 0.3, DFA rev 0.5. §1.2 still names HARA rev 0.3, FSC rev 0.2 and DFA rev 0.3 as the analyses performed for AC-001; that is a record of what was done, not stale |

## 3. For the lead to rate

Eleven items. Each has a proposed rating; reply with the rating per item, or "as proposed".

| # | Pre-check | Item | Proposed | Why |
|---|---|---|---|---|
| 1 | HARA | FSA-1 Item definition available | FC | §2: both item definitions exist, review pending |
| 2 | HARA | FSA-9 All consequences identified | PC | Consequences are recorded per event; secondary consequences (multi-vehicle) are not analysed |
| 3 | HARA | FSA-10 Measures outside ISO 26262 highlighted | PC | §2: identified, not verified |
| 4 | HARA | FSA-14 Exposure not based on fleet penetration | FC | HA-005: E is rated on situation share, no fleet data |
| 5 | HARA | FSA-17 Unavailability hazards justified | FC | Loss with warning is not hazardous; loss without warning is HZ-004 / HZ-012 |
| 6 | HARA | CR-6 Configuration management | FC | YAML under git, baseline, generated exports not committed |
| 7 | HARA | CR-10 All sections complete | PC | §2: FTTI missing in the second set |
| 8 | Item def | IDA-5 Modes cover normal, degraded, fault | PC | No explicit fault mode for a persistent panda fault (NO_OUTPUT after a violation); the pre-check says it is handled as disabled + WD-06 (FSC) |
| 9 | Item def | CR-4d Change history | FC | §2 |
| 10 | Item def | CR-8 Table of contents | PC | §2 |
| 11 | Item def | IDA-3 Non-functional requirements | FC | Performance limits PF-01…PF-06 are stated; no availability or maintainability requirement is claimed |

Not on the list, because no judgement is needed:
- **NA:** CR-7 (header/footer) and CR-2 (template), since the xlsx is a generated view.
- **Nothing to rate yet:** VA-24…32 and VA-1…3, because no verification plan exists.
- **FC, mechanical:** CR-4a, CR-5 and IDA-7.
- **Already checked by `fmea_lint.py`:** VA-33e and FSA-21.

## 4. Offered, not done

The same checklist tool (`hara-checklist-reviewer`) can be run on the WP-C-03 workbook ([`WP-C-03-hara-cartesian.xlsx`](../../../02-concept/hara/WP-C-03-hara-cartesian.xlsx)). That is a reversible technical step. The HARA session can do it when the lead wants the reviews to start from the HARA of record rather than the second set.
