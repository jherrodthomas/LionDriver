#!/usr/bin/env python3
"""Draw <WP-ID> Figure <N-n>, <what it shows in one line> (<fig-xx-n-n-slug>.svg).

<Two or three lines: what the chart shows, where every number comes from (the results file and its keys, or the
source table and §), and what fails the build. Say what it is NOT: synthetic results earn no evidence credit.>

Results against a required value, one bar per result on one linear axis, the requirement as a dashed line. As it
stands it reads ../sim/results/crest.json (sight over a hill crest against the distance to stop from 110 km/h).
Template from .claude/skills/assurance-chart; replace every <...> and the CONFIG block, then delete this line.

    python3 fig_xx_topic.py            # write the SVG next to this file
    python3 fig_xx_topic.py --check    # fail if the source changed shape or the SVG is stale

Standard library only. Output is deterministic: fixed rounding, keys in CONFIG order, no dates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "assurance" / "trace").is_dir())
sys.path.insert(0, str(REPO / "assurance" / "01-management" / "figures"))
from figkit import FAINT, GREY_BG, HAIR, INK, MUTED, RED, RED_BG, header, legend, line, rect, svg, text
sys.path.insert(0, str(REPO / "assurance" / "trace" / "tools"))
import terms

# ---------------------------------------------------------------- CONFIG: the source and what to read from it
SOURCE = REPO / "assurance" / "sim" / "results" / "crest.json"     # <results JSON written by a study script>
CASE = ("cases", "110")                                             # <path to the record inside the JSON>
SYNTHETIC = "Synthetic (DSR-12)"   # the JSON's "about" must start with this; None for real, recorded data
RESULTS_KEY, REQUIRED_KEY = "sight_m", "need_at_110_m"
# Every key the source has, mapped to the label drawn. A new or missing key fails the build, so a changed study is
# looked at rather than drawn in by default.
RESULTS = {
  "driver_tail_lights": "Driver to tail lights",
  "camera_tail_lights": "Camera to tail lights",
  "camera_roof": "Camera to roof",
  "radar_return": "Radar, 0.5 m high",
  "radar_return_low": "Radar, 0.4 m high",
}
REQUIRED = {   # key -> (label, drawn as the line the bars are compared with?)
  "aashto": ("design stopping sight", True),
  "driver_dry": ("driver, dry road", False),
  "driver_wet_3mm": ("driver, wet road", False),
  "item_rate": ("item's own braking", False),
}
UNIT = "m"
OUT = "fig-xx-1-1-chart-template.svg"                               # <fig-<wp>-<section>-<n>-<slug>.svg>
NUMBER, TITLE, REF = "1-1", "Sight over a 110 km/h crest", "<WP-ID §n>"
SUBTITLE = "Distance each sensor sees a stopped car, against the design stopping sight."
W = 640                                                             # phone first: 640 wide, chart text 12-13 px
# ---------------------------------------------------------------- end of CONFIG


class FigureError(Exception):
  """The source no longer has the shape this figure reads."""


def parse(raw: str) -> dict:
  """{about, results: [(key, label, value)], required: [(key, label, value, drawn)]}. Raises FigureError."""
  doc = json.loads(raw)
  about = doc.get("about", "")
  if SYNTHETIC and not about.startswith(SYNTHETIC):
    raise FigureError(f"'about' does not start with {SYNTHETIC!r}: label synthetic data, or set SYNTHETIC = None")
  rec = doc
  for k in CASE:
    if not isinstance(rec, dict) or k not in rec:
      raise FigureError(f"{'/'.join(CASE)} not found in {SOURCE.name}")
    rec = rec[k]
  out = {"about": about}
  for name, key, mapping in (("results", RESULTS_KEY, RESULTS), ("required", REQUIRED_KEY, REQUIRED)):
    got = rec.get(key)
    if not isinstance(got, dict) or not got:
      raise FigureError(f"{key} missing or empty")
    if set(got) != set(mapping):
      raise FigureError(f"{key}: keys {sorted(got)} differ from CONFIG {sorted(mapping)}; map them on purpose")
    rows = []
    for k, lab in mapping.items():
      v = got[k]
      if not isinstance(v, (int, float)) or v < 0:
        raise FigureError(f"{key}.{k} = {v!r} is not a non-negative number")
      rows.append((k, *lab, float(v)) if isinstance(lab, tuple) else (k, lab, float(v)))
    out[name] = rows
  if sum(1 for r in out["required"] if r[2]) != 1:
    raise FigureError("exactly one REQUIRED entry is the line the bars are compared with")
  return out


def halo(el: str) -> str:
  """A white outline under a label, so a grid or required line behind it does not cut through the text."""
  return el.replace("<text ", '<text stroke="#FFFFFF" stroke-width="4" stroke-linejoin="round" paint-order="stroke" ', 1)


def num(v: float) -> str:
  return f"{v:.0f} {UNIT}"


def draw(d: dict) -> str:
  ref_label, ref = next((lab, v) for _k, lab, drawn, v in d["required"] if drawn)
  body = header(W, NUMBER, TITLE, SUBTITLE, REF)
  y = 104
  if SYNTHETIC:
    body.append(text(40, y, f"{SYNTHETIC} · design aid, no evidence credit", size=13, fill=RED, weight=700))
    y += 28
  leg, _ = legend(40, y, [(GREY_BG, MUTED, "result"), (RED_BG, RED, f"short of the {ref_label}"),
                          ("#FFFFFF", INK + " dashed", "required")])
  body += leg
  x0, x1 = 196, W - 64
  top = max(v for *_r, v in d["results"] + d["required"])
  step = 50 if top <= 400 else 10 ** len(str(int(top))) // 10
  hi = (int(top // step) + 1) * step

  def X(v: float) -> float:
    return x0 + v / hi * (x1 - x0)

  y += 22
  rows_top, bar_h, gap = y + 8, 20, 10
  y_end = rows_top + len(d["results"]) * (bar_h + gap)
  for t in range(0, hi + 1, step):   # recessive grid, one axis, the unit on the last tick
    body.append(line(X(t), rows_top - 4, X(t), y_end, stroke=HAIR, sw=1))
    body.append(text(X(t), y_end + 14, f"{t} {UNIT}" if t == hi else f"{t}", size=12, fill=MUTED, anchor="middle"))
  body.append(line(X(ref), rows_top - 8, X(ref), y_end, stroke=INK, sw=1.6, dash="5 4"))   # under the bars
  body.append(text(X(ref), rows_top - 12, f"{ref_label} {num(ref)}", size=12.5, fill=INK, anchor="middle", weight=600))
  for _k, lab, v in d["results"]:
    short = v < ref
    body.append(text(x0 - 10, y + 15, lab, size=13, fill=INK, anchor="end"))
    body.append(rect(x0, y, X(v) - x0, bar_h, fill=RED_BG if short else GREY_BG, stroke=RED if short else MUTED,
                     rx=4, sw=1.2))
    note = f"{num(v)} · short by {num(ref - v)}" if short else num(v)
    body.append(halo(text(X(v) + 6, y + 15, note, size=12.5, fill=RED if short else INK, weight=600 if short else "")))
    y += bar_h + gap
  y = y_end + 42
  others = [f"{lab} {num(v)}" for _k, lab, drawn, v in d["required"] if not drawn]
  if others:
    body.append(text(40, y, "Also needed to stop: " + "; ".join(others[:2]) + (";" if others[2:] else "."),
                     size=12.5, fill=MUTED))
    for i in range(2, len(others), 2):
      y += 18
      body.append(text(40, y, "; ".join(others[i:i + 2]) + ("." if i + 2 >= len(others) else ";"), size=12.5,
                       fill=MUTED))
    y += 26
  foot, y = terms.svg_footer(body, 40, y, W - 80, size=12)
  body += foot
  body.append(text(40, y + 6, f"From {SOURCE.relative_to(REPO).as_posix()} by {Path(__file__).name}; " +
                   "CI fails if it is stale.", size=11, fill=FAINT))
  desc = (f"{SYNTHETIC + ', no evidence credit. ' if SYNTHETIC else ''}{TITLE}. Required: {ref_label} {num(ref)}. " +
          "; ".join(f"{lab} {num(v)}{' (short)' if v < ref else ''}" for _k, lab, v in d["results"]) + ".")
  return svg(W, int(y + 24), f"Figure {NUMBER} · {TITLE}", desc, body)


def build() -> dict[str, str]:
  return {OUT: draw(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"{Path(__file__).stem}: {e}", file=sys.stderr)
    return 1
  rel = HERE.relative_to(REPO).as_posix()
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"{rel}/{n} is stale; run {Path(__file__).name}", file=sys.stderr)
    if not stale:
      print(f"{Path(__file__).stem}: {len(outputs)} figure(s) current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote {rel}/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
