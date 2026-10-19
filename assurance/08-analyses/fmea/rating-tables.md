# LionDriver — FMEA Rating Tables

**Version:** RT-3 (referenced by `rating_tables` in every analysis file). RT-3 (2026-10-19) replaces the provisional §7.4 MSR action priority for S 9–10 with the AIAG-VDA handbook table (DQ-207 A). RT-2 added §7 (FMEA-MSR); §1–§6 are unchanged from RT-1.
**S/O/D unchanged since:** RT-1
**Basis:** AIAG & VDA FMEA Handbook (2019), tailored. Criteria are paraphrased; consult the handbook for the normative wording.
**Applies to:** System FMEA, DFMEA, SW FMEA, PFMEA. FMEDA uses §6. FMEA-MSR (§7) applies to the System FMEA and DFMEA only.

Any change to these tables increments the version (RT-3, …) and triggers re-rating of affected rows. A file rated against the version named in "S/O/D unchanged since" needs no re-rating until it adds rows from a later section; a file with FMEA-MSR rows must name the current version (checked by the linter).

---

## 1. Severity (S) — System FMEA, DFMEA, SW FMEA

Severity is rated on the **end effect** (vehicle / driver / other road users). A failure mode's severity is the highest severity of its effects.

| S | Criterion (AIAG-VDA, paraphrased) | LionDriver tailoring and examples |
|---|---|---|
| 10 | Affects safe operation of the vehicle or the health of occupants or other road users | **Any effect traced to a HARA hazardous event (S1–S3).** E.g. steering torque beyond limits; control not released on driver brake; stock AEB unavailable because the harness intercepts the camera. |
| 9 | Noncompliance with regulations | Violates a legal/regulatory requirement (FMVSS, privacy law) with no traced hazard. E.g. driver camera recorded or uploaded contrary to the user's consent setting. |
| 8 | Loss of primary vehicle function needed for normal driving | Loss of ALC or ACC **with** a correct alert and a controlled handback to the driver. |
| 7 | Degradation of primary vehicle function | ALC/ACC available but degraded within actuator limits (e.g. lane ping-pong, late but bounded lead response). |
| 6 | Loss of secondary function | Loss of features not needed for control: navigation display, logging, upload, settings. |
| 5 | Degradation of secondary function | Slow UI, partial log loss, delayed upload. |
| 4 | Very objectionable appearance, sound, vibration, harshness or haptics | Persistent false alerts; harsh but in-limit steering feel. |
| 3 | Moderately objectionable | Occasional false alert; noticeable UI glitch. |
| 2 | Slightly objectionable | Cosmetic UI issue noticed by few drivers. |
| 1 | No discernible effect | — |

### 1.1 HARA → Severity mapping

| HARA severity | FMEA severity |
|---|---|
| S3, S2, S1 (any hazardous event with ASIL A–D or QM-rated but S ≥ 1) | **10** |
| S0 | Rate using rows 1–9 above |

The linter enforces: an effect with a `hazard` link and a severity must have severity 10.

---

## 2. Occurrence (O)

Occurrence rates how likely the **cause** is, given the **prevention controls** in place. It is not a field failure rate.

### 2.1 Occurrence — DFMEA (hardware) and System FMEA

| O | Criterion (AIAG-VDA, paraphrased) |
|---|---|
| 10 | New technology with no operating experience; no standards or best practices; no prevention controls, or none that predict field performance. |
| 9 | First use within the project of a design with technical innovations or materials; new application or duty cycle; no verification or validation experience. |
| 8 | First use of an innovative design on a new application; few applicable standards; prevention controls not a reliable indicator of field performance. |
| 7 | New design based on similar technology; standards apply to the baseline design but not the innovations; prevention controls give limited indication of performance. |
| 6 | Similar to previous designs with existing technology; changed duty cycle or conditions; standards exist but are insufficient to ensure the cause won't occur. |
| 5 | Detail changes to a proven design; previous test or field experience related to the cause; prevention controls can find deficiencies. |
| 4 | Almost identical design with short-term field exposure; conforms to best practices and standards; prevention controls indicate likely conformance. |
| 3 | Detail changes to a known design with comparable test/field experience, or new design with a successfully completed test procedure. |
| 2 | Almost identical mature design with long-term field exposure; conformance expected with considerable margin. |
| 1 | Cause is eliminated by prevention control; not possible by design. |

### 2.2 Occurrence — SW FMEA (systematic faults)

Tailored to the software prevention controls actually available in this repo (review, `ruff`/`ty`, MISRA C on safety C code, unit/requirements-based tests, coverage).

| O | Prevention controls in place for the element containing the cause |
|---|---|
| 10 | None. New code, no review, no coding standard, no requirements. |
| 9 | New code or algorithm; informal review only; no coding standard applied. |
| 8 | New code; documented review; no static analysis; requirements not documented. |
| 7 | New or modified code based on a similar design; reviewed; static analysis/lint applied; requirements partially documented. |
| 6 | Similar to field-proven code but with changed operating conditions (car, rate, inputs); review + lint; unit tests exist but are not requirements-based. |
| 5 | Detail changes to field-proven code; review, lint, unit tests exercising the element; known issues of predecessor addressed. |
| 4 | Almost identical to field-proven code with short exposure on this configuration; requirements-based tests; MISRA C (C) or typed + linted (Python) with deviations recorded. |
| 3 | Minor changes to mature code with comparable exposure; requirements-based tests with structural coverage measured. |
| 2 | Mature, unchanged code with long exposure on this configuration; full requirements and coverage evidence (e.g. MC/DC for safety C code). |
| 1 | Cause cannot occur by construction (enforced by type system, hardware, or architecture). |

**Field exposure** credit (O ≤ 6) is allowed only for code identical to what was exposed, on the same vehicle configuration, with the evidence cited in the prevention control (`ref`). Upstream comma.ai fleet experience is not credited without that evidence.

---

## 3. Detection (D) — System FMEA, DFMEA, SW FMEA

Detection rates the ability of the **detection controls** to find the failure mode or cause **before the configuration is released**. Field diagnostics that act while driving are safety mechanisms; they reduce severity or occurrence through the design, not D.

Terms used below:
- **Proven:** the test has been shown to fail on an injected instance of this failure mode or cause (fault injection, mutation, or a reproduced past defect). Evidence goes in the control's `ref`.
- **Early:** runs as a blocking gate on every change (PR CI). For hardware: completed before the HW baseline is frozen.
- **Late:** runs only pre-release, on HIL, or in-vehicle.
- **Test type:** pass-fail < test-to-fail (boundary, fault injection, fuzzing) < degradation (long-run replay, soak).

| D | Criterion |
|---|---|
| 10 | No test method defined. |
| 9 | A test exists but is not designed to detect this failure mode or cause (e.g. generic smoke test). |
| 8 | New test method targeted at this failure mode; not proven. |
| 7 | Proven, late, pass-fail. |
| 6 | Proven, late, test-to-fail. |
| 5 | Proven, late, degradation. |
| 4 | Proven, early, pass-fail. |
| 3 | Proven, early, test-to-fail. |
| 2 | Proven, early, degradation (e.g. `process_replay` over a route corpus as a CI gate). |
| 1 | Prior testing confirms the failure mode cannot occur, or the method is proven to always detect it (exhaustive or formal). |

Every detection control rated D ≤ 8 must name a `test` path that exists in the repo (or in a pinned submodule).

---

## 4. PFMEA

"Process" = build & release → provisioning & install → in-vehicle installation → calibration → OTA → car fingerprinting (see `fmea-plan.md` §3.4).

Effect levels for PFMEA map onto the schema's `local / next_higher / end` as: **local** = build/release pipeline, **next_higher** = installer / device, **end** = vehicle operation.

### 4.1 Severity — PFMEA

| S | Criterion |
|---|---|
| 10 | Deployed configuration can produce a hazardous event (traced to HARA), or installer is exposed to a health hazard. |
| 9 | Deployed configuration violates a regulation, or an unassured configuration is deployed without the user being told. |
| 8 | Deployed configuration loses ALC/ACC (with correct alert); or the whole release must be withdrawn. |
| 7 | Deployed configuration degrades ALC/ACC; or a subset of devices must be re-installed. |
| 6 | Release must be rebuilt and redistributed before deployment (caught before reaching users). |
| 5 | Part of the release must be rebuilt before deployment. |
| 4 | Rework in the pipeline; release delayed > 1 day. |
| 3 | Rework in the pipeline; minor delay. |
| 2 | Slight inconvenience to the process or installer. |
| 1 | No discernible effect. |

### 4.2 Occurrence — PFMEA

| O | Prevention controls |
|---|---|
| 10 | None. |
| 9 | Behavioral, undocumented (relies on individual knowledge). |
| 8 | Behavioral, documented instruction exists but is not used as a checklist. |
| 7 | Behavioral, checklist used and recorded. |
| 6 | Technical control (script/tool) newly introduced, not yet proven. |
| 5 | Technical control, proven, but can be bypassed. |
| 4 | Technical control enforced by CI/tooling, cannot be bypassed without a recorded override. |
| 3 | Enforced technical control + best practice (lockfiles, pinned submodules, reproducible build). |
| 2 | Enforced technical control + best practice + cryptographic integrity (signed artifacts, verified on install). |
| 1 | Error-proofed: the cause cannot occur by design of the process. |

### 4.3 Detection — PFMEA

| D | Detection controls |
|---|---|
| 10 | None; failure not detected before it reaches the vehicle. |
| 9 | Not easily detected; random audit only. |
| 8 | Human inspection (visual/audible), method not proven. |
| 7 | Automated check, method not proven. |
| 6 | Human inspection with a proven checklist/method. |
| 5 | Automated check, proven, at a later station (e.g. pre-release). |
| 4 | Automated check, proven, that blocks the release/install from proceeding. |
| 3 | Automated check at the step itself, blocks it immediately. |
| 2 | Cause detected (not just failure mode) and step blocked automatically. |
| 1 | Error-proofing makes the failure impossible to produce. |

---

## 5. Action Priority (AP)

Same table for all four FMEA types (AIAG-VDA 2019). Columns are Detection bands.

| S | O | D 7–10 | D 5–6 | D 2–4 | D 1 |
|---|---|---|---|---|---|
| 9–10 | 8–10 | H | H | H | H |
| 9–10 | 6–7 | H | H | H | H |
| 9–10 | 4–5 | H | H | H | M |
| 9–10 | 2–3 | H | M | L | L |
| 9–10 | 1 | L | L | L | L |
| 7–8 | 8–10 | H | H | H | H |
| 7–8 | 6–7 | H | H | H | M |
| 7–8 | 4–5 | H | M | M | M |
| 7–8 | 2–3 | M | M | L | L |
| 7–8 | 1 | L | L | L | L |
| 4–6 | 8–10 | H | H | M | M |
| 4–6 | 6–7 | M | M | M | L |
| 4–6 | 4–5 | M | L | L | L |
| 4–6 | 2–3 | L | L | L | L |
| 4–6 | 1 | L | L | L | L |
| 2–3 | 8–10 | M | M | L | L |
| 2–3 | 6–7 | L | L | L | L |
| 2–3 | 4–5 | L | L | L | L |
| 2–3 | 2–3 | L | L | L | L |
| 2–3 | 1 | L | L | L | L |
| 1 | 1–10 | L | L | L | L |

**Rules (enforced by the linter):**
- The stored `ap` must equal the value from this table.
- **AP = H:** at least one action, or a documented `rationale` for not acting, approved in review.
- **AP = M:** action or rationale recommended.
- Any cause with **S ≥ 9**: reviewed regardless of AP.

The executable copy of this table is `tools/safety/fmea_lint.py` (`AP_TABLE`); its unit tests pin every row above.

---

## 6. FMEDA classification and targets

Per ISO 26262-5 §8–9 and Annex D. Failure rates in FIT (failures per 10⁹ h).

### 6.1 Fault classification (computed by the linter from the row fields)

| Row fields | Classification |
|---|---|
| `safety_related: false` | not counted |
| `violates_sg_directly: true`, no safety mechanism | Single-point fault (λSPF) |
| `violates_sg_directly: true`, with mechanism of coverage `dc_spf` | Residual λRF = λ·(1−dc_spf); remainder is detected multiple-point |
| `violates_sg_directly: false`, `mpf_potential: true` | Multiple-point; latent part λMPF,L = λ·(1−dc_lf) |
| `violates_sg_directly: false`, `mpf_potential: false` | Safe (λS) |

### 6.2 Diagnostic coverage claims

| Level | DC | Note |
|---|---|---|
| Low | ≥ 60 % | |
| Medium | ≥ 90 % | |
| High | ≥ 99 % | |

Each safety mechanism must state its claimed DC and the basis (ISO 26262-5 Annex D table/row, or analysis/test evidence).

### 6.3 Targets

| ASIL | SPFM | LFM | PMHF |
|---|---|---|---|
| B | ≥ 90 % | ≥ 60 % | < 100 FIT (10⁻⁷ /h) |
| C | ≥ 97 % | ≥ 80 % | < 100 FIT (10⁻⁷ /h) |
| D | ≥ 99 % | ≥ 90 % | < 10 FIT (10⁻⁸ /h) |

The linter reports SPFM, LFM and the single-point + residual part of PMHF (λSPF + λRF). The dual-point PMHF contribution is not computed by the linter and must be added in the FMEDA report.

---

## 7. FMEA-MSR — Monitoring and System Response (added in RT-2)

Supplementary FMEA for Monitoring and System Response (AIAG & VDA 2019). It rates what happens **in the car** when a cause occurs: is it diagnosed, and does the system reach a safe state before harm? Detection (§3) still rates only what is found before release; S, O, D and AP of a cause are never changed by its MSR row. Scope, rationale and phasing: [msr-plan.md](msr-plan.md).

**Rows:** System FMEA and DFMEA causes whose failure mode has S ≥ 9 and lists a `safety_mechanisms` entry. Software-origin causes are rated once, in the System FMEA. Each such cause carries either an `msr` block or an `msr_exempt` reason (an error once the analysis header says `msr: complete`).

### 7.1 Severity after the system response

Rated with the §1 table on the effect that remains **after** the mechanism has acted, e.g. "steering assist lost with an alert; driver steers" is S 8 instead of S 10.

- It never exceeds the failure mode's severity.
- It may drop below 10 only if the FSC safe state is reached without driver action, or with a driver action that the HARA rates C0–C2 within the warning time.
- It enters the MSR AP only at M 1 and only for S 1–8, which still use the provisional stand-in (§7.4); the S 9–10 handbook table rates the original severity in every column, M 1 included.

### 7.2 Frequency (F)

How often the cause occurs in the field over the vehicle life.

| F | Criterion | Hardware cause (λ of the cause, from the FMEDA or DFMEA) | Host and software cause |
|---|---|---|---|
| 10 | Frequency unknown, or the cause occurs on most vehicles | no estimate | no estimate |
| 9 | Very high | ≥ 1000 FIT | F = the cause's O (§2.1 or §2.2): the same evidence, without field-exposure credit |
| 8 | High | 100 to < 1000 FIT | ″ |
| 7 | High | 30 to < 100 FIT | ″ |
| 6 | Moderate | 10 to < 30 FIT | ″ |
| 5 | Moderate | 3 to < 10 FIT | ″ |
| 4 | Low | 1 to < 3 FIT | ″ |
| 3 | Low | 0.3 to < 1 FIT | ″ |
| 2 | Very low | 0.1 to < 0.3 FIT | ″ |
| 1 | Extremely low, or ruled out by the design | < 0.1 FIT | ″ |

The FIT bands are LionDriver tailoring. Generic failure rates (the FMEDAs at this baseline) give at best F 3.

### 7.3 Monitoring (M)

How well the diagnostic detects the cause in operation **and** the system response reaches the safe state within the fault-tolerant time interval (FTTI). FTTI, FDTI and FRTI come from [WP-S-04 §3.7](../../03-system/WP-S-04-timing-ftti-budget.md#37-summary-of-fttis-and-budgets) (budgets) and §4 (code-derived times).

| M | Criterion | Evidence required (checked by the linter where marked ✓) |
|---|---|---|
| 10 | No in-field diagnostic for this cause, or only the driver noticing it unaided | — |
| 9 | A diagnostic exists but is not designed for this cause | — |
| 8 | Diagnostic targets this cause; the response does not reach the safe state, or its time exceeds the FTTI | e.g. EPS-fault siren at 1.26 s against 1 s with the 1 s persistence (WP-S-04 OI-8; 0.96 s since panda `bf8102a`, DQ-048) |
| 7 | Diagnostic and response target this cause; timing unknown or not compared with the FTTI | ✓ timing basis `unknown` forces M ≥ 7 |
| 6 | Within the FTTI on code-derived timing; test exists, not proven | ✓ WP-S-04 row, FTTI, FDTI + FRTI ≤ FTTI; ✓ evidence `test` path |
| 5 | As M 6, and the diagnostic's test is proven (mutation or fault injection) | as M 6 |
| 4 | Within the FTTI on **measured** timing; the proven test covers some instances of the cause | ✓ basis `measured`; ✓ evidence `ref` to the measurement; DFMEA: FMEDA DC ≥ 90 % (warning) |
| 3 | As M 4, covering all instances of the cause | as M 4 |
| 2 | As M 3, with margin shown under worst-case conditions (tolerances, load) | as M 4 |
| 1 | Diagnosis and response always effective (exhaustive or formal argument plus measurement) | as M 4; the severity after the response is rated (§7.4) |

### 7.4 MSR Action Priority

**S 9 and S 10: AIAG-VDA FMEA-MSR handbook table (RT-3).** Source: AIAG & VDA FMEA Handbook (2019), Supplemental FMEA-MSR, action priority table for FMEA-MSR, transcribed cell by cell from the lead's copy of the S 9 and S 10 pages (decision register DQ-207, option A, 2026-10-19). The handbook pages are not stored in the repository. Rows are frequency F, columns monitoring M; the original severity is rated in every column, M 1 included.

| S | F | M 1 | M 2 | M 3 | M 4 | M 5 | M 6 | M 7 | M 8 | M 9 | M 10 |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 10 | 5–10 | H | H | H | H | H | H | H | H | H | H |
| 10 | 4 | M | H | H | H | H | H | H | H | H | H |
| 10 | 3 | L | M | M | H | H | H | H | H | H | H |
| 10 | 2 | L | L | L | M | M | M | M | M | M | M |
| 10 | 1 | L | L | L | L | L | L | L | L | L | L |
| 9 | 4–10 | H | H | H | H | H | H | H | H | H | H |
| 9 | 3 | L | H | H | H | H | H | H | H | H | H |
| 9 | 2 | L | H | H | H | H | H | H | H | H | H |
| 9 | 1 | L | L | L | L | L | L | L | L | L | L |

S 9 is stricter than S 10 at F 2 and F 3. That is how the handbook pages read; it is transcribed as is, not corrected.

> **S 1–8: provisional.** Those handbook pages are not transcribed yet. Until they are, the §5 table is applied with **F in place of O** and **M in place of D**, and with M 1 the severity after the system response (§7.1) replaces the original severity. Transcribing them makes RT-4. The linter reports how many rows use this stand-in. Every MSR row at RT-3 has S 10, so none does.

The executable copy is `tools/safety/fmea_lint.py`: `AP_MSR_HANDBOOK` for S 9–10 and `AP_MSR_TABLE` (the stand-in) for S 1–8, both through `compute_ap_msr`. Its unit tests pin every S 9–10 cell to the table above and the stand-in to §5.

**Rules (enforced by the linter):**
- The stored `msr.ap` must equal the value from this table.
- **MSR AP = H:** an `msr.actions` entry (action `kind: monitoring` where it improves the diagnostic or response) or an `msr.rationale`.
- **MSR AP = M:** action or rationale recommended.
- Every mechanism an MSR row rates must cite a `ref` or `test` on the failure mode.
- `ftti_ms` must equal the FTTI of the cited WP-S-04 row.
- **Closing a cause (lead decision DQ-206, option A, 2026-10-19; [WP-S-04 §6](../../03-system/WP-S-04-timing-ftti-budget.md#6-measurement-plan)).** A diagnostic followed by a safe state closes a hazard-linked cause only when its fault-injection timing has been **measured** (WP-S-04 §6, e.g. M-04, M-05, M-06, M-10) and lies inside the FTTI of WP-S-04 §3.7: the row has `basis: measured` with a `ref` to the measurement (so M ≤ 4) and an MSR AP of L or M. Until that measurement passes, the cause stays open whatever its MSR AP.
- Code-derived timing (WP-S-04 §4, M 5–6) and simulated timing (WP-S-04 §3.9, evidence only, msr-plan §4.2) **rank** the work; they never close a cause.

