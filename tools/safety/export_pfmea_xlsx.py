#!/usr/bin/env python3
"""Export the PFMEA YAML (assurance/08-analyses/fmea/analyses/pfmea.yaml) with the pfmea-builder layout.

Usage: tools/safety/export_pfmea_xlsx.py --generator <pfmea-builder>/scripts/generate_pfmea.py [OUTPUT.xlsx]

Deviations from running the builder directly, so the workbook matches the YAML:
- The builder script ends in NUL bytes that Python refuses to load; a cleaned copy is loaded from a temporary file.
- Action priority uses the AIAG-VDA table of rating-tables.md (fmea_lint.compute_ap). The builder's get_ap is an
  S x O score in which a better detection rating raises the priority, which is inverted.
- The document control, header block, special characteristics, action plan, control-plan linkage, lessons-learned
  and references tabs carry project content instead of the builder's sample electronics-manufacturing rows.
Do not run the builder's recalc.py on these workbooks.

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
from export_fmea_xlsx import STATUS, _history, _join, _row_status

SOURCE = Path("assurance/08-analyses/fmea/analyses/pfmea.yaml")
DEFAULT_OUT = Path("assurance/08-analyses/fmea/exports/pfmea.xlsx")
O01 = "assurance/09-production-operation/WP-O-01-installation-and-provisioning-control.md"

# Special characteristics of the installation, from WP-O-01 §4, with the PFMEA rows they control
SPECIAL_CHARACTERISTICS = [
  ("SPC-01 Harness connector seating and pin integrity", "SC (safety)", "PFM-SE-020, PFM-SE-022",
   "INS-03, INS-11: visual and pull check", "No canBusMissing/canError at INS-14", "PFM-006, PFM-008"),
  ("SPC-02 Relay intercept function", "SC (safety)", "PFM-SE-025", "INS-27 log review", "relayMalfunction absent", "PFM-014"),
  ("SPC-03 Device mount position and attitude", "SC (SOTIF)", "PFM-SE-022, PFM-SE-025",
   "INS-09 photo, INS-25 calibration angles", "Within tolerance band (WP-O-01 OI-2)", "PFM-009"),
  ("SPC-04 Software baseline identity", "SC (safety)", "PFM-SE-023", "INS-15, INS-16, INS-18", "Equal to release record", "PFM-005, PFM-012"),
  ("SPC-05 Panda firmware identity (release build, signature)", "SC (safety)", "PFM-SE-023",
   "INS-17", "Version and signature equal to release record", "PFM-001, PFM-002"),
  ("SPC-06 Safety mode and safety parameter", "SC (safety)", "PFM-SE-024", "INS-22, INS-23", "toyota / 73 / alternative experience 0", "PFM-013"),
  ("SPC-07 Vehicle ECU firmware versions", "SC (safety)", "PFM-SE-021, PFM-SE-024", "INS-21 exact FW compare", "Identical to reference record", "PFM-007"),
  ("SPC-08 Vehicle health", "SC (safety)", "PFM-SE-021", "INS-06, INS-07 scan tool", "No active DTC, unmodified chassis", "PFM-007"),
  ("SPC-09 Parameter set", "SC (SOTIF, CS)", "PFM-SE-023", "INS-19 parameter dump", "Equal to release values", "PFM-011"),
]

# Control-plan linkage: PFMEA row -> installation or release step that controls it
CONTROL_STEPS = {
  "PFM-001": ("SPC-05", "INS-17; WP-P-10 §6 release check", "Version contains RELEASE; signature = release record"),
  "PFM-002": ("SPC-05", "INS-17; WP-P-10 §6", "Signature = LionDriver key"),
  "PFM-003": ("SPC-04", "WP-P-10 §4 step 2 freeze; CI safety workflow", "Pins = baseline manifest; CI green"),
  "PFM-004": ("—", "WP-P-10 §3 gate criteria, §5 evidence package", "Evidence complete before release decision"),
  "PFM-005": ("SPC-04", "INS-15", "Installed commit = release tag commit"),
  "PFM-006": ("SPC-01", "INS-02, INS-03", "Approved harness, no damage"),
  "PFM-007": ("SPC-07, SPC-08", "INS-05..08, INS-21", "Reference vehicle, no DTC"),
  "PFM-008": ("SPC-01", "INS-11, INS-14", "Latches engaged; no CAN alert"),
  "PFM-009": ("SPC-03", "INS-09, INS-25", "Pose within tolerance band"),
  "PFM-010": ("—", "INS-12", "Airbag zones clear"),
  "PFM-011": ("SPC-09", "INS-19", "Parameter dump = release record"),
  "PFM-012": ("SPC-04", "INS-18", "Model hashes = release record"),
  "PFM-013": ("SPC-06", "INS-22, INS-23, INS-24", "carParams and pandaStates as specified"),
  "PFM-014": ("SPC-02", "INS-27", "PCS forwarded, intercepted messages blocked"),
  "PFM-015": ("—", "INS-30", "Signed acknowledgement"),
  "PFM-016": ("SPC-04", "WP-P-10 §8; WP-O-02", "Only approved releases installed"),
  "PFM-017": ("SPC-04, SPC-05", "WP-P-10 §8; WP-O-02", "Rollback target valid for installed panda firmware"),
}


def to_pfmea_json(doc: dict, fsc: dict | None) -> dict:
  hdr = doc["analysis"]
  del fsc  # requirements are listed by ID only
  actions = {a["id"]: a for a in doc["actions"]}
  steps = [e for e in doc["structure"] if e["kind"] == "process_step"]
  names = {e["id"]: e["name"] for e in doc["structure"]}
  fn_by_step = {f["element"]: f for f in doc["functions"]}
  program = {"name": hdr["title"], "process_name": "Release, installation and update of the LionDriver reference configuration (AC-001)",
             "process_responsibility": "Jherrod Thomas (project maintainer)", "model_year": "2020", "doc_id": f"LD-{hdr['id']}-001",
             "revision": hdr["revision"], "date": str(hdr.get("updated", "")), "fmea_owner": "Jherrod Thomas",
             "fmea_team": ", ".join(m["name"] for m in hdr.get("team", [])), "customer": "LionDriver users (owner-installed)", "company": "LionDriver"}
  flow = []
  for i, e in enumerate(steps):
    kind = "Inspection" if "inspection" in e["name"].lower() or "check" in e["name"].lower() else "Operation"
    flow.append({"step_id": e["id"], "step_name": e["name"], "step_type": kind,
                 "upstream_step": steps[i - 1]["id"] if i else "Start", "downstream_step": steps[i + 1]["id"] if i + 1 < len(steps) else "Vehicle operation",
                 "equipment": "", "key_characteristics": ", ".join(sc[0].split(" ", 1)[0] for sc in SPECIAL_CHARACTERISTICS if e["id"] in sc[2]),
                 "key_parameters": ""})
  funcs = []
  for e in steps:
    f = fn_by_step.get(e["id"])
    if f:
      scs = [sc[0] for sc in SPECIAL_CHARACTERISTICS if e["id"] in sc[2]]
      funcs.append({"step_id": e["id"], "function": f["description"], "requirement": ", ".join(f.get("requirements", [])),
                    "characteristic": "; ".join(scs) or "—", "special_characteristic": "SC" if scs else ""})
  rows = []
  for fm in doc["failure_modes"]:
    eff = {e["level"]: e for e in fm["effects"]}
    ends = "; ".join(e["description"] + (f" ({e['hazard']})" if e.get("hazard") else "") for e in fm["effects"] if e["level"] == "end")
    for c in fm["causes"]:
      acts = [actions[a] for a in c.get("actions", [])]
      rows.append({
        "step_id": c.get("element", fm["element"]), "process_step": names[c.get("element", fm["element"])],
        "process_function": fn_by_step[fm["element"]]["description"] if fm["element"] in fn_by_step else "",
        "failure_mode": f"[{fm['id']}] {fm['failure_mode']}",
        "failure_effect_next_op": f"{eff['local']['description']}; {eff['next_higher']['description']}", "failure_effect_end_user": ends,
        "severity": fm["severity"], "failure_cause": f"[{c['id']}] {c['description']}", "occurrence": c["occurrence"],
        "prevention_control": _join(c["prevention_controls"]), "detection_control": _join(c["detection_controls"]), "detection": c["detection"],
        "recommended_action": "; ".join(f"{a['id']}: {a['description']}" for a in acts) or c.get("rationale", ""),
        "owner": ", ".join(dict.fromkeys(a.get("owner", "") for a in acts)), "target_date": "", "status": _row_status(acts)})
  return {"program": program, "process_flow": flow, "process_functions": funcs, "failure_modes": rows}


def load_generator(path: Path, doc: dict):
  src = path.read_bytes().replace(b"\x00", b"")
  tmp = Path(tempfile.mkdtemp()) / "generate_pfmea_clean.py"
  tmp.write_bytes(src)
  spec = importlib.util.spec_from_file_location("pfmea_builder", tmp)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  mod.get_ap = fmea_lint.compute_ap
  hdr = doc["analysis"]

  def table(name, index, headers, rows, widths):
    def build(wb, *_):
      ws = wb.create_sheet(name, index)
      mod.style_header_row(ws, 1, headers)
      for r, rd in enumerate(rows, start=2):
        for c, v in enumerate(rd, start=1):
          mod.style_body_cell(ws.cell(row=r, column=c, value=v), is_alt_row=(r % 2 == 0))
      for i, w in enumerate(widths, start=1):
        ws.column_dimensions[mod.get_column_letter(i)].width = w
    return build

  hist = [(r[0], r[1], r[2], r[3]) for r in _history(hdr, doc)]
  mod.make_document_control = table("01_Document_Control", 1, ["Revision", "Date", "Author", "Change Summary"],
                                    [("0.1", "2026-10-10", "Claude (AI-assisted draft)", "Stub (no content)")] + hist, [12, 14, 26, 70])
  mod.make_header_block = table("02_Header_Block", 2, ["Field", "Value"], [
    ("System / component", "LionDriver L2 ACC/ALC item, reference configuration AC-001"),
    ("Process steps analyzed", "Release (WP-P-10), installation and provisioning (WP-O-01), update and rollback"),
    ("Process flow chart", "03_Process_Flow; WP-O-01 §3; WP-P-10 §4"), ("Prep date", str(hdr.get("updated", ""))),
    ("FMEA review date", "Not reviewed"), ("Responsible function", "Project maintainer"), ("Baseline", hdr["baseline"]),
    ("FMEA ID", f"LD-{hdr['id']}-001"), ("Status", hdr["status"].title())], [35, 90])
  mod.make_special_characteristics = table("06_Special_Characteristics", 6,
                                           ["Characteristic", "Classification", "Source Step", "Recommended Control Method", "Monitoring Plan", "PFMEA rows"],
                                           SPECIAL_CHARACTERISTICS, [44, 18, 24, 36, 36, 18])
  mod.make_action_plan_tracker = table("08_Action_Plan_Tracker", 8,
                                       ["Action ID", "Description", "Owner", "Target Date", "Status", "% Complete", "Completion Date"],
                                       [(a["id"], a["description"], a.get("owner", ""), a.get("due", ""), STATUS[a["status"]], "", "") for a in doc["actions"]],
                                       [14, 90, 16, 12, 14, 10, 14])
  link_rows = []
  for fm in doc["failure_modes"]:
    sc, method, acc = CONTROL_STEPS.get(fm["id"], ("—", "—", "—"))
    link_rows.append((fm["id"], fm["failure_mode"], sc, method, acc))
  mod.make_linkage_to_control_plan = table("10_Linkage_to_Control_Plan", 10,
                                           ["PFMEA Step ID", "Failure Mode", "Control Plan Characteristic", "Control Method", "Acceptance Criteria"],
                                           link_rows, [12, 60, 18, 40, 40])
  mod.make_lessons_learned = table("11_Lessons_Learned_Crossref", 11,
                                   ["Reference Source", "Relevant Failure Mode", "Lessons Learned", "Application to Current PFMEA"], [
    ("Upstream release process (WP-P-10 §2)", "PFM-001, PFM-002", "comma's release build uses comma's key and devices",
     "LionDriver key and release check (PFM-ACT-001, -002)"),
    ("SW FMEA SWF-013.C2", "PFM-001", "Reference lock exists only in a LIONDRIVER_REFERENCE build", "Release build flag is a special characteristic"),
    ("STPA WP-A-05 LS-02, LS-03", "PFM-015", "Driver process model drives override and Chill Mode misuse", "Briefing content (PFM-ACT-010)")],
    [36, 22, 50, 50])
  mod.make_references = table("12_References", 12, ["Reference", "Use"],
                              [("AIAG-VDA FMEA Handbook 2019", "Method; AP per rating-tables.md")]
                              + [(r, "Project document") for r in hdr.get("references", [])]
                              + [(str(SOURCE), "Source of truth (YAML), checked by tools/safety/fmea_lint.py")], [80, 50])
  return mod


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("output", nargs="?", type=Path)
  ap.add_argument("--generator", type=Path, required=True, help="path to pfmea-builder/scripts/generate_pfmea.py")
  ap.add_argument("--root", type=Path, default=Path("."))
  args = ap.parse_args(argv)
  doc = fmea_lint.load_yaml((args.root / SOURCE).read_text())
  fsc_path = args.root / "assurance/08-analyses/fmea/analyses/fsc.yaml"
  data = to_pfmea_json(doc, fmea_lint.load_yaml(fsc_path.read_text()) if fsc_path.exists() else None)
  out = args.output or (args.root / DEFAULT_OUT)
  out.parent.mkdir(parents=True, exist_ok=True)
  mod = load_generator(args.generator, doc)
  with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump(data, f)
  sys.argv = ["generate_pfmea.py", f.name, str(out)]
  mod.main()
  Path(f.name).unlink()
  aps = [fmea_lint.compute_ap(r["severity"], r["occurrence"], r["detection"]) for r in data["failure_modes"]]
  print(json.dumps({"output_path": str(out), "rows": len(aps), "ap": {k: aps.count(k) for k in "HML"}}))
  return 0


if __name__ == "__main__":
  sys.exit(main())
