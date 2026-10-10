#!/usr/bin/env python3
"""Build the functional safety concept workbook from fsc.json and the HARA.

fsc.json holds the analyst's content: the architecture as block-diagram nodes,
the concrete functional safety requirements (keyed by safety goal and node,
each with its implementation status and evidence), and the proposed ASIL
decomposition. The FSC generator expands every safety goal into a fault tree
with one basic event and one requirement per architecture node. This script

  1. maps the concrete requirements onto the generator's basic-event codes,
  2. runs the generator against the HARA workbook,
  3. adds status and evidence columns to the requirement catalog, marking
     every requirement that is still template wording, and
  4. records the proposed doer/checker decomposition in the ASIL allocation.

Usage:
    python build.py <fsc-builder scripts directory>
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = os.path.dirname(os.path.abspath(__file__))
HARA = os.path.join(HERE, "..", "hara", "LD-HARA-001_hara.xlsx")
OUTPUT = os.path.join(HERE, "LD-FSC-001_fsc.xlsx")

BRANCH_OF = {
    "sensor": 1, "comm_in": 1, "power_in": 1,
    "processor": 2, "software": 2, "memory": 2,
    "actuator": 3, "driver": 3, "comm_out": 3,
}
THIN = Side(border_style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER = PatternFill("solid", fgColor="1F3864")
GAP = PatternFill("solid", fgColor="F8CBAD")
DONE = PatternFill("solid", fgColor="C6EFCE")
TEMPLATE = PatternFill("solid", fgColor="FFF2CC")


def basic_event_codes(nodes):
    """Reproduce the generator's numbering: per branch, ASIL-relevant nodes in list order."""
    counters, codes = defaultdict(int), {}
    for node in nodes:
        if not node.get("asil_relevant", True):
            continue
        branch = BRANCH_OF[node["type"]]
        counters[branch] += 1
        codes[node["id"]] = (branch, counters[branch])
    return codes


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    scripts = sys.argv[1]
    with open(os.path.join(HERE, "fsc.json"), encoding="utf-8") as f:
        src = json.load(f)
    nodes = src["block_diagram"]["nodes"]
    codes = basic_event_codes(nodes)

    overrides = []
    for req in src["fsrs"]:
        branch, index = codes[req["node_id"]]
        overrides.append({"sg_id": req["sg_id"],
                          "be_code": f"BE-{req['sg_id'].split('-')[1]}-{branch}-{index:02d}",
                          "fsr_text": req["fsr_text"]})
    gen_input = {"fsc_metadata": src["fsc_metadata"], "block_diagram": src["block_diagram"],
                 "safety_goal_overrides": {}, "fsr_overrides": overrides}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(gen_input, tmp)
    subprocess.run([sys.executable, os.path.join(scripts, "generate_fsc.py"), HARA, tmp.name, OUTPUT], check=True)
    os.unlink(tmp.name)

    wb = load_workbook(OUTPUT)
    by_key = {(r["sg_id"], r["node_id"]): r for r in src["fsrs"]}

    # Requirement catalog: status and evidence for every FSR.
    ws = wb["05_FSR_Catalog"]
    for col, title in ((9, "Status"), (10, "Implementation / evidence")):
        cell = ws.cell(row=4, column=col, value=title)
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.fill = HEADER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER
    for row in ws.iter_rows(min_row=5):
        sg_id, node_cell = row[1].value, row[5].value
        if not sg_id or not node_cell:
            continue
        req = by_key.get((sg_id, str(node_cell).split(" ")[0]))
        if req:
            status, evidence = req["status"], req["evidence"]
            fill = GAP if status == "GAP" else DONE if status.startswith("Implemented") else TEMPLATE
        else:
            status, evidence, fill = "Template", "Generic wording from the FTA expansion; refine or justify as not applicable in the TSC.", TEMPLATE
        for col, value in ((9, status), (10, evidence)):
            cell = ws.cell(row=row[0].row, column=col, value=value)
            cell.font = Font(name="Calibri", size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = BORDER
            cell.fill = fill
    ws.column_dimensions["I"].width = 22
    ws.column_dimensions["J"].width = 60

    # ASIL allocation: the proposed doer/checker decomposition.
    dec = src["decomposition"]
    ws = wb["06_ASIL_Allocation"]
    for row in ws.iter_rows(min_row=5):
        sg_id, node_id = row[0].value, row[1].value
        if sg_id not in dec["safety_goals"] or node_id not in ("N11", "N14"):
            continue
        r = row[0].row
        ws.cell(row=r, column=6, value=dec["scheme"] + ". " + dec["basis"])
        ws.cell(row=r, column=7, value="D(D) + QM(D), proposed")
        ws.cell(row=r, column=8, value="D(D)" if node_id == "N14" else "QM(D)")
        ws.cell(row=r, column=9, value=dec["independence_argument_status"])
        for col in (6, 7, 8, 9):
            ws.cell(row=r, column=col).alignment = Alignment(vertical="top", wrap_text=True)
            ws.cell(row=r, column=col).fill = TEMPLATE

    wb.save(OUTPUT)
    subprocess.run([sys.executable, os.path.join(scripts, "recalc.py"), OUTPUT], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
