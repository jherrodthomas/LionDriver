#!/usr/bin/env python3
"""Draw WP-S-03 Figure 6-2, the safety mechanism map (fig-s03-6-2-safety-mechanisms.svg).

One tile per safety mechanism of the WP-S-03 §6 catalogue, grouped by the element that carries it (the first element
of its Element column): the safety layer E-03a, the panda platform firmware E-03b, the safety MCU hardware E-04a, and
the QM host E-01/E-02. Each tile has the mechanism, the fault it covers, its TSRs, its diagnostic-coverage target and
its status. A second element in the Element column is drawn as a tag on the tile.

Status, from the §6 Status column (the conservative rule drawn in the figure, see `classify`):
  the latest status is the bold part after "at baseline;" when there is one, otherwise the whole cell; each part
  separated by "/" is read by its first word: Impl or Met = implemented, Partial = partly, New or Not = not
  implemented, Unknown = unknown; parts that disagree make the mechanism partly implemented.
Nothing is verified: "implemented" is drawn blue, never green, as in Figure 6-1.

    python3 fig_s03_mechanisms.py            # write the SVG
    python3 fig_s03_mechanisms.py --check    # fail if the SVG is stale or the catalogue cannot be read

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-S-03-technical-safety-concept-architecture.md"
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, HAIR, SAFETY, SAFETY_BG, SW, AMBER, AMBER_BG,  # noqa: E402
                                      RED, RED_BG, BLUE, BLUE_BG, GREY_BG, text, rect, line, svg, header)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

OUT = "fig-s03-6-2-safety-mechanisms.svg"

# Element groups, in drawing order: the elements of WP-S-03 §3.1 that carry a mechanism first.
GROUPS = [
  ("E-03a", "Safety layer", "opendbc safety core and Toyota mode in the panda firmware"),
  ("E-03b", "Panda platform firmware", "main loop, drivers, comms handlers, fault handling"),
  ("E-04a", "Safety MCU hardware", "STM32H7, clock, supply, memories, CAN, siren path"),
  ("E-01", "Host SoC software and models", "openpilot processes and ML models (E-01, E-02)"),
]
ELEMENT_RE = re.compile(r"E-0\d[ab]?")
STATUS = {  # class -> (label, stroke, fill, text colour)
  "impl": ("implemented", BLUE, BLUE_BG, BLUE),
  "partial": ("partly", AMBER, AMBER_BG, "#92400E"),
  "not": ("not implemented", RED, RED_BG, "#991B1B"),
  "unknown": ("unknown", FAINT, GREY_BG, MUTED),
}


class MechanismError(ValueError):
  pass


def _cells(ln: str) -> list[str]:
  return [c.strip() for c in ln.strip()[1:-1].split("|")]


def _plain(s: str) -> str:
  return s.replace("**", "").replace("`", "")


def classify(status: str) -> str:
  """Status class of one §6 Status cell (see the module docstring)."""
  s = status
  m = re.search(r"at baseline; \*\*(.+?)\*\*", s)
  if m:
    s = m.group(1)
  s = re.sub(r"\([^)]*\)", "", _plain(s))
  classes = set()
  for part in re.split(r"\s*/\s*", s):
    word = part.strip().split(" ")[0].rstrip(",;").lower()
    if word in ("impl", "met"):
      classes.add("impl")
    elif word == "partial":
      classes.add("partial")
    elif word in ("new", "not"):
      classes.add("not")
    elif word == "unknown":
      classes.add("unknown")
    elif word:
      raise MechanismError(f"cannot read status {status!r}")
  if not classes:
    raise MechanismError(f"empty status {status!r}")
  return classes.pop() if len(classes) == 1 else "partial"


def elements(cell: str) -> list[str]:
  """'E-03a/b' -> ['E-03a', 'E-03b']; 'E-01 (HMI)' -> ['E-01']; 'E-01/E-02' -> ['E-01', 'E-02']."""
  out: list[str] = []
  for part in cell.split("/"):
    part = part.strip()
    if re.fullmatch(r"[ab]", part) and out:
      part = out[-1][:-1] + part
    m = ELEMENT_RE.match(part)
    if not m:
      raise MechanismError(f"cannot read element {cell!r}")
    out.append(m.group(0))
  return out


def parse(md: str) -> tuple[list[dict], dict[str, str]]:
  m = re.search(r"^## 6\. .*?$(.*?)(?=^## \d+\. )", md, re.M | re.S)
  if not m:
    raise MechanismError("WP-S-03 §6 not found")
  sms = []
  for ln in m.group(1).splitlines():
    if not ln.startswith("| SM-"):
      continue
    c = _cells(ln)
    if len(c) != 8:
      raise MechanismError(f"{c[0]}: {len(c)} cells, expected 8")
    els = elements(c[3])
    sms.append({"id": c[0], "name": _plain(c[1]), "covers": _plain(c[2]), "elements": els, "tsr": _plain(c[4]),
                "status": classify(c[5]), "dc": _plain(c[6])})
  if not sms:
    raise MechanismError("no SM rows in §6")
  m = re.search(r"^### 3\.1 .*?$(.*?)(?=^### |^## )", md, re.M | re.S)
  integrity = {}
  for ln in (m.group(1) if m else "").splitlines():
    if ln.startswith("| E-0"):
      c = _cells(ln)
      integrity[c[0].split()[0]] = _plain(c[2])
  for g, *_ in GROUPS:
    if g not in integrity:
      raise MechanismError(f"§3.1 has no integrity for {g}")
  known = {g for g, *_ in GROUPS} | {"E-02", "E-05"}
  for s in sms:
    if s["elements"][0] == "E-02" or not set(s["elements"]) <= known:
      raise MechanismError(f"{s['id']}: element {s['elements']} has no group")
  return sms, integrity


def group_of(sm: dict) -> str:
  return sm["elements"][0]


def tile(x: float, y: float, w: float, h: float, sm: dict, out: list[str]) -> None:
  label, stroke, fill, tc = STATUS[sm["status"]]
  dash = "4 3" if sm["status"] == "unknown" else ""
  out.append(rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, sw=1, rx=8))
  out.append(rect(x, y, 5, h, fill=stroke, stroke="none", sw=0, rx=2))
  out.append(text(x + 14, y + 20, sm["id"], size=12, weight=700))
  cw = len(label) * 6.1 + 16
  out.append(rect(x + w - cw - 10, y + 8, cw, 17, fill=fill, stroke=stroke, sw=1, rx=8.5, dash=dash))
  out.append(text(x + w - cw / 2 - 10, y + 20, label, size=9.5, fill=tc, weight=700, anchor="middle"))
  extra = [e for e in sm["elements"][1:]]
  tx = x + 62
  for e in extra:
    out.append(rect(tx, y + 8, 46, 17, fill=GREY_BG, stroke=LINE, sw=1, rx=4))
    out.append(text(tx + 23, y + 20, "+" + e, size=9.5, fill=MUTED, weight=600, anchor="middle"))
    tx += 50
  yy = y + 40
  for ln in wrap(sm["name"], w - 28, 11.5, True)[:2]:
    out.append(text(x + 14, yy, ln, size=11.5, weight=600))
    yy += 15
  for ln in wrap("Covers: " + sm["covers"], w - 28, 10)[:2]:
    out.append(text(x + 14, yy, ln, size=10, fill=MUTED))
    yy += 13
  foot = f"TSR {sm['tsr']} · DC {sm['dc']}"
  foot = wrap(foot, w - 28, 9.5)[0] + ("…" if len(wrap(foot, w - 28, 9.5)) > 1 else "")
  out.append(text(x + 14, y + h - 10, foot, size=9.5, fill=MUTED))


def figure(sms: list[dict], integrity: dict[str, str]) -> str:
  W, COLS, GAP = 1280, 4, 12
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  TH = 104
  out = header(W, "6-2", "Safety mechanisms by element",
               f"The {len(sms)} mechanisms of the §6 catalogue on the element that carries them, with the fault each "
               "covers, its TSRs, its DC target and its status", "WP-S-03 §3.1, §6")
  y = 108
  for g, title, sub in GROUPS:
    mine = [s for s in sms if group_of(s) == g]
    if not mine:
      continue
    integ = integrity[g]
    qm = integ.startswith("QM")
    col, bg = (SW, "#F0FDFA") if qm else (SAFETY, SAFETY_BG)
    rows = (len(mine) + COLS - 1) // COLS
    bh = 44 + rows * (TH + GAP)
    out.append(rect(30, y, W - 60, bh, fill=bg, stroke=col, sw=1.2, rx=12))
    out.append(text(46, y + 26, f"{g} · {title}", size=14, weight=700))
    out.append(text(46 + len(f"{g} · {title}") * 8.3 + 14, y + 26, sub, size=11, fill=MUTED))
    pill = f"{'QM' if qm else 'ASIL ' + integ} · {len(mine)} mechanisms"
    pw = len(pill) * 6.4 + 18
    out.append(rect(W - 46 - pw, y + 12, pw, 20, fill=col, stroke="none", sw=0, rx=10))
    out.append(text(W - 46 - pw / 2, y + 26, pill, size=10.5, fill="#FFFFFF", weight=700, anchor="middle"))
    for i, sm in enumerate(mine):
      tile(40 + (i % COLS) * (tw + GAP), y + 40 + (i // COLS) * (TH + GAP), tw, TH, sm, out)
    y += bh + 14
  y += 8
  counts = {k: sum(1 for s in sms if s["status"] == k) for k in STATUS}
  lx = 40
  for k, (label, stroke, fill, tc) in STATUS.items():
    out.append(rect(lx, y - 11, 30, 15, fill=fill, stroke=stroke, sw=1, rx=7.5, dash="4 3" if k == "unknown" else ""))
    s = f"{label} ({counts[k]})"
    out.append(text(lx + 38, y, s, size=11))
    lx += 38 + len(s) * 6.3 + 22
  out.append(rect(lx, y - 11, 46, 15, fill=GREY_BG, stroke=LINE, sw=1, rx=4))
  out.append(text(lx + 23, y, "+E-0x", size=9.5, fill=MUTED, weight=600, anchor="middle"))
  out.append(text(lx + 54, y, "also carried by that element", size=11))
  y += 22
  out.append(text(40, y, "Status is the latest in §6 (the reference build where it is given). Nothing is verified: implemented "
                  "means the code does it, drawn blue, not green. Mixed statuses (Impl / Partial) count as partly.", size=11, fill=MUTED))
  y += 16
  out.append(text(40, y, "DC targets are targets for the FMEDA (WP-H-03) and software safety analysis (WP-W-04), not "
                  "demonstrated. Generated by fig_s03_mechanisms.py from WP-S-03 §3.1 and §6.", size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(sms)} safety mechanisms of WP-S-03 §6 grouped by element. "
          + " ".join(f"{g}: " + ", ".join(f"{s['id']} {s['name']} ({STATUS[s['status']][0]})" for s in sms if group_of(s) == g) + "."
                     for g, *_ in GROUPS))
  return svg(W, h, "Figure 6-2. Safety mechanisms by element (WP-S-03 §6)", desc, out)


def build() -> dict[str, str]:
  sms, integrity = parse(SOURCE.read_text(encoding="utf-8"))
  return {OUT: figure(sms, integrity)}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except MechanismError as e:
    print(f"fig_s03_mechanisms: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, t in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != t]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s03_mechanisms.py")
    if not stale:
      print(f"safety mechanism map: {len(outputs)} up to date")
    return 1 if stale else 0
  for n, t in outputs.items():
    (HERE / n).write_text(t, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
