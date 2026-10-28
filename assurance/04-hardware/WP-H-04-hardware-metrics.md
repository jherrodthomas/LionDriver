# WP-H-04 Hardware architectural metrics (SPFM, LFM)

| Field | Value |
|---|---|
| Work product | WP-H-04 Hardware architectural metrics (SPFM, LFM) |
| Standard reference | ISO 26262-5:2018 §8 (evaluation of the hardware architectural metrics), Annex C (metric definitions, informative), Annex D (diagnostic coverage, informative); ISO 26262-11:2018 (semiconductors, informative) |
| Version | 0.12 (§5.2: SG-07 from FMEDA SG-009 rev 0.9 with the camera-side termination R7/R8: 288 FIT, LFM 97.6 %, planned measures 94.5 %; AI-drafted; 2026-10-27). 0.11 (§3.3 and OI-3: QM-SoC mechanisms stay excluded from DC, an internal method choice until an assessor confirms it (DQ-070 A); 2026-10-22). 0.10 (status line brought up to date: §5.2 and §5.3 hold generic-rate estimates; no content changed; 2026-10-22). 0.9 (§5.2: SG-05 estimate, SPFM 90.38 %, from the FMEDA rev 0.7 per-goal classification; 2026-10-20). 0.8 (OI-6: no ST licence and low CPU coverage, DQ-069 option B, the ASIL C SPFM target likely missed; 2026-10-19). 0.7 (SG-02, SG-03 and SG-06 at ASIL C since WP-C-03 v0.4: §4 targets updated; §5.2 carries the SG-01 estimate for them, decision DQ-362 option A; new OI-6, the 0.16-point ASIL C SPFM miss, for G2; Figure 5-1 updated; 2026-10-18). 0.6 (§5.3 SG-07 SPFM deviation accepted by the lead, DQ-320 option A, conditional on the harness box bench tests; 2026-10-16). 0.5 (§5.2 generic-rate estimate from FMEDA rev 0.4 with SG-01 shown against C and B; Figure 5-1 marks the estimates; 2026-10-16). 0.4 (decisions applied: SG-01 target C with B alongside, DQ-063; route to the BOM, DQ-065; added hardware allowed in principle, DQ-051; HIL bench deferred, DQ-049; IWDG credit conditional, DQ-114; 2026-10-16). 0.3 (§5 status and §4 targets drawn as Figure 5-1; no value changed; 2026-10-13). 0.2 (status note 2026-10-12: DC-01 implemented, not verified, no DC credit; §5.1, §6 step 4). 0.1: initial draft |
| Status | Draft (method and plan; generic-rate estimates for SG-01, SG-05 and SG-07 in §5.2 and §5.3; no part-level metric computed) |
| ASIL / scope | ASIL C (SG-01 provisional; SG-02, SG-03, SG-06 since WP-C-03 v0.4) / ASIL B (SG-04, SG-05, SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `bf6ce8c` (status update 2026-10-12) |

## 1. Purpose

States how LionDriver will compute the single-point fault metric (SPFM) and latent fault metric
(LFM) for the hardware of LD-SDA, which targets apply, what the status is, and the plan to get to
a result. It addresses **GAP-15** (no SPFM/LFM). Under tailoring **T-04**, LionDriver computes the
metrics itself because no supplier evidence exists.

**No metric has been computed. None can be computed today, because there is no BOM, no
schematic and no failure-rate data** ([WP-H-02](WP-H-02-hardware-design.md) §5, UK-01/02).

## 2. Scope of the calculation

| Item | Decision |
|---|---|
| Hardware in scope | Safety-related hardware of E-04 (panda MCU and its periphery: clock, supply, transceivers, relay driver, sense circuits, SPI and reset lines) and E-05 (harness relay, connector, wiring) as identified in WP-H-02 §3.2 |
| Out of scope | SoC, cameras, display, modem (QM; their failures are covered by the envelope or are SOTIF). They enter the DFA, not the metrics. Vehicle ECUs (outside the item, T-02) |
| Per safety goal | Metrics are computed **per safety goal**: SG-01 (with SG-03/SG-04/SG-05 sharing the same hardware path, computed separately because the safe states differ) and SG-07 (relay/harness-dominated). SG-02/SG-06 (warning on loss) are computed for the siren and heartbeat path |
| Level | Item level for the hardware of the item, with the MCU split per ISO 26262-11 ([WP-H-03](WP-H-03-hardware-safety-analysis-fmeda.md) §6.2) |

## 3. Method

### 3.1 Definitions (our words; verify against the licensed text)

For the safety-related hardware elements of one safety goal:

- **λ** = total failure rate of the safety-related hardware.
- **λ_SPF** = rate of single-point faults (no safety mechanism covers them).
- **λ_RF** = rate of residual faults (the uncovered part of faults that a safety mechanism is
  meant to cover): λ_RF = λ_covered-element × (1 − DC_RF).
- **λ_MPF,L** = rate of latent multiple-point faults (neither detected by a safety mechanism nor
  perceived by the driver within the multiple-point fault detection interval).
- **λ_S** = safe faults.

```
SPFM = 1 − (Σ λ_SPF + Σ λ_RF) / Σ λ
LFM  = 1 − Σ λ_MPF,L / (Σ λ − Σ λ_SPF − Σ λ_RF)
```

Only safety-related elements enter the sums. Elements not safety-related are excluded with a
documented rationale in the FMEDA.

### 3.2 Calculation steps

1. Freeze the hardware configuration: device revision, harness part number, MCU option bytes
   (WP-H-02 UK-04) — the metrics are valid for that configuration only.
2. Fill the FMEDA ([WP-H-03](WP-H-03-hardware-safety-analysis-fmeda.md) §6) with failure rates
   from the agreed source and failure-mode distributions.
3. For each failure mode decide: safety-related? violates the SG without a mechanism? which
   mechanism covers it (for the SPF/RF classification) and which covers latent faults?
4. Assign DC per mechanism from the three-level scale (WP-H-03 §2.2). Claims above "low" need
   justification by analysis or fault injection ([WP-H-06](WP-H-06-hardware-integration-verification.md)).
5. Compute the sums and the metrics per SG in a spreadsheet kept under configuration control
   (`trace/` or the analysis folder, per [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md)); record the version of every input.
6. Sensitivity: vary the dominant failure rates and DC values within plausible bounds and show
   whether the target is still met.
7. Independent review (T-09) of the FMEDA and the spreadsheet.

### 3.3 Rules LionDriver applies

| Rule | Reason |
|---|---|
| A mechanism counts only if it leads to the safe state (or to a driver-perceived warning) within the FTTI budget of [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §8 | A report-only fault (GAP-08) has no coverage |
| Mechanisms in the QM SoC (e.g. host-side `controlsMismatch`, `canError`) are **not** credited for SPF/RF coverage | They are QM; crediting them would need the SoC to be developed to the ASIL. Kept as an internal method choice (DQ-070 option A, 2026-10-22); confirmed with an assessor once one is engaged (OI-3) |
| Vehicle measures (EPS LKA limit and timeout, PCM clamp) are **not** credited as DC | External measures; they are handled in the PMHF/EEC argument ([WP-H-05](WP-H-05-random-hardware-failures-pmhf.md) §5) and in the HARA controllability |
| Driver perception counts as latent-fault detection only for effects the driver cannot miss (e.g. engagement refused at start-up with a visible message) | Matches the "perceived" class |
| Start-up tests count for latent faults if executed every drive cycle and if their result blocks engagement | Drive-cycle interval is the multiple-point fault detection interval assumed here |

## 4. Targets

| Metric | ASIL B | ASIL C | ASIL D | Source |
|---|---|---|---|---|
| SPFM | ≥ 90 % | ≥ 97 % | ≥ 99 % | ISO 26262-5 §8 (commonly used values — **verify against licensed text**) |
| LFM | ≥ 60 % | ≥ 80 % | ≥ 90 % | as above |

Applicable targets ([WP-H-01](WP-H-01-hardware-safety-requirements.md) §3). For SG-01 the lead decided to keep ASIL C as the target until the HARA re-rates SG-01, and to show the ASIL B result alongside ([DQ-063](../01-management/decisions/register.yaml), option A, 2026-10-14). The SG-01 rows of §7 therefore carry both targets. Lowering steering authority (WP-M-07 D-13) is expected to bring SG-01 to B, but that is not yet applied to the HARA:

| SG | Current ASIL | Target set | Expected after FSC option (c) |
|---|---|---|---|
| SG-01 | C (provisional) | SPFM ≥ 97 %, LFM ≥ 80 %; the ASIL B result is reported alongside (DQ-063) | B: SPFM ≥ 90 %, LFM ≥ 60 % |
| SG-02, SG-03, SG-06 | C (WP-C-03 v0.4) | SPFM ≥ 97 %, LFM ≥ 80 % | unchanged |
| SG-04, SG-05 | B | SPFM ≥ 90 %, LFM ≥ 60 % | unchanged |
| SG-07 | B | SPFM ≥ 90 %, LFM ≥ 60 % | unchanged |

## 5. Current status

| Step (§3.2) | Status |
|---|---|
| 1 Configuration frozen | No: reference device revision not fixed (WP-H-01 OI-7) |
| 2 FMEDA filled | No: qualitative block-level FMEA (WP-H-03 §4) and a generic-rate block FMEDA (§5.2); no part-level rates |
| 3–4 Classification and DC | Qualitative only |
| 5 Calculation | **Cannot be computed: no BOM** |
| 6 Sensitivity | Not started |
| 7 Review | Not started |

### 5.1 Provisional qualitative assessment

This is engineering judgement, not a metric. It is stated so the decisions in the FSC can be
made with eyes open.

**Baseline hardware and firmware (`8b8c6ae`): the ASIL B targets are very likely not met for
SG-01 or SG-07, and the ASIL C targets are not met.** Reasons:

1. The MCU die is the largest single contributor of failure rate among the safety-related parts
   *(expected; confirm with data)*. Today almost all of it is uncovered: no CPU self-test, no
   watchdog, RAM/flash ECC events not handled, no MPU, faults report-only (WP-H-03 FM-CPU-01,
   FM-CPU-03, FM-RAM-02, FM-FLS-02; GAP-07, GAP-08). The only hardware mechanism with a reaction is
   the CSS on the HSE. With the CPU, SRAM and flash mostly in λ_SPF, SPFM for SG-01 would be far
   below 90 %.
2. For SG-07, relay stuck intercepting (FM-REL-02/04) and MCU hang with the relay driven
   (FM-CPU-03/05) are single-point faults with no mechanism. Their share depends on the relay's
   failure rate and mode distribution, which is unknown.
3. LFM: the ECC logic itself, the CSS, the relay-malfunction check and the heartbeat timeout are
   not tested at start-up, so their faults are latent. The relay-malfunction check is exercised only
   when a stock message appears, which in normal operation never happens.

*Status note 2026-10-12:* since 2026-10-12 DC-01 (IWDG1, window mode, fed from the 100 Hz safety task; panda `9f60e17`) is implemented, **not verified**. No DC credit is taken for it until HIL fault-injection evidence exists and the LSI tolerance is confirmed ([watchdog impact record](../07-supporting/impact/change-2026-10-12-panda-hw-watchdog.md) OI-3 and OI-2). Its own latent fault (LSI failure, WP-H-03 FM-CLK-04) needs the start-up test of OI-4 below. The assessment above is otherwise unchanged.

*Status note 2026-10-16:* the lead accepts the improved watchdog (90 ms, window mode) in place of the interim SG-07 residuals once an independent reviewer has checked it and its clock tolerance ([DQ-114](../01-management/decisions/register.yaml), option A, 2026-10-14). On the hardware side this sets the condition for DC credit: the generic FMEDA SG-009 already carries the IWDG at medium coverage (FMD-SM on `hw_watchdog.h`), and that credit stays provisional until the review and the LSI tolerance check are recorded. The HIL fault injection that would measure it is deferred with the bench ([DQ-049](../01-management/decisions/register.yaml)), so the review and analysis are the only route for now.

**With the firmware-only changes of WP-H-02 §6 (DC-01, DC-04…DC-10):** SPFM ≥ 90 % for SG-01 looks
*plausible but not certain*. The CPU core remains at "medium" coverage at best on a single
non-lockstep core with a software test library; whether that is enough depends on the CPU's share
of the total rate. ASIL C (97 %) is *unlikely* without DC-02 (external supervisor) or a second
channel. This supports the FSC recommendation of option (c).

**For SG-07:** ASIL B is *unlikely* to be met without relay readback (DC-03) unless the relay's
"stuck intercepting" rate is shown to be small relative to the total, which needs part data.

![Figure 5-1: SPFM and LFM status: calculation steps 1 to 7 not done or qualitative only for lack of a BOM, and for SG-01, SG-03/SG-04, SG-05, SG-02/SG-06 and SG-07 the ASIL targets marked with no computed value; the SG-01 estimate is drawn on the SG-03/SG-04 and SG-02/SG-06 rows too (DQ-362)](figures/fig-h04-5-1-metric-status.svg)

*Figure 5-1.* Top: the calculation steps of §3.2 with their status from the §5 table. Bottom: the §4 targets per safety-goal row of §7 on a 50–100 % scale; the hatched track means no metric exists (every “Met?” cell in §7 is “Not yet computed”). Hollow diamonds mark the generic-rate estimates of §5.2, which are not metrics; on the SG-03/SG-04 and SG-02/SG-06 rows they repeat the SG-01 estimate reused by DQ-362. The right column repeats the engineering judgement of §5.1, which is not a metric. Drawn from §4, §5, §5.1, §5.2 and §7. Source: [`figures/fig-h04-5-1-metric-status.svg`](figures/fig-h04-5-1-metric-status.svg); change it together with §4, §5 and §7.

### 5.2 Generic-rate estimate (not a metric)

[WP-H-03](WP-H-03-hardware-safety-analysis-fmeda.md) §6.3 keeps a block-level FMEDA with generic failure rates, plus one secondary-source rate: the harness box switches U1/U2 at the SN 29500-2 reference value. It is computed by `tools/safety/fmea_lint.py` from [`fmeda-sg001.yaml`](../08-analyses/fmea/analyses/fmeda-sg001.yaml) and [`fmeda-sg009.yaml`](../08-analyses/fmea/analyses/fmeda-sg009.yaml), rev 0.4, 2026-10-16 (rev 0.5 of 2026-10-18 adds the per-goal notes of DQ-362; the figures are unchanged). It shows where the architecture falls short. **It is not a metric and does not fill §7.**

| SG | λ (FIT) | SPFM | LFM | Against the current ASIL | Against ASIL B (DQ-063) |
|---|---|---|---|---|---|
| SG-01 | 255 | 96.8 % | 88.9 % | C: misses SPFM (97 %) by 0.2 points; LFM met | B: both met |
| SG-02, SG-03, SG-06 | SG-01 rows reused (DQ-362) | 96.8 % | 88.9 % | C: misses SPFM (97 %) by 0.16 points (96.84 %); LFM met. Open for G2 (OI-6) | — |
| SG-05 | SG-01 rows, FMD-001 and FMD-009 single-point (DQ-362, FMEDA rev 0.7) | 90.4 % | 95.3 % | B: met by 0.38 points on this estimate | — |
| SG-07 | 288 | 78.1 % | 97.6 % | B: misses SPFM (90 %); accepted as a recorded deviation (§5.3, DQ-320) | — |

With the planned measures and the DC assumptions stated in WP-H-03 §6.3, the estimates are:
- SG-01: 99.1 % / 95.4 %.
- SG-07: 94.5 %. This needs switch readback, the transceiver release and a stock-path continuity check; position readback alone gives 83.6 %.

The lead decided to reuse the SG-01 and SG-07 rows for SG-02, SG-03, SG-05 and SG-06, with a note per goal in WP-H-03 §6.4, rather than a separate FMEDA per goal ([DQ-362](../01-management/decisions/register.yaml), option A, 2026-10-18). The rows stay classified for SG-01, so the SG-02/SG-03/SG-06 line above is the shared-path estimate, not a goal-specific one. SG-05 has its own estimate since FMEDA rev 0.7: two of its rows are multiple-point for SG-01 but single-point for SG-05, recorded as `per_goal` entries (WP-H-03 §6.4). It meets B by only 0.38 points, so a small change to the CPU or SRAM rates can tip it.

### 5.3 Deviation: SG-07 SPFM with comma's harness box

The lead decided to keep comma's harness box and bench-test it, with no switch readback ([DQ-209](../01-management/decisions/register.yaml), option A). The lead then accepted the resulting SG-07 SPFM shortfall as a recorded deviation ([DQ-320](../01-management/decisions/register.yaml), option A, 2026-10-16).

| Field | Content |
|---|---|
| Deviation | SG-07 (LD-HARA-001 SG-009, ASIL B): SPFM below the 90 % target. 78.1 % on the generic-rate estimate of §5.2 |
| Cause | The stock camera-to-car path runs through two powered analog switches (U1/U2) with no position readback and no stock-path continuity check. Switch stuck in intercept or channel open is single-point for SG-07 (WP-H-03 §6.3) |
| Condition | The acceptance holds only once the harness box bench tests pass: VS-HW-02 and VS-HW-22…24 ([WP-H-06](WP-H-06-hardware-integration-verification.md) §3.1). The tested failure behaviour then becomes the assumption of use for the stock path. If a bench test fails, the deviation goes back to the lead |
| Argument to build | Bench-tested failure behaviour of the box, field use of the same box, the stock AEB fallback the driver keeps, and the remaining stock-path faults (VIN loss, clamp short) that are perceivable or detected |
| Not covered | The number rests on a secondary-source switch rate and generic discrete rates (WP-H-03 §2.3). A confirmed rate can move it either way; re-state it here when the rates are confirmed |
| Assessor | An assessor may not accept a metric miss on an ASIL B goal. The deviation is stated in the safety case, not hidden |
| Reopen | When the switch rate is confirmed, when a bench test fails, or at the G2 review |

## 6. Plan

| # | Activity | Depends on | Output | Gate |
|---|---|---|---|---|
| 1 | Fix the reference device revision and harness part number. Both boards stay in scope until one is fixed (DQ-011) | WP-C-01 | Configuration record | G1 |
| 2 | Obtain BOM/schematic from comma.ai (WP-H-02 OI-1; ask and wait, no teardown, DQ-065) | Supplier | BOM, schematic extract | G2 |
| 3 | Agree failure-rate sources (WP-H-03 OI-2) and the mission profile (WP-H-05 §3) | Safety manager | Decision record | G2 |
| 4 | Implement firmware mechanisms DC-01, DC-04…DC-10 in the panda fork | D-01 forks, D-04 HIL | Code + tests | G3 (2026-10-12: DC-01 implemented, not verified; DC-09 partial in the reference build) |
| 5 | Fault-injection campaign to justify DC claims (WP-H-06 VS-HW-xx) | HIL bench (deferred by the lead, DQ-049) | Test records | G3 (blocked while the bench is deferred) |
| 6 | Fill FMEDA, compute SPFM/LFM per SG, sensitivity analysis | 2–5 | Calculation + this document v1.0 | G3 |
| 7 | If targets are missed: decide DC-02/DC-03 harness adapter, or record the deviation and its rationale for the assessor. Added hardware is allowed in principle within an agreed budget (DQ-051); the harness route is DQ-209 | 6 | Decision record (WP-M-01 §8) | G3 |
| 8 | Independent review of the FMEDA and calculation | 6 | Review record ([WP-P-05](../07-supporting/WP-P-05-verification-review-procedure.md)) | G3 |

## 7. Results (template)

| SG | ASIL (at calculation) | Σλ (FIT) | Σλ_SPF (FIT) | Σλ_RF (FIT) | Σλ_MPF,L (FIT) | SPFM | Target | LFM | Target | Met? |
|---|---|---|---|---|---|---|---|---|---|---|
| SG-01 | | TBD — requires BOM | TBD | TBD | TBD | TBD | | TBD | | Not yet computed |
| SG-03/SG-04 | | TBD | TBD | TBD | TBD | TBD | | TBD | | Not yet computed |
| SG-05 | | TBD | TBD | TBD | TBD | TBD | | TBD | | Not yet computed |
| SG-02/SG-06 | | TBD | TBD | TBD | TBD | TBD | | TBD | | Not yet computed |
| SG-07 | | TBD | TBD | TBD | TBD | TBD | | TBD | | Not yet computed |

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | BOM and schematic (plan step 2) | G2 |
| OI-2 | ~~Decide whether SG-01 metrics are computed against B or C at G3~~ **Decided** (DQ-063, 2026-10-14): against C until the HARA re-rates SG-01, with B shown alongside (§4) | G2 |
| OI-3 | Exclusion of QM-SoC mechanisms from DC (§3.3) kept as an internal method choice (DQ-070 A, 2026-10-22); confirm it with the external assessor once one is engaged (none yet, DQ-009 C) | G2 |
| OI-4 | Define the start-up test set needed for LFM (IWDG test reset, ECC test, relay check by a controlled toggle with readback, siren self-test) and its effect on availability | G3 |
| OI-5 | Verify target values and metric definitions against the licensed ISO 26262-5 | G2 |
| OI-6 | SG-01, SG-02, SG-03, SG-06 (ASIL C): SPFM 96.84 % on the shared generic-rate estimate, 0.16 points below 97 %. The lead decided not to license ST's safety package and to write LionDriver's own self-tests with low CPU coverage ([DQ-069](../01-management/decisions/register.yaml), option B, 2026-10-19), so the ASIL C SPFM target is **likely missed**; the gap moves to G2. Routes left: the TSR-517 transmit read-back (estimate 97.53 % at an assumed DC 99 %, WP-H-03 §6.4) and handbook rates (WP-H-03 OI-3/OI-10). If neither closes it by G2, back to the lead (DQ-362) | G2 |
