# LAYOUT-CHECK-2026-10-13 — CAN bit positions: HSI specification against the DBC and the C

| Field | Value |
|---|---|
| Status | Draft — AI-assisted (Claude), not reviewed. Not a verification result (tool not classified; [TE-01](../../../07-supporting/tool-evaluations/TE-01-modelling-tools.md) TL-24) |
| Purpose | Close part of the common-cause gap of the back-to-back run: there, the model and the C both get frames packed from the same DBC, so a DBC error that the C shares would go unnoticed ([B2B-TOY-AUTH-2026-10-13](B2B-TOY-AUTH-2026-10-13.md) §5) |
| Code under test | opendbc `7993399` (libsafety, both build variants); DBC `toyota_nodsu_pt_generated` |
| Tool | [`layout_check.py`](../layout_check.py) SHA-256 `bd045f1a…77c6`; same environment as the back-to-back run (CPython 3.12.13, gcc 13.3.0) |
| Raw output | [`layout-check-2026-10-13-reference.json`](layout-check-2026-10-13-reference.json), [`layout-check-2026-10-13-upstream.json`](layout-check-2026-10-13-upstream.json) |
| CI | Runs in the [`b2b` workflow](../../../../.github/workflows/b2b.yaml) after the back-to-back run, in both builds |

## 1. Method

The second source is the bit positions that [WP-S-05](../../../03-system/WP-S-05-hsi-specification.md) §11.1 states. The check has three parts:

- **L0, specification copy.** The positions in the check must still match the WP-S-05 rows, which are read at run time.
- **L1, DBC against the specification.** Packing the signal with the DBC must change exactly the stated bit.
- **L2, C against the specification.** Frames built by hand must make the C react as the SM record says, and the neighbouring bits must not. These frames have the stated bit set (or every other data bit set) and a checksum computed in the check. Messages not under test are packed from the DBC.

The check covers three signals:

| Signal | Stated in WP-S-05 §11.1 | Result |
|---|---|---|
| CRUISE_ACTIVE | `0x1D2` bit 5 (S-09) | L0, L1, L2 pass in both builds |
| GAS_RELEASED | `0x1D2` bit 4 (S-10) | L0, L1, L2 pass in both builds |
| BRAKE_PRESSED | `0x226` bit 37 (S-11) | L0, L1, L2 pass in both builds |

L2 cases, all passing in both builds:
- A rising edge on bit 5 engages.
- Every other `0x1D2` data bit set, with bit 5 clear, does not engage.
- When engaged, clearing bit 5 with all other bits set clears authority.
- Bit 4 clear means gas pressed and bit 4 set means released. The other bits do not release it.
- When engaged, every `0x226` bit except 37 keeps authority, and bit 37 alone clears it.
- The hand checksum is the one the C accepts: a copy with one bit flipped clears authority.

**Check of the check.** Five errors were planted in the check and each made it fail (exit 1). This was run once and is not part of CI. The failing parts:

| Planted error | Parts that failed |
|---|---|
| CRUISE_ACTIVE at bit 6 | L1 and five L2 cases |
| BRAKE_PRESSED at bit 36 | L1 and the brake case |
| GAS_RELEASED at bit 3 | L1 and the gas case |
| Most-significant-bit-first numbering | six L2 cases |
| Checksum without the length term | five L2 cases |

Editing WP-S-05 S-11 to bit 38 made L0 fail. The document was restored afterwards and is unchanged.

## 2. Assumptions and limits

| ID | Item |
|---|---|
| LA-01 | WP-S-05 does not define its bit numbering. The check reads "bit n" as byte n // 8, bit n mod 8, counted from the least significant bit. Under this reading, all three stated positions agree with both the DBC and the C. Under most-significant-bit-first numbering, the C rejects them (see the planted errors above) |
| LA-02 | The Toyota checksum used for hand-built frames comes from WP-W-05 UN-17, which describes the code. So L2 does not check the checksum algorithm independently; it only shows that the check and the C use the same one |
| LA-03 | "Independent" here means independent of the DBC, not of the vehicle. Whether the reference Corolla really puts these signals at these bits needs a bus capture (HIL bench B3) |

## 3. Findings (open)

### LC-01 — WP-S-05 §11.1 does not state the bit positions of several signals the envelope uses

| | |
|---|---|
| Signals | MAIN_ON (`0x1D3`, S-13: no bit given). WHEEL_SPEED_FR/FL/RR/RL and their fault bits (`0xAA`, S-06: width, scale and offset only; the fault bits are not mentioned). LKA_STATE (`0x262`, S-12: width only). STEER_ANGLE_INITIALIZING, the quality flag of `0x260` (not in §11.1; WP-W-05 UN-17 gives bit 3 from the code) |
| Effect | For these signals the DBC is the only source of the layout, so the back-to-back run cannot detect a DBC error that the C shares. B2B-02 (wheel-speed sign) also depends on the `0xAA` layout |
| Proposal | Add bit positions, endianness and bit numbering (LA-01) to WP-S-05 §11.1 for these signals, then extend `STATED` in `layout_check.py`. A change to WP-S-05, so for the HSI owner to decide |
