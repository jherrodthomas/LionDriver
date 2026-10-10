# Gate records

Gate review records for gates G0…G6, as required by [WP-M-02 §10](../../01-management/WP-M-02-safety-plan.md#10-progress-tracking-and-gate-reviews). Gates and their exit criteria are defined in [WP-M-00 §2](../../01-management/WP-M-00-work-product-register.md#2-gates).

No gate review has been held yet.

## File naming

`G<n>-<YYYY-MM-DD>.md`, one file per gate review. A repeated review of the same gate gets a new file.

## Template

```markdown
# G<n> gate review — <gate name>

| Field | Value |
|---|---|
| Gate | G<n> <name> |
| Date | YYYY-MM-DD |
| Baseline | <commit SHA or tag> |
| Chair | Safety manager |
| Participants | Name — role |
| Assessor informed | Yes / No (name) |

## Inputs (WP-M-02 §10)

| Input | Status at this baseline | Link |
|---|---|---|
| WP-M-00 status of the gate's work products | | |
| Open anomalies (`safety-anomaly`), incl. any potential safety goal violation | | |
| Open risks (WP-M-07) | | |
| Confirmation measures assigned to this gate (WP-M-06) and their results | | |
| QA findings (WP-M-05) | | |
| Open items of the phase's work products | | |

## Exit criteria (WP-M-00 §2)

| Criterion | Met? | Evidence |
|---|---|---|

## Outcome

- [ ] Pass  - [ ] Pass with conditions  - [ ] Fail

| Condition | Owner | Due gate | Issue |
|---|---|---|---|

Deferrals of confirmation measures (agreed by safety manager and assessor), with rationale:

Signature / approving GitHub review link:
```
