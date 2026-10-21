#!/usr/bin/env python3
"""Two views of each FMEDA (assurance/08-analyses/fmea/analyses/fmeda-*.yaml) for the review pages, and a live worksheet.

  exports/review/fmeda-views/<name>-cards.svg   phone cards: per goal group, SPFM and LFM against the ASIL targets,
                                                the λ tiles, and the failure modes that cost SPFM points, largest first
  exports/review/fmeda-views/<name>-sheet.svg   the worksheet as a spreadsheet: a group row per component, a row per
                                                failure mode with its class, mechanism, DC and λ split, and the totals
  live worksheet page                           the same worksheet for every FMEDA file, with a goal switch, filters,
                                                search and every field of a row; a private claude.ai page (WORKSHEET_URL)

The class and the λ split of each row follow fmea_lint.fmeda_metrics (rating-tables §6.1, per-goal classification), and
the build fails if the rows do not add up to its metrics. The published page has to follow the YAML, as for
tools/xlsx_viewer.py: fmeda_views.sha256 holds a fingerprint of the page as last built, and --check fails when it no
longer matches a fresh build; the fix is to rebuild with --html and republish to WORKSHEET_URL.

Usage:
  tools/safety/fmeda_views.py                     write the SVGs
  tools/safety/fmeda_views.py --html <file.html>  also write the live page and its fingerprint; then republish it
  tools/safety/fmeda_views.py --check             fail if an SVG or the page's fingerprint is stale
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_fmeda_xlsx  # noqa: E402
import fmea_lint  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FMEA = ROOT / "assurance/08-analyses/fmea"
ANALYSES = FMEA / "analyses"
FIGS = FMEA / "exports/review/fmeda-views"
SOURCES = export_fmeda_xlsx.SOURCES
FINGERPRINT = Path(__file__).with_name("fmeda_views.sha256")
WORKSHEET_URL = "https://claude.ai/artifact/PCbGoJH1mrjZGDmEzegu7N"
GENERATOR = "tools/safety/fmeda_views.py"
W = 640


def load(name: str) -> dict:
  return fmea_lint.load_yaml((ANALYSES / f"{name}.yaml").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- arithmetic

def split(doc: dict, goal: str | None) -> list[dict]:
  """One entry per failure mode of a safety-related component, classified for `goal`: class SPF, RF, MPF or safe, the
  mechanism and DC that apply, and the λ parts in FIT. The same rules as fmea_lint.fmeda_metrics."""
  out = []
  for comp in doc["components"]:
    if not comp["safety_related"]:
      continue
    lam = comp["failure_rate_fit"]
    for row in comp["failure_modes"]:
      fm = fmea_lint.fmeda_mode(row, goal)
      lfm = lam * fm["distribution"]
      e = {"comp": comp["id"], "id": row["id"], "mode": row["mode"], "lam": lfm, "dist": fm["distribution"],
           "sm": "", "dc": None, "spf": 0.0, "rf": 0.0, "lat": 0.0, "det": 0.0, "safe": 0.0,
           "other_goal": goal is not None and any(p["goal"] == goal for p in row.get("per_goal", []))}
      if fm["violates_sg_directly"]:
        dc = fm.get("dc_spf", 0.0) if fm.get("safety_mechanism_spf") else 0.0
        e["sm"], e["dc"] = (fm.get("safety_mechanism_spf") or ""), (dc if fm.get("safety_mechanism_spf") else None)
        if dc == 0.0:
          e["cls"], e["spf"] = "SPF", lfm
        else:
          e["cls"], e["rf"], e["det"] = "RF", lfm * (1 - dc), lfm * dc
      elif fm["mpf_potential"]:
        dc = fm.get("dc_lf", 0.0) if fm.get("safety_mechanism_lf") else 0.0
        e["sm"], e["dc"] = (fm.get("safety_mechanism_lf") or ""), (dc if fm.get("safety_mechanism_lf") else None)
        e["cls"], e["lat"], e["det"] = "MPF", lfm * (1 - dc), lfm * dc
      else:
        e["cls"], e["safe"] = "safe", lfm
      out.append(e)
  return out


def problems(doc: dict, goal: str | None) -> list[str]:
  m = fmea_lint.fmeda_metrics(doc, goal or None)
  rows = split(doc, goal or None)
  sums = {"spf_fit": sum(r["spf"] for r in rows), "rf_fit": sum(r["rf"] for r in rows),
          "mpf_latent_fit": sum(r["lat"] for r in rows), "total_fit": sum(r["lam"] for r in rows)}
  return [f"{doc['analysis']['title']} {goal}: rows add up to {k} {v:.6g}, fmea_lint has {m[k]:.6g}"
          for k, v in sums.items() if abs(v - m[k]) > 1e-9]


def groups(doc: dict) -> list[dict]:
  """Goals with identical metrics share a card: [{goals: [(goal, asil, alongside)], m: metrics}] in target order."""
  out = []
  for goal, asil, along in export_fmeda_xlsx.target_rows(doc):
    m = fmea_lint.fmeda_metrics(doc, goal or None)
    key = (round(m["spfm"], 12), round(m["lfm"], 12), round(m["pmhf_spf_rf_fit"], 12))
    g = next((g for g in out if g["key"] == key), None)
    if g is None:
      out.append(g := {"key": key, "goals": [], "m": m, "goal": goal or None})
    g["goals"].append((goal, asil, along))
  return out


def verdicts(g: dict) -> list[tuple[str, list[str]]]:
  """[(ASIL, [missed metric names])] for the ASILs on a card, strictest first."""
  out = []
  for a in sorted({asil for _g, asil, _al in g["goals"]}, reverse=True):
    s, lt, p = fmea_lint.FMEDA_TARGETS[a]
    m = g["m"]
    out.append((a, [n for n, bad in (("SPFM", m["spfm"] < s), ("LFM", m["lfm"] < lt), ("λSPF+λRF", m["pmhf_spf_rf_fit"] >= p)) if bad]))
  return out


# ---------------------------------------------------------------- SVG helpers

STYLE = """<style>
svg { --bg:#ffffff; --ink:#16202b; --ink2:#5b6876; --line:#d5dbe2; --head:#e8ecf1; --card:#f4f6f8; --track:#e3e8ed;
      --bad:#c2412f; --bad-bg:#fbe9e6; --amb:#a86200; --amb-bg:#fdf1dc; --ok:#1d7a46; --ok-bg:#e3f3e9; --sel:#1f5fa8; }
@media (prefers-color-scheme: dark) {
  svg { --bg:#161d25; --ink:#e4eaf0; --ink2:#94a2b1; --line:#2a3440; --head:#1c252f; --card:#1b232c; --track:#26313c;
        --bad:#ff8f86; --bad-bg:#431b19; --amb:#f0b453; --amb-bg:#3a2c12; --ok:#79d6a0; --ok-bg:#173527; --sel:#7fb0ec; }
}
.bg { fill:var(--bg); } .card { fill:var(--card); stroke:var(--line); stroke-width:1; } .tile { fill:var(--bg); stroke:var(--line); }
.h { font:600 20px 'IBM Plex Sans Condensed','Arial Narrow',system-ui,sans-serif; fill:var(--ink); }
.hc { font:600 16px 'IBM Plex Sans Condensed','Arial Narrow',system-ui,sans-serif; fill:var(--ink); }
.t { font:14px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.tb { font:600 14px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.big { font:600 19px 'IBM Plex Mono',ui-monospace,Menlo,monospace; fill:var(--ink); }
.t2 { font:12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); }
.t2b { font:600 12px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink2); letter-spacing:.04em; }
.m { font:11px 'IBM Plex Mono',ui-monospace,Menlo,monospace; fill:var(--ink); }
.mh { font:600 11px 'IBM Plex Mono',ui-monospace,Menlo,monospace; fill:var(--ink2); }
.mg { font:600 11.5px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--ink); }
.warn { font:600 13px -apple-system,'Segoe UI',Helvetica,Arial,sans-serif; fill:var(--bad); }
.f-bad { fill:var(--bad); } .f-amb { fill:var(--amb); } .f-ok { fill:var(--ok); } .f-ink2 { fill:var(--ink2); }
.b-bad { fill:var(--bad-bg); } .b-amb { fill:var(--amb-bg); } .b-ok { fill:var(--ok-bg); } .b-head { fill:var(--head); }
.track { fill:var(--track); } .grid { stroke:var(--line); stroke-width:1; } .tick { stroke:var(--ink); stroke-width:2; }
.tickb { stroke:var(--ink2); stroke-width:2; stroke-dasharray:3 2; }
</style>"""
CHAR = {"t": 0.5, "tb": 0.54, "t2": 0.5, "m": 0.61, "mg": 0.52, "h": 0.5, "hc": 0.5, "warn": 0.52}
SIZE = {"t": 14, "tb": 14, "t2": 12, "m": 11, "mg": 11.5, "h": 20, "hc": 16, "warn": 13}


def f1(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def T(x, y, s, cls="t", anchor="", extra="") -> str:
  a = f' text-anchor="{anchor}"' if anchor else ""
  return f'<text x="{f1(x)}" y="{f1(y)}" class="{cls}"{a}{extra}>{escape(str(s))}</text>'


def Rc(x, y, w, h, cls, rx=0) -> str:
  return f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}" rx="{rx}" class="{cls}"/>'


def wrap(s: str, w: float, cls="t") -> list[str]:
  out, cur = [], ""
  for word in str(s).split():
    nxt = f"{cur} {word}".strip()
    if cur and len(nxt) * CHAR[cls] * SIZE[cls] > w:
      out.append(cur)
      cur = word
    else:
      cur = nxt
  return out + ([cur] if cur else [])


def fit_text(s: str, w: float, cls: str) -> str:
  n = int(w / (CHAR[cls] * SIZE[cls]))
  return s if len(s) <= n else s[:max(1, n - 1)].rstrip() + "…"


def svg(h: float, title: str, desc: str, body: list[str]) -> str:
  return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{int(h)}" viewBox="0 0 {W} {int(h)}" '
                    'role="img" aria-labelledby="t d">', f'<title id="t">{escape(title)}</title>',
                    f'<desc id="d">{escape(desc)}</desc>', STYLE, f'<rect class="bg" width="{W}" height="{int(h)}"/>', *body,
                    "</svg>"]) + "\n"


def goal_label(goals: list[tuple[str, str, bool]]) -> str:
  by: dict[str, list[str]] = {}
  for g, a, along in goals:
    if not along:
      by.setdefault(a, []).append(g)
  return " · ".join(f"{', '.join(gs)} (ASIL {a})" for a, gs in sorted(by.items(), key=lambda kv: kv[0], reverse=True))


def header(doc: dict, name: str, view: str) -> tuple[list[str], float]:
  a = doc["analysis"]
  generic = sum(1 for c in doc["components"] if c.get("rate_kind", "generic") == "generic")
  b = [T(16, 32, f"FMEDA {a['safety_goal']} · {view}", "h"),
       T(16, 52, f"{name}.yaml rev {a['revision']} · {a['baseline']} · {a['status']} · generated by {GENERATOR}", "t2"),
       T(16, 72, f"Estimate: {generic} of {len(doc['components'])} failure rates generic. Not evidence that a target is met.", "warn")]
  return b, 86


# ---------------------------------------------------------------- cards

def floor_of(v: float, lo: float) -> float:
  """The bar's left end: lo, or the tenth below the value when the value is lower."""
  return min(lo, int(v * 10) / 10)


def bar(x, y, w, v, tC, tB, lo, label) -> list[str]:
  P = lambda t: x + max(0.0, min(1.0, (t - lo) / (1 - lo))) * w  # noqa: E731
  cls = "f-ok" if v >= tC else ("f-amb" if v >= tB else "f-bad")
  out = [T(x, y, label, "tb"), T(x + w, y, f"{v * 100:.2f} %", "tb", "end", f' style="fill:var(--{cls[2:]})"'),
         Rc(x, y + 8, w, 12, "track", 6), Rc(x, y + 8, P(v) - x, 12, cls, 6)]
  for t, a, c in ((tB, "B", "tickb"), (tC, "C", "tick")):
    out += [f'<line x1="{f1(P(t))}" y1="{f1(y + 4)}" x2="{f1(P(t))}" y2="{f1(y + 24)}" class="{c}"/>',
            T(P(t), y + 37, f"{a} {t * 100:.0f}", "t2", "middle")]
  out.append(T(x, y + 37, f"{lo * 100:.0f} %", "t2"))
  return out


def fig_cards(name: str, doc: dict) -> str:
  b, y = header(doc, name, "metrics per goal")
  desc = [f"FMEDA {name} rev {doc['analysis']['revision']}, metrics per goal on generic failure rates (an estimate, not evidence)."]
  for g in groups(doc):
    m, top_asil = g["m"], max(a for _g, a, _al in g["goals"])
    vs = verdicts(g)
    rows = sorted([r for r in split(doc, g["goal"]) if r["spf"] + r["rf"] > 0], key=lambda r: -(r["spf"] + r["rf"]))
    y0 = y + 12
    lab = wrap(goal_label(g["goals"]), W - 32 - 28, "hc")
    inner = [T(30, y0 + 24 + 20 * i, ln, "hc") for i, ln in enumerate(lab)]
    yy = y0 + 24 + 20 * len(lab) - 4
    cx = 30
    for a, miss in vs:
      s = f"ASIL {a}: " + (f"missed on {', '.join(miss)}" if miss else "met on this estimate")
      w = len(s) * 0.55 * 12 + 18
      if cx + w > W - 30:
        cx, yy = 30, yy + 26
      inner += [Rc(cx, yy, w, 20, "b-bad" if miss else "b-ok", 10),
                T(cx + w / 2, yy + 14, s, "t2b", "middle", f' style="fill:var(--{"bad" if miss else "ok"})"')]
      cx += w + 8
    yy += 46
    sT, lT, pT = fmea_lint.FMEDA_TARGETS[top_asil]
    sB, lB, _ = fmea_lint.FMEDA_TARGETS["B"]
    inner += bar(30, yy, W - 60, m["spfm"], sT if top_asil != "B" else sB, sB, floor_of(m["spfm"], 0.8), "SPFM · single-point fault metric")
    yy += 62
    inner += bar(30, yy, W - 60, m["lfm"], lT if top_asil != "B" else lB, lB, floor_of(m["lfm"], 0.5), "LFM · latent fault metric")
    yy += 52
    tw = (W - 60 - 16) / 3
    for i, (lab_, val, sub) in enumerate((("λ safety-related", f"{m['total_fit']:.1f} FIT", ""),
                                          ("λSPF + λRF", f"{m['pmhf_spf_rf_fit']:.2f} FIT", f"ASIL {top_asil} needs < {pT:g}"),
                                          ("λ latent", f"{m['mpf_latent_fit']:.1f} FIT", ""))):
      tx = 30 + i * (tw + 8)
      inner += [Rc(tx, yy, tw, 62, "tile", 6), T(tx + 10, yy + 18, lab_, "t2"), T(tx + 10, yy + 42, val, "big")]
      if sub:
        inner.append(T(tx + 10, yy + 56, sub, "t2"))
    yy += 76
    b.append(Rc(16, y0, W - 32, yy - y0, "card", 10))
    b += inner
    y = yy + 8
    b.append(T(16, y + 14, "WHERE THE SPFM POINTS GO (largest first)", "t2b"))
    y += 24
    for r in rows:
      pts = (r["spf"] + r["rf"]) / m["total_fit"] * 100
      how = ("single-point, no mechanism" if r["cls"] == "SPF" else
             f"residual after {r['sm'].replace('FMD-', '')} (DC {r['dc'] * 100:.0f} %)")
      if r["other_goal"]:
        how += f" · classified for {g['goal']}"
      ml = wrap(r["mode"], W - 32 - 90 - 80, "t")
      sl = wrap(f"{r['comp']} · {how}", W - 32 - 90 - 80, "t2")
      h = 18 * len(ml) + 15 * len(sl) + 12
      b += [T(16, y + 20, r["id"], "tb"),
            *(T(106, y + 20 + 18 * i, ln, "t") for i, ln in enumerate(ml)),
            *(T(106, y + 18 + 18 * len(ml) + 15 * i, ln, "t2") for i, ln in enumerate(sl)),
            T(W - 16, y + 20, f"−{pts:.2f} pt", "tb", "end", ' style="fill:var(--bad)"'),
            T(W - 16, y + 36, f"{r['spf'] + r['rf']:.2f} FIT", "t2", "end"),
            f'<line x1="16" y1="{f1(y + h)}" x2="{W - 16}" y2="{f1(y + h)}" class="grid"/>']
      y += h
    y += 14
    desc.append(f"{goal_label(g['goals'])}: SPFM {m['spfm'] * 100:.2f} %, LFM {m['lfm'] * 100:.2f} %, λSPF+λRF "
                f"{m['pmhf_spf_rf_fit']:.2f} FIT, λ latent {m['mpf_latent_fit']:.1f} FIT of {m['total_fit']:.1f} FIT; " +
                "; ".join(f"ASIL {a} " + (f"missed on {', '.join(ms)}" if ms else "met") for a, ms in vs) +
                ". SPFM lost to: " + ", ".join(f"{r['id']} {(r['spf'] + r['rf']) / m['total_fit'] * 100:.2f} pt" for r in rows) + ".")
  b.append(T(16, y + 4, "The live worksheet has every row, per goal, with filters and the full notes.", "t2"))
  return svg(y + 18, f"FMEDA {name}: metrics per goal", " ".join(desc), b)


# ---------------------------------------------------------------- sheet

COLS = [("", 24), ("ID", 64), ("Failure mode", 150), ("λ FIT", 44), ("Dist", 36), ("Class", 42), ("SM", 54), ("DC", 36),
        ("λSPF", 44), ("λRF", 42), ("λlat", 44)]
CLS_STYLE = {"SPF": ("b-bad", "bad"), "RF": ("b-bad", "bad"), "MPF": ("b-amb", "amb"), "safe": ("b-ok", "ok")}


def num(v: float) -> str:
  return "" if v == 0 else f"{v:.2f}"


def fig_sheet(name: str, doc: dict) -> str:
  goal = groups(doc)[0]["goal"]
  rows = split(doc, goal)
  m = fmea_lint.fmeda_metrics(doc, goal)
  b, y = header(doc, name, "worksheet")
  b.append(T(16, y + 10, f"Classified for {goal or doc['analysis']['safety_goal']}; the live worksheet switches goal. "
                         "Edits go in the YAML, never in a sheet.", "t2"))
  y += 22
  x0 = [16]
  for _c, w in COLS:
    x0.append(x0[-1] + w)
  RH = 20
  letters = " ABCDEFGHIJ"

  def row_cells(yy, vals, cls="m", fills=None, anchors=None, colors=None):
    out = []
    for i, v in enumerate(vals):
      if fills and fills[i]:
        out.append(Rc(x0[i] + 1, yy + 1, COLS[i][1] - 1, RH - 1, fills[i]))
      if v == "":
        continue
      w = COLS[i][1] - 8
      anchor = (anchors or {}).get(i, "end" if i >= 3 and i != 5 and i != 6 else ("middle" if i == 5 else ""))
      tx = x0[i] + 4 if not anchor else (x0[i + 1] - 4 if anchor == "end" else (x0[i] + x0[i + 1]) / 2)
      c = cls[i] if isinstance(cls, list) else cls
      st = f' style="fill:var(--{colors[i]});font-weight:600"' if colors and colors[i] else ""
      out.append(T(tx, yy + 14, fit_text(str(v), w, "m"), c, anchor, st))
    return out

  top = y
  b.append(Rc(16, y, x0[-1] - 16, RH, "b-head"))
  b += row_cells(y, [""] + [letters[i] for i in range(1, len(COLS))], "mh", anchors={i: "middle" for i in range(len(COLS))})
  y += RH
  b.append(Rc(16, y, x0[-1] - 16, RH, "b-head"))
  b += row_cells(y, ["1"] + [c for c, _ in COLS[1:]], "mh", anchors={i: "middle" for i in range(len(COLS))})
  y += RH
  rn, cur = 2, None
  comps = {c["id"]: c for c in doc["components"]}
  for r in rows:
    if r["comp"] != cur:
      cur = r["comp"]
      c = comps[cur]
      b += [Rc(16, y, x0[-1] - 16, RH, "card"), T(x0[0] + 12, y + 14, str(rn), "mh", "middle"),
            T(x0[1] + 4, y + 14, fit_text(f"{cur} · {c['part']}", x0[3] - x0[1] - 8, "mg"), "mg"),
            T(x0[4] - 4, y + 14, f"{c['failure_rate_fit']:g}", "mg", "end")]
      y += RH
      rn += 1
    fill, col = CLS_STYLE[r["cls"]]
    vals = [str(rn), r["id"] + (" *" if r["other_goal"] else ""), r["mode"], f"{r['lam']:.2f}", f"{r['dist']:g}", r["cls"],
            r["sm"].replace("FMD-", ""), "" if r["dc"] is None else f"{r['dc'] * 100:.0f}%",
            num(r["spf"]), num(r["rf"]), num(r["lat"])]
    cls = ["mh"] + ["m"] * 10
    b += row_cells(y, vals, cls, fills=[None] * 5 + [fill] + [None] * 5,
                   colors=[None] * 5 + [col, None, None, "bad", "bad", "amb"])
    y += RH
    rn += 1
  b.append(Rc(16, y, x0[-1] - 16, RH, "b-head"))
  b += row_cells(y, [str(rn), "Σ", "safety-related", f"{m['total_fit']:.1f}", "", "", "", "",
                     f"{m['spf_fit']:.2f}", f"{m['rf_fit']:.2f}", f"{m['mpf_latent_fit']:.2f}"], "mh")
  y += RH
  b.append(Rc(16, y, x0[-1] - 16, RH, "b-head"))
  tgt = [(a, fmea_lint.FMEDA_TARGETS[a]) for a in sorted({a for _g, a, _al in export_fmeda_xlsx.target_rows(doc)
                                                         if _g == (goal or "")} or {doc["analysis"]["asil_target"]})]
  sT = " / ".join(f"{a} ≥ {t[0] * 100:.0f}" for a, t in tgt)
  lT = " / ".join(f"{a} ≥ {t[1] * 100:.0f}" for a, t in tgt)
  b += [T(x0[0] + 12, y + 14, str(rn + 1), "mh", "middle"),
        T(x0[1] + 4, y + 14, f"SPFM {m['spfm'] * 100:.2f} % ({sT}) · LFM {m['lfm'] * 100:.2f} % ({lT})", "mh")]
  y += RH
  for x in x0:
    b.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{f1(y)}" class="grid"/>')
  for yy in range(int(top), int(y) + 1, RH):
    b.append(f'<line x1="16" y1="{yy}" x2="{x0[-1]}" y2="{yy}" class="grid"/>')
  for ln in wrap("SPF single-point · RF residual after a mechanism · MPF multiple-point (λlat its latent part) · safe · "
                 "* classified for this goal by a per-goal entry.", W - 32, "t2"):
    y += 16
    b.append(T(16, y, ln, "t2"))
  desc = (f"FMEDA {name} worksheet classified for {goal}: {len(rows)} failure modes of "
          f"{len({r['comp'] for r in rows})} components; " +
          "; ".join(f"{r['id']} {r['cls']} {r['lam']:.2f} FIT" + (f", {r['sm']} DC {r['dc'] * 100:.0f} %" if r["dc"] is not None else "")
                    for r in rows) +
          f". Totals: λ {m['total_fit']:.1f} FIT, λSPF {m['spf_fit']:.2f}, λRF {m['rf_fit']:.2f}, λ latent "
          f"{m['mpf_latent_fit']:.2f}; SPFM {m['spfm'] * 100:.2f} %, LFM {m['lfm'] * 100:.2f} %.")
  return svg(y + 14, f"FMEDA {name}: worksheet", desc, b)


# ---------------------------------------------------------------- live page

def page_data() -> dict:
  files = {}
  for n in SOURCES:
    doc = load(n)
    a = doc["analysis"]
    targets = []
    for goal, asil, along in export_fmeda_xlsx.target_rows(doc):
      if along:
        targets[-1]["also"].append(asil)
      else:
        targets.append({"goal": goal or a["safety_goal"], "asil": asil, "also": []})
    comps = [{"id": c["id"], "part": c["part"], "lam": c["failure_rate_fit"], "sr": c["safety_related"],
              "kind": c.get("rate_kind", "generic"), "source": c.get("failure_rate_source", ""), "dfmea": c.get("dfmea_element", ""),
              "rows": [{"id": fm["id"], "mode": fm["mode"], "dist": fm["distribution"], "vd": fm["violates_sg_directly"],
                        "mpf": fm["mpf_potential"], "smS": fm.get("safety_mechanism_spf"), "dcS": fm.get("dc_spf", 0.0),
                        "smL": fm.get("safety_mechanism_lf"), "dcL": fm.get("dc_lf", 0.0), "dfmea": fm.get("dfmea_ref", ""),
                        "notes": " ".join(str(fm.get("notes", "")).split()),
                        "pg": [{k: v for k, v in p.items()} for p in fm.get("per_goal", [])]} for fm in c["failure_modes"]]}
             for c in doc["components"]]
    files[n] = {"title": a["title"], "revision": a["revision"], "baseline": a["baseline"], "status": a["status"],
                "updated": a.get("updated", ""), "goal": a["safety_goal"], "targets": targets, "components": comps,
                "sms": {s["id"]: s["description"] for s in doc["safety_mechanisms"]},
                "generic": sum(1 for c in doc["components"] if c.get("rate_kind", "generic") == "generic")}
  return {"files": files, "targets": {k: list(v) for k, v in fmea_lint.FMEDA_TARGETS.items()}}


def build_page() -> str:
  tpl = (Path(__file__).with_name("fmeda_views_page.html")).read_text(encoding="utf-8")
  data = json.dumps(page_data(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
  return tpl.replace("__DATA__", data)


def fingerprint(page: str) -> str:
  return hashlib.sha256(page.encode()).hexdigest()


# ---------------------------------------------------------------- build and check

def build() -> tuple[dict[Path, str], list[str]]:
  out, errs = {}, []
  for n in SOURCES:
    doc = load(n)
    for goal, _a, _al in export_fmeda_xlsx.target_rows(doc):
      errs += problems(doc, goal or None)
    out[FIGS / f"{n}-cards.svg"] = fig_cards(n, doc)
    out[FIGS / f"{n}-sheet.svg"] = fig_sheet(n, doc)
  return out, errs


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--check", action="store_true")
  ap.add_argument("--html", help="also write the live worksheet page here and update the fingerprint")
  args = ap.parse_args(argv)
  out, errs = build()
  page = build_page()
  if args.check:
    errs += [f"stale: {p.relative_to(ROOT)}; run {GENERATOR}" for p, t in out.items()
             if not p.is_file() or p.read_text(encoding="utf-8") != t]
    stored = FINGERPRINT.read_text(encoding="utf-8").split()[0] if FINGERPRINT.exists() else ""
    if stored != fingerprint(page):
      errs.append(f"the live worksheet is out of date; run {GENERATOR} --html <scratch>/fmeda-worksheet.html and republish "
                  f"it to {WORKSHEET_URL}")
    for e in errs:
      print(e, file=sys.stderr)
    if not errs:
      print(f"fmeda_views: {len(out)} figures and the live worksheet current")
    return 1 if errs else 0
  for e in errs:
    print(f"error: {e}", file=sys.stderr)
  if errs:
    return 1
  for p, t in out.items():
    p.write_text(t, encoding="utf-8")
  print(f"fmeda_views: wrote {len(out)} figures")
  if args.html:
    Path(args.html).write_text(page, encoding="utf-8")
    FINGERPRINT.write_text(f"{fingerprint(page)}  published at {WORKSHEET_URL}\n", encoding="utf-8")
    print(f"fmeda_views: wrote {args.html}; republish it to {WORKSHEET_URL}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
