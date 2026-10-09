# WP-P-04 Documentation Management

| Field | Value |
|---|---|
| Work product | WP-P-04 Documentation management |
| Standard reference | ISO 26262-8:2018 §10; ISO/SAE 21434:2021 §5 (documentation management); ASPICE 4.0 SUP.7 (informative), SUP.8 |
| Version | 0.1 |
| Status | Draft |
| ASIL / scope | All |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1) |
| Approver | Project maintainer (acting safety manager) |
| Baseline | `8b8c6ae` |

## 1. Purpose and scope

Defines how LionDriver work products are written, identified, versioned, reviewed, approved, stored, retained and made available, following decision D-07 (docs-as-code) in [WP-M-01](../01-management/WP-M-01-assurance-strategy.md#8-strategic-decisions-required). Applies to everything under `assurance/` and to engineering documents under `docs/` that a work product cites as evidence.

## 2. Principles

1. Documentation is part of the configuration: work products live in the same Git repository as the code they describe and are versioned with it ([WP-P-01](WP-P-01-configuration-management-plan.md) CI-10).
2. A work product changes only through a pull request ([WP-P-02](WP-P-02-change-management.md)); the PR review is the verification review record ([WP-P-05](WP-P-05-verification-review-procedure.md)).
3. Content states what is true at its `Baseline` commit, cites repository paths and line numbers as evidence, and never claims evidence that does not exist.
4. Standards text is not reproduced; references are clause-level only ([`assurance/README.md`](../README.md#standards-text)).

## 3. Format rules

| Rule | Detail |
|---|---|
| File format | GitHub-flavoured Markdown (`.md`), UTF-8, LF line endings (`.gitattributes` sets `text=auto eol=lf`) |
| Machine-readable data | YAML under `assurance/trace/` ([WP-P-06](WP-P-06-requirements-management-traceability.md)) |
| Diagrams | Text-based (ASCII in fenced blocks, Mermaid, or PlantUML source). Binary images only when unavoidable, with the source committed alongside. Note `.gitattributes` routes `*.svg` and `*.png` to Git LFS, whose endpoint is currently comma's (see [WP-P-01 §6](WP-P-01-configuration-management-plan.md#6-submodule-control-d-01)) |
| Spreadsheets | Avoided. If an analysis needs a table tool (e.g. FMEDA), commit a CSV as the controlled source and treat any `.xlsx` as a generated view |
| File naming | `WP-<area>-<nn>-<kebab-case-name>.md` exactly as listed in [WP-M-00](../01-management/WP-M-00-work-product-register.md) |
| Folder | As defined in the [assurance README layout](../README.md#layout) |
| Links | Relative links between work products, using the exact register file names. Code references as repository-relative paths, with `:line` or `:start-end` where useful |
| Tables | Preferred over prose for lists of items, findings, requirements |
| Language | Plain technical English, short sentences; one term per concept (glossary in [WP-C-01](../02-concept/WP-C-01-item-definition.md)) |

## 4. Identification

| Element | Rule |
|---|---|
| Work product | `WP-<area>-<nn>` from the register; never reused |
| Items inside a WP | ID prefixes from [`assurance/README.md`](../README.md#identifiers) (H-, SG-, FSR-, TSR-, ...). IDs never reused; withdrawn items keep their ID with status `Withdrawn` |
| Open items | `OI-<n>`, unique per document |
| Sections | Numbered headings; links use GitHub anchors |
| Record files | Review records `RR-<YYYY>-<nnn>`; confirmation records under `10-safety-case/confirmation/` per [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |

## 5. Document control header and status

Every work product starts with the header block defined in [`assurance/README.md`](../README.md#document-control-header). Status values and meaning are defined there (Skeleton, Draft, In review, Approved, Baselined).

| Field | Rule |
|---|---|
| Version | `0.x` while Draft; `1.0` at first approval; MINOR increment for each approved change; MAJOR when the scope or the safety concept changes |
| Status | Updated in the same PR that changes the state. "In review" is set when the PR is opened; "Approved" only in the merge of an approved PR; "Baselined" only when included in a gate or release tag |
| Baseline | The commit or tag the content was checked against. Updated when the content is re-checked |
| Reviewer(s) | Name and independence level (I0–I3) as recorded in the PR approval |
| Approver | Role from the safety plan ([WP-M-02](../01-management/WP-M-02-safety-plan.md)) |

The register [WP-M-00](../01-management/WP-M-00-work-product-register.md) status column must match the header. A CI check comparing the two is OI-1.

## 6. Change history

Git history is the change log. Each approved version additionally gets one line in a "Revision history" table at the end of the document (version, date, PR number, summary) so that an exported copy carries its history.

## 7. Review and approval

| Step | Mechanism |
|---|---|
| Author submits | PR with label `wp` and the class from [WP-P-02 §4](WP-P-02-change-management.md#4-classification) |
| Verification review | PR review using the checklist for the WP type in [WP-P-05](WP-P-05-verification-review-procedure.md) |
| Approval | GitHub "Approve" by the approver named in the header; for ASIL-relevant WPs also the independence level required by [WP-M-06](../01-management/WP-M-06-confirmation-measures-plan.md) |
| Confirmation review | Separate record (not a PR approval) for WPs listed in WP-M-06, by an independent reviewer |
| Merge | Only after approvals and green CI (Markdown link check, OI-2) |

A comment such as "LGTM" with no checklist reference is not accepted as a verification review for an SR-A or SR-Q work product.

## 8. Storage, backup and export

| Need | Measure |
|---|---|
| Master storage | `assurance/` on the protected `liondriver-dev` branch of the LionDriver repository |
| Backup | Mirror per [WP-P-01 §10](WP-P-01-configuration-management-plan.md#10-backup-retention-and-access) |
| Review records | PR data (description, reviews, comments, approvals, CI checks) exported as JSON through the GitHub API at each baseline into `evidence/<tag>/reviews/` of the evidence package, because GitHub data is not part of a Git clone |
| Problem and change records | Issue export per [WP-P-03 §9](WP-P-03-problem-resolution.md#9-records) |
| Export for assessors | At each gate: (a) `git archive` of the baseline tag; (b) PDF rendering of `assurance/` (e.g. with pandoc), one PDF per WP with the header and commit SHA on each page; (c) review and issue exports; (d) the baseline manifest ([WP-P-01 §8](WP-P-01-configuration-management-plan.md#8-baselines)). Delivered as a single archive with a SHA-256 checksum file |
| ALM migration | Markdown and YAML are kept tool-neutral so the content can be imported into an ALM tool later (D-07) |

## 9. Availability and access

| Audience | Access |
|---|---|
| Project members | Read/write via PR |
| External reviewers and assessor | Read access to the repository, or the export archive (§8) |
| Public | The repository is public today; content that must not be public (unfixed vulnerabilities, personal data from drive logs, private keys) is never committed. Embargoed CS content lives in private security advisories per [WP-O-05](../09-production-operation/WP-O-05-cybersecurity-incident-response-updates.md) |

## 10. Retention

Work products and their records are kept for every released baseline for at least the service life of that release plus 10 years (period to be confirmed in [WP-M-02](../01-management/WP-M-02-safety-plan.md); [WP-P-01 OI-6](WP-P-01-configuration-management-plan.md#13-open-items)). Git history is never rewritten on protected branches. Superseded documents remain retrievable through tags.

## 11. Externally sourced documents

| Document | Handling |
|---|---|
| ISO / SAE / VDA standards | Licensed copies held by the project; not committed; edition recorded in [`assurance/README.md`](../README.md) |
| Upstream docs (`docs/SAFETY.md`, `docs/LIMITATIONS.md`, `docs/INTEGRATION.md`) | Treated as inherited input. A WP citing them cites the commit |
| Component data (STM32H7 reference and safety manuals, datasheets) | Reference by title, revision and source URL; local copy in a non-public store if licence forbids redistribution |

## 12. Open items

| ID | Item |
|---|---|
| OI-1 | CI check that each WP header `Status`/`Version` matches the register |
| OI-2 | Markdown link checker in CI for `assurance/**` (links to WPs not yet written will fail until they exist) |
| OI-3 | Script for the assessor export (§8), including GitHub PR/issue export |
| OI-4 | Add the "Revision history" table to every WP at first approval |
| OI-5 | Decide where non-redistributable reference documents are stored |
