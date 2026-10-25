#!/usr/bin/env python3
"""Draw WP-C-02 Figure 5-1, leaving the ODD (fig-c02-5-1-odd-exits.svg).

One row per ODD exit of WP-C-02 §5.2: whether the item detects it, what it does today, and what closes the gap (a
functional modification of WP-C-07, a driver task, or nothing because it is implemented). The rows are read from §5.2:

  detected  the first word of the "Detected by system?" cell: Yes, Partly or No (anything else fails the build)
  reaction  the "Current reaction" cell; "None…" is drawn as no reaction
  closes    the FM-nn named in the "Gap / proposal" cell, "Driver task", or "Implemented"

    python3 fig_c02_exits.py            # write the SVG
    python3 fig_c02_exits.py --check    # fail if §5.2 cannot be read or the SVG is stale

Standard library only. Drawing helpers come from ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-02-odd-and-intended-functionality.md"
OUT = "fig-c02-5-1-odd-exits.svg"
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, t, wrap, header, svg_doc  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

DETECT = {"yes": ("detected", "#0F766E", "#F0FDFA"), "partly": ("partly", "#B45309", "#FFFBEB"),
          "no": ("not detected", "#B42318", "#FEF2F2")}


class ExitError(ValueError):
  pass


def _cells(ln: str) -> list[str]:
  return [c.strip() for c in ln.strip()[1:-1].split("|")]


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").replace("**", "")


def parse(md: str) -> list[dict]:
  m = re.search(r"^### 5\.2 .*?$(.*?)(?=^### |^## )", md, re.M | re.S)
  if not m:
    raise ExitError("WP-C-02 §5.2 not found")
  rows = []
  for ln in m.group(1).splitlines():
    if not ln.startswith("| ") or ln.startswith(("| ODD exit", "|---")):
      continue
    c = _cells(ln)
    if len(c) != 4:
      raise ExitError(f"§5.2 row has {len(c)} cells: {ln[:40]}")
    word = re.match(r"(Yes|Partly|Not directly|No)\b", c[1])
    if not word:
      raise ExitError(f"cannot read 'Detected by system?' {c[1][:40]!r}")
    det = {"Yes": "yes", "Partly": "partly", "No": "no", "Not directly": "no"}[word.group(1)]
    gap = _plain(c[3])
    fms = re.findall(r"FM-\d\d", gap)
    if gap.startswith("Implemented"):
      closes = "implemented"
    elif fms:
      closes = " · ".join(dict.fromkeys(fms))
    elif gap.startswith("Driver task"):
      closes = "driver task"
    else:
      closes = re.split(r"[;.]", gap)[0]
    reaction = _plain(c[2])
    rows.append({"exit": _plain(c[0]), "detected": det, "detect_text": _plain(c[1]), "reaction": reaction,
                 "none": reaction.lower().startswith("none"), "closes": closes,
                 "driver": "Driver task" in gap})
  if not rows:
    raise ExitError("§5.2 has no rows")
  return rows


def figure(rows: list[dict]) -> str:
  W = 1280
  cols = [("WAY OUT OF THE ODD (§5.2)", 40, 330), ("DOES THE ITEM NOTICE?", 384, 250), ("WHAT IT DOES TODAY", 648, 300),
          ("WHAT CLOSES THE GAP", 962, 278)]
  body = header(W, "Figure 5-1 · Leaving the ODD: what the item notices and what it does",
                "Every way out of the ODD in §5.2, whether the item detects it, how it reacts today, and what closes the "
                "gap. There is no ODD monitor: where it does not notice, the driver must", "WP-C-02 §5", "")
  y = 112
  for lab, x, _ in cols:
    body.append(t(x, y, lab, 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  y += 10
  for i, r in enumerate(rows):
    lab, stroke, fill = DETECT[r["detected"]]
    ex = wrap(r["exit"], cols[0][2] - 12, 11.5, True)[:3]
    dt = wrap(re.sub(r"^(Yes|Partly|Not directly|No)[,:;]?\s*", "", r["detect_text"]), cols[1][2] - 104, 10)[:3]
    re_ = wrap(r["reaction"], cols[2][2] - 12, 10.5)[:3]
    cl = wrap(r["closes"], cols[3][2] - 12, 10.5)[:3]
    h = max(len(ex) * 15, len(dt) * 13, len(re_) * 14, len(cl) * 14, 18) + 16
    if i % 2 == 0:
      body.append(f'<rect x="32" y="{y}" width="{W - 64}" height="{h}" rx="6" fill="#F8FAFC"/>')
    for j, ln in enumerate(ex):
      body.append(t(cols[0][1], y + 19 + 15 * j, ln, 11.5, INK, 600))
    cw = hf.text_w(lab, 9.5, True) + 14
    body.append(f'<rect x="{cols[1][1]}" y="{y + 7}" width="{cw:.1f}" height="17" rx="8.5" fill="{fill}" stroke="{stroke}"/>')
    body.append(t(cols[1][1] + cw / 2, y + 19, lab, 9.5, stroke, 700, "middle"))
    for j, ln in enumerate(dt):
      body.append(t(cols[1][1] + cw + 8, y + 19 + 13 * j, ln, 10, MUTED))
    rc = "#B42318" if r["none"] else INK
    for j, ln in enumerate(re_):
      body.append(t(cols[2][1], y + 19 + 14 * j, ln, 10.5, rc, 700 if r["none"] and j == 0 else None))
    ccol = "#0F766E" if r["closes"] == "implemented" else ("#7C3AED" if r["closes"].startswith("FM-") else INK)
    for j, ln in enumerate(cl):
      body.append(t(cols[3][1], y + 19 + 14 * j, ln, 10.5, ccol, 700 if j == 0 else None))
    y += h
  y += 22
  counts = {k: sum(1 for r in rows if r["detected"] == k) for k in DETECT}
  lx = 40
  for k, (lab, stroke, fill) in DETECT.items():
    s = f"{lab} ({counts[k]})"
    body.append(f'<rect x="{lx}" y="{y - 12}" width="30" height="16" rx="8" fill="{fill}" stroke="{stroke}"/>')
    body.append(t(lx + 38, y, s, 11))
    lx += 38 + hf.text_w(s, 11) + 22
  body.append(t(lx, y, "Red reaction: nothing happens. Violet: a functional modification of WP-C-07 that would close it.", 11, MUTED))
  y += 20
  body.append(t(40, y, "Required at an exit the item detects (§5.3): a take-over request, never staying engaged indefinitely, and "
                "no engagement where it can tell it is outside. First such check: the highway speed floor (DQ-280).", 11, MUTED))
  extra, y = terms.svg_footer(body, 40, y + 20, W - 80)
  body += extra
  body.append(t(W - 40, y + 6, "Generated by fig_c02_exits.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = ("ODD exits of WP-C-02 §5.2: " + "; ".join(
    f"{r['exit']}: {DETECT[r['detected']][0]}, today {r['reaction']}, closed by {r['closes']}" for r in rows) + ".")
  return svg_doc(W, h, "Figure 5-1. Leaving the ODD (WP-C-02 §5)", desc, body)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except ExitError as e:
    print(f"fig_c02_exits: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/02-concept/figures/{n} is stale; run fig_c02_exits.py", file=sys.stderr)
    if not stale:
      print(f"fig_c02_exits: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/02-concept/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
