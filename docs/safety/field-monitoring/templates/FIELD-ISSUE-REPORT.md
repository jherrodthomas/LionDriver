# FI-YYYY-NNN — <short title>

> Template for LD-SAF-PRC-001 §5.1–5.4. Copy it to `cases/FI-YYYY-NNN-<slug>/REPORT.md`.

## 1. Header

| Field | Value |
|---|---|
| FI ID | FI-YYYY-NNN |
| Title | |
| Date received | |
| Reporter / source | |
| Source type | Regulator · Upstream · Fork · Media/community · Own test data · Security · OEM |
| Source links | |
| Severity class | A · B · C · D (per PROCESS §5.2) |
| Provisional category | SYS · RHF · PERF · ML · MISUSE · CFG · CYB · PROC |
| Safety anomaly? | Yes / No (rationale) |
| Status | Open · Containment · RCA · CA · Verification · Awaiting independent review · Closed |
| Safety manager | |
| RCA lead | |

## 2. Event description

What happened. Keep facts separate from claims.

| # | Fact | Source | Confidence (Verified / Reported / Unconfirmed) |
|---|---|---|---|
| 1 | | | |

**Known unknowns:** list the information that is missing and would change the analysis (logs, software version, fork, toggles, driver state, speed, lighting, …).

## 3. Operating context

| Item | Value |
|---|---|
| Vehicle make / model / year | |
| ADAS platform (e.g. Toyota TSS2, radar-ACC) | |
| Device & hardware | |
| Software (upstream / fork, version, commit) | |
| Non-default toggles or parameters | |
| Function engaged (lateral / longitudinal / both / stock ACC) | |
| Road type, speed, lighting, weather | |
| Scenario (e.g. stopped vehicle in lane, cut-out, curve) | |
| Driver state (DM data, if known) | |
| Outcome (injuries, damage) | |

## 4. Applicability to LionDriver (PROCESS §5.3)

| Question | Answer | Evidence (file:line @ commit, flag, domain exclusion) |
|---|---|---|
| Is the suspected component in our baseline? | | |
| Is our reference platform architecturally similar? | | |
| Can the triggering scenario occur in our operating domain? | | |
| Same HMI / DM policy / driver population? | | |
| **Applicable?** | Yes / Partially / No | |

## 5. Containment (PROCESS §5.4)

| Decision | Rationale | In force from | Lift criterion |
|---|---|---|---|
| | | | |

## 6. Links

- RCA: `RCA.md`
- Hazard log entries:
- Corrective actions:
- Upstream / external references:

## 7. Revision history

| Rev | Date | Author | Change |
|---|---|---|---|
| A | | | Initial |
