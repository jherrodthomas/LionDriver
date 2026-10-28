# The wiki, kept in the repository

This folder is the source of the [LionDriver GitHub wiki](https://github.com/jherrodthomas/LionDriver/wiki). The
wiki is a mirror: on every push to `liondriver-dev`, the
[wiki workflow](../.github/workflows/wiki.yaml) builds the pages with
[`tools/wiki/build_wiki.py`](../tools/wiki/build_wiki.py) and pushes them to the wiki repository, so the session log,
the sync stamp and the infographics follow every merge. The same workflow checks the pages on every pull request,
whichever files it touches, so a change that moves a file the pages link to fails before it is merged. The wiki is
never edited in place; an edit made there is overwritten by the next sync.

This file describes the folder and is not published.

## What the wiki is for

Orientation for newcomers, contributors and reviewers: what LionDriver is, how the repository is laid out, how
decisions are made, what the codes mean, how to read the Living Safety Case. It explains and links.

It is not a work product. No page carries a document-control header, counts as evidence, or states a safety claim,
hazard, requirement or vehicle-support fact on its own authority. Where a page touches one, it links to the record
in [`assurance/`](../assurance/README.md) that owns it.

## Writing a page

- One page per file, `Title-With-Hyphens.md`. The wiki shows the file name with the hyphens as spaces.
- Link to another page as `[Glossary](Glossary.md)`: the build strips `.md` so the link works on the wiki, and the
  folder stays readable on GitHub.
- Link to a repository file or folder as `[`assurance/`](../assurance/README.md)`: the build turns it into an
  absolute link on the synced branch and fails if the target does not exist.
- Every page must be linked from [`_Sidebar.md`](_Sidebar.md). [`_Footer.md`](_Footer.md) carries the sync stamp;
  `{{REPO}}`, `{{BRANCH}}`, `{{SYNC_COMMIT}}` and `{{SYNC_DATE}}` are filled in at build time, and
  `{{MERGE_LOG}}` becomes the list of merged pull requests read from the checkout's merge commits.
- Do not type figures that the repository generates (claim counts, evidence counts, vehicle counts). Link to the
  generated source instead, or embed the badge from `assurance/case-records/badge.json`.
- Images: only figures that already exist in the repository, embedded as `![alt](../path/to/figure.svg)`; the build
  turns that into the raw file address on the synced branch. Never draw a figure for the wiki that touches safety
  content; a flow that needs a drawing is written as a Mermaid block, which GitHub renders and reviewers read as
  text. Caption each image with where it comes from and, for a generated figure, what generates it.
- Two infographics are rendered from the records at every sync by [`tools/wiki/infographics.py`](../tools/wiki/infographics.py)
  and published next to the pages, so nothing is committed and nothing goes stale: `decision-register.svg` and
  `change-path.svg`. A page embeds one as `![alt](decision-register.svg)`. Add an infographic there, never by hand.
- Two animated requirement explainers, `req-anatomy.svg` and `req-vague-to-verifiable.svg`, are rendered the same way by
  [`tools/wiki/animations.py`](../tools/wiki/animations.py). Every clause they draw is quoted from the TSC or the
  page, and the build fails when a quote is no longer there.
- The figures of "Building a fault tree" (`fta-symbols.svg`, `fta-item-to-tree.svg`, `fta-and-or.svg`,
  `fta-traps.svg`) are rendered by [`tools/wiki/fta_animations.py`](../tools/wiki/fta_animations.py), checked the same
  way against WP-A-04, the item definition and the TSC.
- The figures of "What is a safety case?" (`case-what-is-it.svg`, `case-claim-tree.svg`, `case-evidence.svg`,
  `case-defeaters.svg`) are rendered by [`tools/wiki/case_animations.py`](../tools/wiki/case_animations.py) from the
  records in `assurance/case-records/`, with the same checks.
- The figures of "From hazard to test" (`h2t-item.svg`, `h2t-hara.svg`, `h2t-what-how.svg`, `h2t-allocation.svg`,
  `h2t-engineers.svg`, `h2t-mechanism.svg`, `h2t-testing.svg`) are rendered by
  [`tools/wiki/h2t_animations.py`](../tools/wiki/h2t_animations.py), with the same checks against the concept,
  system, software and hardware work products, the case records and (when checked out) the opendbc and panda code.
- The figures of "Hardware safety and interference" (`hw-numbers.svg`, `hw-ffi.svg`) are rendered by
  [`tools/wiki/hw_animations.py`](../tools/wiki/hw_animations.py): the metrics are computed from the FMEDA records and
  the FFI verdicts read from WP-A-02 §8.
- The figures of "After release" (`p7-general.svg`, `p7-ours.svg`) are rendered by
  [`tools/wiki/p7_animations.py`](../tools/wiki/p7_animations.py); each LionDriver step is checked against the WP-O
  record it names. The general figure quotes nothing from the standard.
- The figures of "SOTIF and ISO 26262" (`sotif-two-questions.svg`, `sotif-who-owns.svg`, `sotif-triggering.svg`,
  `sotif-four-areas.svg`, `sotif-how-much.svg`, `sotif-unknowns.svg`, `sotif-one-chain.svg`) are rendered by
  [`tools/wiki/sotif_animations.py`](../tools/wiki/sotif_animations.py), checked against the SOTIF and validation work
  products and the case records; the WP-C-05 and WP-C-06 counts come from the generator of WP-C-05 Figure 2-1.
- The figures of "Cybersecurity and ISO/SAE 21434" (`cyber-third-question.svg`, `cyber-one-threat.svg`,
  `cyber-more-than-safety.svg`, `cyber-how-hard.svg`, `cyber-risk-map.svg`, `cyber-goal-to-evidence.svg`, `cyber-meet.svg`,
  `cyber-after-release.svg`) are rendered by [`tools/wiki/cyber_animations.py`](../tools/wiki/cyber_animations.py): the
  risk map, attack-path factors and counts are read from WP-C-09, WP-C-10 and `hatara/`, and every other phrase is
  checked against its record. No figure shows how to carry out an attack.
- The figures of "AI safety and ISO/PAS 8800" (`ai-why.svg`, `ai-boundary.svg`, `ai-errors.svg`, `ai-input-space.svg`,
  `ai-requirements.svg`, `ai-data.svg`, `ai-testing.svg`, `ai-layers.svg`) are rendered by
  [`tools/wiki/ai_animations.py`](../tools/wiki/ai_animations.py): requirement statuses, input-space dimensions and counts
  are read from WP-C-11 and WP-W-10, and every other phrase is checked against its record.
- The figures of "ASPICE: is the process capable?" (`aspice-question.svg`, `aspice-v.svg`, `aspice-rating.svg`,
  `aspice-baseline.svg`, `aspice-trace.svg`, `aspice-together.svg`, `aspice-plan.svg`) are rendered by
  [`tools/wiki/aspice_animations.py`](../tools/wiki/aspice_animations.py): levels, targets, improvement actions, trace
  coverage and the activity count are read from WP-M-13, the trace map and the process model.
- The figures of "Integrated standards: one system, not five" (`integrated-silos.svg`, `integrated-joins.svg`,
  `integrated-coverage.svg`, `integrated-log.svg`, `integrated-mechanism.svg`, `integrated-case.svg`) are rendered by
  [`tools/wiki/integrated_animations.py`](../tools/wiki/integrated_animations.py): lanes, interfaces, register coverage,
  the hazard log, trace lanes and case status are read from their records.
- Standard GitHub Markdown, including alerts (`> [!IMPORTANT]`) and tables.

Check locally before opening a pull request:

```sh
python3 -m unittest discover -s tools/wiki -p 'test_*.py'
python3 tools/wiki/build_wiki.py --out build/wiki
```

## One-time setup

GitHub creates the wiki repository only when a first page is created from the repository's **Wiki** tab. Until
that is done, the publish job fails at "Clone the wiki" and says so. Any first page will do; the first sync
replaces it.
