"""Render every row of a hazard-scene sheet and write the results back (render-tool-plan.md §5, piece 5).

For each row of each method sheet, the engine (engine.py) makes the scene and exports it (the plant or the preset's
stated assumptions), renders the key-event stills with Blender, cached by render key so rows with the same picture
share one render, and composes the row's own dashboard with its own card. The Result columns get the status, a link
to the dashboard, the contact, the smallest gap and TTC, and the motion source. The dashboards go beside the sheet in
<sheet>-dashboards/ as JPEG.

Blender: `blender` on the PATH, a Python with the bpy module (this one), or LIONDRIVER_BLENDER (a command that runs a
script, e.g. "blender -b -P" or "/opt/bpy/bin/python"). The purchased Corolla mesh is used when present
(assurance/sim/assets, ../blender/hazard_scene.py) or given with --vehicle, otherwise the stand-in; the status says
which.

  python3 assurance/sim/render-tool/run_sheet.py my-sheet.xlsx
  python3 assurance/sim/render-tool/run_sheet.py my-sheet.xlsx --no-render     # outcome only, about a second a row
  python3 assurance/sim/render-tool/run_sheet.py my-sheet.xlsx --only F-01/M03/OS-01/W02 --samples 8
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from openpyxl import load_workbook

import engine as en
import row_to_scene as rs
import template


def progress(e: dict) -> None:
  if e["stage"] == "still":
    print(f"  {e['row']}: still {e['done']}/{e['total']}", flush=True)


def run(sheet: Path, args) -> int:
  wb = load_workbook(sheet)
  eng = en.Engine(en.Settings(samples=args.samples, res=args.res, standin=args.standin, vehicle=args.vehicle))
  out_dir = args.out_dir or sheet.with_name(f"{sheet.stem}-dashboards")
  failed = 0
  for ad in rs.load_adapters():
    if ad["method"] not in wb.sheetnames:
      continue
    ws = wb[ad["method"]]
    h = template.header(ws)
    for r, row in template.rows(ws):
      if args.only and str(row["Row ID"]) not in args.only:
        continue
      res = eng.run(row, ad, None if args.no_render else out_dir, progress if args.verbose else lambda e: None)
      cells = {k: None for k, _, _ in rs.RESULTS}
      cells.update(res.outcome or {})
      cells["Status"] = res.status(rendered=not args.no_render)
      link = ws.cell(r, h["Dashboard"])
      if res.dashboard and not res.error:
        cells["Dashboard"] = res.dashboard.name
        link.hyperlink = os.path.relpath(res.dashboard, sheet.parent)
      else:
        link.hyperlink = None
      for k, v in cells.items():
        ws.cell(r, h[k]).value = v
      if res.error:
        failed += 1
        print(f"{res.row}: {cells['Status']}", file=sys.stderr)
      else:
        print(f"{res.row}: {cells['Status']}; contact {cells['Contact']}")
  wb.save(sheet)
  return 1 if failed and args.strict else 0


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("sheet", type=Path)
  ap.add_argument("--only", nargs="+", help="Row IDs to run (default: every row)")
  ap.add_argument("--no-render", action="store_true", help="export and write the outcome; no Blender")
  ap.add_argument("--out-dir", type=Path, help="where the dashboards go (default: <sheet>-dashboards beside it)")
  ap.add_argument("--standin", action="store_true", help="draw every car with the stand-in, not the purchased mesh")
  ap.add_argument("--vehicle", type=Path, help="the ego GLB (default: hazard_scene.py's, the purchased mesh if present)")
  ap.add_argument("--samples", type=int, default=16, help="Cycles samples (hazard_scene.py)")
  ap.add_argument("--res", default="1280x720", help="chase still resolution (hazard_scene.py)")
  ap.add_argument("--strict", action="store_true", help="exit 1 if any row cannot be drawn")
  ap.add_argument("--verbose", action="store_true", help="print every still as it is made")
  args = ap.parse_args(argv)
  return run(args.sheet, args)


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
