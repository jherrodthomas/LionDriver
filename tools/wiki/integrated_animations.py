#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "Integrated standards: one system, not five" as SVG.

  integrated-silos.svg      five standards run as silos against one integrated lifecycle with a lane per discipline;
  integrated-joins.svg      the cross-domain interfaces of the process model, by pair of disciplines, with three examples;
  integrated-coverage.svg   every work product of the register against the standards it serves;
  integrated-log.svg        one hazard log with its SOTIF and TARA links, checked against the TARA, and the trace lanes;
  integrated-mechanism.svg  the panda safety envelope and what each standard asks of it;
  integrated-case.svg       one assurance case: a branch per standard, shared evidence, defeaters and their status.

The lane and interface counts are read from the process model (WP-P-11), the coverage matrix from the work-product
register (WP-M-00), the hazard log from WP-C-03 §7 and WP-C-09 §3, the trace lanes from the ASPICE trace map (WP-T-01)
and the case from assurance/case. Every other phrase is tied to its record (SOURCES) and checked at render time
(`problems()`). When a record changes, the wiki build fails instead of showing old text. build_wiki.py renders them next
to the pages at each sync; they loop with CSS and reduced motion shows the final frame.

Usage: python3 tools/wiki/integrated_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import collections
import random
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, W, Timeline, g, norm, stick, svg, t  # noqa: E402

NAMES = ("integrated-silos.svg", "integrated-joins.svg", "integrated-coverage.svg", "integrated-log.svg",
         "integrated-mechanism.svg", "integrated-case.svg")
BLUE, ORANGE, TEAL, VIOLET, PINK = "#2a78d6", "#c2410c", "#0f766e", "#6250d6", "#be185d"
FS, SO, CS, AIc, AS = BLUE, ORANGE, PINK, TEAL, VIOLET
STD = [("ISO 26262", FS), ("ISO 21448", SO), ("ISO/SAE 21434", CS), ("ISO/PAS 8800", AIc), ("ASPICE", AS)]
LANES = [("joint", NAVY, "joint"), ("ISO 26262", FS, "fusa"), ("SOTIF", SO, "sotif"), ("security", CS, "cs"), ("AI", AIc, "ai"),
         ("HW · SW", MID, "hw+sw"), ("assessment", AS, "assess")]
EXAMPLES = [("WP-P-11", "integrated process model"), ("WP-M-01", "assurance strategy"), ("WP-C-01", "item definition"), ("WP-C-03", "HARA")]
TRACE_COLOURS = {"ISO 26262": FS, "ISO 21448": SO, "ISO/PAS 8800": AIc, "ISO/SAE 21434": CS, "ASPICE": AS}
BRANCHES = [("g1-functional-safety", "G1 ISO 26262", FS), ("g2-sotif", "G2 ISO 21448", SO), ("g3-ai-safety", "G3 ISO/PAS 8800", AIc),
            ("g4-cybersecurity", "G4 ISO/SAE 21434", CS), ("g5-process-and-operation", "G5 process, ASPICE", AS)]

A = Path("assurance")
REG = A / "01-management" / "WP-M-00-work-product-register.md"
MODEL = A / "process" / "model"
IFR = A / "trace" / "items" / "ifr.yaml"
HARA = A / "02-concept" / "WP-C-03-hara.md"
TARA = A / "02-concept" / "WP-C-09-tara.md"
MAP = A / "trace" / "maps" / "aspice-trace-map.md"
CASE = A / "case"
REG_HEADER = "| ID | Work product | ISO 26262 | ISO 21448 | ISO/SAE 21434 | Other | ASPICE | Gate | Status |"

# (record, phrase a figure stands on)
SOURCES = [
  (A / "02-concept" / "WP-C-06-sotif-insufficiencies-triggering-conditions.md", "| FI-14 | S | System supervision | Soft disable keeps actuating for 3 s on the failed inputs"),
  (TARA, "| TS-12 | Denial of service against safety-relevant SoC processes"), (TARA, "soft-disable keeps actuating ~3 s"),
  (A / "02-concept" / "hatara" / "README.md", "Interaction IX-11 found one: TS-04 can alter driver monitoring"),
  (TARA, "| DS-01 | Unintended/excessive lateral actuation induced by manipulation | H-01"), (HARA, "| H-01 | [WP-C-05]"),
  (MODEL / "interfaces.yaml", "TARA safety impact is rated against those hazards and their ASILs"),
  (MODEL / "interfaces.yaml", "One hazard log: each HARA hazard cross-references the SOTIF hazards"),
  (MODEL / "interfaces.yaml", "Model artefacts load through pickle without a hash or signature: AI integrity requirements AIR-19/AIR-20 and threat scenario TS-09"),
  (MODEL / "interfaces.yaml", "an anchor `WP-x-nn:text` must occur verbatim in that"),
  (MAP, "dashed ones exist only in the work-product tables and are not linked yet"), (MAP, "## 7. Not yet traced"),
  (A / "02-concept" / "WP-C-04-functional-safety-concept.md", "| FSR-01.01 | The envelope shall limit the commanded LKA torque magnitude"),
  (A / "03-system" / "WP-S-02-technical-safety-requirements.md", "| TSR-512 | In release builds for the reference configuration the safety MCU shall accept only the modes"),
  (A / "03-system" / "WP-S-02-technical-safety-requirements.md", "Until TSR-102 is implemented, τ_max is the baseline 1500 raw"),
  (A / "03-system" / "WP-S-02-technical-safety-requirements.md", "| 6 | TSR-102, 204, 205 | Speed-dependent torque limit; jerk limits | GAP-04 |"),
  (A / "07-supporting" / "impact" / "change-2026-10-12-panda-safety-mode-lock.md", "| TSR-512 / SWSR-512 (mode and parameter lock) | Met in the reference build |"),
  (A / "02-concept" / "WP-C-05-sotif-hazard-identification.md", "| AC-02 | Every actuation produced by the intended function stays inside the envelope limits whose controllability is demonstrated"),
  (A / "02-concept" / "WP-C-10-cybersecurity-goals-and-concept.md", "| CSR-C-01 | The panda firmware shall enforce the Toyota safety mode and reject any mode/parameter change from the SoC"),
  (A / "02-concept" / "WP-C-11-ai-system-definition-and-safety-requirements.md", "| AIR-28 | AI outputs shall reach the actuators only through `controlsd`/`card` and the panda safety envelope"),
  (A / "01-management" / "WP-M-13-aspice-capability-baseline.md", "| SWE.4 Software unit verification | L (safety code) / P (rest) | Safety code: 100 % line coverage gate"),
  (A / "01-management" / "WP-M-13-aspice-capability-baseline.md", "mutation testing (`tests/mutation.py`, CI job), UBSan, MISRA static analysis"),
  (A / "02-concept" / "WP-C-08-driver-hmi-misuse-analysis.md", "| CA-01 | A typical attentive driver corrects envelope-bounded worst-case steering torque"),
  (A / "06-validation" / "WP-V-06-cybersecurity-validation.md", "| CSG-01 … CSG-08 | Not yet executed |"),
  (CASE / "claims" / "g0-top-level.yaml", 'title: "Reference configuration poses no unreasonable risk"'),
  (A / "10-safety-case" / "WP-K-01-safety-case.md", 'G4["G4 Cybersecurity (ISO/SAE 21434) — WP-K-03"]'),
]


class ParseError(Exception):
  pass


def section(text: str, start: str, end: str) -> str:
  i = text.find(start)
  if i < 0:
    raise ParseError(f"heading {start!r} not found")
  j = text.find(end, i + len(start))
  return text[i:j if j > 0 else None]


def cells(line: str) -> list[str]:
  return [c.strip() for c in line.strip().strip("|").split("|")]


def served(flags) -> str:
  if all(flags):
    return "all five"
  names = [n for (n, _), on in zip(STD, flags, strict=True) if on]
  return f"{names[0]} only" if len(names) == 1 else ", ".join(names)


def register(text: str) -> list[tuple[str, str, list[bool]]]:
  sec, out = None, []
  for line in text.splitlines():
    if line.startswith("### "):
      sec = re.sub(r"^### [\d.]+ ", "", line).split(" (")[0]
    if re.match(r"^\| \[?WP-[A-Z]-", line):
      c = cells(line)
      wid = re.search(r"WP-[A-Z]-\d+", c[0]).group(0)
      out.append((sec, wid, [bool(v and v not in ("—", "-")) for v in c[2:7]]))
  return out


def hazard_log(hara: str, tara: str) -> list[tuple[str, str, str, str]]:
  """One row per hazard of WP-C-03 §7: (H, SOTIF hazard, damage scenarios of WP-C-09 §3 that reach it, flag)."""
  reach = collections.defaultdict(list)
  for line in section(tara, "## 3. Damage scenarios", "## 4.").splitlines():
    if line.startswith("| DS-"):
      c = cells(line)
      link = c[2]
      m = re.match(r"H-(\d+)…H-(\d+)", link)
      hs = [f"H-{k:02d}" for k in range(int(m.group(1)), int(m.group(2)) + 1)] if m else re.findall(r"H-\d+", link)
      for hz in hs:
        reach[hz].append(c[0])
  rows = []
  for line in section(hara, "## 7. Hazard log cross-references", "![").splitlines():
    if re.match(r"^\| H-\d+ ", line):
      c = cells(line)
      sh = re.search(r"SH-\d+", c[1])
      ds = reach.get(c[0], [])
      flag = f"{', '.join(ds)} exists" if c[2] == "—" and ds else ""
      rows.append((c[0], sh.group(0) if sh else "—", ", ".join(ds) or "—", flag))
  return rows


def trace_lanes(text: str) -> list[tuple[str, str, list[tuple[str, bool]]]]:
  lanes, cur = [], None
  for line in text.splitlines():
    m = re.match(r'\s*subgraph \w+\["([^"]+)"\]', line)
    if m:
      cur = (m.group(1), TRACE_COLOURS.get(m.group(1), MID), [])
      lanes.append(cur)
      continue
    m = re.match(r'\s*k\w+\["<b>(\w+)</b> (\d+)<br/>[^"]*"\]:::(traced|doc)', line)
    if m and cur is not None:
      if m.group(1) in ("HWSR", "AOU"):  # side branches of the ISO 26262 lane; the figure draws the main chain
        continue
      cur[2].append((f"{m.group(1)} {m.group(2)}", m.group(3) == "traced"))
  if not lanes:
    raise ParseError(f"{MAP}: no trace lanes found in §3")
  return lanes


def data(root: Path = ROOT) -> dict:
  acts, ifs = [], []
  for p in sorted((root / MODEL).glob("*.yaml")):
    items = yaml.safe_load(p.read_text(encoding="utf-8")) or []
    if isinstance(items, list):
      acts += [x for x in items if isinstance(x, dict) and x.get("kind") == "activity"]
      ifs += [x for x in items if isinstance(x, dict) and x.get("kind") == "interface"]
  # an interface's status is read from its IFR item (DQ-129 A), as in process_model.ix_status
  ifrs = {x["id"]: x for x in yaml.safe_load((root / IFR).read_text(encoding="utf-8")) or []}
  for x in ifs:
    ifr = ifrs.get(x.get("ifr"), {})
    x["status"] = "agreed" if ifr.get("status") == "agreed" else "open" if ifr.get("open_item") else "documented"
  per = collections.Counter(a.get("lane") for a in acts)
  lanes = {k: sum(per[p] for p in k.split("+")) for _, _, k in LANES}
  reg_text = (root / REG).read_text(encoding="utf-8")
  hara, tara = ((root / p).read_text(encoding="utf-8") for p in (HARA, TARA))
  branches = []
  claims = []
  for f, n, c in BRANCHES:
    cl = yaml.safe_load((root / CASE / "claims" / f"{f}.yaml").read_text(encoding="utf-8")) or []
    claims += cl
    branches.append((n, c, len(cl)))
  claims += yaml.safe_load((root / CASE / "claims" / "g0-top-level.yaml").read_text(encoding="utf-8")) or []
  ev = yaml.safe_load((root / CASE / "evidence" / "evidence.yaml").read_text(encoding="utf-8")) or []
  shared = [e for e in ev if len({c.split(".")[0] for c in (e.get("related_claims") or [])}) > 1]
  df = yaml.safe_load((root / CASE / "defeaters" / "defeaters.yaml").read_text(encoding="utf-8")) or []
  return {"activities": len(acts), "lanes": lanes, "unlaned": sum(per.values()) - sum(lanes.values()), "interfaces": ifs,
          "reg": register(reg_text), "reg_header": reg_text.count(REG_HEADER), "log": hazard_log(hara, tara),
          "trace": trace_lanes((root / MAP).read_text(encoding="utf-8")), "branches": branches, "claims": claims,
          "evidence": ev, "shared": shared, "defeaters": df}


def problems(root: Path = ROOT) -> list[str]:
  errs, cache = [], {}
  for path, phrase in SOURCES:
    if path not in cache:
      p = root / path
      cache[path] = norm(p.read_text(encoding="utf-8")) if p.exists() else ""
    if norm(phrase) not in cache[path]:
      errs.append(f"{path}: the integrated-standards page stands on {phrase!r}, which is gone; update the figure")
  try:
    d = data(root)
    if d["unlaned"]:
      errs.append(f"{MODEL}: {d['unlaned']} activities sit in a lane integrated-silos.svg does not draw; add it to LANES")
    secs = len({s for s, _, _ in d["reg"]})
    if d["reg_header"] != secs:
      errs.append(f"{REG}: the standards columns changed; integrated-coverage.svg reads {REG_HEADER!r}")
    if len(d["reg"]) > 92:
      errs.append(f"{REG}: {len(d['reg'])} work products; integrated-coverage.svg draws at most 92")
    for w, _ in EXAMPLES:
      if w not in {r[1] for r in d["reg"]}:
        errs.append(f"{REG}: {w} is gone; integrated-coverage.svg points at it")
    for x in ("IX-01", "IX-03", "IX-07"):
      if x not in {i["id"] for i in d["interfaces"]}:
        errs.append(f"{MODEL / 'interfaces.yaml'}: {x} is gone; integrated-joins.svg shows it")
    if len(d["log"]) > 9:
      errs.append(f"{HARA}: {len(d['log'])} hazards in §7; integrated-log.svg draws at most 9")
    if [n for n, _, _ in d["trace"]] != [n for n, _ in STD[:2]] + ["ISO/PAS 8800", "ISO/SAE 21434", "ASPICE"]:
      errs.append(f"{MAP}: the trace lanes are now {[n for n, _, _ in d['trace']]}; integrated-log.svg draws five")
    if any(len(items) > 6 for _, _, items in d["trace"]):
      errs.append(f"{MAP}: a trace lane has more than six boxes; integrated-log.svg draws at most six")
    if any(c.get("lifecycle_status") != "draft" for c in d["claims"]) or any(c.get("review_state") == "accepted" for c in d["claims"]):
      errs.append(f"{CASE}: a claim is past draft; integrated-case.svg says all are draft and none accepted, update it")
    if any(e.get("review_state") == "accepted" for e in d["evidence"]) or set(collections.Counter(e.get("evidence_status") for e in d["evidence"])) - {"partial", "missing"}:
      errs.append(f"{CASE}: evidence status moved past partial/missing; integrated-case.svg says none is accepted, update it")
    if any(f[2] for s, _, f in d["reg"] if s == "Safety analyses"):
      errs.append(f"{REG}: the safety analyses now have an ISO/SAE 21434 work product; integrated-coverage.svg says none, update it")
    if len(d["branches"]) != 5:
      errs.append(f"{CASE}: integrated-case.svg draws five branches")
  except (ParseError, OSError, ValueError, AttributeError, yaml.YAMLError) as e:
    errs.append(f"cannot read the records the integrated-standards page is drawn from: {e}")
  return errs


def caps(tl, steps):
  out = []
  for i, (t0, cap) in enumerate(steps):
    t1 = steps[i + 1][0] - 0.2 if i + 1 < len(steps) else None
    out.append(g(f"{tl.show(t0, t1)} {'fin' if t1 is None else 'tr'}", [f'<rect x="24" y="66" width="{W - 48}" height="28" rx="6" fill="{NAVY}"/>', t(36, 85, cap, 13, "#fff", 600)]))
  return out


def chip(x, y, label, col, size=10.5, fg="#fff"):
  w = len(label) * 6.3 + 16
  return [f'<rect x="{x}" y="{y - 14}" width="{w:.0f}" height="20" rx="10" fill="{col}"/>', t(round(x + w / 2), y, label, size, fg, 700, "middle")], w


# ------------------------------------------------------------------ 0 silos vs integrated
def silos(d):
  tl, h = Timeline(32.0), 660
  b = [t(24, 38, "Five standards: silos or one system?", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Many organisations run each standard as its own project"),
                 (4.2, "Each silo keeps its own hazards, requirements, tests and report"),
                 (8.0, "The same swerve is analysed three times, under three names"),
                 (11.6, "And some problems fall between the silos"),
                 (16.2, "Integrated: one lifecycle, one discipline lane per standard"),
                 (24.4, "LionDriver works this way; the numbers come from its own records")])
  tw, th, ty = 124, 230, 112
  blocks = ["hazards", "requirements", "tests", "report"]
  for i, (n, c) in enumerate(STD):
    x = 24 + i * (tw + 10)
    o = [f'<rect x="{x}" y="{ty}" width="{tw}" height="{th}" rx="10" fill="#fff" stroke="{c}" stroke-width="2.2"/>',
         f'<rect x="{x}" y="{ty}" width="{tw}" height="28" rx="10" fill="{c}"/>', f'<rect x="{x}" y="{ty + 16}" width="{tw}" height="12" fill="{c}"/>',
         t(x + tw / 2, ty + 19, n, 11.5, "#fff", 800, "middle")]
    for k, bl in enumerate(blocks):
      o += [f'<rect x="{x + 10}" y="{ty + 40 + k * 46}" width="{tw - 20}" height="38" rx="6" fill="#f4f6fa" stroke="{LIGHT}"/>',
            t(x + tw / 2, ty + 64 + k * 46, bl, 11.5, NAVY, 600, "middle")]
    b.append(g(f"{tl.show(0.5 + i * 0.5, 15.8)} tr", o))
  # same swerve three times
  for i, (lab, x) in enumerate([("H-01", 24), ("SH-01", 24 + tw + 10), ("DS-01", 24 + 2 * (tw + 10))]):
    b.append(g(f"{tl.show(8.2 + i * 0.5, 15.8)} tr", [f'<rect x="{x + 18}" y="{ty + 46}" width="{tw - 36}" height="26" rx="13" fill="{RED}"/>',
                                                       t(x + tw / 2, ty + 64, lab + " · swerve", 11, "#fff", 700, "middle")]))
  # falling between
  falls = [(11.8, 24 + tw + 2, "stale data: found by SOTIF and by security"), (13.0, 24 + 2 * tw + 12, "a threat that reached no hazard (hatara IX-11)")]
  for t0, x, _ in falls:
    b.append(g(f"{tl.show(t0, 15.8)} tr", [f'<line x1="{x + 4}" y1="{ty + 10}" x2="{x + 4}" y2="{ty + th + 30}" stroke="{RED}" stroke-width="2" stroke-dasharray="4 4"/>',
                                            f'<circle cx="{x + 4}" cy="{ty + th + 34}" r="7" fill="{RED}"/>']))
  b.append(g(f"{tl.show(11.8, 15.8)} tr", [t(24, ty + th + 64, "Found twice, or not at all: stale-data steering (SOTIF FI-14, security TS-12);", 12, RED, 700),
                                           t(24, ty + th + 82, "driver-monitoring tampering reached no hazard until checked across (hatara IX-11).", 12, RED, 700)]))
  # integrated lanes
  lanes = [(n, c, d["lanes"][k]) for n, c, k in LANES]
  gx, gy, lw = 140, 112, 556
  base = []
  for k, ph in enumerate(["P0", "P1", "P2", "P3", "P4", "P5", "P6"]):
    x = gx + k * lw / 7
    base += [f'<line x1="{x:.0f}" y1="{gy}" x2="{x:.0f}" y2="{gy + 7 * 32}" stroke="#e5e9f0"/>', t(x + lw / 14, gy - 6, ph, 10.5, MID, 700, "middle")]
  b.append(g(f"{tl.show(16.4)} fin", base))
  for i, (n, c, cnt) in enumerate(lanes):
    y = gy + i * 32
    b.append(g(f"{tl.show(16.6 + i * 0.4)} fin", [f'<rect x="{gx}" y="{y + 4}" width="{lw}" height="24" rx="5" fill="{c}" opacity="0.13"/>',
                                                   t(gx - 8, y + 21, n, 11.5, c, 800, "end"), t(gx + lw - 8, y + 21, f"{cnt} activities", 10.5, c, 700, "end")]))
  # interfaces
  rnd = random.Random(4)
  ifs = []
  for k in range(14):
    x = gx + 30 + k * 32
    a, bb = rnd.sample(range(7), 2)
    ifs.append(f'<line x1="{x}" y1="{gy + a * 32 + 16}" x2="{x + 14}" y2="{gy + bb * 32 + 16}" stroke="{NAVY}" stroke-width="1.6" opacity="0.55"/>')
    ifs.append(f'<circle cx="{x + 14}" cy="{gy + bb * 32 + 16}" r="3" fill="{NAVY}"/>')
  b.append(g(f"{tl.show(20.2)} fin", ifs))
  b.append(g(f"{tl.show(20.6)} fin", [t(gx, gy + 7 * 32 + 22, "lines: cross-domain interfaces, where one lane needs another's result (illustrative positions)", 11, MID, 400, "start", True)]))
  b.append(g(f"{tl.show(24.6)} fin", [f'<rect x="24" y="400" width="{W - 48}" height="150" rx="12" fill="#fff" stroke="{NAVY}" stroke-width="2"/>',
             t(40, 424, "LionDriver: one of each", 13.5, NAVY, 800),
             t(40, 448, "• one hazard log: each hazard with its SOTIF hazards and TARA threats on one row (WP-C-03 §7)", 12.5, NAVY),
             t(40, 470, f"• one lifecycle: {d['activities']} activities, {d['lanes']['joint']} of them joint, {len(d['interfaces'])} interfaces (WP-P-11)", 12.5, NAVY),
             t(40, 492, f"• one work-product register: {len(d['reg'])} work products, each naming every standard it serves", 12.5, NAVY),
             t(40, 514, "• one assurance case: a branch per standard under one top claim (WP-K-01)", 12.5, NAVY),
             t(40, 538, "Write it once, count it everywhere it applies, and check across the joins.", 12.5, AS, 700)]))
  b.append(g(f"{tl.show(26.0)} fin", [f'<rect x="24" y="566" width="{W - 110}" height="70" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 588, "Integrated does not mean merged: each standard keeps its own questions,", 12, NAVY),
             t(40, 606, "methods and assessor. It means shared items, shared data and checked joins.", 12, NAVY),
             t(40, 626, "", 1)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Five standards: silos or one system? (animated)",
             f"Five standards run as silos, each with its own hazards, requirements, tests and report, so the same swerve is analysed three times and problems fall between them; then LionDriver's integrated lifecycle with a lane per discipline ({d['activities']} activities, {len(d['interfaces'])} interfaces), one hazard log, one register and one case.", tl, b)


# ------------------------------------------------------------------ 2 coverage matrix
def coverage(d):
  reg = d["reg"]
  tl, h = Timeline(30.0), 660
  b = [t(24, 38, "One work product, many standards", 22, NAVY, 700)]
  n = len(reg)
  multi = [r for r in reg if sum(r[2]) >= 3]
  single = [r for r in reg if sum(r[2]) == 1]
  b += caps(tl, [(0.3, f"All {n} work products of LionDriver against the standards they serve (WP-M-00)"),
                 (9.0, f"{len(multi)} of them serve three standards or more: written once, counted each time"),
                 (15.0, f"{len(single)} serve a single standard: the specialist analyses"),
                 (20.4, "Each row: where in the lifecycle does a standard have its work products?")])
  gx, gy, cw, rh = 140, 130, 6.1, 28
  labels = ["ISO 26262", "ISO 21448", "ISO/SAE 21434", "8800 and others", "ASPICE"]
  cols = [FS, SO, CS, AIc, AS]
  for i, (lab, c) in enumerate(zip(labels, cols, strict=True)):
    b.append(g(f"{tl.show(0.5)} fin", [t(gx - 8, gy + i * rh + 19, lab, 11, c, 800, "end")]))
  # section bands
  secs = []
  for j, (s, _, _) in enumerate(reg):
    if not secs or secs[-1][0] != s:
      secs.append([s, j, j])
    secs[-1][2] = j
  short = {"Management": "Mgmt", "Concept phase": "Concept", "System level": "System", "Hardware level": "HW", "Software level": "SW",
           "Validation": "Valid.", "Supporting processes": "Support", "Safety analyses": "FTA…", "Production, operation and decommissioning": "Ops",
           "Assurance cases and release": "Cases", "Traceability": "Tr"}
  for s, a, e in secs:
    x0, x1 = gx + a * cw, gx + (e + 1) * cw
    b.append(g(f"{tl.show(0.8)} fin", [f'<line x1="{x0:.1f}" y1="{gy - 4}" x2="{x0:.1f}" y2="{gy + 5 * rh + 4}" stroke="{LIGHT}"/>',
                                       t((x0 + x1) / 2, gy - 10, short.get(s, s[:6]), 9.5, MID, 700, "middle")]))
  for j, (_, _, f) in enumerate(reg):
    x = gx + j * cw
    for i, on in enumerate(f):
      if on:
        b.append(g(f"{tl.show(1.2 + j * 0.08)} fin", [f'<rect x="{x + 0.6:.1f}" y="{gy + i * rh + 3}" width="{cw - 1.2:.1f}" height="{rh - 6}" rx="1.5" fill="{cols[i]}"/>']))
  # multi highlight
  for j, (_, _, f) in enumerate(reg):
    if sum(f) >= 3:
      x = gx + j * cw
      b.append(g(f"{tl.show(9.2)} fin", [f'<rect x="{x:.1f}" y="{gy - 2}" width="{cw:.1f}" height="{5 * rh + 4}" fill="none" stroke="{NAVY}" stroke-width="1.2"/>']))
  b.append(g(f"{tl.show(9.4)} fin", [t(gx, gy + 5 * rh + 22, "outlined: serves three standards or more", 11, NAVY, 700)]))
  # examples
  ex = [(w, f"{name}: {served(next(r[2] for r in reg if r[1] == w))}") for w, name in EXAMPLES]
  for i, (w, lab) in enumerate(ex):
    j = next(k for k, r in enumerate(reg) if r[1] == w)
    x = gx + j * cw + cw / 2
    y = 330 + i * 26
    right = x > W / 2
    b.append(g(f"{tl.show(10.6 + i * 1.2)} fin", [f'<line x1="{x:.1f}" y1="{gy + 5 * rh + 4}" x2="{x:.1f}" y2="{y - 4}" stroke="{NAVY}" stroke-width="1" stroke-dasharray="2 2"/>',
                                                   f'<circle cx="{x:.1f}" cy="{y - 4}" r="3" fill="{NAVY}"/>',
                                                   t(x - 8 if right else x + 8, y, f"{w} · {lab}", 11.5, NAVY, 600, "end" if right else "start")]))
  # per-standard counts
  counts = [sum(r[2][i] for r in reg) for i in range(5)]
  by = 450
  b.append(g(f"{tl.show(20.6)} fin", [t(24, by - 8, "Work products per standard", 12.5, NAVY, 700)]))
  for i, (lab, c, k) in enumerate(zip(labels, cols, counts, strict=True)):
    y = by + i * 24
    b.append(g(f"{tl.show(20.8 + i * 0.4)} fin", [t(24, y + 13, lab, 11.5, c, 700), f'<rect x="200" y="{y + 2}" width="{k * 4.4:.0f}" height="14" rx="3" fill="{c}"/>',
                                                   t(206 + k * 4.4, y + 14, str(k), 11.5, NAVY, 700)]))
  b.append(g(f"{tl.show(23.4)} fin", [f'<rect x="24" y="578" width="{W - 110}" height="62" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 600, "A gap shows as an empty stretch: e.g. no ISO/SAE 21434 work product in the analyses", 12, NAVY),
             t(40, 618, "section, because the TARA sits with the concept. Coverage is a map, not a score.", 12, NAVY)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "One work product, many standards (animated)",
             f"All {n} work products of the register as columns against the five standard groups they serve; those serving three or more are outlined, four are labelled, and the count per standard is shown.", tl, b)



# ------------------------------------------------------------------ 1 the joins
def joins(d):
  ifs = d["interfaces"]
  cnt = collections.Counter(x["pattern"] for x in ifs)
  st = collections.Counter(x["status"] for x in ifs)
  tl, h = Timeline(30.0), 650
  b = [t(24, 38, "Where the standards meet: the joins", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "An interface: one discipline's work depends on another's result"),
                 (4.0, f"LionDriver records {len(ifs)} of them, each anchored in both work products (WP-P-11)"),
                 (11.6, "Three examples, one per kind of join"),
                 (22.8, "A join is checked: the anchor text must be in both documents, or CI fails")])
  top = cnt.most_common()
  y0 = 112
  b.append(g(f"{tl.show(4.2)} fin", [t(24, y0 + 4, "interfaces by pair of disciplines", 11, MID, 800)]))
  for i, (p, n) in enumerate(top[:7]):
    y = y0 + 14 + i * 24
    b.append(g(f"{tl.show(4.4 + i * 0.4)} fin", [t(24, y + 13, p, 11.5, NAVY, 700), f'<rect x="170" y="{y + 2}" width="{n * 26}" height="14" rx="3" fill="{AS}"/>',
                                                  t(176 + n * 26, y + 14, str(n), 11.5, NAVY, 700)]))
  rest = sum(n for _, n in top[7:])
  b.append(g(f"{tl.show(7.4)} fin", [t(24, y0 + 14 + 7 * 24 + 13, f"+ {rest} more across operation, release, tools and suppliers", 11, MID, 400, "start", True)]))
  b.append(g(f"{tl.show(8.2)} fin", [f'<rect x="470" y="{y0 + 14}" width="226" height="80" rx="10" fill="#fff" stroke="{GRN}" stroke-width="2"/>',
                                     t(484, y0 + 40, f"{st['documented']} documented", 14, GRN, 800), t(484, y0 + 62, f"{st.get('open', 0)} open, settled by an open item", 12, NAVY),
                                     t(484, y0 + 82, "none yet reviewed", 11.5, MID, 400, "start", True)]))
  ex = [("IX-01", "Safety-Security", "HARA ↔ TARA", "Cyber effects map onto the HARA hazards; the TARA rates", "safety impact against those hazards and their ASILs.", FS, CS),
        ("IX-03", "Safety-SOTIF", "HARA ↔ SOTIF hazards", "One hazard log: each HARA hazard names the SOTIF hazards", "with the same vehicle-level effect.", FS, SO),
        ("IX-07", "Security-AI", "TARA ↔ AI requirements", "Models load through pickle with no hash: the same gap is", "an AI integrity requirement and a threat scenario.", CS, AIc)]
  for i, (iid, pat, pair, l1, l2, c1, c2) in enumerate(ex):
    y = 330 + i * 72
    b.append(g(f"{tl.show(11.8 + i * 3.4)} fin", [f'<rect x="24" y="{y}" width="{W - 48}" height="64" rx="10" fill="#fff" stroke="{LIGHT}"/>',
                                                   f'<rect x="24" y="{y}" width="8" height="64" rx="4" fill="{c1}"/>', f'<rect x="{W - 32}" y="{y}" width="8" height="64" rx="4" fill="{c2}"/>',
                                                   t(44, y + 22, f"{iid} · {pair}", 12.5, NAVY, 800), t(W - 44, y + 22, pat, 11, MID, 700, "end"),
                                                   t(44, y + 40, l1, 12, NAVY), t(44, y + 56, l2, 12, NAVY)]))
  b.append(g(f"{tl.show(23.0)} fin", [f'<rect x="24" y="552" width="{W - 110}" height="78" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 574, "In a silo, nobody owns the join. Here each join names its two work products", 12, NAVY),
             t(40, 594, "and quotes both; when one side changes its text, the model check fails.", 12, NAVY),
             t(40, 616, "Separate from hatara/'s interactions, which ask whether a measure helps or hurts.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "Where the standards meet (animated)",
             f"The {len(ifs)} cross-domain interfaces of the process model by pair of disciplines and their status, three examples (HARA and TARA, HARA and SOTIF hazards, TARA and AI requirements), and how each is checked against both work products.", tl, b)


# ------------------------------------------------------------------ 3 one hazard log, one V
def one_log(d):
  tl, h = Timeline(30.0), 660
  one = all(traced for _, _, items in d["trace"] for _, traced in items)
  b = [t(24, 38, "One hazard log, one trace", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "Each vehicle-level hazard, with its SOTIF and security causes on one row (WP-C-03 §7)"),
                 (9.8, "The log is checked against the TARA: here they disagree" if any(r[3] for r in d["log"]) else "The log is checked against the TARA's damage scenarios: they agree"),
                 (14.6, "Below: the trace, one lane per standard (WP-T-01 §3)"),
                 (22.0, "Every lane is in the trace data and checked by CI" if one else
                  "Solid boxes are in the trace data; dashed ones are linked in tables only")])
  rows = d["log"]
  hy = 104
  b.append(g(f"{tl.show(0.5)} fin", [t(40, hy + 14, "HARA", 11, FS, 800), t(120, hy + 14, "SOTIF", 11, SO, 800), t(210, hy + 14, "TARA damage scenarios that reach it (WP-C-09 §3)", 11, CS, 800)]))
  for i, (hz, sh, ts, flag) in enumerate(rows):
    y = hy + 22 + i * 26
    o = [f'<rect x="24" y="{y}" width="{W - 48}" height="22" rx="4" fill="{"#fff" if i % 2 else "#f7f8fb"}"/>',
         t(40, y + 16, hz, 11.5, FS, 800), t(120, y + 16, sh, 11.5, SO if sh != "—" else MID, 800), t(210, y + 16, ts, 11.5, NAVY if ts != "—" else MID, 600)]
    b.append(g(f"{tl.show(0.8 + i * 0.5)} fin", o))
    if flag:
      ch, w = chip(W - 40 - (len("log says —, but " + flag) * 6.3 + 16), y + 15, "log says —, but " + flag, RED)
      b.append(g(f"{tl.show(10.0)} fin", ch))
  # trace lanes
  ly = 370
  lanes = d["trace"]
  for i, (n, c, items) in enumerate(lanes):
    y = ly + i * 38
    o = [t(24, y + 20, n, 11.5, c, 800)]
    for k, (it, traced) in enumerate(items):
      x = 132 + k * 90
      dash = "" if traced else ' stroke-dasharray="4 3"'
      o += [f'<rect x="{x}" y="{y + 4}" width="78" height="26" rx="6" fill="#fff" stroke="{c}" stroke-width="1.8"{dash}/>', t(x + 39, y + 22, it, 11, NAVY, 700, "middle")]
      if k:
        o.append(f'<line x1="{x - 12}" y1="{y + 17}" x2="{x}" y2="{y + 17}" stroke="{c}" stroke-width="1.8"{dash}/>')
    b.append(g(f"{tl.show(14.8 + i * 0.8)} fin", o))
  b.append(g(f"{tl.show(22.2)} fin", [f'<rect x="24" y="566" width="{W - 110}" height="72" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             *([t(40, 588, "All five standards are in one trace, checked by CI on every change. Still open", 12, NAVY),
                t(40, 606, "(WP-T-01 §7): tags in the code and recorded test results.", 12, NAVY)] if one else
               [t(40, 588, "Solid: in the trace data, checked by CI. Dashed: linked in the work-product", 12, NAVY),
                t(40, 606, "tables only (WP-T-01 §7). Bringing them in is what makes the trace one.", 12, NAVY)]),
             t(40, 626, "", 1)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "One hazard log, one trace (animated)",
             "Each hazard of WP-C-03 with its SOTIF hazard and the TARA damage scenarios that reach it, any disagreement with the TARA flagged; then the trace lanes per standard, solid where in the trace data and dashed where linked in tables only.", tl, b)


# ------------------------------------------------------------------ 4 one mechanism
def one_mechanism():
  tl, h = Timeline(28.0), 640
  b = [t(24, 38, "One mechanism, five standards", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "The panda safety envelope: torque and acceleration limits plus the safety-mode lock"),
                 (3.4, "Each standard asks something different of the same mechanism"),
                 (17.6, "Build it once, verify it once, cite it in every case"),
                 (22.6, "And a gap in it is a gap in all of them")])
  cx, cy = W / 2, 300
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="{cx - 100}" y="{cy - 44}" width="200" height="88" rx="14" fill="#fff6ef" stroke="{ORANGE}" stroke-width="3"/>',
                                     t(cx, cy - 12, "panda envelope", 15, NAVY, 800, "middle"), t(cx, cy + 8, "torque cap · accel bounds", 11.5, MID, 600, "middle"),
                                     t(cx, cy + 26, "safety-mode lock", 11.5, MID, 600, "middle")]))
  spokes = [("ISO 26262", FS, "FSR-01.01 torque cap", "TSR-512 mode lock", (-210, -150)),
            ("ISO 21448", SO, "AC-02: every actuation", "inside controllable limits", (210, -150)),
            ("ISO/SAE 21434", CS, "CSG-01 / CSR-C-01:", "no unauthenticated mode change", (-230, 30)),
            ("ISO/PAS 8800", AIc, "AIR-28: AI outputs reach the", "actuators only through it", (230, 30)),
            ("ASPICE", AS, "SWE.4: 100 % line coverage,", "mutation, MISRA (rated L)", (0, 170))]
  for i, (n, c, l1, l2, (dx, dy)) in enumerate(spokes):
    x, y = cx + dx, cy + dy
    b.append(g(f"{tl.show(3.6 + i * 2.6)} fin", [f'<line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="{c}" stroke-width="2.5"/>',
                                                  f'<rect x="{x - 115}" y="{y - 34}" width="230" height="68" rx="10" fill="#fff" stroke="{c}" stroke-width="2.2"/>',
                                                  t(x, y - 12, n, 12.5, c, 800, "middle"), t(x, y + 6, l1, 11.5, NAVY, 600, "middle"), t(x, y + 22, l2, 11.5, NAVY, 600, "middle")]))
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="{cx - 100}" y="{cy - 44}" width="200" height="88" rx="14" fill="#fff6ef" stroke="{ORANGE}" stroke-width="3"/>',
                                     t(cx, cy - 12, "panda envelope", 15, NAVY, 800, "middle"), t(cx, cy + 8, "torque cap · accel bounds", 11.5, MID, 600, "middle"),
                                     t(cx, cy + 26, "safety-mode lock", 11.5, MID, 600, "middle")]))
  b.append(g(f"{tl.show(22.8)} fin", [f'<rect x="24" y="514" width="{W - 110}" height="108" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 536, "Today: the cap is in place but fixed, not speed-dependent (GAP-04); the lock is built", 12, NAVY),
             t(40, 554, "in the reference release but not verified; controllability (CA-01) and the", 12, NAVY),
             t(40, 572, "penetration test are not run. Each of those holds back a claim in every case.", 12, NAVY),
             t(40, 598, "In silos, five teams would each specify, test and argue the same limits.", 12, AS, 700)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "One mechanism, five standards (animated)",
             "The panda safety envelope in the middle, and what ISO 26262, ISO 21448, ISO/SAE 21434, ISO/PAS 8800 and ASPICE each ask of it; what is still open in it, which holds back a claim in every case.", tl, b)


# ------------------------------------------------------------------ 5 one case
def one_case(d):
  br, ev, shared, df = d["branches"], d["evidence"], d["shared"], d["defeaters"]
  evs = collections.Counter(e.get("evidence_status") for e in ev)
  nclaims = sum(n for _, _, n in br) + 1
  tl, h = Timeline(28.0), 640
  b = [t(24, 38, "One assurance case", 22, NAVY, 700)]
  b += caps(tl, [(0.3, "One top claim: the reference configuration poses no unreasonable risk (G0)"),
                 (2.6, "One branch per standard, each argued its own way"),
                 (9.6, "Some evidence holds up claims in two branches at once"),
                 (14.4, "Doubts are recorded against claims, across the branches"),
                 (19.6, "Today: everything drafted, nothing accepted")])
  b.append(g(f"{tl.show(0.5)} fin", [f'<rect x="{W / 2 - 150}" y="104" width="300" height="44" rx="10" fill="{NAVY}"/>',
                                     t(W / 2, 131, "G0 · no unreasonable risk", 13.5, "#fff", 800, "middle")]))
  bw = 128
  for i, (n, c, k) in enumerate(br):
    x = 24 + i * (bw + 8)
    b.append(g(f"{tl.show(2.8 + i * 0.9)} fin", [f'<path d="M{W / 2},148 L{x + bw / 2},190" stroke="{c}" stroke-width="2"/>',
                                                  f'<rect x="{x}" y="190" width="{bw}" height="64" rx="10" fill="#fff" stroke="{c}" stroke-width="2.2"/>',
                                                  t(x + bw / 2, 212, n.split(" ", 1)[0], 13, c, 800, "middle"), t(x + bw / 2, 228, n.split(" ", 1)[1], 10.5, NAVY, 600, "middle"),
                                                  t(x + bw / 2, 246, f"{k} claim{'s' if k != 1 else ''}", 10.5, MID, 600, "middle")]))
  # shared evidence
  b.append(g(f"{tl.show(9.8)} fin", [t(24, 288, f"{len(shared)} pieces of evidence support claims in two branches, e.g.:", 12.5, NAVY, 700)]))
  for i, e in enumerate(shared[:4]):
    y = 312 + i * 24
    b.append(g(f"{tl.show(10.2 + i * 0.7)} fin", [t(40, y, f"{e['id']} · {e['title'][:52]}", 11.5, NAVY, 600), t(W - 40, y, " + ".join(e["related_claims"]), 11.5, AS, 700, "end")]))
  b.append(g(f"{tl.show(14.6)} fin", [f'<rect x="24" y="420" width="{W - 48}" height="42" rx="8" fill="#fff" stroke="{RED}" stroke-width="1.8"/>',
                                      t(40, 446, f"{len(df)} defeaters: recorded doubts, each pointing at the claims it weakens", 12.5, RED, 700)]))
  b.append(g(f"{tl.show(19.8)} fin", [f'<rect x="24" y="478" width="{W - 110}" height="144" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 500, "LionDriver today (assurance/case)", 13, NAVY, 700),
             t(40, 522, f"{nclaims} claims, all draft; none accepted by review.", 12, NAVY),
             t(40, 542, f"{len(ev)} pieces of evidence: {evs['partial']} partial, {evs['missing']} missing, none accepted.", 12, NAVY),
             t(40, 562, "The case is generated from records and checked in CI, so its status is never", 12, NAVY),
             t(40, 580, "better than the evidence behind it: What is a safety case? shows how it is read.", 12, NAVY),
             t(40, 606, "Branch G4 holds one claim here; its detail is in the cybersecurity case WP-K-03.", 11, MID, 400, "start", True)]))
  b.append(stick(W - 40, h - 20, "point"))
  return svg(h, "One assurance case (animated)",
             f"The top claim G0 with one branch per standard and its claim count, the {len(shared)} pieces of evidence shared between branches, the {len(df)} defeaters, and the status today: {nclaims} draft claims and {len(ev)} pieces of evidence, none accepted.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  d = data(root)
  figs = (silos(d), joins(d), coverage(d), one_log(d), one_mechanism(), one_case(d))
  return dict(zip(NAMES, figs, strict=True))


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render(root).items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a record a figure stands on changed")
  args = ap.parse_args(argv)
  errs = problems()
  for e in errs:
    print(e, file=sys.stderr)
  if args.out is not None and not errs:
    write_all(args.out)
    print(f"wrote {len(NAMES)} animations to {args.out}")
  return 1 if errs else 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
