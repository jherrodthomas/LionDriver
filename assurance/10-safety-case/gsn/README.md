# Safety case diagrams (GSN)

Generated from the case records in [`assurance/case/`](../../case/README.md) and the contexts of [WP-K-01](../WP-K-01-safety-case.md) by `assurance/case/tools/gsn_diagrams.py`. WP-K-01 stays the reviewed document; edit it or the records and regenerate (CI runs `--check`).

| Sheet | Argument from | Goals | Solutions |
|---|---|---|---|
| [1](gsn-1-G0.svg) | G0 | 6 | 5 |
| [2](gsn-2-G1.svg) | G1 | 11 | 33 |
| [3](gsn-3-G1.1.svg) | G1.1 | 5 | 10 |
| [4](gsn-4-G2.svg) | G2 | 5 | 9 |
| [5](gsn-5-G3.svg) | G3 | 6 | 8 |
| [6](gsn-6-G5.svg) | G5 | 8 | 14 |

Notation: goal = rectangle; strategy = parallelogram; solution = circle (green available, amber partial, white dashed missing); context = rounded box; assumption / justification = oval (A / J); diamond = undeveloped goal. Solid arrows are SupportedBy, hollow arrows InContextOf. Defeaters (open counter-evidence, WP-K-01 §7) are listed in red on the goal they undermine.
