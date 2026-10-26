#!/usr/bin/env python3
"""Draw WP-S-02 Figure 2-1, where the technical safety requirements sit (fig-s02-2-1-allocation.svg).

A grid of the TSR blocks of WP-S-02 (1xx lateral … 7xx PCS and harness) and WP-S-06 (8xx operation) against the
allocation of §2.2: P-SW the envelope firmware on the safety MCU (E-03), P-HW the safety MCU hardware (E-04), HAR the
harness and relay (E-05), SoC the host software (E-01, QM), EXT an existing vehicle element (credited through an AoU),
OPS a production or operation process. One pill per TSR in each cell it is allocated to, with:

  number and ASIL   C, B‡, B, A as rated; QM* for QM supporting an ASIL TSR (C-sup / B-sup); QM; ext
  colour            the implementation status at the baseline, by the rule of WP-S-03 Figure 6-1
                    (fig_s03_defence_in_depth.classify): implemented, partly, not implemented, assumed
  "+"               the TSR is also allocated to another column
Everything is read from trace/items/tsr.yaml, the copy of WP-S-02 §3–§10 and WP-S-06 that CI holds to the documents.

    python3 fig_s02_allocation.py            # write the SVG
    python3 fig_s02_allocation.py --check    # fail if the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fig_s03_defence_in_depth as dd  # noqa: E402  (status rule, allocation tokens, YAML loader)
from fig_s03_defence_in_depth import INK, MUTED, FAINT, LINE, GREY_BG, text, rect, svg, header  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

OUT = "fig-s02-2-1-allocation.svg"
W = 1280
COLUMNS = [("P-SW", "envelope firmware", "E-03 · safety MCU"), ("P-HW", "MCU hardware", "E-04"),
           ("HAR", "harness, relay", "E-05"), ("SoC", "host software", "E-01 · QM"),
           ("EXT", "vehicle element", "via an AoU"), ("OPS", "process", "production, operation")]
BLOCKS = {"1": "Lateral envelope", "2": "Longitudinal envelope", "3": "Engagement, override", "4": "Communication",
          "5": "MCU platform", "6": "Host monitoring, DM, HMI", "7": "PCS, harness", "8": "Production, operation"}
STATES = ("implemented", "partly", "not", "assumed")
COL = {"implemented": "#1D4ED8", "partly": "#D97706", "not": "#D2553F", "assumed": "#94A3B8"}
BG = {"implemented": "#EFF6FF", "partly": "#FFFBEB", "not": "#FEF2F2", "assumed": "#F1F5F9"}
LABEL = {"implemented": "implemented", "partly": "partly", "not": "not implemented", "assumed": "assumed (EXT, AoU)"}
RATED = ("C", "B‡", "B", "A")


def asil_class(s) -> str:
  """The ASIL a TSR carries, as a short label: the first rating named, QM* when QM supports an ASIL TSR."""
  s = str(s)
  if s.startswith(("—", "ext")):
    return "ext"
  m = re.search(r"(?<![\w-])(QM|[ABCD])(‡)?", s)
  if not m:
    raise ValueError(f"no ASIL in {s!r}")
  if m.group(1) == "QM":
    return "QM*" if re.search(r"-sup|supports", s[m.end():m.end() + 40]) else "QM"
  return m.group(1) + (m.group(2) or "")


def load() -> list[dict]:
  ts = sorted(dd.ct.load_yaml(dd.ITEMS / "tsr.yaml"), key=lambda t: int(t["id"][4:7]))
  out = []
  for t in ts:
    cols = [c for c, *_ in COLUMNS if c in dd.allocation(t)]
    if not cols:
      raise ValueError(f"{t['id']}: allocation {t.get('allocated_to')!r} names none of {[c for c, *_ in COLUMNS]}")
    out.append({"id": t["id"], "num": t["id"][4:], "block": t["id"][4], "asil": asil_class(t.get("asil", "")),
                "status": dd.classify(t), "cols": cols})
  return out


def figure(ts: list[dict]) -> str:
  stat = Counter(t["status"] for t in ts)
  rated = sum(t["asil"] in RATED for t in ts)
  out = header(W, "2-1", "Where the technical safety requirements sit",
               f"The {len(ts)} TSRs by block and by the element they are allocated to; {rated} carry an ASIL. Status at the "
               f"baseline: {stat['implemented']} implemented, {stat['partly']} partly, {stat['not']} not, "
               f"{stat['assumed']} assumed", "WP-S-02 §2.2, §3–§10 · WP-S-06")
  x0 = 230
  cw = (W - 40 - x0) / len(COLUMNS)
  y = 100
  for i, (c, name, el) in enumerate(COLUMNS):
    x = x0 + i * cw
    n = sum(c in t["cols"] for t in ts)
    out.append(text(x + 8, y + 12, f"{c} · {name}", size=11.5, weight=700))
    out.append(text(x + 8, y + 27, f"{el} · {n} TSRs", size=9.5, fill=MUTED))
  y += 40
  PW, PH, GAP = 46, 17, 4
  per_row = int((cw - 12) // (PW + GAP))
  for b, title in BLOCKS.items():
    rows = [t for t in ts if t["block"] == b]
    if not rows:
      continue
    cells = {c: [t for t in rows if c in t["cols"]] for c, *_ in COLUMNS}
    nrow = max(1, max((len(v) + per_row - 1) // per_row for v in cells.values()))
    bh = 16 + nrow * (PH + GAP) + 8
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=10))
    out.append(text(44, y + 20, f"{b}xx {title}", size=12, weight=700))
    mix = Counter(t["asil"] for t in rows)
    out.append(text(44, y + 36, f"{len(rows)} TSRs", size=10, fill=MUTED))
    out.append(text(44, y + 50, " · ".join(f"{k} {mix[k]}" for k in (*RATED, "QM*", "QM", "ext") if mix[k]), size=9.5,
                    fill=MUTED))
    for i, (c, *_) in enumerate(COLUMNS):
      x = x0 + i * cw + 6
      for j, t in enumerate(cells[c]):
        px = x + (j % per_row) * (PW + GAP)
        py = y + 10 + (j // per_row) * (PH + GAP)
        st = t["status"]
        rated_t = t["asil"] in RATED
        out.append(rect(px, py, PW, PH, fill=BG[st], stroke=COL[st], sw=1.6 if rated_t else 0.9, rx=8,
                        dash="" if rated_t else "3 2"))
        label = f"{t['num']}{'+' if len(t['cols']) > 1 else ''} {t['asil']}"
        out.append(text(px + PW / 2, py + 12, label, size=8.5, weight=700 if rated_t else "", fill=COL[st],
                        anchor="middle", family=dd.MONO))
    y += bh + 8
  # totals per column
  y += 6
  out.append(text(44, y + 14, "Status by element", size=11.5, weight=700))
  for i, (c, *_) in enumerate(COLUMNS):
    x = x0 + i * cw + 6
    items = [t for t in ts if c in t["cols"]]
    bw = cw - 18
    xx = x
    for s in STATES:
      k = sum(t["status"] == s for t in items)
      if k:
        w = bw * k / len(items)
        out.append(rect(xx, y + 2, w, 16, fill=COL[s], stroke="none", sw=0, rx=0))
        if w > 18:
          out.append(text(xx + w / 2, y + 14, str(k), size=9.5, weight=700, fill="#FFFFFF", anchor="middle"))
        xx += w
  y += 40
  x = 40
  for s in STATES:
    out.append(rect(x, y - 11, 34, 14, fill=BG[s], stroke=COL[s], sw=1.4, rx=7))
    out.append(text(x + 42, y, LABEL[s], size=11))
    x += 70 + len(LABEL[s]) * 6
  out.append(rect(x + 10, y - 11, 34, 14, fill="#FFFFFF", stroke=INK, sw=1.6, rx=7))
  out.append(text(x + 52, y, "carries an ASIL", size=11))
  out.append(rect(x + 170, y - 11, 34, 14, fill="#FFFFFF", stroke=INK, sw=0.9, rx=7, dash="3 2"))
  out.append(text(x + 212, y, "QM, QM* (supports an ASIL TSR) or ext", size=11))
  y += 18
  out.append(text(40, y, "\"+\": also allocated to another element. Status by the rule of WP-S-03 Figure 6-1, read from each "
                  "TSR's implementation column; implemented means in the code at the baseline or the reference build, not verified.",
                  size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s02_allocation.py from trace/items/tsr.yaml, the copy of WP-S-02 §3–§10 and WP-S-06 "
                  "that CI holds to the documents; nothing is hand-listed.", size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(ts)} technical safety requirements by block and allocation. " +
          " ".join(f"{t['id']} ({t['asil']}, {'/'.join(t['cols'])}, {LABEL[t['status']]})." for t in ts))
  return svg(W, h, "Figure 2-1. Where the technical safety requirements sit (WP-S-02)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(load())}


def main(argv: list[str]) -> int:
  outputs = build()
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s02_allocation.py", file=sys.stderr)
    if not stale:
      print(f"fig_s02_allocation: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
