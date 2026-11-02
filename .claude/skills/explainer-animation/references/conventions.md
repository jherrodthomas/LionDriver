# Explainer animation: conventions in detail

Read with `SKILL.md`. Everything here is read from the modules in `tools/wiki/`; when this file and a module
disagree, the module wins and this file is fixed.

## Anatomy of a module

Every `tools/wiki/<topic>_animations.py` has the same parts, in this order (see `dec_animations.py`):

| Part | What it holds |
|---|---|
| Docstring | One line per SVG (name, what it shows), the records each part is read from, "the wiki build fails instead of showing old text", "loop with CSS; reduced motion shows the final frame", and `Usage: python3 tools/wiki/<topic>_animations.py [--out DIR] [--check]` |
| Imports | `sys.path.insert(0, str(HERE))`, then `from animations import ...  # noqa: E402` (and `how_animations` / `fta_animations` helpers) |
| `NAMES` | The SVG file names, page-prefixed, in render order |
| Record paths | Repository-relative `Path` constants (`A01 = A / "08-analyses" / "WP-A-01-asil-decomposition.md"`), always joined to a `root` argument so tests can point at a copied tree |
| Drawn content as data | Lists of tuples: what is drawn and, where it states a fact, the record and phrase it stands on (`SOURCES`, `OURS` in `p7_animations`, `ANATOMY` in `animations`) |
| `data(root)` | Parses the values the figures show (counts, statuses, budgets, metrics) with regexes on the record's section or table row; raises `ValueError` / `ParseError` with the record and what is missing |
| `problems(root)` | Returns a list of sentences: every `SOURCES` phrase still in its record (after `norm()`), and every claim the picture makes still follows from `data()`. Catches parse errors into a problem line |
| Drawing helpers | Only what the shared modules lack; colours as named constants at the top |
| One function per figure | Builds `b` (a list of SVG strings) with a `Timeline`; returns `svg(h, title, desc, tl, b)` |
| `render(root)` | `dict(zip(NAMES, (...), strict=True))` |
| `write_all(out, root)` | Writes each SVG into `out` (called by `build_wiki.build`) |
| `main(argv)` | `--out DIR` writes when there are no problems; `--check` only reports. Exit 1 on any problem, problems to stderr |

The base module `animations.py` owns the house look and the timing: `Timeline`, `t()` (text), `g()` (a group with
classes), `coloured()`, `legend()`, `pills()`, `stick()` (a stick figure), `svg()` and `norm()`. `how_animations.py`
adds `box`, `line`, `arrow`, `dot` (SMIL travelling dot, transient), `caption`; `fta_animations.py` adds `blk`,
`wire`, `gate`. Import them; don't copy.

## Timing

- `tl = Timeline(L)`; `tl.show(t_in)` fades in at `t_in` and holds to 96 % of the loop; `tl.show(t_in, t_out)` fades
  out at `t_out`. Each call adds one `@keyframes kN` rule and returns `kN`.
- Wrap with `g(tl.show(...) + " fin", items)` for the end picture and `+ " tr"` for anything that leaves.
- Captions that replace each other share one y and are each `tr` with back-to-back windows
  (`caption(tl, 0.4, 6.0, "...", 290)`); the last, summarising caption is `fin`.
- Give the reader about 2 s per new element and 4 to 6 s per caption; most loops are 30 s.
- Under reduced motion every `tr` is hidden and every `fin` shown, so the end frame must not need a `tr` element.

## Test checklist (`test_<topic>_animations.py`)

Copy the shape of `test_dec_animations.py`: a `copy_records(root)` helper that copies every record into a temporary
tree, and an `edit(root, path, old, new)` helper that asserts `old` is present before replacing it.

1. `problems()` on the real repository is `[]`.
2. The values `data()` reads are what the page says (`d["recs"]["DEC-01"] == "Proposed"`).
3. For each kind of claim the picture makes, edit a copied record so the claim no longer holds and expect a
   problem naming it (a reworded phrase, a changed status, a new row, a met or missed target).
4. Any internal consistency the drawing relies on (the decomposition schemes add up; split lines join back).
5. `render()` returns exactly `NAMES`; each SVG parses with `xml.dom.minidom`, has a non-empty `<title>` and
   `<desc>`, and contains `prefers-reduced-motion: reduce`; no "mock-up".
6. The figure shows the record's values (`f"{d['spfm']:g} % against {d['target']:g} %" in svg`).
7. `build_wiki.build(out=tmp)` returns `[]`, writes every name, and the built page contains `](<name>)` for each.

`python3 -m unittest discover -s tools/wiki -p 'test_*.py'` is the CI step in `.github/workflows/wiki.yaml` ("Build
tool unit tests"); then the job runs `build_wiki.py --out build/wiki` and uploads the result as an artifact, and on
a push to `liondriver-dev` the publish job pushes it to the GitHub wiki. PyYAML is installed in CI because
`case_animations`, `h2t_animations`, `hw_animations` and `integrated_animations` read YAML records.

## Module map

| Module | Wiki page | Main records | `build_wiki` sentinel |
|---|---|---|---|
| `animations.py` | Deriving and writing safety requirements | WP-S-02 TSR-307, TSR-516; the page itself | `TSC` |
| `fta_animations.py` | Building a fault tree | WP-A-04, WP-C-01, WP-S-02 | `FTA` |
| `case_animations.py` | What is a safety case? | `assurance/case-records/` | `CASE / "claims"` |
| `h2t_animations.py` | From hazard to test | WP-C-01…08, WP-S-02, software and hardware WPs, opendbc/panda when checked out | `C03` |
| `hw_animations.py` | Hardware safety and interference | `fmeda-sg001.yaml`, WP-H-03…05, WP-A-02 | `FMEDA` |
| `p7_animations.py` | After release | WP-S-06, WP-O-01, -02, -04, WP-S-02, WP-A-03 | `O02` |
| `sotif_animations.py` | SOTIF and ISO 26262 | WP-C-03…07, WP-V-01, -02, -04, case records; counts via `fig_c05_four_areas.py` | `C06` |
| `cyber_animations.py` | Cybersecurity and ISO/SAE 21434 | WP-C-09, WP-C-10, `hatara/`, WP-O-05, WP-K-03 | `C09` |
| `ai_animations.py` | AI safety and ISO/PAS 8800 | WP-C-11, WP-M-10, WP-W-10 | `C11` |
| `aspice_animations.py` | ASPICE process capability | WP-M-13, trace map, process model | `M13` |
| `integrated_animations.py` | Integrated standards | WP-M-00, process model, `ifr.yaml`, HARA, TARA | `REG` |
| `how_animations.py` | How LionDriver works | WP-S-02, -03, -04, TSR list, WP-W-09 | `W09` |
| `dec_animations.py` | ASIL decomposition | WP-A-01, WP-H-04, WP-S-02 | `A01` |
| `comms_animations.py` | CAN, CAN FD and end-to-end protection | WP-S-05, WP-S-04, TSR list | `S05` |
| `infographics.py` (static) | decision-register.svg, change-path.svg | `register.yaml`, `safety-relevant-paths.txt`, workflows | `register.yaml` |

## GitHub and claude.ai

- **On GitHub** (the wiki, or any Markdown page) the SVG is shown through `<img>`: scripts never run and GitHub
  strips inline `<svg>` from Markdown, but CSS animation and `prefers-reduced-motion` work. That is why the
  explainers are CSS-only, self-contained files with no external reference. A wiki page embeds a generated figure
  by bare name (`![Animated: …](dec-idea.svg)`); `build_wiki.rewrite()` accepts it only if the name is in a module's
  `NAMES`. A committed repository figure is embedded as `../path.svg` and rewritten to the raw file address.
- **In a claude.ai artifact** (an explainer page, a decision card on the inbox page) the same SVG can be inlined
  into the HTML as it is: it carries its own `<style>` and needs no script. Generate it with the module's `--out`
  into the scratchpad and inline the file, never a hand-edited copy, so the quoted phrases are the checked ones.
  Keep `role="img"`, the title and the desc. Load the `artifact-design` skill for the page around it; give the page
  its own dark theme rather than recolouring the SVG, whose `#FCFCFB` background is part of the figure.
- Wiki explainers are not committed and carry no terms footer; a figure that belongs in a work product is an
  `assurance-figure` generator instead, committed with `--check`, a test, a CI line and `terms.FIGURES`.
