# Cybersecurity and ISO/SAE 21434

ISO 26262 asks what happens when something breaks, and SOTIF what happens when nothing breaks but the function still
gets it wrong. ISO/SAE 21434 asks the third question: what if someone attacks it? This page explains the standard
from the start for someone who has never used it, follows one real LionDriver threat through it, and shows where it
meets safety. It explains and links. The analysis is the TARA
([WP-C-09](../assurance/02-concept/WP-C-09-tara.md)), the goals and concept
([WP-C-10](../assurance/02-concept/WP-C-10-cybersecurity-goals-and-concept.md)), the safety–security interactions
([`hatara/`](../assurance/02-concept/hatara/README.md)) and the cybersecurity case
([WP-K-03](../assurance/10-safety-case/WP-K-03-cybersecurity-case.md)); nothing here is analysis content. No figure
shows how to carry out an attack.

Every figure is drawn at each wiki sync by [`tools/wiki/cyber_animations.py`](../tools/wiki/cyber_animations.py). The
risk map, the attack-path factors and the counts are read from the records, and every other ID, rating and status is
checked against the record it comes from. When a record changes, the build fails instead of showing old text.

## 0. The third question

![Animated: the car steers out of its lane; from a fault (ISO 26262), from a model error (SOTIF) and from an attacker who tells the panda to drop its limits (ISO/SAE 21434, TS-02); one hazard, three causes](cyber-third-question.svg)

Security differs from the other two in one way that shapes everything else: an attacker is not random. A broken part
fails by chance; an attacker picks the worst moment and can repeat it on every car. So ISO/SAE 21434 does not count
failure rates. It asks how bad the damage would be and how hard the attack is.

## 1. Following one threat through the TARA

![Animated: the seven questions of a TARA answered for TS-02, from the asset AS-02 to the damage DS-01, the threat, the attack path, the feasibility, the risk 5 of 5 and the treatment by goal CSG-01](cyber-one-threat.svg)

A **threat analysis and risk assessment** (TARA) works through the same questions for every asset: what we protect,
what harm follows if it is broken, who could do what, how, how hard that is, how risky it is, and what we do about
it. The answer to the last question is a **cybersecurity goal**, and its **CAL** (cybersecurity assurance level, 1 to
4) sets how much rigour its development gets.

## 2. Damage is more than safety

![Animated: two damage scenarios rated for safety, financial, operational and privacy impact; unintended steering is Severe for safety, leaked cabin video is Severe for privacy; both are impact level 4](cyber-more-than-safety.svg)

Each damage scenario is rated in four categories, and its impact level is the worst of the four. Safety damage is
taken from the hazard analysis ([WP-C-03](../assurance/02-concept/WP-C-03-hara.md)), so the TARA and the HARA share
one hazard log. Privacy damage has no hazard at all, and ISO 26262 never sees it.

## 3. How hard is the attack?

![Animated: the five attack-potential factors for an attack from the openpilot computer and one from the CAN bus; knowledge of the item is public because the design is open source; closing one path moves the attacker to the next](cyber-how-hard.svg)

Feasibility comes from the attacker's side: time, expertise, knowledge of the item, window of opportunity and
equipment. LionDriver is open source, so knowledge of the item is public for every path. A control is credited only
once it is verified and the path is re-rated with it in place.

## 4. The risk map

![Animated: every threat scenario of WP-C-09 placed on the impact by feasibility matrix, the treatment threshold at risk 3, the four treatment options and LionDriver's status](cyber-risk-map.svg)

Risk is impact against feasibility, from 1 to 5. A risk of 3 or more must be treated: reduced with a control,
avoided by removing the feature, shared, or retained with a reason. A risk of 4 or 5 drives a cybersecurity goal
([WP-C-10](../assurance/02-concept/WP-C-10-cybersecurity-goals-and-concept.md)).

## 5. From goal to control to evidence

![Animated: goal CSG-01, requirement CSR-C-01, the control in the panda firmware, its verification in CI, the penetration test not yet run, and claim CG2.1 of the cybersecurity case](cyber-goal-to-evidence.svg)

A goal becomes requirements, the requirements become a control, and tests and a penetration test show the control
holds. The results support a claim of the cybersecurity case
([WP-K-03](../assurance/10-safety-case/WP-K-03-cybersecurity-case.md)). The same lock is a safety requirement too, as
on [SOTIF and ISO 26262](SOTIF-and-ISO-26262.md), where the torque cap serves two standards.

## 6. Where safety and security meet

![Animated: four interactions of hatara/: one lock serves both, a recovery path is an attack path, a rejected frame is a lost function, firmware integrity holds up the safety goals; the count of interactions by type](cyber-meet.svg)

A measure on one side can help the other, hurt it, or be what the other rests on. LionDriver records each of these
interactions in [`hatara/`](../assurance/02-concept/hatara/README.md), where a tool checks them against the HARA and
the TARA.

## 7. After release

![Animated: what is watched, an example vulnerability report through acknowledgement, evaluation, a stop-use decision, a fix, a staged rollout and an advisory, what makes an update secure, and LionDriver today](cyber-after-release.svg)

New attacks appear after release, so the project watches for them, handles reports and ships fixes as updates
([WP-O-05](../assurance/09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md)). The report in
the figure is an example. How to report a vulnerability is in [SECURITY.md](../SECURITY.md); what keeps the item safe
after release in general is on [After release](After-release.md).

## See also

- [Standards at a glance](Standards-at-a-glance.md): how the standards divide the work.
- [What is a safety case?](What-is-a-safety-case.md): the cybersecurity case is built the same way.
- [Reporting a safety concern](Reporting-a-safety-concern.md).
- [Glossary](Glossary.md) for the work product and ID codes.
