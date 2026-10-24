#!/usr/bin/env python3
"""Draw the cyber simulation's Figure 1: the TS-14 attack path through LionDriver's zones, isometric and looping.

The path of WP-C-09 AP-14 at the §5 level: the threat scenarios that give the foothold (their risk from WP-C-09 §8),
root on the SoC, the panda envelope, the vehicle bus and the damage scenario with its HARA hazard. The gates on the
boundaries are drawn from the statuses of their WP-S-07 §4 requirements with the barrier convention of WP-C-09
Figures 9-2 and 9-3 and WP-C-10 Figure 7-1: no barrier while all are open, dashed amber while a part is built, dashed
blue while built but not verified, solid green only when all are verified. It shows the credited lens: only a verified
gate stops the path. A pulse travels the path in a 5 s loop (SMIL); a viewer without animation shows the end pose,
the pulse at the hazard.

Risks, damage and hazard come from WP-C-09 through fig_c09_scenes (which checks §8 against §3, §6 and §7); the gate
states from WP-S-07 §4. The zone names, stage labels and what the item sees at each stage are drawings, at the level
of the design note (../README.md §2). The build fails if a source row is missing, a status is not understood, or a
foothold path no longer reads as the drawing assumes. No exploitation detail.

    python3 fig_cy_iso.py            # regenerate the SVG
    python3 fig_cy_iso.py --check    # fail if a source disagrees or the SVG is stale

Standard library only. Output is deterministic. Synthetic (DSR-12): a picture of documented statuses, not a result.
"""

from __future__ import annotations

import math
import re
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "assurance" / "02-concept" / "figures"))
import fig_c09_scenes as fc  # noqa: E402  WP-C-09 tables, §8 checked against §3, §6 and §7

S07 = ROOT / "assurance" / "03-system" / "WP-S-07-cybersecurity-requirements-architecture.md"
NAME = "fig-cy-1-ts14-iso.svg"
W, H = 640, 420
DUR = 5                                       # loop length, s (house rule: a loop over 5 s needs a still alternative)
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
TS = "TS-14"
PRECURSORS = ("TS-06", "TS-08", "TS-09", "TS-10")
GATES = [("CSR-092", "CSR-061"), ("CSR-093",)]  # on the boundaries S3→S4 and S4→S5
STAGES = [("S3", "SoC host", "Z2", "nothing"), ("S4", "Envelope", "Z1", "TX refused (ref. build)"),
          ("S5", "Vehicle bus", "Z5", "—"), ("G", None, None, "driver only")]


class ParseError(Exception):
  pass


def csr_state(cell: str) -> str:
  """State of a WP-S-07 §4 'Evidence at baseline' cell, from its latest dated status where there is one."""
  plain = re.sub(r"\s+", " ", re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cell).replace("**", "").replace("`", "")).strip()
  parts = re.split(r"\b\d{4}-\d{2}-\d{2}:", plain)
  s = parts[-1].strip().lower() if len(parts) > 1 and re.match(r"\s*(implemented|partial|not|verified)", parts[-1].lower()) else plain.lower()
  for key, pat in (("done", r"^(implemented and )?verified"), ("partial", r"^(implemented in part|partial|partly)"),
                   ("unverified", r"^implemented\b.*not verified"), ("open", r"^not (implemented|met|determined)")):
    if re.search(pat, s):
      return key
  raise ParseError(f"WP-S-07 §4 status not understood: '{s[:60]}'")


def barrier(states: list[str]) -> str:
  if all(s == "open" for s in states):
    return "open"
  if all(s == "done" for s in states):
    return "done"
  return "partial" if any(s in ("open", "partial") for s in states) else "unverified"


class Sources:
  def __init__(self, tara: fc.Sources, s07: str):
    self.tara = tara
    cells = {}
    for line in s07.splitlines():
      m = re.match(r"^\| (CSR-\d{3}) \|", line)
      if m:
        cells[m.group(1)] = line.rstrip().rstrip("|").split("|")[-1]
    self.csr = {}
    for ids in GATES:
      for c in ids:
        if c not in cells:
          raise ParseError(f"{c} not found in WP-S-07 §4")
        self.csr[c] = csr_state(cells[c])
    ap14 = tara.ap.get("AP-14", {})
    if TS not in ap14.get("ts", []) or "root on soc" not in ap14.get("entry", "").lower():
      raise ParseError("WP-C-09 §5 AP-14 no longer enters from root on the SoC: redraw the foothold")
    if "root on soc" not in tara.ap["AP-08"]["path"].lower() or "AP-06/AP-08" not in tara.ap["AP-09"]["entry"]:
      raise ParseError("WP-C-09 §5 AP-08 or AP-09 no longer reads as a foothold on the SoC: redraw the precursors")
    self.risk = {t: tara.risk[t]["risk"] for t in (TS,) + PRECURSORS}
    ds = tara.ts[TS]["damage"][0]
    hz = re.match(r"(H-\d\d)", tara.ds[ds]["hara"])
    if not hz:
      raise ParseError(f"{ds}: no HARA hazard in WP-C-09 §3")
    self.goal = (ds, hz.group(1))
    self.walls = [barrier([self.csr[c] for c in ids]) for ids in GATES]


def load() -> Sources:
  return Sources(fc.load(), S07.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------- drawing
STYLE = """
:root{--bg:#FFFFFF;--ink:#1F2328;--muted:#5A6270;--hair:#D0D5DD;--cy:#A21CAF;--cysoft:#FAE8FF;--cyglow:#E879F9;
--prop:#0E7490;--amber:#B45309;--amberfill:#FDE68A;--blue:#0369A1;--green:#15803D;--red:#B91C1C;--redsoft:#FEE2E2;
--top:#E2E8F0;--left:#CBD5E1;--right:#94A3B8;--edge:#64748B;--box:#F8FAFC}
@media (prefers-color-scheme: dark){:root{--bg:#111110;--ink:#F0EFEC;--muted:#A3A29B;--hair:#2C2C2A;--cy:#E879F9;
--cysoft:#2A1030;--cyglow:#D946EF;--prop:#22D3EE;--amber:#FAB219;--amberfill:#3A2A0A;--blue:#38BDF8;--green:#4ADE80;
--red:#F87171;--redsoft:#3B1717;--top:#2B3A4F;--left:#22303F;--right:#1A2532;--edge:#5B7AA6;--box:#1A1A19}}
.bg{fill:var(--bg)}.ink{fill:var(--ink)}.mu{fill:var(--muted)}.cy{fill:var(--cy)}.am{fill:var(--amber)}.rd{fill:var(--red)}
.box{fill:var(--box);stroke:var(--hair)}.hair{stroke:var(--hair)}.cysoft{fill:var(--cysoft);stroke:var(--cy)}
.top{fill:var(--top);stroke:var(--edge)}.lf{fill:var(--left)}.rt{fill:var(--right)}
.gtop{fill:var(--redsoft);stroke:var(--red)}.path{fill:none;stroke:var(--cy);stroke-width:3}
.pulse{fill:var(--cyglow);stroke:var(--cy);stroke-width:2}
.w-partial{fill:var(--amberfill);fill-opacity:.55;stroke:var(--amber);stroke-dasharray:5 4;stroke-width:2}
.w-unverified{fill:none;stroke:var(--blue);stroke-dasharray:5 4;stroke-width:2}
.w-done{fill:none;stroke:var(--green);stroke-width:3}
"""
WALL_TXT = {"open": "no barrier: not built", "partial": "dashed amber: part built", "unverified": "dashed blue: not verified",
            "done": "solid green: verified"}


def t(x, y, s, size=13, cls="ink", weight=None, anchor=None):
  a = f' text-anchor="{anchor}"' if anchor else ""
  w = f' font-weight="{weight}"' if weight else ""
  return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" class="{cls}"{w}{a}>{escape(s)}</text>'


def pts(p):
  return " ".join(f"{x:.1f},{y:.1f}" for x, y in p)


K, C30 = 46.0, math.cos(math.pi / 6)
OX, OY = 262.0, 238.0
STEP, WD = 1.32, 0.78


def iso(x, y, z):
  return (OX + (x - y) * C30 * K, OY + (x + y) * 0.5 * K - z * K)


def slab(u, h, cls_top):
  x0, y0 = u, -u
  T = [iso(x0, y0, h), iso(x0 + WD, y0, h), iso(x0 + WD, y0 + WD, h), iso(x0, y0 + WD, h)]
  B = [iso(x0, y0, 0), iso(x0 + WD, y0, 0), iso(x0 + WD, y0 + WD, 0), iso(x0, y0 + WD, 0)]
  out = [f'<polygon points="{pts([T[1], T[2], B[2], B[1]])}" class="rt"/>',
         f'<polygon points="{pts([T[2], T[3], B[3], B[2]])}" class="lf"/>',
         f'<polygon points="{pts(T)}" class="{cls_top}" stroke-width="1.2"/>']
  c = (sum(p[0] for p in T) / 4, sum(p[1] for p in T) / 4)
  return out, c, max(p[1] for p in B)


def arc(p, q, lift=26, n=16):
  return [(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n - lift * 4 * (k / n) * (1 - k / n)) for k in range(n + 1)]


def svg(S: Sources) -> str:
  b = [f'<rect width="{W}" height="{H}" class="bg"/>',
       t(16, 26, "TS-14: the attack path through LionDriver's zones", 16, "ink", 700),
       t(16, 45, "Credited lens: only a verified gate stops the path, and none is verified yet", 13, "mu")]
  # foothold precursors
  ys = [80 + i * 44 for i in range(len(PRECURSORS))]
  orx, ory = 170.0, 80 + 1.5 * 44 + 17
  for y, ts in zip(ys, PRECURSORS):
    b.append(f'<rect x="16" y="{y}" width="120" height="34" rx="5" class="box"/>')
    b.append(t(26, y + 22, ts, 13, "ink", 600))
    b.append(f'<rect x="80" y="{y + 8}" width="48" height="19" rx="4" class="cysoft"/>')
    b.append(t(104, y + 22, f"risk {S.risk[ts]}", 13, "cy", 600, "middle"))
    b.append(f'<line x1="136" y1="{y + 17}" x2="{orx - 13}" y2="{ory}" class="hair" stroke-width="1.2"/>')
  b.append(f'<circle cx="{orx}" cy="{ory}" r="13" class="box"/>')
  b.append(t(orx, ory + 4.5, "OR", 13, "ink", 700, "middle"))
  b.append(t(16, ys[-1] + 54, "Footholds on the SoC", 13, "mu"))
  b.append(t(16, ys[-1] + 70, "(WP-C-09 §5, §8)", 13, "mu"))
  # platforms
  heights = [0.3, 0.42, 0.3, 0.22]
  cents, bottoms = [], []
  for i, h in enumerate(heights):
    poly, c, bot = slab(i * STEP, h, "gtop" if i == 3 else "top")
    b += poly; cents.append(c); bottoms.append(bot)
  b.append(f'<line x1="{orx + 13}" y1="{ory}" x2="{cents[0][0]:.1f}" y2="{cents[0][1]:.1f}" class="path" stroke-dasharray="4 4"/>')
  # gate walls on the boundaries
  for (ids, state, u) in zip(GATES, S.walls, (STEP - (STEP - WD) / 2, 2 * STEP - (STEP - WD) / 2)):
    q = [iso(u, -u, 0), iso(u, -u + WD, 0), iso(u, -u + WD, 0.55), iso(u, -u, 0.55)]
    if state != "open":
      b.append(f'<polygon points="{pts(q)}" class="w-{state}"><animate attributeName="stroke-width" values="2;4;2" '
               f'dur="{DUR}s" repeatCount="indefinite"/></polygon>')
    tx = (q[2][0] + q[3][0]) / 2; ty = min(p[1] for p in q) - 24
    b.append(t(tx, ty, " · ".join(ids), 13, "am" if state == "partial" else "ink", 600, "middle"))
    b.append(t(tx, ty + 15, state if state != "partial" else "part built", 13, "am" if state == "partial" else "mu", None, "middle"))
  # the path and its pulse
  route = []
  for p, q in zip(cents, cents[1:]):
    route += arc(p, q)[(1 if route else 0):]
  b.append(f'<polyline points="{pts(route)}" class="path" stroke-linejoin="round"/>')
  for c in cents:
    b.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="4" class="cy"/>')
  n = len(route); kt = ";".join(f"{0.8 * k / (n - 1):.4f}" for k in range(n)) + ";1"
  xs = ";".join(f"{p[0]:.1f}" for p in route) + f";{route[-1][0]:.1f}"
  ys_ = ";".join(f"{p[1]:.1f}" for p in route) + f";{route[-1][1]:.1f}"
  b.append(f'<circle cx="{route[-1][0]:.1f}" cy="{route[-1][1]:.1f}" r="7" class="pulse">'
           f'<animate attributeName="cx" values="{xs}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'
           f'<animate attributeName="cy" values="{ys_}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/></circle>')
  # threat pin
  cx0, cy0 = cents[0]
  b.append(f'<line x1="{cx0:.1f}" y1="{cy0:.1f}" x2="{cx0:.1f}" y2="{cy0 - 64:.1f}" stroke="var(--cy)" stroke-width="2"/>')
  b.append(f'<rect x="{cx0 - 56:.1f}" y="{cy0 - 88:.1f}" width="112" height="24" rx="5" class="cy"/>')
  b.append(t(cx0, cy0 - 71, f"{TS} · risk {S.risk[TS]}", 13, "bg", 700, "middle"))
  # stage labels and what the item sees
  ds, hz = S.goal
  base = max(bottoms) + 22
  for (sid, name, zone, sees), c in zip(STAGES, cents):
    if sid == "G":
      b.append(t(c[0], base, f"{ds} → {hz}", 13, "rd", 700, "middle"))
      b.append(t(c[0], base + 16, "hazard", 13, "mu", None, "middle"))
    else:
      b.append(t(c[0], base, f"{sid} {name}", 13, "ink", 700, "middle"))
      b.append(t(c[0], base + 16, zone, 13, "mu", None, "middle"))
  b.append(f'<line x1="200" y1="{base + 30}" x2="{W - 16}" y2="{base + 30}" class="hair"/>')
  b.append(t(200, base + 48, "What the item sees", 13, "mu"))
  for (sid, name, zone, sees), c in zip(STAGES, cents):
    lines = [sees] if len(sees) < 14 else sees.replace(" (", "\n(").split("\n")
    for k, ln in enumerate(lines):
      b.append(t(c[0], base + 66 + 15 * k, ln, 13, "am" if "refused" in ln or "ref." in ln else "ink", None, "middle"))
  b.append(t(16, H - 12, "Synthetic (DSR-12), no evidence credit · WP-C-09 §3, §5, §8 · WP-S-07 §4 · fig_cy_iso.py", 13, "mu"))
  title = "TS-14 attack path through LionDriver's zones, isometric"
  walls = "; ".join(f"gate {' and '.join(ids)} on the boundary after {STAGES[i][0]}: {WALL_TXT[s]}" for i, (ids, s) in enumerate(zip(GATES, S.walls)))
  desc = (f"Threat scenarios {', '.join(PRECURSORS)} (risk {', '.join(str(S.risk[x]) for x in PRECURSORS)}) give a foothold on the "
          f"SoC. From there the {TS} path (risk {S.risk[TS]}) crosses the SoC host, the panda envelope and the vehicle bus to "
          f"{ds} and hazard {hz}. {walls[0].upper() + walls[1:]}. Under the credited lens nothing stops it. A pulse runs the "
          f"path in a {DUR} s loop; the still shows it at the hazard. What the item sees: nothing on the SoC, a refused "
          f"frame at the panda in the reference build only, nothing on the bus, and then only the driver.")
  return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{escape(FONT)}" '
          f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
          f'<style>{STYLE}</style>\n' + "\n".join(b) + "\n</svg>\n")


def build(S: Sources | None = None) -> dict[str, str]:
  return {NAME: svg(S or load())}


def main(argv: list[str]) -> int:
  check = "--check" in argv
  try:
    out = build()
  except (ParseError, fc.ParseError) as e:
    print(f"fig_cy_iso: {e}", file=sys.stderr)
    return 1
  stale = []
  for name, text in out.items():
    p = HERE / name
    if check:
      if not p.exists() or p.read_text(encoding="utf-8") != text:
        stale.append(name)
    else:
      p.write_text(text, encoding="utf-8")
  if stale:
    print("fig_cy_iso: stale, run python3 assurance/sim/cyber/figures/fig_cy_iso.py: " + ", ".join(stale), file=sys.stderr)
    return 1
  print("fig_cy_iso: " + ("up to date" if check else "wrote " + ", ".join(out)))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
