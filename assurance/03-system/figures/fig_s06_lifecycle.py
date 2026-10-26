#!/usr/bin/env python3
"""Draw WP-S-06 Figure 3-1, the production and operation requirements over the life of an installed item
(fig-s06-3-1-lifecycle.svg).

One band per phase of WP-S-06 §3 (installation and provisioning, operation, service, software updates,
decommissioning), one tile per requirement TSR-8nn with its ASIL, what it protects (Parent), the procedure steps that
implement it and where it stands:

  defined     the procedure is defined and nothing it needs is missing
  waiting     the procedure is defined but waits on an input (a list, a tolerance, a template, a tool, a work product)
  blocked     cannot be met in substance until a design gap is closed
  design      the design itself now carries part of it (by construction in the reference build, or a system check)
The "Status at baseline" cells are free text, so the status of each requirement is hand-listed in STATUS_OF with a
phrase quoted from its cell; the build fails when a requirement has no entry, an entry has no requirement, or the
phrase is no longer in the cell. A last band shows the design-side TSRs of §4 that would turn manual checks into
system measures, with their status read from the start of the Status cell.

    python3 fig_s06_lifecycle.py            # write the SVG
    python3 fig_s06_lifecycle.py --check    # fail if §3, §4 and STATUS_OF disagree or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, AMBER, AMBER_BG, RED, RED_BG, SAFETY, SAFETY_BG,  # noqa: E402
                                      GREY_BG, text, rect, line, svg, header)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-06-requirements-production-operation.md"
OUT = "fig-s06-3-1-lifecycle.svg"
W = 1280
HEAD = ["ID", "Requirement", "ASIL", "Parent", "Implemented by", "Verification / record", "Status at baseline"]
TEAL, TEAL_BG = "#0F766E", "#F0FDFA"
STATUS = {"defined": ("procedure defined", "#334155", "#F8FAFC"), "waiting": ("waiting on an input", AMBER, AMBER_BG),
          "blocked": ("blocked by a design gap", RED, RED_BG), "design": ("backed by the design", TEAL, TEAL_BG)}

# TSR → (status, phrase quoted from its "Status at baseline" cell).
STATUS_OF = {
  "TSR-801": ("waiting", "release channel not yet defined"),
  "TSR-802": ("blocked", "Blocked in substance by GAP-24/25"),
  "TSR-803": ("defined", "Procedure defined"),
  "TSR-804": ("defined", "so the check confirms it"),
  "TSR-805": ("waiting", "message list pending"),
  "TSR-806": ("design", "absent by construction in the reference build"),
  "TSR-807": ("waiting", "Tolerance band TBD"),
  "TSR-808": ("waiting", "Toyota service information pending"),
  "TSR-809": ("defined", "The 6-month interval is also the latent-fault interval"),
  "TSR-810": ("defined", "Defined"),
  "TSR-811": ("design", "the item itself reads the EPS and ABS/VSC fault codes at start-up"),
  "TSR-812": ("defined", "Defined"),
  "TSR-813": ("waiting", "WP-O-04 pending"),
  "TSR-814": ("waiting", "key-wipe tool pending"),
  "TSR-815": ("waiting", "approved revision TBD"),
  "TSR-816": ("waiting", "Template pending"),
  "TSR-817": ("defined", "Defined"),
  "TSR-818": ("defined", "Defined"),
}
DESIGN = [("not met", ("Not met", "Not started"), RED, RED_BG), ("partial", ("Partial",), AMBER, AMBER_BG),
          ("implemented", ("Implemented",), TEAL, TEAL_BG)]


class LifecycleError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").replace("**", "").replace("~~", "").strip()


def _cells(ln: str) -> list[str]:
  return [x.strip() for x in re.split(r"(?<!\\)\|", ln.strip())[1:-1]]


def parse(md: str) -> tuple[list[tuple[str, list[dict]]], list[dict]]:
  phases, seen = [], set()
  for m in re.finditer(r"^### (3\.\d) (.*?)$(.*?)(?=^##)", md, re.M | re.S):
    reqs = []
    for ln in m.group(3).splitlines():
      if not ln.startswith("| TSR-"):
        continue
      c = dict(zip(HEAD, _cells(ln)))
      tid = c["ID"]
      if tid not in STATUS_OF:
        raise LifecycleError(f"{tid} has no entry in STATUS_OF; classify its status")
      st, phrase = STATUS_OF[tid]
      if phrase not in c["Status at baseline"]:
        raise LifecycleError(f"{tid}: the phrase {phrase!r} is no longer in its status cell; re-classify it")
      seen.add(tid)
      reqs.append({"id": tid, "text": _plain(c["Requirement"]), "asil": _plain(c["ASIL"]), "parent": _plain(c["Parent"]),
                   "by": _plain(c["Implemented by"]), "record": _plain(c["Verification / record"]), "status": st,
                   "note": phrase})
    phases.append((f"{m.group(1)} {_plain(m.group(2))}", reqs))
  stray = set(STATUS_OF) - seen
  if stray:
    raise LifecycleError(f"STATUS_OF lists requirements that WP-S-06 §3 does not have: {sorted(stray)}")
  if not seen:
    raise LifecycleError("WP-S-06 §3 has no TSR rows")
  sec = re.search(r"^## 4\. .*?$(.*?)(?=^## )", md, re.M | re.S)
  if not sec:
    raise LifecycleError("WP-S-06 §4 not found")
  design = []
  for ln in sec.group(1).splitlines():
    c = _cells(ln) if ln.startswith("|") else []
    if len(c) != 3 or c[0] in ("Need",) or set(c[0]) <= set("-: "):
      continue
    kind = next((k for k, prefixes, *_ in DESIGN if _plain(c[2]).startswith(prefixes)), None)
    if kind is None:
      raise LifecycleError(f"WP-S-06 §4: status {c[2]!r} starts with none of {[p for _, ps, *_ in DESIGN for p in ps]}")
    design.append({"need": _plain(c[0]), "tsr": _plain(c[1]), "status": _plain(c[2]), "kind": kind})
  return phases, design


def figure(phases, design) -> str:
  allr = [r for _, rs in phases for r in rs]
  count = {k: sum(r["status"] == k for r in allr) for k in STATUS}
  out = header(W, "3-1", "Production and operation over the life of an installed item",
               f"The {len(allr)} requirements of §3 by phase, each with what it protects, the procedure steps that carry it and "
               f"where it stands: {count['defined']} defined, {count['waiting']} waiting on an input, {count['blocked']} blocked, "
               f"{count['design']} backed by the design", "WP-S-06 §3, §4")
  # the life of the item as a chain of phases
  y = 100
  pw = (W - 80 - 4 * 24) / 5
  for i, (title, reqs) in enumerate(phases):
    x = 40 + i * (pw + 24)
    out.append(rect(x, y, pw, 34, SAFETY_BG, stroke=SAFETY, sw=1.2, rx=17))
    name = re.sub(r"^3\.\d ", "", title).split(" (")[0]
    size = min(12.0, round((pw - 20) / (len(name) * 0.58), 1))  # fit the longest phase name in its pill
    out.append(text(x + pw / 2, y + 22, name, size=size, weight=700, fill=SAFETY, anchor="middle"))
    if i < len(phases) - 1:
      out.append(line(x + pw + 4, y + 17, x + pw + 20, y + 17, stroke=SAFETY, sw=1.6))
      out.append(f'<path d="M{x + pw + 20:.1f} {y + 13}l6 4-6 4z" fill="{SAFETY}"/>')
  y += 52
  COLS, GAP, TH = 3, 10, 116
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  for title, reqs in phases:
    nrow = (len(reqs) + COLS - 1) // COLS
    bh = 38 + nrow * (TH + GAP)
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=12))
    out.append(text(46, y + 24, title, size=13, weight=700))
    for i, r in enumerate(reqs):
      x = 40 + (i % COLS) * (tw + GAP)
      ty = y + 34 + (i // COLS) * (TH + GAP)
      label, col, bg = STATUS[r["status"]]
      out.append(rect(x, ty, tw, TH, fill="#FFFFFF", stroke=col if r["status"] != "defined" else FAINT, sw=1.3, rx=8))
      out.append(text(x + 10, ty + 18, r["id"], size=11.5, weight=700))
      aw = len(r["asil"]) * 6 + 14
      out.append(rect(x + 76, ty + 6, aw, 16, fill=GREY_BG, stroke=LINE, sw=1, rx=8))
      out.append(text(x + 76 + aw / 2, ty + 18, r["asil"], size=9, weight=700, fill=MUTED, anchor="middle"))
      lw = len(label) * 5.6 + 14
      out.append(rect(x + tw - 10 - lw, ty + 6, lw, 16, fill=bg, stroke=col, sw=1, rx=8))
      out.append(text(x + tw - 10 - lw / 2, ty + 18, label, size=9, weight=700, fill=col, anchor="middle"))
      lines = wrap(r["text"], tw - 20, 9.5)
      for j, ln in enumerate(lines[:4]):
        out.append(text(x + 10, ty + 37 + j * 12, ln + ("…" if j == 3 and len(lines) > 4 else ""), size=9.5))
      for j, (k, v) in enumerate((("protects", r["parent"]), ("carried by", r["by"]))):
        txt = f"{k}: {v}"
        cl = wrap(txt, tw - 20, 9)
        out.append(text(x + 10, ty + TH - 22 + j * 12, cl[0] + ("…" if len(cl) > 1 else ""), size=9, fill=MUTED))
    y += bh + 12
  # design measures that replace manual checks
  bh = 38 + len(design) * 22 + 6
  out.append(rect(30, y, W - 60, bh, fill="#FFFFFF", stroke=LINE, sw=1, rx=12))
  out.append(text(46, y + 24, "4 Design measures that turn a manual check into a system measure", size=13, weight=700))
  yy = y + 44
  for d in design:
    label, _, col, bg = next(x for x in DESIGN if x[0] == d["kind"])
    lw = len(label) * 5.8 + 14
    out.append(rect(46, yy - 12, lw, 16, fill=bg, stroke=col, sw=1, rx=8))
    out.append(text(46 + lw / 2, yy, label, size=9, weight=700, fill=col, anchor="middle"))
    out.append(text(150, yy, wrap(d["need"], 600, 10.5)[0], size=10.5))
    out.append(text(780, yy, wrap(f"{d['tsr']} · {d['status']}", W - 830, 10)[0], size=10, fill=MUTED))
    yy += 22
  y += bh + 20
  x = 40
  for k, (label, col, bg) in STATUS.items():
    lw = len(label) * 5.8 + 14
    out.append(rect(x, y - 12, lw, 16, fill=bg, stroke=col, sw=1, rx=8))
    out.append(text(x + lw / 2, y, label, size=9, weight=700, fill=col, anchor="middle"))
    x += lw + 14
  out.append(text(x + 6, y, "The status is read from each requirement's Status cell (STATUS_OF quotes the phrase).",
                  size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Generated by fig_s06_lifecycle.py from WP-S-06 §3 and §4. \"Production\" is installation and "
                  "provisioning of a bought device (tailoring T-07); the procedures are in WP-O-01 to WP-O-05.",
                  size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(allr)} production and operation requirements of WP-S-06 §3. " +
          " ".join(f"{r['id']} ({r['asil']}, {STATUS[r['status']][0]})." for r in allr) +
          " Design measures of §4: " + " ".join(f"{d['tsr']}: {d['kind']}." for d in design))
  return svg(W, h, "Figure 3-1. Production and operation over the life of an installed item (WP-S-06)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(*parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except LifecycleError as e:
    print(f"fig_s06_lifecycle: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s06_lifecycle.py", file=sys.stderr)
    if not stale:
      print(f"fig_s06_lifecycle: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
