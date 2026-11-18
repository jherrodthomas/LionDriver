#!/usr/bin/env python3
"""Conflicts on the V-cycle: only what is out of step, box by box.

Four kinds, each worked out from records that already exist:

- Older than an input it reads: a work product whose newest Version-row date is earlier than the newest change to a
  work product it reads (the producer inputs of the process model, WP-M-03).
- Verification older than what it checks: the newest change on a verification box is more than GRACE_DAYS earlier
  than the newest change on the definition box opposite it.
- Cites a standard no input cites: a work product whose WP-M-00 row cites a standard (the overlay columns of
  vcycle_standards) that none of the work products it reads cite.
- Due before an input it reads: a work product whose first gate (WP-M-00) is earlier than the first gate of a work
  product it reads.

A flag means look, not wrong: an older work product may still be right after its input changed. A flag clears when
the work product gets a new Version entry or a recorded review; the view never clears one.

One picture and one page, `assurance/01-management/vcycle/conflicts.md`, which lists every flag. Called by
fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import datetime as dt
import os
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
import vcycle_standards as vs  # noqa: E402
import vcycle_time as vt  # noqa: E402

SVG = "fig-m00-vcycle-conflicts.svg"
PAGE = "conflicts.md"
GRACE_DAYS = 7  # a verification box this many days or fewer behind the box it checks is not flagged
KINDS = [  # key, name, short tag, stroke, fill, how it is worked out (two lines)
  ("stale", "Older than an input it reads", "older than input", fk.AMBER, fk.AMBER_BG,
   ("a work product dated before the newest change", "to a work product it reads (WP-M-03 inputs)")),
  ("lag", "Verification older than what it checks", "older than definition", fk.SAFETY, fk.RED_BG,
   (f"the newest change on a verification box is more", f"than {GRACE_DAYS} days older than on the box it checks")),
  ("orphan", "Cites a standard no input cites", "standard from nowhere", fk.HW, fk.HW_BG,
   ("cites a standard in WP-M-00 that none of", "its inputs cite: check where it comes from")),
  ("gate", "Due before an input it reads", "gate order", fk.MUTED, fk.CHIP,
   ("due at an earlier gate than a work product", "it reads (WP-M-00 gate column)")),
]
KIND = {k[0]: k for k in KINDS}
W, BW, BH, STEP, PITCH, Y0 = 1640, 372, 96, 30, 108, 104


def date(s: str) -> dt.date:
  return dt.date.fromisoformat(s)


def short(s: str) -> str:
  d = date(s)
  return f"{d.day} {d:%b}"


def plural(n: int, word: str) -> str:
  return f"{n} {word}{'' if n == 1 else 's'}"


# ---------------------------------------------------------------- data

def newest(ids: list[str], last: dict[str, str]) -> tuple[str, str] | None:
  dated = [(last[w], w) for w in ids if w in last]
  return max(dated) if dated else None


def lag(define: dict, verify: dict, last: dict[str, str]) -> dict | None:
  """The verification box's lag behind the definition box opposite it, when over GRACE_DAYS; else None."""
  a, b = newest(define["ids"], last), newest(verify["ids"], last)
  if not a or not b:
    return None
  days = (date(a[0]) - date(b[0])).days
  if days <= GRACE_DAYS:
    return None
  return {"box": verify["title"], "checks": define["title"], "def": a, "ver": b, "days": days}


def model(m: dict) -> dict:
  producer, _, _, ctx = vx.process_facts()
  wps, reg = m["wps"], ctx.register
  last = vt.model(m)["last"]
  inputs = {w: sorted(i for i in producer.get(w, {}).get("inputs", []) if i in wps and i != w) for w in wps}
  stale = {}
  for w, ins in inputs.items():
    newer = [(last[i], i) for i in ins if w in last and i in last and last[i] > last[w]]
    if newer:
      stale[w] = sorted(newer, reverse=True)
  orphan: dict[str, list[str]] = {}
  for key, label, col, needle in vs.STANDARDS:
    for w, ins in inputs.items():
      if ins and vs.cell(reg[w], col, needle) and not any(vs.cell(reg[i], col, needle) for i in ins):
        orphan.setdefault(w, []).append(label)
  gate = {}
  for w, ins in inputs.items():
    late = [i for i in ins if min(wps[i]["gates"]) > min(wps[w]["gates"])]
    if late:
      gate[w] = late
  defs, vers = m["boxes"]["define"], m["boxes"]["verify"]
  if len(defs) != len(vers):
    raise FigureError(f"{len(defs)} definition boxes but {len(vers)} verification boxes; they pair by row")
  lags = {}
  for dbox, vbox in zip(defs, vers):
    g = lag(dbox, vbox, last)
    if g:
      lags[vbox["title"]] = g
  return {"stale": stale, "orphan": orphan, "gate": gate, "lag": lags, "last": last, "register": reg,
          "asof": max(last.values())}


def per_box(d: dict, b: dict) -> dict[str, list[str]]:
  ids = b["ids"]
  return {"stale": [w for w in ids if w in d["stale"]], "lag": [b["title"]] if b["title"] in d["lag"] else [],
          "orphan": [w for w in ids if w in d["orphan"]], "gate": [w for w in ids if w in d["gate"]]}


def totals(d: dict) -> dict[str, int]:
  return {k: len(d[k]) for k in KIND}


# ---------------------------------------------------------------- drawing

def tag(x: float, y: float, key: str, n: int) -> tuple[float, list[str]]:
  _, _, short_name, stroke, fill, _ = KIND[key]
  s = short_name if key == "lag" else f"{n} {short_name}"
  w = fk.text_w(s, 10.5, True) + 16
  return x + w + 6, [rect(x, y, w, 20, fill=fill, stroke=stroke, sw=1, rx=10), text(x + 8, y + 14, s, 10.5, stroke, 700)]


def example(d: dict, b: dict, p: dict, w: float) -> list[str]:
  if p["lag"]:
    g = d["lag"][b["title"]]
    return [text(0, 0, fk.fit(f"{g['ver'][1]} {short(g['ver'][0])}; {g['def'][1]} changed {short(g['def'][0])}, "
                              f"{g['days']} days later", w, 10.5), 10.5, fk.SAFETY)]
  if p["stale"]:
    wp = p["stale"][0]
    when, src = d["stale"][wp][0]
    more = f" (+{len(p['stale']) - 1} more)" if len(p["stale"]) > 1 else ""
    return [text(0, 0, fk.fit(f"e.g. {wp} last {short(d['last'][wp])}, reads {src} changed {short(when)}{more}", w,
                              10.5), 10.5, fk.MUTED)]
  if p["orphan"]:
    wp = p["orphan"][0]
    return [text(0, 0, fk.fit(f"e.g. {wp} cites {', '.join(d['orphan'][wp])}", w, 10.5), 10.5, fk.MUTED)]
  wp = p["gate"][0]
  return [text(0, 0, fk.fit(f"e.g. {wp} reads {', '.join(d['gate'][wp])}, due later", w, 10.5), 10.5, fk.MUTED)]


def box(x: float, y: float, w: float, b: dict, d: dict) -> list[str]:
  p = per_box(d, b)
  n = sum(len(v) for v in p.values())
  k = len(b["ids"])
  out = [rect(x, y, w, BH, fill="#FFFFFF" if n else fk.GREEN_BG, stroke=fk.INK if n else fk.GREEN, sw=1.4 if n else 1.2,
              rx=10),
         text(x + 14, y + 22, fk.fit(b["title"], w - 110, 13, True), 13, fk.INK, 700),
         text(x + w - 14, y + 22, plural(k, "work product"), 11, fk.MUTED, anchor="end")]
  if not n:
    return out + [text(x + 14, y + 54, "Nothing out of step", 12, fk.GREEN_DARK, 700)]
  xx = x + 14
  for key in KIND:
    if p[key]:
      xx, el = tag(xx, y + 34, key, len(p[key]))
      out += el
  out.append(f'<g transform="translate({x + 14:.1f},{y + 74:.1f})">' + "".join(example(d, b, p, w - 28)) + "</g>")
  return out


def chip(x: float, y: float, w: float, b: dict, d: dict) -> list[str]:
  p = per_box(d, b)
  n = sum(len(v) for v in p.values())
  out = [rect(x, y, w, 64, fill="#FFFFFF" if n else fk.GREEN_BG, stroke=fk.INK if n else fk.GREEN, sw=1.2, rx=10),
         text(x + 10, y + 18, fk.fit(b["title"], w - 20, 11.5, True), 11.5, fk.INK, 700)]
  yy = y + 38
  for key in ("stale", "orphan", "gate"):
    if p[key] or key != "gate":
      _, _, short_name, stroke, _, _ = KIND[key]
      out.append(text(x + 10, yy, f"{len(p[key])} {short_name}", 10.5, stroke if p[key] else fk.FAINT,
                      700 if p[key] else ""))
      yy += 16
  return out


def panel(d: dict, x: float, y: float, w: float) -> list[str]:
  t = totals(d)
  out = [text(x + 20, y + 30, "Out of step, by kind", 12, fk.MUTED, 700)]
  yy = y + 50
  for key, name, _, stroke, fill, how in KINDS:
    n = t[key]
    c = stroke if n else fk.GREEN_DARK
    out += [rect(x + 20, yy, w - 40, 92, fill=fill if n else fk.GREEN_BG, stroke=stroke if n else fk.GREEN,
                 sw=1.4 if n else 1, rx=10, dash="" if n else "4 3"),
            text(x + 36, yy + 26, name, 14, c, 700),
            text(x + w - 36, yy + 28, str(n), 20, c, 700, "end"),
            text(x + 36, yy + 50, how[0], 11, fk.MUTED), text(x + 36, yy + 66, how[1], 11, fk.MUTED)]
    yy += 104
  out += [text(x + 20, yy + 10, "A flag means look, not wrong: an older work", 11.5, fk.INK),
          text(x + 20, yy + 28, "product may still be right after its input", 11.5, fk.INK),
          text(x + 20, yy + 46, "changed. A new Version entry or a recorded", 11.5, fk.INK),
          text(x + 20, yy + 64, "review clears a flag; the view never does.", 11.5, fk.INK),
          text(x + 20, yy + 92, f"Dates: Version row of each work product, newest {d['asof']}.", 10.5, fk.MUTED,
               style="italic")]
  return [rect(x, y, w, yy + 110 - y, fill=fk.CHIP, stroke=fk.LINE, rx=12)] + out


def draw(m: dict, d: dict) -> tuple[int, list[str]]:
  body = [text(40, 44, "Conflicts on the V-cycle", 26, fk.INK, 700),
          text(40, 68, "Only what is out of step: work older than what it reads, verification older than what it "
               "checks, standards that appear without coming from upstream, and gate order.", 13, fk.MUTED)]
  nd = len(m["boxes"]["define"])
  for i in range(nd):
    y = Y0 + i * PITCH
    body += box(40 + i * STEP, y, BW, m["boxes"]["define"][i], d)
    body += box(1100 - BW - i * STEP, y, BW, m["boxes"]["verify"][i], d)
  body += box(1100 / 2 - 210 + 20, Y0 + nd * PITCH, 460, m["boxes"]["build"][0], d)
  yb = Y0 + nd * PITCH + BH + 22
  body.append(text(40, yb, "Runs across every phase", 12, fk.MUTED, 700))
  cw = (1100 - 40 - 4 * 10) / 5
  for i, b in enumerate(m["band"]):
    body += chip(40 + i * (cw + 10), yb + 10, cw, b, d)
  body += panel(d, 1140, Y0, 460)
  y = max(yb + 96, Y0 + 660)
  body.append(text(40, y, "Worked out from the WP-M-00 register, the WP-M-03 process model and each work product's "
                   "Version row; nothing is judged wrong by being flagged.", 11.5, fk.MUTED, style="italic"))
  foot, y = terms.svg_footer(body, 40, y + 24, W - 80)
  return int(y + 10), body + foot


# ---------------------------------------------------------------- page

def page(m: dict, d: dict) -> str:
  reg = d["register"]

  def link(wp: str) -> str:
    return f"[{wp}]({Path(os.path.relpath(reg[wp].path, vx.PAGES)).as_posix()})"

  t = totals(d)
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py. Do not edit. -->", "",
           "# Conflicts on the V-cycle", "",
           "[← Back to the V-cycle](../../README.md#the-v-cycle) · [change impact](impact.md) · "
           "[V-cycle over time](over-time.md)", "", "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{SVG}" width="100%" alt="{alt(d)}"></a>',
           "</p>", "",
           "*Only what is out of step. A flag means look, not wrong: an older work product may still be right after its "
           "input changed. A new Version entry or a recorded review clears a flag; the view never does. Drawn by "
           "[`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", ""]
  lines += ["## Verification older than what it checks", "",
            f"The newest change on a verification box against the newest on the definition box opposite it; a gap of "
            f"{GRACE_DAYS} days or fewer is not flagged.", ""]
  if d["lag"]:
    lines += ["| Verification box | Newest change | Checks | Newest change there | Days behind |", "|---|---|---|---|---|"]
    for g in d["lag"].values():
      lines.append(f"| [{g['box']}]({vx.slug(g['box'])}.md) | {link(g['ver'][1])} {g['ver'][0]} | "
                   f"[{g['checks']}]({vx.slug(g['checks'])}.md) | {link(g['def'][1])} {g['def'][0]} | {g['days']} |")
  else:
    lines.append("None.")
  lines += ["", f"## Older than an input it reads ({t['stale']})", "",
            "| Box | Work product | Last changed | Newer inputs |", "|---|---|---|---|"]
  for _, _, b in vx.all_boxes(m):
    for wp in per_box(d, b)["stale"]:
      ins = ", ".join(f"{link(i)} {when}" for when, i in d["stale"][wp])
      lines.append(f"| [{b['title']}]({vx.slug(b['title'])}.md) | {link(wp)} | {d['last'][wp]} | {ins} |")
  lines += ["", f"## Cites a standard no input cites ({t['orphan']})", "",
            "| Box | Work product | Standard |", "|---|---|---|"]
  for _, _, b in vx.all_boxes(m):
    for wp in per_box(d, b)["orphan"]:
      lines.append(f"| [{b['title']}]({vx.slug(b['title'])}.md) | {link(wp)} | {', '.join(d['orphan'][wp])} |")
  lines += ["", f"## Due before an input it reads ({t['gate']})", ""]
  if d["gate"]:
    lines += ["| Work product | First gate | Reads, due later |", "|---|---|---|"]
    for wp in sorted(d["gate"]):
      lines.append(f"| {link(wp)} | G{min(m['wps'][wp]['gates'])} | "
                   + ", ".join(f"{link(i)} G{min(m['wps'][i]['gates'])}" for i in d["gate"][wp]) + " |")
  else:
    lines.append("None: every work product is due at or after the gate of each work product it reads.")
  return "\n".join(lines) + "\n"


def alt(d: dict) -> str:
  t = totals(d)
  return (f"Conflicts on the V-cycle: {t['stale']} work products older than an input they read, {t['lag']} "
          f"verification boxes more than {GRACE_DAYS} days older than what they check, {t['orphan']} citing a standard "
          f"no input cites, {t['gate']} due before an input.")


def render(m: dict) -> dict[Path, str]:
  d = model(m)
  h, body = draw(m, d)
  return {vx.OUT / SVG: fk.svg(W, h, "Conflicts on the V-cycle", alt(d), body), vx.PAGES / PAGE: page(m, d)}
