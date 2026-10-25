#!/usr/bin/env python3
"""Generate the architecture tables of the work products from the SysML model (SY-05, DQ-186).

  WP-S-03 §3.1  elements             parts E-0n with @Catalogue, and the EXT- elements
  WP-S-03 §3.3  interfaces           connections with @InterfaceId; the first of each row carries its text
  WP-S-03 §6    safety mechanisms    the SafetyMechanism actions of Mechanisms.sysml
  WP-W-03 §3.1  firmware catalogue   the panda.* elements under E-03 with @Catalogue and @Unit

Which side is the record is set in ../record.toml. Until the model has been reviewed (OI-8) the work products
are the record: --check fails when a table in a work product is not the table the model generates, so a change
to one needs the same change to the other. Once record.toml says "model", --write puts the generated tables into
the work products under a marker, and the tables are edited in the model only.

    python3 tools/gen_tables.py            # --check, and print the differences
    python3 tools/gen_tables.py --write    # write the tables into the work products (record = "model" only)

Standard library only (tomllib). Output is deterministic.
"""
from __future__ import annotations

import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sysml_lite  # noqa: E402

ROOT = HERE.parent
ASSURANCE = ROOT.parents[1]
RECORD = ROOT / "record.toml"
MARKER = "<!-- Generated from the SysML model (assurance/models/sysml, tools/gen_tables.py); edit the model, not this table. -->"


def natural(s: str) -> list:
  return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def tsr_cell(tsrs: list[str]) -> str:
  """TSR-1xx, TSR-401 … TSR-406 → '1xx, 401–406': tokens that are not plain numbers first, in order; numbers
  sorted, three or more consecutive as a range."""
  toks = [t[4:] if t.startswith("TSR-") else t for t in tsrs]
  other = [t for t in dict.fromkeys(toks) if not t.isdigit()]
  nums = sorted({int(t) for t in toks if t.isdigit()})
  out, i = list(other), 0
  while i < len(nums):
    j = i
    while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
      j += 1
    out += [f"{nums[i]}–{nums[j]}"] if j - i >= 2 else [str(n) for n in nums[i:j + 1]]
    i = j + 1
  return ", ".join(out) or "—"


def row(cells: list[str]) -> str:
  return "| " + " | ".join(cells) + " |"


def table(head: list[str], rows: list[list[str]]) -> list[str]:
  return [row(head), "|" + "---|" * len(head)] + [row(r) for r in rows]


def cat(e: sysml_lite.Element) -> dict:
  return e.meta.get("Catalogue") or {}


def label(e: sysml_lite.Element) -> str:
  return (e.meta.get("Safety") or {}).get("label", "")


def elements_table(m: sysml_lite.Model) -> list[str]:
  inside = sorted((e for e in m.elements.values() if e.short and re.fullmatch(r"E-0\d[ab]?", e.short) and cat(e)),
                  key=lambda e: natural(e.short))
  rows = [[f"{e.short} {cat(e)['name']}", cat(e)["description"], label(e), cat(e)["sources"]] for e in inside]
  ext = [e for e in m.root.children if e.short and e.short.startswith("EXT-") and cat(e)]
  if ext:
    srcs = {cat(e)["sources"] for e in ext}
    if len(srcs) != 1:
      raise sysml_lite.ModelError(f"EXT elements share one row in WP-S-03 §3.1 but name different sources: {srcs}")
    rows.append([", ".join(e.short for e in ext), ", ".join(cat(e)["description"] for e in ext), "AoU only", srcs.pop()])
  return table(["Element", "Description", "Integrity", "Main sources"], rows)


def interfaces_table(m: sysml_lite.Model) -> list[str]:
  by_id: dict[str, list[sysml_lite.Connection]] = defaultdict(list)
  for c in m.connections:
    if c.interface_id:
      by_id[c.interface_id].append(c)
  rows = []
  for ident in sorted(by_id, key=natural):
    heads = [c.meta["InterfaceId"] for c in by_id[ident] if c.meta["InterfaceId"].get("name")]
    if len(heads) > 1:
      raise sysml_lite.ModelError(f"{ident}: {len(heads)} connections carry the WP-S-03 §3.3 row, one may")
    if not heads:
      continue  # covered by a row labelled for several interfaces (IF-05/06)
    h = heads[0]
    lab = h.get("label") or ident
    ids = [ident] + ["IF-" + x for x in lab.split("/")[1:]]
    tsrs = [t for i in ids for c in by_id.get(i, []) for t in sysml_lite._as_list(c.meta["InterfaceId"].get("tsr"))]
    rows.append([lab, h["name"], h["between"], h["content"], h["relevance"], tsr_cell(tsrs), h["detail"]])
  covered = {i for r in rows for i in [r[0].split("/")[0]] + ["IF-" + x for x in r[0].split("/")[1:]]}
  missing = sorted(set(by_id) - covered, key=natural)
  if missing:
    raise sysml_lite.ModelError(f"no connection carries the WP-S-03 §3.3 row of {', '.join(missing)}")
  return table(["ID", "Interface", "Between", "Content", "Safety relevance", "TSRs", "Detail"], rows)


def mechanisms_table(m: sysml_lite.Model) -> list[str]:
  rows = []
  for sm in sorted(m.mechanisms, key=natural):
    x = m.mechanisms[sm]
    v = x.values
    rows.append([sm, x.doc, x.covers, str(v.get("element", "")), tsr_cell(x.tsr), str(v.get("status", "")),
                 x.dc_target, str(v.get("latent", ""))])
  return table(["SM", "Mechanism", "Covers (fault / failure mode)", "Element", "TSR", "Status", "DC target",
                "Latent-fault handling / start-up test"], rows)


def firmware_table(m: sysml_lite.Model) -> list[str]:
  rows = []
  for e in m.find("E-03").walk():
    if not (e.short and e.short.startswith("panda.") and cat(e)):
      continue
    unit = e.meta.get("Unit") or {}
    build = "**[ref]**" if str(unit.get("build", "")).endswith("reference") else "both"
    if cat(e).get("buildNote"):
      build += f" ({cat(e)['buildNote']})"
    rows.append([cat(e).get("name") or f"`{e.short}`", unit.get("id", "—"), cat(e)["sources"], cat(e)["description"],
                 build, cat(e).get("attribution") or label(e)])
  return table(["Element name", "Unit", "Files", "Responsibility at the baseline", "Build", "ASIL attribution"], rows)


WP_S03 = ASSURANCE / "03-system" / "WP-S-03-technical-safety-concept-architecture.md"
WP_W03 = ASSURANCE / "05-software" / "WP-W-03-software-architecture.md"
TABLES = [  # work product, heading the table sits under, renderer
  (WP_S03, "### 3.1 Elements", elements_table),
  (WP_S03, "### 3.3 Interfaces", interfaces_table),
  (WP_S03, "## 6. Safety mechanism catalogue", mechanisms_table),
  (WP_W03, "### 3.1 Component catalogue", firmware_table),
]


def record() -> str:
  r = tomllib.loads(RECORD.read_text(encoding="utf-8"))["record"]
  if r not in ("work-products", "model"):
    raise sysml_lite.ModelError(f"record.toml: record = {r!r}, expected 'work-products' or 'model'")
  return r


def locate(lines: list[str], heading: str) -> tuple[int, int, bool]:
  """Line range [a, b) of the first table under the heading, and whether the generated marker precedes it."""
  try:
    h = lines.index(heading)
  except ValueError:
    raise sysml_lite.ModelError(f"heading {heading!r} not found") from None
  a = next((i for i in range(h + 1, len(lines)) if lines[i].startswith("|") or lines[i].startswith("#")), None)
  if a is None or lines[a].startswith("#"):
    raise sysml_lite.ModelError(f"no table under {heading!r}")
  b = a
  while b < len(lines) and lines[b].startswith("|"):
    b += 1
  return a, b, lines[a - 2] == MARKER if a >= 2 else False


def differences(have: list[str], want: list[str]) -> list[str]:
  """Cell-level differences, keyed by the first cell of the row."""
  def rows(ls):
    return {r[0]: r for r in ([c.strip() for c in ln.strip().strip("|").split(" | ")] for ln in ls[2:])}
  h, w = rows(have), rows(want)
  head = [c.strip() for c in want[0].strip().strip("|").split(" | ")]
  out = []
  if have[:1] != want[:1]:
    out.append(f"header: {have[0]!r} in the document, {want[0]!r} from the model")
  for k in h.keys() - w.keys():
    out.append(f"row {k}: in the document, not in the model")
  for k in w.keys() - h.keys():
    out.append(f"row {k}: in the model, not in the document")
  for k in [k for k in w if k in h]:
    for col, a, b in zip(head, h[k], w[k], strict=False):
      if a != b:
        out.append(f"row {k}, {col}: {a!r} in the document, {b!r} from the model")
  if not out and [ln for ln in have if ln.startswith("|")] != want:
    out.append("rows in a different order")
  return out


def main(argv: list[str]) -> int:
  try:
    m = sysml_lite.load()
    mode = record()
    texts: dict[Path, list[str]] = {}
    problems = []
    for wp, heading, render in TABLES:
      lines = texts.setdefault(wp, wp.read_text(encoding="utf-8").split("\n"))
      a, b, marked = locate(lines, heading)
      want = render(m)
      name = f"{wp.name[:7]} {heading.lstrip('#').strip()}"
      if "--write" in argv and mode == "model":
        lines[a:b] = want
        if not marked:
          lines[a:a] = [MARKER, ""]
        continue
      for d in differences(lines[a:b], want):
        problems.append(f"{name}: {d}")
      if mode == "model" and not marked:
        problems.append(f"{name}: the model is the record (record.toml) but the table has no generated marker; run --write")
      if mode == "work-products" and marked:
        problems.append(f"{name}: generated marker present while record.toml says the work products are the record")
  except sysml_lite.ModelError as e:
    print(f"gen_tables: {e}", file=sys.stderr)
    return 1
  if "--write" in argv:
    if mode != "model":
      print("gen_tables: record.toml says the work products are the record (until the model review, OI-8); "
            "nothing written", file=sys.stderr)
      return 1
    for wp, lines in texts.items():
      wp.write_text("\n".join(lines), encoding="utf-8")
    print(f"gen_tables: wrote {len(TABLES)} tables")
    return 0
  for p in problems:
    print(p, file=sys.stderr)
  if problems:
    print("gen_tables: the work-product tables and the model disagree; change both together "
          f"(record: {mode})", file=sys.stderr)
    return 1
  print(f"gen_tables: {len(TABLES)} tables match the model (record: {mode})")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
