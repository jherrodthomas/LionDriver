#!/usr/bin/env python3
"""Draw the WP-C-06 triggering-condition chain from the document (generated, not hand-drawn).

Figure 5-1 (`../figures/fig-c06-5-1-tc-fi-sh-chain.svg`): triggering conditions TC-nn (WP-C-06 §4) ->
functional insufficiencies FI-nn (§3) -> SOTIF hazards SH-nn (WP-C-05 §3).

The SOTIF scene sheet (`../figures/fig-c06-5-2-sotif-scenes.svg`, one card per hazard) is drawn by `sotif_scenes.py`
and written and checked here with Figure 5-1. The WP-C-07 modification sheets (`../figures/fig-c07-3-1-fm-scenes-p1.svg`,
`fig-c07-3-2-fm-scenes-p2-p3.svg`, one card per FM) are drawn by `fm_scenes.py` and written and checked here too.

- TC -> FI edges come from the WP-C-06 §5 evaluation table, coloured by the row's evaluation outcome.
- FI -> SH edges come from the "Linked SH" column of WP-C-06 §3.
- SH texts and S/C come from WP-C-05 §3.

WP-C-05 and WP-C-06 are the sources of record. Edit their tables and regenerate:

    python3 sotif_figures.py            # write the SVG
    python3 sotif_figures.py --check    # fail if the committed SVG is stale

Both modes print, as warnings, any §5 row that names a hazard none of its FIs links to in §3.
Standard library only. Drawing helpers come from ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, t, header, svg_doc  # noqa: E402

C05 = HERE.parent / "WP-C-05-sotif-hazard-identification.md"
C06 = HERE.parent / "WP-C-06-sotif-insufficiencies-triggering-conditions.md"
OUT_DIR = HERE.parent / "figures"
NAME = "fig-c06-5-1-tc-fi-sh-chain.svg"

OUT_COL = {"mod": "#D2553F", "val": "#D97706", "acc": "#64748B"}
OUT_LAB = {"mod": "Needs modification", "val": "Needs validation", "acc": "Acceptable, with a stated condition"}
LINK_COL = "#475569"


class FigureError(Exception):
  pass


@dataclass
class Data:
  sh: dict[str, tuple[str, str, str]]                 # id -> (behaviour, S, C)
  fi: dict[str, tuple[str, str, str, list[str]]]      # id -> (type, component, text, linked SH)
  tc: dict[str, str]                                  # id -> condition
  rows: list[tuple[list[str], list[str], list[str], str, str]]   # (TCs, FIs, SHs, outcome, evaluation text)


def _cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip()[1:-1].split("|")]


def _ids(s: str, prefix: str) -> list[str]:
  return re.findall(prefix + r"-\d\d", s)


def _section(md: str, num: int, doc: str) -> str:
  m = re.search(rf"^## {num}\. .*?$(.*?)(?=^## \d+\. |\Z)", md, re.M | re.S)
  if not m:
    raise FigureError(f"{doc} §{num} not found")
  return m.group(1)


def outcome(ev: str) -> str:
  for prefix, key in (("Needs modification", "mod"), ("Needs validation", "val"), ("Acceptable", "acc")):
    if ev.startswith(prefix):
      return key
  raise FigureError(f"unrecognised evaluation outcome {ev!r} (WP-C-06 §1 defines Acceptable / Needs modification / Needs validation)")


def parse(md5: str, md6: str) -> Data:
  sh = {}
  for ln in _section(md5, 3, "WP-C-05").splitlines():
    if re.match(r"^\| SH-\d\d \|", ln):
      c = _cells(ln)
      if len(c) != 8:
        raise FigureError(f"WP-C-05 §3 row has {len(c)} cells: {ln[:40]}")
      if c[2] != "—":                   # SH-07 "not used"
        sh[c[0]] = (c[1].replace("`", ""), c[5], c[6])
  fi = {}
  for ln in _section(md6, 3, "WP-C-06").splitlines():
    if re.match(r"^\| FI-\d\d \|", ln):
      c = _cells(ln)
      if len(c) != 6:
        raise FigureError(f"WP-C-06 §3 row has {len(c)} cells: {ln[:40]}")
      linked = _ids(c[4], "SH")
      for s in linked:
        if s not in sh:
          raise FigureError(f"{c[0]}: linked hazard {s} is not in WP-C-05 §3")
      fi[c[0]] = (c[1], c[2], c[3].replace("`", ""), linked)
  tc = {}
  for ln in _section(md6, 4, "WP-C-06").splitlines():
    if re.match(r"^\| TC-\d\d \|", ln):
      c = _cells(ln)
      tc[c[0]] = c[1].replace("`", "")
  rows = []
  for ln in _section(md6, 5, "WP-C-06").splitlines():
    if re.match(r"^\| TC-\d\d", ln):
      c = _cells(ln)
      if len(c) != 6:
        raise FigureError(f"WP-C-06 §5 row has {len(c)} cells: {ln[:40]}")
      tcs, fis, shs = _ids(c[0], "TC"), _ids(c[1], "FI"), _ids(c[2], "SH")
      for x, known, where in ((tcs, tc, "§4"), (fis, fi, "§3")):
        for i in x:
          if i not in known:
            raise FigureError(f"§5 row {c[0]}: {i} is not defined in WP-C-06 {where}")
      for s in shs:
        if s not in sh:
          raise FigureError(f"§5 row {c[0]}: {s} is not in WP-C-05 §3")
      if not tcs or not fis:
        raise FigureError(f"§5 row {c[0]!r} names no TC or no FI")
      rows.append((tcs, fis, shs, outcome(c[4]), c[4]))
  if not sh or not fi or not tc or not rows:
    raise FigureError("SH, FI, TC or evaluation table not found")
  seen_tc = {x for r in rows for x in r[0]}
  if missing := sorted(set(tc) - seen_tc):
    raise FigureError(f"triggering conditions not evaluated in §5: {', '.join(missing)}")
  if unused := sorted(set(fi) - {x for r in rows for x in r[1]}):
    raise FigureError(f"insufficiencies not activated by any §5 row: {', '.join(unused)}")
  dup = [x for x in seen_tc if sum(x in r[0] for r in rows) > 1]
  if dup:
    raise FigureError(f"triggering conditions evaluated in more than one §5 row: {', '.join(sorted(dup))}")
  return Data(sh, fi, tc, rows)


def warnings(d: Data) -> list[str]:
  """§5 rows naming a hazard that none of their FIs links to in §3 (drawn per §3, reported here)."""
  out = []
  for tcs, fis, shs, _, _ in d.rows:
    linked = {s for f in fis for s in d.fi[f][3]}
    for s in shs:
      if s not in linked:
        out.append(f"WP-C-06 §5 {', '.join(tcs)}: names {s}, but none of {', '.join(fis)} links to {s} in §3")
  return out


def _trunc(s: str, width: float, size: float, bold: bool = False) -> str:
  if hf.text_w(s, size, bold) <= width:
    return s
  while s and hf.text_w(s + " …", size, bold) > width:
    s = s[:-1]
  return s.rstrip(" ,;(") + " …"


def figure(d: Data) -> str:
  tc_out, tc_fi = {}, defaultdict(set)
  for tcs, fis, _, o, _ in d.rows:
    for tc in tcs:
      tc_out[tc] = o
      tc_fi[tc] |= set(fis)
  sh_no_fi = sorted(s for s in d.sh if not any(s in v[3] for v in d.fi.values()))

  W = 1280
  TX, TW = 40, 370
  FX, FW = 560, 330
  SX, SW = 1010, 230
  top, RH = 128, 24
  tc_ids = sorted(d.tc)
  tc_y = {tc: top + i * RH + RH / 2 for i, tc in enumerate(tc_ids)}
  bottom = top + len(tc_ids) * RH
  # barycentric ordering of the FI and SH columns keeps edges short
  fi_bary = {f: sum(tc_y[tc] for tc in tc_ids if f in tc_fi[tc]) / sum(1 for tc in tc_ids if f in tc_fi[tc]) for f in d.fi}
  fi_ids = sorted(d.fi, key=lambda f: (fi_bary[f], f))
  FH = (bottom - top) / len(fi_ids)
  fi_y = {f: top + i * FH + FH / 2 for i, f in enumerate(fi_ids)}
  sh_bary = {s: 1e9 if s in sh_no_fi else
             sum(fi_y[f] for f in d.fi if s in d.fi[f][3]) / sum(1 for f in d.fi if s in d.fi[f][3]) for s in d.sh}
  sh_ids = sorted(d.sh, key=lambda s: (sh_bary[s], s))
  SH_H = (bottom - top) / len(sh_ids)
  sh_y = {s: top + i * SH_H + SH_H / 2 for i, s in enumerate(sh_ids)}

  body = header(W, "Figure 5-1 · Triggering conditions → functional insufficiencies → SOTIF hazards",
                f"{len(d.tc)} triggering conditions (§4) activate {len(d.fi)} functional insufficiencies (§3), which lead to "
                f"{len(d.sh) - len(sh_no_fi)} of the {len(d.sh)} SOTIF hazards of WP-C-05",
                "WP-C-06 §3–§5", "hazards: WP-C-05 §3")
  for x, lab in ((TX, "TRIGGERING CONDITION (§4) · evaluation (§5)"), (FX, "FUNCTIONAL INSUFFICIENCY (§3) · S/P · component"),
                 (SX, "SOTIF HAZARD (WP-C-05 §3) · S C")):
    body.append(t(x, top - 18, lab, 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))

  edges = [(TX + TW, tc_y[tc], FX, fi_y[f], OUT_COL[tc_out[tc]], 1.3) for tc in tc_ids for f in sorted(tc_fi[tc])]
  edges += [(FX + FW, fi_y[f], SX, sh_y[s], LINK_COL, 1.2) for f in fi_ids for s in d.fi[f][3]]
  for x1, y1, x2, y2, col, sw in edges:
    mx = (x1 + x2) / 2
    body.append(f'<path d="M{x1} {y1:.1f} C{mx} {y1:.1f} {mx} {y2:.1f} {x2 - 1} {y2:.1f}" stroke="{col}" stroke-width="{sw}" '
                f'fill="none" opacity=".75" marker-end="url(#m{col[1:]})"/>')

  for tc in tc_ids:
    y = tc_y[tc] - RH / 2 + 2
    body.append(f'<rect x="{TX}" y="{y}" width="{TW}" height="{RH - 4}" rx="5" fill="#FFFFFF" stroke="#CBD5E1"/>')
    body.append(f'<rect x="{TX}" y="{y}" width="5" height="{RH - 4}" rx="2" fill="{OUT_COL[tc_out[tc]]}"/>')
    body.append(t(TX + 12, y + 14.5, tc, 10.5, INK, 700))
    body.append(t(TX + 58, y + 14.5, _trunc(d.tc[tc], TW - 66, 10.5), 10.5, INK))
  for f in fi_ids:
    y = fi_y[f] - FH / 2 + 2
    typ, comp, text, _ = d.fi[f]
    body.append(f'<rect x="{FX}" y="{y:.1f}" width="{FW}" height="{FH - 4:.1f}" rx="6" fill="#EEF2FF" stroke="#A5B4FC"/>')
    body.append(t(FX + 10, y + 14, f, 11, INK, 700))
    body.append(t(FX + 56, y + 14, f"{typ} · {comp}", 10.5, MUTED, 600))
    body.append(t(FX + 10, y + 27.5, _trunc(text, FW - 20, 10), 10, INK))
  for s in sh_ids:
    y = sh_y[s] - SH_H / 2 + 3
    text, S, C = d.sh[s]
    nofi = s in sh_no_fi
    dash = ' stroke-dasharray="5 3"' if nofi else ""
    body.append(f'<rect x="{SX}" y="{y:.1f}" width="{SW}" height="{SH_H - 6:.1f}" rx="8" fill="{"#F8FAFC" if nofi else "#FFF7ED"}" '
                f'stroke="{"#94A3B8" if nofi else "#C2410C"}" stroke-width="1.4"{dash}/>')
    sc = f"{S} {C}" if S.startswith("S") else ("S/C as linked SH" if S.startswith("as") else "no direct S/C")
    body.append(t(SX + 10, y + 16, s, 11.5, INK, 700))
    body.append(t(SX + SW - 10, y + 16, sc, 10, MUTED, 600, "end"))
    lines = hf.wrap(text, SW - 20, 10)
    short = lines[:2]
    if len(lines) > 2:
      short[1] = _trunc(short[1] + " " + lines[2], SW - 20, 10)
    if nofi:
      short = [_trunc(text, SW - 20, 10), "no FI or TC in WP-C-06"]
    for i, ln in enumerate(short):
      red = nofi and i == 1
      body.append(t(SX + 10, y + 31 + 12.5 * i, ln, 10, "#D2553F" if red else MUTED, 600 if red else None))

  y = bottom + 24
  notes = ["TC → FI from the §5 evaluation table (edge colour = evaluation outcome of that row); FI → SH from the Linked SH column of §3. "
           "Texts are shortened; the tables are the source.",
           "“Needs modification”: a functional modification in WP-C-07 or an ODD restriction is required; “Needs validation”: "
           "acceptability depends on evidence from WP-V-03 (§1)."]
  acc = [f"{', '.join(r[0])} {r[4].removeprefix('Acceptable').strip()}" for r in d.rows if r[3] == "acc"]
  if acc:
    notes += hf.wrap("Acceptable rows carry a condition (§5): " + "; ".join(acc) + ".", W - 80, 11)
  for n in notes:
    body.append(t(40, y, n, 11, MUTED))
    y += 16
  y += 6
  body.append(f'<line x1="40" y1="{y}" x2="{W - 40}" y2="{y}" stroke="{HAIR}"/>')
  y += 24
  lx = 40
  for o in ("mod", "val", "acc"):
    body.append(f'<line x1="{lx}" y1="{y - 4}" x2="{lx + 28}" y2="{y - 4}" stroke="{OUT_COL[o]}" stroke-width="2"/>')
    body.append(t(lx + 36, y, OUT_LAB[o], 10.5))
    lx += 36 + hf.text_w(OUT_LAB[o], 10.5) + 28
  body.append(f'<line x1="{lx}" y1="{y - 4}" x2="{lx + 28}" y2="{y - 4}" stroke="{LINK_COL}" stroke-width="1.4"/>')
  body.append(t(lx + 36, y, "FI leads to SH", 10.5))
  lx += 36 + hf.text_w("FI leads to SH", 10.5) + 28
  lab = "Insufficiency (P performance, S specification)"
  body.append(f'<rect x="{lx}" y="{y - 12}" width="28" height="16" rx="4" fill="#EEF2FF" stroke="#A5B4FC"/>')
  body.append(t(lx + 36, y, lab, 10.5))
  lx += 36 + hf.text_w(lab, 10.5) + 28
  body.append(f'<rect x="{lx}" y="{y - 12}" width="28" height="16" rx="4" fill="#FFF7ED" stroke="#C2410C"/>')
  body.append(t(lx + 36, y, "SOTIF hazard", 10.5))
  y += 20
  body.append(t(W - 40, y, "Generated by sotif_figures.py", 10, MUTED, None, "end"))
  H = int(y + 18)
  desc = ("Three-column chain. Left: triggering conditions, each marked with the evaluation outcome of its WP-C-06 §5 row (needs modification, "
          "needs validation, or acceptable with a condition). Middle: functional insufficiencies with type and component. Right: SOTIF "
          "hazards of WP-C-05. " + " ".join(f"{tc} to {', '.join(sorted(tc_fi[tc]))}." for tc in tc_ids) + " " +
          " ".join(f"{f} to {', '.join(d.fi[f][3])}." for f in sorted(d.fi)) +
          (f" {', '.join(sh_no_fi)} has no insufficiency in WP-C-06." if sh_no_fi else ""))
  defs = "".join(f'<marker id="m{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" '
                 f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
                 for c in sorted(set(OUT_COL.values()) | {LINK_COL}))
  return svg_doc(W, H, "Figure 5-1. Triggering conditions, functional insufficiencies and SOTIF hazards (WP-C-06 §3-§5)", desc, body, defs)


def load() -> Data:
  return parse(C05.read_text(encoding="utf-8"), C06.read_text(encoding="utf-8"))


def build() -> dict[str, str]:
  import fm_scenes  # the WP-C-07 modification sheets; imports this module, so it is loaded here
  import sotif_scenes  # the SOTIF scene sheet; imports this module, so it is loaded here
  return {NAME: figure(load()), **sotif_scenes.build(), **fm_scenes.build()}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    import fm_scenes  # the WP-C-07 modification sheets (see build)
    import sotif_scenes  # the SOTIF scene sheet (see build)
    data = load()
    outputs = {NAME: figure(data), **sotif_scenes.build(), **fm_scenes.build()}
  except FigureError as e:
    print(f"sotif_figures: {e}", file=sys.stderr)
    return 1
  for w in warnings(data):
    print(f"sotif_figures: warning: {w}", file=sys.stderr)
  if check:
    stale = [n for n, c in outputs.items() if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"stale: figures/{n}", file=sys.stderr)
    if stale:
      print("run: python3 assurance/02-concept/sotif/sotif_figures.py", file=sys.stderr)
      return 1
    print(f"sotif_figures: {len(outputs)} figure(s) current")
    return 0
  for n, c in outputs.items():
    (OUT_DIR / n).write_text(c, encoding="utf-8")
  print(f"sotif_figures: wrote {', '.join(outputs)} to figures/")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
