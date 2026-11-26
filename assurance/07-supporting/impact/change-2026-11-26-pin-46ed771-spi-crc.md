# Change impact: panda pin to `46ed771`, SPI protocol version 3 with CRC-32C, sequence counter and length bound (SWSR-410, 410a, 410h, 412)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to safety-relevant firmware and its host (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-11-26** in this LionDriver PR; host-tested end to end; not verified on hardware; not reviewed independently |
| Pin | panda `fd0a6a7` → `46ed771` (merge commit of [jherrodthomas/panda#26](https://github.com/jherrodthomas/panda/pull/26), change commit `591f8e7`). opendbc unchanged. `pandad` changes in this PR |
| Decision | Register DQ-143 A (project lead): a CRC meeting the residual-error target; CRC-32C selected as a technical choice within it (WP-S-05 §4.1, 2026-11-01). The lead set the order "small fixes first", G-4 bounds check, allow-list, then the SPI CRC, and approved the panda merge in chat ("Merge, then pin") |
| Requirements | TSR-410, TSR-412 (TSR-411 field only); SWSR-410, 410a, 410h, 412 implemented; SWSR-410i (new, host) met by the current hosts; SWSR-413 counts more causes |
| Reference configuration affected | Yes, all builds (the protocol is the same in every build, the bootstub included) |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Commit(s) | Files | Summary of behaviour change | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Verification to re-run | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| panda `591f8e7` | `board/crc32c.h` (new), `board/drivers/spi.h`, `python/spi.py`, `tests/spi_protocol` (new), `tests/hitl/test_5_spi.py` | The 8-bit XOR checks are replaced. Header (7 bytes, as before): sync, endpoint, MOSI length, max MISO length, CRC-8 (poly `0x2F`). Data: sequence counter, control-frame index, payload, CRC-32C over header bytes 0–5, counter, index and payload. Response: DACK, length, echoed counter, payload, CRC-32C. A length beyond the 2047-byte data phase is NACKed at the header. Counter: a step of 1 or 2 is accepted, the last executed counter again is acknowledged without running it, any other step gets `SEQ_NACK` (`0x2E`); every rejection is counted. Protocol version 2 → 3. `spi_rx_done` is split into small functions | Yes (TSR-410, 412: corruption, repetition, loss, reordering of host commands) | No | No | No (a CRC is not a security measure, WP-S-07) | GAP-10, GAP-47; SWF-026.C1 (SWF-ACT-027); DFM-015.C1 (DFM-ACT-009) | WP-W-02 SWSR-410, 410a, 410h, 412, 413; WP-S-05 §4.1 (layout, see §2); WP-S-02 TSR-410, 412 status; WP-W-03, WP-W-05 UN-23 | panda host tests, panda MISRA, HIL `test_5_spi`, `test_pandad_spi.py` | DQ-143 A; lead, chat |
| this PR | `panda`; `openpilot/selfdrive/pandad/spi.cc`, `panda_comms.h`, `panda.cc`; `tests/test_pandad_spi_protocol.py` and `spi_protocol_host.cc` (new); `.github/workflows/safety.yaml` (host suite `spi_protocol`); `tools/ci/complexity_exceptions.toml` (the `spi_rx_done` exception, NLOC 101, CCN 22, removed; `crc32c.h` in scope); WP-W-02 v0.56; generated outputs | `pandad` speaks protocol 3: counter kept across retries and restarted at 0 after `SEQ_NACK`, the sendcan message number as control-frame index on endpoint 3, response length checked against the request | — | — | — | — | — | — | — | — |

## 2. Effect

- **Layout differs from WP-S-05 §4.1.** §4.1 places the counter and the control-frame index in the header with its own CRC-32C. The header has to stay 7 bytes, because the 7-byte `VERSION` request must be recognised by every firmware: hosts use it to detect a protocol mismatch and recover an old panda, app or bootstub, through DFU (`pandad.py`). The MCU receives the header by a fixed-length DMA. So the two fields moved to the start of the data phase, where the CRC-32C covers them with the header fields before anything runs. The header CRC-8 only keeps a corrupted length from starting a wrong DMA. Proposed to the FSC/TSC owner as a §4.1 edit.
- **Upgrade.** Host and firmware must match. A panda on protocol 2 is refused (`PandaProtocolMismatch`) and recovered through DFU by `pandad.py`, as on earlier upstream bumps. Not tried on a device.
- **Residuals of the counter rule.** 0 starts a session and is always accepted, so a host retry of a session's first transfer can run twice. New SWSR-410i makes that first transfer a read in both hosts (`pandad`: `0xc3`; the library: `0xdd`), so the repeat changes nothing. The FSC/TSC owner had proposed treating a 0 after a 0 as a repeat instead. That would have stopped `pandad` connecting: `Panda::list()` (`pandad.cc:478`) opens a one-transfer session, and the real handle's first read at 0 would then be suppressed on every attempt. A repeated CAN read (a retry after a lost response) returns no data; the frames read the first time are lost, as before. A second host process moves the panda's counter; the first one then gets one `SEQ_NACK`, restarts and goes on.
- **Error count.** CRC, length and counter rejections all count in `spi_error_count`. The hosts' drain after a failed transfer (bytes `0x11` / `0x14`) is still counted as bad headers, as before this change; SWSR-413 has to allow for it when it is built (OI-3).
- **Timing.** The CRC is computed in software, four bits at a time: about two table steps per byte, inside the DMA interrupt. Not measured on the MCU (OI-4).

## 3. Verification results

| Check | Result |
|---|---|
| panda host test (local) | `tests/spi_protocol`, 21 tests: the real `spi.h` on a simulated SPI4 bus, driven by the real `python/spi.py`. CRC-32C check value on both ends; every 1-bit error and 3000 random cases each of 2-bit, 3-bit and ≤ 32-bit burst errors on a 64-byte CAN write, none executed; header CRC; length bounds; repetition, gap, reorder, wrap, NACKed transfer, second host session, lost response not executed twice |
| Mutation (local, by hand) | 12 mutants of `spi.h` (CRC not checked, step 3 accepted, repetition executed, MOSI and MISO bounds, header CRC not checked, counter advanced on NACK, echo wrong, repetition and bad step not counted, header outside the data CRC, no resync at 0): all killed |
| pandad end to end (local) | `test_pandad_spi_protocol.py`: `spi.cc` against the pinned `spi.h` over the same bus model, covering connect, 600 control requests through a counter wrap, a 5000-byte CAN write in three transfers with its frame index, a CAN read and a second host session. Passes |
| panda host suites (local) | All nine suites pass |
| panda MISRA (local) | cppcheck MISRA C:2012 clean in both builds, with the host gcc include path (the ARM toolchain is not installed locally; CI runs the real script) |
| ENV-R-07 (local) | `check_complexity.py` passes; 12 exceptions (one fewer) |
| HIL / device | **Not run** (D-04): `test_5_spi` (new header-CRC, length and counter cases), `test_pandad_spi.py` with `SPI_ERR_PROB` |

## 4. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | WP-S-05 §4.1: accept or change the layout of §2 (FSC/TSC owner); TSR-410 and 412 status in WP-S-02 | Next WP-S-05 revision |
| OI-2 | SWSR-411: reject an endpoint-3 transfer whose control-frame index is more than 2 control periods older than the newest accepted one; the Python library sends index 0 | Next panda PR |
| OI-3 | SWSR-413: revoke on N_spi errors while engaged, without counting the hosts' NACK drain | SWSR-413 PR |
| OI-4 | Measure the CRC time in the DMA interrupt; the STM32H7 CRC unit as an alternative | HIL bench (D-04) |
| OI-5 | HIL: `test_5_spi`, `test_pandad_spi.py` with `SPI_ERR_PROB`, and the DFU upgrade from protocol 2; bit-error-rate soak at 50 MHz (new measurement ID, WP-S-05 OI-2) | HIL bench (D-04) |
| OI-6 | SW FMEA SWF-026.C1 and DFMEA DFM-015.C1: re-rate with the CRC and counter as controls (FMEA owners) | FMEA revision |
| OI-7 | A host test that fails when a session's first counted transfer is not a read (SWSR-410i), for `pandad` and the Python library | Next host PR |
