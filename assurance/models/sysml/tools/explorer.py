#!/usr/bin/env python3
"""Build the interactive model explorer (generated/explorer.html) from the SysML model.

One self-contained HTML page: the four views, the model tree, and an inspector that shows for
any element its integrity, source, ports, interfaces, cereal services, safety mechanisms and the
requirements allocated to it (resolved as in check_model.py M8). No network access is needed.

  explorer.py                  write generated/explorer.html
  explorer.py --check          fail if generated/explorer.html is out of date
  explorer.py --fragment PATH  also write the page without the document wrapper (for publishing)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_model
import render_views
import sysml_lite
import svgkit as k

OUT = render_views.OUT / "explorer.html"
VIEW_ORDER = ["V-01", "V-03", "V-02", "V-04", "V-05", "V-06", "V-07"]


def requirement_index(m: sysml_lite.Model) -> dict[str, list[dict]]:
  units: dict[str, list[str]] = defaultdict(list)
  for e in m.elements.values():
    u = e.meta.get("Unit")
    if u:
      units[u["id"]].append(e.short)
  out: dict[str, list[dict]] = defaultdict(list)
  # requirements in the model: from their satisfy relationships, with the cases that verify them
  for r in m.requirements.values():
    for p in r.satisfied_by:
      out[p].append({"id": r.short, "kind": r.short.split("-")[0].lower(), "asil": str(r.values.get("asil", "") or ""),
                     "text": r.doc[:220], "alloc": str(r.values.get("allocText", "")), "via": "satisfy",
                     "cases": sorted(r.verified_by)})
  # software and hardware safety requirements are not modelled yet: from their allocated_to text
  for it in check_model.load_items():
    text = it.get("allocated_to")
    if not text or it["id"] in m.requirements:
      continue
    _, resolved, _ = check_model.resolve_allocation(m, str(text), units)
    paths = set()
    for token, _ in resolved:
      e = m.find(token)
      if e is not None:
        paths.add(e.path)
      elif token in units:
        paths.update(m.find(s).path for s in units[token])
    for p in paths:
      out[p].append({"id": it["id"], "kind": it.get("kind", ""), "asil": str(it.get("asil", "") or ""),
                     "text": str(it.get("text", "")).replace("`", "")[:220], "alloc": str(text), "via": "allocated_to",
                     "cases": []})
  return out


def build_data(m: sysml_lite.Model) -> dict:
  reqs = requirement_index(m)
  elements = {}
  for e in m.elements.values():
    if e.kind != "part":
      continue
    safety = e.meta.get("Safety") or {}
    src = e.meta.get("Source") or {}
    unit = e.meta.get("Unit") or {}
    elements[e.path] = {
      "path": e.path, "ident": e.ident, "short": e.short, "name": e.name,
      "title": render_views.Canvas.default_title(e), "def": e.definition, "classes": e.classes,
      "integrity": e.integrity(), "label": safety.get("label", ""), "scope": e.scope(), "doc": e.doc,
      "source": {"wp": src.get("workProduct"), "clause": src.get("clause"),
                 "paths": sysml_lite._as_list(src.get("paths"))} if src else None,
      "unit": unit.get("id"), "build": str(unit.get("build", "")).split("::")[-1] or None,
      "ports": [p.name for p in e.ports], "children": [c.path for c in e.children],
      "parent": e.parent.path if e.parent else None, "performs": e.performs,
      "reqs": sorted(reqs.get(e.path, []), key=lambda r: r["id"]),
    }
  conns = []
  for c in m.connections:
    conns.append({"name": c.name, "kind": c.kind, "def": c.definition, "id": c.interface_id,
                  "a": c.ends[0], "b": c.ends[1], "doc": c.doc,
                  "service": c.values.get("service"), "rate": c.values.get("rateHz"),
                  "ffi": sysml_lite._as_list((c.meta.get("FfiClaim") or {}).get("claims")),
                  "tsr": sysml_lite._as_list((c.meta.get("InterfaceId") or {}).get("tsr"))})
  mechs = {s: {"id": s, "name": me.name, "doc": me.doc, "covers": me.covers, "dc": me.dc_target,
               "tsr": me.tsr, "by": me.performers} for s, me in m.mechanisms.items()}
  views = {v: {"id": v, "name": m.views[v].name, "doc": m.views[v].doc, "def": m.views[v].definition}
           for v in VIEW_ORDER}
  parts = sum(1 for e in m.elements.values() if e.kind == "part")
  return {"elements": elements, "connections": conns, "mechanisms": mechs, "views": views,
          "aliases": m.aliases, "digest": render_views.model_digest(m),
          "stats": {"parts": parts, "connections": len(m.connections), "mechanisms": len(m.mechanisms),
                    "requirements": sum(len(v) for v in reqs.values()), "modelled": len(m.requirements),
                    "cases": len(m.verifications)}}


STYLE = (HERE / "explorer_assets" / "explorer.css").read_text(encoding="utf-8")

SCRIPT = (HERE / "explorer_assets" / "explorer.js").read_text(encoding="utf-8")


def page(m: sysml_lite.Model, figures: dict[str, str]) -> str:
  data = build_data(m)
  st = data["stats"]
  layout = render_views.tomllib.loads(render_views.LAYOUT.read_text(encoding="utf-8"))["views"]
  tabs, sheets = [], []
  for vid in VIEW_ORDER:
    spec = layout[vid]
    tabs.append(f'<button class="tab" role="tab" data-v="{vid}"><span class="vid">{vid}</span>{k.escape(spec["title"])}</button>')
    first = spec["functions"][0].lower().replace("-", "") if "functions" in spec else ""
    svg = figures[spec["file"].format(f=first)]  # a view drawn per function shows its first function here
    sheets.append(f'<template id="svg-{vid}">{svg}</template>')
  blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
  return f"""<title>LionDriver Model Explorer</title>
<style>{STYLE}</style>
<div class="app">
  <header>
    <div class="brand"><h1>LionDriver architecture model</h1>
      <p>SysML v2 model of LD-SDA · generated from assurance/models/sysml · draft, not reviewed</p></div>
    <div class="stats"><span><b>{st['parts']}</b> parts</span><span><b>{st['connections']}</b> connections</span>
      <span><b>{st['mechanisms']}</b> safety mechanisms</span><span><b>{st['modelled']}</b> requirements in the model</span><span><b>{st['cases']}</b> verification cases</span><span><b>{st['requirements']}</b> requirement allocations resolved</span>
      <span class="digest" title="Digest of the model and layout files">model {data['digest']}</span></div>
  </header>
  <main>
    <section class="panel tree-panel" aria-label="Model tree">
      <div class="tree-head"><h2>Model</h2><input id="q" type="search" placeholder="Filter: E-03a, pandad, U-SAF-TOY" aria-label="Filter the model tree"></div>
      <div class="tree" id="tree" role="tree"></div>
    </section>
    <section class="panel stage" aria-label="Views">
      <div class="tabs" role="tablist">{''.join(tabs)}
        <div class="tools"><button class="tool" id="zout" aria-label="Zoom out">−</button>
          <button class="tool" id="zfit">Fit</button><button class="tool" id="zin" aria-label="Zoom in">+</button></div></div>
      <div class="viewport" id="vp"><div class="sheet" id="sheet"></div></div>
      <div class="caption" id="cap"></div>
    </section>
    <section class="panel inspector" aria-label="Inspector"><div class="insp" id="insp"></div></section>
  </main>
</div>
{''.join(sheets)}
<script type="application/json" id="model-data">{blob}</script>
<script>{SCRIPT}</script>
"""


def document(fragment: str) -> str:
  return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n' +
          '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' +
          f'</head>\n<body>\n{fragment}</body>\n</html>\n')


def main(argv: list[str]) -> int:
  m = sysml_lite.load()
  figures = render_views.render_all(m)
  frag = page(m, figures)
  html = document(frag)
  if "--fragment" in argv:
    Path(argv[argv.index("--fragment") + 1]).write_text(frag, encoding="utf-8")
  if "--check" in argv:
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != html:
      print(f"FAIL {OUT.name} is out of date (run tools/explorer.py)")
      return 1
    print("explorer: up to date")
    return 0
  OUT.write_text(html, encoding="utf-8")
  print(f"explorer: wrote {OUT.relative_to(render_views.SYSML_DIR)} ({len(html) // 1024} KiB)")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
