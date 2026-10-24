# ASIL decomposition: what it is and what it isn't

ASIL decomposition is one of the most misread ideas in ISO 26262. This page explains, from the start, what it is,
what it is not, how it is used, and what LionDriver decided. It explains and links. The record is the
[ASIL decomposition rationale, WP-A-01](../assurance/08-analyses/WP-A-01-asil-decomposition.md); the independence it
depends on is shown in the [dependent failure analysis, WP-A-03](../assurance/08-analyses/WP-A-03-dependent-failure-analysis.md),
and the hardware metrics that may trigger it are in [WP-H-04](../assurance/04-hardware/WP-H-04-hardware-metrics.md).

**In short: LionDriver uses no decomposition today.** The panda envelope is built to ASIL C as one element. One
fallback is prepared in case it cannot meet the ASIL C hardware metrics on its own.

Every figure is drawn at each wiki sync by [`tools/wiki/dec_animations.py`](../tools/wiki/dec_animations.py). The
decision, the independence requirements, the scheme records and the hardware-metric gap are read from WP-A-01 and
WP-H-04, and every phrase drawn from a record is checked against it. The definitions and the allowed splits (figures
1 to 3) come from ISO 26262-9:2018 clause 5, which is not in the repository, so they are not checked by the build.

## 1. The idea

![Animated: one ASIL C requirement met by one ASIL C element, then by two independent elements B(C) and A(C), each meeting it alone, so that one failing is caught by the other](dec-idea.svg)

A **safety requirement** inherits its ASIL from the safety goal it serves. Decomposition meets that requirement with
two **redundant** elements, each of which satisfies the whole requirement on its own, and lets each be developed to a
lower ASIL. The notation keeps both: **B(C)** is an element developed to ASIL B for a goal that stays ASIL C.

## 2. What it is not

![Animated: five misreadings of ASIL decomposition, each struck through and corrected](dec-myths.svg)

Most mistakes come from reading decomposition as a discount. It is a trade: less rigour per element in exchange for
redundancy you have to prove is real. The project's own notations **B‡** and **QM (C-sup)**
([WP-S-02 §2.1](../assurance/03-system/WP-S-02-technical-safety-requirements.md)) are not decompositions; they record
a target that may still change and a QM function backed by a panda requirement.

On hardware metrics, WP-A-01 §4.4 records that they stay at the original ASIL and marks this to be checked against the
licensed text of the standard (its OI-4).

## 3. The splits the standard allows

![Animated: ASIL D, C, B and A with each decomposition ISO 26262-9 allows, as bars that add up to the original ASIL](dec-schemes.svg)

The two letters of a split always add up to the original ASIL. A split with **QM** means one element carries the whole
ASIL and the other is not relied on for the requirement.

## 4. How to use it

1. **Check it is needed.** Decomposition is a fallback for when one element cannot reach the ASIL, not a default.
2. **Find two elements that each meet the whole requirement.** If either only does part, it is not decomposition.
3. **Show they are independent.** A dependent failure analysis must find nothing that can make both fail together:
   power, clock, board, inputs, code, toolchain or one configuring the other.
4. **Keep the rest at the original ASIL.** Integration, verification of the safety goal and confirmation measures do
   not drop.
5. **Record it.** WP-A-01 §6 has the template: scheme, both elements, the redundancy argument, the independence
   requirements, the DFA and the confirmation review.

![Animated: what the panda envelope shares on the comma device, the independence requirements, and the own resources they give the fallback monitor E-07; the relay stays shared](dec-independence.svg)

The figure is step 3 for LionDriver's fallback: the second element, a monitor called **E-07**, only counts if it
shares none of what the panda shares on the comma device. Nothing of E-07 is built.

## 5. LionDriver's decision

![Animated: the envelope hardened to ASIL C with no decomposition; the hardware-metric question that decides; the four candidate schemes and their status](dec-liondriver.svg)

The steering, braking and warning goals SG-02, SG-03 and SG-06 are ASIL C, so the panda envelope has to be ASIL C.
The lead chose to harden it as one element. Whether that holds depends on the hardware metrics, and today's estimate
is just short of the target. If the gap is not closed by G2, the question comes back to the lead with DEC-01 ready.
The other three schemes fail the test of step 2 or step 3.

## See also

- [Hardware safety and interference](Hardware-safety-and-interference.md): the hardware metrics and freedom from
  interference that this decision depends on.
- [How LionDriver works](How-LionDriver-works.md): the panda envelope in the product.
- [Deriving and writing safety requirements](Deriving-and-writing-safety-requirements.md): where the ASIL of a
  requirement comes from.
- [Glossary](Glossary.md) for the ID codes.
