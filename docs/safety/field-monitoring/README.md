# Field Monitoring, Safety Anomalies & Root Cause Analysis

This folder holds LionDriver's closed loop from the field back to the safety case. Every field signal follows one path, whether it comes from a regulator, upstream openpilot, a fork, the community or our own test drives:

**intake → triage → applicability → containment → root cause analysis → hazard log / HARA · SOTIF · TARA update → corrective action → verification → closure**

| File | Purpose |
|---|---|
| [`PROCESS.md`](PROCESS.md) | The process (LD-SAF-PRC-001): roles, classes, methods, closure criteria, SPIs |
| [`REGISTER.md`](REGISTER.md) | Every field issue, its status and the monitoring log |
| [`HAZARD-LOG.md`](HAZARD-LOG.md) | Hazards found from the field. Inputs to the first HARA |
| [`templates/`](templates/) | Field issue report, RCA and corrective-action templates |
| [`cases/`](cases/) | One folder per field issue |

## Reporting a field issue

1. Open a GitHub issue with the `field-issue` label, or copy [`templates/FIELD-ISSUE-REPORT.md`](templates/FIELD-ISSUE-REPORT.md).
2. Include source links, vehicle, software/fork/version, scenario and outcome. If you're unsure, report anyway.
3. The safety manager triages it within 2 business days (PROCESS §5.2).

## Current cases

| FI ID | Summary | Class | Status |
|---|---|---|---|
| [FI-2026-001](cases/FI-2026-001-nhtsa-pe26007/REPORT.md) | NHTSA PE26007: collisions with stopped/slow in-lane vehicles | A | RCA |
