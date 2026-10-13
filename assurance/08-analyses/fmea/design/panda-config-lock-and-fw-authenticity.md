# Panda Configuration Lock and Firmware Authenticity — Design

| | |
|---|---|
| **Doc ID** | LD-DES-001 |
| **Revision** | 0.1 (draft, not implemented) |
| **Date** | 2026-10-10 |
| **Author** | Claude (AI-assisted draft); requires review by Jherrod Thomas |
| **Implements** | DFA measures DM-07 (configuration lock), DM-08 (firmware authenticity), DM-12 (diagnostic mode offroad only); DFA open item DOI-002 |
| **Affects** | FSC FSR-002, 005, 007, 010, 017, 019, 022, 024, 027, 029, 032, 035 (every panda-side channel of a decomposition) |
| **Code basis** | BL-001: panda `92eb565`, opendbc `229dc70`, LionDriver `8b8c6ae` |

## 1. Why

The DFA (LD-DFA-001) accepts none of the 11 panda/SoC decompositions. Every panda channel depends on the SoC in two ways the panda cannot see:

- **DFI-07:** the SoC chooses the configuration the panda enforces.
- **DFI-09:** the SoC chooses the firmware the panda runs.

This design makes both decisions the panda's own, so a fault on the SoC cannot widen what the panda lets through.

## 2. What the BL-001 code does today

All references are to the pinned commits.

| # | Finding | Evidence |
|---|---|---|
| F1 | The host can set any safety mode and parameter at any time. There is no restriction while driving and no allow-list. | `panda/board/main_comms.h:223` (0xdc) → `panda/board/main.c:31` `set_safety_mode` |
| F2 | Alternative experience can only be changed outside a car safety mode, but pandad sets it immediately *before* switching to the car mode, so the SoC still chooses it. | `panda/board/main_comms.h:242`; `openpilot/selfdrive/pandad/panda_safety.cc:68-69` |
| F3 | The Toyota safety parameter is chosen by the SoC and selects: the brake signal the panda trusts (`ALT_BRAKE`), whether openpilot longitudinal is allowed (`STOCK_LONGITUDINAL`), angle versus torque steering (`LTA`), SecOC, and the EPS torque scaling factor (low 8 bits). | `opendbc/safety/modes/toyota.h:369-383` |
| F4 | Firmware built without `RELEASE` (the LionDriver default) defines `ALLOW_DEBUG`. That adds `SAFETY_ALLOUTPUT` and seven debug-only car modes to the hook registry. One host command (mode 17) makes the panda forward every message unchecked, with the relay intercepting. | `panda/SConscript:12-20`; `opendbc/safety/safety.h:413-421` |
| F5 | ELM327 (diagnostic) mode accepts any ISO 15765 diagnostic frame (11-bit 0x6xx/0x7xx, 29-bit UDS) with no ignition or motion condition. pandad selects it at start-up and on OBD-multiplexing changes. | `opendbc/safety/modes/elm327.h:6-33`; `panda_safety.cc:23-36` |
| F6 | The bootstub verifies the app with RSA and a minimum version (`MIN_VERSION 2`). With `ALLOW_DEBUG` it also accepts the debug key, whose **private** key is committed in the repository. | `panda/board/bootstub.c:2,58,63-71`; `panda/board/crypto/certs/debug` |
| F7 | When flashed firmware does not boot, pandad installs the *development* bootloader. A source-built (debug-signed) app on a release bootstub triggers this, so a LionDriver device ends up on a bootstub that trusts the public debug key. | `openpilot/selfdrive/pandad/pandad.py:20-48` |
| F8 | No STM32 option-byte protection (RDP/WRP) is set. The SoC drives the panda's reset and BOOT0 lines, so the STM32 ROM DFU bootloader can erase and rewrite the bootstub. | `openpilot/common/hardware/comma/hardware.py:410`; `panda/python/dfu.py:116-130` |
| F9 | The app accepts "enter softloader" from the host in release builds. The image is still signature-checked at the next boot. | `panda/board/main_comms.h:165-183` |
| F10 | *Outside DM-07/08, found during this review:* heartbeat loss is checked at 1 Hz with a 5 s timeout when ignition is on, and an engaged mismatch drops control after 3 consecutive 1 Hz ticks (~3 s). The SG-001 preliminary FTTI is 900 ms. | `panda/board/main.c:102,184,191-212` |

## 3. Design requirements

Requirement IDs are design-level (DR-xx). They become TSRs when the TSC is written.

### 3.1 Configuration lock (DM-07, DM-12)

**Vehicle lock record (VLR).** The panda holds one provisioned record naming the only car configuration it will enforce.

| Field | Content |
|---|---|
| `magic`, `format_version` | Identifies a VLR and its layout |
| `safety_mode` | e.g. `SAFETY_TOYOTA` (2) |
| `safety_param` | Exact 16-bit parameter, including flags and EPS factor |
| `alternative_experience` | Always 0 in LionDriver release builds |
| `baseline_id` | e.g. BL-001; ties the record to an assured configuration |
| `vehicle_id_hash` | Hash of the VIN read at provisioning; reported, not enforced (see D3) |
| `crc32` | Over all fields |

The VLR is stored in two copies in a dedicated flash sector, outside the app and bootstub sectors. A record is valid only if both copies agree and pass CRC.

| ID | Requirement |
|---|---|
| DR-01 | With a valid VLR, the panda shall accept a safety-mode request only if it is SILENT, NOOUTPUT, or exactly (`VLR.safety_mode`, `VLR.safety_param`). Any other request is rejected: the panda moves to NOOUTPUT and sets a new health fault `CONFIG_REJECTED`. |
| DR-02 | Without a valid VLR (unprovisioned or corrupt), the panda shall accept only SILENT, NOOUTPUT and ELM327 under DR-05. The item cannot actuate until it is provisioned, so the lock fails closed. |
| DR-03 | In LionDriver release builds, alternative experience shall be forced to 0 and the 0xdf command ignored. |
| DR-04 | A VLR shall be written or erased only while ignition is off (`harness_check_ignition() == false` and no CAN ignition), no car safety mode is active, and the request is repeated with a confirmation token within 10 s. Each write is verified by reading it back. |
| DR-05 | ELM327 mode shall be accepted only while ignition is off, or while the vehicle is stationary and no car safety mode was active in this ignition cycle. A request outside these conditions is rejected as in DR-01. |
| DR-06 | LionDriver release builds shall not define `ALLOW_DEBUG`. This removes `SAFETY_ALLOUTPUT` and the debug-only modes from the registry, independently of the VLR. |
| DR-07 | The health packet shall report the VLR state (valid / absent / corrupt), `baseline_id`, the VLR CRC and the `CONFIG_REJECTED` flag. The SoC compares them with CarParams (extends `controlsMismatch`). This is a supplementary QM check; the panda-side checks above don't depend on it. |

**Why this removes DFI-07.** After provisioning, nothing the SoC sends while driving can change the mode, parameter or alternative experience that the panda enforces. The SoC can only *downgrade* the panda to SILENT/NOOUTPUT, which is the safe direction. Two residual risks remain:

- A wrong record written at installation, which belongs in the PFMEA install step.
- A SoC fault during the offroad provisioning window, which DR-04 bounds with the ignition-off condition, the confirmation token and the read-back.

### 3.2 Firmware authenticity (DM-08)

| ID | Requirement |
|---|---|
| DR-10 | LionDriver release firmware shall be built with `RELEASE=1` and signed with a LionDriver release key. The private key is held offline, never in the repository. Its public key is compiled into the LionDriver bootstub. |
| DR-11 | The LionDriver bootstub shall accept only images signed with the LionDriver release key. The debug key is accepted only by development bootstubs, and a device carrying one is outside the assured configuration (see DR-16). |
| DR-12 | The bootstub shall reject images below the LionDriver minimum qualified version (raise `MIN_VERSION`; the existing check at `bootstub.c:58` is kept). |
| DR-13 | Protect the bootstub sector: set write protection on flash sector 0 and RDP level 1 during provisioning. Any route that removes the protection (RDP regression) mass-erases the flash, leaving a blank panda that transmits nothing and leaves the relay to stock (DFI-03 outcome). RDP level 2 is rejected because it is irreversible and prevents recovery from a bootstub defect. **To verify:** system bootloader behavior under RDP1+WRP on STM32H725 (RM0468, AN2606) before relying on it (D2). |
| DR-14 | pandad shall flash panda firmware or enter the softloader only while ignition is off. The panda enforces the same condition for 0xd1 (both modes). |
| DR-15 | In LionDriver release builds, pandad shall not install a development bootstub. The fallback at `pandad.py:34-40` becomes: report the fault and stay in dashcam mode. |
| DR-16 | The panda shall report its bootstub build type and signing key ID in the health packet. The SoC shall refuse to engage (NO_ENTRY, permanent alert) when either is not the LionDriver release one. |

**Why this removes DFI-09.**
- A corrupted image fails the signature check and doesn't boot, so the result is fail-silent.
- A wrong but validly signed older image is blocked by DR-12.
- An image signed with the public debug key is refused by a LionDriver release bootstub (DR-11), and a device with a development bootstub is detected (DR-16).
- The ROM DFU path can no longer leave a modified bootstub running; it can only produce a blank panda (DR-13).

What remains is a *correctly signed but defective* release. That is DFI-18, owned by the release process: the signing step becomes the enforcement point of the separate panda release gate (DM-09). Deliberate attacks, such as key theft or physical access, go to the TARA.

### 3.3 Heartbeat timing (F10, FSC FOI-008)

Out of scope for DM-07/08, but recorded here because the code was read for this design:

| ID | Requirement |
|---|---|
| DR-20 | While controls are allowed, the panda shall check heartbeat age and the engaged/controls-allowed mismatch at the 8 Hz tick or faster, and withdraw controls within a timeout derived from the SG-001 FTTI (OI-004). The current 5 s / ~3 s values exceed the 900 ms preliminary FTTI. |

## 4. Effect on the DFA (once implemented and verified)

| DFI | Now | After this design | Remaining dependency |
|---|---|---|---|
| DFI-07 configuration | insufficient | expected sufficient | Install-time provisioning (PFMEA), DR-01…07 verified |
| DFI-08 diagnostic mode | open → **insufficient** (F5 confirms no restriction) | expected sufficient | DR-05 verified |
| DFI-09 firmware | insufficient | expected sufficient | DR-13 bootloader behavior verified (D2) |
| DFI-18 release | insufficient | still insufficient | Panda release gate (DM-09), with DR-10 signing as its enforcement point |

The DFA itself still marks DM-07, DM-08 and DM-12 as *required*. They move to *existing* only when implemented and tested.

## 5. Change scope

LionDriver would maintain forks of `panda` and `opendbc` (both are submodules pointing at commaai today).

| Component | Change |
|---|---|
| `panda/board/main_comms.h` | Gate 0xdc (DR-01/02/05), ignore 0xdf in release (DR-03), gate 0xd1 (DR-14), new provisioning commands (DR-04) |
| `panda/board/main.c` | Mode allow-list in `set_safety_mode`; `CONFIG_REJECTED` fault; heartbeat timing (DR-20) |
| `panda/board/vehicle_lock.h` (new) | VLR storage, dual copy, CRC, read-back |
| `panda/board/bootstub.c`, `panda/SConscript` | LionDriver release key, `MIN_VERSION`, option-byte setup (DR-10…13) |
| `panda/board/health.h` | VLR state, key ID, build type (DR-07, DR-16) |
| `openpilot/selfdrive/pandad/pandad.py` | Offroad-only flashing, no development-bootstub fallback (DR-14/15) |
| `openpilot/selfdrive/pandad/panda_safety.cc` | Stop setting alternative experience; provisioning flow; read VLR state |
| `openpilot/selfdrive/selfdrived/selfdrived.py` | NO_ENTRY on VLR mismatch or non-release bootstub (DR-07, DR-16) |

**Compatibility.** A device with the LionDriver bootstub no longer runs comma-signed firmware. It becomes dedicated to LionDriver, and recovery to stock needs a documented procedure.

## 6. Verification

| Requirement | Method |
|---|---|
| DR-01…03, DR-05 | Unit tests in the panda safety test harness. Every mode/param combination is rejected except the VLR's; 0xdf is ignored; ELM327 is rejected while moving or after a car mode in the same ignition cycle. |
| DR-04 | Unit tests (ignition-on rejection, missing confirmation, CRC failure, single-copy corruption) plus HIL power-cut during write. |
| DR-06 | Build test: the release image has no `alloutput_hooks` symbol. |
| DR-10…12 | HIL: the release bootstub rejects debug-signed, unsigned, corrupted and down-versioned images. |
| DR-13 | HIL on a sacrificial unit: ROM DFU write attempts with WRP+RDP1 must end with an erased, silent panda, never a running modified bootstub. |
| DR-14…16 | Integration tests on pandad/selfdrived (flash refused while ignition is on; NO_ENTRY on development bootstub). |
| DR-20 | HIL fault injection: stop the heartbeat while engaged and measure time to no output against the FTTI. |

## 7. Decisions needed

| # | Decision | Recommendation |
|---|---|---|
| D1 | Who holds the LionDriver release signing key, and where | Offline key held by the project maintainer; signing only after the panda release gate passes |
| D2 | Protect the bootstub with WRP + RDP1 (DR-13), or leave ROM DFU open and accept the residual | Adopt DR-13 after the bootloader behavior is verified on a sacrificial unit |
| D3 | Whether the VLR enforces the VIN (panda reads the VIN at start-up and refuses on mismatch) | Report only in rev 0.1; enforcing needs a UDS VIN read by the panda before controls are allowed |
| D4 | Accept that devices become LionDriver-only | Yes, for assured configurations; development units keep the debug bootstub and are marked outside scope |
