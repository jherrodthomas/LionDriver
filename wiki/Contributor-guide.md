# Contributor guide

Contributions are welcome in software, functional safety, SOTIF, cybersecurity, AI safety, verification,
documentation and vehicle integration. This page is the short version of
[contributing to LionDriver](../docs/liondriver/contributing.md), which is the rule book, and of the inherited
[openpilot contributing guide](../docs/CONTRIBUTING.md), which covers the development setup and code conventions.

![What a change goes through before it is merged: a pull request against liondriver-dev is classified by the paths it touches, must carry rationale, impact analysis, verification and record updates when safety-relevant, is checked by the workflows, and is reviewed and merged by a person.](change-path.svg)

*Rendered from the [safety-relevant file list](../assurance/07-supporting/safety-relevant-paths.txt) and the [workflow files](../.github/workflows) by [`infographics.py`](../tools/wiki/infographics.py) at every wiki sync.*

## Setting up

LionDriver inherits openpilot's setup. Ubuntu 24.04 is the primary target; macOS works for most of it and
Windows through WSL 2. [`tools/README.md`](../tools/README.md) has the full steps.

```sh
git clone https://github.com/jherrodthomas/LionDriver.git
cd LionDriver
tools/op.sh setup
source .venv/bin/activate
scons -u
```

The assurance checks need only Python:

```sh
python3 assurance/trace/tools/check_trace.py          # hazard log, goals and assumptions
python3 assurance/case-records/tools/validate.py              # Living Safety Case records
python3 assurance/case-records/tools/generate_dashboard.py    # regenerate the dashboard after a record change
python3 assurance/case-records/tools/test_case.py             # validator self-tests
```

## Branches and pull requests

- Branch from `liondriver-dev` and open the pull request against `liondriver-dev`. `master` tracks upstream
  openpilot and does not take LionDriver changes.
- Questions and bugs go to the [issues](https://github.com/jherrodthomas/LionDriver/issues). A review of a
  safety analysis is as valuable as code: comment on the work product in a pull request, or open an issue naming
  the work product and section.
- The [PR review workflow](../.github/workflows/auto_pr_review.yaml) labels each pull request by the paths it
  touches. The other workflows that run on it are listed in
  [how the repository is organized](How-the-repository-is-organized.md#what-checks-a-change).

## Is my change safety-relevant?

A change is safety-relevant if it touches a path on the
[safety-relevant file list](../assurance/07-supporting/safety-relevant-paths.txt) or changes an assurance work
product. The list has three classes:

| Class | What it covers | Examples |
|---|---|---|
| `SR-A` | Code or data in the ASIL path: the safety envelope on the panda microcontroller | `opendbc_repo/opendbc/safety/`, `panda/board/` |
| `SR-Q` | QM, SOTIF or cybersecurity elements that feed hazards, configure the envelope or affect freedom from interference | The Toyota car port, the car abstraction, controls, driver monitoring |
| `SR-T` | Build, test, CI, toolchain or dependency configuration that changes evidence or binaries | Workflows, coverage tooling, pinned toolchains |

Anything not matched is not safety-relevant and takes the standard route. The list is owned by
[WP-P-01 configuration management](../assurance/07-supporting/WP-P-01-configuration-management-plan.md) and
changes only through a change request.

## What a safety-relevant pull request must include

1. **Rationale.** What the change does and why.
2. **Impact analysis.** Which hazards, safety goals, requirements, assumptions and evidence items it affects,
   following [WP-M-12](../assurance/01-management/WP-M-12-impact-analysis.md) and
   [WP-P-02 change management](../assurance/07-supporting/WP-P-02-change-management.md). "No assurance object
   affected" is a valid result, with a reason.
3. **Verification.** The tests or analyses that show the change is correct, and their results.
4. **Record updates.** The affected records in [`assurance/case-records/`](../assurance/case-records/README.md) or
   [`assurance/trace/`](../assurance/trace/README.md), with the dashboard regenerated.

## What can and cannot change a review state

- Only a review record in [`assurance/case-records/reviews/`](../assurance/case-records/reviews), written by the named reviewer
  at the independence level the
  [confirmation measures plan](../assurance/01-management/WP-M-06-confirmation-measures-plan.md) requires, can
  mark a claim or evidence item as accepted.
- A passing CI run, a passing test or an existing file does not accept anything. It can be evidence that a
  reviewer accepts.
- An AI-generated review is not a substitute for the required independent confirmation.
- Never edit `status.json`, the generated SVGs or the README dashboard block by hand. Change the records and
  regenerate.

## Inherited code

Keep changes to inherited openpilot, opendbc and panda code minimal and local, so upstream updates stay
mergeable. Upstream licences, copyright notices and attribution stay in place. Submodule pins change through the
[upstream management process](../assurance/01-management/WP-M-11-upstream-and-supplier-management.md), with an
impact analysis.

## Working with Claude sessions

Much of the drafting is done in Claude Code sessions under the project lead's direction. The rules those
sessions follow are in [CLAUDE.md](../CLAUDE.md) and [`assurance/AGENTS.md`](../assurance/AGENTS.md): sort
questions before asking, keep every question self-contained, ask in batches of ten, and record decisions in the
[register](How-decisions-are-made.md). A session's pull request is reviewed like any other. The
[session log](Session-log.md) lists what has been merged.

## Where to get help

- [Issues](https://github.com/jherrodthomas/LionDriver/issues) for anything about the project.
- [Discussions](https://github.com/jherrodthomas/LionDriver/discussions) for open-ended questions.
- Security problems go through [SECURITY.md](../SECURITY.md), never a public issue. See
  [reporting a safety concern](Reporting-a-safety-concern.md).
