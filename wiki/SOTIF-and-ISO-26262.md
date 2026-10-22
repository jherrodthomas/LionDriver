# SOTIF and ISO 26262

ISO 26262 asks what happens when something in the system breaks. ISO 21448, SOTIF (safety of the intended
functionality), asks what happens when nothing breaks but the system still gets it wrong. LionDriver needs both:
openpilot's parts rarely fail, but its driving model often misjudges. This page explains SOTIF from the start for
someone who has never used it, and shows how it shares work with ISO 26262. It explains and links. The analysis is in
[WP-C-05](../assurance/02-concept/WP-C-05-sotif-hazard-identification.md),
[WP-C-06](../assurance/02-concept/WP-C-06-sotif-insufficiencies-triggering-conditions.md) and
[WP-C-07](../assurance/02-concept/WP-C-07-sotif-functional-modifications.md), and the validation in
[WP-V-02](../assurance/06-validation/WP-V-02-sotif-vv-strategy.md),
[WP-V-03](../assurance/06-validation/WP-V-03-sotif-known-scenarios.md) and
[WP-V-04](../assurance/06-validation/WP-V-04-sotif-unknown-scenarios.md); nothing here is analysis content.

Every figure is drawn at each wiki sync by [`tools/wiki/sotif_animations.py`](../tools/wiki/sotif_animations.py).
Each ID, rating, status and number it draws is checked against the record it comes from, and the counts are computed
from the WP-C-05 and WP-C-06 tables. When a record changes, the build fails instead of showing old text.

## 0. Two questions about the same swerve

![Animated: the car steers out of its lane; from a fault, a software bug sending torque while not engaged, rated ASIL C under SG-01; and from a model error, a tar seam taken for a lane line, SH-01, with no ASIL; both one entry of the hazard log](sotif-two-questions.svg)

The same thing can happen for two reasons. A **malfunction** is ISO 26262's business: a part fails, and the cure is
to detect and contain the fault. A **functional insufficiency** is SOTIF's: every part works as designed, but the
design or its performance is not good enough for the situation, and the cure is to improve the function, restrict
where it may be used, or show by validation that the risk is acceptable.

## 1. Which standard handles this cause?

![Animated: two questions, did a part fail and does the intended function fall short or is it misused, sort four causes into ISO 26262, SOTIF or both](sotif-who-owns.svg)

LionDriver keeps **one hazard log** ([WP-C-03 §7](../assurance/02-concept/WP-C-03-hara.md#7-hazard-log-cross-references)).
A SOTIF hazard SH-0x has the same number as the HARA hazard H-0x with the same effect on the vehicle, and reuses its
severity and controllability ratings. Only ISO 26262 turns them into an ASIL; SOTIF records exposure only to set
validation targets. Some causes belong to both: a performance limit that a safety goal's fault tree also carries,
and the driver who stops watching, which is foreseeable misuse in SOTIF and a rated entry in the HARA. Attacks belong
to ISO/SAE 21434 and its TARA ([WP-C-09](../assurance/02-concept/WP-C-09-tara.md)), in the same log; see
[Cybersecurity and ISO/SAE 21434](Cybersecurity-and-ISO-21434.md).

## 2. How a working system still gets it wrong

![Animated: low sun (TC-01) exposes degraded perception (FI-02) and leads to SH-01 or SH-02, needs validation; a curve too tight (TC-14) exposes the steering torque cap (FI-11) and leads to SH-02, needs modification; the count of evaluation outcomes in WP-C-06](sotif-triggering.svg)

A **triggering condition** (TC) is something in the world the function cannot cope with. It exposes a **functional
insufficiency** (FI): of performance (P), when the design is right but a part is not good enough there, or of the
specification (S), when the design itself is wrong there. The result is a **hazardous behaviour** (SH), harmful only
if the driver does not step in. WP-C-06 evaluates each chain: acceptable, needs modification
([WP-C-07](../assurance/02-concept/WP-C-07-sotif-functional-modifications.md) or an ODD restriction), or needs
validation ([WP-V-03](../assurance/06-validation/WP-V-03-sotif-known-scenarios.md)).

## 3. The goal: shrink what is unsafe

![Animated: the four areas of ISO 21448; analysis moves hazardous situations from unknown to known, changes make known ones safe, exploration finds more; LionDriver today](sotif-four-areas.svg)

Every situation is known or unknown to us, and hazardous or not. SOTIF work moves situations out of area 3 (unknown,
hazardous) into area 2 (known, hazardous) by analysis and exploration, and out of area 2 into area 1 (known, not
hazardous) by modifying the function, restricting the ODD or informing the user. The record version is
[WP-C-05 Figure 2-1](../assurance/02-concept/WP-C-05-sotif-hazard-identification.md#2-method).

## 4. How much driving would prove it?

![Animated: from the human injury-crash rate to an allowed rate of wrong lane departures, the miles a zero-failure demonstration needs against what LionDriver can drive in a year, and the split into per-scenario targets](sotif-how-much.svg)

The acceptance criterion is "no worse than a human driving the stock car". Turned into a rate of hazardous behaviour
and a demonstration with no failure at 95 % confidence, it needs far more driving than one test car can do. So
[WP-V-02](../assurance/06-validation/WP-V-02-sotif-vv-strategy.md) splits it into scenarios, each tested many times
in simulation, on a closed course and in replay, and states in the release argument
([WP-K-02](../assurance/10-safety-case/WP-K-02-sotif-release-argument.md)) what this does not show.

## 5. Hunting for what we do not know yet

![Animated: seven search methods aimed at the unknown area, the four triage classes, a discovery curve that flattens over the blocks, and the stop rule](sotif-unknowns.svg)

Area 3 cannot be listed, only searched. [WP-V-04](../assurance/06-validation/WP-V-04-sotif-unknown-scenarios.md) sets
the search methods, the triage of every odd event (a malfunction found there goes to the ISO 26262 side), and the
rule that says when to stop: new kinds of trouble must stop turning up.

## 6. One requirement, two standards

![Animated: a fault and a model error both answered by FSR-01.01, the steering torque cap; its design in the panda, its controllability test, and the two claims of the safety case it supports](sotif-one-chain.svg)

The two standards meet in the safety envelope. The torque cap that contains a fault also bounds whatever the model
gets wrong, so one controllability test supports a claim on each side of the safety case
([What is a safety case?](What-is-a-safety-case.md)). That is why a gap in it counts twice. The ISO 26262 chain of
the same requirement is followed on [From hazard to test](From-hazard-to-test.md).

## See also

- [Standards at a glance](Standards-at-a-glance.md): how the standards divide the work.
- [Building a fault tree](Building-a-fault-tree.md): performance limits marked [SOTIF] in the SG-02 tree.
- [Glossary](Glossary.md) for the work product and ID codes.
