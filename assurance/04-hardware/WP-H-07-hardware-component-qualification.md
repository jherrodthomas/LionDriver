# WP-H-07 Qualification of hardware components

| Field | Value |
|---|---|
| Work product | WP-H-07 Qualification of hardware components (comma device, STM32H7, harness) |
| Standard reference | ISO 26262-8:2018 §13 (qualification of hardware components); ISO 26262-5:2018 §7–§9 (for complex elements); ISO 26262-11:2018 (semiconductors, informative); ASPICE 4.0 — (no direct process; supports HWE.1–4 at CL1 per T-12) |
| Version | 0.4 (OI-6 closed: the §5 residual risks are recorded as WP-M-07 R-30 and WP-K-01 DF-42; 2026-10-19). 0.3 (decisions applied 2026-10-19: no ST licence, own self-tests with low CPU coverage, DQ-069 option B (QE-03, §5, OI-2); §5 residual risks accepted with the stated conditions, EMC and environment recorded as residual risks, DQ-078 option A (OI-6); harness rows re-based from a relay to the harness box v3 analog switches (RR-2026-010), with the Toyota A harness and box v3 still assumed, not read from the parts, DQ-211 option C). 0.2 (OI-5: no teardown, DQ-065; 2026-10-16). 0.1 |
| Status | Draft (qualification plan; no qualification performed) |
| ASIL / scope | ASIL C (SG-01 provisional; SG-02, SG-03, SG-06 since WP-C-03 v0.4) / ASIL B (SG-04, SG-05, SG-07) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1 minimum, external reviewer, T-09) |
| Approver | TBD (per [WP-M-02](../01-management/WP-M-02-safety-plan.md)) |
| Baseline | `8b8c6ae` |

## 1. Purpose

Under tailoring **T-04** ([WP-M-01](../01-management/WP-M-01-assurance-strategy.md)) the comma
device and its safety MCU are treated as COTS hardware components, qualified per ISO 26262-8 §13,
with hardware metrics computed by LionDriver ([WP-H-04](WP-H-04-hardware-metrics.md),
[WP-H-05](WP-H-05-random-hardware-failures-pmhf.md)). comma.ai is an upstream supplier with no
development interface agreement (T-08, [WP-M-11](../01-management/WP-M-11-upstream-and-supplier-management.md)).

This document is the **qualification plan**: which components, which method, what evidence is
needed from suppliers, what LionDriver tests itself, and what residual risk remains if supplier
evidence is not available. No qualification activity has been performed.

## 2. Components to qualify

| QC-ID | Component | Contains | Safety relevance | Complexity |
|---|---|---|---|---|
| QC-01 | comma device (reference revision, WP-C-01) as an assembled module | PCB, power conversion, SoC module, panda MCU, transceivers, connectors, enclosure, fan | Carries E-03 (envelope) and E-01/E-02 (QM) | Assembly of complex and simple parts |
| QC-02 | STM32H725 safety MCU (panda) | Cortex-M7, flash, SRAM with ECC, FDCAN ×3, IWDG, CSS, PVD/BOR, MPU | Executes the envelope; all SGs | Complex (microcontroller) |
| QC-03 | CAN transceivers ×4 (part numbers unknown) | Physical layer | SG-01, SG-03…SG-07 | Simple–medium |
| QC-04 | Toyota TSS2 harness with the harness box v3 (assumed: Toyota A harness, box v3, not yet read from the parts, [DQ-211](../01-management/decisions/register.yaml) option C) | Intercept switch: two DG419LE CMOS analog switches U1/U2 driven by SBU1 with the R2/R3 pull-down (no relay, [RR-2026-010](reviews/RR-2026-010.md)); box supply D1/D4; clamps D2/D3; wiring, connectors | SG-01 (blocks stock control), SG-07 (stock PCS path) | Simple |
| QC-05 | MCU power supply chain and supervision (regulator, any supervisor, input protection) | Unknown parts | All SGs | Simple–medium |
| QC-06 | Application SoC module (Qualcomm SD845) | — | QM; only freedom-from-interference properties (it controls MCU reset and boot pins, GAP-38) | Complex; **not qualified to an ASIL**; covered by WP-A-02/WP-A-03 |

## 3. Qualification approach

### 3.1 Applicability of 26262-8 §13

ISO 26262-8:2018 §13 distinguishes hardware elements by complexity. For the simplest elements,
qualification by analysis and testing against their specification is sufficient. A microcontroller
belongs to the most complex class, for which qualification alone is not considered sufficient:
its safety-related failure modes must be handled through the ISO 26262-5 safety analyses and
metrics, with ISO 26262-11 as guidance. **Verify the class definitions and the exact
requirements against the licensed text (OI-1).**

Consequences for LionDriver:

| QC | Route |
|---|---|
| QC-02 STM32H725 | 26262-5 route: FMEDA with MCU internal split ([WP-H-03](WP-H-03-hardware-safety-analysis-fmeda.md) §6.2), safety mechanisms in firmware, metrics (WP-H-04/-05), plus 8 §13-style evidence of the component's suitability (datasheet operating conditions, errata review, quality grade) |
| QC-03, QC-04, QC-05 | 8 §13 qualification by analysis + testing, plus inclusion in the FMEDA |
| QC-01 | Module-level qualification by analysis (supplier evidence) + LionDriver testing of the safety-relevant functions ([WP-H-06](WP-H-06-hardware-integration-verification.md)); the module's parts enter the FMEDA individually |
| QC-06 | Not qualified; interference analysis only |

### 3.2 Qualification method per component

For each component the plan follows the same steps:

1. **Specify** the required functional and non-functional properties and the operating conditions
   (mission profile: in-cabin, windscreen mount, vehicle supply, temperature range).
2. **Collect evidence** from the supplier (§4).
3. **Analyse**: compare supplier specification and evidence with the required properties; review
   errata and known field issues; check that the component is used within its specification.
4. **Test** what LionDriver can test on the bench (WP-H-06) to confirm the safety-relevant
   behaviour (failure modes and safety-mechanism function, not environmental robustness).
5. **Decide**: qualified, qualified with restrictions (recorded as assumptions of use), or not
   qualified (residual risk §5, decision by the safety manager).
6. **Record** the qualification report (template §6) under configuration control; any change of
   part, revision or supplier triggers requalification (impact analysis, [WP-M-12](../01-management/WP-M-12-impact-analysis.md)).

## 4. Evidence needed

| QE-ID | Evidence | From | For | Available? |
|---|---|---|---|---|
| QE-01 | Device schematic and BOM with manufacturer part numbers, board revision identification | comma.ai | QC-01, -03, -05; FMEDA | Not available (WP-H-02 UK-01/02) |
| QE-02 | STM32H72x/73x failure rates (FIT) and failure-mode distribution per functional block; reliability report (HTOL, package qualification) | STMicroelectronics | QC-02; FMEDA, PMHF | **To verify.** ST publishes reliability reports for many products; a per-block FMEDA is typically supplied only within a functional-safety package |
| QE-03 | ST functional-safety documentation applicable to STM32H7: safety manual, FMEA/FMEDA report, self-test library | STMicroelectronics | QC-02; DC claims for CPU/RAM | **To verify.** ST offers functional-safety packages for several STM32 series aimed at IEC 61508 (safety manual, FMEA/FMEDA, the X-CUBE-STL self-test library). Whether a package covers the STM32H72x/73x line, its licence terms, and the conditions of use must be confirmed. These target IEC 61508, not ISO 26262; their content is input, not an ISO 26262 claim |
| QE-04 | Datasheet, reference manual (RM0468) and errata sheet for the exact ordering code and silicon revision | ST (public) | QC-02 | Public; ordering code and temperature grade of the fitted part unknown (QE-01) |
| QE-05 | Intercept switch data: DG419LE ratings (supply, logic thresholds, unpowered behaviour), harness box schematic, state with the box unpowered or SBU1 undriven | comma.ai / Vishay | QC-04; AOU-13 | Harness box v3 drawing published (RR-2026-010). DG419LE datasheet not yet read (DFMEA DFM-ACT-015). No teardown (DQ-065); failure behaviour by bench test instead (WP-H-06 VS-HW-02, VS-HW-22…24; DQ-209) |
| QE-06 | Transceiver datasheets incl. qualification grade (e.g. AEC-Q100) and failure behaviour (dominant time-out, behaviour unpowered) | Transceiver maker | QC-03 | Needs part numbers (QE-01) |
| QE-07 | Device EMC test reports (emission, immunity, supply transients) | comma.ai | QC-01 | Unknown |
| QE-08 | Device environmental and durability tests (temperature, humidity, vibration, sun load) | comma.ai | QC-01 | Unknown |
| QE-09 | Manufacturing quality system and change-notification practice (how board/component changes are communicated) | comma.ai | QC-01 (configuration of the qualified item) | Unknown |
| QE-10 | Field return / failure data for devices and harnesses | comma.ai | QC-01, QC-04; supports rate estimates (not proven-in-use, T-06) | Unknown |
| QE-11 | MCU option-byte configuration on shipped devices (RDP, WRP, BOR, IWDG options) | Read-out by LionDriver | QC-02 | Can be obtained (WP-H-02 UK-04) |

### 4.1 Notes on the STM32H7

- The STM32H7 is an industrial/general-purpose microcontroller. The project does not know of an
  AEC-Q100-qualified variant of the fitted part; **verify** (QE-04). Without automotive grade
  qualification, the argument must rest on the datasheet operating conditions being met in the
  mission profile and on the safety mechanisms.
- Silicon safety features relevant to the FMEDA (to be confirmed per RM0468 and the datasheet,
  [WP-H-02](WP-H-02-hardware-design.md) §4): ECC on flash and SRAM with RAMECC monitors, IWDG with
  window on an independent oscillator, CSS on the HSE, BOR/PVD, MPU, CRC unit.
- Single core without lockstep. No hardware redundancy for CPU logic; CPU coverage depends on a
  software self-test library and program-flow monitoring (WP-H-03 FM-CPU-01).
- The firmware is built for `STM32H725xx` (`panda/SConscript:137`) while the linker script header
  names STM32H735ZGTx (`panda/board/stm32h7/stm32h7x5_flash.ld:8-10`), and the clock code expects
  either H725 (SMPS packages) or H723 (`panda/board/stm32h7/clock.h:28-48`). The exact fitted part
  per board revision must be confirmed (OI-3).

### 4.2 Notes on the comma device

- It is a consumer aftermarket product. No ISO 26262, AEC or IATF evidence is known to the project.
- It is mounted on the windscreen: high temperature exposure from sun load is the dominant
  environmental stress. The host already throttles and disengages on SoC temperature
  (`openpilot/system/hardware/hardwared.py:93-103, 360-366`), but the panda's own temperature is
  not used for any reaction (WP-H-01 HWSR-509).
- The SoC controls the MCU's reset and boot pins (`openpilot/common/hardware/comma/hardware.py:401-419`,
  GAP-38). This is an interference path to be covered in WP-A-02, not a qualification topic.

### 4.3 Notes on the harness

- The intercept switch (U1/U2 in the harness box v3, [RR-2026-010](reviews/RR-2026-010.md)) is the only hardware element between the stock camera and the vehicle. Its pass-through state with SBU1 undriven carries SG-07 (AOU-13, FSC OI-6); whether it holds with the box unpowered is to be shown on the bench (RR-2026-010 F-02, VS-HW-22).
- The earlier relay-life note no longer applies: an analog switch has no contact wear. Supply transients against the DG419LE ratings take its place (RR-2026-010 F-05, DFM-010.C4, VS-HW-24).
- The harness letter and box revision on the reference Corolla are assumed (Toyota A, box v3), not yet read from the parts. The lead kept that assumption for now ([DQ-211](../01-management/decisions/register.yaml), option C, 2026-10-19), so G1 cannot close the harness item; if the parts differ, the harness analysis is redone.

## 5. Residual risk if supplier evidence is unavailable

| Missing evidence | Fallback | Residual risk | Accept? |
|---|---|---|---|
| QE-01 schematic/BOM | Ask comma.ai and wait, no teardown (DQ-065); the published harness box v3 drawing; block-level analysis with generic rates (WP-H-03 §6.3) | Part identification errors; no data for hidden parts; board revisions may change silently | **Accepted** with re-check per purchased batch (incoming inspection in [WP-O-01](../09-production-operation/WP-O-01-installation-and-provisioning-control.md)) |
| QE-02 ST FIT data | Handbook die/package model (WP-H-03 §2.3, approved DQ-068), conservative assumptions, sensitivity analysis; ST data used only if given without a licence (DQ-069) | Metric uncertainty; possible optimism or pessimism | **Accepted** with the condition that a sensitivity analysis is reported with the metrics |
| QE-03 ST safety package | LionDriver writes own CPU/RAM start-up and periodic tests; DC claimed only at "low" for CPU | Lower DC. The ASIL C SPFM target (SG-01, SG-02, SG-03, SG-06) is likely missed; the gap moves to G2 (WP-H-04 OI-6) | **Decided:** no licence, own self-tests, low CPU coverage ([DQ-069](../01-management/decisions/register.yaml), option B, 2026-10-19) |
| QE-05 intercept switch data | Bench tests of the harness box failure behaviour (VS-HW-02, VS-HW-22…24); SN 29500-2 reference rate for U1/U2 (secondary source) | SG-07 metric uncertainty; SPFM 78.1 % below the ASIL B target | **Accepted as a recorded deviation**, conditional on the bench tests (no readback, DQ-209 option A; DQ-320 option A; WP-H-04 §5.3) |
| QE-07/QE-08 EMC, environment | No LionDriver test; argue robustness by safety mechanisms (watchdog, ECC, safe state on reset) | Systematic susceptibility undetected; common-cause failures | **Accepted as residual risk** ([DQ-078](../01-management/decisions/register.yaml), option A, 2026-10-19): recorded in the safety case ([WP-K-01](../10-safety-case/WP-K-01-safety-case.md)) and the risk register ([WP-M-07](../01-management/WP-M-07-risk-management.md)), and assessed by the external assessor |
| QE-09 change notification | Identify revision by `hw_type`, MCU UID and visual inspection per batch | Unnoticed changes | Acceptable with incoming inspection |
| QE-10 field data | None | No empirical confirmation | Accepted (T-06: no proven-in-use claim) |

**Decision.** The lead accepted the residual risks of this table with the conditions stated in it ([DQ-078](../01-management/decisions/register.yaml), option A, 2026-10-19): incoming inspection of each batch, sensitivity on the handbook rates, and EMC and environmental robustness recorded as residual risks in WP-K-01 and WP-M-07. The claim therefore rests on handbook data and on the safety mechanisms, and a reviewer will see these limits.

If the residual risk for QC-01/QC-02 is later judged not acceptable, the alternatives are: the harness
adapter with external supervisor and switch readback (WP-H-02 DC-02/DC-03), which moves part of
the safety function onto LionDriver-controlled, analysable hardware; or restriction of the claim
(e.g. a lower ASIL via FSC option (c)).

## 6. Qualification report template (per component)

| Field | Content |
|---|---|
| Component (QC-ID, part, revision, supplier) | |
| Required properties and operating conditions | |
| Evidence obtained (QE-IDs, document IDs, revisions) | |
| Analysis results (specification vs requirement, errata review) | |
| Tests performed (VS-HW IDs, results) | Not yet executed |
| Restrictions / assumptions of use | |
| Residual risk | |
| Verdict (qualified / with restrictions / not qualified) | Not yet determined |
| Reviewer, independence level, date | |

## 7. Informative guidance from ISO 26262-11 used in this plan

ISO 26262-11 is informative. The following topics are used as hints for QC-02 and QC-06:

| Topic | Use here |
|---|---|
| Splitting a microcontroller into parts and sub-parts and assigning failure modes per part | WP-H-03 §6.2 structure |
| Permanent and transient faults counted separately; transient fault rates from soft-error data | WP-H-03 §2.3 |
| Estimating base failure rates when supplier data is limited, and accounting for the mission profile | WP-H-03 §2.3, WP-H-05 §3 |
| Dependent failures inside a chip (shared clock, power, reset, test/debug logic) | Input to [WP-A-03](../08-analyses/WP-A-03-dependent-failure-analysis.md): IWDG and CPU share supply and reset; SWD debug access (`ALLOW_DEBUG` builds, GAP-25) |
| Use of components developed outside ISO 26262 and the evidence to ask the supplier for | §4 evidence list |
| Programmable/complex components and the role of the safety manual's assumptions | QE-03: any ST safety-manual assumptions become AoUs on the LionDriver firmware |

## 8. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Verify the hardware element classes and requirements of 26262-8 §13 against the licensed text and adjust §3.1 | G2 |
| OI-2 | Contact ST for QE-02 data available without a licence. No safety-package licence is bought ([DQ-069](../01-management/decisions/register.yaml), option B, 2026-10-19); the QE-03 question is closed | G2 |
| OI-3 | Confirm the fitted MCU ordering code, package and temperature grade on the reference device (H725 vs H735 vs H723) | G2 |
| OI-4 | Contact comma.ai for QE-01, QE-05, QE-07…QE-10 under WP-M-11 | G2 |
| OI-5 | ~~Plan the teardown of one device and one harness if comma.ai declines~~ **Not planned:** the lead chose to ask comma.ai and wait, with no teardown (DQ-065, option B, 2026-10-14). Revisit only if the lead reopens that decision | G2 |
| OI-6 | ~~Record residual risks of §5 in the safety case and the risk register~~ **Closed 2026-10-19:** accepted by the lead ([DQ-078](../01-management/decisions/register.yaml), option A) and recorded as [WP-M-07](../01-management/WP-M-07-risk-management.md) R-30 and [WP-K-01](../10-safety-case/WP-K-01-safety-case.md) DF-42 | G3 |
