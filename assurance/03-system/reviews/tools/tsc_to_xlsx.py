# ruff: noqa: E501
"""Map the LionDriver TSC work products (WP-S-02/03/04/05, WP-A-03, WP-C-03/04 and the System FMEA) onto the tsc-builder tab layout.

Usage: python3 tsc_to_xlsx.py <assurance dir> <out.xlsx>

Content is copied from the source tables; nothing is invented. Derived fields are marked in the column name or
filled only from an explicit source (e.g. FSR -> SG from WP-C-04 §9, FTTI from WP-C-04 §3).

Every table is found by its column headings, and a cell is read by heading name. When a source no longer has a
table, column or key the converter needs, it stops with a message naming the document, the section and the missing
heading (exit status 2), never with a bare KeyError.

Sheet 08_System_FMEA: WP-A-04 §10 retired its System FMEA table SFMEA-01…40 in v1.19 (DQ-127 A). The rows now come
from the System FMEA of record, 08-analyses/fmea/analyses/system-fmea.yaml, one row per failure mode. "Linked SG" is
traced from each end effect's hazard (HZ-) through fmea/hara-mapping.yaml to its WP-C-03 hazardous events and the
WP-C-03 §6 goals whose "Source HEs" list them.
"""
import re
import sys
from pathlib import Path

from openpyxl import Workbook

SOURCES = {
  "WP-C-03": "02-concept/WP-C-03-hara.md",
  "WP-C-04": "02-concept/WP-C-04-functional-safety-concept.md",
  "WP-S-02": "03-system/WP-S-02-technical-safety-requirements.md",
  "WP-S-03": "03-system/WP-S-03-technical-safety-concept-architecture.md",
  "WP-S-04": "03-system/WP-S-04-timing-ftti-budget.md",
  "WP-S-05": "03-system/WP-S-05-hsi-specification.md",
  "WP-A-03": "08-analyses/WP-A-03-dependent-failure-analysis.md",
  "WP-A-04": "08-analyses/WP-A-04-system-fta-fmea.md",
  "system-fmea.yaml": "08-analyses/fmea/analyses/system-fmea.yaml",
  "hara-mapping.yaml": "08-analyses/fmea/hara-mapping.yaml",
}

SHEETS = ["00_Title_Page", "01_Document_Control", "02_FSRs_From_FSC", "03_System_Architecture", "04_Safety_Mechanism_Catalog",
          "05_TSR_Catalog", "06_HSI_Specification", "07_Timing_Budget", "08_System_FMEA", "09_DFA", "10_Verification",
          "11_HW_Handoff", "12_SW_Handoff"]


class SourceError(Exception):
  """A source no longer has a table, column or key the converter reads."""


class Table:
  def __init__(self, section, header):
    self.section, self.header, self.rows = section, header, []


def read(root, doc):
  path = Path(root) / SOURCES[doc]
  if not path.is_file():
    raise SourceError(f"{doc}: source file {path} not found")
  return path.read_text(encoding="utf-8")


def all_tables(text):
  """Every Markdown table as Table(section, header, rows); rows are dicts keyed by heading, padded to the header."""
  out, cur, section = [], None, ""
  for line in text.splitlines():
    if line.startswith("#"):
      section = line.lstrip("#").strip()
    if line.startswith("|"):
      cells = [c.strip().replace("\x00", "|") for c in line.replace("\\|", "\x00").strip().strip("|").split("|")]
      if cur is None:
        cur = Table(section, cells)
        out.append(cur)
      elif set("".join(cells)) <= set("-: "):
        continue
      else:
        cells += [""] * (len(cur.header) - len(cells))
        cur.rows.append(dict(zip(cur.header, cells, strict=False)))
    else:
      cur = None
  return out


def has(header, col):
  return any(c in header for c in col) if isinstance(col, tuple) else col in header


def name(col):
  return " or ".join(f"'{c}'" for c in col) if isinstance(col, tuple) else f"'{col}'"


def find(tables, doc, what, need, first=None, somewhere=()):
  """The tables of `doc` whose first heading is `first` (when given) and that have every column in `need`.

  A tuple in `need` is a set of alternatives (one of them must be there). Each column in `somewhere` must be in at
  least one of the matched tables (columns that only some variants of a table carry). Raises SourceError naming the
  missing heading(s) of the closest table when nothing matches."""
  cands = [t for t in tables if first is None or (t.header and t.header[0] == first)]
  good = [t for t in cands if all(has(t.header, c) for c in need)]
  if not good:
    pool = cands or tables
    if not pool:
      raise SourceError(f"{doc}: no tables found (looking for {what})")
    best = max(pool, key=lambda t: sum(has(t.header, c) for c in need))
    missing = ", ".join(name(c) for c in need if not has(best.header, c))
    raise SourceError(f"{doc}: {what}: no table has the column(s) {', '.join(name(c) for c in need)}. "
                      + f"The closest, in section '{best.section}', is missing {missing} (its headings: {' | '.join(best.header)})")
  for col in somewhere:
    if not any(has(t.header, col) for t in good):
      sections = "; ".join(sorted({t.section for t in good}))
      raise SourceError(f"{doc}: {what}: column {name(col)} is in none of the matched tables (sections: {sections})")
  return good


def cell(row, *cols):
  """The first of `cols` that the row has (alternative headings of one column)."""
  for c in cols:
    if c in row:
      return row[c]
  return ""


def key(d, k, where):
  if not isinstance(d, dict) or k not in d:
    raise SourceError(f"{where}: key '{k}' not found")
  return d[k]


def version(text, doc):
  m = re.search(r"^\| Version \| ([0-9][0-9.]*)", text, re.M)
  if not m:
    raise SourceError(f"{doc}: header row '| Version | …' not found")
  return m.group(1)


def plain(s):
  return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(s)).replace("**", "").replace("`", "")


def expand_he(text):
  """HE IDs in a WP-C-03 'Source HEs' cell: 'HE-01.1–01.6, HE-02.3' -> HE-01.1 … HE-01.6, HE-02.3."""
  out = set()
  for g, a, g2, b in re.findall(r"HE-(\d\d)\.(\d+)(?:[–-](\d\d)\.(\d+))?", text):
    if b and g2 == g:
      out.update(f"HE-{g}.{k}" for k in range(int(a), int(b) + 1))
    else:
      out.add(f"HE-{g}.{a}")
  return out


def ms(text):
  """First duration in a cell such as '≤ 0.5 s' or '≤ 200 ms', in ms; the text itself when it has none."""
  m = re.search(r"(\d+(?:\.\d+)?)\s*(ms|s)\b", text)
  if not m:
    return text
  v = float(m.group(1)) * (1 if m.group(2) == "ms" else 1000)
  return int(v) if v == int(v) else v


def build(root):
  """Read the sources under `root` (the assurance directory) and return the workbook and a row-count summary."""
  import yaml

  text = {d: read(root, d) for d in SOURCES}
  T = {d: all_tables(t) for d, t in text.items() if d.startswith("WP-")}

  # FSR -> SG from WP-C-04 §9 (first SG marked); the SG columns are the headings SG-nn of the trace table
  trace = find(T["WP-C-04"], "WP-C-04", "§9 FSR → SG trace", ["FSR", "SG-01"], first="FSR")
  fsr_sg = {}
  for t in trace:
    sg_cols = [h for h in t.header if re.fullmatch(r"SG-\d\d", h)]
    for r in t.rows:
      sgs = [sg for sg in sg_cols if r[sg] == "●"]
      for fid in re.findall(r"\d\d\.\d\d", r["FSR"]):
        fsr_sg.setdefault("FSR-" + fid, sgs[0] if sgs else "")
      m = re.match(r"FSR-(\d\d)\.(\d\d)[–-](\d\d)\.(\d\d)", r["FSR"])
      if m and m.group(1) == m.group(3):
        for k in range(int(m.group(2)), int(m.group(4)) + 1):
          fsr_sg.setdefault(f"FSR-{m.group(1)}.{k:02d}", sgs[0] if sgs else "")
  # FTTI per SG from WP-C-04 §3 (first duration of "Preliminary FTTI", in ms)
  ftti = {}
  for t in find(T["WP-C-04"], "WP-C-04", "§3 safety goals", ["SG", "Preliminary FTTI"], first="SG"):
    for r in t.rows:
      if re.fullmatch(r"SG-\d\d", plain(r["SG"])):
        ftti.setdefault(plain(r["SG"]), ms(plain(r["Preliminary FTTI"])))

  fsrs = []
  for t in find(T["WP-C-04"], "WP-C-04", "§5 FSR tables", ["ID", "Requirement", "ASIL", "Alloc"], first="ID"):
    for r in t.rows:
      if r["ID"].startswith("FSR-"):
        sg = fsr_sg.get(r["ID"]) or "SG-" + r["ID"][4:6]
        fsrs.append((r["ID"], sg, r["ASIL"], "", r["Alloc"], r["Requirement"], ftti.get(sg, "")))

  tsrs = []
  for t in find(T["WP-S-02"], "WP-S-02", "TSR tables", ["ID", "Parent", "ASIL", "Alloc", "Verif", ("Requirement", "Requirement (summary)")],
                first="ID", somewhere=["SM", "Timing"]):
    for r in t.rows:
      if r["ID"].startswith("TSR-"):
        parents = re.findall(r"FSR-\d\d\.\d\d", r["Parent"])
        alloc = r["Alloc"]
        typ = "HW-TSR" if re.search(r"P-HW|HAR", alloc) and not re.search(r"P-SW|SoC", alloc) else "SW-TSR"
        for par in (parents or [r["Parent"]]):  # one row per (TSR, parent FSR)
          tsrs.append((r["ID"], par, r["ASIL"], typ, r.get("SM", ""), alloc,
                       cell(r, "Requirement", "Requirement (summary)"), r["Verif"], r.get("Timing", "")))
  tsr_fsr = {}
  for t in tsrs:
    tsr_fsr.setdefault(t[0][4:], t[1])

  mechs = []
  for t in find(T["WP-S-03"], "WP-S-03", "safety mechanism catalogue", ["SM", "Mechanism", "Element", "TSR", "DC target"], first="SM"):
    for r in t.rows:
      nums = set()
      for a, b in re.findall(r"(\d{3})(?:[–-](\d{3}))?", r["TSR"]):
        nums.update(f"{x:03d}" for x in range(int(a), int(b or a) + 1))
      fids = sorted({x[1] for x in tsrs if x[0][4:] in nums and x[1].startswith("FSR-")})
      for fid in fids or [""]:
        asil = next((x[2] for x in tsrs if x[1] == fid and x[0][4:] in nums), "")
        mechs.append((fid, asil, "", r["Element"], r["SM"], r["Mechanism"], r["DC target"], "", "[primary]"))

  arch = []
  hw_map = {"E-04a": ("HW-01", "Safety MCU STM32H7", "STM32H7 (part number TBD, WP-H-02 UK-02)"),
            "E-04b": ("HW-02", "Device hardware (SoC, cameras, IMU, display, speaker, PSU)", "comma 3X / comma four"),
            "E-05": ("HW-03", "Toyota TSS2 harness with intercept relay", "comma harness")}
  sp_map = {"E-01": "SP-01", "E-02": "SP-02", "E-03a": "SP-03", "E-03b": "SP-04"}
  for t in find(T["WP-S-03"], "WP-S-03", "architectural elements", ["Element", "Integrity"], first="Element"):
    for r in t.rows:
      eid = (r["Element"].split() or [""])[0]
      if eid in hw_map:
        hid, nm, part = hw_map[eid]
        arch.append((hid, nm, part, eid, "shared device supply" if eid != "E-05" else "vehicle 12 V via harness", "see WP-S-05 §3"))
      elif eid in sp_map:
        host = "HW-01" if eid.startswith("E-03") else "HW-02"
        arch.append((sp_map[eid], r["Element"], host, eid, "bare metal" if host == "HW-01" else "AGNOS Linux", r["Integrity"]))

  timing = []
  budget = {}
  for t in find(T["WP-S-04"], "WP-S-04", "FTTI budget per goal", ["SG / fault class", "FTTI", "FDTI budget", "FRTI budget"], first="SG / fault class"):
    for r in t.rows:
      for sg in re.findall(r"SG-0\d(?:/0\d)?", r["SG / fault class"]):
        for part in sg.replace("SG-", "").split("/"):
          budget.setdefault("SG-" + part.zfill(2), (r["FTTI"], r["FDTI budget"], r["FRTI budget"]))
  for f in fsrs:
    b = budget.get(f[1], ("", "", ""))
    timing.append((f[0], f[2], b[0], b[1], b[2]))

  # WP-S-05 §2 interface summary (not the §11.4 responsibilities table, which also starts with "HSI")
  hsi = []
  for t in find(T["WP-S-05"], "WP-S-05", "§2 interface summary", ["HSI", "Interface", "HW resource", "Safety relevance", "ASIL", "TSR / HWSR"], first="HSI"):
    for r in t.rows:
      fsr = ""
      for x in re.findall(r"TSR-(\d{3})", r["TSR / HWSR"]):
        if x in tsr_fsr:
          fsr = tsr_fsr[x]
          break
      hsi.append((f"{r['HSI']} {r['Interface']}", "", fsr, r["Safety relevance"], r["HW resource"], "", "", "", r["ASIL"]))

  # System FMEA (system-fmea.yaml; WP-A-04 §10 retired its table in v1.19). HZ -> HE (hara-mapping) -> SG (WP-C-03 §6)
  he_sg = {}
  for t in find(T["WP-C-03"], "WP-C-03", "§6 safety goals", ["ID", "Safety goal", "Source HEs"], first="ID"):
    for r in t.rows:
      sg = plain(r["ID"]).strip()
      if re.fullmatch(r"SG-\d\d", sg):
        for he in expand_he(r["Source HEs"]):
          he_sg.setdefault(he, set()).add(sg)
  hmap = yaml.safe_load(text["hara-mapping.yaml"])
  hz_sg = {}
  for h in key(hmap, "hazards", "hara-mapping.yaml"):
    hz = key(h, "second", "hara-mapping.yaml hazards[]")
    hz_sg[hz] = {sg for he in key(h, "events", f"hara-mapping.yaml hazards[{hz}]") for sg in he_sg.get(he, ())}
  sfm = yaml.safe_load(text["system-fmea.yaml"])
  where = "system-fmea.yaml"
  el_name = {key(s, "id", f"{where} structure[]"): key(s, "name", f"{where} structure[]") for s in key(sfm, "structure", where)}
  fmea = []
  for fm in key(sfm, "failure_modes", where):
    fid = key(fm, "id", f"{where} failure_modes[]")
    w = f"{where} {fid}"
    eff = {}
    for e in key(fm, "effects", w):
      eff.setdefault(key(e, "level", f"{w} effects[]"), []).append(e)
    end = eff.get("end", [])
    local = "; ".join(key(e, "description", f"{w} effects[]") for e in eff.get("local", []))
    veh = "; ".join(key(e, "description", f"{w} effects[]") for e in end)
    sgs = sorted({sg for e in end if e.get("hazard") for sg in hz_sg.get(e["hazard"], ())})
    mech = "; ".join(key(m, "description", f"{w} safety_mechanisms[]") for m in key(fm, "safety_mechanisms", w))
    el = key(fm, "element", w)
    fmea.append((f"{el} {el_name.get(el, '')}".strip(), f"{fid} {key(fm, 'failure_mode', w)}", local, veh, ", ".join(sgs), mech, ""))

  dfa = []
  for t in find(T["WP-A-03"], "WP-A-03", "independence claims", ["Claim", "Not controlled DFIs", "Partly controlled DFIs", "Condition to accept", "Verdict (current baseline)"], first="Claim"):
    for r in t.rows:
      dfa.append((r["Claim"], (r["Not controlled DFIs"] + "; " + r["Partly controlled DFIs"]).strip("; "),
                  "Yes" if r["Not controlled DFIs"].strip() not in ("", "—") else "Partly", r["Condition to accept"], r["Verdict (current baseline)"]))

  v = {d: version(text[d], d) for d in ("WP-C-04", "WP-S-02", "WP-S-03", "WP-S-04", "WP-S-05", "WP-A-03", "WP-A-04")}
  sfm_rev = key(key(sfm, "analysis", where), "revision", f"{where} analysis")

  wb = Workbook()
  wb.remove(wb.active)

  def sheet(nm, header, rows):
    ws = wb.create_sheet(nm)
    ws.append(header)
    for r in rows:
      ws.append([plain(c) for c in r])

  ws = wb.create_sheet("00_Title_Page")
  for k, val in [("Title", "Technical Safety Concept (TSC): WP-S-02 TSRs, WP-S-03 architecture, WP-S-04 timing, WP-S-05 HSI, WP-A-03 DFA, System FMEA (system-fmea.yaml)"),
                 ("Project", "LionDriver"), ("TSC Document ID", "WP-S-02 / WP-S-03 (with WP-S-04, WP-S-05, WP-A-03, WP-A-04, system-fmea.yaml)"),
                 ("Revision", "; ".join(f"{d} {v[d]}" for d in ("WP-S-02", "WP-S-03", "WP-S-04", "WP-S-05", "WP-A-03", "WP-A-04"))
                  + f"; System FMEA rev {sfm_rev}"), ("Status", "Draft"),
                 ("Author", "Assurance team (initial draft)"), ("Approver", "Safety manager"), ("Linked FSC", f"WP-C-04 v{v['WP-C-04']}")]:
    ws.append(["", k, val])
  sheet("01_Document_Control", ["Revision", "Date", "Change", "Author"], [
    ("0.1", "2026-10-11", "Initial TSC set: WP-S-02…05, WP-A-03/04 at baseline 8b8c6ae", "Assurance team"),
    ("0.2", "2026-10-12", "WP-S-02 TSR-621…625; WP-S-03 SM-29…SM-42; WP-A-03 DFI-24…26; WP-A-04 FTAs for SG-02, 04, 05, 06, 07", "Assurance team"),
    ("0.3", "2026-10-12", "RR-2026-005 follow-up: TSR-516 triggers, TSR-303, TSR-501 0.1 s, TSR-626, 627, 711; SG-07 FTTI; WP-S-05 signal catalogue", "Assurance team")])
  sheet("02_FSRs_From_FSC", ["FSR_ID", "SG_ID", "ASIL", "Branch", "Linked Node", "Functional Safety Requirement", "FTTI (ms)"], fsrs)
  sheet("03_System_Architecture", ["Component ID", "Name", "Part / hosted on", "Allocated nodes", "Power domain / OS", "Clock domain / integrity"], arch)
  sheet("04_Safety_Mechanism_Catalog", ["FSR_ID", "Allocated ASIL", "Branch", "Linked Node", "Mechanism ID", "Mechanism Name", "DC target", "Detection time", "Selection"], mechs)
  sheet("05_TSR_Catalog", ["TSR_ID", "FSR_ID", "Allocated ASIL", "Type", "Mechanism", "Linked Node", "Technical Safety Requirement", "Verification Method", "Timing"], tsrs)
  sheet("06_HSI_Specification", ["HSI Signal", "Direction", "Linked FSR", "Mechanism", "Encoding / HW resource", "Update rate", "Integrity", "Failure reaction", "Allocated ASIL"], hsi)
  sheet("07_Timing_Budget", ["FSR_ID", "Allocated ASIL", "FTTI", "FDTI", "FRTI"], timing)
  sheet("08_System_FMEA", ["Element", "Failure mode", "Local effect", "Vehicle effect", "Linked SG", "Existing mechanism", "DC target"], fmea)
  sheet("09_DFA", ["Decomposition pair / independence claim", "Coupling factor", "Coupling present", "Mitigation", "Conclusion"], dfa)
  sheet("10_Verification", ["TSR_ID", "Verification Method"], [(t[0], t[7]) for t in tsrs])
  sheet("11_HW_Handoff", ["TSR_ID", "Allocated HW element", "Note"], [(t[0], t[5], "WP-H-01 HWSR refinement") for t in tsrs if t[3] == "HW-TSR"])
  sheet("12_SW_Handoff", ["TSR_ID", "Allocated SW element", "Note"], [(t[0], t[5], "WP-W-02 SWSR refinement") for t in tsrs if t[3] == "SW-TSR"])
  counts = {"fsrs": len(fsrs), "tsrs": len(tsrs), "mechs": len(mechs), "arch": len(arch), "hsi": len(hsi),
            "timing": len(timing), "fmea": len(fmea), "dfa": len(dfa)}
  empty = [k for k, n in counts.items() if n == 0]
  if empty:
    raise SourceError(f"no rows read for: {', '.join(empty)} (the source tables were found but held no rows)")
  return wb, counts


def main(argv):
  if len(argv) != 3:
    print("usage: tsc_to_xlsx.py <assurance dir> <out.xlsx>", file=sys.stderr)
    return 2
  try:
    wb, counts = build(Path(argv[1]))
  except SourceError as e:
    print(f"tsc_to_xlsx: {e}", file=sys.stderr)
    return 2
  wb.save(Path(argv[2]))
  print(" ".join(f"{k}={n}" for k, n in counts.items()))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
