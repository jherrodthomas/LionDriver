#!/usr/bin/env python3
"""Evidence maturity on the V-cycle: every safety-case evidence item placed on the box of the work product it lives
in, and how far it has matured.

It reads the Living Safety Case records (assurance/case-records, through caselib.load_case): the evidence items, the
claims they support and the defeaters against those claims. An item is placed on the box of the work product its
`location` names (the register's path for that work product, or a WP ID in the path); an item whose location names
no work product is listed under the picture instead.

The maturity ladder, from the records' own fields:

- Accepted: `review_state` accepted;
- Reviewed, not accepted: `review_state` in-review, changes-requested or rejected;
- otherwise by `evidence_status`: available = Performed (performed and approved at a named baseline, WP-K-01 §6),
  partial = Drafted, missing = Not performed.

Per box: the items, their ladder, the claims they support, and the open defeaters against those claims. A defeater
against a claim that two boxes' evidence supports is counted in both, so the box counts do not add up to the total;
the panel gives the distinct total.

One picture and one page, `assurance/01-management/vcycle/evidence.md`, which lists every item with its status,
claims and location. Fails (FigureError) on an evidence status, review state or defeater state outside the schema.
Called by fig_m00_vcycle.py; it has no command line of its own.
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
sys.path.insert(0, str(A / "case-records" / "tools"))

import caselib  # noqa: E402
import figkit as fk  # noqa: E402
from figkit import FigureError, rect, text  # noqa: E402
import terms  # noqa: E402
import vcycle_explode as vx  # noqa: E402

SVG = "fig-m00-vcycle-evidence.svg"
PAGE = "evidence.md"
LADDER = [  # name, fill, stroke, meaning
  ("Not performed", fk.RED_BG, fk.RED, "recorded in WP-K-01 §6, not yet done"),
  ("Drafted", fk.AMBER_BG, fk.AMBER, "drafted analysis or specification"),
  ("Performed", fk.HW_BG, fk.HW, "performed and approved at a named baseline"),
  ("Reviewed, not accepted", fk.GREEN_BG, fk.GREEN, "a recorded review has looked at it"),
  ("Accepted", fk.GREEN_BG, fk.GREEN_DARK, "accepted by a recorded review"),
]
STATUS_LEVEL = {"missing": 0, "partial": 1, "available": 2}
REVIEW_LEVEL = {"not-reviewed": None, "in-review": 3, "changes-requested": 3, "rejected": 3, "accepted": 4}
W, BW, BH, STEP, PITCH, Y0 = 1640, 372, 96, 30, 108, 104


def level(e: dict) -> int:
  st, rv = e.get("evidence_status"), e.get("review_state") or "not-reviewed"
  if st not in STATUS_LEVEL:
    raise FigureError(f"{e['id']}: evidence_status {st!r} is not one of {', '.join(STATUS_LEVEL)}")
  if rv not in REVIEW_LEVEL:
    raise FigureError(f"{e['id']}: review_state {rv!r} is not one of {', '.join(REVIEW_LEVEL)}")
  return REVIEW_LEVEL[rv] if REVIEW_LEVEL[rv] is not None else STATUS_LEVEL[st]


def model(m: dict) -> dict:
  case = caselib.load_case()
  _, _, _, ctx = vx.process_facts()
  path2wp = {Path(os.path.relpath(r.path, caselib.REPO_ROOT)).as_posix(): w for w, r in ctx.register.items()}
  box_of = {w: b["title"] for _, _, b in vx.all_boxes(m) for w in b["ids"]}
  per: dict[str, list[dict]] = {}
  unplaced, wp_of = [], {}
  evidence = sorted(case.of_kind("evidence"), key=lambda e: e["id"])
  for e in evidence:
    level(e)
    loc = (e.get("location") or "").split("#")[0].split(" ")[0].strip()
    wp = path2wp.get(loc)
    if not wp:
      hit = re.search(r"(WP-[A-Z]-\d\d)", loc)
      wp = hit.group(1) if hit and hit.group(1) in box_of else None
    if wp:
      wp_of[e["id"]] = wp
      per.setdefault(box_of[wp], []).append(e)
    else:
      unplaced.append(e)
  defeaters = case.of_kind("defeater")
  for d in defeaters:
    if d.get("lifecycle_status") not in ("open", "closed"):
      raise FigureError(f"{d['id']}: lifecycle_status {d.get('lifecycle_status')!r} is not open or closed")
  open_d = [d for d in defeaters if d["lifecycle_status"] == "open"]
  return {"evidence": evidence, "per": per, "unplaced": unplaced, "wp_of": wp_of, "open": open_d,
          "claims": case.of_kind("claim"), "register": ctx.register}


def box_stats(d: dict, title: str) -> dict:
  es = d["per"].get(title, [])
  claims = sorted({c for e in es for c in e.get("related_claims", [])})
  dfs = sorted({x["id"] for x in d["open"] if set(x.get("related_claims", [])) & set(claims)})
  return {"es": es, "claims": claims, "defeaters": dfs, "levels": [sum(1 for e in es if level(e) == i)
                                                                    for i in range(len(LADDER))]}


# ---------------------------------------------------------------- drawing

def ladder_bar(x, y, w, levels, h=12) -> list[str]:
  n, out, bx = sum(levels), [], x
  for i, k in enumerate(levels):
    if k:
      out.append(rect(bx, y, max(w * k / n - 2, 1), h, fill=LADDER[i][2], stroke="none", rx=3, sw=0))
      bx += w * k / n
  return out


def plural(n: int, word: str) -> str:
  return f"{n} {word}{'' if n == 1 else 's'}"


def box(x, y, w, title, d) -> list[str]:
  s = box_stats(d, title)
  n = len(s["es"])
  out = [rect(x, y, w, BH, fill="#FFFFFF", stroke=fk.INK if n else fk.LINE, sw=1.4 if n else 1, rx=10,
              dash="" if n else "4 3"),
         text(x + 14, y + 22, fk.fit(title, w - 150, 13, True), 13, fk.INK if n else fk.MUTED, 700),
         text(x + w - 14, y + 22, plural(n, "evidence item") if n else "no evidence recorded", 11,
              fk.INK if n else fk.RED, 700, "end")]
  if not n:
    return out + [text(x + 14, y + 52, "Nothing in the safety case cites a work product of this box yet.", 11,
                       fk.MUTED, style="italic")]
  out += ladder_bar(x + 14, y + 34, w - 28, s["levels"])
  out.append(text(x + 14, y + 62, fk.fit(", ".join(f"{k} {LADDER[i][0].lower()}" for i, k in enumerate(s["levels"])
                                                   if k), w - 28, 11), 11, fk.MUTED))
  nd = len(s["defeaters"])
  out.append(text(x + 14, y + 80, f"supports {plural(len(s['claims']), 'claim')} · "
                  f"{plural(nd, 'open defeater')} against them", 11, fk.SAFETY if nd else fk.MUTED, 700 if nd else ""))
  return out


def chip(x, y, w, b, d) -> list[str]:
  s = box_stats(d, b["title"])
  n = len(s["es"])
  out = [rect(x, y, w, 64, fill="#FFFFFF", stroke=fk.INK if n else fk.LINE, sw=1.2, rx=10, dash="" if n else "4 3"),
         text(x + 10, y + 18, fk.fit(b["title"], w - 50, 11.5, True), 11.5, fk.INK if n else fk.MUTED, 700),
         text(x + w - 10, y + 18, str(n), 11, fk.INK if n else fk.FAINT, 700, "end")]
  if n:
    out += ladder_bar(x + 10, y + 28, w - 20, s["levels"], h=10)
    out.append(text(x + 10, y + 54, f"{plural(len(s['defeaters']), 'open defeater')}", 10.5,
                    fk.SAFETY if s["defeaters"] else fk.MUTED))
  else:
    out.append(text(x + 10, y + 42, "none", 10.5, fk.FAINT, style="italic"))
  return out


def panel(d: dict, x: float, y: float, w: float) -> list[str]:
  levels = [sum(1 for e in d["evidence"] if level(e) == i) for i in range(len(LADDER))]
  out = [text(x + 20, y + 30, "All evidence items", 12, fk.MUTED, 700),
         text(x + w - 20, y + 30, str(len(d["evidence"])), 14, fk.INK, 700, "end")]
  yy = y + 50
  for i, (name, fill, stroke, meaning) in enumerate(LADDER):
    k = levels[i]
    out += [rect(x + 20, yy, w - 40, 58, fill=fill, stroke=stroke, sw=1.4 if k else 1, rx=10, dash="" if k else "4 3"),
            text(x + 36, yy + 24, name, 14, stroke, 700),
            text(x + w - 36, yy + 26, str(k), 20, stroke if k else fk.FAINT, 700, "end"),
            text(x + 36, yy + 44, meaning, 11, fk.MUTED)]
    if i < len(LADDER) - 1:
      out.append(text(x + w / 2, yy + 74, "↓", 14, fk.FAINT, anchor="middle"))
    yy += 84
  accepted = levels[-1]
  out += [text(x + 20, yy + 4, "Only work or a recorded review moves an item up a step;", 11.5, fk.INK),
          text(x + 20, yy + 22, "a passing test or a document existing never does.", 11.5, fk.INK),
          text(x + 20, yy + 50, f"{len(d['open'])} open defeaters · {len(d['claims'])} claims · {accepted} accepted", 12,
               fk.SAFETY, 700),
          text(x + 20, yy + 70, "A defeater counts in every box whose claims it stands against.", 11, fk.MUTED,
               style="italic")]
  if d["unplaced"]:
    out.append(text(x + 20, yy + 90, fk.fit("Not on the V (location names no work product): "
                                            + ", ".join(e["id"] for e in d["unplaced"]), w - 40, 11), 11, fk.MUTED,
                    style="italic"))
  return [rect(x, y, w, yy + 106 - y, fill=fk.CHIP, stroke=fk.LINE, rx=12)] + out


def draw(m: dict, d: dict) -> tuple[int, list[str]]:
  body = [text(40, 44, "Evidence maturity on the V-cycle", 26, fk.INK, 700),
          text(40, 68, "Each safety-case evidence item (case-records) on the box of the work product it lives in, and "
               "how far it has matured: not performed, drafted, performed, reviewed, accepted.", 13, fk.MUTED)]
  nd = len(m["boxes"]["define"])
  for i in range(nd):
    y = Y0 + i * PITCH
    body += box(40 + i * STEP, y, BW, m["boxes"]["define"][i]["title"], d)
    body += box(1100 - BW - i * STEP, y, BW, m["boxes"]["verify"][i]["title"], d)
  body += box(1100 / 2 - 210 + 20, Y0 + nd * PITCH, 460, m["boxes"]["build"][0]["title"], d)
  yb = Y0 + nd * PITCH + BH + 22
  body.append(text(40, yb, "Runs across every phase", 12, fk.MUTED, 700))
  cw = (1100 - 40 - 4 * 10) / 5
  for i, b in enumerate(m["band"]):
    body += chip(40 + i * (cw + 10), yb + 10, cw, b, d)
  body += panel(d, 1140, Y0, 460)
  y = max(yb + 100, Y0 + 640)
  body.append(text(40, y, "Status and review state come from the safety-case records; nothing here is assessed or "
                   "accepted by being drawn. Status is not acceptance.", 11.5, fk.MUTED, style="italic"))
  foot, y = terms.svg_footer(body, 40, y + 24, W - 80)
  return int(y + 10), body + foot


# ---------------------------------------------------------------- page

def page(m: dict, d: dict) -> str:
  reg = d["register"]
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from assurance/case-records. "
           "Do not edit. -->", "", "# Evidence maturity", "",
           "[← Back to the V-cycle](../../README.md#the-v-cycle) · [Living Safety Case](../../README.md#living-safety-case)"
           " · [records](../../case-records/README.md)", "", "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{SVG}" width="100%" alt="{alt(d)}"></a>',
           "</p>", "",
           "*Every evidence item of the [safety case records](../../case-records/README.md) on the box of the work "
           "product it lives in. Only work or a recorded review moves an item up a step. Drawn by "
           "[`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", "",
           "## Evidence items by box", "",
           "| Box | Evidence | Step | Review | Claims | Lives in |", "|---|---|---|---|---|---|"]
  for _, _, b in vx.all_boxes(m):
    for e in d["per"].get(b["title"], []):
      wp = d["wp_of"][e["id"]]
      rel = Path(os.path.relpath(reg[wp].path, vx.PAGES)).as_posix()
      lines.append(f"| [{b['title']}]({vx.slug(b['title'])}.md) | {e['id']} {e['title'].replace('|', '/')} | "
                   f"{LADDER[level(e)][0]} | {e.get('review_state') or 'not-reviewed'} | "
                   f"{', '.join(e.get('related_claims', [])) or '—'} | [{wp}]({rel}) |")
  lines += ["", "## Evidence not placed on the V", "",
            "Its location names no work product of the register."] + [""]
  lines += [f"- {e['id']} {e['title']}: {LADDER[level(e)][0]}, `{e.get('location')}`" for e in d["unplaced"]] or ["None."]
  return "\n".join(lines) + "\n"


def alt(d: dict) -> str:
  levels = [sum(1 for e in d["evidence"] if level(e) == i) for i in range(len(LADDER))]
  return (f"Evidence maturity on the V-cycle: {len(d['evidence'])} evidence items, "
          + ", ".join(f"{k} {LADDER[i][0].lower()}" for i, k in enumerate(levels))
          + f"; {len(d['open'])} open defeaters against {len(d['claims'])} claims.")


def render(m: dict) -> dict[Path, str]:
  d = model(m)
  h, body = draw(m, d)
  return {vx.OUT / SVG: fk.svg(W, h, "Evidence maturity on the V-cycle", alt(d), body), vx.PAGES / PAGE: page(m, d)}
