# SOTIF figure generator

This folder holds the generator for the triggering-condition chain in [WP-C-06](../WP-C-06-sotif-insufficiencies-triggering-conditions.md) §5.

| File | What it is |
|---|---|
| [`sotif_figures.py`](sotif_figures.py) | Generator. It reads the WP-C-06 tables (§3 functional insufficiencies, §4 triggering conditions, §5 evaluation) and the WP-C-05 §3 hazard table, then writes Figure 5-1 of WP-C-06 |
| [`test_sotif_figures.py`](test_sotif_figures.py) | Unit tests: the committed SVG is current, every TC and FI appears in the chain, and malformed tables are rejected |
| [`../figures/fig-c06-5-1-tc-fi-sh-chain.svg`](../figures/fig-c06-5-1-tc-fi-sh-chain.svg) | Generated. TC → FI edges come from §5, coloured by the row's evaluation outcome. FI → SH edges come from the "Linked SH" column of §3 |

WP-C-05 and WP-C-06 are the analysis of record. Do not edit the SVG by hand.

## Regenerating

```bash
python3 sotif_figures.py            # write ../figures/fig-c06-5-1-tc-fi-sh-chain.svg
python3 sotif_figures.py --check    # fail if the committed SVG is stale (run in CI)
python3 test_sotif_figures.py
```

The generator fails if:

- a §5 row names a TC or FI that §3/§4 do not define;
- a TC is not evaluated in §5, or is evaluated in more than one row;
- an FI is not activated by any §5 row;
- an evaluation outcome is not one of the three defined in WP-C-06 §1;
- an FI links to a hazard that WP-C-05 §3 does not define.

A §5 row that names a hazard which none of its FIs links to in §3 is printed as a warning. The figure follows §3. The current warning is TC-33 → SH-03, where FI-10 links only to SH-06.

The drawing helpers and the ASIL colour scale are shared with [`../hara/hara_figures.py`](../hara/hara_figures.py).
