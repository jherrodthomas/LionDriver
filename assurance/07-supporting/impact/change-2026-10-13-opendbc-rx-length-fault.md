# Change impact: wrong-length frame of an RX-checked message is an RX fault (proposed)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3, drafted **before** the change for a LionDriver-originated change to safety-relevant firmware (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Implemented 2026-10-17** in [jherrodthomas/opendbc#18](https://github.com/jherrodthomas/opendbc/pull/18) (fix commit `8c0ef6b`), pinned at `62b89a3`; verification in [change-2026-10-17-pin-62b89a3](change-2026-10-17-pin-62b89a3.md). Decision to change the code rather than SWSR-402: project maintainer, 2026-10-13, on the recommendation in [B2B-TOY-AUTH-2026-10-13](../../05-software/reference-models/results/B2B-TOY-AUTH-2026-10-13.md) B2B-01. Not reviewed independently |
| Change request | [jherrodthomas/opendbc#18](https://github.com/jherrodthomas/opendbc/pull/18). Target-state entry: [WP-W-03](../../05-software/WP-W-03-software-architecture.md) ATC-25 |
| Range | — (opendbc `7993399` is the baseline) |
| Reference configuration affected | Yes: the Toyota safety mode runs on the reference device |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD. An AI draft is not a review (WP-M-06) |

## 1. Problem

[SWSR-402](../../05-software/WP-W-02-software-safety-requirements.md) requires the envelope to verify the checksum **and the length** of the Toyota RX-checked messages and to treat one failure as an RX fault. SWSR-406 then requires authority to be cleared in the same call. At opendbc `7993399`, the RX-check entry matches on (address, bus, length). A frame with the right address on bus 0 but a different DLC therefore matches no entry. It is handled like an unchecked ID: it is not validated, does not clear authority, and does not update the time stamp. Only the RX timeout (5 periods plus one task period) catches a message that arrives with the wrong length.

The back-to-back run shows it for all six RX messages in both builds (directed scenario D08; random sequences with DLC 0, 6 and 7). For `0x226`, length is the only validation the message has (no checksum). A brake press in a wrong-length frame is not acted on until the next valid `0x226` frame (D14, WP-W-05 OI-1).

## 2. Proposed change

| Item | Proposal |
|---|---|
| Behaviour | A frame on the RX-check bus whose address matches an RX-check entry, but whose length does not, is an RX fault: `controls_allowed = false` in the same call, and the entry's status is invalid until the next valid frame, so authority cannot be granted again (SWSR-306) |
| Where | `opendbc/safety/safety.h`, in or next to `get_addr_check_index` / `rx_msg_safety_check` (UN-01, UN-02) |
| Build scope | Reference build only (`LIONDRIVER_REFERENCE`), like the other LionDriver envelope changes. Other modes keep the upstream behaviour unless decided otherwise |
| Alternatives considered | (a) Amend SWSR-402 so that a length mismatch makes the frame ignored and the timeout covers it. Not chosen (maintainer decision): it leaves a bus fault or attack with up to 5 periods of undetected stale input, and a brake press in such a frame unprocessed |

## 3. Impact

| Area | Effect |
|---|---|
| FuSa | Detection of a malformed RX-checked frame moves from ≤ 5 periods + 10 ms to the same RX call (SWSR-402, 406). Safe direction: more revocations, never a grant |
| Availability | A vehicle that legitimately sends one of these IDs with a different length on bus 0 would never engage. Check the reference-car logs for the DLC of `0xAA`, `0x260`, `0x1D2`, `0x226`, `0x262`, `0x1D3` before release (all 8 in the DBC) |
| CS | A short-frame injection on the car bus now revokes authority at once instead of starving the input for 5 periods |
| SOTIF / AI | None |
| Other brands | None if scoped to the reference build |

## 4. Work products affected

| WP | Change |
|---|---|
| WP-W-02 SWSR-402, 406 | Baseline column: implemented (reference build) once integrated |
| WP-W-05 UN-01, UN-02; OI-1 | Error handling and algorithm text; OI-1 answered by the new behaviour |
| `state-machines/sm-toy-auth.yaml` T4 | Guard "checksum, quality flag, counter **or length** invalid"; code citation updated; WP-W-05 §5.2 regenerated |
| Back-to-back model | Remove the `length_not_checked` deviation. The CI gate will report it as "no longer needed" in the reference build. It stays needed in the upstream build if the change is reference-only, so it becomes per-build there. Done: the option applies to the upstream build only |
| WP-W-06 / opendbc tests | New host tests: for each RX-checked message, a wrong-length frame while engaged clears authority, and blocks engagement until a valid frame arrives |

## 5. Verification to run after implementation

- opendbc safety tests, both variants, with the 100 % line-coverage gate and mutation testing (`safety.yaml`).
- `b2b_toy_auth.py --all --gate` and `layout_check.py` (`b2b.yaml`), with the deviation updated as above.
- MISRA (opendbc and panda).
- Replay of reference-car logs: no new RX faults.
