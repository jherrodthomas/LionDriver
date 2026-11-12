#!/usr/bin/env python3
"""Exploded views of the V-cycle boxes: one picture and one page per box of fig_m00_vcycle.py.

Clicking a box on the V opens its page, `assurance/01-management/vcycle/<box>.md`. The page shows the box exploded:
its work products as cards, in one row per discipline lane, ordered left to right by what each needs first, with the
work it needs from other boxes, what it feeds, and the confirmation measures that cover it. Under the picture a
table links every work product to its document.

Where each value comes from:

- the box contents, statuses and gates: the model built by fig_m00_vcycle.build_model() from WP-M-00;
- the lane and the "needs first" inputs of each work product: the activity that produces it in the process model
  (assurance/process/model/*.yaml, WP-P-11), with indirect dependencies dropped so only direct steps are drawn;
- the measures and whether each has a record: the `review` items of the process model whose `covers` names a work
  product of the box, checked with process_model.record_present();
- the clause references on each card: the WP-M-00 row, through process_model.load_context().

Fails (FigureError) when a work product has no producing activity, an activity names an unknown lane, or the
inputs inside a box form a cycle. Called by fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(A / "process" / "tools"))
sys.path.insert(0, str(A / "trace" / "tools"))

import figkit as fk  # noqa: E402
from figkit import FigureError, fmt, rect, text, line, path  # noqa: E402
import process_model as pm  # noqa: E402
import terms  # noqa: E402

PAGES = A / "01-management" / "vcycle"
OUT = HERE / "vcycle"
W_MIN, NW, NH, CP, LANE_GAP = 1400, 150, 82, 172, 12
LEFT = 250  # column for the work needed from other boxes
STATUS_FILL = {"S": (fk.GREY_BG, fk.MUTED), "D": (fk.AMBER_BG, fk.AMBER), "R": (fk.HW_BG, fk.HW),
               "A": (fk.GREEN_BG, fk.GREEN), "B": (fk.GREEN_BG, fk.GREEN_DARK), "N/A": (fk.GREY_BG, fk.FAINT)}
STD = [("iso26262", "26262-"), ("iso21448", "21448 "), ("iso21434", "21434 "), ("other", "")]


def slug(title: str) -> str:
  return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def all_boxes(m: dict) -> list[tuple[str, int, dict]]:
  """(side, index, box) for every box of the V and every band group, in reading order."""
  out = [(side, i, b) for side in ("define", "verify", "build") for i, b in enumerate(m["boxes"][side])]
  return out + [("band", i, b) for i, b in enumerate(m["band"])]


# ---------------------------------------------------------------- the process model, per work product

def process_facts() -> tuple[dict[str, dict], dict[str, str], dict[str, dict], pm.Context]:
  model, ctx = pm.load_model(), pm.load_context()
  producer: dict[str, dict] = {}
  for aid in sorted(model.activities):
    act = model.activities[aid]
    if act["lane"] not in model.lanes:
      raise FigureError(f"process model {aid}: unknown lane {act['lane']!r}")
    for wp in act["produces"]:
      producer.setdefault(wp, act)
  lanes = {k: re.sub(r"\s*\(.*\)$", "", v["name"]) for k, v in model.lanes.items()}
  return producer, lanes, model.reviews, ctx


def short_clauses(row: pm.RegisterRow) -> str:
  parts = []
  for key, pre in STD:
    cell = re.sub(r"\s*\([^)]*\)", "", row.clauses.get(key, "")).strip(" ,;")
    if cell and cell not in ("—", "-"):
      parts.append(pre + cell.split(";")[0].split(",")[0].strip())
  return " · ".join(parts)


def dedupe(reviews: list[tuple[str, str, bool]]) -> list[tuple[str, str, bool]]:
  """One line per WP-M-06 measure: a measure planned at several gates counts as recorded if any record exists."""
  out: dict[str, tuple[str, str, bool]] = {}
  for rid, name, ok in reviews:
    out[rid] = (rid, out[rid][1], out[rid][2] or ok) if rid in out else (rid, name, ok)
  return list(out.values())


def explode(m: dict, box: dict, where: dict, facts) -> dict:
  producer, lanes, reviews, ctx = facts
  ids = box["ids"]
  for w in ids:
    if w not in producer:
      raise FigureError(f"{w} ({box['title']}): no activity in the process model produces it")
  inside = set(ids)
  needs = {w: [i for i in producer[w]["inputs"] if i in inside and i != w] for w in ids}

  def anc(n, seen):
    for p in needs[n]:
      if p not in seen:
        seen.add(p)
        anc(p, seen)
    return seen

  direct = {w: [s for s in ss if not any(s in anc(o, set()) for o in ss if o != s)] for w, ss in needs.items()}
  depth: dict[str, int] = {}

  def d(w, stack=()):
    if w in stack:
      raise FigureError(f"{box['title']}: inputs form a cycle through {w}")
    if w not in depth:
      depth[w] = 1 + max((d(p, stack + (w,)) for p in needs[w]), default=-1)
    return depth[w]

  for w in ids:
    d(w)
  outside_in: dict[str, list[str]] = {}
  for w in ids:
    for i in producer[w]["inputs"]:
      if i not in inside and i in where:
        outside_in.setdefault(where[i], [])
        if i not in outside_in[where[i]]:
          outside_in[where[i]].append(i)
  feeds: dict[str, list[str]] = {}
  for w, act in sorted(producer.items()):
    if w not in inside and w in where and inside & set(act["inputs"]):
      feeds.setdefault(where[w], []).append(w)
  covered = [r for rid, r in sorted(reviews.items()) if inside & set(r.get("covers", []))]
  lane_of = {w: producer[w]["lane"] for w in ids}
  order = [k for k in lanes if k in set(lane_of.values())]
  return {"box": box, "ids": ids, "direct": direct, "depth": depth, "lane_of": lane_of, "lanes": order,
          "lane_names": lanes, "in": outside_in, "feeds": feeds,
          "reviews": dedupe([(pm.measure_id(r["id"]), r["name"], pm.record_present(r, ctx.register)) for r in covered]),
          "row": {w: ctx.register[w] for w in ids}}


# ---------------------------------------------------------------- drawing

def mini_v(x: float, y: float, side: str, idx: int, m: dict) -> list[str]:
  out = []
  n = len(m["boxes"]["define"])
  for i in range(n):
    on = side == "define" and i == idx
    out.append(rect(x + i * 8, y + i * 12, 44, 9, fill=fk.DEFINE if on else fk.DEFINE_BG, stroke=fk.DEFINE, sw=.8, rx=2))
    on = side == "verify" and i == idx
    out.append(rect(x + 150 - i * 8, y + i * 12, 44, 9, fill=fk.VERIFY if on else fk.VERIFY_BG, stroke=fk.VERIFY,
                    sw=.8, rx=2))
  out.append(rect(x + 70, y + n * 12, 60, 9, fill=fk.INK if side == "build" else fk.GREY_BG, stroke=fk.INK, sw=.8, rx=2))
  for i in range(len(m["band"])):
    out.append(rect(x + i * 39, y + n * 12 + 16, 35, 7, fill=fk.MUTED if side == "band" and i == idx else "#FFFFFF",
                    stroke=fk.LINE, sw=.8, rx=2))
  hx, hy, hw = {"define": (x + idx * 8, y + idx * 12, 44), "verify": (x + 150 - idx * 8, y + idx * 12, 44),
                "build": (x + 70, y + n * 12, 60), "band": (x + idx * 39, y + n * 12 + 16, 35)}[side]
  out.append(rect(hx - 4, hy - 4, hw + 8, 17 if side != "band" else 15, fill="none", stroke=fk.SAFETY, sw=2, rx=4))
  out.append(text(x + 97, y + n * 12 + 42, "Click the picture to go back to the V", 10.5, fk.MUTED, anchor="middle"))
  return out


def card(x, y, w, e) -> list[str]:
  row = e["row"][w]
  fill, col = STATUS_FILL[row.status]
  out = [rect(x, y, NW, NH, fill="#FFFFFF", stroke=fk.DEFINE, sw=1.5, rx=8),
         text(x + 10, y + 18, w, 11.5, fk.DEFINE, 700)]
  name = pm.STATUS_NAMES[row.status]
  p, pw = fk.pill(0, 0, name, fill, col, h=16, size=9.5, stroke=col)
  out.append(f'<g transform="translate({fmt(x + NW - 8 - pw)},{fmt(y + 6)})">' + "".join(p) + "</g>")
  words, l1, l2 = row.name.split(), "", ""
  for wd in words:
    if not l2 and fk.text_w((l1 + " " + wd).strip(), 12, True) <= NW - 20:
      l1 = (l1 + " " + wd).strip()
    else:
      l2 = (l2 + " " + wd).strip()
  out.append(text(x + 10, y + 37, l1, 12, fk.INK, 600))
  if l2:
    out.append(text(x + 10, y + 52, fk.fit(l2, NW - 20, 12, True), 12, fk.INK, 600))
  out.append(text(x + 10, y + 72, fk.fit(short_clauses(row) or f"gate {row.gate}", NW - 20, 9.5), 9.5, fk.MUTED))
  return out


GUTTER = CP - NW  # free vertical strip between two card columns


def edges(e: dict, pos: dict[str, tuple[float, float]], lane_top: dict[str, tuple[float, float]]) -> list[str]:
  """Arrows routed around the cards, never behind them.

  Every vertical run sits in a gutter between card columns, where no card is. A horizontal run that has to cross
  card columns uses a channel no card in those columns touches: the band under a lane's label, the gap between two
  lanes, or the gap between two stacked cards. An arrow leaves its source on the right; it enters its target on
  the left, or on the right when both are in the same column. Sources take the left half of a gutter and targets
  the right half, each at its own offset, so parallel runs stay apart.
  """
  col = {w: e["depth"][w] for w in pos}
  by_col: dict[int, list[str]] = {}
  for w in sorted(pos, key=lambda w: (pos[w][1], w)):
    by_col.setdefault(col[w], []).append(w)
  channels = sorted({y + 15 for y, _ in lane_top.values()} | {y + h + 6 for y, h in lane_top.values()} |
                    {pos[w][1] + NH + 6 for w in pos})

  def free(y: float, c0: int, c1: int) -> bool:
    return all(not (pos[w][1] - 3 <= y <= pos[w][1] + NH + 3) for c in range(c0, c1 + 1) for w in by_col.get(c, []))

  def exit_x(s):
    return pos[s][0] + NW + 3 + (by_col[col[s]].index(s) % 3) * 3

  def entry_x(t):
    return pos[t][0] - 4 - (by_col[col[t]].index(t) % 3) * 3

  out = []
  for t, srcs in e["direct"].items():
    for s in srcs:
      (sx, sy), (tx, ty) = pos[s], pos[t]
      y1, y2, gx = sy + NH / 2, ty + NH / 2, exit_x(s)
      if col[t] == col[s]:  # same column: down the right-hand gutter, in from the right
        pts, head = [(sx + NW, y1), (gx + 6, y1), (gx + 6, y2), (tx + NW + 7, y2)], (tx + NW, y2, 1)
      elif col[t] == col[s] + 1:  # next column: one shared gutter
        pts, head = [(sx + NW, y1), (gx, y1), (gx, y2), (tx - 7, y2)], (tx, y2, -1)
      else:
        cy = min((y for y in channels if free(y, col[s] + 1, col[t] - 1)),
                 key=lambda y: (abs(y - y1) + abs(y - y2), y), default=None)
        if cy is None:
          raise FigureError(f"{e['box']['title']}: no free channel for the arrow {s} → {t}")
        ex = entry_x(t)
        pts = [(sx + NW, y1), (gx, y1), (gx, cy), (ex, cy), (ex, y2), (tx - 7, y2)]
        head = (tx, y2, -1)
      for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        for w, (rx, ry) in pos.items():
          if rx < max(ax, bx) and min(ax, bx) < rx + NW and ry < max(ay, by) and min(ay, by) < ry + NH:
            raise FigureError(f"{e['box']['title']}: the arrow {s} → {t} would pass behind {w}")
      d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
      out.append(path(d, stroke=fk.FAINT, sw=1.3))
      hx, hy, sign = head  # arrowhead pointing into the card edge
      out.append(path(f"M{fmt(hx)} {fmt(hy)} l{fmt(7 * sign)} -4 v8 z", stroke="none", fill=fk.FAINT))
  return out


def draw(e: dict, side: str, idx: int, m: dict) -> tuple[int, int, list[str]]:
  box = e["box"]
  cols = max(e["depth"].values()) + 1
  width = max(W_MIN, LEFT + cols * CP + 60)
  body = [text(40, 40, f"V-cycle  ›  {box['title']}", 13, fk.DEFINE, 700),
          text(40, 74, f"{box['title']} · exploded view", 26, fk.INK, 700),
          text(40, 100, f"The {len(e['ids'])} work product{'s' if len(e['ids']) != 1 else ''} of this box: what each "
               "needs first (from the process model, WP-P-11), its status, and the reviews that cover the box.",
               13.5, fk.MUTED)]
  body += mini_v(width - 240, 30, side, idx, m)
  y = 170
  # lanes: height grows with the most cards sharing one column in that lane
  pos: dict[str, tuple[float, float]] = {}
  lane_top = {}
  for ln in e["lanes"]:
    per_col: dict[int, int] = {}
    for w in e["ids"]:
      if e["lane_of"][w] == ln:
        c = e["depth"][w]
        pos[w] = (LEFT + c * CP, y + 30 + per_col.get(c, 0) * (NH + 12))
        per_col[c] = per_col.get(c, 0) + 1
    h = 30 + max(per_col.values()) * (NH + 12) + 6
    if ln == e["lanes"][0]:  # the first lane also holds the list of what the box needs from other boxes
      h = max(h, 48 + 42 * len(e["in"]))
    lane_top[ln] = (y, h)
    y += h + LANE_GAP
  lanes_end = y - LANE_GAP
  for i, ln in enumerate(e["lanes"]):
    ly, lh = lane_top[ln]
    body.append(rect(40, ly, width - 80, lh, fill=fk.CHIP if i % 2 == 0 else "#FFFFFF", stroke=fk.HAIR, sw=1, rx=8))
    body.append(text(52, ly + 20, e["lane_names"][ln], 12, fk.MUTED, 700))
  # needs from other boxes, in the left column
  ny = 170 + 40
  if e["in"]:
    body.append(text(LEFT - 18, 170 + 20, "Needs from other boxes", 11, fk.FAINT, anchor="end", style="italic"))
    ny -= 8
    for title, wps in e["in"].items():
      label = f"{title}: {pm_compress(wps)}"
      body.append(rect(52, ny, LEFT - 70, 34, fill="#FFFFFF", stroke=fk.LINE, sw=1, rx=8, dash="4 3"))
      body.append(text(62, ny + 14, fk.fit(title, LEFT - 90, 10.5, True), 10.5, fk.INK, 700))
      body.append(text(62, ny + 28, fk.fit(pm_compress(wps), LEFT - 90, 10), 10, fk.MUTED))
      ny += 42
  # edges, then cards
  body += edges(e, pos, lane_top)
  for w in e["ids"]:
    body += card(*pos[w], w, e)
  # feeds and reviews
  fy = lanes_end + 20
  half = (width - 100) / 2
  rows_f = max(1, len(e["feeds"]))
  rows_r = max(1, (len(e["reviews"]) + 1) // 2)
  bh = 46 + max(rows_f * 22, rows_r * 24)
  body.append(rect(40, fy, half, bh, fill="#FFFFFF", stroke=fk.LINE, rx=10))
  body.append(text(56, fy + 22, "Feeds into", 12, fk.MUTED, 700))
  if not e["feeds"]:
    body.append(text(56, fy + 46, "No work product in another box lists these as an input.", 11.5, fk.FAINT,
                     style="italic"))
  for j, (title, wps) in enumerate(e["feeds"].items()):
    body.append(text(56, fy + 46 + j * 22, f"→ {title}", 12, fk.DEFINE, 700))
    body.append(text(56 + fk.text_w(f"→ {title}", 12, True) + 12, fy + 46 + j * 22,
                     fk.fit(pm_compress(wps), half - fk.text_w(title, 12, True) - 70, 11), 11, fk.MUTED))
  rx0 = 60 + half
  body.append(rect(rx0, fy, half, bh, fill=fk.SAFETY_BG, stroke=fk.SAFETY, rx=10))
  done = sum(1 for _, _, ok in e["reviews"] if ok)
  body.append(text(rx0 + 16, fy + 22, f"Reviews that cover this box (WP-M-06) · {done} of {len(e['reviews'])} "
                   "recorded", 12, fk.SAFETY, 700))
  if not e["reviews"]:
    body.append(text(rx0 + 16, fy + 46, "No confirmation measure names these work products.", 11.5, fk.FAINT,
                     style="italic"))
  for j, (rid, name, ok) in enumerate(e["reviews"]):
    x, yy = rx0 + 16 + (j % 2) * (half / 2), fy + 46 + (j // 2) * 24
    body.append(f'<circle cx="{fmt(x + 5)}" cy="{fmt(yy - 4)}" r="5" fill="{fk.SAFETY if ok else "#FFFFFF"}" '
                f'stroke="{fk.SAFETY}" stroke-width="1.5"/>')
    body.append(text(x + 16, yy, rid, 11.5, fk.INK, 700))
    body.append(text(x + 70, yy, fk.fit(name, half / 2 - 90, 11), 11, fk.MUTED))
  y = fy + bh + 26
  body.append(text(40, y, "Arrows: needs this first (direct steps only), from the process model. Filled circle: "
                   "a review record exists. Status is not acceptance.", 11.5, fk.MUTED))
  foot, y = terms.svg_footer(body, 40, y + 22, width - 80)
  return width, int(y + 10), body + foot


def pm_compress(wps: list[str]) -> str:
  import fig_m00_vcycle as v
  return v.compress(wps)


# ---------------------------------------------------------------- pages

def page(e: dict, svg_name: str, m: dict, title_of: dict[str, str]) -> str:
  box = e["box"]
  up = "../README.md#the-v-cycle"
  folder = f"../../{box['folder']}/README.md"
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from WP-M-00 and the process model. "
           "Do not edit. -->", "", f"# V-cycle: {box['title']}", "",
           f"[← Back to the V-cycle](../../README.md#the-v-cycle) · folder: [`{box['folder']}/`]({folder})", "",
           "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{svg_name}" width="100%" '
           f'alt="{alt(e)}"></a>', "</p>", "",
           "*Click the picture to go back to the V. Drawn from the [register](../WP-M-00-work-product-register.md) "
           "and the [process model](../../process/README.md) by "
           "[`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", "",
           "## Work products", "", "| Work product | Status | Gate | Discipline | Needs first |", "|---|---|---|---|---|"]
  for w in sorted(e["ids"], key=lambda w: (e["depth"][w], w)):
    row = e["row"][w]
    rel = Path(os.path.relpath(row.path, PAGES)).as_posix()
    needs = ", ".join(e["direct"][w]) or "—"
    lines.append(f"| [{w} {row.name}]({rel}) | {pm.STATUS_NAMES[row.status]} | {row.gate} | "
                 f"{e['lane_names'][e['lane_of'][w]]} | {needs} |")
  lines += ["", "## Needs from other boxes", ""]
  lines += [f"- [{t}]({slug(t)}.md): {', '.join(w)}" for t, w in e["in"].items()] or ["None."]
  lines += ["", "## Feeds into", ""]
  lines += [f"- [{t}]({slug(t)}.md): {', '.join(w)}" for t, w in e["feeds"].items()] or ["None."]
  lines += ["", "## Reviews that cover this box", ""]
  lines += [f"- {'Recorded' if ok else 'No record yet'}: {rid}, {name}" for rid, name, ok in e["reviews"]] or ["None."]
  return "\n".join(lines) + "\n"


def alt(e: dict) -> str:
  st = {}
  for w in e["ids"]:
    st[pm.STATUS_NAMES[e["row"][w].status].lower()] = st.get(pm.STATUS_NAMES[e["row"][w].status].lower(), 0) + 1
  done = sum(1 for _, _, ok in e["reviews"] if ok)
  def n(k, word):
    return f"{k} {word}{'' if k == 1 else 's'}"
  return (f"{e['box']['title']} exploded: {n(len(e['ids']), 'work product')} in {n(len(e['lanes']), 'discipline lane')}, "
          f"{', '.join(f'{k} {s}' for s, k in st.items())}; feeds {len(e['feeds'])} other box{'' if len(e['feeds']) == 1 else 'es'}; "
          f"{done} of {len(e['reviews'])} covering reviews recorded.")


def render(m: dict) -> dict[Path, str]:
  facts = process_facts()
  where = {w: b["title"] for _, _, b in all_boxes(m) for w in b["ids"]}
  files = {}
  for side, idx, b in all_boxes(m):
    e = explode(m, b, where, facts)
    w, h, body = draw(e, side, idx, m)
    name = f"fig-m00-vcycle-x-{slug(b['title'])}.svg"
    files[OUT / name] = fk.svg(w, h, f"{b['title']}: exploded view", alt(e), body)
    files[PAGES / f"{slug(b['title'])}.md"] = page(e, name, m, where)
  idx = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py. Do not edit. -->", "",
         "# V-cycle exploded views", "",
         "One page per box of the [V-cycle](../../README.md#the-v-cycle): its work products, what each needs first, "
         "and the reviews that cover the box. The same boxes over time: [V-cycle over time](over-time.md). By standard: "
         + ", ".join(f"[{lb}](standard-{k}.md)" for k, lb, _, _ in __import__("vcycle_standards").STANDARDS) + ".", "",
         "| Box | Work products |", "|---|---|"]
  idx += [f"| [{b['title']}]({slug(b['title'])}.md) | {len(b['ids'])} |" for _, _, b in all_boxes(m)]
  files[PAGES / "README.md"] = "\n".join(idx) + "\n"
  return files
