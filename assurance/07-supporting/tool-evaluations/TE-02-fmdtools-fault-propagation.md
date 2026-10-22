# TE-02 Tool evaluation and pilot plan — NASA fmdtools for fault-propagation models

| Field | Value |
|---|---|
| Purpose | Decide whether NASA fmdtools should run, headless and in CI, as an executable cross-check of the fault trees and FMEAs, and plan a pilot on SG-02 |
| Status | Draft. Started on the lead's go (2026-10-20): P0 to P4 done ([`assurance/models/fmdtools/`](../../models/fmdtools/README.md)); P5: the [Fault Lab page](../../models/fmdtools/sg02/fault-lab.html) and its CI check are done (DQ-409), the OI-4 note and the TL-49 confirmation remain. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Standard reference | ISO 26262-8:2018 §11 (tool classification), applied as in [WP-P-07](../WP-P-07-tool-classification-qualification.md) §2; ISO 26262-9:2018 §8 (safety analyses) |
| Date | 2026-10-20 |
| Baseline | `liondriver-dev` at `13ba1f4` (after #370) |
| Related | [WP-A-04](../../08-analyses/WP-A-04-system-fta-fmea.md) §4 (SG-02 tree), [cut sets](../../08-analyses/fta/cut-sets.md), [fta-fmea-map.yaml](../../08-analyses/fta-fmea-map.yaml), [simulation track](../../sim/README.md), [TE-01](TE-01-modelling-tools.md) |

## 1. Why

The fault trees and FMEAs are written by hand. The cut-set script checks that each tree is self-consistent and that its basic events map to FMEA causes. It cannot tell whether the tree misses a combination of faults that defeats the system. The simulation plant (layer 1) runs the real panda safety code, but only for the faults listed in `faults.yaml`, one at a time.

A fault-propagation model fills the gap between the two. It describes the SG-02 functions, the signals between them and every failure mode of the tree as code, then lets the tool inject every single fault and every combination up to a set order. The result is a list of the fault sets that actually produce the top event in the model. Comparing that list with the 100 hand-derived minimal cut sets of SG-02 gives two kinds of finding:

- **In the model, not in the tree:** a possible gap in the FTA.
- **In the tree, not in the model:** either the tree is conservative, or the model is missing a path. Either way, a reviewer looks at it.

Because the model also runs in time, it gives the time to the take-over warning for each fault set. That time can then be compared with the SG-02 budget (≤ 1 s to warning, WP-C-04) and with the WP-S-04 timing budget.

## 2. The tool

| Item | Finding |
|---|---|
| What | [nasa/fmdtools](https://github.com/nasa/fmdtools): a Python library for modelling systems as functions and flows with failure modes, then simulating nominal and faulty runs, single- and joint-fault sweeps, and FMEA-style tables |
| Version and licence | 2.5.6, Apache-2.0 (can be vendored or pinned). NASA software class E. Active: last commit 2026-10-16 |
| Runs headless | Yes. Checked on 2026-10-20 in a clean Python 3.13 virtual environment: installed from the source, ran the library's water-pump example single-fault sweep (27 results) in 0.8 s, no display needed |
| Defect found | It imports IPython (`analyze/graph/style.py`) without declaring it as a dependency. Our pin must add `ipython`, or we report it upstream |
| Python | Requires ≥ 3.12; the repository pins 3.12.13 (`.python-version`), so it fits |
| Other dependencies | scipy, numpy ≥ 2, pandas ≥ 2.2, networkx, matplotlib, graphviz, shapely, dill, `recordclass == 0.24` (an exact pin; check it installs on the CI image) |

The alternatives looked at on 2026-10-20 are FASTER, AsasBits-Studio and open-fmea. None of them does dynamic fault propagation.

## 3. Pilot scope: SG-02 only

SG-02: no loss or degradation of lateral control without an adequate take-over warning (ASIL C; warning within ≤ 1 s). It was chosen because:

- its tree is the largest computed so far, with 100 minimal cut sets;
- it holds the silent EPS failure the lead decided on 2026-10-18 (DQ-360 A, UE-2.19);
- its top event is a timing condition (warning within 1 s), which a static tree can't check and a time-stepped model can.

**Functions in the model**, one fmdtools Function each:
- perception and model input (`modelV2`, calibration);
- the lateral control law (`controlsd`);
- the engagement and alert logic (`selfdrived`);
- the host-to-panda link (`card`, `pandad`);
- the panda envelope;
- the harness relay and bus;
- the EPS;
- the HMI: UI render, audio, the panda siren, and the cluster cruise indicator;
- the 12 V supply;
- the driver.

**Flows:** the lateral command, the torque request frames, EPS status (`0x262`), the alerts, and power.

**Failure modes:** one Mode for each event of the tree, named by its ID: the basic events BE-2.01 … BE-2.25 and the borrowed BE-1.20 and BE-7.20. The undeveloped events UE-2.18 (driver does not notice) and UE-2.19 (EPS silently stops accepting requests) become driver and EPS modes too. A mapping file links each Mode to its event and, through `fta-fmea-map.yaml`, to its FMEA cause. A check fails CI if an event has no Mode or a Mode has no event.

P1 decision: two latent events are held as baseline design, not as modes. BE-2.11 (a non-finite command is never warned) and BE-2.16 (the cluster never changes) give 25 modes plus 2 latent entries. BE-2.14 (siren not triggered) stays a mode, because the reference build now sounds the siren on heartbeat loss and on a persisting EPS fault.

**Top event in the model:** lateral control is lost or degraded while engaged, and no perceivable take-over cue (UI alert, audio, siren or cluster change) reaches the driver within 1.0 s. It is evaluated from each run's history.

**Behaviour detail:** discrete time, 10 ms steps, a 10 s run at highway speed. Each behaviour is the simplest that reproduces the effect stated in the tree and the FMEA, for example "soft disable keeps actuating ≈3 s" for BE-2.10, or "`controlsMismatch` after ≈2 s" for BE-2.09. No vehicle physics: that stays in the plant model.

## 4. Steps

| Step | Work | Output | Done when |
|---|---|---|---|
| P0 Setup | Pin fmdtools 2.5.6 (plus `ipython`) in `assurance/models/fmdtools/requirements.txt`; add a CI job; enter the tool in WP-P-07 as TL-49 | Requirements file, CI job, TL-49 row | CI installs the library and runs an empty model |
| P1 Model | The SG-02 function architecture of §3, with one Mode per BE/UE and the mapping file | `assurance/models/fmdtools/sg02/` with model, mapping and tests | The nominal run raises no top event; each mode changes only its own function; the mapping check passes |
| P2 Single faults | Inject every mode alone, at 3 times (straight, curve entry, mid-curve) | A table of which single faults cause TE-02, and with what time to warning | Compared with the tree's order-1 effective sets (MCS-02.7 needs UE-2.18 too) |
| P3 Joint faults | Combinations of 2 to 4 of the 25 modes (15,250 sets; 6,297 run after pruning). One run takes about 0.19 s, so the sweep skips sets with no cause and supersets of sets already found. A scheduled job runs the full sweep; the pull-request job runs order 2 only | The minimal fault sets that cause TE-02 in the model | A diff against the 100 computed cut sets. Each difference is written up as a finding for the FTA owner, in the style of F-1…F-36 in `fta-fmea-mapping.md` |
| P4 Timing | Time to warning for every set that the model and the tree both list | A table and figure of the time to warning against 1.0 s, and against WP-S-04 | Every set over 1.0 s is named, with its cut-set row |
| P5 Report and CI | Generated report page, figure and `--check` (like the other generators); results marked synthetic | The pilot report, a decision note on extending to SG-01, SG-03 and SG-06, and the TL-49 class confirmed | CI fails if the report is stale or the model and tree drift apart |

P2 result (2026-10-20, [`p2-single-faults.md`](../../models/fmdtools/sg02/p2-single-faults.md)): the model agrees with the tree's single faults except BE-2.05 (the heartbeat siren covers it; BE-2.14 latent tag) and BE-2.07 on a straight (no torque to feel; an assumption for the plant to test). Both go to the FTA owner. A plant run with a steady lateral push (road crown or crosswind, 0.1–0.5 m/s²) crosses a 3.0 m lane line before the driver corrects, so the straight case is benign only with no push at all; the FTA owner takes it as an AOU-01R validation gap.

P3 result (2026-10-21, after panda `f4803c5`, [`p3-joint-faults.md`](../../models/fmdtools/sg02/p3-joint-faults.md)): 6,297 runs, 51 minimal sets. None of them is missing from the tree. In 10 of the tree's 31 effective sets the model needs a siren failure too, all for the BE-2.14 latent tag: the siren sounds on EPS faults and heartbeat loss (panda `8a69ccf`) and on the engaged-mismatch revocation after a selfdrived stop (`f4803c5`, TSR-307(a), TSR-516(c); [engaged-mismatch](../../sim/results/engaged-mismatch.md)). The diff caught a tree error injected on purpose (validation, §6).

P4 result (2026-10-21, [`p4-timing.md`](../../models/fmdtools/sg02/p4-timing.md)): of the 61 sets, 10 are warned within 1 s by the siren (tightest {BE-2.21}, 0.78 s after the loss), 9 late and 42 not within 6 s. The late ones all have a siren failure: MCS-02.9 (alert 4.9 s after the loss) and MCS-02.1 and MCS-02.11 (escalated take-over 1.5 s, TSR-607 (b)). Every set over 1.0 s is named with its cut-set row.

Effort: about one working session each for P0 and P2, and two for P1. P3 to P5 together take two to three sessions.

## 5. What the pilot is not

- **Not evidence.** Like the simulation track, the results are synthetic (DSR-12). They rank risks and point reviewers at possible gaps; they earn no evidence credit. A finding changes the FTA only after a person reviews it.
- **Not a replacement for the FTA.** The hand-written tree stays the work product. The model checks it.
- **Not physics.** Vehicle dynamics, torque and lateral error stay in the plant model (`assurance/sim/plant/`). If a mode needs a physical effect, the model takes it from a plant run as a stated number.

## 6. Tool classification (proposed, for WP-P-07)

**TI1 while no credit is claimed.** A tool error can only hide a gap that the hand-written tree already has, and the tree's own review is unchanged. That makes it TCL1, with no qualification needed. Validation still follows the WP-P-07 TL-06 pattern: the pilot's tests include known cases, at least one injected tree error that the diff must catch, and the library's own test suite run once on the pinned version.

If results are ever credited, for example "the model confirms the tree is complete", the tool becomes TI2. It then needs the qualification route of TL-45 (validation against reference cases), decided at that point.

## 7. Owners and coordination

| Who | Role |
|---|---|
| FTA owner session | Receives the diff findings; owns any change to WP-A-04 and the cut sets |
| Simulation session | Owns the plant model. Checks that no mode duplicates a `faults.yaml` case, and supplies plant numbers when a mode needs one |
| SW FMEA, System FMEA and hardware sessions | Receive findings that touch FMEA causes or effects |
| Coordinator | Runs P0 and P1, keeps TL-49 and this plan current, merges on full green |

## 8. Open items

| ID | Item |
|---|---|
| OI-1 | ~~Lead's "go" to start P0~~ **Closed** 2026-10-20 (go given) |
| OI-2 | Report the undeclared IPython import upstream (nasa/fmdtools), or keep `ipython` in our pin |
| OI-3 | Confirm `recordclass == 0.24` builds on the CI runner image |
| OI-4 | After P5: extend to SG-01 (hard-over), SG-03 and SG-06, or stop. Decided on what the SG-02 diff finds. **Decided (DQ-417, 2026-10-22): all three, in the order SG-06, SG-01, SG-03**, each with steps P1 to P4 and its own Fault Lab page |
