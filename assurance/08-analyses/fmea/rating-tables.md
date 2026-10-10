# LionDriver — FMEA Rating Tables

**Version:** RT-1 (referenced by `rating_tables: RT-1` in every analysis file)
**Basis:** AIAG & VDA FMEA Handbook (2019), tailored. Criteria are paraphrased; consult the handbook for the normative wording.
**Applies to:** System FMEA, DFMEA, SW FMEA, PFMEA. FMEDA uses §6.

Any change to these tables increments the version (RT-2, …) and triggers re-rating of affected rows.

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
