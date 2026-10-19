# SOTIF figure generator

This folder holds the generator for the triggering-condition chain in [WP-C-06](../WP-C-06-sotif-insufficiencies-triggering-conditions.md) §5.

| File | What it is |
|---|---|
| [`sotif_figures.py`](sotif_figures.py) | Generator. It reads the WP-C-06 tables (§3 functional insufficiencies, §4 triggering conditions, §5 evaluation) and the WP-C-05 §3 hazard table, then writes Figure 5-1 of WP-C-06 |
| [`sotif_scenes.py`](sotif_scenes.py) | Draws the SOTIF scene sheet: one card per SOTIF hazard of WP-C-05 §3, each the chart of one WP-C-06 §5 row (triggering condition → insufficiency → hazard) over a top-down scene. Texts, S/C and evaluations come from the documents; the behaviour curves are schematic and live in this file. Written and checked by `sotif_figures.py` |
| [`test_sotif_scenes.py`](test_sotif_scenes.py) | Unit tests: one card per hazard, card texts and chips match WP-C-05/06, missing models and unlinked insufficiencies are rejected, every scene loops |
| [`test_sotif_figures.py`](test_sotif_figures.py) | Unit tests: the committed SVG is current, every TC and FI appears in the chain, and malformed tables are rejected |
| [`../figures/fig-c06-5-1-tc-fi-sh-chain.svg`](../figures/fig-c06-5-1-tc-fi-sh-chain.svg) | Generated. TC → FI edges come from §5, coloured by the row's evaluation outcome. FI → SH edges come from the "Linked SH" column of §3 |
| [`../figures/fig-c06-5-2-sotif-scenes.svg`](../figures/fig-c06-5-2-sotif-scenes.svg) | Generated. The SOTIF scene sheet (below) |

WP-C-05 and WP-C-06 are the analysis of record. Do not edit the SVGs by hand.

## SOTIF scenes

![Twelve looping cards, one per SOTIF hazard SH-01 to SH-13 (SH-07 is not used). Each shows a chart of what the situation needs, as a dashed green line, against what the car does, as a red line, over a top-down road scene in which a triggering condition such as a tar seam, an overhead gantry, a tight curve or a red light exposes an insufficiency of the intended function](../figures/fig-c06-5-2-sotif-scenes.svg)

*What each SOTIF hazard looks like on the road.* Nothing fails in these scenes: the system works as specified, and a triggering condition exposes an insufficiency. Each card draws one row of WP-C-06 §5 and lists the other triggering conditions that reach the same hazard. Two styles follow the class WP-C-06 §3 gives the insufficiency:

- **P, performance insufficiency** ("it sees it wrong"): the blue dashed layer is what the camera or radar believes, drawn over the true road. The chart sets that belief against what is true.
- **S, specification insufficiency** ("not enough as specified"): the chart sets what the situation needs against what the specification delivers, with the specified limit as a grey dashed line and the gap shaded.

The scenes are schematic, to explain each hazard; the measured cases are the plant runs in [assurance/sim §3.7](../../sim/README.md#37-the-asil-c-hazardous-events-in-the-loop). Each card loops in a browser; a viewer that shows the SVG as a still shows the last frame.

## Regenerating

```bash
python3 sotif_figures.py            # write ../figures/fig-c06-5-1-tc-fi-sh-chain.svg and fig-c06-5-2-sotif-scenes.svg
python3 sotif_figures.py --check    # fail if the committed SVG is stale (run in CI)
python3 test_sotif_figures.py
python3 test_sotif_scenes.py
```

The generator fails if:

- a §5 row names a TC or FI that §3/§4 do not define;
- a TC is not evaluated in §5, or is evaluated in more than one row;
- an FI is not activated by any §5 row;
- an evaluation outcome is not one of the three defined in WP-C-06 §1;
- an FI links to a hazard that WP-C-05 §3 does not define.

A §5 row that names a hazard which none of its FIs links to in §3 is printed as a warning. The figure follows §3. There is no such row at present.

The drawing helpers and the ASIL colour scale are shared with [`../hara/hara_figures.py`](../hara/hara_figures.py).
