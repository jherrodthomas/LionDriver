#!/usr/bin/env python3
"""Build the technical safety concept workbook from tsc.json and the FSC.

tsc.json holds the analyst's content: the hardware and software architecture,
the safety mechanisms, the technical safety requirements with their status
and evidence, a disposition rule for every FSC requirement, the HSI, timing,
DFA and the G1 design. This script reuses the TSC generator's FSC reader,
styling and the tabs it builds well (title page, imported FSRs, architecture,
FMEA scaffold, draw.io export), and writes the analysis tabs from tsc.json,
because the generator's one-template-mechanism-per-FSR model does not fit a
design where one mechanism covers many requirements.

Usage:
    python build.py <tsc-builder scripts directory>
"""
import importlib.util
import json
import os
import sys
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
FSC = os.path.join(HERE, "..", "fsc", "LD-FSC-001_fsc.xlsx")
FSC_REL = "docs/safety/platform/fsc/LD-FSC-001_fsc.xlsx"
OUTPUT = os.path.join(HERE, "LD-TSC-001_tsc.xlsx")

FILLS = {
    "Existing": "C6EFCE",
    "Proposed": "FFF2CC",
    "To verify": "FCE4D6",
    "Open": "F8CBAD",
}


def load_generator(scripts_dir):
    path = os.path.join(scripts_dir, "generate_tsc.py")
    spec = importlib.util.spec_from_file_location("generate_tsc", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def status_fill(status):
    for key, color in FILLS.items():
        if status.startswith(key) or (key == "Existing" and status.startswith("Implemented")):
            return PatternFill("solid", fgColor=color)
    if "Independence argued" in status:
        return PatternFill("solid", fgColor=FILLS["Existing"])
    if "in progress" in status or status.startswith("Design proposed") or status.startswith("Drafted"):
        return PatternFill("solid", fgColor=FILLS["Proposed"])
    if status.startswith("New") or status.startswith("To argue"):
        return PatternFill("solid", fgColor=FILLS["Open"])
    return None


class Sheet:
    """Small helper around the generator's styling for the tabs written here."""

    def __init__(self, gen, wb, name, title, note, headers, widths):
        self.gen, self.ws = gen, wb.create_sheet(name)
        self.ws.sheet_view.showGridLines = False
        self.headers = headers
        gen.style_title_row(self.ws, 1, len(headers), title)
        if note:
            cell = self.ws.cell(row=2, column=1, value=note)
            cell.font = Font(name=gen.FONT_NAME, italic=True, size=10, color="9C5700")
            cell.fill = PatternFill("solid", fgColor=gen.WARN_YELLOW)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            self.ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
            self.ws.row_dimensions[2].height = 48
        gen.style_header_row(self.ws, 4, headers)
        gen.autosize(self.ws, {i + 1: w for i, w in enumerate(widths)})
        self.row = 5

    def add(self, values, status_col=None, asil_col=None):
        for col, value in enumerate(values, start=1):
            cell = self.ws.cell(row=self.row, column=col, value=value)
            cell.font = self.gen.body_font()
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = self.gen.BORDER_ALL
        if status_col:
            fill = status_fill(str(values[status_col - 1]))
            if fill:
                self.ws.cell(row=self.row, column=status_col).fill = fill
        if asil_col:
            self.gen.asil_color_cell(self.ws.cell(row=self.row, column=asil_col), values[asil_col - 1])
        self.row += 1

    def finish(self):
        self.ws.freeze_panes = "A5"
        if self.row > 5:
            last = self.gen.get_column_letter(len(self.headers))
            self.ws.auto_filter.ref = f"A4:{last}{self.row - 1}"


def dispose(fsrs, rules):
    """First matching rule per FSR. Every FSR must match exactly one rule."""
    out = {}
    for f in fsrs:
        for rule in rules:
            if f["sg_id"] in rule["goals"] and f["node_id"] in rule["nodes"]:
                out[f["fsr_id"]] = rule
                break
        else:
            raise SystemExit(f"No disposition rule for {f['fsr_id']} ({f['sg_id']} / {f['node_id']})")
    return out


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    gen = load_generator(sys.argv[1])
    with open(os.path.join(HERE, "tsc.json")) as fh:
        data = json.load(fh)

    fsc = gen.read_fsc(FSC)
    fsrs, nodes = fsc["fsrs"], fsc["nodes"]
    hw = data["architecture"]["hw_components"]
    sw = data["architecture"]["sw_partitions"]
    tsrs = {t["id"]: t for t in data["tsrs"]}

    disposition = dispose(fsrs, data["dispositions"])
    traced = defaultdict(list)
    for f in fsrs:
        for tsr_id in disposition[f["fsr_id"]]["tsrs"]:
            if tsr_id not in tsrs:
                raise SystemExit(f"Unknown TSR {tsr_id} in disposition of {f['fsr_id']}")
            traced[tsr_id].append(f["fsr_id"])

    wb = Workbook()
    wb.remove(wb.active)

    # 00 Title page
    gen.build_title_page(wb, fsc["item"], data["tsc_metadata"], FSC_REL)
    ws = wb["00_Title_Page"]
    extra = [
        ("Pinned sources", data["tsc_metadata"]["pinned_sources"]),
        ("Status", "Draft. Not released. Nothing in this workbook claims compliance."),
        ("Contents", f"{len(hw)} HW components, {len(sw)} SW partitions, {len(data['mechanisms'])} safety mechanisms, "
                     f"{len(tsrs)} TSRs, a disposition for all {len(fsrs)} FSC requirements, HSI, timing, FMEA scaffold, DFA, G1 design, open items."),
    ]
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=2).value == "Methodology":
            ws.cell(row=r, column=3, value="Mechanism-centred refinement: each FSC requirement gets a disposition (refined, covered, or not applicable) "
                                           "pointing at concrete TSRs; mechanisms and TSRs are tied to the pinned code; HSI, timing, FMEA scaffold "
                                           "and DFA follow ISO 26262-4 §6 and ISO 26262-9 §7.")
    row = ws.max_row + 1
    for label, value in extra:
        ws.cell(row=row, column=2, value=label).font = Font(name=gen.FONT_NAME, size=11, bold=True, color=gen.NAVY)
        cell = ws.cell(row=row, column=3, value=value)
        cell.font = gen.body_font()
        cell.alignment = Alignment(horizontal="left", wrap_text=True)
        row += 1

    # 01 Document control
    doc = Sheet(gen, wb, "01_Document_Control", "Document Control", None,
                ["Revision", "Date", "Author", "Description of change", "Approver"], [12, 14, 34, 70, 30])
    meta = data["tsc_metadata"]
    doc.add(["0.1", meta["date"], meta["author"],
             "First draft from FSC LD-FSC-001 0.1: architecture, mechanisms, TSRs, dispositions, HSI, timing, DFA, G1 design.",
             meta["approver"]])
    doc.finish()

    # 02 FSRs imported, with the TSC disposition of each
    gen.build_fsrs_imported(wb, fsrs, FSC_REL)
    ws = wb["02_FSRs_From_FSC"]
    for col, header in ((8, "TSC disposition"), (9, "TSRs")):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = gen.header_font()
        cell.fill = PatternFill("solid", fgColor=gen.NAVY)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = gen.BORDER_ALL
    for i, f in enumerate(fsrs, start=5):
        rule = disposition[f["fsr_id"]]
        for col, value in ((8, rule["disposition"]), (9, ", ".join(rule["tsrs"]) or "—")):
            cell = ws.cell(row=i, column=col, value=value)
            cell.font = gen.body_font()
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = gen.BORDER_ALL
        if rule["disposition"].startswith("Not applicable"):
            ws.cell(row=i, column=8).fill = PatternFill("solid", fgColor="EDEDED")
        elif "gap" in rule["disposition"].lower() or "G1" in rule["disposition"]:
            ws.cell(row=i, column=8).fill = PatternFill("solid", fgColor=FILLS["Proposed"])
        else:
            ws.cell(row=i, column=8).fill = PatternFill("solid", fgColor=FILLS["Existing"])
    ws.auto_filter.ref = f"A4:I{4 + len(fsrs)}"
    gen.autosize(ws, {8: 44, 9: 34})

    # 03 Architecture
    gen.build_architecture(wb, nodes, hw, sw)
    ws = wb["03_System_Architecture"]
    row = ws.max_row + 2
    for text in ["Corrections to the FSC"] + data["corrections_to_fsc"]:
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = Font(name=gen.FONT_NAME, size=10, bold=(text == "Corrections to the FSC"))
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
        ws.row_dimensions[row].height = 15 if text == "Corrections to the FSC" else 45
        row += 1

    # 04 Safety mechanisms
    sm = Sheet(gen, wb, "04_Safety_Mechanisms", "Safety Mechanisms",
               "One row per mechanism, with the architecture element that implements it. One mechanism usually covers many FSRs; the TSR catalog traces each requirement back. DC% stays TBD until the FMEDA (WP-HW-01) or fault injection gives a number.",
               ["ID", "Mechanism", "Type", "Element", "Nodes", "Detection", "Reaction", "DC% (target)", "Status", "Where"],
               [10, 44, 16, 12, 14, 30, 34, 20, 22, 36])
    for m in data["mechanisms"]:
        sm.add([m["id"], m["name"], m["type"], m["element"], ", ".join(m["nodes"]), m["detection"], m["reaction"],
                m["dc"], m["status"], m["where"]], status_col=9)
    sm.finish()

    # 05 TSR catalog
    tc = Sheet(gen, wb, "05_TSR_Catalog", "Technical Safety Requirements (TSRs)",
               "Concrete requirements tied to the pinned panda, opendbc and openpilot code. Status: Existing upstream = implemented today; Proposed = new work, mostly G1; To verify = implemented or assumed but unproven. 'Traces to' lists every FSC requirement whose disposition cites the TSR.",
               ["TSR_ID", "Type", "Element", "ASIL", "Mechanism", "Technical safety requirement", "Status",
                "Implementation / location", "Traces to FSRs", "Verification (++ methods)"],
               [13, 7, 12, 10, 11, 70, 22, 38, 30, 32])
    for t in data["tsrs"]:
        base = gen.asil_base(t["asil"])
        fsr_list = traced.get(t["id"], [])
        trace = f"{len(fsr_list)}: " + ", ".join(fsr_list) if fsr_list else "—"
        tc.add([t["id"], t["type"], t["element"], t["asil"], t["mechanism"], t["text"], t["status"], t["where"],
                trace, ", ".join(gen.VERIFICATION_PLUS_PLUS.get(base, []))], status_col=7, asil_col=4)
    tc.finish()

    # 06 HSI
    hs = Sheet(gen, wb, "06_HSI_Specification", "Hardware-Software Interface (HSI)",
               "Signals across the device-to-panda link, the panda's health report, and the MCU's own safety hardware. Signal names follow <subsystem>.<role>.<signal>.",
               ["HSI signal", "Direction", "Encoding", "Rate", "Integrity", "Reaction", "TSRs", "Status"],
               [36, 18, 38, 24, 30, 40, 22, 18])
    for h in data["hsi"]:
        hs.add([h["signal"], h["direction"], h["encoding"], h["rate"], h["integrity"], h["reaction"], h["tsrs"], h["status"]],
               status_col=8)
    hs.finish()

    # 07 Timing
    tb = Sheet(gen, wb, "07_Timing_Budget", "Timing Budget: FTTI ≥ FDTI + FRTI",
               "FTTIs are not set yet (gap G2), so FTTI is TBD for every goal. This tab records each mechanism's detection (FDTI) and reaction (FRTI) time from the code, so the FTTI measurement can be checked against them as soon as it exists.",
               ["Mechanism", "FTTI", "FDTI", "FRTI", "Notes"], [26, 10, 34, 30, 60])
    for t in data["timing"]:
        tb.add([t["mechanism"], "TBD (G2)", t["fdti"], t["frti"], t["notes"]])
    tb.finish()

    # 08 System FMEA: generator scaffold, existing mechanisms filled per node
    gen.build_system_fmea(wb, nodes, fsc["allocations"])
    ws = wb["08_System_FMEA"]
    by_node = data["fmea_mechanisms_by_node"]
    for r in range(5, ws.max_row + 1):
        node_cell = ws.cell(row=r, column=1).value
        if node_cell:
            node_id = str(node_cell).split(" — ")[0]
            if node_id in by_node:
                ws.cell(row=r, column=7, value=by_node[node_id])

    # 09 DFA
    dfa = data["dfa"]
    df = Sheet(gen, wb, "09_DFA", "Dependent Failure Analysis (DFA)",
               f"Pair: {dfa['pair']}. Conclusion: {dfa['conclusion']}",
               ["Coupling factor", "Present?", "Mitigation / argument", "Status"], [30, 42, 80, 24])
    for d in dfa["rows"]:
        df.add([d["factor"], d["present"], d["mitigation"], d["status"]], status_col=4)
    df.finish()

    # 10 Verification
    ve = Sheet(gen, wb, "10_Verification", "Verification Specification",
               "Verification methods recommended (++) for the allocated ASIL (ISO 26262-4 Table 3) and the confirmation review independence it requires (ISO 26262-2 Table 1). LionDriver evidence already available is listed where it exists.",
               ["TSR_ID", "ASIL", "Recommended methods (++)", "Independence", "Evidence available"], [13, 10, 56, 14, 60])
    evidence = {
        "TSR-LIM-01": "opendbc safety unit tests and mutation tests; Toyota: XZACT equivalence 72/72 traces, 30/30 mutations killed",
        "TSR-LIM-03": "opendbc safety unit tests; Toyota: XZACT equivalence",
        "TSR-LON-01": "opendbc safety unit tests; Toyota: XZACT equivalence",
        "TSR-ENG-01": "opendbc safety unit tests; Toyota: XZACT equivalence",
        "TSR-ENG-02": "opendbc safety unit tests; Toyota: XZACT equivalence",
        "TSR-RX-01": "opendbc safety unit tests; Toyota: XZACT equivalence",
        "TSR-TX-01": "opendbc safety unit tests; Toyota: XZACT equivalence",
        "TSR-RLY-01": "opendbc safety unit tests; Toyota: XZACT equivalence",
    }
    for t in data["tsrs"]:
        base = gen.asil_base(t["asil"])
        independence = {"D": "I3", "C": "I2", "B": "I1", "A": "I0"}.get(base, "—")
        ve.add([t["id"], t["asil"], ", ".join(gen.VERIFICATION_PLUS_PLUS.get(base, [])), independence,
                evidence.get(t["id"], "None yet")], asil_col=2)
    ve.finish()

    # 11 / 12 Hand-offs
    for name, title, kind, part in (("11_HW_Handoff", "HW Hand-off (to ISO 26262-5)", "HW", "FMEDA and hardware metrics (SPFM, LFM, PMHF)"),
                                    ("12_SW_Handoff", "SW Hand-off (to ISO 26262-6)", "SW", "software safety requirements, unit design and unit verification")):
        ho = Sheet(gen, wb, name, title,
                   f"{kind} TSRs handed to the {kind} work ({part}). Requirements marked Proposed are new work; Existing upstream ones still need LionDriver verification evidence.",
                   ["TSR_ID", "Element", "ASIL", "Mechanism", "Requirement", "Status", "Owner"], [13, 12, 10, 11, 70, 22, 16])
        for t in data["tsrs"]:
            if t["type"] == kind:
                ho.add([t["id"], t["element"], t["asil"], t["mechanism"], t["text"], t["status"], "TBD (role vacant)"],
                       status_col=6, asil_col=3)
        ho.finish()

    # 13 G1 design
    g1 = data["g1"]
    gd = Sheet(gen, wb, "13_G1_MCU_Faults", f"G1: {g1['title']}", g1["decision_rule"],
               ["Item", "Content", "Status", "TSRs"], [16, 100, 30, 40])
    for i, text in enumerate(g1["finding"], start=1):
        gd.add([f"Finding {i}", text, "", ""])
    for layer in g1["layers"]:
        gd.add([f"{layer['id']}: {layer['name']}", layer["summary"], layer["status"], ", ".join(layer["tsrs"]) or "—"], status_col=3)
    gd.finish()

    # 14 Open items
    oi = Sheet(gen, wb, "14_Open_Items", "Open Items", "Gaps carried from the FSC (G1–G5) and found in the TSC (T1, T2).",
               ["ID", "Gap", "Status", "Next step"], [8, 50, 50, 70])
    for g in data["gaps"]:
        oi.add([g["id"], g["title"], g["status"], g["next"]], status_col=3)
    oi.finish()

    wb.active = 0
    wb.save(OUTPUT)
    drawio = os.path.join(HERE, "LD-TSC-001_architecture.drawio")
    gen.write_drawio(nodes, hw, sw, drawio)

    counts = defaultdict(int)
    for rule in disposition.values():
        counts["not applicable" if rule["disposition"].startswith("Not applicable")
               else "covered" if rule["disposition"].startswith("Covered") else "refined"] += 1
    print(json.dumps({
        "fsrs": len(fsrs), "dispositions": dict(counts), "tsrs": len(tsrs),
        "tsr_status": {s: sum(1 for t in data["tsrs"] if t["status"].startswith(s)) for s in ("Existing", "Proposed", "To verify")},
        "untraced_tsrs": [t for t in tsrs if t not in traced],
        "output": os.path.relpath(OUTPUT, ROOT),
    }, indent=2))


if __name__ == "__main__":
    main()
