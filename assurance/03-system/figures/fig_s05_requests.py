#!/usr/bin/env python3
"""Draw WP-S-05 Figure 4-1, what the SoC can ask the safety MCU to do (fig-s05-4-1-control-requests.svg).

One tile per row of the WP-S-05 §4.2 control-request table, grouped by the treatment required in a release build with
a car safety mode active ("Required" column), each with its function, its effect on safety and whether it is gated at
the baseline. Required treatment, from the first word of the cell:

  reject, absent        refused   the request must not work in a car mode, or not exist in a release build
  only, keep, carry     limited   allowed under a stated condition
  allow                 allowed   harmless, or the reset it causes is itself safe
  —                     n/a       not handled by the application
Any other first word fails the build. A tile is "open" when its treatment is refused or limited and the baseline
gating cell says "none" for it or for one of its parameters: the SoC can use it today without any check.

    python3 fig_s05_requests.py            # write the SVG
    python3 fig_s05_requests.py --check    # fail if §4.2 cannot be read or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, SAFETY, AMBER, AMBER_BG, RED, RED_BG,  # noqa: E402
                                      GREY_BG, MONO, text, rect, svg, header)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-05-hsi-specification.md"
OUT = "fig-s05-4-1-control-requests.svg"
W = 1280

TREAT = [("refused", "Must be refused in a car mode, or absent from release builds", RED, RED_BG),
         ("limited", "Allowed only under a condition", AMBER, AMBER_BG),
         ("allowed", "Allowed: no effect on safety, or the effect is itself safe", MUTED, "#FFFFFF"),
         ("na", "Not handled by the application", FAINT, "#FFFFFF")]


class RequestError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("**", "").replace("`", "").strip()


def treatment(required: str) -> str:
  s = _plain(required).lower()
  for words, k in ((("reject", "absent"), "refused"), (("only", "keep", "carry"), "limited"), (("allow",), "allowed"),
                   (("—",), "na")):
    if s.startswith(words):
      return k
  raise RequestError(f"cannot classify required treatment {required[:50]!r}; extend treatment()")


def parse(md: str) -> list[dict]:
  m = re.search(r"^### 4\.2 .*?$(.*?)(?=^### )", md, re.M | re.S)
  if not m:
    raise RequestError("WP-S-05 §4.2 not found")
  rows = []
  for ln in m.group(1).splitlines():
    if not ln.startswith("| ") or ln.startswith("| Req") or ln.startswith("|---"):
      continue
    c = [x.strip() for x in ln.strip()[1:-1].split("|")]
    if len(c) != 6:
      raise RequestError(f"{c[0]}: {len(c)} cells, expected 6")
    t = treatment(c[4])
    gate = re.sub(r"\s*\(`?:[\d\-, ]+`?\)", "", _plain(c[3]))
    rows.append({"req": _plain(c[0]), "func": _plain(c[1]), "effect": re.sub(r"\s*\(:[\d\-, ]+\)", "", _plain(c[2])), "gate": gate,
                 "required": re.sub(r"\s*\(`?:[\d\-, ]+`?\)", "", _plain(c[4])), "tsr": _plain(c[5]), "treat": t,
                 "open": t in ("refused", "limited") and re.search(r"\bnone\b", gate.lower()) is not None})
  if not rows:
    raise RequestError("§4.2 has no rows")
  return rows


def figure(rows: list[dict]) -> str:
  n_open = sum(r["open"] for r in rows)
  out = header(W, "4-1", "What the SoC can ask the safety MCU to do",
               f"The {len(rows)} control requests of §4.2 by the treatment a release build needs in a car mode, each with "
               f"its effect and its gating at the baseline: {n_open} that must be refused or limited have no gate today",
               "WP-S-05 §4.2")
  COLS, GAP, TH = 4, 10, 112
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  y = 104
  for k, title, col, bg in TREAT:
    mine = [r for r in rows if r["treat"] == k]
    if not mine:
      continue
    nrow = (len(mine) + COLS - 1) // COLS
    bh = 40 + nrow * (TH + GAP)
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=12))
    out.append(text(46, y + 25, f"{title} ({len(mine)})", size=14, fill=col if k != "allowed" else INK, weight=700))
    for i, r in enumerate(mine):
      x = 40 + (i % COLS) * (tw + GAP)
      ty = y + 36 + (i // COLS) * (TH + GAP)
      stroke = RED if r["open"] else (col if k in ("refused", "limited") else FAINT)
      out.append(rect(x, ty, tw, TH, fill=bg if k in ("refused", "limited") else "#FFFFFF", stroke=stroke,
                      sw=2 if r["open"] else 1.2, rx=8, dash="5 3" if k == "na" else ""))
      codes = wrap(r["req"], tw - 110, 11, True)
      out.append(text(x + 12, ty + 19, codes[0] + ("…" if len(codes) > 1 else ""), size=11.5, weight=700, family=MONO))
      chip, cc, cb = (("no gate today", RED, "#FFFFFF") if r["open"] else
                      ("gated today", AMBER, "#FFFFFF") if k in ("refused", "limited") else (None, None, None))
      if chip:
        cw = len(chip) * 5.9 + 14
        out.append(rect(x + tw - cw - 8, ty + 7, cw, 17, fill=cb, stroke=cc, sw=1.1, rx=8.5))
        out.append(text(x + tw - cw / 2 - 8, ty + 19, chip, size=9.5, fill=cc, weight=700, anchor="middle"))
      yy = ty + 38
      for ln in wrap(r["func"], tw - 24, 10.5, True)[:2]:
        out.append(text(x + 12, yy, ln, size=10.5, weight=600))
        yy += 13.5
      for ln in wrap(r["effect"], tw - 24, 10)[:2]:
        out.append(text(x + 12, yy, ln, size=10, fill=MUTED))
        yy += 13
      foot = f"today: {r['gate']}" if k != "allowed" else f"TSR {r['tsr']}" if r["tsr"] not in ("—", "") else ""
      if k in ("refused", "limited"):
        foot = f"today: {r['gate']} · needed: {r['required']}"
      fl = wrap(foot, tw - 24, 9.5)
      for j, ln in enumerate(fl[:2]):
        out.append(text(x + 12, ty + TH - 24 + j * 12 + (12 if len(fl) == 1 else 0), ln + ("…" if j == 1 and len(fl) > 2 else ""),
                        size=9.5, fill=MUTED))
    y += bh + 14
  y += 6
  out.append(rect(40, y - 12, 30, 16, fill=RED_BG, stroke=RED, sw=2, rx=6))
  out.append(text(78, y, "no gate today: the SoC can use it now in any mode", size=11))
  out.append(rect(400, y - 12, 30, 16, fill=AMBER_BG, stroke=AMBER, sw=1.2, rx=6))
  out.append(text(438, y, "gated today, but not yet as required", size=11))
  out.append(text(700, y, "The table and figure describe the baseline; the reference build adds the mode lock of TSR-512.",
                  size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s05_requests.py from WP-S-05 §4.2; the release whitelist per mode is OI-3.",
                  size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(rows)} control requests of WP-S-05 §4.2. " +
          " ".join(f"{r['req']} {r['func']}: needed {r['required']}; today {r['gate']}" + (" (no gate)." if r["open"] else ".")
                   for r in rows))
  return svg(W, h, "Figure 4-1. What the SoC can ask the safety MCU to do (WP-S-05 §4.2)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except RequestError as e:
    print(f"fig_s05_requests: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s05_requests.py", file=sys.stderr)
    if not stale:
      print(f"fig_s05_requests: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
