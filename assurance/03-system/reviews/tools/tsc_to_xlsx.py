# ruff: noqa: E501
"""Map the LionDriver TSC work products (WP-S-02/03/04/05, WP-A-03/04, WP-C-04) onto the tsc-builder tab layout.

Content is copied from the Markdown tables; nothing is invented. Derived fields are marked in the
column name or filled only from an explicit source (e.g. FSR -> SG from WP-C-04 §9).
"""
import re
import sys
from pathlib import Path

from openpyxl import Workbook

A = Path(sys.argv[1])
OUT = Path(sys.argv[2])


def all_tables(path):
  out, cur, hdr = [], None, None
  for l in Path(path).read_text().splitlines():
    if l.startswith("|"):
      cells = [c.strip() for c in l.strip().strip("|").split("|")]
      if hdr is None:
        hdr, cur = cells, []
        out.append((hdr, cur))
      elif set("".join(cells)) <= set("-: "):
        continue
      else:
        cur.append(dict(zip(hdr, cells, strict=False)))
    else:
      hdr = None
  return out


def plain(s):
  return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(s)).replace("**", "").replace("`", "")


def sheet(wb, name, header, rows):
  ws = wb.create_sheet(name)
  ws.append(header)
  for r in rows:
    ws.append([plain(c) for c in r])


fsc = A / "02-concept/WP-C-04-functional-safety-concept.md"
s02 = A / "03-system/WP-S-02-technical-safety-requirements.md"
s03 = A / "03-system/WP-S-03-technical-safety-concept-architecture.md"
s04 = A / "03-system/WP-S-04-timing-ftti-budget.md"
s05 = A / "03-system/WP-S-05-hsi-specification.md"
a03 = A / "08-analyses/WP-A-03-dependent-failure-analysis.md"
a04 = A / "08-analyses/WP-A-04-system-fta-fmea.md"

# FSR -> SG from WP-C-04 §9 (first SG marked)
sg_cols = ["SG-01", "SG-02", "SG-03", "SG-04", "SG-05", "SG-06", "SG-07"]
fsr_sg = {}
for hdr, rows in all_tables(fsc):
  if hdr[:2] == ["FSR", "SG-01"]:
    for r in rows:
      sgs = [sg for sg in sg_cols if r.get(sg) == "●"]
      for fid in re.findall(r"\d\d\.\d\d", r["FSR"]):
        fsr_sg.setdefault("FSR-" + fid, sgs[0] if sgs else "")
      m = re.match(r"FSR-(\d\d)\.(\d\d)[–-](\d\d)\.(\d\d)", r["FSR"])
      if m and m.group(1) == m.group(3):
        for k in range(int(m.group(2)), int(m.group(4)) + 1):
          fsr_sg.setdefault(f"FSR-{m.group(1)}.{k:02d}", sgs[0] if sgs else "")
ftti = {"SG-01": 500, "SG-02": 1000, "SG-03": 1000, "SG-04": 1000, "SG-05": 200, "SG-06": 1000, "SG-07": "Continuous"}  # WP-C-04 §3

fsrs = []
for hdr, rows in all_tables(fsc):
  if hdr and hdr[0] == "ID" and "Alloc" in hdr:
    for r in rows:
      if r["ID"].startswith("FSR-"):
        sg = fsr_sg.get(r["ID"]) or "SG-" + r["ID"][4:6]
        fsrs.append((r["ID"], sg, r["ASIL"], "", r["Alloc"], r["Requirement"], ftti.get(sg, "")))

tsrs = []
for hdr, rows in all_tables(s02):
  if hdr and hdr[0] == "ID" and "Parent" in hdr:
    for r in rows:
      if r["ID"].startswith("TSR-"):
        parents = re.findall(r"FSR-\d\d\.\d\d", r.get("Parent", ""))
        alloc = r.get("Alloc", "")
        typ = "HW-TSR" if re.search(r"P-HW|HAR", alloc) and not re.search(r"P-SW|SoC", alloc) else "SW-TSR"
        for par in (parents or [r.get("Parent", "")]):  # one row per (TSR, parent FSR)
          tsrs.append((r["ID"], par, r.get("ASIL", ""), typ, r.get("SM", ""), alloc,
                       r.get("Requirement") or r.get("Requirement (summary)", ""), r.get("Verif", ""), r.get("Timing", "")))
tsr_fsr = {}
for t in tsrs:
  tsr_fsr.setdefault(t[0][4:], t[1])

mechs = []
for hdr, rows in all_tables(s03):
  if hdr and hdr[0] == "SM":
    for r in rows:
      nums = set()
      for a, b in re.findall(r"(\d{3})(?:[–-](\d{3}))?", r.get("TSR", "")):
        nums.update(f"{x:03d}" for x in range(int(a), int(b or a) + 1))
      fids = sorted({t[1] for t in tsrs if t[0][4:] in nums and t[1].startswith("FSR-")})
      for fid in fids or [""]:
        asil = next((t[2] for t in tsrs if t[1] == fid and t[0][4:] in nums), "")
        mechs.append((fid, asil, "", r["Element"], r["SM"], r["Mechanism"], r.get("DC target", ""), "", "[primary]"))

arch = []
hw_map = {"E-04a": ("HW-01", "Safety MCU STM32H7", "STM32H7 (part number TBD, WP-H-02 UK-02)"),
          "E-04b": ("HW-02", "Device hardware (SoC, cameras, IMU, display, speaker, PSU)", "comma 3X / comma four"),
          "E-05": ("HW-03", "Toyota TSS2 harness with intercept relay", "comma harness")}
sp_map = {"E-01": "SP-01", "E-02": "SP-02", "E-03a": "SP-03", "E-03b": "SP-04"}
for hdr, rows in all_tables(s03):
  if hdr and hdr[0] == "Element" and "Integrity" in hdr:
    for r in rows:
      eid = r["Element"].split()[0]
      if eid in hw_map:
        hid, name, part = hw_map[eid]
        arch.append((hid, name, part, eid, "shared device supply" if eid != "E-05" else "vehicle 12 V via harness", "see WP-S-05 §3"))
      elif eid in sp_map:
        host = "HW-01" if eid.startswith("E-03") else "HW-02"
        arch.append((sp_map[eid], r["Element"], host, eid, "bare metal" if host == "HW-01" else "AGNOS Linux", r["Integrity"]))

timing = []
budget = {}
for hdr, rows in all_tables(s04):
  if hdr and hdr[0] == "SG / fault class":
    for r in rows:
      for sg in re.findall(r"SG-0\d(?:/0\d)?", r["SG / fault class"]):
        for part in sg.replace("SG-", "").split("/"):
          budget.setdefault("SG-" + part.zfill(2), (r["FTTI"], r["FDTI budget"], r["FRTI budget"]))
for f in fsrs:
  b = budget.get(f[1], ("", "", ""))
  timing.append((f[0], f[2], b[0], b[1], b[2]))

hsi = []
for hdr, rows in all_tables(s05):
  if hdr and hdr[0] == "HSI":
    for r in rows:
      fsr = ""
      for t in re.findall(r"TSR-(\d{3})", r.get("TSR / HWSR", "")):
        if t in tsr_fsr:
          fsr = tsr_fsr[t]
          break
      hsi.append((f"{r['HSI']} {r['Interface']}", "", fsr, r.get("Safety relevance", ""), r.get("HW resource", ""), "", "", "", r.get("ASIL", "")))

fmea = []
for hdr, rows in all_tables(a04):
  if hdr and hdr[0] == "ID" and "Failure mode" in hdr:
    for r in rows:
      eff = r.get("Effect (local → vehicle)", "")
      local, _, veh = eff.partition("→")
      fmea.append((r["Element"], r["Failure mode"], local.strip(), veh.strip() or eff, r.get("SG", ""), r.get("Mechanism (today)", ""), ""))

dfa = []
for hdr, rows in all_tables(a03):
  if hdr and hdr[0] == "Claim":
    for r in rows:
      dfa.append((r["Claim"], (r.get("Not controlled DFIs", "") + "; " + r.get("Partly controlled DFIs", "")).strip("; "),
                  "Yes" if r.get("Not controlled DFIs", "").strip() not in ("", "—") else "Partly", r.get("Condition to accept", ""), r.get("Verdict (current baseline)", "")))

wb = Workbook()
wb.remove(wb.active)
ws = wb.create_sheet("00_Title_Page")
for k, v in [("Title", "Technical Safety Concept (TSC): WP-S-02 TSRs, WP-S-03 architecture, WP-S-04 timing, WP-S-05 HSI, WP-A-03 DFA, WP-A-04 FMEA"),
             ("Project", "LionDriver"), ("TSC Document ID", "WP-S-02 / WP-S-03 (with WP-S-04, WP-S-05, WP-A-03, WP-A-04)"),
             ("Revision", "WP-S-02 0.2; WP-S-03 0.2; WP-A-03/04 0.2; WP-S-04/05 0.1"), ("Status", "Draft"),
             ("Author", "Assurance team (initial draft)"), ("Approver", "Safety manager"), ("Linked FSC", "WP-C-04 v0.2")]:
  ws.append(["", k, v])
sheet(wb, "01_Document_Control", ["Revision", "Date", "Change", "Author"], [
  ("0.1", "2026-10-11", "Initial TSC set: WP-S-02…05, WP-A-03/04 at baseline 8b8c6ae", "Assurance team"),
  ("0.2", "2026-10-12", "WP-S-02 TSR-621…625; WP-S-03 SM-29…SM-42; WP-A-03 DFI-24…26; WP-A-04 FTAs for SG-02, 04, 05, 06, 07", "Assurance team")])
sheet(wb, "02_FSRs_From_FSC", ["FSR_ID", "SG_ID", "ASIL", "Branch", "Linked Node", "Functional Safety Requirement", "FTTI (ms)"], fsrs)
sheet(wb, "03_System_Architecture", ["Component ID", "Name", "Part / hosted on", "Allocated nodes", "Power domain / OS", "Clock domain / integrity"], arch)
sheet(wb, "04_Safety_Mechanism_Catalog", ["FSR_ID", "Allocated ASIL", "Branch", "Linked Node", "Mechanism ID", "Mechanism Name", "DC target", "Detection time", "Selection"], mechs)
sheet(wb, "05_TSR_Catalog", ["TSR_ID", "FSR_ID", "Allocated ASIL", "Type", "Mechanism", "Linked Node", "Technical Safety Requirement", "Verification Method", "Timing"], tsrs)
sheet(wb, "06_HSI_Specification", ["HSI Signal", "Direction", "Linked FSR", "Mechanism", "Encoding / HW resource", "Update rate", "Integrity", "Failure reaction", "Allocated ASIL"], hsi)
sheet(wb, "07_Timing_Budget", ["FSR_ID", "Allocated ASIL", "FTTI", "FDTI", "FRTI"], timing)
sheet(wb, "08_System_FMEA", ["Element", "Failure mode", "Local effect", "Vehicle effect", "Linked SG", "Existing mechanism", "DC target"], fmea)
sheet(wb, "09_DFA", ["Decomposition pair / independence claim", "Coupling factor", "Coupling present", "Mitigation", "Conclusion"], dfa)
sheet(wb, "10_Verification", ["TSR_ID", "Verification Method"], [(t[0], t[7]) for t in tsrs])
sheet(wb, "11_HW_Handoff", ["TSR_ID", "Allocated HW element", "Note"], [(t[0], t[5], "WP-H-01 HWSR refinement") for t in tsrs if t[3] == "HW-TSR"])
sheet(wb, "12_SW_Handoff", ["TSR_ID", "Allocated SW element", "Note"], [(t[0], t[5], "WP-W-02 SWSR refinement") for t in tsrs if t[3] == "SW-TSR"])
wb.save(OUT)
print(f"fsrs={len(fsrs)} tsrs={len(tsrs)} mechs={len(mechs)} arch={len(arch)} hsi={len(hsi)} timing={len(timing)} fmea={len(fmea)} dfa={len(dfa)}")
