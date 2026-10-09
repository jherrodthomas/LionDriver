# WP-A-04 System-Level Safety Analyses (FTA, FMEA)

| Field | Value |
|---|---|
| Work product | WP-A-04 System-level safety analyses (FTA, FMEA) |
| Standard reference | ISO 26262-9:2018 §8 (safety analyses); ISO 26262-4:2018 §6 (safety analysis of the system architectural design, to support the TSC); ISO 21448:2022 §7 (input on insufficiencies, informative here); ASPICE 4.0 SYS.3 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | SG-01 (ASIL C ⚠) and SG-03 (ASIL B ⚠) fault trees; system FMEA covering SG-01…SG-07. Qualitative only |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Safety manager |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

## 1. Purpose and scope

This document provides the system-level deductive (FTA) and inductive (FMEA) safety analyses that ISO 26262-4 §6 asks for to support the technical safety concept. It works on the architecture of [WP-C-01](../02-concept/WP-C-01-item-definition.md) §3 and [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) §2 as built at the baseline, so that it shows **where the inherited design has single points of failure today**. When [WP-S-03](../03-system/WP-S-03-technical-safety-concept-architecture.md) defines the target architecture, this analysis is repeated on it (OI-1).

- Qualitative only. Quantitative evaluation of random hardware failures belongs to [WP-H-04](../04-hardware/WP-H-04-hardware-metrics.md) and [WP-H-05](../04-hardware/WP-H-05-random-hardware-failures-pmhf.md).
- Functional insufficiencies of the ML stack (SOTIF) appear as basic events labelled **[SOTIF]** so the trees are complete. They are evaluated in [WP-C-06](../02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md), not here.
- Dependent failures (common cause) are marked **[CCF → DFI-nn]** and refer to [WP-A-03](WP-A-03-dependent-failure-analysis.md). Interference from QM elements is marked **[FFI → id]** and refers to [WP-A-02](WP-A-02-coexistence-freedom-from-interference.md).
- TSR references are to [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) (Draft v0.1); where no TSR covers a measure this is stated (OI-6).

Notation: `[OR]`, `[AND]` gates; `BE-` basic event; `UE-` undeveloped event (outside the item or analysed elsewhere); `(SPF)` marks an event that alone leads to the top event in the baseline design.

## 2. FTA — SG-01: uncontrollable lateral motion, or steering actuation while not engaged

Top event **TE-01**: LKA torque applied at the steering wheel that exceeds what the driver can control, or any LKA torque while the item is not engaged.

```
TE-01 Uncontrollable lateral motion / torque while not engaged                          [OR]
├── G1.1 Torque above the controllable bound reaches the wheel while engaged            [AND]
│   ├── G1.1.1 Command above controllable bound transmitted on bus 0 (0x2E4)           [OR]
│   │   ├── BE-1.01 Envelope torque limits set above the controllable bound
│   │   │          (raw 1500/15/25/450 not derived, GAP-04; identical in controller,
│   │   │          CCF → DFI-08)                                                        (SPF, systematic)
│   │   ├── G1.1.1.a SoC commands excessive torque AND envelope fails to clamp          [AND]
│   │   │   ├── G-SoC SoC command excessive or wrong                                    [OR]
│   │   │   │   ├── BE-1.02 controlsd/card software fault (QM)
│   │   │   │   ├── BE-1.03 Wrong desired curvature from model                     [SOTIF]
│   │   │   │   ├── BE-1.04 Debug/maneuver process replaces controller
│   │   │   │   │          (process_config.py:34-47, GAP-20)
│   │   │   │   └── BE-1.05 Wrong CarParams / fingerprint (CCF → DFI-09)
│   │   │   └── G-ENV Envelope does not clamp                                           [OR]
│   │   │       ├── BE-1.06 Envelope software defect in lateral checks (lateral.h:60-151)
│   │   │       ├── BE-1.07 MCU execution fault (RAM/register/CPU) corrupts limit or
│   │   │       │          check, not detected (no MPU, no ECC handling, faults
│   │   │       │          report-only; GAP-08)
│   │   │       ├── BE-1.08 Safety mode/param changed by SoC (0xdc, GAP-09)
│   │   │       │          [FFI → FFI-CM-06; CCF → DFI-13: same SoC fault can cause
│   │   │       │          G-SoC and BE-1.08]
│   │   │       └── BE-1.09 Envelope firmware replaced via boot pins / softloader
│   │   │                  (GAP-38, GAP-24) [FFI → FFI-CM-12; CCF → DFI-13]
│   │   └── BE-1.10 Frame corrupted after safety_tx_hook (TX queue RAM, FDCAN
│   │              message RAM, transceiver); no check after the hook
│   │              (can_common.h:161-166, fdcan.h:100-101 checks only a packet XOR
│   │              computed before queuing)                                             (SPF, random HW)
│   └── UE-1.11 EPS does not limit LKA torque to an overpowerable level (AOU-01R fails)
├── G1.2 Torque while not engaged                                                       [OR]
│   ├── G1.2.1 Authority falsely granted AND SoC commands torque                       [AND]
│   │   ├── G1.2.1.a False authority                                                    [OR]
│   │   │   ├── BE-1.12 Corrupted/replayed 0x1D2 creates false cruise rising edge with
│   │   │   │          valid 8-bit checksum (no counter, GAP-01)
│   │   │   ├── BE-1.13 Panda RX path delivers stale/stuck cruise frame to both
│   │   │   │          envelope and SoC (single RX path; CCF → DFI-10)
│   │   │   └── BE-1.14 MCU fault sets controls_allowed (BE-1.07 class)
│   │   └── BE-1.15 SoC commands non-zero torque (normally gated by its own engagement
│   │              state, which is fed by the same CAN data — CCF → DFI-10)
│   ├── G1.2.2 Authority not revoked after driver disengages                            [OR]
│   │   ├── BE-1.16 Brake 0x226 lost/stuck "not pressed" (no checksum, no counter,
│   │   │          timeout ≈2 s; GAP-01, GAP-06)
│   │   └── BE-1.17 0x1D2 stuck "cruise active" with valid checksum (GAP-01)
│   └── BE-1.18 Envelope bypass: ALLOUTPUT/debug mode in a DEBUG build
│              (panda/SConscript:12-20, GAP-25)                                         (SPF, config)
└── G1.3 Stale or frozen torque held beyond FTTI (HE-02.3)                              [AND]
    ├── G1.3.1 SoC stops updating but link stays alive                                 [OR]
    │   ├── BE-1.19 controlsd hang / stale modelV2 used up to ≈3.5 s (GAP-16)
    │   ├── BE-1.20 Diagnostics masked during big-model fallback (GAP-17; E-06 excluded
    │   │          from reference configuration)
    │   └── BE-1.21 SoC replays an old command buffer (no sequence counter, GAP-10)
    └── G1.3.2 Envelope does not remove torque within ≤ 0.5 s                          [OR]
        ├── BE-1.22 Heartbeat shows pandad liveness only; mismatch 3 s, loss 5 s
        │          (main.c:182-213; GAP-06, GAP-10)
        └── BE-1.23 Rate and RT limits accept a constant in-limit value (by design)
```

### 2.1 SG-01 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-01.1 | 1 + ext. | {BE-1.01, UE-1.11} | A wrong envelope limit is itself the failure; only the EPS (unverified) stands behind it. **Systematic single point** |
| MCS-01.2 | 1 + ext. | {BE-1.10, UE-1.11} | Random corruption after the TX hook. No second check on the item side. **Random single point** |
| MCS-01.3 | 1 (effective) | {SoC fault that both commands torque and changes mode/param or reflashes the MCU} = {BE-1.02/1.04 + BE-1.08/1.09 from one cause} | Dual-point in form, single-point in cause (DFI-13) |
| MCS-01.4 | 1 (effective) | {BE-1.13} | One stuck RX path feeds envelope and SoC; both "agree" the system is engaged (DFI-10) |
| MCS-01.5 | 1 | {BE-1.18} | Configuration single point: a debug build has no envelope. Controlled only by the release process ([WP-P-10](../07-supporting/WP-P-10-release-management.md)) |
| MCS-01.6 | 2 | {BE-1.02 or BE-1.03, BE-1.06 or BE-1.07} | True dual-point: the intended envelope pattern. Requires BE-1.07 to be detected (latent-fault coverage, IWDG, ECC) to stay dual |
| MCS-01.7 | 2 | {BE-1.12, BE-1.15} | Needs counters on `0x1D2` or a plausibility check (TSR-403…TSR-405) to remove |
| MCS-01.8 | 2 | {BE-1.19 or BE-1.21, BE-1.22} | Removed only when the command-freshness timeout fits the FTTI (TSR-407…TSR-409, TSR-411) |

## 3. FTA — SG-03: unintended acceleration

Top event **TE-03**: vehicle acceleration that the driver did not intend (positive acceleration request executed beyond the intended value, while not engaged, or after the driver brakes).

```
TE-03 Unintended acceleration                                                           [OR]
├── G3.1 Positive acceleration above controllable bound executed while engaged          [AND]
│   ├── G3.1.1 0x343 ACC_CONTROL accel above controllable bound on bus 0               [OR]
│   │   ├── BE-3.01 Envelope accel upper bound (+2.0 m/s², toyota.h:208) above the
│   │   │          controllable value; RAISED_ACCEL_LIMIT not validated for Corolla
│   │   │          (toyota/interface.py:117-118; GAP-04; CCF → DFI-08)             (SPF, systematic)
│   │   ├── G3.1.1.a SoC excessive accel AND envelope fails to clamp                  [AND]
│   │   │   ├── BE-3.02 Planner/controller fault, wrong lead, e2e accel [SOTIF]/QM
│   │   │   └── G-ENV (as SG-01: BE-1.06…1.09)
│   │   ├── BE-3.03 No jerk limit in envelope: step to +2.0 m/s² allowed (GAP-04,
│   │   │          FSR-03.03 not implemented)
│   │   └── BE-3.04 Frame corrupted after TX hook (as BE-1.10)                          (SPF, random HW)
│   └── UE-3.05 PCM executes request without its own bound (AOU-05R fails)
├── G3.2 In-bound but unintended positive acceleration (e.g. toward a stationary lead)  [AND]
│   ├── BE-3.06 SoC requests positive accel in a closing situation [SOTIF]/QM
│   ├── BE-3.07 Envelope passes any in-bound value while authority is granted (by design)
│   └── UE-3.08 Driver does not brake in time (controllability; AOU-06R)
├── G3.3 Acceleration while not engaged or after driver brake                           [OR]
│   ├── G3.3.1 Authority falsely granted / not revoked                                 [OR]
│   │   ├── BE-1.12, BE-1.13, BE-1.14 (as SG-01)
│   │   └── BE-3.09 Brake 0x226 not detected (no checksum/counter, GAP-01) AND PCM does
│   │              not cancel ACC on brake (AOU-03R)                                   [AND]
│   └── BE-3.10 Inactive value check bypassed by mode/param change (e.g. param that
│              selects another brake signal or stock-longitudinal branch, toyota.h:216-248)
│              [FFI → FFI-CM-06]
├── G3.4 Gas override misinterpreted                                                    [AND]
│   ├── BE-3.11 Gas-pressed signal (PCM_CRUISE.GAS_RELEASED) stuck "pressed": envelope
│   │          then allows only inactive accel (safe direction) — or stuck "released"
│   │          while the driver presses: envelope allows accel (longitudinal.h:3-5)
│   └── UE-3.12 PCM adds item accel on top of driver pedal (to verify, AOU-05R)
└── G3.5 Stale positive acceleration held beyond FTTI                                   [AND]
    ├── BE-1.19 / BE-1.21 (stale SoC command)
    └── BE-1.22 (slow envelope detection)
```

### 3.1 SG-03 minimal cut sets (qualitative)

| Cut set | Order | Events | Comment |
|---|---|---|---|
| MCS-03.1 | 1 + ext. | {BE-3.01, UE-3.05} | Systematic single point; bound selection |
| MCS-03.2 | 1 + ext. | {BE-3.04, UE-3.05} | Random single point after TX hook |
| MCS-03.3 | 1 + ext. | {BE-3.03, UE-3.05} | Step acceleration within bound; jerk not limited in the envelope |
| MCS-03.4 | 2 + driver | {BE-3.06, BE-3.07, UE-3.08} | By design; managed by SOTIF and controllability of the bound |
| MCS-03.5 | 1 (effective) | {SoC fault → command + mode/param change} | DFI-13 |
| MCS-03.6 | 2 | {BE-3.09} (= {`0x226` undetected, PCM no cancel}) | Item side has no independent brake signal |
| MCS-03.7 | 2 | {BE-1.19/1.21, BE-1.22} | Freshness timing |

## 4. Single points of failure and cut-set observations

| ID | Observation | SG | Type | Required measure | TSR / GAP |
|---|---|---|---|---|---|
| SPF-01 | **Limit values are a systematic single point.** Nothing in the item checks that the envelope limits are themselves controllable; the controller uses the same numbers (DFI-08) | SG-01, SG-03, SG-04 | Systematic | Physically derived limits with recorded rationale; controllability test; controller margin | TSR-102, TSR-103, TSR-201, TSR-202, TSR-204, TSR-205, TSR-605; GAP-04 |
| SPF-02 | **No integrity check between the TX hook and the bus.** A random fault in TX queue RAM, FDCAN message RAM or the transceiver changes an already-approved frame | SG-01, SG-03, SG-04 | Random HW | RAM/FDCAN-RAM ECC enabled with reaction; option: TX read-back of own frames from the bus (FDCAN RX of own TX) compared with the approved frame | TSR-503 (RAM ECC) only; **no TSR for post-hook TX integrity** (OI-6); FMEDA WP-H-03 |
| SPF-03 | **SoC can disable or replace its own monitor** (mode/param, boot pins, softloader). Any SoC fault (or compromise) is effectively a single point | All | Common cause / FFI | Safety-mode lock, command rejection in car modes, RDP/WRP, signature | TSR-511…TSR-514; GAP-09, GAP-24, GAP-38 |
| SPF-04 | **Single RX path for both monitor and controller.** The SoC receives vehicle CAN through the panda; a stuck RX path or stuck vehicle frame misleads both | SG-01, SG-03, SG-05 | Common cause | E2E/plausibility on gating signals in the envelope | TSR-401…TSR-406; GAP-01 |
| SPF-05 | **Debug build has no envelope** (ALLOUTPUT, debug key) | All | Configuration | Release-only firmware, build-type check at start-up reported to SoC and enforced | TSR-514, TSR-802; GAP-25 |
| SPF-06 | **MCU hang leaves the relay energised** (GAP-43) with no hardware watchdog. Torque stops (EPS timeout, AOU-01R), but the stock PCS path stays cut if forwarding stops | SG-07 (and SG-02 without warning) | Random HW | IWDG (TSR-501); fault reaction (TSR-502); relay to stock path on fault/reset (TSR-706) | GAP-07, GAP-43 |
| SPF-07 | **Relay welded in intercept position** is not detected (no readback) | SG-07 | Random HW | Relay readback (TSR-506) | GAP-12 |
| SPF-08 | **QM command `0xe7` (power save) in car mode** stops camera-side forwarding with the relay energised (by code reading, WP-A-02 FFI-CM-08) | SG-07 | FFI | Reject in car modes | TSR-513; WP-S-02 NF-05 |
| Obs-01 | MCS-01.6 is the only truly dual-point cut set that the envelope pattern intends. It stays dual only if MCU faults (BE-1.07) are detected; today there is no IWDG, MPU or ECC reaction, so latent MCU faults can accumulate | SG-01 | Latent | Latent-fault diagnostics at start-up and run time | TSR-501, TSR-503, TSR-507 |
| Obs-02 | Every SG-01 and SG-03 path ends in an EPS or PCM AND-input (UE-1.11, UE-3.05). These are unverified AoUs. The tree must not be read as "dual" until AOU-01R/AOU-05R are verified | SG-01, SG-03 | AoU | Vehicle characterisation (WP-S-09) | GAP-05 |

## 5. System FMEA

Severity of the vehicle effect is expressed by the affected SG. Detection = mechanism that detects the failure mode in the item today. Columns: **Mech.** = safety mechanism that reaches the safe state; **Gap** = what is missing.

| ID | Element | Failure mode | Effect (local → vehicle) | SG | Detection (today) | Mechanism (today) | Gap / required |
|---|---|---|---|---|---|---|---|
| SFMEA-01 | E-01 controlsd | Excessive torque command | Torque above intent → lateral deviation | SG-01 | Envelope per-frame limits (`lateral.h:60-151`) | Frame dropped; `controls_allowed` not cleared by TX violation alone | FSR-01.12: revoke on TX violation (TSR-108, TSR-109) |
| SFMEA-02 | E-01 controlsd | Output frozen (hang) | Last command repeated by card/pandad or no command | SG-01, SG-02 | selfdrived `processNotRunning`/`commIssue` (QM); panda heartbeat 3–5 s | Soft disable keeps actuating 3 s (GAP-16); SILENT after 5 s | Freshness check ≤ 0.3 s in envelope (TSR-408, TSR-409; host TSR-602); GAP-06, GAP-10 |
| SFMEA-03 | E-01 controlsd | Non-finite output | Clamped to 0 silently (`controlsd.py:140-147`) → loss of control without warning | SG-02, SG-06 | Logged only | None | FSR-06.04 (TSR-604); GAP-19 |
| SFMEA-04 | E-01 card | Sends `0x343` positive accel while engaged and lead close | Unintended acceleration | SG-03 | None if in bound | Envelope bound +2.0 m/s² | Jerk limit (FSR-03.03, TSR-204); bound rationale |
| SFMEA-05 | E-01 card / pandad | Sends PCS messages `0x344`/`0x411` (or DSU-only IDs, WP-S-02 NF-07) | Stock PCS altered | SG-07 | None | Whitelist allows them | FSR-07.02 (TSR-705; GAP-42) |
| SFMEA-06 | E-01 pandad | Sets wrong safety mode/param | Envelope misconfigured | All | Host cross-check after 10 s (QM, same source) | Mode change clears authority | Safety-mode lock (TSR-512); GAP-09 |
| SFMEA-07 | E-01 pandad | Heartbeat continues while controls loop is dead | Envelope keeps authority | SG-01, SG-02 | 3 s mismatch only if `engaged` flag drops | — | Heartbeat bound to control loop (TSR-409); GAP-10 |
| SFMEA-08 | E-01 selfdrived | Engaged state differs from PCM (`cruiseMismatch`) | Mode confusion | SG-05, SG-02 | Event raised after 6 s, no reaction (`events.py:458-460`) | None | FSR-05.06 (TSR-308); GAP-19 |
| SFMEA-09 | E-01 HMI (ui/soundd) | No take-over warning (crash) | Unannounced loss | SG-02, SG-06 | panda siren after heartbeat loss | Siren 3 s after 5 s | FSR-02.05 timing (TSR-516; SoC TSR-606); DFI-14 |
| SFMEA-10 | E-01 DM chain | DM inactive / demo mode | Inattention undetected | (SG-02/06 controllability) | `dmonitoringd` validity → `commIssue` | Soft disable | FSR-02.08 (QM, SOTIF); GAP-20, GAP-21 |
| SFMEA-11 | E-02 driving model | Wrong curvature / accel | Unintended manoeuvre within bounds | SG-01, SG-03 [SOTIF] | Excessive-actuation latch (2× ISO limits, `selfdrive/selfdrived/helpers.py`) | Soft disable + no-entry | SOTIF (WP-C-06); bounded by envelope |
| SFMEA-12 | E-03 safety hooks | Software defect in limit check | Excess passes | SG-01, SG-03, SG-04 | Unit/mutation tests (design-time) | — | ASIL-level verification (MC/DC, target tests) GAP-13 |
| SFMEA-13 | E-03 RX checks | Stuck/replayed `0x1D2`/`0x226` frames accepted | False authority / no revocation | SG-01, SG-03, SG-05 | Checksum (`0x1D2` only), timeout ≈2 s | `controls_allowed` cleared on checksum fail or timeout | E2E/plausibility, ≤ 0.3 s (TSR-401…TSR-406); GAP-01, GAP-06 |
| SFMEA-14 | E-03 driver-torque handling | Driver steering override not detected in envelope | Torque opposes driver | SG-05 | Host only (`carcontroller.py:33, 83`) | EPS (assumed) | FSR-05.03 (TSR-304); GAP-02 |
| SFMEA-15 | E-03 EPS status | EPS LKA fault not seen by envelope | Unannounced loss | SG-02 | Host only (`carstate.py:122-127`) | Host soft/immediate disable | FSR-02.01 (TSR-110); GAP-03 |
| SFMEA-16 | E-03 tick / heartbeat | Tick ISR starved or stopped | No timeout detection, no siren | SG-01, SG-02 | Interrupt-rate fault (report-only) | None | IWDG (TSR-501); fault reaction (TSR-502); GAP-07, GAP-08 |
| SFMEA-17 | E-03 TX path after hook | Frame bit flip in queue/message RAM | Approved frame altered | SG-01, SG-03, SG-04 | Packet XOR computed before queuing, checked at FDCAN load (`fdcan.h:100-101`) — does not cover FDCAN message RAM or transceiver | — | SPF-02 measures (TSR-503/5xx) |
| SFMEA-18 | E-03 SPI link | Corrupted command passes 8-bit XOR | Wrong CAN frame or wrong control command | All | XOR, NACK | TX hook limits (frames); none for control commands | CRC + counter (TSR-410, TSR-413); GAP-10 |
| SFMEA-19 | E-03 SPI link | Length field above buffer size | DMA overrun into SRAM1/2 | All (potential) | None | Memory-bank separation (unconfirmed) | Length bound (TSR-412; WP-S-02 NF-04); WP-A-02 FFI-SP-02 |
| SFMEA-20 | E-03 forwarding | Camera-side forwarding stops (power-save command, bus-2 fault) with relay energised | Stock PCS suppressed | SG-07 | None in envelope | — | Reject `0xe7` in car modes; forwarding supervision (TSR-513, TSR-707); WP-A-02 FFI-CM-08 |
| SFMEA-21 | E-03 relay malfunction detection | Detection 1–2 s, one direction only | Camera commands reach car / PCS path cut undetected | SG-01, SG-07 | Traffic-based (`safety.h:215-220, 372-380`) | Block all TX | Readback (TSR-506); GAP-12 |
| SFMEA-22 | E-04 MCU core | Hang (no IWDG) | Relay stays energised; TX stops | SG-07, SG-02 | None | EPS timeout (AOU-01R) | TSR-501, TSR-502, TSR-706; GAP-07, GAP-43 |
| SFMEA-23 | E-04 MCU RAM | Bit flip in `controls_allowed`/limits | Authority or limit wrong | SG-01, SG-03 | None (no ECC handling) | — | TSR-503, TSR-507; GAP-08 |
| SFMEA-24 | E-04 MCU clock | HSE failure | Clock loss | All | CSS → NMI → reset (`clock.h:118-119`, `early_init.h:73-76`) | Reset (relay expected released) | Confirm reset-state relay (TSR-706); drift detection (TSR-504) |
| SFMEA-25 | E-04 power | Supply dip / brown-out | Erratic MCU and SoC | All | Voltage reported only | NMI/HardFault reset | BOR/PVD (TSR-505); DFI-01 |
| SFMEA-26 | E-04 CAN transceiver (bus 0) | Dominant-stuck / babbling | Vehicle bus disturbed; EPS/PCM lose messages | SG-02, SG-06, SG-07 | Error counters, bus-off reset (`fdcan.h:76-84`) | None in firmware | TSR-508 |
| SFMEA-27 | E-04 SoC GPIO | BOOT0/RST asserted while driving | MCU in ROM bootloader; relay released (expected) | SG-02 (loss), cybersecurity | pandad recovery logs | Relay release (reset state) | TSR-706, TSR-511; GAP-38 |
| SFMEA-28 | E-05 relay | Welded in intercept | Stock path cut while item off | SG-07 | None | — | TSR-506; GAP-12 |
| SFMEA-29 | E-05 relay | Open coil / released while engaged | Camera LKA/ACC reach car together with item commands | SG-01 (conflicting commands) | Relay malfunction latch 1–2 s | Block all TX | TSR-506 timing |
| SFMEA-30 | E-05 connector | Intermittent contact | CAN errors, ignition flicker, relay chatter | All | Harness status (suspended while relay driven, `harness.h:59`) | Indirect (CAN timeouts) | TSR-701, TSR-703 |
| SFMEA-31 | EXT-EPS | Misreports motor torque | Measured-tracking check misled | SG-01 | None | Magnitude/rate limits still apply | DFI-11; TSR-101, TSR-103, TSR-110 |
| SFMEA-32 | EXT-PCM | Ignores cancel / inactive value | Accel continues | SG-03, SG-05 | `accFaulted` (host) | — | AOU-05R vehicle test (WP-S-09) |

## 6. Feedback to other work products

| To | Item |
|---|---|
| [WP-S-02](../03-system/WP-S-02-technical-safety-requirements.md) | SPF-01, -03…-08 map to existing TSRs (§4). **SPF-02 (post-hook TX integrity) has no TSR**: TSR-503 covers RAM ECC but not FDCAN message RAM or the transceiver, and no TSR requires read-back of own transmitted frames (OI-6) |
| [WP-C-04](../02-concept/WP-C-04-functional-safety-concept.md) | SPF-02 and SPF-08 are not covered by an FSR; FSR-01.09 covers MCU execution faults but not post-hook frame corruption explicitly |
| [WP-H-03](../04-hardware/WP-H-03-hardware-safety-analysis-fmeda.md) | SFMEA-17, -22…-26 as FMEDA inputs |
| [WP-W-04](../05-software/WP-W-04-software-safety-analysis.md) | SFMEA-12, -13, -16, -18, -19 as software safety analysis inputs |
| [WP-V-05](../06-validation/WP-V-05-fault-injection.md) | Every BE marked SPF and every SFMEA row with a mechanism gets a fault-injection case |

## 7. Open items

| ID | Item | Owner | Needed by |
|---|---|---|---|
| OI-1 | Repeat FTA and FMEA on the target architecture of WP-S-03 and show that SPF-01…SPF-08 are removed or argued | Safety engineer | G2 |
| OI-2 | Re-check TSR references when WP-S-02 leaves Draft | Safety engineer | G2 |
| OI-3 | Develop FTAs for SG-02, SG-04, SG-05, SG-06, SG-07 (SG-07 relay/forwarding tree first, because of SPF-06…SPF-08) | Safety engineer | G2 |
| OI-4 | Confirm whether STM32H7 FDCAN message RAM has ECC and whether it is enabled (SPF-02) | HW lead | G2 |
| OI-5 | Confirm by HIL test that an MCU hang leaves the relay energised (SPF-06) and that `0xe7` stops forwarding (SPF-08) | Test lead | G4 |
| OI-6 | Report to the WP-S-02 author: no TSR covers frame integrity between `safety_tx_hook` and the bus (SPF-02) | Safety engineer | G2 |
