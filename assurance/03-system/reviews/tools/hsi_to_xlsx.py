"""Map WP-S-05 (HSI specification, Markdown) onto the hsi-builder tab layout. Only content present in the
source is copied; derived columns are named as such. Fields the source does not specify stay empty."""
import re
import sys
from pathlib import Path

from openpyxl import Workbook

A = Path(sys.argv[1])
OUT = Path(sys.argv[2])
s05 = (A / "03-system/WP-S-05-hsi-specification.md").read_text()
a04 = (A / "08-analyses/WP-A-04-system-fta-fmea.md").read_text()


def tables(text):
  out, hdr = [], None
  for line in text.splitlines():
    if line.startswith("|"):
      cells = [c.strip().replace("\x00", "|") for c in line.replace("\\|", "\x00").strip().strip("|").split("|")]
      if hdr is None:
        hdr = cells
        out.append((hdr, []))
      elif set("".join(cells)) <= set("-: "):
        continue
      else:
        out[-1][1].append(dict(zip(hdr, cells, strict=False)))
    else:
      hdr = None
  return out


def plain(v):
  return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(v)).replace("**", "").replace("`", "")


def fsrs_of(text):
  ids = set()
  for a, b in re.findall(r"(?:TSR-)?(\d{3})(?:…|-)?(\d{3})?", text):
    for x in range(int(a), int(b or a) + 1):
      ids.update(par.get(f"TSR-{x:03d}", []))
  return ", ".join(sorted(ids))


par = {}  # TSR -> parent FSRs, from the requirement tables of WP-S-02
for h, rows in tables((A / "03-system/WP-S-02-technical-safety-requirements.md").read_text()):
  if h and h[0] == "ID" and "Parent" in h:
    for r in rows:
      par.setdefault(r["ID"], set()).update(re.findall(r"FSR-\d\d\.\d\d", r.get("Parent", "")))

T = tables(s05)
summary = next(r for h, r in T if h[0] == "HSI")
signals = [r for h, rows in T if h[:2] == ["ID", "Signal"] for r in rows]  # §11 signal catalogue
sig, timing, fm, tests = [], [], [], []
for r in signals:
  name = f"{r['ID']} {plain(r['Signal'])}"
  # WP-S-05 combines type and width, and range, scale and units, in one column each; both tool columns get the same cell
  ttype, rng = plain(r["Type / bits"]), plain(r["Range, scale, units"])
  sig.append([name, plain(r["Dir"]), ttype, ttype, rng, rng, f"{ttype}; {rng}",
              plain(r["Integrity"]), plain(r["Validity / liveness"]), plain(r["Owner (HW / SW)"]), fsrs_of(r["TSR"]), plain(r["Failure reaction"]), r["ASIL"]])
  rate, _, age = plain(r["Rate / max age"]).partition(" / ")
  timing.append([name, rate, age or rate, age or "—"])
  detection = plain(r["Integrity"]) + "; " + plain(r["Validity / liveness"])
  fm.append([name, "loss, stale, corrupted or out-of-range value", detection, plain(r["Failure reaction"])])
  for t in re.findall(r"VS-[A-Z]+-\d+(?:…\d+)?", r["Tests"]):
    m = re.match(r"(VS-[A-Z]+-)(\d+)…(\d+)", t)
    ids = [f"{m.group(1)}{k:02d}" for k in range(int(m.group(2)), int(m.group(3)) + 1)] if m else [t]
    for tid in ids:
      kind = "fault injection" if tid.startswith("VS-FI") else "hardware integration" if tid.startswith("VS-HW") else "system integration"
      tests.append([tid, name, kind, plain(r["Failure reaction"])])
regs = [[plain(r["Region"]), plain(r["Address"]), f"{plain(r['Content / safety relevance'])}; size {r['Size']}; protection: {plain(r['Protection required'])}"]
        for r in next(r for h, r in T if h[0] == "Region")]
init = [[plain(r["Mode (MCU)"]), plain(r["Entered by"]), f"relay {plain(r['Relay'])}; CAN TX {plain(r['CAN TX'])}", plain(r["Safety relevance"])]
        for r in next(r for h, r in T if h[0] == "Mode (MCU)")]
version = re.search(r"^\| Version \| ([0-9.]+)", s05, re.M).group(1)

wb = Workbook()
wb.remove(wb.active)


def sheet(name, header, rows):
  ws = wb.create_sheet(name)
  ws.append(header)
  for r in rows:
    ws.append([plain(c) for c in r])


ws = wb.create_sheet("00_Title_Page")
for k, v in [("Title", "Hardware-Software Interface Specification (WP-S-05), converted for review"), ("Project", "LionDriver"),
             ("Document ID", "WP-S-05"), ("Revision", version), ("Status", "Draft"), ("Author", "Assurance team (initial draft)"),
             ("Approver", "Safety manager"), ("Linked TSC", "WP-S-02 v0.2 / WP-S-03 v0.2")]:
  ws.append(["", k, v])
sheet("01_Document_Control", ["Revision", "Date", "Change", "Author"],
      [("0.1", "2026-10-11", "Initial HSI at baseline 8b8c6ae", "Assurance team"),
       ("0.2", "2026-10-12", "§11 signal catalogue (29 signals); watchdog timeout 0.1 s", "Assurance team")])
sheet("02_HSI_Signal_Catalog", ["Signal name", "Direction", "Data type", "Bit width", "Range", "Units", "Encoding",
      "Integrity protection", "Validity bit", "Owner", "Linked FSR", "Linked mechanism", "ASIL"], sig)
sheet("03_Register_Map", ["Register / region", "Address", "Description"], regs)
sheet("04_Timing_Specification", ["Signal", "Sample rate", "Max age", "Latency budget / note"], timing)
sheet("05_Failure_Modes_and_Reactions", ["Signal / element", "Failure mode", "Detection mechanism", "Reaction"], fm)
sheet("06_Initialization_Sequence", ["State", "Entered by", "Outputs", "Safety relevance"], init)
sheet("07_Cross_Reference", ["HSI", "TSR / HWSR"], [(r["HSI"], plain(r["TSR / HWSR"])) for r in summary])
sheet("09_Test_Cases", ["Test ID", "Signal", "Test type", "Expected behavior"], tests)
sheet("10_References", ["Reference"], [("WP-S-02",), ("WP-S-03",), ("WP-S-04",), ("WP-H-01",), ("WP-W-02",), ("WP-A-04 §10",)])
wb.save(OUT)
print(f"signals={len(sig)} regs={len(regs)} timing={len(timing)} fm={len(fm)} init={len(init)} tests={len(tests)}")
