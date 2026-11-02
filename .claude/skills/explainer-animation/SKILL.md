---
name: explainer-animation
description: Add or change one of LionDriver's animated SVG explainers, the looping pictures on the GitHub wiki pages (requirement anatomy, fault trees, the safety case, hazard to test, SOTIF, cybersecurity, AI, ASPICE, ASIL decomposition, CAN and end-to-end, how LionDriver works) rendered by tools/wiki/*_animations.py and infographics.py at every wiki sync. Each one loops with CSS and no script, shows its final frame under reduced motion, quotes every on-screen phrase from a record and checks it at render time (problems()), reads its numbers and statuses from the records, and is wired into tools/wiki/build_wiki.py with a test. Use it whenever a wiki page or explainer needs an animation, "a moving picture", "show it step by step", "animate how X works", a new wiki figure, or when the wiki build fails with "drawn phrase no longer in the source" or "stands on ... which is gone", even if nobody names the module. For committed work-product figures use assurance-figure; for cars on a road use road-scene.
---

# Explainer animation

The wiki explains; it never claims. Its animations are built from the records at every sync of the
[wiki workflow](../../../.github/workflows/wiki.yaml), written next to the pages and **never committed**. A phrase or
number that moves in a record moves in the picture, and a phrase that disappears from its record fails the build.
**The module is the source, the record is the truth, and the wiki build refuses to animate old wording.**

Read `references/conventions.md` once per session before writing: it has the anatomy of a module, the module map
(page, records, sentinel), the test checklist and the GitHub vs claude.ai notes. This file is the rules and recipe.

## Is it this skill?

| You need | Use |
|---|---|
| A looping explainer on a `wiki/*.md` page, rendered at sync | this skill |
| A static wiki infographic from a register (counts, bars) | this skill, but `tools/wiki/infographics.py` (`--out` / `--check DIR`) |
| A figure in a work product, README or decision card (committed SVG, terms footer) | `assurance-figure` |
| The red car on a road (hazardous event, FTTI, triggering condition) | `road-scene` |

## The rules

1. **No script, CSS first.** Motion comes from `animations.Timeline(loop)`: `tl.show(t_in, t_out)` returns a class
   with its own `@keyframes`, and `animations.svg()` puts them in one `<style>`. No `<script>`, no `<image>`, no
   external font or stylesheet; the font stack falls back to system fonts. SMIL is used only by
   `how_animations.dot()` for a dot travelling a path, and that dot is transient. Loops run 14 to 34 s; most are 30.
2. **Reduced motion shows the final frame.** `svg()` adds the media query: animation off, `.tr` hidden, `.fin` shown.
   Every timed group gets `tr` (transient: a caption, a "before" state, a moving token) or `fin` (part of the end
   picture). A bare `tl.show()` class with no `tr`/`fin` stays visible under reduced motion, so use it only for
   something that belongs in the end state. **The end frame alone must tell the whole story.**
3. **Quote, don't paraphrase.** Every on-screen phrase that states a fact about LionDriver (a requirement clause,
   an ID, a status, a record's wording) is tied to the record it comes from in a `SOURCES` list of
   `(path, phrase)` (or derived from what is drawn, as `animations.sources()` does) and checked by `problems()`
   after `animations.norm()`. Only joining words, punctuation and the explainer's own plain-language captions are
   the module's. The general part of a lesson (what the standard says in general) quotes nothing and says so.
4. **Read numbers and statuses, never type them.** A `data(root)` function parses counts, statuses, budgets and
   metrics from the records (`dec_animations.data()`: SPFM against its target, IR-01…IR-10, the DEC records).
   `problems()` re-checks that what the picture asserts still follows from them (a met target, a new IR, an
   "Applied" decomposition each raise a problem). Reuse a work-product generator's computation instead of
   re-deriving it (`sotif_animations` imports `fig_c05_four_areas`).
5. **Fail with a sentence.** A problem line names the record, the phrase or value, and the figure that stands on it:
   `"{path}: the ASIL decomposition page stands on {phrase!r}, which is gone; update the figure"`. Parsing errors
   (`ParseError`, `ValueError`, `OSError`) are caught in `problems()` and reported, never swallowed into a default.
6. **Say what it is.** A worked picture that is not the real state is labelled on the figure ("ILLUSTRATION",
   `h2t-mechanism.svg`, `case-defeaters.svg`). An open item stays open in the picture ("not implemented", "gap",
   "Proposed"). No "mock-up". Cybersecurity figures never show how to carry out an attack. A wiki figure is never
   evidence and never states a safety claim on its own authority (`wiki/README.md`).
7. **Accessible.** `svg()` gives `role="img"`, `<title>` and a `<desc>` that tells the whole animation in words,
   with the record's values in it (built from `data`, not typed). The page's alt text starts "Animated:" and
   states what the end frame shows.
8. **House look.** Import colours and helpers from `animations.py` (`NAVY`, `MID`, `LIGHT`, `GRN`, `RED`, `RED_BG`,
   `W` = 720, `t`, `g`, `stick`, `svg`, `norm`), boxes and captions from `how_animations` (`box`, `line`, `caption`)
   or `fta_animations` (`blk`, `wire`). Don't copy them; a missing helper goes into the module that owns the style.

## Recipe: add a new animation

Copy the shape of **`tools/wiki/dec_animations.py`** and **`tools/wiki/test_dec_animations.py`**: records as path
constants, `SOURCES`, `data()`, `problems()`, one function per figure, `render()` / `write_all()` / `main()`, and
tests that edit a copied record and expect the problem. For a page with no numbers, `p7_animations.py` is the
smallest; for statuses read from a requirement list, `comms_animations.py`.

1. Read the wiki page and the records it explains. Write the docstring first: each SVG name and what it shows,
   which record each phrase and number comes from, and that the build fails when one changes.
2. Create `tools/wiki/<topic>_animations.py`. `NAMES` lists the SVGs with a page prefix (`dec-…`, `comms-…`); a name
   must be unique across all modules, since every one is written into the same folder. Draw each figure at
   `W` = 720 wide, with the title (about 23 px bold) and subtitle (14 to 15 px, `MID`) placed as in the file you
   copied, using `Timeline`, `tr`/`fin`, and the shared helpers.
3. Add a page's figure to a new page section, or a new page with its `_Sidebar.md` link, embedding it as
   `![Animated: <what the end frame shows>](dec-idea.svg)` and a line naming the module that draws it.
4. Wire it into `tools/wiki/build_wiki.py` in four places: the `import`, the generated-figure test in `rewrite()`
   (`path in <module>.NAMES`), and in `build()` both `problems += <module>.problems(root)` and
   `<module>.write_all(out, root)`, each behind `if (root / <module>.<SENTINEL>).exists():` (the record the module
   needs most, so a test tree without it still builds). Update the module list in the build docstring.
5. Add the module to the figure list in `wiki/README.md` ("The figures of … are rendered by …").
6. Write `tools/wiki/test_<topic>_animations.py`; the checklist is in `references/conventions.md`. No workflow edit:
   `wiki.yaml` discovers every `tools/wiki/test_*.py`.
7. Run and **look** (next section), then the checks.

## Run, look, check

```bash
python3 tools/wiki/dec_animations.py --check            # exit 1 and one line per problem; writes nothing
python3 tools/wiki/dec_animations.py --out <scratchpad>/dec
grep -o 'animation:k1 [0-9.]*s' <scratchpad>/dec/dec-idea.svg      # the loop length L
node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png <scratchpad>/dec/dec-idea.svg --at 3
node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png <scratchpad>/dec/dec-idea.svg --at 23 --width 390
```

Then Read the PNGs. Without `--at` the preview shows CSS animations at t = 0 (mostly empty), so always pass `--at`.
Look at a moment inside each step, and at **0.95 × L**: the keyframes hold every `fin` group until 96 %, so that
frame equals the reduced-motion final frame. Check that it tells the whole story on its own, that nothing overlaps
(captions that replace each other share a y), that `tr` items are gone, and the 390 px phone width is readable.

```bash
python3 tools/wiki/test_dec_animations.py               # the module's tests
python3 tools/wiki/test_build_wiki.py                   # links, sidebar, and wiki/ checks clean
python3 -m unittest discover -s tools/wiki -p 'test_*.py'   # what CI runs (about a minute; needs PyYAML)
python3 tools/wiki/build_wiki.py --out <scratchpad>/wiki    # the full build, every page and figure
```

The wiki workflow runs no linter, and `tools/wiki` is not ruff-clean today (long lines, mostly), so don't reformat
the existing modules in passing; keep a new module free of new kinds of warning.

Without `--out`, `build_wiki.py` only checks. `infographics.py` differs: `--out DIR` writes and `--check DIR` fails
when DIR's copies differ from the records.

## When a record changes

The wiki build fails with the problem line. Find the module from the record name
(`grep -l "WP-A-01" tools/wiki/*_animations.py`), read what the record now says, and change the drawing and its
`SOURCES` phrase together, on purpose. Never loosen `problems()`, shorten a quoted phrase until it matches, or
type the new number in. If the record changed what the picture means (a status, a count, a verdict), change the
picture's claim, not only its text, and the test that pins it.
