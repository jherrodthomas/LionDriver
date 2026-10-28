# Upstream sync impact analyses

This folder holds the impact analysis record for each upstream sync (change type CT-3,
[WP-P-02 §9](../WP-P-02-change-management.md#9-upstream-synchronization-ct-3-d-02)), produced
under the sync procedure in [WP-M-11 §5](../../01-management/WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02)
with the template in [WP-M-12 §7.3](../../01-management/WP-M-12-impact-analysis.md#73-template).

## When syncs happen

Syncs happen once per MINOR release, before the release-candidate freeze. The only out-of-cycle exception is a targeted security or safety fix. See [WP-M-11 §5](../../01-management/WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02) (D-02, decided 2026-10-10).

## Generating a report

```sh
tools/sync/sync_report.py <repo> [--to <upstream commit|branch|tag>] [--from <commit>]
```

`<repo>` is `openpilot` (the superproject) or one of `panda`, `opendbc_repo`, `msgq_repo`,
`rednose_repo`, `teleoprtc_repo`, `tinygrad_repo`. Defaults:

- `--from`: the current LionDriver pin. For a submodule that is its gitlink commit in `HEAD`. For
  `openpilot` it is the upstream baseline recorded in
  `openpilot/selfdrive/test/process_replay/ref_commit`.
- `--to`: upstream `master`. Name an exact commit before opening a sync change request; the
  procedure never syncs to a moving branch head.

The tool fetches upstream history without file contents and lists every commit and changed
file in the range. It classifies each file against
[`safety-relevant-paths.txt`](../safety-relevant-paths.txt) and writes
`sync-<date>-<repo>-<target>.md` here. It never changes pins and never pushes.

## From generated report to record

A generated report covers procedure steps 2–3 (range, commits, classification) and lays out
step 4. Before it becomes a record:

1. Read every diff in an SR-A or SR-Q file. Commit titles are not enough.
2. Fill in FuSa / SOTIF / AI / CS, the affected hazards and work products (every work product that describes the changed behaviour, not only the requirement documents: check at least WP-W-01, WP-W-03, WP-W-05, WP-W-09, WP-W-11 and the cybersecurity work products, [RR-2026-009](../../05-software/reviews/RR-2026-009.md) F-30), and the decision
   (take / modify / reject) for every safety-relevant commit.
3. Assign the `IA-<yyyy>-<nn>` number, link the change request, and record the author and
   reviewer with their independence level.
4. Attach the verification re-run results and list the updated work products.
5. Set `Status` to `In review`. Merge only after the review in
   [WP-P-05](../WP-P-05-verification-review-procedure.md) is done.

A report with `Status: Draft: generated, not reviewed` documents upstream drift. It is not
a sync decision.

## Records

| File | Range | Highest class | Status |
|---|---|---|---|
| [sync-2026-10-10-openpilot-b9c815d.md](sync-2026-10-10-openpilot-b9c815d.md) | openpilot `655bfde..b9c815d` (2 commits) | SR-Q | Draft: drift survey, no sync decided |
| [sync-2026-10-10-msgq-326a9f5.md](sync-2026-10-10-msgq-326a9f5.md) | msgq `0e266c1..326a9f5` (9 commits) | SR-Q | Draft: drift survey, no sync decided |

On 2026-10-10, upstream `panda`, `opendbc`, `rednose` and `teleoprtc` `master` were identical
to the LionDriver pins, so no report was generated for them.

## LionDriver change records

Impact analyses for changes LionDriver makes itself to safety-relevant code (change type CT-1, [WP-P-02](../WP-P-02-change-management.md)), using the same template.

| File | Change | Highest class | Status |
|---|---|---|---|
| [change-2026-10-12-panda-hw-watchdog.md](change-2026-10-12-panda-hw-watchdog.md) | panda: independent hardware watchdog, [jherrodthomas/panda#1](https://github.com/jherrodthomas/panda/pull/1); 100 Hz safety task and window mode, [jherrodthomas/panda#3](https://github.com/jherrodthomas/panda/pull/3); watchdog reset reporting, [jherrodthomas/panda#6](https://github.com/jherrodthomas/panda/pull/6) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently; D-1, D-2, D-3 accepted as interim |
| [change-2026-10-12-opendbc-toyota-rx-timeout.md](change-2026-10-12-opendbc-toyota-rx-timeout.md) | opendbc: Toyota RX timeout after 5 periods, [jherrodthomas/opendbc#1](https://github.com/jherrodthomas/opendbc/pull/1); engagement gated on the RX checks, [jherrodthomas/opendbc#3](https://github.com/jherrodthomas/opendbc/pull/3) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently |
| [change-2026-10-12-opendbc-toyota-tx-whitelist.md](change-2026-10-12-opendbc-toyota-tx-whitelist.md) | opendbc: PCS and DSU messages removed from the Toyota TX whitelist, [jherrodthomas/opendbc#2](https://github.com/jherrodthomas/opendbc/pull/2) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently |
| [change-2026-10-12-panda-safety-mode-lock.md](change-2026-10-12-panda-safety-mode-lock.md) | panda: safety-mode lock in the reference build, [jherrodthomas/panda#4](https://github.com/jherrodthomas/panda/pull/4) | SR-A | Integrated 2026-10-12 (panda `9f60e17`, opendbc `aff4033`; follow-ups panda `3859fa8`, opendbc `5b5a4ba`); not verified on hardware; not reviewed independently |
| [change-2026-10-12-panda-fast-heartbeat.md](change-2026-10-12-panda-fast-heartbeat.md) | panda: authority revoked 0.3 s after the last SoC heartbeat (TSR-407), [jherrodthomas/panda#7](https://github.com/jherrodthomas/panda/pull/7); siren when that revokes granted authority (TSR-516), [jherrodthomas/panda#15](https://github.com/jherrodthomas/panda/pull/15) (§5, all builds) | SR-A (`panda/board/**`) | Integrated 2026-10-12; not verified on hardware; not reviewed independently (panda `c2e5d93`). Siren: panda `c33343b`, 2026-10-13; not verified on hardware; not reviewed independently |
| [change-2026-10-12-panda-irq-priorities.md](change-2026-10-12-panda-irq-priorities.md) | panda: explicit interrupt priorities and atomic safety-configuration switch (TSR-519, WP-W-03 R-1, R-8), [jherrodthomas/panda#10](https://github.com/jherrodthomas/panda/pull/10) | SR-A (`panda/board/**`) | Integrated 2026-10-12; not verified on hardware; not reviewed independently (panda `52cad44`) |
| [change-2026-10-12-opendbc-toyota-eps-fault.md](change-2026-10-12-opendbc-toyota-eps-fault.md) | opendbc: LKA actuation refused while the EPS reports a fault (TSR-110), [jherrodthomas/opendbc#7](https://github.com/jherrodthomas/opendbc/pull/7); reporting to the host, [opendbc#8](https://github.com/jherrodthomas/opendbc/pull/8), [panda#11](https://github.com/jherrodthomas/panda/pull/11); siren on a persistent EPS fault (TSR-516(b)), [panda#14](https://github.com/jherrodthomas/panda/pull/14) | SR-A (`opendbc/safety/**`) | Integrated 2026-10-12; not verified on hardware; not reviewed independently (opendbc `242d63d`; reporting panda `877730e`, opendbc `adcb7c2`). Siren: panda `b790fca`, pinned by LionDriver PR #45, not merged at time of writing |
| [change-2026-10-12-opendbc-toyota-cruise-main.md](change-2026-10-12-opendbc-toyota-cruise-main.md) | opendbc: CRUISE_ACTIVE checked against MAIN_ON (TSR-405(c)), [jherrodthomas/opendbc#9](https://github.com/jherrodthomas/opendbc/pull/9); TSR-405(b) open | SR-A (`opendbc/safety/**`) | Integrated 2026-10-12; not verified on hardware; not reviewed independently (opendbc `875e325`) |
| [change-2026-10-12-tx-rate-supervision.md](change-2026-10-12-tx-rate-supervision.md) | opendbc and panda: per-ID TX rate supervision (TSR-518, [DN-01](../../05-software/design-notes/DN-01-tx-rate-supervision.md)), [jherrodthomas/opendbc#10](https://github.com/jherrodthomas/opendbc/pull/10), [jherrodthomas/panda#13](https://github.com/jherrodthomas/panda/pull/13) | SR-A (`opendbc/safety/**`, `panda/board/**`) | Integrated 2026-10-12; not verified on hardware; not reviewed independently (opendbc `7993399`, panda `8aa8671`) |
| [change-2026-10-12-opendbc-toyota-tx-arrival.md](change-2026-10-12-opendbc-toyota-tx-arrival.md) | opendbc: arrival supervision of the SoC's actuation frames in the reference build (TSR-408), [jherrodthomas/opendbc#11](https://github.com/jherrodthomas/opendbc/pull/11) | SR-A | Integrated: in every opendbc pin since `273f44e` (now `9a13f60`); not verified on hardware; not reviewed independently |
| [change-2026-10-13-host-supervision.md](change-2026-10-13-host-supervision.md) | openpilot: `selfdrived` acts on panda flags and `controlsAllowed` mismatches promptly; `controlsd` does not actuate on stale or non-finite inputs (TSR-308, TSR-602, TSR-615, TSR-621) | SR-Q | Integrated 2026-10-13 (LionDriver #51, `824a0b0`); not verified on the vehicle; not reviewed independently |
| [change-2026-10-13-pandad-fault-mapping.md](change-2026-10-13-pandad-fault-mapping.md) | pandad/cereal: `interruptRateSoundDma` fault type; `pandaStates.faults` never defaults an entry to `relayMalfunction` (SWF-025) | SR-Q | Integrated 2026-10-13 ([jherrodthomas/LionDriver#48](https://github.com/jherrodthomas/LionDriver/pull/48), `3534bc2`); SWF-ACT-025 completed; not reviewed independently |
| [change-2026-10-13-elm327-gate-hud-authority.md](change-2026-10-13-elm327-gate-hud-authority.md) | panda: ELM327 refused after the car mode until ignition off (DR-05); opendbc: assist-active LKAS_HUD refused without authority (DM-11); DFA DFI-08, DFI-19 | SR-A | Integrated 2026-10-13 (panda `a55bdfc`, opendbc `a57b667`); unit-tested; not verified on hardware; not reviewed independently |
| [change-2026-10-14-pcm-engage-heartbeat-gate.md](change-2026-10-14-pcm-engage-heartbeat-gate.md) | opendbc: PCM-edge authority granted only with the heartbeat's engaged flag (reference build, TSR-301), [jherrodthomas/opendbc#14](https://github.com/jherrodthomas/opendbc/pull/14); `selfdrived` 0.3 s engagement grace (TSR-621); WP-A-05 LS-06 | SR-A | Integrated 2026-10-14 (opendbc `9a13f60`) |
| [change-2026-10-14-ca001-alpha-long-interlock.md](change-2026-10-14-ca001-alpha-long-interlock.md) | openpilot: alpha longitudinal refused on vehicles so stock AEB/PCS is kept (CA-001, LD-FSR-001), [jherrodthomas/LionDriver#79](https://github.com/jherrodthomas/LionDriver/pull/79); explained process-replay diff on the Tesla route | SR-Q | Proposed 2026-10-14; unit-tested; not verified on a vehicle; not reviewed independently |
| [change-2026-10-17-relay-malfunction-latch.md](change-2026-10-17-relay-malfunction-latch.md) | panda: a relay malfunction is latched for the ignition cycle and TOYOTA refused until ignition off (reference build, DFA DM-25), [jherrodthomas/panda#17](https://github.com/jherrodthomas/panda/pull/17) | SR-A (`panda/board/**`) | Proposed 2026-10-17 (pin `0a7da85` for CI); unit-tested; MISRA-clean; not verified on hardware; not reviewed independently |
| [change-2026-10-17-eps-fault-escalation.md](change-2026-10-17-eps-fault-escalation.md) | openpilot: the lighter EPS-fault prompt after an override or at standstill lasts at most 1.5 s, then the take-over request (TSR-607 (b), register DQ-342 A, SFM-ACT-023); while the driver keeps steering, the lighter prompt after 1.5 s (TSR-607 (c), DQ-366 A) | SR-Q | Integrated 2026-10-17 (#174, `7158a9a`); (c) in the follow-up PR; unit-tested in CI; not verified on the vehicle; not reviewed independently |
| [change-2026-10-14-chill-mode-default.md](change-2026-10-14-chill-mode-default.md) | openpilot: `ExperimentalMode` defaults to off, so a new install starts in Chill mode (B-06, D-08, decision register DQ-001) | SR-Q | Integrated 2026-10-14 (LionDriver #74, `9552997`); not reviewed independently |
| [change-2026-10-13-opendbc-rx-length-fault.md](change-2026-10-13-opendbc-rx-length-fault.md) | opendbc: wrong-length frame of an RX-checked message as RX fault (reference build); WP-W-03 ATC-25, B2B-01 | SR-A (`opendbc/safety/**`) | Implemented 2026-10-17 in [jherrodthomas/opendbc#18](https://github.com/jherrodthomas/opendbc/pull/18), pinned at `62b89a3` ([change-2026-10-17-pin-62b89a3](change-2026-10-17-pin-62b89a3.md)); not reviewed independently |
| [change-2026-10-13-release-variant.md](change-2026-10-13-release-variant.md) | LionDriver: explicit `RELEASE_VARIANT` (reference by default) in the release script; CI job building the reference release firmware (WP-W-03 ATC-19, F-33) | SR-Q | Proposed 2026-10-13; CI job not yet run; not reviewed independently |
| [change-2026-10-13-tx-rate-reengagement.md](change-2026-10-13-tx-rate-reengagement.md) | opendbc: no re-engagement while a TX-rate excess persists (amended SWSR-518, WP-W-03 ATC-20, F-34) | SR-A | Integrated 2026-10-16 at the pin bump to opendbc `515b9a2` (merged as opendbc#15); unit-tested; not reviewed independently |
| [change-2026-10-14-mode-set-regrant.md](change-2026-10-14-mode-set-regrant.md) | opendbc: no authority after a safety-mode change without a new engagement (amended SWSR-311, WP-W-03 ATC-26, B2B-06) | SR-A | Integrated 2026-10-16 at the pin bump to opendbc `515b9a2` (merged as opendbc#15); unit-tested; not reviewed independently |
| [change-2026-10-16-pin-515b9a2.md](change-2026-10-16-pin-515b9a2.md) | opendbc pin `9a13f60` → `515b9a2` (opendbc#15, #16); authority record with the LS-06 engagement window (ENGAGE_PENDING); temporary B2B deviations removed; finding SM-F1 (an edge while MAIN_ON = 0 opens the window) | SR-A | Integrated 2026-10-16 (LionDriver #158); finding SM-F1 fixed 2026-10-17; not reviewed independently |
| [change-2026-10-17-pin-98d3be1.md](change-2026-10-17-pin-98d3be1.md) | opendbc pin `515b9a2` → `98d3be1`: finding SM-F1 fixed, a cruise edge refused for MAIN_ON = 0 closes the engagement window ([jherrodthomas/opendbc#17](https://github.com/jherrodthomas/opendbc/pull/17); SWSR-405(c)) | SR-A | Proposed 2026-10-17; unit-tested, LionDriver CI (MISRA, mutation) green at `032bbef`; not reviewed independently |
| [change-2026-10-17-pin-62b89a3.md](change-2026-10-17-pin-62b89a3.md) | opendbc pin `98d3be1` → `62b89a3`: a wrong-length frame of an RX-checked message is an RX fault in the reference build (ATC-25, [jherrodthomas/opendbc#18](https://github.com/jherrodthomas/opendbc/pull/18); SWSR-402, B2B-01 closed) | SR-A | Proposed 2026-10-17; unit-tested, LionDriver CI probe at `8c0ef6b`; not reviewed independently |
| [change-2026-10-17-pin-27f20db.md](change-2026-10-17-pin-27f20db.md) | opendbc pin `62b89a3` → `27f20db`: only accepted command frames keep authority (SWSR-408 v0.28, WP-W-03 ATC-27, [jherrodthomas/opendbc#19](https://github.com/jherrodthomas/opendbc/pull/19); B2B-04 and B2B-05 closed); panda pin to `3ee2796`: the EPS-fault siren also sounds after that revocation ([jherrodthomas/panda#18](https://github.com/jherrodthomas/panda/pull/18), DQ-367) | SR-A | Proposed 2026-10-17; unit-tested, LionDriver CI probes green; not reviewed independently |
| [change-2026-10-17-panda-eps-siren-0-7s.md](change-2026-10-17-panda-eps-siren-0-7s.md) | panda pin `3ee2796` → `bf8102a`: EPS-fault siren persistence 0.7 s instead of 1 s, siren ≤ 0.96 s from onset ([jherrodthomas/panda#19](https://github.com/jherrodthomas/panda/pull/19); DQ-048, TSR-516(b), WP-S-04 OI-8) | SR-A | Proposed 2026-10-17; host-tested, LionDriver CI probe; not reviewed independently |
| [change-2026-10-17-dm-wheeltouch-distance.md](change-2026-10-17-dm-wheeltouch-distance.md) | openpilot: in the wheel-touch fallback, alert k at 5/15/25 s or 150/240/395 m since the last driver interaction, whichever comes first (TSR-634, SWSR-634, register DQ-077 A, WP-C-08 §5.4) | SR-Q | Proposed 2026-10-17; unit-tested; not verified in the vehicle; not reviewed independently |
| [change-2026-10-19-reference-entry-checks.md](change-2026-10-19-reference-entry-checks.md) | openpilot: on the reference platform, no engagement outside the assured settings (DQ-221 A) or below 60 km/h (DQ-280 A); the distance button keeps the relaxed distance | SR-Q | Proposed 2026-10-19; unit-tested; not verified in the vehicle; not reviewed independently |
| [change-2026-10-19-stock-aeb-stand-down.md](change-2026-10-19-stock-aeb-stand-down.md) | openpilot: while the car reports a stock AEB event, no positive acceleration is requested (DQ-300 A, SFM-ACT-020) | SR-Q | Proposed 2026-10-19; unit-tested; not verified in the vehicle; not reviewed independently |
| [change-2026-10-19-pin-e233362.md](change-2026-10-19-pin-e233362.md) | opendbc pin `27f20db` → `e233362`: the Toyota car controller rate-limits the final ACCEL_CMD at 4.5 m/s³ (WP-W-02 OI-15) and sends no positive command during a stock AEB event (SWSR-713h, DQ-300 OI-2), [jherrodthomas/opendbc#20](https://github.com/jherrodthomas/opendbc/pull/20) | SR-Q | Proposed 2026-10-19; unit-tested; not verified in the vehicle; not reviewed independently |
| [change-2026-10-20-settings-held-while-engaged.md](change-2026-10-20-settings-held-while-engaged.md) | openpilot: on the reference platform, a setting changed in the menu while engaged is held until the driver disengages (DQ-403 A) | SR-Q | Proposed 2026-10-20; unit-tested; not verified in the vehicle; not reviewed independently |
| [change-2026-10-20-panda-tx-arrival-siren.md](change-2026-10-20-panda-tx-arrival-siren.md) | opendbc pin `e233362` → `4d1a056`, panda pin `bf8102a` → `8a69ccf`: the TX-arrival revocation (TSR-408) sounds the panda siren, so a full SoC stall is no longer silent ([jherrodthomas/opendbc#21](https://github.com/jherrodthomas/opendbc/pull/21), [jherrodthomas/panda#20](https://github.com/jherrodthomas/panda/pull/20); DQ-404 A, TSR-516(b), WP-S-04 T-34) | SR-A | Proposed 2026-10-20; host-tested; not verified on hardware; not reviewed independently |
| [change-2026-10-20-dm-first-alert-time.md](change-2026-10-20-dm-first-alert-time.md) | openpilot DM policy: the awareness countdown follows elapsed time (SWSR-635a), an uncertain pose output counts as not attentive and the escalation no longer stops at orange (SWSR-635b); TSR-635 | SR-A | Proposed 2026-10-20; unit-tested; not verified on the device; not reviewed independently |
| [change-2026-10-21-panda-engaged-mismatch.md](change-2026-10-21-panda-engaged-mismatch.md) | panda pin `8a69ccf` → `f4803c5`: in the reference build a heartbeat "not engaged" while authority is granted revokes within 0.3 s in the 100 Hz safety task, and the siren sounds if PCM cruise is still active 0.5 s after it ([jherrodthomas/panda#21](https://github.com/jherrodthomas/panda/pull/21); TSR-307(a), TSR-516(c), MCS-02.9) | SR-A | Proposed 2026-10-21; host-tested; not verified on hardware; not reviewed independently |
| [change-2026-10-22-no-comma-upload.md](change-2026-10-22-no-comma-upload.md) | openpilot: the uploader and athena are never started, so nothing is uploaded to comma.ai and comma has no remote access (DQ-121 A, after DQ-084 A) | SR-Q | Proposed 2026-10-22; unit test in CI; not verified on the device |
| [change-2026-10-21-pin-3a8b7c2.md](change-2026-10-21-pin-3a8b7c2.md) | panda pin `f4803c5` → `3a8b7c2`: HIL test for the engaged mismatch (TSR-307(a), TSR-516(c)), no firmware change ([jherrodthomas/panda#22](https://github.com/jherrodthomas/panda/pull/22)) | SR-A | Proposed 2026-10-21; test not run on hardware; not reviewed independently |
| [change-2026-10-25-reference-debug-procs.md](change-2026-10-25-reference-debug-procs.md) | openpilot and release tooling: the reference build neither registers nor ships the joystick and maneuver processes, and no debug param changes the control processes; the DQ-221 entry refusal stays as a second barrier (DQ-131 A; FM-06, CSR-071, TSR-806) | SR-Q, SR-T | Proposed 2026-10-25; unit test in CI; not verified on the device; not reviewed independently |
| [change-2026-10-27-reference-test-switches.md](change-2026-10-27-reference-test-switches.md) | openpilot manager: in the reference build on the device, the test-only environment switches (REPLAY, SIMULATION, FINGERPRINT, BLOCK, STARTED and others) are removed before any process starts (DQ-425 A, decider Claude; SWF-028.C2, SWF-030.C2) | SR-Q | Proposed 2026-10-27; unit test and mutants in CI; not verified on the device; not reviewed independently |
| [change-2026-10-25-startup-fault-code-read.md](change-2026-10-25-startup-fault-code-read.md) | openpilot: on the reference platform, card reads the EPS and ABS/VSC fault codes at start-up (UDS `0x19 0x02`, only stationary and before `FirmwareQueryDone`), and selfdrived refuses engagement on an active code or a failed read (DQ-132 A, after DQ-056 A; TSR-629, SWSR-629…629d) | SR-Q | Proposed 2026-10-25; unit-tested with mocked UDS responses; not verified on the vehicle (WP-S-09 VS-SQ-20); not reviewed independently |

The RX checks for `0x262` and `0x1D3` in the reference build (opendbc `98404a4`, [jherrodthomas/opendbc#6](https://github.com/jherrodthomas/opendbc/pull/6)) are recorded in the RX timeout record (§8) and the EPS fault record.
