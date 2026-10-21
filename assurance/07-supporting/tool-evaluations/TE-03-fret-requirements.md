# TE-03 Tool evaluation and pilot plan — NASA FRET for structured, checkable safety requirements

| Field | Value |
|---|---|
| Purpose | Decide whether NASA FRET should restate the TSRs as structured requirements with a formal meaning, check them for conflicts, and feed runtime monitors (Ogma, Copilot); pilot on the panda TSRs |
| Status | Draft. Started on the lead's go (2026-10-21): P1 and P2 done ([`assurance/models/fret/`](../../models/fret/README.md)); P3 to P5 open. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Standard reference | ISO 26262-8:2018 §6 (specification of safety requirements: unambiguous, verifiable, consistent) and §11 (tool classification), applied as in [WP-P-07](../WP-P-07-tool-classification-qualification.md) §2 |
| Date | 2026-10-21 |
| Baseline | `liondriver-dev` with panda `f4803c5` and opendbc `4d1a056` |
| Related | [WP-S-02](../../03-system/WP-S-02-technical-safety-requirements.md), [WP-S-04](../../03-system/WP-S-04-timing-ftti-budget.md), [TE-02](TE-02-fmdtools-fault-propagation.md) |

## 1. Why

The TSRs are English sentences. ISO 26262-8 §6 asks that safety requirements be unambiguous, verifiable and consistent with each other, and today only review checks that. Writing a requirement in a restricted grammar with a defined temporal meaning makes three things checkable:

- **Ambiguity:** each word has to become a variable, a trigger or a time bound, so a gap in the text shows at once.
- **Text against code:** each variable is mapped to the signal in the code that implements it, so a requirement that says something other than the code does shows up.
- **Consistency:** FRET can check whether a set of requirements can be met together (realizability, with the Kind 2 or JKind solvers) and can generate tests from them.

The same structured requirements are the input to Ogma, which generates Copilot runtime monitors in C99. That is the route to monitors on the panda (survey of 2026-10-21, pilot order 2).

## 2. The tool

| Item | Finding |
|---|---|
| What | [NASA-SW-VnV/fret](https://github.com/NASA-SW-VnV/fret): requirements in "FRETish" (restricted English: scope, condition, component, shall, timing, response), formalised into past- and future-time metric temporal logic, with diagrams, realizability checks and test generation |
| Version and licence | v3.1 (README badge); the source used here is commit `cf0f913` (2026-04-10). Apache-2.0 (`LICENSE.pdf`; the grammar header says the same). Used as a tool; no FRET code enters the repository |
| Runs headless | Yes, through its command-line interface (`formalize`, `realizability`, `list`); checked 2026-10-21 with Node.js 22.22.0. [`install_fret.sh`](../../models/fret/install_fret.sh) fetches the pinned commit, installs the npm packages without install scripts and without Electron, and builds the CLI in about 40 s. Two quirks: npm 10 rejects FRET's old-style `devEngines` field (dropped in the local copy), and the CLI keeps a database under `$HOME/Documents` (a temporary home is used) |
| Other dependencies | Node.js 22 (pinned in CI) and FRET's npm tree (about 3,700 packages, locked by FRET's own lockfiles); Kind 2 or JKind for realizability; none for `formalize` |

## 3. Pilot scope: the panda TSRs

The panda (safety MCU) TSRs were chosen because they are the ASIL C mechanisms, they have precise timing (100 Hz task), and their code is small enough to map every variable to a signal. The first set, P1, restates 6 TSRs as 11 FRETish requirements: TSR-101, TSR-103 (three parts), TSR-110, TSR-307(a), TSR-407 and TSR-516 ((a) in two parts, (b), (c)). Time is in ticks of the safety task, 1 tick = 10 ms.

## 4. Steps

| Step | Work | Output | Done when |
|---|---|---|---|
| P1 Restate | Write the FRETish, a glossary mapping every variable to the code, and the findings; a checker for grammar shape, glossary and source drift, in CI | [`tsr-fretish.yaml`](../../models/fret/tsr-fretish.yaml), [`check_fretish.py`](../../models/fret/check_fretish.py) and its page | **Done** 2026-10-21: 11 requirements, 6 findings (§5) |
| P2 Formalise | Run FRET `formalize` on every sentence; store the past-time and future-time formulas next to the FRETish; CI checks that each stored formula belongs to the current sentence | [`fretish-formalizations.json`](../../models/fret/fretish-formalizations.json), FRET commit pinned | **Done** 2026-10-21: FRET parses all 11; CI reruns FRET and compares. The formulas are AI-reviewed against the TSR text, not yet by a person |
| P3 Realizability | Check the set with Kind 2 or JKind through the FRET CLI | A realizability report | Every conflict is named, or the set is realizable |
| P4 Monitor | One TSR (TSR-307(a) proposed) through Ogma to a Copilot C99 monitor, run first against the plant model's traces | A monitor and its trace verdicts | The monitor agrees with the plant on the engaged-mismatch runs; the licence of the generated code is settled before it goes near the firmware |
| P5 Decide | Extend to the SoC TSRs and the FSRs, or stop | A decision note | The lead has the result |

## 5. P1 result

Writing the 11 sentences found 6 points to route to the WP-S-02 owner ([page](../../models/fret/fretish-requirements.md)):

| ID | TSR | Finding |
|---|---|---|
| FF-01 | TSR-103 | The text rejects a decrease of more than Δ_down; the code never rejects a move toward zero, and uses Δ_down as the least descent when the command exceeds the measured torque |
| FF-02 | TSR-103 | "Any 250 ms window" (sliding) against restarting windows in the code; not binding at the baseline |
| FF-03 | TSR-307(a) | The text revokes on any "not engaged" heartbeat; the code only if it persists to 0.3 s |
| FF-04 | TSR-516 | The general ≤ 0.5 s after detection conflicts with the EPS-fault clause (detection at the first fault frame, persistence up to 0.7 s); read literally, the reference build violates it |
| FF-05 | TSR-516 | No minimum siren duration or loudness: a 10 ms pulse meets the text |
| FF-06 | TSR-516(c) | The code fires at 0.49 s, the text's guard is "more than 0.5 s"; errs toward warning |

None asks the lead for a decision: each is a rewording, or a code change, inside an intent already decided (FF-04: DQ-048).

P2 result (2026-10-21): FRET parses and formalises all 11 sentences, and gives the same formulas on every run. One limit for P3: in the future-time formulas FRET leaves the past-time predicates (`persisted`, `occurred`, `preBool`) as named macros, so FR-407, FR-516a1 and FR-516a2 need them expanded, or restated without them, before a realizability check.

## 6. What the pilot is not

- **Not evidence.** The FRETish restates the TSRs; WP-S-02 stays the source of record. A finding changes a TSR only after its owner reviews it.
- **Not a proof about the code.** The formulas give each TSR a precise meaning. Whether the code meets them is P4's question (monitors on plant traces).

## 7. Tool classification (proposed, for WP-P-07)

**TI1 while no credit is claimed.** An error in FRET or in the checker can only miss a gap that review of WP-S-02 would also have to find; nothing is released on its output. TCL1, no qualification. If realizability results or Ogma monitors are ever credited (P3, P4), the classification is redone: a monitor in the firmware is product code, not a tool output, and falls under the software process.

## 8. Owners and coordination

| Who | Role |
|---|---|
| FTA session (drafting) | Runs P1 to P3; keeps this plan current |
| WP-S-02 owner | Receives FF-01 to FF-06; owns any TSR change |
| Simulation session | Supplies plant traces for P4 |
| Coordinator | Keeps TL-50 in WP-P-07 current; merges on full green |

## 9. Open items

| ID | Item |
|---|---|
| OI-1 | ~~Run FRET (CLI, commit `cf0f913`)~~ **Closed** 2026-10-21: the lead approved the install; FRET runs in CI (P2) |
| OI-2 | ~~Classify FRET and `check_fretish.py` in WP-P-07~~ **Closed** 2026-10-21: TL-50, TCL1 |
| OI-3 | Settle the licence of Ogma's generated monitor code before P4 output goes near the firmware |
