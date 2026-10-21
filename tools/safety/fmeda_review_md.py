#!/usr/bin/env python3
"""Write the FMEDA review pages (assurance/08-analyses/fmea/exports/review/fmeda-*.md) from the FMEDA YAML.

Usage:
  tools/safety/fmeda_review_md.py           write the pages
  tools/safety/fmeda_review_md.py --check   fail if a committed page differs from a fresh build

One page per FMEDA file, readable in GitHub's web view and on a phone: metrics per goal against the targets of
WP-H-04 §4, then components and their rate sources, the failure modes with their classification, rows another goal
classifies differently, safety mechanisms, open items and the revision history. The arithmetic is fmea_lint's.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_fmeda_xlsx  # noqa: E402
import fmea_lint  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FMEA = ROOT / "assurance/08-analyses/fmea"
ANALYSES = FMEA / "analyses"
OUT = FMEA / "exports/review"
GENERATOR = "tools/safety/fmeda_review_md.py"
SOURCES = export_fmeda_xlsx.SOURCES
FIGURE = {"fmeda-sg001": "fig-3-10-fmeda-sg001-metrics.svg", "fmeda-sg009": "fig-3-11-fmeda-sg009-metrics.svg"}
# the what-if page is a private claude.ai artifact of the project lead; it embeds a snapshot of these YAML files
WHAT_IF = "https://claude.ai/artifact/6btZjojvGtcyZdYrhzsR8Z"


def one(s) -> str:
  return " ".join(str(s).split()).replace("|", "\\|")


def pct(v: float) -> str:
  return f"{v * 100:.2f} %"


def fit(v: float) -> str:
  return f"{v:.3g}" if v < 10 else f"{v:.1f}"


def classify(fm: dict) -> str:
  if fm["violates_sg_directly"]:
    return "RF" if fm.get("safety_mechanism_spf") and fm.get("dc_spf", 0) > 0 else "SPF"
  if fm["mpf_potential"]:
    return "MPF, latent part" if not fm.get("safety_mechanism_lf") else "MPF, detected and latent parts"
  return "safe"


def verdict(m: dict, asil: str) -> tuple[bool, str]:
  st, lt, pt = fmea_lint.FMEDA_TARGETS[asil]
  miss = []
  if m["spfm"] < st:
    miss.append(f"SPFM < {st * 100:.0f} %")
  if m["lfm"] < lt:
    miss.append(f"LFM < {lt * 100:.0f} %")
  if m["pmhf_spf_rf_fit"] >= pt:
    miss.append(f"λSPF+λRF ≥ {pt:g} FIT")
  return (not miss, "met on this estimate" if not miss else "missed: " + ", ".join(miss))


def page(name: str, doc: dict) -> str:
  a = doc["analysis"]
  comps = doc["components"]
  sms = {s["id"]: s for s in doc["safety_mechanisms"]}
  generic = sum(1 for c in comps if c.get("rate_kind", "generic") == "generic")
  L = [f"# FMEDA review: {a['title']}", "",
       f"> Generated from [`analyses/{name}.yaml`](../../analyses/{name}.yaml) by `{GENERATOR}`. Edit the YAML and regenerate; "
       "never edit this page.", "",
       "| Revision | Status | Baseline | Rating tables | Updated |", "|---|---|---|---|---|",
       f"| {a['revision']} | {a['status']} | {a['baseline']} | {a['rating_tables']} | {a.get('updated', '')} |", "",
       f"**Scope.** {one(a['scope'])}", "",
       f"> ⚠️ **Estimate.** {generic} of {len(comps)} failure rates are generic order-of-magnitude estimates, and "
       f"{sum(1 for c in comps if c.get('stress_converted'))} are converted to the mission profile. The metrics show where the "
       "design falls short. They are not evidence that a target is met.", "",
       f"![Metrics per goal and failure-rate split](../../figures/generated/{FIGURE[name]})", "",
       "## How to review", "",
       "Start with the metrics per goal, then the failure modes that drive them (SPF and latent rows). Comment on this page's "
       "lines in a pull request, or open an issue naming the row ID (FMD-…). For a rate or DC, say which value you would use "
       f"and its source. To try values before asking for a change, use the [what-if page]({WHAT_IF}) (private link; it holds "
       f"a snapshot of this revision). The same data as a workbook with live formulas: [`{name}-review.xlsx`]({name}-review.xlsx).",
       "",
       "## Contents", "",
       "- [Metrics per goal](#1-metrics-per-goal)", "- [Components and failure-rate sources](#2-components-and-failure-rate-sources)",
       "- [Failure modes](#3-failure-modes)", "- [Rows classified differently for another goal](#4-rows-classified-differently-for-another-goal)",
       "- [Safety mechanisms](#5-safety-mechanisms)", "- [Open items](#6-open-items)", "- [Revision history](#7-revision-history)", "",
       "## 1. Metrics per goal", "",
       "Targets from WP-H-04 §4. LD-HARA-001 rates this file's goal "
       f"{a['safety_goal']} at ASIL {a['asil_target']}; that rating is shown for reference only." if a.get("targets") else
       f"Target: {a['safety_goal']} ASIL {a['asil_target']}.", "",
       "| Goal | ASIL | SPFM | LFM | λSPF + λRF (FIT) | Result | Basis |", "|---|---|---:|---:|---:|---|---|"]
  bases = {t["goal"]: t["basis"] for t in a.get("targets", [])}
  for goal, asil, alongside in export_fmeda_xlsx.target_rows(doc):
    m = fmea_lint.fmeda_metrics(doc, goal or None)
    ok, text = verdict(m, asil)
    L.append(f"| {goal} | {asil}{' (alongside)' if alongside else ''} | {pct(m['spfm'])} | {pct(m['lfm'])} | "
             f"{fit(m['pmhf_spf_rf_fit'])} | {'🟠' if ok else '🔴'} {text} | {'' if alongside else one(bases.get(goal, ''))} |")
  m0 = fmea_lint.fmeda_metrics(doc)
  L += ["", f"Total safety-related λ {fit(m0['total_fit'])} FIT. λSPF + λRF is the single-point and residual part of PMHF only; "
        "the dual-point term is not computed (rating-tables §6.3). 🟠 means met on generic estimates, not verified.", "",
        "## 2. Components and failure-rate sources", "",
        "| ID | Part | λ (FIT) | Rate kind | Handbook reference | Ref. temp. | Converted | Wire ends |",
        "|---|---|---:|---|---|---:|---|---|"]
  for c in comps:
    L.append(f"| {c['id']} | {one(c['part'])}{'' if c['safety_related'] else ' (not safety-related)'} | {c['failure_rate_fit']} | "
             f"{c.get('rate_kind', '—')} | {one(c.get('handbook_ref', '—'))} | "
             f"{str(c['reference_temp_c']) + ' °C' if 'reference_temp_c' in c else '—'} | {'yes' if c.get('stress_converted') else 'no'} | "
             f"{'<sub>' + ', '.join(c['wire_ends']) + '</sub>' if c.get('wire_ends') else '—'} |")
  L += ["", "<details><summary>Rate source text per component</summary>", ""]
  for c in comps:
    L.append(f"- **{c['id']}:** {one(c['failure_rate_source'])}")
  L += ["", "</details>", "", "## 3. Failure modes", "",
        "Classified for this file's own goal (rating-tables §6.1). λ is the component rate × distribution.", "",
        "| Row | Component | Failure mode | Dist. | λ (FIT) | Class | Mechanism (DC) | DFMEA | Other goals |",
        "|---|---|---|---:|---:|---|---|---|---|"]
  badge = {"SPF": "🔴 SPF", "RF": "🟠 RF", "safe": "safe"}
  for c in comps:
    for fm in c["failure_modes"]:
      cls = classify(fm)
      mech = fm.get("safety_mechanism_spf") or fm.get("safety_mechanism_lf")
      dc = fm.get("dc_spf") if fm.get("safety_mechanism_spf") else fm.get("dc_lf")
      lam = (c["failure_rate_fit"] or 0) * fm["distribution"]
      other = ", ".join(pg["goal"] for pg in fm.get("per_goal", []))
      L.append(f"| {fm['id']} | {c['id']} | {one(fm['mode'])} | {fm['distribution'] * 100:g} % | {fit(lam)} | "
               f"{badge.get(cls, '🟡 ' + cls if not mech else cls)} | {f'{mech} ({dc * 100:g} %)' if mech else '—'} | "
               f"{fm.get('dfmea_ref', '—')} | {other or '—'} |")
  L += ["", "<details><summary>Notes per failure mode</summary>", ""]
  for c in comps:
    for fm in c["failure_modes"]:
      if fm.get("notes"):
        L.append(f"- **{fm['id']}:** {one(fm['notes'])}")
  L += ["", "</details>", "", "## 4. Rows classified differently for another goal", ""]
  pgs = [(c, fm, pg) for c in comps for fm in c["failure_modes"] for pg in fm.get("per_goal", [])]
  if pgs:
    L += ["| Goal | Row | Own class | Class for the goal | Reason |", "|---|---|---|---|---|"]
    for c, fm, pg in pgs:
      L.append(f"| {pg['goal']} | {fm['id']} | {classify(fm)} | {classify(fmea_lint.fmeda_mode(fm, pg['goal']))} | {one(pg['reason'])} |")
  else:
    L.append("None: every row classifies the same for every target goal.")
  L += ["", "## 5. Safety mechanisms", "", "| ID | Mechanism | DC basis | Requirement | Credited on |", "|---|---|---|---|---|"]
  for sid, s in sms.items():
    on = [f"{fm['id']} ({(fm.get('dc_spf') if fm.get('safety_mechanism_spf') == sid else fm.get('dc_lf')) * 100:g} %)"
          for c in comps for fm in c["failure_modes"] if sid in (fm.get("safety_mechanism_spf"), fm.get("safety_mechanism_lf"))]
    L.append(f"| {sid} | {one(s['description'])} | {one(s['dc_basis'])} | {s.get('requirement', '—')} | {', '.join(on) or '—'} |")
  wb = export_fmeda_xlsx.build(doc, f"assurance/08-analyses/fmea/analyses/{name}.yaml")
  L += ["", "## 6. Open items", "", "From the workbook's `11_Open_Items` tab.", ""]
  for r in wb["11_Open_Items"].iter_rows(min_row=2, values_only=True):
    L.append(f"- **{r[0]}:** {one(r[1])}")
  L += ["", "## 7. Revision history", "", "| Revision | Date | Change |", "|---|---|---|"]
  for h in a.get("history", []):
    L.append(f"| {h['revision']} | {h['date']} | {one(h['change'])} |")
  L.append("")
  return "\n".join(L)


def build_all() -> dict[Path, str]:
  return {OUT / f"{n}.md": page(n, fmea_lint.load_yaml((ANALYSES / f"{n}.yaml").read_text())) for n in SOURCES}


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--check", action="store_true")
  args = ap.parse_args(argv)
  files = build_all()
  if args.check:
    stale = [p for p, t in files.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
    for p in stale:
      print(f"stale: {p.relative_to(ROOT)}; run {GENERATOR}", file=sys.stderr)
    if stale:
      return 1
    print(f"FMEDA review pages current ({len(files)} files)")
    return 0
  for p, t in files.items():
    p.write_text(t, encoding="utf-8")
  print(f"wrote {len(files)} FMEDA review page(s) under {OUT.relative_to(ROOT)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
