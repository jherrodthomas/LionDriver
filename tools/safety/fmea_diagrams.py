#!/usr/bin/env python3
"""Draw the FMEA, FMEDA and DFA figures from the YAML analyses in assurance/08-analyses/fmea/.

The YAML files under `analyses/` are the analyses of record. This script only draws them: one SVG
per figure (large trees are split into sheets) plus `figures/README.md`, the index. Change the
YAML and regenerate; never edit the SVGs by hand.

Figures (numbered for fmea-plan.md):
  2-1   DFA: dependent failure initiators x ASIL decompositions, measures and open items
  3-1/3-3/3-5/3-8   structure tree (AIAG-VDA step 2-3) of the System FMEA, DFMEA, SW FMEA, PFMEA
  3-2/3-4/3-6/3-9   failure chains (steps 4-6): element -> function -> failure mode -> causes
  3-7   SW FMEA: effect of the actions that carry a predicted ("revised") rating
  3-12  SW FMEA: occurrence x detection grid per element, with predicted moves
  3-13  SW FMEA: detection evidence per cause (cited test run in CI, hardware only, not run) and the cited test files
  3-14  SW FMEA: rating changes of the re-rated causes since the previous baseline
  3-15  SW FMEA: reaction time of the timed safety mechanisms by defence layer
  3-16  SW FMEA: functional safety / SOTIF boundary per element
  3-10/3-11  FMEDA SG-001 / SG-009: SPFM, LFM, lambda SPF+RF against the ASIL target
  4-1   Action Priority overview of the four FMEAs (O x D grid, AP counts, treatment of AP=H)
  4-2   FMEA-MSR overview of the System FMEA and DFMEA (F x M grid, monitoring bands, timing basis, monitoring actions)

    python3 tools/safety/fmea_diagrams.py            # regenerate the SVGs and README.md
    python3 tools/safety/fmea_diagrams.py --check    # exit 1 and list stale files

Standard library only: the YAML is read with the small block-style loader below (the subset the
analyses use). test_fmea_diagrams.py checks it against PyYAML when that is installed.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
FMEA_DIR = ROOT / "assurance" / "08-analyses" / "fmea"
ANALYSES = FMEA_DIR / "analyses"
OUT_DIR = FMEA_DIR / "figures" / "generated"   # owned by this script; hand-drawn figures live one level up
# Only files whose names match this pattern are ever pruned or reported as no longer generated.
OWNED_RE = re.compile(r"^fig-[2-4]-\d+-(?:dfa|sfm|dfm|swf|pfm|fmeda|action-priority|msr)-[a-z0-9-]+\.svg$")
GENERATOR = "tools/safety/fmea_diagrams.py"


class FigError(Exception):
  pass


# ================================================================ YAML subset loader

_KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.\-/ ]*?)\s*:(?:\s+|$)")
_BLOCK_SCALAR_RE = re.compile(r"^([>|])([+-]?)\s*(?:#.*)?$")
_INT_RE = re.compile(r"^[-+]?(?:0|[1-9][0-9_]*)$")
_FLOAT_RE = re.compile(r"^(?:[-+]?[0-9][0-9_]*\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9_]+(?:[eE][-+][0-9]+)?)$")
_UNSUPPORTED_RE = re.compile(r"^(?:[-+]?0b[01_]+|[-+]?0[0-7_]+|[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+(?:\.[0-9_]*)?"
                             r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)|<<|=)$")
_BOOLS = {**dict.fromkeys(("yes", "Yes", "YES", "true", "True", "TRUE", "on", "On", "ON"), True),
          **dict.fromkeys(("no", "No", "NO", "false", "False", "FALSE", "off", "Off", "OFF"), False)}


def _resolve(s: str):
  """Plain-scalar typing as PyYAML's SafeLoader, except dates stay strings (as in fmea_lint)."""
  if s in ("", "~", "null", "Null", "NULL"):
    return None
  if s in _BOOLS:
    return _BOOLS[s]
  if _INT_RE.match(s):
    return int(s.replace("_", ""))
  if _FLOAT_RE.match(s):
    return float(s.replace("_", ""))
  if _UNSUPPORTED_RE.match(s):
    raise FigError(f"YAML: unsupported plain scalar {s!r}; quote it")
  return s


def _strip_comment(s: str) -> str:
  m = re.search(r"(^|\s)#", s)
  return (s[:m.start()] if m else s).rstrip()


def _fold(lines: list[str]) -> str:
  """Join the lines of a multi-line flow or quoted scalar: line breaks fold to spaces, blank lines to newlines."""
  out = ""
  pending_nl = 0
  for i, ln in enumerate(lines):
    if ln == "":
      pending_nl += 1
      continue
    if i:
      out += "\n" * pending_nl if pending_nl else " "
    pending_nl = 0
    out += ln
  return out


def _unescape_dq(s: str) -> str:
  simple = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f",
            "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0"}
  out, i = [], 0
  while i < len(s):
    c = s[i]
    if c != "\\":
      out.append(c)
      i += 1
      continue
    n = s[i + 1]
    if n in simple:
      out.append(simple[n])
      i += 2
    elif n in "xuU":
      k = {"x": 2, "u": 4, "U": 8}[n]
      out.append(chr(int(s[i + 2:i + 2 + k], 16)))
      i += 2 + k
    else:
      raise FigError(f"YAML: unsupported escape \\{n}")
  return "".join(out)


class _Yaml:
  def __init__(self, text: str):
    if "\t" in text.replace("\t#", ""):
      for ln in text.splitlines():
        if ln[:len(ln) - len(ln.lstrip())].count("\t"):
          raise FigError("YAML: tab indentation is not supported")
    self.lines = text.split("\n")
    self.i = 0
    self.anchors: dict[str, object] = {}

  def sig(self):
    while self.i < len(self.lines):
      raw = self.lines[self.i]
      s = raw.strip()
      if s and not s.startswith("#") and s != "---":
        return len(raw) - len(raw.lstrip(" ")), s
      self.i += 1
    return None

  def doc(self):
    val = self.block(0)
    if self.sig() is not None:
      raise FigError(f"YAML: unexpected content at line {self.i + 1}: {self.lines[self.i].strip()!r}")
    return val

  def block(self, min_indent: int):
    s = self.sig()
    if s is None or s[0] < min_indent:
      return None
    if s[1] == "-" or s[1].startswith("- "):
      return self.seq(s[0])
    return self.mapping(s[0])

  def seq(self, c: int):
    out = []
    while True:
      s = self.sig()
      if s is None or s[0] < c:
        break
      if s[0] > c or not (s[1] == "-" or s[1].startswith("- ")):
        if s[0] == c:
          break
        raise FigError(f"YAML: bad indentation at line {self.i + 1}")
      rest = s[1][1:].lstrip(" ")
      col = c + len(s[1]) - len(rest)
      out.append(self.value(rest, col, c, in_map=False))
    return out

  def mapping(self, c: int):
    out: dict = {}
    while True:
      s = self.sig()
      if s is None or s[0] < c or s[1] == "-" or s[1].startswith("- "):
        break
      if s[0] > c:
        raise FigError(f"YAML: bad indentation at line {self.i + 1}")
      m = _KEY_RE.match(s[1])
      if not m:
        raise FigError(f"YAML: expected 'key:' at line {self.i + 1}: {s[1]!r}")
      key = m.group(1)
      if key in out:
        raise FigError(f"YAML: duplicate key {key!r} at line {self.i + 1}")
      rest = s[1][m.end():]
      out[key] = self.value(rest, c + m.end(), c, in_map=True)
    return out

  def value(self, rest: str, col: int, parent: int, in_map: bool):
    anchor = None
    if rest.startswith("&"):
      m = re.match(r"&(\S+)\s*", rest)
      anchor, rest, col = m.group(1), rest[m.end():], col + m.end()
    if rest == "" or rest.startswith("#"):
      self.i += 1
      s = self.sig()
      if s is not None and s[0] > parent:
        val = self.block(parent + 1)
      elif s is not None and in_map and s[0] == parent and (s[1] == "-" or s[1].startswith("- ")):
        val = self.seq(parent)
      else:
        val = None
    elif rest.startswith("*"):
      name = _strip_comment(rest[1:])
      if name not in self.anchors:
        raise FigError(f"YAML: unknown alias *{name}")
      val = self.anchors[name]
      self.i += 1
    elif not in_map and _KEY_RE.match(rest) and rest[0] not in "\"'[{":
      self.lines[self.i] = " " * col + rest
      val = self.mapping(col)
    else:
      val = self.scalar(rest, parent)
    if anchor:
      self.anchors[anchor] = val
    return val

  def scalar(self, rest: str, parent: int):
    m = _BLOCK_SCALAR_RE.match(rest)
    if m:
      return self.block_scalar(m.group(1), m.group(2), parent)
    if rest[0] in "[{":
      val, pos = _flow(rest, 0)
      if _strip_comment(rest[pos:]):
        raise FigError(f"YAML: trailing text after flow collection at line {self.i + 1}")
      self.i += 1
      return val
    if rest[0] in "\"'":
      return self.quoted(rest)
    first = _strip_comment(rest)
    parts = [first]
    j = self.i + 1
    last = self.i
    while j < len(self.lines):
      raw = self.lines[j]
      s = raw.strip()
      ind = len(raw) - len(raw.lstrip(" "))
      if s == "":
        parts.append("")
        j += 1
        continue
      if ind <= parent or s.startswith("#"):
        break
      parts.append(_strip_comment(s))
      last = j
      j += 1
    parts = parts[:last - self.i + 1]
    self.i = last + 1
    if len(parts) == 1:
      return _resolve(first)
    return _fold(parts)

  def quoted(self, rest: str):
    q = rest[0]
    buf = [rest[1:]]
    while True:
      joined = "\n".join(buf)
      end = _quote_end(joined, q)
      if end is not None:
        break
      self.i += 1
      if self.i >= len(self.lines):
        raise FigError("YAML: unterminated quoted scalar")
      buf.append(self.lines[self.i])
    body, tail = joined[:end], joined[end + 1:]
    if _strip_comment(tail):
      raise FigError(f"YAML: text after closing quote at line {self.i + 1}")
    self.i += 1
    lines = body.split("\n")
    lines = [lines[0].rstrip(" ")] + [ln.strip(" ") for ln in lines[1:-1]] + ([lines[-1].lstrip(" ")] if len(lines) > 1 else [])
    if len(lines) == 1:
      text = body
    else:
      text = _fold(lines)
    if q == "'":
      return text.replace("''", "'")
    return _unescape_dq(text)

  def block_scalar(self, style: str, chomp: str, parent: int):
    self.i += 1
    body: list[str] = []
    indent = None
    while self.i < len(self.lines):
      raw = self.lines[self.i]
      if raw.strip() == "":
        body.append("")
        self.i += 1
        continue
      ind = len(raw) - len(raw.lstrip(" "))
      if ind <= parent:
        break
      if indent is None:
        indent = ind
      if ind < indent:
        break
      if ind > indent and style == ">":
        raise FigError(f"YAML: more-indented line in a folded scalar at line {self.i + 1}")
      body.append(raw[indent:])
      self.i += 1
    while body and body[-1] == "":
      body.pop()
    text = "\n".join(body) if style == "|" else _fold(body)
    if chomp == "-" or not text:
      return text
    return text + "\n"


def _quote_end(s: str, q: str):
  i = 0
  while i < len(s):
    c = s[i]
    if q == '"' and c == "\\":
      i += 2
      continue
    if c == q:
      if q == "'" and i + 1 < len(s) and s[i + 1] == "'":
        i += 2
        continue
      return i
    i += 1
  return None


def _flow(s: str, p: int):
  def ws(p):
    while p < len(s) and s[p] == " ":
      p += 1
    return p

  p = ws(p)
  c = s[p]
  if c == "[":
    out, p = [], ws(p + 1)
    while s[p] != "]":
      v, p = _flow(s, p)
      out.append(v)
      p = ws(p)
      if s[p] == ",":
        p = ws(p + 1)
      elif s[p] != "]":
        raise FigError(f"YAML: bad flow sequence {s!r}")
    return out, p + 1
  if c == "{":
    out, p = {}, ws(p + 1)
    while s[p] != "}":
      m = re.compile(r"([A-Za-z0-9_][A-Za-z0-9_.\-]*)\s*:\s").match(s, p)
      if not m:
        raise FigError(f"YAML: bad flow mapping key in {s!r}")
      v, p = _flow(s, m.end())
      out[m.group(1)] = v
      p = ws(p)
      if s[p] == ",":
        p = ws(p + 1)
      elif s[p] != "}":
        raise FigError(f"YAML: bad flow mapping {s!r}")
    return out, p + 1
  if c in "\"'":
    end = _quote_end(s[p + 1:], c)
    if end is None:
      raise FigError(f"YAML: unterminated quote in {s!r}")
    body = s[p + 1:p + 1 + end]
    return (body.replace("''", "'") if c == "'" else _unescape_dq(body)), p + end + 2
  m = re.compile(r"[^,\[\]{}]*").match(s, p)
  return _resolve(m.group(0).strip()), m.end()


def load_yaml(text: str):
  return _Yaml(text).doc()


def load_analyses(directory: Path = ANALYSES) -> dict[str, dict]:
  docs = {}
  for path in sorted(directory.glob("*.yaml")):
    docs[path.stem] = load_yaml(path.read_text(encoding="utf-8"))
  return docs


# ================================================================ rating rules (as tools/safety/fmea_lint.py)

S_BANDS = ((9, 10), (7, 8), (4, 6), (2, 3), (1, 1))
O_BANDS = ((8, 10), (6, 7), (4, 5), (2, 3), (1, 1))
D_BANDS = ((7, 10), (5, 6), (2, 4), (1, 1))
AP_TABLE = {
  (9, 10): ("HHHH", "HHHH", "HHHM", "HMLL", "LLLL"),
  (7, 8): ("HHHH", "HHHM", "HMMM", "MMLL", "LLLL"),
  (4, 6): ("HHMM", "MMML", "MLLL", "LLLL", "LLLL"),
  (2, 3): ("MMLL", "LLLL", "LLLL", "LLLL", "LLLL"),
  (1, 1): ("LLLL", "LLLL", "LLLL", "LLLL", "LLLL"),
}
FMEDA_TARGETS = {"B": (0.90, 0.60, 100.0), "C": (0.97, 0.80, 100.0), "D": (0.99, 0.90, 10.0)}


def _band(v, bands):
  return next(i for i, (lo, hi) in enumerate(bands) if lo <= v <= hi)


def compute_ap(s: int, o: int, d: int) -> str:
  return AP_TABLE[S_BANDS[_band(s, S_BANDS)]][_band(o, O_BANDS)][_band(d, D_BANDS)]


# FMEA-MSR action priority for S 10 (rating-tables §7.4, RT-3: AIAG-VDA handbook table): F -> AP for M = 1..10
AP_MSR_S10 = {**{f: "H" * 10 for f in range(5, 11)}, 4: "M" + "H" * 9, 3: "LMM" + "H" * 7, 2: "LLL" + "M" * 7, 1: "L" * 10}


def compute_ap_msr_s10(f: int, m: int) -> str:
  return AP_MSR_S10[f][m - 1]


def fmeda_mode(fm: dict, goal: str | None) -> dict:
  """The row as classified for `goal` (its per_goal entry applied), as fmea_lint.fmeda_mode."""
  for pg in fm.get("per_goal", []) if goal else []:
    if pg["goal"] == goal:
      return {**fm, **{k: v for k, v in pg.items() if k not in ("goal", "reason")}}
  return fm


def fmeda_targets(doc) -> list[tuple[str | None, str, list[str]]]:
  """[(goal, ASIL, also_show)] as fmea_lint.fmeda_targets."""
  a = doc["analysis"]
  if a.get("targets"):
    return [(t["goal"], t["asil"], t.get("also_show", [])) for t in a["targets"]]
  return [(a.get("safety_goal"), a["asil_target"], [])] if a.get("asil_target") else []


def fmeda_rows(doc, goal: str | None = None) -> list[dict]:
  """Classify every failure mode per rating-tables §6.1 (same arithmetic as fmea_lint.fmeda_metrics)."""
  rows = []
  for comp in doc["components"]:
    lam = comp["failure_rate_fit"]
    for row in comp["failure_modes"]:
      fm = fmeda_mode(row, goal)
      r = {"comp": comp["id"], "id": fm["id"], "mode": fm["mode"], "spf": 0.0, "rf": 0.0, "det": 0.0,
           "latent": 0.0, "mpf_det": 0.0, "safe": 0.0, "sm": None, "dc": None, "counted": comp["safety_related"]}
      if not comp["safety_related"] or lam is None:
        rows.append(r)
        continue
      l_fm = lam * fm["distribution"]
      if fm["violates_sg_directly"]:
        dc = fm.get("dc_spf", 0.0) if fm.get("safety_mechanism_spf") else 0.0
        if dc == 0.0:
          r["spf"] = l_fm
          r["cls"] = "spf"
        else:
          r["rf"] = l_fm * (1 - dc)
          r["det"] = l_fm * dc
          r["cls"] = "rf"
          r["sm"], r["dc"] = fm["safety_mechanism_spf"], dc
      elif fm["mpf_potential"]:
        dc = fm.get("dc_lf", 0.0) if fm.get("safety_mechanism_lf") else 0.0
        r["latent"] = l_fm * (1 - dc)
        r["mpf_det"] = l_fm * dc
        r["cls"] = "mpf"
        if fm.get("safety_mechanism_lf"):
          r["sm"], r["dc"] = fm["safety_mechanism_lf"], dc
      else:
        r["safe"] = l_fm
        r["cls"] = "safe"
      rows.append(r)
  return rows


def fmeda_metrics(doc, goal: str | None = None):
  rows = [r for r in fmeda_rows(doc, goal) if r["counted"]]
  total = sum(c["failure_rate_fit"] for c in doc["components"] if c["safety_related"])
  if total == 0 or any(c["failure_rate_fit"] is None for c in doc["components"] if c["safety_related"]):
    return None
  spf = sum(r["spf"] for r in rows)
  rf = sum(r["rf"] for r in rows)
  latent = sum(r["latent"] for r in rows)
  remaining = total - spf - rf
  return {"total_fit": total, "spf_fit": spf, "rf_fit": rf, "mpf_latent_fit": latent,
          "spfm": 1 - (spf + rf) / total, "lfm": 1 - latent / remaining if remaining > 0 else 1.0,
          "pmhf_spf_rf_fit": spf + rf}


# ================================================================ SVG basics

FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"
# Two styles. The original figures are the record (fig-*.svg); the card style of the fault tree card view and
# fta-viewer.html is an easier-to-read second version of every figure (fig-*-cards.svg). The style is fixed when the
# module is imported: build_all() draws the record here and the card versions in a second process with
# FMEA_FIG_STYLE=cards.
CARDS = os.environ.get("FMEA_FIG_STYLE") == "cards"
if CARDS:
  INK, MUTED, RED = "#0B0B0B", "#52514E", "#D03B3B"
  BG, GRID, FAINT = "#FCFCFB", "#E1E0D9", "#898781"
else:
  INK, MUTED, RED = "#0F172A", "#475569", "#D2553F"
  BG, GRID, FAINT = "#FFFFFF", "#E2E8F0", "#94A3B8"
AMBER, GREEN = "#D97706", "#2E9E6A"
CARD, LINE, SOFT = "#FFFFFF", "#C9C7BF", "#F3F2EE"   # card style only
CAT_BLUE, CAT_ORANGE, CAT_AQUA, CAT_VIOLET = "#2A78D6", "#EB6834", "#1BAF7A", "#6250D6"
AP_TINT_PILL = {"H": ("#FBE9E9", "#9E2424"), "M": ("#FFF5DC", "#7A5600"), "L": ("#E6F5E6", "#0A6A0A")}
ACTION_TINT = {"open": ("#FBE9E9", "#9E2424", None), "decision_pending": ("#FFFFFF", "#7A5600", "#E0B44C"),
               "in_progress": ("#FFF5DC", "#7A5600", None), "completed": ("#E6F5E6", "#0A6A0A", None),
               "not_implemented": ("#FFFFFF", MUTED, LINE)}
ORANGE, TEAL, SLATE = "#C2410C", "#0F766E", "#64748B"
AP_COL = {"H": RED, "M": AMBER, "L": TEAL}
AP_TINT = {"H": "#FBE4DF", "M": "#FDEFD8", "L": "#DDF0EC"}
ACTION_COL = {"open": ("#FFFFFF", RED, RED), "decision_pending": ("#FFFFFF", AMBER, AMBER),
              "in_progress": (AMBER, "#FFFFFF", None), "completed": (GREEN, "#FFFFFF", None),
              "not_implemented": ("#FFFFFF", SLATE, SLATE)}
ACTION_LABEL = {"open": "open", "decision_pending": "decision pending", "in_progress": "in progress",
                "completed": "completed", "not_implemented": "not implemented"}

_NARROW = set("il.,:;'|!I")
_SEMI = set("frtj()[] -/")


def tw(s: str, size: float, weight: int = 400) -> float:
  """Approximate rendered width of `s` in Inter at `size` px."""
  w = 0.0
  for ch in s:
    if ch in _NARROW:
      w += 0.27
    elif ch in _SEMI:
      w += 0.37
    elif ch in "mw":
      w += 0.84
    elif ch in "MW":
      w += 0.92
    elif ch.isupper():
      w += 0.68
    elif ch.isdigit():
      w += 0.62
    elif ch.islower():
      w += 0.56
    else:
      w += 0.62
  return w * size * (1.07 if weight >= 700 else 1.04 if weight >= 600 else 1.0)


def wrap(text: str, width: float, size: float, weight: int = 400, max_lines: int | None = None) -> list[str]:
  words = " ".join(str(text).split()).split(" ")
  lines: list[str] = []
  line = ""
  for word in words:
    cand = f"{line} {word}" if line else word
    if tw(cand, size, weight) <= width or not line:
      line = cand
    else:
      lines.append(line)
      line = word
  if line:
    lines.append(line)
  # hard-split words longer than the width
  out = []
  for ln in lines:
    while tw(ln, size, weight) > width and len(ln) > 4:
      k = len(ln)
      while k > 1 and tw(ln[:k], size, weight) > width:
        k -= 1
      out.append(ln[:k])
      ln = ln[k:]
    out.append(ln)
  if max_lines is not None and len(out) > max_lines:
    out = out[:max_lines]
    last = out[-1]
    while last and tw(last + "…", size, weight) > width:
      last = last[:-1].rstrip()
    out[-1] = last.rstrip(" ,;:") + "…"
  return out


def fit(text: str, width: float, size: float, weight: int = 400) -> str:
  return wrap(text, width, size, weight, 1)[0] if text else ""


def e(s) -> str:
  return escape(str(s))


def n(v: float) -> str:
  """Deterministic coordinate formatting."""
  r = round(v, 1)
  return str(int(r)) if r == int(r) else f"{r:.1f}"


def txt(x, y, s, size=11, fill=INK, weight=400, anchor=None, italic=False, extra="") -> str:
  a = f' font-size="{size}" fill="{fill}"'
  if weight != 400:
    a += f' font-weight="{weight}"'
  if anchor:
    a += f' text-anchor="{anchor}"'
  if italic:
    a += ' font-style="italic"'
  return f'<text x="{n(x)}" y="{n(y)}"{a}{extra}>{e(s)}</text>'


def rect(x, y, w, h, fill="#FFFFFF", stroke=None, sw=1.2, rx=0, extra="") -> str:
  a = f' fill="{fill}"'
  if stroke:
    a += f' stroke="{stroke}" stroke-width="{sw}"'
  if rx:
    a += f' rx="{rx}"'
  return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"{a}{extra}/>'


def line(x1, y1, x2, y2, stroke=GRID, sw=1, extra="") -> str:
  return f'<line x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}" stroke="{stroke}" stroke-width="{sw}"{extra}/>'


PILL_H = 15
PILL_SIZE = 9.5


def pill_w(label: str, size: float = PILL_SIZE) -> float:
  return tw(label, size, 700) + 12


def pill(x, y, label, fill, fg="#FFFFFF", stroke=None, size=PILL_SIZE, h=PILL_H, dashed=False) -> tuple[str, float]:
  w = pill_w(label, size)
  st = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
  if dashed:
    st += ' stroke-dasharray="3 2"'
  svg = (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{h}" rx="{h / 2}" fill="{fill}"{st}/>' +
         f'<text x="{n(x + w / 2)}" y="{n(y + h / 2 + size * 0.36)}" font-size="{size}" font-weight="700" fill="{fg}" ' +
         f'text-anchor="middle" letter-spacing=".02em">{e(label)}</text>')
  return svg, w


def ap_pill(x, y, ap: str, label: str | None = None, h: float = PILL_H) -> tuple[str, float]:
  """Action Priority as a tinted pill with a shape, never colour alone: H a barred disc, M a triangle, L a dot."""
  bg, fg = AP_TINT_PILL[ap]
  label = label or f"AP {ap}"
  w = tw(label, PILL_SIZE, 700) + 24
  cx, cy = x + 9.5, y + h / 2
  if ap == "H":
    mark = f'<circle cx="{n(cx)}" cy="{n(cy)}" r="4.3" fill="{fg}"/><rect x="{n(cx - 2.6)}" y="{n(cy - 0.8)}" width="5.2" height="1.6" fill="{bg}"/>'
  elif ap == "M":
    mark = f'<path d="M{n(cx)} {n(cy - 4)}L{n(cx + 4.4)} {n(cy + 3.6)}H{n(cx - 4.4)}Z" fill="{fg}"/>'
  else:
    mark = f'<circle cx="{n(cx)}" cy="{n(cy)}" r="3.6" fill="{fg}"/>'
  svg = (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{h}" rx="{h / 2}" fill="{bg}"/>' + mark +
         f'<text x="{n(x + 17)}" y="{n(y + h / 2 + PILL_SIZE * 0.36)}" font-size="{PILL_SIZE}" font-weight="700" fill="{fg}">{e(label)}</text>')
  return svg, w


def ap_pill_w(ap: str, label: str | None = None) -> float:
  return tw(label or f"AP {ap}", PILL_SIZE, 700) + 24


_DEFS = """  <defs>
    <marker id="aG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker>
    <marker id="aS" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#94A3B8"/></marker>
    <pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#CBD5E1" stroke-width="2"/></pattern>
@@DOTS@@    <pattern id="hatchA" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#FFFFFF"/><line x1="0" y1="0" x2="0" y2="6" stroke="#F3C38A" stroke-width="2.4"/></pattern>
  </defs>"""
DEFS = _DEFS.replace("@@DOTS@@", '    <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.2" '
                     'cy="1.2" r="1.2" fill="#E7E6E0"/></pattern>\n' if CARDS else "")


def svg_doc(w: float, h: float, title: str, desc: str, fig: str, heading: str, sub: str, ref1: str, ref2: str,
            body: list[str]) -> str:
  w, h = int(round(w)), int(round(h))
  out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
         f'font-family="{FONT}" role="img" aria-labelledby="t d">',
         f'  <title id="t">{e(title)}</title>',
         f'  <desc id="d">{e(desc)}</desc>',
         DEFS,
         f'  <rect width="{w}" height="{h}" fill="{BG}"/>',
         "  " + txt(40, 44, f"Figure {fig} · {heading}", 20, INK, 700),
         "  " + txt(40, 66, sub, 12.5, MUTED),
         "  " + txt(w - 40, 44, ref1, 11, MUTED, anchor="end"),
         "  " + txt(w - 40, 62, ref2, 11, MUTED, anchor="end"),
         "  " + line(40, 82, w - 40, 82)]
  out += ["  " + b for b in body]
  out.append("</svg>")
  return "\n".join(out) + "\n"


def footer(y: float, w: float, source: str) -> list[str]:
  return [txt(40, y, f"Generated by {GENERATOR} from {source}. Edit the YAML and regenerate; do not edit this file.",
              9.5, FAINT)]


# ================================================================ FMEA trees

TYPE_NAME = {"system_fmea": "System FMEA", "dfmea": "DFMEA", "sw_fmea": "SW FMEA", "pfmea": "PFMEA"}
FMEA_FILES = (("system-fmea", "3-1", "3-2", "sfm"), ("dfmea", "3-3", "3-4", "dfm"),
              ("sw-fmea", "3-5", "3-6", "swf"), ("pfmea", "3-8", "3-9", "pfm"))
PLAN_SECTION = {"system-fmea": "§3.1", "dfmea": "§3.2", "sw-fmea": "§3.3", "pfmea": "§3.4"}

COL_STYLE_CLASSIC = {  # fill, stroke of the original boxes
  "element": ("#F8FAFC", SLATE),
  "external": ("#F1F5F9", "#94A3B8"),
  "function": ("#F0FDFA", TEAL),
  "fm": ("#FFF7ED", ORANGE),
  "cause": ("#FFFFFF", "#94A3B8"),
}
COL_STYLE = {  # card style: icon colour and shape before the ID; every card is white with a hairline border
  "element": (MUTED, "square"),
  "external": (MUTED, "outline"),
  "function": (CAT_BLUE, "square"),
  "fm": (CAT_ORANGE, "diamond"),
  "cause": (CAT_VIOLET, "circle"),
  "action": (CAT_AQUA, "circle"),
}
KIND_LABEL = {"element": "ELEMENT", "external": "EXTERNAL", "function": "FUNCTION", "fm": "FAILURE MODE",
              "cause": "CAUSE", "action": "ACTION"}
SIB_GAP = {"element": 22, "function": 16, "fm": 12, "cause": 6}
PAD = 9
MAX_SHEET_H = 1450


@dataclass(eq=False)
class TBox:
  kind: str
  ident: str
  w: float
  lines: list[tuple[str, float, str, int, bool]] = field(default_factory=list)   # text, size, fill, weight, italic
  head_pills: list[tuple[str, str, str, str | None]] = field(default_factory=list)  # label, fill, fg, stroke
  right_pill: tuple[str, str, str, str | None] | None = None
  chips: list[tuple[str, str, str, str | None, bool]] = field(default_factory=list)  # label, fill, fg, stroke, dashed
  chip_caption: str = ""
  style: str = ""
  children: list[TBox] = field(default_factory=list)
  x: float = 0.0
  y: float = 0.0
  h: float = 0.0
  dashed: bool = False
  ap: str | None = None   # Action Priority shown as the right-hand pill

  def chip_rows(self) -> list[list[tuple]]:
    rows: list[list[tuple]] = []
    row: list[tuple] = []
    used = tw(self.chip_caption, 9.5, 600) + 6 if self.chip_caption else 0.0
    avail = self.w - 2 * PAD
    for c in self.chips:
      cw = pill_w(c[0])
      if row and used + cw > avail:
        rows.append(row)
        row, used = [], 0.0
      row.append(c)
      used += cw + 4
    if row:
      rows.append(row)
    return rows

  def measure(self) -> float:
    h = PAD + 13
    for _, size, _, _, _ in self.lines:
      h += size * 1.34
    rows = self.chip_rows()
    if rows:
      h += 4 + len(rows) * (PILL_H + 3)
    self.h = h + PAD - 2
    return self.h


def add_text(box: TBox, text: str, size: float = 10.5, fill: str = INK, weight: int = 400, max_lines: int = 3,
             italic: bool = False, prefix: str = "") -> None:
  for ln in wrap(prefix + text, box.w - 2 * PAD, size, weight, max_lines):
    box.lines.append((ln, size, fill, weight, italic))


def kind_icon(style: str, x: float, y: float) -> str:
  """13 x 12 type icon left of the ID, in the shape language of the fault tree sheets."""
  col, shape = COL_STYLE[style]
  if shape == "square":
    return rect(x + 0.5, y + 0.5, 12, 11, col, rx=3)
  if shape == "outline":
    return rect(x + 1, y + 1, 11, 10, CARD, col, 1.5, 3)
  if shape == "diamond":
    return f'<path d="M{n(x + 6.5)} {n(y)}L{n(x + 13)} {n(y + 6)}L{n(x + 6.5)} {n(y + 12)}L{n(x)} {n(y + 6)}Z" fill="{col}"/>'
  return f'<circle cx="{n(x + 6.5)}" cy="{n(y + 6)}" r="5.5" fill="{col}"/>'


def tw_mono(s: str, size: float) -> float:
  return len(s) * size * 0.6


def _draw_tbox_classic(b: TBox, out: list[str]) -> None:
  fill, stroke = COL_STYLE_CLASSIC[b.style or b.kind]
  dash = ' stroke-dasharray="5 3"' if b.dashed else ""
  out.append(rect(b.x, b.y, b.w, b.h, fill, stroke, 1.3, 8, dash))
  x0 = b.x + PAD
  y = b.y + PAD + 10.5
  out.append(txt(x0, y, b.ident, 12, INK, 700))
  px = x0 + tw(b.ident, 12, 700) + 7
  for label, f, fg, st in b.head_pills:
    s, w = pill(px, y - 11, label, f, fg, st)
    out.append(s)
    px += w + 4
  if b.right_pill:
    label, f, fg, st = b.right_pill
    w = pill_w(label)
    s, _ = pill(b.x + b.w - PAD - w, y - 11, label, f, fg, st)
    out.append(s)
  y += 2.5
  for text, size, fl, weight, italic in b.lines:
    y += size * 1.34
    out.append(txt(x0, y - 2, text, size, fl, weight, italic=italic))
  rows = b.chip_rows()
  if rows:
    y += 4
    for i, row in enumerate(rows):
      cx = x0
      if i == 0 and b.chip_caption:
        out.append(txt(cx, y + 11, b.chip_caption, 9.5, MUTED, 600))
        cx += tw(b.chip_caption, 9.5, 600) + 6
      for label, f, fg, st, dashed in row:
        s, w = pill(cx, y, label, f, fg, st, dashed=dashed)
        out.append(s)
        cx += w + 4
      y += PILL_H + 3


def draw_tbox(b: TBox, out: list[str]) -> None:
  if not CARDS:
    _draw_tbox_classic(b, out)
    return
  style = b.style or b.kind
  dash = ' stroke-dasharray="5 3"' if b.dashed else ""
  out.append(rect(b.x, b.y + 3, b.w, b.h, "#000000", rx=12, extra=' opacity=".05"'))
  out.append(rect(b.x, b.y, b.w, b.h, CARD, MUTED if b.dashed else GRID, 1.3 if b.dashed else 1, 12, dash))
  x0 = b.x + PAD + 1
  y = b.y + PAD + 10.5
  out.append(kind_icon(style, x0, y - 10))
  idx = x0 + 18
  out.append(f'<text x="{n(idx)}" y="{n(y)}" font-size="11.5" font-weight="700" fill="{INK}" font-family="{MONO}">{e(b.ident)}</text>')
  px = idx + tw_mono(b.ident, 11.5) + 7
  for label, f, fg, st in b.head_pills:
    s, w = pill(px, y - 11, label, f, fg, st)
    out.append(s)
    px += w + 4
  right = b.x + b.w - PAD
  if b.ap:
    w = ap_pill_w(b.ap)
    s, _ = ap_pill(right - w, y - 11, b.ap)
    out.append(s)
  elif b.right_pill:
    label, f, fg, st = b.right_pill
    w = pill_w(label)
    s, _ = pill(right - w, y - 11, label, f, fg, st)
    out.append(s)
  elif px + tw(KIND_LABEL[style], 8.5, 600) * 1.1 + 8 < right:
    out.append(txt(right, y - 1, KIND_LABEL[style], 8.5, FAINT, 600, anchor="end", extra=' letter-spacing=".08em"'))
  y += 2.5
  for text, size, fl, weight, italic in b.lines:
    y += size * 1.34
    out.append(txt(x0, y - 2, text, size, fl, weight, italic=italic))
  rows = b.chip_rows()
  if rows:
    y += 4
    for i, row in enumerate(rows):
      cx = x0
      if i == 0 and b.chip_caption:
        out.append(txt(cx, y + 11, b.chip_caption, 9.5, MUTED, 600))
        cx += tw(b.chip_caption, 9.5, 600) + 6
      for label, f, fg, st, dashed in row:
        s, w = pill(cx, y, label, f, fg, st, dashed=dashed)
        out.append(s)
        cx += w + 4
      y += PILL_H + 3


def elbow(px: float, py: float, cx: float, cy: float) -> str:
  """Rounded orthogonal wire from a parent's right edge to a child's left edge."""
  xm = px + min(17, (cx - px) / 2)
  if abs(cy - py) < 1:
    d = f"M{n(px)} {n(py)}H{n(cx)}"
  else:
    r = min(8.0, abs(cy - py) / 2, xm - px)
    s = 1 if cy > py else -1
    d = (f"M{n(px)} {n(py)}H{n(xm - r)}Q{n(xm)} {n(py)} {n(xm)} {n(py + s * r)}V{n(cy - s * r)}"
         f"Q{n(xm)} {n(cy)} {n(xm + r)} {n(cy)}H{n(cx)}")
  return f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.6" stroke-linecap="round"/>'


def place_tree(roots: list[TBox], top: float) -> float:
  """Place boxes: leaves stacked, each parent centred on its children's span. Returns the bottom y."""

  def shift(b: TBox, dy: float):
    b.y += dy
    for c in b.children:
      shift(c, dy)

  def place(b: TBox, y0: float) -> float:
    b.measure()
    if not b.children:
      b.y = y0
      return y0 + b.h
    cur = y0
    for i, c in enumerate(b.children):
      if i:
        cur += SIB_GAP[c.kind]
      cur = place(c, cur)
    span = cur - y0
    if b.h > span:
      off = (b.h - span) / 2
      for c in b.children:
        shift(c, off)
      b.y = y0
      return y0 + b.h
    b.y = y0 + (span - b.h) / 2
    return cur

  cur = top
  for i, r in enumerate(roots):
    if i:
      cur += SIB_GAP[r.kind] + 6
    cur = place(r, cur)
  return cur


def draw_tree(roots: list[TBox], out: list[str]) -> None:
  def edges(b: TBox):
    if b.children:
      px, py = b.x + b.w, b.y + min(b.h / 2, 22)
      for c in b.children:
        cx, cy = c.x, c.y + min(c.h / 2, 22)
        if CARDS:
          out.append(elbow(px, py, cx, cy))
        else:
          xm = px + min(17, (cx - px) / 2)
          out.append(f'<path d="M{n(px)} {n(py)}H{n(xm)}V{n(cy)}H{n(cx - 1)}" fill="none" stroke="#94A3B8" '
                     f'stroke-width="1.2" marker-end="url(#aS)"/>')
      for c in b.children:
        edges(c)

  def boxes(b: TBox):
    draw_tbox(b, out)
    for c in b.children:
      boxes(c)

  for r in roots:
    edges(r)
  for r in roots:
    boxes(r)


def _hazards(fm) -> list[str]:
  seen: list[str] = []
  for ef in fm["effects"]:
    if ef.get("hazard") and ef["hazard"] not in seen:
      seen.append(ef["hazard"])
  return seen


def _end_effect(fm) -> str:
  ends = [ef["description"] for ef in fm["effects"] if ef["level"] == "end"]
  return ends[0] if ends else fm["effects"][-1]["description"]


@dataclass
class Fmea:
  key: str
  doc: dict
  fig_structure: str
  fig_chains: str
  slug: str

  @property
  def a(self):
    return self.doc["analysis"]

  @property
  def name(self) -> str:
    return TYPE_NAME[self.a["type"]]

  @property
  def tag(self) -> str:
    a = self.a
    return f"{a['id']} rev {a['revision']} · {a['baseline']} · {a['status']}"

  @property
  def source(self) -> str:
    return f"analyses/{self.key}.yaml"

  def elements(self) -> dict:
    return {x["id"]: x for x in self.doc["structure"]}

  def functions(self) -> dict:
    return {x["id"]: x for x in self.doc["functions"]}

  def actions(self) -> dict:
    return {x["id"]: x for x in self.doc["actions"]}

  def causes(self):
    for fm in self.doc["failure_modes"]:
      for c in fm["causes"]:
        yield fm, c


def _depths(els: dict) -> dict[str, int]:
  out = {}
  for k in els:
    d, cur, seen = 0, k, set()
    while els[cur].get("parent"):
      if cur in seen:
        raise FigError(f"structure cycle at {k}")
      seen.add(cur)
      cur = els[cur]["parent"]
      d += 1
    out[k] = d
  return out


def _ordered_elements(f: Fmea) -> list[str]:
  """Depth-first order of the structure, roots and children in file order."""
  els = f.elements()
  kids: dict[str | None, list[str]] = {}
  for x in f.doc["structure"]:
    kids.setdefault(x.get("parent"), []).append(x["id"])
  order: list[str] = []

  def visit(k):
    order.append(k)
    for c in kids.get(k, []):
      visit(c)

  for r in kids.get(None, []):
    visit(r)
  if len(order) != len(els):
    raise FigError(f"{f.key}: structure has elements with unknown parents")
  return order


# ---------------------------------------------------------------- structure tree (steps 2-3)

def render_structure(f: Fmea) -> str:
  els = f.elements()
  depth = _depths(els)
  max_d = max(depth.values())
  fns_by_el: dict[str, list[dict]] = {}
  for fn in f.doc["functions"]:
    fns_by_el.setdefault(fn["element"], []).append(fn)
  fm_by_fn: dict[str, int] = {}
  fm_by_el: dict[str, int] = {}
  for fm in f.doc["failure_modes"]:
    fm_by_fn[fm["function"]] = fm_by_fn.get(fm["function"], 0) + 1
    fm_by_el[fm["element"]] = fm_by_el.get(fm["element"], 0) + 1
  cause_by_el: dict[str, int] = {}
  for _, c in f.causes():
    if c.get("element"):
      cause_by_el[c["element"]] = cause_by_el.get(c["element"], 0) + 1

  el_w = 230 if max_d <= 1 else 210
  gap = 34
  fn_x = 40 + (max_d + 1) * (el_w + gap)
  fn_w = 1240 - fn_x
  col_x = [40 + d * (el_w + gap) for d in range(max_d + 1)]

  def el_box(k: str) -> TBox:
    x = els[k]
    style = "external" if x["kind"] == "external" else "element"
    b = TBox("element", k, el_w, style=style, dashed=x["kind"] == "external")
    b.head_pills.append((x["kind"].replace("_", " "), SOFT if CARDS else "#E2E8F0", MUTED, None))
    add_text(b, x["name"], 10.5, INK, 600, 3)
    stats = []
    if fm_by_el.get(k):
      stats.append(f"{fm_by_el[k]} failure mode{'s' if fm_by_el[k] != 1 else ''}")
    if cause_by_el.get(k):
      stats.append(f"{cause_by_el[k]} cause{'s' if cause_by_el[k] != 1 else ''} located here")
    if stats:
      add_text(b, " · ".join(stats), 9.5, MUTED, 400, 2)
    b.x = col_x[depth[k]]
    return b

  def fn_box(fn: dict, owner: str) -> TBox:
    b = TBox("function", fn["id"], fn_w)
    k = fm_by_fn.get(fn["id"], 0)
    if CARDS:
      b.right_pill = (f"{k} FM", SOFT, INK, None) if k else ("no FM", AP_TINT_PILL["H"][0], AP_TINT_PILL["H"][1], None)
    else:
      b.right_pill = (f"{k} FM", "#FFFFFF", ORANGE, ORANGE) if k else ("no FM", "#FFFFFF", RED, RED)
    add_text(b, fn["description"], 10.5, INK, 400, 2)
    for r in fn.get("requirements", []):
      b.chips.append((r, SOFT, MUTED, None, False) if CARDS else (r, "#E2E8F0", INK, None, False))
    if fn.get("requirements"):
      b.chip_caption = "traces to"
    b.x = fn_x
    return b

  kids: dict[str | None, list[str]] = {}
  for x in f.doc["structure"]:
    kids.setdefault(x.get("parent"), []).append(x["id"])

  def build(k: str) -> TBox:
    b = el_box(k)
    for c in kids.get(k, []):
      b.children.append(build(c))
    for fn in fns_by_el.get(k, []):
      b.children.append(fn_box(fn, k))
    return b

  all_roots = [build(r) for r in kids.get(None, [])]
  # external elements without children or functions go in a row of their own below the tree
  ext = [b for b in all_roots if b.style == "external" and not b.children]
  roots = [b for b in all_roots if b not in ext]
  top = 122
  bottom = place_tree(roots, top)
  body: list[str] = []
  if ext:
    y = bottom + 30
    body.append(txt(40, y, "OUTSIDE THE ITEM — EXTERNAL ELEMENTS (NO PARENT)", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
    y += 12
    ew, eg = 230, 13
    per_row = int((1200 + eg) // (ew + eg))
    for r0 in range(0, len(ext), per_row):
      row = ext[r0:r0 + per_row]
      rh = 0.0
      for k, b in enumerate(row):
        b.w = ew
        b.x, b.y = 40 + k * (ew + eg), y
        rh = max(rh, b.measure())
      for b in row:
        b.h = rh
        draw_tbox(b, body)
      y += rh + eg
    bottom = y - eg
  for d in range(max_d + 1):
    body.append(txt(col_x[d], 108, f"Structure level {d}" if d else "Structure root (level 0)", 10, MUTED, 700,
                    extra=' letter-spacing=".06em"'))
  body.append(txt(fn_x, 108, "Functions (step 3) · failure modes found", 10, MUTED, 700, extra=' letter-spacing=".06em"'))
  if CARDS:
    body.insert(0, rect(0, 83, 1280, bottom - 69, "url(#dots)"))
  draw_tree(roots, body)

  y = bottom + 26
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  for style, label in (("element", "Structure element (kind)"), ("external", "External element (outside the item)"),
                       ("function", "Function")):
    if CARDS:
      body.append(kind_icon(style, lx, y - 10))
      body.append(txt(lx + 19, y, label, 10.5, INK))
      lx += 19 + tw(label, 10.5) + 22
    else:
      fill, stroke = COL_STYLE_CLASSIC[style]
      body.append(rect(lx, y - 11, 26, 14, fill, stroke, 1.3, 4, ' stroke-dasharray="5 3"' if style == "external" else ""))
      body.append(txt(lx + 32, y, label, 10.5, INK))
      lx += 32 + tw(label, 10.5) + 22
  s, w = pill(lx, y - 11, "n FM", SOFT, INK) if CARDS else pill(lx, y - 11, "n FM", "#FFFFFF", ORANGE, ORANGE)
  body.append(s)
  body.append(txt(lx + w + 6, y, "failure modes analyzed for the function", 10.5, INK))
  lx += w + 6 + tw("failure modes analyzed for the function", 10.5) + 22
  s, w = pill(lx, y - 11, "no FM", *AP_TINT_PILL["H"]) if CARDS else pill(lx, y - 11, "no FM", "#FFFFFF", RED, RED)
  body.append(s)
  body.append(txt(lx + w + 6, y, "none yet", 10.5, INK))
  y += 20
  body += footer(y, 1280, f.source)
  height = y + 20

  n_fn = len(f.doc["functions"])
  no_fm = [fn["id"] for fn in f.doc["functions"] if not fm_by_fn.get(fn["id"])]
  desc = (f"{f.name} structure tree ({f.a['id']} rev {f.a['revision']}, {f.a['baseline']}): {len(els)} structure elements "
          f"in {len(roots)} root(s), {n_fn} functions with the number of failure modes analyzed for each" +
          (f"; functions without failure modes: {', '.join(no_fm)}" if no_fm else "") + ".")
  return svg_doc(1280, height, f"Figure {f.fig_structure}. {f.name} structure tree ({f.a['id']})", desc,
                 f.fig_structure, f"{f.name} structure and function tree",
                 f"{f.tag} · AIAG-VDA steps 2–3: structure elements by level, functions of each element",
                 f"fmea-plan.md {PLAN_SECTION[f.key]}", f.source, body)


# ---------------------------------------------------------------- failure chains (steps 4-6)

CH_X = (40, 250, 520, 876)
CH_W = (180, 240, 326, 364)


def _cause_box(f: Fmea, fm: dict, c: dict, actions: dict) -> TBox:
  b = TBox("cause", c["id"], CH_W[3])
  ap = c.get("ap")
  if ap and CARDS:
    b.ap = ap
  elif ap:
    b.right_pill = (f"AP {ap}", AP_COL[ap], "#FFFFFF", None)
  else:
    b.right_pill = ("not rated", CARD, MUTED, LINE) if CARDS else ("not rated", "#FFFFFF", SLATE, SLATE)
  add_text(b, c["description"], 10.5, INK, 400, 3)
  meta = []
  if c.get("occurrence") is not None:
    meta.append(f"O{c['occurrence']} · D{c['detection']}")
  if c.get("element"):
    meta.append(f"in {c['element']}")
  if c.get("linked_failure_mode"):
    meta.append(f"→ {c['linked_failure_mode']}")
  if meta:
    add_text(b, " · ".join(meta), 9.8, MUTED, 600, 2)
  for a in c.get("actions", []):
    st = actions[a]["status"]
    fill, fg, stroke = (ACTION_TINT if CARDS else ACTION_COL)[st]
    b.chips.append((f"{a} {ACTION_LABEL[st]}", fill, fg, stroke, CARDS and st == "decision_pending"))
  if not c.get("actions") and c.get("rationale"):
    b.chips.append(("rationale, no action", CARD, MUTED, LINE, False) if CARDS else
                   ("rationale, no action", "#F1F5F9", MUTED, "#CBD5E1", False))
  return b


def _fm_box(fm: dict) -> TBox:
  b = TBox("fm", fm["id"], CH_W[2])
  if CARDS:
    b.head_pills.append((f"S{fm['severity']}", INK, "#FFFFFF", None))
    b.head_pills.append((fm["guideword"].replace("_", " "), CARD, MUTED, LINE))
  else:
    b.head_pills.append((f"S{fm['severity']}", ORANGE, "#FFFFFF", None))
    b.head_pills.append((fm["guideword"].replace("_", " "), "#FFFFFF", ORANGE, "#FDBA74"))
  add_text(b, fm["failure_mode"], 10.5, INK, 600, 3)
  add_text(b, _end_effect(fm), 9.8, MUTED, 400, 2, italic=True, prefix="End effect: ")
  for h in _hazards(fm):
    b.chips.append((h, CARD, INK, LINE, False) if CARDS else (h, "#FFFFFF", ORANGE, ORANGE, False))
  if b.chips:
    b.chip_caption = "hazard"
  return b


def _fn_box(fn: dict, fm_el: str, cont: bool) -> TBox:
  b = TBox("function", fn["id"], CH_W[1])
  if cont:
    b.head_pills.append(("continued", SOFT if CARDS else "#E2E8F0", MUTED, None))
  add_text(b, fn["description"], 10.5, INK, 400, 4)
  if fn["element"] != fm_el:
    add_text(b, f"function of {fn['element']}", 9.5, MUTED, 600, 1)
  for r in fn.get("requirements", []):
    b.chips.append((r, SOFT, MUTED, None, False) if CARDS else (r, "#E2E8F0", INK, None, False))
  return b


def _el_box(x: dict, parent_chain: list[str], cont: bool) -> TBox:
  b = TBox("element", x["id"], CH_W[0], style="external" if x["kind"] == "external" else "element")
  if cont:
    b.head_pills.append(("cont.", SOFT if CARDS else "#E2E8F0", MUTED, None))
  add_text(b, x["name"], 10.5, INK, 600, 4)
  add_text(b, x["kind"].replace("_", " "), 9.5, MUTED, 400, 1)
  if parent_chain:
    add_text(b, "in " + " › ".join(parent_chain), 9.5, MUTED, 400, 2)
  return b


def chain_sheets(f: Fmea) -> list[list[dict]]:
  """Split the failure modes (in structure order) into sheets by estimated height."""
  els = f.elements()
  fns = f.functions()
  actions = f.actions()
  order = {k: i for i, k in enumerate(_ordered_elements(f))}
  fn_order = {fn["id"]: i for i, fn in enumerate(f.doc["functions"])}
  fms = sorted(f.doc["failure_modes"], key=lambda fm: (order[fm["element"]], fn_order[fm["function"]]))
  for fm in fms:
    if fm["element"] not in els or fm["function"] not in fns:
      raise FigError(f"{f.key}: {fm['id']} references an unknown element or function")
  sheets: list[list[dict]] = [[]]
  used = 0.0
  for fm in fms:
    hs = [_cause_box(f, fm, c, actions).measure() for c in fm["causes"]]
    h = max(sum(hs) + SIB_GAP["cause"] * max(len(hs) - 1, 0), _fm_box(fm).measure()) + SIB_GAP["fm"]
    if sheets[-1] and used + h > MAX_SHEET_H:
      sheets.append([])
      used = 0.0
    sheets[-1].append(fm)
    used += h + 4
  return sheets


def render_chain_sheet(f: Fmea, fms: list[dict], no: int, total: int, seen_fn: set, seen_el: set) -> str:
  els = f.elements()
  fns = f.functions()
  actions = f.actions()
  roots: list[TBox] = []
  cur_el = cur_fn = None
  el_box = fn_box = None
  for fm in fms:
    if fm["element"] != cur_el:
      x = els[fm["element"]]
      chain, p = [], x.get("parent")
      while p:
        chain.insert(0, p)
        p = els[p].get("parent")
      el_box = _el_box(x, chain, fm["element"] in seen_el)
      seen_el.add(fm["element"])
      el_box.x = CH_X[0]
      roots.append(el_box)
      cur_el, cur_fn = fm["element"], None
    if fm["function"] != cur_fn:
      fn_box = _fn_box(fns[fm["function"]], fm["element"], (fm["element"], fm["function"]) in seen_fn)
      seen_fn.add((fm["element"], fm["function"]))
      fn_box.x = CH_X[1]
      el_box.children.append(fn_box)
      cur_fn = fm["function"]
    fmb = _fm_box(fm)
    fmb.x = CH_X[2]
    fn_box.children.append(fmb)
    for c in fm["causes"]:
      cb = _cause_box(f, fm, c, actions)
      cb.x = CH_X[3]
      fmb.children.append(cb)

  body: list[str] = []
  heads = ("Structure element", "Function (step 3)", "Failure mode · S · end effect (step 4)",
           "Failure cause · O · D · AP · actions (steps 4–6)")
  for x, label in zip(CH_X, heads):
    body.append(txt(x, 108, label.upper(), 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  bottom = place_tree(roots, 122)
  if CARDS:
    body.insert(0, rect(0, 83, 1280, bottom - 69, "url(#dots)"))
  draw_tree(roots, body)

  y = bottom + 26
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  body.append(txt(lx, y, "Legend", 10.5, INK, 700))
  lx += 56
  for ap in "HML":
    s, w = ap_pill(lx, y - 11, ap) if CARDS else pill(lx, y - 11, f"AP {ap}", AP_COL[ap], "#FFFFFF")
    body.append(s)
    lx += w + 4
  body.append(txt(lx + 4, y, "Action Priority as rated (rating-tables §5)", 10.5, INK))
  lx += 8 + tw("Action Priority as rated (rating-tables §5)", 10.5) + 20
  used_status = sorted({actions[a]["status"] for fm in fms for c in fm["causes"] for a in c.get("actions", [])},
                       key=list(ACTION_COL).index)
  for st in used_status:
    fill, fg, stroke = (ACTION_TINT if CARDS else ACTION_COL)[st]
    s, w = pill(lx, y - 11, f"ACT {ACTION_LABEL[st]}", fill, fg, stroke, dashed=CARDS and st == "decision_pending")
    body.append(s)
    lx += w + 4
  if any(not c.get("actions") and c.get("rationale") for fm in fms for c in fm["causes"]):
    s, w = (pill(lx, y - 11, "rationale, no action", CARD, MUTED, LINE) if CARDS else
            pill(lx, y - 11, "rationale, no action", "#F1F5F9", MUTED, "#CBD5E1"))
    body.append(s)
    lx += w + 4
  body.append(txt(lx + 4, y, "action status (step 6)", 10.5, INK))
  y += 20
  body.append(txt(40, y, "S = severity of the failure mode (max of its effects); O / D = occurrence / detection of the cause; "
                  "“in <element>” = structure element where the cause lies; “→” = linked failure mode in another FMEA; "
                  "hazard = HARA hazard of an end effect.", 10, MUTED))
  y += 18
  body += footer(y, 1280, f.source)
  height = y + 20

  first, last = fms[0]["id"], fms[-1]["id"]
  n_c = sum(len(fm["causes"]) for fm in fms)
  desc = (f"{f.name} failure chains, sheet {no} of {total} ({f.a['id']} rev {f.a['revision']}): failure modes {first} to "
          f"{last} ({len(fms)} failure modes, {n_c} causes), each drawn as structure element, function, failure mode "
          f"with severity, guideword and end effect, and its causes with occurrence, detection, Action Priority and actions.")
  sheet = f" — sheet {no} of {total}" if total > 1 else ""
  return svg_doc(1280, height, f"Figure {f.fig_chains}. {f.name} failure chains{sheet} ({f.a['id']})", desc,
                 f.fig_chains, f"{f.name} failure chains{sheet}",
                 f"{f.tag} · {first} … {last} · {n_c} causes on this sheet",
                 f"fmea-plan.md {PLAN_SECTION[f.key]}", f.source, body)


# ---------------------------------------------------------------- SW FMEA: predicted effect of actions (step 6)

def _predicted(f: Fmea) -> dict[str, tuple[dict, list[str]]]:
  """cause id -> (best revised rating, actions giving it) for causes linked to actions that carry `revised`."""
  acts = f.actions()
  out: dict[str, tuple[dict, list[str]]] = {}
  for fm, c in f.causes():
    for a in c.get("actions", []):
      rev = acts[a].get("revised")
      if not rev or acts[a]["status"] == "not_implemented":
        continue
      exp = compute_ap(rev["severity"], rev["occurrence"], rev["detection"])
      if rev.get("ap") != exp:
        raise FigError(f"{f.key}: {a} revised ap {rev.get('ap')} but the AP table gives {exp}")
      prev = out.get(c["id"])
      if prev is None or "LMH".index(rev["ap"]) < "LMH".index(prev[0]["ap"]):
        out[c["id"]] = (rev, [a])
      elif rev["ap"] == prev[0]["ap"]:
        prev[1].append(a)
  return out


def render_action_effect(f: Fmea, fig: str) -> str:
  acts = f.actions()
  causes = {c["id"]: (fm, c) for fm, c in f.causes()}
  pred = _predicted(f)
  revised_actions = [a for a in f.doc["actions"] if a.get("revised")]
  referenced = {a for _, c in f.causes() for a in c.get("actions", [])}
  body: list[str] = []

  # summary bars
  cur = {"H": 0, "M": 0, "L": 0}
  aft = {"H": 0, "M": 0, "L": 0}
  for cid, (fm, c) in causes.items():
    if c.get("ap"):
      cur[c["ap"]] += 1
      aft[pred[cid][0]["ap"] if cid in pred else c["ap"]] += 1
  total = sum(cur.values())
  y = 104
  body.append(txt(40, y, "RATED CAUSES BY ACTION PRIORITY", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  bx, bw = 330, 760
  for label, counts, planned in (("As rated today", cur, False),
                                 ("If every action with a predicted rating were completed", aft, True)):
    y += 30
    for k, ln in enumerate(wrap(label, 270, 11, 600)):
      body.append(txt(40, y + 13 + k * 13 - (6 if len(wrap(label, 270, 11, 600)) > 1 else 0), ln, 11, INK, 600))
    x = bx
    for ap in "HML":
      if not counts[ap]:
        continue
      w = bw * counts[ap] / total
      if planned:
        body.append(rect(x, y, w, 22, "url(#hatchA)" if ap != "H" else AP_TINT["H"], AP_COL[ap], 1.4, 0,
                         ' stroke-dasharray="5 3"'))
        fg = AP_COL[ap]
      else:
        body.append(rect(x, y, w, 22, AP_COL[ap]))
        fg = "#FFFFFF"
      lab = f"{ap} {counts[ap]}"
      if tw(lab, 10.5, 700) + 8 < w:
        body.append(txt(x + w / 2, y + 15, lab, 10.5, fg, 700, anchor="middle"))
      x += w
    body.append(txt(bx + bw + 14, y + 15, " · ".join(f"{ap} {counts[ap]}" for ap in "HML"), 10.5,
                    AMBER if planned else INK, 700))
  y += 30
  body.append(txt(bx, y + 12, f"{total} rated causes. Prediction only: the hatched bar uses the `revised` S/O/D of open actions; none of these ratings "
                  "has been achieved or verified.", 10, AMBER, 600))
  y += 34

  # per-action rows
  body.append(line(40, y, 1240, y))
  y += 22
  heads = ((40, "ACTION (STEP 6)"), (420, "CAUSES IT ADDRESSES · AS RATED"), (860, "PREDICTED AFTER THE ACTION"))
  for x, h in heads:
    body.append(txt(x, y, h, 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  y += 14
  for a in revised_actions:
    rev = a["revised"]
    linked = [cid for cid, (fm, c) in causes.items() if a["id"] in c.get("actions", [])]
    st = a["status"]
    # left: action box
    ab = TBox("cause", a["id"], 360, style="action" if CARDS else "")
    fill, fg, stroke = (ACTION_TINT if CARDS else ACTION_COL)[st]
    ab.right_pill = (ACTION_LABEL[st], fill, fg, stroke)
    ab.head_pills.append((a["kind"].replace("_", " "), SOFT if CARDS else "#E2E8F0", MUTED, None))
    add_text(ab, a["description"], 10.5, INK, 400, 4)
    if a.get("evidence"):
      add_text(ab, a["evidence"], 9.5, MUTED, 400, 3, italic=True, prefix="Evidence: ")
    ab.x, ab.y = 40, y
    ab.measure()
    # middle: causes grouped by identical as-rated S/O/D
    groups: dict[tuple, list[str]] = {}
    for cid in linked:
      fm, c = causes[cid]
      groups.setdefault((fm["severity"], c["occurrence"], c["detection"], c["ap"]), []).append(cid)
    mid: list[str] = []
    my = y + 4
    if not linked:
      mid.append(txt(420, my + 12, "Not referenced by any cause: the predicted rating", 10.5, RED, 600))
      mid.append(txt(420, my + 26, "cannot be attributed (fmea_lint warning).", 10.5, RED, 600))
      my += 34
    for (s, o, d, ap), cids in sorted(groups.items(), key=lambda kv: (-"LMH".index(kv[0][3]), kv[0])):
      p, w = pill(420, my, f"AP {ap}", AP_COL[ap], "#FFFFFF")
      mid.append(p)
      mid.append(txt(420 + w + 6, my + 11, f"S{s} O{o} D{d} · {len(cids)} cause{'s' if len(cids) != 1 else ''}", 10.5, INK, 600))
      my += PILL_H + 4
      cx = 420
      for cid in cids:
        cw = pill_w(cid)
        if cx + cw > 800:
          cx = 420
          my += PILL_H + 3
        p, _ = pill(cx, my, cid, "#F8FAFC", INK, "#CBD5E1")
        mid.append(p)
        cx += cw + 4
      my += PILL_H + 8
    # right: predicted box
    rh = 58
    row_h = max(ab.h, my - y, rh)
    ry = y + (row_h - rh) / 2
    planned_note = {"open": "planned · not achieved", "in_progress": "in progress · not verified",
                    "decision_pending": "decision pending · not achieved",
                    "completed": "action completed · rating not verified"}.get(st, "not achieved")
    right = [rect(860, ry, 380, rh, "url(#hatchA)", AMBER, 1.4, 8, ' stroke-dasharray="5 3"')]
    p, w = pill(874, ry + 10, f"AP {rev['ap']}", "#FFFFFF", AP_COL[rev["ap"]], AP_COL[rev["ap"]], dashed=True)
    right.append(p)
    right.append(txt(874 + w + 8, ry + 22, f"S{rev['severity']} O{rev['occurrence']} D{rev['detection']}", 12, INK, 700))
    right.append(rect(872, ry + 32, tw(planned_note, 10, 700) + 8, 16, "#FFFFFF", None, 0, 3))
    right.append(txt(876, ry + 44, planned_note, 10, AMBER, 700))
    # arrow from middle to right
    ay = ry + rh / 2
    arrow = f'<path d="M820 {n(ay)}H852" fill="none" stroke="#475569" stroke-width="1.4" stroke-dasharray="4 3" marker-end="url(#aG)"/>'
    draw_tbox(ab, body)
    body += mid + ([arrow] if linked else []) + right
    y += row_h + 14
    body.append(line(40, y - 7, 1240, y - 7, "#F1F5F9"))

  # actions in progress / completed without a predicted rating
  others = [a for a in f.doc["actions"] if not a.get("revised") and a["status"] in ("in_progress", "completed")]
  if others:
    y += 8
    body.append(txt(40, y, "Actions in progress or completed without a predicted rating: " +
                    ", ".join(f"{a['id']} ({ACTION_LABEL[a['status']]})" for a in others) + ".", 10.5, MUTED))
    y += 10
  unref = [a["id"] for a in f.doc["actions"] if a["id"] not in referenced]
  y += 16
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  s, w = pill(lx, y - 11, "AP H", RED, "#FFFFFF")
  body.append(s)
  lx += w + 6
  body.append(txt(lx, y, "as rated (solid)", 10.5, INK))
  lx += tw("as rated (solid)", 10.5) + 20
  body.append(rect(lx, y - 11, 34, 14, "url(#hatchA)", AMBER, 1.4, 4, ' stroke-dasharray="5 3"'))
  body.append(txt(lx + 40, y, "predicted by the action's `revised` rating — not achieved, not verified (hatched, dashed)", 10.5, INK))
  y += 18
  body.append(txt(40, y, "AP recomputed from the revised S/O/D with the AIAG-VDA table (rating-tables §5) and checked against "
                  "the stored value. Actions not referenced by any cause: " + (", ".join(unref) if unref else "none") + ".",
                  10, MUTED))
  y += 18
  body += footer(y, 1280, f.source)
  height = y + 20
  desc = (f"SW FMEA ({f.a['id']} rev {f.a['revision']}): {total} rated causes, as rated "
          f"H {cur['H']}, M {cur['M']}, L {cur['L']}; predicted if every action with a revised rating were completed "
          f"H {aft['H']}, M {aft['M']}, L {aft['L']}. One row per action with a revised rating "
          f"({', '.join(a['id'] for a in revised_actions)}) showing the causes it addresses and the predicted rating, "
          "which is not achieved or verified.")
  return svg_doc(1280, height, f"Figure {fig}. SW FMEA action effect (predicted, not achieved)", desc, fig,
                 "SW FMEA — Action Priority before and after planned actions",
                 f"{f.tag} · actions that record a predicted (`revised`) rating, and the causes they address",
                 "fmea-plan.md §3.3", f.source, body)


# ---------------------------------------------------------------- SW FMEA: O x D per element (step 5)

def _cause_element(fm: dict, c: dict) -> str:
  return c.get("element") or fm["element"]


def _causes_by_element(f: Fmea) -> list[tuple[dict, list[tuple[dict, dict]]]]:
  """Elements that carry causes, in structure order, with their (failure mode, cause) pairs."""
  els = f.elements()
  by: dict[str, list] = {}
  for fm, c in f.causes():
    k = _cause_element(fm, c)
    if k not in els:
      raise FigError(f"{f.key}: {c['id']} names unknown element {k}")
    by.setdefault(k, []).append((fm, c))
  return [(els[k], by[k]) for k in _ordered_elements(f) if k in by]


def render_od_elements(f: Fmea, fig: str) -> str:
  pred = _predicted(f)
  groups = _causes_by_element(f)
  body: list[str] = []
  cols, cell = 8, 11
  pw, gx_off = 150, 22          # panel width; grid offset inside the panel (room for the O axis)
  gw = 10 * cell
  y = 100
  rated = [(fm, c) for fm, c in f.causes() if c.get("ap")]
  hs = [(fm, c) for fm, c in rated if c["ap"] == "H"]
  hd = {"D 9–10": sum(1 for _, c in hs if c["detection"] >= 9), "D 5–8": sum(1 for _, c in hs if 5 <= c["detection"] <= 8),
        "D 1–4": sum(1 for _, c in hs if c["detection"] <= 4)}
  body.append(txt(40, y + 4, f"{len(rated)} rated causes on {len(groups)} elements · AP H {len(hs)}, of which "
                  + ", ".join(f"{v} at {k}" for k, v in hd.items()) + ". Each panel is one element: where its causes sit in "
                  "the AP table, and where the actions with a predicted rating would move them.", 11, INK, 600))
  y += 26
  ph = 18 + 16 + gw + 22        # id line, name line, grid, D axis
  grids: dict[int, str] = {}    # one AP background per severity, drawn once in <defs> and reused
  for i, (el, pairs) in enumerate(groups):
    r, k = divmod(i, cols)
    x0 = 40 + k * pw
    y0 = y + r * (ph + 18)
    s_max = max(fm["severity"] for fm, _ in pairs)
    nh = sum(1 for _, c in pairs if c.get("ap") == "H")
    body.append(txt(x0, y0 + 11, el["id"].replace("SWF-SE-", "SE-"), 10.5, INK, 700))
    tag = f"{len(pairs)} · H {nh}" + (f" · S{s_max}" if s_max < 9 else "")
    body.append(txt(x0 + gx_off + gw, y0 + 11, tag, 9.5, RED if nh else MUTED, 700, anchor="end"))
    body.append(txt(x0, y0 + 25, fit(el["name"], gx_off + gw, 9), 9, MUTED))
    gy = y0 + 34
    gx = x0 + gx_off
    if s_max not in grids:
      grids[s_max] = "".join(rect((d - 1) * cell, oi * cell, cell, cell, AP_TINT[compute_ap(s_max, o, d)], "#FFFFFF", 0.8)
                             for oi, o in enumerate(range(10, 0, -1)) for d in range(1, 11))
    body.append(f'<use href="#odg{s_max}" x="{n(gx)}" y="{n(gy)}"/>')
    for o in (10, 5, 1):
      body.append(txt(gx - 4, gy + (10 - o) * cell + cell / 2 + 3, str(o), 8, MUTED, anchor="end"))
    for d in (1, 5, 10):
      body.append(txt(gx + (d - 0.5) * cell, gy + gw + 10, str(d), 8, MUTED, anchor="middle"))

    def ctr(o, d, gx=gx, gy=gy):
      return gx + (d - 0.5) * cell, gy + (10 - o + 0.5) * cell

    # predicted moves first, under the markers
    for _, c in pairs:
      if c["id"] in pred:
        rv = pred[c["id"]][0]
        (ax, ay), (bx, by) = ctr(c["occurrence"], c["detection"]), ctr(rv["occurrence"], rv["detection"])
        if (ax, ay) != (bx, by):
          body.append(f'<path d="M{n(ax)} {n(ay)}L{n(bx)} {n(by)}" fill="none" stroke="#475569" stroke-width="1" '
                      'stroke-dasharray="2.5 2"/>')
        body.append(f'<circle cx="{n(bx)}" cy="{n(by)}" r="3.6" fill="#FFFFFF" stroke="{AP_COL[rv["ap"]]}" '
                    'stroke-width="1.4" stroke-dasharray="2 1.4"/>')
    cnt: dict[tuple[int, int], list[dict]] = {}
    for _, c in pairs:
      cnt.setdefault((c["occurrence"], c["detection"]), []).append(c)
    for (o, d), cs in sorted(cnt.items()):
      cx, cy = ctr(o, d)
      ap = min((c["ap"] for c in cs), key="HML".index)
      tip = "; ".join(f"{c['id']} O{o} D{d} AP {c['ap']}" for c in cs)
      body.append(f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{4.6 if len(cs) == 1 else 5.4}" fill="{AP_COL[ap]}">'
                  f'<title>{e(tip)}</title></circle>')
      if len(cs) > 1:
        body.append(txt(cx, cy + 2.9, str(len(cs)), 7.5, "#FFFFFF", 700, anchor="middle"))
  body.insert(0, "<defs>" + "".join(f'<g id="odg{s}">{g}</g>' for s, g in sorted(grids.items())) + "</defs>")
  rows = (len(groups) + cols - 1) // cols
  y += rows * (ph + 18) + 6
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  for ap in "HML":
    body.append(rect(lx, y - 11, 14, 14, AP_TINT[ap]))
    body.append(f'<circle cx="{n(lx + 26)}" cy="{n(y - 4)}" r="5" fill="{AP_COL[ap]}"/>')
    lab = f"AP {ap} region / cause rated {ap}"
    body.append(txt(lx + 38, y, lab, 10.5, INK))
    lx += 38 + tw(lab, 10.5) + 22
  body.append(f'<circle cx="{n(lx + 6)}" cy="{n(y - 4)}" r="3.6" fill="#FFFFFF" stroke="{AMBER}" stroke-width="1.4" '
              'stroke-dasharray="2 1.4"/>')
  body.append(f'<path d="M{n(lx + 16)} {n(y - 4)}H{n(lx + 34)}" stroke="#475569" stroke-dasharray="2.5 2"/>')
  body.append(txt(lx + 40, y, "predicted by an action's `revised` rating (not achieved, not verified)", 10.5, INK))
  y += 18
  body.append(txt(40, y, "Rows: occurrence O 10 (top) to 1; columns: detection D 1 to 10. Background = AP from the AIAG-VDA table "
                  "(rating-tables §5) at the element's highest severity; a number in a marker counts causes at that O and D; "
                  "the tag gives causes · AP H.", 10, MUTED))
  y += 15
  body.append(txt(40, y, "A cause far right (D 9–10) is high because no targeted test detects it; far up, because the code is "
                  "likely to be wrong. AP values are those stored in the YAML (fmea_lint checks them against the table).",
                  10, MUTED))
  y += 18
  body += footer(y, 1280, f.source)
  desc = (f"SW FMEA ({f.a['id']} rev {f.a['revision']}): one occurrence by detection grid per element, {len(groups)} elements, "
          f"{len(rated)} rated causes, AP H {len(hs)} ({', '.join(f'{k} {v}' for k, v in hd.items())}). Dashed markers show "
          f"the predicted rating of {len(pred)} causes whose actions record a revised rating; none is achieved.")
  return svg_doc(1280, y + 20, f"Figure {fig}. SW FMEA occurrence and detection by element", desc, fig,
                 "SW FMEA — occurrence × detection, element by element",
                 f"{f.tag} · why each cause has its priority, and what the planned actions are predicted to change",
                 "fmea-plan.md §3.3", f.source, body)


# ---------------------------------------------------------------- SW FMEA: what each D rating rests on

WORKFLOWS = ROOT / ".github" / "workflows"
# Submodules are not checked out in the assurance CI job, so their tests are classified by path, never read.
PANDA_SUITES_RE = re.compile(r"for suite in ([a-z0-9_ ]+); do")
EVIDENCE = (  # key, label, fill, fg
  ("proven", "Test run in CI, D 1–4 (rated as proven: mutation or fault injection)", GREEN, "#FFFFFF"),
  ("targeted", "Targeted test run in CI, not proven (D 5–8)", TEAL, "#FFFFFF"),
  ("generic", "Only a generic test run in CI (D 9–10)", "#94A3B8", "#FFFFFF"),
  ("not_run", "Test cited, but CI does not run it", ORANGE, "#FFFFFF"),
  ("hardware", "Test runs only on a device or HITL rig", "#6D5BD0", "#FFFFFF"),
  ("none", "No test cited", "#FFFFFF", RED),
)
EV_COL = {k: (fill, fg) for k, _, fill, fg in EVIDENCE}
TEST_STATE = {"ci": ("run in CI", TEAL), "not_run": ("not run in CI", ORANGE), "hardware": ("hardware only", "#6D5BD0"),
              "missing": ("file not found", RED)}


@dataclass
class TestIndex:
  """How CI treats each cited test file, worked out from the repository (not from the analysis text)."""
  workflows: str
  ignored: list[str]
  native: str
  panda_suites: set[str]

  @classmethod
  def load(cls) -> TestIndex:
    wf = "\n".join(p.read_text() for p in sorted(WORKFLOWS.glob("*.y*ml")))
    runner = (ROOT / "tools" / "test_runner.py").read_text()
    m = re.search(r"IGNORED = \((.*?)\n\)", runner, re.S)
    ignored = re.findall(r'ROOT / "([^"]+)"', m.group(1)) if m else []
    native_p = ROOT / "openpilot" / "test_native.py"
    suites = set()
    sm = PANDA_SUITES_RE.search((WORKFLOWS / "safety.yaml").read_text()) if (WORKFLOWS / "safety.yaml").exists() else None
    if sm:
      suites = set(sm.group(1).split())
    return cls(wf, ignored, native_p.read_text() if native_p.exists() else "", suites)

  def classify(self, path: str) -> tuple[str, str]:
    """(state, reason) with state in ci / not_run / hardware / missing."""
    if path.startswith(".github/workflows/"):
      return ("ci", "a CI workflow") if (ROOT / path).exists() else ("missing", "workflow not found")
    if path in self.workflows:
      return "ci", "named in a CI workflow"
    if path.startswith("opendbc_repo/opendbc/safety/tests/"):
      return "ci", "opendbc safety suite, run by safety.yaml"
    if path.startswith("panda/tests/"):
      suite = path.split("/")[2]
      if suite == "hitl":
        return "hardware", "panda HITL, needs a rig"
      if suite in self.panda_suites:
        return "ci", f"panda suite {suite}, run by safety.yaml"
      return "not_run", "panda suite not in safety.yaml"
    if not path.startswith("openpilot/"):
      return "not_run", "submodule test outside LionDriver CI"
    p = ROOT / path
    if not p.exists():
      return "missing", "cited file not found"
    if p.suffix == ".cc":
      if path.removesuffix(".cc") in self.native:
        return "ci", "native test, run by test_native.py"
      return "not_run", "native test not in test_native.py"
    if any(path == i or path.startswith(i.rstrip("/") + "/") for i in self.ignored):
      return "not_run", "excluded by tools/test_runner.py"
    src = p.read_text()
    if re.search(r"COMMA_HARDWARE_TEST\s*=\s*True|skipUnless\(\s*HARDWARE", src):
      return "hardware", "skipped off device"
    if not re.search(r"^class \w+\([^)]*TestCase", src, re.M):
      return "not_run", "no TestCase: the unittest runner collects 0 tests"
    return "ci", "unit test, collected by tools/test_runner.py"


def _cause_tests(c: dict) -> list[str]:
  return [dc["test"] for dc in c.get("detection_controls", []) if dc.get("test")]


def cause_evidence(c: dict, idx: TestIndex) -> str:
  states = {idx.classify(t)[0] for t in _cause_tests(c)}
  if "ci" in states:
    d = c["detection"]
    return "proven" if d <= 4 else "targeted" if d <= 8 else "generic"
  if "hardware" in states:
    return "hardware"
  return "not_run" if states else "none"


def render_detection_evidence(f: Fmea, fig: str, idx: TestIndex | None = None) -> str:
  idx = idx or TestIndex.load()
  groups = _causes_by_element(f)
  order = [k for k, *_ in EVIDENCE]
  body: list[str] = []
  allc = [c for _, c in f.causes()]
  ev = {c["id"]: cause_evidence(c, idx) for c in allc}
  tot = {k: sum(1 for v in ev.values() if v == k) for k in order}
  y = 100
  body.append(txt(40, y + 4, "ALL CAUSES BY WHAT THEIR DETECTION RATING RESTS ON", 9.5, MUTED, 700,
                  extra=' letter-spacing=".06em"'))
  y += 14
  x, bw = 40.0, 1200
  for k in order:
    if not tot[k]:
      continue
    w = bw * tot[k] / len(allc)
    fill, fg = EV_COL[k]
    body.append(rect(x, y, w, 22, fill, RED if k == "none" else None, 1.2))
    if tw(str(tot[k]), 10.5, 700) + 6 < w:
      body.append(txt(x + w / 2, y + 15, str(tot[k]), 10.5, fg, 700, anchor="middle"))
    x += w
  y += 42
  lx, ly = 40, y
  for k, lab, fill, _ in EVIDENCE:
    lab = f"{lab} · {tot[k]}"
    if lx + 20 + tw(lab, 10.5) > 1240:
      lx, ly = 40, ly + 18
    body.append(rect(lx, ly - 11, 13, 13, fill, RED if k == "none" else None, 1.2, 2))
    body.append(txt(lx + 19, ly, lab, 10.5, INK))
    lx += 19 + tw(lab, 10.5) + 22
  y = ly + 22
  body.append(line(40, y, 1240, y))
  y += 22
  # left: one row per element; right: the cited test files
  body.append(txt(40, y, "CAUSES PER ELEMENT", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  rx = 640
  body.append(txt(rx, y, "CITED TEST FILES · HOW CI TREATS THEM · CAUSES CITING", 9.5, MUTED, 700,
                  extra=' letter-spacing=".06em"'))
  y += 12
  top = y
  sq, lab_w = 15, 300
  for el, pairs in groups:
    body.append(txt(40, y + 12, el["id"].replace("SWF-SE-", "SE-"), 10, INK, 700))
    body.append(txt(86, y + 12, fit(el["name"], lab_w - 54, 10), 10, MUTED))
    cs = sorted((c for _, c in pairs), key=lambda c: (order.index(ev[c["id"]]), c["id"]))
    for j, c in enumerate(cs):
      fill, _ = EV_COL[ev[c["id"]]]
      tests = _cause_tests(c)
      tip = f"{c['id']} D{c['detection']} AP {c['ap']}: " + (", ".join(f"{t} ({idx.classify(t)[1]})" for t in tests)
                                                            if tests else "no test cited")
      sqr = rect(40 + lab_w + j * sq, y + 2, sq - 3, 14, fill, RED if ev[c["id"]] == "none" else None, 1.2, 2)
      body.append(sqr[:-2] + f"><title>{e(tip)}</title></rect>")
    body.append(txt(40 + lab_w + len(cs) * sq + 4, y + 13, str(len(cs)), 9.5, MUTED))
    y += 20
  left_end = y
  # test file table
  cites: dict[str, list[str]] = {}
  for c in allc:
    for t in dict.fromkeys(_cause_tests(c)):
      cites.setdefault(t, []).append(c["id"])
  st_order = ["not_run", "missing", "hardware", "ci"]
  rows = sorted(cites, key=lambda t: (st_order.index(idx.classify(t)[0]), t))
  ty = top
  for t in rows:
    st, why = idx.classify(t)
    lab, col = TEST_STATE[st]
    p, w = pill(rx, ty + 2, lab, col if st != "missing" else "#FFFFFF", "#FFFFFF" if st != "missing" else RED,
                RED if st == "missing" else None)
    body.append(p)
    body.append(txt(rx + 92, ty + 13, fit(t.removeprefix("openpilot/"), 600 - 92 - 30, 10), 10, INK, 600))
    body.append(txt(1240, ty + 13, str(len(cites[t])), 10, MUTED, 700, anchor="end"))
    body.append(txt(rx + 92, ty + 26, fit(why, 600 - 92, 9.5), 9.5, MUTED, italic=True))
    ty += 32
  y = max(left_end, ty) + 12
  body.append(line(40, y, 1240, y))
  y += 20
  for ln in ("Each square is one cause, coloured by its strongest cited test (detection_controls[].test) and its D rating; hover "
             "for the cause and its tests. How CI treats a file is worked out from the repository, not from the analysis text:",
             "unit tests need a unittest TestCase that tools/test_runner.py collects; COMMA_HARDWARE_TEST or a device skip means "
             "hardware only; panda suites count when safety.yaml runs them; opendbc safety tests and files named in a workflow "
             "count as CI.",
             "Green means the D rating claims proof, not that this figure checked the proof. A test run in CI says nothing "
             "about whether it would fail on the fault."):
    body.append(txt(40, y, ln, 10, MUTED))
    y += 15
  y += 3
  body += footer(y, 1280, f"{f.source}, .github/workflows/, tools/test_runner.py")
  desc = (f"SW FMEA ({f.a['id']} rev {f.a['revision']}): {len(allc)} causes by the evidence behind their detection rating: "
          + ", ".join(f"{k.replace('_', ' ')} {tot[k]}" for k in order) +
          f". One row per element, and the {len(rows)} cited test files with how CI treats each "
          f"({sum(1 for t in rows if idx.classify(t)[0] == 'not_run')} not run in CI).")
  return svg_doc(1280, y + 20, f"Figure {fig}. SW FMEA detection evidence", desc, fig,
                 "SW FMEA — what each detection rating rests on",
                 f"{f.tag} · is the cited test run in CI, only on hardware, or not run at all",
                 "fmea-plan.md §3.3", f.source, body)


# ---------------------------------------------------------------- SW FMEA: what the last baseline changed

def _track(x0: float, y: float, slot: float, before: int, after: int, ap_before: str, ap_after: str, tip: str) -> list[str]:
  """One 1-10 rating track, 1 on the left: the earlier rating hollow, the current one filled, an arrow between."""
  out = [line(x0 + slot / 2, y, x0 + 9.5 * slot, y, "#E2E8F0", 2)]
  for v in range(1, 11):
    out.append(line(x0 + (v - 0.5) * slot, y - 3, x0 + (v - 0.5) * slot, y + 3, "#CBD5E1", 1))
  bx, ax = x0 + (before - 0.5) * slot, x0 + (after - 0.5) * slot
  if before != after:
    sgn = 1 if ax > bx else -1
    out.append(f'<path d="M{n(bx + sgn * 8)} {n(y)}H{n(ax - sgn * 9)}" stroke="#475569" stroke-width="1.3" '
               'marker-end="url(#aG)"/>')
    out.append(f'<circle cx="{n(bx)}" cy="{n(y)}" r="7" fill="#FFFFFF" stroke="{AP_COL[ap_before]}" stroke-width="1.5"/>')
    out.append(txt(bx, y + 3, str(before), 8, AP_COL[ap_before], 700, anchor="middle"))
  out.append(f'<circle cx="{n(ax)}" cy="{n(y)}" r="7" fill="{AP_COL[ap_after]}"><title>{e(tip)}</title></circle>')
  out.append(txt(ax, y + 3, str(after), 8, "#FFFFFF", 700, anchor="middle"))
  return out


def render_baseline_delta(f: Fmea, fig: str) -> str:
  rows = [(fm, c) for fm, c in f.causes() if c.get("previous")]
  if not rows:
    raise FigError(f"{f.key}: no cause records a previous rating")
  order = {k: i for i, k in enumerate(_ordered_elements(f))}

  def gain(fm, c):
    return "HML".index(c["ap"]) - "HML".index(c["previous"]["ap"])

  rows.sort(key=lambda p: (-gain(*p), order[_cause_element(*p)], p[1]["id"]))
  prev_bl = sorted({c["previous"]["baseline"] for _, c in rows})
  out_h = sum(1 for _, c in rows if c["previous"]["ap"] == "H" and c["ap"] != "H")
  o_dn = sum(1 for _, c in rows if c["occurrence"] < c["previous"]["occurrence"])
  d_dn = sum(1 for _, c in rows if c["detection"] < c["previous"]["detection"])
  worse = sum(1 for fm, c in rows if c["occurrence"] > c["previous"]["occurrence"]
              or c["detection"] > c["previous"]["detection"]
              or fm["severity"] > c["previous"].get("severity", fm["severity"]))
  body: list[str] = []
  y = 100
  body.append(txt(40, y + 4, f"{len(rows)} causes re-rated from {', '.join(prev_bl)} to {f.a['baseline']}: {out_h} left AP H, "
                  f"{sum(1 for _, c in rows if c['ap'] == 'H')} are still H. Occurrence fell on {o_dn}, detection on {d_dn}"
                  + (f"; {worse} rated worse." if worse else "; none rated worse."), 11, INK, 600))
  y += 30
  ox, dx, slot = 290, 530, 20
  apx, chx = 760, 880
  body.append(txt(40, y, "CAUSE · ELEMENT", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  body.append(txt(ox, y, "OCCURRENCE", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  body.append(txt(dx, y, "DETECTION", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  body.append(txt(apx, y, "AP", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  body.append(txt(chx, y, "WHAT CHANGED IN THE CODE OR BUILD", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  y += 14
  for x0 in (ox, dx):
    for v in (1, 5, 10):
      body.append(txt(x0 + (v - 0.5) * slot, y, str(v), 8.5, MUTED, anchor="middle"))
  y += 8
  for fm, c in rows:
    p = c["previous"]
    el = _cause_element(fm, c)
    body.append(line(40, y, 1240, y, "#F1F5F9"))
    cy = y + 19
    s_prev = p.get("severity", fm["severity"])
    head = c["id"] + (f" · S{s_prev}→{fm['severity']}" if s_prev != fm["severity"] else "")
    body.append(txt(40, cy - 3, head, 10.5, INK, 700))
    body.append(txt(40, cy + 11, fit(el.replace("SWF-SE-", "SE-") + " · " + fm["failure_mode"], 230, 9), 9, MUTED))
    tip = (f"{c['id']}: {p['baseline']} O{p['occurrence']} D{p['detection']} AP {p['ap']} -> "
           f"{f.a['baseline']} O{c['occurrence']} D{c['detection']} AP {c['ap']}")
    body += _track(ox, cy, slot, p["occurrence"], c["occurrence"], p["ap"], c["ap"], tip)
    body += _track(dx, cy, slot, p["detection"], c["detection"], p["ap"], c["ap"], tip)
    pb, wb = pill(apx, cy - 7.5, p["ap"], "#FFFFFF", AP_COL[p["ap"]], AP_COL[p["ap"]])
    body.append(pb)
    body.append(f'<path d="M{n(apx + wb + 5)} {n(cy)}H{n(apx + wb + 21)}" stroke="#475569" stroke-width="1.3" '
                'marker-end="url(#aG)"/>')
    pa, _ = pill(apx + wb + 26, cy - 7.5, c["ap"], AP_COL[c["ap"]])
    body.append(pa)
    for i, ln in enumerate(wrap(p["change"], 1240 - chx, 9.5, max_lines=2)):
      body.append(txt(chx, cy - 3 + i * 12.5, ln, 9.5, INK))
    y += 40
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  body.append(f'<circle cx="{n(lx + 7)}" cy="{n(y - 4)}" r="7" fill="#FFFFFF" stroke="{RED}" stroke-width="1.5"/>')
  lab = f"rating at {', '.join(prev_bl)} (ring in its AP colour)"
  body.append(txt(lx + 20, y, lab, 10.5, INK))
  lx += 20 + tw(lab, 10.5) + 24
  for ap in "HML":
    body.append(f'<circle cx="{n(lx + 7)}" cy="{n(y - 4)}" r="7" fill="{AP_COL[ap]}"/>')
    lab = f"rating at {f.a['baseline']}, AP {ap}"
    body.append(txt(lx + 20, y, lab, 10.5, INK))
    lx += 20 + tw(lab, 10.5) + 24
  y += 18
  for ln in ("Each row is a cause that records its rating at an earlier baseline (`previous` in the YAML). Tracks run from 1 (left, "
             "better) to 10; a single filled marker means that rating did not change. Sorted by AP gained, then by element.",
             "Causes without a `previous` record are not drawn: they are new at this baseline or were not re-rated. A lower "
             "rating here is credited in the analysis; it is not a claim that the fault was tested in the field."):
    body.append(txt(40, y, ln, 10, MUTED))
    y += 15
  y += 3
  body += footer(y, 1280, f.source)
  desc = (f"SW FMEA ({f.a['id']} rev {f.a['revision']}): {len(rows)} causes re-rated from {', '.join(prev_bl)} to "
          f"{f.a['baseline']}; {out_h} left AP H; occurrence lowered on {o_dn} and detection on {d_dn}. One row per cause "
          "with its occurrence and detection before and after, the AP change and the code or build change credited.")
  return svg_doc(1280, y + 20, f"Figure {fig}. SW FMEA rating changes since the previous baseline", desc, fig,
                 "SW FMEA — what the last baseline changed",
                 f"{f.tag} · which code changes moved which causes, and how far",
                 "fmea-plan.md §3.3", f.source, body)


# ---------------------------------------------------------------- SW FMEA: reaction time by defence layer

LAYERS = (  # key, label, colour, shape
  ("host", "host stops acting (SoC software)", "#334155", "circle"),
  ("envelope", "panda revokes or blocks authority", TEAL, "square"),
  ("alert", "device alert to the driver", AMBER, "triangle"),
  ("siren", "panda siren", "#6D5BD0", "diamond"),
  ("vehicle", "stock ECU reacts", GREEN, "ring"),
)
LAYER_COL = {k: c for k, _, c, _ in LAYERS}
LAYER_SHAPE = {k: s for k, _, _, s in LAYERS}
WARN_LAYERS = ("alert", "siren")
T_MIN, T_MAX = 0.01, 10.0


def layer_mark(shape: str, x: float, y: float, col: str, hollow: bool = False, tip: str = "") -> str:
  fill, extra = ("#FFFFFF", f' stroke="{col}" stroke-width="1.6"') if hollow else (col, "")
  title = f"<title>{e(tip)}</title>" if tip else ""
  if shape == "square":
    return f'<rect x="{n(x - 5)}" y="{n(y - 5)}" width="10" height="10" fill="{fill}"{extra}>{title}</rect>'
  if shape == "triangle":
    return f'<path d="M{n(x)} {n(y - 6)}L{n(x + 6)} {n(y + 5)}L{n(x - 6)} {n(y + 5)}z" fill="{fill}"{extra}>{title}</path>'
  if shape == "diamond":
    return f'<path d="M{n(x)} {n(y - 6.5)}L{n(x + 6.5)} {n(y)}L{n(x)} {n(y + 6.5)}L{n(x - 6.5)} {n(y)}z" fill="{fill}"{extra}>{title}</path>'
  if shape == "ring":
    return f'<circle cx="{n(x)}" cy="{n(y)}" r="5" fill="#FFFFFF" stroke="{col}" stroke-width="2.4">{title}</circle>'
  return f'<circle cx="{n(x)}" cy="{n(y)}" r="5.5" fill="{fill}"{extra}>{title}</circle>'


def fmt_s(t: float) -> str:
  return f"{t * 1000:g} ms" if t < 1 else f"{t:g} s"


def render_reaction_layers(f: Fmea, fig: str) -> str:
  allm = [(fm, m) for fm in f.doc["failure_modes"] for m in fm.get("safety_mechanisms", [])]
  rows = [(fm, [m for m in fm.get("safety_mechanisms", []) if "reaction_s" in m]) for fm in f.doc["failure_modes"]]
  rows = [(fm, ms) for fm, ms in rows if ms]
  if not rows:
    raise FigError(f"{f.key}: no safety mechanism records reaction_s")
  timed = [m for _, ms in rows for m in ms]
  basis: dict[str, int] = {}
  for m in timed:
    basis[m["timing_basis"]] = basis.get(m["timing_basis"], 0) + 1
  no_warn = [fm["id"] for fm, ms in rows if not any(m["layer"] in WARN_LAYERS for m in ms)]
  ax0, ax1 = 330, 900

  def tx(t):
    t = min(max(t, T_MIN), T_MAX)
    return ax0 + (math.log10(t) - math.log10(T_MIN)) / (math.log10(T_MAX) - math.log10(T_MIN)) * (ax1 - ax0)

  body: list[str] = []
  y = 100
  body.append(txt(40, y + 4, f"{len(timed)} of {len(allm)} safety mechanisms carry a reaction time, on {len(rows)} failure modes; "
                  + ", ".join(f"{v} {k.replace('_', '-')}" for k, v in sorted(basis.items()))
                  + f". {len(no_warn)} of those {len(rows)} have no timed warning to the driver.", 11, INK, 600))
  y += 30
  body.append(txt(40, y, "FAILURE MODE", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  body.append(txt(ax0, y, "TIME FROM THE FAULT TO EACH LAYER'S REACTION (LOG SCALE)", 9.5, MUTED, 700,
                  extra=' letter-spacing=".06em"'))
  body.append(txt(930, y, "FIRST TIMED WARNING TO THE DRIVER", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  y += 16
  ticks = [k * 10 ** p for p in range(-2, 1) for k in (1, 2, 5)] + [10.0]
  majors = (0.01, 0.1, 1.0, 10.0)
  for t in majors:
    body.append(txt(tx(t), y, fmt_s(t), 9, MUTED, 600, anchor="middle"))
  y += 8
  for t in ticks:   # grid under the rows
    body.append(line(tx(t), y, tx(t), y + len(rows) * 42 - 6, "#E2E8F0" if t in majors else "#F1F5F9", 1))
  for fm, ms in rows:
    cy = y + 18
    body.append(txt(40, cy - 3, fm["id"], 10.5, INK, 700))
    body.append(txt(40, cy + 11, fit(fm["failure_mode"], ax0 - 60, 9), 9, MUTED))
    body.append(line(ax0, cy, ax1, cy, "#E2E8F0", 1.5))
    for i, m in enumerate(sorted(ms, key=lambda m: m["reaction_s"])):
      x = tx(m["reaction_s"])
      hollow = m["timing_basis"] in ("requirement", "estimate")
      tip = (f"{fm['id']} · {m['layer']} {fmt_s(m['reaction_s'])} ({m['timing_basis'].replace('_', '-')}): "
             f"{m['description']} [{m.get('timing_ref', '')}]")
      body.append(layer_mark(LAYER_SHAPE[m["layer"]], x, cy, LAYER_COL[m["layer"]], hollow, tip))
      body.append(txt(x, cy - 10 if i % 2 == 0 else cy + 18, fmt_s(m["reaction_s"]), 8.5, LAYER_COL[m["layer"]], 700,
                      anchor="middle"))
    warn = sorted((m for m in ms if m["layer"] in WARN_LAYERS), key=lambda m: m["reaction_s"])
    if warn:
      body.append(txt(930, cy + 3, f"{warn[0]['layer']} after {fmt_s(warn[0]['reaction_s'])}", 10, INK, 600))
    else:
      body.append(txt(930, cy + 3, "none timed", 10, ORANGE, 700))
    y += 42
  body.append(line(40, y, 1240, y))
  y += 22
  lx, ly = 40, y
  for _, lab, col, shape in LAYERS:
    if lx + 24 + tw(lab, 10.5) > 1240:
      lx, ly = 40, ly + 18
    body.append(layer_mark(shape, lx + 6, ly - 4, col))
    body.append(txt(lx + 18, ly, lab, 10.5, INK))
    lx += 18 + tw(lab, 10.5) + 22
  y = ly + 18
  for ln in ("Each row is a failure mode with at least one safety mechanism that records `reaction_s`; each mark is one mechanism "
             "at the time from the fault to its layer's reaction. Hover a mark for the mechanism and where its time comes from.",
             "Filled marks are read from the code (code-derived) or measured; hollow marks are a requirement budget or an estimate. "
             "No time here is measured, and the figure does not check any time against an FTTI.",
             "\"None timed\" means no alert or siren mechanism on that row records a time; the driver may still be warned by an "
             "untimed mechanism listed in the YAML."):
    body.append(txt(40, y, ln, 10, MUTED))
    y += 15
  y += 3
  body += footer(y, 1280, f.source)
  desc = (f"SW FMEA ({f.a['id']} rev {f.a['revision']}): reaction times of {len(timed)} of {len(allm)} safety mechanisms "
          f"on {len(rows)} failure modes, by defence layer (host, envelope, alert, siren, vehicle), on a log time axis; "
          + ", ".join(f"{v} {k.replace('_', '-')}" for k, v in sorted(basis.items()))
          + f". {len(no_warn)} rows have no timed warning to the driver.")
  return svg_doc(1280, y + 20, f"Figure {fig}. SW FMEA reaction time by defence layer", desc, fig,
                 "SW FMEA — who catches it, and when",
                 f"{f.tag} · after a fault starts, how long until each layer reacts, and whether the driver is told",
                 "fmea-plan.md §3.3", f.source, body)


# ---------------------------------------------------------------- SW FMEA: where it stops (SOTIF boundary)

BOUNDARY = {  # key: label, fill, fg, stroke
  "functional_safety": ("functional safety", "#FFFFFF", SLATE, SLATE),
  "split": ("split", "#EDE9FE", "#5B21B6", "#7C3AED"),
  "sotif": ("SOTIF", "#7C3AED", "#FFFFFF", None),
}


def _top_element(els: dict, k: str) -> str:
  while els[k].get("parent"):
    k = els[k]["parent"]
  return k


def render_sotif_boundary(f: Fmea, fig: str) -> str:
  els = f.elements()
  tops = [k for k in _ordered_elements(f) if not els[k].get("parent")]
  per: dict[str, dict[str, int]] = {k: {"H": 0, "M": 0, "L": 0} for k in tops}
  fms: dict[str, set] = {k: set() for k in tops}
  for fm, c in f.causes():
    t = _top_element(els, _cause_element(fm, c))
    if c.get("ap"):
      per[t][c["ap"]] += 1
    fms[t].add(fm["id"])
  kinds = {k: (els[k].get("sotif") or {}).get("boundary") for k in tops}
  cnt = {b: sum(1 for v in kinds.values() if v == b) for b in BOUNDARY}
  missing = [k for k, v in kinds.items() if not v]
  body: list[str] = []
  y = 100
  body.append(txt(40, y + 4, f"{len(tops)} top-level elements: {cnt['functional_safety']} functional safety only, {cnt['split']} "
                  f"split between this FMEA and SOTIF, {cnt['sotif']} SOTIF only"
                  + (f", {len(missing)} with no boundary recorded." if missing else ".")
                  + " Left of the line: software faults rated here. Right: performance limits with correct software.",
                  11, INK, 600))
  y += 30
  div, bmax = 640, 200
  tx0 = div + 14 + max(pill_w(v[0]) for v in BOUNDARY.values()) + 12
  scale = bmax / max(1, max(sum(v.values()) for v in per.values()))
  body.append(txt(40, y, "ELEMENT", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  body.append(txt(div - 12, y, "RATED IN THIS SW FMEA · CAUSES BY AP", 9.5, MUTED, 700, anchor="end",
                  extra=' letter-spacing=".06em"'))
  body.append(txt(div + 14, y, "LEFT TO SOTIF (ISO 21448, WP-C-05)", 9.5, "#5B21B6", 700, extra=' letter-spacing=".06em"'))
  y += 10
  top = y
  rows: list[str] = []
  for k in tops:
    el = els[k]
    so = el.get("sotif") or {}
    b = so.get("boundary")
    part = wrap(so.get("sotif_part", ""), 1240 - tx0, 9.5, max_lines=3) if so.get("sotif_part") else []
    h = max(36, 32 + 13 * (len(part) + (1 if so.get("ref") else 0) - 1))
    cy = y + 18
    rows.append(line(40, y, 1240, y, "#F1F5F9"))
    rows.append(txt(40, cy - 3, k.replace("SWF-SE-", "SE-"), 10.5, INK, 700))
    rows.append(txt(40, cy + 11, fit(el["name"], 290, 9), 9, MUTED))
    tot = sum(per[k].values())
    x = div - 12 - tot * scale
    for ap in "LMH":
      w = per[k][ap] * scale
      if w:
        tip = f"{k}: {per[k][ap]} cause(s) AP {ap}"
        rows.append(rect(x, cy - 7, w, 14, AP_COL[ap])[:-2] + f"><title>{e(tip)}</title></rect>")
        x += w
    lab = f"{len(fms[k])} FM · {tot} causes" if tot else "no causes rated"
    rows.append(txt(div - 16 - tot * scale, cy + 4, lab, 9.5, MUTED if tot else ORANGE, 600, anchor="end"))
    lab_b, fill, fg, stroke = BOUNDARY[b] if b else ("not recorded", "#FFFFFF", ORANGE, ORANGE)
    p, _ = pill(div + 14, cy - 7.5, lab_b, fill, fg, stroke)
    rows.append(p)
    if part:
      for i, ln in enumerate(part):
        rows.append(txt(tx0, cy + 3.5 + i * 13, ln, 9.5, INK))
      if so.get("ref"):
        rows.append(txt(tx0, cy + 3.5 + len(part) * 13, so["ref"], 9, "#5B21B6", 600))
    elif b == "functional_safety":
      rows.append(txt(tx0, cy + 3.5, "no SOTIF part: failures here come from faults, rated on the left", 9.5, MUTED, italic=True))
    y += h
  body.append(rect(div, top, 1240 - div, y - top, "#FAF5FF"))
  body.append(line(div, top - 4, div, y + 4, "#7C3AED", 2))
  body += rows
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  for ap in "HML":
    body.append(rect(lx, y - 11, 14, 14, AP_COL[ap]))
    lab = f"causes rated AP {ap}"
    body.append(txt(lx + 20, y, lab, 10.5, INK))
    lx += 20 + tw(lab, 10.5) + 22
  for lab, fill, fg, stroke in BOUNDARY.values():
    p, w = pill(lx, y - 11, lab, fill, fg, stroke)
    body.append(p)
    lx += w + 10
  body.append(txt(lx + 4, y, "boundary recorded on the element (`sotif.boundary`)", 10.5, INK))
  y += 18
  for ln in ("Rows are the top-level elements in structure order; causes of child elements count toward their parent. A split "
             "element has software faults rated here and a performance part owned by SOTIF, quoted from `sotif.sotif_part` with "
             "its WP-C-05 reference.",
             "The right lane says what this FMEA does not rate; it is not a claim that the SOTIF analysis covers it."):
    body.append(txt(40, y, ln, 10, MUTED))
    y += 15
  y += 3
  body += footer(y, 1280, f.source)
  desc = (f"SW FMEA ({f.a['id']} rev {f.a['revision']}): the functional safety / SOTIF boundary for {len(tops)} top-level "
          f"elements: {cnt['functional_safety']} functional safety only, {cnt['split']} split, {cnt['sotif']} SOTIF only. Per "
          "element, the causes rated here by AP, and the performance part left to SOTIF with its WP-C-05 reference.")
  return svg_doc(1280, y + 20, f"Figure {fig}. SW FMEA and SOTIF boundary", desc, fig,
                 "SW FMEA — where it stops and SOTIF starts",
                 f"{f.tag} · per element, which failures this FMEA rates and which are performance limits for SOTIF",
                 "fmea-plan.md §3.3", f.source, body)


# ---------------------------------------------------------------- AP overview (all four FMEAs)

def render_ap_overview(fmeas: list[Fmea], fig: str) -> str:
  body: list[str] = []
  pw, gap = 285, 20
  cell = 22
  top = 100
  max_y = 0.0
  totals = []
  for i, f in enumerate(fmeas):
    x0 = 40 + i * (pw + gap)
    acts = f.actions()
    rated = [(fm, c) for fm, c in f.causes() if c.get("ap")]
    unrated = [c["id"] for fm, c in f.causes() if not c.get("ap")]
    counts = {ap: sum(1 for _, c in rated if c["ap"] == ap) for ap in "HML"}
    totals.append((f, counts))
    y = top
    body.append(txt(x0, y + 14, f.name, 15, INK, 700))
    body.append(txt(x0, y + 31, f"{f.a['id']} rev {f.a['revision']} · {f.a['baseline']} · {f.a['status']}", 10.5, MUTED))
    body.append(txt(x0, y + 46, f"{len(rated)} rated causes" + (f" · {len(unrated)} not rated" if unrated else ""),
                    10.5, MUTED))
    y += 58
    # AP bar
    x = x0
    tot = max(len(rated), 1)
    for ap in "HML":
      if not counts[ap]:
        continue
      w = pw * counts[ap] / tot
      body.append(rect(x, y, w, 22, AP_COL[ap]))
      lab = f"{ap} {counts[ap]}"
      if tw(lab, 10.5, 700) + 6 < w:
        body.append(txt(x + w / 2, y + 15, lab, 10.5, "#FFFFFF", 700, anchor="middle"))
      x += w
    small = [f"{ap} {counts[ap]}" for ap in "HML" if counts[ap] and tw(f"{ap} {counts[ap]}", 10.5, 700) + 6 >= pw * counts[ap] / tot]
    y += 22
    lab_y = y + 14
    body.append(txt(x0, lab_y, "AP as rated: " + "  ".join(f"{ap} {counts[ap]}" for ap in "HML"), 10.5, INK, 600))
    y += 30

    # O x D grid for S 9-10
    body.append(txt(x0, y + 4, "Causes with S 9–10 by occurrence × detection", 10, MUTED, 700))
    y += 14
    gx = x0 + 30
    grid: dict[tuple[int, int], int] = {}
    others = []
    for fm, c in rated:
      if fm["severity"] >= 9:
        grid[(c["occurrence"], c["detection"])] = grid.get((c["occurrence"], c["detection"]), 0) + 1
      else:
        others.append((fm, c))
    for oi, o in enumerate(range(10, 0, -1)):
      cy = y + oi * cell
      body.append(txt(gx - 6, cy + cell / 2 + 3.5, str(o), 9.5, MUTED, anchor="end"))
      for d in range(1, 11):
        cx = gx + (d - 1) * cell
        ap = compute_ap(10, o, d)
        k = grid.get((o, d), 0)
        body.append(rect(cx, cy, cell, cell, AP_TINT[ap], "#FFFFFF", 1))
        if k:
          body.append(f'<circle cx="{n(cx + cell / 2)}" cy="{n(cy + cell / 2)}" r="9.5" fill="{AP_COL[ap]}"/>')
          body.append(txt(cx + cell / 2, cy + cell / 2 + 3.6, str(k), 10 if k < 10 else 9, "#FFFFFF", 700, anchor="middle"))
    gy = y + 10 * cell
    for d in range(1, 11):
      body.append(txt(gx + (d - 0.5) * cell, gy + 12, str(d), 9.5, MUTED, anchor="middle"))
    body.append(txt(gx + 5 * cell, gy + 26, "Detection D →", 9.5, MUTED, 600, anchor="middle"))
    body.append(f'<text x="{n(x0 + 6)}" y="{n(y + 5 * cell)}" font-size="9.5" fill="{MUTED}" font-weight="600" '
                f'text-anchor="middle" transform="rotate(-90 {n(x0 + 6)} {n(y + 5 * cell)})">Occurrence O →</text>')
    y = gy + 40
    # other severities
    if others:
      body.append(txt(x0, y, "Other severities (not in the grid):", 10, MUTED, 700))
      y += 4
      for fm, c in others:
        y += 15
        p, w = pill(x0, y - 11, f"AP {c['ap']}", AP_COL[c["ap"]], "#FFFFFF")
        body.append(p)
        body.append(txt(x0 + w + 6, y, f"{c['id']}  S{fm['severity']} O{c['occurrence']} D{c['detection']}", 10, INK))
      y += 10
    else:
      body.append(txt(x0, y, "All rated causes have S 9–10.", 10, MUTED))
      y += 6
    # non-H causes listed by id
    for ap in "ML":
      ids = [c["id"] for _, c in rated if c["ap"] == ap]
      if ids:
        y += 16
        lines_ = wrap(f"AP {ap}: " + ", ".join(ids), pw, 10)
        for k, ln in enumerate(lines_):
          body.append(txt(x0, y + k * 13, ln, 10, AP_COL[ap], 600))
        y += 13 * (len(lines_) - 1)
    y += 26
    # treatment of AP H
    hs = [c for _, c in rated if c["ap"] == "H"]
    treat: dict[str, int] = {}
    for c in hs:
      sts = {acts[a]["status"] for a in c.get("actions", [])}
      if not sts:
        k = "rationale" if c.get("rationale") else "none"
      else:
        k = min(sts, key=["completed", "in_progress", "decision_pending", "open", "not_implemented"].index)
      treat[k] = treat.get(k, 0) + 1
    body.append(txt(x0, y, f"AP H causes ({len(hs)}) by treatment", 10, MUTED, 700))
    y += 8
    order = ["completed", "in_progress", "decision_pending", "open", "not_implemented", "rationale", "none"]
    tcol = {"completed": (GREEN, "#FFFFFF", None), "in_progress": (AMBER, "#FFFFFF", None),
            "decision_pending": ("#FDEFD8", AMBER, AMBER), "open": ("#FBE4DF", RED, RED),
            "not_implemented": ("#F1F5F9", SLATE, SLATE), "rationale": ("#F1F5F9", MUTED, "#94A3B8"),
            "none": ("#FFFFFF", RED, RED)}
    tlabel = {"completed": "action completed", "in_progress": "action in progress", "decision_pending": "decision pending",
              "open": "action open", "not_implemented": "not implemented", "rationale": "rationale, no action",
              "none": "no action, no rationale"}
    for k in order:
      if not treat.get(k):
        continue
      y += 6
      fill, fg, stroke = tcol[k]
      w = max(4.0, (pw - 120) * treat[k] / max(len(hs), 1))
      body.append(rect(x0, y, w, 16, fill, stroke, 1, 2))
      body.append(txt(x0 + w + 6, y + 12, f"{treat[k]}  {tlabel[k]}", 10, INK))
      y += 16
    max_y = max(max_y, y)
  y = max_y + 26
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  for ap in "HML":
    body.append(rect(lx, y - 11, 14, 14, AP_TINT[ap]))
    body.append(f'<circle cx="{n(lx + 28)}" cy="{n(y - 4)}" r="7" fill="{AP_COL[ap]}"/>')
    lab = f"AP {ap} region of the AIAG-VDA table / causes rated {ap}"
    body.append(txt(lx + 42, y, lab, 10.5, INK))
    lx += 42 + tw(lab, 10.5) + 22
  y += 18
  body.append(txt(40, y, "Grid background = AP for S 9–10 from the AIAG-VDA table (rating-tables §5); circle = number of causes "
                  "rated at that O and D. AP values are those stored in the YAML (fmea_lint checks them against the table).",
                  10, MUTED))
  y += 18
  body += footer(y, 1280, "analyses/system-fmea.yaml, dfmea.yaml, sw-fmea.yaml, pfmea.yaml")
  height = y + 20
  desc = "Action Priority overview: " + "; ".join(
    f"{f.name} {f.a['id']} rev {f.a['revision']} H {c['H']}, M {c['M']}, L {c['L']}" for f, c in totals) + \
    ". For each FMEA an occurrence by detection grid of the severity 9–10 causes over the AP table, the causes at other " \
    "severities, and how the AP H causes are treated (action status or rationale)."
  return svg_doc(1280, height, f"Figure {fig}. Action Priority overview of the four FMEAs", desc, fig,
                 "Action Priority overview of the four FMEAs",
                 "Ratings as recorded (AIAG-VDA 2019 AP, step 5) · where the causes sit in the AP table · how AP H is treated (step 6)",
                 "fmea-plan.md §4", "analyses/*fmea.yaml", body)


# ================================================================ FMEA-MSR overview (msr-plan.md M3)

# Monitoring bands of rating-tables.md section 7 (RT-3), with the evidence each band needs (msr-plan.md section 4.1).
M_BANDS_MSR = ((1, 4, "M 1–4", "measured FDTI + FRTI within the FTTI"),
               (5, 6, "M 5–6", "code-derived timing within the FTTI, test exists"),
               (7, 8, "M 7–8", "reacts, but incomplete, too slow or no FTTI row"),
               (9, 10, "M 9–10", "no in-field monitor, or the driver must notice"))
M_BAND_COL = ("#2E9E6A", TEAL, AMBER, RED)
BASIS_LABEL = {"measured": "measured", "code_derived": "code-derived", "unknown": "unknown"}
MSR_AP_NOTE = ("MSR AP from the AIAG-VDA FMEA-MSR handbook table for S 9–10 (rating-tables §7.4, RT-3, DQ-207); S 1–8 would "
               "still use the provisional stand-in.")


def msr_rows(f: "Fmea") -> tuple[list[tuple[dict, dict, dict]], list[str]]:
  """(failure mode, cause, msr block) for every cause with an msr block, and the ids of the msr_exempt causes."""
  rated, exempt = [], []
  for fm, c in f.causes():
    if c.get("msr"):
      rated.append((fm, c, c["msr"]))
    elif c.get("msr_exempt"):
      exempt.append(c["id"])
  return rated, exempt


def msr_band(m: int) -> int:
  return next(i for i, (lo, hi, _, _) in enumerate(M_BANDS_MSR) if lo <= m <= hi)


def render_msr_overview(fmeas: list["Fmea"], fig: str) -> str:
  body: list[str] = []
  panels = [f for f in fmeas if f.a.get("msr") and f.a["msr"] != "none"]
  if not panels:
    raise FigError("Figure 4-2: no FMEA has msr rows")
  pw, gap, cell, top = 580, 40, 24, 100
  max_y = 0.0
  totals = []
  for i, f in enumerate(panels):
    x0 = 40 + i * (pw + gap)
    rated, exempt = msr_rows(f)
    acts = f.actions()
    counts = {ap: sum(1 for _, _, m in rated if m["ap"] == ap) for ap in "HML"}
    bands = [0, 0, 0, 0]
    for _, _, m in rated:
      bands[msr_band(m["monitoring"])] += 1
    totals.append((f, len(rated), len(exempt), counts, bands))
    y = top
    body.append(txt(x0, y + 14, f.name, 15, INK, 700))
    body.append(txt(x0, y + 31, f"{f.tag} · msr: {f.a['msr']}", 10.5, MUTED))
    body.append(txt(x0, y + 46, f"{len(rated)} causes rated for monitoring and system response"
                    + (f" · {len(exempt)} rated in another FMEA" if exempt else ""), 10.5, MUTED))
    y += 58
    # MSR AP bar
    x = x0
    tot = max(len(rated), 1)
    for ap in "HML":
      if counts[ap]:
        w = pw * counts[ap] / tot
        body.append(rect(x, y, w, 22, AP_COL[ap]))
        lab = f"MSR AP {ap} {counts[ap]}"
        if tw(lab, 10.5, 700) + 6 < w:
          body.append(txt(x + w / 2, y + 15, lab, 10.5, "#FFFFFF", 700, anchor="middle"))
        x += w
    y += 22
    body.append(txt(x0, y + 14, "MSR AP: " + "  ".join(f"{ap} {counts[ap]}" for ap in "HML"), 10.5, INK, 600))
    y += 34

    # F x M grid (left) and monitoring bands (right)
    body.append(txt(x0, y, "Causes by frequency × monitoring", 10, MUTED, 700))
    y += 10
    gx = x0 + 30
    grid: dict[tuple[int, int], list[str]] = {}
    for fm, c, m in rated:
      grid.setdefault((m["frequency"], m["monitoring"]), []).append(m["ap"])
    for fi, fq in enumerate(range(10, 0, -1)):
      cy = y + fi * cell
      body.append(txt(gx - 6, cy + cell / 2 + 3.5, str(fq), 9.5, MUTED, anchor="end"))
      for mm in range(1, 11):
        cx = gx + (mm - 1) * cell
        bg = compute_ap_msr_s10(fq, mm)
        body.append(rect(cx, cy, cell, cell, AP_TINT[bg], "#FFFFFF", 1))
        aps = grid.get((fq, mm))
        if aps:
          ap = min(aps, key="HML".index)
          k = len(aps)
          body.append(f'<circle cx="{n(cx + cell / 2)}" cy="{n(cy + cell / 2)}" r="10" fill="{AP_COL[ap]}"/>')
          body.append(txt(cx + cell / 2, cy + cell / 2 + 3.6, str(k), 10 if k < 10 else 9, "#FFFFFF", 700, anchor="middle"))
    gy = y + 10 * cell
    for mm in range(1, 11):
      body.append(txt(gx + (mm - 0.5) * cell, gy + 12, str(mm), 9.5, MUTED, anchor="middle"))
    body.append(txt(gx + 5 * cell, gy + 26, "Monitoring M →", 9.5, MUTED, 600, anchor="middle"))
    body.append(f'<text x="{n(x0 + 6)}" y="{n(y + 5 * cell)}" font-size="9.5" fill="{MUTED}" font-weight="600" '
                f'text-anchor="middle" transform="rotate(-90 {n(x0 + 6)} {n(y + 5 * cell)})">Frequency F →</text>')
    # bands to the right of the grid
    bx = gx + 10 * cell + 28
    bw = x0 + pw - bx
    by = y
    body.append(txt(bx, by + 4, "Monitoring band", 10, MUTED, 700))
    by += 12
    for bi, (lo, hi, lab, meaning) in enumerate(M_BANDS_MSR):
      k = bands[bi]
      w = max(3.0, (bw - 40) * k / tot) if k else 0
      if w:
        body.append(rect(bx, by, w, 16, M_BAND_COL[bi], None, 1, 2))
      body.append(txt(bx + w + 6, by + 12, f"{k}", 10.5, INK, 700))
      body.append(txt(bx, by + 30, lab, 10, INK, 700))
      for li, ln in enumerate(wrap(meaning, bw - tw(lab, 10, 700) - 8, 9.5, max_lines=2)):
        body.append(txt(bx + tw(lab, 10, 700) + 6, by + 30 + li * 12, ln, 9.5, MUTED))
      by += 48
    # timing basis
    basis: dict[str, int] = {}
    for _, _, m in rated:
      b = (m.get("timing") or {}).get("basis", "unknown")
      basis[b] = basis.get(b, 0) + 1
    body.append(txt(bx, by + 4, "Timing basis", 10, MUTED, 700))
    body.append(txt(bx, by + 20, "  ".join(f"{BASIS_LABEL.get(k, k)} {basis.get(k, 0)}"
                                          for k in ("measured", "code_derived", "unknown")), 10.5, INK))
    lowered = sum(1 for fm, _, m in rated if m["severity_after"] < fm["severity"])
    body.append(txt(bx, by + 44, "Severity after the response", 10, MUTED, 700))
    body.append(txt(bx, by + 60, f"lowered {lowered}  unchanged {len(rated) - lowered}", 10.5, INK))
    y = max(gy + 40, by + 76)

    # best-monitored causes by id
    best = [c["id"] for _, c, m in sorted(rated, key=lambda r: (r[2]["monitoring"], r[1]["id"])) if m["monitoring"] <= 6]
    if best:
      lines_ = wrap("M ≤ 6: " + ", ".join(best), pw, 10)
      for k, ln in enumerate(lines_):
        body.append(txt(x0, y + k * 13, ln, 10, TEAL, 600))
      y += 13 * len(lines_) + 10
    # monitoring actions by status
    ids: dict[str, int] = {}
    for _, _, m in rated:
      for a in m.get("actions") or []:
        ids[a] = ids.get(a, 0) + 1
    body.append(txt(x0, y + 4, f"Actions named in the MSR rows ({len(ids)})", 10, MUTED, 700))
    y += 12
    scol = {"completed": (GREEN, "#FFFFFF", None), "in_progress": (AMBER, "#FFFFFF", None),
            "decision_pending": ("#FDEFD8", AMBER, AMBER), "open": ("#FBE4DF", RED, RED),
            "not_implemented": ("#F1F5F9", SLATE, SLATE)}
    x = x0
    for a in sorted(ids):
      act = acts.get(a)
      st = act["status"] if act else "open"
      fill, fg, stroke = scol.get(st, scol["open"])
      lab = f"{a} · {st.replace('_', ' ')} · {ids[a]}"
      if x + pill_w(lab, 9.5) > x0 + pw:
        x, y = x0, y + 22
      p, w = pill(x, y, lab, fill, fg, stroke, size=9.5)
      body.append(p)
      x += w + 6
    y += 30
    max_y = max(max_y, y)
  width = 40 + len(panels) * pw + (len(panels) - 1) * gap + 40
  y = max_y + 10
  body.append(line(40, y, width - 40, y))
  y += 22
  lx = 40
  for ap in "HML":
    body.append(rect(lx, y - 11, 14, 14, AP_TINT[ap]))
    body.append(f'<circle cx="{n(lx + 28)}" cy="{n(y - 4)}" r="7" fill="{AP_COL[ap]}"/>')
    lab = f"MSR AP {ap} region / causes rated {ap}"
    body.append(txt(lx + 42, y, lab, 10.5, INK))
    lx += 42 + tw(lab, 10.5) + 22
  y += 18
  body.append(txt(40, y, "Grid background = MSR AP for S 10 (handbook table, original severity in every column); circle = "
                  "number of causes at that F and M, coloured by their stored MSR AP. Where the AP is H, M ranks the work.",
                  10, MUTED))
  y += 16
  body.append(txt(40, y, MSR_AP_NOTE, 10, MUTED))
  y += 18
  body += footer(y, width, ", ".join(f"analyses/{f.key}.yaml" for f in panels))
  height = y + 20
  desc = "FMEA-MSR overview: " + "; ".join(
    f"{f.name} {f.a['id']} rev {f.a['revision']} at {f.a['baseline']}: {k} causes rated, {ex} exempt, MSR AP H {c['H']}, "
    f"M {c['M']}, L {c['L']}, monitoring M 1-4 {b[0]}, M 5-6 {b[1]}, M 7-8 {b[2]}, M 9-10 {b[3]}"
    for f, k, ex, c, b in totals) + \
    ". For each FMEA a frequency by monitoring grid over the S 10 handbook MSR AP table, the count per monitoring band, the timing " \
    "basis, how many responses lower the severity, and the actions the MSR rows name."
  return svg_doc(width, height, f"Figure {fig}. FMEA-MSR overview of the System FMEA and DFMEA", desc, fig,
                 "FMEA-MSR overview: monitoring and system response",
                 "Frequency × monitoring as rated (RT-3 §7) · monitoring band · timing basis · actions named in the MSR rows",
                 "msr-plan.md §4.5", "analyses/system-fmea.yaml, dfmea.yaml", body)


# ================================================================ FMEDA

CLS_COL = {"spf": RED, "rf": ORANGE, "det": "#FDBA74", "latent": AMBER, "mpf_det": "#FCE7C2", "safe": "#E2E8F0"}
CLS_LABEL = {"spf": "λSPF single-point", "rf": "λRF residual", "det": "detected by the SPF mechanism",
             "latent": "λMPF latent", "mpf_det": "λMPF detected/perceived", "safe": "λS safe"}


def fit_fmt(v: float) -> str:
  if v == 0:
    return "0"
  if v >= 10:
    return f"{v:.1f}".rstrip("0").rstrip(".")
  return f"{v:.2f}".rstrip("0").rstrip(".")


def pct(v: float) -> str:
  return f"{v * 100:.2f} %"


def render_fmeda(key: str, doc: dict, fig: str) -> str:
  a = doc["analysis"]
  targets = fmeda_targets(doc)
  m = fmeda_metrics(doc)
  if m is None or not targets:
    raise FigError(f"{key}: metrics not computable or no ASIL target")
  rows = fmeda_rows(doc)
  sms = {s["id"]: s for s in doc["safety_mechanisms"]}
  if any("rate_kind" in c for c in doc["components"]):
    generic = [c["id"] for c in doc["components"] if c.get("rate_kind") == "generic"]
  else:
    generic = [c["id"] for c in doc["components"] if str(c.get("failure_rate_source", "")).lower().startswith("generic")]
  converted = sum(1 for c in doc["components"] if c.get("stress_converted"))
  body: list[str] = []
  y = 98
  # estimate banner
  banner = (f"ESTIMATE · {a['status'].upper()} — {len(generic)} of {len(doc['components'])} failure rates are generic "
            f"estimates and {converted} are converted to the mission profile. The metrics below are not verified and are "
            "not evidence that a target is met.")
  bl = wrap(banner, 1160, 11, 600)
  body.append(rect(40, y, 1200, 14 + 15 * len(bl), "#FFFBEB", AMBER, 1.4, 8, ' stroke-dasharray="6 4"'))
  for k, ln in enumerate(bl):
    body.append(txt(56, y + 19 + 15 * k, ln, 11, "#92400E", 600))
  y += 14 + 15 * len(bl) + 26

  body.append(txt(40, y, "HARDWARE ARCHITECTURAL METRICS PER SAFETY GOAL (WP-H-04 §4; rating-tables §6.3)", 9.5, MUTED, 700,
                  extra=' letter-spacing=".06em"'))
  y += 10
  # goals with identical metrics share one row; each row carries the ASIL targets of its goals
  groups: list[dict] = []
  for goal, asil, also in targets:
    gm = fmeda_metrics(doc, goal)
    key3 = (round(gm["spfm"], 9), round(gm["lfm"], 9), round(gm["pmhf_spf_rf_fit"], 9))
    g = next((g for g in groups if g["key"] == key3), None)
    if g is None:
      g = {"key": key3, "m": gm, "goals": [], "asils": []}
      groups.append(g)
    g["goals"].append(f"{goal} {asil}")
    for x in [asil] + list(also):
      if x not in g["asils"]:
        g["asils"].append(x)
  cols = [("SPFM", "spfm", 0, 250, 0.5, 1.0), ("LFM", "lfm", 1, 250, 0.5, 1.0), ("λSPF + λRF (FIT)", "pmhf_spf_rf_fit", 2, 170, 0.0, None)]
  x0 = {"SPFM": 330, "LFM": 666, "λSPF + λRF (FIT)": 1002}
  y += 18
  for name, _, _, w, _, _ in cols:
    body.append(txt(x0[name], y, name, 11, INK, 700))
  y += 8
  for g in groups:
    y += 30
    body.append(line(40, y - 22, 1240, y - 22, "#E2E8F0"))
    for k, ln in enumerate(wrap(" · ".join(g["goals"]), 270, 12.5, 700, max_lines=3)):
      body.append(txt(40, y + 15 * k, ln, 12.5, INK, 700))
    verdicts = []
    for asil in sorted(g["asils"], key="BCD".index, reverse=True):
      st, lt, pt = FMEDA_TARGETS[asil]
      ok = g["m"]["spfm"] >= st and g["m"]["lfm"] >= lt and g["m"]["pmhf_spf_rf_fit"] < pt
      verdicts.append((asil, ok))
    vx = 40
    for asil, ok in verdicts:
      lab = f"ASIL {asil} {'met on this estimate' if ok else 'missed'}"
      p, pw = pill(vx, y + 22, lab, "#FFFFFF" if ok else RED, AMBER if ok else "#FFFFFF", AMBER if ok else None, size=9)
      body.append(p)
      vx += pw + 6
    for name, k, idx, w, lo, hi in cols:
      v = g["m"][k]
      bx = x0[name]
      if hi is None:
        pmax = max(FMEDA_TARGETS[x][2] for x in g["asils"])
        hi = max(pmax * 1.1, v * 1.15)
      body.append(rect(bx, y - 6, w, 18, "#F1F5F9", None, 0, 4))
      worst_ok = all((v >= FMEDA_TARGETS[x][idx]) if idx < 2 else (v < FMEDA_TARGETS[x][idx]) for x in g["asils"])
      col = AMBER if worst_ok else RED
      vw = w * (min(max(v, lo), hi) - lo) / (hi - lo)
      body.append(rect(bx, y - 6, max(vw, 2), 18, col, None, 0, 4))
      by_t: dict[float, list[str]] = {}
      for asil in sorted(g["asils"], key="BCD".index):
        by_t.setdefault(FMEDA_TARGETS[asil][idx], []).append(asil)
      for t, names in by_t.items():
        if not lo <= t <= hi:
          continue
        tx = bx + w * (t - lo) / (hi - lo)
        body.append(line(tx, y - 10, tx, y + 16, INK, 1.4, ' stroke-dasharray="3 2"'))
        lab = f"{'/'.join(names)} {t * 100:.0f} %" if idx < 2 else f"{'/'.join(names)} < {t:g}"
        body.append(txt(tx, y + 27, lab, 9, INK, 700, anchor="middle"))
      vtxt = pct(v) if idx < 2 else fit_fmt(v)
      body.append(txt(bx + w + 6 if idx < 2 else bx + w + 6, y + 8, vtxt, 12, col, 700))
    y += 34
  y += 16
  body.append(txt(40, y, "Dashed ticks: ASIL targets of the goals in the row (B shown alongside C for SG-01, DQ-063). λSPF + λRF is the "
                  "single-point and residual part of PMHF only; the dual-point term is not computed (rating-tables §6.3).", 10, MUTED))
  y += 22

  # per-component split
  body.append(line(40, y, 1240, y))
  y += 22
  body.append(txt(40, y, "FAILURE-RATE SPLIT PER COMPONENT (FIT) — CLASSIFICATION PER rating-tables §6.1", 9.5, MUTED, 700,
                  extra=' letter-spacing=".06em"'))
  y += 12
  max_l = max(c["failure_rate_fit"] or 0 for c in doc["components"])
  cbx, cbw = 360, 640
  by_comp: dict[str, list[dict]] = {}
  for r in rows:
    by_comp.setdefault(r["comp"], []).append(r)
  for comp in doc["components"]:
    y += 12
    lam = comp["failure_rate_fit"]
    body.append(txt(40, y + 12, f"{comp['id']}", 11.5, INK, 700))
    body.append(txt(40 + tw(comp["id"], 11.5, 700) + 8, y + 12, f"λ = {fit_fmt(lam)} FIT" +
                    ("" if comp["safety_related"] else " · not safety-related"), 11, MUTED, 600))
    plines = wrap(comp["part"], 300, 10, max_lines=2)
    for k, ln in enumerate(plines):
      body.append(txt(40, y + 26 + 12 * k, ln, 10, MUTED))
    extra_l = []
    if comp.get("dfmea_element"):
      extra_l.append(comp["dfmea_element"])
    if comp.get("ref_des"):
      extra_l.append(comp["ref_des"])
    if extra_l:
      body.append(txt(40, y + 26 + 12 * len(plines), "DFMEA " + " · ".join(extra_l), 9.5, MUTED, 600))
    # bar
    x = cbx
    body.append(rect(cbx, y + 2, cbw * lam / max_l, 14, "#F8FAFC", "#CBD5E1", 1))
    for cls in ("spf", "rf", "det", "latent", "mpf_det", "safe"):
      v = sum(r[cls] for r in by_comp[comp["id"]])
      if v <= 0:
        continue
      w = cbw * v / max_l
      body.append(rect(x, y + 2, w, 14, CLS_COL[cls]))
      x += w
    totals_txt = " · ".join(f"{k} {fit_fmt(sum(r[c] for r in by_comp[comp['id']]))}" for k, c in
                            (("SPF", "spf"), ("RF", "rf"), ("latent", "latent")) if sum(r[c] for r in by_comp[comp["id"]]) > 0)
    if totals_txt:
      body.append(txt(cbx + cbw * lam / max_l + 8, y + 13, totals_txt, 10, INK, 600))
    # FM chips
    cy = y + 22
    cx = cbx
    for r in by_comp[comp["id"]]:
      cls = r.get("cls", "safe")
      if cls == "spf":
        lab = f"{r['id']} SPF {fit_fmt(r['spf'])}"
        fill, fg, st = RED, "#FFFFFF", None
      elif cls == "rf":
        lab = f"{r['id']} RF {fit_fmt(r['rf'])} · {r['sm']} {r['dc'] * 100:g} %"
        fill, fg, st = ORANGE, "#FFFFFF", None
      elif cls == "mpf":
        lab = f"{r['id']} latent {fit_fmt(r['latent'])}" + (f" · {r['sm']} {r['dc'] * 100:g} %" if r["sm"] else " · no SM")
        fill, fg, st = "#FEF3C7", "#92400E", AMBER
      else:
        lab = f"{r['id']} safe"
        fill, fg, st = "#F1F5F9", MUTED, "#CBD5E1"
      cw = pill_w(lab, 9)
      if cx + cw > 1240:
        cx = cbx
        cy += PILL_H + 3
      p, _ = pill(cx, cy, lab, fill, fg, st, size=9)
      body.append(p)
      cx += cw + 4
    y = max(cy + PILL_H, y + 26 + 12 * (len(plines) + (1 if extra_l else 0))) + 4
    body.append(line(40, y + 6, 1240, y + 6, "#F1F5F9"))
  y += 24
  lx = 40
  for cls in ("spf", "rf", "det", "latent", "mpf_det", "safe"):
    body.append(rect(lx, y - 10, 14, 12, CLS_COL[cls], "#CBD5E1" if cls in ("safe", "mpf_det") else None, 1))
    body.append(txt(lx + 19, y, CLS_LABEL[cls], 10, INK))
    lx += 19 + tw(CLS_LABEL[cls], 10) + 18
  y += 16
  body.append(txt(40, y, f"Totals: λ {fit_fmt(m['total_fit'])} FIT · λSPF {fit_fmt(m['spf_fit'])} · λRF {fit_fmt(m['rf_fit'])} · "
                  f"λMPF,latent {fit_fmt(m['mpf_latent_fit'])} FIT. Chip = failure mode with its class, FIT and the "
                  "credited safety mechanism with its DC.", 10, MUTED))
  y += 26

  # safety mechanisms
  body.append(line(40, y, 1240, y))
  y += 22
  body.append(txt(40, y, "SAFETY MECHANISMS (DC CLAIMED PER FAILURE MODE)", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  credited: dict[str, list[str]] = {}
  for r in rows:
    if r["sm"]:
      credited.setdefault(r["sm"], []).append(f"{r['id']} ({r['dc'] * 100:g} %)")
  for sid, s in sms.items():
    y += 17
    body.append(txt(40, y, sid, 10.5, INK, 700))
    req = f" [{s['requirement']}]" if s.get("requirement") else ""
    body.append(txt(124, y, fit(s["description"] + req, 640, 10.5), 10.5, INK))
    cr = credited.get(sid)
    body.append(txt(780, y, fit("credited on " + ", ".join(cr) if cr else "not credited on any failure mode", 460, 10),
                    10, MUTED if cr else RED, 600))
  y += 26
  body += footer(y, 1280, f"analyses/{key}.yaml")
  height = y + 20

  parts = []
  for g in groups:
    ver = ", ".join(f"ASIL {x} {'met on the estimate, not verified' if all([g['m']['spfm'] >= FMEDA_TARGETS[x][0], g['m']['lfm'] >= FMEDA_TARGETS[x][1], g['m']['pmhf_spf_rf_fit'] < FMEDA_TARGETS[x][2]]) else 'missed'}"
                    for x in g["asils"])
    parts.append(f"{', '.join(g['goals'])}: SPFM {pct(g['m']['spfm'])}, LFM {pct(g['m']['lfm'])}, "
                 f"λSPF+λRF {fit_fmt(g['m']['pmhf_spf_rf_fit'])} FIT ({ver})")
  goal_list = ", ".join(t[0] for t in targets)
  desc = (f"FMEDA {a['id']} rev {a['revision']} ({a['baseline']}, {a['status']}) for {goal_list}, with {len(generic)} of "
          f"{len(doc['components'])} failure rates generic estimates. Metrics per goal: " + "; ".join(parts) +
          ". Below: failure-rate split per component and failure mode, and the safety mechanisms with the failure modes they are "
          "credited on.")
  return svg_doc(1280, height, f"Figure {fig}. FMEDA {a['safety_goal']} metrics per goal (estimate)", desc, fig,
                 f"FMEDA {a['safety_goal']} — metrics per goal: {goal_list}",
                 f"{a['id']} rev {a['revision']} · {a['baseline']} · {a['status']} · {fit(a['title'], 640, 12.5)}",
                 "fmea-plan.md §3.5", f"analyses/{key}.yaml", body)


# ================================================================ DFA

DFI_COL = {"insufficient": RED, "open": AMBER, "safe_by_design": TEAL, "sufficient": GREEN}
DFI_LABEL = {"insufficient": "insufficient", "open": "open", "safe_by_design": "safe by design (argued)",
             "sufficient": "sufficient"}
DM_COL = {"existing": (GREEN, "#FFFFFF", None, False), "existing_unverified": ("#FEF3C7", "#92400E", AMBER, False),
          "required": ("#FFFFFF", RED, RED, True)}
DM_LABEL = {"existing": "existing (verified)", "existing_unverified": "existing, not verified", "required": "required, missing"}
DEC_COL = {"not_accepted": (RED, "#FFFFFF"), "conditional": (AMBER, "#FFFFFF"), "accepted": (GREEN, "#FFFFFF"),
           "not_assessable": ("url(#hatch)", MUTED)}
DEC_LABEL = {"not_accepted": "not acc.", "conditional": "cond.", "accepted": "accepted", "not_assessable": "n/assess."}


def render_dfa(doc: dict, fig: str) -> str:
  a = doc["analysis"]
  cats = doc["categories"]
  decs = doc["decompositions"]
  dfis = doc["dfis"]
  measures = {m["id"]: m for m in doc["measures"]}
  body: list[str] = []
  lab_x, lab_w = 40, 400
  mx0, cw = 450, 54
  mx1 = mx0 + cw * len(decs)
  rx = mx1 + 16
  y = 100
  # column heads
  body.append(txt(lab_x, y + 12, "DEPENDENT FAILURE INITIATOR (BY ISO 26262-9 CATEGORY)", 9.5, MUTED, 700,
                  extra=' letter-spacing=".06em"'))
  body.append(txt(mx0 + cw * len(decs) / 2, y + 12, "ASIL DECOMPOSITION (PARENT FSR)", 9.5, MUTED, 700, anchor="middle",
                  extra=' letter-spacing=".06em"'))
  body.append(txt(rx, y + 12, "MEASURES", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  y += 24
  for j, d in enumerate(decs):
    cx = mx0 + cw * j + cw / 2
    body.append(txt(cx, y + 11, d["fsr"], 10, INK, 700, anchor="middle"))
    chans = [c["fsr"].replace("FSR-", "") for c in d["channels"]]
    body.append(txt(cx, y + 24, " ‖ ".join(chans), 9, MUTED, anchor="middle"))
    fill, fg = DEC_COL[d["status"]]
    body.append(rect(cx - cw / 2 + 3, y + 30, cw - 6, 16, fill, None if d["status"] != "not_assessable" else "#94A3B8", 1, 3))
    body.append(txt(cx, y + 41.5, DEC_LABEL[d["status"]], 9, fg, 700, anchor="middle"))
  y += 54
  grid_top = y
  # not assessable columns hatched
  na_cols = [j for j, d in enumerate(decs) if d["status"] == "not_assessable"]
  rows_svg: list[str] = []
  by_cat: dict[str, list[dict]] = {}
  for d in dfis:
    by_cat.setdefault(d["category"], []).append(d)
  for c in cats:
    # category header
    rows_svg.append(rect(lab_x, y, 1200, 20, "#F8FAFC"))
    rows_svg.append(txt(lab_x + 6, y + 14, f"{c['id']} · {c['name']}", 10.5, INK, 700))
    if not c["applicable"]:
      rows_svg.append(rect(mx0, y + 2, mx1 - mx0, 16, "url(#hatch)", "#CBD5E1", 1, 3, ' stroke-dasharray="4 3"'))
      rows_svg.append(rect(mx0 + 8, y + 3.5, tw("not applicable", 9.5, 700) + 10, 13, "#F8FAFC", None, 0, 3))
      rows_svg.append(txt(mx0 + 13, y + 13.5, "not applicable", 9.5, MUTED, 700))
      rows_svg.append(txt(rx, y + 14, fit(c.get("rationale", ""), 1240 - rx, 9.5), 9.5, MUTED, italic=True))
      y += 24
      continue
    y += 22
    for d in by_cat.get(c["id"], []):
      rh = 26
      kind = "CC" if d["kind"] == "common_cause" else "CAS"
      rows_svg.append(txt(lab_x + 6, y + 16, d["id"], 10.5, INK, 700))
      p, w = pill(lab_x + 54, y + 5, kind, "#E2E8F0", MUTED)
      rows_svg.append(p)
      rows_svg.append(txt(lab_x + 54 + w + 6, y + 16, fit(d["description"], lab_w - 60 - w - 6, 10), 10, INK))
      for j, dec in enumerate(decs):
        cx = mx0 + cw * j + cw / 2
        if dec["fsr"] in d["decompositions"]:
          col = DFI_COL[d["assessment"]]
          if d["assessment"] == "safe_by_design":
            rows_svg.append(rect(cx - 9, y + 4, 18, 18, "#FFFFFF", col, 2, 4))
          else:
            rows_svg.append(rect(cx - 9, y + 4, 18, 18, col, None, 0, 4))
      mxx, my = rx, y + 5
      if not d["measures"]:
        rows_svg.append(txt(mxx, y + 16, "no measure", 10, RED, 700))
      for mid in d["measures"]:
        st = measures[mid]["status"]
        fill, fg, stroke, dashed = DM_COL[st]
        _, w = pill(0, 0, mid, fill, fg, stroke, dashed=dashed)
        if mxx > rx and mxx + w > 1240:  # wrap to a new line rather than run past the figure edge
          mxx, my = rx, my + 20
          rh += 20
        p, w = pill(mxx, my, mid, fill, fg, stroke, dashed=dashed)
        rows_svg.append(p)
        mxx += w + 4
      rows_svg.append(line(lab_x, y + rh, 1240, y + rh, "#F1F5F9"))
      y += rh
    y += 4
  grid_bottom = y
  # grid background first
  for j in range(len(decs) + 1):
    body.append(line(mx0 + cw * j, grid_top - 4, mx0 + cw * j, grid_bottom, "#E2E8F0"))
  for j in na_cols:
    body.append(rect(mx0 + cw * j + 1, grid_top - 4, cw - 2, grid_bottom - grid_top + 4, "url(#hatch)"))
  body += rows_svg
  y += 16

  # assessment legend row
  body.append(line(40, y, 1240, y))
  y += 22
  lx = 40
  body.append(txt(lx, y, "Initiator assessment:", 10.5, INK, 700))
  lx += tw("Initiator assessment:", 10.5, 700) + 10
  used = [k for k in DFI_COL if any(d["assessment"] == k for d in dfis)]
  for k in used:
    if k == "safe_by_design":
      body.append(rect(lx, y - 11, 14, 14, "#FFFFFF", DFI_COL[k], 2, 3))
    else:
      body.append(rect(lx, y - 11, 14, 14, DFI_COL[k], None, 0, 3))
    body.append(txt(lx + 20, y, DFI_LABEL[k], 10.5, INK))
    lx += 20 + tw(DFI_LABEL[k], 10.5) + 18
  p, w = pill(lx, y - 11, "CC", "#E2E8F0", MUTED)
  body.append(p)
  body.append(txt(lx + w + 5, y, "common cause", 10.5, INK))
  lx += w + 5 + tw("common cause", 10.5) + 12
  p, w = pill(lx, y - 11, "CAS", "#E2E8F0", MUTED)
  body.append(p)
  body.append(txt(lx + w + 5, y, "cascading", 10.5, INK))
  y += 22
  lx = 40
  body.append(txt(lx, y, "Measure status:", 10.5, INK, 700))
  lx += tw("Measure status:", 10.5, 700) + 10
  for st in ("existing", "existing_unverified", "required"):
    if not any(m["status"] == st for m in measures.values()):
      continue
    fill, fg, stroke, dashed = DM_COL[st]
    p, w = pill(lx, y - 11, "DM-nn", fill, fg, stroke, dashed=dashed)
    body.append(p)
    body.append(txt(lx + w + 5, y, DM_LABEL[st], 10.5, INK))
    lx += w + 5 + tw(DM_LABEL[st], 10.5) + 18
  body.append(txt(lx, y, "Decomposition:", 10.5, INK, 700))
  lx += tw("Decomposition:", 10.5, 700) + 8
  for st in ("not_accepted", "conditional", "accepted", "not_assessable"):
    if not any(d["status"] == st for d in decs):
      continue
    fill, fg = DEC_COL[st]
    body.append(rect(lx, y - 11, 50, 15, fill, "#94A3B8" if st == "not_assessable" else None, 1, 3))
    body.append(txt(lx + 25, y, DEC_LABEL[st], 9, fg, 700, anchor="middle"))
    full = st.replace("_", " ")
    body.append(txt(lx + 56, y, full, 10.5, INK))
    lx += 56 + tw(full, 10.5) + 14
  y += 26

  # decomposition key
  body.append(line(40, y, 1240, y))
  y += 22
  body.append(txt(40, y, "DECOMPOSITIONS (FSC CHANNELS → ELEMENTS)", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  body.append(txt(660, y, "MEASURES", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  ky = y
  for d in decs:
    ky += 16
    ch = "  ‖  ".join(f"{c['fsr']} [{', '.join(c['elements'])}]" for c in d["channels"])
    fill, fg = DEC_COL[d["status"]]
    body.append(txt(40, ky, d["fsr"], 10, INK, 700))
    body.append(txt(96, ky, fit(ch, 300, 10), 10, INK))
    body.append(txt(400, ky, fit(d["status"].replace("_", " ") + " — " + d.get("rationale", ""), 240, 9.5),
                    9.5, RED if d["status"] == "not_accepted" else MUTED, 600 if d["status"] == "not_accepted" else 400))
  my = y
  for mid, m in measures.items():
    my += 16
    fill, fg, stroke, dashed = DM_COL[m["status"]]
    p, w = pill(660, my - 11, mid, fill, fg, stroke, dashed=dashed)
    body.append(p)
    alloc = ", ".join(m.get("allocated_to", []))
    body.append(txt(660 + 52, my, fit(f"{m['description']}", 400, 10), 10, INK))
    body.append(txt(1240, my, fit(alloc, 110, 9.5), 9.5, MUTED, 600, anchor="end"))
  y = max(ky, my) + 26

  # open items
  body.append(line(40, y, 1240, y))
  y += 22
  body.append(txt(40, y, "DFA OPEN ITEMS", 9.5, MUTED, 700, extra=' letter-spacing=".06em"'))
  for oi in doc["open_items"]:
    y += 17
    st = oi["status"]
    p, w = pill(40, y - 11, f"{oi['id']} {st}", "#FFFFFF" if st != "closed" else "#F1F5F9",
                AMBER if st != "closed" else MUTED, AMBER if st != "closed" else "#CBD5E1")
    body.append(p)
    body.append(txt(40 + 130, y, fit(oi["text"], 640, 10), 10, INK))
    body.append(txt(1240, y, fit("affects " + ", ".join(oi["affects"]), 290, 9.5), 9.5, MUTED, 600, anchor="end"))
  y += 26
  body += footer(y, 1280, "analyses/dfa.yaml")
  height = y + 20

  ac: dict[str, int] = {}
  for d in dfis:
    ac[d["assessment"]] = ac.get(d["assessment"], 0) + 1
  dc: dict[str, int] = {}
  for d in decs:
    dc[d["status"]] = dc.get(d["status"], 0) + 1
  ids = sorted((d["id"] for d in dfis), key=lambda i: (int(re.match(r"DFI-(\d+)", i).group(1)), i))
  desc = (f"Dependent failure analysis {a.get('doc_id', a['id'])} rev {a['revision']} against FSC rev {a['fsc_revision']}: "
          f"{len(dfis)} dependent failure initiators, {ids[0]} to {ids[-1]} (the WP-A-03 numbers of those that reach a "
          f"panda/SoC decomposition), in {len(cats)} categories mapped onto {len(decs)} ASIL decompositions. "
          "Initiators: " + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in sorted(ac.items())) +
          ". Decompositions: " + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in sorted(dc.items())) +
          f". {len(measures)} measures with their status ({sum(1 for m in measures.values() if m['status'] == 'required')} required) "
          "and the DFA open items.")
  return svg_doc(1280, height, f"Figure {fig}. DFA initiators against the ASIL decompositions", desc, fig,
                 "Dependent failure initiators × ASIL decompositions",
                 f"{a.get('doc_id', a['id'])} rev {a['revision']} · FSC rev {a['fsc_revision']} · {a['baseline']} · {a['status']} · "
                 "cell = the initiator affects that decomposition, coloured by the initiator's assessment",
                 "fmea-plan.md §2", "analyses/dfa.yaml", body)


# ================================================================ outputs

def build(docs: dict[str, dict] | None = None) -> dict[str, str]:
  docs = load_analyses() if docs is None else docs
  outputs: dict[str, str] = {}
  index: list[tuple[str, str, str, list[str]]] = []   # figure, title, source, files

  name = "fig-2-1-dfa-initiators.svg"
  outputs[name] = render_dfa(docs["dfa"], "2-1")
  index.append(("2-1", "DFA: dependent failure initiators × ASIL decompositions, measures, open items", "analyses/dfa.yaml", [name]))

  fmeas = [Fmea(k, docs[k], fs, fc, slug) for k, fs, fc, slug in FMEA_FILES]
  for f in fmeas:
    if f.a["type"] not in TYPE_NAME:
      raise FigError(f"{f.key}: unexpected analysis type {f.a['type']}")
    name = f"fig-{f.fig_structure}-{f.slug}-structure.svg"
    outputs[name] = render_structure(f)
    index.append((f.fig_structure, f"{f.name} structure and function tree (steps 2–3)", f.source, [name]))
    sheets = chain_sheets(f)
    names = []
    seen_fn: set = set()
    seen_el: set = set()
    for no, fms in enumerate(sheets, 1):
      name = f"fig-{f.fig_chains}-{f.slug}-failure-chains-{no}.svg"
      outputs[name] = render_chain_sheet(f, fms, no, len(sheets), seen_fn, seen_el)
      names.append(name)
    index.append((f.fig_chains, f"{f.name} failure chains: element → function → failure mode → causes (steps 4–6)",
                  f.source, names))
    if f.key == "sw-fmea":
      name = "fig-3-7-swf-action-effect.svg"
      outputs[name] = render_action_effect(f, "3-7")
      index.append(("3-7", "SW FMEA: Action Priority as rated and as predicted by the planned actions (not achieved)",
                    f.source, [name]))
      name = "fig-3-12-swf-od-elements.svg"
      outputs[name] = render_od_elements(f, "3-12")
      index.append(("3-12", "SW FMEA: occurrence × detection per element, with the moves predicted by planned actions",
                    f.source, [name]))
      name = "fig-3-13-swf-detection-evidence.svg"
      outputs[name] = render_detection_evidence(f, "3-13")
      index.append(("3-13", "SW FMEA: what each detection rating rests on (test run in CI, hardware only, not run, none)",
                    f"{f.source}, .github/workflows/, tools/test_runner.py", [name]))
      for fig, slug, render, title in (
          ("3-14", "baseline-delta", render_baseline_delta,
           "SW FMEA: occurrence, detection and AP of the re-rated causes, previous baseline against this one"),
          ("3-15", "reaction-layers", render_reaction_layers,
           "SW FMEA: reaction time of the timed safety mechanisms by defence layer (code-derived, not measured)"),
          ("3-16", "sotif-boundary", render_sotif_boundary,
           "SW FMEA: per element, the causes rated here and the performance part left to SOTIF")):
        name = f"fig-{fig}-swf-{slug}.svg"
        outputs[name] = render(f, fig)
        index.append((fig, title, f.source, [name]))

  for key, fig in (("fmeda-sg001", "3-10"), ("fmeda-sg009", "3-11")):
    name = f"fig-{fig}-{key}-metrics.svg"
    outputs[name] = render_fmeda(key, docs[key], fig)
    a = docs[key]["analysis"]
    index.append((fig, f"FMEDA {a['safety_goal']}: SPFM, LFM, λSPF+λRF against ASIL {a['asil_target']} (estimate, not verified)",
                  f"analyses/{key}.yaml", [name]))

  name = "fig-4-1-action-priority-overview.svg"
  outputs[name] = render_ap_overview(fmeas, "4-1")
  index.append(("4-1", "Action Priority overview of the four FMEAs", "analyses/*fmea.yaml", [name]))
  name = "fig-4-2-msr-overview.svg"
  outputs[name] = render_msr_overview(fmeas, "4-2")
  index.append(("4-2", "FMEA-MSR overview of the System FMEA and DFMEA (handbook MSR AP table, RT-3)",
                "analyses/system-fmea.yaml, dfmea.yaml", [name]))

  def fig_key(row):
    return tuple(int(p) for p in row[0].split("-"))

  md = ["# FMEA, FMEDA and DFA figures", "",
        f"Generated from the YAML analyses in [`analyses/`](../../analyses/) by `{GENERATOR}`. The YAML is the analysis "
        "of record; edit it and run `python3 tools/safety/fmea_diagrams.py` (`--check` fails when a figure is stale). "
        "Figure numbers follow the sections of [fmea-plan.md](../../fmea-plan.md). This folder is owned by the generator: "
        "hand-drawn figures belong in `figures/`, one level up.", "",
        "Every figure comes in two versions: the original drawing (`fig-*.svg`), which is the figure of record and the "
        "one the FMEA documents embed, and an easier-to-read card version (`fig-*-cards.svg`) in the style of the fault "
        "tree card view and fta-viewer.html. Both are drawn from the same YAML and show the same content.", "",
        "| Figure | Shows | Source | Files (of record) | Card version |", "|---|---|---|---|---|"]
  for fig, title, src, files in sorted(index, key=fig_key):
    links = ", ".join(f"[{i}]({fn})" if len(files) > 1 else f"[{fn}]({fn})" for i, fn in enumerate(files, 1))
    cards = ", ".join(f"[{i}]({cards_name(fn)})" for i, fn in enumerate(files, 1))
    md.append(f"| {fig} | {title} | `{src}` | {links} | {cards} |")
  md += ["",
         "Conventions: Action Priority H / M / L in red / amber / teal as rated in the YAML; predicted ratings of open "
         "actions are hatched and dashed and never shown as achieved. FMEDA metrics are drawn from generic failure-rate "
         "estimates and are marked as not verified; a target met on the estimate is amber, never green. "
         "In the DFA, green marks only measures recorded as `existing` (verified); `existing_unverified` is amber.",
         "", "Large failure-chain trees are split into sheets; an element or function repeated on a later sheet is tagged "
         "“continued”.", ""]
  outputs["README.md"] = "\n".join(md)
  return outputs


def cards_name(name: str) -> str:
  return name[:-len(".svg")] + "-cards.svg"


def build_cards() -> dict[str, str]:
  """The card versions, drawn in a second process: the style is fixed when the module is imported."""
  env = dict(os.environ, FMEA_FIG_STYLE="cards")
  proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--emit-json"], env=env, capture_output=True,
                        text=True, check=False)
  if proc.returncode != 0:
    raise FigError(f"card versions: {(proc.stderr or proc.stdout).strip()[-600:]}")
  return {cards_name(k): v for k, v in json.loads(proc.stdout).items() if k != "README.md"}


def build_all() -> dict[str, str]:
  """The figures of record and their card versions."""
  if CARDS:
    raise FigError("build_all() runs in the original style; unset FMEA_FIG_STYLE")
  outputs = build()
  outputs.update(build_cards())
  return outputs


def main(argv: list[str]) -> int:
  check = "--check" in argv
  if "--emit-json" in argv:   # used by build_cards()
    try:
      print(json.dumps(build(), ensure_ascii=False))
    except FigError as ex:
      print(f"fmea_diagrams: {ex}", file=sys.stderr)
      return 1
    return 0
  try:
    outputs = build_all()
  except FigError as ex:
    print(f"fmea_diagrams: {ex}", file=sys.stderr)
    return 1
  for k in outputs:
    if k != "README.md" and not OWNED_RE.match(k):
      print(f"fmea_diagrams: output name {k} is outside OWNED_RE", file=sys.stderr)
      return 1
  existing = {p.name for p in OUT_DIR.glob("*.svg") if OWNED_RE.match(p.name)} if OUT_DIR.is_dir() else set()
  if check:
    stale = sorted(k for k, v in outputs.items()
                   if not (OUT_DIR / k).exists() or (OUT_DIR / k).read_text(encoding="utf-8") != v)
    extra = sorted(existing - set(outputs))
    if stale or extra:
      for k in stale:
        print(f"stale: {k}", file=sys.stderr)
      for k in extra:
        print(f"no longer generated: {k}", file=sys.stderr)
      print(f"run: python3 {GENERATOR}", file=sys.stderr)
      return 1
    n = sum(1 for k in outputs if k.endswith("-cards.svg"))
    print(f"fmea_diagrams: {len(outputs) - 1 - n} figure file(s) and {n} card versions current")
    return 0
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  for k in sorted(existing - set(outputs)):
    (OUT_DIR / k).unlink()
  for k, v in outputs.items():
    (OUT_DIR / k).write_text(v, encoding="utf-8")
  n = sum(1 for k in outputs if k.endswith("-cards.svg"))
  print(f"fmea_diagrams: wrote {len(outputs) - 1 - n} figure file(s), {n} card versions and README.md to "
        f"{OUT_DIR.relative_to(ROOT)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
