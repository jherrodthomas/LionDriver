# What is a safety case?

A first look at LionDriver's safety case for someone who has never read one: what it is, how one big claim is
broken down, what makes evidence count, and why doubts are written down. This page explains and links. The case
itself is [WP-K-01](../assurance/10-safety-case/WP-K-01-safety-case.md) and the records in
[`assurance/case-records/`](../assurance/case-records/README.md); nothing here is a claim, evidence or a review.

Every figure on this page is drawn at each wiki sync by
[`tools/wiki/case_animations.py`](../tools/wiki/case_animations.py) from those records: every ID, title, status and
count is read from them, so the figures change when the records do. Where a figure puts a record in its own words,
the build checks the record still says it.

> **Assurance status represents recorded engineering evidence and review state. It does not constitute
> certification or approval for unsupervised operation.**

## 1. The idea

![Animated: the definition of a safety case built one phrase at a time: the system (LionDriver on a Toyota Corolla), its environment (limited-access highways), the top claim G0, the argument S0 into G1 to G5, the evidence, and the documents](case-what-is-it.svg)

A safety case is a structured, documented argument supported by evidence that shows a system is acceptably safe to
operate in a specific environment. Each part of that sentence is something you can point at:

| Part | In LionDriver |
|---|---|
| The system | openpilot with the panda safety MCU on the reference Toyota Corolla ([`CFG-001`](../assurance/case-records/configurations/cfg-001-toyota-corolla-e210.yaml)) |
| The environment | Its operational design domain: limited-access highways only ([WP-C-02](../assurance/02-concept/WP-C-02-odd-and-intended-functionality.md)) |
| Acceptably safe | The top claim, G0: the reference configuration poses no unreasonable risk |
| Structured argument | Claims split into smaller claims by arguments (strategies) |
| Evidence | Tests, analyses and reviews, each recorded with where it is and who reviewed it |
| Documented | WP-K-01 and the records, which CI validates on every change |

It shows; it does not prove. A safety case is an argument that a reviewer can check, and the doubts that remain are
part of it (section 4).

## 2. Breaking the big claim down

![Animated: one path down the claim tree, G0 to G1 to G1.1 to G1.1.4, each split by an argument, ending on the evidence of G1.1.4](case-claim-tree.svg)

"No unreasonable risk" cannot be checked directly. An **argument** says how to split it: by source of risk, then by
safety goal, then by property. The split goes on until each claim is small enough that a test, an analysis or a
review can show whether it holds. The top claim holds only if every claim under it holds.

The symbols are those of the Goal Structuring Notation (GSN): a rectangle is a claim, a parallelogram an argument
(strategy), a circle a piece of evidence. The full trees are drawn from the records in
[`assurance/10-safety-case/gsn/`](../assurance/10-safety-case/gsn/).

## 3. What makes evidence count

![Animated: the evidence record Sn-15 checked against five questions (where, which version, which car, complete, independently reviewed), stamped with its status, and the things that never make evidence count on their own](case-evidence.svg)

A test that passes is not yet evidence that counts. Before a piece of evidence can support a claim, it must say what
it is and where it is, which baseline and which car it applies to, it must be complete, and someone independent
must have reviewed it. The rules are in [`assurance/case-records/README.md` §4](../assurance/case-records/README.md#4-rules): a
passing CI run, a passing test, a file that exists or an AI-written review never accept anything on their own.

## 4. Defeaters: the doubts we write down

![Animated: the claim G1.1.4 with its evidence, the defeater DF-02 and its closure route, the other open defeaters on the same claim, the acceptance rule, and an illustration of how a defeater is closed](case-defeaters.svg)

A **defeater** (DF-nn) is a recorded reason a claim might not hold: a gap, an unmeasured time, an untested
assumption. Each one names its closure route. A claim cannot be accepted while any defeater on it is open. The
defeaters are published on purpose: they show exactly what is left to do.

## Where next

- [From hazard to test](From-hazard-to-test.md): one chain from a hazard to the tests whose results become evidence.
- [Reading the Living Safety Case](Reading-the-Living-Safety-Case.md): the dashboard, figure by figure.
- [Deriving and writing safety requirements](Deriving-and-writing-safety-requirements.md) and
  [Building a fault tree](Building-a-fault-tree.md): where the claims' requirements and analyses come from.
