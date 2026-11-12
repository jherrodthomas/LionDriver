#!/usr/bin/env python3
"""Gate readiness: what each gate G0…G6 still needs before it can be reviewed, side by side.

It reads the gate review skeletons that the process model generates (10-safety-case/gates/skeletons/G<n>-skeleton.md,
written by assurance/process/tools/process_model.py from WP-M-00, WP-M-02, WP-M-06 and the IFR items, and checked
in CI). For each gate:

- work products: how many are approved or baselined, by status, from "Work products of this gate";
- open items: the sum of that table's "Open items" column;
- confirmation measures: how many have a record, from "Confirmation measures" (a record "not present" or a record
  work product "not approved" is not performed); a gate with no such section has none assigned;
- interfaces: how many due by the gate are agreed ("Yes" in "Agreed?"), from "Cross-domain interfaces due by this gate";
- roles: those listed as not assigned, from "Roles WP-M-02 §3.1 needs by this gate that are not assigned";
- exit criteria: counted from "Exit criteria"; whether each is met is for the gate review, so the board does not judge.

The next gate is the first without a passed review record (fig_m00_vcycle.build_model). One picture and one page,
`assurance/01-management/vcycle/gates.md`, which links each gate to its skeleton and lists what stands between now
and the next gate, with links.

Fails (FigureError) when a skeleton is missing, a required section or column is missing, a status word is unknown, or
an "Agreed?" cell holds anything but "Yes" or blank. Called by fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(A / "trace" / "tools"))

import figkit as fk  # noqa: E402
from figkit import FigureError, rect, text  # noqa: E402
import terms  # noqa: E402
import vcycle_explode as vx  # noqa: E402

SKELETONS = A / "10-safety-case" / "gates" / "skeletons"
SVG = "fig-m00-vcycle-gates.svg"
PAGE = "gates.md"
STATUSES = [("Approved", fk.GREEN), ("Baselined", fk.GREEN_DARK), ("In review", fk.HW), ("Draft", fk.AMBER),
            ("Skeleton", fk.LINE), ("Tailored out", fk.FAINT)]
W, LX, LW = 1640, 40, 250


# ---------------------------------------------------------------- reading the skeletons

def rows_of(md: str, heading: str, first: str, optional: bool = False) -> tuple[list[str], list[list[str]]]:
  try:
    return fk.table(fk.section(md, heading), first)
  except FigureError:
    if optional and not re.search(rf"^{re.escape(heading)}", md, re.M):
      return [first], []
    raise


def read_gate(n: int) -> dict:
  path = SKELETONS / f"G{n}-skeleton.md"
  if not path.exists():
    raise FigureError(f"{path.relative_to(A.parent)} is missing; run assurance/process/tools/process_model.py")
  md = path.read_text(encoding="utf-8")
  m = re.search(r"^# G\d gate review — (.+)$", md, re.M)
  if not m:
    raise FigureError(f"G{n} skeleton: no title line")
  head, rows = rows_of(md, "### Work products of this gate", "Work product")
  cw, cs, co = (fk.col(head, c) for c in ("Work product", "Status in WP-M-00", "Open items"))
  known = {s for s, _ in STATUSES}
  wps = []
  for r in rows:
    wid = re.search(r"\[(WP-[A-Z]-\d\d)\]", r[cw])
    status = fk.plain(r[cs])
    if status not in known:
      raise FigureError(f"G{n} skeleton: {r[cw][:40]} has unknown status {status!r}")
    if not r[co].strip().isdigit():
      raise FigureError(f"G{n} skeleton: open items {r[co]!r} is not a number")
    wps.append({"id": wid.group(1) if wid else fk.plain(r[cw]), "status": status, "open": int(r[co])})
  head, rows = rows_of(md, "### Confirmation measures", "Measure", optional=True)
  measures = []
  if rows:
    cm, cr = fk.col(head, "Measure"), fk.col(head, "Record")
    measures = [{"id": fk.plain(r[cm]).split()[0], "name": " ".join(fk.plain(r[cm]).split()[1:]),
                 "done": not re.search(r"not (present|approved)", r[cr])} for r in rows]
  head, rows = rows_of(md, "### Cross-domain interfaces due by this gate", "IFR", optional=True)
  ifrs = []
  if rows:
    ci, ct, ca = fk.col(head, "IFR"), fk.col(head, "Title"), fk.col(head, "Agreed?")
    for r in rows:
      if r[ca].strip() not in ("", "Yes"):
        raise FigureError(f"G{n} skeleton: {r[ci]} has Agreed? {r[ca]!r}; expected Yes or blank")
      ifrs.append({"id": fk.plain(r[ci]), "title": fk.plain(r[ct]), "agreed": r[ca].strip() == "Yes"})
  head, rows = rows_of(md, "### Roles WP-M-02 §3.1 needs by this gate that are not assigned", "Role", optional=True)
  roles = [fk.plain(r[0]) for r in rows]
  _, rows = rows_of(md, "## Exit criteria", "Criterion")
  return {"gate": f"G{n}", "name": m.group(1).strip(), "wps": wps, "measures": measures, "ifrs": ifrs,
          "roles": roles, "exit": [fk.plain(r[0]) for r in rows], "skeleton": path}


def model(m: dict) -> dict:
  gates = [read_gate(n) for n in range(7)]
  when = {p["gate"]: p for p in m["phases"]}
  for g in gates:
    g["when"], g["passed"] = when[g["gate"]]["when"], when[g["gate"]]["passed"]
  nxt = next((g for g in gates if not g["passed"]), gates[-1])
  return {"gates": gates, "next": nxt}


# ---------------------------------------------------------------- drawing

def tone(done: int, total: int) -> str:
  if not total:
    return fk.FAINT
  return fk.GREEN if done == total else (fk.RED if done == 0 else fk.AMBER)


ROWS = [("Work products approved", "status in WP-M-00"), ("Open items in them", "rows not marked closed"),
        ("Confirmation measures performed", "WP-M-06, record in confirmation/"),
        ("Interfaces agreed (due by the gate)", "IFR items, agreed by recorded review"),
        ("Roles the gate needs, unassigned", "WP-M-02 §3.1"), ("Exit criteria", "WP-M-00 §2, judged at the review")]


def cell(i: int, g: dict, x: float, y: float, w: float) -> list[str]:
  out: list[str] = []
  if i == 0:
    n = len(g["wps"])
    ok = sum(1 for p in g["wps"] if p["status"] in ("Approved", "Baselined"))
    out.append(text(x, y + 24, f"{ok} of {n}", 15, tone(ok, n), 700))
    bx = x
    for s, c in STATUSES:
      k = sum(1 for p in g["wps"] if p["status"] == s)
      if k:
        out.append(rect(bx, y + 34, max(w * k / n - 1.5, 1), 9, fill=c, stroke="none", rx=2, sw=0))
        bx += w * k / n
    counts = [f"{sum(1 for p in g['wps'] if p['status'] == s)} {s.lower()}" for s, _ in STATUSES
              if any(p["status"] == s for p in g["wps"])]
    out.append(text(x, y + 58, fk.fit(", ".join(counts), w, 10), 10, fk.MUTED))
  elif i == 1:
    oi = sum(p["open"] for p in g["wps"])
    out += [text(x, y + 28, str(oi), 17, fk.INK if oi else fk.GREEN, 700),
            text(x, y + 48, f"across {len(g['wps'])} work products", 10, fk.MUTED)]
  elif i == 2:
    ms = g["measures"]
    if not ms:
      return [text(x, y + 28, "none assigned", 12, fk.FAINT, style="italic")]
    k = sum(1 for mm in ms if mm["done"])
    out.append(text(x, y + 24, f"{k} of {len(ms)}", 15, tone(k, len(ms)), 700))
    cx, cy = x, y + 34
    for mm in ms:
      lw = fk.text_w(mm["id"], 9, True) + 12
      if cx + lw > x + w:
        cx, cy = x, cy + 17
      col = fk.GREEN if mm["done"] else fk.RED
      out += [rect(cx, cy, lw, 14, fill=fk.GREEN_BG if mm["done"] else "#FFFFFF", stroke=col, sw=1, rx=7),
              text(cx + lw / 2, cy + 10.5, mm["id"], 9, col, 700, "middle")]
      cx += lw + 4
  elif i == 3:
    n = len(g["ifrs"])
    if not n:
      return [text(x, y + 28, "none due", 12, fk.FAINT, style="italic")]
    k = sum(1 for f in g["ifrs"] if f["agreed"])
    out += [text(x, y + 24, f"{k} of {n}", 15, tone(k, n), 700),
            rect(x, y + 34, w, 9, fill=fk.HAIR, stroke="none", rx=2, sw=0)]
    if k:
      out.append(rect(x, y + 34, w * k / n, 9, fill=fk.GREEN, stroke="none", rx=2, sw=0))
    out.append(text(x, y + 58, "cumulative to this gate", 10, fk.MUTED))
  elif i == 4:
    n = len(g["roles"])
    out += [text(x, y + 24, f"{n} unassigned" if n else "all assigned", 14, fk.RED if n else fk.GREEN, 700),
            text(x, y + 42, fk.fit(", ".join(g["roles"]), w, 9.5), 9.5, fk.MUTED)]
  else:
    n = len(g["exit"])
    out += [text(x, y + 24, f"{n} criteri{'on' if n == 1 else 'a'}", 14, fk.INK, 700),
            text(x, y + 42, "not yet reviewed" if not g["passed"] else "passed at review", 10, fk.MUTED,
                 style="italic")]
  return out


def draw(d: dict) -> tuple[int, list[str]]:
  gates, nxt = d["gates"], d["next"]
  cw = (W - 80 - LW) / len(gates)
  body = [text(40, 44, "Gate readiness", 26, fk.INK, 700),
          text(40, 68, "What each gate still needs before it can be reviewed, read from the generated gate skeletons "
               "(10-safety-case/gates/skeletons), which the process model writes from WP-M-00, WP-M-02, WP-M-06 and "
               "the IFR items.", 13, fk.MUTED)]
  y = 96
  for i, g in enumerate(gates):
    x, on = LX + LW + i * cw, g is nxt
    body += [rect(x + 4, y, cw - 8, 58, fill=fk.SAFETY_BG if on else fk.CHIP, stroke=fk.SAFETY if on else fk.HAIR,
                  sw=1.6 if on else 1, rx=8),
             text(x + cw / 2, y + 20, g["gate"], 12.5, fk.INK, 700, "middle"),
             text(x + cw / 2, y + 36, fk.fit(g["name"], cw - 16, 11), 11, fk.INK, anchor="middle"),
             text(x + cw / 2, y + 51, "next gate" if on else ("passed" if g["passed"] else g["when"]), 10,
                  fk.SAFETY if on else fk.MUTED, 700 if on else "", "middle")]
  y += 72
  rh = 74
  for ri, (label, sub) in enumerate(ROWS):
    yy = y + ri * rh
    body += [rect(LX, yy, W - 80, rh - 6, fill=fk.CHIP if ri % 2 == 0 else "#FFFFFF", stroke=fk.HAIR, sw=1, rx=8),
             text(LX + 14, yy + 28, label, 13, fk.INK, 700), text(LX + 14, yy + 46, sub, 10.5, fk.MUTED, style="italic")]
    for i, g in enumerate(gates):
      body += cell(ri, g, LX + LW + i * cw + 10, yy, cw - 20)
  yb = y + len(ROWS) * rh + 16
  body += blockers(nxt, yb)
  foot, end = terms.svg_footer(body, 40, yb + 236, W - 80)
  return int(end + 10), body + foot


def blockers(g: dict, y: float) -> list[str]:
  out = [rect(LX, y, W - 80, 214, fill=fk.SAFETY_BG, stroke=fk.SAFETY, sw=1.4, rx=12),
         text(LX + 18, y + 28, f"What stands between now and {g['gate']} {g['name']}", 15, fk.SAFETY, 700)]
  todo_wps = [p["id"] for p in g["wps"] if p["status"] not in ("Approved", "Baselined")]
  cols = [("Work products to review and approve", todo_wps),
          ("Confirmation measures to perform", [mm["id"] for mm in g["measures"] if not mm["done"]]),
          ("Interfaces to agree", [f["id"] for f in g["ifrs"] if not f["agreed"]]),
          ("Roles to assign", g["roles"])]
  cw = (W - 80 - 36) / 4
  for i, (h, items) in enumerate(cols):
    x = LX + 18 + i * cw
    out.append(text(x, y + 56, f"{h} ({len(items)})", 12, fk.INK, 700))
    if not items:
      out.append(text(x, y + 78, "none", 11.5, fk.MUTED, style="italic"))
    elif i == 0:
      cx, cy = x, y + 68
      for it in items:
        if cx + 64 > x + cw - 10:
          cx, cy = x, cy + 20
        out += [rect(cx, cy, 58, 16, fill="#FFFFFF", stroke=fk.AMBER, sw=1, rx=8),
                text(cx + 29, cy + 11.5, it, 9, fk.AMBER, 700, "middle")]
        cx += 62
    else:
      for j, it in enumerate(items[:7]):
        out.append(text(x, y + 78 + j * 18, "• " + fk.fit(it, cw - 20, 11.5), 11.5, fk.INK))
      if len(items) > 7:
        out.append(text(x, y + 78 + 7 * 18, f"and {len(items) - 7} more on the page", 11, fk.MUTED, style="italic"))
  oi = sum(p["open"] for p in g["wps"])
  out.append(text(LX + 18, y + 202, f"Plus {oi} open items in those work products. A gate passes only through a "
                  "recorded review in 10-safety-case/gates/; this board is the skeletons' view, not that review.", 11,
                  fk.MUTED, style="italic"))
  return out


# ---------------------------------------------------------------- page

def page(d: dict, register) -> str:
  gates, nxt = d["gates"], d["next"]
  sk = lambda g: Path(os.path.relpath(g["skeleton"], vx.PAGES)).as_posix()  # noqa: E731
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from the gate skeletons. Do not edit. -->",
           "", "# Gate readiness", "",
           "[← Back to the V-cycle](../../README.md#the-v-cycle) · gates: "
           + " · ".join(f"[{g['gate']}]({sk(g)})" for g in gates) + " · [gate records](../../10-safety-case/gates/README.md)",
           "", "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{SVG}" width="100%" alt="{alt(d)}"></a>',
           "</p>", "",
           "*Each gate's needs, read from its generated review skeleton. The skeletons are written by the "
           "[process model](../../process/README.md) and checked in CI; a gate passes only through a recorded review "
           "in [10-safety-case/gates/](../../10-safety-case/gates/README.md). Drawn by "
           "[`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", "",
           "| Gate | Work products approved | Open items | Measures performed | Interfaces agreed | Roles unassigned | "
           "Exit criteria |", "|---|---|---|---|---|---|---|"]
  for g in gates:
    ok = sum(1 for p in g["wps"] if p["status"] in ("Approved", "Baselined"))
    lines.append(f"| [{g['gate']} {g['name']}]({sk(g)}) | {ok} of {len(g['wps'])} | {sum(p['open'] for p in g['wps'])} | "
                 f"{sum(1 for mm in g['measures'] if mm['done'])} of {len(g['measures'])} | "
                 f"{sum(1 for f in g['ifrs'] if f['agreed'])} of {len(g['ifrs'])} | {len(g['roles'])} | {len(g['exit'])} |")
  lines += ["", f"## What stands between now and {nxt['gate']} {nxt['name']}", "",
            f"From the [{nxt['gate']} skeleton]({sk(nxt)}).", "", "Work products to review and approve:", ""]
  todo = [p for p in nxt["wps"] if p["status"] not in ("Approved", "Baselined")]
  for p in todo:
    row = register.get(p["id"])
    link = Path(os.path.relpath(row.path, vx.PAGES)).as_posix() if row else sk(nxt)
    lines.append(f"- [{p['id']} {row.name if row else ''}]({link}): {p['status']}, {p['open']} open items")
  lines += ["", "Confirmation measures to perform:", ""]
  lines += [f"- {mm['id']} {mm['name']}" for mm in nxt["measures"] if not mm["done"]] or ["- None."]
  lines += ["", "Interfaces to agree:", ""]
  lines += [f"- {f['id']}: {f['title']}" for f in nxt["ifrs"] if not f["agreed"]] or ["- None."]
  lines += ["", "Roles to assign:", ""]
  lines += [f"- {r}" for r in nxt["roles"]] or ["- None."]
  lines += ["", "Exit criteria, judged at the review:", ""] + [f"- {c}" for c in nxt["exit"]]
  return "\n".join(lines) + "\n"


def alt(d: dict) -> str:
  g = d["next"]
  ok = sum(1 for p in g["wps"] if p["status"] in ("Approved", "Baselined"))
  return (f"Gate readiness for G0 to G6. Next gate {g['gate']} {g['name']}: {ok} of {len(g['wps'])} work products "
          f"approved, {sum(1 for mm in g['measures'] if mm['done'])} of {len(g['measures'])} confirmation measures "
          f"performed, {sum(1 for f in g['ifrs'] if f['agreed'])} of {len(g['ifrs'])} interfaces agreed, "
          f"{len(g['roles'])} roles unassigned.")


def render(m: dict) -> dict[Path, str]:
  d = model(m)
  _, _, _, ctx = vx.process_facts()
  h, body = draw(d)
  return {vx.OUT / SVG: fk.svg(W, h, "Gate readiness", alt(d), body), vx.PAGES / PAGE: page(d, ctx.register)}
