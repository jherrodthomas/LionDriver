#!/usr/bin/env python3
"""Draw WP-S-09 Figure 5-1, the vehicle verification cases and what each covers (fig-s09-5-1-cases.svg).

One row per case VS-SQ-nn of WP-S-09 §5, in its §5.x group, with:
  where it runs     from the group: closed course (§5.1, §5.2), recorded data (§5.3), public road after G1 (§5.4)
  what it covers    from the Trace column: assumptions of use (AOU-), each TSR block 1xx…7xx, system requirements (SYS-);
                    a range such as "TSR-1xx…TSR-7xx" covers every block in it
  three flags       run early because it decides a HARA rating (the cases named in OI-4); needs a closed-course test
                    build (the cases named in OI-2); expected to fail (its pass criteria say "Expected to fail")
Everything is read from the document; nothing is hand-listed. No case has been executed.

    python3 fig_s09_cases.py            # write the SVG
    python3 fig_s09_cases.py --check    # fail if §5 or §8 cannot be read or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, AMBER, AMBER_BG, RED, RED_BG, BLUE, BLUE_BG,  # noqa: E402
                                      GREY_BG, SAFETY, SW, text, rect, svg, header, el, line)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-09-system-verification.md"
OUT = "fig-s09-5-1-cases.svg"
W = 1280
COLUMNS = ["AOU", "TSR-1", "TSR-2", "TSR-3", "TSR-4", "TSR-5", "TSR-6", "TSR-7", "SYS"]
HEADS = {"AOU": ("AoU", "vehicle"), "TSR-1": ("1xx", "lateral"), "TSR-2": ("2xx", "longit."), "TSR-3": ("3xx", "engage"),
         "TSR-4": ("4xx", "comms"), "TSR-5": ("5xx", "MCU"), "TSR-6": ("6xx", "host"), "TSR-7": ("7xx", "PCS"),
         "SYS": ("SYS", "system")}
VENUE = {"5.1": ("closed course", SAFETY), "5.2": ("closed course", SAFETY), "5.3": ("recorded data", SW),
         "5.4": ("road, after G1", BLUE)}


class CaseError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").replace("**", "").strip()


def covers(trace: str) -> set[str]:
  out = set()
  if "AOU-" in trace:
    out.add("AOU")
  if "SYS-" in trace:
    out.add("SYS")
  for m in re.finditer(r"TSR-(\d)(?:\d\d|xx)(?:\s*…\s*TSR-(\d)(?:\d\d|xx))?", trace):
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    for d in range(a, b + 1):
      out.add(f"TSR-{d}")
  return out


def _named_cases(md: str, oi: str) -> set[str]:
  m = re.search(rf"^\| {oi} \| (.*?) \|", md, re.M)
  if not m:
    raise CaseError(f"WP-S-09 {oi} not found")
  ids = set()
  for g in re.finditer(r"VS-SQ-(\d\d)((?:,\s*-\d\d)*)", m.group(1)):
    ids.add(f"VS-SQ-{g.group(1)}")
    ids.update(f"VS-SQ-{n}" for n in re.findall(r"-(\d\d)", g.group(2)))
  if not ids:
    raise CaseError(f"{oi} names no VS-SQ case")
  return ids


def parse(md: str) -> list[tuple[str, str, list[dict]]]:
  m = re.search(r"^## 5\. .*?$(.*?)(?=^## 6\. )", md, re.M | re.S)
  if not m:
    raise CaseError("WP-S-09 §5 not found")
  early, build = _named_cases(md, "OI-4"), _named_cases(md, "OI-2")
  groups, ids = [], set()
  for block in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
    head = block.splitlines()[0].strip()
    hm = re.match(r"(5\.\d) (.*)$", head)
    if not hm or hm.group(1) not in VENUE:
      raise CaseError(f"unexpected §5 group {head!r}; give it a venue")
    cases = []
    for ln in block.splitlines():
      if not ln.startswith("| VS-SQ-"):
        continue
      c = [x.strip() for x in ln.strip()[1:-1].split("|")]
      if len(c) != 5:
        raise CaseError(f"{c[0]}: {len(c)} cells, expected 5")
      cov = covers(c[2])
      if not cov:
        raise CaseError(f"{c[0]}: its Trace column names no AoU, TSR or SYS requirement")
      ids.add(c[0])
      cases.append({"id": c[0], "title": _plain(c[1]), "covers": cov, "early": c[0] in early, "build": c[0] in build,
                    "fail": "expected to fail" in _plain(c[4]).lower()})
    groups.append((hm.group(1), hm.group(2), cases))
  for name, s in (("OI-4", early), ("OI-2", build)):
    if s - ids:
      raise CaseError(f"{name} names cases that are not in §5: {sorted(s - ids)}")
  return groups


def figure(groups) -> str:
  allc = [c for *_, cs in groups for c in cs]
  n_fail, n_early, n_build = (sum(c[k] for c in allc) for k in ("fail", "early", "build"))
  out = header(W, "5-1", "The vehicle verification cases and what each covers",
               f"The {len(allc)} cases of §5 by where they run, the requirement groups each covers, and three flags: "
               f"{n_early} decide a HARA rating, {n_build} need a test build, {n_fail} are expected to fail; none executed",
               "WP-S-09 §5, §8")
  X0 = 540
  DX = 50
  X_FLAG = X0 + len(COLUMNS) * DX + 10
  y = 100
  for i, k in enumerate(COLUMNS):
    x = X0 + i * DX + DX / 2
    out.append(text(x, y + 12, HEADS[k][0], size=11.5, weight=700, anchor="middle"))
    out.append(text(x, y + 26, HEADS[k][1], size=9, fill=MUTED, anchor="middle"))
  out.append(text(X_FLAG, y + 12, "Flags", size=11.5, weight=700))
  out.append(text(X_FLAG, y + 26, "early (OI-4) · test build (OI-2) · expected to fail", size=9, fill=MUTED))
  y += 38
  RH = 26
  for sec, title, cases in groups:
    venue, vcol = VENUE[sec]
    bh = 28 + len(cases) * RH + 6
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=10))
    out.append(text(44, y + 19, f"{sec} {title}", size=12.5, weight=700))
    vw = len(venue) * 6.2 + 16
    out.append(rect(X0 - vw - 14, y + 6, vw, 18, fill="#FFFFFF", stroke=vcol, sw=1.2, rx=9))
    out.append(text(X0 - vw / 2 - 14, y + 19, venue, size=9.5, fill=vcol, weight=700, anchor="middle"))
    y += 28
    for c in cases:
      cy = y + RH / 2
      out.append(line(40, y + RH, W - 40, y + RH, stroke="#EEF2F6", sw=1))
      out.append(text(44, cy + 4, c["id"], size=11, weight=700))
      t = wrap(c["title"], X0 - 140 - 20, 11)
      out.append(text(118, cy + 4, t[0] + ("…" if len(t) > 1 else ""), size=11))
      for i, k in enumerate(COLUMNS):
        x = X0 + i * DX + DX / 2
        if k in c["covers"]:
          out.append(el("rect", None, x=f"{x - 8:.1f}", y=f"{cy - 8:.1f}", width=16, height=16, rx=4, fill=SAFETY if k.startswith("TSR") else SW))
        else:
          out.append(el("circle", None, cx=f"{x:.1f}", cy=f"{cy:.1f}", r=2, fill=FAINT))
      fx = X_FLAG
      for key, lab, col, bg in (("early", "early", BLUE, BLUE_BG), ("build", "test build", AMBER, AMBER_BG),
                                ("fail", "expected to fail", RED, RED_BG)):
        if c[key]:
          cw = len(lab) * 5.9 + 14
          out.append(rect(fx, cy - 9, cw, 18, fill=bg, stroke=col, sw=1.1, rx=9))
          out.append(text(fx + cw / 2, cy + 4, lab, size=9.5, fill=col, weight=700, anchor="middle"))
          fx += cw + 6
      y += RH
    y += 16
  y += 10
  out.append(el("rect", None, x=40, y=y - 12, width=16, height=16, rx=4, fill=SAFETY))
  out.append(text(62, y, "covers a TSR block", size=11))
  out.append(el("rect", None, x=200, y=y - 12, width=16, height=16, rx=4, fill=SW))
  out.append(text(222, y, "covers assumptions of use or system requirements", size=11))
  out.append(text(560, y, "TSR blocks 5xx (the MCU platform) are verified on the bench, in WP-S-08, WP-H-06 and WP-V-05.",
                  size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Early: the result decides a HARA controllability rating marked ⚠, so it runs at G1. Test build: a "
                  "closed-course host or panda build that injects out-of-range commands, reflashed after every session (DQ-105 B).",
                  size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s09_cases.py from WP-S-09 §5 (cases and Trace column) and §8 (OI-2, OI-4); "
                  "nothing is hand-listed.", size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(allc)} vehicle verification cases of WP-S-09 §5. " +
          " ".join(f"{c['id']} {c['title']}: covers {', '.join(sorted(c['covers']))}" +
                   "".join(f"; {f}" for f, k in (("early", "early"), ("test build", "build"), ("expected to fail", "fail"))
                           if c[k]) + "." for c in allc))
  return svg(W, h, "Figure 5-1. The vehicle verification cases (WP-S-09 §5)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except CaseError as e:
    print(f"fig_s09_cases: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s09_cases.py", file=sys.stderr)
    if not stale:
      print(f"fig_s09_cases: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
