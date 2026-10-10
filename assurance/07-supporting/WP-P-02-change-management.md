# WP-P-02 Change Management Plan

| Field | Value |
|---|---|
| Work product | WP-P-02 Change management plan |
| Standard reference | ISO 26262-8:2018 §8; ISO 26262-2:2018 §6 (impact analysis); ISO/SAE 21434:2021 §6 (change management in cybersecurity activities); ASPICE 4.0 SUP.10 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Every change to a configuration item listed in [WP-P-01 §3](WP-P-01-configuration-management-plan.md) goes through this process. It closes the planning side of GAP-31, GAP-32 and GAP-37 ([gap assessment](../00-assessment/gap-assessment.md)) and implements D-02 and D-03 of [WP-M-01](../01-management/WP-M-01-assurance-strategy.md#8-strategic-decisions-required).

Current state: there is no CODEOWNERS file and no PR template under `.github/`. `.github/workflows/auto_pr_review.yaml` only applies labels and checks the target branch. `stale.yaml` closes inactive PRs after 24 + 7 days.

## 2. Change request (CR) vehicle

| Element | GitHub implementation |
|---|---|
| Change request | GitHub issue with label `change` (template in §8), or the PR description itself for small changes |
| Change implementation | Pull request against `liondriver-dev` (or `release/ld-vX.Y`), linked to the CR issue with `Refs #n` / `Closes #n` |
| Impact analysis | Section of the PR description (template §6); for upstream syncs a separate file under `assurance/07-supporting/impact/` (proposed) |
| Approval | GitHub PR review approvals from required CODEOWNERS (§7) |
| Record | The merged PR (description, review comments, approvals, CI results) plus the merge commit. Exported at baselines per [WP-P-04](WP-P-04-documentation-management.md) |

## 3. Change types

| Type | Description | Typical class |
|---|---|---|
| CT-1 Feature / fix | LionDriver-authored code change | Per file list |
| CT-2 Configuration / calibration | Car params, limits, fingerprints, params defaults, models | SR |
| CT-3 Upstream sync | Merge or cherry-pick from `commaai/*` or `tinygrad/tinygrad` into a LionDriver fork, or submodule bump | SR (always) |
| CT-4 Dependency / toolchain | `uv.lock`, `pyproject.toml`, comma-deps wheels, cppcheck, compilers | SR-T |
| CT-5 CI / workflow | `.github/workflows/**`, `Jenkinsfile` | SR-T |
| CT-6 Work product | `assurance/**` | Per WP ASIL |
| CT-7 Problem fix | Resolution of a problem report from [WP-P-03](WP-P-03-problem-resolution.md) | Per file list |
| CT-8 Security fix | Vulnerability remediation per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md); may use embargoed private fork | SR (CS) |

## 4. Classification

1. **By path.** If any changed path matches the safety-relevant file list ([WP-P-01 §4](WP-P-01-configuration-management-plan.md#4-safety-relevant-file-list)), the change takes the class of the highest matching entry (SR-A > SR-Q > SR-T). Submodule bumps are classified by the diff inside the submodule.
2. **By work product impact.** If the change alters behaviour, an interface, a limit, a timing value or an assumption that a work product states (requirement, HARA rating, FMEA row, TARA entry, ODD element, AoU), it is safety-relevant even if no listed path is touched.
3. **By label.** The author applies one of `sr-a`, `sr-q`, `sr-t`, `nsr`. A reviewer may raise the class, never lower it without a written reason in the PR.

Automation (proposed): a workflow that compares the PR diff to the machine-readable file list and applies the label, failing if the author's label is lower (OI-2).

## 5. Process

| Step | Activity | Output | Responsible |
|---|---|---|---|
| 1 | Raise CR (issue) or open PR with CR section | CR ID = issue or PR number | Requester |
| 2 | Classify (§4) | Label | Author; checked by reviewer |
| 3 | Impact analysis (§6) for SR-A/SR-Q/SR-T | Completed checklist in PR | Author |
| 4 | Decide: accept / reject / defer | Decision comment | Maintainer (CCB, §7.3) |
| 5 | Implement on a work branch; update affected work products and `assurance/trace/` in the same PR | Commits | Author |
| 6 | Verify: CI green; required additional verification from impact analysis done and linked | CI run, test records | Author / verifier |
| 7 | Review and approve per §7 | Approvals | Reviewers |
| 8 | Merge (squash or merge commit; no force push) | Merge commit | Maintainer |
| 9 | Close CR; update status in [WP-M-00](../01-management/WP-M-00-work-product-register.md) if a WP changed | Closed issue | Author |

A rejected or deferred CR stays as a closed or open issue with its reason; it is never deleted.

## 6. Impact analysis checklist (template)

Copy into the PR for any SR-* change.

```markdown
### Impact analysis
- Change type (CT-1..CT-8):
- Class (SR-A / SR-Q / SR-T / NSR) and matched paths:
- Reference configuration affected? (TOYOTA_COROLLA_TSS2, panda safety mode Toyota) yes/no, how:
- Safety goals / requirements affected (IDs from assurance/trace/):
- Work products to update (WP IDs), or reason none are affected:
- Hazard log / HARA impact (H-, HS-, SG-):
- SOTIF impact (SH-, TC-, FI-, ODD element):
- Cybersecurity impact (TS-, CSG-, CSR-; attack surface change?):
- FFI / DFA impact (new shared resource, timing, process, IPC, param):
- Envelope limits or detection times changed? old -> new values:
- Panda firmware rebuilt? safety mode / safetyParam changed?:
- Models changed? (LFS oid old -> new):
- Tools or dependencies changed? (versions old -> new, TCL from WP-P-07):
- Verification to (re)run: safety tests / MISRA / mutation / process replay / HIL / vehicle:
- Verification evidence links:
- Upstream origin (commit / PR URL) if CT-3:
- Residual open points / follow-up issues:
```

## 7. Approvals

### 7.1 Required reviews by class

| Class | Required approvals | Independence (see [WP-P-05](WP-P-05-verification-review-procedure.md)) |
|---|---|---|
| SR-A | 2: safety reviewer + code owner, neither the author | I1 minimum; I2 for changes to safety requirements of ASIL C/D (per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md)) |
| SR-Q | 1 code owner, not the author; safety reviewer if a WP is affected | I1 |
| SR-T | 1 code owner; tool impact noted in [WP-P-07](WP-P-07-tool-classification-qualification.md) | I1 |
| NSR | 1 reviewer | I0 permitted |
| CT-3 upstream sync | As SR-A if any SR-A path changes | I1 minimum |

**Single-maintainer constraint.** Today only one person can approve. Until a second reviewer exists, SR-A and SR-Q changes are not merged into a baseline that is used for vehicle testing, or the review is done by an external reviewer whose GitHub account is added as a code owner (OI-1). This is recorded as a risk in [WP-M-07](../01-management/WP-M-07-risk-management.md).

### 7.2 Proposed CODEOWNERS content

Proposed for `.github/CODEOWNERS` in the superproject (not created by this document). Team names assume the organization from [WP-P-01 OI-1](WP-P-01-configuration-management-plan.md#13-open-items).

```text
# Default
*                                             @jherrodthomas

# SR-A envelope (enforced in the opendbc and panda forks by their own CODEOWNERS;
# here they guard submodule pointer bumps)
/opendbc_repo                                 @liondriver/safety-reviewers @jherrodthomas
/panda                                        @liondriver/safety-reviewers @jherrodthomas

# SR-Q onboard stack
/openpilot/selfdrive/selfdrived/              @liondriver/safety-reviewers
/openpilot/selfdrive/controls/                @liondriver/safety-reviewers
/openpilot/selfdrive/monitoring/              @liondriver/safety-reviewers
/openpilot/selfdrive/car/                     @liondriver/safety-reviewers
/openpilot/selfdrive/pandad/                  @liondriver/safety-reviewers
/openpilot/selfdrive/modeld/                  @liondriver/safety-reviewers @liondriver/ml-reviewers
/openpilot/selfdrive/locationd/               @liondriver/safety-reviewers
/openpilot/cereal/                            @liondriver/safety-reviewers
/openpilot/common/params_keys.h               @liondriver/safety-reviewers
/openpilot/system/manager/process_config.py   @liondriver/safety-reviewers
/openpilot/system/updated/                    @liondriver/security-reviewers
/openpilot/system/athena/                     @liondriver/security-reviewers
/SECURITY.md                                  @liondriver/security-reviewers

# SR-T configuration
/.gitmodules                                  @liondriver/safety-reviewers
/.lfsconfig                                   @liondriver/safety-reviewers
/uv.lock                                      @liondriver/safety-reviewers
/pyproject.toml                               @liondriver/safety-reviewers
/SConstruct                                   @liondriver/safety-reviewers
/.github/                                     @liondriver/safety-reviewers
/tools/release/                               @liondriver/safety-reviewers

# Work products
/assurance/                                   @liondriver/safety-reviewers
```

Proposed fork-side entries for `opendbc` and `panda` forks: `/opendbc/safety/ @liondriver/safety-reviewers`, `/opendbc/car/toyota/ @liondriver/safety-reviewers`, `/board/ @liondriver/safety-reviewers`, `/SConscript @liondriver/safety-reviewers`.

Branch protection must enable "Require review from Code Owners" for CODEOWNERS to have effect.

### 7.3 Change control board (CCB)

The CCB is the maintainer plus the safety reviewer(s). It decides on CT-3 syncs, model changes (D-05), changes to the safety-relevant file list, and any SR-A change during an RC freeze. Decisions are recorded as issue comments with the label `ccb-decision`.

## 8. Proposed PR template

Proposed for `.github/pull_request_template.md` (not created by this document).

```markdown
## Summary
<!-- what and why; link the CR / problem issue -->
Refs #

## Classification
- [ ] SR-A  - [ ] SR-Q  - [ ] SR-T  - [ ] NSR
Matched safety-relevant paths (WP-P-01 §4):

## Impact analysis
<!-- required for SR-*; paste the WP-P-02 §6 checklist -->

## Work products and trace
- [ ] Affected work products updated (list WP IDs) or "none affected because ..."
- [ ] assurance/trace/ updated for new/changed requirements and tests
- [ ] New/changed tests reference requirement IDs (@req tag, WP-P-06 §6)

## Verification
- [ ] CI green
- [ ] opendbc safety tests + coverage gate (if SR-A)
- [ ] MISRA (opendbc / panda) clean (if SR-A)
- [ ] Mutation tests (if SR-A)
- [ ] Process replay diff reviewed (if SR-Q)
- [ ] HIL / vehicle test record linked (if required by impact analysis)

## Review
- [ ] Reviewer independence stated (I0-I3)
- [ ] Review checklist from WP-P-05 used: <type>
```

## 9. Upstream synchronization (CT-3, D-02)

| Rule | Detail |
|---|---|
| Default | Frozen at `8b8c6ae` and the submodule pins in [WP-P-01 §2](WP-P-01-configuration-management-plan.md#2-current-state-as-found-at-8b8c6ae) |
| Trigger | **Once per MINOR release** (decided 2026-10-10, D-02): a planned sync of all forked submodules and the superproject before the release-candidate freeze. Only exception: an out-of-cycle targeted cherry-pick for a security advisory or a safety-relevant defect affecting the reference configuration ([WP-M-11 §5](../01-management/WP-M-11-upstream-and-supplier-management.md#5-upstream-synchronization-procedure-d-02)) |
| Branch | `sync/upstream-<YYYYMMDD>` in the superproject and the affected forks |
| Analysis | Diff against the safety-relevant file list; list each upstream commit touching SR-A/SR-Q paths with a disposition (take / reject / adapt); model and lockfile changes listed separately |
| Verification | Full re-run of SR-A verification ([WP-W-06](../05-software/WP-W-06-software-unit-verification.md)); process replay against fork references; HIL once available |
| Record | Impact analysis file in [`impact/`](impact/README.md), generated with `tools/sync/sync_report.py` and then completed by hand, plus the PR |
| Not allowed | Automatic dependency upgrades (upstream `repo-maintenance.yaml` runs `uv lock --upgrade` weekly; it is gated on `github.repository == 'commaai/openpilot'` and must stay inactive in the fork) |

## 10. Proposed change requests for fork CI (D-03)

These were raised as change requests under D-03. Status as of 2026-10-10:

| CR | Status |
|---|---|
| CR-CI-01 | **Done:** `stale.yaml` deleted |
| CR-CI-02 | **Done:** `jenkins-pr-trigger.yaml` deleted. `Jenkinsfile` is left in place; it is inert without comma's device farm |
| CR-CI-03 | **Done:** `ui_preview.yaml` deleted. The fork-owned UI report runs in `tests.yaml` (`Create UI Report`) |
| CR-CI-04 | **Done** for `liondriver-dev` (PR #2) and the submodule check (PR #3). `release/**` is not added; no release branches exist yet ([WP-P-10](WP-P-10-release-management.md)) |
| CR-CI-05 | **Done:** `safety.yaml` runs the opendbc safety tests with the coverage gate, opendbc MISRA, mutation tests and panda MISRA, all against the pinned submodules |
| CR-CI-06 | **Done:** `release.yaml` and `repo-maintenance.yaml` deleted |
| CR-CI-07 | **Done:** `problem_report.yml` and `field_report.yml` replace comma's templates; `config.yml` routes vulnerabilities to private reporting |
| CR-CI-08 | **Interim only:** process replay is pinned to comma's references for the baseline (`ref_commit`, PR #2). Fork-owned references are still open; they need LionDriver-controlled storage (GAP-30, GAP-40) |

The table below keeps the original proposals.

| CR | Workflow | Finding | Proposed change | Rationale |
|---|---|---|---|---|
| CR-CI-01 | `.github/workflows/stale.yaml` | Marks PRs stale after 24 days and closes after 7 more (drafts: 30 days); issues ignored | Delete, or set `days-before-pr-close: -1` | Safety CRs must not be closed by automation (GAP-31) |
| CR-CI-02 | `.github/workflows/jenkins-pr-trigger.yaml` | On a `trigger-jenkins` comment pushes `tmp-jenkins-<n>` branches and **deletes the trigger comment**; also deletes `tmp-jenkins*`/`__jenkins*` branches older than 24 h. No Jenkins exists for the fork | Delete | No function in the fork; deleting PR comments removes review record content |
| CR-CI-03 | `.github/workflows/ui_preview.yaml` | `preview` job currently `if: false`; would need `commaai/ci-artifacts` and `CI_ARTIFACTS_DEPLOY_KEY`; triggers on `master` and `pull_request_target` | Delete, or replace with a fork-owned UI report job | Cannot work in the fork; `pull_request_target` widens token exposure |
| CR-CI-04 | `.github/workflows/tests.yaml` | Push trigger is `master` only; `check-submodules` gated to `commaai/openpilot` | Add `liondriver-dev` and `release/**`; enable a fork version of the submodule check (WP-P-01 §6) | Test every integration |
| CR-CI-05 | New workflow | opendbc safety tests, MISRA (opendbc and panda) and mutation do not run in LionDriver CI | Add jobs running `opendbc_repo/opendbc/safety/tests/test.sh`, `.../misra/test_misra.sh`, `.../mutation.py`, `panda/tests/misra/test_misra.sh` | SR-A verification evidence per PR |
| CR-CI-06 | `.github/workflows/release.yaml`, `repo-maintenance.yaml` | Gated to `commaai/openpilot`; inert in fork | Delete to avoid accidental activation if gating changes | Clarity |
| CR-CI-07 | `.github/ISSUE_TEMPLATE/*` | Routes to comma; "We cannot look into bug reports from forks" | Replace per [WP-P-03 §3](WP-P-03-problem-resolution.md) | SUP.9 intake |
| CR-CI-08 | Process replay | Refs fetched from `commaai/ci-artifacts` | Generate fork-owned references as `process_replay/README.md` "Forks" describes | GAP-30 |

## 11. Emergency changes

A safety or security fix needed to stop ongoing harm may be merged with one approval, provided: the CCB is informed the same day; the full impact analysis and second review are completed within 5 working days; and the change is recorded in the problem report ([WP-P-03](WP-P-03-problem-resolution.md)). No emergency change goes into a release without the full process.

## 12. Metrics

Number of SR changes per month; median CR lead time; changes merged without required approval (target 0); impact analyses missing (target 0). Reported in the QA report ([WP-M-05](../01-management/WP-M-05-quality-assurance-plan.md)).

## 13. Open items

| ID | Item |
|---|---|
| OI-1 | Name at least one second reviewer (internal or external) with GitHub access so SR-A approvals can meet the two-approval rule |
| OI-2 | Implement automatic PR classification from the machine-readable file list |
| OI-3 | Raise CR-CI-01 to CR-CI-08 as issues and implement |
| OI-4 | Create `.github/CODEOWNERS` and `.github/pull_request_template.md` from §7.2 and §8 via a CR; create GitHub teams |
| OI-5 | ~~Decide where impact analysis files for syncs live~~ Closed: [`impact/`](impact/README.md) (D-02 tooling) |
| OI-6 | Decide merge strategy (squash vs merge commit) so that review records remain linked to commits in submodule forks |
