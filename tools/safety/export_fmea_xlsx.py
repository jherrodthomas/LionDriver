#!/usr/bin/env python3
"""Export the SW FMEA or the DFMEA YAML to an xlsx workbook with the automotive-skills-suite builders.

Usage:
  tools/safety/export_fmea_xlsx.py sw    --generator <sw-fmea-builder>/scripts/generate_sw_fmea.py [OUTPUT.xlsx]
  tools/safety/export_fmea_xlsx.py dfmea --generator <dfmea-builder>/scripts/generate_dfmea.py   [OUTPUT.xlsx]

The YAML (assurance/08-analyses/fmea/analyses/) stays the source of truth; regenerate rather than editing the
xlsx. One worksheet row per cause, since the builders expect one cause per row.

Two deviations from running the builders directly, both so the workbook matches the YAML:
- Action priority uses the AIAG-VDA table of rating-tables.md (fmea_lint.compute_ap). The builders use a
  simplified rule in which any S >= 9 is High, which disagrees with the table (e.g. S10 O3 D4 is L).
  Do not run the builders' recalc.py on these workbooks: it would restore the simplified rule.
- The document-control tab lists this analysis's revision history instead of the builders' placeholder rows, and the
  references, lessons-learned and (DFMEA) special-characteristics tabs carry project content instead of placeholders.

Requires PyYAML, jsonschema and openpyxl.
"""
import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint

ANALYSES = Path("assurance/08-analyses/fmea/analyses")
EXPORTS = Path("assurance/08-analyses/fmea/exports")
SOURCES = {"sw": ANALYSES / "sw-fmea.yaml", "dfmea": ANALYSES / "dfmea.yaml"}
DEFAULT_OUT = {"sw": EXPORTS / "sw-fmea.xlsx", "dfmea": EXPORTS / "dfmea.xlsx"}

SW_GUIDEWORDS = {
  "omission": "Omitted Function", "commission": "Unintended Function", "early": "Function Too Early",
  "late": "Function Too Late", "value_high": "Incorrect Function", "value_low": "Incorrect Function",
  "value_stale": "Wrong Data Used", "value_frozen": "Wrong Data Used", "corrupted": "Wrong Data Used",
  "out_of_sequence": "Wrong Sequence", "wrong_mode": "Wrong Interface Behavior", "crash": "Omitted Function",
  "hang": "Omitted Function", "resource_exhaustion": "Omitted Function",
}
LEVELS = {"item": "System", "system": "System", "subsystem": "Subsystem", "component": "Component", "interface": "Component",
          "sw_element": "Component", "sw_unit": "Unit"}


# Lessons learned / cross-reference rows: (document, failure modes, lesson applied, notes)
CROSSREF = {
  "sw": [
    ("assurance WP-W-04 v0.2 (software safety analysis of record)", "All rows",
     "This workbook adds AIAG-VDA ratings to the WP-W-04 rows", "Mapping in WP-W-04 §3.5"),
    ("SW FMEA rev 0.2/0.3 at BL-001", "SWF-001, 006, 008, 013, 014, 015",
     "Re-rated at BL-002 after the RX timeout, grant check, watchdog and mode lock changes", "Header comment of sw-fmea.yaml"),
    ("Impact analyses change-2026-10-12-*", "SWF-006, 007, 011, 013, 018, 019", "Behaviour changes of the BL-002 firmware", "assurance/07-supporting/impact/"),
    ("WP-A-03 DFI-08 (identical limits in controller and envelope)", "SWF-001.C1, SWF-003.C1",
     "Mutation testing cannot find wrong limit values", "Needs an independent envelope derivation"),
  ],
  "dfmea": [
    ("assurance WP-H-03 qualitative FMEDA", "All rows",
     "Block-level failure modes and diagnostic coverage reused as DFMEA causes", "FM-xxx IDs cited in each row's notes"),
    ("assurance WP-H-02 hardware design", "All rows", "Observable design facts and unknowns UK-01..UK-09", "No schematic or BOM available"),
    ("assurance WP-A-03 DFA", "DFM-007, 012, 017, 018", "Common-cause initiators shared with the SoC, EPS and PCM", "DFI-01, -04, -06, -20, -23"),
    ("SW FMEA SWF-018/019", "DFM-004, DFM-006", "Watchdog failure modes seen from the software side", "sw-fmea.xlsx"),
  ],
}

# Candidate special characteristics. LionDriver does not own the comma 3X design, so these are characteristics it must
# verify or control at integration and installation, not drawing characteristics.
SPECIAL_CHARACTERISTICS = [
  ("Relay contact state when de-energised connects camera to car (stock path)", "Candidate SC (safety)",
   "DFM-010, DFM-011, DFM-013", "Harness continuity test (UK-03); relay readback (DFM-ACT-007)"),
  ("MCU option bytes: BOR level, RDP/WRP", "Candidate SC (safety, security)", "DFM-007, DFM-016", "Provisioning procedure with read-back (DFM-ACT-005, -010)"),
  ("IWDG timeout and window vs LSI tolerance", "Candidate SC (safety)", "DFM-004, DFM-006", "Datasheet LSI range; HIL test (DFM-ACT-003)"),
  ("Harness connector fully latched", "Candidate SC (safety)", "DFM-012", "Installation check (DFM-ACT-008)"),
  ("Firmware built with RELEASE=1 LIONDRIVER_REFERENCE=1", "Candidate SC (safety)", "SW FMEA SWF-013.C2", "Release procedure (SWF-ACT-009)"),
]


def _join(controls: list[dict]) -> str:
  return "; ".join(c["description"] + (f" [{c['test']}]" if c.get("test") else "") for c in controls)


def _asil(fsr_asils: list[str]) -> str:
  order = ["QM", "A", "B", "C", "D"]
  letters = [a.split("(")[0] for a in fsr_asils]
  return max(letters, key=order.index) if letters else ""


def _history(hdr: dict, doc: dict) -> list[tuple]:
  rows = [(h["revision"], str(h.get("date", "")), h.get("author", ""), h.get("change", ""), "")
          for h in hdr.get("history", [])]
  if not rows:
    rows = [(hdr["revision"], str(hdr.get("updated", "")), "Claude (AI-assisted draft)",
             f"{hdr['status']} at {hdr['baseline']}; see the header comment of the YAML source for earlier revisions", "")]
  return rows


def to_builder_json(kind: str, doc: dict, fsc: dict | None) -> dict:
  hdr = doc["analysis"]
  fsrs = {f["id"]: f for f in (fsc or {}).get("fsrs", [])}
  actions = {a["id"]: a for a in doc["actions"]}
  team = ", ".join(m["name"] for m in hdr.get("team", []))
  program = {
    "name": hdr["title"], "doc_id": f"LD-{hdr['id']}-001", "revision": hdr["revision"], "date": str(hdr.get("updated", "")),
    "fmea_team": team, "customer": "LionDriver (owner-installed)", "company": "LionDriver", "model_year": "2020",
  }
  if kind == "sw":
    program.update(item_name="Panda safety model (opendbc safety + panda firmware)", item_id=hdr["id"], asil="D (FSC; see HARA OI-1)",
                   safety_goal="SG-001..SG-010 (LD-HARA-001)", sw_owner="Jherrod Thomas")
  else:
    program.update(part_name="comma 3X panda section, Toyota harness and relay box", part_number="comma 3X / Toyota A harness",
                   design_owner="Jherrod Thomas (integrator; comma.ai design)", design_responsibility="comma.ai (COTS)")

  structure = [{"id": e["id"], "level": LEVELS.get(e["kind"], "Component"), "name": e["name"], "parent": e.get("parent")}
               for e in doc["structure"]]
  functions = []
  for f in doc["functions"]:
    reqs = f.get("requirements", [])
    functions.append({"id": f["id"], "parent_id": f["element"], "function_statement": f["description"],
                      "requirement_ref": ", ".join(reqs), "asil": _asil([fsrs[r]["asil"] for r in reqs if r in fsrs])})
  fn_safe_state = {f["id"]: "; ".join(dict.fromkeys(fsrs[r]["safe_state"].rstrip(".") for r in f.get("requirements", []) if r in fsrs))
                   for f in doc["functions"]}
  fn_asil = {f["id"]: f["asil"] for f in functions}

  rows = []
  for fm in doc["failure_modes"]:
    eff = {e["level"]: e for e in fm["effects"]}
    ends = "; ".join(e["description"] + (f" ({e['hazard']})" if e.get("hazard") else "") for e in fm["effects"] if e["level"] == "end")
    mechanisms = _join(fm.get("safety_mechanisms", []))
    for c in fm["causes"]:
      acts = [actions[a] for a in c.get("actions", [])]
      row = {
        "id": c["id"], "function_id": fm["function"], "failure_mode": fm["failure_mode"], "severity": fm["severity"],
        "failure_cause": c["description"], "occurrence": c["occurrence"], "detection": c["detection"],
        "prevention_control": _join(c["prevention_controls"]), "detection_control": _join(c["detection_controls"]),
        "recommended_action": "; ".join(f"{a['id']} ({a['status']}): {a['description']}" for a in acts) or c.get("rationale", ""),
        "owner": ", ".join(dict.fromkeys(a.get("owner", "") for a in acts)), "target_date": "",
      }
      if kind == "sw":
        row.update(element_id=c.get("element", fm["element"]), guide_word=SW_GUIDEWORDS.get(fm["guideword"], fm["guideword"]),
                   local_effect=eff["local"]["description"], system_effect=eff["next_higher"]["description"], vehicle_effect=ends,
                   safety_mechanism=mechanisms or "None recorded", safe_state=fn_safe_state.get(fm["function"], ""),
                   asil=fn_asil.get(fm["function"], ""))
      else:
        row.update(focus_element_id=c.get("element", fm["element"]),
                   failure_effect_next=f"{eff['local']['description']}; {eff['next_higher']['description']}",
                   failure_effect_user=ends + (f". In-field mechanism: {mechanisms}" if mechanisms else ""))
      rows.append(row)
  refs = [("AIAG-VDA FMEA Handbook 2019", "Method; Action Priority per the table in rating-tables.md"),
          ("ISO 26262-6:2018 §7, ISO 26262-9:2018 §8" if kind == "sw" else "ISO 26262-5:2018 §7, ISO 26262-9:2018 §7-8", "Safety analyses")]
  refs += [(r, "Project document") for r in hdr.get("references", [])]
  refs.append((str(SOURCES[kind]), "Source of truth for this workbook (YAML); checked by tools/safety/fmea_lint.py"))
  return {"program": program, "structure": structure, "functions": functions, "failure_modes": rows, "_history": _history(hdr, doc),
          "_refs": refs, "_crossref": CROSSREF[kind], "_sc": SPECIAL_CHARACTERISTICS if kind == "dfmea" else None}


def load_generator(path: Path, history: list[tuple], extras: dict):
  spec = importlib.util.spec_from_file_location("fmea_builder", path)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  mod.compute_ap = fmea_lint.compute_ap

  def build_doc_control(wb):
    ws = wb.create_sheet("01_Document_Control")
    ws.sheet_view.showGridLines = False
    mod.style_title_row(ws, 1, 5, "Document Control")
    mod.style_header_row(ws, 3, ["Revision", "Date", "Author", "Description of change", "Approver"])
    for i, rd in enumerate(history, start=4):
      for c, v in enumerate(rd, start=1):
        ws.cell(row=i, column=c, value=v)
    mod.stripe_body(ws, 4, 3 + len(history), 5)
    mod.autosize(ws, {1: 12, 2: 14, 3: 26, 4: 70, 5: 22})

  def table_tab(name, title, headers, rows, widths):
    def build(wb):
      ws = wb.create_sheet(name)
      ws.sheet_view.showGridLines = False
      mod.style_title_row(ws, 1, len(headers), title)
      mod.style_header_row(ws, 3, headers)
      for i, rd in enumerate(rows, start=4):
        for c, v in enumerate(rd, start=1):
          ws.cell(row=i, column=c, value=v)
      if rows:
        mod.stripe_body(ws, 4, 3 + len(rows), len(headers))
      mod.autosize(ws, widths)
    return build

  mod.build_doc_control = build_doc_control
  sw = hasattr(mod, "build_catalog")
  xref = table_tab("11_Lessons_Learned_Crossref" if sw else "10_Lessons_Learned_Crossref", "Lessons Learned & Cross-Reference",
                   ["Document", "Relevant failure modes", "Lesson applied", "Notes"], extras["crossref"], {1: 44, 2: 30, 3: 50, 4: 36})
  refs = table_tab("12_References" if sw else "11_References", "References & Methodology", ["Reference", "Use"], extras["refs"], {1: 70, 2: 60})
  if sw:
    mod.build_lessons = xref
  else:
    mod.build_lessons_learned = xref
    mod.build_special_characteristics = table_tab("06_Special_Characteristics", "Special Characteristics (candidates at integration)",
                                                  ["Characteristic", "Classification", "Source FM ID", "Recommended controls"],
                                                  extras["sc"], {1: 50, 2: 26, 3: 26, 4: 50})
  mod.build_references = refs
  return mod


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("kind", choices=["sw", "dfmea"])
  ap.add_argument("output", nargs="?", type=Path)
  ap.add_argument("--generator", type=Path, required=True, help="path to generate_sw_fmea.py or generate_dfmea.py")
  ap.add_argument("--root", type=Path, default=Path("."))
  args = ap.parse_args(argv)

  root = args.root
  doc = fmea_lint.load_yaml((root / SOURCES[args.kind]).read_text())
  fsc_path = root / ANALYSES / "fsc.yaml"
  fsc = fmea_lint.load_yaml(fsc_path.read_text()) if fsc_path.exists() else None
  data = to_builder_json(args.kind, doc, fsc)
  history = data.pop("_history")
  extras = {"refs": data.pop("_refs"), "crossref": data.pop("_crossref"), "sc": data.pop("_sc")}

  out = args.output or (root / DEFAULT_OUT[args.kind])
  out.parent.mkdir(parents=True, exist_ok=True)
  mod = load_generator(args.generator, history, extras)
  with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump(data, f)
  result = mod.generate(f.name, str(out))
  Path(f.name).unlink()
  print(json.dumps(result, indent=2))
  return 0


if __name__ == "__main__":
  sys.exit(main())
