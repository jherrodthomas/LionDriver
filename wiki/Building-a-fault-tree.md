# Building a fault tree

How to build a qualitative fault tree (FTA) for a LionDriver safety goal, starting from the item diagram, and how to
use the tree to check the safety requirements. This page is for someone who has never built one. It explains and
links. The trees themselves, their cut sets and their findings live in
[WP-A-04](../assurance/08-analyses/WP-A-04-system-fta-fmea.md); nothing here is analysis content.

Every figure on this page is drawn at each wiki sync by
[`tools/wiki/fta_animations.py`](../tools/wiki/fta_animations.py). Each ID, cut set, order and commit it draws is
checked against WP-A-04, the item definition and the TSC, and the build fails if one is no longer there. The trees
are simplified to teach the method; WP-A-04 is the record.

## 1. What a fault tree is for

A fault tree starts from one thing that must not happen, the violation of a safety goal, and asks "what could cause
this?" until it reaches single failures. The answer is a list of **minimal cut sets**: the smallest combinations of
failures that cause the top event. A cut set with one failure is a single point of failure. A cut set with two
failures that are independent is far less likely, which is what a safety mechanism buys.

WP-A-04 numbers everything by safety goal: for SG-02 the top event is TE-02, basic events are BE-2.nn,
undeveloped events (outside the item) UE-2.nn, gates G2.n, and minimal cut sets MCS-02.n.

"Qualitative" means no failure rates: the output is the cut sets and their order (how many failures each needs), not
a probability. Rates come later from the FMEDA.

In this repository:

| What | Where |
|---|---|
| The trees, as indented text, one per safety goal, with the cut-set tables | [WP-A-04](../assurance/08-analyses/WP-A-04-system-fta-fmea.md) |
| The same trees drawn as diagrams (generated) | [`fta/`](../assurance/08-analyses/fta/README.md) |
| The cut sets computed from the trees, checked against the tables (generated) | [cut-sets.md](../assurance/08-analyses/fta/cut-sets.md) |
| A cross-check of the SG-02 tree by fault propagation in a model (fmdtools) | [`models/fmdtools/sg02/`](../assurance/models/fmdtools/sg02/) |
| Every basic event linked to its FMEA rows | [fta-fmea-mapping.md](../assurance/08-analyses/fta-fmea-mapping.md) |

## 2. The symbols

![Fault tree symbols: top event, intermediate event, OR gate, AND gate, basic event (circle), undeveloped event (diamond), transfer (triangle) and minimal cut set, each with an SG-02 example](fta-symbols.svg)

*The symbols of IEC 61025, drawn by the same code that draws the WP-A-04 diagrams, so they look the same there.*

## 3. From the item diagram to a tree

![Animated: the item boundary diagram reduced to eight blocks; the SG-02 top event; the control path traced back from the EPS and the two warning paths; OR over each block's failures, AND over the two warning channels; the cut sets MCS-02.5 and MCS-02.1 and the requirements that break them](fta-item-to-tree.svg)

*SG-02 built in seven steps from the item boundary diagram. Reduced to eight blocks and three causes; the full tree
in WP-A-04 has more of each.*

1. **Start from the item boundary diagram**
   ([WP-C-01 Figure 3-2](../assurance/02-concept/WP-C-01-item-definition.md)). It shows every element inside the
   item, everything outside it, and the interfaces between them. A tree built from it cannot forget a block.
2. **Pick one safety goal and write its top event.** Make it a state you could observe: "steering lost and the driver
   not warned within 1 s" (TE-02), not "the system is unsafe".
3. **Trace the function back from the actuator.** Start at the block that acts on the vehicle (here the EPS) and walk
   the arrows backwards to the sensors. Then do the same for each path that warns the driver.
4. **For each block on the path, ask how it can fail:** no or wrong input, a fault inside, no or wrong output. Any one
   of them breaks the chain, so they go under an **OR**. This is the method of the FSC completeness check
   ([WP-C-04 §14](../assurance/02-concept/WP-C-04-functional-safety-concept.md)), which does it for every node of the
   item.
5. **Where a second, independent channel covers the same failure, use an AND.** The panda siren warns the driver
   without the SoC, so the warning is lost only if the SoC alert *and* the siren both fail.
6. **Read off the minimal cut sets.** Pick one input of every OR and all inputs of every AND, then drop any set that
   contains a smaller one. [`fta_cutsets.py`](../assurance/08-analyses/fta/fta_cutsets.py) does this for every tree.
7. **Check every cut set against the requirements** (section 6).

WP-A-04 writes the same logic one branch per cause: each cause of lost steering is ANDed with the failure of the SoC
warning *for that cause* and the failure of the siren. That form is longer, but it shows what step 5 hides: which SoC
warning fails depends on the cause.

## 4. AND or OR?

![Animated: one umbrella, torn or forgotten, either alone gets you wet, an OR gate; an umbrella under an awning, both must fail, an AND gate; then the same question in SG-02](fta-and-or.svg)

*One question decides every gate: if this input fails alone, does the event above happen? Yes, it is an OR. No,
because something else still covers it, it is an AND.*

An AND is only as good as the independence of its inputs. Two channels that share a power supply, a chip or a piece of
software can fail together, and then the AND is really an OR. That is the first trap below.

## 5. Two traps

![Animated: trap 1, a common cause counted twice, the order 3 cut set as drawn is in fact order 2 (MCS-02.5); trap 2, a latent failure, BE-2.14, makes the effective order 1](fta-traps.svg)

*Both traps make a tree look safer than it is, and both were found in the SG-02 tree.*

- **A common cause counted twice.** A SoC that stalls also cannot raise its own alert. Drawn as two separate events,
  {SoC stalls, SoC alert fails, siren fails} looks like order 3; it is in fact {SoC stalls, siren fails}, order 2.
  Use the same event ID wherever the same failure appears (the tools treat it as one variable) and tag shared causes
  for the [dependent failure analysis](../assurance/08-analyses/WP-A-03-dependent-failure-analysis.md).
- **A latent failure.** A failure that is already present and that nothing reveals does not count as a second
  failure. At the baseline the panda sounded the siren for a SoC stall only after 5 s, past the 1 s budget, so the
  siren branch was already failed and the cut set was effectively order 1. WP-A-04 tags such events latent and gives
  each cut set an *effective* order. The cures are a check that reveals the latent failure, or a design change that
  removes it.

## 6. Using the tree to check the requirements

A requirement is there to break a cut set: to make sure that one of its failures cannot happen, or is caught before
the top event. That gives two checks in each direction.

| Check | What it finds | Where it is done |
|---|---|---|
| Every cut set has a requirement that breaks it, or a recorded reason | A **missing requirement** | The cut-set tables of WP-A-04 name the TSRs for each row |
| Every requirement breaks at least one cut set | A requirement that **may not be needed**, or a branch missing from the tree | The FSC completeness check and the [coverage table](../assurance/02-concept/fsc/fsc-coverage.md) |
| Every cut set's order holds when its failures are injected | A **wrong tree**: the system fails with fewer failures than the tree says | The [fmdtools sweep of SG-02](../assurance/models/fmdtools/sg02/), and the plant runs of the simulation |
| The requirement that breaks the cut set holds when its failures are injected | A requirement that **does not work** as written | Fault-injection tests (VS-FI) and HIL timing, with FRET monitors where they exist |

The first check is the most useful one for a beginner: go down the cut-set table of a goal and look for a row with
no requirement, or with a requirement that only partly covers it. In SG-02, MCS-02.12 (insufficient lateral control)
has no siren trigger at all, and is argued as a single point instead.

## 7. Is my tree done?

- The top event is one observable state, with the goal's time budget.
- Every block on the function's path in the item diagram has been asked for input, process and output failures, or
  the tree says why it cannot violate this goal.
- Every safety mechanism appears under an AND with the failure it covers, and is independent of it, or the shared
  cause is tagged.
- The same failure has the same ID wherever it appears.
- Latent events are tagged, and the cut-set table gives an effective order where one is present.
- Events outside the item (vehicle, driver, road) are undeveloped events (diamonds), with the assumption of use that
  covers them.
- Every cut set names the requirement that breaks it, or a recorded reason.
- The tools agree:

```sh
python3 assurance/08-analyses/fta/fta_cutsets.py      # recompute the cut sets, compare with the tables
python3 assurance/08-analyses/fta/fta_diagrams.py     # redraw the diagrams
python3 assurance/02-concept/fsc/fsc_model.py --check # every node and goal still covered
```

## See also

- [Deriving and writing safety requirements](Deriving-and-writing-safety-requirements.md): the fault tree is the
  first of its six derivation routes.
- [Glossary](Glossary.md) for the work product and requirement codes.
