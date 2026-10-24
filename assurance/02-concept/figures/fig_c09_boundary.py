#!/usr/bin/env python3
"""Draw WP-C-09 Figure 1-1, the item boundary in the cybersecurity view (fig-c09-1-1-cybersecurity-view.svg).

The layout follows WP-C-01 Figure 3-2 and WP-C-04 Figure 10-1: the comma device E-04 with the SoC software E-01, the
models E-02 and the panda safety MCU E-03 inside the boundary, the harness E-05 below it, the vehicle CAN under that,
and the external entities around it. Each place carries what the TARA puts there:

  - the assets of §2 held there (`ASSET_PLACE`, an analyst input: the §2 "Where" column is free text);
  - the threat scenarios of §4 against those assets, coloured by their §8 risk value;
  - the attack paths of §5 whose entry point is there (`AP_ENTRY`, an analyst input from the §5 "Entry point" column).

Each box is outlined by the highest risk among its threat scenarios. Assets, threat scenarios, risk values and attack
paths come from WP-C-09; only the two placements are hand-listed, and the build fails if an asset or attack path of
WP-C-09 is missing from them or a placement names one WP-C-09 does not have.

    python3 fig_c09_boundary.py            # write the SVG
    python3 fig_c09_boundary.py --check    # fail if a placement is incomplete or the SVG is stale

Standard library only. Drawing helpers come from ../hara/hara_figures.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-09-tara.md"
OUT = "fig-c09-1-1-cybersecurity-view.svg"
sys.path.insert(0, str(HERE.parent / "hara"))
import hara_figures as hf  # noqa: E402
from hara_figures import INK, MUTED, HAIR, t, wrap, header, svg_doc  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "trace" / "tools"))
import terms  # noqa: E402  (the shared abbreviation list; each figure ends with its definitions)

RISK_COL = {5: ("#B42318", "#FDE4E1", "#FFFFFF"), 4: ("#C2410C", "#FFF1EB", "#FFFFFF"), 3: ("#B45309", "#FFFBEB", INK),
            2: ("#64748B", "#F8FAFC", INK), 1: ("#94A3B8", "#F8FAFC", INK)}
# Places: id -> (x, y, w, h, title, subtitle, inside the item)
PLACES = {
  "E-01": (282, 214, 360, 176, "E-01 SoC software", "openpilot on AGNOS, params, IPC, updater, SSH", True),
  "E-02": (282, 400, 360, 92, "E-02 ML models", "driving and DM models (LFS)", True),
  "E-03": (662, 214, 300, 176, "E-03 panda safety MCU", "envelope firmware, safety mode, boot chain", True),
  "E-04": (662, 400, 300, 92, "E-04 storage, cameras, key", "data at rest on the device hardware", True),
  "E-05": (560, 532, 402, 92, "E-05 harness and relay", "camera-side forwarding, stock PCS", True),
  "CAN": (240, 676, 722, 92, "Vehicle CAN · Toyota ECUs", "bus 0 actuation and status (IF-01, IF-02); OBD-II port", False),
  "BACKEND": (1010, 214, 230, 130, "comma.ai back end", "athena RPC, connect, upload", False),
  "SUPPLY": (1010, 360, 230, 132, "Code and supply chain", "GitHub, update branch, submodules, wheels", False),
}
ASSET_PLACE = {
  "AS-01": "CAN", "AS-02": "E-03", "AS-03": "E-03", "AS-04": "E-03", "AS-05": "E-01", "AS-06": "E-01", "AS-07": "E-01",
  "AS-08": "E-02", "AS-09": "E-01", "AS-10": "BACKEND", "AS-11": "E-04", "AS-12": "E-04", "AS-13": "E-04",
  "AS-14": "E-01", "AS-15": "E-05", "AS-16": "SUPPLY",
}
AP_ENTRY = {
  "AP-01": "CAN", "AP-02": "E-01", "AP-03": "E-01", "AP-04": "E-01", "AP-05": "E-03", "AP-06": "SUPPLY",
  "AP-07": "BACKEND", "AP-08": "E-01", "AP-09": "E-02", "AP-10": "SUPPLY", "AP-11": "E-04", "AP-12": "E-01",
  "AP-13": "BACKEND", "AP-14": "E-01",
}


class BoundaryError(ValueError):
  pass


def _section(md: str, num: int) -> str:
  m = re.search(rf"^## {num}\. .*?$(.*?)(?=^## |\Z)", md, re.M | re.S)
  if not m:
    raise BoundaryError(f"WP-C-09 §{num} not found")
  return m.group(1)


def _cells(ln: str) -> list[str]:
  return [c.strip() for c in ln.strip()[1:-1].split("|")]


def parse(md: str) -> dict:
  assets = {}
  for ln in _section(md, 2).splitlines():
    if ln.startswith("| AS-"):
      c = _cells(ln)
      assets[c[0]] = c[1].replace("`", "")
  ts = {}
  for ln in _section(md, 4).splitlines():
    if ln.startswith("| TS-"):
      c = _cells(ln)
      ts[c[0]] = {"text": c[1].replace("`", ""), "assets": re.findall(r"AS-\d\d", c[3])}
  for ln in _section(md, 8).splitlines():
    if ln.startswith("| TS-"):
      c = _cells(ln)
      m = re.search(r"\d", c[3])
      if c[0] not in ts or not m:
        raise BoundaryError(f"§8 row {c[0]} has no §4 scenario or no risk value")
      ts[c[0]]["risk"] = int(m.group(0))
  aps = {}
  for ln in _section(md, 5).splitlines():
    if ln.startswith("| AP-"):
      c = _cells(ln)
      aps[c[0]] = {"entry": c[1], "ts": re.findall(r"TS-\d\d", c[4])}
  if not assets or not ts or not aps:
    raise BoundaryError("WP-C-09 §2, §4 or §5 table not found")
  if missing := [x for x in ts if "risk" not in ts[x]]:
    raise BoundaryError(f"threat scenarios without a §8 risk value: {', '.join(missing)}")
  for name, place, ids in (("ASSET_PLACE", ASSET_PLACE, assets), ("AP_ENTRY", AP_ENTRY, aps)):
    if gap := sorted(set(ids) - set(place)):
      raise BoundaryError(f"{name} does not place {', '.join(gap)}")
    if extra := sorted(set(place) - set(ids)):
      raise BoundaryError(f"{name} names {', '.join(extra)}, which WP-C-09 does not define")
    if bad := sorted({p for p in place.values() if p not in PLACES}):
      raise BoundaryError(f"{name} uses unknown places {', '.join(bad)}")
  for x, v in ts.items():
    if bad := [a for a in v["assets"] if a not in assets]:
      raise BoundaryError(f"{x} names assets §2 does not define: {', '.join(bad)}")
  return {"assets": assets, "ts": ts, "aps": aps}


def place_model(d: dict) -> dict[str, dict]:
  out = {}
  for p in PLACES:
    a = sorted(x for x, pl in ASSET_PLACE.items() if pl == p)
    tss = sorted(x for x, v in d["ts"].items() if set(v["assets"]) & set(a))
    out[p] = {"assets": a, "ts": tss, "aps": sorted(x for x, pl in AP_ENTRY.items() if pl == p),
              "top": max((d["ts"][x]["risk"] for x in tss), default=0)}
  return out


def _chip(body, x, y, label, stroke, fill, tc, w=None):
  w = w or hf.text_w(label, 9.5, True) + 10
  body.append(f'<rect x="{x:g}" y="{y:g}" width="{w:.1f}" height="16" rx="4" fill="{fill}" stroke="{stroke}"/>')
  body.append(t(x + w / 2, y + 11.5, label, 9.5, tc, 700, "middle"))
  return w


def _row(body, x0, y, width, items) -> float:
  x = x0
  for label, stroke, fill, tc in items:
    w = hf.text_w(label, 9.5, True) + 10
    if x + w > x0 + width and x > x0:
      x, y = x0, y + 19
    _chip(body, x, y, label, stroke, fill, tc, w)
    x += w + 4
  return y + 19


def _box(body, p, v, d):
  x, y, w, h, title, sub, inside = PLACES[p]
  if v["top"]:
    stroke, fill, _ = RISK_COL[v["top"]]
  else:
    stroke, fill = "#CBD5E1", "#FFFFFF"
  dash = "" if inside else ' stroke-dasharray="5 4"'
  body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill if inside else "#F8FAFC"}" '
              f'stroke="{stroke}" stroke-width="{2 if v["top"] >= 4 else 1.3}"{dash}/>')
  body.append(t(x + 10, y + 19, title, 12, INK, 700))
  yy = y + 33
  for ln in wrap(sub, w - 20, 10)[:1]:
    body.append(t(x + 10, yy, ln, 10, MUTED))
  yy += 8
  yy = _row(body, x + 10, yy, w - 20, [(a, "#64748B", "#FFFFFF", INK) for a in v["assets"]])
  if v["ts"]:
    yy = _row(body, x + 10, yy, w - 20,
              [(f"{x_} · {d['ts'][x_]['risk']}", RISK_COL[d["ts"][x_]["risk"]][0], RISK_COL[d["ts"][x_]["risk"]][0],
                RISK_COL[d["ts"][x_]["risk"]][2]) for x_ in v["ts"]])
  if v["aps"]:
    body.append(t(x + 10, yy + 11, "entered by " + ", ".join(v["aps"]), 10, "#7C3AED", 700))


def figure(d: dict) -> str:
  model = place_model(d)
  W = 1280
  body = header(W, "Figure 1-1 · The item boundary in the cybersecurity view",
                "WP-C-01 Figure 3-2 with the TARA on it: the assets each element holds (§2), the threat scenarios "
                "against them by risk value (§4, §8) and the attack paths that enter there (§5)", "WP-C-09 §2, §4, §5, §8",
                "layout: WP-C-01 Figure 3-2")
  # item boundary and device
  body.append('<rect x="244" y="150" width="736" height="490" rx="16" fill="#FFFDF7" stroke="#C2410C" stroke-width="1.6" stroke-dasharray="7 5"/>')
  body.append('<rect x="262" y="136" width="190" height="26" rx="13" fill="#C2410C"/>')
  body.append(t(357, 153.5, "ITEM BOUNDARY · LD-SDA", 11, "#FFFFFF", 700, "middle"))
  body.append('<rect x="266" y="176" width="712" height="332" rx="11" fill="#FFFFFF" stroke="#94A3B8" stroke-width="1.2"/>')
  body.append(t(280, 200, "E-04 comma device", 12.5, INK, 700))
  body.append(t(420, 200, "the QM SoC and the safety MCU share one board; SPI between them (IF-04)", 10.5, MUTED))
  # links
  body.append('<line x1="642" y1="300" x2="662" y2="300" stroke="#475569" stroke-width="2"/>')
  body.append('<line x1="812" y1="390" x2="812" y2="400" stroke="#475569" stroke-width="0"/>')
  body.append('<line x1="812" y1="492" x2="812" y2="532" stroke="#475569" stroke-width="2"/>')
  body.append('<line x1="700" y1="624" x2="700" y2="676" stroke="#475569" stroke-width="2"/>')
  body.append('<path d="M978 280 H 1010" stroke="#7C3AED" stroke-width="1.6" stroke-dasharray="5 4" fill="none"/>')
  body.append(t(994, 272, "IF-09", 9.5, "#7C3AED", 700, "middle"))
  body.append('<path d="M978 426 H 1010" stroke="#7C3AED" stroke-width="1.6" stroke-dasharray="5 4" fill="none"/>')
  for p in PLACES:
    _box(body, p, model[p], d)
  # attacker with physical access, left
  box_at = len(body)
  body.append(t(52, 192, "Attacker positions (§5)", 12, INK, 700))
  yy = 212
  entries = {}
  for ap, v in d["aps"].items():
    entries.setdefault(v["entry"].replace("`", ""), []).append(ap)
  for entry, ids in entries.items():
    lines = wrap(entry, 156, 10)
    body.append(t(52, yy, ", ".join(ids), 10, "#7C3AED", 700))
    yy += 13
    for ln in lines[:2]:
      body.append(t(52, yy, ln, 10, INK))
      yy += 12.5
    yy += 4
  body.insert(box_at, f'<rect x="40" y="170" width="180" height="{yy - 170 + 6:g}" rx="10" fill="#F5F3FF" stroke="#7C3AED" stroke-dasharray="5 4"/>')
  # key, right bottom
  kx, ky = 1010, 520
  body.append(t(kx, ky, "HOW TO READ", 10.5, MUTED, 700, extra=' letter-spacing=".04em"'))
  for head, txt in (("Grey chips", "assets held there (§2)"),
                    ("Coloured chips", "threat scenarios against them, with their §8 risk value"),
                    ("Outline", "the highest risk value in the box"),
                    ("Violet", "attack paths whose entry point is there (§5)")):
    ky += 16
    body.append(t(kx, ky, head, 11, INK, 700))
    for ln in wrap(txt, 220, 10.5):
      ky += 13.5
      body.append(t(kx, ky, ln, 10.5, MUTED))
  y = 800
  body.append(f'<line x1="40" y1="{y}" x2="{W - 40}" y2="{y}" stroke="{HAIR}"/>')
  y += 24
  lx = 40
  for r in (5, 4, 3):
    _chip(body, lx, y - 12, f"risk {r}", RISK_COL[r][0], RISK_COL[r][0], RISK_COL[r][2])
    lx += hf.text_w(f"risk {r}", 9.5, True) + 18
  body.append(t(lx + 6, y, "risk ≥ 3 needs treatment; 4–5 drive a cybersecurity goal (§7, WP-C-10)", 11))
  y += 20
  body.append(t(40, y, "Ratings reflect the baseline as shipped and credit no control that does not exist yet; treatments in "
                "the reference build are not re-rated (OI-5). Where each asset and entry point is drawn is an analyst "
                "input in fig_c09_boundary.py.", 11, MUTED))
  extra, y = terms.svg_footer(body, 40, y + 20, W - 80)
  body += extra
  body.append(t(W - 40, y + 6, "Generated by fig_c09_boundary.py", 10, MUTED, None, "end"))
  h = y + 20
  desc = ("The WP-C-01 item boundary with the WP-C-09 TARA on it. " + " ".join(
    f"{PLACES[p][4]}: assets {', '.join(v['assets']) or 'none'}; threat scenarios "
    + (", ".join(f"{x} (risk {d['ts'][x]['risk']})" for x in v["ts"]) or "none")
    + f"; entered by {', '.join(v['aps']) or 'none'}." for p, v in model.items()))
  return svg_doc(W, h, "Figure 1-1. The item boundary in the cybersecurity view (WP-C-09 §2, §4, §5, §8)", desc, body)


def build() -> dict[str, str]:
  return {OUT: figure(parse(SOURCE.read_text(encoding="utf-8")))}


def main(argv: list[str]) -> int:
  try:
    outputs = build()
  except BoundaryError as e:
    print(f"fig_c09_boundary: {e}", file=sys.stderr)
    return 1
  if "--check" in argv:
    stale = [n for n, c in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != c]
    for n in stale:
      print(f"assurance/02-concept/figures/{n} is stale; run fig_c09_boundary.py", file=sys.stderr)
    if not stale:
      print(f"fig_c09_boundary: {len(outputs)} figure current")
    return 1 if stale else 0
  for n, c in outputs.items():
    (HERE / n).write_text(c, encoding="utf-8")
    print(f"wrote assurance/02-concept/figures/{n}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
