#!/usr/bin/env python3
"""Draw WP-C-11 Figure 6-1, the AI safety requirements and how far they have got (fig-c11-6-1-air-map.svg).

One tile per AI safety requirement AIR-nn of WP-C-11 §6, in the seven groups of §6.1–§6.7, each with the component it
applies to, its statement and its status. Status, from the first words of the "Status / evidence" cell:

  not evaluated  "Not evaluated…": the requirement needs evaluation data that does not exist yet
  not met        "Not met…", "Not implemented…", "Not started…"
  partly         "Partially…", "Partial…", and the three statuses listed in PARTLY (each says something holds
                 only in part); any other start fails the build so a new status is classified on purpose

    python3 fig_c11_airs.py            # write the SVG
    python3 fig_c11_airs.py --check    # fail if §6 cannot be read or the SVG is stale

Standard library only. Drawing helpers come from ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-11-ai-system-definition-and-safety-requirements.md"
OUT = "fig-c11-6-1-air-map.svg"
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, t, wrap, header, svg_doc  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

STATUS = {"eval": ("not evaluated", "#475569", "#F1F5F9"), "not": ("not met", "#B42318", "#FEF2F2"),
          "partial": ("partly", "#B45309", "#FFFBEB")}
# Statuses that hold only in part, quoted from their first words in §6.
PARTLY = ("Process defined in WP-M-10", "Holds by construction at baseline for the CAN path",
          "Default releases exclude it")


class AirError(ValueError):
  pass


def _cells(ln: str) -> list[str]:
  return [c.strip() for c in ln.strip()[1:-1].split("|")]


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").replace("**", "")


def classify(status: str) -> str:
  s = _plain(status).strip()
  if s.startswith("Not evaluated"):
    return "eval"
  if s.startswith(("Not met", "Not implemented", "Not started")):
    return "not"
  if s.startswith(("Partially", "Partial")) or s.startswith(PARTLY):
    return "partial"
  raise AirError(f"cannot classify status {s[:60]!r}; add it to PARTLY or reword it")


def parse(md: str) -> list[tuple[str, list[dict]]]:
  m = re.search(r"^## 6\. .*?$(.*?)(?=^## \d+\. )", md, re.M | re.S)
  if not m:
    raise AirError("WP-C-11 §6 not found")
  groups: list[tuple[str, list[dict]]] = []
  for block in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
    title = block.splitlines()[0].strip()
    reqs = []
    for ln in block.splitlines():
      if ln.startswith("| AIR-"):
        c = _cells(ln)
        if len(c) != 6:
          raise AirError(f"{c[0]}: {len(c)} cells, expected 6")
        reqs.append({"id": c[0], "text": _plain(c[1]).replace(" (TBC)", ""), "comp": _plain(c[2]),
                     "status": classify(c[5])})
    groups.append((title, reqs))
  if not any(r for _, r in groups):
    raise AirError("§6 has no AIR rows")
  return groups


def figure(groups) -> str:
  W, COLS, GAP = 1280, 4, 10
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  TH = 96
  n = sum(len(r) for _, r in groups)
  body = header(W, "Figure 6-1 · The AI safety requirements and how far they have got",
                f"The {n} AI safety requirements of §6 in their seven groups, each with the component it applies to and "
                "its status at the baseline", "WP-C-11 §6", "")
  y = 104
  for title, reqs in groups:
    rows = (len(reqs) + COLS - 1) // COLS
    bh = 34 + rows * (TH + GAP)
    body.append(f'<rect x="30" y="{y}" width="{W - 60}" height="{bh}" rx="10" fill="#F8FAFC" stroke="#CBD5E1"/>')
    body.append(t(44, y + 22, title, 13, INK, 700))
    for i, r in enumerate(reqs):
      x = 40 + (i % COLS) * (tw + GAP)
      ty = y + 32 + (i // COLS) * (TH + GAP)
      lab, stroke, fill = STATUS[r["status"]]
      body.append(f'<rect x="{x:g}" y="{ty}" width="{tw:g}" height="{TH}" rx="8" fill="#FFFFFF" stroke="#CBD5E1"/>')
      body.append(f'<rect x="{x:g}" y="{ty}" width="5" height="{TH}" rx="2" fill="{stroke}"/>')
      body.append(t(x + 14, ty + 19, r["id"], 12, INK, 700))
      comp = r["comp"] if hf.text_w(r["comp"], 9.5) < tw - 170 else r["comp"].split(" (")[0].split(",")[0]
      body.append(t(x + 72, ty + 19, comp, 9.5, "#5B21B6", 700))
      cw = hf.text_w(lab, 9.5, True) + 14
      body.append(f'<rect x="{x + tw - cw - 8:g}" y="{ty + 7}" width="{cw:.1f}" height="17" rx="8.5" fill="{fill}" stroke="{stroke}"/>')
      body.append(t(x + tw - cw / 2 - 8, ty + 19, lab, 9.5, stroke, 700, "middle"))
      lines = wrap(r["text"], tw - 24, 10.5)
      for j, ln in enumerate(lines[:4]):
        body.append(t(x + 14, ty + 38 + 13.5 * j, ln + ("…" if j == 3 and len(lines) > 4 else ""), 10.5, INK))
    y += bh + 12
  y += 10
  counts = {k: sum(1 for _, rs in groups for r in rs if r["status"] == k) for k in STATUS}
  lx = 40
  for k, (lab, stroke, fill) in STATUS.items():
    s = f"{lab} ({counts[k]})"
    body.append(f'<rect x="{lx}" y="{y - 12}" width="30" height="16" rx="8" fill="{fill}" stroke="{stroke}"/>')
    body.append(t(lx + 38, y, s, 11))
    lx += 38 + hf.text_w(s, 11) + 22
  body.append(t(lx, y, "None is met yet. Not evaluated: it needs LionDriver evaluation data, which does not exist yet.", 11, MUTED))
  y += 20
  body.append(t(40, y, "Values marked TBC in §6 are left out of the tiles; they are confirmed through WP-V-02 (OI-2). Components: "
                "AI-1 driving model, AI-2 big driving model (excluded), AI-3 driver monitoring model.", 11, MUTED))
  extra, y = terms.svg_footer(body, 40, y + 20, W - 80)
  body += extra
  body.append(t(W - 40, y + 6, "Generated by fig_c11_airs.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = (f"{n} AI safety requirements of WP-C-11 §6 by group. " + " ".join(
    f"{title}: " + ", ".join(f"{r['id']} ({STATUS[r['status']][0]})" for r in reqs) + "." for title, reqs in groups))
  return svg_doc(W, h, "Figure 6-1. The AI safety requirements and how far they have got (WP-C-11 §6)", desc, body)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except AirError as e:
    print(f"fig_c11_airs: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/02-concept/figures/{n} is stale; run fig_c11_airs.py", file=sys.stderr)
    if not stale:
      print(f"fig_c11_airs: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/02-concept/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
