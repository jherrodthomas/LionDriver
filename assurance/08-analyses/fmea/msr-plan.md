# LionDriver — FMEA-MSR: audit and plan

**Status:** Draft v0.7, 2026-10-16. Simulation results (plant model) are citable as MSR `evidence` but are no timing basis of their own and never a measurement (§4.2, §5); the linter enforces the second. v0.6, 2026-10-16. M3: Figure 4-2 (FMEA-MSR overview) drawn by `fmea_diagrams.py`; the MSR columns in the review workbooks are still open. v0.5, 2026-10-16. System FMEA MSR rows re-rated at baseline BL-005, crediting the host supervision (TSR-615, TSR-621), TX arrival (TSR-408), the cruise-mismatch alert (TSR-308) and the reference lock, now built by default; results in §4.7. v0.4, 2026-10-14. Step M2 done: every in-scope cause is rated or pointed at the DFMEA (75 rated, 4 exempt; both files `msr: complete`); results in §4.7. v0.3: step M1 pilot done: 32 causes rated (DFMEA complete, System FMEA SG-01 lateral chain), MSR line and §7 in the review pages. v0.2: step M0 done: RT-2 §7 tables, schema `msr` block and linter rules with tests. No cause rated yet (linter report: 0 of 79 in-scope causes). The MSR action priority table is provisional until the handbook table is transcribed (§4.1). v0.1: audit and plan.
**Basis:** AIAG & VDA FMEA Handbook (2019), Supplemental FMEA for Monitoring and System Response (FMEA-MSR), ISO 26262-4 §6 (FTTI) and ISO 26262-5 §8 (diagnostic coverage), by reference.
**Related:** [fmea-plan.md](fmea-plan.md), [rating-tables.md](rating-tables.md) (RT-1), [WP-S-04 timing and FTTI budget](../../03-system/WP-S-04-timing-ftti-budget.md), [WP-V-05 fault injection](../../06-validation/WP-V-05-fault-injection.md).

## 1. Answer

**Yes, as a supplement to the System FMEA and the DFMEA, scoped to hazard-linked causes that have an in-field mechanism.** It is not a sixth analysis file and it does not change any S/O/D or AP already rated.

FMEA-MSR asks a question none of the current analyses rates: *when this cause occurs while driving, does a diagnostic catch it and does the system reach a safe state before harm?* LionDriver's safety argument rests on exactly that (panda envelope and RX timeouts, IWDG reset and relay release, heartbeat loss, siren, driver-monitoring escalation, controls mismatch, EPS fault reaction), but the FMEA set records those mechanisms only as unrated design facts.

## 2. Audit

### 2.1 What the FMEA set does with in-field mechanisms today

| Finding | Evidence |
|---|---|
| No FMEA-MSR anywhere in the plan, rating tables, schema or linter. | Search of `assurance/` and `tools/safety/` for MSR, "monitoring and system response", FMEA-MSR: no hits. |
| RT-1 deliberately excludes in-field diagnostics from Detection. | [rating-tables.md §3](rating-tables.md#3-detection-d--system-fmea-dfmea-sw-fmea): "Field diagnostics that act while driving are safety mechanisms; they reduce severity or occurrence through the design, not D." This is correct AIAG-VDA practice, and it is the gap MSR is meant to fill. |
| The mechanisms are listed but never rated. | `safety_mechanisms` on 90 of 123 failure modes (System FMEA 25/34, SW FMEA 53/53, DFMEA 12/19, PFMEA 0/17). The System FMEA header: "design facts … not credited as detection". |
| AP cannot tell a well-monitored cause from an unmonitored one. | 194 of 201 causes are AP H. A panda MCU hang (IWDG reset and relay release in about 90 ms, inside a 0.5 s FTTI) ranks the same as a cause with no runtime monitor at all. |
| Timing evidence exists but is not tied to failure causes. | WP-S-04 §3.7 gives FTTI, detection and reaction budgets per safety goal and §4 the code-derived times. No FMEA row points at a WP-S-04 row. |
| One known budget overrun is not visible in the FMEA. | WP-S-04 §3.7: EPS-fault siren worst case 1.26 s against a 1 s budget to warning (OI-8). MSR would rate this as poor monitoring on a hazard-linked cause. Today it shows up only in WP-S-04. |
| FMEDA covers part of this, but only for random hardware faults on two goals. | `fmeda-sg001.yaml` and `fmeda-sg009.yaml` claim diagnostic coverage per mechanism. They say nothing about systematic causes, about whether the response is fast enough, or about goals SG-02…SG-07. |

### 2.2 Is MSR required?

No standard makes it mandatory for LionDriver. ISO 26262 asks for the same evidence in its own terms: safety mechanisms with FDTI + FRTI within FTTI (part 4 §6) and diagnostic coverage (part 5). AIAG-VDA MSR is the FMEA-side home for that evidence. Three reasons to add it anyway:

1. **It closes a traceability hole.** Every hazard-linked cause gets an explicit, rated answer to "what catches it in the car, how fast, and what is left". Today a reviewer has to join the FMEA, WP-S-04 and the FSC by hand.
2. **It lets AP sort again.** MSR AP separates causes that are monitored within FTTI from causes that rely on the driver alone, which is where actions belong.
3. **Assessors and OEM-style reviewers expect it** for any design whose argument depends on diagnostics and a safe state.

### 2.3 What MSR must not become

- **Not a back door to lower DFMEA AP.** S/O/D and AP stay as rated under RT-1. MSR adds its own S, F, M and MSR AP.
- **Not a second FMEDA.** For hardware random faults, M must be consistent with the FMEDA's diagnostic coverage; the FMEDA stays the quantitative source. The linter checks the two against each other (§4.4).
- **No credit without timing evidence.** A mechanism whose FDTI + FRTI has not been compared with the FTTI cannot earn a good M rating (§4.2).

## 3. Scope

| Analysis | MSR rows | Why |
|---|---|---|
| System FMEA | Causes with S ≥ 9 whose failure mode lists a `safety_mechanisms` entry. SW-origin causes (`linked_failure_mode: SWF-…`) are rated **here**, once. | This is the vehicle-level view where the safe state and its effect on the driver are visible. Rating SW causes here avoids rating the same chain twice. |
| DFMEA | Hardware causes with S ≥ 9 and an in-field mechanism (watchdog, relay drop-out, transceiver fault detection, power supervision). | Random hardware faults are what AIAG-VDA MSR was designed for. These rows are cross-checked against FMEDA DC. |
| SW FMEA | No MSR rows. Each SW mechanism is listed and referenced from the System FMEA MSR row. | Frequency of a systematic fault in the field has no defensible basis per software element. |
| PFMEA | None. | A process fault is not a failure during customer operation. Install and configuration faults that show up while driving (wrong fingerprint, wrong panda firmware) are already System FMEA causes. |

Size: 64 System FMEA causes and 15 DFMEA causes meet the §3 criteria today (S ≥ 9, failure mode lists a mechanism). **Pilot:** SG-01 lateral chain first, about 15 causes covering envelope limits, RX timeout, heartbeat loss, MCU hang/IWDG and relay stuck. That chain already has WP-S-04 rows and FMEDA SG-001.

## 4. Plan

### 4.1 Rating tables RT-2 (`rating-tables.md` new §7)

Adding MSR tables increments the version to **RT-2**. S/O/D and AP do not change, so no existing row needs re-rating; files move to `rating_tables: RT-2` when they gain MSR rows.

- **Severity (MSR)**: the effect *after* the system response, rated on the existing §1 table. Example: unintended torque caught and released with an alert → S 8 (loss of function with handback) instead of 10. If the response does not reliably reach the safe state, or the driver must intervene to avoid the hazard, the original S stays.
- **Frequency (F) 1–10**: how often the cause occurs in the field over the vehicle life.
  - Hardware: from the FMEDA λ for the part or failure mode.
  - Host and SW-origin causes: the System FMEA occurrence O, with no field-exposure credit (same basis as RT-1 §2).
  - Bands are written against FIT and field exposure and pinned by tests.
- **Monitoring (M) 1–10**: AIAG-VDA criteria (diagnostic detection plus system response), tailored with evidence levels:

  | M band | LionDriver evidence required |
  |---|---|
  | 1–2 | Diagnostic and response always effective. FDTI + FRTI ≤ FTTI **measured** (WP-V-05 fault injection or HIL), with a mutation-proven test of the diagnostic. |
  | 3–4 | As above, measured, but the test does not cover every instance of the cause. |
  | 5–6 | FDTI + FRTI ≤ FTTI from **code-derived** times only (WP-S-04 §4), test exists. |
  | 7–8 | Diagnostic exists but the response is incomplete, or its timing is unknown or exceeds the FTTI (e.g. EPS-fault siren, OI-8). |
  | 9–10 | No in-field diagnostic, or it depends on the driver noticing. |

  The exact wording is transcribed from the handbook at implementation time; the table above sets how evidence maps onto it.
- **MSR AP table**: the AIAG-VDA S × F × M table belongs in `fmea_lint.py` as `AP_MSR_TABLE`. The handbook is not in the repository and the table is not published elsewhere, so RT-2 uses a **provisional** table: the §5 AP table with F for O and M for D, and with M 1 the severity after the response. The linter report says so on every run. Transcribing the handbook table makes RT-3 and re-rates the MSR rows; getting the table is in the decision register.

### 4.2 Schema (`schema/fmea.schema.json`, `schema_version` stays 1, additive)

An optional `msr` object on a cause:

```yaml
msr:
  mechanisms: [1, 2]            # 1-based positions in the failure mode's safety_mechanisms; each must cite a ref or test
  diagnostic: "IWDG expires after 90 ms without refresh"
  system_response: "MCU reset; relay de-energised; stock camera CAN restored"
  effect_after_response: "Steering assist lost with alert; driver steers"
  severity_after: 8
  frequency: 3
  monitoring: 6
  ap: H
  timing: {ftti_ref: "SG-01 MCU execution fault", ftti_ms: 500, fdti_ms: 90, frti_ms: 100, basis: code_derived}  # measured | code_derived | unknown
  fmeda: fmeda-sg001/FMD-012    # DFMEA rows: the FMEDA failure mode whose DC backs M
  evidence: [ ... ]             # controls: `test` for the diagnostic, `ref` for a timing measurement (WP-V-05)
  actions: [ ... ]              # kind: monitoring
  rationale: ...
```

A cause carries `msr` or `msr_exempt` (a reason), never both. The header gets `msr: none|partial|complete`; with `complete`, an in-scope cause without either is an error. Actions stay in the shared `actions` list with the new `kind: monitoring`.

**Simulation results** (the closed-loop plant model, `assurance/sim/`) are evidence, not a timing basis. Decided 2026-10-16 on the simulation session's proposal (§5):

- **How to cite one:** a run that reproduces a cause's timing with the real panda code in the loop goes in `evidence`, with `ref` to the result file and case ID plus the plant commit. `basis` stays what the timing rests on: `code_derived`, or `unknown`.
- **M is unchanged:** a simulation cross-checks the code-derived times. It moves no row up or down.
- **Never a measurement:** M ≤ 4 still needs a HIL or vehicle measurement (WP-V-05). An M ≤ 4 row whose only evidence refs point under `assurance/sim/` is a linter error.
- **Scope:** it covers only the parts the model runs as real code (libsafety and the panda board drivers). EPS, PCM and driver timing are assumptions in the model, and a simulation is no evidence for them.
- **Revisit:** whether a validated simulation could ever earn more depends on the WP-V-02 §5.3 fidelity case for that scenario family (DQ-139).

### 4.3 Where each piece comes from

| Field | Source |
|---|---|
| mechanisms | existing `safety_mechanisms` on the failure mode |
| timing | WP-S-04 §3.7 (FTTI, budget) and §4 (code-derived FDTI/FRTI); measurements from WP-V-05 |
| frequency (HW) | FMEDA λ (`fmeda-sg001.yaml`, `fmeda-sg009.yaml`); DFMEA occurrence where no FMEDA row exists |
| severity after response | HARA effect levels and the FSC safe states (`analyses/fsc.yaml`) |
| monitoring evidence | `test` paths (same rule as RT-1 D ≤ 8) and WP-V-05 records |

### 4.4 Linter (`tools/safety/fmea_lint.py`) and tests

- `msr.ap` equals `AP_MSR_TABLE[S, F, M]`.
- `msr.severity_after` ≤ the failure mode's severity.
- M ≤ 6 requires `timing` with `fdti_ms + frti_ms ≤` the FTTI of the referenced WP-S-04 row.
- M ≤ 4 also requires `basis: measured` and evidence.
- `basis: unknown` forces M ≥ 7.
- Every `mechanisms` entry resolves to a `safety_mechanisms` item that has a `ref` or `test`; `ftti_ms` equals the cited WP-S-04 row.
- **Scope check:** every in-scope cause (§3) either has an `msr` block or an `msr_exempt` rationale (an error once the header says `msr: complete`; reported as coverage before that).
- **FMEDA cross-check (DFMEA):** an M of 4 or better on a hardware cause needs an FMEDA mechanism with DC ≥ 90 %. This is a warning only while the FMEDA is generic.
- MSR AP H follows the same rule as RT-1: an action or an approved rationale.

### 4.5 Review pages and figures

- `tools/safety/fmea_review_md.py`:
  - Each worksheet table gets an MSR line under any cause that has one: diagnostic, response, timing against the FTTI, and S/F/M with an MSR AP badge.
  - A new section, "Monitoring and system response", holds an S × M heat map and the list of MSR AP H causes.
- The P-diagram's error states already link to failure modes. The control factors gain the monitored mechanisms.
- `tools/safety/fmea_diagrams.py`: Figure 4-2, the MSR AP overview next to Figure 4-1.

### 4.6 Phasing

| Step | Deliverable | Depends on |
|---|---|---|
| M0 | RT-2 (§7 tables), schema `msr` block, linter rules and tests; no rows — **done 2026-10-14** | This plan |
| M1 | Pilot: SG-01 lateral chain in the System FMEA (17 rated, 3 rated in the DFMEA) and all 15 DFMEA causes — **done 2026-10-14** | M0, WP-S-04 rev 0.5 |
| M2 | Remaining System FMEA and DFMEA in-scope causes — **done 2026-10-14** (System FMEA rev 0.8: 60 rated, 4 in the DFMEA) | M1 review |
| M3 | Review pages (MSR line per failure mode, §7 table and frequency × monitoring map — **done with M1**), Figure 4-2 (**done 2026-10-16**, [fmea-plan.md §4](fmea-plan.md)), MSR columns in the review workbooks | M1 |
| M4 | Re-rate M as WP-V-05 measurements land (code-derived → measured) | WP-V-05 |
| M5 | Independent review of the MSR rows with the FMEA set | M2 |

**Expected first result:** most M ratings will start at 5–8 because no timing has been measured yet. That is the honest picture, and it ranks the WP-V-05 measurements by safety value.

### 4.7 Pilot result (M1)

| | System FMEA (BL-004) | DFMEA (BL-002) |
|---|---|---|
| Rated / in scope | 17 / 64 (3 more rated in the DFMEA) | 15 / 15 |
| Best monitoring | M 5: panda per-frame steering checks (not engaged, torque magnitude and rate), mutation-tested, code-derived timing | M 7: IWDG reset, response unconfirmed (relay release UK-06, LSI margin OI-7) |
| Reacts, but too slowly or incompletely (M 7–8) | Excessive-actuation check plus 3 s soft disable against a 0.5 s FTTI (SFM-002.C3); command stall held 0.1 s, then about 2 s of EPS decay (SFM-006.C1); safety-model mismatch only after 10 s (SFM-029.C1) | RX loss warns after about 2.2 s against 1 s (DFM-009); relay stuck released found after 1–2 s against 0.5 s (DFM-011); stuck-dominant transceiver not released (DFM-008) |
| No monitor (M 9–10) | Wrong steering direction (SFM-003, 4 causes); panda authority wrong while disengaged (SFM-001.C2); frozen model output and stale messages (SFM-006.C2/C3); limit-code defect (SFM-029.C2); harness bypass (SFM-029.C4) | CPU, flash, SRAM, brown-out, relay readback, TX read-back, harness disconnect, bootloader (10 causes) |

**What it shows:**
- The MSR rows put on one page what WP-S-04 §5 lists as "not met", against the failure causes they leave open.
- New monitoring actions: SFM-ACT-012 (measure the panda reaction on HIL), SFM-ACT-013 (host check of panda authority while disengaged), SFM-ACT-014 (steering-direction plausibility monitor), SFM-ACT-015 (command and input freshness, TSR-408/602). The DFMEA rows reuse the existing DFM-ACT actions.
- **Every MSR AP is H.** With S 10 and F ≥ 4, the provisional table gives H at every M except M 1. So M, not the MSR AP, is what ranks the work: the review pages sort by M. Whether the handbook table separates these rows better is open until it is transcribed (decision register).
- Host supervision added after BL-004 (TSR-615 panda TX blocked, TSR-621 mismatch timing) and the heartbeat-loss siren were not credited at BL-004. They are credited at BL-005 (below).

**After M2 (all in-scope causes):**

| Monitoring | System FMEA (60) | DFMEA (21) | What sits there |
|---|---:|---:|---|
| M 1–4 (measured) | 0 | 0 | Nothing is measured yet (WP-V-05) |
| M 5–6 (code-derived, within FTTI) | 12 | 0 | Panda per-frame steering and acceleration checks; panda revocation on driver brake, cancel and gas |
| M 7–8 (warning only, no FTTI row, or too slow) | 16 | 6 | Saturation, lane-departure and FCW warnings; soft disables after excessive actuation; EPS drop-out and mismatch warnings at about 2–3.5 s against 1 s; harness-box clamp-diode short (bus lost, stock path not restored); switch logic threshold not met with VL at VIN (found as relay stuck released) |
| M 9–10 (no monitor) | 32 | 15 | Wrong targets inside the limits, steering direction, driver override in the panda, silent EPS/PCM non-acceptance, alert-channel supervision, DM false negatives, the zero-awareness reaction, MCU memory and intercept-switch faults, harness-box supply loss, pull-down open and switch overstress (RR-2026-010) |

M2 adds three monitoring actions:
- SFM-ACT-016: driver-override supervision in the panda (TSR-304).
- SFM-ACT-017: FTTI rows for the warning paths that have none, so they can be credited.
- SFM-ACT-018: detection of a silent loss of the actuation path.

**At BL-005 (System FMEA rev 0.9, 2026-10-16).** The reference build is the default at BL-005, so its panda checks count. Every claim was re-checked against the code at liondriver-dev `1033d98`, panda `a55bdfc`, opendbc `9a13f60`.

| Monitoring | System FMEA, BL-004 | System FMEA, BL-005 | What moved |
|---|---:|---:|---|
| M 1–4 (measured) | 0 | 0 | Still nothing measured (WP-V-05, SFM-ACT-012) |
| M 5–6 | 12 | 15 | SFM-015.C2 (controlsMismatch within 0.5 s, TSR-621), SFM-005.C2 and SFM-011.C2 (TX arrival 50/100 ms, TSR-408, then controlsMismatch) |
| M 7–8 | 16 | 16 | In: SFM-021.C1/C2 (cruiseMismatch alert after 1 s, TSR-308; no FTTI row) and SFM-032.C1 (reference lock refuses another safety parameter). Out: the three causes above |
| M 9–10 | 32 | 29 | The three causes that moved to M 7–8 |

What did not move, and why:
- **Refused over-limit frames** (SFM-002, SFM-008, SFM-009): a refusal while engaged now also disengages with an alert (`pandaTxBlocked`, TSR-615), but M stays 5 and S after the response stays 10, because the envelope is not yet derived from the vehicle (SFM-ACT-001).
- **SFM-006.C1** (controlsd hangs): the driver is now warned within about 0.66 s, but no frame follows the stall, so the torque ends only when the EPS drops LKA, about 2 s later; with no active zero frame (TSR-109) it stays M 8.
- **`pandaHeartbeatLost`, `pandaTxRateExceeded`** (TSR-615) are not the main monitor of any System FMEA cause. They name the cause when the panda revokes authority (SFM-015.C2). Heartbeat loss from a hung `pandad` can't reach the host anyway: the panda's own siren covers that case (WP-S-04 T-07a).
- **SFM-001.C2** (panda grants authority while disengaged): TSR-621 still checks only the other direction (SFM-ACT-013).

WP-S-04 §4 still gives the BL-004 values for T-17 (`controlsMismatch`, 2 s) and T-19 (`cruiseMismatch`, 6 s) and has no row for TX arrival (TSR-408). The MSR rows cite the code for these times; the WP-S-04 update is listed for its owner.

**DFMEA at BL-005 (rev 0.7, 2026-10-16).** The hardware is unchanged. The panda changes from `9f60e17` to `a55bdfc` that touch DFMEA rows were read at the pins.

| Monitoring | DFMEA, BL-002 (21) | DFMEA, BL-005 (23) | What moved |
|---|---:|---:|---|
| M 1–4 (measured) | 0 | 0 | Nothing measured (no HIL bench, DQ-049) |
| M 5–6 | 0 | 1 | DFM-009.C1: car-side RX loss now warns within about 0.66 s (RX timeout 0.16 s, then controlsMismatch within 0.5 s, TSR-621) |
| M 7–8 | 6 | 5 | Out: DFM-009.C1 |
| M 9–10 | 15 | 17 | In: DFM-017.C1/C2. The panda now sounds the siren itself on heartbeat loss and on a persistent EPS fault (panda#14, #15), so the siren is a listed mechanism, but nothing checks that its speaker path works without the SoC |

### 4.8 Risks

1. **Double counting** with FMEDA DC: handled by the cross-check (§4.4) and by keeping FMEDA as the source for hardware λ and DC.
2. **Optimistic severity after response:** S after response may drop below 10 only if the FSC safe state is reached without driver action, or with a driver action the HARA rates controllable (C ≤ 2 within the warning time).
3. **Upstream drift:** mechanisms live in `panda` and `opendbc`; MSR rows carry the same baseline SHAs and are re-checked by the existing submodule impact trigger (fmea-plan §7.1).

## 5. Decisions

| Question | Decider | Choice |
|---|---|---|
| Add FMEA-MSR as a supplement to System FMEA and DFMEA (not a separate file), scoped per §3? | Claude (reversible method choice) | Yes, per this plan |
| Rate SW-origin causes in the System FMEA rather than the SW FMEA? | Claude | Yes, once, at vehicle level |
| Add a timing basis `simulated` for plant-model results (proposed by the simulation session, 2026-10-16)? | Claude (reversible method choice) | No: cite the run as `evidence`, keep `basis`; a simulation never counts as a measurement (§4.2). A `simulated` basis capped at M ≥ 7 would only lower rows that already rate M 5–6 on code-derived timing |
| May an MSR AP of M or L count as an accepted residual risk for a hazard-linked cause, or does it stay information for prioritising actions only? | **Lead** (risk acceptance) | Queued in the decision register |
