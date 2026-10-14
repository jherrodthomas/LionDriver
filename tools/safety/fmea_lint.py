#!/usr/bin/env python3
"""Validate LionDriver FMEA / FMEDA files against the schemas and rating rules.

Usage: tools/safety/fmea_lint.py [--root REPO_ROOT] [--report]

Requires PyYAML and jsonschema (not openpilot runtime deps):
  pip install pyyaml jsonschema

Rules are documented in assurance/08-analyses/fmea/rating-tables.md.
"""
import argparse
import configparser
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
SAFETY_DIR = Path("assurance/08-analyses/fmea")
FMEA_TYPES = ("system_fmea", "dfmea", "sw_fmea", "pfmea")

# AIAG-VDA 2019 Action Priority. Rows: (severity band, occurrence band) -> AP for D bands (7-10, 5-6, 2-4, 1).
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

# FMEA-MSR (rating-tables.md section 7). PROVISIONAL: the AIAG-VDA MSR action priority table is not transcribed yet
# (the handbook is not in the repository). Until it is, the table above is applied with frequency in place of occurrence
# and monitoring in place of detection, and every MSR rating is provisional (rating-tables.md section 7.4).
F_BANDS = O_BANDS
M_BANDS = D_BANDS
AP_MSR_TABLE = AP_TABLE
AP_MSR_PROVISIONAL = True
MSR_TYPES = ("system_fmea", "dfmea")  # msr-plan.md section 3
WP_S04 = Path("assurance/03-system/WP-S-04-timing-ftti-budget.md")

# ISO 26262-3 Table 4: for S1-S3, E1-E4, C1-C3 the ASIL depends only on S+E+C.
ASIL_BY_SUM = {10: "D", 9: "C", 8: "B", 7: "A"}
ASIL_ORDER = ("QM", "A", "B", "C", "D")

FMEDA_TARGETS = {  # ASIL: (SPFM, LFM, PMHF FIT)
  "B": (0.90, 0.60, 100.0),
  "C": (0.97, 0.80, 100.0),
  "D": (0.99, 0.90, 10.0),
}


def _band(value, bands):
  return next(i for i, (lo, hi) in enumerate(bands) if lo <= value <= hi)


def compute_ap(s: int, o: int, d: int) -> str:
  for v in (s, o, d):
    if not 1 <= v <= 10:
      raise ValueError(f"rating out of range: {v}")
  return AP_TABLE[S_BANDS[_band(s, S_BANDS)]][_band(o, O_BANDS)][_band(d, D_BANDS)]


def compute_ap_msr(s: int, s_after: int, f: int, m: int) -> str:
  """MSR action priority. With monitoring 1 (diagnosis and response always effective) the severity after the system
  response is rated instead of the original severity (AIAG-VDA MSR logic)."""
  for v in (s, s_after, f, m):
    if not 1 <= v <= 10:
      raise ValueError(f"rating out of range: {v}")
  rated = s_after if m == 1 else s
  return AP_MSR_TABLE[S_BANDS[_band(rated, S_BANDS)]][_band(f, F_BANDS)][_band(m, M_BANDS)]


def parse_ftti_rows(text: str) -> dict[str, float | None]:
  """WP-S-04 section 3.7: row label -> FTTI in ms (None when the FTTI is not a time, e.g. 'per frame')."""
  section = text.split("### 3.7", 1)[1].split("\n## ", 1)[0] if "### 3.7" in text else ""
  rows = {}
  for line in section.splitlines():
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 2 or not cells[0] or cells[0] == "SG / fault class" or set(cells[0]) <= set("-: "):
      continue
    m = re.match(r"([0-9]+(?:\.[0-9]+)?)\s*(ms|s)\b", cells[1])
    rows[cells[0]] = (float(m.group(1)) * (1 if m.group(2) == "ms" else 1000)) if m else None
  return rows


def compute_asil(s: str, e: str, c: str) -> str:
  """ASIL from 'S0'-'S3', 'E0'-'E4', 'C0'-'C3' per ISO 26262-3 Table 4."""
  si, ei, ci = int(s[1]), int(e[1]), int(c[1])
  if not (0 <= si <= 3 and 0 <= ei <= 4 and 0 <= ci <= 3):
    raise ValueError(f"invalid S/E/C: {s} {e} {c}")
  if 0 in (si, ei, ci):
    return "QM"
  return ASIL_BY_SUM.get(si + ei + ci, "QM")


def max_asil(asils) -> str:
  return max(asils, key=ASIL_ORDER.index, default="QM")


@dataclass
class Result:
  errors: list = field(default_factory=list)
  warnings: list = field(default_factory=list)
  report: list = field(default_factory=list)

  def error(self, where, msg):
    self.errors.append(f"ERROR   {where}: {msg}")

  def warn(self, where, msg):
    self.warnings.append(f"WARNING {where}: {msg}")


def rating_tables_version(root: Path) -> str | None:
  text = (root / SAFETY_DIR / "rating-tables.md").read_text()
  m = re.search(r"\*\*Version:\*\*\s*(RT-\d+)", text)
  return m.group(1) if m else None


def sod_unchanged_since(root: Path) -> str | None:
  """Oldest rating-tables version whose S/O/D and AP tables equal the current ones; a file rated against it needs no
  re-rating unless it uses tables added later (FMEA-MSR from RT-2)."""
  text = (root / SAFETY_DIR / "rating-tables.md").read_text()
  m = re.search(r"\*\*S/O/D unchanged since:\*\*\s*(RT-\d+)", text)
  return m.group(1) if m else None


def empty_submodules(root: Path) -> list[str]:
  gm = root / ".gitmodules"
  if not gm.exists():
    return []
  cp = configparser.ConfigParser()
  cp.read(gm)
  paths = [cp[s]["path"] for s in cp.sections() if "path" in cp[s]]
  return [p for p in paths if not (root / p).is_dir() or not any((root / p).iterdir())]


class _Loader(yaml.SafeLoader):
  """SafeLoader that keeps dates as strings, matching the schema's `format: date` strings."""


_Loader.yaml_implicit_resolvers = {
  k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"] for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(text: str):
  return yaml.load(text, Loader=_Loader)


def load_schema(root: Path, name: str) -> dict:
  return json.loads((root / SAFETY_DIR / "schema" / name).read_text())


def schema_errors(data, schema, where, res: Result):
  validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
  for e in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
    loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
    res.error(where, f"schema: {loc}: {e.message}")


def check_fmea(name, doc, ctx, res: Result):
  prefix = doc["analysis"]["id"]
  status = doc["analysis"]["status"]
  elements = {e["id"]: e for e in doc["structure"]}
  functions = {f["id"]: f for f in doc["functions"]}
  actions = {a["id"]: a for a in doc["actions"]}
  referenced_actions = set()

  def own(id_, where):
    if not id_.startswith(prefix + "-"):
      res.error(where, f"{id_} does not use this file's prefix {prefix}")

  for e in doc["structure"]:
    own(e["id"], name)
    if e.get("parent") and e["parent"] not in elements:
      res.error(f"{name} {e['id']}", f"parent {e['parent']} not found")
    for p in e.get("paths", []):
      ctx.check_path(p, f"{name} {e['id']}", res)
  for f in doc["functions"]:
    own(f["id"], name)
    if f["element"] not in elements:
      res.error(f"{name} {f['id']}", f"element {f['element']} not found")
  for a in doc["actions"]:
    own(a["id"], name)

  for fm in doc["failure_modes"]:
    where = f"{name} {fm['id']}"
    own(fm["id"], name)
    if fm["element"] not in elements:
      res.error(where, f"element {fm['element']} not found")
    if fm["function"] not in functions:
      res.error(where, f"function {fm['function']} not found")

    effect_sev = [e["severity"] for e in fm["effects"] if e.get("severity") is not None]
    for e in fm["effects"]:
      if e.get("hazard") and ctx.hazards is not None and e["hazard"] not in ctx.hazards:
        res.error(where, f"effect hazard {e['hazard']} not found in the HARA")
      if e.get("hazard") and e.get("severity") not in (None, 10):
        res.error(where, f"effect linked to {e['hazard']} must have severity 10 (rating-tables 1.1), got {e['severity']}")
    s = fm["severity"]
    if effect_sev and s is not None and s != max(effect_sev):
      res.error(where, f"severity {s} != max effect severity {max(effect_sev)}")

    for c in fm["causes"]:
      cwhere = f"{name} {c['id']}"
      if not c["id"].startswith(fm["id"] + ".C"):
        res.error(cwhere, f"cause id must be {fm['id']}.C<n>")
      if c.get("element") and c["element"] not in elements:
        res.error(cwhere, f"element {c['element']} not found")
      if c.get("linked_failure_mode") and c["linked_failure_mode"] not in ctx.failure_modes:
        res.error(cwhere, f"linked_failure_mode {c['linked_failure_mode']} not found in any analysis")
      for ctl in c["prevention_controls"] + c["detection_controls"]:
        if ctl.get("test"):
          ctx.check_path(ctl["test"], cwhere, res)
      if c["detection"] is not None and c["detection"] <= 8:
        if doc["analysis"]["type"] == "pfmea":
          # process detection is often an inspection or checklist step: its evidence is the procedure (ref), not a test file
          if not any(ctl.get("test") or ctl.get("ref") for ctl in c["detection_controls"]):
            res.error(cwhere, f"detection {c['detection']} claims a detection control; it must name a `test` path or a `ref`")
        elif not any(ctl.get("test") for ctl in c["detection_controls"]):
          res.error(cwhere, f"detection {c['detection']} claims a targeted test; a detection control must name a `test` path")
      for a in c.get("actions", []):
        referenced_actions.add(a)
        if a not in actions:
          res.error(cwhere, f"action {a} not found")
      check_msr_cause(doc, fm, c, cwhere, actions, referenced_actions, ctx, res)

      o, d, ap = c["occurrence"], c["detection"], c["ap"]
      if None in (s, o, d):
        if ap is not None:
          res.error(cwhere, "ap set but severity/occurrence/detection incomplete")
        if status == "released":
          res.error(cwhere, "released analysis requires severity, occurrence and detection")
        continue
      expected = compute_ap(s, o, d)
      if ap != expected:
        res.error(cwhere, f"ap is {ap}, table gives {expected} for S{s} O{o} D{d}")
      ctx.ap_counts[expected] += 1
      if expected == "H" and not c.get("actions") and not c.get("rationale"):
        res.error(cwhere, "AP=H requires an action or a rationale")
      elif expected == "M" and not c.get("actions") and not c.get("rationale"):
        res.warn(cwhere, "AP=M: action or rationale recommended")

  for a in actions:
    if a not in referenced_actions:
      res.warn(f"{name} {a}", "action not referenced by any cause")


def msr_in_scope(kind: str, fm: dict) -> bool:
  """msr-plan.md section 3: System FMEA and DFMEA causes of a failure mode with S >= 9 that lists an in-field mechanism."""
  return kind in MSR_TYPES and (fm.get("severity") or 0) >= 9 and bool(fm.get("safety_mechanisms"))


def check_msr_cause(doc, fm, c, cwhere, actions, referenced_actions, ctx, res: Result):
  kind = doc["analysis"]["type"]
  status = doc["analysis"]["status"]
  in_scope = msr_in_scope(kind, fm)
  msr = c.get("msr")
  if in_scope:
    ctx.msr_counts["in_scope"] += 1
    if c.get("msr_exempt"):
      ctx.msr_counts["exempt"] += 1
    elif not msr and doc["analysis"].get("msr") == "complete":
      res.error(cwhere, "analysis declares msr: complete; this in-scope cause needs an msr row or msr_exempt")
  if not msr:
    return
  if kind not in MSR_TYPES:
    res.error(cwhere, f"msr rows belong in the System FMEA or DFMEA, not {kind} (msr-plan.md section 3)")
    return

  mechs = fm.get("safety_mechanisms") or []
  for i in msr["mechanisms"]:
    if i > len(mechs):
      res.error(cwhere, f"msr mechanism {i} not in the failure mode's safety_mechanisms (it lists {len(mechs)})")
    elif not (mechs[i - 1].get("ref") or mechs[i - 1].get("test")):
      res.error(cwhere, f"msr mechanism {i} has no ref or test; an uncited mechanism cannot be rated")

  s, sa, f, m, ap = fm["severity"], msr["severity_after"], msr["frequency"], msr["monitoring"], msr["ap"]
  if s is not None and sa is not None and sa > s:
    res.error(cwhere, f"msr severity_after {sa} exceeds the failure mode severity {s}")

  t = msr["timing"]
  ftti_row = None
  if t.get("ftti_ref"):
    if ctx.ftti_rows is None:
      res.error(cwhere, f"msr timing cites {t['ftti_ref']!r} but {WP_S04.as_posix()} was not found")
    elif t["ftti_ref"] not in ctx.ftti_rows:
      res.error(cwhere, f"msr ftti_ref {t['ftti_ref']!r} is not a row of WP-S-04 section 3.7")
    else:
      ftti_row = ctx.ftti_rows[t["ftti_ref"]]
      per_frame = ftti_row is None  # e.g. "per frame": the check acts on every frame before it is sent
      if per_frame and t.get("ftti_ms") is not None:
        res.error(cwhere, f"WP-S-04 row {t['ftti_ref']!r} has no FTTI in time units; omit ftti_ms and give fdti_ms 0")
      elif not per_frame and t.get("ftti_ms") is not None and t["ftti_ms"] != ftti_row:
        res.error(cwhere, f"msr ftti_ms {t['ftti_ms']} != {ftti_row:g} ms in WP-S-04 row {t['ftti_ref']!r}")

  if m is not None:
    tests = [e for e in msr.get("evidence", []) if e.get("test")]
    for e in tests:
      ctx.check_path(e["test"], cwhere, res)
    if t["basis"] == "unknown" and m < 7:
      res.error(cwhere, f"monitoring {m} with timing basis unknown; unknown timing rates M 7 or worse (rating-tables 7.3)")
    per_frame = t.get("ftti_ref") in (ctx.ftti_rows or {}) and ctx.ftti_rows[t["ftti_ref"]] is None
    if m <= 6 and per_frame:
      if t.get("fdti_ms") != 0 or t.get("frti_ms") is None:
        res.error(cwhere, f"monitoring {m} on a per-frame WP-S-04 row needs fdti_ms 0 and frti_ms (rating-tables 7.3)")
      if not tests:
        res.error(cwhere, f"monitoring {m} needs an evidence entry with a `test` path for the diagnostic (rating-tables 7.3)")
    elif m <= 6:
      missing = [k for k in ("ftti_ref", "ftti_ms", "fdti_ms", "frti_ms") if t.get(k) is None]
      if missing:
        res.error(cwhere, f"monitoring {m} needs timing {', '.join(missing)} (rating-tables 7.3)")
      elif t["fdti_ms"] + t["frti_ms"] > t["ftti_ms"]:
        res.error(cwhere, f"monitoring {m} but FDTI {t['fdti_ms']:g} + FRTI {t['frti_ms']:g} ms exceeds the FTTI {t['ftti_ms']:g} ms")
      if not tests:
        res.error(cwhere, f"monitoring {m} needs an evidence entry with a `test` path for the diagnostic (rating-tables 7.3)")
    if m <= 4:
      if t["basis"] != "measured":
        res.error(cwhere, f"monitoring {m} needs measured timing; basis is {t['basis']} (rating-tables 7.3)")
      if not any(e.get("ref") for e in msr.get("evidence", [])):
        res.error(cwhere, f"monitoring {m} needs an evidence `ref` to the timing measurement (rating-tables 7.3)")
      if kind == "dfmea":
        dc = ctx.fmeda_dc.get(msr["fmeda"]) if msr.get("fmeda") else None
        if dc is None or dc < 0.9:
          res.warn(cwhere, f"monitoring {m} on a hardware cause is not backed by an FMEDA failure mode with DC >= 90 %"
                   + (f" ({msr['fmeda']}: {dc})" if msr.get("fmeda") else " (no msr.fmeda link)"))
  if msr.get("fmeda") and msr["fmeda"] not in ctx.fmeda_dc:
    res.error(cwhere, f"msr fmeda {msr['fmeda']} not found")

  for a in msr.get("actions", []):
    referenced_actions.add(a)
    if a not in actions:
      res.error(cwhere, f"msr action {a} not found")

  if None in (s, sa, f, m):
    if ap is not None:
      res.error(cwhere, "msr ap set but severity/severity_after/frequency/monitoring incomplete")
    if status == "released":
      res.error(cwhere, "released analysis requires complete msr ratings")
    return
  expected = compute_ap_msr(s, sa, f, m)
  if ap != expected:
    res.error(cwhere, f"msr ap is {ap}, table gives {expected} for S{s} (after response S{sa}) F{f} M{m}")
  ctx.msr_counts[expected] += 1
  if expected == "H" and not msr.get("actions") and not msr.get("rationale"):
    res.error(cwhere, "MSR AP=H requires an msr action or rationale")
  elif expected == "M" and not msr.get("actions") and not msr.get("rationale"):
    res.warn(cwhere, "MSR AP=M: action or rationale recommended")


def fmeda_metrics(doc):
  total = spf = rf = mpf_latent = 0.0
  for comp in doc["components"]:
    lam = comp["failure_rate_fit"]
    if not comp["safety_related"]:
      continue
    if lam is None:
      return None
    total += lam
    for fm in comp["failure_modes"]:
      l_fm = lam * fm["distribution"]
      if fm["violates_sg_directly"]:
        dc = fm.get("dc_spf", 0.0) if fm.get("safety_mechanism_spf") else 0.0
        if dc == 0.0:
          spf += l_fm
        else:
          rf += l_fm * (1 - dc)
      elif fm["mpf_potential"]:
        dc_lf = fm.get("dc_lf", 0.0) if fm.get("safety_mechanism_lf") else 0.0
        mpf_latent += l_fm * (1 - dc_lf)
  if total == 0:
    return None
  spfm = 1 - (spf + rf) / total
  remaining = total - spf - rf
  lfm = 1 - mpf_latent / remaining if remaining > 0 else 1.0
  return {"total_fit": total, "spf_fit": spf, "rf_fit": rf, "mpf_latent_fit": mpf_latent,
          "spfm": spfm, "lfm": lfm, "pmhf_spf_rf_fit": spf + rf}


def check_fmeda(name, doc, ctx, res: Result):
  mechanisms = {m["id"] for m in doc["safety_mechanisms"]}
  for comp in doc["components"]:
    where = f"{name} {comp['id']}"
    if comp.get("dfmea_element") and comp["dfmea_element"] not in ctx.elements:
      res.error(where, f"dfmea_element {comp['dfmea_element']} not found")
    total = sum(fm["distribution"] for fm in comp["failure_modes"])
    if comp["safety_related"] and abs(total - 1.0) > 1e-6:
      res.error(where, f"failure mode distribution sums to {total:.4f}, expected 1.0")
    for fm in comp["failure_modes"]:
      fwhere = f"{name} {fm['id']}"
      for key, dc in (("safety_mechanism_spf", "dc_spf"), ("safety_mechanism_lf", "dc_lf")):
        if fm.get(key):
          if fm[key] not in mechanisms:
            res.error(fwhere, f"{key} {fm[key]} not found")
          if dc not in fm:
            res.error(fwhere, f"{key} set without {dc}")
      if fm.get("dfmea_ref") and fm["dfmea_ref"] not in ctx.failure_modes:
        res.error(fwhere, f"dfmea_ref {fm['dfmea_ref']} not found")

  m = fmeda_metrics(doc)
  asil = doc["analysis"]["asil_target"]
  if m is None:
    res.report.append(f"{name}: metrics not computable (no safety-related components or missing failure rates)")
    return
  res.report.append(f"{name}: λ={m['total_fit']:.3f} FIT  SPFM={m['spfm']:.2%}  LFM={m['lfm']:.2%}  "
                    + f"λSPF+λRF={m['pmhf_spf_rf_fit']:.3f} FIT (dual-point PMHF term not included)")
  if asil:
    spfm_t, lfm_t, pmhf_t = FMEDA_TARGETS[asil]
    misses = []
    if m["spfm"] < spfm_t:
      misses.append(f"SPFM {m['spfm']:.2%} < {spfm_t:.0%}")
    if m["lfm"] < lfm_t:
      misses.append(f"LFM {m['lfm']:.2%} < {lfm_t:.0%}")
    if m["pmhf_spf_rf_fit"] >= pmhf_t:
      misses.append(f"λSPF+λRF {m['pmhf_spf_rf_fit']:.3f} FIT >= {pmhf_t} FIT")
    for miss in misses:
      (res.error if doc["analysis"]["status"] == "released" else res.warn)(name, f"ASIL {asil} target missed: {miss}")


def check_hara(name, doc, ctx, res: Result):
  status = doc["analysis"]["status"]
  situations = {s["id"]: s for s in doc["operational_situations"]}
  hazards = {h["id"]: h for h in doc["hazards"]}
  local_ids = set(situations) | set(hazards) | {x["id"] for k in ("assumptions", "hazardous_events", "safety_goals") for x in doc[k]}

  hazard_asils: dict[str, list[str]] = {h: [] for h in hazards}
  asil_counts = dict.fromkeys(ASIL_ORDER, 0)
  for he in doc["hazardous_events"]:
    where = f"{name} {he['id']}"
    if he["hazard"] not in hazards:
      res.error(where, f"hazard {he['hazard']} not found")
      continue
    if he["situation"] not in situations:
      res.error(where, f"situation {he['situation']} not found")
      continue
    override = he["exposure_override"]
    e = override["exposure"] if override else situations[he["situation"]]["exposure"]
    expected = compute_asil(he["severity"], e, he["controllability"])
    if he["asil"] != expected:
      res.error(where, f"asil is {he['asil']}, ISO 26262-3 Table 4 gives {expected} for {he['severity']} {e} {he['controllability']}")
    hazard_asils[he["hazard"]].append(expected)
    asil_counts[expected] += 1

  for hid, h in hazards.items():
    where = f"{name} {hid}"
    if not hazard_asils[hid]:
      res.warn(where, "hazard has no hazardous event")
    for f in h["functions"]:
      if f not in ctx.functions:
        res.error(where, f"function {f} not found in the System FMEA")
    for ref in h["sfm_refs"]:
      if ref not in ctx.failure_modes:
        res.error(where, f"sfm_ref {ref} not found")
      elif hid not in ctx.fm_hazards.get(ref, set()):
        res.error(where, f"{ref} has no effect linked to {hid}")
  for fm, hzs in ctx.fm_hazards.items():
    for hid in hzs:
      if hid in hazards and fm not in hazards[hid]["sfm_refs"]:
        res.error(f"{name} {hid}", f"{fm} links an effect to {hid} but is not in its sfm_refs")

  covered = set()
  for sg in doc["safety_goals"]:
    where = f"{name} {sg['id']}"
    missing = [h for h in sg["hazards"] if h not in hazards]
    for h in missing:
      res.error(where, f"hazard {h} not found")
    covered.update(sg["hazards"])
    expected = max_asil(a for h in sg["hazards"] if h not in missing for a in hazard_asils[h])
    if sg["asil"] != expected:
      res.error(where, f"asil is {sg['asil']}, highest hazardous event of its hazards is {expected}")
    if status == "released" and sg["ftti_ms"] is None:
      res.error(where, "released HARA requires an FTTI for every safety goal")
    res.report.append(f"{sg['id']} ASIL {sg['asil']}: {sg['statement']}")

  for hid, asils in hazard_asils.items():
    if max_asil(asils) != "QM" and hid not in covered:
      res.error(f"{name} {hid}", f"ASIL {max_asil(asils)} hazard not covered by any safety goal")
  for oi in doc["open_items"]:
    for ref in oi["affects"]:
      if ref not in local_ids:
        res.error(f"{name} {oi['id']}", f"affects {ref}, which is not in the HARA")
    if oi["status"] == "closed" and not oi.get("resolution"):
      res.error(f"{name} {oi['id']}", "closed open item needs a resolution")
  open_ois = [oi["id"] for oi in doc["open_items"] if oi["status"] == "open"]
  if status == "released" and open_ois:
    res.error(name, f"released HARA has open items: {', '.join(open_ois)}")

  check_guidewords(name, doc, hazards, ctx, res)
  check_coverage(name, doc, hazards, situations, ctx, res)
  res.report.insert(0, "hazardous events by ASIL: " + " ".join(f"{k}={v}" for k, v in asil_counts.items()))


GUIDEWORDS = [f"M{i:02d}" for i in range(1, 15)]

# ISO 26262-9 Table 1: permitted decompositions, as sorted pairs of resulting ASILs.
DECOMPOSITION_SCHEMES = {
  "D": {("D", "QM"), ("C", "A"), ("B", "B")},
  "C": {("C", "QM"), ("B", "A")},
  "B": {("B", "QM"), ("A", "A")},
  "A": {("A", "QM")},
}


def parse_asil(s: str) -> tuple[str, str | None]:
  """'B(D)' -> ('B', 'D'); 'C' -> ('C', None)."""
  if "(" in s:
    base, orig = s[:-1].split("(")
    return base, orig
  return s, None


def check_fsc(name, doc, ctx, res: Result):
  status = doc["analysis"]["status"]
  if ctx.hara_revision is None:
    res.error(name, "FSC requires a HARA")
    return
  if doc["analysis"]["hara_revision"] != ctx.hara_revision:
    res.error(name, f"derived from HARA rev {doc['analysis']['hara_revision']}, current HARA is rev {ctx.hara_revision}; update the FSC")
  elements = {e["id"]: e for e in doc["elements"]}
  fsrs = {f["id"]: f for f in doc["fsrs"]}
  warnings = {w["id"] for w in doc["warning_degradation"]}
  local_ids = set(elements) | set(fsrs) | {x["id"] for x in doc["external_measures"]} | set(ctx.safety_goals)
  foi_ids = {o["id"] for o in doc["open_items"]}

  for e in doc["elements"]:
    where = f"{name} {e['id']}"
    for ref in e.get("inputs", []) + e.get("outputs", []):
      if ref not in elements:
        res.error(where, f"connected element {ref} not found")
    for ref in e["sfm_elements"]:
      if ref not in ctx.elements:
        res.error(where, f"System FMEA element {ref} not found")
    for path in e.get("paths", []):
      ctx.check_path(path, where, res)
    if e["type"] == "external" and e["capability_status"] != "not_applicable":
      res.error(where, "external elements carry no capability claim (capability_status: not_applicable)")
  for xm in doc["external_measures"]:
    oi = xm.get("open_item")
    if oi and oi not in foi_ids and oi not in ctx.hara_open_items:
      res.error(f"{name} {xm['id']}", f"open item {oi} not found in FSC or HARA")
    if xm["credited"] and oi:
      res.warn(f"{name} {xm['id']}", f"credited while open item {oi} is open")

  timing = {}
  for tm in doc["timing"]:
    where = f"{name} timing {tm['safety_goal']}"
    if tm["safety_goal"] not in ctx.safety_goals:
      res.error(where, "safety goal not found in the HARA")
      continue
    if tm["safety_goal"] in timing:
      res.error(where, "duplicate timing entry")
    timing[tm["safety_goal"]] = tm
    hara_ftti = ctx.safety_goals[tm["safety_goal"]]["ftti_ms"]
    if hara_ftti is not None and (tm["ftti_ms"] != hara_ftti or tm["ftti_status"] != "confirmed"):
      res.error(where, f"HARA sets FTTI {hara_ftti} ms; FSC must use it with status confirmed")
    if (tm["ftti_ms"] is None) != (tm["ftti_status"] == "tbd"):
      res.error(where, "ftti_status tbd if and only if ftti_ms is null")
    if status == "released" and tm["ftti_status"] != "confirmed":
      res.error(where, "released FSC requires a confirmed FTTI for every safety goal")
  for sg in ctx.safety_goals:
    if sg not in timing:
      res.error(name, f"no timing entry for {sg}")

  parent_of = {}
  for f in doc["fsrs"]:
    for child in f.get("decomposition", {}).get("into", []):
      if child in parent_of:
        res.error(f"{name} {child}", f"decomposed from both {parent_of[child]} and {f['id']}")
      parent_of[child] = f["id"]

  per_sg = dict.fromkeys(ctx.safety_goals, 0)
  gaps, unproven = [], set()
  for f in doc["fsrs"]:
    where = f"{name} {f['id']}"
    sg = ctx.safety_goals.get(f["safety_goal"])
    if sg is None:
      res.error(where, f"safety goal {f['safety_goal']} not found in the HARA")
      continue
    per_sg[f["safety_goal"]] += 1
    base, orig = parse_asil(f["asil"])
    if f["id"] in parent_of:
      parent = fsrs.get(parent_of[f["id"]])
      if parent and (orig != parent["asil"] or parent["safety_goal"] != f["safety_goal"]):
        res.error(where, f"decomposed ASIL {f['asil']} must be written X({parent['asil']}) under the parent's safety goal")
    elif orig is not None or base != sg["asil"]:
      res.error(where, f"ASIL {f['asil']} must be inherited from {f['safety_goal']} ({sg['asil']}) unless decomposed from a parent FSR")
    for el in f["allocated_to"]:
      if el not in elements:
        res.error(where, f"element {el} not found")
      elif elements[el]["type"] == "external":
        res.error(where, f"FSRs cannot be allocated to external element {el}; record it as an external measure")
    if f.get("warning") and f["warning"] not in warnings:
      res.error(where, f"warning concept {f['warning']} not found")
    ftti = timing.get(f["safety_goal"], {}).get("ftti_ms")
    if f.get("fhti_ms") is not None and ftti is not None and f["fhti_ms"] > ftti:
      res.error(where, f"FHTI {f['fhti_ms']} ms exceeds {f['safety_goal']} FTTI {ftti} ms")
    for v in f["verification"]:
      if v.get("test"):
        ctx.check_path(v["test"], where, res)

    dec = f.get("decomposition")
    if dec:
      kids = [fsrs.get(k) for k in dec["into"]]
      if None in kids:
        res.error(where, f"decomposition target not found: {dec['into']}")
        continue
      pair = tuple(sorted((parse_asil(k["asil"])[0] for k in kids), key=lambda a: -ASIL_ORDER.index(a)))
      if base not in DECOMPOSITION_SCHEMES or pair not in DECOMPOSITION_SCHEMES[base]:
        res.error(where, f"decomposition {f['asil']} -> {' + '.join(k['asil'] for k in kids)} is not an ISO 26262-9 scheme")
      union = {el for k in kids for el in k["allocated_to"]}
      if set(f["allocated_to"]) != union:
        res.error(where, f"allocated_to {sorted(f['allocated_to'])} must equal the union of its decomposed FSRs {sorted(union)}")
      continue
    for el in f["allocated_to"]:
      e = elements.get(el)
      if e is None or e["type"] == "external":
        continue
      if ASIL_ORDER.index(base) > ASIL_ORDER.index(e["asil_capability"]):
        gaps.append(f"{f['id']} ({f['asil']}) on {el} (capability {e['asil_capability']})")
      elif base != "QM" and e["capability_status"] == "unproven":
        unproven.add(el)
  for sg, n in per_sg.items():
    if n == 0:
      res.error(name, f"no FSR derived from {sg}")
  for g in gaps:
    (res.error if status == "released" else res.warn)(name, f"capability gap: {g}")

  for oi in doc["open_items"]:
    for ref in oi["affects"]:
      if ref not in local_ids:
        res.error(f"{name} {oi['id']}", f"affects {ref}, which is not in the FSC or HARA")
    if oi["status"] == "closed" and not oi.get("resolution"):
      res.error(f"{name} {oi['id']}", "closed open item needs a resolution")
  if status == "released" and any(oi["status"] == "open" for oi in doc["open_items"]):
    res.error(name, "released FSC has open items")

  impl = {}
  for f in doc["fsrs"]:
    impl[f["implementation"]["status"]] = impl.get(f["implementation"]["status"], 0) + 1
  res.report.append(f"FSC: {len(fsrs)} FSRs; implementation " + " ".join(f"{k}={v}" for k, v in sorted(impl.items())))
  res.report.append(f"FSC: {len(gaps)} capability gap(s); ASIL allocations to unproven elements: {', '.join(sorted(unproven)) or 'none'}")


def check_guidewords(name, doc, hazards, ctx, res: Result):
  """Function x guide-word matrix: complete, consistent with each hazard's functions and guidewords."""
  entries = {}
  for g in doc["guideword_analysis"]:
    key = (g["function"], g["guideword"])
    where = f"{name} {key[0]}/{key[1]}"
    if key in entries:
      res.error(where, "duplicate guide-word entry")
    entries[key] = g
    if g["function"] not in ctx.functions:
      res.error(where, f"function {g['function']} not found in the System FMEA")
    hzs = g.get("hazards", [])
    if g["classification"] == "SC" and not hzs:
      res.error(where, "SC entry must name at least one hazard")
    if g["classification"] != "SC" and hzs:
      res.error(where, f"{g['classification']} entry must not name hazards")
    for h in hzs:
      if h not in hazards:
        res.error(where, f"hazard {h} not found")
  for key, g in entries.items():
    sub = g.get("subsumed_by")
    if sub:
      target = entries.get((key[0], sub))
      if target is None or target.get("subsumed_by") == key[1]:
        res.error(f"{name} {key[0]}/{key[1]}", f"subsumed_by {sub} must name another guide word of the same function")
  for f in sorted(ctx.functions):
    missing = [g for g in GUIDEWORDS if (f, g) not in entries]
    if missing:
      res.error(name, f"guide-word matrix missing {f} x {', '.join(missing)}")
  for hid, h in hazards.items():
    fns = {k[0] for k, g in entries.items() if hid in g.get("hazards", [])}
    gws = {k[1] for k, g in entries.items() if hid in g.get("hazards", [])}
    if not fns:
      res.error(f"{name} {hid}", "hazard not derived from any SC guide-word entry")
      continue
    if set(h["functions"]) != fns:
      res.error(f"{name} {hid}", f"functions {sorted(h['functions'])} != guide-word matrix {sorted(fns)}")
    if set(h["guidewords"]) != gws:
      res.error(f"{name} {hid}", f"guidewords {sorted(h['guidewords'])} != guide-word matrix {sorted(gws)}")


def check_coverage(name, doc, hazards, situations, ctx, res: Result):
  """Hazard x situation coverage: complete; rated pairs match events; dominated estimates do not exceed the dominating ASIL."""
  hes = {he["id"]: he for he in doc["hazardous_events"]}
  he_asil = {he["id"]: he["asil"] for he in hes.values()}
  seen, rated = set(), {}
  for c in doc["situation_coverage"]:
    key = (c["hazard"], c["situation"])
    where = f"{name} {key[0]}/{key[1]}"
    if key in seen:
      res.error(where, "duplicate coverage entry")
    seen.add(key)
    if c["hazard"] not in hazards or c["situation"] not in situations:
      res.error(where, "unknown hazard or situation")
      continue
    st = c["status"]
    if st == "rated":
      he = hes.get(c.get("he", ""))
      if he is None or (he["hazard"], he["situation"]) != key:
        res.error(where, f"rated entry must name the hazardous event for this pair, got {c.get('he')}")
      else:
        rated[he["id"]] = rated.get(he["id"], 0) + 1
    elif st == "dominated":
      by = hes.get(c.get("by", ""))
      if by is None or by["hazard"] != c["hazard"]:
        res.error(where, f"dominated entry must name a rated event of {c['hazard']} in `by`, got {c.get('by')}")
      elif "estimate" not in c:
        res.error(where, "dominated entry needs an [S, E, C] estimate")
      else:
        est = compute_asil(*c["estimate"])
        if ASIL_ORDER.index(est) > ASIL_ORDER.index(he_asil[by["id"]]):
          res.error(where, f"estimate {' '.join(c['estimate'])} gives ASIL {est}, above {by['id']} ({he_asil[by['id']]}); rate this pair as its own event")
    elif c.get("he") or c.get("by") or c.get("estimate"):
      res.error(where, "not_relevant entry must not carry he/by/estimate")
  missing = [f"{h}/{s}" for h in hazards for s in situations if (h, s) not in seen]
  if missing:
    res.error(name, f"situation coverage missing {len(missing)} pair(s): {', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}")
  for hid in hes:
    if rated.get(hid, 0) != 1:
      res.error(f"{name} {hid}", f"hazardous event appears {rated.get(hid, 0)} times as a rated coverage entry, expected 1")


def check_dfa(name, doc, ctx, res: Result):
  fsc = ctx.fsc
  if fsc is None:
    res.error(name, "DFA requires an FSC")
    return
  if doc["analysis"]["fsc_revision"] != fsc["analysis"]["revision"]:
    res.error(name, f"analyzed FSC rev {doc['analysis']['fsc_revision']}, current FSC is rev {fsc['analysis']['revision']}; update the DFA")
  fsrs = {f["id"]: f for f in fsc["fsrs"]}
  fsc_ids = {e["id"] for e in fsc["elements"]} | {x["id"] for x in fsc["external_measures"]}
  parents = {f["id"]: f for f in fsc["fsrs"] if f.get("decomposition")}
  cats = {c["id"]: c for c in doc["categories"]}
  measures = {m["id"]: m for m in doc["measures"]}
  dfis = {d["id"]: d for d in doc["dfis"]}
  decs = {d["fsr"]: d for d in doc["decompositions"]}

  for m in doc["measures"]:
    for a in m.get("allocated_to", []):
      if a != "process" and a not in fsc_ids:
        res.error(f"{name} {m['id']}", f"allocated to {a}, not an FSC element or external measure")

  for fid in parents:
    if fid not in decs:
      res.error(name, f"FSC decomposition {fid} not analyzed")
  for fid, d in decs.items():
    where = f"{name} {fid}"
    if fid not in parents:
      res.error(where, "not a decomposed FSR in the FSC")
      continue
    into = parents[fid]["decomposition"]["into"]
    if sorted(c["fsr"] for c in d["channels"]) != sorted(into):
      res.error(where, f"channels {[c['fsr'] for c in d['channels']]} != FSC decomposition {into}")
    for c in d["channels"]:
      child = fsrs.get(c["fsr"])
      if child is None:
        continue
      els = {e for e in c["elements"] if e.startswith("EL-")}
      if els != set(child["allocated_to"]):
        res.error(where, f"channel {c['fsr']} elements {sorted(els)} != FSC allocation {sorted(child['allocated_to'])}")
      for e in c["elements"]:
        if e not in fsc_ids:
          res.error(where, f"channel element {e} not in the FSC")

  used_cats = set()
  by_dec: dict[str, list[dict]] = {f: [] for f in decs}
  for d in doc["dfis"]:
    where = f"{name} {d['id']}"
    if d["category"] not in cats:
      res.error(where, f"category {d['category']} not defined")
    else:
      used_cats.add(d["category"])
      if not cats[d["category"]]["applicable"]:
        res.error(where, f"category {d['category']} is declared not applicable")
    for f in d["decompositions"]:
      if f not in decs:
        res.error(where, f"decomposition {f} not in this DFA")
      else:
        by_dec[f].append(d)
    for m in d["measures"]:
      if m not in measures:
        res.error(where, f"measure {m} not defined")
    if d["assessment"] == "sufficient" and not any(measures.get(m, {}).get("status") == "existing" for m in d["measures"]):
      res.error(where, "sufficient requires at least one existing (verified) measure")
  for cid, c in cats.items():
    if c["applicable"] and cid not in used_cats:
      res.error(f"{name} {cid}", "applicable category has no DFI")

  counts: dict[str, int] = {}
  for fid, d in decs.items():
    counts[d["status"]] = counts.get(d["status"], 0) + 1
    if d["status"] == "not_assessable":
      if by_dec[fid]:
        res.error(f"{name} {fid}", "not_assessable decomposition must not carry DFIs")
      if not any(fsrs.get(c["fsr"], {}).get("implementation", {}).get("status") == "gap" for c in d["channels"]):
        res.error(f"{name} {fid}", "not_assessable only when a channel is not yet defined (implementation gap)")
      continue
    assessments = {x["assessment"] for x in by_dec[fid]}
    expected = "not_accepted" if "insufficient" in assessments else "conditional" if "open" in assessments else "accepted"
    if d["status"] != expected:
      res.error(f"{name} {fid}", f"status {d['status']} but its DFIs give {expected}")
  if doc["analysis"]["status"] == "released" and counts.get("not_accepted"):
    res.error(name, "released DFA has decompositions that are not accepted")

  ids = set(dfis) | set(measures) | set(fsrs) | {e["id"] for e in fsc["elements"]}
  for oi in doc["open_items"]:
    for ref in oi["affects"]:
      if ref not in ids:
        res.error(f"{name} {oi['id']}", f"affects {ref}, which is not in the DFA or FSC")
    if oi["status"] == "closed" and not oi.get("resolution"):
      res.error(f"{name} {oi['id']}", "closed open item needs a resolution")

  a_counts: dict[str, int] = {}
  for d in doc["dfis"]:
    a_counts[d["assessment"]] = a_counts.get(d["assessment"], 0) + 1
  res.report.append("DFA decompositions: " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
  res.report.append("DFA initiators: " + " ".join(f"{k}={v}" for k, v in sorted(a_counts.items()))
                    + f"; required measures: {sum(1 for m in doc['measures'] if m['status'] == 'required')}")


WP_C03_GOAL = re.compile(r"^\| \*\*(SG-\d{2})\*\* \|[^|]*\| \*\*(QM|A|B|C|D)\*\*")
WP_C03_HAZARD = re.compile(r"^### 5\.\d+ (H-\d{2}) ")
WP_C03_EVENT = re.compile(r"^\| (HE-\d{2}\.\d+) \|")
AGREEMENTS = ("same", "second_higher", "wp_c03_higher", "no_counterpart")


def parse_wp_c03(text: str):
  """Hazards, hazardous events and safety goals (with ASIL) of the HARA of record, from its markdown tables."""
  hazards, events, goals = set(), set(), {}
  for line in text.splitlines():
    if m := WP_C03_HAZARD.match(line):
      hazards.add(m.group(1))
    elif m := WP_C03_EVENT.match(line):
      events.add(m.group(1))
    elif m := WP_C03_GOAL.match(line):
      goals[m.group(1)] = m.group(2)
  return hazards, events, goals


def check_hara_mapping(name, doc, ctx, res: Result):
  """The second-set HARA mapped onto WP-C-03 (docs-safety-reconciliation.md §8)."""
  target = ctx.root / doc["target"]
  if not target.exists():
    res.error(name, f"target {doc['target']} not found")
    return
  wp_hazards, wp_events, wp_goals = parse_wp_c03(target.read_text(encoding="utf-8"))
  decisions = set(doc.get("decisions", []))

  mapped = set()
  for row in doc["hazards"]:
    where = f"{name} {row['second']}"
    mapped.add(row["second"])
    if ctx.hazards is not None and row["second"] not in ctx.hazards:
      res.error(where, "not a hazard of the second-set HARA")
    for h in row["wp_c03"]:
      if h not in wp_hazards:
        res.error(where, f"{h} not found in {doc['target']}")
    for he in row["events"]:
      if he not in wp_events:
        res.error(where, f"{he} not found in {doc['target']}")
    if not row["wp_c03"] and not row.get("note"):
      res.error(where, "unmapped hazard needs a note saying why")
  for h in sorted((ctx.hazards or set()) - mapped):
    res.error(name, f"second-set hazard {h} is not mapped")

  mapped = set()
  for row in doc["goals"]:
    where = f"{name} {row['second']}"
    mapped.add(row["second"])
    sg = ctx.safety_goals.get(row["second"])
    if sg is None:
      res.error(where, "not a safety goal of the second-set HARA")
    elif sg["asil"] != row["second_asil"]:
      res.error(where, f"second_asil {row['second_asil']} != {sg['asil']} in the second-set HARA")
    missing = [g for g in row["wp_c03"] if g not in wp_goals]
    for g in missing:
      res.error(where, f"{g} not found in {doc['target']}")
    wp_asil = max_asil(wp_goals[g] for g in row["wp_c03"]) if row["wp_c03"] and not missing else None
    if not missing and wp_asil != row["wp_c03_asil"]:
      res.error(where, f"wp_c03_asil {row['wp_c03_asil']} != {wp_asil} in {doc['target']}")
    if wp_asil is None:
      expected = "no_counterpart"
    else:
      order = ASIL_ORDER.index(row["second_asil"]) - ASIL_ORDER.index(wp_asil)
      expected = "same" if order == 0 else "second_higher" if order > 0 else "wp_c03_higher"
    if row["agreement"] not in AGREEMENTS:
      res.error(where, f"agreement {row['agreement']} not one of {', '.join(AGREEMENTS)}")
    elif row["agreement"] != expected:
      res.error(where, f"agreement is {row['agreement']}, the ASILs give {expected}")
    if expected in ("second_higher", "no_counterpart"):
      if not row.get("decision"):
        res.error(where, f"{expected} needs a reconciliation decision")
      elif row["decision"] not in decisions:
        res.error(where, f"decision {row['decision']} not listed in decisions")
  for g in sorted(set(ctx.safety_goals) - mapped):
    res.error(name, f"second-set safety goal {g} is not mapped")
  res.report.append(
    f"HARA mapping: {len(doc['goals'])} goals, " +
    ", ".join(f"{a} {sum(r['agreement'] == a for r in doc['goals'])}" for a in AGREEMENTS))


FTA_CLASSES = {   # event class -> FMEA prefixes of which at least one must back it (None: no FMEA, a reason instead)
  "systematic_sw": ("SWF", "SFM"),
  "systematic_hw": ("DFM",),
  "random_hw": ("DFM", "FMEDA"),
  "sotif": ("SFM",),
  "installation": ("PFM",),
  "by_design": None,
  "external": None,
}
WP_C03_GOAL_EVENTS = re.compile(r"^\| \*\*(SG-\d{2})\*\* \|[^|]*\|[^|]*\|([^|]*)\|")
HE_RANGE = re.compile(r"HE-(\d{2})\.(\d+)(?:\s*[–-]\s*(\d{2})\.(\d+))?")


def goal_events(wp_c03_text: str) -> dict[str, set[str]]:
  """Hazardous events each WP-C-03 safety goal covers, from the 'source' column of its goal table."""
  out: dict[str, set[str]] = {}
  for line in wp_c03_text.splitlines():
    m = WP_C03_GOAL_EVENTS.match(line)
    if not m:
      continue
    evs = out.setdefault(m.group(1), set())
    for h, a, h2, b in HE_RANGE.findall(m.group(2)):
      if h2 and h2 != h:
        continue
      for i in range(int(a), int(b or a) + 1):
        evs.add(f"HE-{h}.{i}")
  return out


def _fta_module(root: Path):
  sys.path.insert(0, str(root / "assurance" / "08-analyses" / "fta"))
  try:
    import fta_diagrams
  finally:
    sys.path.pop(0)
  return fta_diagrams


def fta_reach(fd, tree) -> tuple[list, set[str]]:
  """Leaf events (first node per id) and gate ids reachable from a tree's top event, following transfers."""
  leaves: dict[str, object] = {}
  gates: set[str] = set()

  def visit(n):
    if n.kind == "transfer_in":
      gates.add(n.ident)
      visit(n.ref_of)
      return
    if n.children:
      if n.ident:
        gates.add(n.ident)
      for c in n.children:
        visit(c)
    elif n.ident:
      leaves.setdefault(n.ident, n)

  visit(tree.root)
  return list(leaves.values()), gates


def check_fta_fmea_map(name, doc, ctx, res: Result):
  """FTA basic events <-> FMEA failure modes (ISO 26262-9 clause 8), for the goals in scope."""
  fd = _fta_module(ctx.root)
  trees = fd.parse_document((ctx.root / doc["source"]).read_text(encoding="utf-8"))
  fd.resolve(trees)
  by_goal = {t.goal: t for t in trees}
  hm = load_yaml((ctx.root / SAFETY_DIR / "hara-mapping.yaml").read_text())
  sg_events = goal_events((ctx.root / hm["target"]).read_text(encoding="utf-8"))
  hz_events = {h["second"]: set(h["events"]) for h in hm["hazards"]}

  events = {e["id"]: e for e in doc.get("events", [])}
  gates = {g["id"]: g for g in doc.get("gates", [])}

  def refs_ok(where, row):
    for f in row.get("fmea", []):
      if f not in ctx.fm_index:
        res.error(where, f"FMEA failure mode {f} not found")
    for f in row.get("fmeda", []):
      stem, _, fid = f.partition(":")
      if fid not in ctx.fmeda_ids.get(stem, set()):
        res.error(where, f"FMEDA failure mode {f} not found")

  for eid, e in events.items():
    where = f"{name} {eid}"
    refs_ok(where, e)
    cls = e.get("class")
    if cls not in FTA_CLASSES:
      res.error(where, f"class {cls} not one of {', '.join(FTA_CLASSES)}")
      continue
    need = FTA_CLASSES[cls]
    backing = [f.split("-")[0] for f in e.get("fmea", [])] + ["FMEDA"] * len(e.get("fmeda", []))
    if need is None:
      if not (e.get("reason") or e.get("ref")):
        res.error(where, f"{cls} event needs a reason or ref")
    elif not backing:
      if not e.get("gap"):
        res.error(where, "no FMEA backing and no gap statement")
    elif not any(b in need for b in backing):
      res.error(where, f"{cls} event needs one of {', '.join(need)}; has {', '.join(sorted(set(backing)))}")

  for gid, g in gates.items():
    refs_ok(f"{name} {gid}", g)

  nf = {(r["fm"], r["goal"]): r for r in doc.get("not_in_fta", [])}
  for (fm, _goal), r in nf.items():
    if fm not in ctx.fm_index:
      res.error(f"{name} not_in_fta {fm}", "FMEA failure mode not found")
    if r.get("kind") not in ("justified", "tree_gap") or not r.get("reason"):
      res.error(f"{name} not_in_fta {fm}", "kind must be justified or tree_gap, with a reason")

  reachable: set[str] = set()
  for goal in doc["scope"]:
    tree = by_goal.get(goal)
    if tree is None:
      res.error(name, f"scope goal {goal} has no fault tree in {doc['source']}")
      continue
    leaves, gate_ids = fta_reach(fd, tree)
    leaf_ids = {n.ident for n in leaves}
    reachable |= leaf_ids
    for eid in sorted(leaf_ids - set(events), key=fd_sort_key):
      res.error(f"{name} {goal}", f"{eid} is in the {goal} tree but not mapped")
    for gid in set(gates) - gate_ids - {g for t in by_goal.values() for g in fta_reach(fd, t)[1]}:
      res.error(f"{name} {gid}", "gate not found in any tree")

    goal_hz = {hz for hz, evs in hz_events.items() if evs & sg_events.get(goal, set())}
    cited = {f for e in leaf_ids if e in events for f in events[e].get("fmea", [])}
    cited |= {f for g in gate_ids if g in gates for f in gates[g].get("fmea", [])}
    relevant = {fid for fid, fm in ctx.fm_index.items() if {x.get("hazard") for x in fm["effects"]} & goal_hz}
    for fid in sorted(cited & {f for (f, g) in nf if g == goal}):
      res.error(f"{name} {goal}", f"{fid} is in not_in_fta for {goal} but an event or gate of the tree cites it")
    for fid in sorted(relevant - cited):
      if (fid, goal) not in nf:
        hz = ", ".join(sorted({x.get("hazard") for x in ctx.fm_index[fid]["effects"]} & goal_hz))
        res.error(f"{name} {goal}", f"{fid} cites {hz} but no {goal} event or gate cites it, and it is not in not_in_fta")
    for fid in sorted(cited - relevant):
      if fid in ctx.fm_index:
        res.warn(f"{name} {goal}", f"{fid} is cited in the {goal} tree but its effects cite none of {', '.join(sorted(goal_hz))}")

    hot = fd.single_point_nodes(tree)
    spf = {n.ident for n in leaves if id(n) in hot}
    for eid in sorted(spf & set(events)):
      causes = [c for f in events[eid].get("fmea", []) for c in ctx.fm_index.get(f, {}).get("causes", [])]
      if causes and all(isinstance(c.get("detection"), int) and c["detection"] <= 4 for c in causes):
        res.warn(f"{name} {eid}", "single point in the tree, but every FMEA cause claims a detection rating <= 4")

    mapped = [events[e] for e in leaf_ids if e in events]
    counts = {
      "backed": sum(1 for e in mapped if e.get("fmea") or e.get("fmeda")),
      "by design": sum(1 for e in mapped if e.get("class") == "by_design"),
      "external": sum(1 for e in mapped if e.get("class") == "external"),
      "unbacked": sum(1 for e in mapped if e.get("class") not in ("by_design", "external") and not (e.get("fmea") or e.get("fmeda"))),
    }
    for e in mapped:
      if e.get("class") not in ("by_design", "external") and not (e.get("fmea") or e.get("fmeda")):
        res.warn(f"{name} {e['id']}", f"no FMEA backing: {e.get('gap', '(no gap statement)')}")
    rows = [r for (f, g), r in nf.items() if g == goal]
    event_counts = ", ".join(f"{k} {v}" for k, v in counts.items())
    n_just = sum(r["kind"] == "justified" for r in rows)
    n_gap = sum(r["kind"] == "tree_gap" for r in rows)
    fmea_counts = f"in the tree {len(relevant & cited)}, justified {n_just}, tree gaps {n_gap}"
    res.report.append(f"FTA-FMEA map {goal}: {len(leaf_ids)} events ({event_counts}); {len(relevant)} FMEA modes reach {goal} ({fmea_counts})")

  if all(g in by_goal for g in doc["scope"]):
    for eid in sorted(set(events) - reachable, key=fd_sort_key):
      res.warn(f"{name} {eid}", "mapped, but not in the tree of any goal in scope")


STPA_STATUS = ("covered", "known_gap", "new", "open_test")
STPA_UCA_RE = re.compile(r"^\| (UCA-\d+) \|", re.M)
STPA_LS_RE = re.compile(r"^\| (LS-\d+) \|", re.M)
STPA_HAZARD_RE = re.compile(r"^\| (H-\d+|H-STPA-\d+) \|", re.M)
TSR_RE = re.compile(r"^\| (TSR-\d+) \|", re.M)


def check_stpa_map(name, doc, ctx, res: Result):
  """STPA loss scenarios <-> fault-tree events, FMEA failure modes and TSRs (WP-A-05 step 4 cross-check)."""
  text = (ctx.root / doc["source"]).read_text(encoding="utf-8")
  doc_ucas, doc_ls = set(STPA_UCA_RE.findall(text)), set(STPA_LS_RE.findall(text))
  doc_hazards = set(STPA_HAZARD_RE.findall(text))
  fd = _fta_module(ctx.root)
  trees = fd.parse_document((ctx.root / doc["fta_source"]).read_text(encoding="utf-8"))
  fd.resolve(trees)
  goal_events = {t.goal: {n.ident for n in fta_reach(fd, t)[0]} for t in trees}
  all_events = set().union(*goal_events.values())
  tsrs = set(TSR_RE.findall((ctx.root / doc["tsr_source"]).read_text(encoding="utf-8")))

  hazards = doc["hazards"]
  for hid, goals in hazards.items():
    if hid not in doc_hazards:
      res.error(f"{name} {hid}", "hazard not in the STPA hazard table")
    for g in goals:
      if g not in goal_events:
        res.error(f"{name} {hid}", f"goal {g} has no fault tree")
  for hid in sorted(doc_hazards - set(hazards)):
    res.error(f"{name} {hid}", "STPA hazard not mapped to safety goals")

  scenarios = {s["id"]: s for s in doc["scenarios"]}
  external = {u["uca"]: u for u in doc.get("external_ucas", [])}
  for lid in sorted(doc_ls - set(scenarios), key=fd_sort_key):
    res.error(f"{name} {lid}", "loss scenario in WP-A-05 but not in the map")
  for lid in sorted(set(scenarios) - doc_ls, key=fd_sort_key):
    res.error(f"{name} {lid}", "mapped, but no such loss scenario in WP-A-05")
  covered_ucas = {u for s in scenarios.values() for u in s["ucas"]}
  for uid in sorted(doc_ucas - covered_ucas - set(external), key=fd_sort_key):
    res.error(f"{name} {uid}", "UCA has no loss scenario and is not recorded as an external assumption")
  for uid in sorted((covered_ucas | set(external)) - doc_ucas, key=fd_sort_key):
    res.error(f"{name} {uid}", "cited, but no such UCA in WP-A-05")
  for uid, u in external.items():
    if not u.get("assumption"):
      res.error(f"{name} {uid}", "external UCA needs the assumption it rests on")

  counts = dict.fromkeys(STPA_STATUS, 0)
  for lid, s in scenarios.items():
    where = f"{name} {lid}"
    st = s.get("status")
    if st not in STPA_STATUS:
      res.error(where, f"status {st} not one of {', '.join(STPA_STATUS)}")
      continue
    counts[st] += 1
    for h in s["hazards"]:
      if h not in hazards:
        res.error(where, f"hazard {h} not mapped")
    for e in s.get("fta", []):
      if e not in all_events:
        res.error(where, f"fault-tree event {e} not found in {doc['fta_source']}")
    for f in s.get("fmea", []):
      if f not in ctx.fm_index:
        res.error(where, f"FMEA failure mode {f} not found")
    for r in s.get("requirements", []):
      if r not in tsrs:
        res.error(where, f"requirement {r} not found in {doc['tsr_source']}")
    goals = {g for h in s["hazards"] for g in hazards.get(h, [])}
    for e in s.get("fta", []):
      if goals and e in all_events and not any(e in goal_events[g] for g in goals):
        res.warn(where, f"{e} is in no fault tree of {', '.join(sorted(goals))} (the scenario's hazards)")
    refs = s.get("fta", []) + s.get("fmea", [])
    if st in ("covered", "known_gap") and not refs:
      res.error(where, f"status {st} needs at least one fault-tree event or FMEA failure mode")
    if st == "new" and not s.get("finding"):
      res.error(where, "status new needs a finding")
  status_counts = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in counts.items())
  uca_counts = f"{len(covered_ucas & doc_ucas)} with a loss scenario, {len(set(external) & doc_ucas)} external"
  res.report.append(f"STPA map: {len(doc_ucas)} UCAs ({uca_counts}); {len(scenarios)} loss scenarios ({status_counts})")


def fd_sort_key(ident: str):
  return [int(x) if x.isdigit() else x for x in re.split(r"[-.]", ident)]


class Context:
  def __init__(self, root: Path):
    self.root = root
    self.empty_submodules = empty_submodules(root)
    self.failure_modes: set[str] = set()
    self.elements: set[str] = set()
    self.functions: set[str] = set()
    self.fm_hazards: dict[str, set[str]] = {}  # FMEA failure mode -> hazards its effects link to
    self.fm_index: dict[str, dict] = {}  # every FMEA failure mode (System, DFMEA, SW, PFMEA) by id
    self.fmeda_ids: dict[str, set[str]] = {}  # FMEDA file stem -> its failure mode ids
    self.hazards: set[str] | None = None  # None until a HARA file is loaded
    self.safety_goals: dict[str, dict] = {}
    self.hara_revision: str | None = None
    self.hara_open_items: set[str] = set()
    self.fsc: dict | None = None
    self.ap_counts = {"H": 0, "M": 0, "L": 0}
    self.msr_counts = {"in_scope": 0, "exempt": 0, "H": 0, "M": 0, "L": 0}
    self.fmeda_dc: dict[str, float | None] = {}  # "<fmeda file stem>/<failure mode id>" -> dc_spf
    wp = root / WP_S04
    self.ftti_rows = parse_ftti_rows(wp.read_text()) if wp.exists() else None

  def check_path(self, path, where, res: Result):
    if (self.root / path).exists():
      return
    sub = next((s for s in self.empty_submodules if path == s or path.startswith(s + "/")), None)
    if sub:
      res.warn(where, f"{path} is in uninitialized submodule {sub}; cannot verify")
    else:
      res.error(where, f"path {path} does not exist")


def lint(root: Path = ROOT) -> Result:
  res = Result()
  ctx = Context(root)
  safety = root / SAFETY_DIR

  baseline_ids = set()
  bl_path = safety / "baseline.yaml"
  if bl_path.exists():
    bl = load_yaml(bl_path.read_text())
    schema_errors(bl, load_schema(root, "baseline.schema.json"), "baseline.yaml", res)
    baseline_ids = {b.get("id") for b in (bl or {}).get("baselines", [])}
  else:
    res.error("baseline.yaml", "missing")

  rt = rating_tables_version(root)
  rt_sod = sod_unchanged_since(root)
  schemas = {kind: load_schema(root, f"{kind}.schema.json") for kind in ("fmea", "fmeda", "hara", "fsc", "dfa")}

  docs = []
  seen_ids: dict[str, str] = {}
  for path in sorted((safety / "analyses").glob("*.yaml")):
    name = path.relative_to(root).as_posix()
    doc = load_yaml(path.read_text())
    kind = (doc or {}).get("analysis", {}).get("type")
    n_before = len(res.errors)
    schema_errors(doc, schemas.get(kind, schemas["fmea"]), name, res)
    if len(res.errors) > n_before:
      continue  # semantic checks assume a schema-valid document
    hdr = doc["analysis"]
    if hdr["baseline"] not in baseline_ids:
      res.error(name, f"baseline {hdr['baseline']} not in baseline.yaml")
    if kind not in ("hara", "fsc", "dfa") and hdr["rating_tables"] != rt:
      uses_msr = kind in FMEA_TYPES and (hdr.get("msr") in ("partial", "complete")
                                         or any(c.get("msr") for fm in doc["failure_modes"] for c in fm["causes"]))
      if hdr["rating_tables"] != rt_sod or uses_msr:
        res.error(name, f"rating_tables {hdr['rating_tables']} != current {rt}; re-rate against the current tables")

    # FMEA ids are global (cross-linked between files); FMEDA ids are per file (one FMEDA per safety goal).
    if kind == "fmeda":
      scope: dict[str, str] = {}
      ids = [m["id"] for m in doc["safety_mechanisms"]]
      ids += [c["id"] for c in doc["components"]]
      ids += [fm["id"] for c in doc["components"] for fm in c["failure_modes"]]
      ctx.fmeda_ids[path.stem] = {fm["id"] for c in doc["components"] for fm in c["failure_modes"]}
      ctx.fmeda_dc.update((f"{path.stem}/{fm['id']}", fm.get("dc_spf")) for c in doc["components"] for fm in c["failure_modes"])
    elif kind == "hara":
      scope = seen_ids
      ids = [x["id"] for k in ("assumptions", "operational_situations", "hazards", "hazardous_events", "safety_goals", "open_items")
             for x in doc[k]]
      ctx.hazards = {h["id"] for h in doc["hazards"]}
      ctx.safety_goals = {sg["id"]: sg for sg in doc["safety_goals"]}
      ctx.hara_revision = hdr["revision"]
      ctx.hara_open_items = {oi["id"] for oi in doc["open_items"]}
    elif kind == "dfa":
      scope = seen_ids
      ids = [x["id"] for k in ("categories", "dfis", "measures", "open_items") for x in doc[k]]
    elif kind == "fsc":
      scope = seen_ids
      ctx.fsc = doc
      ids = [x["id"] for k in ("elements", "external_measures", "operating_modes", "warning_degradation", "fsrs", "open_items")
             for x in doc[k]]
    else:
      scope = seen_ids
      ids = [x["id"] for k in ("structure", "functions", "actions", "failure_modes") for x in doc[k]]
      ids += [c["id"] for fm in doc["failure_modes"] for c in fm["causes"]]
      ctx.failure_modes.update(fm["id"] for fm in doc["failure_modes"])
      ctx.fm_index.update((fm["id"], fm) for fm in doc["failure_modes"])
      ctx.elements.update(e["id"] for e in doc["structure"])
      # The HARA traces to System FMEA functions and failure modes only; lower-level FMEAs may cite
      # hazards in their effects without joining the guide-word matrix or the HARA sfm_refs back-links.
      if kind == "system_fmea":
        ctx.functions.update(f["id"] for f in doc["functions"])
        for fm in doc["failure_modes"]:
          ctx.fm_hazards[fm["id"]] = {e["hazard"] for e in fm["effects"] if e.get("hazard")}
    for i in ids:
      if i in scope:
        res.error(name, f"duplicate id {i} (also in {scope[i]})")
      scope[i] = name
    docs.append((name, kind, doc))

  for name, kind, doc in docs:
    {"fmeda": check_fmeda, "hara": check_hara, "fsc": check_fsc, "dfa": check_dfa}.get(kind, check_fmea)(name, doc, ctx, res)

  mapping = safety / "hara-mapping.yaml"
  if mapping.exists():
    check_hara_mapping(mapping.relative_to(root).as_posix(), load_yaml(mapping.read_text()), ctx, res)

  stpa_map = root / "assurance" / "08-analyses" / "stpa-map.yaml"
  if stpa_map.exists():
    check_stpa_map(stpa_map.relative_to(root).as_posix(), load_yaml(stpa_map.read_text()), ctx, res)
  fta_map = root / "assurance" / "08-analyses" / "fta-fmea-map.yaml"
  if fta_map.exists():
    check_fta_fmea_map(fta_map.relative_to(root).as_posix(), load_yaml(fta_map.read_text()), ctx, res)

  res.report.insert(0, f"rated causes by AP: H={ctx.ap_counts['H']} M={ctx.ap_counts['M']} L={ctx.ap_counts['L']}")
  mc = ctx.msr_counts
  rated = mc["H"] + mc["M"] + mc["L"]
  provisional = " [provisional MSR AP table]" if AP_MSR_PROVISIONAL else ""
  res.report.insert(1, f"FMEA-MSR: {rated} of {mc['in_scope']} in-scope causes rated "
                    + f"(H={mc['H']} M={mc['M']} L={mc['L']}), {mc['exempt']} exempt{provisional}")
  return res


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--root", type=Path, default=ROOT)
  ap.add_argument("--report", action="store_true", help="print AP summary and FMEDA metrics")
  args = ap.parse_args(argv)

  res = lint(args.root.resolve())
  for line in res.warnings + res.errors:
    print(line)
  if args.report:
    for line in res.report:
      print(line)
  print(f"{len(res.errors)} error(s), {len(res.warnings)} warning(s)")
  return 1 if res.errors else 0


if __name__ == "__main__":
  sys.exit(main())
