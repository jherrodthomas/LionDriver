#!/usr/bin/env python3
"""Draw the two figures at the top of the software folder's index page and write that part of the page (index-top.md).

- Figure W-0-1 (`fig-w00-1-software-v.svg`), the software on one page: the V of ISO 26262-6 and ASPICE SWE.1–6 with one
  box per work product. Down the left, the software safety requirements (WP-W-02), the architecture (WP-W-03) and the
  unit design (WP-W-05); at the bottom, the code and its guidelines (WP-W-01); up the right, unit verification (WP-W-06),
  integration (WP-W-07) and embedded testing (WP-W-08), each level verifying the one across from it. Under the V, the
  four activities that run alongside: software safety analysis (WP-W-04), configuration and calibration data (WP-W-09),
  ML engineering (WP-W-10) and cybersecurity implementation (WP-W-11). Each box carries its status in the WP-M-00 §3
  register and the number of IDs its defining tables hold.
- Figure W-0-2 (`fig-w00-2-status.svg`), where the software stands: the software safety requirements by block and
  implementation state (WP-W-02 Baseline column, read through check_state_machines.impl_state), the structural coverage
  of the four safety-layer units against the 100 % target of WP-W-06 (coverage/structural-baseline.json, the ratchet CI
  holds the code to), and the transitions of the three state-machine records by status.

Every count is read from its document or record at build time; the build fails if a document has no row of the kind it
counts, an SWSR state cannot be read, or a work product is missing from the register. index-top.md also holds a gallery
of the folder's diagrams (GALLERY), each checked to exist. folder_index.py places index-top.md at the top of
05-software/README.md, its links rebased.

    python3 fig_w00_overview.py            # write both SVGs and index-top.md
    python3 fig_w00_overview.py --check    # fail if a source changed shape or an output is stale

Standard library only (PyYAML if present, through check_state_machines). Output is deterministic.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOFTWARE = HERE.parent
ASSURANCE = HERE.parents[1]
FOLDER = "05-software"
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
import folder_index  # noqa: E402
from figkit import (INK, MUTED, FAINT, LINE, HAIR, SW, SW_BG, HW, GREEN, GREEN_BG, AMBER, AMBER_BG, RED, RED_BG,  # noqa: E402
                    GREY_BG, SAFETY, SAFETY_BG, FigureError, text, rect, line, path, svg, pill, fit, text_w)
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402
import check_state_machines as csm  # noqa: E402

OUT_V, OUT_S, SECTION = "fig-w00-1-software-v.svg", "fig-w00-2-status.svg", "index-top.md"
COVERAGE = SOFTWARE / "coverage" / "structural-baseline.json"
W = 500
# Work product → (box title, the IDs its defining tables hold as a regex, what one ID is, the section they are in).
WPS = {
  "WP-W-02": ("Software safety requirements", None, "SWSRs", None),
  "WP-W-03": ("Architectural design", r"U-[A-Z]+-[A-Z]+", "panda components (U-…)", "## 3."),
  "WP-W-05": ("Unit design", r"UN-(?:\d+|N\d)", "units (incl. planned)", "## 2."),
  "WP-W-01": ("Code and coding guidelines", r"DEV-\d+", "MISRA deviations", "## 9."),
  "WP-W-06": ("Unit verification", r"VS-UV-\d+", "test cases", "## 6."),
  "WP-W-07": ("Integration verification", r"VS-SWI-\d+", "test cases", "## 5."),
  "WP-W-08": ("Embedded software testing (HIL)", r"VS-SWQ-\d+", "test cases", "## 5."),
  "WP-W-04": ("Software safety analysis", r"SWF-\d\d", "SW FMEA rows", "## 3."),
  "WP-W-09": ("Configuration and calibration data", r"CD-\d+", "data items", "## 3."),
  "WP-W-10": ("ML engineering", r"MLR-\d+", "ML requirements", "## 2."),
  "WP-W-11": ("Cybersecurity implementation", r"CSR-\d+", "CSRs to verify", "## 8."),
}
LEFT, RIGHT, BOTTOM = ["WP-W-02", "WP-W-03", "WP-W-05"], ["WP-W-08", "WP-W-07", "WP-W-06"], "WP-W-01"
SIDE = ["WP-W-04", "WP-W-09", "WP-W-10", "WP-W-11"]
STATE = {"impl": ("in the code", GREEN, GREEN_BG), "partial": ("partly", AMBER, AMBER_BG),
         "not": ("not in the code", RED, RED_BG), "unknown": ("not assessed", MUTED, GREY_BG)}
BLOCKS = {"1": "1xx lateral", "2": "2xx longitudinal", "3": "3xx engagement", "4": "4xx communication",
          "5": "5xx MCU platform", "6": "6xx host", "7": "7xx PCS"}
# The diagrams of the folder shown in the gallery: (path from 05-software/, caption, where it is explained).
GALLERY = [
  ("figures/fig-w05-5-1-uml-sm-toy-auth.svg", "Toyota authority as a UML state machine", "design/README.md"),
  ("figures/fig-w05-5-3-toy-auth-walk.svg", "One engagement, animated", "design/README.md"),
  ("figures/fig-w03-3-2-panda-software-architecture.svg", "Panda firmware component diagram", "WP-W-03-software-architecture.md"),
  ("diagrams/simulink-panda-firmware.svg", "The firmware by execution context", "WP-W-03-software-architecture.md"),
  ("figures/fig-w05-5-2-uml-sm-selfdrived.svg", "Host engagement as a UML state machine", "design/README.md"),
  ("diagrams/simulink-envelope.svg", "The safety envelope's signal flow", "WP-W-05-software-unit-design.md"),
  ("figures/fig-w03-3-1-software-element-hierarchy.svg", "Software element hierarchy", "WP-W-03-software-architecture.md"),
  ("figures/fig-w10-3-1-ml-data-flow.svg", "ML data flow", "WP-W-10-ml-engineering.md"),
  ("hil-bench/figures/fig-hil-3-1-bench-architecture.svg", "HIL bench architecture", "hil-bench/README.md"),
  ("diagrams/simulink-host.svg", "Host data flow", "WP-W-03-software-architecture.md"),
]


def doc(wid: str) -> Path:
  hits = sorted(SOFTWARE.glob(f"{wid}-*.md"))
  if len(hits) != 1:
    raise FigureError(f"{wid}: expected one document in 05-software, found {len(hits)}")
  return hits[0]


def swsrs() -> dict[str, dict]:
  out = {}
  for sid, r in csm.swsr_records().items():
    if r["withdrawn"]:
      continue
    out[sid] = {"state": csm.impl_state(r["baseline"]), "block": sid[5]}
  if not out:
    raise FigureError("trace/items/swsr.yaml has no SWSRs")
  return out


def counts(sw: dict) -> dict[str, int]:
  out = {"WP-W-02": len(sw)}
  for wid, (_t, rx, _what, sec) in WPS.items():
    if rx is None:
      continue
    md = doc(wid).read_text(encoding="utf-8")
    m = re.search(rf"^{re.escape(sec)} .*?$(.*?)(?=^## |\Z)", md, re.M | re.S)
    if not m:
      raise FigureError(f"{wid}: no section {sec}")
    ids = set(re.findall(rf"^\| \*{{0,2}}`?({rx})`?\*{{0,2}} \|", m.group(1), re.M))
    if wid == "WP-W-03":                      # components: the Unit column of the §3.1 catalogue
      ids = set(re.findall(rf"\| ({rx}) \|", m.group(1)))
    if not ids:
      raise FigureError(f"{wid} {sec}: no row with an ID like {rx}")
    out[wid] = len(ids)
  return out


def register() -> dict[str, dict]:
  regs, rg = folder_index.register_rows()
  items = {it["id"]: it for it in regs[FOLDER][1]} if FOLDER in regs else {}
  for wid in WPS:
    if wid not in items:
      raise FigureError(f"{wid} is not in the WP-M-00 §3 register for {FOLDER}/")
    st, names = items[wid]["status"], dict(rg.statuses)
    if st not in names:
      raise FigureError(f"{wid}: register status {st!r} is not one of {list(names)}")
    items[wid] = {**items[wid], "status": names[st]}
  return items


def box(x, y, w, h, wid, n, reg, accent=SW) -> list[str]:
  title, _rx, what, _s = WPS[wid]
  out = [rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, rx=10), rect(x, y + 8, 4, h - 16, fill=accent, stroke="none", rx=2)]
  out.append(text(x + 14, y + 20, fit(title, w - 24, 12, True), size=12, weight=700))
  st = reg[wid]["status"]
  out.append(text(x + 14, y + 36, wid, size=10, fill=MUTED))
  p, _ = pill(x + 14 + text_w(wid, 10) + 8, y + 26, st, AMBER_BG if st == "Draft" else GREEN_BG,
              AMBER if st == "Draft" else GREEN, h=14, size=8.5, stroke=AMBER if st == "Draft" else GREEN)
  out += p
  out.append(text(x + 14, y + 54, f"{n} {what}", size=11, weight=700, fill=accent))
  return out


def figure_v(n: dict, reg: dict) -> str:
  out = [text(16, 30, "The software on one page", size=18, weight=700),
         text(16, 50, "The V of ISO 26262-6 and SWE.1–6: each level on the right", size=11.5, fill=MUTED),
         text(16, 66, "verifies the level across from it on the left.", size=11.5, fill=MUTED)]
  bw, bh, x1, x2 = 222, 64, 16, W - 16 - 222
  ys = [92, 196, 300]
  for i, (a, b) in enumerate(zip(LEFT, RIGHT, strict=True)):
    out += box(x1 + i * 0, ys[i], bw, bh, a, n[a], reg, SW)
    out += box(x2, ys[i], bw, bh, b, n[b], reg, HW)
    yy = ys[i] + bh / 2
    out.append(line(x1 + bw + 4, yy, x2 - 4, yy, stroke=FAINT, sw=1.2, dash="4 3"))
  for i in range(2):
    out.append(line(x1 + 30, ys[i] + bh, x1 + 30, ys[i + 1] - 4, stroke=MUTED, sw=1.6))
    out.append(path(f"M{x1 + 26} {ys[i + 1] - 9} L{x1 + 30} {ys[i + 1] - 2} L{x1 + 34} {ys[i + 1] - 9} Z", stroke="none",
                    fill=MUTED))
    out.append(line(x2 + bw - 30, ys[i + 1], x2 + bw - 30, ys[i] + bh + 4, stroke=MUTED, sw=1.6))
    out.append(path(f"M{x2 + bw - 34} {ys[i] + bh + 9} L{x2 + bw - 30} {ys[i] + bh + 2} L{x2 + bw - 26} {ys[i] + bh + 9} Z",
                    stroke="none", fill=MUTED))
  by = 404
  out += box((W - 300) / 2, by, 300, bh, BOTTOM, n[BOTTOM], reg, INK)
  out.append(path(f"M{x1 + 30} {ys[2] + bh} L{x1 + 30} {by + bh / 2} L{(W - 300) / 2 - 4} {by + bh / 2}", stroke=MUTED, sw=1.6))
  out.append(path(f"M{(W + 300) / 2 + 4} {by + bh / 2} L{x2 + bw - 30} {by + bh / 2} L{x2 + bw - 30} {ys[2] + bh + 4}",
                  stroke=MUTED, sw=1.6))
  out.append(text(W / 2, by + bh + 16, "panda · opendbc · openpilot at their pinned commits", size=10, fill=MUTED,
                  anchor="middle"))
  y = by + bh + 44
  out.append(text(16, y, "Alongside, at every level", size=12.5, weight=700))
  y += 12
  for i, wid in enumerate(SIDE):
    out += box(x1 if i % 2 == 0 else x2, y + (i // 2) * (bh + 10), bw, bh, wid, n[wid], reg, SAFETY)
  y += 2 * (bh + 10) + 14
  out.append(text(16, y, "Counts are the IDs in each document's defining table;", size=10, fill=MUTED))
  out.append(text(16, y + 14, "status from the WP-M-00 §3 register.", size=10, fill=MUTED))
  extra, y = terms.svg_footer(out, 16, y + 34, W - 32, size=10)
  out += extra
  out.append(text(W - 16, y + 6, "Generated by fig_w00_overview.py", size=10, fill=FAINT, anchor="end"))
  desc = "The software V: " + "; ".join(f"{wid} {WPS[wid][0]}, {n[wid]} {WPS[wid][2]}, {reg[wid]['status']}" for wid in WPS)
  return svg(W, int(y + 18), "Figure W-0-1. The software on one page", desc, out)


def bar(x, y, w, h, parts: list[tuple[int, str, str]], total: int) -> list[str]:
  out, xx = [], x
  for k, col, bg in parts:
    if k:
      ww = w * k / total
      out.append(rect(xx, y, ww, h, fill=col, stroke="#FFFFFF", rx=0, sw=1))
      if ww > 16:
        out.append(text(xx + ww / 2, y + h / 2 + 4, str(k), size=10, weight=700, fill="#FFFFFF", anchor="middle"))
      xx += ww
  return out


def figure_status(sw: dict, cov: dict, machines: list[dict]) -> str:
  out = [text(16, 30, "Where the software stands", size=18, weight=700),
         text(16, 50, "Requirements in the code, structural coverage, and the", size=11.5, fill=MUTED),
         text(16, 66, "state-machine transitions, at the current pins.", size=11.5, fill=MUTED)]
  y = 96
  tot = {k: sum(r["state"] == k for r in sw.values()) for k in STATE}
  out.append(text(16, y, f"{len(sw)} software safety requirements (WP-W-02)", size=12.5, weight=700))
  y += 14
  lx = 150
  for b, label in BLOCKS.items():
    rows = [r for r in sw.values() if r["block"] == b]
    if not rows:
      raise FigureError(f"no SWSR in block {b}xx")
    out.append(text(16, y + 13, label, size=10.5))
    parts = [(sum(r["state"] == k for r in rows), c, bg) for k, (_l, c, bg) in STATE.items()]
    out += bar(lx, y, (W - 16 - lx) * len(rows) / max(sum(1 for r in sw.values() if r["block"] == bb) for bb in BLOCKS),
               18, parts, len(rows))
    y += 24
  x = 16
  for k, (label, c, _bg) in STATE.items():
    out.append(rect(x, y + 2, 12, 10, fill=c, stroke="none", rx=2))
    out.append(text(x + 16, y + 11, f"{label} {tot[k]}", size=10, fill=MUTED))
    x += 30 + text_w(f"{label} {tot[k]}", 10)
  y += 40
  units = cov["units"]
  out.append(text(16, y, f"Structural coverage of the safety layer (opendbc {cov['opendbc']})", size=12.5, weight=700))
  out.append(text(16, y + 16, "Target 100 % with justified exclusions (WP-W-06); CI holds the", size=10, fill=MUTED))
  out.append(text(16, y + 29, "gaps to this baseline so they cannot grow.", size=10, fill=MUTED))
  y += 40
  cw = W - 16 - lx - 40
  for u in sorted(units):
    d = units[u]
    for j, (k, lab) in enumerate((("branches", "branch"), ("mcdc", "MC/DC"))):
      tot_k, unc = d[f"{k}_total"], d[f"{k}_uncovered"]
      pct = 100 * (tot_k - unc) / tot_k
      yy = y + j * 14
      if j == 0:
        out.append(text(16, yy + 10, u, size=10.5, weight=700))
      out.append(text(lx - 6, yy + 10, lab, size=9, fill=MUTED, anchor="end"))
      out.append(rect(lx, yy, cw, 11, fill=GREY_BG, stroke="none", rx=2))
      c = GREEN if pct >= 99 else AMBER if pct >= 70 else RED
      out.append(rect(lx, yy, cw * pct / 100, 11, fill=c, stroke="none", rx=2))
      out.append(text(lx + cw + 6, yy + 10, f"{pct:.0f} %", size=10, weight=700, fill=c))
    y += 36
  y += 14
  out.append(text(16, y, "State-machine transitions by status (WP-W-05 §5)", size=12.5, weight=700))
  y += 14
  for sm in machines:
    n_t = len(sm["transitions"])
    out.append(text(16, y + 13, sm["machine"], size=10.5))
    parts = [(sum(t["status"] == k for t in sm["transitions"]), c, bg) for k, (_l, c, bg) in STATE.items()]
    out += bar(lx, y, (W - 16 - lx) * n_t / max(len(m["transitions"]) for m in machines), 18, parts, n_t)
    y += 24
  y += 12
  out.append(text(16, y, "Status from the SWSRs each item realises (WP-W-02 Baseline);", size=10, fill=MUTED))
  out.append(text(16, y + 14, "nothing is verified on hardware yet.", size=10, fill=MUTED))
  extra, y = terms.svg_footer(out, 16, y + 34, W - 32, size=10)
  out += extra
  out.append(text(W - 16, y + 6, "Generated by fig_w00_overview.py", size=10, fill=FAINT, anchor="end"))
  desc = (f"{len(sw)} SWSRs: " + ", ".join(f"{tot[k]} {STATE[k][0]}" for k in STATE) + ". Coverage: " +
          "; ".join(f"{u} branch {100 * (1 - d['branches_uncovered'] / d['branches_total']):.0f} %, MC/DC "
                    f"{100 * (1 - d['mcdc_uncovered'] / d['mcdc_total']):.0f} %" for u, d in sorted(units.items())))
  return svg(W, int(y + 18), "Figure W-0-2. Where the software stands", desc, out)


def machines() -> list[dict]:
  sw = csm.swsr_records()
  out = []
  for p in sorted(csm.SM_DIR.glob("*.yaml")):
    sm = csm.load(p)
    for t in sm["transitions"]:
      t["status"] = csm.transition_state(t, sw)
    out.append(sm)
  return out


def section_md(n: dict, reg: dict, sw: dict, cov: dict) -> str:
  tot = {k: sum(r["state"] == k for r in sw.values()) for k in STATE}
  for p, _c, where in GALLERY:
    for f in (SOFTWARE / p, SOFTWARE / where):
      if not f.exists():
        raise FigureError(f"gallery: {f.relative_to(ASSURANCE)} does not exist")
  def link(wid):
    return f"[{wid}](../{doc(wid).name})"
  lines = ["## The software at a glance", "",
           f"![The software V: software safety requirements ({n['WP-W-02']} SWSRs), architectural design ({n['WP-W-03']} "
           f"components) and unit design ({n['WP-W-05']} units) down the left; the code with {n['WP-W-01']} MISRA deviations "
           f"at the bottom; unit verification ({n['WP-W-06']} cases), integration ({n['WP-W-07']} cases) and embedded testing "
           f"({n['WP-W-08']} cases) up the right; alongside, software safety analysis ({n['WP-W-04']} SW FMEA rows), "
           f"configuration data ({n['WP-W-09']} items), ML engineering ({n['WP-W-10']} requirements) and cybersecurity "
           f"({n['WP-W-11']} CSRs); all draft]({OUT_V})", "",
           "*Figure W-0-1. One box per work product: down the left the design, up the right the verification of each "
           "level, the code at the bottom. Counts are the IDs in each document's defining table, status is the WP-M-00 §3 "
           "register. Generated by [`fig_w00_overview.py`](fig_w00_overview.py).*", "",
           "Each box, and where it is:", ""]
  for wid in LEFT + [BOTTOM] + list(reversed(RIGHT)) + SIDE:
    lines.append(f"- {WPS[wid][0]}: {n[wid]} {WPS[wid][2]}, {link(wid)}")
  lines += ["", "The design walkthrough, with the UML state machines and the animated engagement, is "
            "[`design/`](../design/README.md).", "",
            "## Where the software stands", "",
            f"![Three panels: the {len(sw)} software safety requirements by block, {tot['impl']} in the code, "
            f"{tot['partial']} partly, {tot['not']} not, {tot['unknown']} not assessed; the branch and MC/DC coverage of "
            f"{', '.join(sorted(cov['units']))} against the 100 % target; the transitions of the three state-machine "
            f"records by status]({OUT_S})", "",
            "*Figure W-0-2. Requirements from the WP-W-02 Baseline column, coverage from "
            "[`coverage/structural-baseline.json`](../coverage/structural-baseline.json) (gaps justified in "
            "[`coverage/justifications.md`](../coverage/justifications.md)), transitions from "
            "[`state-machines/`](../state-machines/README.md). Generated by "
            "[`fig_w00_overview.py`](fig_w00_overview.py); CI fails if it is stale.*", "",
            "## Diagrams in this folder", "", "| | |", "|---|---|"]
  cells = [f'<a href="../{where}"><img src="../{p}" width="360" alt="{cap}"></a><br>{cap}' for p, cap, where in GALLERY]
  for i in range(0, len(cells), 2):
    pair = cells[i:i + 2] + [""] * (2 - len(cells[i:i + 2]))
    lines.append(f"| {pair[0]} | {pair[1]} |")
  lines += ["", "Each picture links to the page that explains it."]
  return "\n".join(lines) + "\n"


def build() -> dict[str, str]:
  sw = swsrs()
  n = counts(sw)
  reg = register()
  cov = json.loads(COVERAGE.read_text(encoding="utf-8"))
  if not cov.get("units"):
    raise FigureError(f"{COVERAGE.name}: no units")
  return {OUT_V: figure_v(n, reg), OUT_S: figure_status(sw, cov, machines()), SECTION: section_md(n, reg, sw, cov)}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_w00_overview: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n_ for n_, c in outputs.items() if not (HERE / n_).exists() or (HERE / n_).read_text(encoding="utf-8") != c]
    for n_ in stale:
      print(f"assurance/05-software/figures/{n_} is stale; run fig_w00_overview.py", file=sys.stderr)
    if not stale:
      print(f"fig_w00_overview: {len(outputs)} outputs current")
    return 1 if stale else 0
  for n_, c in outputs.items():
    (HERE / n_).write_text(c, encoding="utf-8")
    print(f"wrote assurance/05-software/figures/{n_}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
