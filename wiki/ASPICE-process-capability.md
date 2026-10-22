# ASPICE: is the process capable?

The safety and security standards ask whether the product is safe. Automotive SPICE (ASPICE) asks a different
question: is the way the product is built good enough to trust what comes out of it? This page explains ASPICE from
the start for someone who has never used it, with LionDriver's own self-assessment. It explains and links. The
ratings are in [WP-M-13](../assurance/01-management/WP-M-13-aspice-capability-baseline.md), the traceability in
[WP-T-01](../assurance/trace/maps/aspice-trace-map.md) and the process model in
[WP-P-11](../assurance/process/README.md); nothing here is a rating.

> [!NOTE]
> WP-M-13 is a self-assessment, not a formal ASPICE assessment. Its levels cannot be quoted as an ASPICE result.

Every figure is drawn at each wiki sync by [`tools/wiki/aspice_animations.py`](../tools/wiki/aspice_animations.py).
The levels, targets, improvement actions and coverage are read from the records, and every other phrase is checked
against its record. When a record changes, the build fails instead of showing old text.

## 0. A different question

![Animated: product against process; the capability levels 0 to 5 in plain words; LionDriver's targets and baseline](aspice-question.svg)

ASPICE rates each process on a **capability level**: 0 when it is not done or leaves nothing to show, 1 when it is
done and its outputs exist, 2 when it is also planned, tracked and its outputs reviewed and controlled, and higher
levels for a defined, measured and improving organisation.

## 1. The V: specify down, verify up

![Animated: the ASPICE V from SYS.1 down to SWE.3 and up from SWE.4 to VAL.1, each box with its LionDriver work product, and the processes around the V](aspice-v.svg)

## 2. How an assessor rates a process

![Animated: SWE.4 as the example: evidence found and missing, the N/P/L/F scale, the ratings, and what level 2 needs](aspice-rating.svg)

An assessor looks for evidence that each expected practice is performed and rates how fully: N (not), P (partly),
L (largely) or F (fully). Level 1 needs that rating to be L or F. Level 2 also needs the process to be managed: planned,
tracked, and its work products reviewed and controlled.

## 3. Where LionDriver stands

![Animated: every process in scope with its level today and its target, and where evidence has moved since the baseline](aspice-baseline.svg)

## 4. Traceability: every link both ways

![Animated: one chain from a safety goal to a software requirement and the test that names it, then the derivation and verification coverage of the trace map](aspice-trace.svg)

Every requirement should come from a parent, be checked by a test, and every test should name a requirement that
exists. The trace map counts this from the data; the open part is the link from a test to its result
([Building a fault tree](Building-a-fault-tree.md) and [From hazard to test](From-hazard-to-test.md) show the same chain
from the safety side).

## 5. ASPICE and ISO 26262 together

![Animated: ISO 26262 parts beside the ASPICE processes they line up with, what only each covers, and LionDriver's single process model](aspice-together.svg)

ISO 26262 says which work products must exist and how rigorous they must be; ASPICE says how well the process that
makes them runs. LionDriver keeps one process model for all of it, so a work product is written once and counted
wherever it applies.

## 6. Getting to the target

![Animated: the improvement actions with their processes, the self-assessment at each gate, and what moves a process up a level](aspice-plan.svg)

## See also

- [Standards at a glance](Standards-at-a-glance.md): how the standards divide the work.
- [How decisions are made](How-decisions-are-made.md): where the lead's decisions are recorded.
- [Glossary](Glossary.md) for the work product and ID codes.
