# Interactive 3D pages

> **Synthetic data (DSR-12). Design aid, no evidence credit.** Interactive pages that show what the simulation
> track's models compute, as a machine you can turn, cut open, take apart and break. They explain; they prove nothing.

Each page is one HTML file. Open it in a browser (it fetches three.js 0.170 and its fonts from their CDNs). Drag to
turn it, use the slider, and try the buttons: **Cut away**, **Explode**, **X-ray**, **Slow**, **Labels** and the
page's break. **How it is computed** says where every number comes from.

| Page | What it shows | Its numbers come from |
|---|---|---|
| [`comma3x.html`](comma3x.html) | The comma 3X hanging from its mount under the Corolla's windshield. The device box, board, SoC, heat spreader, panda MCU, fan and road cameras are all inside. The slider sets the cabin air at the mount; **Stall the fan** switches to the fan-stalled results. The SoC and MCU are coloured by temperature. | The device heat model ([`results/mcu-heat.json`](../results/mcu-heat.md), [thermal README §2.2](../thermal/README.md#22-the-safety-mcu-next-to-the-soc-dfi-04-tsr-509)); its sizes from [`thermal/params.yaml`](../thermal/params.yaml) |

![The comma 3X cut open under the windshield: the housing's section faces in red, the heat spreader and the SoC inside, labels for the fan at 100 %, the SoC at 81 °C and the panda MCU junction at 68 °C; on the right the hottest SoC point, 81 °C at 35 °C cabin air, with the host's 96 °C limit](figures/comma3x-poster.webp)

*The comma 3X page, cut open with labels, at 35 °C cabin air.*

## Rules

The pages are built with the [Machine Skill](../../../.claude/skills/machine/VENDORED.md) (tool TL-57), a Claude Code
skill vendored at upstream commit `e0bd066`. LionDriver uses it as a presentation layer only:

1. **No second solver.** A page shows only numbers from committed, CI-checked results. [`build_pages.py`](build_pages.py)
   pastes them in, and the page interpolates and animates them. The skill's own small solvers are not used for any number.
2. **Stamped.** Every page carries "SYNTHETIC (DSR-12) · design aid, no evidence credit". Its pills say the same.
3. **No films in git.** The skill's recorder makes MP4 films. They go to Actions artifacts or release assets. This
   folder's `.gitignore` keeps them out.
4. **No licensed mesh.** Geometry is built from code, at the sizes the models use.

## How a page is built

- [`page.html`](page.html): the shared shell, with the stamp, the pinned three.js import map, and markers for the
  kit, the data and the script.
- `<name>.js`: the page's machine (parts, materials, slider, labels, break), written to the skill's `SKILL.md`. It
  reads its numbers from `D`.
- [`build_pages.py`](build_pages.py): reads the results for each page and pastes the vendored kit, the data and the
  script into the shell. It writes `<name>.html`.

## Checks (CI job "simulation interactive pages")

| Check | Catches |
|---|---|
| `build_pages.py --check`: each committed page equals a fresh build | a page left behind when its results change |
| The same: every vendored skill file matches `SHA256SUMS` | a local edit to the vendored skill |
| [`check_pages.mjs`](check_pages.mjs): each page opens headless in Chromium with no page error | a broken page |
| The same: the synthetic stamp is on the page | a page without its label |
| The same: at 8 settings the page's numbers equal the results file, interpolated independently in the checker (an added 1 K fails all 8) | wrong data wiring |

```sh
python3 assurance/sim/interactive/build_pages.py                 # rebuild after the results or a page script change
npm i --no-save --prefix assurance/sim/interactive playwright@1.56.1
node assurance/sim/interactive/check_pages.mjs
```

Stills and films use the skill's own scripts (`.claude/skills/machine/scripts/shot.mjs` and `record.mjs`, which need
Playwright and ffmpeg). Call `__ld.settle()` before a still, so the eased display shows the results' value.
