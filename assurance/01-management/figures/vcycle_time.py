#!/usr/bin/env python3
"""The V-cycle over time: each box of the V as a row, what the records show happened and when the plan has it due.

One picture and one page, `assurance/01-management/vcycle/over-time.md`, linked from the V and its exploded views.

- Left panel, recorded history: one dot per day on which a work product in the row got a dated version entry,
  sized by how many did. The dates are the YYYY-MM-DD dates in each work product's `Version` cell, so the view
  does not depend on how much git history a checkout has. The panel ends at the latest such date ("as of"), not
  at the build date, so the output is deterministic.
- Orange count per row: work products whose input (the activity that produces them in the process model, WP-P-11)
  has a version dated after their own last one. A prompt to look, not proof the work product is wrong.
- Right panel, plan: each row from the previous gate to its own gate, earliest and latest dates from WP-M-03 §5.
- Bottom, four measures: trace freshness (computed), reviews recorded and gates passed (computed from the
  confirmation and gate records), and evidence latency, which needs approval dates the records do not hold yet.
  When a work product is first approved, that tile says the measure is not built yet instead of guessing.

Fails (FigureError) when a work product has no dated version entry, a row's gate has no date, or a gate date
cannot be read. Called by fig_m00_vcycle.py; it has no command line of its own.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(A / "trace" / "tools"))

import figkit as fk  # noqa: E402
from figkit import FigureError, fmt, rect, text, line, path  # noqa: E402
import terms  # noqa: E402
import vcycle_explode as vx  # noqa: E402

SVG = "fig-m00-vcycle-time.svg"
PAGE = "over-time.md"
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                      "Dec"], 1)}
# Abstraction level of each box, in words: L0-L5 already names the degradation levels (FSC §12.1).
LEVEL = {"define": ["Need", "System", "Subsystem", "Subsystem", "Component"], "build": ["Component"],
         "verify": ["Need", "System", "System", "Subsystem", "Component"]}
W, Y0, RH = 1640, 170, 56
HX0, HX1, PX0, PX1 = 330, 1000, 1070, 1600


# ---------------------------------------------------------------- data

def version_dates(row) -> list[str]:
  m = re.search(r"^\| Version \| (.*)$", row.path.read_text(encoding="utf-8"), re.M)
  if not m:
    raise FigureError(f"{row.wp}: no Version row")
  return sorted(set(re.findall(r"20\d\d-\d\d-\d\d", m.group(1))))  # empty for an undated 0.1


def month(s: str) -> dt.date:
  m = re.fullmatch(r"([A-Z][a-z]{2}) (\d{4})", s.strip())
  if not m or m.group(1) not in MONTHS:
    raise FigureError(f"WP-M-03 §5: cannot read the gate date {s!r}")
  return dt.date(int(m.group(2)), MONTHS[m.group(1)], 1)


def gate_dates(m: dict) -> dict[str, tuple[dt.date, dt.date]]:
  out = {}
  for p in m["phases"]:
    if p["when"] == "continuous":
      continue
    a, _, b = p["when"].partition("–")
    out[p["gate"]] = (month(a), month(b or a))
  return out


def rows(m: dict) -> list[dict]:
  """Rows in V order: down the definition side, implementation, up the verification side."""
  out = []
  for side, order in (("define", 1), ("build", 1), ("verify", -1)):
    boxes = m["boxes"][side]
    if len(boxes) != len(LEVEL[side]):
      raise FigureError(f"{side}: {len(boxes)} boxes but {len(LEVEL[side])} levels in LEVEL")
    pairs = list(zip(boxes, LEVEL[side]))
    out += [{"box": b, "side": side, "level": lv} for b, lv in pairs[::order]]
  return out


def model(m: dict) -> dict:
  producer, _, reviews, ctx = vx.process_facts()
  dates = {w: version_dates(ctx.register[w]) for w in m["wps"]}
  undated = sorted(w for w, ds in dates.items() if not ds)
  dates = {w: ds for w, ds in dates.items() if ds}
  if not dates:
    raise FigureError("no work product has a dated version entry")
  last = {w: ds[-1] for w, ds in dates.items()}
  newer: dict[str, tuple[str, str]] = {}
  for w in last:
    ins = [(i, last[i]) for i in producer.get(w, {}).get("inputs", []) if i in last and last[i] > last[w]]
    if ins:
      newer[w] = max(ins, key=lambda t: (t[1], t[0]))
  rv = vx.dedupe([(vx.pm.measure_id(r["id"]), r["name"], vx.pm.record_present(r, ctx.register))
                  for _, r in sorted(reviews.items())])
  first = min(d[0] for d in dates.values())
  asof = max(last.values())
  return {"dates": dates, "undated": undated, "last": last, "newer": newer, "first": first, "asof": asof, "rows": rows(m),
          "gates": gate_dates(m), "reviews": rv, "status": {w: v["status"] for w, v in m["wps"].items()}}


# ---------------------------------------------------------------- drawing

def gate_label(gates: list[int]) -> str:
  import fig_m00_vcycle as v
  return v.gate_label(gates)



def draw(m: dict, d: dict) -> tuple[int, list[str]]:
  d0, d1 = dt.date.fromisoformat(d["first"]), dt.date.fromisoformat(d["asof"])
  nd = max((d1 - d0).days, 1)
  gates = d["gates"]
  p0 = d1.replace(day=1)
  p1 = dt.date(max(b for _, b in gates.values()).year + 1, 7, 1)

  def hx(s):
    return HX0 + (dt.date.fromisoformat(s) - d0).days / nd * (HX1 - HX0)

  def px(t):
    return PX0 + (t - p0).days / (p1 - p0).days * (PX1 - PX0)

  n_wp = len(d["last"])
  body = [text(40, 44, "LionDriver V-cycle over time", 28, fk.INK, 700),
          text(40, 70, "Each row is a box of the V, tagged with its level (need, system, subsystem, component). Left: what the records show happened, day by day. Right: when the "
               "plan has each row due. Bottom: what can be measured from that.", 13.5, fk.MUTED),
          text(HX0, 124, f"Recorded history · {d0:%d %b %Y} – {d1:%d %b %Y} (dated entries in each work product's "
               "Version row)", 11.5, fk.MUTED, 700),
          text(PX0, 124, "Plan · each row from the previous gate to its own gate (WP-M-03 §5)", 11.5, fk.MUTED, 700)]
  ybot = Y0 + len(d["rows"]) * RH
  step = 7 if nd <= 70 else 28
  for k in range(0, nd + 1, step):
    x = HX0 + k / nd * (HX1 - HX0)
    body += [line(x, Y0 - 6, x, ybot, stroke=fk.HAIR, sw=1),
             text(x, ybot + 16, f"{d0 + dt.timedelta(days=k):%d %b}", 10.5, fk.FAINT, anchor="middle")]
  for y in range(p0.year + 1, p1.year + 1):
    x = px(dt.date(y, 1, 1))
    body += [line(x, Y0 - 6, x, ybot, stroke=fk.HAIR, sw=1), text(x, ybot + 16, str(y), 10.5, fk.FAINT, anchor="middle")]
  for g, (a, _) in gates.items():
    x = px(a)
    body.append(path(f"M{fmt(x)} {Y0 - 16} l6 6 l-6 6 l-6 -6 z", stroke=fk.DEFINE, sw=1.5, fill="#FFFFFF"))
    body.append(text(x, Y0 - 22, g, 10, fk.DEFINE, 700, "middle"))
  body.append(path(f"M1030 {Y0 - 10} l-8 {fmt((ybot - Y0 + 10) / 2)} l8 {fmt((ybot - Y0 + 10) / 2)}", stroke=fk.LINE,
                   sw=1, dash="4 4"))
  body.append(text(1035, ybot + 34, "time axis broken: recorded history on the left, the plan to the last gate on the "
                   "right", 10.5, fk.FAINT, anchor="middle", style="italic"))
  for i, r in enumerate(d["rows"]):
    b, y = r["box"], Y0 + i * RH
    col, bg = {"define": (fk.DEFINE, fk.DEFINE_BG), "build": (fk.INK, fk.GREY_BG), "verify": (fk.VERIFY, fk.VERIFY_BG)}[r["side"]]
    cy = y + RH / 2
    body.append(rect(40, y + 4, W - 80, RH - 8, fill=fk.CHIP if i % 2 == 0 else "#FFFFFF", stroke=fk.HAIR, sw=1, rx=6))
    p, pw = fk.pill(0, 0, r["level"], bg, col, h=18, size=10, stroke=col)
    body.append(f'<g transform="translate(50,{fmt(y + 8)})">' + "".join(p) + "</g>")
    body.append(text(50, y + 44, fk.fit(b["title"], 270, 12.5, True), 12.5, fk.INK, 700))
    st = {}
    for w in b["ids"]:
      st[d["status"][w]] = st.get(d["status"][w], 0) + 1
    states = ", ".join(f"{n} {vx.pm.STATUS_NAMES[s].lower()}" for s, n in sorted(st.items()))
    body.append(text(50 + pw + 8, y + 22, fk.fit(f"{len(b['ids'])} work product{'s' if len(b['ids']) != 1 else ''} · {states}"
                                        f" · gate {gate_label(b['gates'])}", 262 - pw, 10.5), 10.5, fk.MUTED))
    body.append(line(HX0, cy, HX1, cy, stroke=fk.HAIR, sw=2))
    per_day: dict[str, int] = {}
    for w in b["ids"]:
      for s in d["dates"].get(w, []):
        per_day[s] = per_day.get(s, 0) + 1
    for s, c in sorted(per_day.items()):
      body.append(f'<circle cx="{fmt(hx(s))}" cy="{fmt(cy)}" r="{fmt(3 + min(c, 8) * 1.2)}" fill="{col}" opacity=".55"/>')
    k = sum(1 for w in b["ids"] if w in d["newer"])
    if k:
      body.append(f'<circle cx="{HX1 + 14}" cy="{fmt(cy)}" r="9" fill="{fk.SAFETY_BG}" stroke="{fk.SAFETY}" stroke-width="1.5"/>')
      body.append(text(HX1 + 14, cy + 4, str(k), 10.5, fk.SAFETY, 700, "middle"))
    g = f"G{b['gates'][-1]}"
    if g not in gates:
      raise FigureError(f"{b['title']}: gate {g} has no date in WP-M-03 §5")
    prev = f"G{int(g[1]) - 1}"
    a = gates[prev][0] if prev in gates else p0
    e0, e1 = gates[g]
    body.append(rect(px(a), cy - 8, px(e0) - px(a), 16, fill=bg, stroke=col, sw=1.2, rx=4))
    if e1 > e0:
      body.append(rect(px(e0), cy - 8, px(e1) - px(e0), 16, fill=bg, stroke=col, sw=1, rx=4, dash="3 2", opacity=".6"))
  x = px(d1)
  body += [line(x, Y0 - 6, x, ybot, stroke=fk.SAFETY, sw=2), text(x + 4, ybot - 4, "as of", 10, fk.SAFETY, 700)]
  ly = ybot + 56
  body += [f'<circle cx="{HX0 + 6}" cy="{ly - 4}" r="7" fill="{fk.DEFINE}" opacity=".55"/>',
           text(HX0 + 20, ly, "version entries that day (bigger = more work products changed)", 11, fk.MUTED),
           f'<circle cx="{HX0 + 6}" cy="{ly + 16}" r="8" fill="{fk.SAFETY_BG}" stroke="{fk.SAFETY}" stroke-width="1.5"/>',
           text(HX0 + 20, ly + 20, "work products in the row with an input dated after their own last version", 11,
                fk.MUTED),
           rect(PX0, ly - 12, 26, 12, fill=fk.DEFINE_BG, stroke=fk.DEFINE, sw=1.2, rx=3),
           text(PX0 + 32, ly, "to the gate's earliest date", 11, fk.MUTED),
           rect(PX0 + 200, ly - 12, 26, 12, fill=fk.DEFINE_BG, stroke=fk.DEFINE, sw=1, rx=3, dash="3 2", opacity=".6"),
           text(PX0 + 232, ly, "to its latest date", 11, fk.MUTED)]
  body += tiles(m, d, ly + 40)
  fy = ly + 40 + 118 + 26
  spread = "were all drafted within" if all(s in ("S", "D") for s in d["status"].values()) else "changed within"
  body.append(text(40, fy, f"As of {d1:%d %b %Y}: the {n_wp} dated work products {spread} {nd + 1} days, while the plan has "
                   "the rows due one after another. The left side spreads out into that order as reviews, gates and "
                   "evidence are recorded.", 11.5, fk.INK))
  body.append(text(40, fy + 20, "Dates come from each work product's Version row; inputs from the process model "
                   "(WP-P-11). An input dated later is a prompt to look, not proof the work product is wrong. Status is "
                   "not acceptance.", 11, fk.MUTED, style="italic"))
  foot, y = terms.svg_footer(body, 40, fy + 44, W - 80)
  return int(y + 10), body + foot


def tiles(m: dict, d: dict, y: float) -> list[str]:
  n_wp, n_new = len(d["last"]), len(d["newer"])
  ex = sorted(d["newer"].items(), key=lambda kv: (kv[1][1], kv[0]))[-1] if d["newer"] else None
  done = sum(1 for _, _, ok in d["reviews"] if ok)
  passed = sum(1 for p in m["phases"] if p["passed"])
  approved = sum(1 for s in d["status"].values() if s in ("A", "B"))
  rows_ = [
    ("Trace freshness", f"{n_new} of {n_wp}",
     (f"work products have an input dated after their own last version, e.g. {ex[0]} "
      f"({dt.date.fromisoformat(d['last'][ex[0]]):%d %b}) needs {ex[1][0]} (dated "
      f"{dt.date.fromisoformat(ex[1][1]):%d %b})") if ex else "no work product has an input dated after it", n_new > 0),
    ("Reviews recorded", f"{done} of {len(d['reviews'])}",
     "confirmation measures of WP-M-06 with a record in 10-safety-case/confirmation/", False),
    ("Gates passed", f"{passed} of 7", "a gate counts once its review record in 10-safety-case/gates/ is ticked Pass",
     False),
    ("Evidence latency", "not yet measurable" if not approved else "not built yet",
     "no work product is approved, so there is no baseline to measure from" if not approved else
     f"{approved} approved; measuring needs approval dates the records do not hold yet", False)]
  tw, out = (W - 80 - 36) / 4, []
  for k, (h, val, note, warn) in enumerate(rows_):
    x = 40 + k * (tw + 12)
    out.append(rect(x, y, tw, 118, fill=fk.SAFETY_BG if warn else fk.CHIP, stroke=fk.SAFETY if warn else fk.LINE,
                    sw=1.2, rx=10))
    out.append(text(x + 16, y + 24, h, 12, fk.MUTED, 700))
    out.append(text(x + 16, y + 54, val, 22 if len(val) < 12 else 17, fk.SAFETY if warn else fk.INK, 700))
    words, ln, yy = note.split(), "", y + 76
    for wd in words:
      if ln and fk.text_w(ln + " " + wd, 10.5) > tw - 32:
        out.append(text(x + 16, yy, ln, 10.5, fk.MUTED))
        yy, ln = yy + 14, wd
      else:
        ln = (ln + " " + wd).strip()
    out.append(text(x + 16, yy, ln, 10.5, fk.MUTED))
  return out


# ---------------------------------------------------------------- page

def page(m: dict, d: dict) -> str:
  stale = sorted(d["newer"].items())
  lines = ["<!-- GENERATED by assurance/01-management/figures/fig_m00_vcycle.py from WP-M-00, WP-M-03 and the process "
           "model. Do not edit. -->", "", "# V-cycle over time", "",
           "[← Back to the V-cycle](../../README.md#the-v-cycle) · [exploded views](README.md)", "",
           "<p align=\"center\">",
           f'  <a href="../../README.md#the-v-cycle"><img src="../figures/vcycle/{SVG}" width="100%" alt="{alt(d)}"></a>',
           "</p>", "",
           "*Each row is a box of the V, tagged with its level: need, system, subsystem or component. Left: the days on which its work products got a dated version "
           "entry. Right: the plan, from the previous gate to the row's own gate. Drawn by "
           "[`fig_m00_vcycle.py`](../figures/fig_m00_vcycle.py); CI fails if it is stale.*", "",
           "## Work products with an input dated after their own last version", "",
           "A prompt to look, not proof the work product is wrong: the input may have changed in a way that does not "
           "affect it.", ""]
  if stale:
    lines += ["| Work product | Its last version | Input dated later | Input's last version |", "|---|---|---|---|"]
    lines += [f"| {w} | {d['last'][w]} | {i} | {di} |" for w, (i, di) in stale]
  else:
    lines.append("None.")
  lines += ["", "## Work products with no dated version entry", "",
            "Still at a first version with no date, so they are not drawn on the history and not in the freshness "
            "check.", ""]
  lines += [f"- {w}" for w in d["undated"]] or ["None."]
  return "\n".join(lines) + "\n"


def alt(d: dict) -> str:
  return (f"The V-cycle over time as of {d['asof']}: {len(d['rows'])} rows from concept down to implementation and back "
          f"up to vehicle validation. {len(d['last'])} work products have dated versions between {d['first']} and "
          f"{d['asof']} ({len(d['undated'])} undated); {len(d['newer'])} have an input dated after their own last version. The plan runs each row "
          "from the previous gate to its own gate.")


def render(m: dict) -> dict[Path, str]:
  d = model(m)
  h, body = draw(m, d)
  return {vx.OUT / SVG: fk.svg(W, h, "LionDriver V-cycle over time", alt(d), body), vx.PAGES / PAGE: page(m, d)}
