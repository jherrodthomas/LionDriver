#!/usr/bin/env python3
"""Draw the two figures of the software folder page's own section and write that section (index-section.md).

- Figure W-0-3 (`fig-w00-3-one-requirement.svg`), follow one requirement through the software: SWSR-407, heartbeat
  loss, from the functional safety requirement it serves through its TSR, itself, the component and unit it is allocated
  to, the code that implements it and the state-machine transition that realises it, to the test cases that verify it
  and its status. Every link is read from the records: the SWSR's parents and allocation (trace/items/swsr.yaml), the
  TSR's parent (tsr.yaml) and the FSR (fsr.yaml), the unit whose SWSR column names it (WP-W-05 §2), the code file and
  pin in its Baseline column, the SM-TOY-AUTH transition whose swsr list holds it (state-machines/), and the cases
  whose SWSR column names it (WP-W-06 §6, WP-W-07 §5, WP-W-08 §5).
- Figure W-0-4 (`fig-w00-4-safety-task-anim.svg`), the safety task in time, animated: a UML timing diagram of one
  heartbeat loss. The host's heartbeat arrives at its rate; each one resets the heartbeat age; the 100 Hz safety task
  counts it up; at the threshold the task revokes authority (SM-TOY-AUTH T10a) and starts the siren. The rates, the
  threshold, the siren hold and the TSR's budget are read from WP-W-03 §3.1, WP-W-05 §4, the TSR and T10a.

The build fails if a link of the chain is missing or ambiguous, or a timing constant can no longer be read. CSS
animation only; with reduced motion the cursor rests at the revocation. folder_index.py places index-section.md under
the tables of 05-software/README.md, its links rebased.

    python3 fig_w00_stories.py            # write both SVGs and index-section.md
    python3 fig_w00_stories.py --check    # fail if a source changed shape or an output is stale

Standard library only (PyYAML if present, through check_state_machines). Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOFTWARE = HERE.parent
ASSURANCE = HERE.parents[1]
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from figkit import (INK, MUTED, FAINT, LINE, HAIR, SW, SW_BG, HW, HW_BG, GREEN, GREEN_BG, AMBER, AMBER_BG, RED,  # noqa: E402
                    RED_BG, SAFETY, SAFETY_BG, GREY_BG, FigureError, text, rect, line, path, svg, pill, text_w, fit)
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402
import check_state_machines as csm  # noqa: E402

OUT_R, OUT_T, SECTION = "fig-w00-3-one-requirement.svg", "fig-w00-4-safety-task-anim.svg", "index-section.md"
ITEMS = ASSURANCE / "trace" / "items"
REQ = "SWSR-407"
MACHINE = "SM-TOY-AUTH"
TESTS = [("WP-W-06", r"VS-UV-\d+", "unit"), ("WP-W-07", r"VS-SWI-\d+", "integration"), ("WP-W-08", r"VS-SWQ-\d+", "HIL")]
W = 500
STEPS, LOOP = 24, 9.0


def records(name: str) -> dict[str, dict]:
  out = {}
  for rec in re.split(r"\n(?=- id: )", (ITEMS / name).read_text(encoding="utf-8")):
    m = re.search(r"^- id: (\S+)", rec, re.M)
    if not m:
      continue
    def f(k, rec=rec):
      mm = re.search(rf'^  {k}: "?(.*?)"?$', rec, re.M)
      return mm.group(1) if mm else ""
    par = re.search(r"^  parents: \[(.*?)\]", rec, re.M)
    out[m.group(1)] = {k: f(k) for k in ("text", "asil", "allocated_to", "timing", "baseline_impl", "acceptance")}
    out[m.group(1)]["parents"] = [p.strip() for p in par.group(1).split(",")] if par else []
  return out


def doc(wid: str) -> str:
  hits = sorted(SOFTWARE.glob(f"{wid}-*.md"))
  if len(hits) != 1:
    raise FigureError(f"{wid}: expected one document, found {len(hits)}")
  return hits[0].read_text(encoding="utf-8")


def one(items: list, what: str):
  if len(items) != 1:
    raise FigureError(f"{REQ}: expected one {what}, found {len(items)}: {items}")
  return items[0]


def chain() -> dict:
  sw = records("swsr.yaml")
  if REQ not in sw:
    raise FigureError(f"{REQ} is not in swsr.yaml")
  s = sw[REQ]
  tsr_id = one([p for p in s["parents"] if p.startswith("TSR-")], "parent TSR")
  tsr = records("tsr.yaml")[tsr_id]
  fsr_id = one([p for p in tsr["parents"] if p.startswith("FSR-")], "parent FSR")
  fsr = records("fsr.yaml")[fsr_id]
  num = REQ.split("-")[1]
  w05 = doc("WP-W-05")
  units = []
  for ln in w05.splitlines():
    c = [x.strip() for x in ln.strip().strip("|").split("|")]
    if len(c) > 7 and re.fullmatch(r"UN-(?:\d+|N\d)", c[0]) and re.search(rf"(?<!\d){num}(?![\d(])", c[-1].split("(not yet)")[0]):
      units.append({"id": c[0], "fn": c[1].split(" (")[0], "comp": c[4], "ctx": c[5]})
  units = [x for x in units if x["comp"] == s["allocated_to"]]   # the units of the component it is allocated to
  if not units:
    raise FigureError(f"{REQ}: no unit of {s['allocated_to']} in WP-W-05 §2 names it")
  code = one(sorted(set(re.findall(r"`((?:drivers|board)/[\w/.]+\.h)`", s["baseline_impl"]))), "code file in the Baseline column")
  pin = re.search(r"panda `([0-9a-f]{7})`", s["baseline_impl"])
  if not pin:
    raise FigureError(f"{REQ}: no panda pin in the Baseline column")
  sm = csm.load(csm.SM_DIR / "sm-toy-auth.yaml")
  tr = one([t for t in sm["transitions"] if REQ in t.get("swsr", [])], f"transition of {MACHINE}")
  tests = []
  for wid, rx, level in TESTS:
    md = doc(wid)
    for ln in md.splitlines():
      m = re.match(rf"^\| ({rx}) \|(.*)$", ln)
      if m and re.search(rf"(?<![\d.-]){num}(?!\d)|{REQ}(?!\d)", m.group(2)):
        cells = [x.strip() for x in m.group(2).split("|")]
        tests.append({"id": m.group(1), "level": level, "what": cells[1] if wid == "WP-W-06" else cells[0]})
  if not tests:
    raise FigureError(f"{REQ}: no test case names it")
  state = csm.impl_state(s["baseline_impl"])
  return {"fsr": (fsr_id, fsr), "tsr": (tsr_id, tsr), "swsr": (REQ, s), "code": code, "pin": pin.group(1),
          "transition": tr, "tests": tests, "units": units, "state": state,
          "hardware": "not yet verified on hardware" in s["baseline_impl"]}


def wrap(s: str, width: float, size: float, rows: int = 3) -> list[str]:
  """s in lines of at most width, at most rows of them, the last ending in an ellipsis when s was cut."""
  s = s.replace("`", "")
  out, cur = [], ""
  for wd in s.split():
    cand = (cur + " " + wd).strip()
    if text_w(cand, size) > width and cur:
      out.append(cur)
      cur = wd
    else:
      cur = cand
  out += [cur] if cur else []
  if len(out) > rows:
    out = out[:rows]
    out[-1] = fit(out[-1] + " …", width, size)
  return out


def card(y, stage, pid, col, bg, lines, meta) -> tuple[list[str], float]:
  body = [l_ for l_ in lines[:3]]
  h = 34 + 15 * len(body) + (16 if meta else 0)
  out = [rect(16, y, W - 32, h, fill="#FFFFFF", stroke=LINE, rx=10), rect(16, y + 8, 4, h - 16, fill=col, stroke="none", rx=2)]
  out.append(text(30, y + 18, stage[0].upper() + stage[1:], size=9.5, weight=700, fill=MUTED))
  p, pw = pill(W - 30 - (text_w(pid, 9.5, True) + 12), y + 7, pid, bg, col, h=16, size=9.5, stroke=col)
  out += p
  for i, ln in enumerate(body):
    out.append(text(30, y + 36 + 15 * i, ln, size=11.5, weight=700 if i == 0 else "", fill=INK))
  if meta:
    out.append(text(30, y + 36 + 15 * len(body), meta, size=10, fill=MUTED))
  return out, h


def arrow(y1, y2, label) -> list[str]:
  x = 46
  return [line(x, y1, x, y2 - 6, stroke=MUTED, sw=1.6), path(f"M{x - 4} {y2 - 9} L{x} {y2 - 2} L{x + 4} {y2 - 9} Z", stroke="none",
          fill=MUTED), text(x + 12, (y1 + y2) / 2 + 4, label, size=10, fill=MUTED)]


def figure_chain(c: dict) -> str:
  out = [text(16, 30, "Follow one requirement", size=18, weight=700),
         text(16, 50, f"{REQ}, heartbeat loss, from the safety requirement it", size=11.5, fill=MUTED),
         text(16, 66, "serves to the code and the tests that verify it.", size=11.5, fill=MUTED)]
  fsr_id, fsr = c["fsr"]
  tsr_id, tsr = c["tsr"]
  sid, s = c["swsr"]
  us, tr = c["units"], c["transition"]
  tw = W - 32 - 40
  cards = [
    ("functional safety requirement", fsr_id, SAFETY, SAFETY_BG, wrap(fsr["text"], tw, 11.5), f"ASIL {fsr['asil']} · WP-C-04", "refines"),
    ("technical safety requirement", tsr_id, SAFETY, SAFETY_BG, wrap(tsr["text"], tw, 11.5), f"ASIL {tsr['asil']} · {tsr['timing']}",
     "refines"),
    ("software safety requirement", sid, SW, SW_BG, wrap(s["text"], tw, 11.5), f"ASIL {s['asil']} · accept: {s['acceptance']}",
     "allocated to"),
    ("component and units", f"{s['allocated_to']}", SW, SW_BG,
     [f"{u['id']} {u['fn'].replace('`', '')}" for u in us], fit(" · ".join(f"{u['id']}: {u['ctx']}" for u in us), tw, 10),
     "implemented in"),
    ("code", c["pin"], INK, GREY_BG, [f"panda {c['code']}"], f"panda commit {c['pin']}", "realises"),
    ("state-machine transition", f"{MACHINE} {tr['id']}", SW, SW_BG,
     wrap(f"{tr['from']} → {tr['to']} on {tr['event']}: {tr['action']}", tw, 11.5), f"build {tr['build']}", "verified by"),
  ]
  y = 86
  for i, (stage, pid, col, bg, lines, meta, rel) in enumerate(cards):
    p, h = card(y, stage, pid, col, bg, lines, meta)
    out += p
    y += h
    out += arrow(y, y + 30, rel)
    y += 30
  out.append(rect(16, y, W - 32, 30 + 18 * len(c["tests"]), fill="#FFFFFF", stroke=LINE, rx=10))
  out.append(rect(16, y + 8, 4, 14 + 18 * len(c["tests"]), fill=HW, stroke="none", rx=2))
  out.append(text(30, y + 18, "Test cases", size=9.5, weight=700, fill=MUTED))
  for i, t in enumerate(c["tests"]):
    yy = y + 36 + 18 * i
    p, pw = pill(30, yy - 12, t["id"], HW_BG, HW, h=15, size=9, stroke=HW)
    out += p
    out.append(text(36 + pw, yy, fit(f"{t['level']}: {t['what']}".replace("`", ""), W - 70 - pw, 10.5), size=10.5))
  y += 30 + 18 * len(c["tests"]) + 14
  label = {"impl": ("in the code", GREEN, GREEN_BG), "partial": ("partly in the code", AMBER, AMBER_BG),
           "not": ("not in the code", RED, RED_BG)}.get(c["state"], ("not assessed", MUTED, GREY_BG))
  out.append(rect(16, y, W - 32, 44, fill=label[2], stroke=label[1], rx=10))
  out.append(text(30, y + 18, "Status", size=9.5, weight=700, fill=label[1]))
  out.append(text(30, y + 35, label[0][0].upper() + label[0][1:] + ("; not yet verified on hardware" if c["hardware"] else ""),
                  size=11.5, weight=700, fill=label[1]))
  y += 44 + 18
  out.append(text(16, y, "Every link read from the records: swsr.yaml, tsr.yaml, fsr.yaml,", size=10, fill=MUTED))
  out.append(text(16, y + 14, "WP-W-05 §2, the state-machine record and WP-W-06/07/08.", size=10, fill=MUTED))
  extra, y = terms.svg_footer(out, 16, y + 34, W - 32, size=10)
  out += extra
  out.append(text(W - 16, y + 6, "Generated by fig_w00_stories.py", size=10, fill=FAINT, anchor="end"))
  desc = (f"{fsr_id} → {tsr_id} → {sid} → {s['allocated_to']} {', '.join(u['id'] for u in us)} → panda {c['code']} ({c['pin']}) → {MACHINE} "
          f"{tr['id']} → " + ", ".join(t["id"] for t in c["tests"]) + f"; {label[0]}")
  return svg(W, int(y + 18), "Figure W-0-3. Follow one requirement", desc, out)


def constants(c: dict) -> dict:
  w03, w05 = doc("WP-W-03"), doc("WP-W-05")
  m = re.search(r"SAFETY_TASK_FREQ` = (\d+) Hz", w03)
  th = re.search(r"returns true while it is ≥ (\d+) \((\d+(?:\.\d+)?) s at (\d+) Hz", w05)
  hb = re.search(r"host sends it at (\d+) Hz", c["tsr"][1]["baseline_impl"])
  sir = re.search(r"siren (\d+) s", str(c["transition"].get("action", "")))
  bud = re.search(r"detect ≤ ([\d.]+) s / react ≤ ([\d.]+) s", c["tsr"][1]["timing"])
  for name, v in (("SAFETY_TASK_FREQ", m), ("heartbeat threshold", th), ("heartbeat rate", hb), ("siren hold", sir),
                  ("TSR budget", bud)):
    if not v:
      raise FigureError(f"cannot read the {name}")
  f = int(m.group(1))
  if int(th.group(3)) != f or abs(int(th.group(1)) / f - float(th.group(2))) > 1e-9:
    raise FigureError("WP-W-05 threshold disagrees with the safety-task frequency")
  return {"f": f, "ticks": int(th.group(1)), "t_th": float(th.group(2)), "hb": int(hb.group(1)), "siren": int(sir.group(1)),
          "detect": float(bud.group(1)), "react": float(bud.group(2))}


def figure_timing(c: dict, k: dict) -> str:
  t0, t1 = -0.35, 0.6
  x0, x1 = 120, W - 20
  xs = lambda t: x0 + (x1 - x0) * (t - t0) / (t1 - t0)  # noqa: E731
  period = 1 / k["hb"]
  beats = [-(i * period) for i in range(int(-t0 / period) + 1)][::-1]
  t_rev = k["t_th"]
  out = [text(16, 30, "The safety task in time", size=18, weight=700),
         text(16, 50, f"One heartbeat loss as a UML timing diagram: the {k['f']} Hz", size=11.5, fill=MUTED),
         text(16, 66, f"task revokes authority {k['t_th']:g} s after the last heartbeat.", size=11.5, fill=MUTED)]
  lanes = [("host heartbeat", f"0xf3 at {k['hb']} Hz"), ("heartbeat age", f"{k['f']} Hz task, ticks"),
           ("controls_allowed", MACHINE), ("siren", f"{k['siren']} s hold")]
  ly, lh = 96, 70
  for i, (name, sub) in enumerate(lanes):
    y = ly + i * lh
    out.append(rect(16, y, W - 32, lh - 8, fill="#FFFFFF" if i % 2 else "#F8FAFC", stroke=HAIR, rx=6))
    out.append(text(24, y + 22, name, size=11, weight=700))
    out.append(text(24, y + 38, sub, size=9.5, fill=MUTED))
  # budget band
  yb = ly + len(lanes) * lh
  out.append(rect(xs(0), ly - 6, xs(k["detect"]) - xs(0), yb - ly, fill=AMBER_BG, stroke="none", rx=0, opacity="0.55"))
  out.append(rect(xs(k["detect"]), ly - 6, xs(k["detect"] + k["react"]) - xs(k["detect"]), yb - ly, fill=SAFETY_BG,
                  stroke="none", rx=0, opacity="0.7"))
  # lane 1: heartbeat pulses
  y = ly + 10
  for b in beats:
    out.append(line(xs(b), y + 40, xs(b), y + 8, stroke=SW, sw=2.4))
  out.append(text(xs(0) + 4, y + 10, "last heartbeat", size=9.5, fill=SW, weight=700))
  # lane 2: age ramp with threshold
  y = ly + lh + 8
  amax = k["ticks"] * 1.25
  ya = lambda a: y + 48 - 40 * min(a, amax) / amax  # noqa: E731
  pts = []
  for i, b in enumerate(beats):
    nxt = beats[i + 1] if i + 1 < len(beats) else t_rev
    pts += [(xs(b), ya(0)), (xs(nxt), ya(k["ticks"] * (nxt - b) / k["t_th"]))]
  pts.append((xs(t1), ya(k["ticks"])))
  out.append(path("M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts), stroke=HW, sw=2))
  out.append(line(x0, ya(k["ticks"]), x1, ya(k["ticks"]), stroke=RED, sw=1, dash="4 3"))
  out.append(text(x1 - 2, ya(k["ticks"]) - 3, f"{k['ticks']} ticks", size=9, fill=RED, anchor="end"))
  # lane 3: authority
  y = ly + 2 * lh + 8
  out.append(path(f"M{xs(t0)} {y + 12} L{xs(t_rev)} {y + 12} L{xs(t_rev)} {y + 42} L{xs(t1)} {y + 42}", stroke=INK, sw=2))
  out.append(text(xs(t0) + 4, y + 8, "granted", size=9.5, fill=MUTED))
  out.append(text(xs(t_rev) + 6, y + 38, f"revoked ({c['transition']['id']})", size=9.5, fill=RED, weight=700))
  # lane 4: siren
  y = ly + 3 * lh + 8
  out.append(path(f"M{xs(t0)} {y + 42} L{xs(t_rev)} {y + 42} L{xs(t_rev)} {y + 12} L{xs(t1)} {y + 12}", stroke=SAFETY, sw=2))
  out.append(text(x1 - 2, y + 26, f"on for {k['siren']} s →", size=9.5, fill=SAFETY, anchor="end"))
  for t in (-0.3, 0, 0.1, 0.2, 0.3, 0.4, 0.5):
    out.append(text(xs(t), yb + 10, f"{t:+.1f} s" if t else "0", size=9, fill=FAINT, anchor="middle"))
  out.append(text(xs(k["detect"] / 2), ly - 10, f"detect ≤ {k['detect']:g} s", size=9, fill=AMBER, anchor="middle", weight=700))
  out.append(text(xs(k["detect"] + k["react"] / 2), ly - 10, f"≤ {k['react']:g} s", size=9, fill=SAFETY, anchor="middle",
                  weight=700))
  # cursor and readout
  ts = [t0 + (t1 - t0) * i / STEPS for i in range(STEPS + 1)]
  keep = min(range(len(ts)), key=lambda i: abs(ts[i] - t_rev - 0.01))
  css = [f".st{{opacity:0;animation:{LOOP:g}s steps(1,end) infinite}}"]
  for i in range(len(ts)):
    a, b = 100 * i / len(ts), 100 * (i + 1) / len(ts)
    css.append(f"@keyframes s{i}{{0%{{opacity:{1 if i == 0 else 0}}}{a:.2f}%{{opacity:1}}{b:.2f}%{{opacity:0}}"
               f"100%{{opacity:{1 if i == 0 else 0}}}}}.s{i}{{animation-name:s{i}}}")
  css.append(f"@keyframes cur{{0%{{transform:translateX(0)}}{100 * STEPS / (STEPS + 1):.2f}%{{transform:translateX("
             f"{x1 - x0}px)}}100%{{transform:translateX({x1 - x0}px)}}}}.cur{{animation:cur {LOOP:g}s linear infinite}}")
  css.append(f"@media (prefers-reduced-motion:reduce){{.st{{animation:none}}.s{keep}{{opacity:1}}"
             f".cur{{animation:none;transform:translateX({xs(ts[keep]) - x0:.1f}px)}}}}")
  out.insert(0, f"<style>{''.join(css)}</style>")
  out.append(f'<g class="cur"><line x1="{x0}" y1="{ly - 4}" x2="{x0}" y2="{yb}" stroke="{INK}" stroke-width="1.4"/></g>')
  yr = yb + 30
  for i, t in enumerate(ts):
    since = max(0.0, t - max([b for b in beats if b <= t], default=t0))
    age = min(k["ticks"], int(round(since * k["f"]))) if t <= t_rev else k["ticks"]
    allowed = t < t_rev
    g = [f'<g class="st s{i}">', rect(16, yr, W - 32, 34, fill=GREEN_BG if allowed else RED_BG, stroke=GREEN if allowed else RED, rx=8),
         text(28, yr + 22, f"t = {t * 1000:+.0f} ms · age {age} ticks · controls_allowed = {1 if allowed else 0}"
              + ("" if allowed else " · siren"), size=11.5, weight=700, fill=GREEN if allowed else RED), "</g>"]
    out += g
  y = yr + 52
  out.append(text(16, y, f"Shaded: the {c['tsr'][0]} budget, detect ≤ {k['detect']:g} s, react ≤ {k['react']:g} s.", size=10,
                  fill=MUTED))
  out.append(text(16, y + 14, "Detection is up to one task period later by design; not", size=10, fill=MUTED))
  out.append(text(16, y + 28, "measured on hardware.", size=10, fill=MUTED))
  extra, y = terms.svg_footer(out, 16, y + 48, W - 32, size=10)
  out += extra
  out.append(text(W - 16, y + 6, "Generated by fig_w00_stories.py", size=10, fill=FAINT, anchor="end"))
  desc = (f"Heartbeat at {k['hb']} Hz stops at t = 0; the {k['f']} Hz safety task counts the age to {k['ticks']} ticks and "
          f"revokes authority at {k['t_th']:g} s ({MACHINE} {c['transition']['id']}), siren for {k['siren']} s; budget detect ≤ "
          f"{k['detect']:g} s, react ≤ {k['react']:g} s")
  return svg(W, int(y + 18), "Figure W-0-4. The safety task in time, animated", desc, out)


def section_md(c: dict, k: dict) -> str:
  fsr_id, tsr_id = c["fsr"][0], c["tsr"][0]
  tests = ", ".join(f"{t['id']} ({t['level']})" for t in c["tests"])
  return "\n".join([
    "## Follow one requirement", "",
    f"![{REQ} followed through the software: it refines {tsr_id} (ASIL {c['tsr'][1]['asil']}), which refines {fsr_id}; it is "
    f"allocated to {c['swsr'][1]['allocated_to']} and realised by its units {', '.join(u['id'] for u in c['units'])}, implemented in panda {c['code']} at "
    f"{c['pin']}, realised by {MACHINE} {c['transition']['id']}, and verified by {tests}]({OUT_R})", "",
    f"*Figure W-0-3. One software safety requirement from the safety requirement it serves to the tests that verify it. "
    f"Every link is read from the records, so the chain breaks the build if one of them changes. Generated by "
    f"[`fig_w00_stories.py`](fig_w00_stories.py).*", "",
    f"Where each link is: [{REQ}](../WP-W-02-software-safety-requirements.md) · "
    f"[{', '.join(u['id'] for u in c['units'])}](../WP-W-05-software-unit-design.md) · "
    f"[{MACHINE} {c['transition']['id']}](../state-machines/README.md) · "
    f"tests in [WP-W-06](../WP-W-06-software-unit-verification.md), [WP-W-07](../WP-W-07-software-integration-verification.md) "
    f"and [WP-W-08](../WP-W-08-embedded-software-testing.md).", "",
    "## The safety task in time", "",
    f"![Animated UML timing diagram: the host's heartbeat at {k['hb']} Hz stops at t = 0; the {k['f']} Hz safety task counts "
    f"the heartbeat age to {k['ticks']} ticks and at {k['t_th']:g} s clears controls_allowed ({MACHINE} "
    f"{c['transition']['id']}) and starts the siren for {k['siren']} s; the {tsr_id} budget, detect ≤ {k['detect']:g} s and "
    f"react ≤ {k['react']:g} s, is shaded]({OUT_T})", "",
    f"*Figure W-0-4. The same requirement in time. A cursor sweeps the second around the loss while the readout gives the "
    f"heartbeat age and the authority. All envelope processing runs in interrupt context, so the {k['f']} Hz task, not the "
    f"main loop, keeps this budget ([WP-W-03 §5](../WP-W-03-software-architecture.md)). Generated by "
    f"[`fig_w00_stories.py`](fig_w00_stories.py).*", ""])


def build() -> dict[str, str]:
  c = chain()
  k = constants(c)
  return {OUT_R: figure_chain(c), OUT_T: figure_timing(c, k), SECTION: section_md(c, k)}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except FigureError as e:
    print(f"fig_w00_stories: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n_ for n_, c_ in outputs.items() if not (HERE / n_).exists() or (HERE / n_).read_text(encoding="utf-8") != c_]
    for n_ in stale:
      print(f"assurance/05-software/figures/{n_} is stale; run fig_w00_stories.py", file=sys.stderr)
    if not stale:
      print(f"fig_w00_stories: {len(outputs)} outputs current")
    return 1 if stale else 0
  for n_, c_ in outputs.items():
    (HERE / n_).write_text(c_, encoding="utf-8")
    print(f"wrote assurance/05-software/figures/{n_}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
