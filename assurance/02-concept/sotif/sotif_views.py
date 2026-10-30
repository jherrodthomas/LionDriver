#!/usr/bin/env python3
"""Draw the two overview figures of the SOTIF analysis (generated, not hand-drawn).

WP-C-06 Figure 4-1 (`../figures/fig-c06-4-1-odd-sotif-view.svg`), the ODD in the SOTIF view: the categories of the
WP-C-02 §3.1 ODD taxonomy, each with the triggering conditions of WP-C-06 §4 that sit in it, coloured by their §5
evaluation outcome. Triggering conditions that are not an ODD attribute (system, configuration, HMI) are drawn in a
group of their own. The category of each triggering condition is an analyst input, `TC_ODD` below.

WP-C-05 Figure 6-1 (`../figures/fig-c05-6-1-sotif-lineup.svg`), the SOTIF line-up: one row per SOTIF hazard of
WP-C-05 §3, from hazard to evidence:
  - the insufficiencies that link to it (WP-C-06 §3) and the triggering conditions whose §5 row names it;
  - the functional modifications that address it (WP-C-07 §2), by priority;
  - the validation targets for it (WP-V-02 §4) and the acceptance criteria that apply to it (WP-C-05 §5.3).

Both are written and checked by `sotif_figures.py`. They fail if a triggering condition has no ODD category, if an
ODD category of `TC_ODD` is not in WP-C-02 §3.1, or if WP-C-07, WP-V-02 or WP-C-05 §5.3 names a hazard WP-C-05 §3
does not define.

Standard library only. Drawing helpers come from ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hara"))
sys.path.insert(0, str(HERE))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, t, wrap, header, svg_doc  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
import sotif_figures as sf  # noqa: E402

C02 = HERE.parent / "WP-C-02-odd-and-intended-functionality.md"
C07 = HERE.parent / "WP-C-07-sotif-functional-modifications.md"
V02 = HERE.parents[1] / "06-validation" / "WP-V-02-sotif-vv-strategy.md"
ODD_NAME = "fig-c06-4-1-odd-sotif-view.svg"
LINEUP_NAME = "fig-c05-6-1-sotif-lineup.svg"
NOT_ODD = "Not an ODD attribute"

# The WP-C-02 §3.1 category each triggering condition of WP-C-06 §4 sits in (analyst input; §4 has its own, coarser
# categories). NOT_ODD: the condition is inside the system, its configuration or its HMI, not in the operating domain.
TC_ODD = {
  "TC-01": "Lighting", "TC-02": "Lighting", "TC-03": "Weather", "TC-04": "Weather", "TC-05": "Lane markings",
  "TC-06": "Infrastructure", "TC-07": "Traffic", "TC-08": "Traffic", "TC-09": "Traffic", "TC-10": "Infrastructure",
  "TC-11": "Traffic", "TC-12": "VRUs", "TC-13": "Road type", "TC-14": "Geometry", "TC-15": "Geometry",
  "TC-16": "Geometry", "TC-17": "Geometry", "TC-18": "Lighting", "TC-19": "Vehicle state", "TC-20": "Speed",
  "TC-21": "Weather", "TC-22": NOT_ODD, "TC-23": NOT_ODD, "TC-24": "Driver state", "TC-25": "Driver state",
  "TC-26": NOT_ODD, "TC-27": "VRUs", "TC-28": "Traffic", "TC-29": NOT_ODD, "TC-30": NOT_ODD, "TC-31": "Road type",
  "TC-32": "Geometry", "TC-33": "Traffic", "TC-34": "Traffic", "TC-35": "Traffic", "TC-36": "Traffic",
}
PRIO_COL = {"P1": ("#991B1B", "#FEE2E2"), "P2": ("#B45309", "#FFFBEB"), "P3": ("#475569", "#F1F5F9")}


class ViewError(sf.FigureError):
  pass


def _cells(ln: str) -> list[str]:
  return [c.strip() for c in ln.strip()[1:-1].split("|")]


def odd_categories(md2: str) -> dict[str, list[str]]:
  """WP-C-02 §3.1: category -> its attributes, in table order."""
  m = re.search(r"^### 3\.1 .*?$(.*?)(?=^### |^## )", md2, re.M | re.S)
  if not m:
    raise ViewError("WP-C-02 §3.1 not found")
  cats: dict[str, list[str]] = {}
  for ln in m.group(1).splitlines():
    if ln.startswith("| ") and not ln.startswith(("| Category", "|---")):
      c = _cells(ln)
      cats.setdefault(c[0], []).append(c[1])
  if not cats:
    raise ViewError("WP-C-02 §3.1 has no rows")
  return cats


def tc_outcomes(d: sf.Data) -> dict[str, str]:
  return {tc: o for tcs, _, _, o, _ in d.rows for tc in tcs}


def check_tc_odd(d: sf.Data, cats: dict[str, list[str]]) -> None:
  if missing := sorted(set(d.tc) - set(TC_ODD)):
    raise ViewError(f"triggering conditions without an ODD category in TC_ODD: {', '.join(missing)}")
  if extra := sorted(set(TC_ODD) - set(d.tc)):
    raise ViewError(f"TC_ODD names triggering conditions WP-C-06 §4 does not define: {', '.join(extra)}")
  if bad := sorted({c for c in TC_ODD.values() if c != NOT_ODD and c not in cats}):
    raise ViewError(f"TC_ODD names categories WP-C-02 §3.1 does not have: {', '.join(bad)}")


def _chip(x: float, y: float, label: str, stroke: str, fill: str, text: str = INK) -> tuple[str, float]:
  w = hf.text_w(label, 9.5, True) + 10
  return (f'<rect x="{x:g}" y="{y:g}" width="{w:.1f}" height="16" rx="4" fill="{fill}" stroke="{stroke}"/>'
          + t(x + w / 2, y + 11.5, label, 9.5, text, 700, "middle")), w


def _outcome_chip(x, y, tc, o):
  return _chip(x, y, tc, sf.OUT_COL[o], "#FFFFFF", sf.OUT_COL[o])


# ---------------------------------------------------------------- WP-C-06 Figure 4-1: the ODD in the SOTIF view

def odd_figure(d: sf.Data, md2: str, md6: str) -> str:
  cats = odd_categories(md2)
  check_tc_odd(d, cats)
  out = tc_outcomes(d)
  tc_cat = {}
  for ln in sf._section(md6, 4, "WP-C-06").splitlines():
    if re.match(r"^\| TC-\d\d \|", ln):
      c = _cells(ln)
      tc_cat[c[0]] = c[2]
  W, COLS, GAP = 1280, 4, 12
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  groups = list(cats) + [NOT_ODD]
  tiles = []
  for g in groups:
    tcs = sorted(tc for tc, c in TC_ODD.items() if c == g)
    lines: list[str] = []
    if g == NOT_ODD:
      sub = wrap("Inside the system, its configuration or its HMI", tw - 24, 10)
    else:
      sub = wrap(", ".join(cats[g]), tw - 24, 10)
    body: list[str] = []
    h = 34 + 13 * len(sub) + 6
    for tc in tcs:
      excl = "outside ODD" in tc_cat.get(tc, "") or "not validated" in tc_cat.get(tc, "")
      txt = wrap(d.tc[tc], tw - 82, 10)
      if len(txt) > 2:
        txt = [txt[0], sf._trunc(" ".join(txt[1:]), tw - 82, 10)]
      lines.append((tc, txt, excl))
    h += sum(8 + 13 * len(x[1]) for x in lines) + (18 if not lines else 0) + 8
    tiles.append((g, sub, lines, h))
  out_svg = header(W, "Figure 4-1 · The ODD in the SOTIF view",
                   "The categories of the WP-C-02 ODD taxonomy, each with the triggering conditions of §4 that sit in it, "
                   "coloured by their §5 evaluation", "WP-C-06 §4, §5", "ODD: WP-C-02 §3.1")
  y = 104
  for r in range(0, len(tiles), COLS):
    row = tiles[r:r + COLS]
    rh = max(h for *_, h in row)
    for i, (g, sub, lines, _) in enumerate(row):
      x = 40 + i * (tw + GAP)
      odd = g != NOT_ODD
      fill, stroke, dash = ("#FFFFFF", "#CBD5E1", "") if odd else ("#F8FAFC", "#94A3B8", ' stroke-dasharray="5 4"')
      out_svg.append(f'<rect x="{x:g}" y="{y}" width="{tw:g}" height="{rh}" rx="9" fill="{fill}" stroke="{stroke}"{dash}/>')
      out_svg.append(t(x + 12, y + 21, g, 12.5, INK, 700))
      n = len(lines)
      out_svg.append(t(x + tw - 12, y + 21, f"{n} TC" if n else "no TC", 10.5, MUTED if n else "#94A3B8", 700, "end"))
      ty = y + 36
      for ln in sub:
        out_svg.append(t(x + 12, ty, ln, 10, MUTED))
        ty += 13
      ty += 6
      if not lines:
        out_svg.append(t(x + 12, ty + 10, "No triggering condition in §4", 10, "#94A3B8", None, extra=' font-style="italic"'))
      for tc, txt, excl in lines:
        chip, cw = _outcome_chip(x + 12, ty, tc, out[tc])
        out_svg.append(chip)
        for j, ln in enumerate(txt):
          out_svg.append(t(x + 18 + cw, ty + 11.5 + 13 * j, ln, 10, INK if not excl else MUTED,
                           extra=' font-style="italic"' if excl else ""))
        ty += 8 + 13 * len(txt)
    y += rh + GAP
  y += 10
  counts = {k: sum(1 for o in out.values() if o == k) for k in sf.OUT_COL}
  lx = 40
  for k, lab in sf.OUT_LAB.items():
    s = f"{lab} ({counts[k]})"
    out_svg.append(f'<rect x="{lx}" y="{y - 11}" width="38" height="15" rx="4" fill="#FFFFFF" stroke="{sf.OUT_COL[k]}"/>')
    out_svg.append(t(lx + 19, y, "TC", 9.5, sf.OUT_COL[k], 700, "middle"))
    out_svg.append(t(lx + 46, y, s, 11))
    lx += 46 + hf.text_w(s, 11) + 24
  out_svg.append(t(lx, y, "Italic: §4 marks the condition outside the ODD or not validated", 11, MUTED, None,
                   extra=' font-style="italic"'))
  y += 20
  out_svg.append(t(40, y, "The category of each condition is an analyst input (TC_ODD in sotif_views.py); §4's own category "
                   "column is coarser. A category with no condition is not shown to be free of them.", 11, MUTED))
  extra, y = terms.svg_footer(out_svg, 40, y + 20, W - 80)
  out_svg += extra
  out_svg.append(t(W - 40, y + 6, "Generated by sotif_views.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = ("The WP-C-02 ODD categories with the WP-C-06 triggering conditions in each. "
          + " ".join(f"{g}: " + (", ".join(f"{tc} ({sf.OUT_LAB[out[tc]]})" for tc, _, _ in lines) or "none") + "."
                     for g, _, lines, _ in tiles))
  return svg_doc(W, h, "Figure 4-1. The ODD in the SOTIF view (WP-C-06 §4, §5; WP-C-02 §3.1)", desc, out_svg)


# ---------------------------------------------------------------- WP-C-05 Figure 6-1: the SOTIF line-up

def _sh_list(text: str, known: list[str], where: str) -> list[str]:
  """'SH-01, 03, 04' / 'SH-02, SH-06' / 'All' / 'All SH' -> hazard ids."""
  s = text.strip()
  if s.startswith("All"):
    return list(known)
  if "SH-" not in s:
    raise ViewError(f"{where}: cannot read hazards {text!r}")
  ids = []
  for tok in re.findall(r"SH-(\d\d)|(?<=, )(\d\d)\b", s):
    ids.append("SH-" + (tok[0] or tok[1]))
  for i in ids:
    if i not in known:
      raise ViewError(f"{where} names {i}, which WP-C-05 §3 does not define")
  return ids


def lineup_model(d: sf.Data, md5: str, md7: str, mv2: str) -> dict[str, dict]:
  shs = list(d.sh)
  model = {s: {"fi": [f for f, v in d.fi.items() if s in v[3]], "tc": [], "fm": [], "vt": [], "ac": [], "vt_all": [],
               "ac_all": []} for s in shs}
  out = tc_outcomes(d)
  for tcs, _, rshs, _, _ in d.rows:
    for s in rshs:
      for tc in tcs:
        if tc not in model[s]["tc"]:
          model[s]["tc"].append(tc)
  for s in shs:
    model[s]["tc"].sort()
    model[s]["tc_out"] = {tc: out[tc] for tc in model[s]["tc"]}
  m = re.search(r"^## 2\. .*?$(.*?)(?=^## \d+\. )", md7, re.M | re.S)
  for ln in (m.group(1) if m else "").splitlines():
    if ln.startswith("| FM-"):
      c = _cells(ln)
      for s in _sh_list(c[2], shs, f"WP-C-07 §2 {c[0]}"):
        model[s]["fm"].append((c[0], c[4]))
  if not any(v["fm"] for v in model.values()):
    raise ViewError("WP-C-07 §2 has no FM rows")
  m = re.search(r"^## 4\. .*?$(.*?)(?=^## \d+\. )", mv2, re.M | re.S)
  for ln in (m.group(1) if m else "").splitlines():
    if ln.startswith("| VT-"):
      c = _cells(ln)
      key = "vt_all" if c[1].startswith("All") else "vt"
      for s in _sh_list(c[1], shs, f"WP-V-02 §4 {c[0]}"):
        model[s][key].append(c[0])
  m = re.search(r"^### 5\.3 .*?$(.*?)(?=^### |^## )", md5, re.M | re.S)
  for ln in (m.group(1) if m else "").splitlines():
    if ln.startswith("| AC-"):
      c = _cells(ln)
      key = "ac_all" if c[2].startswith("All") else "ac"
      for s in _sh_list(c[2], shs, f"WP-C-05 §5.3 {c[0]}"):
        model[s][key].append(c[0])
  return model


def _chips(body, x0, y0, width, items) -> float:
  """Lay chips left to right, wrapping; items are (label, stroke, fill, text). Returns the height used."""
  x, y = x0, y0
  for label, stroke, fill, text in items:
    w = hf.text_w(label, 9.5, True) + 10
    if x + w > x0 + width and x > x0:
      x, y = x0, y + 20
    chip, w = _chip(x, y, label, stroke, fill, text)
    body.append(chip)
    x += w + 4
  return (y - y0 + 16) if items else 16


def lineup_figure(d: sf.Data, md5: str, md7: str, mv2: str) -> str:
  model = lineup_model(d, md5, md7, mv2)
  W = 1280
  cols = [("SOTIF HAZARD (WP-C-05 §3)", 40, 300), ("INSUFFICIENCIES (WP-C-06)", 354, 170),
          ("TRIGGERING CONDITIONS (WP-C-06)", 536, 250), ("MODIFICATIONS (WP-C-07)", 798, 160),
          ("VALIDATION (WP-V-02)", 970, 140), ("ACCEPTANCE (§5.3)", 1122, 118)]
  body = header(W, "Figure 6-1 · The SOTIF line-up: from each hazard to its evidence",
                "Per SOTIF hazard: what exposes it, what changes the function, and what must be shown before the "
                "residual risk is accepted", "WP-C-05 §3, §5.3; WP-C-06 §3, §5", "WP-C-07 §2; WP-V-02 §4")
  y = 112
  for lab, x, _ in cols:
    body.append(t(x, y, lab, 10, MUTED, 700, extra=' letter-spacing=".03em"'))
  y += 12
  rows_svg: list[tuple[float, float, list[str]]] = []
  for i, (s, (behaviour, sev, con)) in enumerate(d.sh.items()):
    v = model[s]
    tmp: list[str] = []
    ry = y + 10
    # hazard card
    tmp.append(t(cols[0][1] + 10, ry + 12, s, 12.5, INK, 700))
    px = cols[0][1] + 64
    for lab in (sev, con):
      if lab in ("—", "", "as linked SH"):
        continue
      tmp.append(f'<rect x="{px}" y="{ry + 1}" width="28" height="16" rx="8" fill="#F1F5F9" stroke="#94A3B8"/>')
      tmp.append(t(px + 14, ry + 12.5, lab, 9.5, INK, 700, "middle"))
      px += 32
    if sev == "as linked SH":
      tmp.append(t(px, ry + 12.5, "S, C as linked SH", 9.5, MUTED))
    short = re.split(r"[:;(]", behaviour, maxsplit=1)[0].strip()
    hl = wrap(short, cols[0][2] - 20, 10.5)[:3]
    for j, ln in enumerate(hl):
      tmp.append(t(cols[0][1] + 10, ry + 32 + j * 13.5, ln, 10.5, INK))
    h_card = 24 + 13.5 * len(hl) + 8
    hs = [h_card]
    hs.append(_chips(tmp, cols[1][1], ry, cols[1][2], [(f, "#64748B", "#FFFFFF", INK) for f in v["fi"]]))
    hs.append(_chips(tmp, cols[2][1], ry, cols[2][2],
                     [(tc, sf.OUT_COL[o], "#FFFFFF", sf.OUT_COL[o]) for tc, o in v["tc_out"].items()]))
    fm = [(f"{f} {p}", PRIO_COL[p][0], PRIO_COL[p][1], PRIO_COL[p][0]) for f, p in v["fm"]]
    hs.append(_chips(tmp, cols[3][1], ry, cols[3][2], fm))
    hs.append(_chips(tmp, cols[4][1], ry, cols[4][2], [(x, "#0F766E", "#F0FDFA", "#0F766E") for x in v["vt"]]))
    hs.append(_chips(tmp, cols[5][1], ry, cols[5][2], [(x, "#1D4ED8", "#EFF6FF", "#1D4ED8") for x in v["ac"]]))
    for k, key in ((3, "fm"), (4, "vt"), (5, "ac")):
      if not v[key]:
        tmp.append(t(cols[k][1], ry + 12, "none", 10, "#94A3B8", None, extra=' font-style="italic"'))
    if not v["fi"]:
      tmp.append(t(cols[1][1], ry + 12, "none", 10, "#94A3B8", None, extra=' font-style="italic"'))
    if not v["tc"]:
      tmp.append(t(cols[2][1], ry + 12, "none", 10, "#94A3B8", None, extra=' font-style="italic"'))
    rh = max(hs) + 20
    rows_svg.append((y, rh, tmp))
    y += rh
  for i, (ry, rh, tmp) in enumerate(rows_svg):
    if i % 2 == 0:
      body.append(f'<rect x="32" y="{ry}" width="{W - 64}" height="{rh}" rx="6" fill="#F8FAFC"/>')
    body += tmp
  for _, x, _ in cols[1:]:
    body.append(f'<line x1="{x - 8}" y1="{rows_svg[0][0]}" x2="{x - 8}" y2="{y}" stroke="{HAIR}"/>')
  y += 16
  all_vt = sorted({x for v in model.values() for x in v["vt_all"]})
  all_ac = sorted({x for v in model.values() for x in v["ac_all"]})
  body.append(t(40, y, f"Apply to every hazard and not repeated per row: validation targets {', '.join(all_vt)}; "
                f"acceptance criteria {', '.join(all_ac)}.", 11, MUTED))
  y += 22
  lx = 40
  for k, lab in sf.OUT_LAB.items():
    body.append(f'<rect x="{lx}" y="{y - 11}" width="36" height="15" rx="4" fill="#FFFFFF" stroke="{sf.OUT_COL[k]}"/>')
    body.append(t(lx + 18, y, "TC", 9.5, sf.OUT_COL[k], 700, "middle"))
    body.append(t(lx + 42, y, lab, 11))
    lx += 42 + hf.text_w(lab, 11) + 20
  for p, lab in (("P1", "P1 before on-road use"), ("P2", "P2 before release"), ("P3", "P3 decide at G2")):
    body.append(f'<rect x="{lx}" y="{y - 11}" width="22" height="15" rx="4" fill="{PRIO_COL[p][1]}" stroke="{PRIO_COL[p][0]}"/>')
    body.append(t(lx + 28, y, lab, 11))
    lx += 28 + hf.text_w(lab, 11) + 18
  y += 20
  body.append(t(40, y, "A row shows what the documents link, not what is done: no modification is verified and no "
                "validation target is frozen or met yet. SH-07 is not used (WP-C-05 §2).", 11, MUTED))
  extra, y = terms.svg_footer(body, 40, y + 20, W - 80)
  body += extra
  body.append(t(W - 40, y + 6, "Generated by sotif_views.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = ("One row per SOTIF hazard of WP-C-05 §3. "
          + " ".join(f"{s}: FI {', '.join(v['fi']) or 'none'}; TC {', '.join(v['tc']) or 'none'}; "
                     f"FM {', '.join(f for f, _ in v['fm']) or 'none'}; VT {', '.join(v['vt']) or 'none'}; "
                     f"AC {', '.join(v['ac']) or 'none'}." for s, v in model.items()))
  return svg_doc(W, h, "Figure 6-1. The SOTIF line-up (WP-C-05, WP-C-06, WP-C-07, WP-V-02)", desc, body)


def build(d: sf.Data | None = None) -> dict[str, str]:
  d = d or sf.load()
  md5, md6 = sf.C05.read_text(encoding="utf-8"), sf.C06.read_text(encoding="utf-8")
  md2, md7, mv2 = (p.read_text(encoding="utf-8") for p in (C02, C07, V02))
  return {ODD_NAME: odd_figure(d, md2, md6), LINEUP_NAME: lineup_figure(d, md5, md7, mv2)}
