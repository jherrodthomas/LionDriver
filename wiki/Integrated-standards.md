# Integrated standards: one system, not five

LionDriver answers to five standards: ISO 26262 (functional safety), ISO 21448 (SOTIF), ISO/SAE 21434
(cybersecurity), ISO/PAS 8800 (AI safety) and Automotive SPICE (process capability). Many organisations run each
one as its own project, with its own team, documents and report. This page explains, from the start, why LionDriver
runs them as one system instead, and how you can see that in its records. It explains and links. The lifecycle is in
the process model ([WP-P-11](../assurance/process/README.md)), the work products in the
[register, WP-M-00](../assurance/01-management/WP-M-00-work-product-register.md), the hazard log in the
[HARA, WP-C-03](../assurance/02-concept/WP-C-03-hara.md) §7 and the case in [`assurance/case-records/`](../assurance/case-records/README.md).

Every figure is drawn at each wiki sync by [`tools/wiki/integrated_animations.py`](../tools/wiki/integrated_animations.py).
The lane and interface counts, the register coverage, the hazard log, the trace lanes and the case status are read
from the records, and every other phrase is checked against its record. When a record changes, the build fails
instead of showing old text.

## 0. Silos or one system?

![Animated: five standards as silos, each with its own hazards, requirements, tests and report; the same swerve analysed three times; problems falling between the silos; then one lifecycle with a lane per discipline](integrated-silos.svg)

In silos, the same hazard is found three times under three names, and a problem that belongs to two standards can be
found twice or not at all. Integrated does not mean merged: each standard keeps its own questions, methods and
assessor. It means one lifecycle, shared items and checked joins.

## 1. Where the standards meet

![Animated: the cross-domain interfaces of the process model by pair of disciplines, their status, and three examples](integrated-joins.svg)

An **interface** is a point where one discipline's work depends on another's result: the TARA rates safety impact
against the HARA's hazards, for example. Each interface names the two work products and quotes text from both, so the
model cannot claim a link the documents do not make. These are different from the safety–security interactions in
[`hatara/`](../assurance/02-concept/hatara/README.md), which ask whether a measure for one helps or hurts the other.

## 2. One work product, many standards

![Animated: every work product of the register against the standards it serves, with the count per standard](integrated-coverage.svg)

Each row of the register names every standard the work product serves. A work product written once is counted
wherever it applies; an empty stretch shows where a standard has no work product of its own.

## 3. One hazard log, one trace

![Animated: each hazard with its SOTIF hazard and the TARA damage scenarios that reach it, checked against the TARA; then the trace lanes per standard](integrated-log.svg)

The HARA keeps one row per vehicle-level hazard with the SOTIF hazards and the cyber attacks that lead to it. The
figure checks that row against the TARA's own damage scenarios and flags any hazard the TARA reaches but the log
does not name. Below it, the trace: a solid lane is in the trace data and checked by CI; a dashed one is linked in its work-product tables only ([From hazard to test](From-hazard-to-test.md) follows
one chain).

## 4. One mechanism, five standards

![Animated: the panda safety envelope and what each standard asks of it, and what is still open in it](integrated-mechanism.svg)

The safety envelope on the panda is where the standards meet in the product. Each asks something different of it,
but it is built, verified and cited once. A gap in it is therefore a gap in every case at once.

## 5. One assurance case

![Animated: one top claim with a branch per standard, evidence shared between branches, defeaters, and the status today](integrated-case.svg)

One top claim, one branch per standard, each argued its own way. Evidence can hold up claims in two branches, and
recorded doubts (defeaters) point at the claims they weaken, wherever those sit. [What is a safety case?](What-is-a-safety-case.md)
shows how a case is read.

## See also

- [Standards at a glance](Standards-at-a-glance.md): how the standards divide the work.
- [SOTIF and ISO 26262](SOTIF-and-ISO-26262.md), [Cybersecurity and ISO/SAE 21434](Cybersecurity-and-ISO-21434.md),
  [AI safety and ISO/PAS 8800](AI-safety-and-ISO-PAS-8800.md) and [ASPICE: is the process capable?](ASPICE-process-capability.md):
  one page per standard.
- [Glossary](Glossary.md) for the work product and ID codes.
