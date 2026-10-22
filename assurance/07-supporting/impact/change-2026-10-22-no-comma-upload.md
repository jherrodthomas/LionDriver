# Change impact: the uploader and athena are never started (DQ-121)

Impact analysis per [WP-M-12](../../01-management/WP-M-12-impact-analysis.md) §7.3 for a LionDriver-originated change to host software (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)). It implements the project lead's answer to DQ-121, option A (2026-10-22), which carries out DQ-084 A: LionDriver test drives upload nothing to comma.ai. Until now the process manager skipped the uploader and athena only while the device had no comma registration (`system/manager/manager.py:108-109`), and a comma 3X registers itself from a factory dongle ID (`system/athena/registration.py:36-47`).

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Status | **Proposed 2026-10-22** in this LionDriver PR; checked by a unit test in CI; not verified on the device; not reviewed independently |
| Change requests | This LionDriver PR |
| Class | SR-Q (`openpilot/system/manager/process_config.py`, [safety-relevant-paths.txt](../safety-relevant-paths.txt)) |
| Reference configuration affected | Yes, and every other LionDriver install: no build of this fork starts the two processes |
| Decision | DQ-121 A (lead, inbox, 2026-10-22), after DQ-084 A |
| Requirements | [WP-O-04](../../09-production-operation/WP-O-04-field-monitoring.md) OI-1 and §3.3 (development data path); GAP-27 ([WP-M-09](../../01-management/WP-M-09-cybersecurity-plan.md) §2); [WP-S-07](../../03-system/WP-S-07-cybersecurity-requirements-architecture.md) CSR-112 no longer applies while athena does not run |
| Author / reviewer (independence) | Claude (AI-assisted draft) / TBD; an AI draft is not a review (WP-M-06) |

## 1. Change

| Change | Files | Behaviour | Verification |
|---|---|---|---|
| No uploader, no athena | `openpilot/system/manager/process_config.py` (`manage_athenad`, `uploader`: `enabled=False`) | The manager's `ensure_running` starts a process only when it is enabled, so neither starts, onroad or offroad, whatever the registration, pairing or settings. Logs stay on the device for manual retrieval (WP-O-04 §3.3) | `openpilot/system/manager/test/test_no_comma_upload.py`: both processes disabled, and neither selected onroad or offroad. Run by the `unit tests` job (`tools/op.sh test`); not run locally (needs the scons build of `libparams` and msgq) |

## 2. Impact

- **Safety:** none on the driving functions. Neither process is in the control path; `loggerd` still records to the device.
- **Cybersecurity:** removes the remote connection of GAP-27 (live-service RPCs, file uploads to arbitrary URLs, SSH tunnel, camera streaming) and the automatic upload path. Updates (`updated`) are unaffected.
- **Field monitoring:** comma's copy of the logs is no longer a fallback; the manual retrieval of WP-O-04 §3.3 is the only path.
- **Upstream:** a two-line difference to carry at each openpilot sync (WP-M-11).

## 3. Open items

| ID | Item | Needed by |
|---|---|---|
| OI-1 | Device registration still contacts `api.commadotai.com` at manager start (`manager.py:66`, `registration.py`) with the serial, IMEI and public key, and the pairing and prime screens of the UI query the same API. No logs or video; decide whether registration is also suppressed (WP-O-04 OI-1) | G1, before the first public-road drive |
| OI-2 | Check on the reference device: neither process running (`ps`), and no connection to comma's hosts during a drive except registration | Vehicle test (WP-V-07) |
| OI-3 | Carry the difference at each upstream sync (sync report, WP-M-11) | Each sync |
