# WP-H-04 Hardware architectural metrics (SPFM, LFM)

| Field | Value |
|---|---|
| Work product | WP-H-04 Hardware architectural metrics (SPFM, LFM) |
| Standard reference | ISO 26262-5:2018 §8 (evaluation of the hardware architectural metrics), Annex C (metric definitions, informative), Annex D (diagnostic coverage, informative); ISO 26262-11:2018 (semiconductors, informative) |
| Version | 0.1 |
| Status | Draft (method and plan; no metric computed) |
| ASIL / scope | ASIL D (provisional, SG-01, until re-rated under FSC option (c)) / ASIL C (SG-03…SG-05) / ASIL B (SG-02, SG-06, SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `8b8c6ae` |

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
| Mechanisms in the QM SoC (e.g. host-side `controlsMismatch`, `canError`) are **not** credited for SPF/RF coverage | They are QM; crediting them would need the SoC to be developed to the ASIL |
| Vehicle measures (EPS LKA limit and timeout, PCM clamp) are **not** credited as DC | External measures; they are handled in the PMHF/EEC argument ([WP-H-05](WP-H-05-random-hardware-failures-pmhf.md) §5) and in the HARA controllability |
| Driver perception counts as latent-fault detection only for effects the driver cannot miss (e.g. engagement refused at start-up with a visible message) | Matches the "perceived" class |
| Start-up tests count for latent faults if executed every drive cycle and if their result blocks engagement | Drive-cycle interval is the multiple-point fault detection interval assumed here |

## 4. Targets

| Metric | ASIL B | ASIL C | ASIL D | Source |
|---|---|---|---|---|
| SPFM | ≥ 90 % | ≥ 97 % | ≥ 99 % | ISO 26262-5 §8 (commonly used values — **verify against licensed text**) |
| LFM | ≥ 60 % | ≥ 80 % | ≥ 90 % | as above |

Applicable targets ([WP-H-01](WP-H-01-hardware-safety-requirements.md) §3):

| SG | Current ASIL | Target set | Expected after FSC option (c) |
|---|---|---|---|
| SG-01 | D (provisional, D-09) | SPFM ≥ 99 %, LFM ≥ 90 % | B: SPFM ≥ 90 %, LFM ≥ 60 % |
| SG-03…SG-05 | C (D-09) | SPFM ≥ 97 %, LFM ≥ 80 % | unchanged (C unless re-rated) |
| SG-02, SG-06 | B | SPFM ≥ 90 %, LFM ≥ 60 % | unchanged |
| SG-07 | B | SPFM ≥ 90 %, LFM ≥ 60 % | unchanged |

## 5. Current status

| Step (§3.2) | Status |
|---|---|
| 1 Configuration frozen | No: reference device revision not fixed (WP-H-01 OI-7) |
| 2 FMEDA filled | No: qualitative block-level FMEA only (WP-H-03 §4) |
| 3–4 Classification and DC | Qualitative only |
| 5 Calculation | **Cannot be computed: no BOM** |
| 6 Sensitivity | Not started |
| 7 Review | Not started |

### 5.1 Provisional qualitative assessment

This is engineering judgement, not a metric. It is stated so the decisions in the FSC can be
made with eyes open.

**Baseline hardware and firmware (`8b8c6ae`): the ASIL B targets are very likely not met for
SG-01 or SG-07, and the ASIL C (SG-03…SG-05) and ASIL D (SG-01) targets are not met.** Reasons:

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

**With the firmware-only changes of WP-H-02 §6 (DC-01, DC-04…DC-10):** SPFM ≥ 90 % for SG-01 looks
*plausible but not certain*. The CPU core remains at "medium" coverage at best on a single
non-lockstep core with a software test library; whether that is enough depends on the CPU's share
of the total rate. ASIL C (97 %), which applies to SG-03…SG-05 on the same MCU since D-09, is *unlikely*
without DC-02 (external supervisor) or a second channel. ASIL D (99 %) for SG-01 is even less likely:
DC-02 and/or a second independent channel (monitoring MCU) become effectively required unless
option (c) succeeds. This supports the FSC recommendation of option (c).

**For SG-07:** ASIL B is *unlikely* to be met without relay readback (DC-03) unless the relay's
"stuck intercepting" rate is shown to be small relative to the total, which needs part data.

## 6. Plan

| # | Activity | Depends on | Output | Gate |
|---|---|---|---|---|
| 1 | Fix the reference device revision and harness part number | WP-C-01 | Configuration record | G1 |
| 2 | Obtain BOM/schematic from comma.ai or perform a teardown (WP-H-02 OI-1) | Supplier | BOM, schematic extract | G2 |
| 3 | Agree failure-rate sources (WP-H-03 OI-2) and the mission profile (WP-H-05 §3) | Safety manager | Decision record | G2 |
| 4 | Implement firmware mechanisms DC-01, DC-04…DC-10 in the panda fork | D-01 forks, D-04 HIL | Code + tests | G3 |
| 5 | Fault-injection campaign to justify DC claims (WP-H-06 VS-HW-xx) | HIL bench | Test records | G3 |
| 6 | Fill FMEDA, compute SPFM/LFM per SG, sensitivity analysis | 2–5 | Calculation + this document v1.0 | G3 |
| 7 | If targets are missed: decide DC-02/DC-03 harness adapter, or record the deviation and its rationale for the assessor | 6 | Decision record (WP-M-01 §8) | G3 |
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
| OI-2 | Decide whether SG-01 metrics are computed against B or C at G3 (depends on HARA re-rating, FSC OI-2) | G2 |
| OI-3 | Confirm that QM-SoC mechanisms are excluded from DC (§3.3) with the external assessor | G2 |
| OI-4 | Define the start-up test set needed for LFM (IWDG test reset, ECC test, relay check by a controlled toggle with readback, siren self-test) and its effect on availability | G3 |
| OI-5 | Verify target values and metric definitions against the licensed ISO 26262-5 | G2 |
