# LionDriver Hazard Log

| Field | Value |
|---|---|
| Document ID | LD-SAF-HZL-001 |
| Status | Living document |
| Governed by | [LD-SAF-PRC-001](PROCESS.md) §5.6 |

This log collects hazards found by field monitoring, RCA, testing and review. Each entry links to its hazardous event and safety goal in the HARA ([WP-C-03](../../../assurance/02-concept/WP-C-03-hara.md)) or to its SOTIF hazard ([WP-C-05](../../../assurance/02-concept/WP-C-05-sotif-hazard-identification.md)), or is rejected with a rationale. A new entry is `HARA-pending` until that is done.

**IDs.** Field hazards are numbered **FHZ-nnn** since revision C (2026-10-19). Until then they were HZ-001…HZ-008, which clashed with the second-set FMEA hazards HZ-001…HZ-013 (`assurance/08-analyses/fmea/analyses/hara.yaml`). The dated FI-2026-001 case files and code comments that cite "FI-2026-001, HZ-nnn" keep the old numbers: read HZ-nnn there as FHZ-nnn.

S/E/C below are the **provisional field-informed estimates** made before the HARA (ISO 26262-3 scale), kept as the record of the field view. They are not ASIL determinations; the linked HARA ratings govern.

| FHZ ID | Hazard / hazardous event | Operational situation | Source | Prov. S | Prov. E | Prov. C | Category | Status | HARA / SOTIF link | Controls (CA/PA) |
|---|---|---|---|---|---|---|---|---|---|---|
| FHZ-001 | Engaged vehicle does not decelerate enough for a stationary or slow vehicle in the ego lane → frontal collision | Highway / arterial, ≥ 70 km/h; queue tail, emergency scene, stalled vehicle, cut-out reveal | FI-2026-001 | S3 | E3–E4 | C2–C3 (complacency) | PERF, ML, MISUSE | Linked | Intended-function limit: WP-C-05 **SH-06** (stationary or slow vehicle not treated as lead). Fault-induced counterpart: WP-C-03 **H-06**, HE-06.1, **SG-06 (ASIL C)** | CA-002, CA-003, CA-004, CA-009, PA-02 |
| FHZ-002 | Stock OEM AEB/PCS disabled or suppressed by openpilot configuration → last-resort barrier lost | Any longitudinal engagement on affected platforms (radar-ACC Toyota + alpha long) | FI-2026-001 | S3 | E4 (while configured) | C3 | CFG, SYS | Linked | WP-C-03 **H-08**, HE-08.1, **SG-07 (ASIL B)**; WP-C-05 SH-08. The reference build refuses alpha longitudinal and is camera-ACC only (AOU-15, assured configuration SYS-040) | CA-001 |
| FHZ-003 | FCW absent or late because it shares perception with the longitudinal function (common cause) | As HZ-001 | FI-2026-001 | S3 | E3 | C3 | SYS | Linked | Not a separate hazardous event: a missing FCW is classified NSC in WP-C-03 (F-06 M01; the driver supervises and the stock PCS warns), so no rating credits FCW. The common-cause perception limit is WP-C-05 **SH-06**; fault-induced loss of deceleration is **H-06 / SG-06 (ASIL C)** | CA-005, CA-002 |
| FHZ-004 | Driver unavailable at the critical moment: distraction below DM threshold, slow escalation, automation complacency | Long engaged drives, high speed | FI-2026-001 | S3 | E4 | C3 | MISUSE, SYS | Linked | WP-C-03 **H-09**, HE-09.1/09.2 (OS-17, OS-18), **SG-08 (ASIL A)**; WP-C-05 SH-12; WP-C-08 MC-01…MC-03 | CA-006, CA-009 |
| FHZ-005 | Safety-relevant configuration drifts outside the assured baseline (forks, toggles, params) and is not identifiable after an event | Any | FI-2026-001 | (per resulting hazard) | — | — | CFG, PROC | Rejected as a hazard | A cause, not a hazard: a configuration outside the assured baseline invalidates the analyses of every hazard rather than adding one. Controlled by the assured configuration (WP-S-01 SYS-040, DQ-221 A; WP-C-01 AOU-14) and the process FMEA (PFM-003, PFM-005) | CA-008 (implemented: identity, check, log), CA-007 |
| FHZ-006 | Unintended or phantom hard braking (e.g. a stationary-clutter false positive). A side effect risk of HZ-001 fixes | Highway with overpasses, signs, parked vehicles | FI-2026-001 (CA-004 impact analysis) | S2–S3 | E4 | C2 | PERF | Linked | WP-C-03 **H-04** (F-02 M03 unrequested braking), HE-04.1, **SG-04 (ASIL B)**; WP-C-05 SH-04 | CA-004 impact analysis, SPI-06 |
| FHZ-007 | Rear-end collision by a following vehicle caused by strong automated braking | Dense traffic | FI-2026-001 (CA-004 impact analysis) | S2 | E3 | C2 | PERF | Linked | WP-C-03 **H-04**, HE-04.1 (rear impact by the following vehicle), **SG-04 (ASIL B)** | CA-004 study S5 (up to ~52 km/h at -8 m/s², short headways) |
| FHZ-008 | Lead vehicle brakes harder than openpilot's braking authority (≥ 4 m/s² at ≥ 100 km/h at standard following distance) → rear-end collision into the lead | Highway following; lead hard or emergency braking | FI-2026-001 (CA-004 study S3) | S2–S3 | E3 | C2 | PERF | Linked | Intended-function limit (deceleration need above −3.5 m/s²): WP-C-05 **SH-06**. Fault-induced counterpart: **H-06 / SG-06 (ASIL C)** | CA-011 (implemented: covers ≤ 4 m/s² up to 100 km/h), CA-010, CA-004 option (b) candidate |

## Revision history

| Rev | Date | Author | Change |
|---|---|---|---|
| A | 2026-10-10 | LionDriver maintainers | Initial entries HZ-001…HZ-007 from FI-2026-001 |
| B | 2026-10-10 | LionDriver maintainers | HZ-008 added from the CA-004 study |
| C | 2026-10-19 | Claude (AI assistant), HARA session | IDs renamed HZ-nnn → FHZ-nnn (clash with the FMEA hazard IDs). Every entry linked to WP-C-03 / WP-C-05 or rejected (FHZ-005), as the log's own rule requires now that the HARA exists |
