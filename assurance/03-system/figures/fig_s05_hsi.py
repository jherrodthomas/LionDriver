#!/usr/bin/env python3
"""Draw WP-S-05 Figure 2-1, the hardware-software interfaces of the safety MCU (fig-s05-2-1-hsi-overview.svg).

Every interface card is read from the §2 table "Interface summary" of WP-S-05: the HSI ID, the interface, the hardware
resource, the ASIL and the TSR / HWSR column. Only the placement is fixed here (PLACE): which side of the MCU an
interface sits on and which external element it reaches. --check fails if §2 gains an HSI row that PLACE does not
place, or loses one that it does.

    python3 fig_s05_hsi.py            # write the SVG
    python3 fig_s05_hsi.py --check    # fail if §2 and PLACE disagree or the SVG is stale

Standard library only. Output is deterministic.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / "assurance" / "03-system" / "WP-S-05-hsi-specification.md"
OUT = "fig-s05-2-1-hsi-overview.svg"

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
SAFETY, SAFETY_BG = "#C2410C", "#FFF7ED"
AMBER = "#D97706"
SW = "#0F766E"
GREY_BG = "#F1F5F9"

# Column of each interface: "soc" (link to the SoC, left), "core" (inside the MCU), "out" (to the vehicle, harness
# or speaker, right). The external element an "soc"/"out" interface reaches is the second value.
PLACE = {
  "HSI-01": ("soc", "soc"), "HSI-02": ("soc", "soc"), "HSI-03": ("soc", "soc"), "HSI-08": ("soc", "soc"),
  "HSI-09": ("core", None), "HSI-10": ("core", None), "HSI-12": ("core", None), "HSI-13": ("core", None),
  "HSI-14": ("core", None),
  "HSI-04": ("out", "can"), "HSI-05": ("out", "harness"), "HSI-06": ("out", "harness"),
  "HSI-07": ("out", "harness"), "HSI-11": ("out", "speaker"),
}
EXTERNAL = {
  "soc": ("E-01 SoC software", ["pandad: SPI driver", "GPIO: STM_RST_N,", "STM_BOOT0"], "QM"),
  "can": ("Vehicle CAN", ["bus 0: car side", "(EPS, PCM, ABS)", "bus 1: OBD / auxiliary", "bus 2: camera side"], "EXT"),
  "harness": ("E-05 harness", ["intercept relay coil", "SBU1 / SBU2 lines", "ignition line"], "C / B"),
  "speaker": ("Speaker", ["shared with the SoC", "(E-04b)"], "QM"),
}

W, MARGIN = 1280, 40
X_EXT_L, W_EXT = 40, 160
X_MCU, W_MCU = 250, 790
COLS = {"soc": (270, 240), "core": (530, 240), "out": (790, 230)}
X_EXT_R = 1080
CARD_GAP, Y0 = 12, 156


def interfaces(md: str) -> list[dict]:
  start = md.index("\n## 2.")
  sec = md[start:md.index("\n## ", start + 1)]
  rows = []
  for line in sec.splitlines():
    m = re.match(r"^\| (HSI-\d\d) \|", line)
    if not m:
      continue
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    rows.append({"id": c[0], "name": c[1], "hw": c[2], "asil": c[5], "reqs": c[6]})
  return rows


def plain(s: str) -> str:
  """Table text without code marks and without parenthetical detail (kept in §2)."""
  s = s.replace("`", "")
  while re.search(r"\s*\([^()]*\)", s):
    s = re.sub(r"\s*\([^()]*\)", "", s)
  return s.strip()


def width(s: str, size: float) -> float:
  return sum((0.28 if c in " ,.()/;:|'" else 0.6 if c.isupper() else 0.55) * size for c in s)


def wrap(s: str, limit: float, size: float, max_lines: int) -> list[str]:
  lines, cur = [], ""
  for word in s.split():
    trial = f"{cur} {word}" if cur else word
    if cur and width(trial, size) > limit:
      lines.append(cur)
      cur = word
    else:
      cur = trial
  if cur:
    lines.append(cur)
  if len(lines) > max_lines:
    lines = lines[:max_lines]
    while width(lines[-1] + " …", size) > limit and " " in lines[-1]:
      lines[-1] = lines[-1].rsplit(" ", 1)[0]
    lines[-1] += " …"
  return lines


def el(tag: str, body: str | None = None, **attrs) -> str:
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if body is None else f"<{tag}{a}>{escape(body)}</{tag}>"


def text(x, y, s, size=11, fill=INK, weight="", anchor="", family="") -> str:
  return el("text", s, x=x, y=y, font_size=size, fill=fill, font_weight=weight, text_anchor=anchor, font_family=family)


def asil_colour(asil: str) -> str:
  return SAFETY if asil.startswith("C") else AMBER if asil.startswith("B") else MUTED


def card(row: dict, x: int, w: int) -> tuple[list[str], int]:
  """One interface card at (x, 0); returns its SVG parts (y relative) and height."""
  name = wrap(plain(row["name"]), w - 24, 11.5, 2)
  hw = wrap(plain(row["hw"]), w - 24, 10, 2) if plain(row["hw"]) not in ("", "—") else []
  reqs = wrap(row["reqs"], w - 24, 9.5, 2)
  h = 30 + 15 * len(name) + 13 * len(hw) + 13 * len(reqs) + 6
  planned = "to be added" in row["name"]
  parts = [el("rect", x=x, y=0, width=w, height=h, rx=8, fill="#FFFFFF",
              stroke=asil_colour(row["asil"]), stroke_width=1.4, stroke_dasharray="5 3" if planned else "")]
  parts.append(text(x + 12, 20, row["id"], 10.5, MUTED, "700"))
  pill = row["asil"].replace(" (+CS)", " + CS")
  pw = width(pill, 10) + 16
  parts.append(el("rect", x=f"{x + w - 10 - pw:.1f}", y=8, width=f"{pw:.1f}", height=17, rx=8.5,
                  fill=asil_colour(row["asil"])))
  parts.append(text(f"{x + w - 10 - pw / 2:.1f}", 20, pill, 10, "#FFFFFF", "700", "middle"))
  y = 38
  for line in name:
    parts.append(text(x + 12, y, line, 11.5, INK, "600"))
    y += 15
  for line in hw:
    parts.append(text(x + 12, y, line, 10, MUTED))
    y += 13
  for line in reqs:
    parts.append(text(x + 12, y, line, 9.5, SW, "600", family=MONO))
    y += 13
  return parts, h


def build(md: str | None = None) -> str:
  md = md if md is not None else SOURCE.read_text(encoding="utf-8")
  rows = interfaces(md)
  body: list[str] = []
  col_y = {c: Y0 for c in COLS}
  anchors: dict[str, list[tuple[float, float]]] = {}  # external -> (y of the card centre, x of the card edge)
  for row in sorted(rows, key=lambda r: r["id"]):
    col, ext = PLACE[row["id"]]
    x, w = COLS[col]
    parts, h = card(row, x, w)
    y = col_y[col]
    body.append(f'<g transform="translate(0,{y})">' + "".join(parts) + "</g>")
    if ext:
      anchors.setdefault(ext, []).append((y + h / 2, x if col == "soc" else x + w))
    col_y[col] = y + h + CARD_GAP
  bottom = max(col_y.values()) - CARD_GAP

  # MCU boundary behind the cards
  mcu = [el("rect", x=X_MCU, y=Y0 - 44, width=W_MCU, height=bottom - Y0 + 64, rx=14, fill=SAFETY_BG,
            fill_opacity=".55", stroke=SAFETY, stroke_width=1.2, stroke_dasharray="4 3"),
         text(X_MCU + 16, Y0 - 22, "Safety MCU · STM32H7 “panda”", 13, INK, "700"),
         text(X_MCU + 236, Y0 - 22, "E-04a hardware · E-03a/E-03b firmware · ASIL C", 11, SAFETY, "700")]
  for col, label in (("soc", "LINK TO THE SoC"), ("core", "INSIDE THE MCU"), ("out", "TO VEHICLE, HARNESS, SPEAKER")):
    x, _ = COLS[col]
    mcu.append(text(x, Y0 - 6, label, 9, "#64748B", "700"))

  # external elements, each spanning the cards it connects to
  ext_parts, links = [], []
  for key, pts in anchors.items():
    title, lines, asil = EXTERNAL[key]
    ys = [p[0] for p in pts]
    need = 34 + 14 * len(lines)
    top = min(min(ys) - 24, (min(ys) + max(ys)) / 2 - need / 2)
    h = max(max(ys) + 24 - top, need)
    left = key == "soc"
    x = X_EXT_L if left else X_EXT_R
    fill = GREY_BG if asil in ("EXT", "QM") else SAFETY_BG
    stroke = FAINT if asil in ("EXT", "QM") else SAFETY
    ext_parts.append(el("rect", x=x, y=f"{top:.1f}", width=W_EXT, height=f"{h:.1f}", rx=10, fill=fill, stroke=stroke,
                        stroke_width=1.2, stroke_dasharray="5 3" if asil == "EXT" else ""))
    ext_parts.append(text(x + 12, f"{top + 20:.1f}", title, 11.5, INK, "700"))
    ext_parts.append(text(x + W_EXT - 10, f"{top + 20:.1f}", asil, 10, MUTED if fill == GREY_BG else SAFETY, "700", "end"))
    for k, line in enumerate(lines):
      ext_parts.append(text(x + 12, f"{top + 38 + 14 * k:.1f}", line, 9.5, MUTED))
    for yc, xe in pts:
      x1, x2 = (xe, x + W_EXT) if left else (xe, x)
      links.append(el("line", x1=x1, y1=f"{yc:.1f}", x2=x2, y2=f"{yc:.1f}", stroke=MUTED, stroke_width=1.4,
                      marker_end="url(#ar)", marker_start="url(#al)"))

  n_c = sum(1 for r in rows if r["asil"].startswith("C"))
  n_b = sum(1 for r in rows if r["asil"].startswith("B"))
  height = bottom + 120
  head = [
    text(MARGIN, 44, "Figure 2-1 · Hardware-software interfaces of the safety MCU", 20, INK, "700"),
    text(MARGIN, 66, f"{len(rows)} interfaces of §2 by where they lead · {n_c} ASIL C, {n_b} ASIL B · the ASIL is the "
         "highest of the interface's TSRs", 12.5, MUTED),
    text(W - MARGIN, 44, "WP-S-05 §2", 11, MUTED, anchor="end"),
    text(W - MARGIN, 62, "detail §3–§9 · signals §11", 11, MUTED, anchor="end"),
    el("line", x1=MARGIN, y1=82, x2=W - MARGIN, y2=82, stroke=HAIR),
  ]
  ly = bottom + 50
  legend = [
    el("line", x1=MARGIN, y1=ly - 18, x2=W - MARGIN, y2=ly - 18, stroke=HAIR),
    el("rect", x=MARGIN, y=ly - 8, width=28, height=16, rx=4, fill="#FFFFFF", stroke=SAFETY, stroke_width=1.4),
    text(MARGIN + 36, ly + 4, "ASIL C interface", 10.5),
    el("rect", x=MARGIN + 170, y=ly - 8, width=28, height=16, rx=4, fill="#FFFFFF", stroke=AMBER, stroke_width=1.4),
    text(MARGIN + 206, ly + 4, "ASIL B interface", 10.5),
    el("rect", x=MARGIN + 340, y=ly - 8, width=28, height=16, rx=4, fill="#FFFFFF", stroke=SAFETY, stroke_width=1.4,
       stroke_dasharray="5 3"),
    text(MARGIN + 376, ly + 4, "to be added (not in the firmware yet)", 10.5),
    text(MARGIN + 620, ly + 4, "TSR / HWSR", 10.5, SW, "600", family=MONO),
    text(MARGIN + 700, ly + 4, "requirements of §2 · + CS: also a cybersecurity interface", 10.5),
    text(MARGIN, ly + 28, "Generated from the WP-S-05 §2 table by fig_s05_hsi.py; parenthetical detail of the "
         "interface and resource columns is left to §2. Pin assignments are to be confirmed against the schematic "
         "(WP-H-02 OI-1).", 10, MUTED),
  ]
  title = "Figure 2-1. Hardware-software interfaces of the safety MCU (WP-S-05 §2)"
  desc = ("The safety MCU (STM32H7, E-04a hardware running the E-03 firmware, ASIL C) and its "
          f"{len(rows)} hardware-software interfaces from WP-S-05 §2. " +
          " ".join(f"{r['id']} {plain(r['name'])}, {r['asil']}, {r['reqs']}." for r in rows))
  defs = ('<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
          f'orient="auto"><path d="M0 0L10 5L0 10z" fill="{MUTED}"/></marker>'
          '<marker id="al" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="6" markerHeight="6" '
          f'orient="auto"><path d="M10 0L0 5L10 10z" fill="{MUTED}"/></marker></defs>')
  out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" '
         f'font-family="{FONT}" role="img" aria-labelledby="t d">',
         f'<title id="t">{escape(title)}</title>', f'<desc id="d">{escape(desc)}</desc>', defs,
         el("rect", width=W, height=height, fill="#FFFFFF"),
         *head, *mcu, *links, *ext_parts, *body, *legend, "</svg>"]
  return "\n".join(out) + "\n"


def problems(md: str) -> list[str]:
  ids = {r["id"] for r in interfaces(md)}
  return ([f"{i}: in WP-S-05 §2 but not placed in fig_s05_hsi.PLACE" for i in sorted(ids - set(PLACE))] +
          [f"{i}: placed in fig_s05_hsi.PLACE but not in WP-S-05 §2" for i in sorted(set(PLACE) - ids)])


def main(argv: list[str]) -> int:
  md = SOURCE.read_text(encoding="utf-8")
  found = problems(md)
  for p in found:
    print(p, file=sys.stderr)
  if found:
    return 1
  svg = build(md)
  path = HERE / OUT
  if "--check" in argv:
    if not path.exists() or path.read_text(encoding="utf-8") != svg:
      print(f"stale: {OUT}\nrun: python3 assurance/03-system/figures/fig_s05_hsi.py", file=sys.stderr)
      return 1
    print(f"fig_s05_hsi: {OUT} current")
    return 0
  path.write_text(svg, encoding="utf-8")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
