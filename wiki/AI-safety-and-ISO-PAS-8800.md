# AI safety and ISO/PAS 8800

LionDriver steers with a neural network that it did not train. ISO 26262 covers parts that fail, ISO 21448 a function
that falls short, and ISO/PAS 8800 what is particular to AI: the data, the training, how a model is tested, the
monitors around it and how it may change. This page explains the standard from the start for someone who has never
used it, with LionDriver's real models. It explains and links. The AI system and its requirements are in
[WP-C-11](../assurance/02-concept/WP-C-11-ai-system-definition-and-safety-requirements.md), the plan in
[WP-M-10](../assurance/01-management/WP-M-10-ai-safety-plan.md) and the ML engineering in
[WP-W-10](../assurance/05-software/WP-W-10-ml-engineering.md); nothing here is analysis content.

Every figure is drawn at each wiki sync by [`tools/wiki/ai_animations.py`](../tools/wiki/ai_animations.py). The
requirement statuses, the input-space dimensions and the counts are read from the records, and every other ID and
number is checked against the record it comes from. When a record changes, the build fails instead of showing old
text.

## 0. Why AI needs its own rules

![Animated: the four coded lines of the panda gate against the 61 MB of weights of the driving model; where ISO 26262, ISO 21448 and ISO/PAS 8800 each fit; LionDriver's acquired, pre-trained model route](ai-why.svg)

Coded software can be read and tested line by line. A learned model's behaviour comes from data, and no line in it
says what it should do, so its safety is shown by testing its behaviour and by what surrounds it. LionDriver does not
train models: it accepts a finished one from upstream, so its AI requirements are acceptance criteria for that model
plus requirements on the code around it.

## 1. What is learned, and what is coded around it

![Animated: the AI system boundary from camera frames through the learned network to the published messages, then the controller and the panda envelope; a wild output is cut to the limit, a wrong in-limit output passes](ai-boundary.svg)

The envelope bounds how much and how fast the car can be steered, whatever the model asks for. It cannot tell a wrong
direction that stays inside the limits from a right one. The AI requirements therefore aim at keeping those in-limit
errors rare and making errors visible.

## 2. How a model gets it wrong

![Animated: the six AI error types, perception, planning, temporal, out of distribution, numerical and driver monitoring, each with an example and its SOTIF insufficiencies](ai-errors.svg)

Each error type links to the functional insufficiencies of the SOTIF analysis, so the AI view and the SOTIF view share
one chain: [SOTIF and ISO 26262](SOTIF-and-ISO-26262.md).

## 3. What the model must handle, and what it learned

![Animated: the claimed input space inside an unknown training distribution; which input-space dimensions the car can observe at runtime](ai-input-space.svg)

The **input space** is the set of conditions in which the model is claimed to work, derived from the operating
domain. Because the training data is not visible, nobody can show that it covers the input space; each claim has to
be tested on LionDriver's own data, condition by condition.

## 4. AI safety requirements

![Animated: the AI safety requirements in seven groups, each coloured by its status in WP-C-11](ai-requirements.svg)

## 5. Data

![Animated: the data a model test needs, recorded on the reference car, tagged by condition, labelled, frozen and independent of training; LionDriver today](ai-data.svg)

A test on data the model was trained on proves nothing, so evaluation data must be recorded independently, tagged
with its conditions so results can be split by them, and frozen once it is used as evidence.

## 6. Testing a model, and changing it

![Animated: the upstream model replay forced to pass, the twelve model tests in four groups, and the path of a model change from upstream to release](ai-testing.svg)

A new model is a safety change. Nothing from upstream is adopted automatically, and every model change goes through
acceptance tests and a new exploration block of the SOTIF validation
([WP-V-04](../assurance/06-validation/WP-V-04-sotif-unknown-scenarios.md)).

## 7. No single model is trusted alone

![Animated: four layers around the model, the runtime monitors with their status, the controller limits, the panda envelope and the supervising driver; the same envelope serves four standards](ai-layers.svg)

The safety argument does not rest on the model being good. It rests on the envelope, on validation that keeps in-limit
errors rare, and on monitors and the driver that catch the rest. The same torque cap and safety-mode lock appear on
[SOTIF and ISO 26262](SOTIF-and-ISO-26262.md) and on
[Cybersecurity and ISO/SAE 21434](Cybersecurity-and-ISO-21434.md).

## See also

- [Standards at a glance](Standards-at-a-glance.md): how the standards divide the work.
- [From hazard to test](From-hazard-to-test.md): the envelope's own requirements and tests.
- [Glossary](Glossary.md) for the work product and ID codes.
