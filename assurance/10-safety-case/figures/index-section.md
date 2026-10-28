## Living Safety Case records

The safety case lives in two folders on purpose. This folder holds the reviewed documents (WP-K-01 to WP-K-06), the GSN
diagrams, gate records and confirmation records. [`assurance/case-records/`](../../case-records/README.md) holds the same safety case as
machine-readable records (claims, evidence, defeaters, actions, configurations, reviews), the validator that checks them
against WP-K-01, and the generators that draw the dashboard, the README status strip and the diagrams in [`gsn/`](../gsn/README.md).
Edit WP-K-01 and the records together; the validator fails if they disagree.
