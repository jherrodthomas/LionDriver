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
  generated source instead, or embed the badge from `assurance/case/badge.json`.
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
