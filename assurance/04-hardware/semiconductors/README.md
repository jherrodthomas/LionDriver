# Semiconductors (ISO 26262-11)

ISO 26262-11 is the informative part of ISO 26262 on semiconductors. It produces no work products of its own
([WP-M-00](../../01-management/WP-M-00-work-product-register.md) §5). It explains how Parts 5, 8 and 9 apply inside a chip:
how to split a chip into parts and sub-parts, which fault models to use, how to estimate base failure rates, how to look
for dependent failures inside the die, and what to ask of a chip supplier. This folder holds the records where LionDriver
does that work. They support [WP-H-03](../WP-H-03-hardware-safety-analysis-fmeda.md) (the FMEDA, including the MCU split of
§6.2) and [WP-H-07](../WP-H-07-hardware-component-qualification.md) (component qualification, §7).

| Field | Value |
|---|---|
| Record | Supporting records of WP-H-03 and WP-H-07; not a registered work product |
| Version | 0.1 (2026-11-19): folder created with the method demonstration; the chip dossiers are planned, not started |
| Status | Draft. Nothing here has been reviewed. The method demonstration is not evidence for LionDriver |
| Author | Claude (AI-assisted draft, I0 under WP-M-02 §3.3) |
| Reviewer(s) | TBD |

## 1. Where each Part 11 topic is answered

ISO 26262-11:2018 clause numbers below are from the published table of contents; they are not checked against the
licensed text.

| Part 11 topic | Where LionDriver answers it | State |
|---|---|---|
| §4.1–4.3 a semiconductor component, its parts and sub-parts, fault models, failure modes | [WP-H-03](../WP-H-03-hardware-safety-analysis-fmeda.md) §6.2 (STM32H725 split); the method demonstration below shows the split on a real netlist | Template in WP-H-03; method shown |
| §4.5 intellectual property (licensed blocks inside a chip) | Not applicable: LionDriver buys finished chips and integrates no IP | Rationale only |
| §4.6 base failure rate for semiconductors | [WP-H-03](../WP-H-03-hardware-safety-analysis-fmeda.md) §2.3 (handbook die and package model, DQ-068) | Draft |
| §4.7 dependent failures inside a chip (shared supply, clock, reset, debug) | Planned `stm32h725/` on-chip DFA, feeding [WP-A-03](../../08-analyses/WP-A-03-dependent-failure-analysis.md) | Planned |
| §4.8, §4.9 production, operation, distributed development (errata, change notices, safety manual) | Planned `stm32h725/` dossier: part identity (WP-H-07 OI-3), errata review, the public STM32H7 safety manual's conditions of use as firmware requirements | Planned |
| §5.1 digital components and memories | Method demonstration: self-test coverage, ECC and lockstep measured on a real netlist | Method shown |
| §5.2 analog and mixed-signal | Harness-box analog switches, CAN transceivers, regulators in [`../fmeda/`](../fmeda/README.md) | Draft |
| §5.3 programmable logic | Not applicable: the item has no programmable logic device | Rationale only |
| §5.4 multi-core | The SoC (QM, interference only, WP-C-04 OI-11) | Planned |
| §5.5 sensors and transducers | The cameras and IMU behind SG-08 driver monitoring | Planned |

## 2. Subfolders

| Folder | What it holds |
|---|---|
| [`method-demo/`](method-demo/README.md) | The Part 11 method run end to end on an open RISC-V core: synthesis to real cells, sub-part split, self-test fault campaign, ECC and lockstep measured, with figures |
