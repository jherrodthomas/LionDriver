# LionDriver Hazard Log

| Field | Value |
|---|---|
| Document ID | LD-SAF-HZL-001 |
| Status | Living document |
| Governed by | [LD-SAF-PRC-001](PROCESS.md) §5.6 |

This log collects hazards found by field monitoring, RCA, testing and review. **No HARA has been issued yet**, so every entry here is a required input to the first HARA and is flagged `HARA-pending`. Once the HARA exists, each entry must link to its hazardous event and safety goal, or be rejected with a rationale.

S/E/C below are **provisional field-informed estimates** (ISO 26262-3 scale) for planning only. They are not ASIL determinations.

| HZ ID | Hazard / hazardous event | Operational situation | Source | Prov. S | Prov. E | Prov. C | Category | Status | Controls (CA/PA) |
|---|---|---|---|---|---|---|---|---|---|
| HZ-001 | Engaged vehicle does not decelerate enough for a stationary or slow vehicle in the ego lane → frontal collision | Highway / arterial, ≥ 70 km/h; queue tail, emergency scene, stalled vehicle, cut-out reveal | FI-2026-001 | S3 | E3–E4 | C2–C3 (complacency) | PERF, ML, MIS | HARA-pending | CA-002, CA-003, CA-004, CA-009, PA-02 |
| HZ-002 | Stock OEM AEB/PCS disabled or suppressed by openpilot configuration → last-resort barrier lost | Any longitudinal engagement on affected platforms (radar-ACC Toyota + alpha long) | FI-2026-001 | S3 | E4 (while configured) | C3 | CFG, SYS | HARA-pending | CA-001 |
| HZ-003 | FCW absent or late because it shares perception with the longitudinal function (common cause) | As HZ-001 | FI-2026-001 | S3 | E3 | C3 | SYS | HARA-pending | CA-005, CA-002 |
| HZ-004 | Driver unavailable at the critical moment: distraction below DM threshold, slow escalation, automation complacency | Long engaged drives, high speed | FI-2026-001 | S3 | E4 | C3 | MIS, SYS | HARA-pending | CA-006, CA-009 |
| HZ-005 | Safety-relevant configuration drifts outside the assured baseline (forks, toggles, params) and is not identifiable after an event | Any | FI-2026-001 | (per resulting hazard) | — | — | CFG, PROC | HARA-pending | CA-007, CA-008 |
| HZ-006 | Unintended or phantom hard braking (e.g. a stationary-clutter false positive). A side effect risk of HZ-001 fixes | Highway with overpasses, signs, parked vehicles | FI-2026-001 (CA-004 impact analysis) | S2–S3 | E4 | C2 | PERF | HARA-pending | CA-004 impact analysis, SPI-06 |
| HZ-007 | Rear-end collision by a following vehicle caused by strong automated braking | Dense traffic | FI-2026-001 (CA-004 impact analysis) | S2 | E3 | C2 | PERF | HARA-pending | CA-004 impact analysis |

## Revision history

| Rev | Date | Author | Change |
|---|---|---|---|
| A | 2026-10-10 | LionDriver maintainers | Initial entries HZ-001…HZ-007 from FI-2026-001 |
