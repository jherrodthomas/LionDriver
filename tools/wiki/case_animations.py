#!/usr/bin/env python3
"""Render the animated explainers of the wiki page "What is a safety case?" as SVG, from the safety-case records.

  case-what-is-it.svg     the definition of a safety case built one phrase at a time: the system, its environment,
                          the top claim G0, the argument S0 into G1…G5, the evidence, the documents;
  case-claim-tree.svg     one path down the claim tree: G0 → S0 → G1 → S1 → G1.1 → S1.1 → G1.1.4 → its evidence;
  case-evidence.svg       what makes evidence count, on the record Sn-15: five questions, its status and review state,
                          what never counts on its own (the acceptance rules of assurance/case-records/README.md §4);
  case-defeaters.svg      defeaters on G1.1.4, with DF-02 and its closure route, the acceptance rule, and an
                          illustration (labelled as one) of how a defeater is closed.

Every ID, title, status and count drawn is read from `assurance/case-records/` (claims, arguments, evidence, defeaters) at
render time, so the figures follow the records. The few phrases that are the animation's own summary of a record
are checked against it (`problems()`): when the record changes, the wiki build fails instead of animating old text.
build_wiki.py renders them next to the pages at each sync (nothing is committed), as it does for animations.py.
A viewer who asks for reduced motion sees the final frame.

Usage: python3 tools/wiki/case_animations.py [--out DIR] [--check]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animations import GRN, LIGHT, MID, NAVY, RED, RED_BG, W, Timeline, g, norm, stick, svg, t  # noqa: E402

CASE = Path("assurance") / "case"
NAMES = ("case-what-is-it.svg", "case-claim-tree.svg", "case-evidence.svg", "case-defeaters.svg")
BLUE, TEAL, VIOLET, ORANGE, AMBER = "#2a78d6", "#0f766e", "#6250d6", "#c2410c", "#b7791f"
EV_GREEN = "#1f9d63"

# the examples the animations follow, and the path down the tree
PATH = ["G0", "G1", "G1.1", "G1.1.4"]
EVIDENCE = "Sn-15"
DEFEATER = "DF-02"
CONFIG = "CFG-001"

DEFINITION = ["A safety case is a structured, documented argument supported by evidence",
              "that shows a system is acceptably safe to operate in a specific environment."]
NEVER = ["a passing CI run", "a passing test", "a file that exists", "an AI-written review"]

# (file, phrase): the animation's own wording of a record, checked against it
SUMMARIES = [
  (CASE / "configurations" / "cfg-001-toyota-corolla-e210.yaml", "Toyota Corolla"),
  (CASE / "configurations" / "cfg-001-toyota-corolla-e210.yaml", "comma device with the integrated panda safety MCU"),
  (Path("assurance") / "02-concept" / "WP-C-02-odd-and-intended-functionality.md", "limited-access highways only"),
  (CASE / "README.md", "What never accepts anything: a passing CI run, a passing test, the existence of a file, or an AI-generated review"),
  (CASE / "README.md", "a `review_ref` pointing to an accepted review record that lists the object, at the same baseline"),
  (CASE / "README.md", "no defeater attached to it is open"),
]
# phrases of the example records that the animations paraphrase
EVIDENCE_PHRASES = ["no run recorded as evidence yet", "host x86 not target"]
DEFEATER_PHRASES = ["heartbeat absence (0.3 s)", "FTTI (≤ 0.5 s)", "unmeasured"]
DEFEATER_CLOSURE = "measurement on HIL `test_12`"


# ---------------------------------------------------------------- records

def load(root: Path = ROOT) -> dict:
  case = root / CASE
  claims = {}
  for f in sorted((case / "claims").glob("*.yaml")):
    for c in yaml.safe_load(f.read_text(encoding="utf-8")):
      claims[c["id"]] = c
  args = {a["id"]: a for a in yaml.safe_load((case / "arguments" / "strategies.yaml").read_text(encoding="utf-8"))}
  ev = {e["id"]: e for e in yaml.safe_load((case / "evidence" / "evidence.yaml").read_text(encoding="utf-8"))}
  df = {d["id"]: d for d in yaml.safe_load((case / "defeaters" / "defeaters.yaml").read_text(encoding="utf-8"))}
  return {"claims": claims, "args": args, "evidence": ev, "defeaters": df}


def problems(root: Path = ROOT) -> list[str]:
  errs = []
  for path, phrase in SUMMARIES:
    p = root / path
    if not p.exists() or norm(phrase) not in norm(p.read_text(encoding="utf-8")):
      errs.append(f"{path}: phrase the safety-case animations rely on is gone: {phrase!r}")
  try:
    r = load(root)
  except (OSError, yaml.YAMLError, KeyError, TypeError) as e:
    return errs + [f"{CASE}: records cannot be read: {e}"]
  c, a = r["claims"], r["args"]
  for i in range(1, len(PATH)):
    child = c.get(PATH[i])
    if not child or child.get("parent") != PATH[i - 1] or child.get("argument") not in a:
      errs.append(f"{CASE}: {PATH[i]} is no longer under {PATH[i - 1]} through an argument")
  e = r["evidence"].get(EVIDENCE)
  if not e or EVIDENCE not in (c.get(PATH[-1]) or {}).get("evidence_refs", []):
    errs.append(f"{CASE}: {EVIDENCE} no longer supports {PATH[-1]}")
  else:
    errs += [f"{CASE}: {EVIDENCE} description no longer says {p!r}" for p in EVIDENCE_PHRASES if p not in e["description"]]
  d = r["defeaters"].get(DEFEATER)
  if not d or d.get("lifecycle_status") != "open" or PATH[-1] not in d.get("related_claims", []):
    errs.append(f"{CASE}: {DEFEATER} is no longer an open defeater of {PATH[-1]}; choose another example")
  else:
    errs += [f"{CASE}: {DEFEATER} title no longer says {p!r}" for p in DEFEATER_PHRASES if p not in d["title"]]
    if DEFEATER_CLOSURE not in d["description"]:
      errs.append(f"{CASE}: {DEFEATER} closure route no longer says {DEFEATER_CLOSURE!r}")
  return errs


# ---------------------------------------------------------------- pieces

def short(title: str) -> str:
  """A claim title without its parenthetical standard, e.g. 'Functional safety (ISO 26262)' -> 'Functional safety'."""
  return re.sub(r"\s*\([^)]*\)\s*$", "", title)


def wrap(text: str, width: int) -> list[str]:
  words, lines = text.split(), [""]
  for w in words:
    if lines[-1] and len(lines[-1]) + 1 + len(w) > width:
      lines.append(w)
    else:
      lines[-1] = (lines[-1] + " " + w).strip()
  return lines


def fit(text: str, width: int, lines: int) -> list[str]:
  """`text` wrapped to at most `lines` lines of `width` characters, the last ending in an ellipsis if cut."""
  if lines == 1:
    return [text if len(text) <= width else text[:width - 1].rstrip(", ") + "…"]
  out = wrap(text, width)
  if len(out) > lines:
    out = out[:lines]
    out[-1] = out[-1][:width - 1].rstrip(",") + "…"
  return out


def claim_box(x, y, w, h, gid, lines, hot=False, size=12) -> list[str]:
  sw, col = (3, ORANGE) if hot else (1.6, NAVY)
  o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="#fff" stroke="{col}" stroke-width="{sw}"/>',
       t(x + w / 2, y + 14, gid, 9.5, MID, 700, "middle")]
  for i, line in enumerate(lines):
    o.append(t(x + w / 2, y + 29 + i * 14, line, size, NAVY, 700, "middle"))
  return o


def strat(cx, y, sid, text, w) -> list[str]:
  return [f'<path d="M{cx - w / 2 + 10},{y} h{w} l-10,28 h-{w} z" fill="#f2f0fd" stroke="{VIOLET}" stroke-width="1.8"/>',
          t(cx - w / 2 + 22, y + 18, sid, 9.5, VIOLET, 700), t(cx + 14, y + 19, text, 11.5, NAVY, 600, "middle")]


def wire(x1, y1, x2, y2, col=MID, sw=1.4) -> str:
  return f'<path d="M{x1},{y1} V{(y1 + y2) / 2} H{x2} V{y2}" fill="none" stroke="{col}" stroke-width="{sw}"/>'


def ev_circle(x, y, label) -> list[str]:
  return [f'<circle cx="{x}" cy="{y}" r="15" fill="#eaf6ef" stroke="{EV_GREEN}" stroke-width="2"/>',
          t(x, y + 32, label, 10.5, EV_GREEN, 700, "middle")]


def captions(tl, steps) -> list[str]:
  out = []
  for i, (t0, cap) in enumerate(steps):
    t1 = steps[i + 1][0] - 0.2 if i + 1 < len(steps) else None
    out.append(g(f"{tl.show(t0, t1)} {'fin' if t1 is None else 'tr'}",
                 [f'<rect x="24" y="66" width="{W - 48}" height="28" rx="6" fill="{NAVY}"/>', t(36, 85, cap, 13, "#fff", 600)]))
  return out


def counts(r) -> dict:
  ev, cl, df = r["evidence"].values(), r["claims"].values(), r["defeaters"].values()
  return {"evidence": len(ev), "ev_accepted": sum(e["review_state"] == "accepted" for e in ev),
          "ev_reviewed": sum(e["review_state"] != "not-reviewed" for e in ev),
          "partial": sum(e["evidence_status"] == "partial" for e in ev), "missing": sum(e["evidence_status"] == "missing" for e in ev),
          "claims": len(cl), "drafts": sum(c["lifecycle_status"] == "draft" for c in cl),
          "claims_accepted": sum(c.get("review_state") == "accepted" for c in cl),
          "df_open": sum(d["lifecycle_status"] == "open" for d in df)}


# ---------------------------------------------------------------- 1 · what is a safety case?

def what_is_it(r) -> str:
  c, a, n = r["claims"], r["args"], counts(r)
  top = c[PATH[0]]
  s0 = a[c[PATH[1]]["argument"]]
  tl, h = Timeline(20.0), 640
  b = [t(24, 38, "What is a safety case?", 24, NAVY, 700),
       f'<rect x="24" y="56" width="{W - 48}" height="62" rx="10" fill="#fff" stroke="{LIGHT}"/>',
       t(40, 82, DEFINITION[0], 14.5, NAVY, 600, italic=True), t(40, 104, DEFINITION[1], 14.5, NAVY, 600, italic=True)]
  chips = [("SYSTEM", BLUE, 2.0), ("ENVIRONMENT", TEAL, 4.0), ("ACCEPTABLY SAFE", NAVY, 6.4),
           ("STRUCTURED ARGUMENT", VIOLET, 8.6), ("EVIDENCE", EV_GREEN, 11.2), ("DOCUMENTED", AMBER, 13.6)]
  x = 24
  for name, col, t0 in chips:
    w = len(name) * 7.4 + 20
    b += [f'<rect x="{x:.0f}" y="132" width="{w:.0f}" height="24" rx="12" fill="#eef1f5"/>', t(round(x + w / 2), 148, name, 11, MID, 700, "middle")]
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="{x:.0f}" y="132" width="{w:.0f}" height="24" rx="12" fill="{col}"/>',
                                       t(round(x + w / 2), 148, name, 11, "#fff", 700, "middle")]))
    x += w + 6
  b.append(g(f"{tl.show(2.0)} fin", [
    f'<path d="M40,268 h150 l-14,-26 h-34 l-12,-18 h-44 l-16,18 h-20 z" fill="#e8f0fb" stroke="{BLUE}" stroke-width="2.5"/>',
    f'<circle cx="72" cy="270" r="13" fill="#fff" stroke="{NAVY}" stroke-width="3"/>',
    f'<circle cx="158" cy="270" r="13" fill="#fff" stroke="{NAVY}" stroke-width="3"/>',
    f'<rect x="104" y="228" width="18" height="10" rx="2" fill="{BLUE}"/>',
    t(24, 206, "The system", 13, BLUE, 700), t(24, 304, "LionDriver: openpilot + the panda", 11.5, NAVY),
    t(24, 320, f"on a Toyota Corolla ({CONFIG})", 11.5, NAVY)]))
  b.append(g(f"{tl.show(4.0)} fin", [
    f'<path d="M24,340 h200" stroke="{TEAL}" stroke-width="3"/>', f'<path d="M24,372 h200" stroke="{TEAL}" stroke-width="3"/>',
    f'<path d="M24,356 h200" stroke="{TEAL}" stroke-width="2" stroke-dasharray="12 10"/>',
    t(24, 396, "The environment", 13, TEAL, 700), t(24, 414, "where it may be used: limited-access", 11.5, NAVY),
    t(24, 430, "highways only (its ODD, WP-C-02)", 11.5, NAVY)]))
  cx = 470
  b.append(g(f"{tl.show(6.4)} fin", claim_box(cx - 150, 196, 300, 48, f"CLAIM · {PATH[0]}", fit(top["title"], 42, 2), size=11.5)
             + [t(cx + 160, 214, "acceptably", 11, MID, 600, "start", True), t(cx + 160, 228, "safe", 11, MID, 600, "start", True)]))
  d = [f'<line x1="{cx}" y1="244" x2="{cx}" y2="262" stroke="{MID}" stroke-width="1.6"/>'] + strat(cx, 262, s0["id"], s0["title"], 300)
  xs = [cx - 180 + i * 90 for i in range(len(s0["subclaims"]))]
  for x0, gid in zip(xs, s0["subclaims"]):
    d += [wire(cx, 290, x0, 322)] + claim_box(x0 - 41, 322, 82, 50, gid, fit(short(c[gid]["title"]), 12, 2), size=11)
  b.append(g(f"{tl.show(8.6)} fin", d))
  e = []
  for x0 in xs:
    for dx in (-18, 18):
      e += [wire(x0, 372, x0 + dx, 396, MID, 1.2), f'<circle cx="{x0 + dx}" cy="410" r="13" fill="#eaf6ef" stroke="{EV_GREEN}" stroke-width="2"/>']
  e.append(t(cx, 446, f"EVIDENCE: tests, analyses, reviews ({n['evidence']} items in the records)", 11.5, EV_GREEN, 700, "middle"))
  b.append(g(f"{tl.show(11.2)} fin", e))
  doc = [f'<rect x="{40 + k * 8}" y="{478 - k * 8}" width="66" height="70" rx="4" fill="#fff" stroke="{AMBER}" stroke-width="2"/>' for k in range(3)]
  doc += [f'<line x1="66" y1="{y}" x2="114" y2="{y}" stroke="{LIGHT}" stroke-width="3"/>' for y in (480, 492, 504, 516)]
  doc += [t(140, 486, "Documented", 13, AMBER, 700), t(140, 504, "WP-K-01, and records anyone can", 11.5, NAVY),
          t(140, 520, "check (assurance/case-records, validated in CI)", 11.5, NAVY)]
  b.append(g(f"{tl.show(13.6)} fin", doc))
  state = ("Ours is in development: no claim is accepted yet, and the evidence awaits review." if n["claims_accepted"] == 0
           else f"{n['claims_accepted']} of {n['claims']} claims accepted so far.")
  b.append(g(f"{tl.show(15.6)} fin", [f'<rect x="24" y="560" width="{W - 48}" height="56" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
                                       t(40, 583, "Claim → argument → evidence, for one system in one environment.", 14, NAVY, 700),
                                       t(40, 603, state, 12.5, MID)]))
  b.append(stick(W - 40, 548, "point"))
  return svg(h, "What is a safety case? (animated)",
             " ".join(DEFINITION) + f" The system, LionDriver on a Toyota Corolla; its environment, limited-access highways; the "
             f"top claim {PATH[0]}, {top['title']}; the argument {s0['id']}, {s0['title']}, into "
             + ", ".join(f"{s} {short(c[s]['title'])}" for s in s0["subclaims"]) + f"; {n['evidence']} evidence items; the documents. "
             + state, tl, b)


# ---------------------------------------------------------------- 2 · breaking the big claim down

def claim_tree(r) -> str:
  c, a, n = r["claims"], r["args"], counts(r)
  s = [a[c[PATH[i]]["argument"]] for i in range(1, len(PATH))]   # S0, S1, S1.1
  tl, h = Timeline(24.0), 700
  b = [t(24, 38, "Breaking the big claim down", 24, NAVY, 700)]
  b += captions(tl, [(0.3, "1 · The top claim is too big to check directly"),
                     (3.0, "2 · An argument says how to split it into smaller claims"),
                     (8.0, "3 · Split again, and again, until each claim is small enough to test"),
                     (15.5, "4 · Only the smallest claims are checked against evidence"),
                     (19.0, "5 · The top holds only if every claim under it holds")])
  cx = W / 2
  b.append(g(f"{tl.show(0.5)} fin", claim_box(cx - 230, 106, 460, 34, PATH[0], [c[PATH[0]]["title"]], hot=True, size=12.5)))
  b.append(g(f"{tl.show(3.2)} fin", [wire(cx, 140, cx, 150)] + strat(cx, 150, s[0]["id"], s[0]["title"], 360)))
  subs = s[0]["subclaims"]
  for i, gid in enumerate(subs):
    x = 32 + i * 134
    b.append(g(f"{tl.show(4.0 + i * 0.3)} fin", [wire(cx, 178, x + 62, 192)]
               + claim_box(x, 192, 124, 34, gid, fit(short(c[gid]["title"]), 19, 1), hot=(gid == PATH[1]), size=11)))
  px = 32 + subs.index(PATH[1]) * 134 + 62
  b.append(g(f"{tl.show(8.2)} fin", [wire(px, 226, px, 240)] + strat(250, 240, s[1]["id"], s[1]["title"], 420)))
  subs2 = s[1]["subclaims"]
  pitch = min(66, (W - 64) // len(subs2))
  for i, gid in enumerate(subs2):
    x = 32 + i * pitch
    hot = gid == PATH[2]
    b.append(g(f"{tl.show(9.0 + i * 0.15)} fin", [wire(px, 268, x + 29, 282),
               f'<rect x="{x}" y="282" width="{pitch - 8}" height="26" rx="3" fill="#fff" stroke="{ORANGE if hot else NAVY}" stroke-width="{3 if hot else 1.4}"/>',
               t(x + (pitch - 8) / 2, 299, gid, 11, NAVY, 700, "middle")]))
  b.append(g(f"{tl.show(10.8)} fin", [t(96, 326, f"{PATH[2]} = {c[PATH[2]]['title']}; the others: the other safety goals and shared properties", 11, MID, 400, "start", True)]))
  qx = 32 + subs2.index(PATH[2]) * pitch + 29
  b.append(g(f"{tl.show(11.8)} fin", [wire(qx, 308, qx, 342)] + strat(300, 342, s[2]["id"], s[2]["title"], 500)))
  leaves = s[2]["subclaims"]
  lw = (W - 64 - 10 * (len(leaves) - 1)) / len(leaves)
  for i, gid in enumerate(leaves):
    x = 32 + i * (lw + 10)
    b.append(g(f"{tl.show(12.6 + i * 0.4)} fin", [wire(qx, 370, x + lw / 2, 386)]
               + claim_box(round(x), 386, round(lw), 62, gid, fit(c[gid]["title"], int(lw / 6.6), 3), hot=(gid == PATH[3]), size=11)))
  lx = 32 + leaves.index(PATH[3]) * (lw + 10) + lw / 2
  refs = c[PATH[3]]["evidence_refs"]
  e = []
  for k, sid in enumerate(refs):
    ex = lx - 35 * (len(refs) - 1) + 70 * k
    e += [wire(lx, 448, ex, 470, EV_GREEN)] + ev_circle(ex, 486, sid)
  b.append(g(f"{tl.show(15.8)} fin", e + [t(32, 480, "Small enough to check: a test, an analysis", 12.5, NAVY, 600),
                                            t(32, 498, "or a review can show it holds (or not).", 12.5, NAVY, 600)]))
  drafts = ("every one still a draft" if n["drafts"] == n["claims"] else f"{n['drafts']} of them still drafts")
  b.append(g(f"{tl.show(19.2)} fin", [f'<rect x="24" y="540" width="{W - 110}" height="66" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 562, "Orange: one path from the top claim to the evidence.", 13, NAVY, 700),
             t(40, 580, "A weak leaf anywhere weakens every claim above it.", 13, NAVY, 600),
             t(40, 598, f"{n['claims']} claims in all, {drafts}.", 12, MID)]))
  b.append(stick(W - 40, h - 70, "point"))
  return svg(h, "Breaking the big claim down (animated)",
             f"{PATH[0]} split by {s[0]['id']} into {', '.join(subs)}; {PATH[1]} split by {s[1]['id']} into {len(subs2)} claims; "
             f"{PATH[2]} split by {s[2]['id']} into {', '.join(leaves)}; {PATH[3]}, {c[PATH[3]]['title']}, checked against "
             f"evidence {', '.join(refs)}. {n['claims']} claims, {drafts}.", tl, b)


# ---------------------------------------------------------------- 3 · what makes evidence count

def evidence(r) -> str:
  c, e, n = r["claims"], r["evidence"][EVIDENCE], counts(r)
  leaf = c[PATH[-1]]
  complete = {"available": ("ok", "available"), "partial": ("part", "partial: no recorded run; PC, not the chip"),
              "missing": ("no", "missing")}[e["evidence_status"]]
  reviewed = ("ok", e["review_state"]) if e["review_state"] == "accepted" else ("no", e["review_state"].replace("-", " "))
  rows = [("Where", e["location"], "ok", "What is it, and where can I find it?"),
          ("Version", f"baseline {e['baseline']}", "ok", "Which version of the system?"),
          ("Car", f"configuration {e['configuration']}", "ok", "Which car and set-up?"),
          ("Complete?", complete[1], complete[0], "Was it run in full, on the real thing?"),
          ("Reviewed?", reviewed[1], reviewed[0], "Has an independent person checked it?")]
  mark = {"ok": (EV_GREEN, "✓"), "part": (AMBER, "~"), "no": (RED, "✗")}
  counts_now = complete[0] == "ok" and reviewed[0] == "ok"
  tl, h = Timeline(24.0), 700
  b = [t(24, 38, "What makes evidence count?", 24, NAVY, 700),
       t(24, 60, "Evidence shows a claim is true: a test, an analysis, a review", 14, MID)]
  b.append(g(f"{tl.show(0.4)} fin", claim_box(130, 78, 460, 46, f"CLAIM · {PATH[-1]}", [leaf["title"]], size=13.5)))
  cy = 150
  title = fit(re.sub(r"\s*\(.*$", "", e["title"]) + ": " + re.search(r"\((.*)\)", e["title"]).group(1), 44, 2)
  b.append(g(f"{tl.show(1.6)} fin", [f'<line x1="202" y1="124" x2="202" y2="{cy}" stroke="{MID}" stroke-width="1.6"/>',
             f'<rect x="24" y="{cy}" width="356" height="276" rx="12" fill="#fff" stroke="{EV_GREEN}" stroke-width="2"/>',
             f'<circle cx="48" cy="{cy + 24}" r="11" fill="#eaf6ef" stroke="{EV_GREEN}" stroke-width="2"/>',
             t(66, cy + 29, f"EVIDENCE · {EVIDENCE}", 11, EV_GREEN, 700),
             t(40, cy + 56, title[0], 13, NAVY, 700), t(40, cy + 74, title[-1], 13, NAVY, 700)]))
  qx = 400
  b.append(g(f"{tl.show(3.6)} fin", [t(qx, cy + 4, "Five questions before it counts", 14, NAVY, 700)]))
  for i, (lab, val, mk, q) in enumerate(rows):
    t0, ry, qy = 4.2 + i * 1.7, cy + 102 + i * 26, cy + 30 + i * 36
    col, sym = mark[mk]
    b.append(g(f"{tl.show(t0, t0 + 1.5)} tr", [f'<rect x="32" y="{ry - 16}" width="340" height="23" rx="5" fill="#eef4fc"/>',
                                               f'<rect x="{qx - 6}" y="{qy - 17}" width="{W - 18 - qx}" height="30" rx="6" fill="#eef4fc"/>']))
    b.append(g(f"{tl.show(t0)} fin", [t(40, ry, lab, 11.5, MID, 700), t(118, ry, val, 11.5, NAVY if mk == "ok" else col, 600),
                                       t(qx, qy, f"{i + 1}. {q}", 12.5, NAVY)]))
    b.append(g(f"{tl.show(t0 + 0.6)} fin", [f'<circle cx="{W - 36}" cy="{qy - 4}" r="11" fill="{col}"/>', t(W - 36, qy + 1, sym, 13, "#fff", 700, "middle")]))
  stamps = []
  if complete[0] != "ok":
    stamps.append((e["evidence_status"].upper(), AMBER if complete[0] == "part" else RED, 40, 150))
  if reviewed[0] != "ok":
    stamps.append((reviewed[1].upper(), RED, 200, 172))
  for k, (txt, col, x, w) in enumerate(stamps):
    b.append(g(f"{tl.show(13.4 + k * 0.6)} fin", [f'<g transform="rotate(-6 {x + w / 2} 400)"><rect x="{x}" y="382" width="{w}" height="34" rx="6" '
               f'fill="none" stroke="{col}" stroke-width="3"/>{t(x + w / 2, 405, txt, 16, col, 800, "middle")}</g>']))
  verdict = ("YES", EV_GREEN) if counts_now else ("NOT YET", RED)
  b.append(g(f"{tl.show(14.8)} fin", [f'<rect x="{qx}" y="386" width="{W - 24 - qx}" height="40" rx="10" fill="{RED_BG}" stroke="{verdict[1]}"/>',
             t(qx + 14, 411, "Counts toward the claim?", 13, NAVY, 700), f'<rect x="{W - 92}" y="395" width="56" height="22" rx="11" fill="{verdict[1]}"/>',
             t(W - 64, 411, verdict[0], 10.5, "#fff", 700, "middle")]))
  ny = 446
  b.append(g(f"{tl.show(16.6)} fin", [f'<rect x="24" y="{ny}" width="{W - 48}" height="128" rx="12" fill="#fff" stroke="{LIGHT}"/>',
                                       t(40, ny + 26, "These never make evidence count on their own", 14, NAVY, 700)]))
  x = 40
  for i, s in enumerate(NEVER):
    w = len(s) * 7 + 30
    b.append(g(f"{tl.show(17.0 + i * 0.4)} fin", [f'<rect x="{x}" y="{ny + 40}" width="{w}" height="26" rx="13" fill="#f1f3f7" stroke="{LIGHT}"/>',
               t(x + 12, ny + 58, "✗", 12, RED, 700), t(x + w / 2 + 6, ny + 58, s, 11.5, NAVY, 600, "middle")]))
    x += w + 8
  b.append(g(f"{tl.show(19.0)} fin", [t(40, ny + 96, "Only a review record, written by a named reviewer with the right independence,", 12.5, NAVY, 600),
                                       t(40, ny + 114, "at the same baseline, accepts it. Then the claim above can use it.", 12.5, NAVY, 600)]))
  tail = (f"{n['partial']} partial and {n['missing']} missing; {n['ev_reviewed']} reviewed so far."
          + (" The honest starting point." if n["ev_accepted"] == 0 else ""))
  b.append(g(f"{tl.show(20.4)} fin", [f'<rect x="24" y="594" width="{W - 110}" height="50" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 616, f"Today: {n['evidence']} evidence items, {n['ev_accepted']} accepted", 14, NAVY, 700), t(40, 634, tail, 12, MID)]))
  b.append(stick(W - 40, h - 14, "clip"))
  return svg(h, "What makes evidence count? (animated)",
             f"The claim {PATH[-1]}, {leaf['title']}, and its evidence {EVIDENCE}, {e['title']}. Five questions: where it is "
             f"({e['location']}), which version ({e['baseline']}), which car ({e['configuration']}), whether it is complete "
             f"({e['evidence_status']}), whether an independent person reviewed it ({e['review_state']}). Counts toward the claim: "
             f"{verdict[0].lower()}. A passing CI run, a passing test, a file that exists or an AI-written review never count on "
             f"their own; only a review record does. Today: {n['evidence']} evidence items, {n['ev_accepted']} accepted.", tl, b)


# ---------------------------------------------------------------- 4 · defeaters

def defeaters(r) -> str:
  c, d, n = r["claims"], r["defeaters"][DEFEATER], counts(r)
  leaf = c[PATH[-1]]
  others = [x for x in leaf["defeaters"] if x != DEFEATER and r["defeaters"][x]["lifecycle_status"] == "open"]
  tl, h = Timeline(24.0), 680
  b = [t(24, 38, "Defeaters: the doubts we write down", 24, NAVY, 700)]
  b += captions(tl, [(0.3, "1 · A claim, with its evidence"),
                     (2.6, "2 · A defeater (DF) is a reason the claim might not hold"),
                     (7.4, "3 · It says how it will be closed"),
                     (10.4, f"4 · This claim has {len(others) + 1} open defeaters"),
                     (13.6, "5 · While any is open, the claim cannot be accepted"),
                     (17.2, "6 · Closing one: do the work, then review it")])
  cx = 250
  refs = leaf["evidence_refs"]
  ev = []
  for k, sid in enumerate(refs):
    ex = cx - 35 * (len(refs) - 1) + 70 * k
    ev += [wire(cx, 160, ex, 190, EV_GREEN)] + ev_circle(ex, 206, sid)
  b.append(g(f"{tl.show(0.5)} fin", claim_box(cx - 200, 110, 400, 50, f"CLAIM · {PATH[-1]}", fit(leaf["title"], 44, 2), size=12.5) + ev))
  fx, fy = 470, 112

  def flag(col, lab):
    return [f'<line x1="{fx}" y1="{fy}" x2="{fx}" y2="{fy + 50}" stroke="{NAVY}" stroke-width="2.5"/>',
            f'<path d="M{fx},{fy} l40,10 l-40,12 z" fill="{col}"/>', t(fx + 46, fy + 18, lab, 12, col, 700),
            f'<line x1="{cx + 200}" y1="134" x2="{fx}" y2="{fy + 30}" stroke="{col}" stroke-width="2" stroke-dasharray="4 3"/>']

  b.append(g(f"{tl.show(2.8, 17.6)} tr", flag(RED, f"{DEFEATER} · open")))
  b.append(g(f"{tl.show(3.6)} fin", [f'<rect x="24" y="262" width="{W - 48}" height="70" rx="10" fill="{RED_BG}" stroke="{RED}"/>',
             t(40, 284, f"DEFEATER · {DEFEATER}", 12, RED, 700),
             t(40, 304, "The RX timeouts and the heartbeat-loss reaction (0.3 s) are inside the preliminary", 12.5, NAVY),
             t(40, 322, "0.5 s time budget on paper, but they have not been measured.", 12.5, NAVY)]))
  b.append(g(f"{tl.show(7.6)} fin", [f'<rect x="24" y="342" width="{W - 48}" height="40" rx="10" fill="#fff" stroke="{LIGHT}"/>',
             t(40, 367, "Closure route: measure it on the hardware-in-the-loop bench (HIL test_12).", 12.5, NAVY, 600)]))
  for i, x_id in enumerate(others[:12]):
    x, y = 470 + (i % 3) * 76, 176 + (i // 3) * 22
    b.append(g(f"{tl.show(10.6 + i * 0.2)} fin", [f'<path d="M{x},{y} l14,4 l-14,5 z" fill="{RED}"/>',
               f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 16}" stroke="{NAVY}" stroke-width="1.5"/>', t(x + 18, y + 10, x_id, 10.5, RED, 700)]))
  b.append(g(f"{tl.show(13.8)} fin", [f'<rect x="24" y="394" width="{W - 48}" height="54" rx="10" fill="#eef2f8" stroke="{NAVY}"/>',
             t(40, 416, "The rule: a claim is accepted only when its evidence is accepted, every claim", 12.5, NAVY, 600),
             t(40, 434, "under it is accepted, and no defeater on it is open.", 12.5, NAVY, 600)]))
  b.append(g(f"{tl.show(17.4)} fin", [f'<rect x="24" y="460" width="{W - 48}" height="128" rx="10" fill="#fff" stroke="{GRN}" stroke-dasharray="6 4"/>',
             t(40, 482, f"ILLUSTRATION · what closing {DEFEATER} would look like (it is still open)", 11, GRN, 700)]))
  for i, (s, t0) in enumerate([("Measure on HIL", 18.0), ("Record as evidence", 18.9), ("Independent review", 19.8), (f"{DEFEATER} closed", 20.7)]):
    x = 40 + i * 164
    b.append(g(f"{tl.show(t0)} fin", [f'<rect x="{x}" y="498" width="152" height="40" rx="8" fill="{"#eaf6ef" if i == 3 else "#f4f6f9"}" '
               f'stroke="{GRN if i == 3 else LIGHT}"/>', t(x + 76, 523, s, 11, NAVY, 700 if i == 3 else 600, "middle")]
               + ([t(x + 158, 523, "→", 13, MID, 700, "middle")] if i < 3 else [])))
  b.append(g(f"{tl.show(20.9)} fin", flag(GRN, f"{DEFEATER} · closed (illustration)")))
  b.append(g(f"{tl.show(21.4)} fin", [t(40, 568, "Writing doubts down is not a weakness: it shows exactly what is left to do.", 12.5, NAVY, 600)]))
  b.append(t(24, 616, f"Today: {n['df_open']} open defeaters across the case.", 13, MID, 700))
  b.append(stick(W - 40, h - 14, "point"))
  return svg(h, "Defeaters (animated)",
             f"The claim {PATH[-1]}, {leaf['title']}, with evidence {', '.join(refs)}. Defeater {DEFEATER}: the RX timeouts and the "
             f"heartbeat-loss reaction are inside the preliminary 0.5 s budget on paper but not measured; closure route, a "
             f"measurement on the HIL bench. {len(others)} more open defeaters on the same claim. The rule: no claim is accepted "
             f"while a defeater on it is open. An illustration of closing {DEFEATER}. {n['df_open']} open defeaters today.", tl, b)


def render(root: Path = ROOT) -> dict[str, str]:
  r = load(root)
  return {"case-what-is-it.svg": what_is_it(r), "case-claim-tree.svg": claim_tree(r), "case-evidence.svg": evidence(r),
          "case-defeaters.svg": defeaters(r)}


def write_all(out: Path, root: Path = ROOT) -> None:
  out.mkdir(parents=True, exist_ok=True)
  for name, text in render(root).items():
    (out / name).write_text(text, encoding="utf-8")


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--out", type=Path, default=None, help="write the SVGs here")
  ap.add_argument("--check", action="store_true", help="fail if a record or phrase the animations rely on changed")
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
