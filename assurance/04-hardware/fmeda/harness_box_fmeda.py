#!/usr/bin/env python3
"""Component-level FMEDA of the harness box v3 (WP-H-03 §6.5): checks, outputs, page and figures.

Reads harness-box-parts.yaml (one entry per designator) and fmeda-flow.yaml, and:

1. checks the part list against the box's sources: every designator of the RR-2026-010 HB rows and of the WireViz BOM
   is a part here, and every part here appears in one of them;
2. rolls the parts up into the goal FMEDAs (08-analyses/fmea/analyses/fmeda-sg009.yaml and fmeda-sg001.yaml): for each
   goal row the parts map to, the parts' rates must add up to the row's rate and, mode by mode, to the row's mode rates;
   each part mode's class must match the goal row's classification. Differences listed in known_differences are
   reported; a new one fails, and a listed one that has gone fails too, so the list only shrinks;
3. computes the four FMEDA outputs: failure rate per mode and per category, useful life, diagnostic coverage per mode,
   coverage of each periodic test; and what the goal metrics would be with the part-level findings applied
   (fmea_lint.fmeda_metrics on an in-memory copy; the FMEDA files are not changed);
4. writes README.md (the generated page), fig-h03-6-0-fmeda-flow.svg and fig-h03-6-5-box-parts.svg.

    python3 harness_box_fmeda.py            # write the outputs
    python3 harness_box_fmeda.py --check    # fail if a check fails or an output is stale

Needs PyYAML (pinned in assurance/trace/requirements.txt). Output is deterministic.
"""
from __future__ import annotations

import copy
import datetime
import io
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ASSURANCE = HERE.parents[1]
REPO = ASSURANCE.parent
FMEA = ASSURANCE / "08-analyses" / "fmea" / "analyses"
sys.path.insert(0, str(REPO / "tools" / "safety"))
import fmea_lint  # noqa: E402
sys.path.insert(0, str(ASSURANCE / "01-management" / "figures"))
from figkit import (INK, MUTED, FAINT, LINE, GREEN, GREEN_BG, AMBER, AMBER_BG, RED, RED_BG, SW, SW_BG,  # noqa: E402
                    FigureError, text, rect, path, svg, text_w)
sys.path.insert(0, str(ASSURANCE / "trace" / "tools"))
import terms  # noqa: E402

PARTS = HERE / "harness-box-parts.yaml"
FLOW = HERE / "fmeda-flow.yaml"
RR = ASSURANCE / "04-hardware" / "reviews" / "RR-2026-010.md"
BOM = ASSURANCE / "04-hardware" / "wiring" / "e05-harness-box.bom.tsv"
GOAL_FILE = {"SG-07": "fmeda-sg009", "SG-01": "fmeda-sg001"}
CLASSES = ("SPF", "RF", "MPF-L", "safe", "none", "open")
OUT_MD, OUT_FLOW, OUT_PARTS = "README.md", "fig-h03-6-0-fmeda-flow.svg", "fig-h03-6-5-box-parts.svg"
OUT_XLSX = "harness-box-fmeda.xlsx"
STAMP = datetime.datetime(2026, 11, 13)   # the part list's version date; keeps the workbook's bytes stable
EFFECT = {"safe": "S", "SPF": "D", "RF": "D", "MPF-L": "L", "none": "#", "open": "?"}
GOAL_TITLE = {"SG-07": "keep the stock pre-collision braking", "SG-01": "lateral control within the envelope"}
W = 640
CLASS_STYLE = {"SPF": (RED, RED_BG), "RF": (AMBER, AMBER_BG), "MPF-L": ("#7C3AED", "#F5F3FF"), "safe": (GREEN, GREEN_BG),
               "none": (FAINT, "#F8FAFC"), "open": (MUTED, "#F1F5F9")}
STATE_STYLE = {"done": (GREEN, GREEN_BG), "partial": (AMBER, AMBER_BG), "missing": (RED, RED_BG),
               "not-needed": (FAINT, "#F8FAFC")}


class BoxError(ValueError):
  pass


# ---------------------------------------------------------------- inputs

def load() -> tuple[dict, dict, dict]:
  data = yaml.safe_load(PARTS.read_text(encoding="utf-8"))
  flow = yaml.safe_load(FLOW.read_text(encoding="utf-8"))
  goals = {f: yaml.safe_load((FMEA / f"{f}.yaml").read_text(encoding="utf-8")) for f in GOAL_FILE.values()}
  return data, flow, goals


def source_designators() -> set[str]:
  refs = set()
  for ln in RR.read_text(encoding="utf-8").splitlines():
    if re.match(r"^\| HB-0[1-6] \|", ln):
      refs |= set(re.findall(r"\b([URDQJ]\d)\b", ln.split("|")[2]))
  for ln in BOM.read_text(encoding="utf-8").splitlines()[1:]:
    cells = ln.split("\t")
    if len(cells) >= 5:
      refs |= set(re.findall(r"\b([URDQJ]\d)\b", cells[4]))
  return refs


def check_parts(data: dict) -> list[dict]:
  parts = data["parts"]
  refs = [p["ref"] for p in parts]
  if len(set(refs)) != len(refs):
    raise BoxError("a designator is listed twice")
  src = source_designators()
  missing, extra = sorted(src - set(refs)), sorted(set(refs) - src)
  if missing:
    raise BoxError(f"designators in RR-2026-010 HB rows or the BOM but not in the part list: {', '.join(missing)}")
  if extra:
    raise BoxError(f"parts in the list but not in RR-2026-010 HB rows or the BOM: {', '.join(extra)}")
  for p in parts:
    total = sum(m["distribution"] for m in p["modes"])
    if abs(total - 1) > 1e-9:
      raise BoxError(f"{p['ref']}: distributions add up to {total:g}, not 1")
    for m in p["modes"]:
      for g, c in m["goals"].items():
        if g not in GOAL_FILE or c not in CLASSES:
          raise BoxError(f"{p['ref']} {m['mode']!r}: {g} {c} is not a known goal and class")
  return parts


# ---------------------------------------------------------------- roll-up into the goal FMEDAs

def goal_class(row: dict) -> str:
  if row["violates_sg_directly"]:
    return "RF" if row.get("safety_mechanism_spf") and row.get("dc_spf") else "SPF"
  if row["mpf_potential"]:
    return "MPF-L"
  return "safe"


def roll_up(parts: list[dict], goals: dict, known: list[dict]) -> list[dict]:
  """Differences between the part split and the goal rows: [{file, row, what}]."""
  diffs = []
  for gname, fname in GOAL_FILE.items():
    doc = goals[fname]
    mode_of = {m["id"]: (c, m) for c in doc["components"] for m in c["failure_modes"]}
    by_row: dict[str, list] = {}
    for p in parts:
      for m in p["modes"]:
        rid = (m.get("rows") or {}).get(fname)
        if not rid:
          continue
        if rid not in mode_of:
          raise BoxError(f"{p['ref']}: {fname} has no mode {rid}")
        comp, row = mode_of[rid]
        if goal_class(row) != m["goals"][gname]:
          raise BoxError(f"{p['ref']} {m['mode']!r}: {m['goals'][gname]} here, {goal_class(row)} in {fname} {rid}")
        by_row.setdefault(comp["id"], []).append((p, m, rid))
    for cid, hits in sorted(by_row.items()):
      comp = next(c for c in doc["components"] if c["id"] == cid)
      contributors = {p["ref"]: p for p, _, _ in hits}
      if any(p["rate_fit"] is None for p in contributors.values()):
        continue  # a part carried inside a wider row (connectors in the wiring row): no exact sum
      lam = sum(p["rate_fit"] for p in contributors.values())
      if abs(lam - comp["failure_rate_fit"]) > 1e-9:
        diffs.append({"file": fname, "row": cid, "what": f"parts {lam:g} FIT, row {comp['failure_rate_fit']:g} FIT"})
        continue
      bad = []
      for m in comp["failure_modes"]:
        part_l = sum(p["rate_fit"] * pm["distribution"] for p, pm, rid in hits if rid == m["id"])
        if abs(part_l - comp["failure_rate_fit"] * m["distribution"]) > 1e-9:
          bad.append(f"{m['id']} parts {part_l:.2f} FIT, row {comp['failure_rate_fit'] * m['distribution']:.2f} FIT")
      if bad:
        diffs.append({"file": fname, "row": cid, "what": "; ".join(bad)})
  listed = {(k["file"], k["row"]) for k in known}
  found = {(d["file"], d["row"]) for d in diffs}
  if found - listed:
    raise BoxError("parts and goal FMEDA disagree: " + "; ".join(f"{d['file']} {d['row']}: {d['what']}"
                                                                   for d in diffs if (d["file"], d["row"]) not in listed))
  if listed - found:
    raise BoxError(f"known_differences lists {sorted(listed - found)}, which now agree: remove them")
  return diffs


# ---------------------------------------------------------------- outputs

def dc_of(m: dict, fname: str, goals: dict) -> tuple[str, float]:
  """(mechanism, DC) the goal FMEDA credits for this part mode, or ('', 0)."""
  rid = (m.get("rows") or {}).get(fname)
  if not rid:
    return "", 0.0
  row = next(r for c in goals[fname]["components"] for r in c["failure_modes"] if r["id"] == rid)
  if row.get("safety_mechanism_spf"):
    return row["safety_mechanism_spf"], row.get("dc_spf", 0.0)
  if row.get("safety_mechanism_lf"):
    return row["safety_mechanism_lf"], row.get("dc_lf", 0.0)
  return "", 0.0


def categories(parts: list[dict], goals: dict) -> dict:
  """λ per category per goal, over the parts that have their own rate."""
  out = {}
  for g, fname in GOAL_FILE.items():
    cat = {c: 0.0 for c in CLASSES}
    for p in parts:
      if p["rate_fit"] is None:
        continue
      for m in p["modes"]:
        cat[m["goals"][g]] += p["rate_fit"] * m["distribution"]
    out[g] = cat
  return out


def what_if(parts: list[dict], goals: dict) -> list[dict]:
  """Goal metrics now, and with the part-level findings applied in memory."""
  rows = []
  sg001 = copy.deepcopy(goals["fmeda-sg001"])
  now = fmea_lint.fmeda_metrics(goals["fmeda-sg001"])
  # finding 1: the DG419LE split of the SG-009 file and the part list, applied to the SG-001 row
  u1 = next(p for p in parts if p["ref"] == "U1")
  comp = next(c for c in sg001["components"] if c["id"] == "FMD-C-007")
  for pm in u1["modes"]:
    for r in comp["failure_modes"]:
      if r["id"] == pm["rows"]["fmeda-sg001"]:
        r["distribution"] = pm["distribution"]
  aligned = fmea_lint.fmeda_metrics(sg001)
  # finding 2: Q6 drain-source short, latent for SG-01, carried as a new row
  q6 = next(p for p in parts if p["ref"] == "Q6")
  short = next(m for m in q6["modes"] if m["goals"]["SG-01"] == "MPF-L")
  sg001["components"].append({"id": "FMD-C-X", "failure_rate_fit": q6["rate_fit"], "safety_related": True,
                              "failure_modes": [
                                {"id": "X1", "distribution": short["distribution"], "violates_sg_directly": False,
                                 "mpf_potential": True},
                                {"id": "X2", "distribution": 1 - short["distribution"], "violates_sg_directly": False,
                                 "mpf_potential": False}]})
  both = fmea_lint.fmeda_metrics(sg001)
  for label, m in (("SG-01 today (fmeda-sg001)", now), ("with the DG419LE split aligned", aligned),
                   ("and Q6 short carried as a latent row", both)):
    rows.append({"case": label, "spfm": m["spfm"], "lfm": m["lfm"], "total": m["total_fit"]})
  return rows


def build() -> dict:
  data, flow, goals = load()
  parts = check_parts(data)
  diffs = roll_up(parts, goals, data.get("known_differences", []))
  for io in flow["inputs"]:
    for r in io["records"]:
      if not (REPO / r).exists():
        raise BoxError(f"fmeda-flow.yaml: {r} does not exist")
  return {"data": data, "flow": flow, "goals": goals, "parts": parts, "diffs": diffs,
          "cat": categories(parts, goals), "whatif": what_if(parts, goals)}


# ---------------------------------------------------------------- page

def fit(x: float) -> str:
  return f"{x:.2f}".rstrip("0").rstrip(".") if x else "0"


def page(r: dict) -> str:
  parts, cat, goals = r["parts"], r["cat"], r["goals"]
  rated = [p for p in parts if p["rate_fit"] is not None]
  n_modes = sum(len(p["modes"]) for p in parts)
  opens = [(p["ref"], m["mode"]) for p in parts for m in p["modes"] if "open" in m["goals"].values()]
  new = [p["ref"] for p in parts if p["rate_fit"] is not None and not any(m.get("rows") for m in p["modes"])]
  wi = r["whatif"]
  L = ["<!-- GENERATED by harness_box_fmeda.py from harness-box-parts.yaml and fmeda-flow.yaml; do not edit -->", "",
       "# Harness box component FMEDA", "",
       "The detailed component FMEDA of the harness box v3 (E-05), one row per part, as [WP-H-03](../WP-H-03-hardware-safety-analysis-fmeda.md) "
       "§6.5 describes. It is the part-level layer under the two goal FMEDAs ([`fmeda-sg009.yaml`](../../08-analyses/fmea/analyses/fmeda-sg009.yaml), "
       "[`fmeda-sg001.yaml`](../../08-analyses/fmea/analyses/fmeda-sg001.yaml)): the check below proves that the parts add up to their box rows. "
       "The rates are still generic estimates (no SN 29500 held), so these numbers show where the box falls short; they are not evidence of "
       "compliance. Draft, AI-assisted (I0), not reviewed.", "",
       "**The box in five lines.**", "",
       f"1. **{len(parts)} parts, {n_modes} failure modes**, every designator of the v3 drawing and the BOM; {len(rated)} carry their own "
       "rate, the connectors sit inside the wiring row.",
       f"2. **For stock braking (SG-07) the box puts {fit(cat['SG-07']['SPF'])} FIT on single points** out of "
       f"{fit(sum(p['rate_fit'] for p in rated))} FIT, almost all of it the two DG419LE switches.",
       f"3. **For steering (SG-01) the box has no single point:** {fit(cat['SG-01']['RF'])} FIT is covered by a mechanism, "
       f"{fit(cat['SG-01']['MPF-L'])} FIT is latent and {fit(cat['SG-01']['safe'])} FIT is safe.",
       f"4. **The part-level view found what the block view hid:** the goal FMEDAs split the same switch two ways, and "
       f"{', '.join(new)} are in no goal FMEDA. Applied, SG-01's SPFM goes from {wi[0]['spfm'] * 100:.2f} % to "
       f"{wi[2]['spfm'] * 100:.2f} % and its LFM from {wi[0]['lfm'] * 100:.2f} % to {wi[2]['lfm'] * 100:.2f} %.",
       f"5. **No periodic test of the box exists**, so every latent fault stays latent for the box's life; {len(opens)} modes "
       "still need their effect analysed.", "",
       "## The FMEDA flow", "",
       "![The FMEDA flow: six inputs (field data not needed; failure modes and safe state, architecture, diagnostics done; "
       "schematic and BOM partial, the box only; prevention and periodic tests partial), the component FMEDA, and four outputs "
       "(rates per mode and category partial, useful life partial, diagnostic coverage done, periodic-test coverage missing)]"
       f"({OUT_FLOW})", "",
       "*Figure 6-0. The inputs a detailed component FMEDA needs and the outputs it gives, with the records that hold each "
       "here and how far each has got ([`fmeda-flow.yaml`](fmeda-flow.yaml)).*", "",
       "## Output 1: failure rate per mode and category", "",
       f"![Each of the {len(parts)} harness box parts with its failure rate and, per failure mode, its class for SG-07 and SG-01]"
       f"({OUT_PARTS})", "",
       "*Figure 6-5. Every part, its rate and the class of each failure mode for both goals.*", "",
       "| Category | SG-07 stock braking (FIT) | SG-01 steering (FIT) |", "|---|---|---|"]
  names = {"SPF": "Single-point", "RF": "Covered by a mechanism (before DC)", "MPF-L": "Latent multiple-point",
           "safe": "Safe", "none": "No effect on this goal", "open": "Effect not yet analysed"}
  for c in CLASSES:
    L.append(f"| {names[c]} | {fit(cat['SG-07'][c])} | {fit(cat['SG-01'][c])} |")
  L += ["", "| Part | λ (FIT) | Failure mode | Share | SG-07 | SG-01 | Goal FMEDA row |", "|---|---|---|---|---|---|---|"]
  for p in parts:
    for m in p["modes"]:
      rows = ", ".join(f"{k.replace('fmeda-', '')} {v}" for k, v in (m.get("rows") or {}).items()) or "none"
      lam = (fit(p["rate_fit"]) if p["rate_fit"] is not None else
             "in the wiring row" if any((p.get("included_in") or {}).values()) else "no rate")
      L.append(f"| {p['ref']} | {lam} | {m['mode']} | {m['distribution']:.0%} | {m['goals']['SG-07']} | "
               f"{m['goals']['SG-01']} | {rows} |")
  L += ["", "## Output 2: useful life", "", f"Mission: {r['data']['useful_life']['mission']}. The rates assume a constant "
        "failure rate, which holds only while no part reaches wear-out.", "", "| Parts | Wear-out | Limit |", "|---|---|---|"]
  for u in r["data"]["useful_life"]["parts"]:
    L.append(f"| {', '.join(u['refs'])} | {u['wear_out']} | {u['limit']} |")
  L += ["", r["data"]["useful_life"]["absent"] + ".", "",
        "## Output 3: diagnostic coverage per failure mode", "",
        "| Part | Failure mode | Goal | Mechanism | DC |", "|---|---|---|---|---|"]
  for p in parts:
    for m in p["modes"]:
      for g, fname in GOAL_FILE.items():
        sm, dc = dc_of(m, fname, goals)
        if sm:
          L.append(f"| {p['ref']} | {m['mode']} | {g} | {sm} | {dc:.0%} |")
  L += ["", "Every other mode of the box has no mechanism: DC 0 %.", "",
        "## Output 4: coverage of each periodic test", "",
        "In ISO 26262 terms the slide's proof test is the test that finds latent faults.", "",
        "| Test | When | Finds | Coverage in service | Note |", "|---|---|---|---|---|"]
  for t in r["data"]["periodic_tests"]:
    L.append(f"| {t['name']} | {t['when']} | {', '.join(t['finds'])} | {t['coverage_in_service']:.0%} | {t['note']} |")
  L += ["", "## Findings", "", "**Disagreements with the goal FMEDAs** (the check reports them; the list only shrinks):", ""]
  for d in r["diffs"]:
    reason = next(k["reason"] for k in r["data"]["known_differences"] if (k["file"], k["row"]) == (d["file"], d["row"]))
    L.append(f"- {d['file']} {d['row']}: {d['what']}. {reason}")
  L += ["", f"**Parts in no goal FMEDA:** {', '.join(new)}. Their modes are classified above; the Q6 drain-source short is "
        "latent for SG-01 (DFM-014.C2).", "",
        "**What the goal metrics would be with these applied** (computed in memory with fmea_lint; the FMEDA files are not "
        "changed here):", "", "| Case | SPFM | LFM | λ total (FIT) |", "|---|---|---|---|"]
  for w in wi:
    L.append(f"| {w['case']} | {w['spfm'] * 100:.2f} % | {w['lfm'] * 100:.2f} % | {fit(w['total'])} |")
  L += ["", "**Modes whose effect is not yet analysed:**", ""]
  for ref, mode in opens:
    L.append(f"- {ref}: {mode}")
  L += ["", "## Where this comes from", "",
        "| File | What it is |", "|---|---|",
        "| [`harness-box-parts.yaml`](harness-box-parts.yaml) | The parts, rates, modes, classes, useful life and periodic tests |",
        "| [`fmeda-flow.yaml`](fmeda-flow.yaml) | The inputs and outputs of Figure 6-0 with their records and state |",
        "| [`harness_box_fmeda.py`](harness_box_fmeda.py) | Checks the part list against RR-2026-010 and the BOM, rolls the parts up "
        "into the goal FMEDAs, computes the outputs and draws the figures; `--check` in CI |"]
  return "\n".join(L) + "\n"


# ---------------------------------------------------------------- figures

def wrap(s: str, width: float, size: float, bold: bool = False) -> list[str]:
  out, cur = [], ""
  for w in s.split():
    nxt = f"{cur} {w}".strip()
    if cur and text_w(nxt, size, bold) > width:
      out.append(cur)
      cur = w
    else:
      cur = nxt
  return out + ([cur] if cur else [])


def chip(x, y, label, state, styles) -> tuple[list[str], float]:
  col, bg = styles[state]
  w = text_w(label, 9, True) + 12
  return [rect(x, y, w, 15, fill=bg, stroke=col, sw=1.1, rx=7), text(x + w / 2, y + 11, label, size=9, weight=700,
                                                                       fill=col, anchor="middle")], w


def footer(out: list[str], y: float, gen: str) -> float:
  extra, y = terms.svg_footer(out, 16, y, W - 32, size=10)
  out += extra
  out.append(text(W - 16, y + 6, f"Generated by {gen}", size=10, fill=FAINT, anchor="end"))
  return y + 18


def fig_flow(r: dict) -> str:
  flow, parts = r["flow"], r["parts"]
  out = [text(16, 30, "Figure 6-0 · The component FMEDA: inputs and outputs", size=15, weight=700),
         text(16, 48, "What a detailed component FMEDA needs and gives, and where LionDriver stands", size=11, fill=MUTED)]
  y = 70

  def block(items, title, y):
    out.append(text(16, y, title, size=12, weight=700))
    y += 8
    for it in items:
      note = wrap(it["note"], W - 200, 10)
      h = 22 + 13 * len(note)
      col, bg = STATE_STYLE[it["state"]]
      out.append(rect(16, y, W - 32, h, fill="#FFFFFF", stroke=LINE, sw=1.1, rx=8))
      out.append(text(28, y + 16, it["name"], size=11.5, weight=700))
      for j, ln in enumerate(note):
        out.append(text(28, y + 30 + 13 * j, ln, size=10, fill=MUTED))
      c, w = chip(W - 28 - text_w(it["state"], 9, True) - 12, y + 6, it["state"], it["state"], STATE_STYLE)
      out.extend(c)
      y += h + 6
    return y

  y = block(flow["inputs"], "Inputs", y)
  y += 4
  out.append(path(f"M{W / 2} {y} L{W / 2} {y + 12}", stroke=FAINT, sw=1.6))
  y += 16
  n_modes = sum(len(p["modes"]) for p in parts)
  out.append(rect(16, y, W - 32, 52, fill="#FEF3C7", stroke=AMBER, sw=1.6, rx=10))
  out.append(text(W / 2, y + 21, "Detailed component FMEDA", size=13, weight=700, anchor="middle"))
  out.append(text(W / 2, y + 39, f"Harness box: {len(parts)} parts, {n_modes} modes, part by part · comma device: "
                  "block level only", size=10.5, fill=INK, anchor="middle"))
  y += 52
  out.append(path(f"M{W / 2} {y + 4} L{W / 2} {y + 16}", stroke=FAINT, sw=1.6))
  y += 30
  y = block(flow["outputs"], "Outputs", y)
  y = footer(out, y + 14, "harness_box_fmeda.py from fmeda-flow.yaml")
  desc = ("Inputs: " + "; ".join(f"{i['name']} ({i['state']})" for i in flow["inputs"]) + ". Outputs: " +
          "; ".join(f"{o['name']} ({o['state']})" for o in flow["outputs"]) + ".")
  return svg(W, int(y), "Figure 6-0. The component FMEDA: inputs and outputs", desc, out)


def fig_parts(r: dict) -> str:
  parts = r["parts"]
  out = [text(16, 30, "Figure 6-5 · Harness box parts, mode by mode", size=15, weight=700),
         text(16, 48, "Each part's rate and, per failure mode, its class for SG-07 and SG-01", size=11, fill=MUTED)]
  y = 64
  x = 16
  for c in CLASSES:
    cc, w = chip(x, y, c, c, CLASS_STYLE)
    out.extend(cc)
    x += w + 6
  y += 30
  for p in parts:
    lam = (f"{fit(p['rate_fit'])} FIT" if p["rate_fit"] is not None else
           "in wiring row" if any((p.get("included_in") or {}).values()) else "no rate")
    out.append(text(16, y + 12, p["ref"], size=12, weight=700))
    out.append(text(52, y + 12, lam, size=10, fill=MUTED))
    for k, g in enumerate(GOAL_FILE):
      xx = 140
      out.append(text(xx, y + 12 + 20 * k, g, size=9.5, weight=700, fill=MUTED))
      xx += 40
      for m in p["modes"]:
        lab = f"{m['goals'][g]} {m['distribution']:.0%}"
        cc, w = chip(xx, y + 1 + 20 * k, lab, m["goals"][g], CLASS_STYLE)
        out.extend(cc)
        xx += w + 4
    y += 46
    out.append(path(f"M16 {y - 4} L{W - 16} {y - 4}", stroke="#E2E8F0", sw=1))
  y += 8
  for ln in wrap("Percentages are the share of the part's rate in that mode. Connectors J1 and J3 are carried inside the "
                 "goal FMEDA's wiring row; J2 has no rate until its use is known.", W - 32, 10):
    out.append(text(16, y, ln, size=10, fill=MUTED))
    y += 13
  y = footer(out, y + 10, "harness_box_fmeda.py from harness-box-parts.yaml")
  desc = "; ".join(f"{p['ref']} " + ", ".join(f"{m['mode']}: SG-07 {m['goals']['SG-07']}, SG-01 {m['goals']['SG-01']}"
                                              for m in p["modes"]) for p in parts)
  return svg(W, int(y), "Figure 6-5. Harness box parts, mode by mode", desc, out)


# ---------------------------------------------------------------- workbook (the FMEDA spreadsheet layout)

def lf_dc(m: dict, fname: str, goals: dict) -> float:
  rid = (m.get("rows") or {}).get(fname)
  if not rid:
    return 0.0
  row = next(r for c in goals[fname]["components"] for r in c["failure_modes"] if r["id"] == rid)
  return row.get("dc_lf", 0.0) if row.get("safety_mechanism_lf") else 0.0


def workbook(r: dict):
  from openpyxl import Workbook
  from openpyxl.styles import Font, PatternFill
  wb = Workbook()
  wb.properties.creator = "assurance/04-hardware/fmeda/harness_box_fmeda.py"
  wb.properties.title = "Harness box v3 component FMEDA"
  wb.properties.created = wb.properties.modified = STAMP
  bold, head = Font(bold=True), PatternFill("solid", fgColor="FEF3C7")
  cols = ["Part designator", "Part type", "Quan.", "Failure mode", "Effect (S, D, L, #, ?)", "Lambda (FIT)",
          "Diagnostic coverage", "SD", "SU", "DD", "DU", "LD", "LU", "#", "?"]
  first = True
  for g, fname in GOAL_FILE.items():
    ws = wb.active if first else wb.create_sheet()
    first = False
    ws.title = f"{g} FMEDA"
    rows, tot = [], [0.0] * 8
    for p in r["parts"]:
      for k, m in enumerate(p["modes"]):
        cls = m["goals"][g]
        lam = None if p["rate_fit"] is None else round(p["rate_fit"] * m["distribution"], 6)
        sm, dc = dc_of(m, fname, r["goals"])
        dc = dc if cls == "RF" else lf_dc(m, fname, r["goals"]) if cls == "MPF-L" else 0.0
        split = [None] * 8
        if lam is not None:
          split = [0.0] * 8
          if cls == "safe":
            split[1] = lam
          elif cls in ("SPF", "RF"):
            split[2], split[3] = round(lam * dc, 6), round(lam * (1 - dc), 6)
          elif cls == "MPF-L":
            split[4], split[5] = round(lam * dc, 6), round(lam * (1 - dc), 6)
          elif cls == "none":
            split[6] = lam
          else:
            split[7] = lam
          tot = [a + b for a, b in zip(tot, split)]
        rows.append([p["ref"] if k == 0 else None, p["part"] if k == 0 else None, 1 if k == 0 else None, m["mode"],
                     EFFECT[cls], lam if lam is not None else "in FMD-C-008" if any((p.get("included_in") or {}).values())
                     else "no rate", dc, *split])
    ws.append([f"Harness box v3 component FMEDA, {g} {GOAL_TITLE[g]}", None, None, STAMP.date().isoformat(), "Done by:",
               "Claude (AI-assisted, I0)", "Reviewed by:", None, "Rates:", "generic estimates; SN 29500 class per part"])
    ws.append(["Project:", "LionDriver reference configuration, harness box v3 (E-05)", None, None, None,
               round(sum(x for x in (row[5] for row in rows) if isinstance(x, float)), 6), None,
               *[round(t, 6) for t in tot]])
    ws.append(cols)
    for row in rows:
      ws.append(row)
    for c in ws[3]:
      c.font, c.fill = bold, head
    ws["A2"].font = bold
    for col, wdt in zip("ABCDEFGHIJKLMNO", (10, 46, 6, 46, 10, 11, 11, 8, 8, 8, 8, 8, 8, 8, 8)):
      ws.column_dimensions[col].width = wdt
  ws = wb.create_sheet("Notes")
  for row in [
      ["Column", "Meaning"],
      ["Effect", "S safe; D dangerous for this goal (ISO 26262 single-point or residual); L latent multiple-point; "
       "# no effect on this goal; ? effect not yet analysed"],
      ["Lambda", "Failure rate of this mode in FIT: the part's rate times the mode's share. Connectors J1 and J3 are carried "
       "inside the goal FMEDA's wiring row FMD-C-008"],
      ["Diagnostic coverage", "The DC the goal FMEDA credits for this mode (dangerous: against single-point; latent: "
       "against latent faults); 0 where no mechanism covers it"],
      ["SD, SU", "Safe detected, safe undetected (no detection of safe faults is credited, so all is SU)"],
      ["DD, DU", "Dangerous detected (Lambda × DC), dangerous undetected (Lambda × (1 − DC))"],
      ["LD, LU", "Latent detected and undetected: ISO 26262's multiple-point faults, in place of the IEC 61508 "
       "annunciation columns AD and AU"],
      ["#, ?", "No effect on this goal; effect not yet analysed"],
      ["Row 2", "Totals of each column"],
      ["Reviewed by", "Left empty for the independent reviewer (WP-P-05); this workbook is AI-assisted, I0, not reviewed"],
      ["Source", "harness-box-parts.yaml, generated by harness_box_fmeda.py; edit the YAML, never this file"]]:
    ws.append(row)
  ws["A1"].font = ws["B1"].font = bold
  ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 20, 110
  return wb


def cell_values(wb) -> dict:
  return {ws.title: [[c.value for c in row] for row in ws.iter_rows()] for ws in wb.worksheets}


def outputs() -> dict[str, str]:
  r = build()
  return {OUT_MD: page(r), OUT_FLOW: fig_flow(r), OUT_PARTS: fig_parts(r), OUT_XLSX: workbook(r)}


def main(argv: list[str]) -> int:
  try:
    outs = outputs()
  except (BoxError, FigureError) as e:
    print(f"harness_box_fmeda: {e}", file=sys.stderr)
    return 1
  stale = []
  from openpyxl import load_workbook
  for name, content in outs.items():
    p = HERE / name
    if name.endswith(".xlsx"):
      if "--check" in argv:
        if not p.exists() or cell_values(load_workbook(p)) != cell_values(content):
          stale.append(name)
      else:
        buf = io.BytesIO()
        content.save(buf)
        p.write_bytes(buf.getvalue())
      continue
    if "--check" in argv:
      if not p.exists() or p.read_text(encoding="utf-8") != content:
        stale.append(name)
    else:
      p.write_text(content, encoding="utf-8")
  if stale:
    print(f"harness_box_fmeda: stale {', '.join(stale)}; run python3 {Path(__file__).name}", file=sys.stderr)
    return 1
  print("harness_box_fmeda: " + ("up to date" if "--check" in argv else f"wrote {', '.join(outs)}"))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
