#!/usr/bin/env python3
"""Draw the WP-C-01 interface figures (Figure 2-1 stock functions, Figure 3-3 CAN interface map, Figure 8-1 envelope).

The source of record is `../WP-C-01-item-definition.md`:
  - Figure 2-1 is generated from the §2.2 table (stock TSS 2.0 function, with LD-SDA installed, basis). The status of
    each row is read from its wording; the AoU status is read from the §7 table.
  - Figure 3-3 is generated from the §3.4 table: every `0xNNN` of the IF-01, IF-02 and IF-03 content cells with its
    name, its bus, direction and counterpart. What the panda safety mode does with each message is listed in TX, RX
    and FORWARD_BLOCKED below. CI does not check out the opendbc submodule, so these facts are hand-listed; each carries
    the exact text (`src`) of an assurance document that states it, and `--check` fails when that text is gone.
    `test_fig_c01_interfaces.py` compares them with `opendbc_repo/opendbc/safety/modes/toyota.h` when it is present.
  - Figure 8-1 is generated from the §8 table; every number is parsed from its Value cell.
`--check` fails when a source text no longer appears, when the §3.4 IDs and the hand-listed facts disagree, or when a
committed SVG differs.

    python3 fig_c01_interfaces.py            # regenerate the SVGs
    python3 fig_c01_interfaces.py --check    # fail if a source text changed or an SVG is stale

Standard library only. Output is deterministic.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "WP-C-01-item-definition.md"
ASSURANCE = HERE.parents[1]
REPO = HERE.parents[2]
TOYOTA_H = REPO / "opendbc_repo" / "opendbc" / "safety" / "modes" / "toyota.h"

# ---------------------------------------------------------------- palette (assurance figure style)

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SFMono-Regular', Menlo, Consolas, monospace"
INK, MUTED, FAINT, LINE, HAIR = "#0F172A", "#475569", "#94A3B8", "#CBD5E1", "#E2E8F0"
BORDER = "#64748B"
CHIP = "#F8FAFC"
SAFETY, SAFETY_BG, SAFETY_SOFT = "#C2410C", "#FFF7ED", "#FDBA74"
SW, SW_BG = "#0F766E", "#F0FDFA"
AMBER, AMBER_BG = "#D97706", "#FFFBEB"
RED = "#D2553F"
GREY_BG = "#F1F5F9"
SCOPE = "#B45309"

# ---------------------------------------------------------------- hand-listed safety-mode facts (Figure 3-3)
# Reference configuration: non-SecOC, LKA torque control, BRAKE_MODULE 0x226, openpilot longitudinal
# (TOYOTA_LONG_TX_MSGS, TOYOTA_RX_CHECKS(false)). Every `src` is (file under assurance/, exact text).

S02 = "03-system/WP-S-02-technical-safety-requirements.md"
S05 = "03-system/WP-S-05-hsi-specification.md"
W05 = "05-software/WP-W-05-software-unit-design.md"
W09 = "05-software/WP-W-09-configuration-calibration-data.md"
DN01 = "05-software/design-notes/DN-01-tx-rate-supervision.md"
DFA = "08-analyses/fmea/analyses/dfa.yaml"
TSR_YAML = "trace/items/tsr.yaml"
V05 = "06-validation/WP-V-05-fault-injection.md"
C01 = "02-concept/WP-C-01-item-definition.md"

WHITELIST_SRC = (W05, "`0x191`, `0x412`, `0x1D2` (8 bytes), `0x2E4` (5 bytes), `0x343` (listed twice, `check_relay` false and " +
                 "true), `0x283` (7 bytes), `0x750`, all bus 0")
STATIC_BLOCK_SRC = (W05, "static block for the reference configuration: `0x191`, `0x412`, `0x2E4`, `0x343` towards bus 0")

# relay: listed with check_relay = true (statically blocked from the camera side, relay malfunction detection).
# check: the content check of toyota_tx_hook. ref: what the reference build adds. sent: False when the reference car
# never sends it. trace: IDs drawn next to the counterpart.
TX = {
  "0x2E4": {"relay": True, "check": "torque limits", "ref": "refused during an EPS fault", "sent": True,
            "trace": ["TSR-101", "TSR-110"],
            "src": [WHITELIST_SRC, STATIC_BLOCK_SRC,
                    (TSR_YAML, "The envelope shall reject every STEERING_LKA (`0x2E4`) frame whose STEER_TORQUE_CMD magnitude"),
                    (S02, "STEERING_LKA frames with torque or a steer request are refused")]},
  "0x191": {"relay": True, "check": "no actuation (LKA mode)", "ref": "", "sent": True, "trace": [],
            "src": [WHITELIST_SRC, STATIC_BLOCK_SRC, (W05, "`0x191` no actuation in LKA configuration")]},
  "0x343": {"relay": True, "check": "accel bounds (§8)", "ref": "", "sent": True, "trace": ["TSR-704"],
            "src": [WHITELIST_SRC, STATIC_BLOCK_SRC, (C01, "| Acceleration command | −3.5 … +2.0 m/s² |")]},
  "0x412": {"relay": True, "check": "whitelist only", "ref": "assist icon needs authority", "sent": True,
            "trace": ["AOU-12", "DM-11"],
            "src": [WHITELIST_SRC, STATIC_BLOCK_SRC,
                    (DFA, "LKAS_HUD with BARRIERS != 0 refused unless controls are allowed or were allowed within 1 s"),
                    (C01, "is not influenced by item TX messages other than `0x412` LKAS_HUD")]},
  "0x1D2": {"relay": False, "check": "whitelist only", "ref": "", "sent": False, "trace": [],
            "src": [WHITELIST_SRC, (DN01, "0 (PCM cancel; not sent by the reference car)")]},
  "0x283": {"relay": False, "check": "zero payload only", "ref": "", "sent": False, "trace": ["TSR-705"],
            "src": [WHITELIST_SRC, (W09, "`0x283` zero payload only"), (DN01, "Zero payload only; no openpilot caller sends it")]},
  "0x750": {"relay": False, "check": "tester present only", "ref": "", "sent": False, "trace": [],
            "src": [WHITELIST_SRC, (W09, "`0x750` tester present only"), (DN01, "0 (radar tester present; DISABLE_RADAR cars only)")]},
}
# On the openpilot-longitudinal whitelist only (not with stock longitudinal).
LONG_ONLY = {"0x283", "0x750"}
# Not accepted from the SoC in the reference build (drawn as a note under the TX rows).
TX_REFUSED = {
  "text": "Not accepted from the SoC: 0x344 and the DSU messages (every build); 0x411 PCS_HUD (reference build, AOU-15)",
  "src": [(W09, "**Removed in every build:** `0x344` PRE_COLLISION_2"),
          (S02, "`0x411` PCS_HUD refused in the reference build"),
          (C01, "It refuses PCS_HUD `0x411` from the SoC")],
}
# RX checks: rate in Hz, checksum verified, ref_only = only in the reference build (LIONDRIVER_REFERENCE).
RX = {
  "0xAA": {"rate": 83, "checksum": False, "ref_only": False, "trace": [],
           "src": [(S05, "| `0xAA` | WHEEL_SPEEDS | 83 Hz | no | no |")]},
  "0x260": {"rate": 50, "checksum": True, "ref_only": False, "trace": [],
            "src": [(S05, "| `0x260` | STEER_TORQUE_SENSOR | 50 Hz | yes | no |")]},
  "0x1D2": {"rate": 33, "checksum": True, "ref_only": False, "trace": ["F-03"],
            "src": [(S05, "| `0x1D2` | PCM_CRUISE | 33 Hz | yes | no |")]},
  "0x226": {"rate": 40, "checksum": False, "ref_only": False, "trace": [],
            "src": [(S05, "| `0x226` | BRAKE_MODULE | 40 Hz | no | no |")]},
  "0x262": {"rate": 25, "checksum": True, "ref_only": True, "trace": ["TSR-110"],
            "src": [(W09, "Reference build adds `0x262` EPS_STATUS 25 Hz and `0x1D3` PCM_CRUISE_2 33 Hz (checksum, no counter"),
                    (S02, "`0x262` is an envelope RX check (checksum, 5-period timeout at a nominal 25 Hz")]},
  "0x1D3": {"rate": 33, "checksum": True, "ref_only": True, "trace": ["TSR-405"],
            "src": [(W09, "Reference build adds `0x262` EPS_STATUS 25 Hz and `0x1D3` PCM_CRUISE_2 33 Hz (checksum, no counter"),
                    (V05, "TSR-405(c) implemented in the reference build: CRUISE_ACTIVE with `0x1D3` MAIN_ON = 0 refuses engagement")]},
}
RX_ARRIVAL_SRC = [(S02, "In the reference build `0x262` (25 Hz) and `0x1D3` (33 Hz) are also RX checks"),
                  (S05, "Reference-configuration RX set used by the envelope")]
# Camera-side frames the envelope does not forward to the car (TSR-704); must equal the relay-checked TX set.
FORWARD_BLOCKED = {
  "ids": ["0x2E4", "0x191", "0x412", "0x343"],
  "src": [(S02, "except STEERING_LKA `0x2E4`, STEERING_LTA `0x191`, LKAS_HUD `0x412` and (openpilot longitudinal) " +
           "ACC_CONTROL `0x343`")],
}
# Prose of the left-hand panel.
PANEL_SRC = [(C01, "The de-energised harness relay connects the forward camera to the vehicle CAN"),
             (C01, "| E-05 Harness | Toyota TSS2 harness with intercept switch between the forward camera and the vehicle CAN"),
             (S02, "| TSR-704 | The envelope shall forward every camera-side frame to the car side unchanged")]
VERIFY_SRC = [(S05, "to be measured, OI-7")]
# The §3.4 radar entry has no description; the meaning is taken from F-02 of §2.1.
RADAR = {"meaning": "lead tracks for F-02", "src": [(C01, "Lead detection fuses the stock radar track and vision")]}

# ---------------------------------------------------------------- SVG helpers (copied from trace_figures.py)


def el(tag: str, text: str | None = None, **attrs) -> str:
  """One SVG element; attribute names use _ for - (stroke_width -> stroke-width), a trailing _ is dropped."""
  a = "".join(f' {k.rstrip("_").replace("_", "-")}="{v}"' for k, v in attrs.items() if v not in ("", None))
  return f"<{tag}{a}/>" if text is None else f"<{tag}{a}>{escape(text)}</{tag}>"


def fmt(v: float) -> str:
  return f"{v:.1f}".rstrip("0").rstrip(".")


def text(x, y, s, size=11, fill=INK, weight="", anchor="", family="", style="") -> str:
  return el("text", s, x=fmt(x), y=fmt(y), font_size=size, fill=fill, font_weight=weight, text_anchor=anchor,
            font_family=family, font_style=style)


def rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, sw=1.2, rx=8, dash="", opacity="") -> str:
  return el("rect", None, x=fmt(x), y=fmt(y), width=fmt(w), height=fmt(h), rx=rx, fill=fill, stroke=stroke,
            stroke_width=sw, stroke_dasharray=dash, opacity=opacity)


def line(x1, y1, x2, y2, stroke=MUTED, sw=1.4, dash="", marker="", start="") -> str:
  return el("line", None, x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), stroke=stroke, stroke_width=sw,
            stroke_dasharray=dash, marker_end=f"url(#{marker})" if marker else "",
            marker_start=f"url(#{start})" if start else "")


def circle(cx, cy, r, fill, stroke="none", sw=0) -> str:
  return el("circle", None, cx=fmt(cx), cy=fmt(cy), r=fmt(r), fill=fill, stroke=stroke, stroke_width=sw)


def text_width(s: str, size: float) -> float:
  """Generous width estimate for Inter: capitals and digits are wider than lower case."""
  return sum((0.68 if c.isupper() or c.isdigit() else 0.3 if c in " .,:;'|/" else 0.55) * size for c in s)


def pill_width(s: str, size=10) -> float:
  return 14 + 0.98 * text_width(s, size)


def pill(x, y, s, fill, size=10, color="#FFFFFF", stroke="none", dash="") -> list[str]:
  """A status tag: rounded rect height 18 with bold text, left edge at x, vertical centre at y."""
  w = pill_width(s, size)
  return [rect(x, y - 9, w, 18, fill=fill, stroke=stroke, rx=9, sw=1.2, dash=dash),
          text(x + w / 2, y + 3.5, s, size=size, fill=color, weight=700, anchor="middle")]


MARKERS = {"safety": SAFETY, "sw": SW, "muted": MUTED, "faint": FAINT}


def svg(width: int, height: int, title: str, desc: str, body: list[str]) -> str:
  defs = "".join(
    f'<marker id="{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" ' +
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for k, c in MARKERS.items())
  defs += ('<pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">' +
           f'<rect width="8" height="8" fill="#FFFFFF"/><line x1="0" y1="0" x2="0" y2="8" stroke="{LINE}" ' +
           'stroke-width="2"/></pattern>')
  defs += ('<pattern id="hatch-amber" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">' +
           f'<rect width="8" height="8" fill="{AMBER_BG}"/><line x1="0" y1="0" x2="0" y2="8" stroke="#FCD34D" ' +
           'stroke-width="1.4"/></pattern>')
  head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" ' +
          f'font-family="{FONT}" role="img">')
  return "\n".join([head, el("title", title), el("desc", desc), f"<defs>{defs}</defs>",
                    rect(0, 0, width, height, fill="#FFFFFF", stroke="none", rx=0, sw=0), *body, "</svg>"]) + "\n"


def header(width: int, number: str, title: str, subtitle: str, ref: str) -> list[str]:
  return [text(40, 44, f"Figure {number} · {title}", size=20, weight=700),
          text(40, 66, subtitle, size=12.5, fill=MUTED),
          text(width - 40, 44, ref, size=11, fill=MUTED, anchor="end"),
          line(40, 82, width - 40, 82, stroke=HAIR, sw=1)]


def wrap(s: str, width_px: float, size=10.5) -> list[str]:
  """Greedy word wrap with a conservative average glyph width."""
  limit = max(8, int(width_px / (0.53 * size)))
  out: list[str] = []
  cur = ""
  for w in s.split():
    if cur and len(cur) + 1 + len(w) > limit:
      out.append(cur)
      cur = w
    else:
      cur = f"{cur} {w}" if cur else w
  if cur:
    out.append(cur)
  return out or [""]


# ---------------------------------------------------------------- source parsing


def split_row(row: str) -> list[str]:
  cells = re.split(r"(?<!\\)\|", row.strip())
  return [c.strip() for c in cells[1:-1]]


def section(md: str, heading: str) -> str:
  if heading not in md:
    raise SystemExit(f"WP-C-01 heading not found: {heading}; update fig_c01_interfaces.py")
  body = md.split(heading, 1)[1]
  return re.split(r"\n#{2,3} ", body, maxsplit=1)[0]


def table(body: str, want: list[str], name: str) -> list[list[str]]:
  rows = [split_row(r) for r in body.splitlines() if r.startswith("|")]
  if not rows or rows[0] != want:
    raise SystemExit(f"WP-C-01 {name} header changed: {rows[0] if rows else None}; update fig_c01_interfaces.py")
  return [r for r in rows[2:] if r]


def plain(s: str) -> str:
  return s.replace("**", "").replace("`", "").strip()


CODE_REF = re.compile(r"`(?:[^`]*\.(?:py|h|cc|c|md))?(?::[0-9, :-]+)?`")


def strip_refs(s: str) -> str:
  """Remove code citations and the punctuation they leave behind."""
  s = CODE_REF.sub("", s)
  s = re.sub(r"\(\s*[,;]?\s*\)", "", s)
  s = re.sub(r"\s*[,;]\s*(?=[,;)]|$)", "", s)
  return re.sub(r"\s{2,}", " ", s).strip(" ;,")


HEX = r"`(0x[0-9A-Fa-f]{2,3})`"
ITEM = re.compile(HEX + r"(?:–" + HEX + r")?\s+([A-Za-z][A-Za-z0-9_]*(?: (?!on\b)[a-z]+)*)")


def depth0(s: str) -> list[bool]:
  """For every character: True when it is outside parentheses."""
  out, d = [], 0
  for ch in s:
    if ch == "(":
      d += 1
    out.append(d == 0)
    if ch == ")":
      d = max(0, d - 1)
  return out


def paren_after(s: str, i: int) -> str:
  """The parenthesised text starting at the first '(' at or after i (only whitespace in between), else ''."""
  j = i
  while j < len(s) and s[j] == " ":
    j += 1
  if j >= len(s) or s[j] != "(":
    return ""
  d = 0
  for k in range(j, len(s)):
    if s[k] == "(":
      d += 1
    elif s[k] == ")":
      d -= 1
      if d == 0:
        return s[j + 1:k]
  return s[j + 1:]


def messages(cell: str) -> list[dict]:
  """Every top-level `0xNNN` (or range) of a §3.4 content cell with its name and first descriptive clause."""
  top = depth0(cell)
  out = []
  for m in ITEM.finditer(cell):
    if not top[m.start()]:
      continue
    name = m.group(3)
    detail = paren_after(cell, m.end())
    rest = cell[m.end():m.end() + 16]
    bus = 1 if rest.startswith(" on bus 1") else 0
    if bus == 1:
      detail = paren_after(cell, m.end() + len(" on bus 1"))
    first = strip_refs(re.split(r";", detail)[0]) if detail else ""
    out.append({"id": m.group(1).upper().replace("0X", "0x"), "end": (m.group(2) or "").upper().replace("0X", "0x"),
                "name": name, "meaning": first, "detail": detail, "bus": bus})
  return out


def counterparts(cell: str) -> dict[str, str]:
  """'EPS (`0x2E4`, `0x191`); cluster (`0x412`)' -> {id: counterpart}."""
  out = {}
  for part in cell.split(";"):
    name = plain(part.split("(", 1)[0])
    for h in re.findall(HEX, part):
      out[h.upper().replace("0X", "0x")] = name
  return out


def interfaces(md: str) -> list[dict]:
  body = section(md, "### 3.4 Interfaces")
  rows = table(body, ["ID", "Interface", "Counterpart", "Direction", "Content (examples)", "Safety relevance"], "§3.4")
  return [{"id": r[0], "name": r[1], "counterpart": r[2], "dir": r[3], "content": r[4], "relevance": r[5]} for r in rows]


def can_rows(md: str) -> dict[str, list[dict]]:
  """IF-01 TX, IF-02 RX (bus 0 and bus 1) messages, with counterparts."""
  ifs = {i["id"]: i for i in interfaces(md)}
  out = {}
  for key in ("IF-01", "IF-02"):
    cp = counterparts(ifs[key]["counterpart"])
    rows = messages(ifs[key]["content"])
    for r in rows:
      r["counterpart"] = cp.get(r["id"], "")
    out[key] = rows
  return out


def aou_status(md: str) -> dict[str, str]:
  body = section(md, "## 7. Assumptions of use (AoU) and external measures")
  rows = table(body, ["ID", "Assumption", "Credited in", "Verification approach", "Status"], "§7")
  return {r[0]: plain(r[4]) for r in rows}


def stock_functions(md: str) -> list[dict]:
  body = section(md, "### 2.2 Vehicle functions replaced, preserved and affected")
  rows = table(body, ["Stock TSS 2.0 function", "With LD-SDA installed", "Basis"], "§2.2")
  out = []
  for fn, cell, basis in rows:
    low = plain(cell).lower()
    if cell.startswith("**Replaced"):
      status = "replaced"
    elif cell.startswith("**Intended to be preserved**") and "not verified" in low:
      status = "preserved"
    elif low.startswith("assumed unaffected") and "not verified" in low:
      status = "assumed"
    elif low.startswith("not modified"):
      status = "unmodified"
    else:
      raise SystemExit(f"WP-C-01 §2.2: cannot classify '{cell}'; update fig_c01_interfaces.py")
    ids = [h.upper().replace("0X", "0x") for h in re.findall(HEX, cell)]
    out.append({"function": fn, "cell": cell, "status": status, "ids": ids, "basis": basis,
                "refs": re.findall(r"\b(?:AOU-\d+|OI-\d+|H-\d+)\b", cell),
                "forwarded": "forwarded" in low, "blocked": "blocked" in low or "intercepts" in low})
  return out


def envelope(md: str) -> dict:
  """§8 rows parsed into numbers; SystemExit when a Value no longer has the expected form."""
  body = section(md, "## 8. Functional and non-functional performance (summary)")
  rows = {r[0]: (r[1], r[2]) for r in table(body, ["Parameter", "Value", "Source"], "§8")}

  def get(param: str, pattern: str):
    if param not in rows:
      raise SystemExit(f"WP-C-01 §8 row '{param}' not found; update fig_c01_interfaces.py")
    m = re.search(pattern, rows[param][0])
    if not m:
      raise SystemExit(f"WP-C-01 §8 '{param}' value '{rows[param][0]}' changed form; update fig_c01_interfaces.py")
    return m, rows[param][0], plain(rows[param][1])

  t, tv, ts = get("Max steering torque request", r"^(\d+) raw \(physical value to be determined, (GAP-\d+)\)")
  r, rv, rs = get("Torque rate", r"^\+(\d+) / −(\d+) raw per (\d+) ms frame; ≤ (\d+) raw per (\d+) ms$")
  la, lav, las = get("Lateral acceleration (controller)", r"^≤ ([\d.]+) m/s² \(roll-compensated\); jerk ≤ ([\d.]+) m/s³$")
  a, av, as_ = get("Acceleration command", r"^−([\d.]+) … \+([\d.]+) m/s²$")
  e, ev, es = get("Minimum engagement speed", r"from standstill \(verify across the trims in scope, (OI-\d+)\)")
  v, vv, vs = get("Max control speed", r"^≈ (\d+) km/h warning \(`?MAX_CTRL_SPEED`?\), no disengage$")
  return {
    "torque": {"max": int(t.group(1)), "gap": t.group(2), "value": tv, "src": ts},
    "rate": {"up": int(r.group(1)), "down": int(r.group(2)), "frame_ms": int(r.group(3)), "window": int(r.group(4)),
             "window_ms": int(r.group(5)), "value": rv, "src": rs},
    "lat": {"accel": float(la.group(1)), "jerk": float(la.group(2)), "accel_s": la.group(1), "jerk_s": la.group(2),
            "value": lav, "src": las},
    "accel": {"min": -float(a.group(1)), "max": float(a.group(2)), "min_s": "−" + a.group(1), "max_s": "+" + a.group(2),
              "value": av, "src": as_},
    "engage": {"min": 0, "oi": e.group(1), "value": ev, "src": es},
    "vmax": {"warn": int(v.group(1)), "value": vv, "src": vs},
  }


# ---------------------------------------------------------------- consistency of the hand-listed facts


def all_src() -> list[tuple[str, str]]:
  out = list(TX_REFUSED["src"]) + list(FORWARD_BLOCKED["src"]) + RX_ARRIVAL_SRC + PANEL_SRC + VERIFY_SRC + RADAR["src"]
  for d in (TX, RX):
    for f in d.values():
      out += f["src"]
  return out


def problems(md: str) -> list[str]:
  """Everything that makes the figures disagree with their sources."""
  out = []
  cache: dict[str, str] = {}
  for path, s in all_src():
    p = ASSURANCE / path
    if path not in cache:
      cache[path] = p.read_text(encoding="utf-8") if p.exists() else ""
    if s not in cache[path]:
      out.append(f"source text no longer in assurance/{path}: {s}")
  rows = can_rows(md)
  tx_ids = [r["id"] for r in rows["IF-01"]]
  rx_ids = [r["id"] for r in rows["IF-02"] if r["bus"] == 0]
  if sorted(tx_ids) != sorted(TX):
    out.append(f"§3.4 IF-01 messages {sorted(tx_ids)} differ from TX facts {sorted(TX)}")
  if sorted(rx_ids) != sorted(RX):
    out.append(f"§3.4 IF-02 bus-0 messages {sorted(rx_ids)} differ from RX facts {sorted(RX)}")
  for key in ("IF-01", "IF-02"):
    for r in rows[key]:
      if not r["counterpart"]:
        out.append(f"§3.4 {key} {r['id']} has no counterpart in the Counterpart cell")
  relay = sorted(k for k, f in TX.items() if f["relay"])
  if relay != sorted(FORWARD_BLOCKED["ids"]):
    out.append(f"relay-checked TX {relay} differ from the camera-side IDs not forwarded {sorted(FORWARD_BLOCKED['ids'])}")
  ifs = {i["id"] for i in interfaces(md)}
  if not {"IF-01", "IF-02", "IF-03", "IF-04"} <= ifs:
    out.append("§3.4 lost one of IF-01 … IF-04")
  return out


# ---------------------------------------------------------------- Figure 3-3 CAN interface map

W = 1280
TX0 = 300            # table left (message chip)
X_DIR0, X_DIR1 = 526, 562
X_IF = 572
X_MEAN = 622
X_CHECK = 806
X_CP = 1040
LH = 13              # line step inside a row


def hex_chip(x, y, s, fill, w=66, color="#FFFFFF", stroke="none", dash="") -> list[str]:
  return [rect(x, y, w, 20, fill=fill, stroke=stroke, rx=5, sw=1.2, dash=dash),
          text(x + w / 2, y + 14, s, size=10.5, fill=color, weight=700, anchor="middle", family=MONO)]


def band(y, s, fg, bg) -> list[str]:
  return [rect(TX0 - 10, y, W - 40 - (TX0 - 10), 26, fill=bg, stroke="none", rx=6),
          text(TX0, y + 17, s, size=11.5, fill=fg, weight=700)]


def trace_pills(x, y, ids: list[str]) -> list[str]:
  out = []
  for t in ids:
    out += pill(x, y, t, GREY_BG, size=9, color=MUTED, stroke=LINE)
    x += pill_width(t, 9) + 4
  return out


def msg_row(y: float, r: dict, kind: str, check: list[tuple[str, str, str]], mark: list[str], trace: list[str]) -> tuple[list[str], float]:
  """One message row. check: (text, colour, style) lines of the panda column; mark: its symbol. Returns (svg, height)."""
  out = []
  chip_w = 66 if not r.get("end") else 128
  label = r["id"] if not r.get("end") else f"{r['id']}–{r['end']}"
  out += hex_chip(TX0, y + 4, label, SAFETY if kind == "tx" else SW, w=chip_w)
  out.append(text(TX0 + chip_w + 8, y + 18, r["name"], size=11, weight=600, family=MONO if r["name"].isupper() else ""))
  if kind == "tx":
    out.append(line(X_DIR0, y + 14, X_DIR1, y + 14, stroke=SAFETY, sw=2, marker="safety"))
  else:
    out.append(line(X_DIR1, y + 14, X_DIR0, y + 14, stroke=SW, sw=2, marker="sw"))
  out.append(text(X_IF, y + 18, r["if"], size=10.5, fill=MUTED, family=MONO))
  mean = wrap(r["meaning"], X_CHECK - X_MEAN - 12, size=10.5)
  for i, s in enumerate(mean):
    out.append(text(X_MEAN, y + 18 + LH * i, s, size=10.5, fill=MUTED))
  out += mark
  for i, (s, c, st) in enumerate(check):
    out.append(text(X_CHECK + 18, y + 18 + LH * i, s, size=10.5 if i == 0 else 9.5, fill=c, style=st))
  cp = wrap(r["counterpart"], W - 40 - X_CP, size=10.5)
  for i, s in enumerate(cp):
    out.append(text(X_CP, y + 18 + LH * i, s, size=10.5))
  n = max(len(mean), len(check), len(cp))
  h = 18 + LH * (n - 1) + 12
  if trace:
    inline = X_CP + text_width(cp[0], 10.5) + 10
    if len(cp) == 1 and inline + sum(pill_width(t, 9) + 4 for t in trace) <= W - 40:
      out += trace_pills(inline, y + 14, trace)
    else:
      ty = y + 18 + LH * (len(cp) - 1) + 17
      out += trace_pills(X_CP, ty, trace)
      h = max(h, ty - y + 9 + 6)
  return out, max(h, 30)


def figure_3_3(md: str) -> str:
  rows = can_rows(md)
  ifs = {i["id"]: i for i in interfaces(md)}
  b: list[str] = []
  b += header(W, "3-3", "CAN interface map",
              "Every CAN message of §3.4 on its bus, with direction, interface, what the panda safety mode checks and the counterpart.",
              "WP-C-01 §3.4")
  b.append(text(W - 40, 66, "reference build, openpilot longitudinal", size=11, fill=MUTED, anchor="end"))
  top = 112
  for x, s in ((TX0, "MESSAGE"), (X_DIR0, "DIR"), (X_IF, "IF"), (X_MEAN, "MEANING (§3.4)"), (X_CHECK, "PANDA SAFETY MODE"),
               (X_CP, "COUNTERPART · TRACE")):
    b.append(text(x, top, s, size=10.5, fill=MUTED, weight=700))
  y = top + 12
  bands: dict[str, float] = {}

  # --- bus 0 TX
  bands["tx"] = y
  b += band(y, "BUS 0 · VEHICLE CAN, CAR SIDE · transmitted by the item (IF-01, " + strip_refs(ifs["IF-01"]["relevance"]) + ")",
            SAFETY, SAFETY_BG)
  y += 32
  for r in rows["IF-01"]:
    r["if"] = "IF-01"
    f = TX[r["id"]]
    parts = ([f["check"]] if f["check"] != "whitelist only" else []) + (["relay check"] if f["relay"] else [])
    check = [(" · ".join(parts) if parts else "whitelist only", SAFETY, "")]
    if f["ref"]:
      check.append(("reference build: " + f["ref"], AMBER, ""))
    if r["id"] in LONG_ONLY:
      check.append(("openpilot longitudinal only", MUTED, ""))
    if not f["sent"]:
      check.append(("not sent by the reference car", FAINT, "italic"))
    mark = [rect(X_CHECK, y + 8, 12, 12, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4)]
    out, h = msg_row(y, r, "tx", check, mark, f["trace"])
    b += out
    y += h
  b.append(text(TX0, y + 12, TX_REFUSED["text"], size=10, fill=MUTED, style="italic"))
  y += 24

  # --- bus 0 RX
  b += band(y, "BUS 0 · VEHICLE CAN, CAR SIDE · received (IF-02, " + strip_refs(ifs["IF-02"]["relevance"]).lower() + ")",
            SW, SW_BG)
  y += 32
  bus1 = []
  for r in rows["IF-02"]:
    r["if"] = "IF-02"
    if r["bus"] == 1:
      bus1.append(r)
      continue
    f = RX[r["id"]]
    s = f"rate {f['rate']} Hz" + (" · checksum" if f["checksum"] else "")
    if f["ref_only"]:
      mark = [circle(X_CHECK + 6, y + 14, 5.5, "#FFFFFF", AMBER, 2)]
      check = [(s, AMBER, ""), ("reference build only;", AMBER, ""), ("upstream builds: host only", AMBER, "")]
    else:
      mark = [circle(X_CHECK + 6, y + 14, 5.5, SW)]
      check = [(s, SW, "")]
    out, h = msg_row(y, r, "rx", check, mark, f["trace"])
    b += out
    y += h
  y += 4

  # --- bus 1
  b += band(y, "BUS 1 · RADAR CAN · received (IF-02)", SW, SW_BG)
  y += 32
  for r in bus1:
    if not r["meaning"]:
      r["meaning"] = RADAR["meaning"]
    mark = [circle(X_CHECK + 6, y + 14, 5.5, "#FFFFFF", FAINT, 2)]
    out, h = msg_row(y, r, "rx", [("host only (no RX check)", MUTED, "")], mark, [])
    b += out
    y += h
  y += 4

  # --- bus 2
  if3 = ifs["IF-03"]
  b += band(y, "BUS 2 · CAMERA SIDE · " + plain(if3["content"]).lower() + " (IF-03)", SW, SW_BG)
  y += 32
  bands["bus2"] = y
  b += hex_chip(TX0, y + 4, "all other IDs", "#FFFFFF", w=104, color=SW, stroke=SW)
  b.append(text(TX0 + 112, y + 18, "incl. PCS outputs", size=11, weight=600))
  b.append(line(X_DIR0, y + 14, X_DIR1, y + 14, stroke=SW, sw=2, marker="sw"))
  b.append(text(X_IF, y + 18, "IF-03", size=10.5, fill=MUTED, family=MONO))
  b.append(text(X_MEAN, y + 18, "stock camera → car, unchanged", size=10.5, fill=MUTED))
  b.append(line(X_CHECK, y + 14, X_CHECK + 12, y + 14, stroke=SW, sw=2))
  b.append(text(X_CHECK + 18, y + 18, "forwarded 2 → 0", size=10.5, fill=SW))
  b.append(text(X_CP, y + 18, "forward camera → car side", size=10.5))
  b += trace_pills(W - 40 - pill_width("AOU-04", 9), y + 14, ["AOU-04"])
  y += 32
  ids = FORWARD_BLOCKED["ids"]
  b += hex_chip(TX0, y + 4, " ".join(ids), "url(#hatch)", w=212, color=MUTED, stroke=FAINT, dash="4 3")
  b.append(line(X_DIR0, y + 14, X_DIR1 - 8, y + 14, stroke=FAINT, sw=2))
  b.append(line(X_DIR1 - 6, y + 6, X_DIR1 - 6, y + 22, stroke=RED, sw=3))
  b.append(text(X_IF, y + 18, "IF-03", size=10.5, fill=MUTED, family=MONO))
  b.append(text(X_MEAN, y + 18, "stock LKA / ACC commands", size=10.5, fill=MUTED))
  b.append(rect(X_CHECK, y + 8, 12, 12, fill="url(#hatch)", stroke=FAINT, rx=3, sw=1.2))
  b.append(text(X_CHECK + 18, y + 18, "not forwarded", size=10.5, fill=SAFETY))
  b.append(text(X_CHECK + 18, y + 31, "(the relay-checked TX above)", size=9.5, fill=MUTED))
  b.append(text(X_CP, y + 18, "replaced by the item's TX", size=10.5))
  b += trace_pills(W - 40 - pill_width("TSR-704", 9), y + 14, ["TSR-704"])
  y += 42
  bands["bus2_end"] = y

  # --- not CAN
  b.append(rect(TX0 - 10, y, W - 40 - (TX0 - 10), 26, fill=CHIP, stroke="none", rx=6))
  b.append(text(TX0, y + 17, "NOT CAN · for completeness", size=11.5, fill=MUTED, weight=700))
  y += 32
  others = [i for i in interfaces(md) if i["id"] not in ("IF-01", "IF-02", "IF-03", "IF-04")]
  s = " · ".join(f"{i['id']} {plain(i['name'])}" for i in others)
  lines_ = wrap(s, X_CP - TX0 - 20, size=10.5)
  for i, ln in enumerate(lines_):
    b.append(text(TX0, y + 16 + 14 * i, ln, size=10.5, fill=INK))
  b.append(text(X_CP, y + 16, "see Figure 3-2", size=10.5, fill=MUTED))
  y += 16 + 14 * len(lines_)
  table_bottom = y

  # --- left panel: item side
  px, pw = 40, 236
  ptop = top - 8
  pbot = table_bottom + 4
  b.append(rect(px, ptop, pw, pbot - ptop, fill="#FFFBEB", stroke=SCOPE, dash="10 5", rx=12, sw=1.5))
  b += pill(px + 16, ptop, "ITEM · LD-SDA", SCOPE, size=10.5)
  ix, iw = px + 14, pw - 28
  y1 = ptop + 26
  b.append(rect(ix, y1, iw, 92, fill="#FFFFFF", stroke=BORDER, rx=10, sw=1.4))
  b.append(text(ix + 12, y1 + 22, "E-01 SoC software", size=12.5, weight=700))
  b.append(text(ix + 12, y1 + 40, "card builds the TX frames;", size=10.5, fill=MUTED))
  b.append(text(ix + 12, y1 + 54, "pandad passes CAN streams;", size=10.5, fill=MUTED))
  b.append(text(ix + 12, y1 + 68, "radar tracks: host only", size=10.5, fill=MUTED))
  if4 = ifs["IF-04"]
  codes = re.findall(r"`(0x[0-9a-f]{2})` ([a-z-]+(?: [a-z-]+)?)", if4["content"])
  y2 = y1 + 92
  b.append(line(ix + 34, y2 + 2, ix + 34, y2 + 58, stroke=MUTED, sw=2, marker="muted", start="muted"))
  b += pill(ix + 48, y2 + 16, f"IF-04 · {if4['dir']}", MUTED, size=9.5)
  for i, (c, n) in enumerate(codes[:2]):
    b.append(text(ix + 48, y2 + 38 + 12 * i, f"{c} {n}", size=9.5, fill=MUTED, family=MONO))
  y3 = y2 + 60
  # E-05 sits level with the bus-2 rows; E-03 fills the space above it
  h5 = 78
  y5 = max(bands["bus2"] - 8, y3 + 330)
  h3 = y5 - 30 - y3
  b.append(rect(ix, y3, iw, h3, fill=SAFETY_BG, stroke=SAFETY, rx=10, sw=1.8))
  b.append(text(ix + 12, y3 + 22, "E-03 panda safety MCU", size=12.5, weight=700))
  b.append(text(ix + 12, y3 + 39, "Toyota safety mode · envelope B‡", size=10.5, fill=MUTED))
  boxes = [("TX hook", ["whitelist, relay check and", "content limits, per message"]),
           ("RX checks", ["rate and checksum per", "message (● in the table)"]),
           ("Forwarding 2 → 0", ["camera traffic passes except", "the relay-checked messages"])]
  ports = (("bus 0", SAFETY, "car side"), ("bus 1", SW, "radar"), ("bus 2", SW, "camera side"))
  py = y3 + h3 - 22 - 24 * (len(ports) - 1)
  gap = (py - 20 - (y3 + 52) - 56 * len(boxes)) / (len(boxes) - 1)
  if gap < 6:
    raise SystemExit("Figure 3-3: E-03 box too short; adjust the layout")
  gap = min(gap, 40)
  by = y3 + 52
  for t, ls in boxes:
    b.append(rect(ix + 10, by, iw - 20, 56, fill="#FFFFFF", stroke=SAFETY_SOFT, rx=8, sw=1.1))
    b.append(text(ix + 20, by + 18, t, size=11, fill=SAFETY, weight=700))
    for i, s in enumerate(ls):
      b.append(text(ix + 20, by + 33 + 13 * i, s, size=10, fill=MUTED))
    by += 56 + gap
  for i, (s, c, lab) in enumerate(ports):
    b += pill(ix + iw - 64, py + 24 * i, s, c, size=10)
    b.append(text(ix + 12, py + 24 * i + 4, lab, size=10, fill=MUTED))
  # bus 2 through the relay
  b.append(line(ix + iw / 2, y3 + h3, ix + iw / 2, y5, stroke=SW, sw=2, marker="sw", start="sw"))
  b.append(text(ix + iw / 2 + 14, y3 + h3 + 19, "bus 2 via the relay", size=10, fill=SW))
  b.append(rect(ix, y5, iw, h5, fill="#FFFFFF", stroke=BORDER, rx=10, sw=1.4))
  b.append(text(ix + 12, y5 + 22, "E-05 harness relay", size=12.5, weight=700))
  b.append(text(ix + 12, y5 + 40, "energised: camera ↔ panda bus 2", size=10.5, fill=MUTED))
  b.append(text(ix + 12, y5 + 56, "released: camera ↔ car (AOU-13)", size=10.5, fill=MUTED))
  if y5 + h5 + 10 > pbot:
    raise SystemExit("Figure 3-3 left panel taller than the table; adjust the layout")

  # --- legend
  ly = pbot + 34
  b.append(line(40, ly - 18, W - 40, ly - 18, stroke=HAIR, sw=1))
  x = 40
  b.append(rect(x, ly - 10, 22, 12, fill=SAFETY, stroke="none", rx=3))
  b.append(text(x + 28, ly, "transmitted by the item", size=11, fill=MUTED))
  x += 172
  b.append(rect(x, ly - 10, 22, 12, fill=SW, stroke="none", rx=3))
  b.append(text(x + 28, ly, "received", size=11, fill=MUTED))
  x += 90
  b.append(rect(x, ly - 10, 12, 12, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  b.append(text(x + 18, ly, "TX check (whitelisted)", size=11, fill=MUTED))
  x += 150
  b.append(circle(x + 6, ly - 4, 5.5, SW))
  b.append(text(x + 18, ly, "RX check in every build", size=11, fill=MUTED))
  x += 158
  b.append(circle(x + 6, ly - 4, 5.5, "#FFFFFF", AMBER, 2))
  b.append(text(x + 18, ly, "RX check in the reference build only", size=11, fill=MUTED))
  x += 222
  b.append(circle(x + 6, ly - 4, 5.5, "#FFFFFF", FAINT, 2))
  b.append(text(x + 18, ly, "read by the host only", size=11, fill=MUTED))
  x += 148
  b.append(rect(x, ly - 10, 22, 12, fill="url(#hatch)", stroke=FAINT, rx=3, dash="4 3"))
  b.append(text(x + 28, ly, "not forwarded", size=11, fill=MUTED))
  note = ("Checks as implemented in toyota.h at the opendbc pin; none is verified on the reference vehicle (the RX rates of " +
          "0x262 and 0x1D3 are to be measured, WP-S-05 OI-7). Messages, names and counterparts: §3.4 table. Checks: WP-S-02, " +
          "WP-S-05 §5, WP-W-05, WP-W-09, DN-01, each named in the generator. Trace pills: requirement, AoU or function the message serves.")
  nl = wrap(note, W - 80, size=10.5)
  for i, s in enumerate(nl):
    b.append(text(40, ly + 24 + 14 * i, s, size=10.5, fill=MUTED))
  height = int(ly + 24 + 14 * len(nl) + 8)

  tx_desc = "; ".join(f"{r['id']} {r['name']} to {r['counterpart']}" for r in rows["IF-01"])
  rx_desc = "; ".join(f"{r['id']} {r['name']}" + (" (reference build only)" if RX.get(r["id"], {}).get("ref_only") else "")
                      for r in rows["IF-02"])
  desc = ("CAN interface map of LD-SDA from WP-C-01 §3.4. Bus 0 transmitted by the item (IF-01): " + tx_desc + ". " +
          "Received (IF-02): " + rx_desc + "; the radar tracks on bus 1 are read by the host only. Bus 2 (IF-03): camera " +
          "frames are forwarded to the car except " + ", ".join(ids) + ", which the item replaces. For each message the " +
          "panda safety mode check is shown: TX whitelist, relay check and content limits; RX rate and checksum, with " +
          "0x262 and 0x1D3 checked only in the reference build. Nothing is shown as verified.")
  return svg(W, height, "Figure 3-3 · CAN interface map", desc, b)


# ---------------------------------------------------------------- Figure 2-1 stock functions

STATUS = {
  "replaced": ("Replaced", SAFETY, "#FFFFFF", SAFETY, ""),
  "preserved": ("Intended to be preserved · not verified", AMBER_BG, AMBER, AMBER, "4 3"),
  "assumed": ("Assumed unaffected · not verified", "#FFFFFF", MUTED, FAINT, "4 3"),
  "unmodified": ("Not modified", "#FFFFFF", MUTED, BORDER, ""),
}


def figure_2_1(md: str) -> str:
  rows = stock_functions(md)
  aou = aou_status(md)
  b: list[str] = []
  b += header(W, "2-1", "Stock TSS 2.0 functions with LD-SDA installed",
              "What happens to each stock function of the reference vehicle when the item is installed, by what mechanism, " +
              "and what it rests on.", "WP-C-01 §2.2")
  X_S, W_S = 40, 270
  X_W, W_W = 352, 560
  X_R = 932
  top = 112
  b.append(text(X_S, top, "STOCK TSS 2.0 FUNCTION", size=10.5, fill=MUTED, weight=700))
  b.append(text(X_W, top, "WITH LD-SDA INSTALLED", size=10.5, fill=MUTED, weight=700))
  b.append(text(X_R, top, "RESTS ON · BASIS", size=10.5, fill=MUTED, weight=700))
  y = top + 14
  for r in rows:
    label, fill, color, stroke, dash = STATUS[r["status"]]
    rest = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", r["cell"])
    rest = re.sub(r"^\*\*[^*]*\*\*\.?|^(Assumed unaffected|Not modified)\.", "", rest)
    rest = re.split(r"\*\*Not verified\*\*|\bNot verified\b", rest)[0]
    rest = plain(rest).strip(" .—")
    if rest.startswith("(") and rest.endswith(")"):
      rest = rest[1:-1]
    m_lines = wrap(rest, W_W - 28, size=10.5) if rest else []
    f_lines = wrap(r["function"], W_S - 28, size=12)
    chips = r["ids"]
    h = max(28 + 15 * len(f_lines), 48 + 14 * len(m_lines) + (30 if chips or r["forwarded"] else 0), 64)
    # stock function
    b.append(rect(X_S, y, W_S, h, fill=GREY_BG, stroke=FAINT, rx=10, sw=1.3))
    for i, s in enumerate(f_lines):
      b.append(text(X_S + 14, y + 24 + 15 * i, s, size=12, weight=700))
    b.append(text(X_S + 14, y + h - 12, "stock vehicle", size=10, fill=MUTED))
    # arrow
    b.append(line(X_S + W_S + 4, y + h / 2, X_W - 6, y + h / 2, stroke=MUTED, sw=1.6, marker="muted"))
    # with LD-SDA
    box_dash = dash if r["status"] in ("preserved", "assumed") else ""
    box_stroke = stroke if r["status"] != "unmodified" else BORDER
    b.append(rect(X_W, y, W_W, h, fill="#FFFFFF" if r["status"] != "preserved" else AMBER_BG, stroke=box_stroke,
                  rx=10, sw=1.5, dash=box_dash))
    b += pill(X_W + 14, y + 20, label, fill, size=10, color=color, stroke=stroke if fill == "#FFFFFF" or r["status"] == "preserved" else "none",
              dash=dash)
    for i, s in enumerate(m_lines):
      b.append(text(X_W + 14, y + 48 + 14 * i, s, size=10.5, fill=INK))
    if not m_lines:
      b.append(text(X_W + 14, y + 48, "no mechanism stated in §2.2", size=10.5, fill=FAINT, style="italic"))
    cy = y + 48 + 14 * len(m_lines) + 6
    cx = X_W + 14
    if chips:
      for c in chips:
        b += hex_chip(cx, cy, c, "url(#hatch)", w=58, color=MUTED, stroke=FAINT, dash="4 3")
        cx += 64
      b.append(line(cx + 2, cy + 10, cx + 30, cy + 10, stroke=FAINT, sw=2))
      b.append(line(cx + 32, cy + 2, cx + 32, cy + 18, stroke=RED, sw=3))
      b.append(text(cx + 42, cy + 14, "from the camera: blocked from the car side", size=10, fill=MUTED))
    elif r["forwarded"]:
      b += hex_chip(cx, cy, "camera PCS messages", "#FFFFFF", w=150, color=SW, stroke=SW)
      b.append(line(cx + 156, cy + 10, cx + 196, cy + 10, stroke=SW, sw=2, marker="sw"))
      b.append(text(cx + 204, cy + 14, "forwarded to the car (IF-03)", size=10, fill=SW))
    # rests on
    ry = y + 14
    rx_ = X_R
    for ref in r["refs"]:
      if ref.startswith("AOU-"):
        st = aou.get(ref, "?")
        s = f"{ref} · {st.lower()}"
        b += pill(rx_, ry, s, AMBER_BG, size=9.5, color=AMBER, stroke=AMBER, dash="4 3")
      elif ref.startswith("OI-"):
        s = f"{ref} · open"
        b += pill(rx_, ry, s, "#FFFFFF", size=9.5, color=MUTED, stroke=FAINT, dash="4 3")
      else:
        s = f"hazard {ref}"
        b += pill(rx_, ry, s, GREY_BG, size=9.5, color=MUTED, stroke=LINE)
      rx_ += pill_width(s, 9.5) + 6
    basis = [s.strip() for s in r["basis"].split(";")] if r["basis"].strip() not in ("—", "") else []
    by = y + (34 if r["refs"] else 18)
    if not basis:
      b.append(text(X_R, by + 4, "no basis given in §2.2", size=10, fill=FAINT, style="italic"))
    for i, s in enumerate(basis):
      b.append(text(X_R, by + 4 + 13 * i, plain(s), size=10, fill=MUTED, family=MONO))
    y += h + 10
  # legend
  ly = y + 24
  b.append(line(40, ly - 18, W - 40, ly - 18, stroke=HAIR, sw=1))
  x = 40
  for key in ("replaced", "preserved", "assumed", "unmodified"):
    label, fill, color, stroke, dash = STATUS[key]
    b += pill(x, ly - 4, label, fill, size=9.5, color=color, stroke=stroke if fill != SAFETY else "none", dash=dash)
    x += pill_width(label, 9.5) + 12
  b.append(rect(x + 6, ly - 12, 22, 14, fill="url(#hatch)", stroke=FAINT, rx=3, dash="4 3"))
  b.append(text(x + 34, ly, "blocked message", size=11, fill=MUTED))
  b.append(text(40, ly + 24, "Status words, mechanism and references are the §2.2 table's; the AoU status is the §7 Status column. " +
                "Nothing here is verified; “Replaced” states the design, not a test result.", size=10.5, fill=MUTED))
  height = int(ly + 44)
  desc = ("Stock TSS 2.0 functions of the reference vehicle with LD-SDA installed, from WP-C-01 §2.2: " +
          "; ".join(f"{r['function']}: {STATUS[r['status']][0]}" for r in rows) +
          ". Blocked camera messages, forwarded PCS messages, the assumptions and open items each row rests on, and the basis " +
          "are shown. Nothing is shown as verified.")
  return svg(W, height, "Figure 2-1 · Stock TSS 2.0 functions with LD-SDA installed", desc, b)


# ---------------------------------------------------------------- Figure 8-1 actuation envelope

PW, PH = 384, 224
GX = [40, 448, 856]


def axis(x0, x1, y, lo, hi, ticks, unit="", fmt_=fmt) -> list[str]:
  out = [line(x0, y, x1, y, stroke=FAINT, sw=1)]
  for t in ticks:
    tx = x0 + (x1 - x0) * (t - lo) / (hi - lo)
    out.append(line(tx, y, tx, y + 4, stroke=FAINT, sw=1))
    out.append(text(tx, y + 16, fmt_(t).replace("-", "−"), size=10, fill=MUTED, anchor="middle"))
  if unit:
    out.append(text(x1, y + 30, unit, size=10, fill=MUTED, anchor="end"))
  return out


def sx(x0, x1, lo, hi, v):
  return x0 + (x1 - x0) * (v - lo) / (hi - lo)


def panel(x, y, title, value, src) -> list[str]:
  out = [rect(x, y, PW, PH, fill="#FFFFFF", stroke=LINE, rx=10, sw=1.3),
         text(x + 16, y + 24, title, size=12.5, weight=700)]
  out += pill(x + PW - 16 - pill_width("inherited · not verified", 9), y + 19, "inherited · not verified", AMBER_BG, size=9,
              color=AMBER, stroke=AMBER, dash="4 3")
  for i, s in enumerate(wrap(value, PW - 32, size=10.5)[:2]):
    out.append(text(x + 16, y + 44 + 13 * i, s, size=10.5, fill=MUTED))
  out.append(text(x + 16, y + PH - 12, src, size=9.5, fill=FAINT, family=MONO))
  return out


def figure_8_1(md: str) -> str:
  e = envelope(md)
  b: list[str] = []
  b += header(W, "8-1", "Inherited actuation envelope",
              "The limits that define the actuation envelope today, as the §8 table states them. They are inherited from " +
              "upstream; targets are in WP-S-01.", "WP-C-01 §8")
  y0, y1 = 104, 104 + PH + 18
  # 1 torque
  x = GX[0]
  t = e["torque"]
  b += panel(x, y0, "Max steering torque request", plain(t["value"]), t["src"])
  ax0, ax1 = x + 24, x + PW - 30
  by = y0 + 92
  b.append(rect(ax0, by, sx(ax0, ax1, 0, 1800, t["max"]) - ax0, 18, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  lx = sx(ax0, ax1, 0, 1800, t["max"])
  b.append(line(lx, by - 8, lx, by + 26, stroke=SAFETY, sw=2))
  b.append(text(lx - 6, by - 10, f"|request| ≤ {t['max']} raw", size=11, fill=SAFETY, weight=700, anchor="end"))
  b += axis(ax0, ax1, by + 26, 0, 1800, [0, 500, 1000, 1500], "raw units")
  py = by + 62
  b.append(rect(ax0, py, ax1 - ax0, 20, fill="url(#hatch-amber)", stroke=AMBER, rx=3, sw=1.2, dash="4 3"))
  b.append(text((ax0 + ax1) / 2, py + 14, f"N·m at the wheel: to be determined ({t['gap']})", size=10.5, fill=AMBER,
                weight=700, anchor="middle"))
  # 2 torque rate
  x = GX[1]
  r = e["rate"]
  b += panel(x, y0, "Torque rate", plain(r["value"]), r["src"])
  ax0, ax1 = x + 24, x + PW - 24
  z = sx(ax0, ax1, -30, 30, 0)
  by = y0 + 88
  b.append(text(ax0, by - 6, f"per {r['frame_ms']} ms frame", size=10, fill=MUTED, weight=600))
  up = sx(ax0, ax1, -30, 30, r["up"])
  dn = sx(ax0, ax1, -30, 30, -r["down"])
  b.append(rect(z, by, up - z, 16, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  b.append(rect(dn, by, z - dn, 16, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  b.append(text(up - 6, by + 12, f"+{r['up']} up", size=10.5, fill=SAFETY, weight=700, anchor="end"))
  b.append(text(dn + 6, by + 12, f"−{r['down']} down", size=10.5, fill=SAFETY, weight=700))
  b.append(line(z, by - 4, z, by + 20, stroke=INK, sw=1))
  b += axis(ax0, ax1, by + 22, -30, 30, [-30, -15, 0, 15, 30], "raw / frame")
  wy = by + 66
  b.append(text(ax0, wy - 6, f"per {r['window_ms']} ms window", size=10, fill=MUTED, weight=600))
  ww = sx(ax0, ax1, 0, 600, r["window"])
  b.append(rect(ax0, wy, ww - ax0, 14, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  b.append(text(ww + 6, wy + 11, f"≤ {r['window']} raw", size=10.5, fill=SAFETY, weight=700))
  b += axis(ax0, ax1, wy + 18, 0, 600, [0, 150, 300, 450, 600], "raw / window")
  # 3 lateral
  x = GX[2]
  la = e["lat"]
  b += panel(x, y0, "Lateral acceleration (controller)", plain(la["value"]), la["src"])
  ax0, ax1 = x + 24, x + PW - 24
  for i, (name, v, vs, hi, ticks, unit) in enumerate((("lateral acceleration", la["accel"], la["accel_s"], 4, [0, 1, 2, 3, 4], "m/s²"),
                                                      ("jerk", la["jerk"], la["jerk_s"], 6, [0, 2, 4, 6], "m/s³"))):
    by = y0 + 88 + 66 * i
    b.append(text(ax0, by - 6, name, size=10, fill=MUTED, weight=600))
    vx = sx(ax0, ax1, 0, hi, v)
    b.append(rect(ax0, by, vx - ax0, 14, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
    b.append(text(vx + 6, by + 11, f"≤ {vs} {unit}", size=10.5, fill=SAFETY, weight=700))
    b += axis(ax0, ax1, by + 18, 0, hi, ticks, "")
  # 4 accel
  x = GX[0]
  a = e["accel"]
  b += panel(x, y1, "Acceleration command", plain(a["value"]), a["src"])
  ax0, ax1 = x + 24, x + PW - 24
  by = y1 + 96
  lo_x, hi_x, z = sx(ax0, ax1, -4, 3, a["min"]), sx(ax0, ax1, -4, 3, a["max"]), sx(ax0, ax1, -4, 3, 0)
  b.append(rect(lo_x, by, hi_x - lo_x, 22, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  b.append(line(z, by - 6, z, by + 28, stroke=INK, sw=1))
  b.append(text(lo_x, by - 8, f"{a['min_s']} m/s²", size=11, fill=SAFETY, weight=700))
  b.append(text(hi_x, by - 8, f"{a['max_s']} m/s²", size=11, fill=SAFETY, weight=700, anchor="end"))
  b.append(text((lo_x + z) / 2, by + 15, "braking", size=10, fill=MUTED, anchor="middle"))
  b.append(text((z + hi_x) / 2, by + 15, "accelerating", size=10, fill=MUTED, anchor="middle"))
  b += axis(ax0, ax1, by + 28, -4, 3, [-4, -3, -2, -1, 0, 1, 2, 3], "m/s²")
  # 5 speed
  x = GX[1]
  v, en = e["vmax"], e["engage"]
  b += panel(x, y1, "Engagement and control speed", "from standstill (" + en["oi"] + "); " + plain(v["value"]),
             en["src"] + " · " + v["src"].split(";")[0])
  ax0, ax1 = x + 24, x + PW - 24
  by = y1 + 96
  wx = sx(ax0, ax1, 0, 180, v["warn"])
  b.append(rect(ax0, by, wx - ax0, 22, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  b.append(rect(wx, by, ax1 - wx, 22, fill="url(#hatch)", stroke=FAINT, rx=3, sw=1.2, dash="4 3"))
  b.append(line(wx, by - 8, wx, by + 28, stroke=AMBER, sw=2))
  b.append(text(wx - 5, by - 10, f"≈ {v['warn']} km/h: warning", size=10.5, fill=AMBER, weight=700, anchor="end"))
  b.append(text(wx + 5, by - 10, "no disengage", size=10, fill=MUTED))
  b.append(text(ax0 + 6, by + 15, "engage from 0 (verify, " + en["oi"] + ")", size=10, fill=SAFETY))
  b += axis(ax0, ax1, by + 28, 0, 180, [0, 30, 60, 90, 120, 150, 180], "km/h")
  # 6 note
  x = GX[2]
  b.append(rect(x, y1, PW, PH, fill=CHIP, stroke=LINE, rx=10, sw=1.2, dash="4 3"))
  b.append(text(x + 16, y1 + 24, "Reading this figure", size=12.5, weight=700))
  note = ("Each bar is the limit as the §8 Value cell states it, drawn from the numbers in that cell. The limits are " +
          f"inherited code limits, not verified on the reference vehicle. The physical steering torque is unknown ({t['gap']}); " +
          "its scale is hatched, not drawn as a number. Above the control-speed warning the item warns but does not disengage.")
  for i, s in enumerate(wrap(note, PW - 32, size=10.5)):
    b.append(text(x + 16, y1 + 48 + 15 * i, s, size=10.5, fill=MUTED))
  # legend
  ly = y1 + PH + 40
  b.append(line(40, ly - 18, W - 40, ly - 18, stroke=HAIR, sw=1))
  b.append(rect(40, ly - 10, 22, 12, fill=SAFETY_BG, stroke=SAFETY, rx=3, sw=1.4))
  b.append(text(68, ly, "within the inherited limit", size=11, fill=MUTED))
  b.append(rect(240, ly - 10, 22, 12, fill="url(#hatch-amber)", stroke=AMBER, rx=3, dash="4 3"))
  b.append(text(268, ly, "to be determined (placeholder)", size=11, fill=MUTED))
  b.append(rect(470, ly - 10, 22, 12, fill="url(#hatch)", stroke=FAINT, rx=3, dash="4 3"))
  b.append(text(498, ly, "warning only, control continues", size=11, fill=MUTED))
  b += pill(700, ly - 4, "inherited · not verified", AMBER_BG, size=9, color=AMBER, stroke=AMBER, dash="4 3")
  b.append(text(840, ly, "Source: §8 table (Value and Source columns)", size=11, fill=MUTED))
  height = int(ly + 22)
  desc = (f"Small multiples of the inherited actuation envelope from WP-C-01 §8: steering torque request at most {t['max']} raw " +
          f"(physical value to be determined, {t['gap']}); torque rate +{r['up']} / −{r['down']} raw per {r['frame_ms']} ms frame " +
          f"and at most {r['window']} raw per {r['window_ms']} ms; lateral acceleration at most {la['accel_s']} m/s² and jerk " +
          f"at most {la['jerk_s']} m/s³; acceleration command {a['min_s']} to {a['max_s']} m/s²; engagement from " +
          f"standstill ({en['oi']}) and a warning at about {v['warn']} km/h without disengagement. All inherited, none verified.")
  return svg(W, height, "Figure 8-1 · Inherited actuation envelope", desc, b)


# ---------------------------------------------------------------- build / check

OUTPUTS = {
  "fig-c01-2-1-stock-functions.svg": figure_2_1,
  "fig-c01-3-3-can-interface-map.svg": figure_3_3,
  "fig-c01-8-1-actuation-envelope.svg": figure_8_1,
}


def build(md: str | None = None) -> dict[str, str]:
  md = md if md is not None else SOURCE.read_text(encoding="utf-8")
  return {name: fn(md) for name, fn in OUTPUTS.items()}


def main(argv: list[str]) -> int:
  md = SOURCE.read_text(encoding="utf-8")
  issues = problems(md)
  if issues:
    for s in issues:
      print(s, file=sys.stderr)
    print("review the figure data in fig_c01_interfaces.py against WP-C-01 and regenerate", file=sys.stderr)
    return 1
  outputs = build(md)
  if "--check" in argv:
    stale = [n for n, t in outputs.items() if not (HERE / n).exists() or (HERE / n).read_text(encoding="utf-8") != t]
    for n in stale:
      print(f"{(HERE / n).relative_to(REPO)} is stale; run fig_c01_interfaces.py", file=sys.stderr)
    if not stale:
      print(f"WP-C-01 interface figures: {len(outputs)} up to date")
    return 1 if stale else 0
  for n, t in outputs.items():
    (HERE / n).write_text(t, encoding="utf-8")
    print(f"wrote {(HERE / n).relative_to(REPO)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
