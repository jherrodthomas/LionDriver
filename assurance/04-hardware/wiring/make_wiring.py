#!/usr/bin/env python3
"""Draw the harness and bench wiring of 04-hardware from the WireViz sources in this folder.

Each `<name>.yaml` here is a WireViz harness file. For each one this script writes, next to it:

  <name>.svg      the drawing (embedded in WP-H-02 and WP-H-06)
  <name>.gv       the Graphviz source WireViz produced (deterministic, compared in --check)
  <name>.bom.tsv  the bill of materials WireViz produced

and, for all of them together, `wire-ends.tsv`: one row per wire of a cable and per line drawn between two pins (a
board net in the box drawing, a lead or probe on the benches), with a stable ID (`<drawing>.<cable>.<wire>` or `<drawing>.<A>.<pin>-<B>.<pin>`) and both ends. WP-H-03 FMEDA rows can cite
these IDs.

Tools (pinned, see requirements.txt): WireViz 0.4.1 (GPL-3.0, run as a tool, nothing is linked into the item) and
Graphviz `dot` (EPL-1.0) from Ubuntu 24.04 (`apt-get install graphviz`, 2.42.2 package, reports 2.43.0).

    python3 make_wiring.py           # rebuild every output
    python3 make_wiring.py --check   # fail if an output is stale or a source breaks a rule

--check always compares the .gv, .bom.tsv and wire-ends.tsv byte for byte. It compares the .svg byte for byte only
when `dot` reports the pinned version, because the SVG layout belongs to the Graphviz build; with another `dot` it
says so and checks that the SVG parses. The .gv files are what the SVGs are drawn from, so a current .gv with the
pinned `dot` gives the committed SVG.
"""

import csv
import io
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
WIREVIZ_VERSION = "0.4.1"
DOT_VERSION = "2.43.0"
WIRE_ENDS = HERE / "wire-ends.tsv"
OUT_SUFFIXES = (".svg", ".gv", ".bom.tsv")
# no HTML-like characters in labels (they break Graphviz HTML labels), no model names in repo files
FORBIDDEN = re.compile(r"[<>]")


def sources() -> list[Path]:
  return sorted(HERE.glob("*.yaml"))


def dot_version() -> str:
  try:
    out = subprocess.run(["dot", "-V"], capture_output=True, text=True, check=True).stderr
  except (OSError, subprocess.CalledProcessError):
    return ""
  m = re.search(r"version (\S+)", out)
  return m.group(1) if m else ""


def wireviz_version() -> str:
  import wireviz
  return getattr(wireviz, "__version__", "")


def _labels(text: str) -> list[str]:
  """All label strings of a source, for the character rule."""
  data = yaml.safe_load(text)
  out = []

  def walk(x):
    if isinstance(x, dict):
      for v in x.values():
        walk(v)
    elif isinstance(x, list):
      for v in x:
        walk(v)
    elif isinstance(x, str):
      out.append(x)
  walk(data.get("connectors", {}))
  walk(data.get("cables", {}))
  walk(data.get("metadata", {}))
  return out


def problems(path: Path) -> list[str]:
  """Rules a source must keep: a drawing code, no < or >, every pinlabel list as long as its pin list."""
  text = path.read_text(encoding="utf-8")
  data = yaml.safe_load(text)
  errs = []
  if not (data.get("metadata") or {}).get("drawing"):
    errs.append(f"{path.name}: metadata.drawing (the wire-ID prefix) is missing")
  for s in _labels(text):
    if FORBIDDEN.search(s):
      errs.append(f"{path.name}: label has < or >: {s!r}")
  for name, c in (data.get("connectors") or {}).items():
    pins, labels = c.get("pins"), c.get("pinlabels")
    if pins is not None and labels is not None and len(pins) != len(labels):
      errs.append(f"{path.name}: {name} has {len(pins)} pins and {len(labels)} pinlabels")
  return errs


def _expand(spec) -> list:
  """WireViz pin/wire lists: [1-3, 5] -> [1, 2, 3, 5]."""
  out = []
  for item in spec if isinstance(spec, list) else [spec]:
    m = re.fullmatch(r"(\d+)-(\d+)", str(item))
    if m:
      a, b = int(m.group(1)), int(m.group(2))
      out.extend(range(a, b + 1) if a <= b else range(a, b - 1, -1))
    else:
      out.append(item)
  return out


def _pinlabel(conn: dict, pin) -> str:
  pins = conn.get("pins") or list(range(1, len(conn.get("pinlabels") or []) + 1))
  labels = conn.get("pinlabels") or []
  for p, lab in zip(pins, labels):
    if str(p) == str(pin):
      return str(lab)
  return ""


def wire_ends(paths: list[Path]) -> str:
  """One row per drawn wire or board net, in source order."""
  rows = [["id", "drawing", "kind", "signal", "colour", "gauge", "end A", "end A label", "end B", "end B label"]]
  for path in paths:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    code = data["metadata"]["drawing"]
    conns = data.get("connectors") or {}
    cables = data.get("cables") or {}
    for cset in data.get("connections") or []:
      items = [(next(iter(e)), _expand(next(iter(e.values())))) if isinstance(e, dict) else (e, None) for e in cset]
      for i in range(0, len(items) - 2, 2):
        (a, apins), (mid, mids), (b, bpins) = items[i], items[i + 1], items[i + 2]
        for k, (pa, pb) in enumerate(zip(apins, bpins)):
          end_a, end_b = f"{a}:{pa}", f"{b}:{pb}"
          la, lb = _pinlabel(conns[a], pa), _pinlabel(conns[b], pb)
          if mid in cables:
            cab = cables[mid]
            w = mids[k]
            labels = cab.get("wirelabels") or []
            colours = cab.get("colors") or []
            rows.append([f"{code}.{mid}.{w}", code, "wire", labels[w - 1] if w <= len(labels) else "",
                         colours[w - 1] if w <= len(colours) else "", str(cab.get("gauge", "")),
                         end_a, la, end_b, lb])
          else:
            rows.append([f"{code}.{a}.{pa}-{b}.{pb}", code, "line" if mid == "--" else "link", la or lb,
                         "", "", end_a, la, end_b, lb])
  buf = io.StringIO()
  csv.writer(buf, delimiter="\t", lineterminator="\n").writerows(rows)
  return buf.getvalue()


def render(path: Path, outdir: Path) -> dict[str, str]:
  """Run WireViz on one source; return {output file name: text}."""
  from wireviz import wireviz as wv
  wv.parse(path, output_formats=("svg", "gv", "tsv"), output_dir=outdir, output_name=path.stem)
  out = {}
  for suf in OUT_SUFFIXES:
    out[path.stem + suf] = (outdir / (path.stem + suf)).read_text(encoding="utf-8")
  return out


def build(paths: list[Path] | None = None) -> dict[str, str]:
  paths = sources() if paths is None else paths
  out = {}
  with tempfile.TemporaryDirectory() as tmp:
    for p in paths:
      out.update(render(p, Path(tmp)))
  out[WIRE_ENDS.name] = wire_ends(paths)
  return out


def check(out: dict[str, str], dot_ok: bool) -> list[str]:
  errs = []
  for name, text in out.items():
    path = HERE / name
    if not path.exists():
      errs.append(f"{name} missing; run make_wiring.py")
      continue
    have = path.read_text(encoding="utf-8")
    if name.endswith(".svg") and not dot_ok:
      try:
        ET.fromstring(have)
      except ET.ParseError as e:
        errs.append(f"{name} does not parse: {e}")
      continue
    if have != text:
      errs.append(f"{name} is stale; run make_wiring.py")
  expected = set(out)
  for p in HERE.iterdir():
    if p.name.endswith(OUT_SUFFIXES) and p.name not in expected:
      errs.append(f"{p.name} has no source; delete it")
  return errs


def main(argv: list[str]) -> int:
  if wireviz_version() != WIREVIZ_VERSION:
    print(f"WireViz {WIREVIZ_VERSION} required, found {wireviz_version() or 'none'} (pip install -r requirements.txt)")
    return 1
  if not shutil.which("dot"):
    print("Graphviz dot not found (apt-get install graphviz)")
    return 1
  errs = [e for p in sources() for e in problems(p)]
  if errs:
    print("\n".join(errs))
    return 1
  dot = dot_version()
  dot_ok = dot == DOT_VERSION
  out = build()
  if "--check" in argv:
    errs = check(out, dot_ok)
    mode = "byte for byte" if dot_ok else f"parse only (dot {dot or '?'} is not the pinned {DOT_VERSION})"
    print(f"{len(sources())} drawings; .gv, .bom.tsv and wire-ends.tsv byte for byte; .svg {mode}")
    if errs:
      print("\n".join(errs))
      return 1
    print("wiring outputs current")
    return 0
  if not dot_ok:
    print(f"dot {dot or '?'} is not the pinned {DOT_VERSION}; the SVGs would not match CI. Not writing.")
    return 1
  for name, text in out.items():
    (HERE / name).write_text(text, encoding="utf-8")
  print(f"wrote {len(out)} files")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
