# TE-01 Tool evaluation — open-source modelling tools (Octave, Scilab/Xcos, OpenModelica, Python)

| Field | Value |
|---|---|
| Purpose | Input to [WP-P-07](../WP-P-07-tool-classification-qualification.md): which open-source tool to use for each LionDriver modelling use case, and how each tool in use would be classified |
| Status | Draft — **recommendation, not a decision**. AI-assisted (Claude), not reviewed. Proposed TL rows (§5) enter WP-P-07 only after a decision |
| Standard reference | ISO 26262-8:2018 §11 (TI, TD, TCL, qualification methods 1a–1d), applied as in WP-P-07 §2 |
| Date | 2026-10-13 |
| Baseline | Superproject branch `claude/modelling-b2b-toy-auth` (opendbc `7993399`, panda `8aa8671`) |

## 1. Why this exists

The question was whether open-source "MATLAB" could be used to create models and state machines. LionDriver does not generate production code from models ([WP-W-01](../../05-software/WP-W-01-software-development-environment-guidelines.md) §14). The envelope C is inherited and written by hand. Models are used only to describe, check and test, and any tool whose output is used as evidence has to be classified under WP-P-07.

This document compares the four candidates for the use cases LionDriver actually has (§2). It proposes classifications for the tools already in use (§5) and says what qualification would need. Versions and licences were looked up on 2026-10-13 (§8). No candidate other than Python was installed or run for this evaluation.

## 2. Use cases

| ID | Use case | Status | Output used for | Safety relevance of the output |
|---|---|---|---|---|
| U1 | State machines as data: YAML records, checker (S1–S6), generated WP-W-05 §5 tables and diagrams | In use (`assurance/trace/tools/check_state_machines.py`, CI) | Design description of the envelope (WP-W-05 §5); consistency findings against WP-W-02 | A wrong table or a missed S-check can hide a gap between design, requirement and code |
| U2 | Executable reference model, run back-to-back against the C | In use, not in CI ([`reference-models/`](../../05-software/reference-models/README.md)) | Divergence findings (B2B-01…03); potentially verification evidence for the SWSRs behind SM-TOY-AUTH | A false "agree" can fail to detect a code defect, if credit is claimed |
| U3 | Plant model for the HIL bench: Corolla EPS/steering and longitudinal | Planned ([HIL bench plan](../../05-software/hil-bench/README.md); no stage uses a closed-loop plant yet) | Stimulus and expected vehicle response in bench tests | A wrong plant can make a HIL verdict pass wrongly, if the verdict depends on plant states |
| U4 | Engineering calculations: limit derivations, timing budgets, rate budgets (e.g. DN-01 §4.1, timeout thresholds) | Done ad hoc, in Markdown with the arithmetic shown | Values in requirements, design notes and configuration data | A wrong value can enter a requirement; reviews and the code tests are the existing detection |
| U5 | Production code generation from models | **Not done** (WP-W-01 §14) | — | Out of scope. If ever proposed, the generator would be TI2 on the envelope and need qualification as a code generator; none of the candidates offers that (§3) |

## 3. Candidates

| Criterion | GNU Octave | Scilab / Xcos | OpenModelica | Python (CPython + libraries) |
|---|---|---|---|---|
| What it is | MATLAB-compatible numerical language | Numerical language plus Xcos block-diagram simulator | Modelica compiler and simulation environment (equation-based, multi-domain) | General-purpose language; numpy and sympy already locked, scipy is not |
| Latest version seen (§8) | 11.3.0 (1 June 2026) | 2026.1.0 (19 May 2026) | 1.26.1 (13 Jan 2026) per the official site; 1.27.1 per Wikipedia only, not confirmed | CPython 3.12.13 pinned in `.python-version`; numpy 2.5.3, sympy 1.14.0 in `uv.lock` |
| Licence | GPLv3+ | GPLv2 (CeCILL v2.1 still offered) | OSMC Public License with GPL and EPL options (component terms not checked) | PSF; numpy BSD-3; scipy BSD-3 |
| MATLAB compatibility | High for the language; **no Simulink or Stateflow** | Own syntax (similar but not compatible); Xcos is not Simulink | None (Modelica) | None |
| State machines | Hand-coded only | Xcos has no Stateflow equivalent | Modelica has state-machine constructs; no Stateflow-like editor or verifier | Hand-coded; records as data (U1) |
| Physical plant models | Hand-coded ODEs | Xcos blocks; Modelica blocks through an optional coupling | **Strongest**: acausal multi-domain libraries (Modelica Standard Library); FMU export | Hand-coded ODEs; integrators would need scipy, which is not in the lockfile |
| Code generation | None for models | Xcos code generator toolbox (ATOMS 0.9.201901, built up to Scilab 2024.0; 2026 support unverified), **not qualified** | C from Modelica; FMUs. Not qualified for production code | Not applicable (no model-to-code use) |
| Qualification kit | None known | None known | None known | None known. As with all in-house tools, 1c validation by the project (WP-P-07 TL-06 pattern) |
| CI fit (GitHub Actions, headless) | Distro packages or container images; headless CLI | Headless CLI available; heavier install | Container images or vendor apt repository; FMUs callable from Python | Already in CI, `uv` lockfile with hashes, same language as the checkers and the opendbc test harness |
| Reproducibility | Pin the version or container digest; no lockfile for Octave packages | Pin the version; ATOMS toolboxes are separate downloads | Pin the version and libraries; the compiler output depends on its version | Hash-pinned `uv.lock` (WP-P-07 TL-16) |
| Already in the repository | No | No | No | Yes |

## 4. Fit per use case

| Use case | Octave | Scilab/Xcos | OpenModelica | Python | Recommendation |
|---|---|---|---|---|---|
| U1 state machines as data | Possible, no benefit | Possible, no benefit | Possible, no benefit (the record must stay plain data) | **Fits**: in use, in CI, no new dependency | **Python** (keep) |
| U2 reference model, back-to-back | Possible, but cannot reuse the cffi/libsafety harness | Same | Not suitable: discrete event logic, not ODEs | **Fits**: drives libsafety directly; same packer and DBC as the unit tests | **Python** (keep) |
| U3 HIL plant | Fits for simple ODEs | Fits; Xcos adds a GUI dependency | **Best fidelity** for multi-domain (EPS motor, rack, tyres) | Fits for 1–2 DOF models; needs scipy | **Python first**, with a simple, reviewable model: column/rack inertia and a bicycle model; longitudinal point mass. **OpenModelica only** if bench tests need fidelity Python cannot give, run as an FMU from Python so the harness stays in one language |
| U4 calculations | Fits | Fits | Overkill | **Fits**: scripts in the repository, run in CI, reviewable | **Python**: a checked script per derived value (as `hara_model.py --check`) |

Not recommended:
- **Octave.** Its main advantage, MATLAB compatibility, has no use here: LionDriver has no MATLAB code, and Octave has no Simulink or Stateflow.
- **Scilab/Xcos.** It would add a third language. Its code generator is unqualified and unverified for the current release, and it has no advantage over Python or OpenModelica for any use case above.

## 5. Proposed classification (for decision, then WP-P-07 §3)

The rows follow WP-P-07 §2. "Credit" means that the output is used as evidence for a safety claim. TI depends on whether credit is claimed.

| Proposed ID | Tool | Use case | Target element | TI | TD | TCL | Rationale |
|---|---|---|---|---|---|---|---|
| TL-23 | `check_state_machines.py` (in-house, standard library, PyYAML optional) | U1 | Envelope design description (WP-W-05 §5) | TI2 | TD2 | **TCL2** | A false "consistent" (S1–S4) or a wrong generated table could hide a design gap. Partial detection: generated tables are diffed in git and read in review; S5/S6 compare against WP-W-02 independently of the record. Nothing else in the process detects a checker error, which is why TD is not TD1. The known-bad-record test suite (`test_check_state_machines.py`, §5 below) is validation evidence (1c), not a detection measure |
| TL-24 | SM-TOY-AUTH reference model and back-to-back harness (in-house, Python; uses cffi, `CANPacker`, DBC) | U2, **no credit** (current use: an additional measure that raises findings) | Envelope verification | TI1 | — | **TCL1** | No claim rests on an "agree". A divergence is a finding that a person checks against the code, so a false divergence costs time, not safety |
| TL-24 (if credit is claimed) | Same | U2, as evidence for the SWSRs behind SM-TOY-AUTH (WP-W-06) | Envelope verification | TI2 | TD2 | **TCL2** | Detection: seeded model faults on every `--all` run (8 of 8 detected, [B2B-TOY-AUTH-2026-10-13](../../05-software/reference-models/results/B2B-TOY-AUTH-2026-10-13.md) §4); the opendbc unit tests verify the same behaviour independently. Limits: `CANPacker` and the DBC are shared with the unit tests (common cause), and the model's author also wrote the specification (README §4) |
| TL-25 | Plant-model tool for the HIL bench: Python with scipy (proposed); OpenModelica only as in §4 | U3 | Envelope verification on the bench | TI2 if a HIL verdict depends on plant states; TI1 if verdicts are taken on envelope outputs (CAN frames, authority) only | TD2 | TCL2 / TCL1 | Design the bench tests so that verdicts are taken on envelope outputs, with the plant only shaping stimuli; then TI1. Where a verdict needs plant states (e.g. lateral acceleration reached), validate the plant against reference-car logs (TD2) |
| TL-26 | Calculation scripts (Python, in the repository, checked in CI) | U4 | Values in requirements and configuration data | TI2 | TD1 | **TCL1** | Each derived value is recomputed by the script and compared with the document (`--check`), and reviewed. That is an independent second calculation, which gives high detection |

**What qualification would need** (TCL2 rows, method 1c as for TL-06 and TL-07):

| Tool | Activities | Evidence |
|---|---|---|
| TL-23 | Test suite of known-bad records, one per check S1–S6, each of which must fail. Golden-file test of the generated §5 table and Mermaid diagram. Run it in CI. Review the checker as SR-T code. **Done (2026-10-13):** [`test_check_state_machines.py`](../../trace/tools/test_check_state_machines.py), 29 tests, run in the assurance workflow. All 15 checker faults planted by hand to check the tests (one or more per check, plus status, escaping, diagram and loader) made the suite fail. That check was run once and is not part of CI. Open: review as SR-T | TQR-23 |
| TL-24 (with credit) | Keep the mutant suite on every run and extend it to every guard and constant of the model. Run `--all` in CI with a pinned environment (**done**, without the pinned environment: the [`b2b` workflow](../../../.github/workflows/b2b.yaml) runs `--all --gate`, but `setup.sh` runs `uv sync` without `--frozen`, as the other opendbc jobs do). Independent (I1 or higher) review of the model against the SM record and the SWSRs, by someone other than its author. Record the shared `CANPacker`/DBC dependency as a known issue, and close it with one hand-packed frame per signal that checks the bit positions against the DBC independently | TQR-24 |
| TL-25 (if TI2) | Validate the plant against reference-vehicle logs (steering torque to angle, speed step response) with stated tolerances. Cross-check two integrators or step sizes. Pin the versions | TQR-25 |

Related tools outside this evaluation are not classified in WP-P-07 either: `check_trace.py`, `sync_requirements.py`, `check_links.py`, the `case/tools` scripts, `hara_model.py`, `fsc_model.py`. They need the same treatment; this is recorded as an open item.

## 6. Recommendation

1. Use **Python** for U1, U2 and U4. Do not adopt Octave or Scilab/Xcos.
2. Classify the current back-to-back run as an **additional measure with no credit** (TL-24, TCL1) until TQR-24 activities are done. It now runs in CI (`b2b` workflow), so the result is repeated on every change to the envelope or the SM record.
3. Treat `check_state_machines.py` as **TCL2** (TL-23) and add its known-bad-record test suite. It already produces the normative WP-W-05 §5 tables.
4. For the HIL plant (U3), start with a **Python** model. Design the bench verdicts on envelope outputs (TI1). Bring in **OpenModelica** (as an FMU) only for a demonstrated fidelity need.
5. Keep **no production code generation from models** (WP-W-01 §14). If that ever changes, it needs a new evaluation; none of the candidates has a qualified generator.

## 7. Decisions requested

| ID | Decision | Recommended |
|---|---|---|
| TE-01-D1 | Tool per use case (§4) | Python for U1, U2, U4; Python then OpenModelica for U3 |
| TE-01-D2 | Enter TL-23…TL-26 into WP-P-07 §3 as proposed in §5 | Yes |
| TE-01-D3 | Credit for the back-to-back run (TL-24) | Not now; additional measure until TQR-24 |
| TE-01-D4 | Classify the other in-house assurance scripts (§5, last paragraph) in a follow-up evaluation | Yes |

## 8. Sources (looked up 2026-10-13)

| Fact | Source |
|---|---|
| Octave 11.3.0, 1 June 2026 | <https://www.octave.org/news.html>; <https://en.wikipedia.org/wiki/GNU_Octave> |
| Scilab 2026.1.0, 19 May 2026, GPLv2 (formerly CeCILL) | <https://www.scilab.org/download>; <https://en.wikipedia.org/wiki/Scilab> |
| Xcos code generator toolbox 0.9.201901 | <https://atoms.scilab.org/toolboxes/xcos_code_generator/> |
| OpenModelica 1.26.1 (official), 1.27.1 (Wikipedia, unconfirmed); OSMC-PL / GPL / EPL | <https://openmodelica.org/>; <https://en.wikipedia.org/wiki/OpenModelica>; [OSMC 2026 workshop slides](https://openmodelica.org/images/M_images/OpenModelicaWorkshop_2026/OpenModelica2026-talk01-FrancescoCasella-OpenModelica-Workshop-StatusDirections-v1.pdf) |
| Python, numpy, sympy versions | `.python-version`, `uv.lock` in this repository |

The GPL licences of Octave and Scilab do not apply to their outputs (data, results) in normal use. The runtime code that OpenModelica bundles into generated FMUs has its own licence terms, which were not checked. Check them before an FMU is distributed.
