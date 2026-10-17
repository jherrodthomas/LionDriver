# Frequently asked questions

Short answers with a link to the record that holds the long one.

## Is LionDriver certified?

No. It is research and development software. It makes no claim of ISO 26262 compliance or ASIL capability and
is not approved for unsupervised operation. The safety case is being built in public precisely so that this
stays checkable. See [Reading the Living Safety Case](Reading-the-Living-Safety-Case.md).

## Is it safer than openpilot?

Not yet, and the project does not claim it is. LionDriver runs the same driving stack and the same panda safety
layer. What it adds today is the engineering record: hazard analysis, requirements, analyses and a
[gap assessment](../assurance/00-assessment/gap-assessment.md) that says where the inherited checker falls short
of what the safety goals need. Changes to the code come in Phase 3 of the [roadmap](Roadmap-and-status.md), each
one traced to a requirement.

## Can I run it on my car?

If openpilot supports your car, LionDriver does too, with the same caveats and the same driver responsibility.
That is "upstream compatible". It does not mean the car has been evaluated or that any safety claim covers it.
One configuration, the Toyota Corolla E210 with Toyota Safety Sense 2.0, is under evaluation. None is
assurance-supported yet. See [vehicle compatibility](../docs/liondriver/compatibility.md) and the
[vehicle register](../docs/liondriver/vehicles/README.md).

## Why a fork rather than contributing upstream?

The assurance work needs a record that moves at its own pace, with its own baselines, review gates and decision
authority. The code is kept close to upstream: upstream is merged in through a documented impact analysis and
every car port is kept. How upstream is managed is in
[WP-M-11](../assurance/01-management/WP-M-11-upstream-and-supplier-management.md); the strategy behind the fork
is in [WP-M-01](../assurance/01-management/WP-M-01-assurance-strategy.md).

## What does "0 accepted" on the dashboard mean?

That no claim has evidence that has passed confirmation review. Evidence is recorded first and accepted only
after independent review. The number will move when reviews start, not before. See
[Reading the Living Safety Case](Reading-the-Living-Safety-Case.md).

## Who decides what?

The project lead is the safety authority and decides risk acceptance, hazard scope, vehicle behaviour defaults,
ODD limits, money, hardware, the assessor, roles and gates. Everything else is a technical choice, recorded so the
lead can change it. See [how decisions are made](How-decisions-are-made.md).

## I found a safety problem. Where do I report it?

- A security vulnerability: follow [SECURITY.md](../SECURITY.md).
- A field incident or a suspected hazard: the
  [field monitoring process](../docs/safety/field-monitoring/PROCESS.md), which has a case template and a
  [register](../docs/safety/field-monitoring/REGISTER.md).
- Anything else: an [issue](https://github.com/jherrodthomas/LionDriver/issues).

## Why is so much of it written with Claude?

Drafting is done in Claude Code sessions under the project lead's direction; the working rules are in
[CLAUDE.md](../CLAUDE.md). Every change goes through pull request review and the workflows described in
[how the repository is organized](How-the-repository-is-organized.md). The lead holds every safety decision, and
no work product leaves draft without an independent confirmation review. The tools used, including this one,
are classified in [WP-P-07](../assurance/07-supporting/WP-P-07-tool-classification-qualification.md).

## Something is missing here

Open an [issue](https://github.com/jherrodthomas/LionDriver/issues). Questions that come up more than once get
added to this page by pull request against [`wiki/`](../wiki/README.md).
