#!/usr/bin/env python3
"""Change impact on the V-cycle: pick a change, see every work product that depends on it and whether it has moved.

A "change" is a work product's latest dated entry in its `Version` row. For a change to work product X, the work
products downstream of X are those whose producing activity in the process model (WP-P-11) lists X as an input,
and so on transitively. Each downstream work product is then:

- updated since: it has a dated version entry on or after the change's date;
- worth a look: its latest dated entry is before the change;
- undated: it has no dated version entry yet.

That is a prompt to look, not proof of an impact: the impact analysis (WP-M-12) and its records decide what a change
actually affects.

Outputs, in assurance/01-management/vcycle/:

- `impact.md`: the picker and a table of every dated work product's latest change, its version, and how many work
  products downstream are updated since, worth a look, or undated;
- `impact-<wp>.md` with figure `fig-m00-vcycle-impact-<wp>.svg` for each of the RECENT most recent changes (one per
  work product, latest date first, ties by ID): the V with every work product as a chip coloured as above, the
  number of steps from the change on each, and a side panel quoting the change.

The pages depend only on the dates in the records, never on the build date, so the output is deterministic. Called by
fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "trace" / "tools"))

import figkit as fk  # noqa: E402
from figkit import FigureError, fmt, rect, text  # noqa: E402
import terms  # noqa: E402
import vcycle_explode as vx  # noqa: E402
import vcycle_time as vt  # noqa: E402

RECENT = 8
INDEX = "impact.md"
STEPS = ["", "Directly", "Two steps away", "Three steps away", "Four steps away", "Five steps away", "Six steps away"]
STATE = {  # stroke, fill, text colour, legend
  "src": (fk.INK, fk.INK, "#FFFFFF", "the change"),
  "look": (fk.SAFETY, fk.SAFETY_BG, fk.SAFETY, "no version dated after the change: worth a look"),
  "ok": (fk.GREEN, fk.GREEN_BG, fk.GREEN, "updated since"),
  "undated": (fk.FAINT, "#FFFFFF", fk.MUTED, "no dated version yet"),
  "none": (fk.HAIR, "#FFFFFF", fk.FAINT, "not downstream"),
}
W, BW, BH, STEP, PITCH, Y0 = 1640, 372, 96, 30, 108, 150


def slug(wp: str) -> str:
  return wp.lower()


def page_name(wp: str) -> str:
  return f"impact-{slug(wp)}.md"


def svg_name(wp: str) -> str:
  return f"fig-m00-vcycle-impact-{slug(wp)}.svg"


# ---------------------------------------------------------------- data

def downstream(producer: dict[str, dict]) -> dict[str, set[str]]:
  out: dict[str, set[str]] = {}
  for wp, act in producer.items():
    for i in act["inputs"]:
      if i != wp:
        out.setdefault(i, set()).add(wp)
  return out


def steps_from(src: str, down: dict[str, set[str]]) -> dict[str, int]:
  """Shortest number of steps from src to each work product downstream of it (breadth first)."""
  hop, frontier = {src: 0}, [src]
  while frontier:
    nxt = []
    for x in frontier:
      for y in sorted(down.get(x, ())):
        if y not in hop:
          hop[y] = hop[x] + 1
          nxt.append(y)
    frontier = nxt
  return hop


def state(wp: str, src: str, when: str, hop: dict[str, int], last: dict[str, str]) -> str:
  if wp == src:
    return "src"
  if wp not in hop:
    return "none"
  if wp not in last:
    return "undated"
  return "ok" if last[wp] >= when else "look"


def latest_entry(row) -> tuple[str, str]:
  """(version, text) of the newest entry in a work product's Version row; text may be empty."""
  m = re.search(r"^\| Version \| (.*)$", row.path.read_text(encoding="utf-8"), re.M)
  if not m:
    raise FigureError(f"{row.wp}: no Version row")
  cell = m.group(1).rstrip(" |")
  v = re.match(r"(\d+\.\d+)\s*(?:\((.*?)\)(?:\.\s+\d+\.\d+|\s*$))?", cell)
  if not v:
    return "", ""
  body = re.sub(r";?\s*20\d\d-\d\d-\d\d\s*$", "", v.group(2) or "").strip()
  return v.group(1), re.sub(r"[`*]", "", body)


def model(m: dict) -> dict:
  producer, _, _, ctx = vx.process_facts()
  tm = vt.model(m)
  last, down = tm["last"], downstream(producer)
  changes = []
  for wp in sorted(last, key=lambda w: (last[w], w), reverse=True):
    hop = steps_from(wp, down)
    counts = {"look": 0, "ok": 0, "undated": 0}
    for w in hop:
      if w != wp:
        counts[state(w, wp, last[wp], hop, last)] += 1
    ver, body = latest_entry(ctx.register[wp])
    changes.append({"wp": wp, "when": last[wp], "hop": hop, "counts": counts, "version": ver, "text": body,
                    "name": ctx.register[wp].name})
  if not changes:
    raise FigureError("no work product has a dated version entry")
  return {"changes": changes, "recent": changes[:RECENT], "last": last, "register": ctx.register}


# ---------------------------------------------------------------- drawing

def short_date(d: str) -> str:
  return f"{dt.date.fromisoformat(d):%d %b}"


def picker(recent: list[dict], current: str) -> list[str]:
  out, x = [text(40, 104, "Recent changes:", 12, fk.MUTED, 700)], 150
  for c in recent:
    on = c["wp"] == current
    p, w = fk.pill(0, 0, f"{c['wp']} · {short_date(c['when'])}", fk.INK if on else "#FFFFFF",
                   "#FFFFFF" if on else fk.MUTED, h=22, size=10.5, stroke=fk.INK if on else fk.LINE)
    out.append(f'<g transform="translate({fmt(x)},91)">' + "".join(p) + "</g>")
    x += w + 8
  return out


def chip(x, y, wp, s, hop, w=58, h=18, size=9.5, label=None) -> list[str]:
  stroke, fill, tc, _ = STATE[s]
  out = [rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.3, rx=h / 2, dash="3 2" if s == "undated" else ""),
         text(x + w / 2, y + h * 0.72, label or wp, size, tc, 700, "middle")]
  if s in ("look", "ok", "undated"):
    out.append(text(x + w + 3, y + 5, str(hop[wp]), 8, fk.MUTED, 700, "middle"))
  return out


def box(x, y, w, b, c, last) -> list[str]:
  src, when, hop = c["wp"], c["when"], c["hop"]
  sts = {wp: state(wp, src, when, hop, last) for wp in b["ids"]}
  here = src in b["ids"]
  hit = [wp for wp, s in sts.items() if s in ("look", "ok", "undated")]
  col = fk.INK if here or hit else fk.HAIR
  out = [rect(x, y, w, BH, fill="#FFFFFF", stroke=col, sw=2.6 if here else (1.4 if hit else 1), rx=10,
              dash="" if here or hit else "4 3"),
         text(x + 14, y + 22, fk.fit(b["title"], w - 150, 13, True), 13, fk.INK if here or hit else fk.FAINT, 700),
         text(x + w - 14, y + 22, "changed here" if here else (f"{len(hit)} of {len(b['ids'])} downstream" if hit
                                                               else "not downstream"), 11,
              fk.INK if here or hit else fk.FAINT, 700, "end")]
  cx, cy = x + 14, y + 34
  for wp in b["ids"]:
    if cx + 64 > x + w - 6:
      cx, cy = x + 14, cy + 22
    out += chip(cx, cy, wp, sts[wp], hop)
    cx += 64
  return out


def band_chip(x, y, w, b, c, last) -> list[str]:
  src, when, hop = c["wp"], c["when"], c["hop"]
  sts = {wp: state(wp, src, when, hop, last) for wp in b["ids"]}
  hit = sum(1 for s in sts.values() if s in ("look", "ok", "undated"))
  here = src in b["ids"]
  on = hit or here
  out = [rect(x, y, w, 106, fill="#FFFFFF", stroke=fk.INK if here else (fk.MUTED if on else fk.HAIR),
              sw=2.6 if here else 1.2, rx=10, dash="" if on else "4 3"),
         text(x + 10, y + 18, fk.fit(b["title"], w - 50, 11.5, True), 11.5, fk.INK if on else fk.FAINT, 700),
         text(x + w - 10, y + 18, f"{hit}/{len(b['ids'])}", 10.5, fk.INK if on else fk.FAINT, 700, "end")]
  cx, cy = x + 8, y + 28
  for wp in b["ids"]:
    if cx + 46 > x + w:
      cx, cy = x + 8, cy + 14
    stroke, fill, tc, _ = STATE[sts[wp]]
    out += [rect(cx, cy, 43, 11, fill=fill, stroke=stroke, sw=1.1, rx=5, dash="3 2" if sts[wp] == "undated" else ""),
            text(cx + 21.5, cy + 8.5, wp, 6.6, tc, 700, "middle")]
    cx += 46
  return out


def panel(c: dict, x: float, y: float, w: float) -> list[str]:
  """The side panel. The change's own words are quoted on the page, not here: free text from the records would make
  the figure's terms line depend on every word anyone writes in a version note."""
  out = [text(x + 20, y + 30, "The change", 12, fk.MUTED, 700),
         text(x + 20, y + 56, fk.fit(f"{c['wp']} {c['name']}", w - 40, 15, True), 15, fk.INK, 700),
         text(x + 20, y + 78, (f"version {c['version']} · " if c["version"] else "") + f"dated {c['when']}", 12,
              fk.MUTED),
         text(x + 20, y + 98, "What changed is quoted on this page, below the picture.", 11, fk.MUTED, style="italic")]
  y2 = y + 136
  out.append(text(x + 20, y2, "Downstream in the process model", 12, fk.MUTED, 700))
  per: dict[int, dict[str, int]] = {}
  for wp, h in c["hop"].items():
    if wp != c["wp"]:
      per.setdefault(h, {"look": 0, "ok": 0, "undated": 0})[c["_state"][wp]] += 1
  yy = y2 + 30
  if not per:
    out.append(text(x + 20, yy, "Nothing in the process model takes this work product", 11.5, fk.MUTED, style="italic"))
    out.append(text(x + 20, yy + 16, "as an input, so nothing is downstream of it.", 11.5, fk.MUTED, style="italic"))
    yy += 40
  for h in sorted(per):
    cnt = per[h]
    total = sum(cnt.values())
    out += [text(x + 20, yy, STEPS[h] if h < len(STEPS) else f"{h} steps away", 12.5, fk.INK, 700),
            text(x + w - 20, yy, str(total), 12.5, fk.INK, 700, "end")]
    bx = x + 20
    for k in ("look", "ok", "undated"):
      if cnt[k]:
        ww = (w - 40) * cnt[k] / total
        out.append(rect(bx, yy + 8, max(ww - 2, 1), 12, fill=STATE[k][0] if k != "undated" else fk.LINE,
                        stroke="none", rx=3, sw=0))
        bx += ww
    yy += 44
  yy += 6
  for k in ("look", "ok", "undated"):
    stroke, fill, _, legend = STATE[k]
    out += [rect(x + 20, yy - 11, 30, 14, fill=fill, stroke=stroke, sw=1.3, rx=7, dash="3 2" if k == "undated" else ""),
            text(x + 58, yy, f"{c['counts'][k]} {legend}", 12, fk.INK)]
    yy += 26
  out += [text(x + 20, yy + 12, "Small number on a chip: steps from the change.", 11, fk.MUTED, style="italic"),
          text(x + 20, yy + 30, "Dashed box: nothing in it depends on the change.", 11, fk.MUTED, style="italic")]
  return [rect(x, y, w, yy + 50 - y, fill=fk.CHIP, stroke=fk.LINE, rx=12)] + out


def draw(m: dict, d: dict, c: dict) -> tuple[int, list[str]]:
  last = d["last"]
  c["_state"] = {wp: state(wp, c["wp"], c["when"], c["hop"], last) for wp in c["hop"]}
  body = [text(40, 44, "Change impact on the V-cycle", 26, fk.INK, 700),
          text(40, 68, "Every work product that depends on the change in the process model (WP-P-11), coloured by "
               "whether it has a version dated after the change.", 13, fk.MUTED)]
  body += picker(d["recent"], c["wp"])
  nd = len(m["boxes"]["define"])
  for i in range(nd):
    y = Y0 + i * PITCH
    body += box(40 + i * STEP, y, BW, m["boxes"]["define"][i], c, last)
    body += box(1100 - BW - i * STEP, y, BW, m["boxes"]["verify"][i], c, last)
  body += box(1100 / 2 - 210 + 20, Y0 + nd * PITCH, 460, m["boxes"]["build"][0], c, last)
  yb = Y0 + nd * PITCH + BH + 22
  body.append(text(40, yb, "Runs across every phase", 12, fk.MUTED, 700))
  cw = (1100 - 40 - 4 * 10) / 5
  for i, b in enumerate(m["band"]):
    body += band_chip(40 + i * (cw + 10), yb + 10, cw, b, c, last)
  body += panel(c, 1140, Y0, 460)
  y = yb + 140
  body.append(text(40, y, "Depending on a change is a prompt to look, not proof of an impact: the impact analysis "
                   "(WP-M-12) and its records decide what a change actually affects. Status is not acceptance.", 11.5,
                   fk.MUTED, style="italic"))
  foot, y = terms.svg_footer(body, 40, y + 24, W - 80)
  del c["_state"]
  return int(y + 10), body + foot


# ---------------------------------------------------------------- pages

def picker_md(d: dict, current: str) -> str:
  items = [f"**{c['wp']} · {short_date(c['when'])}**" if c["wp"] == current else
           f"[{c['wp']} · {short_date(c['when'])}]({page_name(c['wp'])})" for c in d["recent"]]
  idx = "**All changes**" if current == "index" else f"[All changes]({INDEX})"
  return "Recent changes: " + " · ".join(items) + " · " + idx


def page(m: dict, d: dict, c: dict) -> str:
  reg = d["register"]
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from WP-M-00, the work products' "
           "Version rows and the process model. Do not edit. -->", "",
           f"# Change impact: {c['wp']} {c['name']}", "",
           "[← Back to the V-cycle](../../README.md#the-v-cycle) · " + picker_md(d, c["wp"]), "",
           "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{svg_name(c["wp"])}" width="100%" '
           f'alt="{alt(c)}"></a>', "</p>", "",
           f"*The change: {c['wp']}" + (f" version {c['version']}" if c["version"] else "") + f", dated {c['when']}"
           + (f": {c['text']}" if c["text"] else "") + "*", "",
           "Depending on a change is a prompt to look, not proof of an impact: the "
           "[impact analysis (WP-M-12)](../WP-M-12-impact-analysis.md) and its records decide what a change actually "
           "affects.", "",
           "## Downstream work products", "",
           "| Work product | Steps | Its last dated version | Since the change |", "|---|---|---|---|"]
  st = {wp: state(wp, c["wp"], c["when"], c["hop"], d["last"]) for wp in c["hop"]}
  for wp in sorted((w for w in c["hop"] if w != c["wp"]), key=lambda w: (c["hop"][w], w)):
    rel = Path(os.path.relpath(reg[wp].path, vx.PAGES)).as_posix()
    lines.append(f"| [{wp} {reg[wp].name}]({rel}) | {c['hop'][wp]} | {d['last'].get(wp, '—')} | "
                 f"{ {'look': 'worth a look', 'ok': 'updated', 'undated': 'undated'}[st[wp]] } |")
  if len(c["hop"]) == 1:
    lines.append("| — | | | Nothing in the process model takes this work product as an input. |")
  return "\n".join(lines) + "\n"


def index(m: dict, d: dict) -> str:
  reg = d["register"]
  pages = {c["wp"] for c in d["recent"]}
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py. Do not edit. -->", "",
           "# Change impact", "", "[← Back to the V-cycle](../../README.md#the-v-cycle) · " + picker_md(d, "index"), "",
           "Each work product's latest dated change, and what depends on it in the process model (WP-P-11): how many "
           "of those have a version dated after the change, how many have not, and how many have no dated version. "
           f"The {RECENT} most recent changes have a page with the V. A dependence is a prompt to look, not proof "
           "of an impact; the [impact analysis (WP-M-12)](../WP-M-12-impact-analysis.md) decides.", "",
           "| Change | Version | Dated | Downstream | Worth a look | Updated since | Undated |", "|---|---|---|---|---|---|---|"]
  for c in d["changes"]:
    rel = Path(os.path.relpath(reg[c["wp"]].path, vx.PAGES)).as_posix()
    name = f"[{c['wp']}]({page_name(c['wp'])})" if c["wp"] in pages else f"[{c['wp']}]({rel})"
    n = len(c["hop"]) - 1
    lines.append(f"| {name} {c['name']} | {c['version'] or '—'} | {c['when']} | {n} | {c['counts']['look']} | "
                 f"{c['counts']['ok']} | {c['counts']['undated']} |")
  return "\n".join(lines) + "\n"


def alt(c: dict) -> str:
  k = c["counts"]
  return (f"Change impact of {c['wp']} {c['name']}, dated {c['when']}: {len(c['hop']) - 1} work products depend on it "
          f"in the process model; {k['look']} have no version dated after it, {k['ok']} have been updated since, "
          f"{k['undated']} have no dated version.")


def render(m: dict) -> dict[Path, str]:
  d = model(m)
  files = {vx.PAGES / INDEX: index(m, d)}
  for c in d["recent"]:
    h, body = draw(m, d, c)
    files[vx.OUT / svg_name(c["wp"])] = fk.svg(W, h, f"Change impact: {c['wp']}", alt(c), body)
    files[vx.PAGES / page_name(c["wp"])] = page(m, d, c)
  return files
