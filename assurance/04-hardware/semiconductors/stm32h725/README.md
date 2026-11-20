# STM32H725 dossier (the panda safety MCU)

The ISO 26262-11 record for the one chip that carries LionDriver's safety envelope: the STM32H725 on the panda board
inside the comma device. It collects what is known about the part, what each of its safety features does in the
firmware today, and what inside the chip can fail two things at once. It feeds the MCU split of
[WP-H-03](../../WP-H-03-hardware-safety-analysis-fmeda.md) §6.2, the qualification of QC-02 in
[WP-H-07](../../WP-H-07-hardware-component-qualification.md) and the dependent-failure analysis
[WP-A-03](../../../08-analyses/WP-A-03-dependent-failure-analysis.md).

| Field | Value |
|---|---|
| Record | Supporting record of WP-H-03, WP-H-07 and WP-A-03; not a registered work product |
| Version | 0.1 (2026-11-20): identity, 15 safety features checked against the firmware, on-chip dependent failures with Figure 1. Errata review and safety-manual intake not started (§4) |
| Status | Draft, not reviewed. AI-drafted (I0 under WP-M-02 §3.3) |
| Firmware checked | panda at the LionDriver submodule pin `fd0a6a7`; every reference below is a path:line in that tree |
| Records | [`features.yaml`](features.yaml) (MF-01 to MF-15), [`onchip-dfa.yaml`](onchip-dfa.yaml) |

## 1. Which part

| Question | What the code says | Source |
|---|---|---|
| Family | The firmware accepts only device code 0x483, the STM32H72x/73x family, and sends any other chip to the bootloader | `board/early_init.h:47-49`, `board/stm32h7/stm32h7_config.h:5` |
| Part number | Built for STM32H725 (`-DSTM32H725xx`); the linker script header names STM32H735ZGTx; the clock code accepts an STM32H725 in an SMPS package (LQFP144, UFBGA169) or an STM32H723 in TFBGA100, chosen at run time from the package register | `SConscript:148`, `board/stm32h7/stm32h7x5_flash.ld:9`, `board/stm32h7/clock.h:29-48` |
| Boards | tres (comma 3X) and cuatro (comma four), both in scope | [WP-C-01](../../../02-concept/WP-C-01-item-definition.md), [WP-H-02](../../WP-H-02-hardware-design.md) |
| Ordering code, package, temperature grade | Unknown | WP-H-07 OI-3, WP-H-02 UK-02 |
| Silicon revision | Unknown: the firmware never reads the revision half of IDCODE (MF-13) | `board/early_init.h:47` |

The revision decides which errata apply (§4), and the temperature grade decides whether the windscreen mission profile
is inside the datasheet's range. Both can be read from a device without changing it: the part marking, and the IDCODE
and package registers over the debug port or through a one-line addition to the firmware's version report (OI-2).

## 2. What each safety feature does today

[`features.yaml`](features.yaml) checks fifteen features against the firmware, each with what it detects, whether the
firmware uses it, what actually happens when it fires, and the finding the FMEDA or the DFA must carry. It goes one step
further than the feature table of [WP-H-02](../../WP-H-02-hardware-design.md) §4: it follows each detection to its
reaction in the code.

| ID | Feature | Firmware | Reaction today |
|---|---|---|---|
| MF-01 | Independent watchdog (IWDG1) | used | reset, from the first relay drive on |
| MF-02 | Window watchdog (WWDG1) | not used | none |
| MF-03 | Clock security system (CSS) | used | NMI, reset; then an endless wait for the crystal |
| MF-04 | Brown-out reset (BOR) | not set by the firmware | as the option bytes leave it (unknown) |
| MF-05 | Voltage detector (PVD/AVD) | not used | none |
| MF-06 | SRAM ECC and RAMECC monitors | partly | single errors corrected and uncounted; double errors reset through HardFault |
| MF-07 | Flash ECC | not used | as MF-06; no periodic image check |
| MF-08 | MPU | not used | none |
| MF-09 | Level-1 caches | not enabled | not a sub-part of the FMEDA while they stay off |
| MF-10 | CRC unit | not used | none |
| MF-11 | Temperature sensor (DTS) | partly | reported to the host, no reaction |
| MF-12 | Fault exceptions, default handler | partly | HardFault resets; an unhandled interrupt loops for ever |
| MF-13 | Device identity check | partly | family checked; revision never read |
| MF-14 | Debug port (SWD), watchdog freeze | partly | SWD left on in every build; freeze bit never set |
| MF-15 | Package and supply check | used | unknown package: endless loop |

### 2.1 Findings

Findings not yet covered by a WP-H-02 design change are marked **new**.

1. **A silent hang before the watchdog runs (new).** After a crystal failure the CSS resets the MCU, and clock_init then
   waits for the crystal with no time-out (MF-03); an unknown package code loops the same way (MF-15). The watchdog is
   started only at the first relay drive, so nothing ends either loop. The GPIOs stay floated, so the stock path holds
   and SG-07 is not violated, but the device goes silent and never reports why. This interacts with the decision to start
   the watchdog at the first relay drive and not in the bootstub (DQ-149), so it is an open item, not a fix (OI-1).
2. **The silicon revision is unknown (new).** Without it the errata cannot be matched to a device (MF-13; OI-2).
3. **The debug port stays on in release and reference builds.** Whether a debugger can connect depends on the read-out
   protection level, which nobody has read (MF-14, WP-H-02 UK-04, DC-07). It is two of the four common-cause cells in §3.
4. **Corrected memory errors are invisible.** Single-bit errors in SRAM and flash are corrected and counted nowhere, so an
   accumulating fault stays latent until it becomes uncorrectable (MF-06, MF-07; DC-05). The uncorrectable case resets,
   which is the safe state, but is not told apart from any other HardFault.
5. **The caches are off.** That keeps them out of the MCU split in WP-H-03 §6.2 (MF-09). A change that enables them
   must add them back.

## 3. What inside the chip can fail two things at once

![Figure 1: matrix of six shared causes inside the STM32H725 (core supply, main clock, watchdog clock, reset, debug access, die temperature) against five mechanisms (IWDG, CSS, ECC, BOR, software checks on the CPU); 4 common-cause cells, 12 partial, 14 independent; the common causes are the supply and the main clock for the software checks, and debug access for the IWDG and the software checks](figures/fig-h07-semi-1-onchip-dfa.svg)

*Figure 1.* Read across a row to see what one shared cause can take out together. There are 4 common-cause cells, 12
partial and 14 independent. Two common-cause cells are the nature of a single CPU checking itself: the software checks
share the CPU's supply and clock. The argument against them is the watchdog on its own clock with a reset as the safe
state, plus the external supervisor of WP-H-02 DC-02 if the ASIL needs more. The other two come from the debug port
(finding 3). Drawn from [`onchip-dfa.yaml`](onchip-dfa.yaml) by
[`figures/fig_h07_onchip_dfa.py`](figures/fig_h07_onchip_dfa.py); CI fails if it is stale, or if a cell cites a
feature that [`features.yaml`](features.yaml) does not have.

## 4. Errata and the safety manual: not started

Both need ST documents that could not be obtained here: on 2026-11-20 ST's document servers (st.com and st.com.cn)
refused every automated download from this environment. Nothing below is assumed in their place.

| Document | Needed for | State |
|---|---|---|
| ES0491, STM32H72x/73x errata sheet | Each erratum against what the firmware uses (FDCAN, IWDG, ECC, RCC, PWR, SPI, DMA, USB, ADC): relevant or not, workaround present or not; matched to the revision of §1 | Not obtained |
| STM32H7 safety manual (believed to be UM2331; whether it covers the H72x/73x line is to be checked) | Its conditions of use become requirements on the firmware or recorded deviations (WP-H-07 QE-03; the paid ST package stays declined, DQ-069) | Not obtained |
| RM0468, reference manual | The `to-confirm` entries of `features.yaml` and the cells whose basis is RM0468 | Not obtained |
| STM32H725 datasheet | LSI minimum and maximum for the IWDG time-out (WP-H-07 OI-7); temperature grades | Not obtained |

When the PDFs are available (downloaded by hand and attached to a session, for instance), the intake becomes
`errata.yaml` and `aou-intake.yaml` in this folder, in the same form as `features.yaml` (OI-3, OI-4).

## 5. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | The silent hang of finding 1: decide between a bounded wait that resets, an early watchdog for the clock set-up only, or a recorded acceptance; the choice touches DQ-149 | G3 |
| OI-2 | Read the ordering code, package, temperature grade and silicon revision from a reference device (part marking; IDCODE and PKGR read-only), or report them in the firmware's version packet | G2 |
| OI-3 | Errata review against ES0491 for the revision of OI-2 | G2 |
| OI-4 | Safety-manual intake: confirm the document covers the STM32H72x/73x, then turn each condition of use into a firmware requirement or a deviation | G2 |
| OI-5 | Confirm the `to-confirm` features and the RM0468 cells from the reference manual, including the reset value of the IWDG debug-freeze bit | G2 |
| OI-6 | Carry §3 into WP-A-03 as the on-chip part of the dependent-failure analysis | G3 |
