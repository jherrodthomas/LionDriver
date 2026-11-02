# Charts on decision cards

A card's figure is `assurance/01-management/decisions/figures/dq-NNN.svg`, named by the entry's `figure:` with a
`caption:` (`check_decisions.py` fails on a missing file or caption). `build_inbox.py` inlines the SVG into the
inbox page, so the figure **uses the page's tokens and brings no `<style>` of its own** (a `<style>` inside inline
SVG would restyle the whole page). Today every card chart is hand-written; there is no generator and no `--check`.

## What a card chart must do

- **Show the difference between the options**, on one axis, one line or bar per option, labelled with the option
  letter and the number that decides it (`A · 15 s, 230 m`). If the options do not differ on a measurable axis, it
  is not a chart; use a sketch or nothing.
- The recommended option is `s-acc` / `var(--accent)` and heaviest (3.5 px); today's behaviour is `s-muted`, dashed;
  the option with the worst outcome is `s-bad`. Text uses `s-ink` / `s-muted`; lines use `var(--line)`.
- An upper-case title row (`font-size="12" font-weight="600" letter-spacing=".06em"`, `s-muted`), then the
  option key line, as in `dq-424.svg`. `viewBox="0 0 640 H"`, no `width`/`height` (the page sizes it, min 520 px).
- `<title id="…">` says what each option does, numbers included. Simulated numbers carry "synthetic, no evidence
  credit" in the chart (see `dq-404.svg`, from the what-if run of `assurance/sim/plant/silent_stall.py`).
- Every number comes from a record the entry's `sources:` names. If it came from a study run, say which run in the
  caption or the closing line, and prefer adding the chart to that study's own `figure()` so it is regenerated.

## Look at it

The card SVG has no colours of its own, so wrap it with the inbox tokens before rendering:

```bash
python3 - <scratchpad>/card assurance/01-management/decisions/figures/dq-NNN.svg <<'EOF'
import pathlib, re, sys
sys.path.insert(0, "assurance/01-management/decisions")
import build_inbox
css = build_inbox.TEMPLATE
root = re.search(r":root\{.*?\}", css, re.S).group(0).replace(":root", "svg")
toks = re.search(r"/\* SVG tokens.*?\n((?:\.s-.*\n)+)", css).group(1)
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
for f in sys.argv[2:]:
    svg = pathlib.Path(f).read_text(encoding="utf-8")
    style = "<style>" + root + toks + "svg{font-family:var(--font-body)}</style>"
    (out / pathlib.Path(f).name).write_text(re.sub(r"(<svg\b[^>]*>)", lambda m: m.group(1) + style, svg, count=1))
EOF
node .claude/skills/assurance-figure/scripts/preview.mjs <scratchpad>/png <scratchpad>/card/dq-NNN.svg --width 390
```

Then Read both PNGs. This is the light theme; the page also has a dark one, so use tokens only, never a hex.
Then rebuild the inbox (`build_inbox.py --out <scratchpad>/inbox.html`) and republish it as the `decision-inbox`
skill says.

Checked on `dq-424.svg` (2026-11-02): the end label `B · 25 s, 390 m` runs past the 640 viewBox and is cut off, and
`C · 10 s, 150 m` sits on line A. Keep end labels inside `x + text width ≤ 640` and clear of the other lines.
