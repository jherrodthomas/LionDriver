# Field Issue Register

| Field | Value |
|---|---|
| Document ID | LD-SAF-REG-001 |
| Governed by | [LD-SAF-PRC-001](PROCESS.md) |

| FI ID | Title | Source | Received | Class | Category | Applicable? | Status | Containment | Hazards | Actions | Case |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FI-2026-001 | NHTSA PE26007: openpilot strikes stopped/slow in-lane vehicles (5 crashes, 3 fatalities) | NHTSA ODI / press | 2026-10-10 | A | PERF, ML, MISUSE, CFG, PROC | Yes | RCA (awaiting logs and reproduction) | C-1, C-2, C-3 | HZ-001…008 | CA-001…012, PA-01/02, FA-01 | [case](cases/FI-2026-001-nhtsa-pe26007/REPORT.md) |

## Monitoring log

Record each scheduled source sweep (PROCESS §5.1), including sweeps that found nothing.

| Date | Sources checked | New signals | FI IDs raised | By |
|---|---|---|---|---|
| 2026-10-10 | NHTSA PE26007 press coverage | 1 | FI-2026-001 | Maintainer |
| 2026-10-10 | CA-002 SIL baseline (own test data) | 0 new (FI-2026-001 B3 confirmed in SIL) | — | Maintainer |
| 2026-10-10 | CA-004 braking-authority study (own test data) | 1 new hazard in FI-2026-001 scope (HZ-008, TC-07) | — | Maintainer |

## Lessons learned

| FI ID | Lesson |
|---|---|
| FI-2026-001 | A limitation that is only *documented* (`docs/LIMITATIONS.md`) is not a control. Stationary in-lane vehicles were a known upstream limitation, handled solely by user information. Every Class A limitation needs an engineered control or an operating-domain restriction. |
| FI-2026-001 | An "alpha" toggle can remove an independent OEM safety barrier. Configuration options need safety impact analysis just like code changes. |
