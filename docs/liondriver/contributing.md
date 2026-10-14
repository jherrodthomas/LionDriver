# Contributing to LionDriver

Contributions are welcome in software, functional safety, SOTIF, cybersecurity, AI safety, verification, documentation and vehicle integration. LionDriver inherits openpilot's development setup and code conventions; read the upstream [contributing guide](../CONTRIBUTING.md) first. This page adds the rules that come from LionDriver's assurance work.

## Where to start

- **Questions and bugs:** [open an issue](https://github.com/jherrodthomas/LionDriver/issues).
- **Changes:** fork, branch from `liondriver-dev`, and open a [pull request](https://github.com/jherrodthomas/LionDriver/pulls) against `liondriver-dev`. `master` tracks upstream openpilot and does not take LionDriver changes.
- **Reviews of the safety analyses** are as valuable as code. Comment on a work product in a pull request, or open an issue that names the work product and section.

## Safety-relevant changes

A change is safety-relevant if it touches a file on the safety-relevant list in [WP-P-01 configuration management](../../assurance/07-supporting/WP-P-01-configuration-management-plan.md) (safety firmware, safety modes, car ports, controls, driver monitoring and their configuration) or changes an assurance work product. Such a pull request must include:

1. **Rationale**: what the change does and why.
2. **Impact analysis**: which hazards, safety goals, requirements, assumptions and evidence items it affects, following [WP-M-12](../../assurance/01-management/WP-M-12-impact-analysis.md) and [WP-P-02 change management](../../assurance/07-supporting/WP-P-02-change-management.md). "No assurance object affected" is a valid result, with a reason.
3. **Verification**: the tests or analyses that show the change is correct, and their results.
4. **Record updates**: the affected records in [`assurance/case/`](../../assurance/case/README.md) or [`assurance/trace/`](../../assurance/trace/README.md), with the dashboard regenerated.

## Assurance records

```sh
python3 assurance/trace/tools/check_trace.py          # hazard log, goals and assumptions
python3 assurance/case/tools/validate.py              # Living Safety Case records
python3 assurance/case/tools/generate_dashboard.py    # regenerate the dashboard after a record change
python3 assurance/case/tools/test_case.py             # validator self-tests
```

CI runs the same checks on every pull request that touches `assurance/`, the dashboard assets or the README, and fails if the generated dashboard is out of date.

What can and cannot change a review state:

- Only a review record in [`assurance/case/reviews/`](../../assurance/case/reviews/reviews.yaml), written by the named reviewer at the independence level the [confirmation measures plan](../../assurance/01-management/WP-M-06-confirmation-measures-plan.md) requires, can mark a claim or evidence item as accepted.
- A passing CI run, a passing test or an existing file does not accept anything. It can be evidence that a reviewer accepts.
- An AI-generated review is not a substitute for the required independent confirmation.
- Never edit `status.json`, the generated SVGs or the README dashboard block by hand; change the records and regenerate.

## Upstream code

Keep changes to inherited openpilot, opendbc and panda code minimal and local, so upstream updates stay mergeable. Upstream licences, copyright notices and attribution stay in place.
