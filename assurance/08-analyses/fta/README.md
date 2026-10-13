# Fault tree diagrams

Generated from the text trees in [WP-A-04](../WP-A-04-system-fta-fmea.md) by `fta_diagrams.py`. WP-A-04 is the analysis of record; edit it and run `python3 fta_diagrams.py` (CI runs `--check`).

| Goal | Top event | Sheets |
|---|---|---|
| SG-01 | TE-01 uncontrollable lateral motion, or steering actuation while not engaged | [1: TE-01](fta-SG-01-1.svg), [2: G1.1](fta-SG-01-2.svg) |
| SG-02 | TE-02 loss or degradation of lateral control without adequate take-over warning | [1: TE-02](fta-SG-02-1.svg), [2: G2.1](fta-SG-02-2.svg), [3: G2.2](fta-SG-02-3.svg), [4: G2.3](fta-SG-02-4.svg) |
| SG-03 | TE-03 unintended acceleration | [1: TE-03](fta-SG-03-1.svg), [2: G3.1](fta-SG-03-2.svg) |
| SG-04 | TE-04 deceleration beyond what following traffic and the driver can control | [1: TE-04](fta-SG-04-1.svg), [2: G4.1](fta-SG-04-2.svg), [3: G4.6](fta-SG-04-3.svg) |
| SG-05 | TE-05 no release on driver brake, cancel or steering override | [1: TE-05](fta-SG-05-1.svg) |
| SG-06 | TE-06 loss of longitudinal deceleration without take-over warning | [1: TE-06](fta-SG-06-1.svg), [2: G6.1](fta-SG-06-2.svg), [3: G6.2](fta-SG-06-3.svg), [4: G6.4](fta-SG-06-4.svg) |
| SG-07 | TE-07 suppression, delay or alteration of the stock PCS/AEB | [1: TE-07](fta-SG-07-1.svg) |

Symbols follow IEC 61025: rectangle = top or intermediate event; OR / AND gate beneath it; circle = basic event; diamond = undeveloped event; triangle = transfer. Tags: SPF (single point in the baseline design), latent, SOTIF, CCF (→ WP-A-03 DFI), FFI (→ WP-A-02), repeated (event drawn again; defined where first shown).

Minimal cut sets computed from the same trees, and the check of the WP-A-04 tables: [cut-sets.md](cut-sets.md) (`fta_cutsets.py`).
