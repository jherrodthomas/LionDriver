#!/usr/bin/env python3
"""Scope plots (Simulink Scope style) of selected back-to-back scenarios: inputs and controls_allowed over time.

Each plot runs one directed scenario of b2b_toy_auth.py through the opendbc safety C (libsafety, reference build)
and the reference model (literal specification, no deviations), records the inputs and both outputs after every
event, and draws them as stacked strips on one time axis. A CSV beside each SVG holds the same samples (the table
view). Where the C and the model differ, both traces show it; that is a recorded finding, not a plotting error.

Needs the opendbc test environment, like b2b_toy_auth.py:
  opendbc_repo/.venv/bin/python assurance/05-software/reference-models/scope_plots.py [--check]
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "scope"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "diagrams"))
import svgkit as K  # noqa: E402

# (file stem, scenario name in b2b_toy_auth.directed(), title, strips, window start ms before the first marked
# event or None for the whole run)
PLOTS = [
  ("scope-d01-engage", "D01 T1 engage, all RX checks passing",
   "T1: engagement on the CRUISE_ACTIVE rising edge, all RX checks passing", ["CRUISE_ACTIVE", "AUTH"]),
  ("scope-d04-cruise-off", "D04 T2 cruise off",
   "T2: CRUISE_ACTIVE falls; authority cleared on the same frame", ["CRUISE_ACTIVE", "AUTH"]),
  ("scope-d05b-brake-held-then-moving", "D05b T3 engaged with brake held at standstill, then moving",
   "T3: brake held at engagement, then the car moves", ["CRUISE_ACTIVE", "BRAKE_PRESSED", "moving", "AUTH"]),
  ("scope-d07-bad-checksum-1d2", "D07 T4 bad checksum on 0x1d2",
   "T4: one 0x1D2 frame with a bad checksum while engaged", ["CRUISE_ACTIVE", "BAD_CKS", "AUTH"]),
  ("scope-d09-0x1d2-timeout", "D09 T5 tick 1 us past the 0x1d2 timeout (151515 us)",
   "T5: 0x1D2 stops; authority cleared at the first tick past 5 periods", ["AGE_1D2", "AUTH"]),
  ("scope-d10-mode-set", "D10 T7 safety mode set while allowed",
   "T7: safety mode set again while engaged; authority cleared, no re-engagement without a new edge",
   ["CRUISE_ACTIVE", "MODE_SET", "AUTH"]),
  ("scope-d11-main-off-150ms", "D11 T10c main off with cruise on, evaluated at 150 ms + 1 us",
   "T10c: MAIN_ON off while cruising; cleared after more than 150 ms", ["CRUISE_ACTIVE", "MAIN_ON", "AUTH"]),
  ("scope-d12-cruise-edge-main-off", "D12 T10c cruise rising edge while main off",
   "T10c: CRUISE_ACTIVE rises while MAIN_ON is off; no engagement", ["MAIN_ON", "CRUISE_ACTIVE", "AUTH"]),
  ("scope-d13-tx-flood-2x", "D13 T11 0x2E4 flood at 2x while allowed",
   "T11: 0x2E4 at twice its rate; revoked on the 3rd rejected frame in a half-window", ["TX_2E4", "AUTH", "TXFLAG"]),
  ("scope-d18-0x2e4-stops", "D18 T10b 0x2e4 stops while allowed (limit 50 ms)",
   "T10b: the SoC stops sending 0x2E4; authority cleared after more than 50 ms", ["TX_2E4", "AUTH"]),
  ("scope-d14-wrong-dlc-brake", "D14 OI-1 brake pressed in a 0x226 frame that fails validation",
   "B2B-01: brake pressed in a wrong-length 0x226 frame (C ignores it; the specification clears)",
   ["BRAKE_PRESSED", "BAD_FRAME", "AUTH"]),
]
STRIP = {  # name: (label, kind, unit)
  "CRUISE_ACTIVE": ("CRUISE_ACTIVE (0x1D2)", "bool", ""),
  "MAIN_ON": ("MAIN_ON (0x1D3)", "bool", ""),
  "BRAKE_PRESSED": ("BRAKE_PRESSED (0x226)", "bool", ""),
  "moving": ("any wheel speed ≠ 0", "bool", ""),
  "AGE_1D2": ("0x1D2 frame age", "num", "ms"),
  "TX_2E4": ("0x2E4 frames sent, per 10 ms", "num", ""),
  "BAD_FRAME": ("wrong-DLC 0x226 frame", "event", ""),
  "BAD_CKS": ("bad-checksum frame", "event", ""),
  "MODE_SET": ("safety mode set", "event", ""),
  "AUTH": ("controls_allowed", "auth", ""),
  "TXFLAG": ("txRateExceeded flag", "auth", ""),
}
THRESH = {"AGE_1D2": (151.515, "timeout 151.5 ms")}


def opendbc_commit() -> str:
  r = subprocess.run(["git", "-C", str(HERE.parents[2] / "opendbc_repo"), "rev-parse", "--short=7", "HEAD"],
                     capture_output=True, text=True)
  return r.stdout.strip() if r.returncode == 0 else "unknown"


def record(name: str) -> list[dict]:
  import b2b_toy_auth as B
  from sm_toy_auth_model import Rx, SetMode, SmToyAuth, Tx
  events = sorted(B.directed(True)[name], key=lambda te: te[0])
  c = B.CSide()
  c.start()
  m = SmToyAuth(True, {})
  sig = {"CRUISE_ACTIVE": 0, "MAIN_ON": 0, "BRAKE_PRESSED": 0, "moving": 0}
  last_1d2 = None
  rows = []
  for t, ev in events:
    m.now = t
    m.step(ev)
    c.apply(t, ev)
    bad = 0
    tx = 0
    cks = int(isinstance(ev, Rx) and not ev.checksum_ok)
    mode = int(isinstance(ev, SetMode))
    if isinstance(ev, Rx) and ev.bus == 0:
      s = ev.signals
      if ev.addr == 0x1D2:
        sig["CRUISE_ACTIVE"] = int(s["CRUISE_ACTIVE"])
        last_1d2 = t
      elif ev.addr == 0x1D3:
        sig["MAIN_ON"] = int(s["MAIN_ON"])
      elif ev.addr == 0x226:
        sig["BRAKE_PRESSED"] = int(s["BRAKE_PRESSED"])
        bad = int(ev.dlc != 8)
      elif ev.addr == 0x0AA:
        sig["moving"] = int(any(s[f"WHEEL_SPEED_{w}_RAW"] != B.STANDING for w in B.WHEELS))
    if isinstance(ev, Tx) and ev.addr == 0x2E4:
      tx = 1
    rows.append({"t_ms": t / 1000, **sig,
                 "AGE_1D2": (t - last_1d2) / 1000 if last_1d2 is not None else 0.0,
                 "TX_2E4": tx, "BAD_FRAME": bad, "BAD_CKS": cks, "MODE_SET": mode,
                 "AUTH_C": int(c.allowed()), "AUTH_M": int(m.allowed),
                 "TXFLAG_C": int(c.tx_rate_flag()), "TXFLAG_M": int(m.tx_rate_exceeded)})
  return rows


def tx_rate(rows: list[dict]) -> list[tuple[float, float]]:
  """0x2E4 frames per 10 ms bin, as a step series."""
  bins: dict[int, int] = {}
  for r in rows:
    if r["TX_2E4"]:
      b = int(r["t_ms"] // 10)
      bins[b] = bins.get(b, 0) + 1
  if not bins:
    return []
  lo, hi = min(bins), max(bins)
  return [(b * 10.0, float(bins.get(b, 0))) for b in range(lo - 1, hi + 2)]


def render(stem: str, title: str, strips: list[str], rows: list[dict]) -> str:
  W, L, R = 920, 190, 120
  t0, t1 = rows[0]["t_ms"], rows[-1]["t_ms"]
  # zoom on the last 600 ms, where every scenario has its action
  t0 = max(t0, t1 - 600.0)
  rows = [r for r in rows if r["t_ms"] >= t0]
  t_end = t1  # last event; the axis runs 8 % further so a change at the last event stays visible
  t1 = t1 + 0.08 * (t1 - t0)
  xw = W - L - R

  def X(t):
    return L + (t - t0) / (t1 - t0) * xw

  body = [K.text(20, 26, title, "th"),
          K.text(20, 44, f"Scope plot of back-to-back scenario \"{stem.split('-', 2)[1].upper()}\" (reference build, "
                 f"opendbc {opendbc_commit()}), generated by reference-models/scope_plots.py from an actual run.", "ts"),
          K.text(20, 58, "C: opendbc safety code via libsafety. Model: reference model, literal specification. "
                 "Data: the CSV beside this file.", "ts")]
  # intervals where the C grants authority, shaded in every strip
  spans, start = [], None
  for r in rows:
    if r["AUTH_C"] and start is None:
      start = r["t_ms"]
    elif not r["AUTH_C"] and start is not None:
      spans.append((start, r["t_ms"]))
      start = None
  if start is not None:
    spans.append((start, t1))
  y = 78
  for name in strips:
    label, kind, unit = STRIP[name]
    h = 56 if kind in ("bool", "auth", "event") else 96
    top, bot = y, y + h
    body.append(f'<rect class="hi" x="{L}" y="{top}" width="{xw}" height="{h}"/>')
    for a, b in spans:
      body.append(f'<rect class="band" x="{X(a):.1f}" y="{top}" width="{X(b) - X(a):.1f}" height="{h}"/>')
    body.append(K.text(L - 10, top + h / 2 + 4, label, "t2", "end"))

    def Y(v, vmax):
      return bot - 8 - (v / vmax) * (h - 16)

    if kind in ("bool", "auth"):
      for v in (0, 1):
        yy = Y(v, 1)
        body.append(f'<line class="grid" x1="{L}" y1="{yy:.1f}" x2="{L + xw}" y2="{yy:.1f}"/>')
        body.append(K.text(L + xw + 6, yy + 4, str(v), "ts"))
    if kind == "bool":
      pts = [(X(r["t_ms"]), Y(r[name], 1)) for r in rows]
      body.append(_step(pts + [(X(t1), pts[-1][1])], "s3"))
    elif kind == "auth":
      key = "AUTH" if name == "AUTH" else "TXFLAG"
      c_pts = [(X(r["t_ms"]), Y(r[f"{key}_C"], 1)) for r in rows]
      m_pts = [(X(r["t_ms"]), Y(r[f"{key}_M"], 1) - 3) for r in rows]  # 3 px offset so equal traces stay visible
      body.append(_step(c_pts + [(X(t1), c_pts[-1][1])], "s1"))
      body.append(_step(m_pts + [(X(t1), m_pts[-1][1])], "s2"))
      body.append(K.text(L + xw + 22, Y(rows[-1][f"{key}_C"], 1) + 4, "C", "t"))
      body.append(K.text(L + xw + 36, Y(rows[-1][f"{key}_M"], 1) + 4, "model", "t"))
    elif kind == "event":
      body.append(f'<line class="grid" x1="{L}" y1="{bot - 8}" x2="{L + xw}" y2="{bot - 8}"/>')
      for r in rows:
        if r[name]:
          x = X(r["t_ms"])
          body.append(f'<path class="m3" d="M{x:.1f},{bot - 10} l-5,-12 l10,0 Z"/>')
          body.append(K.text(x + 8, bot - 16, f"{r['t_ms']:.1f} ms", "ts"))
    else:
      series = tx_rate(rows) if name == "TX_2E4" else [(r["t_ms"], r[name]) for r in rows]
      vmax = max([v for _, v in series] + [THRESH.get(name, (0, ""))[0], 1.0]) * 1.1
      for frac in (0, 0.5, 1):
        yy = Y(vmax / 1.1 * frac, vmax)
        body.append(f'<line class="grid" x1="{L}" y1="{yy:.1f}" x2="{L + xw}" y2="{yy:.1f}"/>')
        body.append(K.text(L + xw + 6, yy + 4, f"{vmax / 1.1 * frac:.0f}{(' ' + unit) if unit else ''}", "ts"))
      if name in THRESH:
        v, lab = THRESH[name]
        yy = Y(v, vmax)
        body.append(f'<line class="axis" x1="{L}" y1="{yy:.1f}" x2="{L + xw}" y2="{yy:.1f}" stroke-dasharray="2 3"/>')
        body.append(K.text(L + 6, yy - 4, lab, "ts"))
      pts = [(X(t), Y(v, vmax)) for t, v in series if t0 <= t <= t_end]
      body.append(_step(pts, "s3"))
    body.append(f'<rect x="{L}" y="{top}" width="{xw}" height="{h}" fill="none" class="axis"/>')
    y = bot + 10
  # time axis
  span = t1 - t0
  step = 100 if span > 400 else 50 if span > 200 else 20
  first = int(t0 // step + 1) * step
  for t in range(first, int(t1) + 1, step):
    x = X(t)
    body.append(f'<line class="axis" x1="{x:.1f}" y1="{y - 10}" x2="{x:.1f}" y2="{y - 4}"/>')
    body.append(K.text(x, y + 8, f"{t}", "ts", "middle"))
  body.append(K.text(L + xw / 2, y + 26, "time since scenario start (ms)", "t2", "middle"))
  # legend
  ly = y + 46
  body += [f'<path class="s3" d="M{L},{ly} L{L + 26},{ly}"/>', K.text(L + 32, ly + 4, "input (stimulus)", "t"),
           f'<path class="s1" d="M{L + 150},{ly} L{L + 176},{ly}"/>', K.text(L + 182, ly + 4, "C (libsafety)", "t"),
           f'<path class="s2" d="M{L + 290},{ly} L{L + 316},{ly}"/>',
           K.text(L + 322, ly + 4, "model (literal specification), drawn 3 px above when equal", "t")]
  ly += 22
  body += [f'<rect class="band" x="{L}" y="{ly - 7}" width="26" height="14"/>',
           K.text(L + 32, ly + 4, "shaded: C grants authority (controls_allowed = 1)", "t")]
  H = int(ly + 22)
  desc = f"{title}. Strips: " + ", ".join(STRIP[s][0] for s in strips) + ". Data in the CSV of the same name."
  return K.doc(W, H, title, desc, body)


def _step(pts, cls):
  if not pts:
    return ""
  d = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
  for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
    d.append(f"L{x1:.1f},{y0:.1f}")
    if y1 != y0:
      d.append(f"L{x1:.1f},{y1:.1f}")
  return f'<path class="{cls}" d="{" ".join(d)}"/>'


def csv_text(rows: list[dict]) -> str:
  keys = list(rows[0])
  lines = [",".join(keys)]
  for r in rows:
    lines.append(",".join(f"{r[k]:.3f}" if isinstance(r[k], float) else str(r[k]) for k in keys))
  return "\n".join(lines) + "\n"


def outputs() -> dict[str, str]:
  out = {}
  for stem, scen, title, strips in PLOTS:
    rows = record(scen)
    out[f"{stem}.svg"] = render(stem, title, strips, rows)
    out[f"{stem}.csv"] = csv_text(rows)
  return out


def main(argv: list[str]) -> int:
  if os.environ.get("LIONDRIVER_REFERENCE") != "1":
    os.environ["LIONDRIVER_REFERENCE"] = "1"
    os.execv(sys.executable, [sys.executable, *argv])
  stale = []
  OUT.mkdir(parents=True, exist_ok=True)
  for name, content in outputs().items():
    path = OUT / name
    if "--check" in argv:
      if not path.exists() or path.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      path.write_text(content, encoding="utf-8")
      print(f"wrote {path.relative_to(HERE.parents[2])}")
  if stale:
    print("FAIL: out of date: " + ", ".join(stale) + "; run scope_plots.py")
    return 1
  if "--check" in argv:
    print("OK: scope plots current")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
