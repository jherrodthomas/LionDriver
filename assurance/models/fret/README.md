# FRET structured requirements

| Field | Value |
|---|---|
| Plan | [TE-03](../../07-supporting/tool-evaluations/TE-03-fret-requirements.md) (pilot on the panda TSRs) |
| Tool | [NASA FRET](https://github.com/NASA-SW-VnV/fret) v3.1 (source `cf0f913`), Apache-2.0; not yet run (TE-03 OI-1) |
| Status | Step P1 done: 11 FRETish requirements for 6 TSRs, 6 findings. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Evidence | **None.** WP-S-02 stays the source of record |

## What is here

| Path | Content |
|---|---|
| [`tsr-fretish.yaml`](tsr-fretish.yaml) | The source: a glossary that maps every variable to its signal in the code, the FRETish requirements with the TSR text each restates, and the findings |
| [`check_fretish.py`](check_fretish.py) | Checks that each quoted TSR text is still in WP-S-02, that each sentence has the shape of FRET's grammar (`Requirement.g4`), that every variable is in the glossary and none is a FRET keyword, and that findings are cited; writes [`fretish-requirements.md`](fretish-requirements.md). `--check` in CI |
| [`test_check_fretish.py`](test_check_fretish.py) | The real file passes; a reworded TSR, an unknown variable, a keyword, a bad time unit, an unbalanced expression and a missing finding each fail |

## How to read a requirement

    upon authority_granted & !hb_engaged the envelope shall within 30 ticks satisfy !authority_granted

*Upon* is a trigger: the response is due once each time the condition becomes true. *Whenever* is a holding condition: the response is due at every tick the condition holds. Time is in ticks of the panda safety task, 1 tick = 10 ms. The glossary says what each variable is in the code: here `hb_engaged` is the engaged flag of the last heartbeat (`heartbeat_engaged` in `main.c`).

    python3 -m pip install -r assurance/models/fret/requirements.txt
    python3 assurance/models/fret/check_fretish.py           # check and regenerate the page
    python3 assurance/models/fret/check_fretish.py --check   # fail if a check fails or the page is stale
    python3 assurance/models/fret/test_check_fretish.py

When a TSR in WP-S-02 is reworded, the check fails on its entry: review the FRETish against the new text, then update the quote.

## Findings

[`fretish-requirements.md`](fretish-requirements.md) lists the six findings with their evidence. In short: TSR-103's down-rate rule and window differ from the code (FF-01, FF-02); TSR-307(a) does not say the "not engaged" report must persist (FF-03); TSR-516's 0.5 s bound contradicts its own EPS-fault clause (FF-04), it sets no siren duration (FF-05), and its (c) guard is 10 ms longer than the code's (FF-06). They go to the WP-S-02 owner.
