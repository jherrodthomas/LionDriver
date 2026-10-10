#!/usr/bin/env python3
"""Validate LionDriver FMEA / FMEDA files against the schemas and rating rules.

Usage: tools/safety/fmea_lint.py [--root REPO_ROOT] [--report]

Requires PyYAML and jsonschema (not openpilot runtime deps):
  pip install pyyaml jsonschema

Rules are documented in docs/safety/rating-tables.md.
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
SAFETY_DIR = Path("docs/safety")
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
        if not any(ctl.get("test") for ctl in c["detection_controls"]):
          res.error(cwhere, f"detection {c['detection']} claims a targeted test; a detection control must name a `test` path")
      for a in c.get("actions", []):
        referenced_actions.add(a)
        if a not in actions:
          res.error(cwhere, f"action {a} not found")

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


class Context:
  def __init__(self, root: Path):
    self.root = root
    self.empty_submodules = empty_submodules(root)
    self.failure_modes: set[str] = set()
    self.elements: set[str] = set()
    self.functions: set[str] = set()
    self.fm_hazards: dict[str, set[str]] = {}  # FMEA failure mode -> hazards its effects link to
    self.hazards: set[str] | None = None  # None until a HARA file is loaded
    self.ap_counts = {"H": 0, "M": 0, "L": 0}

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
  schemas = {kind: load_schema(root, f"{kind}.schema.json") for kind in ("fmea", "fmeda", "hara")}

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
    if kind != "hara" and hdr["rating_tables"] != rt:
      res.error(name, f"rating_tables {hdr['rating_tables']} != current {rt}; re-rate against the current tables")

    # FMEA ids are global (cross-linked between files); FMEDA ids are per file (one FMEDA per safety goal).
    if kind == "fmeda":
      scope: dict[str, str] = {}
      ids = [m["id"] for m in doc["safety_mechanisms"]]
      ids += [c["id"] for c in doc["components"]]
      ids += [fm["id"] for c in doc["components"] for fm in c["failure_modes"]]
    elif kind == "hara":
      scope = seen_ids
      ids = [x["id"] for k in ("assumptions", "operational_situations", "hazards", "hazardous_events", "safety_goals", "open_items")
             for x in doc[k]]
      ctx.hazards = {h["id"] for h in doc["hazards"]}
    else:
      scope = seen_ids
      ids = [x["id"] for k in ("structure", "functions", "actions", "failure_modes") for x in doc[k]]
      ids += [c["id"] for fm in doc["failure_modes"] for c in fm["causes"]]
      ctx.failure_modes.update(fm["id"] for fm in doc["failure_modes"])
      ctx.elements.update(e["id"] for e in doc["structure"])
      ctx.functions.update(f["id"] for f in doc["functions"])
      for fm in doc["failure_modes"]:
        ctx.fm_hazards[fm["id"]] = {e["hazard"] for e in fm["effects"] if e.get("hazard")}
    for i in ids:
      if i in scope:
        res.error(name, f"duplicate id {i} (also in {scope[i]})")
      scope[i] = name
    docs.append((name, kind, doc))

  for name, kind, doc in docs:
    {"fmeda": check_fmeda, "hara": check_hara}.get(kind, check_fmea)(name, doc, ctx, res)

  res.report.insert(0, f"rated causes by AP: H={ctx.ap_counts['H']} M={ctx.ap_counts['M']} L={ctx.ap_counts['L']}")
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
