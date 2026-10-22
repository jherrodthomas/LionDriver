# After release (ISO 26262 Part 7)

Safety work does not end when the software is released. ISO 26262 Part 7 covers what comes after development:
planning, production, operation, service and decommissioning. This page explains those stages in plain words, then
shows what each one means for LionDriver, which is not built in a factory but installed on an owner's car. It
explains and links. The procedures are the work products of
[`09-production-operation/`](../assurance/09-production-operation/README.md) and their requirements are in
[WP-S-06](../assurance/03-system/WP-S-06-requirements-production-operation.md); nothing here is a procedure.

Both figures are drawn at each wiki sync by [`tools/wiki/p7_animations.py`](../tools/wiki/p7_animations.py). Every
LionDriver step names the record it comes from and is checked against it, so a changed procedure fails the build
instead of showing an old status.

## 1. The five stages, in general

![Animated: a car passes five stages after development, plan, produce, operate, service and decommission, each with what it asks for in plain words; requirements flow in from development and field issues flow back](p7-general.svg)

*An overview in plain words. It quotes nothing from the standard and gives no clause numbers; the requirements are
in the licensed ISO 26262-7:2018 text.*

The idea that joins the stages: the requirements for production, operation, service and decommissioning are written
during development (ISO 26262-4), so that what keeps the item safe after release is designed in, not improvised.
What is learned in the field flows back into the analyses and the next release.

## 2. The same stages for LionDriver

![Animated: the same five stages for LionDriver, plan, install, operate, service and remove, with each step's procedure ID and its status, ending on what is written and what is not yet in place](p7-ours.svg)

| Stage | For a retrofit it means | Record |
|---|---|---|
| Plan | Requirements for each stage, procedures, and who does them | [WP-S-06](../assurance/03-system/WP-S-06-requirements-production-operation.md), WP-O-01…05 |
| Install | The owner's car is the "production line": identify device, harness and car, check the special characteristics (harness variant, connector seating, mount), install only released software, verify the panda firmware, then an engagement check with a trained driver | [WP-O-01](../assurance/09-production-operation/WP-O-01-installation-and-provisioning-control.md) |
| Operate | Only released baselines run; parameters are checked after each update; a withdrawn release forces dashcam mode; field monitoring watches for problems | [WP-O-02](../assurance/09-production-operation/WP-O-02-operation-service-decommissioning.md) §3, §6; [WP-O-04](../assurance/09-production-operation/WP-O-04-field-monitoring.md) |
| Service | A workshop can change what LionDriver relies on: a dealer EPS update, an alignment, a new windscreen. Each one has a follow-up check, and TSR-620 refuses engagement until the car's ECU firmware matches the release record | WP-O-02 §4–§5 |
| Remove | Reconnect the stock camera, confirm the stock driver-assist functions and no trouble codes, reset the device and wipe its identity keys, revoke its credentials | WP-O-02 §7 |

What is not yet in place, as the figure shows: independent roles (one maintainer does every stage, DFI-19), a way to
roll back an update and re-validate after it (WP-O-02 OI-7), and field monitoring with a LionDriver data path
(WP-O-04 §11). None of these procedures has run on a customer car yet.

## Where next

- [From hazard to test](From-hazard-to-test.md): where the requirements for these stages come from.
- [What is a safety case?](What-is-a-safety-case.md): how operation feeds back into the case (defeaters, evidence).
