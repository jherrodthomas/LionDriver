#!/usr/bin/env python3
"""Draw WP-S-07 Figure 3-2a, the trust boundaries one by one, animated (fig-s07-3-2a-boundaries-anim.svg).

The figure walks the seven trust boundaries of WP-S-07 §3.2 from the outside in. Each frame lights the boundary on a
stack of the zones of §3.1, then says what crosses it, the threats it faces and the cybersecurity requirements that
control it (the "Controls (CSR)" cell, ranges expanded over the CSRs of §4), each coloured by the status WP-S-07
Figure 4-1 sorts it into (fig_s07_csr_status.STATUS_OF). The last frame shows all seven boundaries side by side, and it
is the frame that stays under reduced motion.

The build fails when a zone or boundary row changes shape, a boundary names a zone that is not in §3.1, or a control
range names a CSR that §4 does not have.

    python3 fig_s07_boundaries_anim.py            # write the SVG
    python3 fig_s07_boundaries_anim.py --check    # fail if §3 changed shape or the SVG is stale

Standard library only. Output is deterministic. CSS animation only, no script.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from figkit import (INK, MUTED, FAINT, LINE, HAIR, RED, AMBER, GREY_BG, FigureError, text, rect, line, path, svg,  # noqa: E402
                    fit, section, table, col, plain)
import fig_s07_csr_status as fc  # noqa: E402
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402

SOURCE = HERE.parent / "WP-S-07-cybersecurity-requirements-architecture.md"
OUT = "fig-s07-3-2a-boundaries-anim.svg"
W = 500
ORDER = ["TB-3", "TB-6", "TB-4", "TB-1", "TB-2", "TB-5", "TB-7"]   # from the outside in, then the device at rest
STACK = ["Z4", "Z6", "Z3", "Z2", "Z1", "Z5", "Z7"]                  # zones top to bottom
DEVICE = ["Z3", "Z2", "Z1"]                                         # the comma device
HOLD = 3.2                                                          # seconds per frame
STATUS_ORDER = ["in", "partly", "not", "check"]


def wrap(s: str, width: float, size: float, bold: bool = False) -> list[str]:
  from figkit import text_w
  out, cur = [], ""
  for word in s.split():
    nxt = f"{cur} {word}".strip()
    if cur and text_w(nxt, size, bold) > width:
      out.append(cur)
      cur = word
    else:
      cur = nxt
  return out + ([cur] if cur else [])


def expand(cell: str, known: list[str]) -> list[str]:
  out = []
  for part in [p.strip() for p in plain(cell).split(",") if p.strip()]:
    m = re.fullmatch(r"(CSR-\d{3})(?:…(CSR-\d{3}))?", part)
    if not m:
      raise FigureError(f"WP-S-07 §3.2: cannot read control {part!r}")
    lo, hi = m.group(1), m.group(2) or m.group(1)
    for end in (lo, hi):
      if end not in known:
        raise FigureError(f"WP-S-07 §3.2 names {end}, which §4 does not have")
    out += [c for c in known if lo <= c <= hi and c not in out]
  return out


def parse(md: str) -> tuple[dict, list[dict]]:
  zhead, zrows = table(section(md, "### 3.1 Elements and security zones"), "Zone")
  zones = {}
  for r in zrows:
    m = re.match(r"(Z\d) (.+)", plain(r[col(zhead, "Zone")]))
    if not m:
      raise FigureError(f"WP-S-07 §3.1: cannot read zone {r[0]!r}")
    zones[m.group(1)] = {"name": m.group(2), "trust": plain(r[col(zhead, "Trust level")])}
  if sorted(zones) != sorted(STACK):
    raise FigureError(f"WP-S-07 §3.1 zones {sorted(zones)} are not the stack {sorted(STACK)}")
  bhead, brows = table(section(md, "### 3.2 Trust boundaries"), "ID")
  known = sorted(fc.STATUS_OF)
  tbs = {}
  for r in brows:
    tb = plain(r[col(bhead, "ID")])
    name = plain(r[col(bhead, "Boundary")])
    zs = re.findall(r"\bZ\d\b", name)
    for z in zs:
      if z not in zones:
        raise FigureError(f"{tb} names zone {z}, which §3.1 does not have")
    if "device" in name and len(zs) == 1:
      zs.append("Z3")
    ctrl = expand(r[col(bhead, "Controls (CSR)")], known)
    tbs[tb] = {"id": tb, "name": name, "zones": zs, "cross": re.sub(r"\s*\(details:[^)]*\)", "", plain(r[col(bhead, "Data / control crossing")])),
               "threats": plain(r[col(bhead, "Threats (TS)")]), "controls": ctrl,
               "count": {s: sum(1 for c in ctrl if fc.STATUS_OF[c][0] == s) for s in STATUS_ORDER}}
  if sorted(tbs) != sorted(ORDER):
    raise FigureError(f"WP-S-07 §3.2 boundaries {sorted(tbs)} are not {sorted(ORDER)}")
  return zones, [tbs[t] for t in ORDER]


def status_colour(s: str) -> tuple[str, str, str]:
  _, c, bg, dash = fc.STATUS[s]
  return c, bg, dash


def headline(tb: dict) -> tuple[str, str]:
  n, c = len(tb["controls"]), tb["count"]
  if c["in"] == 0:
    return f"none of its {n} controls in place", RED
  if c["in"] < n:
    return f"{c['in']} of its {n} controls in place", AMBER
  return f"all {n} controls in place, not verified", fc.STATUS["in"][1]


def figure(zones: dict, tbs: list[dict]) -> str:
  out = [text(16, 30, "Figure 3-2a · The trust boundaries, one by one", size=15, weight=700),
         text(16, 48, "WP-S-07 §3.2, from the outside in; controls by status (§4)", size=11, fill=MUTED)]
  # zone stack
  zx, zw, zh, zg, y0 = 120, 230, 30, 14, 66
  zy = {z: y0 + i * (zh + zg) for i, z in enumerate(STACK)}
  dev_top, dev_bot = zy["Z3"] - 6, zy["Z1"] + zh + 6
  out.append(rect(zx - 10, dev_top, zw + 20, dev_bot - dev_top, fill="none", stroke=FAINT, sw=1, rx=10, dash="3 3"))
  out.append(text(zx + zw + 14, dev_top + 12, "comma device", size=9.5, fill=FAINT))
  for z in STACK:
    trusted = zones[z]["trust"].lower().startswith("trusted")
    out.append(rect(zx, zy[z], zw, zh, fill="#FFFFFF" if not trusted else "#F0FDF4", stroke=LINE, sw=1.1, rx=7))
    out.append(text(zx + 10, zy[z] + 19, fit(f"{z} {zones[z]['name']}", zw - 20, 10.5, True), size=10.5, weight=700))
  # boundary connectors, on the left of the stack, one lane each
  lanes = {t["id"]: i for i, t in enumerate(tbs)}
  geo = {}
  for t in tbs:
    zs = t["zones"]
    lx = zx - 16 - 12 * lanes[t["id"]]
    if len(zs) == 1:
      a = b = zy[zs[0]] + zh / 2
      geo[t["id"]] = (lx, a - 9, a + 9)
    else:
      ya, yb = sorted([zy[zs[0]] + zh / 2, zy[zs[1]] + zh / 2])
      geo[t["id"]] = (lx, ya, yb)

  def connector(tid: str, colour: str, sw: float, label: bool) -> list[str]:
    lx, ya, yb = geo[tid]
    o = [path(f"M{zx} {ya} L{lx} {ya} L{lx} {yb} L{zx} {yb}", stroke=colour, sw=sw)]
    if label:
      o.append(text(lx - 5, (ya + yb) / 2 + 3, tid, size=9.5, weight=700, fill=colour, anchor="end"))
    return o

  for t in tbs:
    out += connector(t["id"], HAIR, 1.2, False)
  ycard = dev_bot + 2 * (zh + zg) + 26
  # frames
  frames = []
  for t in tbs:
    g = connector(t["id"], INK, 2.4, True)
    for z in t["zones"]:
      g.append(rect(zx, zy[z], zw, zh, fill="none", stroke=INK, sw=2, rx=7))
    y = ycard
    g.append(text(16, y, fit(f"{t['id']} · {t['name']}", W - 32, 13, True), size=13, weight=700))
    y += 18
    for ln in wrap(f"Crosses: {t['cross']}", W - 32, 10.5)[:3]:
      g.append(text(16, y, ln, size=10.5, fill=INK))
      y += 14
    g.append(text(16, y, f"Threats: {t['threats']}", size=10.5, fill=MUTED))
    y += 22
    head, hc = headline(t)
    g.append(text(16, y, head, size=12, weight=700, fill=hc))
    y += 10
    x = 16
    for c in t["controls"]:
      colour, bg, dash = status_colour(fc.STATUS_OF[c][0])
      wpill = 60
      if x + wpill > W - 16:
        x, y = 16, y + 22
      g.append(rect(x, y, wpill - 4, 17, fill=bg, stroke=colour, sw=1.2, rx=5, dash=dash))
      g.append(text(x + (wpill - 4) / 2, y + 12, c, size=9, weight=700, fill=colour, anchor="middle"))
      x += wpill
    frames.append(g)
  # summary frame: every boundary with its bar
  g = []
  for t in tbs:
    g += connector(t["id"], headline(t)[1], 2.2, False)
  y = ycard
  g.append(text(16, y, "All seven boundaries: their controls by status", size=13, weight=700))
  y += 16
  g.append(text(16, y, "Red: no control in place. Amber: some.", size=10.5, fill=MUTED))
  y += 14
  bx, bw = 64, W - 64 - 130
  for t in tbs:
    n = len(t["controls"])
    g.append(text(16, y + 12, t["id"], size=10.5, weight=700))
    x = bx
    for s in STATUS_ORDER:
      if not t["count"][s]:
        continue
      colour, bg, dash = status_colour(s)
      wseg = bw * t["count"][s] / n
      g.append(rect(x, y + 2, wseg, 13, fill=bg, stroke=colour, sw=1, rx=3, dash=dash))
      x += wseg
    head, hc = headline(t)
    g.append(text(bx + bw + 8, y + 12, f"{t['count']['in']}/{n} in place", size=10, fill=hc, weight=700))
    y += 19
  frames.append(g)
  n = len(frames)
  loop = HOLD * n
  css = [f".fr{{opacity:0;animation:{loop:g}s steps(1,end) infinite}}"]
  for i in range(n):
    a, b = 100 * i / n, 100 * (i + 1) / n
    css.append(f"@keyframes k{i}{{0%{{opacity:{1 if i == 0 else 0}}}{a:.2f}%{{opacity:1}}{b:.2f}%{{opacity:0}}"
               f"100%{{opacity:{1 if i == 0 else 0}}}}}.f{i}{{animation-name:k{i}}}")
  css.append(f"@media (prefers-reduced-motion:reduce){{.fr{{animation:none}}.f{n - 1}{{opacity:1}}}}")
  out.insert(0, f"<style>{''.join(css)}</style>")
  for i, g in enumerate(frames):
    out += [f'<g class="fr f{i}">', *g, "</g>"]
  # legend and footer
  y = ycard + 30 + 19 * len(tbs) + 26
  y = max(y, ycard + 150)
  x = 16
  for s in STATUS_ORDER:
    lab, colour, bg, dash = fc.STATUS[s]
    lab = lab.replace(", not verified", "")
    out.append(rect(x, y - 11, 22, 14, fill=bg, stroke=colour, sw=1.2, rx=4, dash=dash))
    out.append(text(x + 28, y, lab, size=10.5))
    x += 28 + len(lab) * 6 + 18
  y += 18
  out.append(text(16, y, "None is verified. Status: WP-S-07 Figure 4-1. Generated by fig_s07_boundaries_anim.py.",
                  size=10, fill=MUTED))
  extra, y = terms.svg_footer(out, 16, y + 20, W - 32, size=10)
  out += extra
  desc = "Trust boundaries of WP-S-07 §3.2, one per frame: " + "; ".join(
    f"{t['id']} {t['name']}, {len(t['controls'])} controls, {t['count']['in']} in place, {t['count']['partly']} partly, "
    f"{t['count']['not']} not met, {t['count']['check']} not determined" for t in tbs) + "."
  return svg(W, int(y + 14), "Figure 3-2a. The trust boundaries, one by one (WP-S-07 §3.2), animated", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(*parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_s07_boundaries_anim: {e}", file=sys.stderr)
    return 1
  stale = []
  for name, content in outputs.items():
    p = HERE / name
    if "--check" in argv:
      if not p.exists() or p.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      p.write_text(content, encoding="utf-8")
  if stale:
    print(f"fig_s07_boundaries_anim: stale {', '.join(stale)}; run python3 {Path(__file__).name}", file=sys.stderr)
    return 1
  print("fig_s07_boundaries_anim: " + ("up to date" if "--check" in argv else f"wrote {', '.join(outputs)}"))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
