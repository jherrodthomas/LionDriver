# Upstream watch list and review log

The record of the monthly upstream review of [WP-M-11](WP-M-11-upstream-and-supplier-management.md) §6: safety-relevant upstream changes (safety modes, the Toyota port, panda firmware, driver-monitoring policy) in the commit history of U-1…U-3, reverts of earlier fixes, and the monthly manual review of security advisories. Format and place decided by the lead on 2026-10-22 (decision register DQ-120, option A): one row per review, appended by pull request like every work product. A review that finds a change to take opens a sync change request (WP-P-02) with its impact analysis (WP-M-12 §7); the row names it.

## Watch list

What each review reads. The pins are those of [WP-P-01](../07-supporting/WP-P-01-configuration-management-plan.md); a review reads upstream from the last range it recorded below.

| ID | Upstream | Paths watched | Why |
|---|---|---|---|
| U-1 | commaai/openpilot | `selfdrive/selfdrived/`, `selfdrive/controls/`, `selfdrive/monitoring/`, `selfdrive/modeld/`, `selfdrive/pandad/`, `system/manager/` | Host safety behaviour, driver monitoring, process set (LionDriver keeps the uploader and athena off, DQ-121) |
| U-2 | commaai/opendbc | `opendbc/safety/`, `opendbc/car/toyota/`, `opendbc/car/interfaces.py`, `opendbc/car/lateral.py` | The envelope and the reference car port |
| U-3 | commaai/panda | `board/` | Safety MCU firmware |
| — | Security advisories of U-1…U-7, U-10 | GitHub security advisories and security-labelled fixes | Monthly manual review next to the weekly automated watch (WP-W-11 SCAN-04) |

## Review log

| Date | Reviewer | Upstream ranges read | Safety-relevant changes found | Reverts | Advisories | Outcome (sync, defer, change record) |
|---|---|---|---|---|---|---|
| — | — | — | No review recorded yet; the first one is due in the month after this file was created (2026-11) | — | — | — |
