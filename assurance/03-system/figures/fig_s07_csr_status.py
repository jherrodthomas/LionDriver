#!/usr/bin/env python3
"""Draw WP-S-07 Figure 4-1, the cybersecurity requirements and where each stands (fig-s07-4-1-csr-status.svg).

One tile per detailed cybersecurity requirement CSR-nnn of WP-S-07 §4, in the sixteen groups of its parent CSR-C-nn,
each with its statement, its allocation (FW firmware, SoC host, ENV environment, USR user procedure) and its status:

  in        in place, not verified
  partly    partly in place, or in the reference build only in part
  not       not met or not implemented
  check     not determined; to verify
The "Evidence at baseline" cells are free text that grows a dated note per change, so the status of each CSR is
hand-listed in STATUS_OF with a phrase quoted from its cell. The build fails when a CSR has no entry, an entry has no
CSR, or the phrase is no longer in the cell, so a changed status is re-sorted on purpose.

    python3 fig_s07_csr_status.py            # write the SVG
    python3 fig_s07_csr_status.py --check    # fail if §4 and STATUS_OF disagree or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fig_s03_defence_in_depth import (INK, MUTED, FAINT, LINE, AMBER, AMBER_BG, RED, RED_BG, BLUE, BLUE_BG,  # noqa: E402
                                      GREY_BG, text, rect, svg, header)
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)
sys.path.insert(0, str(HERE.parents[1] / "02-concept" / "hara"))
from hara_figures import wrap  # noqa: E402

SOURCE = HERE.parent / "WP-S-07-cybersecurity-requirements-architecture.md"
OUT = "fig-s07-4-1-csr-status.svg"
W = 1280

# CSR → (status, phrase quoted from its "Evidence at baseline" cell, the latest note where there is one).
STATUS_OF = {
  "CSR-011": ("in", 'Implemented, not verified (reference build)'),
  "CSR-012": ("partly", 'the lead decided (DQ-082, B)'),
  "CSR-013": ("in", 'Implemented generically'),
  "CSR-014": ("partly", 'Partial (reference build)'),
  "CSR-015": ("in", 'Implemented, not verified (reference build)'),
  "CSR-016": ("not", 'unchanged (TSR-619 not implemented)'),
  "CSR-021": ("not", 'Not met (GAP-25'),
  "CSR-022": ("partly", 'Conditional: correct only if CSR-021 holds'),
  "CSR-023": ("partly", 'Partial: some debug-only commands gated'),
  "CSR-024": ("partly", 'Partial (reference build)'),
  "CSR-031": ("not", 'Not met: the baseline scheme is weaker than required'),
  "CSR-032": ("not", "Not met: the bootstub verifies against comma's key"),
  "CSR-033": ("partly", 'Partial: compile-time minimum only'),
  "CSR-034": ("not", 'Not implemented (GAP-24)'),
  "CSR-041": ("not", 'Not implemented (GAP-38)'),
  "CSR-042": ("not", 'Not implemented (details: private record GD-01)'),
  "CSR-043": ("not", 'INS-17 today (version/signature only)'),
  "CSR-051": ("not", 'Not met (GAP-38; details'),
  "CSR-052": ("not", 'Not met (details: private record GD-03)'),
  "CSR-053": ("partly", 'Partial: checked against the locally built image'),
  "CSR-054": ("not", 'Not met (GAP-38); depends on'),
  "CSR-061": ("partly", 'Partly met by design (limits'),
  "CSR-062": ("not", 'Not implemented (GAP-20)'),
  "CSR-063": ("not", 'Not implemented (GAP-20)'),
  "CSR-064": ("check", 'Not determined: process user/privilege model'),
  "CSR-071": ("in", 'Implemented in the reference build (DQ-131 A'),
  "CSR-072": ("in", 'Implemented in host software, not verified on the vehicle'),
  "CSR-073": ("partly", 'Partly (DQ-131 A)'),
  "CSR-081": ("not", 'Not met (GAP-22'),
  "CSR-082": ("not", 'Not implemented (GAP-22)'),
  "CSR-083": ("not", 'Not met: `.lfsconfig` points to'),
  "CSR-091": ("partly", 'Partial: 8-bit checksums on some'),
  "CSR-092": ("partly", 'PCS and DSU IDs removed'),
  "CSR-093": ("partly", 'Partial: relay-malfunction detection on intercepted'),
  "CSR-101": ("not", 'Not met for INTERNAL builds'),
  "CSR-102": ("in", 'Process exists'),
  "CSR-103": ("check", 'To verify against AGNOS sshd'),
  "CSR-104": ("not", 'Not implemented (proposal; decision OI-3)'),
  "CSR-111": ("not", 'Not met upstream'),
  "CSR-112": ("partly", '(DQ-121 A)'),
  "CSR-113": ("not", 'Not met if enabled'),
  "CSR-114": ("not", 'Not met if enabled'),
  "CSR-115": ("not", 'Not met (details: private record GD-06)'),
  "CSR-116": ("in", 'Implemented: `params_keys.h:62`'),
  "CSR-117": ("check", 'Believed met (athenad is not'),
  "CSR-121": ("not", 'Not implemented: TLS and in-tree hashes only'),
  "CSR-122": ("not", 'Not met (details: private record GD-05)'),
  "CSR-123": ("not", 'Not implemented'),
  "CSR-124": ("in", 'Mechanism exists'),
  "CSR-125": ("partly", 'Partial: offroad-only'),
  "CSR-126": ("not", 'Not implemented ([WP-O-05]'),
  "CSR-131": ("not", 'Not met: relative URLs to'),
  "CSR-132": ("not", 'Not met: cppcheck from `rev=release-cppcheck`'),
  "CSR-133": ("not", 'Not implemented ([WP-M-09]'),
  "CSR-134": ("not", 'Not implemented ([WP-W-11]'),
  "CSR-135": ("not", 'No LionDriver signing in CI'),
  "CSR-141": ("check", 'To verify (details'),
  "CSR-142": ("check", 'Unknown (WP-C-09 OI-3)'),
  "CSR-143": ("check", 'To verify per uploader'),
  "CSR-144": ("check", 'Depends on `RecordFront` and uploader'),
  "CSR-151": ("partly", 'Procedure drafted ([WP-O-02]'),
  "CSR-152": ("partly", 'Procedure drafted (DEC-09, DEC-10)'),
  "CSR-161": ("not", 'Not met: `SECURITY.md:5` routes to'),
  "CSR-162": ("not", 'Not running'),
}
STATUS = {"in": ("in place, not verified", BLUE, BLUE_BG, ""), "partly": ("partly", AMBER, AMBER_BG, ""),
          "not": ("not met", RED, RED_BG, ""), "check": ("not determined", MUTED, GREY_BG, "4 3")}


class CsrError(ValueError):
  pass


def _plain(s: str) -> str:
  s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
  return s.replace("`", "").replace("**", "").strip()


def parse(md: str) -> list[dict]:
  m = re.search(r"^## 4\. .*?$(.*?)(?=^## 5\. )", md, re.M | re.S)
  if not m:
    raise CsrError("WP-S-07 §4 not found")
  groups = []
  for block in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
    title = block.splitlines()[0].strip()
    hm = re.match(r"4\.\d+ (CSR-C-\d\d) (.*?) \((?:(.*?), )?CAL (\d)\)$", title)
    if not hm:
      raise CsrError(f"cannot read group heading {title!r}")
    reqs = []
    for ln in block.splitlines():
      if not ln.startswith("| CSR-"):
        continue
      c = [x.strip() for x in ln.strip()[1:-1].split("|")]
      if len(c) != 6:
        raise CsrError(f"{c[0]}: {len(c)} cells, expected 6")
      if c[0] not in STATUS_OF:
        raise CsrError(f"{c[0]} has no entry in STATUS_OF; sort it")
      st, phrase = STATUS_OF[c[0]]
      if phrase not in c[5]:
        raise CsrError(f"{c[0]}: phrase {phrase!r} is no longer in its evidence cell; re-sort it")
      reqs.append({"id": c[0], "text": _plain(c[1]), "alloc": [a.strip() for a in c[2].split(";")], "status": st})
    groups.append({"parent": hm.group(1), "name": hm.group(2), "csg": hm.group(3) or "no goal", "cal": hm.group(4),
                   "reqs": reqs})
  ids = {r["id"] for g in groups for r in g["reqs"]}
  extra = set(STATUS_OF) - ids
  if extra:
    raise CsrError(f"STATUS_OF entries without a CSR in §4: {sorted(extra)}")
  return groups


def figure(groups: list[dict]) -> str:
  allr = [r for g in groups for r in g["reqs"]]
  counts = {k: sum(1 for r in allr if r["status"] == k) for k in STATUS}
  out = header(W, "4-1", "The cybersecurity requirements and where each stands",
               f"The {len(allr)} requirements of §4 in their sixteen groups, each with its allocation and status: "
               f"{counts['in']} in place, {counts['partly']} partly, {counts['not']} not met, {counts['check']} not "
               "determined; none verified", "WP-S-07 §4")
  COLS, GAP, TH = 4, 10, 84
  tw = (W - 80 - (COLS - 1) * GAP) / COLS
  y = 104
  for g in groups:
    nrow = (len(g["reqs"]) + COLS - 1) // COLS
    bh = 38 + nrow * (TH + GAP)
    out.append(rect(30, y, W - 60, bh, fill="#F8FAFC", stroke=LINE, sw=1, rx=12))
    title = f"{g['parent']} {g['name']}"
    out.append(text(46, y + 24, title, size=13, weight=700))
    out.append(text(46 + len(title) * 7.6 + 12, y + 24, f"{g['csg']} · CAL {g['cal']}", size=11, fill=MUTED))
    for i, r in enumerate(g["reqs"]):
      x = 40 + (i % COLS) * (tw + GAP)
      ty = y + 34 + (i // COLS) * (TH + GAP)
      lab, col, bg, dash = STATUS[r["status"]]
      out.append(rect(x, ty, tw, TH, fill=bg, stroke=col, sw=1.4, rx=8, dash=dash))
      out.append(text(x + 10, ty + 18, r["id"], size=11.5, weight=700))
      cx = x + tw - 8
      for a in reversed(r["alloc"]):
        cw = len(a) * 6.4 + 10
        cx -= cw
        out.append(rect(cx, ty + 6, cw, 16, fill="#FFFFFF", stroke=FAINT, sw=1, rx=4))
        out.append(text(cx + cw / 2, ty + 18, a, size=9.5, fill=MUTED, weight=700, anchor="middle"))
        cx -= 4
      lines = wrap(r["text"], tw - 20, 9.5)
      for j, ln in enumerate(lines[:4]):
        out.append(text(x + 10, ty + 36 + j * 12, ln + ("…" if j == 3 and len(lines) > 4 else ""), size=9.5, fill=INK))
    y += bh + 12
  y += 8
  lx = 40
  for k, (lab, col, bg, dash) in STATUS.items():
    s = f"{lab} ({counts[k]})"
    out.append(rect(lx, y - 12, 30, 16, fill=bg, stroke=col, sw=1.4, rx=6, dash=dash))
    out.append(text(lx + 38, y, s, size=11))
    lx += 38 + len(s) * 6.3 + 22
  y += 18
  out.append(text(40, y, "Allocation: FW panda firmware · SoC host software · ENV build and release environment · "
                  "USR user procedure.", size=11, fill=MUTED))
  y += 18
  out.append(text(40, y, "Status is the latest dated note of the Evidence column (the reference build where one is given). "
                  "Generated by fig_s07_csr_status.py from WP-S-07 §4.", size=11, fill=MUTED))
  extra, y = terms.svg_footer(out, 40, y + 22, W - 80)
  out += extra
  h = int(y + 12)
  desc = (f"{len(allr)} cybersecurity requirements of WP-S-07 §4. " +
          " ".join(f"{g['parent']}: " + ", ".join(f"{r['id']} ({STATUS[r['status']][0]})" for r in g["reqs"]) + "."
                   for g in groups))
  return svg(W, h, "Figure 4-1. The cybersecurity requirements and where each stands (WP-S-07 §4)", desc, out)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except CsrError as e:
    print(f"fig_s07_csr_status: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/03-system/figures/{n} is stale; run fig_s07_csr_status.py", file=sys.stderr)
    if not stale:
      print(f"fig_s07_csr_status: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/03-system/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
