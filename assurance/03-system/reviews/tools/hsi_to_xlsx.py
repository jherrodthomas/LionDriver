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
      cells = [c.strip() for c in line.strip().strip("|").split("|")]
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
direction = {"HSI-01": "Bidirectional (SoC ↔ MCU)", "HSI-02": "In (SoC → MCU)", "HSI-03": "Bidirectional (SoC ↔ MCU)",
             "HSI-04": "Bidirectional (MCU ↔ vehicle CAN)", "HSI-05": "Out (MCU → relay)", "HSI-06": "In (harness → MCU)",
             "HSI-07": "In (harness → MCU)", "HSI-08": "In (SoC → MCU NRST/BOOT0)", "HSI-09": "Internal (MCU)",
             "HSI-10": "Internal (MCU)", "HSI-11": "Out (MCU → speaker)", "HSI-12": "Internal (MCU flash)",
             "HSI-13": "In (supply → ADC)", "HSI-14": "Internal (MCU)"}
integrity = {"HSI-01": "8-bit XOR on header and payload, NACK (CRC + sequence counter required, TSR-410/411)",
             "HSI-02": "8-bit XOR (as HSI-01); no authentication",
             "HSI-03": "8-bit XOR per packet, checked at FDCAN load",
             "HSI-04": "CAN CRC; 8-bit additive checksum on 0x260/0x1D2 only; no counters (GAP-01)",
             "HSI-12": "SHA-1 + RSA-1024 signature at boot (bootstub.c:40-80)"}
sig = []
for r in summary:
  hid = r["HSI"]
  sig.append([f"{hid} {plain(r['Interface'])}", direction.get(hid, ""), "", "", "", "", plain(r["HW resource"]),
              integrity.get(hid, "none specified"), "", plain(r["SW owner"]), fsrs_of(r["TSR / HWSR"]),
              plain(r["Safety relevance"]), r["ASIL"]])
rx = next(r for h, r in T if h[0] == "Addr")
for r in rx:
  sig.append([f"RX {plain(r['Addr'])} {r['Name']}", "In (vehicle CAN bus 0 → MCU)", "CAN frame", "", "", "",
              f"DBC; rate {r['Rate']}", f"checksum: {r['Checksum']}; counter: {r['Counter']}", "", "opendbc safety (modes/toyota.h)",
              fsrs_of("401-406"), plain(r["Envelope use"]), "B‡"])
for r in next(r for h, r in T if h[0] == "Signal"):
  sig.append([plain(r["Signal"]), plain(r["Direction"]), "digital" if "Relay" in r["Signal"] else "analog/digital", "1", "", "",
              f"tres {r['tres']}, cuatro {r['cuatro']}; {plain(r['Behaviour'])}", "none (no readback, GAP-12)" if "Relay" in r["Signal"] else "none",
              "", "drivers/harness.h", fsrs_of("506, 701, 706"), "relay / orientation", "B"])

regs = [[plain(r["Region"]), plain(r["Address"]), f"{plain(r['Content / safety relevance'])}; size {r['Size']}; protection: {plain(r['Protection required'])}"]
        for r in next(r for h, r in T if h[0] == "Region")]
timing = [[plain(r["Parameter"]), plain(r["Value at baseline"]), "", plain(r["Confirmation"])]
          for r in next(r for h, r in T if h[0] == "Parameter")]
for r in rx:
  timing.append([f"RX {plain(r['Addr'])} {r['Name']}", r["Rate"], "timeout max(10 periods, 1 s), evaluated at 1 Hz (TSR-401: ≤ 0.2 s)", "WP-S-04"])
fm = []
for h, rows in tables(a04):
  if h and h[0] == "ID" and "Failure mode" in h:
    for r in rows:
      if re.match(r"E-0[345]", r["Element"]):
        fm.append([f"{r['ID']} {plain(r['Element'])}", plain(r["Failure mode"]), plain(r["Detection (today)"]),
                   plain(r["Mechanism (today)"]) + "; required: " + plain(r["Gap / required"])])
init = [[plain(r["Mode (MCU)"]), plain(r["Entered by"]), f"relay {plain(r['Relay'])}; CAN TX {plain(r['CAN TX'])}", plain(r["Safety relevance"])]
        for r in next(r for h, r in T if h[0] == "Mode (MCU)")]

wb = Workbook()
wb.remove(wb.active)


def sheet(name, header, rows):
  ws = wb.create_sheet(name)
  ws.append(header)
  for r in rows:
    ws.append([plain(c) for c in r])


ws = wb.create_sheet("00_Title_Page")
for k, v in [("Title", "Hardware-Software Interface Specification (WP-S-05), converted for review"), ("Project", "LionDriver"),
             ("Document ID", "WP-S-05"), ("Revision", "0.1"), ("Status", "Draft"), ("Author", "Assurance team (initial draft)"),
             ("Approver", "Safety manager"), ("Linked TSC", "WP-S-02 v0.2 / WP-S-03 v0.2")]:
  ws.append(["", k, v])
sheet("01_Document_Control", ["Revision", "Date", "Change", "Author"],
      [("0.1", "2026-10-11", "Initial HSI at baseline 8b8c6ae", "Assurance team")])
sheet("02_HSI_Signal_Catalog", ["Signal name", "Direction", "Data type", "Bit width", "Range", "Units", "Encoding",
      "Integrity protection", "Validity bit", "Owner", "Linked FSR", "Linked mechanism", "ASIL"], sig)
sheet("03_Register_Map", ["Register / region", "Address", "Description"], regs)
sheet("04_Timing_Specification", ["Signal", "Sample rate", "Max age", "Latency budget / note"], timing)
sheet("05_Failure_Modes_and_Reactions", ["Signal / element", "Failure mode", "Detection mechanism", "Reaction"], fm)
sheet("06_Initialization_Sequence", ["State", "Entered by", "Outputs", "Safety relevance"], init)
sheet("07_Cross_Reference", ["HSI", "TSR / HWSR"], [(r["HSI"], plain(r["TSR / HWSR"])) for r in summary])
sheet("09_Test_Cases", ["Test ID", "Signal", "Test type", "Expected behavior"], [])
sheet("10_References", ["Reference"], [("WP-S-02",), ("WP-S-03",), ("WP-S-04",), ("WP-H-01",), ("WP-W-02",), ("WP-A-04 §10",)])
wb.save(OUT)
print(f"signals={len(sig)} regs={len(regs)} timing={len(timing)} fm={len(fm)} init={len(init)}")
