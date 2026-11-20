#!/usr/bin/env python3
"""Figure 1 of the STM32H725 dossier: dependent failures inside the chip (ISO 26262-11 §4.7).

A matrix of the shared resources on the die (rows) against the mechanisms that watch the CPU (columns). Each cell is
coloured by whether one cause can disable the CPU and that mechanism together, with the one-line note from the record.
Everything is read from ../onchip-dfa.yaml; a cell whose basis names an MCU feature (MF-nn) must name one that exists in
../features.yaml.

Fails (FigureError) on a missing cause or check, a cell that is missing or extra, an unknown rating, a duplicate id,
a note too long for its cell, or a basis that names a feature the feature record does not have.

    python3 fig_h07_onchip_dfa.py            # write the SVG
    python3 fig_h07_onchip_dfa.py --check    # exit 1 when the record changed shape or the SVG is stale
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DOSSIER = HERE.parent
ASSURANCE = HERE.parents[3]
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
from figkit import (INK, MUTED, FAINT, LINE, CHIP, SW, SW_BG, GREEN, GREEN_BG, AMBER, AMBER_BG, RED, RED_BG,  # noqa: E402
                    text, rect, svg, header)
import terms  # noqa: E402

OUT = HERE / "fig-h07-semi-1-onchip-dfa.svg"
RATING = {"common": (RED, RED_BG, "common cause: needs an argument or a measure in WP-A-03"),
          "partial": (AMBER, AMBER_BG, "partial: note it and bound it"),
          "independent": (GREEN, GREEN_BG, "independent, or this mechanism is the monitor for that cause")}
NOTE_MAX = 30


class FigureError(Exception):
  pass


def load() -> tuple[dict, set[str]]:
  rec = yaml.safe_load((DOSSIER / "onchip-dfa.yaml").read_text(encoding="utf-8"))
  feats = yaml.safe_load((DOSSIER / "features.yaml").read_text(encoding="utf-8"))
  return rec, {f["id"] for f in feats["features"]}


def validate(rec: dict, feature_ids: set[str]) -> None:
  for k in ("checks", "causes"):
    if not rec.get(k):
      raise FigureError(f"onchip-dfa.yaml: '{k}' missing or empty")
  check_ids = [c["id"] for c in rec["checks"]]
  cause_ids = [c["id"] for c in rec["causes"]]
  for ids, what in ((check_ids, "check"), (cause_ids, "cause")):
    if len(set(ids)) != len(ids):
      raise FigureError(f"duplicate {what} id")
  for c in rec["causes"]:
    cells = c.get("cells") or {}
    if set(cells) != set(check_ids):
      raise FigureError(f"cause {c['id']}: cells {sorted(cells)} do not match the checks {sorted(check_ids)}")
    for k, cell in cells.items():
      if cell.get("rating") not in RATING:
        raise FigureError(f"cause {c['id']} / {k}: unknown rating {cell.get('rating')!r}")
      if not cell.get("note") or len(cell["note"]) > NOTE_MAX:
        raise FigureError(f"cause {c['id']} / {k}: note missing or longer than {NOTE_MAX} characters")
      for f in re.findall(r"MF-\d\d", cell.get("basis", "")):
        if f not in feature_ids:
          raise FigureError(f"cause {c['id']} / {k}: basis names {f}, which features.yaml does not have")


def build() -> str:
  rec, feature_ids = load()
  validate(rec, feature_ids)
  checks, causes = rec["checks"], rec["causes"]
  W = 1500
  b = header(W, "1", "STM32H725: what inside the chip can fail two things at once",
             "Each row is something shared on the die; each column a mechanism that watches the CPU. Red: one cause can "
             "disable the CPU and that mechanism together.", "ISO 26262-11 §4.7 · feeds WP-A-03")
  x0, y0, rh = 40, 104, 92
  lw = 260
  cw = (W - 80 - lw) / len(checks)
  b.append(text(x0, y0 + 30, "Shared cause ↓   mechanism →", 13, MUTED, "600"))
  for j, c in enumerate(checks):
    x = x0 + lw + j * cw
    b.append(rect(x + 4, y0, cw - 8, 46, fill=SW_BG, stroke=SW, sw=1.2, rx=8))
    b.append(text(x + cw / 2, y0 + 29, c["label"], 14, SW, "700", "middle"))
  counts = {k: 0 for k in RATING}
  for i, cause in enumerate(causes):
    y = y0 + 58 + i * rh
    b.append(rect(x0, y + 4, lw - 8, rh - 8, fill=CHIP, stroke=LINE, sw=1.2, rx=8))
    b.append(text(x0 + 16, y + 38, cause["label"], 16, INK, "700"))
    b.append(text(x0 + 16, y + 60, cause.get("detail", ""), 12, MUTED))
    for j, c in enumerate(checks):
      cell = cause["cells"][c["id"]]
      fg, bg, _ = RATING[cell["rating"]]
      counts[cell["rating"]] += 1
      x = x0 + lw + j * cw
      b.append(rect(x + 4, y + 4, cw - 8, rh - 8, fill=bg, stroke=fg, sw=1.6 if cell["rating"] == "common" else 1, rx=8))
      strong = cell["rating"] == "common"
      b.append(text(x + 16, y + 40, cell["note"], 13, fg if strong else INK, "600" if strong else ""))
      b.append(text(x + 16, y + 62, f"basis: {cell['basis']}", 11, MUTED))
  ly = y0 + 58 + len(causes) * rh + 22
  x = x0
  for k, (fg, bg, lab) in RATING.items():
    b.append(rect(x, ly, 22, 22, fill=bg, stroke=fg, sw=1.6, rx=4))
    b.append(text(x + 32, ly + 16, f"{lab} ({counts[k]})", 13, INK))
    x += 32 + len(lab) * 6.6 + 70
  ny = ly + 50
  b.append(text(x0, ny, "Drawn from the firmware at panda fd0a6a7 and the device header; cells whose basis is RM0468 still need ST's "
                "reference manual. AI-drafted (I0), not reviewed.", 12, FAINT))
  extra, yy = terms.svg_footer(b, x0, ny + 24, W - 80)
  n = sum(counts.values())
  return svg(W, int(yy + 14), "STM32H725 on-chip dependent failures",
             f"{len(causes)} shared causes against {len(checks)} mechanisms: {counts['common']} of {n} cells common cause, "
             f"{counts['partial']} partial, {counts['independent']} independent. Drawn from onchip-dfa.yaml.", b + extra)


def main(argv: list[str]) -> int:
  try:
    out = build()
  except (FigureError, KeyError) as e:
    print(f"fig_h07_onchip_dfa: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != out:
      print(f"{OUT.name} is stale; run fig_h07_onchip_dfa.py", file=sys.stderr)
      return 1
    print("fig_h07_onchip_dfa: 1 figure current")
    return 0
  OUT.write_text(out, encoding="utf-8")
  print(f"wrote {OUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
