"""SVG and Mermaid views of a back-to-back run (standard library only).

trace_svg     one scenario on a time axis: the stimulus, the RX frames, the host's TX frames, the safety task, the
              model and C authority lines, and a band wherever they differ. The model line is the model run without
              re-alignment, so a band shows how long a difference lasts, not only where it starts.
coverage_svg  every transition of the record between the two states, coloured by what the run found.
coverage_mermaid  the same as a Mermaid flowchart, which GitHub renders.

Colours: neutral blue for "model = C", amber for an expected difference, red for a candidate or unexpected one, grey
dashed for a transition the model cannot execute. Nothing is drawn green: agreement is not a pass.

Drafting origin: ai-assisted (Claude), not reviewed.
"""
from __future__ import annotations

from html import escape as e

AGREE, EXPECTED, CANDIDATE, UNEXPECTED, NOT_EXEC, NOT_HIT = "#3D6B8C", "#B7791F", "#B23A3A", "#7A1F9E", "#9AA5B4", "#5A6778"
STIM, INK, MUTED, GRID, FONT = "#6B4FA0", "#0E1A2B", "#5A6778", "#E7EAF0", "IBM Plex Sans,Helvetica,Arial,sans-serif"
RX_ORDER = ["WHEEL_SPEEDS", "BRAKE_MODULE", "STEER_TORQUE_SENSOR", "EPS_STATUS", "PCM_CRUISE_2", "PCM_CRUISE"]
STATUS = {
  "unexpected": (UNEXPECTED, "unexpected difference"),
  "candidate": (CANDIDATE, "candidate finding"),
  "expected": (EXPECTED, "expected difference (open SWSR)"),
  "agree": (AGREE, "exercised, model = C"),
  "nothit": (NOT_HIT, "executable, not reached by any scenario"),
  "notexec": (NOT_EXEC, "not executed at the libsafety boundary"),
}


# ---------------------------------------------------------------- trace

def _steps(rows, val, x, y_hi, y_lo, t_end, t_start=None):
  pts, prev = [], None
  for r in rows:
    v = val(r)
    if prev is None:
      pts.append(f"{x(r['t'] if t_start is None else t_start):.1f},{y_hi if v else y_lo}")
    elif v != prev:
      pts += [f"{x(r['t']):.1f},{y_hi if prev else y_lo}", f"{x(r['t']):.1f},{y_hi if v else y_lo}"]
    prev = v
  if prev is not None:
    pts.append(f"{x(t_end):.1f},{y_hi if prev else y_lo}")
  return " ".join(pts)


def _bands(rows, t_end):
  out, start = [], None
  for r in rows:
    d = r["m"] != r["c"]
    if d and start is None:
      start = r["t"]
    elif not d and start is not None:
      out.append((start, r["t"]))
      start = None
  if start is not None:
    out.append((start, t_end))
  return out


def trace_svg(result: dict, scenario, t0: int, t1: int, width: int, zoom: bool, band_colour: str) -> str:
  """result: one run_b2b result with "trace"; scenario: the Scenario object (for its changes and stops)."""
  rows = [r for r in result["trace"] if t0 <= r["t"] <= t1]
  if not rows:
    return ""
  left, right = 190, width - 20
  x = lambda t: left + (t - t0) / max(t1 - t0, 1) * (right - left)  # noqa: E731
  body: list[str] = []
  y = 34

  def lane(label: str, h: int, sub: str = "") -> int:
    nonlocal y
    top = y
    body.append(f'<text x="{left - 10}" y="{top + h / 2 + 4:.0f}" text-anchor="end" font-size="12" fill="{INK}">{e(label)}</text>')
    if sub:
      body.append(f'<text x="{left - 10}" y="{top + h / 2 + 17:.0f}" text-anchor="end" font-size="10" fill="{MUTED}">{e(sub)}</text>')
    body.append(f'<line x1="{left}" x2="{right}" y1="{top + h}" y2="{top + h}" stroke="{GRID}"/>')
    y += h
    return top

  y_first = y
  # stimulus: every signal the scenario changes, drawn as a step on its own row
  signals = list(dict.fromkeys(k for _, k, _ in scenario.changes))
  rx_rows = [r for r in rows if r["k"] == "rx"]
  for sig in signals:
    vals = [r["v"].get(sig, 0) for r in rx_rows]
    if not vals:
      continue
    base = vals[0]
    changed = sorted({v for v in vals if v != base}, key=str)
    top = lane(sig, 30, f"{base} → {', '.join(map(str, changed))}" if changed else f"{base}")
    body.append(f'<polyline fill="none" stroke="{STIM}" stroke-width="2" points="'
                + _steps(rx_rows, lambda r, s=sig, b0=base: r["v"].get(s, 0) != b0, x, top + 7, top + 25, t1, t0) + '"/>')
  stops = [(n, a, b) for n, a, b in scenario.stops if b > t0 and a < t1] + \
          [(n + " corrupt", a, b) for n, a, b in scenario.corrupts if b > t0 and a < t1]
  if stops and not zoom:
    top = lane("stopped / corrupt", 26)
    for n, a, b in stops:
      xa, xb = x(max(a, t0)), x(min(b, t1))
      body.append(f'<rect x="{xa:.1f}" y="{top + 6}" width="{max(xb - xa, 2):.1f}" height="14" rx="3" fill="{STIM}" opacity=".18"/>')
      body.append(f'<text x="{xa + 4:.1f}" y="{top + 17}" font-size="10.5" fill="{STIM}">{e(n)}</text>')
  if zoom:
    mode_ts = [r["t"] for r in rows if r["k"] == "mode"]
    for name in RX_ORDER:
      top = lane(name, 20)
      for n, a, b in scenario.stops:
        if n == name and b > t0 and a < t1:
          xa, xb = x(max(a, t0)), x(min(b, t1))
          body.append(f'<rect x="{xa:.1f}" y="{top + 4}" width="{max(xb - xa, 2):.1f}" height="12" fill="{STIM}" opacity=".12"/>')
      for r in rows:
        if r["k"] == "rx" and r["n"] == name:
          first = any(m < r["t"] for m in mode_ts) and not any(
            q["k"] == "rx" and q["n"] == name and max(m for m in mode_ts if m < r["t"]) < q["t"] < r["t"] for q in rows)
          col = CANDIDATE if r["cor"] else ("#1F6FE0" if first else NOT_EXEC)
          body.append(f'<circle cx="{x(r["t"]):.1f}" cy="{top + 10}" r="{5 if first or r["cor"] else 3.5}" fill="{col}"/>')
    top = lane("TX (host)", 20)
    for n, a, b in scenario.stops:
      if n in ("STEERING_LKA", "ACC_CONTROL") and b > t0 and a < t1:
        xa, xb = x(max(a, t0)), x(min(b, t1))
        body.append(f'<rect x="{xa:.1f}" y="{top + 4}" width="{max(xb - xa, 2):.1f}" height="12" fill="{STIM}" opacity=".12"/>' +
                    f'<text x="{xa + 4:.1f}" y="{top + 14}" font-size="10" fill="{STIM}">{e(n)} stopped</text>')
    for r in rows:
      if r["k"] == "tx":
        col = CANDIDATE if not r["ok"] else "#7A8699"
        body.append(f'<rect x="{x(r["t"]) - 2:.1f}" y="{top + 5}" width="4" height="10" fill="{col}"/>')
    top = lane("safety task", 20)
    for r in rows:
      if r["k"] == "tick":
        body.append(f'<line x1="{x(r["t"]):.1f}" x2="{x(r["t"]):.1f}" y1="{top + 4}" y2="{top + 16}" stroke="#7A8699"/>')
  top = lane("Model (record)", 46, "ALLOWED / NOT")
  body.append(f'<polyline fill="none" stroke="{AGREE}" stroke-width="2.5" points="{_steps(rows, lambda r: r["m"], x, top + 10, top + 38, t1, t0)}"/>')
  top = lane("C (libsafety)", 46, "ALLOWED / NOT")
  body.append(f'<polyline fill="none" stroke="{INK}" stroke-width="2.5" points="{_steps(rows, lambda r: r["c"], x, top + 10, top + 38, t1, t0)}"/>')
  top = lane("model fired", 24)
  last_x = -99.0
  for r in rows:
    for f in r["f"]:
      if f == "T8" or x(r["t"]) - last_x < 16:
        continue
      last_x = x(r["t"])
      body.append(f'<text x="{last_x:.1f}" y="{top + 16}" text-anchor="middle" font-size="11" font-weight="600" fill="{AGREE}">{f}</text>')
  height = y + 8
  step = next(s for s in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000) if (t1 - t0) / s <= 12)
  axis = [f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="24" y2="{y}" stroke="#EEF1F5"/>' +
          f'<text x="{x(t):.1f}" y="16" text-anchor="middle" font-size="10.5" fill="{MUTED}">{t} ms</text>'
          for t in range(-(-t0 // step) * step, t1 + 1, step)]
  bands = [f'<rect x="{x(a):.1f}" y="{y_first}" width="{max(x(b) - x(a), 2):.1f}" height="{y - y_first}" fill="{band_colour}" opacity=".09"/>' +
           f'<line x1="{x(a):.1f}" x2="{x(a):.1f}" y1="{y_first}" y2="{y}" stroke="{band_colour}" stroke-width="1.5"/>'
           for a, b in _bands(rows, t1)]
  modes = [f'<line x1="{x(r["t"]):.1f}" x2="{x(r["t"]):.1f}" y1="24" y2="{y}" stroke="{STIM}" stroke-dasharray="5 4" stroke-width="1.5"/>' +
           f'<text x="{x(r["t"]) + 5:.1f}" y="{y_first - 3}" font-size="11" fill="{STIM}">safety mode set</text>'
           for r in rows if r["k"] == "mode"]
  return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" ' +
          f'font-family="{FONT}"><rect width="100%" height="100%" fill="#FFFFFF"/>'
          + "".join(axis) + "".join(bands) + "".join(modes) + "".join(body) + "</svg>")


def trace_legend_html() -> str:
  items = [(f'<line x1="0" x2="26" y1="6" y2="6" stroke="{AGREE}" stroke-width="2.5"/>', "model (record), not re-aligned"),
           (f'<line x1="0" x2="26" y1="6" y2="6" stroke="{INK}" stroke-width="2.5"/>', "C code"),
           (f'<rect width="26" height="12" fill="{CANDIDATE}" opacity=".15"/>', "model and C differ"),
           (f'<line x1="0" x2="26" y1="6" y2="6" stroke="{STIM}" stroke-width="2"/>', "stimulus"),
           ('<circle cx="6" cy="6" r="5" fill="#1F6FE0"/>', "first frame after a mode set"),
           (f'<circle cx="6" cy="6" r="5" fill="{CANDIDATE}"/>', "corrupt RX / over-limit TX")]
  return '<div class="legend">' + "".join(f'<span><svg width="28" height="12">{s}</svg> {e(t)}</span>' for s, t in items) + "</div>"


# ---------------------------------------------------------------- coverage

def transition_status(record: dict, results: list[dict], executed: list[str], known: dict) -> dict[str, tuple[str, str]]:
  """transition id -> (status key, note). A difference outranks agreement; the worst class wins."""
  fired = {f for r in results for f in r["fired"]}
  rank = list(STATUS)
  key = {t["id"]: ("agree" if t["id"] in fired else "nothit") if t["id"] in executed else "notexec" for t in record["transitions"]}
  notes: dict[str, set] = {tid: set() for tid in key}
  for r in results:
    for d in r["divergences"]:
      if d["class"] == "known":
        tid, k, note = known[(r["scenario"], r["build"], d["cause"])][1], "candidate", f"{d['id']} ({r['scenario']})"
      else:
        tid = d["cause"].split(",")[0]
        k, note = ("expected", f"open SWSR ({r['scenario']})") if d["class"] == "expected" else ("unexpected", r["scenario"])
      if tid not in key:
        continue
      if rank.index(k) < rank.index(key[tid]):
        key[tid], notes[tid] = k, set()
      if k == key[tid]:
        notes[tid].add(note)
  return {tid: (key[tid], ", ".join(sorted(notes[tid]))) for tid in key}


def coverage_svg(record: dict, status: dict, labels: dict[str, str]) -> str:
  grant = [t for t in record["transitions"] if t["to"] == "ALLOWED"]
  revoke = [t for t in record["transitions"] if t["to"] != "ALLOWED" and t["id"] != "T8"]
  width, rowh, top = 1000, 30, 50
  height = top + (len(grant) + len(revoke)) * rowh + 40
  bx1, bx2, bw = 30, width - 180, 150
  s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="{FONT}">' +
       '<rect width="100%" height="100%" fill="#FFFFFF"/><defs>']
  s += [f'<marker id="m{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">' +
        f'<path d="M0,0L10,5L0,10z" fill="{c}"/></marker>' for k, (c, _) in STATUS.items()]
  s.append("</defs>")
  for bx, name, sub in ((bx1, "NOT_ALLOWED", "initial"), (bx2, "ALLOWED", "")):
    s.append(f'<rect x="{bx}" y="{top - 24}" width="{bw}" height="{height - top}" rx="10" fill="#EEF2F8" stroke="#7A8699"/>' +
             f'<text x="{bx + bw / 2}" y="{height / 2}" text-anchor="middle" font-weight="600" font-size="14" fill="{INK}">{name}</text>' +
             f'<text x="{bx + bw / 2}" y="{height / 2 + 18}" text-anchor="middle" font-size="11" fill="{MUTED}">{sub}</text>')
  y = top
  for t, (x1, x2) in [(t, (bx1 + bw, bx2)) for t in grant] + [(t, (bx2, bx1 + bw)) for t in revoke]:
    key, note = status[t["id"]]
    col = STATUS[key][0]
    dash = ' stroke-dasharray="6 5"' if key in ("notexec", "nothit") else ""
    wide = 2.6 if key in ("candidate", "expected", "unexpected") else 1.8
    s.append(f'<line x1="{x1}" x2="{x2}" y1="{y}" y2="{y}" stroke="{col}" stroke-width="{wide}"{dash} marker-end="url(#m{key})"/>')
    build = f' <tspan fill="{MUTED}">· {t.get("build")}</tspan>' if t.get("build", "all") != "all" else ""
    extra = f' <tspan fill="{col}" font-weight="600">— {e(note)}</tspan>' if note else ""
    s.append(f'<text x="{(x1 + x2) / 2}" y="{y - 6}" text-anchor="middle" font-size="11.5" fill="{INK}">' +
             f'<tspan font-weight="700" fill="{col}">{t["id"]}</tspan> {e(labels.get(t["id"], t["event"]))}{build}{extra}</text>')
    y += rowh
  s.append("</svg>")
  return "".join(s)


def coverage_mermaid(record: dict, status: dict, labels: dict[str, str]) -> str:
  lines = ["```mermaid", "flowchart LR", "  NA([NOT_ALLOWED])", "  AL([ALLOWED])"]
  styles = []
  for i, t in enumerate(x for x in record["transitions"] if x["id"] != "T8"):
    key, note = status[t["id"]]
    label = f'{t["id"]} {labels.get(t["id"], "")}' + (f" — {note}" if note else "")
    label = label.replace('"', "'")
    src, dst = ("NA", "AL") if t["to"] == "ALLOWED" else ("AL", "NA")
    arrow = "-.->" if key in ("notexec", "nothit") else "-->"
    lines.append(f'  {src} {arrow}|"{label}"| {dst}')
    styles.append(f"  linkStyle {i} stroke:{STATUS[key][0]},stroke-width:{3 if key in ('candidate', 'expected', 'unexpected') else 1.5}px")
  return "\n".join(lines + styles + ["```"])
