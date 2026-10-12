# Confirmation measure records

Records of confirmation reviews (CR-01…CR-12), SOTIF reviews (SR-01…SR-03), functional safety audits (`AUD-<n>.md`) and interim functional safety assessments (`FSA-I1.md`, `FSA-I2.md`), as planned in [WP-M-06](../../01-management/WP-M-06-confirmation-measures-plan.md). The final assessment report is [WP-K-04](../WP-K-04-functional-safety-assessment.md).

No confirmation measure has been performed yet.

## Rules

- Records use the review record template of [WP-P-05 §7.2](../../07-supporting/WP-P-05-verification-review-procedure.md#72-review-record-template-r3-inspections-confirmation-reviews-reviews-outside-github) with review type `confirmation`, `audit` or `assessment`.
- Each record is written by the named reviewer, auditor or assessor at the independence level WP-M-06 requires, and states that independence in writing (WP-M-06 §6.1).
- Author-side self-checks and AI-generated pre-review audits (for example [RR-2026-001](../../02-concept/reviews/RR-2026-001.md), [RR-2026-002](../../01-management/reviews/RR-2026-002.md)) are inputs to a confirmation measure. They are never stored here and never count as one.
- An accepted confirmation review is also entered in [`case/reviews/reviews.yaml`](../../case/reviews/reviews.yaml) so the Living Safety Case can reference it.

## File naming

| Measure | File |
|---|---|
| Confirmation review | `CR-<nn>-<WP-ID>-v<version>.md` (WP-M-06 §4.2 step 5), e.g. `CR-02-WP-C-03-v1.0.md` |
| SOTIF review | `SR-<nn>.md` (WP-M-06 §7) |
| Functional safety audit | `AUD-<n>.md` |
| Interim functional safety assessment | `FSA-I1.md`, `FSA-I2.md` |
