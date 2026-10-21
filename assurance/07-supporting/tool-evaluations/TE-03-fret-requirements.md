# TE-03 Tool evaluation and pilot plan — NASA FRET for structured, checkable safety requirements

| Field | Value |
|---|---|
| Purpose | Decide whether NASA FRET should restate the TSRs as structured requirements with a formal meaning, check them for conflicts, and feed runtime monitors (Ogma, Copilot); pilot on the panda TSRs |
| Status | Draft. Started on the lead's go (2026-10-21): P1 to P4 done ([`assurance/models/fret/`](../../models/fret/README.md)); P5 open. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
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
| Other dependencies | Node.js 22 (pinned in CI) and FRET's npm tree (about 3,700 packages, locked by FRET's own lockfiles); for realizability Kind 2 v2.2.0 (Apache-2.0; FRET does not support v2.3.0) and Z3 4.14.1 (MIT), fetched by [`install_solvers.sh`](../../models/fret/install_solvers.sh) and checked by SHA-256 |

## 3. Pilot scope: the panda TSRs

The panda (safety MCU) TSRs were chosen because they are the ASIL C mechanisms, they have precise timing (100 Hz task), and their code is small enough to map every variable to a signal. The first set, P1, restates 6 TSRs as 13 FRETish requirements: TSR-101, TSR-103 (three parts), TSR-110, TSR-307(a), TSR-407 and TSR-516 ((a) in two parts, (b), (b) on an EPS fault, (c) and the siren duration). Time is in ticks of the safety task, 1 tick = 10 ms.

## 4. Steps

| Step | Work | Output | Done when |
|---|---|---|---|
| P1 Restate | Write the FRETish, a glossary mapping every variable to the code, and the findings; a checker for grammar shape, glossary and source drift, in CI | [`tsr-fretish.yaml`](../../models/fret/tsr-fretish.yaml), [`check_fretish.py`](../../models/fret/check_fretish.py) and its page | **Done** 2026-10-21: 13 requirements (11 at first, 2 added for the v0.53 wording), 7 findings (§5) |
| P2 Formalise | Run FRET `formalize` on every sentence; store the past-time and future-time formulas next to the FRETish; CI checks that each stored formula belongs to the current sentence | [`fretish-formalizations.json`](../../models/fret/fretish-formalizations.json), FRET commit pinned | **Done** 2026-10-21: FRET parses all 13; CI reruns FRET and compares. The formulas are AI-reviewed against the TSR text, not yet by a person |
| P3 Realizability | Check the set with Kind 2, built the way FRET's own check builds it; find every minimal conflicting set | [`fret-realizability.md`](../../models/fret/fret-realizability.md) and the Lustre contracts | **Done** 2026-10-21: two components realizable; the torque-limit component unrealizable, 2 minimal conflicts (FF-08) |
| P4 Monitor | TSR-307(a), TSR-516(c) and the TSR-516 siren duration through Ogma to a Copilot C99 monitor, run against the panda's own code in a harness, with mutants it must catch | [`monitor/monitor-results.md`](../../models/fret/monitor/monitor-results.md) | **Done** 2026-10-21: no violation by the pinned code in 6 scenarios (about 180 revocations and 130 siren starts); all 3 mutants caught by the requirement they break. Plant traces are not used yet (the plant needs opendbc's Python modules in the job) |
| P5 Decide | Extend to the SoC TSRs and the FSRs, or stop | A decision note | The lead has the result |

## 5. P1 result

Writing the sentences found 7 points, routed to the WP-S-02 owner ([page](../../models/fret/fretish-requirements.md)). The owner confirmed all 7 against the code and fixed the text in WP-S-02 v0.53 (#391), with no change to the code; FF-07 came from formalising the first rewording, before it merged. The CI check then failed on the five reworded entries, as designed, and the FRETish now restates v0.53:

| ID | TSR | Finding |
|---|---|---|
| FF-01 | TSR-103 | The text rejects a decrease of more than Δ_down; the code never rejects a move toward zero, and uses Δ_down as the least descent when the command exceeds the measured torque |
| FF-02 | TSR-103 | "Any 250 ms window" (sliding) against restarting windows in the code; not binding at the baseline |
| FF-03 | TSR-307(a) | The text revokes on any "not engaged" heartbeat; the code only if it persists to 0.3 s |
| FF-04 | TSR-516 | The general ≤ 0.5 s after detection conflicts with the EPS-fault clause (detection at the first fault frame, persistence up to 0.7 s); read literally, the reference build violates it |
| FF-05 | TSR-516 | No minimum siren duration or loudness: a 10 ms pulse meets the text |
| FF-06 | TSR-516(c) | The code fires at 0.49 s, the text's guard is "more than 0.5 s"; errs toward warning |
| FF-07 | TSR-103 | The first rewording still differed: both checks are sign-aware in the code, allowing [min(r, 0) − Δ, max(r, 0) + Δ] |

None asked the lead for a decision: each was a rewording inside an intent already decided (FF-04: DQ-048). The audibility level of TSR-516 is not formalised: it is set by measurement (WP-S-04 M-05).

P2 result (2026-10-21): FRET parses and formalises all 13 sentences, and gives the same formulas on every run. One limit for P3: in the future-time formulas FRET leaves the past-time predicates (`persisted`, `occurred`, `preBool`) as named macros, so FR-307a, FR-407, FR-516a1, FR-516a2 and FR-516b-eps need them expanded, or restated without them, before a realizability check. FRET's bounds are inclusive (`persisted(n, p)` and "for n ticks" cover n + 1 samples), so durations are written one tick short; the YAML header states the convention.

P3 result (2026-10-21, [`fret-realizability.md`](../../models/fret/fret-realizability.md)). The FRET CLI checks realizability only for a project in its own database, and its import expects requirements FRET has already parsed. So [`fret_realizability.py`](../../models/fret/fret_realizability.py) builds the contract the way FRET's check does: FRET's own Lustre form of each requirement (`CoCoSpecCode`), inputs and outputs from a `role` per glossary variable, one contract per connected component (FRET's compositional analysis), FRET's Kind 2 template rendered by FRET's EJS engine, and `kind2 --enable CONTRACTCK`. One change is needed: Kind 2 v2.2.0 stops with an internal assertion when an `assume` names a ghost variable, so each assumption's formula is written into its `assume` clause. For an unrealizable component, the script finds every minimal conflicting set by deletion. To run the check, P3 adds:
- TSR-103's "any change toward zero is accepted" (FR-103d);
- TSR-104 (FR-104);
- four assumptions that fix the baseline constants and say that r is 0 or a frame that passed TSR-101 and the window check.

Result:
- the authority and siren component (8 requirements) is realizable, and so is TSR-407;
- the torque-limit component is unrealizable, with two minimal conflicts: {FR-103b, FR-103d} and {FR-103d, FR-104}.

TSR-103 says any change toward zero is accepted, but above the measured torque plus Δ_meas a frame must fall by at least Δ_down (TSR-103) and is rejected outright (TSR-104). The code follows neither text: it accepts a fall of at least Δ_down and rejects a smaller one (FF-08, routed to the WP-S-02 owner). The tests check a single rule (realizable), the known conflict, and a conflict injected on purpose (a rule that never rejects, against TSR-101).

A realizable result means only that the requirements can be met together. It does not mean the set is complete: the authority and siren component holds trivially (sound the siren, revoke authority), because no requirement in it limits false alarms.

P4 result (2026-10-21, [`monitor-results.md`](../../models/fret/monitor/monitor-results.md)). [`run_monitor.py`](../../models/fret/monitor/run_monitor.py) runs the whole chain:
- writes FRET's past-time formulas for FR-307a, FR-516c and FR-516-duration as a FRET component specification ([`monitor-spec.json`](../../models/fret/monitor/monitor-spec.json));
- Ogma 1.16.0 (`standalone --input-format fcs`) turns it into a Copilot program, and Copilot 4.8.1 generates a C99 monitor;
- [`harness.c`](../../models/fret/monitor/harness.c) compiles the monitor with the pinned panda `engaged_mismatch.h` and `heartbeat_siren.h`, and runs them in the order of `safety_task_handler()`, 100 Hz tick by tick.

The harness computes `not_engaged_ticks` from its glossary definition rather than reading the code's counter, and revokes authority when PCM cruise drops (TSR-301), as the safety mode does. There are four scripted scenarios (selfdrived stop, a disengagement with an ACC cancel, a single not-engaged heartbeat, 0.25 s not engaged) and two seeded random ones of 2,000 s each.

Result: the pinned code violates none of the three. Each of the three mutants (revocation at 0.45 s, siren at 1.2 s, siren held 2 s) is reported by exactly the requirement it breaks.

The first run found a formalisation error, not a code error. FR-516c fired when PCM cruise dropped during a not-engaged episode and came back while the heartbeat still said "not engaged". TSR-516(c) asks for the siren only if cruise is *still* active 0.5 s after the first not-engaged heartbeat, and the code is silent in that case, correctly. FR-516c now reads `not_engaged_ticks = 50 & persisted(49, pcm_cruise_active)`.

The generated C is built on the fly and never committed (OI-3).

## 6. What the pilot is not

- **Not evidence.** The FRETish restates the TSRs; WP-S-02 stays the source of record. A finding changes a TSR only after its owner reviews it.
- **Not a proof about the code.** The formulas give each TSR a precise meaning. Whether the code meets them is P4's question (monitors on plant traces).

## 7. Tool classification (proposed, for WP-P-07)

**TI1 while no credit is claimed.** An error in FRET or in the checker can only miss a gap that review of WP-S-02 would also have to find; nothing is released on its output. TCL1, no qualification. If realizability results or Ogma monitors are ever credited (P3, P4), the classification is redone: a monitor in the firmware is product code, not a tool output, and falls under the software process.

## 8. Owners and coordination

| Who | Role |
|---|---|
| FTA session (drafting) | Ran P1 to P4; keeps this plan current |
| WP-S-02 owner | Received FF-01 to FF-07 and fixed them in v0.53; owns any TSR change |
| Simulation session | Supplies plant traces for P4 |
| Coordinator | Keeps TL-51 in WP-P-07 current; merges on full green |

## 9. Open items

| ID | Item |
|---|---|
| OI-1 | ~~Run FRET (CLI, commit `cf0f913`)~~ **Closed** 2026-10-21: the lead approved the install; FRET runs in CI (P2) |
| OI-2 | ~~Classify FRET and `check_fretish.py` in WP-P-07~~ **Closed** 2026-10-21: TL-51, TCL1 |
| OI-3 | Settle the licence of Ogma's generated monitor code before any of it goes near the firmware. P4 avoids the question: the generated C is built in CI and not committed |
| OI-4 | Run the P4 monitor on the plant's engaged-mismatch traces as well (the plant job has opendbc's Python modules) |
