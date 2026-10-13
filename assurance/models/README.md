# Modelling plan

| Field | Value |
|---|---|
| What | Which open-source tools model which parts of LionDriver, and what their output may be used for |
| Status | Draft, AI-assisted (Claude), not reviewed |
| Decided | 2026-10-13, project maintainer, adopting Claude's recommendation ("yes" to the four questions in the modelling mockups) |
| Tool classification | [WP-P-07](../07-supporting/WP-P-07-tool-classification-qualification.md) (TL-25 Octave; OI-10 closed by this plan; OI-11) |

Nothing listed under "Planned" exists yet. No model output is verification evidence until the tool that produced it is classified at the confidence level the evidence needs (WP-P-07 §5) and the result has been reviewed.

## 1. Decisions

| ID | Question | Decision | Consequence |
|---|---|---|---|
| MD-01 | Which tool for which job? | **Python** for state machines and the back-to-back test (already in CI; the C harness `libsafety_py` is Python). **OpenModelica** only for the HIL plant model, run headless with `omc`, version pinned. **GNU Octave** for quick calculations and plots only (TL-25, no credit). Scilab/Xcos not adopted | OpenModelica must be classified before its first use (WP-P-07 OI-11) |
| MD-02 | Host state-machine transitions with no SWSR (SM-SELFDRIVED: engage, override, user disable) | Allowed as QM transitions, but each one must carry a written `qm_reason` that a reviewer accepts per transition. The checker must still fail on a transition with neither an SWSR nor a `qm_reason` | `check_state_machines.py` gains `qm_reason` support when SM-SELFDRIVED is added; until a reviewer accepts a reason, the transition counts as an open S4 finding, not as resolved |
| MD-03 | Should the back-to-back reference model follow the state-machine record or the C code? | The **record** (`sm-toy-auth.yaml`) | A divergence on a transition the C does not implement (T9, T10b, T10d, T10e, T12–T15) confirms an already-open SWSR; it is reported but is not a new defect. Any other divergence is a candidate finding |
| MD-04 | EPS torque lag for the plant model | Start with an **assumed value, marked as assumed** in the model and in every result that uses it; replace it with a value fitted from fork-owned Corolla logs when they exist (WP-W-06 OI-9) | Results from the assumed value can only be used to check the bench and the model, never as evidence about the vehicle |

## 2. Work items

| # | Item | Tool | State |
|---|---|---|---|
| 1 | Tool comparison | — | Done: this plan (MD-01) |
| 2 | SM-SELFDRIVED record (host state machine) | Python checker | Planned; needs `qm_reason` (MD-02) |
| 3 | Back-to-back test: Python model of `sm-toy-auth.yaml` vs C `libsafety` | Python | Planned; model follows the record (MD-03) |
| 4 | HIL plant model: Corolla EPS and vehicle lateral, closed loop, bench stage B3 | OpenModelica | Planned; blocked on WP-P-07 OI-11, assumed EPS lag (MD-04) |
| — | Envelope calculations and plots | Octave | Exists: [`octave/`](octave/README.md) |

Item 4 also has an open question: whether a soft real-time loop on the bench PC at 100 Hz is acceptable for stage B3. It is not decided by this plan.
