#!/usr/bin/env python3
"""Draw the WP-C-09 threat scene sheets: one card per threat scenario TS-01 … TS-14.

Two sheets, in the order of the §9 top-risk table: Figure 9-2 (`fig-c09-9-2-threat-scenes-risk-5.svg`) holds the risk-5
threat scenarios, Figure 9-3 (`fig-c09-9-3-threat-scenes-risk-3-4.svg`) the rest. Each card shows:

- where the threat scenario sits in the §7 risk matrix (impact level against feasibility);
- what the damage looks like: a looping top-down road scene for the damage scenarios that reach a HARA hazard, a
  "data leaves the device" picture for the privacy and impersonation ones (SMIL, 6 s; a still viewer shows the key
  moment);
- how it gets there at the §5 level (entry point → attack path → asset → damage) with the missing control in red, and a
  treatment that is implemented but not verified in amber;
- what the item trusts against what is true;
- the five attack-potential factors of §6 and the four impact ratings of §3;
- the risk value and treatment of §8, the GAP of §4 and the cybersecurity goals of WP-C-10 §4 that address it.

Ratings, assets, damage, attack paths, risk and treatment come from WP-C-09; goals and CALs from WP-C-10. The titles,
trust lines, step labels and scenes below are drawings that explain each threat scenario at the abstraction WP-C-09 uses:
no exploitation procedure, command sequence or payload. The build fails if a §4 threat scenario has no card, a card names
one that is not there, or the §8 risk table disagrees with §3, §6 or the §7 matrix (impact = highest damage level,
feasibility = highest of the scenario's attack paths, risk = matrix value).

The road scenes and text helpers are shared with the STPA scene cards (`assurance/08-analyses/figures/stpa_scenes.py`).

    python3 fig_c09_scenes.py            # regenerate the SVGs
    python3 fig_c09_scenes.py --check    # fail if a table disagrees, a card is missing or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-09-tara.md"
GOALS = HERE.parent / "WP-C-10-cybersecurity-goals-and-concept.md"
sys.path.insert(0, str(HERE.parents[1] / "08-analyses" / "figures"))
import stpa_scenes as ss  # drawing helpers only; it never imports this module
from stpa_scenes import GRASS, INK, MUTED, RULE, M, P, T, wrap

W, H, GAP = 980, 730, 24
VIOLET = "#7C3AED"
FEAS = ["High", "Medium", "Low", "Very low"]
LEVEL = {"Severe": 4, "Major": 3, "Moderate": 2, "Negligible": 1}
LEVEL_C = {4: ("#FDE4E1", "#B42318"), 3: ("#FCF0D2", "#9A6400"), 2: ("#E3EAF8", "#3B5BA9"), 1: ("#ECEEF1", "#6B7480")}
RISK_FILL = {5: "#F8B4AC", 4: "#FBD3CD", 3: "#FCE9D6", 2: "#F1F3F5", 1: "#F8F9FA"}
EASE = {  # attack-potential factor value -> how easy it makes the attack (0 hardest … 3 easiest), for the tile shade only
  "Hours": 3, "Days": 2, "Weeks": 1, "Months": 0, "Layman": 3, "Proficient": 2, "Expert": 1, "Multiple experts": 0,
  "Public": 3, "Restricted": 2, "Confidential": 1, "Strictly confidential": 0, "Unlimited": 3, "Easy": 3, "Moderate": 2,
  "Limited": 1, "Difficult": 0, "Standard": 3, "Specialized": 2, "Bespoke": 1, "Multiple bespoke": 0,
}
SHEETS = {
  "fig-c09-9-2-threat-scenes-risk-5.svg": ("9-2", "the risk-5 threat scenarios", lambda r: r == 5),
  "fig-c09-9-3-threat-scenes-risk-3-4.svg": ("9-3", "the risk-3 and risk-4 threat scenarios", lambda r: r < 5),
}


class ParseError(Exception):
  pass


# ============================================================================ sources
def _section(doc, num):
  m = re.search(rf"^## {num}\. .*?(?=^## |\Z)", doc, re.M | re.S)
  if not m:
    raise ParseError(f"WP-C-09 §{num} not found")
  return m.group(0)


def _rows(text, pat):
  return [[c.strip() for c in line.strip().strip("|").split(" | ")] for line in text.splitlines() if re.match(rf"^\| {pat} \|", line)]


def _ids(cell, kind):
  """IDs in a cell, expanding ranges such as `DS-01…07` or `DS-08 … 12`."""
  out = []
  for a, b in re.findall(rf"{kind}-(\d+)\s*(?:…\s*(?:{kind}-)?(\d+))?", cell):
    out += [f"{kind}-{n:02d}" for n in range(int(a), int(b or a) + 1)]
  return out


def _plain(s):
  return s.replace("**", "").strip()


class Sources:
  def __init__(self, doc: str, goals: str):
    self.ds = {}
    for c in _rows(_section(doc, 3), r"DS-\d+"):
      self.ds[c[0]] = dict(text=c[1], hara=c[2], imp=[c[3], c[4], c[5], c[6]], level=int(c[7]))
    self.ts = {c[0]: dict(text=c[1], stride=c[2], assets=c[3], damage=_ids(c[5], "DS"), gap=c[6]) for c in _rows(_section(doc, 4), r"TS-\d+")}
    self.ap = {c[0]: dict(entry=c[1], path=c[2], asset=c[3], ts=_ids(c[4], "TS")) for c in _rows(_section(doc, 5), r"AP-\d+")}
    self.feas = {c[0]: dict(factors=c[1:6], feas=_plain(c[6])) for c in _rows(_section(doc, 6), r"AP-\d+")}
    self.matrix = {}
    for c in _rows(_section(doc, 7), r"\*\*\d — \w+\*\*"):
      self.matrix[int(_plain(c[0])[0])] = [int(_plain(x)) for x in c[1:5]]
    self.risk = {c[0]: dict(impact=int(c[1]), feas=c[2], risk=int(_plain(c[3])), treat=_plain(c[4]), why=c[5]) for c in _rows(_section(doc, 8), r"TS-\d+")}
    self.rank = [c[1] for c in _rows(_section(doc, 9), r"\d+")]
    self.csg = {}
    for c in _rows(goals, r"\*\*CSG-\d+\*\*"):
      for t in _ids(c[2], "TS"):
        self.csg.setdefault(t, []).append((_plain(c[0]), _plain(c[3])))
    if not (self.ds and self.ts and self.ap and self.feas and self.matrix and self.risk and self.rank):
      raise ParseError("WP-C-09 tables not found (§3 damage, §4 threats, §5 paths, §6 feasibility, §7 matrix, §8 risk, §9 rank)")
    self.check()

  def paths(self, ts):
    return [a for a, v in self.ap.items() if ts in v["ts"]]

  def check(self):
    """§8 must follow from §3, §6 and §7 (WP-C-09 §6: a threat scenario's feasibility is the highest of its paths)."""
    if sorted(self.rank) != sorted(self.ts) or sorted(self.risk) != sorted(self.ts):
      raise ParseError("WP-C-09 §4, §8 and §9 do not list the same threat scenarios")
    for t, v in self.ts.items():
      r = self.risk[t]
      imp = max(self.ds[d]["level"] for d in v["damage"])
      aps = self.paths(t)
      if not aps:
        raise ParseError(f"{t} has no attack path in WP-C-09 §5")
      feas = min((self.feas[a]["feas"] for a in aps), key=FEAS.index)
      if (r["impact"], r["feas"]) != (imp, feas):
        raise ParseError(f"{t}: §8 gives impact {r['impact']} / {r['feas']}, §3 and §6 give {imp} / {feas}")
      if self.matrix[imp][FEAS.index(feas)] != r["risk"]:
        raise ParseError(f"{t}: §8 risk {r['risk']} is not the §7 matrix value {self.matrix[imp][FEAS.index(feas)]}")

  def impact(self, ts):
    """Highest rating per category (S, F, O, P) over the threat scenario's damage scenarios."""
    return [max((self.ds[d]["imp"][k] for d in self.ts[ts]["damage"]), key=LEVEL.get) for k in range(4)]


def load() -> Sources:
  return Sources(SOURCE.read_text(encoding="utf-8"), GOALS.read_text(encoding="utf-8"))


# ============================================================================ card parts
def marker(mid, fill, size=6, ref=9):
  return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="{ref}" refY="5" markerWidth="{size}" markerHeight="{size}" orient="auto">'
          f'<path d="M0 0L10 5L0 10z" fill="{fill}"/></marker>')


def matrix(S, r):
  o = [M(0, 10, "RISK · IMPACT × FEASIBILITY (§7)", 11, MUTED)]
  for j, f in enumerate(FEAS):
    o.append(T(60 + j * 82 + 41, 28, f, 11, MUTED, anchor="middle"))
  for i, lv in enumerate((4, 3, 2, 1)):
    y = 34 + i * 17
    o.append(T(52, y + 12, f"impact {lv}", 10.5, MUTED, anchor="end"))
    for j in range(4):
      v, on = S.matrix[lv][j], lv == r["impact"] and FEAS[j] == r["feas"]
      stroke = "#B42318" if on else ("#C9A9A4" if v >= 3 else RULE)
      o += [f'<rect x="{60 + j * 82}" y="{y}" width="80" height="15" rx="2" fill="{RISK_FILL[v]}" stroke="{stroke}" stroke-width="{2.4 if on else 1}"/>',
            T(60 + j * 82 + 40, y + 11.5, f"{v}" + ("  ◀ this one" if on else ""), 10.5, INK, 700 if on else 400, "middle")]
  return '<g transform="translate(564 26)">' + "".join(o) + "</g>"


def _short(cell):
  ids = re.findall(r"AS-\d+", cell)
  return ids[0] if len(ids) == 1 else f"{ids[0]} … {ids[-1][3:]}" if ids else ""


def chain(S, ts, m):
  ds = S.ts[ts]["damage"]
  tags = [", ".join(S.paths(ts)), "§5", _short(S.ts[ts]["assets"]), ds[0] if len(ds) == 1 else f"{ds[0]} … {ds[-1][3:]}"]
  heads = ["ENTRY POINT", "ATTACK PATH (§5 LEVEL)", "ASSET", "DAMAGE"]
  kinds = [("#E3EAF8", "#3B5BA9"), ("#FFFFFF", MUTED), ("#FFF4EC", "#C2410C"), ("#FDE4E1", "#B42318")]
  o = ["<defs>" + marker("{id}r", "#DC2626") + marker("{id}g", "#94A3B8") + "</defs>"]
  for i, text in enumerate(m["steps"]):
    y = 16 + i * 56
    f, s = kinds[i]
    o += [f'<rect x="16" y="{y}" width="408" height="34" rx="6" fill="{f}" stroke="{s}" stroke-width="1.4"/>', M(26, y + 13, heads[i], 9.5, s),
          T(26, y + 27, text, 12, INK, 600), T(414, y + 27, tags[i], 11, MUTED, anchor="end")]
    if i < 3:
      ya, yb, red = y + 34, y + 56, m["broken"][0] == i
      o.append(f'<line x1="60" y1="{ya}" x2="60" y2="{yb - 2}" stroke="{"#DC2626" if red else "#94A3B8"}" stroke-width="{3 if red else 1.6}" '
               f'marker-end="url(#{{id}}{"r" if red else "g"})"/>')
      cy = ya + 11
      if red:
        o += [f'<circle cx="60" cy="{cy}" r="8" fill="#DC2626"/>',
              f'<path d="M56 {cy - 4} L64 {cy + 4} M64 {cy - 4} L56 {cy + 4}" stroke="#FFFFFF" stroke-width="2"/>',
              M(76, cy + 4, m["broken"][1], 10.5, "#B42318")]
      if m.get("net") and m["net"][0] == i:
        o.append(M(414, cy + 4, m["net"][1], 10.5, "#9A6400", "end"))
  return o


def factors(S, ts):
  ap = min(S.paths(ts), key=lambda a: FEAS.index(S.feas[a]["feas"]))
  o = [M(0, 12, f"FEASIBILITY FACTORS (§6, {ap}) · DARKER = EASIER FOR THE ATTACKER", 11, MUTED)]
  for i, (k, v) in enumerate(zip(["Elapsed time", "Expertise", "Knowledge", "Window", "Equipment"], S.feas[ap]["factors"], strict=True)):
    v = re.sub(r"\s*\(.*\)", "", v)
    e = EASE.get(v, 1)
    fill = ["#F1F3F5", "#FCE9D6", "#F8B4AC", "#E5484D"][e]
    o += [f'<rect x="{i * 84}" y="20" width="80" height="40" rx="6" fill="{fill}" stroke="{RULE}"/>',
          T(i * 84 + 40, 35, k, 10.5, "#FFE4E1" if e == 3 else MUTED, anchor="middle"), T(i * 84 + 40, 52, v, 12, "#FFFFFF" if e == 3 else INK, 600, "middle")]
  o.append(T(0, 82, f"→ feasibility {S.risk[ts]['feas']}; knowledge is public on every path (open source)", 12, INK, 600))
  o.append(M(0, 108, "IMPACT (§3, HIGHEST OVER THE DAMAGE SCENARIOS)", 11, MUTED))
  for i, (k, v) in enumerate(zip(["Safety", "Financial", "Operational", "Privacy"], S.impact(ts), strict=True)):
    f, s = LEVEL_C[LEVEL[v]]
    o += [f'<rect x="{i * 105}" y="116" width="100" height="40" rx="6" fill="{f}" stroke="{s}"/>', T(i * 105 + 50, 131, k, 10.5, MUTED, anchor="middle"),
          T(i * 105 + 50, 148, v, 12, s, 700, "middle")]
  return '<g transform="translate(516 446)">' + "".join(o) + "</g>"


def data_scene(sc):
  o = ['<rect width="460" height="250" fill="#E8ECEF"/>', '<rect y="150" width="460" height="100" fill="#D5DBE0"/>']
  if sc.get("origin") == "none":
    pass
  elif sc.get("origin") == "server":
    o += ['<g transform="translate(70 120)"><rect x="-44" y="-34" width="88" height="68" rx="6" fill="#64748B"/>'
          + "".join(f'<rect x="-34" y="{y}" width="68" height="10" rx="2" fill="#94A3B8"/><circle cx="26" cy="{y + 5}" r="2" fill="#4ADE80"/>'
                    for y in (-26, -10, 6, 22))
          + "</g>", T(70, 170, sc.get("origin_label", "back end"), 11, "#334155", anchor="middle")]
  else:
    o += ['<g transform="translate(70 150)"><rect x="-50" y="-30" width="100" height="30" rx="8" fill="#9CA3AF"/>'
          '<rect x="-36" y="-50" width="72" height="24" rx="6" fill="#B8C0C8"/><circle cx="-30" cy="2" r="9" fill="#374151"/>'
          '<circle cx="30" cy="2" r="9" fill="#374151"/></g>', T(70, 182, sc.get("origin_label", "the car, parked"), 11, "#334155", anchor="middle")]
  if sc.get("origin") != "none":
    o.append('<path d="M120 130 C160 110 180 112 200 118" fill="none" stroke="#DC2626" stroke-width="2" stroke-dasharray="5 4"/>')
  o += ['<g transform="translate(230 120)"><rect x="-26" y="-18" width="52" height="36" rx="6" fill="#1F2937"/>'
        '<rect x="-20" y="-12" width="40" height="24" rx="3" fill="#374151"/><circle r="5" fill="#60A5FA"/></g>',
        T(230, 156, sc.get("device_label", "the device"), 11, "#334155", anchor="middle")]
  for label, y in zip(sc["items"], (70, 120, 170), strict=False):
    o += [f'<path d="M262 120 C300 120 310 {y} 340 {y}" fill="none" stroke="#DC2626" stroke-width="1.8"/>',
          f'<rect x="342" y="{y - 13}" width="104" height="26" rx="5" fill="#FDE4E1" stroke="#B42318"/>', T(394, y + 4, label, 11.5, "#7F1D1D", 600, "middle")]
  return o + ss.pills(sc["pills"])


def chips(S, ts, m):
  r = S.risk[ts]
  out = [(f"Risk {r['risk']} · {r['treat'].lower()}", "red" if r["risk"] >= 4 else "amber")]
  if "implemented" in r["why"] and "not verified" in r["why"]:
    out.append(("Treatment implemented, not verified", "amber"))
  gap = S.ts[ts]["gap"]
  if gap and gap != "—":
    out.append((gap, None))
  out += [(f"{g} · {cal}", None) for g, cal in S.csg.get(ts, [])]
  out += [(n, None) for n in m.get("notes", ())]
  return out


def card(S, ts, m, x, y, n):
  r = S.risk[ts]
  if len(wrap(m["title"], 38)) > 2:
    raise ParseError(f"{ts} card: title runs over two lines")
  for i, s in enumerate(m["steps"]):
    if ss.tw(s, 12) > 330:
      raise ParseError(f"{ts} card: step {i + 1} label is too long for its box")
  cid = f"t{n}"
  ds = S.ts[ts]["damage"]
  hz = sorted({h for d in ds for h in re.findall(r"H-\d+", S.ds[d]["hara"])})
  dline = (f"{ds[0]} … {ds[-1]}" if len(ds) > 2 else ", ".join(ds)) + (" · reaches " + ", ".join(hz) if hz else " · no HARA hazard")
  o = [f'<g transform="translate({x} {y})"><title>{escape(ts)}: {escape(m["title"])}</title>',
       f'<rect width="{W}" height="{H}" rx="12" fill="#F6F7F8" stroke="{RULE}"/>',
       M(24, 36, f"{ts} · {S.ts[ts]['stride']} · risk {r['risk']}".upper(), 12, VIOLET)]
  o += [T(24, 70 + 30 * i, line, 25, INK, 700) for i, line in enumerate(wrap(m["title"], 38))]
  o += [T(24, 132, dline, 13, MUTED), matrix(S, r)]
  sc = m["scene"]
  body = data_scene(sc) if sc["kind"] == "data" else ss.SCENE[sc["kind"]](sc)
  o += [M(24, 162, "WHAT THE DAMAGE LOOKS LIKE · SCHEMATIC, LOOPS EVERY 6 S", 11, MUTED),
        f'<svg x="24" y="170" width="470" height="255" viewBox="0 0 460 250"><rect width="460" height="250" rx="8" fill="{GRASS}"/>' + "".join(body) + "</svg>",
        M(516, 162, "HOW IT GETS THERE · THE MISSING CONTROL IN RED", 11, MUTED),
        f'<svg x="516" y="170" width="440" height="250" viewBox="0 0 440 250"><rect x="0.5" y="0.5" width="439" height="249" rx="8" fill="#FFFFFF" '
        f'stroke="{RULE}"/>' + "".join(chain(S, ts, m)).replace("{id}", cid) + "</svg>"]
  q, tr = wrap(f"“{m['trusts']}”", 46), wrap(m["true"], 62)
  h1, h2 = 34 + 23 * len(q), 34 + 20 * len(tr)
  if h1 + 10 + h2 > 206:
    raise ParseError(f"{ts} card: trust and truth text too long ({len(q)} + {len(tr)} lines)")
  o += [f'<rect x="24" y="446" width="470" height="{h1}" rx="8" fill="#F3EEFF" stroke="{VIOLET}"/>', M(38, 466, "WHAT THE ITEM TRUSTS", 11, VIOLET)]
  o += [T(38, 490 + 23 * i, line, 17, INK, 600) for i, line in enumerate(q)]
  y2 = 456 + h1
  o += [f'<rect x="24" y="{y2}" width="470" height="{h2}" rx="8" fill="#FFFFFF" stroke="{RULE}"/>', M(38, y2 + 20, "WHAT IS TRUE", 11, MUTED)]
  o += [T(38, y2 + 42 + 20 * i, line, 14) for i, line in enumerate(tr)]
  o.append(factors(S, ts))
  cx, cy = 24, 662
  for text, st in chips(S, ts, m):
    w = ss.tw(text, 12.5) + 22
    if cx + w > W - 24:
      cx, cy = 24, cy + 32
    f, s = {"red": ("#FDE4E1", "#B42318"), "amber": ("#FCF0D2", "#9A6400"), None: ("#FFFFFF", RULE)}[st]
    o += [f'<rect x="{cx:.0f}" y="{cy}" width="{w:.0f}" height="26" rx="13" fill="{f}" stroke="{s}"/>',
          T(cx + 11, cy + 17.5, text, 12.5, s if st else INK, 600 if st else 400)]
    cx += w + 8
  if cy + 26 > H - 8:
    raise ParseError(f"{ts} card: footer chips overflow the card")
  return "".join(o) + "</g>"


def sheet(S, name):
  num, who, keep = SHEETS[name]
  tss = [t for t in S.rank if keep(S.risk[t]["risk"])]
  rows = (len(tss) + 1) // 2
  w, h = GAP + 2 * (W + GAP), 120 + rows * (H + GAP) + 30
  b = [f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>',
       T(GAP, 46, f"Figure {num}. Threat scenes: {who}", 28, INK, 700),
       T(GAP, 76, "Each card: where the threat sits in the risk matrix; what the damage looks like (schematic, loops every 6 s); how it gets there "
                  "at the §5 level, with the missing control in red; what the item trusts; the feasibility factors and impact ratings.", 14, MUTED),
       T(GAP, 98, "Ratings, paths, risk and treatment from WP-C-09, goals from WP-C-10, in the order of the §9 top-risk table. No exploitation "
                  "detail: the cards stay at the abstraction of §5.", 14, MUTED)]
  b += [card(S, t, MODEL[t], GAP + (i % 2) * (W + GAP), 120 + (i // 2) * (H + GAP), i) for i, t in enumerate(tss)]
  b.append(T(GAP, h - 14, f"WP-C-09 Figure {num} · generated by figures/fig_c09_scenes.py; regenerate after any change to WP-C-09 §3–§9 "
                          "or WP-C-10 §4.", 12, MUTED))
  defs = "<defs>" + marker("ah-b", "#93C5FD", 5, 8) + marker("ah-r", "#FCA5A5", 5, 8) + "</defs>"
  title = f"Figure {num}. Threat scenes: {who} (WP-C-09 §9)"
  desc = f"One card per threat scenario, {who}: " + "; ".join(f"{t} {MODEL[t]['title']}" for t in tss) + "."
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">\n'
          f'<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n{defs}\n' + "".join(b) + "\n</svg>\n")


def build(S=None) -> dict[str, str]:
  S = S or load()
  missing, extra = sorted(set(S.ts) - set(MODEL)), sorted(set(MODEL) - set(S.ts))
  if missing or extra:
    raise ParseError(f"scene cards and WP-C-09 §4 differ: no card for {missing or 'none'}, card without a threat scenario {extra or 'none'}")
  return {name: sheet(S, name) for name in SHEETS}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    out = build()
  except ParseError as e:
    print(f"fig_c09_scenes: {e}", file=sys.stderr)
    return 1
  stale = []
  for name, content in out.items():
    p = HERE / name
    if check:
      if not p.exists() or p.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      p.write_text(content, encoding="utf-8")
  if stale:
    print("stale TARA scene sheets; run fig_c09_scenes.py: " + ", ".join(stale), file=sys.stderr)
    return 1
  print(f"fig_c09_scenes: {len(out)} sheets {'current' if check else 'written'}")
  return 0


# ============================================================================ the cards
SWERVE = dict(kind="lat", still=0.62, want=[(20, 157), (440, 157)], act=[(20, 157), (180, 157), (240, 135), (300, 112), (360, 105), (440, 110)],
              actors=[dict(y=93, keys=[(0, 180), (0.92, 420)])])
DRIFT_LAT = dict(kind="lat", still=0.75, want=[(20, 157), (440, 157)], act=[(20, 157), (200, 157), (300, 170), (380, 186), (440, 196)])
PHANTOM = dict(kind="lon", still=0.7, actors=[dict(y=157, body="#DC2626", brake=True, keys=[(0, 40), (0.4, 200), (0.7, 250), (0.92, 262)]),
                                              dict(y=157, keys=[(0, -52), (0.4, 108), (0.7, 190), (0.92, 210)])])
CURVE_DRIFT = dict(kind="curve", still=0.8, want=ss.CURVE, act=[(-10, 70), (100, 70), (190, 70), (250, 72), (310, 84), (360, 108), (400, 138), (430, 172)])
SOC = "Code execution on the SoC (QM user space)"

MODEL: dict[str, dict] = {
  "TS-01": dict(
    title="Forged frames on the vehicle bus reach actuation and plausibility",
    scene=dict(PHANTOM, pills=P((1, "A device on the OBD port or bus", "bad", 0.15, 6), (2, "Forged frames accepted as the car's own", "bad", 0.3, 28),
                                 (3, "The car brakes for nothing; follower closes", "bad", 0.6, 224))),
    steps=["Physical access to the OBD-II port or bus", "Forged frames injected on the car bus", "Actuation and plausibility messages",
           "Unintended steering, braking or acceleration"],
    broken=(1, "received frames not authenticated"),
    trusts="A frame with a valid checksum came from the car's own ECU.",
    true="Received plausibility frames are not authenticated end to end, so a device on the bus can forge them. Physical access "
         "is needed, which keeps feasibility at Medium."),
  "TS-02": dict(
    title="A compromised SoC switches the panda to a permissive safety mode",
    scene=dict(SWERVE, pills=P((1, "Foothold: code runs on the SoC", "bad", 0.15, 6), (2, "Panda told to use another safety mode", "bad", 0.3, 28),
                                (3, "Envelope gone: a full-torque swerve passes", "bad", 0.6, 224))),
    steps=[SOC, "Host-to-panda safety-mode command", "Panda safety mode and parameter", "Envelope limits replaced"],
    broken=(1, "no authentication, no cross-check"), net=(2, "lock: reference build, not verified"),
    trusts="Any safety-mode command from the SoC is genuine.",
    true="The safety-mode command has no authentication or cross-check, so code on the SoC can swap the envelope out. The reference "
         "build now locks the mode in firmware; not yet verified, and the risk is not re-rated (OI-5)."),
  "TS-03": dict(
    title="A compromised SoC puts other firmware on the panda",
    scene=dict(SWERVE, pills=P((1, "Foothold: code runs on the SoC", "bad", 0.15, 6), (2, "The panda boot path loads other firmware", "bad", 0.3, 28),
                                (3, "No envelope: any actuation passes", "bad", 0.6, 224))),
    steps=[SOC, "SoC reprograms the panda via its boot path", "Panda firmware and boot chain", "Envelope replaced or removed"],
    broken=(1, "flash protection not in place"),
    trusts="Only signed firmware ever runs on the safety MCU.",
    true="With code on the SoC, its control of the panda boot path can put other firmware on the MCU, and flash protection "
         "is not yet in place to stop it. The envelope is then whatever that firmware does. Details: private record GD-03."),
  "TS-04": dict(
    title="Forged parameters or messages on the SoC bend the plan or mute monitoring",
    scene=dict(DRIFT_LAT, pills=P((1, "A local process on the SoC", "bad", 0.15, 6), (2, "Forged parameters or IPC messages", "bad", 0.3, 28),
                                   (3, "Wrong path inside the envelope", "bad", 0.6, 224))),
    steps=["A local process on the SoC", "Writes parameters or publishes forged IPC", "Parameters and inter-process messages",
           "Wrong plan, curvature or driver monitoring"],
    broken=(1, "no integrity or authentication"),
    trusts="Every parameter and message comes from the process that should send it.",
    true="Parameters are plain files and inter-process messages carry no authentication, so any local process can change the plan, "
         "the model output or driver monitoring. The panda bounds the torque, not the path."),
  "TS-05": dict(
    title="Firmware signing below target lets other firmware pass as ours",
    scene=dict(SWERVE, pills=P((1, "Firmware built outside LionDriver", "bad", 0.15, 6), (2, "Accepted by the firmware check", "bad", 0.3, 28),
                                (3, "Unsigned-equivalent firmware runs", "bad", 0.6, 224))),
    steps=["Ability to build and flash panda firmware", "Accepted without the release key", "Panda firmware image",
           "Firmware with no assured envelope runs"],
    broken=(1, "signing below CSG-02"),
    trusts="A firmware image that passes the signature check is ours.",
    true="Firmware signing and the exclusion of debug capability are below what CSG-02 needs. An image that passes the check "
         "need not come from LionDriver. Details: GD-01, GD-02."),
  "TS-06": dict(
    title="A malicious update reaches every device through the updater",
    scene=dict(SWERVE, pills=P((1, "Update source controlled", "bad", 0.15, 6), (2, "Devices install it at the next update", "bad", 0.3, 28),
                                (3, "Any SoC-rooted damage, fleet-wide", "bad", 0.6, 224))),
    steps=["Control of the update source", "Device installs it at the next update", "Software update payload",
           "Any SoC-rooted damage, on every device"],
    broken=(1, "no end-to-end signature"),
    trusts="What the update source delivers is a LionDriver release.",
    true="Updates are not authenticated end to end, so whoever controls the update source controls every device that "
         "updates. Automatic updates stay off until signed updates exist. Details: private record GD-05."),
  "TS-07": dict(
    title="Server-directed remote calls take data or open remote access",
    scene=dict(kind="data", origin="server", origin_label="compromised back end", device_label="the device, online",
               items=["log uploads", "remote access", "device data"],
               pills=P((1, "Back end compromised or token stolen", "bad", 0.1, 6), (2, "Remote calls with wide scope", "bad", 0.3, 28),
                       (3, "Data out; access in", "bad", 0.6, 224))),
    steps=["Compromised back end or stolen device token", "Server-directed remote calls", "Remote channel, video, location",
           "Personal data out; impersonation"],
    broken=(1, "call scope wider than needed"),
    trusts="Requests on the remote channel come from a trustworthy back end.",
    true="With the back end compromised or a device token stolen, remote calls reach further than the item needs: data out "
         "and remote access in. Streaming is blocked while driving. Details: private record GD-06."),
  "TS-08": dict(
    title="A build with SSH switched on gives root on the SoC",
    scene=dict(SWERVE, pills=P((1, "Network reach and a valid SSH key", "bad", 0.15, 6), (2, "Root on the SoC", "bad", 0.3, 28),
                                (3, "Every SoC-rooted path opens", "bad", 0.6, 224))),
    steps=["Network reach and a valid SSH key", "Interactive login to the device", "SSH access and the SoC software",
           "Root on the SoC: every SoC path"],
    broken=(1, "pre-provisioned SSH access"),
    trusts="Only the owner can log in to the device.",
    true="Some builds can come with SSH already enabled and a key installed. Anyone with that key and network reach gets "
         "root on the SoC, and from there every SoC-rooted path. Release builds default SSH to off."),
  "TS-09": dict(
    title="A tampered model file runs code when it is loaded",
    scene=dict(DRIFT_LAT, pills=P((1, "A model file is replaced", "bad", 0.15, 6), (2, "Loading it runs code", "bad", 0.3, 28),
                                   (3, "The driving model's output is theirs", "bad", 0.6, 224))),
    steps=["A way to place a model file", "Model loaded without a check", "ML model artefacts", "Code runs in the driving-model process"],
    broken=(1, "no integrity check; load runs code"),
    trusts="A model file is only numbers.",
    true="Model files are loaded in a format that can execute code, and no hash or signature is checked at load. Whoever "
         "can place a model file runs code in the driving-model process."),
  "TS-10": dict(
    title="A compromised upstream flows into every build",
    scene=dict(SWERVE, pills=P((1, "Upstream repo or dependency compromised", "bad", 0.15, 6), (2, "Flows into the next build or sync", "bad", 0.3, 28),
                                (3, "Every device runs it", "bad", 0.6, 224))),
    steps=["Upstream repo, dependency or mutable branch", "Malicious commit reaches the next build", "Supply-chain artefacts",
           "Fleet-wide compromise"],
    broken=(1, "not pinned by commit; no SBOM scan"),
    trusts="Submodules and dependencies are what we reviewed.",
    true="Submodules, wheels and some tool and model branches can change upstream. A malicious commit flows into the next build or "
         "sync of every device."),
  "TS-11": dict(
    title="A stolen device exposes driver video, trips and its identity key",
    scene=dict(kind="data", device_label="the device, removed", items=["driver video", "trip history", "identity key"],
               pills=P((1, "Device taken from the car", "bad", 0.1, 6), (2, "Storage read: not shown to be encrypted", "bad", 0.3, 28),
                       (3, "Video, trips and identity key exposed", "bad", 0.6, 224))),
    steps=["Possession of a stolen or lost device", "Storage at rest read directly", "Driver video, location logs, identity key",
           "Privacy loss; back-end impersonation"],
    broken=(1, "data and key not shown encrypted"),
    trusts="The device stays with its owner.",
    true="Driver video, location logs and the identity key sit on storage that is not shown to be encrypted. Anyone holding the "
         "device can read them, and the key lets them sign as the device."),
  "TS-12": dict(
    title="Flooding the SoC starves the processes that drive",
    scene=dict(CURVE_DRIFT, pills=P((1, "CPU or IPC exhausted", "bad", 0.36, 150), (2, "Soft disable: seconds on stale data", "bad", 0.5, 174),
                                     (3, "The car runs wide", "bad", 0.7, 198))),
    steps=["A foothold or crafted input on the SoC", "CPU or IPC exhausted", "SoC software and its messages", "Stale actuation, silent loss of control"],
    broken=(1, "no temporal partitioning"),
    trusts="If something stalls, control ends at once.",
    true="Nothing partitions the processes that drive from the rest. A stall raises a soft disable, so actuation goes on with stale "
         "data for a few seconds."),
  "TS-13": dict(
    title="Data signed with a stolen key passes as the device's own",
    scene=dict(kind="data", origin="none", device_label="a copy of the key", items=["trip logs", "uploads", "requests"],
               pills=P((1, "Identity key obtained", "bad", 0.1, 6), (2, "Data signed as the device", "bad", 0.3, 28),
                       (3, "Nobody can tell it apart", "bad", 0.6, 224))),
    steps=["Possession of the device identity key", "Data and requests signed as the device", "Device identity key", "Forged data; back-end impersonation"],
    broken=(1, "nothing beyond the device key"),
    trusts="Data signed with the device key came from the device.",
    true="Non-repudiation rests only on the device token and its key. With the key, anyone can sign data and requests that cannot "
         "be told apart from the device's."),
  "TS-14": dict(
    title="A compromised SoC sends camera frames or floods actuation via the panda",
    scene=dict(PHANTOM, pills=P((1, "Foothold: code runs on the SoC", "bad", 0.15, 6), (2, "Frames the panda should refuse pass", "bad", 0.3, 28),
                                 (3, "Braking nobody asked for", "bad", 0.6, 224))),
    steps=[SOC, "Camera-side frames, or an actuation flood", "Actuation and stock PCS messages", "Unintended braking or steering"],
    broken=(1, "transmit checks incomplete"), net=(2, "refused: reference build, not verified"),
    trusts="Every frame the panda lets through is safe to send.",
    true="At the shipped baseline the panda's transmit checks did not cover these frames and rates. The reference build now "
         "refuses them and checks the rate; not verified on hardware. Details: private record GD-11."),
}


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
