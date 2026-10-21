# FRET structured requirements

| Field | Value |
|---|---|
| Plan | [TE-03](../../07-supporting/tool-evaluations/TE-03-fret-requirements.md) (pilot on the panda TSRs) |
| Tool | [NASA FRET](https://github.com/NASA-SW-VnV/fret) v3.1 (source `cf0f913`), Apache-2.0; its CLI runs in CI |
| Status | Steps P1 and P2 done: 13 FRETish requirements for 6 TSRs, formalised by FRET; 7 findings, all fixed in WP-S-02 v0.53. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Evidence | **None.** WP-S-02 stays the source of record |

## What is here

| Path | Content |
|---|---|
| [`tsr-fretish.yaml`](tsr-fretish.yaml) | The source: a glossary that maps every variable to its signal in the code, the FRETish requirements with the TSR text each restates, and the findings |
| [`check_fretish.py`](check_fretish.py) | Checks that each quoted TSR text is still in WP-S-02, that each sentence has the shape of FRET's grammar (`Requirement.g4`), that every variable is in the glossary and none is a FRET keyword, and that findings are cited; writes [`fretish-requirements.md`](fretish-requirements.md). `--check` in CI |
| [`test_check_fretish.py`](test_check_fretish.py) | The real file passes; a reworded TSR, an unknown variable, a keyword, a bad time unit, an unbalanced expression, a missing finding and a sentence without its formula each fail |
| [`install_fret.sh`](install_fret.sh) | Fetches FRET at the pinned commit and builds its CLI (about 40 s; Node.js 22) |
| [`fret_formalize.py`](fret_formalize.py) | Runs FRET `formalize` on every sentence and writes [`fretish-formalizations.json`](fretish-formalizations.json) (past-time and future-time formulas); `--check` in CI reruns FRET and compares |

## How to read a requirement

    upon authority_granted & !hb_engaged the envelope shall within 30 ticks satisfy !authority_granted

*Upon* is a trigger: the response is due once each time the condition becomes true. *Whenever* is a holding condition: the response is due at every tick the condition holds. Time is in ticks of the panda safety task, 1 tick = 10 ms. The glossary says what each variable is in the code: here `hb_engaged` is the engaged flag of the last heartbeat (`heartbeat_engaged` in `main.c`).

    python3 -m pip install -r assurance/models/fret/requirements.txt
    python3 assurance/models/fret/check_fretish.py           # check and regenerate the page
    python3 assurance/models/fret/check_fretish.py --check   # fail if a check fails or the page is stale
    python3 assurance/models/fret/test_check_fretish.py
    assurance/models/fret/install_fret.sh .fret                                          # FRET CLI
    FRET_DIR=.fret/fret-electron python3 assurance/models/fret/fret_formalize.py          # store FRET's formulas

When a TSR in WP-S-02 is reworded, the check fails on its entry: review the FRETish against the new text, then update the quote. When a sentence changes, rerun `fret_formalize.py`.

## Findings

[`fretish-requirements.md`](fretish-requirements.md) lists the seven findings with their evidence. TSR-103's rate and window rules differed from the code (FF-01, FF-02, FF-07); TSR-307(a) did not say the "not engaged" report must persist (FF-03); TSR-516's 0.5 s bound contradicted its own EPS-fault clause (FF-04), it set no siren duration (FF-05), and its (c) guard was 10 ms longer than the code's (FF-06). The WP-S-02 owner fixed all seven in v0.53 (#391), with no change to the code.
