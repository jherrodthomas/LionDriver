#!/usr/bin/env python3
"""Draw the hazard log sheet: one card per vehicle-level hazard of WP-C-03, everything that reaches it and what holds it.

`figures/fig-c03-7-1-hazard-log.svg` illustrates the shared hazard log of WP-C-03 §7. Each card shows, for one hazard
H-nn:

- WHAT REACHES IT: the lanes that converge on the hazard. A malfunction (the SC function × guide-word pairs of §4), an
  insufficiency of the intended function (the SOTIF hazards §7 names, with their WP-C-06 §5 evaluation), an attack (the
  WP-C-09 §3 damage scenarios that name the hazard, the threat scenarios that reach them and their §8 risk), and
  foreseeable misuse (the hazardous events of §5 rated in a misuse situation of §3). A lane the documents leave empty
  is drawn dashed with what §7 says instead.
- the road outcome of its highest-rated hazardous event, as a looping scene (SMIL, 6 s; the still frame is the end);
- WHAT HOLDS IT TODAY: the §5 Impl status of the WP-C-04 FSRs that serve its safety goals (§9 trace), the WP-C-07
  modifications that address its SOTIF hazards with their recorded status, and the treatment of its highest-risk
  threat scenarios.

Every ID and count is read from the documents; the build fails if §4, §5, §6 and §7 do not list the same hazards, if a
hazardous event has no safety goal (QM aside), if §7 names a SOTIF hazard WP-C-05 does not define, or if a hazard has no
scene. The scenes are schematic. Built and checked by `hara_figures.py`.

Standard library only. Drawing helpers come from hara_figures.py, ../sotif/ and ../fsc/; the data from WP-C-03, -04,
-05/-06, -07 and -09 through their generators.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent / "sotif", HERE.parent / "fsc", HERE.parent / "figures"):
  sys.path.insert(0, str(p))
import hara_figures as hf  # noqa: E402
import fig_c09_scenes as tara  # noqa: E402
import fm_scenes as fm  # noqa: E402
import fsc_figures as ff  # noqa: E402
import fsc_scenes as fsc  # noqa: E402
import sotif_scenes as ss  # noqa: E402
from fm_scenes import BAD, GOOD, NOTE, LANE, NEXT, X0, X1, badge, ego, other, road, sample, still, tag  # noqa: E402
from hara_figures import HAIR, INK, MUTED, pill, svg_doc, t, wrap  # noqa: E402

C03 = HERE.parent / "WP-C-03-hara.md"
NAME = "fig-c03-7-1-hazard-log.svg"
K = hf                                          # the hara_figures module that called build (FigureError)
LANES = {"fault": ("#7C3AED", "Malfunction · HARA §4"), "sotif": ("#2563EB", "Insufficiency · SOTIF"),
         "attack": ("#B91C1C", "Attack · TARA"), "misuse": ("#0F766E", "Foreseeable misuse · HARA §5")}
IMPL = [("implemented", "#16A34A"), ("partial", "#F59E0B"), ("not met", "#DC2626"), ("unverified", "#64748B"), ("see §5", "#CBD5E1")]
ASIL_RANK = {"QM": 0, "A": 1, "B": 2, "C": 3, "D": 4}
ASIL_CHIP = {"A": ("#DCFCE7", "#14532D"), "B": ("#FEF3C7", "#78350F"), "C": ("#FEE2E2", "#7F1D1D"), "D": ("#FCE7F3", "#831843"),
             "QM": ("#E2E8F0", "#334155")}


def fail(msg):
  raise K.FigureError(f"hazard log: {msg}")


def _cells(line):
  return [c.strip() for c in line.strip()[1:-1].split(" | ")]


def _plain(s):
  return s.replace("**", "").replace("`", "")


def _section(md, num):
  m = re.search(rf"^## {num}\. .*?$(.*?)(?=^## \d+\. |\Z)", md, re.M | re.S)
  if not m:
    fail(f"WP-C-03 §{num} not found")
  return m.group(1)


def he_ids(cell):
  """HE-01.1–01.5, HE-02.3 -> [HE-01.1, ..., HE-01.5, HE-02.3]."""
  out = []
  for a, b, c in re.findall(r"HE-(\d\d)\.(\d)(?:–(?:HE-)?\d\d\.(\d))?", cell):
    out += [f"HE-{a}.{k}" for k in range(int(b), int(c or b) + 1)]
  return out


# ---------------------------------------------------------------- documents

def load_c03(md):
  hz = {}
  for ln in _section(md, 4).splitlines():
    if m := re.match(r"^\| \*\*(H-\d\d)\*\* (.+?) \| (.*?) \| (.*?) \|$", ln):
      hz[m.group(1)] = dict(title=m.group(2), pairs=[p.strip() for p in m.group(3).split(",") if p.strip() not in ("", "—")])
  misuse = {c[0] for c in (_cells(ln) for ln in _section(md, 3).splitlines() if ln.startswith("| OS-")) if "foreseeable misuse" in c[1]}
  he, cur = {}, None
  for ln in _section(md, 5).splitlines():
    if m := re.match(r"^### 5\.\d+ (H-\d\d) ", ln):
      cur = m.group(1)
    elif cur and ln.startswith("| HE-"):
      c = _cells(ln)
      if len(c) >= 8 and re.fullmatch(r"S\d", c[3]):
        he[c[0]] = dict(h=cur, situation=c[1], effect=c[2], s=c[3], e=c[4], c=c[5], asil=_plain(c[6]),
                        os=re.findall(r"OS-\d\d", c[1]), misuse=bool(set(re.findall(r"OS-\d\d", c[1])) & misuse))
  sg = {}
  for ln in _section(md, 6).splitlines():
    if ln.startswith("| **SG-"):
      c = _cells(ln)
      sg[_plain(c[0])] = dict(asil=re.match(r"\*\*(\w+)\*\*", c[2]).group(1), hes=he_ids(c[3]))
  log = {}
  for ln in _section(md, 7).splitlines():
    if ln.startswith("| H-"):
      c = _cells(ln)
      log[c[0]] = dict(sotif=c[1], sh=re.findall(r"SH-\d\d", c[1].split(";")[0]), tara=_plain(c[2]), fsc=c[3])
  if not hz or sorted(hz) != sorted({v["h"] for v in he.values()}) or sorted(hz) != sorted(log):
    fail(f"WP-C-03 §4 hazards {sorted(hz)}, §5 sections {sorted({v['h'] for v in he.values()})} and §7 rows {sorted(log)} differ")
  for hid, e in he.items():
    if e["asil"] != "QM" and not any(hid in g["hes"] for g in sg.values()):
      fail(f"{hid} ({e['asil']}) is in no safety goal's Source HEs (§6)")
  return dict(hz=hz, he=he, sg=sg, log=log)


def load():
  c03 = load_c03(C03.read_text(encoding="utf-8"))
  sot = ss.load()
  for h, row in c03["log"].items():
    for s in row["sh"]:
      if s not in sot.data.sh:
        fail(f"§7 names {s} for {h}, which WP-C-05 §3 does not define")
  md4 = ff.SOURCE.read_text(encoding="utf-8")
  return dict(c03=c03, sotif=sot, fms=fm.cards(), fsrs=[f for g in ff.parse(md4) for f in g.fsrs], impl=fsc.impl(md4),
              tara=tara.load())


# ---------------------------------------------------------------- one card's data

def worst(hes):
  top = max(ASIL_RANK[e["asil"]] for e in hes)
  return next(e for e in hes if ASIL_RANK[e["asil"]] == top)


def card_data(h, D):
  c03 = D["c03"]
  hes = [dict(v, id=k) for k, v in c03["he"].items() if v["h"] == h]
  sgs = sorted({g for g, v in c03["sg"].items() for e in hes if e["id"] in v["hes"]})
  rep = worst(hes)
  log = c03["log"][h]
  lanes = []
  pairs = c03["hz"][h]["pairs"]
  lanes.append(("fault", f"{len(pairs)} SC pair{'s' if len(pairs) != 1 else ''}: " + ", ".join(pairs), True))
  if log["sh"]:
    parts = []
    for s in log["sh"]:
      rows = [r for r in D["sotif"].rows if s in r["sh"]]
      tcs = sorted({x for r in rows for x in r["tc"]})
      mod = sum(r["out"] == "mod" for r in rows)
      parts.append(f"{s} {len(tcs)} TC{'s' if len(tcs) != 1 else ''}" + (f", {mod} need{'s' if mod == 1 else ''} modification" if mod else ""))
    lanes.append(("sotif", "; ".join(parts), True))
  else:
    lanes.append(("sotif", "§7: " + re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", log["sotif"]).lstrip("— "), False))
  T = D["tara"]
  ds = [d for d, v in T.ds.items() if h in tara._ids(v["hara"], "H")]
  ts = sorted({x for x, v in T.ts.items() if set(v["damage"]) & set(ds)}, key=lambda x: int(x[3:]))
  if ds:
    top = max(T.risk[x]["risk"] for x in ts) if ts else 0
    lanes.append(("attack", f"{', '.join(ds)} via {len(ts)} threat scenarios · risk up to {top}", True))
  else:
    lanes.append(("attack", f"§7: {log['tara']}; no WP-C-09 §3 damage scenario names {h}", False))
  mis = [e for e in hes if e["misuse"]]
  if mis:
    lanes.append(("misuse", ", ".join(f"{e['id']} {e['asil']}" for e in mis) + " · " + ", ".join(sorted({o for e in mis for o in e["os"]})), True))
  fsrs = [f for f in D["fsrs"] if set(f.serves) & set(sgs)]
  counts = [sum(1 for f in fsrs if D["impl"].get(f.ident, "see §5") == k) for k, _ in IMPL]
  fms = [c for c in D["fms"] if set(c["shs"]) & set(log["sh"])]
  top_ts = [x for x in ts if T.risk[x]["risk"] == max((T.risk[y]["risk"] for y in ts), default=0)]
  holds = []
  if fms:
    st = {c["status"] for c in fms}
    holds.append(("SOTIF", ", ".join(c["fm"] for c in fms) + " (WP-C-07): " +
                  ("partly implemented" if st & {"partial"} else "open"), "#F59E0B" if st & {"partial"} else "#DC2626"))
  if top_ts:
    holds.append(("TARA", f"{', '.join(top_ts)} at risk {T.risk[top_ts[0]]['risk']}: " +
                  "; ".join(sorted({T.risk[x]['treat'] for x in top_ts})), "#F59E0B"))
  return dict(h=h, title=c03["hz"][h]["title"], hes=hes, rep=rep, sgs=sgs, sg_asil={g: c03["sg"][g]["asil"] for g in sgs},
              lanes=lanes, fsr_n=len(fsrs), counts=counts, holds=holds)


# ---------------------------------------------------------------- scenes (the scene kit's strip, from fm_scenes), one per hazard

def go(x0, x1, y=LANE, f1=1.0):
  return sample(lambda f: (x0 + (x1 - x0) * min(1, f / f1), y))


def drift(f0, dy, x0=X0, x1=X1, k=2.0):
  return fm.drifting(f0, dy, x0=x0, x1=x1, k=k)


def h01():
  return road() + [still(200, NEXT)] + ego(drift(0.3, -29, k=1.6)) + [tag(0.8, 140, fm.BELOW, "steers into the next lane", BAD)]


def h02():
  return road() + ego(drift(0.25, 11, k=1.4)) + [tag(0.3, 110, fm.ABOVE, "steering fades, no warning", BAD)]


def h03():
  return road() + [still(240, LANE)] + ego(sample(lambda f: (X0 + 203 * f ** 1.6, LANE))) + [tag(0.7, 130, fm.ABOVE, "accelerates into the lead", BAD)]


def h04():
  stop = 0.4
  xs = lambda f: X0 + 248 * (f if f < stop else stop + (f - stop) * 0.15)
  return road() + [other(sample(lambda f: (min(xs(f) - 26, X0 - 40 + 248 * 0.75 * f), LANE)))] + ego(sample(lambda f: (xs(f), LANE))) + [
    tag(stop, xs(stop) + 40, fm.ABOVE, "hard braking, follower too close", BAD)]


def h05():
  return road() + [still(250, LANE)] + ego(go(X0, 222)) + [tag(0.35, 90, fm.ABOVE, "driver brakes: it keeps driving", BAD)]


def h06():
  return road() + [still(250, LANE), still(226, LANE)] + ego(go(X0, 203, f1=0.85)) + [tag(0.6, 120, fm.ABOVE, "no braking, no warning", BAD)]


def h07():
  return road() + ego(drift(0.3, 11, k=1.4)) + [tag(0.15, 70, fm.ABOVE, "driver believes: it steers", NOTE),
                                               tag(0.65, 180, fm.ABOVE, "it has disengaged: departs", BAD)]


def h08():
  return road() + [still(240, LANE)] + ego(go(X0, 217, f1=0.8)) + [tag(0.6, 150, fm.ABOVE, "stock PCS frame dropped: no AEB", BAD)]


def h09():
  return road() + ego(go(X0, X1)) + [tag(0.2, 80, fm.ABOVE, "eyes off the road", NOTE), tag(0.7, 190, fm.ABOVE, "no escalation", BAD)]


SCENES = dict(zip([f"H-0{i}" for i in range(1, 10)], [h01, h02, h03, h04, h05, h06, h07, h08, h09]))


# ---------------------------------------------------------------- card drawing

COLS, CW, GAP, M = 3, 400, 20, 40
PW = CW - 24
LH = 30                                         # lane height
ST_H = PW * fm.sk.STRIP_H / 280


def converge(px, y, c):
  n = len(c["lanes"])
  h = LH * n + 8
  bw = PW - 92
  nx, ny = px + PW - 34, y + h / 2
  b = [f'<rect x="{px}" y="{y:.1f}" width="{PW}" height="{h}" rx="8" fill="#F8FAFC"/>']
  for i, (kind, text, linked) in enumerate(c["lanes"]):
    col, lab = LANES[kind]
    cy = y + 4 + LH * (i + 0.5)
    dash = "" if linked else ' stroke-dasharray="4 3"'
    line = wrap(text, bw - 16, 8.5)
    line = line[0] + (" …" if len(line) > 1 else "")
    b += [f'<rect x="{px + 6}" y="{cy - 12:.1f}" width="{bw}" height="24" rx="5" fill="#FFFFFF" stroke="{col}" stroke-width="1.2"{dash}/>',
          f'<rect x="{px + 6}" y="{cy - 12:.1f}" width="4" height="24" rx="2" fill="{col}"/>',
          t(px + 16, round(cy - 2, 1), lab, 8.5, col, 700), t(px + 16, round(cy + 8.5, 1), line, 8.5, INK if linked else MUTED),
          f'<path d="M{px + 6 + bw} {cy:.1f} C{px + bw + 30} {cy:.1f} {nx - 36:.1f} {ny:.1f} {nx - 23:.1f} {ny:.1f}" fill="none" '
          f'stroke="{col}" stroke-width="1.5"{dash} marker-end="url(#hl-arr)"/>']
  b += [f'<circle cx="{nx}" cy="{ny:.1f}" r="21" fill="#FEE2E2" stroke="#DC2626" stroke-width="2"/>',
        t(nx, round(ny + 4, 1), c["h"], 11, "#7F1D1D", 700, "middle")]
  return b, h


def fsr_bar(px, y, c):
  b = [t(px, y + 9, f"{c['fsr_n']} FSRs serve {', '.join(c['sgs'])} (WP-C-04 §9)", 9.5, MUTED)]
  y += 14
  bx, bw = px, PW
  tot = sum(c["counts"]) or 1
  x = bx
  for (name, col), n in zip(IMPL, c["counts"]):
    w = bw * n / tot
    if n:
      b.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="12" fill="{col}"/>')
      if w > 16:
        b.append(t(round(x + w / 2, 1), y + 9.5, str(n), 8.5, "#FFFFFF", 700, "middle"))
    x += w
  b.append(t(bx, y + 24, " · ".join(f"{n} {name}" for (name, _), n in zip(IMPL, c["counts"]) if n) or "no FSR traced yet", 8.5, MUTED))
  return b


def card_svg(x, y, c):
  b = [None]
  px, yy = x + 12, y + 26
  b.append(t(px, yy, c["h"], 12, MUTED, 600))
  title = wrap(c["title"], PW - 44, 13.5, True)
  for i, ln in enumerate(title[:2]):
    b.append(t(px + 40, yy + 17 * i, ln, 13.5, INK, 700))
  yy += 17 * (min(len(title), 2) - 1) + 10
  rep = c["rep"]
  chips = [(*ASIL_CHIP[rep["asil"]], f"worst {rep['id']} {rep['s']} {rep['e']} {rep['c']} · {rep['asil']}")]
  chips += [(*ASIL_CHIP[a], f"{g} · ASIL {a}") for g, a in c["sg_asil"].items()]
  chips.append(("#F1F5F9", "#334155", f"{len(c['hes'])} hazardous event{'s' if len(c['hes']) != 1 else ''}"))
  cx = px
  for bg, fg, s in chips:
    w = hf.text_w(s, 10, True) + 14
    if cx + w > px + PW:
      cx, yy = px, yy + 22
    b.append(pill(cx, yy, s, bg, fg, 18, 10)[0])
    cx += w + 6
  yy += 34
  b.append(t(px, yy, "WHAT REACHES IT", 9, MUTED, 700))
  yy += 6
  conv, h = converge(px, yy, c)
  b += conv
  yy += h + 6
  cid = f"hl{c['h']}"
  b.append(f'<svg x="{px}" y="{yy:.1f}" width="{PW}" height="{ST_H:.1f}" viewBox="0 0 280 {fm.sk.STRIP_H}">'
           f'<clipPath id="{cid}"><rect width="280" height="{fm.sk.STRIP_H}" rx="5"/></clipPath><g clip-path="url(#{cid})">' +
           "".join(SCENES[c["h"]]() + [badge(f"{rep['id']} {rep['os'][0] if rep['os'] else ''}".strip(), "#DC2626")]) + "</g></svg>")
  yy += ST_H + 4
  eff = wrap(f"{rep['id']}: {rep['effect']}", PW - 10, 9.5)
  yy += 12
  b.append(t(px, yy, eff[0] + (" …" if len(eff) > 1 else ""), 9.5, MUTED))
  yy += 18
  b.append(t(px, yy, "WHAT HOLDS IT TODAY", 9, MUTED, 700))
  yy += 8
  b += fsr_bar(px, yy, c)
  yy += 48
  for k, v, col in c["holds"]:
    ls = wrap(v, PW - 66, 9.5)
    b.append(f'<circle cx="{px + 4}" cy="{yy - 3.5}" r="3.5" fill="{col}"/>' + t(px + 12, yy, k, 9.5, MUTED, 600))
    for i, ln in enumerate(ls[:2]):
      b.append(t(px + 58, yy + 12 * i, ln + (" …" if i == 1 and len(ls) > 2 else ""), 9.5, INK))
    yy += 12 * min(len(ls), 2) + 4
  return b, yy + 8 - y


def legend(y):
  b, x = [], M
  for col, lab in LANES.values():
    b.append(f'<rect x="{x}" y="{y - 10}" width="14" height="12" rx="2" fill="#FFFFFF" stroke="{col}" stroke-width="1.5"/>')
    b.append(t(x + 20, y, lab, 11, INK))
    x += 30 + hf.text_w(lab, 11) + 8
  b.append(f'<rect x="{x}" y="{y - 10}" width="14" height="12" rx="2" fill="#FFFFFF" stroke="{MUTED}" stroke-dasharray="3 2"/>')
  b.append(t(x + 20, y, "dashed: no entry in that document", 11, INK))
  return b


def sheet(D) -> str:
  hs = sorted(D["c03"]["hz"])
  if missing := [h for h in hs if h not in SCENES]:
    fail(f"no scene for {', '.join(missing)}")
  if extra := [h for h in SCENES if h not in hs]:
    fail(f"scene for {', '.join(extra)}, which WP-C-03 §4 does not define")
  cs = [card_data(h, D) for h in hs]
  w = 2 * M + COLS * CW + (COLS - 1) * GAP
  body = hf.header(w, "Hazard log · what reaches each hazard, and what holds it",
                   "One card per vehicle-level hazard of WP-C-03: malfunctions, insufficiencies, attacks and misuse converge on it.",
                   "WP-C-03 §4-§7 · WP-C-04 · -06 · -07 · -09", "Schematic scenes, not simulation output")
  body += legend(108)
  y, rows = 128, []
  for r in range(0, len(cs), COLS):
    built = [card_svg(M + k * (CW + GAP), y, c) for k, c in enumerate(cs[r:r + COLS])]
    row_h = max(h for _, h in built)
    for (b, _), k in zip(built, range(COLS)):
      b[0] = f'<rect x="{M + k * (CW + GAP)}" y="{y}" width="{CW}" height="{row_h:.0f}" rx="10" fill="#FFFFFF" stroke="{HAIR}"/>'
      rows += b
    y += row_h + GAP
  body += rows
  body.append(t(M, y + 6, "FSR bars: §5 Impl of the WP-C-04 FSRs that the §9 trace marks for the hazard's goals. SOTIF: TCs and evaluations "
                "of WP-C-06 §5; modifications of WP-C-07. TARA: WP-C-09 §3 damage scenarios, §4 threat scenarios, §8 risk.", 10.5, MUTED))
  body.append(t(w - M, y + 24, "Generated by hazlog_cards.py", 10, MUTED, None, "end"))
  desc = (f"{len(cs)} cards, one per hazard of WP-C-03. " +
          " ".join(f"{c['h']} {c['title']}: goals {', '.join(c['sgs'])}; {c['fsr_n']} FSRs, "
                   f"{c['counts'][0]} implemented. " for c in cs))
  defs = ('<marker id="hl-arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">'
          '<path d="M0 0 L8 4 L0 8 Z" fill="#64748B"/></marker>')
  return svg_doc(w, int(y + 36), "Figure 7-1. Hazard log: what reaches each hazard, and what holds it (WP-C-03 §7)", desc, body, defs)


def build(kit=None) -> dict[str, str]:
  """kit: the hara_figures module that calls this (its FigureError); defaults to the one imported here."""
  global K
  K = kit or hf
  return {NAME: sheet(load())}


if __name__ == "__main__":
  sys.exit(hf.main(sys.argv[1:]))
