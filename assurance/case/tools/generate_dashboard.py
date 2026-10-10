#!/usr/bin/env python3
"""Generate the Living Safety Case dashboard from the records in assurance/case.

Outputs (all deterministic, no timestamps):
  assurance/case/status.json                       machine-readable summary
  docs/assets/liondriver/assurance/dashboard.svg   metrics card shown in the README
  docs/assets/liondriver/assurance/lifecycle.svg   lifecycle-area status card
  docs/assets/liondriver/assurance/ecosystem.svg   vehicle classification card
  README.md, between the assurance-summary markers  the same figures as text

Usage:
  python3 assurance/case/tools/generate_dashboard.py           # write the outputs
  python3 assurance/case/tools/generate_dashboard.py --check   # fail if any output is out of date

The records are validated first; invalid records produce no output.
"""
from __future__ import annotations

import json
import re
import sys
from html import escape
from pathlib import Path

from caselib import CASE_DIR, REPO_ROOT, load_case, summarize, validate

ASSET_DIR = REPO_ROOT / "docs" / "assets" / "liondriver" / "assurance"
STATUS_JSON = CASE_DIR / "status.json"
README = REPO_ROOT / "README.md"
BEGIN = "<!-- BEGIN GENERATED: assurance-summary (assurance/case/tools/generate_dashboard.py) -->"
END = "<!-- END GENERATED: assurance-summary -->"

FONT = "Inter, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
C = {
  "bg0": "#070D1A", "bg1": "#0E1A31", "panel": "#111E37", "line": "#24345A",
  "gold": "#E2B85C", "gold_hi": "#F6DC97", "gold_lo": "#A97A2A",
  "blue": "#4EA8FF", "white": "#F4F6FA", "muted": "#93A1BC", "dim": "#5F6E8C",
  "green": "#43D19A", "red": "#F2647A",
}
STATUS_COLOR = {
  "Not Started": C["dim"], "In Progress": C["blue"], "Review Required": C["gold"],
  "Accepted for Defined Baseline": C["green"], "Blocked": C["red"],
}
STATE_COLOR = {"Development": C["blue"], "Under Review": C["gold"], "Evidence Supported": C["green"]}


def _defs(uid: str) -> str:
  return f"""<defs>
    <linearGradient id="{uid}-bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{C['bg1']}"/><stop offset="1" stop-color="{C['bg0']}"/>
    </linearGradient>
    <linearGradient id="{uid}-gold" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{C['gold_lo']}"/><stop offset="0.5" stop-color="{C['gold_hi']}"/><stop offset="1" stop-color="{C['gold_lo']}"/>
    </linearGradient>
  </defs>"""


def _frame(uid: str, w: int, h: int, title: str, desc: str, body: str) -> str:
  return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{uid}-t {uid}-d">
  <title id="{uid}-t">{escape(title)}</title>
  <desc id="{uid}-d">{escape(desc)}</desc>
  {_defs(uid)}
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="22" fill="url(#{uid}-bg)" stroke="{C['line']}"/>
  <rect x="40" y="0" width="{w - 80}" height="3" fill="url(#{uid}-gold)"/>
  <g font-family="{FONT}">
{body}
  </g>
</svg>
"""


def _text(x: float, y: float, s: str, size: int, fill: str, weight: int = 400, anchor: str = "start", spacing: float = 0) -> str:
  ls = f' letter-spacing="{spacing}"' if spacing else ""
  return f'    <text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{ls}>{escape(s)}</text>'


def _pill(x: float, y: float, label: str, color: str, anchor_right: bool = False, size: int = 14) -> str:
  w = int(len(label) * size * 0.66) + 28
  x0 = x - w if anchor_right else x
  return (f'    <rect x="{x0}" y="{y}" width="{w}" height="{size + 16}" rx="{(size + 16) / 2}" fill="{color}" fill-opacity="0.12" stroke="{color}"/>\n'
          + _text(x0 + w / 2, y + size + 3, label.upper(), size, color, 600, "middle", 1.2))


def _bar(x: float, y: float, w: float, h: float, parts: list[tuple[int, str]], total: int) -> str:
  out = [f'    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{C["bg0"]}" stroke="{C["line"]}"/>']
  cx = x
  for n, color in parts:
    if not n or not total:
      continue
    seg = w * n / total
    out.append(f'    <rect x="{cx:.1f}" y="{y}" width="{seg:.1f}" height="{h}" fill="{color}"/>')
    cx += seg
  clip = f'<clipPath id="bar{int(x)}{int(y)}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}"/></clipPath>'
  return f"    <defs>{clip}</defs>\n    <g clip-path=\"url(#bar{int(x)}{int(y)})\">\n" + "\n".join(out) + "\n    </g>"


def dashboard_svg(s: dict) -> str:
  w, h = 1000, 600
  state = s["assurance_state"]
  bl = s["baseline"]
  ev, cl, cf = s["evidence"], s["claims"], s["configurations"]
  body = [
    _text(40, 56, "LIVING SAFETY CASE", 15, C["gold"], 700, spacing=3),
    _text(40, 96, "Recorded assurance state", 30, C["white"], 700),
    _text(40, 126, "Every figure is counted from the structured records in assurance/case.", 16, C["muted"]),
    _pill(960, 38, state, STATE_COLOR[state], anchor_right=True, size=15),
    _text(960, 100, f"Baseline {bl['id']} · {bl['source_revision']} · {bl['lifecycle_status'].replace('-', ' ')}", 15, C["muted"], anchor="end"),
    _text(960, 124, f"Records digest {s['records_digest']}", 15, C["dim"], anchor="end"),
  ]
  tiles = [
    (cl["registered"], "Safety claims", "registered in the argument", C["white"]),
    (cl["with_accepted_evidence"], "Claims with accepted", "supporting evidence", C["white"]),
    (ev["registered"], "Evidence items", f"{ev['partial']} drafted · {ev['missing']} missing", C["white"]),
    (ev["awaiting_review"], "Evidence to review", "drafted, not yet accepted", C["white"]),
    (s["actions_open"], "Open actions", "safety-case open items", C["white"]),
    (s["defeaters_open"], "Open defeaters", "known counter-evidence", C["white"]),
    (cf["evaluated"], "Evaluated", "vehicle configurations", C["white"]),
    (cf["assurance_supported"], "Assurance-supported", "vehicle configurations", C["white"]),
  ]
  tw, th, gap = 218, 128, 16
  for i, (n, l1, l2, color) in enumerate(tiles):
    x = 40 + (i % 4) * (tw + gap)
    y = 160 + (i // 4) * (th + gap)
    accent = C["gold"] if n == 0 else C["blue"]
    body += [
      f'    <rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="14" fill="{C["panel"]}" stroke="{C["line"]}"/>',
      f'    <rect x="{x}" y="{y + 22}" width="3" height="38" rx="1.5" fill="{accent}"/>',
      _text(x + 22, y + 58, str(n), 44, color, 700),
      _text(x + 22, y + 90, l1, 16, C["white"], 600),
      _text(x + 22, y + 112, l2, 14, C["muted"]),
    ]
  y = 460
  total = ev["registered"]
  body += [
    _text(40, y, "Evidence status", 16, C["white"], 600),
    _text(960, y, f"{total} items", 15, C["muted"], anchor="end"),
    _bar(40, y + 16, 920, 14, [(ev["available"], C["green"]), (ev["partial"], C["blue"]), (ev["missing"], C["dim"])], total),
  ]
  lx = 40
  legend = (
    ("Available and accepted", ev["available"], C["green"]),
    ("Drafted (partial)", ev["partial"], C["blue"]),
    ("Not yet performed", ev["missing"], C["dim"]),
  )
  for label, n, color in legend:
    body += [f'    <rect x="{lx}" y="{y + 46}" width="12" height="12" rx="3" fill="{color}"/>', _text(lx + 20, y + 57, f"{label}  {n}", 15, C["muted"])]
    lx += 300
  disclaimer = "Represents recorded engineering evidence and review state. Not a certification or approval for unsupervised operation."
  body.append(_text(40, 568, disclaimer, 14, C["dim"]))
  desc = " ".join([
    f"Assurance state {state}. Baseline {bl['id']} at {bl['source_revision']}.",
    f"{cl['registered']} safety claims registered, {cl['with_accepted_evidence']} with accepted supporting evidence.",
    f"{ev['registered']} evidence items: {ev['available']} available, {ev['partial']} partial, {ev['missing']} missing;",
    f"{ev['awaiting_review']} require review.",
    f"{s['actions_open']} open assurance actions, {s['defeaters_open']} open defeaters.",
    f"{cf['evaluated']} evaluated configuration(s), {cf['assurance_supported']} assurance-supported.",
  ])
  return _frame("dash", w, h, "LionDriver Living Safety Case dashboard", desc, "\n".join(body))


def lifecycle_svg(s: dict) -> str:
  w, h = 1000, 420
  body = [
    _text(40, 56, "LIFECYCLE AREAS", 15, C["gold"], 700, spacing=3),
    _text(40, 94, "Status by engineering area", 28, C["white"], 700),
    _text(960, 94, "Derived from evidence status and review state", 15, C["muted"], anchor="end"),
  ]
  cw, ch, gap = 296, 130, 16
  for i, a in enumerate(s["lifecycle_areas"]):
    x = 40 + (i % 3) * (cw + gap)
    y = 124 + (i // 3) * (ch + gap)
    color = STATUS_COLOR[a["status"]]
    body += [
      f'    <rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="14" fill="{C["panel"]}" stroke="{C["line"]}"/>',
      _text(x + 22, y + 36, f"{i + 1:02d}", 15, C["gold"], 700, spacing=1),
      _text(x + 56, y + 36, a["title"], 18, C["white"], 600),
      _pill(x + 22, y + 52, a["status"], color, size=12),
      _bar(x + 22, y + 94, cw - 44, 8, [(a["available"], C["green"]), (a["partial"], C["blue"]), (a["missing"], C["dim"])], a["evidence"]),
      _text(x + 22, y + 120, f"{a['partial']} drafted · {a['missing']} missing", 13, C["muted"]),
      _text(x + cw - 22, y + 120, f"{a['accepted']} of {a['evidence']} accepted", 13, C["muted"], anchor="end"),
    ]
  desc = "; ".join(f"{a['title']}: {a['status']} ({a['evidence']} evidence items, {a['partial']} drafted, {a['missing']} missing, {a['accepted']} accepted)"
                   for a in s["lifecycle_areas"])
  return _frame("life", w, h, "LionDriver assurance lifecycle areas", desc, "\n".join(body))


def ecosystem_svg(s: dict) -> str:
  w, h = 1000, 400
  up = s["configurations"]["upstream_compatible"]
  ev_n, sup_n = s["configurations"]["evaluated"], s["configurations"]["assurance_supported"]
  tiers = [
    ("UPSTREAM COMPATIBLE", f"{up['stated_count']}", f"Car models from {up['makes']} makes in the inherited openpilot list", C["blue"], 920),
    ("LIONDRIVER EVALUATED", f"{ev_n}", "Configurations under documented engineering evaluation", C["gold"], 800),
    ("ASSURANCE SUPPORTED", f"{sup_n}", "Configurations with accepted evidence for specific claims", C["green"], 680),
  ]
  body = [
    _text(40, 56, "VEHICLE ECOSYSTEM", 15, C["gold"], 700, spacing=3),
    _text(40, 94, "Compatibility is not assurance", 28, C["white"], 700),
    _text(960, 94, "Each tier needs its own evidence", 15, C["muted"], anchor="end"),
  ]
  for i, (label, n, line1, color, tw) in enumerate(tiers):
    y = 124 + i * 86
    x = 40 + (920 - tw) / 2
    filled = n != "0"
    body += [
      f'    <rect x="{x}" y="{y}" width="{tw}" height="74" rx="14" fill="{color if filled else C["panel"]}" '
      + f'fill-opacity="{0.12 if filled else 1}" stroke="{color}"' + ('' if filled else ' stroke-dasharray="6 6"') + '/>',
      _text(x + 28, y + 52, n, 40, C["white"], 700),
      _text(x + 130, y + 31, label, 13, color, 700, spacing=2),
      _text(x + 130, y + 56, line1, 16, C["white"]),
    ]
  desc = " ".join([
    f"Upstream compatible: {up['stated_count']} car models from {up['makes']} makes listed in docs/CARS.md.",
    f"LionDriver evaluated: {ev_n} configuration. Assurance supported: {sup_n} configurations.",
    "Vehicle compatibility does not imply independent safety assurance.",
  ])
  return _frame("eco", w, h, "LionDriver vehicle ecosystem classification", desc, "\n".join(body))


def readme_block(s: dict) -> str:
  ev, cl, cf = s["evidence"], s["claims"], s["configurations"]
  bl = s["baseline"]
  rows = [
    ("Assurance state", s["assurance_state"]),
    ("Engineering baseline", f"`{bl['id']}` at `{bl['source_revision']}` ({bl['lifecycle_status'].replace('-', ' ')})"),
    ("Registered safety claims", f"{cl['registered']}"),
    ("Claims with accepted supporting evidence", f"{cl['with_accepted_evidence']}"),
    ("Registered evidence items", f"{ev['registered']} ({ev['available']} available, {ev['partial']} drafted, {ev['missing']} not yet performed)"),
    ("Evidence requiring review", f"{ev['awaiting_review']}"),
    ("Open assurance actions", f"{s['actions_open']}"),
    ("Open defeaters (known counter-evidence)", f"{s['defeaters_open']}"),
    ("Evaluated configurations", f"{cf['evaluated']}"),
    ("Assurance-supported configurations", f"{cf['assurance_supported']}"),
    ("Records digest", f"`{s['records_digest']}`"),
  ]
  lines = [BEGIN, "", "| Indicator | Recorded value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows] + [""]
  lines += ["| Lifecycle area | Status | Evidence (drafted / missing / accepted) |", "|---|---|---|"]
  lines += [f"| {a['title']} | {a['status']} | {a['evidence']} ({a['partial']} / {a['missing']} / {a['accepted']}) |" for a in s["lifecycle_areas"]]
  lines += ["", END]
  return "\n".join(lines)


def outputs(s: dict) -> dict[Path, str]:
  readme = README.read_text(encoding="utf-8")
  if BEGIN in readme and END in readme:
    pre, rest = readme.split(BEGIN, 1)
    post = rest.split(END, 1)[1]
    readme = pre + readme_block(s) + post
  # Keep the upstream model count quoted in the README prose in step with docs/CARS.md.
  readme = re.sub(r"\*\*[0-9]+ car models\*\*", f"**{s['configurations']['upstream_compatible']['stated_count']} car models**", readme)
  return {
    STATUS_JSON: json.dumps(s, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    ASSET_DIR / "dashboard.svg": dashboard_svg(s),
    ASSET_DIR / "lifecycle.svg": lifecycle_svg(s),
    ASSET_DIR / "ecosystem.svg": ecosystem_svg(s),
    README: readme,
  }


def main(argv: list[str]) -> int:
  check = "--check" in argv
  case = load_case()
  rep = validate(case)
  if rep.errors:
    for e in rep.errors:
      print(f"ERROR {e}")
    print("FAIL: records are invalid; run assurance/case/tools/validate.py and fix them first")
    return 1
  stale = []
  for path, content in outputs(summarize(case)).items():
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
      continue
    if check:
      stale.append(path.relative_to(REPO_ROOT).as_posix())
    else:
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(content, encoding="utf-8")
      print(f"wrote {path.relative_to(REPO_ROOT).as_posix()}")
  if stale:
    print("FAIL: generated outputs are out of date: " + ", ".join(stale))
    print("Run: python3 assurance/case/tools/generate_dashboard.py, then commit the result")
    return 1
  print("OK: dashboard outputs match the records" if check else "OK: dashboard generated")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
