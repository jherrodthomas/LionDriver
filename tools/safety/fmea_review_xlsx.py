#!/usr/bin/env python3
"""Reviewer workbooks for the FMEAs: one AIAG-VDA worksheet per analysis, styled for people, generated from the YAML.

Writes assurance/08-analyses/fmea/exports/review/<analysis>-review.xlsx for the System FMEA, SW FMEA, DFMEA and PFMEA.
Each workbook has four sheets:
  Cover      document control, counts by action priority, legend, reviewer sign-off cells
  Worksheet  one row per cause in the AIAG-VDA 2019 column order (failure analysis, risk analysis, optimization), with
             the element, function, effects and failure mode merged over their causes, AP colour-coded, causes that no
             test targets (D >= 9) in amber, and two reviewer columns (decision from a list, comment) to fill in
  Actions    every action with its causes, owner, status and revised rating
  Structure  the structure tree and the functions

The YAML stays the source of truth: regenerate, never edit the generated sheets. Action priority is recomputed with the
AIAG-VDA table of rating-tables.md (fmea_lint.compute_ap) and must equal the YAML value; fmea_lint enforces that.

Usage:
  tools/safety/fmea_review_xlsx.py            write all four workbooks
  tools/safety/fmea_review_xlsx.py --check    fail if a committed workbook's cell values differ from a fresh build

Requires PyYAML and openpyxl.
"""
from __future__ import annotations

import argparse
import datetime
import io
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fmea_lint

ROOT = fmea_lint.ROOT
ANALYSES = ROOT / fmea_lint.SAFETY_DIR / "analyses"
OUT_DIR = ROOT / fmea_lint.SAFETY_DIR / "exports" / "review"
SOURCES = ["system-fmea", "sw-fmea", "dfmea", "pfmea"]

# palette (design A of the FMEA review mockups): ink on white, slate group bands, AP chips that differ in lightness
INK, MUTED, RULE, RULE_STRONG = "1B2430", "5B6676", "E3E8EE", "C9D1DB"
ACCENT = "1F4E8C"
AMBER = "8A5A00"
BAND = {"failure": ("E8ECF1", "334155"), "risk": ("DCE6F3", "1F3A5F"), "optimization": ("F3E9D7", "6B4A12"),
        "review": ("FFF4CC", "6B4A12")}
AP_STYLE = {"H": ("F6D9D6", "7A1B14"), "M": ("FBEDC9", "5A3E00"), "L": ("E2F1EA", "14513A")}
STATUS_COLOR = {"open": MUTED, "in progress": ACCENT, "decision pending": AMBER, "completed": "14513A", "closed": "14513A"}
FM_FILL = "FBFCFD"
INPUT_FILL = "FFFBEB"
FONT = "Calibri"

COLUMNS = [  # (group, header, width)
  ("failure", "Element", 22),
  ("failure", "Function", 30),
  ("failure", "Failure effects", 36),
  ("failure", "Hazards", 11),
  ("failure", "S", 5),
  ("failure", "Failure mode", 30),
  ("failure", "Cause", 7),
  ("failure", "Failure cause", 40),
  ("risk", "Prevention controls", 34),
  ("risk", "O", 5),
  ("risk", "Detection controls", 34),
  ("risk", "D", 5),
  ("risk", "AP", 6),
  ("optimization", "Actions", 38),
  ("optimization", "Status", 12),
  ("optimization", "Revised S/O/D", 11),
  ("optimization", "Revised AP", 9),
  ("review", "Reviewer decision", 14),
  ("review", "Reviewer comment", 34),
]
GROUP_TITLES = {"failure": "Failure analysis (AIAG-VDA step 4)", "risk": "Risk analysis (step 5)",
                "optimization": "Optimization (step 6)", "review": "Review"}
MERGED = 6  # Element … Failure mode are merged over a failure mode's causes
HEADER_ROWS = 2


def thin(color=RULE):
  return Side(style="thin", color=color)


def font(size=10, bold=False, color=INK, italic=False):
  return Font(name=FONT, size=size, bold=bold, color=color, italic=italic)


def fill(color):
  return PatternFill("solid", start_color=color, end_color=color)


WRAP_TOP = Alignment(wrap_text=True, vertical="top")
CENTER_TOP = Alignment(horizontal="center", vertical="top", wrap_text=True)


def load(name: str) -> dict:
  return fmea_lint.load_yaml((ANALYSES / f"{name}.yaml").read_text())


def ifont(size=10, bold=False, color=INK, italic=False):
  return InlineFont(rFont=FONT, sz=size, b=bold, color=color, i=italic)


def rich(*parts) -> CellRichText:
  """parts: (text, style) with style one of body, bold, id, label, ref, amber."""
  styles = {"body": ifont(), "bold": ifont(bold=True), "id": ifont(9, True, ACCENT), "label": ifont(9, True, MUTED),
            "ref": ifont(8, color=MUTED), "amber": ifont(color=AMBER)}
  return CellRichText([TextBlock(styles[s], txt) for txt, s in parts if txt])


def controls(lst, amber=False):
  parts, plain = [], []
  for k, c in enumerate(lst or []):
    desc = " ".join(c["description"].split())
    ref = c.get("test") or c.get("ref")
    parts.append(("\n" if k else "", "body"))
    parts.append(("• " + desc, "amber" if amber else "body"))
    plain.append("• " + desc)
    if ref:
      parts.append(("\n   " + ref, "ref"))
      plain.append("   " + ref)
  return (rich(*parts) if parts else ""), "\n".join(plain)


def effects_text(fm):
  order = {"end": 0, "next_higher": 1, "local": 2}
  label = {"end": "End", "next_higher": "Next higher", "local": "Local"}
  parts, lines, hazards = [], [], []
  for k, e in enumerate(sorted(fm["effects"], key=lambda e: order.get(e["level"], 3))):
    text = " ".join(e["description"].split())
    parts += [("\n" if k else "", "body"), (label.get(e["level"], e["level"]) + "  ", "label"), (text, "body")]
    lines.append(f"{label.get(e['level'], e['level'])}  {text}")
    if e.get("hazard") and e["hazard"] not in hazards:
      hazards.append(e["hazard"])
  return rich(*parts), "\n".join(lines), "\n".join(hazards)


def rows_estimate(text: str, width: int) -> int:
  chars = max(8, int(width * 1.15))
  return sum(max(1, -(-len(line) // chars)) for line in (text or "").split("\n"))


def counts(doc) -> dict:
  ap = {"H": 0, "M": 0, "L": 0}
  causes = 0
  for fm in doc["failure_modes"]:
    for c in fm["causes"]:
      causes += 1
      if c.get("ap") in ap:
        ap[c["ap"]] += 1
  open_actions = sum(1 for a in doc["actions"] if a.get("status") not in ("completed", "closed"))
  return {"fm": len(doc["failure_modes"]), "causes": causes, "ap": ap, "actions": len(doc["actions"]), "open": open_actions}


def build(name: str) -> Workbook:
  doc = load(name)
  hdr = doc["analysis"]
  elements = {e["id"]: e for e in doc["structure"]}
  functions = {f["id"]: f for f in doc["functions"]}
  actions = {a["id"]: a for a in doc["actions"]}

  wb = Workbook()
  updated = hdr.get("updated")
  stamp = datetime.datetime.fromisoformat(str(updated)) if updated else datetime.datetime(2026, 1, 1)
  wb.properties.creator = "tools/safety/fmea_review_xlsx.py"
  wb.properties.title = f"{hdr['title']} — review workbook"
  wb.properties.created = stamp
  wb.properties.modified = stamp

  cover(wb.active, doc, name)
  worksheet(wb.create_sheet("Worksheet"), doc, elements, functions, actions)
  actions_sheet(wb.create_sheet("Actions"), doc)
  structure_sheet(wb.create_sheet("Structure"), doc, elements)
  return wb


def cover(ws, doc, name):
  hdr = doc["analysis"]
  ws.title = "Cover"
  ws.sheet_view.showGridLines = False
  ws.column_dimensions["A"].width = 3
  ws.column_dimensions["B"].width = 24
  ws.column_dimensions["C"].width = 70
  ws["B2"] = f"LionDriver · {hdr['id']} · AIAG-VDA 2019"
  ws["B2"].font = font(10, True, ACCENT)
  ws["B3"] = hdr["title"]
  ws["B3"].font = font(18, True)
  ws["B4"] = f"Generated from assurance/08-analyses/fmea/analyses/{name}.yaml. Do not edit: regenerate with tools/safety/fmea_review_xlsx.py."
  ws["B4"].font = font(9, color=MUTED, italic=True)
  ws.page_setup.orientation = "portrait"
  ws.page_setup.fitToWidth = 1
  ws.page_setup.fitToHeight = 0
  ws.sheet_properties.pageSetUpPr.fitToPage = True

  team = "; ".join(f"{m['name']} ({m['role']})" for m in hdr.get("team", []))
  rows = [("Revision", f"{hdr['revision']} · {hdr['status']}"), ("Baseline", hdr["baseline"]),
          ("Rating tables", hdr.get("rating_tables", "")), ("Updated", str(hdr.get("updated", ""))),
          ("Scope", " ".join(str(hdr.get("scope", "")).split())), ("Team", team)]
  r = 6
  for k, v in rows:
    ws.cell(r, 2, k).font = font(10, True, MUTED)
    ws.cell(r, 2).alignment = Alignment(vertical="top")
    c = ws.cell(r, 3, v)
    c.font = font(10)
    c.alignment = WRAP_TOP
    ws.row_dimensions[r].height = 15 * rows_estimate(v, 70)
    r += 1

  n = counts(doc)
  r += 1
  ws.cell(r, 2, "Summary").font = font(12, True)
  r += 1
  summary = [("Failure modes", n["fm"]), ("Rated causes", n["causes"]), ("AP High", n["ap"]["H"]),
             ("AP Medium", n["ap"]["M"]), ("AP Low", n["ap"]["L"]), ("Actions (open)", f"{n['actions']} ({n['open']})")]
  for k, v in summary:
    ws.cell(r, 2, k).font = font(10, True, MUTED)
    c = ws.cell(r, 3, v)
    c.font = font(11, True)
    c.alignment = Alignment(horizontal="left")
    if k.startswith("AP "):
      bg, fg = AP_STYLE[k[3]]
      ws.cell(r, 2).fill = fill(bg)
      ws.cell(r, 2).font = font(10, True, fg)
    r += 1

  r += 1
  ws.cell(r, 2, "Legend").font = font(12, True)
  r += 1
  legend = [("H", "High: an action or a rationale is required"), ("M", "Medium: an action or a rationale is recommended"),
            ("L", "Low"), (None, "Amber text: no test targets the cause (detection 9 or 10)"),
            (None, "Yellow cells on the Worksheet: reviewer input (decision from the list, comment)")]
  for ap, text in legend:
    c = ws.cell(r, 2, ap or "")
    if ap:
      bg, fg = AP_STYLE[ap]
      c.fill = fill(bg)
      c.font = font(10, True, fg)
      c.alignment = Alignment(horizontal="center")
    elif "Amber" in text:
      c.value = "Aa"
      c.font = font(10, True, AMBER)
      c.alignment = Alignment(horizontal="center")
    else:
      c.fill = fill(INPUT_FILL)
    ws.cell(r, 3, text).font = font(10)
    r += 1

  r += 1
  ws.cell(r, 2, "Review sign-off").font = font(12, True)
  r += 1
  for k in ("Reviewer", "Independence level", "Date", "Result (accepted / accepted with findings / rejected)", "Findings reference"):
    ws.cell(r, 2, k).font = font(10, True, MUTED)
    ws.cell(r, 2).alignment = WRAP_TOP
    c = ws.cell(r, 3, "")
    c.fill = fill(INPUT_FILL)
    c.border = Border(bottom=thin(RULE_STRONG))
    ws.row_dimensions[r].height = 30 if len(k) > 24 else 18
    r += 1


def worksheet(ws, doc, elements, functions, actions):
  ws.sheet_view.showGridLines = False
  ws.sheet_view.zoomScale = 90
  ncol = len(COLUMNS)

  # row 1: group bands; row 2: column headers
  start = 1
  for i in range(1, ncol + 1):
    group = COLUMNS[i - 1][0]
    last = i == ncol or COLUMNS[i][0] != group
    if last:
      bg, fg = BAND[group]
      ws.merge_cells(start_row=1, start_column=start, end_row=1, end_column=i)
      c = ws.cell(1, start, GROUP_TITLES[group].upper())
      c.font = font(9, True, fg)
      c.alignment = Alignment(vertical="center", indent=1)
      for j in range(start, i + 1):
        ws.cell(1, j).fill = fill(bg)
        ws.cell(1, j).border = Border(left=thin("FFFFFF") if j == start else None)
      start = i + 1
  for i, (_group, title, width) in enumerate(COLUMNS, 1):
    c = ws.cell(2, i, title)
    c.font = font(9, True, "4A5565")
    c.fill = fill("F7F9FB")
    c.alignment = Alignment(horizontal="center" if width <= 11 else "left", vertical="center", wrap_text=True)
    c.border = Border(bottom=Side(style="medium", color=RULE_STRONG))
    ws.column_dimensions[get_column_letter(i)].width = width
  ws.row_dimensions[1].height = 20
  ws.row_dimensions[2].height = 30

  decision = DataValidation(type="list", formula1='"Agree,Re-rate,Reject,Question"', allow_blank=True)
  decision.prompt = "Reviewer decision for this cause"
  decision.promptTitle = "Review"
  ws.add_data_validation(decision)

  row = HEADER_ROWS + 1
  for fm in doc["failure_modes"]:
    el = elements.get(fm["element"], {})
    fn = functions.get(fm["function"], {})
    eff, eff_plain, haz = effects_text(fm)
    causes = fm["causes"]
    first = row
    s = fm.get("severity")
    for k, cause in enumerate(causes):
      o, d, ap = cause.get("occurrence"), cause.get("detection"), cause.get("ap")
      acts = [actions[a] for a in cause.get("actions", []) if a in actions]
      act_parts = []
      for j, a in enumerate(acts):
        act_parts += [("\n" if j else "", "body"), (f"{a['id']} · {a['kind'].replace('_', ' ')}\n", "id"),
                      (" ".join(a["description"].split()), "body")]
      act_plain = "\n".join(f"{a['id']}\n{a['description']}" for a in acts)
      if not acts and cause.get("rationale"):
        act_parts = [("Rationale  ", "label"), (" ".join(cause["rationale"].split()), "body")]
        act_plain = cause["rationale"]
      act_text = rich(*act_parts) if act_parts else ""
      status = "\n".join(a.get("status", "").replace("_", " ") for a in acts)
      revised = [a["revised"] for a in acts if a.get("revised")]
      rev_sod = "\n".join(f"{r['severity']}/{r['occurrence']}/{r['detection']}" for r in revised)
      rev_ap = revised[0]["ap"] if len(revised) == 1 else ("\n".join(r["ap"] for r in revised) if revised else "")
      cause_text = " ".join(cause["description"].split())
      cause_cell = rich((cause_text, "body"), (f"\nlinked: {cause['linked_failure_mode']}" if cause.get("linked_failure_mode") else "", "ref"))
      untested = isinstance(d, int) and d >= 9
      prev_cell, prev_plain = controls(cause.get("prevention_controls"))
      det_cell, det_plain = controls(cause.get("detection_controls"), amber=untested)
      values = [
        rich((fm["element"] + "\n", "id"), (el.get("name", ""), "body")),
        rich((fm["function"] + "\n", "id"), (" ".join(fn.get("description", "").split()), "body")),
        eff, haz, s,
        rich((f"{fm['id']} · {fm['guideword']}\n", "id"), (fm["failure_mode"], "bold")),
        cause["id"].split(".")[-1], cause_cell, prev_cell, o, det_cell, d, ap or "",
        act_text, status, rev_sod, rev_ap, "", "",
      ]
      plain = [f"{fm['element']}\n{el.get('name', '')}", f"{fm['function']}\n{fn.get('description', '')}", eff_plain, haz, s,
               f"{fm['id']}\n{fm['failure_mode']}", "", cause_text, prev_plain, o, det_plain, d, ap or "",
               act_plain, status, rev_sod, rev_ap, "", ""]
      for i, v in enumerate(values, 1):
        if k > 0 and i <= MERGED:
          continue
        c = ws.cell(row, i, v)
        width = COLUMNS[i - 1][2]
        c.alignment = CENTER_TOP if width <= 11 else WRAP_TOP
        c.font = font(10)
      for i in (5, 10, 12):
        ws.cell(row, i).font = font(10, True)
      if status:
        ws.cell(row, 15).font = font(10, True, STATUS_COLOR.get(status.split("\n")[0], MUTED))
      if ap in AP_STYLE:
        bg, fg = AP_STYLE[ap]
        ws.cell(row, 13).fill = fill(bg)
        ws.cell(row, 13).font = font(10, True, fg)
      if isinstance(rev_ap, str) and rev_ap in AP_STYLE:
        bg, fg = AP_STYLE[rev_ap]
        ws.cell(row, 17).fill = fill(bg)
        ws.cell(row, 17).font = font(10, True, fg)
      if untested:
        ws.cell(row, 12).font = font(10, True, AMBER)
      for i in (18, 19):
        ws.cell(row, i).fill = fill(INPUT_FILL)
      decision.add(ws.cell(row, 18))
      height = max(rows_estimate(str(plain[i - 1] or ""), COLUMNS[i - 1][2]) for i in range(MERGED + 1, ncol + 1))
      if len(causes) == 1:
        height = max(height, max(rows_estimate(str(plain[i - 1] or ""), COLUMNS[i - 1][2]) for i in range(1, MERGED + 1)))
      if first == row:
        fm_need = max(rows_estimate(str(plain[i - 1] or ""), COLUMNS[i - 1][2]) for i in range(1, MERGED + 1))
      ws.row_dimensions[row].height = min(409, 13.5 * height + 6)
      row += 1
    last = row - 1
    # merge the failure-mode columns over the causes; make sure the merged block is tall enough
    if last > first:
      need = fm_need
      have = sum((ws.row_dimensions[r].height or 15) for r in range(first, last + 1)) / 13.5
      if need > have:
        ws.row_dimensions[last].height = min(409, (ws.row_dimensions[last].height or 15) + 13.5 * (need - have))
      for i in range(1, MERGED + 1):
        ws.merge_cells(start_row=first, start_column=i, end_row=last, end_column=i)
    for r in range(first, last + 1):
      for i in range(1, ncol + 1):
        bottom = Side(style="medium", color=RULE_STRONG) if r == last else thin()
        ws.cell(r, i).border = Border(left=thin(), right=thin(), bottom=bottom)
        if i <= MERGED and ws.cell(r, i).fill.fgColor.rgb in (None, "00000000"):
          ws.cell(r, i).fill = fill(FM_FILL)

  ws.freeze_panes = ws.cell(HEADER_ROWS + 1, MERGED + 1)
  ws.auto_filter.ref = f"A2:{get_column_letter(ncol)}{max(row - 1, 2)}"
  ws.print_title_rows = "1:2"
  ws.page_setup.orientation = "landscape"
  ws.page_setup.paperSize = ws.PAPERSIZE_A3
  ws.page_setup.fitToWidth = 1
  ws.page_setup.fitToHeight = 0
  ws.sheet_properties.pageSetUpPr.fitToPage = True
  hdr = doc["analysis"]
  ws.oddFooter.left.text = f"{hdr['title']} · rev {hdr['revision']} · {hdr['baseline']}"
  ws.oddFooter.right.text = "Page &P of &N"


def table(ws, headers, widths, rows, wrap_cols=()):
  ws.sheet_view.showGridLines = False
  for i, (h, w) in enumerate(zip(headers, widths, strict=True), 1):
    c = ws.cell(1, i, h)
    c.font = font(9, True, "4A5565")
    c.fill = fill("F7F9FB")
    c.border = Border(bottom=Side(style="medium", color=RULE_STRONG))
    c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.column_dimensions[get_column_letter(i)].width = w
  ws.row_dimensions[1].height = 24
  for r, values in enumerate(rows, 2):
    for i, v in enumerate(values, 1):
      c = ws.cell(r, i, v)
      c.font = font(10)
      c.alignment = WRAP_TOP
      c.border = Border(bottom=thin())
    ws.row_dimensions[r].height = min(409, 13.5 * max(rows_estimate(str(values[i] or ""), widths[i]) for i in wrap_cols) + 6) \
      if wrap_cols else 18
  ws.freeze_panes = "A2"
  ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(len(rows) + 1, 1)}"


def actions_sheet(ws, doc):
  by_action: dict[str, list[str]] = {}
  for fm in doc["failure_modes"]:
    for c in fm["causes"]:
      for a in c.get("actions", []):
        by_action.setdefault(a, []).append(c["id"])
  rows = []
  for a in doc["actions"]:
    rev = a.get("revised") or {}
    rows.append([a["id"], a["kind"].replace("_", " "), " ".join(a["description"].split()), a.get("owner", ""),
                 a.get("status", "").replace("_", " "), "\n".join(by_action.get(a["id"], [])),
                 f"{rev['severity']}/{rev['occurrence']}/{rev['detection']}" if rev else "", rev.get("ap", ""),
                 " ".join(str(a.get("evidence", "")).split())])
  table(ws, ["Action", "Kind", "Description", "Owner", "Status", "Causes", "Revised S/O/D", "Revised AP", "Evidence"],
        [14, 14, 60, 18, 14, 14, 12, 10, 50], rows, wrap_cols=(2, 5, 8))
  for r, values in enumerate(rows, 2):
    ap = values[7]
    if ap in AP_STYLE:
      bg, fg = AP_STYLE[ap]
      ws.cell(r, 8).fill = fill(bg)
      ws.cell(r, 8).font = font(10, True, fg)
    if values[4] == "completed":
      ws.cell(r, 5).font = font(10, True, "14513A")


def structure_sheet(ws, doc, elements):
  def depth(e):
    d, seen = 0, set()
    while e.get("parent") and e["parent"] in elements and e["id"] not in seen:
      seen.add(e["id"])
      e = elements[e["parent"]]
      d += 1
    return d
  fns: dict[str, list[str]] = {}
  for f in doc["functions"]:
    fns.setdefault(f["element"], []).append(f"{f['id']}: {' '.join(f['description'].split())}")
  rows = []
  for e in doc["structure"]:
    rows.append([e["id"], "    " * depth(e) + e["name"], e.get("kind", ""), e.get("parent", "") or "", "\n".join(fns.get(e["id"], []))])
  table(ws, ["Element", "Name", "Kind", "Parent", "Functions"], [14, 50, 16, 14, 90], rows, wrap_cols=(4,))


def cell_values(wb) -> dict:
  return {ws.title: [[c.value for c in r] for r in ws.iter_rows()] for ws in wb.worksheets}


def main(argv=None) -> int:
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("--check", action="store_true", help="compare the committed workbooks with a fresh build")
  args = ap.parse_args(argv)
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  stale = []
  for name in SOURCES:
    wb = build(name)
    path = OUT_DIR / f"{name}-review.xlsx"
    if args.check:
      buf = io.BytesIO()
      wb.save(buf)
      fresh = cell_values(load_workbook(io.BytesIO(buf.getvalue())))
      if not path.exists() or cell_values(load_workbook(path)) != fresh:
        stale.append(path.relative_to(ROOT).as_posix())
    else:
      wb.save(path)
  if args.check:
    if stale:
      print("fmea_review_xlsx: stale, run tools/safety/fmea_review_xlsx.py: " + ", ".join(stale))
      return 1
    print(f"fmea_review_xlsx: {len(SOURCES)} workbook(s) current")
  else:
    print(f"fmea_review_xlsx: wrote {len(SOURCES)} workbook(s) to {OUT_DIR.relative_to(ROOT).as_posix()}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
