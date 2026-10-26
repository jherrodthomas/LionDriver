#!/usr/bin/env python3
"""Draw WP-S-01 Figure 10-1, the system requirements by function (fig-s01-10-1-requirements.svg).

One tile per system requirement SYS-nnn of WP-S-01 §2-§9, in the group of its function, with:
  type          F functional, P performance, I interface, H HMI, C constraint (or two, "F/P")
  target TBD    the requirement or its Target / criterion cell still contains TBD: the value is not set (OI-1)
  verification  the methods of the Verif column
  test case     whether a specified test case verifies it, read from the SysML model's coverage report
                (models/sysml/generated/requirements-coverage.md, generated and checked in CI)
Everything is read from the document and the model; nothing is hand-listed.

    python3 fig_s01_requirements.py            # write the SVG
    python3 fig_s01_requirements.py --check    # fail if a table cannot be read or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, AMBER, AMBER_BG, RED, RED_BG, BLUE, SW,  # noqa: E402
                                      GREY_BG, text, rect, svg, header)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-01-system-requirements.md"
COVERAGE = HERE.parents[1] / "models" / "sysml" / "generated" / "requirements-coverage.md"
OUT = "fig-s01-10-1-requirements.svg"
W = 1280
TYPES = {"F": "functional", "P": "performance", "I": "interface", "H": "HMI", "C": "constraint"}


class SysError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").replace("**", "").strip()


def unverified(cov: str) -> set[str]:
  m = re.search(r"^## SYS: not verified by any case \(\d+\)\n\n(.*?)$", cov, re.M)
  if m is None:
    if re.search(r"^## SYS: not verified", cov, re.M):
      raise SysError("cannot read the SYS list of the coverage report")
    return set()
  return set(re.findall(r"SYS-\d{3}", m.group(1)))


def parse(md: str, cov: str) -> list[tuple[str, list[dict]]]:
  groups, seen = [], set()
  missing_case = unverified(cov)
  for m in re.finditer(r"^## (\d+)\. (F-\d\d(?: / F-\d\d)?) (.*?)$(.*?)(?=^## )", md, re.M | re.S):
    reqs = []
    for ln in m.group(4).splitlines():
      if not ln.startswith("| SYS-"):
        continue
      c = [x.strip() for x in ln.strip()[1:-1].split("|")]
      if len(c) < 6:
        raise SysError(f"{c[0]}: {len(c)} cells, expected at least 6")
      types = [t for t in re.split(r"[/, ]+", c[2]) if t]
      bad = [t for t in types if t not in TYPES]
      if bad:
        raise SysError(f"{c[0]}: unknown type {bad}")
      seen.add(c[0])
      reqs.append({"id": c[0], "text": _plain(c[1]), "types": types, "tbd": "TBD" in c[1] + c[3],
                   "verif": _plain(c[4]), "case": c[0] not in missing_case})
    groups.append((f"{m.group(2)} {_plain(m.group(3))}", reqs))
  if not seen:
    raise SysError("WP-S-01 has no SYS rows")
  stray = missing_case - seen
  if stray:
    raise SysError(f"the coverage report names SYS requirements that WP-S-01 does not have: {sorted(stray)}")
  return groups


def figure(groups) -> str:
  allr = [r for _, rs in groups for r in rs]
  n_tbd = sum(r["tbd"] for r in allr)
  n_nocase = sum(not r["case"] for r in allr)
  out = header(W, "10-1", "The system requirements by function",
               f"The {len(allr)} system requirements of §2–§9, each with its type, its verification methods and two flags: "
               f"{n_tbd} with a target still TBD, {n_nocase} with no test case yet", "WP-S-01 · SysML coverage")
  COLS, GAP, TH = 4, 10, 92
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  y = 104
  for title, reqs in groups:
    nrow = (len(reqs) + COLS - 1) // COLS
    bh = 38 + nrow * (TH + GAP)
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=12))
    out.append(text(46, y + 24, title, size=13, weight=700))
    for i, r in enumerate(reqs):
      x = 40 + (i % COLS) * (tw + GAP)
      ty = y + 34 + (i // COLS) * (TH + GAP)
      out.append(rect(x, ty, tw, TH, fill="#FFFFFF", stroke=FAINT, sw=1.2, rx=8))
      out.append(text(x + 10, ty + 18, r["id"], size=11.5, weight=700))
      cx = x + 74
      for t in r["types"]:
        lab = TYPES[t]
        cw = len(lab) * 5.6 + 12
        out.append(rect(cx, ty + 6, cw, 16, fill=GREY_BG, stroke=LINE, sw=1, rx=8))
        out.append(text(cx + cw / 2, ty + 18, lab, size=9, fill=MUTED, weight=700, anchor="middle"))
        cx += cw + 4
      lines = wrap(r["text"], tw - 20, 9.5)
      for j, ln in enumerate(lines[:3]):
        out.append(text(x + 10, ty + 36 + j * 12, ln + ("…" if j == 2 and len(lines) > 3 else ""), size=9.5))
      fx = x + 10
      fy = ty + TH - 20
      for on, lab, col, bg in ((r["tbd"], "target TBD", AMBER, AMBER_BG), (not r["case"], "no test case", RED, RED_BG)):
        if on:
          cw = len(lab) * 5.7 + 12
          out.append(rect(fx, fy, cw, 15, fill=bg, stroke=col, sw=1, rx=7.5))
          out.append(text(fx + cw / 2, fy + 11, lab, size=9, fill=col, weight=700, anchor="middle"))
          fx += cw + 4
      out.append(text(x + tw - 10, fy + 11, r["verif"], size=9, fill=MUTED, anchor="end"))
    y += bh + 12
  y += 8
  for lab, col, bg, x in (("target TBD: the value is not set yet (OI-1)", AMBER, AMBER_BG, 40),
                          ("no test case: no specified case verifies it (WP-S-09 OI-6)", RED, RED_BG, 380)):
    out.append(rect(x, y - 12, 30, 15, fill=bg, stroke=col, sw=1, rx=7.5))
    out.append(text(x + 38, y, lab, size=11))
  y += 18
  out.append(text(40, y, "Verification methods: A analysis · R review · T-SIL software test or process replay · T-HIL bench test · "
                  "T-VEH vehicle test · LOG drive-log analysis · SIM simulation.", size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s01_requirements.py from WP-S-01 §2–§9 and the coverage report of the SysML model; "
                  "nothing is hand-listed. These are the non-safety requirements; the safety ones are the TSRs of WP-S-02.",
                  size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(allr)} system requirements of WP-S-01. " +
          " ".join(f"{r['id']} ({'/'.join(r['types'])}, {r['verif']}" + (", target TBD" if r["tbd"] else "") +
                   ("" if r["case"] else ", no test case") + ")." for r in allr))
  return svg(W, h, "Figure 10-1. The system requirements by function (WP-S-01)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8"), COVERAGE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except SysError as e:
    print(f"fig_s01_requirements: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s01_requirements.py", file=sys.stderr)
    if not stale:
      print(f"fig_s01_requirements: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
